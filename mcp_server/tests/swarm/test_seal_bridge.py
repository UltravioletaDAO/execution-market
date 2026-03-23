"""
Comprehensive test suite for SealBridge — the analytics-to-on-chain pipeline.

Tests cover:
- Data types: SealRecommendation, SealProfile, BatchSealRequest, SealIssuanceRecord
- Helper functions: _compute_evidence_hash, _sigmoid, _log_scale
- SealBridge initialization and configuration
- Confidence computation (task volume → confidence)
- A2H seal scorers: SKILLFUL, RELIABLE, THOROUGH, ENGAGED, HELPFUL, RESPONSIVE, CURIOUS
- H2A seal scorers: FAIR, ACCURATE, RESPONSIVE_H2A, ETHICAL
- evaluate_worker: full evaluation pipeline
- evaluate_agent_for_worker: H2A evaluation
- prepare_batch: filtering and gas estimation
- Issuance history tracking
- Fleet evaluation and summary
- Edge cases: zero tasks, extreme values, empty metrics
"""

import math
import time

import pytest

from mcp_server.swarm.seal_bridge import (
    A2H_SEALS,
    H2A_SEALS,
    BatchSealRequest,
    SealBridge,
    SealIssuanceRecord,
    SealProfile,
    SealQuadrant,
    SealRecommendation,
    SEAL_TYPES,
    _compute_evidence_hash,
    _log_scale,
    _sigmoid,
)


# ─── Helper Function Tests ──────────────────────────────────────────────


class TestHelperFunctions:
    def test_compute_evidence_hash_deterministic(self):
        data = {"agent_id": "w1", "score": 85}
        h1 = _compute_evidence_hash(data)
        h2 = _compute_evidence_hash(data)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_compute_evidence_hash_order_independent(self):
        d1 = {"b": 2, "a": 1}
        d2 = {"a": 1, "b": 2}
        assert _compute_evidence_hash(d1) == _compute_evidence_hash(d2)

    def test_compute_evidence_hash_different_data(self):
        h1 = _compute_evidence_hash({"x": 1})
        h2 = _compute_evidence_hash({"x": 2})
        assert h1 != h2

    def test_sigmoid_midpoint(self):
        result = _sigmoid(0.5, midpoint=0.5)
        assert abs(result - 0.5) < 1e-9

    def test_sigmoid_high(self):
        result = _sigmoid(1.0, midpoint=0.5, steepness=10)
        assert result > 0.99

    def test_sigmoid_low(self):
        result = _sigmoid(0.0, midpoint=0.5, steepness=10)
        assert result < 0.01

    def test_sigmoid_overflow_protection(self):
        # Very negative → 0
        assert _sigmoid(-1000, midpoint=0.5) == 0.0
        # Very positive → 1
        assert _sigmoid(1000, midpoint=0.5) == 1.0

    def test_log_scale_zero(self):
        assert _log_scale(0, 100) == 0.0

    def test_log_scale_negative(self):
        assert _log_scale(-5, 100) == 0.0

    def test_log_scale_reference_zero(self):
        assert _log_scale(10, 0) == 0.0

    def test_log_scale_at_reference(self):
        result = _log_scale(100, 100)
        assert abs(result - 1.0) < 1e-9

    def test_log_scale_above_reference_capped(self):
        result = _log_scale(1000, 100)
        assert result == 1.0

    def test_log_scale_partial(self):
        result = _log_scale(10, 100)
        assert 0 < result < 1


# ─── Data Type Tests ─────────────────────────────────────────────────────


