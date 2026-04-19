"""Base broker adapter interface."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum


class OrderStatus(str, Enum):
    COMPLETE = "complete"
    REJECTED = "rejected"
    PENDING = "pending"
    CANCELLED = "cancelled"


class BrokerCapabilities:
    """Broker capability flags."""
    def __init__(
        self,
        supports_bracket_orders: bool = False,
        supports_stop_loss: bool = True,
        supports_target: bool = True,
        supported_order_types: List[str] = None,
        supported_products: List[str] = None,
    ):
        self.supports_bracket_orders = supports_bracket_orders
        self.supports_stop_loss = supports_stop_loss
        self.supports_target = supports_target
        self.supported_order_types = supported_order_types or ["MKT", "LMT"]
        self.supported_products = supported_products or ["INTRADAY", "CASH"]


class BrokerAdapter(ABC):
    """Abstract base class for broker adapters."""

    def __init__(self, credentials: Dict[str, Any]):
        self.credentials = credentials
        self.capabilities = self._get_capabilities()

    @abstractmethod
    def _get_capabilities(self) -> BrokerCapabilities:
        """Return broker-specific capabilities."""
        pass

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        exchange: str,
        side: str,
        quantity: float,
        price: float = 0,
        order_type: str = "MKT",
        product: str = "INTRADAY",
        validity: str = "DAY",
    ) -> Dict[str, Any]:
        """Place an order with the broker."""
        pass

    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Modify an existing order."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get all orders from the broker."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions from the broker."""
        pass

    @abstractmethod
    def get_funds(self) -> Dict[str, Any]:
        """Get account funds/margin information."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check broker connection health."""
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific order."""
        pass

    def normalize_symbol(self, symbol: str, exchange: str) -> str:
        """Convert internal symbol format to broker-specific format."""
        # Default implementation - can be overridden by specific brokers
        return symbol

    def normalize_order_type(self, order_type: str) -> str:
        """Convert internal order type to broker-specific format."""
        # Default implementation - can be overridden by specific brokers
        return order_type

    def normalize_product(self, product: str) -> str:
        """Convert internal product type to broker-specific format."""
        # Default implementation - can be overridden by specific brokers
        return product