"""
Tests for PaymentDispatcher (x402r escrow vs preauth mode).

Covers:
- Authorize/Release/Refund in both x402r and preauth modes
- Worker payout consistency across modes (full bounty, no fee deduction)
- Fee calculation and collection
- Error handling (step failures, missing state, fund safety)
- State reconstruction from DB after server restart
- Thread-safe singleton
- Escrow status validation (no duplicate operations)
"""

import json
import os
import threading
from decimal import Decimal
from typing import Any, Dict
from unittest.mock import (
    AsyncMock,
    MagicMock,
    patch,
)

import pytest

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Fake / Stub objects used across tests
# ---------------------------------------------------------------------------

# A deterministic test private key (DO NOT use in production).
# eth_account.Account.from_key(TEST_PK).address = some deterministic addr.
TEST_PK = "0x" + "ab" * 32  # 64-char hex


class FakePaymentInfo:
    """Stub for PaymentInfo from SDK."""

    def __init__(self, receiver="0xPlatform", amount=5000000, tier="standard"):
        self.receiver = receiver
        self.amount = amount
        self.tier = tier


class FakeTaskPayment:
    """Stub for TaskPayment dataclass."""

    def __init__(
        self,
        task_id="task-1",
        payment_info=None,
        amount_usdc=Decimal("5.00"),
        status="authorized",
        tx_hashes=None,
    ):
        self.task_id = task_id
        self.payment_info = payment_info or FakePaymentInfo()
        self.amount_usdc = amount_usdc
        self.status = status
        self.tx_hashes = tx_hashes or ["0x" + "a" * 64]


class FakeTransactionResult:
    """Stub for TransactionResult from SDK."""

    def __init__(self, success=True, tx_hash=None, error=None, gas_used=21000):
        self.success = success
        self.transaction_hash = tx_hash or ("0x" + "b" * 64)
        self.error = error
        self.gas_used = gas_used


class FakeVerifyResult:
    """Stub for verify_task_payment result."""

    def __init__(self, success=True, tx_hash=None, error=None):
        self.success = success
        self.tx_hash = tx_hash
        self.error = error


class FakeEscrow:
    """Mock EMAdvancedEscrow for testing."""

    def __init__(self):
        self._task_payments: Dict[str, Any] = {}
        self.client = MagicMock()

    def authorize_task(self, task_id, receiver, amount_usdc, strategy):
        payment = FakeTaskPayment(task_id=task_id, amount_usdc=amount_usdc)
        self._task_payments[task_id] = payment
        return payment

    def release_to_worker(self, task_id, amount):
        return FakeTransactionResult(success=True)

    def refund_to_agent(self, task_id, amount):
        return FakeTransactionResult(success=True)

    def get_task_payment(self, task_id):
        return self._task_payments.get(task_id)

    def get_config(self):
        return {"chain_id": 8453}

    def _amount_to_atomic(self, amount_usdc):
        return int(amount_usdc * Decimal(10**6))


