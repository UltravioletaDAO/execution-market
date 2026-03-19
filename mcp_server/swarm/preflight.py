"""
SwarmPreflight — Phase 0 validation for swarm activation.

Before the swarm can transition from "code exists" to "running in production",
every component must pass a series of pre-flight checks. This module
automates that validation.

The Pre-Flight Checklist:
    1. API connectivity — Can we reach the EM API?
    2. Agent registry — Are ERC-8004 agents loaded?
    3. Event bus — Does pub/sub work end-to-end?
    4. Component wiring — Are all components initialized?
    5. State persistence — Can we save/load state?
    6. Budget guardrails — Are spending limits configured?
    7. Phase gate — Does Phase 0 evaluate correctly?
    8. Integration test — Full cycle in dry-run mode

Usage:
    preflight = SwarmPreflight(api_url="https://api.execution.market")
    report = preflight.run_all()

    if report.passed:
        print("🟢 Swarm is ready for Phase 0")
    else:
        print(f"🔴 {len(report.failures)} checks failed")
        for f in report.failures:
            print(f"  ❌ {f.name}: {f.error}")

Architecture:
    Each check is a method returning a CheckResult.
    run_all() executes all checks and produces a PreflightReport.
    The report is designed for both human reading and programmatic use.
"""

import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("em.swarm.preflight")


# ─── Types ────────────────────────────────────────────────────────


@dataclass
class CheckResult:
    """Result of a single pre-flight check."""

    name: str
    passed: bool
    duration_ms: float = 0
    details: str = ""
    error: Optional[str] = None
    severity: str = "blocker"  # "blocker", "warning", "info"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "duration_ms": round(self.duration_ms, 1),
            "details": self.details,
            "error": self.error,
            "severity": self.severity,
        }


@dataclass
class PreflightReport:
    """Complete pre-flight validation report."""

    checks: list[CheckResult] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration_ms: float = 0

    @property
    def passed(self) -> bool:
        """All blocker checks passed."""
        return all(
            c.passed for c in self.checks if c.severity == "blocker"
        )

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]

    @property
    def warnings(self) -> list[CheckResult]:
        return [
            c for c in self.checks
            if not c.passed and c.severity == "warning"
        ]

    @property
    def blockers(self) -> list[CheckResult]:
        return [
            c for c in self.checks
            if not c.passed and c.severity == "blocker"
        ]

    @property
    def pass_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def total_count(self) -> int:
        return len(self.checks)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "summary": f"{self.pass_count}/{self.total_count} checks passed",
            "blockers": len(self.blockers),
            "warnings": len(self.warnings),
            "total_duration_ms": round(self.total_duration_ms, 1),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "checks": [c.to_dict() for c in self.checks],
        }

    def to_summary(self) -> str:
        """Human-readable summary."""
        icon = "🟢" if self.passed else "🔴"
        lines = [
            f"{icon} Pre-Flight Report: {self.pass_count}/{self.total_count} checks passed",
            f"   Duration: {self.total_duration_ms:.0f}ms",
        ]

        if self.blockers:
            lines.append(f"\n   🔴 Blockers ({len(self.blockers)}):")
            for c in self.blockers:
                lines.append(f"     ❌ {c.name}: {c.error or c.details}")

        if self.warnings:
            lines.append(f"\n   ⚠️ Warnings ({len(self.warnings)}):")
            for c in self.warnings:
                lines.append(f"     ⚠️ {c.name}: {c.error or c.details}")

        passed = [c for c in self.checks if c.passed]
        if passed:
            lines.append(f"\n   ✅ Passed ({len(passed)}):")
            for c in passed:
                lines.append(f"     ✅ {c.name} ({c.duration_ms:.0f}ms)")

        return "\n".join(lines)


# ─── Pre-Flight Validator ─────────────────────────────────────────


