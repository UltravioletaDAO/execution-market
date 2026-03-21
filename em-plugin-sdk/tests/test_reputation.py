"""Tests for the reputation resource."""

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


class TestReputationRead:
    async def test_get_agent(self, mock_router, client):
        mock_router.get("/reputation/agents/2106").mock(return_value=httpx.Response(200, json={
            "agent_id": 2106, "count": 42, "score": 87.5, "network": "base",
        }))
        rep = await client.reputation.get_agent(2106)
        assert rep.agent_id == 2106
        assert rep.score == 87.5

    async def test_get_agent_identity(self, mock_router, client):
        mock_router.get("/reputation/agents/2106/identity").mock(return_value=httpx.Response(200, json={
            "agent_id": 2106, "owner": "0xABC", "agent_uri": "https://execution.market",
            "network": "base", "name": "Execution Market",
        }))
        identity = await client.reputation.get_agent_identity(2106)
        assert identity.name == "Execution Market"
        assert identity.owner == "0xABC"

    async def test_leaderboard(self, mock_router, client):
        mock_router.get("/reputation/leaderboard").mock(return_value=httpx.Response(200, json={
            "workers": [{"id": "w1", "score": 95}], "total": 1,
        }))
        result = await client.reputation.leaderboard(limit=10)
        assert result["total"] == 1

    async def test_info(self, mock_router, client):
        mock_router.get("/reputation/info").mock(return_value=httpx.Response(200, json={
            "erc8004_available": True, "network": "base",
        }))
        info = await client.reputation.info()
        assert info["erc8004_available"] is True

    async def test_networks(self, mock_router, client):
        mock_router.get("/reputation/networks").mock(return_value=httpx.Response(200, json={
            "networks": ["base", "ethereum", "polygon"],
        }))
        nets = await client.reputation.networks()
        assert "base" in nets

    async def test_em_reputation(self, mock_router, client):
        mock_router.get("/reputation/em").mock(return_value=httpx.Response(200, json={
            "agent_id": 2106, "count": 10, "score": 90, "network": "base",
        }))
        rep = await client.reputation.em_reputation()
        assert rep.agent_id == 2106

    async def test_em_identity(self, mock_router, client):
        mock_router.get("/reputation/em/identity").mock(return_value=httpx.Response(200, json={
            "agent_id": 2106, "owner": "0xABC", "agent_uri": "uri", "network": "base",
        }))
        identity = await client.reputation.em_identity()
        assert identity.agent_id == 2106

    async def test_get_feedback(self, mock_router, client):
        mock_router.get("/reputation/feedback/task-1").mock(return_value=httpx.Response(200, json={
            "task_id": "task-1", "score": 85, "comment": "Great",
        }))
        fb = await client.reputation.get_feedback("task-1")
        assert fb["score"] == 85


class TestReputationWrite:
    async def test_rate_worker(self, mock_router, client):
        mock_router.post("/reputation/workers/rate").mock(return_value=httpx.Response(200, json={
            "success": True, "tx_hash": "0xabc",
        }))
        result = await client.reputation.rate_worker("sub-1", 90, comment="Excellent")
        assert result["success"] is True

    async def test_rate_agent(self, mock_router, client):
        mock_router.post("/reputation/agents/rate").mock(return_value=httpx.Response(200, json={
            "success": True, "tx_hash": "0xdef",
        }))
        result = await client.reputation.rate_agent("task-1", 85)
        assert result["success"] is True

    async def test_register(self, mock_router, client):
        mock_router.post("/reputation/register").mock(return_value=httpx.Response(200, json={
            "success": True, "agent_id": 999,
        }))
        result = await client.reputation.register("0x1234567890abcdef1234567890abcdef12345678")
        assert result["agent_id"] == 999

    async def test_prepare_feedback(self, mock_router, client):
        mock_router.post("/reputation/prepare-feedback").mock(return_value=httpx.Response(200, json={
            "unsigned_tx": {"to": "0xABC", "data": "0x..."},
        }))
        result = await client.reputation.prepare_feedback("task-1", 80)
        assert "unsigned_tx" in result

    async def test_confirm_feedback(self, mock_router, client):
        mock_router.post("/reputation/confirm-feedback").mock(return_value=httpx.Response(200, json={
            "success": True,
        }))
        result = await client.reputation.confirm_feedback("0xabcdef")
        assert result["success"] is True
