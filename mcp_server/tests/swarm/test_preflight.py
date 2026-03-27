"""
Tests for SwarmPreflight — Phase 0 validation for swarm activation.

Covers:
    - CheckResult construction and serialization
    - PreflightReport aggregation (passed, failures, warnings, blockers)
    - SwarmPreflight individual check methods
    - Full run_all() pipeline
    - Error handling in individual checks
    - API connectivity check (mocked)
    - Budget guardrails check
    - Phase gate evaluation
    - State persistence round-trip
    - Integrator wiring and dry-run
"""

import json
import tempfile
from unittest.mock import patch, MagicMock


from mcp_server.swarm.preflight import (
    CheckResult,
    PreflightReport,
    SwarmPreflight,
)


# ─── CheckResult Tests ──────────────────────────────────────────────


class TestCheckResult:
    """Tests for individual check result dataclass."""

    def test_basic_creation(self):
        result = CheckResult(name="test_check", passed=True)
        assert result.name == "test_check"
        assert result.passed is True
        assert result.duration_ms == 0
        assert result.details == ""
        assert result.error is None
        assert result.severity == "blocker"

    def test_failed_result(self):
        result = CheckResult(
            name="imports",
            passed=False,
            duration_ms=12.3,
            error="Module not found: xyz",
            severity="blocker",
        )
        assert result.passed is False
        assert result.error == "Module not found: xyz"
        assert result.duration_ms == 12.3

    def test_warning_severity(self):
        result = CheckResult(
            name="api_connectivity",
            passed=False,
            error="API unreachable",
            severity="warning",
        )
        assert result.severity == "warning"

    def test_info_severity(self):
        result = CheckResult(
            name="version_check",
            passed=True,
            details="v2.1.0",
            severity="info",
        )
        assert result.severity == "info"

    def test_to_dict(self):
        result = CheckResult(
            name="event_bus",
            passed=True,
            duration_ms=1.5678,
            details="Pub/sub working",
        )
        d = result.to_dict()
        assert d["name"] == "event_bus"
        assert d["passed"] is True
        assert d["duration_ms"] == 1.6  # rounded
        assert d["details"] == "Pub/sub working"
        assert d["error"] is None
        assert d["severity"] == "blocker"

    def test_to_dict_with_error(self):
        result = CheckResult(name="fail", passed=False, error="boom", duration_ms=99.99)
        d = result.to_dict()
        assert d["error"] == "boom"
        assert d["duration_ms"] == 100.0


# ─── PreflightReport Tests ──────────────────────────────────────────


class TestPreflightReport:
    """Tests for the aggregated preflight report."""

    def test_empty_report_passes(self):
        report = PreflightReport()
        assert report.passed is True  # no checks = no blockers
        assert report.pass_count == 0
        assert report.total_count == 0
        assert report.failures == []
        assert report.warnings == []
        assert report.blockers == []

    def test_all_checks_pass(self):
        report = PreflightReport(
            checks=[
                CheckResult(name="a", passed=True),
                CheckResult(name="b", passed=True),
                CheckResult(name="c", passed=True),
            ]
        )
        assert report.passed is True
        assert report.pass_count == 3
        assert report.total_count == 3

    def test_blocker_failure(self):
        report = PreflightReport(
            checks=[
                CheckResult(name="ok", passed=True),
                CheckResult(name="fail", passed=False, severity="blocker"),
            ]
        )
        assert report.passed is False
        assert report.pass_count == 1
        assert report.total_count == 2
        assert len(report.blockers) == 1
        assert report.blockers[0].name == "fail"

    def test_warning_only_still_passes(self):
        report = PreflightReport(
            checks=[
                CheckResult(name="ok", passed=True),
                CheckResult(name="warn", passed=False, severity="warning"),
            ]
        )
        assert report.passed is True  # warnings don't block
        assert len(report.warnings) == 1
        assert len(report.blockers) == 0

    def test_mixed_failures(self):
        report = PreflightReport(
            checks=[
                CheckResult(name="ok", passed=True),
                CheckResult(name="warn", passed=False, severity="warning"),
                CheckResult(name="block", passed=False, severity="blocker"),
            ]
        )
        assert report.passed is False
        assert len(report.failures) == 2
        assert len(report.warnings) == 1
        assert len(report.blockers) == 1

    def test_to_dict(self):
        report = PreflightReport(
            checks=[
                CheckResult(name="a", passed=True, duration_ms=1.0),
                CheckResult(name="b", passed=False, severity="warning", error="nope"),
            ],
            started_at="2026-03-27T06:00:00Z",
            completed_at="2026-03-27T06:00:01Z",
            total_duration_ms=1234.5,
        )
        d = report.to_dict()
        assert d["passed"] is True  # warning only
        assert d["summary"] == "1/2 checks passed"
        assert d["blockers"] == 0
        assert d["warnings"] == 1
        assert d["total_duration_ms"] == 1234.5
        assert len(d["checks"]) == 2

    def test_to_summary_all_pass(self):
        report = PreflightReport(
            checks=[
                CheckResult(name="a", passed=True, duration_ms=5.0),
                CheckResult(name="b", passed=True, duration_ms=10.0),
            ],
            total_duration_ms=15.0,
        )
        summary = report.to_summary()
        assert "🟢" in summary
        assert "2/2" in summary
        assert "15ms" in summary

    def test_to_summary_with_failures(self):
        report = PreflightReport(
            checks=[
                CheckResult(name="ok", passed=True, duration_ms=1.0),
                CheckResult(
                    name="bad", passed=False, severity="blocker", error="broken"
                ),
                CheckResult(
                    name="meh", passed=False, severity="warning", error="flaky"
                ),
            ],
            total_duration_ms=50.0,
        )
        summary = report.to_summary()
        assert "🔴" in summary
        assert "1/3" in summary
        assert "Blockers (1)" in summary
        assert "Warnings (1)" in summary
        assert "broken" in summary
        assert "flaky" in summary


