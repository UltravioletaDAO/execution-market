"""
Tests for LifecycleManager — agent state machine, budgets, and health.

Covers:
- State machine transitions (valid and invalid)
- Agent registration/unregistration
- Task assignment and completion
- Budget tracking and enforcement
- Heartbeat monitoring and degradation
- Cooldown management
- Available agent listing
- Swarm status overview
"""

import pytest
from datetime import datetime, timezone, timedelta

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


# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def manager():
    return LifecycleManager()


@pytest.fixture
def manager_with_agent(manager):
    """Manager with one registered agent in IDLE state."""
    manager.register_agent(
        agent_id=1,
        name="Aurora",
        wallet_address="0xAurora",
        personality="explorer",
        tags=["general"],
    )
    manager.transition(1, AgentState.IDLE)
    return manager


@pytest.fixture
def manager_with_active_agent(manager_with_agent):
    """Manager with agent in ACTIVE state."""
    manager_with_agent.transition(1, AgentState.ACTIVE)
    return manager_with_agent


# ─── Data Models ───────────────────────────────────────────────────


class TestDataModels:
    """AgentRecord, BudgetConfig, BudgetState, HealthStatus."""

    def test_agent_record_defaults(self):
        r = AgentRecord(agent_id=1, name="Test", wallet_address="0x1")
        assert r.state == AgentState.INITIALIZING
        assert r.personality == "explorer"
        assert r.current_task_id is None
        assert r.cooldown_until is None
        assert r.created_at is not None
        assert r.state_changed_at is not None

    def test_budget_config_defaults(self):
        bc = BudgetConfig()
        assert bc.daily_limit_usd == 5.0
        assert bc.monthly_limit_usd == 100.0
        assert bc.task_limit_usd == 2.0
        assert bc.warning_threshold == 0.80
        assert bc.hard_stop_threshold == 1.0

    def test_budget_state_daily_reset(self):
        bs = BudgetState(daily_spent_usd=10.0, last_reset_date="2020-01-01")
        bs.check_daily_reset()
        assert bs.daily_spent_usd == 0.0
        assert bs.last_reset_date == datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def test_budget_state_no_reset_same_day(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        bs = BudgetState(daily_spent_usd=3.0, last_reset_date=today)
        bs.check_daily_reset()
        assert bs.daily_spent_usd == 3.0

    def test_budget_state_monthly_reset(self):
        bs = BudgetState(monthly_spent_usd=50.0, last_monthly_reset="2020-01")
        bs.check_monthly_reset()
        assert bs.monthly_spent_usd == 0.0

    def test_health_status_healthy(self):
        hs = HealthStatus(consecutive_missed=0)
        assert hs.is_healthy is True

    def test_health_status_unhealthy(self):
        hs = HealthStatus(consecutive_missed=3)
        assert hs.is_healthy is False

    def test_health_seconds_since_heartbeat_never(self):
        hs = HealthStatus()
        assert hs.seconds_since_heartbeat == float("inf")

    def test_health_seconds_since_heartbeat_recent(self):
        hs = HealthStatus(last_heartbeat=datetime.now(timezone.utc))
        assert hs.seconds_since_heartbeat < 5  # Should be nearly 0


# ─── State Machine ────────────────────────────────────────────────


class TestStateMachine:
    """Valid and invalid state transitions."""

    def test_valid_transitions_defined(self):
        """Every state should have at least one valid transition."""
        for state in AgentState:
            assert state in VALID_TRANSITIONS, f"Missing transitions for {state}"

    def test_initializing_to_idle(self, manager):
        manager.register_agent(1, "Test", "0x1")
        record = manager.transition(1, AgentState.IDLE)
        assert record.state == AgentState.IDLE

    def test_idle_to_active(self, manager_with_agent):
        record = manager_with_agent.transition(1, AgentState.ACTIVE)
        assert record.state == AgentState.ACTIVE

    def test_active_to_working(self, manager_with_active_agent):
        record = manager_with_active_agent.transition(1, AgentState.WORKING)
        assert record.state == AgentState.WORKING

    def test_working_to_cooldown(self, manager_with_active_agent):
        manager_with_active_agent.transition(1, AgentState.WORKING)
        record = manager_with_active_agent.transition(1, AgentState.COOLDOWN)
        assert record.state == AgentState.COOLDOWN

    def test_cooldown_to_idle(self, manager_with_active_agent):
        manager_with_active_agent.transition(1, AgentState.WORKING)
        manager_with_active_agent.transition(1, AgentState.COOLDOWN)
        record = manager_with_active_agent.transition(1, AgentState.IDLE)
        assert record.state == AgentState.IDLE

    def test_degraded_to_idle(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.DEGRADED)
        record = manager_with_agent.transition(1, AgentState.IDLE)
        assert record.state == AgentState.IDLE

    def test_suspended_to_idle(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.SUSPENDED)
        record = manager_with_agent.transition(1, AgentState.IDLE)
        assert record.state == AgentState.IDLE

    def test_invalid_idle_to_working(self, manager_with_agent):
        """Can't go from IDLE directly to WORKING (must go through ACTIVE)."""
        with pytest.raises(LifecycleError, match="Invalid transition"):
            manager_with_agent.transition(1, AgentState.WORKING)

    def test_invalid_working_to_active(self, manager_with_active_agent):
        """Can't go from WORKING back to ACTIVE."""
        manager_with_active_agent.transition(1, AgentState.WORKING)
        with pytest.raises(LifecycleError, match="Invalid transition"):
            manager_with_active_agent.transition(1, AgentState.ACTIVE)

    def test_invalid_cooldown_to_active(self, manager_with_active_agent):
        """Can't go from COOLDOWN to ACTIVE (must go to IDLE first)."""
        manager_with_active_agent.transition(1, AgentState.WORKING)
        manager_with_active_agent.transition(1, AgentState.COOLDOWN)
        with pytest.raises(LifecycleError):
            manager_with_active_agent.transition(1, AgentState.ACTIVE)

    def test_unknown_agent_raises(self, manager):
        with pytest.raises(LifecycleError, match="not found"):
            manager.transition(999, AgentState.IDLE)


# ─── Registration ─────────────────────────────────────────────────


class TestRegistration:
    """Agent registration and unregistration."""

    def test_register_agent(self, manager):
        record = manager.register_agent(
            1, "Aurora", "0xA", personality="explorer", tags=["gen"]
        )
        assert record.agent_id == 1
        assert record.name == "Aurora"
        assert record.state == AgentState.INITIALIZING
        assert "gen" in record.tags

    def test_register_duplicate_raises(self, manager):
        manager.register_agent(1, "A", "0x1")
        with pytest.raises(LifecycleError, match="already registered"):
            manager.register_agent(1, "B", "0x2")

    def test_unregister_agent(self, manager):
        manager.register_agent(1, "A", "0x1")
        manager.unregister_agent(1)
        assert 1 not in manager.agents

    def test_unregister_nonexistent_raises(self, manager):
        with pytest.raises(LifecycleError, match="not found"):
            manager.unregister_agent(999)

    def test_agents_property_returns_copy(self, manager):
        manager.register_agent(1, "A", "0x1")
        agents = manager.agents
        agents[2] = "fake"
        assert 2 not in manager.agents


# ─── Task Assignment ──────────────────────────────────────────────


class TestTaskAssignment:
    """Task assignment and completion lifecycle."""

    def test_assign_task_from_active(self, manager_with_active_agent):
        record = manager_with_active_agent.assign_task(1, "task-abc")
        assert record.state == AgentState.WORKING
        assert record.current_task_id == "task-abc"

    def test_assign_task_not_active_raises(self, manager_with_agent):
        """Must be ACTIVE to accept tasks."""
        with pytest.raises(LifecycleError, match="must be ACTIVE"):
            manager_with_agent.assign_task(1, "task-abc")

    def test_complete_task(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "task-abc")
        record = manager_with_active_agent.complete_task(1, cooldown_seconds=60)
        assert record.state == AgentState.COOLDOWN
        assert record.current_task_id is None
        assert record.cooldown_until is not None

    def test_complete_task_not_working_raises(self, manager_with_active_agent):
        with pytest.raises(LifecycleError, match="must be WORKING"):
            manager_with_active_agent.complete_task(1)


# ─── Cooldown ─────────────────────────────────────────────────────


class TestCooldown:
    """Cooldown expiry detection."""

    def test_cooldown_not_expired(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "t1")
        manager_with_active_agent.complete_task(1, cooldown_seconds=3600)
        transitioned = manager_with_active_agent.check_cooldown_expiry(1)
        assert transitioned is False

    def test_cooldown_expired(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "t1")
        manager_with_active_agent.complete_task(1, cooldown_seconds=0)
        # cooldown_until is set to now + 0 seconds = already expired
        # Force it to be in the past
        agent = manager_with_active_agent._agents[1]
        agent.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=10)
        transitioned = manager_with_active_agent.check_cooldown_expiry(1)
        assert transitioned is True
        assert agent.state == AgentState.IDLE

    def test_check_cooldown_not_in_cooldown(self, manager_with_agent):
        transitioned = manager_with_agent.check_cooldown_expiry(1)
        assert transitioned is False

    def test_cooldown_no_duration_set(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "t1")
        manager_with_active_agent.complete_task(1, cooldown_seconds=30)
        agent = manager_with_active_agent._agents[1]
        agent.cooldown_until = None  # Simulate missing cooldown
        transitioned = manager_with_active_agent.check_cooldown_expiry(1)
        assert transitioned is True


