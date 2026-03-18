"""
SwarmScheduler — Deadline-Aware Priority Scheduling & Dynamic Strategy Selection
=================================================================================

The missing piece between task ingestion and agent assignment. While the
SwarmOrchestrator handles the "who should do this task?" question, the
SwarmScheduler answers "when should we assign this task, and with what strategy?"

Key capabilities:
1. **Deadline urgency scoring** — Tasks approaching deadlines get priority boosts
2. **Dynamic strategy selection** — Picks BEST_FIT vs SPECIALIST vs BUDGET_AWARE
   based on current swarm conditions (agent availability, budget, task type)
3. **Batch optimization** — Groups compatible tasks for efficient routing
4. **Cooldown-aware scheduling** — Predicts when agents exit cooldown
5. **Load balancing** — Prevents agent overload via sliding window limits
6. **Retry scheduling** — Exponential backoff with jitter for failed routes

Architecture:
    TaskQueue → SwarmScheduler.schedule() → PrioritizedBatch[]
    PrioritizedBatch → SwarmOrchestrator.route_task() → Assignment/Failure
    SwarmScheduler monitors outcomes and adapts strategy selection

Integration:
    coordinator = SwarmCoordinator.create(...)
    scheduler = SwarmScheduler(coordinator)
    scheduler.run_scheduling_cycle()  # Call periodically (e.g., every 30s)
"""

import math
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .orchestrator import (
    RoutingStrategy,
    TaskPriority,
    TaskRequest,
    Assignment,
)
from .lifecycle_manager import AgentState


# ──────────────────────────────────────────────────────────────
# Scheduling Data Types
# ──────────────────────────────────────────────────────────────


class UrgencyLevel(str, Enum):
    """Time-pressure classification for tasks."""

    EXPIRED = "expired"  # Past deadline
    CRITICAL = "critical"  # <1 hour to deadline
    URGENT = "urgent"  # <4 hours to deadline
    NORMAL = "normal"  # <24 hours or no deadline
    RELAXED = "relaxed"  # >24 hours to deadline


# Multipliers for urgency-based priority boosting
URGENCY_MULTIPLIERS = {
    UrgencyLevel.EXPIRED: 0.0,  # Don't schedule expired tasks
    UrgencyLevel.CRITICAL: 3.0,
    UrgencyLevel.URGENT: 2.0,
    UrgencyLevel.NORMAL: 1.0,
    UrgencyLevel.RELAXED: 0.8,
}


@dataclass
class ScheduledTask:
    """A task with scheduling metadata."""

    task_id: str
    title: str
    categories: list[str]
    bounty_usd: float
    priority: TaskPriority
    deadline: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Scheduling state
    urgency: UrgencyLevel = UrgencyLevel.NORMAL
    effective_priority: float = 0.0  # Computed priority score
    recommended_strategy: RoutingStrategy = RoutingStrategy.BEST_FIT
    retry_count: int = 0
    last_attempt_at: Optional[float] = None
    next_eligible_at: Optional[float] = None  # Backoff timer

    # Batch grouping
    batch_key: str = ""  # Category-based grouping key

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        self.batch_key = "|".join(sorted(self.categories)) or "uncategorized"


@dataclass
class SchedulingBatch:
    """A group of tasks to route together."""

    batch_id: str
    category_key: str
    tasks: list[ScheduledTask] = field(default_factory=list)
    strategy: RoutingStrategy = RoutingStrategy.BEST_FIT
    created_at: float = field(default_factory=time.time)

    @property
    def total_bounty(self) -> float:
        return sum(t.bounty_usd for t in self.tasks)

    @property
    def max_urgency(self) -> UrgencyLevel:
        """Highest urgency in the batch."""
        urgency_order = [
            UrgencyLevel.CRITICAL,
            UrgencyLevel.URGENT,
            UrgencyLevel.NORMAL,
            UrgencyLevel.RELAXED,
        ]
        for level in urgency_order:
            if any(t.urgency == level for t in self.tasks):
                return level
        return UrgencyLevel.NORMAL

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "category": self.category_key,
            "task_count": len(self.tasks),
            "total_bounty": round(self.total_bounty, 2),
            "max_urgency": self.max_urgency.value,
            "strategy": self.strategy.value,
            "task_ids": [t.task_id for t in self.tasks],
        }


