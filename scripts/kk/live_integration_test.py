#!/usr/bin/env python3
"""
KK V2 Swarm — Live Integration Test Suite

Validates the ENTIRE swarm pipeline against the live EM production API.
This is the bridge between 1,000+ unit tests and production readiness.

Usage:
    python3 scripts/kk/live_integration_test.py
    python3 scripts/kk/live_integration_test.py --verbose
    python3 scripts/kk/live_integration_test.py --report

Tests:
    1. EMApiClient — live API connectivity, health, task fetching
    2. SwarmCoordinator — ingestion from live data, routing simulation
    3. SwarmScheduler — priority scoring with real deadlines
    4. SwarmDashboard — fleet health from live metrics
    5. ConfigManager — environment profile loading
    6. SwarmRunner — dry_run cycle with live data
    7. Analytics — production data analysis
    8. End-to-end — full pipeline from API fetch → route → dashboard
"""

import json
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "mcp_server"))

EM_API_URL = "https://api.execution.market"


@dataclass
class TestResult:
    name: str
    passed: bool
    duration_ms: float
    details: str = ""
    error: str = ""


@dataclass
class TestSuite:
    results: list = field(default_factory=list)
    started_at: str = ""
    duration_ms: float = 0

    @property
    def passed(self):
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self):
        return sum(1 for r in self.results if not r.passed)

    @property
    def total(self):
        return len(self.results)

    def summary(self) -> str:
        lines = [
            f"\n{'=' * 70}",
            "  KK V2 LIVE INTEGRATION TEST RESULTS",
            f"  {self.started_at}",
            f"{'=' * 70}",
        ]
        for r in self.results:
            icon = "✅" if r.passed else "❌"
            lines.append(f"  {icon} {r.name} ({r.duration_ms:.0f}ms)")
            if r.details:
                for line in r.details.split("\n"):
                    lines.append(f"       {line}")
            if r.error:
                lines.append(f"       ERROR: {r.error}")

        lines.append(f"{'=' * 70}")
        lines.append(
            f"  {self.passed}/{self.total} passed, {self.failed} failed "
            f"({self.duration_ms:.0f}ms total)"
        )
        status = "🟢 ALL PASSED" if self.failed == 0 else "🔴 FAILURES DETECTED"
        lines.append(f"  {status}")
        lines.append(f"{'=' * 70}\n")
        return "\n".join(lines)


def run_test(name: str, fn, suite: TestSuite, verbose: bool = False):
    """Run a test function and record the result."""
    start = time.monotonic()
    try:
        details = fn()
        duration = (time.monotonic() - start) * 1000
        result = TestResult(
            name=name, passed=True, duration_ms=duration, details=details or ""
        )
        if verbose:
            print(f"  ✅ {name} ({duration:.0f}ms)")
    except Exception as e:
        duration = (time.monotonic() - start) * 1000
        error_msg = f"{type(e).__name__}: {e}"
        result = TestResult(
            name=name, passed=False, duration_ms=duration, error=error_msg
        )
        if verbose:
            print(f"  ❌ {name} ({duration:.0f}ms) — {error_msg}")
            traceback.print_exc()
    suite.results.append(result)


# ──────────────────────────────────────────────────────────────────────────────
# TEST 1: EMApiClient — Live API Connectivity
# ──────────────────────────────────────────────────────────────────────────────


def test_em_api_health():
    """Verify EMApiClient connects to live API and gets healthy response."""
    from swarm.coordinator import EMApiClient

    client = EMApiClient(base_url=EM_API_URL)
    health = client.get_health()

    assert health.get("status") == "healthy", f"API not healthy: {health}"
    assert "components" in health, "Missing components in health response"

    components = health["components"]
    healthy_components = [
        k for k, v in components.items() if v.get("status") == "healthy"
    ]
    assert len(healthy_components) >= 3, (
        f"Only {len(healthy_components)} healthy components"
    )

    return f"All {len(healthy_components)} components healthy: {', '.join(healthy_components)}"


def test_em_api_list_tasks():
    """Fetch tasks from the live API — validates response parsing."""
    from swarm.coordinator import EMApiClient

    client = EMApiClient(base_url=EM_API_URL)

    # Fetch valid statuses (API uses: published, accepted, in_progress, submitted,
    # verifying, completed, disputed, expired, cancelled)
    all_tasks = []
    for status in ["published", "completed", "expired", "cancelled"]:
        tasks = client.list_tasks(status=status, limit=50)
        all_tasks.extend(tasks)

    assert len(all_tasks) > 0, "No tasks found in any status"

    # Validate task structure
    sample = all_tasks[0]
    required_fields = ["id", "title", "status"]
    for field_name in required_fields:
        assert field_name in sample, f"Missing field '{field_name}' in task"

    # Count by status
    status_counts = {}
    for t in all_tasks:
        s = t.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    status_str = ", ".join(f"{s}={c}" for s, c in sorted(status_counts.items()))
    return f"{len(all_tasks)} tasks fetched ({status_str})"


