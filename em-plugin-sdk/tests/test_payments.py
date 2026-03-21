"""Tests for the payments resource."""

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


class TestPayments:
    async def test_balance(self, mock_router, client):
        mock_router.get("/payments/balance/0xABC").mock(return_value=httpx.Response(200, json={
            "base": {"USDC": "10.50"},
            "ethereum": {"USDC": "0.00"},
            "polygon": {"USDC": "5.25"},
        }))
        result = await client.payments.balance("0xABC")
        assert result["base"]["USDC"] == "10.50"

    async def test_events(self, mock_router, client):
        mock_router.get("/payments/events").mock(return_value=httpx.Response(200, json={
            "events": [
                {"id": "evt-1", "event_type": "disburse_worker", "amount_usdc": 0.087,
                 "tx_hash": "0xabc", "network": "base", "status": "success"},
            ],
            "total": 1,
        }))
        result = await client.payments.events("0xABC", limit=10)
        assert result["total"] == 1
        assert result["events"][0]["event_type"] == "disburse_worker"

    async def test_events_with_filter(self, mock_router, client):
        route = mock_router.get("/payments/events").mock(return_value=httpx.Response(200, json={
            "events": [], "total": 0,
        }))
        await client.payments.events("0xABC", event_type="settle_worker_direct")
        req = route.calls.last.request
        assert "event_type=settle_worker_direct" in str(req.url)

    async def test_task_payment(self, mock_router, client):
        mock_router.get("/tasks/task-1/payment").mock(return_value=httpx.Response(200, json={
            "task_id": "task-1",
            "status": "completed",
            "total_amount": 0.10,
            "released_amount": 0.087,
            "currency": "USDC",
            "network": "base",
            "events": [
                {"id": "e1", "type": "final_release", "actor": "system",
                 "timestamp": "2026-03-20T00:00:00Z", "network": "base",
                 "amount": 0.087, "tx_hash": "0xdef"},
            ],
        }))
        timeline = await client.payments.task_payment("task-1")
        assert timeline.status == "completed"
        assert timeline.released_amount == 0.087
        assert len(timeline.events) == 1

    async def test_task_transactions(self, mock_router, client):
        mock_router.get("/tasks/task-1/transactions").mock(return_value=httpx.Response(200, json={
            "task_id": "task-1",
            "transactions": [
                {"id": "tx-1", "event_type": "settle_worker_direct", "amount_usdc": 0.087},
                {"id": "tx-2", "event_type": "settle_fee_direct", "amount_usdc": 0.013},
            ],
            "total_count": 2,
            "summary": {"total_released": 0.087, "fee_collected": 0.013},
        }))
        result = await client.payments.task_transactions("task-1")
        assert result["total_count"] == 2
