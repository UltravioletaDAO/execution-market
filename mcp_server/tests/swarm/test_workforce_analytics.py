"""
WorkforceAnalytics Test Suite
=============================

Comprehensive tests for the aggregated intelligence dashboard.

Coverage:
- Data types (MetricSeries, WorkerProfile, CategoryBreakdown, etc.)
- Event ingestion (single + batch)
- Report generation (overview, rates, trends, breakdowns)
- Worker profiles (MVP detection, at-risk detection, specialization)
- Category breakdown (completion rate, value per dollar)
- Alert system (thresholds, severity, worker concentration)
- Recommendations engine
- Value analysis (waste rate, ROI)
- Bounty-quality correlation
- Trend analysis (improving, declining, stable)
- Serialization and stats
"""

import time
import pytest

from mcp_server.swarm.workforce_analytics import (
    TrendDirection,
    AlertSeverity,
    MetricSeries,
    WorkerProfile,
    CategoryBreakdown,
    AnalyticsAlert,
    AnalyticsReport,
    TaskEvent,
    WorkforceAnalytics,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def analytics():
    return WorkforceAnalytics()


@pytest.fixture
def sample_events():
    """Diverse set of events from multiple workers and categories."""
    now = time.time()
    events = []
    # 10 completed tasks from 3 workers across 2 categories
    for i in range(10):
        events.append(
            TaskEvent(
                task_id=f"task_{i}",
                category="delivery" if i % 2 == 0 else "verification",
                worker_id=f"worker_{i % 3}",
                outcome="completed",
                quality_score=0.7 + (i % 4) * 0.05,
                bounty_usd=3.0 + i * 0.5,
                completion_hours=2.0 + i * 0.3,
                timestamp=now - (10 - i) * 3600,
            )
        )
    # 3 expired tasks
    for i in range(3):
        events.append(
            TaskEvent(
                task_id=f"expired_{i}",
                category="delivery",
                worker_id=f"worker_{i % 3}",
                outcome="expired",
                bounty_usd=5.0,
                timestamp=now - i * 3600,
            )
        )
    return events


@pytest.fixture
def populated_analytics(analytics, sample_events):
    analytics.ingest_batch(sample_events)
    return analytics


# ──────────────────────────────────────────────────────────────
# Section 1: Data Types (15 tests)
# ──────────────────────────────────────────────────────────────


class TestMetricSeries:
    """MetricSeries properties and trend detection."""

    def test_empty_series(self):
        s = MetricSeries(name="test")
        assert s.latest is None
        assert s.average == 0.0
        assert s.min_value == 0.0
        assert s.max_value == 0.0
        assert s.trend == TrendDirection.INSUFFICIENT_DATA

    def test_add_points(self):
        s = MetricSeries(name="test")
        s.add(1.0, "first")
        s.add(2.0, "second")
        assert s.latest == 2.0
        assert s.average == 1.5
        assert len(s.points) == 2

    def test_min_max(self):
        s = MetricSeries(name="test")
        for v in [3.0, 1.0, 5.0, 2.0]:
            s.add(v)
        assert s.min_value == 1.0
        assert s.max_value == 5.0

    def test_trend_improving(self):
        s = MetricSeries(name="test")
        # Low values first, high values last
        for v in [0.5, 0.5, 0.5, 0.8, 0.9, 0.95]:
            s.add(v)
        assert s.trend == TrendDirection.IMPROVING

    def test_trend_declining(self):
        s = MetricSeries(name="test")
        for v in [0.9, 0.9, 0.9, 0.5, 0.4, 0.3]:
            s.add(v)
        assert s.trend == TrendDirection.DECLINING

    def test_trend_stable(self):
        s = MetricSeries(name="test")
        for v in [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]:
            s.add(v)
        assert s.trend == TrendDirection.STABLE

    def test_trend_insufficient_data(self):
        s = MetricSeries(name="test")
        s.add(1.0)
        s.add(2.0)
        assert s.trend == TrendDirection.INSUFFICIENT_DATA


class TestWorkerProfile:
    """WorkerProfile computed properties."""

    def test_completion_rate(self):
        w = WorkerProfile(worker_id="w1", tasks_completed=8, tasks_total=10)
        assert abs(w.completion_rate - 0.8) < 0.001

    def test_completion_rate_zero(self):
        w = WorkerProfile(worker_id="w1", tasks_total=0)
        assert w.completion_rate == 0.0

    def test_is_mvp(self):
        w = WorkerProfile(
            worker_id="w1", tasks_completed=10, tasks_total=12, avg_quality=0.85
        )
        assert w.is_mvp is True

    def test_not_mvp_low_quality(self):
        w = WorkerProfile(
            worker_id="w1", tasks_completed=10, tasks_total=12, avg_quality=0.5
        )
        assert w.is_mvp is False

    def test_not_mvp_low_volume(self):
        w = WorkerProfile(
            worker_id="w1", tasks_completed=2, tasks_total=2, avg_quality=0.9
        )
        assert w.is_mvp is False

    def test_is_at_risk(self):
        w = WorkerProfile(worker_id="w1", tasks_completed=1, tasks_total=5)
        assert w.is_at_risk is True

    def test_not_at_risk_few_tasks(self):
        w = WorkerProfile(worker_id="w1", tasks_completed=0, tasks_total=2)
        assert w.is_at_risk is False  # < 3 tasks = not enough data

    def test_specialization_dominant(self):
        w = WorkerProfile(worker_id="w1", categories=["delivery"] * 8 + ["photo"] * 2)
        assert w.specialization == "delivery"

    def test_specialization_generalist(self):
        w = WorkerProfile(
            worker_id="w1", categories=["delivery", "photo", "verification", "data"]
        )
        assert w.specialization == "generalist"

    def test_specialization_empty(self):
        w = WorkerProfile(worker_id="w1")
        assert w.specialization == "generalist"


class TestCategoryBreakdown:
    """CategoryBreakdown computed properties."""

    def test_completion_rate(self):
        c = CategoryBreakdown(name="delivery", task_count=10, completed=8)
        assert abs(c.completion_rate - 0.8) < 0.001

    def test_value_per_dollar(self):
        c = CategoryBreakdown(name="delivery", avg_quality=0.8, avg_bounty_usd=4.0)
        assert abs(c.value_per_dollar - 0.2) < 0.001

    def test_value_per_dollar_zero_bounty(self):
        c = CategoryBreakdown(name="delivery", avg_quality=0.8, avg_bounty_usd=0.0)
        assert c.value_per_dollar == 0.0


class TestTaskEvent:
    """TaskEvent properties."""

    def test_is_success(self):
        e = TaskEvent(task_id="t1", outcome="completed")
        assert e.is_success is True

    def test_is_not_success(self):
        e = TaskEvent(task_id="t1", outcome="expired")
        assert e.is_success is False


class TestAnalyticsReport:
    """Report health score."""

    def test_health_score_good(self):
        r = AnalyticsReport(
            completion_rate=0.9,
            avg_quality=0.85,
            total_workers=15,
        )
        assert r.health_score > 60

    def test_health_score_bad(self):
        r = AnalyticsReport(
            completion_rate=0.1,
            avg_quality=0.2,
            total_workers=1,
            alerts=[AnalyticsAlert(severity=AlertSeverity.CRITICAL, message="bad")],
        )
        assert r.health_score < 30


# ──────────────────────────────────────────────────────────────
# Section 2: Event Ingestion (5 tests)
# ──────────────────────────────────────────────────────────────


class TestIngestion:
    """Event recording into analytics."""

    def test_ingest_single(self, analytics):
        analytics.ingest(
            TaskEvent(task_id="t1", outcome="completed", quality_score=0.8)
        )
        assert len(analytics._events) == 1

    def test_ingest_batch(self, analytics, sample_events):
        analytics.ingest_batch(sample_events)
        assert len(analytics._events) == 13  # 10 completed + 3 expired

    def test_series_created(self, analytics):
        analytics.ingest(
            TaskEvent(task_id="t1", outcome="completed", quality_score=0.8)
        )
        assert "completion_rate" in analytics._series
        assert "quality" in analytics._series
        assert "volume" in analytics._series

    def test_series_updated(self, analytics):
        for i in range(5):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    outcome="completed",
                    quality_score=0.7,
                )
            )
        q = analytics.get_series("quality")
        assert q is not None
        assert len(q.points) == 5

    def test_series_nonexistent(self, analytics):
        assert analytics.get_series("nonexistent") is None


