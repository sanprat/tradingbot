"""Risk controls for pre-trade checks."""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.storage.models import OrderIntent, Position, PositionStatus, EnvironmentType

logger = logging.getLogger(__name__)


async def check_order_risk(db: AsyncSession, order_intent: OrderIntent) -> dict:
    """
    Run all pre-trade risk checks.
    
    Returns:
        {"passed": True/False, "reason": optional rejection reason}
    """
    kill_switch = await _check_kill_switch(db)
    if not kill_switch["passed"]:
        return kill_switch

    broker_enabled = await _check_broker_enabled(db, order_intent.broker)
    if not broker_enabled["passed"]:
        return broker_enabled

    max_qty = await _check_max_quantity(order_intent.quantity)
    if not max_qty["passed"]:
        return max_qty

    if order_intent.price:
        max_notional = await _check_max_notional(
            order_intent.quantity, order_intent.price
        )
        if not max_notional["passed"]:
            return max_notional

    max_positions = await _check_max_open_positions(db, order_intent.environment)
    if not max_positions["passed"]:
        return max_positions

    max_daily_loss = await _check_max_daily_loss(db, order_intent.environment)
    if not max_daily_loss["passed"]:
        return max_daily_loss

    return {"passed": True, "reason": None}


async def _check_kill_switch(db: AsyncSession) -> dict:
    """Check if system-wide kill switch is enabled."""
    from app.storage.repositories import get_system_setting
    
    kill_switch = await get_system_setting(db, "kill_switch", False)
    if kill_switch:
        return {"passed": False, "reason": "Kill switch is enabled"}
    return {"passed": True, "reason": None}


async def _check_broker_enabled(db: AsyncSession, broker: str) -> dict:
    """Check if target broker is enabled."""
    if broker in ("paper", "default"):
        return {"passed": True, "reason": None}
    
    from app.storage.repositories import get_system_setting
    
    enabled = await get_system_setting(db, f"broker_{broker}_enabled", True)
    if not enabled:
        return {"passed": False, "reason": f"Broker {broker} is disabled"}
    return {"passed": True, "reason": None}


async def _check_max_quantity(quantity: float) -> dict:
    """Check if quantity is within limits."""
    if quantity > settings.MAX_ORDER_QUANTITY:
        return {
            "passed": False,
            "reason": f"Quantity {quantity} exceeds max {settings.MAX_ORDER_QUANTITY}",
        }
    return {"passed": True, "reason": None}


async def _check_max_notional(quantity: float, price: float) -> dict:
    """Check if notional value is within limits."""
    notional = quantity * price
    if notional > settings.MAX_ORDER_NOTIONAL:
        return {
            "passed": False,
            "reason": f"Notional {notional} exceeds max {settings.MAX_ORDER_NOTIONAL}",
        }
    return {"passed": True, "reason": None}


async def _check_max_open_positions(
    db: AsyncSession, environment: EnvironmentType
) -> dict:
    """Check if max open positions limit is reached."""
    result = await db.execute(
        select(func.count(Position.id)).filter(
            Position.status == PositionStatus.OPEN,
            Position.environment == environment,
        )
    )
    open_count = result.scalar() or 0
    
    if open_count >= settings.MAX_OPEN_POSITIONS:
        return {
            "passed": False,
            "reason": f"Max open positions {open_count} reached",
        }
    return {"passed": True, "reason": None}


async def _check_max_daily_loss(
    db: AsyncSession, environment: EnvironmentType
) -> dict:
    """Check if daily loss threshold is exceeded."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(
        select(func.sum(Position.pnl)).filter(
            Position.environment == environment,
            Position.status == PositionStatus.CLOSED,
            Position.exit_time >= today_start,
        )
    )
    daily_pnl = result.scalar() or 0
    
    if daily_pnl < -settings.MAX_DAILY_LOSS:
        return {
            "passed": False,
            "reason": f"Daily loss {daily_pnl} exceeds threshold",
        }
    return {"passed": True, "reason": None}