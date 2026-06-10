"""
Escrow reconciler — stuck transitional claim remediation.

Crash-window gap (follow-up to the L-19/L-20 atomic claims): if the server
dies between the DB claim (status flipped to 'releasing'/'refunding') and the
on-chain TX, the escrow row is stranded in the transitional state and blocks
all retries forever — and the base reconciler only audits
deposited/pending/locked rows, so it never remediates them.

reconcile_stuck_claims() must:
- only act on transitional rows older than STUCK_CLAIM_THRESHOLD,
- verify on-chain state via the SDK + Facilitator paths the dispatcher
  already uses (query_escrow_state — never direct contract calls),
- advance to the terminal status when the TX completed on-chain,
- roll back to the captured pre-claim status when it did not,
- fail safe (skip) when on-chain state cannot be determined.
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("TESTING", "true")

pytestmark = pytest.mark.payments

import supabase_client  # noqa: E402
import audit.escrow_reconciler as reconciler  # noqa: E402
import integrations.x402.payment_dispatcher as pd  # noqa: E402


TASK_ID = "stuck-claim-task-0001"


def _iso_ago(seconds: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()


def _stuck_row(
    status="releasing",
    previous="locked",
    age_seconds=3600,
    payment_info=True,
):
    meta = {
        "claim_previous_status": previous,
        "claim_claimed_at": _iso_ago(age_seconds),
    }
    if payment_info:
        meta["payment_info"] = {"mode": "fase2", "operator": "0x" + "11" * 20}
    return {
        "id": "esc-1",
        "task_id": TASK_ID,
        "status": status,
        "metadata": meta,
        "updated_at": _iso_ago(age_seconds),
        "created_at": _iso_ago(age_seconds + 120),
    }


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeEscrowTable:
    """Single-row escrows table supporting the reconciler's query shapes."""

    def __init__(self, row):
        self.row = row
        self._mode = None
        self._update_payload = None
        self._eq = {}
        self._in = None

    def select(self, *_a, **_k):
        self._mode = "select"
        self._eq = {}
        self._in = None
        return self

    def update(self, payload):
        self._mode = "update"
        self._update_payload = payload
        self._eq = {}
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def in_(self, col, values):
        self._in = (col, list(values))
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        if self._mode == "update":
            # CAS: only flip if the row is still in the expected status.
            if self._eq.get("status") == self.row["status"]:
                self.row["status"] = self._update_payload["status"]
                if "metadata" in self._update_payload:
                    self.row["metadata"] = self._update_payload["metadata"]
                return _FakeResult([dict(self.row)])
            return _FakeResult([])
        # select
        if self._in is not None:
            col, values = self._in
            if self.row.get(col) in values:
                return _FakeResult([dict(self.row)])
            return _FakeResult([])
        return _FakeResult([dict(self.row)])


class _FakeClient:
    def __init__(self, table):
        self._table = table

    def table(self, name):
        assert name == "escrows"
        return self._table


def _fake_dispatcher(capturable="0", reconstruct=True, client_error=None):
    d = MagicMock()
    pi = MagicMock()
    if reconstruct:
        d._reconstruct_fase2_state = AsyncMock(return_value=(pi, {"network": "base"}))
    else:
        d._reconstruct_fase2_state = AsyncMock(return_value=(None, {}))
    fase2_client = MagicMock()
    fase2_client.query_escrow_state = MagicMock(
        return_value={"capturableAmount": capturable}
    )
    if client_error is not None:
        d._get_fase2_client = MagicMock(side_effect=client_error)
    else:
        d._get_fase2_client = MagicMock(return_value=fase2_client)
    return d


async def _run(row, dispatcher):
    table = _FakeEscrowTable(row)
    with (
        patch.object(supabase_client, "get_client", return_value=_FakeClient(table)),
        patch.object(pd, "get_dispatcher", return_value=dispatcher),
    ):
        summary = await reconciler.reconcile_stuck_claims()
    return table, summary


