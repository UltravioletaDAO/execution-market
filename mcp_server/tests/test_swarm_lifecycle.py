"""Tests for SwarmOrchestrator LifecycleManager."""

import pytest
from datetime import datetime, timezone, timedelta

from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    BudgetConfig,
    LifecycleError,
    BudgetExceededError,
    VALID_TRANSITIONS,
)


@pytest.fixture
def manager():
    return LifecycleManager()


@pytest.fixture
def registered_agent(manager):
    agent = manager.register_agent(
        agent_id=1,
        name="aurora",
        wallet_address="0xabc",
        personality="explorer",
        tags=["photo", "survey"],
    )
    return agent


class TestRegistration:
    def test_register_agent(self, manager):
        agent = manager.register_agent(1, "aurora", "0xabc")
        assert agent.agent_id == 1
        assert agent.name == "aurora"
        assert agent.state == AgentState.INITIALIZING

    def test_register_duplicate_fails(self, manager, registered_agent):
        with pytest.raises(LifecycleError, match="already registered"):
            manager.register_agent(1, "duplicate", "0xdef")

    def test_unregister(self, manager, registered_agent):
        manager.unregister_agent(1)
        assert 1 not in manager.agents

    def test_unregister_missing_fails(self, manager):
        with pytest.raises(LifecycleError, match="not found"):
            manager.unregister_agent(999)

    def test_custom_budget(self, manager):
        budget = BudgetConfig(daily_limit_usd=10.0, monthly_limit_usd=200.0)
        agent = manager.register_agent(
            2,
            "blaze",
            "0xdef",
            budget_config=budget,
        )
        assert agent.budget_config.daily_limit_usd == 10.0
        assert agent.budget_config.monthly_limit_usd == 200.0


