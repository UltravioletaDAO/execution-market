"""
Tests for the canonical credit-card fee math (Phase 2, SC-004 + SC-008).

Validates that ``compute_lock_amount()`` correctly implements the credit-card
formula: lock enough so the worker receives >= bounty after the on-chain
StaticFeeCalculator(1300 BPS) deducts its 13% fee.

Formula: lock = ceil(bounty * 10000 / (10000 - 1300))
         lock = ceil(bounty * 10000 / 8700)

Invariant: lock * 0.87 >= bounty  (worker always gets at least the bounty)
"""

import os
import pytest
from decimal import Decimal, ROUND_CEILING

# Ensure test environment
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("EM_PAYMENT_MODE", "disabled")

from integrations.x402.payment_dispatcher import (
    compute_lock_amount,
    FASE5_FEE_BPS,
    _compute_treasury_remainder,
)


WORKER_SHARE = Decimal(10000 - FASE5_FEE_BPS) / Decimal(10000)  # 0.87


@pytest.mark.payments
class TestCreditCardFormula:
    """Verify the canonical credit-card formula for lock amounts."""

    @pytest.mark.parametrize(
        "bounty",
        [
            Decimal("0.01"),
            Decimal("0.10"),
            Decimal("0.50"),
            Decimal("1.00"),
            Decimal("5.00"),
            Decimal("10.00"),
            Decimal("25.00"),
            Decimal("100.00"),
            Decimal("1000.00"),
            Decimal("9999.99"),
        ],
    )
    def test_credit_card_formula_worker_gets_bounty(self, bounty: Decimal):
        """Worker must receive >= bounty after 13% on-chain deduction."""
        lock = compute_lock_amount(bounty)

        # Worker gets 87% of lock
        worker_gets = (lock * WORKER_SHARE).quantize(
            Decimal("0.000001"), rounding=ROUND_CEILING
        )

        assert worker_gets >= bounty, (
            f"Worker underpaid: bounty={bounty}, lock={lock}, "
            f"worker_gets={worker_gets} (need >= {bounty})"
        )

    def test_old_formula_underpays(self):
        """Demonstrate the old formula (bounty * 1.13) fails the invariant.

        The old formula computes total = bounty * 1.13, but on-chain the fee
        calculator takes 13% of the *total* (not 13% of bounty).  This means
        the worker gets: total * 0.87 = bounty * 1.13 * 0.87 = bounty * 0.9831
        which is ~1.7% less than the bounty.
        """
        bounty = Decimal("10.00")

        # Old (wrong) formula
        old_total = (bounty * Decimal("1.13")).quantize(Decimal("0.000001"))
        old_worker_gets = (old_total * WORKER_SHARE).quantize(Decimal("0.000001"))

        # New (correct) formula
        new_lock = compute_lock_amount(bounty)
        new_worker_gets = (new_lock * WORKER_SHARE).quantize(Decimal("0.000001"))

        # Old formula: worker gets $9.8310, NOT >= $10.00 => FAIL
        assert old_worker_gets < bounty, (
            f"Expected old formula to underpay but got {old_worker_gets} >= {bounty}"
        )

        # New formula: worker gets >= $10.00 => PASS
        assert new_worker_gets >= bounty, (
            f"New formula should guarantee bounty but got {new_worker_gets} < {bounty}"
        )

    @pytest.mark.parametrize(
        "bounty",
        [
            Decimal("0.01"),
            Decimal("0.000001"),
            Decimal("0.02"),
            Decimal("0.05"),
        ],
    )
    def test_micro_bounty_no_rounding_loss(self, bounty: Decimal):
        """Micro-bounties ($0.01 and below) must not lose to rounding.

        USDC has 6 decimals, so the smallest representable amount is 0.000001.
        The lock amount must be quantized to 6 decimals with ROUND_CEILING to
        ensure the worker never loses even 1 unit.
        """
        lock = compute_lock_amount(bounty)

        # Lock must be at least bounty (you can't lock less than what you owe)
        assert lock >= bounty, f"Lock {lock} < bounty {bounty}"

        # Worker share check
        worker_gets = (lock * WORKER_SHARE).quantize(
            Decimal("0.000001"), rounding=ROUND_CEILING
        )
        assert worker_gets >= bounty, (
            f"Micro-bounty rounding loss: bounty={bounty}, lock={lock}, "
            f"worker_gets={worker_gets}"
        )

        # Lock must be quantized to 6 decimals
        assert lock == lock.quantize(Decimal("0.000001")), (
            f"Lock {lock} not quantized to 6 decimals"
        )

    def test_compute_lock_amount_uses_ceiling(self):
        """Verify ROUND_CEILING is used (never round down, which would underpay)."""
        # bounty = 0.01 => lock = 0.01 * 10000 / 8700 = 0.011494252873...
        # With ROUND_CEILING this becomes 0.011495
        bounty = Decimal("0.01")
        lock = compute_lock_amount(bounty)
        exact = bounty * Decimal(10000) / Decimal(8700)
        truncated = exact.quantize(Decimal("0.000001"))  # default rounding

        # Lock must be >= exact value (ceiling, not floor)
        assert lock >= exact, f"Lock {lock} < exact {exact}"
        # And if truncated is different from ceiling, lock should be ceiling
        if truncated < exact:
            assert lock > truncated, (
                f"Lock should use CEILING but got {lock} == {truncated}"
            )

    def test_default_fee_bps(self):
        """Default fee_bps is 1300 (13%)."""
        bounty = Decimal("1.00")
        lock_default = compute_lock_amount(bounty)
        lock_explicit = compute_lock_amount(bounty, fee_bps=1300)
        assert lock_default == lock_explicit

    def test_custom_fee_bps(self):
        """Custom fee_bps works correctly (e.g., 500 = 5%)."""
        bounty = Decimal("10.00")
        lock = compute_lock_amount(bounty, fee_bps=500)
        expected = (bounty * Decimal(10000) / Decimal(9500)).quantize(
            Decimal("0.000001"), rounding=ROUND_CEILING
        )
        assert lock == expected

    def test_zero_fee_bps(self):
        """With 0% fee, lock == bounty."""
        bounty = Decimal("10.00")
        lock = compute_lock_amount(bounty, fee_bps=0)
        assert lock == bounty


