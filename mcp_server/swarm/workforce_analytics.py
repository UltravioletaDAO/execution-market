"""
WorkforceAnalytics — Aggregated Intelligence Dashboard for Workforce Data
=========================================================================

Consolidates data from all swarm modules into a unified analytics view.
This is the module that answers executive-level questions:

  - "How is the workforce performing overall?"
  - "What's our completion rate trend?"
  - "Where are we losing value?"
  - "Which workers are our MVPs?"
  - "What should we change?"

Data sources (all in-process, no external calls):
  - TaskRecords from ReplayEngine/RoutingOptimizer
  - Worker profiles from LifecycleManager
  - Budget data from BudgetController
  - Health data from MetricsCollector
  - Routing weights from RoutingOptimizer

Output: AnalyticsReport — a comprehensive snapshot with insights.

Thread-safe. No external dependencies.
"""

import logging
import math
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("em.swarm.workforce_analytics")


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


class TrendDirection(str, Enum):
    """Direction of a metric trend."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    INSUFFICIENT_DATA = "insufficient_data"


class AlertSeverity(str, Enum):
    """Severity level for analytics alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """A single data point in a time series."""

    timestamp: float
    value: float
    label: str = ""


@dataclass
class MetricSeries:
    """A time series of metric values."""

    name: str
    unit: str = ""
    points: list[MetricPoint] = field(default_factory=list)

    @property
    def latest(self) -> float | None:
        if not self.points:
            return None
        return self.points[-1].value

    @property
    def average(self) -> float:
        if not self.points:
            return 0.0
        return sum(p.value for p in self.points) / len(self.points)

    @property
    def trend(self) -> TrendDirection:
        if len(self.points) < 3:
            return TrendDirection.INSUFFICIENT_DATA
        recent = [p.value for p in self.points[-3:]]
        older = [p.value for p in self.points[:3]]
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        delta = recent_avg - older_avg
        threshold = older_avg * 0.05 if older_avg != 0 else 0.01
        if delta > threshold:
            return TrendDirection.IMPROVING
        elif delta < -threshold:
            return TrendDirection.DECLINING
        return TrendDirection.STABLE

    def add(self, value: float, label: str = "", timestamp: float | None = None):
        self.points.append(
            MetricPoint(
                timestamp=timestamp or time.time(),
                value=value,
                label=label,
            )
        )

    @property
    def min_value(self) -> float:
        if not self.points:
            return 0.0
        return min(p.value for p in self.points)

    @property
    def max_value(self) -> float:
        if not self.points:
            return 0.0
        return max(p.value for p in self.points)


@dataclass
class WorkerProfile:
    """Analytics view of a worker."""

    worker_id: str
    tasks_completed: int = 0
    tasks_expired: int = 0
    tasks_total: int = 0
    avg_quality: float = 0.0
    avg_speed_hours: float = 0.0
    total_earned_usd: float = 0.0
    categories: list[str] = field(default_factory=list)
    reputation_score: float = 0.0
    first_seen: float = 0.0
    last_active: float = 0.0

    @property
    def completion_rate(self) -> float:
        if self.tasks_total == 0:
            return 0.0
        return self.tasks_completed / self.tasks_total

    @property
    def is_mvp(self) -> bool:
        """Top performer: high completion + quality + volume."""
        return (
            self.completion_rate >= 0.8
            and self.avg_quality >= 0.7
            and self.tasks_completed >= 5
        )

    @property
    def is_at_risk(self) -> bool:
        """Worker showing declining performance."""
        return self.completion_rate < 0.5 and self.tasks_total >= 3

    @property
    def specialization(self) -> str:
        """Most common category."""
        if not self.categories:
            return "generalist"
        counter = Counter(self.categories)
        top = counter.most_common(1)[0]
        if top[1] >= len(self.categories) * 0.5:
            return top[0]
        return "generalist"


@dataclass
class CategoryBreakdown:
    """Analytics for a task category."""

    name: str
    task_count: int = 0
    completed: int = 0
    expired: int = 0
    avg_quality: float = 0.0
    avg_bounty_usd: float = 0.0
    avg_completion_hours: float = 0.0
    worker_count: int = 0

    @property
    def completion_rate(self) -> float:
        if self.task_count == 0:
            return 0.0
        return self.completed / self.task_count

    @property
    def value_per_dollar(self) -> float:
        if self.avg_bounty_usd == 0:
            return 0.0
        return self.avg_quality / self.avg_bounty_usd


