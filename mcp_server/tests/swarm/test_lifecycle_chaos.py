"""
Chaos & Stress tests for LifecycleManager.

Tests the agent state machine under adversarial conditions:
1. Large fleet (100+ agents) state management
2. Rapid state transitions
3. Budget exhaustion cascades
4. Heartbeat miss patterns
5. State machine boundary abuse
6. Registration/unregistration storms
7. Concurrent lifecycle operations
8. State history audit trail under load
9. Recovery patterns from degraded states
10. Edge cases in cooldown timing

These verify the lifecycle manager doesn't corrupt state under pressure.
"""

import pytest

from swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    BudgetConfig,
    LifecycleError,
    BudgetExceededError,
    VALID_TRANSITIONS,
)


# ─── Helpers ─────────────────────────────────────────────────────


def register_and_activate(lm, agent_id, name=None):
    """Register an agent and bring it to ACTIVE state."""
    name = name or f"agent-{agent_id}"
    wallet = f"0x{agent_id:040x}"
    lm.register_agent(agent_id, name, wallet, "explorer")
    lm.transition(agent_id, AgentState.IDLE)
    lm.transition(agent_id, AgentState.ACTIVE)
    return lm._agents[agent_id]


# ─── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def lm():
    return LifecycleManager()


# ─── Test: Large Fleet Management ────────────────────────────────


class TestLargeFleet:
    """Managing 100+ agents simultaneously."""

    def test_register_100_agents(self, lm):
        for i in range(100):
            lm.register_agent(i, f"agent-{i}", f"0x{i:040x}", "explorer")
        assert len(lm.agents) == 100

    def test_activate_100_agents(self, lm):
        for i in range(100):
            register_and_activate(lm, i)
        available = lm.get_available_agents()
        assert len(available) == 100

    def test_assign_100_tasks_to_100_agents(self, lm):
        for i in range(100):
            register_and_activate(lm, i)
            lm.assign_task(i, f"task-{i}")

        # All should be WORKING
        for i in range(100):
            assert lm._agents[i].state == AgentState.WORKING
            assert lm._agents[i].current_task_id == f"task-{i}"

        # No agents available
        assert len(lm.get_available_agents()) == 0

    def test_complete_100_tasks(self, lm):
        for i in range(100):
            register_and_activate(lm, i)
            lm.assign_task(i, f"task-{i}")
            lm.complete_task(i, cooldown_seconds=0)

        # All in COOLDOWN, but with 0s cooldown
        # get_available_agents checks cooldown expiry
        available = lm.get_available_agents()
        assert len(available) == 100  # Cooldown expired immediately

    def test_swarm_status_with_mixed_states(self, lm):
        """Fleet with agents in every possible state."""
        # INITIALIZING
        lm.register_agent(1, "init-agent", "0x01", "explorer")

        # IDLE
        lm.register_agent(2, "idle-agent", "0x02", "explorer")
        lm.transition(2, AgentState.IDLE)

        # ACTIVE
        register_and_activate(lm, 3)

        # WORKING
        register_and_activate(lm, 4)
        lm.assign_task(4, "task-4")

        # COOLDOWN
        register_and_activate(lm, 5)
        lm.assign_task(5, "task-5")
        lm.complete_task(5, cooldown_seconds=9999)

        # DEGRADED
        register_and_activate(lm, 6)
        lm.transition(6, AgentState.DEGRADED)

        # SUSPENDED
        register_and_activate(lm, 7)
        lm.transition(7, AgentState.SUSPENDED)

        status = lm.get_swarm_status()
        counts = status["state_counts"]
        assert counts["initializing"] == 1
        assert counts["idle"] == 1
        assert counts["active"] == 1
        assert counts["working"] == 1
        assert counts["cooldown"] == 1
        assert counts["degraded"] == 1
        assert counts["suspended"] == 1


# ─── Test: Rapid State Transitions ──────────────────────────────


