"""
Tests for RoutingOptimizer — Self-Tuning Routing Weights
=========================================================

Covers:
  - RoutingWeights: clamping, normalization, distance, mutation, serialization
  - TaskRecord: success detection, data model
  - FitnessScore: viability, Pareto dominance
  - FitnessEvaluator: scoring, empty data, single records, edge cases
  - RoutingOptimizer: population seeding, evaluation, evolution, full optimization
  - Sensitivity analysis, category analysis
  - RoutingRecommendation: auto-apply logic
  - Serialization: save/load cycle
"""

import math
import random
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "swarm"))

from routing_optimizer import (
    RoutingWeights,
    TaskRecord,
    FitnessScore,
    FitnessEvaluator,
    RoutingOptimizer,
    ConfigCandidate,
    RoutingRecommendation,
    OptimizationRun,
    OutcomeType,
)


# ─── Fixtures ────────────────────────────────────────────────


def make_task(
    task_id="t1",
    category="physical_verification",
    outcome=OutcomeType.COMPLETED,
    quality=0.8,
    hours=2.0,
    bounty=5.0,
    skill_match=0.7,
    reputation=0.6,
    worker="w1",
):
    return TaskRecord(
        task_id=task_id,
        category=category,
        outcome=outcome,
        quality_score=quality,
        completion_hours=hours,
        bounty_usd=bounty,
        worker_skill_match=skill_match,
        worker_reputation=reputation,
        assigned_worker=worker,
    )


def make_completed_records(n=20):
    """Generate n completed tasks with varied metrics."""
    records = []
    categories = ["physical_verification", "data_collection", "content_creation"]
    for i in range(n):
        records.append(
            make_task(
                task_id=f"t{i}",
                category=categories[i % len(categories)],
                outcome=OutcomeType.COMPLETED if i % 5 != 0 else OutcomeType.EXPIRED,
                quality=0.5 + (i % 10) * 0.05,
                hours=1.0 + (i % 8) * 0.5,
                bounty=2.0 + (i % 5) * 1.0,
                skill_match=0.4 + (i % 6) * 0.1,
                reputation=0.3 + (i % 7) * 0.1,
                worker=f"w{i % 4}",
            )
        )
    return records


# ═══════════════════════════════════════════════════════════════
# RoutingWeights
# ═══════════════════════════════════════════════════════════════


class TestRoutingWeights:
    def test_defaults(self):
        w = RoutingWeights()
        assert w.skill_match == 0.35
        assert w.reputation == 0.25
        assert w.capacity == 0.15
        assert w.speed == 0.15
        assert w.cost == 0.10

    def test_total(self):
        w = RoutingWeights()
        assert abs(w.total - 1.0) < 0.001

    def test_clamping_negative(self):
        w = RoutingWeights(skill_match=-0.5, reputation=1.5)
        assert w.skill_match == 0.0
        assert w.reputation == 1.0

    def test_clamping_above_one(self):
        w = RoutingWeights(cost=2.0)
        assert w.cost == 1.0

    def test_normalized(self):
        w = RoutingWeights(0.5, 0.5, 0.5, 0.5, 0.5)
        n = w.normalized()
        assert abs(n.total - 1.0) < 0.001
        assert abs(n.skill_match - 0.2) < 0.001

    def test_normalized_zero_total(self):
        w = RoutingWeights(0.0, 0.0, 0.0, 0.0, 0.0)
        n = w.normalized()
        assert abs(n.skill_match - 0.2) < 0.001  # Falls back to equal weights

    def test_to_list(self):
        w = RoutingWeights(0.1, 0.2, 0.3, 0.4, 0.0)
        lst = w.to_list()
        assert lst == [0.1, 0.2, 0.3, 0.4, 0.0]

    def test_from_list(self):
        w = RoutingWeights.from_list([0.1, 0.2, 0.3, 0.4, 0.0])
        assert w.skill_match == 0.1
        assert w.cost == 0.0

    def test_from_list_wrong_length(self):
        with pytest.raises(ValueError):
            RoutingWeights.from_list([0.1, 0.2])

    def test_distance_same(self):
        w = RoutingWeights()
        assert w.distance(w) == 0.0

    def test_distance_different(self):
        a = RoutingWeights(1.0, 0.0, 0.0, 0.0, 0.0)
        b = RoutingWeights(0.0, 1.0, 0.0, 0.0, 0.0)
        d = a.distance(b)
        assert d == pytest.approx(math.sqrt(2.0), abs=0.01)

    def test_mutate_stays_valid(self):
        random.seed(42)
        w = RoutingWeights()
        mutated = w.mutate(0.1)
        # Should still be normalized
        assert abs(mutated.total - 1.0) < 0.01
        # All values non-negative
        for v in mutated.to_list():
            assert v >= 0.0

    def test_mutate_produces_variation(self):
        random.seed(42)
        w = RoutingWeights()
        mutated = w.mutate(0.5)  # Large mutation rate
        # Should differ from original
        assert w.distance(mutated) > 0.0


