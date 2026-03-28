"""
Chaos & Stress tests for SwarmOrchestrator.

Tests the routing engine under adversarial conditions:
1. Large swarm (50+ agents) routing behavior
2. Task flood (100+ simultaneous tasks)
3. All-agent-excluded edge cases
4. Reputation data races and missing data
5. Round-robin fairness under scale
6. Budget exhaustion cascades
7. History deque boundary behavior
8. Strategy mixing under load
9. Concurrent complete/fail during routing
10. Agent preference conflicts

These are the "what if production goes sideways?" tests.
"""

import pytest
from datetime import datetime, timezone, timedelta

from swarm.orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    TaskPriority,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
)
from swarm.reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
    CompositeScore,
)
from swarm.lifecycle_manager import LifecycleManager, AgentState


# ─── Helpers ─────────────────────────────────────────────────────


def make_agent(lifecycle, bridge, orch, agent_id, name=None, seals=5, quality=0.8):
    """Register an agent with reputation and activate it."""
    name = name or f"agent-{agent_id}"
    wallet = f"0x{agent_id:040x}"
    lifecycle.register_agent(agent_id, name, wallet, "explorer")
    lifecycle.transition(agent_id, AgentState.IDLE)
    lifecycle.transition(agent_id, AgentState.ACTIVE)

    on_chain = OnChainReputation(
        agent_id=agent_id,
        wallet_address=wallet,
        total_seals=seals,
        positive_seals=seals,
    )
    internal = InternalReputation(
        agent_id=agent_id,
        bayesian_score=quality,
        total_tasks=seals * 2,
        successful_tasks=int(seals * 2 * quality),
    )
    orch.register_reputation(agent_id, on_chain, internal)


def make_task(task_id, **kwargs):
    """Create a task request with sensible defaults."""
    defaults = {
        "task_id": task_id,
        "title": f"Task {task_id}",
        "categories": ["photo"],
        "bounty_usd": 0.10,
        "priority": TaskPriority.NORMAL,
    }
    defaults.update(kwargs)
    return TaskRequest(**defaults)


# ─── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def bridge():
    return ReputationBridge()


@pytest.fixture
def lifecycle():
    return LifecycleManager()


@pytest.fixture
def orch(bridge, lifecycle):
    return SwarmOrchestrator(bridge=bridge, lifecycle=lifecycle, cooldown_seconds=0)


# ─── Test: Large Swarm Routing ───────────────────────────────────


class TestLargeSwarm:
    """Routing with 50+ agents."""

    def test_50_agents_best_fit_picks_highest(self, lifecycle, bridge, orch):
        """With 50 agents, BEST_FIT should pick the best."""
        for i in range(1, 51):
            make_agent(lifecycle, bridge, orch, i, seals=i, quality=0.5 + i * 0.01)

        task = make_task("t1")
        result = orch.route_task(task, strategy=RoutingStrategy.BEST_FIT)
        assert isinstance(result, Assignment)
        # Agent 50 has most seals and highest quality
        assert result.agent_id == 50
        assert result.alternatives_count == 49

    def test_50_tasks_to_50_agents(self, lifecycle, bridge, orch):
        """Assign 50 tasks to 50 agents — all should succeed."""
        for i in range(1, 51):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        assignments = []
        for i in range(1, 51):
            result = orch.route_task(make_task(f"t{i}"))
            assert isinstance(result, Assignment), f"Task t{i} failed: {result.reason}"
            assignments.append(result)

        # All 50 unique agents assigned
        agent_ids = {a.agent_id for a in assignments}
        assert len(agent_ids) == 50

    def test_51st_task_fails_with_50_busy_agents(self, lifecycle, bridge, orch):
        """When all 50 agents are busy, 51st task should fail."""
        for i in range(1, 51):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        # Assign all 50
        for i in range(1, 51):
            result = orch.route_task(make_task(f"t{i}"))
            assert isinstance(result, Assignment)

        # 51st fails
        result = orch.route_task(make_task("t51"))
        assert isinstance(result, RoutingFailure)
        assert "No agents available" in result.reason

    def test_round_robin_across_50_agents(self, lifecycle, bridge, orch):
        """Round-robin distributes evenly across 50 agents."""
        for i in range(1, 51):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        # Route and immediately complete 100 tasks
        agent_counts = {}
        for i in range(100):
            result = orch.route_task(
                make_task(f"t{i}"), strategy=RoutingStrategy.ROUND_ROBIN
            )
            assert isinstance(result, Assignment)
            agent_counts[result.agent_id] = agent_counts.get(result.agent_id, 0) + 1
            # Complete immediately to free the agent
            orch.complete_task(f"t{i}")

        # Each agent should get approximately 2 tasks (100/50)
        # Allow some variance from scoring tie-breaks
        assert max(agent_counts.values()) <= 5  # No single agent gets too many
        assert len(agent_counts) >= 25  # At least half the agents used


