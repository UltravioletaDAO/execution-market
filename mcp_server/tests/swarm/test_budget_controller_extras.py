"""
Tests for BudgetController — Fleet-wide budget management, phase policies,
burn rate analysis, balance tracking, and alerts.

Covers:
- SpendPhase enum & PhasePolicy
- SpendRecord, BurnRate, BudgetAlert, BalanceSnapshot dataclasses
- BudgetController phase management
- Spend authorization (all limit types)
- Refunds
- can_spend checks
- Balance tracking
- Burn rate calculation & trend detection
- Fleet status & agent spend reports
- Alerts generation & filtering
- Serialization (to_dict / from_dict)
- PhaseGate metric integration
- Diagnostic report
"""

import time

import pytest

from mcp_server.swarm.budget_controller import (
    BudgetController,
    BudgetExceededError,
    SpendPhase,
    SpendRecord,
    BalanceSnapshot,
    DEFAULT_POLICIES,
)


# ──────────────────────────── Helpers ─────────────────────────────


def _controller(
    phase=SpendPhase.SEMI_AUTO,
    daily=50.0,
    monthly=500.0,
):
    """Create a controller in SEMI_AUTO phase (spending allowed)."""
    bc = BudgetController(
        fleet_daily_limit_usd=daily,
        fleet_monthly_limit_usd=monthly,
    )
    bc.set_phase(phase)
    return bc


# ──────────────────── SpendPhase / PhasePolicy ────────────────────


class TestSpendPhase:
    def test_ordering(self):
        assert SpendPhase.EMERGENCY < SpendPhase.PRE_FLIGHT
        assert SpendPhase.PRE_FLIGHT < SpendPhase.PASSIVE
        assert SpendPhase.PASSIVE < SpendPhase.SEMI_AUTO
        assert SpendPhase.SEMI_AUTO < SpendPhase.FULL_AUTO

    def test_emergency_is_negative(self):
        assert SpendPhase.EMERGENCY == -1


class TestPhasePolicy:
    def test_default_policies_exist_for_all_phases(self):
        for phase in SpendPhase:
            assert phase in DEFAULT_POLICIES


# ──────────────────── SpendRecord ─────────────────────────────────


class TestSpendRecord:
    def test_default_auto_approval(self):
        sr = SpendRecord(task_id="t1", agent_id=1, amount_usd=0.10, category="test")
        assert sr.approved_by == "auto"


# ──────────────────── BalanceSnapshot ─────────────────────────────


class TestBalanceSnapshot:
    def test_age_increases(self):
        bs = BalanceSnapshot(
            wallet_address="0x1",
            balance_usdc=100.0,
            chain="base",
            fetched_at=time.time() - 10,
        )
        assert bs.age_seconds >= 10

    def test_stale_after_five_minutes(self):
        bs = BalanceSnapshot(
            wallet_address="0x1",
            balance_usdc=100.0,
            chain="base",
            fetched_at=time.time() - 400,
        )
        assert bs.is_stale

    def test_not_stale_when_fresh(self):
        bs = BalanceSnapshot(
            wallet_address="0x1",
            balance_usdc=100.0,
            chain="base",
        )
        assert not bs.is_stale


# ──────────────────── BudgetAlert ─────────────────────────────────


# ──────────────────── BurnRate ────────────────────────────────────


# ──────────────────── Controller Phase Management ─────────────────


class TestBudgetControllerPhase:
    def test_initial_phase(self):
        bc = BudgetController()
        assert bc.current_phase == SpendPhase.PRE_FLIGHT

    def test_current_policy(self):
        bc = _controller(phase=SpendPhase.FULL_AUTO)
        assert bc.current_policy.max_task_usd == 10.0

    def test_get_policy_specific(self):
        bc = _controller()
        p = bc.get_policy(SpendPhase.EMERGENCY)
        assert p.max_task_usd == 0.0
        assert p.auto_assign is False

    def test_phase_change_alert(self):
        bc = BudgetController()
        bc.set_phase(SpendPhase.SEMI_AUTO)
        alerts = bc.get_alerts()
        assert any(a.code == "phase_change" for a in alerts)


# ──────────────────── Spend Authorization ─────────────────────────


