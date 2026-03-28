"""
Tests for PHOTINT Verification Infrastructure

Covers: InferenceLogger, ModelRouter, Providers, A/B Testing,
Enhanced Checks (lighting, weather, platform_fingerprint, OCR),
and AWS Rekognition result formatting.

All tests run standalone without external services.
"""

import time

import pytest

# ---------------------------------------------------------------------------
# Marker: all tests in this file are tagged 'verification'
# ---------------------------------------------------------------------------
pytestmark = pytest.mark.verification


# ===================================================================
# 1. InferenceLogger
# ===================================================================


class TestEstimateCost:
    """estimate_cost() pricing calculations."""

    def test_gemini_flash_cost(self):
        from verification.inference_logger import estimate_cost

        # gemini-2.5-flash: input $0.15/1M, output $0.60/1M
        cost = estimate_cost("gemini", "gemini-2.5-flash", 1_000, 500)
        expected = (1_000 * 0.15 + 500 * 0.60) / 1_000_000
        assert cost == round(expected, 6)

    def test_claude_sonnet_cost(self):
        from verification.inference_logger import estimate_cost

        # anthropic:claude-sonnet-4-6-20250627: input $3.00/1M, output $15.00/1M
        cost = estimate_cost("anthropic", "claude-sonnet-4-6-20250627", 2_000, 1_000)
        expected = (2_000 * 3.00 + 1_000 * 15.00) / 1_000_000
        assert cost == round(expected, 6)

    def test_gpt4o_cost(self):
        from verification.inference_logger import estimate_cost

        # openai:gpt-4o: input $2.50/1M, output $10.00/1M
        cost = estimate_cost("openai", "gpt-4o", 5_000, 2_000)
        expected = (5_000 * 2.50 + 2_000 * 10.00) / 1_000_000
        assert cost == round(expected, 6)

    def test_claude_opus_cost(self):
        from verification.inference_logger import estimate_cost

        # anthropic:claude-opus-4-6-20250627: input $15.00/1M, output $75.00/1M
        cost = estimate_cost("anthropic", "claude-opus-4-6-20250627", 10_000, 5_000)
        expected = (10_000 * 15.00 + 5_000 * 75.00) / 1_000_000
        assert cost == round(expected, 6)

    def test_unknown_model_uses_default(self):
        from verification.inference_logger import DEFAULT_COST, estimate_cost

        cost = estimate_cost("acme", "gpt-99", 1_000, 500)
        expected = (
            1_000 * DEFAULT_COST["input"] + 500 * DEFAULT_COST["output"]
        ) / 1_000_000
        assert cost == round(expected, 6)


class TestPromptHash:
    """compute_prompt_hash() determinism."""

    def test_deterministic(self):
        from verification.inference_logger import compute_prompt_hash

        text = "Analyze this image for evidence of physical presence."
        h1 = compute_prompt_hash(text)
        h2 = compute_prompt_hash(text)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_different_input_different_hash(self):
        from verification.inference_logger import compute_prompt_hash

        h1 = compute_prompt_hash("prompt A")
        h2 = compute_prompt_hash("prompt B")
        assert h1 != h2


class TestCommitmentHash:
    """compute_commitment_hash() format."""

    def test_returns_0x_prefixed_hex(self):
        from verification.inference_logger import compute_commitment_hash

        h = compute_commitment_hash("task-123", "The photo is authentic.")
        assert h.startswith("0x")
        # keccak256 produces 32 bytes = 64 hex chars + '0x' prefix
        assert len(h) == 66

    def test_deterministic(self):
        from verification.inference_logger import compute_commitment_hash

        h1 = compute_commitment_hash("task-1", "response")
        h2 = compute_commitment_hash("task-1", "response")
        assert h1 == h2


class TestInferenceTimer:
    """InferenceTimer measures latency."""

    def test_latency_positive_after_sleep(self):
        from verification.inference_logger import InferenceTimer

        with InferenceTimer() as timer:
            time.sleep(0.05)  # 50ms
        assert timer.latency_ms > 0
        # Should be at least ~40ms (allowing jitter)
        assert timer.latency_ms >= 30


