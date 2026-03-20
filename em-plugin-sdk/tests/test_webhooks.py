"""Tests for webhooks resource."""

import hashlib
import hmac

import pytest
import httpx
import respx

from em_plugin_sdk import EMClient

BASE = "https://api.execution.market/api/v1"

WH_JSON = {
    "id": "wh-1",
    "url": "https://my.app/em-hook",
    "events": ["task.completed"],
    "active": True,
    "secret": "whsec_abc123",
}


@pytest.fixture
def mock_router():
    with respx.mock(base_url=BASE) as router:
        yield router


@pytest.fixture
async def client(mock_router):
    async with EMClient(api_key="em_test") as c:
        yield c


class TestWebhooksCRUD:
    async def test_create(self, mock_router, client):
        mock_router.post("/webhooks/").mock(return_value=httpx.Response(201, json=WH_JSON))
        wh = await client.webhooks.create(url="https://my.app/em-hook", events=["task.completed"])
        assert wh.id == "wh-1"
        assert wh.secret == "whsec_abc123"

    async def test_list(self, mock_router, client):
        mock_router.get("/webhooks/").mock(return_value=httpx.Response(200, json={
            "webhooks": [WH_JSON], "count": 1,
        }))
        result = await client.webhooks.list()
        assert result.count == 1
        assert result.webhooks[0].url == "https://my.app/em-hook"

    async def test_get(self, mock_router, client):
        mock_router.get("/webhooks/wh-1").mock(return_value=httpx.Response(200, json=WH_JSON))
        wh = await client.webhooks.get("wh-1")
        assert wh.id == "wh-1"

    async def test_update(self, mock_router, client):
        updated = {**WH_JSON, "active": False}
        mock_router.put("/webhooks/wh-1").mock(return_value=httpx.Response(200, json=updated))
        wh = await client.webhooks.update("wh-1", active=False)
        assert wh.active is False

    async def test_delete(self, mock_router, client):
        mock_router.delete("/webhooks/wh-1").mock(return_value=httpx.Response(200, json={"success": True}))
        result = await client.webhooks.delete("wh-1")
        assert result["success"] is True

    async def test_rotate_secret(self, mock_router, client):
        mock_router.post("/webhooks/wh-1/rotate-secret").mock(return_value=httpx.Response(200, json={
            "secret": "whsec_new456",
        }))
        result = await client.webhooks.rotate_secret("wh-1")
        assert result["secret"] == "whsec_new456"

    async def test_test_ping(self, mock_router, client):
        mock_router.post("/webhooks/wh-1/test").mock(return_value=httpx.Response(200, json={
            "success": True, "status_code": 200,
        }))
        result = await client.webhooks.test("wh-1")
        assert result["success"] is True


class TestWebhookSignature:
    def test_verify_valid_signature(self):
        secret = "whsec_test123"
        body = b'{"event":"task.completed","task_id":"abc"}'
        timestamp = "1711000000"
        signature = hmac.new(
            secret.encode(),
            f"{timestamp}.".encode() + body,
            hashlib.sha256,
        ).hexdigest()
        from em_plugin_sdk.resources.webhooks import WebhooksResource
        assert WebhooksResource.verify_signature(body, signature, timestamp, secret) is True

    def test_verify_invalid_signature(self):
        from em_plugin_sdk.resources.webhooks import WebhooksResource
        assert WebhooksResource.verify_signature(b"body", "invalid", "123", "secret") is False
