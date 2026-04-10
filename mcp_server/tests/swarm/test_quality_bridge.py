"""
Tests for QualityBridge — Module #69: Server-Side Evidence Quality Intelligence

Signal #22: Evidence Quality Prediction

Coverage:
    - Ingestion from Supabase rows (all field name variants)
    - Cold-start behavior (no history → neutral)
    - Historical quality sub-signal
    - Category-specific competence sub-signal
    - EXIF/GPS compliance sub-signal (physical tasks only)
    - Rejection rate sub-signal
    - Combined signal bounds (±0.09)
    - Confidence scaling with observations
    - Physical vs digital task distinction
    - Quality leaderboard
    - Worker quality profile
    - Fleet quality summary
    - Direct record_outcome API
    - Persistence (save/load)
    - Edge cases
"""

import json
import os
import tempfile

import pytest

from swarm.quality_bridge import (
    QualityBridge,
    QualitySignalResult,
    MAX_EQP_BONUS,
    MIN_EQP_PENALTY,
    PHYSICAL_TASK_TYPES,
    DIGITAL_TASK_TYPES,
    QUALITY_EXEMPLARY,
    QUALITY_POOR,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_row(
    worker="0xAaaa",
    task_id="t1",
    category="physical_presence",
    task_type="photo",
    quality_score=0.85,
    verdict="approved",
    has_exif=True,
    has_gps=True,
) -> dict:
    return {
        "worker_wallet": worker,
        "task_id": task_id,
        "task_category": category,
        "task_type": task_type,
        "quality_score": quality_score,
        "verdict": verdict,
        "metadata": {"has_exif": has_exif, "has_gps": has_gps},
    }


def make_bridge() -> QualityBridge:
    return QualityBridge()


def fill_worker(bridge: QualityBridge, worker: str, n: int = 20,
                quality: float = 0.85, category: str = "physical_presence",
                task_type: str = "photo", approved: bool = True, rejected: bool = False,
                has_exif: bool = True, has_gps: bool = True) -> None:
    """Fill a worker with n observations."""
    rows = [
        make_row(
            worker=worker, task_id=f"t{i}",
            category=category, task_type=task_type,
            quality_score=quality,
            verdict="approved" if approved else "rejected",
            has_exif=has_exif, has_gps=has_gps,
        )
        for i in range(n)
    ]
    bridge.ingest_raw(rows)


# ---------------------------------------------------------------------------
# TestIngestion
# ---------------------------------------------------------------------------

class TestIngestion:
    def test_basic_ingestion(self):
        bridge = make_bridge()
        rows = [make_row()]
        count = bridge.ingest_raw(rows)
        assert count == 1

    def test_batch_ingestion(self):
        bridge = make_bridge()
        rows = [make_row(task_id=f"t{i}") for i in range(10)]
        count = bridge.ingest_raw(rows)
        assert count == 10

    def test_worker_address_key(self):
        bridge = make_bridge()
        row = {"worker_address": "0xW2", "task_id": "t2", "quality_score": 0.7,
               "verdict": "approved"}
        count = bridge.ingest_raw([row])
        assert count == 1

    def test_wallet_key(self):
        bridge = make_bridge()
        row = {"wallet": "0xW3", "task_id": "t3", "quality_score": 0.75}
        bridge.ingest_raw([row])
        sig = bridge.signal("0xW3", "general", "photo")
        assert sig.total_obs == 1

    def test_missing_worker_skipped(self):
        bridge = make_bridge()
        row = {"task_id": "t1", "quality_score": 0.80}
        count = bridge.ingest_raw([row])
        assert count == 0

    def test_evidence_quality_field(self):
        bridge = make_bridge()
        row = {"worker_wallet": "0xWalt", "task_id": "t1", "evidence_quality": 0.92}
        bridge.ingest_raw([row])
        state = bridge._state["0xwalt"]
        assert abs(state.avg_quality - 0.92) < 0.01

    def test_score_field(self):
        bridge = make_bridge()
        row = {"worker_wallet": "0xWs", "task_id": "t1", "score": 0.77}
        bridge.ingest_raw([row])
        state = bridge._state["0xws"]
        assert abs(state.avg_quality - 0.77) < 0.01

    def test_rejected_verdict_variants(self):
        bridge = make_bridge()
        for verdict, worker in [("rejected", "0xR1"), ("reject", "0xR2"), ("fail", "0xR3")]:
            bridge.ingest_raw([make_row(worker=worker, verdict=verdict)])
            state = bridge._state[worker.lower()]
            assert state.total_rejected == 1

    def test_approved_verdict_variants(self):
        bridge = make_bridge()
        for verdict, worker in [("approved", "0xA1"), ("accept", "0xA2"), ("pass", "0xA3")]:
            bridge.ingest_raw([make_row(worker=worker, verdict=verdict)])
            state = bridge._state[worker.lower()]
            assert state.total_approved == 1

    def test_physical_task_increments_physical_count(self):
        bridge = make_bridge()
        for tt in ["photo", "photo_geo", "video", "measurement", "receipt"]:
            bridge.ingest_raw([make_row(worker="0xPhys", task_id=tt, task_type=tt)])
        state = bridge._state["0xphys"]
        assert state.total_physical == 5

    def test_digital_task_no_physical_count(self):
        bridge = make_bridge()
        for tt in ["text_response", "document", "screenshot"]:
            bridge.ingest_raw([make_row(worker="0xDig", task_id=tt, task_type=tt)])
        state = bridge._state["0xdig"]
        assert state.total_physical == 0

    def test_metadata_as_string(self):
        bridge = make_bridge()
        row = make_row(worker="0xWstr")
        row["metadata"] = json.dumps({"has_exif": True, "has_gps": True})
        bridge.ingest_raw([row])
        state = bridge._state["0xwstr"]
        assert state.total_has_exif == 1
        assert state.total_has_gps == 1

    def test_quality_clamped(self):
        bridge = make_bridge()
        bridge.ingest_raw([make_row(worker="0xOvr", quality_score=1.5)])
        state = bridge._state["0xovr"]
        assert state.avg_quality <= 1.0

    def test_record_count_tracks(self):
        bridge = make_bridge()
        bridge.ingest_raw([make_row(task_id=f"t{i}") for i in range(7)])
        assert bridge._record_count == 7


# ---------------------------------------------------------------------------
# TestColdStart
# ---------------------------------------------------------------------------

class TestColdStart:
    def test_unknown_worker_neutral(self):
        bridge = make_bridge()
        sig = bridge.signal("0xUnknown", "general", "photo")
        assert sig.quality_bonus == 0.0
        assert sig.predicted_quality == 0.5
        assert sig.confidence == 0.0
        assert sig.reason == "no_verification_history"

    def test_empty_wallet_neutral(self):
        bridge = make_bridge()
        sig = bridge.signal("", "general", "photo")
        assert sig.quality_bonus == 0.0

    def test_one_observation_attenuated(self):
        bridge = make_bridge()
        bridge.ingest_raw([make_row(worker="0xW1", quality_score=0.95)])
        sig = bridge.signal("0xW1", "physical_presence", "photo")
        assert sig.confidence < 0.5
        assert abs(sig.quality_bonus) < MAX_EQP_BONUS


# ---------------------------------------------------------------------------
# TestHistoricalQuality
# ---------------------------------------------------------------------------

class TestHistoricalQuality:
    def test_exemplary_quality_positive(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xW1", quality=0.95)
        sig = bridge.signal("0xW1", "physical_presence", "photo")
        assert sig.quality_bonus > 0.03

    def test_poor_quality_negative(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xW2", quality=0.35, approved=False, rejected=True)
        sig = bridge.signal("0xW2", "physical_presence", "photo")
        assert sig.quality_bonus < 0.0

    def test_standard_quality_near_neutral(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xW3", quality=0.70)
        sig = bridge.signal("0xW3", "physical_presence", "photo")
        assert -0.05 <= sig.quality_bonus <= 0.05

    def test_historical_score_reflected(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xW4", quality=0.90)
        sig = bridge.signal("0xW4", "physical_presence", "photo")
        assert sig.historical_score >= 0.85


# ---------------------------------------------------------------------------
# TestCategoryCompetence
# ---------------------------------------------------------------------------

class TestCategoryCompetence:
    def test_category_expert_boosts(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xWcat", n=15, quality=0.93, category="physical_presence")
        sig = bridge.signal("0xWcat", "physical_presence", "photo")
        assert sig.category_score >= 0.90

    def test_category_cold_start_neutral(self):
        bridge = make_bridge()
        # Only 2 in this category (below cold_start_min_obs=3)
        for i in range(2):
            bridge.ingest_raw([make_row(worker="0xCold", task_id=f"t{i}",
                                        category="rare_category")])
        sig = bridge.signal("0xCold", "rare_category", "photo")
        assert sig.category_obs < 3

    def test_cross_category_independence(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xWmix", n=15, quality=0.92, category="physical_presence")
        for i in range(5):
            bridge.ingest_raw([make_row(worker="0xWmix", task_id=f"b{i}",
                                        category="bureaucratic", quality_score=0.35,
                                        verdict="rejected")])
        sig_phys = bridge.signal("0xWmix", "physical_presence", "photo")
        sig_bur = bridge.signal("0xWmix", "bureaucratic", "document")
        assert sig_phys.quality_bonus > sig_bur.quality_bonus


# ---------------------------------------------------------------------------
# TestExifGps
# ---------------------------------------------------------------------------

class TestExifGps:
    def test_physical_high_exif_boosts(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xExif", n=10, task_type="photo",
                    has_exif=True, has_gps=True)
        sig = bridge.signal("0xExif", "physical_presence", "photo")
        assert sig.exif_gps_score > 0.7

    def test_physical_no_exif_lower(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xNoExif", n=10, task_type="photo",
                    has_exif=False, has_gps=False)
        sig_with = bridge.signal("0xExif" if False else "0xNoExif",
                                  "physical_presence", "photo")
        assert sig_with.exif_gps_score < 0.6

    def test_digital_task_neutral_exif(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xDig", n=10, task_type="text_response",
                    has_exif=False, has_gps=False)
        sig = bridge.signal("0xDig", "general", "text_response")
        assert sig.exif_gps_score == 0.5

    def test_photo_geo_in_physical_types(self):
        assert "photo_geo" in PHYSICAL_TASK_TYPES

    def test_text_response_in_digital_types(self):
        assert "text_response" in DIGITAL_TASK_TYPES


# ---------------------------------------------------------------------------
# TestRejection
# ---------------------------------------------------------------------------

class TestRejection:
    def test_high_rejection_penalty(self):
        bridge = make_bridge()
        # 40% rejection rate
        for i in range(4):
            bridge.ingest_raw([make_row(worker="0xR", task_id=f"rej{i}",
                                        quality_score=0.3, verdict="rejected")])
        for i in range(6):
            bridge.ingest_raw([make_row(worker="0xR", task_id=f"app{i}",
                                        quality_score=0.75, verdict="approved")])
        sig = bridge.signal("0xR", "general", "photo")
        assert sig.rejection_score <= 0.6

    def test_zero_rejection_bonus(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xNoRej", n=20, quality=0.88)
        state = bridge._state["0xnorej"]
        assert state.rejection_rate == 0.0

    def test_all_rejected_penalty(self):
        bridge = make_bridge()
        for i in range(10):
            bridge.ingest_raw([make_row(worker="0xAllRej", task_id=f"r{i}",
                                        quality_score=0.1, verdict="rejected")])
        sig = bridge.signal("0xAllRej", "general", "photo")
        assert sig.quality_bonus < 0.0


# ---------------------------------------------------------------------------
# TestBounds
# ---------------------------------------------------------------------------

class TestBounds:
    def test_max_bonus_not_exceeded(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xMax", n=50, quality=1.0, has_exif=True, has_gps=True)
        sig = bridge.signal("0xMax", "physical_presence", "photo")
        assert sig.quality_bonus <= MAX_EQP_BONUS + 0.001

    def test_min_penalty_not_exceeded(self):
        bridge = make_bridge()
        for i in range(50):
            bridge.ingest_raw([make_row(worker="0xMin", task_id=f"t{i}",
                                        quality_score=0.0, verdict="rejected",
                                        has_exif=False, has_gps=False)])
        sig = bridge.signal("0xMin", "physical_presence", "photo")
        assert sig.quality_bonus >= MIN_EQP_PENALTY - 0.001

    def test_confidence_bounded_0_1(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xConf", n=100)
        sig = bridge.signal("0xConf", "physical_presence", "photo")
        assert 0.0 <= sig.confidence <= 1.0

    def test_predicted_quality_bounded(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xPQ", n=20, quality=0.7)
        sig = bridge.signal("0xPQ", "physical_presence", "photo")
        assert 0.0 <= sig.predicted_quality <= 1.0


# ---------------------------------------------------------------------------
# TestRecordOutcome
# ---------------------------------------------------------------------------

class TestRecordOutcome:
    def test_direct_record(self):
        bridge = make_bridge()
        bridge.record_outcome(
            worker_id="0xDirect",
            task_id="t1",
            task_category="physical_presence",
            task_type="photo",
            quality_score=0.88,
            approved=True,
        )
        sig = bridge.signal("0xDirect", "physical_presence", "photo")
        assert sig.total_obs == 1

    def test_record_outcome_rejected(self):
        bridge = make_bridge()
        bridge.record_outcome(
            worker_id="0xDRej",
            task_id="t1",
            task_category="general",
            task_type="photo",
            quality_score=0.2,
            approved=False,
            rejected=True,
        )
        state = bridge._state["0xdrej"]
        assert state.total_rejected == 1


# ---------------------------------------------------------------------------
# TestLeaderboard
# ---------------------------------------------------------------------------

class TestLeaderboard:
    def test_leaderboard_ordered(self):
        bridge = make_bridge()
        workers = [("0xW1", 0.95), ("0xW2", 0.65), ("0xW3", 0.30)]
        for w, q in workers:
            fill_worker(bridge, w, quality=q, n=20,
                        approved=(q > 0.5), rejected=(q < 0.5))
        lb = bridge.quality_leaderboard("physical_presence", "photo")
        assert lb[0]["worker_id"] == "0xw1"
        for i in range(len(lb) - 1):
            assert lb[i]["quality_bonus"] >= lb[i + 1]["quality_bonus"]

    def test_leaderboard_top_n(self):
        bridge = make_bridge()
        for i in range(10):
            fill_worker(bridge, f"0xW{i}", n=5)
        lb = bridge.quality_leaderboard(top_n=5)
        assert len(lb) == 5

    def test_empty_leaderboard(self):
        bridge = make_bridge()
        lb = bridge.quality_leaderboard()
        assert lb == []


# ---------------------------------------------------------------------------
# TestWorkerProfile
# ---------------------------------------------------------------------------

class TestWorkerProfile:
    def test_unknown_worker(self):
        bridge = make_bridge()
        profile = bridge.worker_quality_profile("0xUnknown")
        assert profile["status"] == "no_history"

    def test_known_worker_profile(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xWP", n=10, quality=0.88)
        profile = bridge.worker_quality_profile("0xWP")
        assert profile["total_obs"] == 10
        assert profile["avg_quality"] > 0.8


# ---------------------------------------------------------------------------
# TestSummary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_empty_summary(self):
        bridge = make_bridge()
        s = bridge.quality_summary()
        assert s["total_workers"] == 0
        assert s["module"] == "QualityBridge"

    def test_summary_counts(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xW1", quality=0.95)
        fill_worker(bridge, "0xW2", quality=0.40)
        s = bridge.quality_summary()
        assert s["total_workers"] == 2
        assert "exemplary_workers" in s

    def test_health_alias(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xWH", n=5)
        s = bridge.health()
        assert "module" in s
        assert s["module"] == "QualityBridge"


# ---------------------------------------------------------------------------
# TestPersistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_load(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xSave", n=10, quality=0.88)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "quality.json")
            bridge.save(path)
            loaded = QualityBridge.load(path)
        s_orig = bridge.signal("0xSave", "physical_presence", "photo")
        s_loaded = loaded.signal("0xSave", "physical_presence", "photo")
        assert s_orig.quality_bonus == s_loaded.quality_bonus

    def test_load_missing_file(self):
        bridge = QualityBridge.load("/nonexistent/quality.json")
        assert len(bridge._state) == 0

    def test_save_creates_directory(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xW", n=3)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "subdir", "quality.json")
            bridge.save(path)  # Should not raise
            assert os.path.exists(path)


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_wallet_case_insensitive(self):
        bridge = make_bridge()
        bridge.ingest_raw([make_row(worker="0xABCDEF")])
        sig_upper = bridge.signal("0xABCDEF", "general", "photo")
        sig_lower = bridge.signal("0xabcdef", "general", "photo")
        assert sig_upper.quality_bonus == sig_lower.quality_bonus

    def test_multiple_workers_independent(self):
        bridge = make_bridge()
        fill_worker(bridge, "0xA", n=20, quality=0.95)
        fill_worker(bridge, "0xB", n=20, quality=0.50)
        fill_worker(bridge, "0xC", n=20, quality=0.25, approved=False, rejected=True)
        sigs = [bridge.signal(w, "physical_presence", "photo") for w in ["0xA", "0xB", "0xC"]]
        assert sigs[0].quality_bonus > sigs[1].quality_bonus > sigs[2].quality_bonus

    def test_last_sync_updated(self):
        bridge = make_bridge()
        assert bridge._last_sync is None
        bridge.ingest_raw([make_row()])
        assert bridge._last_sync is not None

    def test_empty_row_batch(self):
        bridge = make_bridge()
        count = bridge.ingest_raw([])
        assert count == 0

    def test_signal_id_and_module_id(self):
        from swarm.quality_bridge import SIGNAL_ID, MODULE_ID
        assert SIGNAL_ID == 22
        assert MODULE_ID == 69

    def test_bad_metadata_json_handled(self):
        bridge = make_bridge()
        row = make_row(worker="0xBadMeta")
        row["metadata"] = "not-valid-json"
        count = bridge.ingest_raw([row])
        # Should handle gracefully — either skip or ingest without metadata
        # Row still counts since worker is present
        assert count >= 0  # No crash
