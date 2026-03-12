"""
Tests for SwarmHeartbeatHandler — heartbeat integration module.

Verifies the condensed coordination cycle that runs during
OpenClaw heartbeat polls.
"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime, timezone

from swarm.heartbeat_handler import (
    SwarmHeartbeatHandler,
    HeartbeatReport,
    _load_state,
    _save_state,
)


# ─── HeartbeatReport Tests ────────────────────────────────────────────────────


class TestHeartbeatReport:
    """Test HeartbeatReport data model."""

    def test_default_report(self):
        report = HeartbeatReport()
        assert report.new_tasks == 0
        assert report.tasks_routed == 0
        assert report.agents_active == 0
        assert report.errors == []

    def test_to_summary_healthy(self):
        report = HeartbeatReport(
            timestamp="2026-03-12T04:00:00Z",
            duration_ms=150,
            new_tasks=3,
            tasks_routed=2,
            tasks_completed=1,
            agents_active=18,
            agents_degraded=0,
            em_api_healthy=True,
            bounty_earned_usd=1.50,
        )
        summary = report.to_summary()
        assert "🟢" in summary
        assert "Swarm Heartbeat" in summary
        assert "+3 new" in summary
        assert "18 active" in summary
        assert "$1.50" in summary

    def test_to_summary_degraded(self):
        report = HeartbeatReport(
            timestamp="2026-03-12T04:00:00Z",
            duration_ms=200,
            em_api_healthy=True,
            agents_active=16,
            agents_degraded=2,
            errors=["autojob: unreachable"],
        )
        summary = report.to_summary()
        assert "🟡" in summary
        assert "2 degraded" in summary
        assert "Issues:" in summary

    def test_to_summary_unhealthy(self):
        report = HeartbeatReport(
            em_api_healthy=False,
            errors=["em_api: unreachable"],
        )
        summary = report.to_summary()
        assert "🔴" in summary

    def test_is_notable_new_tasks(self):
        report = HeartbeatReport(new_tasks=5)
        assert report.is_notable() is True

    def test_is_notable_completed(self):
        report = HeartbeatReport(tasks_completed=2)
        assert report.is_notable() is True

    def test_is_notable_degraded(self):
        report = HeartbeatReport(agents_degraded=1)
        assert report.is_notable() is True

    def test_is_notable_bounty(self):
        report = HeartbeatReport(bounty_earned_usd=0.50)
        assert report.is_notable() is True

    def test_is_notable_errors(self):
        report = HeartbeatReport(errors=["something broke"])
        assert report.is_notable() is True

    def test_not_notable_empty(self):
        report = HeartbeatReport()
        assert report.is_notable() is False

    def test_to_dict(self):
        report = HeartbeatReport(
            timestamp="2026-03-12T04:00:00Z",
            new_tasks=3,
            agents_active=18,
        )
        d = report.to_dict()
        assert isinstance(d, dict)
        assert d["new_tasks"] == 3
        assert d["agents_active"] == 18
        assert d["timestamp"] == "2026-03-12T04:00:00Z"

    def test_summary_with_skill_dna(self):
        report = HeartbeatReport(
            em_api_healthy=True,
            skill_dna_updates=5,
            duration_ms=100,
        )
        summary = report.to_summary()
        assert "🧬" in summary
        assert "5 updates" in summary


# ─── State Persistence Tests ──────────────────────────────────────────────────


class TestStatePersistence:
    """Test state load/save functions."""

    def test_load_nonexistent(self):
        state = _load_state("/tmp/nonexistent-swarm-state-dir-12345")
        assert state["last_heartbeat"] is None
        assert state["total_cycles"] == 0

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = {
                "last_heartbeat": "2026-03-12T04:00:00Z",
                "total_cycles": 42,
                "total_tasks_processed": 100,
            }
            _save_state(state, tmpdir)

            loaded = _load_state(tmpdir)
            assert loaded["total_cycles"] == 42
            assert loaded["total_tasks_processed"] == 100

    def test_save_creates_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "nested", "dir")
            _save_state({"test": True}, nested)
            assert os.path.exists(os.path.join(nested, "heartbeat_state.json"))

    def test_load_corrupt_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "heartbeat_state.json"), "w") as f:
                f.write("{bad json{")
            state = _load_state(tmpdir)
            assert state["last_heartbeat"] is None  # Falls back to default


# ─── Handler Tests ────────────────────────────────────────────────────────────


class TestSwarmHeartbeatHandler:
    """Test the heartbeat handler lifecycle."""

    def test_init(self):
        handler = SwarmHeartbeatHandler(
            em_api_url="https://api.execution.market",
            mode="passive",
        )
        assert handler.mode == "passive"
        assert handler.em_api_url == "https://api.execution.market"

    @patch("swarm.heartbeat_handler.SwarmCoordinator")
    def test_run_cycle_passive_no_tasks(self, mock_coord_cls):
        """Passive mode with no new tasks should be quick and clean."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_coord = MagicMock()
            mock_coord.em_client.get_health.return_value = {"status": "healthy"}
            mock_coord.ingest_from_api.return_value = 0
            mock_coord.run_health_checks.return_value = {
                "agents": {"checked": 24, "healthy": 24, "degraded": 0},
                "systems": {"em_api": "ok", "autojob": "available"},
            }
            mock_metrics = MagicMock()
            mock_metrics.bounty_earned = 0
            mock_coord.get_metrics.return_value = mock_metrics
            mock_coord_cls.create.return_value = mock_coord

            handler = SwarmHeartbeatHandler(
                state_dir=tmpdir,
                mode="passive",
            )
            report = handler.run_cycle()

            assert report.em_api_healthy is True
            assert report.new_tasks == 0
            assert report.tasks_routed == 0
            assert report.agents_active == 24
            assert report.agents_degraded == 0
            assert report.errors == []
            assert report.duration_ms > 0

    @patch("swarm.heartbeat_handler.SwarmCoordinator")
    def test_run_cycle_semi_auto_with_tasks(self, mock_coord_cls):
        """Semi-auto mode should route tasks when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_coord = MagicMock()
            mock_coord.em_client.get_health.return_value = {"status": "healthy"}
            mock_coord.ingest_from_api.return_value = 3
            # Return assignments (have agent_id attr)
            assignment1 = MagicMock()
            assignment1.agent_id = "agent_1"
            assignment2 = MagicMock()
            assignment2.agent_id = "agent_2"
            mock_coord.process_task_queue.return_value = [assignment1, assignment2]
            mock_coord.run_health_checks.return_value = {
                "agents": {"checked": 24, "healthy": 22, "degraded": 2},
                "systems": {"em_api": "ok", "autojob": "unavailable"},
            }
            mock_metrics = MagicMock()
            mock_metrics.bounty_earned = 5.50
            mock_coord.get_metrics.return_value = mock_metrics
            mock_coord_cls.create.return_value = mock_coord

            handler = SwarmHeartbeatHandler(
                state_dir=tmpdir,
                mode="semi-auto",
            )
            report = handler.run_cycle()

            assert report.em_api_healthy is True
            assert report.new_tasks == 3
            assert report.tasks_routed == 2
            assert report.agents_degraded == 2
            assert report.bounty_earned_usd == 5.50

    @patch("swarm.heartbeat_handler.SwarmCoordinator")
    def test_run_cycle_passive_skips_routing(self, mock_coord_cls):
        """Passive mode should NOT route even when tasks exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_coord = MagicMock()
            mock_coord.em_client.get_health.return_value = {"status": "healthy"}
            mock_coord.ingest_from_api.return_value = 5  # 5 new tasks!
            mock_coord.run_health_checks.return_value = {
                "agents": {"checked": 24, "healthy": 24, "degraded": 0},
                "systems": {},
            }
            mock_metrics = MagicMock()
            mock_metrics.bounty_earned = 0
            mock_coord.get_metrics.return_value = mock_metrics
            mock_coord_cls.create.return_value = mock_coord

            handler = SwarmHeartbeatHandler(
                state_dir=tmpdir,
                mode="passive",
            )
            report = handler.run_cycle()

            assert report.new_tasks == 5
            assert report.tasks_routed == 0
            # process_task_queue should NOT have been called
            mock_coord.process_task_queue.assert_not_called()

    @patch("swarm.heartbeat_handler.SwarmCoordinator")
    def test_run_cycle_api_unreachable(self, mock_coord_cls):
        """Handler should gracefully handle API failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_coord = MagicMock()
            mock_coord.em_client.get_health.side_effect = Exception("Connection refused")
            mock_coord.ingest_from_api.side_effect = Exception("API unreachable")
            mock_coord.run_health_checks.return_value = {
                "agents": {"checked": 0, "healthy": 0, "degraded": 0},
                "systems": {"em_api": "unreachable"},
            }
            mock_metrics = MagicMock()
            mock_metrics.bounty_earned = 0
            mock_coord.get_metrics.return_value = mock_metrics
            mock_coord_cls.create.return_value = mock_coord

            handler = SwarmHeartbeatHandler(
                state_dir=tmpdir,
                mode="passive",
            )
            report = handler.run_cycle()

            assert report.em_api_healthy is False
            assert len(report.errors) > 0
            assert any("ingest" in e for e in report.errors)

    @patch("swarm.heartbeat_handler.SwarmCoordinator")
    def test_state_persists_across_cycles(self, mock_coord_cls):
        """State should accumulate across multiple heartbeat cycles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_coord = MagicMock()
            mock_coord.em_client.get_health.return_value = {"status": "healthy"}
            mock_coord.ingest_from_api.return_value = 0
            mock_coord.run_health_checks.return_value = {
                "agents": {"checked": 24, "healthy": 24, "degraded": 0},
                "systems": {},
            }
            mock_metrics = MagicMock()
            mock_metrics.bounty_earned = 0
            mock_coord.get_metrics.return_value = mock_metrics
            mock_coord_cls.create.return_value = mock_coord

            handler = SwarmHeartbeatHandler(state_dir=tmpdir, mode="passive")

            # Run 3 cycles
            handler.run_cycle()
            handler.run_cycle()
            handler.run_cycle()

            state = handler.get_state()
            assert state["total_cycles"] == 3

    def test_get_state_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            handler = SwarmHeartbeatHandler(state_dir=tmpdir)
            state = handler.get_state()
            assert state["last_heartbeat"] is None
            assert state["total_cycles"] == 0

    @patch("swarm.heartbeat_handler.SwarmCoordinator")
    def test_reset_state(self, mock_coord_cls):
        with tempfile.TemporaryDirectory() as tmpdir:
            _save_state({"total_cycles": 100}, tmpdir)
            handler = SwarmHeartbeatHandler(state_dir=tmpdir)
            handler.reset_state()
            state = handler.get_state()
            assert state.get("total_cycles", 0) == 0