# ─── Budget ───────────────────────────────────────────────────────


class TestBudget:
    """Budget tracking and enforcement."""

    def test_record_spend(self, manager_with_agent):
        manager_with_agent.record_spend(1, 1.50)
        status = manager_with_agent.get_budget_status(1)
        assert status["daily_spent"] == 1.50

    def test_budget_daily_exceeded_suspends(self, manager_with_agent):
        with pytest.raises(BudgetExceededError):
            manager_with_agent.record_spend(1, 6.0)  # Default limit is $5
        agent = manager_with_agent._agents[1]
        assert agent.state == AgentState.SUSPENDED

    def test_budget_status_percentages(self, manager_with_agent):
        manager_with_agent.record_spend(1, 2.0)
        status = manager_with_agent.get_budget_status(1)
        assert status["daily_pct"] == 40.0  # 2/5 * 100
        assert status["at_warning"] is False
        assert status["at_limit"] is False

    def test_budget_warning_threshold(self, manager_with_agent):
        manager_with_agent.record_spend(1, 4.1)  # 82% of $5
        status = manager_with_agent.get_budget_status(1)
        assert status["at_warning"] is True
        assert status["at_limit"] is False

    def test_assign_task_budget_exceeded_blocks(self, manager_with_active_agent):
        """Can't assign task if budget is exceeded."""
        manager_with_active_agent.record_spend(1, 4.0)
        # We haven't exceeded yet, but let's exceed
        # Force daily budget over limit
        agent = manager_with_active_agent._agents[1]
        agent.budget_state.daily_spent_usd = 5.5
        with pytest.raises(BudgetExceededError):
            manager_with_active_agent.assign_task(1, "task-expensive")


