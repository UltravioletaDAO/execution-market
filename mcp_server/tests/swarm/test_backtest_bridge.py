"""
Tests for BacktestBridge — Server-Side Routing Validation (Module #65)
=====================================================================
"""

from __future__ import annotations

import json
import os
import statistics
import tempfile
import time
import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "swarm"))

from backtest_bridge import (
    BacktestBridge,
    DecisionRecord,
    OutcomeRecord,
    ConfigResult,
    PairwiseComparison,
    OverfitResult,
    BacktestResult,
    DEFAULT_WEIGHTS,
    SIGNAL_NAMES,
    MIN_PAIRS_FOR_SIGNIFICANCE,
    VERSION,
)


# ── Helpers ──────────────────────────────────────────────────────────

def make_signal_scores(
    skill: float = 0.5,
    reputation: float = 0.5,
    reliability: float = 0.5,
    recency: float = 0.5,
) -> dict[str, float]:
    return {s: 0.5 for s in SIGNAL_NAMES} | {
        "skill": skill,
        "reputation": reputation,
        "reliability": reliability,
        "recency": recency,
    }


def make_decision(
    task_id: str = "task_1",
    worker_id: str = "worker_1",
    category: str = "physical_verification",
    timestamp: float | None = None,
    signal_scores: dict | None = None,
    final_score: float = 0.5,
    rank: int = 1,
) -> DecisionRecord:
    return DecisionRecord(
        task_id=task_id,
        worker_id=worker_id,
        category=category,
        timestamp=timestamp or time.time(),
        signal_scores=signal_scores or make_signal_scores(),
        final_score=final_score,
        rank=rank,
    )


def make_outcome(
    task_id: str = "task_1",
    outcome: str = "success",
    quality_score: float = 0.8,
    timestamp: float | None = None,
) -> OutcomeRecord:
    return OutcomeRecord(
        task_id=task_id,
        outcome=outcome,
        timestamp=timestamp or time.time(),
        quality_score=quality_score,
    )


def generate_dataset(
    n: int = 50,
    success_rate: float = 0.7,
) -> tuple[list[DecisionRecord], list[OutcomeRecord]]:
    decisions = []
    outcomes = []
    base_time = time.time() - n * 3600

    for i in range(n):
        is_success = i < int(n * success_rate)
        skill = 0.8 if is_success else 0.2
        scores = make_signal_scores(
            skill=skill,
            reputation=0.6 if is_success else 0.4,
            reliability=0.7 if is_success else 0.3,
        )

        d = make_decision(
            task_id=f"task_{i}",
            worker_id=f"worker_{i % 10}",
            category=["physical_verification", "digital_task", "data_collection"][i % 3],
            timestamp=base_time + i * 3600,
            signal_scores=scores,
        )

        o = make_outcome(
            task_id=f"task_{i}",
            outcome="success" if is_success else "failure",
            quality_score=0.85 if is_success else 0.2,
            timestamp=base_time + i * 3600 + 7200,
        )

        decisions.append(d)
        outcomes.append(o)

    return decisions, outcomes


# ══════════════════════════════════════════════════════════════════════
# Initialization
# ══════════════════════════════════════════════════════════════════════

class TestInit:
    def test_fresh_bridge(self):
        bridge = BacktestBridge()
        assert bridge.decision_count == 0
        assert bridge.outcome_count == 0
        assert bridge.matched_count == 0

    def test_summary_empty(self):
        bridge = BacktestBridge()
        s = bridge.summary()
        assert s["version"] == VERSION
        assert s["decisions"] == 0

    def test_health_empty(self):
        bridge = BacktestBridge()
        h = bridge.health()
        assert h["healthy"] is False


# ══════════════════════════════════════════════════════════════════════
# Data Loading
# ══════════════════════════════════════════════════════════════════════

class TestDataLoading:
    def test_load_decisions(self):
        bridge = BacktestBridge()
        decisions, _ = generate_dataset(10)
        bridge.load_decisions(decisions)
        assert bridge.decision_count == 10

    def test_load_outcomes(self):
        bridge = BacktestBridge()
        _, outcomes = generate_dataset(10)
        bridge.load_outcomes(outcomes)
        assert bridge.outcome_count == 10

    def test_matched_pairs(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(20)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)
        assert bridge.matched_count == 20

    def test_partial_match(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(20)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes[:10])
        assert bridge.matched_count == 10

    def test_add_decision(self):
        bridge = BacktestBridge()
        bridge.add_decision(make_decision())
        assert bridge.decision_count == 1

    def test_add_outcome(self):
        bridge = BacktestBridge()
        bridge.add_outcome(make_outcome())
        assert bridge.outcome_count == 1


# ══════════════════════════════════════════════════════════════════════
# Core Backtest
# ══════════════════════════════════════════════════════════════════════

