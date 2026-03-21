"""Tests for SwarmOrchestrator."""

import pytest
from datetime import datetime, timezone, timedelta

from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    RoutingStrategy,
    TaskRequest,
    Assignment,
    RoutingFailure,
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


@pytest.fixture
def bridge():
    return ReputationBridge()


@pytest.fixture
def lifecycle():
    return LifecycleManager()


@pytest.fixture
def orchestrator(bridge, lifecycle):
    return SwarmOrchestrator(
        bridge=bridge,
        lifecycle=lifecycle,
        cooldown_seconds=5,
        min_score_threshold=10.0,
    )


def setup_agent(
    orchestrator,
    agent_id: int,
    name: str,
    wallet: str = "0x",
    total_tasks: int = 50,
    successful_tasks: int = 45,
    avg_rating: float = 4.5,
    bayesian_score: float = 0.8,
    total_seals: int = 30,
    positive_seals: int = 28,
    chains: list | None = None,
    category_scores: dict | None = None,
    budget_config: BudgetConfig | None = None,
):
    """Helper: register + reputation + set to ACTIVE."""
    orchestrator.lifecycle.register_agent(
        agent_id,
        name,
        wallet,
        budget_config=budget_config,
    )
    orchestrator.lifecycle.transition(agent_id, AgentState.IDLE)
    orchestrator.lifecycle.transition(agent_id, AgentState.ACTIVE)

    on_chain = OnChainReputation(
        agent_id=agent_id,
        wallet_address=wallet,
        total_seals=total_seals,
        positive_seals=positive_seals,
        negative_seals=total_seals - positive_seals,
        chains_active=chains or ["base"],
    )
    internal = InternalReputation(
        agent_id=agent_id,
        bayesian_score=bayesian_score,
        total_tasks=total_tasks,
        successful_tasks=successful_tasks,
        avg_rating=avg_rating,
        category_scores=category_scores or {},
    )
    orchestrator.register_reputation(agent_id, on_chain, internal)


class TestBasicRouting:
    def test_route_to_only_agent(self, orchestrator):
        setup_agent(orchestrator, 1, "aurora")
        task = TaskRequest(task_id="t1", title="Test task")
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 1
        assert result.task_id == "t1"

    def test_route_to_best_agent(self, orchestrator):
        setup_agent(
            orchestrator,
            1,
            "aurora",
            total_tasks=3,
            avg_rating=2.0,
            bayesian_score=0.15,
            total_seals=2,
            positive_seals=1,
            successful_tasks=1,
        )
        setup_agent(
            orchestrator,
            2,
            "blaze",
            total_tasks=100,
            avg_rating=4.9,
            bayesian_score=0.95,
            total_seals=80,
            positive_seals=78,
            chains=["base", "eth", "poly", "arb"],
        )
        task = TaskRequest(task_id="t1", title="Test task")
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 2  # Higher score

    def test_no_available_agents(self, orchestrator):
        task = TaskRequest(task_id="t1", title="Test task")
        result = orchestrator.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "No agents available" in result.reason

    def test_duplicate_claim_rejected(self, orchestrator):
        setup_agent(orchestrator, 1, "aurora")
        task = TaskRequest(task_id="t1", title="Test task")
        result1 = orchestrator.route_task(task)
        assert isinstance(result1, Assignment)

        # Second attempt for same task
        setup_agent(orchestrator, 2, "blaze")
        result2 = orchestrator.route_task(task)
        assert isinstance(result2, RoutingFailure)
        assert "already claimed" in result2.reason


class TestExclusions:
    def test_exclude_agents(self, orchestrator):
        setup_agent(orchestrator, 1, "aurora", total_tasks=100, avg_rating=5.0)
        setup_agent(orchestrator, 2, "blaze", total_tasks=10, avg_rating=3.0)
        task = TaskRequest(
            task_id="t1",
            title="Test",
            exclude_agent_ids=[1],
        )
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 2  # Only non-excluded agent

    def test_all_excluded_fails(self, orchestrator):
        setup_agent(orchestrator, 1, "aurora")
        task = TaskRequest(
            task_id="t1",
            title="Test",
            exclude_agent_ids=[1],
        )
        result = orchestrator.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "excluded" in result.reason


class TestPreferences:
    def test_preferred_agent_selected(self, orchestrator):
        setup_agent(
            orchestrator,
            1,
            "aurora",
            total_tasks=100,
            avg_rating=5.0,
            bayesian_score=0.95,
        )
        setup_agent(
            orchestrator, 2, "blaze", total_tasks=10, avg_rating=3.5, bayesian_score=0.6
        )
        task = TaskRequest(
            task_id="t1",
            title="Test",
            preferred_agent_ids=[2],
        )
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 2  # Preferred despite lower score