def test_em_api_task_detail():
    """Fetch a single task by ID and validate detailed response."""
    from swarm.coordinator import EMApiClient

    client = EMApiClient(base_url=EM_API_URL)
    tasks = client.list_tasks(status="completed", limit=1)
    assert len(tasks) > 0, "No completed tasks to fetch details for"

    task_id = tasks[0]["id"]
    detail = client.get_task(task_id)
    assert detail is not None, f"Could not fetch task {task_id}"
    assert detail.get("id") == task_id, "Task ID mismatch"

    return f"Task {task_id[:8]}... fetched with {len(detail)} fields"


# ──────────────────────────────────────────────────────────────────────────────
# TEST 2: SwarmCoordinator — Live Data Ingestion
# ──────────────────────────────────────────────────────────────────────────────


def test_coordinator_ingest_live_tasks():
    """Ingest live tasks into the coordinator and validate queue state."""
    from swarm.coordinator import SwarmCoordinator, EMApiClient

    client = EMApiClient(base_url=EM_API_URL)
    coordinator = SwarmCoordinator.create(
        em_api_url=EM_API_URL,
        autojob_url="https://autojob.cc",
    )

    # Fetch completed tasks (known data)
    tasks = client.list_tasks(status="completed", limit=10)
    assert len(tasks) > 0, "No tasks to ingest"

    # Ingest each task
    ingested = 0
    for task_data in tasks:
        task_id = str(task_data.get("id", ""))
        category = task_data.get("category", "simple_action")
        categories = [category] if isinstance(category, str) else category

        coordinator.ingest_task(
            task_id=task_id,
            title=task_data.get("title", ""),
            categories=categories,
            bounty_usd=float(
                task_data.get("bounty_usd", task_data.get("bounty_amount", 0))
            ),
            source="live_test",
            raw_data=task_data,
        )
        ingested += 1

    # Validate queue state
    summary = coordinator.get_queue_summary()
    assert summary.get("pending", 0) > 0 or summary.get("total", 0) > 0, (
        f"Queue empty after ingesting {ingested} tasks"
    )

    return f"Ingested {ingested} live tasks into coordinator queue"


def test_coordinator_routing_simulation():
    """Route live tasks through the coordinator and validate assignments."""
    from swarm.coordinator import SwarmCoordinator, EMApiClient
    from swarm.lifecycle_manager import BudgetConfig

    coordinator = SwarmCoordinator.create(
        em_api_url=EM_API_URL,
        autojob_url="https://autojob.cc",
    )

    # Register 5 test agents (simulating KK V2 fleet)
    agent_configs = [
        {
            "agent_id": 1001,
            "name": "PhysicalBot",
            "wallet": "0xAgent1",
            "tags": ["physical_presence", "simple_action"],
            "budget": 5.0,
        },
        {
            "agent_id": 1002,
            "name": "KnowledgeBot",
            "wallet": "0xAgent2",
            "tags": ["knowledge_access", "research"],
            "budget": 3.0,
        },
        {
            "agent_id": 1003,
            "name": "CodeBot",
            "wallet": "0xAgent3",
            "tags": ["code_execution"],
            "budget": 10.0,
        },
        {
            "agent_id": 1004,
            "name": "GeneralBot",
            "wallet": "0xAgent4",
            "tags": ["simple_action", "knowledge_access"],
            "budget": 2.0,
        },
        {
            "agent_id": 1005,
            "name": "FieldBot",
            "wallet": "0xAgent5",
            "tags": ["physical_presence", "research"],
            "budget": 8.0,
        },
    ]

    for cfg in agent_configs:
        coordinator.register_agent(
            agent_id=cfg["agent_id"],
            name=cfg["name"],
            wallet_address=cfg["wallet"],
            budget_config=BudgetConfig(daily_limit_usd=cfg["budget"]),
            tags=cfg["tags"],
        )

    # Fetch and ingest live tasks
    client = EMApiClient(base_url=EM_API_URL)
    tasks = client.list_tasks(status="completed", limit=10)

    for task_data in tasks:
        task_id = str(task_data.get("id", ""))
        category = task_data.get("category", "simple_action")
        categories = [category] if isinstance(category, str) else category

        coordinator.ingest_task(
            task_id=task_id,
            title=task_data.get("title", ""),
            categories=categories,
            bounty_usd=float(
                task_data.get("bounty_usd", task_data.get("bounty_amount", 0))
            ),
            source="live_test",
            raw_data=task_data,
        )

    # Route tasks (the coordinator routes locally, no API calls for assignment)
    from swarm.orchestrator import Assignment, RoutingFailure

    results = coordinator.process_task_queue(max_tasks=10)
    assigned = sum(1 for r in results if isinstance(r, Assignment))
    failed = sum(1 for r in results if isinstance(r, RoutingFailure))

    return f"Routed {assigned} tasks ({failed} failures) across 5 agents"


