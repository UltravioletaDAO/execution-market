"""Tests for H2A and agents resources."""

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


class TestH2A:
    async def test_publish(self, mock_router, client):
        mock_router.post("/h2a/tasks").mock(return_value=httpx.Response(201, json={
            "task_id": "h2a-1", "status": "published", "bounty_usd": 5.0,
            "fee_usd": 0.65, "total_required_usd": 5.0, "deadline": "2026-04-01",
        }))
        result = await client.h2a.publish(
            title="Research competitors",
            instructions="Find pricing data for top 5 competitors in the market",
            category="research",
            bounty_usd=5.0,
        )
        assert result["task_id"] == "h2a-1"

    async def test_list(self, mock_router, client):
        mock_router.get("/h2a/tasks").mock(return_value=httpx.Response(200, json={
            "tasks": [{"id": "h2a-1", "title": "Research"}], "total": 1,
        }))
        result = await client.h2a.list()
        assert result["total"] == 1

    async def test_get(self, mock_router, client):
        mock_router.get("/h2a/tasks/h2a-1").mock(return_value=httpx.Response(200, json={
            "id": "h2a-1", "title": "Research", "status": "published",
        }))
        result = await client.h2a.get("h2a-1")
        assert result["id"] == "h2a-1"

    async def test_submissions(self, mock_router, client):
        mock_router.get("/h2a/tasks/h2a-1/submissions").mock(return_value=httpx.Response(200, json={
            "submissions": [{"id": "sub-1", "status": "pending"}], "count": 1,
        }))
        result = await client.h2a.submissions("h2a-1")
        assert result["count"] == 1

    async def test_approve(self, mock_router, client):
        mock_router.post("/h2a/tasks/h2a-1/approve").mock(return_value=httpx.Response(200, json={
            "status": "completed", "worker_tx": "0xabc",
        }))
        result = await client.h2a.approve("h2a-1", submission_id="sub-1")
        assert result["status"] == "completed"

    async def test_reject(self, mock_router, client):
        mock_router.post("/h2a/tasks/h2a-1/reject").mock(return_value=httpx.Response(200, json={
            "status": "rejected",
        }))
        result = await client.h2a.reject("h2a-1", submission_id="sub-1", notes="Incomplete data")
        assert result["status"] == "rejected"

    async def test_cancel(self, mock_router, client):
        mock_router.post("/h2a/tasks/h2a-1/cancel").mock(return_value=httpx.Response(200, json={
            "success": True,
        }))
        result = await client.h2a.cancel("h2a-1")
        assert result["success"] is True


class TestAgents:
    async def test_directory(self, mock_router, client):
        mock_router.get("/agents/directory").mock(return_value=httpx.Response(200, json={
            "agents": [{"executor_id": "a-1", "display_name": "ResearchBot"}],
            "total": 1,
        }))
        result = await client.agents.directory()
        assert result["total"] == 1

    async def test_register_executor(self, mock_router, client):
        mock_router.post("/agents/register-executor").mock(return_value=httpx.Response(201, json={
            "executor_id": "a-1", "display_name": "ResearchBot", "capabilities": ["research"],
        }))
        result = await client.agents.register_executor(
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            capabilities=["research"],
            display_name="ResearchBot",
        )
        assert result["display_name"] == "ResearchBot"