# ──────────────────────────────────────────────────────────────
# Section 3: Report Generation (10 tests)
# ──────────────────────────────────────────────────────────────


class TestReportGeneration:
    """Comprehensive report from ingested events."""

    def test_empty_report(self, analytics):
        r = analytics.generate_report()
        assert r.total_tasks == 0
        assert r.data_points == 0

    def test_report_overview(self, populated_analytics):
        r = populated_analytics.generate_report()
        assert r.total_tasks == 13
        assert r.total_completed == 10
        assert r.total_expired == 3
        assert r.total_workers == 3

    def test_report_rates(self, populated_analytics):
        r = populated_analytics.generate_report()
        assert abs(r.completion_rate - 10 / 13) < 0.01
        assert r.avg_quality > 0
        assert r.avg_speed_hours > 0

    def test_report_total_spent(self, populated_analytics):
        r = populated_analytics.generate_report()
        assert r.total_spent_usd > 0  # Sum of bounties for completed tasks

    def test_report_trends(self, populated_analytics):
        r = populated_analytics.generate_report()
        assert isinstance(r.trends, dict)
        for name, direction in r.trends.items():
            assert isinstance(direction, TrendDirection)

    def test_report_categories(self, populated_analytics):
        r = populated_analytics.generate_report()
        assert len(r.category_breakdown) >= 2  # delivery + verification
        # Sorted by task count
        counts = [c.task_count for c in r.category_breakdown]
        assert counts == sorted(counts, reverse=True)

    def test_report_best_worst_category(self, populated_analytics):
        r = populated_analytics.generate_report()
        assert r.best_category != ""
        assert r.worst_category != ""

    def test_report_mvp_workers(self, analytics):
        """Inject high-volume high-quality worker."""
        for i in range(10):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="mvp_worker",
                    outcome="completed",
                    quality_score=0.9,
                    bounty_usd=5.0,
                    completion_hours=2.0,
                )
            )
        r = analytics.generate_report()
        assert "mvp_worker" in r.mvp_workers

    def test_report_at_risk_workers(self, analytics):
        """Worker with mostly failures."""
        for i in range(5):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="bad_worker",
                    outcome="expired" if i < 4 else "completed",
                    quality_score=0.3,
                )
            )
        r = analytics.generate_report()
        assert "bad_worker" in r.at_risk_workers

    def test_report_recommendations(self, populated_analytics):
        r = populated_analytics.generate_report()
        assert len(r.recommended_actions) > 0


