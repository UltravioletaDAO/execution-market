"""
Focused tests for submitted-task timeout handling in expiration job.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.core

from ..jobs import task_expiration
from api import routes
import supabase_client as db


# ---------------------------------------------------------------------------
# Shared mock helpers (must be defined before test-specific client classes)
# ---------------------------------------------------------------------------


class _ChainMock:
    """Supports chained .eq() / .execute() / .insert() / .update() calls."""

    def __init__(self):
        self.calls = []

    def eq(self, *args, **kwargs):
        self.calls.append(("eq", args, kwargs))
        return self

    def execute(self):
        self.calls.append(("execute",))
        return SimpleNamespace(data=[])

    def update(self, *args, **kwargs):
        self.calls.append(("update", args, kwargs))
        return self

    def insert(self, *args, **kwargs):
        self.calls.append(("insert", args, kwargs))
        return self


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
    """Fake Supabase client supporting submissions + tasks tables."""

    def __init__(self, submission_rows):
        self._submission_rows = submission_rows
        self.tasks_mock = _ChainMock()

    def table(self, name: str):
        if name == "submissions":
            return _SubmissionQuery(self._submission_rows)
        if name == "tasks":
            return self.tasks_mock
        raise AssertionError(f"Unexpected table access: {name}")


@pytest.mark.asyncio
async def test_submitted_timeout_auto_settles_and_auto_approves(monkeypatch):
    task_id = "task-timeout-1"
    submission_id = "sub-timeout-1"
    submission_payload = {
        "id": submission_id,
        "task": {"id": task_id, "agent_id": "agent_test", "bounty_usd": 1.0},
        "executor": {
            "id": "worker_1",
            "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        },
        "agent_verdict": "pending",
    }

    monkeypatch.setattr(
        db, "get_submission", AsyncMock(return_value=submission_payload)
    )
    monkeypatch.setattr(
        routes,
        "_is_submission_ready_for_instant_payout",
        AsyncMock(return_value={"ready": True, "reason": "ready"}),
    )
    settle_mock = AsyncMock(
        return_value={"payment_tx": "0x" + "a" * 64, "payment_error": None}
    )
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
async def test_submitted_timeout_permanent_failure_expires_task(monkeypatch):
    """Permanent failure reasons (e.g. missing_payment_header) should fall
    through to expiration instead of retrying forever."""
    task_id = "task-timeout-2"
    submission_id = "sub-timeout-2"
    submission_payload = {
        "id": submission_id,
        "task": {"id": task_id, "agent_id": "agent_test", "bounty_usd": 1.0},
        "executor": {"id": "worker_2", "wallet_address": None},
        "agent_verdict": "pending",
    }

    monkeypatch.setattr(
        db, "get_submission", AsyncMock(return_value=submission_payload)
    )
    monkeypatch.setattr(
        routes,
        "_is_submission_ready_for_instant_payout",
        AsyncMock(return_value={"ready": False, "reason": "missing_payment_header"}),
    )
    settle_mock = AsyncMock()
    monkeypatch.setattr(routes, "_settle_submission_payment", settle_mock)
    auto_approve_mock = AsyncMock()
    monkeypatch.setattr(routes, "_auto_approve_submission", auto_approve_mock)

    client = _Client([{"id": submission_id, "agent_verdict": "pending"}])
    handled = await task_expiration._process_submitted_timeout_task(
        client,
        {"id": task_id, "status": "submitted"},
    )

    # Permanent failure returns False so the caller expires the task
    assert handled is False
    settle_mock.assert_not_awaited()
    auto_approve_mock.assert_not_awaited()
    # No metadata update (tasks table has no metadata column) — the code
    # just logs and returns False to fall through to normal expiration.


@pytest.mark.asyncio
async def test_submitted_timeout_transient_failure_keeps_for_retry(monkeypatch):
    """Transient/unknown failure reasons should keep the task for retry."""
    task_id = "task-timeout-2b"
    submission_id = "sub-timeout-2b"
    submission_payload = {
        "id": submission_id,
        "task": {"id": task_id, "agent_id": "agent_test", "bounty_usd": 1.0},
        "executor": {"id": "worker_2", "wallet_address": "0x" + "a" * 40},
        "agent_verdict": "pending",
    }

    monkeypatch.setattr(
        db, "get_submission", AsyncMock(return_value=submission_payload)
    )
    monkeypatch.setattr(
        routes,
        "_is_submission_ready_for_instant_payout",
        AsyncMock(return_value={"ready": False, "reason": "missing_worker_wallet"}),
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


# ---------------------------------------------------------------------------
# Helper: mock Supabase client that supports update + insert for expiration
# ---------------------------------------------------------------------------


class _ExpirationClient:
    """Fake Supabase client supporting tasks + payments tables."""

    def __init__(self):
        self.tasks_mock = _ChainMock()
        self.payments_mock = _ChainMock()

    def table(self, name: str):
        if name == "tasks":
            return self.tasks_mock
        if name == "payments":
            return self.payments_mock
        raise AssertionError(f"Unexpected table access: {name}")


# ---------------------------------------------------------------------------
# Fase 5 (direct_release) refund path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expired_task_fase5_uses_payment_dispatcher(monkeypatch):
    """Task with escrow in direct_release mode uses PaymentDispatcher for refund."""
    monkeypatch.setenv("EM_ESCROW_MODE", "direct_release")

    task = {
        "id": "task-expire-fase5",
        "status": "published",
        "agent_id": "agent_test",
        "bounty_usd": 0.10,
        "escrow_id": "escrow-123",
    }

    client = _ExpirationClient()

    # Mock PaymentDispatcher
    refund_mock = AsyncMock(
        return_value={
            "success": True,
            "tx_hash": "0x" + "b" * 64,
            "mode": "fase2",
            "escrow_mode": "direct_release",
        }
    )

    import integrations.x402.payment_dispatcher as pd_module

    mock_dispatcher = MagicMock()
    mock_dispatcher.refund_trustless_escrow = refund_mock
    monkeypatch.setattr(pd_module, "PaymentDispatcher", lambda: mock_dispatcher)

    await task_expiration._process_expired_task(client, task)

    refund_mock.assert_awaited_once_with(
        task_id="task-expire-fase5",
        reason="Auto-refund: task expired past deadline",
    )

    # Verify payment record was inserted
    insert_calls = [c for c in client.payments_mock.calls if c[0] == "insert"]
    assert len(insert_calls) == 1
    record = insert_calls[0][1][0]
    assert record["task_id"] == "task-expire-fase5"
    assert record["type"] == "refund"
    assert "Fase 5 trustless" in record["note"]


@pytest.mark.asyncio
async def test_expired_task_fase5_failed_refund_logs_warning(monkeypatch):
    """Fase 5 refund failure is logged but does not raise."""
    monkeypatch.setenv("EM_ESCROW_MODE", "direct_release")

    task = {
        "id": "task-expire-fail",
        "status": "published",
        "agent_id": "agent_test",
        "bounty_usd": 0.10,
        "escrow_id": "escrow-456",
    }

    client = _ExpirationClient()

    refund_mock = AsyncMock(
        return_value={"success": False, "error": "escrow already refunded"}
    )

    import integrations.x402.payment_dispatcher as pd_module

    mock_dispatcher = MagicMock()
    mock_dispatcher.refund_trustless_escrow = refund_mock
    monkeypatch.setattr(pd_module, "PaymentDispatcher", lambda: mock_dispatcher)

    # Should not raise
    await task_expiration._process_expired_task(client, task)

    refund_mock.assert_awaited_once()
    # No payment record should be inserted on failure
    insert_calls = [c for c in client.payments_mock.calls if c[0] == "insert"]
    assert len(insert_calls) == 0


# ---------------------------------------------------------------------------
# Legacy (platform_release) refund path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expired_task_legacy_uses_advanced_escrow(monkeypatch):
    """Task with escrow in platform_release mode uses legacy refund_to_agent."""
    monkeypatch.setenv("EM_ESCROW_MODE", "platform_release")

    task = {
        "id": "task-expire-legacy",
        "status": "published",
        "agent_id": "agent_test",
        "bounty_usd": 0.10,
        "escrow_id": "escrow-789",
    }

    client = _ExpirationClient()

    mock_result = SimpleNamespace(success=True, transaction_hash="0x" + "c" * 64)

    # Patch the lazy import inside the else branch
    import integrations.x402.advanced_escrow_integration as aei_module

    monkeypatch.setattr(aei_module, "ADVANCED_ESCROW_AVAILABLE", True)
    monkeypatch.setattr(aei_module, "refund_to_agent", lambda task_id: mock_result)

    await task_expiration._process_expired_task(client, task)

    # Verify payment record was inserted with legacy note
    insert_calls = [c for c in client.payments_mock.calls if c[0] == "insert"]
    assert len(insert_calls) == 1
    record = insert_calls[0][1][0]
    assert record["task_id"] == "task-expire-legacy"
    assert record["type"] == "refund"
    assert "via SDK" in record["note"]


@pytest.mark.asyncio
async def test_expired_task_no_escrow_skips_refund(monkeypatch):
    """Task without escrow_id skips refund entirely."""
    monkeypatch.setenv("EM_ESCROW_MODE", "direct_release")

    task = {
        "id": "task-no-escrow",
        "status": "published",
        "agent_id": "agent_test",
        "bounty_usd": 0.10,
        "escrow_id": None,
    }

    client = _ExpirationClient()

    await task_expiration._process_expired_task(client, task)

    # No payment inserts — refund was skipped
    insert_calls = [c for c in client.payments_mock.calls if c[0] == "insert"]
    assert len(insert_calls) == 0
