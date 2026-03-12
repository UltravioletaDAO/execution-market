"""
SwarmCoordinator — Top-level operational controller for the KK V2 agent swarm.

This is the keystone module that integrates all swarm components into a unified
operational system. It manages the full task lifecycle:

    EM API → Task Ingestion → Agent Routing → Monitoring → Completion → Reputation Feedback

Components orchestrated:
    - ReputationBridge: Score computation from on-chain + internal data
    - LifecycleManager: Agent state machine + budget + health
    - SwarmOrchestrator: Task routing with strategy selection
    - AutoJobClient: External enrichment from AutoJob intelligence
    - EMApiClient: Live connection to Execution Market production API

Usage:
    coordinator = SwarmCoordinator.create(
        em_api_url="https://api.execution.market",
        autojob_url="http://localhost:8765",
    )

    # Bootstrap the swarm from ERC-8004 registry
    await coordinator.bootstrap_from_registry()

    # Run the coordination loop
    coordinator.process_task_queue()
    coordinator.run_health_checks()

    # Get operational dashboard
    dashboard = coordinator.get_dashboard()
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

from .reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
    CompositeScore,
    ReputationTier,
)
from .lifecycle_manager import (
    LifecycleManager,
    AgentState,
    AgentRecord,
    BudgetConfig,
    LifecycleError,
    BudgetExceededError,
)
from .orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    TaskPriority,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
)
from .autojob_client import (
    AutoJobClient,
    EnrichedOrchestrator,
    AutoJobEnrichment,
)

logger = logging.getLogger("em.swarm.coordinator")


# ─── EM API Client ────────────────────────────────────────────────────────────

class EMApiClient:
    """
    Lightweight HTTP client for the Execution Market production API.

    Stdlib-only (no requests/httpx). Used by the SwarmCoordinator to:
    - Fetch available tasks
    - Submit task applications
    - Report task completion with evidence
    - Query agent identities from ERC-8004 registry
    """

    def __init__(
        self,
        base_url: str = "https://api.execution.market",
        api_key: Optional[str] = None,
        timeout_seconds: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout_seconds

    def _request(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        """Make an HTTP request to the EM API."""
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = json.dumps(data).encode("utf-8") if data else None
        req = Request(url, data=body, headers=headers, method=method)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"EM API error {e.code} on {method} {path}: {error_body}")
            return {"error": True, "status": e.code, "detail": error_body}
        except (URLError, TimeoutError) as e:
            logger.error(f"EM API unreachable ({method} {path}): {e}")
            return {"error": True, "detail": str(e)}

    def get_health(self) -> dict:
        """Check EM API health status."""
        return self._request("GET", "/health")

    def list_tasks(
        self,
        status: str = "published",
        limit: int = 50,
        category: Optional[str] = None,
    ) -> list[dict]:
        """Fetch tasks from the EM API."""
        params = f"?status={status}&limit={limit}"
        if category:
            params += f"&category={category}"
        result = self._request("GET", f"/api/v1/tasks{params}")
        if isinstance(result, dict) and result.get("error"):
            return []
        # API returns {"tasks": [...]} or just a list
        if isinstance(result, list):
            return result
        return result.get("tasks", result.get("data", []))

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a single task by ID."""
        result = self._request("GET", f"/api/v1/tasks/{task_id}")
        if isinstance(result, dict) and result.get("error"):
            return None
        return result

    def apply_to_task(self, task_id: str, agent_id: int, message: str = "") -> dict:
        """Submit an application for a task."""
        return self._request("POST", f"/api/v1/tasks/{task_id}/apply", {
            "agent_id": agent_id,
            "message": message,
        })

    def submit_evidence(
        self,
        task_id: str,
        evidence_type: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """Submit task completion evidence."""
        payload = {
            "evidence_type": evidence_type,
            "content": content,
        }
        if metadata:
            payload["metadata"] = metadata
        return self._request("POST", f"/api/v1/tasks/{task_id}/evidence", payload)

    def get_agent_identity(self, agent_id: int) -> Optional[dict]:
        """Look up an agent's ERC-8004 identity."""
        result = self._request("GET", f"/api/v1/agents/{agent_id}")
        if isinstance(result, dict) and result.get("error"):
            return None
        return result

    def get_task_stats(self) -> dict:
        """Get aggregate task statistics."""
        return self._request("GET", "/api/v1/tasks/stats")


# ─── Coordination Events ──────────────────────────────────────────────────────

class CoordinatorEvent(str, Enum):
    """Events emitted by the coordinator for monitoring/hooks."""
    TASK_INGESTED = "task_ingested"
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_EXPIRED = "task_expired"
    AGENT_REGISTERED = "agent_registered"
    AGENT_DEGRADED = "agent_degraded"
    AGENT_RECOVERED = "agent_recovered"
    AGENT_SUSPENDED = "agent_suspended"
    BUDGET_WARNING = "budget_warning"
    HEALTH_CHECK = "health_check"
    ROUTING_FAILURE = "routing_failure"
    AUTOJOB_ENRICHED = "autojob_enriched"


@dataclass
class EventRecord:
    """A recorded coordinator event."""
    event: CoordinatorEvent
    timestamp: datetime
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event": self.event.value,
            "timestamp": self.timestamp.isoformat(),
            **self.data,
        }


