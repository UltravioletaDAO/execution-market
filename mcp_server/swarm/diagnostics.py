"""
SwarmDiagnostics — Unified health and performance aggregation layer.

The 48th swarm module. Aggregates signals from:
  - ThroughputTracker (task throughput, routing efficiency, quality, burn rate)
  - ReputationBridge (composite scores, tier distribution)
  - SealBridge (seal profiles, issuance rates)
  - SwarmCoordinator (agent states, task queues, events)
  - LifecycleManager (fleet health, degradation)
  - BudgetController (spend tracking, budget status)
  - RetryPolicy (circuit breaker states, dead letter queue)
  - CapacityPlanner (capacity utilization, forecasts)

Produces:
  - SystemHealthReport (single unified health check)
  - PerformanceTrend (multi-signal trend analysis)
  - AlertDigest (aggregated alerts from all subsystems)
  - DiagnosticSnapshot (full system state for debugging)

Design principles:
  - Read-only: never modifies any subsystem state
  - Fault-tolerant: any subsystem can be unavailable
  - Bounded: all collections have max sizes
  - Observable: all operations produce diagnostic metadata
"""

import logging
import time
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Callable, Any

logger = logging.getLogger("em.swarm.diagnostics")


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class SubsystemHealth:
    """Health report for one subsystem."""
    name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    message: str = ""
    metrics: dict = field(default_factory=dict)
    checked_at: float = field(default_factory=time.time)
    error: str | None = None

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "metrics": self.metrics,
            "checked_at": self.checked_at,
        }
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class SystemHealthReport:
    """Unified health report across all subsystems."""
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    subsystems: list[SubsystemHealth] = field(default_factory=list)
    summary: str = ""
    checked_at: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    @property
    def healthy_count(self) -> int:
        return sum(1 for s in self.subsystems if s.status == HealthStatus.HEALTHY)

    @property
    def degraded_count(self) -> int:
        return sum(1 for s in self.subsystems if s.status == HealthStatus.DEGRADED)

    @property
    def critical_count(self) -> int:
        return sum(1 for s in self.subsystems if s.status == HealthStatus.CRITICAL)

    @property
    def unknown_count(self) -> int:
        return sum(1 for s in self.subsystems if s.status == HealthStatus.UNKNOWN)

    def to_dict(self) -> dict:
        return {
            "overall_status": self.overall_status.value,
            "summary": self.summary,
            "checked_at": self.checked_at,
            "duration_ms": round(self.duration_ms, 2),
            "counts": {
                "total": len(self.subsystems),
                "healthy": self.healthy_count,
                "degraded": self.degraded_count,
                "critical": self.critical_count,
                "unknown": self.unknown_count,
            },
            "subsystems": [s.to_dict() for s in self.subsystems],
        }


@dataclass
class PerformanceTrend:
    """Multi-signal performance trend over time."""
    signal_name: str
    direction: TrendDirection = TrendDirection.INSUFFICIENT_DATA
    current_value: float = 0.0
    previous_value: float = 0.0
    change_pct: float = 0.0
    data_points: int = 0
    window_seconds: float = 3600.0

    def to_dict(self) -> dict:
        return {
            "signal": self.signal_name,
            "direction": self.direction.value,
            "current": round(self.current_value, 3),
            "previous": round(self.previous_value, 3),
            "change_pct": round(self.change_pct, 2),
            "data_points": self.data_points,
            "window_seconds": self.window_seconds,
        }


@dataclass
class Alert:
    """A single alert from any subsystem."""
    source: str
    level: str  # "warning" or "critical"
    message: str
    metric_name: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "level": self.level,
            "message": self.message,
            "metric_name": self.metric_name,
            "metric_value": round(self.metric_value, 3),
            "threshold": round(self.threshold, 3),
            "created_at": self.created_at,
        }


@dataclass
class AlertDigest:
    """Aggregated alerts from all subsystems."""
    alerts: list[Alert] = field(default_factory=list)
    total_warnings: int = 0
    total_criticals: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "total_warnings": self.total_warnings,
            "total_criticals": self.total_criticals,
            "alert_count": len(self.alerts),
            "alerts": [a.to_dict() for a in self.alerts],
            "created_at": self.created_at,
        }


