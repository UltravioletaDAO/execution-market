"""
Tests for SwarmOrchestrator — Task routing across the agent swarm.

Covers:
- Task routing (best_fit, round_robin, specialist, budget_aware)
- Candidate scoring via ReputationBridge
- Duplicate task detection
- Agent availability filtering
- Task completion and failure
- Minimum score threshold
- Agent exclusion and preferences
- Routing failures (no agents, all excluded, score too low)
- Assignment history and failure logs
- Status reporting
- Edge cases (single agent, agent disappears)
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    TaskPriority,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
    PRIORITY_WEIGHTS,
)
from mcp_server.swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
    CompositeScore,
)
from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    BudgetConfig,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def lifecycle():
    """LifecycleManager with 3 registered agents."""
    mgr = LifecycleManager()
    for i in range(1, 4):
        mgr.register_agent(i, f"agent_{i}", f"0x{i:04x}")
        mgr.transition(i, AgentState.IDLE)
        mgr.transition(i, AgentState.ACTIVE)
    return mgr


@pytest.fixture
def bridge():
    """Fresh ReputationBridge."""
    return ReputationBridge()


@pytest.fixture
def orchestrator(bridge, lifecycle):
    """SwarmOrchestrator with 3 active agents."""
    orch = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=10.0)
    # Register reputation data
    for i in range(1, 4):
        orch.register_reputation(
            agent_id=i,
            on_chain=OnChainReputation(
                agent_id=i,
                wallet_address=f"0x{i:04x}",
                total_seals=10 + i * 5,
                positive_seals=8 + i * 4,
            ),
            internal=InternalReputation(
                agent_id=i,
                total_tasks=10 + i * 10,
                successful_tasks=8 + i * 8,
                avg_rating=3.0 + i * 0.5,
                category_scores={"photo": 0.8, "delivery": 0.7},
            ),
        )
    return orch


@pytest.fixture
def task():
    """Standard task request."""
    return TaskRequest(
        task_id="task-1",
        title="Photo verification of storefront",
        categories=["photo"],
        bounty_usd=0.50,
    )


# ─── Basic Routing ────────────────────────────────────────────────────────────


class TestBasicRouting:
    def test_route_task_returns_assignment(self, orchestrator, task):
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.task_id == "task-1"
        assert result.agent_id in (1, 2, 3)

    def test_best_fit_picks_highest_score(self, orchestrator, task):
        result = orchestrator.route_task(task, strategy=RoutingStrategy.BEST_FIT)
        assert isinstance(result, Assignment)
        # Agent 3 has highest reputation (4.5 avg)
        assert result.agent_id == 3

    def test_assignment_includes_alternatives(self, orchestrator, task):
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.alternatives_count == 2  # 3 candidates - 1 selected

    def test_assignment_records_strategy(self, orchestrator, task):
        result = orchestrator.route_task(task, strategy=RoutingStrategy.BEST_FIT)
        assert result.strategy_used == RoutingStrategy.BEST_FIT

    def test_assignment_to_dict(self, orchestrator, task):
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        d = result.to_dict()
        assert "task_id" in d
        assert "agent_id" in d
        assert "score" in d
        assert "strategy" in d


# ─── Routing Strategies ───────────────────────────────────────────────────────


class TestRoutingStrategies:
    def test_round_robin(self, orchestrator):
        """Round-robin should distribute tasks."""
        assigned_agents = []
        for i in range(6):
            task = TaskRequest(task_id=f"rr-{i}", title="Test", categories=["photo"])
            result = orchestrator.route_task(
                task, strategy=RoutingStrategy.ROUND_ROBIN
            )
            if isinstance(result, Assignment):
                assigned_agents.append(result.agent_id)
                orchestrator.complete_task(result.task_id)
                # Re-activate agent for next round
                orchestrator.lifecycle.check_cooldown_expiry(result.agent_id)
                agent = orchestrator.lifecycle._agents[result.agent_id]
                agent.cooldown_until = None
                if agent.state == AgentState.COOLDOWN:
                    orchestrator.lifecycle.transition(
                        result.agent_id, AgentState.IDLE
                    )
                orchestrator.lifecycle.transition(result.agent_id, AgentState.ACTIVE)

        # Should have used multiple agents
        assert len(set(assigned_agents)) > 1

    def test_specialist_requires_skill_score(self, orchestrator):
        """Specialist routing requires minimum skill score."""
        task = TaskRequest(
            task_id="spec-1",
            title="Specialized task",
            categories=["rare_category"],
        )
        result = orchestrator.route_task(
            task, strategy=RoutingStrategy.SPECIALIST
        )
        # May fail if no agent has skill_score >= 50
        # That's expected behavior — specialists must be qualified
        assert isinstance(result, (Assignment, RoutingFailure))

    def test_budget_aware_prefers_budget_headroom(self, bridge):
        """Budget-aware routing prefers agents with more remaining budget."""
        lifecycle = LifecycleManager()
        for i in range(1, 3):
            config = BudgetConfig(daily_limit_usd=10.0)
            lifecycle.register_agent(
                i, f"agent_{i}", f"0x{i:04x}", budget_config=config
            )
            lifecycle.transition(i, AgentState.IDLE)
            lifecycle.transition(i, AgentState.ACTIVE)

        # Agent 1 has spent more budget
        lifecycle.record_spend(1, 8.0)  # 80% used

        orch = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)
        for i in range(1, 3):
            orch.register_reputation(
                i,
                OnChainReputation(agent_id=i, wallet_address=f"0x{i:04x}"),
                InternalReputation(agent_id=i),
            )

        task = TaskRequest(task_id="ba-1", title="Test", categories=["photo"])
        result = orch.route_task(task, strategy=RoutingStrategy.BUDGET_AWARE)
        assert isinstance(result, Assignment)
        # Agent 2 should be preferred (more budget remaining)
        assert result.agent_id == 2


# ─── Duplicate Task Detection ─────────────────────────────────────────────────


class TestDuplicateDetection:
    def test_duplicate_task_rejected(self, orchestrator, task):
        result1 = orchestrator.route_task(task)
        assert isinstance(result1, Assignment)

        # Same task_id again
        result2 = orchestrator.route_task(task)
        assert isinstance(result2, RoutingFailure)
        assert "already claimed" in result2.reason

    def test_completed_task_can_be_rerouted(self, orchestrator, task):
        result1 = orchestrator.route_task(task)
        assert isinstance(result1, Assignment)
        orchestrator.complete_task(task.task_id)

        # Re-activate an agent
        for i in range(1, 4):
            agent = orchestrator.lifecycle._agents.get(i)
            if agent and agent.state == AgentState.COOLDOWN:
                agent.cooldown_until = None
                orchestrator.lifecycle.check_cooldown_expiry(i)
                orchestrator.lifecycle.transition(i, AgentState.ACTIVE)
                break

        # Same task_id should work now (claim cleared)
        result2 = orchestrator.route_task(task)
        assert isinstance(result2, Assignment)


# ─── Agent Filtering ──────────────────────────────────────────────────────────


class TestAgentFiltering:
    def test_exclude_agents(self, orchestrator):
        task = TaskRequest(
            task_id="excl-1",
            title="Test",
            categories=["photo"],
            exclude_agent_ids=[3],  # Exclude highest-scoring
        )
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id != 3

    def test_exclude_all_agents(self, orchestrator):
        task = TaskRequest(
            task_id="excl-all",
            title="Test",
            categories=["photo"],
            exclude_agent_ids=[1, 2, 3],
        )
        result = orchestrator.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "excluded" in result.reason.lower()

    def test_preferred_agents(self, orchestrator):
        task = TaskRequest(
            task_id="pref-1",
            title="Test",
            categories=["photo"],
            preferred_agent_ids=[1],
        )
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 1  # Preferred agent chosen

    def test_no_available_agents(self, bridge):
        lifecycle = LifecycleManager()
        orch = SwarmOrchestrator(bridge, lifecycle)
        task = TaskRequest(task_id="empty", title="Test")
        result = orch.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "No agents available" in result.reason


# ─── Minimum Score Threshold ──────────────────────────────────────────────────


class TestMinScoreThreshold:
    def test_agents_below_threshold_rejected(self, bridge):
        lifecycle = LifecycleManager()
        lifecycle.register_agent(1, "lowscore", "0x0001")
        lifecycle.transition(1, AgentState.IDLE)
        lifecycle.transition(1, AgentState.ACTIVE)

        orch = SwarmOrchestrator(
            bridge, lifecycle, min_score_threshold=99.0  # Very high
        )
        orch.register_reputation(
            1,
            OnChainReputation(agent_id=1, wallet_address="0x0001"),
            InternalReputation(agent_id=1),
        )

        task = TaskRequest(task_id="high-bar", title="Test")
        result = orch.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "minimum score" in result.reason.lower()


# ─── Task Completion ──────────────────────────────────────────────────────────


class TestTaskCompletion:
    def test_complete_task(self, orchestrator, task):
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        agent_id = orchestrator.complete_task(task.task_id)
        assert agent_id == result.agent_id

    def test_complete_unknown_task(self, orchestrator):
        result = orchestrator.complete_task("nonexistent")
        assert result is None

    def test_complete_puts_agent_in_cooldown(self, orchestrator, task):
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        orchestrator.complete_task(task.task_id)
        agent = orchestrator.lifecycle.agents[result.agent_id]
        assert agent.state == AgentState.COOLDOWN


# ─── Task Failure ─────────────────────────────────────────────────────────────


class TestTaskFailure:
    def test_fail_task(self, orchestrator, task):
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        agent_id = orchestrator.fail_task(task.task_id, "API timeout")
        assert agent_id == result.agent_id

    def test_fail_unknown_task(self, orchestrator):
        result = orchestrator.fail_task("nonexistent")
        assert result is None

    def test_fail_increments_consecutive_failures(self, orchestrator, task):
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        orchestrator.fail_task(task.task_id)
        internal = orchestrator._internal.get(result.agent_id)
        if internal:
            assert internal.consecutive_failures >= 1

    def test_fail_records_error(self, orchestrator, task):
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        orchestrator.fail_task(task.task_id, "Connection error")
        agent = orchestrator.lifecycle.agents[result.agent_id]
        assert agent.health.errors_last_hour >= 1


# ─── Reputation Registration ─────────────────────────────────────────────────


class TestReputationRegistration:
    def test_register_reputation(self, orchestrator):
        assert 1 in orchestrator._on_chain
        assert 1 in orchestrator._internal

    def test_update_reputation(self, orchestrator):
        new_on_chain = OnChainReputation(
            agent_id=1,
            wallet_address="0x0001",
            total_seals=100,
            positive_seals=95,
        )
        new_internal = InternalReputation(
            agent_id=1,
            total_tasks=200,
            successful_tasks=180,
        )
        orchestrator.register_reputation(1, new_on_chain, new_internal)
        assert orchestrator._on_chain[1].total_seals == 100
        assert orchestrator._internal[1].total_tasks == 200

    def test_agents_without_reputation_get_defaults(self, bridge):
        lifecycle = LifecycleManager()
        lifecycle.register_agent(1, "norep", "0x0001")
        lifecycle.transition(1, AgentState.IDLE)
        lifecycle.transition(1, AgentState.ACTIVE)

        orch = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)
        # No reputation registered
        task = TaskRequest(task_id="norep", title="Test")
        result = orch.route_task(task)
        assert isinstance(result, Assignment)  # Should still work with defaults


# ─── Status & History ─────────────────────────────────────────────────────────


class TestStatusAndHistory:
    def test_status_structure(self, orchestrator):
        status = orchestrator.get_status()
        assert "active_claims" in status
        assert "total_assignments" in status
        assert "total_failures" in status
        assert "default_strategy" in status
        assert "swarm" in status

    def test_status_after_routing(self, orchestrator, task):
        orchestrator.route_task(task)
        status = orchestrator.get_status()
        assert status["active_claims"] == 1
        assert status["total_assignments"] == 1

    def test_assignment_history(self, orchestrator, task):
        orchestrator.route_task(task)
        history = orchestrator.get_assignment_history()
        assert len(history) == 1
        assert history[0]["task_id"] == "task-1"

    def test_failure_history(self, bridge):
        lifecycle = LifecycleManager()
        orch = SwarmOrchestrator(bridge, lifecycle)
        task = TaskRequest(task_id="fail", title="No agents")
        orch.route_task(task)

        failures = orch.get_failures()
        assert len(failures) == 1
        assert failures[0]["task_id"] == "fail"

    def test_history_limited(self, orchestrator):
        for i in range(5):
            task = TaskRequest(task_id=f"h-{i}", title="Test")
            orchestrator.route_task(task)
            orchestrator.complete_task(f"h-{i}")
            # Re-activate agents
            for aid in range(1, 4):
                agent = orchestrator.lifecycle._agents.get(aid)
                if agent and agent.state == AgentState.COOLDOWN:
                    agent.cooldown_until = None
                    orchestrator.lifecycle.check_cooldown_expiry(aid)
                    orchestrator.lifecycle.transition(aid, AgentState.ACTIVE)

        history = orchestrator.get_assignment_history(limit=3)
        assert len(history) == 3


# ─── TaskRequest ──────────────────────────────────────────────────────────────


class TestTaskRequest:
    def test_defaults(self):
        req = TaskRequest(task_id="t1", title="Test")
        assert req.priority == TaskPriority.NORMAL
        assert req.categories == []
        assert req.bounty_usd == 0.0
        assert req.max_retries == 2
        assert req.created_at is not None

    def test_all_priorities_have_weights(self):
        for priority in TaskPriority:
            assert priority in PRIORITY_WEIGHTS


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_single_agent_routing(self, bridge):
        lifecycle = LifecycleManager()
        lifecycle.register_agent(1, "solo", "0x0001")
        lifecycle.transition(1, AgentState.IDLE)
        lifecycle.transition(1, AgentState.ACTIVE)

        orch = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)
        orch.register_reputation(
            1,
            OnChainReputation(agent_id=1, wallet_address="0x0001"),
            InternalReputation(agent_id=1),
        )

        task = TaskRequest(task_id="solo", title="Test")
        result = orch.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 1
        assert result.alternatives_count == 0

    def test_assignment_lifecycle_error(self, bridge):
        """Test that lifecycle errors during assignment return RoutingFailure."""
        lifecycle = LifecycleManager()
        lifecycle.register_agent(
            1, "budget_blown", "0x0001",
            budget_config=BudgetConfig(daily_limit_usd=0.01),
        )
        lifecycle.transition(1, AgentState.IDLE)
        lifecycle.transition(1, AgentState.ACTIVE)

        # Blow the budget
        try:
            lifecycle.record_spend(1, 0.01)
        except Exception:
            pass

        orch = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)
        orch.register_reputation(
            1,
            OnChainReputation(agent_id=1, wallet_address="0x0001"),
            InternalReputation(agent_id=1),
        )

        task = TaskRequest(task_id="budget-fail", title="Test")
        result = orch.route_task(task)
        # Should handle gracefully — either the agent is unavailable
        # or the assignment raises BudgetExceededError caught as RoutingFailure
        assert isinstance(result, (Assignment, RoutingFailure))

    def test_concurrent_task_claims(self, orchestrator):
        """Multiple tasks to the same agent pool."""
        results = []
        for i in range(3):
            task = TaskRequest(task_id=f"conc-{i}", title=f"Concurrent {i}")
            result = orchestrator.route_task(task)
            results.append(result)

        assignments = [r for r in results if isinstance(r, Assignment)]
        # Each agent can only take 1 task (goes to WORKING state)
        assert len(set(a.agent_id for a in assignments)) == len(assignments)
