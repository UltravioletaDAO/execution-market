"""
Tests for Swarm MCP Tools
===========================

Covers all 5 swarm MCP tools:
  - em_swarm_status
  - em_swarm_dashboard
  - em_swarm_poll
  - em_swarm_agent_info
  - em_swarm_health

Tests both the "swarm disabled" path (coordinator=None)
and the "swarm enabled" path (with mock coordinator).
"""

import asyncio
import os
import pytest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Minimal MCP mock — captures registered tools for testing
# ---------------------------------------------------------------------------

class MockMCP:
    """Minimal MCP mock that captures tools registered via @mcp.tool()."""

    def __init__(self):
        self.tools = {}

    def tool(self):
        """Decorator that captures the function."""
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


# ---------------------------------------------------------------------------
# Mock coordinator and its dependencies
# ---------------------------------------------------------------------------

@dataclass
class MockMetrics:
    bounty_earned: float = 42.50
    success_rate: float = 0.85


@dataclass
class MockHealth:
    is_healthy: bool = True


@dataclass
class MockBudget:
    daily_limit: float = 10.0
    monthly_limit: float = 100.0


@dataclass
class MockState:
    name: str = "ACTIVE"


@dataclass
class MockAgent:
    state: MockState = None
    skills: list = None
    health: MockHealth = None
    budget: MockBudget = None
    daily_spent: float = 2.5
    monthly_spent: float = 25.0

    def __post_init__(self):
        if self.state is None:
            self.state = MockState()
        if self.skills is None:
            self.skills = ["photography", "delivery"]
        if self.health is None:
            self.health = MockHealth()
        if self.budget is None:
            self.budget = MockBudget()


@dataclass
class MockScore:
    total: float = 0.87
    tier: MockState = None

    def __post_init__(self):
        if self.tier is None:
            self.tier = MockState(name="GOLD")


def make_coordinator(
    dashboard=None,
    metrics=None,
    agent=None,
    health=None,
    ingest_count=3,
    assignments=None,
):
    """Build a mock coordinator with configurable returns."""
    c = MagicMock()

    c.get_dashboard.return_value = dashboard or {
        "agents": {"total": 24, "active": 18, "degraded": 2},
        "tasks": {"ingested": 100, "assigned": 85, "completed": 70, "failed": 5},
        "performance": {"avg_routing_ms": 45, "success_rate": 0.87},
    }
    c.get_metrics.return_value = metrics or MockMetrics()
    c.ingest_from_api.return_value = ingest_count

    # Process task queue returns assignment-like objects
    if assignments is None:
        assignment = MagicMock()
        assignment.agent_id = "agent_1"
        assignments = [assignment]
    c.process_task_queue.return_value = assignments

    c.run_health_checks.return_value = health or {
        "agents": {"total": 24, "active": 18, "degraded": 0},
        "tasks": {"queued": 5, "stale": 0},
        "systems": {"em_api": "healthy", "autojob": "healthy"},
        "timestamp": "2026-03-26T05:00:00Z",
    }

    # Lifecycle manager for agent info
    lifecycle = MagicMock()
    lifecycle.get_agent.return_value = agent or MockAgent()
    c.lifecycle = lifecycle

    # Reputation bridge
    reputation = MagicMock()
    reputation.compute.return_value = MockScore()
    c.reputation = reputation

    return c


