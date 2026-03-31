"""
BatchScheduler — Intelligent Task Batching for Multi-Task Routing
==================================================================

Module #59 in the KK V2 Swarm.

Groups incoming tasks into optimized batches before routing. Rather
than routing tasks one-by-one (N routing cycles for N tasks), the
BatchScheduler identifies natural groupings and routes them together,
reducing chain-switch overhead, gas costs, and routing latency.

Architecture:

    ┌──────────────────────────────────────────────────────────┐
    │                    BatchScheduler                         │
    │                                                           │
    │  Incoming Tasks ──► [Grouping Strategy] ──► Batch Plan   │
    │                          │                      │         │
    │                    ┌─────┴──────┐               │         │
    │                    │ Strategy   │               ▼         │
    │                    │ Selection  │         ┌──────────┐    │
    │                    │            │         │  Batches  │    │
    │                    │ • chain    │         │  [{...}]  │    │
    │                    │ • skill    │         │  [{...}]  │    │
    │                    │ • deadline │         │  [{...}]  │    │
    │                    │ • bounty   │         └──────────┘    │
    │                    │ • hybrid   │               │         │
    │                    └────────────┘               ▼         │
    │                                         BatchPlan        │
    │                                    (order + rationale)    │
    └──────────────────────────────────────────────────────────┘

Batching Strategies:
    1. CHAIN — Group tasks by target network (Base, Polygon, etc.)
    2. SKILL — Group tasks requiring similar skills
    3. DEADLINE — Group tasks by deadline urgency tiers
    4. BOUNTY — Group tasks by bounty tier (micro/small/medium/large)
    5. HYBRID — Multi-factor grouping (weighted chain + skill + deadline)

Usage:
    from mcp_server.swarm.batch_scheduler import BatchScheduler

    scheduler = BatchScheduler(strategy=BatchStrategy.HYBRID)

    # Add tasks
    scheduler.add_tasks(tasks)

    # Generate batch plan
    plan = scheduler.plan()

    # Iterate batches in priority order
    for batch in plan.batches:
        print(f"Batch '{batch.label}': {len(batch.tasks)} tasks on {batch.chain}")
        pipeline.process_batch(batch.tasks)

    # Metrics
    print(scheduler.metrics())
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger("em.swarm.batch_scheduler")


# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

DEFAULT_MAX_BATCH_SIZE = 50
DEFAULT_MIN_BATCH_SIZE = 1
DEFAULT_URGENCY_HOURS = [1, 6, 24, 168]  # 1h, 6h, 24h, 1 week

BOUNTY_TIERS = {
    "micro": (0.0, 1.0),
    "small": (1.0, 10.0),
    "medium": (10.0, 100.0),
    "large": (100.0, float("inf")),
}

HYBRID_WEIGHTS = {
    "chain": 0.40,
    "skill": 0.30,
    "deadline": 0.20,
    "bounty": 0.10,
}


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────


class BatchStrategy(str, Enum):
    """Strategy for grouping tasks into batches."""

    CHAIN = "chain"
    SKILL = "skill"
    DEADLINE = "deadline"
    BOUNTY = "bounty"
    HYBRID = "hybrid"


class BatchPriority(str, Enum):
    """Priority classification for batch execution order."""

    CRITICAL = "critical"  # Expiring soon, high bounty
    HIGH = "high"  # Urgent deadline or large bounty
    NORMAL = "normal"  # Standard processing
    LOW = "low"  # No deadline pressure, small bounty
    DEFERRED = "deferred"  # Can wait — no urgency signals


@dataclass
class BatchTask:
    """Normalized task representation for batching."""

    task_id: str
    title: str = ""
    description: str = ""
    bounty: float = 0.0
    chain: str = "base"
    skills: list = field(default_factory=list)
    deadline: Optional[datetime] = None
    evidence_types: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "BatchTask":
        """Create BatchTask from a raw task dictionary."""
        deadline = None
        if d.get("deadline"):
            try:
                if isinstance(d["deadline"], datetime):
                    deadline = d["deadline"]
                elif isinstance(d["deadline"], str):
                    deadline = datetime.fromisoformat(
                        d["deadline"].replace("Z", "+00:00")
                    )
                elif isinstance(d["deadline"], (int, float)):
                    deadline = datetime.fromtimestamp(d["deadline"], tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                pass

        skills = d.get("skills", d.get("required_skills", []))
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]

        return cls(
            task_id=str(d.get("task_id", d.get("id", ""))),
            title=str(d.get("title", "")),
            description=str(d.get("description", "")),
            bounty=float(d.get("bounty", d.get("bounty_amount", 0.0))),
            chain=str(d.get("chain", d.get("network", "base"))).lower(),
            skills=skills if isinstance(skills, list) else [],
            deadline=deadline,
            evidence_types=d.get("evidence_types", []),
            raw=d,
        )


@dataclass
class Batch:
    """A group of tasks to be routed together."""

    batch_id: str
    label: str
    strategy: str
    tasks: list  # list[BatchTask]
    priority: BatchPriority = BatchPriority.NORMAL
    chain: Optional[str] = None
    skill_cluster: Optional[str] = None
    deadline_tier: Optional[str] = None
    bounty_tier: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.tasks)

    @property
    def total_bounty(self) -> float:
        return sum(t.bounty for t in self.tasks)

    @property
    def avg_bounty(self) -> float:
        return self.total_bounty / max(self.size, 1)

    def to_dict(self) -> dict:
        return {
            "batch_id": self.batch_id,
            "label": self.label,
            "strategy": self.strategy,
            "size": self.size,
            "priority": self.priority.value,
            "total_bounty": round(self.total_bounty, 4),
            "avg_bounty": round(self.avg_bounty, 4),
            "chain": self.chain,
            "skill_cluster": self.skill_cluster,
            "deadline_tier": self.deadline_tier,
            "bounty_tier": self.bounty_tier,
            "task_ids": [t.task_id for t in self.tasks],
        }


@dataclass
class BatchPlan:
    """Complete batch plan with ordered batches and rationale."""

    batches: list  # list[Batch], ordered by priority
    strategy: BatchStrategy
    total_tasks: int
    planning_time_ms: float
    rationale: str = ""
    unbatched: list = field(default_factory=list)  # tasks that couldn't be grouped

    @property
    def batch_count(self) -> int:
        return len(self.batches)

    @property
    def batched_tasks(self) -> int:
        return sum(b.size for b in self.batches)

    @property
    def efficiency(self) -> float:
        """Ratio of tasks batched vs total. 1.0 = perfect batching."""
        return self.batched_tasks / max(self.total_tasks, 1)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.value,
            "batch_count": self.batch_count,
            "total_tasks": self.total_tasks,
            "batched_tasks": self.batched_tasks,
            "unbatched_tasks": len(self.unbatched),
            "efficiency": round(self.efficiency, 4),
            "planning_time_ms": round(self.planning_time_ms, 2),
            "rationale": self.rationale,
            "batches": [b.to_dict() for b in self.batches],
        }


# ──────────────────────────────────────────────────────────────
# Priority Ordering
# ──────────────────────────────────────────────────────────────

_PRIORITY_ORDER = {
    BatchPriority.CRITICAL: 0,
    BatchPriority.HIGH: 1,
    BatchPriority.NORMAL: 2,
    BatchPriority.LOW: 3,
    BatchPriority.DEFERRED: 4,
}


def _priority_sort_key(batch: Batch) -> tuple:
    """Sort key: priority first, then total bounty descending."""
    return (_PRIORITY_ORDER.get(batch.priority, 99), -batch.total_bounty)


# ──────────────────────────────────────────────────────────────
# Core
# ──────────────────────────────────────────────────────────────


class BatchScheduler:
    """Intelligent task batching for multi-task routing optimization."""

    def __init__(
        self,
        strategy: BatchStrategy = BatchStrategy.HYBRID,
        max_batch_size: int = DEFAULT_MAX_BATCH_SIZE,
        min_batch_size: int = DEFAULT_MIN_BATCH_SIZE,
        urgency_hours: Optional[list] = None,
        bounty_tiers: Optional[dict] = None,
        hybrid_weights: Optional[dict] = None,
    ):
        self._strategy = strategy
        self._max_batch_size = max_batch_size
        self._min_batch_size = min_batch_size
        self._urgency_hours = urgency_hours or DEFAULT_URGENCY_HOURS
        self._bounty_tiers = bounty_tiers or BOUNTY_TIERS
        self._hybrid_weights = hybrid_weights or HYBRID_WEIGHTS.copy()

        self._tasks: list[BatchTask] = []
        self._batch_counter = 0
        self._plan_history: list[dict] = []
        self._stats = {
            "plans_generated": 0,
            "total_tasks_batched": 0,
            "total_batches_created": 0,
            "avg_batch_size": 0.0,
            "avg_planning_time_ms": 0.0,
            "strategy_usage": defaultdict(int),
        }

    # ── Task Ingestion ──────────────────────────────────────

    def add_task(self, task: dict) -> BatchTask:
        """Add a single task for batching."""
        bt = BatchTask.from_dict(task)
        self._tasks.append(bt)
        return bt

    def add_tasks(self, tasks: list[dict]) -> list[BatchTask]:
        """Add multiple tasks for batching."""
        return [self.add_task(t) for t in tasks]

    def clear_tasks(self):
        """Remove all pending tasks."""
        self._tasks.clear()

    @property
    def pending_count(self) -> int:
        return len(self._tasks)

    @property
    def strategy(self) -> BatchStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, value: BatchStrategy):
        self._strategy = value

    # ── Planning ────────────────────────────────────────────

    def plan(self, strategy: Optional[BatchStrategy] = None) -> BatchPlan:
        """Generate a batch plan for all pending tasks."""
        effective_strategy = strategy or self._strategy
        start = time.monotonic()

        if not self._tasks:
            return BatchPlan(
                batches=[],
                strategy=effective_strategy,
                total_tasks=0,
                planning_time_ms=0.0,
                rationale="No tasks to batch.",
            )

        if effective_strategy == BatchStrategy.CHAIN:
            batches, unbatched, rationale = self._plan_by_chain()
        elif effective_strategy == BatchStrategy.SKILL:
            batches, unbatched, rationale = self._plan_by_skill()
        elif effective_strategy == BatchStrategy.DEADLINE:
            batches, unbatched, rationale = self._plan_by_deadline()
        elif effective_strategy == BatchStrategy.BOUNTY:
            batches, unbatched, rationale = self._plan_by_bounty()
        elif effective_strategy == BatchStrategy.HYBRID:
            batches, unbatched, rationale = self._plan_hybrid()
        else:
            batches, unbatched, rationale = (
                [self._make_single_batch(self._tasks)],
                [],
                "Fallback: single batch",
            )

        # Assign priorities
        for batch in batches:
            batch.priority = self._compute_priority(batch)

        # Sort by priority
        batches.sort(key=_priority_sort_key)

        elapsed_ms = (time.monotonic() - start) * 1000.0
        plan = BatchPlan(
            batches=batches,
            strategy=effective_strategy,
            total_tasks=len(self._tasks),
            planning_time_ms=elapsed_ms,
            rationale=rationale,
            unbatched=unbatched,
        )

        # Update stats
        self._stats["plans_generated"] += 1
        self._stats["total_tasks_batched"] += plan.batched_tasks
        self._stats["total_batches_created"] += plan.batch_count
        self._stats["strategy_usage"][effective_strategy.value] += 1

        total_plans = self._stats["plans_generated"]
        self._stats["avg_batch_size"] = self._stats["total_tasks_batched"] / max(
            self._stats["total_batches_created"], 1
        )
        prev_avg = self._stats["avg_planning_time_ms"]
        self._stats["avg_planning_time_ms"] = (
            prev_avg * (total_plans - 1) + elapsed_ms
        ) / total_plans

        # Record in history
        self._plan_history.append(
            {
                "timestamp": time.time(),
                "strategy": effective_strategy.value,
                "tasks": plan.total_tasks,
                "batches": plan.batch_count,
                "efficiency": plan.efficiency,
                "planning_time_ms": elapsed_ms,
            }
        )

        # Trim history to 100 entries
        if len(self._plan_history) > 100:
            self._plan_history = self._plan_history[-100:]

        return plan

    # ── Strategy Implementations ────────────────────────────

    def _plan_by_chain(self) -> tuple:
        """Group tasks by target blockchain network."""
        groups = defaultdict(list)
        for task in self._tasks:
            groups[task.chain].append(task)

        batches = []
        unbatched = []
        for chain, tasks in sorted(groups.items(), key=lambda x: -len(x[1])):
            for chunk in self._chunk_tasks(tasks):
                if len(chunk) >= self._min_batch_size:
                    batch = self._make_batch(
                        tasks=chunk,
                        label=f"chain:{chain}",
                        strategy="chain",
                        chain=chain,
                    )
                    batches.append(batch)
                else:
                    unbatched.extend(chunk)

        chains_used = len(groups)
        rationale = (
            f"Grouped {len(self._tasks)} tasks across {chains_used} chains. "
            f"Largest chain group: {max(len(v) for v in groups.values())} tasks."
        )
        return batches, unbatched, rationale

    def _plan_by_skill(self) -> tuple:
        """Group tasks by primary skill requirement."""
        groups = defaultdict(list)
        no_skill = []
        for task in self._tasks:
            if task.skills:
                primary = task.skills[0].lower().strip()
                groups[primary].append(task)
            else:
                no_skill.append(task)

        batches = []
        unbatched = []

        for skill, tasks in sorted(groups.items(), key=lambda x: -len(x[1])):
            for chunk in self._chunk_tasks(tasks):
                if len(chunk) >= self._min_batch_size:
                    batch = self._make_batch(
                        tasks=chunk,
                        label=f"skill:{skill}",
                        strategy="skill",
                        skill_cluster=skill,
                    )
                    batches.append(batch)
                else:
                    unbatched.extend(chunk)

        # Handle tasks with no skills
        if no_skill:
            if len(no_skill) >= self._min_batch_size:
                batch = self._make_batch(
                    tasks=no_skill,
                    label="skill:unspecified",
                    strategy="skill",
                    skill_cluster="unspecified",
                )
                batches.append(batch)
            else:
                unbatched.extend(no_skill)

        skills_found = len(groups) + (1 if no_skill else 0)
        rationale = (
            f"Grouped {len(self._tasks)} tasks across {skills_found} skill clusters. "
            f"{len(no_skill)} tasks had no skills specified."
        )
        return batches, unbatched, rationale

    def _plan_by_deadline(self) -> tuple:
        """Group tasks by deadline urgency tier."""
        now = datetime.now(timezone.utc)
        tiers = defaultdict(list)

        for task in self._tasks:
            tier = self._get_deadline_tier(task, now)
            tiers[tier].append(task)

        # Order tiers by urgency
        tier_order = ["overdue", "critical", "urgent", "standard", "relaxed", "none"]
        batches = []
        unbatched = []

        for tier in tier_order:
            tasks = tiers.get(tier, [])
            if not tasks:
                continue
            for chunk in self._chunk_tasks(tasks):
                if len(chunk) >= self._min_batch_size:
                    batch = self._make_batch(
                        tasks=chunk,
                        label=f"deadline:{tier}",
                        strategy="deadline",
                        deadline_tier=tier,
                    )
                    batches.append(batch)
                else:
                    unbatched.extend(chunk)

        tiers_used = sum(1 for t in tier_order if tiers.get(t))
        rationale = (
            f"Grouped {len(self._tasks)} tasks across {tiers_used} deadline tiers. "
            f"Overdue: {len(tiers.get('overdue', []))}, "
            f"Critical: {len(tiers.get('critical', []))}, "
            f"No deadline: {len(tiers.get('none', []))}."
        )
        return batches, unbatched, rationale

    def _plan_by_bounty(self) -> tuple:
        """Group tasks by bounty tier."""
        groups = defaultdict(list)
        for task in self._tasks:
            tier = self._get_bounty_tier(task.bounty)
            groups[tier].append(task)

        # Order tiers by max bounty descending (largest tier first)
        tier_order = sorted(
            groups.keys(),
            key=lambda t: -max((task.bounty for task in groups[t]), default=0),
        )
        batches = []
        unbatched = []

        for tier in tier_order:
            tasks = groups.get(tier, [])
            if not tasks:
                continue
            for chunk in self._chunk_tasks(tasks):
                if len(chunk) >= self._min_batch_size:
                    batch = self._make_batch(
                        tasks=chunk,
                        label=f"bounty:{tier}",
                        strategy="bounty",
                        bounty_tier=tier,
                    )
                    batches.append(batch)
                else:
                    unbatched.extend(chunk)

        tiers_used = len(tier_order)
        tier_summary = ", ".join(f"{t}: {len(groups[t])}" for t in tier_order)
        rationale = (
            f"Grouped {len(self._tasks)} tasks across {tiers_used} bounty tiers. "
            f"{tier_summary}."
        )
        return batches, unbatched, rationale

    def _plan_hybrid(self) -> tuple:
        """Multi-factor grouping using weighted similarity."""
        if len(self._tasks) <= 1:
            if self._tasks:
                batch = self._make_single_batch(self._tasks)
                return [batch], [], "Single task — no batching needed."
            return [], [], "No tasks."

        # Step 1: Primary grouping by chain (strongest signal)
        chain_groups = defaultdict(list)
        for task in self._tasks:
            chain_groups[task.chain].append(task)

        batches = []
        unbatched = []

        for chain, chain_tasks in chain_groups.items():
            if len(chain_tasks) <= 1:
                # Single-task chains: check if above min batch size
                if len(chain_tasks) >= self._min_batch_size:
                    batch = self._make_batch(
                        tasks=chain_tasks,
                        label=f"hybrid:{chain}",
                        strategy="hybrid",
                        chain=chain,
                    )
                    batches.append(batch)
                else:
                    unbatched.extend(chain_tasks)
                continue

            # Step 2: Within each chain, sub-group by skill similarity
            skill_groups = defaultdict(list)
            for task in chain_tasks:
                if task.skills:
                    primary = task.skills[0].lower().strip()
                else:
                    primary = "_none"
                skill_groups[primary].append(task)

            for skill, skill_tasks in skill_groups.items():
                # Step 3: Within each skill group, consider deadline urgency
                now = datetime.now(timezone.utc)
                urgent = []
                normal = []
                for task in skill_tasks:
                    tier = self._get_deadline_tier(task, now)
                    if tier in ("overdue", "critical", "urgent"):
                        urgent.append(task)
                    else:
                        normal.append(task)

                # Urgent tasks get their own batch
                for group, suffix in [(urgent, "urgent"), (normal, "normal")]:
                    if not group:
                        continue
                    for chunk in self._chunk_tasks(group):
                        if len(chunk) >= self._min_batch_size:
                            skill_label = skill if skill != "_none" else "general"
                            batch = self._make_batch(
                                tasks=chunk,
                                label=f"hybrid:{chain}/{skill_label}/{suffix}",
                                strategy="hybrid",
                                chain=chain,
                                skill_cluster=skill_label,
                                deadline_tier=suffix,
                            )
                            batches.append(batch)
                        else:
                            unbatched.extend(chunk)

        # Attempt to batch unbatched tasks together
        if unbatched and len(unbatched) >= self._min_batch_size:
            batch = self._make_batch(
                tasks=unbatched,
                label="hybrid:mixed",
                strategy="hybrid",
            )
            batches.append(batch)
            unbatched = []

        chains = len(chain_groups)
        rationale = (
            f"Hybrid grouping: {len(self._tasks)} tasks → {len(batches)} batches "
            f"across {chains} chains. Weights: chain={self._hybrid_weights['chain']}, "
            f"skill={self._hybrid_weights['skill']}, deadline={self._hybrid_weights['deadline']}, "
            f"bounty={self._hybrid_weights['bounty']}."
        )
        return batches, unbatched, rationale

    # ── Priority Computation ────────────────────────────────

    def _compute_priority(self, batch: Batch) -> BatchPriority:
        """Compute batch priority from task characteristics."""
        now = datetime.now(timezone.utc)

        has_overdue = False
        has_critical = False
        has_high_bounty = False
        total_bounty = batch.total_bounty

        for task in batch.tasks:
            tier = self._get_deadline_tier(task, now)
            if tier == "overdue":
                has_overdue = True
            elif tier == "critical":
                has_critical = True
            if task.bounty >= 100.0:
                has_high_bounty = True

        if has_overdue or (has_critical and has_high_bounty):
            return BatchPriority.CRITICAL
        if has_critical or has_high_bounty:
            return BatchPriority.HIGH
        if total_bounty >= 10.0 or batch.deadline_tier in ("urgent",):
            return BatchPriority.NORMAL
        if total_bounty < 1.0 and batch.size <= 2:
            return BatchPriority.DEFERRED
        if total_bounty < 5.0:
            return BatchPriority.LOW

        return BatchPriority.NORMAL

    # ── Helpers ─────────────────────────────────────────────

    def _get_deadline_tier(self, task: BatchTask, now: datetime) -> str:
        """Classify task deadline urgency."""
        if not task.deadline:
            return "none"

        delta = task.deadline - now
        hours = delta.total_seconds() / 3600.0

        if hours < 0:
            return "overdue"
        if hours <= self._urgency_hours[0]:  # 1h
            return "critical"
        if hours <= self._urgency_hours[1]:  # 6h
            return "urgent"
        if hours <= self._urgency_hours[2]:  # 24h
            return "standard"
        return "relaxed"

    def _get_bounty_tier(self, bounty: float) -> str:
        """Classify bounty amount into tier."""
        for tier, (low, high) in self._bounty_tiers.items():
            if low <= bounty < high:
                return tier
        return "micro"

    def _chunk_tasks(self, tasks: list) -> list:
        """Split task list into chunks of max_batch_size."""
        if not tasks:
            return []
        return [
            tasks[i : i + self._max_batch_size]
            for i in range(0, len(tasks), self._max_batch_size)
        ]

    def _make_batch(
        self,
        tasks: list,
        label: str,
        strategy: str,
        chain: Optional[str] = None,
        skill_cluster: Optional[str] = None,
        deadline_tier: Optional[str] = None,
        bounty_tier: Optional[str] = None,
    ) -> Batch:
        """Create a Batch with auto-incrementing ID."""
        self._batch_counter += 1
        return Batch(
            batch_id=f"batch-{self._batch_counter:04d}",
            label=label,
            strategy=strategy,
            tasks=list(tasks),
            chain=chain,
            skill_cluster=skill_cluster,
            deadline_tier=deadline_tier,
            bounty_tier=bounty_tier,
        )

    def _make_single_batch(self, tasks: list) -> Batch:
        """Create a catch-all batch for all tasks."""
        self._batch_counter += 1
        return Batch(
            batch_id=f"batch-{self._batch_counter:04d}",
            label="all",
            strategy="single",
            tasks=list(tasks),
        )

    # ── Metrics & Diagnostics ───────────────────────────────

    def metrics(self) -> dict:
        """Return scheduler metrics."""
        return {
            "plans_generated": self._stats["plans_generated"],
            "total_tasks_batched": self._stats["total_tasks_batched"],
            "total_batches_created": self._stats["total_batches_created"],
            "avg_batch_size": round(self._stats["avg_batch_size"], 2),
            "avg_planning_time_ms": round(self._stats["avg_planning_time_ms"], 3),
            "strategy_usage": dict(self._stats["strategy_usage"]),
            "pending_tasks": self.pending_count,
        }

    def diagnostics(self) -> dict:
        """Full diagnostic dump."""
        return {
            "config": {
                "strategy": self._strategy.value,
                "max_batch_size": self._max_batch_size,
                "min_batch_size": self._min_batch_size,
                "urgency_hours": self._urgency_hours,
                "bounty_tiers": {k: list(v) for k, v in self._bounty_tiers.items()},
                "hybrid_weights": self._hybrid_weights,
            },
            "metrics": self.metrics(),
            "recent_plans": self._plan_history[-10:],
        }

    # ── Persistence ─────────────────────────────────────────

    def save_state(self) -> dict:
        """Export scheduler state for persistence."""
        return {
            "version": 1,
            "strategy": self._strategy.value,
            "max_batch_size": self._max_batch_size,
            "min_batch_size": self._min_batch_size,
            "urgency_hours": self._urgency_hours,
            "bounty_tiers": {k: list(v) for k, v in self._bounty_tiers.items()},
            "hybrid_weights": self._hybrid_weights,
            "batch_counter": self._batch_counter,
            "stats": {
                "plans_generated": self._stats["plans_generated"],
                "total_tasks_batched": self._stats["total_tasks_batched"],
                "total_batches_created": self._stats["total_batches_created"],
                "avg_batch_size": self._stats["avg_batch_size"],
                "avg_planning_time_ms": self._stats["avg_planning_time_ms"],
                "strategy_usage": dict(self._stats["strategy_usage"]),
            },
            "plan_history": self._plan_history,
        }

    def load_state(self, state: dict):
        """Restore scheduler state from persistence."""
        if not state or state.get("version") != 1:
            logger.warning("Invalid or missing state version, skipping load")
            return

        self._strategy = BatchStrategy(state.get("strategy", "hybrid"))
        self._max_batch_size = state.get("max_batch_size", DEFAULT_MAX_BATCH_SIZE)
        self._min_batch_size = state.get("min_batch_size", DEFAULT_MIN_BATCH_SIZE)
        self._urgency_hours = state.get("urgency_hours", DEFAULT_URGENCY_HOURS)
        self._batch_counter = state.get("batch_counter", 0)
        self._plan_history = state.get("plan_history", [])

        if "bounty_tiers" in state:
            self._bounty_tiers = {k: tuple(v) for k, v in state["bounty_tiers"].items()}
        if "hybrid_weights" in state:
            self._hybrid_weights = state["hybrid_weights"]

        stats = state.get("stats", {})
        self._stats["plans_generated"] = stats.get("plans_generated", 0)
        self._stats["total_tasks_batched"] = stats.get("total_tasks_batched", 0)
        self._stats["total_batches_created"] = stats.get("total_batches_created", 0)
        self._stats["avg_batch_size"] = stats.get("avg_batch_size", 0.0)
        self._stats["avg_planning_time_ms"] = stats.get("avg_planning_time_ms", 0.0)
        for k, v in stats.get("strategy_usage", {}).items():
            self._stats["strategy_usage"][k] = v

    # ── Optimization Queries ────────────────────────────────

    def suggest_strategy(self) -> BatchStrategy:
        """Analyze pending tasks and suggest the best strategy."""
        if not self._tasks:
            return self._strategy

        chains = set(t.chain for t in self._tasks)
        skills = set(t.skills[0].lower() for t in self._tasks if t.skills)
        deadlines = sum(1 for t in self._tasks if t.deadline)

        chain_diversity = len(chains) / max(len(self._tasks), 1)
        skill_diversity = len(skills) / max(len(self._tasks), 1)
        deadline_coverage = deadlines / max(len(self._tasks), 1)

        # If most tasks target the same chain, chain grouping won't help
        if chain_diversity <= 0.25:
            # Low chain diversity → skills or deadline more useful
            if skill_diversity > 0.3:
                return BatchStrategy.SKILL
            if deadline_coverage > 0.5:
                return BatchStrategy.DEADLINE
            return BatchStrategy.BOUNTY

        # High chain diversity → chain grouping is valuable
        if chain_diversity > 0.5 and skill_diversity > 0.3:
            return BatchStrategy.HYBRID

        if chain_diversity > 0.3:
            return BatchStrategy.CHAIN

        return BatchStrategy.HYBRID

    def estimate_savings(self, plan: Optional[BatchPlan] = None) -> dict:
        """Estimate routing savings from batching vs individual routing."""
        if plan is None:
            plan = self.plan()

        # Assumptions: individual routing costs ~50ms per task
        # Batch routing costs ~50ms + 5ms per additional task
        individual_cost_ms = plan.total_tasks * 50.0
        batch_cost_ms = sum(50.0 + (b.size - 1) * 5.0 for b in plan.batches)

        saved_ms = max(0, individual_cost_ms - batch_cost_ms)
        pct_saved = saved_ms / max(individual_cost_ms, 1.0) * 100.0

        # Chain switch savings: each batch uses 1 chain vs N chain switches
        chain_switches_individual = len(set(t.chain for t in self._tasks)) - 1
        chain_switches_batched = plan.batch_count - 1

        return {
            "individual_routing_ms": round(individual_cost_ms, 1),
            "batched_routing_ms": round(batch_cost_ms, 1),
            "saved_ms": round(saved_ms, 1),
            "pct_saved": round(pct_saved, 1),
            "chain_switches_saved": max(
                0, chain_switches_individual - chain_switches_batched
            ),
            "batches_vs_individual": f"{plan.batch_count} vs {plan.total_tasks}",
        }