class TestSealRecommendation:
    def test_to_dict(self):
        rec = SealRecommendation(
            seal_type="SKILLFUL",
            quadrant=SealQuadrant.A2H,
            subject_address="0x1234",
            evaluator_agent_id="agent_1",
            score=85,
            confidence=0.9,
            evidence_summary="Good work",
            evidence_hash="abc123",
            reasoning="High quality scores",
        )
        d = rec.to_dict()
        assert d["quadrant"] == "A2H"
        assert d["score"] == 85
        assert d["confidence"] == 0.9

    def test_is_high_confidence(self):
        rec = SealRecommendation(
            seal_type="SKILLFUL", quadrant=SealQuadrant.A2H,
            subject_address="0x1", evaluator_agent_id="a",
            score=80, confidence=0.8,
            evidence_summary="", evidence_hash="", reasoning=""
        )
        assert rec.is_high_confidence is True

    def test_is_not_high_confidence(self):
        rec = SealRecommendation(
            seal_type="SKILLFUL", quadrant=SealQuadrant.A2H,
            subject_address="0x1", evaluator_agent_id="a",
            score=80, confidence=0.6,
            evidence_summary="", evidence_hash="", reasoning=""
        )
        assert rec.is_high_confidence is False

    def test_is_positive(self):
        rec = SealRecommendation(
            seal_type="SKILLFUL", quadrant=SealQuadrant.A2H,
            subject_address="0x1", evaluator_agent_id="a",
            score=60, confidence=0.5,
            evidence_summary="", evidence_hash="", reasoning=""
        )
        assert rec.is_positive is True

    def test_is_not_positive(self):
        rec = SealRecommendation(
            seal_type="SKILLFUL", quadrant=SealQuadrant.A2H,
            subject_address="0x1", evaluator_agent_id="a",
            score=59, confidence=0.5,
            evidence_summary="", evidence_hash="", reasoning=""
        )
        assert rec.is_positive is False


class TestSealProfile:
    def test_empty_profile(self):
        profile = SealProfile(address="0x1", agent_id="w1")
        assert len(profile.recommendations) == 0
        assert profile.issuable_seals == []

    def test_issuable_seals_filters_by_confidence(self):
        profile = SealProfile(address="0x1", agent_id="w1")
        profile.recommendations = [
            SealRecommendation("SKILLFUL", SealQuadrant.A2H, "0x1", "a", 80, 0.8, "", "", ""),
            SealRecommendation("RELIABLE", SealQuadrant.A2H, "0x1", "a", 70, 0.5, "", "", ""),
        ]
        issuable = profile.issuable_seals
        assert len(issuable) == 1
        assert issuable[0].seal_type == "SKILLFUL"

    def test_to_dict(self):
        profile = SealProfile(address="0x1", agent_id="w1", overall_score=75.5)
        d = profile.to_dict()
        assert d["address"] == "0x1"
        assert d["overall_score"] == 75.5
        assert d["seal_count"] == 0
        assert d["high_confidence_seals"] == 0


class TestBatchSealRequest:
    def test_to_dict(self):
        batch = BatchSealRequest(seals=[], total_gas_estimate=160000)
        d = batch.to_dict()
        assert d["seal_count"] == 0
        assert d["total_gas_estimate"] == 160000


class TestSealIssuanceRecord:
    def test_to_dict(self):
        record = SealIssuanceRecord(
            seal_id=42, tx_hash="0xabc",
            seal_type="SKILLFUL", subject_address="0x1",
            score=85, quadrant=SealQuadrant.A2H,
            block_number=12345
        )
        d = record.to_dict()
        assert d["seal_id"] == 42
        assert d["quadrant"] == "A2H"


# ─── SealBridge Configuration Tests ─────────────────────────────────────


class TestSealBridgeConfig:
    def test_default_config(self):
        bridge = SealBridge()
        assert bridge._evaluator_agent_id == "swarm_coordinator"
        assert bridge._min_confidence == 0.5
        assert bridge._gas_per_seal == 80000

    def test_custom_config(self):
        bridge = SealBridge(
            evaluator_agent_id="agent_2106",
            min_confidence=0.7,
            gas_per_seal=100000
        )
        assert bridge._evaluator_agent_id == "agent_2106"
        assert bridge._min_confidence == 0.7


# ─── Confidence Computation Tests ────────────────────────────────────────


class TestConfidenceComputation:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_below_minimum(self):
        assert self.bridge._compute_confidence(2) == 0.0

    def test_at_minimum(self):
        result = self.bridge._compute_confidence(3)
        assert abs(result - 0.3) < 1e-9

    def test_at_high_confidence_threshold(self):
        result = self.bridge._compute_confidence(10)
        # (10-3)/(50-3) = 7/47 ≈ 0.1489, 0.3 + 0.1489*0.7 ≈ 0.404
        assert 0.3 < result < 0.5

    def test_at_full_confidence(self):
        result = self.bridge._compute_confidence(50)
        assert result == 1.0

    def test_above_full(self):
        result = self.bridge._compute_confidence(100)
        assert result == 1.0

    def test_monotonically_increasing(self):
        prev = 0
        for tasks in range(0, 60, 5):
            c = self.bridge._compute_confidence(tasks)
            assert c >= prev
            prev = c


