"""Settings API - broker credentials and system configuration."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from cryptography.fernet import Fernet
import base64
import hashlib

from app.core.database import get_db
from app.core.config import settings as app_settings
from app.storage.repositories import get_system_setting, set_system_setting
from app.brokers.factory import get_broker, clear_broker_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])

ALLOWED_BROKERS = {"dhan", "shoonya"}


def _get_encryption_key() -> bytes:
    """Get or generate encryption key from environment."""
    key = app_settings.CREDENTIAL_ENCRYPTION_KEY
    if not key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CREDENTIAL_ENCRYPTION_KEY not configured",
        )
    hashed = hashlib.sha256(key.encode()).digest()
    return base64.urlsafe_b64encode(hashed)


def _encrypt_value(value: str) -> str:
    """Encrypt a credential value."""
    if not value:
        return ""
    fernet = Fernet(_get_encryption_key())
    return fernet.encrypt(value.encode()).decode()


def _decrypt_value(value: str) -> Optional[str]:
    """Decrypt a credential value."""
    if not value:
        return None
    try:
        fernet = Fernet(_get_encryption_key())
        return fernet.decrypt(value.encode()).decode()
    except Exception:
        return None


def _mask_secret(secret: str, show_last: int = 4) -> str:
    """Mask a secret, showing only last N characters."""
    if not secret:
        return ""
    if len(secret) <= show_last:
        return "••••••"
    return "••••••" + secret[-show_last:]


class BrokerCredentials(BaseModel):
    """Broker credentials payload."""
    client_id: Optional[str] = Field(None, description="Client ID (for dhan)")
    access_token: Optional[str] = Field(None, description="Access token (for dhan)")
    userid: Optional[str] = Field(None, description="User ID (for shoonya)")
    password: Optional[str] = Field(None, description="Password (for shoonya)")
    vendor_code: Optional[str] = Field(None, description="Vendor code (for shoonya)")
    api_secret: Optional[str] = Field(None, description="API secret (for shoonya)")
    imei: Optional[str] = Field(None, description="IMEI (for shoonya)")
    totp_secret: Optional[str] = Field(None, description="TOTP secret (for shoonya)")


class WebhookSecretPayload(BaseModel):
    """Update webhook secret payload."""
    secret: str = Field(..., min_length=8, description="New webhook secret")


async def _validate_broker(broker: str) -> str:
    """Validate broker name."""
    if broker.lower() not in ALLOWED_BROKERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid broker. Allowed: {', '.join(ALLOWED_BROKERS)}",
        )
    return broker.lower()


@router.get("/broker-config/{broker}")
async def get_broker_config(
    broker: str,
    db: AsyncSession = Depends(get_db),
):
    """Get broker configuration with masked secrets."""
    broker = await _validate_broker(broker)
    
    cred_key = f"broker_credentials_{broker}"
    encrypted_creds = await get_system_setting(db, cred_key)
    
    if not encrypted_creds:
        return {
            "broker": broker,
            "configured": False,
            "credentials": None,
        }
    
    decrypted = _decrypt_value(encrypted_creds)
    if not decrypted:
        return {
            "broker": broker,
            "configured": False,
            "credentials": None,
        }
    
    import json
    try:
        creds = json.loads(decrypted)
    except json.JSONDecodeError:
        return {
            "broker": broker,
            "configured": False,
            "credentials": None,
        }
    
    masked_creds = {}
    for key, value in creds.items():
        if value and isinstance(value, str):
            masked_creds[key] = _mask_secret(value)
        else:
            masked_creds[key] = value
    
    return {
        "broker": broker,
        "configured": True,
        "credentials": masked_creds,
    }


@router.post("/broker-credentials/{broker}")
async def save_broker_credentials(
    broker: str,
    credentials: BrokerCredentials,
    db: AsyncSession = Depends(get_db),
):
    """Save broker credentials (encrypted)."""
    broker = await _validate_broker(broker)
    
    creds_dict = credentials.model_dump(exclude_none=True)
    if not creds_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No credentials provided",
        )
    
    import json
    encrypted = _encrypt_value(json.dumps(creds_dict))
    
    cred_key = f"broker_credentials_{broker}"
    await set_system_setting(db, cred_key, encrypted)
    
    clear_broker_cache()
    logger.info(f"Credentials saved for broker: {broker}")
    
    return {
        "status": "ok",
        "broker": broker,
        "message": "Credentials saved successfully",
    }


@router.post("/broker-test/{broker}")
async def test_broker_connection(
    broker: str,
    db: AsyncSession = Depends(get_db),
):
    """Test broker connection using stored credentials."""
    broker = await _validate_broker(broker)
    
    cred_key = f"broker_credentials_{broker}"
    encrypted_creds = await get_system_setting(db, cred_key)
    
    if not encrypted_creds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No credentials configured for {broker}",
        )
    
    decrypted = _decrypt_value(encrypted_creds)
    if not decrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to decrypt credentials",
        )
    
    import json
    try:
        creds = json.loads(decrypted)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials format",
        )
    
    try:
        if broker == "dhan":
            test_broker = get_broker(broker)
        elif broker == "shoonya":
            test_broker = get_broker(broker)
        
        health = test_broker.health_check()
        
        return {
            "broker": broker,
            "status": "ok",
            "health": health,
        }
    except Exception as e:
        logger.error(f"Broker test failed for {broker}: {e}")
        return {
            "broker": broker,
            "status": "error",
            "message": str(e),
        }


@router.delete("/broker-credentials/{broker}")
async def clear_broker_credentials(
    broker: str,
    db: AsyncSession = Depends(get_db),
):
    """Clear broker credentials."""
    broker = await _validate_broker(broker)
    
    cred_key = f"broker_credentials_{broker}"
    await set_system_setting(db, cred_key, None)
    
    clear_broker_cache()
    logger.info(f"Credentials cleared for broker: {broker}")
    
    return {
        "status": "ok",
        "broker": broker,
        "message": "Credentials cleared successfully",
    }


@router.post("/webhook-secret")
async def update_webhook_secret(
    payload: WebhookSecretPayload,
    db: AsyncSession = Depends(get_db),
):
    """Update TradingView webhook secret."""
    await set_system_setting(db, "tradingview_webhook_secret", payload.secret)
    
    logger.info("Webhook secret updated")
    
    return {
        "status": "ok",
        "message": "Webhook secret updated successfully",
    }