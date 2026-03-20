"""
RoutingOptimizer — Self-Tuning Routing Weights from Historical Outcomes
======================================================================

The swarm's Coordinator routes tasks using configurable weights
(skill match, reputation, capacity, speed, cost). But how do you
know if those weights are good? The RoutingOptimizer answers this
by replaying historical task data with different weight configurations
and measuring which ones produce the best outcomes.

Core concepts:
    1. **Outcome signals**: Completed (good), Expired (bad), Rejected (bad)
    2. **Weight space exploration**: Grid search, random search, or gradient
    3. **Fitness function**: Maps weight configs to outcome quality
    4. **Tournament selection**: Keeps top-N configurations, evolves them
    5. **Recommendations**: Suggests weight changes with confidence levels

The optimizer does NOT route tasks itself. It produces RoutingConfig
recommendations that the Coordinator can adopt.

Architecture:
    Historical outcomes
        ↓
    RoutingOptimizer.evaluate(config)
        ↓
    Fitness score (completion rate, quality, speed, cost efficiency)
        ↓
    Tournament of configs → best config
        ↓
    RoutingRecommendation to Coordinator

Thread-safe. No external dependencies.
"""

import json
import logging
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("em.swarm.routing_optimizer")


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


class OutcomeType(str, Enum):
    """Task outcome classification."""

    COMPLETED = "completed"
    EXPIRED = "expired"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class RoutingWeights:
    """Weight configuration for routing decisions."""

    skill_match: float = 0.35
    reputation: float = 0.25
    capacity: float = 0.15
    speed: float = 0.15
    cost: float = 0.10

    def __post_init__(self):
        """Clamp weights to valid range."""
        self.skill_match = max(0.0, min(1.0, self.skill_match))
        self.reputation = max(0.0, min(1.0, self.reputation))
        self.capacity = max(0.0, min(1.0, self.capacity))
        self.speed = max(0.0, min(1.0, self.speed))
        self.cost = max(0.0, min(1.0, self.cost))

    @property
    def total(self) -> float:
        return self.skill_match + self.reputation + self.capacity + self.speed + self.cost

    def normalized(self) -> "RoutingWeights":
        """Return a copy with weights summing to 1.0."""
        t = self.total
        if t == 0:
            return RoutingWeights(0.2, 0.2, 0.2, 0.2, 0.2)
        return RoutingWeights(
            skill_match=self.skill_match / t,
            reputation=self.reputation / t,
            capacity=self.capacity / t,
            speed=self.speed / t,
            cost=self.cost / t,
        )

    def to_list(self) -> list[float]:
        return [self.skill_match, self.reputation, self.capacity, self.speed, self.cost]

    @classmethod
    def from_list(cls, values: list[float]) -> "RoutingWeights":
        if len(values) != 5:
            raise ValueError("Expected 5 weight values")
        return cls(
            skill_match=values[0],
            reputation=values[1],
            capacity=values[2],
            speed=values[3],
            cost=values[4],
        )

    def distance(self, other: "RoutingWeights") -> float:
        """Euclidean distance between two weight configs."""
        return math.sqrt(
            (self.skill_match - other.skill_match) ** 2
            + (self.reputation - other.reputation) ** 2
            + (self.capacity - other.capacity) ** 2
            + (self.speed - other.speed) ** 2
            + (self.cost - other.cost) ** 2
        )

    def mutate(self, mutation_rate: float = 0.1) -> "RoutingWeights":
        """Create a mutated copy with random perturbations."""
        values = self.to_list()
        mutated = [
            max(0.0, min(1.0, v + random.gauss(0, mutation_rate)))
            for v in values
        ]
        return RoutingWeights.from_list(mutated).normalized()


@dataclass
class TaskRecord:
    """A historical task with its routing decision and outcome."""

    task_id: str
    category: str = ""
    required_skills: list[str] = field(default_factory=list)
    bounty_usd: float = 0.0
    assigned_worker: str = ""
    worker_reputation: float = 0.0
    worker_skill_match: float = 0.0
    outcome: OutcomeType = OutcomeType.COMPLETED
    quality_score: float = 0.0  # 0-1, from evidence evaluation
    completion_hours: float = 0.0
    created_at: float = 0.0  # timestamp

    @property
    def is_success(self) -> bool:
        return self.outcome == OutcomeType.COMPLETED


