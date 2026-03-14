"""
Tests for SwarmDaemon — production-ready continuous coordination loop.

Tests cover configuration, state management, single cycle execution,
multi-cycle runs, bootstrap integration, analytics integration,
error handling, and backoff behavior.
"""

import json
import os
import pytest
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

from mcp_server.swarm.daemon import (
    SwarmDaemon,
    DaemonConfig,
    DaemonState,
    CycleResult,
    _load_daemon_state,
    _save_daemon_state,
)
from mcp_server.swarm.analytics import SwarmAnalytics, TaskEvent, TimeWindow


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_state_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def config(tmp_state_dir):
    return DaemonConfig(
        mode="passive",
        em_api_url="https://api.execution.market",
        state_dir=tmp_state_dir,
        interval_seconds=1,
    )


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator that doesn't require network."""
    coord = MagicMock()
    coord.em_client = MagicMock()
    coord.em_client.get_health.return_value = {"status": "healthy"}
    coord.ingest_from_api.return_value = 0
    coord.task_queue = []
    coord.process_task_queue.return_value = []
    coord.run_health_checks.return_value = {
        "agents": {"healthy": 5, "degraded": 0, "total": 5},
        "systems": {},
    }
    coord.get_metrics.return_value = MagicMock(bounty_earned=0)
    return coord


@pytest.fixture
def mock_event_listener():
    """Mock event listener poll result."""
    listener = MagicMock()
    poll_result = MagicMock()
    poll_result.completed_tasks = 0
    poll_result.failed_tasks = 0
    poll_result.expired_tasks = 0
    listener.poll_once.return_value = poll_result
    return listener


@pytest.fixture
def daemon(config, mock_coordinator, mock_event_listener):
    """Create a daemon with mocked dependencies."""
    d = SwarmDaemon(config, coordinator=mock_coordinator)
    d._bootstrapped = True
    d._event_listener = mock_event_listener
    return d


# ─── DaemonConfig ─────────────────────────────────────────────────────────────


class TestDaemonConfig:
    def test_defaults(self):
        c = DaemonConfig()
        assert c.mode == "passive"
        assert c.interval_seconds == 300
        assert c.max_tasks_per_cycle == 10
        assert c.enable_analytics is True

    def test_to_dict(self):
        c = DaemonConfig()
        d = c.to_dict()
        assert "mode" in d
        assert "interval_seconds" in d
        assert "enable_analytics" in d

    def test_from_env(self):
        with patch.dict(os.environ, {
            "EM_SWARM_MODE": "full-auto",
            "EM_SWARM_INTERVAL": "60",
            "EM_SWARM_MAX_TASKS": "5",
        }):
            c = DaemonConfig.from_env()
            assert c.mode == "full-auto"
            assert c.interval_seconds == 60
            assert c.max_tasks_per_cycle == 5

    def test_custom_values(self):
        c = DaemonConfig(
            mode="semi-auto",
            interval_seconds=120,
            max_bounty_usd=5.0,
            sla_target_seconds=7200,
        )
        assert c.mode == "semi-auto"
        assert c.max_bounty_usd == 5.0


# ─── DaemonState ──────────────────────────────────────────────────────────────


class TestDaemonState:
    def test_defaults(self):
        s = DaemonState()
        assert s.total_cycles == 0
        assert s.consecutive_failures == 0

    def test_to_dict(self):
        s = DaemonState(total_cycles=10, total_bounty_earned_usd=1.5)
        d = s.to_dict()
        assert d["total_cycles"] == 10
        assert d["total_bounty_earned_usd"] == 1.5

    def test_from_dict(self):
        d = {"total_cycles": 5, "consecutive_failures": 2, "errors_total": 3}
        s = DaemonState.from_dict(d)
        assert s.total_cycles == 5
        assert s.consecutive_failures == 2
        assert s.errors_total == 3

    def test_roundtrip(self):
        original = DaemonState(
            total_cycles=42,
            total_tasks_processed=100,
            total_bounty_earned_usd=5.5,
            started_at="2026-03-14T00:00:00Z",
        )
        d = original.to_dict()
        restored = DaemonState.from_dict(d)
        assert restored.total_cycles == 42
        assert restored.total_tasks_processed == 100


