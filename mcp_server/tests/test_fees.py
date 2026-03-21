"""
Tests for Fee Collection Module (NOW-025, NOW-026)

Tests the FeeManager class and related functionality.
"""

import pytest

pytestmark = pytest.mark.payments
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from ..models import TaskCategory
from ..payments.fees import (
    FeeManager,
    FeeBreakdown,
    FeeStatus,
    FEE_RATES,
    MIN_FEE_AMOUNT,
    MAX_FEE_PERCENT,
    calculate_platform_fee,
    get_fee_rate_for_category,
    get_all_fee_rates,
)


class TestFeeRates:
    """Test fee rate configuration."""

    def test_all_categories_have_rates(self):
        """All task categories should have defined fee rates."""
        for category in TaskCategory:
            assert category in FEE_RATES, f"Missing rate for {category}"

    def test_rates_within_bounds(self):
        """All rates should be between 0 and MAX_FEE_PERCENT."""
        for category, rate in FEE_RATES.items():
            assert Decimal("0") <= rate <= MAX_FEE_PERCENT, (
                f"Invalid rate for {category}: {rate}"
            )

    def test_expected_rates(self):
        """Verify specific rates match requirements."""
        assert FEE_RATES[TaskCategory.PHYSICAL_PRESENCE] == Decimal("0.13")  # 13%
        assert FEE_RATES[TaskCategory.KNOWLEDGE_ACCESS] == Decimal("0.12")  # 12%
        assert FEE_RATES[TaskCategory.HUMAN_AUTHORITY] == Decimal("0.11")  # 11%
        assert FEE_RATES[TaskCategory.SIMPLE_ACTION] == Decimal("0.13")  # 13%
        assert FEE_RATES[TaskCategory.DIGITAL_PHYSICAL] == Decimal("0.12")  # 12%


class TestFeeManager:
    """Test FeeManager class."""

    @pytest.fixture
    def manager(self):
        """Create a FeeManager instance."""
        return FeeManager(treasury_wallet="0x1234567890123456789012345678901234567890")

    def test_init_with_defaults(self, manager):
        """Manager should initialize with default rates."""
        assert manager.fee_rates == FEE_RATES
        assert manager.treasury_wallet == "0x1234567890123456789012345678901234567890"

    def test_init_with_custom_rates(self):
        """Manager should accept custom rates."""
        custom_rates = {TaskCategory.SIMPLE_ACTION: Decimal("0.05")}
        manager = FeeManager(custom_rates=custom_rates)
        assert manager.fee_rates[TaskCategory.SIMPLE_ACTION] == Decimal("0.05")

    def test_get_fee_rate(self, manager):
        """Should return correct rate for each category."""
        assert manager.get_fee_rate(TaskCategory.PHYSICAL_PRESENCE) == Decimal("0.13")
        assert manager.get_fee_rate(TaskCategory.HUMAN_AUTHORITY) == Decimal("0.11")


class TestFeeCalculation:
    """Test fee calculation methods."""

    @pytest.fixture
    def manager(self):
        return FeeManager()

    def test_calculate_fee_physical_presence(self, manager):
        """Test 13% fee for physical presence tasks."""
        breakdown = manager.calculate_fee(
            Decimal("100"), TaskCategory.PHYSICAL_PRESENCE
        )

        assert breakdown.gross_amount == Decimal("100")
        assert breakdown.fee_rate == Decimal("0.13")
        assert breakdown.fee_amount == Decimal("13.00")
        assert breakdown.worker_amount == Decimal("87.00")
        assert breakdown.category == TaskCategory.PHYSICAL_PRESENCE
        assert not breakdown.is_waived

    def test_calculate_fee_human_authority(self, manager):
        """Test 11% fee for human authority tasks."""
        breakdown = manager.calculate_fee(Decimal("100"), TaskCategory.HUMAN_AUTHORITY)

        assert breakdown.fee_rate == Decimal("0.11")
        assert breakdown.fee_amount == Decimal("11.00")
        assert breakdown.worker_amount == Decimal("89.00")

    def test_calculate_fee_rounding(self, manager):
        """Test proper rounding of fee amounts."""
        breakdown = manager.calculate_fee(Decimal("15.50"), TaskCategory.SIMPLE_ACTION)

        # 15.50 * 0.13 = 2.015 -> 2.02 (rounded)
        assert breakdown.fee_amount == Decimal("2.02")
        assert breakdown.worker_amount == Decimal("13.48")

    def test_calculate_fee_minimum_enforced(self, manager):
        """Test minimum fee is enforced."""
        # Very small bounty: $0.01 * 0.13 = $0.0013 -> minimum fee applies
        breakdown = manager.calculate_fee(Decimal("0.01"), TaskCategory.SIMPLE_ACTION)

        # $0.01 * 0.13 = $0.0013, minimum fee ($0.01) should apply
        assert breakdown.fee_amount >= MIN_FEE_AMOUNT

    def test_calculate_fee_zero_bounty_raises(self, manager):
        """Zero bounty should raise ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            manager.calculate_fee(Decimal("0"), TaskCategory.SIMPLE_ACTION)

    def test_calculate_fee_negative_bounty_raises(self, manager):
        """Negative bounty should raise ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            manager.calculate_fee(Decimal("-10"), TaskCategory.SIMPLE_ACTION)

    def test_calculate_reverse_fee(self, manager):
        """Test reverse fee calculation."""
        # If worker wants exactly $10, what bounty should agent post?
        breakdown = manager.calculate_reverse_fee(
            Decimal("10"), TaskCategory.SIMPLE_ACTION
        )

        # bounty = 10 / (1 - 0.13) = 10 / 0.87 = 11.49
        assert breakdown.gross_amount == Decimal("11.49")
        # Worker should get approximately $10 (may differ slightly due to rounding)
        assert abs(breakdown.worker_amount - Decimal("10")) < Decimal("0.01")


