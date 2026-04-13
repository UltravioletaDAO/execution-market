"""
Tests for SwarmScheduler — Deadline-Aware Priority Scheduling
=============================================================

Coverage:
- Urgency computation (deadline → urgency level)
- Effective priority scoring (multi-signal)
- Dynamic strategy selection (conditions → strategy)
- Batch optimization (grouping, ordering)
- Circuit breaker (state machine, trips, recovery)
- Retry scheduler (backoff, jitter, max retries)
- Load balancer (sliding window, capacity)
- Full scheduling cycles (compute + execute)
- Edge cases (empty pool, all expired, no agents)
"""

import time
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock


from mcp_server.swarm.scheduler import (
    SwarmScheduler,
    ScheduledTask,
    SchedulingBatch,
    SwarmConditions,
    UrgencyLevel,
    CircuitBreaker,
    CircuitState,
    RetryScheduler,
    AgentLoadBalancer,
)
from mcp_server.swarm.orchestrator import (
    RoutingStrategy,
    TaskPriority,
)
from mcp_server.swarm.lifecycle_manager import AgentState
from mcp_server.swarm.reputation_bridge import ReputationBridge
from mcp_server.swarm.lifecycle_manager import LifecycleManager
from mcp_server.swarm.orchestrator import SwarmOrchestrator


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────


def make_scheduler(**kwargs):
    """Create a standalone scheduler (no coordinator)."""
    return SwarmScheduler(coordinator=None, **kwargs)


def make_coordinator_with_agents(n_agents=5, activate=True):
    """Create a coordinator with N registered agents."""
    from mcp_server.swarm.reputation_bridge import OnChainReputation, InternalReputation

    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge, lifecycle, min_score_threshold=0.0)

    # Mock coordinator
    coordinator = MagicMock()
    coordinator.lifecycle = lifecycle
    coordinator.orchestrator = orchestrator
    coordinator.bridge = bridge

    for i in range(n_agents):
        agent_id = i + 1
        wallet = f"0x{'0' * 39}{agent_id}"
        lifecycle.register_agent(
            agent_id=agent_id,
            name=f"agent_{agent_id}",
            wallet_address=wallet,
        )
        lifecycle.transition(agent_id, AgentState.IDLE)
        if activate:
            lifecycle.transition(agent_id, AgentState.ACTIVE)

        # Register reputation data so orchestrator can score agents
        orchestrator.register_reputation(
            agent_id=agent_id,
            on_chain=OnChainReputation(agent_id=agent_id, wallet_address=wallet),
            internal=InternalReputation(
                agent_id=agent_id,
                bayesian_score=0.7,
                total_tasks=10,
                successful_tasks=8,
            ),
        )

    return coordinator


# ──────────────────────────────────────────────────────────────
# Urgency Computation
# ──────────────────────────────────────────────────────────────


