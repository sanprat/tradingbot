"""TradingBot main application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, close_db
from app.api import webhook, dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    logger.info("Starting TradingBot application...")
    
    await init_db()
    
    from app.workers.execution_worker import start_execution_worker
    start_execution_worker()
    
    logger.info(f"TradingBot started in {settings.ENVIRONMENT} mode on port {settings.API_PORT}")
    
    yield
    
    from app.workers.execution_worker import stop_execution_worker
    await stop_execution_worker()
    await close_db()
    
    logger.info("TradingBot shutdown complete")


app = FastAPI(
    title=settings.API_TITLE, 
    version=settings.API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": "TradingBot",
        "version": settings.API_VERSION,
        "mode": settings.ENVIRONMENT,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "TradingBot API",
        "version": settings.API_VERSION,
        "mode": settings.ENVIRONMENT,
        "docs": "/docs",
    }