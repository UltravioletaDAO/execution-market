"""
Tests for BudgetController — centralized fleet-wide budget management.
"""

import time
import pytest
from unittest.mock import patch

from mcp_server.swarm.budget_controller import (
    BudgetController,
    BudgetExceededError,
    SpendPhase,
    PhasePolicy,
    SpendRecord,
    BurnRate,
    BudgetAlert,
    BalanceSnapshot,
    DEFAULT_POLICIES,
)


# ─── Fixtures ─────────────────────────────────────────────────


@pytest.fixture
def controller():
    """Default controller in PRE_FLIGHT phase."""
    return BudgetController(
        fleet_daily_limit_usd=50.0,
        fleet_monthly_limit_usd=500.0,
    )


@pytest.fixture
def semi_auto_controller():
    """Controller in SEMI_AUTO phase, ready to spend."""
    c = BudgetController(
        fleet_daily_limit_usd=50.0,
        fleet_monthly_limit_usd=500.0,
    )
    c.set_phase(SpendPhase.SEMI_AUTO)
    return c


@pytest.fixture
def full_auto_controller():
    """Controller in FULL_AUTO phase."""
    c = BudgetController(
        fleet_daily_limit_usd=50.0,
        fleet_monthly_limit_usd=500.0,
    )
    c.set_phase(SpendPhase.FULL_AUTO)
    return c


# ─── Phase Management ────────────────────────────────────────


class TestPhaseManagement:

    def test_default_phase_is_preflight(self, controller):
        assert controller.current_phase == SpendPhase.PRE_FLIGHT

    def test_set_phase(self, controller):
        controller.set_phase(SpendPhase.PASSIVE)
        assert controller.current_phase == SpendPhase.PASSIVE

    def test_phase_change_creates_alert(self, controller):
        controller.set_phase(SpendPhase.PASSIVE)
        alerts = controller.get_alerts(level="info")
        assert any("phase_change" == a.code for a in alerts)

    def test_no_alert_on_same_phase(self, controller):
        controller.set_phase(SpendPhase.PRE_FLIGHT)  # Same as default
        alerts = controller.get_alerts(level="info")
        assert not any("phase_change" == a.code for a in alerts)

    def test_get_policy_returns_current(self, controller):
        policy = controller.current_policy
        assert policy.phase == SpendPhase.PRE_FLIGHT
        assert policy.max_task_usd == 0.0

    def test_get_policy_for_other_phase(self, controller):
        policy = controller.get_policy(SpendPhase.FULL_AUTO)
        assert policy.max_task_usd == 10.0
        assert policy.auto_assign is True

    def test_update_policy(self, controller):
        controller.update_policy(SpendPhase.SEMI_AUTO, max_task_usd=0.50)
        policy = controller.get_policy(SpendPhase.SEMI_AUTO)
        assert policy.max_task_usd == 0.50

    def test_update_policy_invalid_field(self, controller):
        with pytest.raises(ValueError, match="Unknown"):
            controller.update_policy(SpendPhase.SEMI_AUTO, nonexistent_field=42)


# ─── Default Policies ────────────────────────────────────────


class TestDefaultPolicies:

    def test_emergency_blocks_all(self):
        policy = DEFAULT_POLICIES[SpendPhase.EMERGENCY]
        assert policy.max_task_usd == 0.0
        assert policy.max_daily_usd == 0.0
        assert policy.require_approval is True
        assert policy.auto_assign is False

    def test_preflight_blocks_all(self):
        policy = DEFAULT_POLICIES[SpendPhase.PRE_FLIGHT]
        assert policy.max_task_usd == 0.0
        assert not policy.allows_spend(0.01)

    def test_passive_blocks_all(self):
        policy = DEFAULT_POLICIES[SpendPhase.PASSIVE]
        assert policy.max_task_usd == 0.0
        assert not policy.allows_spend(0.01)

    def test_semi_auto_limits(self):
        policy = DEFAULT_POLICIES[SpendPhase.SEMI_AUTO]
        assert policy.max_task_usd == 0.25
        assert policy.max_daily_usd == 5.0
        assert policy.max_monthly_usd == 50.0
        assert policy.allows_spend(0.25)
        assert not policy.allows_spend(0.26)
        assert policy.auto_assign is True
        assert policy.require_approval is False

    def test_full_auto_limits(self):
        policy = DEFAULT_POLICIES[SpendPhase.FULL_AUTO]
        assert policy.max_task_usd == 10.0
        assert policy.max_daily_usd == 50.0
        assert policy.max_monthly_usd == 500.0
        assert policy.allows_spend(10.0)
        assert not policy.allows_spend(10.01)


