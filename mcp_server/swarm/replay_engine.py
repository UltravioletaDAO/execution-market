"""
SwarmReplayEngine — Historical Task Decision Replay & Simulation
================================================================

Replays historical task data through the swarm's routing, scheduling, and
feedback pipeline without making real API calls. Essential for:

1. **Validation**: Did the swarm make good decisions? Compare replay routing
   against actual outcomes.
2. **What-if Analysis**: Change routing weights, agent configs, or budget
   limits and see how outcomes would differ.
3. **Regression Testing**: Ensure routing changes don't break known-good
   assignments.
4. **Training**: Generate synthetic scenarios from real data patterns.

Architecture:
    TaskSnapshot ─→ ReplayEngine ─→ ReplayResult
                      ├── route() using SwarmCoordinator
                      ├── schedule() using Scheduler heuristics
                      ├── score() using FeedbackPipeline metrics
                      └── compare() against actual historical outcome

    Scenario ──→ ReplayEngine.run_scenario() ──→ ScenarioReport
      (list of snapshots + config overrides)

No external dependencies. No API calls. Pure simulation from captured data.
"""

import json
import logging
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("em.swarm.replay")


# ──────────────────────────────────────────────────────────────
# Data types
# ──────────────────────────────────────────────────────────────


class TaskOutcome(str, Enum):
    """Historical task outcome."""

    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    IN_PROGRESS = "in_progress"
    DISPUTED = "disputed"


@dataclass
class TaskSnapshot:
    """A frozen snapshot of a task at a point in time."""

    task_id: str
    title: str
    description: str = ""
    category: str = "general"
    bounty_usd: float = 0.0
    deadline_hours: float = 24.0
    required_skills: list = field(default_factory=list)
    location: str = ""
    evidence_types: list = field(default_factory=list)

    # Historical outcome (if known)
    actual_worker_id: Optional[str] = None
    actual_outcome: Optional[str] = None
    actual_completion_hours: Optional[float] = None
    actual_rating: Optional[float] = None

    # Metadata
    created_at: Optional[str] = None
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskSnapshot":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AgentProfile:
    """Simplified agent capability profile for replay."""

    agent_id: str
    skills: list = field(default_factory=list)
    success_rate: float = 0.8
    avg_completion_hours: float = 4.0
    capacity: int = 3  # Max concurrent tasks
    active_tasks: int = 0
    hourly_rate: float = 0.0
    location: str = ""
    reputation_score: float = 0.5

    def available(self) -> bool:
        return self.active_tasks < self.capacity

    def skill_overlap(self, required: list) -> float:
        """Fraction of required skills this agent has."""
        if not required:
            return 1.0
        my_skills = set(s.lower() for s in self.skills)
        req_skills = set(s.lower() for s in required)
        if not req_skills:
            return 1.0
        return len(my_skills & req_skills) / len(req_skills)


@dataclass
class RoutingDecision:
    """The engine's decision for a single task."""

    task_id: str
    recommended_agent_id: Optional[str] = None
    confidence: float = 0.0
    reasoning: str = ""
    skill_match: float = 0.0
    capacity_score: float = 0.0
    reputation_score: float = 0.0
    speed_score: float = 0.0
    composite_score: float = 0.0
    alternatives: list = field(default_factory=list)  # List of (agent_id, score) tuples

    # Comparison with actual
    matches_actual: Optional[bool] = None
    actual_was_better: Optional[bool] = None
    explanation: str = ""


@dataclass
class ReplayResult:
    """Result of replaying a single task."""

    task: TaskSnapshot
    decision: RoutingDecision
    simulated_outcome: str = "unknown"
    estimated_completion_hours: float = 0.0
    cost_estimate: float = 0.0

    def accuracy_signal(self) -> Optional[bool]:
        """Did our routing match the actual outcome's quality?"""
        if self.task.actual_outcome is None:
            return None
        if self.task.actual_outcome == "completed":
            return self.decision.confidence > 0.5
        return self.decision.confidence <= 0.5


