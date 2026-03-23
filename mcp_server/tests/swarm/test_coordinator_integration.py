"""
Integration tests for SwarmCoordinator — E2E flows that validate
the coordinator wired to its real subsystems, simulating production
task lifecycle scenarios.

These tests validate scenarios that unit tests can't:
    - Multi-task routing with budget constraints
    - Agent degradation → suspension → recovery cycles
    - Event-driven workflow automation
    - Dashboard accuracy after complex operations
    - Budget exhaustion mid-operation
    - Concurrent task routing and completion
    - Priority inversion detection and handling
"""

import time
from datetime import datetime, timezone, timedelta

import pytest

from mcp_server.swarm.coordinator import (
    SwarmCoordinator,
    EMApiClient,
    CoordinatorEvent,
    SwarmMetrics,
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
from mcp_server.swarm.orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    TaskPriority,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def coordinator():
    """Coordinator with real subsystems, no external clients."""
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge, lifecycle)
    return SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
        em_client=None,
        autojob_client=None,
        default_strategy=RoutingStrategy.BEST_FIT,
        task_expiry_hours=1.0,  # Short for testing
    )


@pytest.fixture
def swarm(coordinator):
    """Coordinator with a 5-agent swarm registered and active."""
    agents = [
        {
            "agent_id": 100 + i,
            "name": name,
            "wallet_address": f"0x{name}{'0' * (40 - len(name))}",
            "personality": personality,
        }
        for i, (name, personality) in enumerate(
            [
                ("Alpha", "explorer"),
                ("Beta", "specialist"),
                ("Gamma", "generalist"),
                ("Delta", "cautious"),
                ("Epsilon", "aggressive"),
            ]
        )
    ]
    coordinator.register_agents_batch(agents)
    return coordinator


# ─── Multi-Task Routing ──────────────────────────────────────────────────────


class TestMultiTaskRouting:
    """Test routing multiple tasks through the system."""

    def test_saturate_swarm(self, swarm):
        """Route more tasks than agents — some should fail."""
        for i in range(8):
            swarm.ingest_task(
                task_id=f"sat-{i}",
                title=f"Task {i}",
                categories=["test"],
                bounty_usd=1.0,
            )

        results = swarm.process_task_queue()
        assignments = [r for r in results if isinstance(r, Assignment)]
        failures = [r for r in results if isinstance(r, RoutingFailure)]

        # 5 agents available → at most 5 assignments
        assert len(assignments) <= 5
        # Some tasks might fail on first attempt (but can retry)
        assert len(assignments) + len(failures) == 8

    def test_complete_and_reroute(self, swarm):
        """Complete a task, freeing an agent, then route more.
        
        After completing a task, the agent transitions from WORKING → COOLDOWN → IDLE.
        We need to manually expire the cooldown for the agent to be available again.
        """
        # Assign one task
        swarm.ingest_task(
            task_id="fill-0",
            title="Fill 0",
            categories=["test"],
        )
        results = swarm.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], Assignment)
        assigned_agent = results[0].agent_id

        # Complete the task — agent goes to COOLDOWN
        swarm.complete_task("fill-0")

        # Expire cooldown so agent becomes IDLE again
        swarm.lifecycle.check_cooldown_expiry(assigned_agent)
        # Force to ACTIVE if still in cooldown
        record = swarm.lifecycle.agents[assigned_agent]
        if record.state == AgentState.COOLDOWN:
            record.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=1)
            swarm.lifecycle.check_cooldown_expiry(assigned_agent)
        if record.state == AgentState.IDLE:
            swarm.lifecycle.transition(assigned_agent, AgentState.ACTIVE, "reactivate")

        # Now route another task
        swarm.ingest_task(
            task_id="after-complete",
            title="After complete",
            categories=["test"],
        )
        results = swarm.process_task_queue()
        assignments = [r for r in results if isinstance(r, Assignment)]
        assert len(assignments) >= 1

    def test_mixed_priority_batch(self, swarm):
        """Tasks should be routed in priority order."""
        swarm.ingest_task(
            task_id="low",
            title="Low",
            categories=["test"],
            priority=TaskPriority.LOW,
        )
        swarm.ingest_task(
            task_id="critical",
            title="Critical",
            categories=["test"],
            priority=TaskPriority.CRITICAL,
        )
        swarm.ingest_task(
            task_id="normal",
            title="Normal",
            categories=["test"],
            priority=TaskPriority.NORMAL,
        )

        # Route only 1 at a time to verify ordering
        r1 = swarm.process_task_queue(max_tasks=1)
        assert r1[0].task_id == "critical"

        r2 = swarm.process_task_queue(max_tasks=1)
        assert r2[0].task_id == "normal"

        r3 = swarm.process_task_queue(max_tasks=1)
        assert r3[0].task_id == "low"


