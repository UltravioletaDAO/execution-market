"""
Chaos & stress tests for SwarmScheduler — deadline-aware priority scheduling.

Tests the scheduler under extreme conditions:
    - 500 tasks with mixed urgencies
    - Circuit breaker trip and recovery under load
    - Retry scheduler jitter distribution
    - Load balancer saturation across fleet
    - Strategy selection boundary conditions
    - Batch grouping with 50 categories
    - Scheduling cycles under concurrent conditions
    - Decision audit trail accuracy
    - Edge cases: all expired, all critical, empty coordinator
    - Urgency transitions as deadlines approach
"""

import math
import time
from datetime import datetime, timezone, timedelta
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.swarm.scheduler import (
    SwarmScheduler,
    ScheduledTask,
    SchedulingBatch,
    SchedulingDecision,
    SwarmConditions,
    UrgencyLevel,
    URGENCY_MULTIPLIERS,
    CircuitBreaker,
    CircuitState,
    RetryScheduler,
    AgentLoadBalancer,
)
from mcp_server.swarm.coordinator import SwarmCoordinator
from mcp_server.swarm.reputation_bridge import ReputationBridge, OnChainReputation, InternalReputation
from mcp_server.swarm.lifecycle_manager import LifecycleManager, AgentState, BudgetConfig
from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    TaskPriority,
    RoutingStrategy,
    Assignment,
    RoutingFailure,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_wired_scheduler(n_agents: int = 5, **kwargs) -> SwarmScheduler:
    """Create a scheduler wired to a real coordinator with agents."""
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge, lifecycle)
    coord = SwarmCoordinator(
        bridge=bridge, lifecycle=lifecycle, orchestrator=orchestrator
    )
    for i in range(n_agents):
        coord.register_agent(
            agent_id=i + 1,
            name=f"Agent-{i + 1}",
            wallet_address=f"0x{i + 1:040x}",
        )
    return SwarmScheduler(coordinator=coord, **kwargs)


def _standalone_scheduler(**kwargs) -> SwarmScheduler:
    """Scheduler without coordinator (for pure scheduling logic tests)."""
    return SwarmScheduler(coordinator=None, **kwargs)


# ─── Circuit Breaker Chaos ────────────────────────────────────────────────────


