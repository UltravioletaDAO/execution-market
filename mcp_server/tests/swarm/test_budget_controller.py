"""
Tests for BudgetController — Fleet-wide budget management.

Covers:
- Phase policies and transitions
- Spend authorization (task/daily/monthly limits)
- Budget exceeded errors
- Refund processing
- On-chain balance tracking
- Burn rate calculation and trend detection
- Spend projection and risk assessment
- Fleet budget status reporting
- Per-agent spend tracking
- Alert generation (warning/critical thresholds)
- PhaseGate integration metrics
- Serialization (to_dict / from_dict)
- Daily/monthly reset logic
- Diagnostic report generation
"""

import time
from unittest.mock import patch
from datetime import datetime, timezone

import pytest

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


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def controller():
    """Fresh BudgetController in PRE_FLIGHT phase."""
    return BudgetController()


@pytest.fixture
def semi_auto_controller():
    """BudgetController in SEMI_AUTO phase (spending allowed)."""
    c = BudgetController()
    c.set_phase(SpendPhase.SEMI_AUTO)
    return c


@pytest.fixture
def full_auto_controller():
    """BudgetController in FULL_AUTO phase."""
    c = BudgetController(
        fleet_daily_limit_usd=50.0,
        fleet_monthly_limit_usd=500.0,
    )
    c.set_phase(SpendPhase.FULL_AUTO)
    return c


# ─── Phase Management ─────────────────────────────────────────────────────────


class TestPhaseManagement:
    def test_initial_phase_is_pre_flight(self, controller):
        assert controller.current_phase == SpendPhase.PRE_FLIGHT

    def test_set_phase(self, controller):
        controller.set_phase(SpendPhase.SEMI_AUTO)
        assert controller.current_phase == SpendPhase.SEMI_AUTO

    def test_set_phase_generates_alert(self, controller):
        controller.set_phase(SpendPhase.PASSIVE)
        alerts = controller.get_alerts(level="info")
        phase_alerts = [a for a in alerts if a.code == "phase_change"]
        assert len(phase_alerts) == 1
        assert "PRE_FLIGHT" in phase_alerts[0].message
        assert "PASSIVE" in phase_alerts[0].message

    def test_set_same_phase_no_alert(self, controller):
        # Already PRE_FLIGHT, setting again
        controller.set_phase(SpendPhase.PRE_FLIGHT)
        alerts = controller.get_alerts(level="info")
        phase_alerts = [a for a in alerts if a.code == "phase_change"]
        assert len(phase_alerts) == 0

    def test_get_policy_current(self, semi_auto_controller):
        policy = semi_auto_controller.current_policy
        assert policy.phase == SpendPhase.SEMI_AUTO
        assert policy.max_task_usd == 0.25
        assert policy.auto_assign is True

    def test_get_policy_specific_phase(self, controller):
        policy = controller.get_policy(SpendPhase.FULL_AUTO)
        assert policy.max_task_usd == 10.0
        assert policy.max_daily_usd == 50.0
        assert policy.require_approval is False

    def test_update_policy(self, controller):
        controller.update_policy(SpendPhase.SEMI_AUTO, max_task_usd=1.0)
        policy = controller.get_policy(SpendPhase.SEMI_AUTO)
        assert policy.max_task_usd == 1.0

    def test_update_policy_invalid_field(self, controller):
        with pytest.raises(ValueError, match="Unknown policy field"):
            controller.update_policy(SpendPhase.SEMI_AUTO, nonexistent_field=42)

    def test_all_default_policies_exist(self):
        for phase in SpendPhase:
            assert phase in DEFAULT_POLICIES

    def test_emergency_policy_blocks_all(self, controller):
        controller.set_phase(SpendPhase.EMERGENCY)
        policy = controller.current_policy
        assert policy.max_task_usd == 0.0
        assert policy.max_daily_usd == 0.0
        assert policy.require_approval is True
        assert policy.auto_assign is False


# ─── Spend Authorization ──────────────────────────────────────────────────────