class TestRapidTransitions:
    """State machine under rapid-fire transitions."""

    def test_full_lifecycle_loop_100_times(self, lm):
        """One agent cycling through the full lifecycle 100 times."""
        register_and_activate(lm, 1)

        for i in range(100):
            lm.assign_task(1, f"task-{i}")
            lm.complete_task(1, cooldown_seconds=0)
            # Cooldown → check expiry → IDLE
            lm.check_cooldown_expiry(1)
            assert lm._agents[1].state == AgentState.IDLE
            lm.transition(1, AgentState.ACTIVE)

        assert lm._agents[1].state == AgentState.ACTIVE

    def test_degrade_and_recover_50_times(self, lm):
        """Agent flapping between ACTIVE and DEGRADED."""
        register_and_activate(lm, 1)

        for _ in range(50):
            lm.transition(1, AgentState.DEGRADED)
            assert lm._agents[1].state == AgentState.DEGRADED
            lm.record_heartbeat(1)  # Recovery
            assert lm._agents[1].state == AgentState.IDLE
            lm.transition(1, AgentState.ACTIVE)
            assert lm._agents[1].state == AgentState.ACTIVE

    def test_suspend_and_resume_20_times(self, lm):
        """Agent repeatedly suspended and resumed."""
        register_and_activate(lm, 1)

        for _ in range(20):
            lm.transition(1, AgentState.SUSPENDED)
            assert lm._agents[1].state == AgentState.SUSPENDED
            lm.transition(1, AgentState.IDLE)
            assert lm._agents[1].state == AgentState.IDLE
            lm.transition(1, AgentState.ACTIVE)


# ─── Test: Invalid Transition Coverage ───────────────────────────


class TestInvalidTransitions:
    """Every invalid state transition should raise LifecycleError."""

    def test_all_invalid_transitions_raise(self, lm):
        """Systematically test all invalid transitions."""
        all_states = list(AgentState)
        errors = 0

        for from_state in all_states:
            valid_targets = VALID_TRANSITIONS.get(from_state, set())
            for to_state in all_states:
                if to_state in valid_targets:
                    continue  # This is valid, skip

                # Create a fresh agent in from_state
                agent_id = errors + 1000
                lm.register_agent(agent_id, f"test-{agent_id}", f"0x{agent_id:040x}")

                # Navigate to from_state
                try:
                    _navigate_to_state(lm, agent_id, from_state)
                except LifecycleError:
                    continue  # Can't reach this state, skip

                if lm._agents[agent_id].state != from_state:
                    continue

                # Now try the invalid transition
                with pytest.raises(LifecycleError):
                    lm.transition(agent_id, to_state)
                errors += 1

        assert errors > 0  # We should have found some invalid transitions

    def test_cannot_assign_task_from_idle(self, lm):
        lm.register_agent(1, "test", "0x01")
        lm.transition(1, AgentState.IDLE)
        with pytest.raises(LifecycleError, match="ACTIVE"):
            lm.assign_task(1, "task-1")

    def test_cannot_complete_from_active(self, lm):
        register_and_activate(lm, 1)
        with pytest.raises(LifecycleError, match="WORKING"):
            lm.complete_task(1)

    def test_cannot_complete_from_idle(self, lm):
        lm.register_agent(1, "test", "0x01")
        lm.transition(1, AgentState.IDLE)
        with pytest.raises(LifecycleError, match="WORKING"):
            lm.complete_task(1)


