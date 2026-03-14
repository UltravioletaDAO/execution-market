"""
Swarm Bootstrap — Initialize the coordinator from production data.

Connects three data sources to create a production-ready SwarmCoordinator:
1. ERC-8004 registered agents (on-chain identity)
2. Historical task completions (behavioral evidence)
3. Worker Skill DNA profiles (from production_profiler)

This is the bridge between cold-start and intelligent routing.

Usage:
    from swarm.bootstrap import SwarmBootstrap

    bootstrap = SwarmBootstrap()
    coordinator = bootstrap.create_coordinator()  # Full pipeline
    
    # Or step by step:
    bootstrap.fetch_agents()          # Get ERC-8004 agents
    bootstrap.fetch_history()         # Get completed tasks
    bootstrap.build_profiles()        # Build Skill DNA
    coordinator = bootstrap.wire()    # Create coordinator with all data
"""

import json
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

from .coordinator import SwarmCoordinator, EMApiClient
from .reputation_bridge import (
    ReputationBridge,
    OnChainReputation,
    InternalReputation,
    ReputationTier,
)
from .lifecycle_manager import LifecycleManager, BudgetConfig
from .orchestrator import SwarmOrchestrator, RoutingStrategy
from .autojob_client import AutoJobClient, EnrichedOrchestrator

logger = logging.getLogger("em.swarm.bootstrap")


# ─── Agent Registry ──────────────────────────────────────────────────────────

# Known ERC-8004 agents registered on Base (agent IDs 2101-2124)
# These were registered during the KK V2 Swarm buildout.
KNOWN_AGENTS = [
    {"agent_id": 2101, "name": "Aurora", "personality": "explorer",
     "tags": ["general", "verification", "photo"]},
    {"agent_id": 2102, "name": "Nova", "personality": "strategist",
     "tags": ["coding", "technical", "blockchain"]},
    {"agent_id": 2103, "name": "Pulse", "personality": "executor",
     "tags": ["delivery", "physical", "logistics"]},
    {"agent_id": 2104, "name": "Zenith", "personality": "analyst",
     "tags": ["research", "analysis", "data"]},
    {"agent_id": 2105, "name": "Cascade", "personality": "specialist",
     "tags": ["blockchain", "defi", "crypto"]},
    {"agent_id": 2106, "name": "UltraVioleta", "personality": "orchestrator",
     "tags": ["general", "simple_action", "multichain"]},
    {"agent_id": 2107, "name": "Drift", "personality": "explorer",
     "tags": ["creative", "design", "content"]},
    {"agent_id": 2108, "name": "Ember", "personality": "executor",
     "tags": ["verification", "geo", "physical"]},
    {"agent_id": 2109, "name": "Flux", "personality": "strategist",
     "tags": ["coding", "technical", "api"]},
    {"agent_id": 2110, "name": "Haze", "personality": "analyst",
     "tags": ["research", "data", "analysis"]},
    {"agent_id": 2111, "name": "Ion", "personality": "specialist",
     "tags": ["blockchain", "smart_contracts", "audit"]},
    {"agent_id": 2112, "name": "Jade", "personality": "executor",
     "tags": ["delivery", "logistics", "physical"]},
    {"agent_id": 2113, "name": "Kite", "personality": "explorer",
     "tags": ["creative", "writing", "content"]},
    {"agent_id": 2114, "name": "Luma", "personality": "analyst",
     "tags": ["verification", "photo", "quality"]},
    {"agent_id": 2115, "name": "Mist", "personality": "executor",
     "tags": ["general", "simple_action", "support"]},
    {"agent_id": 2116, "name": "Neon", "personality": "specialist",
     "tags": ["coding", "frontend", "ui"]},
    {"agent_id": 2117, "name": "Opal", "personality": "strategist",
     "tags": ["research", "market", "competitive"]},
    {"agent_id": 2118, "name": "Prism", "personality": "explorer",
     "tags": ["blockchain", "defi", "yield"]},
    {"agent_id": 2119, "name": "Quasar", "personality": "executor",
     "tags": ["verification", "document", "notarization"]},
    {"agent_id": 2120, "name": "Reed", "personality": "analyst",
     "tags": ["data", "metrics", "reporting"]},
    {"agent_id": 2121, "name": "Storm", "personality": "specialist",
     "tags": ["coding", "backend", "infrastructure"]},
    {"agent_id": 2122, "name": "Tidal", "personality": "executor",
     "tags": ["delivery", "errand", "physical"]},
    {"agent_id": 2123, "name": "Umbra", "personality": "strategist",
     "tags": ["creative", "design", "branding"]},
    {"agent_id": 2124, "name": "Vortex", "personality": "explorer",
     "tags": ["general", "multichain", "coordination"]},
]

# Common wallet pattern for test agents
AGENT_WALLET_PREFIX = "0x"


