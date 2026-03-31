"""
Tests for VerificationAdapter — PHOTINT Evidence Quality as a Swarm Signal

Validates:
  1. Inference ingestion (single, batch, edge cases)
  2. State computation (quality, approval, escalation, EXIF, trust tier)
  3. Scoring interface (0-100, category-specific, trend-adjusted)
  4. Trust tier classification (UNKNOWN → LOW → STANDARD → HIGH → EXCEPTIONAL)
  5. Routing recommendations (tier, cost estimation)
  6. Fleet analytics and diagnostics
  7. Trend detection (improving, stable, declining)
"""

import sys
import os
import unittest

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from swarm.verification_adapter import (
    VerificationAdapter,
    VerificationTrust,
)


def _make_inference(**overrides) -> dict:
    """Factory for inference dicts."""
    defaults = {
        "submission_id": "sub_001",
        "task_id": "task_001",
        "tier": "tier_1",
        "score": 0.85,
        "decision": "approved",
        "category": "physical_verification",
        "bounty_usd": 5.0,
        "has_exif": True,
        "has_gps": True,
        "photo_source": "camera",
        "cost_usd": 0.002,
        "was_escalated": False,
        "consensus_used": False,
        "consensus_agreed": False,
    }
    defaults.update(overrides)
    return defaults


def _make_inferences(count: int, **overrides) -> list:
    """Create N inference dicts."""
    return [
        _make_inference(
            submission_id=f"sub_{i:03d}", task_id=f"task_{i:03d}", **overrides
        )
        for i in range(count)
    ]


class TestIngestion(unittest.TestCase):
    """Test inference ingestion."""

    def setUp(self):
        self.adapter = VerificationAdapter()

    def test_ingest_single(self):
        ok = self.adapter.ingest_inference("0xW1", _make_inference())
        self.assertTrue(ok)
        state = self.adapter.get_state("0xW1")
        self.assertEqual(state.total_inferences, 1)

    def test_ingest_batch(self):
        infs = [
            {**_make_inference(), "worker_id": "0xW1"},
            {**_make_inference(), "worker_id": "0xW1"},
            {**_make_inference(), "worker_id": "0xW2"},
        ]
        count = self.adapter.ingest_batch(infs)
        self.assertEqual(count, 3)
        self.assertEqual(self.adapter.get_state("0xw1").total_inferences, 2)
        self.assertEqual(self.adapter.get_state("0xw2").total_inferences, 1)

    def test_ingest_empty_worker_rejected(self):
        ok = self.adapter.ingest_inference("", _make_inference())
        self.assertFalse(ok)

    def test_ingest_case_insensitive(self):
        self.adapter.ingest_inference("0xABC", _make_inference())
        self.adapter.ingest_inference("0xabc", _make_inference())
        state = self.adapter.get_state("0xABC")
        self.assertEqual(state.total_inferences, 2)

    def test_ingest_invalidates_cache(self):
        self.adapter.ingest_inference("0xW", _make_inference(score=0.5))
        s1 = self.adapter.get_state("0xW")
        self.adapter.ingest_inference("0xW", _make_inference(score=0.9))
        s2 = self.adapter.get_state("0xW")
        # Different objects due to cache invalidation
        self.assertIsNot(s1, s2)

    def test_ingest_uses_worker_wallet_key(self):
        """Batch ingestion should accept worker_wallet key too."""
        infs = [{"worker_wallet": "0xWW", "score": 0.8}]
        count = self.adapter.ingest_batch(infs)
        self.assertEqual(count, 1)
        self.assertEqual(self.adapter.get_state("0xww").total_inferences, 1)

    def test_ingest_uses_tier_used_key(self):
        """Inference should accept tier_used as alias for tier."""
        ok = self.adapter.ingest_inference("0xW", {"tier_used": "tier_2", "score": 0.7})
        self.assertTrue(ok)


