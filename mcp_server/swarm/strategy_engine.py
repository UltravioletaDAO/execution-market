"""
StrategyEngine — Intelligent multi-strategy task routing decision layer.

Sits between the SwarmOrchestrator and the coordinator, providing
sophisticated routing strategies that go beyond basic matching:

1. **Adaptive Strategy** — Automatically selects the best routing strategy
   based on task characteristics, swarm state, and historical performance.

2. **Load Balancer** — Distributes tasks across agents while respecting
   capacity, cooldowns, and skill alignment.

3. **Deadline-Aware Routing** — Prioritizes tasks approaching their deadlines
   and selects agents with faster completion histories.

4. **Specialization Detector** — Identifies emergent agent specializations
   from task completion history and routes accordingly.

5. **Team Composition** — For complex multi-step tasks, assembles agent teams
   with complementary skills.

6. **Outcome Learning** — Tracks which strategies produce the best outcomes
   and adapts strategy selection over time.

Usage:
    engine = StrategyEngine(orchestrator, lifecycle)
    decision = engine.decide(task_request, swarm_state)
    # decision.strategy — which routing strategy to use
    # decision.agent_preferences — ranked agent preferences
    # decision.confidence — how confident the engine is

Design decisions:
    - Stateful: learns from outcomes across sessions
    - Composable: strategies can be combined and weighted
    - Observable: every decision has an explanation chain
    - Fallback-safe: degrades gracefully to BEST_FIT
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional

from .orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    TaskPriority,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
)
from .lifecycle_manager import (
    LifecycleManager,
    AgentState,
    AgentRecord,
)

logger = logging.getLogger("em.swarm.strategy_engine")


# ─── Decision Types ──────────────────────────────────────────────────────────

class StrategyReason(str, Enum):
    """Why a particular strategy was chosen."""
    DEADLINE_PRESSURE = "deadline_pressure"
    SPECIALIST_AVAILABLE = "specialist_available"
    LOAD_IMBALANCE = "load_imbalance"
    HIGH_VALUE_TASK = "high_value_task"
    NEW_CATEGORY = "new_category"
    AGENT_WARMING = "agent_warming"
    HISTORICAL_SUCCESS = "historical_success"
    DEFAULT_FALLBACK = "default_fallback"


@dataclass
class RoutingDecision:
    """The engine's recommendation for how to route a task."""
    strategy: RoutingStrategy
    confidence: float  # 0.0 - 1.0
    reasons: list[StrategyReason] = field(default_factory=list)
    preferred_agents: list[int] = field(default_factory=list)
    excluded_agents: list[int] = field(default_factory=list)
    explanation: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.value,
            "confidence": round(self.confidence, 3),
            "reasons": [r.value for r in self.reasons],
            "preferred_agents": self.preferred_agents,
            "excluded_agents": self.excluded_agents,
            "explanation": self.explanation,
            "metadata": self.metadata,
        }


@dataclass
class AgentLoad:
    """Current load profile for an agent."""
    agent_id: int
    active_tasks: int = 0
    completed_today: int = 0
    daily_budget_remaining_pct: float = 100.0
    avg_completion_time_minutes: float = 0.0
    specializations: list[str] = field(default_factory=list)
    last_task_completed_at: Optional[datetime] = None
    consecutive_successes: int = 0
    consecutive_failures: int = 0

    @property
    def is_available(self) -> bool:
        return self.active_tasks == 0 and self.daily_budget_remaining_pct > 0

    @property
    def load_score(self) -> float:
        """Lower is less loaded (better for assignment)."""
        return (
            self.active_tasks * 10.0
            + (100 - self.daily_budget_remaining_pct) * 0.5
            + self.completed_today * 0.2
        )


@dataclass
class StrategyOutcome:
    """Recorded outcome of a strategy decision for learning."""
    task_id: str
    strategy_used: RoutingStrategy
    agent_assigned: Optional[int]
    success: bool
    completion_time_minutes: float = 0.0
    quality_score: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "strategy": self.strategy_used.value,
            "agent": self.agent_assigned,
            "success": self.success,
            "completion_minutes": round(self.completion_time_minutes, 1),
            "quality": round(self.quality_score, 3),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CategoryProfile:
    """Learned profile for a task category."""
    category: str
    total_tasks: int = 0
    successful_tasks: int = 0
    avg_completion_minutes: float = 0.0
    avg_quality: float = 0.0
    best_strategy: Optional[RoutingStrategy] = None
    best_agents: list[int] = field(default_factory=list)
    strategy_success_rates: dict[str, float] = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks


