"""Database repositories for TradingBot."""

from typing import Optional, List
from sqlalchemy import select, update as sql_update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.models import (
    AuditLog,
    BrokerOrder,
    OrderIntent,
    Position,
    SignalEvent,
    SystemSetting,
    TradeFill,
    SignalStatus,
    OrderStatus,
    PositionStatus,
)


async def create_signal_event(
    db: AsyncSession,
    correlation_id: str,
    strategy_id: str,
    symbol: str,
    exchange: str,
    side: str,
    quantity: float,
    order_type: str,
    product: str,
    price: Optional[float],
    trigger_price: Optional[float],
    validity: Optional[str],
    broker: Optional[str],
    tags: Optional[list],
    timestamp: str,
    idempotency_key: str,
) -> SignalEvent:
    """Create and persist a signal event."""
    event = SignalEvent(
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        strategy_id=strategy_id,
        symbol=symbol,
        exchange=exchange,
        side=side,
        quantity=quantity,
        order_type=order_type,
        product=product,
        price=price,
        trigger_price=trigger_price,
        validity=validity,
        broker=broker,
        tags=tags,
        timestamp=timestamp,
        status=SignalStatus.RECEIVED,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_signal_event_by_idempotency(
    db: AsyncSession, idempotency_key: str
) -> Optional[SignalEvent]:
    """Get a signal event by its idempotency key."""
    result = await db.execute(
        select(SignalEvent).filter_by(idempotency_key=idempotency_key)
    )
    return result.scalar_one_or_none()


async def create_order_intent(
    db: AsyncSession,
    correlation_id: str,
    signal_event_id: int,
    strategy_id: str,
    symbol: str,
    exchange: str,
    side: str,
    quantity: float,
    order_type: str,
    price: Optional[float],
    stop_loss: Optional[float],
    take_profit: Optional[float],
    broker: str,
    product: str,
    validity: Optional[str],
    tags: Optional[list],
) -> OrderIntent:
    """Create and persist an order intent."""
    intent = OrderIntent(
        correlation_id=correlation_id,
        signal_event_id=signal_event_id,
        strategy_id=strategy_id,
        symbol=symbol,
        exchange=exchange,
        side=side,
        quantity=quantity,
        order_type=order_type,
        price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        broker=broker,
        product=product,
        validity=validity,
        tags=tags,
    )
    db.add(intent)
    await db.commit()
    await db.refresh(intent)
    return intent


async def create_broker_order(
    db: AsyncSession,
    order_intent_id: int,
    broker_order_id: str,
    broker: str,
    status: str,
    average_price: Optional[float],
    filled_quantity: Optional[float],
    raw_response: dict,
) -> BrokerOrder:
    """Create and persist a broker order record."""
    bo = BrokerOrder(
        order_intent_id=order_intent_id,
        broker_order_id=broker_order_id,
        broker=broker,
        status=status,
        average_price=average_price,
        filled_quantity=filled_quantity,
        raw_response=raw_response,
    )
    db.add(bo)
    await db.commit()
    await db.refresh(bo)
    return bo


async def update_broker_order_status(
    db: AsyncSession,
    broker_order_id: str,
    status: str,
    average_price: Optional[float] = None,
    filled_quantity: Optional[float] = None,
) -> bool:
    """Update broker order status."""
    stmt = (
        sql_update(BrokerOrder)
        .where(BrokerOrder.broker_order_id == broker_order_id)
        .values(
            status=status,
            average_price=average_price,
            filled_quantity=filled_quantity,
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def create_trade_fill(
    db: AsyncSession,
    broker_order_id: str,
    quantity: float,
    price: float,
    realized_pnl: Optional[float],
) -> TradeFill:
    """Create and persist a trade fill record."""
    fill = TradeFill(
        broker_order_id=broker_order_id,
        quantity=quantity,
        price=price,
        realized_pnl=realized_pnl,
    )
    db.add(fill)
    await db.commit()
    await db.refresh(fill)
    return fill


async def create_position(
    db: AsyncSession,
    order_intent_id: int,
    strategy_id: str,
    symbol: str,
    exchange: str,
    entry_price: float,
    quantity: int,
    product_type: str,
    stoploss: Optional[float],
    target: Optional[float],
) -> Position:
    """Create and persist a position record."""
    pos = Position(
        order_intent_id=order_intent_id,
        strategy_id=strategy_id,
        symbol=symbol,
        exchange=exchange,
        entry_price=entry_price,
        quantity=quantity,
        product_type=product_type,
        stoploss=stoploss,
        target=target,
    )
    db.add(pos)
    await db.commit()
    await db.refresh(pos)
    return pos


async def update_position(
    db: AsyncSession,
    position_id: int,
    status: Optional[PositionStatus] = None,
    exit_time: Optional[str] = None,
    exit_price: Optional[float] = None,
    pnl: Optional[float] = None,
    pnl_pct: Optional[float] = None,
    exit_reason: Optional[str] = None,
    broker_exit_order_id: Optional[str] = None,
) -> bool:
    """Update a position record."""
    update_data = {}
    if status is not None:
        update_data["status"] = status.value
    if exit_time is not None:
        update_data["exit_time"] = exit_time
    if exit_price is not None:
        update_data["exit_price"] = exit_price
    if pnl is not None:
        update_data["pnl"] = pnl
    if pnl_pct is not None:
        update_data["pnl_pct"] = pnl_pct
    if exit_reason is not None:
        update_data["exit_reason"] = exit_reason
    if broker_exit_order_id is not None:
        update_data["broker_exit_order_id"] = broker_exit_order_id

    if not update_data:
        return False

    stmt = sql_update(Position).where(Position.id == position_id).values(**update_data)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def create_audit_log(
    db: AsyncSession,
    signal_event_id: Optional[int],
    order_intent_id: Optional[int],
    position_id: Optional[int],
    event_type: str,
    details: dict,
) -> AuditLog:
    """Create and persist an audit log entry."""
    log = AuditLog(
        signal_event_id=signal_event_id,
        order_intent_id=order_intent_id,
        position_id=position_id,
        event_type=event_type,
        details=details,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_open_positions(
    db: AsyncSession, symbol: Optional[str] = None
) -> List[Position]:
    """Get open positions, optionally filtered by symbol."""
    query = select(Position).filter(Position.status == PositionStatus.OPEN)
    if symbol:
        query = query.filter(Position.symbol == symbol)
    result = await db.execute(query)
    return result.scalars().all()


async def get_broker_orders_for_strategy(
    db: AsyncSession, strategy_id: str
) -> List[BrokerOrder]:
    """Get broker orders for a strategy."""
    from sqlalchemy import join

    query = (
        select(BrokerOrder)
        .join(OrderIntent, BrokerOrder.order_intent_id == OrderIntent.id)
        .where(OrderIntent.signal_event.has(SignalEvent.strategy_id == strategy_id))
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_system_setting(db: AsyncSession, key: str, default=None) -> Optional:
    """Get a system setting value."""
    result = await db.execute(
        select(SystemSetting).filter_by(key=key)
    )
    obj = result.scalar_one_or_none()
    return obj.value if obj else default


async def set_system_setting(db: AsyncSession, key: str, value) -> None:
    """Set a system setting value."""
    from sqlalchemy import update as sql_update
    
    result = await db.execute(
        select(SystemSetting).filter_by(key=key)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        await db.execute(
            sql_update(SystemSetting)
            .where(SystemSetting.key == key)
            .values(value=value)
        )
    else:
        db.add(SystemSetting(key=key, value=value))
    
    await db.commit()