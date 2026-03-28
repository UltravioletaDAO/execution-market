"""
Test Suite: PerformanceAdapter — Worker Performance as a Routing Signal
=========================================================================

Tests cover:
    1. PerformanceSnapshot data type (risk_penalty, growth_bonus, category_affinity, staleness)
    2. Adapter cache behavior (hit, miss, stale, invalidation)
    3. API fallback (success, error, default)
    4. Scorer factory (weighted scoring, category affinity, growth, risk)
    5. Bulk fetch
    6. Edge cases (empty IDs, no data, cache clearing)
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from mcp_server.swarm.performance_adapter import (
    PerformanceAdapter,
    PerformanceSnapshot,
    make_performance_scorer,
    make_performance_scorer_from_url,
)


# ══════════════════════════════════════════════════════════════
# PerformanceSnapshot Tests
# ══════════════════════════════════════════════════════════════


class TestPerformanceSnapshot:
    def test_defaults(self):
        snap = PerformanceSnapshot(worker_id="0x001")
        assert snap.overall_score == 0.5
        assert snap.reliability == 0.5
        assert snap.risk_level == "unknown"
        assert snap.growth_trend == "unknown"
        assert snap.source == "default"

    def test_risk_penalty_low(self):
        snap = PerformanceSnapshot(worker_id="w1", risk_level="low")
        assert snap.risk_penalty == 0.0

    def test_risk_penalty_medium(self):
        snap = PerformanceSnapshot(worker_id="w1", risk_level="medium")
        assert snap.risk_penalty == 0.05

    def test_risk_penalty_high(self):
        snap = PerformanceSnapshot(worker_id="w1", risk_level="high")
        assert snap.risk_penalty == 0.15

    def test_risk_penalty_unknown(self):
        snap = PerformanceSnapshot(worker_id="w1", risk_level="unknown")
        assert snap.risk_penalty == 0.0

    def test_growth_bonus_improving(self):
        snap = PerformanceSnapshot(worker_id="w1", growth_trend="improving")
        assert snap.growth_bonus == 0.10

    def test_growth_bonus_stable(self):
        snap = PerformanceSnapshot(worker_id="w1", growth_trend="stable")
        assert snap.growth_bonus == 0.0

    def test_growth_bonus_declining(self):
        snap = PerformanceSnapshot(worker_id="w1", growth_trend="declining")
        assert snap.growth_bonus == -0.05

    def test_category_affinity_primary(self):
        snap = PerformanceSnapshot(
            worker_id="w1",
            optimal_categories=["photo", "delivery", "survey"],
        )
        assert snap.category_affinity("photo") == 1.0

    def test_category_affinity_top3(self):
        snap = PerformanceSnapshot(
            worker_id="w1",
            optimal_categories=["photo", "delivery", "survey"],
        )
        assert snap.category_affinity("survey") == 0.8

    def test_category_affinity_other(self):
        snap = PerformanceSnapshot(
            worker_id="w1",
            optimal_categories=["photo", "delivery", "survey", "research"],
        )
        assert snap.category_affinity("research") == 0.6

    def test_category_affinity_unknown(self):
        snap = PerformanceSnapshot(
            worker_id="w1",
            optimal_categories=["photo"],
        )
        assert snap.category_affinity("video") == 0.3

    def test_category_affinity_no_categories(self):
        snap = PerformanceSnapshot(worker_id="w1")
        assert snap.category_affinity("photo") == 0.5

    def test_is_stale_no_timestamp(self):
        snap = PerformanceSnapshot(worker_id="w1")
        assert snap.is_stale is True

    def test_is_stale_recent(self):
        snap = PerformanceSnapshot(
            worker_id="w1",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        assert snap.is_stale is False

    def test_is_stale_old(self):
        two_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        snap = PerformanceSnapshot(worker_id="w1", fetched_at=two_hours_ago)
        assert snap.is_stale is True

    def test_is_stale_bad_timestamp(self):
        snap = PerformanceSnapshot(worker_id="w1", fetched_at="not-a-date")
        assert snap.is_stale is True


# ══════════════════════════════════════════════════════════════
# Adapter Tests
# ══════════════════════════════════════════════════════════════


class TestPerformanceAdapter:
    def test_default_returns_neutral(self):
        adapter = PerformanceAdapter()
        perf = adapter.get_performance("0xunknown")
        assert perf.overall_score == 0.5
        assert perf.source == "default"

    def test_cache_hit(self):
        adapter = PerformanceAdapter()
        snap = PerformanceSnapshot(
            worker_id="0x001",
            overall_score=0.85,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="api",
        )
        adapter._cache["0x001"] = snap

        result = adapter.get_performance("0x001")
        assert result.overall_score == 0.85
        assert adapter._stats["cache_hits"] == 1

    def test_stale_cache_triggers_api(self):
        adapter = PerformanceAdapter()
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        snap = PerformanceSnapshot(
            worker_id="0x001", overall_score=0.7, fetched_at=old, source="api"
        )
        adapter._cache["0x001"] = snap

        # API will fail → should return stale cache
        result = adapter.get_performance("0x001")
        assert result.overall_score == 0.7  # Stale cache returned

    def test_get_stats(self):
        adapter = PerformanceAdapter()
        adapter.get_performance("0x001")

        stats = adapter.get_stats()
        assert stats["defaults_used"] == 1
        assert stats["cache_size"] == 0

    def test_clear_cache(self):
        adapter = PerformanceAdapter()
        adapter._cache["0x001"] = PerformanceSnapshot(worker_id="0x001")
        adapter.clear_cache()
        assert len(adapter._cache) == 0

    def test_invalidate(self):
        adapter = PerformanceAdapter()
        adapter._cache["0x001"] = PerformanceSnapshot(worker_id="0x001")
        adapter._cache["0x002"] = PerformanceSnapshot(worker_id="0x002")
        adapter.invalidate("0x001")
        assert "0x001" not in adapter._cache
        assert "0x002" in adapter._cache

    def test_invalidate_nonexistent(self):
        adapter = PerformanceAdapter()
        adapter.invalidate("0xnone")  # Should not crash

    def test_bulk_fetch(self):
        adapter = PerformanceAdapter()
        results = adapter.bulk_fetch(["0x001", "0x002", "0x003"])
        assert len(results) == 3
        assert all(r.source == "default" for r in results.values())

    def test_api_url_construction(self):
        adapter = PerformanceAdapter(autojob_url="https://test.com/")
        assert adapter.autojob_url == "https://test.com"


# ══════════════════════════════════════════════════════════════
# Scorer Factory Tests
# ══════════════════════════════════════════════════════════════


class TestMakePerformanceScorer:
    def test_neutral_default(self):
        adapter = PerformanceAdapter()
        scorer = make_performance_scorer(adapter)

        score = scorer({"category": "photo"}, {"wallet": "0xunknown"})
        # Default: base=50, affinity=50, growth=0, risk=0
        # 0.50*50 + 0.20*50 + 0.15*0 - 0.15*0 = 25 + 10 = 35
        assert 30 <= score <= 40

    def test_high_performer(self):
        adapter = PerformanceAdapter()
        adapter._cache["0x001"] = PerformanceSnapshot(
            worker_id="0x001",
            overall_score=0.95,
            growth_trend="improving",
            risk_level="low",
            optimal_categories=["photo"],
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        scorer = make_performance_scorer(adapter)

        score = scorer({"category": "photo"}, {"wallet": "0x001"})
        # base=95, affinity=100, growth=10, risk=0
        # 0.50*95 + 0.20*100 + 0.15*10 - 0.15*0 = 47.5 + 20 + 1.5 = 69
        assert score > 60

    def test_high_risk_penalized(self):
        adapter = PerformanceAdapter()
        adapter._cache["0xrisky"] = PerformanceSnapshot(
            worker_id="0xrisky",
            overall_score=0.8,
            risk_level="high",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        adapter._cache["0xsafe"] = PerformanceSnapshot(
            worker_id="0xsafe",
            overall_score=0.8,
            risk_level="low",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        scorer = make_performance_scorer(adapter)

        risky_score = scorer({"category": "photo"}, {"wallet": "0xrisky"})
        safe_score = scorer({"category": "photo"}, {"wallet": "0xsafe"})
        assert safe_score > risky_score

    def test_declining_growth_penalty(self):
        adapter = PerformanceAdapter()
        adapter._cache["0xdecline"] = PerformanceSnapshot(
            worker_id="0xdecline",
            overall_score=0.7,
            growth_trend="declining",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        adapter._cache["0xgrow"] = PerformanceSnapshot(
            worker_id="0xgrow",
            overall_score=0.7,
            growth_trend="improving",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        scorer = make_performance_scorer(adapter)

        decline_score = scorer({}, {"wallet": "0xdecline"})
        grow_score = scorer({}, {"wallet": "0xgrow"})
        assert grow_score > decline_score

    def test_no_wallet_returns_neutral(self):
        adapter = PerformanceAdapter()
        scorer = make_performance_scorer(adapter)
        score = scorer({}, {})
        assert score == 50.0

    def test_worker_id_fallback(self):
        adapter = PerformanceAdapter()
        scorer = make_performance_scorer(adapter)
        score = scorer({}, {"worker_id": "0x001"})
        assert 0 <= score <= 100

    def test_score_clamped_0_100(self):
        adapter = PerformanceAdapter()
        scorer = make_performance_scorer(adapter)
        score = scorer({}, {"wallet": "0x001"})
        assert 0 <= score <= 100

    def test_category_boosts_score(self):
        adapter = PerformanceAdapter()
        adapter._cache["0x001"] = PerformanceSnapshot(
            worker_id="0x001",
            overall_score=0.7,
            optimal_categories=["photo"],
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        scorer = make_performance_scorer(adapter)

        matching = scorer({"category": "photo"}, {"wallet": "0x001"})
        non_matching = scorer({"category": "video"}, {"wallet": "0x001"})
        assert matching > non_matching


class TestConvenienceFactory:
    def test_make_from_url(self):
        scorer = make_performance_scorer_from_url("https://test.com")
        # Should return a callable
        assert callable(scorer)
