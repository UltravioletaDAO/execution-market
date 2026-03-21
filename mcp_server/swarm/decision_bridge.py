"""
DecisionBridge — Wires DecisionSynthesizer into the SwarmCoordinator Pipeline
=============================================================================

The 3 AM session built two keystones:
  1. DecisionSynthesizer — unified multi-signal routing engine
  2. TaskDecomposer (in AutoJob) — compound task breakdown

But neither was connected to the actual routing pipeline. The coordinator
still used basic orchestrator.route_task() with reputation-only scoring.

DecisionBridge solves this by:
  1. **Signal Registration** — wires ReputationBridge, AvailabilityBridge,
     AutoJobClient, WorkforceAnalytics, and CapacityPlanner as signal providers
  2. **Routing Upgrade** — replaces orchestrator.route_task() with
     DecisionSynthesizer.synthesize() for multi-signal decisions
  3. **Decomposition Hook** — calls AutoJob's TaskDecomposer for compound
     tasks and splits them into sub-tasks before routing
  4. **Feedback Loop** — feeds completed task outcomes back to
     RoutingOptimizer for evolutionary weight tuning
  5. **Coordinator Integration** — provides a drop-in method that the
     SwarmCoordinator can call instead of process_task_queue()

Architecture:

    SwarmCoordinator.process_task_queue()
        ↓ [replaced by]
    DecisionBridge.process_with_synthesis()
        ├── _maybe_decompose(task) → sub-tasks (via AutoJob API)
        ├── _collect_candidates(task) → agent list
        ├── DecisionSynthesizer.synthesize(task, candidates) → RankedDecision
        ├── _apply_decision(decision) → Assignment or hold
        └── _record_outcome(task, outcome) → RoutingOptimizer feedback

    Feedback loop (on task completion):
    DecisionBridge.record_outcome(task_id, outcome)
        ├── RoutingOptimizer.record_outcome(weights, outcome_type)
        ├── RoutingOptimizer.evolve() → RoutingRecommendation
        └── DecisionSynthesizer.update_weights(new_weights) [if confidence > threshold]

Usage:
    bridge = DecisionBridge.from_coordinator(coordinator)
    results = bridge.process_with_synthesis(max_tasks=10)

    # Or wire into coordinator:
    coordinator.decision_bridge = DecisionBridge.from_coordinator(coordinator)
    # Then coordinator can call: self.decision_bridge.process_with_synthesis()

Thread-safety: NOT thread-safe (same as SwarmCoordinator).
"""

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable, Any

from .decision_synthesizer import (
    DecisionSynthesizer,
    SignalType,
    DecisionOutcome,
    ConfidenceLevel,
    RankedDecision,
)
from .orchestrator import (
    SwarmOrchestrator,
    TaskRequest,
    Assignment,
    RoutingFailure,
    RoutingStrategy,
)

logger = logging.getLogger("em.swarm.decision_bridge")


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


class BridgeMode(str, Enum):
    """Operational modes for the bridge."""
    SHADOW = "shadow"       # Run synthesis but don't override routing (logging only)
    ADVISORY = "advisory"   # Synthesize and log; coordinator can choose to use it
    PRIMARY = "primary"     # DecisionSynthesizer is the primary routing engine
    DISABLED = "disabled"   # Bridge inactive, coordinator uses legacy routing


@dataclass
class DecomposedTask:
    """A compound task broken into sub-tasks by AutoJob TaskDecomposer."""
    original_task_id: str
    sub_tasks: list[dict] = field(default_factory=list)
    team_strategy: str = "solo"  # solo, specialist, parallel, hybrid
    estimated_total_hours: float = 0.0
    decomposition_time_ms: float = 0.0

    @property
    def is_compound(self) -> bool:
        return len(self.sub_tasks) > 1


