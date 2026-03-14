"""
Tests for SwarmAnalytics engine.

Covers: event recording, time-window filtering, agent performance,
pipeline metrics, financial metrics, health metrics, trend detection,
category/chain breakdown, recommendations, full reports, and
production data loading.
"""

import pytest
from datetime import datetime, timezone, timedelta
from mcp_server.swarm.analytics import (
    SwarmAnalytics,
    TaskEvent,
    TimeWindow,
    AgentMetrics,
    PipelineMetrics,
    FinancialMetrics,
    HealthMetrics,
    TrendAnalysis,
    SwarmRecommendation,
    load_from_production_tasks,
    _parse_datetime,
    WINDOW_SECONDS,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

NOW = datetime(2026, 3, 14, 3, 0, 0, tzinfo=timezone.utc)


def make_event(
    task_id="t1",
    event_type="created",
    agent_id=None,
    agent_name=None,
    category="photo",
    bounty_usd=0.10,
    chain="base",
    token="USDC",
    timestamp=None,
    duration_seconds=None,
    quality_score=None,
    evidence_types=None,
    error=None,
):
    return TaskEvent(
        task_id=task_id,
        event_type=event_type,
        agent_id=agent_id,
        agent_name=agent_name,
        category=category,
        bounty_usd=bounty_usd,
        chain=chain,
        token=token,
        timestamp=timestamp or NOW,
        duration_seconds=duration_seconds,
        quality_score=quality_score,
        evidence_types=evidence_types or [],
        error=error,
    )


def populated_analytics():
    """Create analytics with a realistic set of events."""
    analytics = SwarmAnalytics()

    # Task 1: Created → Assigned → Completed
    analytics.record_event(make_event("t1", "created", bounty_usd=0.10, chain="base"))
    analytics.record_event(make_event("t1", "assigned", agent_id=1, agent_name="aurora"))
    analytics.record_event(make_event(
        "t1", "completed", agent_id=1, agent_name="aurora",
        bounty_usd=0.10, chain="base", duration_seconds=120, quality_score=0.9,
    ))

    # Task 2: Created → Assigned → Completed (different agent, chain)
    analytics.record_event(make_event("t2", "created", bounty_usd=0.20, chain="polygon", category="delivery"))
    analytics.record_event(make_event("t2", "assigned", agent_id=2, agent_name="blaze"))
    analytics.record_event(make_event(
        "t2", "completed", agent_id=2, agent_name="blaze",
        bounty_usd=0.20, chain="polygon", category="delivery",
        duration_seconds=300, quality_score=0.85,
    ))

    # Task 3: Created → Assigned → Failed
    analytics.record_event(make_event("t3", "created", bounty_usd=0.15, chain="arbitrum"))
    analytics.record_event(make_event("t3", "assigned", agent_id=1, agent_name="aurora"))
    analytics.record_event(make_event(
        "t3", "failed", agent_id=1, agent_name="aurora",
        chain="arbitrum", error="timeout",
    ))

    # Task 4: Created → Expired
    analytics.record_event(make_event("t4", "created", bounty_usd=0.10, chain="celo"))
    analytics.record_event(make_event("t4", "expired", chain="celo"))

    # Task 5: Created → Cancelled
    analytics.record_event(make_event("t5", "created", bounty_usd=0.05, chain="base"))
    analytics.record_event(make_event("t5", "cancelled", chain="base"))

    return analytics


# ─── Event Recording ─────────────────────────────────────────────────────────


class TestEventRecording:
    def test_record_single_event(self):
        a = SwarmAnalytics()
        e = make_event()
        a.record_event(e)
        assert a.event_count == 1

    def test_record_multiple_events(self):
        a = SwarmAnalytics()
        events = [make_event(task_id=f"t{i}") for i in range(10)]
        a.record_events(events)
        assert a.event_count == 10

    def test_clear_events(self):
        a = SwarmAnalytics()
        a.record_events([make_event() for _ in range(5)])
        a.clear()
        assert a.event_count == 0

    def test_event_default_timestamp(self):
        e = TaskEvent(task_id="x", event_type="created")
        assert e.timestamp is not None

    def test_event_preserves_fields(self):
        e = make_event(
            task_id="abc", event_type="completed",
            agent_id=42, agent_name="test", category="delivery",
            bounty_usd=1.5, chain="ethereum", token="EURC",
            duration_seconds=99, quality_score=0.77,
            evidence_types=["photo", "text_response"], error=None,
        )
        assert e.task_id == "abc"
        assert e.agent_id == 42
        assert e.bounty_usd == 1.5
        assert e.quality_score == 0.77
        assert len(e.evidence_types) == 2


# ─── Time Window Filtering ───────────────────────────────────────────────────


class TestTimeWindows:
    def test_all_time_returns_everything(self):
        a = SwarmAnalytics()
        old = make_event(timestamp=NOW - timedelta(days=365))
        new = make_event(timestamp=NOW)
        a.record_events([old, new])
        filtered = a._filter_by_window(a._events, TimeWindow.ALL_TIME)
        assert len(filtered) == 2

    def test_hour_window(self):
        a = SwarmAnalytics()
        recent = make_event(timestamp=NOW - timedelta(minutes=30))
        old = make_event(timestamp=NOW - timedelta(hours=2))
        a.record_events([recent, old])
        filtered = a._filter_by_window(a._events, TimeWindow.HOUR, reference_time=NOW)
        assert len(filtered) == 1

    def test_day_window(self):
        a = SwarmAnalytics()
        today = make_event(timestamp=NOW - timedelta(hours=12))
        yesterday = make_event(timestamp=NOW - timedelta(hours=36))
        a.record_events([today, yesterday])
        filtered = a._filter_by_window(a._events, TimeWindow.DAY, reference_time=NOW)
        assert len(filtered) == 1

    def test_week_window(self):
        a = SwarmAnalytics()
        this_week = make_event(timestamp=NOW - timedelta(days=3))
        last_month = make_event(timestamp=NOW - timedelta(days=15))
        a.record_events([this_week, last_month])
        filtered = a._filter_by_window(a._events, TimeWindow.WEEK, reference_time=NOW)
        assert len(filtered) == 1

    def test_events_by_type(self):
        a = populated_analytics()
        created = a._events_by_type("created")
        completed = a._events_by_type("completed")
        assert len(created) == 5
        assert len(completed) == 2


# ─── Agent Performance ───────────────────────────────────────────────────────


class TestAgentPerformance:
    def test_single_agent_metrics(self):
        a = populated_analytics()
        m = a.agent_performance(agent_id=1)
        assert isinstance(m, AgentMetrics)
        assert m.agent_id == 1
        assert m.agent_name == "aurora"
        assert m.tasks_assigned == 2
        assert m.tasks_completed == 1
        assert m.tasks_failed == 1
        assert m.total_earnings_usd == 0.10

    def test_agent_success_rate(self):
        a = populated_analytics()
        m = a.agent_performance(agent_id=1)
        assert m.success_rate == 0.5  # 1 completed, 1 failed

    def test_agent_avg_earnings(self):
        a = populated_analytics()
        m = a.agent_performance(agent_id=2)
        assert m.avg_earnings_per_task == 0.20

    def test_agent_completion_time(self):
        a = populated_analytics()
        m = a.agent_performance(agent_id=2)
        assert m.avg_completion_time_s == 300.0

    def test_agent_quality(self):
        a = populated_analytics()
        m = a.agent_performance(agent_id=2)
        assert m.avg_quality == 0.85

    def test_agent_primary_category(self):
        a = populated_analytics()
        m = a.agent_performance(agent_id=2)
        assert m.primary_category == "delivery"

    def test_all_agents_sorted_by_earnings(self):
        a = populated_analytics()
        agents = a.agent_performance()
        assert isinstance(agents, list)
        assert len(agents) == 2
        assert agents[0].agent_id == 2  # $0.20 > $0.10

    def test_unknown_agent_returns_empty(self):
        a = populated_analytics()
        m = a.agent_performance(agent_id=999)
        assert m.tasks_assigned == 0
        assert m.tasks_completed == 0

    def test_agent_streak_tracking(self):
        a = SwarmAnalytics()
        for i in range(5):
            a.record_event(make_event(f"s{i}", "completed", agent_id=1, agent_name="a"))
        a.record_event(make_event("s5", "failed", agent_id=1, agent_name="a"))
        a.record_event(make_event("s6", "completed", agent_id=1, agent_name="a"))

        m = a.agent_performance(agent_id=1)
        assert m.best_streak == 5
        assert m.active_streak == 1  # Reset after failure

    def test_agent_chain_tracking(self):
        a = SwarmAnalytics()
        a.record_event(make_event("c1", "completed", agent_id=1, chain="base"))
        a.record_event(make_event("c2", "completed", agent_id=1, chain="base"))
        a.record_event(make_event("c3", "completed", agent_id=1, chain="polygon"))
        m = a.agent_performance(agent_id=1)
        assert m.chains["base"] == 2
        assert m.chains["polygon"] == 1

    def test_agent_to_dict(self):
        a = populated_analytics()
        m = a.agent_performance(agent_id=1)
        d = m.to_dict()
        assert "agent_id" in d
        assert "success_rate" in d
        assert "total_earnings_usd" in d
        assert "active_streak" in d

    def test_fastest_slowest_completion(self):
        a = SwarmAnalytics()
        a.record_event(make_event("f1", "completed", agent_id=1, duration_seconds=50))
        a.record_event(make_event("f2", "completed", agent_id=1, duration_seconds=200))
        a.record_event(make_event("f3", "completed", agent_id=1, duration_seconds=100))
        m = a.agent_performance(agent_id=1)
        assert m.fastest_completion_s == 50
        assert m.slowest_completion_s == 200


# ─── Pipeline Metrics ────────────────────────────────────────────────────────


class TestPipelineMetrics:
    def test_basic_pipeline(self):
        a = populated_analytics()
        p = a.pipeline_metrics()
        assert p.created == 5
        assert p.assigned == 3
        assert p.completed == 2
        assert p.failed == 1
        assert p.expired == 1
        assert p.cancelled == 1

    def test_assignment_rate(self):
        a = populated_analytics()
        p = a.pipeline_metrics()
        assert p.assignment_rate == 3 / 5  # 3 assigned out of 5 created

    def test_completion_rate(self):
        a = populated_analytics()
        p = a.pipeline_metrics()
        assert abs(p.completion_rate - 2 / 3) < 0.001

    def test_failure_rate(self):
        a = populated_analytics()
        p = a.pipeline_metrics()
        assert abs(p.failure_rate - 1 / 3) < 0.001

    def test_expiry_rate(self):
        a = populated_analytics()
        p = a.pipeline_metrics()
        assert p.expiry_rate == 1 / 5

    def test_overall_throughput(self):
        a = populated_analytics()
        p = a.pipeline_metrics()
        assert p.overall_throughput == 2 / 5

    def test_empty_pipeline(self):
        a = SwarmAnalytics()
        p = a.pipeline_metrics()
        assert p.assignment_rate == 0.0
        assert p.completion_rate == 0.0
        assert p.overall_throughput == 0.0

    def test_pipeline_to_dict(self):
        a = populated_analytics()
        d = a.pipeline_metrics().to_dict()
        assert "created" in d
        assert "assignment_rate" in d
        assert "overall_throughput" in d


# ─── Financial Metrics ────────────────────────────────────────────────────────


class TestFinancialMetrics:
    def test_total_bounty(self):
        a = populated_analytics()
        f = a.financial_metrics()
        assert abs(f.total_bounty_usd - 0.30) < 0.001  # $0.10 + $0.20

    def test_platform_fees(self):
        a = populated_analytics()
        f = a.financial_metrics()
        expected_fees = 0.30 * 0.13
        assert abs(f.platform_fees_usd - expected_fees) < 0.001

    def test_avg_bounty(self):
        a = populated_analytics()
        f = a.financial_metrics()
        assert abs(f.avg_bounty_usd - 0.15) < 0.001

    def test_median_bounty(self):
        a = populated_analytics()
        f = a.financial_metrics()
        f.compute_stats()
        assert abs(f.median_bounty_usd - 0.15) < 0.001  # median of [0.10, 0.20]

    def test_by_chain_breakdown(self):
        a = populated_analytics()
        f = a.financial_metrics()
        assert "base" in f.by_chain
        assert "polygon" in f.by_chain
        assert abs(f.by_chain["base"] - 0.10) < 0.001

    def test_by_token_breakdown(self):
        a = populated_analytics()
        f = a.financial_metrics()
        assert "USDC" in f.by_token

    def test_by_category_breakdown(self):
        a = populated_analytics()
        f = a.financial_metrics()
        assert "photo" in f.by_category
        assert "delivery" in f.by_category

    def test_empty_financial(self):
        a = SwarmAnalytics()
        f = a.financial_metrics()
        assert f.total_bounty_usd == 0.0
        assert f.avg_bounty_usd == 0.0

    def test_financial_to_dict(self):
        a = populated_analytics()
        d = a.financial_metrics().to_dict()
        assert "total_bounty_usd" in d
        assert "by_chain" in d
        assert "task_count" in d


# ─── Health Metrics ───────────────────────────────────────────────────────────


class TestHealthMetrics:
    def test_total_events(self):
        a = populated_analytics()
        h = a.health_metrics()
        assert h.total_events > 0

    def test_error_count(self):
        a = populated_analytics()
        h = a.health_metrics()
        assert h.error_count == 1  # One failed task with error

    def test_error_rate(self):
        a = populated_analytics()
        h = a.health_metrics()
        assert h.error_rate > 0

    def test_sla_compliance(self):
        a = SwarmAnalytics(sla_target_seconds=200)
        a.record_event(make_event("s1", "completed", duration_seconds=100))  # Under SLA
        a.record_event(make_event("s2", "completed", duration_seconds=300))  # Over SLA
        h = a.health_metrics()
        assert h.sla_compliant == 1
        assert h.sla_violations == 1
        assert h.sla_compliance_rate == 0.5

    def test_latency_percentiles(self):
        a = SwarmAnalytics()
        for i in range(100):
            a.record_event(make_event(
                f"p{i}", "completed", duration_seconds=float(i + 1)
            ))
        h = a.health_metrics()
        assert h.p50_latency_s == 51.0
        assert h.p90_latency_s == 91.0
        assert h.p99_latency_s == 100.0

    def test_empty_health(self):
        a = SwarmAnalytics()
        h = a.health_metrics()
        assert h.total_events == 0
        assert h.error_rate == 0.0
        assert h.sla_compliance_rate == 0.0

    def test_health_to_dict(self):
        a = populated_analytics()
        d = a.health_metrics().to_dict()
        assert "error_rate" in d
        assert "sla_compliance" in d
        assert "p90_latency_s" in d

    def test_custom_sla_target(self):
        a = SwarmAnalytics()
        a.record_event(make_event("x", "completed", duration_seconds=500))
        h = a.health_metrics(sla_target_seconds=600)
        assert h.sla_compliant == 1
        h2 = a.health_metrics(sla_target_seconds=400)
        assert h2.sla_violations == 1


# ─── Trend Detection ─────────────────────────────────────────────────────────


class TestTrendDetection:
    def test_empty_trend(self):
        a = SwarmAnalytics()
        t = a.detect_trends("completion_rate")
        assert t.data_points == 0

    def test_improving_trend(self):
        a = SwarmAnalytics()
        # Day 1: 50% completion, Day 2: 75%, Day 3: 100%
        base = NOW - timedelta(days=5)
        for day in range(3):
            ts = base + timedelta(days=day)
            # Assigned
            a.record_event(make_event(f"a{day}", "assigned", timestamp=ts))
            a.record_event(make_event(f"a{day}", "completed", timestamp=ts))
            if day == 0:  # Day 0 has a failure too
                a.record_event(make_event(f"f{day}", "assigned", timestamp=ts))
                a.record_event(make_event(f"f{day}", "failed", timestamp=ts))

        t = a.detect_trends("completion_rate", window=TimeWindow.WEEK, bucket_hours=24)
        assert t.data_points >= 2

    def test_stable_trend(self):
        a = SwarmAnalytics()
        base = NOW - timedelta(days=5)
        for day in range(5):
            ts = base + timedelta(days=day)
            a.record_event(make_event(f"s{day}", "assigned", timestamp=ts))
            a.record_event(make_event(f"s{day}", "completed", timestamp=ts))
        t = a.detect_trends("completion_rate", window=TimeWindow.WEEK, bucket_hours=24)
        # All days have 100% completion — should be stable
        assert t.direction in ("stable", "improving")

    def test_throughput_trend(self):
        a = SwarmAnalytics()
        base = NOW - timedelta(days=5)
        for day in range(5):
            ts = base + timedelta(days=day)
            for i in range(day + 1):  # Increasing throughput
                a.record_event(make_event(f"th{day}_{i}", "completed", timestamp=ts))
        t = a.detect_trends("throughput", window=TimeWindow.WEEK, bucket_hours=24)
        assert t.data_points >= 2

    def test_trend_to_dict(self):
        t = TrendAnalysis(
            metric_name="test",
            direction="improving",
            slope=0.05,
            confidence=0.8,
            data_points=5,
            current_value=0.9,
            period_avg=0.7,
            period_min=0.5,
            period_max=0.9,
            alert=None,
        )
        d = t.to_dict()
        assert d["metric"] == "test"
        assert d["direction"] == "improving"
        assert "alert" not in d

    def test_trend_with_alert(self):
        t = TrendAnalysis(
            metric_name="test",
            direction="degrading",
            confidence=0.8,
            alert="Something bad",
        )
        d = t.to_dict()
        assert "alert" in d

    def test_single_bucket_is_stable(self):
        a = SwarmAnalytics()
        a.record_event(make_event("x", "completed"))
        t = a.detect_trends("throughput", bucket_hours=24)
        assert t.direction == "stable" or t.data_points < 2


# ─── Category Breakdown ──────────────────────────────────────────────────────


class TestCategoryBreakdown:
    def test_basic_categories(self):
        a = populated_analytics()
        cats = a.category_breakdown()
        assert "photo" in cats
        assert "delivery" in cats

    def test_category_counts(self):
        a = populated_analytics()
        cats = a.category_breakdown()
        assert cats["photo"]["completed"] == 1
        assert cats["delivery"]["completed"] == 1

    def test_category_success_rate(self):
        a = populated_analytics()
        cats = a.category_breakdown()
        # photo: 1 completed, 1 failed → 50%
        assert cats["photo"]["success_rate"] == 0.5

    def test_category_quality(self):
        a = populated_analytics()
        cats = a.category_breakdown()
        assert cats["delivery"]["avg_quality"] == 0.85

    def test_empty_categories(self):
        a = SwarmAnalytics()
        cats = a.category_breakdown()
        assert len(cats) == 0


# ─── Chain Breakdown ──────────────────────────────────────────────────────────


class TestChainBreakdown:
    def test_chain_counts(self):
        a = populated_analytics()
        chains = a.chain_breakdown()
        assert "base" in chains
        assert "polygon" in chains
        assert chains["base"]["tasks"] == 1
        assert chains["polygon"]["tasks"] == 1

    def test_chain_bounties(self):
        a = populated_analytics()
        chains = a.chain_breakdown()
        assert chains["base"]["total_bounty"] == 0.10
        assert chains["polygon"]["total_bounty"] == 0.20

    def test_empty_chains(self):
        a = SwarmAnalytics()
        chains = a.chain_breakdown()
        assert len(chains) == 0


# ─── Recommendations ─────────────────────────────────────────────────────────


class TestRecommendations:
    def test_high_expiry_recommendation(self):
        a = SwarmAnalytics()
        # 10 created, 5 expired
        for i in range(10):
            a.record_event(make_event(f"e{i}", "created"))
        for i in range(5):
            a.record_event(make_event(f"e{i}", "expired"))
        recs = a.recommendations(TimeWindow.ALL_TIME)
        expiry_recs = [r for r in recs if "expiry" in r.title.lower()]
        assert len(expiry_recs) >= 1

    def test_low_completion_recommendation(self):
        a = SwarmAnalytics()
        # 10 assigned, 3 completed, 7 failed → 30% completion
        for i in range(10):
            a.record_event(make_event(f"l{i}", "assigned"))
        for i in range(3):
            a.record_event(make_event(f"l{i}", "completed"))
        for i in range(3, 10):
            a.record_event(make_event(f"l{i}", "failed"))
        recs = a.recommendations(TimeWindow.ALL_TIME)
        completion_recs = [r for r in recs if "completion" in r.title.lower()]
        assert len(completion_recs) >= 1

    def test_sla_violation_recommendation(self):
        a = SwarmAnalytics(sla_target_seconds=100)
        for i in range(5):
            a.record_event(make_event(f"s{i}", "completed", duration_seconds=200))
        recs = a.recommendations(TimeWindow.ALL_TIME)
        sla_recs = [r for r in recs if "sla" in r.title.lower()]
        assert len(sla_recs) >= 1

    def test_high_error_recommendation(self):
        a = SwarmAnalytics()
        for i in range(10):
            a.record_event(make_event(f"err{i}", "failed", error="boom"))
        recs = a.recommendations(TimeWindow.ALL_TIME)
        error_recs = [r for r in recs if "error" in r.title.lower()]
        assert len(error_recs) >= 1
        assert error_recs[0].priority == "critical"

    def test_no_recommendations_when_healthy(self):
        a = SwarmAnalytics()
        # Perfect pipeline: 10 created, 10 assigned, 10 completed, 0 expired
        for i in range(10):
            a.record_event(make_event(f"h{i}", "created", category=f"cat{i % 3}"))
            a.record_event(make_event(f"h{i}", "assigned"))
            a.record_event(make_event(f"h{i}", "completed", duration_seconds=60))
        recs = a.recommendations(TimeWindow.ALL_TIME)
        # Should have zero or only low-priority recs
        critical = [r for r in recs if r.priority in ("critical", "high")]
        assert len(critical) == 0

    def test_recommendation_sorted_by_priority(self):
        a = SwarmAnalytics(sla_target_seconds=100)
        # Create multiple issues
        for i in range(20):
            a.record_event(make_event(f"m{i}", "created"))
            a.record_event(make_event(f"m{i}", "expired"))  # High expiry
            a.record_event(make_event(f"m{i}", "failed", error="err"))  # Errors
            a.record_event(make_event(f"m{i}", "completed", duration_seconds=200))
        recs = a.recommendations(TimeWindow.ALL_TIME)
        if len(recs) >= 2:
            priorities = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for i in range(len(recs) - 1):
                assert priorities.get(recs[i].priority, 9) <= priorities.get(recs[i + 1].priority, 9)

    def test_recommendation_to_dict(self):
        r = SwarmRecommendation(
            category="scaling",
            priority="high",
            title="Test",
            description="Test desc",
            action="Do something",
            impact="Big impact",
            data={"key": "value"},
        )
        d = r.to_dict()
        assert d["category"] == "scaling"
        assert d["data"]["key"] == "value"

    def test_single_category_recommendation(self):
        a = SwarmAnalytics()
        for i in range(15):
            a.record_event(make_event(f"sc{i}", "created", category="photo"))
            a.record_event(make_event(f"sc{i}", "assigned"))
            a.record_event(make_event(f"sc{i}", "completed", category="photo"))
        recs = a.recommendations(TimeWindow.ALL_TIME)
        cat_recs = [r for r in recs if "concentration" in r.title.lower()]
        assert len(cat_recs) >= 1


# ─── Full Report ──────────────────────────────────────────────────────────────


class TestFullReport:
    def test_report_structure(self):
        a = populated_analytics()
        r = a.full_report()
        assert "pipeline" in r
        assert "financial" in r
        assert "health" in r
        assert "agents" in r
        assert "categories" in r
        assert "chains" in r
        assert "recommendations" in r
        assert "total_events" in r
        assert "window" in r

    def test_report_with_window(self):
        a = populated_analytics()
        r = a.full_report(TimeWindow.DAY)
        assert r["window"] == "day"

    def test_summary_string(self):
        a = populated_analytics()
        s = a.summary()
        assert "Pipeline" in s
        assert "Throughput" in s


# ─── Production Data Loading ─────────────────────────────────────────────────


class TestProductionDataLoading:
    def test_load_completed_task(self):
        tasks = [{
            "id": 1,
            "title": "Test task",
            "status": "completed",
            "category": "photo",
            "bounty": 0.10,
            "chain": "base",
            "token": "USDC",
            "created_at": "2026-03-13T12:00:00Z",
            "completed_at": "2026-03-13T12:05:00Z",
            "assigned_to": 2106,
            "evidence": [{"type": "photo"}, {"type": "text_response"}],
        }]
        a = load_from_production_tasks(tasks)
        assert a.event_count == 3  # created + assigned + completed

        p = a.pipeline_metrics()
        assert p.completed == 1

    def test_load_expired_task(self):
        tasks = [{"id": 2, "status": "expired", "bounty": 0.10}]
        a = load_from_production_tasks(tasks)
        p = a.pipeline_metrics()
        assert p.expired == 1

    def test_load_failed_task(self):
        tasks = [{"id": 3, "status": "failed", "error": "timeout", "assigned_to": 5}]
        a = load_from_production_tasks(tasks)
        p = a.pipeline_metrics()
        assert p.failed == 1

    def test_load_cancelled_task(self):
        tasks = [{"id": 4, "status": "cancelled"}]
        a = load_from_production_tasks(tasks)
        p = a.pipeline_metrics()
        assert p.cancelled == 1

    def test_load_multiple_tasks(self):
        tasks = [
            {"id": i, "status": "completed", "bounty": 0.10, "chain": "base", "assigned_to": 1}
            for i in range(20)
        ]
        a = load_from_production_tasks(tasks)
        assert a.event_count == 60  # 20 * 3 (created + assigned + completed)

    def test_load_into_existing_analytics(self):
        a = SwarmAnalytics()
        a.record_event(make_event("existing", "created"))
        tasks = [{"id": 1, "status": "completed", "bounty": 0.10}]
        load_from_production_tasks(tasks, analytics=a)
        assert a.event_count > 1

    def test_evidence_quality_heuristic(self):
        tasks = [{
            "id": 1,
            "status": "completed",
            "bounty": 0.10,
            "evidence": [{"type": "photo"}, {"type": "text_response"}, {"type": "receipt"}],
        }]
        a = load_from_production_tasks(tasks)
        completed = [e for e in a._events if e.event_type == "completed"]
        assert len(completed) == 1
        assert completed[0].quality_score == 0.8  # 0.5 + 3*0.1

    def test_duration_calculation(self):
        tasks = [{
            "id": 1,
            "status": "completed",
            "created_at": "2026-03-13T12:00:00Z",
            "completed_at": "2026-03-13T12:10:00Z",
        }]
        a = load_from_production_tasks(tasks)
        completed = [e for e in a._events if e.event_type == "completed"]
        assert abs(completed[0].duration_seconds - 600) < 1

    def test_missing_fields_handled(self):
        tasks = [{"id": 1}]  # Minimal task
        a = load_from_production_tasks(tasks)
        assert a.event_count >= 1  # At least created


# ─── Parse Datetime ───────────────────────────────────────────────────────────


class TestParseDatetime:
    def test_none(self):
        assert _parse_datetime(None) is None

    def test_iso_format(self):
        dt = _parse_datetime("2026-03-14T03:00:00+00:00")
        assert dt is not None
        assert dt.year == 2026

    def test_z_format(self):
        dt = _parse_datetime("2026-03-14T03:00:00Z")
        assert dt is not None

    def test_datetime_passthrough(self):
        dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert _parse_datetime(dt) is dt

    def test_invalid_string(self):
        assert _parse_datetime("not a date") is None

    def test_integer_fails_gracefully(self):
        assert _parse_datetime(12345) is None


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_large_event_volume(self):
        a = SwarmAnalytics()
        events = [make_event(f"big{i}", "completed", bounty_usd=0.01, duration_seconds=float(i))
                  for i in range(1, 1001)]
        a.record_events(events)
        assert a.event_count == 1000

        f = a.financial_metrics()
        assert abs(f.total_bounty_usd - 10.0) < 0.01

        h = a.health_metrics()
        assert h.p50_latency_s == 501.0

    def test_zero_bounty_tasks(self):
        a = SwarmAnalytics()
        a.record_event(make_event("z1", "completed", bounty_usd=0.0))
        f = a.financial_metrics()
        assert f.total_bounty_usd == 0.0
        assert f.avg_bounty_usd == 0.0

    def test_concurrent_agent_ids(self):
        a = SwarmAnalytics()
        for i in range(24):
            a.record_event(make_event(f"a{i}", "completed", agent_id=i + 1, agent_name=f"agent{i}"))
        agents = a.agent_performance()
        assert len(agents) == 24

    def test_all_event_types(self):
        a = SwarmAnalytics()
        for etype in ["created", "assigned", "completed", "failed", "expired", "cancelled"]:
            a.record_event(make_event(f"et_{etype}", etype))
        p = a.pipeline_metrics()
        assert p.created == 1
        assert p.assigned == 1
        assert p.completed == 1
        assert p.failed == 1
        assert p.expired == 1
        assert p.cancelled == 1

    def test_window_constants(self):
        assert WINDOW_SECONDS[TimeWindow.HOUR] == 3600
        assert WINDOW_SECONDS[TimeWindow.DAY] == 86400
        assert WINDOW_SECONDS[TimeWindow.WEEK] == 604800
        assert WINDOW_SECONDS[TimeWindow.ALL_TIME] == float("inf")