class TestSpendAuthorization:
    def test_spend_in_semi_auto(self, semi_auto_controller):
        record = semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.20, category="photo"
        )
        assert isinstance(record, SpendRecord)
        assert record.task_id == "t1"
        assert record.agent_id == 1
        assert record.amount_usd == 0.20
        assert record.category == "photo"
        assert record.status == "committed"

    def test_spend_exceeds_task_limit(self, semi_auto_controller):
        with pytest.raises(BudgetExceededError) as exc_info:
            semi_auto_controller.authorize_spend(
                task_id="t1", agent_id=1, amount_usd=0.50
            )
        assert exc_info.value.limit_type == "phase_task"
        assert exc_info.value.limit_usd == 0.25

    def test_spend_exceeds_daily_limit(self, semi_auto_controller):
        # Daily limit for SEMI_AUTO is $5.00
        # Spend 20 tasks at $0.25 each = $5.00
        for i in range(20):
            semi_auto_controller.authorize_spend(
                task_id=f"t{i}", agent_id=1, amount_usd=0.25
            )
        # Next should fail
        with pytest.raises(BudgetExceededError) as exc_info:
            semi_auto_controller.authorize_spend(
                task_id="overflow", agent_id=1, amount_usd=0.25
            )
        assert exc_info.value.limit_type == "daily_fleet"

    def test_spend_exceeds_monthly_limit(self):
        c = BudgetController(
            fleet_daily_limit_usd=1000.0,  # High daily to hit monthly first
            fleet_monthly_limit_usd=1.0,
        )
        c.set_phase(SpendPhase.FULL_AUTO)
        # Update policy monthly cap to $1
        c.update_policy(SpendPhase.FULL_AUTO, max_monthly_usd=1.0)

        c.authorize_spend(task_id="t1", agent_id=1, amount_usd=0.80)
        with pytest.raises(BudgetExceededError) as exc_info:
            c.authorize_spend(task_id="t2", agent_id=1, amount_usd=0.30)
        assert exc_info.value.limit_type == "monthly_fleet"

    def test_spend_requires_approval_in_passive(self, controller):
        controller.set_phase(SpendPhase.PASSIVE)
        with pytest.raises(BudgetExceededError) as exc_info:
            controller.authorize_spend(
                task_id="t1", agent_id=1, amount_usd=0.01
            )
        # Passive max_task is 0, so it fails on phase_task first
        assert exc_info.value.limit_type == "phase_task"

    def test_spend_with_human_approval(self):
        """Even in approval-required phases, explicit human approval works."""
        c = BudgetController()
        # Create a custom phase that requires approval but allows spending
        c.update_policy(
            SpendPhase.PASSIVE,
            max_task_usd=1.0,
            max_daily_usd=10.0,
            max_monthly_usd=100.0,
        )
        c.set_phase(SpendPhase.PASSIVE)
        # This should fail because approved_by="auto" and require_approval=True
        with pytest.raises(BudgetExceededError) as exc_info:
            c.authorize_spend(task_id="t1", agent_id=1, amount_usd=0.50)
        assert exc_info.value.limit_type == "approval_required"

        # But with human approval it works
        record = c.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.50, approved_by="saul"
        )
        assert record.approved_by == "saul"

    def test_spend_tracked_per_agent(self, full_auto_controller):
        full_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=1.00
        )
        full_auto_controller.authorize_spend(
            task_id="t2", agent_id=2, amount_usd=2.00
        )
        full_auto_controller.authorize_spend(
            task_id="t3", agent_id=1, amount_usd=0.50
        )

        agent1 = full_auto_controller.get_agent_spend(1)
        assert agent1["total_usd"] == 1.50
        assert agent1["transaction_count"] == 2

        agent2 = full_auto_controller.get_agent_spend(2)
        assert agent2["total_usd"] == 2.00

    def test_spend_updates_all_counters(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.10
        )
        status = semi_auto_controller.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == 0.10
        assert status["monthly"]["spent_usd"] == 0.10
        assert status["all_time"]["total_spent_usd"] == 0.10
        assert status["all_time"]["approval_count"] == 1

    def test_rejection_counted(self, semi_auto_controller):
        with pytest.raises(BudgetExceededError):
            semi_auto_controller.authorize_spend(
                task_id="t1", agent_id=1, amount_usd=999.0
            )
        status = semi_auto_controller.get_fleet_budget_status()
        assert status["all_time"]["rejection_count"] == 1


# ─── Can Spend (Pre-check) ────────────────────────────────────────────────────


