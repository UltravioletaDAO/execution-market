"""
SwarmDashboard Test Suite
=========================

Comprehensive tests for the real-time fleet health monitoring dashboard.

Coverage:
- Data types (AgentStatus, PipelineMetrics, BudgetSummary, etc.)
- Agent registration and state management
- Task event recording and daily tracking
- Snapshot generation (pipeline, budget, coordination, SLA)
- Health score computation (weighted composite)
- Alert generation (per-agent + fleet-wide, severity ordering)
- Fleet status assessment (HEALTHY → DOWN)
- Coordination health (locks, IRC, contention)
- Category heatmap generation
- Health report generation (condensed notifications)
- Utilities (top performers, struggling agents, daily reset)
"""

import time
import pytest

from mcp_server.swarm.dashboard import (
    AgentStatus,
    PipelineMetrics,
    BudgetSummary,
    CategoryHeatmapEntry,
    DashboardAlert,
    SLAMetrics,
    DashboardSnapshot,
    HealthReport,
    Severity,
    FleetStatus,
    PipelineStage,
    SwarmDashboard,
    _today_start_ts,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


@pytest.fixture
def dashboard():
    """Fresh dashboard instance."""
    return SwarmDashboard()


@pytest.fixture
def populated_dashboard():
    """Dashboard with 5 registered agents and some events."""
    d = SwarmDashboard()
    for i in range(5):
        d.register_agent(
            f"agent_{i}",
            budget_limit_usd=10.0,
            specializations=[f"skill_{i}", "general"],
        )
        d.update_agent_state(f"agent_{i}", "idle")

    # Record some task events
    for i in range(3):
        d.record_task_event(
            agent_id="agent_0",
            task_id=f"task_{i}",
            event_type="task_completed",
            category="delivery",
            bounty_usd=2.0,
            quality=4.0,
            duration_s=3600,
        )
    d.record_task_event(
        agent_id="agent_1",
        task_id="fail_1",
        event_type="task_failed",
        category="verification",
    )
    d.record_task_event(
        agent_id="agent_1",
        task_id="complete_1",
        event_type="task_completed",
        category="verification",
        bounty_usd=3.0,
        quality=3.5,
        duration_s=7200,
    )
    return d


# ──────────────────────────────────────────────────────────────
# Section 1: Data Type Properties (12 tests)
# ──────────────────────────────────────────────────────────────


class TestDataTypes:
    """Computed properties on dashboard data types."""

    def test_agent_status_stale_true(self):
        s = AgentStatus(agent_id="a1", last_activity_ts=time.time() - 700)
        assert s.is_stale is True

    def test_agent_status_stale_false_recent(self):
        s = AgentStatus(agent_id="a1", last_activity_ts=time.time() - 100)
        assert s.is_stale is False

    def test_agent_status_stale_never_active(self):
        s = AgentStatus(agent_id="a1", last_activity_ts=0.0)
        assert s.is_stale is True

    def test_agent_status_budget_headroom(self):
        s = AgentStatus(agent_id="a1", daily_budget_usd=10.0, daily_spend_usd=3.0)
        assert s.budget_headroom_usd == 7.0

    def test_agent_status_budget_headroom_over(self):
        s = AgentStatus(agent_id="a1", daily_budget_usd=5.0, daily_spend_usd=8.0)
        assert s.budget_headroom_usd == 0

    def test_pipeline_metrics_total_active(self):
        p = PipelineMetrics(queued=5, scheduling=2, assigned=3, in_progress=4)
        assert p.total_active == 14

    def test_pipeline_metrics_total_resolved(self):
        p = PipelineMetrics(completed_today=10, failed_today=3, expired_today=2)
        assert p.total_resolved_today == 15

    def test_budget_summary_utilization(self):
        b = BudgetSummary(total_daily_budget_usd=100.0, total_spent_today_usd=60.0)
        assert abs(b.utilization - 0.6) < 0.001

    def test_budget_summary_utilization_zero(self):
        b = BudgetSummary(total_daily_budget_usd=0.0)
        assert b.utilization == 0.0

    def test_category_heatmap_entry_success_rate(self):
        e = CategoryHeatmapEntry(
            agent_id="a1", category="delivery", tasks_completed=8, tasks_failed=2
        )
        assert abs(e.success_rate - 0.8) < 0.001

    def test_category_heatmap_entry_no_tasks(self):
        e = CategoryHeatmapEntry(agent_id="a1", category="delivery")
        assert e.success_rate == 0.0

    def test_sla_adherence_rate(self):
        s = SLAMetrics(tasks_met_deadline=9, tasks_missed_deadline=1)
        assert abs(s.adherence_rate - 0.9) < 0.001

    def test_sla_no_deadlines(self):
        s = SLAMetrics()
        assert s.adherence_rate == 1.0


# ──────────────────────────────────────────────────────────────
# Section 2: Dashboard Snapshot Properties (6 tests)
# ──────────────────────────────────────────────────────────────


class TestDashboardSnapshot:
    """DashboardSnapshot computed properties and serialization."""

    def test_operational_rate(self):
        snap = DashboardSnapshot(agent_count=10, agents_operational=8)
        assert abs(snap.operational_rate - 0.8) < 0.001

    def test_operational_rate_zero_agents(self):
        snap = DashboardSnapshot(agent_count=0)
        assert snap.operational_rate == 0.0

    def test_summary_line(self):
        snap = DashboardSnapshot(
            fleet_status=FleetStatus.HEALTHY,
            agent_count=24,
            agents_operational=22,
            pipeline=PipelineMetrics(completed_today=50, failed_today=3),
            budget=BudgetSummary(total_spent_today_usd=45.0),
        )
        line = snap.summary_line()
        assert "HEALTHY" in line
        assert "22/24" in line
        assert "50 done" in line

    def test_to_dict(self):
        snap = DashboardSnapshot(
            fleet_status=FleetStatus.DEGRADED,
            agent_count=5,
            agents_operational=3,
        )
        d = snap.to_dict()
        assert d["fleet_status"] == "degraded"
        assert d["agent_count"] == 5
        assert "pipeline" in d
        assert "budget" in d

    def test_alert_to_dict(self):
        alert = DashboardAlert(
            severity=Severity.CRITICAL,
            title="Test",
            message="Something broke",
            agent_id="a1",
        )
        d = alert.to_dict()
        assert d["severity"] == "critical"
        assert d["title"] == "Test"

    def test_enums(self):
        assert FleetStatus.HEALTHY.value == "healthy"
        assert Severity.EMERGENCY.value == "emergency"
        assert PipelineStage.QUEUED.value == "queued"


# ──────────────────────────────────────────────────────────────
# Section 3: Agent Registration & State (8 tests)
# ──────────────────────────────────────────────────────────────


class TestAgentManagement:
    """Agent registration and lifecycle state updates."""

    def test_register_agent(self, dashboard):
        dashboard.register_agent(
            "a1", budget_limit_usd=5.0, specializations=["delivery"]
        )
        assert "a1" in dashboard.get_agent_ids()

    def test_register_multiple_agents(self, dashboard):
        for i in range(5):
            dashboard.register_agent(f"agent_{i}")
        assert len(dashboard.get_agent_ids()) == 5

    def test_update_agent_state(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "working", task_id="t1")
        assert dashboard._agent_states["a1"] == "working"
        assert dashboard._agent_tasks["a1"] == "t1"

    def test_state_idle_clears_task(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "working", task_id="t1")
        dashboard.update_agent_state("a1", "idle")
        assert dashboard._agent_tasks["a1"] is None

    def test_state_suspended_clears_task(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "working", task_id="t1")
        dashboard.update_agent_state("a1", "suspended")
        assert dashboard._agent_tasks["a1"] is None

    def test_budget_tracking(self, dashboard):
        dashboard.register_agent("a1", budget_limit_usd=10.0)
        dashboard.record_task_event("a1", "t1", "task_completed", bounty_usd=3.0)
        dashboard.record_task_event("a1", "t2", "task_completed", bounty_usd=2.0)
        spent, limit = dashboard._agent_budgets["a1"]
        assert spent == 5.0
        assert limit == 10.0

    def test_register_preserves_existing_spend(self, dashboard):
        dashboard.register_agent("a1", budget_limit_usd=10.0)
        dashboard.record_task_event("a1", "t1", "task_completed", bounty_usd=3.0)
        # Re-register with new budget limit
        dashboard.register_agent("a1", budget_limit_usd=20.0)
        spent, limit = dashboard._agent_budgets["a1"]
        assert spent == 3.0  # Preserved
        assert limit == 20.0  # Updated

    def test_specializations_stored(self, dashboard):
        dashboard.register_agent("a1", specializations=["photo", "delivery"])
        assert dashboard._agent_specializations["a1"] == ["photo", "delivery"]


# ──────────────────────────────────────────────────────────────
# Section 4: Snapshot Generation (10 tests)
# ──────────────────────────────────────────────────────────────


class TestSnapshotGeneration:
    """Full snapshot generation from dashboard state."""

    def test_empty_snapshot(self, dashboard):
        snap = dashboard.generate_snapshot()
        assert snap.agent_count == 0
        assert snap.fleet_status == FleetStatus.DOWN  # No agents = down

    def test_snapshot_agent_counts(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        assert snap.agent_count == 5

    def test_snapshot_pipeline_completed(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        assert snap.pipeline.completed_today >= 4  # 3 from agent_0, 1 from agent_1

    def test_snapshot_pipeline_failed(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        assert snap.pipeline.failed_today >= 1  # 1 from agent_1

    def test_snapshot_budget_tracking(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        assert snap.budget.total_spent_today_usd >= 9.0  # 3×2 + 1×3
        assert snap.budget.total_daily_budget_usd == 50.0  # 5 agents × $10

    def test_snapshot_uptime(self, dashboard):
        dashboard.register_agent("a1")
        time.sleep(0.01)  # Small delay
        snap = dashboard.generate_snapshot()
        assert snap.uptime_seconds > 0

    def test_snapshot_working_agents(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "working", task_id="t1")
        snap = dashboard.generate_snapshot()
        assert snap.agents_working == 1

    def test_snapshot_degraded_agents(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "degraded")
        snap = dashboard.generate_snapshot()
        assert snap.agents_degraded == 1

    def test_snapshot_suspended_agents(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "suspended")
        snap = dashboard.generate_snapshot()
        assert snap.agents_suspended == 1

    def test_snapshot_in_progress_count(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.register_agent("a2")
        dashboard.update_agent_state("a1", "working", task_id="t1")
        dashboard.update_agent_state("a2", "working", task_id="t2")
        snap = dashboard.generate_snapshot()
        assert snap.pipeline.in_progress == 2


# ──────────────────────────────────────────────────────────────
# Section 5: Health Score Computation (7 tests)
# ──────────────────────────────────────────────────────────────


class TestHealthScore:
    """Agent health score computation."""

    def test_perfect_agent(self, dashboard):
        """100% success, fresh, no failures, headroom → high score."""
        score = dashboard._compute_health_score(
            success_rate=1.0,
            budget_util=0.2,
            consecutive_failures=0,
            now=time.time(),
            last_activity=time.time() - 10,  # Just active
        )
        assert score > 0.8

    def test_terrible_agent(self, dashboard):
        """0% success, over budget, stale, many failures → low score."""
        score = dashboard._compute_health_score(
            success_rate=0.0,
            budget_util=1.0,
            consecutive_failures=6,
            now=time.time(),
            last_activity=time.time() - 100000,  # Very stale
        )
        assert score < 0.1

    def test_staleness_penalty(self, dashboard):
        now = time.time()
        recent = dashboard._compute_health_score(1.0, 0.0, 0, now, now - 10)
        stale = dashboard._compute_health_score(1.0, 0.0, 0, now, now - 10000)
        assert recent > stale

    def test_failure_streak_penalty(self, dashboard):
        now = time.time()
        no_fails = dashboard._compute_health_score(0.8, 0.3, 0, now, now - 10)
        some_fails = dashboard._compute_health_score(0.8, 0.3, 3, now, now - 10)
        many_fails = dashboard._compute_health_score(0.8, 0.3, 5, now, now - 10)
        assert no_fails > some_fails > many_fails

    def test_budget_penalty(self, dashboard):
        now = time.time()
        low_util = dashboard._compute_health_score(0.8, 0.1, 0, now, now - 10)
        high_util = dashboard._compute_health_score(0.8, 0.9, 0, now, now - 10)
        assert low_util > high_util

    def test_score_bounded(self, dashboard):
        """Score always between 0 and 1."""
        now = time.time()
        score = dashboard._compute_health_score(1.0, 0.0, 0, now, now)
        assert 0.0 <= score <= 1.0

        score = dashboard._compute_health_score(0.0, 1.0, 10, now, 0.0)
        assert 0.0 <= score <= 1.0

    def test_never_active_zero_freshness(self, dashboard):
        score = dashboard._compute_health_score(0.8, 0.3, 0, time.time(), 0.0)
        # With last_activity=0, freshness component should be 0
        # Score = 0.8*0.4 + 0.7*0.2 + 0*0.2 + 1.0*0.2 = 0.32 + 0.14 + 0 + 0.2 = 0.66
        assert 0.5 < score < 0.8


# ──────────────────────────────────────────────────────────────
# Section 6: Alert Generation (11 tests)
# ──────────────────────────────────────────────────────────────


class TestAlertGeneration:
    """Alert system for various conditions."""

    def test_no_alerts_healthy(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "idle")
        dashboard.record_task_event(
            "a1", "t1", "task_completed", bounty_usd=1.0, quality=4.0, duration_s=1800
        )
        snap = dashboard.generate_snapshot()
        # A single healthy agent shouldn't trigger critical alerts
        critical = [
            a
            for a in snap.alerts
            if a.severity in (Severity.CRITICAL, Severity.EMERGENCY)
        ]
        assert len(critical) == 0

    def test_failure_streak_warning(self, dashboard):
        dashboard.register_agent("a1")
        for i in range(3):
            dashboard.record_task_event("a1", f"f{i}", "task_failed")
        snap = dashboard.generate_snapshot()
        streak_alerts = [
            a
            for a in snap.alerts
            if "failure streak" in a.title.lower() or "failing" in a.title.lower()
        ]
        assert len(streak_alerts) >= 1

    def test_failure_streak_critical(self, dashboard):
        dashboard.register_agent("a1")
        for i in range(5):
            dashboard.record_task_event("a1", f"f{i}", "task_failed")
        snap = dashboard.generate_snapshot()
        critical = [
            a
            for a in snap.alerts
            if a.severity == Severity.CRITICAL and "failure" in a.title.lower()
        ]
        assert len(critical) >= 1

    def test_over_budget_alert(self, dashboard):
        dashboard.register_agent("a1", budget_limit_usd=5.0)
        for i in range(4):
            dashboard.record_task_event("a1", f"t{i}", "task_completed", bounty_usd=2.0)
        snap = dashboard.generate_snapshot()
        budget_alerts = [a for a in snap.alerts if "budget" in a.title.lower()]
        assert len(budget_alerts) >= 1

    def test_stale_agent_alert(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "active")
        # Force old activity timestamp
        dashboard._agent_events["a1"].append(
            {
                "agent_id": "a1",
                "task_id": "old",
                "event_type": "task_completed",
                "category": "",
                "bounty_usd": 0,
                "quality": 0,
                "duration_s": 0,
                "timestamp": time.time() - 2000,  # Way past stale timeout
            }
        )
        snap = dashboard.generate_snapshot()
        stale_alerts = [a for a in snap.alerts if "unresponsive" in a.title.lower()]
        assert len(stale_alerts) >= 1

    def test_stale_agent_not_triggered_for_suspended(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "suspended")
        snap = dashboard.generate_snapshot()
        stale_alerts = [a for a in snap.alerts if "unresponsive" in a.title.lower()]
        assert len(stale_alerts) == 0

    def test_irc_offline_alert(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.register_agent("a2")
        dashboard.set_irc_connected(False)
        snap = dashboard.generate_snapshot()
        irc_alerts = [a for a in snap.alerts if "irc" in a.title.lower()]
        assert len(irc_alerts) >= 1

    def test_sla_warning(self, dashboard):
        dashboard.register_agent("a1")
        # 85% adherence → warning
        for i in range(17):
            dashboard._deadline_results.append({"met": True, "margin_s": 300})
        for i in range(3):
            dashboard._deadline_results.append({"met": False, "margin_s": -600})
        snap = dashboard.generate_snapshot()
        sla_alerts = [a for a in snap.alerts if "sla" in a.title.lower()]
        assert len(sla_alerts) >= 1

    def test_high_expiry_alert(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.record_task_event("a1", "c1", "task_completed")
        for i in range(5):
            dashboard.record_task_event("a1", f"e{i}", "task_expired")
        snap = dashboard.generate_snapshot()
        expiry_alerts = [a for a in snap.alerts if "expiry" in a.title.lower()]
        assert len(expiry_alerts) >= 1

    def test_alerts_sorted_by_severity(self, dashboard):
        """Emergency/critical before warning/info."""
        dashboard.register_agent("a1", budget_limit_usd=1.0)
        # Trigger multiple alert types
        for i in range(6):
            dashboard.record_task_event("a1", f"f{i}", "task_failed")
        dashboard.record_task_event("a1", "c1", "task_completed", bounty_usd=5.0)
        snap = dashboard.generate_snapshot()
        if len(snap.alerts) >= 2:
            severities = [a.severity for a in snap.alerts]
            severity_order = {
                Severity.EMERGENCY: 0,
                Severity.CRITICAL: 1,
                Severity.WARNING: 2,
                Severity.INFO: 3,
            }
            indices = [severity_order[s] for s in severities]
            assert indices == sorted(indices)

    def test_stale_locks_alert(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.record_lock_event("lock", "worker_1", "a1")
        # Force stale
        dashboard._active_locks["worker_1"]["ts"] = time.time() - 400
        snap = dashboard.generate_snapshot()
        lock_alerts = [a for a in snap.alerts if "lock" in a.title.lower()]
        assert len(lock_alerts) >= 1


# ──────────────────────────────────────────────────────────────
# Section 7: Fleet Status Assessment (5 tests)
# ──────────────────────────────────────────────────────────────


class TestFleetStatus:
    """Overall fleet health status determination."""

    def test_healthy_fleet(self, dashboard):
        for i in range(10):
            dashboard.register_agent(f"a{i}")
            dashboard.update_agent_state(f"a{i}", "idle")
        snap = dashboard.generate_snapshot()
        assert snap.fleet_status in (FleetStatus.HEALTHY, FleetStatus.DEGRADED)

    def test_down_no_agents(self, dashboard):
        snap = dashboard.generate_snapshot()
        assert snap.fleet_status == FleetStatus.DOWN

    def test_impaired_few_operational(self, dashboard):
        for i in range(10):
            dashboard.register_agent(f"a{i}")
            # 4 operational, 6 suspended
            if i < 4:
                dashboard.update_agent_state(f"a{i}", "idle")
            else:
                dashboard.update_agent_state(f"a{i}", "suspended")
        snap = dashboard.generate_snapshot()
        assert snap.fleet_status in (FleetStatus.IMPAIRED, FleetStatus.DEGRADED)

    def test_degraded_some_warnings(self, dashboard):
        """With only warnings and >80% operational → DEGRADED."""
        for i in range(5):
            dashboard.register_agent(f"a{i}")
            dashboard.update_agent_state(f"a{i}", "idle")
        dashboard.set_irc_connected(False)  # Triggers warning
        snap = dashboard.generate_snapshot()
        assert snap.fleet_status == FleetStatus.DEGRADED

    def test_status_downgrades_with_critical(self, dashboard):
        for i in range(4):
            dashboard.register_agent(f"a{i}", budget_limit_usd=1.0)
            dashboard.update_agent_state(f"a{i}", "idle")
            # All over budget
            dashboard.record_task_event(
                f"a{i}", f"t{i}", "task_completed", bounty_usd=5.0
            )
        snap = dashboard.generate_snapshot()
        # With all agents over budget → budget crisis → IMPAIRED or worse
        assert snap.fleet_status != FleetStatus.HEALTHY


# ──────────────────────────────────────────────────────────────
# Section 8: Coordination Health (7 tests)
# ──────────────────────────────────────────────────────────────


class TestCoordinationHealth:
    """Lock tracking, IRC monitoring, contention detection."""

    def test_lock_tracking(self, dashboard):
        dashboard.record_lock_event("lock", "worker_1", "agent_1")
        assert len(dashboard._active_locks) == 1

    def test_lock_release(self, dashboard):
        dashboard.record_lock_event("lock", "worker_1", "agent_1")
        dashboard.record_lock_event("release", "worker_1", "agent_1")
        assert len(dashboard._active_locks) == 0

    def test_lock_contention(self, dashboard):
        dashboard.record_lock_event("lock", "worker_1", "agent_1")
        dashboard.record_lock_event("lock", "worker_1", "agent_2")
        assert dashboard._contention_count_1h == 1

    def test_irc_activity(self, dashboard):
        dashboard.record_irc_activity("agent_1")
        dashboard.record_irc_activity("agent_2")
        assert "agent_1" in dashboard._agents_seen_irc
        assert "agent_2" in dashboard._agents_seen_irc

    def test_coordination_in_snapshot(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.set_irc_connected(True)
        dashboard.record_irc_activity("a1")
        dashboard.record_lock_event("lock", "w1", "a1")
        snap = dashboard.generate_snapshot()
        assert snap.coordination.irc_connected is True
        assert snap.coordination.active_locks == 1
        assert snap.coordination.agents_online >= 1

    def test_message_rate(self, dashboard):
        dashboard.register_agent("a1")
        for i in range(10):
            dashboard.record_irc_activity("a1")
        snap = dashboard.generate_snapshot()
        assert snap.coordination.message_rate_per_min >= 10

    def test_stale_lock_detection(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.record_lock_event("lock", "w1", "a1")
        # Make it stale
        dashboard._active_locks["w1"]["ts"] = time.time() - 400
        snap = dashboard.generate_snapshot()
        assert snap.coordination.stale_locks == 1


# ──────────────────────────────────────────────────────────────
# Section 9: SLA Tracking (5 tests)
# ──────────────────────────────────────────────────────────────


class TestSLATracking:
    """Deadline adherence tracking."""

    def test_no_deadlines(self, dashboard):
        dashboard.register_agent("a1")
        snap = dashboard.generate_snapshot()
        assert snap.sla.adherence_rate == 1.0  # Default

    def test_deadline_met(self, dashboard):
        dashboard.register_agent("a1")
        # Complete before deadline
        future_deadline = time.time() + 3600
        dashboard.record_task_event(
            "a1", "t1", "task_completed", deadline_ts=future_deadline
        )
        snap = dashboard.generate_snapshot()
        assert snap.sla.tasks_met_deadline == 1
        assert snap.sla.tasks_missed_deadline == 0

    def test_deadline_missed(self, dashboard):
        dashboard.register_agent("a1")
        # Complete AFTER deadline (past)
        past_deadline = time.time() - 3600
        dashboard.record_task_event(
            "a1", "t1", "task_completed", deadline_ts=past_deadline
        )
        snap = dashboard.generate_snapshot()
        assert snap.sla.tasks_missed_deadline == 1

    def test_sla_adherence_mixed(self, dashboard):
        dashboard.register_agent("a1")
        future = time.time() + 3600
        past = time.time() - 3600
        # 3 met, 1 missed = 75%
        for i in range(3):
            dashboard.record_task_event(
                "a1", f"m{i}", "task_completed", deadline_ts=future
            )
        dashboard.record_task_event("a1", "miss", "task_completed", deadline_ts=past)
        snap = dashboard.generate_snapshot()
        assert abs(snap.sla.adherence_rate - 0.75) < 0.001

    def test_sla_failed_tasks_count(self, dashboard):
        dashboard.register_agent("a1")
        past = time.time() - 3600
        dashboard.record_task_event("a1", "t1", "task_failed", deadline_ts=past)
        snap = dashboard.generate_snapshot()
        assert snap.sla.total_tasks_with_deadline == 1


# ──────────────────────────────────────────────────────────────
# Section 10: Heatmap Generation (4 tests)
# ──────────────────────────────────────────────────────────────


class TestHeatmap:
    """Per-agent × per-category performance heatmap."""

    def test_empty_heatmap(self, dashboard):
        snap = dashboard.generate_snapshot()
        assert snap.heatmap == []

    def test_heatmap_with_data(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        assert len(snap.heatmap) > 0
        for entry in snap.heatmap:
            assert hasattr(entry, "agent_id")
            assert hasattr(entry, "category")

    def test_heatmap_sorted(self, populated_dashboard):
        snap = populated_dashboard.generate_snapshot()
        keys = [(e.agent_id, e.category) for e in snap.heatmap]
        assert keys == sorted(keys)

    def test_heatmap_quality_tracking(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.record_task_event(
            "a1",
            "t1",
            "task_completed",
            category="delivery",
            quality=4.0,
            duration_s=1800,
        )
        dashboard.record_task_event(
            "a1",
            "t2",
            "task_completed",
            category="delivery",
            quality=5.0,
            duration_s=1200,
        )
        snap = dashboard.generate_snapshot()
        delivery_entries = [e for e in snap.heatmap if e.category == "delivery"]
        assert len(delivery_entries) == 1
        assert delivery_entries[0].tasks_completed == 2
        assert delivery_entries[0].avg_quality > 0


# ──────────────────────────────────────────────────────────────
# Section 11: Health Report (4 tests)
# ──────────────────────────────────────────────────────────────


class TestHealthReport:
    """Condensed health report generation."""

    def test_health_report_structure(self, populated_dashboard):
        report = populated_dashboard.generate_health_report()
        assert isinstance(report, HealthReport)
        assert report.fleet_status in FleetStatus
        assert isinstance(report.summary, str)
        assert isinstance(report.critical_alerts, list)
        assert isinstance(report.recommendations, list)

    def test_health_report_degraded_recommendation(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.update_agent_state("a1", "degraded")
        report = dashboard.generate_health_report()
        has_degraded_rec = any("degraded" in r.lower() for r in report.recommendations)
        assert has_degraded_rec

    def test_health_report_budget_recommendation(self, dashboard):
        dashboard.register_agent("a1", budget_limit_usd=1.0)
        dashboard.record_task_event("a1", "t1", "task_completed", bounty_usd=5.0)
        report = dashboard.generate_health_report()
        has_budget_rec = any("budget" in r.lower() for r in report.recommendations)
        assert has_budget_rec

    def test_health_report_stale_lock_recommendation(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.record_lock_event("lock", "w1", "a1")
        dashboard._active_locks["w1"]["ts"] = time.time() - 400
        report = dashboard.generate_health_report()
        has_lock_rec = any("lock" in r.lower() for r in report.recommendations)
        assert has_lock_rec


# ──────────────────────────────────────────────────────────────
# Section 12: Utilities (6 tests)
# ──────────────────────────────────────────────────────────────


class TestUtilities:
    """Helper methods and daily operations."""

    def test_get_agent_ids(self, populated_dashboard):
        ids = populated_dashboard.get_agent_ids()
        assert len(ids) == 5
        assert ids == sorted(ids)

    def test_top_performers(self, populated_dashboard):
        top = populated_dashboard.get_top_performers(n=3)
        assert len(top) <= 3
        for agent in top:
            assert isinstance(agent, AgentStatus)

    def test_struggling_agents(self, dashboard):
        dashboard.register_agent("a1")
        for i in range(5):
            dashboard.record_task_event("a1", f"f{i}", "task_failed")
        struggling = dashboard.get_struggling_agents()
        assert len(struggling) >= 1

    def test_reset_daily_counters(self, populated_dashboard):
        populated_dashboard.reset_daily_counters()
        for agent_id in populated_dashboard.get_agent_ids():
            spent, _ = populated_dashboard._agent_budgets[agent_id]
            assert spent == 0.0

    def test_today_start_ts(self):
        ts = _today_start_ts()
        assert ts > 0
        assert ts < time.time()

    def test_consecutive_failure_tracking(self, dashboard):
        dashboard.register_agent("a1")
        dashboard.record_task_event("a1", "c1", "task_completed")
        dashboard.record_task_event("a1", "f1", "task_failed")
        dashboard.record_task_event("a1", "f2", "task_failed")
        snap = dashboard.generate_snapshot()
        agent = next(a for a in snap.agent_statuses if a.agent_id == "a1")
        assert agent.consecutive_failures == 2
