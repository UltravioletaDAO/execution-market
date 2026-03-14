#!/usr/bin/env python3
"""
Ecosystem Health Check — Cross-System Intelligence Dashboard
=============================================================

Unified health check across all Ultravioleta ecosystem components:
- Execution Market API (production)
- KK V2 Swarm (coordinator, analytics, daemon)
- AutoJob (evidence flywheel, worker registry)
- describe-net (SealRegistry on-chain)
- ERC-8004 (Identity + Reputation on Base)

Usage:
    python3 scripts/kk/ecosystem_health.py           # Full health check
    python3 scripts/kk/ecosystem_health.py --quick    # Fast mode (skip on-chain)
    python3 scripts/kk/ecosystem_health.py --json     # JSON output
    python3 scripts/kk/ecosystem_health.py --watch    # Continuous monitoring (60s)

Created: 2026-03-14 4:00 AM Dream Session
"""

import json
import os
import ssl
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ─── Configuration ────────────────────────────────────────────────────────────

EM_API = "https://api.execution.market"
AUTOJOB_DIR = Path.home() / "clawd" / "projects" / "autojob"
EM_DIR = Path.home() / "clawd" / "projects" / "execution-market"
DESCRIBE_NET_DIR = Path.home() / "clawd" / "projects" / "describe-net-contracts"

# ERC-8004 contracts on Base
ERC8004_IDENTITY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
ERC8004_REPUTATION = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
BASE_RPC = "https://mainnet.base.org"

# Colors
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
DIM = "\033[2m"
RESET = "\033[0m"
CHECK = f"{GREEN}✅{RESET}"
WARN = f"{YELLOW}⚠️{RESET}"
FAIL = f"{RED}❌{RESET}"


# ─── HTTP Helpers ─────────────────────────────────────────────────────────────

SSL_CTX = ssl.create_default_context()


