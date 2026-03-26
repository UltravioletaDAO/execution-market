"""
SwarmAnalytics Test Suite
=========================

Comprehensive tests for the metrics aggregation and trend analysis engine.

Coverage:
- TaskEvent and AgentMetrics data types (serialization, properties)
- Event recording (single + batch)
- Agent metrics updates (completion, failure, expiry)
- Dashboard generation (fleet counts, performance, categories)
- Trend analysis (windowing, direction detection)
- Alert system (thresholds, per-agent, fleet-wide)
- Snapshots (auto-generation, storage limits)
- Persistence (save/load roundtrip, corruption resilience)
- Edge cases (empty state, single agent, max events)
"""

import json
import os
import tempfile
import time
import pytest

from mcp_server.swarm.analytics import (
    TaskEvent,
    AgentMetrics,
    FleetSnapshot,
    Alert,
    SwarmAnalytics,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def analytics():
    """Fresh analytics instance with no persistence."""
    return SwarmAnalytics()


@pytest.fixture
def analytics_with_dir():
    """Analytics instance with temp storage directory."""
    with tempfile.TemporaryDirectory() as tmp:
        yield SwarmAnalytics(storage_dir=tmp), tmp


@pytest.fixture
def sample_events():
    """Generate a batch of realistic task events."""
    now = time.time()
    events = []
    for i in range(10):
        events.append(TaskEvent(
            event_type="task_completed",
            agent_id=f"agent_{i % 3}",
            task_id=f"task_{i}",
            category="physical_verification" if i % 2 == 0 else "delivery",
            bounty_usd=5.0 + i * 0.5,
            quality_rating=3.5 + (i % 5) * 0.3,
            duration_seconds=1800 + i * 300,
            timestamp=now - (10 - i) * 3600,
        ))
    # Add some failures
    events.append(TaskEvent(
        event_type="task_failed",
        agent_id="agent_0",
        task_id="task_f1",
        category="physical_verification",
        timestamp=now - 500,
    ))
    events.append(TaskEvent(
        event_type="task_expired",
        agent_id="agent_1",
        task_id="task_e1",
        category="delivery",
        timestamp=now - 200,
    ))
    return events


# ──────────────────────────────────────────────────────────────
# Section 1: Data Types (10 tests)
# ──────────────────────────────────────────────────────────────


class TestTaskEvent:
    """TaskEvent data class."""

    def test_defaults(self):
        e = TaskEvent(event_type="task_completed", agent_id="a1", task_id="t1")
        assert e.event_type == "task_completed"
        assert e.agent_id == "a1"
        assert e.bounty_usd == 0.0
        assert e.quality_rating == 0.0
        assert e.duration_seconds == 0.0
        assert isinstance(e.metadata, dict)
        assert e.timestamp > 0

    def test_to_dict(self):
        e = TaskEvent(
            event_type="task_failed",
            agent_id="a1",
            task_id="t1",
            category="delivery",
            bounty_usd=10.0,
        )
        d = e.to_dict()
        assert d["event_type"] == "task_failed"
        assert d["bounty_usd"] == 10.0
        assert d["category"] == "delivery"

    def test_from_dict(self):
        data = {
            "event_type": "task_completed",
            "agent_id": "a2",
            "task_id": "t2",
            "category": "photo",
            "bounty_usd": 7.5,
            "quality_rating": 4.2,
            "duration_seconds": 3600,
            "timestamp": 1000000,
            "metadata": {"key": "val"},
        }
        e = TaskEvent.from_dict(data)
        assert e.agent_id == "a2"
        assert e.bounty_usd == 7.5
        assert e.quality_rating == 4.2

    def test_from_dict_ignores_extra_keys(self):
        data = {
            "event_type": "task_completed",
            "agent_id": "a1",
            "task_id": "t1",
            "unknown_field": "ignored",
        }
        e = TaskEvent.from_dict(data)
        assert e.agent_id == "a1"

    def test_roundtrip(self):
        original = TaskEvent(
            event_type="task_expired",
            agent_id="a3",
            task_id="t3",
            bounty_usd=15.0,
            metadata={"reason": "timeout"},
        )
        restored = TaskEvent.from_dict(original.to_dict())
        assert restored.event_type == original.event_type
        assert restored.agent_id == original.agent_id
        assert restored.bounty_usd == original.bounty_usd
        assert restored.metadata == original.metadata


class TestAgentMetrics:
    """AgentMetrics computed properties."""

    def test_success_rate_zero_tasks(self):
        m = AgentMetrics(agent_id="a1")
        assert m.success_rate == 0.0

    def test_success_rate_all_completed(self):
        m = AgentMetrics(agent_id="a1", tasks_completed=10, tasks_failed=0, tasks_expired=0)
        assert m.success_rate == 1.0

    def test_success_rate_mixed(self):
        m = AgentMetrics(agent_id="a1", tasks_completed=7, tasks_failed=2, tasks_expired=1)
        assert abs(m.success_rate - 0.7) < 0.001

    def test_is_active_recent(self):
        m = AgentMetrics(agent_id="a1", last_active=time.time() - 100)
        assert m.is_active is True

    def test_is_active_old(self):
        m = AgentMetrics(agent_id="a1", last_active=time.time() - 100000)
        assert m.is_active is False

    def test_is_stale_no_activity(self):
        m = AgentMetrics(agent_id="a1", last_active=0.0)
        assert m.is_stale is False  # Never active = not stale (no last_active)

    def test_is_stale_old_activity(self):
        m = AgentMetrics(agent_id="a1", last_active=time.time() - 700000)
        assert m.is_stale is True

    def test_to_dict_includes_properties(self):
        m = AgentMetrics(agent_id="a1", tasks_completed=8, tasks_failed=2)
        d = m.to_dict()
        assert "success_rate" in d
        assert "is_active" in d
        assert "is_stale" in d
        assert abs(d["success_rate"] - 0.8) < 0.001


# ──────────────────────────────────────────────────────────────
# Section 2: Event Recording (8 tests)
# ──────────────────────────────────────────────────────────────


class TestEventRecording:
    """Record events and verify metric updates."""

    def test_record_single_completed(self, analytics):
        e = TaskEvent(
            event_type="task_completed",
            agent_id="a1",
            task_id="t1",
            bounty_usd=5.0,
            quality_rating=4.5,
            duration_seconds=3600,
        )
        analytics.record_event(e)
        assert analytics.event_count == 1
        assert analytics.agent_count == 1

    def test_record_updates_agent_metrics(self, analytics):
        e = TaskEvent(
            event_type="task_completed",
            agent_id="a1",
            task_id="t1",
            bounty_usd=10.0,
            quality_rating=4.0,
            duration_seconds=1800,
            category="delivery",
        )
        analytics.record_event(e)
        detail = analytics.get_agent_detail("a1")
        assert detail is not None
        assert detail["tasks_completed"] == 1
        assert detail["total_revenue_usd"] == 10.0
        assert detail["avg_quality"] == 4.0
        assert detail["categories"]["delivery"] == 1

    def test_record_failure(self, analytics):
        e = TaskEvent(event_type="task_failed", agent_id="a1", task_id="t1")
        analytics.record_event(e)
        detail = analytics.get_agent_detail("a1")
        assert detail["tasks_failed"] == 1

    def test_record_expiry(self, analytics):
        e = TaskEvent(event_type="task_expired", agent_id="a1", task_id="t1")
        analytics.record_event(e)
        detail = analytics.get_agent_detail("a1")
        assert detail["tasks_expired"] == 1

    def test_record_assigned(self, analytics):
        e = TaskEvent(event_type="task_assigned", agent_id="a1", task_id="t1")
        analytics.record_event(e)
        detail = analytics.get_agent_detail("a1")
        assert detail["tasks_assigned"] == 1

    def test_max_events_enforced(self):
        a = SwarmAnalytics(max_events=5)
        for i in range(10):
            a.record_event(TaskEvent(
                event_type="task_completed", agent_id="a1", task_id=f"t{i}"
            ))
        assert a.event_count == 5

    def test_batch_recording(self, analytics):
        events = [
            TaskEvent(event_type="task_completed", agent_id="a1", task_id=f"t{i}",
                      bounty_usd=1.0, quality_rating=3.0)
            for i in range(5)
        ]
        count = analytics.record_batch(events)
        assert count == 5
        assert analytics.event_count == 5
        detail = analytics.get_agent_detail("a1")
        assert detail["tasks_completed"] == 5
        assert detail["total_revenue_usd"] == 5.0

    def test_multiple_agents(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        assert analytics.agent_count == 3  # agent_0, agent_1, agent_2


# ──────────────────────────────────────────────────────────────
# Section 3: Dashboard Generation (9 tests)
# ──────────────────────────────────────────────────────────────


class TestDashboard:
    """Dashboard data generation."""

    def test_empty_dashboard(self, analytics):
        d = analytics.get_dashboard()
        assert d["fleet"]["total_agents"] == 0
        assert d["fleet"]["active_agents"] == 0
        assert d["performance"]["total_tasks_completed"] == 0
        assert d["categories"] == []

    def test_dashboard_with_data(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        d = analytics.get_dashboard()
        assert d["fleet"]["total_agents"] == 3
        assert d["performance"]["total_tasks_completed"] == 10
        assert d["performance"]["total_tasks_failed"] == 1
        assert d["performance"]["total_revenue_usd"] > 0
        assert len(d["categories"]) > 0

    def test_dashboard_top_agents(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        d = analytics.get_dashboard()
        assert len(d["top_agents"]) <= 5
        for agent in d["top_agents"]:
            assert "agent_id" in agent
            assert "score" in agent
            assert "tasks" in agent

    def test_dashboard_categories_sorted(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        d = analytics.get_dashboard()
        cats = d["categories"]
        # Categories should be sorted by count descending
        counts = [c["count"] for c in cats]
        assert counts == sorted(counts, reverse=True)

    def test_get_agent_detail_missing(self, analytics):
        assert analytics.get_agent_detail("nonexistent") is None

    def test_get_all_agents(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        agents = analytics.get_all_agents(sort_by="tasks_completed")
        assert len(agents) == 3
        # First should have most completed
        assert agents[0]["tasks_completed"] >= agents[1]["tasks_completed"]

    def test_get_all_agents_sort_by_quality(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        agents = analytics.get_all_agents(sort_by="quality")
        assert len(agents) == 3

    def test_get_all_agents_limit(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        agents = analytics.get_all_agents(limit=2)
        assert len(agents) == 2

    def test_category_heatmap(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        heatmap = analytics.get_category_heatmap()
        assert len(heatmap) > 0
        for agent_id, categories in heatmap.items():
            assert isinstance(categories, dict)


# ──────────────────────────────────────────────────────────────
# Section 4: Trend Analysis (7 tests)
# ──────────────────────────────────────────────────────────────


class TestTrends:
    """Trend analysis and windowing."""

    def test_empty_trends(self, analytics):
        t = analytics.get_trends()
        assert t["events"] == 0
        assert t["trend"] == "no_data"

    def test_trends_with_data(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        t = analytics.get_trends(window_hours=168)
        assert t["events"] > 0
        assert t["total_completed"] > 0
        assert t["trend"] in ("improving", "declining", "stable", "growing", "flat", "insufficient_data")

    def test_trends_daily_rollups(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        t = analytics.get_trends(window_hours=168)
        assert "daily" in t
        for day, stats in t["daily"].items():
            assert "completed" in stats
            assert "failed" in stats
            assert "revenue" in stats

    def test_trends_narrow_window(self, analytics):
        """Events outside window are excluded."""
        now = time.time()
        # Old event (2 weeks ago)
        analytics.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="old",
            timestamp=now - 14 * 86400,
        ))
        # Recent event
        analytics.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="new",
            timestamp=now - 3600,
        ))
        t = analytics.get_trends(window_hours=24)
        assert t["events"] == 1  # Only the recent one

    def test_trends_improving(self, analytics):
        """More completions in second half = improving trend."""
        now = time.time()
        # 1 early completion (first half of window)
        analytics.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="early_0",
            timestamp=now - 60 * 3600,
        ))
        # 10 completions in last 10 hours (second half)
        for i in range(10):
            analytics.record_event(TaskEvent(
                event_type="task_completed", agent_id="a1", task_id=f"late_{i}",
                timestamp=now - 5 * 3600 + i * 1800,  # Cluster in recent hours
            ))
        t = analytics.get_trends(window_hours=72)
        assert t["trend"] in ("improving", "growing")

    def test_trends_total_revenue(self, analytics):
        now = time.time()
        for i in range(5):
            analytics.record_event(TaskEvent(
                event_type="task_completed", agent_id="a1", task_id=f"t{i}",
                bounty_usd=10.0, timestamp=now - i * 3600,
            ))
        t = analytics.get_trends(window_hours=24)
        assert t["total_revenue"] == 50.0

    def test_trends_window_zero_events_outside(self, analytics):
        """Very narrow window with no events."""
        now = time.time()
        analytics.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="t1",
            timestamp=now - 48 * 3600,
        ))
        t = analytics.get_trends(window_hours=1)
        assert t["events"] == 0


# ──────────────────────────────────────────────────────────────
# Section 5: Alert System (10 tests)
# ──────────────────────────────────────────────────────────────


class TestAlerts:
    """Alert generation and thresholds."""

    def test_no_alerts_empty(self, analytics):
        alerts = analytics.check_alerts()
        assert alerts == []

    def test_low_success_rate_alert(self, analytics):
        """Agent with <60% success rate triggers warning."""
        # Record events: 2 completed, 5 failed (28.5% success rate)
        for i in range(2):
            analytics.record_event(TaskEvent(
                event_type="task_completed", agent_id="bad_agent",
                task_id=f"c{i}", timestamp=time.time(),
            ))
        for i in range(5):
            analytics.record_event(TaskEvent(
                event_type="task_failed", agent_id="bad_agent",
                task_id=f"f{i}", timestamp=time.time(),
            ))
        alerts = analytics.check_alerts()
        success_alerts = [a for a in alerts if a["metric"] == "success_rate"]
        assert len(success_alerts) == 1
        assert success_alerts[0]["level"] == "warning"

    def test_low_quality_alert(self, analytics):
        """Agent with avg quality < 2.5 triggers warning."""
        for i in range(5):
            analytics.record_event(TaskEvent(
                event_type="task_completed", agent_id="low_q",
                task_id=f"t{i}", quality_rating=1.5, timestamp=time.time(),
            ))
        alerts = analytics.check_alerts()
        quality_alerts = [a for a in alerts if a["metric"] == "avg_quality"]
        assert len(quality_alerts) == 1

    def test_stale_agent_alert(self, analytics):
        """Agent inactive for 7+ days triggers info alert."""
        analytics.record_event(TaskEvent(
            event_type="task_completed", agent_id="stale",
            task_id="t1", timestamp=time.time() - 8 * 86400,
        ))
        # Need at least 3 tasks for alerts to trigger on other metrics,
        # but stale is checked separately
        for i in range(3):
            analytics.record_event(TaskEvent(
                event_type="task_completed", agent_id="stale",
                task_id=f"t{i+2}", timestamp=time.time() - 8 * 86400,
            ))
        alerts = analytics.check_alerts()
        stale_alerts = [a for a in alerts if a["metric"] == "days_inactive"]
        assert len(stale_alerts) == 1
        assert stale_alerts[0]["level"] == "info"

    def test_fleet_active_alert(self, analytics):
        """Low fleet activity triggers critical alert."""
        # Register 4 agents, all stale (old activity)
        for i in range(4):
            # 3 completions each (to pass min task threshold) but old
            for j in range(3):
                analytics.record_event(TaskEvent(
                    event_type="task_completed",
                    agent_id=f"agent_{i}",
                    task_id=f"t{i}_{j}",
                    timestamp=time.time() - 100000,  # Very old
                ))
        alerts = analytics.check_alerts()
        fleet_alerts = [a for a in alerts if a["metric"] == "fleet_active_pct"]
        assert len(fleet_alerts) == 1
        assert fleet_alerts[0]["level"] == "critical"

    def test_no_alert_insufficient_data(self, analytics):
        """Agents with <3 tasks don't trigger per-agent alerts."""
        analytics.record_event(TaskEvent(
            event_type="task_failed", agent_id="new_agent", task_id="t1",
        ))
        analytics.record_event(TaskEvent(
            event_type="task_failed", agent_id="new_agent", task_id="t2",
        ))
        alerts = analytics.check_alerts()
        agent_alerts = [a for a in alerts if a.get("agent_id") == "new_agent"]
        # Should be empty — not enough data
        assert len(agent_alerts) == 0

    def test_set_alert_threshold(self, analytics):
        analytics.set_alert_threshold("min_success_rate", 0.80)
        assert analytics._alert_thresholds["min_success_rate"] == 0.80

    def test_set_threshold_unknown_key(self, analytics):
        """Unknown threshold keys are ignored."""
        analytics.set_alert_threshold("nonexistent", 1.0)
        assert "nonexistent" not in analytics._alert_thresholds

    def test_alert_dict_format(self, analytics):
        """Verify alert dict has expected keys."""
        for i in range(5):
            analytics.record_event(TaskEvent(
                event_type="task_failed", agent_id="bad",
                task_id=f"t{i}", timestamp=time.time(),
            ))
        alerts = analytics.check_alerts()
        assert len(alerts) > 0
        alert = alerts[0]
        assert "level" in alert
        assert "agent_id" in alert
        assert "message" in alert
        assert "metric" in alert
        assert "value" in alert
        assert "threshold" in alert

    def test_good_agent_no_alerts(self, analytics):
        """Agent with 100% success rate and good quality → no alerts."""
        for i in range(5):
            analytics.record_event(TaskEvent(
                event_type="task_completed", agent_id="good",
                task_id=f"t{i}", quality_rating=4.5, timestamp=time.time(),
            ))
        alerts = analytics.check_alerts()
        agent_alerts = [a for a in alerts if a.get("agent_id") == "good"]
        assert len(agent_alerts) == 0


# ──────────────────────────────────────────────────────────────
# Section 6: Snapshots (6 tests)
# ──────────────────────────────────────────────────────────────


class TestSnapshots:
    """Fleet snapshots (point-in-time captures)."""

    def test_no_snapshots_initially(self, analytics):
        assert analytics.get_snapshots() == []

    def test_snapshot_auto_generated(self):
        """Snapshot generated when interval elapsed."""
        a = SwarmAnalytics(snapshot_interval_seconds=0)  # Generate immediately
        a.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="t1",
        ))
        snaps = a.get_snapshots()
        assert len(snaps) >= 1

    def test_snapshot_content(self):
        a = SwarmAnalytics(snapshot_interval_seconds=0)
        a.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="t1",
            bounty_usd=5.0,
        ))
        snaps = a.get_snapshots(limit=1)
        assert len(snaps) == 1
        snap = snaps[0]
        assert snap["total_agents"] == 1
        assert snap["total_tasks_completed"] == 1
        assert snap["total_revenue_usd"] == 5.0

    def test_snapshot_limit(self):
        a = SwarmAnalytics(snapshot_interval_seconds=0)
        for i in range(10):
            a._last_snapshot_time = 0  # Force new snapshot each time
            a.record_event(TaskEvent(
                event_type="task_completed", agent_id="a1", task_id=f"t{i}",
            ))
        snaps = a.get_snapshots(limit=3)
        assert len(snaps) == 3

    def test_fleet_snapshot_serialization(self):
        snap = FleetSnapshot(
            timestamp=1000000,
            total_agents=24,
            active_agents=20,
            stale_agents=2,
            total_tasks_completed=100,
            total_tasks_failed=5,
            total_revenue_usd=500.0,
            avg_fleet_quality=4.2,
            avg_success_rate=0.95,
            top_categories=[{"category": "delivery", "count": 50}],
        )
        d = snap.to_dict()
        assert d["total_agents"] == 24
        assert d["avg_fleet_quality"] == 4.2

    def test_alert_to_dict(self):
        alert = Alert(
            level="warning",
            agent_id="a1",
            message="Test alert",
            metric="success_rate",
            value=0.4,
            threshold=0.6,
        )
        d = alert.to_dict()
        assert d["level"] == "warning"
        assert d["value"] == 0.4


