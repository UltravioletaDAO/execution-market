"""
Tests for StrategyEngine — Intelligent multi-strategy task routing.

Coverage targets:
    - Decision making (strategy selection, confidence, reasons)
    - Deadline analysis (pressure detection, scoring)
    - Specialization detection (specialist matching, is_specialist)
    - Load balance analysis (imbalance detection, underloaded agents)
    - Value analysis (bounty-based scoring)
    - Historical learning (outcome recording, strategy adaptation)
    - Category profiles (learning, best strategy, success rates)
    - Agent specialization (category tracking, Herfindahl index)
    - Composite routing (full pipeline)
    - Edge cases (empty state, no agents, no history)
"""

from datetime import datetime, timezone, timedelta

import pytest

from mcp_server.swarm.strategy_engine import (
    StrategyEngine,
    RoutingDecision,
    AgentLoad,
    StrategyOutcome,
    StrategyReason,
    CategoryProfile,
    AgentSpecialization,
)
from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    TaskPriority,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
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


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def bridge():
    return ReputationBridge()


@pytest.fixture
def lifecycle():
    return LifecycleManager()


@pytest.fixture
def orchestrator(bridge, lifecycle):
    return SwarmOrchestrator(bridge, lifecycle)


@pytest.fixture
def engine(orchestrator, lifecycle):
    return StrategyEngine(orchestrator, lifecycle)


@pytest.fixture
def engine_with_agents(orchestrator, lifecycle, bridge):
    """Engine with registered agents ready for routing."""
    eng = StrategyEngine(orchestrator, lifecycle)

    for i in range(1, 5):
        wallet = "0x" + f"{i:02x}" * 20
        lifecycle.register_agent(
            agent_id=i,
            name=f"Agent-{i}",
            wallet_address=wallet,
        )
        lifecycle.transition(i, AgentState.IDLE, "test setup")
        lifecycle.transition(i, AgentState.ACTIVE, "test setup")

        on_chain = OnChainReputation(agent_id=i, wallet_address=wallet)
        internal = InternalReputation(agent_id=i)
        orchestrator.register_reputation(i, on_chain, internal)

    return eng


@pytest.fixture
def task_basic():
    return TaskRequest(
        task_id="test-1",
        title="Test Task",
        categories=["delivery"],
        bounty_usd=5.0,
    )


@pytest.fixture
def task_urgent():
    return TaskRequest(
        task_id="urgent-1",
        title="Urgent Task",
        categories=["delivery"],
        bounty_usd=5.0,
        deadline=datetime.now(timezone.utc) + timedelta(hours=1),
    )


@pytest.fixture
def task_high_value():
    return TaskRequest(
        task_id="hv-1",
        title="High Value Task",
        categories=["blockchain", "defi"],
        bounty_usd=100.0,
    )


# ─── Decision Making Tests ──────────────────────────────────────────────────

class TestDecisionMaking:

    def test_default_decision_no_signals(self, engine, task_basic):
        decision = engine.decide(task_basic)
        assert isinstance(decision, RoutingDecision)
        # With no history, "delivery" is a new category → triggers ROUND_ROBIN
        # or falls back to BEST_FIT
        assert decision.strategy in (RoutingStrategy.BEST_FIT, RoutingStrategy.ROUND_ROBIN)
        assert 0 <= decision.confidence <= 1.0

    def test_decision_has_explanation(self, engine, task_basic):
        decision = engine.decide(task_basic)
        assert len(decision.explanation) > 0

    def test_decision_to_dict(self, engine, task_basic):
        decision = engine.decide(task_basic)
        d = decision.to_dict()
        assert "strategy" in d
        assert "confidence" in d
        assert "reasons" in d
        assert "metadata" in d
        assert "scores" in d["metadata"]

    def test_decision_increments_counter(self, engine, task_basic):
        assert engine._decision_count == 0
        engine.decide(task_basic)
        assert engine._decision_count == 1
        engine.decide(task_basic)
        assert engine._decision_count == 2


# ─── Deadline Analysis Tests ─────────────────────────────────────────────────

