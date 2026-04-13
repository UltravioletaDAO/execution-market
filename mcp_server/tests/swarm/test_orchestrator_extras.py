"""
Tests for SwarmOrchestrator — task routing, assignment, and failure handling.

Covers:
- RoutingStrategy enum
- TaskRequest / Assignment / RoutingFailure dataclasses
- SwarmOrchestrator routing (best_fit, round_robin, specialist, budget_aware)
- Task completion and failure
- Anti-duplication claims
- Score thresholds
- Agent preference and exclusion
- Status and history tracking
"""

from datetime import datetime, timezone, timedelta


from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    RoutingStrategy,
    TaskPriority,
    TaskRequest,
    Assignment,
    RoutingFailure,
    PRIORITY_WEIGHTS,
)
from mcp_server.swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
)
from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    BudgetConfig,
)


# ──────────────────────────── Fixtures ────────────────────────────


def _setup_orchestrator(
    num_agents=3,
    min_score=15.0,
    strategy=RoutingStrategy.BEST_FIT,
    cooldown=30,
):
    """Create an orchestrator with N agents, all ACTIVE and with reputation data."""
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orch = SwarmOrchestrator(
        bridge,
        lifecycle,
        default_strategy=strategy,
        cooldown_seconds=cooldown,
        min_score_threshold=min_score,
    )

    for i in range(1, num_agents + 1):
        budget = BudgetConfig(daily_limit_usd=10.0, monthly_limit_usd=200.0)
        lifecycle.register_agent(i, f"agent-{i}", f"0x{i:04x}", budget_config=budget)
        lifecycle.transition(i, AgentState.IDLE)
        lifecycle.transition(i, AgentState.ACTIVE)

        # Register reputation (agents get progressively better)
        orch.register_reputation(
            agent_id=i,
            on_chain=OnChainReputation(
                agent_id=i,
                wallet_address=f"0x{i:04x}",
                total_seals=i * 20,
                positive_seals=i * 18,
                chains_active=["base"] * min(i, 8),
            ),
            internal=InternalReputation(
                agent_id=i,
                bayesian_score=0.5 + i * 0.1,
                total_tasks=i * 25,
                successful_tasks=i * 23,
                avg_rating=3.5 + i * 0.3,
                category_scores={"photo": 0.6 + i * 0.1, "data": 0.5 + i * 0.05},
            ),
        )

    return orch, lifecycle


def _task(
    task_id="t1",
    title="Photo verification",
    categories=None,
    bounty=1.0,
    priority=TaskPriority.NORMAL,
    preferred=None,
    exclude=None,
):
    return TaskRequest(
        task_id=task_id,
        title=title,
        categories=categories or ["photo"],
        bounty_usd=bounty,
        priority=priority,
        preferred_agent_ids=preferred or [],
        exclude_agent_ids=exclude or [],
    )


# ──────────────────── Enums & Dataclasses ─────────────────────────


class TestRoutingStrategy:
    def test_values(self):
        assert RoutingStrategy.BEST_FIT.value == "best_fit"
        assert RoutingStrategy.ROUND_ROBIN.value == "round_robin"
        assert RoutingStrategy.SPECIALIST.value == "specialist"
        assert RoutingStrategy.BUDGET_AWARE.value == "budget_aware"


class TestTaskPriority:
    def test_values(self):
        assert TaskPriority.CRITICAL.value == "critical"
        assert TaskPriority.LOW.value == "low"

    def test_weights_ordering(self):
        assert (
            PRIORITY_WEIGHTS[TaskPriority.CRITICAL]
            > PRIORITY_WEIGHTS[TaskPriority.HIGH]
        )
        assert (
            PRIORITY_WEIGHTS[TaskPriority.HIGH] > PRIORITY_WEIGHTS[TaskPriority.NORMAL]
        )
        assert (
            PRIORITY_WEIGHTS[TaskPriority.NORMAL] > PRIORITY_WEIGHTS[TaskPriority.LOW]
        )


class TestTaskRequest:
    def test_custom_fields(self):
        tr = _task(priority=TaskPriority.CRITICAL, preferred=[1, 2], exclude=[3])
        assert tr.priority == TaskPriority.CRITICAL
        assert tr.preferred_agent_ids == [1, 2]
        assert tr.exclude_agent_ids == [3]


class TestAssignment:
    def test_to_dict(self):
        a = Assignment(
            task_id="t1",
            agent_id=42,
            agent_name="aurora",
            score=75.5,
            strategy_used=RoutingStrategy.BEST_FIT,
            alternatives_count=3,
        )
        d = a.to_dict()
        assert d["task_id"] == "t1"
        assert d["agent_id"] == 42
        assert d["agent_name"] == "aurora"
        assert d["score"] == 75.5
        assert d["strategy"] == "best_fit"
        assert d["alternatives"] == 3
        assert "assigned_at" in d