# ─── Heartbeat ────────────────────────────────────────────────────


class TestHeartbeat:
    """Heartbeat monitoring and degradation."""

    def test_record_heartbeat(self, manager_with_agent):
        record = manager_with_agent.record_heartbeat(1)
        assert record.health.last_heartbeat is not None
        assert record.health.total_heartbeats == 1
        assert record.health.consecutive_missed == 0

    def test_record_heartbeat_recovers_degraded(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.DEGRADED)
        record = manager_with_agent.record_heartbeat(1)
        assert record.state == AgentState.IDLE

    def test_check_heartbeat_healthy(self, manager_with_agent):
        manager_with_agent.record_heartbeat(1)
        healthy = manager_with_agent.check_heartbeat(1)
        assert healthy is True

    def test_check_heartbeat_overdue_degrades(self, manager_with_agent):
        # Set heartbeat to long ago
        agent = manager_with_agent._agents[1]
        agent.health.last_heartbeat = datetime.now(timezone.utc) - timedelta(hours=1)
        agent.health.heartbeat_interval_seconds = 300  # 5 min

        # Need 3 consecutive misses to degrade
        manager_with_agent.check_heartbeat(1)
        manager_with_agent.check_heartbeat(1)
        healthy = manager_with_agent.check_heartbeat(1)
        assert healthy is False
        assert agent.state == AgentState.DEGRADED

    def test_record_error(self, manager_with_agent):
        manager_with_agent.record_error(1, "test error")
        agent = manager_with_agent._agents[1]
        assert agent.health.errors_last_hour == 1
        assert agent.health.last_error == "test error"


