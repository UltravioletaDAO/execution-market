"""
SwarmAnalytics — Comprehensive performance analytics and decision support.

Provides real-time and historical analytics across the swarm:
1. **Agent Performance** — Per-agent success rates, throughput, earnings, specializations
2. **Task Pipeline** — Funnel analysis: created → assigned → completed → paid
3. **Financial Metrics** — Revenue, costs, margins, ROI per agent/category
4. **Operational Health** — SLA compliance, latency percentiles, error rates
5. **Trend Detection** — Performance trajectory, degradation alerts, growth signals
6. **Decision Support** — Recommendations for swarm scaling, budget allocation

Design:
- Stateless queries over event history (no separate DB)
- Time-window based aggregation (hourly, daily, weekly)
- Exportable reports for monitoring dashboards
- Integrates with HeartbeatHandler for periodic summaries
"""

import math
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger("em.swarm.analytics")


# ─── Data Models ──────────────────────────────────────────────────────────────


class TimeWindow(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL_TIME = "all_time"


WINDOW_SECONDS = {
    TimeWindow.HOUR: 3600,
    TimeWindow.DAY: 86400,
    TimeWindow.WEEK: 604800,
    TimeWindow.MONTH: 2592000,
    TimeWindow.ALL_TIME: float("inf"),
}


@dataclass
class TaskEvent:
    """A single task lifecycle event for analytics."""
    task_id: str
    event_type: str  # created, assigned, completed, failed, expired, cancelled
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    category: str = "unknown"
    bounty_usd: float = 0.0
    chain: str = "unknown"
    token: str = "USDC"
    timestamp: Optional[datetime] = None
    duration_seconds: Optional[float] = None  # Time from assignment to completion
    quality_score: Optional[float] = None  # 0.0 to 1.0
    evidence_types: list[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class AgentMetrics:
    """Aggregated metrics for a single agent."""
    agent_id: int
    agent_name: str = ""
    tasks_assigned: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_earnings_usd: float = 0.0
    avg_completion_time_s: float = 0.0
    avg_quality: float = 0.0
    categories: dict[str, int] = field(default_factory=dict)  # category → count
    chains: dict[str, int] = field(default_factory=dict)  # chain → count
    fastest_completion_s: float = float("inf")
    slowest_completion_s: float = 0.0
    active_streak: int = 0  # Current consecutive successes
    best_streak: int = 0

    @property
    def success_rate(self) -> float:
        total = self.tasks_completed + self.tasks_failed
        return self.tasks_completed / total if total > 0 else 0.0

    @property
    def avg_earnings_per_task(self) -> float:
        return self.total_earnings_usd / self.tasks_completed if self.tasks_completed > 0 else 0.0

    @property
    def primary_category(self) -> Optional[str]:
        if not self.categories:
            return None
        return max(self.categories, key=self.categories.get)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "tasks_assigned": self.tasks_assigned,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "success_rate": round(self.success_rate, 3),
            "total_earnings_usd": round(self.total_earnings_usd, 2),
            "avg_earnings_per_task": round(self.avg_earnings_per_task, 4),
            "avg_completion_time_s": round(self.avg_completion_time_s, 1),
            "avg_quality": round(self.avg_quality, 3),
            "primary_category": self.primary_category,
            "categories": dict(self.categories),
            "chains": dict(self.chains),
            "active_streak": self.active_streak,
            "best_streak": self.best_streak,
        }


@dataclass
class PipelineMetrics:
    """Task pipeline funnel metrics."""
    created: int = 0
    assigned: int = 0
    completed: int = 0
    failed: int = 0
    expired: int = 0
    cancelled: int = 0

    @property
    def assignment_rate(self) -> float:
        return self.assigned / self.created if self.created > 0 else 0.0

    @property
    def completion_rate(self) -> float:
        return self.completed / self.assigned if self.assigned > 0 else 0.0

    @property
    def failure_rate(self) -> float:
        total_resolved = self.completed + self.failed
        return self.failed / total_resolved if total_resolved > 0 else 0.0

    @property
    def expiry_rate(self) -> float:
        return self.expired / self.created if self.created > 0 else 0.0

    @property
    def overall_throughput(self) -> float:
        """End-to-end: created → completed."""
        return self.completed / self.created if self.created > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "assigned": self.assigned,
            "completed": self.completed,
            "failed": self.failed,
            "expired": self.expired,
            "cancelled": self.cancelled,
            "assignment_rate": round(self.assignment_rate, 3),
            "completion_rate": round(self.completion_rate, 3),
            "failure_rate": round(self.failure_rate, 3),
            "expiry_rate": round(self.expiry_rate, 3),
            "overall_throughput": round(self.overall_throughput, 3),
        }


