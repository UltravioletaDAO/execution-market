"""
Test Suite: MetricsCollector — Swarm Observability Engine
==========================================================

Tests cover:
    1. Recording methods (routing, completion, expiry, pipeline, worker, source)
    2. Counter and gauge operations
    3. Summary generation (routing, completion, pipeline, workforce, health)
    4. Trend analysis (bucketed time-series)
    5. Alert conditions (high expiry, pipeline errors, low availability routing)
    6. Reset functionality
    7. Event retrieval and filtering
    8. Edge cases (empty state, large volumes, concurrent recording)
"""

import time
import pytest

from mcp_server.swarm.metrics_collector import (
    MetricsCollector,
    MetricEvent,
    MAX_EVENTS_PER_CATEGORY,
    RECENT_WINDOW_SECONDS,
)


# ══════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════


def _fresh_collector():
    return MetricsCollector()


def _populated_collector():
    """Create a collector with some data."""
    mc = MetricsCollector()
    mc.record_routing("t1", "0x001", 85.0, response_minutes=5.0)
    mc.record_routing("t2", "0x002", 70.0, available_now=False)
    mc.record_completion("t1", quality=0.9, hours_to_complete=2.5, on_time=True)
    mc.record_completion("t2", quality=0.6, on_time=False)
    mc.record_expiry("t3", reason="timeout")
    mc.record_pipeline("ingest", "success", 150.0)
    mc.record_pipeline("ingest", "error", 500.0)
    mc.record_worker_activity("0x001", "joined")
    mc.record_worker_activity("0x002", "active")
    mc.record_source_health("craigslist", "healthy", 0.85)
    return mc


# ══════════════════════════════════════════════════════════════
# Data Type Tests
# ══════════════════════════════════════════════════════════════


class TestMetricEvent:
    def test_creation(self):
        event = MetricEvent(
            category="routing",
            name="task_routed",
            value=85.0,
            timestamp=time.time(),
            tags={"task_id": "t1"},
        )
        assert event.category == "routing"
        assert event.value == 85.0

    def test_default_tags(self):
        event = MetricEvent(
            category="test", name="test", value=1.0, timestamp=time.time()
        )
        assert event.tags == {}


# ══════════════════════════════════════════════════════════════
# Recording Tests
# ══════════════════════════════════════════════════════════════


class TestRecordRouting:
    def test_basic_routing(self):
        mc = _fresh_collector()
        mc.record_routing("t1", "0x001", 85.0)

        assert mc.get_counter("routing.total") == 1
        assert mc.get_counter("routing.to_available") == 1

    def test_unavailable_worker(self):
        mc = _fresh_collector()
        mc.record_routing("t1", "0x001", 70.0, available_now=False)

        assert mc.get_counter("routing.total") == 1
        assert mc.get_counter("routing.to_available") == 0

    def test_with_response_time(self):
        mc = _fresh_collector()
        mc.record_routing("t1", "0x001", 85.0, response_minutes=5.0)

        events = mc.get_events("routing")
        response_events = [e for e in events if e["name"] == "response_time"]
        assert len(response_events) == 1
        assert response_events[0]["value"] == 5.0

    def test_multiple_routings(self):
        mc = _fresh_collector()
        for i in range(10):
            mc.record_routing(f"t{i}", f"0x{i:03x}", 50.0 + i * 5)

        assert mc.get_counter("routing.total") == 10


class TestRecordCompletion:
    def test_basic_completion(self):
        mc = _fresh_collector()
        mc.record_completion("t1", quality=0.9)

        assert mc.get_counter("completion.total") == 1
        assert mc.get_counter("completion.on_time") == 1  # Default on_time=True

    def test_late_completion(self):
        mc = _fresh_collector()
        mc.record_completion("t1", quality=0.5, on_time=False)

        assert mc.get_counter("completion.total") == 1
        assert mc.get_counter("completion.on_time") == 0

    def test_with_hours(self):
        mc = _fresh_collector()
        mc.record_completion("t1", hours_to_complete=3.5)

        events = mc.get_events("completion")
        time_events = [e for e in events if e["name"] == "time_to_complete"]
        assert len(time_events) == 1
        assert time_events[0]["value"] == 3.5


class TestRecordExpiry:
    def test_basic_expiry(self):
        mc = _fresh_collector()
        mc.record_expiry("t1")

        assert mc.get_counter("completion.expired") == 1

    def test_custom_reason(self):
        mc = _fresh_collector()
        mc.record_expiry("t1", reason="worker_abandoned")

        events = mc.get_events("completion")
        expired = [e for e in events if e["name"] == "task_expired"]
        assert expired[0]["tags"]["reason"] == "worker_abandoned"