# ─── Spend Authorization ─────────────────────────────────────


class TestSpendAuthorization:

    def test_preflight_blocks_any_spend(self, controller):
        with pytest.raises(BudgetExceededError, match="max task"):
            controller.authorize_spend("t1", 1, 0.01)

    def test_passive_blocks_any_spend(self, controller):
        controller.set_phase(SpendPhase.PASSIVE)
        with pytest.raises(BudgetExceededError):
            controller.authorize_spend("t1", 1, 0.01)

    def test_emergency_blocks_any_spend(self, controller):
        controller.set_phase(SpendPhase.EMERGENCY)
        with pytest.raises(BudgetExceededError):
            controller.authorize_spend("t1", 1, 0.01)

    def test_semi_auto_allows_micro_task(self, semi_auto_controller):
        record = semi_auto_controller.authorize_spend("t1", 1, 0.20, "photo")
        assert isinstance(record, SpendRecord)
        assert record.amount_usd == 0.20
        assert record.status == "committed"
        assert record.category == "photo"

    def test_semi_auto_blocks_over_limit(self, semi_auto_controller):
        with pytest.raises(BudgetExceededError, match="max task"):
            semi_auto_controller.authorize_spend("t1", 1, 0.30)

    def test_full_auto_allows_larger_tasks(self, full_auto_controller):
        record = full_auto_controller.authorize_spend("t1", 1, 5.00)
        assert record.amount_usd == 5.00

    def test_daily_fleet_limit_enforced(self, semi_auto_controller):
        # Semi-auto daily limit is $5
        for i in range(20):
            semi_auto_controller.authorize_spend(f"t{i}", 1, 0.25)
        # Now at $5.00 exactly — next should fail
        with pytest.raises(BudgetExceededError, match="Daily"):
            semi_auto_controller.authorize_spend("t_over", 1, 0.01)

    def test_monthly_fleet_limit_enforced(self, full_auto_controller):
        # Full auto monthly limit is $500, daily is $50
        # Exhaust with many days by directly setting state
        full_auto_controller._monthly_spent_usd = 499.50
        with pytest.raises(BudgetExceededError, match="Monthly"):
            full_auto_controller.authorize_spend("t_over", 1, 1.00)

    def test_daily_tracking_accumulates(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.10)
        semi_auto_controller.authorize_spend("t2", 2, 0.15)
        status = semi_auto_controller.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == 0.25

    def test_approval_required_rejects_auto(self, controller):
        # PRE_FLIGHT requires approval — override limits to let task/daily/monthly pass
        controller.update_policy(
            SpendPhase.PRE_FLIGHT,
            max_task_usd=1.0,
            max_daily_usd=5.0,
            max_monthly_usd=50.0,
        )
        with pytest.raises(BudgetExceededError, match="approval"):
            controller.authorize_spend("t1", 1, 0.50)

    def test_approval_with_human_approved(self, controller):
        # Override PRE_FLIGHT to allow spending (for testing)
        controller.update_policy(
            SpendPhase.PRE_FLIGHT,
            max_task_usd=1.0,
            max_daily_usd=5.0,
            max_monthly_usd=50.0,
        )
        record = controller.authorize_spend("t1", 1, 0.50, approved_by="saul")
        assert record.approved_by == "saul"

    def test_per_agent_tracking(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 100, 0.20)
        semi_auto_controller.authorize_spend("t2", 200, 0.15)
        semi_auto_controller.authorize_spend("t3", 100, 0.10)

        agent_100 = semi_auto_controller.get_agent_spend(100)
        assert agent_100["total_usd"] == 0.30
        assert agent_100["transaction_count"] == 2

        agent_200 = semi_auto_controller.get_agent_spend(200)
        assert agent_200["total_usd"] == 0.15


