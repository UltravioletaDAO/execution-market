"""
Unit tests for Ring 2 Arbiter Service + Registry + TierRouter + Consensus.

Covers Phase 1 of the commerce scheme + arbiter integration:
- ArbiterService.evaluate() dual-ring orchestration
- ArbiterRegistry category routing (21 categories)
- TierRouter bounty-based tier selection + cost caps
- DualRingConsensus decision logic (cheap/standard/max)
- ArbiterVerdict serialization + commitment hashing

All tests use mocked PHOTINT data -- no real LLM calls.

Run:
    pytest -m arbiter
"""

from decimal import Decimal

import pytest

from integrations.arbiter.consensus import DualRingConsensus
from integrations.arbiter.registry import (
    CATEGORY_CONFIGS,
    GENERIC_FALLBACK,
    get_default_registry,
)
from integrations.arbiter.service import ArbiterService
from integrations.arbiter.tier_router import TierRouter
from integrations.arbiter.types import (
    ArbiterConfig,
    ArbiterDecision,
    ArbiterTier,
    ArbiterVerdict,
    RingScore,
)

pytestmark = pytest.mark.arbiter


# ============================================================================
# ArbiterRegistry tests
# ============================================================================


class TestArbiterRegistry:
    """Category routing and config lookup."""

    def test_registry_has_all_21_categories(self):
        """Every TaskCategory in models.py must have a config."""
        reg = get_default_registry()
        expected = {
            "physical_presence",
            "simple_action",
            "location_based",
            "digital_physical",
            "sensory",
            "social",
            "creative",
            "emergency",
            "knowledge_access",
            "human_authority",
            "bureaucratic",
            "verification",
            "social_proof",
            "data_collection",
            "proxy",
            "data_processing",
            "api_integration",
            "content_generation",
            "code_execution",
            "research",
            "multi_step_workflow",
        }
        assert set(reg.all_categories()) == expected
        assert len(reg.all_categories()) == 21

    def test_registry_fallback_unknown_category(self):
        reg = get_default_registry()
        config = reg.get("nonexistent_category")
        assert config is GENERIC_FALLBACK
        assert config.pass_threshold == 0.85
        assert config.fail_threshold == 0.25

    def test_registry_empty_category_uses_fallback(self):
        reg = get_default_registry()
        assert reg.get("") is GENERIC_FALLBACK
        assert reg.get(None) is GENERIC_FALLBACK

    def test_high_stakes_categories_force_consensus(self):
        """human_authority, bureaucratic, emergency must always force MAX tier."""
        reg = get_default_registry()
        forced = set(reg.consensus_required_categories())
        assert "human_authority" in forced
        assert "bureaucratic" in forced
        assert "emergency" in forced
        # Default physical_presence does NOT force consensus
        assert "physical_presence" not in forced

    def test_physical_categories_require_gps(self):
        reg = get_default_registry()
        assert reg.get("physical_presence").requires_gps is True
        assert reg.get("location_based").requires_gps is True
        # Digital-only categories do not
        assert reg.get("data_processing").requires_photo is False


# ============================================================================
# TierRouter tests
# ============================================================================