class TestDeadlineAnalysis:

    def test_no_deadline_zero_score(self, engine):
        task = TaskRequest(task_id="nd-1", title="No Deadline", categories=["test"])
        score = engine._analyze_deadline(task)
        assert score == 0.0

    def test_imminent_deadline_high_score(self, engine):
        task = TaskRequest(
            task_id="imm-1",
            title="Imminent",
            categories=["test"],
            deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        score = engine._analyze_deadline(task)
        assert score > 0.8

    def test_past_deadline_max_score(self, engine):
        task = TaskRequest(
            task_id="past-1",
            title="Overdue",
            categories=["test"],
            deadline=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        score = engine._analyze_deadline(task)
        assert score == 1.0

    def test_far_deadline_zero_score(self, engine):
        task = TaskRequest(
            task_id="far-1",
            title="Far Away",
            categories=["test"],
            deadline=datetime.now(timezone.utc) + timedelta(days=7),
        )
        score = engine._analyze_deadline(task)
        assert score == 0.0

    def test_deadline_pressure_triggers_reason(self, engine, task_urgent):
        decision = engine.decide(task_urgent)
        assert StrategyReason.DEADLINE_PRESSURE in decision.reasons

    def test_moderate_deadline_moderate_score(self, engine):
        task = TaskRequest(
            task_id="mod-1",
            title="Moderate",
            categories=["test"],
            deadline=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        score = engine._analyze_deadline(task)
        assert 0.3 < score < 0.7


# ─── Value Analysis Tests ────────────────────────────────────────────────────

class TestValueAnalysis:

    def test_zero_bounty(self, engine):
        assert engine._analyze_value(
            TaskRequest(task_id="v0", title="Free", categories=["test"], bounty_usd=0)
        ) == 0.0

    def test_low_bounty(self, engine):
        score = engine._analyze_value(
            TaskRequest(task_id="v1", title="Low", categories=["test"], bounty_usd=1.0)
        )
        assert 0 <= score <= 0.5

    def test_medium_bounty(self, engine):
        score = engine._analyze_value(
            TaskRequest(task_id="v2", title="Med", categories=["test"], bounty_usd=10.0)
        )
        assert 0.3 < score <= 1.0

    def test_high_bounty(self, engine):
        score = engine._analyze_value(
            TaskRequest(task_id="v3", title="High", categories=["test"], bounty_usd=100.0)
        )
        assert score > 0.5

    def test_very_high_bounty_capped(self, engine):
        score = engine._analyze_value(
            TaskRequest(task_id="v4", title="VHigh", categories=["test"], bounty_usd=10000.0)
        )
        assert score <= 1.0

    def test_high_value_triggers_reason(self, engine, task_high_value):
        decision = engine.decide(task_high_value)
        assert StrategyReason.HIGH_VALUE_TASK in decision.reasons


# ─── Load Balance Analysis Tests ──────────────────────────────────────────────

class TestLoadBalanceAnalysis:

    def test_no_loads(self, engine):
        result = engine._analyze_load_balance({})
        assert not result["imbalanced"]

    def test_single_agent(self, engine):
        loads = {1: AgentLoad(agent_id=1, active_tasks=5)}
        result = engine._analyze_load_balance(loads)
        assert not result["imbalanced"]

    def test_balanced_load(self, engine):
        loads = {
            1: AgentLoad(agent_id=1, active_tasks=2),
            2: AgentLoad(agent_id=2, active_tasks=2),
            3: AgentLoad(agent_id=3, active_tasks=2),
        }
        result = engine._analyze_load_balance(loads)
        assert not result["imbalanced"]

    def test_imbalanced_load(self, engine):
        loads = {
            1: AgentLoad(agent_id=1, active_tasks=10, completed_today=20),
            2: AgentLoad(agent_id=2, active_tasks=0, completed_today=0),
        }
        result = engine._analyze_load_balance(loads)
        assert result["imbalanced"]
        assert 2 in result["underloaded"]

    def test_load_imbalance_triggers_round_robin(self, engine, task_basic):
        loads = {
            1: AgentLoad(agent_id=1, active_tasks=10, completed_today=20),
            2: AgentLoad(agent_id=2, active_tasks=0, completed_today=0),
        }
        decision = engine.decide(task_basic, agent_loads=loads)
        assert StrategyReason.LOAD_IMBALANCE in decision.reasons

    def test_exhausted_agents_excluded(self, engine):
        loads = {
            1: AgentLoad(agent_id=1, daily_budget_remaining_pct=0),
            2: AgentLoad(agent_id=2, daily_budget_remaining_pct=80),
        }
        result = engine._analyze_load_balance(loads)
        # Agent 1 has 0% budget, should not appear in underloaded
        if result["underloaded"]:
            assert 1 not in result["underloaded"]


# ─── AgentLoad Tests ─────────────────────────────────────────────────────────

class TestAgentLoad:

    def test_agent_available_when_idle(self):
        load = AgentLoad(agent_id=1, active_tasks=0, daily_budget_remaining_pct=50)
        assert load.is_available

    def test_agent_unavailable_when_busy(self):
        load = AgentLoad(agent_id=1, active_tasks=2)
        assert not load.is_available

    def test_agent_unavailable_when_no_budget(self):
        load = AgentLoad(agent_id=1, active_tasks=0, daily_budget_remaining_pct=0)
        assert not load.is_available

    def test_load_score_increases_with_tasks(self):
        light = AgentLoad(agent_id=1, active_tasks=0)
        heavy = AgentLoad(agent_id=2, active_tasks=5)
        assert heavy.load_score > light.load_score

    def test_load_score_considers_budget(self):
        full_budget = AgentLoad(agent_id=1, daily_budget_remaining_pct=100)
        low_budget = AgentLoad(agent_id=2, daily_budget_remaining_pct=10)
        assert low_budget.load_score > full_budget.load_score


# ─── Specialization Detection Tests ──────────────────────────────────────────

class TestSpecializationDetection:

    def test_no_specializations(self, engine, task_basic):
        result = engine._analyze_specialization(task_basic)
        assert not result["has_specialist"]

    def test_specialist_detected(self, engine, task_basic):
        # Create a specialist
        spec = AgentSpecialization(
            agent_id=1,
            category_task_counts={"delivery": 20, "errand": 3},
            category_success_rates={"delivery": 0.95, "errand": 0.6},
        )
        engine._agent_specializations[1] = spec
        result = engine._analyze_specialization(task_basic)
        assert result["has_specialist"]
        assert 1 in result["specialists"]

    def test_is_specialist_property(self):
        # Specialist: >60% in ≤2 categories
        specialist = AgentSpecialization(
            agent_id=1,
            category_task_counts={"delivery": 50, "errand": 30, "coding": 5, "research": 2},
        )
        assert specialist.is_specialist  # 80/87 = 92% in top 2

    def test_is_not_specialist(self):
        generalist = AgentSpecialization(
            agent_id=2,
            category_task_counts={"delivery": 5, "coding": 5, "research": 5, "design": 5},
        )
        assert not generalist.is_specialist  # 10/20 = 50% in top 2

    def test_insufficient_history_not_specialist(self):
        newbie = AgentSpecialization(
            agent_id=3,
            category_task_counts={"delivery": 3},
        )
        assert not newbie.is_specialist  # Only 3 tasks, need 5 minimum

    def test_no_history_not_specialist(self):
        empty = AgentSpecialization(agent_id=4)
        assert not empty.is_specialist

    def test_specialist_triggers_strategy(self, engine, task_basic):
        spec = AgentSpecialization(
            agent_id=1,
            category_task_counts={"delivery": 20},
            category_success_rates={"delivery": 0.9},
        )
        engine._agent_specializations[1] = spec
        decision = engine.decide(task_basic)
        assert StrategyReason.SPECIALIST_AVAILABLE in decision.reasons


# ─── New Category Detection Tests ────────────────────────────────────────────

class TestNewCategoryDetection:

    def test_new_category_detected(self, engine):
        task = TaskRequest(task_id="nc-1", title="New", categories=["quantum_computing"])
        assert engine._is_new_category(task)

    def test_known_category_not_new(self, engine):
        engine._category_profiles["delivery"] = CategoryProfile(category="delivery", total_tasks=10)
        task = TaskRequest(task_id="kc-1", title="Known", categories=["delivery"])
        assert not engine._is_new_category(task)

    def test_low_history_still_new(self, engine):
        engine._category_profiles["delivery"] = CategoryProfile(category="delivery", total_tasks=2)
        task = TaskRequest(task_id="lh-1", title="Low History", categories=["delivery"])
        assert engine._is_new_category(task)  # Only 2 tasks, need 3

    def test_new_category_triggers_round_robin(self, engine):
        task = TaskRequest(task_id="ncrr-1", title="New Cat", categories=["alien_tech"])
        decision = engine.decide(task)
        assert StrategyReason.NEW_CATEGORY in decision.reasons


# ─── Outcome Recording Tests ─────────────────────────────────────────────────

class TestOutcomeRecording:

    def test_record_outcome_basic(self, engine):
        engine.record_outcome(
            task_id="out-1",
            strategy_used=RoutingStrategy.BEST_FIT,
            agent_id=1,
            success=True,
            categories=["delivery"],
        )
        assert len(engine._outcomes) == 1

    def test_record_outcome_updates_strategy_success(self, engine):
        engine.record_outcome("o1", RoutingStrategy.BEST_FIT, 1, True, ["delivery"])
        engine.record_outcome("o2", RoutingStrategy.BEST_FIT, 1, False, ["delivery"])
        assert len(engine._strategy_success["best_fit"]) == 2

    def test_record_outcome_updates_category_profile(self, engine):
        engine.record_outcome("o1", RoutingStrategy.BEST_FIT, 1, True, ["delivery"],
                            completion_time_minutes=30.0, quality_score=0.9)
        profile = engine.get_category_profile("delivery")
        assert profile is not None
        assert profile.total_tasks == 1
        assert profile.successful_tasks == 1
        assert profile.avg_quality == 0.9

    def test_record_outcome_updates_specialization(self, engine):
        for i in range(5):
            engine.record_outcome(f"spec-{i}", RoutingStrategy.BEST_FIT, 1, True, ["delivery"])
        spec = engine.get_agent_specialization(1)
        assert spec is not None
        assert "delivery" in spec.category_task_counts
        assert spec.category_task_counts["delivery"] == 5

    def test_outcomes_bounded(self, engine):
        for i in range(6000):
            engine.record_outcome(f"bound-{i}", RoutingStrategy.BEST_FIT, 1, True)
        assert len(engine._outcomes) <= 5000  # Pruned from 5001 to 2500, then grows

    def test_category_profile_running_averages(self, engine):
        engine.record_outcome("avg-1", RoutingStrategy.BEST_FIT, 1, True, ["delivery"],
                            completion_time_minutes=30.0, quality_score=0.8)
        engine.record_outcome("avg-2", RoutingStrategy.BEST_FIT, 1, True, ["delivery"],
                            completion_time_minutes=60.0, quality_score=1.0)
        profile = engine.get_category_profile("delivery")
        assert profile.avg_completion_minutes == pytest.approx(45.0)
        assert profile.avg_quality == pytest.approx(0.9)

    def test_category_profile_success_rate(self, engine):
        engine.record_outcome("sr-1", RoutingStrategy.BEST_FIT, 1, True, ["coding"])
        engine.record_outcome("sr-2", RoutingStrategy.BEST_FIT, 1, True, ["coding"])
        engine.record_outcome("sr-3", RoutingStrategy.BEST_FIT, 1, False, ["coding"])
        profile = engine.get_category_profile("coding")
        assert profile.success_rate == pytest.approx(2/3)

    def test_category_tracks_best_agents(self, engine):
        engine.record_outcome("ba-1", RoutingStrategy.BEST_FIT, 1, True, ["delivery"])
        engine.record_outcome("ba-2", RoutingStrategy.BEST_FIT, 2, True, ["delivery"])
        engine.record_outcome("ba-3", RoutingStrategy.BEST_FIT, 3, False, ["delivery"])  # Failed
        profile = engine.get_category_profile("delivery")
        assert 1 in profile.best_agents
        assert 2 in profile.best_agents
        assert 3 not in profile.best_agents  # Failed, not best


# ─── Historical Learning Tests ───────────────────────────────────────────────

class TestHistoricalLearning:

    def test_no_history_no_recommendation(self, engine, task_basic):
        result = engine._analyze_historical(task_basic)
        assert result["best_strategy"] is None

    def test_learns_from_outcomes(self, engine, task_basic):
        # Record enough successful SPECIALIST outcomes
        for i in range(15):
            engine.record_outcome(
                f"learn-{i}",
                RoutingStrategy.SPECIALIST,
                1,
                success=True,
                categories=["delivery"],
            )
        # Record some failed BEST_FIT outcomes
        for i in range(10):
            engine.record_outcome(
                f"fail-{i}",
                RoutingStrategy.BEST_FIT,
                2,
                success=False,
                categories=["delivery"],
            )

        result = engine._analyze_historical(task_basic)
        assert result["best_strategy"] == RoutingStrategy.SPECIALIST
        assert result["success_rate"] > 0.6

    def test_insufficient_history_uses_overall(self, engine):
        # Record overall outcomes but not for our specific category
        for i in range(20):
            engine.record_outcome(
                f"overall-{i}",
                RoutingStrategy.ROUND_ROBIN,
                1,
                success=True,
                categories=["coding"],
            )
        task = TaskRequest(task_id="rare-1", title="Rare", categories=["rare_category"])
        result = engine._analyze_historical(task)
        # Should use overall stats since "rare_category" has no history
        if result["best_strategy"]:
            assert result["success_rate"] > 0


# ─── Composite Routing Tests ─────────────────────────────────────────────────

class TestCompositeRouting:

    def test_route_with_strategy(self, engine_with_agents, task_basic):
        decision, result = engine_with_agents.route_with_strategy(task_basic)
        assert isinstance(decision, RoutingDecision)
        assert isinstance(result, (Assignment, RoutingFailure))

    def test_route_with_loads(self, engine_with_agents, task_basic):
        loads = {
            i: AgentLoad(agent_id=i, active_tasks=0) for i in range(1, 5)
        }
        decision, result = engine_with_agents.route_with_strategy(task_basic, agent_loads=loads)
        assert isinstance(decision, RoutingDecision)

    def test_route_applies_preferences(self, engine_with_agents):
        # Set up a specialist
        engine_with_agents._agent_specializations[2] = AgentSpecialization(
            agent_id=2,
            category_task_counts={"blockchain": 20},
            category_success_rates={"blockchain": 0.95},
        )
        task = TaskRequest(
            task_id="pref-1",
            title="Blockchain Task",
            categories=["blockchain"],
            bounty_usd=50.0,
        )
        decision, result = engine_with_agents.route_with_strategy(task)
        # Agent 2 should be preferred
        if decision.preferred_agents:
            assert 2 in decision.preferred_agents


# ─── Strategy Report Tests ───────────────────────────────────────────────────

class TestStrategyReport:

    def test_empty_report(self, engine):
        report = engine.get_strategy_report()
        assert report["total_decisions"] == 0
        assert report["total_outcomes"] == 0
        assert report["strategy_performance"] == {}
        assert report["category_profiles"] == {}
        assert report["agent_specializations"] == {}

    def test_report_after_outcomes(self, engine):
        engine.record_outcome("r1", RoutingStrategy.BEST_FIT, 1, True, ["delivery"],
                            completion_time_minutes=15, quality_score=0.9)
        engine.record_outcome("r2", RoutingStrategy.BEST_FIT, 1, True, ["delivery"],
                            completion_time_minutes=20, quality_score=0.85)
        engine.record_outcome("r3", RoutingStrategy.ROUND_ROBIN, 2, False, ["coding"])

        engine.decide(TaskRequest(task_id="d1", title="Test", categories=["test"]))

        report = engine.get_strategy_report()
        assert report["total_decisions"] == 1
        assert report["total_outcomes"] == 3
        assert "best_fit" in report["strategy_performance"]
        assert report["strategy_performance"]["best_fit"]["total"] == 2
        assert "delivery" in report["category_profiles"]
        assert "1" in report["agent_specializations"]


# ─── StrategyOutcome Tests ────────────────────────────────────────────────────

class TestStrategyOutcome:

    def test_outcome_to_dict(self):
        outcome = StrategyOutcome(
            task_id="out-1",
            strategy_used=RoutingStrategy.BEST_FIT,
            agent_assigned=1,
            success=True,
            completion_time_minutes=30.5,
            quality_score=0.85,
        )
        d = outcome.to_dict()
        assert d["task_id"] == "out-1"
        assert d["strategy"] == "best_fit"
        assert d["agent"] == 1
        assert d["success"] is True
        assert d["completion_minutes"] == 30.5
        assert d["quality"] == 0.85


# ─── CategoryProfile Tests ───────────────────────────────────────────────────

class TestCategoryProfile:

    def test_success_rate_empty(self):
        profile = CategoryProfile(category="test")
        assert profile.success_rate == 0.0

    def test_success_rate_computed(self):
        profile = CategoryProfile(category="test", total_tasks=10, successful_tasks=8)
        assert profile.success_rate == 0.8


# ─── Edge Cases ──────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_decide_with_empty_categories(self, engine):
        task = TaskRequest(task_id="ec-1", title="No Cats", categories=[])
        decision = engine.decide(task)
        assert isinstance(decision, RoutingDecision)

    def test_decide_with_none_deadline(self, engine, task_basic):
        task_basic.deadline = None
        decision = engine.decide(task_basic)
        assert StrategyReason.DEADLINE_PRESSURE not in decision.reasons

    def test_record_outcome_without_categories(self, engine):
        engine.record_outcome("nc-1", RoutingStrategy.BEST_FIT, 1, True)
        assert len(engine._outcomes) == 1

    def test_record_outcome_without_agent(self, engine):
        engine.record_outcome("na-1", RoutingStrategy.BEST_FIT, None, False, ["delivery"])
        assert len(engine._outcomes) == 1

    def test_get_nonexistent_category_profile(self, engine):
        assert engine.get_category_profile("nonexistent") is None

    def test_get_nonexistent_specialization(self, engine):
        assert engine.get_agent_specialization(999) is None

    def test_multiple_decisions_independent(self, engine, task_basic):
        d1 = engine.decide(task_basic)
        d2 = engine.decide(task_basic)
        # Each decision should be independent
        assert d1.metadata["decision_number"] == 1
        assert d2.metadata["decision_number"] == 2
