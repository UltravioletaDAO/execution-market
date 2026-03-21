"""Swarm resource — client.swarm.status(), .dashboard(), .agents(), etc."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import EMClient


class SwarmResource:
    """Swarm coordination and monitoring (13 endpoints).

    Most read endpoints require an API key. Write endpoints (poll, config,
    activate, suspend, budget) require admin auth.

    Usage::

        status = await client.swarm.status()
        dashboard = await client.swarm.dashboard()
        agents = await client.swarm.agents()
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    # -- read ---------------------------------------------------------------

    async def status(self) -> dict[str, Any]:
        """Fleet overview — agent count, task queue, metrics."""
        return await self._client._request("GET", "/swarm/status")

    async def health(self) -> dict[str, Any]:
        """Subsystem health checks."""
        return await self._client._request("GET", "/swarm/health")

    async def agents(self) -> dict[str, Any]:
        """List all registered swarm agents."""
        return await self._client._request("GET", "/swarm/agents")

    async def agent(self, agent_id: str) -> dict[str, Any]:
        """Get details for a single swarm agent."""
        return await self._client._request("GET", f"/swarm/agents/{agent_id}")

    async def dashboard(self) -> dict[str, Any]:
        """Full operational dashboard."""
        return await self._client._request("GET", "/swarm/dashboard")

    async def metrics(self) -> dict[str, Any]:
        """Numeric metrics for monitoring/alerting."""
        return await self._client._request("GET", "/swarm/metrics")

    async def events(self, *, limit: int = 50) -> dict[str, Any]:
        """Recent coordinator events."""
        return await self._client._request("GET", "/swarm/events", params={"limit": limit})

    async def tasks(self) -> dict[str, Any]:
        """Swarm task queue status."""
        return await self._client._request("GET", "/swarm/tasks")

    # -- write (admin) ------------------------------------------------------

    async def poll(self) -> dict[str, Any]:
        """Trigger a poll cycle (ingest + route). Requires admin auth."""
        return await self._client._request("POST", "/swarm/poll")

    async def update_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Update swarm configuration. Requires admin auth."""
        return await self._client._request("POST", "/swarm/config", json=config)

    async def activate_agent(self, agent_id: str) -> dict[str, Any]:
        """Activate a swarm agent. Requires admin auth."""
        return await self._client._request("POST", f"/swarm/agents/{agent_id}/activate")

    async def suspend_agent(self, agent_id: str) -> dict[str, Any]:
        """Suspend a swarm agent. Requires admin auth."""
        return await self._client._request("POST", f"/swarm/agents/{agent_id}/suspend")

    async def update_budget(self, agent_id: str, budget: dict[str, Any]) -> dict[str, Any]:
        """Update an agent's budget. Requires admin auth."""
        return await self._client._request(
            "POST", f"/swarm/agents/{agent_id}/budget", json=budget,
        )