@dataclass
class AnalyticsAlert:
    """An insight or warning from analytics."""

    severity: AlertSeverity
    message: str
    metric: str = ""
    value: float = 0.0
    threshold: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class AnalyticsReport:
    """Comprehensive analytics snapshot."""

    # Overview
    total_tasks: int = 0
    total_completed: int = 0
    total_expired: int = 0
    total_workers: int = 0
    total_spent_usd: float = 0.0

    # Rates
    completion_rate: float = 0.0
    avg_quality: float = 0.0
    avg_speed_hours: float = 0.0

    # Trends
    trends: dict[str, TrendDirection] = field(default_factory=dict)

    # Breakdowns
    category_breakdown: list[CategoryBreakdown] = field(default_factory=list)
    mvp_workers: list[str] = field(default_factory=list)
    at_risk_workers: list[str] = field(default_factory=list)

    # Alerts
    alerts: list[AnalyticsAlert] = field(default_factory=list)

    # Optimization
    best_category: str = ""
    worst_category: str = ""
    recommended_actions: list[str] = field(default_factory=list)

    # Meta
    generated_at: float = field(default_factory=time.time)
    data_points: int = 0

    @property
    def health_score(self) -> float:
        """Overall health score 0-100."""
        score = 0.0
        score += self.completion_rate * 40  # 40% weight
        score += self.avg_quality * 30  # 30% weight
        score += (
            min(1.0, self.total_workers / 10) * 15
        )  # 15% weight (10+ workers = full)
        score += (
            1.0
            - len([a for a in self.alerts if a.severity == AlertSeverity.CRITICAL])
            / max(1, len(self.alerts))
        ) * 15
        return min(100.0, score)


# ──────────────────────────────────────────────────────────────
# Task Record (light version for analytics input)
# ──────────────────────────────────────────────────────────────


@dataclass
class TaskEvent:
    """A task event for analytics ingestion."""

    task_id: str
    category: str = ""
    worker_id: str = ""
    outcome: str = "completed"  # completed, expired, rejected, cancelled
    quality_score: float = 0.0
    bounty_usd: float = 0.0
    completion_hours: float = 0.0
    timestamp: float = 0.0

    @property
    def is_success(self) -> bool:
        return self.outcome == "completed"


# ──────────────────────────────────────────────────────────────
# Core Analytics Engine
# ──────────────────────────────────────────────────────────────


