"""
Tests for Phase 3: Multimodal AI Verification.

Covers: GeminiProvider, image_downloader, background_runner, weight system,
Phase B checks, auto-approve logic, merge_phase_b, commitment hashes.
"""

import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.security


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(**overrides):
    base = {
        "id": "task-001",
        "title": "Test Task",
        "instructions": "Take a photo",
        "category": "physical_presence",
        "evidence_schema": {"required": ["photo"], "optional": ["notes"]},
        "location_lat": 4.71,
        "location_lng": -74.07,
        "deadline": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "assigned_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "status": "submitted",
    }
    base.update(overrides)
    return base


def _make_submission(**overrides):
    base = {
        "id": "sub-001",
        "task_id": "task-001",
        "evidence": {
            "photo": {
                "fileUrl": "https://cdn.example.com/photo.jpg",
            },
            "notes": "Done",
        },
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "notes": "test",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# TestGeminiProvider
# ---------------------------------------------------------------------------


class TestGeminiProvider:
    def test_availability_with_key(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key-123")
        from verification.providers import GeminiProvider

        provider = GeminiProvider()
        assert provider.is_available() is True
        assert provider.name == "gemini"

    def test_availability_without_key(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        from verification.providers import GeminiProvider

        provider = GeminiProvider(api_key=None)
        # Force api_key to None since env might be set
        provider.api_key = None
        assert provider.is_available() is False

    def test_model_override(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "k")
        monkeypatch.setenv("AI_VERIFICATION_MODEL", "gemini-pro")
        from verification.providers import GeminiProvider

        provider = GeminiProvider()
        assert provider.model_id == "gemini-pro"

    @pytest.mark.asyncio
    async def test_analyze_mocked(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "k")
        from verification.providers import GeminiProvider, VisionRequest

        provider = GeminiProvider()

        mock_response = MagicMock()
        mock_response.text = '{"decision": "approved"}'
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50

        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response

        mock_genai = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.types.GenerationConfig.return_value = {}

        mock_google = MagicMock()
        mock_google.generativeai = mock_genai
        with patch.dict(
            "sys.modules", {"google": mock_google, "google.generativeai": mock_genai}
        ):
            result = await provider.analyze(
                VisionRequest(
                    prompt="Check this",
                    images=[b"fake-image-data"],
                    image_types=["image/jpeg"],
                )
            )

        assert result.text == '{"decision": "approved"}'
        assert result.provider == "gemini"

    def test_fallback_chain_prefers_gemini(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "gkey")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        from verification.providers import get_provider

        provider = get_provider()
        assert provider.name == "gemini"


# ---------------------------------------------------------------------------
# TestImageDownloader
# ---------------------------------------------------------------------------


class TestImageDownloader:
    def test_extract_photo_urls_simple(self):
        from verification.image_downloader import extract_photo_urls

        evidence = {
            "photo": {"fileUrl": "https://cdn.example.com/photo.jpg"},
        }
        urls = extract_photo_urls(evidence)
        assert len(urls) == 1
        assert urls[0] == "https://cdn.example.com/photo.jpg"

    def test_extract_photo_urls_dedup(self):
        from verification.image_downloader import extract_photo_urls

        evidence = {
            "photo": {"fileUrl": "https://cdn.example.com/photo.jpg"},
            "photo_geo": {"fileUrl": "https://cdn.example.com/photo.jpg"},
        }
        urls = extract_photo_urls(evidence)
        assert len(urls) == 1

    def test_extract_photo_urls_nested(self):
        from verification.image_downloader import extract_photo_urls

        evidence = {
            "photo": {
                "fileUrl": "https://cdn.example.com/a.jpg",
                "metadata": {"url": "https://cdn.example.com/b.png"},
            },
        }
        urls = extract_photo_urls(evidence)
        assert len(urls) >= 1

    def test_extract_photo_urls_direct_string(self):
        from verification.image_downloader import extract_photo_urls

        evidence = {
            "photo": "https://cdn.example.com/direct.jpg",
        }
        urls = extract_photo_urls(evidence)
        assert len(urls) == 1

    def test_extract_photo_urls_no_urls(self):
        from verification.image_downloader import extract_photo_urls

        evidence = {"notes": "just text", "rating": 5}
        urls = extract_photo_urls(evidence)
        assert len(urls) == 0

    def test_extract_photo_urls_max_limit(self):
        from verification.image_downloader import extract_photo_urls, MAX_IMAGES

        evidence = {}
        for i in range(MAX_IMAGES + 5):
            evidence[f"photo_{i}"] = {"fileUrl": f"https://cdn.example.com/{i}.jpg"}
        urls = extract_photo_urls(evidence)
        assert len(urls) <= MAX_IMAGES

    @pytest.mark.asyncio
    async def test_download_non_image_skipped(self):
        from verification.image_downloader import download_images_to_temp

        with patch("verification.image_downloader.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            results = await download_images_to_temp(["https://example.com/page.html"])
            assert len(results) == 0

    def test_cleanup_temp_files(self):
        from verification.image_downloader import cleanup_temp_files

        # Create temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        tmp.write(b"test")
        tmp.close()
        path = tmp.name
        assert os.path.exists(path)

        cleanup_temp_files([path])
        assert not os.path.exists(path)

    def test_cleanup_handles_missing(self):
        from verification.image_downloader import cleanup_temp_files

        # Should not raise
        cleanup_temp_files(["/nonexistent/file.jpg"])


# ---------------------------------------------------------------------------
# TestPhaseAWeights
# ---------------------------------------------------------------------------


class TestPhaseAWeights:
    def test_phase_a_weight_sum(self):
        from verification.pipeline import PHASE_A_WEIGHTS

        assert abs(sum(PHASE_A_WEIGHTS.values()) - 0.50) < 0.001

    def test_phase_b_weight_sum(self):
        from verification.pipeline import PHASE_B_WEIGHTS

        assert abs(sum(PHASE_B_WEIGHTS.values()) - 0.50) < 0.001

    def test_all_weights_sum(self):
        from verification.pipeline import ALL_WEIGHTS

        assert abs(sum(ALL_WEIGHTS.values()) - 1.00) < 0.001

    def test_backward_compat_alias(self):
        from verification.pipeline import CHECK_WEIGHTS, PHASE_A_WEIGHTS

        assert CHECK_WEIGHTS is PHASE_A_WEIGHTS


# ---------------------------------------------------------------------------
# TestPhaseBChecks
# ---------------------------------------------------------------------------


class TestPhaseBChecks:
    @pytest.mark.asyncio
    async def test_ai_semantic_no_provider(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        from verification.background_runner import _run_ai_semantic_check

        result = await _run_ai_semantic_check(
            _make_task(), {"photo": "url"}, ["https://cdn.example.com/photo.jpg"]
        )
        assert result.name == "ai_semantic"
        assert result.score == 0.5
        assert (
            "skipped" in (result.reason or "").lower()
            or "no" in (result.reason or "").lower()
        )

    @pytest.mark.asyncio
    async def test_tampering_no_images(self):
        from verification.background_runner import _run_tampering_check

        result = await _run_tampering_check([])
        assert result.name == "tampering"
        assert result.score == 0.5

    @pytest.mark.asyncio
    async def test_tampering_clean_image(self):
        from verification.background_runner import _run_tampering_check

        mock_result = MagicMock()
        mock_result.is_suspicious = False
        mock_result.confidence = 0.1
        mock_result.reason = "Clean"
        mock_result.signals = []

        with patch(
            "verification.checks.tampering.check_tampering",
            return_value=mock_result,
        ):
            result = await _run_tampering_check(["/tmp/test.jpg"])
            assert result.name == "tampering"
            assert result.passed is True
            assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_genai_no_images(self):
        from verification.background_runner import _run_genai_detection_check

        result = await _run_genai_detection_check([])
        assert result.name == "genai_detection"
        assert result.score == 0.5

    @pytest.mark.asyncio
    async def test_genai_clean_image(self):
        mock_result = MagicMock()
        mock_result.is_ai_generated = False
        mock_result.confidence = 0.1
        mock_result.reason = "Natural"
        mock_result.model_hint = None
        mock_result.signals = []

        with patch(
            "verification.checks.genai.check_genai",
            return_value=mock_result,
        ):
            from verification.background_runner import _run_genai_detection_check

            result = await _run_genai_detection_check(["/tmp/test.jpg"])
            assert result.name == "genai_detection"
            assert result.passed is True
            assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_photo_source_no_images(self):
        from verification.background_runner import _run_photo_source_check

        result = await _run_photo_source_check([], "physical_presence")
        assert result.name == "photo_source"
        assert result.score == 0.5

    @pytest.mark.asyncio
    async def test_photo_source_camera(self):
        mock_result = MagicMock()
        mock_result.is_valid = True
        mock_result.source = "camera"
        mock_result.timestamp = datetime.now(timezone.utc)
        mock_result.reason = None

        with patch(
            "verification.checks.photo_source.check_photo_source",
            return_value=mock_result,
        ):
            from verification.background_runner import _run_photo_source_check

            result = await _run_photo_source_check(
                ["/tmp/test.jpg"], "physical_presence"
            )
            assert result.name == "photo_source"
            assert result.passed is True
            assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_photo_source_screenshot(self):
        mock_result = MagicMock()
        mock_result.is_valid = False
        mock_result.source = "screenshot"
        mock_result.timestamp = None
        mock_result.reason = "Screenshot"

        with patch(
            "verification.checks.photo_source.check_photo_source",
            return_value=mock_result,
        ):
            from verification.background_runner import _run_photo_source_check

            result = await _run_photo_source_check(
                ["/tmp/test.jpg"], "physical_presence"
            )
            assert result.name == "photo_source"
            assert result.passed is False
            assert result.score == 0.1

    @pytest.mark.asyncio
    async def test_duplicate_no_images(self):
        from verification.background_runner import _run_duplicate_check

        result, hashes = await _run_duplicate_check([], "sub-1", "task-1")
        assert result.name == "duplicate"
        assert result.score == 0.5
        assert hashes is None

    @pytest.mark.asyncio
    async def test_duplicate_no_match(self):
        mock_detector = MagicMock()
        mock_detector.compute_hash.return_value = ("aabb", "ccdd", "eeff")
        mock_detector.compute_similarity.return_value = 0.2

        # Mock imagehash module (may not be installed locally)
        mock_imagehash = MagicMock()
        with patch.dict("sys.modules", {"imagehash": mock_imagehash}):
            import importlib
            import verification.checks.duplicate as dup_mod

            importlib.reload(dup_mod)

            with patch.object(dup_mod, "DuplicateDetector", return_value=mock_detector):
                with patch(
                    "supabase_client.get_existing_perceptual_hashes",
                    new_callable=AsyncMock,
                    return_value=[],
                ):
                    from verification.background_runner import _run_duplicate_check

                    result, hashes = await _run_duplicate_check(
                        ["/tmp/test.jpg"], "sub-1", "task-1"
                    )
                    assert result.name == "duplicate"
                    assert result.passed is True
                    assert result.score == 1.0
                    assert hashes == {
                        "phash": "aabb",
                        "dhash": "ccdd",
                        "ahash": "eeff",
                    }


# ---------------------------------------------------------------------------
# TestAutoApprove
# ---------------------------------------------------------------------------


class TestAutoApprove:
    def _merged_all_pass(self, score=0.96):
        return {
            "passed": True,
            "score": score,
            "checks": [
                {"name": "schema", "passed": True, "score": 1.0},
                {"name": "gps", "passed": True, "score": 0.9},
                {"name": "timestamp", "passed": True, "score": 1.0},
                {"name": "evidence_hash", "passed": True, "score": 0.8},
                {"name": "metadata", "passed": True, "score": 0.9},
                {"name": "ai_semantic", "passed": True, "score": 1.0},
                {"name": "tampering", "passed": True, "score": 1.0},
                {"name": "genai_detection", "passed": True, "score": 1.0},
                {"name": "photo_source", "passed": True, "score": 1.0},
                {"name": "duplicate", "passed": True, "score": 1.0},
            ],
            "phase": "AB",
        }

    def _phase_b_checks_all_pass(self):
        from verification.pipeline import CheckResult

        return [
            CheckResult(
                name="ai_semantic",
                passed=True,
                score=1.0,
                reason="Approved",
                details={
                    "decision": "approved",
                    "confidence": 0.95,
                },
            ),
            CheckResult(
                name="tampering",
                passed=True,
                score=1.0,
                details={"confidence": 0.1},
            ),
            CheckResult(
                name="genai_detection",
                passed=True,
                score=1.0,
                details={"confidence": 0.1},
            ),
            CheckResult(
                name="photo_source",
                passed=True,
                score=1.0,
            ),
            CheckResult(
                name="duplicate",
                passed=True,
                score=1.0,
            ),
        ]

    @pytest.mark.asyncio
    async def test_auto_approve_threshold_met(self):
        from verification.background_runner import _evaluate_auto_approve

        with patch(
            "supabase_client.get_task",
            new_callable=AsyncMock,
            return_value={"id": "task-001", "status": "submitted"},
        ):
            with patch(
                "supabase_client.auto_approve_submission",
                new_callable=AsyncMock,
                return_value=True,
            ) as mock_approve:
                await _evaluate_auto_approve(
                    submission_id="sub-001",
                    merged=self._merged_all_pass(),
                    phase_b_checks=self._phase_b_checks_all_pass(),
                    task=_make_task(),
                )
                mock_approve.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_approve_score_too_low(self):
        from verification.background_runner import _evaluate_auto_approve

        with patch(
            "supabase_client.auto_approve_submission",
            new_callable=AsyncMock,
        ) as mock_approve:
            await _evaluate_auto_approve(
                submission_id="sub-001",
                merged=self._merged_all_pass(score=0.80),
                phase_b_checks=self._phase_b_checks_all_pass(),
                task=_make_task(),
            )
            mock_approve.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_approve_already_reviewed(self):
        from verification.background_runner import _evaluate_auto_approve

        task = _make_task(status="completed")
        with patch(
            "supabase_client.get_task",
            new_callable=AsyncMock,
            return_value=task,
        ):
            with patch(
                "supabase_client.auto_approve_submission",
                new_callable=AsyncMock,
            ) as mock_approve:
                await _evaluate_auto_approve(
                    submission_id="sub-001",
                    merged=self._merged_all_pass(),
                    phase_b_checks=self._phase_b_checks_all_pass(),
                    task=task,
                )
                mock_approve.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_approve_no_ai_check(self):
        from verification.background_runner import _evaluate_auto_approve
        from verification.pipeline import CheckResult

        # Phase B checks without AI semantic
        checks = [
            CheckResult(
                name="tampering", passed=True, score=1.0, details={"confidence": 0.1}
            ),
        ]

        with patch(
            "supabase_client.auto_approve_submission",
            new_callable=AsyncMock,
        ) as mock_approve:
            await _evaluate_auto_approve(
                submission_id="sub-001",
                merged=self._merged_all_pass(),
                phase_b_checks=checks,
                task=_make_task(),
            )
            mock_approve.assert_not_called()

    @pytest.mark.asyncio
    async def test_auto_approve_tampering_detected(self):
        from verification.background_runner import _evaluate_auto_approve
        from verification.pipeline import CheckResult

        checks = self._phase_b_checks_all_pass()
        # Modify tampering to be suspicious
        checks[1] = CheckResult(
            name="tampering",
            passed=False,
            score=0.2,
            details={"confidence": 0.8},
        )

        with patch(
            "supabase_client.auto_approve_submission",
            new_callable=AsyncMock,
        ) as mock_approve:
            await _evaluate_auto_approve(
                submission_id="sub-001",
                merged=self._merged_all_pass(),
                phase_b_checks=checks,
                task=_make_task(),
            )
            mock_approve.assert_not_called()


# ---------------------------------------------------------------------------
# TestMergePhaseB
# ---------------------------------------------------------------------------


class TestMergePhaseB:
    def test_merge_combines_checks(self):
        from verification.pipeline import merge_phase_b, CheckResult

        existing = {
            "passed": True,
            "score": 0.85,
            "checks": [
                {
                    "name": "schema",
                    "passed": True,
                    "score": 1.0,
                    "reason": "OK",
                    "details": {},
                },
                {
                    "name": "gps",
                    "passed": True,
                    "score": 0.9,
                    "reason": "OK",
                    "details": {},
                },
            ],
            "warnings": [],
            "phase": "A",
        }

        phase_b = [
            CheckResult(name="ai_semantic", passed=True, score=1.0),
            CheckResult(name="tampering", passed=True, score=1.0),
        ]

        merged = merge_phase_b(existing, phase_b)
        assert merged["phase"] == "AB"
        assert len(merged["checks"]) == 4
        check_names = [c["name"] for c in merged["checks"]]
        assert "schema" in check_names
        assert "ai_semantic" in check_names

    def test_merge_recomputes_score(self):
        from verification.pipeline import merge_phase_b, CheckResult

        existing = {
            "passed": True,
            "score": 0.85,
            "checks": [
                {
                    "name": "schema",
                    "passed": True,
                    "score": 1.0,
                    "reason": "OK",
                    "details": {},
                },
            ],
            "warnings": [],
            "phase": "A",
        }

        phase_b = [
            CheckResult(name="ai_semantic", passed=True, score=1.0),
        ]

        merged = merge_phase_b(existing, phase_b)
        # Score should be recomputed with ALL_WEIGHTS
        assert merged["score"] != 0.85
        assert merged["score"] > 0

    def test_merge_preserves_phase_a(self):
        from verification.pipeline import merge_phase_b, CheckResult

        existing = {
            "passed": True,
            "score": 0.85,
            "checks": [
                {
                    "name": "schema",
                    "passed": True,
                    "score": 1.0,
                    "reason": "schema ok",
                    "details": {"test": True},
                },
            ],
            "warnings": ["test warning"],
            "phase": "A",
        }

        merged = merge_phase_b(
            existing, [CheckResult(name="ai_semantic", passed=True, score=1.0)]
        )
        schema_check = next(c for c in merged["checks"] if c["name"] == "schema")
        assert schema_check["reason"] == "schema ok"
        assert merged["warnings"] == ["test warning"]

    def test_merge_sets_phase_ab(self):
        from verification.pipeline import merge_phase_b, CheckResult

        existing = {
            "passed": True,
            "score": 0.85,
            "checks": [],
            "warnings": [],
            "phase": "A",
        }

        merged = merge_phase_b(
            existing, [CheckResult(name="ai_semantic", passed=True, score=1.0)]
        )
        assert merged["phase"] == "AB"


# ---------------------------------------------------------------------------
# TestCommitmentHash
# ---------------------------------------------------------------------------


class TestCommitmentHash:
    @pytest.mark.asyncio
    async def test_commitment_hash_computed(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        from verification.background_runner import _run_ai_semantic_check
        from verification.ai_review import VerificationDecision

        mock_result = MagicMock()
        mock_result.decision = VerificationDecision.APPROVED
        mock_result.confidence = 0.9
        mock_result.explanation = "Looks good"
        mock_result.issues = []
        mock_result.provider = "gemini"
        mock_result.model = "gemini-2.5-flash"
        mock_result.task_specific_checks = {}

        mock_verifier = MagicMock()
        mock_verifier.is_available = True
        mock_verifier.verify_evidence = AsyncMock(return_value=mock_result)

        with patch("verification.ai_review.AIVerifier", return_value=mock_verifier):
            result = await _run_ai_semantic_check(
                _make_task(), {"photo": "url"}, ["https://example.com/img.jpg"]
            )

        assert result.details.get("commitment_hash")
        assert result.details["commitment_hash"].startswith("0x")

    @pytest.mark.asyncio
    async def test_commitment_hash_deterministic(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        from verification.background_runner import _run_ai_semantic_check
        from verification.ai_review import VerificationDecision

        mock_result = MagicMock()
        mock_result.decision = VerificationDecision.APPROVED
        mock_result.confidence = 0.9
        mock_result.explanation = "Looks good"
        mock_result.issues = []
        mock_result.provider = "gemini"
        mock_result.model = "gemini-2.5-flash"

        mock_verifier = MagicMock()
        mock_verifier.is_available = True
        mock_verifier.verify_evidence = AsyncMock(return_value=mock_result)

        with patch("verification.ai_review.AIVerifier", return_value=mock_verifier):
            result1 = await _run_ai_semantic_check(
                _make_task(), {}, ["https://example.com/img.jpg"]
            )
            result2 = await _run_ai_semantic_check(
                _make_task(), {}, ["https://example.com/img.jpg"]
            )

        assert result1.details["commitment_hash"] == result2.details["commitment_hash"]


# ---------------------------------------------------------------------------
# TestBackgroundRunner
# ---------------------------------------------------------------------------


class TestBackgroundRunner:
    @pytest.mark.asyncio
    async def test_skipped_when_disabled(self, monkeypatch):
        monkeypatch.setenv("VERIFICATION_AI_ENABLED", "false")

        # Need to reimport to pick up the env var at module level
        import importlib
        import verification.background_runner as br

        importlib.reload(br)

        # Should return immediately
        await br.run_phase_b_verification(
            submission_id="sub-001",
            submission=_make_submission(),
            task=_make_task(),
        )

        # Restore
        monkeypatch.setenv("VERIFICATION_AI_ENABLED", "true")
        importlib.reload(br)

    @pytest.mark.asyncio
    async def test_skipped_when_no_photos(self):
        from verification.background_runner import run_phase_b_verification

        submission = _make_submission(evidence={"notes": "text only"})
        # Should not raise
        await run_phase_b_verification(
            submission_id="sub-001",
            submission=submission,
            task=_make_task(),
        )

    @pytest.mark.asyncio
    async def test_skipped_when_download_fails(self):
        from verification.background_runner import run_phase_b_verification

        with patch(
            "verification.background_runner.download_images_to_temp",
            new_callable=AsyncMock,
            return_value=[],
        ):
            await run_phase_b_verification(
                submission_id="sub-001",
                submission=_make_submission(),
                task=_make_task(),
            )

    @pytest.mark.asyncio
    async def test_cleanup_always_runs(self):
        from verification.background_runner import run_phase_b_verification

        with patch(
            "verification.background_runner.download_images_to_temp",
            new_callable=AsyncMock,
            return_value=[("/tmp/fake.jpg", "https://example.com/img.jpg")],
        ):
            with patch(
                "verification.background_runner.cleanup_temp_files"
            ) as mock_cleanup:
                # Force an error in gather
                with patch(
                    "verification.background_runner.asyncio.gather",
                    side_effect=Exception("boom"),
                ):
                    await run_phase_b_verification(
                        submission_id="sub-001",
                        submission=_make_submission(),
                        task=_make_task(),
                    )
                mock_cleanup.assert_called_once_with(["/tmp/fake.jpg"])

    @pytest.mark.asyncio
    async def test_phase_indicator_in_result(self):
        from verification.pipeline import run_verification_pipeline

        task = _make_task()
        submission = _make_submission()
        result = await run_verification_pipeline(submission, task)
        assert result.phase == "A"
        d = result.to_dict()
        assert d["phase"] == "A"