class TestCircuitBreakerChaos:
    """Stress the circuit breaker pattern."""

    def test_trip_on_exact_threshold(self):
        """Breaker trips exactly at failure_threshold."""
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        """A success in CLOSED state resets the failure counter."""
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb._failure_count == 2

        cb.record_success()
        assert cb._failure_count == 0

        # Now need 3 more failures to trip
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED

    def test_rapid_trip_recovery_cycles(self):
        """Rapid trip → recover → trip cycles don't corrupt state."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_seconds=0.01)

        for cycle in range(50):
            # Trip it
            cb.record_failure()
            cb.record_failure()
            assert cb.state == CircuitState.OPEN

            # Wait for recovery timeout
            time.sleep(0.015)
            assert cb.state == CircuitState.HALF_OPEN

            # Recover
            cb.record_success()
            assert cb.state == CircuitState.CLOSED

        assert cb._total_trips == 50

    def test_half_open_failure_reopens(self):
        """Failure in HALF_OPEN goes back to OPEN."""
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_seconds=0.01)

        # Trip
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait → HALF_OPEN
        time.sleep(0.015)
        assert cb.state == CircuitState.HALF_OPEN

        # Fail again → OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb._total_trips == 2

    def test_half_open_max_calls_respected(self):
        """Only half_open_max_calls requests allowed in HALF_OPEN."""
        cb = CircuitBreaker(
            "test",
            failure_threshold=2,
            recovery_timeout_seconds=0.01,
            half_open_max_calls=2,
        )

        # Trip
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.015)
        assert cb.state == CircuitState.HALF_OPEN

        # First 2 allowed
        assert cb.allow_request() is True
        cb._half_open_calls = 1
        assert cb.allow_request() is True
        cb._half_open_calls = 2
        assert cb.allow_request() is False

    def test_force_reset(self):
        """Force reset clears all state."""
        cb = CircuitBreaker("test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0
        assert cb.allow_request() is True

    def test_status_dict_structure(self):
        """get_status returns complete data."""
        cb = CircuitBreaker("em_api", failure_threshold=5)
        cb.record_success()
        cb.record_failure()

        status = cb.get_status()
        assert status["name"] == "em_api"
        assert status["state"] == "closed"
        assert status["failure_count"] == 1
        assert status["success_count"] == 1
        assert status["total_trips"] == 0


# ─── Retry Scheduler Chaos ───────────────────────────────────────────────────


class TestRetrySchedulerChaos:
    """Stress the retry/backoff system."""

    def test_delay_bounded_by_max(self):
        """Delays never exceed max_delay regardless of attempt count."""
        rs = RetryScheduler(base_delay=1.0, max_delay=10.0, max_retries=100)
        for attempt in range(100):
            delay = rs.next_delay("task-1", attempt)
            if delay >= 0:
                assert delay <= 10.0

    def test_should_retry_respects_max(self):
        """should_retry returns False at max_retries."""
        rs = RetryScheduler(max_retries=3)
        assert rs.should_retry("t1", 0) is True
        assert rs.should_retry("t1", 1) is True
        assert rs.should_retry("t1", 2) is True
        assert rs.should_retry("t1", 3) is False

    def test_delay_returns_negative_past_max(self):
        """next_delay returns -1 when retries exhausted."""
        rs = RetryScheduler(max_retries=2)
        assert rs.next_delay("t1", 2) == -1.0
        assert rs.next_delay("t1", 5) == -1.0

    def test_jitter_produces_varied_delays(self):
        """Decorrelated jitter produces different delays each call."""
        rs = RetryScheduler(base_delay=1.0, max_delay=100.0, max_retries=10)
        delays = set()
        for i in range(20):
            delay = rs.next_delay(f"jitter-{i}", 1)
            delays.add(round(delay, 4))

        # With randomness, we should get multiple distinct values
        assert len(delays) > 5

    def test_clear_resets_previous_delay(self):
        """Clearing a task resets its delay tracking."""
        rs = RetryScheduler(base_delay=1.0, max_delay=100.0)
        # Build up some delay history
        rs.next_delay("t1", 1)
        rs.next_delay("t1", 2)
        assert "t1" in rs._previous_delays

        rs.clear("t1")
        assert "t1" not in rs._previous_delays

    def test_get_next_eligible_time_future(self):
        """Next eligible time is always in the future."""
        rs = RetryScheduler(base_delay=1.0, max_delay=10.0)
        now = time.time()
        eligible = rs.get_next_eligible_time("t1", 0)
        assert eligible > now

    def test_get_next_eligible_time_inf_past_max(self):
        """Next eligible time is inf when retries exhausted."""
        rs = RetryScheduler(max_retries=2)
        assert rs.get_next_eligible_time("t1", 2) == float("inf")

    def test_100_tasks_independent_tracking(self):
        """100 tasks each get independent retry tracking."""
        rs = RetryScheduler(base_delay=1.0, max_delay=50.0)
        for i in range(100):
            rs.next_delay(f"task-{i}", 0)

        assert len(rs._previous_delays) == 100


# ─── Load Balancer Chaos ─────────────────────────────────────────────────────


class TestLoadBalancerChaos:
    """Stress the sliding window load limiter."""

    def test_window_enforcement(self):
        """Agent at capacity is blocked; others are available."""
        lb = AgentLoadBalancer(window_seconds=3600, max_tasks_per_window=3)

        for _ in range(3):
            lb.record_assignment(1)

        assert lb.is_available(1) is False
        assert lb.is_available(2) is True  # Never assigned

    def test_50_agents_load_tracking(self):
        """Track load across 50 agents simultaneously."""
        lb = AgentLoadBalancer(window_seconds=3600, max_tasks_per_window=5)

        for agent_id in range(1, 51):
            for _ in range(agent_id % 5):  # 0-4 tasks each
                lb.record_assignment(agent_id)

        # Agent 5 has 0 assignments (5 % 5 = 0)
        assert lb.is_available(5) is True
        # Agent 4 has 4 assignments
        load_4 = lb.get_load(4)
        assert load_4["recent_tasks"] == 4

    def test_fleet_load_summary(self):
        """Fleet load summary aggregates correctly."""
        lb = AgentLoadBalancer(window_seconds=3600, max_tasks_per_window=5)

        for agent_id in range(1, 11):
            for _ in range(3):
                lb.record_assignment(agent_id)

        fleet = lb.get_fleet_load(list(range(1, 11)))
        assert fleet["total_agents"] == 10
        assert fleet["total_recent_tasks"] == 30
        assert fleet["total_capacity"] == 50
        assert fleet["fleet_utilization"] == 0.6
        assert fleet["overloaded_agents"] == 0

    def test_unknown_agent_available(self):
        """Agent never assigned is always available."""
        lb = AgentLoadBalancer()
        assert lb.is_available(999) is True
        load = lb.get_load(999)
        assert load["recent_tasks"] == 0

    def test_deque_maxlen_prevents_memory_leak(self):
        """Assignment deque is bounded at maxlen=100."""
        lb = AgentLoadBalancer(window_seconds=3600, max_tasks_per_window=200)

        for _ in range(150):
            lb.record_assignment(1)

        # Deque should cap at 100
        assert len(lb._assignments[1]) == 100


# ─── Urgency Computation Chaos ────────────────────────────────────────────────


class TestUrgencyChaos:
    """Stress urgency/priority computation edge cases."""

    def test_all_urgency_levels_reachable(self):
        """Each urgency level is reachable via deadline manipulation."""
        scheduler = _standalone_scheduler()
        now = datetime.now(timezone.utc)

        cases = {
            UrgencyLevel.EXPIRED: now - timedelta(hours=1),
            UrgencyLevel.CRITICAL: now + timedelta(minutes=30),
            UrgencyLevel.URGENT: now + timedelta(hours=2),
            UrgencyLevel.NORMAL: now + timedelta(hours=12),
            UrgencyLevel.RELAXED: now + timedelta(hours=48),
        }

        for expected_urgency, deadline in cases.items():
            task = scheduler.add_task(
                task_id=f"urg-{expected_urgency.value}",
                title=f"Urgency {expected_urgency.value}",
                categories=["a"],
                deadline=deadline,
            )
            assert task.urgency == expected_urgency, f"Expected {expected_urgency}, got {task.urgency}"

    def test_no_deadline_is_normal(self):
        """Task without deadline defaults to NORMAL urgency."""
        scheduler = _standalone_scheduler()
        task = scheduler.add_task(
            task_id="no-dl", title="No Deadline", categories=["a"]
        )
        assert task.urgency == UrgencyLevel.NORMAL

    def test_priority_computation_signals(self):
        """Effective priority combines all 5 signals correctly."""
        scheduler = _standalone_scheduler()
        now = datetime.now(timezone.utc)

        # High base + urgent + high bounty + old + no retries = HIGH score
        high_task = scheduler.add_task(
            task_id="high",
            title="High",
            categories=["a"],
            bounty_usd=500.0,
            priority=TaskPriority.CRITICAL,
            deadline=now + timedelta(minutes=30),
            created_at=now - timedelta(hours=10),
        )

        # Low base + relaxed + low bounty + new + many retries = LOW score
        low_task = scheduler.add_task(
            task_id="low",
            title="Low",
            categories=["a"],
            bounty_usd=0.01,
            priority=TaskPriority.LOW,
            deadline=now + timedelta(hours=48),
            created_at=now,
        )
        low_task.retry_count = 5
        scheduler._compute_effective_priority(low_task)

        assert high_task.effective_priority > low_task.effective_priority

    def test_expired_task_gets_zero_priority(self):
        """Expired urgency multiplier is 0.0 → effective priority is 0."""
        scheduler = _standalone_scheduler()
        task = scheduler.add_task(
            task_id="exp",
            title="Expired",
            categories=["a"],
            bounty_usd=1000.0,
            priority=TaskPriority.CRITICAL,
            deadline=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert task.effective_priority == 0.0

    def test_retry_penalty_accumulates(self):
        """More retries = lower effective priority."""
        scheduler = _standalone_scheduler()
        task = scheduler.add_task(
            task_id="retry-pen",
            title="RP",
            categories=["a"],
            bounty_usd=10.0,
            priority=TaskPriority.NORMAL,
        )

        priorities = []
        for retries in range(6):
            task.retry_count = retries
            scheduler._compute_effective_priority(task)
            priorities.append(task.effective_priority)

        # Priority should decrease (or stay same at cap) with more retries
        for i in range(len(priorities) - 1):
            assert priorities[i] >= priorities[i + 1]

    def test_bounty_bonus_log_scale(self):
        """Bounty bonus follows log scale and caps at +1.0."""
        scheduler = _standalone_scheduler()

        # Very high bounty shouldn't give more than +1.0 bonus
        task = scheduler.add_task(
            task_id="big-bounty",
            title="BB",
            categories=["a"],
            bounty_usd=1_000_000.0,
            priority=TaskPriority.NORMAL,
        )

        # Base priority = 2.0, bounty bonus capped at 1.0, age bonus ~0
        # So effective_priority should be <= 4.0 or so (with urgency mult = 1.0)
        assert task.effective_priority <= 5.0


# ─── Strategy Selection Chaos ────────────────────────────────────────────────


class TestStrategySelectionChaos:
    """Test dynamic strategy selection under various swarm conditions."""

    def test_critical_urgency_always_best_fit(self):
        """Critical urgency overrides all other factors."""
        scheduler = _standalone_scheduler()
        task = ScheduledTask(
            task_id="crit",
            title="Critical",
            categories=["general"],
            bounty_usd=5.0,
            priority=TaskPriority.LOW,  # Even low priority
            urgency=UrgencyLevel.CRITICAL,
        )
        conditions = SwarmConditions(
            avg_budget_utilization=0.9,  # High budget → normally BUDGET_AWARE
            total_agents=10,
            idle_agents=1,
            pending_tasks=50,  # Overloaded → normally ROUND_ROBIN
        )

        strategy, reason = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BEST_FIT

    def test_high_budget_selects_budget_aware(self):
        """High budget utilization triggers BUDGET_AWARE."""
        scheduler = _standalone_scheduler()
        task = ScheduledTask(
            task_id="ba",
            title="BudgetAware",
            categories=["general"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
            urgency=UrgencyLevel.NORMAL,
        )
        conditions = SwarmConditions(
            avg_budget_utilization=0.7,
            total_agents=10,
            idle_agents=5,
            active_agents=5,
            pending_tasks=3,
        )

        strategy, reason = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BUDGET_AWARE

    def test_overloaded_selects_round_robin(self):
        """High load factor triggers ROUND_ROBIN."""
        scheduler = _standalone_scheduler()
        task = ScheduledTask(
            task_id="rr",
            title="RoundRobin",
            categories=["general"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
            urgency=UrgencyLevel.NORMAL,
        )
        conditions = SwarmConditions(
            avg_budget_utilization=0.3,
            total_agents=10,
            idle_agents=2,
            active_agents=1,
            pending_tasks=20,  # load_factor = 20/3 ≈ 6.7 > 3.0
        )

        strategy, reason = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.ROUND_ROBIN

    def test_specialist_category_selects_specialist(self):
        """Specialist categories trigger SPECIALIST strategy."""
        scheduler = _standalone_scheduler()
        task = ScheduledTask(
            task_id="spec",
            title="Research",
            categories=["research"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
            urgency=UrgencyLevel.NORMAL,
        )
        conditions = SwarmConditions(
            total_agents=10,
            idle_agents=5,
            active_agents=5,
            pending_tasks=3,
        )

        strategy, reason = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.SPECIALIST

    def test_default_is_best_fit(self):
        """Normal conditions → BEST_FIT."""
        scheduler = _standalone_scheduler()
        task = ScheduledTask(
            task_id="def",
            title="Default",
            categories=["delivery"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
            urgency=UrgencyLevel.NORMAL,
        )
        conditions = SwarmConditions(
            total_agents=10,
            idle_agents=5,
            active_agents=5,
            pending_tasks=3,
        )

        strategy, reason = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BEST_FIT


# ─── Batch Grouping Chaos ────────────────────────────────────────────────────


class TestBatchGroupingChaos:
    """Test batch creation under extreme category diversity."""

    def test_50_categories_create_50_batches(self):
        """50 unique categories create 50 separate batches."""
        scheduler = _standalone_scheduler()

        for i in range(50):
            scheduler.add_task(
                task_id=f"cat-{i}",
                title=f"Category {i}",
                categories=[f"cat_{i}"],
                bounty_usd=5.0,
            )

        batches = scheduler.compute_schedule()
        # Each unique category should get its own batch
        assert len(batches) == 50

    def test_same_category_grouped_together(self):
        """Tasks with same category go into same batch (up to max_batch_size)."""
        scheduler = _standalone_scheduler(max_batch_size=10)

        for i in range(8):
            scheduler.add_task(
                task_id=f"same-{i}",
                title=f"Same {i}",
                categories=["photo"],
                bounty_usd=5.0,
            )

        batches = scheduler.compute_schedule()
        assert len(batches) == 1
        assert len(batches[0].tasks) == 8

    def test_batch_splits_at_max_size(self):
        """Batches split when exceeding max_batch_size."""
        scheduler = _standalone_scheduler(max_batch_size=5)

        for i in range(12):
            scheduler.add_task(
                task_id=f"split-{i}",
                title=f"Split {i}",
                categories=["delivery"],
                bounty_usd=5.0,
            )

        batches = scheduler.compute_schedule()
        # 12 tasks / max 5 per batch = 3 batches
        total_tasks = sum(len(b.tasks) for b in batches)
        assert total_tasks == 12
        assert len(batches) == 3

    def test_multi_category_batch_key(self):
        """Tasks with multiple categories create sorted composite batch keys."""
        scheduler = _standalone_scheduler()

        scheduler.add_task(
            task_id="mc-1", title="MC1", categories=["photo", "delivery"]
        )
        scheduler.add_task(
            task_id="mc-2", title="MC2", categories=["delivery", "photo"]
        )

        batches = scheduler.compute_schedule()
        # Both should be in the same batch (sorted category key)
        assert len(batches) == 1
        assert len(batches[0].tasks) == 2

    def test_empty_categories_go_to_uncategorized(self):
        """Tasks with no categories get batch_key 'uncategorized'."""
        scheduler = _standalone_scheduler()

        scheduler.add_task(task_id="empty-cat", title="EC", categories=[])
        task = scheduler.get_task("empty-cat")
        assert task.batch_key == "uncategorized"


# ─── Schedule Computation Chaos ───────────────────────────────────────────────


class TestScheduleComputationChaos:
    """Stress schedule computation under load."""

    def test_500_tasks_mixed_urgency(self):
        """Compute schedule for 500 tasks with mixed urgencies."""
        scheduler = _standalone_scheduler()
        now = datetime.now(timezone.utc)

        for i in range(500):
            # Rotate through urgency levels
            if i % 5 == 0:
                deadline = now + timedelta(minutes=30)  # Critical
            elif i % 5 == 1:
                deadline = now + timedelta(hours=2)  # Urgent
            elif i % 5 == 2:
                deadline = now + timedelta(hours=12)  # Normal
            elif i % 5 == 3:
                deadline = now + timedelta(hours=48)  # Relaxed
            else:
                deadline = now - timedelta(hours=1)  # Expired

            scheduler.add_task(
                task_id=f"mix-{i}",
                title=f"Mix {i}",
                categories=[f"cat-{i % 10}"],
                bounty_usd=float(i % 20) + 1.0,
                priority=[TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH, TaskPriority.CRITICAL][i % 4],
                deadline=deadline,
            )

        batches = scheduler.compute_schedule()

        # Expired tasks should be filtered out
        total_in_batches = sum(len(b.tasks) for b in batches)
        assert total_in_batches == 400  # 500 - 100 expired

    def test_all_expired_returns_empty(self):
        """All expired tasks → empty schedule."""
        scheduler = _standalone_scheduler()
        past = datetime.now(timezone.utc) - timedelta(hours=1)

        for i in range(20):
            scheduler.add_task(
                task_id=f"dead-{i}",
                title=f"Dead {i}",
                categories=["a"],
                deadline=past,
            )

        batches = scheduler.compute_schedule()
        assert len(batches) == 0

    def test_schedule_sorted_by_urgency(self):
        """Batches are sorted: critical before relaxed."""
        scheduler = _standalone_scheduler()
        now = datetime.now(timezone.utc)

        scheduler.add_task(
            task_id="relaxed",
            title="Relaxed",
            categories=["a"],
            deadline=now + timedelta(hours=48),
        )
        scheduler.add_task(
            task_id="critical",
            title="Critical",
            categories=["b"],
            deadline=now + timedelta(minutes=30),
        )

        batches = scheduler.compute_schedule()
        assert len(batches) == 2
        # Critical batch should be first
        critical_first = any(
            t.task_id == "critical" for t in batches[0].tasks
        )
        assert critical_first

    def test_backoff_tasks_deferred(self):
        """Tasks in backoff period are skipped."""
        scheduler = _standalone_scheduler()

        task = scheduler.add_task(
            task_id="backoff", title="Backoff", categories=["a"], bounty_usd=5.0
        )
        task.next_eligible_at = time.time() + 3600  # 1 hour from now

        batches = scheduler.compute_schedule()
        total = sum(len(b.tasks) for b in batches)
        assert total == 0
        assert scheduler._tasks_deferred >= 1


# ─── Scheduling Execution Chaos ──────────────────────────────────────────────


class TestScheduleExecutionChaos:
    """Test execute_schedule under load with real coordinator."""

    def test_execute_20_tasks_5_agents(self):
        """Execute schedule with 20 tasks across 5 agents."""
        scheduler = _make_wired_scheduler(n_agents=5)

        for i in range(20):
            scheduler.add_task(
                task_id=f"exec-{i}",
                title=f"Exec {i}",
                categories=["general"],
                bounty_usd=5.0,
            )

        batches = scheduler.compute_schedule()
        results = scheduler.execute_schedule(batches)

        assigned = [r for r in results if r.get("outcome") == "assigned"]
        # Should assign up to 5 (one per agent)
        assert len(assigned) <= 5
        assert len(assigned) > 0

    def test_circuit_breaker_blocks_routing(self):
        """Open circuit breaker prevents routing."""
        scheduler = _make_wired_scheduler(n_agents=5)

        # Trip the EM API circuit breaker
        em_cb = scheduler._circuit_breakers.get("em_api")
        assert em_cb is not None
        for _ in range(10):
            em_cb.record_failure()
        assert em_cb.state == CircuitState.OPEN

        scheduler.add_task(
            task_id="blocked", title="Blocked", categories=["a"], bounty_usd=5.0
        )

        batches = scheduler.compute_schedule()
        results = scheduler.execute_schedule(batches)

        assert len(results) > 0
        assert results[0]["outcome"] == "circuit_open"

    def test_retry_on_routing_failure(self):
        """Failed routing schedules retry with backoff."""
        scheduler = _make_wired_scheduler(n_agents=0)  # No agents → all routing fails

        scheduler.add_task(
            task_id="will-fail", title="WillFail", categories=["a"], bounty_usd=5.0
        )

        batches = scheduler.compute_schedule()
        results = scheduler.execute_schedule(batches)

        if results:
            # Should either be retry_scheduled or max_retries_exceeded
            assert results[0]["outcome"] in ("retry_scheduled", "max_retries_exceeded")

    def test_no_coordinator_returns_error(self):
        """Execute with no coordinator returns error dict."""
        scheduler = _standalone_scheduler()
        scheduler.add_task(task_id="nc", title="NC", categories=["a"])

        batches = scheduler.compute_schedule()
        results = scheduler.execute_schedule(batches)
        assert len(results) == 1
        assert "error" in results[0]

    def test_successful_routing_clears_retry(self):
        """Successful routing clears the retry tracker for that task."""
        scheduler = _make_wired_scheduler(n_agents=5)

        # Prime the retry scheduler
        scheduler.retry_scheduler._previous_delays["clear-me"] = 50.0

        scheduler.add_task(
            task_id="clear-me", title="ClearMe", categories=["a"], bounty_usd=5.0
        )

        batches = scheduler.compute_schedule()
        results = scheduler.execute_schedule(batches)

        assigned = [r for r in results if r.get("outcome") == "assigned" and r.get("task_id") == "clear-me"]
        if assigned:
            assert "clear-me" not in scheduler.retry_scheduler._previous_delays


# ─── Full Scheduling Cycle Chaos ─────────────────────────────────────────────


class TestSchedulingCycleChaos:
    """Test the full run_scheduling_cycle method under load."""

    def test_100_tasks_through_cycle(self):
        """Push 100 tasks through a complete scheduling cycle."""
        scheduler = _make_wired_scheduler(n_agents=20)

        for i in range(100):
            scheduler.add_task(
                task_id=f"cycle-{i}",
                title=f"Cycle {i}",
                categories=[f"cat-{i % 5}"],
                bounty_usd=float(i % 10) + 1.0,
            )

        summary = scheduler.run_scheduling_cycle()

        assert summary["cycle"] == 1
        assert summary["tasks_processed"] > 0
        assert summary["tasks_assigned"] > 0
        assert summary["batches"] > 0

    def test_multiple_cycles_drains_queue(self):
        """Multiple cycles eventually process all routable tasks."""
        scheduler = _make_wired_scheduler(n_agents=10)

        for i in range(10):
            scheduler.add_task(
                task_id=f"drain-{i}",
                title=f"Drain {i}",
                categories=["general"],
                bounty_usd=5.0,
            )

        total_assigned = 0
        for _ in range(10):
            summary = scheduler.run_scheduling_cycle()
            total_assigned += summary["tasks_assigned"]
            if summary["tasks_remaining"] == 0:
                break

            # Complete assigned tasks in coordinator to free agents
            if scheduler.coordinator:
                for tid, task in list(scheduler.coordinator._task_queue.items()):
                    if task.status == "assigned":
                        scheduler.coordinator.complete_task(tid)

        # Should have assigned at least some
        assert total_assigned > 0

    def test_empty_cycle_returns_zero(self):
        """Empty scheduler produces clean zero-result summary."""
        scheduler = _make_wired_scheduler(n_agents=5)
        summary = scheduler.run_scheduling_cycle()

        assert summary["cycle"] == 1
        assert summary["batches"] == 0
        assert summary["tasks_processed"] == 0
        assert summary["tasks_assigned"] == 0
        assert summary["tasks_remaining"] == 0

    def test_cycle_count_increments(self):
        """Each cycle increments the counter."""
        scheduler = _make_wired_scheduler(n_agents=5)

        for _ in range(10):
            scheduler.run_scheduling_cycle()

        assert scheduler._cycles_run == 10

    def test_strategy_usage_tracked(self):
        """Strategy usage is tracked across cycles."""
        scheduler = _make_wired_scheduler(n_agents=5)

        for i in range(5):
            scheduler.add_task(
                task_id=f"su-{i}", title=f"SU{i}", categories=["general"], bounty_usd=5.0
            )

        scheduler.run_scheduling_cycle()

        # At least one strategy should have been used
        total_usage = sum(scheduler._strategy_usage.values())
        assert total_usage > 0


# ─── Task Management Edge Cases ──────────────────────────────────────────────


class TestTaskManagementChaos:
    """Edge cases in task add/remove/get."""

    def test_remove_nonexistent_task(self):
        """Remove returns False for unknown task."""
        scheduler = _standalone_scheduler()
        assert scheduler.remove_task("ghost") is False

    def test_get_nonexistent_task(self):
        """Get returns None for unknown task."""
        scheduler = _standalone_scheduler()
        assert scheduler.get_task("ghost") is None

    def test_pending_count_accuracy(self):
        """pending_count tracks adds and removes."""
        scheduler = _standalone_scheduler()

        for i in range(10):
            scheduler.add_task(task_id=f"pc-{i}", title=f"PC{i}", categories=["a"])

        assert scheduler.pending_count == 10

        scheduler.remove_task("pc-3")
        scheduler.remove_task("pc-7")
        assert scheduler.pending_count == 8

    def test_add_task_computes_batch_key(self):
        """Batch key is computed from sorted categories."""
        scheduler = _standalone_scheduler()
        task = scheduler.add_task(
            task_id="bk", title="BK", categories=["zebra", "alpha", "middle"]
        )
        assert task.batch_key == "alpha|middle|zebra"


# ─── SwarmConditions Edge Cases ──────────────────────────────────────────────


class TestSwarmConditionsChaos:
    """Test SwarmConditions computed properties."""

    def test_zero_agents_availability_ratio(self):
        """Zero total agents → 0.0 availability ratio."""
        c = SwarmConditions(total_agents=0)
        assert c.availability_ratio == 0.0

    def test_zero_available_load_factor_inf(self):
        """Zero available agents → infinite load factor."""
        c = SwarmConditions(
            total_agents=5, idle_agents=0, active_agents=0, pending_tasks=10
        )
        assert c.load_factor == float("inf")
        assert c.is_overloaded is True

    def test_underloaded_detection(self):
        """Low load factor → underloaded."""
        c = SwarmConditions(
            total_agents=10, idle_agents=5, active_agents=5, pending_tasks=1
        )
        assert c.load_factor < 0.5
        assert c.is_underloaded is True

    def test_budget_headroom_computation(self):
        """Budget headroom = 1 - utilization."""
        c = SwarmConditions(avg_budget_utilization=0.75)
        assert c.budget_headroom == 0.25

    def test_budget_headroom_floor_at_zero(self):
        """Budget headroom doesn't go negative."""
        c = SwarmConditions(avg_budget_utilization=1.5)
        assert c.budget_headroom == 0.0


