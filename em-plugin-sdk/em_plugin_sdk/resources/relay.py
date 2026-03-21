"""Relay chains resource — client.relay.create(), .get(), .assign_leg(), .handoff()."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import EMClient


class RelayResource:
    """Multi-worker relay chain operations.

    Relay chains split a task across multiple workers (legs), each responsible
    for a segment of a delivery or multi-step process.

    Usage::

        chain = await client.relay.create(parent_task_id="...", legs=3)
        status = await client.relay.get("chain-uuid")
        await client.relay.assign_leg("chain-uuid", leg_number=1, executor_id="exec-1")
        await client.relay.handoff("chain-uuid", leg_number=1)
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    async def create(
        self,
        parent_task_id: str,
        *,
        legs: int = 2,
        weights: list[float] | None = None,
    ) -> dict[str, Any]:
        """Create a relay chain from a parent task."""
        body: dict[str, Any] = {"parent_task_id": parent_task_id, "legs": legs}
        if weights:
            body["weights"] = weights
        return await self._client._request("POST", "/relay-chains", json=body)

    async def get(self, chain_id: str) -> dict[str, Any]:
        """Get relay chain status with all legs."""
        return await self._client._request("GET", f"/relay-chains/{chain_id}")

    async def assign_leg(
        self,
        chain_id: str,
        leg_number: int,
        executor_id: str,
    ) -> dict[str, Any]:
        """Assign a worker to a relay leg."""
        return await self._client._request(
            "POST", f"/relay-chains/{chain_id}/legs/{leg_number}/assign",
            json={"executor_id": executor_id},
        )

    async def handoff(
        self,
        chain_id: str,
        leg_number: int,
        *,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Record a handoff between relay workers."""
        body: dict[str, Any] = {}
        if notes:
            body["notes"] = notes
        return await self._client._request(
            "POST", f"/relay-chains/{chain_id}/legs/{leg_number}/handoff",
            json=body,
        )
