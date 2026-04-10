"""
Arbiter-as-a-Service (AaaS) — Public Ring 2 evaluation endpoint.

Part of Phase 5 of the commerce scheme + arbiter integration.

Exposes the Ring 2 ArbiterService as a standalone public endpoint so
OTHER marketplaces can use EM's dual-inference verification without
implementing their own AI layer.

Endpoint:
    POST /api/v1/arbiter/verify

Request:
    {
      "evidence": {...},         # Evidence payload to evaluate
      "task_schema": {            # What the task requires
        "category": "physical_presence",
        "instructions": "...",
        "required_fields": ["photo", "gps"]
      },
      "bounty_usd": 5.0,          # Used for tier routing + cost cap
      "photint_score": 0.85       # Optional: caller-provided Ring 1 score
                                  # (caller runs their own PHOTINT)
    }

Response:
    {
      "verdict": "pass" | "fail" | "inconclusive",
      "tier": "cheap" | "standard" | "max",
      "aggregate_score": 0.87,
      "confidence": 0.82,
      "evidence_hash": "0x...",
      "commitment_hash": "0x...",
      "reason": "...",
      "ring_scores": [...],
      "disagreement": false,
      "cost_usd": 0.001,
      "latency_ms": 2400
    }

Pricing:
    Free for EM's own tasks (internal). For external callers, this is
    protected by a per-caller rate limit (100 req/min per API key) and
    will eventually be paywalled via x402 commerce scheme (Phase 5+).

Auth:
    Requires an API key (free tier: 100/min) OR ERC-8128 wallet signature.
"""

import logging
import os
import uuid as _uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from integrations.arbiter.config import is_arbiter_enabled
from integrations.arbiter.service import ArbiterService
from integrations.arbiter.types import ArbiterDecision

from ..auth import AgentAuth, verify_agent_auth_write

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/arbiter", tags=["Arbiter-as-a-Service"])


# ============================================================================
# Phase 0 GR-0.2: hard kill-switch for Arbiter-as-a-Service
# ============================================================================
#
# Ring 2 LLM inference is currently a STUB (AI-001) that returns []. The
# AaaS endpoint is therefore "dual-inference" in name only. Additionally:
#
#   * Auth is anonymous-callable via the verify_agent_auth fallback path
#     (Track A is hardening that).
#   * bounty_usd is caller-controlled with no daily spend cap (AI-003, AI-004).
#   * Prompt injection is trivial via task_schema.instructions (AI-006).
#   * There is no kill switch for arbiter auto-release (AI-005 — see
#     processor.py for its sibling gate).
#
# Until Phase 1 guardrails land (real LLM wiring, daily budget enforcement,
# prompt hardening, authenticated callers), both the /verify and /status
# endpoints are hard-disabled by default. Flip EM_AAAS_ENABLED=true ONLY
# for internal testing.
#
# Default is False. Missing env var == disabled. See
# docs/reports/security-audit-2026-04-07/specialists/SC_03_AI_REDTEAM.md.
def _aaas_enabled() -> bool:
    """Read the AaaS master kill-switch at call time.

    Reading at call time (instead of at import time) makes the flag
    testable via monkeypatching os.environ inside a single test process.
    """
    return os.environ.get("EM_AAAS_ENABLED", "false").strip().lower() == "true"


_AAAS_DISABLED_DETAIL = (
    "Arbiter-as-a-Service is disabled on this deployment. "
    "See https://execution.market/skill.md for updates."
)


# ============================================================================
# Request / Response Models
# ============================================================================


class TaskSchema(BaseModel):
    """Minimal task description the arbiter needs to evaluate evidence."""

    category: str = Field(
        default="general",
        description="Task category (maps to per-category thresholds)",
        max_length=50,
    )
    instructions: Optional[str] = Field(
        default=None, description="Human-readable task instructions", max_length=5000
    )
    required_fields: Optional[list[str]] = Field(
        default=None, description="Evidence schema required fields"
    )


