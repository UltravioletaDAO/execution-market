"""Phase 6 (Task 6.2) — contract tests for the verification pipeline.

C-36/C-41: three status vocabularies and TWO different message schemas
reached the Ring 2 queue (the backend's publish_ring2 vs the Ring 1
Lambda's _publish_to_ring2) with zero contract tests. These tests pin:

1. The canonical auto_check_details payload shape (what the dashboard
   parses — see dashboard verification contract parser).
2. That the Ring 2 handler accepts BOTH queue message schemas.
"""

import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# The canonical contract — any change here must be coordinated with the
# dashboard parser (dashboard/src/lib/verificationContract.ts).
CANONICAL_DETAIL_KEYS = {
    "passed",
    "score",
    "checks",
    "warnings",
    "phase",
    "pass_threshold",
}
CANONICAL_CHECK_KEYS = {"name", "passed", "score", "reason", "details"}
RING1_TERMINAL_STATUSES = {"complete", "error", "skipped_no_media"}


class TestCanonicalPayloadShape:
    def test_to_dict_shape(self):
        from verification.pipeline import CheckResult, VerificationResult

        result = VerificationResult(
            passed=True,
            score=0.8,
            checks=[CheckResult(name="schema", passed=True, score=1.0)],
            warnings=["w"],
            phase="A",
        )
        d = result.to_dict()
        assert CANONICAL_DETAIL_KEYS.issubset(d.keys())
        assert isinstance(d["passed"], bool)
        assert isinstance(d["score"], float)
        assert d["pass_threshold"] == 0.5
        assert set(d["checks"][0].keys()) == CANONICAL_CHECK_KEYS

    def test_merge_phase_b_shape(self):
        from verification.pipeline import CheckResult, merge_phase_b

        merged = merge_phase_b(
            {
                "passed": True,
                "score": 0.8,
                "checks": [
                    {"name": "schema", "passed": True, "score": 1.0, "reason": None}
                ],
                "warnings": [],
                "phase": "A",
            },
            [CheckResult(name="tampering", passed=True, score=0.9)],
        )
        assert CANONICAL_DETAIL_KEYS.issubset(merged.keys())
        assert merged["phase"] == "AB"
        for check in merged["checks"]:
            assert CANONICAL_CHECK_KEYS == set(check.keys())

    def test_payload_is_json_serializable(self):
        from verification.pipeline import CheckResult, VerificationResult

        d = VerificationResult(
            passed=False,
            score=0.3,
            checks=[CheckResult(name="gps", passed=False, score=0.0)],
        ).to_dict()
        json.dumps(d)  # must not raise


# ---------------------------------------------------------------------------
# C-41 — both Ring 2 queue message schemas are accepted
# ---------------------------------------------------------------------------


def _load_ring2():
    path = REPO_ROOT / "lambda" / "ring2" / "handler.py"
    spec = importlib.util.spec_from_file_location("ring2_handler", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ring2_handler"] = mod
    spec.loader.exec_module(mod)
    return mod


def _pass_verdict():
    from integrations.arbiter.types import (
        ArbiterDecision,
        ArbiterTier,
        ArbiterVerdict,
    )

    return ArbiterVerdict(
        decision=ArbiterDecision.PASS,
        tier=ArbiterTier.STANDARD,
        aggregate_score=0.9,
        confidence=0.85,
        evidence_hash="0xev",
        commitment_hash="0xcm",
    )


def _stub_supabase(monkeypatch):
    stub = types.ModuleType("supabase_helper")
    stub.get_submission = lambda sid: {
        "id": sid,
        "arbiter_verdict": None,
        "auto_check_details": {},
    }
    stub.get_task = lambda tid: {
        "id": tid,
        "agent_id": "agent-1",
        "category": "general",
        "bounty_usd": 5.0,
    }
    stub.is_arbiter_enabled = lambda: True
    stub.emit_verification_event = lambda *a, **k: None
    stub.update_submission_verdict = lambda sid, data: True
    stub.write_error_to_submission = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "supabase_helper", stub)
    return stub


@pytest.mark.ring2_lambda
class TestRing2MessageSchemas:
    @pytest.mark.asyncio
    async def test_accepts_lambda_shape_message(self, monkeypatch):
        """Shape produced by lambda/ring1 _publish_to_ring2."""
        handler = _load_ring2()
        _stub_supabase(monkeypatch)

        arbiter = MagicMock()
        arbiter.evaluate = AsyncMock(return_value=_pass_verdict())

        with patch("integrations.arbiter.service.ArbiterService") as cls:
            cls.from_defaults.return_value = arbiter
            result = await handler._process_record(
                {
                    "submission_id": "sub-a",
                    "task_id": "task-a",
                    "ring1_result": {
                        "passed": True,
                        "score": 0.9,
                        "phase": "AB",
                        "checks_count": 5,
                    },
                    "enqueued_at": 1718000000.0,
                }
            )

        assert result["verdict"] == "pass"

    @pytest.mark.asyncio
    async def test_accepts_backend_shape_message(self, monkeypatch):
        """Shape produced by verification.sqs_publisher.publish_ring2
        (text-only submissions skip Ring 1 and publish directly)."""
        handler = _load_ring2()
        _stub_supabase(monkeypatch)

        arbiter = MagicMock()
        arbiter.evaluate = AsyncMock(return_value=_pass_verdict())

        with patch("integrations.arbiter.service.ArbiterService") as cls:
            cls.from_defaults.return_value = arbiter
            result = await handler._process_record(
                {
                    "version": "1",
                    "ring": "ring2",
                    "submission_id": "sub-b",
                    "task_id": "task-b",
                    "evidence": {"text_response": "done"},
                    "submitted_at": "2026-06-12T00:00:00Z",
                    "task": {"id": "task-b", "category": "general"},
                    "photo_urls": [],
                    "enqueued_at": "2026-06-12T00:00:01Z",
                }
            )

        assert result["verdict"] == "pass"

    def test_ring1_statuses_are_the_canonical_set(self):
        """The backend must only ever write these terminal statuses — the
        dashboard renders exactly this vocabulary (plus 'running')."""
        ring1_src = (REPO_ROOT / "lambda" / "ring1" / "handler.py").read_text(
            encoding="utf-8"
        )
        workers_src = (
            REPO_ROOT / "mcp_server" / "api" / "routers" / "workers.py"
        ).read_text(encoding="utf-8")

        import re

        written = set(
            re.findall(r"\"ring1_status\":\s*\"(\w+)\"", ring1_src)
            + re.findall(r"\"ring1_status\":\s*\"(\w+)\"", workers_src)
        )
        assert written - {"running"} <= RING1_TERMINAL_STATUSES, (
            f"unexpected ring1_status values written: {written}"
        )