# ─── Task Queue ───────────────────────────────────────────────────────────────

@dataclass
class QueuedTask:
    """A task in the coordinator's processing queue."""
    task_id: str
    title: str
    categories: list[str]
    bounty_usd: float
    priority: TaskPriority = TaskPriority.NORMAL
    source: str = "api"  # api, manual, autojob
    raw_data: dict = field(default_factory=dict)
    ingested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempts: int = 0
    max_attempts: int = 3
    last_attempt_at: Optional[datetime] = None
    assigned_agent_id: Optional[int] = None
    status: str = "pending"  # pending, assigned, completed, failed, expired

    def to_task_request(self) -> TaskRequest:
        """Convert to a TaskRequest for the orchestrator."""
        return TaskRequest(
            task_id=self.task_id,
            title=self.title,
            categories=self.categories,
            bounty_usd=self.bounty_usd,
            priority=self.priority,
        )


# ─── Operational Metrics ──────────────────────────────────────────────────────

@dataclass
class SwarmMetrics:
    """Aggregated operational metrics for the swarm."""
    # Task metrics
    tasks_ingested: int = 0
    tasks_assigned: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_expired: int = 0
    total_bounty_earned_usd: float = 0.0
    avg_assignment_time_ms: float = 0.0

    # Agent metrics
    agents_registered: int = 0
    agents_active: int = 0
    agents_degraded: int = 0
    agents_suspended: int = 0

    # Performance
    avg_routing_time_ms: float = 0.0
    routing_success_rate: float = 0.0
    autojob_enrichment_rate: float = 0.0

    # Budget
    total_daily_spend_usd: float = 0.0
    total_monthly_spend_usd: float = 0.0

    # Timing
    last_task_ingested_at: Optional[str] = None
    last_task_completed_at: Optional[str] = None
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tasks": {
                "ingested": self.tasks_ingested,
                "assigned": self.tasks_assigned,
                "completed": self.tasks_completed,
                "failed": self.tasks_failed,
                "expired": self.tasks_expired,
                "bounty_earned_usd": round(self.total_bounty_earned_usd, 2),
                "avg_assignment_time_ms": round(self.avg_assignment_time_ms, 1),
            },
            "agents": {
                "registered": self.agents_registered,
                "active": self.agents_active,
                "degraded": self.agents_degraded,
                "suspended": self.agents_suspended,
            },
            "performance": {
                "avg_routing_time_ms": round(self.avg_routing_time_ms, 1),
                "routing_success_rate": round(self.routing_success_rate, 3),
                "autojob_enrichment_rate": round(self.autojob_enrichment_rate, 3),
            },
            "budget": {
                "daily_spend_usd": round(self.total_daily_spend_usd, 2),
                "monthly_spend_usd": round(self.total_monthly_spend_usd, 2),
            },
            "timing": {
                "last_task_ingested": self.last_task_ingested_at,
                "last_task_completed": self.last_task_completed_at,
                "uptime_seconds": round(self.uptime_seconds, 0),
            },
        }


# ─── SwarmCoordinator ─────────────────────────────────────────────────────────