# ─── A2H Seal Scorer Tests ──────────────────────────────────────────────


class TestScoreSkillful:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_perfect_worker(self):
        score, _, _ = self.bridge._score_skillful({
            "avg_quality": 5.0, "success_rate": 1.0, "tasks_completed": 100
        })
        assert score > 90

    def test_no_quality_neutral(self):
        score, _, _ = self.bridge._score_skillful({
            "avg_quality": 0, "success_rate": 0.8, "tasks_completed": 10
        })
        # quality_score=50, success_score=80
        assert 40 < score < 70

    def test_zero_tasks(self):
        score, _, _ = self.bridge._score_skillful({
            "avg_quality": 0, "success_rate": 0, "tasks_completed": 0
        })
        assert score >= 0

    def test_volume_factor_boosts_high_volume(self):
        low, _, _ = self.bridge._score_skillful({
            "avg_quality": 4.0, "success_rate": 0.9, "tasks_completed": 1
        })
        high, _, _ = self.bridge._score_skillful({
            "avg_quality": 4.0, "success_rate": 0.9, "tasks_completed": 100
        })
        assert high > low


class TestScoreReliable:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_perfect_reliability(self):
        score, _, _ = self.bridge._score_reliable({
            "success_rate": 1.0, "tasks_completed": 50,
            "tasks_failed": 0, "tasks_expired": 0
        })
        assert score > 90

    def test_expiry_penalty(self):
        no_expiry, _, _ = self.bridge._score_reliable({
            "success_rate": 0.8, "tasks_completed": 8,
            "tasks_failed": 2, "tasks_expired": 0
        })
        with_expiry, _, _ = self.bridge._score_reliable({
            "success_rate": 0.8, "tasks_completed": 8,
            "tasks_failed": 0, "tasks_expired": 2
        })
        assert no_expiry > with_expiry

    def test_zero_success(self):
        score, _, _ = self.bridge._score_reliable({
            "success_rate": 0, "tasks_completed": 0,
            "tasks_failed": 5, "tasks_expired": 0
        })
        assert score < 20


class TestScoreThorough:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_no_quality_data(self):
        score, _, _ = self.bridge._score_thorough({
            "avg_quality": 0, "quality_scores": [], "tasks_completed": 0
        })
        assert score == 50  # Neutral

    def test_high_consistent_quality(self):
        score, _, _ = self.bridge._score_thorough({
            "avg_quality": 4.8, "quality_scores": [4.8, 4.9, 4.7, 4.8, 4.9],
            "tasks_completed": 5
        })
        assert score > 80

    def test_high_but_inconsistent(self):
        consistent, _, _ = self.bridge._score_thorough({
            "quality_scores": [4.5, 4.5, 4.5, 4.5, 4.5],
            "tasks_completed": 5
        })
        inconsistent, _, _ = self.bridge._score_thorough({
            "quality_scores": [5.0, 1.0, 5.0, 1.0, 5.0],
            "tasks_completed": 5
        })
        # Same average (3.4 vs 3.0ish) but consistency penalty
        assert consistent > inconsistent

    def test_synthesized_from_average(self):
        score, _, _ = self.bridge._score_thorough({
            "avg_quality": 4.0, "tasks_completed": 10
        })
        assert score > 50


class TestScoreEngaged:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_highly_engaged(self):
        score, _, _ = self.bridge._score_engaged({
            "tasks_completed": 100,
            "categories": {"a": 20, "b": 20, "c": 20, "d": 20, "e": 20},
            "total_revenue_usd": 500,
            "last_active": time.time() - 3600  # 1 hour ago
        })
        assert score > 80

    def test_inactive_worker(self):
        score, _, _ = self.bridge._score_engaged({
            "tasks_completed": 1,
            "categories": {},
            "total_revenue_usd": 0,
            "last_active": time.time() - 86400 * 60  # 60 days ago
        })
        assert score < 30

    def test_no_last_active(self):
        score, _, _ = self.bridge._score_engaged({
            "tasks_completed": 10,
            "categories": {"a": 10},
            "total_revenue_usd": 50,
            "last_active": 0
        })
        # No recency points
        assert score >= 0