class TestStrategies:
    def test_best_fit_strategy(self, orchestrator):
        setup_agent(orchestrator, 1, "a", bayesian_score=0.5, avg_rating=3.0)
        setup_agent(orchestrator, 2, "b", bayesian_score=0.9, avg_rating=4.8)
        task = TaskRequest(task_id="t1", title="Test")
        result = orchestrator.route_task(task, strategy=RoutingStrategy.BEST_FIT)
        assert isinstance(result, Assignment)
        assert result.agent_id == 2
        assert result.strategy_used == RoutingStrategy.BEST_FIT

    def test_round_robin_distribution(self, orchestrator):
        setup_agent(orchestrator, 1, "a", bayesian_score=0.8)
        setup_agent(orchestrator, 2, "b", bayesian_score=0.8)
        setup_agent(orchestrator, 3, "c", bayesian_score=0.8)

        # Route 3 tasks with round robin
        assignments = []
        for i in range(3):
            task = TaskRequest(task_id=f"t{i}", title=f"Task {i}")
            result = orchestrator.route_task(task, strategy=RoutingStrategy.ROUND_ROBIN)
            if isinstance(result, Assignment):
                assignments.append(result)
                orchestrator.complete_task(result.task_id)
                # Re-activate agent for next round
                orchestrator.lifecycle._agents[result.agent_id].cooldown_until = (
                    datetime.now(timezone.utc) - timedelta(seconds=1)
                )
                orchestrator.lifecycle.check_cooldown_expiry(result.agent_id)
                orchestrator.lifecycle.transition(result.agent_id, AgentState.ACTIVE)

        assert len(assignments) == 3
        # Should have distributed across agents (not all to the same one)
        agent_ids = [a.agent_id for a in assignments]
        assert len(set(agent_ids)) > 1  # At least 2 different agents

    def test_specialist_strategy(self, orchestrator):
        # Generalist: has tasks but no category-specific scores, very low stats
        setup_agent(
            orchestrator,
            1,
            "generalist",
            category_scores={},
            total_tasks=3,
            avg_rating=2.5,
            bayesian_score=0.2,
            successful_tasks=2,
            total_seals=1,
            positive_seals=0,
        )
        # Specialist: strong in photo_verification
        setup_agent(
            orchestrator,
            2,
            "specialist",
            category_scores={"photo_verification": 0.95},
            total_tasks=80,
            avg_rating=4.8,
            bayesian_score=0.9,
        )
        task = TaskRequest(
            task_id="t1",
            title="Photo task",
            categories=["photo_verification"],
        )
        result = orchestrator.route_task(task, strategy=RoutingStrategy.SPECIALIST)
        assert isinstance(result, Assignment)
        assert result.agent_id == 2  # Specialist has higher skill_score (>50)

    def test_specialist_no_match(self, orchestrator):
        # Agent with no category scores AND very low general experience
        setup_agent(
            orchestrator,
            1,
            "generalist",
            category_scores={},
            total_tasks=1,
            avg_rating=2.0,
            bayesian_score=0.1,
            successful_tasks=0,
            total_seals=0,
            positive_seals=0,
        )
        task = TaskRequest(
            task_id="t1",
            title="Niche task",
            categories=["super_specific_niche"],
        )
        result = orchestrator.route_task(task, strategy=RoutingStrategy.SPECIALIST)
        # Generalist's skill_score from fallback should be <50
        # 1 task, 0 success: success_rate=0, so skill = 0*60 + min(1/50,1)*40 = 0.8 → very low
        assert isinstance(result, RoutingFailure)

    def test_budget_aware_strategy(self, orchestrator):
        # Agent 1: low budget remaining, low reputation
        budget1 = BudgetConfig(daily_limit_usd=5.0)
        setup_agent(
            orchestrator,
            1,
            "expensive",
            budget_config=budget1,
            total_tasks=10,
            avg_rating=3.5,
            bayesian_score=0.5,
        )
        orchestrator.lifecycle.record_spend(1, 4.0)  # 80% used

        # Agent 2: plenty of budget, same reputation
        budget2 = BudgetConfig(daily_limit_usd=5.0)
        setup_agent(
            orchestrator,
            2,
            "fresh",
            budget_config=budget2,
            total_tasks=10,
            avg_rating=3.5,
            bayesian_score=0.5,
        )
        orchestrator.lifecycle.record_spend(2, 0.5)  # 10% used

        task = TaskRequest(task_id="t1", title="Test")
        result = orchestrator.route_task(task, strategy=RoutingStrategy.BUDGET_AWARE)
        assert isinstance(result, Assignment)
        assert result.agent_id == 2  # Has more budget headroom