class TestTierRouter:
    """Bounty -> tier selection + cost cap enforcement."""

    def _config(self, **overrides):
        defaults = dict(
            category="test",
            pass_threshold=0.80,
            fail_threshold=0.30,
            requires_photo=False,
            requires_gps=False,
            max_tier=ArbiterTier.MAX,
            consensus_required=False,
            max_cost_per_eval_usd=0.20,
            cost_to_bounty_ratio_max=0.10,
        )
        defaults.update(overrides)
        return ArbiterConfig(**defaults)

    def test_cheap_tier_for_low_bounty(self):
        router = TierRouter()
        decision = router.select_tier(bounty_usd=0.10, config=self._config())
        assert decision.tier == ArbiterTier.CHEAP

    def test_standard_tier_for_mid_bounty(self):
        router = TierRouter()
        decision = router.select_tier(bounty_usd=5.0, config=self._config())
        assert decision.tier == ArbiterTier.STANDARD

    def test_max_tier_for_high_bounty(self):
        router = TierRouter()
        decision = router.select_tier(bounty_usd=50.0, config=self._config())
        assert decision.tier == ArbiterTier.MAX

    def test_disputed_forces_max_tier(self):
        """Any disputed submission bypasses the bounty-based routing."""
        router = TierRouter()
        # Low bounty, but disputed -> MAX
        decision = router.select_tier(
            bounty_usd=0.10, config=self._config(), is_disputed=True
        )
        assert decision.tier == ArbiterTier.MAX

    def test_consensus_required_forces_max(self):
        """Categories with consensus_required=True always get MAX tier."""
        router = TierRouter()
        config = self._config(consensus_required=True)
        decision = router.select_tier(bounty_usd=0.10, config=config)
        assert decision.tier == ArbiterTier.MAX

    def test_max_tier_cap_respected(self):
        """A category with max_tier=STANDARD never gets MAX."""
        router = TierRouter()
        config = self._config(max_tier=ArbiterTier.STANDARD)
        decision = router.select_tier(bounty_usd=100.0, config=config)
        assert decision.tier == ArbiterTier.STANDARD

    def test_cost_cap_is_ten_percent_of_bounty(self):
        router = TierRouter()
        decision = router.select_tier(bounty_usd=5.0, config=self._config())
        # 10% of $5 = $0.50, capped at absolute $0.20 -> $0.20
        assert decision.max_cost_allowed_usd == 0.20
        # 10% of $1 = $0.10 < absolute $0.20 -> $0.10
        decision = router.select_tier(bounty_usd=1.0, config=self._config())
        assert decision.max_cost_allowed_usd == pytest.approx(0.10)

    def test_negative_bounty_clamps_to_zero(self):
        """Defensive: negative bounty should not produce negative cap."""
        router = TierRouter()
        decision = router.select_tier(bounty_usd=-50.0, config=self._config())
        assert decision.tier == ArbiterTier.CHEAP
        assert decision.max_cost_allowed_usd == 0.0

    def test_none_bounty_clamps_to_zero(self):
        router = TierRouter()
        decision = router.select_tier(bounty_usd=None, config=self._config())
        assert decision.tier == ArbiterTier.CHEAP
        assert decision.max_cost_allowed_usd == 0.0

    def test_custom_tier_boundaries(self):
        """PlatformConfig can override tier thresholds."""
        router = TierRouter(
            cheap_max_usd=Decimal("0.50"),
            standard_max_usd=Decimal("5.00"),
        )
        # Bounty $0.60 is now STANDARD (not CHEAP)
        decision = router.select_tier(bounty_usd=0.60, config=self._config())
        assert decision.tier == ArbiterTier.STANDARD


# ============================================================================
# DualRingConsensus tests
# ============================================================================