@dataclass
class ScenarioReport:
    """Summary of a full scenario replay."""

    scenario_name: str
    task_count: int = 0
    routed_count: int = 0
    unroutable_count: int = 0
    avg_confidence: float = 0.0
    avg_skill_match: float = 0.0

    # Comparison metrics (when historical data available)
    match_rate: float = 0.0  # % where replay agreed with actual assignment
    outcome_correlation: float = 0.0  # Correlation between confidence and success

    # Agent utilization
    agent_load: dict = field(default_factory=dict)  # agent_id → task count
    agent_diversity: float = 0.0  # 0=all tasks to one agent, 1=evenly spread

    # Budget
    total_estimated_cost: float = 0.0
    avg_cost_per_task: float = 0.0

    results: list = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert results to dicts too
        d["results"] = [
            {
                "task_id": r.task.task_id,
                "agent": r.decision.recommended_agent_id,
                "confidence": round(r.decision.confidence, 3),
                "skill_match": round(r.decision.skill_match, 3),
                "matches_actual": r.decision.matches_actual,
            }
            for r in self.results
        ]
        return d


# ──────────────────────────────────────────────────────────────
# Routing config
# ──────────────────────────────────────────────────────────────


@dataclass
class RoutingConfig:
    """Tunable routing weights for what-if analysis."""

    skill_weight: float = 0.35
    capacity_weight: float = 0.15
    reputation_weight: float = 0.25
    speed_weight: float = 0.15
    cost_weight: float = 0.10

    # Thresholds
    min_skill_overlap: float = 0.3  # Minimum skill match to consider
    min_reputation: float = 0.1  # Minimum reputation to consider
    max_load_ratio: float = 0.9  # Max active/capacity ratio

    def validate(self) -> list:
        """Returns list of validation errors."""
        errors = []
        total = (
            self.skill_weight
            + self.capacity_weight
            + self.reputation_weight
            + self.speed_weight
            + self.cost_weight
        )
        if abs(total - 1.0) > 0.01:
            errors.append(f"Weights sum to {total:.3f}, should be 1.0")
        for attr in [
            "skill_weight",
            "capacity_weight",
            "reputation_weight",
            "speed_weight",
            "cost_weight",
        ]:
            if getattr(self, attr) < 0:
                errors.append(f"{attr} is negative")
        return errors


# ──────────────────────────────────────────────────────────────
# Replay engine
# ──────────────────────────────────────────────────────────────


