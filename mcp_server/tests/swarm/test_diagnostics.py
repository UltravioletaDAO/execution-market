"""
SwarmDiagnostics Test Suite — 48th swarm module.

Tests the unified health aggregation, trend analysis, alerting,
and snapshot capabilities of the diagnostics layer.
"""

import time

from mcp_server.swarm.diagnostics import (
    SwarmDiagnostics,
    HealthStatus,
    TrendDirection,
    SubsystemHealth,
    PerformanceTrend,
    Alert,
)


# ──────────────────────────────────────────────────────────────
# Health Check Registration and Execution
# ──────────────────────────────────────────────────────────────


class TestHealthCheckRegistration:
    """Tests for registering and managing health checks."""

    def test_register_health_check(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="test", status=HealthStatus.HEALTHY)
        )
        assert "test" in diag.registered_checks

    def test_unregister_health_check(self):
        diag = SwarmDiagnostics()
        diag.register_health_check("test", lambda: SubsystemHealth(name="test"))
        assert diag.unregister_health_check("test") is True
        assert "test" not in diag.registered_checks

    def test_unregister_nonexistent(self):
        diag = SwarmDiagnostics()
        assert diag.unregister_health_check("nope") is False

    def test_multiple_registrations(self):
        diag = SwarmDiagnostics()
        for i in range(5):
            diag.register_health_check(
                f"sub_{i}",
                lambda: SubsystemHealth(name="sub", status=HealthStatus.HEALTHY),
            )
        assert len(diag.registered_checks) == 5

    def test_overwrite_registration(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="test", status=HealthStatus.HEALTHY)
        )
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="test", status=HealthStatus.CRITICAL)
        )
        report = diag.run_health_check()
        assert report.subsystems[0].status == HealthStatus.CRITICAL


class TestHealthCheckExecution:
    """Tests for running health checks."""

    def test_run_empty_produces_unknown(self):
        diag = SwarmDiagnostics()
        report = diag.run_health_check()
        assert report.overall_status == HealthStatus.UNKNOWN
        assert len(report.subsystems) == 0

    def test_all_healthy(self):
        diag = SwarmDiagnostics()
        for i in range(3):
            diag.register_health_check(
                f"sub_{i}",
                lambda: SubsystemHealth(name="", status=HealthStatus.HEALTHY),
            )
        report = diag.run_health_check()
        assert report.overall_status == HealthStatus.HEALTHY
        assert report.healthy_count == 3

    def test_one_degraded_degrades_overall(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "healthy", lambda: SubsystemHealth(name="h", status=HealthStatus.HEALTHY)
        )
        diag.register_health_check(
            "degraded", lambda: SubsystemHealth(name="d", status=HealthStatus.DEGRADED)
        )
        report = diag.run_health_check()
        assert report.overall_status == HealthStatus.DEGRADED

    def test_one_critical_makes_overall_critical(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "healthy", lambda: SubsystemHealth(name="h", status=HealthStatus.HEALTHY)
        )
        diag.register_health_check(
            "critical", lambda: SubsystemHealth(name="c", status=HealthStatus.CRITICAL)
        )
        report = diag.run_health_check()
        assert report.overall_status == HealthStatus.CRITICAL

    def test_critical_beats_degraded(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "degraded", lambda: SubsystemHealth(name="d", status=HealthStatus.DEGRADED)
        )
        diag.register_health_check(
            "critical", lambda: SubsystemHealth(name="c", status=HealthStatus.CRITICAL)
        )
        report = diag.run_health_check()
        assert report.overall_status == HealthStatus.CRITICAL

    def test_failing_health_check_returns_unknown(self):
        diag = SwarmDiagnostics()

        def broken():
            raise RuntimeError("boom")

        diag.register_health_check("broken", broken)
        report = diag.run_health_check()
        assert report.subsystems[0].status == HealthStatus.UNKNOWN
        assert "RuntimeError" in report.subsystems[0].message
        assert report.subsystems[0].error == "boom"

    def test_mixed_healthy_and_unknown(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "healthy", lambda: SubsystemHealth(name="h", status=HealthStatus.HEALTHY)
        )
        diag.register_health_check(
            "unknown", lambda: SubsystemHealth(name="u", status=HealthStatus.UNKNOWN)
        )
        report = diag.run_health_check()
        # Mix of healthy + unknown → healthy (unknown is not degradation)
        assert report.overall_status == HealthStatus.HEALTHY

    def test_all_unknown(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "u1", lambda: SubsystemHealth(name="u", status=HealthStatus.UNKNOWN)
        )
        diag.register_health_check(
            "u2", lambda: SubsystemHealth(name="u", status=HealthStatus.UNKNOWN)
        )
        report = diag.run_health_check()
        assert report.overall_status == HealthStatus.UNKNOWN

    def test_health_check_increments_counter(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="t", status=HealthStatus.HEALTHY)
        )
        diag.run_health_check()
        diag.run_health_check()
        diag.run_health_check()
        assert diag._check_count == 3

    def test_report_duration_measured(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="t", status=HealthStatus.HEALTHY)
        )
        report = diag.run_health_check()
        assert report.duration_ms >= 0

    def test_report_summary_text(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "a", lambda: SubsystemHealth(name="a", status=HealthStatus.HEALTHY)
        )
        diag.register_health_check(
            "b", lambda: SubsystemHealth(name="b", status=HealthStatus.DEGRADED)
        )
        report = diag.run_health_check()
        assert "2 subsystems" in report.summary
        assert "1 healthy" in report.summary
        assert "1 degraded" in report.summary

    def test_report_to_dict(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="t", status=HealthStatus.HEALTHY)
        )
        report = diag.run_health_check()
        d = report.to_dict()
        assert "overall_status" in d
        assert "subsystems" in d
        assert "counts" in d
        assert d["counts"]["total"] == 1


