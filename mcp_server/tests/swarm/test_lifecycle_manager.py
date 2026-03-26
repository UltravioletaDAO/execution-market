"""
Tests for LifecycleManager — Agent state machine, budgets, and health.

Covers:
- Agent registration and unregistration
- State transitions (valid and invalid)
- Task assignment and completion
- Cooldown handling (expiry, auto-transition)
- Budget tracking (daily, monthly, hard stops)
- Budget reset logic (daily, monthly)
- Heartbeat monitoring (recording, checking, degradation)
- Error recording
- Available agents filtering
- Swarm status overview
- State history audit log
"""

from datetime import datetime, timezone, timedelta

import pytest

from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    AgentRecord,
    BudgetConfig,
    HealthStatus,
    LifecycleError,
    BudgetExceededError,
    VALID_TRANSITIONS,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def manager():
    """Fresh LifecycleManager."""
    return LifecycleManager()


@pytest.fixture
def manager_with_agent(manager):
    """Manager with one registered agent in IDLE state."""
    manager.register_agent(1, "aurora", "0xABC", personality="explorer")
    manager.transition(1, AgentState.IDLE)
    return manager


@pytest.fixture
def manager_with_active_agent(manager_with_agent):
    """Manager with one agent in ACTIVE state."""
    manager_with_agent.transition(1, AgentState.ACTIVE)
    return manager_with_agent


# ─── Agent Registration ──────────────────────────────────────────────────────


class TestRegistration:
    def test_register_agent(self, manager):
        record = manager.register_agent(1, "aurora", "0xABC")
        assert isinstance(record, AgentRecord)
        assert record.agent_id == 1
        assert record.name == "aurora"
        assert record.wallet_address == "0xABC"
        assert record.state == AgentState.INITIALIZING

    def test_register_with_personality(self, manager):
        record = manager.register_agent(1, "aurora", "0xABC", personality="specialist")
        assert record.personality == "specialist"

    def test_register_with_custom_budget(self, manager):
        config = BudgetConfig(daily_limit_usd=10.0, task_limit_usd=5.0)
        record = manager.register_agent(1, "aurora", "0xABC", budget_config=config)
        assert record.budget_config.daily_limit_usd == 10.0
        assert record.budget_config.task_limit_usd == 5.0

    def test_register_with_tags(self, manager):
        record = manager.register_agent(
            1, "aurora", "0xABC", tags=["photo", "delivery"]
        )
        assert record.tags == ["photo", "delivery"]

    def test_register_duplicate_raises(self, manager):
        manager.register_agent(1, "aurora", "0xABC")
        with pytest.raises(LifecycleError, match="already registered"):
            manager.register_agent(1, "aurora_2", "0xDEF")

    def test_unregister_agent(self, manager):
        manager.register_agent(1, "aurora", "0xABC")
        manager.unregister_agent(1)
        assert 1 not in manager.agents

    def test_unregister_nonexistent_raises(self, manager):
        with pytest.raises(LifecycleError, match="not found"):
            manager.unregister_agent(999)

    def test_agents_property_returns_copy(self, manager):
        manager.register_agent(1, "aurora", "0xABC")
        agents = manager.agents
        agents[999] = "should not affect internal state"
        assert 999 not in manager.agents


# ─── State Transitions ───────────────────────────────────────────────────────


