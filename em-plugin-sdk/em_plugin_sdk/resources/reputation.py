"""Reputation resource — client.reputation.get_agent(), .rate_worker(), etc.

Wraps the ERC-8004 on-chain reputation and identity endpoints.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..models import AgentIdentity, AgentReputation

if TYPE_CHECKING:
    from ..client import EMClient


class ReputationResource:
    """ERC-8004 reputation and identity operations.

    Usage::

        rep = await client.reputation.get_agent(2106)
        identity = await client.reputation.get_agent_identity(2106)
        board = await client.reputation.leaderboard()
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    # -- read ---------------------------------------------------------------

    async def get_agent(self, agent_id: int, *, network: str = "base") -> AgentReputation:
        """Get reputation summary for an agent by ERC-8004 token ID."""
        data = await self._client._request(
            "GET", f"/reputation/agents/{agent_id}",
            params={"network": network},
        )
        return AgentReputation.model_validate(data)

    async def get_agent_identity(self, agent_id: int, *, network: str = "base") -> AgentIdentity:
        """Get on-chain identity for an agent."""
        data = await self._client._request(
            "GET", f"/reputation/agents/{agent_id}/identity",
            params={"network": network},
        )
        return AgentIdentity.model_validate(data)

    async def leaderboard(self, *, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """Get the worker reputation leaderboard."""
        return await self._client._request(
            "GET", "/reputation/leaderboard",
            params={"limit": limit, "offset": offset},
        )

    async def info(self) -> dict[str, Any]:
        """Get ERC-8004 integration status and configuration."""
        return await self._client._request("GET", "/reputation/info")

    async def networks(self) -> list[str]:
        """List supported ERC-8004 networks."""
        data = await self._client._request("GET", "/reputation/networks")
        return data.get("networks", []) if isinstance(data, dict) else data

    async def em_reputation(self) -> AgentReputation:
        """Get Execution Market's own on-chain reputation."""
        data = await self._client._request("GET", "/reputation/em")
        return AgentReputation.model_validate(data)

    async def em_identity(self) -> AgentIdentity:
        """Get Execution Market's on-chain identity."""
        data = await self._client._request("GET", "/reputation/em/identity")
        return AgentIdentity.model_validate(data)

    async def get_feedback(self, task_id: str) -> dict[str, Any]:
        """Get the off-chain feedback document for a task."""
        return await self._client._request("GET", f"/reputation/feedback/{task_id}")

    # -- write (require auth) -----------------------------------------------

    async def rate_worker(
        self,
        submission_id: str,
        score: int,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Agent rates a worker after task completion (on-chain via Facilitator)."""
        body: dict[str, Any] = {"submission_id": submission_id, "score": score}
        if comment:
            body["comment"] = comment
        return await self._client._request("POST", "/reputation/workers/rate", json=body)

    async def rate_agent(
        self,
        task_id: str,
        score: int,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Worker rates an agent after task completion (on-chain via Facilitator)."""
        body: dict[str, Any] = {"task_id": task_id, "score": score}
        if comment:
            body["comment"] = comment
        return await self._client._request("POST", "/reputation/agents/rate", json=body)

    async def register(self, wallet_address: str, *, network: str = "base") -> dict[str, Any]:
        """Register an agent on the ERC-8004 identity registry (gasless)."""
        return await self._client._request(
            "POST", "/reputation/register",
            json={"wallet_address": wallet_address, "network": network},
        )

    async def prepare_feedback(
        self,
        task_id: str,
        score: int,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        """Prepare on-chain feedback params for worker signing."""
        body: dict[str, Any] = {"task_id": task_id, "score": score}
        if comment:
            body["comment"] = comment
        return await self._client._request("POST", "/reputation/prepare-feedback", json=body)

    async def confirm_feedback(self, tx_hash: str) -> dict[str, Any]:
        """Confirm a worker-signed feedback transaction."""
        return await self._client._request(
            "POST", "/reputation/confirm-feedback",
            json={"tx_hash": tx_hash},
        )