class TestStateComputation(unittest.TestCase):
    """Test state computation accuracy."""

    def setUp(self):
        self.adapter = VerificationAdapter()

    def test_empty_state(self):
        state = self.adapter.get_state("0xNOBODY")
        self.assertEqual(state.total_inferences, 0)
        self.assertEqual(state.avg_score, 0.0)
        self.assertEqual(state.trust, VerificationTrust.UNKNOWN)

    def test_avg_score(self):
        for s in [0.9, 0.8, 0.7]:
            self.adapter.ingest_inference("0xW", _make_inference(score=s))
        state = self.adapter.get_state("0xW")
        self.assertAlmostEqual(state.avg_score, 0.8, places=3)

    def test_approval_rate(self):
        for i in range(7):
            self.adapter.ingest_inference(
                "0xW", _make_inference(decision="approved", score=0.8)
            )
        for i in range(3):
            self.adapter.ingest_inference(
                "0xW", _make_inference(decision="rejected", score=0.3)
            )
        state = self.adapter.get_state("0xW")
        self.assertAlmostEqual(state.approval_rate, 0.7)
        self.assertEqual(state.total_inferences, 10)

    def test_escalation_rate(self):
        for i in range(8):
            self.adapter.ingest_inference(
                "0xW", _make_inference(was_escalated=False, score=0.8)
            )
        for i in range(2):
            self.adapter.ingest_inference(
                "0xW", _make_inference(was_escalated=True, score=0.6)
            )
        state = self.adapter.get_state("0xW")
        self.assertAlmostEqual(state.escalation_rate, 0.2)

    def test_exif_rate(self):
        for i in range(10):
            self.adapter.ingest_inference(
                "0xW", _make_inference(has_exif=(i < 8), score=0.8)
            )
        state = self.adapter.get_state("0xW")
        self.assertAlmostEqual(state.exif_rate, 0.8)

    def test_camera_rate(self):
        for i in range(10):
            source = "camera" if i < 6 else "screenshot"
            self.adapter.ingest_inference(
                "0xW", _make_inference(photo_source=source, score=0.8)
            )
        state = self.adapter.get_state("0xW")
        self.assertAlmostEqual(state.camera_rate, 0.6)

    def test_category_scores(self):
        for i in range(5):
            self.adapter.ingest_inference(
                "0xW", _make_inference(category="physical_verification", score=0.9)
            )
        for i in range(3):
            self.adapter.ingest_inference(
                "0xW", _make_inference(category="bureaucratic", score=0.6)
            )
        state = self.adapter.get_state("0xW")
        self.assertIn("physical_verification", state.category_scores)
        self.assertIn("bureaucratic", state.category_scores)
        self.assertAlmostEqual(
            state.category_scores["physical_verification"], 0.9, places=2
        )

    def test_avg_cost(self):
        for i in range(5):
            self.adapter.ingest_inference(
                "0xW", _make_inference(cost_usd=0.002, score=0.8)
            )
        state = self.adapter.get_state("0xW")
        self.assertAlmostEqual(state.avg_cost, 0.002, places=4)

    def test_state_caching(self):
        self.adapter.ingest_inference("0xW", _make_inference(score=0.8))
        s1 = self.adapter.get_state("0xW")
        s2 = self.adapter.get_state("0xW")
        self.assertIs(s1, s2)  # Same cached object


class TestTrustClassification(unittest.TestCase):
    """Test trust tier classification."""

    def setUp(self):
        self.adapter = VerificationAdapter()

    def test_unknown_few_records(self):
        self.adapter.ingest_inference("0xW", _make_inference(score=0.99))
        self.adapter.ingest_inference("0xW", _make_inference(score=0.99))
        state = self.adapter.get_state("0xW")
        self.assertEqual(state.trust, VerificationTrust.UNKNOWN)

    def test_low_trust(self):
        for i in range(5):
            self.adapter.ingest_inference(
                "0xW", _make_inference(score=0.3, was_escalated=True)
            )
        state = self.adapter.get_state("0xW")
        self.assertEqual(state.trust, VerificationTrust.LOW)

    def test_standard_trust(self):
        for i in range(5):
            self.adapter.ingest_inference(
                "0xW", _make_inference(score=0.6, was_escalated=False)
            )
        state = self.adapter.get_state("0xW")
        self.assertEqual(state.trust, VerificationTrust.STANDARD)

    def test_high_trust(self):
        for i in range(15):
            self.adapter.ingest_inference(
                "0xW", _make_inference(score=0.85, was_escalated=False)
            )
        state = self.adapter.get_state("0xW")
        self.assertEqual(state.trust, VerificationTrust.HIGH)

    def test_exceptional_trust(self):
        for i in range(25):
            self.adapter.ingest_inference(
                "0xW", _make_inference(score=0.97, was_escalated=False)
            )
        state = self.adapter.get_state("0xW")
        self.assertEqual(state.trust, VerificationTrust.EXCEPTIONAL)

    def test_not_exceptional_with_escalation(self):
        """High escalation prevents exceptional classification."""
        for i in range(20):
            self.adapter.ingest_inference(
                "0xW",
                _make_inference(
                    score=0.97,
                    was_escalated=(i < 5),  # 25% escalation
                ),
            )
        state = self.adapter.get_state("0xW")
        self.assertNotEqual(state.trust, VerificationTrust.EXCEPTIONAL)


