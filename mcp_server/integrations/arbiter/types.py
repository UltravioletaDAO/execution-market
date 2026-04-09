"""
Arbiter Types — Verdict, Decision, Tier dataclasses.

Shared types used across the arbiter module. Kept in a separate file
to avoid circular imports between service.py, consensus.py, and processor.py.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ArbiterDecision(str, Enum):
    """Final verdict from Ring 2 arbiter (or dual-ring consensus)."""

    PASS = "pass"  # Evidence accepted -> trigger release
    FAIL = "fail"  # Evidence rejected -> trigger refund
    INCONCLUSIVE = "inconclusive"  # Cannot decide -> escalate to L2 human
    SKIPPED = "skipped"  # Arbiter not run (manual mode, disabled, etc.)


class ArbiterTier(str, Enum):
    """Inference strategy selected by bounty value.

    Cheap:    no Ring 2 LLM call, route on PHOTINT score only
    Standard: 1 Ring 2 LLM call (different provider when possible)
    Max:      2 Ring 2 LLM calls from different providers + 3-way consensus
    """

    CHEAP = "cheap"
    STANDARD = "standard"
    MAX = "max"


@dataclass
class RingScore:
    """Score from a single ring (Ring 1 PHOTINT or a Ring 2 inference)."""

    ring: str  # "ring1" | "ring2_a" | "ring2_b"
    score: float  # 0.0 - 1.0
    decision: str  # "pass" | "fail" | "inconclusive"
    confidence: float  # 0.0 - 1.0
    provider: Optional[str] = None  # e.g., "anthropic"
    model: Optional[str] = None  # e.g., "claude-haiku-4-5-20251001"
    reason: Optional[str] = None
    raw_response: Optional[str] = None
    inference_id: Optional[str] = None  # FK into verification_inferences table


@dataclass
class ArbiterVerdict:
    """Final verdict produced by ArbiterService.evaluate().

    This is what gets persisted to submissions.arbiter_* columns and
    consumed by the verdict processor (Phase 2) to trigger release/refund.
    """

    # Core decision
    decision: ArbiterDecision
    tier: ArbiterTier
    aggregate_score: float  # Combined Ring 1 + Ring 2 score (0.0 - 1.0)
    confidence: float  # Confidence in the decision (0.0 - 1.0)

    # Provenance and audit trail
    evidence_hash: str  # keccak256 of canonical evidence payload
    commitment_hash: str  # keccak256 of (task_id, decision, scores) for on-chain proof
    ring_scores: List[RingScore] = field(default_factory=list)

    # Metadata
    reason: Optional[str] = None  # Human-readable explanation
    disagreement: bool = False  # True if rings disagreed (forces L2 escalation)
    cost_usd: float = 0.0  # Total LLM cost for Ring 2 inferences (0 for cheap tier)
    latency_ms: int = 0  # Total wall-clock time for evaluation
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for JSONB storage in submissions.arbiter_verdict_data.

        Sanitizes RingScore.raw_response (truncated to 500 chars) and
        RingScore.reason (truncated to 500 chars) to keep JSONB rows small
        and avoid storing arbitrary LLM output blobs in DB rows.
        """
        return {
            "decision": self.decision.value,
            "tier": self.tier.value,
            "aggregate_score": round(self.aggregate_score, 4),
            "confidence": round(self.confidence, 4),
            "evidence_hash": self.evidence_hash,
            "commitment_hash": self.commitment_hash,
            "ring_scores": [
                {
                    "ring": rs.ring,
                    "score": round(float(rs.score), 4),
                    "decision": rs.decision,
                    "confidence": round(float(rs.confidence), 4),
                    "provider": rs.provider,
                    "model": rs.model,
                    "reason": (rs.reason[:500] if rs.reason else None),
                    "inference_id": rs.inference_id,
                    # raw_response intentionally excluded -- audit trail lives in
                    # the verification_inferences table, not in JSONB rows.
                }
                for rs in self.ring_scores
            ],
            "reason": (self.reason[:500] if self.reason else None),
            "disagreement": self.disagreement,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": self.latency_ms,
            "evaluated_at": self.evaluated_at.isoformat(),
        }

    @property
    def is_pass(self) -> bool:
        return self.decision == ArbiterDecision.PASS

    @property
    def is_fail(self) -> bool:
        return self.decision == ArbiterDecision.FAIL

    @property
    def needs_escalation(self) -> bool:
        return self.decision == ArbiterDecision.INCONCLUSIVE


@dataclass
class ArbiterConfig:
    """Per-category thresholds and inference settings.

    Loaded from registry.py CATEGORY_CONFIGS dict, override-able via
    PlatformConfig at runtime.
    """

    category: str
    pass_threshold: float = 0.80  # Min aggregate_score for PASS
    fail_threshold: float = 0.30  # Max aggregate_score for FAIL
    requires_photo: bool = False
    requires_gps: bool = False
    max_tier: ArbiterTier = ArbiterTier.MAX  # Cap on inference strategy
    consensus_required: bool = False  # Force MAX tier even on low bounty

    # Cost controls
    max_cost_per_eval_usd: float = 0.20  # Hard cap, enforced before model_router call
    cost_to_bounty_ratio_max: float = 0.10  # Cost <= 10% of bounty
