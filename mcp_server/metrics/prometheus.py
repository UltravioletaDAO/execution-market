"""
Prometheus metrics module (Task 6.1 — SaaS production hardening).

Exposes RED metrics (Rate, Errors, Duration) for every HTTP request plus a
small set of business counters used by dashboards to answer "is the market
still functioning?" without paying for CloudWatch custom metrics.

Design goals:

  - **Graceful degradation.** If ``prometheus_client`` isn't installed (a
    valid state in minimal dev images), the whole module turns into
    no-ops and the application still starts. Same policy we use for
    Sentry.
  - **Stable label cardinality.** Labels are the classic cardinality
    hazard for Prometheus: keys like ``task_id`` or ``wallet_address``
    would explode the series count. We stick to low-cardinality labels
    (method, status_class, network, status) and whitelist the route
    templates we care about so untracked paths don't create new series.
  - **Route template normalisation.** FastAPI/Starlette exposes the
    matched route via ``request.scope['route'].path``. We prefer that
    template so ``/api/v1/tasks/{task_id}`` collapses instead of one
    series per UUID. Fallback to the literal path when no route matched
    (e.g. 404s) — clients still bucket those via status=404.
  - **Admin-protected exposure.** ``generate_metrics()`` renders the
    registry on demand; the HTTP endpoint wiring is owned by the caller
    (typically ``main.py``) so policy decisions (admin key, IP allow
    list, etc.) stay out of this module.

Reference: https://prometheus.io/docs/practices/instrumentation/
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency guard — module stays importable without prometheus_client
# ---------------------------------------------------------------------------

try:
    from prometheus_client import (  # type: ignore
        CONTENT_TYPE_LATEST,
        CollectorRegistry,
        Counter,
        Histogram,
        generate_latest,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover — covered indirectly by no-op tests
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"  # noqa: N816
    CollectorRegistry = None  # type: ignore
    Counter = None  # type: ignore
    Histogram = None  # type: ignore

    def generate_latest(*_args, **_kwargs):  # type: ignore[misc]
        return b""


# ---------------------------------------------------------------------------
# Registry + metric definitions
# ---------------------------------------------------------------------------

_REGISTRY = CollectorRegistry() if PROMETHEUS_AVAILABLE else None

# RED metrics — HTTP
_HTTP_REQUESTS_TOTAL = None
_HTTP_REQUEST_DURATION_SECONDS = None

# Business counters
_TASKS_CREATED_TOTAL = None
_TASKS_COMPLETED_TOTAL = None
_PAYMENTS_SETTLED_USD_TOTAL = None

if PROMETHEUS_AVAILABLE:
    _HTTP_REQUESTS_TOTAL = Counter(
        "em_http_requests_total",
        "Total HTTP requests handled by the MCP server.",
        labelnames=("method", "route", "status_class"),
        registry=_REGISTRY,
    )
    _HTTP_REQUEST_DURATION_SECONDS = Histogram(
        "em_http_request_duration_seconds",
        "HTTP request latency by route (seconds).",
        labelnames=("method", "route"),
        # Buckets tuned for a web API: fast reads < 100ms, slow writes < 10s.
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        registry=_REGISTRY,
    )

    _TASKS_CREATED_TOTAL = Counter(
        "em_tasks_created_total",
        "Tasks created via the REST API, labelled by payment network.",
        labelnames=("network",),
        registry=_REGISTRY,
    )
    _TASKS_COMPLETED_TOTAL = Counter(
        "em_tasks_completed_total",
        "Tasks reaching terminal status. Label: completed | expired | cancelled.",
        labelnames=("outcome",),
        registry=_REGISTRY,
    )
    _PAYMENTS_SETTLED_USD_TOTAL = Counter(
        "em_payments_settled_usd_total",
        "Cumulative USD settled to workers (excluding platform fee).",
        labelnames=("network",),
        registry=_REGISTRY,
    )


# ---------------------------------------------------------------------------
# Low-cardinality label helpers
# ---------------------------------------------------------------------------

_STATUS_CLASS_MAP = {
    1: "1xx",
    2: "2xx",
    3: "3xx",
    4: "4xx",
    5: "5xx",
}


def _status_class(status_code: int) -> str:
    return _STATUS_CLASS_MAP.get(status_code // 100, "other")


def _route_template(request) -> str:
    """Prefer the matched route template over the literal path.

    When no route matched (typical 404), fall back to the literal path
    but truncate query strings — we never want query values to leak into
    label values.
    """
    scope = getattr(request, "scope", {}) or {}
    route = scope.get("route")
    template = getattr(route, "path", None)
    if template:
        return template
    raw_path = getattr(getattr(request, "url", None), "path", None) or "unknown"
    return raw_path


# ---------------------------------------------------------------------------
# Public API — recorders (all safe to call even when the dep is absent)
# ---------------------------------------------------------------------------


def record_http_request(
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Record a single completed HTTP request. Safe to call on cold start."""
    if not PROMETHEUS_AVAILABLE:
        return
    try:
        _HTTP_REQUESTS_TOTAL.labels(
            method=method,
            route=route,
            status_class=_status_class(status_code),
        ).inc()
        _HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=route).observe(
            max(duration_seconds, 0.0)
        )
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug("prometheus record_http_request failed: %s", exc)


