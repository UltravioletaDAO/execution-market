from __future__ import annotations
"""
LoadBridge — Server-Side Sustainable Workload Distribution

Module #75 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's LoadBalancer (Signal #28).
Prevents worker overload by tracking active task assignments,
estimating worker capacity, and producing routing penalties for
workers approaching their limits.

The Winner-Take-All Problem
===========================

Without load balancing, a 28-signal routing system creates a
self-reinforcing loop: the best worker gets all tasks, gains more
experience, scores higher, gets MORE tasks, and eventually burns out.
Meanwhile, capable workers sit idle because they never got a chance.

This is the "thundering herd" problem from distributed systems applied
to human labor. And it's worse with humans because:
  - Humans fatigue (servers don't get tired)
  - Burnout is permanent (you can't reboot a person)
  - Humans have dignity (nobody wants to be a task factory)

Architecture
============

Three complementary mechanisms:

1. **Active Load Tracking** — Count in-progress tasks per worker
2. **Capacity Estimation** — EWMA of daily completion rates
3. **Load Penalty** — Sigmoid-shaped penalty curve:
   - 0-50%: no penalty (plenty of headroom)
   - 50-80%: gentle ramp (starting to get busy)
   - 80-100%: steep penalty (approaching limits)
   - >100%: max penalty (overloaded)

Additional features:
  - Cooling period after burst completions (TCP-style congestion control)
  - Task complexity weighting (notarized 2.5x, text_response 0.3x)
  - Fleet-wide utilization monitoring
  - Worker capacity profiling

Integration with SwarmCoordinator:
    coordinator.load_bridge.on_task_assigned(task_id, worker_id, task_type)
    coordinator.load_bridge.on_task_completed(task_id, worker_id, success)
    sig = coordinator.load_bridge.signal(worker_id)
    if sig.risk_level == "overloaded":
        skip_worker(worker_id)

Author: Clawd (Dream Session, April 4 2026)
"""

import json
import logging
import math
import os
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("swarm.load_bridge")

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class LoadBridgeConfig:
    """Configuration for the server-side LoadBridge."""

    # Penalty scaling
    max_penalty: float = 0.12

    # Capacity estimation
    default_capacity: float = 3.0
    min_capacity: float = 1.0
    max_capacity: float = 50.0
    ewma_alpha: float = 0.3

    # Utilization thresholds
    no_penalty_threshold: float = 0.50
    gentle_threshold: float = 0.80
    steep_threshold: float = 1.00
    overload_threshold: float = 1.20

    # Cooling mechanism
    enable_cooling: bool = True
    cooling_burst_count: int = 5
    cooling_window_seconds: float = 3600.0
    cooling_penalty: float = 0.03
    cooling_duration_seconds: float = 1800.0

    # Task complexity weights
    complexity_weights: dict[str, float] = field(default_factory=lambda: {
        "photo": 0.5,
        "photo_geo": 0.7,
        "video": 1.5,
        "document": 1.0,
        "receipt": 0.8,
        "signature": 1.2,
        "notarized": 2.5,
        "measurement": 1.0,
        "text_response": 0.3,
        "screenshot": 0.4,
    })

    # History
    history_decay_days: float = 14.0
    min_history_days: int = 3


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ActiveTask:
    """A task currently assigned to a worker."""
    task_id: str
    worker_id: str
    assigned_at: float
    complexity: float = 1.0
    task_type: str = ""


@dataclass
class CompletionEvent:
    """A task completion event."""
    task_id: str
    worker_id: str
    assigned_at: float
    completed_at: float
    complexity: float = 1.0
    success: bool = True
    duration_seconds: float = 0.0