class TestCanSpend:
    def test_can_spend_within_limits(self, semi_auto_controller):
        allowed, reason = semi_auto_controller.can_spend(0.10)
        assert allowed is True
        assert reason == "OK"

    def test_can_spend_exceeds_task_limit(self, semi_auto_controller):
        allowed, reason = semi_auto_controller.can_spend(0.50)
        assert allowed is False
        assert "task limit" in reason.lower()

    def test_can_spend_requires_approval(self, controller):
        # PRE_FLIGHT requires approval
        allowed, reason = controller.can_spend(0.01)
        assert allowed is False  # max_task is 0 in PRE_FLIGHT


# ─── Refunds ──────────────────────────────────────────────────────────────────


class TestRefunds:
    def test_refund_reduces_counters(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.20
        )
        semi_auto_controller.record_refund("t1", 0.20)

        status = semi_auto_controller.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == 0.0
        assert status["monthly"]["spent_usd"] == 0.0
        assert status["all_time"]["refund_count"] == 1

    def test_refund_marks_record(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.20
        )
        semi_auto_controller.record_refund("t1", 0.20)

        agent = semi_auto_controller.get_agent_spend(1)
        assert agent["total_usd"] == 0.0

    def test_refund_generates_alert(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.20
        )
        semi_auto_controller.record_refund("t1", 0.20)

        alerts = semi_auto_controller.get_alerts(level="info")
        refund_alerts = [a for a in alerts if a.code == "refund_processed"]
        assert len(refund_alerts) == 1

    def test_refund_floors_at_zero(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.10
        )
        # Refund more than spent
        semi_auto_controller.record_refund("t1", 1.00)
        status = semi_auto_controller.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == 0.0


# ─── Balance Tracking ─────────────────────────────────────────────────────────


class TestBalanceTracking:
    def test_update_balance(self, controller):
        snap = controller.update_balance("0x123", 100.0, "base", block_number=12345)
        assert isinstance(snap, BalanceSnapshot)
        assert snap.balance_usdc == 100.0
        assert snap.chain == "base"
        assert snap.wallet_address == "0x123"

    def test_total_balance_across_chains(self, controller):
        controller.update_balance("0x123", 50.0, "base")
        controller.update_balance("0x123", 30.0, "ethereum")
        assert controller.get_total_balance() == 80.0

    def test_low_balance_warning(self, controller):
        controller.update_balance("0x123", 5.0, "base")
        alerts = controller.get_alerts(level="warning")
        low_balance = [a for a in alerts if a.code == "low_balance"]
        assert len(low_balance) == 1

    def test_critical_low_balance(self, controller):
        controller.update_balance("0x123", 0.50, "base")
        alerts = controller.get_alerts(level="critical")
        low_balance = [a for a in alerts if a.code == "low_balance"]
        assert len(low_balance) == 1

    def test_balance_staleness(self):
        snap = BalanceSnapshot(
            wallet_address="0x123",
            balance_usdc=10.0,
            chain="base",
            fetched_at=time.time() - 600,  # 10 min ago
        )
        assert snap.is_stale is True

    def test_balance_freshness(self):
        snap = BalanceSnapshot(
            wallet_address="0x123",
            balance_usdc=10.0,
            chain="base",
        )
        assert snap.is_stale is False

    def test_get_balances(self, controller):
        controller.update_balance("0x123", 50.0, "base")
        controller.update_balance("0x456", 30.0, "ethereum")
        balances = controller.get_balances()
        assert "base" in balances
        assert "ethereum" in balances


# ─── Burn Rate ────────────────────────────────────────────────────────────────


