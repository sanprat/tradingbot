"""
Database module for TradingBot using async SQLAlchemy with aiosqlite.
"""

import logging
from pathlib import Path
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_DB_PATH = DATA_DIR / "tradingbot.db"
DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_DB_PATH}"

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session as FastAPI dependency.
    
    Note: Commits are handled by the calling code (route handlers, workers).
    Don't auto-commit here to avoid double-commits.
    """
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Initialize database tables."""
    from app.storage.models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info(f"Database initialized at {SQLITE_DB_PATH}")


async def close_db():
    """Close database engine."""
    await engine.dispose()
    logger.info("Database connection closed")