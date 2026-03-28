"""
Test Suite: PricingAdapter — AutoJob Pricing Intelligence
============================================================

Tests cover:
    1. PricingSnapshot and MarketDemandSnapshot data types
    2. Task pricing (API, cache, default fallback)
    3. Market demand signals
    4. Supply gaps
    5. Scorer factory (competitive pricing evaluation)
    6. Category normalization
    7. Cache behavior (TTL, stale fallback)
    8. Statistics tracking
"""

import time
import pytest
from unittest.mock import patch, MagicMock

from mcp_server.swarm.pricing_adapter import (
    PricingAdapter,
    PricingSnapshot,
    MarketDemandSnapshot,
    make_pricing_scorer,
    DEFAULT_PRICING,
)


# ══════════════════════════════════════════════════════════════
# Data Type Tests
# ══════════════════════════════════════════════════════════════


class TestPricingSnapshot:
    def test_defaults(self):
        ps = PricingSnapshot(category="photo")
        assert ps.recommended_usd == 3.0
        assert ps.range_low_usd == 1.50
        assert ps.range_high_usd == 5.0
        assert ps.source == "default"

    def test_is_stale_new(self):
        ps = PricingSnapshot(category="photo", fetched_at=time.time())
        assert ps.is_stale(3600) is False

    def test_is_stale_old(self):
        ps = PricingSnapshot(category="photo", fetched_at=time.time() - 7200)
        assert ps.is_stale(3600) is True

    def test_to_dict(self):
        ps = PricingSnapshot(
            category="delivery",
            recommended_usd=8.0,
            range_low_usd=5.0,
            range_high_usd=15.0,
            confidence=0.8,
        )
        d = ps.to_dict()
        assert d["category"] == "delivery"
        assert d["recommended_usd"] == 8.0
        assert d["range"] == [5.0, 15.0]
        assert d["confidence"] == 0.8


class TestMarketDemandSnapshot:
    def test_defaults(self):
        ms = MarketDemandSnapshot(category="photo")
        assert ms.demand_score == 0.5
        assert ms.trend == "stable"
        assert ms.supply_gap_severity == "none"

    def test_is_stale(self):
        ms = MarketDemandSnapshot(category="photo", fetched_at=time.time())
        assert ms.is_stale(3600) is False

    def test_to_dict(self):
        ms = MarketDemandSnapshot(category="research", demand_score=0.8, trend="growing")
        d = ms.to_dict()
        assert d["category"] == "research"
        assert d["demand_score"] == 0.8
        assert d["trend"] == "growing"


# ══════════════════════════════════════════════════════════════
# Adapter Tests — Pricing
# ══════════════════════════════════════════════════════════════


class TestGetTaskPricing:
    def test_default_fallback(self):
        adapter = PricingAdapter()
        pricing = adapter.get_task_pricing("physical_verification")
        assert pricing.source == "default"
        assert pricing.recommended_usd == DEFAULT_PRICING["physical_verification"]["median"]

    def test_unknown_category_uses_general(self):
        adapter = PricingAdapter()
        pricing = adapter.get_task_pricing("alien_abduction")
        assert pricing.recommended_usd == DEFAULT_PRICING["general"]["median"]

    def test_cache_hit(self):
        adapter = PricingAdapter()
        cached = PricingSnapshot(
            category="photo", recommended_usd=4.0,
            fetched_at=time.time(), source="api",
        )
        adapter._pricing_cache["photo"] = cached

        result = adapter.get_task_pricing("photo")
        assert result.recommended_usd == 4.0
        assert result.source == "api"
        assert adapter._stats["cache_hits"] == 1

    def test_stale_cache_triggers_fetch(self):
        adapter = PricingAdapter()
        old = PricingSnapshot(
            category="photo", recommended_usd=4.0,
            fetched_at=time.time() - 7200, source="api",
        )
        adapter._pricing_cache["photo"] = old

        # API will fail → stale cache returned
        result = adapter.get_task_pricing("photo")
        assert result.recommended_usd == 4.0  # Stale cache

    def test_category_normalization(self):
        adapter = PricingAdapter()
        result = adapter.get_task_pricing("Physical Verification")
        assert result.category == "physical_verification"

    def test_empty_category_defaults_to_general(self):
        adapter = PricingAdapter()
        result = adapter.get_task_pricing("")
        assert result.category == "general"

    def test_delivery_pricing(self):
        adapter = PricingAdapter()
        result = adapter.get_task_pricing("delivery")
        assert result.recommended_usd == 8.0

    def test_stats_tracked(self):
        adapter = PricingAdapter()
        adapter.get_task_pricing("photo")
        assert adapter._stats["default_fallbacks"] >= 1