# ═══════════════════════════════════════════════════════════════
# TaskRecord
# ═══════════════════════════════════════════════════════════════


class TestTaskRecord:
    def test_completed_is_success(self):
        r = make_task(outcome=OutcomeType.COMPLETED)
        assert r.is_success is True

    def test_expired_not_success(self):
        r = make_task(outcome=OutcomeType.EXPIRED)
        assert r.is_success is False

    def test_rejected_not_success(self):
        r = make_task(outcome=OutcomeType.REJECTED)
        assert r.is_success is False

    def test_cancelled_not_success(self):
        r = make_task(outcome=OutcomeType.CANCELLED)
        assert r.is_success is False

    def test_defaults(self):
        r = TaskRecord(task_id="t1")
        assert r.category == ""
        assert r.bounty_usd == 0.0
        assert r.outcome == OutcomeType.COMPLETED


# ═══════════════════════════════════════════════════════════════
# FitnessScore
# ═══════════════════════════════════════════════════════════════


class TestFitnessScore:
    def test_default_not_viable(self):
        f = FitnessScore()
        assert f.is_viable is False

    def test_viable_with_completions(self):
        f = FitnessScore(completion_rate=0.5)
        assert f.is_viable is True

    def test_dominance_clear(self):
        a = FitnessScore(
            completion_rate=0.8, avg_quality=0.9, avg_speed=0.7, cost_efficiency=0.6
        )
        b = FitnessScore(
            completion_rate=0.5, avg_quality=0.5, avg_speed=0.5, cost_efficiency=0.5
        )
        assert a.dominates(b) is True
        assert b.dominates(a) is False

    def test_dominance_equal(self):
        a = FitnessScore(
            completion_rate=0.8, avg_quality=0.9, avg_speed=0.7, cost_efficiency=0.6
        )
        b = FitnessScore(
            completion_rate=0.8, avg_quality=0.9, avg_speed=0.7, cost_efficiency=0.6
        )
        # Equal in all dimensions — not strictly better in any
        assert a.dominates(b) is False

    def test_dominance_mixed(self):
        a = FitnessScore(
            completion_rate=0.9, avg_quality=0.5, avg_speed=0.7, cost_efficiency=0.6
        )
        b = FitnessScore(
            completion_rate=0.5, avg_quality=0.9, avg_speed=0.7, cost_efficiency=0.6
        )
        # Neither dominates (a beats on completion, b beats on quality)
        assert a.dominates(b) is False
        assert b.dominates(a) is False


# ═══════════════════════════════════════════════════════════════
# FitnessEvaluator
# ═══════════════════════════════════════════════════════════════


