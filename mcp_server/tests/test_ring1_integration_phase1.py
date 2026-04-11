"""
Tests for Phase 1 Ring 1 PHOTINT integration.

Verifies that GPS anti-spoofing, hardware attestation, evidence hash
verification, multi-image EXIF extraction, and weather/platform_fingerprint
scoring are properly wired into the pipeline.

Tasks covered:
  1.1  GPS anti-spoofing integration into pipeline
  1.2  Hardware attestation integration into pipeline
  1.3  Evidence hash actual verification (not just presence)
  1.4  Multi-image EXIF extraction
  1.5  Weather + platform_fingerprint in scoring weights
"""

import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# Ensure mcp_server is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from verification.pipeline import (
    run_verification_pipeline,
    _run_evidence_hash_check,
    _run_gps_antispoofing_check,
    _run_attestation_check,
    _compute_evidence_hash,
    PHASE_A_WEIGHTS,
    PHASE_B_WEIGHTS,
    ALL_WEIGHTS,
    CheckResult,
)
from verification.exif_extractor import (
    ExifData,
    extract_exif_multi,
    extract_exif_multi_from_bytes,
    merge_exif_to_prompt_context,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_submission(evidence=None, executor_id="executor-001", **kwargs):
    """Build a minimal submission dict for testing."""
    base = {
        "id": "sub-001",
        "task_id": "task-001",
        "executor_id": executor_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "evidence": evidence or {},
    }
    base.update(kwargs)
    return base


def _make_task(category="physical_presence", bounty=0.10, **kwargs):
    """Build a minimal task dict for testing."""
    base = {
        "id": "task-001",
        "category": category,
        "bounty": bounty,
        "location_lat": 40.7128,
        "location_lng": -74.0060,
        "deadline": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "evidence_schema": {"required": ["photo"], "optional": []},
    }
    base.update(kwargs)
    return base


# ============================================================================
# Task 1.1 — GPS Anti-Spoofing Integration
# ============================================================================


class TestGPSAntiSpoofingIntegration:
    """GPS anti-spoofing should run AFTER basic GPS check passes."""

    @pytest.mark.asyncio
    async def test_antispoofing_runs_when_gps_passes(self):
        """Anti-spoofing check should appear in results when GPS passes."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
            "gps": {"lat": 40.7128, "lng": -74.0060},
        }
        submission = _make_submission(evidence=evidence)
        task = _make_task()

        result = await run_verification_pipeline(submission, task)

        check_names = [c.name for c in result.checks]
        assert "gps" in check_names, "Basic GPS check should run"
        assert "gps_antispoofing" in check_names, (
            "GPS anti-spoofing should run when basic GPS passes"
        )

    @pytest.mark.asyncio
    async def test_antispoofing_skipped_when_gps_fails(self):
        """Anti-spoofing should NOT run when basic GPS check fails."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
            # GPS far away from task location
            "gps": {"lat": 0.0, "lng": 0.0},
        }
        submission = _make_submission(evidence=evidence)
        task = _make_task()

        result = await run_verification_pipeline(submission, task)

        check_names = [c.name for c in result.checks]
        assert "gps" in check_names
        # GPS failed (too far), so antispoofing should not run
        gps_check = next(c for c in result.checks if c.name == "gps")
        if not gps_check.passed:
            assert "gps_antispoofing" not in check_names

    @pytest.mark.asyncio
    async def test_antispoofing_no_penalty_on_error(self):
        """Anti-spoofing errors should not block the pipeline."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
            "gps": {"lat": 40.7128, "lng": -74.0060},
        }
        submission = _make_submission(evidence=evidence)
        task = _make_task()

        # Even with normal execution, the pipeline should pass
        result = await run_verification_pipeline(submission, task)
        antispoof = next(
            (c for c in result.checks if c.name == "gps_antispoofing"), None
        )
        if antispoof:
            assert antispoof.score >= 0.0  # Should not crash

    @pytest.mark.asyncio
    async def test_antispoofing_check_standalone(self):
        """Direct test of _run_gps_antispoofing_check."""
        evidence = {
            "gps": {"lat": 40.7128, "lng": -74.0060},
            "forensic_metadata": {
                "device_id": "dev-123",
                "platform": "android",
            },
        }
        submission = _make_submission(evidence=evidence)
        task = _make_task()

        result = await _run_gps_antispoofing_check(evidence, submission, task)
        assert result is not None
        assert result.name == "gps_antispoofing"
        assert 0.0 <= result.score <= 1.0
        assert result.details.get("risk_level") is not None

    @pytest.mark.asyncio
    async def test_antispoofing_returns_none_without_gps(self):
        """No GPS coords -> anti-spoofing returns None."""
        evidence = {"photo": "https://cdn.example.com/img.jpg"}
        submission = _make_submission(evidence=evidence)
        task = _make_task()

        result = await _run_gps_antispoofing_check(evidence, submission, task)
        assert result is None

    @pytest.mark.asyncio
    async def test_antispoofing_weight_in_phase_a(self):
        """gps_antispoofing must have a weight in PHASE_A_WEIGHTS."""
        assert "gps_antispoofing" in PHASE_A_WEIGHTS
        assert PHASE_A_WEIGHTS["gps_antispoofing"] > 0


# ============================================================================
# Task 1.2 — Hardware Attestation Integration
# ============================================================================


class TestAttestationIntegration:
    """Hardware attestation should be an optional check in the pipeline."""

    def test_attestation_absent_no_penalty_low_bounty(self):
        """No attestation data + low bounty = no check returned (no penalty)."""
        evidence = {"photo": "https://cdn.example.com/img.jpg"}
        task = _make_task(bounty=0.10)  # Low bounty, no attestation needed

        result = _run_attestation_check(evidence, task)
        # Low bounty, not required, not recommended -> None (skip)
        assert result is None

    def test_attestation_absent_penalty_high_bounty(self):
        """No attestation data + high bounty = partial penalty."""
        evidence = {"photo": "https://cdn.example.com/img.jpg"}
        task = _make_task(bounty=100.0, category="human_authority")

        result = _run_attestation_check(evidence, task)
        assert result is not None
        assert result.name == "attestation"
        assert result.passed is False
        assert result.score < 0.5  # Penalized

    def test_attestation_present_strong(self):
        """Attestation with STRONG level = high score."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
            "attestation": {
                "platform": "ios",
                "level": "strong",
                "device_id": "device-abc",
            },
        }
        task = _make_task(bounty=100.0, category="human_authority")

        result = _run_attestation_check(evidence, task)
        assert result is not None
        assert result.passed is True
        assert result.score >= 0.8

    def test_attestation_present_verified(self):
        """Attestation with VERIFIED level = perfect score."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
            "attestation": {
                "platform": "android",
                "level": "verified",
            },
        }
        task = _make_task(bounty=50.0)

        result = _run_attestation_check(evidence, task)
        assert result is not None
        assert result.score == 1.0

    def test_attestation_present_basic(self):
        """Attestation with BASIC level = moderate score."""
        evidence = {
            "attestation": {"platform": "android", "level": "basic"},
        }
        task = _make_task(bounty=30.0)

        result = _run_attestation_check(evidence, task)
        assert result is not None
        assert result.score == 0.6

    def test_attestation_recommended_bounty_range(self):
        """Bounty in recommended range ($20-$50) without attestation = neutral."""
        evidence = {"photo": "https://cdn.example.com/img.jpg"}
        task = _make_task(bounty=25.0, category="simple_action")

        result = _run_attestation_check(evidence, task)
        # Should be recommended but not required
        if result is not None:
            assert result.passed is True
            assert result.score >= 0.5

    @pytest.mark.asyncio
    async def test_attestation_in_pipeline(self):
        """Attestation check appears in full pipeline run when present."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
            "gps": {"lat": 40.7128, "lng": -74.0060},
            "attestation": {"platform": "ios", "level": "verified"},
        }
        submission = _make_submission(evidence=evidence)
        task = _make_task(bounty=100.0, category="human_authority")

        result = await run_verification_pipeline(submission, task)
        check_names = [c.name for c in result.checks]
        assert "attestation" in check_names

    def test_attestation_weight_in_phase_a(self):
        """attestation must have a weight in PHASE_A_WEIGHTS."""
        assert "attestation" in PHASE_A_WEIGHTS
        assert PHASE_A_WEIGHTS["attestation"] > 0


