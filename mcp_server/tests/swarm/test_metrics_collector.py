"""
Tests for swarm.metrics_collector module.

Covers:
    - Recording events (routing, completion, expiry, pipeline, workforce, health)
    - Counters and gauges
    - Summary generation
    - Trend analysis
    - Alert conditions
    - Event querying
    - Reset functionality
    - Edge cases
"""

import time
import pytest
from dataclasses import asdict

from mcp_server.swarm.metrics_collector import (
    MetricsCollector,
    MetricEvent,
)


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------


class TestRecording:
    def test_record_routing(self):
        m = MetricsCollector()
        m.record_routing("task_1", "0xA", score=85.0, response_minutes=12.0)
        assert m.get_counter("routing.total") == 1
        assert m.get_counter("routing.to_available") == 1

    def test_record_routing_unavailable(self):
        m = MetricsCollector()
        m.record_routing("task_1", "0xA", score=70.0, available_now=False)
        assert m.get_counter("routing.total") == 1
        assert m.get_counter("routing.to_available") == 0

    def test_record_completion(self):
        m = MetricsCollector()
        m.record_completion("task_1", quality=0.9, hours_to_complete=2.5, on_time=True)
        assert m.get_counter("completion.total") == 1
        assert m.get_counter("completion.on_time") == 1

    def test_record_expiry(self):
        m = MetricsCollector()
        m.record_expiry("task_1", reason="worker_no_show")
        assert m.get_counter("completion.expired") == 1

    def test_record_pipeline(self):
        m = MetricsCollector()
        m.record_pipeline("match", "success", 150.0)
        m.record_pipeline("match", "error", 50.0)
        assert m.get_counter("pipeline.match.total") == 2
        assert m.get_counter("pipeline.match.success") == 1
        assert m.get_counter("pipeline.match.error") == 1

    def test_record_worker_activity(self):
        m = MetricsCollector()
        m.record_worker_activity("0xA", "joined")
        m.record_worker_activity("0xB", "active")
        assert m.get_counter("workforce.joined") == 1
        assert m.get_counter("workforce.active") == 1

    def test_record_source_health(self):
        m = MetricsCollector()
        m.record_source_health("remoteok", "healthy", 0.95)
        assert m.get_gauge("source.remoteok.quality") == 0.95
        assert m.get_gauge("source.remoteok.status") == "healthy"


# ---------------------------------------------------------------------------
# Counters and Gauges
# ---------------------------------------------------------------------------


class TestCountersAndGauges:
    def test_increment(self):
        m = MetricsCollector()
        m.increment("custom.counter")
        m.increment("custom.counter", 5)
        assert m.get_counter("custom.counter") == 6

    def test_set_gauge(self):
        m = MetricsCollector()
        m.set_gauge("active_workers", 24)
        assert m.get_gauge("active_workers") == 24

    def test_gauge_overwrite(self):
        m = MetricsCollector()
        m.set_gauge("pool_size", 10)
        m.set_gauge("pool_size", 15)
        assert m.get_gauge("pool_size") == 15

    def test_missing_counter(self):
        m = MetricsCollector()
        assert m.get_counter("nonexistent") == 0

    def test_missing_gauge(self):
        m = MetricsCollector()
        assert m.get_gauge("nonexistent") is None


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_empty_summary(self):
        m = MetricsCollector()
        s = m.summary()
        assert "routing" in s
        assert "completion" in s
        assert "pipeline" in s
        assert "workforce" in s
        assert "health" in s
        assert s["uptime_seconds"] >= 0

    def test_routing_summary(self):
        m = MetricsCollector()
        m.record_routing("t1", "0xA", 80.0, response_minutes=10.0)
        m.record_routing("t2", "0xB", 90.0, response_minutes=20.0)
        s = m.summary()
        assert s["routing"]["tasks_routed"] == 2
        assert s["routing"]["avg_match_score"] == 85.0
        assert s["routing"]["avg_response_minutes"] == 15.0

    def test_completion_summary(self):
        m = MetricsCollector()
        m.record_completion("t1", quality=0.8, hours_to_complete=2.0)
        m.record_completion("t2", quality=0.9, hours_to_complete=3.0)
        m.record_expiry("t3")
        s = m.summary()
        assert s["completion"]["completed"] == 2
        assert s["completion"]["expired"] == 1
        assert s["completion"]["completion_rate"] == pytest.approx(0.667, abs=0.01)

    def test_pipeline_summary(self):
        m = MetricsCollector()
        m.record_pipeline("ingest", "success", 100.0)
        m.record_pipeline("ingest", "success", 120.0)
        m.record_pipeline("ingest", "error", 50.0)
        s = m.summary()
        assert "ingest" in s["pipeline"]
        assert s["pipeline"]["ingest"]["total"] == 3
        assert s["pipeline"]["ingest"]["success"] == 2
        assert s["pipeline"]["ingest"]["success_rate"] == pytest.approx(0.667, abs=0.01)

    def test_health_summary(self):
        m = MetricsCollector()
        m.record_source_health("remoteok", "healthy", 0.95)
        m.record_source_health("weworkremotely", "degraded", 0.60)
        s = m.summary()
        assert s["health"]["sources_tracked"] == 2
        assert "remoteok" in s["health"]["sources"]

    def test_counters_in_summary(self):
        m = MetricsCollector()
        m.increment("custom.test", 3)
        s = m.summary()
        assert s["counters"]["custom.test"] == 3

    def test_gauges_in_summary(self):
        m = MetricsCollector()
        m.set_gauge("pool_health", 85.0)
        s = m.summary()
        assert s["gauges"]["pool_health"] == 85.0


# ---------------------------------------------------------------------------
# Event Querying
# ---------------------------------------------------------------------------