# ──────────────────────────────────────────────────────────────
# Section 4: Alert System (8 tests)
# ──────────────────────────────────────────────────────────────


class TestAlerts:
    """Alert generation from thresholds."""

    def test_low_completion_alert(self, analytics):
        for i in range(10):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="w1",
                    outcome="expired" if i < 8 else "completed",
                    quality_score=0.7,
                    bounty_usd=5.0,
                )
            )
        r = analytics.generate_report()
        completion_alerts = [a for a in r.alerts if a.metric == "completion_rate"]
        assert len(completion_alerts) >= 1

    def test_low_quality_alert(self, analytics):
        for i in range(5):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="w1",
                    outcome="completed",
                    quality_score=0.3,
                    bounty_usd=5.0,
                )
            )
        r = analytics.generate_report()
        quality_alerts = [a for a in r.alerts if a.metric == "avg_quality"]
        assert len(quality_alerts) >= 1

    def test_slow_completion_alert(self):
        a = WorkforceAnalytics(
            alert_thresholds={
                "max_avg_hours": 10.0,
                "min_completion_rate": 0.0,
                "min_quality": 0.0,
                "min_workers": 0,
            }
        )
        for i in range(5):
            a.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="w1",
                    outcome="completed",
                    quality_score=0.8,
                    completion_hours=20.0,
                    bounty_usd=5.0,
                )
            )
        r = a.generate_report()
        speed_alerts = [a for a in r.alerts if a.metric == "avg_speed_hours"]
        assert len(speed_alerts) >= 1

    def test_low_worker_count_alert(self, analytics):
        analytics.ingest(
            TaskEvent(
                task_id="t1",
                worker_id="only_worker",
                outcome="completed",
                quality_score=0.8,
            )
        )
        r = analytics.generate_report()
        worker_alerts = [a for a in r.alerts if a.metric == "worker_count"]
        assert len(worker_alerts) >= 1

    def test_worker_concentration_alert(self, analytics):
        # One worker does 80% of tasks
        for i in range(8):
            analytics.ingest(
                TaskEvent(
                    task_id=f"dom_{i}",
                    worker_id="dominant",
                    outcome="completed",
                    quality_score=0.8,
                )
            )
        for i in range(2):
            analytics.ingest(
                TaskEvent(
                    task_id=f"other_{i}",
                    worker_id=f"other_{i}",
                    outcome="completed",
                    quality_score=0.8,
                )
            )
        r = analytics.generate_report()
        conc_alerts = [a for a in r.alerts if a.metric == "concentration"]
        assert len(conc_alerts) >= 1

    def test_at_risk_worker_alert(self, analytics):
        for i in range(5):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="struggling",
                    outcome="expired" if i < 4 else "completed",
                )
            )
        r = analytics.generate_report()
        risk_alerts = [a for a in r.alerts if a.metric == "worker_completion_rate"]
        assert len(risk_alerts) >= 1

    def test_critical_completion_rate(self, analytics):
        """Very low completion rate → CRITICAL severity."""
        for i in range(10):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="w1",
                    outcome="expired" if i < 9 else "completed",
                    quality_score=0.5,
                )
            )
        r = analytics.generate_report()
        critical = [
            a
            for a in r.alerts
            if a.metric == "completion_rate" and a.severity == AlertSeverity.CRITICAL
        ]
        assert len(critical) >= 1

    def test_custom_thresholds(self):
        a = WorkforceAnalytics(
            alert_thresholds={
                "min_completion_rate": 0.9,
                "min_quality": 0.0,
                "max_avg_hours": 999,
                "min_workers": 0,
                "max_concentration": 1.0,
            }
        )
        for i in range(10):
            a.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="w1",
                    outcome="completed" if i < 8 else "expired",
                    quality_score=0.9,
                )
            )
        r = a.generate_report()
        # 80% completion < 90% threshold
        comp_alerts = [al for al in r.alerts if al.metric == "completion_rate"]
        assert len(comp_alerts) >= 1


