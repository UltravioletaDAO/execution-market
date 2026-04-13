"""
Test Suite: SwarmHeartbeatHandler — Heartbeat-Driven Coordination
===================================================================

Tests cover:
    1. HeartbeatReport (summary generation, notable detection, serialization)
    2. State persistence (load, save, default state)
    3. Handler initialization (lazy coordinator, mode)
    4. Edge cases (empty state, error handling)
"""

import tempfile

from mcp_server.swarm.heartbeat_handler import (
    HeartbeatReport,
    SwarmHeartbeatHandler,
    _load_state,
)


# ══════════════════════════════════════════════════════════════
# HeartbeatReport Tests
# ══════════════════════════════════════════════════════════════


class TestHeartbeatReport:
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


# ══════════════════════════════════════════════════════════════
# State Persistence Tests
# ══════════════════════════════════════════════════════════════


class TestStatePersistence:
    def test_load_default_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state = _load_state(tmpdir)
            assert state["last_heartbeat"] is None
            assert state["total_cycles"] == 0


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