# ──────────────────────────────────────────────────────────────
# Section 7: Persistence (8 tests)
# ──────────────────────────────────────────────────────────────


class TestPersistence:
    """Save/load state to disk."""

    def test_save_creates_file(self, analytics_with_dir):
        a, tmp = analytics_with_dir
        a.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="t1",
            bounty_usd=5.0,
        ))
        a.flush()
        assert os.path.exists(os.path.join(tmp, "analytics_state.json"))

    def test_roundtrip(self, analytics_with_dir):
        a, tmp = analytics_with_dir
        for i in range(5):
            a.record_event(TaskEvent(
                event_type="task_completed", agent_id="a1", task_id=f"t{i}",
                bounty_usd=2.0, quality_rating=4.0, category="delivery",
            ))
        a.flush()

        # Load into new instance
        b = SwarmAnalytics(storage_dir=tmp)
        detail = b.get_agent_detail("a1")
        assert detail is not None
        assert detail["tasks_completed"] == 5
        assert detail["total_revenue_usd"] == 10.0

    def test_load_preserves_categories(self, analytics_with_dir):
        a, tmp = analytics_with_dir
        a.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="t1",
            category="physical_verification",
        ))
        a.flush()

        b = SwarmAnalytics(storage_dir=tmp)
        detail = b.get_agent_detail("a1")
        assert detail["categories"]["physical_verification"] == 1

    def test_load_preserves_thresholds(self, analytics_with_dir):
        a, tmp = analytics_with_dir
        a.set_alert_threshold("min_success_rate", 0.75)
        a.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="t1",
        ))
        a.flush()

        b = SwarmAnalytics(storage_dir=tmp)
        assert b._alert_thresholds["min_success_rate"] == 0.75

    def test_corrupted_state_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Write corrupted JSON
            with open(os.path.join(tmp, "analytics_state.json"), "w") as f:
                f.write("not valid json{{{")
            # Should not raise — starts fresh
            a = SwarmAnalytics(storage_dir=tmp)
            assert a.event_count == 0

    def test_wrong_version_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "analytics_state.json"), "w") as f:
                json.dump({"version": 999, "agents": {}}, f)
            a = SwarmAnalytics(storage_dir=tmp)
            assert a.agent_count == 0

    def test_no_storage_dir_no_file(self):
        a = SwarmAnalytics()  # No storage dir
        a.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="t1",
        ))
        a.flush()  # Should not raise

    def test_debounced_saves(self):
        """Save is debounced to avoid excessive I/O."""
        with tempfile.TemporaryDirectory() as tmp:
            a = SwarmAnalytics(storage_dir=tmp)
            a._save_debounce_seconds = 9999  # Very long debounce
            a._last_save_time = time.time()  # Set to now

            a.record_event(TaskEvent(
                event_type="task_completed", agent_id="a1", task_id="t1",
            ))
            # File should not exist yet (debounce not expired)
            assert not os.path.exists(os.path.join(tmp, "analytics_state.json"))

            # Force flush should work
            a.flush()
            assert os.path.exists(os.path.join(tmp, "analytics_state.json"))


