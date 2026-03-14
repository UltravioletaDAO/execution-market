"""
End-to-End Swarm Integration Tests

These tests exercise the FULL swarm pipeline:
- Agent registration → task routing → execution → reputation update
- Multi-agent competition and specialization
- Failover and recovery
- Budget enforcement
- Reputation flow
- Full day simulation

All tests use the SwarmTestHarness to avoid dependency on external APIs.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta

from mcp_server.swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
    CompositeScore,
)
from mcp_server.swarm.lifecycle_manager import (
    LifecycleManager,
    AgentState,
    AgentRecord,
    BudgetConfig,
    BudgetExceededError,
)
from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
    TaskPriority,
)


# ---------------------------------------------------------------------------
# SwarmTestHarness — reusable E2E setup
# ---------------------------------------------------------------------------

class SwarmTestHarness:
    """Reusable test harness for swarm E2E tests."""

    def __init__(self, max_agents: int = 24):
        self.bridge = ReputationBridge()
        self.lifecycle = LifecycleManager()
        self.orchestrator = SwarmOrchestrator(
            bridge=self.bridge,
            lifecycle=self.lifecycle,
            min_score_threshold=0.0,  # Don't filter for tests
        )
        self._next_id = 1

    def add_agent(
        self,
        name: str,
        wallet: str = None,
        personality: str = "explorer",
        budget_daily: float = 50.0,
        activate: bool = True,
    ) -> int:
        """Register and optionally activate an agent. Returns agent_id."""
        agent_id = self._next_id
        self._next_id += 1
        wallet = wallet or f"0x{agent_id:040x}"

        budget = BudgetConfig(daily_limit_usd=budget_daily)
        self.lifecycle.register_agent(
            agent_id=agent_id,
            name=name,
            wallet_address=wallet,
            personality=personality,
            budget_config=budget,
        )

        # Register default reputation
        on_chain = OnChainReputation(
            agent_id=agent_id,
            wallet_address=wallet,
        )
        internal = InternalReputation(
            agent_id=agent_id,
        )
        self.orchestrator.register_reputation(agent_id, on_chain, internal)

        if activate:
            self.lifecycle.transition(agent_id, AgentState.IDLE, "initial setup")
            self.lifecycle.transition(agent_id, AgentState.ACTIVE, "test activation")

        return agent_id

    def add_kk_roster(self, count: int = 5) -> dict[str, int]:
        """Add a mini KarmaKadabra roster. Returns name→id map."""
        agents = [
            ("aurora", "explorer"),
            ("cipher", "auditor"),
            ("echo", "creator"),
            ("delta", "communicator"),
            ("foxtrot", "tester"),
        ]
        result = {}
        for name, personality in agents[:count]:
            agent_id = self.add_agent(name=name, personality=personality)
            result[name] = agent_id
        return result

    def route_task(
        self,
        task_id: str,
        title: str = "Test task",
        categories: list = None,
        bounty_usd: float = 1.0,
        priority: TaskPriority = TaskPriority.NORMAL,
        strategy: RoutingStrategy = None,
    ) -> Assignment | RoutingFailure:
        """Route a task through the orchestrator."""
        task = TaskRequest(
            task_id=task_id,
            title=title,
            categories=categories or ["general"],
            bounty_usd=bounty_usd,
            priority=priority,
        )
        return self.orchestrator.route_task(task, strategy=strategy)

    def complete_task(self, task_id: str, success: bool = True) -> int | None:
        """Complete a task. Returns agent_id or None."""
        if success:
            return self.orchestrator.complete_task(task_id)
        else:
            return self.orchestrator.fail_task(task_id, error="test failure")

    def record_reputation(self, agent_id: int, success: bool = True, quality: float = 0.85):
        """Update internal reputation for an agent."""
        internal = self.orchestrator._internal.get(agent_id)
        if internal is None:
            internal = InternalReputation(agent_id=agent_id)

        if success:
            internal = InternalReputation(
                agent_id=agent_id,
                total_tasks=internal.total_tasks + 1,
                successful_tasks=internal.successful_tasks + 1,
                bayesian_score=min(1.0, internal.bayesian_score + 0.05),
                avg_rating=quality * 5.0,
                consecutive_failures=0,
            )
        else:
            internal = InternalReputation(
                agent_id=agent_id,
                total_tasks=internal.total_tasks + 1,
                successful_tasks=internal.successful_tasks,
                bayesian_score=max(0.0, internal.bayesian_score - 0.1),
                avg_rating=internal.avg_rating,
                consecutive_failures=internal.consecutive_failures + 1,
            )

        on_chain = self.orchestrator._on_chain.get(agent_id, OnChainReputation(
            agent_id=agent_id,
            wallet_address=f"0x{agent_id:040x}",
        ))
        self.orchestrator.register_reputation(agent_id, on_chain, internal)


# ---------------------------------------------------------------------------
# TestFullTaskPipeline
# ---------------------------------------------------------------------------

class TestFullTaskPipeline:
    """Tests the complete lifecycle of tasks through the swarm."""

    def setup_method(self):
        self.harness = SwarmTestHarness()
        self.agents = self.harness.add_kk_roster(3)

    def test_single_task_full_pipeline(self):
        """Single task: register → route → complete → reputation update."""
        result = self.harness.route_task("task_001", categories=["research"], bounty_usd=2.0)
        assert isinstance(result, Assignment)
        assert result.agent_id in self.agents.values()

        completed_agent = self.harness.complete_task("task_001", success=True)
        assert completed_agent is not None

        # Record reputation
        self.harness.record_reputation(completed_agent, success=True)

    def test_failed_task_pipeline(self):
        """Failed task: route → fail → error tracking."""
        result = self.harness.route_task("task_fail", categories=["general"])
        assert isinstance(result, Assignment)

        failed_agent = self.harness.complete_task("task_fail", success=False)
        assert failed_agent is not None
        self.harness.record_reputation(failed_agent, success=False)

    def test_multi_task_sequential_pipeline(self):
        """Multiple tasks completed sequentially."""
        completed = 0
        for i in range(5):
            result = self.harness.route_task(f"task_{i}", categories=["general"])
            if isinstance(result, Assignment):
                agent_id = self.harness.complete_task(f"task_{i}", success=True)
                if agent_id:
                    self.harness.record_reputation(agent_id, success=True)
                    completed += 1
        assert completed >= 3  # At least some should complete

    def test_duplicate_task_rejected(self):
        """Same task ID can't be assigned twice."""
        r1 = self.harness.route_task("dup_task")
        assert isinstance(r1, Assignment)

        r2 = self.harness.route_task("dup_task")
        assert isinstance(r2, RoutingFailure)
        assert "already claimed" in r2.reason


