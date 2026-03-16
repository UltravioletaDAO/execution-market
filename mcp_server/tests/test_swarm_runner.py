"""Tests for SwarmRunner — the 7-phase daemon loop."""

import json
import os
import tempfile


from swarm.runner import (
    SwarmRunner,
    RunMode,
    CycleResult,
    RunnerState,
)
from swarm.coordinator import SwarmCoordinator
from swarm.lifecycle_manager import LifecycleManager
from swarm.orchestrator import SwarmOrchestrator
from swarm.reputation_bridge import ReputationBridge


# ── Fixtures ──────────────────────────────────────────────────────────


class MockEMApiClient:
    """Mock EM API client for testing."""

    def __init__(self):
        self.base_url = "https://api.execution.market"
        self.tasks = {
            "published": [],
            "completed": [],
            "failed": [],
        }
        self.health = {"status": "healthy"}
        self.api_key = None

    def get_health(self):
        return self.health

    def list_tasks(self, status="published", limit=50, category=None):
        return self.tasks.get(status, [])[:limit]

    def get_task(self, task_id):
        for tasks in self.tasks.values():
            for t in tasks:
                if str(t.get("id")) == str(task_id):
                    return t
        return None

    def apply_to_task(self, task_id, agent_id, message=""):
        return {"success": True}

    def submit_evidence(self, task_id, evidence_type, content, metadata=None):
        return {"success": True}

    def get_agent_identity(self, agent_id):
        return {"agent_id": agent_id, "registered": True}

    def get_task_stats(self):
        return {"total": len(self.tasks.get("published", []))}


def make_coordinator(mock_em=None):
    """Create a SwarmCoordinator with mock EM client."""
    bridge = ReputationBridge()
    lifecycle = LifecycleManager()
    orchestrator = SwarmOrchestrator(bridge=bridge, lifecycle=lifecycle)
    coordinator = SwarmCoordinator(
        bridge=bridge,
        lifecycle=lifecycle,
        orchestrator=orchestrator,
    )
    coordinator.em_client = mock_em or MockEMApiClient()
    return coordinator


def make_runner(mock_em=None, mode="passive", state_dir=None, max_cycles=1):
    """Create a SwarmRunner with mock dependencies."""
    coordinator = make_coordinator(mock_em)
    return SwarmRunner(
        coordinator=coordinator,
        mode=RunMode(mode),
        cycle_interval_seconds=0.1,
        state_dir=state_dir or tempfile.mkdtemp(),
        max_tasks_per_cycle=10,
        max_cycles=max_cycles,
    )


# ── CycleResult Tests ────────────────────────────────────────────────


class TestCycleResult:
    """Tests for CycleResult data class."""

    def test_default_values(self):
        result = CycleResult()
        assert result.cycle_number == 0
        assert result.tasks_discovered == 0
        assert result.tasks_new == 0
        assert result.errors == []
        assert result.phases_completed == []

    def test_to_dict(self):
        result = CycleResult(cycle_number=5, tasks_new=3)
        d = result.to_dict()
        assert d["cycle_number"] == 5
        assert d["tasks_new"] == 3
        assert isinstance(d, dict)

    def test_summary_line_empty(self):
        result = CycleResult(cycle_number=1, duration_ms=50)
        summary = result.summary_line()
        assert "Cycle #1" in summary
        assert "50ms" in summary

    def test_summary_line_with_activity(self):
        result = CycleResult(
            cycle_number=5,
            tasks_new=3,
            tasks_routed=2,
            tasks_completed=1,
            bounty_earned_usd=5.50,
            duration_ms=150,
        )
        summary = result.summary_line()
        assert "+3 tasks" in summary
        assert "2 routed" in summary
        assert "1 completed" in summary
        assert "$5.50 earned" in summary

    def test_summary_line_with_errors(self):
        result = CycleResult(
            cycle_number=1,
            errors=["err1", "err2"],
            duration_ms=10,
        )
        summary = result.summary_line()
        assert "2 errors" in summary

    def test_summary_line_with_degraded(self):
        result = CycleResult(
            cycle_number=1,
            agents_degraded=2,
            duration_ms=10,
        )
        summary = result.summary_line()
        assert "2 degraded" in summary


