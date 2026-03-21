#!/usr/bin/env python3
"""
Swarm Operations CLI — Monitor and operate the KK V2 agent fleet.

Usage:
    python3 swarm_ops.py status          # Fleet status overview
    python3 swarm_ops.py dashboard       # Full dashboard with metrics
    python3 swarm_ops.py agents          # List all registered agents
    python3 swarm_ops.py poll            # Run a single poll cycle
    python3 swarm_ops.py health          # System health checks
    python3 swarm_ops.py simulate        # Run 24-agent simulation
    python3 swarm_ops.py benchmark       # Performance benchmark

Connects to live EM API at https://api.execution.market
"""

import argparse
import sys
import time
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp_server"))

from swarm.coordinator import SwarmCoordinator, EMApiClient
from swarm.orchestrator import TaskPriority
from swarm.autojob_client import AutoJobClient
from swarm.event_listener import EventListener, ListenerState
from swarm.evidence_parser import EvidenceParser, WorkerRegistry


# ─── ANSI Colors ──────────────────────────────────────────────────────────────


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    PURPLE = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def header(text):
    print(f"\n{C.BOLD}{C.PURPLE}{'═' * 60}{C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}  {text}{C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}{'═' * 60}{C.RESET}")


def subheader(text):
    print(f"\n{C.BOLD}{C.CYAN}  ── {text} ──{C.RESET}")


def ok(text):
    print(f"  {C.GREEN}✓{C.RESET} {text}")


def warn(text):
    print(f"  {C.YELLOW}⚠{C.RESET} {text}")


def fail(text):
    print(f"  {C.RED}✗{C.RESET} {text}")


def info(text):
    print(f"  {C.DIM}›{C.RESET} {text}")


def metric(label, value, color=C.WHITE):
    print(f"  {C.DIM}{label}:{C.RESET} {color}{value}{C.RESET}")


# ─── Commands ─────────────────────────────────────────────────────────────────


def cmd_status(args):
    """Quick fleet status overview."""
    header("KK V2 SWARM — STATUS")

    # Check EM API
    subheader("EM API")
    client = EMApiClient(
        base_url=os.environ.get("EM_API_URL", "https://api.execution.market")
    )
    health = client.get_health()
    if health.get("error"):
        fail(f"EM API unreachable: {health.get('detail', 'unknown')}")
    else:
        block = health.get("block_number", health.get("latest_block", "?"))
        ok(f"EM API healthy (block: {block})")

    # Check published tasks
    subheader("Task Pipeline")
    published = client.list_tasks(status="published")
    completed = client.list_tasks(status="completed")
    metric("Published tasks", len(published), C.YELLOW if published else C.GREEN)
    metric("Completed tasks (recent)", len(completed), C.GREEN)

    # Total bounty in published tasks
    total_bounty = sum(float(t.get("bounty_amount", 0) or 0) for t in published)
    metric("Available bounty", f"${total_bounty:.2f}", C.CYAN)

    # AutoJob check
    subheader("AutoJob")
    try:
        autojob = AutoJobClient(base_url="http://localhost:8765")
        if autojob.is_available():
            ok("AutoJob service available")
        else:
            warn("AutoJob service not running (enrichment unavailable)")
    except Exception:
        warn("AutoJob service not reachable")

    # Swarm modules — verify each can be imported
    subheader("Swarm Modules")
    modules_check = [
        ("ReputationBridge", "swarm.reputation_bridge", "on-chain + internal scoring"),
        ("LifecycleManager", "swarm.lifecycle_manager", "7-state machine + budget"),
        ("SwarmOrchestrator", "swarm.orchestrator", "4 routing strategies"),
        ("AutoJobClient", "swarm.autojob_client", "enrichment bridge"),
        ("SwarmCoordinator", "swarm.coordinator", "operational controller"),
        ("EventListener", "swarm.event_listener", "API polling + watermarks"),
        ("EvidenceParser", "swarm.evidence_parser", "Skill DNA extraction"),
    ]
    for name, module_path, description in modules_check:
        try:
            __import__(module_path)
            ok(f"{name} — {description}")
        except ImportError as e:
            fail(f"{name} — import failed: {e}")

    print()