class TestEventQuerying:
    def test_get_events(self):
        m = MetricsCollector()
        m.record_routing("t1", "0xA", 80.0)
        m.record_routing("t2", "0xB", 90.0)
        events = m.get_events("routing")
        assert len(events) == 2
        # Should be reverse chronological
        assert events[0]["timestamp"] >= events[1]["timestamp"]

    def test_get_events_limit(self):
        m = MetricsCollector()
        for i in range(10):
            m.record_routing(f"t{i}", "0xA", 80.0)
        events = m.get_events("routing", limit=5)
        assert len(events) == 5

    def test_get_events_since(self):
        m = MetricsCollector()
        m.record_routing("t1", "0xA", 80.0)
        cutoff = time.time() + 1  # Future
        m.record_routing("t2", "0xB", 90.0)
        # Both events are before cutoff, so since=cutoff should return 0
        events = m.get_events("routing", since=cutoff)
        assert len(events) == 0

    def test_get_events_empty_category(self):
        m = MetricsCollector()
        events = m.get_events("nonexistent")
        assert events == []


# ---------------------------------------------------------------------------
# Trend Analysis
# ---------------------------------------------------------------------------


class TestTrends:
    def test_empty_trend(self):
        m = MetricsCollector()
        trend = m.trend("routing", "task_routed", buckets=4)
        assert len(trend) == 4
        assert all(t["count"] == 0 for t in trend)
        assert all(t["avg_value"] is None for t in trend)

    def test_trend_with_data(self):
        m = MetricsCollector()
        # Record some events
        for _ in range(5):
            m.record_routing("t", "0xA", 80.0)
        trend = m.trend("routing", "task_routed", buckets=4, window_seconds=60)
        # All events are recent, so they should be in the last bucket
        total_events = sum(t["count"] for t in trend)
        assert total_events == 5

    def test_trend_bucket_count(self):
        m = MetricsCollector()
        trend = m.trend("routing", "task_routed", buckets=12)
        assert len(trend) == 12


# ---------------------------------------------------------------------------
# Alert Conditions
# ---------------------------------------------------------------------------


class TestAlerts:
    def test_no_alerts_when_healthy(self):
        m = MetricsCollector()
        for i in range(10):
            m.record_completion(f"t{i}", quality=0.9)
        m.record_expiry("expired1")  # 1/11 = ~9% expiry
        alerts = m.check_alerts()
        expiry_alerts = [a for a in alerts if a["type"] == "high_expiry_rate"]
        assert len(expiry_alerts) == 0

    def test_high_expiry_alert(self):
        m = MetricsCollector()
        for i in range(3):
            m.record_completion(f"t{i}")
        for i in range(5):
            m.record_expiry(f"expired{i}")
        alerts = m.check_alerts()
        expiry_alerts = [a for a in alerts if a["type"] == "high_expiry_rate"]
        assert len(expiry_alerts) == 1
        assert expiry_alerts[0]["level"] == "critical"  # 5/8 > 50%

    def test_pipeline_error_alert(self):
        m = MetricsCollector()
        for i in range(5):
            m.record_pipeline("ingest", "error", 100.0)
        m.record_pipeline("ingest", "success", 100.0)
        alerts = m.check_alerts()
        pipe_alerts = [a for a in alerts if a["type"] == "pipeline_errors"]
        assert len(pipe_alerts) >= 1

    def test_low_availability_routing_alert(self):
        m = MetricsCollector()
        for i in range(8):
            m.record_routing(f"t{i}", "0xA", 80.0, available_now=False)
        m.record_routing("t9", "0xB", 80.0, available_now=True)
        alerts = m.check_alerts()
        avail_alerts = [a for a in alerts if a["type"] == "low_availability_routing"]
        assert len(avail_alerts) == 1

    def test_no_alerts_with_few_events(self):
        m = MetricsCollector()
        m.record_expiry("t1")
        m.record_expiry("t2")
        # Only 2 events, below threshold of 5
        alerts = m.check_alerts()
        expiry_alerts = [a for a in alerts if a["type"] == "high_expiry_rate"]
        assert len(expiry_alerts) == 0


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_clears_all(self):
        m = MetricsCollector()
        m.record_routing("t1", "0xA", 80.0)
        m.increment("custom.counter", 5)
        m.set_gauge("test", 42)
        m.reset()
        assert m.get_counter("routing.total") == 0
        assert m.get_counter("custom.counter") == 0
        assert m.get_gauge("test") is None
        assert m.get_events("routing") == []


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_max_events_cap(self):
        m = MetricsCollector(max_events=10)
        for i in range(20):
            m.record_routing(f"t{i}", "0xA", 80.0)
        events = m.get_events("routing")
        assert len(events) == 10

    def test_metric_event_dataclass(self):
        e = MetricEvent(
            category="test",
            name="test_event",
            value=1.0,
            timestamp=time.time(),
            tags={"key": "value"},
        )
        asdict(e) if hasattr(e, "__dataclass_fields__") else {}
        assert e.category == "test"
        assert e.tags["key"] == "value"

    def test_concurrent_categories(self):
        m = MetricsCollector()
        m.record_routing("t1", "0xA", 80.0)
        m.record_completion("t1", quality=0.9)
        m.record_pipeline("match", "success", 100.0)
        s = m.summary()
        assert s["routing"]["tasks_routed"] == 1
        assert s["completion"]["completed"] == 1
        assert "match" in s["pipeline"]

    def test_multiple_pipelines(self):
        m = MetricsCollector()
        m.record_pipeline("ingest", "success", 100.0)
        m.record_pipeline("match", "success", 200.0)
        m.record_pipeline("feedback", "error", 50.0)
        s = m.summary()
        assert len(s["pipeline"]) == 3