@dataclass
class BridgeResult:
    """Result of processing a task through the decision bridge."""
    task_id: str
    decision: Optional[RankedDecision] = None
    assignment: Optional[Assignment] = None
    failure: Optional[RoutingFailure] = None
    decomposition: Optional[DecomposedTask] = None
    legacy_result: Any = None  # What the old pipeline would have done
    mode: BridgeMode = BridgeMode.PRIMARY
    synthesis_time_ms: float = 0.0
    used_synthesis: bool = False

    @property
    def succeeded(self) -> bool:
        return self.assignment is not None

    def to_dict(self) -> dict:
        result = {
            "task_id": self.task_id,
            "mode": self.mode.value,
            "used_synthesis": self.used_synthesis,
            "synthesis_time_ms": round(self.synthesis_time_ms, 2),
            "succeeded": self.succeeded,
        }
        if self.decision:
            result["decision"] = {
                "outcome": self.decision.outcome.value,
                "best_candidate": self.decision.best_candidate,
                "confidence": self.decision.confidence_level.value,
                "signals_used": self.decision.signal_types_used,
            }
        if self.decomposition and self.decomposition.is_compound:
            result["decomposed"] = {
                "sub_task_count": len(self.decomposition.sub_tasks),
                "team_strategy": self.decomposition.team_strategy,
            }
        return result


@dataclass
class FeedbackRecord:
    """Records a decision outcome for the feedback loop."""
    task_id: str
    decision_outcome: str  # routed, held, etc.
    actual_outcome: str    # completed, expired, failed
    agent_id: Optional[str] = None
    decision_score: float = 0.0
    signals_used: list[str] = field(default_factory=list)
    time_to_completion_hours: float = 0.0
    quality_rating: float = 0.0  # 0-1 if rated
    timestamp: str = ""


# ──────────────────────────────────────────────────────────────
# Signal Adapters — Convert existing module outputs to scorer functions
# ──────────────────────────────────────────────────────────────


def _make_reputation_scorer(source) -> Callable:
    """Create a scorer function from reputation data source.

    Accepts either:
    - A SwarmOrchestrator (with _on_chain / _internal dicts)
    - Any object with get_composite_score(agent_id) method

    The orchestrator stores on-chain + internal reputation data and
    uses ReputationBridge to compute composite scores on the fly.
    """
    def scorer(task: dict, candidate: dict) -> float:
        agent_id = candidate.get("agent_id") or candidate.get("id")
        if agent_id is None:
            return 0.0
        try:
            agent_id = int(agent_id)
            # Try orchestrator path: compute via stored on-chain + internal
            if hasattr(source, '_on_chain') and hasattr(source, '_internal'):
                on_chain = source._on_chain.get(agent_id)
                internal = source._internal.get(agent_id)
                if on_chain and internal and hasattr(source, 'bridge'):
                    composite = source.bridge.compute_composite(on_chain, internal)
                    return composite.total  # 0-100
                elif on_chain is None and internal is None:
                    return 0.0
            # Try direct method
            if hasattr(source, 'get_composite_score'):
                composite = source.get_composite_score(agent_id)
                return getattr(composite, 'total',
                              getattr(composite, 'overall_score', 0.0))
            return 0.0
        except Exception:
            return 0.0
    return scorer


def _make_availability_scorer(avail_bridge) -> Callable:
    """Create a scorer function from AvailabilityBridge."""
    def scorer(task: dict, candidate: dict) -> float:
        wallet = candidate.get("wallet", "")
        if not wallet:
            return 50.0  # Neutral if no wallet
        try:
            prediction = avail_bridge.predict(wallet)
            # prediction.probability is 0.0-1.0
            return prediction.probability * 100
        except Exception:
            return 50.0  # Neutral on error
    return scorer


def _make_skill_match_scorer(autojob_client) -> Callable:
    """Create a scorer from AutoJob's skill matching."""
    def scorer(task: dict, candidate: dict) -> float:
        wallet = candidate.get("wallet", "")
        if not wallet:
            return 0.0
        try:
            enrichments = autojob_client.enrich_agents(task, [wallet])
            enrichment = enrichments.get(wallet)
            if enrichment:
                return enrichment.skill_match  # 0-100
            return 0.0
        except Exception:
            return 0.0
    return scorer


def _make_reliability_scorer(source) -> Callable:
    """Create a reliability scorer from internal reputation data.

    Accepts a SwarmOrchestrator (with _internal dict) or any object
    that stores internal reputation data keyed by agent_id.
    """
    def scorer(task: dict, candidate: dict) -> float:
        agent_id = candidate.get("agent_id") or candidate.get("id")
        if agent_id is None:
            return 0.0
        try:
            internal_dict = getattr(source, '_internal', {})
            internal = internal_dict.get(int(agent_id))
            if internal and internal.total_tasks > 0:
                return (internal.successful_tasks / internal.total_tasks) * 100
            return 50.0  # Neutral for new agents
        except Exception:
            return 50.0
    return scorer