class TestFitnessEvaluator:
    def test_empty_records(self):
        evaluator = FitnessEvaluator()
        score = evaluator.evaluate(RoutingWeights(), [])
        assert score.completion_rate == 0.0
        assert score.composite == 0.0

    def test_all_completed(self):
        evaluator = FitnessEvaluator()
        records = [make_task(task_id=f"t{i}", worker=f"w{i}") for i in range(5)]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert score.completion_rate == 1.0
        assert score.avg_quality > 0.0
        assert score.composite > 0.0

    def test_all_expired(self):
        evaluator = FitnessEvaluator()
        records = [
            make_task(task_id=f"t{i}", outcome=OutcomeType.EXPIRED) for i in range(5)
        ]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert score.completion_rate == 0.0
        assert score.avg_quality == 0.0

    def test_mixed_outcomes(self):
        evaluator = FitnessEvaluator()
        records = [
            make_task(task_id="t1", outcome=OutcomeType.COMPLETED),
            make_task(task_id="t2", outcome=OutcomeType.EXPIRED),
            make_task(task_id="t3", outcome=OutcomeType.COMPLETED),
        ]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert abs(score.completion_rate - 2 / 3) < 0.01

    def test_diversity_one_worker(self):
        evaluator = FitnessEvaluator()
        records = [make_task(task_id=f"t{i}", worker="w1") for i in range(10)]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert score.diversity == pytest.approx(1 / 10, abs=0.01)

    def test_diversity_many_workers(self):
        evaluator = FitnessEvaluator()
        records = [make_task(task_id=f"t{i}", worker=f"w{i}") for i in range(5)]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert score.diversity == 1.0  # 5 workers / 5 tasks

    def test_quality_average(self):
        evaluator = FitnessEvaluator()
        records = [
            make_task(task_id="t1", quality=0.6),
            make_task(task_id="t2", quality=0.8),
        ]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert abs(score.avg_quality - 0.7) < 0.01

    def test_speed_fast_tasks(self):
        evaluator = FitnessEvaluator()
        records = [make_task(task_id=f"t{i}", hours=0.1) for i in range(3)]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert score.avg_speed == 1.0  # Capped at 1.0 for very fast tasks

    def test_speed_slow_tasks(self):
        evaluator = FitnessEvaluator()
        records = [make_task(task_id=f"t{i}", hours=24.0) for i in range(3)]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert score.avg_speed < 0.1  # 1/24 ≈ 0.042

    def test_cost_efficiency_free_task(self):
        evaluator = FitnessEvaluator()
        records = [make_task(task_id="t1", bounty=0.0, quality=0.8)]
        score = evaluator.evaluate(RoutingWeights(), records)
        # quality_score counts as cost_efficiency when bounty is 0
        assert score.cost_efficiency > 0.0

    def test_custom_fitness_weights(self):
        evaluator = FitnessEvaluator(
            fitness_weights={
                "completion_rate": 1.0,
                "avg_quality": 0.0,
                "avg_speed": 0.0,
                "cost_efficiency": 0.0,
                "diversity": 0.0,
            }
        )
        records = [make_task(task_id=f"t{i}") for i in range(5)]
        score = evaluator.evaluate(RoutingWeights(), records)
        # Composite should equal completion_rate since only that weight is 1.0
        assert abs(score.composite - score.completion_rate) < 0.01


# ═══════════════════════════════════════════════════════════════
# RoutingOptimizer — Population Management
# ═══════════════════════════════════════════════════════════════


class TestOptimizerPopulation:
    def test_seed_population_default_size(self):
        opt = RoutingOptimizer(population_size=20)
        opt.seed_population()
        assert len(opt.population) == 20

    def test_seed_population_includes_base(self):
        base = RoutingWeights(0.5, 0.2, 0.1, 0.1, 0.1)
        opt = RoutingOptimizer(population_size=10)
        opt.seed_population(initial_weights=base)
        # First candidate should be the base weights
        assert opt.population[0].weights.skill_match == base.skill_match

    def test_seed_population_includes_extremes(self):
        opt = RoutingOptimizer(population_size=10)
        opt.seed_population()
        # Should include at least one skill-heavy config
        has_skill_heavy = any(c.weights.skill_match > 0.7 for c in opt.population)
        assert has_skill_heavy

    def test_initial_generation_is_zero(self):
        opt = RoutingOptimizer()
        opt.seed_population()
        assert opt.generation == 0
        for c in opt.population:
            assert c.generation == 0

    def test_best_is_none_before_eval(self):
        opt = RoutingOptimizer()
        opt.seed_population()
        assert opt.best is None


# ═══════════════════════════════════════════════════════════════
# RoutingOptimizer — Evaluation
# ═══════════════════════════════════════════════════════════════