class TestInferenceRecord:
    """InferenceRecord dataclass instantiation."""

    def test_full_fields(self):
        from verification.inference_logger import InferenceRecord

        rec = InferenceRecord(
            submission_id="sub-001",
            task_id="task-001",
            check_name="ai_semantic",
            tier="tier_2",
            provider="anthropic",
            model="claude-sonnet-4-6-20250627",
            prompt_version="photint-v1.0-physical_presence",
            prompt_text="Analyze this photo.",
            response_text='{"decision": "approve"}',
            parsed_decision="approve",
            parsed_confidence=0.95,
            parsed_issues=["low_lighting"],
            input_tokens=1500,
            output_tokens=300,
            latency_ms=820,
            estimated_cost_usd=0.0045,
            task_category="physical_presence",
            evidence_types=["photo"],
            photo_count=2,
            commitment_hash="0xabc123",
            metadata={"escalated": True},
        )
        assert rec.submission_id == "sub-001"
        assert rec.parsed_confidence == 0.95
        assert rec.metadata == {"escalated": True}

    def test_minimal_fields_defaults(self):
        from verification.inference_logger import InferenceRecord

        rec = InferenceRecord(
            submission_id="sub-002",
            task_id="task-002",
            check_name="tampering",
            tier="tier_1",
            provider="gemini",
            model="gemini-2.5-flash",
            prompt_version="photint-v1.0-simple_action",
            prompt_text="Check for tampering.",
            response_text="No tampering detected.",
        )
        assert rec.parsed_decision is None
        assert rec.parsed_confidence is None
        assert rec.parsed_issues is None
        assert rec.input_tokens is None
        assert rec.output_tokens is None
        assert rec.latency_ms is None
        assert rec.estimated_cost_usd is None
        assert rec.metadata == {}


# ===================================================================
# 2. ModelRouter
# ===================================================================


class TestSelectTier:
    """select_tier() routing logic."""

    def test_low_value_with_exif_tier_1(self):
        from verification.model_router import select_tier

        sel = select_tier(bounty_usd=0.10, has_exif=True)
        assert sel.tier == "tier_1"

    def test_medium_value_tier_2(self):
        from verification.model_router import select_tier

        sel = select_tier(bounty_usd=1.00)
        assert sel.tier == "tier_2"

    def test_high_value_tier_3(self):
        from verification.model_router import select_tier

        sel = select_tier(bounty_usd=15.00)
        assert sel.tier == "tier_3"

    def test_disputed_always_tier_3(self):
        from verification.model_router import select_tier

        sel = select_tier(bounty_usd=0.05, is_disputed=True)
        assert sel.tier == "tier_3"

    @pytest.mark.parametrize(
        "category",
        ["human_authority", "physical_presence", "bureaucratic", "emergency"],
    )
    def test_high_stakes_category_at_least_tier_2(self, category):
        from verification.model_router import select_tier

        sel = select_tier(bounty_usd=0.50, category=category)
        assert sel.tier in ("tier_2", "tier_3")

    def test_new_worker_tier_2(self):
        from verification.model_router import select_tier

        sel = select_tier(bounty_usd=0.10, worker_completed_tasks=3, has_exif=True)
        assert sel.tier == "tier_2"

    def test_low_reputation_tier_2(self):
        from verification.model_router import select_tier

        sel = select_tier(bounty_usd=0.10, worker_reputation=2.5, has_exif=True)
        assert sel.tier == "tier_2"

    def test_no_exif_physical_task_tier_2(self):
        from verification.model_router import select_tier

        sel = select_tier(bounty_usd=0.10, category="simple_action", has_exif=False)
        assert sel.tier == "tier_2"

    def test_digital_category_tier_1(self):
        from verification.model_router import select_tier

        sel = select_tier(bounty_usd=0.10, category="data_processing", has_exif=True)
        assert sel.tier == "tier_1"


