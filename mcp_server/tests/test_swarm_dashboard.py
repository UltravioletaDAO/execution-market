"""
Tests for SwarmDashboard — Real-Time Fleet Health Monitoring
=============================================================

Covers:
1. Data types and properties (AgentStatus, PipelineMetrics, etc.)
2. Agent registration and state management
3. Task event recording and budget tracking
4. Lock events and coordination health
5. IRC activity tracking
6. Snapshot generation — full integration
7. Alert generation (all severity levels)
8. Fleet status assessment
9. Health report generation
10. SLA metrics
11. Heatmap generation
12. Utilities (top performers, struggling agents)
13. Edge cases and boundary conditions
"""

import time
from unittest.mock import patch

import pytest

from mcp_server.swarm.dashboard import (
    AgentStatus,
    BudgetSummary,
    CategoryHeatmapEntry,
    DashboardAlert,
    DashboardSnapshot,
    FleetStatus,
    HealthReport,
    PipelineMetrics,
    PipelineStage,
    SLAMetrics,
    Severity,
    SwarmDashboard,
    _today_start_ts,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def dashboard():
    return SwarmDashboard()


@pytest.fixture
def populated_dashboard():
    """Dashboard with 3 agents and some task history."""
    db = SwarmDashboard()
    db.register_agent(
        "agent-01", budget_limit_usd=5.0, specializations=["simple_action"]
    )
    db.register_agent(
        "agent-02",
        budget_limit_usd=10.0,
        specializations=["research", "code_execution"],
    )
    db.register_agent("agent-03", budget_limit_usd=3.0)

    # agent-01: 3 completed, 0 failed (100% success)
    for i in range(3):
        db.record_task_event(
            "agent-01",
            f"task-{i}",
            "task_completed",
            category="simple_action",
            bounty_usd=0.15,
            quality=0.9,
            duration_s=30.0,
        )

    # agent-02: 2 completed, 1 failed (67% success)
    db.record_task_event(
        "agent-02",
        "task-10",
        "task_completed",
        category="research",
        bounty_usd=0.50,
        quality=0.8,
        duration_s=120.0,
    )
    db.record_task_event(
        "agent-02",
        "task-11",
        "task_completed",
        category="code_execution",
        bounty_usd=0.75,
        quality=0.95,
        duration_s=180.0,
    )
    db.record_task_event(
        "agent-02",
        "task-12",
        "task_failed",
        category="research",
        bounty_usd=0.0,
        duration_s=60.0,
    )

    # agent-03: idle, no tasks
    db.update_agent_state("agent-01", "working", task_id="task-99")
    db.update_agent_state("agent-02", "idle")
    db.update_agent_state("agent-03", "idle")

    return db


# ──────────────────────────────────────────────────────────────
# 1. Data Type Tests
# ──────────────────────────────────────────────────────────────


class TestAgentStatus:
    def test_defaults(self):
        status = AgentStatus(agent_id="test")
        assert status.agent_id == "test"
        assert status.state == "unknown"
        assert status.health_score == 0.0
        assert status.daily_budget_usd == 5.0

    def test_is_stale_no_activity(self):
        status = AgentStatus(agent_id="test", last_activity_ts=0.0)
        assert status.is_stale is True

    def test_is_stale_recent(self):
        status = AgentStatus(agent_id="test", last_activity_ts=time.time() - 60)
        assert status.is_stale is False

    def test_is_stale_old(self):
        status = AgentStatus(agent_id="test", last_activity_ts=time.time() - 700)
        assert status.is_stale is True

    def test_budget_headroom(self):
        status = AgentStatus(agent_id="test", daily_spend_usd=3.0, daily_budget_usd=5.0)
        assert status.budget_headroom_usd == 2.0

    def test_budget_headroom_over(self):
        status = AgentStatus(agent_id="test", daily_spend_usd=7.0, daily_budget_usd=5.0)
        assert status.budget_headroom_usd == 0.0


class TestPipelineMetrics:
    def test_total_active(self):
        pm = PipelineMetrics(queued=5, scheduling=2, assigned=3, in_progress=1)
        assert pm.total_active == 11

    def test_total_resolved(self):
        pm = PipelineMetrics(completed_today=10, failed_today=3, expired_today=2)
        assert pm.total_resolved_today == 15


class TestBudgetSummary:
    def test_utilization(self):
        bs = BudgetSummary(total_daily_budget_usd=100.0, total_spent_today_usd=50.0)
        assert bs.utilization == 0.5

    def test_utilization_over_budget(self):
        bs = BudgetSummary(total_daily_budget_usd=100.0, total_spent_today_usd=150.0)
        assert bs.utilization == 1.0  # Capped at 1.0

    def test_utilization_zero_budget(self):
        bs = BudgetSummary(total_daily_budget_usd=0.0, total_spent_today_usd=10.0)
        assert bs.utilization == 0.0


class TestCategoryHeatmapEntry:
    def test_success_rate(self):
        entry = CategoryHeatmapEntry(
            agent_id="a1",
            category="test",
            tasks_completed=7,
            tasks_failed=3,
        )
        assert entry.success_rate == 0.7

    def test_success_rate_no_tasks(self):
        entry = CategoryHeatmapEntry(agent_id="a1", category="test")
        assert entry.success_rate == 0.0


class TestSLAMetrics:
    def test_adherence_rate(self):
        sla = SLAMetrics(tasks_met_deadline=9, tasks_missed_deadline=1)
        assert sla.adherence_rate == 0.9

    def test_adherence_no_tasks(self):
        sla = SLAMetrics()
        assert sla.adherence_rate == 1.0


class TestDashboardAlert:
    def test_to_dict(self):
        alert = DashboardAlert(
            severity=Severity.CRITICAL,
            title="Test",
            message="Test alert",
        )
        d = alert.to_dict()
        assert d["severity"] == "critical"
        assert d["title"] == "Test"


class TestDashboardSnapshot:
    def test_operational_rate(self):
        snap = DashboardSnapshot(agent_count=10, agents_operational=8)
        assert snap.operational_rate == 0.8

    def test_operational_rate_zero(self):
        snap = DashboardSnapshot(agent_count=0, agents_operational=0)
        assert snap.operational_rate == 0.0

    def test_summary_line(self):
        snap = DashboardSnapshot(
            fleet_status=FleetStatus.HEALTHY,
            agent_count=24,
            agents_operational=22,
            pipeline=PipelineMetrics(completed_today=10, failed_today=2),
            budget=BudgetSummary(total_spent_today_usd=5.50),
        )
        line = snap.summary_line()
        assert "HEALTHY" in line
        assert "22/24" in line
        assert "10 done" in line
        assert "$5.50" in line

    def test_to_dict(self):
        snap = DashboardSnapshot(fleet_status=FleetStatus.DEGRADED, agent_count=5)
        d = snap.to_dict()
        assert d["fleet_status"] == "degraded"
        assert d["agent_count"] == 5
        assert "pipeline" in d
        assert "budget" in d


# ──────────────────────────────────────────────────────────────
# 2. Agent Registration
# ──────────────────────────────────────────────────────────────


class TestAgentRegistration:
    def test_register_single(self, dashboard):
        dashboard.register_agent("agent-01")
        assert "agent-01" in dashboard.get_agent_ids()

    def test_register_with_budget(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=10.0)
        snap = dashboard.generate_snapshot()
        agent = snap.agent_statuses[0]
        assert agent.daily_budget_usd == 10.0

    def test_register_with_specializations(self, dashboard):
        dashboard.register_agent("agent-01", specializations=["research", "code"])
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].specializations == ["research", "code"]

    def test_register_multiple(self, dashboard):
        for i in range(5):
            dashboard.register_agent(f"agent-{i:02d}")
        assert len(dashboard.get_agent_ids()) == 5

    def test_re_register_preserves_state(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=5.0)
        dashboard.record_task_event(
            "agent-01",
            "t1",
            "task_completed",
            bounty_usd=1.0,
        )
        # Re-register with different budget
        dashboard.register_agent("agent-01", budget_limit_usd=10.0)
        snap = dashboard.generate_snapshot()
        agent = snap.agent_statuses[0]
        assert agent.daily_spend_usd == 1.0  # Preserved
        assert agent.daily_budget_usd == 10.0  # Updated