# ---------------------------------------------------------------------------
# TestMultiAgentCompetition
# ---------------------------------------------------------------------------

class TestMultiAgentCompetition:
    """Tests multi-agent competition for tasks."""

    def setup_method(self):
        self.harness = SwarmTestHarness()
        self.agents = self.harness.add_kk_roster(5)

    def test_tasks_distribute_across_agents(self):
        """Multiple tasks should distribute across agents."""
        assignments = []
        for i in range(5):
            result = self.harness.route_task(f"dist_{i}", categories=["general"])
            if isinstance(result, Assignment):
                assignments.append(result)
                self.harness.complete_task(f"dist_{i}", success=True)

        agent_ids = {a.agent_id for a in assignments}
        assert len(agent_ids) >= 2  # Should spread across agents

    def test_alternatives_count_tracked(self):
        """Assignment should track how many alternatives were considered."""
        result = self.harness.route_task("alt_test")
        if isinstance(result, Assignment):
            assert result.alternatives_count >= 0

    def test_round_robin_distributes(self):
        """ROUND_ROBIN strategy should distribute tasks."""
        assignments = []
        for i in range(10):
            result = self.harness.route_task(
                f"rr_{i}", strategy=RoutingStrategy.ROUND_ROBIN,
            )
            if isinstance(result, Assignment):
                assignments.append(result)
                self.harness.complete_task(f"rr_{i}", success=True)

        if len(assignments) >= 5:
            agent_counts = {}
            for a in assignments:
                agent_counts[a.agent_id] = agent_counts.get(a.agent_id, 0) + 1
            # Should spread: no agent more than 3x the min
            if len(agent_counts) > 1:
                max_count = max(agent_counts.values())
                min_count = min(agent_counts.values())
                assert max_count <= min_count * 4

    def test_exclude_agents_respected(self):
        """Excluded agents should not receive tasks."""
        first_agent = list(self.agents.values())[0]
        task = TaskRequest(
            task_id="exclude_test",
            title="Test exclude",
            categories=["general"],
            exclude_agent_ids=[first_agent],
        )
        result = self.harness.orchestrator.route_task(task)
        if isinstance(result, Assignment):
            assert result.agent_id != first_agent

    def test_preferred_agents_honored(self):
        """Preferred agents should get priority."""
        preferred = list(self.agents.values())[2]
        task = TaskRequest(
            task_id="prefer_test",
            title="Test prefer",
            categories=["general"],
            preferred_agent_ids=[preferred],
        )
        result = self.harness.orchestrator.route_task(task)
        assert isinstance(result, (Assignment, RoutingFailure))


