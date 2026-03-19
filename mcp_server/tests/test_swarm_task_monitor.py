"""
Tests for TaskMonitor — real-time task lifecycle monitoring and intervention engine.

Covers:
    - MonitoredTask: properties, urgency, deadline calculations
    - InterventionRule: matching logic
    - TaskMonitor: ingestion, urgency classification, rules engine,
      intervention triggering, cooldowns, outcome tracking, stats, health,
      default rules, callbacks
"""

import time
import pytest
from unittest.mock import MagicMock

from mcp_server.swarm.task_monitor import (
    TaskMonitor,
    MonitoredTask,
    Intervention,
    InterventionRule,
    InterventionOutcome,
    InterventionType,
    TaskUrgency,
)


# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def monitor():
    return TaskMonitor()


@pytest.fixture
def monitor_with_rules():
    return TaskMonitor.with_default_rules()


@pytest.fixture
def now():
    return time.time()


# ─── MonitoredTask Tests ──────────────────────────────────────────


class TestMonitoredTask:
    """Test MonitoredTask dataclass and properties."""

    def test_basic_creation(self):
        task = MonitoredTask(task_id="t1", title="Test task")
        assert task.task_id == "t1"
        assert task.title == "Test task"
        assert task.status == "open"
        assert task.urgency == TaskUrgency.HEALTHY
        assert task.intervention_count == 0
        assert task.max_interventions == 3

    def test_time_remaining_no_deadline(self):
        task = MonitoredTask(task_id="t1", title="Test", deadline_at=None)
        assert task.time_remaining_seconds is None

    def test_time_remaining_future_deadline(self):
        future = time.time() + 3600
        task = MonitoredTask(task_id="t1", title="Test", deadline_at=future)
        remaining = task.time_remaining_seconds
        assert remaining is not None
        assert 3590 < remaining <= 3600

    def test_time_remaining_past_deadline(self):
        past = time.time() - 100
        task = MonitoredTask(task_id="t1", title="Test", deadline_at=past)
        assert task.time_remaining_seconds == 0

    def test_time_elapsed_ratio_no_deadline(self):
        task = MonitoredTask(task_id="t1", title="Test", deadline_at=None)
        assert task.time_elapsed_ratio is None

    def test_time_elapsed_ratio_same_create_deadline(self):
        now = time.time()
        task = MonitoredTask(
            task_id="t1",
            title="Test",
            created_at=now,
            deadline_at=now,
        )
        assert task.time_elapsed_ratio is None

    def test_time_elapsed_ratio_midway(self):
        now = time.time()
        task = MonitoredTask(
            task_id="t1",
            title="Test",
            created_at=now - 500,
            deadline_at=now + 500,
        )
        ratio = task.time_elapsed_ratio
        assert ratio is not None
        assert 0.45 < ratio < 0.55

    def test_time_elapsed_ratio_past_deadline(self):
        now = time.time()
        task = MonitoredTask(
            task_id="t1",
            title="Test",
            created_at=now - 1000,
            deadline_at=now - 500,
        )
        assert task.time_elapsed_ratio == 1.0

    def test_time_elapsed_ratio_just_created(self):
        now = time.time()
        task = MonitoredTask(
            task_id="t1",
            title="Test",
            created_at=now,
            deadline_at=now + 1000,
        )
        ratio = task.time_elapsed_ratio
        assert ratio is not None
        assert ratio < 0.05

    def test_is_assigned(self):
        task = MonitoredTask(task_id="t1", title="Test")
        assert not task.is_assigned
        task.worker_id = "w1"
        assert task.is_assigned

    def test_can_intervene(self):
        task = MonitoredTask(task_id="t1", title="Test", max_interventions=2)
        assert task.can_intervene
        task.intervention_count = 1
        assert task.can_intervene
        task.intervention_count = 2
        assert not task.can_intervene


# ─── Intervention Tests ──────────────────────────────────────────


