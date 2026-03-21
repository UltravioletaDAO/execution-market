"""
Tests for A2A Protocol Integration

Tests the A2A JSON-RPC endpoint, task manager, and data models.
"""

import pytest
from unittest.mock import patch


# ============== MODEL TESTS ==============


class TestA2AModels:
    """Test A2A protocol data models."""

    def test_task_state_enum(self):
        from a2a.models import A2ATaskState

        assert A2ATaskState.SUBMITTED == "submitted"
        assert A2ATaskState.WORKING == "working"
        assert A2ATaskState.INPUT_REQUIRED == "input-required"
        assert A2ATaskState.COMPLETED == "completed"
        assert A2ATaskState.FAILED == "failed"
        assert A2ATaskState.CANCELED == "canceled"

    def test_em_status_mapping(self):
        from a2a.models import em_status_to_a2a, A2ATaskState

        assert em_status_to_a2a("published") == A2ATaskState.SUBMITTED
        assert em_status_to_a2a("accepted") == A2ATaskState.WORKING
        assert em_status_to_a2a("in_progress") == A2ATaskState.WORKING
        assert em_status_to_a2a("submitted") == A2ATaskState.INPUT_REQUIRED
        assert em_status_to_a2a("verifying") == A2ATaskState.INPUT_REQUIRED
        assert em_status_to_a2a("completed") == A2ATaskState.COMPLETED
        assert em_status_to_a2a("expired") == A2ATaskState.FAILED
        assert em_status_to_a2a("cancelled") == A2ATaskState.CANCELED
        assert em_status_to_a2a("unknown_state") == A2ATaskState.UNKNOWN

    def test_em_status_mapping_case_insensitive(self):
        from a2a.models import em_status_to_a2a, A2ATaskState

        assert em_status_to_a2a("PUBLISHED") == A2ATaskState.SUBMITTED
        assert em_status_to_a2a("Completed") == A2ATaskState.COMPLETED
        assert em_status_to_a2a("  cancelled  ") == A2ATaskState.CANCELED

    def test_text_part(self):
        from a2a.models import TextPart

        part = TextPart(text="Hello world")
        assert part.kind == "text"
        assert part.text == "Hello world"

    def test_file_part_with_uri(self):
        from a2a.models import FilePart

        part = FilePart(mimeType="image/jpeg", uri="https://example.com/photo.jpg")
        assert part.kind == "file"
        assert part.uri == "https://example.com/photo.jpg"
        assert part.data is None

    def test_file_part_with_data(self):
        from a2a.models import FilePart

        part = FilePart(mimeType="image/png", data="base64encodeddata==")
        assert part.data == "base64encodeddata=="
        assert part.uri is None

    def test_data_part(self):
        from a2a.models import DataPart

        part = DataPart(data={"lat": 25.76, "lng": -80.19})
        assert part.kind == "data"
        assert part.data["lat"] == 25.76

    def test_parse_part_text(self):
        from a2a.models import parse_part, TextPart

        part = parse_part({"kind": "text", "text": "hello"})
        assert isinstance(part, TextPart)
        assert part.text == "hello"

    def test_parse_part_file(self):
        from a2a.models import parse_part, FilePart

        part = parse_part(
            {"kind": "file", "mimeType": "image/jpeg", "uri": "https://x.com/img.jpg"}
        )
        assert isinstance(part, FilePart)

    def test_parse_part_data(self):
        from a2a.models import parse_part, DataPart

        part = parse_part({"kind": "data", "data": {"key": "value"}})
        assert isinstance(part, DataPart)

    def test_parse_part_default_text(self):
        from a2a.models import parse_part, TextPart

        part = parse_part({"text": "no kind specified"})
        assert isinstance(part, TextPart)

    def test_message(self):
        from a2a.models import Message, TextPart

        msg = Message(
            role="user",
            parts=[TextPart(text="Verify store is open")],
        )
        assert msg.role == "user"
        assert len(msg.parts) == 1

    def test_artifact(self):
        from a2a.models import Artifact, TextPart, FilePart

        artifact = Artifact(
            name="evidence_0",
            description="Worker photo evidence",
            parts=[
                TextPart(text="Store verified open at 2pm"),
                FilePart(mimeType="image/jpeg", uri="https://cdn.em/photo1.jpg"),
            ],
            index=0,
            lastChunk=True,
        )
        assert len(artifact.parts) == 2
        assert artifact.lastChunk is True

    def test_task_status(self):
        from a2a.models import A2ATaskStatus, A2ATaskState, Message, TextPart

        status = A2ATaskStatus(
            state=A2ATaskState.SUBMITTED,
            message=Message(role="agent", parts=[TextPart(text="Task created")]),
            timestamp="2026-02-12T04:00:00Z",
        )
        assert status.state == A2ATaskState.SUBMITTED

    def test_a2a_task(self):
        from a2a.models import A2ATask, A2ATaskStatus, A2ATaskState, Message, TextPart

        task = A2ATask(
            id="task-123",
            contextId="agent-456",
            status=A2ATaskStatus(
                state=A2ATaskState.SUBMITTED,
                message=Message(role="agent", parts=[TextPart(text="Created")]),
                timestamp="2026-02-12T04:00:00Z",
            ),
            metadata={"em_task_id": "task-123", "bounty_usd": 2.50},
        )
        assert task.id == "task-123"
        assert task.metadata["bounty_usd"] == 2.50

    def test_a2a_task_serialization(self):
        from a2a.models import A2ATask, A2ATaskStatus, A2ATaskState

        task = A2ATask(
            id="task-abc",
            status=A2ATaskStatus(
                state=A2ATaskState.WORKING,
                timestamp="2026-02-12T04:00:00Z",
            ),
        )
        data = task.model_dump(exclude_none=True)
        assert "id" in data
        assert data["status"]["state"] == "working"
        assert "artifacts" not in data  # excluded when None

    def test_jsonrpc_error_codes(self):
        from a2a.models import JSONRPCError

        assert JSONRPCError.PARSE_ERROR == -32700
        assert JSONRPCError.METHOD_NOT_FOUND == -32601
        assert JSONRPCError.TASK_NOT_FOUND == -32001

    def test_jsonrpc_error_make(self):
        from a2a.models import JSONRPCError

        err = JSONRPCError.make(-32001, "Not found", {"task_id": "abc"})
        assert err["code"] == -32001
        assert err["message"] == "Not found"
        assert err["data"]["task_id"] == "abc"

    def test_jsonrpc_error_make_no_data(self):
        from a2a.models import JSONRPCError

        err = JSONRPCError.make(-32601, "Method not found")
        assert "data" not in err

    def test_now_iso_format(self):
        from a2a.models import now_iso

        ts = now_iso()
        assert "T" in ts  # ISO format
        assert "+" in ts or "Z" in ts or ts.endswith("+00:00")  # has timezone


