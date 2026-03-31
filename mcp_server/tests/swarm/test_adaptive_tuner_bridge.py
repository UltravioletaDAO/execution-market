"""Tests for AdaptiveTunerBridge — Server-Side Weight Optimization (Module #64)."""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../swarm"))

from adaptive_tuner_bridge import (
    AdaptiveTunerBridge,
    BridgeConfig,
    DecisionRecord,
    OutcomeRecord,
    OutcomeType,
    SignalStats,
    WeightRecommendation,
    SIGNAL_NAMES,
    DEFAULT_WEIGHTS,
    MIN_WEIGHT,
    MAX_WEIGHT,
    VERSION,
)


# ── Helpers ────────────────────────────────────────────────────────────

def make_decision(
    task_id: str = "task_1",
    worker_id: str = "0xW1",
    category: str = "physical",
    signal_scores: dict | None = None,
    final_score: float = 0.75,
) -> dict:
    """Create decision args."""
    return {
        "task_id": task_id,
        "worker_id": worker_id,
        "category": category,
        "signal_scores": signal_scores or {"skill": 0.8, "reputation": 0.7, "reliability": 0.9},
        "final_score": final_score,
    }


def make_supabase_row(
    task_id: str = "task_1",
    status: str = "completed",
    category: str = "physical",
    worker_address: str = "0xW1",
    pre_check_score: float | None = 85.0,
) -> dict:
    """Create a Supabase task row."""
    return {
        "id": task_id,
        "status": status,
        "category": category,
        "worker_address": worker_address,
        "pre_check_score": pre_check_score,
        "created_at": "2026-03-30T10:00:00Z",
        "completed_at": "2026-03-30T12:00:00Z",
        "evidence_count": 3,
    }


def generate_correlated_data(n: int) -> tuple[list[dict], list[dict]]:
    """Generate correlated decision/outcome pairs."""
    decisions = []
    rows = []
    for i in range(n):
        is_success = i % 3 != 0
        scores = {s: 0.5 for s in SIGNAL_NAMES}
        scores["skill"] = 0.8 if is_success else 0.2
        scores["reputation"] = 0.6 if is_success else 0.4

        decisions.append({
            "task_id": f"t_{i}",
            "worker_id": f"0xW{i}",
            "category": "physical",
            "signal_scores": scores,
            "final_score": sum(scores.values()) / len(scores),
        })
        rows.append(make_supabase_row(
            task_id=f"t_{i}",
            status="completed" if is_success else "failed",
            pre_check_score=85.0 if is_success else 20.0,
        ))
    return decisions, rows


# ── Test Classes ───────────────────────────────────────────────────────

class TestDataTypes:
    """Test data type constructors and serialization."""

    def test_decision_record_to_dict(self):
        rec = DecisionRecord(
            task_id="t1", worker_id="w1", category="test",
            timestamp=1.0, signal_scores={"skill": 0.8}, final_score=0.75,
        )
        d = rec.to_dict()
        assert d["task_id"] == "t1"
        assert d["signal_scores"]["skill"] == 0.8

    def test_decision_record_from_dict(self):
        d = {"task_id": "t1", "worker_id": "w1", "signal_scores": {"skill": 0.5}}
        rec = DecisionRecord.from_dict(d)
        assert rec.task_id == "t1"

    def test_outcome_record_to_dict(self):
        rec = OutcomeRecord(
            task_id="t1", outcome=OutcomeType.SUCCESS,
            timestamp=1.0, quality_score=0.9,
        )
        d = rec.to_dict()
        assert d["outcome"] == "success"

    def test_outcome_record_from_dict(self):
        d = {"task_id": "t1", "outcome": "partial", "quality_score": 0.6}
        rec = OutcomeRecord.from_dict(d)
        assert rec.outcome == OutcomeType.PARTIAL

    def test_outcome_record_unknown_outcome(self):
        d = {"task_id": "t1", "outcome": "exploded"}
        rec = OutcomeRecord.from_dict(d)
        assert rec.outcome == OutcomeType.FAILURE

    def test_outcome_score_success(self):
        rec = OutcomeRecord(task_id="t1", outcome=OutcomeType.SUCCESS,
                           timestamp=1.0, quality_score=0.9)
        assert rec.outcome_score == pytest.approx(0.95)

    def test_outcome_score_failure(self):
        rec = OutcomeRecord(task_id="t1", outcome=OutcomeType.FAILURE, timestamp=1.0)
        assert rec.outcome_score == 0.0

    def test_signal_stats_to_dict(self):
        stats = SignalStats(signal="skill", correlation=0.8, separation=0.4,
                           sample_count=50, confidence=0.5)
        d = stats.to_dict()
        assert d["signal"] == "skill"
        assert d["correlation"] == 0.8

    def test_weight_recommendation_to_dict(self):
        rec = WeightRecommendation(signal="skill", current=0.45,
                                   suggested=0.48, delta=0.03, reason="test")
        d = rec.to_dict()
        assert d["delta"] == 0.03