# ─── Specialization Detection ────────────────────────────────────────────────

@dataclass
class AgentSpecialization:
    """Detected specialization for an agent."""
    agent_id: int
    primary_categories: list[str] = field(default_factory=list)
    category_success_rates: dict[str, float] = field(default_factory=dict)
    category_task_counts: dict[str, int] = field(default_factory=dict)
    specialization_score: float = 0.0  # How specialized (vs generalist)

    @property
    def is_specialist(self) -> bool:
        """An agent is a specialist if >60% of their tasks are in ≤2 categories."""
        if not self.category_task_counts:
            return False
        total = sum(self.category_task_counts.values())
        if total < 5:  # Need minimum history
            return False
        sorted_cats = sorted(self.category_task_counts.values(), reverse=True)
        top_two = sum(sorted_cats[:2])
        return (top_two / total) > 0.6


# ─── Strategy Engine ─────────────────────────────────────────────────────────

class StrategyEngine:
    """
    Intelligent routing strategy selector.

    Analyzes task characteristics, swarm state, and historical outcomes
    to recommend the best routing approach for each task.
    """

    # Strategy selection weights
    DEADLINE_WEIGHT = 0.30
    SPECIALIZATION_WEIGHT = 0.25
    LOAD_BALANCE_WEIGHT = 0.20
    VALUE_WEIGHT = 0.15
    HISTORICAL_WEIGHT = 0.10

    # Thresholds
    HIGH_VALUE_THRESHOLD_USD = 10.0
    DEADLINE_PRESSURE_HOURS = 4.0
    LOAD_IMBALANCE_THRESHOLD = 3.0  # Max diff between most/least loaded
    MIN_HISTORY_FOR_LEARNING = 10

    def __init__(
        self,
        orchestrator: SwarmOrchestrator,
        lifecycle: LifecycleManager,
        default_strategy: RoutingStrategy = RoutingStrategy.BEST_FIT,
    ):
        self.orchestrator = orchestrator
        self.lifecycle = lifecycle
        self.default_strategy = default_strategy

        # Learning state
        self._outcomes: list[StrategyOutcome] = []
        self._category_profiles: dict[str, CategoryProfile] = {}
        self._agent_specializations: dict[int, AgentSpecialization] = {}
        self._strategy_success: dict[str, list[bool]] = {
            s.value: [] for s in RoutingStrategy
        }
        self._decision_count = 0

    # ─── Main Decision Method ─────────────────────────────────────────────

    def decide(self, task: TaskRequest, agent_loads: Optional[dict[int, AgentLoad]] = None) -> RoutingDecision:
        """
        Analyze task + swarm state and recommend the best routing strategy.

        Args:
            task: The task to route
            agent_loads: Optional load profiles for each agent

        Returns:
            RoutingDecision with strategy, confidence, and explanation
        """
        self._decision_count += 1
        scores: dict[RoutingStrategy, float] = {s: 0.0 for s in RoutingStrategy}
        reasons: list[StrategyReason] = []
        explanations: list[str] = []
        preferred_agents: list[int] = []
        excluded_agents: list[int] = []

        # 1. Deadline analysis
        deadline_score = self._analyze_deadline(task)
        if deadline_score > 0.5:
            scores[RoutingStrategy.BEST_FIT] += deadline_score * self.DEADLINE_WEIGHT
            reasons.append(StrategyReason.DEADLINE_PRESSURE)
            explanations.append(f"deadline pressure ({deadline_score:.1f})")

        # 2. Specialization analysis
        spec_result = self._analyze_specialization(task)
        if spec_result["has_specialist"]:
            scores[RoutingStrategy.SPECIALIST] += spec_result["score"] * self.SPECIALIZATION_WEIGHT
            reasons.append(StrategyReason.SPECIALIST_AVAILABLE)
            preferred_agents.extend(spec_result["specialists"])
            explanations.append(f"specialist available: {spec_result['specialists']}")

        # 3. Load balance analysis
        if agent_loads:
            load_result = self._analyze_load_balance(agent_loads)
            if load_result["imbalanced"]:
                scores[RoutingStrategy.ROUND_ROBIN] += load_result["score"] * self.LOAD_BALANCE_WEIGHT
                reasons.append(StrategyReason.LOAD_IMBALANCE)
                preferred_agents.extend(load_result["underloaded"])
                explanations.append(f"load imbalance (spread: {load_result['spread']:.1f})")

        # 4. Value analysis
        value_score = self._analyze_value(task)
        if value_score > 0.5:
            scores[RoutingStrategy.BEST_FIT] += value_score * self.VALUE_WEIGHT
            reasons.append(StrategyReason.HIGH_VALUE_TASK)
            explanations.append(f"high value task (${task.bounty_usd})")

        # 5. Historical learning
        if len(self._outcomes) >= self.MIN_HISTORY_FOR_LEARNING:
            hist_result = self._analyze_historical(task)
            if hist_result["best_strategy"]:
                strategy = hist_result["best_strategy"]
                scores[strategy] += hist_result["score"] * self.HISTORICAL_WEIGHT
                reasons.append(StrategyReason.HISTORICAL_SUCCESS)
                explanations.append(f"historical success: {strategy.value} ({hist_result['success_rate']:.0%})")

        # 6. New category detection
        if self._is_new_category(task):
            scores[RoutingStrategy.ROUND_ROBIN] += 0.3
            reasons.append(StrategyReason.NEW_CATEGORY)
            explanations.append("new category — exploring via round-robin")

        # Select strategy with highest score
        best_strategy = max(scores, key=scores.get)  # type: ignore
        best_score = scores[best_strategy]

        # Default fallback
        if best_score < 0.1:
            best_strategy = self.default_strategy
            reasons = [StrategyReason.DEFAULT_FALLBACK]
            explanations = ["no strong signal, using default"]
            best_score = 0.5

        # Compute confidence
        total_score = sum(scores.values())
        confidence = best_score / total_score if total_score > 0 else 0.5

        return RoutingDecision(
            strategy=best_strategy,
            confidence=min(1.0, confidence),
            reasons=reasons,
            preferred_agents=list(set(preferred_agents)),
            excluded_agents=list(set(excluded_agents)),
            explanation="; ".join(explanations) if explanations else "default strategy",
            metadata={
                "scores": {s.value: round(v, 3) for s, v in scores.items()},
                "decision_number": self._decision_count,
            },
        )

    # ─── Analysis Methods ─────────────────────────────────────────────────

    def _analyze_deadline(self, task: TaskRequest) -> float:
        """Score how urgent the deadline is (0.0 = no deadline, 1.0 = imminent)."""
        if task.deadline is None:
            return 0.0
        now = datetime.now(timezone.utc)
        hours_remaining = (task.deadline - now).total_seconds() / 3600
        if hours_remaining <= 0:
            return 1.0
        if hours_remaining <= self.DEADLINE_PRESSURE_HOURS:
            return 1.0 - (hours_remaining / self.DEADLINE_PRESSURE_HOURS)
        return 0.0

    def _analyze_specialization(self, task: TaskRequest) -> dict:
        """Check if any agents specialize in the task's categories."""
        result = {"has_specialist": False, "score": 0.0, "specialists": []}

        if not task.categories:
            return result

        for agent_id, spec in self._agent_specializations.items():
            if not spec.is_specialist:
                continue
            # Check if agent specializes in any of the task's categories
            for cat in task.categories:
                if cat in spec.category_success_rates:
                    rate = spec.category_success_rates[cat]
                    if rate > 0.7 and spec.category_task_counts.get(cat, 0) >= 3:
                        result["specialists"].append(agent_id)
                        result["score"] = max(result["score"], rate)
                        result["has_specialist"] = True

        return result

    def _analyze_load_balance(self, agent_loads: dict[int, AgentLoad]) -> dict:
        """Check if load is imbalanced across agents."""
        result = {"imbalanced": False, "score": 0.0, "spread": 0.0, "underloaded": []}

        if len(agent_loads) < 2:
            return result

        load_scores = [(aid, load.load_score) for aid, load in agent_loads.items()
                       if load.daily_budget_remaining_pct > 0]

        if not load_scores:
            return result

        scores_only = [s for _, s in load_scores]
        spread = max(scores_only) - min(scores_only)
        result["spread"] = spread

        if spread > self.LOAD_IMBALANCE_THRESHOLD:
            result["imbalanced"] = True
            result["score"] = min(1.0, spread / (self.LOAD_IMBALANCE_THRESHOLD * 3))
            # Identify underloaded agents
            median_load = sorted(scores_only)[len(scores_only) // 2]
            result["underloaded"] = [
                aid for aid, score in load_scores if score < median_load
            ]

        return result

    def _analyze_value(self, task: TaskRequest) -> float:
        """Score how high-value the task is (0.0-1.0)."""
        if task.bounty_usd <= 0:
            return 0.0
        # Logarithmic scaling: $10 = 0.5, $100 = 0.8, $1000 = 1.0
        return min(1.0, math.log10(max(1, task.bounty_usd)) / 3.0)

    def _analyze_historical(self, task: TaskRequest) -> dict:
        """Use historical outcomes to recommend a strategy."""
        result = {"best_strategy": None, "score": 0.0, "success_rate": 0.0}

        # Find outcomes for similar categories
        relevant_outcomes = [
            o for o in self._outcomes
            if any(cat in task.categories for cat in self._get_outcome_categories(o))
        ]

        if len(relevant_outcomes) < 5:
            # Not enough history for this category, use overall stats
            relevant_outcomes = self._outcomes[-50:]  # Last 50 outcomes

        if not relevant_outcomes:
            return result

        # Compute per-strategy success rates
        strategy_stats: dict[str, list[bool]] = {}
        for outcome in relevant_outcomes:
            key = outcome.strategy_used.value
            if key not in strategy_stats:
                strategy_stats[key] = []
            strategy_stats[key].append(outcome.success)

        # Find best strategy by success rate (with minimum sample size)
        best_strategy = None
        best_rate = 0.0
        for strategy_key, successes in strategy_stats.items():
            if len(successes) < 3:
                continue
            rate = sum(successes) / len(successes)
            if rate > best_rate:
                best_rate = rate
                best_strategy = RoutingStrategy(strategy_key)

        if best_strategy and best_rate > 0.6:
            result["best_strategy"] = best_strategy
            result["score"] = best_rate
            result["success_rate"] = best_rate

        return result

    def _is_new_category(self, task: TaskRequest) -> bool:
        """Check if the task is in a category we haven't seen much of."""
        for cat in task.categories:
            profile = self._category_profiles.get(cat)
            if profile is None or profile.total_tasks < 3:
                return True
        return False

    def _get_outcome_categories(self, outcome: StrategyOutcome) -> list[str]:
        """Get categories associated with an outcome (from metadata)."""
        return outcome.to_dict().get("categories", [])

    # ─── Outcome Recording ────────────────────────────────────────────────

    def record_outcome(
        self,
        task_id: str,
        strategy_used: RoutingStrategy,
        agent_id: Optional[int],
        success: bool,
        categories: Optional[list[str]] = None,
        completion_time_minutes: float = 0.0,
        quality_score: float = 0.0,
    ):
        """
        Record the outcome of a task for learning.

        This is the feedback loop: outcomes improve future decisions.
        """
        outcome = StrategyOutcome(
            task_id=task_id,
            strategy_used=strategy_used,
            agent_assigned=agent_id,
            success=success,
            completion_time_minutes=completion_time_minutes,
            quality_score=quality_score,
        )
        self._outcomes.append(outcome)

        # Keep bounded
        if len(self._outcomes) > 5000:
            self._outcomes = self._outcomes[-2500:]

        # Update strategy success tracking
        key = strategy_used.value
        if key not in self._strategy_success:
            self._strategy_success[key] = []
        self._strategy_success[key].append(success)

        # Update category profile
        if categories:
            for cat in categories:
                self._update_category_profile(
                    cat, strategy_used, success,
                    completion_time_minutes, quality_score,
                    agent_id,
                )

        # Update agent specialization
        if agent_id and categories:
            self._update_agent_specialization(agent_id, categories, success)

        logger.debug(
            f"Recorded outcome for {task_id}: "
            f"strategy={strategy_used.value}, success={success}, "
            f"agent={agent_id}"
        )

    def _update_category_profile(
        self,
        category: str,
        strategy: RoutingStrategy,
        success: bool,
        completion_minutes: float,
        quality: float,
        agent_id: Optional[int],
    ):
        """Update the learned profile for a task category."""
        if category not in self._category_profiles:
            self._category_profiles[category] = CategoryProfile(category=category)

        profile = self._category_profiles[category]
        profile.total_tasks += 1
        if success:
            profile.successful_tasks += 1

        # Update averages
        if profile.total_tasks == 1:
            profile.avg_completion_minutes = completion_minutes
            profile.avg_quality = quality
        else:
            n = profile.total_tasks
            profile.avg_completion_minutes = (
                profile.avg_completion_minutes * (n - 1) + completion_minutes
            ) / n
            profile.avg_quality = (
                profile.avg_quality * (n - 1) + quality
            ) / n

        # Track per-strategy success rates
        key = strategy.value
        if key not in profile.strategy_success_rates:
            profile.strategy_success_rates[key] = 0.0
        # EMA update
        current = profile.strategy_success_rates[key]
        profile.strategy_success_rates[key] = current * 0.8 + (1.0 if success else 0.0) * 0.2

        # Track best strategy
        if profile.strategy_success_rates:
            best_key = max(profile.strategy_success_rates, key=profile.strategy_success_rates.get)
            profile.best_strategy = RoutingStrategy(best_key)

        # Track best agents
        if agent_id and success and agent_id not in profile.best_agents:
            profile.best_agents.append(agent_id)
            if len(profile.best_agents) > 10:
                profile.best_agents = profile.best_agents[-10:]

    def _update_agent_specialization(
        self,
        agent_id: int,
        categories: list[str],
        success: bool,
    ):
        """Update the specialization profile for an agent."""
        if agent_id not in self._agent_specializations:
            self._agent_specializations[agent_id] = AgentSpecialization(agent_id=agent_id)

        spec = self._agent_specializations[agent_id]

        for cat in categories:
            # Update task counts
            spec.category_task_counts[cat] = spec.category_task_counts.get(cat, 0) + 1

            # Update success rates (EMA)
            current_rate = spec.category_success_rates.get(cat, 0.5)
            spec.category_success_rates[cat] = current_rate * 0.8 + (1.0 if success else 0.0) * 0.2

        # Recalculate primary categories
        sorted_cats = sorted(
            spec.category_task_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        spec.primary_categories = [cat for cat, _ in sorted_cats[:3]]

        # Calculate specialization score (Herfindahl index)
        total = sum(spec.category_task_counts.values())
        if total > 0:
            shares = [count / total for count in spec.category_task_counts.values()]
            spec.specialization_score = sum(s * s for s in shares)

    # ─── Composite Routing ────────────────────────────────────────────────

    def route_with_strategy(
        self,
        task: TaskRequest,
        agent_loads: Optional[dict[int, AgentLoad]] = None,
    ) -> tuple[RoutingDecision, Assignment | RoutingFailure]:
        """
        Full pipeline: decide strategy → route task → return both decision and result.

        This is the main entry point for strategy-aware routing.
        """
        decision = self.decide(task, agent_loads)

        # Apply preferred agents to task request
        if decision.preferred_agents:
            task.preferred_agent_ids = decision.preferred_agents
        if decision.excluded_agents:
            task.exclude_agent_ids = decision.excluded_agents

        # Route using the selected strategy
        result = self.orchestrator.route_task(task, strategy=decision.strategy)

        return decision, result

    # ─── Reporting ────────────────────────────────────────────────────────

    def get_strategy_report(self) -> dict:
        """Get a report of strategy performance."""
        strategy_stats = {}
        for strategy_key, successes in self._strategy_success.items():
            if not successes:
                continue
            strategy_stats[strategy_key] = {
                "total": len(successes),
                "successes": sum(successes),
                "success_rate": round(sum(successes) / len(successes), 3),
            }

        category_stats = {}
        for cat, profile in self._category_profiles.items():
            category_stats[cat] = {
                "total_tasks": profile.total_tasks,
                "success_rate": round(profile.success_rate, 3),
                "avg_completion_minutes": round(profile.avg_completion_minutes, 1),
                "avg_quality": round(profile.avg_quality, 3),
                "best_strategy": profile.best_strategy.value if profile.best_strategy else None,
            }

        specialization_stats = {}
        for agent_id, spec in self._agent_specializations.items():
            specialization_stats[str(agent_id)] = {
                "is_specialist": spec.is_specialist,
                "primary_categories": spec.primary_categories,
                "specialization_score": round(spec.specialization_score, 3),
                "category_counts": spec.category_task_counts,
            }

        return {
            "total_decisions": self._decision_count,
            "total_outcomes": len(self._outcomes),
            "strategy_performance": strategy_stats,
            "category_profiles": category_stats,
            "agent_specializations": specialization_stats,
        }

    def get_category_profile(self, category: str) -> Optional[CategoryProfile]:
        """Get the learned profile for a category."""
        return self._category_profiles.get(category)

    def get_agent_specialization(self, agent_id: int) -> Optional[AgentSpecialization]:
        """Get the specialization profile for an agent."""
        return self._agent_specializations.get(agent_id)