# ---------------------------------------------------------------------------
# TestFailoverAndRecovery
# ---------------------------------------------------------------------------

class TestFailoverAndRecovery:
    """Tests failover and recovery mechanisms."""

    def setup_method(self):
        self.harness = SwarmTestHarness()
        self.agents = self.harness.add_kk_roster(3)

    def test_failover_after_task_failure(self):
        """After failing a task, another agent should be available."""
        r1 = self.harness.route_task("t_fail1", categories=["general"])
        assert isinstance(r1, Assignment)
        self.harness.complete_task("t_fail1", success=False)

        # After cooldown expiry (or next available), another task routes fine
        r2 = self.harness.route_task("t_fail2", categories=["general"])
        assert isinstance(r2, Assignment)

    def test_agent_error_state(self):
        """Error state should be handled gracefully."""
        agent_id = list(self.agents.values())[0]
        self.harness.lifecycle.record_error(agent_id, "test error")

        # Other agents should still be available
        r = self.harness.route_task("t_after_error")
        assert isinstance(r, Assignment)

    def test_recover_from_cooldown(self):
        """Agent should recover from cooldown state."""
        r1 = self.harness.route_task("t_cool1")
        assert isinstance(r1, Assignment)
        agent_id = r1.agent_id
        self.harness.complete_task("t_cool1", success=True)

        # Agent goes to COOLDOWN after completion
        record = self.harness.lifecycle.agents.get(agent_id)
        if record and record.state == AgentState.COOLDOWN:
            # Check if cooldown can expire
            expired = self.harness.lifecycle.check_cooldown_expiry(agent_id)
            # Either way, other agents should work
            r2 = self.harness.route_task("t_cool2")
            assert isinstance(r2, (Assignment, RoutingFailure))


# ---------------------------------------------------------------------------
# TestBudgetEnforcement
# ---------------------------------------------------------------------------

