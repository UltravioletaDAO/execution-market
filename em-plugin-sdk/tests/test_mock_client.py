"""Tests for MockEMClient — verifies it mirrors the real client API."""

import pytest

from em_plugin_sdk.testing import MockEMClient
from em_plugin_sdk import CreateTaskParams, SubmitEvidenceParams, RejectParams, TaskCategory, EvidenceType


class TestMockTasks:
    async def test_create(self):
        client = MockEMClient()
        params = CreateTaskParams(
            title="Test task title",
            instructions="Detailed instructions that are at least 20 chars long",
            category=TaskCategory.SIMPLE_ACTION,
            bounty_usd=1.0,
            deadline_hours=1,
            evidence_required=[EvidenceType.PHOTO],
        )
        task = await client.tasks.create(params)
        assert task.id == "mock-task-001"
        assert client.tasks._calls[0] == ("create", params)

    async def test_get(self):
        client = MockEMClient()
        task = await client.tasks.get("my-task")
        assert task.id == "my-task"

    async def test_list_page(self):
        client = MockEMClient()
        result = await client.tasks.list_page(status="published")
        assert result.total == 1

    async def test_list_iterate(self):
        client = MockEMClient()
        tasks = await client.tasks.list(status="published").collect()
        assert len(tasks) == 1

    async def test_cancel(self):
        client = MockEMClient()
        result = await client.tasks.cancel("t1")
        assert result["success"] is True

    async def test_assign(self):
        client = MockEMClient()
        result = await client.tasks.assign("t1", "e1")
        assert result["success"] is True

    async def test_apply(self):
        client = MockEMClient()
        app = await client.tasks.apply("t1", "e1")
        assert app.task_id == "t1"

    async def test_custom_response(self):
        client = MockEMClient()
        client.tasks._create_response = {
            "id": "custom-id",
            "title": "Custom",
            "status": "published",
            "category": "research",
            "bounty_usd": 99.0,
            "deadline": "2026-12-01T00:00:00Z",
            "created_at": "2026-01-01T00:00:00Z",
            "agent_id": "custom-agent",
        }
        params = CreateTaskParams(
            title="Custom task title",
            instructions="Instructions for the custom task here",
            category=TaskCategory.RESEARCH,
            bounty_usd=99.0,
            deadline_hours=24,
            evidence_required=[EvidenceType.TEXT_RESPONSE],
        )
        task = await client.tasks.create(params)
        assert task.id == "custom-id"
        assert task.bounty_usd == 99.0


class TestMockSubmissions:
    async def test_list(self):
        client = MockEMClient()
        result = await client.submissions.list("t1")
        assert result.count == 1

    async def test_submit(self):
        client = MockEMClient()
        params = SubmitEvidenceParams(executor_id="e1", evidence={"photo": "url"})
        sub = await client.submissions.submit("t1", params)
        assert sub.task_id == "t1"

    async def test_approve(self):
        client = MockEMClient()
        result = await client.submissions.approve("s1")
        assert result["success"] is True

    async def test_reject(self):
        client = MockEMClient()
        result = await client.submissions.reject("s1", RejectParams(notes="Bad evidence quality overall"))
        assert result["success"] is True


class TestMockWorkers:
    async def test_get(self):
        client = MockEMClient()
        worker = await client.workers.get("e1")
        assert worker.id == "e1"

    async def test_register(self):
        client = MockEMClient()
        worker = await client.workers.register("0x" + "ab" * 20, name="Alice")
        assert worker.name == "Alice"

    async def test_balance(self):
        client = MockEMClient()
        result = await client.workers.balance("0xABC")
        assert "base" in result


class TestMockTopLevel:
    async def test_health(self):
        client = MockEMClient()
        resp = await client.health()
        assert resp.status == "ok"

    async def test_config(self):
        client = MockEMClient()
        cfg = await client.config()
        assert cfg.preferred_network == "base"

    async def test_context_manager(self):
        async with MockEMClient() as client:
            resp = await client.health()
            assert resp.status == "ok"

    async def test_call_tracking(self):
        client = MockEMClient()
        await client.tasks.get("a")
        await client.tasks.get("b")
        await client.tasks.cancel("c")
        assert len(client.tasks._calls) == 3
        assert client.tasks._calls[0] == ("get", "a")
        assert client.tasks._calls[2] == ("cancel", "c")