# ── RunnerState Tests ─────────────────────────────────────────────────


class TestRunnerState:
    """Tests for RunnerState persistence."""

    def test_default_values(self):
        state = RunnerState()
        assert state.total_cycles == 0
        assert state.total_tasks_routed == 0
        assert state.total_bounty_earned_usd == 0

    def test_to_dict_and_back(self):
        state = RunnerState(
            total_cycles=100,
            total_tasks_routed=50,
            total_bounty_earned_usd=125.75,
        )
        d = state.to_dict()
        restored = RunnerState.from_dict(d)
        assert restored.total_cycles == 100
        assert restored.total_tasks_routed == 50
        assert restored.total_bounty_earned_usd == 125.75

    def test_from_dict_ignores_unknown_keys(self):
        d = {"total_cycles": 5, "unknown_key": "value"}
        state = RunnerState.from_dict(d)
        assert state.total_cycles == 5


# ── SwarmRunner Creation Tests ────────────────────────────────────────


class TestRunnerCreation:
    """Tests for SwarmRunner initialization."""

    def test_create_passive(self):
        runner = make_runner(mode="passive")
        assert runner.mode == RunMode.PASSIVE
        assert runner.coordinator is not None

    def test_create_active(self):
        runner = make_runner(mode="active")
        assert runner.mode == RunMode.ACTIVE

    def test_create_dry_run(self):
        runner = make_runner(mode="dry_run")
        assert runner.mode == RunMode.DRY_RUN

    def test_default_cycle_interval(self):
        runner = make_runner()
        assert runner.cycle_interval == 0.1  # test override

    def test_max_tasks_per_cycle(self):
        runner = make_runner()
        assert runner.max_tasks_per_cycle == 10


# ── Phase 1: Discover Tests ──────────────────────────────────────────