def _navigate_to_state(lm, agent_id, target_state):
    """Navigate an agent from INITIALIZING to the target state."""
    current = lm._agents[agent_id].state

    if current == target_state:
        return

    # Define paths to each state
    paths = {
        AgentState.INITIALIZING: [],
        AgentState.IDLE: [AgentState.IDLE],
        AgentState.ACTIVE: [AgentState.IDLE, AgentState.ACTIVE],
        AgentState.WORKING: [AgentState.IDLE, AgentState.ACTIVE],  # + assign_task
        AgentState.COOLDOWN: [
            AgentState.IDLE,
            AgentState.ACTIVE,
        ],  # + assign + complete
        AgentState.DEGRADED: [AgentState.IDLE, AgentState.DEGRADED],
        AgentState.SUSPENDED: [AgentState.IDLE, AgentState.SUSPENDED],
    }

    path = paths.get(target_state, [])
    for state in path:
        if lm._agents[agent_id].state != state:
            lm.transition(agent_id, state)

    if target_state == AgentState.WORKING:
        lm.assign_task(agent_id, f"nav-task-{agent_id}")
    elif target_state == AgentState.COOLDOWN:
        lm.assign_task(agent_id, f"nav-task-{agent_id}")
        lm.complete_task(agent_id, cooldown_seconds=9999)


# ─── Test: Budget Stress ─────────────────────────────────────────


class TestBudgetStress:
    """Budget system under financial pressure."""

    def test_budget_exhaustion(self, lm):
        """Spending up to the daily limit triggers BudgetExceededError."""
        config = BudgetConfig(daily_limit_usd=10.0, monthly_limit_usd=100.0)
        lm.register_agent(1, "spender", "0x01", budget_config=config)
        lm.transition(1, AgentState.IDLE)

        # Spend in increments — record_spend checks budget and raises
        for i in range(9):
            lm.record_spend(1, 1.0)  # 9.0 total, under limit

        # The 10th spend hits the limit
        with pytest.raises(BudgetExceededError):
            lm.record_spend(1, 1.0)

        # Budget should show 10.0 spent (the amount was added before check)
        assert lm._agents[1].budget_state.daily_spent_usd == 10.0

    def test_budget_excluded_from_available(self, lm):
        """Budget-exceeded agents excluded from available list."""
        config = BudgetConfig(daily_limit_usd=2.0)
        lm.register_agent(1, "broke", "0x01", budget_config=config)
        lm.transition(1, AgentState.IDLE)
        lm.transition(1, AgentState.ACTIVE)

        # Spend up to limit (record_spend raises on exceed)
        lm.record_spend(1, 1.5)  # Under limit, fine
        with pytest.raises(BudgetExceededError):
            lm.record_spend(1, 0.5)  # Hits limit

        # Agent 1 is ACTIVE but over budget
        register_and_activate(lm, 2)  # Agent 2 is fine

        available = lm.get_available_agents()
        agent_ids = [a.agent_id for a in available]
        assert 1 not in agent_ids
        assert 2 in agent_ids

    def test_many_small_spends(self, lm):
        """1000 small spends that add up."""
        config = BudgetConfig(daily_limit_usd=10.0)
        lm.register_agent(1, "micro-spender", "0x01", budget_config=config)
        lm.transition(1, AgentState.IDLE)

        for _ in range(1000):
            lm.record_spend(1, 0.009)

        assert lm._agents[1].budget_state.daily_spent_usd == pytest.approx(
            9.0, abs=0.01
        )

    def test_budget_status_accuracy(self, lm):
        """Budget status reports correct percentages."""
        config = BudgetConfig(daily_limit_usd=10.0, monthly_limit_usd=100.0)
        lm.register_agent(1, "tracked", "0x01", budget_config=config)
        lm.transition(1, AgentState.IDLE)

        lm.record_spend(1, 5.0)
        status = lm.get_budget_status(1)
        assert status["daily_pct"] == pytest.approx(50.0, abs=0.1)


# ─── Test: Heartbeat Patterns ────────────────────────────────────