# ─── SwarmPreflight Individual Checks ──────────────────────────────


class TestSwarmPreflightChecks:
    """Tests for individual preflight check methods."""

    def setup_method(self):
        self.preflight = SwarmPreflight(
            api_url="https://api.execution.market",
            state_dir=None,
        )

    def test_check_imports(self):
        """All swarm modules should be importable."""
        result = self.preflight.check_imports()
        assert result.name == "imports"
        assert result.passed is True
        assert "modules imported successfully" in result.details
        assert result.duration_ms >= 0

    def test_check_event_bus(self):
        """EventBus pub/sub should work end-to-end."""
        result = self.preflight.check_event_bus()
        assert result.name == "event_bus"
        assert result.passed is True
        assert "Pub/sub working" in result.details

    def test_check_coordinator_init(self):
        """SwarmCoordinator should be creatable."""
        result = self.preflight.check_coordinator_init()
        assert result.name == "coordinator_init"
        assert result.passed is True

    def test_check_lifecycle_manager(self):
        """LifecycleManager state machine should work."""
        result = self.preflight.check_lifecycle_manager()
        assert result.name == "lifecycle_manager"
        assert result.passed is True
        assert "WORKING" in result.details

    def test_check_phase_gate(self):
        """PhaseGate evaluation should work."""
        result = self.preflight.check_phase_gate()
        assert result.name == "phase_gate"
        assert result.passed is True
        assert "can_advance" in result.details

    def test_check_state_persistence(self):
        """State save/load round-trip should work."""
        result = self.preflight.check_state_persistence()
        assert result.name == "state_persistence"
        assert result.passed is True
        assert "roundtrip" in result.details.lower()

    def test_check_xmtp_bridge_init(self):
        """XMTPBridge should initialize without connections."""
        result = self.preflight.check_xmtp_bridge_init()
        assert result.name == "xmtp_bridge_init"
        assert result.passed is True
        assert "rate_limit" in result.details

    def test_check_integrator_wiring(self):
        """SwarmIntegrator should wire components."""
        result = self.preflight.check_integrator_wiring()
        assert result.name == "integrator_wiring"
        assert result.passed is True
        assert "Components:" in result.details

    def test_check_integrator_dry_run(self):
        """Integrator dry-run cycle should complete."""
        result = self.preflight.check_integrator_dry_run()
        assert result.name == "integrator_dry_run"
        assert result.passed is True
        assert "cycle" in result.details.lower()

    def test_check_budget_guardrails(self):
        """Budget tracking and limits should work."""
        result = self.preflight.check_budget_guardrails()
        assert result.name == "budget_guardrails"
        assert result.passed is True
        assert "Budget tracking" in result.details

    def test_check_api_connectivity_mocked_success(self):
        """API connectivity check passes with mocked healthy response."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status":"healthy"}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.preflight.urlopen", return_value=mock_resp):
            result = self.preflight.check_api_connectivity()
            assert result.name == "api_connectivity"
            assert result.passed is True
            assert result.severity == "warning"

    def test_check_api_connectivity_mocked_failure(self):
        """API connectivity check fails gracefully when API unreachable."""
        from urllib.error import URLError

        with patch(
            "mcp_server.swarm.preflight.urlopen",
            side_effect=URLError("Connection refused"),
        ):
            result = self.preflight.check_api_connectivity()
            assert result.name == "api_connectivity"
            assert result.passed is False
            assert result.severity == "warning"
            assert "unreachable" in result.error.lower()

    def test_check_api_connectivity_timeout(self):
        """API connectivity check handles timeout."""
        with patch(
            "mcp_server.swarm.preflight.urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            result = self.preflight.check_api_connectivity()
            assert result.passed is False
            assert result.severity == "warning"

    def test_check_api_connectivity_http_error(self):
        """API connectivity check handles HTTP errors."""
        from urllib.error import HTTPError

        with patch(
            "mcp_server.swarm.preflight.urlopen",
            side_effect=HTTPError(
                "https://api.execution.market/health", 500, "Server Error", {}, None
            ),
        ):
            result = self.preflight.check_api_connectivity()
            assert result.passed is False
            assert result.severity == "warning"


# ─── SwarmPreflight run_all() ───────────────────────────────────────


class TestSwarmPreflightRunAll:
    """Tests for the full preflight pipeline."""

    def test_run_all_offline(self):
        """run_all() should complete with most checks passing (API may fail)."""
        preflight = SwarmPreflight(api_url="http://localhost:99999")
        report = preflight.run_all()

        assert isinstance(report, PreflightReport)
        assert report.total_count == 11  # Total number of checks
        assert report.started_at is not None
        assert report.completed_at is not None
        assert report.total_duration_ms > 0

        # All non-API checks should pass
        non_api = [c for c in report.checks if c.name != "api_connectivity"]
        for c in non_api:
            assert c.passed is True, f"Check {c.name} failed: {c.error}"

    def test_run_all_with_mocked_api(self):
        """run_all() should fully pass with mocked API."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status":"healthy"}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("mcp_server.swarm.preflight.urlopen", return_value=mock_resp):
            preflight = SwarmPreflight()
            report = preflight.run_all()

            assert report.passed is True
            assert report.pass_count == report.total_count

    def test_run_all_handles_check_exception(self):
        """run_all() should gracefully handle exceptions in individual checks."""
        preflight = SwarmPreflight()

        # Monkey-patch check_event_bus with a named function that raises
        def check_event_bus():
            raise RuntimeError("test boom")

        preflight.check_event_bus = check_event_bus

        report = preflight.run_all()

        # The failing check should be recorded as a failure
        failed = [
            c for c in report.checks if not c.passed and "test boom" in (c.error or "")
        ]
        assert len(failed) == 1
        assert failed[0].passed is False

    def test_run_all_timing(self):
        """run_all() should record reasonable timing."""
        preflight = SwarmPreflight(api_url="http://localhost:99999")
        report = preflight.run_all()

        # Should complete in under 30 seconds (usually < 1 second)
        assert report.total_duration_ms < 30000

        # Each check should have positive duration
        for c in report.checks:
            assert c.duration_ms >= 0

    def test_run_all_report_serializable(self):
        """Report should be JSON-serializable."""
        preflight = SwarmPreflight(api_url="http://localhost:99999")
        report = preflight.run_all()
        d = report.to_dict()
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["passed"] is True or parsed["passed"] is False

    def test_run_all_summary_readable(self):
        """Report summary should be human-readable."""
        preflight = SwarmPreflight(api_url="http://localhost:99999")
        report = preflight.run_all()
        summary = report.to_summary()
        assert "Pre-Flight Report" in summary
        assert "/" in summary  # e.g. "10/11"