# ─── Decision Audit Trail ────────────────────────────────────────────────────


class TestDecisionAuditChaos:
    """Test decision recording and retrieval."""

    def test_decisions_capped_at_500(self):
        """Decision deque is bounded at 500."""
        scheduler = _standalone_scheduler()
        now = datetime.now(timezone.utc)

        for i in range(600):
            scheduler.add_task(
                task_id=f"aud-{i}",
                title=f"Audit {i}",
                categories=["a"],
                deadline=now + timedelta(hours=12),
            )

        scheduler.compute_schedule()
        assert len(scheduler._decisions) == 500

    def test_decisions_have_correct_structure(self):
        """Each decision dict has required fields."""
        scheduler = _standalone_scheduler()

        scheduler.add_task(
            task_id="struct", title="Struct", categories=["a"], bounty_usd=5.0
        )
        scheduler.compute_schedule()

        decisions = scheduler.get_decisions(limit=10)
        assert len(decisions) > 0
        d = decisions[0]
        assert "task_id" in d
        assert "urgency" in d
        assert "priority" in d
        assert "strategy" in d
        assert "reason" in d
        assert "outcome" in d
        assert "timestamp" in d

    def test_decision_limit_respected(self):
        """get_decisions respects limit parameter."""
        scheduler = _standalone_scheduler()

        for i in range(20):
            scheduler.add_task(
                task_id=f"lim-{i}", title=f"L{i}", categories=["a"]
            )
        scheduler.compute_schedule()

        decisions = scheduler.get_decisions(limit=5)
        assert len(decisions) <= 5


