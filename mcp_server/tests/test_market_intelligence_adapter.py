"""
Tests for MarketIntelligenceAdapter — The 12th Signal
=====================================================

Tests cover:
1. MarketSnapshot scoring and health calculation
2. TimingSnapshot creation
3. SupplyGapSnapshot creation
4. 4-tier cache fallback (fresh → API → stale → default)
5. API response parsing
6. Error handling and graceful degradation
7. Scorer factory for DecisionSynthesizer integration
8. Edge cases (empty categories, unknown trends, zero data)
"""

import json
import time
import unittest
from unittest.mock import patch, MagicMock

from mcp_server.swarm.market_intelligence_adapter import (
    MarketIntelligenceAdapter,
    MarketSnapshot,
    TimingSnapshot,
    SupplyGapSnapshot,
    make_market_scorer,
    FRESH_TTL,
    STALE_TTL,
)


class TestMarketSnapshot(unittest.TestCase):
    """Test MarketSnapshot data type and scoring."""

    def test_default_values(self):
        s = MarketSnapshot(category="test")
        self.assertEqual(s.category, "test")
        self.assertEqual(s.demand_score, 0.5)
        self.assertEqual(s.completion_rate, 0.5)
        self.assertEqual(s.trend, "stable")
        self.assertFalse(s.from_cache)

    def test_age_seconds_no_fetch(self):
        s = MarketSnapshot(category="test")
        self.assertEqual(s.age_seconds, float("inf"))

    def test_age_seconds_with_fetch(self):
        s = MarketSnapshot(category="test", fetched_at=time.time() - 60)
        self.assertAlmostEqual(s.age_seconds, 60.0, delta=2.0)

    def test_market_health_ideal(self):
        """High completion, low expiry, moderate demand, growing = high health."""
        s = MarketSnapshot(
            category="test",
            completion_rate=0.9,
            expiry_rate=0.1,
            demand_score=0.5,
            trend="growing",
        )
        score = s.market_health_score
        # 0.9*40=36 + 0.9*20=18 + 20 (ideal range) + 15 (growing) = 89
        self.assertGreater(score, 80)

    def test_market_health_terrible(self):
        """Low completion, high expiry, low demand, declining = low health."""
        s = MarketSnapshot(
            category="test",
            completion_rate=0.1,
            expiry_rate=0.9,
            demand_score=0.1,
            trend="declining",
        )
        score = s.market_health_score
        self.assertLess(score, 25)

    def test_market_health_moderate(self):
        """Average everything = moderate health."""
        s = MarketSnapshot(
            category="test",
            completion_rate=0.5,
            expiry_rate=0.5,
            demand_score=0.5,
            trend="stable",
        )
        score = s.market_health_score
        self.assertGreater(score, 35)
        self.assertLess(score, 65)

    def test_market_health_clamped_0_100(self):
        """Score should never exceed 0-100 range."""
        # Max possible
        s_max = MarketSnapshot(
            category="test",
            completion_rate=1.0,
            expiry_rate=0.0,
            demand_score=0.5,
            trend="growing",
        )
        self.assertLessEqual(s_max.market_health_score, 100.0)

        # Min possible
        s_min = MarketSnapshot(
            category="test",
            completion_rate=0.0,
            expiry_rate=1.0,
            demand_score=0.0,
            trend="declining",
        )
        self.assertGreaterEqual(s_min.market_health_score, 0.0)

    def test_high_demand_penalty(self):
        """Very high demand (> 0.7) should get lower demand contribution."""
        s_moderate = MarketSnapshot(
            category="test",
            completion_rate=0.5,
            expiry_rate=0.5,
            demand_score=0.5,
            trend="stable",
        )
        s_high = MarketSnapshot(
            category="test",
            completion_rate=0.5,
            expiry_rate=0.5,
            demand_score=0.95,
            trend="stable",
        )
        # High demand should score lower than moderate
        self.assertGreater(s_moderate.market_health_score, s_high.market_health_score)

    def test_trend_impact(self):
        """Growing trend should score higher than declining."""
        base = dict(
            category="test",
            completion_rate=0.5,
            expiry_rate=0.5,
            demand_score=0.5,
        )
        s_growing = MarketSnapshot(**base, trend="growing")
        s_stable = MarketSnapshot(**base, trend="stable")
        s_declining = MarketSnapshot(**base, trend="declining")

        self.assertGreater(s_growing.market_health_score, s_stable.market_health_score)
        self.assertGreater(s_stable.market_health_score, s_declining.market_health_score)