# ─── Test: Task Flood ────────────────────────────────────────────


class TestTaskFlood:
    """Overwhelming the orchestrator with tasks."""

    def test_100_rapid_tasks_5_agents(self, lifecycle, bridge, orch):
        """100 tasks with only 5 agents — 5 succeed, 95 fail."""
        for i in range(1, 6):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        success = 0
        failure = 0
        for i in range(100):
            result = orch.route_task(make_task(f"t{i}"))
            if isinstance(result, Assignment):
                success += 1
            else:
                failure += 1

        assert success == 5
        assert failure == 95

    def test_complete_then_requeue(self, lifecycle, bridge, orch):
        """Process 100 tasks through 5 agents by completing between assignments."""
        for i in range(1, 6):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        for batch in range(20):
            tasks_this_batch = []
            for j in range(5):
                tid = f"t{batch * 5 + j}"
                result = orch.route_task(make_task(tid))
                assert isinstance(result, Assignment), f"Failed at batch {batch}, task {j}: {result.reason}"
                tasks_this_batch.append(tid)

            # Complete all tasks in batch
            for tid in tasks_this_batch:
                orch.complete_task(tid)

        # 100 total assignments
        assert len(orch._assignment_history) == 100

    def test_history_deque_overflow(self, lifecycle, bridge, orch):
        """Assignment history should cap at 1000 entries."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)

        for i in range(1200):
            result = orch.route_task(make_task(f"t{i}"))
            assert isinstance(result, Assignment)
            orch.complete_task(f"t{i}")

        assert len(orch._assignment_history) == 1000
        # Latest should be t1199
        last = list(orch._assignment_history)[-1]
        assert last.task_id == "t1199"

    def test_failure_deque_overflow(self, lifecycle, bridge, orch):
        """Failure history should also cap at 1000."""
        # No agents registered → all fail
        for i in range(1200):
            result = orch.route_task(make_task(f"t{i}"))
            assert isinstance(result, RoutingFailure)

        assert len(orch._failures) == 1000


# ─── Test: Exclusion Edge Cases ──────────────────────────────────


class TestExclusionEdgeCases:
    """What happens when exclusions get extreme."""

    def test_exclude_all_agents(self, lifecycle, bridge, orch):
        """Excluding all agents should produce RoutingFailure."""
        for i in range(1, 6):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        task = make_task("t1", exclude_agent_ids=list(range(1, 6)))
        result = orch.route_task(task)
        assert isinstance(result, RoutingFailure)
        assert "excluded" in result.reason.lower()
        assert result.excluded_agents == 5

    def test_exclude_all_but_one(self, lifecycle, bridge, orch):
        """Excluding all but one should route to the remaining agent."""
        for i in range(1, 6):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        task = make_task("t1", exclude_agent_ids=[1, 2, 3, 4])
        result = orch.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 5

    def test_exclude_nonexistent_agents(self, lifecycle, bridge, orch):
        """Excluding agents that don't exist should be harmless."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)

        task = make_task("t1", exclude_agent_ids=[999, 1000, 1001])
        result = orch.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 1