class ArbiterVerifyRequest(BaseModel):
    """Public AaaS request body."""

    evidence: Dict[str, Any] = Field(
        ..., description="Evidence payload to evaluate (arbitrary dict)"
    )
    task_schema: TaskSchema = Field(..., description="Task description")
    bounty_usd: float = Field(
        default=0.0,
        ge=0,
        le=10000,
        description="Task bounty (drives tier routing and cost cap)",
    )
    photint_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Optional caller-provided Ring 1 (PHOTINT) score",
    )
    photint_confidence: Optional[float] = Field(
        default=None, ge=0, le=1, description="Optional Ring 1 confidence"
    )


class RingScoreResponse(BaseModel):
    ring: str
    score: float
    decision: str
    confidence: float
    provider: Optional[str] = None
    model: Optional[str] = None
    reason: Optional[str] = None


class ArbiterVerifyResponse(BaseModel):
    """Public AaaS response body."""

    verdict: str
    tier: str
    aggregate_score: float
    confidence: float
    evidence_hash: str
    commitment_hash: str
    reason: Optional[str]
    ring_scores: list[RingScoreResponse]
    disagreement: bool
    cost_usd: float
    latency_ms: int


# ============================================================================
# Rate limiting (in-memory for MVP; Redis for production)
# ============================================================================

# Per-caller rate limit: 100 req/min
RATE_LIMIT_MAX_PER_MINUTE = 100
_rate_limit_buckets: Dict[str, list] = {}


def _check_rate_limit(caller_id: str) -> None:
    """Simple sliding-window rate limiter (100 req/min).

    For MVP only -- replace with Redis-backed limiter for production
    horizontal scaling.
    """
    import time

    now = time.time()
    cutoff = now - 60.0
    bucket = _rate_limit_buckets.setdefault(caller_id, [])
    # Drop old entries
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= RATE_LIMIT_MAX_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_MAX_PER_MINUTE} req/min",
        )
    bucket.append(now)


# ============================================================================
# Main endpoint
# ============================================================================