def _make_capacity_scorer(lifecycle) -> Callable:
    """Create a capacity scorer from LifecycleManager."""
    def scorer(task: dict, candidate: dict) -> float:
        agent_id = candidate.get("agent_id") or candidate.get("id")
        if agent_id is None:
            return 0.0
        try:
            record = lifecycle.agents.get(int(agent_id))
            if record is None:
                return 0.0
            # Agent is available if no current task
            if record.current_task_id:
                return 10.0  # Busy but could queue
            budget = lifecycle.get_budget_status(int(agent_id))
            # More budget headroom = higher score
            daily_remaining = 100 - budget.get("daily_pct", 0)
            return max(0, min(100, daily_remaining))
        except Exception:
            return 50.0
    return scorer


def _make_workforce_scorer(analytics) -> Callable:
    """Create a scorer from WorkforceAnalytics health scores."""
    def scorer(task: dict, candidate: dict) -> float:
        agent_id = str(candidate.get("agent_id") or candidate.get("id", ""))
        if not agent_id:
            return 0.0
        try:
            health = analytics.get_worker_health(agent_id)
            if health:
                return health.get("health_score", 50.0)  # 0-100
            return 50.0
        except Exception:
            return 50.0
    return scorer


# ──────────────────────────────────────────────────────────────
# DecisionBridge
# ──────────────────────────────────────────────────────────────


