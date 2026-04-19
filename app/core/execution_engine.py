"""Execution Engine - Core orchestration for order execution."""

import logging
from typing import Optional
from sqlalchemy import select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import (
    OrderIntent,
    OrderStatus,
    SignalStatus,
)
from app.storage.repositories import (
    create_broker_order,
    create_position,
    update_position,
    create_audit_log,
)
from app.brokers.factory import get_broker

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Core orchestration for order execution."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(self, order_intent_id: int) -> dict:
        """
        Execute an order intent through the full workflow.
        
        Steps:
        1. Load OrderIntent from DB
        2. Run risk checks
        3. Select broker adapter
        4. Place order
        5. Track state
        6. Create position if filled
        """
        result = await self._load_order_intent(order_intent_id)
        if not result:
            return {"status": "error", "message": "Order intent not found"}

        order_intent, risk_result = result

        if not risk_result["passed"]:
            await self._reject_order_intent(order_intent_id, risk_result["reason"])
            return {"status": "rejected", "reason": risk_result["reason"]}

        await self._update_order_status(order_intent_id, OrderStatus.QUEUED)

        broker = get_broker(order_intent.broker)

        broker_response = broker.place_order(
            symbol=order_intent.symbol,
            exchange=order_intent.exchange,
            side=order_intent.side,
            quantity=order_intent.quantity,
            price=order_intent.price or 0,
            order_type=order_intent.order_type,
            product=order_intent.product,
            validity=order_intent.validity or "DAY",
        )

        if broker_response.get("status") == "error":
            await self._reject_order_intent(order_intent_id, broker_response.get("message", "Broker error"))
            await create_audit_log(
                self.db,
                signal_event_id=order_intent.signal_event_id,
                order_intent_id=order_intent_id,
                position_id=None,
                event_type="order_rejected",
                details={"reason": broker_response.get("message")},
            )
            return broker_response

        await self._update_order_status(order_intent_id, OrderStatus.SUBMITTED)

        broker_order_id = broker_response.get("order_id") or f"sim_{order_intent_id}"
        
        await create_broker_order(
            self.db,
            order_intent_id=order_intent_id,
            broker_order_id=broker_order_id,
            broker=order_intent.broker,
            status=broker_response.get("status", "pending"),
            average_price=broker_response.get("average_price"),
            filled_quantity=broker_response.get("filled_quantity"),
            raw_response=broker_response,
        )

        fill_price = broker_response.get("average_price", order_intent.price or 0)
        filled_qty = broker_response.get("filled_quantity", order_intent.quantity)

        if filled_qty and filled_qty > 0:
            await self._update_order_status(order_intent_id, OrderStatus.FILLED)

            position = await create_position(
                self.db,
                order_intent_id=order_intent_id,
                strategy_id=order_intent.strategy_id,
                symbol=order_intent.symbol,
                exchange=order_intent.exchange,
                entry_price=fill_price,
                quantity=int(filled_qty),
                product_type=order_intent.product,
                stoploss=order_intent.stop_loss,
                target=order_intent.take_profit,
                environment=order_intent.environment,
            )

            await create_audit_log(
                self.db,
                signal_event_id=order_intent.signal_event_id,
                order_intent_id=order_intent_id,
                position_id=position.id,
                event_type="position_opened",
                details={
                    "entry_price": fill_price,
                    "quantity": filled_qty,
                    "stoploss": order_intent.stop_loss,
                    "target": order_intent.take_profit,
                },
            )

            return {
                "status": "filled",
                "broker_order_id": broker_order_id,
                "position_id": position.id,
                "fill_price": fill_price,
                "filled_quantity": filled_qty,
            }

        await self._update_order_status(order_intent_id, OrderStatus.OPEN)
        return {
            "status": "submitted",
            "broker_order_id": broker_order_id,
        }

    async def _load_order_intent(self, order_intent_id: int):
        """Load order intent and run risk checks."""
        from app.core.risk import check_order_risk
        
        result = await self.db.execute(
            select(OrderIntent).where(OrderIntent.id == order_intent_id)
        )
        order_intent = result.scalar_one_or_none()
        
        if not order_intent:
            return None

        risk_result = await check_order_risk(self.db, order_intent)
        return order_intent, risk_result

    async def _update_order_status(self, order_intent_id: int, status: OrderStatus):
        """Update order intent status."""
        stmt = (
            sql_update(OrderIntent)
            .where(OrderIntent.id == order_intent_id)
            .values(status=status)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def _reject_order_intent(self, order_intent_id: int, reason: str):
        """Mark order intent as rejected."""
        await self._update_order_status(order_intent_id, OrderStatus.REJECTED)
        await create_audit_log(
            self.db,
            signal_event_id=None,
            order_intent_id=order_intent_id,
            position_id=None,
            event_type="order_rejected",
            details={"reason": reason},
        )