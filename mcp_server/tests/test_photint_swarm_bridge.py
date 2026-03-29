"""
PHOTINT × Swarm Integration Tests

Tests the bridge between the PHOTINT forensic verification engine
and the swarm's evidence parser, model router, and inference logger.

Validates that:
1. Model routing correctly adapts to worker reputation from swarm analytics
2. Evidence parser skill signals align with PHOTINT prompt categories
3. Inference costs are correctly estimated across all supported models
4. Prompt library covers all task categories used by the swarm
5. Tier escalation respects reputation thresholds
6. PHOTINT category mapping matches swarm category taxonomy
7. Cross-chain reputation integrates with verification tier selection
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from swarm.evidence_parser import (
    EvidenceParser,
    EvidenceQuality,
    SkillDimension,
)
from verification.model_router import (
    HIGH_STAKES_CATEGORIES,
    LOW_STAKES_CATEGORIES,
    ModelSelection,
    needs_consensus,
    select_tier,
    should_escalate,
)
from verification.inference_logger import (
    COST_PER_1M_TOKENS,
    InferenceRecord,
    InferenceTimer,
    estimate_cost,
)
from verification.prompts import PromptLibrary, PromptResult
from verification.prompts.version import MAJOR, MINOR


# ============================================================================
# Section 1: Evidence Parser → Model Router Integration
# ============================================================================


class TestEvidenceQualityToTierMapping:
    """Evidence quality from swarm should inform verification tier selection."""

    def test_high_quality_evidence_low_tier(self):
        """Workers with excellent evidence history deserve lower verification tiers."""
        # Excellent evidence = trusted worker = Tier 1 for low-value
        result = select_tier(
            bounty_usd=0.30,
            category="simple_action",
            worker_reputation=4.5,
            worker_completed_tasks=50,
            has_exif=True,
        )
        assert result.tier == "tier_1"

    def test_no_exif_forces_tier_2(self):
        """Missing EXIF metadata should force at least Tier 2 for physical tasks."""
        result = select_tier(
            bounty_usd=0.30,
            category="simple_action",
            worker_reputation=4.5,
            worker_completed_tasks=50,
            has_exif=False,  # Suspicious
        )
        assert result.tier == "tier_2"
        assert "EXIF" in result.reason or "exif" in result.reason.lower()

    def test_new_worker_always_tier_2(self):
        """New workers (< 5 tasks) should always get Tier 2 minimum."""
        result = select_tier(
            bounty_usd=0.20,
            category="data_processing",
            worker_reputation=5.0,  # High rep but few tasks
            worker_completed_tasks=2,
            has_exif=True,
        )
        assert result.tier == "tier_2"

    def test_low_reputation_forces_scrutiny(self):
        """Workers with < 3.0 reputation should get extra verification."""
        result = select_tier(
            bounty_usd=0.20,
            category="data_processing",
            worker_reputation=2.5,
            worker_completed_tasks=20,
            has_exif=True,
        )
        assert result.tier == "tier_2"
        assert "reputation" in result.reason.lower() or "Low" in result.reason


class TestSwarmCategoryToPhotintMapping:
    """Swarm task categories should map correctly to PHOTINT prompt categories."""

    def test_all_high_stakes_are_physical(self):
        """HIGH_STAKES_CATEGORIES should be physical-world categories."""
        for cat in HIGH_STAKES_CATEGORIES:
            # Physical world tasks require at least Tier 2
            result = select_tier(bounty_usd=0.50, category=cat)
            assert result.tier in ("tier_2", "tier_3"), (
                f"Category '{cat}' should be at least Tier 2, got {result.tier}"
            )

    def test_digital_categories_accept_tier_1(self):
        """Digital-only categories should accept Tier 1 screening."""
        for cat in LOW_STAKES_CATEGORIES:
            result = select_tier(
                bounty_usd=0.20,
                category=cat,
                worker_reputation=4.0,
                worker_completed_tasks=10,
                has_exif=True,
            )
            assert result.tier == "tier_1", (
                f"Digital category '{cat}' should route to Tier 1, got {result.tier}"
            )

    def test_prompt_library_covers_all_categories(self):
        """PromptLibrary should have prompts for all swarm-used categories."""
        lib = PromptLibrary()
        # All high-stakes categories must have prompts
        for cat in HIGH_STAKES_CATEGORIES:
            result = lib.get_prompt(
                category=cat,
                task={"title": "Test task", "description": "Test"},
                evidence={"type": "photo"},
            )
            assert result.text
            assert result.version.startswith("photint-v")
            assert cat in result.version or "general" in result.version

    def test_prompt_library_digital_fallback(self):
        """Digital categories should use the fallback prompt."""
        lib = PromptLibrary()
        for cat in ["data_processing", "api_integration", "content_generation", "code_execution"]:
            result = lib.get_prompt(
                category=cat,
                task={"title": "Digital task"},
                evidence={"type": "screenshot"},
            )
            assert result.text
            assert "photint-v" in result.version


# ============================================================================
# Section 2: Inference Cost Estimation Accuracy
# ============================================================================


class TestInferenceCostEstimation:
    """Verify cost estimation is accurate for all supported models."""

    def test_all_models_have_costs(self):
        """Every model in the cost table should have input AND output rates."""
        for key, rates in COST_PER_1M_TOKENS.items():
            assert "input" in rates, f"Model {key} missing input rate"
            assert "output" in rates, f"Model {key} missing output rate"
            assert rates["input"] > 0, f"Model {key} has zero input rate"
            assert rates["output"] > 0, f"Model {key} has zero output rate"

    def test_tier_1_models_cheapest(self):
        """Tier 1 models (Flash/Haiku/Mini) should be cheapest."""
        tier_1_keys = [
            k for k in COST_PER_1M_TOKENS
            if any(m in k for m in ["flash", "mini", "haiku"])
        ]
        tier_3_keys = [
            k for k in COST_PER_1M_TOKENS
            if "opus" in k
        ]
        if tier_1_keys and tier_3_keys:
            max_tier_1 = max(COST_PER_1M_TOKENS[k]["output"] for k in tier_1_keys)
            min_tier_3 = min(COST_PER_1M_TOKENS[k]["output"] for k in tier_3_keys)
            assert max_tier_1 < min_tier_3, "Tier 1 should be cheaper than Tier 3"

    def test_typical_verification_cost(self):
        """A typical Tier 2 verification should cost roughly $0.01."""
        # Claude Sonnet: ~500 input tokens (prompt), ~300 output tokens (analysis)
        cost = estimate_cost(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_tokens=500,
            output_tokens=300,
        )
        assert 0.001 <= cost <= 0.05, f"Typical cost ${cost} outside expected range"

    def test_high_value_opus_verification_cost(self):
        """An Opus verification should cost significantly more."""
        cost = estimate_cost(
            provider="anthropic",
            model="claude-opus-4-6-20250627",
            input_tokens=1000,
            output_tokens=500,
        )
        # Should be ~$0.05 range
        assert cost > 0.01, f"Opus cost ${cost} too cheap"

    def test_unknown_model_uses_default(self):
        """Unknown models should use the default (Sonnet-level) rate."""
        cost_unknown = estimate_cost("unknown", "mystery-model", 1000, 500)
        cost_sonnet = estimate_cost("anthropic", "claude-sonnet-4-20250514", 1000, 500)
        assert cost_unknown == cost_sonnet, "Unknown model should match default (Sonnet) rates"

    def test_zero_tokens_zero_cost(self):
        """Zero tokens should produce zero cost."""
        cost = estimate_cost("anthropic", "claude-sonnet-4-20250514", 0, 0)
        assert cost == 0.0

    def test_flash_screening_very_cheap(self):
        """Gemini Flash screening should be under $0.001 for typical use."""
        cost = estimate_cost("gemini", "gemini-2.5-flash", 400, 200)
        assert cost < 0.001, f"Flash screening cost ${cost} too expensive"


# ============================================================================
# Section 3: Tier Escalation Logic
# ============================================================================


class TestTierEscalation:
    """Tier escalation should correctly promote uncertain results."""

    def test_tier_1_low_score_escalates(self):
        """Tier 1 with low score should escalate to Tier 2."""
        next_tier = should_escalate(tier="tier_1", score=0.70, confidence=0.90)
        assert next_tier == "tier_2"

    def test_tier_1_low_confidence_escalates(self):
        """Tier 1 with low confidence should escalate to Tier 2."""
        next_tier = should_escalate(tier="tier_1", score=0.95, confidence=0.60)
        assert next_tier == "tier_2"

    def test_tier_1_good_results_no_escalation(self):
        """Tier 1 with good results should not escalate."""
        next_tier = should_escalate(tier="tier_1", score=0.95, confidence=0.90)
        assert next_tier is None

    def test_tier_2_low_confidence_escalates_to_3(self):
        """Tier 2 with low confidence should escalate to Tier 3."""
        next_tier = should_escalate(tier="tier_2", score=0.50, confidence=0.50)
        assert next_tier == "tier_3"

    def test_tier_3_never_escalates(self):
        """Tier 3 should never escalate (highest tier)."""
        next_tier = should_escalate(tier="tier_3", score=0.10, confidence=0.10)
        assert next_tier is None

    def test_escalation_chain(self):
        """Full escalation: Tier 1 → Tier 2 → Tier 3."""
        # Start at Tier 1, low score
        tier = "tier_1"
        score, confidence = 0.70, 0.60

        next_tier = should_escalate(tier, score, confidence)
        assert next_tier == "tier_2"

        # At Tier 2, still low confidence
        next_tier = should_escalate("tier_2", score, confidence)
        assert next_tier == "tier_3"

        # At Tier 3, terminal
        next_tier = should_escalate("tier_3", score, confidence)
        assert next_tier is None


# ============================================================================
# Section 4: Consensus Verification Thresholds
# ============================================================================


class TestConsensusThresholds:
    """Multi-model consensus requirements based on task value."""

    def test_high_value_needs_consensus(self):
        """Tasks >= $10 should require multi-model consensus."""
        assert needs_consensus(bounty_usd=10.0) is True
        assert needs_consensus(bounty_usd=50.0) is True
        assert needs_consensus(bounty_usd=100.0) is True

    def test_low_value_no_consensus(self):
        """Tasks < $10 should not require consensus by default."""
        assert needs_consensus(bounty_usd=0.50) is False
        assert needs_consensus(bounty_usd=5.0) is False
        assert needs_consensus(bounty_usd=9.99) is False

    def test_disputed_always_consensus(self):
        """Disputed tasks should always require consensus regardless of value."""
        assert needs_consensus(bounty_usd=0.50, is_disputed=True) is True

    def test_consensus_threshold_boundary(self):
        """Test exact boundary at $10."""
        assert needs_consensus(bounty_usd=9.99) is False
        assert needs_consensus(bounty_usd=10.00) is True


# ============================================================================
# Section 5: Prompt Library Completeness
# ============================================================================


class TestPromptLibraryCompleteness:
    """Verify the prompt library covers all necessary categories."""

    def setup_method(self):
        self.lib = PromptLibrary()

    def test_all_21_categories_render(self):
        """All 21 registered categories should produce valid prompts."""
        categories = [
            "physical_presence", "knowledge_access", "human_authority",
            "simple_action", "digital_physical", "location_based",
            "verification", "social_proof", "data_collection",
            "sensory", "social", "proxy", "bureaucratic",
            "emergency", "creative",
            # Digital fallback categories
            "data_processing", "api_integration", "content_generation",
            "code_execution", "research", "multi_step_workflow",
        ]
        task = {"title": "Test task", "description": "A test", "location": {"lat": 25.76, "lon": -80.19}}
        evidence = {"type": "photo", "url": "https://example.com/photo.jpg"}

        for cat in categories:
            result = self.lib.get_prompt(category=cat, task=task, evidence=evidence)
            assert isinstance(result, PromptResult), f"Category '{cat}' failed"
            assert len(result.text) > 100, f"Category '{cat}' prompt too short"
            assert result.version, f"Category '{cat}' missing version"
            assert result.hash, f"Category '{cat}' missing hash"

    def test_prompt_hash_deterministic(self):
        """Same inputs should produce same hash."""
        task = {"title": "Buy coffee", "description": "Test"}
        evidence = {"type": "receipt"}

        h1 = self.lib.get_prompt("proxy", task, evidence).hash
        h2 = self.lib.get_prompt("proxy", task, evidence).hash
        assert h1 == h2

    def test_different_tasks_different_hashes(self):
        """Different task descriptions should produce different hashes."""
        evidence = {"type": "photo"}
        h1 = self.lib.get_prompt("proxy", {"title": "Buy coffee"}, evidence).hash
        h2 = self.lib.get_prompt("proxy", {"title": "Buy tea"}, evidence).hash
        assert h1 != h2

    def test_version_format(self):
        """Version string should follow photint-vMAJOR.MINOR-category format."""
        result = self.lib.get_prompt(
            "physical_presence",
            {"title": "Test"},
            {"type": "photo"},
        )
        assert result.version == f"photint-v{MAJOR}.{MINOR}-physical_presence"

    def test_unknown_category_fallback(self):
        """Unknown categories should produce a valid (general) prompt."""
        result = self.lib.get_prompt(
            "nonexistent_category_xyz",
            {"title": "Test"},
            {"type": "photo"},
        )
        assert result.text  # Should still produce something
        assert result.hash  # Should still have a hash


# ============================================================================
# Section 6: Inference Record Integrity
# ============================================================================


class TestInferenceRecordIntegrity:
    """Inference records must be complete for audit trail."""

    def test_full_record_creation(self):
        """A complete inference record should have all required fields."""
        record = InferenceRecord(
            submission_id="sub-001",
            task_id="task-001",
            check_name="ai_semantic",
            tier="tier_2",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            prompt_version="photint-v1.0-physical_presence",
            prompt_text="Analyze this evidence...",
            response_text='{"decision": "approved", "confidence": 0.95}',
            parsed_decision="approved",
            parsed_confidence=0.95,
            input_tokens=500,
            output_tokens=300,
        )
        assert record.submission_id == "sub-001"
        assert record.tier == "tier_2"
        assert record.prompt_version == "photint-v1.0-physical_presence"

    def test_record_cost_estimation(self):
        """Inference record should correctly estimate cost."""
        record = InferenceRecord(
            submission_id="sub-002",
            task_id="task-002",
            check_name="ai_semantic",
            tier="tier_2",
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            prompt_version="photint-v1.0-proxy",
            prompt_text="...",
            response_text="...",
            input_tokens=1000,
            output_tokens=500,
        )
        cost = estimate_cost(
            record.provider, record.model,
            record.input_tokens, record.output_tokens,
        )
        assert cost > 0

    def test_inference_timer_context_manager(self):
        """InferenceTimer should measure elapsed time."""
        with InferenceTimer() as timer:
            pass  # Fast operation
        assert timer.latency_ms >= 0


# ============================================================================
# Section 7: Evidence Parser Skill Extraction
# ============================================================================


class TestEvidenceParserSkillExtraction:
    """Verify evidence parser extracts skills that align with PHOTINT categories."""

    def setup_method(self):
        self.parser = EvidenceParser()

    def test_photo_geo_extracts_physical_skills(self):
        """photo_geo evidence should signal physical execution + geo mobility."""
        result = self.parser.parse_evidence([
            {"type": "photo_geo", "url": "https://example.com/geo.jpg"}
        ])
        dims = [s.dimension for s in result.signals]
        assert SkillDimension.GEO_MOBILITY in dims or SkillDimension.PHYSICAL_EXECUTION in dims

    def test_text_response_extracts_communication(self):
        """text_response evidence should signal communication skill."""
        result = self.parser.parse_evidence([
            {"type": "text_response", "content": "Detailed report about the task..."}
        ])
        dims = [s.dimension for s in result.signals]
        assert SkillDimension.COMMUNICATION in dims

    def test_notarized_extracts_verification(self):
        """Notarized evidence should signal verification skill."""
        result = self.parser.parse_evidence([
            {"type": "notarized", "url": "https://example.com/doc.pdf"}
        ])
        dims = [s.dimension for s in result.signals]
        assert SkillDimension.VERIFICATION_SKILL in dims

    def test_multiple_evidence_types_compound(self):
        """Multiple evidence types should produce compound skill signals."""
        result = self.parser.parse_evidence([
            {"type": "photo", "url": "https://example.com/photo.jpg"},
            {"type": "receipt", "url": "https://example.com/receipt.jpg"},
            {"type": "text_response", "content": "I bought the item at the store"},
        ])
        dims = [s.dimension for s in result.signals]
        # Should have at least 2 different dimensions
        assert len(set(dims)) >= 2

    def test_screenshot_extracts_digital_proficiency(self):
        """Screenshot evidence should signal digital proficiency."""
        result = self.parser.parse_evidence([
            {"type": "screenshot", "url": "https://example.com/screen.png"}
        ])
        dims = [s.dimension for s in result.signals]
        assert SkillDimension.DIGITAL_PROFICIENCY in dims


# ============================================================================
# Section 8: Category-Tier Alignment Matrix
# ============================================================================


class TestCategoryTierAlignmentMatrix:
    """Comprehensive test of how task categories map to verification tiers."""

    @pytest.mark.parametrize("category,min_tier", [
        ("physical_presence", "tier_2"),
        ("human_authority", "tier_2"),
        ("bureaucratic", "tier_2"),
        ("emergency", "tier_2"),
    ])
    def test_high_stakes_min_tier(self, category, min_tier):
        """High-stakes categories should have minimum tier guarantees."""
        result = select_tier(bounty_usd=0.50, category=category)
        tier_order = {"tier_1": 1, "tier_2": 2, "tier_3": 3}
        assert tier_order[result.tier] >= tier_order[min_tier]

    @pytest.mark.parametrize("bounty", [0.10, 0.20, 0.30, 0.49])
    def test_low_bounty_with_exif_gets_tier_1(self, bounty):
        """Low-value tasks with EXIF should route to Tier 1."""
        result = select_tier(
            bounty_usd=bounty,
            category="simple_action",
            worker_reputation=4.0,
            worker_completed_tasks=20,
            has_exif=True,
        )
        assert result.tier == "tier_1"

    @pytest.mark.parametrize("bounty", [10.0, 15.0, 50.0, 100.0])
    def test_high_bounty_gets_tier_3(self, bounty):
        """High-value tasks should always route to Tier 3."""
        result = select_tier(bounty_usd=bounty, category="simple_action")
        assert result.tier == "tier_3"

    def test_disputed_overrides_everything(self):
        """Disputed status should always force Tier 3."""
        # Even a cheap digital task should go to Tier 3 if disputed
        result = select_tier(
            bounty_usd=0.10,
            category="data_processing",
            worker_reputation=5.0,
            worker_completed_tasks=100,
            is_disputed=True,
        )
        assert result.tier == "tier_3"

    def test_medium_bounty_gets_tier_2(self):
        """Medium-value tasks ($1-$9.99) should route to Tier 2."""
        result = select_tier(
            bounty_usd=5.0,
            category="simple_action",
            worker_reputation=4.0,
            worker_completed_tasks=20,
        )
        assert result.tier == "tier_2"


# ============================================================================
# Section 9: Prompt Version Stability
# ============================================================================


class TestPromptVersionStability:
    """Prompt versions should be stable and well-formed."""

    def test_major_version_is_positive(self):
        assert MAJOR >= 1

    def test_minor_version_is_non_negative(self):
        assert MINOR >= 0

    def test_version_string_format(self):
        """Version should be 'photint-vX.Y-category'."""
        from verification.prompts.version import prompt_version
        v = prompt_version("physical_presence")
        parts = v.split("-")
        assert len(parts) == 3
        assert parts[0] == "photint"
        assert parts[1].startswith("v")
        assert "." in parts[1]
        assert parts[2] == "physical_presence"


# ============================================================================
# Section 10: Swarm Reputation → PHOTINT Routing Integration
# ============================================================================


class TestReputationRoutingIntegration:
    """Worker reputation from swarm should influence PHOTINT routing decisions."""

    def test_diamante_worker_gets_lighter_verification(self):
        """Diamante-tier worker (100+ tasks, 4.8+ rating) should get Tier 1 for low-value."""
        result = select_tier(
            bounty_usd=0.30,
            category="simple_action",
            worker_reputation=4.8,
            worker_completed_tasks=150,
            has_exif=True,
        )
        assert result.tier == "tier_1"

    def test_nuevo_worker_gets_heavier_verification(self):
        """Nuevo-tier worker (< 5 tasks) should get Tier 2 minimum."""
        result = select_tier(
            bounty_usd=0.30,
            category="simple_action",
            worker_reputation=5.0,  # High rep, few tasks
            worker_completed_tasks=1,
            has_exif=True,
        )
        assert result.tier == "tier_2"

    def test_reputation_doesnt_override_disputes(self):
        """Even Diamante workers get Tier 3 for disputed submissions."""
        result = select_tier(
            bounty_usd=0.30,
            category="simple_action",
            worker_reputation=4.9,
            worker_completed_tasks=200,
            has_exif=True,
            is_disputed=True,
        )
        assert result.tier == "tier_3"

    def test_reputation_doesnt_override_high_value(self):
        """Even Diamante workers get Tier 3 for $10+ tasks."""
        result = select_tier(
            bounty_usd=15.0,
            category="simple_action",
            worker_reputation=4.9,
            worker_completed_tasks=200,
            has_exif=True,
        )
        assert result.tier == "tier_3"

    def test_no_reputation_data_defaults_safely(self):
        """Missing reputation data should default to reasonable tier."""
        result = select_tier(
            bounty_usd=0.50,
            category="simple_action",
            worker_reputation=None,
            worker_completed_tasks=None,
        )
        # Should be at least Tier 2 (no trust data = cautious)
        assert result.tier in ("tier_2", "tier_3")
