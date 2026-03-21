"""Tests for EMClient — resource-based API with retry and pagination."""

import pytest
import httpx
import respx

from em_plugin_sdk import (
    EMClient,
    EMAuthError,
    EMNotFoundError,
    EMValidationError,
    EMServerError,
    EMError,
    CreateTaskParams,
    SubmitEvidenceParams,
    ApproveParams,
    RejectParams,
    TaskCategory,
    EvidenceType,
)

BASE = "https://api.execution.market/api/v1"
API_KEY = "em_test_key_123"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_router():
    with respx.mock(base_url=BASE) as router:
        yield router


@pytest.fixture
async def client(mock_router):
    async with EMClient(api_key=API_KEY) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth & headers
# ---------------------------------------------------------------------------

class TestHeaders:
    async def test_bearer_token_sent(self, mock_router, client):
        route = mock_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        await client.health()
        assert route.calls.last.request.headers["authorization"] == f"Bearer {API_KEY}"

    async def test_user_agent_sent(self, mock_router, client):
        route = mock_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        await client.health()
        assert "em-plugin-sdk" in route.calls.last.request.headers["user-agent"]

    async def test_no_auth_header_when_no_key(self, mock_router):
        mock_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        async with EMClient() as c:
            await c.health()
        req = mock_router.calls.last.request
        assert "authorization" not in req.headers


# ---------------------------------------------------------------------------
# Health & Config
# ---------------------------------------------------------------------------

class TestTopLevel:
    async def test_health(self, mock_router, client):
        mock_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok", "version": "2.0"}))
        resp = await client.health()
        assert resp.status == "ok"
        assert resp.version == "2.0"

    async def test_config(self, mock_router, client):
        mock_router.get("/config").mock(return_value=httpx.Response(200, json={
            "min_bounty_usd": 0.01,
            "max_bounty_usd": 10000,
            "supported_networks": ["base", "ethereum"],
            "supported_tokens": ["USDC"],
            "preferred_network": "base",
            "require_api_key": False,
        }))
        cfg = await client.config()
        assert cfg.preferred_network == "base"
        assert not cfg.require_api_key


# ---------------------------------------------------------------------------
# Tasks resource
# ---------------------------------------------------------------------------

TASK_JSON = {
    "id": "abc-123",
    "title": "Test task",
    "status": "published",
    "category": "simple_action",
    "bounty_usd": 0.10,
    "deadline": "2026-04-01T00:00:00Z",
    "created_at": "2026-03-20T00:00:00Z",
    "agent_id": "0xABC",
}


