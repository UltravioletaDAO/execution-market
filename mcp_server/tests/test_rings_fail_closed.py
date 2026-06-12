"""Fail-closed behavior of the rings verification pipeline (Phase 1).

Covers the 2026-06-11 audit findings:
- C-02/C-09: a provider/parse failure must NEVER become a perfect score
  (NEEDS_HUMAN + confidence 0.0 used to yield score 1.0, passed=True).
- C-42: a Ring 1 pipeline error must NEVER leave auto_check_passed=True,
  and auto_check_score must actually be persisted.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RING1_HANDLER = REPO_ROOT / "lambda" / "ring1" / "handler.py"


def _load_ring1_handler():
    """Load the Ring 1 Lambda handler by path ('lambda' is a reserved word)."""
    spec = importlib.util.spec_from_file_location("ring1_handler", RING1_HANDLER)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ring1_handler"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_result(**overrides):
    """Build a real VerificationResult with sane defaults."""
    from verification.ai_review import VerificationDecision, VerificationResult

    defaults = dict(
        decision=VerificationDecision.NEEDS_HUMAN,
        confidence=0.5,
        explanation="provider blew up",
        issues=[],
        task_specific_checks={},
        provider="gemini",
        model="gemini-2.5-flash",
    )
    defaults.update(overrides)
    return VerificationResult(**defaults)


# ---------------------------------------------------------------------------
# C-02/C-09 — ai_review error paths carry the error flag + neutral confidence
# ---------------------------------------------------------------------------


class TestAIReviewErrorFlag:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "exc",
        [
            ValueError("Gemini API error 401: unauthorized"),
            RuntimeError("rate limited"),
            ValueError("Unexpected Gemini response structure: 'candidates'"),
        ],
    )
    async def test_provider_exception_returns_error_flag(self, exc):
        from verification.ai_review import AIVerifier, VerificationDecision

        provider = MagicMock()
        provider.name = "gemini"
        provider.model_id = "gemini-2.5-flash"
        provider.is_available.return_value = True
        provider.analyze = AsyncMock(side_effect=exc)

        verifier = AIVerifier(provider=provider)
        with patch.object(
            AIVerifier, "_download_image", AsyncMock(return_value=b"img")
        ):
            result = await verifier.verify_evidence(
                task={"title": "t", "category": "general", "instructions": "x"},
                evidence={},
                photo_urls=["https://cdn.example.com/a.jpg"],
            )

        assert result.error is True
        assert result.decision == VerificationDecision.NEEDS_HUMAN
        assert result.confidence == 0.5  # neutral — never 0.0

    def test_parse_failure_returns_error_flag(self):
        from verification.ai_review import AIVerifier, VerificationDecision

        verifier = AIVerifier(provider=MagicMock())
        result = verifier._parse_response("definitely not json {{{")

        assert result.error is True
        assert result.decision == VerificationDecision.NEEDS_HUMAN
        assert result.confidence == 0.5

    def test_genuine_results_have_no_error_flag(self):
        from verification.ai_review import AIVerifier, VerificationDecision

        verifier = AIVerifier(provider=MagicMock())
        result = verifier._parse_response(
            '{"decision": "needs_human", "confidence": 0.9, '
            '"explanation": "ambiguous photo", "issues": []}'
        )
        assert result.error is False
        assert result.decision == VerificationDecision.NEEDS_HUMAN
        assert result.confidence == 0.9


# ---------------------------------------------------------------------------
# C-02 — Lambda ai_semantic check: error → 0.5 + review flag, never 1.0
# ---------------------------------------------------------------------------


class TestLambdaAISemanticCheck:
    @pytest.mark.asyncio
    async def test_error_result_scores_neutral(self):
        handler = _load_ring1_handler()

        error_result = _make_result(error=True, confidence=0.0)
        verifier = MagicMock()
        verifier.is_available = True
        verifier.verify_evidence = AsyncMock(return_value=error_result)

        with patch("verification.ai_review.AIVerifier", return_value=verifier):
            check = await handler._run_ai_semantic_check(
                task={"title": "t"},
                evidence={},
                photo_urls=["https://cdn.example.com/a.jpg"],
                exif_context="",
                temp_paths=[],
            )

        assert check.score == 0.5  # never 1.0 - confidence
        assert check.passed is False
        assert check.details["review_required"] is True
        assert check.details["error"] is True
        assert check.details["decision"] == "error_needs_human"

    @pytest.mark.asyncio
    async def test_genuine_needs_human_keeps_confidence_score(self):
        from verification.ai_review import VerificationDecision

        handler = _load_ring1_handler()

        genuine = _make_result(
            decision=VerificationDecision.NEEDS_HUMAN,
            confidence=0.9,
            error=False,
        )
        verifier = MagicMock()
        verifier.is_available = True
        verifier.verify_evidence = AsyncMock(return_value=genuine)

        with patch("verification.ai_review.AIVerifier", return_value=verifier):
            check = await handler._run_ai_semantic_check(
                task={"title": "t"},
                evidence={},
                photo_urls=["https://cdn.example.com/a.jpg"],
                exif_context="",
                temp_paths=[],
            )

        assert check.score == pytest.approx(0.1)
        assert check.details.get("error") is None

    @pytest.mark.asyncio
    async def test_verifier_crash_scores_neutral_and_flags(self):
        handler = _load_ring1_handler()

        verifier = MagicMock()
        verifier.is_available = True
        verifier.verify_evidence = AsyncMock(side_effect=OSError("boom"))

        with patch("verification.ai_review.AIVerifier", return_value=verifier):
            check = await handler._run_ai_semantic_check(
                task={"title": "t"},
                evidence={},
                photo_urls=["https://cdn.example.com/a.jpg"],
                exif_context="",
                temp_paths=[],
            )

        assert check.score == 0.5
        assert check.passed is False
        assert check.details["review_required"] is True


# ---------------------------------------------------------------------------
# C-42 — pipeline error writes fail closed + auto_check_score persisted
# ---------------------------------------------------------------------------


class TestFailClosedWrites:
    @pytest.mark.asyncio
    async def test_write_error_forces_passed_false(self, monkeypatch):
        handler = _load_ring1_handler()

        calls = {}

        async def fake_update(submission_id, passed, details):
            calls["submission_id"] = submission_id
            calls["passed"] = passed
            calls["details"] = details

        stub = types.ModuleType("supabase_helper")
        stub.update_auto_check = fake_update
        monkeypatch.setitem(sys.modules, "supabase_helper", stub)

        # Phase A said passed=True — the error write must still fail closed.
        await handler._write_error(
            "sub-123",
            "task-123",
            {"passed": True, "score": 0.9},
            "All Ring 1 checks failed",
        )

        assert calls["passed"] is False
        assert calls["details"]["ring1_status"] == "error"
        assert calls["details"]["review_required"] is True

    @pytest.mark.asyncio
    async def test_auto_check_score_persisted(self, monkeypatch):
        import supabase_client

        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        client = MagicMock()
        client.table.return_value = table
        monkeypatch.setattr(supabase_client, "get_client", lambda: client)

        await supabase_client.update_submission_auto_check(
            "sub-1", False, {"score": 0.42, "ring1_status": "error"}
        )

        payload = table.update.call_args.args[0]
        assert payload["auto_check_passed"] is False
        assert payload["auto_check_score"] == 0.42

    @pytest.mark.asyncio
    async def test_auto_check_score_skipped_when_absent(self, monkeypatch):
        import supabase_client

        table = MagicMock()
        table.update.return_value = table
        table.eq.return_value = table
        client = MagicMock()
        client.table.return_value = table
        monkeypatch.setattr(supabase_client, "get_client", lambda: client)

        await supabase_client.update_submission_auto_check(
            "sub-1", True, {"ring1_status": "running"}
        )

        payload = table.update.call_args.args[0]
        assert "auto_check_score" not in payload