def cmd_dashboard(args):
    """Full operational dashboard with metrics."""
    header("KK V2 SWARM — DASHBOARD")

    from swarm.bootstrap import SwarmBootstrap

    # Use production-aware bootstrap
    subheader("Bootstrapping Fleet")
    bootstrap = SwarmBootstrap()
    coordinator, result = bootstrap.create_coordinator(
        fetch_live=False, use_cached_profiles=True
    )
    info(f"Registered {result.agents_registered} agents ({result.bootstrap_ms:.0f}ms)")

    # Ingest published tasks
    subheader("Ingesting Tasks")
    client = coordinator.em_client
    published = client.list_tasks(status="published")
    ingested = 0
    for task in published:
        try:
            task_id = str(task.get("id", ""))
            if task_id:
                coordinator.ingest_task(
                    task_id=task_id,
                    title=task.get("title", "Untitled"),
                    categories=["general"],
                    bounty_usd=float(task.get("bounty_amount", 0) or 0),
                )
                ingested += 1
        except Exception:
            pass
    info(f"Ingested {ingested} tasks from EM API")

    # Process queue
    subheader("Routing")
    start = time.monotonic()
    coordinator.process_task_queue()
    routing_ms = (time.monotonic() - start) * 1000
    info(f"Queue processed in {routing_ms:.1f}ms")

    # Get dashboard
    dashboard = coordinator.get_dashboard()

    subheader("Metrics")
    metrics = dashboard.get("metrics", {})
    tasks = metrics.get("tasks", {})
    agents = metrics.get("agents", {})
    perf = metrics.get("performance", {})

    metric("Tasks ingested", tasks.get("ingested", 0))
    metric("Tasks assigned", tasks.get("assigned", 0), C.GREEN)
    metric("Tasks completed", tasks.get("completed", 0), C.GREEN)
    metric(
        "Tasks failed",
        tasks.get("failed", 0),
        C.RED if tasks.get("failed") else C.GREEN,
    )
    metric("Bounty earned", f"${tasks.get('bounty_earned_usd', 0):.2f}", C.CYAN)

    print()
    metric("Agents registered", agents.get("registered", 0))
    metric("Agents active", agents.get("active", 0), C.GREEN)
    metric(
        "Agents degraded",
        agents.get("degraded", 0),
        C.YELLOW if agents.get("degraded") else C.GREEN,
    )
    metric(
        "Agents suspended",
        agents.get("suspended", 0),
        C.RED if agents.get("suspended") else C.GREEN,
    )

    print()
    metric("Routing time", f"{perf.get('avg_routing_time_ms', 0):.1f}ms")
    metric("Success rate", f"{perf.get('routing_success_rate', 0) * 100:.0f}%")

    # Fleet details
    subheader("Fleet")
    fleet = dashboard.get("fleet", [])
    for agent in fleet[:10]:  # Show top 10
        agent_id = agent.get("agent_id", "?")
        state = agent.get("state", "?")
        budget = agent.get("budget", {})
        remaining = budget.get("daily_remaining_usd", 0)

        state_color = {
            "IDLE": C.BLUE,
            "ACTIVE": C.GREEN,
            "WORKING": C.CYAN,
            "DEGRADED": C.YELLOW,
            "SUSPENDED": C.RED,
        }.get(state, C.DIM)

        print(
            f"  Agent {agent_id}: {state_color}{state}{C.RESET} | Budget: ${remaining:.2f}"
        )

    if len(fleet) > 10:
        info(f"... and {len(fleet) - 10} more agents")

    print()


def cmd_agents(args):
    """List all registered agents with details."""
    header("KK V2 SWARM — AGENTS")

    # Check EM API for registered agents
    client = EMApiClient(
        base_url=os.environ.get("EM_API_URL", "https://api.execution.market")
    )

    subheader("ERC-8004 Registered Agents")
    for agent_id in range(2101, 2125):
        identity = client.get_agent_identity(agent_id)
        if identity and not identity.get("error"):
            name = identity.get(
                "name", identity.get("display_name", f"Agent-{agent_id}")
            )
            wallet = identity.get("wallet", "unknown")[:10] + "..."
            ok(f"Agent {agent_id}: {name} ({wallet})")
        else:
            info(f"Agent {agent_id}: not registered or not found")

    print()