@dataclass
class SchedulingDecision:
    """Record of a scheduling decision for audit/learning."""

    task_id: str
    urgency: str
    effective_priority: float
    chosen_strategy: str
    reason: str
    outcome: Optional[str] = None  # "assigned", "failed", "deferred"
    timestamp: float = field(default_factory=time.time)


@dataclass
class SwarmConditions:
    """Snapshot of current swarm state for strategy selection."""

    total_agents: int = 0
    idle_agents: int = 0
    active_agents: int = 0
    working_agents: int = 0
    cooldown_agents: int = 0
    degraded_agents: int = 0
    suspended_agents: int = 0
    avg_budget_utilization: float = 0.0  # 0.0 to 1.0
    pending_tasks: int = 0
    high_priority_pending: int = 0

    @property
    def availability_ratio(self) -> float:
        """Ratio of available (idle+active) agents to total."""
        if self.total_agents == 0:
            return 0.0
        return (self.idle_agents + self.active_agents) / self.total_agents

    @property
    def load_factor(self) -> float:
        """Current load: pending tasks / available agents."""
        available = self.idle_agents + self.active_agents
        if available == 0:
            return float("inf")
        return self.pending_tasks / available

    @property
    def is_overloaded(self) -> bool:
        return self.load_factor > 3.0

    @property
    def is_underloaded(self) -> bool:
        return self.load_factor < 0.5

    @property
    def budget_headroom(self) -> float:
        """Average remaining budget capacity (0.0 to 1.0)."""
        return max(0.0, 1.0 - self.avg_budget_utilization)


# ──────────────────────────────────────────────────────────────
# Circuit Breaker (API Resilience)
# ──────────────────────────────────────────────────────────────


class CircuitState(str, Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures exceeded threshold, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern for API resilience.

    Prevents cascade failures when the EM API or AutoJob is unresponsive.

    States:
        CLOSED → OPEN: After failure_threshold consecutive failures
        OPEN → HALF_OPEN: After recovery_timeout_seconds
        HALF_OPEN → CLOSED: On success
        HALF_OPEN → OPEN: On failure

    Usage:
        breaker = CircuitBreaker("em_api", failure_threshold=5)

        if breaker.allow_request():
            try:
                result = em_client.list_tasks()
                breaker.record_success()
            except Exception:
                breaker.record_failure()
        else:
            # Service is in open state, skip
            pass
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_at: Optional[float] = None
        self._opened_at: Optional[float] = None
        self._half_open_calls = 0
        self._total_trips = 0

    @property
    def state(self) -> CircuitState:
        # Check if OPEN should transition to HALF_OPEN
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            elapsed = time.time() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        current = self.state
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        return False  # OPEN

    def record_success(self) -> None:
        """Record a successful API call."""
        self._success_count += 1

        if self._state == CircuitState.HALF_OPEN:
            # Recovery confirmed
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._half_open_calls = 0
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed API call."""
        self._failure_count += 1
        self._last_failure_at = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Recovery failed, re-open
            self._trip()
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._trip()

    def _trip(self) -> None:
        """Trip the circuit breaker to OPEN state."""
        self._state = CircuitState.OPEN
        self._opened_at = time.time()
        self._total_trips += 1
        self._half_open_calls = 0

    def reset(self) -> None:
        """Force reset to CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        self._opened_at = None

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_trips": self._total_trips,
            "last_failure_at": self._last_failure_at,
            "recovery_timeout": self.recovery_timeout,
        }


# ──────────────────────────────────────────────────────────────
# Retry Scheduler with Jitter
# ──────────────────────────────────────────────────────────────


