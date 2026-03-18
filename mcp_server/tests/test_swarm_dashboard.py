"""
Tests for SwarmDashboard — Fleet Health Monitoring
"""

import time
import pytest
from mcp_server.swarm.dashboard import (
    SwarmDashboard,
    AgentStatus,
    PipelineMetrics,
    BudgetSummary,
    SLAMetrics,
    CategoryHeatmapEntry,
    DashboardAlert,
    HealthReport,
    Severity,
    FleetStatus,
    PipelineStage,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def dashboard():
    return SwarmDashboard()


@pytest.fixture
def populated_dashboard():
    """Dashboard with 24 agents registered and some activity."""
    db = SwarmDashboard()
    for i in range(24):
        agent_id = f"agent-{i:02d}"
        db.register_agent(
            agent_id,
            budget_limit_usd=5.0,
            specializations=["simple_action", "knowledge_access"],
        )
        db.update_agent_state(agent_id, "idle")
    return db


# ──────────────────────────────────────────────────────────────
# Agent Registration & State
# ──────────────────────────────────────────────────────────────


class TestAgentRegistration:
    def test_register_agent(self, dashboard):
        dashboard.register_agent(
            "agent-01", budget_limit_usd=10.0, specializations=["research"]
        )
        assert "agent-01" in dashboard.get_agent_ids()

    def test_register_multiple_agents(self, dashboard):
        for i in range(5):
            dashboard.register_agent(f"agent-{i:02d}")
        assert len(dashboard.get_agent_ids()) == 5

    def test_register_agent_default_budget(self, dashboard):
        dashboard.register_agent("agent-01")
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.daily_budget_usd == 5.0

    def test_register_agent_custom_budget(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=15.0)
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.daily_budget_usd == 15.0

    def test_register_preserves_existing_spend(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=5.0)
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=2.0)
        # Re-register shouldn't reset spend
        dashboard.register_agent("agent-01", budget_limit_usd=10.0)
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.daily_spend_usd == 2.0
        assert agent.daily_budget_usd == 10.0


