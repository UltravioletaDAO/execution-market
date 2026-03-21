#!/usr/bin/env python3
"""
Production Analyzer — Deep analysis of live Execution Market data
through the KK V2 Swarm intelligence lens.

Connects to the live EM API, pulls all tasks and worker data, and
generates insights about:
  - Task distribution and category diversity
  - Worker specialization patterns
  - Routing quality predictions
  - Evidence quality signals
  - Flywheel health metrics
  - Swarm readiness assessment

Usage:
    python3 production_analyzer.py               # Full analysis
    python3 production_analyzer.py --summary      # Quick summary only
    python3 production_analyzer.py --export json   # Export to JSON
    python3 production_analyzer.py --export md     # Export to Markdown

Output saved to: ~/clawd/projects/execution-market/scripts/kk/data/
"""

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp_server"))

from swarm.coordinator import EMApiClient
from swarm.bootstrap import SwarmBootstrap
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


def header(text):
    print(f"\n{C.BOLD}{C.PURPLE}{'═' * 70}{C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}  {text}{C.RESET}")
    print(f"{C.BOLD}{C.PURPLE}{'═' * 70}{C.RESET}")


def subheader(text):
    print(f"\n{C.BOLD}{C.CYAN}  ── {text} ──{C.RESET}")


def metric(label, value, color=C.WHITE):
    print(f"  {C.DIM}{label}:{C.RESET} {color}{value}{C.RESET}")


def ok(text):
    print(f"  {C.GREEN}✓{C.RESET} {text}")


def warn(text):
    print(f"  {C.YELLOW}⚠{C.RESET} {text}")


def fail(text):
    print(f"  {C.RED}✗{C.RESET} {text}")


def bar(value, max_val, width=30, color=C.GREEN):
    """Render an ASCII progress bar."""
    if max_val == 0:
        return f"[{'░' * width}] 0%"
    pct = min(1.0, value / max_val)
    filled = int(pct * width)
    empty = width - filled
    return f"[{color}{'█' * filled}{C.DIM}{'░' * empty}{C.RESET}] {pct * 100:.0f}%"


# ─── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class TaskAnalysis:
    """Analysis of a single task."""

    task_id: str
    title: str
    status: str
    category: str
    bounty_usd: float
    created_at: str
    worker_wallet: str = ""
    evidence_types: list = field(default_factory=list)
    quality_rating: float = 0.0
    completion_hours: float = 0.0
    payment_network: str = "base"
    has_gps: bool = False
    evidence_count: int = 0


@dataclass
class WorkerProfile:
    """Analyzed worker profile."""

    wallet: str
    tasks_completed: int = 0
    categories_worked: list = field(default_factory=list)
    avg_rating: float = 0.0
    total_earned_usd: float = 0.0
    evidence_types_used: list = field(default_factory=list)
    first_task_at: str = ""
    last_task_at: str = ""
    specialization_score: float = 0.0  # 0=generalist, 1=specialist


