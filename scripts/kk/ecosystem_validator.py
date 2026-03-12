#!/usr/bin/env python3
"""
Ecosystem Validator — One-command verification of all Ultravioleta projects.

Validates:
  1. Execution Market (Python tests + API health)
  2. AutoJob (Python tests + server health)
  3. describe-net (Foundry/Forge tests)
  4. KK V2 Swarm (all 7 modules, 295 tests)
  5. Cross-project integration points

Usage:
  python3 scripts/kk/ecosystem_validator.py           # Full validation
  python3 scripts/kk/ecosystem_validator.py --quick    # Tests only, skip API checks
  python3 scripts/kk/ecosystem_validator.py --live     # Include live API integration tests
"""

import subprocess
import sys
import time
import json
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ── Project Roots ──────────────────────────────────────────────────

PROJECTS_ROOT = Path.home() / "clawd" / "projects"

PROJECTS = {
    "execution-market": PROJECTS_ROOT / "execution-market",
    "autojob": PROJECTS_ROOT / "autojob",
    "describe-net": PROJECTS_ROOT / "describe-net-contracts",
}

# ── Data Classes ───────────────────────────────────────────────────

@dataclass
class TestResult:
    project: str
    suite: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_s: float = 0.0
    output: str = ""
    success: bool = True


@dataclass
class HealthCheck:
    service: str
    url: str
    status: str = "unknown"
    latency_ms: float = 0.0
    details: str = ""
    success: bool = False


@dataclass
class EcosystemReport:
    timestamp: str = ""
    test_results: list = field(default_factory=list)
    health_checks: list = field(default_factory=list)
    total_passed: int = 0
    total_failed: int = 0
    total_duration_s: float = 0.0
    all_green: bool = True


# ── Test Runners ───────────────────────────────────────────────────

def run_pytest(project: str, root: Path, test_paths: list[str],
               suite_name: str, timeout: int = 120) -> TestResult:
    """Run pytest and parse results."""
    result = TestResult(project=project, suite=suite_name)
    start = time.time()

    cmd = [
        sys.executable, "-m", "pytest",
        *test_paths,
        "--tb=no", "-q", "--no-header"
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout
        )
        result.output = proc.stdout + proc.stderr
        result.duration_s = time.time() - start

        # Parse "X passed, Y failed" line
        for line in result.output.split("\n"):
            line = line.strip()
            if "passed" in line or "failed" in line or "error" in line:
                import re
                passed_m = re.search(r"(\d+) passed", line)
                failed_m = re.search(r"(\d+) failed", line)
                error_m = re.search(r"(\d+) error", line)
                skipped_m = re.search(r"(\d+) skipped", line)
                if passed_m:
                    result.passed = int(passed_m.group(1))
                if failed_m:
                    result.failed = int(failed_m.group(1))
                if error_m:
                    result.errors = int(error_m.group(1))
                if skipped_m:
                    result.skipped = int(skipped_m.group(1))

        result.success = proc.returncode == 0

    except subprocess.TimeoutExpired:
        result.duration_s = time.time() - start
        result.output = f"TIMEOUT after {timeout}s"
        result.success = False
    except Exception as e:
        result.duration_s = time.time() - start
        result.output = str(e)
        result.success = False

    return result


