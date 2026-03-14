"""
Tests for Swarm REST API Routes (/api/v1/swarm/*)

Tests the FastAPI endpoints that expose the swarm coordinator
through the standard EM REST API.
"""

import pytest
import json
import time
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

# Stub out supabase_client before any api imports to avoid the
# "SUPABASE_URL required" RuntimeError.  The swarm API module
# does NOT use supabase_client, but importing through api.__init__
# → api.routes → api.routers.tasks triggers it.
if "supabase_client" not in sys.modules:
    _stub = MagicMock()
    _stub.SUPABASE_URL = "https://test.supabase.co"
    sys.modules["supabase_client"] = _stub

from api.swarm import (
    router,
    get_coordinator,
    require_coordinator,
    SwarmConfigUpdate,
    BudgetUpdate,
    AgentActivation,
    PollResult,
    SWARM_ENABLED,
)


# ─── Config Model Tests ──────────────────────────────────────────────────────


class TestSwarmConfigUpdate:
    """Test SwarmConfigUpdate Pydantic model."""

    def test_valid_config(self):
        config = SwarmConfigUpdate(
            mode="semi-auto",
            daily_budget=25.0,
            max_task_bounty=2.0,
        )
        assert config.mode == "semi-auto"
        assert config.daily_budget == 25.0
        assert config.max_task_bounty == 2.0

    def test_partial_config(self):
        config = SwarmConfigUpdate(mode="passive")
        assert config.mode == "passive"
        assert config.daily_budget is None
        assert config.max_task_bounty is None

    def test_empty_config(self):
        config = SwarmConfigUpdate()
        assert config.mode is None
        assert config.daily_budget is None

    def test_budget_non_negative(self):
        with pytest.raises(Exception):  # ValidationError
            SwarmConfigUpdate(daily_budget=-5.0)


class TestBudgetUpdate:
    """Test BudgetUpdate Pydantic model."""

    def test_valid_budget(self):
        budget = BudgetUpdate(daily_limit=10.0, monthly_limit=200.0)
        assert budget.daily_limit == 10.0
        assert budget.monthly_limit == 200.0

    def test_partial_budget(self):
        budget = BudgetUpdate(daily_limit=5.0)
        assert budget.daily_limit == 5.0
        assert budget.monthly_limit is None

    def test_zero_budget(self):
        budget = BudgetUpdate(daily_limit=0.0)
        assert budget.daily_limit == 0.0


class TestAgentActivation:
    """Test AgentActivation Pydantic model."""

    def test_with_skills(self):
        activation = AgentActivation(
            skills=["physical_presence", "data_collection"],
            daily_budget=15.0,
        )
        assert len(activation.skills) == 2
        assert activation.daily_budget == 15.0

    def test_empty(self):
        activation = AgentActivation()
        assert activation.skills is None
        assert activation.daily_budget is None


class TestPollResult:
    """Test PollResult Pydantic model."""

    def test_default_values(self):
        result = PollResult()
        assert result.new_tasks_ingested == 0
        assert result.tasks_assigned == 0
        assert result.health_issues == []
        assert result.duration_ms == 0

    def test_populated_result(self):
        result = PollResult(
            new_tasks_ingested=5,
            tasks_assigned=3,
            health_issues=["low_budget: agent_1"],
            duration_ms=42.5,
            mode="semi-auto",
            timestamp="2026-03-12T04:00:00Z",
        )
        assert result.new_tasks_ingested == 5
        assert result.tasks_assigned == 3
        assert len(result.health_issues) == 1
        assert result.mode == "semi-auto"

    def test_serialization(self):
        result = PollResult(new_tasks_ingested=2, tasks_assigned=1)
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["new_tasks_ingested"] == 2


# ─── Coordinator Singleton Tests ──────────────────────────────────────────────


class TestCoordinatorInit:
    """Test coordinator lazy initialization."""

    def test_get_coordinator_disabled(self):
        """When SWARM_ENABLED is false, coordinator is None."""
        import api.swarm as swarm_module
        # Reset state
        swarm_module._coordinator = None
        swarm_module._coordinator_initialized = False
        swarm_module.SWARM_ENABLED = False

        result = swarm_module.get_coordinator()
        assert result is None
        assert swarm_module._coordinator_initialized is True

    def test_get_coordinator_cached(self):
        """Second call returns cached result."""
        import api.swarm as swarm_module
        swarm_module._coordinator = "cached"
        swarm_module._coordinator_initialized = True

        result = swarm_module.get_coordinator()
        assert result == "cached"

    def test_require_coordinator_raises(self):
        """require_coordinator raises 503 when disabled."""
        import api.swarm as swarm_module
        swarm_module._coordinator = None
        swarm_module._coordinator_initialized = True

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            swarm_module.require_coordinator()
        assert exc_info.value.status_code == 503


# ─── FastAPI Integration Tests ────────────────────────────────────────────────