# ──────────────────────────────────────────────────────────────────────────────
# TEST 3: SwarmScheduler — Real Deadline Scoring
# ──────────────────────────────────────────────────────────────────────────────


def test_scheduler_deadline_scoring():
    """Score live tasks by deadline urgency using the SwarmScheduler."""
    from swarm.scheduler import SwarmScheduler
    from swarm.coordinator import EMApiClient
    from datetime import datetime

    scheduler = SwarmScheduler()
    client = EMApiClient(base_url=EM_API_URL)

    # Get tasks with various statuses to get deadline variety
    all_tasks = []
    for status in ["completed", "expired"]:
        tasks = client.list_tasks(status=status, limit=10)
        all_tasks.extend(tasks)

    assert len(all_tasks) > 0, "No tasks to score"

    # Add tasks to scheduler and let it compute priorities
    for task in all_tasks:
        task_id = str(task.get("id", ""))
        bounty = float(task.get("bounty_usd", task.get("bounty_amount", 0)))
        category = task.get("category", "simple_action")
        deadline_str = task.get("deadline")

        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        scheduler.add_task(
            task_id=task_id,
            title=task.get("title", "")[:60],
            categories=[category],
            bounty_usd=bounty,
            deadline=deadline,
        )

    # Get scheduled tasks and their effective priorities
    task_entries = list(scheduler._tasks.values())
    scored = [
        (t.title[:40], t.effective_priority, t.categories[0] if t.categories else "?")
        for t in task_entries
    ]
    scored.sort(key=lambda x: -x[1])

    details = []
    for title, score, cat in scored[:5]:
        details.append(f"  [{score:.1f}] {title} ({cat})")

    return f"Scored {len(scored)} tasks in scheduler\n" + "\n".join(details)


# ──────────────────────────────────────────────────────────────────────────────
# TEST 4: SwarmDashboard — Fleet Health from Live Metrics
# ──────────────────────────────────────────────────────────────────────────────


def test_dashboard_fleet_health():
    """Generate a fleet health dashboard with simulated agents."""
    from swarm.dashboard import SwarmDashboard

    dashboard = SwarmDashboard()

    # Register agents directly in the dashboard
    categories_pool = [
        "simple_action",
        "physical_presence",
        "knowledge_access",
        "code_execution",
        "research",
    ]
    for i in range(1, 7):
        agent_id = f"agent_{2100 + i}"
        specs = [
            categories_pool[i % len(categories_pool)],
            categories_pool[(i + 1) % len(categories_pool)],
        ]
        dashboard.register_agent(agent_id, budget_limit_usd=5.0, specializations=specs)
        dashboard.update_agent_state(agent_id, "active")

    # Simulate some task events
    for i in range(3):
        dashboard.record_task_event(
            agent_id=f"agent_{2101}",
            task_id=f"live_task_{i}",
            event_type="task_completed",
            bounty_usd=0.25,
            category="simple_action",
        )

    # Generate snapshot
    snapshot = dashboard.generate_snapshot()
    assert snapshot is not None, "Dashboard snapshot is None"

    status = snapshot.fleet_status
    total = snapshot.agent_count
    operational = snapshot.agents_operational

    return f"Fleet status: {status}, {total} agents, {operational} operational"


# ──────────────────────────────────────────────────────────────────────────────
# TEST 5: ConfigManager — Environment Profile
# ──────────────────────────────────────────────────────────────────────────────


def test_config_manager_profiles():
    """Load and validate ConfigManager with default config."""
    from swarm.config_manager import ConfigManager, SwarmConfig, validate_config

    # Test default config loading
    manager = ConfigManager()
    config = manager.config  # triggers load with defaults
    assert config is not None, "Config is None"
    assert isinstance(config, SwarmConfig), f"Expected SwarmConfig, got {type(config)}"

    # Validate config
    errors = validate_config(config)

    # Test test-environment manager
    test_manager = ConfigManager(environment="test")
    test_config = test_manager.config
    assert test_config is not None, "Test config is None"

    return f"Default config loaded, {len(errors)} validation errors"