# ─── Available Agents ─────────────────────────────────────────────


class TestAvailableAgents:
    """get_available_agents() logic."""

    def test_idle_agent_available(self, manager_with_agent):
        available = manager_with_agent.get_available_agents()
        assert len(available) == 1
        assert available[0].agent_id == 1

    def test_active_agent_available(self, manager_with_active_agent):
        available = manager_with_active_agent.get_available_agents()
        assert len(available) == 1

    def test_working_agent_not_available(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "t1")
        available = manager_with_active_agent.get_available_agents()
        assert len(available) == 0

    def test_suspended_agent_not_available(self, manager_with_agent):
        manager_with_agent.transition(1, AgentState.SUSPENDED)
        available = manager_with_agent.get_available_agents()
        assert len(available) == 0

    def test_expired_cooldown_becomes_available(self, manager_with_active_agent):
        manager_with_active_agent.assign_task(1, "t1")
        manager_with_active_agent.complete_task(1, cooldown_seconds=0)
        agent = manager_with_active_agent._agents[1]
        agent.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=10)
        available = manager_with_active_agent.get_available_agents()
        assert len(available) == 1

    def test_budget_exceeded_not_available(self, manager_with_agent):
        agent = manager_with_agent._agents[1]
        # Set today's date so the reset check doesn't clear the spend
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        agent.budget_state.daily_spent_usd = 10.0  # Well over $5 limit
        agent.budget_state.last_reset_date = today
        agent.budget_state.last_monthly_reset = this_month
        available = manager_with_agent.get_available_agents()
        assert len(available) == 0


# ─── Swarm Status ─────────────────────────────────────────────────


class TestSwarmStatus:
    """get_swarm_status() overview."""

    def test_status_with_agents(self, manager):
        manager.register_agent(1, "A", "0x1")
        manager.transition(1, AgentState.IDLE)
        manager.register_agent(2, "B", "0x2")
        manager.transition(2, AgentState.IDLE)
        manager.transition(2, AgentState.DEGRADED)

        status = manager.get_swarm_status()
        assert status["total_agents"] == 2
        assert status["state_counts"]["idle"] == 1
        assert status["state_counts"]["degraded"] == 1
        assert 2 in status["degraded_agents"]

    def test_status_empty_swarm(self, manager):
        status = manager.get_swarm_status()
        assert status["total_agents"] == 0
        assert status["available_count"] == 0


# ─── Audit Log ────────────────────────────────────────────────────


class TestAuditLog:
    """State transition audit history."""

    def test_transitions_logged(self, manager):
        manager.register_agent(1, "A", "0x1")
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)

        history = manager.state_history
        assert len(history) >= 3  # register + 2 transitions
        last = history[-1]
        assert last["from"] == "idle"
        assert last["to"] == "active"
        assert "timestamp" in last

    def test_history_returns_copy(self, manager):
        manager.register_agent(1, "A", "0x1")
        h = manager.state_history
        h.append("fake")
        assert "fake" not in manager.state_history
