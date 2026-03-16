"""
Tests for SwarmAnalytics — Metrics Aggregation & Trend Analysis
================================================================

Tests cover:
- TaskEvent creation and serialization
- AgentMetrics aggregation (success rate, quality, revenue)
- Fleet-wide dashboard generation
- Trend analysis (hourly/daily bucketing, direction detection)
- Alert generation (success rate, quality, staleness, fleet-wide)
- Category heatmap
- Persistence (save/load/corruption recovery)
- Edge cases (empty state, single event, high volume)
"""

import json
import shutil
import tempfile
import time

import pytest

from mcp_server.swarm.analytics import (
    SwarmAnalytics,
    TaskEvent,
    AgentMetrics,
    FleetSnapshot,
    Alert,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def tmpdir():
    d = tempfile.mkdtemp(prefix="swarm_analytics_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def analytics():
    return SwarmAnalytics(max_events=1000)


@pytest.fixture
def analytics_persisted(tmpdir):
    return SwarmAnalytics(storage_dir=tmpdir, max_events=1000, snapshot_interval_seconds=1)


def make_event(
    event_type="task_completed",
    agent_id="agent_001",
    task_id="task_001",
    category="physical_verification",
    bounty_usd=5.0,
    quality_rating=4.5,
    duration_seconds=3600,
    timestamp=None,
) -> TaskEvent:
    return TaskEvent(
        event_type=event_type,
        agent_id=agent_id,
        task_id=task_id,
        category=category,
        bounty_usd=bounty_usd,
        quality_rating=quality_rating,
        duration_seconds=duration_seconds,
        timestamp=timestamp or time.time(),
    )


# ──────────────────────────────────────────────────────────────
# TaskEvent Tests
# ──────────────────────────────────────────────────────────────

class TestTaskEvent:

    def test_creation(self):
        e = make_event()
        assert e.event_type == "task_completed"
        assert e.agent_id == "agent_001"
        assert e.bounty_usd == 5.0

    def test_to_dict(self):
        e = make_event()
        d = e.to_dict()
        assert isinstance(d, dict)
        assert d["event_type"] == "task_completed"
        assert d["quality_rating"] == 4.5

    def test_from_dict(self):
        e = make_event()
        d = e.to_dict()
        e2 = TaskEvent.from_dict(d)
        assert e2.agent_id == e.agent_id
        assert e2.bounty_usd == e.bounty_usd

    def test_from_dict_ignores_unknown_keys(self):
        d = {"event_type": "task_completed", "agent_id": "a1", "task_id": "t1", "extra_field": 99}
        e = TaskEvent.from_dict(d)
        assert e.agent_id == "a1"

    def test_default_timestamp(self):
        e = TaskEvent(event_type="task_completed", agent_id="a", task_id="t")
        assert e.timestamp > 0

    def test_default_metadata(self):
        e = make_event()
        assert isinstance(e.metadata, dict)


# ──────────────────────────────────────────────────────────────
# AgentMetrics Tests
# ──────────────────────────────────────────────────────────────

class TestAgentMetrics:

    def test_success_rate_zero(self):
        m = AgentMetrics(agent_id="a1")
        assert m.success_rate == 0.0

    def test_success_rate_perfect(self):
        m = AgentMetrics(agent_id="a1", tasks_completed=10, tasks_failed=0, tasks_expired=0)
        assert m.success_rate == 1.0

    def test_success_rate_mixed(self):
        m = AgentMetrics(agent_id="a1", tasks_completed=7, tasks_failed=2, tasks_expired=1)
        assert abs(m.success_rate - 0.7) < 0.01

    def test_is_active_recent(self):
        m = AgentMetrics(agent_id="a1", last_active=time.time())
        assert m.is_active is True

    def test_is_active_old(self):
        m = AgentMetrics(agent_id="a1", last_active=time.time() - 100000)
        assert m.is_active is False

    def test_is_stale(self):
        m = AgentMetrics(agent_id="a1", last_active=time.time() - 700000)
        assert m.is_stale is True

    def test_is_not_stale_when_never_active(self):
        m = AgentMetrics(agent_id="a1", last_active=0)
        assert m.is_stale is False

    def test_to_dict(self):
        m = AgentMetrics(agent_id="a1", tasks_completed=5, tasks_failed=1)
        d = m.to_dict()
        assert d["agent_id"] == "a1"
        assert "success_rate" in d
        assert "is_active" in d
        assert "is_stale" in d


# ──────────────────────────────────────────────────────────────
# SwarmAnalytics Core Tests
# ──────────────────────────────────────────────────────────────

class TestSwarmAnalyticsCore:

    def test_empty_state(self, analytics):
        assert analytics.event_count == 0
        assert analytics.agent_count == 0

    def test_record_single_event(self, analytics):
        analytics.record_event(make_event())
        assert analytics.event_count == 1
        assert analytics.agent_count == 1

    def test_record_multiple_agents(self, analytics):
        analytics.record_event(make_event(agent_id="a1", task_id="t1"))
        analytics.record_event(make_event(agent_id="a2", task_id="t2"))
        analytics.record_event(make_event(agent_id="a3", task_id="t3"))
        assert analytics.agent_count == 3

    def test_record_batch(self, analytics):
        events = [make_event(agent_id=f"a{i}", task_id=f"t{i}") for i in range(10)]
        count = analytics.record_batch(events)
        assert count == 10
        assert analytics.event_count == 10

    def test_max_events_enforcement(self):
        a = SwarmAnalytics(max_events=5)
        for i in range(10):
            a.record_event(make_event(task_id=f"t{i}"))
        assert a.event_count == 5

    def test_completed_updates_metrics(self, analytics):
        analytics.record_event(make_event(
            agent_id="a1", bounty_usd=10.0, quality_rating=4.0
        ))
        detail = analytics.get_agent_detail("a1")
        assert detail["tasks_completed"] == 1
        assert detail["total_revenue_usd"] == 10.0
        assert detail["avg_quality"] == 4.0

    def test_failed_updates_metrics(self, analytics):
        analytics.record_event(make_event(event_type="task_failed", agent_id="a1"))
        detail = analytics.get_agent_detail("a1")
        assert detail["tasks_failed"] == 1

    def test_expired_updates_metrics(self, analytics):
        analytics.record_event(make_event(event_type="task_expired", agent_id="a1"))
        detail = analytics.get_agent_detail("a1")
        assert detail["tasks_expired"] == 1

    def test_assigned_updates_metrics(self, analytics):
        analytics.record_event(make_event(event_type="task_assigned", agent_id="a1"))
        detail = analytics.get_agent_detail("a1")
        assert detail["tasks_assigned"] == 1

    def test_multiple_tasks_accumulate(self, analytics):
        for i in range(5):
            analytics.record_event(make_event(
                agent_id="a1", task_id=f"t{i}",
                bounty_usd=2.0 * (i + 1), quality_rating=3.0 + i * 0.5
            ))
        detail = analytics.get_agent_detail("a1")
        assert detail["tasks_completed"] == 5
        assert detail["total_revenue_usd"] == 30.0  # 2+4+6+8+10
        assert detail["avg_quality"] == pytest.approx(4.0, abs=0.01)

    def test_category_tracking(self, analytics):
        analytics.record_event(make_event(agent_id="a1", task_id="t1", category="physical_verification"))
        analytics.record_event(make_event(agent_id="a1", task_id="t2", category="physical_verification"))
        analytics.record_event(make_event(agent_id="a1", task_id="t3", category="data_collection"))
        detail = analytics.get_agent_detail("a1")
        assert detail["categories"]["physical_verification"] == 2
        assert detail["categories"]["data_collection"] == 1

    def test_unknown_agent_returns_none(self, analytics):
        assert analytics.get_agent_detail("nonexistent") is None


# ──────────────────────────────────────────────────────────────
# Dashboard Tests
# ──────────────────────────────────────────────────────────────

class TestDashboard:

    def test_empty_dashboard(self, analytics):
        d = analytics.get_dashboard()
        assert d["fleet"]["total_agents"] == 0
        assert d["performance"]["total_tasks_completed"] == 0

    def test_dashboard_with_data(self, analytics):
        for i in range(5):
            analytics.record_event(make_event(
                agent_id=f"a{i}", task_id=f"t{i}",
                bounty_usd=10.0, quality_rating=4.0 + i * 0.2,
                category="physical_verification"
            ))
        d = analytics.get_dashboard()
        assert d["fleet"]["total_agents"] == 5
        assert d["fleet"]["active_agents"] == 5
        assert d["performance"]["total_tasks_completed"] == 5
        assert d["performance"]["total_revenue_usd"] == 50.0
        assert d["performance"]["avg_quality"] > 0

    def test_dashboard_categories(self, analytics):
        analytics.record_event(make_event(agent_id="a1", task_id="t1", category="delivery"))
        analytics.record_event(make_event(agent_id="a2", task_id="t2", category="delivery"))
        analytics.record_event(make_event(agent_id="a3", task_id="t3", category="technical_task"))
        d = analytics.get_dashboard()
        cats = {c["category"]: c["count"] for c in d["categories"]}
        assert cats["delivery"] == 2
        assert cats["technical_task"] == 1

    def test_dashboard_top_agents(self, analytics):
        for i in range(10):
            for j in range(i + 1):
                analytics.record_event(make_event(
                    agent_id=f"a{i}", task_id=f"t{i}_{j}",
                    bounty_usd=5.0, quality_rating=4.0
                ))
        d = analytics.get_dashboard()
        assert len(d["top_agents"]) == 5
        # Agent a9 should be top (10 tasks)
        assert d["top_agents"][0]["agent_id"] == "a9"

    def test_get_all_agents_sorted(self, analytics):
        analytics.record_event(make_event(agent_id="slow", task_id="t1", bounty_usd=1.0))
        analytics.record_event(make_event(agent_id="fast", task_id="t2", bounty_usd=100.0))
        analytics.record_event(make_event(agent_id="fast", task_id="t3", bounty_usd=100.0))

        by_tasks = analytics.get_all_agents(sort_by="tasks_completed")
        assert by_tasks[0]["agent_id"] == "fast"

        by_revenue = analytics.get_all_agents(sort_by="revenue")
        assert by_revenue[0]["agent_id"] == "fast"


# ──────────────────────────────────────────────────────────────
# Trend Analysis Tests
# ──────────────────────────────────────────────────────────────

class TestTrends:

    def test_no_data(self, analytics):
        t = analytics.get_trends()
        assert t["trend"] == "no_data"

    def test_single_event(self, analytics):
        analytics.record_event(make_event())
        t = analytics.get_trends()
        assert t["events"] >= 1

    def test_improving_trend(self, analytics):
        now = time.time()
        # Few events early, many events recently
        for i in range(2):
            analytics.record_event(make_event(
                task_id=f"early_{i}", timestamp=now - 6 * 3600 + i * 60
            ))
        for i in range(10):
            analytics.record_event(make_event(
                task_id=f"recent_{i}", timestamp=now - 1 * 3600 + i * 60
            ))
        t = analytics.get_trends(window_hours=24)
        assert t["total_completed"] == 12

    def test_daily_rollup(self, analytics):
        now = time.time()
        for i in range(5):
            analytics.record_event(make_event(
                task_id=f"t{i}", bounty_usd=10.0, timestamp=now - i * 100
            ))
        t = analytics.get_trends(window_hours=24)
        assert len(t["daily"]) >= 1

    def test_trend_revenue(self, analytics):
        for i in range(5):
            analytics.record_event(make_event(task_id=f"t{i}", bounty_usd=20.0))
        t = analytics.get_trends(window_hours=1)
        assert t["total_revenue"] == 100.0


# ──────────────────────────────────────────────────────────────
# Alert Tests
# ──────────────────────────────────────────────────────────────

class TestAlerts:

    def test_no_alerts_when_healthy(self, analytics):
        for i in range(5):
            analytics.record_event(make_event(
                agent_id="good_agent", task_id=f"t{i}", quality_rating=4.5
            ))
        alerts = analytics.check_alerts()
        # Should not have success rate or quality alerts
        agent_alerts = [a for a in alerts if a["agent_id"] == "good_agent"]
        critical = [a for a in agent_alerts if a["level"] in ("warning", "critical")]
        assert len(critical) == 0

    def test_low_success_rate_alert(self, analytics):
        # 1 completed, 3 failed → 25% success rate
        analytics.record_event(make_event(agent_id="bad", task_id="t1"))
        for i in range(3):
            analytics.record_event(make_event(
                event_type="task_failed", agent_id="bad", task_id=f"f{i}"
            ))
        alerts = analytics.check_alerts()
        sr_alerts = [a for a in alerts if a["metric"] == "success_rate"]
        assert len(sr_alerts) >= 1
        assert sr_alerts[0]["value"] < 0.6

    def test_low_quality_alert(self, analytics):
        for i in range(5):
            analytics.record_event(make_event(
                agent_id="lowq", task_id=f"t{i}", quality_rating=2.0
            ))
        alerts = analytics.check_alerts()
        q_alerts = [a for a in alerts if a["metric"] == "avg_quality"]
        assert len(q_alerts) >= 1

    def test_stale_agent_alert(self, analytics):
        old_time = time.time() - 800000  # ~9 days ago
        analytics.record_event(make_event(
            agent_id="stale_one", task_id="t1", timestamp=old_time
        ))
        # Need 3+ tasks for the agent to trigger per-agent checks
        for i in range(3):
            analytics.record_event(make_event(
                agent_id="stale_one", task_id=f"t{i+1}", timestamp=old_time + i
            ))
        alerts = analytics.check_alerts()
        stale_alerts = [a for a in alerts if a["metric"] == "days_inactive"]
        assert len(stale_alerts) >= 1

    def test_fleet_activity_alert(self, analytics):
        old_time = time.time() - 800000
        for i in range(10):
            analytics.record_event(make_event(
                agent_id=f"dead_{i}", task_id=f"t{i}", timestamp=old_time
            ))
        alerts = analytics.check_alerts()
        fleet_alerts = [a for a in alerts if a["metric"] == "fleet_active_pct"]
        assert len(fleet_alerts) >= 1
        assert fleet_alerts[0]["level"] == "critical"

    def test_set_alert_threshold(self, analytics):
        analytics.set_alert_threshold("min_success_rate", 0.9)
        assert analytics._alert_thresholds["min_success_rate"] == 0.9

    def test_few_tasks_skip_alerts(self, analytics):
        # Agent with only 1 task shouldn't trigger alerts
        analytics.record_event(make_event(
            event_type="task_failed", agent_id="newbie", task_id="t1"
        ))
        alerts = analytics.check_alerts()
        newbie_alerts = [a for a in alerts if a["agent_id"] == "newbie"]
        assert len(newbie_alerts) == 0


# ──────────────────────────────────────────────────────────────
# Category Heatmap Tests
# ──────────────────────────────────────────────────────────────

class TestCategoryHeatmap:

    def test_empty_heatmap(self, analytics):
        hm = analytics.get_category_heatmap()
        assert hm == {}

    def test_heatmap_structure(self, analytics):
        analytics.record_event(make_event(agent_id="a1", task_id="t1", category="delivery"))
        analytics.record_event(make_event(agent_id="a1", task_id="t2", category="delivery"))
        analytics.record_event(make_event(agent_id="a2", task_id="t3", category="technical_task"))
        hm = analytics.get_category_heatmap()
        assert hm["a1"]["delivery"] == 2
        assert hm["a2"]["technical_task"] == 1
        assert "a1" not in hm.get("a2", {})


# ──────────────────────────────────────────────────────────────
# Snapshot Tests
# ──────────────────────────────────────────────────────────────

class TestSnapshots:

    def test_auto_snapshot(self):
        a = SwarmAnalytics(max_events=1000, snapshot_interval_seconds=0)
        a.record_event(make_event())
        snaps = a.get_snapshots()
        assert len(snaps) >= 1

    def test_snapshot_content(self):
        a = SwarmAnalytics(max_events=1000, snapshot_interval_seconds=0)
        for i in range(3):
            a.record_event(make_event(
                agent_id=f"a{i}", task_id=f"t{i}",
                bounty_usd=5.0, quality_rating=4.0
            ))
        snaps = a.get_snapshots()
        s = snaps[-1]
        assert s["total_agents"] == 3
        assert s["total_tasks_completed"] == 3

    def test_snapshot_limit(self):
        a = SwarmAnalytics(max_events=1000, snapshot_interval_seconds=0)
        for i in range(5):
            a.record_event(make_event(task_id=f"t{i}"))
        snaps = a.get_snapshots(limit=2)
        assert len(snaps) <= 2


# ──────────────────────────────────────────────────────────────
# Persistence Tests
# ──────────────────────────────────────────────────────────────

class TestPersistence:

    def test_save_and_load(self, tmpdir):
        a1 = SwarmAnalytics(storage_dir=tmpdir, max_events=100)
        for i in range(5):
            a1.record_event(make_event(
                agent_id="a1", task_id=f"t{i}",
                bounty_usd=10.0, quality_rating=4.0
            ))

        # Create new instance from same dir
        a2 = SwarmAnalytics(storage_dir=tmpdir, max_events=100)
        detail = a2.get_agent_detail("a1")
        assert detail is not None
        assert detail["tasks_completed"] == 5
        assert detail["total_revenue_usd"] == 50.0

    def test_corrupted_state_recovery(self, tmpdir):
        import pathlib
        state_path = pathlib.Path(tmpdir) / "analytics_state.json"
        state_path.write_text("{{invalid json!!!")

        # Should not crash
        a = SwarmAnalytics(storage_dir=tmpdir)
        assert a.agent_count == 0

    def test_empty_state_file(self, tmpdir):
        import pathlib
        state_path = pathlib.Path(tmpdir) / "analytics_state.json"
        state_path.write_text("{}")

        a = SwarmAnalytics(storage_dir=tmpdir)
        assert a.agent_count == 0

    def test_threshold_persistence(self, tmpdir):
        a1 = SwarmAnalytics(storage_dir=tmpdir)
        a1.set_alert_threshold("min_success_rate", 0.9)
        a1.record_event(make_event())  # Triggers save

        a2 = SwarmAnalytics(storage_dir=tmpdir)
        assert a2._alert_thresholds["min_success_rate"] == 0.9


# ──────────────────────────────────────────────────────────────
# Edge Case Tests
# ──────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_zero_bounty_event(self, analytics):
        analytics.record_event(make_event(bounty_usd=0.0))
        detail = analytics.get_agent_detail("agent_001")
        assert detail["total_revenue_usd"] == 0.0

    def test_zero_quality_event(self, analytics):
        analytics.record_event(make_event(quality_rating=0.0))
        detail = analytics.get_agent_detail("agent_001")
        assert detail["avg_quality"] == 0.0  # 0 is skipped

    def test_negative_duration(self, analytics):
        analytics.record_event(make_event(duration_seconds=-1))
        detail = analytics.get_agent_detail("agent_001")
        # Should not crash
        assert detail is not None

    def test_summary_string(self, analytics):
        analytics.record_event(make_event())
        s = analytics.summary()
        assert "Fleet:" in s
        assert "Tasks:" in s

    def test_reset(self, analytics):
        for i in range(10):
            analytics.record_event(make_event(task_id=f"t{i}"))
        analytics.reset()
        assert analytics.event_count == 0
        assert analytics.agent_count == 0

    def test_high_volume(self, analytics):
        events = [
            make_event(
                agent_id=f"agent_{i % 24}",
                task_id=f"task_{i}",
                category=["physical_verification", "data_collection", "delivery",
                          "technical_task", "content_creation"][i % 5],
                bounty_usd=5.0 + (i % 10),
                quality_rating=3.0 + (i % 20) / 10.0,
            )
            for i in range(500)
        ]
        analytics.record_batch(events)
        assert analytics.event_count == 500
        assert analytics.agent_count == 24

        d = analytics.get_dashboard()
        assert d["fleet"]["total_agents"] == 24
        assert d["performance"]["total_tasks_completed"] == 500


# ──────────────────────────────────────────────────────────────
# Alert + FleetSnapshot data class tests
# ──────────────────────────────────────────────────────────────

class TestDataClasses:

    def test_alert_to_dict(self):
        a = Alert(level="warning", agent_id="a1", message="test",
                  metric="quality", value=2.0, threshold=3.0)
        d = a.to_dict()
        assert d["level"] == "warning"
        assert d["value"] == 2.0

    def test_fleet_snapshot_to_dict(self):
        s = FleetSnapshot(
            timestamp=time.time(), total_agents=24, active_agents=20,
            stale_agents=2, total_tasks_completed=100, total_tasks_failed=5,
            total_revenue_usd=500.0, avg_fleet_quality=4.2,
            avg_success_rate=0.95, top_categories=[]
        )
        d = s.to_dict()
        assert d["total_agents"] == 24
        assert d["avg_fleet_quality"] == 4.2