# ══════════════════════════════════════════════════════════════
# Adapter Tests — Market Demand
# ══════════════════════════════════════════════════════════════


class TestGetMarketDemand:
    def test_default_demand(self):
        adapter = PricingAdapter()
        demand = adapter.get_market_demand("photo")
        assert demand.source == "default"
        assert demand.demand_score == 0.5

    def test_cache_hit(self):
        adapter = PricingAdapter()
        cached = MarketDemandSnapshot(
            category="delivery", demand_score=0.8,
            fetched_at=time.time(), source="api",
        )
        adapter._demand_cache["delivery"] = cached

        result = adapter.get_market_demand("delivery")
        assert result.demand_score == 0.8

    def test_category_normalization(self):
        adapter = PricingAdapter()
        result = adapter.get_market_demand("Content Creation")
        assert result.category == "content_creation"


# ══════════════════════════════════════════════════════════════
# Supply Gaps Tests
# ══════════════════════════════════════════════════════════════


class TestSupplyGaps:
    def test_default_empty(self):
        adapter = PricingAdapter()
        gaps = adapter.get_supply_gaps()
        assert gaps == []


# ══════════════════════════════════════════════════════════════
# Scorer Factory Tests
# ══════════════════════════════════════════════════════════════


class TestMakePricingScorer:
    def test_well_priced_task(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        # Delivery median is $8, offering $10 → generous
        score = scorer(
            {"category": "delivery", "bounty_usd": 10.0},
            {"wallet": "0x001"},
        )
        assert score >= 0.8

    def test_underpriced_task(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        # Delivery range_low is $5, offering $1 → severely underpriced
        score = scorer(
            {"category": "delivery", "bounty_usd": 1.0},
            {"wallet": "0x001"},
        )
        assert score < 0.5

    def test_mid_range_task(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        # Delivery range_low=$5, recommended=$8, offering $6 → mid range
        score = scorer(
            {"category": "delivery", "bounty_usd": 6.0},
            {"wallet": "0x001"},
        )
        assert 0.5 <= score <= 0.8

    def test_no_bounty_neutral(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        score = scorer({"category": "photo"}, {"wallet": "0x001"})
        assert score == 0.5

    def test_zero_bounty_neutral(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        score = scorer({"category": "photo", "bounty_usd": 0}, {"wallet": "0x001"})
        assert score == 0.5

    def test_very_generous_bounty(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        # Delivery median=$8, offering $100 → very generous
        score = scorer(
            {"category": "delivery", "bounty_usd": 100.0},
            {"wallet": "0x001"},
        )
        assert score >= 0.9

    def test_bounty_amount_usdc_key(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        score = scorer(
            {"category": "delivery", "bounty_amount_usdc": 10.0},
            {"wallet": "0x001"},
        )
        assert score >= 0.8

    def test_score_clamped(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        score = scorer(
            {"category": "delivery", "bounty_usd": 10000.0},
            {"wallet": "0x001"},
        )
        assert score <= 1.0

    def test_exactly_recommended(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        # Exactly at recommended price
        score = scorer(
            {"category": "delivery", "bounty_usd": 8.0},
            {"wallet": "0x001"},
        )
        assert score >= 0.8

    def test_exactly_range_low(self):
        adapter = PricingAdapter()
        scorer = make_pricing_scorer(adapter)

        # Exactly at range_low
        score = scorer(
            {"category": "delivery", "bounty_usd": 5.0},
            {"wallet": "0x001"},
        )
        assert score == pytest.approx(0.5, abs=0.01)


# ══════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_all_default_categories(self):
        adapter = PricingAdapter()
        for category in DEFAULT_PRICING:
            pricing = adapter.get_task_pricing(category)
            assert pricing.recommended_usd == DEFAULT_PRICING[category]["median"]

    def test_hyphen_normalization(self):
        adapter = PricingAdapter()
        result = adapter.get_task_pricing("data-collection")
        assert result.category == "data_collection"

    def test_stats_accumulate(self):
        adapter = PricingAdapter()
        for i in range(5):
            adapter.get_task_pricing(f"cat_{i}")
        stats = adapter.get_stats()
        assert stats["default_fallbacks"] == 5

    def test_url_trailing_slash(self):
        adapter = PricingAdapter(autojob_url="https://test.com/")
        assert adapter._url == "https://test.com"