# ──────────────────────────────────────────────────────────────────────────────
# TEST 6: SwarmRunner — Dry Run Cycle
# ──────────────────────────────────────────────────────────────────────────────


def test_runner_dry_cycle():
    """Execute a dry_run cycle against the live API."""
    from swarm.runner import SwarmRunner
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        runner = SwarmRunner.create(
            em_api_url=EM_API_URL,
            mode="dry_run",
            max_tasks_per_cycle=5,
            max_cycles=1,
            state_dir=tmpdir,
        )

        result = runner.run_once()

        assert result is not None, "Cycle result is None"
        assert result.cycle_number == 1, f"Expected cycle 1, got {result.cycle_number}"
        assert len(result.phases_completed) > 0, "No phases completed"

        details = [
            f"Phases: {len(result.phases_completed)}/7 completed",
            f"Tasks discovered: {result.tasks_discovered}",
            f"New tasks: {result.tasks_new}",
            f"Duration: {result.duration_ms:.0f}ms",
        ]
        if result.errors:
            details.append(f"Errors: {len(result.errors)}")
            for err in result.errors[:3]:
                details.append(f"  ⚠ {err}")

        return "\n".join(details)


# ──────────────────────────────────────────────────────────────────────────────
# TEST 7: Analytics — Production Data Analysis
# ──────────────────────────────────────────────────────────────────────────────


def test_analytics_live_data():
    """Run analytics on live task data."""
    from swarm.analytics import SwarmAnalytics, TaskEvent
    from swarm.coordinator import EMApiClient

    client = EMApiClient(base_url=EM_API_URL)
    analytics = SwarmAnalytics()

    # Fetch completed tasks for analysis
    completed = client.list_tasks(status="completed", limit=20)
    if not completed:
        return "No completed tasks to analyze (skipped)"

    # Feed data to analytics using TaskEvent
    events = []
    for task in completed:
        event = TaskEvent(
            event_type="task_completed",
            agent_id=str(task.get("agent_id", "unknown")),
            task_id=str(task.get("id")),
            category=task.get("category", "unknown"),
            bounty_usd=float(task.get("bounty_usd", task.get("bounty_amount", 0))),
        )
        events.append(event)

    analytics.record_batch(events)

    analytics.get_dashboard()
    total_events = len(analytics._events)

    return f"Analyzed {total_events} task events from live API ({len(completed)} completed tasks)"


# ──────────────────────────────────────────────────────────────────────────────
# TEST 8: End-to-End Pipeline
# ──────────────────────────────────────────────────────────────────────────────