# ─── Custom API URL ────────────────────────────────────────────────


class TestSwarmPreflightConfig:
    """Tests for preflight configuration."""

    def test_custom_api_url(self):
        preflight = SwarmPreflight(api_url="https://custom.api.example.com/")
        assert (
            preflight.api_url == "https://custom.api.example.com"
        )  # trailing slash stripped

    def test_custom_state_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            preflight = SwarmPreflight(state_dir=tmp)
            assert preflight.state_dir == tmp

    def test_default_api_url(self):
        preflight = SwarmPreflight()
        assert preflight.api_url == "https://api.execution.market"


# ─── Edge Cases ────────────────────────────────────────────────────


class TestPreflightEdgeCases:
    """Edge cases and boundary conditions."""

    def test_check_result_zero_duration(self):
        result = CheckResult(name="instant", passed=True, duration_ms=0.0)
        assert result.to_dict()["duration_ms"] == 0.0

    def test_check_result_large_duration(self):
        result = CheckResult(name="slow", passed=True, duration_ms=99999.999)
        d = result.to_dict()
        assert d["duration_ms"] == 100000.0  # rounded to 1 decimal

    def test_report_all_failed(self):
        report = PreflightReport(
            checks=[
                CheckResult(name="a", passed=False, severity="blocker"),
                CheckResult(name="b", passed=False, severity="blocker"),
            ]
        )
        assert report.passed is False
        assert report.pass_count == 0
        assert len(report.blockers) == 2

    def test_report_timestamps(self):
        report = PreflightReport(
            started_at="2026-03-27T06:00:00Z",
            completed_at="2026-03-27T06:00:05Z",
            total_duration_ms=5000,
        )
        d = report.to_dict()
        assert d["started_at"] == "2026-03-27T06:00:00Z"
        assert d["completed_at"] == "2026-03-27T06:00:05Z"

    def test_report_no_timestamps(self):
        report = PreflightReport()
        d = report.to_dict()
        assert d["started_at"] is None
        assert d["completed_at"] is None

    def test_multiple_run_all_calls(self):
        """Preflight should be rerunnable."""
        preflight = SwarmPreflight(api_url="http://localhost:99999")
        r1 = preflight.run_all()
        r2 = preflight.run_all()
        assert r1.total_count == r2.total_count
