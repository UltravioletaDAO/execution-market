"""
Ring 2 End-to-End Integration Tests.

Full pipeline: evidence -> Ring 1 -> Ring 2 -> EvidenceScore -> verdict message.

Tests the FULL flow with mocked LLM providers (no real API calls).
Validates tier routing, cost controls, consensus logic, grade output,
and graceful degradation when Ring 2 providers fail.
"""

from unittest.mock import AsyncMock, patch

import pytest

from integrations.arbiter.consensus import DualRingConsensus
from integrations.arbiter.cost_tracker import (
    CostTracker,
)
from integrations.arbiter.messages import (
    build_verdict_message,
    extract_scoring_fields,
    score_to_grade,
)
from integrations.arbiter.providers import Ring2Response
from integrations.arbiter.registry import get_default_registry
from integrations.arbiter.service import ArbiterService
from integrations.arbiter.tier_router import TierRouter
from integrations.arbiter.types import (
    ArbiterDecision,
    ArbiterTier,
    CheckDetail,
    RingScore,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def arbiter():
    """ArbiterService with real registry/router/consensus (no mocks)."""
    return ArbiterService.from_defaults()


@pytest.fixture
def cost_tracker():
    """Fresh CostTracker with small budgets for test isolation.

    daily_budget=10.0 is high enough that per-caller tests hit per-caller
    limits before daily limits, while daily budget tests can set _daily_total
    directly.
    """
    import integrations.arbiter.cost_tracker as ct_mod

    # Reset global state
    ct_mod._daily_total = 0.0
    ct_mod._daily_date = ""
    ct_mod._per_caller.clear()
    return CostTracker(daily_budget=10.0, per_caller_budget=0.50)


def _make_task(bounty_usd: float, category: str = "physical_presence") -> dict:
    """Build a minimal task dict for arbiter evaluation."""
    return {
        "id": f"test-task-{bounty_usd}",
        "category": category,
        "bounty_usd": bounty_usd,
        "instructions": "Take a photo of the storefront.",
        "evidence_schema": {"required": ["photo"]},
    }


def _make_submission(
    photint_score: float | None = None,
    ai_score: float | None = None,
) -> dict:
    """Build a minimal submission dict with optional Ring 1 scores."""
    sub: dict = {
        "id": "test-sub-001",
        "evidence": {"photo": "https://cdn.example.com/photo.jpg"},
        "auto_check_details": None,
        "ai_verification_result": None,
    }
    if photint_score is not None:
        sub["auto_check_details"] = {"score": photint_score}
    if ai_score is not None:
        sub["ai_verification_result"] = {"score": ai_score}
    return sub


def _mock_ring2_response(
    completed: bool = True,
    confidence: float = 0.85,
    provider: str = "clawrouter",
    model: str = "anthropic/claude-haiku-4-5-20251001",
    cost_usd: float = 0.001,
) -> Ring2Response:
    """Build a mock Ring2Response."""
    return Ring2Response(
        completed=completed,
        confidence=confidence,
        reason="Evidence shows task completion"
        if completed
        else "Evidence insufficient",
        model=model,
        provider=provider,
        cost_usd=cost_usd,
        raw_response='{"completed": true}',
    )


# ---------------------------------------------------------------------------
# Test Class: Full Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.arbiter
class TestRing2EndToEnd:
    """Full pipeline: evidence -> Ring 1 -> Ring 2 -> EvidenceScore -> verdict message."""

    @pytest.mark.asyncio
    async def test_cheap_tier_ring1_only(self, arbiter):
        """Bounty < $1 with non-physical category: only Ring 1 runs, Ring 2 skipped.

        Note: physical_presence is in CATEGORIES_MIN_STANDARD so it gets promoted
        to STANDARD even on sub-$1 bounty. Use knowledge_access for a true CHEAP test.
        """
        task = _make_task(bounty_usd=0.50, category="knowledge_access")
        submission = _make_submission(photint_score=0.90)

        verdict = await arbiter.evaluate(task, submission)

        assert verdict.tier == ArbiterTier.CHEAP
        assert verdict.decision == ArbiterDecision.PASS
        assert verdict.aggregate_score >= 0.80
        # Only Ring 1 score, no Ring 2
        assert len(verdict.ring_scores) == 1
        assert verdict.ring_scores[0].ring == "ring1"
        assert verdict.cost_usd == 0.0

    @pytest.mark.asyncio
    async def test_standard_tier_both_rings(self, arbiter):
        """Bounty $1-$10: Ring 1 + Ring 2 primary model."""
        task = _make_task(bounty_usd=5.0)
        submission = _make_submission(photint_score=0.85)

        mock_response = _mock_ring2_response(completed=True, confidence=0.88)

        with patch(
            "integrations.arbiter.providers.get_ring2_provider"
        ) as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.evaluate.return_value = mock_response
            mock_get_provider.return_value = mock_provider

            verdict = await arbiter.evaluate(task, submission)

        assert verdict.tier == ArbiterTier.STANDARD
        # Ring 1 + 1 Ring 2 score
        assert len(verdict.ring_scores) == 2
        ring_names = [rs.ring for rs in verdict.ring_scores]
        assert "ring1" in ring_names
        assert "ring2_primary" in ring_names

    @pytest.mark.asyncio
    async def test_max_tier_dual_consensus(self, arbiter):
        """Bounty > $10: Ring 1 + Ring 2 primary + Ring 2 secondary."""
        task = _make_task(bounty_usd=15.0)
        submission = _make_submission(photint_score=0.90, ai_score=0.88)

        mock_primary = _mock_ring2_response(
            completed=True,
            confidence=0.92,
            provider="clawrouter",
            model="anthropic/claude-haiku-4-5-20251001",
        )
        mock_secondary = _mock_ring2_response(
            completed=True,
            confidence=0.87,
            provider="eigenai",
            model="eigenai/verifiable",
        )

        with (
            patch(
                "integrations.arbiter.providers.get_ring2_provider"
            ) as mock_get_primary,
            patch(
                "integrations.arbiter.providers.get_ring2_secondary_provider"
            ) as mock_get_secondary,
        ):
            primary_provider = AsyncMock()
            primary_provider.evaluate.return_value = mock_primary
            mock_get_primary.return_value = primary_provider

            secondary_provider = AsyncMock()
            secondary_provider.evaluate.return_value = mock_secondary
            mock_get_secondary.return_value = secondary_provider

            verdict = await arbiter.evaluate(task, submission)

        assert verdict.tier == ArbiterTier.MAX
        # Ring 1 + 2 Ring 2 scores = 3 total
        assert len(verdict.ring_scores) == 3
        ring_names = [rs.ring for rs in verdict.ring_scores]
        assert "ring1" in ring_names
        assert "ring2_primary" in ring_names
        assert "ring2_secondary" in ring_names

    @pytest.mark.asyncio
    async def test_ring2_failure_degrades_to_ring1(self, arbiter):
        """If Ring 2 provider fails, verdict still produced from Ring 1 only."""
        task = _make_task(bounty_usd=5.0)  # STANDARD tier
        submission = _make_submission(photint_score=0.90)

        with patch(
            "integrations.arbiter.providers.get_ring2_provider"
        ) as mock_get_provider:
            mock_provider = AsyncMock()
            mock_provider.evaluate.side_effect = RuntimeError("Provider unavailable")
            mock_get_provider.return_value = mock_provider

            verdict = await arbiter.evaluate(task, submission)

        # Graceful degradation: verdict produced from Ring 1 only
        assert verdict.decision in (
            ArbiterDecision.PASS,
            ArbiterDecision.INCONCLUSIVE,
        )
        # Only Ring 1 score (Ring 2 failed, no scores added)
        assert len(verdict.ring_scores) == 1
        assert verdict.ring_scores[0].ring == "ring1"

    def test_cost_cap_blocks_expensive_eval(self, cost_tracker):
        """Daily budget exceeded -> blocked."""
        import integrations.arbiter.cost_tracker as ct_mod

        # Spend up to the daily budget ($10.0 in test fixture)
        ct_mod._daily_total = 9.99
        ct_mod._daily_date = (
            __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .strftime("%Y-%m-%d")
        )

        can, reason = cost_tracker.can_spend(0.02, "external-agent-xyz")
        assert not can
        assert "Daily budget exceeded" in reason

    def test_per_eval_cap(self, cost_tracker):
        """Single eval exceeding MAX_PER_EVAL_USD is blocked."""
        can, reason = cost_tracker.can_spend(0.25, "any-caller")
        assert not can
        assert "Single eval exceeds cap" in reason

    def test_external_caller_capped_to_cheap(self):
        """No task_id -> bounty capped to $0.99 -> CHEAP tier.

        The AaaS endpoint caps bounty_usd to _EXTERNAL_BOUNTY_CAP_USD ($0.99)
        for external callers, forcing CHEAP tier routing (< $1 boundary).

        Note: uses knowledge_access because physical_presence is in
        CATEGORIES_MIN_STANDARD and would be promoted to STANDARD regardless
        of bounty amount.
        """
        from api.routers.arbiter_public import _EXTERNAL_BOUNTY_CAP_USD

        # External caller sends bounty=$100 but it gets capped to $0.99
        external_bounty = 100.0
        effective = min(external_bounty, _EXTERNAL_BOUNTY_CAP_USD)
        assert effective == 0.99

        # $0.99 bounty routes to CHEAP tier (< $1 threshold in tier router)
        router = TierRouter()
        registry = get_default_registry()
        config = registry.get("knowledge_access")
        decision = router.select_tier(
            bounty_usd=effective, config=config, is_disputed=False
        )
        assert decision.tier == ArbiterTier.CHEAP

    @pytest.mark.asyncio
    async def test_verdict_includes_grade_and_summary(self, arbiter):
        """Response includes grade, summary, check_details."""
        task = _make_task(bounty_usd=0.50)
        submission = _make_submission(photint_score=0.92)

        verdict = await arbiter.evaluate(task, submission)

        scoring = extract_scoring_fields(verdict)
        assert scoring["grade"] in ("A", "B", "C", "D", "F")
        assert scoring["summary"] is not None
        assert len(scoring["summary"]) > 0
        assert scoring["check_details"] is not None
        assert isinstance(scoring["check_details"], list)
        assert len(scoring["check_details"]) >= 1

        # Verify grade matches score
        expected_grade = score_to_grade(verdict.aggregate_score)
        assert scoring["grade"] == expected_grade

    @pytest.mark.asyncio
    async def test_hard_floor_tampering_fails(self):
        """Tampering score < 0.20 -> FAIL regardless of completion."""
        consensus = DualRingConsensus()
        registry = get_default_registry()
        config = registry.get("physical_presence")

        ring1 = RingScore(
            ring="ring1",
            score=0.85,  # High authenticity overall
            decision="pass",
            confidence=0.90,
            provider="photint",
        )

        # But tampering check is below hard floor
        tampering_check = CheckDetail(
            check="tampering",
            passed=False,
            score=0.10,  # Below 0.20 hard floor
            weight=0.30,
            details="Pixel manipulation detected",
            issues=["JPEG artifact anomaly"],
        )

        result = consensus.decide_v2(
            ring1_score=ring1,
            ring2_scores=[],
            tier=ArbiterTier.CHEAP,
            config=config,
            category="physical_presence",
            authenticity_checks=[tampering_check],
        )

        assert result.verdict == "fail"
        assert "hard floor" in result.summary.lower()
        assert len(result.rejection_reasons) > 0
        assert any("tampering" in r.lower() for r in result.rejection_reasons)

    @pytest.mark.asyncio
    async def test_anonymous_caller_low_budget(self, cost_tracker):
        """Anonymous callers get $1/day budget (ANONYMOUS_PER_CALLER_BUDGET_USD)."""
        import integrations.arbiter.cost_tracker as ct_mod

        # Reset state for this test
        ct_mod._daily_date = (
            __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .strftime("%Y-%m-%d")
        )

        # Spend under anonymous budget
        can, reason = cost_tracker.can_spend(0.003, "anonymous")
        assert can

        # Record some spend for anonymous
        cost_tracker.record_spend(0.95, "anonymous")

        # Now should be over anonymous budget ($1)
        can, reason = cost_tracker.can_spend(0.10, "anonymous")
        assert not can
        assert "Per-caller budget exceeded" in reason

    @pytest.mark.asyncio
    async def test_platform_agent_low_budget(self, cost_tracker):
        """Platform agent (2106) gets same low budget as anonymous."""
        import integrations.arbiter.cost_tracker as ct_mod

        ct_mod._daily_date = (
            __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .strftime("%Y-%m-%d")
        )

        cost_tracker.record_spend(0.99, "2106")
        can, reason = cost_tracker.can_spend(0.02, "2106")
        assert not can
        assert "Per-caller budget exceeded" in reason

    @pytest.mark.asyncio
    async def test_verdict_message_pass(self, arbiter):
        """PASS verdict produces readable message with grade."""
        task = _make_task(bounty_usd=0.50)
        submission = _make_submission(photint_score=0.95)

        verdict = await arbiter.evaluate(task, submission)
        message = build_verdict_message(verdict)

        assert "Verified" in message or "Score:" in message
        assert "Grade:" in message or "/100" in message

    @pytest.mark.asyncio
    async def test_verdict_message_fail(self, arbiter):
        """FAIL verdict produces readable message with fix suggestions."""
        task = _make_task(bounty_usd=0.50)
        submission = _make_submission(photint_score=0.15)

        verdict = await arbiter.evaluate(task, submission)
        message = build_verdict_message(verdict)

        assert "Rejected" in message or "Score:" in message

    @pytest.mark.asyncio
    async def test_cost_tracker_daily_reset(self, cost_tracker):
        """Cost tracker resets daily totals at midnight UTC."""
        import integrations.arbiter.cost_tracker as ct_mod

        # Set to yesterday
        ct_mod._daily_date = "2025-01-01"
        ct_mod._daily_total = 999.99
        ct_mod._per_caller["old-caller"] = 999.99

        # New day should reset
        can, reason = cost_tracker.can_spend(0.001, "new-caller")
        assert can
        assert ct_mod._daily_total == 0.0
        assert "old-caller" not in ct_mod._per_caller

    @pytest.mark.asyncio
    async def test_evidence_hash_deterministic(self, arbiter):
        """Same evidence produces same evidence_hash (idempotent)."""
        task = _make_task(bounty_usd=0.50)
        submission = _make_submission(photint_score=0.90)

        verdict1 = await arbiter.evaluate(task, submission)
        verdict2 = await arbiter.evaluate(task, submission)

        assert verdict1.evidence_hash == verdict2.evidence_hash
        assert verdict1.evidence_hash.startswith("0x")