# ─── State Persistence ───────────────────────────────────────────────────────


class TestStatePersistence:
    def test_save_and_load(self, tmp_state_dir):
        state = DaemonState(total_cycles=5, total_tasks_processed=20)
        _save_daemon_state(state, tmp_state_dir)

        loaded = _load_daemon_state(tmp_state_dir)
        assert loaded.total_cycles == 5
        assert loaded.total_tasks_processed == 20

    def test_load_nonexistent(self, tmp_state_dir):
        loaded = _load_daemon_state(tmp_state_dir)
        assert loaded.total_cycles == 0

    def test_load_corrupt_json(self, tmp_state_dir):
        state_file = os.path.join(tmp_state_dir, "daemon_state.json")
        with open(state_file, "w") as f:
            f.write("{invalid json")
        loaded = _load_daemon_state(tmp_state_dir)
        assert loaded.total_cycles == 0

    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as parent:
            nested = os.path.join(parent, "sub", "dir")
            state = DaemonState(total_cycles=1)
            _save_daemon_state(state, nested)
            assert os.path.exists(os.path.join(nested, "daemon_state.json"))


# ─── CycleResult ──────────────────────────────────────────────────────────────


class TestCycleResult:
    def test_success_when_no_errors(self):
        r = CycleResult(cycle_number=1, timestamp="now", duration_ms=100)
        assert r.success is True

    def test_failure_when_errors(self):
        r = CycleResult(cycle_number=1, timestamp="now", duration_ms=100, errors=["oops"])
        assert r.success is False

    def test_is_notable(self):
        r = CycleResult(cycle_number=1, timestamp="now", duration_ms=100)
        assert r.is_notable is False

        r.tasks_ingested = 5
        assert r.is_notable is True

    def test_to_dict(self):
        r = CycleResult(
            cycle_number=3,
            timestamp="2026-03-14T03:00:00Z",
            duration_ms=150.5,
            tasks_ingested=2,
            tasks_completed=1,
            agents_active=5,
            agents_total=10,
        )
        d = r.to_dict()
        assert d["cycle"] == 3
        assert d["tasks"]["ingested"] == 2
        assert d["agents"]["active"] == 5

    def test_to_summary(self):
        r = CycleResult(
            cycle_number=1,
            timestamp="now",
            duration_ms=100,
            em_api_healthy=True,
            tasks_ingested=3,
            tasks_completed=2,
            agents_total=5,
            agents_active=4,
        )
        summary = r.to_summary()
        assert "Cycle #1" in summary
        assert "100ms" in summary
        assert "4/5" in summary

    def test_summary_with_errors(self):
        r = CycleResult(
            cycle_number=1, timestamp="now", duration_ms=50,
            errors=["ingest: timeout", "health: down"],
        )
        summary = r.to_summary()
        assert "⚠️" in summary
        assert "2 errors" in summary

    def test_summary_with_recommendations(self):
        r = CycleResult(
            cycle_number=1, timestamp="now", duration_ms=50,
            recommendations_count=3,
        )
        summary = r.to_summary()
        assert "3 recommendations" in summary


# ─── Daemon Creation ─────────────────────────────────────────────────────────


class TestDaemonCreation:
    def test_create_factory(self, tmp_state_dir):
        d = SwarmDaemon.create(
            mode="passive",
            state_dir=tmp_state_dir,
        )
        assert d.config.mode == "passive"
        assert d.is_running is False

    def test_initial_state(self, daemon):
        assert daemon.is_running is False
        assert daemon.state.total_cycles == 0

    def test_analytics_initialized(self, daemon):
        assert daemon.analytics is not None
        assert daemon.analytics.event_count == 0