@dataclass
class BootstrapResult:
    """Result of the bootstrap process."""
    agents_registered: int
    tasks_ingested: int
    profiles_built: int
    chains_active: list[str]
    total_bounty_usd: float
    bootstrap_ms: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agents_registered": self.agents_registered,
            "tasks_ingested": self.tasks_ingested,
            "profiles_built": self.profiles_built,
            "chains_active": self.chains_active,
            "total_bounty_usd": round(self.total_bounty_usd, 2),
            "bootstrap_ms": round(self.bootstrap_ms, 1),
            "warnings": self.warnings,
        }


class SwarmBootstrap:
    """
    Initializes the SwarmCoordinator from production data.
    
    Handles the cold-start problem by:
    1. Loading known ERC-8004 agents
    2. Fetching historical task data
    3. Computing reputation from evidence
    4. Wiring everything into a ready-to-use coordinator
    """

    def __init__(
        self,
        em_api_url: str = "https://api.execution.market",
        em_api_key: Optional[str] = None,
        autojob_url: str = "http://localhost:8765",
        profiles_path: Optional[str] = None,
        default_strategy: RoutingStrategy = RoutingStrategy.BEST_FIT,
    ):
        self.em_api_url = em_api_url
        self.em_api_key = em_api_key
        self.autojob_url = autojob_url
        self.profiles_path = profiles_path or os.path.expanduser("~/.em-production-profiles.json")
        self.default_strategy = default_strategy

        # Data stores
        self._agents: list[dict] = []
        self._completed_tasks: list[dict] = []
        self._profiles: dict = {}
        self._chain_analytics: dict = {}

        # Computed reputation
        self._on_chain_reps: dict[int, OnChainReputation] = {}
        self._internal_reps: dict[int, InternalReputation] = {}

    def create_coordinator(
        self,
        fetch_live: bool = True,
        use_cached_profiles: bool = True,
    ) -> tuple[SwarmCoordinator, BootstrapResult]:
        """
        Full bootstrap pipeline. Returns (coordinator, result).

        Args:
            fetch_live: If True, fetch latest data from EM API
            use_cached_profiles: If True, load profiles from disk if available
        """
        start = time.monotonic()
        warnings = []

        # Step 1: Load agent definitions
        self._agents = list(KNOWN_AGENTS)
        logger.info(f"Loaded {len(self._agents)} known agents")

        # Step 2: Load or fetch profiles
        if use_cached_profiles and os.path.exists(self.profiles_path):
            self._load_cached_profiles()
            logger.info(f"Loaded {len(self._profiles)} cached profiles")
        elif fetch_live:
            self._fetch_history()
            self._build_profiles_from_history()
        else:
            warnings.append("No profile data available — using defaults")

        # Step 3: Build reputation data
        self._build_reputation_data()

        # Step 4: Wire the coordinator
        coordinator = self._wire_coordinator()

        # Step 5: Register agents
        agents_registered = self._register_agents(coordinator)

        elapsed_ms = (time.monotonic() - start) * 1000

        # Compute result
        chains = set()
        total_bounty = 0.0
        for task in self._completed_tasks:
            chains.add(task.get("payment_network", "unknown"))
            total_bounty += float(task.get("bounty_usd", 0) or 0)

        result = BootstrapResult(
            agents_registered=agents_registered,
            tasks_ingested=len(self._completed_tasks),
            profiles_built=len(self._profiles),
            chains_active=sorted(chains) if chains else ["base"],
            total_bounty_usd=total_bounty,
            bootstrap_ms=elapsed_ms,
            warnings=warnings,
        )

        logger.info(
            f"Bootstrap complete: {agents_registered} agents, "
            f"{len(self._completed_tasks)} tasks, {elapsed_ms:.0f}ms"
        )

        return coordinator, result

    def _load_cached_profiles(self) -> None:
        """Load previously exported profiles from disk."""
        try:
            with open(self.profiles_path) as f:
                data = json.load(f)
            self._profiles = data.get("profiles", {})
            self._chain_analytics = data.get("chain_analytics", {})
            # Reconstruct task count from summary
            summary = data.get("summary", {})
            if summary.get("total_tasks"):
                # Create placeholder tasks for count tracking
                self._completed_tasks = [{}] * summary["total_tasks"]
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load cached profiles: {e}")

    def _fetch_history(self) -> None:
        """Fetch completed tasks from live EM API."""
        client = EMApiClient(base_url=self.em_api_url, api_key=self.em_api_key)
        
        all_tasks = []
        offset = 0
        limit = 50
        
        while True:
            result = client._request(
                "GET",
                f"/api/v1/tasks?status=completed&limit={limit}&offset={offset}",
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
            
            if len(tasks) < limit:
                break
        
        self._completed_tasks = all_tasks
        logger.info(f"Fetched {len(all_tasks)} completed tasks from EM API")

    def _build_profiles_from_history(self) -> None:
        """Build executor profiles from task history."""
        from collections import Counter, defaultdict

        executor_tasks = defaultdict(list)
        for task in self._completed_tasks:
            executor_id = task.get("executor_id", "")
            if executor_id:
                executor_tasks[executor_id].append(task)

        for executor_id, tasks in executor_tasks.items():
            chains = Counter()
            categories = Counter()
            total_bounty = 0.0

            for task in tasks:
                chains[task.get("payment_network", "unknown")] += 1
                categories[task.get("category", "unknown")] += 1
                total_bounty += float(task.get("bounty_usd", 0) or 0)

            self._profiles[executor_id] = {
                "executor_id": executor_id,
                "total_tasks": len(tasks),
                "total_earned_usd": round(total_bounty, 2),
                "chains": dict(chains.most_common()),
                "categories": dict(categories.most_common()),
                "skill_dna": {
                    "primary_category": categories.most_common(1)[0][0] if categories else "unknown",
                    "primary_chain": chains.most_common(1)[0][0] if chains else "unknown",
                    "multi_chain": len(chains) > 1,
                    "experience_level": (
                        "expert" if len(tasks) >= 100 else
                        "advanced" if len(tasks) >= 50 else
                        "intermediate" if len(tasks) >= 20 else
                        "beginner"
                    ),
                },
            }

    def _build_reputation_data(self) -> None:
        """Build on-chain and internal reputation from profiles."""
        # For each known agent, build reputation data
        for agent_def in self._agents:
            agent_id = agent_def["agent_id"]
            wallet = f"0x{agent_id:040x}"

            # On-chain reputation: based on whether they're registered
            on_chain = OnChainReputation(
                agent_id=agent_id,
                wallet_address=wallet,
                total_seals=0,
                positive_seals=0,
                chains_active=["base"],  # All registered on Base
                registered_at=datetime(2026, 2, 21, tzinfo=timezone.utc),
            )

            # Internal reputation: start neutral, enhance from profiles
            internal = InternalReputation(
                agent_id=agent_id,
                bayesian_score=0.5,
            )

            # If this agent has profile data (e.g., agent 2106 is the main operator)
            if agent_id == 2106 and self._profiles:
                # Agent 2106 is the platform operator — has task history
                total_tasks = len(self._completed_tasks)
                internal.total_tasks = total_tasks
                internal.successful_tasks = total_tasks  # All completed = all successful
                internal.avg_rating = 5.0
                internal.bayesian_score = 0.95
                internal.avg_completion_time_hours = 1.0

                # Set chain diversity from production data
                chains = set()
                for task in self._completed_tasks:
                    chain = task.get("payment_network")
                    if chain:
                        chains.add(chain)
                on_chain.chains_active = sorted(chains)
                on_chain.total_seals = total_tasks
                on_chain.positive_seals = total_tasks

                # Category scores from production data
                for profile in self._profiles.values():
                    for cat, count in profile.get("categories", {}).items():
                        score = min(100, count * 2)  # 2 points per task
                        internal.category_scores[cat] = score

            # Give agents tagged with relevant skills some base category scores
            for tag in agent_def.get("tags", []):
                if tag not in internal.category_scores:
                    internal.category_scores[tag] = 30  # Base competence

            self._on_chain_reps[agent_id] = on_chain
            self._internal_reps[agent_id] = internal

    def _wire_coordinator(self) -> SwarmCoordinator:
        """Create and wire all coordinator components."""
        bridge = ReputationBridge()
        lifecycle = LifecycleManager()
        orchestrator = SwarmOrchestrator(
            bridge=bridge,
            lifecycle=lifecycle,
            default_strategy=self.default_strategy,
        )

        em_client = EMApiClient(
            base_url=self.em_api_url,
            api_key=self.em_api_key,
        )

        autojob_client = AutoJobClient(base_url=self.autojob_url)
        enriched = None
        if autojob_client.is_available():
            enriched = EnrichedOrchestrator(orchestrator, autojob_client)

        coordinator = SwarmCoordinator(
            bridge=bridge,
            lifecycle=lifecycle,
            orchestrator=orchestrator,
            em_client=em_client,
            autojob_client=autojob_client,
            enriched_orchestrator=enriched,
            default_strategy=self.default_strategy,
        )

        return coordinator

    def _register_agents(self, coordinator: SwarmCoordinator) -> int:
        """Register all known agents with the coordinator."""
        count = 0
        for agent_def in self._agents:
            agent_id = agent_def["agent_id"]
            wallet = f"0x{agent_id:040x}"

            try:
                coordinator.register_agent(
                    agent_id=agent_id,
                    name=agent_def["name"],
                    wallet_address=wallet,
                    personality=agent_def.get("personality", "explorer"),
                    on_chain=self._on_chain_reps.get(agent_id),
                    internal=self._internal_reps.get(agent_id),
                    tags=agent_def.get("tags", []),
                    activate=True,
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to register agent {agent_id}: {e}")

        return count

    @staticmethod
    def quick_start() -> SwarmCoordinator:
        """
        Minimal bootstrap — creates a coordinator with defaults.
        No API calls, no profile loading. For testing and development.
        """
        bootstrap = SwarmBootstrap()
        coordinator, _ = bootstrap.create_coordinator(
            fetch_live=False,
            use_cached_profiles=False,
        )
        return coordinator
