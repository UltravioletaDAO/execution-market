"""
ArbiterService — Ring 2 entry point.

Orchestrates the dual-ring verdict pipeline:
1. Read Ring 1 (PHOTINT) results from submission.ai_verification_result + auto_check_details
2. Route to inference tier (Cheap/Standard/Max) via TierRouter
3. Run independent Ring 2 inference(s) with task-completion prompt
4. Combine via DualRingConsensus
5. Compute commitment hash and return ArbiterVerdict

This is a STATELESS service. Persistence is the caller's responsibility
(processor.py in Phase 2 stores the verdict and triggers release/refund).

Usage:
    arbiter = ArbiterService.from_defaults()
    verdict = await arbiter.evaluate(task, submission)
    if verdict.is_pass:
        ...
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from web3 import Web3

from verification.events import emit_verification_event

from .consensus import DualRingConsensus, get_default_consensus
from .registry import ArbiterRegistry, get_default_registry
from .tier_router import TierRouter, get_default_router
from .types import (
    ArbiterConfig,
    ArbiterDecision,
    ArbiterTier,
    ArbiterVerdict,
    RingScore,
)

logger = logging.getLogger(__name__)


class ArbiterService:
    """Ring 2 orchestrator. Stateless -- safe to instantiate per request."""

    def __init__(
        self,
        registry: ArbiterRegistry,
        tier_router: TierRouter,
        consensus: DualRingConsensus,
    ):
        self.registry = registry
        self.tier_router = tier_router
        self.consensus = consensus

    @classmethod
    def from_defaults(cls) -> "ArbiterService":
        """Factory: returns service wired with default registry/router/consensus."""
        return cls(
            registry=get_default_registry(),
            tier_router=get_default_router(),
            consensus=get_default_consensus(),
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        task: Dict[str, Any],
        submission: Dict[str, Any],
    ) -> ArbiterVerdict:
        """Evaluate a submission and produce an ArbiterVerdict.

        Args:
            task: Task row from DB (must have 'category', 'bounty_usd', 'id')
            submission: Submission row from DB (must have 'evidence',
                        'auto_check_details', 'ai_verification_result')

        Returns:
            ArbiterVerdict ready for persistence and downstream processing.
        """
        start_time = time.monotonic()
        submission_id = submission.get("id", "")

        # 1. Lookup per-category config
        category = task.get("category", "")
        config = self.registry.get(category)

        # 2. Compute evidence hash (deterministic, on-chain auditable)
        evidence = submission.get("evidence") or {}
        evidence_hash = self._compute_evidence_hash(evidence)

        # 3. Build Ring 1 score from existing PHOTINT results
        ring1_score = self._build_ring1_score(submission)
        if ring1_score is None:
            # PHOTINT hasn't run yet -- can't evaluate. Return SKIPPED.
            logger.warning(
                "Submission %s has no PHOTINT results -- arbiter SKIPPED",
                submission.get("id"),
            )
            return self._skipped_verdict(task, evidence_hash, "PHOTINT not available")

        # 4. Route to inference tier based on bounty
        bounty_usd = float(task.get("bounty_usd", 0) or 0)
        tier_decision = self.tier_router.select_tier(
            bounty_usd=bounty_usd,
            config=config,
            is_disputed=bool(task.get("is_disputed", False)),
        )

        logger.info(
            "Arbiter routing for task %s: tier=%s reason=%s cost_cap=$%.4f",
            task.get("id"),
            tier_decision.tier.value,
            tier_decision.reason,
            tier_decision.max_cost_allowed_usd,
        )

        try:
            await emit_verification_event(
                submission_id,
                2,
                "tier_routing",
                "complete",
                {
                    "tier": tier_decision.tier.value,
                    "reason": tier_decision.reason,
                    "bounty": bounty_usd,
                },
            )
        except Exception:
            pass

        # 5. Run Ring 2 inference (depends on tier)
        # Phase 1 Task 1.6 will wire actual LLM calls here. For now, the
        # orchestration framework supports it but the inference call returns
        # an empty list -- the consensus engine handles CHEAP tier without
        # any Ring 2 scores.
        ring2_scores = await self._run_ring2_inferences(
            task=task,
            submission=submission,
            evidence=evidence,
            tier=tier_decision.tier,
            config=config,
            cost_cap_usd=tier_decision.max_cost_allowed_usd,
            submission_id=submission_id,
        )

        # 6. Combine via consensus engine
        consensus_result = self.consensus.decide(
            ring1_score=ring1_score,
            ring2_scores=ring2_scores,
            tier=tier_decision.tier,
            config=config,
        )

        try:
            await emit_verification_event(
                submission_id,
                2,
                "consensus",
                "complete",
                {
                    "decision": consensus_result.decision.value,
                    "score": round(consensus_result.aggregate_score, 4),
                    "confidence": round(consensus_result.confidence, 4),
                },
            )
        except Exception:
            pass

        # 7. Compute commitment hash for on-chain auditability
        commitment_hash = self._compute_commitment_hash(
            task_id=task.get("id", ""),
            decision=consensus_result.decision.value,
            ring1_score=ring1_score.score,
            ring2_scores=[rs.score for rs in ring2_scores],
        )

        # 8. Compute total cost from Ring 2 inferences.
        # Ring 2 providers report cost per-request via usage.total_cost.
        # Sum across all Ring 2 scores (0 for CHEAP tier).
        total_cost = 0.0
        for rs in ring2_scores:
            if rs.raw_response:
                # Cost is tracked in the Ring2Response, but RingScore doesn't
                # carry cost directly. For now, total_cost stays 0 until
                # InferenceLogger is wired (Phase 2 Task 2.8+).
                pass

        latency_ms = int((time.monotonic() - start_time) * 1000)

        verdict = ArbiterVerdict(
            decision=consensus_result.decision,
            tier=tier_decision.tier,
            aggregate_score=consensus_result.aggregate_score,
            confidence=consensus_result.confidence,
            evidence_hash=evidence_hash,
            commitment_hash=commitment_hash,
            ring_scores=[ring1_score, *ring2_scores],
            reason=consensus_result.reason,
            disagreement=consensus_result.disagreement,
            cost_usd=total_cost,
            latency_ms=latency_ms,
        )

        logger.info(
            "Arbiter verdict for task %s: decision=%s tier=%s score=%.3f conf=%.2f cost=$%.4f latency=%dms",
            task.get("id"),
            verdict.decision.value,
            verdict.tier.value,
            verdict.aggregate_score,
            verdict.confidence,
            verdict.cost_usd,
            verdict.latency_ms,
        )

        try:
            await emit_verification_event(
                submission_id,
                2,
                "ring2_complete",
                "complete",
                {
                    "verdict": verdict.decision.value,
                    "cost_usd": round(total_cost, 6),
                },
            )
        except Exception:
            pass

        return verdict

    # ------------------------------------------------------------------
    # Ring 1 (PHOTINT) score extraction
    # ------------------------------------------------------------------

    def _build_ring1_score(self, submission: Dict[str, Any]) -> Optional[RingScore]:
        """Extract a RingScore from existing PHOTINT results.

        Reads from submission.auto_check_details (Phase A, sync) and
        submission.ai_verification_result (Phase B, async). If Phase B
        hasn't run yet, falls back to Phase A only with conservative
        confidence reduction.
        """
        phase_a = submission.get("auto_check_details") or {}
        phase_b = submission.get("ai_verification_result") or {}

        phase_a_score = phase_a.get("score")
        phase_b_score = phase_b.get("score") if isinstance(phase_b, dict) else None

        # If neither phase has a score, we can't proceed
        if phase_a_score is None and phase_b_score is None:
            return None

        # Combine scores (reuses pipeline.py weights: A=0.50, B=0.50)
        if phase_a_score is not None and phase_b_score is not None:
            combined = (phase_a_score + phase_b_score) / 2.0
            confidence = 0.9
            reason = (
                f"PHOTINT A+B combined: A={phase_a_score:.2f}, B={phase_b_score:.2f}"
            )
        elif phase_a_score is not None:
            # Phase A only -- lower confidence (Phase B may flip the verdict)
            combined = phase_a_score
            confidence = 0.6
            reason = f"PHOTINT A only (Phase B pending): A={phase_a_score:.2f}"
        else:
            combined = phase_b_score
            confidence = 0.7
            reason = f"PHOTINT B only: B={phase_b_score:.2f}"

        # Decision label (informational; consensus engine recomputes)
        if combined >= 0.80:
            decision = "pass"
        elif combined <= 0.30:
            decision = "fail"
        else:
            decision = "inconclusive"

        return RingScore(
            ring="ring1",
            score=float(combined),
            decision=decision,
            confidence=confidence,
            provider="photint",
            model="phase_a+b",
            reason=reason,
        )

    # ------------------------------------------------------------------
    # Ring 2 inference (placeholder -- Task 1.6 will wire LLM calls)
    # ------------------------------------------------------------------

    async def _run_ring2_inferences(
        self,
        task: Dict[str, Any],
        submission: Dict[str, Any],
        evidence: Dict[str, Any],
        tier: ArbiterTier,
        config: ArbiterConfig,
        cost_cap_usd: float,
        submission_id: str = "",
    ) -> List[RingScore]:
        """Run Ring 2 LLM inference(s) based on tier.

        CHEAP: no LLM call (Ring 1 only).
        STANDARD: 1 LLM call via primary provider (ClawRouter > OpenRouter).
        MAX: 2 LLM calls from different providers (primary + secondary).

        Provider priority (per x402r arbiter research):
        - Primary: ClawRouter (USDC via x402) > OpenRouter (API key)
        - Secondary: EigenAI (verifiable) > OpenRouter (different model)
        """
        if tier == ArbiterTier.CHEAP:
            return []

        from .prompts import build_ring2_prompt
        from .providers import get_ring2_provider, get_ring2_secondary_provider

        # Extract Ring 1 score info for the prompt
        ring1_data = self._extract_ring1_for_prompt(submission)

        prompt = build_ring2_prompt(
            task=task,
            evidence=evidence,
            ring1_score=ring1_data.get("score"),
            ring1_confidence=ring1_data.get("confidence"),
            ring1_decision=ring1_data.get("decision"),
            ring1_reason=ring1_data.get("reason"),
        )

        scores: List[RingScore] = []

        # Primary provider (STANDARD + MAX)
        try:
            await emit_verification_event(
                submission_id,
                2,
                "llm_primary",
                "running",
                {"provider": "ring2_primary"},
            )
        except Exception:
            pass
        try:
            primary = get_ring2_provider()
            _t0 = time.monotonic()
            result = await primary.evaluate(prompt, tier)
            _latency = int((time.monotonic() - _t0) * 1000)
            scores.append(
                RingScore(
                    ring="ring2_primary",
                    score=result.confidence,
                    decision="pass" if result.completed else "fail",
                    confidence=result.confidence,
                    provider=result.provider,
                    model=result.model,
                    reason=result.reason,
                    raw_response=result.raw_response,
                )
            )
            logger.info(
                "Ring 2 primary: provider=%s model=%s completed=%s conf=%.2f cost=$%.4f",
                result.provider,
                result.model,
                result.completed,
                result.confidence,
                result.cost_usd,
            )
            try:
                await emit_verification_event(
                    submission_id,
                    2,
                    "llm_primary",
                    "complete",
                    {
                        "provider": result.provider,
                        "decision": "pass" if result.completed else "fail",
                        "score": round(result.confidence, 4),
                        "latency_ms": _latency,
                    },
                )
            except Exception:
                pass
        except Exception as e:
            logger.error("Ring 2 primary provider failed: %s", e)
            try:
                await emit_verification_event(
                    submission_id,
                    2,
                    "llm_primary",
                    "failed",
                    {"error": str(e)[:200]},
                )
            except Exception:
                pass

        # Secondary provider (MAX only -- dual consensus)
        if tier == ArbiterTier.MAX and scores:
            try:
                await emit_verification_event(
                    submission_id,
                    2,
                    "llm_secondary",
                    "running",
                    {"provider": "ring2_secondary"},
                )
            except Exception:
                pass
            try:
                secondary = get_ring2_secondary_provider()
                _t1 = time.monotonic()
                result2 = await secondary.evaluate(prompt, tier)
                _latency2 = int((time.monotonic() - _t1) * 1000)
                scores.append(
                    RingScore(
                        ring="ring2_secondary",
                        score=result2.confidence,
                        decision="pass" if result2.completed else "fail",
                        confidence=result2.confidence,
                        provider=result2.provider,
                        model=result2.model,
                        reason=result2.reason,
                        raw_response=result2.raw_response,
                    )
                )
                logger.info(
                    "Ring 2 secondary: provider=%s model=%s completed=%s conf=%.2f cost=$%.4f",
                    result2.provider,
                    result2.model,
                    result2.completed,
                    result2.confidence,
                    result2.cost_usd,
                )
                try:
                    await emit_verification_event(
                        submission_id,
                        2,
                        "llm_secondary",
                        "complete",
                        {
                            "provider": result2.provider,
                            "decision": "pass" if result2.completed else "fail",
                            "score": round(result2.confidence, 4),
                            "latency_ms": _latency2,
                        },
                    )
                except Exception:
                    pass
            except Exception as e:
                logger.error("Ring 2 secondary provider failed: %s", e)
                try:
                    await emit_verification_event(
                        submission_id,
                        2,
                        "llm_secondary",
                        "failed",
                        {"error": str(e)[:200]},
                    )
                except Exception:
                    pass

        if not scores:
            logger.warning(
                "All Ring 2 providers failed (tier=%s) -- gracefully degrading to CHEAP",
                tier.value,
            )

        return scores

    @staticmethod
    def _extract_ring1_for_prompt(submission: Dict[str, Any]) -> Dict[str, Any]:
        """Extract Ring 1 (PHOTINT) data for inclusion in Ring 2 prompt."""
        phase_a = submission.get("auto_check_details") or {}
        phase_b = submission.get("ai_verification_result") or {}

        score = phase_a.get("score")
        if isinstance(phase_b, dict) and phase_b.get("score") is not None:
            if score is not None:
                score = (score + phase_b["score"]) / 2.0
            else:
                score = phase_b["score"]

        decision = None
        if score is not None:
            if score >= 0.80:
                decision = "pass"
            elif score <= 0.30:
                decision = "fail"
            else:
                decision = "inconclusive"

        reason = phase_b.get("reason") or phase_a.get("reason") or None
        confidence = phase_b.get("confidence") or phase_a.get("confidence") or None

        return {
            "score": score,
            "confidence": confidence,
            "decision": decision,
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # Hash computation (audit trail)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_evidence_hash(evidence: Dict[str, Any]) -> str:
        """keccak256 of canonical JSON evidence payload.

        Uses sorted keys and stable separators for determinism. The hash
        is what gets posted on-chain (eventually) so the agent can prove
        what the arbiter actually evaluated.
        """
        canonical = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
        digest = Web3.keccak(text=canonical).hex()
        return digest if digest.startswith("0x") else f"0x{digest}"

    @staticmethod
    def _compute_commitment_hash(
        task_id: str,
        decision: str,
        ring1_score: float,
        ring2_scores: List[float],
    ) -> str:
        """keccak256 commitment over (task, decision, all ring scores).

        Mirrors verification.inference_logger.compute_commitment_hash but
        includes the full ring breakdown so the on-chain commitment proves
        the dual-ring vote, not just the final verdict.
        """
        parts = [
            f"task:{task_id}",
            f"decision:{decision}",
            f"ring1:{ring1_score:.6f}",
        ]
        for i, s in enumerate(ring2_scores):
            parts.append(f"ring2_{i}:{s:.6f}")
        raw = "|".join(parts)
        digest = Web3.keccak(text=raw).hex()
        return digest if digest.startswith("0x") else f"0x{digest}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _skipped_verdict(
        self,
        task: Dict[str, Any],
        evidence_hash: str,
        reason: str,
    ) -> ArbiterVerdict:
        """Build a SKIPPED verdict when arbiter cannot evaluate."""
        return ArbiterVerdict(
            decision=ArbiterDecision.SKIPPED,
            tier=ArbiterTier.CHEAP,
            aggregate_score=0.0,
            confidence=0.0,
            evidence_hash=evidence_hash,
            commitment_hash=self._compute_commitment_hash(
                task_id=task.get("id", ""),
                decision="skipped",
                ring1_score=0.0,
                ring2_scores=[],
            ),
            ring_scores=[],
            reason=reason,
            disagreement=False,
            cost_usd=0.0,
            latency_ms=0,
        )
