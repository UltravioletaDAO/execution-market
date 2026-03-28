"""
Test Suite: MarketIntelligenceAdapter — Category-Level Market Signals
=======================================================================

Tests cover:
    1. MarketSnapshot (health score, age, demand balance)
    2. TimingSnapshot and SupplyGapSnapshot data types
    3. Adapter 4-tier fallback (fresh cache, API, stale cache, default)
    4. Scorer factory (market health as routing signal)
    5. Cache behavior (TTL, stale fallback)
    6. Statistics tracking
"""

import time

from mcp_server.swarm.market_intelligence_adapter import (
    MarketIntelligenceAdapter,
    MarketSnapshot,
    TimingSnapshot,
    SupplyGapSnapshot,
    make_market_scorer,
    FRESH_TTL,
)


# ══════════════════════════════════════════════════════════════
# MarketSnapshot Tests
# ══════════════════════════════════════════════════════════════


class TestMarketSnapshot:
    def test_defaults(self):
        snap = MarketSnapshot(category="photo")
        assert snap.demand_score == 0.5
        assert snap.completion_rate == 0.5
        assert snap.trend == "stable"
        assert snap.confidence == 0.3

    def test_age_seconds(self):
        snap = MarketSnapshot(category="photo", fetched_at=time.time())
        assert snap.age_seconds < 1.0

    def test_age_seconds_old(self):
        snap = MarketSnapshot(category="photo", fetched_at=time.time() - 3600)
        assert snap.age_seconds >= 3599

    def test_age_seconds_never_fetched(self):
        snap = MarketSnapshot(category="photo")
        assert snap.age_seconds == float("inf")

    def test_health_score_high(self):
        snap = MarketSnapshot(
            category="photo",
            completion_rate=0.9,
            expiry_rate=0.1,
            demand_score=0.5,
            trend="growing",
        )
        score = snap.market_health_score
        # 0.9*40 + 0.9*20 + 20 + 15 = 36 + 18 + 20 + 15 = 89
        assert score >= 80

    def test_health_score_low(self):
        snap = MarketSnapshot(
            category="photo",
            completion_rate=0.1,
            expiry_rate=0.9,
            demand_score=0.9,
            trend="declining",
        )
        score = snap.market_health_score
        assert score < 30

    def test_health_score_moderate(self):
        snap = MarketSnapshot(
            category="photo",
            completion_rate=0.5,
            expiry_rate=0.5,
            demand_score=0.5,
            trend="stable",
        )
        score = snap.market_health_score
        assert 40 <= score <= 70

    def test_health_score_ideal_demand(self):
        snap = MarketSnapshot(category="photo", demand_score=0.5)
        # 0.3-0.7 range gets 20 points for demand
        snap2 = MarketSnapshot(category="photo", demand_score=0.1)
        assert snap.market_health_score > snap2.market_health_score

    def test_health_score_growing_bonus(self):
        growing = MarketSnapshot(category="photo", trend="growing")
        declining = MarketSnapshot(category="photo", trend="declining")
        assert growing.market_health_score > declining.market_health_score

    def test_health_score_clamped(self):
        snap = MarketSnapshot(
            category="photo",
            completion_rate=1.0,
            expiry_rate=0.0,
            demand_score=0.5,
            trend="growing",
        )
        assert snap.market_health_score <= 100.0

    def test_health_score_floor(self):
        snap = MarketSnapshot(
            category="photo",
            completion_rate=0.0,
            expiry_rate=1.0,
            demand_score=0.0,
            trend="declining",
        )
        assert snap.market_health_score >= 0.0


# ══════════════════════════════════════════════════════════════
# TimingSnapshot Tests
# ══════════════════════════════════════════════════════════════


class TestTimingSnapshot:
    def test_defaults(self):
        ts = TimingSnapshot(category="photo")
        assert ts.best_hour_utc == 14
        assert ts.best_day == "tuesday"
        assert ts.acceptance_likelihood == 0.5

    def test_age(self):
        ts = TimingSnapshot(category="photo", fetched_at=time.time())
        assert ts.age_seconds < 1.0


# ══════════════════════════════════════════════════════════════
# SupplyGapSnapshot Tests
# ══════════════════════════════════════════════════════════════


class TestSupplyGapSnapshot:
    def test_defaults(self):
        sg = SupplyGapSnapshot(category="delivery")
        assert sg.gap_severity == 0.0
        assert sg.worker_deficit == 0

    def test_with_data(self):
        sg = SupplyGapSnapshot(
            category="delivery",
            gap_severity=0.8,
            worker_deficit=5,
            recommendation="increase_bounty",
        )
        assert sg.recommendation == "increase_bounty"


# ══════════════════════════════════════════════════════════════
# Adapter Tests
# ══════════════════════════════════════════════════════════════


