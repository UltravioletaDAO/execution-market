"""
Test Suite: SwarmHeartbeatHandler — Heartbeat-Driven Coordination
===================================================================

Tests cover:
    1. HeartbeatReport (summary generation, notable detection, serialization)
    2. State persistence (load, save, default state)
    3. Handler initialization (lazy coordinator, mode)
    4. Edge cases (empty state, error handling)
"""

import os
import tempfile
from unittest.mock import MagicMock

from mcp_server.swarm.heartbeat_handler import (
    HeartbeatReport,
    SwarmHeartbeatHandler,
    _load_state,
    _save_state,
)


# ══════════════════════════════════════════════════════════════
# HeartbeatReport Tests
# ══════════════════════════════════════════════════════════════


class TestHeartbeatReport:
    def test_default_values(self):
        report = HeartbeatReport()
        assert report.new_tasks == 0
        assert report.em_api_healthy is False
        assert report.errors == []

    def test_summary_healthy(self):
        report = HeartbeatReport(
            em_api_healthy=True,
            new_tasks=3,
            tasks_routed=2,
            tasks_completed=1,
            agents_active=5,
            duration_ms=150.0,
        )
        summary = report.to_summary()
        assert "🟢" in summary
        assert "3" in summary

    def test_summary_with_errors(self):
        report = HeartbeatReport(
            em_api_healthy=True,
            errors=["ingest: timeout"],
            duration_ms=500.0,
        )
        summary = report.to_summary()
        assert "🟡" in summary  # healthy but with errors
        assert "timeout" in summary

    def test_summary_unhealthy(self):
        report = HeartbeatReport(
            em_api_healthy=False,
            duration_ms=50.0,
        )
        summary = report.to_summary()
        assert "🔴" in summary

    def test_summary_with_earnings(self):
        report = HeartbeatReport(
            em_api_healthy=True,
            bounty_earned_usd=5.50,
            duration_ms=100.0,
        )
        summary = report.to_summary()
        assert "$5.50" in summary

    def test_summary_with_degraded(self):
        report = HeartbeatReport(
            em_api_healthy=True,
            agents_active=5,
            agents_degraded=2,
            duration_ms=100.0,
        )
        summary = report.to_summary()
        assert "degraded" in summary

    def test_summary_with_skill_dna(self):
        report = HeartbeatReport(
            em_api_healthy=True,
            skill_dna_updates=3,
            duration_ms=100.0,
        )
        summary = report.to_summary()
        assert "🧬" in summary

    def test_is_notable_new_tasks(self):
        report = HeartbeatReport(new_tasks=1)
        assert report.is_notable() is True

    def test_is_notable_completed(self):
        report = HeartbeatReport(tasks_completed=1)
        assert report.is_notable() is True

    def test_is_notable_degraded(self):
        report = HeartbeatReport(agents_degraded=1)
        assert report.is_notable() is True

    def test_is_notable_errors(self):
        report = HeartbeatReport(errors=["something"])
        assert report.is_notable() is True

    def test_is_notable_earnings(self):
        report = HeartbeatReport(bounty_earned_usd=1.0)
        assert report.is_notable() is True

    def test_not_notable_empty(self):
        report = HeartbeatReport()
        assert report.is_notable() is False

    def test_to_dict(self):
        report = HeartbeatReport(
            timestamp="2026-03-28T00:00:00Z",
            new_tasks=5,
            em_api_healthy=True,
        )
        d = report.to_dict()
        assert d["timestamp"] == "2026-03-28T00:00:00Z"
        assert d["new_tasks"] == 5
        assert d["em_api_healthy"] is True

    def test_to_dict_complete(self):
        report = HeartbeatReport()
        d = report.to_dict()
        expected_keys = {
            "timestamp",
            "duration_ms",
            "new_tasks",
            "tasks_routed",
            "tasks_completed",
            "tasks_failed",
            "agents_active",
            "agents_degraded",
            "em_api_healthy",
            "autojob_available",
            "errors",
            "skill_dna_updates",
            "bounty_earned_usd",
        }
        assert set(d.keys()) == expected_keys

    def test_summary_truncates_errors(self):
        report = HeartbeatReport(
            em_api_healthy=True,
            errors=["err1", "err2", "err3", "err4", "err5"],
            duration_ms=100.0,
        )
        summary = report.to_summary()
        # Should show at most 3 errors
        assert "err4" not in summary


