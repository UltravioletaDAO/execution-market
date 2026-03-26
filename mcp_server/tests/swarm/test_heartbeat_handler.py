"""
Tests for SwarmHeartbeatHandler — integrates swarm coordination with heartbeat cycle.

Covers:
- HeartbeatReport data class (summary, notable detection, serialization)
- State persistence (load/save/reset)
- Handler initialization (lazy coordinator + event listener)
- Run cycle (health check, ingest, route, complete, metrics, persist)
- Error resilience (each step can fail independently)
- Mode behavior (passive vs semi-auto routing)
- Max task bounty filtering
"""

import json
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


from mcp_server.swarm.heartbeat_handler import (
    HeartbeatReport,
    SwarmHeartbeatHandler,
    _load_state,
    _save_state,
)


# ─── HeartbeatReport Tests ────────────────────────────────────────────────────


class TestHeartbeatReport:
    def test_default_values(self):
        r = HeartbeatReport()
        assert r.new_tasks == 0
        assert r.tasks_routed == 0
        assert r.tasks_completed == 0
        assert r.tasks_failed == 0
        assert r.agents_active == 0
        assert r.agents_degraded == 0
        assert r.em_api_healthy is False
        assert r.autojob_available is False
        assert r.errors == []
        assert r.skill_dna_updates == 0
        assert r.bounty_earned_usd == 0

    def test_summary_healthy_idle(self):
        r = HeartbeatReport(em_api_healthy=True, duration_ms=42.5)
        summary = r.to_summary()
        assert "🟢" in summary
        assert "42ms" in summary or "43ms" in summary

    def test_summary_healthy_with_errors(self):
        r = HeartbeatReport(em_api_healthy=True, errors=["timeout"])
        summary = r.to_summary()
        assert "🟡" in summary
        assert "timeout" in summary

    def test_summary_unhealthy(self):
        r = HeartbeatReport(em_api_healthy=False)
        summary = r.to_summary()
        assert "🔴" in summary

    def test_summary_with_tasks(self):
        r = HeartbeatReport(
            em_api_healthy=True,
            new_tasks=3,
            tasks_routed=2,
            tasks_completed=1,
        )
        summary = r.to_summary()
        assert "+3 new" in summary
        assert "2 routed" in summary
        assert "1 completed" in summary

    def test_summary_with_agents(self):
        r = HeartbeatReport(
            em_api_healthy=True,
            agents_active=5,
            agents_degraded=2,
        )
        summary = r.to_summary()
        assert "5 active" in summary
        assert "2 degraded" in summary

    def test_summary_agents_no_degraded(self):
        r = HeartbeatReport(em_api_healthy=True, agents_active=5)
        summary = r.to_summary()
        assert "5 active" in summary
        assert "degraded" not in summary

    def test_summary_with_earnings(self):
        r = HeartbeatReport(em_api_healthy=True, bounty_earned_usd=3.50)
        summary = r.to_summary()
        assert "$3.50" in summary

    def test_summary_with_dna_updates(self):
        r = HeartbeatReport(em_api_healthy=True, skill_dna_updates=7)
        summary = r.to_summary()
        assert "7 updates" in summary

    def test_summary_truncates_errors(self):
        r = HeartbeatReport(
            em_api_healthy=True,
            errors=["e1", "e2", "e3", "e4", "e5"],
        )
        summary = r.to_summary()
        # Only first 3 errors shown
        assert "e1" in summary
        assert "e2" in summary
        assert "e3" in summary
        assert "e4" not in summary

    def test_is_notable_new_tasks(self):
        r = HeartbeatReport(new_tasks=1)
        assert r.is_notable() is True

    def test_is_notable_completed(self):
        r = HeartbeatReport(tasks_completed=1)
        assert r.is_notable() is True

    def test_is_notable_degraded(self):
        r = HeartbeatReport(agents_degraded=1)
        assert r.is_notable() is True

    def test_is_notable_errors(self):
        r = HeartbeatReport(errors=["boom"])
        assert r.is_notable() is True

    def test_is_notable_earnings(self):
        r = HeartbeatReport(bounty_earned_usd=0.50)
        assert r.is_notable() is True

    def test_not_notable_idle(self):
        r = HeartbeatReport(em_api_healthy=True, agents_active=5)
        assert r.is_notable() is False

    def test_to_dict_roundtrip(self):
        r = HeartbeatReport(
            timestamp="2026-03-24T04:00:00Z",
            duration_ms=150.5,
            new_tasks=3,
            tasks_routed=2,
            tasks_completed=1,
            tasks_failed=0,
            agents_active=5,
            agents_degraded=1,
            em_api_healthy=True,
            autojob_available=True,
            errors=["warn1"],
            skill_dna_updates=4,
            bounty_earned_usd=2.50,
        )
        d = r.to_dict()
        assert d["timestamp"] == "2026-03-24T04:00:00Z"
        assert d["duration_ms"] == 150.5
        assert d["new_tasks"] == 3
        assert d["em_api_healthy"] is True
        assert d["errors"] == ["warn1"]
        assert d["bounty_earned_usd"] == 2.50

    def test_to_dict_serializable(self):
        """to_dict output must be JSON-serializable."""
        r = HeartbeatReport(
            timestamp="2026-03-24T04:00:00Z",
            errors=["err"],
            bounty_earned_usd=1.0,
        )
        serialized = json.dumps(r.to_dict())
        assert '"timestamp"' in serialized


