"""
Tests for SealBridge — Analytics-to-On-Chain Reputation Pipeline
================================================================

Tests the complete bridge from SwarmAnalytics metrics to describe-net
SealRecommendation objects. Covers all 6 A2H seal scorers, 4 H2A scorers,
confidence calculation, batch preparation, fleet evaluation, and edge cases.
"""

import time
import pytest

from mcp_server.swarm.seal_bridge import (
    SealBridge,
    SealRecommendation,
    SealProfile,
    SealQuadrant,
    SealIssuanceRecord,
    A2H_SEALS,
    H2A_SEALS,
    _compute_evidence_hash,
    _sigmoid,
    _log_scale,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def bridge():
    return SealBridge(evaluator_agent_id="test_evaluator")


@pytest.fixture
def excellent_worker():
    """Metrics for a high-performing worker."""
    return {
        "agent_id": "worker_star",
        "tasks_assigned": 60,
        "tasks_completed": 55,
        "tasks_failed": 3,
        "tasks_expired": 2,
        "total_revenue_usd": 275.00,
        "avg_quality": 4.7,
        "avg_duration_seconds": 5400,  # 1.5 hours
        "success_rate": 55 / 60,
        "categories": {
            "physical_verification": 20,
            "photo_verification": 15,
            "data_collection": 10,
            "technical_task": 5,
            "notarization": 5,
        },
        "last_active": time.time() - 3600,  # 1 hour ago
        "quality_scores": [4.5, 4.8, 5.0, 4.6, 4.9, 4.7, 4.8, 4.5, 4.9, 5.0],
        "durations": [5000, 5500, 5200, 5800, 4800, 5100, 5300, 5600, 5400, 5200],
    }


@pytest.fixture
def poor_worker():
    """Metrics for a struggling worker."""
    return {
        "agent_id": "worker_poor",
        "tasks_assigned": 15,
        "tasks_completed": 5,
        "tasks_failed": 6,
        "tasks_expired": 4,
        "total_revenue_usd": 12.50,
        "avg_quality": 2.1,
        "avg_duration_seconds": 172800,  # 48 hours
        "success_rate": 5 / 15,
        "categories": {"simple_action": 15},
        "last_active": time.time() - 86400 * 14,  # 14 days ago
        "quality_scores": [1.5, 2.0, 3.0, 2.5, 1.5],
        "durations": [100000, 200000, 172800, 150000, 240000],
    }


@pytest.fixture
def new_worker():
    """Metrics for a brand new worker (minimal data)."""
    return {
        "agent_id": "worker_new",
        "tasks_assigned": 2,
        "tasks_completed": 2,
        "tasks_failed": 0,
        "tasks_expired": 0,
        "total_revenue_usd": 5.00,
        "avg_quality": 4.0,
        "avg_duration_seconds": 7200,
        "success_rate": 1.0,
        "categories": {"simple_action": 2},
        "last_active": time.time() - 7200,
        "quality_scores": [4.0, 4.0],
        "durations": [7200, 7200],
    }


@pytest.fixture
def diverse_worker():
    """Metrics for a worker with broad category coverage."""
    return {
        "agent_id": "worker_diverse",
        "tasks_assigned": 30,
        "tasks_completed": 28,
        "tasks_failed": 1,
        "tasks_expired": 1,
        "total_revenue_usd": 140.00,
        "avg_quality": 4.2,
        "avg_duration_seconds": 14400,  # 4 hours
        "success_rate": 28 / 30,
        "categories": {
            "physical_verification": 5,
            "photo_verification": 5,
            "data_collection": 5,
            "technical_task": 4,
            "notarization": 3,
            "simple_action": 3,
            "delivery": 3,
        },
        "last_active": time.time() - 1800,
        "quality_scores": [4.0, 4.5, 4.0, 4.2, 4.3, 4.1, 4.5, 4.0, 4.2, 4.1],
        "durations": [
            14000,
            15000,
            13000,
            14500,
            14200,
            13800,
            15200,
            14600,
            13500,
            14800,
        ],
    }


# ──────────────────────────────────────────────────────────────
# Utility Function Tests
# ──────────────────────────────────────────────────────────────


class TestUtilityFunctions:
    """Test helper/utility functions."""

    def test_evidence_hash_deterministic(self):
        data = {"agent_id": "a1", "score": 85}
        h1 = _compute_evidence_hash(data)
        h2 = _compute_evidence_hash(data)
        assert h1 == h2

    def test_evidence_hash_different_data(self):
        h1 = _compute_evidence_hash({"key": "value1"})
        h2 = _compute_evidence_hash({"key": "value2"})
        assert h1 != h2

    def test_evidence_hash_order_independent(self):
        """JSON keys are sorted, so order doesn't matter."""
        h1 = _compute_evidence_hash({"b": 2, "a": 1})
        h2 = _compute_evidence_hash({"a": 1, "b": 2})
        assert h1 == h2

    def test_sigmoid_overflow(self):
        """Should not raise on extreme values."""
        result = _sigmoid(-1000)
        assert result == 0.0
        result = _sigmoid(1000)
        assert result == 1.0

    def test_log_scale_reference(self):
        """At reference value, should be 1.0."""
        result = _log_scale(100, 100)
        assert abs(result - 1.0) < 0.01

    def test_log_scale_over_reference(self):
        """Above reference, capped at 1.0."""
        assert _log_scale(200, 100) == 1.0


# ──────────────────────────────────────────────────────────────
# SealRecommendation Tests
# ──────────────────────────────────────────────────────────────


class TestSealRecommendation:
    """Test SealRecommendation data class."""

    def test_creation(self):
        rec = SealRecommendation(
            seal_type="SKILLFUL",
            quadrant=SealQuadrant.A2H,
            subject_address="0x1234",
            evaluator_agent_id="evaluator_1",
            score=85,
            confidence=0.9,
            evidence_summary="Good worker",
            evidence_hash="abc123",
            reasoning="High quality",
        )
        assert rec.score == 85
        assert rec.is_positive
        assert rec.is_high_confidence

    def test_low_confidence(self):
        rec = SealRecommendation(
            seal_type="RELIABLE",
            quadrant=SealQuadrant.A2H,
            subject_address="0x1234",
            evaluator_agent_id="e1",
            score=80,
            confidence=0.3,
            evidence_summary="",
            evidence_hash="",
            reasoning="",
        )
        assert not rec.is_high_confidence

    def test_negative_score(self):
        rec = SealRecommendation(
            seal_type="RELIABLE",
            quadrant=SealQuadrant.A2H,
            subject_address="0x1234",
            evaluator_agent_id="e1",
            score=40,
            confidence=0.9,
            evidence_summary="",
            evidence_hash="",
            reasoning="",
        )
        assert not rec.is_positive


# ──────────────────────────────────────────────────────────────
# SealProfile Tests
# ──────────────────────────────────────────────────────────────


class TestSealProfile:
    """Test SealProfile data class."""

    def test_profile_with_seals(self):
        recs = [
            SealRecommendation(
                "SKILLFUL", SealQuadrant.A2H, "0x1", "e1", 90, 0.95, "", "", ""
            ),
            SealRecommendation(
                "RELIABLE", SealQuadrant.A2H, "0x1", "e1", 85, 0.8, "", "", ""
            ),
            SealRecommendation(
                "CURIOUS", SealQuadrant.A2H, "0x1", "e1", 40, 0.3, "", "", ""
            ),
        ]
        p = SealProfile(address="0x1", agent_id="a1", recommendations=recs)
        assert len(p.issuable_seals) == 2  # Only high confidence
        d = p.to_dict()
        assert d["seal_count"] == 3
        assert d["high_confidence_seals"] == 2


# ──────────────────────────────────────────────────────────────
# Confidence Calculation
# ──────────────────────────────────────────────────────────────


class TestConfidence:
    """Test confidence calculation logic."""

    def test_at_high_confidence(self, bridge):
        c = bridge._compute_confidence(10)
        assert c >= 0.4  # 10 tasks is moderate confidence

    def test_monotonic_increase(self, bridge):
        prev = 0
        for n in range(3, 60):
            c = bridge._compute_confidence(n)
            assert c >= prev
            prev = c


# ──────────────────────────────────────────────────────────────
# A2H Seal Scoring Tests
# ──────────────────────────────────────────────────────────────


class TestSkillfulScoring:
    """Test SKILLFUL seal scoring."""

    def test_excellent_worker_high_skillful(self, bridge, excellent_worker):
        score, reasoning, evidence = bridge._score_skillful(excellent_worker)
        assert score > 75, f"Expected >75, got {score}"
        assert "quality" in reasoning.lower() or "Quality" in reasoning

    def test_poor_worker_low_skillful(self, bridge, poor_worker):
        score, _, _ = bridge._score_skillful(poor_worker)
        assert score < 50, f"Expected <50, got {score}"

    def test_perfect_quality(self, bridge):
        metrics = {"avg_quality": 5.0, "success_rate": 1.0, "tasks_completed": 100}
        score, _, _ = bridge._score_skillful(metrics)
        assert score > 90

    def test_volume_matters(self, bridge):
        base = {"avg_quality": 4.0, "success_rate": 0.8}
        score_low, _, _ = bridge._score_skillful({**base, "tasks_completed": 1})
        score_high, _, _ = bridge._score_skillful({**base, "tasks_completed": 100})
        assert score_high > score_low


class TestReliableScoring:
    """Test RELIABLE seal scoring."""

    def test_unreliable_worker(self, bridge, poor_worker):
        score, _, _ = bridge._score_reliable(poor_worker)
        assert score < 50

    def test_expiration_penalty(self, bridge):
        metrics_no_expire = {
            "success_rate": 0.8,
            "tasks_completed": 20,
            "tasks_failed": 5,
            "tasks_expired": 0,
        }
        metrics_expire = {
            "success_rate": 0.6,
            "tasks_completed": 20,
            "tasks_failed": 5,
            "tasks_expired": 8,
        }
        score_no, _, _ = bridge._score_reliable(metrics_no_expire)
        score_exp, _, _ = bridge._score_reliable(metrics_expire)
        assert score_no > score_exp


class TestThoroughScoring:
    """Test THOROUGH seal scoring."""

    def test_consistent_high_quality(self, bridge, excellent_worker):
        score, _, _ = bridge._score_thorough(excellent_worker)
        assert score > 70

    def test_inconsistent_quality(self, bridge):
        metrics = {
            "avg_quality": 3.0,
            "quality_scores": [1.0, 5.0, 1.0, 5.0, 1.0, 5.0],
            "tasks_completed": 6,
        }
        score, reasoning, _ = bridge._score_thorough(metrics)
        # High variance should hurt thoroughness
        assert score < 70

    def test_single_score(self, bridge):
        metrics = {"avg_quality": 4.5, "quality_scores": [4.5], "tasks_completed": 1}
        score, _, _ = bridge._score_thorough(metrics)
        assert 40 <= score <= 80  # Single data point = moderate confidence


class TestEngagedScoring:
    """Test ENGAGED seal scoring."""

    def test_recently_active(self, bridge):
        metrics = {
            "tasks_completed": 30,
            "categories": {"a": 10, "b": 10, "c": 10},
            "total_revenue_usd": 50,
            "last_active": time.time() - 60,  # Just now
        }
        score, _, _ = bridge._score_engaged(metrics)
        assert score > 50


class TestResponsiveScoring:
    """Test RESPONSIVE seal scoring (A2H)."""

    def test_no_duration_data(self, bridge):
        metrics = {"avg_duration_seconds": 0, "tasks_completed": 0, "durations": []}
        score, _, _ = bridge._score_responsive(metrics)
        assert score == 50  # Neutral

    def test_consistent_speed_bonus(self, bridge):
        # Consistent durations should get a bonus
        metrics_consistent = {
            "avg_duration_seconds": 7200,
            "tasks_completed": 10,
            "durations": [7200] * 10,
        }
        metrics_inconsistent = {
            "avg_duration_seconds": 7200,
            "tasks_completed": 10,
            "durations": [
                1000,
                14000,
                3000,
                11000,
                7200,
                2000,
                13000,
                5000,
                9000,
                6800,
            ],
        }
        score_c, _, _ = bridge._score_responsive(metrics_consistent)
        score_i, _, _ = bridge._score_responsive(metrics_inconsistent)
        assert score_c >= score_i  # Consistency bonus


class TestCuriousScoring:
    """Test CURIOUS seal scoring."""

    def test_diverse_categories(self, bridge, diverse_worker):
        score, _, _ = bridge._score_curious(diverse_worker)
        assert score > 60

    def test_even_distribution_bonus(self, bridge):
        # Perfectly even distribution
        even = {
            "categories": {"a": 10, "b": 10, "c": 10, "d": 10, "e": 10},
            "tasks_completed": 50,
        }
        # Skewed distribution
        skewed = {
            "categories": {"a": 46, "b": 1, "c": 1, "d": 1, "e": 1},
            "tasks_completed": 50,
        }
        score_even, _, _ = bridge._score_curious(even)
        score_skewed, _, _ = bridge._score_curious(skewed)
        assert score_even > score_skewed  # Evenness bonus


# ──────────────────────────────────────────────────────────────
# H2A Seal Scoring Tests
# ──────────────────────────────────────────────────────────────


class TestFairScoring:
    """Test FAIR seal scoring (H2A)."""

    def test_balanced_categories(self, bridge):
        metrics = {"categories": {"a": 10, "b": 10, "c": 10}, "tasks_assigned": 30}
        score, _, _ = bridge._score_fair(metrics)
        assert score > 70

    def test_single_category_unfair(self, bridge):
        metrics = {"categories": {"a": 30}, "tasks_assigned": 30}
        score, _, _ = bridge._score_fair(metrics)
        assert score == 50  # Single category = neutral


class TestEthicalScoring:
    """Test ETHICAL seal scoring (H2A)."""

    def test_no_expirations(self, bridge):
        metrics = {"tasks_completed": 30, "tasks_failed": 2, "tasks_expired": 0}
        score, _, _ = bridge._score_ethical(metrics)
        assert score > 75  # No expirations = ethical bonus


# ──────────────────────────────────────────────────────────────
# Full Evaluation Pipeline Tests
# ──────────────────────────────────────────────────────────────


class TestEvaluateWorker:
    """Test full worker evaluation pipeline."""

    def test_excellent_worker_profile(self, bridge, excellent_worker):
        profile = bridge.evaluate_worker(
            worker_address="0xExcellent",
            agent_id="worker_star",
            metrics=excellent_worker,
        )
        assert profile.data_points == 58  # completed + failed (55+3)
        assert (
            len(profile.recommendations) == 6
        )  # All 6 A2H seals (SKILLFUL, RELIABLE, THOROUGH, ENGAGED, HELPFUL, CURIOUS)
        assert profile.overall_score > 60

        # All seals should have the right quadrant
        for rec in profile.recommendations:
            assert rec.quadrant == SealQuadrant.A2H
            assert rec.seal_type in A2H_SEALS
            assert rec.subject_address == "0xExcellent"
            assert rec.evaluator_agent_id == "test_evaluator"

    def test_poor_worker_profile(self, bridge, poor_worker):
        profile = bridge.evaluate_worker(
            worker_address="0xPoor",
            agent_id="worker_poor",
            metrics=poor_worker,
        )
        assert profile.overall_score < 50
        assert len(profile.recommendations) >= 5  # Most A2H seals generated

    def test_new_worker_no_seals(self, bridge, new_worker):
        """Workers with < 3 tasks should get no recommendations."""
        profile = bridge.evaluate_worker(
            worker_address="0xNew",
            agent_id="worker_new",
            metrics=new_worker,
        )
        assert len(profile.recommendations) == 0
        assert profile.data_points == 2

    def test_evidence_hashes_unique(self, bridge, excellent_worker):
        profile = bridge.evaluate_worker("0x1", "w1", excellent_worker)
        hashes = [r.evidence_hash for r in profile.recommendations]
        assert len(set(hashes)) == len(hashes)  # All unique


class TestEvaluateAgentForWorker:
    """Test H2A evaluation (worker rates agent)."""

    def test_h2a_seal_types(self, bridge, excellent_worker):
        profile = bridge.evaluate_agent_for_worker(
            agent_address="0xAgent",
            agent_id="agent_2106",
            metrics=excellent_worker,
        )
        for rec in profile.recommendations:
            assert rec.quadrant == SealQuadrant.H2A
            assert rec.seal_type in H2A_SEALS

    def test_h2a_few_tasks_no_seals(self, bridge, new_worker):
        profile = bridge.evaluate_agent_for_worker("0x1", "a1", new_worker)
        assert len(profile.recommendations) == 0


# ──────────────────────────────────────────────────────────────
# Batch Preparation Tests
# ──────────────────────────────────────────────────────────────


class TestBatchPreparation:
    """Test batch seal preparation."""

    def test_prepare_batch_filters_low_confidence(self, bridge):
        recs = [
            SealRecommendation(
                "SKILLFUL", SealQuadrant.A2H, "0x1", "e1", 90, 0.95, "", "", ""
            ),
            SealRecommendation(
                "RELIABLE", SealQuadrant.A2H, "0x1", "e1", 85, 0.2, "", "", ""
            ),
            SealRecommendation(
                "THOROUGH", SealQuadrant.A2H, "0x1", "e1", 80, 0.8, "", "", ""
            ),
        ]
        batch = bridge.prepare_batch(recs)
        assert len(batch.seals) == 2  # Filters out 0.2 confidence

    def test_prepare_batch_custom_threshold(self, bridge):
        recs = [
            SealRecommendation(
                "SKILLFUL", SealQuadrant.A2H, "0x1", "e1", 90, 0.95, "", "", ""
            ),
            SealRecommendation(
                "RELIABLE", SealQuadrant.A2H, "0x1", "e1", 85, 0.8, "", "", ""
            ),
        ]
        batch = bridge.prepare_batch(recs, min_confidence=0.9)
        assert len(batch.seals) == 1

    def test_batch_sorted_by_score(self, bridge):
        recs = [
            SealRecommendation(
                "CURIOUS", SealQuadrant.A2H, "0x1", "e1", 60, 0.9, "", "", ""
            ),
            SealRecommendation(
                "SKILLFUL", SealQuadrant.A2H, "0x1", "e1", 95, 0.9, "", "", ""
            ),
            SealRecommendation(
                "RELIABLE", SealQuadrant.A2H, "0x1", "e1", 78, 0.9, "", "", ""
            ),
        ]
        batch = bridge.prepare_batch(recs)
        scores = [s.score for s in batch.seals]
        assert scores == sorted(scores, reverse=True)

    def test_batch_gas_estimate(self, bridge):
        recs = [
            SealRecommendation(
                "SKILLFUL", SealQuadrant.A2H, "0x1", "e1", 90, 0.9, "", "", ""
            ),
            SealRecommendation(
                "RELIABLE", SealQuadrant.A2H, "0x1", "e1", 85, 0.9, "", "", ""
            ),
        ]
        batch = bridge.prepare_batch(recs)
        assert batch.total_gas_estimate == 160000  # 2 * 80000

    def test_batch_max_50(self, bridge):
        recs = [
            SealRecommendation(
                f"SEAL_{i}", SealQuadrant.A2H, "0x1", "e1", 80, 0.9, "", "", ""
            )
            for i in range(60)
        ]
        batch = bridge.prepare_batch(recs)
        assert len(batch.seals) <= 50

    def test_empty_batch(self, bridge):
        batch = bridge.prepare_batch([])
        assert len(batch.seals) == 0
        assert batch.total_gas_estimate == 0

    def test_batch_to_dict(self, bridge):
        recs = [
            SealRecommendation(
                "SKILLFUL", SealQuadrant.A2H, "0x1", "e1", 90, 0.9, "", "", ""
            ),
        ]
        batch = bridge.prepare_batch(recs)
        d = batch.to_dict()
        assert d["seal_count"] == 1
        assert "seals" in d


# ──────────────────────────────────────────────────────────────
# Issuance History Tests
# ──────────────────────────────────────────────────────────────


class TestIssuanceHistory:
    """Test seal issuance recording."""

    def test_multiple_issuances(self, bridge):
        for i in range(5):
            bridge.record_issuance(
                SealIssuanceRecord(
                    seal_id=i,
                    tx_hash=f"0x{i}",
                    seal_type="RELIABLE",
                    subject_address="0x1",
                    score=80,
                    quadrant=SealQuadrant.A2H,
                )
            )
        assert bridge.issuance_count == 5


# ──────────────────────────────────────────────────────────────
# Fleet Evaluation Tests
# ──────────────────────────────────────────────────────────────


class TestFleetEvaluation:
    """Test fleet-wide evaluation."""

    def test_evaluate_fleet(
        self, bridge, excellent_worker, poor_worker, diverse_worker
    ):
        fleet_metrics = {
            "worker_star": excellent_worker,
            "worker_poor": poor_worker,
            "worker_diverse": diverse_worker,
        }
        address_map = {
            "worker_star": "0xStar",
            "worker_poor": "0xPoor",
            "worker_diverse": "0xDiverse",
        }
        profiles = bridge.evaluate_fleet(fleet_metrics, address_map)
        assert len(profiles) == 3
        # Should be sorted by overall_score descending
        assert profiles[0].overall_score >= profiles[1].overall_score
        assert profiles[1].overall_score >= profiles[2].overall_score

    def test_fleet_no_address_map(self, bridge, excellent_worker):
        profiles = bridge.evaluate_fleet({"w1": excellent_worker})
        assert len(profiles) == 1
        assert profiles[0].address == "0xw1"  # Fallback address

    def test_fleet_summary(self, bridge, excellent_worker, diverse_worker):
        fleet_metrics = {
            "w1": excellent_worker,
            "w2": diverse_worker,
        }
        profiles = bridge.evaluate_fleet(fleet_metrics)
        summary = bridge.fleet_summary(profiles)

        assert summary["agents_evaluated"] == 2
        assert summary["total_seals"] >= 10  # Multiple seals per worker
        assert "seal_breakdown" in summary
        assert "SKILLFUL" in summary["seal_breakdown"]
        assert len(summary["top_performers"]) <= 5

    def test_fleet_summary_empty(self, bridge):
        summary = bridge.fleet_summary([])
        assert summary["agents_evaluated"] == 0

    def test_fleet_skips_insufficient_data(self, bridge, new_worker):
        profiles = bridge.evaluate_fleet({"new": new_worker})
        assert len(profiles) == 0  # < 3 tasks, no recommendations


# ──────────────────────────────────────────────────────────────
# Edge Cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_everything(self, bridge):
        metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_expired": 0,
            "avg_quality": 0,
            "success_rate": 0,
            "avg_duration_seconds": 0,
            "categories": {},
            "last_active": 0,
            "quality_scores": [],
            "durations": [],
            "total_revenue_usd": 0,
        }
        profile = bridge.evaluate_worker("0x0", "zero", metrics)
        assert len(profile.recommendations) == 0  # 0 total tasks < 3 min

    def test_all_failed(self, bridge):
        metrics = {
            "tasks_completed": 0,
            "tasks_failed": 10,
            "tasks_expired": 5,
            "avg_quality": 0,
            "success_rate": 0,
            "avg_duration_seconds": 0,
            "categories": {"simple_action": 15},
            "last_active": time.time() - 3600,
            "quality_scores": [],
            "durations": [],
            "total_revenue_usd": 0,
            "tasks_assigned": 15,
        }
        profile = bridge.evaluate_worker("0xFail", "failure", metrics)
        assert profile.data_points >= 10  # completed + failed (0+10)
        # Most scores should be low
        low_scores = [r for r in profile.recommendations if r.score < 60]
        assert len(low_scores) >= 3, (
            "Expected most seal scores to be low for all-failed worker"
        )

    def test_exactly_3_tasks(self, bridge):
        """Minimum threshold: exactly 3 tasks should produce seals."""
        metrics = {
            "tasks_completed": 2,
            "tasks_failed": 1,
            "tasks_expired": 0,
            "avg_quality": 3.5,
            "success_rate": 2 / 3,
            "avg_duration_seconds": 7200,
            "categories": {"simple_action": 3},
            "last_active": time.time(),
            "quality_scores": [3.0, 4.0],
            "durations": [7200, 7200],
            "total_revenue_usd": 5,
        }
        profile = bridge.evaluate_worker("0x3", "three", metrics)
        assert len(profile.recommendations) > 0

    def test_missing_keys_handled(self, bridge):
        """Metrics with missing keys shouldn't crash."""
        metrics = {
            "tasks_completed": 5,
            "tasks_failed": 1,
            # Missing: tasks_expired, avg_quality, etc.
        }
        profile = bridge.evaluate_worker("0xPartial", "partial", metrics)
        # Should not raise, may produce default scores
        assert isinstance(profile, SealProfile)

    def test_negative_values_handled(self, bridge):
        metrics = {
            "tasks_completed": -1,
            "tasks_failed": 5,
            "tasks_expired": 0,
            "avg_quality": -2,
            "success_rate": -0.5,
            "avg_duration_seconds": -100,
            "categories": {},
            "last_active": 0,
            "quality_scores": [],
            "durations": [],
            "total_revenue_usd": -10,
        }
        # Should not crash
        profile = bridge.evaluate_worker("0xNeg", "neg", metrics)
        assert isinstance(profile, SealProfile)

    def test_seal_quadrant_serialization(self):
        """Quadrant enum should serialize correctly."""
        assert SealQuadrant.A2H.value == "A2H"
        assert SealQuadrant.H2A.value == "H2A"
        assert SealQuadrant.A2A.value == "A2A"
        assert SealQuadrant.H2H.value == "H2H"