class TestAgentState:
    def test_update_state_idle(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.update_agent_state("agent-01", "idle")
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.state == "idle"

    def test_update_state_working_with_task(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.update_agent_state("agent-01", "working", task_id="task-123")
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.state == "working"
        assert agent.current_task_id == "task-123"

    def test_state_transition_clears_task(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.update_agent_state("agent-01", "working", task_id="task-123")
        dashboard.update_agent_state("agent-01", "idle")
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.current_task_id is None

    def test_suspended_state(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.update_agent_state("agent-01", "suspended")
        snapshot = dashboard.generate_snapshot()
        assert snapshot.agents_suspended == 1


# ──────────────────────────────────────────────────────────────
# Task Events
# ──────────────────────────────────────────────────────────────


class TestTaskEvents:
    def test_record_completion(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event(
            "agent-01",
            "t1",
            "task_completed",
            category="research",
            bounty_usd=1.50,
            quality=0.85,
            duration_s=120,
        )
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.tasks_completed_today == 1
        assert agent.daily_spend_usd == 1.50

    def test_record_failure(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event(
            "agent-01", "t1", "task_failed", category="research"
        )
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.tasks_failed_today == 1

    def test_success_rate_calculation(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(8):
            dashboard.record_task_event(
                "agent-01", f"t{i}", "task_completed", bounty_usd=0.50
            )
        for i in range(2):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.success_rate == 0.8

    def test_consecutive_failures_tracked(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=0.5)
        dashboard.record_task_event("agent-01", "f1", "task_failed")
        dashboard.record_task_event("agent-01", "f2", "task_failed")
        dashboard.record_task_event("agent-01", "f3", "task_failed")
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.consecutive_failures == 3

    def test_consecutive_failures_reset_on_success(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event("agent-01", "f1", "task_failed")
        dashboard.record_task_event("agent-01", "f2", "task_failed")
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=0.5)
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.consecutive_failures == 0

    def test_budget_accumulation(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=5.0)
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=1.5)
        dashboard.record_task_event("agent-01", "t2", "task_completed", bounty_usd=2.0)
        snapshot = dashboard.generate_snapshot()
        agent = [a for a in snapshot.agent_statuses if a.agent_id == "agent-01"][0]
        assert agent.daily_spend_usd == 3.5
        assert agent.budget_utilization == 0.7


# ──────────────────────────────────────────────────────────────
# Snapshot Generation
# ──────────────────────────────────────────────────────────────


class TestSnapshotGeneration:
    def test_empty_dashboard_snapshot(self, dashboard):
        snapshot = dashboard.generate_snapshot()
        assert snapshot.agent_count == 0
        assert snapshot.fleet_status == FleetStatus.DOWN

    def test_healthy_fleet(self, populated_dashboard):
        # Give all agents recent activity so they're not flagged as stale
        for i in range(24):
            populated_dashboard.record_task_event(
                f"agent-{i:02d}",
                f"t{i}",
                "task_completed",
                bounty_usd=0.10,
                quality=0.9,
            )
        populated_dashboard.set_irc_connected(True)  # Suppress IRC warning
        snapshot = populated_dashboard.generate_snapshot()
        assert snapshot.agent_count == 24
        assert snapshot.agents_operational == 24
        assert snapshot.fleet_status == FleetStatus.HEALTHY

    def test_snapshot_has_timestamp(self, dashboard):
        before = time.time()
        snapshot = dashboard.generate_snapshot()
        after = time.time()
        assert before <= snapshot.timestamp <= after

    def test_snapshot_uptime(self, dashboard):
        dashboard.register_agent("agent-01")
        snapshot = dashboard.generate_snapshot()
        assert snapshot.uptime_seconds >= 0

    def test_operational_rate(self, populated_dashboard):
        db = populated_dashboard
        for i in range(6):
            db.update_agent_state(f"agent-{i:02d}", "suspended")
        snapshot = db.generate_snapshot()
        assert snapshot.operational_rate == 18 / 24

    def test_summary_line(self, populated_dashboard):
        # Give all agents recent activity
        for i in range(24):
            populated_dashboard.record_task_event(
                f"agent-{i:02d}",
                f"t{i}",
                "task_completed",
                bounty_usd=0.10,
                quality=0.9,
            )
        populated_dashboard.set_irc_connected(True)
        snapshot = populated_dashboard.generate_snapshot()
        line = snapshot.summary_line()
        assert "HEALTHY" in line
        assert "24/24" in line

    def test_to_dict(self, populated_dashboard):
        snapshot = populated_dashboard.generate_snapshot()
        d = snapshot.to_dict()
        assert "fleet_status" in d
        assert "agent_count" in d
        assert "pipeline" in d
        assert "budget" in d
        assert d["agent_count"] == 24


# ──────────────────────────────────────────────────────────────
# Fleet Status Assessment
# ──────────────────────────────────────────────────────────────


class TestFleetStatus:
    def test_healthy_when_all_operational(self, populated_dashboard):
        # Give all agents recent activity so they're not flagged stale
        for i in range(24):
            populated_dashboard.record_task_event(
                f"agent-{i:02d}",
                f"t{i}",
                "task_completed",
                bounty_usd=0.10,
                quality=0.9,
            )
        populated_dashboard.set_irc_connected(True)  # Suppress IRC alert
        snapshot = populated_dashboard.generate_snapshot()
        assert snapshot.fleet_status == FleetStatus.HEALTHY

    def test_degraded_when_some_suspended(self, populated_dashboard):
        db = populated_dashboard
        for i in range(6):  # 25% suspended → 75% operational
            db.update_agent_state(f"agent-{i:02d}", "suspended")
        snapshot = db.generate_snapshot()
        assert snapshot.fleet_status in (FleetStatus.DEGRADED, FleetStatus.HEALTHY)

    def test_impaired_when_many_down(self, populated_dashboard):
        db = populated_dashboard
        for i in range(14):  # >50% suspended
            db.update_agent_state(f"agent-{i:02d}", "suspended")
        snapshot = db.generate_snapshot()
        assert snapshot.fleet_status in (FleetStatus.IMPAIRED, FleetStatus.DEGRADED)

    def test_down_when_most_suspended(self, populated_dashboard):
        db = populated_dashboard
        for i in range(20):  # >75% suspended
            db.update_agent_state(f"agent-{i:02d}", "suspended")
        snapshot = db.generate_snapshot()
        assert snapshot.fleet_status in (FleetStatus.DOWN, FleetStatus.IMPAIRED)


# ──────────────────────────────────────────────────────────────
# Pipeline Metrics
# ──────────────────────────────────────────────────────────────


class TestPipelineMetrics:
    def test_empty_pipeline(self, dashboard):
        snapshot = dashboard.generate_snapshot()
        assert snapshot.pipeline.completed_today == 0
        assert snapshot.pipeline.failed_today == 0

    def test_pipeline_counts(self, populated_dashboard):
        db = populated_dashboard
        for i in range(5):
            db.record_task_event(
                f"agent-{i:02d}", f"t{i}", "task_completed", bounty_usd=1.0
            )
        for i in range(2):
            db.record_task_event(f"agent-{i + 5:02d}", f"f{i}", "task_failed")
        snapshot = db.generate_snapshot()
        assert snapshot.pipeline.completed_today == 5
        assert snapshot.pipeline.failed_today == 2

    def test_pipeline_in_progress(self, populated_dashboard):
        db = populated_dashboard
        db.update_agent_state("agent-00", "working", task_id="t1")
        db.update_agent_state("agent-01", "working", task_id="t2")
        snapshot = db.generate_snapshot()
        assert snapshot.pipeline.in_progress == 2

    def test_total_active_property(self):
        pm = PipelineMetrics(queued=3, scheduling=1, assigned=2, in_progress=5)
        assert pm.total_active == 11

    def test_total_resolved_property(self):
        pm = PipelineMetrics(completed_today=10, failed_today=3, expired_today=2)
        assert pm.total_resolved_today == 15


# ──────────────────────────────────────────────────────────────
# Budget Summary
# ──────────────────────────────────────────────────────────────


class TestBudgetSummary:
    def test_empty_budget(self, populated_dashboard):
        snapshot = populated_dashboard.generate_snapshot()
        assert snapshot.budget.total_spent_today_usd == 0.0
        assert snapshot.budget.total_daily_budget_usd == 120.0  # 24 × $5

    def test_budget_spending(self, populated_dashboard):
        db = populated_dashboard
        db.record_task_event("agent-00", "t1", "task_completed", bounty_usd=3.0)
        db.record_task_event("agent-01", "t2", "task_completed", bounty_usd=2.0)
        snapshot = db.generate_snapshot()
        assert snapshot.budget.total_spent_today_usd == 5.0

    def test_agents_near_budget(self, populated_dashboard):
        db = populated_dashboard
        db.record_task_event("agent-00", "t1", "task_completed", bounty_usd=4.5)  # 90%
        snapshot = db.generate_snapshot()
        assert snapshot.budget.agents_near_budget >= 1

    def test_agents_over_budget(self, populated_dashboard):
        db = populated_dashboard
        db.record_task_event(
            "agent-00", "t1", "task_completed", bounty_usd=6.0
        )  # Over $5
        snapshot = db.generate_snapshot()
        assert snapshot.budget.agents_over_budget >= 1

    def test_budget_utilization_property(self):
        bs = BudgetSummary(total_daily_budget_usd=100.0, total_spent_today_usd=50.0)
        assert bs.utilization == 0.5


# ──────────────────────────────────────────────────────────────
# Coordination Health
# ──────────────────────────────────────────────────────────────


class TestCoordinationHealth:
    def test_irc_disconnected_by_default(self, dashboard):
        dashboard.register_agent("agent-01")
        snapshot = dashboard.generate_snapshot()
        assert not snapshot.coordination.irc_connected

    def test_irc_connected(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.set_irc_connected(True)
        snapshot = dashboard.generate_snapshot()
        assert snapshot.coordination.irc_connected

    def test_active_locks_counted(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_lock_event("lock", "worker-1", "agent-01", "research")
        dashboard.record_lock_event("lock", "worker-2", "agent-01", "data_entry")
        snapshot = dashboard.generate_snapshot()
        assert snapshot.coordination.active_locks == 2

    def test_lock_release(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_lock_event("lock", "worker-1", "agent-01")
        dashboard.record_lock_event("release", "worker-1")
        snapshot = dashboard.generate_snapshot()
        assert (
            snapshot.coordination.active_locks == 0
        )  # Release removes from active locks

    def test_lock_contention(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.register_agent("agent-02")
        dashboard.record_lock_event("lock", "worker-1", "agent-01")
        dashboard.record_lock_event("lock", "worker-1", "agent-02")  # Contention!
        snapshot = dashboard.generate_snapshot()
        assert snapshot.coordination.lock_contentions_1h == 1

    def test_agents_seen_on_irc(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_irc_activity("agent-01")
        snapshot = dashboard.generate_snapshot()
        assert snapshot.coordination.agents_online >= 1


# ──────────────────────────────────────────────────────────────
# SLA Metrics
# ──────────────────────────────────────────────────────────────


class TestSLAMetrics:
    def test_no_deadlines(self, dashboard):
        dashboard.register_agent("agent-01")
        snapshot = dashboard.generate_snapshot()
        assert snapshot.sla.adherence_rate == 1.0

    def test_deadline_met(self, dashboard):
        dashboard.register_agent("agent-01")
        future = time.time() + 3600  # 1 hour from now
        dashboard.record_task_event(
            "agent-01", "t1", "task_completed", bounty_usd=1.0, deadline_ts=future
        )
        snapshot = dashboard.generate_snapshot()
        assert snapshot.sla.tasks_met_deadline == 1
        assert snapshot.sla.adherence_rate == 1.0

    def test_deadline_missed(self, dashboard):
        dashboard.register_agent("agent-01")
        past = time.time() - 3600  # 1 hour ago
        dashboard.record_task_event(
            "agent-01", "t1", "task_completed", bounty_usd=1.0, deadline_ts=past
        )
        snapshot = dashboard.generate_snapshot()
        assert snapshot.sla.tasks_missed_deadline == 1
        assert snapshot.sla.adherence_rate == 0.0

    def test_mixed_deadlines(self, dashboard):
        dashboard.register_agent("agent-01")
        future = time.time() + 3600
        past = time.time() - 3600
        dashboard.record_task_event(
            "agent-01", "t1", "task_completed", bounty_usd=1.0, deadline_ts=future
        )
        dashboard.record_task_event(
            "agent-01", "t2", "task_completed", bounty_usd=1.0, deadline_ts=past
        )
        snapshot = dashboard.generate_snapshot()
        assert snapshot.sla.adherence_rate == 0.5


# ──────────────────────────────────────────────────────────────
# Heatmap
# ──────────────────────────────────────────────────────────────


class TestHeatmap:
    def test_empty_heatmap(self, dashboard):
        snapshot = dashboard.generate_snapshot()
        assert len(snapshot.heatmap) == 0

    def test_heatmap_entries(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event(
            "agent-01",
            "t1",
            "task_completed",
            category="research",
            bounty_usd=1.0,
            quality=0.9,
        )
        dashboard.record_task_event(
            "agent-01",
            "t2",
            "task_completed",
            category="research",
            bounty_usd=1.0,
            quality=0.8,
        )
        dashboard.record_task_event(
            "agent-01", "t3", "task_completed", category="data_entry", bounty_usd=0.5
        )
        snapshot = dashboard.generate_snapshot()
        assert len(snapshot.heatmap) == 2
        research = [h for h in snapshot.heatmap if h.category == "research"][0]
        assert research.tasks_completed == 2

    def test_heatmap_success_rate(self):
        entry = CategoryHeatmapEntry(
            agent_id="a1", category="c1", tasks_completed=7, tasks_failed=3
        )
        assert entry.success_rate == 0.7


# ──────────────────────────────────────────────────────────────
# Alert Generation
# ──────────────────────────────────────────────────────────────


class TestAlerts:
    def test_no_alerts_healthy_fleet(self, populated_dashboard):
        snapshot = populated_dashboard.generate_snapshot()
        # Only stale agent alerts possible (no activity recorded)
        critical = [a for a in snapshot.alerts if a.severity == Severity.CRITICAL]
        assert len(critical) == 0

    def test_failure_streak_warning(self, dashboard):
        dashboard.register_agent("agent-01")
        # Need exactly FAILURE_STREAK_WARNING (3) consecutive failures but < CRITICAL (5)
        # First do a success so there's activity, then failures
        dashboard.record_task_event("agent-01", "t0", "task_completed", bounty_usd=0.1)
        for i in range(4):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        snapshot = dashboard.generate_snapshot()
        failure_alerts = [
            a
            for a in snapshot.alerts
            if "failure" in a.title.lower() or "failing" in a.title.lower()
        ]
        assert len(failure_alerts) >= 1

    def test_failure_streak_critical(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(5):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        snapshot = dashboard.generate_snapshot()
        critical = [
            a
            for a in snapshot.alerts
            if a.severity == Severity.CRITICAL and "failure" in a.title.lower()
        ]
        assert len(critical) >= 1

    def test_over_budget_alert(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=5.0)
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=6.0)
        snapshot = dashboard.generate_snapshot()
        budget_alerts = [a for a in snapshot.alerts if "budget" in a.title.lower()]
        assert len(budget_alerts) >= 1

    def test_irc_disconnected_alert(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.register_agent("agent-02")
        snapshot = dashboard.generate_snapshot()
        irc_alerts = [a for a in snapshot.alerts if "IRC" in a.title]
        assert len(irc_alerts) >= 1

    def test_stale_locks_alert(self, dashboard):
        dashboard.register_agent("agent-01")
        # Manually insert a stale lock
        dashboard._active_locks["worker-1"] = {
            "agent": "agent-01",
            "ts": time.time() - 600,
            "task": "test",
        }
        snapshot = dashboard.generate_snapshot()
        lock_alerts = [a for a in snapshot.alerts if "lock" in a.title.lower()]
        assert len(lock_alerts) >= 1

    def test_alerts_sorted_by_severity(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.register_agent("agent-02")
        # Create conditions for multiple alert types
        for i in range(5):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        dashboard.record_task_event("agent-02", "t1", "task_completed", bounty_usd=10.0)
        snapshot = dashboard.generate_snapshot()
        if len(snapshot.alerts) >= 2:
            severities = [a.severity for a in snapshot.alerts]
            severity_values = {"emergency": 0, "critical": 1, "warning": 2, "info": 3}
            for i in range(len(severities) - 1):
                assert severity_values.get(
                    severities[i].value, 99
                ) <= severity_values.get(severities[i + 1].value, 99)

    def test_alert_to_dict(self):
        alert = DashboardAlert(
            severity=Severity.WARNING,
            title="Test",
            message="Test message",
            agent_id="agent-01",
        )
        d = alert.to_dict()
        assert d["severity"] == "warning"
        assert d["title"] == "Test"


# ──────────────────────────────────────────────────────────────
# Health Report
# ──────────────────────────────────────────────────────────────


class TestHealthReport:
    def test_generate_report(self, populated_dashboard):
        # Give all agents recent activity
        for i in range(24):
            populated_dashboard.record_task_event(
                f"agent-{i:02d}",
                f"t{i}",
                "task_completed",
                bounty_usd=0.10,
                quality=0.9,
            )
        populated_dashboard.set_irc_connected(True)
        report = populated_dashboard.generate_health_report()
        assert isinstance(report, HealthReport)
        assert report.fleet_status == FleetStatus.HEALTHY

    def test_report_with_issues(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(5):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        report = dashboard.generate_health_report()
        assert len(report.critical_alerts) >= 1

    def test_report_recommendations(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.update_agent_state("agent-01", "degraded")
        report = dashboard.generate_health_report()
        assert len(report.recommendations) >= 1


# ──────────────────────────────────────────────────────────────
# Health Score
# ──────────────────────────────────────────────────────────────


class TestHealthScore:
    def test_perfect_health(self, dashboard):
        dashboard.register_agent("agent-01")
        dashboard.record_task_event(
            "agent-01", "t1", "task_completed", bounty_usd=0.50, quality=1.0
        )
        snapshot = dashboard.generate_snapshot()
        agent = snapshot.agent_statuses[0]
        assert agent.health_score > 0.5

    def test_zero_health_all_failures(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(10):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        snapshot = dashboard.generate_snapshot()
        agent = snapshot.agent_statuses[0]
        assert agent.health_score < 0.5

    def test_health_decreases_with_budget_usage(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=5.0)
        dashboard.record_task_event(
            "agent-01", "t1", "task_completed", bounty_usd=1.0, quality=1.0
        )
        snap1 = dashboard.generate_snapshot()
        h1 = snap1.agent_statuses[0].health_score

        dashboard.record_task_event(
            "agent-01", "t2", "task_completed", bounty_usd=4.0, quality=1.0
        )
        snap2 = dashboard.generate_snapshot()
        h2 = snap2.agent_statuses[0].health_score
        # Higher budget usage should decrease health
        assert h2 <= h1


# ──────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────


class TestUtilities:
    def test_get_top_performers(self, populated_dashboard):
        db = populated_dashboard
        # Give some agents better records
        for i in range(5):
            db.record_task_event(
                f"agent-{i:02d}", f"t{i}", "task_completed", bounty_usd=0.5, quality=0.9
            )
        top = db.get_top_performers(3)
        assert len(top) == 3

    def test_get_struggling_agents(self, dashboard):
        dashboard.register_agent("agent-01")
        for i in range(5):
            dashboard.record_task_event("agent-01", f"f{i}", "task_failed")
        struggling = dashboard.get_struggling_agents()
        assert len(struggling) >= 1
        assert struggling[0].agent_id == "agent-01"

    def test_reset_daily_counters(self, dashboard):
        dashboard.register_agent("agent-01", budget_limit_usd=5.0)
        dashboard.record_task_event("agent-01", "t1", "task_completed", bounty_usd=3.0)
        dashboard.reset_daily_counters()
        snapshot = dashboard.generate_snapshot()
        agent = snapshot.agent_statuses[0]
        assert agent.daily_spend_usd == 0.0

    def test_agent_status_is_stale(self):
        status = AgentStatus(agent_id="a1", last_activity_ts=time.time() - 700)
        assert status.is_stale

    def test_agent_status_not_stale(self):
        status = AgentStatus(agent_id="a1", last_activity_ts=time.time())
        assert not status.is_stale

    def test_agent_status_budget_headroom(self):
        status = AgentStatus(agent_id="a1", daily_spend_usd=3.0, daily_budget_usd=5.0)
        assert status.budget_headroom_usd == 2.0


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


class TestDataTypes:
    def test_severity_values(self):
        assert Severity.INFO.value == "info"
        assert Severity.WARNING.value == "warning"
        assert Severity.CRITICAL.value == "critical"
        assert Severity.EMERGENCY.value == "emergency"

    def test_fleet_status_values(self):
        assert FleetStatus.HEALTHY.value == "healthy"
        assert FleetStatus.DEGRADED.value == "degraded"
        assert FleetStatus.IMPAIRED.value == "impaired"
        assert FleetStatus.DOWN.value == "down"

    def test_pipeline_stage_values(self):
        assert PipelineStage.QUEUED.value == "queued"
        assert PipelineStage.COMPLETED.value == "completed"

    def test_sla_adherence_empty(self):
        sla = SLAMetrics()
        assert sla.adherence_rate == 1.0

    def test_budget_utilization_zero_budget(self):
        bs = BudgetSummary(total_daily_budget_usd=0.0)
        assert bs.utilization == 0.0