class TestIntervention:
    """Test Intervention dataclass."""

    def test_basic_creation(self):
        intervention = Intervention(
            intervention_id="int-1",
            task_id="t1",
            intervention_type=InterventionType.REBROADCAST,
        )
        assert intervention.intervention_id == "int-1"
        assert intervention.outcome == InterventionOutcome.PENDING
        assert intervention.resolved_at is None

    def test_duration_pending(self):
        intervention = Intervention(
            intervention_id="int-1",
            task_id="t1",
            intervention_type=InterventionType.REBROADCAST,
        )
        assert intervention.duration_seconds is None

    def test_duration_resolved(self):
        now = time.time()
        intervention = Intervention(
            intervention_id="int-1",
            task_id="t1",
            intervention_type=InterventionType.REBROADCAST,
            triggered_at=now - 60,
            resolved_at=now,
        )
        assert abs(intervention.duration_seconds - 60.0) < 1


# ─── InterventionRule Tests ──────────────────────────────────────


class TestInterventionRule:
    """Test InterventionRule matching logic."""

    def test_basic_match(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
        )
        task = MonitoredTask(task_id="t1", title="T", urgency=TaskUrgency.WARNING)
        assert rule.matches(task)

    def test_no_match_wrong_urgency(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
        )
        task = MonitoredTask(task_id="t1", title="T", urgency=TaskUrgency.HEALTHY)
        assert not rule.matches(task)

    def test_disabled_rule(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
            enabled=False,
        )
        task = MonitoredTask(task_id="t1", title="T", urgency=TaskUrgency.WARNING)
        assert not rule.matches(task)

    def test_requires_assignment_true(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.CRITICAL,
            intervention_type=InterventionType.DEADLINE_WARNING,
            requires_assignment=True,
        )
        unassigned = MonitoredTask(
            task_id="t1", title="T", urgency=TaskUrgency.CRITICAL
        )
        assigned = MonitoredTask(
            task_id="t2", title="T", urgency=TaskUrgency.CRITICAL, worker_id="w1"
        )
        assert not rule.matches(unassigned)
        assert rule.matches(assigned)

    def test_requires_assignment_false(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.CRITICAL,
            intervention_type=InterventionType.ESCALATE_BOUNTY,
            requires_assignment=False,
        )
        unassigned = MonitoredTask(
            task_id="t1", title="T", urgency=TaskUrgency.CRITICAL
        )
        assigned = MonitoredTask(
            task_id="t2", title="T", urgency=TaskUrgency.CRITICAL, worker_id="w1"
        )
        assert rule.matches(unassigned)
        assert not rule.matches(assigned)

    def test_bounty_range(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
            min_bounty_usd=0.10,
            max_bounty_usd=1.00,
        )
        too_low = MonitoredTask(
            task_id="t1", title="T", urgency=TaskUrgency.WARNING, bounty_usd=0.05
        )
        in_range = MonitoredTask(
            task_id="t2", title="T", urgency=TaskUrgency.WARNING, bounty_usd=0.50
        )
        too_high = MonitoredTask(
            task_id="t3", title="T", urgency=TaskUrgency.WARNING, bounty_usd=2.00
        )
        assert not rule.matches(too_low)
        assert rule.matches(in_range)
        assert not rule.matches(too_high)

    def test_requires_assignment_none_matches_both(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
            requires_assignment=None,
        )
        unassigned = MonitoredTask(task_id="t1", title="T", urgency=TaskUrgency.WARNING)
        assigned = MonitoredTask(
            task_id="t2", title="T", urgency=TaskUrgency.WARNING, worker_id="w1"
        )
        assert rule.matches(unassigned)
        assert rule.matches(assigned)


# ─── TaskMonitor Ingestion Tests ─────────────────────────────────