# ──────────────────────────────────────────────────────────────
# Section 5: Value Analysis (6 tests)
# ──────────────────────────────────────────────────────────────


class TestValueAnalysis:
    """ROI and waste tracking."""

    def test_empty_value(self, analytics):
        v = analytics.value_analysis()
        assert v["total_spent"] == 0
        assert v["roi"] == 0

    def test_value_with_data(self, populated_analytics):
        v = populated_analytics.value_analysis()
        assert v["total_spent"] > 0
        assert v["total_wasted"] > 0  # 3 expired tasks had bounties
        assert 0 <= v["waste_rate"] <= 1.0

    def test_waste_rate(self, analytics):
        # 5 completed, 5 expired
        for i in range(10):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="w1",
                    outcome="completed" if i < 5 else "expired",
                    quality_score=0.8,
                    bounty_usd=10.0,
                )
            )
        v = analytics.value_analysis()
        assert abs(v["waste_rate"] - 0.5) < 0.01

    def test_quality_adjusted_value(self, analytics):
        analytics.ingest(
            TaskEvent(
                task_id="t1",
                worker_id="w1",
                outcome="completed",
                quality_score=0.9,
                bounty_usd=10.0,
            )
        )
        v = analytics.value_analysis()
        assert abs(v["quality_adjusted_value"] - 9.0) < 0.01  # 10 * 0.9

    def test_avg_cost_per_completion(self, analytics):
        for i in range(4):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="w1",
                    outcome="completed",
                    quality_score=0.8,
                    bounty_usd=5.0,
                )
            )
        analytics.ingest(
            TaskEvent(
                task_id="exp",
                worker_id="w1",
                outcome="expired",
                bounty_usd=5.0,
            )
        )
        v = analytics.value_analysis()
        # 4 completions cost $20 (5*4), total was $25
        assert abs(v["avg_cost_per_completion"] - 5.0) < 0.01

    def test_roi_calculation(self, analytics):
        analytics.ingest(
            TaskEvent(
                task_id="t1",
                worker_id="w1",
                outcome="completed",
                quality_score=1.0,
                bounty_usd=10.0,
            )
        )
        v = analytics.value_analysis()
        # quality_adjusted_value = 10 * 1.0 = 10, total_spent = 10
        # ROI = 10/10 = 1.0
        assert abs(v["roi"] - 1.0) < 0.01