@pytest.mark.payments
class TestComputeTreasuryRemainder:
    """Verify _compute_treasury_remainder is advisory and correct."""

    def test_basic_remainder(self):
        """Treasury gets lock - bounty (after protocol fee)."""
        bounty = Decimal("10.00")
        lock = compute_lock_amount(bounty)
        fee = _compute_treasury_remainder(bounty, lock, on_chain_fee_bps=0)

        # Fee should be lock - bounty
        expected = (lock - bounty).quantize(Decimal("0.000001"))
        assert fee == expected, f"Expected {expected}, got {fee}"

    def test_with_protocol_fee(self):
        """Protocol fee reduces treasury share."""
        bounty = Decimal("10.00")
        lock = compute_lock_amount(bounty)

        fee_no_protocol = _compute_treasury_remainder(bounty, lock, on_chain_fee_bps=0)
        fee_with_protocol = _compute_treasury_remainder(
            bounty, lock, on_chain_fee_bps=200
        )  # 2%

        assert fee_with_protocol < fee_no_protocol, (
            f"Protocol fee should reduce treasury: {fee_with_protocol} >= {fee_no_protocol}"
        )

    def test_negative_clamped_to_zero(self):
        """If protocol fee exceeds platform margin, treasury gets 0 (not negative)."""
        bounty = Decimal("10.00")
        lock = compute_lock_amount(bounty)

        # With a huge protocol fee (99%), treasury would go negative
        fee = _compute_treasury_remainder(bounty, lock, on_chain_fee_bps=9900)
        assert fee == Decimal("0"), f"Expected 0, got {fee}"

    def test_minimum_fee(self):
        """Non-zero treasury amount < $0.01 is rounded up to $0.01."""
        bounty = Decimal("0.01")
        lock = compute_lock_amount(bounty)
        fee = _compute_treasury_remainder(bounty, lock, on_chain_fee_bps=0)

        # For $0.01 bounty, fee would be tiny — should be clamped to $0.01 minimum
        if fee > Decimal("0"):
            assert fee >= Decimal("0.01"), f"Fee {fee} below $0.01 minimum"


@pytest.mark.payments
class TestStorePreauthValidation:
    """Verify store_preauth validates valid_before timestamps (SC-012)."""

    def test_past_valid_before_raises(self):
        """valid_before in the past must raise ValueError."""
        from integrations.x402.payment_dispatcher import PaymentDispatcher

        dispatcher = PaymentDispatcher()

        past_ts = 1000000  # year 1970

        with pytest.raises(ValueError, match="must be in the future"):
            dispatcher.store_preauth(
                task_id="test-task-001",
                payload_json='{"payload":{"authorization":{"from":"0xabc"},"paymentInfo":{"maxAmount":"100000"}}}',
                valid_before=past_ts,
                network="base",
            )

    def test_far_future_valid_before_raises(self):
        """valid_before more than 14 days out must raise ValueError."""
        import time as _time
        from integrations.x402.payment_dispatcher import PaymentDispatcher

        dispatcher = PaymentDispatcher()

        far_future = int(_time.time()) + 86400 * 30  # 30 days from now

        with pytest.raises(ValueError, match="exceeds 14-day maximum"):
            dispatcher.store_preauth(
                task_id="test-task-002",
                payload_json='{"payload":{"authorization":{"from":"0xabc"},"paymentInfo":{"maxAmount":"100000"}}}',
                valid_before=far_future,
                network="base",
            )

    def test_valid_future_timestamp_accepted(self):
        """valid_before within 14 days should not raise on time validation.

        Note: The DB insert may fail in test (no Supabase), but time
        validation itself should pass.
        """
        import time as _time
        from integrations.x402.payment_dispatcher import PaymentDispatcher

        dispatcher = PaymentDispatcher()

        valid_ts = int(_time.time()) + 3600  # 1 hour from now

        # This should pass time validation but may fail on DB insert (expected in tests)
        try:
            dispatcher.store_preauth(
                task_id="test-task-003",
                payload_json='{"payload":{"authorization":{"from":"0xabc"},"paymentInfo":{"maxAmount":"100000"}}}',
                valid_before=valid_ts,
                network="base",
            )
            # If we get here, DB was available — check it didn't error on validation
            # (success may be True or False depending on DB state)
        except ValueError:
            # Should NOT raise ValueError for valid timestamps
            pytest.fail("Valid timestamp should not raise ValueError")
        except Exception:
            # DB/import errors are expected in unit tests — time validation passed
            pass
