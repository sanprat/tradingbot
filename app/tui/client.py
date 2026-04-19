"""TUI HTTP Client."""

import httpx


class TradingBotClient:
    def __init__(self, base_url: str = "http://localhost:8002"):
        self.base_url = base_url
        self._client = httpx.AsyncClient(base_url=base_url)

    async def health_check(self) -> bool:
        response = await self._client.get("/health")
        return response.status_code == 200

    async def get_status(self) -> dict:
        response = await self._client.get("/api/status")
        return response.json()

    async def get_positions(self, status: str = None) -> dict:
        params = {}
        if status:
            params["status"] = status
        response = await self._client.get("/api/positions", params=params)
        return response.json()

    async def get_orders(self, status: str = None, limit: int = 50) -> dict:
        params = {"limit": limit}
        if status:
            params["status"] = status
        response = await self._client.get("/api/orders", params=params)
        return response.json()

    async def get_signals(self, limit: int = 50) -> dict:
        response = await self._client.get("/api/signals", params={"limit": limit})
        return response.json()

    async def toggle_kill_switch(self, enabled: bool) -> dict:
        response = await self._client.post(
            "/api/kill-switch", json={"enabled": enabled}
        )
        return response.json()

    async def send_order(self, payload: dict) -> dict:
        response = await self._client.post("/api/orders", json=payload)
        return response.json()

    async def get_broker_config(self, broker: str) -> dict:
        response = await self._client.get(f"/api/brokers/{broker}/config")
        return response.json()

    async def save_broker_credentials(self, broker: str, credentials: dict) -> dict:
        response = await self._client.post(
            f"/api/brokers/{broker}/credentials", json=credentials
        )
        return response.json()

    async def test_broker_connection(self, broker: str) -> dict:
        response = await self._client.post(f"/api/brokers/{broker}/test")
        return response.json()

    async def clear_broker_credentials(self, broker: str) -> dict:
        response = await self._client.delete(f"/api/brokers/{broker}/credentials")
        return response.json()

    async def update_webhook_secret(self, new_secret: str) -> dict:
        response = await self._client.post(
            "/api/webhook/secret", json={"secret": new_secret}
        )
        return response.json()

    async def close(self):
        await self._client.aclose()