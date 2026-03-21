"""
Metrics Collector — Swarm Observability Engine
================================================

Collects, aggregates, and reports metrics across all swarm modules.
Provides the data layer for dashboards, alerts, and performance
optimization. Designed to answer: "Is the swarm healthy? Is it
improving? What needs attention?"

Metric categories:
    1. Routing: task assignment accuracy, match scores, response times
    2. Workforce: active workers, skill coverage, concentration
    3. Pipeline: ingest/match/feedback throughput, error rates
    4. Performance: end-to-end latency, task completion rates
    5. Health: source availability, stale profiles, dead zones

Usage:
    from swarm.metrics_collector import MetricsCollector

    metrics = MetricsCollector()
    metrics.record_routing("task_123", "0xWorker", score=85.0)
    metrics.record_completion("task_123", quality=0.9, hours=2.5)
    report = metrics.summary()
"""

import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import timezone
from typing import Optional, Any

UTC = timezone.utc

# Maximum events to keep in memory per category
MAX_EVENTS_PER_CATEGORY = 1000

# Time window for "recent" metrics (seconds)
RECENT_WINDOW_SECONDS = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Metric Event Types
# ---------------------------------------------------------------------------


@dataclass
class MetricEvent:
    """A single recorded metric event."""

    category: str
    name: str
    value: float
    timestamp: float  # Unix timestamp
    tags: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Metrics Collector
# ---------------------------------------------------------------------------