class TestFeeWaivers:
    """Test fee waiver functionality."""

    @pytest.fixture
    def manager(self):
        return FeeManager()

    def test_register_waiver_code(self, manager):
        """Test registering a waiver code."""
        manager.register_waiver_code(
            code="LAUNCH2026",
            reason="Launch promotion",
            max_uses=100,
        )

        assert "LAUNCH2026" in manager._waiver_codes
        assert manager._waiver_codes["LAUNCH2026"]["reason"] == "Launch promotion"

    def test_calculate_fee_with_waiver(self, manager):
        """Test fee calculation with valid waiver."""
        manager.register_waiver_code("FREEFEE", reason="Test waiver")

        breakdown = manager.calculate_fee(
            Decimal("100"),
            TaskCategory.SIMPLE_ACTION,
            waiver_code="FREEFEE",
        )

        assert breakdown.is_waived
        assert breakdown.fee_amount == Decimal("0")
        assert breakdown.worker_amount == Decimal("100")
        assert breakdown.waiver_reason == "Test waiver"

    def test_calculate_fee_with_invalid_waiver(self, manager):
        """Test fee calculation with invalid waiver code."""
        breakdown = manager.calculate_fee(
            Decimal("100"),
            TaskCategory.SIMPLE_ACTION,
            waiver_code="INVALID",
        )

        assert not breakdown.is_waived
        assert breakdown.fee_amount == Decimal("13.00")

    def test_waiver_expiration(self, manager):
        """Test that expired waivers are not applied."""
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        manager.register_waiver_code(
            code="EXPIRED",
            reason="Expired promo",
            expires_at=yesterday,
        )

        breakdown = manager.calculate_fee(
            Decimal("100"),
            TaskCategory.SIMPLE_ACTION,
            waiver_code="EXPIRED",
        )

        assert not breakdown.is_waived
        assert breakdown.fee_amount == Decimal("13.00")


