#!/usr/bin/env python3
"""
Production Data Profiler — Builds worker Skill DNA from live EM task history.

Ingests ALL completed tasks from the EM API, analyzes evidence and metadata,
builds worker profiles, and generates a production-ready dataset that the
SwarmCoordinator can use for intelligent routing decisions.

This is the bridge between historical data and future intelligent routing.

Usage:
    python3 production_profiler.py              # Full profile run
    python3 production_profiler.py --summary    # Summary only
    python3 production_profiler.py --export      # Export profiles to JSON
    python3 production_profiler.py --chains      # Chain utilization analysis

Output:
    ~/.em-production-profiles.json  — Worker Skill DNA profiles
    ~/.em-chain-analytics.json      — Per-chain analytics
"""

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp_server"))

from swarm.coordinator import EMApiClient


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


def metric(label, value, color=C.RESET):
    print(f"  {C.DIM}{label}:{C.RESET} {color}{value}{C.RESET}")


# ─── Task Fetcher ─────────────────────────────────────────────────────────────


def fetch_all_tasks(client: EMApiClient, status: str = "completed") -> list[dict]:
    """Fetch all tasks of a given status, handling pagination."""
    all_tasks = []
    offset = 0
    limit = 50

    while True:
        result = client._request(
            "GET", f"/api/v1/tasks?status={status}&limit={limit}&offset={offset}"
        )
        if isinstance(result, dict) and result.get("error"):
            break

        tasks = []
        if isinstance(result, list):
            tasks = result
        elif isinstance(result, dict):
            tasks = result.get("tasks", result.get("data", []))

        if not tasks:
            break

        all_tasks.extend(tasks)
        offset += len(tasks)

        # Safety: if we got fewer than limit, we're done
        if len(tasks) < limit:
            break

    return all_tasks


# ─── Analytics Engine ─────────────────────────────────────────────────────────