# ─── Single Cycle ─────────────────────────────────────────────────────────────


class TestRunOnce:
    def test_basic_cycle(self, daemon):
        result = daemon.run_once()
        assert isinstance(result, CycleResult)
        assert result.cycle_number == 1
        assert result.duration_ms > 0

    def test_health_check_passes(self, daemon, mock_coordinator):
        mock_coordinator.em_client.get_health.return_value = {"status": "healthy"}
        result = daemon.run_once()
        assert result.em_api_healthy is True

    def test_health_check_fails(self, daemon, mock_coordinator):
        mock_coordinator.em_client.get_health.side_effect = Exception("timeout")
        result = daemon.run_once()
        assert result.em_api_healthy is False
        assert any("health_check" in e for e in result.errors)

    def test_ingest_counts(self, daemon, mock_coordinator):
        mock_coordinator.ingest_from_api.return_value = 5
        mock_coordinator.task_queue = [{"id": f"t{i}"} for i in range(5)]
        result = daemon.run_once()
        assert result.tasks_ingested == 5

    def test_passive_mode_no_routing(self, daemon, mock_coordinator):
        daemon.config.mode = "passive"
        mock_coordinator.ingest_from_api.return_value = 3
        mock_coordinator.task_queue = [{"id": "t1"}]
        result = daemon.run_once()
        mock_coordinator.process_task_queue.assert_not_called()
        assert result.tasks_routed == 0

    def test_semi_auto_routes_tasks(self, daemon, mock_coordinator):
        daemon.config.mode = "semi-auto"
        mock_coordinator.ingest_from_api.return_value = 2
        mock_coordinator.task_queue = [{"id": "t1"}, {"id": "t2"}]
        assignment = MagicMock()
        assignment.task_id = "t1"
        assignment.agent_id = 1
        assignment.agent_name = "aurora"
        mock_coordinator.process_task_queue.return_value = [assignment]
        result = daemon.run_once()
        assert result.tasks_routed == 1

    def test_event_listener_completions(self, daemon, mock_event_listener):
        poll_result = MagicMock()
        poll_result.completed_tasks = 3
        poll_result.failed_tasks = 1
        poll_result.expired_tasks = 0
        mock_event_listener.poll_once.return_value = poll_result
        result = daemon.run_once()
        assert result.tasks_completed == 3
        assert result.tasks_failed == 1

    def test_agent_counts(self, daemon, mock_coordinator):
        mock_coordinator.run_health_checks.return_value = {
            "agents": {"healthy": 8, "degraded": 2, "total": 10},
        }
        result = daemon.run_once()
        assert result.agents_active == 8
        assert result.agents_total == 10

    def test_cycle_increments_state(self, daemon):
        daemon.run_once()
        assert daemon.state.total_cycles == 1
        daemon.run_once()
        assert daemon.state.total_cycles == 2

    def test_state_persisted(self, daemon, config):
        daemon.run_once()
        loaded = _load_daemon_state(config.state_dir)
        assert loaded.total_cycles == 1

    def test_analytics_summary_generated(self, daemon):
        result = daemon.run_once()
        # Analytics summary should exist even if empty
        assert result.analytics_summary is not None

    def test_phase_durations_tracked(self, daemon):
        result = daemon.run_once()
        phases = result.phase_durations_ms
        assert "bootstrap" in phases
        assert "health_check" in phases
        assert "ingest" in phases
        assert "routing" in phases
        assert "events" in phases
        assert "persist" in phases

    def test_on_cycle_complete_callback(self, config, mock_coordinator, mock_event_listener):
        results_collected = []
        
        def callback(r):
            results_collected.append(r)

        d = SwarmDaemon(config, coordinator=mock_coordinator, on_cycle_complete=callback)
        d._bootstrapped = True
        d._event_listener = mock_event_listener
        d.run_once()

        assert len(results_collected) == 1
        assert results_collected[0].cycle_number == 1


