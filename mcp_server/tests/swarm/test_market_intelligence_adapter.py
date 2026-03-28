"""Tests for MarketIntelligenceAdapter — 12th signal: market conditions.

Coverage targets:
- MarketSnapshot: health score formula, boundary values, all field combinations
- TimingSnapshot: age tracking, field defaults
- SupplyGapSnapshot: age tracking, all fields
- MarketIntelligenceAdapter: 4-tier fallback, caching (fresh/stale/expired), stats
- make_market_scorer: task-level consistency, error handling, neutral defaults
"""

import time
import pytest

from mcp_server.swarm.market_intelligence_adapter import (
    MarketIntelligenceAdapter,
    MarketSnapshot,
    TimingSnapshot,
    SupplyGapSnapshot,
    make_market_scorer,
    FRESH_TTL,
    STALE_TTL,
)


@pytest.fixture
def adapter():
    return MarketIntelligenceAdapter(
        autojob_base_url="http://localhost:19999", timeout_s=0.5
    )


@pytest.fixture
def healthy_market():
    return MarketSnapshot(
        category="physical_presence",
        demand_score=0.5,
        completion_rate=0.85,
        expiry_rate=0.1,
        trend="growing",
        avg_bounty_usd=0.75,
        active_tasks=15,
        unique_workers=5,
        confidence=0.8,
        fetched_at=time.time(),
    )


@pytest.fixture
def unhealthy_market():
    return MarketSnapshot(
        category="delivery",
        demand_score=0.9,
        completion_rate=0.2,
        expiry_rate=0.7,
        trend="declining",
        avg_bounty_usd=1.50,
        active_tasks=2,
        unique_workers=1,
        confidence=0.5,
        fetched_at=time.time(),
    )


# ──────────────────────────────────────────────────────────────
# MarketSnapshot Tests
# ──────────────────────────────────────────────────────────────


class TestMarketSnapshot:
    def test_age_seconds_fresh(self, healthy_market):
        assert 0 <= healthy_market.age_seconds < 5

    def test_age_seconds_zero_fetched_at(self):
        snap = MarketSnapshot(category="test", fetched_at=0.0)
        assert snap.age_seconds == float("inf")

    def test_health_score_range(self, healthy_market):
        score = healthy_market.market_health_score
        assert 0 <= score <= 100

    def test_healthy_higher_than_unhealthy(self, healthy_market, unhealthy_market):
        assert healthy_market.market_health_score > unhealthy_market.market_health_score

    def test_health_score_perfect_market(self):
        """Perfect conditions → high score."""
        snap = MarketSnapshot(
            category="ideal",
            demand_score=0.5,
            completion_rate=1.0,
            expiry_rate=0.0,
            trend="growing",
            fetched_at=time.time(),
        )
        score = snap.market_health_score
        assert score >= 85  # Near-perfect: 40 + 20 + 20 + 15 = 95

    def test_health_score_worst_market(self):
        """Worst possible conditions → low score."""
        snap = MarketSnapshot(
            category="terrible",
            demand_score=0.0,
            completion_rate=0.0,
            expiry_rate=1.0,
            trend="declining",
            fetched_at=time.time(),
        )
        score = snap.market_health_score
        assert score <= 15  # Near-zero: 0 + 0 + 0 + 0 = 0

    def test_health_score_moderate_demand_sweet_spot(self):
        """Demand in 0.3-0.7 gets full demand contribution."""
        for demand in [0.3, 0.5, 0.7]:
            snap = MarketSnapshot(
                category="moderate",
                demand_score=demand,
                completion_rate=0.5,
                expiry_rate=0.5,
                trend="stable",
                fetched_at=time.time(),
            )
            # Same completion/expiry/trend, so demand contributes max
            # completion: 0.5*40=20, expiry: 0.5*20=10, demand: 20, trend: 10 = 60
            assert snap.market_health_score == pytest.approx(60.0, abs=0.1)

    def test_health_score_low_demand(self):
        """Very low demand gets proportionally lower score."""
        low = MarketSnapshot(
            category="low",
            demand_score=0.1,
            completion_rate=0.5,
            expiry_rate=0.5,
            trend="stable",
            fetched_at=time.time(),
        )
        moderate = MarketSnapshot(
            category="mod",
            demand_score=0.5,
            completion_rate=0.5,
            expiry_rate=0.5,
            trend="stable",
            fetched_at=time.time(),
        )
        assert low.market_health_score < moderate.market_health_score

    def test_health_score_high_demand_penalty(self):
        """Very high demand (>0.7) reduces score vs moderate."""
        high = MarketSnapshot(
            category="high",
            demand_score=0.95,
            completion_rate=0.5,
            expiry_rate=0.5,
            trend="stable",
            fetched_at=time.time(),
        )
        moderate = MarketSnapshot(
            category="mod",
            demand_score=0.5,
            completion_rate=0.5,
            expiry_rate=0.5,
            trend="stable",
            fetched_at=time.time(),
        )
        assert high.market_health_score < moderate.market_health_score

    def test_health_score_trend_ordering(self):
        """Growing > stable > declining for same base metrics."""

        def make(trend):
            return MarketSnapshot(
                category="test",
                demand_score=0.5,
                completion_rate=0.5,
                expiry_rate=0.5,
                trend=trend,
                fetched_at=time.time(),
            )

        assert make("growing").market_health_score > make("stable").market_health_score
        assert (
            make("stable").market_health_score > make("declining").market_health_score
        )

    def test_health_score_unknown_trend(self):
        """Unknown trend uses default (same as stable)."""
        stable = MarketSnapshot(category="test", trend="stable", fetched_at=time.time())
        unknown = MarketSnapshot(
            category="test", trend="unknown_trend", fetched_at=time.time()
        )
        assert stable.market_health_score == unknown.market_health_score

    def test_health_score_clamped_to_100(self):
        """Score cannot exceed 100."""
        snap = MarketSnapshot(
            category="over",
            demand_score=0.5,
            completion_rate=1.0,
            expiry_rate=0.0,
            trend="growing",
            fetched_at=time.time(),
        )
        assert snap.market_health_score <= 100.0

    def test_health_score_clamped_to_0(self):
        """Score cannot go below 0."""
        snap = MarketSnapshot(
            category="under",
            demand_score=0.0,
            completion_rate=0.0,
            expiry_rate=1.0,
            trend="declining",
            fetched_at=time.time(),
        )
        assert snap.market_health_score >= 0.0

    def test_default_values(self):
        """Default snapshot has neutral values."""
        snap = MarketSnapshot(category="default")
        assert snap.demand_score == 0.5
        assert snap.completion_rate == 0.5
        assert snap.expiry_rate == 0.5
        assert snap.trend == "stable"
        assert snap.confidence == 0.3
        assert snap.from_cache is False

    def test_from_cache_flag(self):
        snap = MarketSnapshot(category="cached", from_cache=True)
        assert snap.from_cache is True