class ReplayEngine:
    """Replays task assignments through configurable routing logic."""

    def __init__(self, agents: list = None, config: RoutingConfig = None):
        self.agents = {a.agent_id: a for a in (agents or [])}
        self.config = config or RoutingConfig()
        self._replay_count = 0
        self._cache = {}

    def add_agent(self, agent: AgentProfile):
        """Register an agent for routing."""
        self.agents[agent.agent_id] = agent

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent. Returns True if existed."""
        return self.agents.pop(agent_id, None) is not None

    def reset_agent_loads(self):
        """Reset all agents to zero active tasks."""
        for agent in self.agents.values():
            agent.active_tasks = 0

    def route_task(self, task: TaskSnapshot) -> RoutingDecision:
        """Route a single task to the best available agent."""
        decision = RoutingDecision(task_id=task.task_id)

        if not self.agents:
            decision.reasoning = "No agents registered"
            return decision

        candidates = []
        for agent in self.agents.values():
            score_detail = self._score_agent(agent, task)
            if score_detail is None:
                continue
            candidates.append((agent, score_detail))

        if not candidates:
            decision.reasoning = (
                "No eligible agents (skill/capacity/reputation filters)"
            )
            return decision

        # Sort by composite score descending
        candidates.sort(key=lambda x: x[1]["composite"], reverse=True)

        best_agent, best_scores = candidates[0]
        decision.recommended_agent_id = best_agent.agent_id
        decision.skill_match = best_scores["skill"]
        decision.capacity_score = best_scores["capacity"]
        decision.reputation_score = best_scores["reputation"]
        decision.speed_score = best_scores["speed"]
        decision.composite_score = best_scores["composite"]
        decision.confidence = min(1.0, best_scores["composite"] * 1.2)

        # Alternatives
        decision.alternatives = [
            (a.agent_id, round(s["composite"], 3)) for a, s in candidates[1:4]
        ]

        # Build reasoning
        parts = [f"Best match: {best_agent.agent_id}"]
        if decision.skill_match > 0.8:
            parts.append("strong skill alignment")
        elif decision.skill_match > 0.5:
            parts.append("partial skill overlap")
        if best_agent.success_rate > 0.9:
            parts.append("high success rate")
        if len(candidates) == 1:
            parts.append("only eligible agent")
        decision.reasoning = "; ".join(parts)

        # Compare with actual if available
        if task.actual_worker_id:
            decision.matches_actual = best_agent.agent_id == task.actual_worker_id
            if not decision.matches_actual and task.actual_outcome == "completed":
                # Our pick was different but the actual one succeeded
                actual_in_candidates = any(
                    a.agent_id == task.actual_worker_id for a, _ in candidates
                )
                if actual_in_candidates:
                    actual_score = next(
                        s["composite"]
                        for a, s in candidates
                        if a.agent_id == task.actual_worker_id
                    )
                    decision.actual_was_better = actual_score > best_scores["composite"]

        return decision

    def _score_agent(self, agent: AgentProfile, task: TaskSnapshot) -> Optional[dict]:
        """Score an agent for a task. Returns None if ineligible."""
        cfg = self.config

        # Hard filters
        skill_match = agent.skill_overlap(task.required_skills)
        if skill_match < cfg.min_skill_overlap and task.required_skills:
            return None

        if agent.reputation_score < cfg.min_reputation:
            return None

        load_ratio = agent.active_tasks / max(agent.capacity, 1)
        if load_ratio >= cfg.max_load_ratio:
            return None

        # Soft scores (0-1 range)
        capacity_score = 1.0 - load_ratio
        reputation_score = agent.reputation_score
        speed_score = max(
            0, 1.0 - (agent.avg_completion_hours / max(task.deadline_hours, 1))
        )
        cost_score = 1.0  # Placeholder for cost optimization

        if agent.hourly_rate > 0 and task.bounty_usd > 0:
            estimated_cost = agent.hourly_rate * agent.avg_completion_hours
            cost_score = max(0, 1.0 - (estimated_cost / task.bounty_usd))

        composite = (
            skill_match * cfg.skill_weight
            + capacity_score * cfg.capacity_weight
            + reputation_score * cfg.reputation_weight
            + speed_score * cfg.speed_weight
            + cost_score * cfg.cost_weight
        )

        return {
            "skill": skill_match,
            "capacity": capacity_score,
            "reputation": reputation_score,
            "speed": speed_score,
            "cost": cost_score,
            "composite": composite,
        }

    def replay_task(self, task: TaskSnapshot) -> ReplayResult:
        """Replay a single task through the full pipeline."""
        decision = self.route_task(task)

        result = ReplayResult(
            task=task,
            decision=decision,
        )

        if decision.recommended_agent_id:
            agent = self.agents[decision.recommended_agent_id]
            result.estimated_completion_hours = agent.avg_completion_hours
            result.cost_estimate = task.bounty_usd

            # Simulate outcome based on agent profile + confidence
            if decision.confidence > 0.7 and agent.success_rate > 0.7:
                result.simulated_outcome = "completed"
            elif decision.confidence > 0.4:
                result.simulated_outcome = "at_risk"
            else:
                result.simulated_outcome = "likely_expired"

            # Track agent load for sequential replays
            agent.active_tasks += 1
        else:
            result.simulated_outcome = "unroutable"

        self._replay_count += 1
        return result

    def run_scenario(
        self, name: str, tasks: list, reset_loads: bool = True
    ) -> ScenarioReport:
        """Run a full scenario (list of tasks) and generate a report."""
        start = time.monotonic()

        if reset_loads:
            self.reset_agent_loads()

        report = ScenarioReport(scenario_name=name, task_count=len(tasks))
        results = []
        confidences = []
        skill_matches = []
        agent_assignments = Counter()

        for task in tasks:
            result = self.replay_task(task)
            results.append(result)

            if result.decision.recommended_agent_id:
                report.routed_count += 1
                confidences.append(result.decision.confidence)
                skill_matches.append(result.decision.skill_match)
                agent_assignments[result.decision.recommended_agent_id] += 1
                report.total_estimated_cost += result.cost_estimate
            else:
                report.unroutable_count += 1

        report.results = results
        report.duration_ms = (time.monotonic() - start) * 1000

        # Averages
        if confidences:
            report.avg_confidence = sum(confidences) / len(confidences)
        if skill_matches:
            report.avg_skill_match = sum(skill_matches) / len(skill_matches)
        if report.routed_count > 0:
            report.avg_cost_per_task = report.total_estimated_cost / report.routed_count

        # Agent load distribution
        report.agent_load = dict(agent_assignments)

        # Agent diversity (normalized entropy)
        if agent_assignments and report.routed_count > 0:
            import math

            n_agents = len(agent_assignments)
            if n_agents > 1:
                entropy = -sum(
                    (c / report.routed_count) * math.log2(c / report.routed_count)
                    for c in agent_assignments.values()
                )
                max_entropy = math.log2(n_agents)
                report.agent_diversity = entropy / max_entropy if max_entropy > 0 else 0
            else:
                report.agent_diversity = 0.0

        # Match rate (when historical data available)
        matches = [r for r in results if r.decision.matches_actual is not None]
        if matches:
            correct = sum(1 for r in matches if r.decision.matches_actual)
            report.match_rate = correct / len(matches)

        # Outcome correlation
        outcome_pairs = [
            (
                r.decision.confidence,
                1.0 if r.task.actual_outcome == "completed" else 0.0,
            )
            for r in results
            if r.task.actual_outcome is not None
        ]
        if len(outcome_pairs) >= 2:
            report.outcome_correlation = self._pearson(outcome_pairs)

        return report

    @staticmethod
    def _pearson(pairs: list) -> float:
        """Simple Pearson correlation coefficient."""
        n = len(pairs)
        if n < 2:
            return 0.0
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
        den_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
        den_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
        if den_x * den_y == 0:
            return 0.0
        return num / (den_x * den_y)

    # ──────────────────────────────────────────────────────────────
    # I/O helpers
    # ──────────────────────────────────────────────────────────────

    def load_tasks(self, path: str) -> list:
        """Load task snapshots from a JSON file."""
        data = json.loads(Path(path).read_text())
        tasks = data if isinstance(data, list) else data.get("tasks", [])
        return [TaskSnapshot.from_dict(t) for t in tasks]

    def save_report(self, report: ScenarioReport, path: str):
        """Save scenario report to JSON."""
        Path(path).write_text(json.dumps(report.to_dict(), indent=2))

    def export_decisions(self, results: list) -> list:
        """Export routing decisions as dicts for analysis."""
        return [
            {
                "task_id": r.task.task_id,
                "title": r.task.title,
                "recommended_agent": r.decision.recommended_agent_id,
                "confidence": round(r.decision.confidence, 3),
                "skill_match": round(r.decision.skill_match, 3),
                "composite_score": round(r.decision.composite_score, 3),
                "simulated_outcome": r.simulated_outcome,
                "actual_outcome": r.task.actual_outcome,
                "matches_actual": r.decision.matches_actual,
                "alternatives": r.decision.alternatives,
            }
            for r in results
        ]

    # ──────────────────────────────────────────────────────────────
    # What-if API
    # ──────────────────────────────────────────────────────────────

    def compare_configs(self, tasks: list, configs: list) -> dict:
        """Run same tasks with different routing configs and compare results."""
        comparisons = {}
        for i, config in enumerate(configs):
            name = getattr(config, "name", f"config_{i}")
            self.config = config
            report = self.run_scenario(name=name, tasks=tasks, reset_loads=True)
            comparisons[name] = {
                "avg_confidence": round(report.avg_confidence, 3),
                "avg_skill_match": round(report.avg_skill_match, 3),
                "routed_pct": round(report.routed_count / max(report.task_count, 1), 3),
                "agent_diversity": round(report.agent_diversity, 3),
                "match_rate": round(report.match_rate, 3),
                "total_cost": round(report.total_estimated_cost, 2),
            }
        return comparisons

    @property
    def replay_count(self) -> int:
        return self._replay_count