# ──────────────────────────────────────────────────────────────
# Metrics Recording
# ──────────────────────────────────────────────────────────────


class TestMetricsRecording:
    """Tests for recording and retrieving metrics."""

    def test_record_and_retrieve(self):
        diag = SwarmDiagnostics()
        diag.record_metric("throughput", 42.5)
        history = diag.get_metric_history("throughput")
        assert len(history) == 1
        assert history[0][1] == 42.5

    def test_multiple_records(self):
        diag = SwarmDiagnostics()
        for i in range(10):
            diag.record_metric("throughput", float(i))
        history = diag.get_metric_history("throughput")
        assert len(history) == 10

    def test_history_limit(self):
        diag = SwarmDiagnostics()
        for i in range(20):
            diag.record_metric("x", float(i))
        history = diag.get_metric_history("x", limit=5)
        assert len(history) == 5
        assert history[-1][1] == 19.0  # Most recent

    def test_nonexistent_metric_returns_empty(self):
        diag = SwarmDiagnostics()
        assert diag.get_metric_history("nope") == []

    def test_metric_names_tracked(self):
        diag = SwarmDiagnostics()
        diag.record_metric("a", 1.0)
        diag.record_metric("b", 2.0)
        assert set(diag.metric_names) == {"a", "b"}

    def test_custom_timestamp(self):
        diag = SwarmDiagnostics()
        diag.record_metric("x", 5.0, timestamp=1000.0)
        history = diag.get_metric_history("x")
        assert history[0][0] == 1000.0

    def test_max_history_bounded(self):
        diag = SwarmDiagnostics()
        for i in range(diag.MAX_METRICS_HISTORY + 100):
            diag.record_metric("x", float(i))
        history = diag.get_metric_history("x", limit=diag.MAX_METRICS_HISTORY + 100)
        assert len(history) == diag.MAX_METRICS_HISTORY

    def test_metric_stats(self):
        diag = SwarmDiagnostics()
        for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
            diag.record_metric("x", v)
        stats = diag.get_metric_stats("x")
        assert stats["count"] == 5
        assert stats["mean"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["latest"] == 50.0
        assert stats["median"] == 30.0

    def test_stats_empty_metric(self):
        diag = SwarmDiagnostics()
        stats = diag.get_metric_stats("empty")
        assert stats["count"] == 0

    def test_stats_single_value(self):
        diag = SwarmDiagnostics()
        diag.record_metric("x", 42.0)
        stats = diag.get_metric_stats("x")
        assert stats["count"] == 1
        assert stats["std"] == 0.0


# ──────────────────────────────────────────────────────────────
# Trend Analysis
# ──────────────────────────────────────────────────────────────


class TestTrendAnalysis:
    """Tests for trend computation."""

    def test_insufficient_data(self):
        diag = SwarmDiagnostics()
        diag.record_metric("x", 1.0)
        trend = diag.compute_trend("x")
        assert trend.direction == TrendDirection.INSUFFICIENT_DATA

    def test_improving_trend(self):
        diag = SwarmDiagnostics()
        now = time.time()
        # Previous window: low values
        for i in range(5):
            diag.record_metric("x", 10.0, timestamp=now - 7200 + i * 100)
        # Recent window: high values
        for i in range(5):
            diag.record_metric("x", 50.0, timestamp=now - 1800 + i * 100)
        trend = diag.compute_trend("x", window_seconds=3600)
        assert trend.direction == TrendDirection.IMPROVING
        assert trend.change_pct > 0

    def test_declining_trend(self):
        diag = SwarmDiagnostics()
        now = time.time()
        # Previous: high
        for i in range(5):
            diag.record_metric("x", 50.0, timestamp=now - 7200 + i * 100)
        # Recent: low
        for i in range(5):
            diag.record_metric("x", 10.0, timestamp=now - 1800 + i * 100)
        trend = diag.compute_trend("x", window_seconds=3600)
        assert trend.direction == TrendDirection.DECLINING
        assert trend.change_pct < 0

    def test_stable_trend(self):
        diag = SwarmDiagnostics()
        now = time.time()
        for i in range(10):
            diag.record_metric(
                "x", 50.0 + (i % 2) * 0.5, timestamp=now - 7200 + i * 800
            )
        trend = diag.compute_trend("x", window_seconds=3600)
        assert trend.direction == TrendDirection.STABLE

    def test_compute_all_trends(self):
        diag = SwarmDiagnostics()
        now = time.time()
        for name in ["a", "b", "c"]:
            for i in range(5):
                diag.record_metric(name, float(i), timestamp=now - 1800 + i * 100)
        trends = diag.compute_all_trends()
        assert len(trends) == 3

    def test_trend_to_dict(self):
        trend = PerformanceTrend(
            signal_name="test",
            direction=TrendDirection.IMPROVING,
            current_value=50.0,
            previous_value=40.0,
            change_pct=25.0,
            data_points=10,
        )
        d = trend.to_dict()
        assert d["signal"] == "test"
        assert d["direction"] == "improving"
        assert d["current"] == 50.0


# ──────────────────────────────────────────────────────────────
# Alerts
# ──────────────────────────────────────────────────────────────


class TestAlerts:
    """Tests for alert management."""

    def test_raise_alert(self):
        diag = SwarmDiagnostics()
        alert = Alert(source="test", level="warning", message="test alert")
        diag.raise_alert(alert)
        digest = diag.get_alert_digest()
        assert len(digest.alerts) == 1
        assert digest.total_warnings == 1

    def test_critical_alert(self):
        diag = SwarmDiagnostics()
        alert = Alert(source="test", level="critical", message="bad")
        diag.raise_alert(alert)
        digest = diag.get_alert_digest()
        assert digest.total_criticals == 1

    def test_alert_callback(self):
        diag = SwarmDiagnostics()
        received = []
        diag.register_alert_callback(lambda a: received.append(a))
        alert = Alert(source="test", level="warning", message="hello")
        diag.raise_alert(alert)
        assert len(received) == 1
        assert received[0].message == "hello"

    def test_alert_callback_error_isolation(self):
        diag = SwarmDiagnostics()

        def bad_callback(a):
            raise ValueError("oops")

        diag.register_alert_callback(bad_callback)
        # Should not raise
        diag.raise_alert(Alert(source="test", level="warning", message="x"))

    def test_alert_deque_bounded(self):
        diag = SwarmDiagnostics()
        for i in range(diag.MAX_ALERTS + 100):
            diag.raise_alert(
                Alert(source="test", level="warning", message=f"alert {i}")
            )
        digest = diag.get_alert_digest(limit=diag.MAX_ALERTS + 100)
        assert len(digest.alerts) <= diag.MAX_ALERTS

    def test_alert_digest_limit(self):
        diag = SwarmDiagnostics()
        for i in range(20):
            diag.raise_alert(Alert(source="test", level="warning", message=f"a{i}"))
        digest = diag.get_alert_digest(limit=5)
        assert len(digest.alerts) == 5

    def test_threshold_check_warning(self):
        diag = SwarmDiagnostics()
        diag.record_metric("cpu", 75.0)
        alert = diag.check_thresholds(
            "cpu", warning_threshold=70.0, critical_threshold=90.0
        )
        assert alert is not None
        assert alert.level == "warning"

    def test_threshold_check_critical(self):
        diag = SwarmDiagnostics()
        diag.record_metric("cpu", 95.0)
        alert = diag.check_thresholds(
            "cpu", warning_threshold=70.0, critical_threshold=90.0
        )
        assert alert is not None
        assert alert.level == "critical"

    def test_threshold_check_ok(self):
        diag = SwarmDiagnostics()
        diag.record_metric("cpu", 50.0)
        alert = diag.check_thresholds(
            "cpu", warning_threshold=70.0, critical_threshold=90.0
        )
        assert alert is None

    def test_threshold_check_below_mode(self):
        diag = SwarmDiagnostics()
        diag.record_metric("throughput", 5.0)
        alert = diag.check_thresholds(
            "throughput",
            warning_threshold=20.0,
            critical_threshold=10.0,
            comparison="below",
        )
        assert alert is not None
        assert alert.level == "critical"

    def test_threshold_no_data(self):
        diag = SwarmDiagnostics()
        alert = diag.check_thresholds(
            "missing", warning_threshold=50.0, critical_threshold=90.0
        )
        assert alert is None

    def test_alert_to_dict(self):
        alert = Alert(
            source="test",
            level="warning",
            message="msg",
            metric_name="cpu",
            metric_value=75.0,
            threshold=70.0,
        )
        d = alert.to_dict()
        assert d["source"] == "test"
        assert d["level"] == "warning"
        assert d["metric_value"] == 75.0


# ──────────────────────────────────────────────────────────────
# Snapshots
# ──────────────────────────────────────────────────────────────


class TestSnapshots:
    """Tests for diagnostic snapshots."""

    def test_take_snapshot(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="t", status=HealthStatus.HEALTHY)
        )
        diag.record_metric("x", 42.0)
        snapshot = diag.take_snapshot()
        assert snapshot.health.overall_status == HealthStatus.HEALTHY
        assert "check_count" in snapshot.metadata

    def test_snapshot_without_health(self):
        diag = SwarmDiagnostics()
        diag.record_metric("x", 42.0)
        snapshot = diag.take_snapshot(include_health=False)
        assert len(snapshot.health.subsystems) == 0

    def test_snapshot_includes_trends(self):
        diag = SwarmDiagnostics()
        now = time.time()
        for i in range(5):
            diag.record_metric("x", float(i), timestamp=now - 1800 + i * 100)
        snapshot = diag.take_snapshot()
        assert len(snapshot.trends) == 1

    def test_snapshot_includes_alerts(self):
        diag = SwarmDiagnostics()
        diag.raise_alert(Alert(source="test", level="warning", message="w"))
        diag.raise_alert(Alert(source="test", level="critical", message="c"))
        snapshot = diag.take_snapshot()
        assert snapshot.alerts.total_warnings == 1
        assert snapshot.alerts.total_criticals == 1

    def test_snapshot_history_bounded(self):
        diag = SwarmDiagnostics()
        for i in range(diag.MAX_SNAPSHOTS + 10):
            diag.take_snapshot(include_health=False)
        assert len(diag._snapshots) == diag.MAX_SNAPSHOTS

    def test_snapshot_history_retrieval(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="t", status=HealthStatus.HEALTHY)
        )
        for i in range(5):
            diag.take_snapshot()
        history = diag.get_snapshot_history(limit=3)
        assert len(history) == 3
        assert "overall_status" in history[0]

    def test_snapshot_to_dict(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="t", status=HealthStatus.HEALTHY)
        )
        snapshot = diag.take_snapshot()
        d = snapshot.to_dict()
        assert "health" in d
        assert "trends" in d
        assert "alerts" in d
        assert "metadata" in d