class TestHeartbeatPatterns:
    """Heartbeat monitoring edge cases."""

    def test_heartbeat_recovery_from_degraded(self, lm):
        """Degraded agent recovers via heartbeat."""
        register_and_activate(lm, 1)
        lm.transition(1, AgentState.DEGRADED)
        assert lm._agents[1].state == AgentState.DEGRADED

        lm.record_heartbeat(1)
        assert lm._agents[1].state == AgentState.IDLE

    def test_many_heartbeats(self, lm):
        """Recording 1000 heartbeats doesn't cause issues."""
        register_and_activate(lm, 1)

        for _ in range(1000):
            lm.record_heartbeat(1)

        assert lm._agents[1].health.total_heartbeats == 1000
        assert lm._agents[1].health.consecutive_missed == 0

    def test_heartbeat_from_non_degraded_doesnt_change_state(self, lm):
        """Heartbeat from ACTIVE agent keeps it ACTIVE."""
        register_and_activate(lm, 1)
        assert lm._agents[1].state == AgentState.ACTIVE

        lm.record_heartbeat(1)
        assert lm._agents[1].state == AgentState.ACTIVE

    def test_error_recording(self, lm):
        """Recording errors accumulates correctly."""
        register_and_activate(lm, 1)

        for i in range(20):
            lm.record_error(1, f"error-{i}")

        assert lm._agents[1].health.errors_last_hour == 20
        assert lm._agents[1].health.last_error == "error-19"


# ─── Test: Registration Edge Cases ──────────────────────────────


class TestRegistrationEdgeCases:
    """Registration and unregistration boundary cases."""

    def test_duplicate_registration_raises(self, lm):
        lm.register_agent(1, "first", "0x01")
        with pytest.raises(LifecycleError, match="already registered"):
            lm.register_agent(1, "duplicate", "0x01")

    def test_unregister_nonexistent_raises(self, lm):
        with pytest.raises(LifecycleError, match="not found"):
            lm.unregister_agent(999)

    def test_register_unregister_100_agents(self, lm):
        """Register and unregister 100 agents."""
        for i in range(100):
            lm.register_agent(i, f"agent-{i}", f"0x{i:040x}")
        assert len(lm.agents) == 100

        for i in range(100):
            lm.unregister_agent(i)
        assert len(lm.agents) == 0

    def test_reuse_agent_id_after_unregister(self, lm):
        """Unregistered agent ID can be reused."""
        lm.register_agent(1, "first", "0x01")
        lm.unregister_agent(1)
        lm.register_agent(1, "second", "0x02")
        assert lm._agents[1].name == "second"
        assert lm._agents[1].wallet_address == "0x02"

    def test_operations_on_nonexistent_agent(self, lm):
        """Operations on unregistered agents should raise."""
        with pytest.raises(LifecycleError):
            lm.transition(999, AgentState.IDLE)
        with pytest.raises(LifecycleError):
            lm.assign_task(999, "task-1")
        with pytest.raises(LifecycleError):
            lm.complete_task(999)
        with pytest.raises(LifecycleError):
            lm.record_heartbeat(999)


# ─── Test: State History Audit Trail ─────────────────────────────


class TestStateHistory:
    """Audit trail accuracy under load."""

    def test_history_grows_with_transitions(self, lm):
        """Each transition adds to history."""
        register_and_activate(lm, 1)
        # INITIALIZING registered + IDLE + ACTIVE = 3 entries
        history = lm.state_history
        assert len(history) >= 3

    def test_history_after_100_agents_cycling(self, lm):
        """100 agents each doing 5 transitions = 500+ history entries."""
        for i in range(100):
            register_and_activate(lm, i)
            lm.assign_task(i, f"task-{i}")
            lm.complete_task(i, cooldown_seconds=0)

        history = lm.state_history
        # Each agent: register(1) + IDLE(1) + ACTIVE(1) + WORKING(1) + COOLDOWN(1) = 5
        assert len(history) >= 500

    def test_history_contains_agent_ids(self, lm):
        register_and_activate(lm, 42)
        history = lm.state_history
        agent_42_entries = [h for h in history if h.get("agent_id") == 42]
        assert len(agent_42_entries) >= 3


# ─── Test: Cooldown Edge Cases ───────────────────────────────────


