"""H2H executor-type enforcement on the REST apply path (Task 5.3 / F-08).

When a task targets human executors (services catalog / Rappi-style H2H,
``target_executor_type == "human"``), ``POST /tasks/{id}/apply`` must reject a
non-human (agent/robot) executor with 403 and let a human through. This mirrors
the MCP accept-path guard so the REST surface cannot be used to bypass it.

The DB layer is mocked: ``db.get_task`` returns the target task,
``db.get_client().table("executors")`` returns the applicant's ``executor_type``,
and ``db.apply_to_task`` is only expected to run for the allowed (human) case.
World ID eligibility and the World-AgentKit lookup are stubbed so the test
isolates the executor-type gate.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.core

TASK_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EXECUTOR_ID = "12345678-1234-1234-1234-1234567890ab"


class _FakeQueryResult:
    def __init__(self, data=None):
        self.data = data if data is not None else []

    def select(self, *a, **kw):
        return self

    def eq(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

    def single(self):
        return self

    def execute(self):
        return self


class _FakeTable:
    def __init__(self, data=None):
        self._data = data if data is not None else []

    def select(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def update(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def eq(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def limit(self, *a, **kw):
        return _FakeQueryResult(self._data)


class _FakeClient:
    def __init__(self, tables=None):
        self._tables = tables or {}

    def table(self, name):
        return self._tables.get(name, _FakeTable())


def _apply_app():
    """Minimal app with the workers router. FIX-P1-01 made worker identity
    resolution fail-closed, so we supply an authenticated WorkerAuth principal
    matching the body executor_id (the executor-type gate is the subject under
    test, not the auth layer)."""
    from fastapi import FastAPI
    from api.routers.workers import router
    from api.auth import verify_worker_auth, WorkerAuth

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_worker_auth] = lambda: WorkerAuth(
        executor_id=EXECUTOR_ID, auth_method="jwt"
    )
    return app


def _client(app):
    from fastapi.testclient import TestClient

    try:
        return TestClient(app, raise_server_exceptions=False)
    except TypeError:
        pytest.skip("httpx/starlette TestClient incompatibility")


def _mock_db(applicant_type: str):
    """A db mock for the H2H apply path with a fixed task + applicant type."""
    mock_db = MagicMock()
    mock_db.get_task = AsyncMock(
        return_value={
            "id": TASK_ID,
            "target_executor_type": "human",
            "bounty_usd": 10.0,
            "payment_network": "base",
            "agent_id": "agent-publisher",
        }
    )
    mock_db.get_executor_stats = AsyncMock(
        return_value={"wallet_address": "0x" + "33" * 20}
    )
    mock_db.get_client.return_value = _FakeClient(
        tables={"executors": _FakeTable(data=[{"executor_type": applicant_type}])}
    )
    mock_db.apply_to_task = AsyncMock(
        return_value={
            "application": {"id": "application-1"},
            "task": {"agent_id": "agent-publisher"},
        }
    )
    return mock_db


def _patches(mock_db):
    """Common patches: db, World ID eligibility (allow), World-AgentKit (off)."""
    fake_platform_config = MagicMock()
    fake_platform_config.get = AsyncMock(return_value=False)  # world_agentkit off
    return (
        patch("api.routers.workers.db", mock_db),
        patch(
            "integrations.worldid.enforcement.check_world_id_eligibility",
            new=AsyncMock(return_value=(True, None)),
        ),
        patch("config.platform_config.PlatformConfig", fake_platform_config),
    )


def test_agent_executor_rejected_from_human_task():
    """target_executor_type='human' + agent applicant -> 403, apply not run."""
    app = _apply_app()
    mock_db = _mock_db(applicant_type="agent")
    p_db, p_wid, p_cfg = _patches(mock_db)

    with p_db, p_wid, p_cfg:
        resp = _client(app).post(
            f"/api/v1/tasks/{TASK_ID}/apply",
            json={"executor_id": EXECUTOR_ID, "message": "I can do it"},
        )

    assert resp.status_code == 403, resp.text
    assert "human" in resp.json()["detail"].lower()
    mock_db.apply_to_task.assert_not_called()


def test_robot_executor_rejected_from_human_task():
    """A non-human, non-agent type (robot) is also rejected from a human task."""
    app = _apply_app()
    mock_db = _mock_db(applicant_type="robot")
    p_db, p_wid, p_cfg = _patches(mock_db)

    with p_db, p_wid, p_cfg:
        resp = _client(app).post(
            f"/api/v1/tasks/{TASK_ID}/apply",
            json={"executor_id": EXECUTOR_ID},
        )

    assert resp.status_code == 403, resp.text
    mock_db.apply_to_task.assert_not_called()


def test_human_executor_allowed_on_human_task():
    """target_executor_type='human' + human applicant -> gate passes; the apply
    reaches db.apply_to_task."""
    app = _apply_app()
    mock_db = _mock_db(applicant_type="human")
    p_db, p_wid, p_cfg = _patches(mock_db)

    with p_db, p_wid, p_cfg:
        resp = _client(app).post(
            f"/api/v1/tasks/{TASK_ID}/apply",
            json={"executor_id": EXECUTOR_ID, "message": "On my way"},
        )

    # The H2H gate must not reject a human; the apply path runs.
    assert resp.status_code != 403, resp.text
    mock_db.apply_to_task.assert_awaited_once()
