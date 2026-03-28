"""
Multi-Model Consensus Verification

For high-value tasks (bounty > $10) or disputed submissions, runs
verification through 2 different models and requires agreement.

Both approve → approved (high confidence)
Both reject → rejected (high confidence)
Disagree → needs_human (flag for agent review)

Part of PHOTINT Verification Overhaul (Phase 4).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    """Result of multi-model consensus verification."""

    decision: str  # "approved", "rejected", "needs_human"
    confidence: float
    explanation: str
    models_used: List[str]
    model_decisions: List[dict]
    consensus_reached: bool


async def run_consensus_verification(
    task: dict,
    evidence: dict,
    photo_urls: List[str],
    exif_context: str = "",
    rekognition_context: str = "",
) -> ConsensusResult:
    """
    Run verification through 2 different models and check for agreement.

    Uses Tier 2 and Tier 3 models from different providers for diversity.
    """
    from .ai_review import AIVerifier
    from .providers import get_provider_for_tier

    # Get two different providers
    provider_a = get_provider_for_tier("tier_2")
    provider_b = get_provider_for_tier("tier_3")

    if not provider_a and not provider_b:
        return ConsensusResult(
            decision="needs_human",
            confidence=0.0,
            explanation="No providers available for consensus verification",
            models_used=[],
            model_decisions=[],
            consensus_reached=False,
        )

    # If only one provider available, use it as single source
    if not provider_b:
        provider_b = get_provider_for_tier(
            "tier_2", exclude_providers=[provider_a.name]
        )

    # Run both in parallel
    async def _verify(provider):
        if provider is None:
            return None
        verifier = AIVerifier(provider=provider)
        return await verifier.verify_evidence(
            task=task,
            evidence=evidence,
            photo_urls=photo_urls,
            exif_context=exif_context,
            rekognition_context=rekognition_context,
        )

    results = await asyncio.gather(
        _verify(provider_a),
        _verify(provider_b),
        return_exceptions=True,
    )

    # Collect valid results
    valid_results = []
    model_decisions = []
    models_used = []

    for r in results:
        if isinstance(r, Exception) or r is None:
            continue
        valid_results.append(r)
        models_used.append(f"{r.provider}/{r.model}")
        model_decisions.append(
            {
                "provider": r.provider,
                "model": r.model,
                "decision": r.decision.value,
                "confidence": r.confidence,
                "explanation": r.explanation,
            }
        )

    if len(valid_results) < 2:
        # Only one model responded — use its decision
        if valid_results:
            r = valid_results[0]
            return ConsensusResult(
                decision=r.decision.value,
                confidence=r.confidence * 0.8,  # Reduce confidence for single model
                explanation=f"Single model ({r.provider}/{r.model}): {r.explanation}",
                models_used=models_used,
                model_decisions=model_decisions,
                consensus_reached=False,
            )
        return ConsensusResult(
            decision="needs_human",
            confidence=0.0,
            explanation="No models responded for consensus",
            models_used=[],
            model_decisions=[],
            consensus_reached=False,
        )

    # Check consensus
    d1 = valid_results[0].decision
    d2 = valid_results[1].decision
    c1 = valid_results[0].confidence
    c2 = valid_results[1].confidence

    if d1 == d2:
        # Agreement
        avg_confidence = (c1 + c2) / 2
        return ConsensusResult(
            decision=d1.value,
            confidence=min(avg_confidence * 1.1, 1.0),  # Boost for agreement
            explanation=f"Consensus ({models_used[0]} + {models_used[1]}): {valid_results[0].explanation}",
            models_used=models_used,
            model_decisions=model_decisions,
            consensus_reached=True,
        )
    else:
        # Disagreement — defer to human
        return ConsensusResult(
            decision="needs_human",
            confidence=max(c1, c2) * 0.5,  # Low confidence on disagreement
            explanation=(
                f"Models disagree: {models_used[0]}={d1.value} vs "
                f"{models_used[1]}={d2.value}. Requires agent review."
            ),
            models_used=models_used,
            model_decisions=model_decisions,
            consensus_reached=False,
        )