class TestCoreBacktest:
    def test_empty_run(self):
        bridge = BacktestBridge()
        result = bridge.run(configs={"default": DEFAULT_WEIGHTS})
        assert result.matched_pairs == 0

    def test_single_config(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(30)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={"default": DEFAULT_WEIGHTS})
        assert result.matched_pairs == 30
        assert "default" in result.config_results

    def test_multiple_configs(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(50)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={
            "default": DEFAULT_WEIGHTS,
            "skill_heavy": {**DEFAULT_WEIGHTS, "skill": 0.60},
        })
        assert result.configs_tested == 2
        assert result.best_config in result.config_results

    def test_category_filter(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(60)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(
            configs={"default": DEFAULT_WEIGHTS},
            categories=["physical_verification"],
        )
        assert result.matched_pairs < 60

    def test_result_summary(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(30)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={
            "a": DEFAULT_WEIGHTS,
            "b": {**DEFAULT_WEIGHTS, "skill": 0.55},
        })
        summary = result.summary()
        assert "Backtest" in summary

    def test_serialization(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(30)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={"test": DEFAULT_WEIGHTS})
        d = result.to_dict()
        assert isinstance(d, dict)
        json_str = json.dumps(d, default=str)
        parsed = json.loads(json_str)
        assert parsed["configs_tested"] == 1


# ══════════════════════════════════════════════════════════════════════
# Pairwise Comparisons
# ══════════════════════════════════════════════════════════════════════

class TestPairwiseComparisons:
    def test_pairwise_generated(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(50)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={
            "a": DEFAULT_WEIGHTS,
            "b": {**DEFAULT_WEIGHTS, "skill": 0.55},
        })
        assert len(result.pairwise) > 0

    def test_pairwise_min_samples(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(5)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={
            "a": DEFAULT_WEIGHTS,
            "b": {**DEFAULT_WEIGHTS, "skill": 0.55},
        })
        assert len(result.pairwise) == 0

    def test_identical_configs(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(50)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={
            "a": dict(DEFAULT_WEIGHTS),
            "b": dict(DEFAULT_WEIGHTS),
        })
        for p in result.pairwise:
            assert abs(p.mean_diff) < 0.001

    def test_three_configs_three_comparisons(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(50)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={
            "a": DEFAULT_WEIGHTS,
            "b": {**DEFAULT_WEIGHTS, "skill": 0.60},
            "c": {**DEFAULT_WEIGHTS, "reputation": 0.50},
        })
        assert len(result.pairwise) == 3

    def test_pairwise_serialization(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(50)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={
            "a": DEFAULT_WEIGHTS,
            "b": {**DEFAULT_WEIGHTS, "skill": 0.60},
        })
        for p in result.pairwise:
            d = p.to_dict()
            assert "significant" in d
            assert "direction" in d


# ══════════════════════════════════════════════════════════════════════
# Overfitting Detection
# ══════════════════════════════════════════════════════════════════════

class TestOverfitDetection:
    def test_overfit_needs_data(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(10)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={"test": DEFAULT_WEIGHTS})
        assert len(result.overfit_results) == 0

    def test_overfit_runs_with_enough_data(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(100)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={"test": DEFAULT_WEIGHTS})
        assert len(result.overfit_results) == 1

    def test_overfit_disabled(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(100)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={"test": DEFAULT_WEIGHTS}, check_overfit=False)
        assert len(result.overfit_results) == 0

    def test_overfit_serialization(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(100)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={"test": DEFAULT_WEIGHTS})
        for o in result.overfit_results:
            d = o.to_dict()
            assert "likely_overfit" in d


# ══════════════════════════════════════════════════════════════════════
# Ablation Study
# ══════════════════════════════════════════════════════════════════════

class TestAblationStudy:
    def test_ablation_empty(self):
        bridge = BacktestBridge()
        assert bridge.ablation_study() == []

    def test_ablation_basic(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(30)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        results = bridge.ablation_study()
        assert len(results) > 0
        for r in results:
            assert "signal" in r
            assert "importance" in r

    def test_ablation_sorted(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(50)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        results = bridge.ablation_study()
        for i in range(len(results) - 1):
            assert results[i]["importance"] >= results[i+1]["importance"]


# ══════════════════════════════════════════════════════════════════════
# Category Analysis
# ══════════════════════════════════════════════════════════════════════

class TestCategoryAnalysis:
    def test_best_per_category(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(60)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.best_config_per_category(configs={
            "default": DEFAULT_WEIGHTS,
            "alt": {**DEFAULT_WEIGHTS, "skill": 0.55},
        })
        assert isinstance(result, dict)

    def test_category_metrics_in_result(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(60)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={"default": DEFAULT_WEIGHTS})
        cr = result.config_results["default"]
        assert len(cr.category_metrics) > 0


# ══════════════════════════════════════════════════════════════════════
# Data Structures
# ══════════════════════════════════════════════════════════════════════

class TestDataStructures:
    def test_decision_record_roundtrip(self):
        d = make_decision()
        data = d.to_dict()
        d2 = DecisionRecord.from_dict(data)
        assert d2.task_id == d.task_id

    def test_outcome_record_roundtrip(self):
        o = make_outcome()
        data = o.to_dict()
        o2 = OutcomeRecord.from_dict(data)
        assert o2.task_id == o.task_id

    def test_outcome_score_success(self):
        o = make_outcome(outcome="success", quality_score=0.9)
        assert o.outcome_score == 0.5 + 0.5 * 0.9

    def test_outcome_score_failure(self):
        o = make_outcome(outcome="failure")
        assert o.outcome_score == 0.0

    def test_config_result_improvement_ratio(self):
        cr = ConfigResult(
            config_name="test", weights=DEFAULT_WEIGHTS,
            better_picks=10, worse_picks=5,
        )
        assert abs(cr.improvement_ratio - 2.0) < 0.001

    def test_config_result_no_worse(self):
        cr = ConfigResult(
            config_name="test", weights=DEFAULT_WEIGHTS,
            better_picks=5, worse_picks=0,
        )
        assert cr.improvement_ratio == float("inf")


# ══════════════════════════════════════════════════════════════════════
# Persistence
# ══════════════════════════════════════════════════════════════════════

class TestPersistence:
    def test_save_empty(self):
        bridge = BacktestBridge()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            with open(path) as f:
                data = json.load(f)
            assert data["version"] == VERSION
        finally:
            os.unlink(path)

    def test_save_with_results(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(30)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)
        bridge.run(configs={"test": DEFAULT_WEIGHTS})

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            with open(path) as f:
                data = json.load(f)
            assert len(data["results_history"]) == 1
        finally:
            os.unlink(path)


# ══════════════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════════════

class TestHealth:
    def test_health_with_data(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(20)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        h = bridge.health()
        assert h["healthy"] is True
        assert h["decisions"] == 20
        assert h["matched_pairs"] == 20


# ══════════════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_all_successes(self):
        bridge = BacktestBridge()
        for i in range(20):
            bridge.add_decision(make_decision(task_id=f"t_{i}"))
            bridge.add_outcome(make_outcome(task_id=f"t_{i}", outcome="success"))

        result = bridge.run(configs={"default": DEFAULT_WEIGHTS})
        assert result.config_results["default"].success_rate == 1.0

    def test_all_failures(self):
        bridge = BacktestBridge()
        for i in range(20):
            bridge.add_decision(make_decision(task_id=f"t_{i}"))
            bridge.add_outcome(make_outcome(task_id=f"t_{i}", outcome="failure", quality_score=0))

        result = bridge.run(configs={"default": DEFAULT_WEIGHTS})
        assert result.config_results["default"].success_rate == 0.0

    def test_no_outcomes(self):
        bridge = BacktestBridge()
        for i in range(10):
            bridge.add_decision(make_decision(task_id=f"t_{i}"))

        result = bridge.run(configs={"default": DEFAULT_WEIGHTS})
        assert result.matched_pairs == 0

    def test_single_pair(self):
        bridge = BacktestBridge()
        bridge.add_decision(make_decision(task_id="t_1"))
        bridge.add_outcome(make_outcome(task_id="t_1"))

        result = bridge.run(configs={"default": DEFAULT_WEIGHTS})
        assert result.matched_pairs == 1

    def test_duplicate_workers_per_task(self):
        bridge = BacktestBridge()
        bridge.add_decision(make_decision(task_id="t_1", worker_id="w_a", rank=1))
        bridge.add_decision(make_decision(task_id="t_1", worker_id="w_b", rank=2))
        bridge.add_outcome(make_outcome(task_id="t_1"))

        assert bridge.matched_count == 2

    def test_empty_category_filter(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(30)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(
            configs={"default": DEFAULT_WEIGHTS},
            categories=["nonexistent"],
        )
        assert result.matched_pairs == 0


# ══════════════════════════════════════════════════════════════════════
# Stress Tests
# ══════════════════════════════════════════════════════════════════════

class TestStress:
    def test_large_dataset(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(500)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        result = bridge.run(configs={
            "a": DEFAULT_WEIGHTS,
            "b": {**DEFAULT_WEIGHTS, "skill": 0.55},
            "c": {**DEFAULT_WEIGHTS, "reputation": 0.40},
        })
        assert result.matched_pairs == 500
        assert result.duration_ms < 5000

    def test_many_configs(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(100)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        configs = {f"c_{i}": {**DEFAULT_WEIGHTS, "skill": 0.1 + i * 0.05} for i in range(10)}
        result = bridge.run(configs=configs)
        assert result.configs_tested == 10
        assert len(result.pairwise) == 45


# ══════════════════════════════════════════════════════════════════════
# Results History
# ══════════════════════════════════════════════════════════════════════

class TestResultsHistory:
    def test_history_accumulates(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(30)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        bridge.run(configs={"a": DEFAULT_WEIGHTS})
        bridge.run(configs={"b": DEFAULT_WEIGHTS})
        assert len(bridge._results_history) == 2

    def test_history_in_summary(self):
        bridge = BacktestBridge()
        decisions, outcomes = generate_dataset(20)
        bridge.load_decisions(decisions)
        bridge.load_outcomes(outcomes)

        bridge.run(configs={"a": DEFAULT_WEIGHTS})
        s = bridge.summary()
        assert s["results_history_length"] == 1
        assert s["last_best_config"] is not None