class TestShouldEscalate:
    """should_escalate() escalation logic."""

    def test_tier_1_low_score_escalates_to_tier_2(self):
        from verification.model_router import should_escalate

        result = should_escalate("tier_1", 0.85, 0.75)
        assert result == "tier_2"

    def test_tier_1_high_score_no_escalation(self):
        from verification.model_router import should_escalate

        result = should_escalate("tier_1", 0.95, 0.90)
        assert result is None

    def test_tier_2_low_confidence_escalates_to_tier_3(self):
        from verification.model_router import should_escalate

        result = should_escalate("tier_2", 0.5, 0.60)
        assert result == "tier_3"

    def test_tier_3_never_escalates(self):
        from verification.model_router import should_escalate

        result = should_escalate("tier_3", 0.3, 0.2)
        assert result is None


class TestNeedsConsensus:
    """needs_consensus() multi-model check."""

    def test_high_value_needs_consensus(self):
        from verification.model_router import needs_consensus

        assert needs_consensus(15.0) is True

    def test_low_value_no_consensus(self):
        from verification.model_router import needs_consensus

        assert needs_consensus(5.0) is False

    def test_disputed_needs_consensus(self):
        from verification.model_router import needs_consensus

        assert needs_consensus(0.10, is_disputed=True) is True


# ===================================================================
# 3. Providers
# ===================================================================


class TestTierModels:
    """TIER_MODELS registry structure."""

    def test_has_all_tiers(self):
        from verification.providers import TIER_MODELS

        assert "tier_1" in TIER_MODELS
        assert "tier_2" in TIER_MODELS
        assert "tier_3" in TIER_MODELS

    def test_each_tier_has_at_least_two_options(self):
        from verification.providers import TIER_MODELS

        for tier, models in TIER_MODELS.items():
            assert len(models) >= 2, f"{tier} has fewer than 2 model options"


class TestGetProviderForTier:
    """get_provider_for_tier() availability and exclusion."""

    def test_returns_none_or_provider(self):
        from verification.providers import get_provider_for_tier

        # Without API keys set this should return None;
        # with keys it returns a provider. Either is acceptable.
        result = get_provider_for_tier("tier_1")
        if result is not None:
            assert hasattr(result, "analyze")
            assert hasattr(result, "is_available")

    def test_exclude_providers_skips_excluded(self):
        from verification.providers import TIER_MODELS, get_provider_for_tier

        # Exclude every provider name that appears in tier_1
        all_providers = [p for p, _ in TIER_MODELS["tier_1"]]
        result = get_provider_for_tier("tier_1", exclude_providers=all_providers)
        assert result is None


# ===================================================================
# 4. A/B Testing
# ===================================================================


class TestABTesting:
    """A/B testing prompt variant selection."""

    def test_no_config_returns_base(self, monkeypatch):
        monkeypatch.delenv("VERIFICATION_AB_TEST", raising=False)
        from verification.ab_testing import select_prompt_variant

        result = select_prompt_variant(
            "physical_presence", "photint-v1.0-physical_presence"
        )
        assert result == "photint-v1.0-physical_presence"

    def test_get_active_experiments_empty(self, monkeypatch):
        monkeypatch.delenv("VERIFICATION_AB_TEST", raising=False)
        from verification.ab_testing import get_active_experiments

        assert get_active_experiments() == {}


# ===================================================================
# 5. Enhanced Checks
# ===================================================================


class TestLightingTimeConsistency:
    """_check_time_consistency() cross-reference logic."""

    def test_midday_hour_12_consistent(self):
        from verification.checks.lighting import _check_time_consistency

        assert _check_time_consistency("midday", 12) is True

    def test_night_hour_12_inconsistent(self):
        from verification.checks.lighting import _check_time_consistency

        assert _check_time_consistency("night", 12) is False

    def test_indoor_any_hour_consistent(self):
        from verification.checks.lighting import _check_time_consistency

        for hour in (0, 6, 12, 18, 23):
            assert _check_time_consistency("indoor", hour) is True

    def test_morning_hour_7_consistent(self):
        from verification.checks.lighting import _check_time_consistency

        assert _check_time_consistency("morning", 7) is True

    def test_evening_hour_6_inconsistent(self):
        from verification.checks.lighting import _check_time_consistency

        # evening range is 16-20, hour 6 is outside
        assert _check_time_consistency("evening", 6) is False


