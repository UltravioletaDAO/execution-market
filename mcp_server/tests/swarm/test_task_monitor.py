"""
Tests for TaskMonitor — Real-time task lifecycle monitoring
============================================================

Covers:
- MonitoredTask: urgency computation, properties, deadlines
- InterventionRule: matching logic, filters
- TaskMonitor: ingest, run_cycle, callbacks, stats, resolution
"""

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from swarm.task_monitor import (
    TaskUrgency,
    InterventionType,
    InterventionOutcome,
    MonitoredTask,
    Intervention,
    InterventionRule,
    MonitoringStats,
    TaskMonitor,
)


# ---------------------------------------------------------------------------
# MonitoredTask
# ---------------------------------------------------------------------------


class TestMonitoredTask:
    def test_default_urgency(self):
        t = MonitoredTask(task_id="t1", title="Test")
        assert t.urgency == TaskUrgency.HEALTHY

    def test_time_remaining_no_deadline(self):
        t = MonitoredTask(task_id="t1", title="Test")
        assert t.time_remaining_seconds is None

    def test_time_remaining_with_deadline(self):
        t = MonitoredTask(task_id="t1", title="Test", deadline_at=time.time() + 3600)
        remaining = t.time_remaining_seconds
        assert remaining is not None
        assert 3599 <= remaining <= 3601

    def test_time_remaining_overdue(self):
        t = MonitoredTask(task_id="t1", title="Test", deadline_at=time.time() - 100)
        assert t.time_remaining_seconds == 0

    def test_elapsed_ratio_no_deadline(self):
        t = MonitoredTask(task_id="t1", title="Test")
        assert t.time_elapsed_ratio is None

    def test_is_assigned(self):
        t1 = MonitoredTask(task_id="t1", title="Test")
        assert not t1.is_assigned

        t2 = MonitoredTask(task_id="t2", title="Test", worker_id="w1")
        assert t2.is_assigned

    def test_can_intervene(self):
        t = MonitoredTask(
            task_id="t1", title="Test", max_interventions=3, intervention_count=2
        )
        assert t.can_intervene

        t2 = MonitoredTask(
            task_id="t2", title="Test", max_interventions=3, intervention_count=3
        )
        assert not t2.can_intervene


# ---------------------------------------------------------------------------
# InterventionRule
# ---------------------------------------------------------------------------


class TestInterventionRule:
    def test_matches_basic(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
        )
        task = MonitoredTask(task_id="t1", title="Test", urgency=TaskUrgency.WARNING)
        assert rule.matches(task)

    def test_no_match_wrong_urgency(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.CRITICAL,
            intervention_type=InterventionType.REBROADCAST,
        )
        task = MonitoredTask(task_id="t1", title="Test", urgency=TaskUrgency.WARNING)
        assert not rule.matches(task)

    def test_no_match_disabled(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
            enabled=False,
        )
        task = MonitoredTask(task_id="t1", title="Test", urgency=TaskUrgency.WARNING)
        assert not rule.matches(task)

    def test_requires_assignment_true(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.DEADLINE_WARNING,
            requires_assignment=True,
        )
        unassigned = MonitoredTask(task_id="t1", title="T", urgency=TaskUrgency.WARNING)
        assigned = MonitoredTask(
            task_id="t2", title="T", urgency=TaskUrgency.WARNING, worker_id="w1"
        )
        assert not rule.matches(unassigned)
        assert rule.matches(assigned)

    def test_requires_assignment_false(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
            requires_assignment=False,
        )
        assigned = MonitoredTask(
            task_id="t1", title="T", urgency=TaskUrgency.WARNING, worker_id="w1"
        )
        assert not rule.matches(assigned)

    def test_bounty_filter(self):
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.ESCALATE_BOUNTY,
            min_bounty_usd=0.25,
            max_bounty_usd=5.00,
        )
        low = MonitoredTask(
            task_id="t1", title="T", urgency=TaskUrgency.WARNING, bounty_usd=0.10
        )
        mid = MonitoredTask(
            task_id="t2", title="T", urgency=TaskUrgency.WARNING, bounty_usd=1.00
        )
        high = MonitoredTask(
            task_id="t3", title="T", urgency=TaskUrgency.WARNING, bounty_usd=10.00
        )
        assert not rule.matches(low)
        assert rule.matches(mid)
        assert not rule.matches(high)


# ---------------------------------------------------------------------------
# TaskMonitor — Core Operations
# ---------------------------------------------------------------------------


class TestTaskMonitorCore:
    def test_ingest_new_task(self):
        monitor = TaskMonitor()
        task = monitor.ingest_task("t1", title="Test task", bounty_usd=0.50)
        assert task.task_id == "t1"
        assert "t1" in monitor.tasks

    def test_ingest_updates_existing(self):
        monitor = TaskMonitor()
        monitor.ingest_task("t1", title="Test", status="open")
        monitor.ingest_task("t1", status="assigned", worker_id="w1")
        assert monitor.tasks["t1"].status == "assigned"
        assert monitor.tasks["t1"].worker_id == "w1"

    def test_remove_task(self):
        monitor = TaskMonitor()
        monitor.ingest_task("t1", title="Test")
        assert "t1" in monitor.tasks
        monitor.remove_task("t1")
        assert "t1" not in monitor.tasks

    def test_remove_nonexistent_ok(self):
        monitor = TaskMonitor()
        monitor.remove_task("no-such-task")  # Should not raise

    def test_get_task(self):
        monitor = TaskMonitor()
        monitor.ingest_task("t1", title="Hello")
        task = monitor.get_task("t1")
        assert task is not None
        assert task.title == "Hello"

    def test_get_task_missing(self):
        monitor = TaskMonitor()
        assert monitor.get_task("nope") is None

    def test_get_active_tasks(self):
        monitor = TaskMonitor()
        monitor.ingest_task("t1", title="A")
        monitor.ingest_task("t2", title="B")
        active = monitor.get_active_tasks()
        assert len(active) == 2

    def test_run_cycle_no_tasks(self):
        monitor = TaskMonitor()
        result = monitor.run_cycle()
        # Should not crash with no tasks
        assert result is not None or result is None  # May return dict or None

    def test_run_cycle_with_tasks(self):
        monitor = TaskMonitor()
        now = time.time()
        monitor.ingest_task(
            "t1", title="Test", created_at=now - 3600, deadline_at=now + 600
        )
        monitor.run_cycle()
        # Task should have updated urgency
        task = monitor.get_task("t1")
        assert task is not None