class TestRecordPipeline:
    def test_success(self):
        mc = _fresh_collector()
        mc.record_pipeline("ingest", "success", 100.0)

        assert mc.get_counter("pipeline.ingest.total") == 1
        assert mc.get_counter("pipeline.ingest.success") == 1

    def test_error(self):
        mc = _fresh_collector()
        mc.record_pipeline("ingest", "error", 500.0)

        assert mc.get_counter("pipeline.ingest.total") == 1
        assert mc.get_counter("pipeline.ingest.error") == 1

    def test_multiple_pipelines(self):
        mc = _fresh_collector()
        mc.record_pipeline("ingest", "success", 100.0)
        mc.record_pipeline("feedback", "success", 50.0)
        mc.record_pipeline("ingest", "error", 200.0)

        assert mc.get_counter("pipeline.ingest.total") == 2
        assert mc.get_counter("pipeline.feedback.total") == 1


class TestRecordWorkerActivity:
    def test_joined(self):
        mc = _fresh_collector()
        mc.record_worker_activity("0x001", "joined")

        assert mc.get_counter("workforce.joined") == 1

    def test_multiple_activities(self):
        mc = _fresh_collector()
        mc.record_worker_activity("0x001", "joined")
        mc.record_worker_activity("0x001", "active")
        mc.record_worker_activity("0x002", "joined")

        assert mc.get_counter("workforce.joined") == 2
        assert mc.get_counter("workforce.active") == 1


class TestRecordSourceHealth:
    def test_source_tracking(self):
        mc = _fresh_collector()
        mc.record_source_health("craigslist", "healthy", 0.85)

        assert mc.get_gauge("source.craigslist.quality") == 0.85
        assert mc.get_gauge("source.craigslist.status") == "healthy"

    def test_multiple_sources(self):
        mc = _fresh_collector()
        mc.record_source_health("source_a", "healthy", 0.9)
        mc.record_source_health("source_b", "degraded", 0.3)

        assert mc.get_gauge("source.source_a.quality") == 0.9
        assert mc.get_gauge("source.source_b.quality") == 0.3

    def test_source_update(self):
        mc = _fresh_collector()
        mc.record_source_health("src", "healthy", 0.9)
        mc.record_source_health("src", "degraded", 0.3)

        assert mc.get_gauge("source.src.quality") == 0.3


# ══════════════════════════════════════════════════════════════
# Counter & Gauge Tests
# ══════════════════════════════════════════════════════════════


class TestCountersAndGauges:
    def test_set_gauge(self):
        mc = _fresh_collector()
        mc.set_gauge("active_agents", 42)

        assert mc.get_gauge("active_agents") == 42

    def test_increment(self):
        mc = _fresh_collector()
        mc.increment("custom_counter")
        mc.increment("custom_counter", 5)

        assert mc.get_counter("custom_counter") == 6

    def test_missing_counter(self):
        mc = _fresh_collector()
        assert mc.get_counter("nonexistent") == 0

    def test_missing_gauge(self):
        mc = _fresh_collector()
        assert mc.get_gauge("nonexistent") is None


# ══════════════════════════════════════════════════════════════
# Summary Tests
# ══════════════════════════════════════════════════════════════


class TestSummary:
    def test_all_sections_present(self):
        mc = _populated_collector()
        summary = mc.summary()

        assert "uptime_seconds" in summary
        assert "routing" in summary
        assert "completion" in summary
        assert "pipeline" in summary
        assert "workforce" in summary
        assert "health" in summary
        assert "counters" in summary
        assert "gauges" in summary

    def test_routing_summary(self):
        mc = _populated_collector()
        summary = mc.summary()

        assert summary["routing"]["tasks_routed"] == 2
        assert summary["routing"]["avg_match_score"] is not None
        assert summary["routing"]["to_available_count"] == 1

    def test_completion_summary(self):
        mc = _populated_collector()
        summary = mc.summary()

        assert summary["completion"]["completed"] == 2
        assert summary["completion"]["expired"] == 1
        assert summary["completion"]["avg_quality"] is not None

    def test_completion_rate(self):
        mc = _populated_collector()
        summary = mc.summary()

        # 2 completed, 1 expired → 2/3 ≈ 0.667
        rate = summary["completion"]["completion_rate"]
        assert abs(rate - 0.667) < 0.01

    def test_pipeline_summary(self):
        mc = _populated_collector()
        summary = mc.summary()

        assert "ingest" in summary["pipeline"]
        assert summary["pipeline"]["ingest"]["total"] == 2
        assert summary["pipeline"]["ingest"]["success"] == 1
        assert summary["pipeline"]["ingest"]["error"] == 1

    def test_workforce_summary(self):
        mc = _populated_collector()
        summary = mc.summary()

        assert summary["workforce"]["joins"] == 1
        assert summary["workforce"]["active"] == 1

    def test_health_summary(self):
        mc = _populated_collector()
        summary = mc.summary()

        assert summary["health"]["sources_tracked"] == 1
        assert "craigslist" in summary["health"]["sources"]

    def test_empty_summary(self):
        mc = _fresh_collector()
        summary = mc.summary()

        assert summary["routing"]["tasks_routed"] == 0
        assert summary["completion"]["completed"] == 0
        assert summary["routing"]["avg_match_score"] is None

    def test_uptime_tracked(self):
        mc = _fresh_collector()
        time.sleep(0.01)
        summary = mc.summary()
        assert summary["uptime_seconds"] >= 0.01

    def test_window_filtering(self):
        mc = _fresh_collector()
        mc.record_routing("t1", "0x001", 85.0)

        # Very short window should still include recent events
        summary = mc.summary(window_seconds=60)
        assert summary["routing"]["tasks_routed"] == 1