# ══════════════════════════════════════════════════════════════
# State Persistence Tests
# ══════════════════════════════════════════════════════════════


class TestStatePersistence:
    def test_load_default_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = _load_state(tmpdir)
            assert state["last_heartbeat"] is None
            assert state["total_cycles"] == 0

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {"last_heartbeat": "2026-03-28T00:00:00Z", "total_cycles": 5}
            _save_state(state, tmpdir)

            loaded = _load_state(tmpdir)
            assert loaded["last_heartbeat"] == "2026-03-28T00:00:00Z"
            assert loaded["total_cycles"] == 5

    def test_load_corrupt_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = os.path.join(tmpdir, "heartbeat_state.json")
            with open(state_file, "w") as f:
                f.write("not valid json")

            state = _load_state(tmpdir)
            assert state["total_cycles"] == 0  # Returns default

    def test_save_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "sub", "dir")
            _save_state({"test": True}, nested)
            assert os.path.exists(os.path.join(nested, "heartbeat_state.json"))


# ══════════════════════════════════════════════════════════════
# Handler Tests
# ══════════════════════════════════════════════════════════════


class TestSwarmHeartbeatHandler:
    def test_initialization(self):
        handler = SwarmHeartbeatHandler(
            em_api_url="https://test.com",
            mode="passive",
        )
        assert handler.em_api_url == "https://test.com"
        assert handler.mode == "passive"
        assert handler._coordinator is None

    def test_max_task_bounty(self):
        handler = SwarmHeartbeatHandler(max_task_bounty=5.0)
        assert handler.max_task_bounty == 5.0

    def test_get_state_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SwarmHeartbeatHandler(state_dir=tmpdir)
            state = handler.get_state()
            assert state["total_cycles"] == 0

    def test_reset_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SwarmHeartbeatHandler(state_dir=tmpdir)
            _save_state({"total_cycles": 100}, tmpdir)
            handler.reset_state()
            state = handler.get_state()
            assert "total_cycles" not in state or state.get("total_cycles", 0) == 0

    def test_run_cycle_returns_report(self):
        """Test that run_cycle returns a HeartbeatReport even on coordinator init failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SwarmHeartbeatHandler(
                em_api_url="https://nonexistent.local",
                state_dir=tmpdir,
            )

            # Coordinator init will likely fail → report should contain error
            report = handler.run_cycle()
            assert isinstance(report, HeartbeatReport)
            assert report.duration_ms >= 0
            # Either it works or it has errors
            assert report.timestamp != ""

    def test_passive_mode_no_routing(self):
        """In passive mode, no routing should happen even with new tasks."""
        handler = SwarmHeartbeatHandler(mode="passive")

        # Mock coordinator to avoid actual API calls
        coord = MagicMock()
        coord.em_client = MagicMock()
        coord.em_client.get_health.return_value = {"status": "healthy"}
        coord.ingest_from_api.return_value = 3  # 3 new tasks
        coord.run_health_checks.return_value = {
            "agents": {"healthy": 2, "degraded": 0},
            "systems": {},
        }
        coord.get_metrics.return_value = MagicMock(bounty_earned=0)
        handler._coordinator = coord

        # Mock event listener
        listener = MagicMock()
        listener.poll_once.return_value = MagicMock(
            completed_tasks=0, failed_tasks=0, expired_tasks=0
        )
        handler._event_listener = listener

        with tempfile.TemporaryDirectory() as tmpdir:
            handler.state_dir = tmpdir
            report = handler.run_cycle()
            assert report.new_tasks == 3
            # In passive mode, process_task_queue should NOT be called
            coord.process_task_queue.assert_not_called()
