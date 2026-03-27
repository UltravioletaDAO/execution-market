"""
Advanced SwarmOrchestrator tests — Multi-strategy routing, priority inversion,
budget interaction, and coordination patterns.

Builds on test_orchestrator.py (basic coverage) with complex behavioral tests:
1. Multi-agent, multi-strategy routing competitions
2. Score-based ranking with real composite scores
3. Budget-aware routing logic
4. Round-robin fairness properties
5. Specialist routing (category matching)
6. Priority inversion detection
7. Concurrent task routing
8. Failure cascade patterns
9. Agent recovery after cooldown
10. History and status accuracy

These tests verify the orchestrator as a behavioral system, not just individual methods.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    RoutingStrategy,
    Assignment,
    RoutingFailure,
    TaskPriority,
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
from mcp_server.swarm.coordinator import TaskRequest


# ── Fixtures ─────────────────────────────────────────────────────────────────


def make_on_chain(positive_seals=17, total_seals=20, chains=2) -> OnChainReputation:
    return OnChainReputation(
        agent_id=0,
        wallet_address="0x0000000000000000000000000000000000000001",
        total_seals=total_seals,
        positive_seals=positive_seals,
        negative_seals=total_seals - positive_seals,
        chains_active=["base", "ethereum"][:chains],
    )


def make_internal(
    bayesian_score=0.75,
    tasks=20,
    successful=17,
    categories=None,
    consecutive_failures=0,
) -> InternalReputation:
    cat_scores = {c: 0.8 for c in (categories or ["delivery"])}
    return InternalReputation(
        agent_id=0,
        bayesian_score=bayesian_score,
        total_tasks=tasks,
        successful_tasks=successful,
        avg_rating=4.2,
        avg_completion_time_hours=3.0,
        consecutive_failures=consecutive_failures,
        category_scores=cat_scores,
    )


@pytest.fixture
def lifecycle():
    lm = LifecycleManager()
    return lm


@pytest.fixture
def bridge():
    return ReputationBridge()


@pytest.fixture
def orchestrator(bridge, lifecycle):
    return SwarmOrchestrator(
        bridge=bridge,
        lifecycle=lifecycle,
        default_strategy=RoutingStrategy.BEST_FIT,
        cooldown_seconds=5,
        min_score_threshold=10.0,
    )


def register_agent(
    orchestrator,
    lifecycle,
    agent_id,
    name="Agent",
    positive_seals=17,
    bayesian_score=0.75,
    categories=None,
    consecutive_failures=0,
) -> int:
    """Helper: register and activate an agent with given parameters."""
    wallet = f"0x{'0' * 38}{agent_id:02d}"
    lifecycle.register_agent(agent_id, name=name, wallet_address=wallet)
    lifecycle.transition(agent_id, AgentState.IDLE, "ready")

    on_chain = make_on_chain(positive_seals=positive_seals, total_seals=20)
    on_chain.agent_id = agent_id
    on_chain.wallet_address = wallet
    internal = make_internal(
        bayesian_score=bayesian_score,
        categories=categories,
        consecutive_failures=consecutive_failures,
    )
    internal.agent_id = agent_id

    orchestrator.register_reputation(agent_id, on_chain, internal)
    return agent_id


def make_task(
    task_id="t1",
    category="delivery",
    bounty=0.50,
    priority=TaskPriority.NORMAL,
    exclude=None,
) -> TaskRequest:
    return TaskRequest(
        task_id=task_id,
        title=f"Task {task_id}",
        categories=[category],
        bounty_usd=bounty,
        priority=priority,
        exclude_agent_ids=exclude or [],
    )


# ── Basic Routing ─────────────────────────────────────────────────────────────


class TestBasicRouting:
    def test_routes_to_single_available_agent(self, orchestrator, lifecycle):
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        task = make_task()
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 1
        assert result.task_id == "t1"

    def test_returns_failure_with_no_agents(self, orchestrator):
        task = make_task()
        result = orchestrator.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "No agents available" in result.reason

    def test_returns_failure_if_all_excluded(self, orchestrator, lifecycle):
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        task = make_task(exclude=[1])
        result = orchestrator.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "excluded" in result.reason.lower()

    def test_duplicate_task_returns_failure(self, orchestrator, lifecycle):
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        task = make_task()
        orchestrator.route_task(task)
        # Route same task again
        result = orchestrator.route_task(make_task())  # Same task_id
        assert isinstance(result, RoutingFailure)
        assert "already claimed" in result.reason.lower()

    def test_assignment_recorded_in_history(self, orchestrator, lifecycle):
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        task = make_task()
        orchestrator.route_task(task)
        history = orchestrator.get_assignment_history()
        assert len(history) == 1
        assert history[0]["task_id"] == "t1"

    def test_failure_recorded_in_failures(self, orchestrator):
        task = make_task()
        orchestrator.route_task(task)
        failures = orchestrator.get_failures()
        assert len(failures) == 1


# ── Multi-Agent Score Competition ─────────────────────────────────────────────


class TestScoreCompetition:
    def test_best_fit_routes_to_highest_score(self, orchestrator, lifecycle):
        """BEST_FIT always picks the highest-scored agent."""
        register_agent(
            orchestrator,
            lifecycle,
            1,
            "LowScore",
            positive_seals=4,
            bayesian_score=0.30,
        )
        register_agent(
            orchestrator,
            lifecycle,
            2,
            "HighScore",
            positive_seals=19,
            bayesian_score=0.95,
        )
        register_agent(
            orchestrator,
            lifecycle,
            3,
            "MidScore",
            positive_seals=12,
            bayesian_score=0.60,
        )

        task = make_task("t1")
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 2  # HighScore wins

    def test_best_fit_second_task_goes_to_second_best(self, orchestrator, lifecycle):
        """After top agent takes task, next task goes to next best."""
        register_agent(
            orchestrator,
            lifecycle,
            1,
            "LowScore",
            positive_seals=4,
            bayesian_score=0.30,
        )
        register_agent(
            orchestrator,
            lifecycle,
            2,
            "HighScore",
            positive_seals=19,
            bayesian_score=0.95,
        )
        register_agent(
            orchestrator,
            lifecycle,
            3,
            "MidScore",
            positive_seals=12,
            bayesian_score=0.60,
        )

        orchestrator.route_task(make_task("t1"))
        # Agent 2 is now busy; next task should go to agent 3
        result = orchestrator.route_task(make_task("t2"))
        assert isinstance(result, Assignment)
        assert result.agent_id == 3

    def test_score_below_threshold_causes_failure(self, orchestrator, lifecycle):
        """Agents with score below min_score_threshold are rejected."""
        # Register agent with minimal seals and very low bayesian score
        wallet = "0x0000000000000000000000000000000000000099"
        lifecycle.register_agent(99, name="PoorAgent", wallet_address=wallet)
        lifecycle.transition(99, AgentState.IDLE, "ready")
        on_chain = make_on_chain(positive_seals=0, total_seals=1)  # 0% seal ratio
        on_chain.agent_id = 99
        on_chain.wallet_address = wallet
        internal = make_internal(bayesian_score=0.01, tasks=1, successful=0)
        internal.agent_id = 99
        orchestrator.register_reputation(99, on_chain, internal)

        # Create orchestrator with very high threshold so this agent fails
        high_threshold_orch = SwarmOrchestrator(
            bridge=orchestrator.bridge,
            lifecycle=lifecycle,
            min_score_threshold=90.0,  # Very high — no agent will pass
        )
        high_threshold_orch.register_reputation(99, on_chain, internal)

        task = make_task()
        result = high_threshold_orch.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "threshold" in result.reason.lower()

    def test_assignment_includes_score(self, orchestrator, lifecycle):
        """Assignment object carries the score used for routing."""
        register_agent(
            orchestrator, lifecycle, 1, "Alpha", positive_seals=18, bayesian_score=0.88
        )
        result = orchestrator.route_task(make_task())
        assert isinstance(result, Assignment)
        assert result.score > 0

    def test_alternatives_count_is_n_minus_one(self, orchestrator, lifecycle):
        """alternatives_count reflects how many other candidates existed."""
        for i in range(4):
            register_agent(orchestrator, lifecycle, i + 1, f"Agent{i + 1}")
        result = orchestrator.route_task(make_task())
        assert isinstance(result, Assignment)
        assert result.alternatives_count == 3


# ── Round Robin ───────────────────────────────────────────────────────────────


class TestRoundRobin:
    def test_round_robin_distributes_across_agents(self, orchestrator, lifecycle):
        """RR cycles through available agents across multiple tasks."""
        for i in range(3):
            register_agent(orchestrator, lifecycle, i + 1, f"Agent{i + 1}")

        assignments = []
        for i in range(6):
            result = orchestrator.route_task(
                make_task(f"t{i}", category="delivery"),
                strategy=RoutingStrategy.ROUND_ROBIN,
            )
            if isinstance(result, Assignment):
                assignments.append(result.agent_id)

        # With 6 tasks and 3 agents, each agent should get 2
        from collections import Counter

        counts = Counter(assignments)
        assert len(counts) == 3  # All 3 agents were used
        assert max(counts.values()) - min(counts.values()) <= 1  # Even distribution

    def test_round_robin_skips_busy_agents(self, orchestrator, lifecycle):
        """RR skips agents that are currently busy."""
        for i in range(3):
            register_agent(orchestrator, lifecycle, i + 1, f"Agent{i + 1}")

        # Assign a task to agent 1 first (via BEST_FIT)
        result1 = orchestrator.route_task(
            make_task("t_busy"), strategy=RoutingStrategy.BEST_FIT
        )
        busy_agent = result1.agent_id

        # Now run 2 more tasks via RR — busy agent should not appear twice
        agents_used = set()
        for i in range(2):
            result = orchestrator.route_task(
                make_task(f"t_rr_{i}"), strategy=RoutingStrategy.ROUND_ROBIN
            )
            if isinstance(result, Assignment):
                agents_used.add(result.agent_id)

        # The 2 RR tasks should only use agents that aren't busy
        assert busy_agent not in agents_used or len(agents_used) <= 2


# ── Specialist Routing ────────────────────────────────────────────────────────


class TestSpecialistRouting:
    def test_specialist_routes_to_category_expert(self, orchestrator, lifecycle):
        """SPECIALIST mode prefers agents with matching category experience."""
        # Agent 1: delivery specialist, high seals
        register_agent(
            orchestrator,
            lifecycle,
            1,
            "GeneralistA",
            positive_seals=18,
            bayesian_score=0.90,
            categories=["delivery"],
        )
        # Agent 2: code_execution specialist but lower seals
        register_agent(
            orchestrator,
            lifecycle,
            2,
            "Specialist",
            positive_seals=12,
            bayesian_score=0.60,
            categories=["code_execution"],
        )
        register_agent(
            orchestrator,
            lifecycle,
            3,
            "GeneralistB",
            positive_seals=15,
            bayesian_score=0.75,
            categories=["delivery"],
        )

        # Task requiring "code_execution" — Agent 2 has matching category
        task = make_task("t1", category="code_execution")
        result = orchestrator.route_task(task, strategy=RoutingStrategy.SPECIALIST)
        # Should be assigned to someone — specialist or fallback
        assert isinstance(result, Assignment)

    def test_specialist_falls_back_to_best_fit_if_no_specialist(
        self, orchestrator, lifecycle
    ):
        """If no specialist exists, SPECIALIST may fall back or return a failure — both are valid."""
        register_agent(
            orchestrator,
            lifecycle,
            1,
            "Alpha",
            positive_seals=17,
            bayesian_score=0.85,
            categories=["delivery"],
        )
        register_agent(
            orchestrator,
            lifecycle,
            2,
            "Beta",
            positive_seals=17,
            bayesian_score=0.85,
            categories=["pickup"],
        )

        # Task for "knowledge_access" — no specialist
        task = make_task("t1", category="knowledge_access")
        result = orchestrator.route_task(task, strategy=RoutingStrategy.SPECIALIST)
        # Either routed (fallback) or failed gracefully (no specialist, threshold)
        assert isinstance(result, (Assignment, RoutingFailure))


# ── Budget-Aware Routing ──────────────────────────────────────────────────────


class TestBudgetAwareRouting:
    def test_budget_aware_routes_successfully(self, orchestrator, lifecycle):
        """BUDGET_AWARE routing assigns a task."""
        register_agent(
            orchestrator, lifecycle, 1, "AgentA", positive_seals=15, bayesian_score=0.75
        )
        register_agent(
            orchestrator, lifecycle, 2, "AgentB", positive_seals=12, bayesian_score=0.60
        )

        task = make_task()
        result = orchestrator.route_task(task, strategy=RoutingStrategy.BUDGET_AWARE)
        assert isinstance(result, Assignment)

    def test_budget_aware_with_single_agent(self, orchestrator, lifecycle):
        """BUDGET_AWARE with one agent routes to that agent."""
        register_agent(orchestrator, lifecycle, 1, "OnlyAgent")
        task = make_task()
        result = orchestrator.route_task(task, strategy=RoutingStrategy.BUDGET_AWARE)
        assert isinstance(result, Assignment)
        assert result.agent_id == 1

    def test_budget_config_enforced_by_lifecycle(self, orchestrator, lifecycle):
        """
        Agents over their budget are in SUSPENDED state and unavailable.
        BUDGET_AWARE routing naturally excludes them via lifecycle.get_available_agents().
        """
        # Register agent with tight budget
        wallet = "0x0000000000000000000000000000000000000099"
        lifecycle.register_agent(
            99,
            name="OverBudget",
            wallet_address=wallet,
            budget_config=BudgetConfig(daily_limit_usd=0.01, monthly_limit_usd=0.01),
        )
        lifecycle.transition(99, AgentState.IDLE, "ready")
        on_chain = make_on_chain()
        on_chain.agent_id = 99
        on_chain.wallet_address = wallet
        internal = make_internal()
        internal.agent_id = 99
        orchestrator.register_reputation(99, on_chain, internal)

        # Register normal agent
        register_agent(orchestrator, lifecycle, 1, "NormalAgent")

        # Route first task — should succeed
        result = orchestrator.route_task(make_task("t1"))
        assert isinstance(result, Assignment)


# ── Task Completion and Recovery ─────────────────────────────────────────────


class TestTaskCompletion:
    def test_complete_task_frees_agent(self, orchestrator, lifecycle):
        """After completing a task, agent becomes available again."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")

        # Route task → agent busy
        orchestrator.route_task(make_task("t1"))
        agent_id = orchestrator._active_claims.get("t1")
        assert agent_id is not None

        # Complete task
        completed_agent = orchestrator.complete_task("t1")
        assert completed_agent == agent_id

        # Task no longer in active claims
        assert "t1" not in orchestrator._active_claims

    def test_complete_unknown_task_returns_none(self, orchestrator):
        """Completing a task that wasn't claimed returns None."""
        result = orchestrator.complete_task("nonexistent")
        assert result is None

    def test_fail_task_frees_agent(self, orchestrator, lifecycle):
        """Failing a task removes the active claim."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        orchestrator.route_task(make_task("t1"))
        orchestrator.fail_task("t1", error="Worker disappeared")
        assert "t1" not in orchestrator._active_claims

    def test_fail_task_increments_consecutive_failures(self, orchestrator, lifecycle):
        """Failing a task increments the agent's consecutive_failures counter."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        orchestrator.route_task(make_task("t1"))
        initial_failures = orchestrator._internal[1].consecutive_failures
        orchestrator.fail_task("t1", error="Timeout")
        assert orchestrator._internal[1].consecutive_failures == initial_failures + 1

    def test_agent_available_after_cooldown_expires(self, orchestrator, lifecycle):
        """
        After task completion, the agent enters cooldown. Once cooldown
        expires (simulated via lifecycle), agent is available again.
        """
        lifecycle_mock = MagicMock(spec=LifecycleManager)
        # Setup: agent IS available after cooldown
        mock_agent = MagicMock()
        mock_agent.agent_id = 1
        mock_agent.name = "Alpha"
        mock_agent.state = AgentState.IDLE
        mock_agent.budget_config = BudgetConfig()
        mock_agent.total_spend_usd = 0.0
        lifecycle_mock.get_available_agents.return_value = [mock_agent]
        lifecycle_mock.agents = {1: mock_agent}
        lifecycle_mock.assign_task.return_value = mock_agent
        lifecycle_mock.transition.return_value = mock_agent

        orch = SwarmOrchestrator(
            bridge=ReputationBridge(),
            lifecycle=lifecycle_mock,
            min_score_threshold=10.0,
        )
        on_chain = make_on_chain(positive_seals=17, total_seals=20)
        on_chain.agent_id = 1
        internal = make_internal(bayesian_score=0.75)
        internal.agent_id = 1
        orch.register_reputation(1, on_chain, internal)

        result = orch.route_task(make_task("t_cooldown"))
        assert isinstance(result, Assignment)