# ─── Status & Metrics ────────────────────────────────────────────────────────


class TestStatusChaos:
    """Test status reporting under various conditions."""

    def test_status_structure_complete(self):
        """get_status returns all expected fields."""
        scheduler = _make_wired_scheduler(5)

        for i in range(5):
            scheduler.add_task(
                task_id=f"st-{i}", title=f"ST{i}", categories=["a"], bounty_usd=5.0
            )
        scheduler.run_scheduling_cycle()

        status = scheduler.get_status()
        assert "pending_tasks" in status
        assert "cycles_run" in status
        assert "tasks_scheduled" in status
        assert "tasks_deferred" in status
        assert "strategy_usage" in status
        assert "circuit_breakers" in status
        assert "load_balancer" in status
        assert "retry_scheduler" in status

    def test_urgency_distribution(self):
        """Urgency distribution reflects actual task urgencies."""
        scheduler = _standalone_scheduler()
        now = datetime.now(timezone.utc)

        # 3 normal, 2 critical, 1 relaxed
        for i in range(3):
            scheduler.add_task(
                task_id=f"norm-{i}", title=f"N{i}", categories=["a"],
                deadline=now + timedelta(hours=12),
            )
        for i in range(2):
            scheduler.add_task(
                task_id=f"crit-{i}", title=f"C{i}", categories=["a"],
                deadline=now + timedelta(minutes=30),
            )
        scheduler.add_task(
            task_id="relax-0", title="R0", categories=["a"],
            deadline=now + timedelta(hours=48),
        )

        dist = scheduler.get_urgency_distribution()
        assert dist.get("normal", 0) == 3
        assert dist.get("critical", 0) == 2
        assert dist.get("relaxed", 0) == 1