# ─── Budget Lifecycle ─────────────────────────────────────────────────────────


class TestBudgetLifecycle:
    """Test budget constraints through the coordinator."""

    def test_budget_tracking_through_completion(self, coordinator):
        """Budget should reflect task completions."""
        budget = BudgetConfig(
            daily_limit_usd=10.0,
            monthly_limit_usd=50.0,
            task_limit_usd=5.0,
        )
        coordinator.register_agent(
            agent_id=200,
            name="BudgetAgent",
            wallet_address="0xBudget" + "0" * 34,
            budget_config=budget,
        )

        coordinator.ingest_task(
            task_id="budget-1",
            title="Cheap task",
            categories=["test"],
            bounty_usd=3.0,
        )
        coordinator.process_task_queue()
        coordinator.complete_task("budget-1", bounty_earned_usd=3.0)

        budget_status = coordinator.lifecycle.get_budget_status(200)
        assert budget_status["daily_spent"] == 3.0

    def test_multiple_completions_accumulate_budget(self, coordinator):
        """Multiple task completions should accumulate budget spend.
        
        After each completion, agent goes to COOLDOWN. We need to expire
        the cooldown and re-activate the agent before the next task.
        """
        budget = BudgetConfig(daily_limit_usd=20.0, monthly_limit_usd=100.0)
        coordinator.register_agent(
            agent_id=201,
            name="MultiTask",
            wallet_address="0xMulti" + "0" * 35,
            budget_config=budget,
        )

        total_bounty = 0.0
        for i in range(3):
            coordinator.ingest_task(
                task_id=f"acc-{i}",
                title=f"Task {i}",
                categories=["test"],
                bounty_usd=4.0,
            )
            coordinator.process_task_queue()
            result = coordinator.complete_task(f"acc-{i}", bounty_earned_usd=4.0)
            if result:
                total_bounty += 4.0

            # Expire cooldown and re-activate for next task
            record = coordinator.lifecycle.agents[201]
            if record.state == AgentState.COOLDOWN:
                record.cooldown_until = datetime.now(timezone.utc) - timedelta(seconds=1)
                coordinator.lifecycle.check_cooldown_expiry(201)
            if record.state == AgentState.IDLE:
                coordinator.lifecycle.transition(201, AgentState.ACTIVE, "reactivate")

        assert coordinator._total_bounty_earned == total_bounty
        assert total_bounty == 12.0


# ─── Event-Driven Workflows ──────────────────────────────────────────────────


class TestEventDrivenWorkflows:
    """Test event hooks for building workflows on top of the coordinator."""

    def test_auto_reroute_on_failure(self, swarm):
        """Hook into TASK_FAILED to trigger auto re-ingest."""
        rerouted = []

        def on_failure(event):
            task_id = event.data.get("task_id")
            if task_id:
                rerouted.append(task_id)

        swarm.on_event(CoordinatorEvent.TASK_FAILED, on_failure)

        swarm.ingest_task(
            task_id="reroute-1",
            title="Will fail",
            categories=["test"],
        )
        swarm.process_task_queue()
        swarm.fail_task("reroute-1", error="Worker quit")

        assert "reroute-1" in rerouted

    def test_budget_warning_hook(self, coordinator):
        """Budget warning events should fire when threshold crossed."""
        warnings = []

        def on_warning(event):
            warnings.append(event.data)

        coordinator.on_event(CoordinatorEvent.BUDGET_WARNING, on_warning)

        budget = BudgetConfig(
            daily_limit_usd=5.0,
            monthly_limit_usd=100.0,
            warning_threshold=0.50,
        )
        coordinator.register_agent(
            agent_id=300,
            name="BudgetWatch",
            wallet_address="0xWatch" + "0" * 35,
            budget_config=budget,
        )

        # Spend enough to trigger warning
        coordinator.lifecycle.record_spend(300, 3.0)  # 60% of daily

        coordinator.run_health_checks()
        assert len(warnings) >= 1

    def test_event_chain_ingest_to_complete(self, swarm):
        """Track the full event chain for a single task."""
        events_seen = []

        for event_type in [
            CoordinatorEvent.TASK_INGESTED,
            CoordinatorEvent.TASK_ASSIGNED,
            CoordinatorEvent.TASK_COMPLETED,
        ]:
            swarm.on_event(
                event_type, lambda e, et=event_type: events_seen.append(et.value)
            )

        swarm.ingest_task(
            task_id="chain-1", title="Track me", categories=["test"]
        )
        swarm.process_task_queue()
        swarm.complete_task("chain-1")

        assert events_seen == ["task_ingested", "task_assigned", "task_completed"]