# ─── Integration: Report + Handler ────────────────────────────────────────────


class TestReportIntegration:
    """Test that handler produces useful reports."""

    @patch("swarm.heartbeat_handler.SwarmCoordinator")
    def test_notable_report_triggers_notification(self, mock_coord_cls):
        """Reports with new tasks should be flagged as notable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_coord = MagicMock()
            mock_coord.em_client.get_health.return_value = {"status": "healthy"}
            mock_coord.ingest_from_api.return_value = 5
            mock_coord.run_health_checks.return_value = {
                "agents": {"checked": 24, "healthy": 24, "degraded": 0},
                "systems": {},
            }
            mock_metrics = MagicMock()
            mock_metrics.bounty_earned = 0
            mock_coord.get_metrics.return_value = mock_metrics
            mock_coord_cls.create.return_value = mock_coord

            handler = SwarmHeartbeatHandler(state_dir=tmpdir, mode="passive")
            report = handler.run_cycle()

            assert report.is_notable() is True
            summary = report.to_summary()
            assert len(summary) > 0
            assert "+5 new" in summary

    @patch("swarm.heartbeat_handler.SwarmCoordinator")
    def test_quiet_report_not_notable(self, mock_coord_cls):
        """Reports with no activity should not be notable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_coord = MagicMock()
            mock_coord.em_client.get_health.return_value = {"status": "healthy"}
            mock_coord.ingest_from_api.return_value = 0
            mock_coord.run_health_checks.return_value = {
                "agents": {"checked": 24, "healthy": 24, "degraded": 0},
                "systems": {},
            }
            mock_metrics = MagicMock()
            mock_metrics.bounty_earned = 0
            mock_coord.get_metrics.return_value = mock_metrics
            mock_coord_cls.create.return_value = mock_coord

            handler = SwarmHeartbeatHandler(state_dir=tmpdir, mode="passive")
            report = handler.run_cycle()

            assert report.is_notable() is False