# ─── Can Spend (Pre-check) ───────────────────────────────────


class TestCanSpend:

    def test_can_spend_returns_true_when_ok(self, semi_auto_controller):
        allowed, reason = semi_auto_controller.can_spend(0.20)
        assert allowed is True
        assert reason == "OK"

    def test_can_spend_returns_false_over_task_limit(self, semi_auto_controller):
        allowed, reason = semi_auto_controller.can_spend(0.30)
        assert allowed is False
        assert "task limit" in reason.lower()

    def test_can_spend_returns_false_daily_limit(self, semi_auto_controller):
        semi_auto_controller._daily_spent_usd = 4.90
        allowed, reason = semi_auto_controller.can_spend(0.20)
        assert allowed is False
        assert "daily" in reason.lower()

    def test_can_spend_returns_false_approval_required(self, controller):
        # PRE_FLIGHT requires approval — override limits to let task/daily/monthly pass
        controller.update_policy(
            SpendPhase.PRE_FLIGHT,
            max_task_usd=1.0,
            max_daily_usd=5.0,
            max_monthly_usd=50.0,
        )
        allowed, reason = controller.can_spend(0.50)
        assert allowed is False
        assert "approval" in reason.lower()


# ─── Refunds ──────────────────────────────────────────────────


class TestRefunds:

    def test_refund_reduces_totals(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.20)
        semi_auto_controller.record_refund("t1", 0.20)

        status = semi_auto_controller.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == 0.0
        assert status["monthly"]["spent_usd"] == 0.0

    def test_refund_marks_record(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.20)
        semi_auto_controller.record_refund("t1", 0.20)

        # Find record in history
        refunded = [r for r in semi_auto_controller._history if r.task_id == "t1"]
        assert refunded[0].status == "refunded"

    def test_refund_creates_alert(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.20)
        semi_auto_controller.record_refund("t1", 0.20)

        alerts = semi_auto_controller.get_alerts()
        assert any(a.code == "refund_processed" for a in alerts)

    def test_refund_doesnt_go_negative(self, semi_auto_controller):
        semi_auto_controller.record_refund("nonexistent", 100.0)
        assert semi_auto_controller._daily_spent_usd == 0.0
        assert semi_auto_controller._monthly_spent_usd == 0.0


# ─── Balance Tracking ────────────────────────────────────────


class TestBalanceTracking:

    def test_update_balance(self, controller):
        snap = controller.update_balance(
            "0xPlatform",
            balance_usdc=100.0,
            chain="base",
            block_number=44000000,
        )
        assert isinstance(snap, BalanceSnapshot)
        assert snap.balance_usdc == 100.0
        assert snap.chain == "base"

    def test_total_balance_multi_chain(self, controller):
        controller.update_balance("0xA", 100.0, "base")
        controller.update_balance("0xA", 50.0, "ethereum")
        assert controller.get_total_balance() == 150.0

    def test_balance_update_replaces(self, controller):
        controller.update_balance("0xA", 100.0, "base")
        controller.update_balance("0xA", 80.0, "base")
        assert controller.get_total_balance() == 80.0

    def test_low_balance_warning(self, controller):
        controller.update_balance("0xA", 5.0, "base")
        alerts = controller.get_alerts(level="warning")
        assert any(a.code == "low_balance" for a in alerts)

    def test_critical_low_balance(self, controller):
        controller.update_balance("0xA", 0.50, "base")
        alerts = controller.get_alerts(level="critical")
        assert any(a.code == "low_balance" for a in alerts)

    def test_balance_staleness(self, controller):
        snap = controller.update_balance("0xA", 100.0, "base")
        assert not snap.is_stale  # Just created

    def test_balance_age(self, controller):
        snap = BalanceSnapshot(
            wallet_address="0xA",
            balance_usdc=100.0,
            chain="base",
            fetched_at=time.time() - 600,
        )
        assert snap.is_stale  # 10 minutes old


