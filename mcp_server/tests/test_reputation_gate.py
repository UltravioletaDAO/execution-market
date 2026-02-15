"""Tests for reputation gate enforcement on apply_to_task and assign_task.

Verifies boundary conditions: score=49 vs min=50, score=50 vs min=50,
default min_reputation=0, and cascading effects after reputation changes.
"""

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import supabase_client as sbc

pytestmark = [pytest.mark.core, pytest.mark.erc8004]


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

TASK_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EXECUTOR_ID = "11111111-2222-3333-4444-555555555555"


def _make_task(min_reputation=0, status="published"):
    return {
        "id": TASK_ID,
        "agent_id": "agent_test",
        "status": status,
        "bounty_usd": 0.10,
        "min_reputation": min_reputation,
    }


def _make_executor(reputation_score=80):
    return {
        "id": EXECUTOR_ID,
        "wallet_address": "0xWorker",
        "reputation_score": reputation_score,
        "name": "Test Worker",
    }


class _MockChainQuery:
    """Chainable mock Supabase query returning a single executor."""

    def __init__(self, executor_data=None, apps_data=None, fail_single=False):
        self._executor_data = executor_data
        self._apps_data = apps_data
        self._fail_single = fail_single
        self._table = None
        self._inserting = False
        self._insert_data = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, *_a, **_kw):
        return self

    def single(self):
        if self._fail_single:
            raise Exception("not found")
        return self

    def execute(self):
        if self._inserting:
            return SimpleNamespace(
                data=[{"id": "app-mock-123", **(self._insert_data or {})}]
            )
        if self._table == "executors":
            return SimpleNamespace(data=self._executor_data)
        elif self._table in ("task_applications", "applications"):
            return SimpleNamespace(data=self._apps_data or [])
        elif self._table == "tasks":
            return SimpleNamespace(
                data=[self._executor_data] if self._executor_data else []
            )
        return SimpleNamespace(data=[])

    def insert(self, data):
        self._inserting = True
        self._insert_data = data
        return self

    def update(self, _data):
        return self


class _MockClient:
    """Supabase client mock for reputation gate tests."""

    def __init__(self, executor_data=None, apps_data=None, fail_single=False):
        self._executor_data = executor_data
        self._apps_data = apps_data
        self._fail_single = fail_single

    def table(self, name):
        q = _MockChainQuery(
            executor_data=self._executor_data,
            apps_data=self._apps_data,
            fail_single=self._fail_single,
        )
        q._table = name
        return q


# ---------------------------------------------------------------------------
# apply_to_task tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_score_49_vs_min_50_rejected(monkeypatch):
    """Worker with score 49 applying to task with min_reputation=50 should be rejected."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=50))
    )
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=49)),
    )

    with pytest.raises(
        Exception, match="Insufficient reputation.*Required: 50.*yours: 49"
    ):
        await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)


@pytest.mark.asyncio
async def test_apply_score_50_vs_min_50_allowed(monkeypatch):
    """Worker with score 50 applying to task with min_reputation=50 should be allowed."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=50))
    )

    mock_client = _MockClient(executor_data=_make_executor(reputation_score=50))
    monkeypatch.setattr(sbc, "get_client", lambda: mock_client)

    # apply_to_task should NOT raise — score exactly meets minimum
    # It will try to insert application and return
    result = await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)
    # If it gets past reputation check, result should have application data
    assert result is not None


@pytest.mark.asyncio
async def test_apply_score_51_vs_min_50_allowed(monkeypatch):
    """Worker with score 51 applying to task with min_reputation=50 should be allowed."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=50))
    )
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=51)),
    )

    result = await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)
    assert result is not None


@pytest.mark.asyncio
async def test_apply_score_0_vs_min_0_allowed(monkeypatch):
    """Worker with score 0 applying to task with default min_reputation=0 should be allowed."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=0))
    )
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=0)),
    )

    result = await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)
    assert result is not None


@pytest.mark.asyncio
async def test_apply_no_min_reputation_field_defaults_to_zero(monkeypatch):
    """Task without min_reputation field should default to 0 (anyone can apply)."""
    task = _make_task()
    del task["min_reputation"]  # Remove the field entirely
    monkeypatch.setattr(sbc, "get_task", AsyncMock(return_value=task))
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=0)),
    )

    result = await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)
    assert result is not None


