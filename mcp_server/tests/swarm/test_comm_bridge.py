"""
Tests for CommBridge — Module #70: Server-Side Communication Quality Intelligence

Coverage:
    - CommRecord and WorkerCommProfile data structures
    - CommBridge initialization
    - Ingestion: ingest_raw, full_refresh
    - Row parsing: all EM field name variants
    - Signal computation: cold start, silent workers, full profiles
    - Sub-signals: response latency, clarity, engagement, outcome
    - Confidence scaling: sparse vs mature data
    - Bonus bounds: ±0.07 enforced
    - Leaderboard, silent workers, fleet summary
    - Worker profile breakdown
    - Persistence: save/load roundtrip
    - Health endpoint
"""

import json
import os
import tempfile
import pytest

from mcp_server.swarm.comm_bridge import (
    CommBridge,
    CommRecord,
    WorkerCommProfile,
    CommSignal,
    MAX_COMM_BONUS,
    MIN_COMM_PENALTY,
    MIN_COMM_OBSERVATIONS,
    OPTIMAL_MESSAGE_COUNT,
    RESPONSE_DECAY_HOURS,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def make_row(
    worker_wallet: str = "0xWorker",
    task_id: str = "task-001",
    status: str = "approved",
    response_time_seconds: float = 300.0,
    message_count: int = 3,
    avg_message_length: float = 80.0,
    has_question: bool = False,
    has_resolution_keyword: bool = True,
    has_escalation_keyword: bool = False,
    task_category: str = "photo",
) -> dict:
    return {
        "worker_wallet": worker_wallet,
        "task_id": task_id,
        "task_category": task_category,
        "status": status,
        "response_time_seconds": response_time_seconds,
        "message_count": message_count,
        "avg_message_length": avg_message_length,
        "has_question": has_question,
        "has_resolution_keyword": has_resolution_keyword,
        "has_escalation_keyword": has_escalation_keyword,
    }


def seed_bridge(bridge: CommBridge, worker_id: str = "0xWorker", count: int = 20, **kwargs) -> None:
    rows = [
        make_row(worker_wallet=worker_id, task_id=f"task-{i:03d}", **kwargs)
        for i in range(count)
    ]
    bridge.ingest_raw(rows)


# ─── CommRecord ───────────────────────────────────────────────────────────────

class TestCommRecord:
    def test_basic_creation(self):
        rec = CommRecord(
            worker_id="0xW",
            task_id="t1",
            task_category="photo",
            outcome="approved",
            response_time_seconds=300.0,
            message_count=3,
            avg_message_length=80.0,
            asked_clarifying_question=False,
            used_resolution_keyword=True,
            used_escalation_keyword=False,
        )
        assert rec.worker_id == "0xW"
        assert rec.outcome == "approved"
        assert rec.message_count == 3


# ─── WorkerCommProfile ────────────────────────────────────────────────────────

class TestWorkerCommProfile:
    def test_empty_profile(self):
        p = WorkerCommProfile("0xW")
        assert p.task_count == 0
        assert p.communicating_task_count == 0

    def test_apply_communicating_record(self):
        p = WorkerCommProfile("0xW")
        rec = CommRecord("0xW", "t1", "photo", "approved", 300.0, 3, 80.0, False, True, False)
        p.apply(rec)
        assert p.task_count == 1
        assert p.communicating_task_count == 1
        assert p.total_messages == 3

    def test_apply_silent_record(self):
        p = WorkerCommProfile("0xW")
        rec = CommRecord("0xW", "t1", "photo", "approved", 0.0, 0, 0.0, False, False, False)
        p.apply(rec)
        assert p.task_count == 1
        assert p.silent_task_count == 1
        assert p.communicating_task_count == 0

    def test_avg_response_no_comm(self):
        p = WorkerCommProfile("0xW")
        rec = CommRecord("0xW", "t1", "photo", "approved", 0.0, 0, 0.0, False, False, False)
        p.apply(rec)
        assert p.avg_response_time_seconds == 0.0

    def test_comm_approved_rate_all_approved(self):
        p = WorkerCommProfile("0xW")
        for i in range(8):
            p.apply(CommRecord("0xW", f"t{i}", "photo", "approved", 300.0, 2, 60.0, False, False, False))
        assert p.comm_approved_rate == 1.0

    def test_comm_approved_rate_never_communicated(self):
        p = WorkerCommProfile("0xW")
        p.apply(CommRecord("0xW", "t1", "photo", "approved", 0.0, 0, 0.0, False, False, False))
        assert p.comm_approved_rate == 0.5  # Neutral

    def test_avg_messages_per_task(self):
        p = WorkerCommProfile("0xW")
        p.apply(CommRecord("0xW", "t1", "photo", "approved", 300.0, 2, 60.0, False, False, False))
        p.apply(CommRecord("0xW", "t2", "photo", "approved", 300.0, 4, 60.0, False, False, False))
        assert p.avg_messages_per_task == 3.0


# ─── CommBridge Init ─────────────────────────────────────────────────────────

class TestCommBridgeInit:
    def test_empty_init(self):
        bridge = CommBridge()
        assert len(bridge._profiles) == 0
        assert bridge._total_records == 0

    def test_empty_summary(self):
        bridge = CommBridge()
        summary = bridge.comm_summary()
        assert summary["worker_count"] == 0
        assert summary["module_id"] == 70
        assert summary["signal_id"] == 23


# ─── Ingestion ────────────────────────────────────────────────────────────────

class TestIngestion:
    def test_ingest_single_row(self):
        bridge = CommBridge()
        bridge.ingest_raw([make_row()])
        assert "0xWorker" in bridge._profiles

    def test_ingest_batch(self):
        bridge = CommBridge()
        rows = [make_row(task_id=f"t{i}") for i in range(5)]
        count = bridge.ingest_raw(rows)
        assert count == 5
        assert bridge._profiles["0xWorker"].task_count == 5

    def test_missing_worker_skipped(self):
        bridge = CommBridge()
        rows = [{"task_id": "t1", "status": "approved"}]
        count = bridge.ingest_raw(rows)
        assert count == 0

    def test_full_refresh_clears_old_data(self):
        bridge = CommBridge()
        bridge.ingest_raw([make_row(worker_wallet="0xOld", task_id="old-task")])
        bridge.full_refresh([make_row(worker_wallet="0xNew", task_id="new-task")])
        assert "0xNew" in bridge._profiles
        assert "0xOld" not in bridge._profiles

    def test_total_records_tracked(self):
        bridge = CommBridge()
        bridge.ingest_raw([make_row(task_id=f"t{i}") for i in range(5)])
        bridge.ingest_raw([make_row(task_id=f"t{i+5}") for i in range(3)])
        assert bridge._total_records == 8

    def test_sync_count_increments(self):
        bridge = CommBridge()
        bridge.ingest_raw([make_row()])
        bridge.ingest_raw([make_row(task_id="t2")])
        assert bridge._sync_count == 2


# ─── Row Parsing: Field Variants ─────────────────────────────────────────────

class TestRowParsing:
    def test_worker_wallet_field(self):
        bridge = CommBridge()
        bridge.ingest_raw([{"worker_wallet": "0xW1", "task_id": "t1", "status": "approved",
                             "message_count": 2}])
        assert "0xW1" in bridge._profiles

    def test_worker_address_field(self):
        bridge = CommBridge()
        bridge.ingest_raw([{"worker_address": "0xW2", "task_id": "t2", "verdict": "pass",
                             "message_count": 2}])
        assert "0xW2" in bridge._profiles

    def test_wallet_field(self):
        bridge = CommBridge()
        bridge.ingest_raw([{"wallet": "0xW3", "id": "t3", "outcome": "success",
                             "message_count": 2}])
        assert "0xW3" in bridge._profiles

    def test_worker_id_field(self):
        bridge = CommBridge()
        bridge.ingest_raw([{"worker_id": "0xW4", "task_id": "t4", "status": "approved",
                             "message_count": 1}])
        assert "0xW4" in bridge._profiles

    def test_verdict_field(self):
        bridge = CommBridge()
        bridge.ingest_raw([{"worker_wallet": "0xW", "task_id": "t", "verdict": "pass",
                             "message_count": 2}])
        sig = bridge.signal("0xW")
        assert sig.sample_size == 1

    def test_outcome_normalization_all_variants(self):
        bridge = CommBridge()
        cases = [
            ("approved", "approved"),
            ("pass", "approved"),
            ("success", "approved"),
            ("rejected", "rejected"),
            ("fail", "rejected"),
            ("failed", "rejected"),
            ("cancelled", "cancelled"),
            ("canceled", "cancelled"),
            ("expired", "expired"),
        ]
        for raw, expected in cases:
            bridge2 = CommBridge()
            rec = bridge2._parse_row({"worker_wallet": "0xW", "task_id": "t", "status": raw,
                                      "message_count": 2})
            assert rec is not None
            assert rec.outcome == expected, f"Failed for {raw}"

    def test_zero_message_count_defaults_to_silent(self):
        bridge = CommBridge()
        bridge.ingest_raw([{"worker_wallet": "0xSilent", "task_id": "t1", "status": "approved"}])
        profile = bridge._profiles.get("0xSilent")
        assert profile is not None
        assert profile.silent_task_count == 1

    def test_missing_comm_fields_default_to_zero(self):
        bridge = CommBridge()
        bridge.ingest_raw([{"worker_wallet": "0xMinimal", "task_id": "t", "status": "approved"}])
        profile = bridge._profiles.get("0xMinimal")
        assert profile.silent_task_count == 1  # message_count defaults to 0


# ─── Cold Start / Silent Workers ─────────────────────────────────────────────

class TestColdStartAndSilent:
    def test_unknown_worker_neutral(self):
        bridge = CommBridge()
        sig = bridge.signal("0xUnknown")
        assert sig.comm_bonus == 0.0
        assert sig.confidence == 0.0
        assert sig.sample_size == 0
        assert "no communication data" in sig.reason

    def test_silent_worker_neutral(self):
        bridge = CommBridge()
        rows = [make_row(worker_wallet="0xSilent", task_id=f"t{i}", message_count=0)
                for i in range(10)]
        bridge.ingest_raw(rows)
        sig = bridge.signal("0xSilent")
        assert sig.comm_bonus == 0.0
        assert sig.confidence == 0.0
        assert "silent" in sig.reason

    def test_one_comm_task_low_confidence(self):
        bridge = CommBridge()
        bridge.ingest_raw([make_row()])
        sig = bridge.signal("0xWorker")
        assert sig.confidence < 0.5
        assert abs(sig.comm_bonus) < MAX_COMM_BONUS * 0.5


# ─── Sub-signals ─────────────────────────────────────────────────────────────

class TestResponseLatency:
    def test_instant_response_high_score(self):
        bridge = CommBridge()
        seed_bridge(bridge, response_time_seconds=30.0)
        sig = bridge.signal("0xWorker")
        assert sig.response_latency_score > 0.9

    def test_two_hour_response_moderate(self):
        bridge = CommBridge()
        seed_bridge(bridge, response_time_seconds=7200.0)  # 2h
        sig = bridge.signal("0xWorker")
        # exp(-2/2) ≈ 0.37
        assert 0.30 < sig.response_latency_score < 0.45

    def test_eight_hour_response_low(self):
        bridge = CommBridge()
        seed_bridge(bridge, response_time_seconds=28800.0)  # 8h
        sig = bridge.signal("0xWorker")
        assert sig.response_latency_score < 0.2

    def test_latency_clamped(self):
        bridge = CommBridge()
        seed_bridge(bridge, response_time_seconds=0.0001)
        sig = bridge.signal("0xWorker")
        assert 0.0 <= sig.response_latency_score <= 1.0


class TestMessageClarity:
    def test_long_messages_high_clarity(self):
        bridge = CommBridge()
        seed_bridge(bridge, avg_message_length=150.0)
        sig = bridge.signal("0xWorker")
        assert sig.clarity_score > 0.5

    def test_short_messages_lower_clarity(self):
        bridge = CommBridge()
        seed_bridge(bridge, avg_message_length=5.0)
        sig = bridge.signal("0xWorker")
        assert sig.clarity_score < 0.5

    def test_resolution_keyword_boosts_clarity(self):
        bridge = CommBridge()
        seed_bridge(bridge, avg_message_length=80.0, has_resolution_keyword=True)
        sig = bridge.signal("0xWorker")
        assert sig.clarity_score > 0.6

    def test_escalation_keyword_boosts_clarity(self):
        bridge = CommBridge()
        seed_bridge(bridge, avg_message_length=80.0, has_escalation_keyword=True)
        sig = bridge.signal("0xWorker")
        assert sig.clarity_score >= 0.3


class TestEngagementScore:
    def test_optimal_messages_high_score(self):
        bridge = CommBridge()
        seed_bridge(bridge, message_count=OPTIMAL_MESSAGE_COUNT)
        sig = bridge.signal("0xWorker")
        assert sig.engagement_score >= 0.95

    def test_too_few_messages_low_score(self):
        bridge = CommBridge()
        seed_bridge(bridge, message_count=1)
        sig = bridge.signal("0xWorker")
        assert sig.engagement_score < 0.5

    def test_too_many_messages_penalty(self):
        bridge = CommBridge()
        seed_bridge(bridge, message_count=15)
        sig = bridge.signal("0xWorker")
        assert sig.engagement_score < 0.3

    def test_engagement_clamped(self):
        bridge = CommBridge()
        seed_bridge(bridge, message_count=100)
        sig = bridge.signal("0xWorker")
        assert 0.0 <= sig.engagement_score <= 1.0


class TestCommunicationOutcome:
    def test_all_approved_high_outcome(self):
        bridge = CommBridge()
        seed_bridge(bridge, status="approved")
        sig = bridge.signal("0xWorker")
        assert sig.outcome_score >= 0.9

    def test_all_rejected_low_outcome(self):
        bridge = CommBridge()
        seed_bridge(bridge, status="rejected")
        sig = bridge.signal("0xWorker")
        assert sig.outcome_score <= 0.1

    def test_mixed_outcomes_near_half(self):
        bridge = CommBridge()
        rows = (
            [make_row(task_id=f"a{i}", status="approved") for i in range(10)] +
            [make_row(task_id=f"r{i}", status="rejected") for i in range(10)]
        )
        bridge.ingest_raw(rows)
        sig = bridge.signal("0xWorker")
        assert 0.45 < sig.outcome_score < 0.55


# ─── Confidence Scaling ───────────────────────────────────────────────────────

class TestConfidenceScaling:
    def test_confidence_grows_with_data(self):
        bridge = CommBridge()
        prev = 0.0
        for i in range(1, MIN_COMM_OBSERVATIONS + 2):
            bridge.ingest_raw([make_row(task_id=f"t{i}")])
            sig = bridge.signal("0xWorker")
            assert sig.confidence >= prev
            prev = sig.confidence

    def test_full_confidence_at_threshold(self):
        bridge = CommBridge()
        seed_bridge(bridge, count=MIN_COMM_OBSERVATIONS)
        sig = bridge.signal("0xWorker")
        assert sig.confidence >= 0.99

    def test_sparse_data_reduces_bonus(self):
        bridge_sparse = CommBridge()
        bridge_mature = CommBridge()

        params = dict(response_time_seconds=120.0, message_count=3,
                      avg_message_length=80.0, status="approved")

        seed_bridge(bridge_sparse, count=2, **params)
        seed_bridge(bridge_mature, count=20, **params)

        sig_sparse = bridge_sparse.signal("0xWorker")
        sig_mature = bridge_mature.signal("0xWorker")

        assert abs(sig_sparse.comm_bonus) < abs(sig_mature.comm_bonus)


# ─── Bonus Bounds ─────────────────────────────────────────────────────────────

class TestBonusBounds:
    def test_best_worker_capped(self):
        bridge = CommBridge()
        rows = [
            make_row(task_id=f"t{i}", response_time_seconds=30.0, message_count=3,
                     avg_message_length=200.0, has_question=True,
                     has_resolution_keyword=True, has_escalation_keyword=True, status="approved")
            for i in range(30)
        ]
        bridge.ingest_raw(rows)
        sig = bridge.signal("0xWorker")
        assert sig.comm_bonus <= MAX_COMM_BONUS

    def test_worst_worker_floored(self):
        bridge = CommBridge()
        rows = [
            make_row(task_id=f"t{i}", response_time_seconds=72000.0, message_count=20,
                     avg_message_length=4.0, has_question=False,
                     has_resolution_keyword=False, has_escalation_keyword=False, status="rejected")
            for i in range(30)
        ]
        bridge.ingest_raw(rows)
        sig = bridge.signal("0xWorker")
        assert sig.comm_bonus >= MIN_COMM_PENALTY

    def test_bonus_always_in_range(self):
        import random
        bridge = CommBridge()
        rng = random.Random(42)
        rows = []
        for i in range(200):
            rows.append({
                "worker_wallet": f"0xW{i % 10}",
                "task_id": f"t{i}",
                "status": rng.choice(["approved", "rejected", "cancelled"]),
                "response_time_seconds": rng.uniform(0, 86400),
                "message_count": rng.randint(0, 20),
                "avg_message_length": rng.uniform(0, 300),
                "has_question": rng.random() > 0.7,
                "has_resolution_keyword": rng.random() > 0.5,
                "has_escalation_keyword": rng.random() > 0.8,
            })
        bridge.ingest_raw(rows)
        for i in range(10):
            sig = bridge.signal(f"0xW{i}")
            assert MIN_COMM_PENALTY <= sig.comm_bonus <= MAX_COMM_BONUS


# ─── Leaderboard ─────────────────────────────────────────────────────────────

class TestLeaderboard:
    def test_leaderboard_ordered(self):
        bridge = CommBridge()
        for i in range(20):
            bridge.ingest_raw([make_row(worker_wallet="0xGood", task_id=f"g{i}",
                                        message_count=3, response_time_seconds=120.0, status="approved")])
        for i in range(20):
            bridge.ingest_raw([make_row(worker_wallet="0xBad", task_id=f"b{i}",
                                        message_count=15, response_time_seconds=28800.0, status="rejected")])
        board = bridge.comm_leaderboard(top_n=5)
        assert board[0]["worker_id"] == "0xGood"
        assert board[0]["comm_bonus"] > board[-1]["comm_bonus"]

    def test_leaderboard_top_n(self):
        bridge = CommBridge()
        for j in range(10):
            for i in range(10):
                bridge.ingest_raw([make_row(worker_wallet=f"0xW{j}", task_id=f"t{j}{i}")])
        board = bridge.comm_leaderboard(top_n=3)
        assert len(board) == 3

    def test_leaderboard_empty(self):
        bridge = CommBridge()
        assert bridge.comm_leaderboard() == []


# ─── Silent Workers ───────────────────────────────────────────────────────────

class TestSilentWorkers:
    def test_silent_worker_appears(self):
        bridge = CommBridge()
        rows = [make_row(worker_wallet="0xSilent", task_id=f"t{i}", message_count=0)
                for i in range(5)]
        bridge.ingest_raw(rows)
        silent = bridge.silent_workers()
        assert len(silent) == 1
        assert silent[0]["worker_id"] == "0xSilent"

    def test_communicating_worker_not_silent(self):
        bridge = CommBridge()
        seed_bridge(bridge)
        assert all(w["worker_id"] != "0xWorker" for w in bridge.silent_workers())

    def test_empty_engine(self):
        bridge = CommBridge()
        assert bridge.silent_workers() == []


# ─── Fleet Summary ────────────────────────────────────────────────────────────

class TestFleetSummary:
    def test_summary_keys(self):
        bridge = CommBridge()
        seed_bridge(bridge, count=20)
        summary = bridge.comm_summary()
        for key in ["worker_count", "communicating_workers", "silent_workers",
                    "avg_response_hours", "positive_signal_workers", "module_id", "signal_id"]:
            assert key in summary

    def test_summary_worker_count(self):
        bridge = CommBridge()
        for w in ["0xA", "0xB", "0xC"]:
            for i in range(5):
                bridge.ingest_raw([make_row(worker_wallet=w, task_id=f"t{w}{i}")])
        summary = bridge.comm_summary()
        assert summary["worker_count"] == 3

    def test_module_signal_ids(self):
        bridge = CommBridge()
        summary = bridge.comm_summary()
        assert summary["module_id"] == 70
        assert summary["signal_id"] == 23


# ─── Worker Profile ───────────────────────────────────────────────────────────

class TestWorkerProfile:
    def test_profile_known_worker(self):
        bridge = CommBridge()
        seed_bridge(bridge, count=15)
        profile = bridge.worker_profile("0xWorker")
        assert "signal" in profile
        assert "profile" in profile
        assert profile["profile"]["task_count"] == 15

    def test_profile_unknown_worker(self):
        bridge = CommBridge()
        profile = bridge.worker_profile("0xGhost")
        assert "error" in profile

    def test_profile_rates(self):
        bridge = CommBridge()
        rows = [make_row(task_id=f"t{i}", has_resolution_keyword=True) for i in range(10)]
        bridge.ingest_raw(rows)
        profile = bridge.worker_profile("0xWorker")
        assert profile["profile"]["resolution_keyword_rate"] == 1.0


# ─── Persistence ─────────────────────────────────────────────────────────────

class TestPersistence:
    def test_save_load_roundtrip(self):
        bridge = CommBridge()
        seed_bridge(bridge, count=20, response_time_seconds=300.0,
                    message_count=3, avg_message_length=80.0, status="approved")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        try:
            bridge.save(path)
            bridge2 = CommBridge()
            bridge2.load(path)

            # Verify loaded data matches original
            assert len(bridge2._profiles) == len(bridge._profiles)
            assert bridge2._total_records == bridge._total_records

            sig1 = bridge.signal("0xWorker")
            sig2 = bridge2.signal("0xWorker")
            assert abs(sig1.comm_bonus - sig2.comm_bonus) < 0.001
        finally:
            os.unlink(path)

    def test_save_creates_valid_json(self):
        bridge = CommBridge()
        seed_bridge(bridge)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name

        try:
            bridge.save(path)
            with open(path) as f:
                data = json.load(f)
            assert "version" in data
            assert "profiles" in data
            assert "module_id" in data
            assert data["module_id"] == 70
        finally:
            os.unlink(path)


# ─── Health ───────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_empty(self):
        bridge = CommBridge()
        h = bridge.health()
        assert h["status"] == "empty"
        assert h["worker_count"] == 0
        assert h["module_id"] == 70

    def test_health_with_data(self):
        bridge = CommBridge()
        seed_bridge(bridge)
        h = bridge.health()
        assert h["status"] == "healthy"
        assert h["worker_count"] == 1

    def test_health_includes_sync_info(self):
        bridge = CommBridge()
        seed_bridge(bridge)
        h = bridge.health()
        assert "last_sync_at" in h
        assert h["sync_count"] >= 1


# ─── Signal to_dict ───────────────────────────────────────────────────────────

class TestSignalDict:
    def test_to_dict_keys(self):
        bridge = CommBridge()
        seed_bridge(bridge, count=20)
        sig = bridge.signal("0xWorker")
        d = sig.to_dict()
        for key in ["worker_id", "comm_bonus", "response_latency_score", "clarity_score",
                    "engagement_score", "outcome_score", "raw_comm_score",
                    "confidence", "sample_size", "reason"]:
            assert key in d

    def test_to_dict_rounding(self):
        bridge = CommBridge()
        seed_bridge(bridge, count=20)
        d = bridge.signal("0xWorker").to_dict()
        assert isinstance(d["comm_bonus"], float)
        assert isinstance(d["sample_size"], int)


# ─── Integration ─────────────────────────────────────────────────────────────

class TestIntegration:
    def test_multi_worker_differentiation(self):
        bridge = CommBridge()

        # Good: fast, clear, approved
        rows_good = [
            make_row(worker_wallet="0xGood", task_id=f"g{i}",
                     response_time_seconds=120.0, message_count=3,
                     avg_message_length=100.0, has_resolution_keyword=True,
                     status="approved")
            for i in range(20)
        ]
        # Bad: slow, short, rejected
        rows_bad = [
            make_row(worker_wallet="0xBad", task_id=f"b{i}",
                     response_time_seconds=21600.0, message_count=15,
                     avg_message_length=6.0, status="rejected")
            for i in range(20)
        ]
        bridge.ingest_raw(rows_good + rows_bad)

        sig_good = bridge.signal("0xGood")
        sig_bad = bridge.signal("0xBad")

        assert sig_good.comm_bonus > 0.0
        assert sig_bad.comm_bonus < 0.0
        assert sig_good.comm_bonus > sig_bad.comm_bonus

    def test_reason_string_present(self):
        bridge = CommBridge()
        seed_bridge(bridge, count=20, response_time_seconds=60.0, status="approved")
        sig = bridge.signal("0xWorker")
        assert "Signal #23" in sig.reason
        assert len(sig.reason) > 20