class TestStateTransitions:
    def test_initializing_to_idle(self, manager):
        manager.register_agent(1, "aurora", "0xABC")
        record = manager.transition(1, AgentState.IDLE)
        assert record.state == AgentState.IDLE

    def test_idle_to_active(self, manager_with_agent):
        record = manager_with_agent.transition(1, AgentState.ACTIVE)
        assert record.state == AgentState.ACTIVE

    def test_active_to_working_via_assign(self, manager_with_active_agent):
        record = manager_with_active_agent.assign_task(1, "task-1")
        assert record.state == AgentState.WORKING

    def test_working_to_cooldown_via_complete(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "task-1")
        record = manager_with_active_agent.complete_task(1)
        assert record.state == AgentState.COOLDOWN

    def test_idle_to_suspended(self, manager_with_agent):
        record = manager_with_agent.transition(
            1, AgentState.SUSPENDED, reason="manual pause"
        )
        assert record.state == AgentState.SUSPENDED

    def test_suspended_to_idle(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.SUSPENDED)
        record = manager_with_agent.transition(1, AgentState.IDLE)
        assert record.state == AgentState.IDLE

    def test_invalid_transition_raises(self, manager_with_agent):
        # IDLE → WORKING is invalid (must go through ACTIVE first)
        with pytest.raises(LifecycleError, match="Invalid transition"):
            manager_with_agent.transition(1, AgentState.WORKING)

    def test_invalid_transition_shows_valid_targets(self, manager_with_agent):
        with pytest.raises(LifecycleError) as exc_info:
            manager_with_agent.transition(1, AgentState.COOLDOWN)
        assert "Valid targets" in str(exc_info.value)

    def test_transition_nonexistent_agent(self, manager):
        with pytest.raises(LifecycleError, match="not found"):
            manager.transition(999, AgentState.IDLE)

    def test_all_valid_transitions_defined(self):
        """Every state has a transition definition."""
        for state in AgentState:
            assert state in VALID_TRANSITIONS

    def test_transition_updates_timestamp(self, manager_with_agent):
        before = manager_with_agent.agents[1].state_changed_at
        manager_with_agent.transition(1, AgentState.ACTIVE)
        after = manager_with_agent.agents[1].state_changed_at
        assert after >= before

    def test_degraded_to_idle_on_recovery(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.DEGRADED)
        record = manager_with_agent.transition(1, AgentState.IDLE)
        assert record.state == AgentState.IDLE

    def test_degraded_to_suspended(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.DEGRADED)
        record = manager_with_agent.transition(1, AgentState.SUSPENDED)
        assert record.state == AgentState.SUSPENDED


# ─── Task Assignment ─────────────────────────────────────────────────────────


class TestTaskAssignment:
    def test_assign_task_sets_task_id(self, manager_with_active_agent):
        record = manager_with_active_agent.assign_task(1, "task-42")
        assert record.current_task_id == "task-42"

    def test_assign_task_wrong_state(self, manager_with_agent):
        # Agent is IDLE, not ACTIVE
        with pytest.raises(LifecycleError, match="must be ACTIVE"):
            manager_with_agent.assign_task(1, "task-1")

    def test_complete_task_clears_task_id(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "task-1")
        record = manager_with_active_agent.complete_task(1)
        assert record.current_task_id is None

    def test_complete_task_wrong_state(self, manager_with_active_agent):
        with pytest.raises(LifecycleError, match="must be WORKING"):
            manager_with_active_agent.complete_task(1)

    def test_complete_task_sets_cooldown(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "task-1")
        record = manager_with_active_agent.complete_task(1, cooldown_seconds=120)
        assert record.cooldown_until is not None
        expected = datetime.now(timezone.utc) + timedelta(seconds=120)
        assert abs((record.cooldown_until - expected).total_seconds()) < 2


# ─── Cooldown Handling ────────────────────────────────────────────────────────


class TestCooldown:
    def test_cooldown_not_expired(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "task-1")
        manager_with_active_agent.complete_task(1, cooldown_seconds=3600)
        expired = manager_with_active_agent.check_cooldown_expiry(1)
        assert expired is False

    def test_cooldown_expired(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "task-1")
        manager_with_active_agent.complete_task(1, cooldown_seconds=0)
        # Set cooldown to the past
        agent = manager_with_active_agent._agents[1]
        agent.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        expired = manager_with_active_agent.check_cooldown_expiry(1)
        assert expired is True
        assert agent.state == AgentState.IDLE

    def test_cooldown_none_expires_immediately(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "task-1")
        manager_with_active_agent.complete_task(1)
        # Force cooldown_until to None
        agent = manager_with_active_agent._agents[1]
        agent.cooldown_until = None
        expired = manager_with_active_agent.check_cooldown_expiry(1)
        assert expired is True
        assert agent.state == AgentState.IDLE

    def test_check_cooldown_not_in_cooldown_state(self, manager_with_agent):
        # Agent is IDLE, not COOLDOWN
        expired = manager_with_agent.check_cooldown_expiry(1)
        assert expired is False


