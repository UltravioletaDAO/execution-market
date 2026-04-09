"""
Dual-Ring Consensus Engine — Combines Ring 1 (PHOTINT) + Ring 2 (Arbiter) verdicts.

The consensus engine takes scores from both rings and decides PASS/FAIL/INCONCLUSIVE
based on tier-specific rules:

CHEAP tier:
    Only Ring 1 score available. Decision based on PHOTINT thresholds.

STANDARD tier:
    Ring 1 + 1 Ring 2 score (different provider). If they AGREE -> PASS or FAIL.
    If they DISAGREE -> INCONCLUSIVE (forces L2 escalation).

MAX tier:
    Ring 1 + 2 Ring 2 scores (3-way vote, different providers).
    3/3 PASS  -> PASS
    3/3 FAIL  -> FAIL
    2/3 PASS  -> INCONCLUSIVE (escalate, lower confidence)
    2/3 FAIL  -> FAIL (conservative)
    Divided   -> FAIL (conservative)
"""

import logging
from dataclasses import dataclass
from typing import List

from .types import ArbiterConfig, ArbiterDecision, ArbiterTier, RingScore

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    """Output of the consensus engine."""

    decision: ArbiterDecision
    aggregate_score: float  # Weighted combination of all ring scores
    confidence: float  # 0-1, lower if disagreement
    reason: str
    disagreement: bool  # True if rings did not agree (escalation flag)


