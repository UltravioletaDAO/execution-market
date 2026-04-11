"""
Tests for V3-A Scoring Framework:
- Normalized scores on all 11 check result types (Task 3.1)
- EvidenceScore and CheckDetail dataclasses (Task 3.2)
- Two-axis consensus with category blend weights (Task 3.3)
- Per-category blend weights for all 21 categories (Task 3.4)
"""

import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

# Mock optional imaging dependencies that may not be installed in CI/test env
for _mod in ("imagehash", "piexif", "PIL", "PIL.Image", "PIL.ExifTags"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from mcp_server.integrations.arbiter.consensus import (
    HARD_FLOOR_RULES,
    DualRingConsensus,
)
from mcp_server.integrations.arbiter.registry import (
    BLEND_WEIGHTS,
    CATEGORY_CONFIGS,
    GENERIC_BLEND_WEIGHTS,
    get_default_registry,
)
from mcp_server.integrations.arbiter.types import (
    ArbiterConfig,
    ArbiterTier,
    CheckDetail,
    EvidenceScore,
    RingScore,
)

# ---- Check result imports (after mocks) ----
from mcp_server.verification.checks.duplicate import DuplicateResult
from mcp_server.verification.checks.genai import GenAIResult
from mcp_server.verification.checks.gps import GPSResult
from mcp_server.verification.checks.lighting import LightingResult
from mcp_server.verification.checks.ocr import OcrResult
from mcp_server.verification.checks.photo_source import PhotoSourceResult
from mcp_server.verification.checks.platform_fingerprint import PlatformFingerprint
from mcp_server.verification.checks.schema import SchemaValidationResult
from mcp_server.verification.checks.tampering import TamperingResult
from mcp_server.verification.checks.timestamp import TimestampResult
from mcp_server.verification.checks.weather import WeatherResult


# ======================================================================
# Task 3.1 — Normalized score tests for all 11 check types
# ======================================================================


class TestDuplicateNormalizedScore:
    """DuplicateResult.normalized_score: 1.0 = unique, 0.0 = exact duplicate."""

    def test_unique_image(self):
        r = DuplicateResult(
            is_duplicate=False, match_id=None, similarity=0.0, phash="abc", reason=None
        )
        assert r.normalized_score == 1.0

    def test_exact_duplicate(self):
        r = DuplicateResult(
            is_duplicate=True, match_id="t1", similarity=1.0, phash="abc", reason="dup"
        )
        assert r.normalized_score == 0.0

    def test_partial_similarity(self):
        r = DuplicateResult(
            is_duplicate=False,
            match_id=None,
            similarity=0.5,
            phash="abc",
            reason=None,
        )
        assert r.normalized_score == pytest.approx(0.5, abs=0.01)

    def test_high_similarity(self):
        r = DuplicateResult(
            is_duplicate=True,
            match_id="t2",
            similarity=0.85,
            phash="abc",
            reason="dup",
        )
        assert r.normalized_score == pytest.approx(0.15, abs=0.01)


class TestGenAINormalizedScore:
    """GenAIResult.normalized_score: 1.0 = real photo, 0.0 = AI-generated."""

    def test_real_photo(self):
        r = GenAIResult(
            is_ai_generated=False,
            confidence=0.0,
            model_hint=None,
            signals=[],
            details={},
            reason=None,
        )
        assert r.normalized_score == 1.0

    def test_confirmed_ai(self):
        r = GenAIResult(
            is_ai_generated=True,
            confidence=1.0,
            model_hint="midjourney",
            signals=["c2pa"],
            details={},
            reason="AI",
        )
        assert r.normalized_score == 0.0

    def test_medium_confidence(self):
        r = GenAIResult(
            is_ai_generated=False,
            confidence=0.3,
            model_hint=None,
            signals=[],
            details={},
            reason=None,
        )
        assert r.normalized_score == pytest.approx(0.7, abs=0.01)


class TestGPSNormalizedScore:
    """GPSResult.normalized_score: 1.0 = exact match, 0.0 = no GPS or too far."""

    def test_exact_match(self):
        r = GPSResult(
            is_valid=True,
            distance_meters=0.0,
            photo_coords=(10.0, 20.0),
            task_coords=(10.0, 20.0),
            max_distance=500,
            reason=None,
        )
        assert r.normalized_score == 1.0

    def test_no_gps(self):
        r = GPSResult(
            is_valid=False,
            distance_meters=None,
            photo_coords=None,
            task_coords=(10.0, 20.0),
            max_distance=500,
            reason="No GPS",
        )
        assert r.normalized_score == 0.0

    def test_half_distance(self):
        r = GPSResult(
            is_valid=True,
            distance_meters=250.0,
            photo_coords=(10.0, 20.0),
            task_coords=(10.0, 20.1),
            max_distance=500,
            reason=None,
        )
        assert r.normalized_score == pytest.approx(0.5, abs=0.01)

    def test_at_max_distance(self):
        r = GPSResult(
            is_valid=False,
            distance_meters=500.0,
            photo_coords=(10.0, 20.0),
            task_coords=(10.0, 21.0),
            max_distance=500,
            reason="Too far",
        )
        assert r.normalized_score == pytest.approx(0.0, abs=0.01)

    def test_beyond_max_distance(self):
        r = GPSResult(
            is_valid=False,
            distance_meters=1000.0,
            photo_coords=(10.0, 20.0),
            task_coords=(10.0, 25.0),
            max_distance=500,
            reason="Too far",
        )
        assert r.normalized_score == 0.0


class TestLightingNormalizedScore:
    """LightingResult.normalized_score: 1.0 = consistent, 0.0 = inconsistent."""

    def test_consistent(self):
        r = LightingResult(is_consistent_with_time=True)
        assert r.normalized_score == 1.0

    def test_inconsistent(self):
        r = LightingResult(is_consistent_with_time=False)
        assert r.normalized_score == 0.0

    def test_no_time_reference(self):
        r = LightingResult(is_consistent_with_time=None)
        assert r.normalized_score == 0.5


class TestOcrNormalizedScore:
    """OcrResult.normalized_score: text detection quality."""

    def test_text_found_high_confidence(self):
        r = OcrResult(
            text_blocks=[{"text": "receipt", "confidence": 95}],
            full_text="receipt",
            has_text=True,
            method="rekognition",
        )
        assert r.normalized_score == pytest.approx(0.95, abs=0.01)

    def test_no_text_neutral(self):
        r = OcrResult(has_text=False, method="pillow")
        assert r.normalized_score == 0.5

    def test_error(self):
        r = OcrResult(error="Failed")
        assert r.normalized_score == 0.0


class TestPhotoSourceNormalizedScore:
    """PhotoSourceResult.normalized_score: source type scoring."""

    def test_camera(self):
        r = PhotoSourceResult(
            is_valid=True,
            source="camera",
            timestamp=datetime.now(UTC),
            reason=None,
            details={},
        )
        assert r.normalized_score == 1.0

    def test_screenshot(self):
        r = PhotoSourceResult(
            is_valid=False,
            source="screenshot",
            timestamp=None,
            reason="screenshot",
            details={},
        )
        assert r.normalized_score == 0.0

    def test_unknown(self):
        r = PhotoSourceResult(
            is_valid=False,
            source="unknown",
            timestamp=None,
            reason="unknown",
            details={},
        )
        assert r.normalized_score == 0.3

    def test_gallery(self):
        r = PhotoSourceResult(
            is_valid=False,
            source="gallery",
            timestamp=None,
            reason="gallery",
            details={},
        )
        assert r.normalized_score == 0.1


class TestPlatformFingerprintNormalizedScore:
    """PlatformFingerprint.normalized_score: platform type scoring."""

    def test_original(self):
        r = PlatformFingerprint(
            platform="original", confidence=0.9, hops_estimate=0, signals=["EXIF"]
        )
        assert r.normalized_score == 1.0

    def test_whatsapp(self):
        r = PlatformFingerprint(
            platform="whatsapp", confidence=0.7, hops_estimate=1, signals=["filename"]
        )
        assert r.normalized_score == 0.6

    def test_screenshot(self):
        r = PlatformFingerprint(
            platform="screenshot", confidence=0.8, hops_estimate=1, signals=["filename"]
        )
        assert r.normalized_score == 0.2

    def test_unknown(self):
        r = PlatformFingerprint(
            platform="unknown", confidence=0.0, hops_estimate=0, signals=[]
        )
        assert r.normalized_score == 0.5


class TestSchemaNormalizedScore:
    """SchemaValidationResult.normalized_score: schema completeness."""

    def test_fully_valid(self):
        r = SchemaValidationResult(
            is_valid=True,
            missing_required=[],
            invalid_fields=[],
            warnings=[],
            reason=None,
        )
        assert r.normalized_score == 1.0

    def test_valid_with_warnings(self):
        r = SchemaValidationResult(
            is_valid=True,
            missing_required=[],
            invalid_fields=[],
            warnings=["extra field"],
            reason=None,
        )
        assert 0.8 <= r.normalized_score < 1.0

    def test_one_missing(self):
        r = SchemaValidationResult(
            is_valid=False,
            missing_required=["photo"],
            invalid_fields=[],
            warnings=[],
            reason="Missing photo",
        )
        assert r.normalized_score == pytest.approx(0.75, abs=0.01)

    def test_many_missing(self):
        r = SchemaValidationResult(
            is_valid=False,
            missing_required=["photo", "gps", "timestamp", "receipt"],
            invalid_fields=[],
            warnings=[],
            reason="Missing many",
        )
        assert r.normalized_score == 0.0


class TestTamperingNormalizedScore:
    """TamperingResult.normalized_score: 1.0 = clean, 0.0 = tampered."""

    def test_clean(self):
        r = TamperingResult(
            is_suspicious=False, confidence=0.0, signals=[], details={}, reason=None
        )
        assert r.normalized_score == 1.0

    def test_tampered(self):
        r = TamperingResult(
            is_suspicious=True,
            confidence=0.9,
            signals=["ai_generated"],
            details={},
            reason="tampered",
        )
        assert r.normalized_score == pytest.approx(0.1, abs=0.01)


class TestTimestampNormalizedScore:
    """TimestampResult.normalized_score: freshness decay."""

    def test_fresh_valid(self):
        now = datetime.now(UTC)
        r = TimestampResult(
            is_valid=True,
            photo_timestamp=now,
            submission_timestamp=now,
            task_start=None,
            task_deadline=None,
            age_seconds=0.0,
            reason=None,
        )
        assert r.normalized_score == 1.0

    def test_invalid(self):
        r = TimestampResult(
            is_valid=False,
            photo_timestamp=None,
            submission_timestamp=datetime.now(UTC),
            task_start=None,
            task_deadline=None,
            age_seconds=None,
            reason="No timestamp",
        )
        assert r.normalized_score == 0.0

    def test_5_minute_old(self):
        now = datetime.now(UTC)
        r = TimestampResult(
            is_valid=True,
            photo_timestamp=now,
            submission_timestamp=now,
            task_start=None,
            task_deadline=None,
            age_seconds=300.0,
            reason=None,
        )
        assert r.normalized_score == pytest.approx(0.7, abs=0.01)


class TestWeatherNormalizedScore:
    """WeatherResult.normalized_score: informational."""

    def test_available(self):
        r = WeatherResult(is_available=True, temperature_c=25.0)
        assert r.normalized_score == 1.0

    def test_unavailable(self):
        r = WeatherResult(is_available=False)
        assert r.normalized_score == 0.5

    def test_error_neutral(self):
        r = WeatherResult(error="API timeout")
        assert r.normalized_score == 0.5


# ======================================================================
# Task 3.2 — EvidenceScore and CheckDetail dataclass tests
# ======================================================================


class TestCheckDetail:
    """CheckDetail dataclass."""

    def test_creation(self):
        cd = CheckDetail(
            check="gps",
            passed=True,
            score=0.95,
            weight=0.20,
            details="10m from task location",
            issues=[],
        )
        assert cd.check == "gps"
        assert cd.passed is True
        assert cd.score == 0.95
        assert cd.issues == []

    def test_with_issues(self):
        cd = CheckDetail(
            check="tampering",
            passed=False,
            score=0.15,
            weight=0.25,
            details="Photoshop detected in EXIF",
            issues=["professional_editor_detected", "ela_anomaly"],
        )
        assert cd.passed is False
        assert len(cd.issues) == 2


class TestEvidenceScore:
    """EvidenceScore dataclass."""

    def test_creation(self):
        es = EvidenceScore(
            authenticity_score=0.85,
            authenticity_checks=[],
            completion_score=0.90,
            aggregate_score=0.87,
            verdict="pass",
            tier="standard",
            summary="Evidence passed",
            grade="B",
        )
        assert es.verdict == "pass"
        assert es.grade == "B"

    def test_to_dict(self):
        cd = CheckDetail(
            check="gps", passed=True, score=0.9, weight=0.2, details="OK", issues=[]
        )
        es = EvidenceScore(
            authenticity_score=0.85,
            authenticity_checks=[cd],
            completion_score=0.90,
            aggregate_score=0.87,
            verdict="pass",
            tier="standard",
            summary="Evidence passed",
            grade="B",
        )
        d = es.to_dict()
        assert d["verdict"] == "pass"
        assert d["grade"] == "B"
        assert len(d["authenticity_checks"]) == 1
        assert d["authenticity_checks"][0]["check"] == "gps"
        assert d["aggregate_score"] == 0.87

    def test_compute_grade(self):
        assert EvidenceScore.compute_grade(0.95) == "A"
        assert EvidenceScore.compute_grade(0.85) == "B"
        assert EvidenceScore.compute_grade(0.70) == "C"
        assert EvidenceScore.compute_grade(0.55) == "D"
        assert EvidenceScore.compute_grade(0.30) == "F"
        assert EvidenceScore.compute_grade(0.0) == "F"
        assert EvidenceScore.compute_grade(1.0) == "A"

    def test_default_rejection_reasons_empty(self):
        es = EvidenceScore(authenticity_score=0.9)
        assert es.rejection_reasons == []

    def test_default_verdict(self):
        es = EvidenceScore(authenticity_score=0.5)
        assert es.verdict == "inconclusive"


# ======================================================================
# Task 3.3 — Two-axis consensus with blend weights
# ======================================================================


class TestTwoAxisConsensus:
    """DualRingConsensus.decide_v2() tests."""

    def setup_method(self):
        self.consensus = DualRingConsensus()
        self.config = ArbiterConfig(
            category="physical_presence",
            pass_threshold=0.80,
            fail_threshold=0.30,
        )

    def _ring(self, ring: str, score: float, decision: str = "pass") -> RingScore:
        return RingScore(ring=ring, score=score, decision=decision, confidence=0.9)

    def test_pass_physical_presence(self):
        """High authenticity + moderate completion -> PASS for physical category."""
        ring1 = self._ring("ring1", 0.90)
        ring2 = [self._ring("ring2_a", 0.85)]

        result = self.consensus.decide_v2(
            ring1, ring2, ArbiterTier.STANDARD, self.config, "physical_presence"
        )

        assert result.verdict == "pass"
        assert result.authenticity_score == pytest.approx(0.90, abs=0.01)
        assert result.completion_score == pytest.approx(0.85, abs=0.01)
        # physical_presence: 70% auth + 30% comp = 0.70*0.90 + 0.30*0.85 = 0.885
        assert result.aggregate_score == pytest.approx(0.885, abs=0.01)
        assert result.grade in ("A", "B")

    def test_fail_low_scores(self):
        """Low scores on both axes -> FAIL."""
        ring1 = self._ring("ring1", 0.20, "fail")
        ring2 = [self._ring("ring2_a", 0.15, "fail")]

        result = self.consensus.decide_v2(
            ring1, ring2, ArbiterTier.STANDARD, self.config, "physical_presence"
        )

        assert result.verdict == "fail"
        assert result.aggregate_score < 0.30

    def test_inconclusive_middle_band(self):
        """Middle scores -> INCONCLUSIVE."""
        ring1 = self._ring("ring1", 0.55, "inconclusive")
        ring2 = [self._ring("ring2_a", 0.50, "inconclusive")]

        result = self.consensus.decide_v2(
            ring1, ring2, ArbiterTier.STANDARD, self.config, "physical_presence"
        )

        assert result.verdict == "inconclusive"

    def test_knowledge_access_weights(self):
        """Knowledge category: 30% auth + 70% completion."""
        ring1 = self._ring("ring1", 0.60)  # moderate authenticity
        ring2 = [self._ring("ring2_a", 0.95)]  # high completion

        config = ArbiterConfig(
            category="knowledge_access",
            pass_threshold=0.80,
            fail_threshold=0.25,
        )

        result = self.consensus.decide_v2(
            ring1, ring2, ArbiterTier.STANDARD, config, "knowledge_access"
        )

        # 0.30*0.60 + 0.70*0.95 = 0.18 + 0.665 = 0.845
        assert result.aggregate_score == pytest.approx(0.845, abs=0.01)
        assert result.verdict == "pass"

    def test_cheap_tier_no_ring2(self):
        """CHEAP tier: no Ring 2, uses Ring 1 as proxy for both axes."""
        ring1 = self._ring("ring1", 0.85)

        result = self.consensus.decide_v2(
            ring1, [], ArbiterTier.CHEAP, self.config, "physical_presence"
        )

        assert result.authenticity_score == 0.85
        assert result.completion_score == 0.85  # proxy from ring1
        assert result.completion_assessment is None
        assert result.verdict == "pass"

    def test_hard_floor_tampering(self):
        """Tampering below hard floor forces FAIL regardless of completion."""
        ring1 = self._ring("ring1", 0.90)
        ring2 = [self._ring("ring2_a", 0.95)]

        tampering_check = CheckDetail(
            check="tampering",
            passed=False,
            score=0.10,  # Below 0.20 hard floor
            weight=0.25,
            details="Photoshop detected",
            issues=["professional_editor_detected"],
        )

        result = self.consensus.decide_v2(
            ring1,
            ring2,
            ArbiterTier.STANDARD,
            self.config,
            "physical_presence",
            authenticity_checks=[tampering_check],
        )

        assert result.verdict == "fail"
        assert len(result.rejection_reasons) > 0
        assert "hard floor" in result.rejection_reasons[0].lower()

    def test_hard_floor_genai(self):
        """GenAI detection below hard floor forces FAIL."""
        ring1 = self._ring("ring1", 0.85)
        ring2 = [self._ring("ring2_a", 0.90)]

        genai_check = CheckDetail(
            check="genai",
            passed=False,
            score=0.05,  # Below 0.20 hard floor
            weight=0.20,
            details="DALL-E detected",
            issues=["c2pa_ai_metadata"],
        )

        result = self.consensus.decide_v2(
            ring1,
            ring2,
            ArbiterTier.STANDARD,
            self.config,
            "physical_presence",
            authenticity_checks=[genai_check],
        )

        assert result.verdict == "fail"
        assert any("genai" in r for r in result.rejection_reasons)

    def test_no_hard_floor_violation_passes(self):
        """Checks above hard floor do not trigger forced FAIL."""
        ring1 = self._ring("ring1", 0.90)
        ring2 = [self._ring("ring2_a", 0.85)]

        tampering_check = CheckDetail(
            check="tampering",
            passed=True,
            score=0.95,  # Well above floor
            weight=0.25,
            details="Clean",
            issues=[],
        )

        result = self.consensus.decide_v2(
            ring1,
            ring2,
            ArbiterTier.STANDARD,
            self.config,
            "physical_presence",
            authenticity_checks=[tampering_check],
        )

        assert result.verdict == "pass"
        assert result.rejection_reasons == []

    def test_custom_blend_weights(self):
        """Override blend weights at call site."""
        ring1 = self._ring("ring1", 0.90)
        ring2 = [self._ring("ring2_a", 0.50)]

        # Force 100% auth, 0% completion
        result = self.consensus.decide_v2(
            ring1,
            ring2,
            ArbiterTier.STANDARD,
            self.config,
            "custom",
            blend_weights={"authenticity": 1.0, "completion": 0.0},
        )

        assert result.aggregate_score == pytest.approx(0.90, abs=0.01)

    def test_max_tier_averages_ring2(self):
        """MAX tier: completion is average of 2 Ring 2 scores."""
        ring1 = self._ring("ring1", 0.85)
        ring2 = [
            self._ring("ring2_a", 0.90),
            self._ring("ring2_b", 0.80),
        ]

        result = self.consensus.decide_v2(
            ring1, ring2, ArbiterTier.MAX, self.config, "simple_action"
        )

        # simple_action: 50/50
        # completion = (0.90 + 0.80) / 2 = 0.85
        # aggregate = 0.50*0.85 + 0.50*0.85 = 0.85
        assert result.completion_score == pytest.approx(0.85, abs=0.01)
        assert result.aggregate_score == pytest.approx(0.85, abs=0.01)

    def test_evidence_score_has_tier(self):
        """EvidenceScore.tier reflects the tier used."""
        ring1 = self._ring("ring1", 0.85)

        result = self.consensus.decide_v2(
            ring1, [], ArbiterTier.CHEAP, self.config, "physical_presence"
        )
        assert result.tier == "cheap"

    def test_summary_populated(self):
        """Summary is always populated."""
        ring1 = self._ring("ring1", 0.85)

        result = self.consensus.decide_v2(
            ring1, [], ArbiterTier.CHEAP, self.config, "physical_presence"
        )
        assert len(result.summary) > 0


# ======================================================================
# Task 3.4 — Per-category blend weights for all 21 categories
# ======================================================================


class TestBlendWeights:
    """Validate blend weights exist and are correct for all 21 categories."""

    def test_all_21_categories_have_weights(self):
        """Every category in CATEGORY_CONFIGS must have blend weights."""
        for cat in CATEGORY_CONFIGS:
            assert cat in BLEND_WEIGHTS, f"Missing blend weights for category: {cat}"

    def test_weights_sum_to_one(self):
        """Authenticity + completion must sum to 1.0 for every category."""
        for cat, w in BLEND_WEIGHTS.items():
            total = w["authenticity"] + w["completion"]
            assert total == pytest.approx(1.0, abs=0.001), (
                f"Blend weights for {cat} sum to {total}, not 1.0"
            )

    def test_generic_fallback_sums_to_one(self):
        total = (
            GENERIC_BLEND_WEIGHTS["authenticity"] + GENERIC_BLEND_WEIGHTS["completion"]
        )
        assert total == pytest.approx(1.0, abs=0.001)

    def test_physical_categories_favor_authenticity(self):
        """Physical-world categories should weight authenticity >= 0.50."""
        physical = ["physical_presence", "location_based", "sensory", "emergency"]
        for cat in physical:
            assert BLEND_WEIGHTS[cat]["authenticity"] >= 0.50, (
                f"{cat} should favor authenticity, got {BLEND_WEIGHTS[cat]}"
            )

    def test_knowledge_categories_favor_completion(self):
        """Knowledge/content categories should weight completion >= 0.50."""
        knowledge = ["knowledge_access", "data_collection", "creative"]
        for cat in knowledge:
            assert BLEND_WEIGHTS[cat]["completion"] >= 0.50, (
                f"{cat} should favor completion, got {BLEND_WEIGHTS[cat]}"
            )

    def test_digital_categories_favor_completion(self):
        """Digital categories should weight completion >= 0.70."""
        digital = [
            "data_processing",
            "api_integration",
            "content_generation",
            "code_execution",
            "research",
            "multi_step_workflow",
        ]
        for cat in digital:
            assert BLEND_WEIGHTS[cat]["completion"] >= 0.70, (
                f"{cat} should heavily favor completion, got {BLEND_WEIGHTS[cat]}"
            )

    def test_authority_categories_balanced_with_auth_edge(self):
        """Authority categories should weight authenticity >= 0.50."""
        authority = ["human_authority", "bureaucratic"]
        for cat in authority:
            assert BLEND_WEIGHTS[cat]["authenticity"] >= 0.50, (
                f"{cat} should favor authenticity, got {BLEND_WEIGHTS[cat]}"
            )

    def test_registry_get_blend_weights(self):
        """ArbiterRegistry.get_blend_weights() returns correct weights."""
        registry = get_default_registry()

        w = registry.get_blend_weights("physical_presence")
        assert w == {"authenticity": 0.70, "completion": 0.30}

        w = registry.get_blend_weights("knowledge_access")
        assert w == {"authenticity": 0.30, "completion": 0.70}

    def test_registry_unknown_category_uses_fallback(self):
        """Unknown category falls back to 50/50 blend."""
        registry = get_default_registry()
        w = registry.get_blend_weights("nonexistent_category")
        assert w == GENERIC_BLEND_WEIGHTS

    def test_registry_empty_category_uses_fallback(self):
        """Empty category falls back to 50/50 blend."""
        registry = get_default_registry()
        w = registry.get_blend_weights("")
        assert w == GENERIC_BLEND_WEIGHTS

    def test_blend_weight_count(self):
        """Exactly 21 categories in BLEND_WEIGHTS."""
        assert len(BLEND_WEIGHTS) == 21


class TestHardFloorRules:
    """Validate hard-floor configuration."""

    def test_tampering_floor_exists(self):
        assert "tampering" in HARD_FLOOR_RULES
        assert HARD_FLOOR_RULES["tampering"] == 0.20

    def test_genai_floor_exists(self):
        assert "genai" in HARD_FLOOR_RULES
        assert HARD_FLOOR_RULES["genai"] == 0.20

    def test_photo_source_floor_exists(self):
        assert "photo_source" in HARD_FLOOR_RULES
        assert HARD_FLOOR_RULES["photo_source"] == 0.15

    def test_floors_are_low(self):
        """Hard floors should be conservative (low) to avoid false rejections."""
        for check, floor in HARD_FLOOR_RULES.items():
            assert 0.0 < floor <= 0.30, (
                f"Hard floor for {check} ({floor}) should be between 0 and 0.30"
            )
