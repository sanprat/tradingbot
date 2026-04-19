"""Dhan broker adapter implementation."""

import requests
import logging
from typing import Dict, List, Optional, Any
from .base import BrokerAdapter, BrokerCapabilities, OrderStatus

logger = logging.getLogger(__name__)


class DhanAdapter(BrokerAdapter):
    """Dhan broker adapter."""

    BASE_URL = "https://api.dhan.co"

    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        self.client_id = credentials.get("client_id") or ""
        self.access_token = credentials.get("access_token") or ""
        self.headers = {
            "Content-Type": "application/json",
            "access-token": self.access_token,
            "client-id": self.client_id,
        }

    def _get_capabilities(self) -> BrokerCapabilities:
        """Return Dhan-specific capabilities."""
        return BrokerCapabilities(
            supports_bracket_orders=False,  # Dhan doesn't natively support bracket orders
            supports_stop_loss=True,
            supports_target=True,
            supported_order_types=["MKT", "LMT", "SL", "SL-M"],
            supported_products=["INTRADAY", "CASH", "MTF", "CO"],
        )

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
        """Place an order with Dhan broker."""
        if not self.client_id or not self.access_token:
            return {"status": "error", "message": "Dhan credentials not configured"}

        # Map internal symbols to Dhan format
        trading_symbol = self.normalize_symbol(symbol, exchange)

        # Map internal order type to Dhan format
        dhan_order_type = self.normalize_order_type(order_type)

        # Map internal product to Dhan format
        dhan_product = self.normalize_product(product)

        # Map side to Dhan transaction type
        # BUY = open long, SELL = close long
        # EXIT_LONG = close existing long position → SELL
        # EXIT_SHORT = close existing short position → BUY
        if side == "BUY":
            transaction_type = "BUY"
        elif side == "SELL":
            transaction_type = "SELL"
        elif side == "EXIT_LONG":
            transaction_type = "SELL"
        elif side == "EXIT_SHORT":
            transaction_type = "BUY"
        else:
            transaction_type = "BUY"

        payload = {
            "dhanClientId": self.client_id,
            "transactionType": transaction_type,
            "exchangeSegment": exchange,
            "productType": dhan_product,
            "orderType": dhan_order_type,
            "validity": validity,
            "tradingSymbol": trading_symbol,
            "quantity": int(quantity),
            "price": price,
            "triggerPrice": 0,
            "afterMarketOrder": False,
        }

        try:
            logger.info(f"Placing Dhan order: {payload}")
            response = requests.post(
                f"{self.BASE_URL}/orders",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Dhan order response: {result}")
            return {
                "status": "ok" if result.get("status") == "success" else "error",
                "order_id": result.get("data", {}).get("orderId"),
                "message": result.get("remarks", "Order placed"),
                "raw_response": result
            }
        except Exception as e:
            logger.error(f"Dhan order placement failed: {e}")
            return {"status": "error", "message": str(e)}

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Modify an existing Dhan order."""
        if not self.client_id or not self.access_token:
            return {"status": "error", "message": "Dhan credentials not configured"}

        # Build payload for modification
        payload = {
            "dhanClientId": self.client_id,
            "orderId": order_id,
        }

        if quantity is not None:
            payload["quantity"] = int(quantity)
        if price is not None:
            payload["price"] = price
        if order_type is not None:
            payload["orderType"] = self.normalize_order_type(order_type)

        try:
            logger.info(f"Modifying Dhan order {order_id}: {payload}")
            response = requests.put(
                f"{self.BASE_URL}/orders/{order_id}",
                json=payload,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Dhan order modification response: {result}")
            return {
                "status": "ok" if result.get("status") == "success" else "error",
                "message": result.get("remarks", "Order modified"),
                "raw_response": result
            }
        except Exception as e:
            logger.error(f"Dhan order modification failed: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a Dhan order."""
        if not self.client_id or not self.access_token:
            logger.warning("Dhan credentials not configured")
            return False

        try:
            logger.info(f"Cancelling Dhan order {order_id}")
            response = requests.delete(
                f"{self.BASE_URL}/orders/{order_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Dhan order cancellation response: {result}")
            return result.get("status") == "success"
        except Exception as e:
            logger.error(f"Dhan order cancellation failed: {e}")
            return False

    def get_orders(self) -> List[Dict[str, Any]]:
        """Get all orders from Dhan."""
        if not self.client_id or not self.access_token:
            return []

        try:
            logger.info("Fetching Dhan orders")
            response = requests.get(
                f"{self.BASE_URL}/orders",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Dhan orders response: {result}")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch Dhan orders: {e}")
            return []

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions from Dhan."""
        if not self.client_id or not self.access_token:
            return []

        try:
            logger.info("Fetching Dhan positions")
            response = requests.get(
                f"{self.BASE_URL}/positions",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Dhan positions response: {result}")
            return result.get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch Dhan positions: {e}")
            return []

    def get_funds(self) -> Dict[str, Any]:
        """Get account funds/margin information from Dhan."""
        if not self.client_id or not self.access_token:
            return {}

        try:
            logger.info("Fetching Dhan funds")
            response = requests.get(
                f"{self.BASE_URL}/fundlimit",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Dhan funds response: {result}")
            return result.get("data", {})
        except Exception as e:
            logger.error(f"Failed to fetch Dhan funds: {e}")
            return {}

    def health_check(self) -> Dict[str, Any]:
        """Check Dhan connection health."""
        if not self.client_id or not self.access_token:
            return {"status": "error", "message": "Dhan credentials not configured"}

        try:
            logger.info("Checking Dhan health")
            # Use a lightweight endpoint for health check
            response = requests.get(
                f"{self.BASE_URL}/fundlimit",
                headers=self.headers,
                timeout=5
            )
            response.raise_for_status()
            return {"status": "ok", "message": "Dhan connection healthy"}
        except Exception as e:
            logger.error(f"Dhan health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific Dhan order."""
        if not self.client_id or not self.access_token:
            return {"status": "error", "message": "Dhan credentials not configured"}

        try:
            logger.info(f"Getting Dhan order status for {order_id}")
            response = requests.get(
                f"{self.BASE_URL}/orders/{order_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()

            order_data = result.get("data", {})
            dhan_status = order_data.get("orderStatus", "").upper()

            # Map Dhan status to internal status
            if "TRADED" in dhan_status or "COMPLETE" in dhan_status:
                status = OrderStatus.COMPLETE
            elif "REJECT" in dhan_status or "CANCEL" in dhan_status:
                status = OrderStatus.REJECTED
            else:
                status = OrderStatus.PENDING

            return {
                "status": status.value,
                "average_price": float(order_data.get("averagePrice", 0.0) or 0.0),
                "filled_quantity": float(order_data.get("filledQuantity", 0.0) or 0.0),
                "raw_response": result
            }
        except Exception as e:
            logger.error(f"Failed to get Dhan order status: {e}")
            return {"status": "error", "message": str(e)}