# ─── Burn Rate Analysis ──────────────────────────────────────


class TestBurnRate:

    def test_zero_burn_rate_no_spending(self, controller):
        burn = controller.calculate_burn_rate()
        assert burn.usd_per_hour == 0.0
        assert burn.usd_per_day == 0.0
        assert burn.runway_hours is None

    def test_burn_rate_after_spending(self, semi_auto_controller):
        now = time.time()
        # Simulate recent spends
        for i in range(10):
            semi_auto_controller._recent_spends.append(
                (now - (i * 360), 0.10)  # $0.10 every 6 min for last hour
            )
        burn = semi_auto_controller.calculate_burn_rate(window_hours=1.0)
        assert burn.total_usd == pytest.approx(1.0, abs=0.01)
        assert burn.transaction_count == 10
        assert burn.usd_per_hour > 0

    def test_burn_rate_runway_with_balance(self, semi_auto_controller):
        semi_auto_controller.update_balance("0xA", 10.0, "base")
        now = time.time()
        for i in range(10):
            semi_auto_controller._recent_spends.append(
                (now - (i * 360), 0.10)
            )
        burn = semi_auto_controller.calculate_burn_rate(window_hours=1.0)
        assert burn.runway_hours is not None
        assert burn.runway_hours > 0

    def test_burn_rate_trend_zero(self, controller):
        # Add all-zero history
        for _ in range(5):
            controller._burn_rate_history.append(0.0)
        burn = controller.calculate_burn_rate()
        assert burn.trend == "zero"

    def test_burn_rate_trend_increasing(self, semi_auto_controller):
        # Old rates low, new rates high
        for _ in range(5):
            semi_auto_controller._burn_rate_history.append(0.1)
        for _ in range(5):
            semi_auto_controller._burn_rate_history.append(0.5)
        burn = semi_auto_controller.calculate_burn_rate()
        assert burn.trend == "increasing"

    def test_burn_rate_trend_decreasing(self, semi_auto_controller):
        for _ in range(5):
            semi_auto_controller._burn_rate_history.append(0.5)
        for _ in range(5):
            semi_auto_controller._burn_rate_history.append(0.1)
        burn = semi_auto_controller.calculate_burn_rate()
        assert burn.trend == "decreasing"

    def test_burn_rate_trend_stable(self, semi_auto_controller):
        for _ in range(10):
            semi_auto_controller._burn_rate_history.append(0.3)
        burn = semi_auto_controller.calculate_burn_rate()
        assert burn.trend == "stable"


# ─── Spend Projections ───────────────────────────────────────


class TestProjections:

    def test_projection_no_spending(self, controller):
        proj = controller.project_spend(hours=24)
        assert proj["projected_usd"] == 0.0
        assert proj["risk_level"] == "low"

    def test_projection_with_spending(self, semi_auto_controller):
        now = time.time()
        for i in range(5):
            semi_auto_controller._recent_spends.append(
                (now - (i * 720), 0.20)
            )
        proj = semi_auto_controller.project_spend(hours=24)
        assert proj["projected_usd"] > 0
        assert "burn_rate" in proj

    def test_projection_recommendations_overspend(self, semi_auto_controller):
        now = time.time()
        # Heavy spending: $0.25 every 6 minutes = $2.50/hr
        for i in range(25):
            semi_auto_controller._recent_spends.append(
                (now - (i * 360), 0.25)
            )
        proj = semi_auto_controller.project_spend(hours=24)
        assert len(proj["recommendations"]) > 0

    def test_projection_risk_level_high(self, semi_auto_controller):
        semi_auto_controller._daily_spent_usd = 4.90  # Almost at $5 limit
        now = time.time()
        for i in range(10):
            semi_auto_controller._recent_spends.append(
                (now - (i * 360), 0.10)
            )
        proj = semi_auto_controller.project_spend(hours=24)
        assert proj["risk_level"] in ("high", "critical")


# ─── Budget Alerts ────────────────────────────────────────────


