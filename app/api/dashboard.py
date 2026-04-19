"""Dashboard API - monitoring endpoints."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.storage.models import (
    Position, 
    OrderIntent, 
    SignalEvent, 
    PositionStatus, 
    OrderStatus,
    EnvironmentType,
)
from app.storage.repositories import get_system_setting, set_system_setting
from app.brokers.factory import get_broker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/positions")
async def get_positions(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get open/closed positions with PnL."""
    query = select(Position)
    
    if status_filter:
        query = query.filter(Position.status == PositionStatus(status_filter))
    else:
        query = query.filter(Position.status == PositionStatus.OPEN)
    
    query = query.order_by(Position.created_at.desc())
    result = await db.execute(query)
    positions = result.scalars().all()
    
    return {
        "count": len(positions),
        "positions": [
            {
                "id": p.id,
                "symbol": p.symbol,
                "exchange": p.exchange,
                "side": "long" if p.quantity > 0 else "short",
                "quantity": abs(p.quantity),
                "entry_price": p.entry_price,
                "exit_price": p.exit_price,
                "stoploss": p.stoploss,
                "target": p.target,
                "status": p.status.value,
                "pnl": p.pnl,
                "pnl_pct": p.pnl_pct,
                "environment": p.environment.value,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in positions
        ],
    }


@router.get("/orders")
async def get_orders(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get order history with status."""
    query = select(OrderIntent).order_by(OrderIntent.created_at.desc())
    
    if status_filter:
        query = query.filter(OrderIntent.status == OrderStatus(status_filter))
    
    query = query.limit(limit)
    result = await db.execute(query)
    orders = result.scalars().all()
    
    return {
        "count": len(orders),
        "orders": [
            {
                "id": o.id,
                "symbol": o.symbol,
                "side": o.side,
                "quantity": o.quantity,
                "order_type": o.order_type,
                "status": o.status.value,
                "broker": o.broker,
                "environment": o.environment.value,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ],
    }


@router.get("/signals")
async def get_signals(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get signal event log."""
    query = (
        select(SignalEvent)
        .order_by(SignalEvent.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    signals = result.scalars().all()
    
    return {
        "count": len(signals),
        "signals": [
            {
                "id": s.id,
                "correlation_id": s.correlation_id,
                "strategy_id": s.strategy_id,
                "symbol": s.symbol,
                "side": s.side,
                "quantity": s.quantity,
                "status": s.status.value,
                "environment": s.environment.value,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in signals
        ],
    }


@router.get("/status")
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """Get system status: kill switch, broker health, daily PnL."""
    kill_switch = await get_system_setting(db, "kill_switch", False)
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.sum(Position.pnl)).filter(
            Position.environment == EnvironmentType.PAPER,
            Position.status == PositionStatus.CLOSED,
            Position.exit_time >= today_start.isoformat(),
        )
    )
    daily_pnl = result.scalar() or 0
    
    result = await db.execute(
        select(func.count(Position.id)).filter(
            Position.status == PositionStatus.OPEN,
        )
    )
    open_positions = result.scalar() or 0
    
    broker_health = {}
    for broker_name in ["paper"]:
        if settings.is_live_mode:
            broker_name = settings.DEFAULT_BROKER
        
        try:
            broker = get_broker(broker_name)
            health = broker.health_check()
            broker_health[broker_name] = health
        except Exception as e:
            broker_health[broker_name] = {"status": "error", "message": str(e)}
    
    return {
        "mode": settings.ENVIRONMENT,
        "kill_switch": kill_switch,
        "daily_pnl": daily_pnl,
        "open_positions": open_positions,
        "max_positions": settings.MAX_OPEN_POSITIONS,
        "broker_health": broker_health,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/settings/kill-switch")
async def toggle_kill_switch(
    enabled: bool,
    db: AsyncSession = Depends(get_db),
):
    """Toggle kill switch."""
    await set_system_setting(db, "kill_switch", enabled)
    logger.info(f"Kill switch {'enabled' if enabled else 'disabled'}")
    
    return {
        "status": "ok",
        "kill_switch": enabled,
    }


@router.post("/settings/mode")
async def switch_mode(
    mode: str,
    db: AsyncSession = Depends(get_db),
):
    """Switch paper/live mode."""
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail="Mode must be 'paper' or 'live'")
    
    settings.ENVIRONMENT = mode
    settings.DEFAULT_BROKER = mode
    
    await set_system_setting(db, "environment", mode)
    logger.info(f"Switched to {mode} mode")
    
    return {
        "status": "ok",
        "mode": mode,
    }