def cmd_poll(args):
    """Run a single poll cycle against live EM API."""
    header("KK V2 SWARM — POLL CYCLE")

    coordinator = SwarmCoordinator.create(
        em_api_url=os.environ.get("EM_API_URL", "https://api.execution.market"),
    )

    # Register basic agents
    for i in range(1, 25):
        try:
            coordinator.register_agent(
                agent_id=2100 + i,
                wallet_address=f"0x{i:040x}",
                name=f"Agent-{2100 + i}",
                tags=["general"],
            )
        except Exception:
            pass

    state_path = os.path.expanduser("~/.em-swarm-listener-state.json")
    listener = EventListener(coordinator, state_path=state_path)

    subheader("Running Poll")
    result = listener.poll_once()

    ok(f"Poll complete in {result.duration_ms:.1f}ms")
    metric("New tasks", result.new_tasks, C.YELLOW if result.new_tasks else C.DIM)
    metric(
        "Completions",
        result.completed_tasks,
        C.GREEN if result.completed_tasks else C.DIM,
    )
    metric("Failures", result.failed_tasks, C.RED if result.failed_tasks else C.DIM)
    metric("Expired", result.expired_tasks, C.YELLOW if result.expired_tasks else C.DIM)

    if result.errors:
        for err in result.errors:
            warn(f"Error: {err}")

    # Show listener state
    subheader("Listener State")
    state = listener.get_status()["state"]
    metric("Total polls", state["poll_count"])
    metric("Total tasks discovered", state["total_new_tasks"])
    metric("Total completions", state["total_completions"])
    metric("Known task IDs", state["known_task_count"])

    print()


def cmd_health(args):
    """System health checks."""
    header("KK V2 SWARM — HEALTH")

    checks_passed = 0
    checks_total = 0

    # EM API
    subheader("Infrastructure")
    checks_total += 1
    client = EMApiClient(
        base_url=os.environ.get("EM_API_URL", "https://api.execution.market")
    )
    health = client.get_health()
    if health.get("error"):
        fail("EM API: unreachable")
    else:
        ok(f"EM API: healthy (block {health.get('block_number', '?')})")
        checks_passed += 1

    # AutoJob
    checks_total += 1
    try:
        autojob = AutoJobClient(base_url="http://localhost:8765")
        if autojob.is_available():
            ok("AutoJob: available")
            checks_passed += 1
        else:
            warn("AutoJob: not running (optional)")
            checks_passed += 1  # Optional service
    except Exception:
        warn("AutoJob: not reachable (optional)")
        checks_passed += 1

    # Module imports
    subheader("Modules")
    modules = [
        ("ReputationBridge", "swarm.reputation_bridge"),
        ("LifecycleManager", "swarm.lifecycle_manager"),
        ("SwarmOrchestrator", "swarm.orchestrator"),
        ("AutoJobClient", "swarm.autojob_client"),
        ("SwarmCoordinator", "swarm.coordinator"),
        ("EventListener", "swarm.event_listener"),
        ("EvidenceParser", "swarm.evidence_parser"),
    ]
    for name, module in modules:
        checks_total += 1
        try:
            __import__(module)
            ok(f"{name}: importable")
            checks_passed += 1
        except ImportError as e:
            fail(f"{name}: import error ({e})")

    # Listener state
    subheader("State")
    checks_total += 1
    state_path = os.path.expanduser("~/.em-swarm-listener-state.json")
    if os.path.exists(state_path):
        state = ListenerState.load(state_path)
        ok(
            f"Listener state: {state.poll_count} polls, {state.total_new_tasks} tasks seen"
        )
        checks_passed += 1
    else:
        info("Listener state: no state file (first run)")
        checks_passed += 1

    # Registry
    checks_total += 1
    registry_path = os.path.expanduser("~/.em-swarm-worker-registry.json")
    if os.path.exists(registry_path):
        registry = WorkerRegistry.load(registry_path)
        ok(f"Worker registry: {len(registry.list_workers())} workers")
        checks_passed += 1
    else:
        info("Worker registry: no registry file (first run)")
        checks_passed += 1

    # Summary
    subheader("Summary")
    color = C.GREEN if checks_passed == checks_total else C.YELLOW
    print(f"  {color}{checks_passed}/{checks_total} checks passed{C.RESET}")

    print()


