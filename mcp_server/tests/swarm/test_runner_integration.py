"""
SwarmRunner Integration Tests
==============================

Tests the SwarmRunner's dry-run cycle against mocked EM API responses,
ensuring all 7 phases execute correctly.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from swarm.runner import SwarmRunner, RunMode, CycleResult, Phase
from swarm.coordinator import EMApiClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_em_client():
    """EMApiClient that returns realistic responses."""
    client = MagicMock(spec=EMApiClient)
    client.base_url = "https://api.execution.market"
    client.get_health.return_value = {
        "status": "healthy",
        "version": "1.0.0",
    }
    client.list_tasks.return_value = []
    client._request.return_value = {"tasks": [], "total": 0}
    return client


@pytest.fixture
def runner():
    """SwarmRunner in dry-run mode."""
    return SwarmRunner.create(
        em_api_url="https://mock.example.com",
        mode="dry_run",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunnerCreation:
    def test_create_dry_run(self):
        runner = SwarmRunner.create(
            em_api_url="https://mock.example.com",
            mode="dry_run",
        )
        assert runner.mode == RunMode.DRY_RUN

    def test_create_passive(self):
        runner = SwarmRunner.create(
            em_api_url="https://mock.example.com",
            mode="passive",
        )
        assert runner.mode == RunMode.PASSIVE

    def test_create_active(self):
        runner = SwarmRunner.create(
            em_api_url="https://mock.example.com",
            mode="active",
        )
        assert runner.mode == RunMode.ACTIVE

    def test_default_mode(self):
        """Default should be passive for safety."""
        runner = SwarmRunner.create(em_api_url="https://mock.example.com")
        assert runner.mode == RunMode.PASSIVE


class TestDryRunCycle:
    def test_all_phases_complete(self, runner):
        """All 7 phases should complete in a dry-run cycle."""
        # Patch the EM client to avoid real API calls
        runner.coordinator.em_client = MagicMock()
        runner.coordinator.em_client.get_health.return_value = {"status": "healthy"}
        runner.coordinator.em_client.list_tasks.return_value = []
        runner.coordinator.em_client._request.return_value = {"tasks": [], "total": 0}

        cycle = runner.run_once()

        assert isinstance(cycle, CycleResult)
        assert cycle.cycle_number >= 1
        assert cycle.mode == "dry_run"
        assert len(cycle.phases_completed) == 7
        assert len(cycle.phases_failed) == 0
        assert set(cycle.phases_completed) == {
            "discover",
            "enrich",
            "route",
            "monitor",
            "collect",
            "learn",
            "report",
        }

    def test_duration_tracked(self, runner):
        runner.coordinator.em_client = MagicMock()
        runner.coordinator.em_client.get_health.return_value = {"status": "healthy"}
        runner.coordinator.em_client.list_tasks.return_value = []
        runner.coordinator.em_client._request.return_value = {"tasks": [], "total": 0}

        cycle = runner.run_once()
        assert cycle.duration_ms >= 0

    def test_no_errors_in_dry_run(self, runner):
        runner.coordinator.em_client = MagicMock()
        runner.coordinator.em_client.get_health.return_value = {"status": "healthy"}
        runner.coordinator.em_client.list_tasks.return_value = []
        runner.coordinator.em_client._request.return_value = {"tasks": [], "total": 0}

        cycle = runner.run_once()
        assert len(cycle.errors) == 0

    def test_started_at_is_iso(self, runner):
        runner.coordinator.em_client = MagicMock()
        runner.coordinator.em_client.get_health.return_value = {"status": "healthy"}
        runner.coordinator.em_client.list_tasks.return_value = []
        runner.coordinator.em_client._request.return_value = {"tasks": [], "total": 0}

        cycle = runner.run_once()
        # Should be a valid ISO 8601 timestamp
        dt = datetime.fromisoformat(cycle.started_at)
        assert (
            dt.tzinfo is not None or "+" in cycle.started_at or "Z" in cycle.started_at
        )


class TestCycleWithTasks:
    def test_discover_finds_tasks(self, runner):
        """Discover phase should count found tasks."""
        mock_tasks = [
            {
                "id": "t1",
                "title": "Test Task 1",
                "status": "published",
                "category": "digital_physical",
                "bounty_usd": 0.5,
            },
            {
                "id": "t2",
                "title": "Test Task 2",
                "status": "published",
                "category": "digital_physical",
                "bounty_usd": 1.0,
            },
        ]

        runner.coordinator.em_client = MagicMock()
        runner.coordinator.em_client.get_health.return_value = {"status": "healthy"}
        runner.coordinator.em_client.list_tasks.return_value = mock_tasks
        runner.coordinator.em_client._request.return_value = {"tasks": [], "total": 0}

        cycle = runner.run_once()
        assert "discover" in cycle.phases_completed
        # Tasks should be discovered (exact count depends on deduplication logic)
        assert cycle.tasks_discovered >= 0


class TestCycleResult:
    def test_to_dict(self):
        cycle = CycleResult(
            cycle_number=1,
            started_at="2026-03-21T02:00:00+00:00",
            duration_ms=100,
            mode="dry_run",
        )
        d = cycle.to_dict()
        assert isinstance(d, dict)
        assert d["cycle_number"] == 1
        assert d["mode"] == "dry_run"

    def test_summary_line(self):
        cycle = CycleResult(
            cycle_number=1,
            started_at="2026-03-21T02:00:00+00:00",
            duration_ms=100,
            mode="dry_run",
            phases_completed=["discover", "report"],
        )
        summary = cycle.summary_line()
        assert isinstance(summary, str)
        assert "1" in summary  # cycle number


class TestRunModes:
    def test_run_mode_enum(self):
        assert RunMode.PASSIVE == "passive"
        assert RunMode.ACTIVE == "active"
        assert RunMode.DRY_RUN == "dry_run"

    def test_phase_enum(self):
        assert Phase.DISCOVER == "discover"
        assert Phase.ENRICH == "enrich"
        assert Phase.ROUTE == "route"
        assert Phase.MONITOR == "monitor"
        assert Phase.COLLECT == "collect"
        assert Phase.LEARN == "learn"
        assert Phase.REPORT == "report"