class TestDualRingConsensus:
    """Tier-specific decision logic."""

    def _config(self):
        return ArbiterConfig(
            category="test",
            pass_threshold=0.80,
            fail_threshold=0.30,
        )

    def _ring(self, ring, score, decision="pass", confidence=0.85):
        return RingScore(
            ring=ring,
            score=score,
            decision=decision,
            confidence=confidence,
            provider="test",
            model="test",
        )

    def test_cheap_pass(self):
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.92),
            ring2_scores=[],
            tier=ArbiterTier.CHEAP,
            config=self._config(),
        )
        assert result.decision == ArbiterDecision.PASS
        assert result.aggregate_score == 0.92
        assert result.disagreement is False

    def test_cheap_fail(self):
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.15),
            ring2_scores=[],
            tier=ArbiterTier.CHEAP,
            config=self._config(),
        )
        assert result.decision == ArbiterDecision.FAIL

    def test_cheap_inconclusive_middle_band(self):
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.55),
            ring2_scores=[],
            tier=ArbiterTier.CHEAP,
            config=self._config(),
        )
        assert result.decision == ArbiterDecision.INCONCLUSIVE

    def test_standard_both_pass(self):
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.90),
            ring2_scores=[self._ring("ring2_a", 0.88)],
            tier=ArbiterTier.STANDARD,
            config=self._config(),
        )
        assert result.decision == ArbiterDecision.PASS
        assert result.disagreement is False

    def test_standard_both_fail(self):
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.10),
            ring2_scores=[self._ring("ring2_a", 0.15)],
            tier=ArbiterTier.STANDARD,
            config=self._config(),
        )
        assert result.decision == ArbiterDecision.FAIL

    def test_standard_disagreement_escalates(self):
        """R1 says PASS, R2 says FAIL -> INCONCLUSIVE with disagreement=True."""
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.90, decision="pass"),
            ring2_scores=[self._ring("ring2_a", 0.15, decision="fail")],
            tier=ArbiterTier.STANDARD,
            config=self._config(),
        )
        assert result.decision == ArbiterDecision.INCONCLUSIVE
        assert result.disagreement is True

    def test_max_unanimous_pass(self):
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.92),
            ring2_scores=[
                self._ring("ring2_a", 0.90),
                self._ring("ring2_b", 0.91),
            ],
            tier=ArbiterTier.MAX,
            config=self._config(),
        )
        assert result.decision == ArbiterDecision.PASS
        assert result.disagreement is False

    def test_max_2_of_3_pass_escalates(self):
        """2/3 PASS is not enough -- escalate for review."""
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.90),
            ring2_scores=[
                self._ring("ring2_a", 0.85),
                self._ring("ring2_b", 0.20),  # dissenter
            ],
            tier=ArbiterTier.MAX,
            config=self._config(),
        )
        assert result.decision == ArbiterDecision.INCONCLUSIVE
        assert result.disagreement is True

    def test_max_2_of_3_fail_conservative_refund(self):
        """2/3 FAIL -> conservative refund (don't bother escalating)."""
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.10),
            ring2_scores=[
                self._ring("ring2_a", 0.15),
                self._ring("ring2_b", 0.90),  # dissenter
            ],
            tier=ArbiterTier.MAX,
            config=self._config(),
        )
        assert result.decision == ArbiterDecision.FAIL
        assert result.disagreement is True

    def test_max_graceful_degrade_missing_ring2(self):
        """If MAX tier has no ring2 scores, fall back to CHEAP logic."""
        consensus = DualRingConsensus()
        result = consensus.decide(
            ring1_score=self._ring("ring1", 0.92),
            ring2_scores=[],
            tier=ArbiterTier.MAX,
            config=self._config(),
        )
        # Should still produce a sensible verdict
        assert result.decision == ArbiterDecision.PASS


# ============================================================================
# ArbiterService tests
# ============================================================================


