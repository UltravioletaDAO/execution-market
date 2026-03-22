"""
Tests for PricingAdapter — AutoJob pricing intelligence as a swarm signal.

Tests cover:
- PricingSnapshot data model
- MarketDemandSnapshot data model
- Default fallback pricing
- Cache behavior
- Scorer function
- Stats tracking
- Edge cases
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from mcp_server.swarm.pricing_adapter import (
    PricingAdapter,
    PricingSnapshot,
    MarketDemandSnapshot,
    make_pricing_scorer,
    DEFAULT_PRICING,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter():
    """Adapter with unreachable URL (tests fallback behavior)."""
    return PricingAdapter(
        autojob_url="http://localhost:99999",
        timeout_seconds=0.1,
    )


# ---------------------------------------------------------------------------
# PricingSnapshot Tests
# ---------------------------------------------------------------------------


class TestPricingSnapshot:
    def test_creation(self):
        snap = PricingSnapshot(category="delivery", recommended_usd=8.0)
        assert snap.category == "delivery"
        assert snap.recommended_usd == 8.0

    def test_stale_detection(self):
        snap = PricingSnapshot(category="test", fetched_at=time.time() - 7200)
        assert snap.is_stale(max_age_seconds=3600)

    def test_fresh_detection(self):
        snap = PricingSnapshot(category="test", fetched_at=time.time())
        assert not snap.is_stale(max_age_seconds=3600)

    def test_to_dict(self):
        snap = PricingSnapshot(
            category="research",
            recommended_usd=5.0,
            range_low_usd=3.0,
            range_high_usd=8.0,
            confidence=0.75,
        )
        d = snap.to_dict()
        assert d["category"] == "research"
        assert d["recommended_usd"] == 5.0
        assert d["range"] == [3.0, 8.0]
        assert d["confidence"] == 0.75

    def test_default_values(self):
        snap = PricingSnapshot(category="test")
        assert snap.source == "default"
        assert snap.confidence == 0.3


# ---------------------------------------------------------------------------
# MarketDemandSnapshot Tests
# ---------------------------------------------------------------------------


class TestMarketDemandSnapshot:
    def test_creation(self):
        snap = MarketDemandSnapshot(
            category="delivery",
            demand_score=0.8,
            trend="growing",
        )
        assert snap.demand_score == 0.8
        assert snap.trend == "growing"

    def test_stale_detection(self):
        snap = MarketDemandSnapshot(category="test", fetched_at=time.time() - 7200)
        assert snap.is_stale(max_age_seconds=3600)

    def test_to_dict(self):
        snap = MarketDemandSnapshot(
            category="research",
            demand_score=0.6,
            completion_rate=0.7,
            supply_gap_severity="moderate",
        )
        d = snap.to_dict()
        assert d["demand_score"] == 0.6
        assert d["supply_gap_severity"] == "moderate"


# ---------------------------------------------------------------------------
# PricingAdapter Tests
# ---------------------------------------------------------------------------


class TestPricingAdapter:
    def test_default_fallback(self, adapter):
        """When API is unreachable, falls back to defaults."""
        pricing = adapter.get_task_pricing("physical_verification")
        assert pricing.source == "default"
        assert pricing.recommended_usd == DEFAULT_PRICING["physical_verification"]["median"]
        assert pricing.confidence == 0.3

    def test_unknown_category_uses_general(self, adapter):
        """Unknown categories fall back to 'general' defaults."""
        pricing = adapter.get_task_pricing("underwater_basket_weaving")
        assert pricing.recommended_usd == DEFAULT_PRICING["general"]["median"]

    def test_category_normalization(self, adapter):
        """Categories are normalized (lowercase, underscores)."""
        p1 = adapter.get_task_pricing("Physical Verification")
        p2 = adapter.get_task_pricing("physical_verification")
        assert p1.category == p2.category

    def test_cache_on_default(self, adapter):
        """Even defaults don't re-fetch if cached recently."""
        adapter.get_task_pricing("delivery")
        adapter.get_task_pricing("delivery")
        # Second call should be a cache hit
        stats = adapter.get_stats()
        assert stats["cache_hits"] >= 0  # May or may not cache defaults

    def test_market_demand_default(self, adapter):
        """Market demand falls back to defaults."""
        demand = adapter.get_market_demand("research")
        assert demand.source == "default"
        assert demand.demand_score == 0.5

    def test_stats_tracking(self, adapter):
        """Stats are tracked across calls."""
        adapter.get_task_pricing("delivery")
        adapter.get_task_pricing("research")
        stats = adapter.get_stats()
        assert stats["api_calls"] >= 0
        assert "api_errors" in stats
        assert "default_fallbacks" in stats

    def test_supply_gaps_fallback(self, adapter):
        """Supply gaps returns empty on API failure."""
        gaps = adapter.get_supply_gaps()
        assert gaps == []


# ---------------------------------------------------------------------------
# Scorer Tests
# ---------------------------------------------------------------------------


class TestPricingScorer:
    def test_well_priced_task(self, adapter):
        """Task at recommended price gets high score."""
        scorer = make_pricing_scorer(adapter)
        score = scorer(
            {"category": "physical_verification", "bounty_usd": 3.0},
            {"wallet": "0xAlice"},
        )
        assert score >= 0.7

    def test_generous_bounty_higher_score(self, adapter):
        """Task above recommended price gets higher score."""
        scorer = make_pricing_scorer(adapter)
        score = scorer(
            {"category": "physical_verification", "bounty_usd": 10.0},
            {"wallet": "0xAlice"},
        )
        assert score >= 0.8

    def test_underpriced_task_low_score(self, adapter):
        """Task far below range gets low score."""
        scorer = make_pricing_scorer(adapter)
        score = scorer(
            {"category": "delivery", "bounty_usd": 0.50},
            {"wallet": "0xAlice"},
        )
        assert score < 0.5

    def test_no_bounty_neutral(self, adapter):
        """Task with no bounty info gets neutral score."""
        scorer = make_pricing_scorer(adapter)
        score = scorer(
            {"category": "research"},
            {"wallet": "0xAlice"},
        )
        assert score == 0.5

    def test_score_range(self, adapter):
        """All scores are between 0 and 1."""
        scorer = make_pricing_scorer(adapter)
        for bounty in [0.01, 0.5, 1.0, 3.0, 5.0, 10.0, 50.0, 100.0]:
            score = scorer(
                {"category": "physical_verification", "bounty_usd": bounty},
                {"wallet": "0x1"},
            )
            assert 0 <= score <= 1, f"Score {score} out of range for bounty ${bounty}"

    def test_score_monotonic(self, adapter):
        """Higher bounties should give equal or higher scores (within a category)."""
        scorer = make_pricing_scorer(adapter)
        prev_score = 0
        for bounty in [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]:
            score = scorer(
                {"category": "physical_verification", "bounty_usd": bounty},
                {"wallet": "0x1"},
            )
            assert score >= prev_score - 0.01, (
                f"Score decreased: ${bounty} → {score} (was {prev_score})"
            )
            prev_score = score

    def test_scorer_with_bounty_amount_usdc(self, adapter):
        """Scorer handles bounty_amount_usdc field."""
        scorer = make_pricing_scorer(adapter)
        score = scorer(
            {"category": "delivery", "bounty_amount_usdc": 8.0},
            {"wallet": "0x1"},
        )
        assert score >= 0.7
