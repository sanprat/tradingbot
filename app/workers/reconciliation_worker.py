"""Reconciliation worker - syncs local state with broker state."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.core.database import AsyncSessionLocal
from app.brokers.factory import get_broker
from app.storage.models import BrokerOrder, Position, PositionStatus
from app.storage.repositories import update_position, create_audit_log
from sqlalchemy import select

logger = logging.getLogger(__name__)

RECONCILE_INTERVAL = 60
_worker_task: Optional[asyncio.Task] = None
_is_running = False


async def start_reconciliation_worker():
    """Start the reconciliation worker."""
    global _worker_task, _is_running
    
    if _is_running:
        logger.warning("Reconciliation worker already running")
        return
    
    _is_running = True
    _worker_task = asyncio.create_task(_run_reconciliation())
    logger.info("Reconciliation worker started")


async def stop_reconciliation_worker():
    """Stop the reconciliation worker."""
    global _is_running
    
    if not _is_running:
        return
    
    _is_running = False
    
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Reconciliation worker stopped")


async def _run_reconciliation():
    """Main reconciliation loop."""
    logger.info("Reconciliation loop started")
    
    while _is_running:
        try:
            await asyncio.sleep(RECONCILE_INTERVAL)
            await _reconcile_all()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Reconciliation error: {e}")
    
    logger.info("Reconciliation loop stopped")


async def _reconcile_all():
    """Reconciliation all broker state with local state."""
    from app.core.config import settings
    
    broker_name = settings.DEFAULT_BROKER
    try:
        await _reconcile_broker(broker_name)
    except Exception as e:
        logger.error(f"Error reconciling broker {broker_name}: {e}")


async def _reconcile_broker(broker_name: str):
    """Reconcile state for a specific broker."""
    broker = get_broker(broker_name)
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Position).filter(
                Position.status == PositionStatus.OPEN,
            )
        )
        positions = result.scalars().all()
        
        broker_positions = broker.get_positions()
        broker_position_map = {
            p.get("tsym"): p for p in broker_positions
        }
        
        for position in positions:
            broker_key = f"{position.symbol}:{position.exchange}"
            
            if broker_key not in broker_position_map:
                continue
            
            broker_pos = broker_position_map[broker_key]
            
            if broker_pos.get("NetQty", 0) == 0:
                exit_price = broker_pos.get("avgprc", position.entry_price)
                
                pnl = (exit_price - position.entry_price) * position.quantity
                if position.stoploss and exit_price <= position.stoploss:
                    pnl = (position.stoploss - position.entry_price) * position.quantity
                    exit_reason = "stoploss"
                elif position.target and exit_price >= position.target:
                    pnl = (position.target - position.entry_price) * position.quantity
                    exit_reason = "target"
                else:
                    exit_reason = "manual"
                
                pnl_pct = (pnl / position.entry_price) * 100 if position.entry_price else 0
                
                await update_position(
                    db,
                    position_id=position.id,
                    status=PositionStatus.CLOSED,
                    exit_time=datetime.utcnow().isoformat(),
                    exit_price=exit_price,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    exit_reason=exit_reason,
                )
                
                await create_audit_log(
                    db,
                    signal_event_id=None,
                    order_intent_id=position.order_intent_id,
                    position_id=position.id,
                    event_type="position_closed",
                    details={
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "exit_reason": exit_reason,
                    },
                )
                
                logger.info(f"Reconciled position {position.id}: closed at {exit_price}, PnL: {pnl}")