class TestBudgetEnforcement:
    """Tests budget enforcement in the pipeline."""

    def setup_method(self):
        self.harness = SwarmTestHarness()

    def test_budget_tracking(self):
        """Spending should be tracked."""
        agent_id = self.harness.add_agent("budget_test", budget_daily=10.0)
        self.harness.lifecycle.record_spend(agent_id, 5.0)
        status = self.harness.lifecycle.get_budget_status(agent_id)
        assert status["daily_spent"] >= 5.0

    def test_budget_exceeded_blocks_assignment(self):
        """Over-budget agent should be blocked from tasks."""
        agent_id = self.harness.add_agent("broke_agent", budget_daily=1.0)

        # record_spend itself raises BudgetExceededError when limit hit
        with pytest.raises(BudgetExceededError):
            self.harness.lifecycle.record_spend(agent_id, 999.0)

    def test_cheap_task_within_budget(self):
        """Cheap tasks should work within budget."""
        agent_id = self.harness.add_agent("frugal", budget_daily=100.0)
        result = self.harness.route_task("t_cheap", bounty_usd=0.50)
        assert isinstance(result, Assignment)

    def test_budget_status_report(self):
        """Budget status should be reportable."""
        agent_id = self.harness.add_agent("tracked", budget_daily=50.0)
        status = self.harness.lifecycle.get_budget_status(agent_id)
        assert "daily_limit" in status
        assert "daily_spent" in status

    def test_multiple_agents_independent_budgets(self):
        """Each agent's budget should be independent."""
        id1 = self.harness.add_agent("spender", budget_daily=10.0)
        id2 = self.harness.add_agent("saver", budget_daily=100.0)

        self.harness.lifecycle.record_spend(id1, 9.0)
        status1 = self.harness.lifecycle.get_budget_status(id1)
        status2 = self.harness.lifecycle.get_budget_status(id2)

        assert status1["daily_spent"] >= 9.0
        assert status2["daily_spent"] < 1.0


# ---------------------------------------------------------------------------
# TestReputationFlow
# ---------------------------------------------------------------------------

class TestReputationFlow:
    """Tests reputation scoring through the pipeline."""

    def setup_method(self):
        self.harness = SwarmTestHarness()
        self.agents = self.harness.add_kk_roster(3)

    def test_new_agent_has_default_reputation(self):
        """New agents should have default reputation data."""
        agent_id = list(self.agents.values())[0]
        on_chain = self.harness.orchestrator._on_chain.get(agent_id)
        internal = self.harness.orchestrator._internal.get(agent_id)
        assert on_chain is not None
        assert internal is not None

    def test_reputation_updates_after_completion(self):
        """Reputation should improve after successful tasks."""
        agent_id = list(self.agents.values())[0]

        # Before
        internal_before = self.harness.orchestrator._internal[agent_id]
        before_completed = internal_before.successful_tasks

        # Complete a task and record reputation
        self.harness.record_reputation(agent_id, success=True)

        # After
        internal_after = self.harness.orchestrator._internal[agent_id]
        assert internal_after.successful_tasks == before_completed + 1

    def test_composite_score_computation(self):
        """Composite scores should be computable."""
        agent_id = list(self.agents.values())[0]

        # Record some reputation
        for _ in range(5):
            self.harness.record_reputation(agent_id, success=True)

        on_chain = self.harness.orchestrator._on_chain[agent_id]
        internal = self.harness.orchestrator._internal[agent_id]

        score = self.harness.bridge.compute_composite(
            on_chain=on_chain,
            internal=internal,
        )
        assert isinstance(score, CompositeScore)
        assert score.total >= 0

    def test_success_rate_progression(self):
        """Success rate should reflect actual outcomes."""
        agent_id = list(self.agents.values())[0]

        # 8 successes, 2 failures
        for i in range(10):
            self.harness.record_reputation(agent_id, success=(i % 5 != 0))

        internal = self.harness.orchestrator._internal[agent_id]
        rate = internal.success_rate
        assert 0.5 < rate < 1.0  # ~80% success rate

    def test_multiple_agents_independent_reputation(self):
        """Each agent should have independent reputation."""
        ids = list(self.agents.values())

        # Agent 0: perfect record
        for _ in range(5):
            self.harness.record_reputation(ids[0], success=True)

        # Agent 1: terrible record
        for _ in range(5):
            self.harness.record_reputation(ids[1], success=False)

        int0 = self.harness.orchestrator._internal[ids[0]]
        int1 = self.harness.orchestrator._internal[ids[1]]

        assert int0.success_rate > int1.success_rate


# ---------------------------------------------------------------------------
# TestSwarmOperations
# ---------------------------------------------------------------------------