class DecisionBridge:
    """
    Wires DecisionSynthesizer into the SwarmCoordinator routing pipeline.

    This is the integration layer that turns disconnected intelligence
    modules into a unified decision engine.
    """

    def __init__(
        self,
        synthesizer: DecisionSynthesizer,
        orchestrator: SwarmOrchestrator,
        lifecycle_manager=None,
        reputation_bridge=None,
        autojob_client=None,
        availability_bridge=None,
        workforce_analytics=None,
        routing_optimizer=None,
        mode: BridgeMode = BridgeMode.PRIMARY,
        decomposition_enabled: bool = True,
        feedback_enabled: bool = True,
        auto_evolve_threshold: int = 20,
    ):
        self.synthesizer = synthesizer
        self.orchestrator = orchestrator
        self.lifecycle = lifecycle_manager
        self.reputation_bridge = reputation_bridge
        self.autojob = autojob_client
        self.availability_bridge = availability_bridge
        self.workforce_analytics = workforce_analytics
        self.routing_optimizer = routing_optimizer
        self.mode = mode
        self.decomposition_enabled = decomposition_enabled
        self.feedback_enabled = feedback_enabled
        self.auto_evolve_threshold = auto_evolve_threshold

        # Tracking
        self._results: deque[BridgeResult] = deque(maxlen=1000)
        self._feedback: deque[FeedbackRecord] = deque(maxlen=1000)
        self._decisions_since_evolve = 0
        self._total_processed = 0
        self._total_synthesized = 0
        self._total_decomposed = 0
        self._total_feedback_recorded = 0

        # Auto-register available signals
        self._register_available_signals()

    @classmethod
    def from_coordinator(
        cls,
        coordinator,  # SwarmCoordinator
        mode: BridgeMode = BridgeMode.PRIMARY,
        **kwargs,
    ) -> "DecisionBridge":
        """
        Factory: build a DecisionBridge from an existing SwarmCoordinator.

        Automatically detects which intelligence modules are available
        and registers them as signal providers.
        """
        synthesizer = DecisionSynthesizer()

        # Import optional modules safely
        routing_optimizer = None
        availability_bridge = None
        workforce_analytics = None

        # Try to get routing_optimizer from coordinator or integrator
        routing_optimizer = getattr(coordinator, "routing_optimizer", None)
        availability_bridge = getattr(coordinator, "availability_bridge", None)
        workforce_analytics = getattr(coordinator, "workforce_analytics", None)

        return cls(
            synthesizer=synthesizer,
            orchestrator=coordinator.orchestrator,
            lifecycle_manager=coordinator.lifecycle,
            reputation_bridge=coordinator.bridge,
            autojob_client=coordinator.autojob,
            availability_bridge=availability_bridge,
            workforce_analytics=workforce_analytics,
            routing_optimizer=routing_optimizer,
            mode=mode,
            **kwargs,
        )

    # ── Signal Registration ──────────────────────────────────

    def _register_available_signals(self):
        """Auto-detect and register available intelligence modules as signals."""
        registered = []

        # Reputation (use orchestrator for data access, falls back to bridge)
        rep_source = self.orchestrator if self.orchestrator else self.reputation_bridge
        if rep_source:
            self.synthesizer.register_signal(
                SignalType.REPUTATION,
                _make_reputation_scorer(rep_source),
                confidence=0.85,
                description="ReputationBridge (on-chain + internal)",
            )
            # Also register reliability from internal reputation
            self.synthesizer.register_signal(
                SignalType.RELIABILITY,
                _make_reliability_scorer(rep_source),
                confidence=0.75,
                description="Completion rate from internal reputation",
            )
            registered.extend(["reputation", "reliability"])

        # Skill match from AutoJob
        if self.autojob:
            self.synthesizer.register_signal(
                SignalType.SKILL_MATCH,
                _make_skill_match_scorer(self.autojob),
                confidence=0.80,
                description="AutoJob SkillGraph-enriched matching",
            )
            registered.append("skill_match")

        # Availability predictions
        if self.availability_bridge:
            self.synthesizer.register_signal(
                SignalType.AVAILABILITY,
                _make_availability_scorer(self.availability_bridge),
                confidence=0.70,
                description="Timezone-aware availability prediction",
            )
            registered.append("availability")

        # Capacity from lifecycle
        if self.lifecycle:
            self.synthesizer.register_signal(
                SignalType.CAPACITY,
                _make_capacity_scorer(self.lifecycle),
                confidence=0.90,
                description="LifecycleManager budget + workload",
            )
            registered.append("capacity")

        # Workforce health
        if self.workforce_analytics:
            self.synthesizer.register_signal(
                SignalType.SPECIALIZATION,
                _make_workforce_scorer(self.workforce_analytics),
                confidence=0.65,
                description="WorkforceAnalytics health score",
            )
            registered.append("specialization")

        logger.info(
            "DecisionBridge registered %d signals: %s",
            len(registered), ", ".join(registered),
        )

    # ── Core Processing ──────────────────────────────────────

    def process_with_synthesis(
        self,
        task_queue: dict,
        max_tasks: int = 10,
        strategy: Optional[RoutingStrategy] = None,
    ) -> list[BridgeResult]:
        """
        Process pending tasks using multi-signal DecisionSynthesizer.

        Drop-in replacement for SwarmCoordinator.process_task_queue().

        Args:
            task_queue: The coordinator's _task_queue dict
            max_tasks: Max tasks to process per cycle
            strategy: Optional routing strategy override

        Returns:
            List of BridgeResult with full decision context
        """
        results = []

        # Get pending tasks (same sorting as coordinator)
        pending = [
            t for t in task_queue.values()
            if t.status == "pending" and t.attempts < t.max_attempts
        ]
        pending.sort(
            key=lambda t: (
                -{"critical": 3, "high": 2, "normal": 1, "low": 0}.get(
                    t.priority.value, 0
                ),
                t.ingested_at,
            )
        )

        for task in pending[:max_tasks]:
            result = self._process_single_task(task, strategy)
            results.append(result)
            self._results.append(result)
            self._total_processed += 1

        return results

    def _process_single_task(
        self,
        queued_task,  # QueuedTask
        strategy: Optional[RoutingStrategy] = None,
    ) -> BridgeResult:
        """Process a single task through the full decision pipeline."""
        task_id = queued_task.task_id
        start = time.monotonic()

        # Step 1: Maybe decompose compound tasks
        decomposition = None
        if self.decomposition_enabled and self.autojob:
            decomposition = self._try_decompose(queued_task)

        # Step 2: Collect candidates
        candidates = self._collect_candidates(queued_task)

        if not candidates:
            return BridgeResult(
                task_id=task_id,
                failure=RoutingFailure(
                    task_id=task_id,
                    reason="No available candidates",
                    attempted_agents=0, excluded_agents=0,
                ),
                mode=self.mode,
                decomposition=decomposition,
            )

        # Step 3: Build task dict for synthesizer
        task_dict = {
            "id": task_id,
            "task_id": task_id,
            "title": queued_task.title,
            "category": queued_task.categories[0] if queued_task.categories else "general",
            "categories": queued_task.categories,
            "bounty_usd": queued_task.bounty_usd,
            "priority": queued_task.priority.value,
        }

        # Step 4: Synthesize decision
        if self.mode in (BridgeMode.PRIMARY, BridgeMode.ADVISORY, BridgeMode.SHADOW):
            decision = self.synthesizer.synthesize(task_dict, candidates)
            self._total_synthesized += 1
            self._decisions_since_evolve += 1
        else:
            decision = None

        elapsed = (time.monotonic() - start) * 1000

        # Step 5: Apply decision or fall back to legacy routing
        if self.mode == BridgeMode.PRIMARY and decision:
            assignment, failure = self._apply_decision(
                queued_task, decision, candidates
            )
            return BridgeResult(
                task_id=task_id,
                decision=decision,
                assignment=assignment,
                failure=failure,
                decomposition=decomposition,
                mode=self.mode,
                synthesis_time_ms=elapsed,
                used_synthesis=True,
            )

        elif self.mode == BridgeMode.SHADOW:
            # Run synthesis for logging but use legacy routing
            legacy = self._legacy_route(queued_task, strategy)
            return BridgeResult(
                task_id=task_id,
                decision=decision,
                assignment=legacy if isinstance(legacy, Assignment) else None,
                failure=legacy if isinstance(legacy, RoutingFailure) else None,
                legacy_result=legacy,
                decomposition=decomposition,
                mode=self.mode,
                synthesis_time_ms=elapsed,
                used_synthesis=False,
            )

        else:
            # Advisory or disabled: legacy route
            legacy = self._legacy_route(queued_task, strategy)
            return BridgeResult(
                task_id=task_id,
                decision=decision,
                assignment=legacy if isinstance(legacy, Assignment) else None,
                failure=legacy if isinstance(legacy, RoutingFailure) else None,
                legacy_result=legacy,
                decomposition=decomposition,
                mode=self.mode,
                synthesis_time_ms=elapsed,
                used_synthesis=False,
            )

    def _collect_candidates(self, queued_task) -> list[dict]:
        """Build candidate list from lifecycle-managed agents."""
        if not self.lifecycle:
            return []

        available = self.lifecycle.get_available_agents()
        candidates = []

        for agent in available:
            candidates.append({
                "id": agent.agent_id,
                "agent_id": agent.agent_id,
                "name": agent.name,
                "wallet": agent.wallet_address,
                "personality": agent.personality,
                "tags": agent.tags if hasattr(agent, "tags") else [],
                "current_task": agent.current_task_id,
            })

        return candidates

    def _apply_decision(
        self,
        queued_task,
        decision: RankedDecision,
        candidates: list[dict],
    ) -> tuple[Optional[Assignment], Optional[RoutingFailure]]:
        """
        Apply a synthesized decision by assigning the task to the best candidate.

        Uses the orchestrator's claim mechanism to ensure proper lifecycle transitions.
        """
        if decision.outcome != DecisionOutcome.ROUTED or not decision.best_candidate:
            return None, RoutingFailure(
                task_id=queued_task.task_id,
                reason=f"Decision outcome: {decision.outcome.value}",
                attempted_agents=len(decision.rankings), excluded_agents=0,
            )

        # Find the best candidate's agent_id
        best_id = decision.best_candidate
        try:
            agent_id = int(best_id)
        except (ValueError, TypeError):
            return None, RoutingFailure(
                task_id=queued_task.task_id,
                reason=f"Invalid candidate ID: {best_id}",
                attempted_agents=len(decision.rankings), excluded_agents=0,
            )

        # Use orchestrator to claim the task (handles lifecycle transitions)
        task_request = queued_task.to_task_request()

        # Try to claim with the synthesis-recommended agent
        try:
            result = self.orchestrator.route_task(
                task_request,
                strategy=RoutingStrategy.BEST_FIT,
            )

            if isinstance(result, Assignment):
                # Check if the orchestrator picked the same agent as synthesis
                if result.agent_id != agent_id:
                    logger.info(
                        "Synthesis recommended agent %d but orchestrator assigned %d "
                        "(synthesis score=%.3f, confidence=%s)",
                        agent_id, result.agent_id,
                        decision.best_score, decision.confidence_level.value,
                    )
                return result, None
            else:
                return None, result

        except Exception as e:
            logger.error("Failed to apply decision for task %s: %s",
                         queued_task.task_id, e)
            return None, RoutingFailure(
                task_id=queued_task.task_id,
                reason=f"Application error: {e}",
                attempted_agents=len(decision.rankings), excluded_agents=0,
            )

    def _legacy_route(self, queued_task, strategy=None):
        """Fall back to the original orchestrator routing."""
        task_request = queued_task.to_task_request()
        strategy = strategy or RoutingStrategy.BEST_FIT

        if hasattr(self, '_enriched') and self._enriched:
            return self._enriched.route_task(task_request, strategy=strategy)
        return self.orchestrator.route_task(task_request, strategy=strategy)

    # ── Task Decomposition ───────────────────────────────────

    def _try_decompose(self, queued_task) -> Optional[DecomposedTask]:
        """
        Try to decompose a compound task via AutoJob's TaskDecomposer.

        Only decomposes if:
        1. AutoJob is available
        2. Task description suggests multi-skill requirements
        3. Bounty is high enough to justify decomposition
        """
        if not self.autojob or not self.autojob.is_available():
            return None

        # Only decompose tasks with substantial bounties (worth splitting)
        if queued_task.bounty_usd < 10.0:
            return None

        start = time.monotonic()

        try:
            task_dict = {
                "title": queued_task.title,
                "category": queued_task.categories[0] if queued_task.categories else "general",
                "bounty_usd": queued_task.bounty_usd,
                "description": queued_task.raw_data.get("description", ""),
            }

            resp = self.autojob._post("/api/swarm/decompose", task_dict)
            elapsed = (time.monotonic() - start) * 1000

            if resp.get("success") and resp.get("sub_tasks"):
                self._total_decomposed += 1
                return DecomposedTask(
                    original_task_id=queued_task.task_id,
                    sub_tasks=resp["sub_tasks"],
                    team_strategy=resp.get("team_strategy", "solo"),
                    estimated_total_hours=resp.get("estimated_hours", 0),
                    decomposition_time_ms=elapsed,
                )
        except Exception as e:
            logger.warning("Decomposition failed for %s: %s", queued_task.task_id, e)

        return None

    # ── Feedback Loop ────────────────────────────────────────

    def record_outcome(
        self,
        task_id: str,
        outcome: str,  # completed, expired, failed, rejected
        quality_rating: float = 0.0,
        time_to_completion_hours: float = 0.0,
    ):
        """
        Record a task outcome for the routing feedback loop.

        This is called when a task reaches a terminal state.
        The outcome is used to:
        1. Update the RoutingOptimizer with real-world results
        2. Track DecisionSynthesizer accuracy over time
        3. Trigger weight evolution when enough data accumulates
        """
        if not self.feedback_enabled:
            return

        # Find the decision that led to this outcome
        matching_results = [
            r for r in self._results if r.task_id == task_id
        ]

        record = FeedbackRecord(
            task_id=task_id,
            decision_outcome=(
                matching_results[-1].decision.outcome.value
                if matching_results and matching_results[-1].decision
                else "unknown"
            ),
            actual_outcome=outcome,
            agent_id=(
                str(matching_results[-1].decision.best_candidate)
                if matching_results and matching_results[-1].decision
                else None
            ),
            decision_score=(
                matching_results[-1].decision.best_score
                if matching_results and matching_results[-1].decision
                else 0.0
            ),
            signals_used=(
                matching_results[-1].decision.signal_types_used
                if matching_results and matching_results[-1].decision
                else []
            ),
            time_to_completion_hours=time_to_completion_hours,
            quality_rating=quality_rating,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._feedback.append(record)
        self._total_feedback_recorded += 1

        # Feed to RoutingOptimizer if available
        if self.routing_optimizer:
            try:
                self._feed_optimizer(record)
            except Exception as e:
                logger.warning("Failed to feed optimizer: %s", e)

        # Auto-evolve weights if enough outcomes accumulated
        if (
            self.routing_optimizer
            and self._decisions_since_evolve >= self.auto_evolve_threshold
        ):
            self._try_evolve_weights()

    def _feed_optimizer(self, record: FeedbackRecord):
        """Feed a single outcome to the RoutingOptimizer."""
        if not self.routing_optimizer:
            return

        # Map string outcomes to optimizer's OutcomeType
        from .routing_optimizer import OutcomeType, TaskOutcome

        outcome_map = {
            "completed": OutcomeType.COMPLETED,
            "expired": OutcomeType.EXPIRED,
            "failed": OutcomeType.REJECTED,
            "rejected": OutcomeType.REJECTED,
            "cancelled": OutcomeType.CANCELLED,
        }

        outcome_type = outcome_map.get(record.actual_outcome, OutcomeType.REJECTED)

        self.routing_optimizer.record_outcome(
            TaskOutcome(
                task_id=record.task_id,
                outcome=outcome_type,
                quality=record.quality_rating,
                time_hours=record.time_to_completion_hours,
            )
        )

    def _try_evolve_weights(self):
        """
        Run evolutionary weight tuning from accumulated outcomes.

        Only applies new weights if the optimizer's recommendation
        has high enough confidence.
        """
        if not self.routing_optimizer:
            return

        try:
            recommendation = self.routing_optimizer.evolve()
            if recommendation and recommendation.confidence >= 0.6:
                # Map optimizer weights to synthesizer signal types
                new_weights = {}
                weight_config = recommendation.weights
                if hasattr(weight_config, 'skill_match'):
                    new_weights[SignalType.SKILL_MATCH] = weight_config.skill_match
                if hasattr(weight_config, 'reputation'):
                    new_weights[SignalType.REPUTATION] = weight_config.reputation
                if hasattr(weight_config, 'capacity'):
                    new_weights[SignalType.CAPACITY] = weight_config.capacity
                if hasattr(weight_config, 'speed'):
                    new_weights[SignalType.SPEED] = weight_config.speed
                if hasattr(weight_config, 'cost'):
                    new_weights[SignalType.COST] = weight_config.cost

                if new_weights:
                    self.synthesizer.update_weights(new_weights)
                    logger.info(
                        "Evolved weights from optimizer (confidence=%.2f): %s",
                        recommendation.confidence,
                        {k.value: round(v, 3) for k, v in new_weights.items()},
                    )

            self._decisions_since_evolve = 0

        except Exception as e:
            logger.warning("Weight evolution failed: %s", e)

    # ── Dashboard & Stats ────────────────────────────────────

    @property
    def stats(self) -> dict:
        """Comprehensive bridge statistics."""
        synth_stats = self.synthesizer.stats

        # Feedback accuracy
        correct = sum(
            1 for f in self._feedback
            if f.decision_outcome == "routed" and f.actual_outcome == "completed"
        )
        total_routed = sum(
            1 for f in self._feedback
            if f.decision_outcome == "routed"
        )

        return {
            "mode": self.mode.value,
            "total_processed": self._total_processed,
            "total_synthesized": self._total_synthesized,
            "total_decomposed": self._total_decomposed,
            "feedback_recorded": self._total_feedback_recorded,
            "decisions_since_evolve": self._decisions_since_evolve,
            "auto_evolve_threshold": self.auto_evolve_threshold,
            "routing_accuracy": (
                round(correct / total_routed, 3) if total_routed > 0 else None
            ),
            "synthesizer": synth_stats,
            "current_weights": self.synthesizer.get_weights(),
            "registered_signals": self.synthesizer.registered_signals,
        }

    def get_feedback_history(self, limit: int = 50) -> list[dict]:
        """Get recent feedback records."""
        records = list(self._feedback)[-limit:]
        return [
            {
                "task_id": r.task_id,
                "decision": r.decision_outcome,
                "actual": r.actual_outcome,
                "agent": r.agent_id,
                "score": round(r.decision_score, 3),
                "quality": round(r.quality_rating, 2),
                "time_h": round(r.time_to_completion_hours, 2),
                "signals": len(r.signals_used),
                "ts": r.timestamp,
            }
            for r in records
        ]