class TestTasks:
    async def test_create(self, mock_router, client):
        mock_router.post("/tasks").mock(return_value=httpx.Response(201, json=TASK_JSON))
        params = CreateTaskParams(
            title="Test task title here",
            instructions="Detailed instructions for the task that must be at least 20 chars",
            category=TaskCategory.SIMPLE_ACTION,
            bounty_usd=0.10,
            deadline_hours=1,
            evidence_required=[EvidenceType.PHOTO],
        )
        task = await client.tasks.create(params)
        assert task.id == "abc-123"

    async def test_get(self, mock_router, client):
        mock_router.get("/tasks/abc-123").mock(return_value=httpx.Response(200, json=TASK_JSON))
        task = await client.tasks.get("abc-123")
        assert task.title == "Test task"

    async def test_list_page(self, mock_router, client):
        mock_router.get("/tasks").mock(return_value=httpx.Response(200, json={
            "tasks": [TASK_JSON],
            "total": 1,
            "count": 1,
            "offset": 0,
            "has_more": False,
        }))
        result = await client.tasks.list_page(status="published")
        assert result.total == 1
        assert result.tasks[0].id == "abc-123"

    async def test_list_auto_paginate(self, mock_router, client):
        """Test that list() returns a PageIterator that auto-paginates."""
        # Page 1
        mock_router.get("/tasks").mock(side_effect=[
            httpx.Response(200, json={
                "tasks": [TASK_JSON],
                "total": 2,
                "count": 1,
                "offset": 0,
                "has_more": True,
            }),
            httpx.Response(200, json={
                "tasks": [{**TASK_JSON, "id": "def-456"}],
                "total": 2,
                "count": 1,
                "offset": 1,
                "has_more": False,
            }),
        ])
        tasks = await client.tasks.list(status="published").collect()
        assert len(tasks) == 2
        assert tasks[0].id == "abc-123"
        assert tasks[1].id == "def-456"

    async def test_cancel(self, mock_router, client):
        mock_router.post("/tasks/abc-123/cancel").mock(return_value=httpx.Response(200, json={
            "success": True, "message": "Cancelled",
        }))
        result = await client.tasks.cancel("abc-123", reason="Done")
        assert result["success"] is True

    async def test_assign(self, mock_router, client):
        mock_router.post("/tasks/abc-123/assign").mock(return_value=httpx.Response(200, json={
            "success": True, "message": "Assigned",
        }))
        result = await client.tasks.assign("abc-123", "exec-1")
        assert result["success"] is True

    async def test_batch_create(self, mock_router, client):
        mock_router.post("/tasks/batch").mock(return_value=httpx.Response(200, json={
            "created": 2, "failed": 0, "tasks": [], "errors": [], "total_bounty": 0.20,
        }))
        result = await client.tasks.batch_create([{"title": "t1"}, {"title": "t2"}])
        assert result["created"] == 2

    async def test_apply(self, mock_router, client):
        mock_router.post("/tasks/abc-123/apply").mock(return_value=httpx.Response(201, json={
            "id": "app-1", "task_id": "abc-123", "executor_id": "exec-1",
            "status": "pending", "created_at": "2026-03-20T00:00:00Z",
        }))
        app = await client.tasks.apply("abc-123", "exec-1", message="I can do this")
        assert app.executor_id == "exec-1"

    async def test_list_applications(self, mock_router, client):
        mock_router.get("/tasks/abc-123/applications").mock(return_value=httpx.Response(200, json={
            "applications": [{"id": "app-1", "task_id": "abc-123", "executor_id": "exec-1",
                              "status": "pending", "created_at": "2026-03-20T00:00:00Z"}],
            "count": 1,
        }))
        result = await client.tasks.list_applications("abc-123")
        assert result.count == 1

    async def test_get_payment(self, mock_router, client):
        mock_router.get("/tasks/abc-123/payment").mock(return_value=httpx.Response(200, json={
            "task_id": "abc-123", "status": "completed", "total_amount": 0.10,
            "released_amount": 0.087, "events": [],
        }))
        timeline = await client.tasks.get_payment("abc-123")
        assert timeline.released_amount == 0.087


# ---------------------------------------------------------------------------
# Submissions resource
# ---------------------------------------------------------------------------

SUB_JSON = {
    "id": "sub-1", "task_id": "abc-123", "executor_id": "exec-1",
    "status": "pending", "submitted_at": "2026-03-20T00:00:00Z",
    "evidence": {"photo": "https://cdn.example.com/photo.jpg"},
}


class TestSubmissions:
    async def test_list(self, mock_router, client):
        mock_router.get("/tasks/abc-123/submissions").mock(return_value=httpx.Response(200, json={
            "submissions": [SUB_JSON], "count": 1,
        }))
        result = await client.submissions.list("abc-123")
        assert result.count == 1

    async def test_submit(self, mock_router, client):
        mock_router.post("/tasks/abc-123/submit").mock(return_value=httpx.Response(201, json=SUB_JSON))
        params = SubmitEvidenceParams(executor_id="exec-1", evidence={"photo": "url"})
        sub = await client.submissions.submit("abc-123", params)
        assert sub.id == "sub-1"

    async def test_approve(self, mock_router, client):
        mock_router.post("/submissions/sub-1/approve").mock(return_value=httpx.Response(200, json={
            "success": True, "message": "Approved",
        }))
        result = await client.submissions.approve("sub-1", ApproveParams(notes="Good"))
        assert result["success"] is True

    async def test_reject(self, mock_router, client):
        mock_router.post("/submissions/sub-1/reject").mock(return_value=httpx.Response(200, json={
            "success": True, "message": "Rejected",
        }))
        result = await client.submissions.reject("sub-1", RejectParams(notes="Evidence is blurry and unusable"))
        assert result["success"] is True

    async def test_request_more_info(self, mock_router, client):
        mock_router.post("/submissions/sub-1/request-more-info").mock(return_value=httpx.Response(200, json={
            "success": True, "message": "Info requested",
        }))
        result = await client.submissions.request_more_info("sub-1", "Please add GPS coordinates")
        assert result["success"] is True


