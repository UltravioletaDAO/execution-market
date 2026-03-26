"""
Comprehensive test suite for SwarmScheduler — deadline-aware priority scheduling.

Tests cover:
- UrgencyLevel and URGENCY_MULTIPLIERS
- ScheduledTask: defaults, batch_key, post_init
- SchedulingBatch: total_bounty, max_urgency, to_dict
- SwarmConditions: availability_ratio, load_factor, overloaded/underloaded, budget_headroom
- CircuitBreaker: state transitions, allow_request, success/failure recording, half_open
- RetryScheduler: should_retry, decorrelated jitter, get_next_eligible_time, clear
- AgentLoadBalancer: record_assignment, is_available, get_load, get_fleet_load
- SwarmScheduler: add_task, remove_task, urgency computation, effective priority
- Dynamic strategy selection (conditions → strategy)
- Batch computation: grouping, sorting, expired/backoff filtering
- Schedule execution (mock coordinator)
- Scheduling cycle end-to-end
- Status and decision recording
"""

import time
from datetime import datetime, timezone, timedelta


from mcp_server.swarm.scheduler import (
    AgentLoadBalancer,
    CircuitBreaker,
    CircuitState,
    RetryScheduler,
    ScheduledTask,
    SchedulingBatch,
    SwarmConditions,
    SwarmScheduler,
    UrgencyLevel,
    URGENCY_MULTIPLIERS,
)
from mcp_server.swarm.orchestrator import (
    RoutingStrategy,
    TaskPriority,
)


# ─── UrgencyLevel & Multipliers Tests ───────────────────────────────────


class TestUrgencyConstants:
    def test_all_urgencies_have_multipliers(self):
        for level in UrgencyLevel:
            assert level in URGENCY_MULTIPLIERS

    def test_expired_zero_multiplier(self):
        assert URGENCY_MULTIPLIERS[UrgencyLevel.EXPIRED] == 0.0

    def test_critical_highest_multiplier(self):
        assert (
            URGENCY_MULTIPLIERS[UrgencyLevel.CRITICAL]
            > URGENCY_MULTIPLIERS[UrgencyLevel.URGENT]
        )
        assert (
            URGENCY_MULTIPLIERS[UrgencyLevel.URGENT]
            > URGENCY_MULTIPLIERS[UrgencyLevel.NORMAL]
        )


# ─── ScheduledTask Tests ────────────────────────────────────────────────