# ──────────────────────────────────────────────────────────────
# Pre-built Health Checks
# ──────────────────────────────────────────────────────────────


class TestPrebuiltChecks:
    """Tests for factory-created health checks."""

    def test_metric_health_check_healthy(self):
        diag = SwarmDiagnostics()
        diag.record_metric("success_rate", 0.95)
        check = SwarmDiagnostics.create_metric_health_check(
            diag, "success_rate", healthy_min=0.8, degraded_min=0.5, label="success"
        )
        result = check()
        assert result.status == HealthStatus.HEALTHY

    def test_metric_health_check_degraded(self):
        diag = SwarmDiagnostics()
        diag.record_metric("success_rate", 0.6)
        check = SwarmDiagnostics.create_metric_health_check(
            diag, "success_rate", healthy_min=0.8, degraded_min=0.5
        )
        result = check()
        assert result.status == HealthStatus.DEGRADED

    def test_metric_health_check_critical(self):
        diag = SwarmDiagnostics()
        diag.record_metric("success_rate", 0.3)
        check = SwarmDiagnostics.create_metric_health_check(
            diag, "success_rate", healthy_min=0.8, degraded_min=0.5
        )
        result = check()
        assert result.status == HealthStatus.CRITICAL

    def test_metric_health_check_no_data(self):
        diag = SwarmDiagnostics()
        check = SwarmDiagnostics.create_metric_health_check(
            diag, "missing", healthy_min=0.8, degraded_min=0.5
        )
        result = check()
        assert result.status == HealthStatus.UNKNOWN