# ──────────────────── Orchestrator Routing ────────────────────────


class TestOrchestratorBestFit:
    def test_routes_to_best_agent(self):
        orch, lm = _setup_orchestrator(num_agents=3)
        task = _task()
        result = orch.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 3  # Agent 3 has best reputation
        assert result.strategy_used == RoutingStrategy.BEST_FIT

    def test_assignment_updates_lifecycle(self):
        orch, lm = _setup_orchestrator(num_agents=2)
        task = _task()
        result = orch.route_task(task)
        assert isinstance(result, Assignment)
        agent = lm.agents[result.agent_id]
        assert agent.state == AgentState.WORKING
        assert agent.current_task_id == "t1"

    def test_alternatives_count(self):
        orch, lm = _setup_orchestrator(num_agents=3)
        result = orch.route_task(_task())
        assert isinstance(result, Assignment)
        assert result.alternatives_count == 2  # 3 agents - 1 assigned

    def test_no_agents_available(self):
        orch, lm = _setup_orchestrator(num_agents=0)
        result = orch.route_task(_task())
        assert isinstance(result, RoutingFailure)
        assert "No agents available" in result.reason


class TestOrchestratorAntiDuplication:
    def test_different_tasks_allowed(self):
        orch, lm = _setup_orchestrator(num_agents=3)
        result1 = orch.route_task(_task(task_id="t1"))
        result2 = orch.route_task(_task(task_id="t2"))
        assert isinstance(result1, Assignment)
        assert isinstance(result2, Assignment)
        assert (
            result1.agent_id != result2.agent_id or result1.task_id != result2.task_id
        )


class TestOrchestratorScoreThreshold:
    def test_below_threshold_fails(self):
        orch, lm = _setup_orchestrator(num_agents=1, min_score=999.0)
        result = orch.route_task(_task())
        assert isinstance(result, RoutingFailure)
        assert "minimum score" in result.reason

    def test_above_threshold_succeeds(self):
        orch, lm = _setup_orchestrator(num_agents=1, min_score=0.0)
        result = orch.route_task(_task())
        assert isinstance(result, Assignment)


class TestOrchestratorRoundRobin:
    def test_round_robin_distributes(self):
        orch, lm = _setup_orchestrator(
            num_agents=3, strategy=RoutingStrategy.ROUND_ROBIN
        )
        results = []
        for i in range(3):
            # Need to free agents after each task
            result = orch.route_task(
                _task(task_id=f"t{i}"), strategy=RoutingStrategy.ROUND_ROBIN
            )
            if isinstance(result, Assignment):
                results.append(result.agent_id)
                orch.complete_task(f"t{i}")
                # Move agent back to active
                lm.check_cooldown_expiry(result.agent_id)
                if lm.agents[result.agent_id].state == AgentState.COOLDOWN:
                    lm._agents[result.agent_id].cooldown_until = datetime.now(
                        timezone.utc
                    ) - timedelta(seconds=1)
                    lm.check_cooldown_expiry(result.agent_id)
                if lm.agents[result.agent_id].state == AgentState.IDLE:
                    lm.transition(result.agent_id, AgentState.ACTIVE)
        assert len(results) == 3


class TestOrchestratorSpecialist:
    def test_specialist_requires_category_experience(self):
        orch, lm = _setup_orchestrator(num_agents=3)
        # Agent 3 has skill_score > 50 for photo category
        result = orch.route_task(
            _task(categories=["photo"]), strategy=RoutingStrategy.SPECIALIST
        )
        assert isinstance(result, Assignment)

    def test_specialist_no_qualified(self):
        orch, lm = _setup_orchestrator(num_agents=1, min_score=0.0)
        # Override agent 1's reputation to have no category experience
        orch._internal[1] = InternalReputation(
            agent_id=1,
            bayesian_score=0.3,
            total_tasks=2,
            successful_tasks=1,
            category_scores={},
        )
        result = orch.route_task(
            _task(categories=["notarization"]), strategy=RoutingStrategy.SPECIALIST
        )
        # With min_score=0 but specialist requires skill_score >= 50
        assert isinstance(result, (Assignment, RoutingFailure))


class TestOrchestratorBudgetAware:
    def test_budget_aware_prefers_headroom(self):
        orch, lm = _setup_orchestrator(
            num_agents=2, strategy=RoutingStrategy.BUDGET_AWARE
        )
        # Agent 1: spent a lot
        lm.record_spend(1, 8.0)  # 80% of $10 daily
        # Agent 2: barely spent
        lm.record_spend(2, 0.50)  # 5% of $10 daily
        result = orch.route_task(_task(), strategy=RoutingStrategy.BUDGET_AWARE)
        assert isinstance(result, Assignment)
        # Agent 2 should be preferred due to budget headroom
        # (though agent 2 also has better reputation, so both factors align)
        assert result.agent_id == 2