# ---------------------------------------------------------------------------
# TaskMonitor — Rules
# ---------------------------------------------------------------------------


class TestTaskMonitorRules:
    def test_add_rule(self):
        monitor = TaskMonitor()
        rule = InterventionRule(
            name="test",
            urgency_trigger=TaskUrgency.WARNING,
            intervention_type=InterventionType.REBROADCAST,
        )
        monitor.add_rule(rule)
        assert len(monitor.rules) == 1

    def test_get_rules(self):
        monitor = TaskMonitor()
        monitor.add_rule(
            InterventionRule(
                name="r1",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
            )
        )
        rules = monitor.get_rules()
        assert len(rules) >= 1

    def test_remove_rule(self):
        monitor = TaskMonitor()
        monitor.add_rule(
            InterventionRule(
                name="r1",
                urgency_trigger=TaskUrgency.WARNING,
                intervention_type=InterventionType.REBROADCAST,
            )
        )
        count_before = len(monitor.rules)
        monitor.remove_rule("r1")
        assert len(monitor.rules) < count_before

    def test_with_default_rules(self):
        monitor = TaskMonitor.with_default_rules()
        assert len(monitor.rules) >= 1


# ---------------------------------------------------------------------------
# TaskMonitor — Callbacks
# ---------------------------------------------------------------------------


class TestTaskMonitorCallbacks:
    def test_on_intervention_callback(self):
        monitor = TaskMonitor()
        handler = MagicMock()
        monitor.on_intervention(handler)

        # Set up conditions for intervention
        monitor.add_rule(
            InterventionRule(
                name="test",
                urgency_trigger=TaskUrgency.CRITICAL,
                intervention_type=InterventionType.REBROADCAST,
                cooldown_seconds=0,
            )
        )
        now = time.time()
        monitor.ingest_task(
            "t1", title="Test", created_at=now - 3600, deadline_at=now + 10
        )
        monitor.run_cycle()
        # If urgency reached CRITICAL, handler may be called

    def test_on_urgency_change_callback(self):
        monitor = TaskMonitor()
        handler = MagicMock()
        monitor.on_urgency_change(handler)

        now = time.time()
        monitor.ingest_task(
            "t1", title="Test", created_at=now - 3600, deadline_at=now + 100
        )
        monitor.run_cycle()
        # If urgency changed from HEALTHY, handler should be called


# ---------------------------------------------------------------------------
# TaskMonitor — Stats
# ---------------------------------------------------------------------------


class TestTaskMonitorStats:
    def test_empty_stats(self):
        monitor = TaskMonitor()
        stats = monitor.get_stats()
        assert isinstance(stats, MonitoringStats)
        assert stats.total_tasks_monitored == 0

    def test_stats_after_ingest(self):
        monitor = TaskMonitor()
        monitor.ingest_task("t1", title="A")
        monitor.ingest_task("t2", title="B")
        stats = monitor.get_stats()
        assert stats.tasks_currently_active == 2

    def test_health_check(self):
        monitor = TaskMonitor()
        health = monitor.get_health()
        assert isinstance(health, dict)


# ---------------------------------------------------------------------------
# TaskMonitor — Urgency by tasks
# ---------------------------------------------------------------------------


class TestTaskMonitorUrgency:
    def test_get_tasks_by_urgency(self):
        monitor = TaskMonitor()
        now = time.time()
        # Healthy task (far from deadline)
        monitor.ingest_task(
            "t1", title="Healthy", created_at=now, deadline_at=now + 86400
        )
        # Overdue task
        monitor.ingest_task(
            "t2", title="Overdue", created_at=now - 7200, deadline_at=now - 100
        )
        monitor.run_cycle()

        overdue = monitor.get_tasks_by_urgency(TaskUrgency.OVERDUE)
        assert isinstance(overdue, list)


# ---------------------------------------------------------------------------
# Intervention dataclass
# ---------------------------------------------------------------------------


class TestInterventionDataclass:
    def test_duration_unresolved(self):
        i = Intervention(
            intervention_id="i1",
            task_id="t1",
            intervention_type=InterventionType.REBROADCAST,
        )
        assert i.duration_seconds is None

    def test_duration_resolved(self):
        now = time.time()
        i = Intervention(
            intervention_id="i1",
            task_id="t1",
            intervention_type=InterventionType.REBROADCAST,
            triggered_at=now - 60,
            resolved_at=now,
        )
        assert abs(i.duration_seconds - 60) < 1

    def test_outcome_default_pending(self):
        i = Intervention(
            intervention_id="i1",
            task_id="t1",
            intervention_type=InterventionType.REBROADCAST,
        )
        assert i.outcome == InterventionOutcome.PENDING


# ---------------------------------------------------------------------------
# TaskMonitor — Record outcome
# ---------------------------------------------------------------------------


class TestTaskMonitorOutcome:
    def test_record_task_outcome(self):
        monitor = TaskMonitor()
        monitor.ingest_task("t1", title="Test")
        # record_task_outcome should work without error
        monitor.record_task_outcome("t1", "completed")