def run_forge_tests(root: Path) -> TestResult:
    """Run Foundry/Forge tests for Solidity contracts."""
    result = TestResult(project="describe-net", suite="forge-tests")
    start = time.time()

    try:
        proc = subprocess.run(
            ["forge", "test", "--no-match-test", "testFuzz"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=120
        )
        result.output = proc.stdout + proc.stderr
        result.duration_s = time.time() - start

        import re
        # Parse forge output: "Test result: ok. X passed; Y failed;"
        for line in result.output.split("\n"):
            ok_m = re.search(r"(\d+) passed.*?(\d+) failed", line)
            if ok_m:
                result.passed = int(ok_m.group(1))
                result.failed = int(ok_m.group(2))

        # Also count individual test passes from [PASS] lines
        if result.passed == 0:
            result.passed = len(re.findall(r"\[PASS\]", result.output))
            result.failed = len(re.findall(r"\[FAIL\]", result.output))

        result.success = proc.returncode == 0

    except FileNotFoundError:
        result.output = "forge not found (Foundry not installed)"
        result.success = False
        result.duration_s = time.time() - start
    except subprocess.TimeoutExpired:
        result.output = "TIMEOUT after 120s"
        result.success = False
        result.duration_s = time.time() - start
    except Exception as e:
        result.output = str(e)
        result.success = False
        result.duration_s = time.time() - start

    return result


# ── Health Checks ──────────────────────────────────────────────────

def check_health(service: str, url: str, timeout: int = 10) -> HealthCheck:
    """Check API health endpoint."""
    check = HealthCheck(service=service, url=url)
    start = time.time()

    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "ecosystem-validator/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            check.latency_ms = (time.time() - start) * 1000
            data = json.loads(resp.read().decode())
            check.status = data.get("status", "unknown")
            check.success = check.status == "healthy"
            check.details = json.dumps(data, indent=2)[:500]
    except Exception as e:
        check.latency_ms = (time.time() - start) * 1000
        check.status = "unreachable"
        check.details = str(e)[:200]
        check.success = False

    return check


# ── Main Validator ─────────────────────────────────────────────────

def validate_ecosystem(quick: bool = False, live: bool = False) -> EcosystemReport:
    """Run full ecosystem validation."""
    report = EcosystemReport(
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S %Z")
    )
    start = time.time()

    print("=" * 60)
    print("  🦞 ULTRAVIOLETA ECOSYSTEM VALIDATOR")
    print("=" * 60)
    print()

    em_root = PROJECTS["execution-market"]
    aj_root = PROJECTS["autojob"]
    dn_root = PROJECTS["describe-net"]

    # ── 1. Execution Market — Core Tests ───────────────────────
    print("📦 [1/6] Execution Market — Core Tests...")
    em_core = run_pytest(
        "execution-market", em_root,
        ["tests/", "mcp_server/tests/",
         "--ignore=tests/test_swarm_coordinator.py",
         "--ignore=tests/test_autojob_integration.py",
         "--ignore=mcp_server/tests/test_evidence_parser.py",
         "--ignore=mcp_server/tests/test_event_listener.py",
         "--ignore=mcp_server/tests/test_swarm_lifecycle.py",
         "--ignore=mcp_server/tests/test_swarm_orchestrator.py",
         "--ignore=mcp_server/tests/test_swarm_reputation_bridge.py"],
        "em-core",
        timeout=180
    )
    report.test_results.append(em_core)
    status = "✅" if em_core.success else "❌"
    print(f"   {status} {em_core.passed} passed, {em_core.failed} failed ({em_core.duration_s:.1f}s)")

    # ── 2. KK V2 Swarm — All 7 Modules ────────────────────────
    print("🐝 [2/6] KK V2 Swarm — 7 Modules...")
    swarm_tests = [
        "tests/test_swarm_coordinator.py",
        "tests/test_autojob_integration.py",
        "mcp_server/tests/test_evidence_parser.py",
        "mcp_server/tests/test_event_listener.py",
        "mcp_server/tests/test_swarm_lifecycle.py",
        "mcp_server/tests/test_swarm_orchestrator.py",
        "mcp_server/tests/test_swarm_reputation_bridge.py",
    ]
    swarm = run_pytest(
        "execution-market", em_root,
        swarm_tests,
        "kk-v2-swarm",
        timeout=120
    )
    report.test_results.append(swarm)
    status = "✅" if swarm.success else "❌"
    print(f"   {status} {swarm.passed} passed, {swarm.failed} failed ({swarm.duration_s:.1f}s)")

    # ── 3. AutoJob ─────────────────────────────────────────────
    print("🔍 [3/6] AutoJob — Evidence Matching Engine...")
    if aj_root.exists():
        autojob = run_pytest(
            "autojob", aj_root,
            ["tests/"],
            "autojob-tests",
            timeout=120
        )
        report.test_results.append(autojob)
        status = "✅" if autojob.success else "❌"
        print(f"   {status} {autojob.passed} passed, {autojob.failed} failed ({autojob.duration_s:.1f}s)")
    else:
        print(f"   ⚠️  AutoJob not found at {aj_root}")

    # ── 4. describe-net Contracts ──────────────────────────────
    print("⛓️  [4/6] describe-net — Solidity Contracts...")
    if dn_root.exists():
        describe = run_forge_tests(dn_root)
        report.test_results.append(describe)
        status = "✅" if describe.success else "❌"
        print(f"   {status} {describe.passed} passed, {describe.failed} failed ({describe.duration_s:.1f}s)")
    else:
        print(f"   ⚠️  describe-net not found at {dn_root}")

    # ── 5. API Health Checks ───────────────────────────────────
    if not quick:
        print("🌐 [5/6] API Health Checks...")
        em_health = check_health("execution-market", "https://api.execution.market/health")
        report.health_checks.append(em_health)
        status = "✅" if em_health.success else "❌"
        print(f"   {status} EM API: {em_health.status} ({em_health.latency_ms:.0f}ms)")

        erc8128 = check_health("erc-8128-auth", "https://api.execution.market/api/v1/auth/erc8128/info")
        # ERC-8128 info endpoint returns {supported: true}, not {status: "healthy"}
        if not erc8128.success and "supported" in erc8128.details:
            erc8128.success = True
            erc8128.status = "supported"
        report.health_checks.append(erc8128)
        status = "✅" if erc8128.success else "❌"
        print(f"   {status} ERC-8128 Auth: {erc8128.status} ({erc8128.latency_ms:.0f}ms)")
    else:
        print("⏩ [5/6] API Health Checks — SKIPPED (--quick)")

    # ── 6. Cross-Project Integration ───────────────────────────
    if live:
        print("🔗 [6/6] Cross-Project Integration (live)...")
        # Test that swarm can read live EM tasks
        integration = run_pytest(
            "execution-market", em_root,
            ["tests/test_autojob_integration.py", "-k", "live"],
            "cross-project-live",
            timeout=30
        )
        report.test_results.append(integration)
        status = "✅" if integration.success else "⚠️ "
        print(f"   {status} Live integration: {integration.passed} passed ({integration.duration_s:.1f}s)")
    else:
        print("⏩ [6/6] Live Integration — SKIPPED (use --live)")

    # ── Summary ────────────────────────────────────────────────
    report.total_duration_s = time.time() - start
    report.total_passed = sum(r.passed for r in report.test_results)
    report.total_failed = sum(r.failed for r in report.test_results)
    report.all_green = all(r.success for r in report.test_results) and \
                       all(h.success for h in report.health_checks)

    print()
    print("=" * 60)
    verdict = "🟢 ALL GREEN" if report.all_green else "🔴 ISSUES DETECTED"
    print(f"  {verdict}")
    print(f"  Total: {report.total_passed} passed, {report.total_failed} failed")
    print(f"  Duration: {report.total_duration_s:.1f}s")
    print("=" * 60)

    # Project breakdown
    print()
    print("  Project Breakdown:")
    for r in report.test_results:
        icon = "✅" if r.success else "❌"
        print(f"    {icon} {r.project}/{r.suite}: {r.passed} passed ({r.duration_s:.1f}s)")

    if report.health_checks:
        print()
        print("  API Services:")
        for h in report.health_checks:
            icon = "✅" if h.success else "❌"
            print(f"    {icon} {h.service}: {h.status} ({h.latency_ms:.0f}ms)")

    print()
    return report


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    live = "--live" in sys.argv

    report = validate_ecosystem(quick=quick, live=live)
    sys.exit(0 if report.all_green else 1)