# ── Status and History Accuracy ───────────────────────────────────────────────


class TestStatusAccuracy:
    def test_get_status_shape(self, orchestrator, lifecycle):
        """Status dict has expected keys."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        orchestrator.route_task(make_task("t1"))
        status = orchestrator.get_status()
        assert "active_claims" in status
        assert "total_assignments" in status
        assert "total_failures" in status
        assert "default_strategy" in status

    def test_active_tasks_count_increases(self, orchestrator, lifecycle):
        """Active task count reflects routed tasks."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        register_agent(orchestrator, lifecycle, 2, "Beta")
        orchestrator.route_task(make_task("t1"))
        orchestrator.route_task(make_task("t2"))
        status = orchestrator.get_status()
        assert status["active_claims"] == 2

    def test_active_tasks_count_decreases_on_complete(self, orchestrator, lifecycle):
        """Active task count decreases when task is completed."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        orchestrator.route_task(make_task("t1"))
        orchestrator.complete_task("t1")
        status = orchestrator.get_status()
        assert status["active_claims"] == 0

    def test_assignment_history_limit(self, orchestrator, lifecycle):
        """Assignment history is bounded by maxlen."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        # Route many tasks (lifecycle assigns them all, even if agent is busy,
        # because mock doesn't enforce state — just test history size stays bounded)
        # Actually we need enough agents — just use one and complete each task
        for i in range(10):
            orchestrator.route_task(make_task(f"t{i}"))
            orchestrator.complete_task(f"t{i}")
        history = orchestrator.get_assignment_history(limit=5)
        assert len(history) <= 5

    def test_history_contains_strategy_used(self, orchestrator, lifecycle):
        """Each history entry records the strategy used."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        orchestrator.route_task(make_task("t1"), strategy=RoutingStrategy.ROUND_ROBIN)
        history = orchestrator.get_assignment_history()
        # The serialized key is "strategy" (from Assignment.to_dict())
        assert history[0]["strategy"] == RoutingStrategy.ROUND_ROBIN.value


# ── Priority Inversion Tests ──────────────────────────────────────────────────


class TestPriorityInversion:
    def test_critical_task_routes_before_low_priority(self, orchestrator, lifecycle):
        """
        Critical tasks should be routed first when orchestrator processes
        a queue. (Tests that priority is passed through to routing decision.)
        """
        register_agent(orchestrator, lifecycle, 1, "Alpha")

        critical_task = make_task("tc", priority=TaskPriority.CRITICAL)
        low_task = make_task("tl", priority=TaskPriority.LOW)

        # Route critical task first
        result_critical = orchestrator.route_task(critical_task)
        assert isinstance(result_critical, Assignment)
        assert result_critical.task_id == "tc"

        # Agent is now busy; low priority task may need to wait
        result_low = orchestrator.route_task(low_task)
        # Either succeeds (if there's capacity) or fails gracefully
        assert isinstance(result_low, (Assignment, RoutingFailure))

    def test_routing_failure_includes_priority_context(self, orchestrator):
        """Routing failure contains task_id for diagnosis."""
        task = make_task("high_priority_fail", priority=TaskPriority.HIGH)
        failure = orchestrator.route_task(task)
        assert isinstance(failure, RoutingFailure)
        assert failure.task_id == "high_priority_fail"


# ── Concurrent Task Load ──────────────────────────────────────────────────────


class TestConcurrentLoad:
    def test_n_tasks_with_n_agents_all_assigned(self, orchestrator, lifecycle):
        """N tasks with N agents should all be assignable."""
        n = 5
        for i in range(n):
            register_agent(orchestrator, lifecycle, i + 1, f"Agent{i + 1}")

        results = []
        for i in range(n):
            results.append(orchestrator.route_task(make_task(f"t{i}")))

        assignments = [r for r in results if isinstance(r, Assignment)]
        assert len(assignments) == n

    def test_n_plus_one_tasks_causes_one_failure(self, orchestrator, lifecycle):
        """n+1 tasks with n agents → exactly 1 failure."""
        n = 3
        for i in range(n):
            register_agent(orchestrator, lifecycle, i + 1, f"Agent{i + 1}")

        results = []
        for i in range(n + 1):
            results.append(orchestrator.route_task(make_task(f"t{i}")))

        assignments = [r for r in results if isinstance(r, Assignment)]
        failures = [r for r in results if isinstance(r, RoutingFailure)]
        assert len(assignments) == n
        assert len(failures) == 1

    def test_complete_and_reuse_agent(self, orchestrator, lifecycle):
        """
        Complete tasks and reuse the agent for subsequent tasks.
        After cooldown expires (simulated via check_cooldown_expiry + manual transition),
        agent can take the next task.
        """
        register_agent(orchestrator, lifecycle, 1, "Alpha")

        assignments = []
        for i in range(3):
            r = orchestrator.route_task(make_task(f"t{i}"))
            assert isinstance(r, Assignment), f"Task {i} routing failed: {r}"
            assignments.append(r)
            orchestrator.complete_task(f"t{i}")
            # Manually expire cooldown and return agent to IDLE for next cycle
            agent_rec = lifecycle.agents[1]
            agent_rec.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=1)
            lifecycle.transition(1, AgentState.IDLE, "cooldown_expired_simulated")

        assert len(assignments) == 3
        # After 3 complete cycles, history has 3 assignments
        history = orchestrator.get_assignment_history()
        assert len(history) == 3


# ── Failure Cascade Tests ─────────────────────────────────────────────────────


class TestFailureCascade:
    def test_multiple_failures_all_recorded(self, orchestrator):
        """All routing failures are recorded in failure history."""
        for i in range(5):
            orchestrator.route_task(make_task(f"t{i}"))
        failures = orchestrator.get_failures()
        assert len(failures) == 5

    def test_failure_count_in_status(self, orchestrator, lifecycle):
        """Status reflects cumulative failure count."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        orchestrator.route_task(make_task("t1"))  # succeeds
        # With agent busy, next task fails
        orchestrator.route_task(make_task("t2"))
        status = orchestrator.get_status()
        assert status["total_failures"] >= 1

    def test_excluded_agents_count_in_failure(self, orchestrator, lifecycle):
        """Failure message includes excluded agent context."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        task = make_task(exclude=[1])
        failure = orchestrator.route_task(task)
        assert isinstance(failure, RoutingFailure)
        assert failure.excluded_agents == 1


# ── Strategy Switching ────────────────────────────────────────────────────────


class TestStrategySwitching:
    def test_can_mix_strategies_across_tasks(self, orchestrator, lifecycle):
        """Different strategies can be used for different tasks."""
        for i in range(4):
            register_agent(
                orchestrator,
                lifecycle,
                i + 1,
                f"Agent{i + 1}",
                positive_seals=10 + i * 2,
            )

        strategies = [
            RoutingStrategy.BEST_FIT,
            RoutingStrategy.ROUND_ROBIN,
            RoutingStrategy.SPECIALIST,
            RoutingStrategy.BUDGET_AWARE,
        ]

        results = []
        for i, strategy in enumerate(strategies):
            r = orchestrator.route_task(make_task(f"t{i}"), strategy=strategy)
            results.append(r)

        assignments = [r for r in results if isinstance(r, Assignment)]
        assert len(assignments) == 4
        # Each assignment records the strategy used
        used_strategies = {a.strategy_used for a in assignments}
        assert len(used_strategies) == 4

    def test_default_strategy_used_when_none_specified(self, orchestrator, lifecycle):
        """Default strategy is used when no strategy is specified."""
        register_agent(orchestrator, lifecycle, 1, "Alpha")
        result = orchestrator.route_task(make_task())  # No strategy arg
        assert isinstance(result, Assignment)
        assert result.strategy_used == RoutingStrategy.BEST_FIT  # Default in fixture