# ─── State Persistence Tests ─────────────────────────────────────────────────


class TestStatePersistence:
    def test_load_missing_file(self):
        state = _load_state("/nonexistent/path")
        assert state["last_heartbeat"] is None
        assert state["total_cycles"] == 0

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            state = {"last_heartbeat": "2026-03-24", "total_cycles": 5}
            _save_state(state, td)
            loaded = _load_state(td)
            assert loaded["last_heartbeat"] == "2026-03-24"
            assert loaded["total_cycles"] == 5

    def test_save_creates_directory(self):
        with tempfile.TemporaryDirectory() as td:
            nested = os.path.join(td, "deep", "nested")
            _save_state({"x": 1}, nested)
            assert os.path.isfile(os.path.join(nested, "heartbeat_state.json"))

    def test_load_corrupt_json(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "heartbeat_state.json"), "w") as f:
                f.write("{broken json")
            state = _load_state(td)
            assert state["total_cycles"] == 0  # falls back to defaults


# ─── Handler Initialization Tests ─────────────────────────────────────────────


class TestHandlerInit:
    def test_default_params(self):
        h = SwarmHeartbeatHandler()
        assert h.em_api_url == "https://api.execution.market"
        assert h.mode == "passive"
        assert h.max_task_bounty == 1.0

    def test_custom_params(self):
        h = SwarmHeartbeatHandler(
            em_api_url="http://localhost:8000",
            autojob_url="http://localhost:9000",
            mode="semi-auto",
            max_task_bounty=5.0,
        )
        assert h.em_api_url == "http://localhost:8000"
        assert h.autojob_url == "http://localhost:9000"
        assert h.mode == "semi-auto"
        assert h.max_task_bounty == 5.0

    def test_coordinator_lazy_init(self):
        h = SwarmHeartbeatHandler()
        assert h._coordinator is None

    def test_event_listener_lazy_init(self):
        h = SwarmHeartbeatHandler()
        assert h._event_listener is None


# ─── Run Cycle Tests ──────────────────────────────────────────────────────────