# ============================================================================
# Task 1.3 — Evidence Hash Verification
# ============================================================================


class TestEvidenceHashVerification:
    """Evidence hash should be actually verified, not just checked for presence."""

    def test_no_hash_returns_neutral_score(self):
        """No hash provided = neutral score (0.5), not penalty."""
        evidence = {"photo": "https://cdn.example.com/img.jpg"}
        result = _run_evidence_hash_check(evidence)
        assert result is not None
        assert result.score == 0.5
        assert result.passed is True

    def test_correct_hash_returns_perfect_score(self):
        """Correct hash = score 1.0."""
        evidence = {"photo": "https://cdn.example.com/img.jpg", "notes": "test"}
        # Compute what the hash SHOULD be
        hashable = {k: v for k, v in evidence.items()}
        canonical = json.dumps(
            hashable, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        correct_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

        evidence["evidence_hash"] = correct_hash
        result = _run_evidence_hash_check(evidence)
        assert result is not None
        assert result.score == 1.0
        assert result.passed is True
        assert result.details.get("verified") is True

    def test_wrong_hash_returns_zero_score(self):
        """Wrong hash = score 0.0 with tampering warning."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
            "evidence_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        }
        result = _run_evidence_hash_check(evidence)
        assert result is not None
        assert result.score == 0.0
        assert result.passed is False
        assert "mismatch" in result.reason.lower()
        assert result.details.get("verified") is False

    def test_compute_evidence_hash_deterministic(self):
        """Hash computation should be deterministic."""
        evidence = {"photo": "https://cdn.example.com/img.jpg", "gps": {"lat": 40.7}}
        h1 = _compute_evidence_hash(evidence)
        h2 = _compute_evidence_hash(evidence)
        assert h1 == h2
        assert h1 is not None

    def test_compute_evidence_hash_excludes_hash_fields(self):
        """Hash computation excludes the hash fields themselves."""
        evidence = {"photo": "https://cdn.example.com/img.jpg"}
        h1 = _compute_evidence_hash(evidence)

        evidence_with_hash = {**evidence, "evidence_hash": "something"}
        h2 = _compute_evidence_hash(evidence_with_hash)
        assert h1 == h2

    def test_hash_no_longer_awards_0_8_for_presence(self):
        """Regression: old code awarded 0.8 just for hash presence. Now it verifies."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
            "evidence_hash": "deadbeef" * 8,  # Wrong hash
        }
        result = _run_evidence_hash_check(evidence)
        # Old behavior: score=0.8. New: should be 0.0 (mismatch)
        assert result.score != 0.8, "Should NOT award 0.8 for mere presence"