class TestBridgeConfig:
    """Test BridgeConfig."""

    def test_default(self):
        cfg = BridgeConfig()
        assert cfg.adaptation_rate == 0.05
        assert cfg.min_samples == 10

    def test_to_dict(self):
        cfg = BridgeConfig()
        d = cfg.to_dict()
        assert "adaptation_rate" in d

    def test_from_dict(self):
        d = {"min_samples": 20, "adaptation_rate": 0.1}
        cfg = BridgeConfig.from_dict(d)
        assert cfg.min_samples == 20


class TestSupabaseSync:
    """Test outcome ingestion from Supabase rows."""

    def test_sync_completed_tasks(self):
        bridge = AdaptiveTunerBridge()
        rows = [make_supabase_row(task_id=f"t_{i}") for i in range(5)]
        count = bridge.sync_from_supabase(rows)
        assert count == 5

    def test_sync_skips_in_progress(self):
        bridge = AdaptiveTunerBridge()
        rows = [
            make_supabase_row(task_id="t1", status="completed"),
            make_supabase_row(task_id="t2", status="in_progress"),
            make_supabase_row(task_id="t3", status="published"),
        ]
        count = bridge.sync_from_supabase(rows)
        assert count == 1  # Only completed

    def test_sync_maps_statuses(self):
        bridge = AdaptiveTunerBridge()
        rows = [
            make_supabase_row(task_id="t1", status="completed"),
            make_supabase_row(task_id="t2", status="failed"),
            make_supabase_row(task_id="t3", status="expired"),
            make_supabase_row(task_id="t4", status="cancelled"),
            make_supabase_row(task_id="t5", status="disputed"),
        ]
        count = bridge.sync_from_supabase(rows)
        assert count == 5
        assert bridge._outcomes["t1"].outcome == OutcomeType.SUCCESS
        assert bridge._outcomes["t2"].outcome == OutcomeType.FAILURE
        assert bridge._outcomes["t3"].outcome == OutcomeType.TIMEOUT
        assert bridge._outcomes["t4"].outcome == OutcomeType.ABANDONED
        assert bridge._outcomes["t5"].outcome == OutcomeType.PARTIAL

    def test_sync_computes_quality(self):
        bridge = AdaptiveTunerBridge()
        rows = [make_supabase_row(task_id="t1", pre_check_score=85.0)]
        bridge.sync_from_supabase(rows)
        assert bridge._outcomes["t1"].quality_score == pytest.approx(0.85)

    def test_sync_computes_quality_no_score(self):
        bridge = AdaptiveTunerBridge()
        rows = [make_supabase_row(task_id="t1", pre_check_score=None)]
        bridge.sync_from_supabase(rows)
        assert bridge._outcomes["t1"].quality_score == 0.7  # Baseline for completed

    def test_sync_computes_hours(self):
        bridge = AdaptiveTunerBridge()
        rows = [make_supabase_row(task_id="t1")]
        bridge.sync_from_supabase(rows)
        assert bridge._outcomes["t1"].completion_hours == pytest.approx(2.0, abs=0.1)

    def test_sync_updates_metrics(self):
        bridge = AdaptiveTunerBridge()
        bridge.sync_from_supabase([make_supabase_row()])
        assert bridge._metrics["outcomes_ingested"] == 1
        assert bridge._metrics["syncs_completed"] == 1
        assert bridge._sync_count == 1

    def test_sync_auto_pairs_with_decisions(self):
        bridge = AdaptiveTunerBridge()
        bridge.record_decision(**make_decision(task_id="t1"))
        bridge.sync_from_supabase([make_supabase_row(task_id="t1")])
        assert bridge.paired_count == 1

    def test_sync_trimming(self):
        config = BridgeConfig(max_outcomes=5)
        bridge = AdaptiveTunerBridge(config=config)
        rows = [make_supabase_row(task_id=f"t_{i}") for i in range(10)]
        bridge.sync_from_supabase(rows)
        assert len(bridge._outcomes) == 5

    def test_sync_skips_empty_id(self):
        bridge = AdaptiveTunerBridge()
        rows = [{"status": "completed", "category": "test"}]  # No id
        count = bridge.sync_from_supabase(rows)
        assert count == 0