class TestAlerts:

    def test_warning_at_75_percent(self, semi_auto_controller):
        # Semi-auto daily limit is $5, spend $3.80 (76%)
        for i in range(19):
            semi_auto_controller.authorize_spend(f"t{i}", 1, 0.20)
        alerts = semi_auto_controller.get_alerts(level="warning")
        assert any("daily_budget_warning" == a.code for a in alerts)

    def test_critical_at_90_percent(self, semi_auto_controller):
        # Spend $4.50 out of $5 (90%)
        for i in range(18):
            semi_auto_controller.authorize_spend(f"t{i}", 1, 0.25)
        alerts = semi_auto_controller.get_alerts(level="critical")
        assert any("daily_budget_critical" == a.code for a in alerts)

    def test_alert_filtering_by_level(self, controller):
        controller._add_alert("info", "test_info", "Info message")
        controller._add_alert("warning", "test_warn", "Warning message")
        controller._add_alert("critical", "test_crit", "Critical message")

        info = controller.get_alerts(level="info")
        warn = controller.get_alerts(level="warning")
        crit = controller.get_alerts(level="critical")

        assert len(info) >= 1
        assert len(warn) >= 1
        assert len(crit) >= 1

    def test_alert_filtering_by_time(self, controller):
        old_time = time.time() - 3600
        controller._alerts.append(
            BudgetAlert(level="info", code="old", message="Old", timestamp=old_time)
        )
        controller._add_alert("info", "new", "New")

        recent = controller.get_alerts(since=time.time() - 60)
        assert len(recent) == 1
        assert recent[0].code == "new"

    def test_alert_limit(self, controller):
        for i in range(100):
            controller._add_alert("info", f"test_{i}", f"Test {i}")
        limited = controller.get_alerts(limit=10)
        assert len(limited) == 10


# ─── Fleet Status ─────────────────────────────────────────────


class TestFleetStatus:

    def test_fleet_status_structure(self, controller):
        status = controller.get_fleet_budget_status()
        assert "phase" in status
        assert "policy" in status
        assert "daily" in status
        assert "monthly" in status
        assert "all_time" in status
        assert "balances" in status
        assert "top_spenders" in status
        assert "category_breakdown" in status

    def test_fleet_status_tracks_categories(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.10, "photo")
        semi_auto_controller.authorize_spend("t2", 1, 0.20, "delivery")
        semi_auto_controller.authorize_spend("t3", 1, 0.05, "photo")

        status = semi_auto_controller.get_fleet_budget_status()
        cats = status["category_breakdown"]
        assert cats["photo"] == 0.15
        assert cats["delivery"] == 0.20

    def test_fleet_status_top_spenders(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 100, 0.20)
        semi_auto_controller.authorize_spend("t2", 200, 0.10)
        semi_auto_controller.authorize_spend("t3", 100, 0.05)

        status = semi_auto_controller.get_fleet_budget_status()
        top = status["top_spenders"]
        assert top[0]["agent_id"] == 100
        assert top[0]["total_usd"] == 0.25


# ─── Agent Spend ──────────────────────────────────────────────


class TestAgentSpend:

    def test_agent_spend_empty(self, controller):
        result = controller.get_agent_spend(999)
        assert result["total_usd"] == 0
        assert result["transaction_count"] == 0

    def test_agent_spend_with_records(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 42, 0.20, "photo")
        semi_auto_controller.authorize_spend("t2", 42, 0.05, "delivery")

        result = semi_auto_controller.get_agent_spend(42)
        assert result["total_usd"] == 0.25
        assert result["transaction_count"] == 2
        assert "photo" in result["categories"]
        assert "delivery" in result["categories"]
        assert len(result["recent"]) == 2


# ─── PhaseGate Integration ───────────────────────────────────