# ─── Budget Tracking ─────────────────────────────────────────────────────────


class TestBudgetTracking:
    def test_record_spend(self, manager_with_agent):
        manager_with_agent.record_spend(1, 1.0)
        status = manager_with_agent.get_budget_status(1)
        assert status["daily_spent"] == 1.0
        assert status["monthly_spent"] == 1.0

    def test_spend_accumulates(self, manager_with_agent):
        manager_with_agent.record_spend(1, 1.0)
        manager_with_agent.record_spend(1, 0.50)
        status = manager_with_agent.get_budget_status(1)
        assert status["daily_spent"] == 1.50

    def test_budget_exceeded_suspends_agent(self, manager_with_agent):
        # Default daily limit is $5.0
        with pytest.raises(BudgetExceededError):
            manager_with_agent.record_spend(1, 5.5)
        agent = manager_with_agent.agents[1]
        assert agent.state == AgentState.SUSPENDED

    def test_budget_warning_threshold(self, manager_with_agent):
        manager_with_agent.record_spend(1, 4.0)  # 80% of $5 default
        status = manager_with_agent.get_budget_status(1)
        assert status["at_warning"] is True
        assert status["at_limit"] is False

    def test_budget_at_limit(self, manager_with_agent):
        with pytest.raises(BudgetExceededError):
            manager_with_agent.record_spend(1, 5.0)
        status = manager_with_agent.get_budget_status(1)
        assert status["at_limit"] is True

    def test_monthly_budget_exceeded(self):
        mgr = LifecycleManager()
        config = BudgetConfig(
            daily_limit_usd=1000.0,  # High daily
            monthly_limit_usd=2.0,  # Low monthly
        )
        mgr.register_agent(1, "aurora", "0xABC", budget_config=config)
        mgr.transition(1, AgentState.IDLE)

        with pytest.raises(BudgetExceededError, match="monthly budget exceeded"):
            mgr.record_spend(1, 2.5)

    def test_budget_pct_calculation(self, manager_with_agent):
        manager_with_agent.record_spend(1, 2.5)
        status = manager_with_agent.get_budget_status(1)
        assert status["daily_pct"] == 50.0  # 2.5 / 5.0 = 50%

    def test_budget_status_unknown_agent(self, manager):
        with pytest.raises(LifecycleError, match="not found"):
            manager.get_budget_status(999)

    def test_assign_task_checks_budget(self, manager):
        config = BudgetConfig(daily_limit_usd=1.0)
        manager.register_agent(1, "aurora", "0xABC", budget_config=config)
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        # record_spend at limit triggers budget exceeded + suspension
        with pytest.raises(BudgetExceededError):
            manager.record_spend(1, 1.0)
        # Agent is now suspended, so assign_task fails with LifecycleError
        with pytest.raises(LifecycleError):
            manager.assign_task(1, "task-1")


# ─── Budget Resets ────────────────────────────────────────────────────────────


class TestBudgetResets:
    def test_daily_reset(self, manager_with_agent):
        manager_with_agent.record_spend(1, 1.0)
        # Simulate previous day
        agent = manager_with_agent._agents[1]
        agent.budget_state.last_reset_date = "2020-01-01"
        agent.budget_state.check_daily_reset()
        assert agent.budget_state.daily_spent_usd == 0.0

    def test_monthly_reset(self, manager_with_agent):
        manager_with_agent.record_spend(1, 1.0)
        agent = manager_with_agent._agents[1]
        agent.budget_state.last_monthly_reset = "2020-01"
        agent.budget_state.check_monthly_reset()
        assert agent.budget_state.monthly_spent_usd == 0.0


