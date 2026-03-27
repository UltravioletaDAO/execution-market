"""
Tests for SwarmRunner — Production daemon loop for KK V2 swarm.

Covers:
  1. RunMode & Phase enums
  2. CycleResult construction & summary
  3. RunnerState persistence
  4. SwarmRunner lifecycle (start/stop/run_once)
  5. 7-phase cycle execution
  6. State management (load/save)
  7. Task deduplication & known_task_ids cap
  8. Status & diagnostics
  9. Error handling per phase
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from mcp_server.swarm.runner import (
    SwarmRunner,
    RunMode,
    Phase,
    CycleResult,
    RunnerState,
)


# ─── Helpers ──────────────────────────────────────────────────

def make_mock_coordinator():
    """Create a mock SwarmCoordinator with required attributes."""
    coord = MagicMock()
    coord.em_client = MagicMock()
    coord.em_client.list_tasks.return_value = []
    coord.em_client.get_health.return_value = {"status": "healthy"}
    coord.lifecycle = MagicMock()
    coord.lifecycle.agents = {}
    coord.get_queue_summary.return_value = {"pending": 0, "assigned": 0}
    coord.process_task_queue.return_value = {"assigned": 0, "failed": 0}
    coord.run_health_checks.return_value = {"agents": {"checked": 0, "degraded": 0}}
    coord.get_dashboard.return_value = {}
    return coord


def make_runner(mode="passive", **kwargs):
    """Create a SwarmRunner with mocks."""
    coord = make_mock_coordinator()
    state_dir = kwargs.pop("state_dir", tempfile.mkdtemp())
    return SwarmRunner(
        coordinator=coord,
        event_listener=MagicMock(),
        evidence_parser=MagicMock(),
        worker_registry=MagicMock(),
        mode=RunMode(mode),
        cycle_interval_seconds=0.01,
        state_dir=state_dir,
        **kwargs,
    )


# ─── Section 1: Enums ────────────────────────────────────────

class TestEnums:
    def test_run_modes(self):
        assert RunMode.PASSIVE.value == "passive"
        assert RunMode.ACTIVE.value == "active"
        assert RunMode.DRY_RUN.value == "dry_run"

    def test_phases(self):
        assert len(Phase) == 7
        assert Phase.DISCOVER.value == "discover"
        assert Phase.REPORT.value == "report"

    def test_phase_order(self):
        expected = ["discover", "enrich", "route", "monitor", "collect", "learn", "report"]
        actual = [p.value for p in Phase]
        assert actual == expected


# ─── Section 2: CycleResult ──────────────────────────────────

class TestCycleResult:
    def test_default_values(self):
        r = CycleResult()
        assert r.cycle_number == 0
        assert r.tasks_discovered == 0
        assert r.bounty_earned_usd == 0.0
        assert r.errors == []

    def test_summary_line_empty(self):
        r = CycleResult(cycle_number=1, duration_ms=45.2)
        line = r.summary_line()
        assert "Cycle #1" in line
        assert "45ms" in line

    def test_summary_line_with_data(self):
        r = CycleResult(
            cycle_number=5,
            tasks_new=3,
            tasks_routed=2,
            tasks_completed=1,
            bounty_earned_usd=5.50,
            duration_ms=120.0,
        )
        line = r.summary_line()
        assert "+3 tasks" in line
        assert "2 routed" in line
        assert "$5.50" in line

    def test_summary_line_with_errors(self):
        r = CycleResult(
            cycle_number=1,
            errors=["discover: API timeout"],
            duration_ms=10.0,
        )
        line = r.summary_line()
        assert "1 errors" in line

    def test_summary_line_with_degraded(self):
        r = CycleResult(
            cycle_number=1,
            agents_degraded=2,
            duration_ms=10.0,
        )
        line = r.summary_line()
        assert "2 degraded" in line

    def test_to_dict(self):
        r = CycleResult(cycle_number=3, tasks_new=5)
        d = r.to_dict()
        assert d["cycle_number"] == 3
        assert d["tasks_new"] == 5
        assert isinstance(d, dict)


# ─── Section 3: RunnerState ──────────────────────────────────

class TestRunnerState:
    def test_default_state(self):
        s = RunnerState()
        assert s.total_cycles == 0
        assert s.total_bounty_earned_usd == 0.0

    def test_to_dict(self):
        s = RunnerState(total_cycles=10, total_bounty_earned_usd=25.50)
        d = s.to_dict()
        assert d["total_cycles"] == 10
        assert d["total_bounty_earned_usd"] == 25.50

    def test_from_dict(self):
        data = {
            "total_cycles": 100,
            "total_tasks_routed": 50,
            "total_bounty_earned_usd": 150.0,
            "started_at": "2026-03-27T00:00:00Z",
        }
        s = RunnerState.from_dict(data)
        assert s.total_cycles == 100
        assert s.total_tasks_routed == 50

    def test_from_dict_ignores_unknown_fields(self):
        data = {"total_cycles": 5, "unknown_field": True}
        s = RunnerState.from_dict(data)
        assert s.total_cycles == 5
        assert not hasattr(s, "unknown_field")

    def test_roundtrip(self):
        original = RunnerState(
            total_cycles=42,
            total_bounty_earned_usd=99.99,
            started_at="2026-01-01T00:00:00Z",
        )
        d = original.to_dict()
        restored = RunnerState.from_dict(d)
        assert restored.total_cycles == original.total_cycles
        assert restored.total_bounty_earned_usd == original.total_bounty_earned_usd


# ─── Section 4: SwarmRunner Lifecycle ─────────────────────────

class TestRunnerLifecycle:
    def test_run_once_returns_cycle_result(self):
        runner = make_runner()
        result = runner.run_once()
        assert isinstance(result, CycleResult)
        assert result.cycle_number == 1

    def test_run_once_increments_state(self):
        runner = make_runner()
        runner.run_once()
        assert runner._state.total_cycles == 1
        runner.run_once()
        assert runner._state.total_cycles == 2

    def test_stop_sets_flag(self):
        runner = make_runner()
        runner._running = True
        runner.stop()
        assert runner._running is False

    def test_max_cycles_stops_run(self):
        runner = make_runner(max_cycles=3)
        runner.run()  # Should stop after 3 cycles
        assert runner._state.total_cycles == 3

    def test_passive_mode(self):
        runner = make_runner(mode="passive")
        result = runner.run_once()
        # In passive mode, no tasks should be routed
        assert result.tasks_routed == 0

    def test_dry_run_mode(self):
        runner = make_runner(mode="dry_run")
        runner.coordinator.get_queue_summary.return_value = {"pending": 5}
        result = runner.run_once()
        # Dry run reports pending but doesn't call process_task_queue
        assert result.tasks_routed == 5
        runner.coordinator.process_task_queue.assert_not_called()


# ─── Section 5: 7-Phase Execution ────────────────────────────

class TestPhaseExecution:
    def test_all_phases_complete(self):
        runner = make_runner()
        result = runner.run_once()
        assert len(result.phases_completed) == 7
        assert result.phases_failed == []

    def test_discover_phase_finds_tasks(self):
        runner = make_runner()
        runner.coordinator.em_client.list_tasks.return_value = [
            {"id": "t1", "title": "Task 1", "category": "delivery", "bounty_amount": 5.0},
            {"id": "t2", "title": "Task 2", "category": "photo", "bounty_amount": 3.0},
        ]
        result = runner.run_once()
        assert result.tasks_discovered == 2
        assert result.tasks_new == 2

    def test_discover_deduplicates(self):
        runner = make_runner()
        tasks = [{"id": "t1", "title": "Task 1", "category": "test"}]
        runner.coordinator.em_client.list_tasks.return_value = tasks

        r1 = runner.run_once()
        assert r1.tasks_new == 1

        r2 = runner.run_once()
        assert r2.tasks_new == 0  # Same task, already known

    def test_monitor_phase_counts_agents(self):
        runner = make_runner()
        
        # Create mock agents with state
        agent1 = MagicMock()
        agent1.state = MagicMock(value="active")
        agent2 = MagicMock()
        agent2.state = MagicMock(value="suspended")

        runner.coordinator.lifecycle.agents = {
            "a1": agent1,
            "a2": agent2,
        }

        result = runner.run_once()
        assert result.agents_active == 1
        assert result.agents_suspended == 1

    def test_report_phase_checks_health(self):
        runner = make_runner()
        runner.coordinator.em_client.get_health.return_value = {"status": "healthy"}
        result = runner.run_once()
        assert result.em_api_healthy is True

    def test_report_phase_unhealthy(self):
        runner = make_runner()
        runner.coordinator.em_client.get_health.return_value = {"status": "degraded"}
        result = runner.run_once()
        assert result.em_api_healthy is False

    def test_collect_phase_counts_completed(self):
        runner = make_runner()
        runner.coordinator.em_client.list_tasks.side_effect = [
            [],  # discover: published tasks
            [{"id": "t1", "bounty_amount": 5.0}],  # collect: completed
            [],  # collect: disputed
            [],  # learn: completed
        ]
        result = runner.run_once()
        assert result.tasks_completed == 1


# ─── Section 6: State Management ─────────────────────────────

class TestStateManagement:
    def test_state_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = make_runner(state_dir=tmpdir)
            runner.run_once()

            state_file = os.path.join(tmpdir, "runner_state.json")
            assert os.path.exists(state_file)

            data = json.loads(open(state_file).read())
            assert data["total_cycles"] == 1

    def test_state_loads_from_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write initial state
            state_file = os.path.join(tmpdir, "runner_state.json")
            with open(state_file, "w") as f:
                json.dump({"total_cycles": 50, "total_bounty_earned_usd": 100.0}, f)

            runner = make_runner(state_dir=tmpdir)
            runner._load_state()
            assert runner._state.total_cycles == 50
            assert runner._state.total_bounty_earned_usd == 100.0

    def test_state_load_handles_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = make_runner(state_dir=tmpdir)
            runner._load_state()  # Should not raise
            assert runner._state.total_cycles == 0

    def test_state_accumulates(self):
        runner = make_runner()
        runner.run_once()
        runner.run_once()
        runner.run_once()
        assert runner._state.total_cycles == 3


# ─── Section 7: Task Deduplication ────────────────────────────

class TestTaskDeduplication:
    def test_known_tasks_cap(self):
        runner = make_runner()
        runner._max_known_tasks = 5

        # Add 10 tasks
        for i in range(10):
            runner._known_task_ids.add(f"task_{i}")

        # Run a cycle that triggers the cap logic
        runner.coordinator.em_client.list_tasks.return_value = [
            {"id": f"task_{i}", "category": "test"} for i in range(10, 15)
        ]
        runner.run_once()

        # Should be capped
        assert len(runner._known_task_ids) <= runner._max_known_tasks + 5

    def test_empty_task_id_skipped(self):
        runner = make_runner()
        runner.coordinator.em_client.list_tasks.return_value = [
            {"id": "", "title": "No ID task"},
        ]
        result = runner.run_once()
        assert result.tasks_new == 0


# ─── Section 8: Status & Diagnostics ─────────────────────────

class TestDiagnostics:
    def test_get_status(self):
        runner = make_runner()
        runner.run_once()
        status = runner.get_status()
        assert "running" in status
        assert "mode" in status
        assert status["mode"] == "passive"
        assert "state" in status
        assert "known_tasks" in status

    def test_get_cycle_history(self):
        runner = make_runner()
        runner.run_once()
        runner.run_once()
        history = runner.get_cycle_history(limit=5)
        assert len(history) == 2
        assert history[0]["cycle_number"] == 1
        assert history[1]["cycle_number"] == 2

    def test_cycle_history_capped(self):
        runner = make_runner()
        runner._max_cycle_history = 3
        for _ in range(10):
            runner.run_once()
        assert len(runner._cycle_history) <= 3


# ─── Section 9: Error Handling ────────────────────────────────

class TestErrorHandling:
    def test_discover_error_recorded(self):
        runner = make_runner()
        runner.coordinator.em_client.list_tasks.side_effect = RuntimeError("API down")
        result = runner.run_once()
        assert "discover" in result.phases_failed
        assert len(result.errors) >= 1
        assert "discover" in result.errors[0]

    def test_other_phases_continue_after_error(self):
        runner = make_runner()
        runner.coordinator.em_client.list_tasks.side_effect = RuntimeError("boom")
        result = runner.run_once()
        # Discover fails but other phases should still run
        assert "discover" in result.phases_failed
        # Monitor, report etc should still complete
        assert len(result.phases_completed) > 0

    def test_state_save_failure_handled(self):
        runner = make_runner(state_dir="/nonexistent/path/deep/nested")
        # Should not raise, just log warning
        runner._save_state()

    def test_learn_phase_handles_missing_worker(self):
        runner = make_runner()
        runner.coordinator.em_client.list_tasks.side_effect = [
            [],  # discover
            [],  # collect completed
            [],  # collect disputed
            [{"id": "t1", "worker_wallet": "", "category": "test"}],  # learn
        ]
        result = runner.run_once()
        # Should not crash, just skip workers without wallets
        assert result.skill_updates == 0