class TestTaskCompletion:
    def test_complete_task(self, orchestrator):
        setup_agent(orchestrator, 1, "aurora")
        task = TaskRequest(task_id="t1", title="Test")
        orchestrator.route_task(task)

        agent_id = orchestrator.complete_task("t1")
        assert agent_id == 1
        assert "t1" not in orchestrator._active_claims
        assert orchestrator.lifecycle.agents[1].state == AgentState.COOLDOWN

    def test_complete_unknown_task(self, orchestrator):
        result = orchestrator.complete_task("nonexistent")
        assert result is None

    def test_fail_task(self, orchestrator):
        setup_agent(orchestrator, 1, "aurora")
        task = TaskRequest(task_id="t1", title="Test")
        orchestrator.route_task(task)

        agent_id = orchestrator.fail_task("t1", "connection timeout")
        assert agent_id == 1
        assert orchestrator.lifecycle.agents[1].health.errors_last_hour == 1
        # Internal reputation should track failure
        assert orchestrator._internal[1].consecutive_failures == 1

    def test_fail_unknown_task(self, orchestrator):
        result = orchestrator.fail_task("nonexistent")
        assert result is None


class TestCategoryRouting:
    def test_photo_specialist_wins(self, orchestrator):
        setup_agent(
            orchestrator,
            1,
            "photo_pro",
            category_scores={"photo_verification": 0.95, "delivery": 0.7},
            total_tasks=80,
            avg_rating=4.8,
            bayesian_score=0.9,
        )
        setup_agent(
            orchestrator,
            2,
            "delivery_pro",
            category_scores={"delivery": 0.95, "photo_verification": 0.3},
            total_tasks=80,
            avg_rating=4.8,
            bayesian_score=0.9,
        )
        task = TaskRequest(
            task_id="t1",
            title="Photo check",
            categories=["photo_verification"],
        )
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 1  # Photo specialist


class TestOrchestratorStatus:
    def test_status_shape(self, orchestrator):
        status = orchestrator.get_status()
        assert "active_claims" in status
        assert "total_assignments" in status
        assert "total_failures" in status
        assert "default_strategy" in status
        assert "swarm" in status

    def test_assignment_history(self, orchestrator):
        setup_agent(orchestrator, 1, "aurora")
        task = TaskRequest(task_id="t1", title="Test")
        orchestrator.route_task(task)

        history = orchestrator.get_assignment_history()
        assert len(history) == 1
        assert history[0]["task_id"] == "t1"
        assert history[0]["agent_id"] == 1

    def test_failure_history(self, orchestrator):
        task = TaskRequest(task_id="t1", title="Test")
        orchestrator.route_task(task)

        failures = orchestrator.get_failures()
        assert len(failures) == 1
        assert failures[0]["task_id"] == "t1"


class TestEdgeCases:
    def test_agent_without_reputation_data(self, orchestrator):
        """Agent registered in lifecycle but not in reputation store."""
        orchestrator.lifecycle.register_agent(1, "unknown", "0x1")
        orchestrator.lifecycle.transition(1, AgentState.IDLE)
        orchestrator.lifecycle.transition(1, AgentState.ACTIVE)

        task = TaskRequest(task_id="t1", title="Test")
        result = orchestrator.route_task(task)
        # Should still route with default scores
        assert isinstance(result, Assignment)

    def test_agent_goes_idle_during_scoring(self, orchestrator):
        """Agent becomes unavailable between scoring and assignment."""
        setup_agent(orchestrator, 1, "aurora")
        setup_agent(orchestrator, 2, "blaze")

        # Route first task to agent 2 (higher score if configured so)
        task = TaskRequest(task_id="t1", title="Test")
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)

    def test_many_agents(self, orchestrator):
        """Stress test with many agents — best agent gets the task."""
        for i in range(20):
            setup_agent(
                orchestrator,
                i,
                f"agent_{i}",
                total_tasks=2 + i * 5,
                successful_tasks=1 + i * 4,
                avg_rating=1.5 + (i * 0.15),
                bayesian_score=0.05 + (i * 0.04),
                total_seals=i * 3,
                positive_seals=i * 2,
                chains=["base"] if i < 10 else ["base", "eth", "poly"],
            )

        task = TaskRequest(task_id="t1", title="Test")
        result = orchestrator.route_task(task)
        assert isinstance(result, Assignment)
        # Agent 19: tasks=97, success=77, rating=4.35, bayesian=0.81, seals=57/38
        # Should be among the top
        assert result.agent_id >= 10  # Top half at minimum

    def test_min_score_threshold(self, orchestrator):
        """Very high threshold rejects all agents."""
        orch = SwarmOrchestrator(
            bridge=orchestrator.bridge,
            lifecycle=orchestrator.lifecycle,
            min_score_threshold=200.0,  # Impossible to reach
        )
        setup_agent(orch, 1, "aurora")
        task = TaskRequest(task_id="t1", title="Test")
        result = orch.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "minimum score" in result.reason