@dataclass
class LoadSignal:
    """Load balancing signal for routing decisions."""
    worker_id: str
    load_penalty: float         # Negative (penalty) or 0.0
    utilization: float          # 0.0 to N (>1.0 = overloaded)
    active_tasks: int
    active_complexity: float    # Weighted task count
    estimated_capacity: float   # Daily throughput estimate
    capacity_confidence: float  # 0.0-1.0
    cooling_active: bool
    risk_level: str             # idle/light/moderate/heavy/overloaded
    recommendation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FleetUtilization:
    """Fleet-wide load status."""
    total_workers: int
    active_workers: int
    idle_workers: int
    overloaded_workers: int
    total_active_tasks: int
    avg_utilization: float
    capacity_headroom: float
    bottleneck_workers: list[str]

    def to_dict(self) -> dict:
        return {
            "total_workers": self.total_workers,
            "active_workers": self.active_workers,
            "idle_workers": self.idle_workers,
            "overloaded_workers": self.overloaded_workers,
            "total_active_tasks": self.total_active_tasks,
            "avg_utilization": round(self.avg_utilization, 4),
            "capacity_headroom": round(self.capacity_headroom, 2),
            "bottleneck_workers": self.bottleneck_workers,
        }


# ---------------------------------------------------------------------------
# LoadBridge
# ---------------------------------------------------------------------------