class TestMarketIntelligenceAdapter:
    def test_default_fallback(self):
        adapter = MarketIntelligenceAdapter()
        result = adapter.analyze("photo")
        assert result.category == "photo"
        assert result.confidence == 0.1  # Default low confidence

    def test_cache_hit(self):
        adapter = MarketIntelligenceAdapter()
        cached = MarketSnapshot(
            category="photo",
            demand_score=0.8,
            confidence=0.7,
            fetched_at=time.time(),
        )
        adapter._market_cache["photo"] = cached

        result = adapter.analyze("photo")
        assert result.demand_score == 0.8
        assert result.from_cache is True
        assert adapter._cache_hits == 1

    def test_stale_cache_used_on_api_failure(self):
        adapter = MarketIntelligenceAdapter()
        stale = MarketSnapshot(
            category="photo",
            demand_score=0.7,
            fetched_at=time.time() - FRESH_TTL - 1,  # Past fresh TTL
        )
        adapter._market_cache["photo"] = stale

        result = adapter.analyze("photo")
        assert result.demand_score == 0.7  # Stale cache

    def test_category_normalization(self):
        adapter = MarketIntelligenceAdapter()
        adapter._market_cache["physical_verification"] = MarketSnapshot(
            category="physical_verification",
            demand_score=0.9,
            fetched_at=time.time(),
        )

        result = adapter.analyze("Physical Verification")
        assert result.demand_score == 0.9

    def test_stats(self):
        adapter = MarketIntelligenceAdapter()
        adapter.analyze("photo")
        adapter.analyze("delivery")

        stats = adapter.stats()
        assert stats["total_requests"] == 2
        assert stats["market_cache_size"] >= 0

    def test_timing_default(self):
        adapter = MarketIntelligenceAdapter()
        result = adapter.get_timing("photo")
        assert result.best_hour_utc == 14
        assert result.category == "photo"

    def test_timing_cache(self):
        adapter = MarketIntelligenceAdapter()
        cached = TimingSnapshot(
            category="photo",
            best_hour_utc=10,
            best_day="friday",
            fetched_at=time.time(),
        )
        adapter._timing_cache["photo"] = cached

        result = adapter.get_timing("photo")
        assert result.best_hour_utc == 10

    def test_supply_gaps_default_empty(self):
        adapter = MarketIntelligenceAdapter()
        gaps = adapter.get_supply_gaps()
        assert gaps == []

    def test_supply_gaps_cached(self):
        adapter = MarketIntelligenceAdapter()
        adapter._gaps_cache = [
            SupplyGapSnapshot(category="delivery", gap_severity=0.8),
        ]
        adapter._gaps_fetched_at = time.time()

        gaps = adapter.get_supply_gaps()
        assert len(gaps) == 1
        assert gaps[0].category == "delivery"

    def test_url_cleanup(self):
        adapter = MarketIntelligenceAdapter(autojob_base_url="http://test.com/")
        assert adapter.base_url == "http://test.com"

    def test_hit_rate(self):
        adapter = MarketIntelligenceAdapter()
        # 2 requests, 0 hits
        adapter.analyze("a")
        adapter.analyze("b")
        stats = adapter.stats()
        assert stats["hit_rate"] == 0.0

        # Now cache hit
        adapter._market_cache["a"] = MarketSnapshot(
            category="a", fetched_at=time.time()
        )
        adapter.analyze("a")
        stats = adapter.stats()
        assert stats["hit_rate"] > 0


# ══════════════════════════════════════════════════════════════
# Scorer Factory Tests
# ══════════════════════════════════════════════════════════════


class TestMakeMarketScorer:
    def test_neutral_default(self):
        adapter = MarketIntelligenceAdapter()
        scorer = make_market_scorer(adapter)

        score = scorer({"category": "photo"}, {"wallet": "0x001"})
        assert 0 <= score <= 100

    def test_healthy_market(self):
        adapter = MarketIntelligenceAdapter()
        adapter._market_cache["photo"] = MarketSnapshot(
            category="photo",
            completion_rate=0.9,
            expiry_rate=0.1,
            demand_score=0.5,
            trend="growing",
            fetched_at=time.time(),
        )
        scorer = make_market_scorer(adapter)

        score = scorer({"category": "photo"}, {"wallet": "0x001"})
        assert score >= 80

    def test_unhealthy_market(self):
        adapter = MarketIntelligenceAdapter()
        adapter._market_cache["photo"] = MarketSnapshot(
            category="photo",
            completion_rate=0.1,
            expiry_rate=0.9,
            demand_score=0.95,
            trend="declining",
            fetched_at=time.time(),
        )
        scorer = make_market_scorer(adapter)

        score = scorer({"category": "photo"}, {"wallet": "0x001"})
        assert score < 30

    def test_task_type_fallback(self):
        adapter = MarketIntelligenceAdapter()
        scorer = make_market_scorer(adapter)

        # Uses task_type if category missing
        score = scorer({"task_type": "delivery"}, {"wallet": "0x001"})
        assert 0 <= score <= 100

    def test_same_score_for_all_candidates(self):
        """Market intelligence is task-level, not worker-level."""
        adapter = MarketIntelligenceAdapter()
        adapter._market_cache["photo"] = MarketSnapshot(
            category="photo",
            completion_rate=0.7,
            fetched_at=time.time(),
        )
        scorer = make_market_scorer(adapter)

        task = {"category": "photo"}
        score1 = scorer(task, {"wallet": "0x001"})
        score2 = scorer(task, {"wallet": "0x002"})
        assert score1 == score2
