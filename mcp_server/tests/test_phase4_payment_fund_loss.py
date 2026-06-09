"""
Phase 4 — Payment fund-loss hardening (security audit 2026-06-09).

Reproduces and locks down the PM-elevated P2 fund-loss findings owned by
work-stream WS-PAY:

- 4.1 / L-16 — settlement must never silently fall back to the cold treasury.
- 4.3 / L-19,L-20 — release/refund must be atomic + idempotent under concurrency.
- 4.4 / L-22 — EM_SERVER_SIGNING must gate the disbursement/settlement signers.
- 4.5 / L-25 — Solana payout must validate the recipient before settling.

Each test asserts the *vulnerable* behaviour is gone (would have passed-through
pre-fix) and the secure behaviour holds.
"""

import asyncio
import os
import threading
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Must be set before importing the payment modules so the EM_TREASURY_ADDRESS
# module-load guard does not abort import.
os.environ.setdefault("TESTING", "true")

pytestmark = pytest.mark.payments

import integrations.x402.payment_dispatcher as pd  # noqa: E402
import integrations.x402.sdk_client as sdk_client  # noqa: E402
import supabase_client  # noqa: E402  (import once so patch.object is cheap)


TASK_ID = "phase4-task-0001"
WORKER = "0x" + "ab" * 20
OTHER = "0x" + "cd" * 20


# ===========================================================================
# 4.1 / L-16 — settlement must never silently fall back to the treasury
# ===========================================================================


class TestSettlementAddressNoTreasuryFallback:
    def test_misconfig_raises_instead_of_returning_treasury(self):
        """Pre-fix this returned EM_TREASURY (cold wallet) — a silent fund trap.

        With neither EM_SETTLEMENT_ADDRESS nor WALLET_PRIVATE_KEY set, and not in
        test/disabled mode, resolution MUST raise rather than redirect every
        bounty into cold storage.
        """
        with patch.object(sdk_client, "EM_SETTLEMENT_ADDRESS", None), patch.object(
            sdk_client, "_is_testing", False
        ), patch.object(sdk_client, "_is_payment_disabled", False), patch.dict(
            os.environ, {}, clear=False
        ):
            os.environ.pop("WALLET_PRIVATE_KEY", None)
            with pytest.raises(RuntimeError, match="settlement address is not configured"):
                sdk_client.EMX402SDK._resolve_settlement_address()

    def test_explicit_settlement_address_is_used(self):
        with patch.object(sdk_client, "EM_SETTLEMENT_ADDRESS", WORKER):
            assert sdk_client.EMX402SDK._resolve_settlement_address() == WORKER

    def test_testing_mode_allows_treasury_placeholder(self):
        """In TESTING/disabled mode (no real funds) the placeholder is allowed."""
        with patch.object(sdk_client, "EM_SETTLEMENT_ADDRESS", None), patch.object(
            sdk_client, "_is_testing", True
        ), patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WALLET_PRIVATE_KEY", None)
            assert (
                sdk_client.EMX402SDK._resolve_settlement_address()
                == sdk_client.EM_TREASURY
            )


# ===========================================================================
# 4.4 / L-22 — EM_SERVER_SIGNING gate on disbursement/settlement signers
# ===========================================================================


class TestServerSigningGate:
    def test_get_agent_account_blocked_when_signing_disabled(self):
        """With EM_SERVER_SIGNING off, loading the platform key to sign a
        disbursement MUST be refused (pre-fix it signed unconditionally)."""
        sdk = sdk_client.EMX402SDK.__new__(sdk_client.EMX402SDK)  # no __init__
        with patch.dict(os.environ, {"WALLET_PRIVATE_KEY": "0x" + "11" * 32}, clear=False):
            os.environ.pop("EM_SERVER_SIGNING", None)
            with pytest.raises(RuntimeError, match="Server-side payment signing is disabled"):
                sdk._get_agent_account()

    def test_get_agent_account_allowed_when_signing_enabled(self):
        sdk = sdk_client.EMX402SDK.__new__(sdk_client.EMX402SDK)
        with patch.dict(
            os.environ,
            {"WALLET_PRIVATE_KEY": "0x" + "11" * 32, "EM_SERVER_SIGNING": "true"},
            clear=False,
        ):
            acct = sdk._get_agent_account()
            assert acct.address.startswith("0x")

    @pytest.mark.asyncio
    async def test_disburse_to_worker_blocked_when_signing_disabled(self):
        """End-to-end: the public disbursement entry point fails closed."""
        sdk = sdk_client.EMX402SDK.__new__(sdk_client.EMX402SDK)
        sdk.network = "base"
        with patch.dict(os.environ, {"WALLET_PRIVATE_KEY": "0x" + "11" * 32}, clear=False):
            os.environ.pop("EM_SERVER_SIGNING", None)
            result = await sdk.disburse_to_worker(
                worker_address=WORKER,
                amount_usdc=Decimal("0.10"),
                task_id=TASK_ID,
            )
            assert result["success"] is False
            assert "EM_SERVER_SIGNING" in result["error"]