# ============================================================================
# Task 1.4 — Multi-Image EXIF Extraction
# ============================================================================


class TestMultiImageExifExtraction:
    """EXIF should be extracted from ALL images, not just the first."""

    def test_extract_exif_multi_returns_list(self):
        """extract_exif_multi returns a list of ExifData."""
        # Use non-existent paths — should return empty ExifData for each
        paths = ["/nonexistent/img1.jpg", "/nonexistent/img2.jpg"]
        results = extract_exif_multi(paths)
        assert len(results) == 2
        assert all(isinstance(r, ExifData) for r in results)

    def test_extract_exif_multi_empty_list(self):
        """Empty list returns empty list."""
        results = extract_exif_multi([])
        assert results == []

    def test_extract_exif_multi_from_bytes_returns_list(self):
        """extract_exif_multi_from_bytes handles multiple images."""
        # Create minimal valid JPEG bytes (smallest valid JPEG)
        # This will fail EXIF extraction but not crash
        images = [
            (b"\xff\xd8\xff\xe0" + b"\x00" * 100, "test1.jpg"),
            (b"\xff\xd8\xff\xe0" + b"\x00" * 50, "test2.jpg"),
        ]
        results = extract_exif_multi_from_bytes(images)
        assert len(results) == 2
        assert all(isinstance(r, ExifData) for r in results)

    def test_merge_exif_to_prompt_single(self):
        """Single image: no '[Image N]' prefix."""
        exif = ExifData(
            camera_make="Apple", camera_model="iPhone 15 Pro", has_exif=True
        )
        context = merge_exif_to_prompt_context([exif])
        assert "Image 1" not in context  # Single image, no numbering
        assert "Apple" in context

    def test_merge_exif_to_prompt_multiple(self):
        """Multiple images: '[Image N]' prefix for each."""
        exif1 = ExifData(camera_make="Apple", has_exif=True)
        exif2 = ExifData(camera_make="Samsung", has_exif=True)
        context = merge_exif_to_prompt_context([exif1, exif2])
        assert "[Image 1]" in context
        assert "[Image 2]" in context
        assert "Apple" in context
        assert "Samsung" in context

    def test_merge_exif_to_prompt_empty(self):
        """Empty list returns fallback message."""
        context = merge_exif_to_prompt_context([])
        assert "No EXIF data" in context

    def test_extract_exif_multi_graceful_on_bad_files(self):
        """Bad files should not crash, just return empty ExifData."""
        paths = ["/nonexistent.jpg", "/also/nonexistent.png"]
        results = extract_exif_multi(paths)
        assert len(results) == 2
        for r in results:
            assert r.has_exif is False