class TestDecisionRecording:
    """Test decision recording."""

    def test_record_decision(self):
        bridge = AdaptiveTunerBridge()
        bridge.record_decision(**make_decision())
        assert bridge._metrics["decisions_recorded"] == 1
        assert len(bridge._decisions) == 1

    def test_auto_pair_with_existing_outcome(self):
        bridge = AdaptiveTunerBridge()
        bridge.sync_from_supabase([make_supabase_row(task_id="t1")])
        bridge.record_decision(**make_decision(task_id="t1"))
        assert bridge.paired_count == 1

    def test_no_duplicate_pairs(self):
        bridge = AdaptiveTunerBridge()
        bridge.record_decision(**make_decision(task_id="t1"))
        bridge.sync_from_supabase([make_supabase_row(task_id="t1")])
        # Sync again — should not duplicate
        bridge.sync_from_supabase([make_supabase_row(task_id="t1")])
        assert bridge.paired_count == 1

    def test_decision_trimming(self):
        config = BridgeConfig(max_decisions=5)
        bridge = AdaptiveTunerBridge(config=config)
        for i in range(10):
            bridge.record_decision(**make_decision(task_id=f"t_{i}"))
        assert len(bridge._decisions) == 5


class TestEffectiveness:
    """Test signal effectiveness computation."""

    def test_empty_returns_empty(self):
        bridge = AdaptiveTunerBridge()
        assert bridge.compute_effectiveness() == {}

    def test_with_correlated_data(self):
        bridge = AdaptiveTunerBridge()
        decisions, rows = generate_correlated_data(30)
        for d in decisions:
            bridge.record_decision(**d)
        bridge.sync_from_supabase(rows)

        eff = bridge.compute_effectiveness()
        assert len(eff) > 0

    def test_positive_correlation(self):
        bridge = AdaptiveTunerBridge()
        decisions, rows = generate_correlated_data(50)
        for d in decisions:
            bridge.record_decision(**d)
        bridge.sync_from_supabase(rows)

        eff = bridge.compute_effectiveness()
        if "skill" in eff:
            assert eff["skill"].correlation > 0

    def test_category_filter(self):
        bridge = AdaptiveTunerBridge()
        decisions, rows = generate_correlated_data(20)
        for d in decisions:
            bridge.record_decision(**d)
        bridge.sync_from_supabase(rows)

        eff = bridge.compute_effectiveness(category="physical")
        assert isinstance(eff, dict)