class SwarmCoordinator:
    """
    Top-level operational controller for the KK V2 agent swarm.

    Integrates all components into a unified system that can:
    1. Ingest tasks from the EM API or manual submission
    2. Route tasks using reputation + AutoJob enrichment
    3. Monitor agent health and budget across the swarm
    4. Track task lifecycle from ingestion to completion
    5. Provide operational dashboards and metrics
    6. Emit events for external monitoring systems

    Thread-safety: NOT thread-safe. Use from a single event loop or
    add locking for concurrent access.
    """

    def __init__(
        self,
        bridge: ReputationBridge,
        lifecycle: LifecycleManager,
        orchestrator: SwarmOrchestrator,
        em_client: Optional[EMApiClient] = None,
        autojob_client: Optional[AutoJobClient] = None,
        enriched_orchestrator: Optional[EnrichedOrchestrator] = None,
        default_strategy: RoutingStrategy = RoutingStrategy.BEST_FIT,
        task_expiry_hours: float = 24.0,
        health_check_interval_seconds: int = 300,
    ):
        # Core components
        self.bridge = bridge
        self.lifecycle = lifecycle
        self.orchestrator = orchestrator
        self.em_client = em_client
        self.autojob = autojob_client
        self.enriched = enriched_orchestrator
        self.default_strategy = default_strategy

        # Configuration
        self.task_expiry_hours = task_expiry_hours
        self.health_check_interval = health_check_interval_seconds

        # Task queue
        self._task_queue: dict[str, QueuedTask] = {}
        self._completed_tasks: list[QueuedTask] = []

        # Events
        self._events: list[EventRecord] = []
        self._event_hooks: dict[CoordinatorEvent, list[Callable]] = {}

        # Metrics tracking
        self._routing_times: list[float] = []
        self._assignment_times: list[float] = []
        self._started_at = datetime.now(timezone.utc)
        self._last_health_check: Optional[datetime] = None
        self._last_api_poll: Optional[datetime] = None

        # Counters
        self._total_ingested = 0
        self._total_assigned = 0
        self._total_completed = 0
        self._total_failed = 0
        self._total_expired = 0
        self._total_bounty_earned = 0.0
        self._autojob_enrichments = 0
        self._routing_attempts = 0
        self._routing_successes = 0

    @classmethod
    def create(
        cls,
        em_api_url: str = "https://api.execution.market",
        em_api_key: Optional[str] = None,
        autojob_url: str = "http://localhost:8765",
        default_strategy: RoutingStrategy = RoutingStrategy.BEST_FIT,
        **kwargs,
    ) -> "SwarmCoordinator":
        """Factory method: create a fully-wired SwarmCoordinator."""
        bridge = ReputationBridge()
        lifecycle = LifecycleManager()
        orchestrator = SwarmOrchestrator(bridge, lifecycle, default_strategy=default_strategy)

        em_client = EMApiClient(base_url=em_api_url, api_key=em_api_key)
        autojob_client = AutoJobClient(base_url=autojob_url)
        enriched = EnrichedOrchestrator(orchestrator, autojob_client)

        return cls(
            bridge=bridge,
            lifecycle=lifecycle,
            orchestrator=orchestrator,
            em_client=em_client,
            autojob_client=autojob_client,
            enriched_orchestrator=enriched,
            default_strategy=default_strategy,
            **kwargs,
        )

    # ─── Agent Registration ───────────────────────────────────────────────

    def register_agent(
        self,
        agent_id: int,
        name: str,
        wallet_address: str,
        personality: str = "explorer",
        budget_config: Optional[BudgetConfig] = None,
        on_chain: Optional[OnChainReputation] = None,
        internal: Optional[InternalReputation] = None,
        tags: Optional[list[str]] = None,
        activate: bool = True,
    ) -> AgentRecord:
        """
        Register an agent with all swarm subsystems.

        This is the single entry point for adding an agent. It handles:
        1. Lifecycle registration (state machine + budget)
        2. Reputation registration (on-chain + internal)
        3. Initial state transition to IDLE/ACTIVE

        Args:
            agent_id: ERC-8004 identity ID
            name: Human-readable name
            wallet_address: Ethereum wallet address
            personality: Agent personality type
            budget_config: Budget limits (uses defaults if None)
            on_chain: Pre-loaded on-chain reputation data
            internal: Pre-loaded internal reputation data
            tags: Classification tags
            activate: Whether to transition to ACTIVE immediately

        Returns:
            The registered AgentRecord
        """
        # Register with lifecycle manager
        record = self.lifecycle.register_agent(
            agent_id=agent_id,
            name=name,
            wallet_address=wallet_address,
            personality=personality,
            budget_config=budget_config,
            tags=tags,
        )

        # Register reputation data
        on_chain = on_chain or OnChainReputation(
            agent_id=agent_id,
            wallet_address=wallet_address,
        )
        internal = internal or InternalReputation(agent_id=agent_id)

        self.orchestrator.register_reputation(
            agent_id=agent_id,
            on_chain=on_chain,
            internal=internal,
        )

        # Transition to IDLE, then optionally ACTIVE
        self.lifecycle.transition(agent_id, AgentState.IDLE, "coordinator registration")
        if activate:
            self.lifecycle.transition(agent_id, AgentState.ACTIVE, "auto-activated")

        self._emit(CoordinatorEvent.AGENT_REGISTERED, {
            "agent_id": agent_id,
            "name": name,
            "wallet": wallet_address[:10] + "...",
        })

        return record

    def register_agents_batch(
        self,
        agents: list[dict],
        activate: bool = True,
    ) -> list[AgentRecord]:
        """
        Register multiple agents at once.

        Each dict should have: agent_id, name, wallet_address
        Optional: personality, budget_config, on_chain, internal, tags
        """
        records = []
        for agent_data in agents:
            try:
                record = self.register_agent(
                    activate=activate,
                    **agent_data,
                )
                records.append(record)
            except LifecycleError as e:
                logger.warning(f"Failed to register agent {agent_data.get('agent_id')}: {e}")
        return records

    # ─── Task Ingestion ───────────────────────────────────────────────────

    def ingest_task(
        self,
        task_id: str,
        title: str,
        categories: list[str],
        bounty_usd: float = 0.0,
        priority: TaskPriority = TaskPriority.NORMAL,
        source: str = "manual",
        raw_data: Optional[dict] = None,
    ) -> QueuedTask:
        """
        Add a task to the coordination queue.

        Tasks are not immediately routed — they enter the queue and
        are processed by process_task_queue().
        """
        if task_id in self._task_queue:
            existing = self._task_queue[task_id]
            if existing.status not in ("failed", "expired"):
                logger.info(f"Task {task_id} already in queue (status={existing.status})")
                return existing

        queued = QueuedTask(
            task_id=task_id,
            title=title,
            categories=categories,
            bounty_usd=bounty_usd,
            priority=priority,
            source=source,
            raw_data=raw_data or {},
        )

        self._task_queue[task_id] = queued
        self._total_ingested += 1

        self._emit(CoordinatorEvent.TASK_INGESTED, {
            "task_id": task_id,
            "title": title,
            "categories": categories,
            "bounty_usd": bounty_usd,
            "source": source,
        })

        return queued

    def ingest_from_api(
        self,
        status: str = "published",
        limit: int = 50,
        category: Optional[str] = None,
        auto_priority: bool = True,
    ) -> list[QueuedTask]:
        """
        Pull tasks from the live EM API and add them to the queue.

        Automatically maps EM task format to QueuedTask.
        Skips tasks already in the queue.
        """
        if self.em_client is None:
            logger.warning("No EM API client configured")
            return []

        tasks = self.em_client.list_tasks(status=status, limit=limit, category=category)
        ingested = []

        for task_data in tasks:
            task_id = str(task_data.get("id", task_data.get("task_id", "")))
            if not task_id or task_id in self._task_queue:
                continue

            # Map EM task to queued task
            title = task_data.get("title", "Untitled")
            categories = []
            if task_data.get("category"):
                categories = [task_data["category"]]
            elif task_data.get("categories"):
                categories = task_data["categories"]

            bounty = float(task_data.get("bounty_usd", task_data.get("bounty", 0)))

            # Auto-priority based on bounty
            priority = TaskPriority.NORMAL
            if auto_priority:
                if bounty >= 50:
                    priority = TaskPriority.HIGH
                elif bounty >= 100:
                    priority = TaskPriority.CRITICAL

            queued = self.ingest_task(
                task_id=task_id,
                title=title,
                categories=categories,
                bounty_usd=bounty,
                priority=priority,
                source="api",
                raw_data=task_data,
            )
            ingested.append(queued)

        self._last_api_poll = datetime.now(timezone.utc)
        return ingested

    # ─── Task Routing & Processing ────────────────────────────────────────

    def process_task_queue(
        self,
        strategy: Optional[RoutingStrategy] = None,
        max_tasks: int = 10,
    ) -> list[Assignment | RoutingFailure]:
        """
        Process pending tasks in the queue by routing them to agents.

        Returns a list of Assignment or RoutingFailure results.
        """
        strategy = strategy or self.default_strategy
        results = []

        # Get pending tasks sorted by priority then age
        pending = [
            t for t in self._task_queue.values()
            if t.status == "pending" and t.attempts < t.max_attempts
        ]
        pending.sort(
            key=lambda t: (
                -{"critical": 3, "high": 2, "normal": 1, "low": 0}.get(t.priority.value, 0),
                t.ingested_at,
            )
        )

        for task in pending[:max_tasks]:
            task.attempts += 1
            task.last_attempt_at = datetime.now(timezone.utc)

            start_time = time.monotonic()
            request = task.to_task_request()

            # Use enriched orchestrator if available, otherwise standard
            if self.enriched and self.autojob and self.autojob.is_available():
                result = self.enriched.route_task(request, strategy=strategy)
                self._autojob_enrichments += 1
                self._emit(CoordinatorEvent.AUTOJOB_ENRICHED, {
                    "task_id": task.task_id,
                })
            else:
                result = self.orchestrator.route_task(request, strategy=strategy)

            elapsed_ms = (time.monotonic() - start_time) * 1000
            self._routing_times.append(elapsed_ms)
            self._routing_attempts += 1

            if isinstance(result, Assignment):
                task.status = "assigned"
                task.assigned_agent_id = result.agent_id
                self._total_assigned += 1
                self._routing_successes += 1
                self._assignment_times.append(elapsed_ms)

                self._emit(CoordinatorEvent.TASK_ASSIGNED, {
                    "task_id": task.task_id,
                    "agent_id": result.agent_id,
                    "agent_name": result.agent_name,
                    "score": round(result.score, 2),
                    "strategy": result.strategy_used.value,
                    "routing_ms": round(elapsed_ms, 1),
                })
            else:
                if task.attempts >= task.max_attempts:
                    task.status = "failed"
                    self._total_failed += 1
                    self._emit(CoordinatorEvent.ROUTING_FAILURE, {
                        "task_id": task.task_id,
                        "reason": result.reason,
                        "attempts": task.attempts,
                    })

            results.append(result)

        return results

    def complete_task(
        self,
        task_id: str,
        bounty_earned_usd: Optional[float] = None,
    ) -> bool:
        """
        Mark a task as completed. Updates all subsystems.

        Returns True if successfully completed.
        """
        task = self._task_queue.get(task_id)
        if task is None:
            logger.warning(f"Task {task_id} not in queue")
            return False

        # Complete in orchestrator (handles lifecycle transition)
        agent_id = self.orchestrator.complete_task(task_id)
        if agent_id is None:
            logger.warning(f"Task {task_id} not claimed in orchestrator")
            return False

        # Update queue status
        task.status = "completed"
        self._total_completed += 1

        # Track earnings
        bounty = bounty_earned_usd or task.bounty_usd
        self._total_bounty_earned += bounty

        # Record spend against agent budget
        if bounty > 0:
            try:
                self.lifecycle.record_spend(agent_id, bounty * 0.0)  # Agent cost, not bounty
            except BudgetExceededError:
                pass

        # Update internal reputation (successful completion)
        if agent_id in self.orchestrator._internal:
            internal = self.orchestrator._internal[agent_id]
            internal.total_tasks += 1
            internal.successful_tasks += 1
            internal.consecutive_failures = 0
            for cat in task.categories:
                current = internal.category_scores.get(cat, 0)
                internal.category_scores[cat] = min(100, current + 5)  # Reward

        # Move to completed list
        self._completed_tasks.append(task)

        self._emit(CoordinatorEvent.TASK_COMPLETED, {
            "task_id": task_id,
            "agent_id": agent_id,
            "bounty_usd": bounty,
        })

        return True

    def fail_task(self, task_id: str, error: str = "") -> bool:
        """
        Mark a task as failed. Updates reputation and lifecycle.
        """
        task = self._task_queue.get(task_id)
        if task is None:
            return False

        agent_id = self.orchestrator.fail_task(task_id, error)
        if agent_id is not None:
            self._emit(CoordinatorEvent.TASK_FAILED, {
                "task_id": task_id,
                "agent_id": agent_id,
                "error": error,
            })

        task.status = "failed"
        self._total_failed += 1
        return True

    # ─── Health & Monitoring ──────────────────────────────────────────────

    def run_health_checks(self) -> dict:
        """
        Run health checks across all subsystems.

        Checks:
        1. Agent heartbeats (degradation detection)
        2. Cooldown expiry (auto-transition back to IDLE)
        3. Budget warnings
        4. Task expiry
        5. EM API connectivity
        6. AutoJob availability

        Returns a health summary dict.
        """
        now = datetime.now(timezone.utc)
        report = {
            "timestamp": now.isoformat(),
            "agents": {"checked": 0, "healthy": 0, "degraded": 0, "recovered": 0},
            "tasks": {"expired": 0, "stale": 0},
            "systems": {},
        }

        # 1. Check agent heartbeats and cooldowns
        for agent_id, record in list(self.lifecycle.agents.items()):
            report["agents"]["checked"] += 1

            # Check cooldown expiry
            if record.state == AgentState.COOLDOWN:
                if self.lifecycle.check_cooldown_expiry(agent_id):
                    report["agents"]["recovered"] += 1
                    self._emit(CoordinatorEvent.AGENT_RECOVERED, {"agent_id": agent_id})

            # Check heartbeat health
            was_healthy = record.health.is_healthy
            is_healthy = self.lifecycle.check_heartbeat(agent_id)

            if is_healthy:
                report["agents"]["healthy"] += 1
            else:
                report["agents"]["degraded"] += 1
                if was_healthy:
                    self._emit(CoordinatorEvent.AGENT_DEGRADED, {"agent_id": agent_id})

            # Check budget warnings
            try:
                budget = self.lifecycle.get_budget_status(agent_id)
                if budget["at_warning"] and not budget["at_limit"]:
                    self._emit(CoordinatorEvent.BUDGET_WARNING, {
                        "agent_id": agent_id,
                        "daily_pct": budget["daily_pct"],
                        "monthly_pct": budget["monthly_pct"],
                    })
            except LifecycleError:
                pass

        # 2. Check task expiry
        expiry_cutoff = now - timedelta(hours=self.task_expiry_hours)
        for task_id, task in list(self._task_queue.items()):
            if task.status == "pending" and task.ingested_at < expiry_cutoff:
                task.status = "expired"
                self._total_expired += 1
                report["tasks"]["expired"] += 1
                self._emit(CoordinatorEvent.TASK_EXPIRED, {"task_id": task_id})

            elif task.status == "assigned":
                # Check for stale assignments (assigned but not progressing)
                assigned_hours = (now - (task.last_attempt_at or task.ingested_at)).total_seconds() / 3600
                if assigned_hours > self.task_expiry_hours:
                    report["tasks"]["stale"] += 1

        # 3. Check EM API
        if self.em_client:
            try:
                health = self.em_client.get_health()
                report["systems"]["em_api"] = health.get("status", "unknown")
            except Exception:
                report["systems"]["em_api"] = "unreachable"

        # 4. Check AutoJob
        if self.autojob:
            report["systems"]["autojob"] = "available" if self.autojob.is_available() else "unavailable"

        self._last_health_check = now
        self._emit(CoordinatorEvent.HEALTH_CHECK, report)

        return report

    # ─── Metrics & Dashboard ──────────────────────────────────────────────

    def get_metrics(self) -> SwarmMetrics:
        """Compute current operational metrics."""
        now = datetime.now(timezone.utc)
        swarm_status = self.lifecycle.get_swarm_status()

        metrics = SwarmMetrics(
            tasks_ingested=self._total_ingested,
            tasks_assigned=self._total_assigned,
            tasks_completed=self._total_completed,
            tasks_failed=self._total_failed,
            tasks_expired=self._total_expired,
            total_bounty_earned_usd=self._total_bounty_earned,
            agents_registered=swarm_status["total_agents"],
            agents_active=swarm_status["available_count"],
            agents_degraded=len(swarm_status.get("degraded_agents", [])),
            agents_suspended=len(swarm_status.get("suspended_agents", [])),
            total_daily_spend_usd=swarm_status.get("total_daily_spend", 0),
            total_monthly_spend_usd=swarm_status.get("total_monthly_spend", 0),
            uptime_seconds=(now - self._started_at).total_seconds(),
        )

        # Compute averages
        if self._routing_times:
            metrics.avg_routing_time_ms = sum(self._routing_times) / len(self._routing_times)
        if self._assignment_times:
            metrics.avg_assignment_time_ms = sum(self._assignment_times) / len(self._assignment_times)
        if self._routing_attempts > 0:
            metrics.routing_success_rate = self._routing_successes / self._routing_attempts
        if self._routing_attempts > 0:
            metrics.autojob_enrichment_rate = self._autojob_enrichments / self._routing_attempts

        return metrics

    def get_dashboard(self) -> dict:
        """
        Get a comprehensive operational dashboard.

        Returns a dict suitable for rendering in a monitoring UI:
        - Metrics summary
        - Queue status
        - Agent fleet status
        - Recent events
        - System health
        """
        metrics = self.get_metrics()
        swarm_status = self.lifecycle.get_swarm_status()

        # Queue breakdown
        queue_status = {"pending": 0, "assigned": 0, "completed": 0, "failed": 0, "expired": 0}
        for task in self._task_queue.values():
            queue_status[task.status] = queue_status.get(task.status, 0) + 1

        # Per-agent status
        agent_fleet = []
        for agent_id, record in self.lifecycle.agents.items():
            budget = self.lifecycle.get_budget_status(agent_id)
            agent_fleet.append({
                "agent_id": agent_id,
                "name": record.name,
                "state": record.state.value,
                "personality": record.personality,
                "current_task": record.current_task_id,
                "budget_daily_pct": budget["daily_pct"],
                "budget_monthly_pct": budget["monthly_pct"],
                "health": "healthy" if record.health.is_healthy else "degraded",
                "tags": record.tags,
            })

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics.to_dict(),
            "queue": queue_status,
            "fleet": agent_fleet,
            "swarm": swarm_status,
            "recent_events": [e.to_dict() for e in self._events[-20:]],
            "systems": {
                "em_api": "configured" if self.em_client else "not configured",
                "autojob": "configured" if self.autojob else "not configured",
                "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
                "last_api_poll": self._last_api_poll.isoformat() if self._last_api_poll else None,
            },
        }

    # ─── Event System ─────────────────────────────────────────────────────

    def on_event(self, event: CoordinatorEvent, callback: Callable) -> None:
        """Register a callback for a coordinator event."""
        if event not in self._event_hooks:
            self._event_hooks[event] = []
        self._event_hooks[event].append(callback)

    def _emit(self, event: CoordinatorEvent, data: dict = None) -> None:
        """Emit an event and call registered hooks."""
        record = EventRecord(
            event=event,
            timestamp=datetime.now(timezone.utc),
            data=data or {},
        )
        self._events.append(record)

        # Keep events bounded (last 1000)
        if len(self._events) > 1000:
            self._events = self._events[-500:]

        # Call hooks
        for callback in self._event_hooks.get(event, []):
            try:
                callback(record)
            except Exception as e:
                logger.error(f"Event hook error for {event.value}: {e}")

    def get_events(
        self,
        event_type: Optional[CoordinatorEvent] = None,
        limit: int = 50,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        """Query event history with optional filters."""
        events = self._events
        if event_type:
            events = [e for e in events if e.event == event_type]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return [e.to_dict() for e in events[-limit:]]

    # ─── Utility ──────────────────────────────────────────────────────────

    def get_queue_summary(self) -> dict:
        """Quick summary of the task queue."""
        by_status = {}
        by_category = {}
        total_bounty = 0.0

        for task in self._task_queue.values():
            by_status[task.status] = by_status.get(task.status, 0) + 1
            for cat in task.categories:
                by_category[cat] = by_category.get(cat, 0) + 1
            if task.status in ("pending", "assigned"):
                total_bounty += task.bounty_usd

        return {
            "total": len(self._task_queue),
            "by_status": by_status,
            "by_category": by_category,
            "pending_bounty_usd": round(total_bounty, 2),
        }

    def cleanup_completed(self, older_than_hours: float = 24.0) -> int:
        """Remove completed/failed/expired tasks older than threshold."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        to_remove = [
            tid for tid, task in self._task_queue.items()
            if task.status in ("completed", "failed", "expired")
            and task.ingested_at < cutoff
        ]
        for tid in to_remove:
            del self._task_queue[tid]
        return len(to_remove)

    def reset_metrics(self) -> None:
        """Reset all runtime metrics (useful for testing)."""
        self._routing_times.clear()
        self._assignment_times.clear()
        self._total_ingested = 0
        self._total_assigned = 0
        self._total_completed = 0
        self._total_failed = 0
        self._total_expired = 0
        self._total_bounty_earned = 0.0
        self._autojob_enrichments = 0
        self._routing_attempts = 0
        self._routing_successes = 0
        self._events.clear()
        self._started_at = datetime.now(timezone.utc)