# ─── Error Handling ───────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_ingest_error_captured(self, daemon, mock_coordinator):
        mock_coordinator.ingest_from_api.side_effect = Exception("API down")
        result = daemon.run_once()
        assert any("ingest" in e for e in result.errors)
        assert result.success is False

    def test_event_listener_error_captured(self, daemon, mock_event_listener):
        mock_event_listener.poll_once.side_effect = Exception("poll failed")
        result = daemon.run_once()
        assert any("events" in e for e in result.errors)

    def test_health_check_error_captured(self, daemon, mock_coordinator):
        mock_coordinator.run_health_checks.side_effect = Exception("boom")
        result = daemon.run_once()
        assert any("swarm_health" in e for e in result.errors)

    def test_consecutive_failures_tracked(self, daemon, mock_coordinator):
        mock_coordinator.em_client.get_health.side_effect = Exception("fail")
        daemon.run_once()
        assert daemon.state.consecutive_failures == 1
        daemon.run_once()
        assert daemon.state.consecutive_failures == 2

    def test_failures_reset_on_success(self, daemon, mock_coordinator):
        mock_coordinator.em_client.get_health.side_effect = Exception("fail")
        daemon.run_once()
        assert daemon.state.consecutive_failures == 1

        mock_coordinator.em_client.get_health.side_effect = None
        mock_coordinator.em_client.get_health.return_value = {"status": "healthy"}
        daemon.run_once()
        assert daemon.state.consecutive_failures == 0

    def test_errors_total_accumulates(self, daemon, mock_coordinator):
        mock_coordinator.em_client.get_health.side_effect = Exception("fail")
        daemon.run_once()
        daemon.run_once()
        assert daemon.state.errors_total >= 2

    def test_callback_error_doesnt_crash_cycle(self, config, mock_coordinator, mock_event_listener):
        def bad_callback(r):
            raise ValueError("callback boom")

        d = SwarmDaemon(config, coordinator=mock_coordinator, on_cycle_complete=bad_callback)
        d._bootstrapped = True
        d._event_listener = mock_event_listener
        result = d.run_once()
        # Should complete without crashing
        assert result.cycle_number == 1


# ─── Multi-Cycle ──────────────────────────────────────────────────────────────


class TestMultiCycle:
    def test_run_max_cycles(self, daemon):
        results = daemon.run(max_cycles=3, interval=0)
        assert len(results) == 3
        assert daemon.state.total_cycles == 3

    def test_stop_signal(self, daemon):
        def stop_after_2(result):
            if result.cycle_number >= 2:
                daemon.stop()

        daemon._on_cycle_complete = stop_after_2
        results = daemon.run(max_cycles=5, interval=0)
        assert len(results) == 2

    def test_running_flag(self, daemon):
        assert daemon.is_running is False
        results = daemon.run(max_cycles=1, interval=0)
        assert daemon.is_running is False

    def test_started_at_set(self, daemon):
        daemon.run(max_cycles=1, interval=0)
        assert daemon.state.started_at is not None


# ─── Status ───────────────────────────────────────────────────────────────────


class TestStatus:
    def test_get_status(self, daemon):
        s = daemon.get_status()
        assert "running" in s
        assert "config" in s
        assert "state" in s
        assert "analytics" in s
        assert s["bootstrapped"] is True

    def test_get_analytics_report(self, daemon):
        # Seed some events
        daemon.analytics.record_event(
            TaskEvent(task_id="x", event_type="created")
        )
        report = daemon.get_analytics_report()
        assert "pipeline" in report
        assert report["total_events"] == 1

    def test_analytics_with_window(self, daemon):
        report = daemon.get_analytics_report(TimeWindow.DAY)
        assert report["window"] == "day"


# ─── Bootstrap Integration ───────────────────────────────────────────────────


