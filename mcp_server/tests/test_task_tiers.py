"""
Tests for task_types.tiers module.

Covers:
- TierConfig bounty validation
- TierManager tier determination from bounty
- Worker eligibility checks
- Tier progression suggestions
- Tier statistics
- Edge cases and boundary values
"""

from decimal import Decimal

import pytest

from mcp_server.task_types.tiers import (
    TaskTier,
    TierConfig,
    TierManager,
    TIER_CONFIGS,
    get_tier_for_bounty,
    get_tier_config,
)


@pytest.fixture
def manager():
    return TierManager()


# ═══════════════════════════════════════════════════════════
# TierConfig
# ═══════════════════════════════════════════════════════════

class TestTierConfig:
    """Tests for TierConfig data model."""

    def test_validate_bounty_within_range(self):
        cfg = TIER_CONFIGS[TaskTier.TIER_1]
        valid, msg = cfg.validate_bounty(Decimal("3.00"))
        assert valid is True
        assert msg == ""

    def test_validate_bounty_at_min(self):
        cfg = TIER_CONFIGS[TaskTier.TIER_1]
        valid, _ = cfg.validate_bounty(cfg.min_bounty)
        assert valid is True

    def test_validate_bounty_at_max(self):
        cfg = TIER_CONFIGS[TaskTier.TIER_1]
        valid, _ = cfg.validate_bounty(cfg.max_bounty)
        assert valid is True

    def test_validate_bounty_below_min(self):
        cfg = TIER_CONFIGS[TaskTier.TIER_1]
        valid, msg = cfg.validate_bounty(Decimal("0.50"))
        assert valid is False
        assert "below" in msg.lower()

    def test_validate_bounty_above_max(self):
        cfg = TIER_CONFIGS[TaskTier.TIER_1]
        valid, msg = cfg.validate_bounty(Decimal("999.00"))
        assert valid is False
        assert "exceeds" in msg.lower()

    def test_to_dict(self):
        cfg = TIER_CONFIGS[TaskTier.TIER_2]
        d = cfg.to_dict()
        assert d["tier"] == "tier_2"
        assert d["verification_level"] == "ai_assisted"
        assert "min_bounty" in d

    def test_default_tier_configs_exist(self):
        assert TaskTier.TIER_1 in TIER_CONFIGS
        assert TaskTier.TIER_2 in TIER_CONFIGS
        assert TaskTier.TIER_3 in TIER_CONFIGS

    def test_tier_1_defaults(self):
        cfg = TIER_CONFIGS[TaskTier.TIER_1]
        assert cfg.min_bounty == Decimal("1.00")
        assert cfg.max_bounty == Decimal("5.00")
        assert cfg.min_reputation == 0
        assert cfg.insurance_required is False

    def test_tier_3_requires_insurance(self):
        cfg = TIER_CONFIGS[TaskTier.TIER_3]
        assert cfg.insurance_required is True
        assert cfg.min_reputation == 60


# ═══════════════════════════════════════════════════════════
# TierManager — Determine Tier
# ═══════════════════════════════════════════════════════════

class TestTierDetermination:
    """Tests for determining appropriate tier from bounty."""

    def test_tier_1_bounty(self, manager):
        assert manager.determine_tier(Decimal("3.00")) == TaskTier.TIER_1

    def test_tier_2_bounty(self, manager):
        assert manager.determine_tier(Decimal("20.00")) == TaskTier.TIER_2

    def test_tier_3_bounty(self, manager):
        assert manager.determine_tier(Decimal("100.00")) == TaskTier.TIER_3

    def test_bounty_below_minimum_raises(self, manager):
        with pytest.raises(ValueError, match="below minimum"):
            manager.determine_tier(Decimal("0.01"))

    def test_bounty_above_maximum_raises(self, manager):
        with pytest.raises(ValueError, match="exceeds maximum"):
            manager.determine_tier(Decimal("999.00"))

    def test_bounty_in_gap_rounds_down(self, manager):
        # Between tier 1 max ($5) and tier 2 min ($10) → tier 1
        tier = manager.determine_tier(Decimal("7.00"))
        assert tier == TaskTier.TIER_1

    def test_boundary_tier_1_max(self, manager):
        assert manager.determine_tier(Decimal("5.00")) == TaskTier.TIER_1

    def test_boundary_tier_2_min(self, manager):
        assert manager.determine_tier(Decimal("10.00")) == TaskTier.TIER_2

    def test_boundary_tier_3_max(self, manager):
        assert manager.determine_tier(Decimal("500.00")) == TaskTier.TIER_3


