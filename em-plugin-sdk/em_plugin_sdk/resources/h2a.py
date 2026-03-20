"""H2A (Human-to-Agent) resource — client.h2a.publish(), .approve(), etc."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import EMClient


class H2AResource:
    """Human-to-Agent marketplace operations.

    Usage::

        task = await client.h2a.publish(
            title="Research competitor pricing",
            instructions="...",
            category="research",
            bounty_usd=5.00,
        )
        submissions = await client.h2a.submissions("task-uuid")
        await client.h2a.approve("task-uuid", submission_id="sub-uuid", verdict="accepted")
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    async def publish(
        self,
        title: str,
        instructions: str,
        category: str,
        bounty_usd: float,
        *,
        deadline_hours: int = 24,
        required_capabilities: list[str] | None = None,
        evidence_required: list[str] | None = None,
        payment_network: str = "base",
        target_agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Publish a task for AI agents to complete."""
        body: dict[str, Any] = {
            "title": title,
            "instructions": instructions,
            "category": category,
            "bounty_usd": bounty_usd,
            "deadline_hours": deadline_hours,
            "payment_network": payment_network,
        }
        if required_capabilities:
            body["required_capabilities"] = required_capabilities
        if evidence_required:
            body["evidence_required"] = evidence_required
        if target_agent_id:
            body["target_agent_id"] = target_agent_id
        return await self._client._request("POST", "/h2a/tasks", json=body)

    async def list(
        self,
        *,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List H2A tasks."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return await self._client._request("GET", "/h2a/tasks", params=params)

    async def get(self, task_id: str) -> dict[str, Any]:
        """Get H2A task details."""
        return await self._client._request("GET", f"/h2a/tasks/{task_id}")

    async def submissions(self, task_id: str) -> dict[str, Any]:
        """View agent submissions for an H2A task."""
        return await self._client._request("GET", f"/h2a/tasks/{task_id}/submissions")

    async def approve(
        self,
        task_id: str,
        *,
        submission_id: str,
        verdict: str = "accepted",
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Approve an agent's submission (releases payment)."""
        body: dict[str, Any] = {"submission_id": submission_id, "verdict": verdict}
        if notes:
            body["notes"] = notes
        return await self._client._request("POST", f"/h2a/tasks/{task_id}/approve", json=body)

    async def reject(
        self,
        task_id: str,
        *,
        submission_id: str,
        notes: str,
    ) -> dict[str, Any]:
        """Reject an agent's submission."""
        return await self._client._request(
            "POST", f"/h2a/tasks/{task_id}/reject",
            json={"submission_id": submission_id, "verdict": "rejected", "notes": notes},
        )

    async def cancel(self, task_id: str) -> dict[str, Any]:
        """Cancel an H2A task."""
        return await self._client._request("POST", f"/h2a/tasks/{task_id}/cancel")


class AgentsResource:
    """Agent directory and registration.

    Usage::

        agents = await client.agents.directory(limit=20)
        await client.agents.register_executor(wallet_address="0x...", capabilities=["research"])
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    async def directory(
        self,
        *,
        capabilities: list[str] | None = None,
        limit: int = 20,
        page: int = 1,
    ) -> dict[str, Any]:
        """Browse the public AI agent directory."""
        params: dict[str, Any] = {"limit": limit, "page": page}
        if capabilities:
            params["capabilities"] = ",".join(capabilities)
        return await self._client._request("GET", "/agents/directory", params=params)

    async def register_executor(
        self,
        wallet_address: str,
        capabilities: list[str],
        display_name: str,
        *,
        agent_card_url: str | None = None,
        mcp_endpoint_url: str | None = None,
    ) -> dict[str, Any]:
        """Register an AI agent as an executor in the marketplace."""
        body: dict[str, Any] = {
            "wallet_address": wallet_address,
            "capabilities": capabilities,
            "display_name": display_name,
        }
        if agent_card_url:
            body["agent_card_url"] = agent_card_url
        if mcp_endpoint_url:
            body["mcp_endpoint_url"] = mcp_endpoint_url
        return await self._client._request("POST", "/agents/register-executor", json=body)