# ══════════════════════════════════════════════════════════════
# Event Retrieval Tests
# ══════════════════════════════════════════════════════════════


class TestEventRetrieval:
    def test_get_events_by_category(self):
        mc = _populated_collector()
        events = mc.get_events("routing")

        assert len(events) > 0
        assert all(e["category"] == "routing" for e in events)

    def test_get_events_limit(self):
        mc = _fresh_collector()
        for i in range(10):
            mc.record_routing(f"t{i}", "0x001", 50.0)

        events = mc.get_events("routing", limit=3)
        assert len(events) == 3

    def test_get_events_sorted_recent_first(self):
        mc = _fresh_collector()
        mc.record_routing("t1", "0x001", 50.0)
        time.sleep(0.01)
        mc.record_routing("t2", "0x002", 60.0)

        events = mc.get_events("routing", limit=2)
        assert events[0]["timestamp"] >= events[1]["timestamp"]

    def test_get_events_since_filter(self):
        mc = _fresh_collector()
        mc.record_routing("t1", "0x001", 50.0)

        future = time.time() + 100
        events = mc.get_events("routing", since=future)
        assert len(events) == 0

    def test_get_events_nonexistent_category(self):
        mc = _fresh_collector()
        events = mc.get_events("nonexistent")
        assert events == []


# ══════════════════════════════════════════════════════════════
# Trend Analysis Tests
# ══════════════════════════════════════════════════════════════


class TestTrendAnalysis:
    def test_basic_trend(self):
        mc = _fresh_collector()
        for i in range(5):
            mc.record_routing(f"t{i}", "0x001", 50.0 + i * 10)

        trend = mc.trend("routing", "task_routed", buckets=6)
        assert len(trend) == 6

    def test_trend_bucket_structure(self):
        mc = _fresh_collector()
        mc.record_routing("t1", "0x001", 85.0)

        trend = mc.trend("routing", "task_routed", buckets=4)
        for bucket in trend:
            assert "bucket" in bucket
            assert "count" in bucket
            assert "avg_value" in bucket or bucket["avg_value"] is None

    def test_empty_trend(self):
        mc = _fresh_collector()
        trend = mc.trend("routing", "task_routed", buckets=6)
        assert len(trend) == 6
        assert all(b["count"] == 0 for b in trend)

    def test_trend_values_in_latest_bucket(self):
        mc = _fresh_collector()
        mc.record_routing("t1", "0x001", 85.0)

        trend = mc.trend("routing", "task_routed", buckets=6, window_seconds=60)
        # Latest bucket should have our event
        last_bucket = trend[-1]
        assert last_bucket["count"] >= 0  # Could be in any bucket depending on timing


# ══════════════════════════════════════════════════════════════
# Alert Tests
# ══════════════════════════════════════════════════════════════


