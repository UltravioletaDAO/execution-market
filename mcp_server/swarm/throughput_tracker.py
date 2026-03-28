"""
ThroughputTracker — Real-time task throughput monitoring for the swarm.

Tracks completions, failures, and routing events with sliding-window
metrics for throughput, quality distribution, and burn rate.

Integrates with EventBus for automatic event-driven updates.

Metrics provided:
    - Tasks per hour (sliding window)
    - Routing efficiency (first-attempt success rate)
    - Quality score distribution (mean, median, std, histogram)
    - Budget burn rate (spend velocity)
    - Alert thresholds with configurable warning/critical levels
"""

import logging
import time
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger("em.swarm.throughput_tracker")


class AlertLevel(Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlertThresholds:
    """Configurable alert thresholds for each signal."""
    # Throughput: percentage of baseline
    throughput_warning_pct: float = 50.0   # <50% of baseline = warning
    throughput_critical_pct: float = 25.0  # <25% of baseline = critical

    # Routing efficiency
    routing_warning_pct: float = 80.0      # <80% first-attempt = warning
    routing_critical_pct: float = 60.0     # <60% first-attempt = critical

    # Quality distribution
    quality_warning_mean: float = 0.6      # Mean <0.6 = warning
    quality_critical_mean: float = 0.5     # Mean <0.5 = critical

    # Budget burn rate: percentage over projected
    burn_warning_pct: float = 150.0        # >150% of projected = warning
    burn_critical_pct: float = 200.0       # >200% of projected = critical

    # Agent health: percentage degraded
    health_warning_pct: float = 20.0       # >20% degraded = warning
    health_critical_pct: float = 30.0      # >30% degraded = critical


@dataclass
class ThroughputSnapshot:
    """Point-in-time throughput metrics."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tasks_per_hour: float = 0.0
    routing_efficiency: float = 1.0
    quality_mean: float = 0.0
    quality_median: float = 0.0
    quality_std: float = 0.0
    burn_rate_usd_per_hour: float = 0.0
    agents_healthy: int = 0
    agents_degraded: int = 0
    agents_total: int = 0
    alerts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "throughput": {
                "tasks_per_hour": round(self.tasks_per_hour, 2),
            },
            "routing": {
                "efficiency": round(self.routing_efficiency, 4),
            },
            "quality": {
                "mean": round(self.quality_mean, 4),
                "median": round(self.quality_median, 4),
                "std": round(self.quality_std, 4),
            },
            "budget": {
                "burn_rate_usd_per_hour": round(self.burn_rate_usd_per_hour, 4),
            },
            "agents": {
                "healthy": self.agents_healthy,
                "degraded": self.agents_degraded,
                "total": self.agents_total,
            },
            "alerts": self.alerts,
        }


class ThroughputTracker:
    """
    Real-time throughput monitoring with sliding windows and alerts.

    Tracks events (completions, failures, quality scores, spend) in
    time-windowed deques and computes derived metrics on demand.
    """

    def __init__(
        self,
        window_minutes: int = 60,
        baseline_tasks_per_hour: float = 10.0,
        projected_daily_spend_usd: float = 100.0,
        thresholds: Optional[AlertThresholds] = None,
        max_samples: int = 2000,
    ):
        self.window_minutes = window_minutes
        self.baseline_tph = baseline_tasks_per_hour
        self.projected_daily_spend = projected_daily_spend_usd
        self.thresholds = thresholds or AlertThresholds()
        self.max_samples = max_samples

        # Time-stamped event deques
        self._completions: deque[float] = deque(maxlen=max_samples)
        self._failures: deque[float] = deque(maxlen=max_samples)
        self._routing_attempts: deque[tuple[float, bool]] = deque(maxlen=max_samples)
        self._quality_scores: deque[tuple[float, float]] = deque(maxlen=max_samples)
        self._spends: deque[tuple[float, float]] = deque(maxlen=max_samples)

        # Agent health tracking
        self._agent_health: dict[int, bool] = {}  # agent_id → is_healthy

        # Alert callbacks
        self._alert_callbacks: list[Callable] = []

        # History of snapshots (for trend analysis)
        self._snapshot_history: deque[ThroughputSnapshot] = deque(maxlen=500)

    # ─── Event Recording ─────────────────────────────────────────────────

    def record_completion(self, quality_score: float = 0.0, bounty_usd: float = 0.0):
        """Record a successful task completion."""
        now = time.time()
        self._completions.append(now)
        if quality_score > 0:
            self._quality_scores.append((now, quality_score))
        if bounty_usd > 0:
            self._spends.append((now, bounty_usd))

    def record_failure(self, bounty_usd: float = 0.0):
        """Record a task failure."""
        now = time.time()
        self._failures.append(now)
        if bounty_usd > 0:
            self._spends.append((now, bounty_usd))

    def record_routing_attempt(self, success: bool):
        """Record a routing attempt and whether it succeeded on first try."""
        self._routing_attempts.append((time.time(), success))

    def record_agent_health(self, agent_id: int, is_healthy: bool):
        """Update agent health status."""
        self._agent_health[agent_id] = is_healthy

    def on_alert(self, callback: Callable):
        """Register a callback for alert state changes."""
        self._alert_callbacks.append(callback)

    # ─── Metric Computation ──────────────────────────────────────────────

    def _window_cutoff(self) -> float:
        """Compute the window cutoff timestamp."""
        return time.time() - (self.window_minutes * 60)

    def tasks_per_hour(self) -> float:
        """Compute current tasks per hour (completions in window)."""
        cutoff = self._window_cutoff()
        recent = sum(1 for t in self._completions if t > cutoff)
        window_hours = self.window_minutes / 60.0
        return recent / window_hours if window_hours > 0 else 0.0

    def failures_per_hour(self) -> float:
        """Compute failures per hour in window."""
        cutoff = self._window_cutoff()
        recent = sum(1 for t in self._failures if t > cutoff)
        window_hours = self.window_minutes / 60.0
        return recent / window_hours if window_hours > 0 else 0.0

    def routing_efficiency(self) -> float:
        """Percentage of routing attempts that succeeded on first try."""
        cutoff = self._window_cutoff()
        recent = [(t, s) for t, s in self._routing_attempts if t > cutoff]
        if not recent:
            return 1.0  # No data = assume healthy
        successes = sum(1 for _, s in recent if s)
        return successes / len(recent)

    def quality_stats(self) -> dict:
        """Compute quality score statistics in window."""
        cutoff = self._window_cutoff()
        scores = [s for t, s in self._quality_scores if t > cutoff]

        if not scores:
            return {"mean": 0.0, "median": 0.0, "std": 0.0, "count": 0}

        mean = sum(scores) / len(scores)
        sorted_scores = sorted(scores)
        n = len(sorted_scores)
        median = sorted_scores[n // 2] if n % 2 == 1 else (sorted_scores[n // 2 - 1] + sorted_scores[n // 2]) / 2
        variance = sum((s - mean) ** 2 for s in scores) / len(scores) if len(scores) > 1 else 0.0
        std = math.sqrt(variance)

        return {
            "mean": mean,
            "median": median,
            "std": std,
            "count": len(scores),
        }

    def burn_rate_per_hour(self) -> float:
        """Compute USD burn rate per hour in window."""
        cutoff = self._window_cutoff()
        recent_spend = sum(amt for t, amt in self._spends if t > cutoff)
        window_hours = self.window_minutes / 60.0
        return recent_spend / window_hours if window_hours > 0 else 0.0

    def agent_health_summary(self) -> dict:
        """Summarize agent health status."""
        total = len(self._agent_health)
        healthy = sum(1 for h in self._agent_health.values() if h)
        degraded = total - healthy
        return {
            "total": total,
            "healthy": healthy,
            "degraded": degraded,
            "degraded_pct": (degraded / total * 100) if total > 0 else 0.0,
        }

    # ─── Alert Evaluation ────────────────────────────────────────────────

    def evaluate_alerts(self) -> dict[str, AlertLevel]:
        """Evaluate all alert signals and return alert levels."""
        alerts = {}
        t = self.thresholds

        # 1. Throughput
        tph = self.tasks_per_hour()
        if self.baseline_tph > 0:
            tph_pct = (tph / self.baseline_tph) * 100
            if tph_pct < t.throughput_critical_pct:
                alerts["throughput"] = AlertLevel.CRITICAL
            elif tph_pct < t.throughput_warning_pct:
                alerts["throughput"] = AlertLevel.WARNING
            else:
                alerts["throughput"] = AlertLevel.OK
        else:
            alerts["throughput"] = AlertLevel.OK

        # 2. Routing efficiency
        eff = self.routing_efficiency()
        eff_pct = eff * 100
        if eff_pct < t.routing_critical_pct:
            alerts["routing"] = AlertLevel.CRITICAL
        elif eff_pct < t.routing_warning_pct:
            alerts["routing"] = AlertLevel.WARNING
        else:
            alerts["routing"] = AlertLevel.OK

        # 3. Quality
        qstats = self.quality_stats()
        if qstats["count"] > 0:
            if qstats["mean"] < t.quality_critical_mean:
                alerts["quality"] = AlertLevel.CRITICAL
            elif qstats["mean"] < t.quality_warning_mean:
                alerts["quality"] = AlertLevel.WARNING
            else:
                alerts["quality"] = AlertLevel.OK
        else:
            alerts["quality"] = AlertLevel.OK

        # 4. Budget burn rate
        burn = self.burn_rate_per_hour()
        projected_hourly = self.projected_daily_spend / 24.0
        if projected_hourly > 0:
            burn_pct = (burn / projected_hourly) * 100
            if burn_pct > t.burn_critical_pct:
                alerts["budget"] = AlertLevel.CRITICAL
            elif burn_pct > t.burn_warning_pct:
                alerts["budget"] = AlertLevel.WARNING
            else:
                alerts["budget"] = AlertLevel.OK
        else:
            alerts["budget"] = AlertLevel.OK

        # 5. Agent health
        health = self.agent_health_summary()
        if health["degraded_pct"] > t.health_critical_pct:
            alerts["health"] = AlertLevel.CRITICAL
        elif health["degraded_pct"] > t.health_warning_pct:
            alerts["health"] = AlertLevel.WARNING
        else:
            alerts["health"] = AlertLevel.OK

        return alerts

    def has_any_alert(self, min_level: AlertLevel = AlertLevel.WARNING) -> bool:
        """Check if any alert is at or above the given level."""
        alerts = self.evaluate_alerts()
        levels = {AlertLevel.OK: 0, AlertLevel.WARNING: 1, AlertLevel.CRITICAL: 2}
        min_val = levels[min_level]
        return any(levels[v] >= min_val for v in alerts.values())

    # ─── Snapshot ────────────────────────────────────────────────────────

    def snapshot(self) -> ThroughputSnapshot:
        """Capture a point-in-time snapshot of all metrics."""
        qstats = self.quality_stats()
        health = self.agent_health_summary()
        alerts = self.evaluate_alerts()

        snap = ThroughputSnapshot(
            tasks_per_hour=self.tasks_per_hour(),
            routing_efficiency=self.routing_efficiency(),
            quality_mean=qstats["mean"],
            quality_median=qstats["median"],
            quality_std=qstats["std"],
            burn_rate_usd_per_hour=self.burn_rate_per_hour(),
            agents_healthy=health["healthy"],
            agents_degraded=health["degraded"],
            agents_total=health["total"],
            alerts={k: v.value for k, v in alerts.items()},
        )

        self._snapshot_history.append(snap)

        # Fire alert callbacks for WARNING/CRITICAL
        for signal, level in alerts.items():
            if level in (AlertLevel.WARNING, AlertLevel.CRITICAL):
                for cb in self._alert_callbacks:
                    try:
                        cb(signal, level, snap)
                    except Exception as e:
                        logger.error(f"Alert callback error: {e}")

        return snap

    def get_trend(self, metric: str = "tasks_per_hour", last_n: int = 10) -> list[float]:
        """Get recent trend for a metric from snapshot history."""
        snapshots = list(self._snapshot_history)[-last_n:]
        return [getattr(s, metric, 0.0) for s in snapshots]

    # ─── Reset ───────────────────────────────────────────────────────────

    def reset(self):
        """Clear all tracked data."""
        self._completions.clear()
        self._failures.clear()
        self._routing_attempts.clear()
        self._quality_scores.clear()
        self._spends.clear()
        self._agent_health.clear()
        self._snapshot_history.clear()
