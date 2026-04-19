"""
TradingBot Configuration
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Application settings loaded from environment variables."""

    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    API_TITLE = "TradingBot API"
    API_VERSION = "1.0"
    API_PORT = int(os.getenv("API_PORT", "8001"))

    DEFAULT_BROKER = os.getenv("DEFAULT_BROKER", "dhan")
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

    TRADINGVIEW_WEBHOOK_SECRET = os.getenv(
        "TRADINGVIEW_WEBHOOK_SECRET", 
        "dev-secret-change-in-production"
    )
    WEBHOOK_MAX_CLOCK_SKEW_MINUTES = int(
        os.getenv("WEBHOOK_MAX_CLOCK_SKEW_MINUTES", "5")
    )

    MARKET_OPEN_HOUR = 9
    MARKET_OPEN_MINUTE = 15
    MARKET_CLOSE_HOUR = 15
    MARKET_CLOSE_MINUTE = 30

    MAX_ORDER_QUANTITY = int(os.getenv("MAX_ORDER_QUANTITY", "10000"))
    MAX_ORDER_NOTIONAL = float(os.getenv("MAX_ORDER_NOTIONAL", "1000000.0"))
    MAX_DAILY_LOSS = float(os.getenv("MAX_DAILY_LOSS", "5000.0"))
    MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "10"))
    SIGNAL_COOLDOWN_SECONDS = int(os.getenv("SIGNAL_COOLDOWN_SECONDS", "30"))

    WEBHOOK_QUEUE_TTL_SECONDS = int(os.getenv("WEBHOOK_QUEUE_TTL_SECONDS", "300"))
    API_RESPONSE_TIMEOUT = int(os.getenv("API_RESPONSE_TIMEOUT", "30"))

    CORS_ORIGINS = [
        origin.strip() 
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
    ]

    SHOONYA_USER_ID = os.getenv("SHOONYA_USER_ID", "")
    SHOONYA_PASSWORD = os.getenv("SHOONYA_PASSWORD", "")
    SHOONYA_API_KEY = os.getenv("SHOONYA_API_KEY", "")
    SHOONYA_VENDOR_CODE = os.getenv("SHOONYA_VENDOR_CODE", "")
    SHOONYA_IMEI = os.getenv("SHOONYA_IMEI", "")
    SHOONYA_TOTP_SECRET = os.getenv("SHOONYA_TOTP_SECRET", "")

    DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")
    DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")

    


settings = Settings()