# We test using httpx + TestClient for proper async FastAPI testing

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    test_app = FastAPI()
    test_app.include_router(router)
    client = TestClient(test_app)
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi/httpx not available")
class TestStatusEndpoint:
    """Test GET /api/v1/swarm/status."""

    def test_status_disabled(self):
        """Status returns even when swarm is disabled."""
        import api.swarm as swarm_module
        swarm_module._coordinator = None
        swarm_module._coordinator_initialized = True
        swarm_module.SWARM_ENABLED = False

        response = client.get("/api/v1/swarm/status")
        assert response.status_code == 200
        data = response.json()
        assert data["swarm_enabled"] is False
        assert data["coordinator"] == "not_initialized"

    def test_status_with_coordinator(self):
        """Status returns dashboard data when coordinator is active."""
        import api.swarm as swarm_module
        mock_coord = MagicMock()
        mock_coord.get_dashboard.return_value = {
            "agents": {"registered": 24, "active": 18},
            "tasks": {"ingested": 100, "completed": 75},
            "performance": {"success_rate": 0.92},
        }
        swarm_module._coordinator = mock_coord
        swarm_module._coordinator_initialized = True
        swarm_module.SWARM_ENABLED = True

        response = client.get("/api/v1/swarm/status")
        assert response.status_code == 200
        data = response.json()
        assert data["coordinator"] == "active"
        assert data["agents"]["registered"] == 24


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi/httpx not available")
class TestHealthEndpoint:
    """Test GET /api/v1/swarm/health."""

    def test_health_disabled(self):
        import api.swarm as swarm_module
        swarm_module._coordinator = None
        swarm_module._coordinator_initialized = True

        response = client.get("/api/v1/swarm/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"

    def test_health_all_green(self):
        import api.swarm as swarm_module
        mock_coord = MagicMock()
        mock_coord.run_health_checks.return_value = {
            "timestamp": "2026-03-12T04:00:00Z",
            "agents": {"checked": 24, "healthy": 24, "degraded": 0, "recovered": 0},
            "tasks": {"expired": 0, "stale": 0},
            "systems": {"em_api": "ok", "autojob": "available"},
        }
        swarm_module._coordinator = mock_coord
        swarm_module._coordinator_initialized = True
        swarm_module.SWARM_ENABLED = True

        response = client.get("/api/v1/swarm/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["issues_count"] == 0

    def test_health_degraded(self):
        import api.swarm as swarm_module
        mock_coord = MagicMock()
        mock_coord.run_health_checks.return_value = {
            "timestamp": "2026-03-12T04:00:00Z",
            "agents": {"checked": 24, "healthy": 22, "degraded": 2, "recovered": 0},
            "tasks": {"expired": 1, "stale": 0},
            "systems": {"em_api": "ok", "autojob": "available"},
        }
        swarm_module._coordinator = mock_coord
        swarm_module._coordinator_initialized = True

        response = client.get("/api/v1/swarm/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["issues_count"] == 2


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi/httpx not available")
class TestAgentsEndpoints:
    """Test GET /api/v1/swarm/agents."""

    def test_list_agents(self):
        import api.swarm as swarm_module
        mock_coord = MagicMock()
        mock_coord.get_dashboard.return_value = {
            "fleet": [
                {"agent_id": "agent_1", "state": "IDLE"},
                {"agent_id": "agent_2", "state": "ACTIVE"},
                {"agent_id": "agent_3", "state": "IDLE"},
            ],
        }
        swarm_module._coordinator = mock_coord
        swarm_module._coordinator_initialized = True
        swarm_module.SWARM_ENABLED = True

        response = client.get("/api/v1/swarm/agents")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["agents"]) == 3

    def test_list_agents_filter_state(self):
        import api.swarm as swarm_module
        mock_coord = MagicMock()
        mock_coord.get_dashboard.return_value = {
            "fleet": [
                {"agent_id": "agent_1", "state": "IDLE"},
                {"agent_id": "agent_2", "state": "ACTIVE"},
                {"agent_id": "agent_3", "state": "IDLE"},
            ],
        }
        swarm_module._coordinator = mock_coord
        swarm_module._coordinator_initialized = True

        response = client.get("/api/v1/swarm/agents?state=IDLE")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(a["state"] == "IDLE" for a in data["agents"])

    def test_agents_coordinator_required(self):
        import api.swarm as swarm_module
        swarm_module._coordinator = None
        swarm_module._coordinator_initialized = True

        response = client.get("/api/v1/swarm/agents")
        assert response.status_code == 503


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi/httpx not available")
class TestDashboardEndpoint:
    """Test GET /api/v1/swarm/dashboard."""

    def test_dashboard(self):
        import api.swarm as swarm_module
        mock_coord = MagicMock()
        mock_coord.get_dashboard.return_value = {
            "agents": {"registered": 24, "active": 18},
            "tasks": {"ingested": 50, "completed": 40},
            "fleet": [],
            "performance": {"success_rate": 0.85},
        }
        swarm_module._coordinator = mock_coord
        swarm_module._coordinator_initialized = True
        swarm_module.SWARM_ENABLED = True

        response = client.get("/api/v1/swarm/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert data["config"]["mode"] is not None
        assert "timestamp" in data


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi/httpx not available")
class TestMetricsEndpoint:
    """Test GET /api/v1/swarm/metrics."""

    def test_metrics_disabled(self):
        import api.swarm as swarm_module
        swarm_module._coordinator = None
        swarm_module._coordinator_initialized = True

        response = client.get("/api/v1/swarm/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["swarm_enabled"] == 0

    def test_metrics_with_data(self):
        import api.swarm as swarm_module
        mock_coord = MagicMock()
        mock_metrics = MagicMock()
        mock_metrics.agents_registered = 24
        mock_metrics.agents_active = 18
        mock_metrics.agents_degraded = 1
        mock_metrics.agents_suspended = 2
        mock_metrics.tasks_ingested = 100
        mock_metrics.tasks_assigned = 85
        mock_metrics.tasks_completed = 75
        mock_metrics.tasks_failed = 5
        mock_metrics.bounty_earned = 150.50
        mock_metrics.avg_routing_ms = 3.2
        mock_metrics.success_rate = 0.94
        mock_metrics.enrichment_rate = 0.65
        mock_coord.get_metrics.return_value = mock_metrics
        swarm_module._coordinator = mock_coord
        swarm_module._coordinator_initialized = True
        swarm_module.SWARM_ENABLED = True

        response = client.get("/api/v1/swarm/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["swarm_enabled"] == 1
        assert data["agents_registered"] == 24
        assert data["tasks_completed"] == 75
        assert data["success_rate"] == 0.94


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi/httpx not available")
class TestEventsEndpoint:
    """Test GET /api/v1/swarm/events."""

    def test_list_events(self):
        import api.swarm as swarm_module
        mock_coord = MagicMock()
        mock_coord.get_events.return_value = [
            {"type": "TASK_ASSIGNED", "agent_id": "agent_1", "task_id": "t1"},
            {"type": "TASK_COMPLETED", "agent_id": "agent_1", "task_id": "t1"},
            {"type": "HEALTH_DEGRADED", "agent_id": "agent_2"},
        ]
        swarm_module._coordinator = mock_coord
        swarm_module._coordinator_initialized = True
        swarm_module.SWARM_ENABLED = True

        response = client.get("/api/v1/swarm/events")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

    def test_events_filter_type(self):
        import api.swarm as swarm_module
        mock_coord = MagicMock()
        mock_coord.get_events.return_value = [
            {"type": "TASK_ASSIGNED", "agent_id": "agent_1"},
            {"type": "TASK_COMPLETED", "agent_id": "agent_1"},
            {"type": "TASK_ASSIGNED", "agent_id": "agent_2"},
        ]
        swarm_module._coordinator = mock_coord
        swarm_module._coordinator_initialized = True

        response = client.get("/api/v1/swarm/events?event_type=TASK_ASSIGNED")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2


@pytest.mark.skipif(not HAS_TESTCLIENT, reason="fastapi/httpx not available")
class TestConfigEndpoint:
    """Test POST /api/v1/swarm/config."""

    def _admin_client(self):
        """Create a test client with auth dependency overridden."""
        from api.swarm import require_admin
        app_with_auth = FastAPI()
        app_with_auth.include_router(router)
        app_with_auth.dependency_overrides[require_admin] = lambda: MagicMock()
        return TestClient(app_with_auth)

    def test_update_mode(self):
        import api.swarm as swarm_module
        swarm_module.SWARM_MODE = "passive"

        admin_client = self._admin_client()
        response = admin_client.post(
            "/api/v1/swarm/config",
            json={"mode": "semi-auto"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"]["mode"] == "semi-auto"
        assert data["current_config"]["mode"] == "semi-auto"

    def test_update_budget(self):
        import api.swarm as swarm_module

        admin_client = self._admin_client()
        response = admin_client.post(
            "/api/v1/swarm/config",
            json={"daily_budget": 50.0, "max_task_bounty": 5.0},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["updated"]["daily_budget"] == 50.0
        assert data["updated"]["max_task_bounty"] == 5.0

    def test_invalid_mode(self):
        admin_client = self._admin_client()
        response = admin_client.post(
            "/api/v1/swarm/config",
            json={"mode": "yolo"},
        )
        assert response.status_code == 400


# ─── Router Registration Test ────────────────────────────────────────────────

class TestRouterRegistration:
    """Verify the router has all expected routes."""

    def test_router_prefix(self):
        assert router.prefix == "/api/v1/swarm"

    def test_router_has_routes(self):
        paths = [r.path for r in router.routes]
        # Routes include the router prefix
        prefix = "/api/v1/swarm"
        expected = [
            f"{prefix}/status",
            f"{prefix}/health",
            f"{prefix}/agents",
            f"{prefix}/agents/{{agent_id}}",
            f"{prefix}/poll",
            f"{prefix}/dashboard",
            f"{prefix}/metrics",
            f"{prefix}/config",
            f"{prefix}/events",
            f"{prefix}/tasks",
            f"{prefix}/agents/{{agent_id}}/activate",
            f"{prefix}/agents/{{agent_id}}/suspend",
            f"{prefix}/agents/{{agent_id}}/budget",
        ]
        for path in expected:
            assert path in paths, f"Missing route: {path}. Available: {paths}"

    def test_router_tags(self):
        assert "swarm" in router.tags