@dataclass
class AnalysisReport:
    """Full production analysis report."""

    generated_at: str = ""
    em_api_healthy: bool = False

    # Task metrics
    total_tasks: int = 0
    tasks_by_status: dict = field(default_factory=dict)
    tasks_by_category: dict = field(default_factory=dict)
    tasks_by_network: dict = field(default_factory=dict)
    category_diversity_score: float = 0.0
    total_volume_usd: float = 0.0
    avg_bounty_usd: float = 0.0
    median_bounty_usd: float = 0.0

    # Worker metrics
    total_workers: int = 0
    worker_profiles: list = field(default_factory=list)
    avg_tasks_per_worker: float = 0.0
    specialization_index: float = 0.0

    # Evidence quality
    evidence_type_distribution: dict = field(default_factory=dict)
    avg_evidence_per_task: float = 0.0
    gps_evidence_pct: float = 0.0

    # Swarm readiness
    swarm_readiness: dict = field(default_factory=dict)
    routing_simulation: dict = field(default_factory=dict)

    # Time analysis
    tasks_by_day: dict = field(default_factory=dict)
    avg_completion_hours: float = 0.0
    busiest_day: str = ""

    def to_dict(self):
        return {
            "generated_at": self.generated_at,
            "em_api_healthy": self.em_api_healthy,
            "tasks": {
                "total": self.total_tasks,
                "by_status": self.tasks_by_status,
                "by_category": self.tasks_by_category,
                "by_network": self.tasks_by_network,
                "category_diversity": round(self.category_diversity_score, 3),
                "volume_usd": round(self.total_volume_usd, 2),
                "avg_bounty_usd": round(self.avg_bounty_usd, 2),
                "median_bounty_usd": round(self.median_bounty_usd, 2),
            },
            "workers": {
                "total": self.total_workers,
                "avg_tasks_per_worker": round(self.avg_tasks_per_worker, 1),
                "specialization_index": round(self.specialization_index, 3),
                "profiles": [
                    {
                        "wallet": p.wallet[:10] + "...",
                        "tasks_completed": p.tasks_completed,
                        "categories": p.categories_worked,
                        "avg_rating": round(p.avg_rating, 2),
                        "total_earned": round(p.total_earned_usd, 2),
                        "specialization": round(p.specialization_score, 3),
                    }
                    for p in self.worker_profiles
                ],
            },
            "evidence": {
                "type_distribution": self.evidence_type_distribution,
                "avg_per_task": round(self.avg_evidence_per_task, 1),
                "gps_pct": round(self.gps_evidence_pct, 1),
            },
            "swarm_readiness": self.swarm_readiness,
            "routing_simulation": self.routing_simulation,
            "timeline": {
                "by_day": self.tasks_by_day,
                "avg_completion_hours": round(self.avg_completion_hours, 1),
                "busiest_day": self.busiest_day,
            },
        }

    def to_markdown(self) -> str:
        """Generate a markdown report."""
        lines = [
            "# Execution Market Production Analysis",
            "",
            f"**Generated:** {self.generated_at}",
            f"**EM API:** {'✅ Healthy' if self.em_api_healthy else '❌ Unhealthy'}",
            "",
            "## Task Overview",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Tasks | {self.total_tasks} |",
            f"| Total Volume | ${self.total_volume_usd:.2f} |",
            f"| Avg Bounty | ${self.avg_bounty_usd:.2f} |",
            f"| Median Bounty | ${self.median_bounty_usd:.2f} |",
            f"| Category Diversity | {self.category_diversity_score:.3f} |",
            "",
            "### Tasks by Status",
            "",
        ]
        for status, count in sorted(self.tasks_by_status.items(), key=lambda x: -x[1]):
            lines.append(f"- **{status}**: {count}")

        lines.extend(
            [
                "",
                "### Tasks by Category",
                "",
            ]
        )
        for cat, count in sorted(self.tasks_by_category.items(), key=lambda x: -x[1]):
            lines.append(f"- **{cat}**: {count}")

        lines.extend(
            [
                "",
                "### Tasks by Network",
                "",
            ]
        )
        for net, count in sorted(self.tasks_by_network.items(), key=lambda x: -x[1]):
            lines.append(f"- **{net}**: {count}")

        lines.extend(
            [
                "",
                "## Worker Analysis",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Total Workers | {self.total_workers} |",
                f"| Avg Tasks/Worker | {self.avg_tasks_per_worker:.1f} |",
                f"| Specialization Index | {self.specialization_index:.3f} |",
                "",
                "### Top Workers",
                "",
            ]
        )
        for wp in self.worker_profiles[:10]:
            cats = ", ".join(wp.categories_worked[:3])
            lines.append(
                f"- `{wp.wallet[:10]}...` — {wp.tasks_completed} tasks, "
                f"${wp.total_earned_usd:.2f} earned, rating {wp.avg_rating:.1f}, "
                f"categories: {cats}"
            )

        lines.extend(
            [
                "",
                "## Evidence Quality",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Avg Evidence/Task | {self.avg_evidence_per_task:.1f} |",
                f"| GPS Evidence | {self.gps_evidence_pct:.1f}% |",
                "",
                "### Evidence Types",
                "",
            ]
        )
        for etype, count in sorted(
            self.evidence_type_distribution.items(), key=lambda x: -x[1]
        ):
            lines.append(f"- **{etype}**: {count}")

        lines.extend(
            [
                "",
                "## Swarm Readiness",
                "",
            ]
        )
        for check, result in self.swarm_readiness.items():
            status = "✅" if result.get("pass") else "⚠️" if result.get("warn") else "❌"
            lines.append(f"- {status} **{check}**: {result.get('message', '')}")

        if self.routing_simulation:
            lines.extend(
                [
                    "",
                    "## Routing Simulation",
                    "",
                    f"Simulated routing of {self.routing_simulation.get('tasks_simulated', 0)} tasks "
                    f"across {self.routing_simulation.get('agents_available', 0)} agents.",
                    "",
                    f"- **Assigned**: {self.routing_simulation.get('tasks_assigned', 0)}",
                    f"- **Unassigned**: {self.routing_simulation.get('tasks_unassigned', 0)}",
                    f"- **Avg Score**: {self.routing_simulation.get('avg_score', 0):.1f}",
                    f"- **Routing Time**: {self.routing_simulation.get('routing_ms', 0):.1f}ms",
                ]
            )

        lines.extend(
            [
                "",
                "---",
                "*Generated by KK V2 Production Analyzer*",
            ]
        )

        return "\n".join(lines)


