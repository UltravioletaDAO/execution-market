"""Tests for swarm and relay resources."""

import pytest
import httpx
import respx

from em_plugin_sdk import EMClient

BASE = "https://api.execution.market/api/v1"


@pytest.fixture
def mock_router():
    with respx.mock(base_url=BASE) as router:
        yield router


@pytest.fixture
async def client(mock_router):
    async with EMClient(api_key="em_test") as c:
        yield c


class TestSwarm:
    async def test_status(self, mock_router, client):
        mock_router.get("/swarm/status").mock(return_value=httpx.Response(200, json={
            "active_agents": 5, "task_queue": 12, "uptime_hours": 48,
        }))
        result = await client.swarm.status()
        assert result["active_agents"] == 5

    async def test_health(self, mock_router, client):
        mock_router.get("/swarm/health").mock(return_value=httpx.Response(200, json={
            "coordinator": "ok", "event_bus": "ok", "budget_controller": "ok",
        }))
        result = await client.swarm.health()
        assert result["coordinator"] == "ok"

    async def test_agents(self, mock_router, client):
        mock_router.get("/swarm/agents").mock(return_value=httpx.Response(200, json={
            "agents": [{"id": "a1", "status": "active"}], "count": 1,
        }))
        result = await client.swarm.agents()
        assert result["count"] == 1

    async def test_agent_detail(self, mock_router, client):
        mock_router.get("/swarm/agents/a1").mock(return_value=httpx.Response(200, json={
            "id": "a1", "personality": "explorer", "tasks_completed": 10,
        }))
        result = await client.swarm.agent("a1")
        assert result["personality"] == "explorer"

    async def test_dashboard(self, mock_router, client):
        mock_router.get("/swarm/dashboard").mock(return_value=httpx.Response(200, json={
            "overview": {}, "agents": [], "tasks": [],
        }))
        result = await client.swarm.dashboard()
        assert "overview" in result

    async def test_metrics(self, mock_router, client):
        mock_router.get("/swarm/metrics").mock(return_value=httpx.Response(200, json={
            "tasks_per_hour": 2.5, "avg_completion_min": 15,
        }))
        result = await client.swarm.metrics()
        assert result["tasks_per_hour"] == 2.5

    async def test_events(self, mock_router, client):
        mock_router.get("/swarm/events").mock(return_value=httpx.Response(200, json={
            "events": [{"type": "task.assigned", "timestamp": "2026-03-20"}], "count": 1,
        }))
        result = await client.swarm.events(limit=10)
        assert result["count"] == 1

    async def test_tasks(self, mock_router, client):
        mock_router.get("/swarm/tasks").mock(return_value=httpx.Response(200, json={
            "queued": 3, "in_progress": 2, "tasks": [],
        }))
        result = await client.swarm.tasks()
        assert result["queued"] == 3

    async def test_poll(self, mock_router, client):
        mock_router.post("/swarm/poll").mock(return_value=httpx.Response(200, json={
            "ingested": 2, "routed": 1,
        }))
        result = await client.swarm.poll()
        assert result["ingested"] == 2

    async def test_update_config(self, mock_router, client):
        mock_router.post("/swarm/config").mock(return_value=httpx.Response(200, json={
            "success": True,
        }))
        result = await client.swarm.update_config({"max_concurrent": 10})
        assert result["success"] is True

    async def test_activate_agent(self, mock_router, client):
        mock_router.post("/swarm/agents/a1/activate").mock(return_value=httpx.Response(200, json={
            "success": True, "status": "active",
        }))
        result = await client.swarm.activate_agent("a1")
        assert result["status"] == "active"

    async def test_suspend_agent(self, mock_router, client):
        mock_router.post("/swarm/agents/a1/suspend").mock(return_value=httpx.Response(200, json={
            "success": True, "status": "suspended",
        }))
        result = await client.swarm.suspend_agent("a1")
        assert result["status"] == "suspended"

    async def test_update_budget(self, mock_router, client):
        mock_router.post("/swarm/agents/a1/budget").mock(return_value=httpx.Response(200, json={
            "success": True, "daily_budget_usd": 5.0,
        }))
        result = await client.swarm.update_budget("a1", {"daily_budget_usd": 5.0})
        assert result["daily_budget_usd"] == 5.0


class TestRelay:
    async def test_create(self, mock_router, client):
        mock_router.post("/relay-chains").mock(return_value=httpx.Response(201, json={
            "chain_id": "rc-1", "parent_task_id": "task-1", "legs": 3,
        }))
        result = await client.relay.create("task-1", legs=3)
        assert result["chain_id"] == "rc-1"

    async def test_get(self, mock_router, client):
        mock_router.get("/relay-chains/rc-1").mock(return_value=httpx.Response(200, json={
            "chain_id": "rc-1", "status": "in_progress",
            "legs": [{"number": 1, "status": "completed"}, {"number": 2, "status": "active"}],
        }))
        result = await client.relay.get("rc-1")
        assert len(result["legs"]) == 2

    async def test_assign_leg(self, mock_router, client):
        mock_router.post("/relay-chains/rc-1/legs/1/assign").mock(return_value=httpx.Response(200, json={
            "success": True,
        }))
        result = await client.relay.assign_leg("rc-1", 1, "exec-1")
        assert result["success"] is True

    async def test_handoff(self, mock_router, client):
        mock_router.post("/relay-chains/rc-1/legs/1/handoff").mock(return_value=httpx.Response(200, json={
            "success": True, "next_leg": 2,
        }))
        result = await client.relay.handoff("rc-1", 1, notes="Package delivered to checkpoint")
        assert result["next_leg"] == 2