@dataclass
class DiagnosticSnapshot:
    """Full system state for debugging."""
    health: SystemHealthReport = field(default_factory=SystemHealthReport)
    trends: list[PerformanceTrend] = field(default_factory=list)
    alerts: AlertDigest = field(default_factory=AlertDigest)
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "health": self.health.to_dict(),
            "trends": [t.to_dict() for t in self.trends],
            "alerts": self.alerts.to_dict(),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


# ──────────────────────────────────────────────────────────────
# Diagnostics Engine
# ──────────────────────────────────────────────────────────────

class SwarmDiagnostics:
    """
    Unified diagnostics aggregator for the swarm.

    Collects health, performance, and alert data from all subsystems
    into a single coherent view. Designed for dashboard consumption,
    automated alerting, and debugging.

    Usage:
        diag = SwarmDiagnostics()
        diag.register_health_check("coordinator", check_coordinator)
        diag.register_health_check("scheduler", check_scheduler)

        report = diag.run_health_check()
        print(f"System: {report.overall_status.value}")

        diag.record_metric("throughput", 42.5)
        diag.record_metric("throughput", 45.0)
        trend = diag.compute_trend("throughput")
    """

    MAX_METRICS_HISTORY = 1000
    MAX_ALERTS = 500
    MAX_SNAPSHOTS = 100

    def __init__(self):
        self._health_checks: dict[str, Callable] = {}
        self._metrics: dict[str, deque] = {}
        self._alerts: deque[Alert] = deque(maxlen=self.MAX_ALERTS)
        self._snapshots: deque[DiagnosticSnapshot] = deque(maxlen=self.MAX_SNAPSHOTS)
        self._alert_callbacks: list[Callable[[Alert], None]] = []
        self._check_count: int = 0
        self._last_check_at: float = 0.0

    # ──────────────────────────────────────────────────────────
    # Health Check Registration
    # ──────────────────────────────────────────────────────────

    def register_health_check(
        self, name: str, check_fn: Callable[[], SubsystemHealth]
    ) -> None:
        """Register a health check function for a subsystem."""
        self._health_checks[name] = check_fn

    def unregister_health_check(self, name: str) -> bool:
        """Remove a health check. Returns True if it existed."""
        return self._health_checks.pop(name, None) is not None

    @property
    def registered_checks(self) -> list[str]:
        return list(self._health_checks.keys())

    # ──────────────────────────────────────────────────────────
    # Health Checks
    # ──────────────────────────────────────────────────────────

    def run_health_check(self) -> SystemHealthReport:
        """Run all registered health checks and produce unified report."""
        start = time.time()
        report = SystemHealthReport()
        report.checked_at = start

        for name, check_fn in self._health_checks.items():
            try:
                sub_health = check_fn()
                sub_health.name = name
            except Exception as e:
                sub_health = SubsystemHealth(
                    name=name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check failed: {type(e).__name__}",
                    error=str(e),
                )
            report.subsystems.append(sub_health)

        # Determine overall status
        report.overall_status = self._compute_overall_status(report.subsystems)
        report.summary = self._generate_summary(report)
        report.duration_ms = (time.time() - start) * 1000

        self._check_count += 1
        self._last_check_at = time.time()

        return report

    def _compute_overall_status(self, subsystems: list[SubsystemHealth]) -> HealthStatus:
        """Determine overall status from subsystem statuses."""
        if not subsystems:
            return HealthStatus.UNKNOWN

        statuses = [s.status for s in subsystems]

        if any(s == HealthStatus.CRITICAL for s in statuses):
            return HealthStatus.CRITICAL
        if any(s == HealthStatus.DEGRADED for s in statuses):
            return HealthStatus.DEGRADED
        if all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        if all(s == HealthStatus.UNKNOWN for s in statuses):
            return HealthStatus.UNKNOWN

        # Mix of healthy and unknown
        return HealthStatus.HEALTHY

    def _generate_summary(self, report: SystemHealthReport) -> str:
        """Generate human-readable summary."""
        total = len(report.subsystems)
        if total == 0:
            return "No subsystems registered"

        parts = []
        if report.healthy_count > 0:
            parts.append(f"{report.healthy_count} healthy")
        if report.degraded_count > 0:
            parts.append(f"{report.degraded_count} degraded")
        if report.critical_count > 0:
            parts.append(f"{report.critical_count} critical")
        if report.unknown_count > 0:
            parts.append(f"{report.unknown_count} unknown")

        return f"{total} subsystems: {', '.join(parts)}"

    # ──────────────────────────────────────────────────────────
    # Metrics Recording
    # ──────────────────────────────────────────────────────────

    def record_metric(self, name: str, value: float, timestamp: float | None = None) -> None:
        """Record a metric data point."""
        ts = timestamp or time.time()
        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=self.MAX_METRICS_HISTORY)
        self._metrics[name].append((ts, value))

    def get_metric_history(self, name: str, limit: int = 100) -> list[tuple[float, float]]:
        """Get recent metric history as (timestamp, value) pairs."""
        if name not in self._metrics:
            return []
        history = list(self._metrics[name])
        return history[-limit:]

    @property
    def metric_names(self) -> list[str]:
        return list(self._metrics.keys())

    def get_metric_stats(self, name: str) -> dict:
        """Get statistical summary for a metric."""
        history = self.get_metric_history(name, limit=self.MAX_METRICS_HISTORY)
        if not history:
            return {"count": 0}

        values = [v for _, v in history]
        n = len(values)
        mean = sum(values) / n
        sorted_vals = sorted(values)
        median = sorted_vals[n // 2]

        if n > 1:
            variance = sum((v - mean) ** 2 for v in values) / n
            std = math.sqrt(variance)
        else:
            std = 0.0

        return {
            "count": n,
            "mean": round(mean, 3),
            "median": round(median, 3),
            "std": round(std, 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "latest": round(values[-1], 3),
        }

    # ──────────────────────────────────────────────────────────
    # Trend Analysis
    # ──────────────────────────────────────────────────────────

    def compute_trend(
        self, name: str, window_seconds: float = 3600.0
    ) -> PerformanceTrend:
        """Compute trend direction for a metric over a time window."""
        trend = PerformanceTrend(signal_name=name, window_seconds=window_seconds)

        history = self.get_metric_history(name, limit=self.MAX_METRICS_HISTORY)
        if len(history) < 3:
            trend.data_points = len(history)
            return trend

        now = time.time()
        cutoff = now - window_seconds

        # Split into recent and previous windows
        recent = [(t, v) for t, v in history if t >= cutoff]
        previous = [(t, v) for t, v in history if t < cutoff]

        if not recent:
            trend.data_points = len(history)
            trend.direction = TrendDirection.INSUFFICIENT_DATA
            return trend

        trend.data_points = len(recent)
        trend.current_value = sum(v for _, v in recent) / len(recent)

        if previous:
            trend.previous_value = sum(v for _, v in previous) / len(previous)
            if trend.previous_value != 0:
                trend.change_pct = (
                    (trend.current_value - trend.previous_value) / abs(trend.previous_value)
                ) * 100
            elif trend.current_value != 0:
                trend.change_pct = 100.0
            else:
                trend.change_pct = 0.0

            # Determine direction
            if abs(trend.change_pct) < 5.0:
                trend.direction = TrendDirection.STABLE
            elif trend.change_pct > 0:
                trend.direction = TrendDirection.IMPROVING
            else:
                trend.direction = TrendDirection.DECLINING
        else:
            # Only recent data, use slope within recent window
            if len(recent) >= 3:
                first_half = recent[: len(recent) // 2]
                second_half = recent[len(recent) // 2 :]
                first_avg = sum(v for _, v in first_half) / len(first_half)
                second_avg = sum(v for _, v in second_half) / len(second_half)

                if first_avg > 0:
                    intra_change = ((second_avg - first_avg) / abs(first_avg)) * 100
                else:
                    intra_change = 0.0

                if abs(intra_change) < 5.0:
                    trend.direction = TrendDirection.STABLE
                elif intra_change > 0:
                    trend.direction = TrendDirection.IMPROVING
                else:
                    trend.direction = TrendDirection.DECLINING
                trend.change_pct = intra_change
            else:
                trend.direction = TrendDirection.INSUFFICIENT_DATA

        return trend

    def compute_all_trends(self, window_seconds: float = 3600.0) -> list[PerformanceTrend]:
        """Compute trends for all recorded metrics."""
        return [self.compute_trend(name, window_seconds) for name in self._metrics]

    # ──────────────────────────────────────────────────────────
    # Alerts
    # ──────────────────────────────────────────────────────────

    def raise_alert(self, alert: Alert) -> None:
        """Record and dispatch an alert."""
        self._alerts.append(alert)
        for cb in self._alert_callbacks:
            try:
                cb(alert)
            except Exception as e:
                logger.warning(f"Alert callback error: {e}")

    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Register a callback for new alerts."""
        self._alert_callbacks.append(callback)

    def get_alert_digest(self, limit: int = 50) -> AlertDigest:
        """Get recent alerts as a digest."""
        recent = list(self._alerts)[-limit:]
        return AlertDigest(
            alerts=recent,
            total_warnings=sum(1 for a in recent if a.level == "warning"),
            total_criticals=sum(1 for a in recent if a.level == "critical"),
        )

    def check_thresholds(
        self, name: str, warning_threshold: float, critical_threshold: float,
        comparison: str = "above"
    ) -> Alert | None:
        """Check a metric against thresholds and raise alert if violated."""
        history = self.get_metric_history(name, limit=1)
        if not history:
            return None

        _, value = history[-1]

        if comparison == "above":
            is_critical = value >= critical_threshold
            is_warning = value >= warning_threshold
        else:  # "below"
            is_critical = value <= critical_threshold
            is_warning = value <= warning_threshold

        if is_critical:
            alert = Alert(
                source="diagnostics",
                level="critical",
                message=f"{name} at {value:.3f} ({comparison} critical threshold {critical_threshold})",
                metric_name=name,
                metric_value=value,
                threshold=critical_threshold,
            )
            self.raise_alert(alert)
            return alert
        elif is_warning:
            alert = Alert(
                source="diagnostics",
                level="warning",
                message=f"{name} at {value:.3f} ({comparison} warning threshold {warning_threshold})",
                metric_name=name,
                metric_value=value,
                threshold=warning_threshold,
            )
            self.raise_alert(alert)
            return alert

        return None

    # ──────────────────────────────────────────────────────────
    # Snapshots
    # ──────────────────────────────────────────────────────────

    def take_snapshot(self, include_health: bool = True) -> DiagnosticSnapshot:
        """Take a full diagnostic snapshot."""
        snapshot = DiagnosticSnapshot()

        if include_health:
            snapshot.health = self.run_health_check()

        snapshot.trends = self.compute_all_trends()
        snapshot.alerts = self.get_alert_digest()
        snapshot.metadata = {
            "check_count": self._check_count,
            "last_check_at": self._last_check_at,
            "registered_checks": len(self._health_checks),
            "metric_count": len(self._metrics),
            "alert_count": len(self._alerts),
            "snapshot_count": len(self._snapshots) + 1,
        }

        self._snapshots.append(snapshot)
        return snapshot

    def get_snapshot_history(self, limit: int = 10) -> list[dict]:
        """Get recent snapshot metadata (not full snapshots — for list views)."""
        recent = list(self._snapshots)[-limit:]
        return [
            {
                "created_at": s.created_at,
                "overall_status": s.health.overall_status.value,
                "alert_count": len(s.alerts.alerts),
                "trend_count": len(s.trends),
            }
            for s in recent
        ]

    # ──────────────────────────────────────────────────────────
    # Convenience: Pre-built Health Checks
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def create_metric_health_check(
        diagnostics: "SwarmDiagnostics",
        metric_name: str,
        healthy_min: float,
        degraded_min: float,
        label: str = "",
    ) -> Callable[[], SubsystemHealth]:
        """
        Create a health check function based on a metric value.
        healthy_min >= value → healthy, degraded_min >= value → degraded, else critical.
        """
        def check() -> SubsystemHealth:
            history = diagnostics.get_metric_history(metric_name, limit=1)
            if not history:
                return SubsystemHealth(
                    name=label or metric_name,
                    status=HealthStatus.UNKNOWN,
                    message=f"No data for {metric_name}",
                )

            _, value = history[-1]
            if value >= healthy_min:
                status = HealthStatus.HEALTHY
            elif value >= degraded_min:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.CRITICAL

            return SubsystemHealth(
                name=label or metric_name,
                status=status,
                message=f"{metric_name}: {value:.3f}",
                metrics={metric_name: value},
            )

        return check

    # ──────────────────────────────────────────────────────────
    # Status
    # ──────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Quick status overview without running health checks."""
        return {
            "registered_checks": len(self._health_checks),
            "check_names": list(self._health_checks.keys()),
            "metric_count": len(self._metrics),
            "metric_names": list(self._metrics.keys()),
            "alert_count": len(self._alerts),
            "snapshot_count": len(self._snapshots),
            "total_checks_run": self._check_count,
            "last_check_at": self._last_check_at,
        }
