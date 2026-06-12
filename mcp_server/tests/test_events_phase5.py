"""Phase 5 of the Rings Verification fixes — reliable forensic events.

Covers:
- C-05/C-22/C-30: merge_phase_b and the final write must not destroy the
  verification_events log.
- C-06/C-10/C-23: emitters use the atomic append_verification_event RPC
  (migration 121), with a legacy fallback pre-migration.
- C-08: an unhandled exception in the Ring 1 Lambda still writes a
  terminal error state (no eternal 'running').
"""

import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_ring1():
    path = REPO_ROOT / "lambda" / "ring1" / "handler.py"
    spec = importlib.util.spec_from_file_location("ring1_handler", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ring1_handler"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# C-05/C-22 — merge_phase_b preserves the event log
# ---------------------------------------------------------------------------


class TestMergePreservesEvents:
    def test_merge_phase_b_keeps_verification_events(self):
        from verification.pipeline import CheckResult, merge_phase_b

        events = [
            {"ts": 1, "ring": 1, "step": "exif_extraction", "status": "complete"},
            {"ts": 2, "ring": 1, "step": "tampering", "status": "running"},
        ]
        existing = {
            "passed": True,
            "score": 0.8,
            "checks": [
                {"name": "schema", "passed": True, "score": 1.0, "reason": None}
            ],
            "warnings": [],
            "phase": "A",
            "verification_events": events,
        }
        merged = merge_phase_b(
            existing,
            [CheckResult(name="tampering", passed=True, score=0.9)],
        )
        assert merged["verification_events"] == events
        assert merged["phase"] == "AB"

    def test_merge_phase_b_without_events_adds_none(self):
        from verification.pipeline import CheckResult, merge_phase_b

        existing = {
            "passed": True,
            "score": 0.8,
            "checks": [],
            "warnings": [],
            "phase": "A",
        }
        merged = merge_phase_b(
            existing, [CheckResult(name="tampering", passed=True, score=0.9)]
        )
        assert "verification_events" not in merged


# ---------------------------------------------------------------------------
# C-06/C-10/C-23 — atomic RPC emit with legacy fallback
# ---------------------------------------------------------------------------


class TestAtomicEmit:
    @pytest.mark.asyncio
    async def test_emit_uses_rpc(self, monkeypatch):
        import verification.events as events_mod

        rpc_calls = []
        client = MagicMock()

        def fake_rpc(name, params):
            rpc_calls.append((name, params))
            return MagicMock()  # .execute() succeeds

        client.rpc.side_effect = fake_rpc
        monkeypatch.setattr(events_mod.db, "get_client", lambda: client)

        await events_mod.emit_verification_event("sub-1", 1, "tampering", "complete")

        assert len(rpc_calls) == 1
        name, params = rpc_calls[0]
        assert name == "append_verification_event"
        assert params["p_submission_id"] == "sub-1"
        assert params["p_event"]["step"] == "tampering"
        assert params["p_event"]["status"] == "complete"

    @pytest.mark.asyncio
    async def test_ten_parallel_emits_all_reach_rpc(self, monkeypatch):
        """All concurrent emits land — no read-modify-write race drops any."""
        import verification.events as events_mod

        rpc_calls = []
        client = MagicMock()
        client.rpc.side_effect = lambda name, params: (
            rpc_calls.append(params["p_event"]["step"]) or MagicMock()
        )
        monkeypatch.setattr(events_mod.db, "get_client", lambda: client)

        await asyncio.gather(
            *[
                events_mod.emit_verification_event("sub-1", 1, f"step_{i}", "complete")
                for i in range(10)
            ]
        )

        assert sorted(rpc_calls) == sorted(f"step_{i}" for i in range(10))

    @pytest.mark.asyncio
    async def test_emit_falls_back_when_rpc_missing(self, monkeypatch):
        import verification.events as events_mod

        client = MagicMock()
        client.rpc.side_effect = RuntimeError("PGRST202: function not found")
        monkeypatch.setattr(events_mod.db, "get_client", lambda: client)

        async def fake_get_submission(sid):
            return {"id": sid, "auto_check_details": {"passed": True}}

        legacy_writes = []

        async def fake_update(submission_id, auto_check_passed, auto_check_details):
            legacy_writes.append(auto_check_details)

        monkeypatch.setattr(events_mod.db, "get_submission", fake_get_submission)
        monkeypatch.setattr(events_mod.db, "update_submission_auto_check", fake_update)

        await events_mod.emit_verification_event("sub-1", 1, "tampering", "complete")

        assert len(legacy_writes) == 1
        evts = legacy_writes[0]["verification_events"]
        assert len(evts) == 1
        assert evts[0]["step"] == "tampering"


# ---------------------------------------------------------------------------
# C-08 — unhandled Lambda exception still writes a terminal state
# ---------------------------------------------------------------------------


@pytest.mark.ring1_lambda
class TestTerminalWriteOnCrash:
    def test_unhandled_exception_writes_error_and_reraises(self, monkeypatch):
        handler = _load_ring1()

        writes = []

        async def fake_update(submission_id, passed, details):
            writes.append((submission_id, passed, details))

        stub = types.ModuleType("supabase_helper")
        stub.update_auto_check = fake_update
        monkeypatch.setitem(sys.modules, "supabase_helper", stub)
        monkeypatch.setattr(handler, "_load_secrets", lambda: None)
        monkeypatch.setattr(handler, "_publish_to_ring2", lambda *a, **k: None)

        async def boom(body):
            raise RuntimeError("mid-run explosion")

        monkeypatch.setattr(handler, "_process_submission", boom)

        event = {
            "Records": [
                {
                    "body": json.dumps(
                        {
                            "submission_id": "sub-7",
                            "task_id": "task-7",
                            "phase_a_result": {"passed": True, "score": 0.9},
                        }
                    )
                }
            ]
        }

        with pytest.raises(RuntimeError, match="mid-run explosion"):
            handler.lambda_handler(event, None)

        assert len(writes) == 1
        submission_id, passed, details = writes[0]
        assert submission_id == "sub-7"
        assert passed is False
        assert details["ring1_status"] == "error"
        assert "mid-run explosion" in details["ring1_error"]
        assert details["review_required"] is True
