"""
Tests for the Verification Event Log (emit_verification_event).

Covers: append-only event stream, concurrent writes, ring interleaving,
error suppression.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.verification


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_auto_check_details(**overrides):
    """Create a minimal auto_check_details dict."""
    base = {"passed": False, "verification_events": []}
    base.update(overrides)
    return base


def _make_submission_row(submission_id="sub-001", events=None):
    """Create a minimal submission dict as returned by get_submission."""
    return {
        "id": submission_id,
        "auto_check_details": _make_auto_check_details(
            verification_events=events or [],
        ),
    }


# ---------------------------------------------------------------------------
# TestEmitVerificationEvent
# ---------------------------------------------------------------------------


class TestEmitVerificationEvent:
    @pytest.mark.asyncio
    async def test_emit_event_appends_to_array(self):
        """Emit 3 events sequentially; all 3 appear with correct fields."""
        stored_details = {"passed": False, "verification_events": []}

        async def fake_get_submission(sid):
            return {"id": sid, "auto_check_details": stored_details}

        async def fake_update(submission_id, auto_check_passed, auto_check_details):
            stored_details.update(auto_check_details)

        with patch(
            "verification.events.db.get_submission",
            side_effect=fake_get_submission,
        ):
            with patch(
                "verification.events.db.update_submission_auto_check",
                side_effect=fake_update,
            ):
                from verification.events import emit_verification_event

                await emit_verification_event(
                    "sub-001", ring=1, step="exif_extraction", status="running"
                )
                await emit_verification_event(
                    "sub-001",
                    ring=1,
                    step="exif_extraction",
                    status="complete",
                    detail={"exif_count": 12},
                )
                await emit_verification_event(
                    "sub-001", ring=2, step="arbiter_inference", status="running"
                )

        events = stored_details["verification_events"]
        assert len(events) == 3

        # Verify field structure for each event
        for ev in events:
            assert "ts" in ev
            assert "ring" in ev
            assert "step" in ev
            assert "status" in ev
            assert "detail" in ev

        # Verify specific values
        assert events[0]["ring"] == 1
        assert events[0]["step"] == "exif_extraction"
        assert events[0]["status"] == "running"

        assert events[1]["status"] == "complete"
        assert events[1]["detail"]["exif_count"] == 12

        assert events[2]["ring"] == 2
        assert events[2]["step"] == "arbiter_inference"

    @pytest.mark.asyncio
    async def test_emit_event_concurrent_no_clobber(self):
        """Emit 5 events concurrently via asyncio.gather; all 5 present (lock works)."""
        stored_details = {"passed": False, "verification_events": []}

        async def fake_get_submission(sid):
            # Simulate small delay to increase overlap window
            await asyncio.sleep(0.01)
            return {"id": sid, "auto_check_details": stored_details}

        async def fake_update(submission_id, auto_check_passed, auto_check_details):
            stored_details.update(auto_check_details)

        with patch(
            "verification.events.db.get_submission",
            side_effect=fake_get_submission,
        ):
            with patch(
                "verification.events.db.update_submission_auto_check",
                side_effect=fake_update,
            ):
                from verification.events import emit_verification_event

                await asyncio.gather(
                    emit_verification_event(
                        "sub-001", ring=1, step="step_a", status="running"
                    ),
                    emit_verification_event(
                        "sub-001", ring=1, step="step_b", status="running"
                    ),
                    emit_verification_event(
                        "sub-001", ring=1, step="step_c", status="running"
                    ),
                    emit_verification_event(
                        "sub-001", ring=2, step="step_d", status="running"
                    ),
                    emit_verification_event(
                        "sub-001", ring=2, step="step_e", status="running"
                    ),
                )

        events = stored_details["verification_events"]
        assert len(events) == 5

        step_names = {ev["step"] for ev in events}
        assert step_names == {"step_a", "step_b", "step_c", "step_d", "step_e"}

    @pytest.mark.asyncio
    async def test_emit_event_ring1_and_ring2_interleaved(self):
        """Ring 1 and Ring 2 events emitted alternately; ordering preserved."""
        stored_details = {"passed": False, "verification_events": []}

        async def fake_get_submission(sid):
            return {"id": sid, "auto_check_details": stored_details}

        async def fake_update(submission_id, auto_check_passed, auto_check_details):
            stored_details.update(auto_check_details)

        with patch(
            "verification.events.db.get_submission",
            side_effect=fake_get_submission,
        ):
            with patch(
                "verification.events.db.update_submission_auto_check",
                side_effect=fake_update,
            ):
                from verification.events import emit_verification_event

                # Alternate ring 1 / ring 2
                await emit_verification_event(
                    "sub-001", ring=1, step="exif", status="running"
                )
                await emit_verification_event(
                    "sub-001", ring=2, step="arbiter", status="running"
                )
                await emit_verification_event(
                    "sub-001", ring=1, step="exif", status="complete"
                )
                await emit_verification_event(
                    "sub-001", ring=2, step="arbiter", status="complete"
                )

        events = stored_details["verification_events"]
        assert len(events) == 4

        # Verify sequential ordering preserved
        assert events[0] == {
            "ts": events[0]["ts"],
            "ring": 1,
            "step": "exif",
            "status": "running",
            "detail": {},
        }
        assert events[1]["ring"] == 2
        assert events[2]["ring"] == 1
        assert events[3]["ring"] == 2

        # Ring ordering: 1, 2, 1, 2
        rings = [ev["ring"] for ev in events]
        assert rings == [1, 2, 1, 2]

    @pytest.mark.asyncio
    async def test_emit_event_never_raises(self):
        """When DB raises, emit returns without exception."""
        with patch(
            "verification.events.db.get_submission",
            new_callable=AsyncMock,
            side_effect=Exception("DB connection lost"),
        ):
            from verification.events import emit_verification_event

            # Must not raise
            await emit_verification_event(
                "sub-001", ring=1, step="exif", status="running"
            )

    @pytest.mark.asyncio
    async def test_emit_event_update_raises_no_propagation(self):
        """When update_submission_auto_check raises, emit swallows the error."""
        with patch(
            "verification.events.db.get_submission",
            new_callable=AsyncMock,
            return_value=_make_submission_row(),
        ):
            with patch(
                "verification.events.db.update_submission_auto_check",
                new_callable=AsyncMock,
                side_effect=Exception("Update failed"),
            ):
                from verification.events import emit_verification_event

                # Must not raise
                await emit_verification_event(
                    "sub-001", ring=1, step="exif", status="running"
                )

    @pytest.mark.asyncio
    async def test_emit_event_none_submission(self):
        """When get_submission returns None, emit handles gracefully."""
        with patch(
            "verification.events.db.get_submission",
            new_callable=AsyncMock,
            return_value=None,
        ):
            with patch(
                "verification.events.db.update_submission_auto_check",
                new_callable=AsyncMock,
            ) as mock_update:
                from verification.events import emit_verification_event

                # Must not raise
                await emit_verification_event(
                    "sub-001", ring=1, step="exif", status="running"
                )
                # Should still attempt update with the new event
                mock_update.assert_called_once()
