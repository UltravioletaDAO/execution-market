"""
Tests for SwarmHealthDashboard — real-time health monitoring.

Coverage:
    - ComponentCheck data model
    - MarketplaceState data model
    - ChainState data model
    - HealthReport (default, summary, degraded, components)
    - SwarmHealthDashboard (EM health, auth, autojob, fleet, marketplace)
    - SwarmComponentStatus tracker
"""

import json
import time
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from mcp_server.swarm.swarm_health_dashboard import (
    SwarmHealthDashboard,
    HealthReport,
    HealthStatus,
    ComponentCheck,
    MarketplaceState,
    ChainState,
    SwarmComponentStatus,
    _http_get,
)


# ---------------------------------------------------------------------------
# TestComponentCheck
# ---------------------------------------------------------------------------

class TestComponentCheck(unittest.TestCase):
    """Test ComponentCheck data model."""

    def test_healthy_check(self):
        check = ComponentCheck(name="test", status=HealthStatus.HEALTHY)
        self.assertTrue(check.is_healthy)
        self.assertEqual(check.status, HealthStatus.HEALTHY)

    def test_down_check(self):
        check = ComponentCheck(name="test", status=HealthStatus.DOWN)
        self.assertFalse(check.is_healthy)

    def test_degraded_check(self):
        check = ComponentCheck(
            name="api",
            status=HealthStatus.DEGRADED,
            latency_ms=250.5,
            message="Slow response",
        )
        self.assertFalse(check.is_healthy)
        self.assertEqual(check.latency_ms, 250.5)

    def test_unknown_check(self):
        check = ComponentCheck(name="new_component")
        self.assertEqual(check.status, HealthStatus.UNKNOWN)
        self.assertFalse(check.is_healthy)

    def test_with_details(self):
        check = ComponentCheck(
            name="em_api",
            status=HealthStatus.HEALTHY,
            details={"version": "1.0", "uptime": 3600},
        )
        d = check.to_dict()
        self.assertEqual(d["name"], "em_api")
        self.assertEqual(d["details"]["version"], "1.0")
        self.assertIn("checked_at", d)


# ---------------------------------------------------------------------------
# TestMarketplaceState
# ---------------------------------------------------------------------------

class TestMarketplaceState(unittest.TestCase):
    """Test MarketplaceState data model."""

    def test_defaults(self):
        state = MarketplaceState()
        self.assertEqual(state.total_tasks, 0)
        self.assertEqual(state.active_tasks, 0)
        self.assertEqual(state.completed_tasks, 0)
        self.assertEqual(state.registered_workers, 0)

    def test_populated(self):
        state = MarketplaceState(
            total_tasks=200,
            active_tasks=15,
            completed_tasks=180,
            registered_workers=50,
            registered_agents=24,
        )
        d = state.to_dict()
        self.assertEqual(d["total_tasks"], 200)
        self.assertEqual(d["active_tasks"], 15)
        self.assertEqual(d["registered_agents"], 24)


# ---------------------------------------------------------------------------
# TestChainState
# ---------------------------------------------------------------------------

class TestChainState(unittest.TestCase):
    """Test ChainState data model."""

    def test_defaults(self):
        state = ChainState()
        self.assertFalse(state.is_healthy)
        self.assertEqual(state.chain, "")

    def test_fully_healthy(self):
        state = ChainState(
            chain="base",
            connected=True,
            block_height=12345678,
            contracts_verified=True,
            last_tx_age_seconds=60,
        )
        self.assertTrue(state.is_healthy)
        d = state.to_dict()
        self.assertEqual(d["chain"], "base")
        self.assertEqual(d["block_height"], 12345678)


# ---------------------------------------------------------------------------
# TestHealthReport
# ---------------------------------------------------------------------------

