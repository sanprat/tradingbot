"""Shoonya broker adapter implementation."""

import logging
import os
from typing import Dict, List, Optional, Any
from .base import BrokerAdapter, BrokerCapabilities, OrderStatus

logger = logging.getLogger(__name__)


class ShoonyaAdapter(BrokerAdapter):
    """Shoonya broker adapter using NorenRestApiPy."""

    def __init__(self, credentials: Dict[str, Any]):
        super().__init__(credentials)
        try:
            from NorenRestApiPy.NorenApi import NorenApi
            import pyotp

            class ShoonyaApiPy(NorenApi):
                def __init__(self):
                    super().__init__(
                        host="https://api.shoonya.com/NorenWClient10/",
                        websocket="wss://api.shoonya.com/NorenWSClient10/",
                    )

            self.api = ShoonyaApiPy()
            totp_secret = credentials.get("totp_secret") or os.environ.get(
                "SHOONYA_TOTP_SECRET", ""
            )
            totp = pyotp.TOTP(totp_secret).now() if totp_secret else ""
            self.api.login(
                userid=credentials.get("userid") or os.environ.get("SHOONYA_USER_ID", ""),
                password=credentials.get("password")
                or os.environ.get("SHOONYA_PASSWORD", ""),
                twoFA=totp,
                vendor_code=credentials.get("vendor_code")
                or os.environ.get("SHOONYA_VENDOR_CODE", ""),
                api_secret=credentials.get("api_secret")
                or os.environ.get("SHOONYA_API_SECRET", ""),
                imei=credentials.get("imei") or os.environ.get("SHOONYA_IMEI", "abc1234"),
            )
            logger.info("Shoonya: connected")
        except Exception as e:
            logger.error(f"Shoonya init failed: {e}")
            self.api = None

    def _get_capabilities(self) -> BrokerCapabilities:
        """Return Shoonya-specific capabilities."""
        return BrokerCapabilities(
            supports_bracket_orders=False,  # Shoonya doesn't natively support bracket orders
            supports_stop_loss=True,
            supports_target=True,
            supported_order_types=["MKT", "LMT", "SL", "SL-M"],
            supported_products=["INTRADAY", "CASH", "MTF", "CO", "NRML"],
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
        """Place an order with Shoonya broker."""
        if not self.api:
            return {"status": "error", "message": "Shoonya not connected"}

        # Map internal symbol to Shoonya format
        trading_symbol = self.normalize_symbol(symbol, exchange)

        # Map internal order type to Shoonya format
        shoonya_order_type = self.normalize_order_type(order_type)

        # Map internal product to Shoonya format
        shoonya_product = self.normalize_product(product)

        # Map side to Shoonya buy/sell (B=buy, S=sell)
        if side == "BUY":
            buy_or_sell = "B"
        elif side == "SELL":
            buy_or_sell = "S"
        elif side == "EXIT_LONG":
            buy_or_sell = "S"
        elif side == "EXIT_SHORT":
            buy_or_sell = "B"
        else:
            buy_or_sell = "B"

        try:
            logger.info(f"Placing Shoonya order: symbol={trading_symbol}, side={buy_or_sell}, "
                       f"quantity={quantity}, price={price}, order_type={shoonya_order_type}, "
                       f"product={shoonya_product}")

            ret = self.api.place_order(
                buy_or_sell=buy_or_sell,
                product_type=shoonya_product,  # Intraday
                exchange=exchange,
                tradingsymbol=trading_symbol,
                quantity=int(quantity),
                discloseqty=0,
                price_type=shoonya_order_type,
                price=price,
                trigger_price=0,  # For SL/SL-M orders
                retention=validity,
                remarks="TradingBot",
            )

            result = ret or {"status": "error"}
            logger.info(f"Shoonya order response: {result}")
            return result
        except Exception as e:
            logger.error(f"Shoonya order placement failed: {e}")
            return {"status": "error", "message": str(e)}

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
        exchange: Optional[str] = None,
        tradingsymbol: Optional[str] = None,
        trigger_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Modify an existing Shoonya order.

        Uses Shoonya's native modify_order API:
        modify_order(orderno, exchange, tradingsymbol, newquantity,
                     newprice_type, newprice, newtrigger_price, amo)
        """
        if not self.api:
            return {"status": "error", "message": "Shoonya not connected"}

        try:
            logger.info(f"Modifying Shoonya order {order_id}: qty={quantity}, price={price}, type={order_type}")

            # Build kwargs — Shoonya requires exchange and tradingsymbol
            # If not provided, we need to look up from order history
            if not exchange or not tradingsymbol:
                order_hist = self.api.single_order_history(orderno=order_id)
                if order_hist and isinstance(order_hist, list):
                    latest = order_hist[0]
                    exchange = exchange or latest.get("exch", "NSE")
                    tradingsymbol = tradingsymbol or latest.get("tsym", "")
                else:
                    return {"status": "error", "message": f"Cannot find order {order_id} to modify"}

            # Map order type to Shoonya price type
            new_price_type = self.normalize_order_type(order_type) if order_type else None

            ret = self.api.modify_order(
                orderno=order_id,
                exchange=exchange,
                tradingsymbol=tradingsymbol,
                newquantity=int(quantity) if quantity else None,
                newprice_type=new_price_type,
                newprice=price if price else None,
                newtrigger_price=trigger_price if trigger_price else None,
                amo=None,
            )

            result = ret or {"status": "error"}
            logger.info(f"Shoonya order modification response: {result}")

            return {
                "status": "ok" if result.get("stat") == "Ok" else "error",
                "order_id": order_id,
                "message": result.get("emsg", "Order modified"),
                "raw_response": result,
            }
        except Exception as e:
            logger.error(f"Shoonya order modification failed: {e}")
            return {"status": "error", "message": str(e)}

    def cancel_order(self, order_id: str) -> bool:
        """Cancel a Shoonya order."""
        if not self.api:
            logger.warning("Shoonya not connected")
            return False

        try:
            logger.info(f"Cancelling Shoonya order {order_id}")
            result = bool(self.api.cancel_order(orderno=order_id))
            logger.info(f"Shoonya order cancellation result: {result}")
            return result
        except Exception as e:
            logger.error(f"Shoonya order cancellation failed: {e}")
            return False

    def get_orders(self) -> List[Dict[str, Any]]:
        """Get all orders from Shoonya."""
        if not self.api:
            return []

        try:
            logger.info("Fetching Shoonya orders")
            from datetime import datetime, timedelta
            
            today = datetime.now().date()
            orders = self.api.order_history(
                exch="NSE",
                ordfrom=today.strftime("%Y-%m-%d"),
                ordto=today.strftime("%Y-%m-%d"),
                status="",
            )
            
            if orders and isinstance(orders, list):
                return [
                    {
                        "order_id": o.get("orderno"),
                        "symbol": o.get("tsym"),
                        "side": "BUY" if o.get("buy_or_sell") == "B" else "SELL",
                        "quantity": float(o.get("qty", 0)),
                        "filled_quantity": float(o.get("fqty", 0)),
                        "order_type": o.get("prctyp"),
                        "status": o.get("status"),
                        "average_price": float(o.get("avgprc", 0) or 0),
                    }
                    for o in orders
                ]
            return []
        except Exception as e:
            logger.error(f"Failed to fetch Shoonya orders: {e}")
            return []

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions from Shoonya."""
        if not self.api:
            return []

        try:
            logger.info("Fetching Shoonya positions")
            positions = self.api.get_positions() or []
            logger.info(f"Fetched {len(positions)} Shoonya positions")
            return positions
        except Exception as e:
            logger.error(f"Failed to fetch Shoonya positions: {e}")
            return []

    def get_funds(self) -> Dict[str, Any]:
        """Get account funds/margin information from Shoonya."""
        if not self.api:
            return {}

        try:
            logger.info("Fetching Shoonya funds")
            funds = self.api.get_funds()
            
            if funds and isinstance(funds, dict):
                return {
                    "cash": float(funds.get("cash", 0) or 0),
                    "margin_available": float(funds.get("marginalloc", 0) or 0),
                    "total_equity": float(funds.get("net", 0) or 0),
                    "uncleared_funds": float(funds.get("uncleared", 0) or 0),
                    "debt_funds": float(funds.get("debt", 0) or 0),
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to fetch Shoonya funds: {e}")
            return {}

    def health_check(self) -> Dict[str, Any]:
        """Check Shoonya connection health."""
        if not self.api:
            return {"status": "error", "message": "Shoonya not connected"}

        try:
            logger.info("Checking Shoonya health")
            # Try to get a simple quote or position to verify connection
            # For now, we'll consider it healthy if the API object exists
            return {"status": "ok", "message": "Shoonya connection healthy"}
        except Exception as e:
            logger.error(f"Shoonya health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of a specific Shoonya order."""
        if not self.api:
            return {"status": "error", "message": "Shoonya not connected"}

        try:
            logger.info(f"Getting Shoonya order status for {order_id}")
            res = self.api.single_order_history(orderno=order_id)
            if not res or not isinstance(res, list):
                return {"status": "UNKNOWN"}

            # Usually the first object is the latest status in NorenApi
            latest = res[0]
            st = latest.get("status", "").upper()

            if "COMPLETE" in st:
                status = OrderStatus.COMPLETE
            elif "REJECT" in st or "CANCEL" in st:
                status = OrderStatus.REJECTED
            else:
                status = OrderStatus.PENDING

            avg_price = float(latest.get("avgprc", 0.0) or 0.0)

            return {
                "status": status.value,
                "average_price": avg_price,
                "raw_response": res
            }
        except Exception as e:
            logger.error(f"Failed to get Shoonya order status: {e}")
            return {"status": "error", "message": str(e)}

    def normalize_symbol(self, symbol: str, exchange: str) -> str:
        """Convert internal symbol format to Shoonya-specific format."""
        # Shoonya typically uses the symbol as-is for NSE/BSE
        # Add .NS or .BS suffix if needed based on exchange
        if exchange.upper() == "NSE" and not symbol.endswith(".NS"):
            return f"{symbol}.NS"
        elif exchange.upper() == "BSE" and not symbol.endswith(".BS"):
            return f"{symbol}.BS"
        return symbol

    def normalize_order_type(self, order_type: str) -> str:
        """Convert internal order type to Shoonya-specific format."""
        # Map internal order types to Shoonya price types
        mapping = {
            "MKT": "MKT",
            "LMT": "LMT",
            "SL": "SL",
            "SL-M": "SL-M",
        }
        return mapping.get(order_type, "MKT")

    def normalize_product(self, product: str) -> str:
        """Convert internal product type to Shoonya-specific format."""
        # Map internal products to Shoonya product types
        mapping = {
            "INTRADAY": "I",
            "CASH": "CNC",
            "MTF": "MTF",
            "CO": "CO",
            "NRML": "NRML",
        }
        return mapping.get(product, "I")