def cmd_simulate(args):
    """Run full swarm simulation with 24 agents."""
    header("KK V2 SWARM — SIMULATION")

    coordinator = SwarmCoordinator.create(
        em_api_url=os.environ.get("EM_API_URL", "https://api.execution.market"),
    )

    # Register 24 agents with varied skills
    subheader("Registering Fleet (24 agents)")
    categories_pool = [
        ["delivery", "physical", "logistics"],
        ["coding", "digital", "technical"],
        ["design", "creative", "digital"],
        ["verification", "photo", "geo"],
        ["blockchain", "defi", "crypto"],
        ["research", "analysis", "digital"],
    ]

    for i in range(1, 25):
        cats = categories_pool[i % len(categories_pool)]
        coordinator.register_agent(
            agent_id=2100 + i,
            wallet_address=f"0x{i:040x}",
            name=f"Agent-{2100 + i}",
            tags=cats,
        )
    ok(f"Registered 24 agents across {len(categories_pool)} specializations")

    # Create simulated tasks
    subheader("Ingesting Tasks")
    tasks = [
        (
            "Deliver package to 5th Ave",
            ["delivery", "physical"],
            15.0,
            TaskPriority.NORMAL,
        ),
        ("Smart contract audit", ["blockchain", "defi"], 75.0, TaskPriority.HIGH),
        ("Design landing page", ["design", "creative"], 30.0, TaskPriority.NORMAL),
        ("Photo verify storefront", ["verification", "photo"], 5.0, TaskPriority.LOW),
        ("Python API integration", ["coding", "technical"], 50.0, TaskPriority.HIGH),
        (
            "Research competitor pricing",
            ["research", "analysis"],
            20.0,
            TaskPriority.NORMAL,
        ),
        ("Deliver food order", ["delivery", "physical"], 8.0, TaskPriority.NORMAL),
        ("Write blog post", ["writing", "creative"], 25.0, TaskPriority.NORMAL),
        ("DeFi yield analysis", ["blockchain", "defi"], 40.0, TaskPriority.HIGH),
        (
            "Geo-verify construction site",
            ["verification", "geo"],
            10.0,
            TaskPriority.NORMAL,
        ),
    ]

    for i, (title, cats, bounty, priority) in enumerate(tasks):
        coordinator.ingest_task(
            task_id=f"sim-{i + 1:03d}",
            title=title,
            categories=cats,
            bounty_usd=bounty,
            priority=priority,
        )
    ok(f"Ingested {len(tasks)} simulated tasks")

    # Route tasks
    subheader("Routing")
    start = time.monotonic()
    coordinator.process_task_queue()
    routing_ms = (time.monotonic() - start) * 1000
    ok(f"Routed in {routing_ms:.1f}ms")

    # Show assignments
    subheader("Assignments")
    for task_id, task in coordinator._task_queue.items():
        if task.assigned_agent_id:
            ok(
                f"{task.title[:40]:40s} → Agent {task.assigned_agent_id} (${task.bounty_usd:.0f})"
            )
        else:
            warn(f"{task.title[:40]:40s} → UNASSIGNED")

    # Complete some tasks and test evidence parser
    subheader("Simulating Completions")
    EvidenceParser()
    registry = WorkerRegistry()

    completions = [
        (
            "sim-001",
            2101,
            [
                {
                    "type": "photo_geo",
                    "content": "delivery-proof.jpg",
                    "metadata": {"latitude": 25.76},
                },
                {"type": "receipt", "content": "Receipt #456"},
            ],
        ),
        (
            "sim-005",
            2102,
            [
                {"type": "screenshot", "content": "api-test-output.png"},
                {
                    "type": "text_response",
                    "content": "Implemented REST API with 15 endpoints, full test coverage, and documentation. "
                    * 3,
                },
                {"type": "document", "content": "API Documentation v1.0"},
            ],
        ),
        (
            "sim-002",
            2105,
            [
                {
                    "type": "document",
                    "content": "Smart contract audit report covering 12 contracts. "
                    * 5,
                },
                {
                    "type": "text_response",
                    "content": "No critical vulnerabilities found. 3 medium-severity issues documented.",
                },
            ],
        ),
    ]

    for task_id, agent_id, evidence in completions:
        try:
            coordinator.complete_task(task_id=task_id)
        except Exception:
            pass

        dna, assessment = registry.process_completion(
            worker_id=str(agent_id),
            evidence=evidence,
        )
        ok(
            f"Task {task_id}: quality={assessment.quality.value} score={assessment.score:.2f}"
        )
        info(
            f"  → Agent {agent_id} Skill DNA: {[f'{k}={v:.2f}' for k, v in dna.get_top_skills(3)]}"
        )

    # Dashboard
    subheader("Dashboard")
    dashboard = coordinator.get_dashboard()
    metrics = dashboard.get("metrics", {})
    tasks_m = metrics.get("tasks", {})
    metric("Assigned", f"{tasks_m.get('assigned', 0)}/{len(tasks)}")
    metric("Completed", tasks_m.get("completed", 0), C.GREEN)
    metric("Routing time", f"{routing_ms:.1f}ms")
    metric("Workers profiled", len(registry.list_workers()))

    print()
    ok("Simulation complete!")
    print()