class TestHealthReport(unittest.TestCase):
    """Test HealthReport aggregation."""

    def test_default_report(self):
        report = HealthReport()
        self.assertEqual(report.overall_status, HealthStatus.UNKNOWN)
        self.assertIn("UNKNOWN", report.summary())

    def test_summary_output(self):
        report = HealthReport(
            components=[
                ComponentCheck(name="em_api", status=HealthStatus.HEALTHY, latency_ms=50),
                ComponentCheck(name="auth", status=HealthStatus.HEALTHY, latency_ms=30),
            ],
            fleet_size=24,
            active_agents=20,
        )
        summary = report.summary()
        self.assertIn("HEALTHY", summary)
        self.assertIn("em_api", summary)
        self.assertIn("20/24", summary)

    def test_degraded_summary(self):
        report = HealthReport(
            components=[
                ComponentCheck(name="em_api", status=HealthStatus.HEALTHY),
                ComponentCheck(name="autojob", status=HealthStatus.DEGRADED, message="Slow"),
            ]
        )
        self.assertEqual(report.overall_status, HealthStatus.DEGRADED)
        summary = report.summary()
        self.assertIn("DEGRADED", summary)

    def test_summary_with_missing_agents(self):
        report = HealthReport(
            components=[
                ComponentCheck(name="fleet", status=HealthStatus.HEALTHY),
            ],
            missing_agents=["agent_99", "agent_100"],
        )
        summary = report.summary()
        self.assertIn("agent_99", summary)

    def test_summary_with_components(self):
        report = HealthReport(
            components=[
                ComponentCheck(name="em_api", status=HealthStatus.DOWN, message="Timeout"),
            ]
        )
        self.assertEqual(report.overall_status, HealthStatus.DOWN)
        summary = report.summary()
        self.assertIn("❌", summary)
        self.assertIn("Timeout", summary)

    def test_to_dict(self):
        report = HealthReport(
            components=[
                ComponentCheck(name="em_api", status=HealthStatus.HEALTHY),
            ],
            marketplace=MarketplaceState(total_tasks=100),
            fleet_size=24,
            active_agents=18,
        )
        d = report.to_dict()
        self.assertEqual(d["overall_status"], "healthy")
        self.assertEqual(d["fleet_size"], 24)
        self.assertEqual(d["marketplace"]["total_tasks"], 100)


# ---------------------------------------------------------------------------
# TestSwarmHealthDashboard
# ---------------------------------------------------------------------------