# ─── Analyzer ─────────────────────────────────────────────────────────────────


class ProductionAnalyzer:
    """Analyzes live EM production data through the swarm intelligence lens."""

    def __init__(self, em_api_url: str = "https://api.execution.market"):
        self.client = EMApiClient(base_url=em_api_url)
        self.evidence_parser = EvidenceParser()
        self.worker_registry = WorkerRegistry()

    def _fetch_all_tasks(self, status: str, max_pages: int = 20) -> list:
        """Fetch all tasks for a given status with pagination."""
        all_tasks = []
        page = 0
        while page < max_pages:
            tasks = self.client.list_tasks(status=status, limit=100)
            if not tasks:
                break
            all_tasks.extend(tasks)
            # If we got fewer than 100, we've reached the end
            if len(tasks) < 100:
                break
            page += 1
            # The EM API doesn't have offset/cursor yet — so we get at most 100
            break  # Current API doesn't support pagination beyond limit
        return all_tasks

    def analyze(self, verbose: bool = True) -> AnalysisReport:
        """Run full production analysis."""
        report = AnalysisReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # 1. Check API health
        if verbose:
            header("EXECUTION MARKET — PRODUCTION ANALYSIS")
            subheader("API Health")

        health = self.client.get_health()
        report.em_api_healthy = health.get("status") == "healthy"
        if verbose:
            if report.em_api_healthy:
                components = health.get("components", {})
                for comp_name, comp_data in components.items():
                    status = comp_data.get("status", "unknown")
                    msg = comp_data.get("message", "")
                    if status == "healthy":
                        ok(f"{comp_name}: {msg}")
                    else:
                        warn(f"{comp_name}: {status} - {msg}")
            else:
                fail("EM API unhealthy")

        # 2. Fetch all tasks
        if verbose:
            subheader("Fetching Tasks")

        all_tasks = []
        valid_statuses = [
            "completed",
            "submitted",
            "published",
            "accepted",
            "in_progress",
            "verifying",
            "expired",
            "cancelled",
            "disputed",
        ]
        for status in valid_statuses:
            # Paginate — API limit is 100 per request
            page_tasks = self._fetch_all_tasks(status=status)
            all_tasks.extend(page_tasks)
            if verbose:
                metric(f"  {status}", len(page_tasks), C.GREEN if page_tasks else C.DIM)

        report.total_tasks = len(all_tasks)
        if verbose:
            ok(f"Total: {report.total_tasks} tasks")

        # 3. Analyze tasks
        if verbose:
            subheader("Task Analysis")

        self._analyze_tasks(all_tasks, report)

        if verbose:
            metric("Categories", len(report.tasks_by_category))
            metric("Networks", len(report.tasks_by_network))
            metric("Total volume", f"${report.total_volume_usd:.2f}", C.CYAN)
            metric("Avg bounty", f"${report.avg_bounty_usd:.2f}")
            metric(
                "Category diversity",
                f"{report.category_diversity_score:.3f}",
                C.GREEN if report.category_diversity_score > 0.5 else C.YELLOW,
            )

            # Show category distribution
            print(f"\n  {C.BOLD}Category Distribution:{C.RESET}")
            max_cat_count = (
                max(report.tasks_by_category.values())
                if report.tasks_by_category
                else 1
            )
            for cat, count in sorted(
                report.tasks_by_category.items(), key=lambda x: -x[1]
            )[:10]:
                pct = count / report.total_tasks * 100
                print(
                    f"    {cat:25s} {bar(count, max_cat_count, 25)} {count:4d} ({pct:.0f}%)"
                )

        # 4. Analyze workers
        if verbose:
            subheader("Worker Analysis")

        self._analyze_workers(all_tasks, report)

        if verbose:
            metric("Total workers", report.total_workers)
            metric("Avg tasks/worker", f"{report.avg_tasks_per_worker:.1f}")
            metric("Specialization index", f"{report.specialization_index:.3f}")

            print(f"\n  {C.BOLD}Top Workers:{C.RESET}")
            for i, wp in enumerate(report.worker_profiles[:5], 1):
                cats = ", ".join(wp.categories_worked[:3]) or "none"
                rating_str = f"★{wp.avg_rating:.1f}" if wp.avg_rating > 0 else "unrated"
                print(
                    f"    {i}. {C.CYAN}{wp.wallet[:10]}...{C.RESET} — "
                    f"{wp.tasks_completed} tasks, ${wp.total_earned_usd:.2f}, "
                    f"{rating_str}, [{cats}]"
                )

        # 5. Analyze evidence
        if verbose:
            subheader("Evidence Quality")

        self._analyze_evidence(all_tasks, report)

        if verbose:
            metric("Avg evidence/task", f"{report.avg_evidence_per_task:.1f}")
            metric("GPS evidence", f"{report.gps_evidence_pct:.1f}%")

            if report.evidence_type_distribution:
                print(f"\n  {C.BOLD}Evidence Types:{C.RESET}")
                max_ev = (
                    max(report.evidence_type_distribution.values())
                    if report.evidence_type_distribution
                    else 1
                )
                for etype, count in sorted(
                    report.evidence_type_distribution.items(), key=lambda x: -x[1]
                ):
                    print(
                        f"    {etype:20s} {bar(count, max_ev, 20, C.BLUE)} {count:4d}"
                    )

        # 6. Timeline analysis
        if verbose:
            subheader("Timeline")

        self._analyze_timeline(all_tasks, report)

        if verbose:
            metric("Avg completion time", f"{report.avg_completion_hours:.1f}h")
            metric("Busiest day", report.busiest_day)

        # 7. Swarm readiness assessment
        if verbose:
            subheader("Swarm Readiness")

        self._assess_swarm_readiness(report)

        if verbose:
            for check, result in report.swarm_readiness.items():
                if result.get("pass"):
                    ok(f"{check}: {result['message']}")
                elif result.get("warn"):
                    warn(f"{check}: {result['message']}")
                else:
                    fail(f"{check}: {result['message']}")

        # 8. Routing simulation
        if verbose:
            subheader("Routing Simulation")

        self._simulate_routing(all_tasks, report)

        if verbose:
            sim = report.routing_simulation
            metric("Tasks simulated", sim.get("tasks_simulated", 0))
            metric("Agents available", sim.get("agents_available", 0))
            metric("Tasks assigned", sim.get("tasks_assigned", 0), C.GREEN)
            metric(
                "Tasks unassigned",
                sim.get("tasks_unassigned", 0),
                C.RED if sim.get("tasks_unassigned", 0) > 0 else C.GREEN,
            )
            metric("Avg assignment score", f"{sim.get('avg_score', 0):.1f}")
            metric("Routing time", f"{sim.get('routing_ms', 0):.1f}ms")

        if verbose:
            print()

        return report

    def _analyze_tasks(self, tasks: list, report: AnalysisReport):
        """Analyze task distribution and diversity."""
        status_counts = Counter()
        category_counts = Counter()
        network_counts = Counter()
        bounties = []

        for task in tasks:
            status = task.get("status", "unknown")
            status_counts[status] += 1

            category = task.get("category", "uncategorized")
            category_counts[category] += 1

            network = task.get("payment_network", task.get("chain", "base"))
            network_counts[network] += 1

            bounty = float(task.get("bounty_amount", task.get("bounty_usd", 0)) or 0)
            bounties.append(bounty)

        report.tasks_by_status = dict(status_counts)
        report.tasks_by_category = dict(category_counts)
        report.tasks_by_network = dict(network_counts)

        if bounties:
            report.total_volume_usd = sum(bounties)
            report.avg_bounty_usd = sum(bounties) / len(bounties)
            sorted_bounties = sorted(bounties)
            mid = len(sorted_bounties) // 2
            report.median_bounty_usd = sorted_bounties[mid]

        # Category diversity: Shannon entropy normalized by log(n)
        if category_counts:
            import math

            total = sum(category_counts.values())
            entropy = 0.0
            for count in category_counts.values():
                p = count / total
                if p > 0:
                    entropy -= p * math.log2(p)
            max_entropy = (
                math.log2(len(category_counts)) if len(category_counts) > 1 else 1.0
            )
            report.category_diversity_score = (
                entropy / max_entropy if max_entropy > 0 else 0.0
            )

    def _analyze_workers(self, tasks: list, report: AnalysisReport):
        """Analyze worker behavior and specialization."""
        worker_data = defaultdict(
            lambda: {
                "tasks": 0,
                "categories": Counter(),
                "ratings": [],
                "earned": 0.0,
                "evidence_types": Counter(),
                "first": None,
                "last": None,
            }
        )

        for task in tasks:
            if task.get("status") not in ("completed", "submitted"):
                continue

            wallet = task.get("worker_wallet", task.get("worker_address", ""))
            if not wallet:
                continue

            data = worker_data[wallet]
            data["tasks"] += 1

            category = task.get("category", "uncategorized")
            data["categories"][category] += 1

            rating = task.get("quality_rating")
            if rating:
                data["ratings"].append(float(rating))

            bounty = float(task.get("bounty_amount", task.get("bounty_usd", 0)) or 0)
            data["earned"] += bounty

            created = task.get("created_at", "")
            if created:
                if data["first"] is None or created < data["first"]:
                    data["first"] = created
                if data["last"] is None or created > data["last"]:
                    data["last"] = created

            # Evidence types
            evidence = task.get("required_evidence", task.get("evidence_types", []))
            if isinstance(evidence, list):
                for etype in evidence:
                    if isinstance(etype, str):
                        data["evidence_types"][etype] += 1
                    elif isinstance(etype, dict):
                        data["evidence_types"][etype.get("type", "unknown")] += 1

        profiles = []
        for wallet, data in worker_data.items():
            categories = [cat for cat, _ in data["categories"].most_common()]
            avg_rating = (
                sum(data["ratings"]) / len(data["ratings"]) if data["ratings"] else 0.0
            )

            # Specialization: Herfindahl-Hirschman Index (0=diverse, 1=specialized)
            total = sum(data["categories"].values())
            hhi = (
                sum((c / total) ** 2 for c in data["categories"].values())
                if total > 0
                else 0.0
            )

            profiles.append(
                WorkerProfile(
                    wallet=wallet,
                    tasks_completed=data["tasks"],
                    categories_worked=categories,
                    avg_rating=avg_rating,
                    total_earned_usd=data["earned"],
                    evidence_types_used=list(data["evidence_types"].keys()),
                    first_task_at=data["first"] or "",
                    last_task_at=data["last"] or "",
                    specialization_score=hhi,
                )
            )

        profiles.sort(key=lambda p: p.tasks_completed, reverse=True)

        report.total_workers = len(profiles)
        report.worker_profiles = profiles
        report.avg_tasks_per_worker = (
            sum(p.tasks_completed for p in profiles) / len(profiles)
            if profiles
            else 0.0
        )
        report.specialization_index = (
            sum(p.specialization_score for p in profiles) / len(profiles)
            if profiles
            else 0.0
        )

    def _analyze_evidence(self, tasks: list, report: AnalysisReport):
        """Analyze evidence quality across tasks."""
        evidence_counts = Counter()
        tasks_with_evidence = 0
        total_evidence_items = 0
        gps_count = 0

        for task in tasks:
            evidence = task.get("required_evidence", task.get("evidence_types", []))
            if isinstance(evidence, list) and evidence:
                tasks_with_evidence += 1
                for item in evidence:
                    if isinstance(item, str):
                        evidence_counts[item] += 1
                        total_evidence_items += 1
                        if item in ("photo_geo", "gps_coordinates"):
                            gps_count += 1
                    elif isinstance(item, dict):
                        etype = item.get("type", "unknown")
                        evidence_counts[etype] += 1
                        total_evidence_items += 1
                        if etype in ("photo_geo", "gps_coordinates"):
                            gps_count += 1

        report.evidence_type_distribution = dict(evidence_counts)
        report.avg_evidence_per_task = (
            total_evidence_items / tasks_with_evidence if tasks_with_evidence else 0.0
        )
        report.gps_evidence_pct = (
            gps_count / total_evidence_items * 100 if total_evidence_items else 0.0
        )

    def _analyze_timeline(self, tasks: list, report: AnalysisReport):
        """Analyze task creation timeline."""
        day_counts = Counter()
        completion_hours = []

        for task in tasks:
            created = task.get("created_at", "")
            if created:
                try:
                    day = created[:10]  # YYYY-MM-DD
                    day_counts[day] += 1
                except (IndexError, TypeError):
                    pass

            # Estimate completion time
            if task.get("status") == "completed":
                created_at = task.get("created_at", "")
                completed_at = task.get("completed_at", task.get("updated_at", ""))
                if created_at and completed_at:
                    try:
                        c = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        d = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                        hours = (d - c).total_seconds() / 3600
                        if 0 < hours < 720:  # Ignore outliers > 30 days
                            completion_hours.append(hours)
                    except (ValueError, TypeError):
                        pass

        report.tasks_by_day = dict(sorted(day_counts.items()))
        report.avg_completion_hours = (
            sum(completion_hours) / len(completion_hours) if completion_hours else 0.0
        )
        report.busiest_day = day_counts.most_common(1)[0][0] if day_counts else ""

    def _assess_swarm_readiness(self, report: AnalysisReport):
        """Assess readiness for KK V2 Swarm operation."""
        checks = {}

        # Check 1: Task volume
        completed = report.tasks_by_status.get("completed", 0)
        if completed >= 100:
            checks["task_volume"] = {
                "pass": True,
                "message": f"{completed} completed tasks — strong signal",
            }
        elif completed >= 20:
            checks["task_volume"] = {
                "pass": True,
                "warn": True,
                "message": f"{completed} completed — growing",
            }
        else:
            checks["task_volume"] = {
                "pass": False,
                "message": f"Only {completed} completed — need more data",
            }

        # Check 2: Category diversity
        div = report.category_diversity_score
        num_cats = len(report.tasks_by_category)
        if div > 0.5 and num_cats >= 3:
            checks["category_diversity"] = {
                "pass": True,
                "message": f"Diversity {div:.2f} across {num_cats} categories",
            }
        elif num_cats >= 2:
            checks["category_diversity"] = {
                "pass": True,
                "warn": True,
                "message": f"Low diversity ({div:.2f}) — {num_cats} categories",
            }
        else:
            checks["category_diversity"] = {
                "pass": False,
                "message": f"Only {num_cats} category — need diversity for meaningful routing",
            }

        # Check 3: Worker pool
        if report.total_workers >= 10:
            checks["worker_pool"] = {
                "pass": True,
                "message": f"{report.total_workers} workers — healthy pool",
            }
        elif report.total_workers >= 3:
            checks["worker_pool"] = {
                "pass": True,
                "warn": True,
                "message": f"{report.total_workers} workers — growing",
            }
        else:
            checks["worker_pool"] = {
                "pass": False,
                "message": f"Only {report.total_workers} workers — need more",
            }

        # Check 4: Evidence quality
        if report.avg_evidence_per_task >= 1.5:
            checks["evidence_quality"] = {
                "pass": True,
                "message": f"Avg {report.avg_evidence_per_task:.1f} evidence items/task",
            }
        elif report.avg_evidence_per_task >= 0.5:
            checks["evidence_quality"] = {
                "pass": True,
                "warn": True,
                "message": f"Low evidence density ({report.avg_evidence_per_task:.1f}/task)",
            }
        else:
            checks["evidence_quality"] = {
                "pass": False,
                "message": "Insufficient evidence data",
            }

        # Check 5: Swarm modules
        try:
            from swarm.coordinator import SwarmCoordinator  # noqa: F401
            from swarm.orchestrator import SwarmOrchestrator  # noqa: F401
            from swarm.reputation_bridge import ReputationBridge  # noqa: F401
            from swarm.lifecycle_manager import LifecycleManager  # noqa: F401

            checks["swarm_modules"] = {
                "pass": True,
                "message": "All modules importable",
            }
        except ImportError as e:
            checks["swarm_modules"] = {"pass": False, "message": f"Import failed: {e}"}

        # Check 6: API connectivity
        if report.em_api_healthy:
            checks["api_connectivity"] = {"pass": True, "message": "EM API healthy"}
        else:
            checks["api_connectivity"] = {"pass": False, "message": "EM API unhealthy"}

        report.swarm_readiness = checks

    def _simulate_routing(self, tasks: list, report: AnalysisReport):
        """Simulate routing recent published/completed tasks through the swarm."""
        # Create coordinator with default agents
        bootstrap = SwarmBootstrap()
        coordinator, boot_result = bootstrap.create_coordinator(
            fetch_live=False,
            use_cached_profiles=False,
        )

        # Get recent tasks suitable for routing
        route_tasks = [
            t
            for t in tasks
            if t.get("status") in ("completed", "published", "submitted")
        ][:20]  # Limit to 20 for simulation

        # Ingest tasks
        for task in route_tasks:
            task_id = str(task.get("id", ""))
            if not task_id:
                continue

            category = task.get("category", "simple_action")
            categories = [category] if isinstance(category, str) else category
            bounty = float(task.get("bounty_amount", task.get("bounty_usd", 0)) or 0)

            coordinator.ingest_task(
                task_id=task_id,
                title=task.get("title", "Untitled"),
                categories=categories,
                bounty_usd=bounty,
                source="simulation",
            )

        # Route all
        start = time.monotonic()
        results = coordinator.process_task_queue(max_tasks=20)
        routing_ms = (time.monotonic() - start) * 1000

        assigned = sum(1 for r in results if hasattr(r, "agent_id"))
        scores = [r.score for r in results if hasattr(r, "score")]

        report.routing_simulation = {
            "tasks_simulated": len(route_tasks),
            "agents_available": boot_result.agents_registered,
            "tasks_assigned": assigned,
            "tasks_unassigned": len(route_tasks) - assigned,
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
            "routing_ms": round(routing_ms, 1),
        }