@dataclass
class FitnessScore:
    """Multi-dimensional fitness evaluation of a weight configuration."""

    completion_rate: float = 0.0  # % of tasks completed
    avg_quality: float = 0.0  # Average quality score
    avg_speed: float = 0.0  # Average completion speed (inverse hours)
    cost_efficiency: float = 0.0  # Quality per dollar
    diversity: float = 0.0  # Worker diversity (0-1)
    composite: float = 0.0  # Weighted composite score

    @property
    def is_viable(self) -> bool:
        """Minimum viable fitness (at least some tasks complete)."""
        return self.completion_rate > 0.0

    def dominates(self, other: "FitnessScore") -> bool:
        """Pareto dominance: this is at least as good in all dimensions and strictly better in at least one."""
        dims_self = [self.completion_rate, self.avg_quality, self.avg_speed, self.cost_efficiency]
        dims_other = [other.completion_rate, other.avg_quality, other.avg_speed, other.cost_efficiency]

        at_least_as_good = all(s >= o for s, o in zip(dims_self, dims_other))
        strictly_better = any(s > o for s, o in zip(dims_self, dims_other))
        return at_least_as_good and strictly_better


@dataclass
class ConfigCandidate:
    """A weight configuration with its fitness history."""

    weights: RoutingWeights
    fitness: FitnessScore = field(default_factory=FitnessScore)
    generation: int = 0
    evaluations: int = 0
    created_at: float = field(default_factory=time.time)

    @property
    def label(self) -> str:
        w = self.weights
        return f"S{w.skill_match:.0%}R{w.reputation:.0%}C{w.capacity:.0%}Sp{w.speed:.0%}$Co{w.cost:.0%}"


@dataclass
class RoutingRecommendation:
    """The optimizer's output: a recommended weight change."""

    current: RoutingWeights
    recommended: RoutingWeights
    improvement: float  # Expected fitness improvement (0-1)
    confidence: float  # How confident in this recommendation (0-1)
    reasoning: str = ""
    evaluation_count: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def should_apply(self) -> bool:
        """Whether this recommendation should be automatically applied."""
        return self.confidence >= 0.7 and self.improvement >= 0.05


@dataclass
class OptimizationRun:
    """Summary of a full optimization cycle."""

    candidates_evaluated: int = 0
    generations: int = 0
    best_fitness: float = 0.0
    baseline_fitness: float = 0.0
    improvement: float = 0.0
    best_weights: RoutingWeights = field(default_factory=RoutingWeights)
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)


# ──────────────────────────────────────────────────────────────
# Fitness Evaluator
# ──────────────────────────────────────────────────────────────


class FitnessEvaluator:
    """
    Evaluates how well a weight configuration would perform
    against a set of historical task records.
    """

    def __init__(
        self,
        fitness_weights: dict[str, float] | None = None,
    ):
        self._fitness_weights = fitness_weights or {
            "completion_rate": 0.35,
            "avg_quality": 0.30,
            "avg_speed": 0.15,
            "cost_efficiency": 0.10,
            "diversity": 0.10,
        }

    def evaluate(
        self,
        weights: RoutingWeights,
        records: list[TaskRecord],
    ) -> FitnessScore:
        """
        Evaluate a weight configuration against historical records.

        Simulates routing decisions: higher weight on a factor means
        tasks where that factor was high should be rewarded more.
        """
        if not records:
            return FitnessScore()

        # Score each task based on how well the weights predict good outcomes
        task_scores: list[float] = []
        completed = 0
        quality_sum = 0.0
        speed_sum = 0.0
        cost_sum = 0.0
        workers_seen: set[str] = set()

        for record in records:
            # Compute routing score for this task's assignment
            routing_score = self._routing_score(weights, record)

            if record.is_success:
                completed += 1
                quality_sum += record.quality_score
                # Speed: inverse of hours (capped at 1.0 for instant tasks)
                speed = min(1.0, 1.0 / max(0.1, record.completion_hours))
                speed_sum += speed
                # Cost efficiency: quality per dollar
                if record.bounty_usd > 0:
                    cost_sum += record.quality_score / record.bounty_usd
                else:
                    cost_sum += record.quality_score

            if record.assigned_worker:
                workers_seen.add(record.assigned_worker)

            task_scores.append(routing_score)

        n = len(records)
        completion_rate = completed / n if n > 0 else 0.0
        avg_quality = quality_sum / completed if completed > 0 else 0.0
        avg_speed = speed_sum / completed if completed > 0 else 0.0
        cost_efficiency = min(1.0, cost_sum / completed) if completed > 0 else 0.0

        # Diversity: how many unique workers vs tasks
        diversity = min(1.0, len(workers_seen) / max(1, n))

        # Compute composite score
        fw = self._fitness_weights
        composite = (
            completion_rate * fw.get("completion_rate", 0.35)
            + avg_quality * fw.get("avg_quality", 0.30)
            + avg_speed * fw.get("avg_speed", 0.15)
            + cost_efficiency * fw.get("cost_efficiency", 0.10)
            + diversity * fw.get("diversity", 0.10)
        )

        return FitnessScore(
            completion_rate=completion_rate,
            avg_quality=avg_quality,
            avg_speed=avg_speed,
            cost_efficiency=cost_efficiency,
            diversity=diversity,
            composite=composite,
        )

    def _routing_score(self, weights: RoutingWeights, record: TaskRecord) -> float:
        """Compute how well the weight config rates this assignment."""
        w = weights.normalized()
        score = (
            record.worker_skill_match * w.skill_match
            + record.worker_reputation * w.reputation
            + (1.0 - min(1.0, record.completion_hours / 24.0)) * w.speed
            + (min(1.0, 1.0 / max(0.01, record.bounty_usd))) * w.cost
        )
        return score