class ProductionAnalytics:
    """Analyzes production task data for operational insights."""

    def __init__(self, tasks: list[dict]):
        self.tasks = tasks
        self._computed = False

        # Chain analytics
        self.chain_counts = Counter()
        self.chain_bounties = defaultdict(float)
        self.chain_first_seen = {}
        self.chain_last_seen = {}

        # Token analytics
        self.token_counts = Counter()
        self.token_volume = defaultdict(float)

        # Category analytics
        self.category_counts = Counter()
        self.category_bounties = defaultdict(float)

        # Agent analytics
        self.agent_tasks = defaultdict(list)
        self.executor_tasks = defaultdict(list)

        # Time analytics
        self.tasks_by_day = Counter()
        self.tasks_by_hour = Counter()
        self.creation_dates = []

        # Bounty analytics
        self.bounties = []
        self.total_bounty = 0.0

        self._compute()

    def _compute(self):
        """Process all tasks and compute analytics."""
        for task in self.tasks:
            # Chain
            chain = task.get("payment_network", "unknown")
            self.chain_counts[chain] += 1
            bounty = float(task.get("bounty_usd", 0) or 0)
            self.chain_bounties[chain] += bounty

            created = task.get("created_at", "")
            if created:
                if (
                    chain not in self.chain_first_seen
                    or created < self.chain_first_seen[chain]
                ):
                    self.chain_first_seen[chain] = created
                if (
                    chain not in self.chain_last_seen
                    or created > self.chain_last_seen[chain]
                ):
                    self.chain_last_seen[chain] = created

            # Token
            token = task.get("payment_token", "unknown")
            self.token_counts[token] += 1
            self.token_volume[token] += bounty

            # Category
            category = task.get("category", "uncategorized")
            self.category_counts[category] += 1
            self.category_bounties[category] += bounty

            # Agent
            agent_id = task.get("agent_id", task.get("erc8004_agent_id", "unknown"))
            self.agent_tasks[str(agent_id)].append(task)

            # Executor
            executor_id = task.get("executor_id", "")
            if executor_id:
                self.executor_tasks[executor_id].append(task)

            # Time
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    day = dt.strftime("%Y-%m-%d")
                    self.tasks_by_day[day] += 1
                    self.tasks_by_hour[dt.hour] += 1
                    self.creation_dates.append(dt)
                except (ValueError, AttributeError):
                    pass

            # Bounty
            self.bounties.append(bounty)
            self.total_bounty += bounty

        self._computed = True

    def chain_report(self) -> dict:
        """Per-chain utilization report."""
        report = {}
        for chain in sorted(self.chain_counts, key=self.chain_counts.get, reverse=True):
            report[chain] = {
                "tasks": self.chain_counts[chain],
                "total_bounty_usd": round(self.chain_bounties[chain], 2),
                "avg_bounty_usd": round(
                    self.chain_bounties[chain] / self.chain_counts[chain], 2
                )
                if self.chain_counts[chain]
                else 0,
                "first_task": self.chain_first_seen.get(chain, ""),
                "last_task": self.chain_last_seen.get(chain, ""),
                "share_pct": round(self.chain_counts[chain] / len(self.tasks) * 100, 1),
            }
        return report

    def time_report(self) -> dict:
        """Temporal distribution analysis."""
        if not self.creation_dates:
            return {}

        dates_sorted = sorted(self.creation_dates)
        span = (dates_sorted[-1] - dates_sorted[0]).days + 1

        # Find busiest day
        busiest_day = (
            self.tasks_by_day.most_common(1)[0] if self.tasks_by_day else ("none", 0)
        )

        # Find busiest hour
        busiest_hour = (
            self.tasks_by_hour.most_common(1)[0] if self.tasks_by_hour else (0, 0)
        )

        return {
            "total_days": span,
            "first_task": dates_sorted[0].isoformat(),
            "last_task": dates_sorted[-1].isoformat(),
            "avg_tasks_per_day": round(len(self.tasks) / max(span, 1), 1),
            "busiest_day": {"date": busiest_day[0], "count": busiest_day[1]},
            "busiest_hour_utc": {"hour": busiest_hour[0], "count": busiest_hour[1]},
            "daily_distribution": dict(sorted(self.tasks_by_day.items())),
        }

    def executor_report(self) -> dict:
        """Worker/executor analysis."""
        report = {}
        for executor_id, tasks in sorted(
            self.executor_tasks.items(),
            key=lambda x: len(x[1]),
            reverse=True,
        ):
            chains_used = set()
            categories = Counter()
            total_bounty = 0.0

            for task in tasks:
                chains_used.add(task.get("payment_network", "unknown"))
                categories[task.get("category", "unknown")] += 1
                total_bounty += float(task.get("bounty_usd", 0) or 0)

            report[executor_id] = {
                "tasks_completed": len(tasks),
                "total_earned_usd": round(total_bounty, 2),
                "chains_used": sorted(chains_used),
                "categories": dict(categories.most_common()),
                "avg_bounty_usd": round(total_bounty / len(tasks), 2) if tasks else 0,
            }
        return report

    def summary(self) -> dict:
        """High-level summary."""
        return {
            "total_tasks": len(self.tasks),
            "total_bounty_usd": round(self.total_bounty, 2),
            "avg_bounty_usd": round(self.total_bounty / len(self.tasks), 2)
            if self.tasks
            else 0,
            "unique_chains": len(self.chain_counts),
            "unique_tokens": len(self.token_counts),
            "unique_categories": len(self.category_counts),
            "unique_agents": len(self.agent_tasks),
            "unique_executors": len(self.executor_tasks),
            "chains": dict(self.chain_counts.most_common()),
            "tokens": dict(self.token_counts.most_common()),
            "categories": dict(self.category_counts.most_common()),
        }


# ─── Profile Builder ─────────────────────────────────────────────────────────