class LoadBridge:
    """
    Server-side load balancing intelligence for the KK V2 Swarm.

    Mirrors AutoJob's LoadBalancer (Signal #28) with server-side
    lifecycle hooks for the SwarmCoordinator.
    """

    def __init__(self, config: LoadBridgeConfig | None = None):
        self.config = config or LoadBridgeConfig()

        # Active assignments: worker_id → {task_id: ActiveTask}
        self._active: dict[str, dict[str, ActiveTask]] = defaultdict(dict)

        # Completion history: worker_id → [CompletionEvent]
        self._history: dict[str, list[CompletionEvent]] = defaultdict(list)

        # Capacity estimates: worker_id → float
        self._capacity: dict[str, float] = {}

        # Confidence: worker_id → float
        self._confidence: dict[str, float] = {}

        # Daily counts for EWMA: worker_id → {date_str: weighted_count}
        self._daily_counts: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

        # Recent completions for cooling: worker_id → [timestamp]
        self._recent_completions: dict[str, list[float]] = defaultdict(list)

        # Cooling state: worker_id → expires_at
        self._cooling_until: dict[str, float] = {}

        # Stats
        self._total_assignments = 0
        self._total_completions = 0
        self._total_expirations = 0

    # ----- Lifecycle Hooks (for SwarmCoordinator) -----

    def on_task_assigned(
        self,
        task_id: str,
        worker_id: str,
        task_type: str = "",
        complexity: float | None = None,
        assigned_at: float | None = None,
    ) -> LoadSignal:
        """Called when a task is assigned to a worker.

        Returns the current LoadSignal for the worker AFTER assignment.
        """
        assigned_at = assigned_at or time.time()

        # Resolve complexity
        if complexity is None:
            complexity = self.config.complexity_weights.get(task_type, 1.0)

        task = ActiveTask(
            task_id=task_id,
            worker_id=worker_id,
            assigned_at=assigned_at,
            complexity=complexity,
            task_type=task_type,
        )
        self._active[worker_id][task_id] = task
        self._total_assignments += 1

        logger.debug(
            f"Task {task_id} assigned to {worker_id[:10]}... "
            f"(complexity={complexity:.2f}, active={len(self._active[worker_id])})"
        )

        return self.signal(worker_id)

    def on_task_completed(
        self,
        task_id: str,
        worker_id: str,
        success: bool = True,
        completed_at: float | None = None,
    ) -> LoadSignal:
        """Called when a task is completed.

        Returns the updated LoadSignal after removing the task.
        """
        completed_at = completed_at or time.time()

        # Remove from active
        task = self._active.get(worker_id, {}).pop(task_id, None)

        assigned_at = task.assigned_at if task else completed_at - 3600
        complexity = task.complexity if task else 1.0

        # Record completion
        event = CompletionEvent(
            task_id=task_id,
            worker_id=worker_id,
            assigned_at=assigned_at,
            completed_at=completed_at,
            complexity=complexity,
            success=success,
            duration_seconds=completed_at - assigned_at,
        )
        self._history[worker_id].append(event)
        self._total_completions += 1

        # Update daily count
        day_str = datetime.fromtimestamp(completed_at, tz=UTC).strftime("%Y-%m-%d")
        self._daily_counts[worker_id][day_str] += complexity

        # Track for cooling
        self._recent_completions[worker_id].append(completed_at)
        if self.config.enable_cooling:
            self._check_cooling(worker_id, completed_at)

        # Recalculate capacity
        self._update_capacity(worker_id)

        return self.signal(worker_id)

    def on_task_expired(self, task_id: str, worker_id: str) -> None:
        """Called when a task expires or is cancelled."""
        self._active.get(worker_id, {}).pop(task_id, None)
        self._total_expirations += 1

    # ----- Signal Generation -----

    def signal(self, worker_id: str) -> LoadSignal:
        """Get load signal for a worker."""
        active = self._active.get(worker_id, {})
        active_count = len(active)
        active_complexity = sum(t.complexity for t in active.values())

        capacity = self._get_capacity(worker_id)
        confidence = self._confidence.get(worker_id, 0.0)

        utilization = active_complexity / capacity if capacity > 0 else 0.0

        now = time.time()
        cooling = (
            self.config.enable_cooling
            and worker_id in self._cooling_until
            and self._cooling_until[worker_id] > now
        )

        penalty = self._calculate_penalty(utilization, cooling, confidence)
        risk = self._classify_risk(utilization, cooling)
        recommendation = self._make_recommendation(
            utilization, active_count, capacity, cooling, risk
        )

        return LoadSignal(
            worker_id=worker_id,
            load_penalty=penalty,
            utilization=round(utilization, 4),
            active_tasks=active_count,
            active_complexity=round(active_complexity, 2),
            estimated_capacity=round(capacity, 2),
            capacity_confidence=round(confidence, 3),
            cooling_active=cooling,
            risk_level=risk,
            recommendation=recommendation,
        )

    # ----- Fleet Status -----

    def fleet_utilization(self) -> FleetUtilization:
        """Get fleet-wide load status."""
        all_workers = set(list(self._active.keys()) + list(self._capacity.keys()))
        active_list = []
        idle_list = []
        overloaded_list = []
        total_tasks = 0
        total_headroom = 0.0
        utilizations = []
        bottlenecks = []

        for worker in all_workers:
            sig = self.signal(worker)
            total_tasks += sig.active_tasks

            if sig.active_tasks > 0:
                active_list.append(worker)
                utilizations.append(sig.utilization)
                remaining = sig.estimated_capacity - sig.active_complexity
                total_headroom += max(0.0, remaining)
                if sig.utilization > 1.0:
                    overloaded_list.append(worker)
                if sig.utilization > 0.9:
                    bottlenecks.append(worker)
            else:
                idle_list.append(worker)
                total_headroom += sig.estimated_capacity

        avg_util = sum(utilizations) / len(utilizations) if utilizations else 0.0

        return FleetUtilization(
            total_workers=len(all_workers),
            active_workers=len(active_list),
            idle_workers=len(idle_list),
            overloaded_workers=len(overloaded_list),
            total_active_tasks=total_tasks,
            avg_utilization=avg_util,
            capacity_headroom=total_headroom,
            bottleneck_workers=bottlenecks[:10],
        )

    def get_least_loaded(
        self,
        worker_ids: list[str],
        top_n: int = 3,
    ) -> list[LoadSignal]:
        """Get least loaded workers from a list (for tie-breaking)."""
        signals = [self.signal(w) for w in worker_ids]
        signals.sort(key=lambda s: s.utilization)
        return signals[:top_n]

    def worker_profile(self, worker_id: str, days: int = 7) -> dict:
        """Get detailed load profile for a worker."""
        now = time.time()
        cutoff = now - (days * 86400)

        history = self._history.get(worker_id, [])
        recent = [h for h in history if h.completed_at >= cutoff]

        daily = defaultdict(lambda: {"count": 0, "complexity": 0.0, "successes": 0})
        for event in recent:
            day = datetime.fromtimestamp(event.completed_at, tz=UTC).strftime("%Y-%m-%d")
            daily[day]["count"] += 1
            daily[day]["complexity"] += event.complexity
            if event.success:
                daily[day]["successes"] += 1

        avg_duration = 0.0
        if recent:
            durations = [e.duration_seconds for e in recent if e.duration_seconds > 0]
            avg_duration = sum(durations) / len(durations) if durations else 0.0

        return {
            "worker_id": worker_id,
            "period_days": days,
            "total_completions": len(recent),
            "estimated_capacity": self._get_capacity(worker_id),
            "capacity_confidence": self._confidence.get(worker_id, 0.0),
            "current_active": len(self._active.get(worker_id, {})),
            "avg_duration_seconds": round(avg_duration, 1),
            "daily_breakdown": dict(daily),
        }

    # ----- Health & Status -----

    def health(self) -> dict:
        """Health check endpoint."""
        fleet = self.fleet_utilization()
        return {
            "status": "operational",
            "module": "load_bridge",
            "module_number": 75,
            "signal_number": 28,
            "tracked_workers": fleet.total_workers,
            "active_assignments": fleet.total_active_tasks,
            "total_assignments": self._total_assignments,
            "total_completions": self._total_completions,
            "total_expirations": self._total_expirations,
            "capacity_estimates": len(self._capacity),
            "cooling_active": sum(
                1 for t in self._cooling_until.values() if t > time.time()
            ),
            "fleet_utilization": round(fleet.avg_utilization, 4),
        }

    # ----- Persistence -----

    def save(self, path: str) -> None:
        """Save state to JSON."""
        state = {
            "version": 1,
            "module": "load_bridge",
            "module_number": 75,
            "saved_at": time.time(),
            "capacity": self._capacity,
            "confidence": self._confidence,
            "daily_counts": {
                w: dict(d) for w, d in self._daily_counts.items()
            },
            "active": {
                w: {
                    t: {
                        "task_id": a.task_id,
                        "worker_id": a.worker_id,
                        "assigned_at": a.assigned_at,
                        "complexity": a.complexity,
                        "task_type": a.task_type,
                    }
                    for t, a in tasks.items()
                }
                for w, tasks in self._active.items()
            },
            "stats": {
                "total_assignments": self._total_assignments,
                "total_completions": self._total_completions,
                "total_expirations": self._total_expirations,
            },
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        logger.info(f"LoadBridge state saved to {path}")

    def load(self, path: str) -> None:
        """Load state from JSON."""
        if not os.path.exists(path):
            return

        try:
            with open(path) as f:
                state = json.load(f)

            self._capacity = state.get("capacity", {})
            self._confidence = state.get("confidence", {})

            for w, counts in state.get("daily_counts", {}).items():
                for day, count in counts.items():
                    self._daily_counts[w][day] = count

            for w, tasks in state.get("active", {}).items():
                for t, data in tasks.items():
                    self._active[w][t] = ActiveTask(
                        task_id=data["task_id"],
                        worker_id=data["worker_id"],
                        assigned_at=data["assigned_at"],
                        complexity=data.get("complexity", 1.0),
                        task_type=data.get("task_type", ""),
                    )

            stats = state.get("stats", {})
            self._total_assignments = stats.get("total_assignments", 0)
            self._total_completions = stats.get("total_completions", 0)
            self._total_expirations = stats.get("total_expirations", 0)

            logger.info(f"LoadBridge state loaded from {path}")
        except Exception as e:
            logger.warning(f"Failed to load LoadBridge state: {e}")

    # ----- Cleanup -----

    def cleanup_stale(self, max_age_hours: float = 48.0) -> int:
        """Remove stale active tasks."""
        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        removed = 0

        for worker in list(self._active.keys()):
            tasks = self._active[worker]
            stale = [t for t, a in tasks.items() if a.assigned_at < cutoff]
            for t in stale:
                del tasks[t]
                removed += 1
            if not tasks:
                del self._active[worker]

        if removed:
            logger.info(f"Cleaned {removed} stale assignments (>{max_age_hours}h)")
        return removed

    # ----- Internal Methods -----

    def _get_capacity(self, worker_id: str) -> float:
        """Get estimated daily capacity."""
        if worker_id in self._capacity:
            return self._capacity[worker_id]
        return max(self.config.min_capacity, self.config.default_capacity)

    def _update_capacity(self, worker_id: str) -> None:
        """Update capacity estimate via EWMA."""
        daily = self._daily_counts.get(worker_id, {})
        if not daily:
            return

        cfg = self.config
        now = time.time()
        cutoff = now - (cfg.history_decay_days * 86400)

        recent = {}
        for day_str, count in daily.items():
            try:
                day_ts = datetime.strptime(day_str, "%Y-%m-%d").replace(
                    tzinfo=UTC
                ).timestamp()
                if day_ts >= cutoff:
                    recent[day_str] = count
            except ValueError:
                continue

        if not recent:
            return

        sorted_days = sorted(recent.items())
        alpha = cfg.ewma_alpha
        ewma = sorted_days[0][1]
        for _, count in sorted_days[1:]:
            ewma = alpha * count + (1 - alpha) * ewma

        capacity = max(cfg.min_capacity, min(cfg.max_capacity, ewma))
        self._capacity[worker_id] = capacity

        num_days = len(recent)
        self._confidence[worker_id] = min(1.0, num_days / max(1, cfg.min_history_days * 2))

    def _calculate_penalty(
        self,
        utilization: float,
        cooling: bool,
        confidence: float,
    ) -> float:
        """Calculate routing penalty from utilization."""
        cfg = self.config
        max_p = cfg.max_penalty

        if utilization <= cfg.no_penalty_threshold:
            penalty = 0.0
        elif utilization <= cfg.gentle_threshold:
            t = (utilization - cfg.no_penalty_threshold) / (
                cfg.gentle_threshold - cfg.no_penalty_threshold
            )
            penalty = t * 0.30 * max_p
        elif utilization <= cfg.steep_threshold:
            t = (utilization - cfg.gentle_threshold) / (
                cfg.steep_threshold - cfg.gentle_threshold
            )
            penalty = (0.30 + t * 0.50) * max_p
        elif utilization <= cfg.overload_threshold:
            t = (utilization - cfg.steep_threshold) / (
                cfg.overload_threshold - cfg.steep_threshold
            )
            penalty = (0.80 + t * 0.20) * max_p
        else:
            penalty = max_p

        if cooling:
            penalty += cfg.cooling_penalty

        if confidence < 0.5:
            penalty *= (0.5 + confidence)

        max_total = max_p + (cfg.cooling_penalty if cooling else 0.0)
        penalty = min(penalty, max_total)

        return round(-penalty, 6)

    def _check_cooling(self, worker_id: str, now: float) -> None:
        """Check for burst activity and trigger cooling."""
        cfg = self.config
        recent = self._recent_completions.get(worker_id, [])
        cutoff = now - cfg.cooling_window_seconds
        recent = [t for t in recent if t >= cutoff]
        self._recent_completions[worker_id] = recent

        if len(recent) >= cfg.cooling_burst_count:
            self._cooling_until[worker_id] = now + cfg.cooling_duration_seconds
            logger.info(
                f"Cooling triggered for {worker_id[:10]}... "
                f"({len(recent)} tasks in {cfg.cooling_window_seconds/60:.0f}min)"
            )

    def _classify_risk(self, utilization: float, cooling: bool) -> str:
        """Classify worker load risk level."""
        if utilization <= 0.0:
            return "idle"
        elif utilization <= self.config.no_penalty_threshold:
            return "light"
        elif utilization <= self.config.gentle_threshold:
            return "moderate"
        elif utilization <= self.config.steep_threshold:
            return "heavy_cooling" if cooling else "heavy"
        else:
            return "overloaded"

    def _make_recommendation(
        self,
        utilization: float,
        active: int,
        capacity: float,
        cooling: bool,
        risk: str,
    ) -> str:
        """Generate human-readable recommendation."""
        if risk == "idle":
            return "Available — no active tasks"
        elif risk == "light":
            remaining = capacity - active
            return f"Available — {active} active, ~{remaining:.0f} remaining"
        elif risk == "moderate":
            return f"Getting busy — {active} active ({utilization:.0%})"
        elif risk == "heavy_cooling":
            return f"Cooling down — {active} active ({utilization:.0%}), post-burst"
        elif risk == "heavy":
            return f"Near capacity — {active} active ({utilization:.0%})"
        else:
            return f"OVERLOADED — {active} active ({utilization:.0%} of {capacity:.0f})"

    def __repr__(self) -> str:
        fleet = self.fleet_utilization()
        return (
            f"LoadBridge(workers={fleet.total_workers}, "
            f"active={fleet.total_active_tasks}, "
            f"util={fleet.avg_utilization:.1%})"
        )