class TestScoreHelpful:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_no_tasks(self):
        score, _, _ = self.bridge._score_helpful({
            "tasks_completed": 0, "tasks_failed": 0,
            "tasks_expired": 0, "categories": {}
        })
        assert score == 30

    def test_high_completion(self):
        score, _, _ = self.bridge._score_helpful({
            "tasks_completed": 50, "tasks_failed": 2,
            "tasks_expired": 0, "categories": {"a": 20, "b": 15, "c": 10, "d": 7}
        })
        assert score > 70

    def test_many_failures_low_score(self):
        score, _, _ = self.bridge._score_helpful({
            "tasks_completed": 2, "tasks_failed": 10,
            "tasks_expired": 5, "categories": {"a": 2}
        })
        assert score < 30


class TestScoreResponsive:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_no_completions(self):
        score, _, _ = self.bridge._score_responsive({
            "avg_duration_seconds": 0, "tasks_completed": 0
        })
        assert score == 50

    def test_fast_worker(self):
        score, _, _ = self.bridge._score_responsive({
            "avg_duration_seconds": 3600,  # 1 hour
            "tasks_completed": 20
        })
        assert score == 100

    def test_normal_speed(self):
        score, _, _ = self.bridge._score_responsive({
            "avg_duration_seconds": 12 * 3600,  # 12 hours
            "tasks_completed": 20
        })
        assert 55 < score < 65

    def test_slow_worker(self):
        score, _, _ = self.bridge._score_responsive({
            "avg_duration_seconds": 48 * 3600,  # 48 hours
            "tasks_completed": 10
        })
        assert score < 25

    def test_consistency_bonus(self):
        # Consistent durations get bonus
        consistent, _, _ = self.bridge._score_responsive({
            "avg_duration_seconds": 7200,
            "tasks_completed": 5,
            "durations": [7000, 7200, 7400, 7100, 7300]
        })
        # Just fast without consistency data
        fast_only, _, _ = self.bridge._score_responsive({
            "avg_duration_seconds": 7200,
            "tasks_completed": 5,
        })
        assert consistent >= fast_only


class TestScoreCurious:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_no_categories(self):
        score, _, _ = self.bridge._score_curious({"categories": {}})
        assert score == 30

    def test_single_category(self):
        score, _, _ = self.bridge._score_curious({
            "categories": {"delivery": 50}
        })
        # 1 cat → 1/5*60=12, 1 cat no evenness → 12
        assert score < 30

    def test_diverse_even_categories(self):
        score, _, _ = self.bridge._score_curious({
            "categories": {"a": 10, "b": 10, "c": 10, "d": 10, "e": 10}
        })
        # 5 cats → 60, perfect evenness → 40 → total 100
        assert score > 90

    def test_diverse_but_uneven(self):
        even, _, _ = self.bridge._score_curious({
            "categories": {"a": 10, "b": 10, "c": 10}
        })
        uneven, _, _ = self.bridge._score_curious({
            "categories": {"a": 100, "b": 1, "c": 1}
        })
        assert even > uneven


# ─── H2A Seal Scorer Tests ──────────────────────────────────────────────


class TestScoreFair:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_no_data(self):
        score, _, _ = self.bridge._score_fair({
            "categories": {}, "tasks_assigned": 0
        })
        assert score == 50

    def test_even_distribution(self):
        score, _, _ = self.bridge._score_fair({
            "categories": {"a": 10, "b": 10, "c": 10},
            "tasks_assigned": 30
        })
        assert score > 80

    def test_single_category_concentration(self):
        score, _, _ = self.bridge._score_fair({
            "categories": {"a": 100},
            "tasks_assigned": 100
        })
        assert score == 50  # Single category = 50 default


class TestScoreAccurate:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_no_tasks(self):
        score, _, _ = self.bridge._score_accurate({
            "tasks_completed": 0, "tasks_failed": 0, "tasks_expired": 0
        })
        assert score == 50

    def test_high_completion(self):
        score, _, _ = self.bridge._score_accurate({
            "tasks_completed": 95, "tasks_failed": 3, "tasks_expired": 2
        })
        assert score > 80

    def test_low_completion(self):
        score, _, _ = self.bridge._score_accurate({
            "tasks_completed": 2, "tasks_failed": 5, "tasks_expired": 3
        })
        assert score < 30


