"""Tests for the fee calculator."""

import pytest

from em_plugin_sdk.fees import calculate_fee, calculate_reverse_fee, get_fee_rate, FEE_RATES
from em_plugin_sdk.models import TaskCategory


class TestFeeCalculation:
    def test_standard_13_percent(self):
        fee = calculate_fee(10.00, "simple_action")
        assert fee.fee_rate == 0.13
        assert fee.fee_amount == 1.30
        assert fee.worker_amount == 8.70
        assert fee.gross_amount == 10.00

    def test_reduced_12_percent(self):
        fee = calculate_fee(10.00, "knowledge_access")
        assert fee.fee_rate == 0.12
        assert fee.fee_amount == 1.20
        assert fee.worker_amount == 8.80

    def test_incentivized_11_percent(self):
        fee = calculate_fee(10.00, "human_authority")
        assert fee.fee_rate == 0.11
        assert fee.fee_amount == 1.10
        assert fee.worker_amount == 8.90

    def test_minimum_fee(self):
        """Very small bounties still have $0.01 minimum fee."""
        fee = calculate_fee(0.05, "simple_action")
        assert fee.fee_amount == 0.01

    def test_accepts_enum(self):
        fee = calculate_fee(10.00, TaskCategory.PHYSICAL_PRESENCE)
        assert fee.category == "physical_presence"
        assert fee.fee_rate == 0.13

    def test_unknown_category_uses_default(self):
        fee = calculate_fee(10.00, "unknown_category")
        assert fee.fee_rate == 0.13

    def test_zero_bounty_raises(self):
        with pytest.raises(ValueError):
            calculate_fee(0, "simple_action")

    def test_negative_bounty_raises(self):
        with pytest.raises(ValueError):
            calculate_fee(-5, "simple_action")

    def test_all_categories_have_rates(self):
        for cat in TaskCategory:
            rate = get_fee_rate(cat)
            assert 0.11 <= rate <= 0.15


class TestReverseFee:
    def test_reverse_fee_basic(self):
        """Worker wants $10 → what bounty to post?"""
        fee = calculate_reverse_fee(10.00, "simple_action")
        # bounty = 10.00 / (1 - 0.13) = 11.49
        assert fee.gross_amount == 11.49
        assert fee.worker_amount == 10.00  # $11.49 - $1.49 = $10.00

    def test_reverse_fee_zero_raises(self):
        with pytest.raises(ValueError):
            calculate_reverse_fee(0, "simple_action")


class TestGetFeeRate:
    def test_string_category(self):
        assert get_fee_rate("physical_presence") == 0.13

    def test_enum_category(self):
        assert get_fee_rate(TaskCategory.HUMAN_AUTHORITY) == 0.11

    def test_all_21_categories_covered(self):
        assert len(FEE_RATES) == 21