class TestUrgencyComputation:
    """Test deadline → urgency level classification."""

    def test_no_deadline_is_normal(self):
        scheduler = make_scheduler()
        task = scheduler.add_task("t1", "No deadline", ["general"])
        assert task.urgency == UrgencyLevel.NORMAL

    def test_expired_deadline(self):
        scheduler = make_scheduler()
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        task = scheduler.add_task("t1", "Expired", ["general"], deadline=past)
        assert task.urgency == UrgencyLevel.EXPIRED

    def test_critical_deadline_under_1h(self):
        scheduler = make_scheduler()
        soon = datetime.now(timezone.utc) + timedelta(minutes=30)
        task = scheduler.add_task("t1", "Critical", ["general"], deadline=soon)
        assert task.urgency == UrgencyLevel.CRITICAL

    def test_urgent_deadline_1_to_4h(self):
        scheduler = make_scheduler()
        deadline = datetime.now(timezone.utc) + timedelta(hours=2)
        task = scheduler.add_task("t1", "Urgent", ["general"], deadline=deadline)
        assert task.urgency == UrgencyLevel.URGENT

    def test_normal_deadline_4_to_24h(self):
        scheduler = make_scheduler()
        deadline = datetime.now(timezone.utc) + timedelta(hours=12)
        task = scheduler.add_task("t1", "Normal", ["general"], deadline=deadline)
        assert task.urgency == UrgencyLevel.NORMAL

    def test_relaxed_deadline_over_24h(self):
        scheduler = make_scheduler()
        deadline = datetime.now(timezone.utc) + timedelta(days=3)
        task = scheduler.add_task("t1", "Relaxed", ["general"], deadline=deadline)
        assert task.urgency == UrgencyLevel.RELAXED

    def test_urgency_boundary_exactly_1h(self):
        """At exactly 1h, should be URGENT (not CRITICAL)."""
        scheduler = make_scheduler()
        # Add a small buffer since computation takes time
        deadline = datetime.now(timezone.utc) + timedelta(hours=1, seconds=5)
        task = scheduler.add_task("t1", "Boundary", ["general"], deadline=deadline)
        assert task.urgency == UrgencyLevel.URGENT

    def test_urgency_boundary_exactly_4h(self):
        """At exactly 4h, should be NORMAL (not URGENT)."""
        scheduler = make_scheduler()
        deadline = datetime.now(timezone.utc) + timedelta(hours=4, seconds=5)
        task = scheduler.add_task("t1", "Boundary", ["general"], deadline=deadline)
        assert task.urgency == UrgencyLevel.NORMAL

    def test_naive_deadline_treated_as_utc(self):
        """Deadlines without timezone are treated as UTC."""
        scheduler = make_scheduler()
        naive = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
        task = scheduler.add_task("t1", "Naive", ["general"], deadline=naive)
        assert task.urgency == UrgencyLevel.CRITICAL


# ──────────────────────────────────────────────────────────────
# Effective Priority Scoring
# ──────────────────────────────────────────────────────────────


class TestEffectivePriority:
    """Test multi-signal priority computation."""

    def test_critical_priority_highest(self):
        scheduler = make_scheduler()
        c = scheduler.add_task("c", "Critical", ["x"], priority=TaskPriority.CRITICAL)
        h = scheduler.add_task("h", "High", ["x"], priority=TaskPriority.HIGH)
        n = scheduler.add_task("n", "Normal", ["x"], priority=TaskPriority.NORMAL)
        l = scheduler.add_task("l", "Low", ["x"], priority=TaskPriority.LOW)
        assert c.effective_priority > h.effective_priority
        assert h.effective_priority > n.effective_priority
        assert n.effective_priority > l.effective_priority

    def test_urgency_multiplier_boosts_priority(self):
        scheduler = make_scheduler()
        urgent_deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
        urgent = scheduler.add_task(
            "u", "Urgent", ["x"], priority=TaskPriority.NORMAL, deadline=urgent_deadline
        )
        relaxed_deadline = datetime.now(timezone.utc) + timedelta(days=7)
        relaxed = scheduler.add_task(
            "r",
            "Relaxed",
            ["x"],
            priority=TaskPriority.NORMAL,
            deadline=relaxed_deadline,
        )
        assert urgent.effective_priority > relaxed.effective_priority

    def test_bounty_bonus(self):
        """Higher bounty tasks get priority boost."""
        scheduler = make_scheduler()
        rich = scheduler.add_task("r", "Rich", ["x"], bounty_usd=100.0)
        poor = scheduler.add_task("p", "Poor", ["x"], bounty_usd=0.01)
        assert rich.effective_priority > poor.effective_priority

    def test_expired_task_has_zero_priority(self):
        scheduler = make_scheduler()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        expired = scheduler.add_task("e", "Expired", ["x"], deadline=past)
        assert expired.effective_priority == 0.0

    def test_retry_penalty_reduces_priority(self):
        scheduler = make_scheduler()
        task = scheduler.add_task("t", "Retry test", ["x"])
        original_priority = task.effective_priority

        task.retry_count = 3
        scheduler._compute_effective_priority(task)
        assert task.effective_priority < original_priority