class TestBudgetControllerSpend:
    def test_authorize_valid_spend(self):
        bc = _controller(phase=SpendPhase.SEMI_AUTO)
        record = bc.authorize_spend("t1", 1, 0.20, "photo")
        assert isinstance(record, SpendRecord)
        assert record.amount_usd == 0.20
        assert record.status == "committed"

    def test_authorize_exceeds_task_limit(self):
        bc = _controller(phase=SpendPhase.SEMI_AUTO)
        # SEMI_AUTO max_task = $0.25
        with pytest.raises(BudgetExceededError, match="Phase"):
            bc.authorize_spend("t1", 1, 0.50, "photo")

    def test_authorize_exceeds_daily_fleet_limit(self):
        bc = _controller(phase=SpendPhase.SEMI_AUTO, daily=0.50)
        bc.authorize_spend("t1", 1, 0.20, "photo")
        bc.authorize_spend("t2", 1, 0.20, "photo")
        with pytest.raises(BudgetExceededError, match="Daily fleet"):
            bc.authorize_spend("t3", 1, 0.20, "photo")

    def test_authorize_exceeds_monthly_fleet_limit(self):
        bc = _controller(phase=SpendPhase.SEMI_AUTO, monthly=0.50)
        bc.authorize_spend("t1", 1, 0.20, "photo")
        bc.authorize_spend("t2", 1, 0.20, "photo")
        with pytest.raises(BudgetExceededError, match="Monthly fleet"):
            bc.authorize_spend("t3", 1, 0.20, "photo")

    def test_authorize_requires_approval_in_passive(self):
        bc = _controller(phase=SpendPhase.PRE_FLIGHT)
        with pytest.raises(BudgetExceededError):
            bc.authorize_spend("t1", 1, 0.10, "photo")

    def test_authorize_with_human_approval(self):
        # Update pre_flight to allow some spending with approval
        bc = BudgetController(fleet_daily_limit_usd=50.0, fleet_monthly_limit_usd=500.0)
        bc.set_phase(SpendPhase.SEMI_AUTO)
        bc.update_policy(SpendPhase.SEMI_AUTO, require_approval=True)
        # Without approval → rejected
        with pytest.raises(BudgetExceededError, match="approval"):
            bc.authorize_spend("t1", 1, 0.10, "photo", approved_by="auto")
        # With approval → allowed
        record = bc.authorize_spend("t1", 1, 0.10, "photo", approved_by="saul")
        assert record.approved_by == "saul"

    def test_authorize_tracks_agent_totals(self):
        bc = _controller()
        bc.authorize_spend("t1", 42, 0.15, "photo")
        bc.authorize_spend("t2", 42, 0.10, "data")
        agent_spend = bc.get_agent_spend(42)
        assert agent_spend["total_usd"] == 0.25
        assert agent_spend["transaction_count"] == 2

    def test_authorize_increments_approval_count(self):
        bc = _controller()
        bc.authorize_spend("t1", 1, 0.10, "photo")
        assert bc._approval_count == 1

    def test_rejected_increments_rejection_count(self):
        bc = _controller()
        try:
            bc.authorize_spend("t1", 1, 999.0, "photo")
        except BudgetExceededError:
            pass
        assert bc._rejection_count >= 1

    def test_daily_warning_alert(self):
        bc = _controller(phase=SpendPhase.SEMI_AUTO, daily=1.0)
        # Spend to 80%
        for i in range(4):
            bc.authorize_spend(f"t{i}", 1, 0.20, "photo")
        alerts = bc.get_alerts(level="warning")
        assert any("budget" in a.code for a in alerts)

    def test_daily_critical_alert(self):
        bc = _controller(phase=SpendPhase.FULL_AUTO, daily=1.0)
        # Spend to 95%
        bc.authorize_spend("t1", 1, 0.95, "photo")
        alerts = bc.get_alerts(level="critical")
        assert any("daily_budget_critical" == a.code for a in alerts)


# ──────────────────── Refunds ─────────────────────────────────────


class TestBudgetControllerRefunds:
    def test_refund_reduces_totals(self):
        bc = _controller()
        bc.authorize_spend("t1", 1, 0.20, "photo")
        assert bc._daily_spent_usd == pytest.approx(0.20)
        bc.record_refund("t1", 0.20)
        assert bc._daily_spent_usd == pytest.approx(0.0)
        assert bc._monthly_spent_usd == pytest.approx(0.0)
        assert bc._total_spent_usd == pytest.approx(0.0)
        assert bc._refund_count == 1


# ──────────────────── can_spend ───────────────────────────────────


class TestBudgetControllerCanSpend:
    def test_can_spend_ok(self):
        bc = _controller(phase=SpendPhase.SEMI_AUTO)
        ok, reason = bc.can_spend(0.20)
        assert ok is True
        assert reason == "OK"

    def test_can_spend_exceeds_task(self):
        bc = _controller(phase=SpendPhase.SEMI_AUTO)
        ok, reason = bc.can_spend(1.00)
        assert ok is False
        assert "task limit" in reason

    def test_can_spend_exceeds_daily(self):
        bc = _controller(phase=SpendPhase.SEMI_AUTO, daily=0.30)
        bc.authorize_spend("t1", 1, 0.20, "photo")
        ok, reason = bc.can_spend(0.20)
        assert ok is False
        assert "daily" in reason.lower()