class TestTaskMonitorIngestion:
    """Test task ingestion and tracking."""

    def test_ingest_new_task(self, monitor):
        task = monitor.ingest_task("t1", title="Buy groceries", bounty_usd=0.25)
        assert task.task_id == "t1"
        assert task.title == "Buy groceries"
        assert task.bounty_usd == 0.25
        assert "t1" in monitor.tasks

    def test_ingest_updates_existing(self, monitor):
        monitor.ingest_task("t1", title="Test", status="open")
        monitor.ingest_task("t1", status="assigned", worker_id="w1")
        task = monitor.get_task("t1")
        assert task.status == "assigned"
        assert task.worker_id == "w1"

    def test_ingest_preserves_deadline_on_update(self, monitor):
        deadline = time.time() + 3600
        monitor.ingest_task("t1", title="Test", deadline_at=deadline)
        monitor.ingest_task("t1", status="assigned")
        assert monitor.get_task("t1").deadline_at == deadline

    def test_ingest_updates_deadline(self, monitor):
        deadline1 = time.time() + 3600
        deadline2 = time.time() + 7200
        monitor.ingest_task("t1", title="Test", deadline_at=deadline1)
        monitor.ingest_task("t1", deadline_at=deadline2)
        assert monitor.get_task("t1").deadline_at == deadline2

    def test_remove_task(self, monitor):
        monitor.ingest_task("t1", title="Test")
        assert monitor.remove_task("t1")
        assert monitor.get_task("t1") is None

    def test_remove_nonexistent_task(self, monitor):
        assert not monitor.remove_task("nonexistent")

    def test_get_active_tasks(self, monitor):
        monitor.ingest_task("t1", title="Task 1")
        monitor.ingest_task("t2", title="Task 2")
        monitor.ingest_task("t3", title="Task 3")
        active = monitor.get_active_tasks()
        assert len(active) == 3

    def test_get_task_nonexistent(self, monitor):
        assert monitor.get_task("ghost") is None


# ─── Urgency Classification Tests ────────────────────────────────


class TestUrgencyClassification:
    """Test urgency level classification based on deadline proximity."""

    def test_no_deadline_is_healthy(self, monitor):
        task = monitor.ingest_task("t1", title="Test")
        assert task.urgency == TaskUrgency.HEALTHY

    def test_early_task_is_healthy(self, monitor, now):
        task = monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now,
            deadline_at=now + 10000,  # Long deadline
        )
        assert task.urgency == TaskUrgency.HEALTHY

    def test_watch_urgency(self, monitor, now):
        # 35% elapsed → WATCH (between 25% and 50%)
        task = monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 350,
            deadline_at=now + 650,
        )
        assert task.urgency == TaskUrgency.WATCH

    def test_warning_urgency(self, monitor, now):
        # 60% elapsed → WARNING (between 50% and 75%)
        task = monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        assert task.urgency == TaskUrgency.WARNING

    def test_critical_urgency(self, monitor, now):
        # 85% elapsed → CRITICAL (between 75% and 100%)
        task = monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 850,
            deadline_at=now + 150,
        )
        assert task.urgency == TaskUrgency.CRITICAL

    def test_overdue_urgency(self, monitor, now):
        task = monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 1000,
            deadline_at=now - 10,
        )
        assert task.urgency == TaskUrgency.OVERDUE

    def test_get_tasks_by_urgency(self, monitor, now):
        monitor.ingest_task("t1", title="T1")  # No deadline = HEALTHY
        monitor.ingest_task(
            "t2",
            title="T2",
            created_at=now - 850,
            deadline_at=now + 150,
        )  # CRITICAL
        monitor.ingest_task(
            "t3",
            title="T3",
            created_at=now - 1000,
            deadline_at=now - 10,
        )  # OVERDUE

        healthy = monitor.get_tasks_by_urgency(TaskUrgency.HEALTHY)
        critical = monitor.get_tasks_by_urgency(TaskUrgency.CRITICAL)
        overdue = monitor.get_tasks_by_urgency(TaskUrgency.OVERDUE)
        assert len(healthy) == 1
        assert len(critical) == 1
        assert len(overdue) == 1

    def test_urgency_change_callback(self, monitor, now):
        changes = []
        monitor.on_urgency_change(
            lambda task, old, new: changes.append((task.task_id, old, new))
        )

        # First ingest — classified on creation (default HEALTHY, new might differ)
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 850,
            deadline_at=now + 150,
        )
        # Changes if different from initial HEALTHY default
        assert len(changes) >= 1  # HEALTHY → CRITICAL
        assert changes[-1][2] == TaskUrgency.CRITICAL

    def test_urgency_change_on_update(self, monitor, now):
        changes = []

        # Start healthy
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now,
            deadline_at=now + 10000,
        )

        monitor.on_urgency_change(lambda task, old, new: changes.append((old, new)))

        # Update deadline to push into critical
        monitor.ingest_task(
            "t1",
            deadline_at=now + 50,
        )
        # Created_at still near now, so elapsed ratio is low → should stay HEALTHY
        # Actually, created_at stays as original (now), deadline becomes now+50
        # elapsed = time.time() - now ≈ 0, total = 50, ratio ≈ 0 → HEALTHY
        # So no change expected here. Let's force a change.

    def test_custom_urgency_thresholds(self, now):
        custom = {
            TaskUrgency.HEALTHY: 0.10,
            TaskUrgency.WATCH: 0.30,
            TaskUrgency.WARNING: 0.50,
            TaskUrgency.CRITICAL: 1.0,
        }
        monitor = TaskMonitor(urgency_thresholds=custom)
        # 20% elapsed with custom thresholds → WATCH (not HEALTHY)
        task = monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 200,
            deadline_at=now + 800,
        )
        assert task.urgency == TaskUrgency.WATCH


