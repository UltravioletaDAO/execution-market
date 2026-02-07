"""
Metrics Collection for Execution Market Monitoring.

Production-ready metrics collection supporting Prometheus and CloudWatch.

Features:
- Counter, Gauge, Histogram, and Summary metric types
- Thread-safe operations with proper locking
- Label support for multi-dimensional metrics
- Prometheus text exposition format export
- FastAPI middleware for automatic request metrics
- Business metrics for tasks, submissions, payments, workers
"""

import time
import threading
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


# =============================================================================
# Metric Types
# =============================================================================


@dataclass
class MetricValue:
    """A single metric value with timestamp and labels."""

    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    labels: Dict[str, str] = field(default_factory=dict)


class MetricType(str, Enum):
    """Prometheus metric types."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class Counter:
    """
    Monotonically increasing counter metric.

    Use for: request counts, error counts, completed tasks, etc.
    """

    def __init__(self, name: str, description: str, labels: List[str] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self._type = MetricType.COUNTER
        self._values: Dict[Tuple, float] = defaultdict(float)
        self._lock = threading.Lock()
        self._created_at = datetime.now(timezone.utc)

    def inc(self, amount: float = 1, **label_values) -> None:
        """
        Increment counter by amount.

        Args:
            amount: Value to increment by (must be >= 0)
            **label_values: Label name-value pairs
        """
        if amount < 0:
            raise ValueError("Counter can only be incremented by non-negative values")

        key = self._make_key(label_values)
        with self._lock:
            self._values[key] += amount

    def get(self, **label_values) -> float:
        """Get current counter value for given labels."""
        key = self._make_key(label_values)
        return self._values.get(key, 0)

    def get_all(self) -> Dict[Tuple, float]:
        """Get all counter values."""
        with self._lock:
            return dict(self._values)

    def _make_key(self, label_values: Dict[str, str]) -> Tuple:
        """Create hashable key from label values."""
        return tuple(sorted(label_values.items()))

    def reset(self) -> None:
        """Reset counter (use with caution - breaks Prometheus semantics)."""
        with self._lock:
            self._values.clear()


class Gauge:
    """
    Point-in-time value metric that can go up or down.

    Use for: active workers, queue size, temperature, etc.
    """

    def __init__(self, name: str, description: str, labels: List[str] = None):
        self.name = name
        self.description = description
        self.labels = labels or []
        self._type = MetricType.GAUGE
        self._values: Dict[Tuple, float] = {}
        self._lock = threading.Lock()

    def set(self, value: float, **label_values) -> None:
        """Set gauge to specific value."""
        key = self._make_key(label_values)
        with self._lock:
            self._values[key] = value

    def inc(self, amount: float = 1, **label_values) -> None:
        """Increment gauge by amount."""
        key = self._make_key(label_values)
        with self._lock:
            self._values[key] = self._values.get(key, 0) + amount

    def dec(self, amount: float = 1, **label_values) -> None:
        """Decrement gauge by amount."""
        key = self._make_key(label_values)
        with self._lock:
            self._values[key] = self._values.get(key, 0) - amount

    def get(self, **label_values) -> float:
        """Get current gauge value."""
        key = self._make_key(label_values)
        return self._values.get(key, 0)

    def get_all(self) -> Dict[Tuple, float]:
        """Get all gauge values."""
        with self._lock:
            return dict(self._values)

    def _make_key(self, label_values: Dict[str, str]) -> Tuple:
        return tuple(sorted(label_values.items()))

    def set_to_current_time(self, **label_values) -> None:
        """Set gauge to current Unix timestamp."""
        self.set(time.time(), **label_values)


class Histogram:
    """
    Distribution metric with configurable buckets.

    Use for: request latencies, response sizes, task durations.
    """

    # Default latency buckets in seconds
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)

    # Task duration buckets in seconds (1min to 8hrs)
    TASK_BUCKETS = (60, 300, 600, 1800, 3600, 7200, 14400, 28800)

    # Payment amount buckets in USD
    PAYMENT_BUCKETS = (1, 5, 10, 25, 50, 100, 250, 500, 1000)

    def __init__(
        self,
        name: str,
        description: str,
        buckets: Tuple[float, ...] = None,
        labels: List[str] = None,
    ):
        self.name = name
        self.description = description
        self.buckets = tuple(sorted(buckets or self.DEFAULT_BUCKETS))
        self.labels = labels or []
        self._type = MetricType.HISTOGRAM

        # Per-label-set: bucket counts, sum, and total count
        self._bucket_counts: Dict[Tuple, Dict[float, int]] = defaultdict(
            lambda: {b: 0 for b in self.buckets}
        )
        self._sums: Dict[Tuple, float] = defaultdict(float)
        self._counts: Dict[Tuple, int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, **label_values) -> None:
        """
        Record an observed value.

        Args:
            value: Observed value to record
            **label_values: Label name-value pairs
        """
        key = self._make_key(label_values)

        with self._lock:
            self._sums[key] += value
            self._counts[key] += 1

            # Increment all buckets >= value
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[key][bucket] += 1

    def get_count(self, **label_values) -> int:
        """Get total observation count."""
        key = self._make_key(label_values)
        return self._counts.get(key, 0)

    def get_sum(self, **label_values) -> float:
        """Get sum of all observations."""
        key = self._make_key(label_values)
        return self._sums.get(key, 0)

    def get_bucket(self, bucket: float, **label_values) -> int:
        """Get count for specific bucket (cumulative)."""
        key = self._make_key(label_values)
        if key not in self._bucket_counts:
            return 0
        return self._bucket_counts[key].get(bucket, 0)

    def get_percentile(self, percentile: float, **label_values) -> Optional[float]:
        """
        Get approximate percentile value.

        Args:
            percentile: Percentile to compute (0-1, e.g., 0.95 for 95th)
            **label_values: Label name-value pairs

        Returns:
            Approximate percentile value (upper bucket bound)
        """
        key = self._make_key(label_values)
        total = self._counts.get(key, 0)

        if total == 0:
            return None

        target = total * percentile
        cumulative = 0

        for bucket in self.buckets:
            count = self._bucket_counts[key].get(bucket, 0)
            cumulative = count  # Counts are cumulative
            if cumulative >= target:
                return bucket

        return self.buckets[-1] if self.buckets else None

    def _make_key(self, label_values: Dict[str, str]) -> Tuple:
        return tuple(sorted(label_values.items()))

    def time(self, **label_values):
        """
        Context manager/decorator for timing operations.

        Usage:
            with histogram.time(method="GET"):
                do_work()

            @histogram.time(operation="process")
            def process():
                ...
        """
        return _Timer(self, label_values)


class _Timer:
    """Context manager and decorator for histogram timing."""

    def __init__(self, histogram: Histogram, label_values: Dict[str, str]):
        self._histogram = histogram
        self._label_values = label_values
        self._start: Optional[float] = None

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self._start
        self._histogram.observe(duration, **self._label_values)
        return False

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper


class Summary:
    """
    Summary metric with quantile calculation.

    More expensive than histogram but provides accurate quantiles.
    Use sparingly for critical latency metrics.
    """

    DEFAULT_QUANTILES = (0.5, 0.9, 0.95, 0.99)
    MAX_AGE_SECONDS = 600  # 10 minutes

    def __init__(
        self,
        name: str,
        description: str,
        quantiles: Tuple[float, ...] = None,
        max_age: int = None,
        labels: List[str] = None,
    ):
        self.name = name
        self.description = description
        self.quantiles = quantiles or self.DEFAULT_QUANTILES
        self.max_age = max_age or self.MAX_AGE_SECONDS
        self.labels = labels or []
        self._type = MetricType.SUMMARY

        self._observations: Dict[Tuple, List[Tuple[float, float]]] = defaultdict(list)
        self._sums: Dict[Tuple, float] = defaultdict(float)
        self._counts: Dict[Tuple, int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, **label_values) -> None:
        """Record an observed value."""
        key = self._make_key(label_values)
        now = time.time()

        with self._lock:
            self._observations[key].append((now, value))
            self._sums[key] += value
            self._counts[key] += 1

            # Cleanup old observations
            self._cleanup(key, now)

    def get_quantile(self, quantile: float, **label_values) -> Optional[float]:
        """Get quantile value from recent observations."""
        key = self._make_key(label_values)

        with self._lock:
            self._cleanup(key, time.time())
            observations = self._observations.get(key, [])

            if not observations:
                return None

            values = sorted(obs[1] for obs in observations)
            idx = int(len(values) * quantile)
            idx = min(idx, len(values) - 1)
            return values[idx]

    def _cleanup(self, key: Tuple, now: float) -> None:
        """Remove observations older than max_age."""
        cutoff = now - self.max_age
        self._observations[key] = [
            obs for obs in self._observations[key] if obs[0] > cutoff
        ]

    def _make_key(self, label_values: Dict[str, str]) -> Tuple:
        return tuple(sorted(label_values.items()))


# =============================================================================
# Metrics Registry
# =============================================================================


class MetricsRegistry:
    """
    Central registry for all Execution Market metrics.

    Metrics categories:
    - Task lifecycle (created, completed, failed, duration)
    - Submissions (received, approved, rejected)
    - Payments (processed, volume, failures)
    - Workers (active, availability, reputation)
    - API (requests, latency, errors)
    - System (health, resources)
    """

    def __init__(self):
        self._start_time = datetime.now(timezone.utc)

        # =====================================================================
        # Task Metrics
        # =====================================================================
        self.tasks_created = Counter(
            "em_tasks_created_total",
            "Total number of tasks created",
            labels=["category", "agent_tier"],
        )

        self.tasks_completed = Counter(
            "em_tasks_completed_total",
            "Total number of tasks completed successfully",
            labels=["category"],
        )

        self.tasks_failed = Counter(
            "em_tasks_failed_total",
            "Total number of tasks that failed or were cancelled",
            labels=["category", "reason"],
        )

        self.task_duration = Histogram(
            "em_task_duration_seconds",
            "Task completion duration in seconds",
            buckets=Histogram.TASK_BUCKETS,
            labels=["category"],
        )

        self.active_tasks = Gauge(
            "em_active_tasks", "Number of currently active tasks", labels=["status"]
        )

        self.task_bounty = Histogram(
            "em_task_bounty_usd",
            "Task bounty amounts in USD",
            buckets=Histogram.PAYMENT_BUCKETS,
            labels=["category"],
        )

        # =====================================================================
        # Submission Metrics
        # =====================================================================
        self.submissions_received = Counter(
            "em_submissions_received_total",
            "Total submissions received",
            labels=["category"],
        )

        self.submissions_approved = Counter(
            "em_submissions_approved_total",
            "Total submissions approved",
            labels=["category"],
        )

        self.submissions_rejected = Counter(
            "em_submissions_rejected_total",
            "Total submissions rejected",
            labels=["category", "reason"],
        )

        self.submission_review_time = Histogram(
            "em_submission_review_seconds",
            "Time to review submissions",
            labels=["category", "verdict"],
        )

        # =====================================================================
        # Payment Metrics
        # =====================================================================
        self.payments_processed = Counter(
            "em_payments_processed_total",
            "Total payments processed",
            labels=["token", "status"],
        )

        self.payment_volume = Counter(
            "em_payment_volume_usd_total",
            "Total payment volume in USD",
            labels=["token"],
        )

        self.payment_failures = Counter(
            "em_payment_failures_total",
            "Total payment failures",
            labels=["token", "error_type"],
        )

        self.payment_latency = Histogram(
            "em_payment_processing_seconds", "Payment processing time", labels=["token"]
        )

        self.escrow_balance = Gauge(
            "em_escrow_balance_usd", "Current escrow balance in USD", labels=["token"]
        )

        # =====================================================================
        # Worker Metrics
        # =====================================================================
        self.active_workers = Gauge(
            "em_active_workers", "Number of active workers", labels=["tier", "category"]
        )

        self.worker_registrations = Counter(
            "em_worker_registrations_total", "Total worker registrations"
        )

        self.worker_reputation_distribution = Histogram(
            "em_worker_reputation_score",
            "Distribution of worker reputation scores",
            buckets=(10, 25, 50, 75, 100, 150, 200, 300, 500),
        )

        self.worker_availability = Gauge(
            "em_worker_availability_ratio",
            "Ratio of available workers to total workers",
            labels=["category"],
        )

        self.worker_task_acceptance_rate = Gauge(
            "em_worker_task_acceptance_rate",
            "Rolling task acceptance rate per worker tier",
            labels=["tier"],
        )

        # =====================================================================
        # API Metrics
        # =====================================================================
        self.api_requests = Counter(
            "em_api_requests_total",
            "Total API requests",
            labels=["method", "path", "status"],
        )

        self.api_latency = Histogram(
            "em_api_latency_seconds", "API request latency", labels=["method", "path"]
        )

        self.api_errors = Counter(
            "em_api_errors_total",
            "Total API errors",
            labels=["method", "path", "error_type"],
        )

        self.api_rate_limited = Counter(
            "em_api_rate_limited_total",
            "Total requests that were rate limited",
            labels=["tier"],
        )

        self.websocket_connections = Gauge(
            "em_websocket_connections", "Current WebSocket connections", labels=["type"]
        )

        # =====================================================================
        # Verification Metrics
        # =====================================================================
        self.verifications_performed = Counter(
            "em_verifications_total",
            "Total verifications performed",
            labels=["type", "result"],
        )

        self.verification_latency = Histogram(
            "em_verification_latency_seconds",
            "Verification processing time",
            labels=["type"],
        )

        self.ai_review_calls = Counter(
            "em_ai_review_calls_total",
            "Total AI review API calls",
            labels=["model", "status"],
        )

        self.ai_review_tokens = Counter(
            "em_ai_review_tokens_total",
            "Total tokens used for AI review",
            labels=["model", "direction"],  # direction: input/output
        )

        # =====================================================================
        # Dispute Metrics
        # =====================================================================
        self.disputes_opened = Counter(
            "em_disputes_opened_total", "Total disputes opened", labels=["category"]
        )

        self.disputes_resolved = Counter(
            "em_disputes_resolved_total",
            "Total disputes resolved",
            labels=["category", "resolution"],
        )

        self.dispute_resolution_time = Histogram(
            "em_dispute_resolution_seconds",
            "Time to resolve disputes",
            buckets=(3600, 7200, 14400, 28800, 86400, 172800, 604800),  # 1hr to 1 week
        )

        # =====================================================================
        # System Metrics
        # =====================================================================
        self.health_check_duration = Histogram(
            "em_health_check_duration_seconds",
            "Health check duration",
            labels=["component"],
        )

        self.background_job_duration = Histogram(
            "em_background_job_duration_seconds",
            "Background job execution time",
            labels=["job_type"],
        )

        self.background_job_failures = Counter(
            "em_background_job_failures_total",
            "Background job failures",
            labels=["job_type", "error_type"],
        )

        self.cache_hits = Counter(
            "em_cache_hits_total", "Cache hit count", labels=["cache"]
        )

        self.cache_misses = Counter(
            "em_cache_misses_total", "Cache miss count", labels=["cache"]
        )

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def record_task_created(
        self, category: str, bounty_usd: float, agent_tier: str = "free"
    ) -> None:
        """Record task creation with associated metrics."""
        self.tasks_created.inc(category=category, agent_tier=agent_tier)
        self.active_tasks.inc(status="published")
        self.task_bounty.observe(bounty_usd, category=category)

    def record_task_completed(
        self, category: str, duration_seconds: float, bounty_usd: float
    ) -> None:
        """Record successful task completion."""
        self.tasks_completed.inc(category=category)
        self.task_duration.observe(duration_seconds, category=category)
        self.active_tasks.dec(status="in_progress")
        self.payment_volume.inc(bounty_usd, token="USDC")

    def record_task_failed(self, category: str, reason: str) -> None:
        """Record task failure."""
        self.tasks_failed.inc(category=category, reason=reason)
        self.active_tasks.dec(status="in_progress")

    def record_submission(
        self, category: str, verdict: str, review_time_seconds: float
    ) -> None:
        """Record submission with verdict."""
        self.submissions_received.inc(category=category)
        self.submission_review_time.observe(
            review_time_seconds, category=category, verdict=verdict
        )

        if verdict == "approved":
            self.submissions_approved.inc(category=category)
        elif verdict == "rejected":
            self.submissions_rejected.inc(category=category, reason="quality")

    def record_payment(
        self,
        amount_usd: float,
        token: str = "USDC",
        duration_seconds: float = 0,
        success: bool = True,
        error_type: str = None,
    ) -> None:
        """Record payment processing."""
        status = "success" if success else "failed"
        self.payments_processed.inc(token=token, status=status)

        if success:
            self.payment_volume.inc(amount_usd, token=token)
            if duration_seconds > 0:
                self.payment_latency.observe(duration_seconds, token=token)
        else:
            self.payment_failures.inc(token=token, error_type=error_type or "unknown")

    def record_api_request(
        self, method: str, path: str, status_code: int, duration_seconds: float
    ) -> None:
        """Record API request metrics."""
        # Normalize path (remove IDs)
        normalized_path = self._normalize_path(path)

        self.api_requests.inc(
            method=method, path=normalized_path, status=str(status_code)
        )
        self.api_latency.observe(duration_seconds, method=method, path=normalized_path)

        if status_code >= 400:
            error_type = "client_error" if status_code < 500 else "server_error"
            self.api_errors.inc(
                method=method, path=normalized_path, error_type=error_type
            )

    def record_verification(
        self, verification_type: str, result: str, duration_seconds: float
    ) -> None:
        """Record verification metrics."""
        self.verifications_performed.inc(type=verification_type, result=result)
        self.verification_latency.observe(duration_seconds, type=verification_type)

    def record_ai_review(
        self, model: str, input_tokens: int, output_tokens: int, success: bool = True
    ) -> None:
        """Record AI review API usage."""
        status = "success" if success else "failed"
        self.ai_review_calls.inc(model=model, status=status)
        self.ai_review_tokens.inc(input_tokens, model=model, direction="input")
        self.ai_review_tokens.inc(output_tokens, model=model, direction="output")

    def _normalize_path(self, path: str) -> str:
        """Normalize API path by replacing UUIDs and IDs with placeholders."""
        import re

        # Replace UUIDs
        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
            flags=re.IGNORECASE,
        )
        # Replace numeric IDs
        path = re.sub(r"/\d+(?=/|$)", "/{id}", path)
        return path

    # =========================================================================
    # Export Methods
    # =========================================================================

    def to_prometheus(self) -> str:
        """Export all metrics in Prometheus text exposition format."""
        lines = []

        # Collect all metrics
        all_metrics = [
            # Tasks
            self.tasks_created,
            self.tasks_completed,
            self.tasks_failed,
            self.task_duration,
            self.active_tasks,
            self.task_bounty,
            # Submissions
            self.submissions_received,
            self.submissions_approved,
            self.submissions_rejected,
            self.submission_review_time,
            # Payments
            self.payments_processed,
            self.payment_volume,
            self.payment_failures,
            self.payment_latency,
            self.escrow_balance,
            # Workers
            self.active_workers,
            self.worker_registrations,
            self.worker_reputation_distribution,
            self.worker_availability,
            # API
            self.api_requests,
            self.api_latency,
            self.api_errors,
            self.api_rate_limited,
            self.websocket_connections,
            # Verification
            self.verifications_performed,
            self.verification_latency,
            self.ai_review_calls,
            self.ai_review_tokens,
            # Disputes
            self.disputes_opened,
            self.disputes_resolved,
            self.dispute_resolution_time,
            # System
            self.health_check_duration,
            self.background_job_duration,
            self.background_job_failures,
            self.cache_hits,
            self.cache_misses,
        ]

        for metric in all_metrics:
            lines.extend(self._format_metric(metric))
            lines.append("")

        return "\n".join(lines)

    def _format_metric(self, metric) -> List[str]:
        """Format a single metric for Prometheus."""
        lines = [
            f"# HELP {metric.name} {metric.description}",
            f"# TYPE {metric.name} {metric._type.value}",
        ]

        if isinstance(metric, Counter):
            for labels, value in metric.get_all().items():
                label_str = self._format_labels(labels)
                lines.append(f"{metric.name}{label_str} {value}")

        elif isinstance(metric, Gauge):
            for labels, value in metric.get_all().items():
                label_str = self._format_labels(labels)
                lines.append(f"{metric.name}{label_str} {value}")

        elif isinstance(metric, Histogram):
            # Export bucket counts, sum, and count
            for labels in metric._bucket_counts.keys():
                label_str = self._format_labels(labels)

                # Buckets (cumulative)
                for bucket in metric.buckets:
                    count = metric._bucket_counts[labels][bucket]
                    bucket_label = (
                        f'{label_str[:-1]},le="{bucket}"}}'
                        if label_str
                        else f'{{le="{bucket}"}}'
                    )
                    if label_str and label_str != "{}":
                        bucket_label = f'{label_str[:-1]},le="{bucket}"}}'
                    else:
                        bucket_label = f'{{le="{bucket}"}}'
                    lines.append(f"{metric.name}_bucket{bucket_label} {count}")

                # +Inf bucket
                inf_label = (
                    f'{label_str[:-1]},le="+Inf"}}'
                    if label_str and label_str != "{}"
                    else '{le="+Inf"}'
                )
                lines.append(
                    f"{metric.name}_bucket{inf_label} {metric._counts[labels]}"
                )

                # Sum and count
                lines.append(f"{metric.name}_sum{label_str} {metric._sums[labels]}")
                lines.append(f"{metric.name}_count{label_str} {metric._counts[labels]}")

        return lines

    def _format_labels(self, labels: Tuple) -> str:
        """Format labels tuple to Prometheus label string."""
        if not labels:
            return ""
        label_dict = dict(labels)
        parts = [f'{k}="{v}"' for k, v in label_dict.items()]
        return "{" + ",".join(parts) + "}"

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of current metrics for dashboards."""
        return {
            "tasks": {
                "created_total": sum(self.tasks_created.get_all().values()),
                "completed_total": sum(self.tasks_completed.get_all().values()),
                "failed_total": sum(self.tasks_failed.get_all().values()),
                "active": sum(self.active_tasks.get_all().values()),
            },
            "submissions": {
                "received_total": sum(self.submissions_received.get_all().values()),
                "approved_total": sum(self.submissions_approved.get_all().values()),
                "rejected_total": sum(self.submissions_rejected.get_all().values()),
            },
            "payments": {
                "processed_total": sum(self.payments_processed.get_all().values()),
                "volume_usd": sum(self.payment_volume.get_all().values()),
                "failures_total": sum(self.payment_failures.get_all().values()),
            },
            "workers": {
                "active": sum(self.active_workers.get_all().values()),
                "registrations_total": self.worker_registrations.get(),
            },
            "api": {
                "requests_total": sum(self.api_requests.get_all().values()),
                "errors_total": sum(self.api_errors.get_all().values()),
            },
            "uptime_seconds": (
                datetime.now(timezone.utc) - self._start_time
            ).total_seconds(),
        }