class TestScoreEthical:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_no_data(self):
        score, _, _ = self.bridge._score_ethical({
            "tasks_completed": 0, "tasks_failed": 0, "tasks_expired": 0
        })
        assert score == 50

    def test_ethical_agent(self):
        score, _, _ = self.bridge._score_ethical({
            "tasks_completed": 50, "tasks_failed": 2, "tasks_expired": 0
        })
        # High completion + zero expirations + volume bonus
        assert score > 80

    def test_many_expirations(self):
        score, _, _ = self.bridge._score_ethical({
            "tasks_completed": 5, "tasks_failed": 0, "tasks_expired": 15
        })
        # Low completion rate + many expirations
        assert score < 40


# ─── evaluate_worker Tests ───────────────────────────────────────────────


class TestEvaluateWorker:
    def setup_method(self):
        self.bridge = SealBridge(evaluator_agent_id="agent_2106")

    def test_below_minimum_tasks(self):
        profile = self.bridge.evaluate_worker(
            worker_address="0x1", agent_id="w1",
            metrics={"tasks_completed": 1, "tasks_failed": 0}
        )
        assert len(profile.recommendations) == 0
        assert profile.data_points == 1

    def test_basic_evaluation(self):
        profile = self.bridge.evaluate_worker(
            worker_address="0x1", agent_id="w1",
            metrics={
                "tasks_completed": 20, "tasks_failed": 2, "tasks_expired": 1,
                "avg_quality": 4.2, "success_rate": 0.87,
                "avg_duration_seconds": 7200,
                "categories": {"delivery": 10, "photo": 10},
                "total_revenue_usd": 150,
            }
        )
        assert len(profile.recommendations) > 0
        assert profile.data_points == 22
        assert profile.overall_score > 0

        # Should have A2H seals
        seal_types = {r.seal_type for r in profile.recommendations}
        assert seal_types.issubset(A2H_SEALS)

    def test_all_a2h_seals_generated(self):
        profile = self.bridge.evaluate_worker(
            worker_address="0x1", agent_id="w1",
            metrics={
                "tasks_completed": 50, "tasks_failed": 5, "tasks_expired": 2,
                "avg_quality": 4.5, "success_rate": 0.88,
                "avg_duration_seconds": 3600,
                "categories": {"a": 10, "b": 15, "c": 10, "d": 10, "e": 7},
                "total_revenue_usd": 300,
                "last_active": time.time(),
            }
        )
        seal_types = {r.seal_type for r in profile.recommendations}
        assert seal_types == A2H_SEALS

    def test_scores_clamped_0_100(self):
        profile = self.bridge.evaluate_worker(
            worker_address="0x1", agent_id="w1",
            metrics={
                "tasks_completed": 200, "tasks_failed": 0, "tasks_expired": 0,
                "avg_quality": 5.0, "success_rate": 1.0,
                "avg_duration_seconds": 1800,
                "categories": {"a": 50, "b": 50, "c": 50, "d": 50},
                "total_revenue_usd": 1000,
                "last_active": time.time(),
            }
        )
        for rec in profile.recommendations:
            assert 0 <= rec.score <= 100

    def test_evaluator_agent_id_set(self):
        profile = self.bridge.evaluate_worker(
            worker_address="0x1", agent_id="w1",
            metrics={"tasks_completed": 5, "tasks_failed": 0}
        )
        for rec in profile.recommendations:
            assert rec.evaluator_agent_id == "agent_2106"

    def test_extreme_scores_lower_confidence(self):
        profile = self.bridge.evaluate_worker(
            worker_address="0x1", agent_id="w1",
            metrics={
                "tasks_completed": 10, "tasks_failed": 0,
                "avg_quality": 5.0, "success_rate": 1.0,
                "avg_duration_seconds": 900,
                "categories": {"a": 10},
                "total_revenue_usd": 50,
            }
        )
        base_confidence = self.bridge._compute_confidence(10)
        for rec in profile.recommendations:
            if rec.score > 90:
                assert rec.confidence <= base_confidence

    def test_h2a_quadrant(self):
        # Test that H2A quadrant only gets H2A seals
        profile = self.bridge.evaluate_worker(
            worker_address="0x1", agent_id="w1",
            metrics={
                "tasks_completed": 20, "tasks_failed": 2,
                "avg_quality": 4.0, "success_rate": 0.9,
                "avg_duration_seconds": 7200,
                "categories": {"a": 20},
            },
            quadrant=SealQuadrant.H2A
        )
        for rec in profile.recommendations:
            assert rec.quadrant == SealQuadrant.H2A