@dataclass
class FinancialMetrics:
    """Financial performance metrics."""
    total_bounty_usd: float = 0.0
    total_paid_usd: float = 0.0
    platform_fees_usd: float = 0.0
    avg_bounty_usd: float = 0.0
    median_bounty_usd: float = 0.0
    bounties: list[float] = field(default_factory=list)
    by_chain: dict[str, float] = field(default_factory=dict)
    by_token: dict[str, float] = field(default_factory=dict)
    by_category: dict[str, float] = field(default_factory=dict)

    def compute_stats(self) -> None:
        """Compute derived stats from bounties list."""
        if not self.bounties:
            return
        self.avg_bounty_usd = sum(self.bounties) / len(self.bounties)
        sorted_b = sorted(self.bounties)
        n = len(sorted_b)
        self.median_bounty_usd = (
            sorted_b[n // 2]
            if n % 2 == 1
            else (sorted_b[n // 2 - 1] + sorted_b[n // 2]) / 2
        )

    def to_dict(self) -> dict:
        return {
            "total_bounty_usd": round(self.total_bounty_usd, 2),
            "total_paid_usd": round(self.total_paid_usd, 2),
            "platform_fees_usd": round(self.platform_fees_usd, 2),
            "avg_bounty_usd": round(self.avg_bounty_usd, 4),
            "median_bounty_usd": round(self.median_bounty_usd, 4),
            "task_count": len(self.bounties),
            "by_chain": {k: round(v, 2) for k, v in self.by_chain.items()},
            "by_token": {k: round(v, 2) for k, v in self.by_token.items()},
            "by_category": {k: round(v, 2) for k, v in self.by_category.items()},
        }


@dataclass
class HealthMetrics:
    """Operational health metrics."""
    total_events: int = 0
    error_count: int = 0
    avg_latency_s: float = 0.0
    p50_latency_s: float = 0.0
    p90_latency_s: float = 0.0
    p99_latency_s: float = 0.0
    latencies: list[float] = field(default_factory=list)
    sla_target_seconds: float = 3600.0  # 1 hour default SLA
    sla_compliant: int = 0
    sla_violations: int = 0

    def compute_percentiles(self) -> None:
        """Compute latency percentiles."""
        if not self.latencies:
            return
        sorted_l = sorted(self.latencies)
        n = len(sorted_l)
        self.avg_latency_s = sum(sorted_l) / n
        self.p50_latency_s = sorted_l[int(n * 0.50)]
        self.p90_latency_s = sorted_l[int(min(n * 0.90, n - 1))]
        self.p99_latency_s = sorted_l[int(min(n * 0.99, n - 1))]

    @property
    def sla_compliance_rate(self) -> float:
        total = self.sla_compliant + self.sla_violations
        return self.sla_compliant / total if total > 0 else 0.0

    @property
    def error_rate(self) -> float:
        return self.error_count / self.total_events if self.total_events > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "total_events": self.total_events,
            "error_count": self.error_count,
            "error_rate": round(self.error_rate, 4),
            "avg_latency_s": round(self.avg_latency_s, 1),
            "p50_latency_s": round(self.p50_latency_s, 1),
            "p90_latency_s": round(self.p90_latency_s, 1),
            "p99_latency_s": round(self.p99_latency_s, 1),
            "sla_target_s": self.sla_target_seconds,
            "sla_compliance": round(self.sla_compliance_rate, 3),
            "sla_violations": self.sla_violations,
        }


@dataclass
class TrendPoint:
    """A single data point in a time series trend."""
    timestamp: datetime
    value: float
    label: str = ""


@dataclass
class TrendAnalysis:
    """Trend detection results."""
    metric_name: str
    direction: str = "stable"  # improving, degrading, stable, volatile
    slope: float = 0.0  # Rate of change per day
    confidence: float = 0.0  # 0.0 to 1.0
    data_points: int = 0
    current_value: float = 0.0
    period_avg: float = 0.0
    period_min: float = 0.0
    period_max: float = 0.0
    alert: Optional[str] = None

    def to_dict(self) -> dict:
        result = {
            "metric": self.metric_name,
            "direction": self.direction,
            "slope_per_day": round(self.slope, 4),
            "confidence": round(self.confidence, 3),
            "data_points": self.data_points,
            "current": round(self.current_value, 4),
            "avg": round(self.period_avg, 4),
            "min": round(self.period_min, 4),
            "max": round(self.period_max, 4),
        }
        if self.alert:
            result["alert"] = self.alert
        return result


@dataclass
class SwarmRecommendation:
    """Decision support recommendation."""
    category: str  # scaling, budget, routing, health
    priority: str  # critical, high, medium, low
    title: str
    description: str
    action: str  # What should be done
    impact: str  # Expected impact
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "action": self.action,
            "impact": self.impact,
            "data": self.data,
        }


# ─── Analytics Engine ─────────────────────────────────────────────────────────


class SwarmAnalytics:
    """
    Comprehensive swarm analytics engine.

    Usage:
        analytics = SwarmAnalytics()

        # Ingest events
        analytics.record_event(TaskEvent(
            task_id="t1", event_type="created",
            category="photo", bounty_usd=0.10, chain="base"
        ))
        analytics.record_event(TaskEvent(
            task_id="t1", event_type="assigned", agent_id=1, agent_name="aurora"
        ))
        analytics.record_event(TaskEvent(
            task_id="t1", event_type="completed", agent_id=1,
            duration_seconds=120, quality_score=0.95
        ))

        # Query analytics
        report = analytics.full_report(window=TimeWindow.DAY)
        agent_metrics = analytics.agent_performance(agent_id=1)
        trends = analytics.detect_trends(metric="completion_rate")
        recs = analytics.recommendations()
    """

    def __init__(self, sla_target_seconds: float = 3600.0, platform_fee_rate: float = 0.13):
        self._events: list[TaskEvent] = []
        self._sla_target = sla_target_seconds
        self._fee_rate = platform_fee_rate

    @property
    def event_count(self) -> int:
        return len(self._events)

    def record_event(self, event: TaskEvent) -> None:
        """Record a task lifecycle event."""
        self._events.append(event)

    def record_events(self, events: list[TaskEvent]) -> None:
        """Record multiple events at once."""
        self._events.extend(events)

    def clear(self) -> None:
        """Clear all events (for testing)."""
        self._events.clear()

    # ─── Time-window filtering ────────────────────────────────────────

    def _filter_by_window(
        self,
        events: list[TaskEvent],
        window: TimeWindow,
        reference_time: Optional[datetime] = None,
    ) -> list[TaskEvent]:
        """Filter events within a time window."""
        if window == TimeWindow.ALL_TIME:
            return events

        cutoff_seconds = WINDOW_SECONDS[window]
        now = reference_time or datetime.now(timezone.utc)

        return [
            e for e in events
            if e.timestamp and (now - e.timestamp).total_seconds() <= cutoff_seconds
        ]

    def _events_by_type(
        self,
        event_type: str,
        window: TimeWindow = TimeWindow.ALL_TIME,
    ) -> list[TaskEvent]:
        """Get events of a specific type within a window."""
        filtered = self._filter_by_window(self._events, window)
        return [e for e in filtered if e.event_type == event_type]

    # ─── Agent Performance ────────────────────────────────────────────

    def agent_performance(
        self,
        agent_id: Optional[int] = None,
        window: TimeWindow = TimeWindow.ALL_TIME,
    ) -> AgentMetrics | list[AgentMetrics]:
        """
        Get performance metrics for one agent or all agents.
        Returns single AgentMetrics if agent_id specified, else list sorted by earnings.
        """
        filtered = self._filter_by_window(self._events, window)

        # Group by agent
        agent_events: dict[int, list[TaskEvent]] = defaultdict(list)
        for e in filtered:
            if e.agent_id is not None:
                agent_events[e.agent_id].append(e)

        if agent_id is not None:
            return self._compute_agent_metrics(agent_id, agent_events.get(agent_id, []))

        # All agents
        results = []
        for aid, events in agent_events.items():
            results.append(self._compute_agent_metrics(aid, events))

        results.sort(key=lambda m: m.total_earnings_usd, reverse=True)
        return results

    def _compute_agent_metrics(self, agent_id: int, events: list[TaskEvent]) -> AgentMetrics:
        """Compute metrics for a single agent from their events."""
        metrics = AgentMetrics(agent_id=agent_id)

        completion_times = []
        quality_scores = []
        streak = 0

        for e in events:
            if not metrics.agent_name and e.agent_name:
                metrics.agent_name = e.agent_name

            if e.event_type == "assigned":
                metrics.tasks_assigned += 1

            elif e.event_type == "completed":
                metrics.tasks_completed += 1
                metrics.total_earnings_usd += e.bounty_usd
                streak += 1
                metrics.active_streak = streak
                metrics.best_streak = max(metrics.best_streak, streak)

                if e.duration_seconds is not None and e.duration_seconds > 0:
                    completion_times.append(e.duration_seconds)
                    if e.duration_seconds < metrics.fastest_completion_s:
                        metrics.fastest_completion_s = e.duration_seconds
                    if e.duration_seconds > metrics.slowest_completion_s:
                        metrics.slowest_completion_s = e.duration_seconds

                if e.quality_score is not None:
                    quality_scores.append(e.quality_score)

                if e.category and e.category != "unknown":
                    metrics.categories[e.category] = metrics.categories.get(e.category, 0) + 1
                if e.chain and e.chain != "unknown":
                    metrics.chains[e.chain] = metrics.chains.get(e.chain, 0) + 1

            elif e.event_type == "failed":
                metrics.tasks_failed += 1
                streak = 0
                metrics.active_streak = 0

        if completion_times:
            metrics.avg_completion_time_s = sum(completion_times) / len(completion_times)
        if quality_scores:
            metrics.avg_quality = sum(quality_scores) / len(quality_scores)

        return metrics

    # ─── Pipeline Analysis ────────────────────────────────────────────

    def pipeline_metrics(self, window: TimeWindow = TimeWindow.ALL_TIME) -> PipelineMetrics:
        """Compute task pipeline funnel metrics."""
        filtered = self._filter_by_window(self._events, window)
        metrics = PipelineMetrics()

        for e in filtered:
            if e.event_type == "created":
                metrics.created += 1
            elif e.event_type == "assigned":
                metrics.assigned += 1
            elif e.event_type == "completed":
                metrics.completed += 1
            elif e.event_type == "failed":
                metrics.failed += 1
            elif e.event_type == "expired":
                metrics.expired += 1
            elif e.event_type == "cancelled":
                metrics.cancelled += 1

        return metrics

    # ─── Financial Analysis ───────────────────────────────────────────

    def financial_metrics(self, window: TimeWindow = TimeWindow.ALL_TIME) -> FinancialMetrics:
        """Compute financial performance metrics."""
        completed = self._events_by_type("completed", window)
        metrics = FinancialMetrics()

        for e in completed:
            bounty = e.bounty_usd
            metrics.total_bounty_usd += bounty
            metrics.bounties.append(bounty)

            fee = bounty * self._fee_rate
            metrics.platform_fees_usd += fee
            metrics.total_paid_usd += bounty - fee

            chain = e.chain or "unknown"
            metrics.by_chain[chain] = metrics.by_chain.get(chain, 0) + bounty

            token = e.token or "USDC"
            metrics.by_token[token] = metrics.by_token.get(token, 0) + bounty

            category = e.category or "unknown"
            metrics.by_category[category] = metrics.by_category.get(category, 0) + bounty

        metrics.compute_stats()
        return metrics

    # ─── Health Analysis ──────────────────────────────────────────────

    def health_metrics(
        self,
        window: TimeWindow = TimeWindow.ALL_TIME,
        sla_target_seconds: Optional[float] = None,
    ) -> HealthMetrics:
        """Compute operational health metrics."""
        sla = sla_target_seconds or self._sla_target
        filtered = self._filter_by_window(self._events, window)

        metrics = HealthMetrics(sla_target_seconds=sla)
        metrics.total_events = len(filtered)

        for e in filtered:
            if e.error:
                metrics.error_count += 1

            if e.event_type == "completed" and e.duration_seconds is not None:
                metrics.latencies.append(e.duration_seconds)
                if e.duration_seconds <= sla:
                    metrics.sla_compliant += 1
                else:
                    metrics.sla_violations += 1

        metrics.compute_percentiles()
        return metrics

    # ─── Trend Detection ─────────────────────────────────────────────

    def detect_trends(
        self,
        metric: str = "completion_rate",
        window: TimeWindow = TimeWindow.WEEK,
        bucket_hours: int = 24,
    ) -> TrendAnalysis:
        """
        Detect performance trends over time by bucketing events.

        Supported metrics: completion_rate, avg_quality, avg_bounty,
                          throughput, error_rate
        """
        filtered = self._filter_by_window(self._events, window)
        if not filtered:
            return TrendAnalysis(metric_name=metric, data_points=0)

        # Sort by timestamp
        sorted_events = sorted(filtered, key=lambda e: e.timestamp)

        # Bucket by time intervals
        bucket_delta = timedelta(hours=bucket_hours)
        buckets: dict[int, list[TaskEvent]] = defaultdict(list)

        start_time = sorted_events[0].timestamp
        for e in sorted_events:
            bucket_idx = int((e.timestamp - start_time).total_seconds() / bucket_delta.total_seconds())
            buckets[bucket_idx].append(e)

        if len(buckets) < 2:
            return TrendAnalysis(
                metric_name=metric,
                data_points=len(buckets),
                direction="stable",
            )

        # Compute metric per bucket
        values = []
        for idx in sorted(buckets.keys()):
            bucket_events = buckets[idx]
            value = self._compute_bucket_metric(metric, bucket_events)
            if value is not None:
                values.append(value)

        if len(values) < 2:
            return TrendAnalysis(metric_name=metric, data_points=len(values))

        # Linear regression for slope
        n = len(values)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator > 0 else 0

        # R² for confidence
        ss_res = sum((values[i] - (y_mean + slope * (x[i] - x_mean))) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # Determine direction
        threshold = 0.01  # Minimum slope to count as a trend
        if abs(slope) < threshold:
            direction = "stable"
        elif slope > 0:
            direction = "improving"
        else:
            direction = "degrading"

        # Volatility check: high variance relative to mean
        if n > 2 and y_mean > 0:
            variance = sum((v - y_mean) ** 2 for v in values) / n
            cv = math.sqrt(variance) / abs(y_mean)
            if cv > 0.5 and r_squared < 0.3:
                direction = "volatile"

        # Generate alerts
        alert = None
        if direction == "degrading" and r_squared > 0.5:
            alert = f"{metric} has been declining with high confidence (R²={r_squared:.2f})"
        elif direction == "volatile":
            alert = f"{metric} is highly volatile — investigate root cause"

        return TrendAnalysis(
            metric_name=metric,
            direction=direction,
            slope=slope * (24 / bucket_hours),  # Normalize to per-day
            confidence=max(0, r_squared),
            data_points=n,
            current_value=values[-1],
            period_avg=y_mean,
            period_min=min(values),
            period_max=max(values),
            alert=alert,
        )

    def _compute_bucket_metric(self, metric: str, events: list[TaskEvent]) -> Optional[float]:
        """Compute a single metric value from a bucket of events."""
        if metric == "completion_rate":
            completed = sum(1 for e in events if e.event_type == "completed")
            assigned = sum(1 for e in events if e.event_type == "assigned")
            return completed / assigned if assigned > 0 else None

        elif metric == "avg_quality":
            scores = [e.quality_score for e in events if e.quality_score is not None]
            return sum(scores) / len(scores) if scores else None

        elif metric == "avg_bounty":
            bounties = [e.bounty_usd for e in events if e.event_type == "completed" and e.bounty_usd > 0]
            return sum(bounties) / len(bounties) if bounties else None

        elif metric == "throughput":
            return sum(1 for e in events if e.event_type == "completed")

        elif metric == "error_rate":
            total = len(events)
            errors = sum(1 for e in events if e.error)
            return errors / total if total > 0 else None

        return None

    # ─── Category Analysis ────────────────────────────────────────────

    def category_breakdown(
        self, window: TimeWindow = TimeWindow.ALL_TIME
    ) -> dict[str, dict]:
        """Break down performance by task category."""
        completed = self._events_by_type("completed", window)
        failed = self._events_by_type("failed", window)
        created = self._events_by_type("created", window)

        categories: dict[str, dict] = defaultdict(lambda: {
            "created": 0, "completed": 0, "failed": 0,
            "total_bounty": 0.0, "avg_quality": 0.0,
            "qualities": [], "completion_times": [],
        })

        for e in created:
            categories[e.category]["created"] += 1

        for e in completed:
            cat = categories[e.category]
            cat["completed"] += 1
            cat["total_bounty"] += e.bounty_usd
            if e.quality_score is not None:
                cat["qualities"].append(e.quality_score)
            if e.duration_seconds is not None:
                cat["completion_times"].append(e.duration_seconds)

        for e in failed:
            categories[e.category]["failed"] += 1

        # Compute derived metrics
        result = {}
        for cat_name, data in categories.items():
            quals = data.pop("qualities")
            times = data.pop("completion_times")
            data["avg_quality"] = sum(quals) / len(quals) if quals else 0.0
            data["avg_completion_time_s"] = sum(times) / len(times) if times else 0.0
            data["success_rate"] = (
                data["completed"] / (data["completed"] + data["failed"])
                if (data["completed"] + data["failed"]) > 0
                else 0.0
            )
            # Round floats
            for k in ["total_bounty", "avg_quality", "avg_completion_time_s", "success_rate"]:
                data[k] = round(data[k], 3)
            result[cat_name] = data

        return result

    # ─── Chain Analysis ───────────────────────────────────────────────

    def chain_breakdown(
        self, window: TimeWindow = TimeWindow.ALL_TIME
    ) -> dict[str, dict]:
        """Break down performance by blockchain."""
        completed = self._events_by_type("completed", window)

        chains: dict[str, dict] = defaultdict(lambda: {
            "tasks": 0, "total_bounty": 0.0, "avg_bounty": 0.0,
        })

        for e in completed:
            chain = e.chain or "unknown"
            chains[chain]["tasks"] += 1
            chains[chain]["total_bounty"] += e.bounty_usd

        for data in chains.values():
            data["avg_bounty"] = round(
                data["total_bounty"] / data["tasks"] if data["tasks"] > 0 else 0.0, 4
            )
            data["total_bounty"] = round(data["total_bounty"], 2)

        return dict(chains)

    # ─── Recommendations ─────────────────────────────────────────────

    def recommendations(
        self,
        window: TimeWindow = TimeWindow.WEEK,
    ) -> list[SwarmRecommendation]:
        """Generate actionable recommendations based on analytics."""
        recs = []

        pipeline = self.pipeline_metrics(window)
        financial = self.financial_metrics(window)
        health = self.health_metrics(window)

        # 1. High expiry rate → need more workers or better matching
        if pipeline.expiry_rate > 0.30:
            recs.append(SwarmRecommendation(
                category="scaling",
                priority="high",
                title="High task expiry rate",
                description=f"Expiry rate is {pipeline.expiry_rate:.0%} — tasks aren't finding workers",
                action="Register more agents or broaden task categories",
                impact="Could recover {:.0f} tasks/week".format(
                    pipeline.expired * (1 - 0.10)  # Target 10% expiry
                ),
                data={"current_rate": pipeline.expiry_rate, "target_rate": 0.10},
            ))

        # 2. Low completion rate → routing or quality issue
        if pipeline.assigned > 5 and pipeline.completion_rate < 0.70:
            recs.append(SwarmRecommendation(
                category="routing",
                priority="high",
                title="Low task completion rate",
                description=f"Only {pipeline.completion_rate:.0%} of assigned tasks complete",
                action="Review routing strategy — agents may be mismatched",
                impact="Improve worker-task fit to target 90%+ completion",
                data={"current_rate": pipeline.completion_rate, "target_rate": 0.90},
            ))

        # 3. SLA violations → latency issue
        if health.sla_violations > 3:
            recs.append(SwarmRecommendation(
                category="health",
                priority="medium",
                title="SLA violations detected",
                description=f"{health.sla_violations} tasks exceeded {health.sla_target_seconds/3600:.0f}h SLA",
                action="Add deadline-aware routing or increase agent pool",
                impact=f"Improve SLA compliance from {health.sla_compliance_rate:.0%} to 95%+",
                data={
                    "violations": health.sla_violations,
                    "compliance": health.sla_compliance_rate,
                    "p90_latency_s": health.p90_latency_s,
                },
            ))

        # 4. Single-category concentration → diversify
        categories = self.category_breakdown(window)
        if len(categories) == 1 and pipeline.completed > 10:
            cat_name = list(categories.keys())[0]
            recs.append(SwarmRecommendation(
                category="scaling",
                priority="medium",
                title="Task category concentration",
                description=f"All tasks are '{cat_name}' — swarm has unused potential",
                action="Create tasks in diverse categories to build agent skills",
                impact="Richer Skill DNA, better routing, more versatile swarm",
                data={"sole_category": cat_name},
            ))

        # 5. Budget underutilization → scale up
        if financial.total_bounty_usd > 0 and pipeline.completed > 0:
            avg_cost = financial.avg_bounty_usd
            if avg_cost < 0.10:
                recs.append(SwarmRecommendation(
                    category="budget",
                    priority="low",
                    title="Very low average bounty",
                    description=f"Average bounty is ${avg_cost:.4f} — workers may not be incentivized",
                    action="Consider increasing bounties for complex tasks",
                    impact="Higher worker participation and quality",
                    data={"avg_bounty": avg_cost},
                ))

        # 6. High error rate
        if health.error_rate > 0.10:
            recs.append(SwarmRecommendation(
                category="health",
                priority="critical",
                title="High error rate",
                description=f"Error rate is {health.error_rate:.0%}",
                action="Investigate error logs and fix root causes",
                impact="Reduce operational costs and improve reliability",
                data={"error_rate": health.error_rate, "error_count": health.error_count},
            ))

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recs.sort(key=lambda r: priority_order.get(r.priority, 9))

        return recs

    # ─── Full Report ──────────────────────────────────────────────────

    def full_report(
        self,
        window: TimeWindow = TimeWindow.ALL_TIME,
    ) -> dict:
        """Generate comprehensive analytics report."""
        agent_metrics = self.agent_performance(window=window)
        agent_list = agent_metrics if isinstance(agent_metrics, list) else [agent_metrics]

        return {
            "window": window.value,
            "total_events": len(self._filter_by_window(self._events, window)),
            "pipeline": self.pipeline_metrics(window).to_dict(),
            "financial": self.financial_metrics(window).to_dict(),
            "health": self.health_metrics(window).to_dict(),
            "agents": [a.to_dict() for a in agent_list],
            "categories": self.category_breakdown(window),
            "chains": self.chain_breakdown(window),
            "recommendations": [r.to_dict() for r in self.recommendations(window)],
        }

    def summary(self, window: TimeWindow = TimeWindow.DAY) -> str:
        """Generate a human-readable summary string."""
        pipeline = self.pipeline_metrics(window)
        financial = self.financial_metrics(window)
        health = self.health_metrics(window)

        lines = [
            f"📊 **Swarm Analytics** ({window.value})",
            f"",
            f"**Pipeline:** {pipeline.created} created → {pipeline.assigned} assigned → {pipeline.completed} completed",
            f"**Throughput:** {pipeline.overall_throughput:.0%} | Expiry: {pipeline.expiry_rate:.0%}",
        ]

        if financial.total_bounty_usd > 0:
            lines.append(
                f"**Revenue:** ${financial.total_bounty_usd:.2f} total | "
                f"${financial.avg_bounty_usd:.4f} avg/task | "
                f"${financial.platform_fees_usd:.2f} fees"
            )

        if health.latencies:
            lines.append(
                f"**Latency:** p50={health.p50_latency_s:.0f}s p90={health.p90_latency_s:.0f}s | "
                f"SLA: {health.sla_compliance_rate:.0%}"
            )

        recs = self.recommendations(window)
        if recs:
            lines.append(f"")
            lines.append(f"**Recommendations:** {len(recs)}")
            for r in recs[:3]:
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(r.priority, "⚪")
                lines.append(f"  {emoji} {r.title}")

        return "\n".join(lines)


# ─── Convenience: Load analytics from production data ─────────────────────────


def load_from_production_tasks(tasks: list[dict], analytics: Optional[SwarmAnalytics] = None) -> SwarmAnalytics:
    """
    Load analytics from EM API task data (list of task dicts).

    Expected task dict fields:
        id, title, status, category, bounty, chain, token,
        created_at, completed_at, assigned_to, evidence
    """
    if analytics is None:
        analytics = SwarmAnalytics()

    for task in tasks:
        task_id = str(task.get("id", ""))
        status = task.get("status", "")
        category = task.get("category", "unknown")
        bounty = float(task.get("bounty", 0))
        chain = task.get("chain", "unknown")
        token = task.get("token", "USDC")
        agent_id = task.get("assigned_to")

        created_at = _parse_datetime(task.get("created_at"))
        completed_at = _parse_datetime(task.get("completed_at"))

        # Always record creation
        analytics.record_event(TaskEvent(
            task_id=task_id,
            event_type="created",
            category=category,
            bounty_usd=bounty,
            chain=chain,
            token=token,
            timestamp=created_at,
        ))

        # Record assignment if we know the agent
        if agent_id is not None:
            analytics.record_event(TaskEvent(
                task_id=task_id,
                event_type="assigned",
                agent_id=int(agent_id) if agent_id else None,
                category=category,
                bounty_usd=bounty,
                chain=chain,
                token=token,
                timestamp=created_at,  # Approximate
            ))

        # Record outcome
        if status == "completed":
            duration = None
            if created_at and completed_at:
                duration = (completed_at - created_at).total_seconds()

            evidence = task.get("evidence", [])
            evidence_types = []
            quality = None
            if isinstance(evidence, list):
                evidence_types = [e.get("type", "") for e in evidence if isinstance(e, dict)]
                # Heuristic quality from evidence richness
                if evidence_types:
                    quality = min(0.5 + len(evidence_types) * 0.1, 1.0)

            analytics.record_event(TaskEvent(
                task_id=task_id,
                event_type="completed",
                agent_id=int(agent_id) if agent_id else None,
                category=category,
                bounty_usd=bounty,
                chain=chain,
                token=token,
                timestamp=completed_at or created_at,
                duration_seconds=duration,
                quality_score=quality,
                evidence_types=evidence_types,
            ))

        elif status == "failed":
            analytics.record_event(TaskEvent(
                task_id=task_id,
                event_type="failed",
                agent_id=int(agent_id) if agent_id else None,
                category=category,
                bounty_usd=bounty,
                chain=chain,
                timestamp=completed_at or created_at,
                error=task.get("error", "unknown"),
            ))

        elif status == "expired":
            analytics.record_event(TaskEvent(
                task_id=task_id,
                event_type="expired",
                category=category,
                bounty_usd=bounty,
                chain=chain,
                timestamp=completed_at or created_at,
            ))

        elif status == "cancelled":
            analytics.record_event(TaskEvent(
                task_id=task_id,
                event_type="cancelled",
                category=category,
                bounty_usd=bounty,
                chain=chain,
                timestamp=completed_at or created_at,
            ))

    return analytics


def _parse_datetime(value) -> Optional[datetime]:
    """Parse a datetime string or return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        # Handle ISO format with Z or +00:00
        s = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
