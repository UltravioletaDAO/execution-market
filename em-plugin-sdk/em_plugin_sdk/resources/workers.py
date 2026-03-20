"""Workers resource — client.workers.register(), .earnings(), etc."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..models import Executor

if TYPE_CHECKING:
    from ..client import EMClient


class WorkersResource:
    """Operations on workers / executors.

    Usage::

        worker = await client.workers.register(wallet_address="0x...")
        info = await client.workers.get("executor-uuid")
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    async def get(self, executor_id: str) -> Executor:
        """Get worker profile by executor ID."""
        data = await self._client._request("GET", f"/workers/{executor_id}")
        return Executor.model_validate(data)

    async def register(
        self,
        wallet_address: str,
        name: str | None = None,
        email: str | None = None,
    ) -> Executor:
        """Register a new worker by wallet address."""
        body: dict[str, Any] = {"wallet_address": wallet_address}
        if name:
            body["name"] = name
        if email:
            body["email"] = email
        data = await self._client._request("POST", "/workers/register", json=body)
        return Executor.model_validate(data)

    async def balance(self, wallet_address: str) -> dict[str, Any]:
        """Get USDC balances across all chains for a wallet."""
        return await self._client._request("GET", f"/payments/balance/{wallet_address}")

    async def payment_events(
        self,
        wallet_address: str,
        *,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get payment events (earnings history) for a wallet."""
        return await self._client._request(
            "GET", "/payments/events",
            params={"wallet_address": wallet_address, "limit": limit},
        )
