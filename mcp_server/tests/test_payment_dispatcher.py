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

pytestmark = pytest.mark.payments

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
                            "max_fee_bps": 1300,
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
        """x402r should fall back to fase1 if advanced escrow is unavailable."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", False),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="x402r")
            assert d.mode == "fase1"

    def test_x402r_falls_back_when_sdk_unavailable(self):
        """x402r should fall back to fase1 if SDK unavailable (needed for disbursement)."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", False),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="x402r")
            assert d.mode == "fase1"

    def test_unknown_mode_falls_back_to_fase1(self):
        """Unknown mode should fall back to fase1 with warning."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="invalid_mode")
            assert d.mode == "fase1"

    def test_fase1_mode_accepted(self):
        """fase1 mode should be accepted directly."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="fase1")
            assert d.mode == "fase1"

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
        # $0.50 * 13% = $0.065 (above minimum $0.01)
        assert result["platform_fee"] == 0.065

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
        # $0.05 * 13% = $0.0065 < $0.01 -> bumped to $0.01
        assert result["platform_fee"] == 0.01


# ===========================================================================
# Test: Helper Functions
# ===========================================================================


# ===========================================================================
# Test: Fase 1 Payment Flow (Auth on Approve)
# ===========================================================================


class TestFase1Flow:
    """Tests for Fase 1 payment flow (balance check + direct settlements)."""

    def _make_fase1_dispatcher(self):
        """Create dispatcher in fase1 mode with mocked SDK."""
        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", False),
            patch(f"{DISPATCHER_MODULE}.FASE2_SDK_AVAILABLE", False),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="fase1")
            d._sdk = FakeSDK()
            d._sdk._get_agent_account = MagicMock()
            d._sdk._get_agent_account.return_value.address = "0xAgent123"
            d._sdk.check_agent_balance = AsyncMock()
            d._sdk.settle_direct_payments = AsyncMock()
            return d

    @pytest.mark.asyncio
    async def test_fase1_authorize_success_sufficient_balance(self):
        """Fase 1 authorize with sufficient balance should succeed."""
        d = self._make_fase1_dispatcher()
        d._sdk.check_agent_balance.return_value = {
            "sufficient": True,
            "balance": "15.00",
        }

        result = await d.authorize_payment(
            task_id="task-f1-1",
            receiver="0xWorker",
            amount_usdc=Decimal("10.00"),
            agent_address="0xAgent123",
            network="base",
        )

        assert result["success"] is True
        assert result["mode"] == "fase1"
        assert result["escrow_status"] == "balance_verified"
        assert result["error"] is None
        assert result["warning"] is None

    @pytest.mark.asyncio
    async def test_fase1_authorize_insufficient_balance_warning(self):
        """Fase 1 authorize with insufficient balance should warn but succeed."""
        d = self._make_fase1_dispatcher()
        d._sdk.check_agent_balance.return_value = {
            "sufficient": False,
            "balance": "5.00",
        }

        result = await d.authorize_payment(
            task_id="task-f1-2",
            receiver="0xWorker",
            amount_usdc=Decimal("10.00"),
            agent_address="0xAgent123",
            network="base",
        )

        assert result["success"] is True  # Always succeed - advisory check
        assert result["mode"] == "fase1"
        assert result["escrow_status"] == "insufficient_balance"
        assert result["warning"] is not None
        assert "insufficient" in result["warning"].lower()

    @pytest.mark.asyncio
    async def test_fase1_authorize_no_agent_address(self):
        """Fase 1 authorize without agent address should derive from SDK."""
        d = self._make_fase1_dispatcher()
        d._sdk.check_agent_balance.return_value = {
            "sufficient": True,
            "balance": "15.00",
        }

        result = await d.authorize_payment(
            task_id="task-f1-3",
            receiver="0xWorker",
            amount_usdc=Decimal("10.00"),
            network="base",
        )

        assert result["success"] is True
        assert result["escrow_status"] == "balance_verified"
        d._sdk.check_agent_balance.assert_called_once()

    @pytest.mark.asyncio
    async def test_fase1_authorize_sdk_agent_derivation_failure(self):
        """Fase 1 authorize should handle SDK agent derivation failure gracefully."""
        d = self._make_fase1_dispatcher()
        d._sdk._get_agent_account.side_effect = Exception("No private key")

        result = await d.authorize_payment(
            task_id="task-f1-4",
            receiver="0xWorker",
            amount_usdc=Decimal("10.00"),
            network="base",
        )

        assert result["success"] is True
        assert result["escrow_status"] == "balance_unknown"
        assert "No agent address available" in result["warning"]

    @pytest.mark.asyncio
    async def test_fase1_release_success_server_managed(self):
        """Fase 1 release for server-managed agent should succeed."""
        d = self._make_fase1_dispatcher()
        d._sdk.settle_direct_payments.return_value = {
            "success": True,
            "tx_hash": "0x" + "a" * 64,
            "fee_tx_hash": "0x" + "b" * 64,
            "gross_amount": 10.80,
            "platform_fee": 0.80,
            "net_to_worker": 10.00,
        }

        result = await d.release_payment(
            task_id="task-f1-5",
            worker_address="0xWorker123",
            bounty_amount=Decimal("10.00"),
            network="base",
        )

        assert result["success"] is True
        assert result["mode"] == "fase1"
        assert result["tx_hash"] == "0x" + "a" * 64
        assert result["fee_tx_hash"] == "0x" + "b" * 64
        assert result["gross_amount"] == 10.80
        assert result["net_to_worker"] == 10.00

        # Verify SDK was called without pre-signed headers
        d._sdk.settle_direct_payments.assert_called_once_with(
            task_id="task-f1-5",
            worker_address="0xWorker123",
            bounty_amount=Decimal("10.00"),
            worker_auth_header=None,
            fee_auth_header=None,
            network="base",
            token="USDC",
        )

    @pytest.mark.asyncio
    async def test_fase1_release_with_presigned_headers(self):
        """Fase 1 release with pre-signed headers for external agents."""
        d = self._make_fase1_dispatcher()
        d._sdk.settle_direct_payments.return_value = {
            "success": True,
            "tx_hash": "0x" + "c" * 64,
            "fee_tx_hash": "0x" + "d" * 64,
            "gross_amount": 5.40,
            "platform_fee": 0.40,
            "net_to_worker": 5.00,
        }

        worker_header = "eip3009-worker-signature-data"
        fee_header = "eip3009-fee-signature-data"

        result = await d.release_payment(
            task_id="task-f1-6",
            worker_address="0xWorker456",
            bounty_amount=Decimal("5.00"),
            worker_auth_header=worker_header,
            fee_auth_header=fee_header,
            network="polygon",
            token="USDC",
        )

        assert result["success"] is True
        assert result["tx_hash"] == "0x" + "c" * 64

        # Verify pre-signed headers were passed through
        d._sdk.settle_direct_payments.assert_called_once_with(
            task_id="task-f1-6",
            worker_address="0xWorker456",
            bounty_amount=Decimal("5.00"),
            worker_auth_header=worker_header,
            fee_auth_header=fee_header,
            network="polygon",
            token="USDC",
        )

    @pytest.mark.asyncio
    async def test_fase1_release_sdk_failure(self):
        """Fase 1 release should handle SDK settlement failure."""
        d = self._make_fase1_dispatcher()
        d._sdk.settle_direct_payments.return_value = {
            "success": False,
            "error": "Insufficient allowance",
        }

        result = await d.release_payment(
            task_id="task-f1-7",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is False
        assert result["mode"] == "fase1"
        assert "Insufficient allowance" in result["error"]

    @pytest.mark.asyncio
    async def test_fase1_refund_no_op(self):
        """Fase 1 refund should be a no-op (no funds moved)."""
        d = self._make_fase1_dispatcher()

        result = await d.refund_payment(
            task_id="task-f1-8",
            reason="Task cancelled",
        )

        assert result["success"] is True
        assert result["mode"] == "fase1"
        assert result["status"] == "no_funds_moved"
        assert result["tx_hash"] is None
        assert result["error"] is None


# ===========================================================================
# Test: Fase 2 Payment Flow (On-chain escrow via AdvancedEscrowClient)
# ===========================================================================


class FaseClientMock:
    """Mock AdvancedEscrowClient for fase2 testing."""

    def __init__(self):
        self.payer = "0xAgent789"
        self.chain_id = 8453

    def build_payment_info(self, receiver, amount, tier, max_fee_bps):
        return FakeEscrowPaymentInfo(
            operator="0xOperator",
            receiver=receiver,
            token="0xUSDC",
            max_amount=amount,
            pre_approval_expiry=9999999999,
            authorization_expiry=9999999999,
            refund_expiry=9999999999,
            min_fee_bps=0,
            max_fee_bps=max_fee_bps,
            fee_receiver="0xTreasury",
            salt="0x" + "1234" * 16,
        )

    def authorize(self, payment_info):
        return FakeTransactionResult(success=True, tx_hash="0x" + "auth" * 16)

    def release_via_facilitator(self, payment_info):
        return FakeTransactionResult(success=True, tx_hash="0x" + "release" * 14)

    def refund_via_facilitator(self, payment_info):
        return FakeTransactionResult(success=True, tx_hash="0x" + "refund" * 15)


class FakeEscrowPaymentInfo:
    """Mock EscrowPaymentInfo for fase2."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestFase2Flow:
    """Tests for Fase 2 payment flow (on-chain escrow + gasless facilitator)."""

    def _make_fase2_dispatcher(self, sdk_available=True):
        """Create dispatcher in fase2 mode with mocked clients."""

        # Mock TaskTier enum
        class MockTaskTier:
            MICRO = "micro"
            STANDARD = "standard"
            PREMIUM = "premium"
            ENTERPRISE = "enterprise"

        with (
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", False),
            patch(f"{DISPATCHER_MODULE}.FASE2_SDK_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", sdk_available),
            patch(f"{DISPATCHER_MODULE}.TaskTier", MockTaskTier),
            patch(
                f"{DISPATCHER_MODULE}.NETWORK_CONFIG",
                {
                    "base": {
                        "chain_id": 8453,
                        "rpc_url": "https://mainnet.base.org",
                        "tokens": {"USDC": {"decimals": 6}},
                    }
                },
            ),
            patch(f"{DISPATCHER_MODULE}.PLATFORM_FEE_PERCENT", Decimal("0.13")),
            patch(
                f"{DISPATCHER_MODULE}._get_platform_address",
                return_value="0xPlatformAddr",
            ),
            patch.dict(os.environ, {"WALLET_PRIVATE_KEY": TEST_PK}),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="fase2")
            if sdk_available:
                d._sdk = FakeSDK()
            mock_client = FaseClientMock()
            d._fase2_clients = {8453: mock_client}
            return d, mock_client

    @pytest.mark.asyncio
    async def test_fase2_authorize_success(self):
        """Fase 2 authorize should lock funds in escrow via facilitator."""
        d = _make_dispatcher("fase1")  # Start with simple mode
        d.mode = "fase2"  # Override mode

        # Mock the fase2 authorize method directly
        d._authorize_fase2 = AsyncMock(
            return_value={
                "success": True,
                "tx_hash": "0x" + "auth" * 16,
                "mode": "fase2",
                "escrow_status": "deposited",
                "payment_info": FakeEscrowPaymentInfo(receiver="0xPlatformAddr"),
                "payment_info_serialized": {"mode": "fase2"},
                "payer_address": "0xAgent789",
                "error": None,
            }
        )

        result = await d.authorize_payment(
            task_id="task-f2-1",
            receiver="0xWorker",
            amount_usdc=Decimal("10.00"),
            network="base",
        )

        assert result["success"] is True
        assert result["mode"] == "fase2"
        assert result["escrow_status"] == "deposited"
        assert result["tx_hash"] == "0x" + "auth" * 16
        assert result["payer_address"] == "0xAgent789"
        assert result["payment_info_serialized"]["mode"] == "fase2"

    @pytest.mark.asyncio
    async def test_fase2_authorize_sdk_unavailable_fallback(self):
        """Fase 2 should fallback to fase1 if SDK not available during init."""
        with (
            patch(f"{DISPATCHER_MODULE}.FASE2_SDK_AVAILABLE", True),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", False),  # Force fallback
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="fase2")
            assert d.mode == "fase1"

    @pytest.mark.asyncio
    async def test_fase2_authorize_escrow_client_unavailable(self):
        """Fase 2 should fallback to fase1 if AdvancedEscrowClient not available."""
        with (
            patch(f"{DISPATCHER_MODULE}.FASE2_SDK_AVAILABLE", False),  # Force fallback
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="fase2")
            assert d.mode == "fase1"

    @pytest.mark.asyncio
    async def test_fase2_authorize_failure(self):
        """Fase 2 authorize failure should return error."""
        d = _make_dispatcher("fase1")  # Start with simple mode
        d.mode = "fase2"  # Override mode

        # Mock the fase2 authorize method to return failure
        d._authorize_fase2 = AsyncMock(
            return_value={
                "success": False,
                "tx_hash": None,
                "mode": "fase2",
                "escrow_status": "authorize_failed",
                "payment_info": None,
                "payment_info_serialized": None,
                "error": "Escrow authorize failed: Insufficient allowance",
            }
        )

        result = await d.authorize_payment(
            task_id="task-f2-2",
            receiver="0xWorker",
            amount_usdc=Decimal("10.00"),
            network="base",
        )

        assert result["success"] is False
        assert result["mode"] == "fase2"
        assert result["escrow_status"] == "authorize_failed"
        assert "Insufficient allowance" in result["error"]

    @pytest.mark.asyncio
    async def test_fase2_release_success_full_flow(self):
        """Fase 2 release should reconstruct state, release escrow, and disburse."""
        d, mock_client = self._make_fase2_dispatcher()

        # Mock DB state reconstruction
        d._reconstruct_fase2_state = AsyncMock(
            return_value=(
                FakeEscrowPaymentInfo(
                    operator="0xOperator",
                    receiver="0xPlatform",
                    token="0xUSDC",
                    max_amount=10800000,
                    salt="0x" + "1234" * 16,
                ),
                {"network": "base"},
            )
        )

        result = await d.release_payment(
            task_id="task-f2-3",
            worker_address="0xWorker789",
            bounty_amount=Decimal("10.00"),
            network="base",
        )

        assert result["success"] is True
        assert result["mode"] == "fase2"
        assert result["tx_hash"] == "0x" + "c" * 64  # Worker disbursement
        assert result["escrow_release_tx"] == "0x" + "release" * 14
        assert result["fee_tx_hash"] == "0x" + "d" * 64
        assert result["net_to_worker"] == 10.00
        assert result["platform_fee"] == 1.30

    @pytest.mark.asyncio
    async def test_fase2_release_no_escrow_state(self):
        """Fase 2 release without escrow state should fail."""
        d, mock_client = self._make_fase2_dispatcher()
        d._reconstruct_fase2_state = AsyncMock(return_value=(None, {}))

        result = await d.release_payment(
            task_id="task-f2-4",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is False
        assert "payment state not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_fase2_release_escrow_release_failure(self):
        """Fase 2 release should handle escrow release failure."""
        d, mock_client = self._make_fase2_dispatcher()

        d._reconstruct_fase2_state = AsyncMock(
            return_value=(
                FakeEscrowPaymentInfo(salt="0x1234"),
                {"network": "base"},
            )
        )

        # Mock release failure
        mock_client.release_via_facilitator = lambda pi: FakeTransactionResult(
            success=False, error="Release window expired"
        )

        result = await d.release_payment(
            task_id="task-f2-5",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is False
        assert "Release window expired" in result["error"]

    @pytest.mark.asyncio
    async def test_fase2_release_worker_disbursement_failure(self):
        """Fase 2 release should handle worker disbursement failure after escrow release."""
        d, mock_client = self._make_fase2_dispatcher()

        d._reconstruct_fase2_state = AsyncMock(
            return_value=(
                FakeEscrowPaymentInfo(salt="0x1234", receiver="0xPlatform"),
                {"network": "base"},
            )
        )

        # Mock worker disbursement failure
        d._sdk.disburse_to_worker = AsyncMock(
            return_value={"success": False, "error": "Gas price too high"}
        )

        result = await d.release_payment(
            task_id="task-f2-6",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is False
        assert result["escrow_release_tx"] == "0x" + "release" * 14  # Escrow released
        assert "Gas price too high" in result["error"]

    @pytest.mark.asyncio
    async def test_fase2_refund_success(self):
        """Fase 2 refund should refund via facilitator (gasless)."""
        d, mock_client = self._make_fase2_dispatcher()

        d._reconstruct_fase2_state = AsyncMock(
            return_value=(
                FakeEscrowPaymentInfo(salt="0x5678", receiver="0xPlatform"),
                {"network": "base"},
            )
        )

        result = await d.refund_payment(
            task_id="task-f2-7",
            reason="Task cancelled by agent",
        )

        assert result["success"] is True
        assert result["mode"] == "fase2"
        assert result["status"] == "refunded"
        assert result["tx_hash"] == "0x" + "refund" * 15
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_fase2_refund_no_escrow_found(self):
        """Fase 2 refund with no escrow state should be treated as no-op."""
        d, mock_client = self._make_fase2_dispatcher()
        d._reconstruct_fase2_state = AsyncMock(return_value=(None, {}))

        result = await d.refund_payment(
            task_id="task-f2-8",
            reason="No escrow created",
        )

        assert result["success"] is True
        assert result["status"] == "no_escrow_found"
        assert result["tx_hash"] is None

    @pytest.mark.asyncio
    async def test_fase2_refund_failure(self):
        """Fase 2 refund failure should return error."""
        d, mock_client = self._make_fase2_dispatcher()

        d._reconstruct_fase2_state = AsyncMock(
            return_value=(
                FakeEscrowPaymentInfo(salt="0x9abc"),
                {"network": "base"},
            )
        )

        # Mock refund failure
        mock_client.refund_via_facilitator = lambda pi: FakeTransactionResult(
            success=False, error="Refund window closed"
        )

        result = await d.refund_payment(
            task_id="task-f2-9",
            reason="Agent requested refund",
        )

        assert result["success"] is False
        assert result["status"] == "refund_failed"
        assert "Refund window closed" in result["error"]

    @pytest.mark.asyncio
    async def test_fase2_reconstruct_state_success(self):
        """_reconstruct_fase2_state should rebuild PaymentInfo from DB."""
        d, mock_client = self._make_fase2_dispatcher()

        mock_client_obj = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "status": "deposited",
                "metadata": json.dumps(
                    {
                        "payment_info": {
                            "mode": "fase2",
                            "operator": "0xOp",
                            "receiver": "0xRec",
                            "token": "0xTok",
                            "max_amount": 1000000,
                            "pre_approval_expiry": 9999999999,
                            "authorization_expiry": 9999999999,
                            "refund_expiry": 9999999999,
                            "min_fee_bps": 0,
                            "max_fee_bps": 1300,
                            "fee_receiver": "0xFee",
                            "salt": "0xabcd1234",
                            "network": "base",
                        }
                    }
                ),
                "total_amount_usdc": 1.00,
            }
        ]
        mock_client_obj.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        # Mock EscrowPaymentInfo constructor to return our fake object
        with (
            patch("supabase_client.get_client", return_value=mock_client_obj),
            patch(f"{DISPATCHER_MODULE}.EscrowPaymentInfo", FakeEscrowPaymentInfo),
        ):
            pi, pi_data = await d._reconstruct_fase2_state("task-reconstruct")

        assert pi is not None
        assert pi.operator == "0xOp"
        assert pi.receiver == "0xRec"
        assert pi.salt == "0xabcd1234"
        assert pi_data["network"] == "base"

    @pytest.mark.asyncio
    async def test_fase2_reconstruct_state_terminal_status(self):
        """_reconstruct_fase2_state should refuse terminal statuses."""
        d, mock_client = self._make_fase2_dispatcher()

        mock_client_obj = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"status": "released"}]  # Terminal status
        mock_client_obj.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        with patch("supabase_client.get_client", return_value=mock_client_obj):
            pi, pi_data = await d._reconstruct_fase2_state("task-terminal")

        assert pi is None
        assert pi_data == {}

    @pytest.mark.asyncio
    async def test_fase2_reconstruct_state_missing_metadata(self):
        """_reconstruct_fase2_state should handle missing payment_info."""
        d, mock_client = self._make_fase2_dispatcher()

        mock_client_obj = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "status": "deposited",
                "metadata": json.dumps({"other": "data"}),  # No payment_info
                "total_amount_usdc": 5.00,
            }
        ]
        mock_client_obj.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        with patch("supabase_client.get_client", return_value=mock_client_obj):
            pi, pi_data = await d._reconstruct_fase2_state("task-no-metadata")

        assert pi is None
        assert pi_data == {}

    @pytest.mark.asyncio
    async def test_fase2_reconstruct_state_mode_mismatch(self):
        """_reconstruct_fase2_state should reject non-fase2 payment_info."""
        d, mock_client = self._make_fase2_dispatcher()

        mock_client_obj = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "status": "deposited",
                "metadata": json.dumps(
                    {
                        "payment_info": {"mode": "x402r"}  # Wrong mode
                    }
                ),
                "total_amount_usdc": 5.00,
            }
        ]
        mock_client_obj.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_result

        with patch("supabase_client.get_client", return_value=mock_client_obj):
            pi, pi_data = await d._reconstruct_fase2_state("task-wrong-mode")

        assert pi is None
        assert pi_data == {}


# ===========================================================================
# Test: Cross-Mode Fallback Scenarios
# ===========================================================================


class TestCrossModeFallbacks:
    """Tests for cross-mode fallback scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_mode_fallback_cascade(self):
        """Test complete fallback cascade: fase2 → fase1 when dependencies unavailable."""
        with (
            patch(f"{DISPATCHER_MODULE}.FASE2_SDK_AVAILABLE", False),
            patch(f"{DISPATCHER_MODULE}.ADVANCED_ESCROW_AVAILABLE", False),
            patch(f"{DISPATCHER_MODULE}.SDK_AVAILABLE", True),
        ):
            from integrations.x402.payment_dispatcher import PaymentDispatcher

            d = PaymentDispatcher(mode="fase2")
            assert d.mode == "fase1"

    @pytest.mark.asyncio
    async def test_sdk_exception_handling(self):
        """Test that SDK exceptions are properly caught and returned."""
        d = _make_dispatcher("fase1")
        d._sdk.settle_direct_payments = AsyncMock(
            side_effect=RuntimeError("Network timeout")
        )

        result = await d.release_payment(
            task_id="task-exception",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is False
        assert "Network timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_dispatcher_exception_handling_authorize(self):
        """Test that dispatcher-level exceptions in authorize are handled."""
        d = _make_dispatcher("x402r")
        d._authorize_x402r = AsyncMock(side_effect=ValueError("Invalid amount"))

        result = await d.authorize_payment(
            task_id="task-auth-exception",
            receiver="0xAgent",
            amount_usdc=Decimal("-1.00"),  # Invalid
        )

        assert result["success"] is False
        assert "Invalid amount" in result["error"]
        assert result["mode"] == "x402r"

    @pytest.mark.asyncio
    async def test_dispatcher_exception_handling_release(self):
        """Test that dispatcher-level exceptions in release are handled."""
        d = _make_dispatcher("preauth")
        d._release_preauth = AsyncMock(side_effect=KeyError("Missing header"))

        result = await d.release_payment(
            task_id="task-rel-exception",
            worker_address="0xWorker",
            bounty_amount=Decimal("10.00"),
        )

        assert result["success"] is False
        assert "Missing header" in result["error"]
        assert result["mode"] == "preauth"

    @pytest.mark.asyncio
    async def test_dispatcher_exception_handling_refund(self):
        """Test that dispatcher-level exceptions in refund are handled."""
        d = _make_dispatcher("x402r")
        d._refund_x402r = AsyncMock(side_effect=ConnectionError("DB unavailable"))

        result = await d.refund_payment(
            task_id="task-ref-exception",
            agent_address="0xAgent",
        )

        assert result["success"] is False
        assert "DB unavailable" in result["error"]
        assert result["mode"] == "x402r"


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