class TestCooldownEdgeCases:
    """Cooldown timing and expiry edge cases."""

    def test_zero_cooldown_expires_immediately(self, lm):
        register_and_activate(lm, 1)
        lm.assign_task(1, "task-1")
        lm.complete_task(1, cooldown_seconds=0)

        assert lm._agents[1].state == AgentState.COOLDOWN
        expired = lm.check_cooldown_expiry(1)
        assert expired
        assert lm._agents[1].state == AgentState.IDLE

    def test_check_cooldown_not_in_cooldown(self, lm):
        """Checking cooldown on non-COOLDOWN agent returns False."""
        register_and_activate(lm, 1)
        assert not lm.check_cooldown_expiry(1)

    def test_long_cooldown_doesnt_expire(self, lm):
        """Agent with very long cooldown stays in COOLDOWN."""
        register_and_activate(lm, 1)
        lm.assign_task(1, "task-1")
        lm.complete_task(1, cooldown_seconds=999999)

        assert not lm.check_cooldown_expiry(1)
        assert lm._agents[1].state == AgentState.COOLDOWN

    def test_cooldown_none_until(self, lm):
        """Agent in COOLDOWN with None cooldown_until transitions immediately."""
        register_and_activate(lm, 1)
        lm.assign_task(1, "task-1")
        lm.complete_task(1, cooldown_seconds=0)

        # Manually set cooldown_until to None
        lm._agents[1].cooldown_until = None
        expired = lm.check_cooldown_expiry(1)
        assert expired
        assert lm._agents[1].state == AgentState.IDLE


# ─── Test: Stress Patterns ───────────────────────────────────────


class TestStressPatterns:
    """High-volume operation patterns."""

    def test_50_agents_full_lifecycle_simultaneously(self, lm):
        """All 50 agents progress through full lifecycle in lockstep."""
        agents = list(range(50))

        # Register all
        for a in agents:
            lm.register_agent(a, f"agent-{a}", f"0x{a:040x}")

        # IDLE
        for a in agents:
            lm.transition(a, AgentState.IDLE)

        # ACTIVE
        for a in agents:
            lm.transition(a, AgentState.ACTIVE)

        # WORKING
        for a in agents:
            lm.assign_task(a, f"task-{a}")

        # Verify all WORKING
        for a in agents:
            assert lm._agents[a].state == AgentState.WORKING

        # COOLDOWN
        for a in agents:
            lm.complete_task(a, cooldown_seconds=0)

        # Back to IDLE
        for a in agents:
            lm.check_cooldown_expiry(a)

        for a in agents:
            assert lm._agents[a].state == AgentState.IDLE

    def test_agent_tags_preserved_through_lifecycle(self, lm):
        """Custom tags survive state transitions."""
        lm.register_agent(1, "tagged", "0x01", tags=["fast", "reliable"])
        lm.transition(1, AgentState.IDLE)
        lm.transition(1, AgentState.ACTIVE)
        lm.assign_task(1, "task-1")
        lm.complete_task(1, cooldown_seconds=0)

        assert lm._agents[1].tags == ["fast", "reliable"]

    def test_swarm_status_accuracy(self, lm):
        """Swarm status counts match reality."""
        for i in range(10):
            register_and_activate(lm, i)

        # Put 5 in WORKING
        for i in range(5):
            lm.assign_task(i, f"task-{i}")

        status = lm.get_swarm_status()
        counts = status["state_counts"]
        assert counts["active"] == 5
        assert counts["working"] == 5

    def test_state_changed_at_updates(self, lm):
        """state_changed_at updates on every transition."""
        register_and_activate(lm, 1)
        t1 = lm._agents[1].state_changed_at

        lm.assign_task(1, "task-1")
        t2 = lm._agents[1].state_changed_at

        assert t2 >= t1

    def test_personality_preserved(self, lm):
        """Agent personality survives transitions."""
        lm.register_agent(1, "explorer-1", "0x01", personality="guardian")
        lm.transition(1, AgentState.IDLE)
        lm.transition(1, AgentState.ACTIVE)

        assert lm._agents[1].personality == "guardian"