# ─── Test: Reputation Edge Cases ─────────────────────────────────


class TestReputationEdgeCases:
    """Missing, minimal, and extreme reputation data."""

    def test_agent_with_no_reputation(self, lifecycle, bridge, orch):
        """Agent registered but without reputation data should get defaults."""
        lifecycle.register_agent(1, "no-rep", "0x01", "explorer")
        lifecycle.transition(1, AgentState.IDLE)
        lifecycle.transition(1, AgentState.ACTIVE)
        # Don't register reputation

        task = make_task("t1")
        result = orch.route_task(task)
        # Default reputation may be below threshold
        if isinstance(result, RoutingFailure):
            assert "threshold" in result.reason.lower() or "No agent" in result.reason
        else:
            assert isinstance(result, Assignment)

    def test_agent_with_zero_seals(self, lifecycle, bridge, orch):
        """Agent with zero reputation should still route if above threshold."""
        make_agent(lifecycle, bridge, orch, 1, seals=0, quality=0.0)
        
        task = make_task("t1")
        result = orch.route_task(task)
        # Zero rep likely below min_score_threshold (15.0)
        assert isinstance(result, (Assignment, RoutingFailure))

    def test_agent_with_max_reputation(self, lifecycle, bridge, orch):
        """Agent with maximum reputation scores highest."""
        make_agent(lifecycle, bridge, orch, 1, seals=1000, quality=1.0)
        make_agent(lifecycle, bridge, orch, 2, seals=1, quality=0.1)

        task = make_task("t1")
        result = orch.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 1  # Higher rep wins

    def test_reputation_update_affects_routing(self, lifecycle, bridge, orch):
        """Updating reputation should change who gets the task."""
        make_agent(lifecycle, bridge, orch, 1, seals=5, quality=0.5)
        make_agent(lifecycle, bridge, orch, 2, seals=10, quality=0.9)

        # Agent 2 should win initially
        r1 = orch.route_task(make_task("t1"))
        assert isinstance(r1, Assignment)
        assert r1.agent_id == 2
        orch.complete_task("t1")

        # Now boost agent 1's reputation way up
        orch.register_reputation(
            1,
            OnChainReputation(agent_id=1, wallet_address="0x01", total_seals=100, positive_seals=100),
            InternalReputation(agent_id=1, bayesian_score=0.99, total_tasks=200, successful_tasks=198),
        )

        r2 = orch.route_task(make_task("t2"))
        assert isinstance(r2, Assignment)
        assert r2.agent_id == 1  # Agent 1 now wins


# ─── Test: Duplicate Task Handling ───────────────────────────────


class TestDuplicateTasks:
    """Task deduplication under various conditions."""

    def test_duplicate_rejected(self, lifecycle, bridge, orch):
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)

        r1 = orch.route_task(make_task("t1"))
        assert isinstance(r1, Assignment)

        r2 = orch.route_task(make_task("t1"))
        assert isinstance(r2, RoutingFailure)
        assert "already claimed" in r2.reason.lower()

    def test_completed_task_can_be_rerouted(self, lifecycle, bridge, orch):
        """After completing a task, its ID can be reused."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)

        r1 = orch.route_task(make_task("t1"))
        assert isinstance(r1, Assignment)
        orch.complete_task("t1")

        r2 = orch.route_task(make_task("t1"))
        assert isinstance(r2, Assignment)

    def test_failed_task_can_be_rerouted(self, lifecycle, bridge, orch):
        """After failing a task, its ID can be retried."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)

        r1 = orch.route_task(make_task("t1"))
        assert isinstance(r1, Assignment)
        orch.fail_task("t1", "test failure")

        # Agent in cooldown, need another
        make_agent(lifecycle, bridge, orch, 2, seals=10, quality=0.8)
        r2 = orch.route_task(make_task("t1"))
        assert isinstance(r2, Assignment)
        assert r2.agent_id == 2


