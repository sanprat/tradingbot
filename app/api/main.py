"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routers
from app.core.config import settings

app = FastAPI(title=settings.API_TITLE, version=settings.API_VERSION)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
for router in routers.routers:
    app.include_router(router)

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "app": "TradingBot", "port": settings.API_PORT}