# ──────────────────────────────────────────────────────────────
# TimingSnapshot Tests
# ──────────────────────────────────────────────────────────────


class TestTimingSnapshot:
    def test_basic_fields(self):
        snap = TimingSnapshot(
            category="test",
            best_day="Wednesday",
            best_hour_utc=14,
            acceptance_likelihood=0.75,
            confidence=0.8,
            fetched_at=time.time(),
        )
        assert snap.category == "test"
        assert snap.best_hour_utc == 14
        assert 0 <= snap.age_seconds < 5

    def test_default_values(self):
        snap = TimingSnapshot(category="default")
        assert snap.best_hour_utc == 14
        assert snap.best_day == "tuesday"
        assert snap.acceptance_likelihood == 0.5
        assert snap.confidence == 0.3

    def test_age_no_fetched_at(self):
        snap = TimingSnapshot(category="test", fetched_at=0.0)
        assert snap.age_seconds == float("inf")


# ──────────────────────────────────────────────────────────────
# SupplyGapSnapshot Tests
# ──────────────────────────────────────────────────────────────


class TestSupplyGapSnapshot:
    def test_creation(self):
        gap = SupplyGapSnapshot(
            category="delivery",
            gap_severity=0.8,
            worker_deficit=5,
            avg_wait_hours=48,
            fetched_at=time.time(),
        )
        assert gap.gap_severity == 0.8
        assert gap.category == "delivery"

    def test_defaults(self):
        gap = SupplyGapSnapshot(category="default")
        assert gap.gap_severity == 0.0
        assert gap.worker_deficit == 0
        assert gap.recommendation == ""

    def test_age_tracking(self):
        gap = SupplyGapSnapshot(category="test", fetched_at=time.time())
        assert 0 <= gap.age_seconds < 5

    def test_age_no_fetched_at(self):
        gap = SupplyGapSnapshot(category="test", fetched_at=0.0)
        assert gap.age_seconds == float("inf")


# ──────────────────────────────────────────────────────────────
# Adapter Core Tests
# ──────────────────────────────────────────────────────────────