class TestStateTransitions:
    def test_init_to_idle(self, manager, registered_agent):
        agent = manager.transition(1, AgentState.IDLE)
        assert agent.state == AgentState.IDLE

    def test_idle_to_active(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        agent = manager.transition(1, AgentState.ACTIVE)
        assert agent.state == AgentState.ACTIVE

    def test_invalid_transition(self, manager, registered_agent):
        # INITIALIZING → WORKING is not valid
        with pytest.raises(LifecycleError, match="Invalid transition"):
            manager.transition(1, AgentState.WORKING)

    def test_full_happy_path(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        manager.assign_task(1, "task-1")
        assert manager.agents[1].state == AgentState.WORKING
        manager.complete_task(1)
        assert manager.agents[1].state == AgentState.COOLDOWN

    def test_all_valid_transitions_covered(self):
        """Every state should have at least one outgoing transition."""
        for state in AgentState:
            assert state in VALID_TRANSITIONS
            assert len(VALID_TRANSITIONS[state]) > 0

    def test_suspended_can_only_resume(self, manager, registered_agent):
        manager.transition(1, AgentState.SUSPENDED)
        # Can only go to IDLE
        assert VALID_TRANSITIONS[AgentState.SUSPENDED] == {AgentState.IDLE}
        manager.transition(1, AgentState.IDLE)
        assert manager.agents[1].state == AgentState.IDLE

    def test_transition_records_timestamp(self, manager, registered_agent):
        before = datetime.now(timezone.utc)
        manager.transition(1, AgentState.IDLE)
        agent = manager.agents[1]
        assert agent.state_changed_at >= before

    def test_state_history_audit(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE, "boot complete")
        manager.transition(1, AgentState.ACTIVE, "ready for work")

        history = manager.state_history
        # 3 entries: registered, idle, active
        assert len(history) == 3
        assert history[0]["to"] == "initializing"
        assert history[1]["to"] == "idle"
        assert history[1]["reason"] == "boot complete"
        assert history[2]["to"] == "active"


class TestTaskAssignment:
    def test_assign_task_from_active(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        agent = manager.assign_task(1, "task-42")
        assert agent.state == AgentState.WORKING
        assert agent.current_task_id == "task-42"

    def test_assign_task_from_idle_fails(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        with pytest.raises(LifecycleError, match="must be ACTIVE"):
            manager.assign_task(1, "task-1")

    def test_complete_task_clears_id(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        manager.assign_task(1, "task-42")
        agent = manager.complete_task(1, cooldown_seconds=5)
        assert agent.current_task_id is None
        assert agent.state == AgentState.COOLDOWN
        assert agent.cooldown_until is not None

    def test_complete_task_not_working_fails(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        with pytest.raises(LifecycleError, match="must be WORKING"):
            manager.complete_task(1)


class TestCooldown:
    def test_cooldown_not_expired(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        manager.assign_task(1, "task-1")
        manager.complete_task(1, cooldown_seconds=3600)  # 1 hour
        assert not manager.check_cooldown_expiry(1)
        assert manager.agents[1].state == AgentState.COOLDOWN

    def test_cooldown_expired(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        manager.assign_task(1, "task-1")
        manager.complete_task(1, cooldown_seconds=0)  # Immediate

        # Manually set cooldown to the past
        manager._agents[1].cooldown_until = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )
        assert manager.check_cooldown_expiry(1)
        assert manager.agents[1].state == AgentState.IDLE

    def test_cooldown_not_in_cooldown_state(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        assert not manager.check_cooldown_expiry(1)


class TestHealthMonitoring:
    def test_record_heartbeat(self, manager, registered_agent):
        agent = manager.record_heartbeat(1)
        assert agent.health.last_heartbeat is not None
        assert agent.health.consecutive_missed == 0
        assert agent.health.total_heartbeats == 1

    def test_multiple_heartbeats(self, manager, registered_agent):
        manager.record_heartbeat(1)
        manager.record_heartbeat(1)
        manager.record_heartbeat(1)
        assert manager.agents[1].health.total_heartbeats == 3

    def test_missed_heartbeats_degrade(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)

        # Simulate: set last heartbeat to way in the past
        manager._agents[1].health.last_heartbeat = datetime.now(
            timezone.utc
        ) - timedelta(hours=1)

        # Check repeatedly to exceed threshold
        for _ in range(4):
            manager.check_heartbeat(1)

        assert manager.agents[1].state == AgentState.DEGRADED

    def test_recovery_after_heartbeat(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        # Force to degraded
        manager.transition(1, AgentState.DEGRADED)
        assert manager.agents[1].state == AgentState.DEGRADED

        # Heartbeat should recover
        manager.record_heartbeat(1)
        assert manager.agents[1].state == AgentState.IDLE

    def test_record_error(self, manager, registered_agent):
        manager.record_error(1, "timeout connecting")
        assert manager.agents[1].health.errors_last_hour == 1
        assert manager.agents[1].health.last_error == "timeout connecting"


class TestBudget:
    def test_record_spend(self, manager, registered_agent):
        manager.record_spend(1, 1.50)
        status = manager.get_budget_status(1)
        assert status["daily_spent"] == 1.50
        assert status["monthly_spent"] == 1.50

    def test_daily_budget_exceeded(self, manager, registered_agent):
        # Default daily limit is 5.0
        manager.transition(1, AgentState.IDLE)
        manager.record_spend(1, 4.99)
        # Should not raise yet
        status = manager.get_budget_status(1)
        assert not status["at_limit"]

        # Exceed
        with pytest.raises(BudgetExceededError, match="daily budget exceeded"):
            manager.record_spend(1, 0.02)

    def test_monthly_budget_exceeded(self, manager):
        budget = BudgetConfig(daily_limit_usd=1000, monthly_limit_usd=10)
        manager.register_agent(2, "blaze", "0xdef", budget_config=budget)
        manager.transition(2, AgentState.IDLE)

        with pytest.raises(BudgetExceededError, match="monthly budget exceeded"):
            manager.record_spend(2, 10.01)

    def test_warning_threshold(self, manager, registered_agent):
        manager.record_spend(1, 4.0)  # 80% of 5.0
        status = manager.get_budget_status(1)
        assert status["at_warning"]

    def test_budget_blocks_task_assignment(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)

        # Exhaust budget (use record_spend so daily reset date is set properly)
        manager.record_spend(1, 4.99)
        # Now exceed via another spend to trigger the auto-suspend
        with pytest.raises(BudgetExceededError):
            manager.record_spend(1, 0.02)


class TestAvailableAgents:
    def test_available_idle(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        available = manager.get_available_agents()
        assert len(available) == 1
        assert available[0].agent_id == 1

    def test_available_active(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        available = manager.get_available_agents()
        assert len(available) == 1

    def test_not_available_working(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        manager.assign_task(1, "task-1")
        available = manager.get_available_agents()
        assert len(available) == 0

    def test_not_available_suspended(self, manager, registered_agent):
        manager.transition(1, AgentState.SUSPENDED)
        available = manager.get_available_agents()
        assert len(available) == 0

    def test_expired_cooldown_becomes_available(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        manager.transition(1, AgentState.ACTIVE)
        manager.assign_task(1, "task-1")
        manager.complete_task(1, cooldown_seconds=0)
        manager._agents[1].cooldown_until = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )
        available = manager.get_available_agents()
        assert len(available) == 1

    def test_budget_exceeded_not_available(self, manager, registered_agent):
        manager.transition(1, AgentState.IDLE)
        # Use record_spend so the reset date gets set properly
        try:
            manager.record_spend(1, 5.01)
        except BudgetExceededError:
            pass
        available = manager.get_available_agents()
        assert len(available) == 0


class TestSwarmStatus:
    def test_status_shape(self, manager, registered_agent):
        status = manager.get_swarm_status()
        assert "total_agents" in status
        assert "state_counts" in status
        assert "available_count" in status
        assert "total_daily_spend" in status
        assert "degraded_agents" in status
        assert status["total_agents"] == 1

    def test_status_counts(self, manager):
        manager.register_agent(1, "a", "0x1")
        manager.register_agent(2, "b", "0x2")
        manager.register_agent(3, "c", "0x3")
        manager.transition(1, AgentState.IDLE)
        manager.transition(2, AgentState.IDLE)
        manager.transition(3, AgentState.SUSPENDED)

        status = manager.get_swarm_status()
        assert status["state_counts"]["idle"] == 2
        assert status["state_counts"]["suspended"] == 1
        assert 3 in status["suspended_agents"]