class ProductionProfileBuilder:
    """Builds worker profiles from production task history."""

    def __init__(self, analytics: ProductionAnalytics):
        self.analytics = analytics
        self.profiles = {}

    def build_profiles(self) -> dict:
        """Build Skill DNA profiles from production data."""
        for executor_id, tasks in self.analytics.executor_tasks.items():
            profile = self._build_executor_profile(executor_id, tasks)
            self.profiles[executor_id] = profile

        return self.profiles

    def _build_executor_profile(self, executor_id: str, tasks: list[dict]) -> dict:
        """Build a single executor's profile."""
        chains = Counter()
        categories = Counter()
        tokens = Counter()
        bounties = []
        deadline_window_hours = []

        for task in tasks:
            chains[task.get("payment_network", "unknown")] += 1
            categories[task.get("category", "unknown")] += 1
            tokens[task.get("payment_token", "unknown")] += 1
            bounty = float(task.get("bounty_usd", 0) or 0)
            bounties.append(bounty)

            # Estimate deadline window from created_at → deadline
            created = task.get("created_at", "")
            deadline = task.get("deadline", "")
            if created and deadline:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    deadline_dt = datetime.fromisoformat(
                        deadline.replace("Z", "+00:00")
                    )
                    delta_hours = (deadline_dt - created_dt).total_seconds() / 3600
                    deadline_window_hours.append(delta_hours)
                except (ValueError, AttributeError):
                    pass

        total_bounty = sum(bounties)

        # Compute specialization score (how focused vs diverse)
        total_tasks = len(tasks)
        max_category_share = (
            max(categories.values()) / total_tasks if total_tasks else 0
        )
        # Dynamic normalization: use total unique chains seen across all executors,
        # falling back to the number of chains this executor has used (min 1).
        available_chains = (
            len(self.analytics.chain_counts)
            if self.analytics.chain_counts
            else max(len(chains), 1)
        )
        chain_diversity = len(chains) / available_chains

        return {
            "executor_id": executor_id,
            "total_tasks": total_tasks,
            "total_earned_usd": round(total_bounty, 2),
            "avg_bounty_usd": round(total_bounty / total_tasks, 2)
            if total_tasks
            else 0,
            "chains": dict(chains.most_common()),
            "categories": dict(categories.most_common()),
            "tokens": dict(tokens.most_common()),
            "chain_diversity": round(chain_diversity, 2),
            "specialization_score": round(max_category_share, 2),
            "avg_deadline_window_hours": round(
                sum(deadline_window_hours) / len(deadline_window_hours), 1
            )
            if deadline_window_hours
            else None,
            "skill_dna": {
                "primary_category": categories.most_common(1)[0][0]
                if categories
                else "unknown",
                "primary_chain": chains.most_common(1)[0][0] if chains else "unknown",
                "experience_level": self._determine_experience(total_tasks),
                "reliability_score": 1.0,  # All completed = 100% reliable from this data
                "multi_chain": len(chains) > 1,
            },
        }

    def _determine_experience(self, total_tasks: int) -> str:
        """Map task count to experience level."""
        if total_tasks >= 100:
            return "expert"
        elif total_tasks >= 50:
            return "advanced"
        elif total_tasks >= 20:
            return "intermediate"
        elif total_tasks >= 5:
            return "beginner"
        else:
            return "novice"


# ─── Commands ─────────────────────────────────────────────────────────────────