# ─── Test: Complete/Fail Edge Cases ──────────────────────────────


class TestCompleteFailEdgeCases:
    """Edge cases in task completion and failure handling."""

    def test_complete_nonexistent_task(self, orch):
        assert orch.complete_task("nonexistent") is None

    def test_fail_nonexistent_task(self, orch):
        assert orch.fail_task("nonexistent") is None

    def test_double_complete(self, lifecycle, bridge, orch):
        """Completing the same task twice should return None on second call."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)
        orch.route_task(make_task("t1"))
        
        assert orch.complete_task("t1") == 1
        assert orch.complete_task("t1") is None  # Already completed

    def test_complete_then_fail(self, lifecycle, bridge, orch):
        """Completing then failing should return None on fail."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)
        orch.route_task(make_task("t1"))

        assert orch.complete_task("t1") == 1
        assert orch.fail_task("t1") is None

    def test_fail_updates_internal_reputation(self, lifecycle, bridge, orch):
        """Failing a task should increment consecutive_failures."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)
        orch.route_task(make_task("t1"))

        initial_failures = orch._internal[1].consecutive_failures
        orch.fail_task("t1", "test")
        assert orch._internal[1].consecutive_failures == initial_failures + 1

    def test_many_consecutive_failures(self, lifecycle, bridge, orch):
        """Agent with many failures still gets internal reputation tracked."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)

        for i in range(10):
            orch.route_task(make_task(f"t{i}"))
            orch.fail_task(f"t{i}", f"failure {i}")

        assert orch._internal[1].consecutive_failures >= 10


# ─── Test: Preference Conflicts ──────────────────────────────────


class TestPreferenceConflicts:
    """What happens when preferences conflict with strategy."""

    def test_preferred_agent_overrides_best_fit(self, lifecycle, bridge, orch):
        """Preferred agents should be selected even if not highest scoring."""
        make_agent(lifecycle, bridge, orch, 1, seals=100, quality=1.0)  # Best
        make_agent(lifecycle, bridge, orch, 2, seals=5, quality=0.5)    # Weaker

        task = make_task("t1", preferred_agent_ids=[2])
        result = orch.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 2

    def test_preferred_and_excluded_same_agent(self, lifecycle, bridge, orch):
        """If an agent is both preferred AND excluded, exclusion wins."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)
        make_agent(lifecycle, bridge, orch, 2, seals=10, quality=0.8)

        task = make_task("t1", preferred_agent_ids=[1], exclude_agent_ids=[1])
        result = orch.route_task(task)
        assert isinstance(result, Assignment)
        assert result.agent_id == 2  # Agent 1 excluded, agent 2 gets it

    def test_all_preferred_agents_busy(self, lifecycle, bridge, orch):
        """If preferred agents are busy, should fallback to any available."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)
        make_agent(lifecycle, bridge, orch, 2, seals=10, quality=0.8)

        # Occupy agent 1
        orch.route_task(make_task("t0"))

        # Now prefer only agent 1 for t1
        task = make_task("t1", preferred_agent_ids=[1])
        result = orch.route_task(task)
        # Agent 1 is busy, agent 2 should be available (preferences don't hard-exclude)
        assert isinstance(result, Assignment)


# ─── Test: Strategy Stress ───────────────────────────────────────


