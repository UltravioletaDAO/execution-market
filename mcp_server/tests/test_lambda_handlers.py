"""Phase 6 (Task 6.1/6.5) of the Rings Verification fixes.

C-35: the Lambda handlers — where every incident happened — had ZERO
tests. This file covers the Ring 1 pipeline paths the audits flagged:
happy path, no-photos, redelivery idempotency, and the Gemini salvage
parser (C-40 — markdown-wrapped/truncated responses had no regression
tests). Error/crash/advisory paths live in test_rings_fail_closed.py,
test_ring2_advisory.py and test_events_phase5.py.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_ring1():
    path = REPO_ROOT / "lambda" / "ring1" / "handler.py"
    spec = importlib.util.spec_from_file_location("ring1_handler", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ring1_handler"] = mod
    spec.loader.exec_module(mod)
    return mod


def _sqs_body(**overrides):
    body = {
        "submission_id": "sub-happy",
        "task_id": "task-happy",
        "evidence": {"photo": {"fileUrl": "https://cdn.example.com/a.jpg"}},
        "task": {"category": "physical_presence", "title": "t"},
        "photo_urls": ["https://cdn.example.com/a.jpg"],
        "phase_a_result": {
            "passed": True,
            "score": 0.9,
            "checks": [
                {"name": "schema", "passed": True, "score": 1.0, "reason": None}
            ],
            "warnings": [],
            "phase": "A",
        },
    }
    body.update(overrides)
    return body


def _check(name, passed=True, score=0.9):
    from verification.pipeline import CheckResult

    return CheckResult(name=name, passed=passed, score=score)


@pytest.fixture
def ring1(monkeypatch):
    """Ring 1 handler with a stubbed supabase_helper module."""
    handler = _load_ring1()

    state = {"updates": [], "events": [], "submission": {"auto_check_details": {}}}

    async def get_submission(sid):
        return {"id": sid, **state["submission"]}

    async def update_auto_check(sid, passed, details):
        state["updates"].append((sid, passed, details))

    async def update_ai_verification(sid, result):
        pass

    async def update_perceptual_hashes(sid, hashes):
        pass

    async def emit_verification_event(sid, ring, step, status, detail=None):
        state["events"].append((step, status))

    stub = types.ModuleType("supabase_helper")
    stub.get_submission = get_submission
    stub.update_auto_check = update_auto_check
    stub.update_ai_verification = update_ai_verification
    stub.update_perceptual_hashes = update_perceptual_hashes
    stub.emit_verification_event = emit_verification_event
    monkeypatch.setitem(sys.modules, "supabase_helper", stub)

    handler._test_state = state
    return handler


@pytest.mark.ring1_lambda
class TestRing1HappyPath:
    @pytest.mark.asyncio
    async def test_full_pipeline_completes_and_publishes_ring2(
        self, ring1, monkeypatch
    ):
        published = []
        monkeypatch.setattr(
            ring1,
            "_publish_to_ring2",
            lambda sid, tid, merged: published.append(merged),
        )
        monkeypatch.setattr(
            ring1,
            "_download_images",
            AsyncMock(return_value=[("https://cdn.example.com/a.jpg", b"img")]),
        )
        monkeypatch.setattr(ring1, "_write_temp_files", lambda imgs: ["/tmp/x.jpg"])
        monkeypatch.setattr(ring1, "_cleanup_temp_files", lambda paths: None)
        monkeypatch.setattr(
            ring1, "_run_exif_check", AsyncMock(return_value=("exif ctx", {}))
        )
        monkeypatch.setattr(
            ring1, "_run_tampering_check", AsyncMock(return_value=_check("tampering"))
        )
        monkeypatch.setattr(
            ring1, "_run_genai_check", AsyncMock(return_value=_check("genai"))
        )
        monkeypatch.setattr(
            ring1,
            "_run_photo_source_check",
            AsyncMock(return_value=_check("photo_source")),
        )
        monkeypatch.setattr(
            ring1,
            "_run_duplicate_check",
            AsyncMock(return_value=(_check("duplicate"), {"phash": "abc"})),
        )
        monkeypatch.setattr(
            ring1,
            "_run_ai_semantic_check",
            AsyncMock(return_value=_check("ai_semantic", score=0.85)),
        )

        result = await ring1._process_submission(_sqs_body())

        assert result["status"] == "complete"
        assert result["passed"] is True
        # Final write is terminal + carries the merged phase AB payload
        final = ring1._test_state["updates"][-1][2]
        assert final["ring1_status"] == "complete"
        assert final["phase"] == "AB"
        # Ring 2 always receives the handoff
        assert len(published) == 1
        assert published[0]["ring1_status"] == "complete"

    @pytest.mark.asyncio
    async def test_no_photos_is_terminal_error_with_ring2_handoff(
        self, ring1, monkeypatch
    ):
        published = []
        monkeypatch.setattr(
            ring1,
            "_publish_to_ring2",
            lambda sid, tid, details: published.append(details),
        )

        result = await ring1._process_submission(_sqs_body(photo_urls=[]))

        assert result["status"] == "error"
        assert result["reason"] == "no_photos"
        sid, passed, details = ring1._test_state["updates"][-1]
        assert passed is False  # C-42: fail closed
        assert details["ring1_status"] == "error"
        assert len(published) == 1  # C-07: arbiter still gets the handoff

    @pytest.mark.asyncio
    async def test_redelivery_is_idempotent(self, ring1, monkeypatch):
        ring1._test_state["submission"] = {
            "auto_check_details": {"ring1_status": "complete", "passed": True}
        }
        published = []
        monkeypatch.setattr(
            ring1,
            "_publish_to_ring2",
            lambda sid, tid, details: published.append(details),
        )
        download_spy = AsyncMock()
        monkeypatch.setattr(ring1, "_download_images", download_spy)

        result = await ring1._process_submission(_sqs_body())

        assert result["status"] == "skipped"
        assert result["reason"] == "already_complete"
        download_spy.assert_not_awaited()  # pipeline did NOT re-run
        assert len(published) == 1  # C-14: but Ring 2 is re-published


# ---------------------------------------------------------------------------
# C-40 (Task 6.5) — Gemini salvage parser regression tests
# ---------------------------------------------------------------------------


class TestGeminiResponseParsing:
    def _parse(self, text):
        from verification.ai_review import AIVerifier

        return AIVerifier(provider=MagicMock())._parse_response(text)

    def test_clean_json(self):
        from verification.ai_review import VerificationDecision

        result = self._parse(
            '{"decision": "approved", "confidence": 0.92, '
            '"explanation": "all good", "issues": []}'
        )
        assert result.decision == VerificationDecision.APPROVED
        assert result.confidence == 0.92
        assert result.error is False

    def test_markdown_wrapped_json(self):
        from verification.ai_review import VerificationDecision

        result = self._parse(
            "Here is my analysis:\n```json\n"
            '{"decision": "rejected", "confidence": 0.85, '
            '"explanation": "wrong location", "issues": ["geo mismatch"]}'
            "\n```\nLet me know if you need more."
        )
        assert result.decision == VerificationDecision.REJECTED
        assert result.confidence == 0.85
        assert result.issues == ["geo mismatch"]

    def test_markdown_without_language_tag(self):
        from verification.ai_review import VerificationDecision

        result = self._parse(
            '```\n{"decision": "approved", "confidence": 0.8, '
            '"explanation": "ok", "issues": []}\n```'
        )
        assert result.decision == VerificationDecision.APPROVED

    def test_truncated_by_safety_filter_salvages_decision(self):
        """Gemini SAFETY/RECITATION stops mid-JSON — salvage decision+confidence."""
        from verification.ai_review import VerificationDecision

        truncated = (
            '{"decision": "rejected", "confidence": 0.9, '
            '"explanation": "the photo shows clear evidence of'  # no close
        )
        result = self._parse(truncated)
        assert result.decision == VerificationDecision.REJECTED
        assert result.confidence == 0.9
        assert "truncated" in result.issues[0].lower()

    def test_garbage_returns_neutral_error(self):
        from verification.ai_review import VerificationDecision

        result = self._parse("I cannot analyze this image, sorry!")
        assert result.decision == VerificationDecision.NEEDS_HUMAN
        assert result.confidence == 0.5  # C-02: neutral, never 0.0
        assert result.error is True

    def test_forensic_field_merged_into_task_checks(self):
        result = self._parse(
            '{"decision": "approved", "confidence": 0.9, "explanation": "ok", '
            '"issues": [], "task_checks": {"door_visible": true}, '
            '"forensic": {"exif_consistent": true}}'
        )
        assert result.task_specific_checks["door_visible"] is True
        assert result.task_specific_checks["_forensic"]["exif_consistent"] is True


# ---------------------------------------------------------------------------
# photo_source policy — a screenshot is valid when the task asked for one
# ---------------------------------------------------------------------------


@pytest.mark.ring1_lambda
class TestPhotoSourceScreenshotPolicy:
    def _screenshot_result(self):
        return types.SimpleNamespace(
            source="screenshot",
            is_valid=False,
            reason="Photo source is 'screenshot'. Only live camera photos are accepted.",
            timestamp=None,
        )

    @pytest.mark.asyncio
    async def test_screenshot_accepted_when_task_requires_it(self):
        handler = _load_ring1()
        with patch(
            "verification.checks.photo_source.check_photo_source",
            return_value=self._screenshot_result(),
        ):
            check = await handler._run_photo_source_check(
                ["/tmp/x.png"],
                "digital_physical",
                {"screenshot", "text_response"},
            )
        assert check.passed is True
        assert check.score == 1.0
        assert "screenshot" in check.reason.lower()
        assert check.details["accepted_by_task"] is True

    @pytest.mark.asyncio
    async def test_screenshot_rejected_when_task_wants_camera(self):
        handler = _load_ring1()
        with patch(
            "verification.checks.photo_source.check_photo_source",
            return_value=self._screenshot_result(),
        ):
            check = await handler._run_photo_source_check(
                ["/tmp/x.png"], "physical_presence", {"photo_geo"}
            )
        assert check.passed is False
        assert check.score == 0.1

    @pytest.mark.asyncio
    async def test_camera_always_passes(self):
        handler = _load_ring1()
        camera = types.SimpleNamespace(
            source="camera", is_valid=True, reason="Camera capture", timestamp=None
        )
        with patch(
            "verification.checks.photo_source.check_photo_source",
            return_value=camera,
        ):
            check = await handler._run_photo_source_check(
                ["/tmp/x.jpg"], "physical_presence", {"photo_geo"}
            )
        assert check.passed is True
        assert check.score == 1.0