# ─── evaluate_agent_for_worker Tests ─────────────────────────────────────


class TestEvaluateAgentForWorker:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_below_minimum(self):
        profile = self.bridge.evaluate_agent_for_worker(
            agent_address="0x1", agent_id="a1",
            metrics={"tasks_assigned": 1}
        )
        assert len(profile.recommendations) == 0

    def test_basic_h2a_evaluation(self):
        profile = self.bridge.evaluate_agent_for_worker(
            agent_address="0x1", agent_id="a1",
            metrics={
                "tasks_assigned": 30, "tasks_completed": 25,
                "tasks_failed": 3, "tasks_expired": 2,
                "avg_quality": 4.0, "success_rate": 0.83,
                "avg_duration_seconds": 14400,
                "categories": {"a": 15, "b": 15},
            }
        )
        seal_types = {r.seal_type for r in profile.recommendations}
        assert "FAIR" in seal_types
        assert "ACCURATE" in seal_types
        assert "ETHICAL" in seal_types

        for rec in profile.recommendations:
            assert rec.quadrant == SealQuadrant.H2A


# ─── prepare_batch Tests ─────────────────────────────────────────────────


class TestPrepareBatch:
    def setup_method(self):
        self.bridge = SealBridge(gas_per_seal=80000)

    def _make_rec(self, seal_type, score, confidence):
        return SealRecommendation(
            seal_type=seal_type, quadrant=SealQuadrant.A2H,
            subject_address="0x1", evaluator_agent_id="a",
            score=score, confidence=confidence,
            evidence_summary="", evidence_hash="", reasoning=""
        )

    def test_empty_list(self):
        batch = self.bridge.prepare_batch([])
        assert len(batch.seals) == 0
        assert batch.total_gas_estimate == 0

    def test_filters_by_confidence(self):
        recs = [
            self._make_rec("SKILLFUL", 80, 0.8),
            self._make_rec("RELIABLE", 70, 0.3),  # Below default 0.5
        ]
        batch = self.bridge.prepare_batch(recs)
        assert len(batch.seals) == 1
        assert batch.seals[0].seal_type == "SKILLFUL"

    def test_custom_min_confidence(self):
        recs = [
            self._make_rec("SKILLFUL", 80, 0.6),
            self._make_rec("RELIABLE", 70, 0.8),
        ]
        batch = self.bridge.prepare_batch(recs, min_confidence=0.7)
        assert len(batch.seals) == 1
        assert batch.seals[0].seal_type == "RELIABLE"

    def test_sorted_by_score_descending(self):
        recs = [
            self._make_rec("A", 60, 0.8),
            self._make_rec("B", 90, 0.8),
            self._make_rec("C", 75, 0.8),
        ]
        batch = self.bridge.prepare_batch(recs)
        scores = [s.score for s in batch.seals]
        assert scores == [90, 75, 60]

    def test_gas_estimation(self):
        recs = [self._make_rec(f"S{i}", 80, 0.8) for i in range(5)]
        batch = self.bridge.prepare_batch(recs)
        assert batch.total_gas_estimate == 5 * 80000

    def test_batch_limit_50(self):
        recs = [self._make_rec(f"S{i}", 80, 0.8) for i in range(60)]
        batch = self.bridge.prepare_batch(recs)
        assert len(batch.seals) == 50


# ─── Issuance History Tests ──────────────────────────────────────────────


class TestIssuanceHistory:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_initial_count(self):
        assert self.bridge.issuance_count == 0

    def test_record_issuance(self):
        record = SealIssuanceRecord(
            seal_id=1, tx_hash="0xabc",
            seal_type="SKILLFUL", subject_address="0x1",
            score=85, quadrant=SealQuadrant.A2H
        )
        self.bridge.record_issuance(record)
        assert self.bridge.issuance_count == 1

    def test_history_limit(self):
        bridge = SealBridge()
        bridge._max_issuance_history = 10
        for i in range(15):
            bridge.record_issuance(SealIssuanceRecord(
                seal_id=i, tx_hash=f"0x{i}",
                seal_type="SKILLFUL", subject_address="0x1",
                score=80, quadrant=SealQuadrant.A2H
            ))
        assert bridge.issuance_count == 10

    def test_get_issuance_history(self):
        for i in range(5):
            self.bridge.record_issuance(SealIssuanceRecord(
                seal_id=i, tx_hash=f"0x{i}",
                seal_type="SKILLFUL", subject_address="0x1",
                score=80, quadrant=SealQuadrant.A2H
            ))
        history = self.bridge.get_issuance_history(limit=3)
        assert len(history) == 3
        assert all(isinstance(h, dict) for h in history)


