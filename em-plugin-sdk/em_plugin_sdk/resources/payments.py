"""Payments resource — client.payments.balance(), .events(), etc."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..models import PaymentTimeline

if TYPE_CHECKING:
    from ..client import EMClient


class PaymentsResource:
    """Payment queries — balances, events, task payment timelines.

    Usage::

        balances = await client.payments.balance("0xABC...")
        events = await client.payments.events("0xABC...")
        timeline = await client.payments.task_payment("task-uuid")
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    async def balance(self, wallet_address: str) -> dict[str, Any]:
        """Get USDC balances across all enabled chains for a wallet."""
        return await self._client._request("GET", f"/payments/balance/{wallet_address}")

    async def events(
        self,
        wallet_address: str,
        *,
        event_type: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get payment events (earnings, settlements, refunds) for a wallet."""
        params: dict[str, Any] = {"wallet_address": wallet_address, "limit": limit}
        if event_type:
            params["event_type"] = event_type
        return await self._client._request("GET", "/payments/events", params=params)

    async def task_payment(self, task_id: str) -> PaymentTimeline:
        """Get payment status and timeline for a specific task."""
        data = await self._client._request("GET", f"/tasks/{task_id}/payment")
        return PaymentTimeline.model_validate(data)

    async def task_transactions(self, task_id: str) -> dict[str, Any]:
        """Get the full transaction audit trail for a task."""
        return await self._client._request("GET", f"/tasks/{task_id}/transactions")