class TestPhaseDiscover:
    """Tests for the task discovery phase."""

    def test_discover_no_tasks(self):
        runner = make_runner()
        result = CycleResult()
        runner._phase_discover(result)
        assert result.tasks_discovered == 0
        assert result.tasks_new == 0

    def test_discover_new_tasks(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["published"] = [
            {
                "id": "task-1",
                "title": "Test Task 1",
                "category": "simple_action",
                "bounty_amount": 1.0,
            },
            {
                "id": "task-2",
                "title": "Test Task 2",
                "category": "data_collection",
                "bounty_amount": 2.5,
            },
        ]

        runner = make_runner(mock_em=mock_em)
        result = CycleResult()
        runner._phase_discover(result)

        assert result.tasks_discovered == 2
        assert result.tasks_new == 2

    def test_discover_deduplicates(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["published"] = [
            {
                "id": "task-1",
                "title": "Test",
                "category": "simple_action",
                "bounty_amount": 1.0,
            },
        ]

        runner = make_runner(mock_em=mock_em)

        # First cycle
        result1 = CycleResult()
        runner._phase_discover(result1)
        assert result1.tasks_new == 1

        # Second cycle — same task should not be new
        result2 = CycleResult()
        runner._phase_discover(result2)
        assert result2.tasks_discovered == 1
        assert result2.tasks_new == 0

    def test_discover_no_em_client(self):
        runner = make_runner()
        runner.coordinator.em_client = None
        result = CycleResult()
        runner._phase_discover(result)
        assert result.tasks_discovered == 0


# ── Phase 3: Route Tests ──────────────────────────────────────────────


class TestPhaseRoute:
    """Tests for the task routing phase."""

    def test_passive_mode_no_routing(self):
        runner = make_runner(mode="passive")
        result = CycleResult()
        runner._phase_route(result)
        assert result.tasks_routed == 0

    def test_dry_run_mode_counts(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["published"] = [
            {
                "id": "task-1",
                "title": "Test",
                "category": "simple_action",
                "bounty_amount": 1.0,
            },
        ]

        runner = make_runner(mock_em=mock_em, mode="dry_run")

        # First discover
        discover_result = CycleResult()
        runner._phase_discover(discover_result)

        # Then route
        route_result = CycleResult()
        runner._phase_route(route_result)
        # In dry run, it reports pending count


# ── Phase 4: Monitor Tests ────────────────────────────────────────────


class TestPhaseMonitor:
    """Tests for the health monitoring phase."""

    def test_monitor_no_agents(self):
        runner = make_runner()
        result = CycleResult()
        runner._phase_monitor(result)
        assert result.agents_active == 0
        assert result.agents_degraded == 0

    def test_monitor_with_agents(self):
        runner = make_runner()
        # Register some agents
        runner.coordinator.register_agent(
            agent_id=1, wallet_address="0x1111", name="agent-1"
        )
        runner.coordinator.register_agent(
            agent_id=2, wallet_address="0x2222", name="agent-2"
        )

        result = CycleResult()
        runner._phase_monitor(result)
        assert result.health_checks_run > 0


# ── Phase 5: Collect Tests ────────────────────────────────────────────


class TestPhaseCollect:
    """Tests for the evidence collection phase."""

    def test_collect_no_completed(self):
        runner = make_runner()
        result = CycleResult()
        runner._phase_collect(result)
        assert result.tasks_completed == 0
        assert result.bounty_earned_usd == 0

    def test_collect_completed_tasks(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["completed"] = [
            {"id": "task-1", "bounty_amount": 5.0, "worker_wallet": "0xabc"},
            {"id": "task-2", "bounty_amount": 3.0, "worker_wallet": "0xdef"},
        ]

        runner = make_runner(mock_em=mock_em)
        # Mark these as known
        runner._known_task_ids = {"task-1", "task-2"}

        result = CycleResult()
        runner._phase_collect(result)
        assert result.tasks_completed == 2
        assert result.bounty_earned_usd == 8.0

    def test_collect_with_failed_tasks(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["failed"] = [
            {"id": "task-3", "error": "timeout"},
        ]

        runner = make_runner(mock_em=mock_em)
        result = CycleResult()
        runner._phase_collect(result)
        assert result.tasks_failed == 1


# ── Phase 7: Report Tests ─────────────────────────────────────────────


class TestPhaseReport:
    """Tests for the reporting phase."""

    def test_report_healthy_api(self):
        runner = make_runner()
        result = CycleResult()
        runner._phase_report(result)
        assert result.em_api_healthy is True

    def test_report_unhealthy_api(self):
        mock_em = MockEMApiClient()
        mock_em.health = {"status": "unhealthy"}
        runner = make_runner(mock_em=mock_em)
        result = CycleResult()
        runner._phase_report(result)
        assert result.em_api_healthy is False


# ── Full Cycle Tests ──────────────────────────────────────────────────


class TestFullCycle:
    """Tests for complete coordination cycles."""

    def test_empty_cycle(self):
        runner = make_runner()
        result = runner.run_once()
        assert result.cycle_number == 1
        assert result.duration_ms > 0
        assert len(result.phases_completed) == 7
        assert len(result.phases_failed) == 0

    def test_cycle_with_tasks(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["published"] = [
            {
                "id": "t1",
                "title": "Test",
                "category": "simple_action",
                "bounty_amount": 1.0,
            },
            {
                "id": "t2",
                "title": "Test 2",
                "category": "data_collection",
                "bounty_amount": 2.0,
            },
        ]

        runner = make_runner(mock_em=mock_em)
        result = runner.run_once()
        assert result.tasks_new == 2
        assert result.em_api_healthy is True

    def test_consecutive_cycles(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["published"] = [
            {
                "id": "t1",
                "title": "Test",
                "category": "simple_action",
                "bounty_amount": 1.0,
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = make_runner(mock_em=mock_em, state_dir=tmpdir)

            result1 = runner.run_once()
            assert result1.tasks_new == 1

            result2 = runner.run_once()
            assert result2.tasks_new == 0  # Deduplicated

            assert runner._state.total_cycles == 2

    def test_cycle_with_phase_error(self):
        """Phase errors should be caught and reported, not crash the cycle."""
        runner = make_runner()

        # Break the EM client to cause a discover error
        class BrokenClient:
            base_url = "broken"

            def list_tasks(self, **kw):
                raise ConnectionError("API unreachable")

            def get_health(self):
                raise ConnectionError("API unreachable")

        runner.coordinator.em_client = BrokenClient()

        result = runner.run_once()
        assert "discover" in result.phases_failed
        assert len(result.errors) > 0
        # Other phases should still complete
        assert "monitor" in result.phases_completed


# ── State Persistence Tests ───────────────────────────────────────────


class TestStatePersistence:
    """Tests for state save/load across restarts."""

    def test_state_saves_to_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = make_runner(state_dir=tmpdir)
            runner.run_once()

            state_file = os.path.join(tmpdir, "runner_state.json")
            assert os.path.exists(state_file)

            data = json.loads(open(state_file).read())
            assert data["total_cycles"] == 1

    def test_state_loads_on_restart(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # First run
            runner1 = make_runner(state_dir=tmpdir)
            runner1.run_once()
            runner1.run_once()
            assert runner1._state.total_cycles == 2

            # Second runner loads state
            runner2 = make_runner(state_dir=tmpdir)
            runner2._load_state()
            assert runner2._state.total_cycles == 2

    def test_state_accumulates(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["completed"] = [
            {"id": "t1", "bounty_amount": 5.0, "worker_wallet": "0xabc"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            runner = make_runner(mock_em=mock_em, state_dir=tmpdir)
            runner._known_task_ids = {"t1"}

            runner.run_once()
            runner.run_once()

            assert runner._state.total_bounty_earned_usd == 10.0


# ── Dashboard Tests ───────────────────────────────────────────────────


class TestDashboard:
    """Tests for the runner status/dashboard."""

    def test_get_status(self):
        runner = make_runner()
        status = runner.get_status()
        assert "mode" in status
        assert "state" in status
        assert "running" in status
        assert status["mode"] == "passive"

    def test_cycle_history(self):
        runner = make_runner()
        runner.run_once()
        runner.run_once()

        history = runner.get_cycle_history(limit=5)
        assert len(history) == 2
        assert history[0]["cycle_number"] == 1
        assert history[1]["cycle_number"] == 2

    def test_status_includes_coordinator_dashboard(self):
        runner = make_runner()
        status = runner.get_status()
        assert "coordinator_dashboard" in status


# ── Mode Behavior Tests ──────────────────────────────────────────────


class TestModes:
    """Tests for runner mode behavior differences."""

    def test_passive_observes_only(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["published"] = [
            {
                "id": "t1",
                "title": "Task",
                "category": "simple_action",
                "bounty_amount": 1.0,
            },
        ]

        runner = make_runner(mock_em=mock_em, mode="passive")
        result = runner.run_once()
        assert result.tasks_new == 1
        assert result.tasks_routed == 0  # Passive doesn't route

    def test_dry_run_processes_without_api(self):
        mock_em = MockEMApiClient()
        mock_em.tasks["published"] = [
            {
                "id": "t1",
                "title": "Task",
                "category": "simple_action",
                "bounty_amount": 1.0,
            },
        ]

        runner = make_runner(mock_em=mock_em, mode="dry_run")
        result = runner.run_once()
        assert result.tasks_new == 1
        # Dry run counts pending tasks as "routed"

    def test_stop_signal(self):
        runner = make_runner(max_cycles=100)
        runner.stop()
        assert runner._running is False