class FakeSDK:
    """Mock EMX402SDK for testing."""

    def __init__(self):
        self.client = MagicMock()
        self.recipient_address = "0xRecipient"
        self.facilitator_url = "https://facilitator.test"
        self.network = "base"

    async def disburse_to_worker(self, **kwargs):
        return {"success": True, "tx_hash": "0x" + "c" * 64}

    async def collect_platform_fee(self, **kwargs):
        return {"success": True, "tx_hash": "0x" + "d" * 64}

    async def verify_task_payment(self, **kwargs):
        return FakeVerifyResult(success=True)

    async def settle_task_payment(self, **kwargs):
        return {
            "success": True,
            "tx_hash": "0x" + "e" * 64,
            "net_to_worker": float(kwargs.get("bounty_amount", 0)),
        }

    async def refund_task_payment(self, **kwargs):
        return {"success": True, "tx_hash": "0x" + "f" * 64, "status": "refunded"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DISPATCHER_MODULE = "integrations.x402.payment_dispatcher"


@pytest.fixture(autouse=True)
def _reset_dispatcher_singleton():
    """Reset singleton state before each test."""
    import integrations.x402.payment_dispatcher as mod

    mod._dispatcher = None
    mod._cached_platform_address = None
    yield
    mod._dispatcher = None
    mod._cached_platform_address = None


@pytest.fixture()
def _patch_platform_address():
    """Patch _get_platform_address for all tests that need it."""
    with patch(
        f"{DISPATCHER_MODULE}._get_platform_address",
        return_value="0xPlatformAddr",
    ):
        yield


def _make_dispatcher(mode="x402r", seed_task_id=None, seed_amount=None):
    """
    Create a PaymentDispatcher with mocked backends.

    If seed_task_id is provided, pre-populates the escrow with a TaskPayment
    so that release/refund can find it (simulating a prior authorize).
    """
    with (
        patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", True),
        patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
    ):
        from integrations.x402.payment_dispatcher import PaymentDispatcher

        dispatcher = PaymentDispatcher(mode=mode)

    fake_escrow = FakeEscrow()
    fake_sdk = FakeSDK()

    # Pre-seed escrow state if requested
    if seed_task_id:
        amt = seed_amount or Decimal("10.80")
        fake_escrow._task_payments[seed_task_id] = FakeTaskPayment(
            task_id=seed_task_id, amount_usdc=amt
        )

    dispatcher._escrow = fake_escrow
    dispatcher._sdk = fake_sdk
    return dispatcher


# ===========================================================================
# Test: Authorize Payment
# ===========================================================================


class TestAuthorizePayment:
    """Tests for PaymentDispatcher.authorize_payment()."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_patch_platform_address")
    async def test_x402r_authorize_success(self):
        """x402r authorize should lock funds on-chain and return success."""
        d = _make_dispatcher("x402r")

        result = await d.authorize_payment(
            task_id="task-1",
            receiver="0xAgent",
            amount_usdc=Decimal("10.80"),
            x_payment_header=None,
        )

        assert result["success"] is True
        assert result["mode"] == "x402r"
        assert result["escrow_status"] == "deposited"
        assert result["payment_info"] is not None

    @pytest.mark.asyncio
    async def test_preauth_authorize_without_header_fails(self):
        """preauth authorize without X-Payment header should fail."""
        d = _make_dispatcher("preauth")

        result = await d.authorize_payment(
            task_id="task-2",
            receiver="0xAgent",
            amount_usdc=Decimal("5.40"),
            x_payment_header=None,
        )

        assert result["success"] is False
        assert result["mode"] == "preauth"
        assert "header required" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_authorize_returns_correct_mode(self):
        """Each mode should identify itself in the response."""
        for mode in ("x402r", "preauth"):
            d = _make_dispatcher(mode)
            result = await d.authorize_payment(
                task_id=f"task-{mode}",
                receiver="0xAgent",
                amount_usdc=Decimal("5.00"),
            )
            assert result["mode"] == mode


# ===========================================================================
# Test: Release Payment
# ===========================================================================


class TestReleasePayment:
    """Tests for PaymentDispatcher.release_payment()."""

    @pytest.mark.asyncio
    async def test_x402r_release_worker_gets_full_bounty(self):
        """x402r release: worker should receive the FULL bounty (no fee deduction)."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-1", seed_amount=Decimal("10.80")
        )

        result = await d.release_payment(
            task_id="task-1",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is True
        assert result["mode"] == "x402r"
        assert result["net_to_worker"] == 10.0
        assert result["platform_fee"] > 0
        assert result["gross_amount"] > result["net_to_worker"]

    @pytest.mark.asyncio
    async def test_x402r_release_without_state_fails(self):
        """x402r release without prior authorize should fail cleanly."""
        d = _make_dispatcher("x402r")
        # No seed — no state in escrow, and _ensure_escrow_state will fail
        d._ensure_escrow_state = AsyncMock(return_value=False)

        result = await d.release_payment(
            task_id="task-no-state",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is False
        assert "state not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_x402r_release_escrow_failure(self):
        """If escrow release fails, worker should NOT be paid."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-1", seed_amount=Decimal("10.80")
        )

        d._escrow.release_to_worker = lambda tid, amt: FakeTransactionResult(
            success=False, error="Contract reverted"
        )

        result = await d.release_payment(
            task_id="task-1",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is False
        assert "escrow release failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_x402r_release_worker_disbursement_failure(self):
        """If worker disbursement fails after escrow release, report failure."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-1", seed_amount=Decimal("10.80")
        )

        d._sdk.disburse_to_worker = AsyncMock(
            return_value={"success": False, "error": "Facilitator timeout"}
        )

        result = await d.release_payment(
            task_id="task-1",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is False
        assert result["error"] is not None  # Contains the SDK error message

    @pytest.mark.asyncio
    async def test_x402r_fee_collection_failure_flagged(self):
        """If fee collection fails, success should be True but fee_collection_error set."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-1", seed_amount=Decimal("10.80")
        )

        d._sdk.collect_platform_fee = AsyncMock(
            return_value={"success": False, "error": "Treasury unreachable"}
        )

        result = await d.release_payment(
            task_id="task-1",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is True
        assert result.get("fee_collection_error") is not None
        assert "treasury" in result["fee_collection_error"].lower()

    @pytest.mark.asyncio
    async def test_preauth_release_requires_payment_header(self):
        """preauth release without payment_header should fail."""
        d = _make_dispatcher("preauth")

        result = await d.release_payment(
            task_id="task-1",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
            payment_header=None,
        )

        assert result["success"] is False
        assert "header required" in result["error"].lower()


# ===========================================================================
# Test: Refund Payment
# ===========================================================================


class TestRefundPayment:
    """Tests for PaymentDispatcher.refund_payment()."""

    @pytest.mark.asyncio
    async def test_x402r_refund_success(self):
        """x402r refund with agent address should complete fully."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-1", seed_amount=Decimal("10.80")
        )

        result = await d.refund_payment(
            task_id="task-1",
            agent_address="0xAgent",
        )

        assert result["success"] is True
        assert result["mode"] == "x402r"
        assert result["status"] == "refunded"
        assert result["agent_refund_tx"] is not None

    @pytest.mark.asyncio
    async def test_x402r_refund_disbursement_failure_returns_false(self):
        """If agent disbursement fails after escrow refund, success should be False."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-1", seed_amount=Decimal("10.80")
        )

        d._sdk.disburse_to_worker = AsyncMock(
            return_value={"success": False, "error": "Nonce too low"}
        )

        result = await d.refund_payment(
            task_id="task-1",
            agent_address="0xAgent",
        )

        assert result["success"] is False
        assert result["status"] == "partial_refund"
        assert "platform wallet" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_x402r_refund_no_agent_address(self):
        """x402r refund without agent_address should fail (can't disburse)."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-1", seed_amount=Decimal("10.80")
        )

        result = await d.refund_payment(
            task_id="task-1",
            agent_address=None,
        )

        assert result["success"] is False
        assert result["status"] == "partial_refund"

    @pytest.mark.asyncio
    async def test_x402r_refund_without_state_fails(self):
        """x402r refund without escrow state should fail cleanly."""
        d = _make_dispatcher("x402r")
        d._ensure_escrow_state = AsyncMock(return_value=False)

        result = await d.refund_payment(
            task_id="task-no-state",
            agent_address="0xAgent",
        )

        assert result["success"] is False
        assert "state not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_preauth_refund_no_escrow_id(self):
        """preauth refund without escrow_id means auth expires naturally."""
        d = _make_dispatcher("preauth")

        result = await d.refund_payment(
            task_id="task-1",
            escrow_id=None,
        )

        assert result["success"] is True
        assert result["status"] == "auth_expired"


# ===========================================================================
# Test: State Reconstruction
# ===========================================================================


class TestStateReconstruction:
    """Tests for _ensure_escrow_state (DB-based state recovery)."""

    @pytest.mark.asyncio
    async def test_state_already_in_memory(self):
        """If state is already in memory, should return True immediately."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-1", seed_amount=Decimal("10.80")
        )

        result = await d._ensure_escrow_state("task-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_reconstruction_blocks_terminal_status(self):
        """Should refuse to reconstruct state for already-released escrows."""
        d = _make_dispatcher("x402r")  # No seed — state not in memory

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "status": "released",
                "metadata": json.dumps(
                    {
                        "payment_info": {
                            "receiver": "0xPlatform",
                            "amount": 10800000,
                            "tier": "standard",
                            "max_fee_bps": 800,
                        }
                    }
                ),
                "total_amount_usdc": 10.80,
                "beneficiary_address": "0xAgent",
            }
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        with patch("supabase_client.get_client", return_value=mock_client):
            result = await d._ensure_escrow_state("task-already-released")

        assert result is False

    @pytest.mark.asyncio
    async def test_reconstruction_no_payment_info_fails(self):
        """Should fail if escrow metadata lacks payment_info."""
        d = _make_dispatcher("x402r")

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "status": "deposited",
                "metadata": json.dumps({}),
                "total_amount_usdc": 10.80,
                "beneficiary_address": "0xAgent",
            }
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        with patch("supabase_client.get_client", return_value=mock_client):
            result = await d._ensure_escrow_state("task-no-pi")

        assert result is False


# ===========================================================================
# Test: Mode Selection and Fallbacks
# ===========================================================================


class TestModeSelection:
    """Tests for payment mode selection and fallback logic."""

    def test_x402r_falls_back_when_escrow_unavailable(self):
        """x402r should fall back to preauth if advanced escrow is unavailable."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", False),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="x402r")
            assert d.mode == "preauth"

    def test_x402r_falls_back_when_sdk_unavailable(self):
        """x402r should fall back to preauth if SDK unavailable (needed for disbursement)."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", False),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="x402r")
            assert d.mode == "preauth"

    def test_unknown_mode_falls_back_to_preauth(self):
        """Unknown mode should fall back to preauth with warning."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="invalid_mode")
            assert d.mode == "preauth"

    def test_get_mode_returns_current(self):
        """get_mode() should return the configured mode."""
        d = _make_dispatcher("x402r")
        assert d.get_mode() == "x402r"

        d2 = _make_dispatcher("preauth")
        assert d2.get_mode() == "preauth"

    def test_get_info_includes_mode(self):
        """get_info() should include mode and availability."""
        d = _make_dispatcher("x402r")
        info = d.get_info()
        assert info["mode"] == "x402r"
        assert "timestamp" in info


