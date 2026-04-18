"""Observability primitives (tracing, correlated logs).

Sibling module to ``mcp_server/metrics`` which owns Prometheus. Keeping
tracing here (instead of under ``metrics``) so the two concerns stay
separable — metrics are aggregated counters/histograms, traces are
per-request spans. They cost different things and have different
lifecycles.
"""

from .tracing import (
    TRACING_AVAILABLE,
    get_tracer,
    instrument_fastapi_app,
    setup_tracing,
)

__all__ = [
    "TRACING_AVAILABLE",
    "get_tracer",
    "instrument_fastapi_app",
    "setup_tracing",
]