# ──────────────────────────────────────────────────────────────
# Status
# ──────────────────────────────────────────────────────────────


class TestStatus:
    """Tests for quick status overview."""

    def test_status_empty(self):
        diag = SwarmDiagnostics()
        s = diag.status()
        assert s["registered_checks"] == 0
        assert s["metric_count"] == 0
        assert s["alert_count"] == 0

    def test_status_after_activity(self):
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "test", lambda: SubsystemHealth(name="t", status=HealthStatus.HEALTHY)
        )
        diag.record_metric("x", 1.0)
        diag.raise_alert(Alert(source="t", level="warning", message="w"))
        diag.run_health_check()

        s = diag.status()
        assert s["registered_checks"] == 1
        assert s["metric_count"] == 1
        assert s["alert_count"] == 1
        assert s["total_checks_run"] == 1


# ──────────────────────────────────────────────────────────────
# Integration: Multi-Subsystem Scenario
# ──────────────────────────────────────────────────────────────


class TestIntegrationScenario:
    """End-to-end integration testing with multiple subsystems."""

    def test_full_diagnostic_flow(self):
        """Register checks, record metrics, raise alerts, take snapshot."""
        diag = SwarmDiagnostics()

        # Register 5 subsystem health checks
        for name, status in [
            ("coordinator", HealthStatus.HEALTHY),
            ("scheduler", HealthStatus.HEALTHY),
            ("lifecycle", HealthStatus.DEGRADED),
            ("budget", HealthStatus.HEALTHY),
            ("throughput", HealthStatus.HEALTHY),
        ]:
            st = status  # closure capture
            diag.register_health_check(
                name, lambda s=st: SubsystemHealth(name="", status=s)
            )

        # Record metrics
        now = time.time()
        for i in range(20):
            diag.record_metric(
                "tasks_per_hour", 40.0 + i * 0.5, timestamp=now - 3600 + i * 180
            )
            diag.record_metric(
                "success_rate", 0.85 + i * 0.005, timestamp=now - 3600 + i * 180
            )

        # Raise some alerts
        diag.raise_alert(
            Alert(
                source="lifecycle",
                level="warning",
                message="Agent degraded",
                metric_name="agent_health",
                metric_value=0.6,
            )
        )

        # Take snapshot
        snapshot = diag.take_snapshot()

        assert snapshot.health.overall_status == HealthStatus.DEGRADED
        assert snapshot.health.healthy_count == 4
        assert snapshot.health.degraded_count == 1
        assert len(snapshot.trends) == 2
        assert len(snapshot.alerts.alerts) == 1

    def test_ten_subsystem_health_check(self):
        """10 subsystems with various health states."""
        diag = SwarmDiagnostics()
        states = [
            HealthStatus.HEALTHY,
            HealthStatus.HEALTHY,
            HealthStatus.HEALTHY,
            HealthStatus.HEALTHY,
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.DEGRADED,
            HealthStatus.HEALTHY,
            HealthStatus.HEALTHY,
            HealthStatus.HEALTHY,
        ]
        for i, st in enumerate(states):
            s = st
            diag.register_health_check(
                f"sub_{i}", lambda s=s: SubsystemHealth(name="", status=s)
            )

        report = diag.run_health_check()
        assert report.overall_status == HealthStatus.DEGRADED
        assert report.healthy_count == 8
        assert report.degraded_count == 2
        assert "10 subsystems" in report.summary

    def test_metric_driven_health_checks(self):
        """Use recorded metrics as health check sources."""
        diag = SwarmDiagnostics()

        diag.record_metric("throughput", 45.0)
        diag.record_metric("error_rate", 0.02)

        # Create metric-based health checks
        tp_check = SwarmDiagnostics.create_metric_health_check(
            diag, "throughput", healthy_min=30.0, degraded_min=15.0, label="throughput"
        )
        er_check = SwarmDiagnostics.create_metric_health_check(
            diag, "error_rate", healthy_min=0.0, degraded_min=0.0, label="error_rate"
        )

        diag.register_health_check("throughput", tp_check)
        diag.register_health_check("error_rate", er_check)

        report = diag.run_health_check()
        tp_sub = next(s for s in report.subsystems if s.name == "throughput")
        assert tp_sub.status == HealthStatus.HEALTHY

    def test_rapid_check_cycles(self):
        """50 rapid health check cycles should all succeed."""
        diag = SwarmDiagnostics()
        diag.register_health_check(
            "fast", lambda: SubsystemHealth(name="f", status=HealthStatus.HEALTHY)
        )
        for _ in range(50):
            report = diag.run_health_check()
            assert report.overall_status == HealthStatus.HEALTHY
        assert diag._check_count == 50