class TestWeightOptimization:
    """Test weight suggestion."""

    def test_insufficient_data_returns_base(self):
        bridge = AdaptiveTunerBridge()
        weights = bridge.suggest_weights()
        assert weights == dict(DEFAULT_WEIGHTS)

    def test_suggest_with_data(self):
        bridge = AdaptiveTunerBridge()
        decisions, rows = generate_correlated_data(30)
        for d in decisions:
            bridge.record_decision(**d)
        bridge.sync_from_supabase(rows)

        weights = bridge.suggest_weights()
        assert isinstance(weights, dict)
        assert len(weights) > 0

    def test_guardrails_min(self):
        bridge = AdaptiveTunerBridge()
        bridge.apply_weights({"skill": 0.001})
        assert bridge._weights["skill"] >= MIN_WEIGHT

    def test_guardrails_max(self):
        bridge = AdaptiveTunerBridge()
        bridge.apply_weights({"skill": 0.99})
        assert bridge._weights["skill"] <= MAX_WEIGHT

    def test_category_specific(self):
        bridge = AdaptiveTunerBridge()
        decisions, rows = generate_correlated_data(30)
        for d in decisions:
            d["category"] = "special"
            bridge.record_decision(**d)
        for r in rows:
            r["category"] = "special"
        bridge.sync_from_supabase(rows)

        weights = bridge.suggest_weights(category="special")
        assert "special" in bridge._category_weights

    def test_get_recommendations(self):
        bridge = AdaptiveTunerBridge()
        decisions, rows = generate_correlated_data(30)
        for d in decisions:
            bridge.record_decision(**d)
        bridge.sync_from_supabase(rows)

        recs = bridge.get_recommendations()
        assert isinstance(recs, list)
        for r in recs:
            assert isinstance(r, WeightRecommendation)

    def test_get_recommendations_insufficient(self):
        bridge = AdaptiveTunerBridge()
        assert bridge.get_recommendations() == []

    def test_apply_weights(self):
        bridge = AdaptiveTunerBridge()
        bridge.apply_weights({"skill": 0.5, "reputation": 0.3})
        assert bridge._weights["skill"] == 0.5
        assert bridge._weights["reputation"] == 0.3

    def test_apply_ignores_unknown(self):
        bridge = AdaptiveTunerBridge()
        bridge.apply_weights({"unknown": 0.99})
        assert "unknown" not in bridge._weights

    def test_reset_weights(self):
        bridge = AdaptiveTunerBridge()
        bridge.apply_weights({"skill": 0.55})
        bridge._category_weights["cat"] = {"skill": 0.6}
        bridge.reset_weights()
        assert bridge._weights == dict(DEFAULT_WEIGHTS)
        assert bridge._category_weights == {}

    def test_current_weights(self):
        bridge = AdaptiveTunerBridge()
        w = bridge.current_weights
        assert w == dict(DEFAULT_WEIGHTS)
        w["skill"] = 99
        assert bridge._weights["skill"] != 99

    def test_category_weights_accessor(self):
        bridge = AdaptiveTunerBridge()
        bridge._category_weights["cat"] = {"skill": 0.6}
        assert bridge.category_weights("cat")["skill"] == 0.6

    def test_category_weights_fallback(self):
        bridge = AdaptiveTunerBridge()
        assert bridge.category_weights("nonexistent") == bridge.current_weights

    def test_get_weights_for_task(self):
        bridge = AdaptiveTunerBridge()
        bridge._category_weights["special"] = {"skill": 0.6}
        w = bridge.get_weights_for_task({"category": "special"})
        assert w["skill"] == 0.6

    def test_get_weights_for_task_fallback(self):
        bridge = AdaptiveTunerBridge()
        w = bridge.get_weights_for_task({"category": "unknown"})
        assert w == dict(DEFAULT_WEIGHTS)