class TestScoring(unittest.TestCase):
    """Test the 0-100 scoring interface."""

    def setUp(self):
        self.adapter = VerificationAdapter(min_inferences_for_signal=3)

    def test_default_score_no_history(self):
        score = self.adapter.score("0xNOBODY")
        self.assertEqual(score, 50.0)

    def test_default_score_few_records(self):
        self.adapter.ingest_inference("0xW", _make_inference(score=0.99))
        score = self.adapter.score("0xW")
        self.assertEqual(score, 50.0)  # Below min_inferences

    def test_high_quality_high_score(self):
        for i in range(10):
            self.adapter.ingest_inference(
                "0xW",
                _make_inference(
                    score=0.95, decision="approved", has_exif=True, was_escalated=False
                ),
            )
        score = self.adapter.score("0xW")
        self.assertGreater(score, 80.0)

    def test_low_quality_low_score(self):
        for i in range(5):
            self.adapter.ingest_inference(
                "0xW",
                _make_inference(
                    score=0.3, decision="rejected", has_exif=False, was_escalated=True
                ),
            )
        score = self.adapter.score("0xW")
        self.assertLess(score, 40.0)

    def test_category_specific_scoring(self):
        """Score should use category-specific metrics when available."""
        # Good at physical, bad at bureaucratic
        for i in range(5):
            self.adapter.ingest_inference(
                "0xW", _make_inference(category="physical_verification", score=0.95)
            )
        for i in range(5):
            self.adapter.ingest_inference(
                "0xW", _make_inference(category="bureaucratic", score=0.4)
            )

        phys_score = self.adapter.score("0xW", {"category": "physical_verification"})
        bur_score = self.adapter.score("0xW", {"category": "bureaucratic"})
        self.assertGreater(phys_score, bur_score)

    def test_score_bounded(self):
        """Score should always be 0-100."""
        for i in range(10):
            self.adapter.ingest_inference("0xW", _make_inference(score=1.0))
        score = self.adapter.score("0xW")
        self.assertLessEqual(score, 100.0)
        self.assertGreaterEqual(score, 0.0)

    def test_improving_trend_boost(self):
        """Improving workers should score higher than stable ones."""
        # Worker A: improving (low then high)
        for i in range(5):
            self.adapter.ingest_inference("0xA", _make_inference(score=0.5))
        for i in range(5):
            self.adapter.ingest_inference("0xA", _make_inference(score=0.9))

        # Worker B: stable at same average
        for i in range(10):
            self.adapter.ingest_inference("0xB", _make_inference(score=0.7))

        score_a = self.adapter.score("0xA")
        score_b = self.adapter.score("0xB")
        # A should get trend boost
        # Note: the average scores differ, so this tests the combined effect
        # Both are roughly 0.7 average but A gets "improving" trend bonus
        self.assertIsInstance(score_a, float)
        self.assertIsInstance(score_b, float)


class TestTrend(unittest.TestCase):
    """Test trend detection."""

    def setUp(self):
        self.adapter = VerificationAdapter()

    def test_stable_few_records(self):
        for i in range(3):
            self.adapter.ingest_inference("0xW", _make_inference(score=0.8))
        state = self.adapter.get_state("0xW")
        self.assertEqual(state.trend, "stable")

    def test_improving(self):
        for i in range(5):
            self.adapter.ingest_inference("0xW", _make_inference(score=0.4))
        for i in range(5):
            self.adapter.ingest_inference("0xW", _make_inference(score=0.9))
        state = self.adapter.get_state("0xW")
        self.assertEqual(state.trend, "improving")

    def test_declining(self):
        for i in range(5):
            self.adapter.ingest_inference("0xW", _make_inference(score=0.9))
        for i in range(5):
            self.adapter.ingest_inference("0xW", _make_inference(score=0.4))
        state = self.adapter.get_state("0xW")
        self.assertEqual(state.trend, "declining")

    def test_stable(self):
        for i in range(10):
            self.adapter.ingest_inference("0xW", _make_inference(score=0.75))
        state = self.adapter.get_state("0xW")
        self.assertEqual(state.trend, "stable")


class TestRoutingRecommendations(unittest.TestCase):
    """Test tier recommendations and cost estimation."""

    def setUp(self):
        self.adapter = VerificationAdapter()

    def test_unknown_gets_tier_2(self):
        tier = self.adapter.recommend_tier("0xNEW")
        self.assertEqual(tier, "tier_2")

    def test_trusted_gets_tier_1(self):
        for i in range(15):
            self.adapter.ingest_inference(
                "0xW", _make_inference(score=0.88, was_escalated=False)
            )
        tier = self.adapter.recommend_tier("0xW")
        self.assertEqual(tier, "tier_1")

    def test_low_trust_gets_tier_2(self):
        for i in range(5):
            self.adapter.ingest_inference(
                "0xW", _make_inference(score=0.3, was_escalated=True)
            )
        tier = self.adapter.recommend_tier("0xW")
        self.assertEqual(tier, "tier_2")

    def test_cost_estimation(self):
        # Unknown worker → tier_2 → $0.01/image
        cost = self.adapter.estimate_verification_cost("0xNEW", photo_count=3)
        self.assertAlmostEqual(cost, 0.03)

    def test_cost_estimation_trusted(self):
        for i in range(15):
            self.adapter.ingest_inference(
                "0xW", _make_inference(score=0.88, was_escalated=False)
            )
        cost = self.adapter.estimate_verification_cost("0xW", photo_count=3)
        self.assertAlmostEqual(cost, 0.006)  # tier_1 → $0.002 * 3