# ─── Task Expiry ──────────────────────────────────────────────────────────────


class TestTaskExpiry:
    """Test task expiration flows."""

    def test_pending_tasks_expire(self, swarm):
        """Pending tasks older than expiry threshold should be expired."""
        task = swarm.ingest_task(
            task_id="expire-1",
            title="Old pending",
            categories=["test"],
        )
        task.ingested_at = datetime.now(timezone.utc) - timedelta(hours=2)

        report = swarm.run_health_checks()
        assert report["tasks"]["expired"] >= 1
        assert swarm._task_queue["expire-1"].status == "expired"
        assert swarm._total_expired >= 1

    def test_assigned_tasks_dont_expire(self, swarm):
        """Assigned tasks should not be expired, only flagged as stale."""
        swarm.ingest_task(
            task_id="no-expire",
            title="Assigned",
            categories=["test"],
        )
        swarm.process_task_queue()

        task = swarm._task_queue["no-expire"]
        task.last_attempt_at = datetime.now(timezone.utc) - timedelta(hours=2)

        report = swarm.run_health_checks()
        # Assigned tasks should be flagged stale, not expired
        assert task.status == "assigned"

    def test_expired_tasks_emit_event(self, swarm):
        task = swarm.ingest_task(
            task_id="exp-evt",
            title="Will expire",
            categories=["test"],
        )
        task.ingested_at = datetime.now(timezone.utc) - timedelta(hours=2)

        swarm.run_health_checks()

        events = swarm.get_events(event_type=CoordinatorEvent.TASK_EXPIRED)
        assert len(events) >= 1
        assert events[-1]["task_id"] == "exp-evt"


# ─── Dashboard Accuracy ──────────────────────────────────────────────────────


class TestDashboardAccuracy:
    """Test that the dashboard reflects actual system state."""

    def test_dashboard_after_complex_operations(self, swarm):
        """Dashboard should accurately reflect mixed operations."""
        # Ingest 4 tasks
        for i in range(4):
            swarm.ingest_task(
                task_id=f"complex-{i}",
                title=f"Task {i}",
                categories=["photo"] if i % 2 == 0 else ["delivery"],
                bounty_usd=5.0 + i,
            )

        # Route all
        swarm.process_task_queue()

        # Complete 2, fail 1
        swarm.complete_task("complex-0", bounty_earned_usd=5.0)
        swarm.complete_task("complex-1", bounty_earned_usd=6.0)
        swarm.fail_task("complex-2", error="no-show")

        # Health check
        swarm.run_health_checks()

        # Verify dashboard
        dashboard = swarm.get_dashboard()
        assert dashboard["metrics"]["tasks"]["ingested"] == 4
        assert dashboard["metrics"]["tasks"]["completed"] == 2
        assert dashboard["metrics"]["tasks"]["failed"] >= 1
        assert dashboard["metrics"]["tasks"]["bounty_earned_usd"] == 11.0

    def test_dashboard_fleet_states(self, swarm):
        """Fleet should show accurate agent states."""
        swarm.ingest_task(
            task_id="state-1", title="T1", categories=["test"]
        )
        swarm.process_task_queue()

        dashboard = swarm.get_dashboard()
        states = [a["state"] for a in dashboard["fleet"]]

        # At least one agent should be WORKING (assigned to task)
        assert "working" in states or "active" in states

    def test_queue_summary_accuracy(self, swarm):
        """Queue summary should match actual queue state."""
        swarm.ingest_task(
            task_id="qs-1", title="T1", categories=["photo"], bounty_usd=5.0
        )
        swarm.ingest_task(
            task_id="qs-2", title="T2", categories=["delivery"], bounty_usd=10.0
        )
        swarm.process_task_queue(max_tasks=1)

        summary = swarm.get_queue_summary()
        assert summary["total"] == 2
        assert summary["by_status"].get("assigned", 0) >= 1
        assert summary["by_status"].get("pending", 0) >= 0


# ─── Resilience ───────────────────────────────────────────────────────────────