class TestLightingResult:
    """LightingResult dataclass defaults."""

    def test_default_values(self):
        from verification.checks.lighting import LightingResult

        r = LightingResult()
        assert r.estimated_time_of_day is None
        assert r.brightness_mean == 0.0
        assert r.is_consistent_with_time is None


class TestWeatherResult:
    """WeatherResult formatting."""

    def test_to_context_formats_correctly(self):
        from verification.checks.weather import WeatherResult

        w = WeatherResult(
            temperature_c=22.5,
            weather_description="Partly cloudy",
            cloud_cover_pct=45,
            precipitation_mm=0.0,
            is_available=True,
        )
        ctx = w.to_context()
        assert "Partly cloudy" in ctx
        assert "22C" in ctx or "23C" in ctx  # rounded
        assert "45%" in ctx
        # No precipitation line when 0
        assert "Precipitation" not in ctx

    def test_empty_result_returns_empty_string(self):
        from verification.checks.weather import WeatherResult

        w = WeatherResult()
        assert w.to_context() == ""


class TestPlatformFingerprint:
    """check_platform() filename pattern detection."""

    def test_whatsapp_filename_detected(self):
        from verification.checks.platform_fingerprint import check_platform

        fp = check_platform("IMG-20260328-WA0042.jpg", has_exif=False)
        assert fp.platform == "whatsapp"
        assert fp.confidence > 0
        assert any("WhatsApp" in s for s in fp.signals)

    def test_original_camera_filename(self):
        from verification.checks.platform_fingerprint import check_platform

        fp = check_platform("IMG_20260328_143022.jpg", has_exif=True)
        assert fp.platform == "original"
        assert any("Android" in s or "camera" in s.lower() for s in fp.signals)

    def test_telegram_filename_detected(self):
        from verification.checks.platform_fingerprint import check_platform

        fp = check_platform("photo_2026-03-28_14-30-22.jpg", has_exif=False)
        assert fp.platform == "telegram"
        assert any("Telegram" in s for s in fp.signals)


class TestOcrResult:
    """OcrResult formatting."""

    def test_to_context_formats_blocks(self):
        from verification.checks.ocr import OcrResult

        r = OcrResult(
            text_blocks=[
                {"text": "RECEIPT #12345", "confidence": 98.5, "type": "LINE"},
                {"text": "Total: $42.50", "confidence": 95.0, "type": "LINE"},
            ],
            full_text="RECEIPT #12345 | Total: $42.50",
            has_text=True,
            method="rekognition",
        )
        ctx = r.to_context()
        assert "rekognition" in ctx
        assert "RECEIPT #12345" in ctx
        assert "Total: $42.50" in ctx

    def test_no_text_returns_empty(self):
        from verification.checks.ocr import OcrResult

        r = OcrResult()
        assert r.to_context() == ""


# ===================================================================
# 6. Rekognition Result
# ===================================================================


class TestRekognitionResult:
    """RekognitionResult.to_prompt_context() formatting."""

    def test_formats_labels_text_faces(self):
        from verification.providers_aws import RekognitionResult

        r = RekognitionResult(
            labels=[
                {"name": "Building", "confidence": 99.1},
                {"name": "Street", "confidence": 95.3},
            ],
            text_detections=[{"text": "OPEN", "type": "LINE", "confidence": 92.0}],
            extracted_text="OPEN",
            face_count=2,
            quality={"sharpness": 85.0, "brightness": 72.0},
            available=True,
        )
        ctx = r.to_prompt_context()
        assert "Building" in ctx
        assert "Street" in ctx
        assert "OPEN" in ctx
        assert "Faces detected: 2" in ctx
        assert "sharpness=85" in ctx

    def test_empty_unavailable_returns_empty(self):
        from verification.providers_aws import RekognitionResult

        r = RekognitionResult()
        assert r.to_prompt_context() == ""

    def test_available_but_no_data_returns_empty(self):
        from verification.providers_aws import RekognitionResult

        r = RekognitionResult(available=True)
        assert r.to_prompt_context() == ""
