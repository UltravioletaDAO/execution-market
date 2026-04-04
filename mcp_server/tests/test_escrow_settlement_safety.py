"""
Tests for settlement safety: escrow state validation at release time,
unsafe default handling in cancellation, and TX hash confirmation guard.

Covers Phase 2 fixes from the Escrow Validation Master Plan:
- Task 2.1: _settle_submission_payment() validates escrow status is releasable
- Task 2.2: Cancel endpoint no longer defaults to "authorized" on escrow lookup failure
- Task 2.3: Escrow not marked "released" without confirmed TX hash
"""

import os
import pytest
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

# Must be set before any mcp_server imports to bypass treasury check
os.environ.setdefault("TESTING", "true")

pytestmark = [pytest.mark.asyncio, pytest.mark.payments]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MOCK_TASK_ID = "11111111-2222-3333-4444-555555555555"
MOCK_SUBMISSION_ID = "sub-settle-001"
MOCK_ESCROW_ID = "escrow-settle-001"
MOCK_WORKER_WALLET = "0x" + "ab" * 20  # Valid 42-char ETH address
MOCK_AGENT_WALLET = "0x" + "cd" * 20


def _make_submission(
    task_id: str = MOCK_TASK_ID,
    bounty: float = 10.0,
    worker_wallet: str = MOCK_WORKER_WALLET,
    escrow_id: str = MOCK_ESCROW_ID,
    escrow_tx: str = "0xESCROW_TX_123",
    payment_network: str = "base",
    payment_token: str = "USDC",
) -> dict:
    """Build a submission dict matching what _settle_submission_payment expects."""
    return {
        "task": {
            "id": task_id,
            "bounty_usd": bounty,
            "escrow_id": escrow_id,
            "escrow_tx": escrow_tx,
            "payment_network": payment_network,
            "payment_token": payment_token,
        },
        "executor": {
            "id": "exec-001",
            "wallet_address": worker_wallet,
        },
    }