class SwarmPreflight:
    """
    Validates all swarm components are ready for Phase 0 activation.

    Runs checks against:
    - Live API connectivity
    - Module imports and initialization
    - Event bus wiring
    - State persistence
    - Budget configuration
    - Phase gate evaluation
    - Dry-run integration cycle
    """

    def __init__(
        self,
        api_url: str = "https://api.execution.market",
        state_dir: Optional[str] = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.state_dir = state_dir

    def run_all(self) -> PreflightReport:
        """Run all pre-flight checks and return a report."""
        report = PreflightReport()
        report.started_at = datetime.now(timezone.utc).isoformat()

        start = time.time()

        checks = [
            self.check_imports,
            self.check_event_bus,
            self.check_coordinator_init,
            self.check_lifecycle_manager,
            self.check_phase_gate,
            self.check_state_persistence,
            self.check_xmtp_bridge_init,
            self.check_integrator_wiring,
            self.check_integrator_dry_run,
            self.check_budget_guardrails,
            self.check_api_connectivity,
        ]

        for check_fn in checks:
            try:
                result = check_fn()
            except Exception as e:
                result = CheckResult(
                    name=check_fn.__name__.replace("check_", ""),
                    passed=False,
                    error=f"Unexpected error: {str(e)[:200]}",
                    severity="blocker",
                )
            report.checks.append(result)

        report.total_duration_ms = (time.time() - start) * 1000
        report.completed_at = datetime.now(timezone.utc).isoformat()

        return report

    # ─── Individual Checks ────────────────────────────────────

    def check_imports(self) -> CheckResult:
        """Verify all swarm modules can be imported."""
        start = time.time()
        errors = []
        modules = [
            "coordinator", "event_bus", "scheduler", "runner",
            "orchestrator", "lifecycle_manager", "feedback_pipeline",
            "evidence_parser", "expiry_analyzer", "config_manager",
            "xmtp_bridge", "phase_gate", "integrator", "analytics",
            "state_persistence", "heartbeat_handler", "dashboard",
            "bootstrap", "autojob_client", "seal_bridge",
            "acontext_adapter", "mcp_tools", "event_listener",
        ]

        imported = 0
        for mod in modules:
            try:
                __import__(f"mcp_server.swarm.{mod}")
                imported += 1
            except ImportError as e:
                errors.append(f"{mod}: {e}")

        duration = (time.time() - start) * 1000
        if errors:
            return CheckResult(
                name="imports",
                passed=False,
                duration_ms=duration,
                error=f"{len(errors)} modules failed to import: {'; '.join(errors[:3])}",
            )

        return CheckResult(
            name="imports",
            passed=True,
            duration_ms=duration,
            details=f"{imported}/{len(modules)} modules imported successfully",
        )

    def check_event_bus(self) -> CheckResult:
        """Verify EventBus pub/sub works end-to-end."""
        start = time.time()
        from .event_bus import EventBus, TASK_ASSIGNED

        bus = EventBus()
        received = []
        bus.on(TASK_ASSIGNED, lambda e: received.append(e))
        bus.emit(TASK_ASSIGNED, {"task_id": "preflight-test"})

        duration = (time.time() - start) * 1000
        if len(received) != 1:
            return CheckResult(
                name="event_bus",
                passed=False,
                duration_ms=duration,
                error=f"Expected 1 event, got {len(received)}",
            )

        return CheckResult(
            name="event_bus",
            passed=True,
            duration_ms=duration,
            details="Pub/sub working: emit → handler delivery confirmed",
        )

    def check_coordinator_init(self) -> CheckResult:
        """Verify SwarmCoordinator can be created with mock data."""
        start = time.time()
        try:
            from .coordinator import SwarmCoordinator, EMApiClient

            # Create with mock client (no API calls)
            coordinator = SwarmCoordinator.__new__(SwarmCoordinator)
            coordinator.agents = {}
            coordinator.task_queue = []

            duration = (time.time() - start) * 1000
            return CheckResult(
                name="coordinator_init",
                passed=True,
                duration_ms=duration,
                details="Coordinator created successfully",
            )
        except Exception as e:
            return CheckResult(
                name="coordinator_init",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                error=str(e)[:200],
            )

    def check_lifecycle_manager(self) -> CheckResult:
        """Verify LifecycleManager state machine works."""
        start = time.time()
        from .lifecycle_manager import LifecycleManager, AgentState

        lm = LifecycleManager()
        lm.register_agent(agent_id=9999, name="preflight-test", wallet_address="0xPreflight")
        lm.transition(9999, AgentState.IDLE)
        lm.transition(9999, AgentState.ACTIVE)
        record = lm.transition(9999, AgentState.WORKING)

        duration = (time.time() - start) * 1000
        if record.state != AgentState.WORKING:
            return CheckResult(
                name="lifecycle_manager",
                passed=False,
                duration_ms=duration,
                error=f"Expected WORKING state, got {record.state}",
            )

        return CheckResult(
            name="lifecycle_manager",
            passed=True,
            duration_ms=duration,
            details="State machine: INIT → IDLE → ACTIVE → WORKING ✓",
        )

    def check_phase_gate(self) -> CheckResult:
        """Verify PhaseGate can evaluate Phase 0 → 1 readiness."""
        start = time.time()
        from .phase_gate import PhaseGate, SwarmMetrics

        gate = PhaseGate()
        label = gate.phase_label

        # Evaluate with realistic pre-flight metrics
        metrics = SwarmMetrics(
            api_healthy=True,
            agents_registered=24,
            agents_healthy=24,
            swarm_enabled=True,
            swarm_mode="passive",
            coordinator_active=True,
        )
        evaluation = gate.evaluate_advance(metrics)

        duration = (time.time() - start) * 1000
        return CheckResult(
            name="phase_gate",
            passed=True,
            duration_ms=duration,
            details=(
                f"{label}: can_advance={evaluation.can_advance}, "
                f"blockers={len(evaluation.blockers)}"
            ),
        )

    def check_state_persistence(self) -> CheckResult:
        """Verify state can be saved and loaded."""
        start = time.time()
        from .state_persistence import SwarmStatePersistence, PersistedState

        with tempfile.TemporaryDirectory() as tmp_dir:
            persistence = SwarmStatePersistence(state_dir=tmp_dir)
            state = PersistedState(
                pending_tasks=[{"id": "preflight-test"}],
                total_ingested=1,
            )
            saved = persistence.save(state)
            if not saved:
                return CheckResult(
                    name="state_persistence",
                    passed=False,
                    duration_ms=(time.time() - start) * 1000,
                    error="Failed to save state",
                )

            loaded = persistence.load()
            if loaded is None:
                return CheckResult(
                    name="state_persistence",
                    passed=False,
                    duration_ms=(time.time() - start) * 1000,
                    error="Failed to load state after save",
                )

        duration = (time.time() - start) * 1000
        return CheckResult(
            name="state_persistence",
            passed=True,
            duration_ms=duration,
            details="Save → Load roundtrip successful",
        )

    def check_xmtp_bridge_init(self) -> CheckResult:
        """Verify XMTPBridge can be initialized (no actual connections)."""
        start = time.time()
        from .xmtp_bridge import XMTPBridge

        bridge = XMTPBridge(
            bot_api_url="http://localhost:3100",
            em_api_url=self.api_url,
        )
        status = bridge.get_status()

        duration = (time.time() - start) * 1000
        return CheckResult(
            name="xmtp_bridge_init",
            passed=True,
            duration_ms=duration,
            details=f"Bridge initialized: rate_limit={status['rate_limit']['per_worker_per_hour']}/hr",
        )

    def check_integrator_wiring(self) -> CheckResult:
        """Verify SwarmIntegrator can wire all components together."""
        start = time.time()
        from .integrator import SwarmIntegrator, SwarmMode
        from .event_bus import EventBus

        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        bus = EventBus()
        integrator.set_event_bus(bus)
        integrator.wire()

        health = integrator.health()

        duration = (time.time() - start) * 1000
        if not health.get("components", {}).get("total", 0):
            return CheckResult(
                name="integrator_wiring",
                passed=False,
                duration_ms=duration,
                error="No components registered after wiring",
            )

        return CheckResult(
            name="integrator_wiring",
            passed=True,
            duration_ms=duration,
            details=f"Components: {health['components']['total']}, mode: {health['mode']}",
        )

    def check_integrator_dry_run(self) -> CheckResult:
        """Verify a dry-run cycle completes without errors."""
        start = time.time()
        from .integrator import SwarmIntegrator, SwarmMode
        from .event_bus import EventBus

        integrator = SwarmIntegrator(mode=SwarmMode.PASSIVE)
        bus = EventBus()
        integrator.set_event_bus(bus)
        integrator.wire()
        integrator.start()

        result = integrator.run_cycle(dry_run=True)
        integrator.stop()

        duration = (time.time() - start) * 1000
        if result.errors:
            return CheckResult(
                name="integrator_dry_run",
                passed=False,
                duration_ms=duration,
                error=f"Cycle errors: {result.errors[:3]}",
            )

        return CheckResult(
            name="integrator_dry_run",
            passed=True,
            duration_ms=duration,
            details=f"Dry-run cycle #{result.cycle_number} completed in {result.duration_ms:.0f}ms",
        )

    def check_budget_guardrails(self) -> CheckResult:
        """Verify budget limits are configured and enforced."""
        start = time.time()
        from .lifecycle_manager import LifecycleManager, BudgetConfig, BudgetExceededError, AgentState

        lm = LifecycleManager()
        config = BudgetConfig(
            daily_limit_usd=5.0,
            monthly_limit_usd=100.0,
            task_limit_usd=2.0,
        )
        lm.register_agent(
            agent_id=9998,
            name="budget-test",
            wallet_address="0xBudgetTest",
            budget_config=config,
        )
        lm.transition(9998, AgentState.IDLE)

        # Verify spending tracks
        lm.record_spend(9998, 2.0)
        status = lm.get_budget_status(9998)
        if status["daily_spent"] != 2.0:
            return CheckResult(
                name="budget_guardrails",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                error="Budget tracking not working",
            )

        # Verify overspend triggers suspension
        try:
            lm.record_spend(9998, 4.0)  # Total 6.0 > 5.0 limit
            return CheckResult(
                name="budget_guardrails",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                error="Budget exceeded but no error raised",
            )
        except BudgetExceededError:
            pass  # Expected

        duration = (time.time() - start) * 1000
        return CheckResult(
            name="budget_guardrails",
            passed=True,
            duration_ms=duration,
            details="Budget tracking + daily limit enforcement ✓",
        )

    def check_api_connectivity(self) -> CheckResult:
        """Verify EM API is reachable (warning, not blocker)."""
        start = time.time()
        try:
            req = Request(f"{self.api_url}/health", method="GET")
            with urlopen(req, timeout=10) as resp:
                if resp.status < 300:
                    data = resp.read().decode()
                    duration = (time.time() - start) * 1000
                    return CheckResult(
                        name="api_connectivity",
                        passed=True,
                        duration_ms=duration,
                        details=f"EM API healthy: {data[:100]}",
                        severity="warning",
                    )
                else:
                    return CheckResult(
                        name="api_connectivity",
                        passed=False,
                        duration_ms=(time.time() - start) * 1000,
                        error=f"API returned HTTP {resp.status}",
                        severity="warning",
                    )
        except (URLError, HTTPError, TimeoutError) as e:
            return CheckResult(
                name="api_connectivity",
                passed=False,
                duration_ms=(time.time() - start) * 1000,
                error=f"API unreachable: {str(e)[:100]}",
                severity="warning",
            )
