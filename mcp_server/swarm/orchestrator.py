"""
SwarmOrchestrator — Routes tasks to the best available agent.

Coordinates the swarm by:
1. Receiving task requests from the EM API
2. Querying ReputationBridge for agent rankings
3. Checking LifecycleManager for agent availability
4. Assigning tasks with anti-duplication claims
5. Monitoring task progress and handling failures

Task routing strategies:
- BEST_FIT: Assign to highest-scoring available agent
- ROUND_ROBIN: Distribute evenly with tie-breaking by score
- SPECIALIST: Only agents with category experience
- BUDGET_AWARE: Prefer agents with remaining budget headroom
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
    CompositeScore,
)
from .lifecycle_manager import (
    LifecycleManager,
    AgentState,
    AgentRecord,
    LifecycleError,
    BudgetExceededError,
)


class RoutingStrategy(str, Enum):
    BEST_FIT = "best_fit"
    ROUND_ROBIN = "round_robin"
    SPECIALIST = "specialist"
    BUDGET_AWARE = "budget_aware"


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


PRIORITY_WEIGHTS = {
    TaskPriority.CRITICAL: 1.0,
    TaskPriority.HIGH: 0.8,
    TaskPriority.NORMAL: 0.5,
    TaskPriority.LOW: 0.2,
}


@dataclass
class TaskRequest:
    """Incoming task to be routed to an agent."""

    task_id: str
    title: str
    categories: list[str] = field(default_factory=list)
    bounty_usd: float = 0.0
    priority: TaskPriority = TaskPriority.NORMAL
    required_tier: Optional[str] = None  # Minimum reputation tier
    preferred_agent_ids: list[int] = field(default_factory=list)
    exclude_agent_ids: list[int] = field(default_factory=list)
    deadline: Optional[datetime] = None
    max_retries: int = 2
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class Assignment:
    """Result of task routing."""

    task_id: str
    agent_id: int
    agent_name: str
    score: float
    strategy_used: RoutingStrategy
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    alternatives_count: int = 0  # How many agents could have taken this

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "score": round(self.score, 2),
            "strategy": self.strategy_used.value,
            "assigned_at": self.assigned_at.isoformat(),
            "alternatives": self.alternatives_count,
        }


@dataclass
class RoutingFailure:
    """When no agent can handle a task."""

    task_id: str
    reason: str
    attempted_agents: int
    excluded_agents: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SwarmOrchestrator:
    """
    Coordinates task assignment across the agent swarm.

    Usage:
        bridge = ReputationBridge()
        lifecycle = LifecycleManager()
        orchestrator = SwarmOrchestrator(bridge, lifecycle)

        # Register agents
        lifecycle.register_agent(1, "aurora", "0x...", "explorer")
        lifecycle.transition(1, AgentState.IDLE)
        lifecycle.transition(1, AgentState.ACTIVE)

        # Register reputation data
        orchestrator.register_reputation(
            agent_id=1,
            on_chain=OnChainReputation(...),
            internal=InternalReputation(...)
        )

        # Route a task
        task = TaskRequest(task_id="t1", title="Photo verification", categories=["photo"])
        result = orchestrator.route_task(task)
    """

    def __init__(
        self,
        bridge: ReputationBridge,
        lifecycle: LifecycleManager,
        default_strategy: RoutingStrategy = RoutingStrategy.BEST_FIT,
        cooldown_seconds: int = 30,
        min_score_threshold: float = 15.0,
    ):
        self.bridge = bridge
        self.lifecycle = lifecycle
        self.default_strategy = default_strategy
        self.cooldown_seconds = cooldown_seconds
        self.min_score_threshold = min_score_threshold

        # Reputation data store (would be DB in production)
        self._on_chain: dict[int, OnChainReputation] = {}
        self._internal: dict[int, InternalReputation] = {}
        self._last_active: dict[int, datetime] = {}

        # Task tracking
        self._active_claims: dict[str, int] = {}  # task_id → agent_id
        self._assignment_history: deque[Assignment] = deque(maxlen=1000)
        self._failures: deque[RoutingFailure] = deque(maxlen=1000)
        self._round_robin_index: int = 0

    def register_reputation(
        self,
        agent_id: int,
        on_chain: OnChainReputation,
        internal: InternalReputation,
    ) -> None:
        """Register/update reputation data for an agent."""
        self._on_chain[agent_id] = on_chain
        self._internal[agent_id] = internal
        self._last_active[agent_id] = datetime.now(timezone.utc)

    def route_task(
        self,
        task: TaskRequest,
        strategy: Optional[RoutingStrategy] = None,
    ) -> Assignment | RoutingFailure:
        """
        Route a task to the best available agent.
        Returns Assignment on success, RoutingFailure if no agent available.
        """
        strategy = strategy or self.default_strategy

        # Check if task is already claimed
        if task.task_id in self._active_claims:
            existing_agent = self._active_claims[task.task_id]
            return RoutingFailure(
                task_id=task.task_id,
                reason=f"Task already claimed by agent {existing_agent}",
                attempted_agents=0,
                excluded_agents=0,
            )

        # Get available agents from lifecycle manager
        available = self.lifecycle.get_available_agents()

        if not available:
            failure = RoutingFailure(
                task_id=task.task_id,
                reason="No agents available",
                attempted_agents=0,
                excluded_agents=0,
            )
            self._failures.append(failure)
            return failure

        # Filter out excluded agents and apply preferences
        candidates = [a for a in available if a.agent_id not in task.exclude_agent_ids]

        excluded_count = len(available) - len(candidates)

        if not candidates:
            failure = RoutingFailure(
                task_id=task.task_id,
                reason="All available agents are excluded",
                attempted_agents=len(available),
                excluded_agents=excluded_count,
            )
            self._failures.append(failure)
            return failure

        # Score candidates
        scored = self._score_candidates(candidates, task)

        # Apply routing strategy
        selected = self._apply_strategy(scored, task, strategy)

        if selected is None:
            failure = RoutingFailure(
                task_id=task.task_id,
                reason=f"No agent meets minimum score threshold ({self.min_score_threshold})",
                attempted_agents=len(candidates),
                excluded_agents=excluded_count,
            )
            self._failures.append(failure)
            return failure

        # Attempt assignment
        agent_id, score = selected
        agent_record = self.lifecycle.agents.get(agent_id)

        if agent_record is None:
            failure = RoutingFailure(
                task_id=task.task_id,
                reason=f"Selected agent {agent_id} disappeared during routing",
                attempted_agents=len(candidates),
                excluded_agents=excluded_count,
            )
            self._failures.append(failure)
            return failure

        try:
            # Ensure agent is in ACTIVE state
            if agent_record.state == AgentState.IDLE:
                self.lifecycle.transition(agent_id, AgentState.ACTIVE, "task routing")

            # Assign the task
            self.lifecycle.assign_task(agent_id, task.task_id)
            self._active_claims[task.task_id] = agent_id
            self._last_active[agent_id] = datetime.now(timezone.utc)

            assignment = Assignment(
                task_id=task.task_id,
                agent_id=agent_id,
                agent_name=agent_record.name,
                score=score.total if isinstance(score, CompositeScore) else score,
                strategy_used=strategy,
                alternatives_count=len(candidates) - 1,
            )
            self._assignment_history.append(assignment)
            return assignment

        except (LifecycleError, BudgetExceededError) as e:
            failure = RoutingFailure(
                task_id=task.task_id,
                reason=f"Assignment failed: {str(e)}",
                attempted_agents=len(candidates),
                excluded_agents=excluded_count,
            )
            self._failures.append(failure)
            return failure

    def complete_task(self, task_id: str) -> Optional[int]:
        """
        Mark a task as completed by its agent.
        Returns the agent_id or None if task not found.
        """
        agent_id = self._active_claims.pop(task_id, None)
        if agent_id is None:
            return None

        try:
            self.lifecycle.complete_task(
                agent_id, cooldown_seconds=self.cooldown_seconds
            )
        except LifecycleError:
            pass  # Agent might already be in different state

        self._last_active[agent_id] = datetime.now(timezone.utc)
        return agent_id

    def fail_task(self, task_id: str, error: str = "") -> Optional[int]:
        """
        Mark a task as failed. Agent goes to cooldown with longer duration.
        Returns the agent_id or None if task not found.
        """
        agent_id = self._active_claims.pop(task_id, None)
        if agent_id is None:
            return None

        self.lifecycle.record_error(agent_id, error or f"Task {task_id} failed")

        if agent_id in self._internal:
            self._internal[agent_id].consecutive_failures += 1

        try:
            # Longer cooldown for failures
            self.lifecycle.complete_task(
                agent_id,
                cooldown_seconds=self.cooldown_seconds * 3,
            )
        except LifecycleError:
            pass

        return agent_id

    def _score_candidates(
        self,
        candidates: list[AgentRecord],
        task: TaskRequest,
    ) -> list[tuple[int, CompositeScore]]:
        """Score all candidates using the reputation bridge."""
        results = []
        for agent in candidates:
            on_chain = self._on_chain.get(agent.agent_id)
            internal = self._internal.get(agent.agent_id)

            if on_chain is None or internal is None:
                # Create minimal defaults for unregistered agents
                on_chain = on_chain or OnChainReputation(
                    agent_id=agent.agent_id,
                    wallet_address=agent.wallet_address,
                )
                internal = internal or InternalReputation(agent_id=agent.agent_id)

            score = self.bridge.compute_composite(
                on_chain=on_chain,
                internal=internal,
                task_categories=task.categories,
                last_active=self._last_active.get(agent.agent_id),
            )
            results.append((agent.agent_id, score))

        # Sort by total score descending
        results.sort(key=lambda x: x[1].total, reverse=True)
        return results

    def _apply_strategy(
        self,
        scored: list[tuple[int, CompositeScore]],
        task: TaskRequest,
        strategy: RoutingStrategy,
    ) -> Optional[tuple[int, CompositeScore]]:
        """Apply routing strategy to select the final agent."""
        if not scored:
            return None

        # Filter by minimum score
        qualified = [
            (aid, score)
            for aid, score in scored
            if score.total >= self.min_score_threshold
        ]

        if not qualified:
            return None

        # Apply preferences
        if task.preferred_agent_ids:
            preferred = [
                (aid, score)
                for aid, score in qualified
                if aid in task.preferred_agent_ids
            ]
            if preferred:
                qualified = preferred

        if strategy == RoutingStrategy.BEST_FIT:
            return qualified[0]  # Already sorted by score

        elif strategy == RoutingStrategy.ROUND_ROBIN:
            # Round-robin with tie-breaking by score
            idx = self._round_robin_index % len(qualified)
            self._round_robin_index += 1
            return qualified[idx]

        elif strategy == RoutingStrategy.SPECIALIST:
            # Only agents with category-specific experience
            specialists = [
                (aid, score)
                for aid, score in qualified
                if score.skill_score >= 50  # Must have real category experience
            ]
            return specialists[0] if specialists else None

        elif strategy == RoutingStrategy.BUDGET_AWARE:
            # Prefer agents with more budget remaining
            budget_scored = []
            for aid, score in qualified:
                budget = self.lifecycle.get_budget_status(aid)
                headroom = 100 - max(budget["daily_pct"], budget["monthly_pct"])
                # Blend: 70% reputation score + 30% budget headroom
                blended = score.total * 0.7 + headroom * 0.3
                budget_scored.append((aid, score, blended))

            budget_scored.sort(key=lambda x: x[2], reverse=True)
            if budget_scored:
                return (budget_scored[0][0], budget_scored[0][1])
            return None

        # Fallback to best fit
        return qualified[0]

    def get_status(self) -> dict:
        """Get orchestrator status."""
        return {
            "active_claims": len(self._active_claims),
            "total_assignments": len(self._assignment_history),
            "total_failures": len(self._failures),
            "default_strategy": self.default_strategy.value,
            "min_score_threshold": self.min_score_threshold,
            "registered_reputations": len(self._on_chain),
            "swarm": self.lifecycle.get_swarm_status(),
        }

    def get_assignment_history(self, limit: int = 20) -> list[dict]:
        """Get recent assignment history."""
        return [a.to_dict() for a in list(self._assignment_history)[-limit:]]

    def get_failures(self, limit: int = 20) -> list[dict]:
        """Get recent routing failures."""
        return [
            {
                "task_id": f.task_id,
                "reason": f.reason,
                "attempted": f.attempted_agents,
                "excluded": f.excluded_agents,
                "timestamp": f.timestamp.isoformat(),
            }
            for f in list(self._failures)[-limit:]
        ]