class TestOptimizerEvaluation:
    def test_evaluate_sets_fitness(self):
        opt = RoutingOptimizer(population_size=5)
        opt.seed_population()
        records = make_completed_records(20)
        opt.evaluate_population(records)
        for c in opt.population:
            assert c.evaluations == 1
            # Fitness should be set
            assert c.fitness.composite >= 0.0

    def test_evaluate_tracks_best(self):
        opt = RoutingOptimizer(population_size=5)
        opt.seed_population()
        records = make_completed_records(20)
        opt.evaluate_population(records)
        assert opt.best is not None
        assert opt.best.fitness.composite > 0.0

    def test_evaluate_empty_records(self):
        opt = RoutingOptimizer(population_size=5)
        opt.seed_population()
        opt.evaluate_population([])
        # All fitness scores should be zero
        for c in opt.population:
            assert c.fitness.composite == 0.0


# ═══════════════════════════════════════════════════════════════
# RoutingOptimizer — Evolution
# ═══════════════════════════════════════════════════════════════


class TestOptimizerEvolution:
    def test_evolve_increments_generation(self):
        random.seed(42)
        opt = RoutingOptimizer(population_size=10)
        opt.seed_population()
        records = make_completed_records(20)
        opt.evolve(records)
        assert opt.generation == 1

    def test_evolve_preserves_population_size(self):
        random.seed(42)
        opt = RoutingOptimizer(population_size=10)
        opt.seed_population()
        records = make_completed_records(20)
        opt.evolve(records)
        assert len(opt.population) == 10

    def test_evolve_improves_over_generations(self):
        random.seed(42)
        opt = RoutingOptimizer(population_size=15, elite_count=3)
        opt.seed_population()
        records = make_completed_records(30)

        # Track fitness improvement
        opt.evaluate_population(records)
        gen0_best = opt.best.fitness.composite

        for _ in range(5):
            opt.evolve(records)

        gen5_best = opt.best.fitness.composite
        # Should improve or maintain (elite preserved)
        assert gen5_best >= gen0_best

    def test_elite_count_clamped(self):
        opt = RoutingOptimizer(population_size=5, elite_count=10)
        assert opt._elite_count == 5  # Clamped to population_size


# ═══════════════════════════════════════════════════════════════
# RoutingOptimizer — Full Optimization
# ═══════════════════════════════════════════════════════════════


class TestOptimizerFullRun:
    def test_optimize_returns_recommendation(self):
        random.seed(42)
        opt = RoutingOptimizer(population_size=10)
        records = make_completed_records(30)
        rec = opt.optimize(records, generations=5)
        assert isinstance(rec, RoutingRecommendation)
        assert rec.evaluation_count == 50  # 10 * 5
        assert rec.confidence > 0.0

    def test_optimize_records_history(self):
        random.seed(42)
        opt = RoutingOptimizer(population_size=10)
        records = make_completed_records(20)
        opt.optimize(records, generations=3)
        assert len(opt.history) == 1
        assert opt.history[0].generations == 3

    def test_optimize_with_custom_initial(self):
        random.seed(42)
        opt = RoutingOptimizer(population_size=10)
        records = make_completed_records(20)
        initial = RoutingWeights(0.5, 0.2, 0.1, 0.1, 0.1)
        rec = opt.optimize(records, generations=3, initial_weights=initial)
        assert rec.current.skill_match == initial.skill_match

    def test_optimize_reasoning_nonempty(self):
        random.seed(42)
        opt = RoutingOptimizer(population_size=10)
        records = make_completed_records(20)
        rec = opt.optimize(records, generations=3)
        assert len(rec.reasoning) > 0
        assert "Biggest change" in rec.reasoning


# ═══════════════════════════════════════════════════════════════
# RoutingRecommendation
# ═══════════════════════════════════════════════════════════════


class TestRoutingRecommendation:
    def test_should_apply_high_confidence_improvement(self):
        rec = RoutingRecommendation(
            current=RoutingWeights(),
            recommended=RoutingWeights(0.5, 0.2, 0.1, 0.1, 0.1),
            improvement=0.1,
            confidence=0.8,
        )
        assert rec.should_apply is True

    def test_should_not_apply_low_confidence(self):
        rec = RoutingRecommendation(
            current=RoutingWeights(),
            recommended=RoutingWeights(),
            improvement=0.1,
            confidence=0.5,
        )
        assert rec.should_apply is False

    def test_should_not_apply_small_improvement(self):
        rec = RoutingRecommendation(
            current=RoutingWeights(),
            recommended=RoutingWeights(),
            improvement=0.02,
            confidence=0.9,
        )
        assert rec.should_apply is False

    def test_should_not_apply_no_improvement(self):
        rec = RoutingRecommendation(
            current=RoutingWeights(),
            recommended=RoutingWeights(),
            improvement=0.0,
            confidence=1.0,
        )
        assert rec.should_apply is False