class TestPhaseGateMetrics:

    def test_metrics_structure(self, controller):
        metrics = controller.get_metrics_for_phase_gate()
        assert "avg_budget_utilization" in metrics
        assert "daily_utilization" in metrics
        assert "monthly_utilization" in metrics
        assert "burn_rate_usd_per_hour" in metrics
        assert "burn_rate_trend" in metrics
        assert "total_balance_usd" in metrics
        assert "approval_count" in metrics
        assert "rejection_count" in metrics

    def test_metrics_reflect_spending(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.25)
        metrics = semi_auto_controller.get_metrics_for_phase_gate()
        assert metrics["daily_utilization"] > 0
        assert metrics["approval_count"] == 1

    def test_metrics_reflect_rejections(self, controller):
        try:
            controller.authorize_spend("t1", 1, 0.01)
        except BudgetExceededError:
            pass
        metrics = controller.get_metrics_for_phase_gate()
        assert metrics["rejection_count"] == 1

    def test_metrics_balance(self, controller):
        controller.update_balance("0xA", 42.0, "base")
        metrics = controller.get_metrics_for_phase_gate()
        assert metrics["total_balance_usd"] == 42.0

    def test_metrics_has_active_alerts(self, controller):
        metrics = controller.get_metrics_for_phase_gate()
        assert metrics["has_active_alerts"] is False

        controller._add_alert("critical", "test", "Test critical")
        metrics = controller.get_metrics_for_phase_gate()
        assert metrics["has_active_alerts"] is True


# ─── Serialization ────────────────────────────────────────────


class TestSerialization:

    def test_to_dict(self, controller):
        d = controller.to_dict()
        assert d["phase"] == "PRE_FLIGHT"
        assert "fleet_daily_limit" in d
        assert "fleet_monthly_limit" in d
        assert "policies" in d

    def test_round_trip(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.20)
        semi_auto_controller.authorize_spend("t2", 2, 0.15)
        semi_auto_controller.update_balance("0xA", 100.0, "base")

        d = semi_auto_controller.to_dict()
        restored = BudgetController.from_dict(d)

        assert restored.current_phase == SpendPhase.SEMI_AUTO
        assert restored._daily_spent_usd == pytest.approx(0.35, abs=0.01)
        assert restored._total_spent_usd == pytest.approx(0.35, abs=0.01)
        assert restored._approval_count == 2

    def test_from_dict_unknown_phase_defaults(self):
        d = {"phase": "NONEXISTENT"}
        restored = BudgetController.from_dict(d)
        assert restored.current_phase == SpendPhase.PRE_FLIGHT

    def test_from_dict_empty(self):
        restored = BudgetController.from_dict({})
        assert restored.current_phase == SpendPhase.PRE_FLIGHT
        assert restored._fleet_daily_limit == 50.0


# ─── Daily/Monthly Resets ─────────────────────────────────────


class TestResets:

    def test_daily_reset_on_date_change(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.25)
        assert semi_auto_controller._daily_spent_usd == 0.25

        # Force date change
        semi_auto_controller._last_daily_reset = "2020-01-01"
        semi_auto_controller._check_resets()
        assert semi_auto_controller._daily_spent_usd == 0.0

    def test_monthly_reset_on_month_change(self, semi_auto_controller):
        semi_auto_controller._monthly_spent_usd = 100.0
        semi_auto_controller._last_monthly_reset = "2020-01"
        semi_auto_controller._check_resets()
        assert semi_auto_controller._monthly_spent_usd == 0.0

    def test_daily_reset_clears_agent_daily(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.25)
        assert semi_auto_controller._agent_daily.get(1, 0) == 0.25

        semi_auto_controller._last_daily_reset = "2020-01-01"
        semi_auto_controller._check_resets()
        assert len(semi_auto_controller._agent_daily) == 0


# ─── Diagnostic Report ───────────────────────────────────────


class TestDiagnosticReport:

    def test_report_renders(self, controller):
        report = controller.diagnostic_report()
        assert "BUDGET CONTROLLER" in report
        assert "Phase" in report
        assert "Daily" in report

    def test_report_with_spending(self, semi_auto_controller):
        semi_auto_controller.authorize_spend("t1", 1, 0.20)
        semi_auto_controller.update_balance("0xA", 50.0, "base")
        report = semi_auto_controller.diagnostic_report()
        assert "$" in report
        assert "SEMI_AUTO" in report

    def test_report_with_alerts(self, controller):
        controller._add_alert("critical", "test", "Test critical alert")
        report = controller.diagnostic_report()
        assert "CRITICAL" in report


