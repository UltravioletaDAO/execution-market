"""
Ring 2 — Decentralized Arbiter Service

Independent semantic verification layer that complements PHOTINT (Ring 1).
While Ring 1 asks "Is this evidence authentic?", Ring 2 asks "Does this
evidence prove the task was completed as requested?".

The two rings run independent inference (different prompts, optionally
different providers) and combine verdicts via a tier-aware consensus engine.

Architecture:
- service.py    -- ArbiterService (entry point, orchestration)
- registry.py   -- ArbiterRegistry (per-category thresholds + config)
- tier_router.py -- TierRouter (bounty -> inference strategy)
- consensus.py  -- DualRingConsensus (combines Ring 1 + Ring 2 verdicts)
- prompts/      -- 21 category-specific semantic prompts (Phase 1 Task 1.6)
- processor.py  -- process_arbiter_verdict (Phase 2: release/refund dispatch)
- escalation.py -- L2 human arbiter escalation (Phase 2)

See: docs/planning/MASTER_PLAN_COMMERCE_SCHEME_ARBITER.md
"""

from .types import (
    ArbiterDecision,
    ArbiterTier,
    ArbiterVerdict,
    CheckDetail,
    EvidenceScore,
)

__all__ = [
    "ArbiterDecision",
    "ArbiterTier",
    "ArbiterVerdict",
    "CheckDetail",
    "EvidenceScore",
]