# =============================================================================
# Global Instance
# =============================================================================

_registry: Optional[MetricsRegistry] = None


def get_metrics() -> MetricsRegistry:
    """Get singleton metrics registry."""
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


# =============================================================================
# FastAPI Middleware
# =============================================================================

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware to automatically record API request metrics.

    Records:
    - Request count by method/path/status
    - Request latency histogram
    - Error counts
    """

    # Paths to exclude from metrics (health checks, etc.)
    EXCLUDE_PATHS = {"/health", "/health/live", "/health/ready", "/metrics"}

    async def dispatch(self, request: Request, call_next):
        # Skip excluded paths
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)

        start = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start

            get_metrics().record_api_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=duration,
            )

            return response

        except Exception:
            duration = time.time() - start

            get_metrics().record_api_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_seconds=duration,
            )

            raise


# =============================================================================
# Prometheus Endpoint
# =============================================================================

from fastapi import APIRouter, Response

metrics_router = APIRouter(tags=["metrics"])


@metrics_router.get("/metrics")
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns all metrics in Prometheus text exposition format.
    """
    registry = get_metrics()
    content = registry.to_prometheus()

    return Response(
        content=content, media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@metrics_router.get("/metrics/summary")
async def metrics_summary() -> Dict[str, Any]:
    """
    Get human-readable metrics summary.

    Useful for dashboards and quick status checks.
    """
    registry = get_metrics()
    return registry.get_summary()