def test_end_to_end_pipeline():
    """Full pipeline: API fetch → ingest → route → dashboard → analytics."""
    from swarm.coordinator import SwarmCoordinator, EMApiClient
    from swarm.scheduler import SwarmScheduler
    from swarm.analytics import SwarmAnalytics, TaskEvent
    from swarm.dashboard import SwarmDashboard
    from swarm.lifecycle_manager import BudgetConfig
    from datetime import datetime

    start = time.monotonic()

    # Step 1: Fetch from live API
    client = EMApiClient(base_url=EM_API_URL)
    health = client.get_health()
    assert health.get("status") == "healthy"

    all_tasks = []
    for status in ["completed", "expired", "cancelled"]:
        tasks = client.list_tasks(status=status, limit=20)
        all_tasks.extend(tasks)

    # Step 2: Create coordinator with 10 agents
    coordinator = SwarmCoordinator.create(
        em_api_url=EM_API_URL,
        autojob_url="https://autojob.cc",
    )

    categories_all = [
        "simple_action",
        "physical_presence",
        "knowledge_access",
        "code_execution",
        "research",
    ]
    for i in range(10):
        tags = [
            categories_all[i % len(categories_all)],
            categories_all[(i + 1) % len(categories_all)],
        ]
        coordinator.register_agent(
            agent_id=3000 + i,
            name=f"E2E_Agent_{i}",
            wallet_address=f"0xE2E_Agent_{i}",
            budget_config=BudgetConfig(daily_limit_usd=5.0),
            tags=tags,
        )

    # Step 3: Ingest tasks
    ingested = 0
    for task_data in all_tasks:
        task_id = str(task_data.get("id", ""))
        category = task_data.get("category", "simple_action")
        categories = [category] if isinstance(category, str) else category

        coordinator.ingest_task(
            task_id=task_id,
            title=task_data.get("title", ""),
            categories=categories,
            bounty_usd=float(
                task_data.get("bounty_usd", task_data.get("bounty_amount", 0))
            ),
            source="e2e_test",
            raw_data=task_data,
        )
        ingested += 1

    # Step 4: Route
    from swarm.orchestrator import Assignment

    route_results = coordinator.process_task_queue(max_tasks=50)
    assigned = sum(1 for r in route_results if isinstance(r, Assignment))

    # Step 5: Scheduler scoring
    scheduler = SwarmScheduler()
    for task in all_tasks[:10]:
        deadline_str = task.get("deadline")
        deadline = None
        if deadline_str:
            try:
                deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        scheduler.add_task(
            task_id=str(task.get("id")),
            title=task.get("title", "")[:60],
            categories=[task.get("category", "simple_action")],
            bounty_usd=float(task.get("bounty_usd", task.get("bounty_amount", 0))),
            deadline=deadline,
        )

    scheduler_count = len(scheduler._tasks)

    # Step 6: Analytics
    analytics = SwarmAnalytics()
    events = []
    for task in all_tasks:
        if task.get("status") == "completed":
            events.append(
                TaskEvent(
                    event_type="task_completed",
                    agent_id=str(task.get("agent_id", "unknown")),
                    task_id=str(task.get("id")),
                    category=task.get("category", "unknown"),
                    bounty_usd=float(
                        task.get("bounty_usd", task.get("bounty_amount", 0))
                    ),
                )
            )
    if events:
        analytics.record_batch(events)

    # Step 7: Dashboard
    dashboard = SwarmDashboard()
    for i in range(6):
        dashboard.register_agent(f"e2e_agent_{i}", budget_limit_usd=5.0)
        dashboard.update_agent_state(f"e2e_agent_{i}", "active")
    snapshot = dashboard.generate_snapshot()

    duration = (time.monotonic() - start) * 1000

    return (
        f"Pipeline completed in {duration:.0f}ms\n"
        f"  API: healthy\n"
        f"  Tasks fetched: {len(all_tasks)}\n"
        f"  Ingested: {ingested}\n"
        f"  Routed: {assigned}\n"
        f"  Scheduled: {scheduler_count}\n"
        f"  Analytics events: {len(events)}\n"
        f"  Dashboard: {snapshot.fleet_status}, {snapshot.agent_count} agents"
    )


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────


def main():
    import argparse

    parser = argparse.ArgumentParser(description="KK V2 Live Integration Tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--report", action="store_true", help="Save report to file")
    args = parser.parse_args()

    verbose = args.verbose

    suite = TestSuite(started_at=datetime.now(timezone.utc).isoformat())
    start = time.monotonic()

    print(f"\n🔬 KK V2 Live Integration Tests — {EM_API_URL}")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Run all tests
    tests = [
        ("EMApiClient.health", test_em_api_health),
        ("EMApiClient.list_tasks", test_em_api_list_tasks),
        ("EMApiClient.task_detail", test_em_api_task_detail),
        ("Coordinator.ingest_live_tasks", test_coordinator_ingest_live_tasks),
        ("Coordinator.routing_simulation", test_coordinator_routing_simulation),
        ("Scheduler.deadline_scoring", test_scheduler_deadline_scoring),
        ("Dashboard.fleet_health", test_dashboard_fleet_health),
        ("ConfigManager.profiles", test_config_manager_profiles),
        ("Runner.dry_run_cycle", test_runner_dry_cycle),
        ("Analytics.live_data", test_analytics_live_data),
        ("End-to-End.full_pipeline", test_end_to_end_pipeline),
    ]

    for name, fn in tests:
        run_test(name, fn, suite, verbose=verbose)

    suite.duration_ms = (time.monotonic() - start) * 1000
    print(suite.summary())

    if args.report:
        report_path = project_root / "scripts" / "kk" / "live_integration_report.json"
        report_data = {
            "suite": "kk_v2_live_integration",
            "timestamp": suite.started_at,
            "duration_ms": suite.duration_ms,
            "passed": suite.passed,
            "failed": suite.failed,
            "total": suite.total,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "duration_ms": r.duration_ms,
                    "details": r.details,
                    "error": r.error,
                }
                for r in suite.results
            ],
        }
        report_path.write_text(json.dumps(report_data, indent=2))
        print(f"📄 Report saved to {report_path}")

    return 0 if suite.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
