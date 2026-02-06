"""
Focused tests for submitted-task timeout handling in expiration job.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from ..jobs import task_expiration
from api import routes
import supabase_client as db


class _SubmissionQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _Client:
    def __init__(self, submission_rows):
        self._submission_rows = submission_rows

    def table(self, name: str):
        if name == "submissions":
            return _SubmissionQuery(self._submission_rows)
        raise AssertionError(f"Unexpected table access: {name}")


@pytest.mark.asyncio
async def test_submitted_timeout_auto_settles_and_auto_approves(monkeypatch):
    task_id = "task-timeout-1"
    submission_id = "sub-timeout-1"
    submission_payload = {
        "id": submission_id,
        "task": {"id": task_id, "agent_id": "agent_test", "bounty_usd": 1.0},
        "executor": {"id": "worker_1", "wallet_address": "0x1234567890abcdef1234567890abcdef12345678"},
        "agent_verdict": "pending",
    }

    monkeypatch.setattr(db, "get_submission", AsyncMock(return_value=submission_payload))
    monkeypatch.setattr(
        routes,
        "_is_submission_ready_for_instant_payout",
        AsyncMock(return_value={"ready": True, "reason": "ready"}),
    )
    settle_mock = AsyncMock(return_value={"payment_tx": "0x" + "a" * 64, "payment_error": None})
    monkeypatch.setattr(routes, "_settle_submission_payment", settle_mock)
    auto_approve_mock = AsyncMock(return_value=submission_payload)
    monkeypatch.setattr(routes, "_auto_approve_submission", auto_approve_mock)

    handled = await task_expiration._process_submitted_timeout_task(
        _Client([{"id": submission_id, "agent_verdict": "pending"}]),
        {"id": task_id, "status": "submitted"},
    )

    assert handled is True
    settle_mock.assert_awaited_once()
    auto_approve_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_submitted_timeout_not_ready_keeps_task_for_retry(monkeypatch):
    task_id = "task-timeout-2"
    submission_id = "sub-timeout-2"
    submission_payload = {
        "id": submission_id,
        "task": {"id": task_id, "agent_id": "agent_test", "bounty_usd": 1.0},
        "executor": {"id": "worker_2", "wallet_address": None},
        "agent_verdict": "pending",
    }

    monkeypatch.setattr(db, "get_submission", AsyncMock(return_value=submission_payload))
    monkeypatch.setattr(
        routes,
        "_is_submission_ready_for_instant_payout",
        AsyncMock(return_value={"ready": False, "reason": "missing_payment_header"}),
    )
    settle_mock = AsyncMock()
    monkeypatch.setattr(routes, "_settle_submission_payment", settle_mock)
    auto_approve_mock = AsyncMock()
    monkeypatch.setattr(routes, "_auto_approve_submission", auto_approve_mock)

    handled = await task_expiration._process_submitted_timeout_task(
        _Client([{"id": submission_id, "agent_verdict": "pending"}]),
        {"id": task_id, "status": "submitted"},
    )

    assert handled is True
    settle_mock.assert_not_awaited()
    auto_approve_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_submitted_timeout_without_submission_falls_back_to_expire():
    handled = await task_expiration._process_submitted_timeout_task(
        _Client([]),
        {"id": "task-timeout-3", "status": "submitted"},
    )
    assert handled is False