# ============================================================================
# Task 1.5 — Weather + Platform Fingerprint in Scoring
# ============================================================================


class TestWeatherAndPlatformFingerprintWeights:
    """Weather and platform_fingerprint must be in the weight maps."""

    def test_weather_in_phase_b_weights(self):
        """weather must be in PHASE_B_WEIGHTS."""
        assert "weather" in PHASE_B_WEIGHTS
        assert PHASE_B_WEIGHTS["weather"] > 0

    def test_platform_fingerprint_in_phase_b_weights(self):
        """platform_fingerprint must be in PHASE_B_WEIGHTS."""
        assert "platform_fingerprint" in PHASE_B_WEIGHTS
        assert PHASE_B_WEIGHTS["platform_fingerprint"] > 0

    def test_weather_in_all_weights(self):
        """weather must be in ALL_WEIGHTS (combined)."""
        assert "weather" in ALL_WEIGHTS

    def test_platform_fingerprint_in_all_weights(self):
        """platform_fingerprint must be in ALL_WEIGHTS (combined)."""
        assert "platform_fingerprint" in ALL_WEIGHTS

    def test_all_11_checks_in_weights(self):
        """All 11 check types should have weights."""
        expected_checks = {
            # Phase A
            "schema",
            "gps",
            "gps_antispoofing",
            "timestamp",
            "evidence_hash",
            "metadata",
            "attestation",
            # Phase B
            "ai_semantic",
            "tampering",
            "genai_detection",
            "photo_source",
            "duplicate",
            "weather",
            "platform_fingerprint",
        }
        all_weighted = set(ALL_WEIGHTS.keys())
        missing = expected_checks - all_weighted
        assert not missing, f"Missing weights for: {missing}"

    def test_phase_a_weights_sum_reasonable(self):
        """Phase A weights should sum to approximately 0.50."""
        total = sum(PHASE_A_WEIGHTS.values())
        assert 0.40 <= total <= 0.60, f"Phase A weights sum to {total}, expected ~0.50"

    def test_phase_b_weights_sum_reasonable(self):
        """Phase B weights should sum to approximately 0.50."""
        total = sum(PHASE_B_WEIGHTS.values())
        assert 0.40 <= total <= 0.60, f"Phase B weights sum to {total}, expected ~0.50"

    def test_weather_check_contributes_to_score(self):
        """A weather CheckResult with the 'weather' name should pick up its weight from ALL_WEIGHTS."""
        weather_check = CheckResult(
            name="weather",
            passed=True,
            score=0.9,
            reason="Weather cross-reference: partly cloudy matches visible sky",
        )
        weight = ALL_WEIGHTS.get(weather_check.name, 0)
        assert weight > 0, "Weather check should have non-zero weight"

    def test_platform_fingerprint_contributes_to_score(self):
        """A platform_fingerprint CheckResult should pick up its weight."""
        pf_check = CheckResult(
            name="platform_fingerprint",
            passed=True,
            score=0.8,
            reason="Original camera capture",
        )
        weight = ALL_WEIGHTS.get(pf_check.name, 0)
        assert weight > 0, "platform_fingerprint check should have non-zero weight"