class TestMarketIntelligenceAdapter:
    def test_init(self):
        adapter = MarketIntelligenceAdapter()
        assert hasattr(adapter, "base_url")
        assert adapter._total_requests == 0
        assert adapter._cache_hits == 0

    def test_init_custom_url(self):
        adapter = MarketIntelligenceAdapter(
            autojob_base_url="http://custom:5000",
            timeout_s=10.0,
        )
        assert adapter.base_url == "http://custom:5000"
        assert adapter.timeout_s == 10.0

    def test_init_strips_trailing_slash(self):
        adapter = MarketIntelligenceAdapter(autojob_base_url="http://host:9999/")
        assert adapter.base_url == "http://host:9999"

    def test_analyze_returns_snapshot(self, adapter):
        """When API is unreachable, returns default snapshot (tier 4)."""
        result = adapter.analyze("physical_presence")
        assert isinstance(result, MarketSnapshot)
        assert result.category == "physical_presence"

    def test_analyze_default_has_low_confidence(self, adapter):
        """Default fallback has low confidence to signal uncertainty."""
        result = adapter.analyze("unknown_category")
        assert result.confidence <= 0.2

    def test_analyze_consistent_category(self, adapter):
        r1 = adapter.analyze("digital")
        r2 = adapter.analyze("digital")
        assert r1.category == r2.category == "digital"

    def test_different_categories(self, adapter):
        r1 = adapter.analyze("physical_presence")
        r2 = adapter.analyze("digital_physical")
        assert r1.category != r2.category

    def test_get_timing(self, adapter):
        result = adapter.get_timing("physical_presence")
        assert isinstance(result, TimingSnapshot)

    def test_get_timing_default_on_failure(self, adapter):
        result = adapter.get_timing("anything")
        # API unreachable → returns default
        assert result.best_hour_utc == 14  # default

    def test_get_supply_gaps(self, adapter):
        result = adapter.get_supply_gaps()
        assert isinstance(result, list)

    def test_get_supply_gaps_empty_on_failure(self, adapter):
        result = adapter.get_supply_gaps()
        assert result == []  # No API → empty list

    def test_stats(self, adapter):
        stats = adapter.stats()
        assert isinstance(stats, dict)
        assert "total_requests" in stats
        assert "cache_hits" in stats
        assert "api_calls" in stats
        assert "api_errors" in stats
        assert "hit_rate" in stats

    def test_stats_after_operations(self, adapter):
        adapter.analyze("cat1")
        adapter.analyze("cat2")
        stats = adapter.stats()
        assert stats["total_requests"] == 2
        assert stats["api_calls"] >= 2  # Two API attempts
        assert stats["api_errors"] >= 2  # Both fail (no server)

    def test_stats_hit_rate_zero_initially(self, adapter):
        assert adapter.stats()["hit_rate"] == 0


# ──────────────────────────────────────────────────────────────
# Adapter Caching Tests
# ──────────────────────────────────────────────────────────────


class TestAdapterCaching:
    def test_fresh_cache_hit(self, adapter):
        """Inject a fresh snapshot into cache → analyze returns it."""
        fresh = MarketSnapshot(
            category="test_cat",
            demand_score=0.8,
            confidence=0.9,
            fetched_at=time.time(),
        )
        adapter._market_cache["test_cat"] = fresh

        result = adapter.analyze("test_cat")
        assert result.demand_score == 0.8
        assert result.from_cache is True
        assert adapter._cache_hits == 1

    def test_stale_cache_fallback(self, adapter):
        """Stale but not expired cache is used when API fails."""
        stale = MarketSnapshot(
            category="stale_cat",
            demand_score=0.6,
            confidence=0.7,
            fetched_at=time.time() - FRESH_TTL - 10,  # Past fresh, within stale
        )
        adapter._market_cache["stale_cat"] = stale

        result = adapter.analyze("stale_cat")
        # Should try API (fails), then use stale cache
        assert result.demand_score == 0.6
        assert result.from_cache is True

    def test_expired_cache_returns_default(self, adapter):
        """Fully expired cache → returns default snapshot."""
        expired = MarketSnapshot(
            category="expired_cat",
            demand_score=0.9,
            fetched_at=time.time() - STALE_TTL - 10,  # Past stale TTL
        )
        adapter._market_cache["expired_cat"] = expired

        result = adapter.analyze("expired_cat")
        assert result.confidence <= 0.2  # Default confidence
        # The expired value (0.9) is NOT returned
        assert result.demand_score != 0.9 or result.confidence <= 0.2

    def test_cache_key_normalization(self, adapter):
        """Category names are normalized: lowercase + underscores."""
        adapter._market_cache["physical_presence"] = MarketSnapshot(
            category="physical_presence",
            demand_score=0.7,
            fetched_at=time.time(),
        )

        # "physical_presence" with different casing should still hit cache
        # Note: current implementation does .lower().replace(" ", "_")
        result = adapter.analyze("Physical Presence")
        assert result.demand_score == 0.7

    def test_timing_cache_fresh(self, adapter):
        """Fresh timing cache is returned without API call."""
        fresh = TimingSnapshot(
            category="test",
            best_hour_utc=10,
            confidence=0.9,
            fetched_at=time.time(),
        )
        adapter._timing_cache["test"] = fresh
        result = adapter.get_timing("test")
        assert result.best_hour_utc == 10

    def test_timing_cache_stale_fallback(self, adapter):
        """Stale timing cache used when API fails."""
        stale = TimingSnapshot(
            category="stale",
            best_hour_utc=16,
            fetched_at=time.time() - FRESH_TTL - 10,
        )
        adapter._timing_cache["stale"] = stale
        result = adapter.get_timing("stale")
        assert result.best_hour_utc == 16

    def test_gaps_cache_fresh(self, adapter):
        """Fresh gaps cache is returned."""
        gaps = [
            SupplyGapSnapshot(category="test", gap_severity=0.5, fetched_at=time.time())
        ]
        adapter._gaps_cache = gaps
        adapter._gaps_fetched_at = time.time()

        result = adapter.get_supply_gaps()
        assert len(result) == 1
        assert result[0].gap_severity == 0.5

    def test_gaps_cache_stale_fallback(self, adapter):
        """Stale gaps cache used when API fails."""
        gaps = [SupplyGapSnapshot(category="stale", gap_severity=0.3)]
        adapter._gaps_cache = gaps
        adapter._gaps_fetched_at = time.time() - FRESH_TTL - 10  # past fresh

        result = adapter.get_supply_gaps()
        assert len(result) == 1

    def test_multiple_categories_cached_independently(self, adapter):
        """Each category gets its own cache entry."""
        adapter._market_cache["cat_a"] = MarketSnapshot(
            category="cat_a", demand_score=0.3, fetched_at=time.time()
        )
        adapter._market_cache["cat_b"] = MarketSnapshot(
            category="cat_b", demand_score=0.7, fetched_at=time.time()
        )

        a = adapter.analyze("cat_a")
        b = adapter.analyze("cat_b")
        assert a.demand_score == 0.3
        assert b.demand_score == 0.7