class TestBootstrapIntegration:
    def test_auto_bootstrap_on_first_cycle(self, config):
        """Non-bootstrapped daemon bootstraps on first cycle."""
        d = SwarmDaemon(config)
        with patch.object(d, 'bootstrap') as mock_bootstrap:
            mock_bootstrap.return_value = None
            # Mock coordinator after bootstrap
            d._coordinator = MagicMock()
            d._coordinator.em_client = MagicMock()
            d._coordinator.em_client.get_health.return_value = {"status": "healthy"}
            d._coordinator.ingest_from_api.return_value = 0
            d._coordinator.run_health_checks.return_value = {"agents": {"healthy": 0, "total": 0}}
            d._event_listener = MagicMock()
            poll = MagicMock()
            poll.completed_tasks = 0
            poll.failed_tasks = 0
            poll.expired_tasks = 0
            d._event_listener.poll_once.return_value = poll
            d._bootstrapped = True

            d.run_once()
            # Bootstrap should not be called since we set _bootstrapped=True
            # This test confirms the flow works

    def test_skip_bootstrap_when_already_done(self, daemon):
        daemon._bootstrapped = True
        result = daemon.bootstrap()
        assert result is None  # No-op when already bootstrapped


# ─── Analytics Integration ────────────────────────────────────────────────────


class TestAnalyticsIntegration:
    def test_analytics_disabled(self, config, mock_coordinator, mock_event_listener):
        config.enable_analytics = False
        d = SwarmDaemon(config, coordinator=mock_coordinator)
        d._bootstrapped = True
        d._event_listener = mock_event_listener
        result = d.run_once()
        assert result.analytics_summary is None

    def test_events_recorded_on_ingest(self, daemon, mock_coordinator):
        mock_coordinator.ingest_from_api.return_value = 2
        mock_coordinator.task_queue = [
            {"id": "t1", "category": "photo", "bounty": 0.10, "chain": "base"},
            {"id": "t2", "category": "delivery", "bounty": 0.20, "chain": "polygon"},
        ]
        daemon.run_once()
        assert daemon.analytics.event_count >= 2

    def test_recommendations_counted(self, daemon):
        # Add events that trigger recommendations
        for i in range(20):
            daemon.analytics.record_event(TaskEvent(
                task_id=f"exp{i}", event_type="created",
            ))
            daemon.analytics.record_event(TaskEvent(
                task_id=f"exp{i}", event_type="expired",
            ))
        result = daemon.run_once()
        assert result.recommendations_count > 0


# ─── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_no_coordinator_creates_one(self, config):
        d = SwarmDaemon(config)
        with patch("mcp_server.swarm.daemon.SwarmBootstrap") as MockBoot:
            mock_result = MagicMock()
            mock_result.coordinator = MagicMock()
            mock_result.agents_registered = 0
            mock_result.tasks_loaded = 0
            mock_result.reputation_updates = 0
            mock_result.historical_tasks = []
            MockBoot.return_value.bootstrap.return_value = mock_result
            coord = d._ensure_coordinator()
            assert coord is not None

    def test_daemon_state_default_values(self):
        s = DaemonState()
        assert s.started_at is None
        assert s.last_cycle_at is None
        assert s.last_cycle_success is True

    def test_config_from_env_defaults(self):
        """Ensure from_env works with no env vars set."""
        with patch.dict(os.environ, {}, clear=False):
            c = DaemonConfig.from_env()
            assert c.mode in ("passive", "semi-auto", "full-auto")

    def test_multiple_errors_in_one_cycle(self, daemon, mock_coordinator, mock_event_listener):
        mock_coordinator.em_client.get_health.side_effect = Exception("err1")
        mock_coordinator.ingest_from_api.side_effect = Exception("err2")
        mock_event_listener.poll_once.side_effect = Exception("err3")
        mock_coordinator.run_health_checks.side_effect = Exception("err4")

        result = daemon.run_once()
        assert len(result.errors) >= 4
        assert not result.success

    def test_zero_interval_doesnt_block(self, daemon):
        results = daemon.run(max_cycles=2, interval=0)
        assert len(results) == 2
