"""
Tests for Swarm MCP Tools.

Verifies that the MCP tool functions work correctly
with and without an active coordinator.
"""

import pytest
from unittest.mock import MagicMock, patch

# Poll response format stabilized — all tests passing.


# ─── Helper to register tools and capture them ───────────────────────────────


class MockMCP:
    """Minimal mock that captures tool registrations."""

    def __init__(self):
        self._tools = {}

    def tool(self):
        """Decorator that captures the async function."""

        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn

        return decorator

    def get_tool(self, name):
        return self._tools.get(name)


async def _run(coro):
    """Helper to run a coroutine."""
    return await coro


# ─── Tests with coordinator disabled ──────────────────────────────────────────


class TestSwarmMCPToolsDisabled:
    """All tools should return graceful disabled responses when coordinator is None."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from swarm.mcp_tools import register_swarm_tools

        self.mcp = MockMCP()
        register_swarm_tools(self.mcp, coordinator=None)

    @pytest.mark.asyncio
    async def test_status_disabled(self):
        tool = self.mcp.get_tool("em_swarm_status")
        result = await tool()
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_dashboard_disabled(self):
        tool = self.mcp.get_tool("em_swarm_dashboard")
        result = await tool()
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_poll_disabled(self):
        tool = self.mcp.get_tool("em_swarm_poll")
        result = await tool()
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_agent_info_disabled(self):
        tool = self.mcp.get_tool("em_swarm_agent_info")
        result = await tool("agent_1")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_disabled(self):
        tool = self.mcp.get_tool("em_swarm_health")
        result = await tool()
        assert result["status"] == "disabled"

    def test_all_five_tools_registered(self):
        expected = [
            "em_swarm_status",
            "em_swarm_dashboard",
            "em_swarm_poll",
            "em_swarm_agent_info",
            "em_swarm_health",
        ]
        for name in expected:
            assert self.mcp.get_tool(name) is not None, f"Missing tool: {name}"


# ─── Tests with active coordinator ────────────────────────────────────────────


class TestSwarmMCPToolsActive:
    """Tools with an active coordinator should return real data."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from swarm.mcp_tools import register_swarm_tools

        self.mock_coord = MagicMock()
        self.mcp = MockMCP()

        with patch.dict(
            "os.environ", {"SWARM_ENABLED": "true", "SWARM_MODE": "semi-auto"}
        ):
            register_swarm_tools(self.mcp, coordinator=self.mock_coord)

    @pytest.mark.asyncio
    async def test_status_returns_metrics(self):
        self.mock_coord.get_dashboard.return_value = {
            "agents": {"registered": 24, "active": 18},
            "tasks": {"ingested": 100, "completed": 75},
            "performance": {"success_rate": 0.92},
        }
        mock_metrics = MagicMock()
        mock_metrics.bounty_earned = 25.50
        mock_metrics.success_rate = 0.92
        self.mock_coord.get_metrics.return_value = mock_metrics

        tool = self.mcp.get_tool("em_swarm_status")
        result = await tool()

        assert result["enabled"] is True
        assert result["agents"]["registered"] == 24
        assert result["bounty_earned_usd"] == 25.50

    @pytest.mark.asyncio
    async def test_dashboard_returns_full_data(self):
        self.mock_coord.get_dashboard.return_value = {
            "agents": {"registered": 24, "active": 18},
            "tasks": {"ingested": 50},
            "fleet": [{"agent_id": "a1", "state": "IDLE"}],
        }

        tool = self.mcp.get_tool("em_swarm_dashboard")
        result = await tool()

        assert "config" in result
        assert "timestamp" in result
        assert result["fleet"][0]["agent_id"] == "a1"

    @pytest.mark.asyncio
    async def test_poll_ingests_and_routes(self):
        self.mock_coord.ingest_from_api.return_value = 3
        assignment = MagicMock()
        assignment.agent_id = "agent_1"
        self.mock_coord.process_task_queue.return_value = [assignment]
        self.mock_coord.run_health_checks.return_value = {
            "agents": {"degraded": 0},
            "systems": {},
        }

        tool = self.mcp.get_tool("em_swarm_poll")
        result = await tool()

        assert result["new_tasks"] == 3
        assert result["tasks_assigned"] == 1
        assert result["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_poll_passive_skips_routing(self):
        """In passive mode, poll returns early without ingesting or routing."""
        mcp = MockMCP()
        with patch.dict(
            "os.environ", {"SWARM_ENABLED": "true", "SWARM_MODE": "passive"}
        ):
            from swarm.mcp_tools import register_swarm_tools

            register_swarm_tools(mcp, coordinator=self.mock_coord)

        tool = mcp.get_tool("em_swarm_poll")
        result = await tool()

        assert result["mode"] == "passive"
        assert result["enabled"] is True
        assert "message" in result
        self.mock_coord.ingest_from_api.assert_not_called()
        self.mock_coord.process_task_queue.assert_not_called()

    @pytest.mark.asyncio
    async def test_agent_info_found(self):
        mock_record = MagicMock()
        mock_record.state.name = "IDLE"
        mock_record.skills = ["physical_presence", "data_collection"]
        mock_record.health.is_healthy = True
        mock_record.budget.daily_limit = 10.0
        mock_record.budget.monthly_limit = 200.0
        mock_record.daily_spent = 2.50
        mock_record.monthly_spent = 45.0
        self.mock_coord.lifecycle.get_agent.return_value = mock_record

        mock_score = MagicMock()
        mock_score.total = 0.85
        mock_score.tier.name = "ORO"
        self.mock_coord.reputation.compute.return_value = mock_score

        tool = self.mcp.get_tool("em_swarm_agent_info")
        result = await tool("agent_1")

        assert result["agent_id"] == "agent_1"
        assert result["state"] == "IDLE"
        assert len(result["skills"]) == 2
        assert result["composite_score"]["total"] == 0.85
        assert result["composite_score"]["tier"] == "ORO"

    @pytest.mark.asyncio
    async def test_agent_info_not_found(self):
        self.mock_coord.lifecycle.get_agent.return_value = None

        tool = self.mcp.get_tool("em_swarm_agent_info")
        result = await tool("nonexistent")

        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_health_all_green(self):
        self.mock_coord.run_health_checks.return_value = {
            "timestamp": "2026-03-12T04:00:00Z",
            "agents": {"checked": 24, "healthy": 24, "degraded": 0},
            "tasks": {"expired": 0, "stale": 0},
            "systems": {"em_api": "ok", "autojob": "available"},
        }

        tool = self.mcp.get_tool("em_swarm_health")
        result = await tool()

        assert result["status"] == "healthy"
        assert result["agents"]["healthy"] == 24

    @pytest.mark.asyncio
    async def test_health_degraded(self):
        self.mock_coord.run_health_checks.return_value = {
            "timestamp": "2026-03-12T04:00:00Z",
            "agents": {"checked": 24, "healthy": 20, "degraded": 4},
            "tasks": {"expired": 2},
            "systems": {"em_api": "ok", "autojob": "unreachable"},
        }

        tool = self.mcp.get_tool("em_swarm_health")
        result = await tool()

        assert result["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_status_handles_exception(self):
        self.mock_coord.get_dashboard.side_effect = Exception("DB error")

        tool = self.mcp.get_tool("em_swarm_status")
        result = await tool()

        assert result["enabled"] is True
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_handles_exception(self):
        self.mock_coord.run_health_checks.side_effect = Exception("Timeout")

        tool = self.mcp.get_tool("em_swarm_health")
        result = await tool()

        assert result["status"] == "error"
        assert "Timeout" in result["error"]
