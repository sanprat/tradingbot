"""TradingView webhook endpoint."""

import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, field_validator

from app.core.database import get_db
from app.core.validation import validate_tradingview_webhook
from app.storage.repositories import (
    create_signal_event,
    create_order_intent,
    get_signal_event_by_idempotency,
)
from app.storage.models import EnvironmentType
from app.core.config import settings

router = APIRouter(prefix="/webhook", tags=["webhook"])

execution_queue = None


def set_execution_queue(queue):
    """Set the execution queue for the webhook."""
    global execution_queue
    execution_queue = queue


class TradingViewWebhookPayload(BaseModel):
    """TradingView webhook payload with validation."""
    secret: str = Field(..., description="Shared secret for webhook authentication")
    strategy_id: str = Field(..., description="Strategy identifier")
    symbol: str = Field(..., description="Trading symbol (e.g., RELIANCE)")
    exchange: str = Field(..., description="Exchange (e.g., NSE, BSE)")
    side: str = Field(..., description="Order side: BUY, SELL, EXIT_LONG, EXIT_SHORT")
    quantity: float = Field(..., gt=0, description="Order quantity")
    order_type: str = Field(..., description="Order type: MKT or LMT")
    product: str = Field(..., description="Product type: INTRADAY or CASH")
    timestamp: str = Field(..., description="Unix timestamp as string")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key")
    price: Optional[float] = Field(None, description="Limit price (for LMT orders)")
    trigger_price: Optional[float] = Field(None, description="Trigger price (for stop orders)")
    validity: Optional[str] = Field(None, description="Order validity")
    broker: Optional[str] = Field(None, description="Target broker")
    take_profit: Optional[float] = Field(None, description="Take profit level")
    stop_loss: Optional[float] = Field(None, description="Stop loss level")
    tags: Optional[list] = Field(None, description="Optional tags")

    @field_validator('side')
    @classmethod
    def validate_side(cls, v):
        allowed_sides = {'BUY', 'SELL', 'EXIT_LONG', 'EXIT_SHORT'}
        if v not in allowed_sides:
            raise ValueError(f'side must be one of {allowed_sides}')
        return v

    @field_validator('product')
    @classmethod
    def validate_product(cls, v):
        allowed_products = {'INTRADAY', 'CASH'}
        if v not in allowed_products:
            raise ValueError(f'product must be one of {allowed_products}')
        return v

    @field_validator('order_type')
    @classmethod
    def validate_order_type(cls, v):
        allowed_types = {'MKT', 'LMT'}
        if v not in allowed_types:
            raise ValueError(f'order_type must be one of {allowed_types}')
        return v


@router.post("/tradingview", status_code=status.HTTP_202_ACCEPTED)
async def tradingview_webhook(
    payload: TradingViewWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle TradingView alert webhook.

    Validates the webhook, checks for duplicates, persists the signal event,
    creates an order intent, and enqueues the execution worker.
    Returns 202 immediately after validation + enqueue.
    """
    try:
        # Convert Pydantic model to dict for validation
        payload_dict = payload.model_dump()

        # Validate webhook secret and data
        await validate_tradingview_webhook(payload_dict, db)

        # Generate or use provided idempotency key
        idempotency_key = payload.idempotency_key or f"tv_{payload.strategy_id}_{payload.timestamp}"

        # Check for duplicate signal
        existing = await get_signal_event_by_idempotency(db, idempotency_key)
        if existing:
            # Already processed - return the same correlation ID
            return {
                "status": "duplicate",
                "correlation_id": existing.correlation_id,
                "message": "Signal already processed",
            }

        # Determine environment (paper vs live) - use settings, fallback to broker param
        if payload.broker and payload.broker.lower() == "paper":
            environment = EnvironmentType.PAPER
        elif payload.broker and payload.broker.lower() == "live":
            environment = EnvironmentType.LIVE
        else:
            environment = (
                EnvironmentType.PAPER 
                if settings.is_paper_mode 
                else EnvironmentType.LIVE
            )

        # Persist raw signal event
        signal_event = await create_signal_event(
            db=db,
            correlation_id=f"sig_{idempotency_key}",
            strategy_id=payload.strategy_id,
            symbol=payload.symbol,
            exchange=payload.exchange,
            side=payload.side,
            quantity=payload.quantity,
            order_type=payload.order_type,
            product=payload.product,
            price=payload.price,
            trigger_price=payload.trigger_price,
            validity=payload.validity,
            broker=payload.broker,
            tags=payload.tags,
            timestamp=payload.timestamp,
            idempotency_key=idempotency_key,
            environment=environment,
        )

        # Create order intent (will be picked up by async worker)
        order_intent = await create_order_intent(
            db=db,
            correlation_id=signal_event.correlation_id,
            signal_event_id=signal_event.id,
            strategy_id=payload.strategy_id,
            symbol=payload.symbol,
            exchange=payload.exchange,
            side=payload.side,
            quantity=payload.quantity,
            order_type=payload.order_type,
            price=payload.price,
            stop_loss=payload.stop_loss,
            take_profit=payload.take_profit,
            broker=payload.broker or "default",
            product=payload.product,
            validity=payload.validity,
            tags=payload.tags,
            environment=environment,
        )

        if execution_queue:
            await execution_queue.put(order_intent.id)

        await db.commit()

        return {
            "status": "accepted",
            "correlation_id": signal_event.correlation_id,
            "order_intent_id": order_intent.id,
            "idempotency_key": idempotency_key,
        }
    except Exception:
        await db.rollback()
        raise