# ─── Fleet Evaluation Tests ──────────────────────────────────────────────


class TestFleetEvaluation:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_empty_fleet(self):
        profiles = self.bridge.evaluate_fleet({})
        assert profiles == []

    def test_single_agent_fleet(self):
        metrics = {
            "w1": {
                "tasks_completed": 20, "tasks_failed": 2,
                "avg_quality": 4.0, "success_rate": 0.9,
                "avg_duration_seconds": 7200,
                "categories": {"delivery": 20},
                "total_revenue_usd": 100,
            }
        }
        profiles = self.bridge.evaluate_fleet(metrics)
        assert len(profiles) == 1
        assert profiles[0].agent_id == "w1"

    def test_fleet_sorted_by_score(self):
        metrics = {
            "good": {
                "tasks_completed": 50, "tasks_failed": 1,
                "avg_quality": 4.8, "success_rate": 0.98,
                "avg_duration_seconds": 3600,
                "categories": {"a": 20, "b": 30},
                "total_revenue_usd": 300,
                "last_active": time.time(),
            },
            "bad": {
                "tasks_completed": 3, "tasks_failed": 5,
                "avg_quality": 2.0, "success_rate": 0.375,
                "avg_duration_seconds": 86400,
                "categories": {"a": 3},
                "total_revenue_usd": 10,
            },
        }
        profiles = self.bridge.evaluate_fleet(metrics)
        assert profiles[0].agent_id == "good"

    def test_address_map_used(self):
        metrics = {
            "w1": {"tasks_completed": 10, "tasks_failed": 0}
        }
        profiles = self.bridge.evaluate_fleet(
            metrics, address_map={"w1": "0xRealAddress"}
        )
        assert profiles[0].address == "0xRealAddress"

    def test_agents_below_minimum_excluded(self):
        metrics = {
            "enough": {"tasks_completed": 10, "tasks_failed": 0},
            "not_enough": {"tasks_completed": 1, "tasks_failed": 0},
        }
        profiles = self.bridge.evaluate_fleet(metrics)
        # Only "enough" should have recommendations
        assert len(profiles) == 1
        assert profiles[0].agent_id == "enough"


class TestFleetSummary:
    def setup_method(self):
        self.bridge = SealBridge()

    def test_empty_fleet(self):
        summary = self.bridge.fleet_summary([])
        assert summary["agents_evaluated"] == 0
        assert summary["total_seals"] == 0

    def test_basic_summary(self):
        metrics = {
            "w1": {
                "tasks_completed": 30, "tasks_failed": 2,
                "avg_quality": 4.5, "success_rate": 0.94,
                "avg_duration_seconds": 5400,
                "categories": {"a": 15, "b": 17},
                "total_revenue_usd": 200,
                "last_active": time.time(),
            },
            "w2": {
                "tasks_completed": 20, "tasks_failed": 5,
                "avg_quality": 3.5, "success_rate": 0.8,
                "avg_duration_seconds": 14400,
                "categories": {"a": 20},
                "total_revenue_usd": 80,
            },
        }
        profiles = self.bridge.evaluate_fleet(metrics)
        summary = self.bridge.fleet_summary(profiles)
        assert summary["agents_evaluated"] == 2
        assert summary["total_seals"] > 0
        assert "seal_breakdown" in summary
        assert len(summary["top_performers"]) <= 5


# ─── Constants and Seal Type Coverage ────────────────────────────────────


class TestConstants:
    def test_a2h_and_h2a_no_overlap(self):
        assert A2H_SEALS.isdisjoint(H2A_SEALS)

    def test_all_seal_types_defined(self):
        all_defined = set(SEAL_TYPES.keys())
        all_used = A2H_SEALS | H2A_SEALS
        # Every used seal must be defined
        assert all_used.issubset(all_defined)

    def test_quadrant_values(self):
        assert SealQuadrant.H2H.value == "H2H"
        assert SealQuadrant.H2A.value == "H2A"
        assert SealQuadrant.A2H.value == "A2H"
        assert SealQuadrant.A2A.value == "A2A"
