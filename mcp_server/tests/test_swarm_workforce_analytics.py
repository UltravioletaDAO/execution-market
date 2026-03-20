"""Tests for WorkforceAnalytics — Aggregated Intelligence Dashboard."""

import time

import pytest

from mcp_server.swarm.workforce_analytics import (
    AlertSeverity,
    AnalyticsAlert,
    AnalyticsReport,
    CategoryBreakdown,
    MetricPoint,
    MetricSeries,
    TaskEvent,
    TrendDirection,
    WorkerProfile,
    WorkforceAnalytics,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


def _make_events(
    n: int = 50,
    completion_rate: float = 0.7,
    categories: list[str] | None = None,
    workers: list[str] | None = None,
) -> list[TaskEvent]:
    """Generate synthetic task events."""
    import random
    rng = random.Random(42)
    cats = categories or ["delivery", "inspection", "photography", "survey"]
    wkrs = workers or [f"worker_{i}" for i in range(8)]

    events = []
    for i in range(n):
        is_success = rng.random() < completion_rate
        events.append(TaskEvent(
            task_id=f"task_{i}",
            category=rng.choice(cats),
            worker_id=rng.choice(wkrs),
            outcome="completed" if is_success else rng.choice(["expired", "rejected"]),
            quality_score=rng.uniform(0.5, 1.0) if is_success else 0.0,
            bounty_usd=rng.uniform(2.0, 50.0),
            completion_hours=rng.uniform(1.0, 36.0) if is_success else 0.0,
            timestamp=1700000000 + i * 3600,
        ))
    return events


@pytest.fixture
def events():
    return _make_events()


@pytest.fixture
def analytics():
    return WorkforceAnalytics()


@pytest.fixture
def loaded_analytics(events):
    a = WorkforceAnalytics()
    a.ingest_batch(events)
    return a


# ──────────────────────────────────────────────────────────────
# MetricPoint Tests
# ──────────────────────────────────────────────────────────────


class TestMetricPoint:
    def test_creation(self):
        p = MetricPoint(timestamp=1700000000, value=0.75, label="test")
        assert p.timestamp == 1700000000
        assert p.value == 0.75
        assert p.label == "test"


# ──────────────────────────────────────────────────────────────
# MetricSeries Tests
# ──────────────────────────────────────────────────────────────


class TestMetricSeries:
    def test_empty_series(self):
        s = MetricSeries(name="test")
        assert s.latest is None
        assert s.average == 0.0
        assert s.trend == TrendDirection.INSUFFICIENT_DATA
        assert s.min_value == 0.0
        assert s.max_value == 0.0

    def test_add_points(self):
        s = MetricSeries(name="test")
        s.add(0.5, timestamp=1.0)
        s.add(0.7, timestamp=2.0)
        assert s.latest == 0.7
        assert len(s.points) == 2

    def test_average(self):
        s = MetricSeries(name="test")
        s.add(0.4)
        s.add(0.6)
        s.add(0.8)
        assert s.average == pytest.approx(0.6)

    def test_min_max(self):
        s = MetricSeries(name="test")
        s.add(0.2)
        s.add(0.9)
        s.add(0.5)
        assert s.min_value == 0.2
        assert s.max_value == 0.9

    def test_trend_improving(self):
        s = MetricSeries(name="test")
        for i in range(6):
            s.add(0.3 + i * 0.1, timestamp=float(i))
        assert s.trend == TrendDirection.IMPROVING

    def test_trend_declining(self):
        s = MetricSeries(name="test")
        for i in range(6):
            s.add(0.8 - i * 0.1, timestamp=float(i))
        assert s.trend == TrendDirection.DECLINING

    def test_trend_stable(self):
        s = MetricSeries(name="test")
        for i in range(6):
            s.add(0.5, timestamp=float(i))
        assert s.trend == TrendDirection.STABLE

    def test_trend_insufficient_data(self):
        s = MetricSeries(name="test")
        s.add(0.5)
        s.add(0.6)
        assert s.trend == TrendDirection.INSUFFICIENT_DATA


# ──────────────────────────────────────────────────────────────
# WorkerProfile Tests
# ──────────────────────────────────────────────────────────────


class TestWorkerProfile:
    def test_completion_rate(self):
        p = WorkerProfile(worker_id="w1", tasks_completed=7, tasks_total=10)
        assert p.completion_rate == pytest.approx(0.7)

    def test_completion_rate_zero(self):
        p = WorkerProfile(worker_id="w1", tasks_completed=0, tasks_total=0)
        assert p.completion_rate == 0.0

    def test_is_mvp(self):
        p = WorkerProfile(
            worker_id="w1",
            tasks_completed=10,
            tasks_total=11,
            avg_quality=0.85,
        )
        assert p.is_mvp

    def test_is_not_mvp_low_volume(self):
        p = WorkerProfile(
            worker_id="w1",
            tasks_completed=2,
            tasks_total=2,
            avg_quality=0.9,
        )
        assert not p.is_mvp  # Not enough volume

    def test_is_at_risk(self):
        p = WorkerProfile(
            worker_id="w1",
            tasks_completed=1,
            tasks_total=5,
        )
        assert p.is_at_risk

    def test_not_at_risk_low_volume(self):
        p = WorkerProfile(
            worker_id="w1",
            tasks_completed=0,
            tasks_total=2,
        )
        assert not p.is_at_risk  # Not enough tasks to judge

    def test_specialization(self):
        p = WorkerProfile(
            worker_id="w1",
            categories=["delivery", "delivery", "delivery", "inspection"],
        )
        assert p.specialization == "delivery"

    def test_specialization_generalist(self):
        p = WorkerProfile(
            worker_id="w1",
            categories=["delivery", "inspection", "photography", "survey"],
        )
        assert p.specialization == "generalist"

    def test_specialization_empty(self):
        p = WorkerProfile(worker_id="w1")
        assert p.specialization == "generalist"


# ──────────────────────────────────────────────────────────────
# CategoryBreakdown Tests
# ──────────────────────────────────────────────────────────────


class TestCategoryBreakdown:
    def test_completion_rate(self):
        b = CategoryBreakdown(name="delivery", task_count=10, completed=7)
        assert b.completion_rate == pytest.approx(0.7)

    def test_completion_rate_zero(self):
        b = CategoryBreakdown(name="delivery", task_count=0)
        assert b.completion_rate == 0.0

    def test_value_per_dollar(self):
        b = CategoryBreakdown(name="delivery", avg_quality=0.8, avg_bounty_usd=10.0)
        assert b.value_per_dollar == pytest.approx(0.08)

    def test_value_per_dollar_zero_bounty(self):
        b = CategoryBreakdown(name="delivery", avg_quality=0.8, avg_bounty_usd=0.0)
        assert b.value_per_dollar == 0.0


# ──────────────────────────────────────────────────────────────
# AnalyticsReport Tests
# ──────────────────────────────────────────────────────────────


class TestAnalyticsReport:
    def test_health_score_perfect(self):
        report = AnalyticsReport(
            completion_rate=1.0,
            avg_quality=1.0,
            total_workers=15,
        )
        assert report.health_score >= 80

    def test_health_score_bad(self):
        report = AnalyticsReport(
            completion_rate=0.2,
            avg_quality=0.3,
            total_workers=1,
            alerts=[
                AnalyticsAlert(severity=AlertSeverity.CRITICAL, message="bad"),
            ],
        )
        assert report.health_score < 50

    def test_empty_report(self):
        report = AnalyticsReport()
        assert report.health_score >= 0


# ──────────────────────────────────────────────────────────────
# WorkforceAnalytics — Ingestion
# ──────────────────────────────────────────────────────────────


class TestIngestion:
    def test_ingest_single(self, analytics):
        event = TaskEvent(task_id="t1", outcome="completed", quality_score=0.9)
        analytics.ingest(event)
        assert analytics.stats()["events_ingested"] == 1

    def test_ingest_batch(self, analytics, events):
        analytics.ingest_batch(events)
        assert analytics.stats()["events_ingested"] == len(events)

    def test_series_created_on_ingest(self, analytics):
        analytics.ingest(TaskEvent(task_id="t1", outcome="completed", quality_score=0.8))
        assert analytics.get_series("completion_rate") is not None
        assert analytics.get_series("quality") is not None
        assert analytics.get_series("volume") is not None


# ──────────────────────────────────────────────────────────────
# WorkforceAnalytics — Report
# ──────────────────────────────────────────────────────────────


class TestReport:
    def test_empty_report(self, analytics):
        report = analytics.generate_report()
        assert report.total_tasks == 0
        assert report.data_points == 0

    def test_basic_report(self, loaded_analytics):
        report = loaded_analytics.generate_report()
        assert report.total_tasks == 50
        assert report.total_completed > 0
        assert 0.0 < report.completion_rate <= 1.0
        assert report.total_workers > 0

    def test_report_quality(self, loaded_analytics):
        report = loaded_analytics.generate_report()
        assert report.avg_quality > 0.0

    def test_report_speed(self, loaded_analytics):
        report = loaded_analytics.generate_report()
        assert report.avg_speed_hours > 0.0

    def test_report_spending(self, loaded_analytics):
        report = loaded_analytics.generate_report()
        assert report.total_spent_usd > 0.0

    def test_category_breakdown(self, loaded_analytics):
        report = loaded_analytics.generate_report()
        assert len(report.category_breakdown) > 0
        assert report.best_category != ""
        assert report.worst_category != ""

    def test_category_sorted_by_count(self, loaded_analytics):
        report = loaded_analytics.generate_report()
        counts = [c.task_count for c in report.category_breakdown]
        assert counts == sorted(counts, reverse=True)

    def test_recommendations_generated(self, loaded_analytics):
        report = loaded_analytics.generate_report()
        assert len(report.recommended_actions) > 0

    def test_trends_included(self, loaded_analytics):
        report = loaded_analytics.generate_report()
        assert len(report.trends) > 0

    def test_health_score_range(self, loaded_analytics):
        report = loaded_analytics.generate_report()
        assert 0.0 <= report.health_score <= 100.0


# ──────────────────────────────────────────────────────────────
# WorkforceAnalytics — Alerts
# ──────────────────────────────────────────────────────────────


class TestAlerts:
    def test_low_completion_alert(self):
        analytics = WorkforceAnalytics(alert_thresholds={"min_completion_rate": 0.9, "min_workers": 0})
        events = _make_events(n=20, completion_rate=0.3)
        analytics.ingest_batch(events)
        report = analytics.generate_report()
        completion_alerts = [a for a in report.alerts if a.metric == "completion_rate"]
        assert len(completion_alerts) >= 1

    def test_low_worker_count_alert(self):
        analytics = WorkforceAnalytics(alert_thresholds={"min_workers": 10, "min_completion_rate": 0.0})
        events = _make_events(n=20, workers=["w1", "w2"])
        analytics.ingest_batch(events)
        report = analytics.generate_report()
        worker_alerts = [a for a in report.alerts if a.metric == "worker_count"]
        assert len(worker_alerts) >= 1

    def test_concentration_alert(self):
        analytics = WorkforceAnalytics(alert_thresholds={
            "max_concentration": 0.5,
            "min_completion_rate": 0.0,
            "min_workers": 0,
        })
        # One worker does everything
        events = [
            TaskEvent(task_id=f"t{i}", worker_id="monopoly_worker", outcome="completed",
                      quality_score=0.8, timestamp=1700000000 + i * 3600)
            for i in range(20)
        ]
        analytics.ingest_batch(events)
        report = analytics.generate_report()
        conc_alerts = [a for a in report.alerts if a.metric == "concentration"]
        assert len(conc_alerts) >= 1

    def test_no_alerts_healthy_system(self):
        analytics = WorkforceAnalytics(alert_thresholds={
            "min_completion_rate": 0.3,
            "min_quality": 0.3,
            "max_avg_hours": 100.0,
            "min_workers": 1,
            "max_concentration": 0.99,
        })
        events = _make_events(n=30, completion_rate=0.9)
        analytics.ingest_batch(events)
        report = analytics.generate_report()
        critical = [a for a in report.alerts if a.severity == AlertSeverity.CRITICAL]
        assert len(critical) == 0


# ──────────────────────────────────────────────────────────────
# WorkforceAnalytics — Worker Analytics
# ──────────────────────────────────────────────────────────────


class TestWorkerAnalytics:
    def test_top_workers(self, loaded_analytics):
        top = loaded_analytics.top_workers(n=3)
        assert len(top) <= 3
        assert all(isinstance(w, WorkerProfile) for w in top)

    def test_top_workers_sorted(self, loaded_analytics):
        top = loaded_analytics.top_workers(n=5)
        completions = [w.tasks_completed for w in top]
        assert completions == sorted(completions, reverse=True)

    def test_worker_detail_found(self, loaded_analytics):
        top = loaded_analytics.top_workers(n=1)
        if top:
            detail = loaded_analytics.worker_detail(top[0].worker_id)
            assert detail is not None
            assert detail.worker_id == top[0].worker_id

    def test_worker_detail_not_found(self, loaded_analytics):
        assert loaded_analytics.worker_detail("nonexistent") is None


# ──────────────────────────────────────────────────────────────
# WorkforceAnalytics — Category Analytics
# ──────────────────────────────────────────────────────────────


class TestCategoryAnalytics:
    def test_category_comparison(self, loaded_analytics):
        cats = loaded_analytics.category_comparison()
        assert len(cats) > 0
        for cat in cats:
            assert isinstance(cat, CategoryBreakdown)
            assert cat.task_count > 0


# ──────────────────────────────────────────────────────────────
# WorkforceAnalytics — Value Analysis
# ──────────────────────────────────────────────────────────────


class TestValueAnalysis:
    def test_value_analysis_empty(self, analytics):
        result = analytics.value_analysis()
        assert result["total_spent"] == 0
        assert result["roi"] == 0

    def test_value_analysis_loaded(self, loaded_analytics):
        result = loaded_analytics.value_analysis()
        assert result["total_spent"] > 0
        assert result["total_wasted"] >= 0
        assert 0.0 <= result["waste_rate"] <= 1.0
        assert result["roi"] >= 0

    def test_value_analysis_all_successful(self):
        analytics = WorkforceAnalytics()
        events = [
            TaskEvent(
                task_id=f"t{i}",
                outcome="completed",
                bounty_usd=10.0,
                quality_score=0.9,
                timestamp=1700000000 + i,
            )
            for i in range(10)
        ]
        analytics.ingest_batch(events)
        result = analytics.value_analysis()
        assert result["total_wasted"] == 0.0
        assert result["waste_rate"] == 0.0


# ──────────────────────────────────────────────────────────────
# WorkforceAnalytics — Correlation Analysis
# ──────────────────────────────────────────────────────────────


class TestCorrelationAnalysis:
    def test_bounty_quality_insufficient_data(self, analytics):
        analytics.ingest(TaskEvent(task_id="t1", outcome="completed", bounty_usd=10, quality_score=0.8))
        result = analytics.bounty_quality_correlation()
        assert result["insight"] == "Insufficient data"

    def test_bounty_quality_with_data(self, loaded_analytics):
        result = loaded_analytics.bounty_quality_correlation()
        assert -1.0 <= result["correlation"] <= 1.0
        assert result["sample_size"] > 0
        assert len(result["insight"]) > 0

    def test_positive_correlation(self):
        analytics = WorkforceAnalytics()
        for i in range(20):
            bounty = 5.0 + i * 2
            quality = 0.3 + i * 0.03
            analytics.ingest(TaskEvent(
                task_id=f"t{i}",
                outcome="completed",
                bounty_usd=bounty,
                quality_score=quality,
                timestamp=1700000000 + i,
            ))
        result = analytics.bounty_quality_correlation()
        assert result["correlation"] > 0.3


# ──────────────────────────────────────────────────────────────
# WorkforceAnalytics — Serialization & Stats
# ──────────────────────────────────────────────────────────────


class TestSerialization:
    def test_to_dict(self, loaded_analytics):
        data = loaded_analytics.to_dict()
        assert "event_count" in data
        assert "series" in data
        assert data["event_count"] == 50

    def test_stats(self, loaded_analytics):
        stats = loaded_analytics.stats()
        assert stats["events_ingested"] == 50
        assert stats["unique_workers"] > 0
        assert stats["unique_categories"] > 0
        assert stats["date_range"]["earliest"] > 0

    def test_stats_empty(self, analytics):
        stats = analytics.stats()
        assert stats["events_ingested"] == 0


# ──────────────────────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────────────────────


class TestIntegration:
    def test_full_pipeline(self):
        """Full analytics pipeline: ingest → report → analyze → insights."""
        analytics = WorkforceAnalytics()

        # Ingest diverse events
        events = _make_events(n=100, completion_rate=0.65)
        analytics.ingest_batch(events)

        # Generate report
        report = analytics.generate_report()
        assert report.total_tasks == 100
        assert report.total_workers > 0
        assert len(report.category_breakdown) > 0
        assert len(report.recommended_actions) > 0

        # Worker analytics
        top = analytics.top_workers(n=3)
        assert len(top) > 0

        # Value analysis
        value = analytics.value_analysis()
        assert value["total_spent"] > 0

        # Correlation
        corr = analytics.bounty_quality_correlation()
        assert corr["sample_size"] > 0

        # Trends
        trends = analytics.get_all_trends()
        assert len(trends) > 0

    def test_incremental_ingestion(self):
        """Events can be ingested incrementally."""
        analytics = WorkforceAnalytics()

        # First batch
        batch1 = _make_events(n=20)
        analytics.ingest_batch(batch1)
        report1 = analytics.generate_report()

        # Second batch
        batch2 = _make_events(n=20)
        analytics.ingest_batch(batch2)
        report2 = analytics.generate_report()

        assert report2.total_tasks == report1.total_tasks + 20

    def test_single_worker_scenario(self):
        """System with only one worker should generate warnings."""
        analytics = WorkforceAnalytics()
        events = [
            TaskEvent(
                task_id=f"t{i}",
                worker_id="only_worker",
                category="delivery",
                outcome="completed",
                quality_score=0.8,
                bounty_usd=10.0,
                completion_hours=4.0,
                timestamp=1700000000 + i * 3600,
            )
            for i in range(15)
        ]
        analytics.ingest_batch(events)
        report = analytics.generate_report()

        # Should flag worker concentration
        assert report.total_workers == 1
        assert any("worker" in a.message.lower() for a in report.alerts)
