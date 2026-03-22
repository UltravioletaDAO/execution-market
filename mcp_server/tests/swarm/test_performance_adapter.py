"""
Tests for PerformanceAdapter — AutoJob worker performance as routing signal.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from swarm.performance_adapter import (
    PerformanceAdapter,
    PerformanceSnapshot,
    make_performance_scorer,
)


# ---------------------------------------------------------------------------
# PerformanceSnapshot Tests
# ---------------------------------------------------------------------------

class TestPerformanceSnapshot:
    def test_default_values(self):
        snap = PerformanceSnapshot(worker_id="0x1")
        assert snap.overall_score == 0.5
        assert snap.risk_level == "unknown"
        assert snap.growth_trend == "unknown"
        assert snap.source == "default"

    def test_risk_penalty(self):
        assert PerformanceSnapshot(worker_id="a", risk_level="low").risk_penalty == 0.0
        assert PerformanceSnapshot(worker_id="a", risk_level="medium").risk_penalty == 0.05
        assert PerformanceSnapshot(worker_id="a", risk_level="high").risk_penalty == 0.15
        assert PerformanceSnapshot(worker_id="a", risk_level="unknown").risk_penalty == 0.0

    def test_growth_bonus(self):
        assert PerformanceSnapshot(worker_id="a", growth_trend="improving").growth_bonus == 0.10
        assert PerformanceSnapshot(worker_id="a", growth_trend="stable").growth_bonus == 0.0
        assert PerformanceSnapshot(worker_id="a", growth_trend="declining").growth_bonus == -0.05

    def test_category_affinity_optimal(self):
        snap = PerformanceSnapshot(
            worker_id="a",
            optimal_categories=["photo_verification", "data_collection", "delivery"],
        )
        assert snap.category_affinity("photo_verification") == 1.0
        assert snap.category_affinity("data_collection") == 0.8
        assert snap.category_affinity("delivery") == 0.8
        assert snap.category_affinity("unknown") == 0.3

    def test_category_affinity_empty(self):
        snap = PerformanceSnapshot(worker_id="a")
        assert snap.category_affinity("anything") == 0.5

    def test_is_stale_no_timestamp(self):
        snap = PerformanceSnapshot(worker_id="a")
        assert snap.is_stale is True

    def test_is_stale_fresh(self):
        snap = PerformanceSnapshot(
            worker_id="a",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        assert snap.is_stale is False

    def test_is_stale_old(self):
        old = datetime.now(timezone.utc) - timedelta(hours=2)
        snap = PerformanceSnapshot(
            worker_id="a",
            fetched_at=old.isoformat(),
        )
        assert snap.is_stale is True


# ---------------------------------------------------------------------------
# PerformanceAdapter Tests
# ---------------------------------------------------------------------------

class TestPerformanceAdapter:
    def test_default_returns_neutral(self):
        adapter = PerformanceAdapter()
        snap = adapter.get_performance("0xUnknown")
        assert snap.worker_id == "0xUnknown"
        assert snap.overall_score == 0.5
        assert snap.source == "default"

    def test_cache_hit(self):
        adapter = PerformanceAdapter()
        # Pre-populate cache
        adapter._cache["0x1"] = PerformanceSnapshot(
            worker_id="0x1",
            overall_score=0.9,
            source="api",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        snap = adapter.get_performance("0x1")
        assert snap.overall_score == 0.9
        assert snap.source == "api"
        assert adapter._stats["cache_hits"] == 1

    def test_cache_miss_returns_default(self):
        adapter = PerformanceAdapter()
        snap = adapter.get_performance("0xMiss")
        assert snap.source == "default"
        assert adapter._stats["defaults_used"] == 1

    def test_stale_cache_returned_on_api_error(self):
        adapter = PerformanceAdapter()
        old = datetime.now(timezone.utc) - timedelta(hours=2)
        adapter._cache["0x1"] = PerformanceSnapshot(
            worker_id="0x1",
            overall_score=0.8,
            fetched_at=old.isoformat(),
            source="api",
        )

        # Mock API to fail
        with patch.object(adapter, "_fetch_from_api", side_effect=Exception("timeout")):
            snap = adapter.get_performance("0x1")
            # Should return stale cache
            assert snap.overall_score == 0.8

    def test_api_success_caches(self):
        adapter = PerformanceAdapter()
        profile = PerformanceSnapshot(
            worker_id="0x1",
            overall_score=0.85,
            source="api",
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        with patch.object(adapter, "_fetch_from_api", return_value=profile):
            snap = adapter.get_performance("0x1")
            assert snap.overall_score == 0.85
            # Should be in cache now
            assert "0x1" in adapter._cache

    def test_stats_tracking(self):
        adapter = PerformanceAdapter()
        adapter.get_performance("0x1")
        adapter.get_performance("0x2")
        stats = adapter.get_stats()
        assert stats["defaults_used"] == 2
        assert stats["cache_size"] == 0

    def test_clear_cache(self):
        adapter = PerformanceAdapter()
        adapter._cache["0x1"] = PerformanceSnapshot(worker_id="0x1")
        assert len(adapter._cache) == 1
        adapter.clear_cache()
        assert len(adapter._cache) == 0

    def test_invalidate(self):
        adapter = PerformanceAdapter()
        adapter._cache["0x1"] = PerformanceSnapshot(worker_id="0x1")
        adapter._cache["0x2"] = PerformanceSnapshot(worker_id="0x2")
        adapter.invalidate("0x1")
        assert "0x1" not in adapter._cache
        assert "0x2" in adapter._cache

    def test_bulk_fetch(self):
        adapter = PerformanceAdapter()
        results = adapter.bulk_fetch(["0x1", "0x2", "0x3"])
        assert len(results) == 3
        assert all(isinstance(v, PerformanceSnapshot) for v in results.values())


# ---------------------------------------------------------------------------
# Scorer Tests
# ---------------------------------------------------------------------------

class TestPerformanceScorer:
    def test_scorer_neutral_worker(self):
        adapter = PerformanceAdapter()
        scorer = make_performance_scorer(adapter)
        # Unknown worker → neutral scores
        score = scorer({"category": "delivery"}, {"wallet": "0xUnknown"})
        assert 20 <= score <= 80  # Should be near neutral

    def test_scorer_excellent_worker(self):
        adapter = PerformanceAdapter()
        adapter._cache["0xGood"] = PerformanceSnapshot(
            worker_id="0xGood",
            overall_score=0.95,
            risk_level="low",
            growth_trend="improving",
            optimal_categories=["delivery"],
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        scorer = make_performance_scorer(adapter)
        score = scorer({"category": "delivery"}, {"wallet": "0xGood"})
        assert score > 60  # High score

    def test_scorer_risky_worker(self):
        adapter = PerformanceAdapter()
        adapter._cache["0xBad"] = PerformanceSnapshot(
            worker_id="0xBad",
            overall_score=0.3,
            risk_level="high",
            growth_trend="declining",
            optimal_categories=[],
            fetched_at=datetime.now(timezone.utc).isoformat(),
        )
        scorer = make_performance_scorer(adapter)
        score = scorer({"category": "delivery"}, {"wallet": "0xBad"})
        assert score < 30  # Low score

    def test_scorer_excellent_beats_risky(self):
        adapter = PerformanceAdapter()
        now = datetime.now(timezone.utc).isoformat()
        adapter._cache["0xGood"] = PerformanceSnapshot(
            worker_id="0xGood",
            overall_score=0.9,
            risk_level="low",
            growth_trend="improving",
            optimal_categories=["delivery"],
            fetched_at=now,
        )
        adapter._cache["0xBad"] = PerformanceSnapshot(
            worker_id="0xBad",
            overall_score=0.3,
            risk_level="high",
            growth_trend="declining",
            fetched_at=now,
        )
        scorer = make_performance_scorer(adapter)
        good_score = scorer({"category": "delivery"}, {"wallet": "0xGood"})
        bad_score = scorer({"category": "delivery"}, {"wallet": "0xBad"})
        assert good_score > bad_score

    def test_scorer_category_affinity_matters(self):
        adapter = PerformanceAdapter()
        now = datetime.now(timezone.utc).isoformat()
        adapter._cache["0xSpec"] = PerformanceSnapshot(
            worker_id="0xSpec",
            overall_score=0.7,
            risk_level="low",
            growth_trend="stable",
            optimal_categories=["delivery", "logistics"],
            fetched_at=now,
        )
        scorer = make_performance_scorer(adapter)

        # Matching category
        delivery_score = scorer({"category": "delivery"}, {"wallet": "0xSpec"})
        # Non-matching category
        tech_score = scorer({"category": "technical_task"}, {"wallet": "0xSpec"})

        assert delivery_score > tech_score  # Affinity matters

    def test_scorer_no_wallet(self):
        adapter = PerformanceAdapter()
        scorer = make_performance_scorer(adapter)
        score = scorer({"category": "x"}, {})
        assert score == 50.0  # neutral

    def test_scorer_bounded_0_100(self):
        adapter = PerformanceAdapter()
        now = datetime.now(timezone.utc).isoformat()

        # Extreme high
        adapter._cache["0xMax"] = PerformanceSnapshot(
            worker_id="0xMax",
            overall_score=1.0,
            risk_level="low",
            growth_trend="improving",
            optimal_categories=["all"],
            fetched_at=now,
        )
        scorer = make_performance_scorer(adapter)
        score = scorer({"category": "all"}, {"wallet": "0xMax"})
        assert 0 <= score <= 100

        # Extreme low
        adapter._cache["0xMin"] = PerformanceSnapshot(
            worker_id="0xMin",
            overall_score=0.0,
            risk_level="high",
            growth_trend="declining",
            fetched_at=now,
        )
        score = scorer({"category": "x"}, {"wallet": "0xMin"})
        assert 0 <= score <= 100


# ---------------------------------------------------------------------------
# API Response Parsing
# ---------------------------------------------------------------------------

class TestAPIResponseParsing:
    def test_parse_full_api_response(self):
        """Verify _fetch_from_api correctly parses API response format."""
        adapter = PerformanceAdapter()

        mock_response = json.dumps({
            "success": True,
            "worker_id": "0xTest",
            "profile": {
                "overall_score": 0.82,
                "reliability_score": 0.88,
                "speed_percentile": 0.75,
                "quality_score": 0.79,
                "consistency_score": 0.91,
                "risk": {"overall_risk": "low", "flags": [], "details": {}},
                "growth": {"trend": "improving", "slope": 0.15},
                "optimal_categories": ["physical_verification", "delivery"],
                "recommended_complexity": "complex",
            }
        }).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            snap = adapter._fetch_from_api("0xTest")

        assert snap is not None
        assert snap.overall_score == 0.82
        assert snap.reliability == 0.88
        assert snap.risk_level == "low"
        assert snap.growth_trend == "improving"
        assert "physical_verification" in snap.optimal_categories
        assert snap.recommended_complexity == "complex"
        assert snap.source == "api"

    def test_parse_unsuccessful_response(self):
        adapter = PerformanceAdapter()
        mock_response = json.dumps({"success": False, "error": "not found"}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            snap = adapter._fetch_from_api("0xNotFound")

        assert snap is None

    def test_parse_no_profile(self):
        adapter = PerformanceAdapter()
        mock_response = json.dumps({"success": True, "profile": None}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            snap = adapter._fetch_from_api("0xEmpty")

        assert snap is None