# ──────────────────────────────────────────────────────────────
# Dynamic Strategy Selection
# ──────────────────────────────────────────────────────────────


class TestStrategySelection:
    """Test dynamic strategy selection based on conditions."""

    def test_urgent_task_gets_best_fit(self):
        scheduler = make_scheduler()
        task = ScheduledTask(
            task_id="t1",
            title="Urgent",
            categories=["photo"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
            urgency=UrgencyLevel.CRITICAL,
        )
        conditions = SwarmConditions(total_agents=10, idle_agents=5)
        strategy, reason = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BEST_FIT
        assert "urgent" in reason

    def test_critical_priority_gets_best_fit(self):
        scheduler = make_scheduler()
        task = ScheduledTask(
            task_id="t1",
            title="Critical",
            categories=["photo"],
            bounty_usd=50.0,
            priority=TaskPriority.CRITICAL,
        )
        conditions = SwarmConditions(total_agents=10, idle_agents=5)
        strategy, _ = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BEST_FIT

    def test_high_budget_gets_budget_aware(self):
        scheduler = make_scheduler()
        task = ScheduledTask(
            task_id="t1",
            title="Normal",
            categories=["photo"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
        )
        conditions = SwarmConditions(
            total_agents=10,
            idle_agents=5,
            avg_budget_utilization=0.75,  # 75% used
        )
        strategy, reason = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BUDGET_AWARE
        assert "budget" in reason.lower()

    def test_overloaded_gets_round_robin(self):
        scheduler = make_scheduler()
        task = ScheduledTask(
            task_id="t1",
            title="Normal",
            categories=["photo"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
        )
        # 2 available agents, 10 pending tasks → load factor 5.0
        conditions = SwarmConditions(
            total_agents=10,
            idle_agents=1,
            active_agents=1,
            working_agents=8,
            pending_tasks=10,
        )
        strategy, reason = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.ROUND_ROBIN
        assert "overloaded" in reason.lower()

    def test_specialist_categories_get_specialist(self):
        scheduler = make_scheduler()
        task = ScheduledTask(
            task_id="t1",
            title="Code task",
            categories=["code_execution"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
        )
        conditions = SwarmConditions(total_agents=10, idle_agents=5)
        strategy, reason = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.SPECIALIST
        assert "specialist" in reason.lower()

    def test_default_gets_best_fit(self):
        scheduler = make_scheduler()
        task = ScheduledTask(
            task_id="t1",
            title="Normal",
            categories=["simple_action"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
        )
        conditions = SwarmConditions(total_agents=10, idle_agents=5)
        strategy, _ = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BEST_FIT

    def test_urgency_overrides_budget(self):
        """Urgent tasks use BEST_FIT even with high budget usage."""
        scheduler = make_scheduler()
        task = ScheduledTask(
            task_id="t1",
            title="Urgent rich",
            categories=["photo"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
            urgency=UrgencyLevel.URGENT,
        )
        conditions = SwarmConditions(
            total_agents=10,
            idle_agents=5,
            avg_budget_utilization=0.9,
        )
        strategy, _ = scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BEST_FIT


# ──────────────────────────────────────────────────────────────
# Circuit Breaker
# ──────────────────────────────────────────────────────────────


class TestCircuitBreaker:
    """Test circuit breaker state machine."""

    def test_starts_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_trip_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()  # Reset
        cb.record_failure()  # Back to 1
        assert cb.state == CircuitState.CLOSED

    def test_reset_forces_closed(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_total_trips_counter(self):
        cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout_seconds=0.01)
        cb.record_failure()
        assert cb._total_trips == 1
        time.sleep(0.02)
        # Must check state first to trigger OPEN → HALF_OPEN transition
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()  # half_open → open
        assert cb._total_trips == 2

    def test_status_report(self):
        cb = CircuitBreaker("test_svc", failure_threshold=3)
        cb.record_failure()
        status = cb.get_status()
        assert status["name"] == "test_svc"
        assert status["state"] == "closed"
        assert status["failure_count"] == 1
        assert status["total_trips"] == 0


# ──────────────────────────────────────────────────────────────
# Retry Scheduler
# ──────────────────────────────────────────────────────────────


class TestRetryScheduler:
    """Test exponential backoff with jitter."""

    def test_delay_positive(self):
        rs = RetryScheduler(base_delay=1.0, max_delay=100.0)
        delay = rs.next_delay("t1", 0)
        assert delay > 0
        assert delay <= 100.0

    def test_delay_increases_on_average(self):
        """Over many samples, later attempts should have higher average delay."""
        RetryScheduler(base_delay=1.0, max_delay=1000.0)
        early_delays = []
        late_delays = []
        for _ in range(100):
            rs_local = RetryScheduler(base_delay=1.0, max_delay=1000.0)
            early_delays.append(rs_local.next_delay("t1", 0))
            rs_local.next_delay("t1", 1)
            rs_local.next_delay("t1", 2)
            late_delays.append(rs_local.next_delay("t1", 3))
        # Average late delay should be higher (with high probability)
        assert sum(late_delays) / len(late_delays) > sum(early_delays) / len(
            early_delays
        )

    def test_delay_capped(self):
        rs = RetryScheduler(base_delay=1.0, max_delay=5.0, max_retries=100)
        # Pump up the previous delay
        for i in range(20):
            rs.next_delay("t1", i)
        delay = rs.next_delay("t1", 21)
        assert delay <= 5.0

    def test_max_retries_returns_negative(self):
        rs = RetryScheduler(max_retries=2)
        result = rs.next_delay("t1", 5)
        assert result == -1.0

    def test_clear_resets_state(self):
        rs = RetryScheduler()
        rs.next_delay("t1", 0)
        rs.next_delay("t1", 1)
        rs.clear("t1")
        # After clear, first delay should be back to base range
        delay = rs.next_delay("t1", 0)
        assert delay <= rs.base_delay * 3  # Upper bound of first jitter

    def test_eligible_time_in_future(self):
        rs = RetryScheduler(base_delay=10.0)
        eligible = rs.get_next_eligible_time("t1", 0)
        assert eligible > time.time()
        assert eligible < time.time() + 100  # Within reasonable range


# ──────────────────────────────────────────────────────────────
# Load Balancer
# ──────────────────────────────────────────────────────────────


class TestAgentLoadBalancer:
    """Test sliding window load limiting."""

    def test_empty_agent_available(self):
        lb = AgentLoadBalancer(max_tasks_per_window=3)
        assert lb.is_available(1) is True

    def test_under_limit_available(self):
        lb = AgentLoadBalancer(max_tasks_per_window=3)
        lb.record_assignment(1)
        lb.record_assignment(1)
        assert lb.is_available(1) is True

    def test_at_limit_unavailable(self):
        lb = AgentLoadBalancer(max_tasks_per_window=3)
        lb.record_assignment(1)
        lb.record_assignment(1)
        lb.record_assignment(1)
        assert lb.is_available(1) is False

    def test_window_expiry_frees_capacity(self):
        lb = AgentLoadBalancer(window_seconds=1, max_tasks_per_window=1)
        lb.record_assignment(1)
        assert lb.is_available(1) is False
        time.sleep(1.1)
        assert lb.is_available(1) is True


# ──────────────────────────────────────────────────────────────
# SwarmConditions
# ──────────────────────────────────────────────────────────────


class TestSwarmConditions:
    def test_availability_ratio_zero_agents(self):
        c = SwarmConditions(total_agents=0)
        assert c.availability_ratio == 0.0

    def test_load_factor(self):
        c = SwarmConditions(
            total_agents=10,
            idle_agents=2,
            active_agents=3,
            pending_tasks=15,
        )
        assert c.load_factor == 3.0

    def test_is_overloaded(self):
        c = SwarmConditions(
            total_agents=10,
            idle_agents=1,
            active_agents=1,
            pending_tasks=10,
        )
        assert c.is_overloaded is True

    def test_is_underloaded(self):
        c = SwarmConditions(
            total_agents=10,
            idle_agents=5,
            active_agents=5,
            pending_tasks=2,
        )
        assert c.is_underloaded is True


# ──────────────────────────────────────────────────────────────
# Batch Computation
# ──────────────────────────────────────────────────────────────


class TestBatchComputation:
    """Test schedule computation and batch grouping."""

    def test_empty_pool_returns_empty(self):
        scheduler = make_scheduler()
        batches = scheduler.compute_schedule()
        assert batches == []

    def test_single_task_single_batch(self):
        scheduler = make_scheduler()
        scheduler.add_task("t1", "Photo task", ["photo"], bounty_usd=5.0)
        batches = scheduler.compute_schedule()
        assert len(batches) == 1
        assert len(batches[0].tasks) == 1

    def test_same_category_grouped(self):
        scheduler = make_scheduler(max_batch_size=10)
        scheduler.add_task("t1", "Photo 1", ["photo"], bounty_usd=5.0)
        scheduler.add_task("t2", "Photo 2", ["photo"], bounty_usd=3.0)
        scheduler.add_task("t3", "Photo 3", ["photo"], bounty_usd=7.0)
        batches = scheduler.compute_schedule()
        # All same category → one batch
        assert len(batches) == 1
        assert len(batches[0].tasks) == 3

    def test_different_categories_separate_batches(self):
        scheduler = make_scheduler()
        scheduler.add_task("t1", "Photo", ["photo"], bounty_usd=5.0)
        scheduler.add_task("t2", "Code", ["code_execution"], bounty_usd=10.0)
        batches = scheduler.compute_schedule()
        assert len(batches) == 2

    def test_batch_split_at_max_size(self):
        scheduler = make_scheduler(max_batch_size=2)
        scheduler.add_task("t1", "P1", ["photo"], bounty_usd=5.0)
        scheduler.add_task("t2", "P2", ["photo"], bounty_usd=5.0)
        scheduler.add_task("t3", "P3", ["photo"], bounty_usd=5.0)
        batches = scheduler.compute_schedule()
        # 3 tasks, max 2 per batch → 2 batches
        assert len(batches) == 2
        total_tasks = sum(len(b.tasks) for b in batches)
        assert total_tasks == 3

    def test_expired_tasks_filtered_out(self):
        scheduler = make_scheduler()
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        scheduler.add_task("expired", "Old", ["x"], deadline=past)
        scheduler.add_task("active", "New", ["x"])
        batches = scheduler.compute_schedule()
        assert len(batches) == 1
        assert batches[0].tasks[0].task_id == "active"

    def test_critical_batch_first(self):
        """Critical urgency batches should come before normal."""
        scheduler = make_scheduler()
        scheduler.add_task("normal", "Normal", ["photo"], bounty_usd=5.0)
        critical_deadline = datetime.now(timezone.utc) + timedelta(minutes=20)
        scheduler.add_task(
            "critical",
            "Critical",
            ["code_execution"],
            bounty_usd=5.0,
            deadline=critical_deadline,
        )
        batches = scheduler.compute_schedule()
        # Critical batch should be first
        assert any(t.task_id == "critical" for t in batches[0].tasks)

    def test_backoff_tasks_deferred(self):
        """Tasks in backoff are skipped."""
        scheduler = make_scheduler()
        task = scheduler.add_task("t1", "Deferred", ["x"])
        task.next_eligible_at = time.time() + 3600  # 1 hour from now
        batches = scheduler.compute_schedule()
        assert len(batches) == 0

    def test_scheduling_batch_to_dict(self):
        batch = SchedulingBatch(
            batch_id="b1",
            category_key="photo",
            tasks=[
                ScheduledTask("t1", "T1", ["photo"], 5.0, TaskPriority.NORMAL),
                ScheduledTask("t2", "T2", ["photo"], 3.0, TaskPriority.NORMAL),
            ],
            strategy=RoutingStrategy.BEST_FIT,
        )
        d = batch.to_dict()
        assert d["batch_id"] == "b1"
        assert d["task_count"] == 2
        assert d["total_bounty"] == 8.0
        assert d["strategy"] == "best_fit"
        assert "t1" in d["task_ids"]


# ──────────────────────────────────────────────────────────────
# Full Scheduling Cycle (with mock coordinator)
# ──────────────────────────────────────────────────────────────


class TestSchedulingCycle:
    """Test compute + execute cycle with a real orchestrator."""

    def test_cycle_assigns_task(self):
        coordinator = make_coordinator_with_agents(3)
        scheduler = SwarmScheduler(
            coordinator=coordinator, enable_circuit_breakers=False
        )
        scheduler.add_task("t1", "Photo task", ["photo"], bounty_usd=5.0)
        result = scheduler.run_scheduling_cycle()
        assert result["tasks_assigned"] == 1
        assert result["tasks_remaining"] == 0

    def test_cycle_assigns_multiple(self):
        coordinator = make_coordinator_with_agents(5)
        scheduler = SwarmScheduler(
            coordinator=coordinator, enable_circuit_breakers=False
        )
        for i in range(3):
            scheduler.add_task(f"t{i}", f"Task {i}", ["photo"], bounty_usd=2.0)
        result = scheduler.run_scheduling_cycle()
        assert result["tasks_assigned"] == 3

    def test_cycle_no_agents_fails(self):
        coordinator = make_coordinator_with_agents(0)
        scheduler = SwarmScheduler(
            coordinator=coordinator, enable_circuit_breakers=False
        )
        scheduler.add_task("t1", "No agents", ["photo"])
        result = scheduler.run_scheduling_cycle()
        assert result["tasks_assigned"] == 0
        assert result["tasks_failed"] >= 1

    def test_cycle_empty_pool(self):
        coordinator = make_coordinator_with_agents(3)
        scheduler = SwarmScheduler(coordinator=coordinator)
        result = scheduler.run_scheduling_cycle()
        assert result["tasks_assigned"] == 0
        assert result["batches"] == 0

    def test_retry_on_failure(self):
        """Failed tasks should get retry scheduled."""
        coordinator = make_coordinator_with_agents(0)  # No agents → failures
        scheduler = SwarmScheduler(
            coordinator=coordinator, enable_circuit_breakers=False
        )
        scheduler.add_task("t1", "Will fail", ["photo"])
        result = scheduler.run_scheduling_cycle()
        assert any(r.get("outcome") == "retry_scheduled" for r in result["results"])
        # Task should still be in pool
        assert scheduler.pending_count == 1

    def test_circuit_breaker_blocks_on_failures(self):
        """After enough failures, circuit breaker should block."""
        coordinator = make_coordinator_with_agents(0)  # No agents → failures
        scheduler = SwarmScheduler(
            coordinator=coordinator, enable_circuit_breakers=True
        )
        # Configure low threshold
        scheduler._circuit_breakers["em_api"] = CircuitBreaker(
            "em_api", failure_threshold=2
        )

        # Each task routes through the orchestrator (no EM API call in test),
        # but we manually trip the breaker for testing
        scheduler._circuit_breakers["em_api"].record_failure()
        scheduler._circuit_breakers["em_api"].record_failure()

        scheduler.add_task("t1", "Blocked", ["photo"])
        result = scheduler.run_scheduling_cycle()
        # Should be blocked by circuit breaker
        assert any(
            r.get("outcome") == "circuit_open" for r in result.get("results", [])
        )


# ──────────────────────────────────────────────────────────────
# Task Management
# ──────────────────────────────────────────────────────────────


class TestTaskManagement:
    def test_batch_key_from_categories(self):
        scheduler = make_scheduler()
        task = scheduler.add_task("t1", "Multi", ["code_execution", "research"])
        assert task.batch_key == "code_execution|research"

    def test_empty_categories_batch_key(self):
        scheduler = make_scheduler()
        task = scheduler.add_task("t1", "No cat", [])
        assert task.batch_key == "uncategorized"


# ──────────────────────────────────────────────────────────────
# Status & Metrics
# ──────────────────────────────────────────────────────────────


class TestStatusAndMetrics:
    def test_strategy_usage_tracking(self):
        coordinator = make_coordinator_with_agents(3)
        scheduler = SwarmScheduler(
            coordinator=coordinator, enable_circuit_breakers=False
        )
        scheduler.add_task("t1", "T1", ["simple_action"], bounty_usd=5.0)
        scheduler.run_scheduling_cycle()
        assert scheduler._tasks_scheduled >= 1
        assert sum(scheduler._strategy_usage.values()) >= 1


# ──────────────────────────────────────────────────────────────
# Swarm Conditions Assessment
# ──────────────────────────────────────────────────────────────


class TestConditionsAssessment:
    def test_conditions_with_coordinator(self):
        coordinator = make_coordinator_with_agents(5)
        scheduler = SwarmScheduler(coordinator=coordinator)
        conditions = scheduler._assess_swarm_conditions()
        assert conditions.total_agents == 5
        assert conditions.active_agents == 5

    def test_conditions_without_coordinator(self):
        scheduler = make_scheduler()
        conditions = scheduler._assess_swarm_conditions()
        assert conditions.total_agents == 0


# ──────────────────────────────────────────────────────────────
# Edge Cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_all_tasks_expired(self):
        scheduler = make_scheduler()
        past = datetime.now(timezone.utc) - timedelta(hours=2)
        for i in range(5):
            scheduler.add_task(f"t{i}", f"Expired {i}", ["x"], deadline=past)
        batches = scheduler.compute_schedule()
        assert len(batches) == 0

    def test_all_tasks_in_backoff(self):
        scheduler = make_scheduler()
        future = time.time() + 3600
        for i in range(3):
            task = scheduler.add_task(f"t{i}", f"Backoff {i}", ["x"])
            task.next_eligible_at = future
        batches = scheduler.compute_schedule()
        assert len(batches) == 0

    def test_no_coordinator_execute(self):
        scheduler = make_scheduler()
        scheduler.add_task("t1", "T1", ["x"])
        batches = scheduler.compute_schedule()
        results = scheduler.execute_schedule(batches)
        assert results == [{"error": "No coordinator configured"}]

    def test_large_task_pool(self):
        """Handle 100+ tasks efficiently."""
        scheduler = make_scheduler(max_batch_size=10)
        for i in range(100):
            scheduler.add_task(
                f"t{i}",
                f"Task {i}",
                [["photo", "code_execution", "research"][i % 3]],
                bounty_usd=float(i),
                priority=[TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH][
                    i % 3
                ],
            )
        batches = scheduler.compute_schedule()
        total = sum(len(b.tasks) for b in batches)
        assert total == 100
        # Should have multiple batches due to categories
        assert len(batches) >= 3

    def test_mixed_urgencies_ordered_correctly(self):
        """Tasks with different urgencies should be ordered properly in batches."""
        scheduler = make_scheduler(max_batch_size=100)
        # All different categories to get separate batches
        scheduler.add_task(
            "relaxed",
            "Relaxed",
            ["cat_a"],
            deadline=datetime.now(timezone.utc) + timedelta(days=5),
        )
        scheduler.add_task(
            "critical",
            "Critical",
            ["cat_b"],
            deadline=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        scheduler.add_task("normal", "Normal", ["cat_c"])

        batches = scheduler.compute_schedule()
        # Critical batch should come first
        assert batches[0].tasks[0].task_id == "critical"