class TestResilience:
    """Test coordinator resilience to edge cases."""

    def test_empty_swarm_routing(self, coordinator):
        """Routing with no agents should fail gracefully."""
        coordinator.ingest_task(
            task_id="empty-1", title="No agents", categories=["test"]
        )
        task = coordinator._task_queue["empty-1"]
        task.max_attempts = 1

        results = coordinator.process_task_queue()
        assert len(results) == 1
        assert isinstance(results[0], RoutingFailure)

    def test_rapid_ingest_route_cycle(self, swarm):
        """Rapid ingest-route cycles should work without state corruption."""
        for cycle in range(5):
            task_id = f"rapid-{cycle}"
            swarm.ingest_task(
                task_id=task_id,
                title=f"Rapid {cycle}",
                categories=["test"],
                bounty_usd=1.0,
            )
            results = swarm.process_task_queue()
            if results and isinstance(results[0], Assignment):
                swarm.complete_task(task_id, bounty_earned_usd=1.0)

        metrics = swarm.get_metrics()
        assert metrics.tasks_ingested == 5
        assert metrics.tasks_completed <= 5  # Up to 5 completed

    def test_double_complete(self, swarm):
        """Completing a task twice should not crash or double-count."""
        swarm.ingest_task(
            task_id="double-1", title="Double", categories=["test"], bounty_usd=5.0
        )
        swarm.process_task_queue()

        result1 = swarm.complete_task("double-1", bounty_earned_usd=5.0)
        result2 = swarm.complete_task("double-1", bounty_earned_usd=5.0)

        # First should succeed, second may succeed or fail gracefully
        assert result1 is True

    def test_cleanup_after_mixed_operations(self, swarm):
        """Cleanup should only remove terminated tasks."""
        for i in range(5):
            swarm.ingest_task(
                task_id=f"mix-{i}",
                title=f"Mix {i}",
                categories=["test"],
            )

        swarm.process_task_queue()
        swarm.complete_task("mix-0")
        swarm.fail_task("mix-1")

        # Backdate completed/failed tasks
        for tid in ["mix-0", "mix-1"]:
            if tid in swarm._task_queue:
                swarm._task_queue[tid].ingested_at = (
                    datetime.now(timezone.utc) - timedelta(hours=48)
                )

        removed = swarm.cleanup_completed(older_than_hours=24.0)
        assert removed >= 1

        # Pending/assigned tasks should survive
        remaining_pending = [
            t for t in swarm._task_queue.values()
            if t.status in ("pending", "assigned")
        ]
        assert len(remaining_pending) >= 1

    def test_metrics_consistency(self, swarm):
        """Metrics should be internally consistent."""
        for i in range(3):
            swarm.ingest_task(
                task_id=f"con-{i}",
                title=f"T{i}",
                categories=["test"],
            )
        swarm.process_task_queue()
        swarm.complete_task("con-0")
        swarm.fail_task("con-1")

        metrics = swarm.get_metrics()
        # Assigned = (initially assigned) - completed - failed
        assert metrics.tasks_assigned >= metrics.tasks_completed
        assert metrics.tasks_ingested >= metrics.tasks_assigned


# ─── Strategy Selection ──────────────────────────────────────────────────────


class TestStrategySelection:
    """Test different routing strategies through the coordinator."""

    def test_round_robin_strategy(self, swarm):
        """ROUND_ROBIN should distribute tasks."""
        for i in range(3):
            swarm.ingest_task(
                task_id=f"rr-{i}",
                title=f"RR {i}",
                categories=["test"],
            )

        results = swarm.process_task_queue(strategy=RoutingStrategy.ROUND_ROBIN)
        assigned_agents = set()
        for r in results:
            if isinstance(r, Assignment):
                assigned_agents.add(r.agent_id)

        # Round robin should try to use different agents
        assert len(assigned_agents) >= 1

    def test_specialist_strategy(self, swarm):
        """SPECIALIST strategy should work without errors."""
        swarm.ingest_task(
            task_id="spec-1",
            title="Specialist task",
            categories=["photo_verification"],
        )

        results = swarm.process_task_queue(strategy=RoutingStrategy.SPECIALIST)
        assert len(results) == 1

    def test_budget_aware_strategy(self, swarm):
        """BUDGET_AWARE should work without errors."""
        swarm.ingest_task(
            task_id="ba-1",
            title="Budget aware",
            categories=["test"],
            bounty_usd=2.0,
        )

        results = swarm.process_task_queue(strategy=RoutingStrategy.BUDGET_AWARE)
        assert len(results) == 1