# ──────────────────────────────────────────────────────────────
# 3. Agent State Management
# ──────────────────────────────────────────────────────────────


class TestAgentStateManagement:
    def test_update_state(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.update_agent_state("agent-01", "working", task_id="task-1")
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].state == "working"
        assert snap.agent_statuses[0].current_task_id == "task-1"

    def test_clear_task_on_idle(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.update_agent_state("agent-01", "working", task_id="task-1")
        dashboard.update_agent_state("agent-01", "idle")
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].current_task_id is None

    def test_clear_task_on_suspended(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.update_agent_state("agent-01", "working", task_id="task-1")
        dashboard.update_agent_state("agent-01", "suspended")
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].state == "suspended"
        assert snap.agent_statuses[0].current_task_id is None


# ──────────────────────────────────────────────────────────────
# 4. Task Events & Budget Tracking
# ──────────────────────────────────────────────────────────────


class TestTaskEvents:
    def test_completed_task_counts(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=0.15)
        dashboard.record_task_event("agent-01", "t2", "task_completed", bounty_usd=0.20)
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].tasks_completed_today == 2
        assert snap.pipeline.completed_today == 2

    def test_failed_task_counts(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event("agent-01", "t1", "task_failed")
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].tasks_failed_today == 1
        assert snap.pipeline.failed_today == 1

    def test_budget_tracking(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=5.0)
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=1.50)
        dashboard.record_task_event("agent-01", "t2", "task_completed", bounty_usd=2.25)
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].daily_spend_usd == 3.75

    def test_success_rate(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(7):
            dashboard.record_task_event("agent-01", f"t{i}", "task_completed")
        for i in range(3):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].success_rate == 0.7

    def test_consecutive_failures(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event("agent-01", "t1", "task_completed")
        dashboard.record_task_event("agent-01", "t2", "task_failed")
        dashboard.record_task_event("agent-01", "t3", "task_failed")
        dashboard.record_task_event("agent-01", "t4", "task_failed")
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].consecutive_failures == 3

    def test_consecutive_failures_reset(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event("agent-01", "t1", "task_failed")
        dashboard.record_task_event("agent-01", "t2", "task_failed")
        dashboard.record_task_event("agent-01", "t3", "task_completed")  # Resets streak
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].consecutive_failures == 0

    def test_avg_completion_time(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event(
            "agent-01", "t1", "task_completed", duration_s=100.0
        )
        dashboard.record_task_event(
            "agent-01", "t2", "task_completed", duration_s=200.0
        )
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].avg_completion_time_s == 150.0

    def test_expired_task_tracking(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event("agent-01", "t1", "task_expired")
        dashboard.record_task_event("agent-01", "t2", "task_expired")
        snap = dashboard.generate_snapshot()
        assert snap.pipeline.expired_today == 2


# ──────────────────────────────────────────────────────────────
# 5. Coordination & Lock Events
# ──────────────────────────────────────────────────────────────


class TestCoordination:
    def test_lock_tracking(self, dashboard):
        dashboard.record_lock_event("lock", "worker-1", "agent-01")
        snap = dashboard.generate_snapshot()
        assert snap.coordination.active_locks == 1

    def test_lock_release(self, dashboard):
        dashboard.record_lock_event("lock", "worker-1", "agent-01")
        dashboard.record_lock_event("release", "worker-1")
        snap = dashboard.generate_snapshot()
        assert snap.coordination.active_locks == 0

    def test_lock_contention(self, dashboard):
        dashboard.record_lock_event("lock", "worker-1", "agent-01")
        dashboard.record_lock_event("lock", "worker-1", "agent-02")  # Different agent
        snap = dashboard.generate_snapshot()
        assert snap.coordination.lock_contentions_1h == 1

    def test_stale_lock_detection(self, dashboard):
        with patch("mcp_server.swarm.dashboard.time") as mock_time:
            mock_time.time.return_value = 1000.0
            dashboard.record_lock_event("lock", "worker-1", "agent-01")

            # Fast forward 6 minutes
            mock_time.time.return_value = 1360.0
            snap = dashboard.generate_snapshot()
            assert snap.coordination.stale_locks == 1

    def test_irc_connected_flag(self, dashboard):
        dashboard.set_irc_connected(True)
        snap = dashboard.generate_snapshot()
        assert snap.coordination.irc_connected is True

    def test_irc_activity(self, dashboard):
        dashboard.record_irc_activity("agent-01")
        snap = dashboard.generate_snapshot()
        assert snap.coordination.agents_online >= 1
        assert snap.coordination.message_rate_per_min >= 1

    def test_lock_duration_calculation(self, dashboard):
        with patch("mcp_server.swarm.dashboard.time") as mock_time:
            mock_time.time.return_value = 1000.0
            dashboard.record_lock_event("lock", "worker-1", "agent-01")

            mock_time.time.return_value = 1060.0  # 60 seconds later
            dashboard.record_lock_event("release", "worker-1")

            snap = dashboard.generate_snapshot()
            assert snap.coordination.avg_lock_duration_s == 60.0


# ──────────────────────────────────────────────────────────────
# 6. Snapshot Generation
# ──────────────────────────────────────────────────────────────


class TestSnapshotGeneration:
    def test_empty_snapshot(self, dashboard):
        snap = dashboard.generate_snapshot()
        assert snap.agent_count == 0
        assert snap.fleet_status == FleetStatus.DOWN  # No agents = down

    def test_populated_snapshot(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        assert snap.agent_count == 3
        assert snap.agents_working == 1  # agent-01
        assert snap.agents_idle >= 1  # agent-02, agent-03

    def test_uptime_tracking(self, dashboard):
        snap = dashboard.generate_snapshot()
        assert snap.uptime_seconds >= 0

    def test_snapshot_sorting(self, dashboard):
        dashboard.register_agent("agent-03")
        dashboard.register_agent("agent-01")
        dashboard.register_agent("agent-02")
        snap = dashboard.generate_snapshot()
        ids = [a.agent_id for a in snap.agent_statuses]
        assert ids == sorted(ids)

    def test_pipeline_in_progress(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.register_agent("agent-02")
        dashboard.update_agent_state("agent-01", "working", task_id="t1")
        dashboard.update_agent_state("agent-02", "working", task_id="t2")
        snap = dashboard.generate_snapshot()
        assert snap.pipeline.in_progress == 2


# ──────────────────────────────────────────────────────────────
# 7. Alert Generation
# ──────────────────────────────────────────────────────────────


class TestAlertGeneration:
    def test_failure_streak_warning(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(3):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        snap = dashboard.generate_snapshot()
        warnings = [
            a
            for a in snap.alerts
            if a.severity == Severity.WARNING and "failing" in a.title
        ]
        assert len(warnings) >= 1

    def test_failure_streak_critical(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(5):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        snap = dashboard.generate_snapshot()
        criticals = [
            a
            for a in snap.alerts
            if a.severity == Severity.CRITICAL and "failure streak" in a.title
        ]
        assert len(criticals) >= 1

    def test_over_budget_alert(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=1.0)
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=1.50)
        snap = dashboard.generate_snapshot()
        budget_alerts = [a for a in snap.alerts if "over budget" in a.title]
        assert len(budget_alerts) >= 1

    def test_stale_agent_alert(self, dashboard):
        dashboard.register_agent("agent-01")
        # Agent has activity from 15 minutes ago
        event = {
            "agent_id": "agent-01",
            "task_id": "old",
            "event_type": "task_completed",
            "category": "",
            "bounty_usd": 0.0,
            "quality": 0.0,
            "duration_s": 0.0,
            "timestamp": time.time() - 900,  # 15 min ago
        }
        dashboard._agent_events["agent-01"].append(event)
        snap = dashboard.generate_snapshot()
        stale_alerts = [a for a in snap.alerts if "unresponsive" in a.title]
        assert len(stale_alerts) >= 1

    def test_irc_offline_alert(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.register_agent("agent-02")
        dashboard.set_irc_connected(False)
        snap = dashboard.generate_snapshot()
        irc_alerts = [a for a in snap.alerts if "IRC" in a.title]
        assert len(irc_alerts) >= 1

    def test_stale_lock_alert(self, dashboard):
        dashboard.register_agent("agent-01")
        with patch("mcp_server.swarm.dashboard.time") as mock_time:
            mock_time.time.return_value = 1000.0
            dashboard.record_lock_event("lock", "worker-1", "agent-01")
            mock_time.time.return_value = 1400.0
            snap = dashboard.generate_snapshot()
            lock_alerts = [a for a in snap.alerts if "Stale" in a.title]
            assert len(lock_alerts) >= 1

    def test_high_expiry_alert(self, dashboard):
        dashboard.register_agent("agent-01")
        # More expired than completed
        dashboard.record_task_event("agent-01", "t1", "task_completed")
        dashboard.record_task_event("agent-01", "e1", "task_expired")
        dashboard.record_task_event("agent-01", "e2", "task_expired")
        snap = dashboard.generate_snapshot()
        expiry_alerts = [a for a in snap.alerts if "expiry" in a.title]
        assert len(expiry_alerts) >= 1

    def test_alert_severity_sorting(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=0.01)
        # Trigger critical (failure streak) + warning (over budget)
        for i in range(5):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=1.0)
        snap = dashboard.generate_snapshot()
        if len(snap.alerts) >= 2:
            # Verify critical comes before warning
            severity_order = {
                Severity.EMERGENCY: 0,
                Severity.CRITICAL: 1,
                Severity.WARNING: 2,
                Severity.INFO: 3,
            }
            for i in range(len(snap.alerts) - 1):
                assert (
                    severity_order[snap.alerts[i].severity]
                    <= severity_order[snap.alerts[i + 1].severity]
                )

    def test_no_stale_alert_for_suspended(self, dashboard):
        """Suspended agents shouldn't generate stale alerts."""
        dashboard.register_agent("agent-01")
        dashboard.update_agent_state("agent-01", "suspended")
        # Add old activity
        event = {
            "agent_id": "agent-01",
            "task_id": "old",
            "event_type": "task_completed",
            "category": "",
            "bounty_usd": 0.0,
            "quality": 0.0,
            "duration_s": 0.0,
            "timestamp": time.time() - 900,
        }
        dashboard._agent_events["agent-01"].append(event)
        snap = dashboard.generate_snapshot()
        stale_alerts = [a for a in snap.alerts if "unresponsive" in a.title]
        assert len(stale_alerts) == 0  # No stale alert for suspended


# ──────────────────────────────────────────────────────────────
# 8. Fleet Status Assessment
# ──────────────────────────────────────────────────────────────


class TestFleetStatus:
    def test_healthy(self, dashboard):
        for i in range(10):
            dashboard.register_agent(f"agent-{i:02d}")
            dashboard.update_agent_state(f"agent-{i:02d}", "active")
            # Give each agent recent activity so they're not stale
            dashboard.record_task_event(f"agent-{i:02d}", f"t{i}", "task_completed")
        dashboard.set_irc_connected(True)
        snap = dashboard.generate_snapshot()
        assert snap.fleet_status == FleetStatus.HEALTHY

    def test_degraded_low_operational(self, dashboard):
        for i in range(10):
            dashboard.register_agent(f"agent-{i:02d}")
        # Only 7 operational (70%)
        for i in range(7):
            dashboard.update_agent_state(f"agent-{i:02d}", "active")
        for i in range(7, 10):
            dashboard.update_agent_state(f"agent-{i:02d}", "suspended")
        snap = dashboard.generate_snapshot()
        # Either DEGRADED (from operational rate) or from warnings
        assert snap.fleet_status in (FleetStatus.DEGRADED, FleetStatus.IMPAIRED)

    def test_down_no_agents(self, dashboard):
        snap = dashboard.generate_snapshot()
        assert snap.fleet_status == FleetStatus.DOWN

    def test_impaired_critical_alerts(self, dashboard):
        for i in range(4):
            dashboard.register_agent(f"agent-{i:02d}")
            dashboard.update_agent_state(f"agent-{i:02d}", "active")
        # Trigger critical: failure streak on one agent
        for j in range(5):
            dashboard.record_task_event("agent-00", f"f{j}", "task_failed")
        snap = dashboard.generate_snapshot()
        # Should be IMPAIRED because of critical alert
        assert snap.fleet_status in (FleetStatus.IMPAIRED, FleetStatus.DEGRADED)


# ──────────────────────────────────────────────────────────────
# 9. Health Report
# ──────────────────────────────────────────────────────────────


class TestHealthReport:
    def test_basic_report(self, populated_dashboard):
        report = populated_dashboard.generate_health_report()
        assert isinstance(report, HealthReport)
        assert report.fleet_status in FleetStatus
        assert len(report.summary) > 0

    def test_report_with_critical_alerts(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(5):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        report = dashboard.generate_health_report()
        assert len(report.critical_alerts) >= 1

    def test_report_recommendations_budget(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=0.10)
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=0.50)
        report = dashboard.generate_health_report()
        budget_recs = [r for r in report.recommendations if "budget" in r.lower()]
        assert len(budget_recs) >= 1

    def test_report_recommendations_expired(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(3):
            dashboard.record_task_event("agent-01", f"e{i}", "task_expired")
        report = dashboard.generate_health_report()
        expired_recs = [r for r in report.recommendations if "expired" in r.lower()]
        assert len(expired_recs) >= 1


# ──────────────────────────────────────────────────────────────
# 10. SLA Metrics
# ──────────────────────────────────────────────────────────────


class TestSLADeadlineTracking:
    def test_deadline_tracking_met(self, dashboard):
        dashboard.register_agent("agent-01")
        future_deadline = time.time() + 3600  # 1 hour from now
        dashboard.record_task_event(
            "agent-01",
            "t1",
            "task_completed",
            deadline_ts=future_deadline,
        )
        snap = dashboard.generate_snapshot()
        assert snap.sla.tasks_met_deadline == 1
        assert snap.sla.tasks_missed_deadline == 0

    def test_deadline_tracking_missed(self, dashboard):
        dashboard.register_agent("agent-01")
        past_deadline = time.time() - 3600  # 1 hour ago
        dashboard.record_task_event(
            "agent-01",
            "t1",
            "task_completed",
            deadline_ts=past_deadline,
        )
        snap = dashboard.generate_snapshot()
        assert snap.sla.tasks_missed_deadline == 1

    def test_sla_alert_warning(self, dashboard):
        dashboard.register_agent("agent-01")
        past = time.time() - 100
        # 1 met, 2 missed = 33% adherence
        dashboard.record_task_event(
            "agent-01", "t1", "task_completed", deadline_ts=time.time() + 100
        )
        dashboard.record_task_event("agent-01", "t2", "task_failed", deadline_ts=past)
        dashboard.record_task_event("agent-01", "t3", "task_failed", deadline_ts=past)
        snap = dashboard.generate_snapshot()
        sla_alerts = [a for a in snap.alerts if "SLA" in a.title]
        assert len(sla_alerts) >= 1


# ──────────────────────────────────────────────────────────────
# 11. Heatmap
# ──────────────────────────────────────────────────────────────


class TestHeatmap:
    def test_heatmap_generation(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        assert len(snap.heatmap) > 0
        # agent-01 should have simple_action entry
        agent01_entries = [h for h in snap.heatmap if h.agent_id == "agent-01"]
        assert len(agent01_entries) >= 1

    def test_heatmap_categories(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        categories = set(h.category for h in snap.heatmap)
        assert "simple_action" in categories
        assert "research" in categories

    def test_heatmap_success_rates(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        # agent-01: 100% in simple_action
        agent01_sa = [
            h
            for h in snap.heatmap
            if h.agent_id == "agent-01" and h.category == "simple_action"
        ]
        if agent01_sa:
            assert agent01_sa[0].success_rate == 1.0

    def test_heatmap_sorted(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        for i in range(len(snap.heatmap) - 1):
            key_a = (snap.heatmap[i].agent_id, snap.heatmap[i].category)
            key_b = (snap.heatmap[i + 1].agent_id, snap.heatmap[i + 1].category)
            assert key_a <= key_b


# ──────────────────────────────────────────────────────────────
# 12. Utilities
# ──────────────────────────────────────────────────────────────


class TestUtilities:
    def test_get_agent_ids(self, populated_dashboard):
        ids = populated_dashboard.get_agent_ids()
        assert len(ids) == 3
        assert ids == sorted(ids)

    def test_top_performers(self, populated_dashboard):
        top = populated_dashboard.get_top_performers(n=2)
        assert len(top) <= 2
        # First should have highest health score
        if len(top) >= 2:
            assert top[0].health_score >= top[1].health_score

    def test_struggling_agents(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(4):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        struggling = dashboard.get_struggling_agents()
        ids = [a.agent_id for a in struggling]
        assert "agent-01" in ids

    def test_reset_daily_counters(self, populated_dashboard):
        populated_dashboard.reset_daily_counters()
        # Budgets should be reset
        for agent_id, (spent, limit) in populated_dashboard._agent_budgets.items():
            assert spent == 0.0

    def test_today_start_ts(self):
        ts = _today_start_ts()
        assert ts > 0
        assert ts <= time.time()


# ──────────────────────────────────────────────────────────────
# 13. Health Score Computation
# ──────────────────────────────────────────────────────────────


class TestHealthScore:
    def test_perfect_health(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=10.0)
        # 10 completions, 0 failures, just happened
        for i in range(10):
            dashboard.record_task_event(
                "agent-01", f"t{i}", "task_completed", bounty_usd=0.10
            )
        dashboard.update_agent_state("agent-01", "active")
        snap = dashboard.generate_snapshot()
        # Should have high health score
        assert snap.agent_statuses[0].health_score >= 0.7

    def test_zero_health(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=1.0)
        # All failures, over budget, stale
        for i in range(6):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=5.0)
        # Make stale by manipulating last activity
        dashboard._agent_events["agent-01"][-1]["timestamp"] = time.time() - 1200
        snap = dashboard.generate_snapshot()
        assert snap.agent_statuses[0].health_score < 0.5

    def test_health_varies_by_success(self, dashboard):
        # Two agents: one perfect, one failing
        dashboard.register_agent("agent-good")
        dashboard.register_agent("agent-bad")
        for i in range(5):
            dashboard.record_task_event("agent-good", f"t{i}", "task_completed")
            dashboard.record_task_event("agent-bad", f"f{i}", "task_failed")
        snap = dashboard.generate_snapshot()
        good = [a for a in snap.agent_statuses if a.agent_id == "agent-good"][0]
        bad = [a for a in snap.agent_statuses if a.agent_id == "agent-bad"][0]
        assert good.health_score > bad.health_score


# ──────────────────────────────────────────────────────────────
# 14. Budget Summary Fleet-Wide
# ──────────────────────────────────────────────────────────────


class TestBudgetFleetWide:
    def test_fleet_budget_aggregation(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        # Total budget = 5 + 10 + 3 = 18
        assert snap.budget.total_daily_budget_usd == 18.0
        # Total spent = 0.45 (agent-01: 3×0.15) + 1.25 (agent-02: 0.50+0.75) + 0 = 1.70
        assert abs(snap.budget.total_spent_today_usd - 1.70) < 0.01

    def test_fleet_budget_crisis_alert(self, dashboard):
        for i in range(4):
            dashboard.register_agent(f"agent-{i}", budget_limit_usd=1.0)
            dashboard.record_task_event(
                f"agent-{i}", f"t{i}", "task_completed", bounty_usd=1.50
            )
        snap = dashboard.generate_snapshot()
        crisis_alerts = [a for a in snap.alerts if "crisis" in a.title.lower()]
        assert len(crisis_alerts) >= 1


# ──────────────────────────────────────────────────────────────
# 15. Edge Cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_agent_with_no_events(self, dashboard):
        dashboard.register_agent("agent-01")
        snap = dashboard.generate_snapshot()
        agent = snap.agent_statuses[0]
        assert agent.tasks_completed_today == 0
        assert agent.success_rate == 0.0

    def test_multiple_snapshots_consistent(self, populated_dashboard):
        snap1 = populated_dashboard.generate_snapshot()
        snap2 = populated_dashboard.generate_snapshot()
        assert snap1.agent_count == snap2.agent_count
        assert snap1.pipeline.completed_today == snap2.pipeline.completed_today

    def test_pipeline_stage_enum(self):
        assert PipelineStage.QUEUED.value == "queued"
        assert PipelineStage.COMPLETED.value == "completed"

    def test_severity_enum(self):
        assert Severity.EMERGENCY.value == "emergency"
        assert Severity.INFO.value == "info"

    def test_fleet_status_enum(self):
        assert FleetStatus.HEALTHY.value == "healthy"
        assert FleetStatus.DOWN.value == "down"

    def test_snapshot_to_dict_completeness(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        d = snap.to_dict()
        required_keys = [
            "timestamp",
            "fleet_status",
            "agent_count",
            "agents_operational",
            "pipeline",
            "budget",
            "coordination",
            "sla",
            "alert_count",
        ]
        for key in required_keys:
            assert key in d, f"Missing key: {key}"
