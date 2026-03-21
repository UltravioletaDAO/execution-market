"""
Edge case tests for escrow validation: Fase 1 bypass, expired escrow,
and pending_assignment status handling.

Covers:
- Fase 1 mode skips escrow validation entirely on assign
- pending_assignment is NOT a funded status (submit_work rejects)
- partial_released IS a funded status (submit_work allows)
"""

import pytest
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import supabase_client as sbc

pytestmark = [pytest.mark.payments, pytest.mark.escrow_validation]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TASK_ID = "aaaaaaaa-1111-2222-3333-aaaaaaaaaaaa"
AGENT_ID = "agent-escrow-test"
EXECUTOR_ID = "exec-escrow-test"


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_task(status="accepted", executor_id=EXECUTOR_ID):
    """Build a task dict suitable for submit_work / assign_task tests."""
    return {
        "id": TASK_ID,
        "agent_id": AGENT_ID,
        "status": status,
        "executor_id": executor_id,
        "bounty_usd": 0.10,
        "min_reputation": 0,
        "deadline": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "evidence_schema": {"required": ["photo"]},
    }


def _make_executor():
    return {
        "id": EXECUTOR_ID,
        "wallet_address": "0xWorkerEscrowTest",
        "reputation_score": 80,
        "name": "Escrow Edge Worker",
        "erc8004_agent_id": "",
    }


class _EscrowMockChainQuery:
    """Chainable mock for Supabase table queries with escrow support."""

    def __init__(self, executor_data=None, escrow_data=None, apps_data=None):
        self._executor_data = executor_data
        self._escrow_data = escrow_data
        self._apps_data = apps_data
        self._table = None
        self._inserting = False
        self._insert_data = None

    def select(self, *_a, **_kw):
        return self

    def eq(self, *_a, **_kw):
        return self

    def neq(self, *_a, **_kw):
        return self

    def limit(self, *_a, **_kw):
        return self

    def single(self):
        return self

    def insert(self, data):
        self._inserting = True
        self._insert_data = data
        return self

    def update(self, _data):
        return self

    def execute(self):
        if self._inserting:
            return SimpleNamespace(
                data=[{"id": "sub-mock-123", **(self._insert_data or {})}]
            )
        if self._table == "executors":
            return SimpleNamespace(data=self._executor_data)
        if self._table == "escrows":
            return SimpleNamespace(data=self._escrow_data or [])
        if self._table in ("task_applications", "applications"):
            return SimpleNamespace(data=self._apps_data or [])
        if self._table == "submissions":
            return SimpleNamespace(
                data=[{"id": "sub-mock-123", **(self._insert_data or {})}]
            )
        return SimpleNamespace(data=[])


class _EscrowMockClient:
    """Supabase client mock with configurable escrow rows."""

    def __init__(self, executor_data=None, escrow_data=None, apps_data=None):
        self._executor_data = executor_data
        self._escrow_data = escrow_data
        self._apps_data = apps_data

    def table(self, name):
        q = _EscrowMockChainQuery(
            executor_data=self._executor_data,
            escrow_data=self._escrow_data,
            apps_data=self._apps_data,
        )
        q._table = name
        return q


# ---------------------------------------------------------------------------
# Test 1: Fase 1 skips escrow validation on assign
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fase1_skips_escrow_validation_on_assign(monkeypatch):
    """In Fase 1 mode, assign_task succeeds even with NO escrow record at all.

    Fase 1 means no escrow by design -- the `if payment_mode != 'fase1'` guard
    in assign_task must skip the entire escrow validation block.
    """
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase1")

    task = _make_task(status="published", executor_id=None)
    monkeypatch.setattr(sbc, "get_task", AsyncMock(return_value=task))

    # No escrow rows at all -- this would blow up in fase2
    mock_client = _EscrowMockClient(
        executor_data=_make_executor(),
        escrow_data=[],  # empty = no escrow record
    )
    monkeypatch.setattr(sbc, "get_client", lambda: mock_client)

    # Mock update_task so we don't need a real DB
    monkeypatch.setattr(
        sbc,
        "update_task",
        AsyncMock(
            return_value={**task, "status": "accepted", "executor_id": EXECUTOR_ID}
        ),
    )

    # Should NOT raise -- Fase 1 bypasses escrow validation
    result = await sbc.assign_task(
        task_id=TASK_ID,
        agent_id=AGENT_ID,
        executor_id=EXECUTOR_ID,
    )
    assert result is not None
    assert result["task"]["status"] == "accepted"


# ---------------------------------------------------------------------------
# Test 2: submit_work rejects pending_assignment escrow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_rejects_pending_assignment_escrow(monkeypatch):
    """In Fase 2, submit_work must reject when escrow status is 'pending_assignment'.

    pending_assignment means the balance was checked but escrow was NOT yet
    locked for the worker.  It is NOT in the _FUNDED_ESCROW_STATUSES set
    (deposited, funded, locked, active, partial_released).
    """
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase2")

    task = _make_task(status="in_progress")
    monkeypatch.setattr(sbc, "get_task", AsyncMock(return_value=task))

    # Escrow exists but status is pending_assignment (NOT funded)
    mock_client = _EscrowMockClient(
        escrow_data=[{"status": "pending_assignment", "expires_at": None}],
    )
    monkeypatch.setattr(sbc, "get_client", lambda: mock_client)

    with pytest.raises(Exception, match="escrow not confirmed on-chain"):
        await sbc.submit_work(
            task_id=TASK_ID,
            executor_id=EXECUTOR_ID,
            evidence={"photo": "https://example.com/photo.jpg"},
        )


# ---------------------------------------------------------------------------
# Test 3: submit_work allows partial_released escrow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_allows_partial_released_escrow(monkeypatch):
    """In Fase 2, submit_work must succeed when escrow status is 'partial_released'.

    partial_released IS in the _FUNDED_ESCROW_STATUSES set -- it means part of
    the escrow was released but funds remain.  Workers should be able to submit
    evidence against a partially-released escrow.
    """
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase2")

    task = _make_task(status="in_progress")
    monkeypatch.setattr(sbc, "get_task", AsyncMock(return_value=task))

    # Escrow exists with partial_released status (IS funded)
    mock_client = _EscrowMockClient(
        escrow_data=[{"status": "partial_released", "expires_at": None}],
    )
    monkeypatch.setattr(sbc, "get_client", lambda: mock_client)

    # Mock update_task so submit_work can update status after inserting submission
    monkeypatch.setattr(
        sbc,
        "update_task",
        AsyncMock(return_value={**task, "status": "submitted"}),
    )

    result = await sbc.submit_work(
        task_id=TASK_ID,
        executor_id=EXECUTOR_ID,
        evidence={"photo": "https://example.com/photo.jpg"},
    )
    assert result is not None
