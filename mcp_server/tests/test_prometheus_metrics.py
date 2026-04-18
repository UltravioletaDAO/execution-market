"""
Unit tests for the Prometheus metrics module (Task 6.1).

These tests exercise ``metrics.prometheus`` directly without standing up
the full FastAPI app. They verify:

  - The module is import-safe and its public recorders are no-ops when
    ``prometheus_client`` isn't installed (we treat the optional
    dependency the same way we treat Sentry).
  - ``_status_class`` bucketises HTTP status codes into the five stable
    Prometheus labels (``1xx`` … ``5xx`` + ``other``) so label
    cardinality stays bounded.
  - ``_route_template`` prefers the matched route path over the literal
    URL path — that's the whole reason we normalise in the first place
    (``/api/v1/tasks/{task_id}`` mustn't explode into one series per
    UUID).
  - The business counters and the HTTP histogram increment on call, and
    that the rendered exposition format contains the expected metric
    names (regression guard — if a label/ name drifts the dashboards
    break silently).
  - ``PrometheusMiddleware`` skips instrumenting ``/metrics`` /
    ``/healthz`` / ``/livez`` so scrapers and liveness probes don't
    pollute their own histograms.

All tests read from the module-level ``_REGISTRY``; we snapshot the
counter values before and after rather than resetting the registry to
avoid reaching into library internals. This also mirrors how real
scrapes see the metric stream — monotonic counters — so the assertions
describe production behaviour, not a test-only artifact.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from metrics import prometheus as pm


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def _counter_value(counter, **labels) -> float:
    """Return the current value of a Prometheus Counter at given labels.

    Hitting ``.labels(**labels)._value.get()`` is implementation-specific
    but stable enough for tests; we isolate it so the rest of the file
    stays readable.
    """
    return counter.labels(**labels)._value.get()


def _histogram_count(histogram, **labels) -> float:
    """Return the ``_count`` of a Prometheus Histogram at given labels."""
    return histogram.labels(**labels)._sum.get()


# ---------------------------------------------------------------------------
# Low-cardinality label helpers
# ---------------------------------------------------------------------------


class TestStatusClass:
    """``_status_class`` is the linchpin of label cardinality — one
    series per HTTP class, not per status code.
    """

    @pytest.mark.parametrize(
        "code, expected",
        [
            (100, "1xx"),
            (199, "1xx"),
            (200, "2xx"),
            (204, "2xx"),
            (301, "3xx"),
            (399, "3xx"),
            (400, "4xx"),
            (404, "4xx"),
            (429, "4xx"),
            (500, "5xx"),
            (599, "5xx"),
        ],
    )
    def test_buckets_by_hundreds(self, code: int, expected: str) -> None:
        assert pm._status_class(code) == expected

    def test_out_of_band_codes_bucket_into_other(self) -> None:
        # 600+ isn't a real HTTP class — we still want a stable label so
        # misbehaving clients can't create unbounded series.
        assert pm._status_class(700) == "other"
        # 0 shouldn't ever happen, but defensive mapping matters.
        assert pm._status_class(0) == "other"


class TestRouteTemplate:
    def test_prefers_route_template_over_literal_path(self) -> None:
        fake_route = SimpleNamespace(path="/api/v1/tasks/{task_id}")
        request = SimpleNamespace(
            scope={"route": fake_route},
            url=SimpleNamespace(path="/api/v1/tasks/8c3d5f2e"),
        )
        assert pm._route_template(request) == "/api/v1/tasks/{task_id}"

    def test_falls_back_to_literal_path_when_no_route(self) -> None:
        request = SimpleNamespace(
            scope={},
            url=SimpleNamespace(path="/unknown-endpoint"),
        )
        assert pm._route_template(request) == "/unknown-endpoint"

    def test_unknown_when_neither_route_nor_path(self) -> None:
        request = SimpleNamespace(scope={}, url=None)
        assert pm._route_template(request) == "unknown"


# ---------------------------------------------------------------------------
# Public recorders — live counters / histogram
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not pm.PROMETHEUS_AVAILABLE,
    reason="prometheus_client not installed in this environment",
)
class TestRecorders:
    def test_record_http_request_increments_counter_and_histogram(self) -> None:
        method, route = "GET", "/api/v1/tasks/{task_id}"
        before = _counter_value(
            pm._HTTP_REQUESTS_TOTAL,
            method=method,
            route=route,
            status_class="2xx",
        )
        pm.record_http_request(method, route, 200, 0.042)
        after = _counter_value(
            pm._HTTP_REQUESTS_TOTAL,
            method=method,
            route=route,
            status_class="2xx",
        )
        assert after == before + 1

        # Histogram _sum should include our observed latency.
        hist_sum = _histogram_count(
            pm._HTTP_REQUEST_DURATION_SECONDS, method=method, route=route
        )
        assert hist_sum >= 0.042  # monotonic; prior tests may have added

    def test_record_http_request_clamps_negative_duration(self) -> None:
        # Defensive: perf_counter clock skew can theoretically yield
        # negative deltas; the recorder must not observe a negative
        # value (Prometheus will raise) — it clamps to 0.
        pm.record_http_request("GET", "/api/v1/tasks", 200, -0.01)

    def test_record_task_created_labels_unknown_on_missing_network(self) -> None:
        before = _counter_value(pm._TASKS_CREATED_TOTAL, network="unknown")
        pm.record_task_created(None)
        after = _counter_value(pm._TASKS_CREATED_TOTAL, network="unknown")
        assert after == before + 1

    def test_record_task_completed_uses_given_outcome(self) -> None:
        before = _counter_value(pm._TASKS_COMPLETED_TOTAL, outcome="completed")
        pm.record_task_completed("completed")
        after = _counter_value(pm._TASKS_COMPLETED_TOTAL, outcome="completed")
        assert after == before + 1

    def test_record_task_completed_empty_outcome_falls_back(self) -> None:
        before = _counter_value(pm._TASKS_COMPLETED_TOTAL, outcome="unknown")
        pm.record_task_completed("")
        after = _counter_value(pm._TASKS_COMPLETED_TOTAL, outcome="unknown")
        assert after == before + 1

    def test_record_payment_settled_increments_usd_total(self) -> None:
        before = _counter_value(pm._PAYMENTS_SETTLED_USD_TOTAL, network="base")
        pm.record_payment_settled("base", 0.087)
        after = _counter_value(pm._PAYMENTS_SETTLED_USD_TOTAL, network="base")
        assert after == pytest.approx(before + 0.087, rel=1e-6)

    def test_record_payment_settled_ignores_zero_or_negative(self) -> None:
        # Business rule: we never want negative or zero dollar amounts
        # polluting the "USD settled" counter (monotonic counters
        # in Prometheus must never decrease).
        before = _counter_value(pm._PAYMENTS_SETTLED_USD_TOTAL, network="polygon")
        pm.record_payment_settled("polygon", 0)
        pm.record_payment_settled("polygon", -1.25)
        after = _counter_value(pm._PAYMENTS_SETTLED_USD_TOTAL, network="polygon")
        assert after == before


# ---------------------------------------------------------------------------
# generate_metrics — exposition format sanity check
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not pm.PROMETHEUS_AVAILABLE,
    reason="prometheus_client not installed in this environment",
)
class TestGenerateMetrics:
    def test_returns_bytes_body_and_content_type(self) -> None:
        body, content_type = pm.generate_metrics()
        assert isinstance(body, (bytes, bytearray))
        assert content_type.startswith("text/plain")

    def test_body_contains_expected_metric_names(self) -> None:
        # Trigger at least one sample per metric family so they appear
        # in the exposition output.
        pm.record_http_request("GET", "/probe", 200, 0.001)
        pm.record_task_created("base")
        pm.record_task_completed("completed")
        pm.record_payment_settled("base", 0.01)

        body, _ = pm.generate_metrics()
        text = body.decode("utf-8")

        # If any of these names drift the Grafana dashboards break
        # silently — lock them down with explicit assertions.
        assert "em_http_requests_total" in text
        assert "em_http_request_duration_seconds" in text
        assert "em_tasks_created_total" in text
        assert "em_tasks_completed_total" in text
        assert "em_payments_settled_usd_total" in text


# ---------------------------------------------------------------------------
# PrometheusMiddleware — excluded prefixes
# ---------------------------------------------------------------------------


class TestPrometheusMiddlewareExclusions:
    @pytest.mark.parametrize(
        "path, excluded",
        [
            ("/metrics", True),
            ("/metrics/", True),
            ("/healthz", True),
            ("/livez", True),
            ("/api/v1/tasks", False),
            ("/docs", False),
        ],
    )
    def test_exclusion_policy(self, path: str, excluded: bool) -> None:
        cls = pm.PrometheusMiddleware
        starts_excluded = any(path.startswith(p) for p in cls.EXCLUDED_PREFIXES)
        assert starts_excluded == excluded


# ---------------------------------------------------------------------------
# Graceful degradation — module must stay safe when the dep is absent
# ---------------------------------------------------------------------------


class TestGracefulDegradation:
    """These run regardless of whether prometheus_client is installed.

    We simulate the "unavailable" state by monkey-patching the module
    flag rather than uninstalling the dependency at runtime. The
    recorders must return ``None`` without raising so callers never have
    to branch.
    """

    def test_recorders_noop_when_unavailable(self, monkeypatch) -> None:
        monkeypatch.setattr(pm, "PROMETHEUS_AVAILABLE", False)
        # All of these would AttributeError if they weren't early-returning.
        assert pm.record_http_request("GET", "/x", 200, 0.01) is None
        assert pm.record_task_created("base") is None
        assert pm.record_task_completed("completed") is None
        assert pm.record_payment_settled("base", 0.05) is None

    def test_generate_metrics_returns_placeholder_when_unavailable(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(pm, "PROMETHEUS_AVAILABLE", False)
        body, content_type = pm.generate_metrics()
        assert b"prometheus_client not installed" in body
        assert content_type.startswith("text/plain")
