#!/usr/bin/env python3
"""
Swarm Simulation — End-to-End KK V2 System Exercise
====================================================

Simulates a realistic multi-agent swarm processing tasks from a realistic
task distribution. Exercises the full pipeline:

    Scheduler → Coordinator → Orchestrator → ReputationBridge → Analytics

Produces:
- Throughput metrics (tasks/sec, routing latency)
- Budget utilization across agents
- Strategy effectiveness comparison
- Urgency handling accuracy
- Load balancer effectiveness
- Full dashboard snapshot

Usage:
    python3 scripts/kk/swarm_simulation.py
    python3 scripts/kk/swarm_simulation.py --agents 24 --tasks 500 --cycles 20
"""

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from mcp_server.swarm.reputation_bridge import (  # noqa: E402
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
)
from mcp_server.swarm.lifecycle_manager import (  # noqa: E402
    LifecycleManager,
    AgentState,
    BudgetConfig,
)
from mcp_server.swarm.orchestrator import (  # noqa: E402
    SwarmOrchestrator,
    TaskPriority,
)
from mcp_server.swarm.coordinator import SwarmCoordinator  # noqa: E402
from mcp_server.swarm.scheduler import (  # noqa: E402
    SwarmScheduler,
)
from mcp_server.swarm.analytics import SwarmAnalytics, TaskEvent  # noqa: E402


# ──────────────────────────────────────────────────────────────
# Simulation Constants
# ──────────────────────────────────────────────────────────────

# Category distribution (matches production data from March 18 analysis)
CATEGORY_DISTRIBUTION = {
    "simple_action": 0.55,
    "knowledge_access": 0.12,
    "code_execution": 0.10,
    "physical_presence": 0.08,
    "research": 0.05,
    "data_collection": 0.04,
    "photo_verification": 0.03,
    "notarization": 0.02,
    "technical_task": 0.01,
}

# Bounty distribution (realistic USD values)
BOUNTY_RANGES = {
    "simple_action": (0.10, 2.00),
    "knowledge_access": (0.50, 5.00),
    "code_execution": (2.00, 25.00),
    "physical_presence": (1.00, 10.00),
    "research": (1.00, 15.00),
    "data_collection": (0.25, 3.00),
    "photo_verification": (0.50, 5.00),
    "notarization": (5.00, 50.00),
    "technical_task": (5.00, 100.00),
}

# Agent personality distribution
PERSONALITY_TYPES = [
    "explorer",
    "specialist",
    "generalist",
    "budget_hawk",
    "speed_demon",
]

# Agent specialties
AGENT_SPECIALTIES = {
    "explorer": ["simple_action", "data_collection", "photo_verification"],
    "specialist": ["code_execution", "technical_task", "research"],
    "generalist": list(CATEGORY_DISTRIBUTION.keys()),
    "budget_hawk": ["simple_action", "knowledge_access", "data_collection"],
    "speed_demon": ["simple_action", "knowledge_access", "photo_verification"],
}


def weighted_choice(distribution: dict) -> str:
    """Pick a category based on weighted distribution."""
    categories = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(categories, weights=weights, k=1)[0]


def generate_task(task_id: int) -> dict:
    """Generate a realistic task."""
    category = weighted_choice(CATEGORY_DISTRIBUTION)
    lo, hi = BOUNTY_RANGES.get(category, (0.10, 5.00))
    bounty = round(random.uniform(lo, hi), 2)

    # 20% of tasks have deadlines
    deadline = None
    if random.random() < 0.20:
        hours = random.choice([0.5, 1, 2, 4, 8, 12, 24, 48])
        deadline = datetime.now(timezone.utc) + timedelta(hours=hours)

    # Priority distribution
    priority = random.choices(
        [
            TaskPriority.CRITICAL,
            TaskPriority.HIGH,
            TaskPriority.NORMAL,
            TaskPriority.LOW,
        ],
        weights=[0.05, 0.15, 0.60, 0.20],
        k=1,
    )[0]

    return {
        "task_id": f"sim-{task_id:04d}",
        "title": f"Simulated {category.replace('_', ' ').title()} Task #{task_id}",
        "categories": [category],
        "bounty_usd": bounty,
        "priority": priority,
        "deadline": deadline,
    }