class TestTimingSnapshot(unittest.TestCase):
    """Test TimingSnapshot data type."""

    def test_defaults(self):
        t = TimingSnapshot(category="delivery")
        self.assertEqual(t.best_hour_utc, 14)
        self.assertEqual(t.best_day, "tuesday")
        self.assertEqual(t.acceptance_likelihood, 0.5)

    def test_age(self):
        t = TimingSnapshot(category="test", fetched_at=time.time() - 120)
        self.assertAlmostEqual(t.age_seconds, 120.0, delta=2.0)


class TestSupplyGapSnapshot(unittest.TestCase):
    """Test SupplyGapSnapshot data type."""

    def test_defaults(self):
        g = SupplyGapSnapshot(category="notarization")
        self.assertEqual(g.gap_severity, 0.0)
        self.assertEqual(g.worker_deficit, 0)
        self.assertEqual(g.recommendation, "")


class TestMarketIntelligenceAdapter(unittest.TestCase):
    """Test the adapter's cache, API calls, and fallback behavior."""

    def setUp(self):
        self.adapter = MarketIntelligenceAdapter(
            autojob_base_url="http://localhost:8899",
            timeout_s=5.0,
        )

    def test_fresh_cache_hit(self):
        """Tier 1: Fresh cache should be returned without API call."""
        snap = MarketSnapshot(
            category="physical_verification",
            demand_score=0.8,
            completion_rate=0.7,
            fetched_at=time.time(),
        )
        self.adapter._market_cache["physical_verification"] = snap

        result = self.adapter.analyze("physical_verification")
        self.assertEqual(result.demand_score, 0.8)
        self.assertTrue(result.from_cache)
        self.assertEqual(self.adapter._api_calls, 0)

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_api_success(self, mock_urlopen):
        """Tier 2: Successful API call should return and cache."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "report": {
                "categories": {
                    "delivery": {
                        "demand_score": 0.6,
                        "completion_rate": 0.75,
                        "expiry_rate": 0.25,
                        "trend": "growing",
                        "avg_bounty_usd": 4.0,
                        "avg_time_to_acceptance_hours": 12.0,
                        "active_tasks": 15,
                        "unique_workers": 8,
                        "avg_applications_per_task": 2.5,
                        "total_tasks": 50,
                    }
                }
            }
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.adapter.analyze("delivery")
        self.assertEqual(result.demand_score, 0.6)
        self.assertEqual(result.completion_rate, 0.75)
        self.assertEqual(result.trend, "growing")
        self.assertFalse(result.from_cache)
        self.assertIn("delivery", self.adapter._market_cache)

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_api_failure_stale_cache(self, mock_urlopen):
        """Tier 3: API failure with stale cache should use stale data."""
        mock_urlopen.side_effect = TimeoutError("timeout")

        # Plant stale cache (2 hours old — fresh TTL is 30min, stale is 4h)
        stale = MarketSnapshot(
            category="survey",
            demand_score=0.4,
            completion_rate=0.6,
            fetched_at=time.time() - 7200,  # 2h ago
        )
        self.adapter._market_cache["survey"] = stale

        result = self.adapter.analyze("survey")
        self.assertEqual(result.demand_score, 0.4)
        self.assertTrue(result.from_cache)

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_api_failure_no_cache(self, mock_urlopen):
        """Tier 4: API failure with no cache should return defaults."""
        mock_urlopen.side_effect = TimeoutError("timeout")

        result = self.adapter.analyze("unknown_category")
        self.assertEqual(result.demand_score, 0.5)  # Default
        self.assertEqual(result.confidence, 0.1)  # Low confidence default

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_api_returns_failure(self, mock_urlopen):
        """API returning success=false should fall through."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": False}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.adapter.analyze("test")
        self.assertEqual(result.confidence, 0.1)  # Default

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_unknown_category_returns_empty_market(self, mock_urlopen):
        """Category not in market report should return zero-data snapshot."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "report": {"categories": {"delivery": {"demand_score": 0.5}}}
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.adapter.analyze("quantum_computing")
        self.assertEqual(result.demand_score, 0.0)
        self.assertEqual(result.active_tasks, 0)
        self.assertEqual(result.confidence, 0.2)

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_fuzzy_category_match(self, mock_urlopen):
        """Should fuzzy-match category names."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "report": {"categories": {
                "physical_verification": {"demand_score": 0.7, "total_tasks": 30}
            }}
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.adapter.analyze("verification")
        self.assertEqual(result.demand_score, 0.7)

    def test_stats(self):
        """Stats should track requests and hits."""
        stats = self.adapter.stats()
        self.assertEqual(stats["total_requests"], 0)
        self.assertEqual(stats["cache_hits"], 0)
        self.assertEqual(stats["api_calls"], 0)
        self.assertEqual(stats["hit_rate"], 0)