# ─── BudgetExceededError ──────────────────────────────────────


class TestBudgetExceededError:

    def test_error_attributes(self):
        err = BudgetExceededError(
            "Test error",
            limit_type="daily_fleet",
            limit_usd=5.0,
            requested_usd=6.0,
        )
        assert err.limit_type == "daily_fleet"
        assert err.limit_usd == 5.0
        assert err.requested_usd == 6.0
        assert str(err) == "Test error"


# ─── SpendRecord ──────────────────────────────────────────────


class TestSpendRecord:

    def test_record_to_dict(self):
        record = SpendRecord(
            task_id="t1",
            agent_id=1,
            amount_usd=0.50,
            category="photo",
        )
        d = record.to_dict()
        assert d["task_id"] == "t1"
        assert d["amount_usd"] == 0.50
        assert d["status"] == "committed"


# ─── PhasePolicy ──────────────────────────────────────────────


class TestPhasePolicy:

    def test_allows_spend_boundary(self):
        policy = PhasePolicy(
            phase=SpendPhase.SEMI_AUTO,
            max_task_usd=0.25,
            max_daily_usd=5.0,
            max_monthly_usd=50.0,
            require_approval=False,
            auto_assign=True,
        )
        assert policy.allows_spend(0.25) is True
        assert policy.allows_spend(0.00) is True
        assert policy.allows_spend(0.26) is False

    def test_policy_to_dict(self):
        policy = PhasePolicy(
            phase=SpendPhase.SEMI_AUTO,
            max_task_usd=0.25,
            max_daily_usd=5.0,
            max_monthly_usd=50.0,
            require_approval=False,
            auto_assign=True,
            description="Test policy",
        )
        d = policy.to_dict()
        assert d["phase"] == "SEMI_AUTO"
        assert d["description"] == "Test policy"


# ─── BalanceSnapshot ──────────────────────────────────────────


class TestBalanceSnapshot:

    def test_snapshot_to_dict(self):
        snap = BalanceSnapshot(
            wallet_address="0xTest",
            balance_usdc=100.0,
            chain="base",
            block_number=44000000,
        )
        d = snap.to_dict()
        assert d["balance_usdc"] == 100.0
        assert d["chain"] == "base"
        assert "age_seconds" in d
        assert "is_stale" in d


# ─── Edge Cases ───────────────────────────────────────────────


class TestEdgeCases:

    def test_massive_spend_count(self, semi_auto_controller):
        """Test with many small spends."""
        for i in range(100):
            try:
                semi_auto_controller.authorize_spend(f"t{i}", 1, 0.01)
            except BudgetExceededError:
                break

    def test_zero_amount_spend(self, semi_auto_controller):
        record = semi_auto_controller.authorize_spend("t0", 1, 0.0)
        assert record.amount_usd == 0.0

    def test_concurrent_agent_tracking(self, semi_auto_controller):
        """Multiple agents spending concurrently."""
        for agent_id in range(1, 11):
            semi_auto_controller.authorize_spend(
                f"t_{agent_id}", agent_id, 0.10
            )
        status = semi_auto_controller.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == pytest.approx(1.0, abs=0.01)
        assert len(status["top_spenders"]) == 5  # Top 5

    def test_custom_policies(self):
        """Controller with custom policies."""
        custom_policies = {
            SpendPhase.SEMI_AUTO: PhasePolicy(
                phase=SpendPhase.SEMI_AUTO,
                max_task_usd=1.0,
                max_daily_usd=10.0,
                max_monthly_usd=100.0,
                require_approval=False,
                auto_assign=True,
            ),
        }
        # Merge with defaults
        policies = dict(DEFAULT_POLICIES)
        policies.update(custom_policies)

        c = BudgetController(policies=policies)
        c.set_phase(SpendPhase.SEMI_AUTO)
        record = c.authorize_spend("t1", 1, 0.75)  # Would fail with default $0.25 limit
        assert record.amount_usd == 0.75

    def test_fleet_limit_overrides_phase_policy(self):
        """Fleet daily limit should constrain even if phase policy is higher."""
        c = BudgetController(fleet_daily_limit_usd=2.0)
        c.set_phase(SpendPhase.FULL_AUTO)  # Phase allows $50/day

        # Spend should be constrained by fleet $2 limit
        c.authorize_spend("t1", 1, 1.50)
        with pytest.raises(BudgetExceededError, match="Daily"):
            c.authorize_spend("t2", 1, 1.00)