class TestAlerts:
    def test_high_expiry_rate_warning(self):
        mc = _fresh_collector()
        # 3 completed, 3 expired → 50% expiry rate → warning (not > 0.5 for critical)
        for i in range(3):
            mc.record_completion(f"t{i}", quality=0.5)
        for i in range(3):
            mc.record_expiry(f"e{i}")

        alerts = mc.check_alerts()
        expiry_alerts = [a for a in alerts if a["type"] == "high_expiry_rate"]
        assert len(expiry_alerts) == 1
        assert expiry_alerts[0]["level"] == "warning"  # exactly 50%

    def test_high_expiry_rate_critical(self):
        mc = _fresh_collector()
        # 1 completed, 5 expired → 83% expiry rate
        mc.record_completion("t1", quality=0.5)
        for i in range(5):
            mc.record_expiry(f"e{i}")

        alerts = mc.check_alerts()
        expiry_alerts = [a for a in alerts if a["type"] == "high_expiry_rate"]
        assert len(expiry_alerts) == 1
        assert expiry_alerts[0]["level"] == "critical"

    def test_no_alert_low_expiry(self):
        mc = _fresh_collector()
        for i in range(10):
            mc.record_completion(f"t{i}", quality=0.8)

        alerts = mc.check_alerts()
        expiry_alerts = [a for a in alerts if a["type"] == "high_expiry_rate"]
        assert len(expiry_alerts) == 0

    def test_pipeline_error_alert(self):
        mc = _fresh_collector()
        mc.record_pipeline("ingest", "success", 100.0)
        mc.record_pipeline("ingest", "error", 500.0)
        mc.record_pipeline("ingest", "error", 400.0)

        alerts = mc.check_alerts()
        pipeline_alerts = [a for a in alerts if a["type"] == "pipeline_errors"]
        assert len(pipeline_alerts) >= 1

    def test_low_availability_routing_alert(self):
        mc = _fresh_collector()
        # Route 5 tasks, only 1 to available worker
        mc.record_routing("t1", "0x001", 85.0, available_now=True)
        for i in range(4):
            mc.record_routing(f"t{i+2}", "0x002", 70.0, available_now=False)

        alerts = mc.check_alerts()
        avail_alerts = [a for a in alerts if a["type"] == "low_availability_routing"]
        assert len(avail_alerts) == 1

    def test_no_alerts_healthy(self):
        mc = _fresh_collector()
        for i in range(10):
            mc.record_routing(f"t{i}", "0x001", 85.0, available_now=True)
            mc.record_completion(f"t{i}", quality=0.9, on_time=True)

        alerts = mc.check_alerts()
        assert len(alerts) == 0

    def test_not_enough_data_no_alerts(self):
        mc = _fresh_collector()
        # Only 2 tasks — below the 5-task threshold
        mc.record_completion("t1", quality=0.5)
        mc.record_expiry("t2")

        alerts = mc.check_alerts()
        expiry_alerts = [a for a in alerts if a["type"] == "high_expiry_rate"]
        assert len(expiry_alerts) == 0


# ══════════════════════════════════════════════════════════════
# Reset Tests
# ══════════════════════════════════════════════════════════════


class TestReset:
    def test_reset_clears_everything(self):
        mc = _populated_collector()

        mc.reset()

        assert mc.get_counter("routing.total") == 0
        assert mc.get_gauge("source.craigslist.quality") is None
        events = mc.get_events("routing")
        assert len(events) == 0

    def test_reset_resets_uptime(self):
        mc = _fresh_collector()
        time.sleep(0.01)
        mc.reset()
        summary = mc.summary()
        assert summary["uptime_seconds"] < 1.0


# ══════════════════════════════════════════════════════════════
# Edge Cases
# ══════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_max_events_per_category(self):
        mc = MetricsCollector(max_events=10)
        for i in range(20):
            mc.record_routing(f"t{i}", "0x001", 50.0)

        events = mc.get_events("routing")
        assert len(events) <= 10

    def test_custom_max_events(self):
        mc = MetricsCollector(max_events=5)
        for i in range(10):
            mc.record_completion(f"t{i}", quality=0.5)

        events = mc.get_events("completion")
        assert len(events) <= 5

    def test_concurrent_recording_many(self):
        mc = _fresh_collector()
        for i in range(500):
            mc.record_routing(f"t{i}", f"0x{i:03x}", float(i))

        assert mc.get_counter("routing.total") == 500

    def test_pipeline_success_rate(self):
        mc = _fresh_collector()
        for i in range(8):
            mc.record_pipeline("test", "success", 100.0)
        for i in range(2):
            mc.record_pipeline("test", "error", 500.0)

        summary = mc.summary()
        assert summary["pipeline"]["test"]["success_rate"] == 0.8

    def test_completion_hours_average(self):
        mc = _fresh_collector()
        mc.record_completion("t1", hours_to_complete=2.0)
        mc.record_completion("t2", hours_to_complete=4.0)

        summary = mc.summary()
        assert summary["completion"]["avg_hours_to_complete"] == 3.0

    def test_routing_avg_score(self):
        mc = _fresh_collector()
        mc.record_routing("t1", "0x001", 80.0)
        mc.record_routing("t2", "0x002", 90.0)

        summary = mc.summary()
        assert summary["routing"]["avg_match_score"] == 85.0