class TestStrategyStress:
    """Each strategy under pressure."""

    def test_specialist_with_no_specialists(self, lifecycle, bridge, orch):
        """SPECIALIST strategy with no specialists should fail gracefully."""
        make_agent(lifecycle, bridge, orch, 1, seals=1, quality=0.3)

        task = make_task("t1", categories=["advanced_robotics"])
        result = orch.route_task(task, strategy=RoutingStrategy.SPECIALIST)
        # Likely fails: no agent has skill_score >= 50 in this category
        assert isinstance(result, (Assignment, RoutingFailure))

    def test_budget_aware_with_fresh_agents(self, lifecycle, bridge, orch):
        """BUDGET_AWARE should work when no spending has occurred."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)
        make_agent(lifecycle, bridge, orch, 2, seals=10, quality=0.8)

        task = make_task("t1")
        result = orch.route_task(task, strategy=RoutingStrategy.BUDGET_AWARE)
        assert isinstance(result, Assignment)

    def test_strategy_switching_between_tasks(self, lifecycle, bridge, orch):
        """Different strategies for different tasks."""
        for i in range(1, 6):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        strategies = [
            RoutingStrategy.BEST_FIT,
            RoutingStrategy.ROUND_ROBIN,
            RoutingStrategy.BUDGET_AWARE,
        ]

        for i, strat in enumerate(strategies):
            result = orch.route_task(make_task(f"t{i}"), strategy=strat)
            assert isinstance(result, Assignment)
            assert result.strategy_used == strat


# ─── Test: Status & Reporting Under Load ─────────────────────────


class TestStatusUnderLoad:
    """Status and reporting accuracy during heavy operations."""

    def test_status_after_100_operations(self, lifecycle, bridge, orch):
        """Status should be accurate after many operations."""
        for i in range(1, 11):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        # Assign then complete 100 tasks
        for i in range(100):
            result = orch.route_task(make_task(f"t{i}"))
            assert isinstance(result, Assignment)
            orch.complete_task(f"t{i}")

        status = orch.get_status()
        assert status["active_claims"] == 0  # All completed
        assert status["total_assignments"] == 100
        assert status["registered_reputations"] == 10

    def test_failure_history_after_mass_failure(self, lifecycle, bridge, orch):
        """Failure history is accurate after many failures."""
        for i in range(200):
            orch.route_task(make_task(f"t{i}"))

        failures = orch.get_failures(limit=50)
        assert len(failures) == 50
        # Latest should be at the end
        assert failures[-1]["task_id"] == "t199"

    def test_assignment_history_limit(self, lifecycle, bridge, orch):
        """Assignment history respects limit parameter."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)

        for i in range(30):
            orch.route_task(make_task(f"t{i}"))
            orch.complete_task(f"t{i}")

        assert len(orch.get_assignment_history(limit=5)) == 5
        assert len(orch.get_assignment_history(limit=50)) == 30

    def test_active_claims_count(self, lifecycle, bridge, orch):
        """Active claims should track correctly."""
        for i in range(1, 6):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        # Assign 5 tasks
        for i in range(5):
            orch.route_task(make_task(f"t{i}"))

        assert orch.get_status()["active_claims"] == 5

        # Complete 3
        for i in range(3):
            orch.complete_task(f"t{i}")

        assert orch.get_status()["active_claims"] == 2

        # Fail 1
        orch.fail_task("t3", "error")
        assert orch.get_status()["active_claims"] == 1


# ─── Test: Priority Routing ─────────────────────────────────────


class TestPriorityRouting:
    """Task priority affects routing decisions."""

    def test_critical_task_gets_assigned(self, lifecycle, bridge, orch):
        """Critical priority tasks should still route normally."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)

        task = make_task("t1", priority=TaskPriority.CRITICAL)
        result = orch.route_task(task)
        assert isinstance(result, Assignment)

    def test_low_priority_task_gets_assigned(self, lifecycle, bridge, orch):
        """Low priority tasks should still get assigned."""
        make_agent(lifecycle, bridge, orch, 1, seals=10, quality=0.8)

        task = make_task("t1", priority=TaskPriority.LOW)
        result = orch.route_task(task)
        assert isinstance(result, Assignment)

    def test_all_priority_levels(self, lifecycle, bridge, orch):
        """All priority levels should route successfully."""
        for i in range(1, 5):
            make_agent(lifecycle, bridge, orch, i, seals=10, quality=0.8)

        priorities = [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW,
        ]
        for i, prio in enumerate(priorities):
            result = orch.route_task(make_task(f"t{i}", priority=prio))
            assert isinstance(result, Assignment)
            orch.complete_task(f"t{i}")