# ═══════════════════════════════════════════════════════════
# TierManager — Worker Eligibility
# ═══════════════════════════════════════════════════════════

class TestWorkerEligibility:
    """Tests for worker eligibility checks."""

    def test_eligible_tier_1_zero_rep(self, manager):
        eligible, reasons = manager.check_worker_eligibility(TaskTier.TIER_1, 0)
        assert eligible is True
        assert len(reasons) == 0

    def test_ineligible_tier_2_low_rep(self, manager):
        eligible, reasons = manager.check_worker_eligibility(TaskTier.TIER_2, 10)
        assert eligible is False
        assert any("reputation" in r.lower() for r in reasons)

    def test_eligible_tier_2_sufficient_rep(self, manager):
        eligible, _ = manager.check_worker_eligibility(TaskTier.TIER_2, 50)
        assert eligible is True

    def test_ineligible_too_many_active_tasks(self, manager):
        eligible, reasons = manager.check_worker_eligibility(
            TaskTier.TIER_1, 100, worker_active_tasks=10,
        )
        assert eligible is False
        assert any("active tasks" in r.lower() for r in reasons)

    def test_ineligible_multiple_reasons(self, manager):
        eligible, reasons = manager.check_worker_eligibility(
            TaskTier.TIER_3, 10, worker_active_tasks=3,
        )
        assert eligible is False
        assert len(reasons) == 2  # low rep + too many tasks


# ═══════════════════════════════════════════════════════════
# TierManager — Accessible Tiers & Progression
# ═══════════════════════════════════════════════════════════

class TestTierProgression:
    """Tests for tier access and progression suggestions."""

    def test_zero_rep_only_tier_1(self, manager):
        accessible = manager.get_accessible_tiers(0)
        assert accessible == [TaskTier.TIER_1]

    def test_high_rep_all_tiers(self, manager):
        accessible = manager.get_accessible_tiers(100)
        assert TaskTier.TIER_1 in accessible
        assert TaskTier.TIER_2 in accessible
        assert TaskTier.TIER_3 in accessible

    def test_suggest_next_from_tier_1(self, manager):
        suggestion = manager.suggest_next_tier(TaskTier.TIER_1, 10)
        assert suggestion is not None
        assert suggestion["next_tier"] == "tier_2"
        assert suggestion["reputation_needed"] == 20  # 30 - 10

    def test_suggest_next_from_tier_3_none(self, manager):
        suggestion = manager.suggest_next_tier(TaskTier.TIER_3, 100)
        assert suggestion is None


# ═══════════════════════════════════════════════════════════
# TierManager — Statistics
# ═══════════════════════════════════════════════════════════

class TestTierStats:
    """Tests for tier statistics."""

    def test_tier_stats_structure(self, manager):
        stats = manager.calculate_tier_stats(TaskTier.TIER_1)
        assert "tier" in stats
        assert "bounty_range" in stats
        assert "requirements" in stats
        assert "expected_hourly_rate" in stats

    def test_tier_stats_bounty_range(self, manager):
        stats = manager.calculate_tier_stats(TaskTier.TIER_2)
        assert stats["bounty_range"]["min"] == "10.00"
        assert stats["bounty_range"]["max"] == "30.00"


# ═══════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_tier_for_bounty(self):
        assert get_tier_for_bounty(3.0) == TaskTier.TIER_1
        assert get_tier_for_bounty(20.0) == TaskTier.TIER_2
        assert get_tier_for_bounty(100.0) == TaskTier.TIER_3

    def test_get_tier_config(self):
        cfg = get_tier_config(TaskTier.TIER_1)
        assert cfg.tier == TaskTier.TIER_1
        assert cfg.min_bounty == Decimal("1.00")