# ---------------------------------------------------------------------------
# Workers resource
# ---------------------------------------------------------------------------

class TestWorkers:
    async def test_get(self, mock_router, client):
        mock_router.get("/workers/exec-1").mock(return_value=httpx.Response(200, json={
            "id": "exec-1", "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
            "name": "Alice",
        }))
        worker = await client.workers.get("exec-1")
        assert worker.name == "Alice"

    async def test_register(self, mock_router, client):
        mock_router.post("/workers/register").mock(return_value=httpx.Response(201, json={
            "id": "exec-1", "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        }))
        worker = await client.workers.register("0x1234567890abcdef1234567890abcdef12345678")
        assert worker.id == "exec-1"

    async def test_balance(self, mock_router, client):
        mock_router.get("/payments/balance/0xABC").mock(return_value=httpx.Response(200, json={
            "base": {"USDC": "10.50"}, "ethereum": {"USDC": "0.00"},
        }))
        result = await client.workers.balance("0xABC")
        assert "base" in result


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    async def test_401(self, mock_router, client):
        mock_router.get("/tasks").mock(return_value=httpx.Response(401, json={"message": "Bad key"}))
        with pytest.raises(EMAuthError) as exc:
            await client.tasks.list_page()
        assert exc.value.status_code == 401

    async def test_404(self, mock_router, client):
        mock_router.get("/tasks/nope").mock(return_value=httpx.Response(404, json={"message": "Not found"}))
        with pytest.raises(EMNotFoundError):
            await client.tasks.get("nope")

    async def test_422(self, mock_router, client):
        mock_router.post("/tasks").mock(return_value=httpx.Response(422, json={"message": "Invalid"}))
        params = CreateTaskParams(
            title="Test title here", instructions="x" * 20,
            category=TaskCategory.SIMPLE_ACTION, bounty_usd=0.01,
            deadline_hours=1, evidence_required=[EvidenceType.PHOTO],
        )
        with pytest.raises(EMValidationError):
            await client.tasks.create(params)

    async def test_500(self, mock_router, client):
        # With max_retries=2, respx needs 3 responses (initial + 2 retries)
        mock_router.get("/health").mock(side_effect=[
            httpx.Response(500, json={"message": "Error"}),
            httpx.Response(500, json={"message": "Error"}),
            httpx.Response(500, json={"message": "Error"}),
        ])
        with pytest.raises(EMServerError):
            await client.health()

    async def test_429(self, mock_router, client):
        mock_router.get("/tasks").mock(side_effect=[
            httpx.Response(429, json={"message": "Rate limited"}),
            httpx.Response(429, json={"message": "Rate limited"}),
            httpx.Response(429, json={"message": "Rate limited"}),
        ])
        with pytest.raises(EMError):
            await client.tasks.list_page()


# ---------------------------------------------------------------------------
# Retry behavior
# ---------------------------------------------------------------------------

class TestRetry:
    async def test_retry_recovers_on_second_attempt(self, mock_router):
        mock_router.get("/health").mock(side_effect=[
            httpx.Response(502, text="Bad Gateway"),
            httpx.Response(200, json={"status": "ok"}),
        ])
        async with EMClient(api_key=API_KEY, max_retries=2) as client:
            resp = await client.health()
            assert resp.status == "ok"

    async def test_no_retry_on_4xx(self, mock_router):
        route = mock_router.get("/tasks/x").mock(return_value=httpx.Response(404, json={"message": "Not found"}))
        async with EMClient(api_key=API_KEY, max_retries=2) as client:
            with pytest.raises(EMNotFoundError):
                await client.tasks.get("x")
        assert len(route.calls) == 1  # No retry on 404


# ---------------------------------------------------------------------------
# Client lifecycle
# ---------------------------------------------------------------------------

class TestLifecycle:
    async def test_context_manager(self, mock_router):
        mock_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        async with EMClient(api_key=API_KEY) as client:
            resp = await client.health()
            assert resp.status == "ok"

    async def test_custom_base_url(self):
        custom = "https://custom.example.com/v2"
        with respx.mock(base_url=custom) as router:
            router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
            async with EMClient(api_key=API_KEY, base_url=custom) as client:
                resp = await client.health()
                assert resp.status == "ok"