# ===========================================================================
# 4.3 / L-19,L-20 — atomic + idempotent release/refund under concurrency
# ===========================================================================


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _AtomicEscrowTable:
    """Simulates a single escrow row with an atomic conditional UPDATE.

    The conditional ``UPDATE ... WHERE status NOT IN (blocked)`` is serialized
    under a lock so the test can fire concurrent claims and assert exactly one
    wins — exactly the race the fix must close.
    """

    def __init__(self, initial_status="locked"):
        self._status = initial_status
        self._lock = threading.Lock()
        # builder state
        self._mode = None
        self._update_payload = None
        self._not_in = None
        self._eq_status = None

    # --- builder API ---------------------------------------------------
    def update(self, payload):
        self._mode = "update"
        self._update_payload = payload
        self._not_in = None
        self._eq_status = None
        return self

    def select(self, *_a, **_k):
        self._mode = "select"
        return self

    def eq(self, col, val):
        if col == "status":
            self._eq_status = val
        return self

    @property
    def not_(self):
        # postgrest chains as `.not_.in_(...)` — `not_` is a property that
        # returns a builder exposing `in_`. Returning self preserves state.
        return self

    def in_(self, _col, values):
        self._not_in = set(values)
        return self

    def order(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        if self._mode == "update":
            with self._lock:
                payload_status = self._update_payload.get("status")
                # Rollback update: .eq("status", transitional)
                if self._eq_status is not None:
                    if self._status == self._eq_status:
                        self._status = payload_status
                        return _FakeResult([{"status": payload_status}])
                    return _FakeResult([])
                # Claim update: NOT IN blocked
                if self._not_in is not None and self._status in self._not_in:
                    return _FakeResult([])  # blocked — claim refused
                prev = self._status
                self._status = payload_status
                return _FakeResult([{"status": payload_status, "_prev": prev}])
        # select latest row
        return _FakeResult([{"status": self._status}])


class _FakeClient:
    def __init__(self, table):
        self._table = table

    def table(self, name):
        assert name == "escrows"
        return self._table


def _make_dispatcher(mode="fase2"):
    with patch.object(pd, "FASE2_SDK_AVAILABLE", True), patch.object(
        pd, "SDK_AVAILABLE", True
    ):
        return pd.PaymentDispatcher(mode=mode)


class TestAtomicClaim:
    @pytest.mark.asyncio
    async def test_first_claim_wins_second_refused(self):
        table = _AtomicEscrowTable(initial_status="locked")
        d = _make_dispatcher()
        with patch.object(supabase_client, "get_client", return_value=_FakeClient(table)):
            first = await d._claim_escrow_operation(TASK_ID, "release")
            second = await d._claim_escrow_operation(TASK_ID, "release")
        assert first["claimed"] is True
        assert second["claimed"] is False
        assert second["reason"] == "already_settled"
        assert table._status == "releasing"

    @pytest.mark.asyncio
    async def test_no_escrow_row_distinguished(self):
        table = _AtomicEscrowTable(initial_status="locked")
        # Empty table → both update and select return []
        table._status = None  # select returns [{status: None}] -> treat as row

        class _EmptyTable(_AtomicEscrowTable):
            def execute(self):
                if self._mode == "update":
                    return _FakeResult([])
                return _FakeResult([])

        empty = _EmptyTable()
        d = _make_dispatcher()
        with patch.object(supabase_client, "get_client", return_value=_FakeClient(empty)):
            claim = await d._claim_escrow_operation(TASK_ID, "release")
        assert claim["claimed"] is False
        assert claim["reason"] == "no_escrow_row"

    @pytest.mark.asyncio
    async def test_concurrent_releases_settle_exactly_once(self):
        """REPRO L-19/L-20: fire many concurrent release claims; exactly one wins."""
        table = _AtomicEscrowTable(initial_status="locked")
        d = _make_dispatcher()
        with patch.object(supabase_client, "get_client", return_value=_FakeClient(table)):
            results = await asyncio.gather(
                *[d._claim_escrow_operation(TASK_ID, "release") for _ in range(20)]
            )
        wins = [r for r in results if r.get("claimed")]
        assert len(wins) == 1, f"expected exactly 1 winning claim, got {len(wins)}"

    @pytest.mark.asyncio
    async def test_claim_error_fails_closed(self):
        """If the claim query throws, we must NOT proceed to move funds."""
        broken = MagicMock()
        broken.table.side_effect = RuntimeError("db down")
        d = _make_dispatcher()
        with patch.object(supabase_client, "get_client", return_value=broken):
            claim = await d._claim_escrow_operation(TASK_ID, "release")
        assert claim["claimed"] is False
        assert claim["reason"] == "claim_error"

    @pytest.mark.asyncio
    async def test_already_released_release_is_idempotent_success(self):
        table = _AtomicEscrowTable(initial_status="released")
        d = _make_dispatcher()
        with patch.object(supabase_client, "get_client", return_value=_FakeClient(table)):
            claim = await d._claim_escrow_operation(TASK_ID, "release")
            blocked = await d._release_claim_blocked_result(TASK_ID, claim)
        assert claim["claimed"] is False
        assert blocked is not None
        assert blocked["success"] is True
        assert blocked["status"] == "already_released"
        assert blocked["tx_hash"] is None  # no second on-chain TX

    @pytest.mark.asyncio
    async def test_already_refunded_refund_is_idempotent_success(self):
        table = _AtomicEscrowTable(initial_status="refunded")
        d = _make_dispatcher()
        with patch.object(supabase_client, "get_client", return_value=_FakeClient(table)):
            claim = await d._claim_escrow_operation(TASK_ID, "refund")
            blocked = await d._refund_claim_blocked_result(TASK_ID, claim)
        assert blocked is not None
        assert blocked["success"] is True
        assert blocked["status"] == "already_refunded"

    @pytest.mark.asyncio
    async def test_rollback_restores_locked_for_retry(self):
        table = _AtomicEscrowTable(initial_status="locked")
        d = _make_dispatcher()
        with patch.object(supabase_client, "get_client", return_value=_FakeClient(table)):
            claim = await d._claim_escrow_operation(TASK_ID, "release")
            assert claim["claimed"] is True
            assert table._status == "releasing"
            await d._release_claim_rollback(TASK_ID, "release")
        assert table._status == "locked"


# ===========================================================================
# 4.5 / L-25 — Solana payout recipient validation
# ===========================================================================


def test_solana_pubkeys_match_helper():
    assert pd._solana_pubkeys_match("AbC", "AbC") is True
    assert pd._solana_pubkeys_match(" AbC ", "AbC") is True
    # Solana is case-sensitive base58 — different case is a different key.
    assert pd._solana_pubkeys_match("abc", "AbC") is False
    assert pd._solana_pubkeys_match("", "AbC") is False
    assert pd._solana_pubkeys_match(None, "AbC") is False
    assert pd._solana_pubkeys_match("AbC", None) is False


class _FakeSession:
    def __init__(self, payee):
        self.payee = payee


class TestSolanaPayoutRecipient:
    @pytest.mark.asyncio
    async def test_release_refused_when_payee_mismatch(self):
        """REPRO L-25: channel payee != assigned worker → refuse to settle."""
        d = _make_dispatcher()
        fake_client = MagicMock()
        fake_client.get_session = AsyncMock(return_value=_FakeSession(payee=OTHER))
        fake_client.close_session = AsyncMock()

        with patch.object(d, "_lookup_channel_id", AsyncMock(return_value="Chan11111111111111111111111111111111")), patch.object(
            pd, "get_pay_shell_client", return_value=fake_client
        ), patch.object(pd, "log_payment_event", AsyncMock()):
            result = await d._release_solana_session(
                task_id=TASK_ID,
                worker_address=WORKER,
                bounty_amount=Decimal("0.10"),
                token="USDC",
            )
        assert result["success"] is False
        assert "recipient mismatch" in result["error"].lower()
        # Critical: close_session (which settles funds) must NOT have run.
        fake_client.close_session.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_release_proceeds_when_payee_matches(self):
        d = _make_dispatcher()

        close_result = MagicMock()
        close_result.settlement_tx_hash = "soln_tx_hash_123"
        close_result.final_cumulative_usdc = Decimal("0.10")
        close_result.refund_usdc = Decimal("0")

        fake_client = MagicMock()
        fake_client.get_session = AsyncMock(return_value=_FakeSession(payee=WORKER))
        fake_client.close_session = AsyncMock(return_value=close_result)

        with patch.object(d, "_lookup_channel_id", AsyncMock(return_value="Chan11111111111111111111111111111111")), patch.object(
            pd, "get_pay_shell_client", return_value=fake_client
        ), patch.object(pd, "log_payment_event", AsyncMock()):
            result = await d._release_solana_session(
                task_id=TASK_ID,
                worker_address=WORKER,
                bounty_amount=Decimal("0.10"),
                token="USDC",
            )
        assert result["success"] is True
        assert result["tx_hash"] == "soln_tx_hash_123"
        fake_client.close_session.assert_awaited_once()