class TestFeeCollection:
    """Test fee collection functionality."""

    @pytest.fixture
    def manager(self):
        return FeeManager()

    @pytest.mark.asyncio
    async def test_collect_fee(self, manager):
        """Test recording a collected fee."""
        breakdown = manager.calculate_fee(
            Decimal("100"), TaskCategory.PHYSICAL_PRESENCE
        )

        collected = await manager.collect_fee(
            task_id="task-123",
            breakdown=breakdown,
            release_tx="0xabcdef123456",
            agent_id="agent-1",
            worker_id="worker-1",
        )

        assert collected.task_id == "task-123"
        assert collected.amount == Decimal("13.00")
        assert collected.status == FeeStatus.COLLECTED
        assert collected.tx_hash == "0xabcdef123456"
        assert collected.agent_id == "agent-1"
        assert collected.worker_id == "worker-1"

    @pytest.mark.asyncio
    async def test_collect_waived_fee(self, manager):
        """Test recording a waived fee."""
        manager.register_waiver_code("FREE", reason="Free!")
        breakdown = manager.calculate_fee(
            Decimal("100"),
            TaskCategory.SIMPLE_ACTION,
            waiver_code="FREE",
        )

        collected = await manager.collect_fee(
            task_id="task-456",
            breakdown=breakdown,
            release_tx="0x123",
        )

        assert collected.status == FeeStatus.WAIVED
        assert collected.amount == Decimal("0")

    @pytest.mark.asyncio
    async def test_refund_fee(self, manager):
        """Test refunding a collected fee."""
        breakdown = manager.calculate_fee(Decimal("100"), TaskCategory.SIMPLE_ACTION)
        collected = await manager.collect_fee(
            task_id="task-789",
            breakdown=breakdown,
            release_tx="0xabc",
        )

        refunded = await manager.refund_fee(
            fee_id=collected.id,
            reason="Task cancelled",
            refund_tx="0xdef",
        )

        assert refunded.status == FeeStatus.REFUNDED
        assert refunded.metadata["refund_reason"] == "Task cancelled"

    @pytest.mark.asyncio
    async def test_refund_nonexistent_fee(self, manager):
        """Test refunding a non-existent fee raises error."""
        with pytest.raises(ValueError, match="not found"):
            await manager.refund_fee("fake-id", "reason")


class TestFeeAnalytics:
    """Test fee analytics functionality."""

    @pytest.fixture
    def manager(self):
        return FeeManager()

    @pytest.mark.asyncio
    async def test_get_analytics_empty(self, manager):
        """Test analytics with no fees."""
        analytics = manager.get_analytics()

        assert analytics.total_collected == Decimal("0")
        assert analytics.transaction_count == 0

    @pytest.mark.asyncio
    async def test_get_analytics_with_data(self, manager):
        """Test analytics with collected fees."""
        # Collect some fees
        for i in range(5):
            breakdown = manager.calculate_fee(
                Decimal("100"),
                TaskCategory.PHYSICAL_PRESENCE,
            )
            await manager.collect_fee(
                task_id=f"task-{i}",
                breakdown=breakdown,
                release_tx=f"0x{i}",
                agent_id="agent-1",
            )

        analytics = manager.get_analytics()

        assert analytics.total_collected == Decimal("65.00")  # 5 * $13
        assert analytics.transaction_count == 5
        assert analytics.by_category.get("physical_presence") == Decimal("65.00")

    def test_get_fee_structure(self, manager):
        """Test getting fee structure information."""
        structure = manager.get_fee_structure()

        assert "rates_by_category" in structure
        assert "default_rate" in structure
        assert "limits" in structure
        assert "distribution" in structure

        # Check specific rate
        assert (
            structure["rates_by_category"]["physical_presence"]["rate_percent"] == 13.0
        )


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_calculate_platform_fee(self):
        """Test convenience function for fee calculation."""
        result = calculate_platform_fee(100.0, TaskCategory.SIMPLE_ACTION)

        assert result["fee_rate_percent"] == 13.0
        assert result["fee_amount"] == 13.0
        assert result["worker_amount"] == 87.0

    def test_get_fee_rate_for_category(self):
        """Test getting fee rate for a category."""
        rate = get_fee_rate_for_category(TaskCategory.HUMAN_AUTHORITY)
        assert rate == 0.11

    def test_get_all_fee_rates(self):
        """Test getting all fee rates."""
        rates = get_all_fee_rates()

        assert len(rates) == len(TaskCategory)
        assert rates["physical_presence"] == 0.13
        assert rates["human_authority"] == 0.11


class TestFeeBreakdownSerialization:
    """Test FeeBreakdown serialization."""

    def test_to_dict(self):
        """Test FeeBreakdown.to_dict() method."""
        breakdown = FeeBreakdown(
            gross_amount=Decimal("100"),
            fee_rate=Decimal("0.13"),
            fee_amount=Decimal("13.00"),
            worker_amount=Decimal("87.00"),
            treasury_wallet="0x123",
            category=TaskCategory.PHYSICAL_PRESENCE,
        )

        result = breakdown.to_dict()

        assert result["gross_amount"] == 100.0
        assert result["fee_rate"] == 0.13
        assert result["fee_rate_percent"] == 13.0
        assert result["fee_amount"] == 13.0
        assert result["worker_amount"] == 87.0
        assert result["worker_percent"] == 87.0
        assert result["category"] == "physical_presence"
        assert result["is_waived"] is False