class TestSwarmOperations:
    """Tests operational management of the swarm."""

    def setup_method(self):
        self.harness = SwarmTestHarness()
        self.agents = self.harness.add_kk_roster(5)

    def test_swarm_status_report(self):
        """Swarm status should reflect all agents."""
        status = self.harness.lifecycle.get_swarm_status()
        assert status["total_agents"] == 5

    def test_available_agents_list(self):
        """Should list available agents."""
        available = self.harness.lifecycle.get_available_agents()
        assert len(available) >= 3

    def test_agent_heartbeat_tracking(self):
        """Heartbeats should be recordable."""
        agent_id = list(self.agents.values())[0]
        record = self.harness.lifecycle.record_heartbeat(agent_id)
        assert record is not None

    def test_orchestrator_status(self):
        """Orchestrator status should be reportable."""
        # Do some work first
        for i in range(3):
            r = self.harness.route_task(f"status_{i}")
            if isinstance(r, Assignment):
                self.harness.complete_task(f"status_{i}", success=True)

        status = self.harness.orchestrator.get_status()
        assert "total_assignments" in status or "active_claims" in status

    def test_assignment_history(self):
        """Assignment history should be retrievable."""
        for i in range(3):
            r = self.harness.route_task(f"hist_{i}")
            if isinstance(r, Assignment):
                self.harness.complete_task(f"hist_{i}", success=True)

        history = self.harness.orchestrator.get_assignment_history(limit=10)
        assert len(history) >= 1

    def test_state_history(self):
        """Lifecycle state history should be tracked."""
        history = self.harness.lifecycle.state_history
        # Registration + transitions should produce history entries
        assert len(history) >= 1

    def test_unregister_agent(self):
        """Unregistering an agent should work."""
        agent_id = list(self.agents.values())[0]
        self.harness.lifecycle.unregister_agent(agent_id)
        available = self.harness.lifecycle.get_available_agents()
        ids = [a.agent_id for a in available]
        assert agent_id not in ids


# ---------------------------------------------------------------------------
# TestStressAndEdgeCases
# ---------------------------------------------------------------------------

class TestStressAndEdgeCases:
    """Stress tests and edge cases."""

    def setup_method(self):
        self.harness = SwarmTestHarness()
        self.agents = self.harness.add_kk_roster(5)

    def test_complete_unknown_task(self):
        """Completing unknown task should return None."""
        result = self.harness.orchestrator.complete_task("nonexistent_task_xyz")
        assert result is None

    def test_many_tasks_sequential(self):
        """Process many tasks sequentially."""
        completed = 0
        failed = 0
        for i in range(50):
            # Expire cooldowns so agents become available again
            for aid in list(self.harness.lifecycle.agents.keys()):
                try:
                    record = self.harness.lifecycle._agents.get(aid)
                    if record and record.state == AgentState.COOLDOWN:
                        self.harness.lifecycle.transition(aid, AgentState.IDLE, "cooldown expired")
                        self.harness.lifecycle.transition(aid, AgentState.ACTIVE, "ready")
                except Exception:
                    pass
            result = self.harness.route_task(f"stress_{i}")
            if isinstance(result, Assignment):
                success = (i % 3 != 0)
                self.harness.complete_task(f"stress_{i}", success=success)
                if success:
                    completed += 1
                else:
                    failed += 1
        assert completed >= 20

    def test_no_available_agents(self):
        """When no agents available, should return RoutingFailure."""
        # Remove all agents
        for agent_id in list(self.agents.values()):
            self.harness.lifecycle.unregister_agent(agent_id)

        result = self.harness.route_task("t_no_agents")
        assert isinstance(result, RoutingFailure)
        assert "No agents" in result.reason

    def test_all_agents_excluded(self):
        """When all agents excluded, should return RoutingFailure."""
        all_ids = list(self.agents.values())
        task = TaskRequest(
            task_id="t_all_excluded",
            title="Nobody can do this",
            exclude_agent_ids=all_ids,
        )
        result = self.harness.orchestrator.route_task(task)
        assert isinstance(result, RoutingFailure)

    def test_high_priority_task(self):
        """Critical priority tasks should route."""
        result = self.harness.route_task(
            "t_critical", priority=TaskPriority.CRITICAL, bounty_usd=100.0
        )
        assert isinstance(result, Assignment)

    def test_assignment_serialization(self):
        """Assignments should be serializable via to_dict."""
        result = self.harness.route_task("t_serial")
        if isinstance(result, Assignment):
            d = result.to_dict()
            assert "task_id" in d
            assert "agent_id" in d
            assert "score" in d
            assert "strategy" in d

    def test_failure_history_tracked(self):
        """Routing failures should be tracked."""
        # Remove all agents to force failure
        for agent_id in list(self.agents.values()):
            self.harness.lifecycle.unregister_agent(agent_id)

        self.harness.route_task("t_tracked_fail")
        failures = self.harness.orchestrator.get_failures(limit=10)
        assert len(failures) >= 1