class TestArbiterService:
    """End-to-end orchestration: PHOTINT -> verdict."""

    @pytest.mark.asyncio
    async def test_evaluate_reads_phase_a_and_b(self):
        service = ArbiterService.from_defaults()
        task = {
            "id": "task-001",
            "category": "physical_presence",
            "bounty_usd": 0.10,
        }
        submission = {
            "id": "sub-001",
            "evidence": {"photo": "url", "gps": {"lat": 4.6, "lng": -74.1}},
            "auto_check_details": {"score": 0.92},  # Phase A
            "ai_verification_result": {"score": 0.88},  # Phase B
        }
        verdict = await service.evaluate(task, submission)
        assert verdict.decision == ArbiterDecision.PASS
        assert verdict.tier == ArbiterTier.CHEAP  # bounty < $1
        assert verdict.aggregate_score == pytest.approx(0.90, abs=0.01)

    @pytest.mark.asyncio
    async def test_evaluate_skipped_when_no_photint(self):
        service = ArbiterService.from_defaults()
        task = {"id": "task-002", "category": "physical_presence", "bounty_usd": 0.10}
        submission = {
            "id": "sub-002",
            "evidence": {},
            "auto_check_details": None,
            "ai_verification_result": None,
        }
        verdict = await service.evaluate(task, submission)
        assert verdict.decision == ArbiterDecision.SKIPPED

    @pytest.mark.asyncio
    async def test_evaluate_phase_a_only(self):
        """When Phase B hasn't completed, fall back to Phase A with lower confidence."""
        service = ArbiterService.from_defaults()
        task = {"id": "task-003", "category": "physical_presence", "bounty_usd": 0.10}
        submission = {
            "id": "sub-003",
            "evidence": {"photo": "url"},
            "auto_check_details": {"score": 0.90},
            "ai_verification_result": None,
        }
        verdict = await service.evaluate(task, submission)
        assert verdict.decision == ArbiterDecision.PASS
        # Confidence should be lower because Phase B is missing
        assert verdict.confidence < 0.9

    @pytest.mark.asyncio
    async def test_evidence_hash_deterministic(self):
        """Same evidence payload -> same hash regardless of dict key order."""
        service = ArbiterService.from_defaults()
        task = {"id": "task-004", "category": "physical_presence", "bounty_usd": 0.10}

        sub_a = {
            "id": "sub-a",
            "evidence": {"a": 1, "b": 2, "c": 3},
            "auto_check_details": {"score": 0.92},
            "ai_verification_result": {"score": 0.88},
        }
        sub_b = {
            "id": "sub-b",
            "evidence": {"c": 3, "a": 1, "b": 2},  # Same data, different key order
            "auto_check_details": {"score": 0.92},
            "ai_verification_result": {"score": 0.88},
        }

        v_a = await service.evaluate(task, sub_a)
        v_b = await service.evaluate(task, sub_b)
        assert v_a.evidence_hash == v_b.evidence_hash
        assert v_a.evidence_hash.startswith("0x")
        assert len(v_a.evidence_hash) == 66  # 0x + 64 hex chars

    @pytest.mark.asyncio
    async def test_commitment_hash_includes_decision(self):
        """Commitment hash must change if decision changes."""
        service = ArbiterService.from_defaults()
        task = {"id": "task-005", "category": "physical_presence", "bounty_usd": 0.10}

        sub_pass = {
            "id": "sub-p",
            "evidence": {"x": 1},
            "auto_check_details": {"score": 0.92},
            "ai_verification_result": {"score": 0.88},
        }
        sub_fail = {
            "id": "sub-f",
            "evidence": {"x": 1},
            "auto_check_details": {"score": 0.10},
            "ai_verification_result": {"score": 0.15},
        }

        v_pass = await service.evaluate(task, sub_pass)
        v_fail = await service.evaluate(task, sub_fail)

        assert v_pass.evidence_hash == v_fail.evidence_hash  # Same evidence
        assert v_pass.commitment_hash != v_fail.commitment_hash  # Different decision

    @pytest.mark.asyncio
    async def test_forced_consensus_bypasses_cheap(self):
        """human_authority forces MAX tier even for $0.10 bounty."""
        service = ArbiterService.from_defaults()
        task = {"id": "task-006", "category": "human_authority", "bounty_usd": 0.10}
        submission = {
            "id": "sub-006",
            "evidence": {"photo": "url"},
            "auto_check_details": {"score": 0.92},
            "ai_verification_result": {"score": 0.88},
        }
        verdict = await service.evaluate(task, submission)
        assert verdict.tier == ArbiterTier.MAX

    @pytest.mark.asyncio
    async def test_unknown_category_uses_fallback(self):
        service = ArbiterService.from_defaults()
        task = {"id": "task-007", "category": "__nope__", "bounty_usd": 0.10}
        submission = {
            "id": "sub-007",
            "evidence": {"x": 1},
            "auto_check_details": {
                "score": 0.95
            },  # Need high score -- fallback is strict
            "ai_verification_result": {"score": 0.92},
        }
        verdict = await service.evaluate(task, submission)
        # Fallback has pass_threshold=0.85, so 0.935 aggregate should pass
        assert verdict.decision == ArbiterDecision.PASS

    @pytest.mark.asyncio
    async def test_high_bounty_selects_max_tier(self):
        """$50 bounty on physical_presence should hit MAX tier."""
        service = ArbiterService.from_defaults()
        task = {"id": "task-008", "category": "physical_presence", "bounty_usd": 50.0}
        submission = {
            "id": "sub-008",
            "evidence": {"photo": "url"},
            "auto_check_details": {"score": 0.95},
            "ai_verification_result": {"score": 0.90},
        }
        verdict = await service.evaluate(task, submission)
        assert verdict.tier == ArbiterTier.MAX


# ============================================================================
# ArbiterVerdict serialization tests
# ============================================================================