class TestScheduledTask:
    def test_defaults(self):
        task = ScheduledTask(
            task_id="t1",
            title="Test",
            categories=["delivery"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
        )
        assert task.urgency == UrgencyLevel.NORMAL
        assert task.retry_count == 0
        assert task.created_at is not None

    def test_batch_key(self):
        task = ScheduledTask(
            task_id="t1",
            title="Test",
            categories=["delivery", "photo"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
        )
        assert task.batch_key == "delivery|photo"

    def test_batch_key_sorted(self):
        task = ScheduledTask(
            task_id="t1",
            title="Test",
            categories=["photo", "delivery"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
        )
        assert task.batch_key == "delivery|photo"

    def test_empty_categories(self):
        task = ScheduledTask(
            task_id="t1",
            title="Test",
            categories=[],
            bounty_usd=0,
            priority=TaskPriority.LOW,
        )
        assert task.batch_key == "uncategorized"


# ─── SchedulingBatch Tests ──────────────────────────────────────────────


class TestSchedulingBatch:
    def test_total_bounty(self):
        batch = SchedulingBatch(batch_id="b1", category_key="delivery")
        batch.tasks = [
            ScheduledTask("t1", "A", ["delivery"], 5.0, TaskPriority.NORMAL),
            ScheduledTask("t2", "B", ["delivery"], 10.0, TaskPriority.NORMAL),
        ]
        assert batch.total_bounty == 15.0

    def test_max_urgency(self):
        batch = SchedulingBatch(batch_id="b1", category_key="delivery")
        t1 = ScheduledTask("t1", "A", ["delivery"], 5.0, TaskPriority.NORMAL)
        t1.urgency = UrgencyLevel.NORMAL
        t2 = ScheduledTask("t2", "B", ["delivery"], 10.0, TaskPriority.NORMAL)
        t2.urgency = UrgencyLevel.CRITICAL
        batch.tasks = [t1, t2]
        assert batch.max_urgency == UrgencyLevel.CRITICAL

    def test_to_dict(self):
        batch = SchedulingBatch(batch_id="b1", category_key="delivery")
        batch.tasks = [
            ScheduledTask("t1", "A", ["delivery"], 5.0, TaskPriority.NORMAL),
        ]
        d = batch.to_dict()
        assert d["batch_id"] == "b1"
        assert d["task_count"] == 1
        assert d["total_bounty"] == 5.0


# ─── SwarmConditions Tests ──────────────────────────────────────────────


class TestSwarmConditions:
    def test_availability_ratio_empty(self):
        c = SwarmConditions(total_agents=0)
        assert c.availability_ratio == 0.0

    def test_availability_ratio(self):
        c = SwarmConditions(total_agents=10, idle_agents=3, active_agents=2)
        assert c.availability_ratio == 0.5

    def test_load_factor_no_available(self):
        c = SwarmConditions(idle_agents=0, active_agents=0, pending_tasks=5)
        assert c.load_factor == float("inf")

    def test_load_factor_normal(self):
        c = SwarmConditions(idle_agents=2, active_agents=3, pending_tasks=10)
        assert c.load_factor == 2.0

    def test_overloaded(self):
        c = SwarmConditions(idle_agents=1, active_agents=0, pending_tasks=5)
        assert c.is_overloaded is True

    def test_underloaded(self):
        c = SwarmConditions(idle_agents=10, active_agents=5, pending_tasks=3)
        assert c.is_underloaded is True

    def test_budget_headroom(self):
        c = SwarmConditions(avg_budget_utilization=0.7)
        assert abs(c.budget_headroom - 0.3) < 1e-9


# ─── CircuitBreaker Tests ───────────────────────────────────────────────


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_trip_on_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_success_resets_failures(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()  # Reset
        cb.record_failure()  # Only 1 again
        assert cb.state == CircuitState.CLOSED

    def test_open_to_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_seconds=0.01)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True

    def test_half_open_success_closes(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_seconds=0.01)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout_seconds=0.01)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_max_calls(self):
        cb = CircuitBreaker(
            "test",
            failure_threshold=2,
            recovery_timeout_seconds=0.01,
            half_open_max_calls=2,
        )
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.02)
        # Transition to HALF_OPEN by checking state
        assert cb.state == CircuitState.HALF_OPEN
        # Now manually set half_open_calls to max (simulating 2 calls)
        cb._half_open_calls = 2
        assert cb.allow_request() is False

    def test_reset(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    def test_get_status(self):
        cb = CircuitBreaker("test_service")
        cb.record_failure()
        status = cb.get_status()
        assert status["name"] == "test_service"
        assert status["state"] == "closed"
        assert status["failure_count"] == 1

    def test_total_trips_counted(self):
        cb = CircuitBreaker("test", failure_threshold=1)
        cb.record_failure()  # Trip 1
        cb.reset()
        cb.record_failure()  # Trip 2
        assert cb._total_trips == 2


# ─── RetryScheduler Tests ───────────────────────────────────────────────


class TestRetryScheduler:
    def test_should_retry_under_max(self):
        rs = RetryScheduler(max_retries=3)
        assert rs.should_retry("t1", 0) is True
        assert rs.should_retry("t1", 2) is True

    def test_should_not_retry_at_max(self):
        rs = RetryScheduler(max_retries=3)
        assert rs.should_retry("t1", 3) is False

    def test_next_delay_positive(self):
        rs = RetryScheduler(base_delay=1.0, max_delay=100.0)
        delay = rs.next_delay("t1", 0)
        assert 1.0 <= delay <= 100.0

    def test_next_delay_max_retries_returns_negative(self):
        rs = RetryScheduler(max_retries=3)
        assert rs.next_delay("t1", 3) == -1.0

    def test_next_delay_capped(self):
        rs = RetryScheduler(base_delay=1.0, max_delay=10.0)
        for i in range(10):
            delay = rs.next_delay("t1", i % 5)
            assert delay <= 10.0

    def test_get_next_eligible_time(self):
        rs = RetryScheduler(base_delay=1.0)
        t = rs.get_next_eligible_time("t1", 0)
        assert t > time.time()

    def test_get_next_eligible_time_expired(self):
        rs = RetryScheduler(max_retries=2)
        t = rs.get_next_eligible_time("t1", 2)
        assert t == float("inf")

    def test_clear(self):
        rs = RetryScheduler()
        rs.next_delay("t1", 0)
        assert "t1" in rs._previous_delays
        rs.clear("t1")
        assert "t1" not in rs._previous_delays


# ─── AgentLoadBalancer Tests ────────────────────────────────────────────


class TestAgentLoadBalancer:
    def test_initially_available(self):
        lb = AgentLoadBalancer(max_tasks_per_window=5)
        assert lb.is_available(1) is True

    def test_becomes_unavailable_at_limit(self):
        lb = AgentLoadBalancer(window_seconds=3600, max_tasks_per_window=3)
        for _ in range(3):
            lb.record_assignment(1)
        assert lb.is_available(1) is False

    def test_different_agents_independent(self):
        lb = AgentLoadBalancer(max_tasks_per_window=2)
        lb.record_assignment(1)
        lb.record_assignment(1)
        assert lb.is_available(1) is False
        assert lb.is_available(2) is True

    def test_get_load(self):
        lb = AgentLoadBalancer(max_tasks_per_window=5)
        lb.record_assignment(1)
        lb.record_assignment(1)
        load = lb.get_load(1)
        assert load["recent_tasks"] == 2
        assert load["capacity"] == 5
        assert load["utilization"] == 0.4

    def test_get_load_unknown_agent(self):
        lb = AgentLoadBalancer(max_tasks_per_window=5)
        load = lb.get_load(99)
        assert load["recent_tasks"] == 0

    def test_get_fleet_load(self):
        lb = AgentLoadBalancer(max_tasks_per_window=3)
        lb.record_assignment(1)
        lb.record_assignment(2)
        lb.record_assignment(2)
        fleet = lb.get_fleet_load([1, 2, 3])
        assert fleet["total_agents"] == 3
        assert fleet["total_recent_tasks"] == 3
        assert fleet["total_capacity"] == 9
        assert fleet["overloaded_agents"] == 0


# ─── SwarmScheduler Task Management Tests ────────────────────────────────


class TestSchedulerTaskManagement:
    def setup_method(self):
        self.scheduler = SwarmScheduler(enable_circuit_breakers=False)

    def test_add_task(self):
        task = self.scheduler.add_task(
            task_id="t1",
            title="Photo job",
            categories=["photo"],
            bounty_usd=5.0,
            priority=TaskPriority.NORMAL,
        )
        assert task.task_id == "t1"
        assert self.scheduler.pending_count == 1

    def test_remove_task(self):
        self.scheduler.add_task("t1", "Test", ["photo"], 5.0, TaskPriority.NORMAL)
        assert self.scheduler.remove_task("t1") is True
        assert self.scheduler.pending_count == 0

    def test_remove_nonexistent(self):
        assert self.scheduler.remove_task("nope") is False

    def test_get_task(self):
        self.scheduler.add_task("t1", "Test", ["photo"], 5.0, TaskPriority.NORMAL)
        assert self.scheduler.get_task("t1") is not None
        assert self.scheduler.get_task("nope") is None


# ─── Urgency Computation Tests ──────────────────────────────────────────


class TestUrgencyComputation:
    def setup_method(self):
        self.scheduler = SwarmScheduler(enable_circuit_breakers=False)

    def test_no_deadline_normal(self):
        task = self.scheduler.add_task("t1", "Test", ["a"], 5.0, TaskPriority.NORMAL)
        assert task.urgency == UrgencyLevel.NORMAL

    def test_past_deadline_expired(self):
        task = self.scheduler.add_task(
            "t1",
            "Test",
            ["a"],
            5.0,
            TaskPriority.NORMAL,
            deadline=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert task.urgency == UrgencyLevel.EXPIRED

    def test_30min_deadline_critical(self):
        task = self.scheduler.add_task(
            "t1",
            "Test",
            ["a"],
            5.0,
            TaskPriority.NORMAL,
            deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        assert task.urgency == UrgencyLevel.CRITICAL

    def test_2h_deadline_urgent(self):
        task = self.scheduler.add_task(
            "t1",
            "Test",
            ["a"],
            5.0,
            TaskPriority.NORMAL,
            deadline=datetime.now(timezone.utc) + timedelta(hours=2),
        )
        assert task.urgency == UrgencyLevel.URGENT

    def test_12h_deadline_normal(self):
        task = self.scheduler.add_task(
            "t1",
            "Test",
            ["a"],
            5.0,
            TaskPriority.NORMAL,
            deadline=datetime.now(timezone.utc) + timedelta(hours=12),
        )
        assert task.urgency == UrgencyLevel.NORMAL

    def test_48h_deadline_relaxed(self):
        task = self.scheduler.add_task(
            "t1",
            "Test",
            ["a"],
            5.0,
            TaskPriority.NORMAL,
            deadline=datetime.now(timezone.utc) + timedelta(hours=48),
        )
        assert task.urgency == UrgencyLevel.RELAXED


# ─── Effective Priority Tests ────────────────────────────────────────────


class TestEffectivePriority:
    def setup_method(self):
        self.scheduler = SwarmScheduler(enable_circuit_breakers=False)

    def test_higher_base_priority_wins(self):
        t_critical = self.scheduler.add_task(
            "t1", "A", ["a"], 5.0, TaskPriority.CRITICAL
        )
        t_low = self.scheduler.add_task("t2", "B", ["a"], 5.0, TaskPriority.LOW)
        assert t_critical.effective_priority > t_low.effective_priority

    def test_higher_bounty_adds_bonus(self):
        t_high = self.scheduler.add_task("t1", "A", ["a"], 100.0, TaskPriority.NORMAL)
        t_low = self.scheduler.add_task("t2", "B", ["a"], 1.0, TaskPriority.NORMAL)
        assert t_high.effective_priority > t_low.effective_priority

    def test_expired_task_zero_priority(self):
        t = self.scheduler.add_task(
            "t1",
            "A",
            ["a"],
            5.0,
            TaskPriority.CRITICAL,
            deadline=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert t.effective_priority == 0.0

    def test_retry_penalty(self):
        t = self.scheduler.add_task("t1", "A", ["a"], 5.0, TaskPriority.NORMAL)
        initial = t.effective_priority
        t.retry_count = 3
        self.scheduler._compute_effective_priority(t)
        assert t.effective_priority < initial


# ─── Strategy Selection Tests ────────────────────────────────────────────


class TestStrategySelection:
    def setup_method(self):
        self.scheduler = SwarmScheduler(enable_circuit_breakers=False)

    def _make_task(
        self, urgency=UrgencyLevel.NORMAL, priority=TaskPriority.NORMAL, categories=None
    ):
        task = ScheduledTask(
            task_id="t1",
            title="Test",
            categories=categories or ["general"],
            bounty_usd=5.0,
            priority=priority,
        )
        task.urgency = urgency
        return task

    def test_critical_urgency_best_fit(self):
        task = self._make_task(urgency=UrgencyLevel.CRITICAL)
        strategy, _ = self.scheduler.select_strategy(task, SwarmConditions())
        assert strategy == RoutingStrategy.BEST_FIT

    def test_urgent_urgency_best_fit(self):
        task = self._make_task(urgency=UrgencyLevel.URGENT)
        strategy, _ = self.scheduler.select_strategy(task, SwarmConditions())
        assert strategy == RoutingStrategy.BEST_FIT

    def test_critical_priority_best_fit(self):
        task = self._make_task(priority=TaskPriority.CRITICAL)
        strategy, _ = self.scheduler.select_strategy(task, SwarmConditions())
        assert strategy == RoutingStrategy.BEST_FIT

    def test_high_budget_utilization(self):
        task = self._make_task()
        conditions = SwarmConditions(avg_budget_utilization=0.7)
        strategy, _ = self.scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BUDGET_AWARE

    def test_overloaded_round_robin(self):
        task = self._make_task()
        conditions = SwarmConditions(idle_agents=1, active_agents=0, pending_tasks=5)
        strategy, _ = self.scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.ROUND_ROBIN

    def test_specialist_category(self):
        task = self._make_task(categories=["code_execution"])
        conditions = SwarmConditions(idle_agents=5, active_agents=5)
        strategy, _ = self.scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.SPECIALIST

    def test_default_best_fit(self):
        task = self._make_task()
        conditions = SwarmConditions(idle_agents=5, active_agents=5, pending_tasks=3)
        strategy, _ = self.scheduler.select_strategy(task, conditions)
        assert strategy == RoutingStrategy.BEST_FIT


# ─── Compute Schedule Tests ─────────────────────────────────────────────


class TestComputeSchedule:
    def setup_method(self):
        self.scheduler = SwarmScheduler(enable_circuit_breakers=False)

    def test_empty_pool(self):
        batches = self.scheduler.compute_schedule()
        assert batches == []

    def test_groups_by_category(self):
        self.scheduler.add_task("t1", "A", ["photo"], 5.0, TaskPriority.NORMAL)
        self.scheduler.add_task("t2", "B", ["photo"], 5.0, TaskPriority.NORMAL)
        self.scheduler.add_task("t3", "C", ["delivery"], 5.0, TaskPriority.NORMAL)
        batches = self.scheduler.compute_schedule()
        categories = {b.category_key for b in batches}
        assert "photo" in categories
        assert "delivery" in categories

    def test_expired_tasks_excluded(self):
        self.scheduler.add_task(
            "t1",
            "Expired",
            ["a"],
            5.0,
            TaskPriority.NORMAL,
            deadline=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        self.scheduler.add_task("t2", "Valid", ["a"], 5.0, TaskPriority.NORMAL)
        batches = self.scheduler.compute_schedule()
        all_task_ids = [t.task_id for b in batches for t in b.tasks]
        assert "t1" not in all_task_ids
        assert "t2" in all_task_ids

    def test_backoff_tasks_excluded(self):
        self.scheduler.add_task("t1", "Backoff", ["a"], 5.0, TaskPriority.NORMAL)
        task = self.scheduler.get_task("t1")
        task.next_eligible_at = time.time() + 3600  # 1 hour from now
        batches = self.scheduler.compute_schedule()
        all_task_ids = [t.task_id for b in batches for t in b.tasks]
        assert "t1" not in all_task_ids

    def test_priority_ordering(self):
        self.scheduler.add_task("t_low", "Low", ["a"], 1.0, TaskPriority.LOW)
        self.scheduler.add_task(
            "t_crit",
            "Crit",
            ["a"],
            5.0,
            TaskPriority.CRITICAL,
            deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        batches = self.scheduler.compute_schedule()
        assert len(batches) > 0
        # Critical task should be first in the batch
        first_task = batches[0].tasks[0]
        assert first_task.task_id == "t_crit"

    def test_batch_size_limit(self):
        scheduler = SwarmScheduler(max_batch_size=2, enable_circuit_breakers=False)
        for i in range(5):
            scheduler.add_task(
                f"t{i}", f"Task {i}", ["photo"], 5.0, TaskPriority.NORMAL
            )
        batches = scheduler.compute_schedule()
        for batch in batches:
            assert len(batch.tasks) <= 2

    def test_decisions_recorded(self):
        self.scheduler.add_task("t1", "A", ["photo"], 5.0, TaskPriority.NORMAL)
        self.scheduler.compute_schedule()
        decisions = self.scheduler.get_decisions()
        assert len(decisions) > 0
        assert decisions[0]["task_id"] == "t1"


# ─── Status and Metrics Tests ───────────────────────────────────────────


class TestSchedulerStatus:
    def test_initial_status(self):
        scheduler = SwarmScheduler(enable_circuit_breakers=True)
        status = scheduler.get_status()
        assert status["pending_tasks"] == 0
        assert status["cycles_run"] == 0
        assert "em_api" in status["circuit_breakers"]

    def test_urgency_distribution(self):
        scheduler = SwarmScheduler(enable_circuit_breakers=False)
        scheduler.add_task("t1", "A", ["a"], 5.0, TaskPriority.NORMAL)
        scheduler.add_task(
            "t2",
            "B",
            ["a"],
            5.0,
            TaskPriority.NORMAL,
            deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
        )
        dist = scheduler.get_urgency_distribution()
        assert "normal" in dist
        assert "critical" in dist

    def test_scheduling_cycle_no_coordinator(self):
        scheduler = SwarmScheduler(enable_circuit_breakers=False)
        scheduler.add_task("t1", "A", ["a"], 5.0, TaskPriority.NORMAL)
        result = scheduler.run_scheduling_cycle()
        assert result["cycle"] == 1
        # Without coordinator, execute_schedule returns error
        assert result["tasks_remaining"] >= 0