class TestStuckClaimReconciliation:
    @pytest.mark.asyncio
    async def test_crash_window_releasing_settled_onchain_advances(self):
        """REPRO crash window: row stuck in 'releasing' past the threshold,
        on-chain says capturableAmount == 0 (the release TX DID land before
        the crash) → the reconciler advances the row to 'released'."""
        row = _stuck_row(status="releasing", age_seconds=3600)
        table, summary = await _run(row, _fake_dispatcher(capturable="0"))
        assert summary["checked"] == 1
        assert summary["advanced"] == 1
        assert summary["rolled_back"] == 0
        assert table.row["status"] == "released"
        assert table.row["metadata"]["reconciler_action"] == "stuck_claim_advanced"

    @pytest.mark.asyncio
    async def test_crash_window_releasing_not_settled_rolls_back(self):
        """Row stuck in 'releasing', on-chain says funds are still capturable
        (the TX never landed) → roll back to the captured pre-claim status so
        retries unblock — NOT a hardcoded 'locked'."""
        row = _stuck_row(
            status="releasing", previous="pending_assignment", age_seconds=3600
        )
        table, summary = await _run(row, _fake_dispatcher(capturable="100000"))
        assert summary["checked"] == 1
        assert summary["rolled_back"] == 1
        assert summary["advanced"] == 0
        assert table.row["status"] == "pending_assignment"
        assert table.row["metadata"]["reconciler_action"] == "stuck_claim_rolled_back"
        assert table.row["metadata"]["reconciler_reason"] == "onchain_not_settled"

    @pytest.mark.asyncio
    async def test_crash_window_refunding_settled_onchain_advances(self):
        row = _stuck_row(status="refunding", age_seconds=3600)
        table, summary = await _run(row, _fake_dispatcher(capturable="0"))
        assert summary["advanced"] == 1
        assert table.row["status"] == "refunded"

    @pytest.mark.asyncio
    async def test_young_claim_is_left_alone(self):
        """A transitional row younger than the threshold is an in-flight
        settlement — the reconciler must not touch it."""
        row = _stuck_row(status="releasing", age_seconds=10)
        dispatcher = _fake_dispatcher(capturable="0")
        table, summary = await _run(row, dispatcher)
        assert summary["checked"] == 0
        assert table.row["status"] == "releasing"
        dispatcher._reconstruct_fase2_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_payment_info_rolls_back_blind(self):
        """Without stored fase2 payment_info the dispatcher could never have
        fired an on-chain TX — the claim is pure DB state and is rolled back
        to the pre-claim status without an on-chain query."""
        row = _stuck_row(
            status="refunding",
            previous="authorized",
            age_seconds=3600,
            payment_info=False,
        )
        dispatcher = _fake_dispatcher()
        table, summary = await _run(row, dispatcher)
        assert summary["rolled_back"] == 1
        assert table.row["status"] == "authorized"
        assert table.row["metadata"]["reconciler_reason"] == "no_payment_info"
        dispatcher._reconstruct_fase2_state.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_unknown_onchain_state_is_skipped_fail_safe(self):
        """If the on-chain state cannot be queried (e.g. no signing key —
        RuntimeError from _get_fase2_client), do NOT guess: leave the row for
        the next cycle / manual verification."""
        row = _stuck_row(status="releasing", age_seconds=3600)
        table, summary = await _run(
            row, _fake_dispatcher(client_error=RuntimeError("EM_SERVER_SIGNING off"))
        )
        assert summary["skipped"] == 1
        assert summary["advanced"] == 0
        assert summary["rolled_back"] == 0
        assert table.row["status"] == "releasing"

    @pytest.mark.asyncio
    async def test_reconstruction_failure_is_skipped(self):
        """payment_info exists but PaymentInfo reconstruction fails (possibly
        transient) → skip rather than guess."""
        row = _stuck_row(status="releasing", age_seconds=3600)
        table, summary = await _run(row, _fake_dispatcher(reconstruct=False))
        assert summary["skipped"] == 1
        assert table.row["status"] == "releasing"

    @pytest.mark.asyncio
    async def test_audit_events_emitted(self):
        """Detection + auto-correction follow the existing audit-event
        pattern (AUDIT_ESCROW_STUCK_CLAIM / AUDIT_ESCROW_AUTO_CORRECTED)."""
        row = _stuck_row(status="releasing", age_seconds=3600)
        table = _FakeEscrowTable(row)
        with (
            patch.object(
                supabase_client, "get_client", return_value=_FakeClient(table)
            ),
            patch.object(
                pd, "get_dispatcher", return_value=_fake_dispatcher(capturable="0")
            ),
            patch("audit.audit_log") as mock_audit,
        ):
            await reconciler.reconcile_stuck_claims()
        events = [c.args[0] for c in mock_audit.call_args_list]
        assert "AUDIT_ESCROW_STUCK_CLAIM" in events
        assert "AUDIT_ESCROW_AUTO_CORRECTED" in events

    @pytest.mark.asyncio
    async def test_query_failure_recorded_not_fatal(self):
        """An exception while resolving one row is recorded and does not
        abort the reconciliation run."""
        row = _stuck_row(status="releasing", age_seconds=3600)
        dispatcher = _fake_dispatcher()
        dispatcher._get_fase2_client = MagicMock(
            return_value=MagicMock(
                query_escrow_state=MagicMock(side_effect=Exception("rpc boom"))
            )
        )
        table, summary = await _run(row, dispatcher)
        assert summary["checked"] == 1
        assert len(summary["errors"]) == 1
        assert table.row["status"] == "releasing"  # untouched — fail safe

    @pytest.mark.asyncio
    async def test_legacy_row_without_claim_metadata_uses_updated_at(self):
        """Rows claimed before the claim markers existed have no
        claim_claimed_at / claim_previous_status — age falls back to
        updated_at and the rollback target falls back to 'locked'."""
        row = _stuck_row(status="releasing", age_seconds=3600, payment_info=False)
        row["metadata"] = {}  # legacy: no claim markers at all
        table, summary = await _run(row, _fake_dispatcher())
        assert summary["rolled_back"] == 1
        assert table.row["status"] == "locked"
