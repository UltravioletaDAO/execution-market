"""Tests for EMClient — all HTTP calls mocked via respx."""

import pytest
import httpx
import respx

from em_plugin_sdk import EMClient, EMAuthError, EMNotFoundError, EMValidationError, EMServerError, EMError
from em_plugin_sdk.models import (
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
# Auth header injection
# ---------------------------------------------------------------------------

class TestAuthHeaders:
    async def test_bearer_token_sent(self, mock_router, client):
        route = mock_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        await client.health()
        assert route.calls.last.request.headers["authorization"] == f"Bearer {API_KEY}"

    async def test_user_agent_sent(self, mock_router, client):
        route = mock_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        await client.health()
        assert "em-plugin-sdk" in route.calls.last.request.headers["user-agent"]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    async def test_health_ok(self, mock_router, client):
        mock_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok", "version": "1.0.0"}))
        resp = await client.health()
        assert resp.status == "ok"
        assert resp.version == "1.0.0"


# ---------------------------------------------------------------------------
# Tasks
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
    async def test_list_tasks(self, mock_router, client):
        mock_router.get("/tasks").mock(return_value=httpx.Response(200, json={
            "tasks": [TASK_JSON],
            "total": 1,
            "count": 1,
            "offset": 0,
            "has_more": False,
        }))
        result = await client.list_tasks(status="published", limit=10)
        assert result.total == 1
        assert result.tasks[0].id == "abc-123"

    async def test_list_tasks_params(self, mock_router, client):
        route = mock_router.get("/tasks").mock(return_value=httpx.Response(200, json={
            "tasks": [],
            "total": 0,
            "count": 0,
            "offset": 5,
            "has_more": False,
        }))
        await client.list_tasks(category="simple_action", offset=5)
        req = route.calls.last.request
        assert "category=simple_action" in str(req.url)
        assert "offset=5" in str(req.url)

    async def test_get_task(self, mock_router, client):
        mock_router.get("/tasks/abc-123").mock(return_value=httpx.Response(200, json=TASK_JSON))
        task = await client.get_task("abc-123")
        assert task.title == "Test task"
        assert task.bounty_usd == 0.10

    async def test_publish_task(self, mock_router, client):
        mock_router.post("/tasks").mock(return_value=httpx.Response(201, json=TASK_JSON))
        params = CreateTaskParams(
            title="Test task title here",
            instructions="Detailed instructions for the task that must be at least 20 chars",
            category=TaskCategory.SIMPLE_ACTION,
            bounty_usd=0.10,
            deadline_hours=1,
            evidence_required=[EvidenceType.PHOTO],
        )
        task = await client.publish_task(params)
        assert task.id == "abc-123"

    async def test_cancel_task(self, mock_router, client):
        mock_router.post("/tasks/abc-123/cancel").mock(return_value=httpx.Response(200, json={
            "success": True,
            "message": "Task cancelled",
        }))
        result = await client.cancel_task("abc-123", reason="No longer needed")
        assert result["success"] is True


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

APP_JSON = {
    "id": "app-1",
    "task_id": "abc-123",
    "executor_id": "exec-1",
    "message": "I can do this",
    "status": "pending",
    "created_at": "2026-03-20T00:00:00Z",
}


class TestApplications:
    async def test_apply_to_task(self, mock_router, client):
        mock_router.post("/tasks/abc-123/apply").mock(return_value=httpx.Response(201, json=APP_JSON))
        app = await client.apply_to_task("abc-123", "exec-1", message="I can do this")
        assert app.executor_id == "exec-1"

    async def test_list_applications(self, mock_router, client):
        mock_router.get("/tasks/abc-123/applications").mock(return_value=httpx.Response(200, json={
            "applications": [APP_JSON],
            "count": 1,
        }))
        result = await client.list_applications("abc-123")
        assert result.count == 1

    async def test_assign_task(self, mock_router, client):
        mock_router.post("/tasks/abc-123/assign").mock(return_value=httpx.Response(200, json={
            "success": True,
            "message": "Assigned",
        }))
        result = await client.assign_task("abc-123", "exec-1")
        assert result["success"] is True


# ---------------------------------------------------------------------------
# Submissions
# ---------------------------------------------------------------------------

SUB_JSON = {
    "id": "sub-1",
    "task_id": "abc-123",
    "executor_id": "exec-1",
    "status": "pending",
    "submitted_at": "2026-03-20T00:00:00Z",
    "evidence": {"photo": "https://cdn.example.com/photo.jpg"},
}


class TestSubmissions:
    async def test_submit_evidence(self, mock_router, client):
        mock_router.post("/tasks/abc-123/submit").mock(return_value=httpx.Response(201, json=SUB_JSON))
        params = SubmitEvidenceParams(
            executor_id="exec-1",
            evidence={"photo": "https://cdn.example.com/photo.jpg"},
        )
        sub = await client.submit_evidence("abc-123", params)
        assert sub.id == "sub-1"

    async def test_list_submissions(self, mock_router, client):
        mock_router.get("/tasks/abc-123/submissions").mock(return_value=httpx.Response(200, json={
            "submissions": [SUB_JSON],
            "count": 1,
        }))
        result = await client.list_submissions("abc-123")
        assert result.count == 1

    async def test_approve_submission(self, mock_router, client):
        mock_router.post("/submissions/sub-1/approve").mock(return_value=httpx.Response(200, json={
            "success": True,
            "message": "Approved",
        }))
        result = await client.approve_submission("sub-1", ApproveParams(notes="Good work"))
        assert result["success"] is True

    async def test_reject_submission(self, mock_router, client):
        mock_router.post("/submissions/sub-1/reject").mock(return_value=httpx.Response(200, json={
            "success": True,
            "message": "Rejected",
        }))
        result = await client.reject_submission(
            "sub-1",
            RejectParams(notes="Evidence is blurry and unusable"),
        )
        assert result["success"] is True


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

EXECUTOR_JSON = {
    "id": "exec-1",
    "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
    "name": "Test Worker",
}


class TestWorkers:
    async def test_get_executor(self, mock_router, client):
        mock_router.get("/workers/exec-1").mock(return_value=httpx.Response(200, json=EXECUTOR_JSON))
        executor = await client.get_executor("exec-1")
        assert executor.name == "Test Worker"

    async def test_register_worker(self, mock_router, client):
        mock_router.post("/workers/register").mock(return_value=httpx.Response(201, json=EXECUTOR_JSON))
        executor = await client.register_worker(
            wallet_address="0x1234567890abcdef1234567890abcdef12345678",
            name="Test Worker",
        )
        assert executor.id == "exec-1"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    async def test_401_raises_auth_error(self, mock_router, client):
        mock_router.get("/tasks").mock(return_value=httpx.Response(401, json={
            "error": "UNAUTHORIZED",
            "message": "Invalid API key",
        }))
        with pytest.raises(EMAuthError) as exc_info:
            await client.list_tasks()
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.message

    async def test_403_raises_auth_error(self, mock_router, client):
        mock_router.get("/tasks").mock(return_value=httpx.Response(403, json={
            "error": "FORBIDDEN",
            "message": "Access denied",
        }))
        with pytest.raises(EMAuthError):
            await client.list_tasks()

    async def test_404_raises_not_found(self, mock_router, client):
        mock_router.get("/tasks/nonexistent").mock(return_value=httpx.Response(404, json={
            "error": "TASK_NOT_FOUND",
            "message": "Task not found",
        }))
        with pytest.raises(EMNotFoundError) as exc_info:
            await client.get_task("nonexistent")
        assert exc_info.value.status_code == 404

    async def test_422_raises_validation_error(self, mock_router, client):
        mock_router.post("/tasks").mock(return_value=httpx.Response(422, json={
            "error": "VALIDATION_ERROR",
            "message": "bounty_usd must be > 0",
        }))
        params = CreateTaskParams(
            title="Test task title here",
            instructions="Detailed instructions for the task that must be at least 20 chars",
            category=TaskCategory.SIMPLE_ACTION,
            bounty_usd=0.01,
            deadline_hours=1,
            evidence_required=[EvidenceType.PHOTO],
        )
        with pytest.raises(EMValidationError):
            await client.publish_task(params)

    async def test_500_raises_server_error(self, mock_router, client):
        mock_router.get("/health").mock(return_value=httpx.Response(500, json={
            "message": "Internal server error",
        }))
        with pytest.raises(EMServerError) as exc_info:
            await client.health()
        assert exc_info.value.status_code == 500

    async def test_502_raises_server_error(self, mock_router, client):
        mock_router.get("/health").mock(return_value=httpx.Response(502, text="Bad Gateway"))
        with pytest.raises(EMServerError) as exc_info:
            await client.health()
        assert exc_info.value.status_code == 502

    async def test_429_raises_generic_error(self, mock_router, client):
        mock_router.get("/tasks").mock(return_value=httpx.Response(429, json={
            "message": "Rate limited",
        }))
        with pytest.raises(EMError) as exc_info:
            await client.list_tasks()
        assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# Client lifecycle
# ---------------------------------------------------------------------------

class TestClientLifecycle:
    async def test_context_manager(self, mock_router):
        mock_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        async with EMClient(api_key=API_KEY) as client:
            resp = await client.health()
            assert resp.status == "ok"

    async def test_custom_base_url(self, mock_router):
        custom_url = "https://custom.api.example.com/v2"
        with respx.mock(base_url=custom_url) as custom_router:
            custom_router.get("/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
            async with EMClient(api_key=API_KEY, base_url=custom_url) as client:
                resp = await client.health()
                assert resp.status == "ok"

    async def test_custom_timeout(self):
        client = EMClient(api_key=API_KEY, timeout=5.0)
        assert client._timeout == 5.0
        await client.close()
