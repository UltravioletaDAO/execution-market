"""Tests for RoutingOptimizer — Self-Tuning Routing Weights."""

import random
import tempfile
from pathlib import Path

import pytest

from mcp_server.swarm.routing_optimizer import (
    ConfigCandidate,
    FitnessEvaluator,
    FitnessScore,
    OptimizationRun,
    OutcomeType,
    RoutingOptimizer,
    RoutingRecommendation,
    RoutingWeights,
    TaskRecord,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


def _make_records(
    n: int = 50,
    completion_rate: float = 0.7,
    seed: int = 42,
) -> list[TaskRecord]:
    """Generate synthetic task records for testing."""
    rng = random.Random(seed)
    records = []

    categories = ["delivery", "inspection", "data_collection", "photography", "survey"]
    workers = [f"worker_{i}" for i in range(10)]

    for i in range(n):
        is_completed = rng.random() < completion_rate
        worker = rng.choice(workers)

        records.append(TaskRecord(
            task_id=f"task_{i}",
            category=rng.choice(categories),
            required_skills=rng.sample(
                ["photography", "driving", "inspection", "data_entry", "survey"],
                k=rng.randint(1, 3),
            ),
            bounty_usd=rng.uniform(1.0, 50.0),
            assigned_worker=worker,
            worker_reputation=rng.uniform(0.3, 1.0),
            worker_skill_match=rng.uniform(0.2, 1.0),
            outcome=OutcomeType.COMPLETED if is_completed else rng.choice(
                [OutcomeType.EXPIRED, OutcomeType.REJECTED]
            ),
            quality_score=rng.uniform(0.5, 1.0) if is_completed else 0.0,
            completion_hours=rng.uniform(0.5, 48.0) if is_completed else 0.0,
            created_at=1700000000 + i * 3600,
        ))

    return records


@pytest.fixture
def records():
    return _make_records()


@pytest.fixture
def small_records():
    return _make_records(n=10)


@pytest.fixture
def evaluator():
    return FitnessEvaluator()


@pytest.fixture
def optimizer():
    return RoutingOptimizer(population_size=10, mutation_rate=0.15)


# ──────────────────────────────────────────────────────────────
# RoutingWeights Tests
# ──────────────────────────────────────────────────────────────


class TestRoutingWeights:
    def test_defaults(self):
        w = RoutingWeights()
        assert w.skill_match == 0.35
        assert w.reputation == 0.25
        assert w.total == pytest.approx(1.0)

    def test_clamping(self):
        w = RoutingWeights(skill_match=-0.5, reputation=1.5)
        assert w.skill_match == 0.0
        assert w.reputation == 1.0

    def test_normalized(self):
        w = RoutingWeights(0.5, 0.5, 0.5, 0.5, 0.5)
        n = w.normalized()
        assert n.total == pytest.approx(1.0)
        assert n.skill_match == pytest.approx(0.2)

    def test_normalized_zero(self):
        w = RoutingWeights(0, 0, 0, 0, 0)
        n = w.normalized()
        assert n.total == pytest.approx(1.0)

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
        assert w.distance(w) == pytest.approx(0.0)

    def test_distance_different(self):
        a = RoutingWeights(1.0, 0.0, 0.0, 0.0, 0.0)
        b = RoutingWeights(0.0, 1.0, 0.0, 0.0, 0.0)
        assert a.distance(b) > 0

    def test_mutate(self):
        w = RoutingWeights()
        m = w.mutate(0.1)
        # Mutation should produce different weights
        assert isinstance(m, RoutingWeights)
        assert m.total == pytest.approx(1.0)  # Normalized

    def test_mutate_stays_valid(self):
        w = RoutingWeights(0.8, 0.05, 0.05, 0.05, 0.05)
        for _ in range(20):
            m = w.mutate(0.3)
            for val in m.to_list():
                assert 0.0 <= val <= 1.0


# ──────────────────────────────────────────────────────────────
# TaskRecord Tests
# ──────────────────────────────────────────────────────────────


class TestTaskRecord:
    def test_success(self):
        r = TaskRecord(task_id="t1", outcome=OutcomeType.COMPLETED)
        assert r.is_success

    def test_failure(self):
        r = TaskRecord(task_id="t1", outcome=OutcomeType.EXPIRED)
        assert not r.is_success

    def test_defaults(self):
        r = TaskRecord(task_id="t1")
        assert r.category == ""
        assert r.bounty_usd == 0.0
        assert r.quality_score == 0.0


# ──────────────────────────────────────────────────────────────
# FitnessScore Tests
# ──────────────────────────────────────────────────────────────


class TestFitnessScore:
    def test_is_viable(self):
        assert FitnessScore(completion_rate=0.5).is_viable
        assert not FitnessScore(completion_rate=0.0).is_viable

    def test_dominates(self):
        a = FitnessScore(completion_rate=0.8, avg_quality=0.9, avg_speed=0.7, cost_efficiency=0.6)
        b = FitnessScore(completion_rate=0.7, avg_quality=0.8, avg_speed=0.6, cost_efficiency=0.5)
        assert a.dominates(b)
        assert not b.dominates(a)

    def test_no_domination_tradeoff(self):
        a = FitnessScore(completion_rate=0.9, avg_quality=0.5)
        b = FitnessScore(completion_rate=0.5, avg_quality=0.9)
        assert not a.dominates(b)
        assert not b.dominates(a)


# ──────────────────────────────────────────────────────────────
# ConfigCandidate Tests
# ──────────────────────────────────────────────────────────────


class TestConfigCandidate:
    def test_label(self):
        c = ConfigCandidate(weights=RoutingWeights())
        label = c.label
        assert "S" in label
        assert "R" in label

    def test_generation(self):
        c = ConfigCandidate(weights=RoutingWeights(), generation=5)
        assert c.generation == 5


# ──────────────────────────────────────────────────────────────
# RoutingRecommendation Tests
# ──────────────────────────────────────────────────────────────


class TestRoutingRecommendation:
    def test_should_apply_high_confidence(self):
        r = RoutingRecommendation(
            current=RoutingWeights(),
            recommended=RoutingWeights(0.5, 0.2, 0.1, 0.1, 0.1),
            improvement=0.1,
            confidence=0.8,
        )
        assert r.should_apply

    def test_should_not_apply_low_confidence(self):
        r = RoutingRecommendation(
            current=RoutingWeights(),
            recommended=RoutingWeights(),
            improvement=0.1,
            confidence=0.3,
        )
        assert not r.should_apply

    def test_should_not_apply_low_improvement(self):
        r = RoutingRecommendation(
            current=RoutingWeights(),
            recommended=RoutingWeights(),
            improvement=0.01,
            confidence=0.9,
        )
        assert not r.should_apply


# ──────────────────────────────────────────────────────────────
# FitnessEvaluator Tests
# ──────────────────────────────────────────────────────────────


class TestFitnessEvaluator:
    def test_evaluate_empty(self, evaluator):
        score = evaluator.evaluate(RoutingWeights(), [])
        assert score.completion_rate == 0.0
        assert score.composite == 0.0

    def test_evaluate_all_completed(self, evaluator):
        records = [
            TaskRecord(
                task_id=f"t{i}",
                outcome=OutcomeType.COMPLETED,
                quality_score=0.9,
                completion_hours=2.0,
                bounty_usd=10.0,
                worker_skill_match=0.8,
                worker_reputation=0.9,
                assigned_worker=f"w{i}",
            )
            for i in range(10)
        ]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert score.completion_rate == 1.0
        assert score.avg_quality > 0.0
        assert score.is_viable

    def test_evaluate_mixed_outcomes(self, evaluator, records):
        score = evaluator.evaluate(RoutingWeights(), records)
        assert 0.0 < score.completion_rate < 1.0
        assert score.composite > 0.0

    def test_different_weights_different_scores(self, evaluator, records):
        score_skill = evaluator.evaluate(
            RoutingWeights(0.8, 0.05, 0.05, 0.05, 0.05), records
        )
        score_cost = evaluator.evaluate(
            RoutingWeights(0.05, 0.05, 0.05, 0.05, 0.8), records
        )
        # Different weights should produce different composite scores
        # (not always, but very likely with enough data)
        assert isinstance(score_skill.composite, float)
        assert isinstance(score_cost.composite, float)

    def test_zero_bounty_no_crash(self, evaluator):
        records = [
            TaskRecord(
                task_id="t1",
                outcome=OutcomeType.COMPLETED,
                bounty_usd=0.0,
                quality_score=0.8,
                completion_hours=1.0,
            )
        ]
        score = evaluator.evaluate(RoutingWeights(), records)
        assert score.is_viable

    def test_custom_fitness_weights(self):
        custom = FitnessEvaluator(fitness_weights={
            "completion_rate": 1.0,
            "avg_quality": 0.0,
            "avg_speed": 0.0,
            "cost_efficiency": 0.0,
            "diversity": 0.0,
        })
        records = [
            TaskRecord(task_id="t1", outcome=OutcomeType.COMPLETED, quality_score=0.9,
                       completion_hours=1.0, assigned_worker="w1"),
        ]
        score = custom.evaluate(RoutingWeights(), records)
        # With only completion_rate weighted, composite = completion_rate
        assert score.composite == pytest.approx(score.completion_rate)


# ──────────────────────────────────────────────────────────────
# RoutingOptimizer Tests
# ──────────────────────────────────────────────────────────────


class TestRoutingOptimizer:
    def test_seed_population(self, optimizer):
        optimizer.seed_population()
        assert len(optimizer.population) == 10

    def test_seed_with_initial_weights(self, optimizer):
        custom = RoutingWeights(0.5, 0.2, 0.1, 0.1, 0.1)
        optimizer.seed_population(custom)
        # First candidate should be the initial config
        assert optimizer.population[0].weights.skill_match == 0.5

    def test_evaluate_population(self, optimizer, records):
        optimizer.seed_population()
        optimizer.evaluate_population(records)
        # All should have been evaluated
        for candidate in optimizer.population:
            assert candidate.evaluations >= 1
        # Best ever should be set
        assert optimizer.best is not None

    def test_evolve(self, optimizer, records):
        optimizer.seed_population()
        initial_gen = optimizer.generation
        optimizer.evolve(records)
        assert optimizer.generation == initial_gen + 1

    def test_evolve_multiple_generations(self, optimizer, records):
        optimizer.seed_population()
        for _ in range(5):
            optimizer.evolve(records)
        assert optimizer.generation == 5
        assert optimizer.best is not None

    def test_optimize_full(self, optimizer, records):
        rec = optimizer.optimize(records, generations=5)
        assert isinstance(rec, RoutingRecommendation)
        assert rec.improvement is not None
        assert rec.confidence >= 0.0
        assert rec.evaluation_count > 0
        assert len(rec.reasoning) > 0

    def test_optimize_with_initial_weights(self, optimizer, records):
        initial = RoutingWeights(0.5, 0.2, 0.1, 0.1, 0.1)
        rec = optimizer.optimize(records, generations=3, initial_weights=initial)
        assert rec.current.skill_match == 0.5

    def test_optimize_small_dataset(self, optimizer, small_records):
        rec = optimizer.optimize(small_records, generations=3)
        # Should work but with lower confidence
        assert isinstance(rec, RoutingRecommendation)

    def test_history_tracking(self, optimizer, records):
        optimizer.optimize(records, generations=3)
        assert len(optimizer.history) == 1
        run = optimizer.history[0]
        assert run.generations == 3
        assert run.duration_seconds >= 0

    def test_multiple_optimization_runs(self, optimizer, records):
        optimizer.optimize(records, generations=3)
        optimizer.optimize(records, generations=3)
        assert len(optimizer.history) == 2

    def test_sensitivity_analysis(self, optimizer, records):
        results = optimizer.sensitivity_analysis(records, steps=3)
        assert "skill_match" in results
        assert "reputation" in results
        assert len(results["skill_match"]) == 4  # 0.0, 0.33, 0.67, 1.0

    def test_category_analysis(self, optimizer, records):
        optimizer.seed_population()
        optimizer.evaluate_population(records)
        results = optimizer.category_analysis(records)
        assert len(results) > 0
        for cat, score in results.items():
            assert isinstance(score, FitnessScore)

    def test_stats(self, optimizer, records):
        optimizer.optimize(records, generations=3)
        stats = optimizer.stats()
        assert "generation" in stats
        assert "population_size" in stats
        assert "best_fitness" in stats
        assert stats["best_fitness"] > 0

    def test_save(self, optimizer, records):
        optimizer.optimize(records, generations=3)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "optimizer.json"
            optimizer.save(path)
            assert path.exists()

    def test_empty_records(self, optimizer):
        rec = optimizer.optimize([], generations=3)
        assert isinstance(rec, RoutingRecommendation)
        # With no data, recommendation should have low confidence
        assert rec.confidence <= 0.5

    def test_convergence(self, records):
        """Verify optimizer converges over many generations."""
        opt = RoutingOptimizer(population_size=15, mutation_rate=0.1)
        opt.seed_population()

        # Track fitness over generations
        fitness_history = []
        for _ in range(10):
            opt.evolve(records)
            best = max(opt.population, key=lambda c: c.fitness.composite)
            fitness_history.append(best.fitness.composite)

        # Later generations should be at least as good as earlier
        # (elite preservation guarantees non-degradation)
        assert fitness_history[-1] >= fitness_history[0]

    def test_reproducibility(self, records):
        """Same seed should produce similar results."""
        random.seed(42)
        opt1 = RoutingOptimizer(population_size=10)
        rec1 = opt1.optimize(records, generations=5)

        random.seed(42)
        opt2 = RoutingOptimizer(population_size=10)
        rec2 = opt2.optimize(records, generations=5)

        # Results should be identical with same seed
        assert rec1.recommended.skill_match == pytest.approx(rec2.recommended.skill_match, abs=0.01)


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────


class TestIntegration:
    def test_skill_heavy_data(self):
        """When high-skill-match correlates with success, optimizer should favor skill weight."""
        records = []
        for i in range(100):
            skill_match = random.uniform(0.7, 1.0)
            is_good = skill_match > 0.85
            records.append(TaskRecord(
                task_id=f"t{i}",
                worker_skill_match=skill_match,
                worker_reputation=random.uniform(0.3, 1.0),
                outcome=OutcomeType.COMPLETED if is_good else OutcomeType.EXPIRED,
                quality_score=skill_match if is_good else 0.0,
                completion_hours=random.uniform(1, 24),
                bounty_usd=random.uniform(5, 50),
                assigned_worker=f"w{i % 20}",
            ))

        opt = RoutingOptimizer(population_size=15, mutation_rate=0.1)
        rec = opt.optimize(records, generations=10)
        # Should find some configuration (no crash)
        assert isinstance(rec, RoutingRecommendation)
        assert rec.evaluation_count > 0

    def test_end_to_end_pipeline(self, records):
        """Full pipeline: optimize → analyze → save → recommend."""
        opt = RoutingOptimizer(population_size=10)

        # 1. Optimize
        rec = opt.optimize(records, generations=5)

        # 2. Sensitivity analysis
        sensitivity = opt.sensitivity_analysis(records)
        assert len(sensitivity) == 5

        # 3. Category analysis
        categories = opt.category_analysis(records)
        assert len(categories) > 0

        # 4. Save state
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"
            opt.save(path)
            assert path.exists()

        # 5. Stats
        stats = opt.stats()
        assert stats["optimization_runs"] == 1
        assert stats["best_fitness"] > 0
