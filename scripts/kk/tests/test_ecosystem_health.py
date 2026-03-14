"""
Tests for the Ecosystem Health Check.

Verifies the health check infrastructure works correctly
with mocked external dependencies.
"""

import json
import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ecosystem_health import (
    HealthReport,
    check_swarm,
    check_autojob,
    check_describe_net,
    check_cross_system,
)


class TestHealthReport(unittest.TestCase):
    """Test the HealthReport accumulator."""

    def test_empty_report(self):
        report = HealthReport()
        result = report.summary()
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["status"], "healthy")

    def test_all_passing(self):
        report = HealthReport()
        report.section("Test Section")
        report.check("Check 1", True, "OK")
        report.check("Check 2", True, "OK")
        result = report.summary()
        self.assertEqual(result["passed"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["status"], "healthy")

    def test_one_failure(self):
        report = HealthReport()
        report.section("Test")
        report.check("Good", True)
        report.check("Bad", False, "Failed")
        result = report.summary()
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["status"], "degraded")

    def test_warning_not_failure(self):
        report = HealthReport()
        report.section("Test")
        report.check("Good", True)
        report.check("Warn", False, "Warning", warn=True)
        result = report.summary()
        self.assertEqual(result["passed"], 1)
        self.assertEqual(result["warnings"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["status"], "healthy")

    def test_metric_recording(self):
        report = HealthReport()
        report.section("Metrics")
        report.metric("count", 42, "items")
        self.assertEqual(report.sections[0]["metrics"]["count"]["value"], 42)
        self.assertEqual(report.sections[0]["metrics"]["count"]["unit"], "items")

    def test_sections_accumulate(self):
        report = HealthReport()
        report.section("Section A")
        report.check("A1", True)
        report.section("Section B")
        report.check("B1", True)
        report.check("B2", False)
        result = report.summary()
        self.assertEqual(len(result["sections"]), 2)
        self.assertEqual(result["sections"][0]["name"], "Section A")
        self.assertEqual(len(result["sections"][0]["checks"]), 1)
        self.assertEqual(len(result["sections"][1]["checks"]), 2)

    def test_elapsed_time(self):
        report = HealthReport()
        result = report.summary()
        self.assertIn("elapsed_s", result)
        self.assertGreaterEqual(result["elapsed_s"], 0)


class TestSwarmCheck(unittest.TestCase):
    """Test the swarm module check."""

    def test_swarm_modules_present(self):
        """Swarm check should find all 14 modules."""
        report = HealthReport()
        check_swarm(report)

        # Should have created a section with checks
        self.assertTrue(len(report.sections) > 0)
        self.assertEqual(report.sections[0]["name"], "KK V2 Swarm")

        # All modules should be present
        module_check = report.sections[0]["checks"][0]
        self.assertTrue(module_check["passed"])
        self.assertIn("14/14", module_check["detail"])


class TestAutoJobCheck(unittest.TestCase):
    """Test the AutoJob check."""

    def test_autojob_present(self):
        """AutoJob check should find the project."""
        report = HealthReport()
        check_autojob(report)

        self.assertTrue(len(report.sections) > 0)
        self.assertEqual(report.sections[0]["name"], "AutoJob Evidence Flywheel")

        # Project should exist
        project_check = report.sections[0]["checks"][0]
        self.assertTrue(project_check["passed"])

    def test_describe_net_source_connected(self):
        """Should detect describe-net evidence source."""
        report = HealthReport()
        check_autojob(report)

        # Find the describe-net check
        dn_checks = [
            c for c in report.sections[0]["checks"]
            if "describe-net" in c["name"]
        ]
        self.assertTrue(len(dn_checks) > 0)
        self.assertTrue(dn_checks[0]["passed"])


class TestDescribeNetCheck(unittest.TestCase):
    """Test the describe-net check."""

    def test_contracts_present(self):
        """Should find describe-net contracts."""
        report = HealthReport()
        check_describe_net(report, quick=True)

        self.assertTrue(len(report.sections) > 0)
        self.assertEqual(report.sections[0]["name"], "describe-net Contracts")

        # Project should exist
        project_check = report.sections[0]["checks"][0]
        self.assertTrue(project_check["passed"])


class TestCrossSystemCheck(unittest.TestCase):
    """Test the cross-system integration check."""

    def test_integration_score(self):
        """All cross-system bridges should be connected."""
        report = HealthReport()
        check_cross_system(report)

        self.assertEqual(report.sections[0]["name"], "Cross-System Integration")

        # All bridges should be connected
        metrics = report.sections[0]["metrics"]
        self.assertIn("Integration score", metrics)

        # Check all passed
        checks = report.sections[0]["checks"]
        failed_checks = [c for c in checks if not c["passed"]]
        self.assertEqual(len(failed_checks), 0,
                         f"Failed checks: {[c['name'] for c in failed_checks]}")


if __name__ == "__main__":
    unittest.main()
