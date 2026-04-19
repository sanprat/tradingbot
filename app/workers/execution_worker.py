"""Execution worker - consumes order intents from queue and executes them."""

import asyncio
import logging
from typing import Optional

from app.core.database import AsyncSessionLocal
from app.core.execution_engine import ExecutionEngine
from app.api.webhook import set_execution_queue

logger = logging.getLogger(__name__)

execution_queue: Optional[asyncio.Queue] = None
_worker_task: Optional[asyncio.Task] = None
_reconcile_task: Optional[asyncio.Task] = None
_is_running = False


def start_execution_worker():
    """Start the execution worker and reconciliation worker."""
    global execution_queue, _worker_task, _reconcile_task, _is_running
    
    if _is_running:
        logger.warning("Execution worker already running")
        return
    
    execution_queue = asyncio.Queue(maxsize=1000)
    set_execution_queue(execution_queue)
    
    _worker_task = asyncio.create_task(_run_worker())
    
    from app.workers.reconciliation_worker import start_reconciliation_worker
    asyncio.create_task(start_reconciliation_worker())
    
    _is_running = True
    
    logger.info("Execution and reconciliation workers started")


async def stop_execution_worker():
    """Stop the execution worker and reconciliation worker."""
    global _is_running
    
    if not _is_running:
        return
    
    _is_running = False
    
    from app.workers.reconciliation_worker import stop_reconciliation_worker
    await stop_reconciliation_worker()
    
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    
    logger.info("Execution workers stopped")


async def _run_worker():
    """Main worker loop - processes order intents from queue."""
    global execution_queue
    
    logger.info("Execution worker loop started")
    
    while _is_running:
        try:
            order_intent_id = await asyncio.wait_for(
                execution_queue.get(),
                timeout=1.0,
            )
        except asyncio.TimeoutError:
            continue
        except asyncio.CancelledError:
            break
        
        try:
            async with AsyncSessionLocal() as db:
                engine = ExecutionEngine(db)
                result = await engine.execute(order_intent_id)
                
                logger.info(f"Order {order_intent_id} execution result: {result.get('status')}")
                
        except Exception as e:
            logger.error(f"Error executing order {order_intent_id}: {e}")
    
    logger.info("Execution worker loop stopped")