def generate_agent(agent_id: int) -> dict:
    """Generate a realistic agent profile."""
    personality = random.choice(PERSONALITY_TYPES)
    specialties = AGENT_SPECIALTIES[personality]

    # Generate skill scores for specialties
    category_scores = {}
    for cat in CATEGORY_DISTRIBUTION:
        if cat in specialties:
            category_scores[cat] = random.uniform(60, 95)
        else:
            category_scores[cat] = random.uniform(10, 40)

    total_tasks = random.randint(5, 200)
    success_rate = random.uniform(0.65, 0.98)
    successful = int(total_tasks * success_rate)

    return {
        "agent_id": agent_id,
        "name": f"agent_{personality}_{agent_id:03d}",
        "wallet": f"0x{random.randbytes(20).hex()}",
        "personality": personality,
        "total_tasks": total_tasks,
        "successful_tasks": successful,
        "avg_rating": round(random.uniform(3.0, 5.0), 2),
        "bayesian_score": round(random.uniform(0.4, 0.95), 3),
        "category_scores": category_scores,
        "chains_active": random.sample(
            [
                "ethereum",
                "base",
                "polygon",
                "arbitrum",
                "optimism",
                "avalanche",
                "celo",
                "monad",
            ],
            k=random.randint(1, 5),
        ),
        "daily_budget": round(random.uniform(2.0, 20.0), 2),
    }


# ──────────────────────────────────────────────────────────────
# Simulation Engine
# ──────────────────────────────────────────────────────────────