# ──────────────────────────────────────────────────────────────
# Integration: Analytics → SealBridge Pipeline
# ──────────────────────────────────────────────────────────────


class TestAnalyticsPipeline:
    """
    Test the full pipeline from SwarmAnalytics-style metrics
    to SealBridge recommendations to batch preparation.
    """

    def test_full_pipeline(self, bridge, excellent_worker):
        # Step 1: Evaluate worker
        profile = bridge.evaluate_worker("0xStar", "star", excellent_worker)
        assert profile.recommendations

        # Step 2: Get issuable seals
        issuable = profile.issuable_seals
        assert len(issuable) > 0

        # Step 3: Prepare batch
        batch = bridge.prepare_batch(issuable)
        assert len(batch.seals) > 0
        assert batch.total_gas_estimate > 0

        # Step 4: Verify batch is valid for SealRegistry
        for seal in batch.seals:
            assert 0 <= seal.score <= 100
            assert seal.seal_type in A2H_SEALS
            assert seal.evidence_hash  # Non-empty
            assert seal.subject_address == "0xStar"

    def test_pipeline_with_fleet(
        self, bridge, excellent_worker, poor_worker, diverse_worker
    ):
        fleet = {
            "star": excellent_worker,
            "poor": poor_worker,
            "diverse": diverse_worker,
        }
        addresses = {"star": "0xStar", "poor": "0xPoor", "diverse": "0xDiverse"}

        profiles = bridge.evaluate_fleet(fleet, addresses)
        summary = bridge.fleet_summary(profiles)

        # All workers should have seals (all have > 3 tasks)
        assert summary["agents_evaluated"] == 3
        assert summary["total_seals"] >= 15  # Multiple seals per worker

        # Prepare combined batch
        all_issuable = []
        for p in profiles:
            all_issuable.extend(p.issuable_seals)

        batch = bridge.prepare_batch(all_issuable)
        assert len(batch.seals) > 0

        # Summary should show seal type distribution
        assert "SKILLFUL" in summary["seal_breakdown"]
        assert "RELIABLE" in summary["seal_breakdown"]

    def test_bidirectional_evaluation(self, bridge, excellent_worker):
        """Test both A2H and H2A evaluations on same entity."""
        # Agent evaluates worker (A2H)
        a2h_profile = bridge.evaluate_worker("0xWorker", "w1", excellent_worker)

        # Worker evaluates agent (H2A)
        h2a_profile = bridge.evaluate_agent_for_worker(
            "0xAgent", "a1", excellent_worker
        )

        # Different seal types
        a2h_types = {r.seal_type for r in a2h_profile.recommendations}
        h2a_types = {r.seal_type for r in h2a_profile.recommendations}
        assert a2h_types.issubset(A2H_SEALS)
        assert h2a_types.issubset(H2A_SEALS)
        assert a2h_types.isdisjoint(h2a_types)  # No overlap
