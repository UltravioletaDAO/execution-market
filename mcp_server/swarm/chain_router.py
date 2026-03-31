"""
ChainRouter — Intelligent Multi-Chain Task Routing (Module #57)
================================================================

Routes tasks to optimal chains based on economic analysis, feature
requirements, worker chain preferences, and real-time network status.

While NetworkRegistry (Module #56) answers "what chains exist?",
ChainRouter answers "which chain should THIS task use?". It combines:

    1. Gas cost analysis (from chain configurations)
    2. Worker chain preferences (from task pool data)
    3. Feature requirements (escrow, reputation, identity)
    4. Network status (degraded chains automatically deprioritized)
    5. Task value economics (micro-tasks vs large bounties)
    6. Historical success rates (which chains have best completion rates)

Integration:
    - NetworkRegistry: Provides chain configurations and status
    - CoordinatorPipeline: Uses ChainRouter as a pre-routing step
    - BudgetController: Factors gas costs into budget allocation
    - SwarmIntegrator: Registers via set_chain_router()

Usage:
    registry = NetworkRegistry.with_defaults()
    router = ChainRouter(registry)

    decision = router.route_task(
        task_value_usd=5.00,
        required_features=["escrow", "payments"],
        worker_wallets=["0xABC..."],
    )
    print(decision.chain)           # "base"
    print(decision.gas_savings_usd) # 1.594 (vs ethereum)
    print(decision.reasoning)       # "Base selected — low gas (0.12%)..."
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, List, Any

logger = logging.getLogger("em.swarm.chain_router")


# ─── Types ────────────────────────────────────────────────────


class RoutingStrategy(str, Enum):
    """Strategy for chain selection."""

    COST_OPTIMAL = "cost_optimal"  # Minimize gas costs
    SPEED_OPTIMAL = "speed_optimal"  # Minimize confirmation time
    FEATURE_MATCH = "feature_match"  # Maximize feature availability
    WORKER_ALIGNED = "worker_aligned"  # Match worker chain preferences
    BALANCED = "balanced"  # Weighted combination (default)


class ChainStatus(str, Enum):
    """Simplified chain status for routing decisions."""

    ACTIVE = "active"
    DEGRADED = "degraded"
    DISABLED = "disabled"


@dataclass
class ChainProfile:
    """Chain profile used by the router (abstracted from NetworkRegistry)."""

    name: str
    chain_key: str
    chain_id: Optional[int] = None
    gas_per_task_usd: float = 0.0
    confirmation_time_seconds: float = 5.0
    status: ChainStatus = ChainStatus.ACTIVE
    supports_escrow: bool = True
    supports_payments: bool = True
    supports_reputation: bool = True
    supports_identity: bool = True
    explorer_url: Optional[str] = None

    @property
    def feature_count(self) -> int:
        return sum(
            [
                self.supports_escrow,
                self.supports_payments,
                self.supports_reputation,
                self.supports_identity,
            ]
        )


@dataclass
class RoutingDecision:
    """Result of a chain routing decision."""

    chain: str
    chain_name: str
    chain_id: Optional[int]
    gas_cost_usd: float
    gas_savings_vs_default_usd: float
    confirmation_time_seconds: float
    score: float
    strategy: str
    reasoning: str
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    decided_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChainSuccessRecord:
    """Tracks task success rate on a specific chain."""

    chain: str
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    avg_completion_time_seconds: float = 0.0
    total_gas_spent_usd: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.completed_tasks / self.total_tasks

    @property
    def avg_gas_per_task_usd(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.total_gas_spent_usd / self.total_tasks


@dataclass
class RoutingStats:
    """Aggregate routing statistics."""

    total_decisions: int = 0
    decisions_per_chain: Dict[str, int] = field(default_factory=dict)
    total_gas_saved_usd: float = 0.0
    avg_decision_time_ms: float = 0.0
    strategy_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Configuration ────────────────────────────────────────────


@dataclass
class ChainRouterConfig:
    """Configuration for the ChainRouter."""

    # Default strategy
    default_strategy: RoutingStrategy = RoutingStrategy.BALANCED

    # Weight distribution for balanced strategy
    cost_weight: float = 0.40
    speed_weight: float = 0.15
    feature_weight: float = 0.15
    history_weight: float = 0.15
    preference_weight: float = 0.15

    # Default chain (when all else fails)
    default_chain: str = "base"

    # Micro-task threshold
    micro_task_threshold_usd: float = 1.00

    # Maximum acceptable gas ratio
    max_gas_ratio: float = 0.10

    # Degraded chain penalty (score multiplier)
    degraded_penalty: float = 0.5

    # History window for success tracking
    history_window: int = 200

    # Platform fee rate (for economics calculation)
    platform_fee_rate: float = 0.13


# ─── Main Class ───────────────────────────────────────────────


class ChainRouter:
    """
    Intelligent multi-chain task routing.

    Selects the optimal blockchain for task deployment based on
    economics, features, worker preferences, and historical data.
    """

    def __init__(
        self,
        config: Optional[ChainRouterConfig] = None,
        chains: Optional[Dict[str, ChainProfile]] = None,
    ):
        self._config = config or ChainRouterConfig()
        self._chains: Dict[str, ChainProfile] = dict(chains or {})
        self._success_records: Dict[str, ChainSuccessRecord] = {}
        self._decision_history: deque = deque(maxlen=self._config.history_window)
        self._stats = RoutingStats()
        self._worker_preferences: Dict[str, str] = {}  # wallet -> preferred chain
        self._created_at = time.time()

    # ─── Factory Methods ─────────────────────────────────────

    @classmethod
    def with_default_chains(
        cls, config: Optional[ChainRouterConfig] = None
    ) -> "ChainRouter":
        """Create router with default chain profiles for all EM networks."""
        chains = {
            "base": ChainProfile(
                name="Base",
                chain_key="base",
                chain_id=8453,
                gas_per_task_usd=0.006,
                confirmation_time_seconds=2.0,
            ),
            "ethereum": ChainProfile(
                name="Ethereum",
                chain_key="ethereum",
                chain_id=1,
                gas_per_task_usd=1.60,
                confirmation_time_seconds=15.0,
            ),
            "polygon": ChainProfile(
                name="Polygon",
                chain_key="polygon",
                chain_id=137,
                gas_per_task_usd=0.025,
                confirmation_time_seconds=5.0,
            ),
            "arbitrum": ChainProfile(
                name="Arbitrum",
                chain_key="arbitrum",
                chain_id=42161,
                gas_per_task_usd=0.008,
                confirmation_time_seconds=2.0,
            ),
            "optimism": ChainProfile(
                name="Optimism",
                chain_key="optimism",
                chain_id=10,
                gas_per_task_usd=0.008,
                confirmation_time_seconds=2.0,
            ),
            "avalanche": ChainProfile(
                name="Avalanche",
                chain_key="avalanche",
                chain_id=43114,
                gas_per_task_usd=0.014,
                confirmation_time_seconds=3.0,
            ),
            "celo": ChainProfile(
                name="Celo",
                chain_key="celo",
                chain_id=42220,
                gas_per_task_usd=0.0016,
                confirmation_time_seconds=5.0,
            ),
            "monad": ChainProfile(
                name="Monad",
                chain_key="monad",
                chain_id=None,
                gas_per_task_usd=0.001,
                confirmation_time_seconds=1.0,
            ),
            "skale": ChainProfile(
                name="SKALE",
                chain_key="skale",
                chain_id=None,
                gas_per_task_usd=0.0,
                confirmation_time_seconds=3.0,
            ),
        }
        return cls(config=config, chains=chains)

    # ─── Core: Route Task ────────────────────────────────────

    def route_task(
        self,
        task_value_usd: float,
        required_features: Optional[List[str]] = None,
        preferred_chain: Optional[str] = None,
        worker_wallets: Optional[List[str]] = None,
        strategy: Optional[RoutingStrategy] = None,
    ) -> RoutingDecision:
        """
        Route a task to the optimal chain.

        Returns a RoutingDecision with the selected chain, score,
        reasoning, and alternatives.
        """
        start_time = time.time()
        strategy = strategy or self._config.default_strategy
        required_features = required_features or []

        # Step 1: Filter eligible chains
        eligible = self._filter_eligible(required_features)
        if not eligible:
            eligible = [
                k for k, v in self._chains.items() if v.status != ChainStatus.DISABLED
            ]
        if not eligible:
            eligible = list(self._chains.keys())

        # Step 2: Score each chain
        scored = []
        for chain_key in eligible:
            profile = self._chains[chain_key]
            score = self._score_chain(
                chain_key,
                profile,
                task_value_usd,
                strategy,
                preferred_chain,
                worker_wallets,
            )
            scored.append((chain_key, profile, score))

        scored.sort(key=lambda x: x[2], reverse=True)

        if not scored:
            # Fallback to default chain
            default = self._chains.get(self._config.default_chain)
            if default is None:
                # Create a minimal fallback
                return RoutingDecision(
                    chain=self._config.default_chain,
                    chain_name="Unknown",
                    chain_id=None,
                    gas_cost_usd=0.0,
                    gas_savings_vs_default_usd=0.0,
                    confirmation_time_seconds=0.0,
                    score=0.0,
                    strategy=strategy.value,
                    reasoning="No chains available — using default",
                )
            scored = [(self._config.default_chain, default, 0.0)]

        best_key, best_profile, best_score = scored[0]

        # Calculate gas savings vs default (ethereum)
        default_gas = self._chains.get(
            "ethereum", ChainProfile(name="", chain_key="", gas_per_task_usd=0.0)
        ).gas_per_task_usd
        gas_savings = max(0, default_gas - best_profile.gas_per_task_usd)

        # Build alternatives
        alternatives = []
        for key, profile, score in scored[1:4]:
            alternatives.append(
                {
                    "chain": key,
                    "chain_name": profile.name,
                    "score": round(score, 2),
                    "gas_cost_usd": round(profile.gas_per_task_usd, 6),
                }
            )

        # Warnings
        warnings = self._generate_warnings(best_key, best_profile, task_value_usd)

        # Reasoning
        reasoning = self._build_reasoning(
            best_key, best_profile, task_value_usd, strategy
        )

        # Metadata
        gas_ratio = (
            (best_profile.gas_per_task_usd / task_value_usd * 100)
            if task_value_usd > 0
            else 0.0
        )
        metadata = {
            "gas_ratio_percent": round(gas_ratio, 4),
            "is_micro_task": task_value_usd < self._config.micro_task_threshold_usd,
            "eligible_chains": len(eligible),
            "scored_chains": len(scored),
        }

        decision = RoutingDecision(
            chain=best_key,
            chain_name=best_profile.name,
            chain_id=best_profile.chain_id,
            gas_cost_usd=round(best_profile.gas_per_task_usd, 6),
            gas_savings_vs_default_usd=round(gas_savings, 6),
            confirmation_time_seconds=best_profile.confirmation_time_seconds,
            score=round(best_score, 2),
            strategy=strategy.value,
            reasoning=reasoning,
            alternatives=alternatives,
            warnings=warnings,
            metadata=metadata,
        )

        # Track decision
        self._record_decision(decision, time.time() - start_time)

        return decision

    # ─── Strategy-Specific Routing ───────────────────────────

    def route_micro_task(self, task_value_usd: float) -> RoutingDecision:
        """Specialized routing for micro-tasks (<$1.00)."""
        return self.route_task(
            task_value_usd=task_value_usd,
            strategy=RoutingStrategy.COST_OPTIMAL,
        )

    def route_high_value_task(
        self,
        task_value_usd: float,
        required_features: Optional[List[str]] = None,
    ) -> RoutingDecision:
        """Specialized routing for high-value tasks (>$100)."""
        return self.route_task(
            task_value_usd=task_value_usd,
            required_features=required_features or ["escrow", "payments", "reputation"],
            strategy=RoutingStrategy.FEATURE_MATCH,
        )

    def route_batch(
        self,
        task_values: List[float],
        strategy: Optional[RoutingStrategy] = None,
    ) -> Dict:
        """
        Route a batch of tasks, optimizing for total gas cost.

        Returns a recommendation to use one chain for all tasks
        (batch efficiency) or split across chains if beneficial.
        """
        if not task_values:
            return {
                "task_count": 0,
                "recommended_chain": self._config.default_chain,
                "total_gas_usd": 0.0,
                "decisions": [],
            }

        total_value = sum(task_values)

        # Score each chain for the batch
        chain_scores = {}
        for chain_key, profile in self._chains.items():
            if profile.status == ChainStatus.DISABLED:
                continue
            total_gas = profile.gas_per_task_usd * len(task_values)
            gas_ratio = (total_gas / total_value) if total_value > 0 else 0.0
            chain_scores[chain_key] = {
                "total_gas_usd": round(total_gas, 4),
                "gas_ratio": round(gas_ratio, 4),
                "per_task_gas": round(profile.gas_per_task_usd, 6),
            }

        # Find optimal
        if chain_scores:
            optimal = min(chain_scores.items(), key=lambda x: x[1]["total_gas_usd"])
            optimal_chain = optimal[0]
            optimal_gas = optimal[1]["total_gas_usd"]
        else:
            optimal_chain = self._config.default_chain
            optimal_gas = 0.0

        # Savings vs Ethereum
        eth_gas = chain_scores.get("ethereum", {}).get("total_gas_usd", 0.0)

        return {
            "task_count": len(task_values),
            "total_value_usd": round(total_value, 4),
            "recommended_chain": optimal_chain,
            "total_gas_usd": optimal_gas,
            "savings_vs_ethereum_usd": round(eth_gas - optimal_gas, 4),
            "chain_analysis": chain_scores,
        }

    # ─── Chain Management ────────────────────────────────────

    def register_chain(self, key: str, profile: ChainProfile) -> None:
        """Register or update a chain profile."""
        self._chains[key] = profile
        if key not in self._success_records:
            self._success_records[key] = ChainSuccessRecord(chain=key)

    def remove_chain(self, key: str) -> bool:
        """Remove a chain."""
        if key in self._chains:
            del self._chains[key]
            return True
        return False

    def get_chain(self, key: str) -> Optional[ChainProfile]:
        """Get a chain profile."""
        return self._chains.get(key)

    def list_chains(self) -> List[str]:
        """List all registered chain keys."""
        return list(self._chains.keys())

    def set_chain_status(self, key: str, status: ChainStatus) -> bool:
        """Update a chain's operational status."""
        if key not in self._chains:
            return False
        self._chains[key].status = status
        return True

    def active_chains(self) -> List[str]:
        """Get all non-disabled chains (includes active and degraded)."""
        return [k for k, v in self._chains.items() if v.status != ChainStatus.DISABLED]

    # ─── Worker Preferences ──────────────────────────────────

    def set_worker_preference(self, wallet: str, chain: str) -> None:
        """Record a worker's chain preference."""
        self._worker_preferences[wallet] = chain

    def get_worker_preference(self, wallet: str) -> Optional[str]:
        """Get a worker's preferred chain."""
        return self._worker_preferences.get(wallet)

    def worker_consensus_chain(self, wallets: List[str]) -> Optional[str]:
        """Find the most popular chain among a set of workers."""
        if not wallets:
            return None
        chain_counts: Dict[str, int] = {}
        for wallet in wallets:
            pref = self._worker_preferences.get(wallet)
            if pref:
                chain_counts[pref] = chain_counts.get(pref, 0) + 1
        if not chain_counts:
            return None
        return max(chain_counts.items(), key=lambda x: x[1])[0]

    # ─── Success Tracking ────────────────────────────────────

    def record_task_outcome(
        self,
        chain: str,
        completed: bool,
        completion_time_seconds: float = 0.0,
        gas_spent_usd: float = 0.0,
    ) -> None:
        """Record a task outcome for chain success rate tracking."""
        if chain not in self._success_records:
            self._success_records[chain] = ChainSuccessRecord(chain=chain)

        record = self._success_records[chain]
        record.total_tasks += 1
        record.total_gas_spent_usd += gas_spent_usd

        if completed:
            record.completed_tasks += 1
            # Update rolling average completion time
            if record.completed_tasks == 1:
                record.avg_completion_time_seconds = completion_time_seconds
            else:
                record.avg_completion_time_seconds = (
                    record.avg_completion_time_seconds * 0.9
                    + completion_time_seconds * 0.1
                )
        else:
            record.failed_tasks += 1

    def chain_success_rate(self, chain: str) -> float:
        """Get the success rate for a chain (0.0-1.0)."""
        record = self._success_records.get(chain)
        if record is None:
            return 0.0
        return record.success_rate

    def chain_success_records(self) -> Dict[str, Dict]:
        """Get all success records."""
        return {
            k: {
                "total_tasks": v.total_tasks,
                "completed": v.completed_tasks,
                "failed": v.failed_tasks,
                "success_rate": round(v.success_rate, 4),
                "avg_completion_seconds": round(v.avg_completion_time_seconds, 1),
                "avg_gas_per_task_usd": round(v.avg_gas_per_task_usd, 6),
            }
            for k, v in self._success_records.items()
        }

    # ─── Diagnostics ─────────────────────────────────────────

    def diagnostics(self) -> Dict:
        """Full diagnostic snapshot."""
        return {
            "chains_registered": len(self._chains),
            "active_chains": len(self.active_chains()),
            "total_decisions": self._stats.total_decisions,
            "decisions_per_chain": dict(self._stats.decisions_per_chain),
            "total_gas_saved_usd": round(self._stats.total_gas_saved_usd, 4),
            "avg_decision_time_ms": round(self._stats.avg_decision_time_ms, 2),
            "strategy_distribution": dict(self._stats.strategy_distribution),
            "worker_preferences_tracked": len(self._worker_preferences),
            "chains_with_history": len(self._success_records),
            "uptime_seconds": round(time.time() - self._created_at, 1),
        }

    def health_check(self) -> Dict:
        """Quick health status."""
        active = self.active_chains()
        degraded = [
            k for k, v in self._chains.items() if v.status == ChainStatus.DEGRADED
        ]
        disabled = [
            k for k, v in self._chains.items() if v.status == ChainStatus.DISABLED
        ]

        status = "healthy"
        if len(degraded) > 0:
            status = "degraded"
        if len(active) == 0:
            status = "critical"

        return {
            "status": status,
            "active": active,
            "degraded": degraded,
            "disabled": disabled,
        }

    # ─── Persistence ─────────────────────────────────────────

    def save(self, path: str) -> None:
        """Save state to JSON."""
        import json

        data = {
            "version": 1,
            "chains": {
                k: {
                    "name": v.name,
                    "chain_key": v.chain_key,
                    "chain_id": v.chain_id,
                    "gas_per_task_usd": v.gas_per_task_usd,
                    "confirmation_time_seconds": v.confirmation_time_seconds,
                    "status": v.status.value,
                    "supports_escrow": v.supports_escrow,
                    "supports_payments": v.supports_payments,
                    "supports_reputation": v.supports_reputation,
                    "supports_identity": v.supports_identity,
                }
                for k, v in self._chains.items()
            },
            "success_records": {
                k: {
                    "total_tasks": v.total_tasks,
                    "completed_tasks": v.completed_tasks,
                    "failed_tasks": v.failed_tasks,
                    "avg_completion_time_seconds": v.avg_completion_time_seconds,
                    "total_gas_spent_usd": v.total_gas_spent_usd,
                }
                for k, v in self._success_records.items()
            },
            "worker_preferences": dict(self._worker_preferences),
            "stats": self._stats.to_dict(),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        """Load state from JSON."""
        import json

        with open(path) as f:
            data = json.load(f)

        if "chains" in data:
            for key, cfg in data["chains"].items():
                self._chains[key] = ChainProfile(
                    name=cfg["name"],
                    chain_key=cfg.get("chain_key", key),
                    chain_id=cfg.get("chain_id"),
                    gas_per_task_usd=cfg.get("gas_per_task_usd", 0.0),
                    confirmation_time_seconds=cfg.get("confirmation_time_seconds", 5.0),
                    status=ChainStatus(cfg.get("status", "active")),
                    supports_escrow=cfg.get("supports_escrow", True),
                    supports_payments=cfg.get("supports_payments", True),
                    supports_reputation=cfg.get("supports_reputation", True),
                    supports_identity=cfg.get("supports_identity", True),
                )

        if "success_records" in data:
            for key, rec in data["success_records"].items():
                self._success_records[key] = ChainSuccessRecord(
                    chain=key,
                    total_tasks=rec.get("total_tasks", 0),
                    completed_tasks=rec.get("completed_tasks", 0),
                    failed_tasks=rec.get("failed_tasks", 0),
                    avg_completion_time_seconds=rec.get(
                        "avg_completion_time_seconds", 0
                    ),
                    total_gas_spent_usd=rec.get("total_gas_spent_usd", 0),
                )

        if "worker_preferences" in data:
            self._worker_preferences = dict(data["worker_preferences"])

        if "stats" in data:
            stats = data["stats"]
            self._stats.total_decisions = stats.get("total_decisions", 0)
            self._stats.decisions_per_chain = stats.get("decisions_per_chain", {})
            self._stats.total_gas_saved_usd = stats.get("total_gas_saved_usd", 0)

    # ─── Private Helpers ─────────────────────────────────────

    def _filter_eligible(self, required_features: List[str]) -> List[str]:
        """Filter chains by status and feature requirements."""
        result = []
        for key, profile in self._chains.items():
            if profile.status == ChainStatus.DISABLED:
                continue

            # Feature checks
            if "escrow" in required_features and not profile.supports_escrow:
                continue
            if "payments" in required_features and not profile.supports_payments:
                continue
            if "reputation" in required_features and not profile.supports_reputation:
                continue
            if "identity" in required_features and not profile.supports_identity:
                continue

            result.append(key)
        return result

    def _score_chain(
        self,
        chain_key: str,
        profile: ChainProfile,
        task_value: float,
        strategy: RoutingStrategy,
        preferred: Optional[str],
        worker_wallets: Optional[List[str]],
    ) -> float:
        """Score a chain based on the selected strategy."""

        if strategy == RoutingStrategy.COST_OPTIMAL:
            return self._score_cost_optimal(chain_key, profile, task_value)
        elif strategy == RoutingStrategy.SPEED_OPTIMAL:
            return self._score_speed_optimal(profile)
        elif strategy == RoutingStrategy.FEATURE_MATCH:
            return self._score_feature_match(profile)
        elif strategy == RoutingStrategy.WORKER_ALIGNED:
            return self._score_worker_aligned(chain_key, profile, worker_wallets or [])
        else:  # BALANCED
            return self._score_balanced(
                chain_key,
                profile,
                task_value,
                preferred,
                worker_wallets,
            )

    def _score_cost_optimal(
        self, chain_key: str, profile: ChainProfile, task_value: float
    ) -> float:
        """Score purely on gas cost efficiency."""
        if task_value <= 0:
            return 100.0 if profile.gas_per_task_usd == 0 else 50.0

        gas_ratio = profile.gas_per_task_usd / task_value
        score = max(0, 100 * (1 - gas_ratio * 10))

        # Degraded penalty
        if profile.status == ChainStatus.DEGRADED:
            score *= self._config.degraded_penalty

        return round(score, 2)

    def _score_speed_optimal(self, profile: ChainProfile) -> float:
        """Score on confirmation speed."""
        # Lower confirmation time = higher score
        # Max score at 1s, drops to 0 at 30s
        score = max(0, 100 * (1 - profile.confirmation_time_seconds / 30))

        if profile.status == ChainStatus.DEGRADED:
            score *= self._config.degraded_penalty

        return round(score, 2)

    def _score_feature_match(self, profile: ChainProfile) -> float:
        """Score on feature completeness."""
        score = profile.feature_count * 25  # 25 per feature, max 100

        if profile.status == ChainStatus.DEGRADED:
            score *= self._config.degraded_penalty

        return round(score, 2)

    def _score_worker_aligned(
        self,
        chain_key: str,
        profile: ChainProfile,
        worker_wallets: List[str],
    ) -> float:
        """Score based on worker chain preferences."""
        if not worker_wallets:
            return 50.0  # Neutral

        matches = sum(
            1 for w in worker_wallets if self._worker_preferences.get(w) == chain_key
        )
        match_ratio = matches / len(worker_wallets)
        score = match_ratio * 100

        if profile.status == ChainStatus.DEGRADED:
            score *= self._config.degraded_penalty

        return round(score, 2)

    def _score_balanced(
        self,
        chain_key: str,
        profile: ChainProfile,
        task_value: float,
        preferred: Optional[str],
        worker_wallets: Optional[List[str]],
    ) -> float:
        """Balanced scoring across all dimensions."""
        cfg = self._config

        # Cost component
        cost_score = self._score_cost_optimal(chain_key, profile, task_value)

        # Speed component
        speed_score = self._score_speed_optimal(profile)

        # Feature component
        feature_score = self._score_feature_match(profile)

        # History component
        record = self._success_records.get(chain_key)
        if record and record.total_tasks > 0:
            history_score = record.success_rate * 100
        else:
            history_score = 50.0  # Neutral for unknown chains

        # Preference component
        pref_score = 50.0  # Default neutral
        if preferred and chain_key == preferred:
            pref_score = 100.0
        elif worker_wallets:
            consensus = self.worker_consensus_chain(worker_wallets)
            if consensus == chain_key:
                pref_score = 80.0

        total = (
            cost_score * cfg.cost_weight
            + speed_score * cfg.speed_weight
            + feature_score * cfg.feature_weight
            + history_score * cfg.history_weight
            + pref_score * cfg.preference_weight
        )

        # Degraded penalty (applied on top of component penalties)
        if profile.status == ChainStatus.DEGRADED:
            total *= self._config.degraded_penalty

        return round(total, 2)

    def _generate_warnings(
        self,
        chain_key: str,
        profile: ChainProfile,
        task_value: float,
    ) -> List[str]:
        """Generate warnings for a routing decision."""
        warnings = []

        if profile.status == ChainStatus.DEGRADED:
            warnings.append(f"{profile.name} is currently degraded — monitor closely")

        if task_value > 0:
            gas_ratio = profile.gas_per_task_usd / task_value
            if gas_ratio > self._config.max_gas_ratio:
                warnings.append(
                    f"Gas cost ({gas_ratio * 100:.1f}%) exceeds "
                    f"target ({self._config.max_gas_ratio * 100:.0f}%)"
                )

        if task_value < self._config.micro_task_threshold_usd:
            if profile.gas_per_task_usd > 0:
                warnings.append("Micro-task with non-zero gas — consider free chains")

        record = self._success_records.get(chain_key)
        if record and record.total_tasks >= 5 and record.success_rate < 0.8:
            warnings.append(
                f"Low success rate on {profile.name}: {record.success_rate:.0%}"
            )

        return warnings

    def _build_reasoning(
        self,
        chain_key: str,
        profile: ChainProfile,
        task_value: float,
        strategy: RoutingStrategy,
    ) -> str:
        """Build human-readable reasoning."""
        parts = [f"{profile.name} selected"]

        if strategy == RoutingStrategy.COST_OPTIMAL:
            parts.append("cost-optimized")
        elif strategy == RoutingStrategy.SPEED_OPTIMAL:
            parts.append(f"fastest ({profile.confirmation_time_seconds}s)")
        elif strategy == RoutingStrategy.FEATURE_MATCH:
            parts.append(f"{profile.feature_count}/4 features")
        elif strategy == RoutingStrategy.WORKER_ALIGNED:
            parts.append("worker-preferred")
        else:
            parts.append("balanced scoring")

        if profile.gas_per_task_usd == 0:
            parts.append("zero gas")
        elif task_value > 0:
            pct = profile.gas_per_task_usd / task_value * 100
            parts.append(f"gas {pct:.2f}%")

        return " — ".join(parts)

    def _record_decision(self, decision: RoutingDecision, elapsed: float) -> None:
        """Record a routing decision in history and stats."""
        self._decision_history.append(decision)

        self._stats.total_decisions += 1
        chain = decision.chain
        self._stats.decisions_per_chain[chain] = (
            self._stats.decisions_per_chain.get(chain, 0) + 1
        )
        self._stats.total_gas_saved_usd += decision.gas_savings_vs_default_usd
        self._stats.strategy_distribution[decision.strategy] = (
            self._stats.strategy_distribution.get(decision.strategy, 0) + 1
        )

        # Rolling average decision time
        elapsed_ms = elapsed * 1000
        n = self._stats.total_decisions
        if n == 1:
            self._stats.avg_decision_time_ms = elapsed_ms
        else:
            self._stats.avg_decision_time_ms = (
                self._stats.avg_decision_time_ms * 0.95 + elapsed_ms * 0.05
            )