class TestRunCycle:
    def _make_handler(self, state_dir=None):
        """Create handler with temp state dir."""
        if state_dir is None:
            state_dir = tempfile.mkdtemp()
        return SwarmHeartbeatHandler(
            em_api_url="https://api.execution.market",
            state_dir=state_dir,
            mode="passive",
        )

    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_coordinator_init_failure(self, mock_init):
        """If coordinator fails to init, report captures the error."""
        mock_init.side_effect = RuntimeError("no config")
        h = self._make_handler()
        report = h.run_cycle()
        assert "coordinator_init" in report.errors[0]
        assert report.duration_ms > 0

    @patch.object(SwarmHeartbeatHandler, "_init_event_listener")
    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_healthy_api(self, mock_coord, mock_listener):
        """EM API health check success."""
        coord = MagicMock()
        coord.em_client.get_health.return_value = {"status": "healthy"}
        coord.ingest_from_api.return_value = 0
        coord.run_health_checks.return_value = {
            "agents": {"healthy": 3, "degraded": 0},
            "systems": {"autojob": "available"},
        }
        coord.get_metrics.return_value = SimpleNamespace(bounty_earned=0)
        mock_coord.return_value = coord

        listener = MagicMock()
        listener.poll_once.return_value = SimpleNamespace(
            completed_tasks=0, failed_tasks=0, expired_tasks=0
        )
        mock_listener.return_value = listener

        h = self._make_handler()
        report = h.run_cycle()
        assert report.em_api_healthy is True
        assert report.agents_active == 3
        assert report.autojob_available is True

    @patch.object(SwarmHeartbeatHandler, "_init_event_listener")
    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_unhealthy_api(self, mock_coord, mock_listener):
        """EM API health check failure."""
        coord = MagicMock()
        coord.em_client.get_health.side_effect = ConnectionError("timeout")
        coord.ingest_from_api.return_value = 0
        coord.run_health_checks.return_value = {
            "agents": {},
            "systems": {},
        }
        coord.get_metrics.return_value = SimpleNamespace()
        mock_coord.return_value = coord

        listener = MagicMock()
        listener.poll_once.return_value = SimpleNamespace(
            completed_tasks=0, failed_tasks=0, expired_tasks=0
        )
        mock_listener.return_value = listener

        h = self._make_handler()
        report = h.run_cycle()
        assert report.em_api_healthy is False

    @patch.object(SwarmHeartbeatHandler, "_init_event_listener")
    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_ingests_new_tasks(self, mock_coord, mock_listener):
        """New tasks are counted in the report."""
        coord = MagicMock()
        coord.em_client.get_health.return_value = {"status": "healthy"}
        coord.ingest_from_api.return_value = 5
        coord.run_health_checks.return_value = {"agents": {}, "systems": {}}
        coord.get_metrics.return_value = SimpleNamespace()
        mock_coord.return_value = coord

        listener = MagicMock()
        listener.poll_once.return_value = SimpleNamespace(
            completed_tasks=0, failed_tasks=0, expired_tasks=0
        )
        mock_listener.return_value = listener

        h = self._make_handler()
        report = h.run_cycle()
        assert report.new_tasks == 5

    @patch.object(SwarmHeartbeatHandler, "_init_event_listener")
    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_passive_mode_no_routing(self, mock_coord, mock_listener):
        """Passive mode doesn't route tasks even when new ones exist."""
        coord = MagicMock()
        coord.em_client.get_health.return_value = {"status": "healthy"}
        coord.ingest_from_api.return_value = 3
        coord.run_health_checks.return_value = {"agents": {}, "systems": {}}
        coord.get_metrics.return_value = SimpleNamespace()
        mock_coord.return_value = coord

        listener = MagicMock()
        listener.poll_once.return_value = SimpleNamespace(
            completed_tasks=0, failed_tasks=0, expired_tasks=0
        )
        mock_listener.return_value = listener

        h = self._make_handler()
        h.mode = "passive"
        report = h.run_cycle()
        coord.process_task_queue.assert_not_called()
        assert report.tasks_routed == 0

    @patch.object(SwarmHeartbeatHandler, "_init_event_listener")
    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_semi_auto_routes_tasks(self, mock_coord, mock_listener):
        """Semi-auto mode routes tasks when new ones arrive."""
        coord = MagicMock()
        coord.em_client.get_health.return_value = {"status": "healthy"}
        coord.ingest_from_api.return_value = 2
        coord._task_queue = {}  # no tasks to filter by bounty
        assignment = SimpleNamespace(agent_id="agent1")
        coord.process_task_queue.return_value = [assignment]
        coord.run_health_checks.return_value = {"agents": {}, "systems": {}}
        coord.get_metrics.return_value = SimpleNamespace()
        mock_coord.return_value = coord

        listener = MagicMock()
        listener.poll_once.return_value = SimpleNamespace(
            completed_tasks=0, failed_tasks=0, expired_tasks=0
        )
        mock_listener.return_value = listener

        h = self._make_handler()
        h.mode = "semi-auto"
        report = h.run_cycle()
        coord.process_task_queue.assert_called_once_with(max_tasks=5)
        assert report.tasks_routed == 1

    @patch.object(SwarmHeartbeatHandler, "_init_event_listener")
    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_completed_tasks_counted(self, mock_coord, mock_listener):
        """Completed and failed tasks from event listener are reported."""
        coord = MagicMock()
        coord.em_client.get_health.return_value = {"status": "healthy"}
        coord.ingest_from_api.return_value = 0
        coord.run_health_checks.return_value = {"agents": {}, "systems": {}}
        coord.get_metrics.return_value = SimpleNamespace()
        mock_coord.return_value = coord

        listener = MagicMock()
        listener.poll_once.return_value = SimpleNamespace(
            completed_tasks=4, failed_tasks=1, expired_tasks=2
        )
        mock_listener.return_value = listener

        h = self._make_handler()
        report = h.run_cycle()
        assert report.tasks_completed == 4
        assert report.tasks_failed == 3  # 1 failed + 2 expired

    @patch.object(SwarmHeartbeatHandler, "_init_event_listener")
    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_ingest_error_captured(self, mock_coord, mock_listener):
        """Ingest errors are captured without killing the cycle."""
        coord = MagicMock()
        coord.em_client.get_health.return_value = {"status": "healthy"}
        coord.ingest_from_api.side_effect = ConnectionError("API down")
        coord.run_health_checks.return_value = {"agents": {}, "systems": {}}
        coord.get_metrics.return_value = SimpleNamespace()
        mock_coord.return_value = coord

        listener = MagicMock()
        listener.poll_once.return_value = SimpleNamespace(
            completed_tasks=0, failed_tasks=0, expired_tasks=0
        )
        mock_listener.return_value = listener

        h = self._make_handler()
        report = h.run_cycle()
        assert any("ingest" in e for e in report.errors)
        # Other steps still ran
        assert report.duration_ms > 0

    @patch.object(SwarmHeartbeatHandler, "_init_event_listener")
    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_state_persisted_after_cycle(self, mock_coord, mock_listener):
        """State file is updated after each cycle."""
        coord = MagicMock()
        coord.em_client.get_health.return_value = {"status": "healthy"}
        coord.ingest_from_api.return_value = 0
        coord.run_health_checks.return_value = {"agents": {}, "systems": {}}
        coord.get_metrics.return_value = SimpleNamespace()
        mock_coord.return_value = coord

        listener = MagicMock()
        listener.poll_once.return_value = SimpleNamespace(
            completed_tasks=2, failed_tasks=0, expired_tasks=0
        )
        mock_listener.return_value = listener

        with tempfile.TemporaryDirectory() as td:
            h = self._make_handler(state_dir=td)
            h.run_cycle()

            state = _load_state(td)
            assert state["total_cycles"] == 1
            assert state["total_tasks_processed"] == 2

            # Second cycle increments
            h.run_cycle()
            state = _load_state(td)
            assert state["total_cycles"] == 2
            assert state["total_tasks_processed"] == 4

    @patch.object(SwarmHeartbeatHandler, "_init_event_listener")
    @patch.object(SwarmHeartbeatHandler, "_init_coordinator")
    def test_bounty_earnings_tracked(self, mock_coord, mock_listener):
        """Bounty earnings are read from coordinator metrics."""
        coord = MagicMock()
        coord.em_client.get_health.return_value = {"status": "healthy"}
        coord.ingest_from_api.return_value = 0
        coord.run_health_checks.return_value = {"agents": {}, "systems": {}}
        coord.get_metrics.return_value = SimpleNamespace(bounty_earned=12.50)
        mock_coord.return_value = coord

        listener = MagicMock()
        listener.poll_once.return_value = SimpleNamespace(
            completed_tasks=0, failed_tasks=0, expired_tasks=0
        )
        mock_listener.return_value = listener

        h = self._make_handler()
        report = h.run_cycle()
        assert report.bounty_earned_usd == 12.50


# ─── Handler State Management ────────────────────────────────────────────────


class TestHandlerState:
    def test_get_state_empty(self):
        h = SwarmHeartbeatHandler(state_dir="/tmp/nonexistent_hb_test")
        state = h.get_state()
        assert state["total_cycles"] == 0

    def test_reset_state(self):
        with tempfile.TemporaryDirectory() as td:
            _save_state({"total_cycles": 100}, td)
            h = SwarmHeartbeatHandler(state_dir=td)
            h.reset_state()
            state = h.get_state()
            assert "total_cycles" not in state or state.get("total_cycles", 0) == 0
