"""
Prometheus Metrics for Chamba

Provides metrics collection and exposition for monitoring:
- Request count by endpoint and status
- Response time histograms
- Active tasks gauge
- Escrow balance gauge
- Worker and agent activity metrics

Compatible with:
- Prometheus
- Grafana
- DataDog
- New Relic
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)


# =============================================================================
# Metric Types
# =============================================================================


@dataclass
class Counter:
    """A monotonically increasing counter metric."""
    name: str
    description: str
    labels: Tuple[str, ...] = ()
    _values: Dict[Tuple[str, ...], float] = field(default_factory=lambda: defaultdict(float))

    def inc(self, labels: Dict[str, str] = None, value: float = 1.0) -> None:
        """Increment counter by value."""
        label_key = tuple((labels or {}).get(l, "") for l in self.labels)
        self._values[label_key] += value

    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current counter value."""
        label_key = tuple((labels or {}).get(l, "") for l in self.labels)
        return self._values.get(label_key, 0.0)

    def reset(self) -> None:
        """Reset all counter values (for testing)."""
        self._values.clear()

    def to_prometheus(self) -> str:
        """Export in Prometheus text format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        if not self._values:
            lines.append(f"{self.name} 0")
        else:
            for label_values, value in sorted(self._values.items()):
                if self.labels and any(label_values):
                    label_str = ",".join(
                        f'{l}="{v}"' for l, v in zip(self.labels, label_values) if v
                    )
                    lines.append(f"{self.name}{{{label_str}}} {value}")
                else:
                    lines.append(f"{self.name} {value}")
        return "\n".join(lines)


@dataclass
class Gauge:
    """A metric that can go up or down."""
    name: str
    description: str
    labels: Tuple[str, ...] = ()
    _values: Dict[Tuple[str, ...], float] = field(default_factory=lambda: defaultdict(float))

    def set(self, value: float, labels: Dict[str, str] = None) -> None:
        """Set gauge to a specific value."""
        label_key = tuple((labels or {}).get(l, "") for l in self.labels)
        self._values[label_key] = value

    def inc(self, labels: Dict[str, str] = None, value: float = 1.0) -> None:
        """Increment gauge by value."""
        label_key = tuple((labels or {}).get(l, "") for l in self.labels)
        self._values[label_key] += value

    def dec(self, labels: Dict[str, str] = None, value: float = 1.0) -> None:
        """Decrement gauge by value."""
        label_key = tuple((labels or {}).get(l, "") for l in self.labels)
        self._values[label_key] -= value

    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current gauge value."""
        label_key = tuple((labels or {}).get(l, "") for l in self.labels)
        return self._values.get(label_key, 0.0)

    def reset(self) -> None:
        """Reset all gauge values."""
        self._values.clear()

    def to_prometheus(self) -> str:
        """Export in Prometheus text format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        if not self._values:
            lines.append(f"{self.name} 0")
        else:
            for label_values, value in sorted(self._values.items()):
                if self.labels and any(label_values):
                    label_str = ",".join(
                        f'{l}="{v}"' for l, v in zip(self.labels, label_values) if v
                    )
                    lines.append(f"{self.name}{{{label_str}}} {value}")
                else:
                    lines.append(f"{self.name} {value}")
        return "\n".join(lines)


@dataclass
class Histogram:
    """
    A histogram metric for measuring distributions.

    Uses pre-defined buckets for latency measurements.
    """
    name: str
    description: str
    labels: Tuple[str, ...] = ()
    buckets: Tuple[float, ...] = (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
    _counts: Dict[Tuple[str, ...], List[int]] = field(default_factory=dict)
    _sums: Dict[Tuple[str, ...], float] = field(default_factory=lambda: defaultdict(float))
    _totals: Dict[Tuple[str, ...], int] = field(default_factory=lambda: defaultdict(int))

    def observe(self, value: float, labels: Dict[str, str] = None) -> None:
        """Record an observation."""
        label_key = tuple((labels or {}).get(l, "") for l in self.labels)

        # Initialize bucket counts if needed
        if label_key not in self._counts:
            self._counts[label_key] = [0] * len(self.buckets)

        # Increment bucket counts
        for i, bucket in enumerate(self.buckets):
            if value <= bucket:
                self._counts[label_key][i] += 1

        self._sums[label_key] += value
        self._totals[label_key] += 1

    def get_count(self, labels: Dict[str, str] = None) -> int:
        """Get total observation count."""
        label_key = tuple((labels or {}).get(l, "") for l in self.labels)
        return self._totals.get(label_key, 0)

    def get_sum(self, labels: Dict[str, str] = None) -> float:
        """Get sum of all observations."""
        label_key = tuple((labels or {}).get(l, "") for l in self.labels)
        return self._sums.get(label_key, 0.0)

    def reset(self) -> None:
        """Reset all histogram values."""
        self._counts.clear()
        self._sums.clear()
        self._totals.clear()

    @contextmanager
    def time(self, labels: Dict[str, str] = None):
        """Context manager to time an operation."""
        start = time.time()
        try:
            yield
        finally:
            self.observe(time.time() - start, labels)

    def to_prometheus(self) -> str:
        """Export in Prometheus text format."""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]

        for label_values in sorted(self._counts.keys()):
            label_str = ""
            if self.labels and any(label_values):
                label_str = ",".join(
                    f'{l}="{v}"' for l, v in zip(self.labels, label_values) if v
                )

            # Cumulative bucket counts
            cumulative = 0
            for i, bucket in enumerate(self.buckets):
                cumulative += self._counts[label_values][i]
                le_label = f'le="{bucket}"'
                if label_str:
                    lines.append(f'{self.name}_bucket{{{label_str},{le_label}}} {cumulative}')
                else:
                    lines.append(f'{self.name}_bucket{{{le_label}}} {cumulative}')

            # +Inf bucket
            total = self._totals[label_values]
            if label_str:
                lines.append(f'{self.name}_bucket{{{label_str},le="+Inf"}} {total}')
                lines.append(f'{self.name}_sum{{{label_str}}} {self._sums[label_values]:.6f}')
                lines.append(f'{self.name}_count{{{label_str}}} {total}')
            else:
                lines.append(f'{self.name}_bucket{{le="+Inf"}} {total}')
                lines.append(f'{self.name}_sum {self._sums[label_values]:.6f}')
                lines.append(f'{self.name}_count {total}')

        if not self._counts:
            # No observations yet
            for bucket in self.buckets:
                lines.append(f'{self.name}_bucket{{le="{bucket}"}} 0')
            lines.append(f'{self.name}_bucket{{le="+Inf"}} 0')
            lines.append(f'{self.name}_sum 0')
            lines.append(f'{self.name}_count 0')

        return "\n".join(lines)


# =============================================================================
# Predefined Metrics
# =============================================================================


# Request metrics
REQUEST_COUNT = Counter(
    name="chamba_requests_total",
    description="Total number of requests by endpoint and status",
    labels=("endpoint", "method", "status"),
)

REQUEST_LATENCY = Histogram(
    name="chamba_request_duration_seconds",
    description="Request duration in seconds",
    labels=("endpoint", "method"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Task metrics
ACTIVE_TASKS = Gauge(
    name="chamba_active_tasks",
    description="Number of active tasks by status",
    labels=("status", "category"),
)

TASKS_CREATED = Counter(
    name="chamba_tasks_created_total",
    description="Total tasks created",
    labels=("category",),
)

TASKS_COMPLETED = Counter(
    name="chamba_tasks_completed_total",
    description="Total tasks completed",
    labels=("category",),
)

# Payment metrics
ESCROW_BALANCE = Gauge(
    name="chamba_escrow_balance_usd",
    description="Total USD value locked in escrow",
    labels=("token",),
)

PAYMENTS_RELEASED = Counter(
    name="chamba_payments_released_total",
    description="Total payments released",
    labels=("token",),
)

PAYMENTS_RELEASED_USD = Counter(
    name="chamba_payments_released_usd_total",
    description="Total USD value of released payments",
    labels=("token",),
)

# Worker metrics
ACTIVE_WORKERS = Gauge(
    name="chamba_active_workers",
    description="Number of active workers",
    labels=(),
)

SUBMISSIONS_TOTAL = Counter(
    name="chamba_submissions_total",
    description="Total submissions by verdict",
    labels=("verdict",),
)

# System metrics
HEALTH_CHECK_DURATION = Histogram(
    name="chamba_health_check_duration_seconds",
    description="Health check duration by component",
    labels=("component",),
)

COMPONENT_HEALTH = Gauge(
    name="chamba_component_health",
    description="Component health status (1=healthy, 0.5=degraded, 0=unhealthy)",
    labels=("component",),
)


# =============================================================================
# Metrics Collector
# =============================================================================


class MetricsCollector:
    """
    Central metrics collection and exposition.

    Features:
    - Automatic metric registration
    - Prometheus text format export
    - Async-safe operations
    - Background refresh for expensive metrics
    """

    def __init__(self):
        self._metrics: Dict[str, Any] = {
            "chamba_requests_total": REQUEST_COUNT,
            "chamba_request_duration_seconds": REQUEST_LATENCY,
            "chamba_active_tasks": ACTIVE_TASKS,
            "chamba_tasks_created_total": TASKS_CREATED,
            "chamba_tasks_completed_total": TASKS_COMPLETED,
            "chamba_escrow_balance_usd": ESCROW_BALANCE,
            "chamba_payments_released_total": PAYMENTS_RELEASED,
            "chamba_payments_released_usd_total": PAYMENTS_RELEASED_USD,
            "chamba_active_workers": ACTIVE_WORKERS,
            "chamba_submissions_total": SUBMISSIONS_TOTAL,
            "chamba_health_check_duration_seconds": HEALTH_CHECK_DURATION,
            "chamba_component_health": COMPONENT_HEALTH,
        }
        self._last_refresh: Optional[datetime] = None
        self._refresh_interval = 60  # seconds

    def register(self, metric: Any) -> None:
        """Register a custom metric."""
        self._metrics[metric.name] = metric

    def unregister(self, name: str) -> None:
        """Unregister a metric."""
        self._metrics.pop(name, None)

    def get(self, name: str) -> Optional[Any]:
        """Get a metric by name."""
        return self._metrics.get(name)

    async def refresh_expensive_metrics(self) -> None:
        """
        Refresh metrics that require database queries.

        Called periodically or on-demand before scraping.
        """
        try:
            # Refresh task counts by status
            await self._refresh_task_metrics()

            # Refresh escrow balance
            await self._refresh_escrow_metrics()

            # Refresh worker count
            await self._refresh_worker_metrics()

            self._last_refresh = datetime.now(timezone.utc)
            logger.debug("Metrics refresh complete")

        except Exception as e:
            logger.error("Failed to refresh metrics: %s", str(e))

    async def _refresh_task_metrics(self) -> None:
        """Refresh task-related metrics from database."""
        try:
            import supabase_client
            client = supabase_client.get_client()

            # Get task counts by status
            statuses = ["published", "accepted", "in_progress", "submitted", "completed", "cancelled"]
            categories = [
                "physical_presence", "knowledge_access", "human_authority",
                "social_verification", "sensitive_handling"
            ]

            for status in statuses:
                result = client.table("tasks").select("id, category", count="exact").eq("status", status).execute()
                count = result.count or 0

                # Group by category if we have data
                if result.data:
                    category_counts = defaultdict(int)
                    for task in result.data:
                        cat = task.get("category", "unknown")
                        category_counts[cat] += 1

                    for cat, cat_count in category_counts.items():
                        ACTIVE_TASKS.set(
                            cat_count,
                            labels={"status": status, "category": cat}
                        )
                else:
                    # Set zero for all categories in this status
                    for cat in categories:
                        ACTIVE_TASKS.set(0, labels={"status": status, "category": cat})

        except Exception as e:
            logger.warning("Failed to refresh task metrics: %s", str(e))

    async def _refresh_escrow_metrics(self) -> None:
        """Refresh escrow balance metrics."""
        try:
            # Try to get from escrow manager
            from integrations.x402.escrow import get_manager
            manager = get_manager()

            total_by_token: Dict[str, float] = defaultdict(float)
            for escrow in manager._escrows.values():
                if escrow.is_active:
                    total_by_token[escrow.token.value] += float(escrow.remaining_amount)

            for token, amount in total_by_token.items():
                ESCROW_BALANCE.set(amount, labels={"token": token})

            # Set zero for tokens with no balance
            for token in ["USDC", "EURC", "DAI", "USDT"]:
                if token not in total_by_token:
                    ESCROW_BALANCE.set(0, labels={"token": token})

        except Exception as e:
            logger.debug("Could not refresh escrow metrics: %s", str(e))

    async def _refresh_worker_metrics(self) -> None:
        """Refresh worker-related metrics."""
        try:
            import supabase_client
            client = supabase_client.get_client()

            # Count active workers (have completed tasks in last 30 days)
            result = client.table("executors").select("id", count="exact").execute()
            count = result.count or 0
            ACTIVE_WORKERS.set(count)

        except Exception as e:
            logger.warning("Failed to refresh worker metrics: %s", str(e))

    def export_prometheus(self) -> str:
        """
        Export all metrics in Prometheus text exposition format.

        Returns:
            String in Prometheus format
        """
        lines = []

        # Add timestamp comment
        lines.append(f"# Scraped at {datetime.now(timezone.utc).isoformat()}")
        lines.append("")

        # Export each metric
        for name, metric in sorted(self._metrics.items()):
            if hasattr(metric, "to_prometheus"):
                lines.append(metric.to_prometheus())
                lines.append("")

        # Add uptime metric
        if hasattr(self, "_start_time"):
            uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
            lines.extend([
                "# HELP chamba_uptime_seconds Service uptime in seconds",
                "# TYPE chamba_uptime_seconds counter",
                f"chamba_uptime_seconds {uptime:.2f}",
                ""
            ])

        return "\n".join(lines)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current metrics.

        Returns:
            Dictionary with metric summaries
        """
        return {
            "requests_total": REQUEST_COUNT._values,
            "active_tasks": dict(ACTIVE_TASKS._values),
            "escrow_balance": dict(ESCROW_BALANCE._values),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
        }


# =============================================================================
# Global Collector Instance
# =============================================================================


_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# =============================================================================
# Convenience Decorators
# =============================================================================


def track_request(endpoint: str, method: str = "GET"):
    """
    Decorator to track request metrics.

    Usage:
        @track_request("/api/v1/tasks", "POST")
        async def create_task():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            labels = {"endpoint": endpoint, "method": method}

            with REQUEST_LATENCY.time(labels):
                try:
                    result = await func(*args, **kwargs)
                    REQUEST_COUNT.inc(labels={**labels, "status": "success"})
                    return result
                except Exception as e:
                    REQUEST_COUNT.inc(labels={**labels, "status": "error"})
                    raise

        return wrapper
    return decorator


def track_task_operation(operation: str):
    """
    Decorator to track task operations.

    Usage:
        @track_task_operation("created")
        async def publish_task():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Try to extract category from result
            category = "unknown"
            if isinstance(result, dict):
                category = result.get("category", "unknown")

            if operation == "created":
                TASKS_CREATED.inc(labels={"category": category})
            elif operation == "completed":
                TASKS_COMPLETED.inc(labels={"category": category})

            return result

        return wrapper
    return decorator