class TestMarketTimingFetch(unittest.TestCase):
    """Test timing endpoint integration."""

    def setUp(self):
        self.adapter = MarketIntelligenceAdapter()

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_timing_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "timing": {
                "best_hour_utc": 16,
                "best_day": "wednesday",
                "acceptance_likelihood": 0.75,
                "confidence": 0.8,
            }
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.adapter.get_timing("delivery")
        self.assertEqual(result.best_hour_utc, 16)
        self.assertEqual(result.best_day, "wednesday")
        self.assertEqual(result.acceptance_likelihood, 0.75)

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_timing_failure_returns_default(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timeout")
        result = self.adapter.get_timing("test")
        self.assertEqual(result.best_hour_utc, 14)  # Default
        self.assertEqual(result.best_day, "tuesday")

    def test_timing_cache_hit(self):
        snap = TimingSnapshot(
            category="delivery",
            best_hour_utc=10,
            fetched_at=time.time(),
        )
        self.adapter._timing_cache["delivery"] = snap
        result = self.adapter.get_timing("delivery")
        self.assertEqual(result.best_hour_utc, 10)


class TestSupplyGapsFetch(unittest.TestCase):
    """Test supply gaps endpoint integration."""

    def setUp(self):
        self.adapter = MarketIntelligenceAdapter()

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_gaps_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "gaps": [
                {
                    "category": "notarization",
                    "severity": 0.8,
                    "worker_deficit": 5,
                    "avg_wait_hours": 48.0,
                    "recommendation": "increase_bounty",
                },
                {
                    "category": "code_execution",
                    "severity": 0.6,
                    "worker_deficit": 3,
                    "avg_wait_hours": 36.0,
                    "recommendation": "notify_workers",
                },
            ]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        gaps = self.adapter.get_supply_gaps()
        self.assertEqual(len(gaps), 2)
        self.assertEqual(gaps[0].category, "notarization")
        self.assertEqual(gaps[0].gap_severity, 0.8)
        self.assertEqual(gaps[1].recommendation, "notify_workers")

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_gaps_failure_returns_empty(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timeout")
        gaps = self.adapter.get_supply_gaps()
        self.assertEqual(gaps, [])

    def test_gaps_cache(self):
        self.adapter._gaps_cache = [
            SupplyGapSnapshot(category="test", gap_severity=0.5, fetched_at=time.time())
        ]
        self.adapter._gaps_fetched_at = time.time()
        gaps = self.adapter.get_supply_gaps()
        self.assertEqual(len(gaps), 1)


class TestMarketScorer(unittest.TestCase):
    """Test the scorer factory for DecisionSynthesizer integration."""

    def test_scorer_returns_health_score(self):
        """Scorer should return market_health_score for task category."""
        adapter = MarketIntelligenceAdapter()

        # Pre-populate cache with known data
        adapter._market_cache["delivery"] = MarketSnapshot(
            category="delivery",
            completion_rate=0.8,
            expiry_rate=0.2,
            demand_score=0.5,
            trend="growing",
            fetched_at=time.time(),
        )

        scorer = make_market_scorer(adapter)
        score = scorer(
            task={"category": "delivery"},
            candidate={"wallet": "0xABC"},
        )
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_scorer_with_task_type_fallback(self):
        """Scorer should try task_type if category not present."""
        adapter = MarketIntelligenceAdapter()
        adapter._market_cache["survey"] = MarketSnapshot(
            category="survey",
            completion_rate=0.5,
            demand_score=0.5,
            fetched_at=time.time(),
        )

        scorer = make_market_scorer(adapter)
        score = scorer(
            task={"task_type": "survey"},
            candidate={"wallet": "0xDEF"},
        )
        self.assertIsInstance(score, float)

    def test_scorer_error_returns_neutral(self):
        """Scorer should return 50 on unexpected errors."""
        adapter = MarketIntelligenceAdapter()

        # Force an error by passing None
        scorer = make_market_scorer(adapter)
        with patch.object(adapter, 'analyze', side_effect=Exception("boom")):
            score = scorer(task={"category": "test"}, candidate={})
            self.assertEqual(score, 50.0)

    def test_same_score_for_all_candidates(self):
        """Market score should be identical for all candidates (task-level signal)."""
        adapter = MarketIntelligenceAdapter()
        adapter._market_cache["delivery"] = MarketSnapshot(
            category="delivery",
            completion_rate=0.7,
            demand_score=0.5,
            trend="stable",
            fetched_at=time.time(),
        )

        scorer = make_market_scorer(adapter)
        task = {"category": "delivery"}

        score_1 = scorer(task, {"wallet": "0x111"})
        score_2 = scorer(task, {"wallet": "0x222"})
        score_3 = scorer(task, {"wallet": "0x333"})

        self.assertEqual(score_1, score_2)
        self.assertEqual(score_2, score_3)

    def test_different_categories_different_scores(self):
        """Different task categories should produce different scores."""
        adapter = MarketIntelligenceAdapter()

        adapter._market_cache["delivery"] = MarketSnapshot(
            category="delivery",
            completion_rate=0.9,
            expiry_rate=0.1,
            demand_score=0.5,
            trend="growing",
            fetched_at=time.time(),
        )
        adapter._market_cache["notarization"] = MarketSnapshot(
            category="notarization",
            completion_rate=0.2,
            expiry_rate=0.8,
            demand_score=0.9,
            trend="declining",
            fetched_at=time.time(),
        )

        scorer = make_market_scorer(adapter)
        score_delivery = scorer({"category": "delivery"}, {"wallet": "0x1"})
        score_notary = scorer({"category": "notarization"}, {"wallet": "0x1"})

        self.assertGreater(score_delivery, score_notary)


class TestCacheTTLBehavior(unittest.TestCase):
    """Test specific TTL edge cases."""

    def setUp(self):
        self.adapter = MarketIntelligenceAdapter()

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_expired_fresh_triggers_api(self, mock_urlopen):
        """Cache just past FRESH_TTL should trigger API call."""
        mock_urlopen.side_effect = TimeoutError("no api")

        # Plant cache just past fresh TTL
        stale = MarketSnapshot(
            category="test",
            demand_score=0.9,
            fetched_at=time.time() - FRESH_TTL - 10,
        )
        self.adapter._market_cache["test"] = stale

        result = self.adapter.analyze("test")
        # Should have tried API (and failed), then used stale cache
        self.assertEqual(result.demand_score, 0.9)
        self.assertTrue(result.from_cache)
        self.assertEqual(self.adapter._api_calls, 1)

    @patch("mcp_server.swarm.market_intelligence_adapter.urlopen")
    def test_expired_stale_returns_default(self, mock_urlopen):
        """Cache past STALE_TTL should return defaults."""
        mock_urlopen.side_effect = TimeoutError("no api")

        # Plant cache way past stale TTL
        very_old = MarketSnapshot(
            category="test",
            demand_score=0.9,
            fetched_at=time.time() - STALE_TTL - 100,
        )
        self.adapter._market_cache["test"] = very_old

        result = self.adapter.analyze("test")
        # Should get defaults, not stale cache
        self.assertEqual(result.demand_score, 0.5)
        self.assertEqual(result.confidence, 0.1)


if __name__ == "__main__":
    unittest.main()