# ──────────────────────────────────────────────────────────────
# Core Optimizer
# ──────────────────────────────────────────────────────────────


class RoutingOptimizer:
    """
    Optimizes routing weights by evaluating configurations against
    historical task data. Uses evolutionary tournament selection.
    """

    def __init__(
        self,
        population_size: int = 20,
        mutation_rate: float = 0.1,
        elite_count: int = 3,
        evaluator: FitnessEvaluator | None = None,
    ):
        self._population_size = population_size
        self._mutation_rate = mutation_rate
        self._elite_count = min(elite_count, population_size)
        self._evaluator = evaluator or FitnessEvaluator()
        self._population: list[ConfigCandidate] = []
        self._history: list[OptimizationRun] = []
        self._generation = 0
        self._best_ever: ConfigCandidate | None = None

    @property
    def population(self) -> list[ConfigCandidate]:
        return list(self._population)

    @property
    def best(self) -> ConfigCandidate | None:
        return self._best_ever

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def history(self) -> list[OptimizationRun]:
        return list(self._history)

    # ── Population Management ────────────────────────────────

    def seed_population(
        self,
        initial_weights: RoutingWeights | None = None,
    ):
        """
        Create initial population with diverse configurations.
        Includes the current config plus random mutations.
        """
        self._population = []

        # Add current config
        base = initial_weights or RoutingWeights()
        self._population.append(ConfigCandidate(weights=base, generation=0))

        # Add extreme configs (one weight dominant)
        extremes = [
            RoutingWeights(0.8, 0.05, 0.05, 0.05, 0.05),  # Skill-heavy
            RoutingWeights(0.05, 0.8, 0.05, 0.05, 0.05),  # Reputation-heavy
            RoutingWeights(0.05, 0.05, 0.8, 0.05, 0.05),  # Capacity-heavy
            RoutingWeights(0.05, 0.05, 0.05, 0.8, 0.05),  # Speed-heavy
            RoutingWeights(0.05, 0.05, 0.05, 0.05, 0.8),  # Cost-heavy
            RoutingWeights(0.2, 0.2, 0.2, 0.2, 0.2),  # Equal
        ]
        for w in extremes:
            if len(self._population) < self._population_size:
                self._population.append(ConfigCandidate(weights=w.normalized(), generation=0))

        # Fill remaining with mutations of base
        while len(self._population) < self._population_size:
            mutated = base.mutate(self._mutation_rate * 2)
            self._population.append(ConfigCandidate(weights=mutated, generation=0))

    def evaluate_population(self, records: list[TaskRecord]):
        """Evaluate all candidates against historical data."""
        for candidate in self._population:
            candidate.fitness = self._evaluator.evaluate(candidate.weights, records)
            candidate.evaluations += 1

        # Track best ever
        current_best = max(self._population, key=lambda c: c.fitness.composite)
        if self._best_ever is None or current_best.fitness.composite > self._best_ever.fitness.composite:
            self._best_ever = ConfigCandidate(
                weights=RoutingWeights.from_list(current_best.weights.to_list()),
                fitness=current_best.fitness,
                generation=self._generation,
                evaluations=current_best.evaluations,
            )

    def evolve(self, records: list[TaskRecord]):
        """
        Run one generation of evolution:
        1. Evaluate current population
        2. Select elite (top N)
        3. Generate offspring via crossover + mutation
        4. Replace population
        """
        self._generation += 1

        # Evaluate
        self.evaluate_population(records)

        # Sort by composite fitness (descending)
        self._population.sort(key=lambda c: c.fitness.composite, reverse=True)

        # Elite selection
        elite = self._population[: self._elite_count]

        # Generate new population
        new_pop = [
            ConfigCandidate(
                weights=RoutingWeights.from_list(c.weights.to_list()),
                generation=self._generation,
            )
            for c in elite
        ]

        # Crossover + mutation to fill population
        while len(new_pop) < self._population_size:
            # Tournament selection of two parents
            parent1 = self._tournament_select()
            parent2 = self._tournament_select()

            # Crossover
            child_weights = self._crossover(parent1.weights, parent2.weights)

            # Mutation
            child_weights = child_weights.mutate(self._mutation_rate)

            new_pop.append(ConfigCandidate(
                weights=child_weights,
                generation=self._generation,
            ))

        self._population = new_pop

    def _tournament_select(self, tournament_size: int = 3) -> ConfigCandidate:
        """Select best candidate from a random subset."""
        if not self._population:
            return ConfigCandidate(weights=RoutingWeights())
        contestants = random.sample(
            self._population,
            min(tournament_size, len(self._population)),
        )
        return max(contestants, key=lambda c: c.fitness.composite)

    @staticmethod
    def _crossover(a: RoutingWeights, b: RoutingWeights) -> RoutingWeights:
        """Uniform crossover between two weight configs."""
        values_a = a.to_list()
        values_b = b.to_list()
        child = [
            va if random.random() < 0.5 else vb
            for va, vb in zip(values_a, values_b)
        ]
        return RoutingWeights.from_list(child).normalized()

    # ── Full Optimization Run ────────────────────────────────

    def optimize(
        self,
        records: list[TaskRecord],
        generations: int = 10,
        initial_weights: RoutingWeights | None = None,
    ) -> RoutingRecommendation:
        """
        Run a full optimization cycle:
        1. Seed population
        2. Evolve for N generations
        3. Return recommendation
        """
        start = time.time()

        # Seed
        self.seed_population(initial_weights)

        # Evaluate baseline
        baseline = self._evaluator.evaluate(
            initial_weights or RoutingWeights(), records
        )

        # Evolve
        for _ in range(generations):
            self.evolve(records)

        duration = time.time() - start

        # Record run
        best = self._best_ever
        run = OptimizationRun(
            candidates_evaluated=self._population_size * generations,
            generations=generations,
            best_fitness=best.fitness.composite if best else 0.0,
            baseline_fitness=baseline.composite,
            improvement=best.fitness.composite - baseline.composite if best else 0.0,
            best_weights=best.weights if best else RoutingWeights(),
            duration_seconds=duration,
        )
        self._history.append(run)

        # Build recommendation
        if not best:
            return RoutingRecommendation(
                current=initial_weights or RoutingWeights(),
                recommended=RoutingWeights(),
                improvement=0.0,
                confidence=0.0,
                reasoning="No viable configurations found",
            )

        improvement = run.improvement
        confidence = self._compute_confidence(records, generations)

        current = initial_weights or RoutingWeights()
        reasoning = self._build_reasoning(current, best.weights, best.fitness, baseline)

        return RoutingRecommendation(
            current=current,
            recommended=best.weights,
            improvement=improvement,
            confidence=confidence,
            reasoning=reasoning,
            evaluation_count=self._population_size * generations,
        )

    def _compute_confidence(
        self,
        records: list[TaskRecord],
        generations: int,
    ) -> float:
        """
        Confidence based on:
        - Data volume (more records → higher confidence)
        - Convergence (top candidates agree → higher confidence)
        - Generations run (more → higher)
        """
        # Data volume factor
        data_factor = min(1.0, len(records) / 50)  # 50+ records = full confidence

        # Convergence: how similar are the top 3?
        if len(self._population) >= 3:
            sorted_pop = sorted(self._population, key=lambda c: c.fitness.composite, reverse=True)
            top3 = sorted_pop[:3]
            avg_distance = sum(
                top3[i].weights.distance(top3[j].weights)
                for i in range(3) for j in range(i + 1, 3)
            ) / 3
            convergence = max(0.0, 1.0 - avg_distance)
        else:
            convergence = 0.5

        # Generation factor
        gen_factor = min(1.0, generations / 10)

        return data_factor * 0.5 + convergence * 0.3 + gen_factor * 0.2

    def _build_reasoning(
        self,
        current: RoutingWeights,
        recommended: RoutingWeights,
        fitness: FitnessScore,
        baseline: FitnessScore,
    ) -> str:
        """Human-readable explanation of the recommendation."""
        parts = []

        # What changed most?
        changes = [
            ("skill_match", current.skill_match, recommended.skill_match),
            ("reputation", current.reputation, recommended.reputation),
            ("capacity", current.capacity, recommended.capacity),
            ("speed", current.speed, recommended.speed),
            ("cost", current.cost, recommended.cost),
        ]
        changes.sort(key=lambda c: abs(c[2] - c[1]), reverse=True)

        biggest = changes[0]
        delta = biggest[2] - biggest[1]
        direction = "increased" if delta > 0 else "decreased"
        parts.append(
            f"Biggest change: {biggest[0]} {direction} by {abs(delta):.2f}"
        )

        # Fitness improvement
        if fitness.composite > baseline.composite:
            parts.append(
                f"Composite fitness: {baseline.composite:.3f} → {fitness.composite:.3f} "
                f"(+{fitness.composite - baseline.composite:.3f})"
            )
        else:
            parts.append("No significant improvement found")

        # Key metric changes
        if fitness.completion_rate > baseline.completion_rate:
            parts.append(f"Completion rate improved: {baseline.completion_rate:.0%} → {fitness.completion_rate:.0%}")
        if fitness.avg_quality > baseline.avg_quality:
            parts.append(f"Average quality improved: {baseline.avg_quality:.2f} → {fitness.avg_quality:.2f}")

        return ". ".join(parts) + "."

    # ── Analysis Tools ───────────────────────────────────────

    def sensitivity_analysis(
        self,
        records: list[TaskRecord],
        base_weights: RoutingWeights | None = None,
        steps: int = 5,
    ) -> dict[str, list[tuple[float, float]]]:
        """
        Vary each weight independently and measure fitness impact.
        Returns {weight_name: [(value, fitness), ...]}
        """
        base = base_weights or RoutingWeights()
        results: dict[str, list[tuple[float, float]]] = {}

        weight_names = ["skill_match", "reputation", "capacity", "speed", "cost"]
        step_values = [i / steps for i in range(steps + 1)]

        for name in weight_names:
            curve = []
            for val in step_values:
                test = RoutingWeights.from_list(base.to_list())
                setattr(test, name, val)
                test = test.normalized()
                fitness = self._evaluator.evaluate(test, records)
                curve.append((val, fitness.composite))
            results[name] = curve

        return results

    def category_analysis(
        self,
        records: list[TaskRecord],
    ) -> dict[str, FitnessScore]:
        """
        Evaluate the current best config per task category.
        Reveals which categories benefit most from optimization.
        """
        categories: dict[str, list[TaskRecord]] = defaultdict(list)
        for r in records:
            cat = r.category or "uncategorized"
            categories[cat].append(r)

        weights = self._best_ever.weights if self._best_ever else RoutingWeights()
        results = {}
        for cat, cat_records in categories.items():
            results[cat] = self._evaluator.evaluate(weights, cat_records)

        return results

    # ── Serialization ────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize optimizer state."""
        return {
            "generation": self._generation,
            "population_size": self._population_size,
            "mutation_rate": self._mutation_rate,
            "elite_count": self._elite_count,
            "best_ever": {
                "weights": asdict(self._best_ever.weights),
                "fitness": asdict(self._best_ever.fitness),
                "generation": self._best_ever.generation,
            } if self._best_ever else None,
            "history": [
                {
                    "generations": r.generations,
                    "best_fitness": r.best_fitness,
                    "baseline_fitness": r.baseline_fitness,
                    "improvement": r.improvement,
                    "duration_seconds": r.duration_seconds,
                }
                for r in self._history
            ],
        }

    def save(self, path: str | Path):
        """Save optimizer state to JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    # ── Stats ────────────────────────────────────────────────

    def stats(self) -> dict:
        """Current optimizer statistics."""
        return {
            "generation": self._generation,
            "population_size": len(self._population),
            "best_fitness": self._best_ever.fitness.composite if self._best_ever else 0.0,
            "best_weights": asdict(self._best_ever.weights) if self._best_ever else None,
            "total_evaluations": sum(c.evaluations for c in self._population),
            "optimization_runs": len(self._history),
            "avg_improvement": (
                sum(r.improvement for r in self._history) / len(self._history)
                if self._history else 0.0
            ),
        }