def cmd_benchmark(args):
    """Performance benchmark — routing speed test."""
    header("KK V2 SWARM — BENCHMARK")

    coordinator = SwarmCoordinator.create(
        em_api_url=os.environ.get("EM_API_URL", "https://api.execution.market"),
    )

    # Register agents
    for i in range(1, 25):
        coordinator.register_agent(
            agent_id=2100 + i,
            wallet_address=f"0x{i:040x}",
            name=f"Agent-{2100 + i}",
            tags=["general", "simple_action"],
        )

    # Benchmark: ingestion speed
    subheader("Ingestion Speed")
    n_tasks = 100
    start = time.monotonic()
    for i in range(n_tasks):
        coordinator.ingest_task(
            task_id=f"bench-{i:04d}",
            title=f"Benchmark task {i}",
            categories=["general"],
            bounty_usd=10.0,
        )
    ingest_ms = (time.monotonic() - start) * 1000
    ok(
        f"{n_tasks} tasks ingested in {ingest_ms:.1f}ms ({ingest_ms / n_tasks:.2f}ms/task)"
    )

    # Benchmark: routing speed
    subheader("Routing Speed")
    start = time.monotonic()
    coordinator.process_task_queue()
    route_ms = (time.monotonic() - start) * 1000
    ok(f"{n_tasks} tasks routed in {route_ms:.1f}ms ({route_ms / n_tasks:.2f}ms/task)")

    # Benchmark: evidence parsing speed
    subheader("Evidence Parsing Speed")
    parser = EvidenceParser()
    evidence_batch = [
        {"type": "photo_geo", "content": "url", "metadata": {"latitude": 25.76}},
        {"type": "text_response", "content": "Detailed work report " * 20},
        {"type": "receipt", "content": "Receipt data"},
    ]

    n_parse = 1000
    start = time.monotonic()
    for _ in range(n_parse):
        parser.parse_evidence(evidence_batch)
    parse_ms = (time.monotonic() - start) * 1000
    ok(
        f"{n_parse} evidence sets parsed in {parse_ms:.1f}ms ({parse_ms / n_parse:.3f}ms/set)"
    )

    # Benchmark: Skill DNA updates
    subheader("Skill DNA Update Speed")
    registry = WorkerRegistry()
    n_updates = 1000
    start = time.monotonic()
    for i in range(n_updates):
        registry.process_completion(
            f"worker-{i % 50}",
            evidence_batch,
        )
    update_ms = (time.monotonic() - start) * 1000
    ok(
        f"{n_updates} DNA updates in {update_ms:.1f}ms ({update_ms / n_updates:.3f}ms/update)"
    )

    # Summary
    subheader("Summary")
    metric("Ingestion throughput", f"{n_tasks / (ingest_ms / 1000):.0f} tasks/sec")
    metric("Routing throughput", f"{n_tasks / (route_ms / 1000):.0f} tasks/sec")
    metric("Evidence parse rate", f"{n_parse / (parse_ms / 1000):.0f} sets/sec")
    metric("DNA update rate", f"{n_updates / (update_ms / 1000):.0f} updates/sec")

    print()


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="KK V2 Swarm Operations CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  status     Quick fleet status overview
  dashboard  Full dashboard with metrics
  agents     List registered agents
  poll       Run a single EM API poll cycle
  health     System health checks
  simulate   Run 24-agent simulation
  benchmark  Performance benchmark
        """,
    )
    parser.add_argument(
        "command",
        choices=[
            "status",
            "dashboard",
            "agents",
            "poll",
            "health",
            "simulate",
            "benchmark",
        ],
    )

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "dashboard": cmd_dashboard,
        "agents": cmd_agents,
        "poll": cmd_poll,
        "health": cmd_health,
        "simulate": cmd_simulate,
        "benchmark": cmd_benchmark,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
