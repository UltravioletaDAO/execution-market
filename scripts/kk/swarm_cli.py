#!/usr/bin/env python3
"""
KK V2 Swarm CLI — Operational command-line interface for the agent swarm.

Usage:
    python3 scripts/kk/swarm_cli.py status          # Fleet status summary
    python3 scripts/kk/swarm_cli.py tasks            # List available tasks
    python3 scripts/kk/swarm_cli.py tasks --status completed --limit 5
    python3 scripts/kk/swarm_cli.py health           # EM API health check
    python3 scripts/kk/swarm_cli.py agents           # List registered agents
    python3 scripts/kk/swarm_cli.py simulate         # Run routing simulation
    python3 scripts/kk/swarm_cli.py run --once       # Single coordination cycle
    python3 scripts/kk/swarm_cli.py run --mode passive --interval 120
    python3 scripts/kk/swarm_cli.py test             # Run live integration tests
    python3 scripts/kk/swarm_cli.py dashboard        # Full dashboard snapshot
    python3 scripts/kk/swarm_cli.py history [task_id] # Task detail
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "mcp_server"))

EM_API_URL = os.environ.get("EM_API_URL", "https://api.execution.market")
AUTOJOB_URL = os.environ.get("AUTOJOB_URL", "https://autojob.cc")


def cmd_health(args):
    """Check EM API health status."""
    from swarm.coordinator import EMApiClient

    client = EMApiClient(base_url=EM_API_URL)
    health = client.get_health()

    if health.get("error"):
        print(f"❌ EM API unreachable: {health.get('detail', 'unknown error')}")
        return 1

    status_icon = "🟢" if health.get("status") == "healthy" else "🔴"
    print(f"{status_icon} EM API: {health.get('status', 'unknown')}")

    components = health.get("components", {})
    for name, comp in components.items():
        icon = "✅" if comp.get("status") == "healthy" else "❌"
        latency = comp.get("latency_ms", "?")
        msg = comp.get("message", "")
        print(f"  {icon} {name}: {msg} ({latency}ms)")

    uptime = health.get("uptime_seconds", 0)
    if uptime:
        hours = uptime / 3600
        print(f"\n  Uptime: {hours:.1f}h")

    return 0


def cmd_tasks(args):
    """List tasks from the EM API."""
    from swarm.coordinator import EMApiClient

    client = EMApiClient(base_url=EM_API_URL)

    statuses = [args.status] if args.status else ["published", "completed", "expired"]
    all_tasks = []
    for status in statuses:
        tasks = client.list_tasks(status=status, limit=args.limit)
        all_tasks.extend(tasks)

    if not all_tasks:
        print("No tasks found.")
        return 0

    # Group by status
    by_status = {}
    for t in all_tasks:
        s = t.get("status", "unknown")
        by_status.setdefault(s, []).append(t)

    total_bounty = sum(float(t.get("bounty_usd", t.get("bounty_amount", 0))) for t in all_tasks)

    print(f"\n📋 Tasks ({len(all_tasks)} total, ${total_bounty:.2f} bounty)")
    print(f"{'─' * 70}")

    status_icons = {
        "published": "🟡", "accepted": "🟠", "in_progress": "🔵",
        "submitted": "📤", "completed": "✅", "expired": "⏰",
        "cancelled": "❌", "disputed": "⚠️",
    }

    for status, tasks in sorted(by_status.items()):
        icon = status_icons.get(status, "❓")
        print(f"\n{icon} {status.upper()} ({len(tasks)})")
        for t in tasks[:args.limit]:
            bounty = float(t.get("bounty_usd", t.get("bounty_amount", 0)))
            cat = t.get("category", "?")
            title = t.get("title", "Untitled")[:50]
            task_id = str(t.get("id", ""))[:8]
            print(f"  [{task_id}] ${bounty:.2f} {cat:<20} {title}")

    # Category breakdown
    cats = {}
    for t in all_tasks:
        c = t.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1

    print(f"\n📊 Categories:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        pct = count / len(all_tasks) * 100
        print(f"  {cat}: {count} ({pct:.0f}%)")

    return 0


def cmd_status(args):
    """Fleet status summary."""
    from swarm.coordinator import EMApiClient

    client = EMApiClient(base_url=EM_API_URL)

    print(f"\n🐙 KK V2 Swarm Status")
    print(f"{'─' * 50}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  API: {EM_API_URL}")

    # Health
    health = client.get_health()
    api_status = "🟢 healthy" if health.get("status") == "healthy" else "🔴 unhealthy"
    print(f"  EM API: {api_status}")

    # Task stats
    status_counts = {}
    for status in ["published", "accepted", "in_progress", "completed", "expired", "cancelled"]:
        tasks = client.list_tasks(status=status, limit=100)
        if tasks:
            status_counts[status] = len(tasks)

    total = sum(status_counts.values())
    print(f"\n📋 Tasks: {total} total")
    for s, c in sorted(status_counts.items(), key=lambda x: -x[1]):
        print(f"  {s}: {c}")

    # Swarm module stats
    try:
        from swarm import __init__ as swarm_init
        module_files = list((project_root / "mcp_server" / "swarm").glob("*.py"))
        test_files = list((project_root / "mcp_server" / "tests").glob("test_swarm*.py"))
        print(f"\n🔧 Swarm Modules: {len(module_files)} files")
        print(f"  Test files: {len(test_files)}")
    except Exception:
        pass

    # Check state dir
    state_dir = Path.home() / ".em-swarm"
    if state_dir.exists():
        state_file = state_dir / "runner_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            print(f"\n📊 Runner State:")
            print(f"  Total cycles: {state.get('total_cycles', 0)}")
            print(f"  Tasks routed: {state.get('total_tasks_routed', 0)}")
            print(f"  Tasks completed: {state.get('total_tasks_completed', 0)}")
            print(f"  Bounty earned: ${state.get('total_bounty_earned_usd', 0):.2f}")
            print(f"  Last cycle: {state.get('last_cycle_at', 'never')}")
    else:
        print(f"\n  Runner state: not yet initialized")

    return 0


def cmd_simulate(args):
    """Run a routing simulation with live data."""
    from swarm.coordinator import SwarmCoordinator, EMApiClient
    from swarm.orchestrator import Assignment, RoutingFailure
    from swarm.lifecycle_manager import BudgetConfig

    print(f"\n🎯 Routing Simulation")
    print(f"{'─' * 50}")

    client = EMApiClient(base_url=EM_API_URL)
    coordinator = SwarmCoordinator.create(
        em_api_url=EM_API_URL,
        autojob_url=AUTOJOB_URL,
    )

    # Register simulated agents
    categories = ["simple_action", "physical_presence", "knowledge_access",
                   "code_execution", "research"]
    num_agents = args.agents or 10
    for i in range(num_agents):
        cats = [categories[i % len(categories)], categories[(i + 2) % len(categories)]]
        coordinator.register_agent(
            agent_id=5000 + i,
            name=f"SimAgent_{i}",
            wallet_address=f"0xSim_{i:04x}",
            budget_config=BudgetConfig(daily_limit_usd=args.budget or 5.0),
            tags=cats,
        )

    # Fetch and ingest live tasks
    all_tasks = []
    for status in ["completed", "expired", "published"]:
        tasks = client.list_tasks(status=status, limit=20)
        all_tasks.extend(tasks)

    for task_data in all_tasks:
        task_id = str(task_data.get("id", ""))
        category = task_data.get("category", "simple_action")
        coordinator.ingest_task(
            task_id=task_id,
            title=task_data.get("title", ""),
            categories=[category],
            bounty_usd=float(task_data.get("bounty_usd", task_data.get("bounty_amount", 0))),
            source="simulation",
            raw_data=task_data,
        )

    print(f"  Agents: {num_agents}")
    print(f"  Tasks ingested: {len(all_tasks)}")

    # Route
    start = time.monotonic()
    results = coordinator.process_task_queue(max_tasks=len(all_tasks))
    duration = (time.monotonic() - start) * 1000

    assigned = [r for r in results if isinstance(r, Assignment)]
    failed = [r for r in results if isinstance(r, RoutingFailure)]

    print(f"\n📊 Results ({duration:.0f}ms):")
    print(f"  ✅ Assigned: {len(assigned)}")
    print(f"  ❌ Failed: {len(failed)}")
    if results:
        print(f"  Rate: {len(assigned)/len(results)*100:.0f}%")

    if assigned:
        print(f"\n  Assignments:")
        agent_counts = {}
        for a in assigned:
            agent_counts[a.agent_name] = agent_counts.get(a.agent_name, 0) + 1
        for name, count in sorted(agent_counts.items(), key=lambda x: -x[1]):
            print(f"    {name}: {count} tasks")

    if failed:
        print(f"\n  Failures:")
        reasons = {}
        for f_item in failed:
            reasons[f_item.reason] = reasons.get(f_item.reason, 0) + 1
        for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"    {reason}: {count}")

    return 0


def cmd_run(args):
    """Run the swarm daemon."""
    from swarm.runner import SwarmRunner

    print(f"\n🚀 Starting SwarmRunner")
    print(f"  Mode: {args.mode}")
    print(f"  Interval: {args.interval}s")
    print(f"  Max tasks/cycle: {args.max_tasks}")
    if args.once:
        print(f"  Single cycle mode")
    print()

    runner = SwarmRunner.create(
        em_api_url=EM_API_URL,
        mode=args.mode,
        cycle_interval=args.interval,
        max_tasks_per_cycle=args.max_tasks,
        max_cycles=1 if args.once else args.max_cycles,
    )

    if args.once:
        result = runner.run_once()
        print(f"\n{result.summary_line()}")
        if result.errors:
            for err in result.errors:
                print(f"  ⚠ {err}")
        print(f"\nPhases completed: {', '.join(result.phases_completed)}")
        if result.phases_failed:
            print(f"Phases failed: {', '.join(result.phases_failed)}")
    else:
        runner.run()

    return 0


def cmd_dashboard(args):
    """Generate a dashboard snapshot."""
    from swarm.dashboard import SwarmDashboard
    from swarm.coordinator import EMApiClient

    dashboard = SwarmDashboard()

    # Register simulated fleet to show dashboard capabilities
    categories = ["simple_action", "physical_presence", "knowledge_access",
                   "code_execution", "research"]
    for i in range(24):
        agent_id = f"kk_agent_{i:03d}"
        specs = [categories[i % len(categories)]]
        dashboard.register_agent(agent_id, budget_limit_usd=5.0, specializations=specs)
        dashboard.update_agent_state(agent_id, "active" if i < 20 else "idle")

    snapshot = dashboard.generate_snapshot()

    print(f"\n📊 KK V2 Fleet Dashboard")
    print(f"{'─' * 60}")
    print(f"  Status: {snapshot.fleet_status.value.upper()}")
    print(f"  Agents: {snapshot.agent_count} total")
    print(f"    Operational: {snapshot.agents_operational}")
    print(f"    Working: {snapshot.agents_working}")
    print(f"    Idle: {snapshot.agents_idle}")
    print(f"    Degraded: {snapshot.agents_degraded}")
    print(f"    Suspended: {snapshot.agents_suspended}")
    print(f"  Operational Rate: {snapshot.operational_rate:.0%}")
    print(f"  Uptime: {snapshot.uptime_seconds:.0f}s")

    if snapshot.alerts:
        print(f"\n⚠️ Alerts ({len(snapshot.alerts)}):")
        for alert in snapshot.alerts[:5]:
            print(f"    [{alert.severity.value}] {alert.message}")

    # Also fetch live API stats
    client = EMApiClient(base_url=EM_API_URL)
    health = client.get_health()
    api_status = "🟢" if health.get("status") == "healthy" else "🔴"
    print(f"\n  EM API: {api_status} {health.get('status', '?')}")

    return 0


def cmd_test(args):
    """Run live integration tests."""
    import subprocess
    test_script = project_root / "scripts" / "kk" / "live_integration_test.py"
    cmd = [sys.executable, str(test_script), "--verbose"]
    if args.report:
        cmd.append("--report")
    return subprocess.call(cmd)


def cmd_history(args):
    """Get task details."""
    from swarm.coordinator import EMApiClient

    client = EMApiClient(base_url=EM_API_URL)

    if args.task_id:
        detail = client.get_task(args.task_id)
        if detail:
            print(json.dumps(detail, indent=2, default=str))
        else:
            print(f"Task {args.task_id} not found")
            return 1
    else:
        # Show recent completed tasks
        tasks = client.list_tasks(status="completed", limit=10)
        for t in tasks:
            bounty = float(t.get("bounty_usd", t.get("bounty_amount", 0)))
            print(f"  [{str(t['id'])[:8]}] ${bounty:.2f} {t.get('title', '')[:50]}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="KK V2 Swarm CLI — Operational interface for the agent swarm",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status              Fleet status summary
  %(prog)s tasks               List all tasks  
  %(prog)s tasks --status published  List open tasks
  %(prog)s health              EM API health check
  %(prog)s simulate            Run routing simulation
  %(prog)s simulate --agents 24 --budget 10
  %(prog)s run --once           Single coordination cycle
  %(prog)s run --mode active    Start daemon (active mode)
  %(prog)s dashboard            Fleet dashboard
  %(prog)s test                 Run integration tests
  %(prog)s history [task_id]    Task history/details
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # health
    subparsers.add_parser("health", help="EM API health check")

    # tasks
    tasks_parser = subparsers.add_parser("tasks", help="List tasks")
    tasks_parser.add_argument("--status", help="Filter by status")
    tasks_parser.add_argument("--limit", type=int, default=20, help="Max tasks per status")

    # status
    subparsers.add_parser("status", help="Fleet status summary")

    # simulate
    sim_parser = subparsers.add_parser("simulate", help="Run routing simulation")
    sim_parser.add_argument("--agents", type=int, default=10, help="Number of simulated agents")
    sim_parser.add_argument("--budget", type=float, default=5.0, help="Agent daily budget")

    # run
    run_parser = subparsers.add_parser("run", help="Run the swarm daemon")
    run_parser.add_argument("--mode", choices=["passive", "active", "dry_run"], default="passive")
    run_parser.add_argument("--interval", type=float, default=120, help="Cycle interval in seconds")
    run_parser.add_argument("--max-tasks", type=int, default=10, help="Max tasks per cycle")
    run_parser.add_argument("--max-cycles", type=int, default=0, help="Max cycles (0=unlimited)")
    run_parser.add_argument("--once", action="store_true", help="Run single cycle")

    # dashboard
    subparsers.add_parser("dashboard", help="Fleet dashboard")

    # test
    test_parser = subparsers.add_parser("test", help="Run integration tests")
    test_parser.add_argument("--report", action="store_true", help="Save report")

    # history
    hist_parser = subparsers.add_parser("history", help="Task history/details")
    hist_parser.add_argument("task_id", nargs="?", help="Task ID for details")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "health": cmd_health,
        "tasks": cmd_tasks,
        "status": cmd_status,
        "simulate": cmd_simulate,
        "run": cmd_run,
        "dashboard": cmd_dashboard,
        "test": cmd_test,
        "history": cmd_history,
    }

    fn = commands.get(args.command)
    if fn:
        return fn(args) or 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
