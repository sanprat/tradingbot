"""Database models for TradingBot."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


def utc_now_naive():
    """Return current UTC time as naive datetime."""
    return datetime.utcnow()


class SignalStatus(str, enum.Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    REJECTED = "rejected"


class OrderStatus(str, enum.Enum):
    RECEIVED = "received"
    QUEUED = "queued"
    SUBMITTED = "submitted"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXIT_PENDING = "exit_pending"
    CLOSED = "closed"


class PositionStatus(str, enum.Enum):
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CLOSED = "closed"


class EnvironmentType(str, enum.Enum):
    PAPER = "paper"
    LIVE = "live"


class SignalEvent(Base):
    """Raw TradingView webhook events."""
    __tablename__ = "signal_events"

    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(36), nullable=False, index=True)
    idempotency_key = Column(String(100), nullable=False, unique=True)
    strategy_id = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    order_type = Column(String(10), nullable=False)
    product = Column(String(20), nullable=False)
    price = Column(Float)
    trigger_price = Column(Float)
    validity = Column(String(20))
    broker = Column(String(50))
    tags = Column(JSON)
    timestamp = Column(String(50))  # ISO-8601 timestamp from TradingView
    status = Column(Enum(SignalStatus), default=SignalStatus.RECEIVED)
    environment = Column(Enum(EnvironmentType), nullable=False)
    created_at = Column(DateTime(timezone=False), default=utc_now_naive)
    processed_at = Column(DateTime(timezone=False))

    # Relationships
    order_intents = relationship("OrderIntent", back_populates="signal_event", cascade="all, delete-orphan")


class OrderIntent(Base):
    """Normalized order intent awaiting execution."""
    __tablename__ = "order_intents"

    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(36), nullable=False, index=True)
    signal_event_id = Column(Integer, ForeignKey("signal_events.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # BUY, SELL, EXIT_LONG, EXIT_SHORT
    quantity = Column(Float, nullable=False)
    order_type = Column(String(10), nullable=False)
    price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    broker = Column(String(50), nullable=False)
    product = Column(String(20), default="INTRADAY")
    validity = Column(String(20))
    tags = Column(JSON)
    environment = Column(Enum(EnvironmentType), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.RECEIVED)
    created_at = Column(DateTime(timezone=False), default=utc_now_naive)
    updated_at = Column(DateTime(timezone=False), default=utc_now_naive, onupdate=utc_now_naive)

    # Relationships
    signal_event = relationship("SignalEvent", back_populates="order_intents")
    broker_orders = relationship("BrokerOrder", back_populates="order_intent", cascade="all, delete-orphan")
    position = relationship("Position", back_populates="order_intent", uselist=False)


class BrokerOrder(Base):
    """Broker API order responses."""
    __tablename__ = "broker_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_intent_id = Column(Integer, ForeignKey("order_intents.id", ondelete="CASCADE"), nullable=False)
    broker_order_id = Column(String(100), nullable=False, unique=True)
    broker = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)  # COMPLETE, REJECTED, PENDING, etc.
    average_price = Column(Float)
    filled_quantity = Column(Float, default=0.0)
    raw_response = Column(JSON)
    created_at = Column(DateTime(timezone=False), default=utc_now_naive)
    updated_at = Column(DateTime(timezone=False), default=utc_now_naive, onupdate=utc_now_naive)

    # Relationships
    order_intent = relationship("OrderIntent", back_populates="broker_orders")
    trade_fills = relationship("TradeFill", back_populates="broker_order", cascade="all, delete-orphan")


class TradeFill(Base):
    """Completed trade fills."""
    __tablename__ = "trade_fills"

    id = Column(Integer, primary_key=True, index=True)
    broker_order_id = Column(Integer, ForeignKey("broker_orders.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    realized_pnl = Column(Float)
    created_at = Column(DateTime(timezone=False), default=utc_now_naive)

    # Relationships
    broker_order = relationship("BrokerOrder", back_populates="trade_fills")


class Position(Base):
    """Current open positions with SL/Target."""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    order_intent_id = Column(Integer, ForeignKey("order_intents.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(String(50), nullable=False)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(20), default="NSE")
    entry_price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    product_type = Column(String(20), default="INTRADAY")
    stoploss = Column(Float)
    target = Column(Float)
    status = Column(Enum(PositionStatus), default=PositionStatus.OPEN)
    entry_time = Column(DateTime(timezone=False), default=utc_now_naive)
    exit_time = Column(DateTime(timezone=False))
    exit_price = Column(Float)
    pnl = Column(Float)
    pnl_pct = Column(Float)
    exit_reason = Column(String(100))
    broker_order_id = Column(String(100))
    broker_exit_order_id = Column(String(100))
    environment = Column(Enum(EnvironmentType), nullable=False)
    created_at = Column(DateTime(timezone=False), default=utc_now_naive)

    # Relationships
    order_intent = relationship("OrderIntent", back_populates="position")


class AuditLog(Base):
    """Audit trail for trading events."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    signal_event_id = Column(Integer, ForeignKey("signal_events.id", ondelete="CASCADE"), nullable=True)
    order_intent_id = Column(Integer, ForeignKey("order_intents.id", ondelete="SET NULL"), nullable=True)
    position_id = Column(Integer, ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(100), nullable=False)
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=False), default=utc_now_naive)

    # Relationships
    signal_event = relationship("SignalEvent")
    order_intent = relationship("OrderIntent")
    position = relationship("Position")


class SystemSetting(Base):
    """System-wide settings."""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True)
    value = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=False), default=utc_now_naive, onupdate=utc_now_naive)