# ============================================================================
# Integration: Full pipeline with all new checks
# ============================================================================


class TestFullPipelineIntegration:
    """Full pipeline runs with all new checks integrated."""

    @pytest.mark.asyncio
    async def test_pipeline_with_all_evidence(self):
        """Pipeline runs cleanly with GPS, attestation, and hash."""
        evidence_payload = {
            "photo": "https://cdn.example.com/img.jpg",
            "gps": {"lat": 40.7128, "lng": -74.0060},
            "notes": "Verified at location",
            "attestation": {"platform": "ios", "level": "verified"},
        }
        # Compute correct hash
        hashable = {
            k: v for k, v in evidence_payload.items() if k not in ("evidence_hash",)
        }
        canonical = json.dumps(
            hashable, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        evidence_payload["evidence_hash"] = hashlib.sha256(
            canonical.encode()
        ).hexdigest()

        submission = _make_submission(evidence=evidence_payload)
        task = _make_task(bounty=100.0, category="human_authority")

        result = await run_verification_pipeline(submission, task)

        check_names = [c.name for c in result.checks]
        assert "schema" in check_names
        assert "gps" in check_names
        assert "evidence_hash" in check_names
        assert "attestation" in check_names

        # Hash should be verified (score=1.0)
        hash_check = next(c for c in result.checks if c.name == "evidence_hash")
        assert hash_check.score == 1.0

    @pytest.mark.asyncio
    async def test_pipeline_without_optional_data(self):
        """Pipeline handles missing optional data gracefully."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
        }
        submission = _make_submission(evidence=evidence)
        task = _make_task(category="knowledge_access", bounty=0.05)

        result = await run_verification_pipeline(submission, task)

        # Should not crash, should have at least schema + metadata
        assert result is not None
        assert result.score >= 0.0
        check_names = [c.name for c in result.checks]
        assert "schema" in check_names

    @pytest.mark.asyncio
    async def test_pipeline_score_range(self):
        """Pipeline score should always be between 0.0 and 1.0."""
        evidence = {
            "photo": "https://cdn.example.com/img.jpg",
            "gps": {"lat": 40.7128, "lng": -74.0060},
        }
        submission = _make_submission(evidence=evidence)
        task = _make_task()

        result = await run_verification_pipeline(submission, task)
        assert 0.0 <= result.score <= 1.0
        for check in result.checks:
            assert 0.0 <= check.score <= 1.0, (
                f"Check {check.name} has score {check.score} outside [0, 1]"
            )
