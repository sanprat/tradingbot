"""API router configuration."""

from app.api.dashboard import router as dashboard_router
from app.api.webhook import router as webhook_router
from app.api.settings import router as settings_router

routers = [dashboard_router, webhook_router, settings_router]