"""Phase 2 of the Rings Verification fixes — Ring 2 revival without zombies.

Covers:
- C-13: the Ring 2 Lambda is advisory-only — INCONCLUSIVE persists the
  verdict + recommendation but creates NO dispute and never touches
  agent_verdict (the INC-2026-04-22 fix only covered the dead ECS path).
- C-07/C-14: Ring 1 hands off to Ring 2 even on error/skip paths, and the
  idempotency branch re-publishes so one failed publish can't silence the
  arbiter forever.
- C-16/C-47: honest single-provider mode — MAX tier never simulates two
  votes from the same provider.
"""

import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from integrations.arbiter.types import (
    ArbiterDecision,
    ArbiterTier,
    ArbiterVerdict,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_lambda(name: str):
    """Load a Lambda handler by path ('lambda' is a reserved word)."""
    path = REPO_ROOT / "lambda" / name / "handler.py"
    spec = importlib.util.spec_from_file_location(f"{name}_handler", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"{name}_handler"] = mod
    spec.loader.exec_module(mod)
    return mod


def _inconclusive_verdict() -> ArbiterVerdict:
    return ArbiterVerdict(
        decision=ArbiterDecision.INCONCLUSIVE,
        tier=ArbiterTier.STANDARD,
        aggregate_score=0.55,
        confidence=0.4,
        evidence_hash="0xev",
        commitment_hash="0xcm",
        reason="mid-band score",
        disagreement=True,
    )


# ---------------------------------------------------------------------------
# C-13 — Ring 2 Lambda INCONCLUSIVE is advisory-only
# ---------------------------------------------------------------------------


class TestRing2AdvisoryOnly:
    @pytest.mark.asyncio
    async def test_inconclusive_creates_no_dispute_and_never_touches_agent_verdict(
        self, monkeypatch
    ):
        handler = _load_lambda("ring2")

        verdict_updates = []
        dispute_calls = []

        stub = types.ModuleType("supabase_helper")
        stub.get_submission = lambda sid: {
            "id": sid,
            "arbiter_verdict": None,
            "auto_check_details": {},
            "executor": {"id": "ex-1"},
        }
        stub.get_task = lambda tid: {
            "id": tid,
            "agent_id": "agent-1",
            "category": "general",
            "bounty_usd": 5.0,
        }
        stub.is_arbiter_enabled = lambda: True
        stub.emit_verification_event = lambda *a, **k: None

        def _update_verdict(sid, update_data):
            verdict_updates.append(update_data)
            return True

        stub.update_submission_verdict = _update_verdict
        # Tripwires: the advisory handler must never even attempt these.
        stub.create_dispute = lambda *a, **k: dispute_calls.append(a) or {"id": "d"}
        stub.mark_submission_disputed = lambda *a, **k: dispute_calls.append(a)
        stub.write_error_to_submission = lambda *a, **k: None
        monkeypatch.setitem(sys.modules, "supabase_helper", stub)

        arbiter = MagicMock()
        arbiter.evaluate = AsyncMock(return_value=_inconclusive_verdict())

        with patch("integrations.arbiter.service.ArbiterService") as service_cls:
            service_cls.from_defaults.return_value = arbiter
            result = await handler._process_record(
                {
                    "submission_id": "sub-1",
                    "task_id": "task-1",
                    "task": {},
                    "ring1_result": {"passed": True, "score": 0.8},
                }
            )

        assert result["verdict"] == "inconclusive"
        assert dispute_calls == []  # 0 inserts to disputes
        assert len(verdict_updates) == 1
        persisted = verdict_updates[0]
        assert persisted["arbiter_verdict"] == "inconclusive"
        assert "agent_verdict" not in persisted
        assert "agent_notes" not in persisted

    def test_handler_has_no_dispute_path(self):
        """The dispute-creation code must be gone, not just unreached."""
        handler_src = (REPO_ROOT / "lambda" / "ring2" / "handler.py").read_text(
            encoding="utf-8"
        )
        helper_src = (REPO_ROOT / "lambda" / "ring2" / "supabase_helper.py").read_text(
            encoding="utf-8"
        )
        assert "create_dispute" not in handler_src
        assert "mark_submission_disputed" not in handler_src
        assert "create_dispute" not in helper_src
        assert "agent_verdict" not in helper_src.replace(
            "arbiter_verdict", ""
        )  # only arbiter_* columns are written


# ---------------------------------------------------------------------------
# C-07/C-14 — Ring 1 always hands off to Ring 2
# ---------------------------------------------------------------------------


class TestRing1HandsOffToRing2:
    @pytest.mark.asyncio
    async def test_write_error_publishes_to_ring2(self, monkeypatch):
        handler = _load_lambda("ring1")

        async def fake_update(sid, passed, details):
            pass

        stub = types.ModuleType("supabase_helper")
        stub.update_auto_check = fake_update
        monkeypatch.setitem(sys.modules, "supabase_helper", stub)

        published = []
        monkeypatch.setattr(
            handler,
            "_publish_to_ring2",
            lambda sid, tid, result: published.append((sid, tid, result)),
        )

        await handler._write_error(
            "sub-9", "task-9", {"passed": False, "score": 0.2}, "download failed"
        )

        assert len(published) == 1
        sid, tid, result = published[0]
        assert sid == "sub-9"
        assert tid == "task-9"
        assert result["ring1_status"] == "error"

    @pytest.mark.asyncio
    async def test_idempotent_skip_republishes_to_ring2(self, monkeypatch):
        handler = _load_lambda("ring1")

        complete_details = {"ring1_status": "complete", "passed": True, "score": 0.9}

        async def fake_get_submission(sid):
            return {"id": sid, "auto_check_details": complete_details}

        stub = types.ModuleType("supabase_helper")
        stub.get_submission = fake_get_submission
        monkeypatch.setitem(sys.modules, "supabase_helper", stub)

        published = []
        monkeypatch.setattr(
            handler,
            "_publish_to_ring2",
            lambda sid, tid, result: published.append((sid, tid, result)),
        )

        result = await handler._process_submission(
            {
                "submission_id": "sub-2",
                "task_id": "task-2",
                "evidence": {},
                "task": {},
                "photo_urls": ["https://cdn.example.com/a.jpg"],
                "phase_a_result": {},
            }
        )

        assert result["status"] == "skipped"
        assert published == [("sub-2", "task-2", complete_details)]


# ---------------------------------------------------------------------------
# C-16/C-47 — honest single-provider mode (no phantom second vote)
# ---------------------------------------------------------------------------


class TestSingleProviderMode:
    def _provider(self, name: str, completed: bool = True):
        from integrations.arbiter.providers import Ring2Response

        provider = MagicMock()
        provider.name = name
        provider.is_available.return_value = True
        provider.evaluate = AsyncMock(
            return_value=Ring2Response(
                completed=completed,
                confidence=0.9,
                reason="ok",
                model=f"{name}-model",
                provider=name,
                cost_usd=0.001,
            )
        )
        return provider

    @pytest.mark.asyncio
    async def test_max_tier_skips_second_vote_from_same_provider(self):
        from integrations.arbiter.service import ArbiterService

        service = ArbiterService.from_defaults()
        primary = self._provider("openrouter")
        secondary = self._provider("openrouter")

        with (
            patch(
                "integrations.arbiter.providers.get_ring2_provider",
                return_value=primary,
            ),
            patch(
                "integrations.arbiter.providers.get_ring2_secondary_provider",
                return_value=secondary,
            ),
        ):
            scores = await service._run_ring2_inferences(
                task={"category": "general"},
                submission={},
                evidence={},
                tier=ArbiterTier.MAX,
                config=MagicMock(),
                cost_cap_usd=0.2,
            )

        assert len(scores) == 1  # one honest OpenRouter vote
        assert scores[0].provider == "openrouter"
        secondary.evaluate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_max_tier_runs_second_vote_from_distinct_provider(self):
        from integrations.arbiter.service import ArbiterService

        service = ArbiterService.from_defaults()
        primary = self._provider("openrouter")
        secondary = self._provider("eigenai")

        with (
            patch(
                "integrations.arbiter.providers.get_ring2_provider",
                return_value=primary,
            ),
            patch(
                "integrations.arbiter.providers.get_ring2_secondary_provider",
                return_value=secondary,
            ),
        ):
            scores = await service._run_ring2_inferences(
                task={"category": "general"},
                submission={},
                evidence={},
                tier=ArbiterTier.MAX,
                config=MagicMock(),
                cost_cap_usd=0.2,
            )

        assert len(scores) == 2
        assert {s.provider for s in scores} == {"openrouter", "eigenai"}
        secondary.evaluate.assert_awaited_once()
