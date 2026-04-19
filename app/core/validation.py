"""Validation logic for TradingView webhook and orders."""

import time
from typing import Optional
from fastapi import HTTPException, status

from app.core.config import settings
from app.storage.repositories import get_signal_event_by_idempotency
from sqlalchemy.ext.asyncio import AsyncSession


async def validate_tradingview_webhook(payload: dict, db: AsyncSession) -> bool:
    """
    Validate TradingView webhook secret and data.

    Validates:
    - Secret key matches TRADINGVIEW_WEBHOOK_SECRET (shared secret approach)
    - Timestamp is within allowed clock skew window
    - No duplicate idempotency_key
    """
    if payload.get("secret") != settings.TRADINGVIEW_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret",
        )

    try:
        webhook_time = int(payload["timestamp"])
        current_time = int(time.time())
        max_skew = settings.WEBHOOK_MAX_CLOCK_SKEW_MINUTES * 60
        if abs(current_time - webhook_time) > max_skew:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook timestamp too old or too new",
            )
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timestamp format",
        )

    idempotency_key = payload.get("idempotency_key")
    if idempotency_key:
        existing = await get_signal_event_by_idempotency(db, idempotency_key)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate webhook received",
            )

    return True