class _FakeQueryResult:
    """Minimal Supabase query result for chaining."""

    def __init__(self, data=None):
        self.data = data or []

    def execute(self):
        return self

    # Support chaining: .select().eq().limit().single().execute()
    def select(self, *a, **kw):
        return self

    def eq(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

    def single(self):
        return self

    def update(self, *a, **kw):
        return self

    def insert(self, *a, **kw):
        return self


class _FakeTable:
    """Minimal fake for supabase client.table() calls."""

    def __init__(self, data=None, raise_on_select=False, exc=None):
        self._data = data
        self._raise_on_select = raise_on_select
        self._exc = exc

    def select(self, *a, **kw):
        if self._raise_on_select:
            raise (self._exc or Exception("DB lookup failed"))
        return _FakeQueryResult(self._data)

    def eq(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def limit(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def single(self):
        return _FakeQueryResult(self._data)

    def update(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def insert(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def execute(self):
        return _FakeQueryResult(self._data)


class _FakeClient:
    """Fake supabase client that routes table() calls."""

    def __init__(self, tables: dict = None):
        self._tables = tables or {}

    def table(self, name: str):
        if name in self._tables:
            return self._tables[name]
        return _FakeTable()


# ---------------------------------------------------------------------------
# Test 1: Settle rejects escrow in "released" state (Phase 2 Task 2.1)
# ---------------------------------------------------------------------------


async def test_settle_rejects_released_escrow():
    """
    When the escrow status is already 'released', _settle_submission_payment
    must return a payment_error about non-releasable state and NOT proceed
    with settlement.
    """
    escrow_row = {
        "metadata": json.dumps({"escrow_mode": "direct_release"}),
        "status": "released",
    }

    fake_client = _FakeClient(
        tables={
            "escrows": _FakeTable(data=[escrow_row]),
            "payments": _FakeTable(data=[]),
        }
    )

    mock_dispatcher = MagicMock()
    mock_dispatcher.get_mode.return_value = "fase2"
    mock_dispatcher.escrow_mode = "direct_release"
    # Safety: if escrow check fails to bail out, don't crash on await
    mock_dispatcher.release_direct_to_worker = AsyncMock(
        return_value={"success": False, "error": "should not reach here"}
    )

    with (
        patch("api.routers._helpers.db") as mock_db,
        patch(
            "api.routers._helpers.get_payment_dispatcher",
            return_value=mock_dispatcher,
        ),
        patch("api.routers._helpers.X402_AVAILABLE", True),
        patch(
            "api.routers._helpers.get_platform_fee_percent",
            new_callable=AsyncMock,
            return_value=Decimal("0.13"),
        ),
        patch(
            "api.routers._helpers._get_existing_submission_payment",
            return_value=None,
        ),
        patch(
            "api.routers._helpers._resolve_task_payment_header",
            return_value="x-payment-header-mock",
        ),
        patch(
            "api.routers._helpers._extract_agent_wallet_from_header",
            return_value=MOCK_AGENT_WALLET,
        ),
    ):
        mock_db.get_client.return_value = fake_client

        from api.routers._helpers import _settle_submission_payment

        result = await _settle_submission_payment(
            submission_id=MOCK_SUBMISSION_ID,
            submission=_make_submission(),
        )

    assert result["payment_tx"] is None
    assert result["payment_error"] is not None
    assert (
        "releasable" in result["payment_error"].lower()
        or "released" in result["payment_error"].lower()
    )


# ---------------------------------------------------------------------------
# Test 2: Settle rejects escrow in "refunded" state (Phase 2 Task 2.1)
# ---------------------------------------------------------------------------


async def test_settle_rejects_refunded_escrow():
    """
    When the escrow status is 'refunded', _settle_submission_payment
    must return a payment_error about non-releasable state.
    """
    escrow_row = {
        "metadata": json.dumps({"escrow_mode": "direct_release"}),
        "status": "refunded",
    }

    fake_client = _FakeClient(
        tables={
            "escrows": _FakeTable(data=[escrow_row]),
            "payments": _FakeTable(data=[]),
        }
    )

    mock_dispatcher = MagicMock()
    mock_dispatcher.get_mode.return_value = "fase2"
    mock_dispatcher.escrow_mode = "direct_release"
    # Safety: if escrow check fails to bail out, don't crash on await
    mock_dispatcher.release_direct_to_worker = AsyncMock(
        return_value={"success": False, "error": "should not reach here"}
    )

    with (
        patch("api.routers._helpers.db") as mock_db,
        patch(
            "api.routers._helpers.get_payment_dispatcher",
            return_value=mock_dispatcher,
        ),
        patch("api.routers._helpers.X402_AVAILABLE", True),
        patch(
            "api.routers._helpers.get_platform_fee_percent",
            new_callable=AsyncMock,
            return_value=Decimal("0.13"),
        ),
        patch(
            "api.routers._helpers._get_existing_submission_payment",
            return_value=None,
        ),
        patch(
            "api.routers._helpers._resolve_task_payment_header",
            return_value="x-payment-header-mock",
        ),
        patch(
            "api.routers._helpers._extract_agent_wallet_from_header",
            return_value=MOCK_AGENT_WALLET,
        ),
    ):
        mock_db.get_client.return_value = fake_client

        from api.routers._helpers import _settle_submission_payment

        result = await _settle_submission_payment(
            submission_id=MOCK_SUBMISSION_ID,
            submission=_make_submission(),
        )

    assert result["payment_tx"] is None
    assert result["payment_error"] is not None
    assert (
        "releasable" in result["payment_error"].lower()
        or "refunded" in result["payment_error"].lower()
    )


# ---------------------------------------------------------------------------
# Test 3: Settlement without TX hash returns error (Phase 2 Task 2.3)
# ---------------------------------------------------------------------------


async def test_settlement_no_tx_hash_returns_error():
    """
    When the dispatcher returns success=True but no tx_hash,
    _settle_submission_payment must:
    1. Return payment_error about missing tx hash
    2. NOT update escrow to 'released'
    """
    escrow_row = {
        "metadata": json.dumps({"escrow_mode": "direct_release"}),
        "status": "locked",
    }

    escrow_table = _FakeTable(data=[escrow_row])
    escrow_update_calls = []

    # Track whether escrow was updated to "released"
    def tracking_update(*args, **kwargs):
        escrow_update_calls.append(("update", args, kwargs))
        return _FakeQueryResult()

    escrow_table.update = tracking_update

    fake_client = _FakeClient(
        tables={
            "escrows": escrow_table,
            "payments": _FakeTable(data=[]),
        }
    )

    mock_dispatcher = MagicMock()
    mock_dispatcher.get_mode.return_value = "fase2"
    mock_dispatcher.escrow_mode = "direct_release"
    # Simulate successful release but WITHOUT a tx_hash
    mock_dispatcher.release_direct_to_worker = AsyncMock(
        return_value={
            "success": True,
            # No tx_hash, transaction_hash, transaction, or hash keys
            "mode": "direct_release",
        }
    )

    with (
        patch("api.routers._helpers.db") as mock_db,
        patch(
            "api.routers._helpers.get_payment_dispatcher",
            return_value=mock_dispatcher,
        ),
        patch("api.routers._helpers.X402_AVAILABLE", True),
        patch(
            "api.routers._helpers.get_platform_fee_percent",
            new_callable=AsyncMock,
            return_value=Decimal("0.13"),
        ),
        patch(
            "api.routers._helpers._get_existing_submission_payment",
            return_value=None,
        ),
        patch(
            "api.routers._helpers._resolve_task_payment_header",
            return_value="x-payment-header-mock",
        ),
        patch(
            "api.routers._helpers._extract_agent_wallet_from_header",
            return_value=MOCK_AGENT_WALLET,
        ),
    ):
        mock_db.get_client.return_value = fake_client

        from api.routers._helpers import _settle_submission_payment

        result = await _settle_submission_payment(
            submission_id=MOCK_SUBMISSION_ID,
            submission=_make_submission(),
        )

    # Must return error about missing TX hash
    assert result["payment_tx"] is None
    assert result["payment_error"] is not None
    assert (
        "tx hash" in result["payment_error"].lower()
        or "tx_hash" in result["payment_error"].lower()
    )

    # Escrow must NOT have been updated to "released"
    released_updates = [
        call
        for call in escrow_update_calls
        if call[0] == "update"
        and len(call[1]) > 0
        and isinstance(call[1][0], dict)
        and call[1][0].get("status") == "released"
    ]
    assert len(released_updates) == 0, (
        "Escrow should NOT be marked 'released' without a confirmed TX hash"
    )


# ---------------------------------------------------------------------------
# Test 4: Cancel with escrow_tx raises HTTP 500 on lookup failure
#          (Phase 2 Task 2.2)
# ---------------------------------------------------------------------------


async def test_cancel_escrow_lookup_failure_with_tx_raises():
    """
    When a task has an escrow_tx but the escrow DB lookup fails,
    the cancel endpoint must raise HTTP 500 instead of silently
    defaulting to 'authorized' status.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    # Build a minimal FastAPI app with the cancel endpoint
    app = FastAPI()

    # Mock the auth dependency
    mock_auth = MagicMock()
    mock_auth.agent_id = "agent-test-001"
    mock_auth.wallet_address = "0x" + "ef" * 20

    # Task that has an escrow_tx (on-chain escrow was locked)
    mock_task = {
        "id": MOCK_TASK_ID,
        "agent_id": "agent-test-001",
        "status": "accepted",
        "escrow_tx": "0xABC123EXISTING_ESCROW_TX",
        "escrow_id": MOCK_ESCROW_ID,
        "bounty_usd": 10.0,
    }

    # Escrow table that raises on select (simulates DB failure)
    escrow_table_failing = _FakeTable(
        raise_on_select=True, exc=Exception("Connection refused")
    )

    fake_client = _FakeClient(
        tables={
            "escrows": escrow_table_failing,
        }
    )

    mock_dispatcher = MagicMock()
    mock_dispatcher.get_mode.return_value = "fase2"
    mock_dispatcher.escrow_mode = "direct_release"

    with (
        patch("api.routers.tasks.verify_agent_auth", return_value=mock_auth),
        patch("api.routers.tasks.db") as mock_tasks_db,
        patch(
            "api.routers.tasks.get_payment_dispatcher",
            return_value=mock_dispatcher,
        ),
        patch(
            "api.routers.tasks._normalize_status",
            side_effect=lambda v: str(v or "").strip().lower(),
        ),
    ):
        mock_tasks_db.get_task = AsyncMock(return_value=mock_task)
        mock_tasks_db.get_client.return_value = fake_client
        mock_tasks_db.cancel_task = AsyncMock(return_value={"status": "cancelled"})

        from api.routers.tasks import router

        app.include_router(router)

        # Override the auth dependency at app level
        from api.auth import verify_agent_auth

        app.dependency_overrides[verify_agent_auth] = lambda: mock_auth

        try:
            client = TestClient(app, raise_server_exceptions=False)
        except TypeError:
            pytest.skip("httpx/starlette TestClient incompatibility")

        response = client.post(f"/api/v1/tasks/{MOCK_TASK_ID}/cancel")

    # The endpoint should return 500 (not 200 with silent default)
    # because escrow lookup failed but the task has a real escrow_tx
    assert response.status_code == 500, (
        f"Expected HTTP 500 when escrow lookup fails for task with escrow_tx, "
        f"got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert (
        "escrow" in body.get("detail", "").lower()
        or "verify" in body.get("detail", "").lower()
    )