class TestArbiterVerdictSerialization:
    """ArbiterVerdict.to_dict() produces JSONB-safe output."""

    def _verdict(self, **overrides):
        defaults = dict(
            decision=ArbiterDecision.PASS,
            tier=ArbiterTier.CHEAP,
            aggregate_score=0.9234,
            confidence=0.85,
            evidence_hash="0x" + "a" * 64,
            commitment_hash="0x" + "b" * 64,
            ring_scores=[
                RingScore(
                    ring="ring1",
                    score=0.92,
                    decision="pass",
                    confidence=0.85,
                    provider="photint",
                    model="phase_a+b",
                    reason="short reason",
                )
            ],
            reason="Valid verdict",
            disagreement=False,
            cost_usd=0.0012345678,
            latency_ms=2500,
        )
        defaults.update(overrides)
        return ArbiterVerdict(**defaults)

    def test_to_dict_rounds_score_to_4_decimals(self):
        d = self._verdict().to_dict()
        # 0.9234 rounds to 0.9234 (already 4 decimals)
        assert d["aggregate_score"] == 0.9234

    def test_to_dict_rounds_cost_to_6_decimals(self):
        d = self._verdict().to_dict()
        # 0.0012345678 rounds to 0.001235
        assert d["cost_usd"] == 0.001235

    def test_to_dict_excludes_raw_response_from_ring_scores(self):
        """raw_response must NEVER be in the JSONB payload (too large)."""
        rs = RingScore(
            ring="ring2_a",
            score=0.85,
            decision="pass",
            confidence=0.80,
            provider="anthropic",
            model="haiku",
            raw_response="A" * 10000,  # Huge blob
        )
        v = self._verdict(ring_scores=[rs])
        d = v.to_dict()
        assert "raw_response" not in d["ring_scores"][0]

    def test_to_dict_truncates_long_reason(self):
        long_reason = "x" * 2000
        v = self._verdict(reason=long_reason)
        d = v.to_dict()
        assert len(d["reason"]) <= 500

    def test_to_dict_truncates_long_ring_reason(self):
        long_reason = "y" * 2000
        rs = RingScore(
            ring="ring1",
            score=0.5,
            decision="inconclusive",
            confidence=0.5,
            reason=long_reason,
        )
        v = self._verdict(ring_scores=[rs])
        d = v.to_dict()
        assert len(d["ring_scores"][0]["reason"]) <= 500

    def test_to_dict_datetime_is_isoformat_string(self):
        d = self._verdict().to_dict()
        # isoformat gives "YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM"
        assert isinstance(d["evaluated_at"], str)
        assert "T" in d["evaluated_at"]

    def test_to_dict_is_json_serializable(self):
        """The to_dict output must be safe for json.dumps (no Decimals/datetimes)."""
        import json

        d = self._verdict().to_dict()
        # Should not raise
        serialized = json.dumps(d)
        assert len(serialized) > 0

    def test_verdict_properties(self):
        v_pass = self._verdict(decision=ArbiterDecision.PASS)
        assert v_pass.is_pass
        assert not v_pass.is_fail
        assert not v_pass.needs_escalation

        v_fail = self._verdict(decision=ArbiterDecision.FAIL)
        assert v_fail.is_fail
        assert not v_fail.is_pass

        v_inc = self._verdict(decision=ArbiterDecision.INCONCLUSIVE)
        assert v_inc.needs_escalation


# ============================================================================
# Category-level regression tests
# ============================================================================


class TestCategoryConfigs:
    """Sanity checks on the 21 per-category configurations."""

    @pytest.mark.parametrize("category", list(CATEGORY_CONFIGS.keys()))
    def test_thresholds_are_valid_for_category(self, category):
        config = CATEGORY_CONFIGS[category]
        assert 0.0 <= config.fail_threshold < config.pass_threshold <= 1.0, (
            f"Category {category}: fail_threshold must be < pass_threshold"
        )

    @pytest.mark.parametrize("category", list(CATEGORY_CONFIGS.keys()))
    def test_cost_cap_is_positive(self, category):
        config = CATEGORY_CONFIGS[category]
        assert config.max_cost_per_eval_usd > 0
        assert config.cost_to_bounty_ratio_max > 0