class MetricsCollector:
    """Collects and aggregates swarm metrics.

    Thread-safe for single-threaded async use. For multi-threaded
    environments, wrap with a lock.
    """

    def __init__(self, max_events: int = MAX_EVENTS_PER_CATEGORY):
        self.max_events = max_events
        self._events: dict = defaultdict(lambda: deque(maxlen=max_events))
        self._counters: dict = Counter()
        self._gauges: dict = {}
        self._started_at = time.time()

    # -------------------------------------------------------------------
    # Recording Methods
    # -------------------------------------------------------------------

    def record_routing(
        self,
        task_id: str,
        worker_wallet: str,
        score: float,
        response_minutes: Optional[float] = None,
        available_now: bool = True,
    ):
        """Record a task routing decision."""
        self._record(
            "routing",
            "task_routed",
            score,
            {
                "task_id": task_id,
                "worker": worker_wallet,
                "available_now": available_now,
            },
        )
        self._counters["routing.total"] += 1
        if available_now:
            self._counters["routing.to_available"] += 1
        if response_minutes is not None:
            self._record(
                "routing",
                "response_time",
                response_minutes,
                {
                    "task_id": task_id,
                },
            )

    def record_completion(
        self,
        task_id: str,
        quality: float = 0.5,
        hours_to_complete: Optional[float] = None,
        on_time: bool = True,
    ):
        """Record a task completion."""
        self._record(
            "completion",
            "task_completed",
            quality,
            {
                "task_id": task_id,
                "on_time": on_time,
            },
        )
        self._counters["completion.total"] += 1
        if on_time:
            self._counters["completion.on_time"] += 1
        if hours_to_complete is not None:
            self._record(
                "completion",
                "time_to_complete",
                hours_to_complete,
                {
                    "task_id": task_id,
                },
            )

    def record_expiry(self, task_id: str, reason: str = "timeout"):
        """Record a task expiry (not completed in time)."""
        self._record(
            "completion",
            "task_expired",
            1.0,
            {
                "task_id": task_id,
                "reason": reason,
            },
        )
        self._counters["completion.expired"] += 1

    def record_pipeline(
        self,
        pipeline_name: str,
        status: str,
        duration_ms: float,
    ):
        """Record a pipeline execution."""
        self._record(
            "pipeline",
            f"{pipeline_name}_{status}",
            duration_ms,
            {
                "pipeline": pipeline_name,
            },
        )
        self._counters[f"pipeline.{pipeline_name}.total"] += 1
        if status == "success":
            self._counters[f"pipeline.{pipeline_name}.success"] += 1
        elif status == "error":
            self._counters[f"pipeline.{pipeline_name}.error"] += 1

    def record_worker_activity(self, wallet: str, action: str):
        """Record worker activity (joined, active, left, etc.)."""
        self._record("workforce", action, 1.0, {"wallet": wallet})
        self._counters[f"workforce.{action}"] += 1

    def record_source_health(
        self,
        source_name: str,
        status: str,
        quality: float,
    ):
        """Record a job source health check result."""
        self._record(
            "health",
            "source_check",
            quality,
            {
                "source": source_name,
                "status": status,
            },
        )
        self._gauges[f"source.{source_name}.quality"] = quality
        self._gauges[f"source.{source_name}.status"] = status

    def set_gauge(self, name: str, value: Any):
        """Set a point-in-time gauge value."""
        self._gauges[name] = value

    def increment(self, name: str, amount: int = 1):
        """Increment a counter."""
        self._counters[name] += amount

    # -------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------

    def summary(self, window_seconds: int = RECENT_WINDOW_SECONDS) -> dict:
        """Generate comprehensive metrics summary.

        Args:
            window_seconds: Only include events from this recent window

        Returns:
            Dict with routing, completion, pipeline, workforce, health sections
        """
        cutoff = time.time() - window_seconds
        uptime = time.time() - self._started_at

        return {
            "uptime_seconds": round(uptime, 1),
            "window_seconds": window_seconds,
            "routing": self._routing_summary(cutoff),
            "completion": self._completion_summary(cutoff),
            "pipeline": self._pipeline_summary(cutoff),
            "workforce": self._workforce_summary(),
            "health": self._health_summary(),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
        }

    def get_events(
        self,
        category: str,
        limit: int = 50,
        since: Optional[float] = None,
    ) -> list:
        """Get recent events for a category."""
        events = list(self._events.get(category, []))
        if since:
            events = [e for e in events if e.timestamp >= since]
        events.sort(key=lambda e: -e.timestamp)
        return [asdict(e) for e in events[:limit]]

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> Any:
        return self._gauges.get(name)

    # -------------------------------------------------------------------
    # Trend Analysis
    # -------------------------------------------------------------------

    def trend(
        self,
        category: str,
        name: str,
        buckets: int = 6,
        window_seconds: int = RECENT_WINDOW_SECONDS,
    ) -> list:
        """Compute trend over time (value per bucket).

        Returns list of {bucket_start, bucket_end, count, avg_value}
        """
        now = time.time()
        bucket_size = window_seconds / buckets
        result = []

        events = [
            e
            for e in self._events.get(category, [])
            if e.timestamp >= now - window_seconds and e.name == name
        ]

        for i in range(buckets):
            bucket_start = now - window_seconds + i * bucket_size
            bucket_end = bucket_start + bucket_size
            bucket_events = [
                e for e in events if bucket_start <= e.timestamp < bucket_end
            ]

            values = [e.value for e in bucket_events]
            result.append(
                {
                    "bucket": i,
                    "count": len(bucket_events),
                    "avg_value": round(sum(values) / len(values), 3)
                    if values
                    else None,
                    "min_value": round(min(values), 3) if values else None,
                    "max_value": round(max(values), 3) if values else None,
                }
            )

        return result

    # -------------------------------------------------------------------
    # Alert Conditions
    # -------------------------------------------------------------------

    def check_alerts(self) -> list:
        """Check for conditions that should trigger alerts.

        Returns list of alert dicts.
        """
        alerts = []

        # High expiry rate
        total = self._counters.get("completion.total", 0) + self._counters.get(
            "completion.expired", 0
        )
        expired = self._counters.get("completion.expired", 0)
        if total >= 5:
            expiry_rate = expired / total
            if expiry_rate > 0.3:
                alerts.append(
                    {
                        "level": "critical" if expiry_rate > 0.5 else "warning",
                        "type": "high_expiry_rate",
                        "value": round(expiry_rate, 3),
                        "message": f"Task expiry rate is {expiry_rate:.0%} ({expired}/{total})",
                    }
                )

        # Pipeline errors
        for key, count in self._counters.items():
            if key.endswith(".error") and count > 0:
                pipeline = key.replace("pipeline.", "").replace(".error", "")
                total_key = key.replace(".error", ".total")
                total = self._counters.get(total_key, count)
                error_rate = count / total if total > 0 else 1.0
                if error_rate > 0.2:
                    alerts.append(
                        {
                            "level": "warning",
                            "type": "pipeline_errors",
                            "pipeline": pipeline,
                            "error_rate": round(error_rate, 3),
                            "message": f"Pipeline '{pipeline}' error rate: {error_rate:.0%}",
                        }
                    )

        # Low routing-to-available rate
        routing_total = self._counters.get("routing.total", 0)
        routing_avail = self._counters.get("routing.to_available", 0)
        if routing_total >= 5:
            avail_rate = routing_avail / routing_total
            if avail_rate < 0.5:
                alerts.append(
                    {
                        "level": "warning",
                        "type": "low_availability_routing",
                        "value": round(avail_rate, 3),
                        "message": f"Only {avail_rate:.0%} of tasks routed to available workers",
                    }
                )

        return alerts

    # -------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------

    def reset(self):
        """Reset all metrics."""
        self._events.clear()
        self._counters.clear()
        self._gauges.clear()
        self._started_at = time.time()

    # -------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------

    def _record(self, category: str, name: str, value: float, tags: dict):
        event = MetricEvent(
            category=category,
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags,
        )
        self._events[category].append(event)

    def _routing_summary(self, cutoff: float) -> dict:
        events = [e for e in self._events.get("routing", []) if e.timestamp >= cutoff]
        routed = [e for e in events if e.name == "task_routed"]
        response_times = [e for e in events if e.name == "response_time"]

        scores = [e.value for e in routed]
        times = [e.value for e in response_times]

        return {
            "tasks_routed": len(routed),
            "avg_match_score": round(sum(scores) / len(scores), 2) if scores else None,
            "avg_response_minutes": round(sum(times) / len(times), 1)
            if times
            else None,
            "to_available_count": self._counters.get("routing.to_available", 0),
        }

    def _completion_summary(self, cutoff: float) -> dict:
        events = [
            e for e in self._events.get("completion", []) if e.timestamp >= cutoff
        ]
        completed = [e for e in events if e.name == "task_completed"]
        expired = [e for e in events if e.name == "task_expired"]
        times = [e for e in events if e.name == "time_to_complete"]

        qualities = [e.value for e in completed]
        durations = [e.value for e in times]
        total = len(completed) + len(expired)

        return {
            "completed": len(completed),
            "expired": len(expired),
            "completion_rate": round(len(completed) / total, 3) if total > 0 else None,
            "avg_quality": round(sum(qualities) / len(qualities), 3)
            if qualities
            else None,
            "avg_hours_to_complete": round(sum(durations) / len(durations), 2)
            if durations
            else None,
            "on_time_count": self._counters.get("completion.on_time", 0),
        }

    def _pipeline_summary(self, cutoff: float) -> dict:
        pipelines = {}
        for key, count in self._counters.items():
            if key.startswith("pipeline.") and key.endswith(".total"):
                name = key.replace("pipeline.", "").replace(".total", "")
                success = self._counters.get(f"pipeline.{name}.success", 0)
                error = self._counters.get(f"pipeline.{name}.error", 0)
                pipelines[name] = {
                    "total": count,
                    "success": success,
                    "error": error,
                    "success_rate": round(success / count, 3) if count > 0 else None,
                }
        return pipelines

    def _workforce_summary(self) -> dict:
        return {
            "joins": self._counters.get("workforce.joined", 0),
            "active": self._counters.get("workforce.active", 0),
            "left": self._counters.get("workforce.left", 0),
        }

    def _health_summary(self) -> dict:
        sources = {}
        for key, value in self._gauges.items():
            if key.startswith("source.") and key.endswith(".quality"):
                source = key.replace("source.", "").replace(".quality", "")
                status = self._gauges.get(f"source.{source}.status", "unknown")
                sources[source] = {"quality": value, "status": status}
        return {
            "sources_tracked": len(sources),
            "sources": sources,
        }
