"""Paper trading broker adapter - simulated execution for testing."""

import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.brokers.base import BrokerAdapter, BrokerCapabilities, OrderStatus

logger = logging.getLogger(__name__)

_order_book: Dict[str, dict] = {}
_positions: Dict[str, dict] = {}


class PaperBroker(BrokerAdapter):
    """Paper trading broker with simulated execution."""

    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        self._rejection_rate = float(credentials.get("rejection_rate", 0.0))
        self._fake_fill_price = credentials.get("fake_fill_price", None)

    def _get_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_bracket_orders=True,
            supports_stop_loss=True,
            supports_target=True,
            supported_order_types=["MKT", "LMT", "SL", "SL-M"],
            supported_products=["INTRADAY", "CASH", "NRML"],
        )

    def normalize_symbol(self, symbol: str, exchange: str) -> str:
        return f"{symbol}:{exchange}"

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
        order_id = f"paper_{uuid.uuid4().hex[:12]}"

        if self._rejection_rate > 0 and (order_id[-1] in "01234567"):
            logger.info(f"Paper broker: simulating rejection for {symbol}")
            return {
                "status": "error",
                "message": "Simulated rejection for testing",
                "order_id": order_id,
            }

        trading_symbol = self.normalize_symbol(symbol, exchange)

        if order_type == "MKT":
            fill_price = self._fake_fill_price or price or 100.0
        else:
            fill_price = price or 100.0

        order_data = {
            "order_id": order_id,
            "symbol": trading_symbol,
            "side": side,
            "quantity": quantity,
            "filled_quantity": quantity,
            "average_price": fill_price,
            "status": "complete",
            "order_type": order_type,
            "product": product,
            "exchange": exchange,
            "timestamp": datetime.utcnow().isoformat(),
        }

        _order_book[order_id] = order_data

        if side in ("BUY", "EXIT_LONG"):
            position_key = f"{trading_symbol}_long"
            if position_key in _positions:
                _positions[position_key]["quantity"] += quantity
                _positions[position_key]["avg_price"] = fill_price
            else:
                _positions[position_key] = {
                    "symbol": trading_symbol,
                    "side": "long",
                    "quantity": quantity,
                    "avg_price": fill_price,
                }
        elif side in ("SELL", "EXIT_SHORT"):
            position_key = f"{trading_symbol}_short"
            if position_key in _positions:
                _positions[position_key]["quantity"] += quantity
                _positions[position_key]["avg_price"] = fill_price
            else:
                _positions[position_key] = {
                    "symbol": trading_symbol,
                    "side": "short",
                    "quantity": quantity,
                    "avg_price": fill_price,
                }

        logger.info(f"Paper broker: filled order {order_id} at {fill_price}")

        return {
            "status": "ok",
            "order_id": order_id,
            "average_price": fill_price,
            "filled_quantity": quantity,
            "raw_response": order_data,
        }

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        if order_id not in _order_book:
            return {"status": "error", "message": "Order not found"}

        order = _order_book[order_id]
        if quantity:
            order["quantity"] = quantity
        if price:
            order["average_price"] = price

        return {
            "status": "ok",
            "order_id": order_id,
            "message": "Order modified",
        }

    def cancel_order(self, order_id: str) -> bool:
        if order_id in _order_book:
            _order_book[order_id]["status"] = "cancelled"
            logger.info(f"Paper broker: cancelled order {order_id}")
            return True
        return False

    def get_orders(self) -> List[Dict[str, Any]]:
        return list(_order_book.values())

    def get_positions(self) -> List[Dict[str, Any]]:
        return list(_positions.values())

    def get_funds(self) -> Dict[str, Any]:
        return {
            "cash": 1000000.0,
            "margin_available": 1000000.0,
            "total_equity": 1000000.0,
        }

    def health_check(self) -> Dict[str, Any]:
        return {"status": "ok", "message": "Paper broker healthy"}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if order_id not in _order_book:
            return {"status": "error", "message": "Order not found"}

        order = _order_book[order_id]
        return {
            "status": order.get("status", "unknown"),
            "average_price": order.get("average_price"),
            "filled_quantity": order.get("filled_quantity"),
            "raw_response": order,
        }


def reset_order_book():
    """Reset order book (useful for testing)."""
    _order_book.clear()
    _positions.clear()