class TestSwarmHealthDashboard(unittest.TestCase):
    """Test the main dashboard class."""

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_em_health_healthy(self, mock_get):
        mock_get.return_value = (200, '{"status":"ok"}', 45.0)
        dashboard = SwarmHealthDashboard()
        check = dashboard.check_em_health()
        self.assertTrue(check.is_healthy)
        self.assertEqual(check.name, "em_api")
        self.assertAlmostEqual(check.latency_ms, 45.0)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_em_health_degraded(self, mock_get):
        mock_get.return_value = (503, "Service Unavailable", 100.0)
        dashboard = SwarmHealthDashboard()
        check = dashboard.check_em_health()
        self.assertEqual(check.status, HealthStatus.DEGRADED)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_em_health_down(self, mock_get):
        mock_get.return_value = (0, "Connection refused", 1000.0)
        dashboard = SwarmHealthDashboard()
        check = dashboard.check_em_health()
        self.assertEqual(check.status, HealthStatus.DOWN)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_em_auth(self, mock_get):
        mock_get.return_value = (200, '{"nonce":"abc123def456"}', 30.0)
        dashboard = SwarmHealthDashboard()
        check = dashboard.check_em_auth()
        self.assertTrue(check.is_healthy)
        self.assertEqual(check.details["nonce_length"], 12)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_em_auth_empty_nonce(self, mock_get):
        mock_get.return_value = (200, '{"nonce":""}', 30.0)
        dashboard = SwarmHealthDashboard()
        check = dashboard.check_em_auth()
        self.assertEqual(check.status, HealthStatus.DEGRADED)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_em_auth_invalid_json(self, mock_get):
        mock_get.return_value = (200, 'not json', 30.0)
        dashboard = SwarmHealthDashboard()
        check = dashboard.check_em_auth()
        self.assertEqual(check.status, HealthStatus.DEGRADED)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_em_auth_down(self, mock_get):
        mock_get.return_value = (0, "timeout", 5000.0)
        dashboard = SwarmHealthDashboard()
        check = dashboard.check_em_auth()
        self.assertEqual(check.status, HealthStatus.DOWN)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_autojob_healthy(self, mock_get):
        mock_get.return_value = (200, '{"status":"ok"}', 20.0)
        dashboard = SwarmHealthDashboard(autojob_url="http://localhost:8765")
        check = dashboard.check_autojob()
        self.assertTrue(check.is_healthy)

    def test_check_autojob_not_configured(self):
        dashboard = SwarmHealthDashboard()
        check = dashboard.check_autojob()
        self.assertEqual(check.status, HealthStatus.UNKNOWN)
        self.assertIn("not configured", check.message)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_autojob_down(self, mock_get):
        mock_get.return_value = (0, "refused", 100.0)
        dashboard = SwarmHealthDashboard(autojob_url="http://localhost:8765")
        check = dashboard.check_autojob()
        self.assertEqual(check.status, HealthStatus.DOWN)

    def test_check_fleet_no_lifecycle(self):
        dashboard = SwarmHealthDashboard()
        check = dashboard.check_fleet()
        self.assertEqual(check.status, HealthStatus.UNKNOWN)

    def test_check_fleet_no_agents(self):
        lifecycle = MagicMock()
        lifecycle._agents = {}
        dashboard = SwarmHealthDashboard(lifecycle_manager=lifecycle)
        check = dashboard.check_fleet()
        self.assertEqual(check.status, HealthStatus.DOWN)

    def test_check_fleet_all_active(self):
        class MockAgent:
            def __init__(self, s):
                self.status = s

        lifecycle = MagicMock()
        lifecycle._agents = {
            "a1": MockAgent("active"),
            "a2": MockAgent("active"),
            "a3": MockAgent("busy"),
        }
        dashboard = SwarmHealthDashboard(lifecycle_manager=lifecycle)
        check = dashboard.check_fleet()
        self.assertTrue(check.is_healthy)
        self.assertIn("3/3", check.message)

    def test_check_fleet_none_active(self):
        class MockAgent:
            def __init__(self, s):
                self.status = s

        lifecycle = MagicMock()
        lifecycle._agents = {
            "a1": MockAgent("sleeping"),
            "a2": MockAgent("error"),
        }
        dashboard = SwarmHealthDashboard(lifecycle_manager=lifecycle)
        check = dashboard.check_fleet()
        self.assertEqual(check.status, HealthStatus.DEGRADED)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_check_marketplace(self, mock_get):
        mock_get.return_value = (200, '{"total":100,"active":5,"completed":90}', 40.0)
        dashboard = SwarmHealthDashboard()
        check, marketplace = dashboard.check_marketplace()
        self.assertTrue(check.is_healthy)
        self.assertEqual(marketplace.total_tasks, 100)

    @patch("mcp_server.swarm.swarm_health_dashboard._http_get")
    def test_full_report(self, mock_get):
        mock_get.return_value = (200, '{"status":"ok","nonce":"abc123"}', 30.0)
        dashboard = SwarmHealthDashboard()
        report = dashboard.full_report()
        self.assertIsInstance(report, HealthReport)
        self.assertGreaterEqual(len(report.components), 4)


# ---------------------------------------------------------------------------
# TestSwarmComponentStatus
# ---------------------------------------------------------------------------

class TestSwarmComponentStatus(unittest.TestCase):
    """Test component status tracker."""

    def test_existing_component(self):
        status = SwarmComponentStatus()
        check = ComponentCheck(name="em_api", status=HealthStatus.HEALTHY)
        status.update(check)

        retrieved = status.get("em_api")
        self.assertIsNotNone(retrieved)
        self.assertTrue(retrieved.is_healthy)

    def test_missing_component(self):
        status = SwarmComponentStatus()
        self.assertIsNone(status.get("nonexistent"))

    def test_update_replaces_latest(self):
        status = SwarmComponentStatus()
        status.update(ComponentCheck(name="api", status=HealthStatus.HEALTHY))
        status.update(ComponentCheck(name="api", status=HealthStatus.DOWN))

        latest = status.get("api")
        self.assertEqual(latest.status, HealthStatus.DOWN)

    def test_all_components(self):
        status = SwarmComponentStatus()
        status.update(ComponentCheck(name="a", status=HealthStatus.HEALTHY))
        status.update(ComponentCheck(name="b", status=HealthStatus.DOWN))

        all_c = status.all_components()
        self.assertEqual(len(all_c), 2)
        self.assertIn("a", all_c)
        self.assertIn("b", all_c)

    def test_history_limit(self):
        status = SwarmComponentStatus()
        for i in range(150):
            status.update(ComponentCheck(name="api", status=HealthStatus.HEALTHY))
        # History should be capped at 100
        self.assertLessEqual(len(status._history["api"]), 100)


if __name__ == "__main__":
    unittest.main()