def cmd_full(args):
    """Full production profiling run."""
    header("PRODUCTION DATA PROFILER")

    # Fetch data
    subheader("Fetching Production Data")
    client = EMApiClient()

    start = time.monotonic()
    completed = fetch_all_tasks(client, "completed")
    fetch_ms = (time.monotonic() - start) * 1000
    ok(f"Fetched {len(completed)} completed tasks in {fetch_ms:.0f}ms")

    expired = fetch_all_tasks(client, "expired")
    ok(f"Fetched {len(expired)} expired tasks")

    # Analyze completed tasks
    subheader("Analyzing Completed Tasks")
    analytics = ProductionAnalytics(completed)
    summary = analytics.summary()

    metric("Total tasks", summary["total_tasks"])
    metric("Total bounty", f"${summary['total_bounty_usd']:.2f}", C.CYAN)
    metric("Avg bounty", f"${summary['avg_bounty_usd']:.2f}")
    metric("Unique chains", summary["unique_chains"])
    metric("Unique executors", summary["unique_executors"])

    # Chain report
    subheader("Chain Utilization")
    chain_report = analytics.chain_report()
    for chain, data in chain_report.items():
        share = data["share_pct"]
        bar = "█" * int(share / 2) + "░" * (50 - int(share / 2))
        color = (
            C.GREEN
            if data["tasks"] >= 10
            else C.YELLOW
            if data["tasks"] >= 5
            else C.DIM
        )
        print(
            f"  {color}{chain:12s}{C.RESET} {bar} {data['tasks']:3d} tasks (${data['total_bounty_usd']:.2f})"
        )

    # Token report
    subheader("Token Distribution")
    for token, count in analytics.token_counts.most_common():
        volume = analytics.token_volume[token]
        metric(f"{token}", f"{count} tasks, ${volume:.2f} volume")

    # Category report
    subheader("Task Categories")
    for cat, count in analytics.category_counts.most_common():
        bounty = analytics.category_bounties[cat]
        metric(f"{cat}", f"{count} tasks, ${bounty:.2f} total")

    # Time report
    subheader("Temporal Analysis")
    time_report = analytics.time_report()
    if time_report:
        metric("Active period", f"{time_report['total_days']} days")
        metric("First task", time_report["first_task"][:19])
        metric("Last task", time_report["last_task"][:19])
        metric("Avg tasks/day", time_report["avg_tasks_per_day"])
        metric(
            "Busiest day",
            f"{time_report['busiest_day']['date']} ({time_report['busiest_day']['count']} tasks)",
        )

    # Executor profiles
    subheader("Worker Profiles")
    builder = ProductionProfileBuilder(analytics)
    profiles = builder.build_profiles()

    for executor_id, profile in profiles.items():
        chains_str = ", ".join(profile["chains"].keys())
        exp = profile["skill_dna"]["experience_level"]
        print(
            f"  {C.GREEN}●{C.RESET} {executor_id[:12]}... — {profile['total_tasks']} tasks, "
            f"${profile['total_earned_usd']:.2f}, {exp}"
        )
        print(
            f"    {C.DIM}Chains: {chains_str} | Primary: {profile['skill_dna']['primary_category']}{C.RESET}"
        )

    # Expired task analysis
    subheader("Expired Task Analysis")
    if expired:
        expired_analytics = ProductionAnalytics(expired)
        expired_summary = expired_analytics.summary()
        metric("Total expired", expired_summary["total_tasks"])
        metric("Lost bounty", f"${expired_summary['total_bounty_usd']:.2f}", C.RED)

        # Expiry rate
        total_tasks = len(completed) + len(expired)
        expiry_rate = len(expired) / total_tasks * 100 if total_tasks else 0
        metric(
            "Expiry rate",
            f"{expiry_rate:.1f}%",
            C.YELLOW if expiry_rate > 30 else C.GREEN,
        )

    # Export profiles
    if args.export:
        profile_path = os.path.expanduser("~/.em-production-profiles.json")
        with open(profile_path, "w") as f:
            json.dump(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_tasks_analyzed": len(completed),
                    "profiles": profiles,
                    "chain_analytics": chain_report,
                    "summary": summary,
                },
                f,
                indent=2,
            )
        ok(f"Profiles exported to {profile_path}")

    # Insights
    subheader("🧠 Insights")

    # Insight 1: Category diversity
    if len(analytics.category_counts) == 1:
        warn(
            f"All {len(completed)} tasks are '{list(analytics.category_counts.keys())[0]}' — "
            f"need category diversity for richer Skill DNA"
        )

    # Insight 2: Chain utilization
    if len(analytics.chain_counts) >= 5:
        ok(f"Multi-chain operational: {len(analytics.chain_counts)} chains active")

    # Insight 3: Worker concentration
    max_worker = max(analytics.executor_tasks.items(), key=lambda x: len(x[1]))
    worker_concentration = len(max_worker[1]) / len(completed) * 100
    if worker_concentration > 90:
        warn(
            f"Worker concentration: {worker_concentration:.0f}% tasks by single executor — "
            f"need more workers for swarm routing diversity"
        )

    # Insight 4: Expiry rate
    if expired and len(expired) > len(completed) * 0.3:
        warn(
            f"High expiry rate ({len(expired)}/{len(completed) + len(expired)} = "
            f"{len(expired) / (len(completed) + len(expired)) * 100:.0f}%) — "
            f"indicates supply/demand imbalance"
        )

    print()
    ok("Production profiling complete!")
    print()