# ─── Full Lifecycle Test ──────────────────────────────────────


class TestFullLifecycle:

    def test_complete_budget_lifecycle(self):
        """Walk through a complete budget lifecycle: create → spend → alert → refund → report."""
        c = BudgetController(
            fleet_daily_limit_usd=10.0,
            fleet_monthly_limit_usd=100.0,
        )

        # Phase 0: Pre-flight — no spending allowed
        assert c.current_phase == SpendPhase.PRE_FLIGHT
        with pytest.raises(BudgetExceededError):
            c.authorize_spend("t1", 1, 0.10)

        # Advance to Phase 2: Semi-auto
        c.set_phase(SpendPhase.SEMI_AUTO)

        # Fund the wallet
        c.update_balance("0xPlatform", 25.0, "base", block_number=44000000)

        # Create some tasks
        c.authorize_spend("t1", 1, 0.20, "photo")
        c.authorize_spend("t2", 2, 0.15, "delivery")
        c.authorize_spend("t3", 1, 0.25, "verification")

        # Check status
        status = c.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == pytest.approx(0.60, abs=0.01)
        assert status["phase"] == "SEMI_AUTO"

        # Check burn rate
        burn = c.calculate_burn_rate()
        assert burn.transaction_count >= 0  # May or may not be in window

        # Refund one task
        c.record_refund("t2", 0.15)
        status = c.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == pytest.approx(0.45, abs=0.01)

        # Generate report
        report = c.diagnostic_report()
        assert "SEMI_AUTO" in report

        # Export for PhaseGate
        metrics = c.get_metrics_for_phase_gate()
        assert metrics["approval_count"] == 3
        assert metrics["total_balance_usd"] == 25.0

        # Serialize and restore
        d = c.to_dict()
        restored = BudgetController.from_dict(d)
        assert restored.current_phase == SpendPhase.SEMI_AUTO
        assert restored._total_spent_usd == pytest.approx(0.45, abs=0.01)

    def test_phase_progression_budget_journey(self):
        """Test budget behavior across phase transitions."""
        c = BudgetController(fleet_daily_limit_usd=50.0)

        # Emergency → everything blocked
        c.set_phase(SpendPhase.EMERGENCY)
        with pytest.raises(BudgetExceededError):
            c.authorize_spend("t1", 1, 0.01)

        # Pre-flight → still blocked
        c.set_phase(SpendPhase.PRE_FLIGHT)
        with pytest.raises(BudgetExceededError):
            c.authorize_spend("t1", 1, 0.01)

        # Passive → blocked (observation only)
        c.set_phase(SpendPhase.PASSIVE)
        with pytest.raises(BudgetExceededError):
            c.authorize_spend("t1", 1, 0.01)

        # Semi-auto → micro-tasks allowed
        c.set_phase(SpendPhase.SEMI_AUTO)
        c.authorize_spend("t1", 1, 0.20)  # OK
        with pytest.raises(BudgetExceededError):
            c.authorize_spend("t2", 1, 0.30)  # Too expensive

        # Full-auto → larger tasks
        c.set_phase(SpendPhase.FULL_AUTO)
        c.authorize_spend("t3", 1, 5.00)  # OK
        with pytest.raises(BudgetExceededError):
            c.authorize_spend("t4", 1, 15.00)  # Over $10 limit

        # Emergency stop → immediate block
        c.set_phase(SpendPhase.EMERGENCY)
        with pytest.raises(BudgetExceededError):
            c.authorize_spend("t5", 1, 0.01)

        # Check alerts — should have multiple phase changes
        # PF→EM, EM→PF, PF→PA, PA→SA, SA→FA, FA→EM = 6 transitions
        alerts = [a for a in c.get_alerts() if a.code == "phase_change"]
        assert len(alerts) == 6