class TestBurnRate:
    def test_zero_burn_rate_no_spends(self, controller):
        burn = controller.calculate_burn_rate()
        assert burn.usd_per_hour == 0.0
        assert burn.usd_per_day == 0.0
        assert burn.runway_hours is None
        assert burn.transaction_count == 0

    def test_burn_rate_with_spends(self, full_auto_controller):
        # Spend some amounts
        for i in range(5):
            full_auto_controller.authorize_spend(
                task_id=f"t{i}", agent_id=1, amount_usd=1.0
            )
        burn = full_auto_controller.calculate_burn_rate(window_hours=24.0)
        assert burn.total_usd == 5.0
        assert burn.transaction_count == 5
        assert burn.usd_per_hour > 0

    def test_burn_rate_to_dict(self):
        burn = BurnRate(
            window_seconds=86400,
            total_usd=10.0,
            transaction_count=5,
            usd_per_hour=0.4167,
            usd_per_day=10.0,
            runway_hours=240.0,
            runway_days=10.0,
            trend="stable",
        )
        d = burn.to_dict()
        assert d["total_usd"] == 10.0
        assert d["trend"] == "stable"
        assert d["runway_days"] == 10.0

    def test_trend_insufficient_data(self, controller):
        burn = controller.calculate_burn_rate()
        assert burn.trend == "insufficient_data"

    def test_trend_zero(self):
        c = BudgetController()
        c.set_phase(SpendPhase.FULL_AUTO)
        # Push multiple zero burn rates
        for _ in range(5):
            c._burn_rate_history.append(0.0)
        trend = c._detect_trend()
        assert trend == "zero"

    def test_trend_increasing(self):
        c = BudgetController()
        c._burn_rate_history.extend([0.1, 0.1, 0.1, 0.5, 0.5, 0.5])
        trend = c._detect_trend()
        assert trend == "increasing"

    def test_trend_decreasing(self):
        c = BudgetController()
        c._burn_rate_history.extend([0.5, 0.5, 0.5, 0.1, 0.1, 0.1])
        trend = c._detect_trend()
        assert trend == "decreasing"

    def test_trend_stable(self):
        c = BudgetController()
        c._burn_rate_history.extend([0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
        trend = c._detect_trend()
        assert trend == "stable"


# ─── Spend Projection ─────────────────────────────────────────────────────────


class TestSpendProjection:
    def test_projection_no_spends(self, controller):
        proj = controller.project_spend(hours=24)
        assert proj["projected_usd"] == 0.0
        assert proj["risk_level"] == "low"
        assert proj["recommendations"] == []

    def test_projection_with_balance(self, full_auto_controller):
        full_auto_controller.update_balance("0x123", 100.0, "base")
        for i in range(10):
            full_auto_controller.authorize_spend(
                task_id=f"t{i}", agent_id=1, amount_usd=1.0
            )
        proj = full_auto_controller.project_spend(hours=24)
        assert proj["on_chain_balance_usd"] == 100.0
        assert proj["projection_hours"] == 24

    def test_projection_risk_levels(self, full_auto_controller):
        # No spending = low risk
        proj = full_auto_controller.project_spend(hours=24)
        assert proj["risk_level"] == "low"


# ─── Alert System ─────────────────────────────────────────────────────────────


class TestAlerts:
    def test_daily_warning_at_75pct(self):
        c = BudgetController(fleet_daily_limit_usd=4.0)
        c.set_phase(SpendPhase.SEMI_AUTO)
        # policy max_daily is $5, fleet is $4 → effective $4
        # 75% of $4 = $3.0, spend 15 × $0.20 = $3.00
        for i in range(15):
            c.authorize_spend(task_id=f"t{i}", agent_id=1, amount_usd=0.20)
        alerts = c.get_alerts(level="warning")
        daily_warns = [a for a in alerts if a.code == "daily_budget_warning"]
        assert len(daily_warns) >= 1

    def test_daily_critical_at_90pct(self):
        c = BudgetController(fleet_daily_limit_usd=4.0)
        c.set_phase(SpendPhase.SEMI_AUTO)
        # 90% of $4 = $3.60, spend 18 × $0.20 = $3.60
        for i in range(18):
            c.authorize_spend(task_id=f"t{i}", agent_id=1, amount_usd=0.20)
        alerts = c.get_alerts(level="critical")
        daily_crits = [a for a in alerts if a.code == "daily_budget_critical"]
        assert len(daily_crits) >= 1

    def test_get_alerts_filtered_by_level(self, controller):
        controller._add_alert("info", "test_info", "Info message")
        controller._add_alert("warning", "test_warn", "Warning message")
        controller._add_alert("critical", "test_crit", "Critical message")

        info_alerts = controller.get_alerts(level="info")
        assert all(a.level == "info" for a in info_alerts)

        crit_alerts = controller.get_alerts(level="critical")
        assert all(a.level == "critical" for a in crit_alerts)

    def test_get_alerts_since_timestamp(self, controller):
        controller._add_alert("info", "old", "Old alert")
        marker = time.time()
        time.sleep(0.01)
        controller._add_alert("info", "new", "New alert")

        alerts = controller.get_alerts(since=marker)
        assert len(alerts) >= 1
        assert any(a.code == "new" for a in alerts)

    def test_alert_to_dict(self):
        alert = BudgetAlert(
            level="warning",
            code="test",
            message="Test alert",
            data={"key": "value"},
        )
        d = alert.to_dict()
        assert d["level"] == "warning"
        assert d["code"] == "test"
        assert d["data"]["key"] == "value"


# ─── Fleet Status ─────────────────────────────────────────────────────────────


class TestFleetStatus:
    def test_fleet_status_structure(self, semi_auto_controller):
        status = semi_auto_controller.get_fleet_budget_status()
        assert "phase" in status
        assert "policy" in status
        assert "daily" in status
        assert "monthly" in status
        assert "all_time" in status
        assert "balances" in status
        assert "top_spenders" in status
        assert "category_breakdown" in status

    def test_fleet_status_after_spends(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.10, category="photo"
        )
        semi_auto_controller.authorize_spend(
            task_id="t2", agent_id=2, amount_usd=0.20, category="delivery"
        )

        status = semi_auto_controller.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == 0.30
        assert status["all_time"]["transaction_count"] == 2
        assert len(status["top_spenders"]) == 2
        assert "photo" in status["category_breakdown"]
        assert "delivery" in status["category_breakdown"]

    def test_top_spenders_sorted(self, full_auto_controller):
        for i in range(5):
            full_auto_controller.authorize_spend(
                task_id=f"t1_{i}", agent_id=1, amount_usd=1.0
            )
        full_auto_controller.authorize_spend(
            task_id="t2_0", agent_id=2, amount_usd=0.50
        )

        status = full_auto_controller.get_fleet_budget_status()
        spenders = status["top_spenders"]
        assert spenders[0]["agent_id"] == 1
        assert spenders[0]["total_usd"] == 5.0


# ─── Agent Spend ──────────────────────────────────────────────────────────────


class TestAgentSpend:
    def test_agent_spend_unknown_agent(self, controller):
        result = controller.get_agent_spend(999)
        assert result["total_usd"] == 0.0
        assert result["transaction_count"] == 0

    def test_agent_spend_with_categories(self, full_auto_controller):
        full_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=1.0, category="photo"
        )
        full_auto_controller.authorize_spend(
            task_id="t2", agent_id=1, amount_usd=2.0, category="delivery"
        )
        full_auto_controller.authorize_spend(
            task_id="t3", agent_id=1, amount_usd=0.5, category="photo"
        )

        spend = full_auto_controller.get_agent_spend(1)
        assert spend["categories"]["photo"] == 1.5
        assert spend["categories"]["delivery"] == 2.0
        assert len(spend["recent"]) == 3


# ─── PhaseGate Metrics ────────────────────────────────────────────────────────


class TestPhaseGateMetrics:
    def test_metrics_structure(self, controller):
        metrics = controller.get_metrics_for_phase_gate()
        assert "avg_budget_utilization" in metrics
        assert "daily_utilization" in metrics
        assert "monthly_utilization" in metrics
        assert "burn_rate_usd_per_hour" in metrics
        assert "burn_rate_trend" in metrics
        assert "total_balance_usd" in metrics
        assert "has_active_alerts" in metrics

    def test_metrics_zero_at_start(self, controller):
        metrics = controller.get_metrics_for_phase_gate()
        assert metrics["avg_budget_utilization"] == 0.0
        assert metrics["daily_utilization"] == 0.0
        assert metrics["burn_rate_usd_per_hour"] == 0.0

    def test_metrics_after_spending(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.25
        )
        metrics = semi_auto_controller.get_metrics_for_phase_gate()
        assert metrics["daily_utilization"] > 0
        assert metrics["approval_count"] == 1


# ─── Serialization ────────────────────────────────────────────────────────────


class TestSerialization:
    def test_to_dict(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.10
        )
        d = semi_auto_controller.to_dict()
        assert d["phase"] == "SEMI_AUTO"
        assert d["daily_spent"] == 0.10
        assert d["total_spent"] == 0.10
        assert d["approval_count"] == 1
        assert 1 in d["agent_totals"]

    def test_from_dict_roundtrip(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.10
        )
        d = semi_auto_controller.to_dict()
        restored = BudgetController.from_dict(d)
        assert restored.current_phase == SpendPhase.SEMI_AUTO
        assert restored._total_spent_usd == 0.10
        assert restored._approval_count == 1

    def test_from_dict_unknown_phase_defaults(self):
        restored = BudgetController.from_dict({"phase": "UNKNOWN_PHASE"})
        assert restored.current_phase == SpendPhase.PRE_FLIGHT

    def test_from_dict_empty(self):
        restored = BudgetController.from_dict({})
        assert restored.current_phase == SpendPhase.PRE_FLIGHT
        assert restored._total_spent_usd == 0.0


# ─── Daily/Monthly Resets ─────────────────────────────────────────────────────


class TestResets:
    def test_daily_reset_on_new_day(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.10
        )
        # Simulate next day
        semi_auto_controller._last_daily_reset = "2020-01-01"
        semi_auto_controller._check_resets()
        assert semi_auto_controller._daily_spent_usd == 0.0

    def test_monthly_reset_on_new_month(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.10
        )
        # Simulate next month
        semi_auto_controller._last_monthly_reset = "2020-01"
        semi_auto_controller._check_resets()
        assert semi_auto_controller._monthly_spent_usd == 0.0

    def test_agent_daily_cleared_on_reset(self, semi_auto_controller):
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.10
        )
        semi_auto_controller._last_daily_reset = "2020-01-01"
        semi_auto_controller._check_resets()
        assert semi_auto_controller._agent_daily == {}