def cmd_summary(args):
    """Quick summary only."""
    header("PRODUCTION DATA — SUMMARY")

    client = EMApiClient()
    completed = fetch_all_tasks(client, "completed")
    expired = fetch_all_tasks(client, "expired")

    analytics = ProductionAnalytics(completed)
    summary = analytics.summary()

    total_all = len(completed) + len(expired)
    completion_rate = len(completed) / total_all * 100 if total_all else 0

    metric("Completed tasks", summary["total_tasks"])
    metric("Expired tasks", len(expired))
    metric("Completion rate", f"{completion_rate:.1f}%")
    metric("Total bounty processed", f"${summary['total_bounty_usd']:.2f}")
    metric(
        "Chains active",
        f"{summary['unique_chains']} ({', '.join(summary['chains'].keys())})",
    )
    metric(
        "Tokens used",
        f"{summary['unique_tokens']} ({', '.join(summary['tokens'].keys())})",
    )
    metric("Unique executors", summary["unique_executors"])
    print()


def cmd_chains(args):
    """Chain utilization analysis."""
    header("PRODUCTION DATA — CHAIN ANALYTICS")

    client = EMApiClient()
    completed = fetch_all_tasks(client, "completed")

    analytics = ProductionAnalytics(completed)
    chain_report = analytics.chain_report()

    subheader("Chain Utilization Matrix")
    print(
        f"\n  {'Chain':12s} {'Tasks':>6s} {'Share':>7s} {'Bounty':>10s} {'Avg':>7s}  {'First Seen':19s}"
    )
    print(f"  {'─' * 12} {'─' * 6} {'─' * 7} {'─' * 10} {'─' * 7}  {'─' * 19}")

    for chain, data in chain_report.items():
        first = data["first_task"][:10] if data["first_task"] else "?"
        print(
            f"  {chain:12s} {data['tasks']:6d} {data['share_pct']:6.1f}% "
            f"${data['total_bounty_usd']:8.2f} ${data['avg_bounty_usd']:5.2f}  {first}"
        )

    # Export
    if args.export:
        path = os.path.expanduser("~/.em-chain-analytics.json")
        with open(path, "w") as f:
            json.dump(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "chains": chain_report,
                },
                f,
                indent=2,
            )
        ok(f"Exported to {path}")

    print()


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Production Data Profiler — Build worker Skill DNA from EM task history",
    )
    parser.add_argument("--summary", action="store_true", help="Quick summary only")
    parser.add_argument(
        "--chains", action="store_true", help="Chain utilization analysis"
    )
    parser.add_argument("--export", action="store_true", help="Export profiles to JSON")

    args = parser.parse_args()

    if args.summary:
        cmd_summary(args)
    elif args.chains:
        cmd_chains(args)
    else:
        cmd_full(args)


if __name__ == "__main__":
    main()