class DualRingConsensus:
    """Combines Ring 1 + Ring 2 scores into a single arbiter decision.

    Stateless service. Per-category thresholds come from ArbiterConfig.
    Tier-specific logic comes from ArbiterTier on the verdict.
    """

    def decide(
        self,
        ring1_score: RingScore,
        ring2_scores: List[RingScore],
        tier: ArbiterTier,
        config: ArbiterConfig,
    ) -> ConsensusResult:
        """Combine ring scores into a final decision.

        Args:
            ring1_score: PHOTINT (Ring 1) verdict (always present)
            ring2_scores: List of Ring 2 verdicts (0 for CHEAP, 1 for STANDARD, 2 for MAX)
            tier: The tier that was used (determines logic path)
            config: Per-category thresholds

        Returns:
            ConsensusResult with PASS/FAIL/INCONCLUSIVE.
        """
        if tier == ArbiterTier.CHEAP:
            return self._decide_cheap(ring1_score, config)
        elif tier == ArbiterTier.STANDARD:
            if len(ring2_scores) != 1:
                logger.error(
                    "STANDARD tier expects 1 ring2 score, got %d -- falling back to cheap",
                    len(ring2_scores),
                )
                return self._decide_cheap(ring1_score, config)
            return self._decide_standard(ring1_score, ring2_scores[0], config)
        elif tier == ArbiterTier.MAX:
            if len(ring2_scores) != 2:
                logger.error(
                    "MAX tier expects 2 ring2 scores, got %d -- falling back to standard",
                    len(ring2_scores),
                )
                if len(ring2_scores) == 1:
                    return self._decide_standard(ring1_score, ring2_scores[0], config)
                return self._decide_cheap(ring1_score, config)
            return self._decide_max(
                ring1_score, ring2_scores[0], ring2_scores[1], config
            )
        else:
            raise ValueError(f"Unknown tier: {tier}")

    # ------------------------------------------------------------------
    # Tier-specific decision logic
    # ------------------------------------------------------------------

    def _decide_cheap(
        self,
        ring1: RingScore,
        config: ArbiterConfig,
    ) -> ConsensusResult:
        """CHEAP tier: route on PHOTINT score only, no Ring 2 inference."""
        score = ring1.score
        if score >= config.pass_threshold:
            return ConsensusResult(
                decision=ArbiterDecision.PASS,
                aggregate_score=score,
                confidence=ring1.confidence,
                reason=f"CHEAP: PHOTINT score {score:.2f} >= pass threshold {config.pass_threshold:.2f}",
                disagreement=False,
            )
        elif score <= config.fail_threshold:
            return ConsensusResult(
                decision=ArbiterDecision.FAIL,
                aggregate_score=score,
                confidence=ring1.confidence,
                reason=f"CHEAP: PHOTINT score {score:.2f} <= fail threshold {config.fail_threshold:.2f}",
                disagreement=False,
            )
        else:
            return ConsensusResult(
                decision=ArbiterDecision.INCONCLUSIVE,
                aggregate_score=score,
                confidence=ring1.confidence * 0.5,  # Low confidence in middle band
                reason=(
                    f"CHEAP: PHOTINT score {score:.2f} in inconclusive range "
                    f"({config.fail_threshold:.2f}-{config.pass_threshold:.2f})"
                ),
                disagreement=False,
            )

    def _decide_standard(
        self,
        ring1: RingScore,
        ring2: RingScore,
        config: ArbiterConfig,
    ) -> ConsensusResult:
        """STANDARD tier: Ring 1 + 1 Ring 2 inference. Both must agree."""
        ring1_pass = ring1.score >= config.pass_threshold
        ring2_pass = ring2.score >= config.pass_threshold
        ring1_fail = ring1.score <= config.fail_threshold
        ring2_fail = ring2.score <= config.fail_threshold

        # Weighted aggregate (equal weight for both rings in STANDARD)
        agg = (ring1.score + ring2.score) / 2.0
        avg_conf = (ring1.confidence + ring2.confidence) / 2.0

        # Both PASS -> PASS
        if ring1_pass and ring2_pass:
            return ConsensusResult(
                decision=ArbiterDecision.PASS,
                aggregate_score=agg,
                confidence=avg_conf * 1.1,  # Boost: independent agreement
                reason=f"STANDARD: both rings PASS (R1={ring1.score:.2f}, R2={ring2.score:.2f})",
                disagreement=False,
            )

        # Both FAIL -> FAIL
        if ring1_fail and ring2_fail:
            return ConsensusResult(
                decision=ArbiterDecision.FAIL,
                aggregate_score=agg,
                confidence=avg_conf * 1.1,
                reason=f"STANDARD: both rings FAIL (R1={ring1.score:.2f}, R2={ring2.score:.2f})",
                disagreement=False,
            )

        # Disagreement: one ring says PASS, the other says FAIL or vice versa
        if (ring1_pass and ring2_fail) or (ring1_fail and ring2_pass):
            return ConsensusResult(
                decision=ArbiterDecision.INCONCLUSIVE,
                aggregate_score=agg,
                confidence=avg_conf * 0.4,  # Strong disagreement -> very low confidence
                reason=(
                    f"STANDARD DISAGREEMENT: R1={ring1.score:.2f} ({ring1.decision}) "
                    f"vs R2={ring2.score:.2f} ({ring2.decision}) -- escalating to L2"
                ),
                disagreement=True,
            )

        # At least one ring is in the inconclusive middle band
        return ConsensusResult(
            decision=ArbiterDecision.INCONCLUSIVE,
            aggregate_score=agg,
            confidence=avg_conf * 0.6,
            reason=(
                f"STANDARD: at least one ring inconclusive "
                f"(R1={ring1.score:.2f}, R2={ring2.score:.2f}) -- escalating to L2"
            ),
            disagreement=False,
        )

    def _decide_max(
        self,
        ring1: RingScore,
        ring2_a: RingScore,
        ring2_b: RingScore,
        config: ArbiterConfig,
    ) -> ConsensusResult:
        """MAX tier: 3-way vote (Ring 1 + 2 Ring 2 inferences from different providers)."""
        scores = [ring1, ring2_a, ring2_b]
        votes_pass = sum(1 for s in scores if s.score >= config.pass_threshold)
        votes_fail = sum(1 for s in scores if s.score <= config.fail_threshold)

        agg = sum(s.score for s in scores) / 3.0
        avg_conf = sum(s.confidence for s in scores) / 3.0

        # 3/3 unanimous PASS -> high-confidence PASS
        if votes_pass == 3:
            return ConsensusResult(
                decision=ArbiterDecision.PASS,
                aggregate_score=agg,
                confidence=min(1.0, avg_conf * 1.2),  # Cap at 1.0
                reason=f"MAX: 3/3 PASS unanimous (R1={ring1.score:.2f}, R2A={ring2_a.score:.2f}, R2B={ring2_b.score:.2f})",
                disagreement=False,
            )

        # 3/3 unanimous FAIL -> high-confidence FAIL
        if votes_fail == 3:
            return ConsensusResult(
                decision=ArbiterDecision.FAIL,
                aggregate_score=agg,
                confidence=min(1.0, avg_conf * 1.2),
                reason=f"MAX: 3/3 FAIL unanimous (R1={ring1.score:.2f}, R2A={ring2_a.score:.2f}, R2B={ring2_b.score:.2f})",
                disagreement=False,
            )

        # 2/3 PASS -> INCONCLUSIVE (escalate, one ring disagrees)
        if votes_pass == 2:
            return ConsensusResult(
                decision=ArbiterDecision.INCONCLUSIVE,
                aggregate_score=agg,
                confidence=avg_conf * 0.7,
                reason=(
                    f"MAX: 2/3 PASS but one ring disagrees -- escalating to L2 "
                    f"(R1={ring1.score:.2f}, R2A={ring2_a.score:.2f}, R2B={ring2_b.score:.2f})"
                ),
                disagreement=True,
            )

        # 2/3 FAIL -> FAIL (conservative when in doubt about negative outcome)
        if votes_fail == 2:
            return ConsensusResult(
                decision=ArbiterDecision.FAIL,
                aggregate_score=agg,
                confidence=avg_conf * 0.8,
                reason=(
                    f"MAX: 2/3 FAIL (conservative refund) "
                    f"(R1={ring1.score:.2f}, R2A={ring2_a.score:.2f}, R2B={ring2_b.score:.2f})"
                ),
                disagreement=True,
            )

        # Divided: 1 pass, 1 fail, 1 inconclusive -- conservative refund
        return ConsensusResult(
            decision=ArbiterDecision.FAIL,
            aggregate_score=agg,
            confidence=avg_conf * 0.5,
            reason=(
                f"MAX: divided vote (no majority) -- conservative refund "
                f"(R1={ring1.score:.2f}, R2A={ring2_a.score:.2f}, R2B={ring2_b.score:.2f})"
            ),
            disagreement=True,
        )


def get_default_consensus() -> DualRingConsensus:
    """Factory: stateless, no config needed."""
    return DualRingConsensus()