# ─── Diagnostic Report ────────────────────────────────────────────────────────


class TestDiagnosticReport:
    def test_report_is_string(self, controller):
        report = controller.diagnostic_report()
        assert isinstance(report, str)
        assert "BUDGET CONTROLLER" in report

    def test_report_includes_phase(self, semi_auto_controller):
        report = semi_auto_controller.diagnostic_report()
        assert "SEMI_AUTO" in report

    def test_report_with_spends(self, full_auto_controller):
        full_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=1.0
        )
        report = full_auto_controller.diagnostic_report()
        assert "$" in report


# ─── SpendRecord ──────────────────────────────────────────────────────────────


class TestSpendRecord:
    def test_record_to_dict(self):
        record = SpendRecord(
            task_id="t1",
            agent_id=42,
            amount_usd=0.50,
            category="photo",
        )
        d = record.to_dict()
        assert d["task_id"] == "t1"
        assert d["agent_id"] == 42
        assert d["amount_usd"] == 0.50
        assert d["status"] == "committed"


# ─── PhasePolicy ──────────────────────────────────────────────────────────────


class TestPhasePolicy:
    def test_allows_spend_within_limit(self):
        policy = PhasePolicy(
            phase=SpendPhase.SEMI_AUTO,
            max_task_usd=0.25,
            max_daily_usd=5.0,
            max_monthly_usd=50.0,
            require_approval=False,
            auto_assign=True,
        )
        assert policy.allows_spend(0.20) is True
        assert policy.allows_spend(0.25) is True
        assert policy.allows_spend(0.26) is False

    def test_policy_to_dict(self):
        policy = DEFAULT_POLICIES[SpendPhase.FULL_AUTO]
        d = policy.to_dict()
        assert d["phase"] == "FULL_AUTO"
        assert d["max_task_usd"] == 10.0
        assert d["auto_assign"] is True


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_zero_amount_spend(self, full_auto_controller):
        record = full_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.0
        )
        assert record.amount_usd == 0.0

    def test_fleet_limit_lower_than_policy(self):
        """Fleet limit takes precedence when lower than policy limit."""
        c = BudgetController(
            fleet_daily_limit_usd=1.0,  # Lower than FULL_AUTO's $50
        )
        c.set_phase(SpendPhase.FULL_AUTO)
        # Spend up to fleet limit
        c.authorize_spend(task_id="t1", agent_id=1, amount_usd=0.80)
        with pytest.raises(BudgetExceededError):
            c.authorize_spend(task_id="t2", agent_id=1, amount_usd=0.30)

    def test_multiple_agents_share_fleet_budget(self, semi_auto_controller):
        # Both agents contribute to fleet daily total
        semi_auto_controller.authorize_spend(
            task_id="t1", agent_id=1, amount_usd=0.25
        )
        semi_auto_controller.authorize_spend(
            task_id="t2", agent_id=2, amount_usd=0.25
        )
        status = semi_auto_controller.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == 0.50

    def test_history_max_size(self):
        c = BudgetController(history_max_size=5)
        c.set_phase(SpendPhase.FULL_AUTO)
        for i in range(10):
            c.authorize_spend(task_id=f"t{i}", agent_id=1, amount_usd=0.01)
        assert len(c._history) == 5