# ─── Heartbeat Monitoring ────────────────────────────────────────────────────


class TestHeartbeat:
    def test_record_heartbeat(self, manager_with_agent):
        record = manager_with_agent.record_heartbeat(1)
        assert record.health.last_heartbeat is not None
        assert record.health.total_heartbeats == 1
        assert record.health.consecutive_missed == 0

    def test_heartbeat_resets_missed_count(self, manager_with_agent):
        agent = manager_with_agent._agents[1]
        agent.health.consecutive_missed = 2
        manager_with_agent.record_heartbeat(1)
        assert agent.health.consecutive_missed == 0

    def test_heartbeat_recovers_degraded(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.DEGRADED)
        record = manager_with_agent.record_heartbeat(1)
        assert record.state == AgentState.IDLE

    def test_check_heartbeat_healthy(self, manager_with_agent):
        manager_with_agent.record_heartbeat(1)
        healthy = manager_with_agent.check_heartbeat(1)
        assert healthy is True

    def test_check_heartbeat_overdue(self, manager_with_agent):
        agent = manager_with_agent._agents[1]
        agent.health.last_heartbeat = datetime.now(timezone.utc) - timedelta(
            seconds=600
        )
        # Need to miss 3 heartbeats for degraded
        for _ in range(3):
            manager_with_agent.check_heartbeat(1)
        assert agent.state == AgentState.DEGRADED

    def test_check_heartbeat_initializing_grace(self, manager):
        manager.register_agent(1, "aurora", "0xABC")
        # INITIALIZING agents get a grace period
        healthy = manager.check_heartbeat(1)
        assert healthy is True

    def test_health_status_properties(self):
        hs = HealthStatus()
        assert hs.is_healthy is True
        assert hs.seconds_since_heartbeat == float("inf")

        hs.last_heartbeat = datetime.now(timezone.utc)
        assert hs.seconds_since_heartbeat < 1

    def test_health_status_no_timezone(self):
        """Handles naive datetime (adds UTC)."""
        hs = HealthStatus()
        hs.last_heartbeat = datetime(2026, 1, 1, 0, 0, 0)  # Naive
        # Should not raise
        secs = hs.seconds_since_heartbeat
        assert secs > 0


# ─── Error Recording ─────────────────────────────────────────────────────────


class TestErrorRecording:
    def test_record_error(self, manager_with_agent):
        manager_with_agent.record_error(1, "Connection timeout")
        agent = manager_with_agent.agents[1]
        assert agent.health.errors_last_hour == 1
        assert agent.health.last_error == "Connection timeout"
        assert agent.health.last_error_at is not None

    def test_multiple_errors(self, manager_with_agent):
        manager_with_agent.record_error(1, "Error 1")
        manager_with_agent.record_error(1, "Error 2")
        agent = manager_with_agent.agents[1]
        assert agent.health.errors_last_hour == 2
        assert agent.health.last_error == "Error 2"


# ─── Available Agents ─────────────────────────────────────────────────────────