# ──────────────────────────────────────────────────────────────
# Section 8: Utilities & Edge Cases (7 tests)
# ──────────────────────────────────────────────────────────────


class TestUtilities:
    """Utility methods and edge cases."""

    def test_reset(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        assert analytics.event_count > 0
        analytics.reset()
        assert analytics.event_count == 0
        assert analytics.agent_count == 0

    def test_summary_string(self, analytics, sample_events):
        analytics.record_batch(sample_events)
        s = analytics.summary()
        assert "Fleet:" in s
        assert "Tasks:" in s
        assert "Quality:" in s
        assert "Revenue:" in s

    def test_summary_empty(self, analytics):
        s = analytics.summary()
        assert "0/0" in s or "Fleet: 0" in s

    def test_event_count_property(self, analytics):
        assert analytics.event_count == 0
        analytics.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="t1",
        ))
        assert analytics.event_count == 1

    def test_agent_count_property(self, analytics):
        assert analytics.agent_count == 0
        analytics.record_event(TaskEvent(
            event_type="task_completed", agent_id="a1", task_id="t1",
        ))
        assert analytics.agent_count == 1

    def test_quality_tracking_accuracy(self, analytics):
        """Verify running average of quality scores."""
        ratings = [3.0, 4.0, 5.0]
        for i, r in enumerate(ratings):
            analytics.record_event(TaskEvent(
                event_type="task_completed", agent_id="a1", task_id=f"t{i}",
                quality_rating=r,
            ))
        detail = analytics.get_agent_detail("a1")
        expected_avg = sum(ratings) / len(ratings)
        assert abs(detail["avg_quality"] - expected_avg) < 0.001

    def test_duration_tracking(self, analytics):
        """Verify running average of durations."""
        durations = [1000, 2000, 3000]
        for i, d in enumerate(durations):
            analytics.record_event(TaskEvent(
                event_type="task_completed", agent_id="a1", task_id=f"t{i}",
                duration_seconds=d,
            ))
        detail = analytics.get_agent_detail("a1")
        assert abs(detail["avg_duration_seconds"] - 2000.0) < 0.001
