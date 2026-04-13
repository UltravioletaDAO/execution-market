"""
Tests for SwarmPreflight — Phase 0 activation validation.

Covers:
- CheckResult and PreflightReport data models
- All individual pre-flight checks
- Full run_all() execution
- Report generation (dict, summary)
"""

import pytest
from unittest.mock import patch, MagicMock

from mcp_server.swarm.preflight import (
    SwarmPreflight,
    CheckResult,
    PreflightReport,
)


# ─── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def preflight():
    return SwarmPreflight(
        api_url="https://api.execution.market",
    )


# ─── Data Models ───────────────────────────────────────────────────


class TestCheckResult:
    """CheckResult data model."""

    def test_defaults(self):
        r = CheckResult(name="test", passed=True)
        assert r.severity == "blocker"
        assert r.error is None
        assert r.duration_ms == 0


class TestPreflightReport:
    """PreflightReport aggregation logic."""

    def test_all_pass(self):
        r = PreflightReport(
            checks=[
                CheckResult("a", True),
                CheckResult("b", True),
            ]
        )
        assert r.passed is True
        assert r.pass_count == 2
        assert len(r.failures) == 0

    def test_blocker_fails_report(self):
        r = PreflightReport(
            checks=[
                CheckResult("a", True),
                CheckResult("b", False, severity="blocker"),
            ]
        )
        assert r.passed is False
        assert len(r.blockers) == 1

    def test_warning_doesnt_fail_report(self):
        r = PreflightReport(
            checks=[
                CheckResult("a", True),
                CheckResult("b", False, severity="warning"),
            ]
        )
        assert r.passed is True  # Warnings don't fail
        assert len(r.warnings) == 1

    def test_to_summary_readable(self):
        r = PreflightReport(
            checks=[
                CheckResult("imports", True, duration_ms=5),
                CheckResult("api", False, error="timeout", severity="warning"),
            ]
        )
        r.total_duration_ms = 50
        summary = r.to_summary()
        assert "Pre-Flight Report" in summary
        assert "✅ imports" in summary
        assert "⚠️ api" in summary

    def test_total_count(self):
        r = PreflightReport(
            checks=[
                CheckResult("a", True),
                CheckResult("b", True),
                CheckResult("c", False),
            ]
        )
        assert r.total_count == 3
        assert r.pass_count == 2


# ─── Individual Checks ────────────────────────────────────────────


class TestCheckImports:
    """check_imports — module import validation."""

    def test_all_imports_pass(self, preflight):
        result = preflight.check_imports()
        assert result.passed is True
        assert "modules imported" in result.details

    def test_import_count(self, preflight):
        result = preflight.check_imports()
        # Should import 23+ modules
        assert "23/23" in result.details or result.passed


class TestCheckEventBus:
    """check_event_bus — pub/sub verification."""

    def test_event_bus_works(self, preflight):
        result = preflight.check_event_bus()
        assert result.passed is True
        assert "Pub/sub working" in result.details


class TestCheckCoordinatorInit:
    """check_coordinator_init — coordinator creation."""

    def test_coordinator_creates(self, preflight):
        result = preflight.check_coordinator_init()
        assert result.passed is True


class TestCheckLifecycleManager:
    """check_lifecycle_manager — state machine validation."""

    def test_state_machine_works(self, preflight):
        result = preflight.check_lifecycle_manager()
        assert result.passed is True
        assert "WORKING" in result.details


class TestCheckPhaseGate:
    """check_phase_gate — phase evaluation."""

    def test_phase_gate_evaluates(self, preflight):
        result = preflight.check_phase_gate()
        assert result.passed is True
        assert "Phase 0" in result.details


class TestCheckStatePersistence:
    """check_state_persistence — save/load roundtrip."""

    def test_persistence_roundtrip(self, preflight):
        result = preflight.check_state_persistence()
        assert result.passed is True
        assert "roundtrip" in result.details.lower()


class TestCheckXMTPBridgeInit:
    """check_xmtp_bridge_init — bridge initialization."""

    def test_bridge_initializes(self, preflight):
        result = preflight.check_xmtp_bridge_init()
        assert result.passed is True
        assert "rate_limit" in result.details


class TestCheckIntegratorWiring:
    """check_integrator_wiring — component wiring."""

    def test_integrator_wires(self, preflight):
        result = preflight.check_integrator_wiring()
        assert result.passed is True
        assert "Components" in result.details


class TestCheckIntegratorDryRun:
    """check_integrator_dry_run — dry-run cycle."""

    def test_dry_run_completes(self, preflight):
        result = preflight.check_integrator_dry_run()
        assert result.passed is True
        assert "Dry-run cycle" in result.details


class TestCheckBudgetGuardrails:
    """check_budget_guardrails — spending limit enforcement."""

    def test_budgets_enforced(self, preflight):
        result = preflight.check_budget_guardrails()
        assert result.passed is True
        assert "enforcement" in result.details.lower()


class TestCheckAPIConnectivity:
    """check_api_connectivity — live API check (warning severity)."""

    @patch("mcp_server.swarm.preflight.urlopen")
    def test_api_check_is_warning_severity(self, mock_urlopen, preflight):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status":"ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = preflight.check_api_connectivity()
        assert result.severity == "warning"

    @patch("mcp_server.swarm.preflight.urlopen")
    def test_api_connectivity_success(self, mock_urlopen, preflight):
        """Should pass when API responds with 200."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status":"ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = preflight.check_api_connectivity()
        assert result.name == "api_connectivity"
        assert result.passed is True

    @patch("mcp_server.swarm.preflight.urlopen")
    def test_api_connectivity_failure(self, mock_urlopen, preflight):
        """Should fail gracefully when API is down."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")
        result = preflight.check_api_connectivity()
        assert result.name == "api_connectivity"
        assert result.passed is False
        assert result.error is not None


# ─── Full Run ─────────────────────────────────────────────────────


class TestRunAll:
    """Full pre-flight run."""

    @patch("mcp_server.swarm.preflight.urlopen")
    def test_run_all_completes(self, mock_urlopen, preflight):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status":"ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        report = preflight.run_all()
        assert isinstance(report, PreflightReport)
        assert report.total_count >= 10
        assert report.started_at is not None
        assert report.completed_at is not None
        assert report.total_duration_ms > 0

    @patch("mcp_server.swarm.preflight.urlopen")
    def test_run_all_local_checks_pass(self, mock_urlopen, preflight):
        """All local checks (non-API) should pass."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status":"ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        report = preflight.run_all()
        local_checks = [c for c in report.checks if c.severity == "blocker"]
        for c in local_checks:
            assert c.passed is True, f"Blocker check failed: {c.name} — {c.error}"

    @patch("mcp_server.swarm.preflight.urlopen")
    def test_report_dict_serializable(self, mock_urlopen, preflight):
        """Report dict should be JSON-serializable."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status":"ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        report = preflight.run_all()
        import json

        json_str = json.dumps(report.to_dict())
        assert len(json_str) > 100

    @patch("mcp_server.swarm.preflight.urlopen")
    def test_report_summary_readable(self, mock_urlopen, preflight):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status":"ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        report = preflight.run_all()
        summary = report.to_summary()
        assert "Pre-Flight Report" in summary
        assert "checks passed" in summary.lower() or "passed" in summary.lower()