class TestAvailableAgents:
    def test_idle_agent_available(self, manager_with_agent):
        available = manager_with_agent.get_available_agents()
        assert len(available) == 1
        assert available[0].agent_id == 1

    def test_active_agent_available(self, manager_with_active_agent):
        available = manager_with_active_agent.get_available_agents()
        assert len(available) == 1

    def test_working_agent_not_available(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "task-1")
        available = manager_with_active_agent.get_available_agents()
        assert len(available) == 0

    def test_suspended_agent_not_available(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.SUSPENDED)
        available = manager_with_agent.get_available_agents()
        assert len(available) == 0

    def test_cooldown_expired_becomes_available(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "task-1")
        manager_with_active_agent.complete_task(1)
        # Set cooldown to past
        agent = manager_with_active_agent._agents[1]
        agent.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        available = manager_with_active_agent.get_available_agents()
        assert len(available) == 1

    def test_budget_exceeded_agent_not_available(self, manager):
        config = BudgetConfig(daily_limit_usd=1.0)
        manager.register_agent(1, "aurora", "0xABC", budget_config=config)
        manager.transition(1, AgentState.IDLE)
        # Spending up to limit won't raise because daily_pct < 1.0
        # But recording exactly at limit will raise
        try:
            manager.record_spend(1, 1.0)
        except BudgetExceededError:
            pass
        available = manager.get_available_agents()
        assert len(available) == 0

    def test_multiple_agents_availability(self, manager):
        for i in range(3):
            manager.register_agent(i, f"agent_{i}", f"0x{i}")
            manager.transition(i, AgentState.IDLE)
        manager.transition(1, AgentState.SUSPENDED)  # Suspend one
        available = manager.get_available_agents()
        ids = [a.agent_id for a in available]
        assert 0 in ids
        assert 2 in ids
        assert 1 not in ids


# ─── Swarm Status ─────────────────────────────────────────────────────────────


class TestSwarmStatus:
    def test_empty_swarm(self, manager):
        status = manager.get_swarm_status()
        assert status["total_agents"] == 0
        assert status["available_count"] == 0

    def test_status_with_agents(self, manager):
        manager.register_agent(1, "a1", "0x1")
        manager.transition(1, AgentState.IDLE)
        manager.register_agent(2, "a2", "0x2")
        manager.transition(2, AgentState.IDLE)
        manager.transition(2, AgentState.DEGRADED)

        status = manager.get_swarm_status()
        assert status["total_agents"] == 2
        assert status["state_counts"]["idle"] == 1
        assert status["state_counts"]["degraded"] == 1
        assert status["degraded_agents"] == [2]

    def test_status_includes_spend(self, manager_with_agent):
        manager_with_agent.record_spend(1, 2.50)
        status = manager_with_agent.get_swarm_status()
        assert status["total_daily_spend"] == 2.50
        assert status["total_monthly_spend"] == 2.50


# ─── State History ────────────────────────────────────────────────────────────


class TestStateHistory:
    def test_history_records_registration(self, manager):
        manager.register_agent(1, "aurora", "0xABC")
        history = manager.state_history
        assert len(history) >= 1
        assert history[0]["to"] == "initializing"
        assert history[0]["from"] is None

    def test_history_records_transition(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.ACTIVE)
        history = manager_with_agent.state_history
        last = history[-1]
        assert last["from"] == "idle"
        assert last["to"] == "active"

    def test_history_returns_copy(self, manager_with_agent):
        history = manager_with_agent.state_history
        history.append({"fake": True})
        assert {"fake": True} not in manager_with_agent.state_history

    def test_history_includes_reason(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.SUSPENDED, reason="manual pause")
        history = manager_with_agent.state_history
        last = history[-1]
        assert last["reason"] == "manual pause"

    def test_history_includes_timestamp(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.ACTIVE)
        history = manager_with_agent.state_history
        assert "timestamp" in history[-1]


# ─── AgentRecord ──────────────────────────────────────────────────────────────


class TestAgentRecord:
    def test_post_init_sets_timestamps(self):
        record = AgentRecord(agent_id=1, name="test", wallet_address="0x123")
        assert record.created_at is not None
        assert record.state_changed_at is not None

    def test_default_state_is_initializing(self):
        record = AgentRecord(agent_id=1, name="test", wallet_address="0x123")
        assert record.state == AgentState.INITIALIZING

    def test_default_budget_config(self):
        config = BudgetConfig()
        assert config.daily_limit_usd == 5.0
        assert config.monthly_limit_usd == 100.0
        assert config.task_limit_usd == 2.0
        assert config.warning_threshold == 0.80
        assert config.hard_stop_threshold == 1.0