# ═══════════════════════════════════════════════════════════════
# Sensitivity & Category Analysis
# ═══════════════════════════════════════════════════════════════


class TestAnalysis:
    def test_sensitivity_returns_all_weights(self):
        opt = RoutingOptimizer(population_size=5)
        records = make_completed_records(15)
        result = opt.sensitivity_analysis(records, steps=3)
        assert "skill_match" in result
        assert "reputation" in result
        assert "capacity" in result
        assert "speed" in result
        assert "cost" in result

    def test_sensitivity_correct_steps(self):
        opt = RoutingOptimizer(population_size=5)
        records = make_completed_records(15)
        result = opt.sensitivity_analysis(records, steps=4)
        for name, curve in result.items():
            assert len(curve) == 5  # steps + 1

    def test_sensitivity_values_bounded(self):
        opt = RoutingOptimizer(population_size=5)
        records = make_completed_records(15)
        result = opt.sensitivity_analysis(records, steps=5)
        for name, curve in result.items():
            for val, fitness in curve:
                assert 0.0 <= val <= 1.0
                assert fitness >= 0.0

    def test_category_analysis(self):
        opt = RoutingOptimizer(population_size=5)
        opt.seed_population()
        records = make_completed_records(15)
        opt.evaluate_population(records)
        result = opt.category_analysis(records)
        assert "physical_verification" in result
        assert "data_collection" in result
        assert isinstance(result["physical_verification"], FitnessScore)


# ═══════════════════════════════════════════════════════════════
# Serialization
# ═══════════════════════════════════════════════════════════════


class TestSerialization:
    def test_to_dict(self):
        random.seed(42)
        opt = RoutingOptimizer(population_size=5)
        records = make_completed_records(10)
        opt.optimize(records, generations=2)
        d = opt.to_dict()
        assert "generation" in d
        assert "best_ever" in d
        assert "history" in d
        assert d["best_ever"] is not None
        assert len(d["history"]) == 1

    def test_to_dict_before_optimization(self):
        opt = RoutingOptimizer()
        d = opt.to_dict()
        assert d["best_ever"] is None
        assert len(d["history"]) == 0

    def test_save(self, tmp_path):
        random.seed(42)
        opt = RoutingOptimizer(population_size=5)
        records = make_completed_records(10)
        opt.optimize(records, generations=2)
        path = tmp_path / "optimizer.json"
        opt.save(path)
        assert path.exists()
        import json

        data = json.loads(path.read_text())
        assert "best_ever" in data

    def test_stats(self):
        random.seed(42)
        opt = RoutingOptimizer(population_size=5)
        records = make_completed_records(10)
        opt.optimize(records, generations=2)
        stats = opt.stats()
        assert stats["optimization_runs"] == 1
        assert stats["best_fitness"] > 0.0
        assert stats["best_weights"] is not None


# ═══════════════════════════════════════════════════════════════
# ConfigCandidate
# ═══════════════════════════════════════════════════════════════


class TestConfigCandidate:
    def test_label_format(self):
        c = ConfigCandidate(weights=RoutingWeights(0.35, 0.25, 0.15, 0.15, 0.10))
        label = c.label
        assert "S35%" in label
        assert "R25%" in label

    def test_default_fitness(self):
        c = ConfigCandidate(weights=RoutingWeights())
        assert c.fitness.composite == 0.0
        assert c.evaluations == 0


# ═══════════════════════════════════════════════════════════════
# OptimizationRun
# ═══════════════════════════════════════════════════════════════


class TestOptimizationRun:
    def test_defaults(self):
        run = OptimizationRun()
        assert run.candidates_evaluated == 0
        assert run.generations == 0
        assert run.improvement == 0.0

    def test_with_data(self):
        run = OptimizationRun(
            candidates_evaluated=100,
            generations=10,
            best_fitness=0.85,
            baseline_fitness=0.70,
            improvement=0.15,
        )
        assert run.improvement == 0.15
        assert run.best_fitness == 0.85