class TestDiagnostics:
    """Test health and diagnostic methods."""

    def test_health_empty(self):
        bridge = AdaptiveTunerBridge()
        h = bridge.health()
        assert h["status"] == "stale"
        assert h["paired_count"] == 0
        assert h["can_suggest"] is False

    def test_health_after_sync(self):
        bridge = AdaptiveTunerBridge()
        bridge.sync_from_supabase([make_supabase_row()])
        h = bridge.health()
        assert h["status"] == "healthy"
        assert h["sync_count"] == 1

    def test_summary(self):
        bridge = AdaptiveTunerBridge()
        s = bridge.summary()
        assert s["version"] == VERSION
        assert "metrics" in s
        assert "sync" in s

    def test_summary_with_data(self):
        bridge = AdaptiveTunerBridge()
        decisions, rows = generate_correlated_data(20)
        for d in decisions:
            bridge.record_decision(**d)
        bridge.sync_from_supabase(rows)
        s = bridge.summary()
        assert s["paired_count"] > 0

    def test_metrics(self):
        bridge = AdaptiveTunerBridge()
        m = bridge.metrics()
        assert "decisions_recorded" in m

    def test_outcome_distribution(self):
        bridge = AdaptiveTunerBridge()
        bridge.sync_from_supabase([
            make_supabase_row(task_id="t1", status="completed"),
            make_supabase_row(task_id="t2", status="failed"),
            make_supabase_row(task_id="t3", status="completed"),
        ])
        dist = bridge.outcome_distribution()
        assert dist["success"] == 2
        assert dist["failure"] == 1

    def test_success_rate(self):
        bridge = AdaptiveTunerBridge()
        bridge.sync_from_supabase([
            make_supabase_row(task_id="t1", status="completed"),
            make_supabase_row(task_id="t2", status="completed"),
            make_supabase_row(task_id="t3", status="failed"),
        ])
        assert bridge.success_rate() == pytest.approx(2 / 3)

    def test_success_rate_empty(self):
        bridge = AdaptiveTunerBridge()
        assert bridge.success_rate() == 0.0

    def test_list_categories(self):
        bridge = AdaptiveTunerBridge()
        bridge.record_decision(**make_decision(task_id="t1", category="phys"))
        bridge.record_decision(**make_decision(task_id="t2", category="digital"))
        cats = bridge.list_categories()
        assert cats == ["digital", "phys"]


class TestPersistence:
    """Test save/load round-trip."""

    def test_save_creates_file(self):
        bridge = AdaptiveTunerBridge()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            assert os.path.exists(path)
            with open(path) as f:
                data = json.load(f)
            assert data["version"] == VERSION
        finally:
            os.unlink(path)

    def test_load_round_trip(self):
        bridge = AdaptiveTunerBridge()
        decisions, rows = generate_correlated_data(15)
        for d in decisions:
            bridge.record_decision(**d)
        bridge.sync_from_supabase(rows)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            restored = AdaptiveTunerBridge.load(path)
            assert restored.paired_count == bridge.paired_count
            assert restored._weights == bridge._weights
        finally:
            os.unlink(path)

    def test_load_preserves_category_weights(self):
        bridge = AdaptiveTunerBridge()
        bridge._category_weights["cat"] = {"skill": 0.6}

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            restored = AdaptiveTunerBridge.load(path)
            assert "cat" in restored._category_weights
        finally:
            os.unlink(path)


class TestEdgeCases:
    """Test edge cases."""

    def test_pearson_too_few(self):
        r = AdaptiveTunerBridge._pearson([1.0], [2.0])
        assert r == 0.0

    def test_pearson_constant(self):
        r = AdaptiveTunerBridge._pearson([5.0, 5.0, 5.0], [1.0, 2.0, 3.0])
        assert r == 0.0

    def test_pearson_perfect(self):
        r = AdaptiveTunerBridge._pearson([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert r == pytest.approx(1.0, abs=0.001)

    def test_empty_sync(self):
        bridge = AdaptiveTunerBridge()
        count = bridge.sync_from_supabase([])
        assert count == 0

    def test_status_to_outcome_unknown(self):
        result = AdaptiveTunerBridge._status_to_outcome("in_progress")
        assert result is None

    def test_compute_quality_clamping(self):
        assert AdaptiveTunerBridge._compute_quality({"pre_check_score": 150}) == 1.0
        assert AdaptiveTunerBridge._compute_quality({"pre_check_score": -10}) == 0.0

    def test_compute_hours_no_timestamps(self):
        assert AdaptiveTunerBridge._compute_hours({}) == 0.0

    def test_compute_hours_bad_timestamps(self):
        assert AdaptiveTunerBridge._compute_hours(
            {"created_at": "bad", "completed_at": "also bad"}
        ) == 0.0