# ──────────────────────────────────────────────────────────────
# Section 6: Bounty-Quality Correlation (5 tests)
# ──────────────────────────────────────────────────────────────


class TestCorrelation:
    """Bounty-quality relationship analysis."""

    def test_insufficient_data(self, analytics):
        analytics.ingest(
            TaskEvent(
                task_id="t1", outcome="completed", quality_score=0.8, bounty_usd=5.0
            )
        )
        c = analytics.bounty_quality_correlation()
        assert c["insight"] == "Insufficient data"

    def test_positive_correlation(self, analytics):
        # Higher bounty → higher quality
        pairs = [(1.0, 0.3), (2.0, 0.5), (5.0, 0.7), (10.0, 0.9), (20.0, 0.95)]
        for bounty, quality in pairs:
            analytics.ingest(
                TaskEvent(
                    task_id=f"t_{bounty}",
                    worker_id="w1",
                    outcome="completed",
                    quality_score=quality,
                    bounty_usd=bounty,
                )
            )
        c = analytics.bounty_quality_correlation()
        assert c["correlation"] > 0.3
        assert "higher bounties correlate" in c["insight"].lower()

    def test_no_correlation(self, analytics):
        """Same quality regardless of bounty."""
        for bounty in [1.0, 5.0, 10.0, 20.0, 50.0]:
            analytics.ingest(
                TaskEvent(
                    task_id=f"t_{bounty}",
                    worker_id="w1",
                    outcome="completed",
                    quality_score=0.7,
                    bounty_usd=bounty,
                )
            )
        c = analytics.bounty_quality_correlation()
        # All same quality → correlation near 0
        assert abs(c["correlation"]) < 0.3

    def test_correlation_averages(self, analytics):
        for bounty, quality in [(5.0, 0.6), (10.0, 0.8), (15.0, 0.9)]:
            analytics.ingest(
                TaskEvent(
                    task_id=f"t_{bounty}",
                    worker_id="w1",
                    outcome="completed",
                    quality_score=quality,
                    bounty_usd=bounty,
                )
            )
        c = analytics.bounty_quality_correlation()
        assert c["avg_bounty"] == 10.0
        assert abs(c["avg_quality"] - (0.6 + 0.8 + 0.9) / 3) < 0.01

    def test_sample_size(self, analytics):
        for i in range(7):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="w1",
                    outcome="completed",
                    quality_score=0.7,
                    bounty_usd=5.0,
                )
            )
        c = analytics.bounty_quality_correlation()
        assert c["sample_size"] == 7


# ──────────────────────────────────────────────────────────────
# Section 7: Worker & Category Analytics (6 tests)
# ──────────────────────────────────────────────────────────────


class TestWorkerCategoryAnalytics:
    """Top workers, worker detail, category comparison."""

    def test_top_workers(self, populated_analytics):
        top = populated_analytics.top_workers(n=3)
        assert len(top) <= 3
        # Sorted by completion count
        counts = [w.tasks_completed for w in top]
        assert counts == sorted(counts, reverse=True)

    def test_worker_detail(self, populated_analytics):
        detail = populated_analytics.worker_detail("worker_0")
        assert detail is not None
        assert detail.worker_id == "worker_0"
        assert detail.tasks_total > 0

    def test_worker_detail_missing(self, populated_analytics):
        assert populated_analytics.worker_detail("nonexistent") is None

    def test_category_comparison(self, populated_analytics):
        cats = populated_analytics.category_comparison()
        assert len(cats) >= 2  # delivery + verification
        # Sorted by task count
        counts = [c.task_count for c in cats]
        assert counts == sorted(counts, reverse=True)

    def test_category_quality(self, analytics):
        for i in range(5):
            analytics.ingest(
                TaskEvent(
                    task_id=f"d{i}",
                    category="delivery",
                    worker_id="w1",
                    outcome="completed",
                    quality_score=0.9,
                    bounty_usd=5.0,
                    completion_hours=2.0,
                )
            )
        cats = analytics.category_comparison()
        delivery = next(c for c in cats if c.name == "delivery")
        assert abs(delivery.avg_quality - 0.9) < 0.01
        assert delivery.completed == 5

    def test_category_worker_count(self, populated_analytics):
        cats = populated_analytics.category_comparison()
        for cat in cats:
            assert cat.worker_count > 0