# ============== TASK MANAGER TESTS ==============


class TestA2ATaskManager:
    """Test the A2A task manager."""

    def test_extract_task_params_text(self):
        from a2a.task_manager import _extract_task_params
        from a2a.models import Message, TextPart

        msg = Message(
            role="user",
            parts=[TextPart(text="Verify store is open\nAt 123 Main St, check hours")],
        )
        params = _extract_task_params(msg)
        assert params["title"] == "Verify store is open"
        assert "123 Main St" in params["description"]

    def test_extract_task_params_structured(self):
        from a2a.task_manager import _extract_task_params
        from a2a.models import Message, DataPart

        msg = Message(
            role="user",
            parts=[
                DataPart(
                    data={
                        "title": "Photo verification",
                        "description": "Take a photo of the storefront",
                        "bounty_usd": 5.00,
                        "category": "physical_presence",
                        "evidence_required": ["photo_geo"],
                        "deadline_hours": 48,
                    }
                )
            ],
        )
        params = _extract_task_params(msg)
        assert params["title"] == "Photo verification"
        assert params["bounty_usd"] == 5.00
        assert params["category"] == "physical_presence"
        assert params["evidence_required"] == ["photo_geo"]
        assert params["deadline_hours"] == 48

    def test_extract_task_params_mixed(self):
        from a2a.task_manager import _extract_task_params
        from a2a.models import Message, TextPart, DataPart

        msg = Message(
            role="user",
            parts=[
                TextPart(text="Please complete this task"),
                DataPart(
                    data={
                        "title": "Store verification",
                        "bounty_usd": 2.50,
                    }
                ),
            ],
        )
        params = _extract_task_params(msg)
        # DataPart title takes precedence
        assert params["title"] == "Store verification"
        assert params["bounty_usd"] == 2.50

    def test_extract_task_params_defaults(self):
        from a2a.task_manager import _extract_task_params
        from a2a.models import Message, TextPart

        msg = Message(
            role="user",
            parts=[TextPart(text="Do something")],
        )
        params = _extract_task_params(msg)
        assert params["bounty_usd"] == 1.00
        assert params["category"] == "simple_action"
        assert params["evidence_required"] == ["text_response"]
        assert params["deadline_hours"] == 24

    def test_extract_task_params_extra_metadata(self):
        from a2a.task_manager import _extract_task_params
        from a2a.models import Message, DataPart

        msg = Message(
            role="user",
            parts=[
                DataPart(
                    data={
                        "title": "Test",
                        "custom_field": "custom_value",
                        "priority": "high",
                    }
                )
            ],
        )
        params = _extract_task_params(msg)
        assert params["metadata"]["custom_field"] == "custom_value"
        assert params["metadata"]["priority"] == "high"

    def test_extract_task_params_bounty_alias(self):
        """Test that 'bounty' (without _usd) also works."""
        from a2a.task_manager import _extract_task_params
        from a2a.models import Message, DataPart

        msg = Message(
            role="user",
            parts=[DataPart(data={"title": "Test", "bounty": 3.50})],
        )
        params = _extract_task_params(msg)
        assert params["bounty_usd"] == 3.50

    def test_extract_task_params_long_title_truncated(self):
        from a2a.task_manager import _extract_task_params
        from a2a.models import Message, TextPart

        msg = Message(
            role="user",
            parts=[TextPart(text="A" * 300)],
        )
        params = _extract_task_params(msg)
        assert len(params["title"]) <= 200

    def test_em_task_to_a2a_published(self):
        from a2a.task_manager import _em_task_to_a2a
        from a2a.models import A2ATaskState

        em_task = {
            "id": "task-001",
            "title": "Verify store",
            "status": "published",
            "bounty_usd": 2.50,
            "agent_id": "agent-123",
            "created_at": "2026-02-12T04:00:00Z",
            "updated_at": "2026-02-12T04:00:00Z",
        }
        a2a_task = _em_task_to_a2a(em_task)
        assert a2a_task.id == "task-001"
        assert a2a_task.status.state == A2ATaskState.SUBMITTED
        assert "Verify store" in a2a_task.status.message.parts[0].text
        assert a2a_task.metadata["bounty_usd"] == 2.50

    def test_em_task_to_a2a_completed(self):
        from a2a.task_manager import _em_task_to_a2a
        from a2a.models import A2ATaskState

        em_task = {
            "id": "task-002",
            "title": "Photo task",
            "status": "completed",
            "bounty_usd": 5.00,
            "created_at": "2026-02-12T04:00:00Z",
            "updated_at": "2026-02-12T05:00:00Z",
        }
        a2a_task = _em_task_to_a2a(em_task)
        assert a2a_task.status.state == A2ATaskState.COMPLETED
        assert "completed" in a2a_task.status.message.parts[0].text.lower()

    def test_em_task_to_a2a_with_submissions(self):
        from a2a.task_manager import _em_task_to_a2a

        em_task = {
            "id": "task-003",
            "title": "Store check",
            "status": "submitted",
            "bounty_usd": 1.00,
            "created_at": "2026-02-12T04:00:00Z",
            "submissions": [
                {
                    "evidence_text": "Store is open, verified at 2pm",
                    "photos": ["https://cdn.em/photo1.jpg"],
                    "gps": {"lat": 25.76, "lng": -80.19, "accuracy": 5},
                    "submitted_at": "2026-02-12T04:30:00Z",
                }
            ],
        }
        a2a_task = _em_task_to_a2a(em_task)
        assert a2a_task.artifacts is not None
        assert len(a2a_task.artifacts) == 1
        artifact = a2a_task.artifacts[0]
        assert len(artifact.parts) == 3  # text + file + data(gps)

    def test_em_task_to_a2a_with_history(self):
        from a2a.task_manager import _em_task_to_a2a

        em_task = {
            "id": "task-004",
            "title": "Test task",
            "description": "A test",
            "status": "completed",
            "created_at": "2026-02-12T04:00:00Z",
            "status_history": [
                {
                    "type": "status_change",
                    "message": "Worker assigned",
                    "timestamp": "2026-02-12T04:10:00Z",
                },
            ],
        }
        a2a_task = _em_task_to_a2a(em_task, include_history=True)
        assert a2a_task.history is not None
        assert len(a2a_task.history) >= 2  # creation + status change

    def test_em_task_to_a2a_strips_none_metadata(self):
        from a2a.task_manager import _em_task_to_a2a

        em_task = {
            "id": "task-005",
            "title": "Minimal",
            "status": "published",
            "created_at": "2026-02-12T04:00:00Z",
        }
        a2a_task = _em_task_to_a2a(em_task)
        # None values should be stripped from metadata
        assert "worker_id" not in a2a_task.metadata
        assert "location" not in a2a_task.metadata

    @pytest.mark.asyncio
    async def test_create_task(self):
        from a2a.task_manager import A2ATaskManager
        from a2a.models import Message, TextPart, A2ATaskState

        manager = A2ATaskManager(agent_id="test-agent")
        msg = Message(
            role="user",
            parts=[TextPart(text="Verify coffee shop is open")],
        )

        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.create_task.return_value = {
                "id": "new-task-123",
                "title": "Verify coffee shop is open",
                "status": "published",
                "bounty_usd": 1.00,
                "agent_id": "test-agent",
                "created_at": "2026-02-12T04:00:00Z",
                "updated_at": "2026-02-12T04:00:00Z",
            }

            result = await manager.create_task(msg)

        assert result.id == "new-task-123"
        assert result.status.state == A2ATaskState.SUBMITTED

    @pytest.mark.asyncio
    async def test_get_task_found(self):
        from a2a.task_manager import A2ATaskManager
        from a2a.models import A2ATaskState

        manager = A2ATaskManager(agent_id="test-agent")

        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.get_task.return_value = {
                "id": "task-xyz",
                "title": "Test",
                "status": "in_progress",
                "agent_id": "test-agent",
                "bounty_usd": 3.00,
                "created_at": "2026-02-12T04:00:00Z",
            }

            result = await manager.get_task("task-xyz")

        assert result is not None
        assert result.status.state == A2ATaskState.WORKING

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        from a2a.task_manager import A2ATaskManager

        manager = A2ATaskManager()

        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.get_task.return_value = None
            result = await manager.get_task("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_task_success(self):
        from a2a.task_manager import A2ATaskManager
        from a2a.models import A2ATaskState

        manager = A2ATaskManager(agent_id="test-agent")

        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.get_task.return_value = {
                "id": "task-cancel",
                "title": "Cancel me",
                "status": "published",
                "agent_id": "test-agent",
                "created_at": "2026-02-12T04:00:00Z",
            }
            mock_db.update_task.return_value = None

            result = await manager.cancel_task("task-cancel")

        assert result is not None
        assert result.status.state == A2ATaskState.CANCELED

    @pytest.mark.asyncio
    async def test_cancel_task_not_cancellable(self):
        from a2a.task_manager import A2ATaskManager

        manager = A2ATaskManager(agent_id="test-agent")

        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.get_task.return_value = {
                "id": "task-done",
                "title": "Already done",
                "status": "completed",
                "agent_id": "test-agent",
                "created_at": "2026-02-12T04:00:00Z",
            }

            result = await manager.cancel_task("task-done")

        assert result is None

    @pytest.mark.asyncio
    async def test_cancel_task_wrong_agent(self):
        from a2a.task_manager import A2ATaskManager

        manager = A2ATaskManager(agent_id="other-agent")

        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.get_task.return_value = {
                "id": "task-notmine",
                "title": "Not mine",
                "status": "published",
                "agent_id": "real-owner",
                "created_at": "2026-02-12T04:00:00Z",
            }

            result = await manager.cancel_task("task-notmine")

        assert result is None


# ============== JSON-RPC ROUTER TESTS ==============


class TestA2AJSONRPCRouter:
    """Test the A2A JSON-RPC endpoint."""

    @pytest.fixture
    def client(self):
        """Create a test client for the A2A router."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from a2a.jsonrpc_router import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_health_endpoint(self, client):
        resp = client.get("/a2a/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["protocol"] == "A2A"
        assert "message/send" in data["methods"]

    def test_invalid_json(self, client):
        resp = client.post(
            "/a2a/v1",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["error"]["code"] == -32700  # PARSE_ERROR

    def test_invalid_jsonrpc_version(self, client):
        resp = client.post(
            "/a2a/v1",
            json={
                "jsonrpc": "1.0",
                "id": 1,
                "method": "message/send",
            },
        )
        data = resp.json()
        assert data["error"]["code"] == -32600  # INVALID_REQUEST

    def test_missing_method(self, client):
        resp = client.post(
            "/a2a/v1",
            json={
                "jsonrpc": "2.0",
                "id": 1,
            },
        )
        data = resp.json()
        assert data["error"]["code"] == -32600

    def test_unknown_method(self, client):
        resp = client.post(
            "/a2a/v1",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "nonexistent/method",
            },
        )
        data = resp.json()
        assert data["error"]["code"] == -32601  # METHOD_NOT_FOUND

    def test_message_send_missing_message(self, client):
        resp = client.post(
            "/a2a/v1",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "message/send",
                "params": {},
            },
        )
        data = resp.json()
        assert data["error"]["code"] == -32602  # INVALID_PARAMS

    def test_tasks_get_missing_id(self, client):
        resp = client.post(
            "/a2a/v1",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/get",
                "params": {},
            },
        )
        data = resp.json()
        assert data["error"]["code"] == -32602

    def test_tasks_cancel_missing_id(self, client):
        resp = client.post(
            "/a2a/v1",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tasks/cancel",
                "params": {},
            },
        )
        data = resp.json()
        assert data["error"]["code"] == -32602

    def test_message_send_creates_task(self, client):
        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.create_task.return_value = {
                "id": "task-new",
                "title": "Verify store",
                "status": "published",
                "bounty_usd": 1.00,
                "created_at": "2026-02-12T04:00:00Z",
                "updated_at": "2026-02-12T04:00:00Z",
            }

            resp = client.post(
                "/a2a/v1",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [{"kind": "text", "text": "Verify store"}],
                        },
                    },
                },
            )

        data = resp.json()
        assert data["id"] == 1
        assert data["result"]["id"] == "task-new"
        assert data["result"]["status"]["state"] == "submitted"

    def test_tasks_get_returns_task(self, client):
        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.get_task.return_value = {
                "id": "task-123",
                "title": "Working task",
                "status": "in_progress",
                "bounty_usd": 3.00,
                "created_at": "2026-02-12T04:00:00Z",
                "updated_at": "2026-02-12T04:30:00Z",
            }

            resp = client.post(
                "/a2a/v1",
                json={
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tasks/get",
                    "params": {"id": "task-123"},
                },
            )

        data = resp.json()
        assert data["result"]["status"]["state"] == "working"

    def test_batch_request(self, client):
        with patch("a2a.jsonrpc_router._dispatch") as mock_dispatch:
            mock_dispatch.return_value = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {"status": "ok"},
            }

            resp = client.post(
                "/a2a/v1",
                json=[
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tasks/get",
                        "params": {"id": "a"},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tasks/get",
                        "params": {"id": "b"},
                    },
                ],
            )

        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_empty_batch_request(self, client):
        resp = client.post("/a2a/v1", json=[])
        data = resp.json()
        assert data["error"]["code"] == -32600

    def test_non_object_request(self, client):
        resp = client.post("/a2a/v1", json="not an object")
        data = resp.json()
        assert data["error"]["code"] == -32600

    def test_response_preserves_request_id(self, client):
        resp = client.post(
            "/a2a/v1",
            json={
                "jsonrpc": "2.0",
                "id": "custom-id-42",
                "method": "nonexistent/method",
            },
        )
        data = resp.json()
        assert data["id"] == "custom-id-42"

    def test_response_preserves_null_id(self, client):
        resp = client.post(
            "/a2a/v1",
            json={
                "jsonrpc": "2.0",
                "id": None,
                "method": "nonexistent/method",
            },
        )
        data = resp.json()
        assert data["id"] is None

    def test_auth_extraction_api_key(self, client):
        """Test that X-API-Key header is extracted and task returned."""
        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.get_task.return_value = {
                "id": "t1",
                "title": "Auth test",
                "status": "published",
                "bounty_usd": 1.0,
                "created_at": "2026-02-12T04:00:00Z",
            }

            resp = client.post(
                "/a2a/v1",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tasks/get",
                    "params": {"id": "t1"},
                },
                headers={"X-API-Key": "test-key-12345678"},
            )

        data = resp.json()
        assert "result" in data
        assert data["result"]["id"] == "t1"

    def test_auth_extraction_bearer(self, client):
        """Test that Authorization Bearer header is extracted."""
        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.get_task.return_value = {
                "id": "t1",
                "title": "Auth test",
                "status": "published",
                "bounty_usd": 1.0,
                "created_at": "2026-02-12T04:00:00Z",
            }

            resp = client.post(
                "/a2a/v1",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tasks/get",
                    "params": {"id": "t1"},
                },
                headers={"Authorization": "Bearer mytoken12345"},
            )

        data = resp.json()
        assert "result" in data

    def test_auth_extraction_erc8004(self, client):
        """Test that ERC-8004 agent ID header is extracted."""
        with patch("a2a.task_manager.db", create=True) as mock_db:
            mock_db.get_task.return_value = {
                "id": "t1",
                "title": "Auth test",
                "status": "published",
                "agent_id": "erc8004:469",
                "bounty_usd": 1.0,
                "created_at": "2026-02-12T04:00:00Z",
            }

            resp = client.post(
                "/a2a/v1",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tasks/get",
                    "params": {"id": "t1"},
                },
                headers={"X-ERC8004-Agent-Id": "469"},
            )

        data = resp.json()
        assert "result" in data


# ============== AGENT CARD TESTS ==============


class TestAgentCard:
    """Test Agent Card generation and endpoints."""

    def test_agent_card_generation(self):
        from a2a.agent_card import get_agent_card

        card = get_agent_card("https://test.example.com")
        assert card.name == "Execution Market"
        assert "Universal Execution Layer" in card.description
        assert card.protocol_version == "0.3.0"
        assert len(card.skills) > 0

    def test_agent_card_serialization(self):
        from a2a.agent_card import get_agent_card

        card = get_agent_card("https://test.example.com")
        data = card.to_dict()

        assert data["protocolVersion"] == "0.3.0"
        assert data["name"] == "Execution Market"
        assert "skills" in data
        assert len(data["skills"]) >= 5
        assert "securitySchemes" in data
        assert "bearer" in data["securitySchemes"]

    def test_agent_card_skills_have_required_fields(self):
        from a2a.agent_card import get_agent_card

        card = get_agent_card("https://test.example.com")
        for skill in card.skills:
            data = skill.to_dict()
            assert "id" in data
            assert "name" in data
            assert "description" in data
            assert "tags" in data
            assert len(data["tags"]) > 0

    def test_agent_card_url_normalization(self):
        from a2a.agent_card import _normalize_base_url

        assert _normalize_base_url("https://api.em.com/") == "https://api.em.com"
        assert (
            _normalize_base_url("http://remote.host.com") == "https://remote.host.com"
        )
        assert _normalize_base_url("http://localhost:8000") == "http://localhost:8000"
        assert _normalize_base_url("") == "https://api.execution.market"

    def test_agent_card_endpoint(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from a2a.agent_card import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.get("/.well-known/agent.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Execution Market"
        assert "X-A2A-Protocol-Version" in resp.headers

    def test_discovery_endpoint(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from a2a.agent_card import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        resp = client.get("/discovery/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["agents"]) == 1