def record_task_created(network: Optional[str]) -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    try:
        _TASKS_CREATED_TOTAL.labels(network=(network or "unknown")).inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("prometheus record_task_created failed: %s", exc)


def record_task_completed(outcome: str) -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    try:
        _TASKS_COMPLETED_TOTAL.labels(outcome=outcome or "unknown").inc()
    except Exception as exc:  # pragma: no cover
        logger.debug("prometheus record_task_completed failed: %s", exc)


def record_payment_settled(network: Optional[str], amount_usd: float) -> None:
    if not PROMETHEUS_AVAILABLE:
        return
    if amount_usd <= 0:
        return
    try:
        _PAYMENTS_SETTLED_USD_TOTAL.labels(network=(network or "unknown")).inc(
            amount_usd
        )
    except Exception as exc:  # pragma: no cover
        logger.debug("prometheus record_payment_settled failed: %s", exc)


def generate_metrics() -> Tuple[bytes, str]:
    """Render the registry for /metrics. Returns (body, content_type)."""
    if not PROMETHEUS_AVAILABLE:
        return (b"# prometheus_client not installed\n", CONTENT_TYPE_LATEST)
    return (generate_latest(_REGISTRY), CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Starlette middleware
# ---------------------------------------------------------------------------


try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.types import ASGIApp

    _MIDDLEWARE_BASE_AVAILABLE = True
except ImportError:  # pragma: no cover
    BaseHTTPMiddleware = object  # type: ignore[misc]
    ASGIApp = object  # type: ignore[misc]
    _MIDDLEWARE_BASE_AVAILABLE = False


class PrometheusMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """Record RED metrics on every request.

    We skip instrumenting the ``/metrics`` endpoint itself so a busy
    scraper doesn't pollute its own histograms.
    """

    # Paths excluded from the metrics — the /metrics endpoint is the classic
    # self-observation trap, and health/livez don't represent real traffic.
    EXCLUDED_PREFIXES: tuple[str, ...] = (
        "/metrics",
        "/healthz",
        "/livez",
    )

    def __init__(self, app: "ASGIApp") -> None:
        if _MIDDLEWARE_BASE_AVAILABLE:
            super().__init__(app)
        self.app = app

    async def dispatch(self, request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.EXCLUDED_PREFIXES):
            return await call_next(request)

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            # Re-raise so FastAPI's exception handlers still run; the
            # finally block ensures we still record a 500.
            raise
        finally:
            elapsed = time.perf_counter() - start
            record_http_request(
                method=request.method,
                route=_route_template(request),
                status_code=status_code,
                duration_seconds=elapsed,
            )