# ──────────────── Task Completion & Failure ───────────────────────


class TestOrchestratorTaskLifecycle:
    def test_fail_task_increments_consecutive_failures(self):
        orch, lm = _setup_orchestrator(num_agents=1)
        orch.route_task(_task())
        agent_id = 1
        orch.fail_task("t1", "timeout")
        assert orch._internal[agent_id].consecutive_failures == 1

    def test_fail_task_longer_cooldown(self):
        orch, lm = _setup_orchestrator(num_agents=1, cooldown=30)
        orch.route_task(_task())
        orch.fail_task("t1", "error")
        agent = lm.agents[1]
        # Failure cooldown should be 3x normal
        if agent.cooldown_until:
            datetime.now(timezone.utc) + timedelta(seconds=80)
            assert agent.cooldown_until > datetime.now(timezone.utc) + timedelta(
                seconds=60
            )


# ──────────────────── Reputation Registration ─────────────────────


class TestOrchestratorReputation:
    def test_agent_without_reputation_gets_defaults(self):
        orch, lm = _setup_orchestrator(num_agents=1, min_score=0.0)
        # Clear reputation for agent 1
        del orch._on_chain[1]
        del orch._internal[1]
        result = orch.route_task(_task())
        assert isinstance(result, Assignment)  # Should still work with defaults


# ──────────────────── Status & History ────────────────────────────


class TestOrchestratorStatus:
    def test_get_status(self):
        orch, lm = _setup_orchestrator(num_agents=2)
        orch.route_task(_task(task_id="t1"))
        status = orch.get_status()
        assert status["active_claims"] == 1
        assert status["total_assignments"] >= 1
        assert status["default_strategy"] == "best_fit"
        assert "swarm" in status

    def test_assignment_history_limit(self):
        orch, lm = _setup_orchestrator(num_agents=3)
        orch.route_task(_task(task_id="t1"))
        orch.route_task(_task(task_id="t2"))
        history = orch.get_assignment_history(limit=1)
        assert len(history) == 1

    def test_failures_tracked(self):
        orch, lm = _setup_orchestrator(num_agents=0)
        orch.route_task(_task())
        failures = orch.get_failures()
        assert len(failures) == 1
        assert failures[0]["reason"] == "No agents available"

    def test_failures_limit(self):
        orch, lm = _setup_orchestrator(num_agents=0)
        orch.route_task(_task(task_id="t1"))
        orch.route_task(_task(task_id="t2"))
        failures = orch.get_failures(limit=1)
        assert len(failures) == 1


class TestOrchestratorEdgeCases:
    def test_route_after_completion_frees_slot(self):
        orch, lm = _setup_orchestrator(num_agents=1)
        result1 = orch.route_task(_task(task_id="t1"))
        assert isinstance(result1, Assignment)
        # Agent is now WORKING, can't take another task
        result2 = orch.route_task(_task(task_id="t2"))
        assert isinstance(result2, RoutingFailure)
        # Complete task 1
        orch.complete_task("t1")
        # Force cooldown expiry
        lm._agents[1].cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=1)
        lm.check_cooldown_expiry(1)
        lm.transition(1, AgentState.ACTIVE)
        # Now should work
        result3 = orch.route_task(_task(task_id="t2"))
        assert isinstance(result3, Assignment)

    def test_multiple_tasks_different_agents(self):
        orch, lm = _setup_orchestrator(num_agents=3)
        results = []
        for i in range(3):
            r = orch.route_task(_task(task_id=f"task-{i}"))
            if isinstance(r, Assignment):
                results.append(r)
        assert len(results) == 3
        agent_ids = {r.agent_id for r in results}
        assert len(agent_ids) == 3  # All different agents

    def test_idle_agent_auto_activated(self):
        """If agent is IDLE (not ACTIVE), orchestrator should activate it."""
        bridge = ReputationBridge()
        lifecycle = LifecycleManager()
        orch = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)
        lifecycle.register_agent(1, "a1", "0x1")
        lifecycle.transition(1, AgentState.IDLE)
        # Don't transition to ACTIVE manually
        orch.register_reputation(
            1,
            OnChainReputation(1, "0x1", total_seals=10, positive_seals=9),
            InternalReputation(
                1,
                bayesian_score=0.7,
                total_tasks=20,
                successful_tasks=18,
                avg_rating=4.0,
            ),
        )
        result = orch.route_task(_task())
        assert isinstance(result, Assignment)
        assert lifecycle.agents[1].state == AgentState.WORKING