def _run(coro):
    """Run an async function synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Import and register
# ---------------------------------------------------------------------------

from swarm.mcp_tools import register_swarm_tools


# ===========================================================================
# SECTION 1: Disabled Swarm (coordinator=None)
# ===========================================================================

class TestDisabledSwarm:
    """All tools should return graceful 'not enabled' responses."""

    def setup_method(self):
        self.mcp = MockMCP()
        register_swarm_tools(self.mcp, coordinator=None)

    def test_status_disabled(self):
        result = _run(self.mcp.tools["em_swarm_status"]())
        assert result["enabled"] is False
        assert "not enabled" in result["message"].lower()

    def test_dashboard_disabled(self):
        result = _run(self.mcp.tools["em_swarm_dashboard"]())
        assert result["enabled"] is False

    def test_poll_disabled(self):
        result = _run(self.mcp.tools["em_swarm_poll"]())
        assert result["enabled"] is False

    def test_agent_info_disabled(self):
        result = _run(self.mcp.tools["em_swarm_agent_info"]("agent_123"))
        assert "error" in result
        assert "not enabled" in result["error"].lower()

    def test_health_disabled(self):
        result = _run(self.mcp.tools["em_swarm_health"]())
        assert result["status"] == "disabled"


# ===========================================================================
# SECTION 2: em_swarm_status
# ===========================================================================

class TestSwarmStatus:
    def setup_method(self):
        self.mcp = MockMCP()
        self.coordinator = make_coordinator()
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "semi-auto"}):
            register_swarm_tools(self.mcp, self.coordinator)

    def test_status_enabled(self):
        result = _run(self.mcp.tools["em_swarm_status"]())
        assert result["enabled"] is True
        assert "agents" in result
        assert "tasks" in result
        assert "timestamp" in result

    def test_status_includes_metrics(self):
        result = _run(self.mcp.tools["em_swarm_status"]())
        assert result["bounty_earned_usd"] == 42.50
        assert result["success_rate"] == 0.85

    def test_status_mode(self):
        result = _run(self.mcp.tools["em_swarm_status"]())
        assert result["mode"] == "semi-auto"

    def test_status_error_handling(self):
        self.coordinator.get_dashboard.side_effect = RuntimeError("DB down")
        result = _run(self.mcp.tools["em_swarm_status"]())
        assert result["enabled"] is True
        assert "error" in result
        assert "DB down" in result["error"]

    def test_status_missing_metrics_attrs(self):
        """Handles metrics objects without bounty_earned/success_rate."""
        self.coordinator.get_metrics.return_value = object()
        result = _run(self.mcp.tools["em_swarm_status"]())
        assert result["bounty_earned_usd"] == 0
        assert result["success_rate"] == 0


# ===========================================================================
# SECTION 3: em_swarm_dashboard
# ===========================================================================

class TestSwarmDashboard:
    def setup_method(self):
        self.mcp = MockMCP()
        self.coordinator = make_coordinator()
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "full-auto"}):
            register_swarm_tools(self.mcp, self.coordinator)

    def test_dashboard_returns_full_data(self):
        result = _run(self.mcp.tools["em_swarm_dashboard"]())
        assert "agents" in result
        assert "tasks" in result
        assert "config" in result
        assert "timestamp" in result

    def test_dashboard_config(self):
        result = _run(self.mcp.tools["em_swarm_dashboard"]())
        assert result["config"]["mode"] == "full-auto"
        assert result["config"]["enabled"] is True

    def test_dashboard_error_handling(self):
        self.coordinator.get_dashboard.side_effect = Exception("timeout")
        result = _run(self.mcp.tools["em_swarm_dashboard"]())
        assert "error" in result
        assert "timeout" in result["error"]


# ===========================================================================
# SECTION 4: em_swarm_poll
# ===========================================================================

class TestSwarmPoll:
    def test_poll_passive_mode(self):
        mcp = MockMCP()
        coordinator = make_coordinator()
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "passive"}):
            register_swarm_tools(mcp, coordinator)
        result = _run(mcp.tools["em_swarm_poll"]())
        assert result["mode"] == "passive"
        assert "passive" in result["message"].lower()
        # Should NOT call ingest or process
        coordinator.ingest_from_api.assert_not_called()

    def test_poll_semi_auto(self):
        mcp = MockMCP()
        coordinator = make_coordinator(ingest_count=5)
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "semi-auto"}):
            register_swarm_tools(mcp, coordinator)
        result = _run(mcp.tools["em_swarm_poll"]())
        assert result["mode"] == "semi-auto"
        assert result["new_tasks"] == 5
        assert result["tasks_assigned"] == 1
        assert "duration_ms" in result
        coordinator.ingest_from_api.assert_called_once()
        coordinator.process_task_queue.assert_called_once_with(max_tasks=10)

    def test_poll_full_auto(self):
        mcp = MockMCP()
        coordinator = make_coordinator(ingest_count=0)
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "full-auto"}):
            register_swarm_tools(mcp, coordinator)
        result = _run(mcp.tools["em_swarm_poll"]())
        assert result["new_tasks"] == 0
        assert result["tasks_assigned"] == 1

    def test_poll_ingest_error(self):
        mcp = MockMCP()
        coordinator = make_coordinator()
        coordinator.ingest_from_api.side_effect = RuntimeError("API unreachable")
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "semi-auto"}):
            register_swarm_tools(mcp, coordinator)
        result = _run(mcp.tools["em_swarm_poll"]())
        issues = result["health_issues"]
        assert any("ingest" in i for i in issues)

    def test_poll_routing_error(self):
        mcp = MockMCP()
        coordinator = make_coordinator()
        coordinator.process_task_queue.side_effect = RuntimeError("Routing failed")
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "semi-auto"}):
            register_swarm_tools(mcp, coordinator)
        result = _run(mcp.tools["em_swarm_poll"]())
        issues = result["health_issues"]
        assert any("routing" in i for i in issues)

    def test_poll_health_degraded_agents(self):
        mcp = MockMCP()
        coordinator = make_coordinator(health={
            "agents": {"total": 24, "active": 18, "degraded": 3},
            "tasks": {"queued": 2, "stale": 0},
            "systems": {},
        })
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "semi-auto"}):
            register_swarm_tools(mcp, coordinator)
        result = _run(mcp.tools["em_swarm_poll"]())
        issues = result["health_issues"]
        assert any("degraded_agents" in i for i in issues)

    def test_poll_health_check_error(self):
        mcp = MockMCP()
        coordinator = make_coordinator()
        coordinator.run_health_checks.side_effect = Exception("health boom")
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "semi-auto"}):
            register_swarm_tools(mcp, coordinator)
        result = _run(mcp.tools["em_swarm_poll"]())
        issues = result["health_issues"]
        assert any("health" in i for i in issues)

    def test_poll_no_assignments(self):
        mcp = MockMCP()
        coordinator = make_coordinator(assignments=[])
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "full-auto"}):
            register_swarm_tools(mcp, coordinator)
        result = _run(mcp.tools["em_swarm_poll"]())
        assert result["tasks_assigned"] == 0


# ===========================================================================
# SECTION 5: em_swarm_agent_info
# ===========================================================================

class TestSwarmAgentInfo:
    def setup_method(self):
        self.mcp = MockMCP()
        self.coordinator = make_coordinator()
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "semi-auto"}):
            register_swarm_tools(self.mcp, self.coordinator)

    def test_agent_info_success(self):
        result = _run(self.mcp.tools["em_swarm_agent_info"]("agent_1"))
        assert result["agent_id"] == "agent_1"
        assert result["state"] == "ACTIVE"
        assert "photography" in result["skills"]
        assert result["health"]["is_healthy"] is True

    def test_agent_info_budget(self):
        result = _run(self.mcp.tools["em_swarm_agent_info"]("agent_1"))
        assert "budget" in result
        assert result["budget"]["daily_spent"] == 2.5
        assert result["budget"]["monthly_spent"] == 25.0
        assert result["budget"]["daily_limit"] == 10.0

    def test_agent_info_composite_score(self):
        result = _run(self.mcp.tools["em_swarm_agent_info"]("agent_1"))
        assert result["composite_score"]["total"] == 0.87
        assert result["composite_score"]["tier"] == "GOLD"

    def test_agent_not_found(self):
        self.coordinator.lifecycle.get_agent.return_value = None
        result = _run(self.mcp.tools["em_swarm_agent_info"]("nonexistent"))
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_agent_info_reputation_error(self):
        """Reputation computation failure should set composite_score=None."""
        self.coordinator.reputation.compute.side_effect = Exception("no data")
        result = _run(self.mcp.tools["em_swarm_agent_info"]("agent_1"))
        assert result["composite_score"] is None

    def test_agent_info_no_budget(self):
        """Agent without budget attribute."""
        agent = MockAgent()
        agent.budget = None
        self.coordinator.lifecycle.get_agent.return_value = agent
        result = _run(self.mcp.tools["em_swarm_agent_info"]("agent_1"))
        assert "budget" not in result

    def test_agent_info_exception(self):
        self.coordinator.lifecycle.get_agent.side_effect = RuntimeError("DB error")
        result = _run(self.mcp.tools["em_swarm_agent_info"]("agent_1"))
        assert "error" in result
        assert "DB error" in result["error"]


# ===========================================================================
# SECTION 6: em_swarm_health
# ===========================================================================

class TestSwarmHealth:
    def setup_method(self):
        self.mcp = MockMCP()
        self.coordinator = make_coordinator()
        with patch.dict(os.environ, {"SWARM_ENABLED": "true", "SWARM_MODE": "semi-auto"}):
            register_swarm_tools(self.mcp, self.coordinator)

    def test_health_healthy(self):
        result = _run(self.mcp.tools["em_swarm_health"]())
        assert result["status"] == "healthy"
        assert "agents" in result
        assert "tasks" in result
        assert "systems" in result
        assert "timestamp" in result

    def test_health_degraded(self):
        self.coordinator.run_health_checks.return_value = {
            "agents": {"total": 24, "active": 18, "degraded": 2},
            "tasks": {"queued": 5},
            "systems": {"em_api": "healthy", "autojob": "unreachable"},
        }
        result = _run(self.mcp.tools["em_swarm_health"]())
        assert result["status"] == "degraded"

    def test_health_degraded_by_agents(self):
        self.coordinator.run_health_checks.return_value = {
            "agents": {"total": 24, "active": 22, "degraded": 1},
            "tasks": {},
            "systems": {},
        }
        result = _run(self.mcp.tools["em_swarm_health"]())
        assert result["status"] == "degraded"

    def test_health_degraded_by_systems(self):
        self.coordinator.run_health_checks.return_value = {
            "agents": {"total": 24, "active": 24, "degraded": 0},
            "tasks": {},
            "systems": {"em_api": "unavailable"},
        }
        result = _run(self.mcp.tools["em_swarm_health"]())
        assert result["status"] == "degraded"

    def test_health_error(self):
        self.coordinator.run_health_checks.side_effect = Exception("health crash")
        result = _run(self.mcp.tools["em_swarm_health"]())
        assert result["status"] == "error"
        assert "health crash" in result["error"]


# ===========================================================================
# SECTION 7: Registration
# ===========================================================================

class TestRegistration:
    def test_registers_5_tools(self):
        mcp = MockMCP()
        register_swarm_tools(mcp, coordinator=None)
        assert len(mcp.tools) == 5
        expected = {
            "em_swarm_status",
            "em_swarm_dashboard",
            "em_swarm_poll",
            "em_swarm_agent_info",
            "em_swarm_health",
        }
        assert set(mcp.tools.keys()) == expected

    def test_registers_with_coordinator(self):
        mcp = MockMCP()
        coordinator = make_coordinator()
        register_swarm_tools(mcp, coordinator)
        assert len(mcp.tools) == 5

    def test_tools_are_async(self):
        mcp = MockMCP()
        register_swarm_tools(mcp, coordinator=None)
        import inspect
        for name, fn in mcp.tools.items():
            assert inspect.iscoroutinefunction(fn), f"{name} is not async"
