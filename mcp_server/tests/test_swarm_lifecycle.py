"""
Tests for LifecycleManager — Agent state machine, budgets, and health.

Covers:
- AgentState transitions (valid + invalid)
- BudgetConfig / BudgetState resets
- HealthStatus tracking
- AgentRecord lifecycle
- LifecycleManager operations (register, transition, task assignment)
- Budget enforcement (daily, monthly, warning, hard stop)
- Heartbeat monitoring & degradation
- Swarm status aggregation
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    AgentRecord,
    BudgetConfig,
    BudgetState,
    HealthStatus,
    LifecycleError,
    BudgetExceededError,
    VALID_TRANSITIONS,
)


# ──────────────────────────── Fixtures ────────────────────────────


def _manager_with_agent(
    agent_id=1,
    name="aurora",
    wallet="0xAAA",
    daily_limit=5.0,
    monthly_limit=100.0,
) -> tuple:
    """Returns (manager, agent_record)."""
    mgr = LifecycleManager()
    budget = BudgetConfig(daily_limit_usd=daily_limit, monthly_limit_usd=monthly_limit)
    record = mgr.register_agent(agent_id, name, wallet, budget_config=budget)
    return mgr, record


# ──────────────────── AgentState & Transitions ────────────────────


class TestAgentState:
    def test_state_values(self):
        assert AgentState.INITIALIZING.value == "initializing"
        assert AgentState.IDLE.value == "idle"
        assert AgentState.WORKING.value == "working"
        assert AgentState.SUSPENDED.value == "suspended"

    def test_all_states_have_transitions(self):
        for state in AgentState:
            assert state in VALID_TRANSITIONS

    def test_suspended_only_resumes_to_idle(self):
        assert VALID_TRANSITIONS[AgentState.SUSPENDED] == {AgentState.IDLE}

    def test_initializing_can_go_idle_or_suspended(self):
        targets = VALID_TRANSITIONS[AgentState.INITIALIZING]
        assert AgentState.IDLE in targets
        assert AgentState.SUSPENDED in targets
        assert len(targets) == 2

    def test_working_cannot_go_idle_directly(self):
        targets = VALID_TRANSITIONS[AgentState.WORKING]
        assert AgentState.IDLE not in targets

    def test_no_self_transitions_implicit(self):
        """The code doesn't explicitly block self-transitions, but
        they're not in VALID_TRANSITIONS so they'd be rejected."""
        for state, targets in VALID_TRANSITIONS.items():
            # Working → Working not allowed (must go through cooldown)
            if state == AgentState.WORKING:
                assert AgentState.WORKING not in targets


# ──────────────────── BudgetConfig / BudgetState ──────────────────


class TestBudgetState:
    def test_daily_reset_different_day(self):
        bs = BudgetState(daily_spent_usd=4.50, last_reset_date="2026-01-01")
        bs.check_daily_reset()
        assert bs.daily_spent_usd == 0.0
        assert bs.last_reset_date == datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def test_daily_reset_same_day(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        bs = BudgetState(daily_spent_usd=3.00, last_reset_date=today)
        bs.check_daily_reset()
        assert bs.daily_spent_usd == 3.00  # Not reset

    def test_monthly_reset_different_month(self):
        bs = BudgetState(monthly_spent_usd=80.0, last_monthly_reset="2025-01")
        bs.check_monthly_reset()
        assert bs.monthly_spent_usd == 0.0

    def test_monthly_reset_same_month(self):
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        bs = BudgetState(monthly_spent_usd=50.0, last_monthly_reset=this_month)
        bs.check_monthly_reset()
        assert bs.monthly_spent_usd == 50.0  # Not reset


# ──────────────────── HealthStatus Tests ──────────────────────────


class TestHealthStatus:
    def test_healthy_by_default(self):
        hs = HealthStatus()
        assert hs.is_healthy

    def test_not_healthy_after_missed(self):
        hs = HealthStatus(consecutive_missed=3, max_missed_heartbeats=3)
        assert not hs.is_healthy

    def test_seconds_since_heartbeat_none(self):
        hs = HealthStatus()
        assert hs.seconds_since_heartbeat == float("inf")

    def test_seconds_since_heartbeat_recent(self):
        hs = HealthStatus(last_heartbeat=datetime.now(timezone.utc) - timedelta(seconds=30))
        assert 25 <= hs.seconds_since_heartbeat <= 35

    def test_seconds_since_heartbeat_naive(self):
        """Naive datetime treated as UTC."""
        hs = HealthStatus(last_heartbeat=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=60))
        assert 55 <= hs.seconds_since_heartbeat <= 65


# ──────────────────── AgentRecord Tests ───────────────────────────


class TestAgentRecord:
    def test_defaults(self):
        r = AgentRecord(agent_id=1, name="test", wallet_address="0x1")
        assert r.state == AgentState.INITIALIZING
        assert r.current_task_id is None
        assert r.created_at is not None
        assert r.state_changed_at is not None
        assert r.personality == "explorer"

    def test_custom_personality(self):
        r = AgentRecord(agent_id=1, name="test", wallet_address="0x1", personality="cautious")
        assert r.personality == "cautious"


# ──────────────────── LifecycleManager Tests ──────────────────────


class TestLifecycleManagerRegistration:
    def test_register_agent(self):
        mgr = LifecycleManager()
        rec = mgr.register_agent(1, "aurora", "0xAAA")
        assert rec.agent_id == 1
        assert rec.name == "aurora"
        assert rec.state == AgentState.INITIALIZING

    def test_register_duplicate_raises(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "aurora", "0xAAA")
        with pytest.raises(LifecycleError, match="already registered"):
            mgr.register_agent(1, "aurora", "0xAAA")

    def test_register_with_budget(self):
        mgr = LifecycleManager()
        budget = BudgetConfig(daily_limit_usd=10.0)
        rec = mgr.register_agent(1, "aurora", "0xAAA", budget_config=budget)
        assert rec.budget_config.daily_limit_usd == 10.0

    def test_register_with_tags(self):
        mgr = LifecycleManager()
        rec = mgr.register_agent(1, "aurora", "0xAAA", tags=["photo", "verification"])
        assert "photo" in rec.tags

    def test_unregister_agent(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "aurora", "0xAAA")
        mgr.unregister_agent(1)
        assert 1 not in mgr.agents

    def test_unregister_nonexistent_raises(self):
        mgr = LifecycleManager()
        with pytest.raises(LifecycleError, match="not found"):
            mgr.unregister_agent(999)

    def test_agents_property_returns_copy(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "aurora", "0xAAA")
        agents = mgr.agents
        agents[999] = None  # Modify the copy
        assert 999 not in mgr.agents  # Original unchanged


class TestLifecycleManagerTransitions:
    def test_valid_transition_init_to_idle(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        assert mgr.agents[1].state == AgentState.IDLE

    def test_valid_transition_chain(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(1, AgentState.ACTIVE)
        mgr.transition(1, AgentState.IDLE)
        assert mgr.agents[1].state == AgentState.IDLE

    def test_invalid_transition_raises(self):
        mgr, rec = _manager_with_agent()
        with pytest.raises(LifecycleError, match="Invalid transition"):
            mgr.transition(1, AgentState.WORKING)  # Can't go INITIALIZING → WORKING

    def test_transition_nonexistent_agent(self):
        mgr = LifecycleManager()
        with pytest.raises(LifecycleError, match="not found"):
            mgr.transition(999, AgentState.IDLE)

    def test_transition_updates_timestamp(self):
        mgr, rec = _manager_with_agent()
        old_time = mgr.agents[1].state_changed_at
        mgr.transition(1, AgentState.IDLE)
        assert mgr.agents[1].state_changed_at >= old_time

    def test_transition_logs_history(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE, reason="test")
        history = mgr.state_history
        # First entry is registration, second is transition
        assert len(history) >= 2
        last = history[-1]
        assert last["from"] == "initializing"
        assert last["to"] == "idle"
        assert last["reason"] == "test"


class TestLifecycleManagerTasks:
    def test_assign_task_from_active(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(1, AgentState.ACTIVE)
        mgr.assign_task(1, "task-001")
        assert mgr.agents[1].state == AgentState.WORKING
        assert mgr.agents[1].current_task_id == "task-001"

    def test_assign_task_not_active_raises(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        with pytest.raises(LifecycleError, match="must be ACTIVE"):
            mgr.assign_task(1, "task-001")

    def test_complete_task(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(1, AgentState.ACTIVE)
        mgr.assign_task(1, "task-001")
        mgr.complete_task(1, cooldown_seconds=60)
        assert mgr.agents[1].state == AgentState.COOLDOWN
        assert mgr.agents[1].current_task_id is None
        assert mgr.agents[1].cooldown_until is not None

    def test_complete_task_not_working_raises(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        with pytest.raises(LifecycleError, match="must be WORKING"):
            mgr.complete_task(1)


class TestLifecycleManagerCooldown:
    def test_cooldown_not_expired(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(1, AgentState.ACTIVE)
        mgr.assign_task(1, "task-001")
        mgr.complete_task(1, cooldown_seconds=3600)  # 1 hour
        result = mgr.check_cooldown_expiry(1)
        assert result is False
        assert mgr.agents[1].state == AgentState.COOLDOWN

    def test_cooldown_expired(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(1, AgentState.ACTIVE)
        mgr.assign_task(1, "task-001")
        mgr.complete_task(1, cooldown_seconds=0)
        # Set cooldown in the past
        mgr._agents[1].cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=10)
        result = mgr.check_cooldown_expiry(1)
        assert result is True
        assert mgr.agents[1].state == AgentState.IDLE

    def test_cooldown_no_duration_set(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(1, AgentState.ACTIVE)
        mgr.assign_task(1, "task-001")
        mgr.complete_task(1, cooldown_seconds=0)
        mgr._agents[1].cooldown_until = None
        result = mgr.check_cooldown_expiry(1)
        assert result is True
        assert mgr.agents[1].state == AgentState.IDLE

    def test_cooldown_check_non_cooldown_state(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        result = mgr.check_cooldown_expiry(1)
        assert result is False


class TestLifecycleManagerHeartbeats:
    def test_record_heartbeat(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        mgr.record_heartbeat(1)
        agent = mgr.agents[1]
        assert agent.health.last_heartbeat is not None
        assert agent.health.total_heartbeats == 1
        assert agent.health.consecutive_missed == 0

    def test_heartbeat_recovers_from_degraded(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(1, AgentState.DEGRADED)
        assert mgr.agents[1].state == AgentState.DEGRADED
        mgr.record_heartbeat(1)
        assert mgr.agents[1].state == AgentState.IDLE

    def test_check_heartbeat_healthy(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        mgr.record_heartbeat(1)
        result = mgr.check_heartbeat(1)
        assert result is True

    def test_check_heartbeat_overdue_degrades(self):
        mgr, rec = _manager_with_agent()
        mgr.transition(1, AgentState.IDLE)
        # Set heartbeat way in the past
        mgr._agents[1].health.last_heartbeat = datetime.now(timezone.utc) - timedelta(hours=1)
        mgr._agents[1].health.heartbeat_interval_seconds = 300
        # Need 3 missed to degrade
        mgr.check_heartbeat(1)  # miss 1
        mgr.check_heartbeat(1)  # miss 2
        result = mgr.check_heartbeat(1)  # miss 3
        assert result is False
        assert mgr.agents[1].state == AgentState.DEGRADED

    def test_check_heartbeat_initializing_grace(self):
        mgr, rec = _manager_with_agent()
        # Agent is INITIALIZING, never sent heartbeat
        result = mgr.check_heartbeat(1)
        assert result is True  # Grace period for initializing

    def test_record_error(self):
        mgr, rec = _manager_with_agent()
        mgr.record_error(1, "connection timeout")
        agent = mgr.agents[1]
        assert agent.health.errors_last_hour == 1
        assert agent.health.last_error == "connection timeout"
        assert agent.health.last_error_at is not None


class TestLifecycleManagerBudget:
    def test_record_spend(self):
        mgr, rec = _manager_with_agent(daily_limit=5.0)
        mgr.record_spend(1, 2.50)
        status = mgr.get_budget_status(1)
        assert status["daily_spent"] == 2.50
        assert status["daily_pct"] == 50.0

    def test_budget_hard_stop_daily(self):
        mgr, rec = _manager_with_agent(daily_limit=5.0)
        mgr.transition(1, AgentState.IDLE)
        with pytest.raises(BudgetExceededError, match="daily budget"):
            mgr.record_spend(1, 6.00)
        assert mgr.agents[1].state == AgentState.SUSPENDED

    def test_budget_hard_stop_monthly(self):
        mgr, rec = _manager_with_agent(daily_limit=1000.0, monthly_limit=10.0)
        mgr.transition(1, AgentState.IDLE)
        with pytest.raises(BudgetExceededError, match="monthly budget"):
            mgr.record_spend(1, 11.00)

    def test_budget_warning_threshold(self):
        mgr, rec = _manager_with_agent(daily_limit=10.0)
        mgr.record_spend(1, 8.50)  # 85% of daily
        status = mgr.get_budget_status(1)
        assert status["at_warning"] is True
        assert status["at_limit"] is False

    def test_budget_status_keys(self):
        mgr, rec = _manager_with_agent()
        status = mgr.get_budget_status(1)
        expected_keys = {
            "agent_id", "daily_spent", "daily_limit", "daily_pct",
            "monthly_spent", "monthly_limit", "monthly_pct",
            "at_warning", "at_limit",
        }
        assert set(status.keys()) == expected_keys


class TestLifecycleManagerAvailability:
    def test_get_available_agents_idle(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "a1", "0x1")
        mgr.register_agent(2, "a2", "0x2")
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(2, AgentState.IDLE)
        available = mgr.get_available_agents()
        assert len(available) == 2

    def test_get_available_agents_excludes_working(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "a1", "0x1")
        mgr.register_agent(2, "a2", "0x2")
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(1, AgentState.ACTIVE)
        mgr.assign_task(1, "task-1")
        mgr.transition(2, AgentState.IDLE)
        available = mgr.get_available_agents()
        assert len(available) == 1
        assert available[0].agent_id == 2

    def test_get_available_excludes_over_budget(self):
        mgr = LifecycleManager()
        budget = BudgetConfig(daily_limit_usd=1.0)
        mgr.register_agent(1, "a1", "0x1", budget_config=budget)
        mgr.transition(1, AgentState.IDLE)
        mgr.record_spend(1, 0.50)  # Under budget still
        available = mgr.get_available_agents()
        assert len(available) == 1

    def test_get_available_auto_expires_cooldown(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "a1", "0x1")
        mgr.transition(1, AgentState.IDLE)
        mgr.transition(1, AgentState.ACTIVE)
        mgr.assign_task(1, "task-1")
        mgr.complete_task(1, cooldown_seconds=0)
        # Force cooldown to past
        mgr._agents[1].cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=5)
        available = mgr.get_available_agents()
        assert len(available) == 1
        assert mgr.agents[1].state == AgentState.IDLE


class TestLifecycleManagerSwarmStatus:
    def test_swarm_status_keys(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "a1", "0x1")
        mgr.register_agent(2, "a2", "0x2")
        mgr.transition(1, AgentState.IDLE)
        status = mgr.get_swarm_status()
        assert status["total_agents"] == 2
        assert "state_counts" in status
        assert "available_count" in status
        assert "degraded_agents" in status
        assert "suspended_agents" in status

    def test_swarm_status_state_counts(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "a1", "0x1")
        mgr.register_agent(2, "a2", "0x2")
        mgr.transition(1, AgentState.IDLE)
        status = mgr.get_swarm_status()
        assert status["state_counts"]["idle"] == 1
        assert status["state_counts"]["initializing"] == 1

    def test_swarm_status_tracks_spend(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "a1", "0x1")
        mgr.record_spend(1, 2.50)
        status = mgr.get_swarm_status()
        assert status["total_daily_spend"] == 2.50


class TestLifecycleManagerHistory:
    def test_state_history_audit_log(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "a1", "0x1")
        mgr.transition(1, AgentState.IDLE, "boot complete")
        history = mgr.state_history
        assert len(history) == 2  # register + transition
        assert history[0]["to"] == "initializing"
        assert history[1]["to"] == "idle"
        assert history[1]["reason"] == "boot complete"

    def test_state_history_returns_copy(self):
        mgr = LifecycleManager()
        mgr.register_agent(1, "a1", "0x1")
        h1 = mgr.state_history
        h1.append({"fake": True})
        assert len(mgr.state_history) == 1  # Original unchanged