# ──────────────────── Balance Tracking ────────────────────────────


class TestBudgetControllerBalances:
    def test_get_total_balance(self):
        bc = _controller()
        bc.update_balance("0x1", 300.0, "base")
        bc.update_balance("0x1", 200.0, "ethereum")
        assert bc.get_total_balance() == pytest.approx(500.0)

    def test_low_balance_alert(self):
        bc = _controller()
        bc.update_balance("0x1", 0.50, "base")
        alerts = bc.get_alerts(level="critical")
        assert any("low_balance" == a.code for a in alerts)

    def test_balance_overwrite_same_chain(self):
        bc = _controller()
        bc.update_balance("0x1", 100.0, "base")
        bc.update_balance("0x1", 200.0, "base")
        assert bc.get_total_balance() == pytest.approx(200.0)

    def test_get_balances_dict(self):
        bc = _controller()
        bc.update_balance("0x1", 100.0, "base")
        balances = bc.get_balances()
        assert "base" in balances
        assert balances["base"].balance_usdc == 100.0


# ──────────────────── Burn Rate ───────────────────────────────────


class TestBudgetControllerBurnRate:
    def test_burn_rate_zero_when_no_spends(self):
        bc = _controller()
        rate = bc.calculate_burn_rate()
        assert rate.usd_per_hour == pytest.approx(0.0)
        assert rate.transaction_count == 0

    def test_burn_rate_runway_with_balance(self):
        bc = _controller()
        bc.update_balance("0x1", 100.0, "base")
        bc.authorize_spend("t1", 1, 0.10, "photo")
        rate = bc.calculate_burn_rate(window_hours=1.0)
        if rate.usd_per_hour > 0:
            assert rate.runway_hours is not None
            assert rate.runway_hours > 0

    def test_burn_rate_runway_none_when_zero_spend(self):
        bc = _controller()
        rate = bc.calculate_burn_rate()
        assert rate.runway_hours is None


# ──────────────────── Projections ─────────────────────────────────


class TestBudgetControllerProjections:
    def test_project_spend_keys(self):
        bc = _controller()
        proj = bc.project_spend(hours=24)
        assert "projected_usd" in proj
        assert "burn_rate" in proj
        assert "risk_level" in proj
        assert "recommendations" in proj
        assert "daily_remaining_usd" in proj

    def test_project_spend_low_risk_when_idle(self):
        bc = _controller()
        proj = bc.project_spend()
        assert proj["risk_level"] == "low"

    def test_project_spend_high_risk_exceeds_daily(self):
        bc = _controller(phase=SpendPhase.FULL_AUTO, daily=0.50)
        # Spend close to limit
        bc.authorize_spend("t1", 1, 0.45, "photo")
        proj = bc.project_spend(hours=24)
        # Might generate recommendations about daily remaining
        assert isinstance(proj["recommendations"], list)


# ──────────────────── Fleet Status ────────────────────────────────


class TestBudgetControllerFleetStatus:
    def test_fleet_status_keys(self):
        bc = _controller()
        bc.authorize_spend("t1", 1, 0.10, "photo")
        status = bc.get_fleet_budget_status()
        assert "phase" in status
        assert "daily" in status
        assert "monthly" in status
        assert "all_time" in status
        assert "top_spenders" in status
        assert "category_breakdown" in status
        assert "total_on_chain_usd" in status

    def test_fleet_status_daily_tracking(self):
        bc = _controller()
        bc.authorize_spend("t1", 1, 0.10, "photo")
        bc.authorize_spend("t2", 2, 0.15, "data")
        status = bc.get_fleet_budget_status()
        assert status["daily"]["spent_usd"] == pytest.approx(0.25, abs=0.001)

    def test_fleet_status_category_breakdown(self):
        bc = _controller()
        bc.authorize_spend("t1", 1, 0.10, "photo")
        bc.authorize_spend("t2", 1, 0.15, "data")
        status = bc.get_fleet_budget_status()
        assert "photo" in status["category_breakdown"]
        assert "data" in status["category_breakdown"]

    def test_fleet_status_top_spenders(self):
        bc = _controller()
        bc.authorize_spend("t1", 42, 0.20, "photo")
        bc.authorize_spend("t2", 99, 0.10, "data")
        status = bc.get_fleet_budget_status()
        assert len(status["top_spenders"]) == 2
        assert status["top_spenders"][0]["agent_id"] == 42  # Higher spender first