class WorkforceAnalytics:
    """
    Aggregated intelligence dashboard for the KK V2 swarm.
    Ingests task events and produces analytics reports.
    """

    def __init__(
        self,
        alert_thresholds: dict[str, float] | None = None,
    ):
        self._events: list[TaskEvent] = []
        self._series: dict[str, MetricSeries] = {}
        self._alert_thresholds = alert_thresholds or {
            "min_completion_rate": 0.5,
            "min_quality": 0.6,
            "max_avg_hours": 48.0,
            "min_workers": 3,
            "max_concentration": 0.7,  # Single worker doing > 70% of tasks
        }

    # ── Event Ingestion ──────────────────────────────────────

    def ingest(self, event: TaskEvent):
        """Add a task event to the analytics pipeline."""
        self._events.append(event)
        self._update_series(event)

    def ingest_batch(self, events: list[TaskEvent]):
        """Add multiple events at once."""
        for event in events:
            self.ingest(event)

    def _update_series(self, event: TaskEvent):
        """Update time series from an event."""
        ts = event.timestamp or time.time()

        if "completion_rate" not in self._series:
            self._series["completion_rate"] = MetricSeries(
                name="Completion Rate", unit="%"
            )
        if "quality" not in self._series:
            self._series["quality"] = MetricSeries(name="Quality Score", unit="")
        if "volume" not in self._series:
            self._series["volume"] = MetricSeries(name="Task Volume", unit="tasks")

        # Recompute rolling metrics
        recent = self._events[-20:]  # Last 20 events
        completed = sum(1 for e in recent if e.is_success)
        rate = completed / len(recent) if recent else 0.0
        self._series["completion_rate"].add(rate, timestamp=ts)

        if event.is_success and event.quality_score > 0:
            self._series["quality"].add(event.quality_score, timestamp=ts)

        self._series["volume"].add(len(self._events), timestamp=ts)

    # ── Report Generation ────────────────────────────────────

    def generate_report(self) -> AnalyticsReport:
        """Generate a comprehensive analytics report from all ingested events."""
        if not self._events:
            return AnalyticsReport(data_points=0)

        report = AnalyticsReport(data_points=len(self._events))

        # Overview
        report.total_tasks = len(self._events)
        report.total_completed = sum(1 for e in self._events if e.is_success)
        report.total_expired = sum(1 for e in self._events if e.outcome == "expired")
        workers = {e.worker_id for e in self._events if e.worker_id}
        report.total_workers = len(workers)
        report.total_spent_usd = sum(e.bounty_usd for e in self._events if e.is_success)

        # Rates
        report.completion_rate = (
            report.total_completed / report.total_tasks
            if report.total_tasks > 0
            else 0.0
        )
        completed_events = [e for e in self._events if e.is_success]
        report.avg_quality = (
            sum(e.quality_score for e in completed_events) / len(completed_events)
            if completed_events
            else 0.0
        )
        report.avg_speed_hours = (
            sum(e.completion_hours for e in completed_events) / len(completed_events)
            if completed_events
            else 0.0
        )

        # Trends
        for name, series in self._series.items():
            report.trends[name] = series.trend

        # Category breakdown
        report.category_breakdown = self._compute_category_breakdown()
        if report.category_breakdown:
            best = max(report.category_breakdown, key=lambda c: c.completion_rate)
            worst = min(report.category_breakdown, key=lambda c: c.completion_rate)
            report.best_category = best.name
            report.worst_category = worst.name

        # Worker profiles
        worker_profiles = self._compute_worker_profiles()
        report.mvp_workers = [w.worker_id for w in worker_profiles if w.is_mvp]
        report.at_risk_workers = [w.worker_id for w in worker_profiles if w.is_at_risk]

        # Alerts
        report.alerts = self._compute_alerts(report, worker_profiles)

        # Recommendations
        report.recommended_actions = self._compute_recommendations(report)

        return report

    def _compute_category_breakdown(self) -> list[CategoryBreakdown]:
        """Compute per-category analytics."""
        categories: dict[str, list[TaskEvent]] = defaultdict(list)
        for e in self._events:
            cat = e.category or "uncategorized"
            categories[cat].append(e)

        breakdowns = []
        for name, events in categories.items():
            completed = [e for e in events if e.is_success]
            expired = [e for e in events if e.outcome == "expired"]
            workers = {e.worker_id for e in events if e.worker_id}

            bd = CategoryBreakdown(
                name=name,
                task_count=len(events),
                completed=len(completed),
                expired=len(expired),
                avg_quality=(
                    sum(e.quality_score for e in completed) / len(completed)
                    if completed
                    else 0.0
                ),
                avg_bounty_usd=(
                    sum(e.bounty_usd for e in events) / len(events) if events else 0.0
                ),
                avg_completion_hours=(
                    sum(e.completion_hours for e in completed) / len(completed)
                    if completed
                    else 0.0
                ),
                worker_count=len(workers),
            )
            breakdowns.append(bd)

        breakdowns.sort(key=lambda b: b.task_count, reverse=True)
        return breakdowns

    def _compute_worker_profiles(self) -> list[WorkerProfile]:
        """Compute per-worker analytics."""
        workers: dict[str, list[TaskEvent]] = defaultdict(list)
        for e in self._events:
            if e.worker_id:
                workers[e.worker_id].append(e)

        profiles = []
        for worker_id, events in workers.items():
            completed = [e for e in events if e.is_success]
            expired = [e for e in events if e.outcome == "expired"]
            timestamps = [e.timestamp for e in events if e.timestamp > 0]

            profile = WorkerProfile(
                worker_id=worker_id,
                tasks_completed=len(completed),
                tasks_expired=len(expired),
                tasks_total=len(events),
                avg_quality=(
                    sum(e.quality_score for e in completed) / len(completed)
                    if completed
                    else 0.0
                ),
                avg_speed_hours=(
                    sum(e.completion_hours for e in completed) / len(completed)
                    if completed
                    else 0.0
                ),
                total_earned_usd=sum(e.bounty_usd for e in completed),
                categories=[e.category for e in events if e.category],
                first_seen=min(timestamps) if timestamps else 0.0,
                last_active=max(timestamps) if timestamps else 0.0,
            )
            profiles.append(profile)

        profiles.sort(key=lambda p: p.tasks_completed, reverse=True)
        return profiles

    def _compute_alerts(
        self,
        report: AnalyticsReport,
        workers: list[WorkerProfile],
    ) -> list[AnalyticsAlert]:
        """Generate alerts from thresholds."""
        alerts = []
        thresholds = self._alert_thresholds

        # Completion rate
        if report.completion_rate < thresholds.get("min_completion_rate", 0.5):
            alerts.append(
                AnalyticsAlert(
                    severity=AlertSeverity.WARNING
                    if report.completion_rate > 0.3
                    else AlertSeverity.CRITICAL,
                    message=f"Completion rate {report.completion_rate:.0%} below threshold {thresholds['min_completion_rate']:.0%}",
                    metric="completion_rate",
                    value=report.completion_rate,
                    threshold=thresholds["min_completion_rate"],
                )
            )

        # Quality
        if report.avg_quality < thresholds.get("min_quality", 0.6):
            alerts.append(
                AnalyticsAlert(
                    severity=AlertSeverity.WARNING,
                    message=f"Average quality {report.avg_quality:.2f} below threshold {thresholds['min_quality']:.2f}",
                    metric="avg_quality",
                    value=report.avg_quality,
                    threshold=thresholds["min_quality"],
                )
            )

        # Speed
        if report.avg_speed_hours > thresholds.get("max_avg_hours", 48.0):
            alerts.append(
                AnalyticsAlert(
                    severity=AlertSeverity.WARNING,
                    message=f"Average completion time {report.avg_speed_hours:.1f}h exceeds {thresholds['max_avg_hours']:.0f}h",
                    metric="avg_speed_hours",
                    value=report.avg_speed_hours,
                    threshold=thresholds["max_avg_hours"],
                )
            )

        # Worker count
        if report.total_workers < thresholds.get("min_workers", 3):
            severity = (
                AlertSeverity.CRITICAL
                if report.total_workers <= 1
                else AlertSeverity.WARNING
            )
            alerts.append(
                AnalyticsAlert(
                    severity=severity,
                    message=f"Only {report.total_workers} active workers (minimum: {thresholds['min_workers']:.0f})",
                    metric="worker_count",
                    value=report.total_workers,
                    threshold=thresholds["min_workers"],
                )
            )

        # Worker concentration
        if workers and report.total_tasks > 0:
            top_worker = workers[0]
            concentration = top_worker.tasks_total / report.total_tasks
            if concentration > thresholds.get("max_concentration", 0.7):
                alerts.append(
                    AnalyticsAlert(
                        severity=AlertSeverity.WARNING,
                        message=f"Worker {top_worker.worker_id} handles {concentration:.0%} of all tasks (risk: single point of failure)",
                        metric="concentration",
                        value=concentration,
                        threshold=thresholds.get("max_concentration", 0.7),
                    )
                )

        # At-risk workers
        for w in workers:
            if w.is_at_risk:
                alerts.append(
                    AnalyticsAlert(
                        severity=AlertSeverity.INFO,
                        message=f"Worker {w.worker_id} completion rate is {w.completion_rate:.0%} ({w.tasks_total} tasks)",
                        metric="worker_completion_rate",
                        value=w.completion_rate,
                    )
                )

        return alerts

    def _compute_recommendations(self, report: AnalyticsReport) -> list[str]:
        """Generate actionable recommendations."""
        recs = []

        if report.completion_rate < 0.5:
            recs.append(
                "CRITICAL: Completion rate below 50%. Review task requirements and worker matching."
            )

        if report.total_workers < 3:
            recs.append(
                f"RECRUIT: Only {report.total_workers} workers. Target 5+ for resilience."
            )

        if report.worst_category and report.category_breakdown:
            worst = next(
                (
                    c
                    for c in report.category_breakdown
                    if c.name == report.worst_category
                ),
                None,
            )
            if worst and worst.completion_rate < 0.5:
                recs.append(
                    f"IMPROVE: '{worst.name}' category has {worst.completion_rate:.0%} completion. Recruit specialists."
                )

        if report.avg_speed_hours > 24:
            recs.append(
                f"SPEED: Average completion is {report.avg_speed_hours:.1f}h. Consider shorter deadlines or urgency incentives."
            )

        if report.mvp_workers:
            recs.append(
                f"RETAIN: {len(report.mvp_workers)} MVP workers identified. Prioritize their task routing."
            )

        if not recs:
            recs.append(
                "System performing within normal parameters. Continue monitoring."
            )

        return recs

    # ── Trend Analysis ───────────────────────────────────────

    def get_series(self, name: str) -> MetricSeries | None:
        """Get a specific metric series."""
        return self._series.get(name)

    def get_all_trends(self) -> dict[str, TrendDirection]:
        """Get trend direction for all tracked metrics."""
        return {name: series.trend for name, series in self._series.items()}

    # ── Worker Analytics ─────────────────────────────────────

    def top_workers(self, n: int = 5) -> list[WorkerProfile]:
        """Get top N workers by completion count."""
        profiles = self._compute_worker_profiles()
        return profiles[:n]

    def worker_detail(self, worker_id: str) -> WorkerProfile | None:
        """Get detailed analytics for a specific worker."""
        profiles = self._compute_worker_profiles()
        for p in profiles:
            if p.worker_id == worker_id:
                return p
        return None

    # ── Category Analytics ───────────────────────────────────

    def category_comparison(self) -> list[CategoryBreakdown]:
        """Get all categories sorted by performance."""
        return self._compute_category_breakdown()

    # ── Value Analysis ───────────────────────────────────────

    def value_analysis(self) -> dict:
        """Analyze value: where is money well-spent vs wasted?"""
        if not self._events:
            return {"total_spent": 0, "total_wasted": 0, "roi": 0}

        total_spent = sum(e.bounty_usd for e in self._events)
        wasted = sum(e.bounty_usd for e in self._events if not e.is_success)
        successful_value = sum(
            e.bounty_usd * e.quality_score for e in self._events if e.is_success
        )

        return {
            "total_spent": total_spent,
            "total_wasted": wasted,
            "successful_spend": total_spent - wasted,
            "waste_rate": wasted / total_spent if total_spent > 0 else 0.0,
            "quality_adjusted_value": successful_value,
            "roi": successful_value / total_spent if total_spent > 0 else 0.0,
            "avg_cost_per_completion": (
                (total_spent - wasted) / sum(1 for e in self._events if e.is_success)
                if any(e.is_success for e in self._events)
                else 0.0
            ),
        }

    # ── Correlation Analysis ─────────────────────────────────

    def bounty_quality_correlation(self) -> dict:
        """Analyze relationship between bounty size and quality."""
        completed = [e for e in self._events if e.is_success and e.bounty_usd > 0]
        if len(completed) < 3:
            return {
                "correlation": 0.0,
                "sample_size": len(completed),
                "insight": "Insufficient data",
            }

        bounties = [e.bounty_usd for e in completed]
        qualities = [e.quality_score for e in completed]

        # Pearson correlation
        n = len(completed)
        sum_x = sum(bounties)
        sum_y = sum(qualities)
        sum_xy = sum(x * y for x, y in zip(bounties, qualities))
        sum_x2 = sum(x**2 for x in bounties)
        sum_y2 = sum(y**2 for y in qualities)

        denom_product = (n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2)
        denom = math.sqrt(max(0.0, denom_product))  # Guard against float rounding
        if denom == 0:
            corr = 0.0
        else:
            corr = (n * sum_xy - sum_x * sum_y) / denom

        if corr > 0.3:
            insight = "Higher bounties correlate with better quality. Consider premium pricing for critical tasks."
        elif corr < -0.3:
            insight = "Counter-intuitively, higher bounties don't improve quality. Review task design."
        else:
            insight = "Bounty size has minimal impact on quality. Focus on worker selection over pricing."

        return {
            "correlation": corr,
            "sample_size": n,
            "insight": insight,
            "avg_bounty": sum_x / n,
            "avg_quality": sum_y / n,
        }

    # ── Serialization ────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize analytics state."""
        return {
            "event_count": len(self._events),
            "series": {
                name: {
                    "name": s.name,
                    "latest": s.latest,
                    "average": s.average,
                    "trend": s.trend.value,
                    "point_count": len(s.points),
                }
                for name, s in self._series.items()
            },
            "alert_thresholds": self._alert_thresholds,
        }

    def stats(self) -> dict:
        """Quick stats snapshot."""
        return {
            "events_ingested": len(self._events),
            "series_tracked": len(self._series),
            "unique_workers": len({e.worker_id for e in self._events if e.worker_id}),
            "unique_categories": len({e.category for e in self._events if e.category}),
            "date_range": {
                "earliest": min(
                    (e.timestamp for e in self._events if e.timestamp > 0), default=0
                ),
                "latest": max(
                    (e.timestamp for e in self._events if e.timestamp > 0), default=0
                ),
            },
        }