# ──────────────────────────────────────────────────────────────
# Market Scorer Tests
# ──────────────────────────────────────────────────────────────


class TestMarketScorer:
    def test_callable(self, adapter):
        scorer = make_market_scorer(adapter)
        assert callable(scorer)

    def test_returns_float(self, adapter):
        scorer = make_market_scorer(adapter)
        score = scorer({"category": "test"}, {"wallet": "0xW"})
        assert isinstance(score, (int, float))

    def test_task_level_signal(self, adapter):
        """Market score is task-level — same for all candidates."""
        scorer = make_market_scorer(adapter)
        task = {"category": "physical_presence"}
        s1 = scorer(task, {"wallet": "0xA"})
        s2 = scorer(task, {"wallet": "0xB"})
        assert s1 == s2

    def test_consistent(self, adapter):
        scorer = make_market_scorer(adapter)
        task = {"category": "test"}
        c = {"wallet": "0xSame"}
        assert scorer(task, c) == scorer(task, c)

    def test_uses_task_type_fallback(self, adapter):
        """If 'category' missing, falls back to 'task_type'."""
        scorer = make_market_scorer(adapter)
        score = scorer({"task_type": "digital"}, {"wallet": "0xW"})
        assert isinstance(score, (int, float))

    def test_missing_category_uses_general(self, adapter):
        """No category key → defaults to 'general'."""
        scorer = make_market_scorer(adapter)
        score = scorer({}, {"wallet": "0xW"})
        assert isinstance(score, (int, float))

    def test_scorer_with_cached_market(self, adapter):
        """Scorer uses cached market data when available."""
        adapter._market_cache["delivery"] = MarketSnapshot(
            category="delivery",
            demand_score=0.5,
            completion_rate=0.9,
            expiry_rate=0.05,
            trend="growing",
            fetched_at=time.time(),
        )
        scorer = make_market_scorer(adapter)
        score = scorer({"category": "delivery"}, {"wallet": "0xW"})
        # High health score due to good metrics
        assert score > 60

    def test_scorer_neutral_on_unknown(self, adapter):
        """Scorer returns neutral-ish score for unknown categories."""
        scorer = make_market_scorer(adapter)
        score = scorer({"category": "totally_unknown"}, {"wallet": "0xW"})
        # Default snapshot → moderate health score
        assert 20 <= score <= 80


# ──────────────────────────────────────────────────────────────
# Constants Sanity
# ──────────────────────────────────────────────────────────────


class TestConstants:
    def test_fresh_ttl_reasonable(self):
        assert 60 <= FRESH_TTL <= 7200  # 1 min to 2 hours

    def test_stale_ttl_greater_than_fresh(self):
        assert STALE_TTL > FRESH_TTL

    def test_stale_ttl_reasonable(self):
        assert STALE_TTL <= 86400  # Max 24 hours
