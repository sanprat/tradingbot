"""Broker factory - creates broker adapter instances."""

import logging
from typing import Dict, Any, Optional

from app.brokers.base import BrokerAdapter

logger = logging.getLogger(__name__)

_broker_cache: Dict[str, BrokerAdapter] = {}


def get_broker(name: str) -> BrokerAdapter:
    """
    Get or create a broker adapter by name.
    
    Broker names:
    - "paper" - Paper trading simulator
    - "dhan" - Dhan live trading
    - "shoonya" - Shoonya live trading
    - "default" - Uses config DEFAULT_BROKER setting
    """
    from app.core.config import settings
    
    if name == "default":
        name = settings.DEFAULT_BROKER
    
    if name in _broker_cache:
        return _broker_cache[name]
    
    if name == "paper":
        from app.brokers.paper import PaperBroker
        broker = PaperBroker({})
    elif name == "dhan":
        from app.brokers.dhan import DhanAdapter
        broker = DhanAdapter({
            "client_id": settings.DHAN_CLIENT_ID,
            "access_token": settings.DHAN_ACCESS_TOKEN,
        })
    elif name == "shoonya":
        from app.brokers.shoonya import ShoonyaAdapter
        broker = ShoonyaAdapter({
            "userid": settings.SHOONYA_USER_ID,
            "password": settings.SHOONYA_PASSWORD,
            "vendor_code": settings.SHOONYA_VENDOR_CODE,
            "api_secret": settings.SHOONYA_API_KEY,
            "imei": settings.SHOONYA_IMEI,
            "totp_secret": settings.SHOONYA_TOTP_SECRET,
        })
    else:
        logger.warning(f"Unknown broker {name}, defaulting to paper")
        from app.brokers.paper import PaperBroker
        broker = PaperBroker({})
    
    _broker_cache[name] = broker
    return broker


def clear_broker_cache():
    """Clear broker cache (useful for testing)."""
    _broker_cache.clear()