# ──────────────────────────────────────────────────────────────
# Section 8: Recommendations (4 tests)
# ──────────────────────────────────────────────────────────────


class TestRecommendations:
    """Action recommendations engine."""

    def test_recruit_recommendation(self, analytics):
        analytics.ingest(
            TaskEvent(
                task_id="t1",
                worker_id="only",
                outcome="completed",
                quality_score=0.8,
            )
        )
        r = analytics.generate_report()
        has_recruit = any("recruit" in rec.lower() for rec in r.recommended_actions)
        assert has_recruit

    def test_mvp_retention_recommendation(self, analytics):
        for i in range(10):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id="star",
                    outcome="completed",
                    quality_score=0.9,
                )
            )
        # Need 3+ workers to avoid worker count alert dominating
        for i in range(3):
            analytics.ingest(
                TaskEvent(
                    task_id=f"x{i}",
                    worker_id=f"other_{i}",
                    outcome="completed",
                    quality_score=0.8,
                )
            )
        r = analytics.generate_report()
        has_retain = any(
            "retain" in rec.lower() or "mvp" in rec.lower()
            for rec in r.recommended_actions
        )
        assert has_retain

    def test_healthy_system_recommendation(self, analytics):
        """Good system gets 'normal parameters' message."""
        for i in range(20):
            analytics.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id=f"w_{i % 5}",
                    outcome="completed",
                    quality_score=0.9,
                    bounty_usd=5.0,
                    completion_hours=2.0,
                )
            )
        r = analytics.generate_report()
        has_normal = any("normal" in rec.lower() for rec in r.recommended_actions)
        assert has_normal

    def test_speed_recommendation(self):
        a = WorkforceAnalytics(
            alert_thresholds={
                "min_completion_rate": 0.0,
                "min_quality": 0.0,
                "max_avg_hours": 999,
                "min_workers": 0,
                "max_concentration": 1.0,
            }
        )
        for i in range(5):
            a.ingest(
                TaskEvent(
                    task_id=f"t{i}",
                    worker_id=f"w{i}",
                    outcome="completed",
                    quality_score=0.9,
                    completion_hours=30.0,
                    bounty_usd=5.0,
                )
            )
        r = a.generate_report()
        has_speed = any(
            "speed" in rec.lower() or "completion" in rec.lower()
            for rec in r.recommended_actions
        )
        assert has_speed


# ──────────────────────────────────────────────────────────────
# Section 9: Serialization & Stats (5 tests)
# ──────────────────────────────────────────────────────────────


class TestSerialization:
    """to_dict and stats methods."""

    def test_to_dict_empty(self, analytics):
        d = analytics.to_dict()
        assert d["event_count"] == 0
        assert isinstance(d["series"], dict)

    def test_to_dict_with_data(self, populated_analytics):
        d = populated_analytics.to_dict()
        assert d["event_count"] == 13
        assert "completion_rate" in d["series"]
        assert d["series"]["completion_rate"]["trend"] in [
            t.value for t in TrendDirection
        ]

    def test_stats_empty(self, analytics):
        s = analytics.stats()
        assert s["events_ingested"] == 0
        assert s["unique_workers"] == 0

    def test_stats_with_data(self, populated_analytics):
        s = populated_analytics.stats()
        assert s["events_ingested"] == 13
        assert s["unique_workers"] == 3
        assert s["unique_categories"] == 2
        assert s["series_tracked"] >= 3

    def test_all_trends(self, populated_analytics):
        trends = populated_analytics.get_all_trends()
        assert isinstance(trends, dict)
        for name, direction in trends.items():
            assert isinstance(direction, TrendDirection)
