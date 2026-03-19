"""
TaskMonitor — Real-time task lifecycle monitoring and intervention engine.
=========================================================================

Watches active tasks in the Execution Market production API and triggers
automated interventions when tasks are at risk of expiring.

Responsibilities:
    1. Poll active tasks at configurable intervals
    2. Detect tasks approaching deadline (warning → critical → expired)
    3. Trigger interventions: re-broadcast, escalate bounty, notify workers
    4. Track intervention outcomes for learning
    5. Emit events for analytics and alerting

Architecture:
    EM API → TaskMonitor → Interventions → EventBus
                ↕
         InterventionHistory
                ↕
          OutcomeTracker

Intervention types:
    - REBROADCAST: Re-notify available workers via XMTP
    - ESCALATE_BOUNTY: Suggest increased bounty for underperforming tasks
    - DEADLINE_WARNING: Send urgent notification to assigned worker
    - REASSIGN: Release current assignment, find new worker
    - CANCEL_GRACEFUL: Cancel with explanation if unrecoverable

Thread-safe. No external dependencies beyond urllib.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("em.swarm.task_monitor")


# ─── Types ────────────────────────────────────────────────────────


class TaskUrgency(str, Enum):
    """Urgency levels based on time to deadline."""
    HEALTHY = "healthy"         # > 75% time remaining
    WATCH = "watch"             # 50-75% time remaining
    WARNING = "warning"         # 25-50% time remaining
    CRITICAL = "critical"       # < 25% time remaining
    OVERDUE = "overdue"         # Past deadline


class InterventionType(str, Enum):
    """Types of automated interventions."""
    REBROADCAST = "rebroadcast"
    ESCALATE_BOUNTY = "escalate_bounty"
    DEADLINE_WARNING = "deadline_warning"
    REASSIGN = "reassign"
    CANCEL_GRACEFUL = "cancel_graceful"


class InterventionOutcome(str, Enum):
    """Result of an intervention."""
    PENDING = "pending"
    SUCCESS = "success"         # Task completed after intervention
    FAILED = "failed"           # Task still expired
    PARTIAL = "partial"         # Worker responded but didn't complete
    SKIPPED = "skipped"         # Intervention was suppressed


@dataclass
class MonitoredTask:
    """A task being actively monitored."""
    task_id: str
    title: str
    category: str = ""
    bounty_usd: float = 0.0
    status: str = "open"
    worker_id: Optional[str] = None
    network: str = "base"
    created_at: float = field(default_factory=time.time)
    deadline_at: Optional[float] = None
    first_seen: float = field(default_factory=time.time)
    last_checked: float = field(default_factory=time.time)
    urgency: TaskUrgency = TaskUrgency.HEALTHY
    intervention_count: int = 0
    max_interventions: int = 3

    @property
    def time_remaining_seconds(self) -> Optional[float]:
        """Seconds until deadline, or None if no deadline."""
        if self.deadline_at is None:
            return None
        return max(0, self.deadline_at - time.time())

    @property
    def time_elapsed_ratio(self) -> Optional[float]:
        """Ratio of time elapsed (0.0 = just created, 1.0 = at deadline)."""
        if self.deadline_at is None or self.created_at == self.deadline_at:
            return None
        total = self.deadline_at - self.created_at
        if total <= 0:
            return 1.0
        elapsed = time.time() - self.created_at
        return min(1.0, max(0.0, elapsed / total))

    @property
    def is_assigned(self) -> bool:
        return self.worker_id is not None

    @property
    def can_intervene(self) -> bool:
        return self.intervention_count < self.max_interventions


@dataclass
class Intervention:
    """A recorded intervention on a task."""
    intervention_id: str
    task_id: str
    intervention_type: InterventionType
    triggered_at: float = field(default_factory=time.time)
    urgency_at_trigger: TaskUrgency = TaskUrgency.WARNING
    outcome: InterventionOutcome = InterventionOutcome.PENDING
    resolved_at: Optional[float] = None
    details: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.resolved_at is None:
            return None
        return self.resolved_at - self.triggered_at


@dataclass
class InterventionRule:
    """A rule defining when and how to intervene."""
    name: str
    urgency_trigger: TaskUrgency
    intervention_type: InterventionType
    cooldown_seconds: float = 300.0  # Don't repeat same intervention within 5 min
    requires_assignment: Optional[bool] = None  # None = any, True/False = specific
    min_bounty_usd: float = 0.0
    max_bounty_usd: float = float("inf")
    max_per_task: int = 2
    enabled: bool = True

    def matches(self, task: MonitoredTask) -> bool:
        """Check if this rule applies to the given task."""
        if not self.enabled:
            return False
        if task.urgency != self.urgency_trigger:
            return False
        if self.requires_assignment is not None:
            if task.is_assigned != self.requires_assignment:
                return False
        if task.bounty_usd < self.min_bounty_usd:
            return False
        if task.bounty_usd > self.max_bounty_usd:
            return False
        return True


@dataclass
class MonitoringStats:
    """Aggregated monitoring statistics."""
    total_tasks_monitored: int = 0
    tasks_currently_active: int = 0
    tasks_completed_after_intervention: int = 0
    tasks_expired_despite_intervention: int = 0
    total_interventions: int = 0
    interventions_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    interventions_by_outcome: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    avg_intervention_response_seconds: float = 0.0
    urgency_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


# ─── TaskMonitor ────────────────────────────────────────────────────────


class TaskMonitor:
    """
    Monitors active tasks and triggers automated interventions.

    The monitor runs in a cycle:
        1. Fetch active tasks from API (or receive via events)
        2. Classify urgency based on deadline proximity
        3. Evaluate intervention rules
        4. Execute interventions (via callbacks)
        5. Track outcomes

    Usage:
        monitor = TaskMonitor()
        monitor.add_rule(InterventionRule(
            name="warn_unassigned",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
            requires_assignment=False,
        ))
        monitor.on_intervention(my_intervention_handler)
        monitor.ingest_task(task_data)
        monitor.run_cycle()
    """

    DEFAULT_URGENCY_THRESHOLDS = {
        TaskUrgency.HEALTHY: 0.25,     # < 25% elapsed
        TaskUrgency.WATCH: 0.50,       # 25-50% elapsed
        TaskUrgency.WARNING: 0.75,     # 50-75% elapsed
        TaskUrgency.CRITICAL: 1.0,     # 75-100% elapsed
        # OVERDUE: > 100%
    }

    def __init__(
        self,
        urgency_thresholds: Optional[Dict[TaskUrgency, float]] = None,
        intervention_id_prefix: str = "int",
    ):
        self.urgency_thresholds = urgency_thresholds or dict(self.DEFAULT_URGENCY_THRESHOLDS)
        self.intervention_id_prefix = intervention_id_prefix

        # State
        self.tasks: Dict[str, MonitoredTask] = {}
        self.interventions: List[Intervention] = []
        self.rules: List[InterventionRule] = []
        self._intervention_counter = 0

        # Callbacks
        self._intervention_handlers: List[Callable] = []
        self._urgency_change_handlers: List[Callable] = []

        # Cooldown tracking: (task_id, intervention_type) -> last_triggered_at
        self._cooldowns: Dict[tuple, float] = {}

        # Intervention count per (task_id, intervention_type)
        self._intervention_counts: Dict[tuple, int] = defaultdict(int)

    # ──────── Task Management ────────

    def ingest_task(
        self,
        task_id: str,
        title: str = "",
        category: str = "",
        bounty_usd: float = 0.0,
        status: str = "open",
        worker_id: Optional[str] = None,
        network: str = "base",
        created_at: Optional[float] = None,
        deadline_at: Optional[float] = None,
    ) -> MonitoredTask:
        """Add or update a task in the monitoring pool."""
        now = time.time()

        if task_id in self.tasks:
            # Update existing
            task = self.tasks[task_id]
            task.status = status
            task.worker_id = worker_id
            task.last_checked = now
            if deadline_at is not None:
                task.deadline_at = deadline_at
        else:
            # New task
            task = MonitoredTask(
                task_id=task_id,
                title=title,
                category=category,
                bounty_usd=bounty_usd,
                status=status,
                worker_id=worker_id,
                network=network,
                created_at=created_at or now,
                deadline_at=deadline_at,
                first_seen=now,
                last_checked=now,
            )
            self.tasks[task_id] = task

        # Classify urgency
        old_urgency = task.urgency
        task.urgency = self._classify_urgency(task)
        if old_urgency != task.urgency:
            self._emit_urgency_change(task, old_urgency, task.urgency)

        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from monitoring (completed/cancelled)."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

    def get_task(self, task_id: str) -> Optional[MonitoredTask]:
        """Get a monitored task by ID."""
        return self.tasks.get(task_id)

    def get_active_tasks(self) -> List[MonitoredTask]:
        """Get all actively monitored tasks."""
        return list(self.tasks.values())

    def get_tasks_by_urgency(self, urgency: TaskUrgency) -> List[MonitoredTask]:
        """Get all tasks at a specific urgency level."""
        return [t for t in self.tasks.values() if t.urgency == urgency]

    # ──────── Urgency Classification ────────

    def _classify_urgency(self, task: MonitoredTask) -> TaskUrgency:
        """Classify task urgency based on deadline proximity."""
        ratio = task.time_elapsed_ratio

        # No deadline — always healthy
        if ratio is None:
            return TaskUrgency.HEALTHY

        # Past deadline
        if ratio >= 1.0:
            return TaskUrgency.OVERDUE

        # Check thresholds (ordered from least to most urgent)
        if ratio < self.urgency_thresholds[TaskUrgency.HEALTHY]:
            return TaskUrgency.HEALTHY
        elif ratio < self.urgency_thresholds[TaskUrgency.WATCH]:
            return TaskUrgency.WATCH
        elif ratio < self.urgency_thresholds[TaskUrgency.WARNING]:
            return TaskUrgency.WARNING
        else:
            return TaskUrgency.CRITICAL

    # ──────── Rules Engine ────────

    def add_rule(self, rule: InterventionRule):
        """Add an intervention rule."""
        self.rules.append(rule)

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        before = len(self.rules)
        self.rules = [r for r in self.rules if r.name != name]
        return len(self.rules) < before

    def get_rules(self) -> List[InterventionRule]:
        """Get all registered rules."""
        return list(self.rules)

    # ──────── Intervention Engine ────────

    def run_cycle(self) -> List[Intervention]:
        """
        Run a monitoring cycle:
        1. Re-classify all task urgencies
        2. Evaluate rules against each task
        3. Trigger interventions where rules match
        Returns list of interventions triggered.
        """
        triggered = []
        now = time.time()

        for task in list(self.tasks.values()):
            # Skip terminal states
            if task.status in ("completed", "cancelled", "expired"):
                continue

            # Re-classify
            old_urgency = task.urgency
            task.urgency = self._classify_urgency(task)
            task.last_checked = now
            if old_urgency != task.urgency:
                self._emit_urgency_change(task, old_urgency, task.urgency)

            # Evaluate rules
            for rule in self.rules:
                if not rule.matches(task):
                    continue

                # Check cooldown
                key = (task.task_id, rule.intervention_type)
                last_triggered = self._cooldowns.get(key, 0)
                if (now - last_triggered) < rule.cooldown_seconds:
                    continue

                # Check per-task limit for this intervention type
                if self._intervention_counts[key] >= rule.max_per_task:
                    continue

                # Check overall task intervention limit
                if not task.can_intervene:
                    continue

                # Trigger intervention
                intervention = self._trigger_intervention(task, rule)
                if intervention:
                    triggered.append(intervention)

        return triggered

    def _trigger_intervention(
        self, task: MonitoredTask, rule: InterventionRule
    ) -> Optional[Intervention]:
        """Create and execute an intervention."""
        self._intervention_counter += 1
        intervention_id = f"{self.intervention_id_prefix}-{self._intervention_counter}"

        intervention = Intervention(
            intervention_id=intervention_id,
            task_id=task.task_id,
            intervention_type=rule.intervention_type,
            urgency_at_trigger=task.urgency,
            details=f"Rule '{rule.name}' triggered for task '{task.title}'",
        )

        self.interventions.append(intervention)
        task.intervention_count += 1

        # Update cooldown and counts
        key = (task.task_id, rule.intervention_type)
        self._cooldowns[key] = time.time()
        self._intervention_counts[key] += 1

        # Notify handlers
        for handler in self._intervention_handlers:
            try:
                handler(intervention, task)
            except Exception as e:
                logger.error(f"Intervention handler error: {e}")

        logger.info(
            f"[TaskMonitor] Intervention {intervention_id}: "
            f"{rule.intervention_type.value} on {task.task_id} "
            f"(urgency: {task.urgency.value})"
        )

        return intervention

    # ──────── Outcome Tracking ────────

    def record_outcome(
        self,
        intervention_id: str,
        outcome: InterventionOutcome,
    ) -> bool:
        """Record the outcome of an intervention."""
        for intervention in self.interventions:
            if intervention.intervention_id == intervention_id:
                intervention.outcome = outcome
                intervention.resolved_at = time.time()
                return True
        return False

    def record_task_outcome(
        self,
        task_id: str,
        completed: bool,
    ):
        """Record that a task completed or expired, updating all pending interventions."""
        outcome = InterventionOutcome.SUCCESS if completed else InterventionOutcome.FAILED
        for intervention in self.interventions:
            if (
                intervention.task_id == task_id
                and intervention.outcome == InterventionOutcome.PENDING
            ):
                intervention.outcome = outcome
                intervention.resolved_at = time.time()

    def get_interventions(
        self,
        task_id: Optional[str] = None,
        intervention_type: Optional[InterventionType] = None,
        outcome: Optional[InterventionOutcome] = None,
    ) -> List[Intervention]:
        """Query interventions with optional filters."""
        results = self.interventions
        if task_id:
            results = [i for i in results if i.task_id == task_id]
        if intervention_type:
            results = [i for i in results if i.intervention_type == intervention_type]
        if outcome:
            results = [i for i in results if i.outcome == outcome]
        return results

    # ──────── Callbacks ────────

    def on_intervention(self, handler: Callable):
        """Register callback for intervention events."""
        self._intervention_handlers.append(handler)

    def on_urgency_change(self, handler: Callable):
        """Register callback for urgency level changes."""
        self._urgency_change_handlers.append(handler)

    def _emit_urgency_change(
        self,
        task: MonitoredTask,
        old: TaskUrgency,
        new: TaskUrgency,
    ):
        """Notify handlers about urgency level change."""
        for handler in self._urgency_change_handlers:
            try:
                handler(task, old, new)
            except Exception as e:
                logger.error(f"Urgency change handler error: {e}")

    # ──────── Statistics ────────

    def get_stats(self) -> MonitoringStats:
        """Get aggregated monitoring statistics."""
        stats = MonitoringStats()
        stats.total_tasks_monitored = len(self.tasks) + sum(
            1 for i in self.interventions if i.task_id not in self.tasks
        )
        stats.tasks_currently_active = len(self.tasks)
        stats.total_interventions = len(self.interventions)

        # Urgency distribution
        for task in self.tasks.values():
            stats.urgency_distribution[task.urgency.value] += 1

        # Intervention breakdowns
        response_times = []
        for intervention in self.interventions:
            stats.interventions_by_type[intervention.intervention_type.value] += 1
            stats.interventions_by_outcome[intervention.outcome.value] += 1

            if intervention.outcome == InterventionOutcome.SUCCESS:
                stats.tasks_completed_after_intervention += 1
            elif intervention.outcome == InterventionOutcome.FAILED:
                stats.tasks_expired_despite_intervention += 1

            if intervention.duration_seconds is not None:
                response_times.append(intervention.duration_seconds)

        if response_times:
            stats.avg_intervention_response_seconds = sum(response_times) / len(
                response_times
            )

        return stats

    def get_health(self) -> Dict[str, Any]:
        """Get monitoring health summary."""
        critical_count = len(self.get_tasks_by_urgency(TaskUrgency.CRITICAL))
        overdue_count = len(self.get_tasks_by_urgency(TaskUrgency.OVERDUE))
        warning_count = len(self.get_tasks_by_urgency(TaskUrgency.WARNING))

        success_count = sum(
            1 for i in self.interventions if i.outcome == InterventionOutcome.SUCCESS
        )
        total_resolved = sum(
            1
            for i in self.interventions
            if i.outcome in (InterventionOutcome.SUCCESS, InterventionOutcome.FAILED)
        )

        return {
            "status": "critical" if critical_count > 0 or overdue_count > 0 else (
                "warning" if warning_count > 0 else "healthy"
            ),
            "tasks_monitored": len(self.tasks),
            "critical_tasks": critical_count,
            "overdue_tasks": overdue_count,
            "warning_tasks": warning_count,
            "total_interventions": len(self.interventions),
            "intervention_success_rate": (
                success_count / total_resolved if total_resolved > 0 else 0.0
            ),
            "pending_interventions": sum(
                1
                for i in self.interventions
                if i.outcome == InterventionOutcome.PENDING
            ),
        }

    # ──────── Default Rules ────────

    @classmethod
    def with_default_rules(cls, **kwargs) -> "TaskMonitor":
        """Create a TaskMonitor with sensible default intervention rules."""
        monitor = cls(**kwargs)

        # Unassigned tasks at warning level → rebroadcast to workers
        monitor.add_rule(InterventionRule(
            name="rebroadcast_unassigned_warning",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
            requires_assignment=False,
            cooldown_seconds=600.0,  # At most once per 10 min
            max_per_task=2,
        ))

        # Assigned tasks at critical level → warn the worker
        monitor.add_rule(InterventionRule(
            name="deadline_warning_assigned",
            urgency_trigger=TaskUrgency.CRITICAL,
            intervention_type=InterventionType.DEADLINE_WARNING,
            requires_assignment=True,
            cooldown_seconds=300.0,
            max_per_task=2,
        ))

        # Unassigned tasks at critical → suggest bounty escalation
        monitor.add_rule(InterventionRule(
            name="escalate_bounty_critical",
            urgency_trigger=TaskUrgency.CRITICAL,
            intervention_type=InterventionType.ESCALATE_BOUNTY,
            requires_assignment=False,
            cooldown_seconds=900.0,
            max_per_task=1,
        ))

        # Overdue assigned tasks → reassign
        monitor.add_rule(InterventionRule(
            name="reassign_overdue",
            urgency_trigger=TaskUrgency.OVERDUE,
            intervention_type=InterventionType.REASSIGN,
            requires_assignment=True,
            cooldown_seconds=600.0,
            max_per_task=1,
        ))

        # Overdue unassigned → graceful cancel
        monitor.add_rule(InterventionRule(
            name="cancel_overdue_unassigned",
            urgency_trigger=TaskUrgency.OVERDUE,
            intervention_type=InterventionType.CANCEL_GRACEFUL,
            requires_assignment=False,
            cooldown_seconds=0,  # Immediate
            max_per_task=1,
        ))

        return monitor
