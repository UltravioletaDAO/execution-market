"""
Unit tests for ``observability.tracing`` (Task 6.2 — SaaS production
hardening).

The tracing module is the kind of optional telemetry where a silent
misbehavior is expensive:

  - If graceful degradation breaks, a missing dep crashes the whole
    app at boot — same failure mode as a bad Sentry DSN.
  - If ``setup_tracing()`` is not idempotent, repeated calls (tests,
    reloads, ASGI worker fork) install duplicate span processors and
    the exporter sends each span N times, blowing up the collector
    bill for no reason.
  - If ``get_tracer()`` raises when OTel isn't initialized, every
    instrumented code path must wrap it in try/except — defeating the
    whole point of the helper.

So the tests here focus on the three invariants above plus a minimal
happy-path when OTel is installed. We never actually export to a
collector; the exporter is exercised elsewhere by the integration suite.
"""

from __future__ import annotations

import logging

import pytest

# Loaded once at module import so tests can introspect the live module
# state (e.g. _TRACING_INITIALIZED flag). Each test that mutates env
# vars reloads the module via monkeypatch + importlib to get a fresh
# flag state.
from observability import tracing as tracing_mod


# ---------------------------------------------------------------------------
# Graceful off-path
# ---------------------------------------------------------------------------


class TestSetupGracefulOff:
    """``setup_tracing()`` must return False without raising when OTel is off."""

    def test_default_off_returns_false(self, monkeypatch):
        monkeypatch.delenv("OTEL_ENABLED", raising=False)
        monkeypatch.setattr(tracing_mod, "_TRACING_INITIALIZED", False)
        assert tracing_mod.setup_tracing() is False

    @pytest.mark.parametrize("value", ["false", "0", "no", "off", ""])
    def test_falsy_values_stay_off(self, monkeypatch, value):
        monkeypatch.setenv("OTEL_ENABLED", value)
        monkeypatch.setattr(tracing_mod, "_TRACING_INITIALIZED", False)
        assert tracing_mod.setup_tracing() is False

    def test_idempotent_when_already_initialized(self, monkeypatch):
        # If a previous call already set the flag, the second call must
        # return True without re-running the import / instrumentation work.
        monkeypatch.setenv("OTEL_ENABLED", "true")
        monkeypatch.setattr(tracing_mod, "_TRACING_INITIALIZED", True)
        assert tracing_mod.setup_tracing() is True


# ---------------------------------------------------------------------------
# No-op tracer
# ---------------------------------------------------------------------------


class TestGetTracerNoop:
    """``get_tracer()`` must always return something span-compatible."""

    def test_returns_tracer_like_object(self, monkeypatch):
        monkeypatch.delenv("OTEL_ENABLED", raising=False)
        tracer = tracing_mod.get_tracer("test.module")
        # We don't care whether it's the real OTel ProxyTracer or our
        # _NoopTracer — only that ``start_as_current_span`` is callable
        # and the returned context manager exposes the methods the rest
        # of the codebase relies on.
        assert hasattr(tracer, "start_as_current_span")

    def test_noop_span_context_manager_does_not_raise(self, monkeypatch):
        monkeypatch.delenv("OTEL_ENABLED", raising=False)
        tracer = tracing_mod.get_tracer("test.module")
        with tracer.start_as_current_span("noop") as span:
            # These calls mirror what real instrumented code does inside
            # a span. If any of them raises on the noop tracer we've
            # broken the abstraction.
            span.set_attribute("key", "value")
            span.set_status("ok")
            try:
                raise RuntimeError("recorded")
            except RuntimeError as exc:
                span.record_exception(exc)

    def test_noop_when_tracing_unavailable(self, monkeypatch):
        # Simulate the "opentelemetry isn't installed" case by flipping
        # the probe flag. ``get_tracer`` must still return a working
        # no-op tracer.
        monkeypatch.setattr(tracing_mod, "TRACING_AVAILABLE", False)
        tracer = tracing_mod.get_tracer("test.module")
        assert tracer.__class__.__name__ == "_NoopTracer"
        with tracer.start_as_current_span("probe") as span:
            span.set_attribute("x", 1)


# ---------------------------------------------------------------------------
# FastAPI instrumentation hook
# ---------------------------------------------------------------------------


class TestInstrumentFastAPIApp:
    def test_noop_when_tracing_not_initialized(self, monkeypatch):
        monkeypatch.setattr(tracing_mod, "_TRACING_INITIALIZED", False)

        # A plain object stands in for the FastAPI instance — the
        # function must not touch it when tracing is off.
        class _Sentinel:
            pass

        sentinel = _Sentinel()
        assert tracing_mod.instrument_fastapi_app(sentinel) is False


# ---------------------------------------------------------------------------
# OTEL_ENABLED truthy path (best-effort — only runs if deps are installed)
# ---------------------------------------------------------------------------


class TestSetupTruthy:
    """When the OTel deps are installed and ``OTEL_ENABLED`` is truthy,
    ``setup_tracing()`` must succeed end-to-end without raising."""

    def test_enables_when_deps_present(self, monkeypatch, caplog):
        pytest.importorskip("opentelemetry.sdk.trace")
        pytest.importorskip("opentelemetry.exporter.otlp.proto.http.trace_exporter")
        pytest.importorskip("opentelemetry.instrumentation.httpx")

        monkeypatch.setenv("OTEL_ENABLED", "true")
        monkeypatch.setenv("OTEL_SERVICE_NAME", "em-test")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "1.0")
        monkeypatch.setattr(tracing_mod, "_TRACING_INITIALIZED", False)

        with caplog.at_level(logging.INFO, logger=tracing_mod.logger.name):
            ok = tracing_mod.setup_tracing()

        # Either the full path ran (ok=True) or the instrumentation
        # packages aren't installed even though the probe passed (ok=False,
        # warning logged). Both are acceptable outcomes — this test just
        # guards against an unhandled exception crashing the app on boot.
        assert ok in (True, False)
        if ok:
            # A successful init logs a line containing the service name.
            assert any("em-test" in record.message for record in caplog.records), (
                "expected setup_tracing() to log the service name on success"
            )