class RetryScheduler:
    """
    Exponential backoff with jitter for failed task routing.

    Uses "decorrelated jitter" algorithm (AWS best practice):
        delay = min(cap, random_between(base, previous_delay * 3))

    This prevents thundering herd when multiple tasks retry simultaneously.
    """

    BASE_DELAY_SECONDS = 10.0
    MAX_DELAY_SECONDS = 300.0
    MAX_RETRIES = 5

    def __init__(
        self,
        base_delay: float = BASE_DELAY_SECONDS,
        max_delay: float = MAX_DELAY_SECONDS,
        max_retries: int = MAX_RETRIES,
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self._previous_delays: dict[str, float] = {}

    def should_retry(self, task_id: str, attempt: int) -> bool:
        """Check if a task should be retried."""
        return attempt < self.max_retries

    def next_delay(self, task_id: str, attempt: int) -> float:
        """
        Compute next retry delay with decorrelated jitter.

        Returns delay in seconds, or -1 if max retries exceeded.
        """
        if attempt >= self.max_retries:
            return -1.0

        prev = self._previous_delays.get(task_id, self.base_delay)
        # Decorrelated jitter: random between base and 3x previous
        delay = min(self.max_delay, random.uniform(self.base_delay, prev * 3))
        self._previous_delays[task_id] = delay
        return delay

    def get_next_eligible_time(self, task_id: str, attempt: int) -> float:
        """Get the next eligible timestamp for retry."""
        delay = self.next_delay(task_id, attempt)
        if delay < 0:
            return float("inf")
        return time.time() + delay

    def clear(self, task_id: str) -> None:
        """Clear retry tracking for a task (on success)."""
        self._previous_delays.pop(task_id, None)


# ──────────────────────────────────────────────────────────────
# Load Balancer
# ──────────────────────────────────────────────────────────────


class AgentLoadBalancer:
    """
    Sliding window load limiter per agent.

    Prevents overwhelming any single agent with too many tasks
    in a short time window, even if they're the highest-scoring.

    Window: last N minutes
    Limit: max tasks per window
    """

    def __init__(
        self,
        window_seconds: int = 3600,  # 1 hour
        max_tasks_per_window: int = 5,
    ):
        self.window_seconds = window_seconds
        self.max_tasks = max_tasks_per_window
        self._assignments: dict[int, deque[float]] = defaultdict(
            lambda: deque(maxlen=100)
        )

    def record_assignment(self, agent_id: int) -> None:
        """Record a task assignment to an agent."""
        self._assignments[agent_id].append(time.time())

    def is_available(self, agent_id: int) -> bool:
        """Check if an agent has capacity in the current window."""
        if agent_id not in self._assignments:
            return True

        cutoff = time.time() - self.window_seconds
        recent = sum(1 for t in self._assignments[agent_id] if t > cutoff)
        return recent < self.max_tasks

    def get_load(self, agent_id: int) -> dict:
        """Get current load info for an agent."""
        cutoff = time.time() - self.window_seconds
        if agent_id not in self._assignments:
            return {"agent_id": agent_id, "recent_tasks": 0, "capacity": self.max_tasks}

        recent = sum(1 for t in self._assignments[agent_id] if t > cutoff)
        return {
            "agent_id": agent_id,
            "recent_tasks": recent,
            "capacity": self.max_tasks,
            "utilization": round(recent / self.max_tasks, 2),
        }

    def get_fleet_load(self, agent_ids: list[int]) -> dict:
        """Get load summary across the fleet."""
        loads = [self.get_load(aid) for aid in agent_ids]
        total_recent = sum(l["recent_tasks"] for l in loads)
        total_capacity = sum(l["capacity"] for l in loads)
        overloaded = [l for l in loads if l["recent_tasks"] >= l["capacity"]]

        return {
            "total_agents": len(agent_ids),
            "total_recent_tasks": total_recent,
            "total_capacity": total_capacity,
            "fleet_utilization": round(
                total_recent / total_capacity if total_capacity > 0 else 0.0, 3
            ),
            "overloaded_agents": len(overloaded),
        }


# ──────────────────────────────────────────────────────────────
# SwarmScheduler
# ──────────────────────────────────────────────────────────────


class SwarmScheduler:
    """
    Intelligent task scheduling with deadline awareness and dynamic strategy.

    The scheduler sits between task ingestion and the orchestrator, adding
    a layer of intelligence about *when* and *how* to route each task.

    Usage:
        from .coordinator import SwarmCoordinator
        from .scheduler import SwarmScheduler

        coordinator = SwarmCoordinator.create(...)
        scheduler = SwarmScheduler(coordinator)

        # Periodic scheduling cycle
        results = scheduler.run_scheduling_cycle()

        # Or manual scheduling
        scheduler.add_task(task_id="t1", title="Photo", categories=["photo"],
                          bounty_usd=5.0, deadline=datetime(...))
        batches = scheduler.compute_schedule()
        results = scheduler.execute_schedule(batches)
    """

    def __init__(
        self,
        coordinator=None,  # SwarmCoordinator (optional for testing)
        max_batch_size: int = 5,
        scheduling_interval_seconds: float = 30.0,
        enable_circuit_breakers: bool = True,
    ):
        self.coordinator = coordinator
        self.max_batch_size = max_batch_size
        self.scheduling_interval = scheduling_interval_seconds

        # Task pool
        self._tasks: dict[str, ScheduledTask] = {}

        # Subsystems
        self.retry_scheduler = RetryScheduler()
        self.load_balancer = AgentLoadBalancer()
        self._decisions: deque[SchedulingDecision] = deque(maxlen=500)

        # Circuit breakers
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        if enable_circuit_breakers:
            self._circuit_breakers["em_api"] = CircuitBreaker(
                "em_api", failure_threshold=5, recovery_timeout_seconds=60
            )
            self._circuit_breakers["autojob"] = CircuitBreaker(
                "autojob", failure_threshold=3, recovery_timeout_seconds=120
            )

        # Metrics
        self._cycles_run = 0
        self._tasks_scheduled = 0
        self._tasks_deferred = 0
        self._strategy_usage: dict[str, int] = defaultdict(int)
        self._last_cycle_at: Optional[float] = None

    # ─── Task Management ──────────────────────────────────────

    def add_task(
        self,
        task_id: str,
        title: str,
        categories: list[str],
        bounty_usd: float = 0.0,
        priority: TaskPriority = TaskPriority.NORMAL,
        deadline: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ) -> ScheduledTask:
        """Add a task to the scheduling pool."""
        task = ScheduledTask(
            task_id=task_id,
            title=title,
            categories=categories,
            bounty_usd=bounty_usd,
            priority=priority,
            deadline=deadline,
            created_at=created_at,
        )

        # Compute initial urgency and priority
        self._compute_urgency(task)
        self._compute_effective_priority(task)

        self._tasks[task_id] = task
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the scheduling pool."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self.retry_scheduler.clear(task_id)
            return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    @property
    def pending_count(self) -> int:
        return len(self._tasks)

    # ─── Urgency & Priority Computation ───────────────────────

    def _compute_urgency(self, task: ScheduledTask) -> None:
        """Compute deadline urgency for a task."""
        if task.deadline is None:
            task.urgency = UrgencyLevel.NORMAL
            return

        now = datetime.now(timezone.utc)
        if task.deadline.tzinfo is None:
            deadline = task.deadline.replace(tzinfo=timezone.utc)
        else:
            deadline = task.deadline

        remaining = (deadline - now).total_seconds() / 3600  # hours

        if remaining <= 0:
            task.urgency = UrgencyLevel.EXPIRED
        elif remaining <= 1:
            task.urgency = UrgencyLevel.CRITICAL
        elif remaining <= 4:
            task.urgency = UrgencyLevel.URGENT
        elif remaining <= 24:
            task.urgency = UrgencyLevel.NORMAL
        else:
            task.urgency = UrgencyLevel.RELAXED

    def _compute_effective_priority(self, task: ScheduledTask) -> None:
        """
        Compute effective priority score from multiple signals.

        Signals:
        1. Base priority (CRITICAL=4, HIGH=3, NORMAL=2, LOW=1)
        2. Deadline urgency multiplier
        3. Bounty value (higher bounty = slightly higher priority)
        4. Age penalty (older tasks get small boost to prevent starvation)
        5. Retry penalty (failed retries get deprioritized slightly)
        """
        # Base priority
        base_scores = {
            TaskPriority.CRITICAL: 4.0,
            TaskPriority.HIGH: 3.0,
            TaskPriority.NORMAL: 2.0,
            TaskPriority.LOW: 1.0,
        }
        base = base_scores.get(task.priority, 2.0)

        # Urgency multiplier
        urgency_mult = URGENCY_MULTIPLIERS.get(task.urgency, 1.0)

        # Bounty bonus (log scale, capped at +1.0)
        bounty_bonus = min(1.0, math.log10(max(task.bounty_usd, 1)) / 3)

        # Age bonus (prevent starvation — older tasks get +0.1 per hour, max +1.0)
        age_hours = 0.0
        if task.created_at:
            now = datetime.now(timezone.utc)
            if task.created_at.tzinfo is None:
                created = task.created_at.replace(tzinfo=timezone.utc)
            else:
                created = task.created_at
            age_hours = max(0, (now - created).total_seconds() / 3600)
        age_bonus = min(1.0, age_hours * 0.1)

        # Retry penalty (-0.2 per retry, max -1.0)
        retry_penalty = min(1.0, task.retry_count * 0.2)

        task.effective_priority = (
            base + bounty_bonus + age_bonus - retry_penalty
        ) * urgency_mult

    # ─── Dynamic Strategy Selection ───────────────────────────

    def _assess_swarm_conditions(self) -> SwarmConditions:
        """Assess current swarm state from the coordinator."""
        conditions = SwarmConditions()

        if self.coordinator is None:
            return conditions

        agents = self.coordinator.lifecycle.agents
        conditions.total_agents = len(agents)

        for record in agents.values():
            if record.state == AgentState.IDLE:
                conditions.idle_agents += 1
            elif record.state == AgentState.ACTIVE:
                conditions.active_agents += 1
            elif record.state == AgentState.WORKING:
                conditions.working_agents += 1
            elif record.state == AgentState.COOLDOWN:
                conditions.cooldown_agents += 1
            elif record.state == AgentState.DEGRADED:
                conditions.degraded_agents += 1
            elif record.state == AgentState.SUSPENDED:
                conditions.suspended_agents += 1

        # Budget utilization
        budget_utils = []
        for agent_id in agents:
            try:
                budget = self.coordinator.lifecycle.get_budget_status(agent_id)
                budget_utils.append(
                    max(budget["daily_pct"], budget["monthly_pct"]) / 100.0
                )
            except Exception:
                pass

        if budget_utils:
            conditions.avg_budget_utilization = sum(budget_utils) / len(budget_utils)

        conditions.pending_tasks = len(self._tasks)
        conditions.high_priority_pending = sum(
            1
            for t in self._tasks.values()
            if t.priority in (TaskPriority.CRITICAL, TaskPriority.HIGH)
        )

        return conditions

    def select_strategy(
        self,
        task: ScheduledTask,
        conditions: SwarmConditions,
    ) -> tuple[RoutingStrategy, str]:
        """
        Dynamically select the best routing strategy for a task.

        Returns (strategy, reason) tuple.

        Decision matrix:
        - SPECIALIST if task has specific category AND specialists available
        - BUDGET_AWARE if fleet budget utilization > 60%
        - ROUND_ROBIN if overloaded (spread work evenly)
        - BEST_FIT as default
        - CRITICAL tasks always use BEST_FIT (get the best agent ASAP)
        """
        # Critical urgency → always BEST_FIT
        if task.urgency in (UrgencyLevel.CRITICAL, UrgencyLevel.URGENT):
            return RoutingStrategy.BEST_FIT, "urgent task — best agent needed"

        # Critical priority → always BEST_FIT
        if task.priority == TaskPriority.CRITICAL:
            return RoutingStrategy.BEST_FIT, "critical priority — best agent needed"

        # High budget utilization → BUDGET_AWARE
        if conditions.avg_budget_utilization > 0.6:
            return RoutingStrategy.BUDGET_AWARE, (
                f"high budget utilization ({conditions.avg_budget_utilization:.0%})"
            )

        # Overloaded → ROUND_ROBIN
        if conditions.is_overloaded:
            return RoutingStrategy.ROUND_ROBIN, (
                f"overloaded (load factor: {conditions.load_factor:.1f})"
            )

        # Specialist categories → SPECIALIST
        specialist_categories = {
            "code_execution",
            "technical_task",
            "notarization",
            "research",
        }
        if any(cat in specialist_categories for cat in task.categories):
            return RoutingStrategy.SPECIALIST, (
                f"specialist category: {task.categories}"
            )

        # Default → BEST_FIT
        return RoutingStrategy.BEST_FIT, "default — best available agent"

    # ─── Schedule Computation ─────────────────────────────────

    def compute_schedule(self) -> list[SchedulingBatch]:
        """
        Compute the optimal scheduling plan for all pending tasks.

        Steps:
        1. Refresh urgency/priority for all tasks
        2. Filter out expired and ineligible tasks
        3. Group by category for batch routing
        4. Sort batches by max urgency/priority
        5. Select strategy per batch

        Returns ordered list of SchedulingBatch to execute.
        """
        now = time.time()
        conditions = self._assess_swarm_conditions()

        # 1. Refresh all tasks
        eligible = []
        for task in self._tasks.values():
            self._compute_urgency(task)
            self._compute_effective_priority(task)

            # Skip expired tasks
            if task.urgency == UrgencyLevel.EXPIRED:
                self._record_decision(
                    task, RoutingStrategy.BEST_FIT, "expired", "expired"
                )
                continue

            # Skip tasks in backoff
            if task.next_eligible_at and now < task.next_eligible_at:
                self._record_decision(
                    task, RoutingStrategy.BEST_FIT, "in backoff", "deferred"
                )
                self._tasks_deferred += 1
                continue

            eligible.append(task)

        if not eligible:
            return []

        # 2. Sort by effective priority (descending)
        eligible.sort(key=lambda t: t.effective_priority, reverse=True)

        # 3. Group into batches by category
        batch_groups: dict[str, list[ScheduledTask]] = defaultdict(list)
        for task in eligible:
            batch_groups[task.batch_key].append(task)

        # 4. Create batches with strategy selection
        batches = []
        batch_counter = 0
        for category_key, tasks in batch_groups.items():
            # Split into max_batch_size chunks
            for i in range(0, len(tasks), self.max_batch_size):
                chunk = tasks[i : i + self.max_batch_size]
                batch_counter += 1

                # Use highest-priority task in batch for strategy selection
                representative = chunk[0]
                strategy, reason = self.select_strategy(representative, conditions)

                batch = SchedulingBatch(
                    batch_id=f"batch-{batch_counter}-{int(now)}",
                    category_key=category_key,
                    tasks=chunk,
                    strategy=strategy,
                )

                # Record decisions
                for task in chunk:
                    task.recommended_strategy = strategy
                    self._record_decision(task, strategy, reason, "scheduled")

                batches.append(batch)

        # 5. Sort batches by max urgency and priority
        urgency_order = {
            UrgencyLevel.CRITICAL: 4,
            UrgencyLevel.URGENT: 3,
            UrgencyLevel.NORMAL: 2,
            UrgencyLevel.RELAXED: 1,
            UrgencyLevel.EXPIRED: 0,
        }
        batches.sort(
            key=lambda b: (
                max(urgency_order.get(t.urgency, 0) for t in b.tasks),
                max(t.effective_priority for t in b.tasks),
            ),
            reverse=True,
        )

        return batches

    def execute_schedule(
        self,
        batches: list[SchedulingBatch],
    ) -> list[dict]:
        """
        Execute the scheduling plan by routing tasks through the coordinator.

        For each batch:
        1. Route tasks using the batch's selected strategy
        2. Record outcomes (assigned/failed)
        3. Handle retries for failures
        4. Update load balancer

        Returns list of result dicts.
        """
        if self.coordinator is None:
            return [{"error": "No coordinator configured"}]

        results = []

        for batch in batches:
            for task in batch.tasks:
                # Check circuit breaker
                em_breaker = self._circuit_breakers.get("em_api")
                if em_breaker and not em_breaker.allow_request():
                    results.append(
                        {
                            "task_id": task.task_id,
                            "outcome": "circuit_open",
                            "reason": "EM API circuit breaker open",
                        }
                    )
                    continue

                # Create task request
                request = TaskRequest(
                    task_id=task.task_id,
                    title=task.title,
                    categories=task.categories,
                    bounty_usd=task.bounty_usd,
                    priority=task.priority,
                    deadline=task.deadline,
                )

                # Route via orchestrator
                result = self.coordinator.orchestrator.route_task(
                    request, strategy=batch.strategy
                )

                if isinstance(result, Assignment):
                    # Success
                    self.load_balancer.record_assignment(result.agent_id)
                    self.retry_scheduler.clear(task.task_id)
                    self._strategy_usage[batch.strategy.value] += 1
                    self._tasks_scheduled += 1

                    if em_breaker:
                        em_breaker.record_success()

                    # Remove from pool
                    self._tasks.pop(task.task_id, None)

                    results.append(
                        {
                            "task_id": task.task_id,
                            "outcome": "assigned",
                            "agent_id": result.agent_id,
                            "agent_name": result.agent_name,
                            "score": round(result.score, 2),
                            "strategy": batch.strategy.value,
                        }
                    )
                else:
                    # Failure — schedule retry
                    task.retry_count += 1
                    task.last_attempt_at = time.time()

                    if self.retry_scheduler.should_retry(
                        task.task_id, task.retry_count
                    ):
                        task.next_eligible_at = (
                            self.retry_scheduler.get_next_eligible_time(
                                task.task_id, task.retry_count
                            )
                        )
                        outcome = "retry_scheduled"
                    else:
                        outcome = "max_retries_exceeded"
                        self._tasks.pop(task.task_id, None)

                    if em_breaker:
                        em_breaker.record_failure()

                    results.append(
                        {
                            "task_id": task.task_id,
                            "outcome": outcome,
                            "reason": result.reason,
                            "retry_count": task.retry_count,
                        }
                    )

        return results

    def run_scheduling_cycle(self) -> dict:
        """
        Run a complete scheduling cycle: compute + execute.

        This is the main entry point for periodic scheduling.
        Returns a summary of the cycle.
        """
        self._cycles_run += 1
        self._last_cycle_at = time.time()

        batches = self.compute_schedule()
        if not batches:
            return {
                "cycle": self._cycles_run,
                "batches": 0,
                "tasks_processed": 0,
                "tasks_assigned": 0,
                "tasks_failed": 0,
                "tasks_remaining": len(self._tasks),
                "results": [],
            }

        results = self.execute_schedule(batches)

        assigned = sum(1 for r in results if r.get("outcome") == "assigned")
        failed = sum(1 for r in results if r.get("outcome") != "assigned")

        return {
            "cycle": self._cycles_run,
            "batches": len(batches),
            "tasks_processed": len(results),
            "tasks_assigned": assigned,
            "tasks_failed": failed,
            "tasks_remaining": len(self._tasks),
            "results": results,
        }

    # ─── Decision Recording ───────────────────────────────────

    def _record_decision(
        self,
        task: ScheduledTask,
        strategy: RoutingStrategy,
        reason: str,
        outcome: str,
    ) -> None:
        """Record a scheduling decision for audit."""
        self._decisions.append(
            SchedulingDecision(
                task_id=task.task_id,
                urgency=task.urgency.value,
                effective_priority=round(task.effective_priority, 3),
                chosen_strategy=strategy.value,
                reason=reason,
                outcome=outcome,
            )
        )

    # ─── Status & Metrics ────────────────────────────────────

    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            "pending_tasks": len(self._tasks),
            "cycles_run": self._cycles_run,
            "tasks_scheduled": self._tasks_scheduled,
            "tasks_deferred": self._tasks_deferred,
            "last_cycle_at": self._last_cycle_at,
            "scheduling_interval": self.scheduling_interval,
            "strategy_usage": dict(self._strategy_usage),
            "circuit_breakers": {
                name: cb.get_status() for name, cb in self._circuit_breakers.items()
            },
            "load_balancer": {
                "window_seconds": self.load_balancer.window_seconds,
                "max_tasks_per_window": self.load_balancer.max_tasks,
            },
            "retry_scheduler": {
                "max_retries": self.retry_scheduler.max_retries,
                "base_delay": self.retry_scheduler.base_delay,
            },
        }

    def get_decisions(self, limit: int = 50) -> list[dict]:
        """Get recent scheduling decisions."""
        decisions = list(self._decisions)[-limit:]
        return [
            {
                "task_id": d.task_id,
                "urgency": d.urgency,
                "priority": round(d.effective_priority, 3),
                "strategy": d.chosen_strategy,
                "reason": d.reason,
                "outcome": d.outcome,
                "timestamp": d.timestamp,
            }
            for d in decisions
        ]

    def get_urgency_distribution(self) -> dict:
        """Get distribution of urgency levels across pending tasks."""
        dist = defaultdict(int)
        for task in self._tasks.values():
            dist[task.urgency.value] += 1
        return dict(dist)