# ===========================================================================
# Test: Thread Safety
# ===========================================================================


class TestThreadSafety:
    """Tests for thread-safe singleton."""

    def test_singleton_returns_same_instance(self):
        """get_dispatcher() should return the same instance."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}._dispatcher", None),
            patch(
                f"{DISPATCHER_MODULE}._get_platform_address",
                return_value="0xPlatformAddr",
            ),
        ):
            from integrations.x402.payment_dispatcher import get_dispatcher

            d1 = get_dispatcher()
            d2 = get_dispatcher()
            assert d1 is d2

    def test_concurrent_creation_returns_same_instance(self):
        """Multiple threads calling get_dispatcher() should get the same instance."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}._dispatcher", None),
            patch(
                f"{DISPATCHER_MODULE}._get_platform_address",
                return_value="0xPlatformAddr",
            ),
        ):
            from integrations.x402.payment_dispatcher import get_dispatcher

            results = []

            def create():
                results.append(get_dispatcher())

            threads = [threading.Thread(target=create) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert all(r is results[0] for r in results)


# ===========================================================================
# Test: Fee Calculations
# ===========================================================================


class TestFeeCalculations:
    """Verify fee math across modes."""

    @pytest.mark.asyncio
    async def test_x402r_fee_minimum_enforced(self):
        """Platform fee should be at least $0.01 for non-zero fees."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-small", seed_amount=Decimal("0.54")
        )

        result = await d.release_payment(
            task_id="task-small",
            worker_address="0xWorker",
            bounty_amount=Decimal("0.50"),
        )

        assert result["success"] is True
        # $0.50 * 8% = $0.04 (above minimum $0.01)
        assert result["platform_fee"] == 0.04

    @pytest.mark.asyncio
    async def test_x402r_fee_for_tiny_bounty(self):
        """Very small bounties should still have minimum $0.01 fee."""
        d = _make_dispatcher(
            "x402r", seed_task_id="task-tiny", seed_amount=Decimal("0.06")
        )

        result = await d.release_payment(
            task_id="task-tiny",
            worker_address="0xWorker",
            bounty_amount=Decimal("0.05"),
        )

        assert result["success"] is True
        # $0.05 * 8% = $0.004 < $0.01 -> bumped to $0.01
        assert result["platform_fee"] == 0.01


# ===========================================================================
# Test: Helper Functions
# ===========================================================================


class TestHelpers:
    """Tests for module-level helper functions."""

    def test_extract_tx_hash_from_dict(self):
        from integrations.x402.payment_dispatcher import _extract_tx_hash

        tx = "0x" + "a" * 64
        assert _extract_tx_hash({"tx_hash": tx}) == tx
        assert _extract_tx_hash({"transaction_hash": tx}) == tx
        assert _extract_tx_hash({"transaction": tx}) == tx
        assert _extract_tx_hash({"hash": tx}) == tx

    def test_extract_tx_hash_from_none(self):
        from integrations.x402.payment_dispatcher import _extract_tx_hash

        assert _extract_tx_hash(None) is None

    def test_extract_tx_hash_rejects_invalid(self):
        from integrations.x402.payment_dispatcher import _extract_tx_hash

        assert _extract_tx_hash({"tx_hash": "not-a-hash"}) is None
        assert _extract_tx_hash({"tx_hash": "0x1234"}) is None

    def test_get_platform_address_caching(self):
        """_get_platform_address should cache the result."""
        import integrations.x402.payment_dispatcher as mod

        mod._cached_platform_address = None

        with patch.dict(os.environ, {"WALLET_PRIVATE_KEY": TEST_PK}):
            addr1 = mod._get_platform_address()
            addr2 = mod._get_platform_address()
            assert addr1 == addr2
            assert addr1.startswith("0x")
            assert mod._cached_platform_address == addr1

        mod._cached_platform_address = None

    def test_get_platform_address_missing_key_raises(self):
        """Should raise RuntimeError if WALLET_PRIVATE_KEY is not set."""
        import integrations.x402.payment_dispatcher as mod

        mod._cached_platform_address = None

        old = os.environ.pop("WALLET_PRIVATE_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="WALLET_PRIVATE_KEY"):
                mod._get_platform_address()
        finally:
            if old:
                os.environ["WALLET_PRIVATE_KEY"] = old
            mod._cached_platform_address = None