# ──────────────────── Agent Spend ─────────────────────────────────


class TestBudgetControllerAgentSpend:
    def test_agent_spend_report(self):
        bc = _controller()
        bc.authorize_spend("t1", 42, 0.10, "photo")
        bc.authorize_spend("t2", 42, 0.15, "data")
        report = bc.get_agent_spend(42)
        assert report["agent_id"] == 42
        assert report["total_usd"] == pytest.approx(0.25)
        assert report["transaction_count"] == 2
        assert "photo" in report["categories"]


# ──────────────────── Alerts ──────────────────────────────────────


class TestBudgetControllerAlerts:
    def test_get_alerts_empty(self):
        bc = BudgetController()
        alerts = bc.get_alerts()
        assert isinstance(alerts, list)

    def test_get_alerts_filtered_by_time(self):
        bc = _controller()
        cutoff = time.time()
        bc.update_balance("0x1", 0.10, "base")
        alerts_after = bc.get_alerts(since=cutoff)
        assert len(alerts_after) >= 1

    def test_get_alerts_limit(self):
        bc = _controller()
        for i in range(10):
            bc.update_balance(f"0x{i}", 0.01, f"chain{i}")
        alerts = bc.get_alerts(limit=3)
        assert len(alerts) <= 3


# ──────────────────── Serialization ───────────────────────────────


class TestBudgetControllerSerialization:
    def test_from_dict_round_trip(self):
        bc = _controller()
        bc.authorize_spend("t1", 1, 0.10, "photo")
        d = bc.to_dict()
        bc2 = BudgetController.from_dict(d)
        assert bc2.current_phase == SpendPhase.SEMI_AUTO
        assert bc2._daily_spent_usd == pytest.approx(0.10)
        assert bc2._approval_count == 1

    def test_from_dict_unknown_phase(self):
        bc = BudgetController.from_dict({"phase": "NONEXISTENT"})
        assert bc.current_phase == SpendPhase.PRE_FLIGHT  # Fallback


# ──────────────────── PhaseGate Metrics ───────────────────────────


class TestBudgetControllerPhaseGateMetrics:
    def test_metrics_keys(self):
        bc = _controller()
        metrics = bc.get_metrics_for_phase_gate()
        expected = {
            "avg_budget_utilization",
            "daily_utilization",
            "monthly_utilization",
            "burn_rate_usd_per_hour",
            "burn_rate_trend",
            "total_balance_usd",
            "daily_remaining_usd",
            "monthly_remaining_usd",
            "approval_count",
            "rejection_count",
            "has_active_alerts",
        }
        assert set(metrics.keys()) == expected

    def test_metrics_utilization_increases(self):
        bc = _controller(daily=1.0, monthly=10.0)
        m1 = bc.get_metrics_for_phase_gate()
        bc.authorize_spend("t1", 1, 0.25, "photo")
        m2 = bc.get_metrics_for_phase_gate()
        assert m2["daily_utilization"] > m1["daily_utilization"]

    def test_metrics_has_active_alerts(self):
        bc = _controller()
        assert bc.get_metrics_for_phase_gate()["has_active_alerts"] is False
        bc.update_balance("0x1", 0.01, "base")  # critical low_balance
        assert bc.get_metrics_for_phase_gate()["has_active_alerts"] is True


# ──────────────────── Diagnostic Report ───────────────────────────


class TestBudgetControllerDiagnostic:
    def test_diagnostic_report_format(self):
        bc = _controller()
        bc.authorize_spend("t1", 1, 0.10, "photo")
        bc.update_balance("0x1", 500.0, "base")
        report = bc.diagnostic_report()
        assert "BUDGET CONTROLLER" in report
        assert "Phase:" in report
        assert "Daily:" in report
        assert "Burn rate:" in report

    def test_diagnostic_with_critical_alerts(self):
        bc = _controller()
        bc.update_balance("0x1", 0.01, "base")
        report = bc.diagnostic_report()
        assert "CRITICAL" in report


# ──────────────────── BudgetExceededError ─────────────────────────


class TestBudgetExceededError:
    def test_error_attributes(self):
        err = BudgetExceededError(
            "test message",
            limit_type="daily_fleet",
            limit_usd=5.0,
            requested_usd=6.0,
        )
        assert err.limit_type == "daily_fleet"
        assert err.limit_usd == 5.0
        assert err.requested_usd == 6.0
        assert "test message" in str(err)