# ─── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="KK V2 Production Analyzer — Deep analysis of live EM data"
    )
    parser.add_argument("--summary", action="store_true", help="Quick summary only")
    parser.add_argument(
        "--export", choices=["json", "md", "both"], help="Export format"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress terminal output"
    )
    parser.add_argument(
        "--em-url", default="https://api.execution.market", help="EM API URL"
    )

    args = parser.parse_args()

    analyzer = ProductionAnalyzer(em_api_url=args.em_url)
    report = analyzer.analyze(verbose=not args.quiet)

    # Export
    if args.export:
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")

        if args.export in ("json", "both"):
            json_path = data_dir / f"analysis_{timestamp}.json"
            json_path.write_text(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
            )
            print(f"\n  {C.GREEN}✓{C.RESET} JSON exported: {json_path}")

        if args.export in ("md", "both"):
            md_path = data_dir / f"analysis_{timestamp}.md"
            md_path.write_text(report.to_markdown())
            print(f"\n  {C.GREEN}✓{C.RESET} Markdown exported: {md_path}")

    # Print summary line
    if not args.quiet:
        header("SUMMARY")
        total_checks = len(report.swarm_readiness)
        passed = sum(1 for r in report.swarm_readiness.values() if r.get("pass"))
        color = (
            C.GREEN
            if passed == total_checks
            else C.YELLOW
            if passed > total_checks / 2
            else C.RED
        )
        print(f"  {color}{passed}/{total_checks} readiness checks passed{C.RESET}")
        print(
            f"  {report.total_tasks} tasks | {report.total_workers} workers | "
            f"${report.total_volume_usd:.2f} volume | "
            f"{len(report.tasks_by_category)} categories"
        )
        print()


if __name__ == "__main__":
    main()