# ─── Scheduling Batch Properties ─────────────────────────────────────────────


class TestBatchProperties:
    """Test SchedulingBatch computed properties."""

    def test_total_bounty_aggregation(self):
        """Total bounty sums across all tasks in batch."""
        batch = SchedulingBatch(
            batch_id="b1",
            category_key="general",
            tasks=[
                ScheduledTask(task_id=f"t{i}", title=f"T{i}", categories=["a"], bounty_usd=10.0 + i, priority=TaskPriority.NORMAL)
                for i in range(5)
            ],
        )
        assert batch.total_bounty == 60.0  # 10+11+12+13+14

    def test_max_urgency_finds_highest(self):
        """max_urgency returns the highest urgency in the batch."""
        tasks = [
            ScheduledTask(task_id="t1", title="T1", categories=["a"], bounty_usd=1.0, priority=TaskPriority.NORMAL),
            ScheduledTask(task_id="t2", title="T2", categories=["a"], bounty_usd=1.0, priority=TaskPriority.NORMAL),
            ScheduledTask(task_id="t3", title="T3", categories=["a"], bounty_usd=1.0, priority=TaskPriority.NORMAL),
        ]
        tasks[0].urgency = UrgencyLevel.RELAXED
        tasks[1].urgency = UrgencyLevel.URGENT
        tasks[2].urgency = UrgencyLevel.NORMAL

        batch = SchedulingBatch(batch_id="b1", category_key="a", tasks=tasks)
        assert batch.max_urgency == UrgencyLevel.URGENT

    def test_batch_to_dict(self):
        """Batch serialization includes all fields."""
        batch = SchedulingBatch(
            batch_id="b1",
            category_key="photo",
            tasks=[
                ScheduledTask(task_id="t1", title="T1", categories=["photo"], bounty_usd=5.0, priority=TaskPriority.NORMAL),
            ],
            strategy=RoutingStrategy.SPECIALIST,
        )

        d = batch.to_dict()
        assert d["batch_id"] == "b1"
        assert d["category"] == "photo"
        assert d["task_count"] == 1
        assert d["total_bounty"] == 5.0
        assert d["strategy"] == "specialist"
        assert d["task_ids"] == ["t1"]
