#!/usr/bin/env python3
"""
KK V2 Swarm Simulation — Demonstrates the full coordination pipeline.

Registers the 24 ERC-8004 agents, creates realistic task scenarios,
routes them through the orchestrator, and produces an operational report.

Usage:
    python3 scripts/kk/simulate_swarm.py [--live] [--agents N] [--tasks N]

Flags:
    --live     Connect to live EM API for health check and task ingestion
    --agents N Number of agents (default: 24)
    --tasks N  Number of simulated tasks (default: 20)
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, ".")

from mcp_server.swarm.coordinator import SwarmCoordinator
from mcp_server.swarm.reputation_bridge import OnChainReputation, InternalReputation, ReputationTier
from mcp_server.swarm.lifecycle_manager import BudgetConfig
from mcp_server.swarm.orchestrator import TaskRequest, TaskPriority, Assignment, RoutingFailure, RoutingStrategy


# ─── Agent Profiles ───────────────────────────────────────────────────────────

AGENT_PROFILES = [
    {"name": "aurora", "personality": "explorer", "strengths": ["photo", "delivery"]},
    {"name": "helios", "personality": "analyst", "strengths": ["document", "measurement"]},
    {"name": "nebula", "personality": "creative", "strengths": ["photo", "video"]},
    {"name": "quasar", "personality": "specialist", "strengths": ["measurement", "receipt"]},
    {"name": "zenith", "personality": "generalist", "strengths": ["photo", "delivery", "document"]},
    {"name": "solstice", "personality": "explorer", "strengths": ["photo", "screenshot"]},
    {"name": "meridian", "personality": "analyst", "strengths": ["document", "timestamp_proof"]},
    {"name": "eclipse", "personality": "creative", "strengths": ["video", "photo"]},
    {"name": "perihelion", "personality": "specialist", "strengths": ["measurement", "receipt"]},
    {"name": "aphelion", "personality": "generalist", "strengths": ["delivery", "photo"]},
    {"name": "vortex", "personality": "explorer", "strengths": ["photo", "signature"]},
    {"name": "cascade", "personality": "analyst", "strengths": ["document", "text_response"]},
    {"name": "prism", "personality": "creative", "strengths": ["photo", "video", "screenshot"]},
    {"name": "vertex", "personality": "specialist", "strengths": ["measurement", "notarized"]},
    {"name": "nexus", "personality": "generalist", "strengths": ["delivery", "document", "photo"]},
    {"name": "corona", "personality": "explorer", "strengths": ["photo", "receipt"]},
    {"name": "flux", "personality": "analyst", "strengths": ["document", "measurement"]},
    {"name": "radiance", "personality": "creative", "strengths": ["video", "photo"]},
    {"name": "parallax", "personality": "specialist", "strengths": ["timestamp_proof", "signature"]},
    {"name": "horizon", "personality": "generalist", "strengths": ["photo", "delivery"]},
    {"name": "spectrum", "personality": "explorer", "strengths": ["photo", "screenshot"]},
    {"name": "pulsar", "personality": "analyst", "strengths": ["document", "text_response"]},
    {"name": "nova", "personality": "creative", "strengths": ["video", "photo", "receipt"]},
    {"name": "orbit", "personality": "specialist", "strengths": ["measurement", "notarized", "document"]},
]

TASK_CATEGORIES = ["photo", "delivery", "document", "measurement", "receipt", "video", "screenshot", "text_response"]

TASK_TEMPLATES = [
    ("Verify store location with photo", ["photo", "photo_geo"], 5.0),
    ("Deliver package to address", ["delivery"], 15.0),
    ("Scan and upload document", ["document"], 3.0),
    ("Measure room dimensions", ["measurement"], 8.0),
    ("Photograph receipt for expense report", ["receipt"], 2.0),
    ("Record 30-second video walkthrough", ["video"], 10.0),
    ("Take screenshot of dashboard", ["screenshot"], 1.5),
    ("Write product review (200 words)", ["text_response"], 4.0),
    ("Verify business hours sign", ["photo"], 3.0),
    ("Confirm delivery receipt", ["receipt", "photo"], 5.0),
    ("Document construction progress", ["photo", "video"], 12.0),
    ("Collect competitor pricing data", ["photo", "text_response"], 7.0),
    ("Inspect property condition", ["photo", "measurement"], 20.0),
    ("Verify event setup", ["photo", "video"], 8.0),
    ("Notarize legal document", ["document", "notarized"], 25.0),
    ("Capture timestamp proof of condition", ["photo", "timestamp_proof"], 6.0),
    ("Collect signed agreement", ["document", "signature"], 10.0),
    ("Survey retail shelf placement", ["photo", "measurement"], 9.0),
    ("Take geotagged photos of landmarks", ["photo_geo", "photo"], 4.0),
    ("Verify package delivery status", ["delivery", "photo"], 5.0),
]


def build_agent_data(idx: int, profile: dict) -> dict:
    """Build agent registration data with realistic reputation."""
    # Vary experience by index — older agents have more history
    experience_factor = min(idx * 0.1 + 0.3, 1.0)
    total_seals = int(5 + idx * 3 * experience_factor)
    positive_pct = 0.75 + random.random() * 0.2  # 75-95% positive

    total_tasks = int(10 + idx * 5 * experience_factor)
    successful = int(total_tasks * (0.8 + random.random() * 0.15))

    category_scores = {}
    for cat in profile["strengths"]:
        category_scores[cat] = 40 + random.random() * 50  # 40-90

    return {
        "agent_id": idx + 1,
        "name": profile["name"],
        "wallet_address": f"0x{(idx + 1):040X}",
        "personality": profile["personality"],
        "on_chain": OnChainReputation(
            agent_id=idx + 1,
            wallet_address=f"0x{(idx + 1):040X}",
            total_seals=total_seals,
            positive_seals=int(total_seals * positive_pct),
        ),
        "internal": InternalReputation(
            agent_id=idx + 1,
            total_tasks=total_tasks,
            successful_tasks=successful,
            avg_rating=3.5 + random.random() * 1.3,  # 3.5-4.8
            category_scores=category_scores,
        ),
        "budget_config": BudgetConfig(
            daily_limit_usd=5.0 + idx * 0.5,
            monthly_limit_usd=100.0 + idx * 10,
        ),
        "tags": profile["strengths"],
    }


def run_simulation(
    num_agents: int = 24,
    num_tasks: int = 20,
    live: bool = False,
):
    """Run the full swarm simulation."""
    print("=" * 70)
    print("  KK V2 SWARM SIMULATION")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    # Create coordinator
    if live:
        coord = SwarmCoordinator.create(em_api_url="https://api.execution.market")
        print("\n🌐 Connected to LIVE EM API")

        health = coord.em_client.get_health()
        status = health.get("status", "unknown")
        block = health.get("components", {}).get("blockchain", {}).get("details", {}).get("block_number", "?")
        print(f"   Status: {status}")
        print(f"   Block:  {block}")
    else:
        coord = SwarmCoordinator.create(em_api_url="http://localhost:3000")
        print("\n📦 Running in OFFLINE mode (no live API)")

    # ─── Register Agents ──────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  AGENT REGISTRATION ({num_agents} agents)")
    print(f"{'─' * 50}")

    start = time.monotonic()
    agents_data = []
    for i in range(min(num_agents, len(AGENT_PROFILES))):
        agents_data.append(build_agent_data(i, AGENT_PROFILES[i]))

    records = coord.register_agents_batch(agents_data)
    reg_ms = (time.monotonic() - start) * 1000
    print(f"  ✅ Registered {len(records)} agents in {reg_ms:.1f}ms")

    # Print agent roster
    for r in records[:10]:
        budget = coord.lifecycle.get_budget_status(r.agent_id)
        tags = ", ".join(r.tags[:3]) if r.tags else "general"
        print(f"     {r.agent_id:2d}. {r.name:12s} [{r.personality:10s}] "
              f"budget=${r.budget_config.daily_limit_usd:.0f}/day | {tags}")
    if len(records) > 10:
        print(f"     ... and {len(records) - 10} more")

    # ─── Ingest Tasks ─────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  TASK INGESTION ({num_tasks} tasks)")
    print(f"{'─' * 50}")

    # Ingest from live API if available
    if live:
        api_tasks = coord.ingest_from_api(status="published", limit=10)
        print(f"  📡 Ingested {len(api_tasks)} tasks from live API")

    # Add simulated tasks
    priorities = [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.NORMAL, TaskPriority.LOW]
    for i in range(num_tasks):
        template = TASK_TEMPLATES[i % len(TASK_TEMPLATES)]
        title, categories, base_bounty = template
        bounty = base_bounty * (0.8 + random.random() * 0.4)  # ±20% variation
        priority = random.choices(priorities, weights=[5, 15, 60, 20])[0]

        coord.ingest_task(
            task_id=f"sim_{i:04d}",
            title=f"{title} #{i+1}",
            categories=categories,
            bounty_usd=round(bounty, 2),
            priority=priority,
            source="simulation",
        )

    queue = coord.get_queue_summary()
    print(f"  📋 Queue: {queue['total']} tasks")
    print(f"     By status: {json.dumps(queue['by_status'])}")
    print(f"     By category: {json.dumps(queue['by_category'])}")
    print(f"     Pending bounty: ${queue['pending_bounty_usd']:.2f}")

    # ─── Route Tasks ──────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  TASK ROUTING")
    print(f"{'─' * 50}")

    strategies = [RoutingStrategy.BEST_FIT, RoutingStrategy.ROUND_ROBIN, RoutingStrategy.SPECIALIST]

    start = time.monotonic()
    all_results = []
    # Route in batches with different strategies to show variety
    batch_size = num_tasks // 3

    for i, strategy in enumerate(strategies):
        batch_results = coord.process_task_queue(
            strategy=strategy,
            max_tasks=batch_size + (1 if i == 2 else 0),  # Handle remainder
        )
        all_results.extend(batch_results)

    # Route any remaining
    remaining = coord.process_task_queue(max_tasks=num_tasks)
    all_results.extend(remaining)

    route_ms = (time.monotonic() - start) * 1000

    assignments = [r for r in all_results if isinstance(r, Assignment)]
    failures = [r for r in all_results if isinstance(r, RoutingFailure)]

    print(f"  ⚡ Routed in {route_ms:.1f}ms")
    print(f"     Assignments: {len(assignments)}")
    print(f"     Failures:    {len(failures)}")

    if assignments:
        print(f"\n  Top 5 Assignments:")
        for a in sorted(assignments, key=lambda x: x.score, reverse=True)[:5]:
            print(f"     {a.task_id:12s} → {a.agent_name:12s} "
                  f"score={a.score:5.1f} strategy={a.strategy_used.value}")

    if failures:
        print(f"\n  Failures:")
        for f in failures[:3]:
            print(f"     {f.task_id}: {f.reason}")

    # ─── Simulate Task Execution ──────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  TASK EXECUTION (simulated)")
    print(f"{'─' * 50}")

    completed = 0
    failed = 0
    total_earned = 0.0

    for assignment in assignments:
        # Simulate 85% success rate
        if random.random() < 0.85:
            task = coord._task_queue.get(assignment.task_id)
            bounty = task.bounty_usd if task else 0
            coord.complete_task(assignment.task_id, bounty_earned_usd=bounty)
            completed += 1
            total_earned += bounty
        else:
            errors = ["Worker cancelled", "Quality below threshold",
                     "Evidence not submitted", "Deadline exceeded", "Network error"]
            coord.fail_task(assignment.task_id, random.choice(errors))
            failed += 1

    print(f"  ✅ Completed: {completed}")
    print(f"  ❌ Failed:    {failed}")
    print(f"  💰 Earned:    ${total_earned:.2f}")

    # ─── Health Checks ────────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  HEALTH CHECKS")
    print(f"{'─' * 50}")

    report = coord.run_health_checks()
    print(f"  Agents checked: {report['agents']['checked']}")
    print(f"  Healthy:        {report['agents']['healthy']}")
    print(f"  Degraded:       {report['agents']['degraded']}")
    print(f"  Recovered:      {report['agents']['recovered']}")
    if report.get("systems"):
        print(f"  Systems:        {json.dumps(report['systems'])}")

    # ─── Final Dashboard ──────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print(f"  OPERATIONAL DASHBOARD")
    print(f"{'─' * 50}")

    dashboard = coord.get_dashboard()
    metrics = dashboard["metrics"]

    print(f"\n  📊 TASKS")
    for k, v in metrics["tasks"].items():
        print(f"     {k:25s}: {v}")

    print(f"\n  🤖 AGENTS")
    for k, v in metrics["agents"].items():
        print(f"     {k:25s}: {v}")

    print(f"\n  ⚙️  PERFORMANCE")
    for k, v in metrics["performance"].items():
        print(f"     {k:25s}: {v}")

    print(f"\n  💰 BUDGET")
    for k, v in metrics["budget"].items():
        print(f"     {k:25s}: {v}")

    # Agent fleet summary
    print(f"\n  🏴 FLEET ({len(dashboard['fleet'])} agents)")
    states = {}
    for agent in dashboard["fleet"]:
        state = agent["state"]
        states[state] = states.get(state, 0) + 1
    for state, count in sorted(states.items()):
        print(f"     {state:15s}: {count}")

    # Event summary
    event_counts = {}
    for e in dashboard["recent_events"]:
        et = e["event"]
        event_counts[et] = event_counts.get(et, 0) + 1
    print(f"\n  📡 EVENTS ({len(dashboard['recent_events'])} total)")
    for et, count in sorted(event_counts.items(), key=lambda x: -x[1]):
        print(f"     {et:25s}: {count}")

    print(f"\n{'=' * 70}")
    print(f"  SIMULATION COMPLETE")
    print(f"  Total time: {(time.monotonic() - start) * 1000:.0f}ms")
    print(f"={'=' * 69}")

    return dashboard


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KK V2 Swarm Simulation")
    parser.add_argument("--live", action="store_true", help="Connect to live EM API")
    parser.add_argument("--agents", type=int, default=24, help="Number of agents")
    parser.add_argument("--tasks", type=int, default=20, help="Number of tasks")
    args = parser.parse_args()

    run_simulation(
        num_agents=args.agents,
        num_tasks=args.tasks,
        live=args.live,
    )
