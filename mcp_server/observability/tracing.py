"""
OpenTelemetry tracing bootstrap (Task 6.2 — SaaS production hardening).

Wires application-layer distributed tracing so the full request chain
``agent -> EM API -> facilitator -> chain RPC`` is visible in one trace,
instead of five disconnected CloudWatch log streams.

Design goals
------------

- **Graceful degradation.** If ``opentelemetry-*`` isn't installed (minimal
  dev image) or ``OTEL_ENABLED`` is falsy, the whole module is a no-op and
  the app boots normally. Same policy as Sentry and Prometheus.
- **Early init.** The ``httpx`` and ``requests`` auto-instrumentation
  patches the library at import time — if we bootstrap after those libs
  are already loaded, the early httpx calls (e.g. Sentry's own transport,
  Supabase client construction) go untraced. ``setup_tracing()`` MUST run
  before those libraries are imported. ``main.py`` calls it right after
  the Sentry block.
- **FastAPI instrumentation deferred.** Unlike httpx/requests, the FastAPI
  instrumentor needs the app instance. Caller invokes
  ``instrument_fastapi_app(app)`` after ``FastAPI(...)`` is constructed.
- **Exporter = OTLP/HTTP.** Targets the AWS ADOT collector running as a
  sidecar on :4318 (default). The collector then routes to CloudWatch
  X-Ray / Grafana Tempo / wherever ops decides. Keeps this module
  vendor-neutral — no awscollector code here.
- **Log correlation.** ``LoggingInstrumentor`` injects ``trace_id`` and
  ``span_id`` into every ``LogRecord`` so the JSON log formatter picks
  them up automatically. Queries in CloudWatch Insights can then pivot
  from a slow trace to its matching log lines.

Environment variables
---------------------

- ``OTEL_ENABLED`` — ``true``/``1``/``yes`` to enable. Default ``false``.
- ``OTEL_SERVICE_NAME`` — Resource ``service.name``. Default
  ``execution-market-mcp``.
- ``OTEL_EXPORTER_OTLP_ENDPOINT`` — OTLP/HTTP collector URL. Default
  ``http://localhost:4318`` (ADOT sidecar). The instrumentor appends the
  ``/v1/traces`` path suffix automatically.
- ``OTEL_TRACES_SAMPLER_ARG`` — Head-sampling rate 0.0-1.0. Default
  ``0.1`` (10%) to keep collector cost bounded under bursty load.
- ``ENVIRONMENT`` — Used to populate ``deployment.environment`` resource
  attribute. Re-used from the existing Sentry/config convention.
- ``GIT_SHA`` — Resource ``service.version``. Re-used.

Reference: https://opentelemetry.io/docs/languages/python/
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Optional dependency guard — module stays importable without OTel installed
# ---------------------------------------------------------------------------
#
# We import the heavy symbols inside ``setup_tracing()`` rather than at module
# top so the import cost is paid only when tracing is actually enabled. The
# top-level ``try/except`` is used just to set ``TRACING_AVAILABLE`` — a
# lightweight probe the rest of the codebase can check.

try:
    import opentelemetry  # noqa: F401  — probe only

    TRACING_AVAILABLE = True
except ImportError:  # pragma: no cover — dev images may skip OTel
    TRACING_AVAILABLE = False


# Module-level flag so idempotent callers (tests, reload) can query state
# without re-invoking setup.
_TRACING_INITIALIZED = False


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in ("true", "1", "yes", "on")


def _otel_enabled() -> bool:
    return _truthy(os.environ.get("OTEL_ENABLED"))


def setup_tracing() -> bool:
    """Initialize the OTel tracer provider + library auto-instrumentation.

    Returns ``True`` when tracing is live, ``False`` on graceful skip.
    Safe to call multiple times — subsequent calls short-circuit.

    MUST be called before ``httpx``, ``requests``, or any third-party
    library we want to trace is imported at request time. In practice
    that means "right after the Sentry block in main.py".
    """
    global _TRACING_INITIALIZED

    if _TRACING_INITIALIZED:
        return True

    if not _otel_enabled():
        # Quietly disabled — log at debug so production boots don't get
        # an INFO line on every cold start.
        logger.debug("OpenTelemetry tracing disabled (OTEL_ENABLED not truthy)")
        return False

    if not TRACING_AVAILABLE:
        logger.warning(
            "OTEL_ENABLED is set but opentelemetry-* packages are missing — "
            "tracing will be skipped. Install the optional extras or unset "
            "the env var to silence this warning."
        )
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
    except ImportError as exc:  # pragma: no cover — probe above should catch
        logger.warning("OTel import failed despite probe success: %s", exc)
        return False

    # ----------------------- resource attributes ---------------------------
    # Keep attribute keys aligned with the OTel semantic conventions so
    # downstream dashboards (Grafana, Tempo) can filter by them without
    # per-service mapping configs.
    service_name = os.environ.get("OTEL_SERVICE_NAME", "execution-market-mcp")
    service_version = os.environ.get("GIT_SHA", "unknown")
    deployment_env = os.environ.get("ENVIRONMENT", "development")

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": deployment_env,
        }
    )

    # ----------------------- sampler ---------------------------------------
    # Head-based ratio sampler — cheap and predictable. For tail-based
    # smart sampling (always keep errors, sample 10% of successes), rely
    # on the collector-side processor instead of the SDK.
    try:
        sampler_ratio = float(os.environ.get("OTEL_TRACES_SAMPLER_ARG", "0.1"))
    except ValueError:
        sampler_ratio = 0.1
    # Clamp to [0, 1] so a mis-set env var can't break the sampler.
    sampler_ratio = max(0.0, min(1.0, sampler_ratio))
    sampler = TraceIdRatioBased(sampler_ratio)

    # ----------------------- exporter + provider ---------------------------
    # ``OTEL_EXPORTER_OTLP_ENDPOINT`` is also read by the exporter itself,
    # but we pass it explicitly so this module is the single source of
    # documentation for the env var.
    endpoint = os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"
    ).rstrip("/")
    # The HTTP exporter wants the full ``/v1/traces`` URL; append if caller
    # gave us just the base.
    if not endpoint.endswith("/v1/traces"):
        endpoint = f"{endpoint}/v1/traces"

    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider = TracerProvider(resource=resource, sampler=sampler)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # ----------------------- auto-instrumentation --------------------------
    # Order matters only insofar as these must run before the first
    # httpx/requests client is constructed at request time. Caller
    # (main.py) invokes setup_tracing() before those libs are imported.
    try:
        HTTPXClientInstrumentor().instrument()
    except Exception as exc:  # pragma: no cover — best-effort
        logger.warning("HTTPX instrumentation failed: %s", exc)

    try:
        RequestsInstrumentor().instrument()
    except Exception as exc:  # pragma: no cover — best-effort
        logger.warning("Requests instrumentation failed: %s", exc)

    # Inject trace_id / span_id into every LogRecord so the JSON formatter
    # serializes them alongside request_id. ``set_logging_format=False``
    # because we already own formatting via ``logging_config.py``.
    try:
        LoggingInstrumentor().instrument(set_logging_format=False)
    except Exception as exc:  # pragma: no cover
        logger.warning("Logging instrumentation failed: %s", exc)

    _TRACING_INITIALIZED = True
    logger.info(
        "OpenTelemetry tracing initialized "
        "(service=%s version=%s env=%s endpoint=%s sampler=%.2f)",
        service_name,
        service_version,
        deployment_env,
        endpoint,
        sampler_ratio,
    )
    return True


def instrument_fastapi_app(app) -> bool:
    """Attach OTel instrumentation to the FastAPI app. Safe cold-start.

    Must be called AFTER ``app = FastAPI(...)`` — the instrumentor wraps
    the app's ASGI callable in place. No-op when tracing is disabled or
    setup_tracing() hasn't been called yet.
    """
    if not _TRACING_INITIALIZED:
        return False
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:  # pragma: no cover
        return False
    try:
        # Exclude health/metrics endpoints — they're polled aggressively and
        # create span noise that buries real request traces.
        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="healthz,livez,readyz,metrics",
        )
        logger.info("FastAPI OTel instrumentation attached")
        return True
    except Exception as exc:
        logger.warning("FastAPI instrumentation failed: %s", exc)
        return False


def get_tracer(name: str):
    """Return a tracer — no-op tracer when tracing is disabled.

    Callers should use this helper instead of calling
    ``opentelemetry.trace.get_tracer`` directly so tests and dev boots
    without OTel installed never hit an ``ImportError``.
    """
    if not TRACING_AVAILABLE:

        class _NoopSpan:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def set_attribute(self, *_args, **_kwargs):
                pass

            def set_status(self, *_args, **_kwargs):
                pass

            def record_exception(self, *_args, **_kwargs):
                pass

        class _NoopTracer:
            def start_as_current_span(self, *_args, **_kwargs):
                return _NoopSpan()

            def start_span(self, *_args, **_kwargs):
                return _NoopSpan()

        return _NoopTracer()
    from opentelemetry import trace

    return trace.get_tracer(name)