@router.post("/verify", response_model=ArbiterVerifyResponse)
async def verify_evidence(
    body: ArbiterVerifyRequest,
    auth: AgentAuth = Depends(verify_agent_auth_write),
) -> ArbiterVerifyResponse:
    """Run Ring 2 arbiter evaluation on arbitrary evidence.

    This is the public Arbiter-as-a-Service endpoint. External marketplaces
    can POST evidence payloads and receive a dual-inference verdict they
    can use to drive their own payment flows.

    The caller must provide either:
      1. A pre-computed PHOTINT score in `photint_score` (if they ran
         their own Ring 1), OR
      2. Evidence that the arbiter's CHEAP tier can evaluate without
         running LLM inference.

    Tier is determined by bounty_usd:
      - bounty < $1   -> CHEAP  ($0 cost)
      - bounty < $10  -> STANDARD (~$0.001)
      - bounty >= $10 -> MAX (~$0.003)

    Cost cap: max 10% of bounty_usd.

    Returns verdict, confidence, cryptographic hashes (keccak256), and
    ring breakdown. Idempotent: same inputs -> same evidence_hash.
    """
    # 0. Phase 0 GR-0.2: hard kill-switch — disabled by default until
    #    Phase 1 guardrails land (Ring 2 wiring, daily budget, prompt
    #    injection defenses, authenticated callers). This MUST be the
    #    first check so unauthenticated callers can't probe deeper.
    if not _aaas_enabled():
        raise HTTPException(
            status_code=503,
            detail=_AAAS_DISABLED_DETAIL,
        )

    # 1. Master switch check
    if not await is_arbiter_enabled():
        raise HTTPException(
            status_code=503,
            detail="Arbiter service is not enabled on this deployment",
        )

    # 2. Rate limiting per caller
    caller_id = getattr(auth, "wallet_address", None) or auth.agent_id or "anonymous"
    _check_rate_limit(caller_id)

    # 3. Build synthetic task + submission dicts that ArbiterService expects
    #    The AaaS path doesn't hit the DB -- we feed the service inline data.
    task = {
        "id": f"aaas-{caller_id}-{int(body.bounty_usd * 1000)}",
        "category": body.task_schema.category,
        "bounty_usd": body.bounty_usd,
        "instructions": body.task_schema.instructions or "",
        "evidence_schema": {
            "required": body.task_schema.required_fields or [],
        },
    }
    submission = {
        "id": f"aaas-sub-{caller_id}",
        "evidence": body.evidence,
        "auto_check_details": (
            {"score": body.photint_score} if body.photint_score is not None else None
        ),
        "ai_verification_result": None,
    }

    # 4. Run the arbiter
    try:
        arbiter = ArbiterService.from_defaults()
        verdict = await arbiter.evaluate(task, submission)
    except Exception:
        req_id = str(_uuid.uuid4())[:8]
        logger.exception(
            "AaaS evaluation failed for caller %s [req=%s]", caller_id, req_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Arbiter evaluation failed (ref: {req_id})",
        )

    # 5. Handle SKIPPED (caller didn't provide enough signal)
    if verdict.decision == ArbiterDecision.SKIPPED:
        raise HTTPException(
            status_code=400,
            detail=(
                "Arbiter cannot evaluate without a photint_score or cached "
                "verification result. Provide photint_score in the request body."
            ),
        )

    # 6. Serialize for the response
    return ArbiterVerifyResponse(
        verdict=verdict.decision.value,
        tier=verdict.tier.value,
        aggregate_score=round(verdict.aggregate_score, 4),
        confidence=round(verdict.confidence, 4),
        evidence_hash=verdict.evidence_hash,
        commitment_hash=verdict.commitment_hash,
        reason=verdict.reason,
        ring_scores=[
            RingScoreResponse(
                ring=rs.ring,
                score=round(float(rs.score), 4),
                decision=rs.decision,
                confidence=round(float(rs.confidence), 4),
                provider=rs.provider,
                model=rs.model,
                reason=rs.reason[:500] if rs.reason else None,
            )
            for rs in verdict.ring_scores
        ],
        disagreement=verdict.disagreement,
        cost_usd=round(verdict.cost_usd, 6),
        latency_ms=verdict.latency_ms,
    )


# ============================================================================
# Health / metadata endpoint
# ============================================================================


class ArbiterStatusResponse(BaseModel):
    enabled: bool
    tier_thresholds: Dict[str, float]
    supported_categories: list[str]
    cost_model: Dict[str, Any]


@router.get("/status", response_model=ArbiterStatusResponse)
async def arbiter_status() -> ArbiterStatusResponse:
    """Public status endpoint: is the arbiter available, what are its
    thresholds, what categories are supported, and how does pricing work.

    No authentication required -- intended for service discovery.
    """
    # Phase 0 GR-0.2: do NOT leak the presence of the arbiter endpoint
    # while the service is kill-switched. Return 503 with the same
    # detail as /verify so probes see a consistent disabled surface.
    if not _aaas_enabled():
        raise HTTPException(
            status_code=503,
            detail=_AAAS_DISABLED_DETAIL,
        )

    from integrations.arbiter.config import get_cost_controls, get_tier_boundaries
    from integrations.arbiter.registry import get_default_registry

    tiers = await get_tier_boundaries()
    costs = await get_cost_controls()
    registry = get_default_registry()

    return ArbiterStatusResponse(
        enabled=await is_arbiter_enabled(),
        tier_thresholds={
            "cheap_max_usd": float(tiers["cheap_max"]),
            "standard_max_usd": float(tiers["standard_max"]),
        },
        supported_categories=registry.all_categories(),
        cost_model={
            "cheap_cost_usd": 0.0,
            "standard_cost_usd": 0.001,
            "max_cost_usd": 0.003,
            "hard_cap_per_eval_usd": float(costs["max_per_eval_usd"]),
            "max_pct_of_bounty": float(costs["bounty_ratio_max"]),
            "rate_limit_per_minute": RATE_LIMIT_MAX_PER_MINUTE,
        },
    )