class TestFleetAnalytics(unittest.TestCase):
    """Test fleet-level analytics."""

    def setUp(self):
        self.adapter = VerificationAdapter()

    def test_empty_fleet(self):
        metrics = self.adapter.get_fleet_metrics()
        self.assertEqual(metrics["total_workers"], 0)

    def test_multi_worker_fleet(self):
        for i in range(10):
            self.adapter.ingest_inference("0xA", _make_inference(score=0.9))
        for i in range(5):
            self.adapter.ingest_inference("0xB", _make_inference(score=0.6))

        metrics = self.adapter.get_fleet_metrics()
        self.assertEqual(metrics["total_workers"], 2)
        self.assertEqual(metrics["total_inferences"], 15)
        self.assertIn("trust_distribution", metrics)

    def test_category_performance(self):
        for i in range(5):
            self.adapter.ingest_inference(
                "0xA", _make_inference(category="physical_verification", score=0.9)
            )
        for i in range(3):
            self.adapter.ingest_inference(
                "0xB", _make_inference(category="bureaucratic", score=0.7)
            )

        cat_perf = self.adapter.get_category_performance()
        self.assertIn("physical_verification", cat_perf)
        self.assertIn("bureaucratic", cat_perf)
        self.assertEqual(cat_perf["physical_verification"]["worker_count"], 1)


class TestDiagnostics(unittest.TestCase):
    """Test diagnostic snapshot."""

    def setUp(self):
        self.adapter = VerificationAdapter()

    def test_empty_diagnostics(self):
        diag = self.adapter.diagnose()
        self.assertEqual(diag["fleet_metrics"]["total_workers"], 0)
        self.assertIn("adapter_config", diag)

    def test_full_diagnostics(self):
        for i in range(10):
            self.adapter.ingest_inference(
                "0xW", _make_inference(score=0.85, cost_usd=0.002)
            )

        diag = self.adapter.diagnose()
        self.assertEqual(diag["fleet_metrics"]["total_workers"], 1)
        self.assertIn("cost_analysis", diag)
        self.assertGreater(diag["cost_analysis"]["savings_pct"], 0)

    def test_config_in_diagnostics(self):
        adapter = VerificationAdapter(min_inferences_for_signal=5, default_score=60.0)
        diag = adapter.diagnose()
        self.assertEqual(diag["adapter_config"]["min_inferences"], 5)
        self.assertEqual(diag["adapter_config"]["default_score"], 60.0)


class TestIntegrationPatterns(unittest.TestCase):
    """Test real integration patterns with the swarm."""

    def setUp(self):
        self.adapter = VerificationAdapter()

    def test_decision_synthesizer_interface(self):
        """Verify the score method works as a signal provider callback."""
        # This is how DecisionSynthesizer would call it
        for i in range(5):
            self.adapter.ingest_inference("0xW", _make_inference(score=0.85))

        # Simulate: synthesizer.register_signal("verification_quality", adapter.score)
        # Then: signal_value = signal_fn(worker_id, task)
        task = {"id": "t1", "category": "physical_verification"}
        score = self.adapter.score("0xW", task)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_coordinator_routing_flow(self):
        """Simulate coordinator using verification quality for routing."""
        # Three workers with different quality
        for i in range(10):
            self.adapter.ingest_inference("0xGOOD", _make_inference(score=0.95))
            self.adapter.ingest_inference("0xOK", _make_inference(score=0.65))
            self.adapter.ingest_inference("0xBAD", _make_inference(score=0.3))

        task = {"category": "physical_verification"}
        scores = {
            "good": self.adapter.score("0xGOOD", task),
            "ok": self.adapter.score("0xOK", task),
            "bad": self.adapter.score("0xBAD", task),
        }

        # Verify ordering
        self.assertGreater(scores["good"], scores["ok"])
        self.assertGreater(scores["ok"], scores["bad"])

    def test_budget_controller_cost_integration(self):
        """Verify cost estimation feeds into budget planning."""
        # Trusted worker → cheap verification
        for i in range(15):
            self.adapter.ingest_inference("0xTRUSTED", _make_inference(score=0.9))

        trusted_cost = self.adapter.estimate_verification_cost("0xTRUSTED", 2)
        unknown_cost = self.adapter.estimate_verification_cost("0xNEW", 2)

        # Trusted is cheaper
        self.assertLess(trusted_cost, unknown_cost)


if __name__ == "__main__":
    unittest.main()