@pytest.mark.asyncio
async def test_apply_score_25_vs_min_50_rejected(monkeypatch):
    """Worker with very low score should be rejected."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=50))
    )
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=25)),
    )

    with pytest.raises(
        Exception, match="Insufficient reputation.*Required: 50.*yours: 25"
    ):
        await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)


@pytest.mark.asyncio
async def test_apply_score_75_vs_min_50_allowed(monkeypatch):
    """Worker with high score should be allowed."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=50))
    )
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=75)),
    )

    result = await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)
    assert result is not None


@pytest.mark.asyncio
async def test_apply_high_min_reputation_gate(monkeypatch):
    """Task with high min_reputation=90 should reject score=80 worker."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=90))
    )
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=80)),
    )

    with pytest.raises(
        Exception, match="Insufficient reputation.*Required: 90.*yours: 80"
    ):
        await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)


# ---------------------------------------------------------------------------
# assign_task tests (reputation gate at assignment)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_score_49_vs_min_50_rejected(monkeypatch):
    """Assigning worker with score 49 to task with min_reputation=50 should be rejected."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=50))
    )
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=49)),
    )

    with pytest.raises(Exception, match="insufficient reputation"):
        await sbc.assign_task(
            task_id=TASK_ID, agent_id="agent_test", executor_id=EXECUTOR_ID
        )


@pytest.mark.asyncio
async def test_assign_score_50_vs_min_50_passes_rep_check(monkeypatch):
    """Assigning worker with score 50 to task with min_reputation=50 passes reputation check."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=50))
    )
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=50)),
    )
    monkeypatch.setattr(
        sbc, "update_task", AsyncMock(return_value=_make_task(min_reputation=50))
    )

    # Should pass reputation check — score exactly meets minimum
    result = await sbc.assign_task(
        task_id=TASK_ID, agent_id="agent_test", executor_id=EXECUTOR_ID
    )
    assert result is not None


# ---------------------------------------------------------------------------
# HTTP endpoint tests (403 status code)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_endpoint_returns_403_for_insufficient_reputation(monkeypatch):
    """The /tasks/{task_id}/apply endpoint should return 403 when reputation is insufficient."""
    from api import routes
    from fastapi import HTTPException

    monkeypatch.setattr(
        routes.db,
        "apply_to_task",
        AsyncMock(
            side_effect=Exception("Insufficient reputation. Required: 50, yours: 30")
        ),
    )

    request = routes.WorkerApplicationRequest(
        executor_id=EXECUTOR_ID,
        message="I want to help",
    )

    with pytest.raises(HTTPException) as exc:
        await routes.apply_to_task(task_id=TASK_ID, request=request)

    assert exc.value.status_code == 403
    assert "Insufficient reputation" in exc.value.detail


@pytest.mark.asyncio
async def test_apply_endpoint_returns_200_for_sufficient_reputation(monkeypatch):
    """The /tasks/{task_id}/apply endpoint should return 200 when reputation is sufficient."""
    from api import routes

    monkeypatch.setattr(
        routes.db,
        "apply_to_task",
        AsyncMock(
            return_value={
                "application": {
                    "id": "app-123",
                    "task_id": TASK_ID,
                    "status": "pending",
                }
            }
        ),
    )

    request = routes.WorkerApplicationRequest(
        executor_id=EXECUTOR_ID,
        message="I want to help",
    )

    result = await routes.apply_to_task(task_id=TASK_ID, request=request)

    assert result.message == "Application submitted successfully"
    assert result.data["application_id"] == "app-123"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_executor_missing_reputation_score_field(monkeypatch):
    """Executor without reputation_score field should default to 0."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=10))
    )

    executor_without_score = {"id": EXECUTOR_ID, "wallet_address": "0xWorker"}
    monkeypatch.setattr(
        sbc, "get_client", lambda: _MockClient(executor_data=executor_without_score)
    )

    with pytest.raises(
        Exception, match="Insufficient reputation.*Required: 10.*yours: 0"
    ):
        await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)


@pytest.mark.asyncio
async def test_apply_min_reputation_100_only_perfect_allowed(monkeypatch):
    """Only worker with score >= 100 can apply to a task with min_reputation=100."""
    monkeypatch.setattr(
        sbc, "get_task", AsyncMock(return_value=_make_task(min_reputation=100))
    )
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=99)),
    )

    with pytest.raises(Exception, match="Insufficient reputation"):
        await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)

    # Score 100 should be allowed
    monkeypatch.setattr(
        sbc,
        "get_client",
        lambda: _MockClient(executor_data=_make_executor(reputation_score=100)),
    )
    result = await sbc.apply_to_task(task_id=TASK_ID, executor_id=EXECUTOR_ID)
    assert result is not None