class SwarmSimulation:
    """Full swarm simulation engine."""

    def __init__(self, n_agents: int = 24, n_tasks: int = 200, n_cycles: int = 10):
        self.n_agents = n_agents
        self.n_tasks = n_tasks
        self.n_cycles = n_cycles

        # Core components
        self.bridge = ReputationBridge()
        self.lifecycle = LifecycleManager()
        self.orchestrator = SwarmOrchestrator(
            self.bridge,
            self.lifecycle,
            min_score_threshold=10.0,
            cooldown_seconds=0,  # No cooldown in simulation
        )
        self.coordinator = SwarmCoordinator(
            bridge=self.bridge,
            lifecycle=self.lifecycle,
            orchestrator=self.orchestrator,
            task_expiry_hours=48.0,
        )
        self.scheduler = SwarmScheduler(
            coordinator=self.coordinator,
            max_batch_size=10,
            enable_circuit_breakers=False,
        )
        self.analytics = SwarmAnalytics()

        # Simulation state
        self.agents = []
        self.tasks = []
        self.results = {
            "total_assigned": 0,
            "total_failed": 0,
            "total_completed": 0,
            "strategy_results": {},
            "category_results": {},
            "urgency_results": {},
            "cycle_times": [],
            "per_agent": {},
        }

    def setup(self) -> None:
        """Initialize agents and tasks."""
        print(f"🔧 Setting up simulation: {self.n_agents} agents, {self.n_tasks} tasks")

        # Register agents
        for i in range(self.n_agents):
            agent_data = generate_agent(i + 1)
            self.agents.append(agent_data)

            on_chain = OnChainReputation(
                agent_id=agent_data["agent_id"],
                wallet_address=agent_data["wallet"],
                total_seals=agent_data["total_tasks"],
                positive_seals=agent_data["successful_tasks"],
                chains_active=agent_data["chains_active"],
            )
            internal = InternalReputation(
                agent_id=agent_data["agent_id"],
                bayesian_score=agent_data["bayesian_score"],
                total_tasks=agent_data["total_tasks"],
                successful_tasks=agent_data["successful_tasks"],
                avg_rating=agent_data["avg_rating"],
                category_scores=agent_data["category_scores"],
            )

            self.coordinator.register_agent(
                agent_id=agent_data["agent_id"],
                name=agent_data["name"],
                wallet_address=agent_data["wallet"],
                personality=agent_data["personality"],
                budget_config=BudgetConfig(
                    daily_limit_usd=agent_data["daily_budget"],
                    monthly_limit_usd=agent_data["daily_budget"] * 30,
                    task_limit_usd=50.0,
                ),
                on_chain=on_chain,
                internal=internal,
                activate=True,
            )

        # Generate tasks
        for i in range(self.n_tasks):
            task = generate_task(i + 1)
            self.tasks.append(task)

        print(f"   ✅ {self.n_agents} agents registered")
        print(f"   ✅ {self.n_tasks} tasks generated")

    def run(self) -> dict:
        """Run the full simulation."""
        print(f"\n🚀 Running {self.n_cycles} scheduling cycles...\n")

        tasks_per_cycle = max(1, self.n_tasks // self.n_cycles)
        task_idx = 0

        for cycle in range(1, self.n_cycles + 1):
            cycle_start = time.monotonic()

            # Ingest a batch of tasks into the scheduler
            batch_end = min(task_idx + tasks_per_cycle, self.n_tasks)
            for i in range(task_idx, batch_end):
                t = self.tasks[i]
                self.scheduler.add_task(**t)
            task_idx = batch_end

            # Complete all assigned tasks from previous cycle and re-activate agents
            for agent_id, record in list(self.lifecycle.agents.items()):
                if record.state == AgentState.WORKING and record.current_task_id:
                    # Simulate instant completion
                    try:
                        self.lifecycle.complete_task(agent_id, cooldown_seconds=0)
                    except Exception:
                        pass
                if record.state == AgentState.COOLDOWN:
                    record.cooldown_until = None  # Expire cooldown immediately
                    self.lifecycle.check_cooldown_expiry(agent_id)
                if record.state == AgentState.IDLE:
                    try:
                        self.lifecycle.transition(
                            agent_id, AgentState.ACTIVE, "sim re-activate"
                        )
                    except Exception:
                        pass

            # Also release claims in orchestrator for completed tasks
            for task_id in list(self.orchestrator._active_claims.keys()):
                self.orchestrator.complete_task(task_id)

            # Re-activate any agents left in non-active states
            for agent_id, record in list(self.lifecycle.agents.items()):
                if record.state in (AgentState.COOLDOWN, AgentState.IDLE):
                    if record.state == AgentState.COOLDOWN:
                        record.cooldown_until = None
                        self.lifecycle.check_cooldown_expiry(agent_id)
                    if record.state == AgentState.IDLE:
                        try:
                            self.lifecycle.transition(
                                agent_id, AgentState.ACTIVE, "sim re-activate"
                            )
                        except Exception:
                            pass

            # Run scheduling cycle
            cycle_result = self.scheduler.run_scheduling_cycle()

            cycle_ms = (time.monotonic() - cycle_start) * 1000
            self.results["cycle_times"].append(cycle_ms)

            assigned = cycle_result.get("tasks_assigned", 0)
            failed = cycle_result.get("tasks_failed", 0)
            self.results["total_assigned"] += assigned
            self.results["total_failed"] += failed

            # Record analytics events for assigned tasks
            for r in cycle_result.get("results", []):
                if r.get("outcome") == "assigned":
                    task_data = next(
                        (t for t in self.tasks if t["task_id"] == r["task_id"]), None
                    )
                    if task_data:
                        cat = (
                            task_data["categories"][0]
                            if task_data["categories"]
                            else "unknown"
                        )
                        strategy = r.get("strategy", "unknown")

                        # Track strategy results
                        if strategy not in self.results["strategy_results"]:
                            self.results["strategy_results"][strategy] = {
                                "assigned": 0,
                                "total_bounty": 0.0,
                            }
                        self.results["strategy_results"][strategy]["assigned"] += 1
                        self.results["strategy_results"][strategy]["total_bounty"] += (
                            task_data["bounty_usd"]
                        )

                        # Track category results
                        if cat not in self.results["category_results"]:
                            self.results["category_results"][cat] = {"assigned": 0}
                        self.results["category_results"][cat]["assigned"] += 1

                        # Track per-agent
                        agent_id = r.get("agent_id", 0)
                        if agent_id not in self.results["per_agent"]:
                            self.results["per_agent"][agent_id] = {
                                "assigned": 0,
                                "bounty": 0.0,
                            }
                        self.results["per_agent"][agent_id]["assigned"] += 1
                        self.results["per_agent"][agent_id]["bounty"] += task_data[
                            "bounty_usd"
                        ]

                        # Record in analytics
                        self.analytics.record_event(
                            TaskEvent(
                                event_type="task_completed",
                                agent_id=str(agent_id),
                                task_id=r["task_id"],
                                category=cat,
                                bounty_usd=task_data["bounty_usd"],
                                quality_rating=random.uniform(3.5, 5.0),
                                duration_seconds=random.uniform(300, 7200),
                            )
                        )

                        # Simulate task completion in coordinator
                        self.coordinator.complete_task(
                            r["task_id"], task_data["bounty_usd"]
                        )

            # Progress
            remaining = self.scheduler.pending_count
            print(
                f"   Cycle {cycle:2d}: "
                f"assigned={assigned:3d} failed={failed:3d} "
                f"remaining={remaining:3d} "
                f"time={cycle_ms:.1f}ms"
            )

        return self.results

    def report(self) -> str:
        """Generate a comprehensive simulation report."""
        lines = []
        lines.append("=" * 70)
        lines.append("   KK V2 SWARM SIMULATION REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Summary
        total = self.results["total_assigned"] + self.results["total_failed"]
        success_rate = self.results["total_assigned"] / total * 100 if total > 0 else 0
        lines.append("📊 SUMMARY")
        lines.append(f"   Agents: {self.n_agents}")
        lines.append(f"   Tasks generated: {self.n_tasks}")
        lines.append(f"   Cycles: {self.n_cycles}")
        lines.append(f"   Tasks assigned: {self.results['total_assigned']}")
        lines.append(f"   Tasks failed: {self.results['total_failed']}")
        lines.append(f"   Assignment rate: {success_rate:.1f}%")
        lines.append(f"   Remaining in pool: {self.scheduler.pending_count}")
        lines.append("")

        # Timing
        if self.results["cycle_times"]:
            times = self.results["cycle_times"]
            avg = sum(times) / len(times)
            p95 = sorted(times)[int(len(times) * 0.95)] if len(times) >= 2 else times[0]
            lines.append("⏱️  PERFORMANCE")
            lines.append(f"   Avg cycle time: {avg:.1f}ms")
            lines.append(f"   P95 cycle time: {p95:.1f}ms")
            lines.append(f"   Total time: {sum(times):.0f}ms")
            throughput = (
                self.results["total_assigned"] / (sum(times) / 1000)
                if sum(times) > 0
                else 0
            )
            lines.append(f"   Throughput: {throughput:.0f} tasks/sec")
            lines.append("")

        # Strategy breakdown
        if self.results["strategy_results"]:
            lines.append("🎯 STRATEGY EFFECTIVENESS")
            for strategy, data in sorted(
                self.results["strategy_results"].items(),
                key=lambda x: x[1]["assigned"],
                reverse=True,
            ):
                pct = (
                    data["assigned"] / self.results["total_assigned"] * 100
                    if self.results["total_assigned"] > 0
                    else 0
                )
                lines.append(
                    f"   {strategy:15s}: {data['assigned']:4d} tasks ({pct:5.1f}%) "
                    f"${data['total_bounty']:8.2f} bounty"
                )
            lines.append("")

        # Category breakdown
        if self.results["category_results"]:
            lines.append("📂 CATEGORY DISTRIBUTION")
            for cat, data in sorted(
                self.results["category_results"].items(),
                key=lambda x: x[1]["assigned"],
                reverse=True,
            ):
                pct = (
                    data["assigned"] / self.results["total_assigned"] * 100
                    if self.results["total_assigned"] > 0
                    else 0
                )
                bar = "█" * int(pct / 2)
                lines.append(f"   {cat:25s}: {data['assigned']:4d} ({pct:5.1f}%) {bar}")
            lines.append("")

        # Top agents
        if self.results["per_agent"]:
            lines.append("🏆 TOP 10 AGENTS BY ASSIGNMENTS")
            sorted_agents = sorted(
                self.results["per_agent"].items(),
                key=lambda x: x[1]["assigned"],
                reverse=True,
            )[:10]
            for agent_id, data in sorted_agents:
                agent_data = next(
                    (a for a in self.agents if a["agent_id"] == agent_id), None
                )
                name = agent_data["name"] if agent_data else f"agent_{agent_id}"
                personality = agent_data["personality"] if agent_data else "?"
                lines.append(
                    f"   {name:30s} ({personality:12s}): "
                    f"{data['assigned']:3d} tasks, ${data['bounty']:.2f}"
                )
            lines.append("")

        # Load distribution (Gini coefficient)
        if self.results["per_agent"]:
            assignments = sorted(
                [d["assigned"] for d in self.results["per_agent"].values()]
            )
            n = len(assignments)
            if n > 0 and sum(assignments) > 0:
                total_assignments = sum(assignments)
                # Gini: 0 = perfect equality, 1 = one agent does everything
                cumulative = 0
                gini_sum = 0
                for i, a in enumerate(assignments):
                    cumulative += a
                    gini_sum += (2 * (i + 1) - n - 1) * a
                gini = (
                    gini_sum / (n * total_assignments) if total_assignments > 0 else 0
                )
                lines.append("⚖️  LOAD DISTRIBUTION")
                lines.append(
                    f"   Gini coefficient: {gini:.3f} (0=perfect equality, 1=monopoly)"
                )
                lines.append(f"   Active agents: {len(assignments)}/{self.n_agents}")
                if assignments:
                    lines.append(f"   Min assignments: {assignments[0]}")
                    lines.append(f"   Max assignments: {assignments[-1]}")
                    lines.append(f"   Median: {assignments[len(assignments) // 2]}")
                lines.append("")

        # Urgency distribution
        urgency_dist = self.scheduler.get_urgency_distribution()
        if urgency_dist:
            lines.append("🔥 URGENCY DISTRIBUTION (remaining)")
            for level, count in sorted(urgency_dist.items()):
                lines.append(f"   {level:10s}: {count}")
            lines.append("")

        # Analytics dashboard
        dashboard = self.analytics.get_dashboard()
        if dashboard:
            lines.append("📈 ANALYTICS DASHBOARD")
            perf = dashboard.get("performance", {})
            lines.append(f"   Completed: {perf.get('total_tasks_completed', 0)}")
            lines.append(f"   Avg quality: {perf.get('avg_quality', 0):.2f}/5.0")
            lines.append(f"   Revenue: ${perf.get('total_revenue_usd', 0):.2f}")
            lines.append(f"   Success rate: {perf.get('avg_success_rate', 0):.2%}")
            lines.append("")

        # Scheduler status
        sched = self.scheduler.get_status()
        lines.append("🗓️  SCHEDULER STATUS")
        lines.append(f"   Cycles run: {sched['cycles_run']}")
        lines.append(f"   Tasks scheduled: {sched['tasks_scheduled']}")
        lines.append(f"   Tasks deferred: {sched['tasks_deferred']}")
        lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="KK V2 Swarm Simulation")
    parser.add_argument("--agents", type=int, default=24, help="Number of agents")
    parser.add_argument("--tasks", type=int, default=200, help="Number of tasks")
    parser.add_argument("--cycles", type=int, default=10, help="Scheduling cycles")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()

    random.seed(args.seed)

    sim = SwarmSimulation(
        n_agents=args.agents,
        n_tasks=args.tasks,
        n_cycles=args.cycles,
    )
    sim.setup()
    results = sim.run()
    report = sim.report()

    print(f"\n{report}")

    if args.json:
        # Serialize-safe results
        json_results = {
            "config": {
                "agents": args.agents,
                "tasks": args.tasks,
                "cycles": args.cycles,
                "seed": args.seed,
            },
            "summary": {
                "total_assigned": results["total_assigned"],
                "total_failed": results["total_failed"],
                "remaining": sim.scheduler.pending_count,
                "assignment_rate": round(
                    results["total_assigned"]
                    / (results["total_assigned"] + results["total_failed"])
                    * 100
                    if (results["total_assigned"] + results["total_failed"]) > 0
                    else 0,
                    1,
                ),
            },
            "strategy_results": results["strategy_results"],
            "category_results": results["category_results"],
            "timing": {
                "avg_cycle_ms": round(
                    sum(results["cycle_times"]) / len(results["cycle_times"]), 1
                )
                if results["cycle_times"]
                else 0,
                "total_ms": round(sum(results["cycle_times"]), 0),
            },
            "dashboard": sim.analytics.get_dashboard(),
        }
        output = json.dumps(json_results, indent=2)
        if args.output:
            Path(args.output).write_text(output)
            print(f"\n📁 JSON saved to {args.output}")
        else:
            print(output)


if __name__ == "__main__":
    main()