def _fetch(url: str, timeout: int = 10) -> dict:
    """Fetch JSON from URL."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def _rpc_call(method: str, params: list, rpc_url: str = BASE_RPC) -> dict:
    """Make a JSON-RPC call."""
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }).encode()

    req = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}


def _eth_call(to: str, data: str) -> str:
    """Execute eth_call on Base mainnet."""
    result = _rpc_call("eth_call", [{"to": to, "data": data}, "latest"])
    return result.get("result", "0x")


# ─── Health Checks ───────────────────────────────────────────────────────────

class HealthReport:
    """Accumulates health check results."""

    def __init__(self):
        self.sections = []
        self.total_checks = 0
        self.passed = 0
        self.warnings = 0
        self.failed = 0
        self.start_time = time.monotonic()

    def section(self, name: str):
        self.sections.append({"name": name, "checks": [], "metrics": {}})

    def check(self, name: str, passed: bool, detail: str = "", warn: bool = False):
        self.total_checks += 1
        if passed:
            self.passed += 1
            icon = CHECK
        elif warn:
            self.warnings += 1
            icon = WARN
        else:
            self.failed += 1
            icon = FAIL

        if self.sections:
            self.sections[-1]["checks"].append({
                "name": name, "passed": passed, "warn": warn, "detail": detail,
            })

        print(f"  {icon} {name}")
        if detail:
            print(f"     {DIM}{detail}{RESET}")

    def metric(self, name: str, value, unit: str = ""):
        if self.sections:
            self.sections[-1]["metrics"][name] = {"value": value, "unit": unit}
        suffix = f" {unit}" if unit else ""
        print(f"  {YELLOW}▸{RESET} {name}: {BOLD}{value}{RESET}{suffix}")

    def summary(self):
        elapsed = time.monotonic() - self.start_time
        total = self.total_checks

        if self.failed > 0:
            status = f"{RED}{BOLD}🔴 DEGRADED"
            detail = f"{self.failed} critical issue(s)"
        elif self.warnings > 0:
            status = f"{YELLOW}{BOLD}🟡 HEALTHY (with warnings)"
            detail = f"{self.warnings} warning(s)"
        else:
            status = f"{GREEN}{BOLD}🟢 ALL SYSTEMS OPERATIONAL"
            detail = "No issues detected"

        print(f"\n{CYAN}{'═' * 70}{RESET}")
        print(f"  {status}{RESET}")
        print(f"  {DIM}{self.passed}/{total} checks passed | {detail} | {elapsed:.1f}s{RESET}")
        print(f"{CYAN}{'═' * 70}{RESET}")

        return {
            "status": "degraded" if self.failed > 0 else "healthy",
            "passed": self.passed,
            "warnings": self.warnings,
            "failed": self.failed,
            "total": total,
            "elapsed_s": round(elapsed, 2),
            "sections": self.sections,
        }


def check_em_api(report: HealthReport):
    """Check Execution Market API health."""
    report.section("Execution Market API")

    # Health endpoint
    health = _fetch(f"{EM_API}/health")
    report.check("API health endpoint", "error" not in health,
                 health.get("error", f"status={health.get('status', 'ok')}"))

    # Nonce endpoint (auth system)
    nonce = _fetch(f"{EM_API}/api/v1/auth/nonce")
    report.check("ERC-8128 auth (nonce)", "error" not in nonce and "nonce" in nonce,
                 f"nonce={'available' if 'nonce' in nonce else nonce.get('error', 'missing')}")

    # Task listing
    tasks = _fetch(f"{EM_API}/api/v1/tasks?limit=5")
    if isinstance(tasks, list):
        report.check("Task API", True, f"{len(tasks)} recent tasks returned")
        # Check for completed tasks
        completed = [t for t in tasks if t.get("status") == "completed"]
        report.metric("Recent completed tasks", len(completed), "(last 5)")
    elif isinstance(tasks, dict) and "data" in tasks:
        data = tasks["data"]
        report.check("Task API", True, f"{len(data)} recent tasks returned")
    else:
        report.check("Task API", "error" not in tasks,
                     tasks.get("error", "unexpected response format"), warn=True)

    # ERC-8128 info
    info = _fetch(f"{EM_API}/api/v1/auth/erc8128/info")
    if "error" not in info:
        chains = info.get("supported_chains", info.get("chains", []))
        report.check("ERC-8128 configuration", len(chains) > 0,
                     f"{len(chains)} chains supported")
    else:
        report.check("ERC-8128 configuration", False, info.get("error", ""), warn=True)


def check_erc8004(report: HealthReport, quick: bool = False):
    """Check ERC-8004 contracts on Base."""
    report.section("ERC-8004 On-Chain (Base)")

    if quick:
        report.check("ERC-8004 check", True, "Skipped (--quick mode)", warn=True)
        return

    # Check Identity Registry - totalAgents()
    # totalAgents selector: 0xe2b4e16f
    result = _eth_call(ERC8004_IDENTITY, "0xe2b4e16f")
    if result and result != "0x" and len(result) > 2:
        total_agents = int(result, 16) if result.startswith("0x") else 0
        report.check("Identity Registry", total_agents > 0,
                     f"{total_agents} agents registered")
        report.metric("Total agents", total_agents)
    else:
        report.check("Identity Registry", False, "Could not read contract", warn=True)

    # Check Reputation Registry - basic call
    # We check if the contract responds to a view call
    result = _eth_call(ERC8004_REPUTATION, "0xe2b4e16f")
    if result and result != "0x":
        report.check("Reputation Registry", True, "Contract responsive")
    else:
        report.check("Reputation Registry", False, "Contract unresponsive", warn=True)

    # Check our platform wallet is registered
    platform_wallet = "0xD3868E1eD738CED6945A574a7c769433BeD5d474"
    # agentOf(address) selector: 0xe1bae704
    clean_addr = platform_wallet.lower().replace("0x", "").zfill(64)
    result = _eth_call(ERC8004_IDENTITY, "0xe1bae704" + clean_addr)
    if result and result != "0x" and len(result) > 2:
        agent_id = int(result, 16) if result.startswith("0x") else 0
        report.check("Platform wallet registered", agent_id > 0,
                     f"Agent ID: {agent_id}")
    else:
        report.check("Platform wallet registered", False,
                     "Not found or call failed", warn=True)


def check_swarm(report: HealthReport):
    """Check KK V2 Swarm modules."""
    report.section("KK V2 Swarm")

    swarm_dir = EM_DIR / "mcp_server" / "swarm"

    # Check module presence
    modules = [
        "coordinator.py", "orchestrator.py", "reputation_bridge.py",
        "lifecycle_manager.py", "evidence_parser.py", "event_listener.py",
        "strategy_engine.py", "bootstrap.py", "autojob_client.py",
        "heartbeat_handler.py", "analytics.py", "daemon.py",
        "acontext_adapter.py", "mcp_tools.py",
    ]

    present = sum(1 for m in modules if (swarm_dir / m).exists())
    report.check("Swarm modules present", present == len(modules),
                 f"{present}/{len(modules)} modules found")
    report.metric("Module count", present)

    # Count total LOC
    total_loc = 0
    for m in modules:
        path = swarm_dir / m
        if path.exists():
            total_loc += sum(1 for _ in open(path))
    report.metric("Total swarm LOC", f"{total_loc:,}")

    # Check test files
    test_dir = EM_DIR / "mcp_server" / "tests"
    swarm_tests = list(test_dir.glob("test_swarm*.py")) if test_dir.exists() else []
    report.check("Swarm test files", len(swarm_tests) >= 5,
                 f"{len(swarm_tests)} test files found")

    # Check operational docs
    for doc in ["ACTIVATION.md", "ARCHITECTURE.md", "OPERATIONS.md"]:
        exists = (swarm_dir / doc).exists()
        report.check(f"Doc: {doc}", exists,
                     "Present" if exists else "Missing", warn=not exists)


def check_autojob(report: HealthReport):
    """Check AutoJob evidence flywheel."""
    report.section("AutoJob Evidence Flywheel")

    # Check project exists
    report.check("AutoJob project", AUTOJOB_DIR.exists(),
                 str(AUTOJOB_DIR))

    if not AUTOJOB_DIR.exists():
        return

    # Count evidence sources
    sources_dir = AUTOJOB_DIR / "evidence_sources"
    if sources_dir.exists():
        source_files = [f for f in sources_dir.glob("*.py") if f.name != "__init__.py" and f.name != "base.py"]
        report.check("Evidence sources", len(source_files) >= 10,
                     f"{len(source_files)} sources")
        report.metric("Evidence sources", len(source_files))

        # Check for describe-net source specifically
        describe_exists = (sources_dir / "describe_net.py").exists()
        report.check("describe-net evidence source", describe_exists,
                     "Connected" if describe_exists else "Missing")

    # Count tests
    test_dir = AUTOJOB_DIR / "tests"
    if test_dir.exists():
        test_files = list(test_dir.glob("test_*.py"))
        report.metric("Test files", len(test_files))

    # Check worker registry
    workers_dir = AUTOJOB_DIR / "workers"
    if workers_dir.exists():
        worker_files = list(workers_dir.glob("*.json"))
        report.metric("Workers in registry", len(worker_files))
    else:
        report.metric("Workers in registry", 0)

    # Check main modules
    key_modules = [
        "swarm_router.py", "reputation_matcher.py", "em_event_listener.py",
        "worker_registry.py", "task_skill_mapper.py", "erc8004_reader.py",
    ]
    present = sum(1 for m in key_modules if (AUTOJOB_DIR / m).exists())
    report.check("Key modules", present == len(key_modules),
                 f"{present}/{len(key_modules)} modules present")


def check_describe_net(report: HealthReport, quick: bool = False):
    """Check describe-net contracts."""
    report.section("describe-net Contracts")

    report.check("Project exists", DESCRIBE_NET_DIR.exists(),
                 str(DESCRIBE_NET_DIR))

    if not DESCRIBE_NET_DIR.exists():
        return

    # Check contract files
    src_dir = DESCRIBE_NET_DIR / "src"
    if src_dir.exists():
        sol_files = list(src_dir.glob("*.sol"))
        report.check("Solidity contracts", len(sol_files) > 0,
                     f"{len(sol_files)} contracts")

        key_contracts = ["SealRegistry.sol", "ERC8004ReputationAdapter.sol"]
        for contract in key_contracts:
            exists = (src_dir / contract).exists()
            report.check(f"Contract: {contract}", exists,
                         "Present" if exists else "Missing")

    # Check test files
    test_dir = DESCRIBE_NET_DIR / "test"
    if test_dir.exists():
        test_files = list(test_dir.glob("*.sol"))
        report.metric("Test files", len(test_files))

    # Check deployment records (Foundry uses broadcast/ and deployments/)
    deployments_dir = DESCRIBE_NET_DIR / "deployments"
    broadcast_dir = DESCRIBE_NET_DIR / "broadcast"
    if deployments_dir.exists():
        deploy_files = [f.stem for f in deployments_dir.glob("*.json")]
        report.check("Deployments", len(deploy_files) > 0,
                     f"Deployed to: {', '.join(deploy_files)}" if deploy_files else "None found")
    elif broadcast_dir.exists():
        broadcast_scripts = [d.name for d in broadcast_dir.iterdir() if d.is_dir()]
        report.check("Deployments (broadcast)", len(broadcast_scripts) > 0,
                     f"Scripts: {', '.join(broadcast_scripts)}" if broadcast_scripts else "None found")
    else:
        report.check("Deployments", False, "No deployment records found", warn=True)


def check_cross_system(report: HealthReport):
    """Check cross-system integration health."""
    report.section("Cross-System Integration")

    # AutoJob → EM bridge
    bridge_files = [
        AUTOJOB_DIR / "swarm_router.py",          # AutoJob routing for EM tasks
        AUTOJOB_DIR / "em_event_listener.py",       # EM → AutoJob evidence ingestion
        AUTOJOB_DIR / "task_skill_mapper.py",       # EM tasks → AutoJob job format
        AUTOJOB_DIR / "reputation_matcher.py",      # ERC-8004 + Skill DNA scoring
    ]
    present = sum(1 for f in bridge_files if f.exists())
    report.check("AutoJob ↔ EM bridge", present == len(bridge_files),
                 f"{present}/{len(bridge_files)} bridge modules")

    # EM Swarm → AutoJob client
    autojob_client = EM_DIR / "mcp_server" / "swarm" / "autojob_client.py"
    report.check("Swarm → AutoJob client", autojob_client.exists(),
                 "Connected" if autojob_client.exists() else "Missing")

    # describe-net → AutoJob evidence source
    dn_source = AUTOJOB_DIR / "evidence_sources" / "describe_net.py"
    report.check("describe-net → AutoJob evidence", dn_source.exists(),
                 "Evidence source active" if dn_source.exists() else "Not connected")

    # EM Swarm → Reputation bridge
    rep_bridge = EM_DIR / "mcp_server" / "swarm" / "reputation_bridge.py"
    report.check("Swarm → ERC-8004 reputation", rep_bridge.exists(),
                 "Bridge active" if rep_bridge.exists() else "Missing")

    # Integration score
    total_bridges = 4
    active = sum([
        all(f.exists() for f in bridge_files),
        autojob_client.exists(),
        dn_source.exists(),
        rep_bridge.exists(),
    ])
    report.metric("Integration score", f"{active}/{total_bridges}",
                  f"({active/total_bridges*100:.0f}% connected)")


# ─── Main ─────────────────────────────────────────────────────────────────────

def run(quick: bool = False, as_json: bool = False):
    """Run full ecosystem health check."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if not as_json:
        print(f"\n{BOLD}{CYAN}{'═' * 70}{RESET}")
        print(f"  {BOLD}🌐 Ultravioleta Ecosystem Health Check{RESET}")
        print(f"  {DIM}{now}{RESET}")
        print(f"{CYAN}{'═' * 70}{RESET}\n")

    report = HealthReport()

    # Run all checks
    check_em_api(report)
    print()
    check_erc8004(report, quick=quick)
    print()
    check_swarm(report)
    print()
    check_autojob(report)
    print()
    check_describe_net(report, quick=quick)
    print()
    check_cross_system(report)

    result = report.summary()

    if as_json:
        print(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    as_json = "--json" in sys.argv
    watch = "--watch" in sys.argv

    if watch:
        while True:
            os.system("clear")
            run(quick=quick, as_json=as_json)
            time.sleep(60)
    else:
        result = run(quick=quick, as_json=as_json)
        sys.exit(1 if result["failed"] > 0 else 0)