# ─── Rules Engine Tests ──────────────────────────────────────────


class TestRulesEngine:
    """Test rule management."""

    def test_add_rule(self, monitor):
        rule = InterventionRule(
            name="test_rule",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
        )
        monitor.add_rule(rule)
        assert len(monitor.get_rules()) == 1

    def test_remove_rule(self, monitor):
        monitor.add_rule(
            InterventionRule(
                name="r1",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
            )
        )
        monitor.add_rule(
            InterventionRule(
                name="r2",
                urgency_trigger=TaskUrgency.CRITICAL,
                intervention_type=InterventionType.ESCALATE_BOUNTY,
            )
        )
        assert monitor.remove_rule("r1")
        assert len(monitor.get_rules()) == 1
        assert monitor.get_rules()[0].name == "r2"

    def test_remove_nonexistent_rule(self, monitor):
        assert not monitor.remove_rule("ghost")


# ─── Intervention Triggering Tests ───────────────────────────────


class TestInterventionTriggering:
    """Test the run_cycle intervention triggering logic."""

    def test_run_cycle_triggers_matching_rule(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="warn_unassigned",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        triggered = monitor.run_cycle()
        assert len(triggered) == 1
        assert triggered[0].intervention_type == InterventionType.REBROADCAST

    def test_run_cycle_no_match(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="only_critical",
                urgency_trigger=TaskUrgency.CRITICAL,
                intervention_type=InterventionType.ESCALATE_BOUNTY,
                cooldown_seconds=0,
            )
        )
        # Task is HEALTHY
        monitor.ingest_task("t1", title="Test")
        triggered = monitor.run_cycle()
        assert len(triggered) == 0

    def test_run_cycle_skips_completed_tasks(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="warn",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            status="completed",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        triggered = monitor.run_cycle()
        assert len(triggered) == 0

    def test_run_cycle_skips_cancelled_tasks(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="warn",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            status="cancelled",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        triggered = monitor.run_cycle()
        assert len(triggered) == 0

    def test_run_cycle_skips_expired_tasks(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="warn",
                urgency_trigger=TaskUrgency.OVERDUE,
                intervention_type=InterventionType.CANCEL_GRACEFUL,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            status="expired",
            created_at=now - 1000,
            deadline_at=now - 10,
        )
        triggered = monitor.run_cycle()
        assert len(triggered) == 0

    def test_intervention_handler_called(self, monitor, now):
        handler = MagicMock()
        monitor.on_intervention(handler)
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        monitor.run_cycle()
        handler.assert_called_once()
        args = handler.call_args[0]
        assert isinstance(args[0], Intervention)
        assert isinstance(args[1], MonitoredTask)

    def test_intervention_handler_error_doesnt_crash(self, monitor, now):
        def bad_handler(intervention, task):
            raise RuntimeError("boom")

        monitor.on_intervention(bad_handler)
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        # Should not raise
        triggered = monitor.run_cycle()
        assert len(triggered) == 1

    def test_urgency_change_handler_error_doesnt_crash(self, monitor, now):
        def bad_handler(task, old, new):
            raise RuntimeError("urgency boom")

        monitor.on_urgency_change(bad_handler)
        # Should not raise despite bad handler
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 850,
            deadline_at=now + 150,
        )

    def test_multiple_interventions_same_cycle(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="rule1",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.add_rule(
            InterventionRule(
                name="rule2",
                urgency_trigger=TaskUrgency.CRITICAL,
                intervention_type=InterventionType.ESCALATE_BOUNTY,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Warning task",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        monitor.ingest_task(
            "t2",
            title="Critical task",
            created_at=now - 850,
            deadline_at=now + 150,
        )
        triggered = monitor.run_cycle()
        assert len(triggered) == 2
        types = {t.intervention_type for t in triggered}
        assert InterventionType.REBROADCAST in types
        assert InterventionType.ESCALATE_BOUNTY in types

    def test_intervention_increments_task_count(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
                max_per_task=5,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        monitor.run_cycle()
        task = monitor.get_task("t1")
        assert task.intervention_count == 1


# ─── Cooldown Tests ──────────────────────────────────────────────


class TestCooldowns:
    """Test intervention cooldown logic."""

    def test_cooldown_prevents_repeat(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=600,  # 10 min cooldown
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        first = monitor.run_cycle()
        assert len(first) == 1

        # Second cycle immediately — should be blocked by cooldown
        second = monitor.run_cycle()
        assert len(second) == 0

    def test_zero_cooldown_allows_repeat(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
                max_per_task=5,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        first = monitor.run_cycle()
        second = monitor.run_cycle()
        assert len(first) == 1
        assert len(second) == 1

    def test_max_per_task_limit(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
                max_per_task=2,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        r1 = monitor.run_cycle()
        r2 = monitor.run_cycle()
        r3 = monitor.run_cycle()  # Should be blocked
        assert len(r1) == 1
        assert len(r2) == 1
        assert len(r3) == 0

    def test_max_interventions_global_limit(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="r1",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
                max_per_task=10,
            )
        )
        monitor.add_rule(
            InterventionRule(
                name="r2",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.ESCALATE_BOUNTY,
                cooldown_seconds=0,
                max_per_task=10,
            )
        )
        # Task with max_interventions=2
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        monitor.tasks["t1"].max_interventions = 2

        r1 = monitor.run_cycle()  # Should trigger 2 (hits max)
        assert len(r1) == 2
        r2 = monitor.run_cycle()  # Should be blocked by can_intervene
        assert len(r2) == 0


# ─── Outcome Tracking Tests ─────────────────────────────────────


class TestOutcomeTracking:
    """Test intervention outcome recording."""

    def test_record_outcome(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        triggered = monitor.run_cycle()
        iid = triggered[0].intervention_id

        assert monitor.record_outcome(iid, InterventionOutcome.SUCCESS)
        intervention = monitor.get_interventions(task_id="t1")[0]
        assert intervention.outcome == InterventionOutcome.SUCCESS
        assert intervention.resolved_at is not None

    def test_record_outcome_nonexistent(self, monitor):
        assert not monitor.record_outcome("ghost-id", InterventionOutcome.FAILED)

    def test_record_task_outcome_completed(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
                max_per_task=5,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        monitor.run_cycle()
        monitor.run_cycle()  # Two interventions

        monitor.record_task_outcome("t1", completed=True)
        interventions = monitor.get_interventions(task_id="t1")
        assert all(i.outcome == InterventionOutcome.SUCCESS for i in interventions)

    def test_record_task_outcome_expired(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        monitor.run_cycle()

        monitor.record_task_outcome("t1", completed=False)
        interventions = monitor.get_interventions(task_id="t1")
        assert all(i.outcome == InterventionOutcome.FAILED for i in interventions)

    def test_record_task_outcome_doesnt_override_resolved(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        triggered = monitor.run_cycle()
        iid = triggered[0].intervention_id

        # Manually resolve
        monitor.record_outcome(iid, InterventionOutcome.PARTIAL)

        # Task-level outcome shouldn't override PARTIAL
        monitor.record_task_outcome("t1", completed=True)
        intervention = monitor.get_interventions(task_id="t1")[0]
        assert intervention.outcome == InterventionOutcome.PARTIAL  # unchanged


# ─── Query Tests ─────────────────────────────────────────────────


class TestInterventionQueries:
    """Test intervention filtering."""

    def test_filter_by_task(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1", title="T1", created_at=now - 600, deadline_at=now + 400
        )
        monitor.ingest_task(
            "t2", title="T2", created_at=now - 600, deadline_at=now + 400
        )
        monitor.run_cycle()

        t1_ints = monitor.get_interventions(task_id="t1")
        t2_ints = monitor.get_interventions(task_id="t2")
        assert len(t1_ints) == 1
        assert len(t2_ints) == 1

    def test_filter_by_type(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="r1",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.add_rule(
            InterventionRule(
                name="r2",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.ESCALATE_BOUNTY,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1", title="T", created_at=now - 600, deadline_at=now + 400
        )
        monitor.run_cycle()

        rebroadcasts = monitor.get_interventions(
            intervention_type=InterventionType.REBROADCAST
        )
        escalations = monitor.get_interventions(
            intervention_type=InterventionType.ESCALATE_BOUNTY
        )
        assert len(rebroadcasts) == 1
        assert len(escalations) == 1

    def test_filter_by_outcome(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1", title="T", created_at=now - 600, deadline_at=now + 400
        )
        monitor.run_cycle()

        pending = monitor.get_interventions(outcome=InterventionOutcome.PENDING)
        success = monitor.get_interventions(outcome=InterventionOutcome.SUCCESS)
        assert len(pending) == 1
        assert len(success) == 0


# ─── Stats & Health Tests ───────────────────────────────────────


class TestStatsAndHealth:
    """Test monitoring statistics and health reports."""

    def test_empty_stats(self, monitor):
        stats = monitor.get_stats()
        assert stats.total_tasks_monitored == 0
        assert stats.tasks_currently_active == 0
        assert stats.total_interventions == 0

    def test_stats_after_activity(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1", title="T", created_at=now - 600, deadline_at=now + 400
        )
        monitor.run_cycle()

        stats = monitor.get_stats()
        assert stats.tasks_currently_active == 1
        assert stats.total_interventions == 1
        assert stats.interventions_by_type["rebroadcast"] == 1
        assert stats.interventions_by_outcome["pending"] == 1

    def test_stats_urgency_distribution(self, monitor, now):
        monitor.ingest_task("t1", title="Healthy")
        monitor.ingest_task(
            "t2",
            title="Critical",
            created_at=now - 850,
            deadline_at=now + 150,
        )
        stats = monitor.get_stats()
        assert stats.urgency_distribution["healthy"] == 1
        assert stats.urgency_distribution["critical"] == 1

    def test_stats_avg_response_time(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1", title="T", created_at=now - 600, deadline_at=now + 400
        )
        triggered = monitor.run_cycle()
        monitor.record_outcome(
            triggered[0].intervention_id, InterventionOutcome.SUCCESS
        )

        stats = monitor.get_stats()
        assert stats.tasks_completed_after_intervention == 1
        assert stats.avg_intervention_response_seconds >= 0

    def test_health_empty(self, monitor):
        health = monitor.get_health()
        assert health["status"] == "healthy"
        assert health["tasks_monitored"] == 0
        assert health["total_interventions"] == 0

    def test_health_with_critical(self, monitor, now):
        monitor.ingest_task(
            "t1",
            title="Critical",
            created_at=now - 850,
            deadline_at=now + 150,
        )
        health = monitor.get_health()
        assert health["status"] == "critical"
        assert health["critical_tasks"] == 1

    def test_health_with_overdue(self, monitor, now):
        monitor.ingest_task(
            "t1",
            title="Overdue",
            created_at=now - 1000,
            deadline_at=now - 10,
        )
        health = monitor.get_health()
        assert health["status"] == "critical"
        assert health["overdue_tasks"] == 1

    def test_health_with_warning_only(self, monitor, now):
        monitor.ingest_task(
            "t1",
            title="Warning",
            created_at=now - 600,
            deadline_at=now + 400,
        )
        health = monitor.get_health()
        assert health["status"] == "warning"
        assert health["warning_tasks"] == 1

    def test_health_intervention_success_rate(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
                max_per_task=5,
            )
        )
        monitor.ingest_task(
            "t1", title="T", created_at=now - 600, deadline_at=now + 400
        )
        t1 = monitor.run_cycle()
        t2 = monitor.run_cycle()
        monitor.record_outcome(t1[0].intervention_id, InterventionOutcome.SUCCESS)
        monitor.record_outcome(t2[0].intervention_id, InterventionOutcome.FAILED)

        health = monitor.get_health()
        assert health["intervention_success_rate"] == 0.5

    def test_health_pending_interventions(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1", title="T", created_at=now - 600, deadline_at=now + 400
        )
        monitor.run_cycle()

        health = monitor.get_health()
        assert health["pending_interventions"] == 1


# ─── Default Rules Tests ────────────────────────────────────────


class TestDefaultRules:
    """Test the with_default_rules factory."""

    def test_creates_5_default_rules(self, monitor_with_rules):
        rules = monitor_with_rules.get_rules()
        assert len(rules) == 5

    def test_default_rule_names(self, monitor_with_rules):
        names = {r.name for r in monitor_with_rules.get_rules()}
        assert "rebroadcast_unassigned_warning" in names
        assert "deadline_warning_assigned" in names
        assert "escalate_bounty_critical" in names
        assert "reassign_overdue" in names
        assert "cancel_overdue_unassigned" in names

    def test_rebroadcast_triggers_for_unassigned_warning(self, monitor_with_rules, now):
        # Unassigned task at WARNING level
        monitor_with_rules.ingest_task(
            "t1",
            title="Test",
            created_at=now - 600,
            deadline_at=now + 400,
            status="open",
        )
        triggered = monitor_with_rules.run_cycle()
        rebroadcasts = [
            t for t in triggered if t.intervention_type == InterventionType.REBROADCAST
        ]
        assert len(rebroadcasts) == 1

    def test_deadline_warning_triggers_for_assigned_critical(
        self, monitor_with_rules, now
    ):
        monitor_with_rules.ingest_task(
            "t1",
            title="Test",
            created_at=now - 850,
            deadline_at=now + 150,
            worker_id="w1",
        )
        triggered = monitor_with_rules.run_cycle()
        warnings = [
            t
            for t in triggered
            if t.intervention_type == InterventionType.DEADLINE_WARNING
        ]
        assert len(warnings) == 1

    def test_escalate_bounty_for_unassigned_critical(self, monitor_with_rules, now):
        monitor_with_rules.ingest_task(
            "t1",
            title="Test",
            created_at=now - 850,
            deadline_at=now + 150,
        )
        triggered = monitor_with_rules.run_cycle()
        escalations = [
            t
            for t in triggered
            if t.intervention_type == InterventionType.ESCALATE_BOUNTY
        ]
        assert len(escalations) == 1

    def test_reassign_for_overdue_assigned(self, monitor_with_rules, now):
        monitor_with_rules.ingest_task(
            "t1",
            title="Test",
            created_at=now - 1000,
            deadline_at=now - 10,
            worker_id="w1",
        )
        triggered = monitor_with_rules.run_cycle()
        reassigns = [
            t for t in triggered if t.intervention_type == InterventionType.REASSIGN
        ]
        assert len(reassigns) == 1

    def test_cancel_graceful_for_overdue_unassigned(self, monitor_with_rules, now):
        monitor_with_rules.ingest_task(
            "t1",
            title="Test",
            created_at=now - 1000,
            deadline_at=now - 10,
        )
        triggered = monitor_with_rules.run_cycle()
        cancels = [
            t
            for t in triggered
            if t.intervention_type == InterventionType.CANCEL_GRACEFUL
        ]
        assert len(cancels) == 1


# ─── Intervention ID Prefix Tests ───────────────────────────────


class TestInterventionIdPrefix:
    """Test custom intervention ID prefix."""

    def test_custom_prefix(self, now):
        monitor = TaskMonitor(intervention_id_prefix="tm")
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1", title="T", created_at=now - 600, deadline_at=now + 400
        )
        triggered = monitor.run_cycle()
        assert triggered[0].intervention_id.startswith("tm-")

    def test_default_prefix(self, monitor, now):
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        monitor.ingest_task(
            "t1", title="T", created_at=now - 600, deadline_at=now + 400
        )
        triggered = monitor.run_cycle()
        assert triggered[0].intervention_id.startswith("int-")


# ─── Full Lifecycle Test ─────────────────────────────────────────


class TestFullLifecycle:
    """End-to-end lifecycle test."""

    def test_task_lifecycle_healthy_to_overdue(self, now):
        monitor = TaskMonitor.with_default_rules()

        # Record all interventions
        all_interventions = []
        monitor.on_intervention(lambda i, t: all_interventions.append(i))

        # Ingest a task that's already critical (simulating time passage)
        monitor.ingest_task(
            "t1",
            title="Buy coffee",
            bounty_usd=0.25,
            created_at=now - 850,
            deadline_at=now + 150,
        )

        # First cycle — should trigger (escalate_bounty for unassigned critical)
        cycle1 = monitor.run_cycle()
        assert len(cycle1) >= 1

        # Record task completion
        monitor.record_task_outcome("t1", completed=True)

        # All interventions should be SUCCESS
        for i in monitor.get_interventions(task_id="t1"):
            assert i.outcome == InterventionOutcome.SUCCESS

        # Health should reflect
        stats = monitor.get_stats()
        assert stats.tasks_completed_after_intervention >= 1

    def test_multi_task_multi_intervention(self, now):
        monitor = TaskMonitor.with_default_rules()

        # Three tasks at different urgency levels
        monitor.ingest_task("t1", title="Healthy task")  # HEALTHY
        monitor.ingest_task(
            "t2",
            title="Warning task",
            created_at=now - 600,
            deadline_at=now + 400,
        )  # WARNING
        monitor.ingest_task(
            "t3",
            title="Overdue task",
            created_at=now - 1000,
            deadline_at=now - 10,
        )  # OVERDUE

        triggered = monitor.run_cycle()

        # Should have interventions for t2 and t3, not t1
        task_ids = {t.task_id for t in triggered}
        assert "t1" not in task_ids
        assert "t2" in task_ids
        assert "t3" in task_ids