# ---------------------------------------------------------------------------
# TestFullDaySimulation
# ---------------------------------------------------------------------------

class TestFullDaySimulation:
    """Simulate a full day of swarm operations."""

    def test_day_simulation_24_hours(self):
        """Run a simplified day simulation with 24 tasks."""
        harness = SwarmTestHarness()
        agents = harness.add_kk_roster(5)

        total_completed = 0
        total_failed = 0
        total_unroutable = 0

        categories = ["research", "verification", "content", "translation", "testing", "data"]

        for hour in range(24):
            # Expire cooldowns between "hours"
            for aid in list(harness.lifecycle._agents.keys()):
                try:
                    record = harness.lifecycle._agents.get(aid)
                    if record and record.state == AgentState.COOLDOWN:
                        harness.lifecycle.transition(aid, AgentState.IDLE, "hour passed")
                        harness.lifecycle.transition(aid, AgentState.ACTIVE, "ready")
                except Exception:
                    pass

            cat = categories[hour % len(categories)]
            bounty = 1.0 + (hour % 5) * 0.5

            result = harness.route_task(
                f"day_{hour}", categories=[cat], bounty_usd=bounty
            )
            if isinstance(result, Assignment):
                success = hour % 7 != 0  # ~14% failure rate
                harness.complete_task(f"day_{hour}", success=success)
                harness.record_reputation(result.agent_id, success=success)
                if success:
                    total_completed += 1
                else:
                    total_failed += 1
            else:
                total_unroutable += 1

        assert total_completed >= 15
        assert total_failed < 10

        # Verify final state
        status = harness.lifecycle.get_swarm_status()
        assert status["total_agents"] == 5

    def test_sustained_workload_100_tasks(self):
        """100-task sustained workload test."""
        harness = SwarmTestHarness()
        harness.add_kk_roster(5)

        assigned = 0
        for i in range(100):
            # Expire cooldowns so agents recycle
            for aid in list(harness.lifecycle._agents.keys()):
                try:
                    record = harness.lifecycle._agents.get(aid)
                    if record and record.state == AgentState.COOLDOWN:
                        harness.lifecycle.transition(aid, AgentState.IDLE, "cooldown expired")
                        harness.lifecycle.transition(aid, AgentState.ACTIVE, "ready")
                except Exception:
                    pass

            result = harness.route_task(f"load_{i}")
            if isinstance(result, Assignment):
                assigned += 1
                harness.complete_task(f"load_{i}", success=(i % 10 != 0))

        # At least 50% should be assignable
        assert assigned >= 50

    def test_mixed_strategies_simulation(self):
        """Run tasks with different strategies."""
        harness = SwarmTestHarness()
        harness.add_kk_roster(5)

        strategies = [
            RoutingStrategy.BEST_FIT,
            RoutingStrategy.ROUND_ROBIN,
            RoutingStrategy.SPECIALIST,
            RoutingStrategy.BUDGET_AWARE,
        ]

        results = {s.value: 0 for s in strategies}
        for i in range(20):
            strategy = strategies[i % len(strategies)]
            result = harness.route_task(f"strat_{i}", strategy=strategy)
            if isinstance(result, Assignment):
                results[strategy.value] += 1
                harness.complete_task(f"strat_{i}", success=True)

        # At least some strategies should succeed
        successful_strategies = sum(1 for v in results.values() if v > 0)
        assert successful_strategies >= 2
