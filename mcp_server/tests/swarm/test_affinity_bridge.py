"""
Tests for AffinityBridge — Server-Side Intrinsic Motivation (Module #67)
=========================================================================

Coverage:
  - AffinityRecord ingestion
  - ingest_raw() from Supabase-style dicts
  - Row-to-record conversion: timestamps, complexity from bounty
  - Neutral signal for unknown worker/category
  - Confidence scaling
  - Acceptance velocity sub-score
  - Completion eagerness sub-score
  - Voluntary escalation sub-score
  - Temporal clustering sub-score
  - Full signal pipeline: high vs low affinity
  - Affinity bonus clamped to max
  - Aggregate signal (no category)
  - routing_signal() output format
  - category_leaderboard() ranking
  - worker_top_categories() ranking
  - summary() stats
  - health() status
  - Persistence: save() / load() round-trip
  - Malformed row skipping (graceful degradation)
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "swarm"))

from affinity_bridge import (
    AffinityBridge,
    AffinityRecord,
    NEUTRAL_PRIOR,
    MAX_AFFINITY_BONUS,
    MIN_OBSERVATIONS,
    MATURE_THRESHOLD,
)

UTC = timezone.utc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record(
    worker="0xABCD",
    task="t1",
    category="delivery",
    assigned_at=1000.0,
    first_action_at=1060.0,
    estimated_seconds=3600.0,
    completed_at=4660.0,
    complexity=1.0,
) -> AffinityRecord:
    return AffinityRecord(
        worker_id=worker,
        task_id=task,
        category=category,
        assigned_at=assigned_at,
        first_action_at=first_action_at,
        estimated_seconds=estimated_seconds,
        completed_at=completed_at,
        complexity_score=complexity,
    )


def _raw_row(
    worker="0xW",
    task_id="t1",
    category="delivery",
    assigned_at_ts=1700000000.0,
    accepted_offset=30.0,
    completed_offset=3600.0,
    estimate=3600.0,
    bounty_usd=10.0,
) -> dict:
    from datetime import datetime, timezone
    def _iso(ts):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return {
        "worker_wallet": worker,
        "task_id": task_id,
        "category": category,
        "assigned_at": _iso(assigned_at_ts),
        "accepted_at": _iso(assigned_at_ts + accepted_offset),
        "completed_at": _iso(assigned_at_ts + completed_offset),
        "time_estimate_seconds": estimate,
        "bounty_usd": bounty_usd,
    }


def _populate_high_affinity(bridge: AffinityBridge, worker="0xHI", n: int = MATURE_THRESHOLD + 2):
    base = 1000.0
    recs = [
        AffinityRecord(
            worker_id=worker,
            task_id=f"hi-t{i}",
            category="delivery",
            assigned_at=base + i * 5000,
            first_action_at=base + i * 5000 + 5.0,     # very fast accept
            estimated_seconds=3600.0,
            completed_at=base + i * 5000 + 5.0 + 1800.0,  # 50% of estimate
            complexity_score=1.0 + i * 0.05,             # always escalating
        )
        for i in range(n)
    ]
    bridge.ingest_records(recs)


def _populate_low_affinity(bridge: AffinityBridge, worker="0xLO", n: int = MATURE_THRESHOLD + 2):
    base = 1000.0
    recs = [
        AffinityRecord(
            worker_id=worker,
            task_id=f"lo-t{i}",
            category="delivery",
            assigned_at=base + i * 5000,
            first_action_at=base + i * 5000 + 7200.0,   # very slow accept
            estimated_seconds=3600.0,
            completed_at=base + i * 5000 + 7200.0 + 9000.0,  # 250% of estimate
            complexity_score=max(0.5, 2.0 - i * 0.05),  # always de-escalating
        )
        for i in range(n)
    ]
    bridge.ingest_records(recs)


# ---------------------------------------------------------------------------
# Basic ingestion
# ---------------------------------------------------------------------------

class TestIngestion:
    def test_ingest_record(self):
        bridge = AffinityBridge()
        bridge.ingest_records([_record()])
        assert "0xABCD" in bridge._state

    def test_ingest_batch_count(self):
        bridge = AffinityBridge()
        recs = [_record(task=f"t{i}") for i in range(10)]
        count = bridge.ingest_records(recs)
        assert count == 10

    def test_ingest_raw_basic(self):
        bridge = AffinityBridge()
        rows = [_raw_row(task_id=f"t{i}") for i in range(5)]
        count = bridge.ingest_raw(rows)
        assert count == 5
        assert "0xW" in bridge._state

    def test_ingest_raw_missing_worker_skipped(self):
        bridge = AffinityBridge()
        rows = [{"task_id": "t1", "category": "delivery"}]  # no worker_wallet
        count = bridge.ingest_raw(rows)
        assert count == 0

    def test_ingest_raw_malformed_ts_graceful(self):
        bridge = AffinityBridge()
        rows = [_raw_row()]
        rows[0]["assigned_at"] = "NOT_A_TIMESTAMP"
        # Should not raise; accept_time will be None
        count = bridge.ingest_raw(rows)
        assert count == 1

    def test_ingest_raw_bounty_to_complexity(self):
        """High bounty → higher complexity score."""
        bridge = AffinityBridge()
        bridge.ingest_raw([_raw_row(bounty_usd=100.0, task_id="t1")])
        bridge.ingest_raw([_raw_row(bounty_usd=1.0, task_id="t2", worker="0xW2")])
        cs_rich = bridge._state["0xW"]["delivery"]
        cs_poor = bridge._state["0xW2"]["delivery"]
        assert cs_rich.complexity_sequence[0] > cs_poor.complexity_sequence[0]

    def test_ingest_raw_zero_bounty(self):
        bridge = AffinityBridge()
        row = _raw_row(bounty_usd=0.0)
        bridge.ingest_raw([row])  # should not raise


# ---------------------------------------------------------------------------
# Neutral signal
# ---------------------------------------------------------------------------

class TestNeutralSignal:
    def test_unknown_worker(self):
        bridge = AffinityBridge()
        sig = bridge.signal("0xNEW", "delivery")
        assert sig.affinity_score == NEUTRAL_PRIOR
        assert sig.affinity_bonus == 0.0
        assert sig.confidence == 0.0

    def test_unknown_category(self):
        bridge = AffinityBridge()
        bridge.ingest_records([_record()])
        sig = bridge.signal("0xABCD", "photography")
        assert sig.affinity_score == NEUTRAL_PRIOR
        assert sig.affinity_bonus == 0.0

    def test_aggregate_unknown_worker(self):
        bridge = AffinityBridge()
        sig = bridge.signal("0xNEW")
        assert sig.affinity_score == NEUTRAL_PRIOR
        assert sig.category == "*"


# ---------------------------------------------------------------------------
# Confidence scaling
# ---------------------------------------------------------------------------

class TestConfidence:
    def test_zero_observations(self):
        bridge = AffinityBridge()
        assert bridge._confidence(0) == 0.0

    def test_mature_observations(self):
        bridge = AffinityBridge()
        assert bridge._confidence(MATURE_THRESHOLD) >= 0.99

    def test_partial_confidence(self):
        bridge = AffinityBridge()
        c = bridge._confidence(MIN_OBSERVATIONS)
        assert 0.0 < c < 1.0


# ---------------------------------------------------------------------------
# Sub-signal computations
# ---------------------------------------------------------------------------

class TestVelocity:
    def test_fast_accept_high_score(self):
        bridge = AffinityBridge()
        # 5 slow events to set high median, then 3 fast events
        base = 1000.0
        for i in range(5):
            bridge.ingest_records([AffinityRecord("0xW", f"slow{i}", "delivery",
                assigned_at=base+i*10000, first_action_at=base+i*10000+3600)])
        for i in range(3):
            bridge.ingest_records([AffinityRecord("0xW", f"fast{i}", "delivery",
                assigned_at=base+100000+i*10000, first_action_at=base+100000+i*10000+10)])
        cs = bridge._state["0xW"]["delivery"]
        score = bridge._compute_velocity(cs)
        assert score > 0.5

    def test_slow_accept_low_score(self):
        bridge = AffinityBridge()
        base = 1000.0
        # Fast events first, then slow
        for i in range(5):
            bridge.ingest_records([AffinityRecord("0xW", f"fast{i}", "delivery",
                assigned_at=base+i*10000, first_action_at=base+i*10000+10)])
        for i in range(3):
            bridge.ingest_records([AffinityRecord("0xW", f"slow{i}", "delivery",
                assigned_at=base+100000+i*10000, first_action_at=base+100000+i*10000+7200)])
        cs = bridge._state["0xW"]["delivery"]
        score = bridge._compute_velocity(cs)
        assert score < 0.5

    def test_single_obs_neutral(self):
        bridge = AffinityBridge()
        bridge.ingest_records([_record()])
        cs = bridge._state["0xABCD"]["delivery"]
        assert bridge._compute_velocity(cs) == 0.5


class TestEagerness:
    def test_fast_complete_high_score(self):
        bridge = AffinityBridge()
        recs = [AffinityRecord("0xW", f"t{i}", "delivery",
            assigned_at=1000.0+i*10000, first_action_at=1060.0+i*10000,
            estimated_seconds=3600.0,
            completed_at=1060.0+i*10000+1800.0)  # 50% of estimate
            for i in range(6)]
        bridge.ingest_records(recs)
        cs = bridge._state["0xW"]["delivery"]
        assert bridge._compute_eagerness(cs) > 0.5

    def test_slow_complete_low_score(self):
        bridge = AffinityBridge()
        recs = [AffinityRecord("0xW", f"t{i}", "delivery",
            assigned_at=1000.0+i*10000, first_action_at=1060.0+i*10000,
            estimated_seconds=3600.0,
            completed_at=1060.0+i*10000+9000.0)  # 250% of estimate
            for i in range(6)]
        bridge.ingest_records(recs)
        cs = bridge._state["0xW"]["delivery"]
        assert bridge._compute_eagerness(cs) < 0.5

    def test_no_estimates_neutral(self):
        bridge = AffinityBridge()
        bridge.ingest_records([AffinityRecord("0xW", "t1", "delivery", complexity_score=1.0)])
        cs = bridge._state["0xW"]["delivery"]
        assert bridge._compute_eagerness(cs) == 0.5


class TestEscalation:
    def test_always_escalating(self):
        bridge = AffinityBridge()
        for i, c in enumerate([0.5, 1.0, 1.5, 2.0, 2.5]):
            bridge.ingest_records([AffinityRecord("0xW", f"t{i}", "delivery", complexity_score=c)])
        cs = bridge._state["0xW"]["delivery"]
        assert bridge._compute_escalation(cs) == 1.0

    def test_never_escalating(self):
        bridge = AffinityBridge()
        for i, c in enumerate([2.5, 2.0, 1.5, 1.0, 0.5]):
            bridge.ingest_records([AffinityRecord("0xW", f"t{i}", "delivery", complexity_score=c)])
        cs = bridge._state["0xW"]["delivery"]
        assert bridge._compute_escalation(cs) == 0.0


class TestTemporal:
    def test_concentrated_hours_high_score(self):
        bridge = AffinityBridge()
        # All completions in 8-12 window
        recs = []
        for i in range(12):
            h = 8 + (i % 4)
            dt = datetime(2024, 3, 10, h, 0, 0, tzinfo=UTC)
            ts = dt.timestamp()
            recs.append(AffinityRecord("0xW", f"t{i}", "delivery",
                completed_at=ts, complexity_score=1.0))
        bridge.ingest_records(recs)
        cs = bridge._state["0xW"]["delivery"]
        assert bridge._compute_temporal(cs) > 0.5

    def test_spread_hours_low_score(self):
        bridge = AffinityBridge()
        recs = []
        for i, h in enumerate([0, 4, 8, 12, 16, 20] * 3):
            dt = datetime(2024, 3, 10, h, 0, 0, tzinfo=UTC)
            ts = dt.timestamp()
            recs.append(AffinityRecord("0xW", f"t{i}", "delivery",
                completed_at=ts, complexity_score=1.0))
        bridge.ingest_records(recs)
        cs = bridge._state["0xW"]["delivery"]
        assert bridge._compute_temporal(cs) < 0.5


# ---------------------------------------------------------------------------
# Full signal pipeline
# ---------------------------------------------------------------------------

class TestSignalPipeline:
    def test_high_affinity_above_neutral(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge)
        sig = bridge.signal("0xHI", "delivery")
        assert sig.affinity_score > NEUTRAL_PRIOR
        assert sig.affinity_bonus > 0
        assert sig.confidence > 0.8

    def test_low_affinity_below_neutral(self):
        bridge = AffinityBridge()
        _populate_low_affinity(bridge)
        sig = bridge.signal("0xLO", "delivery")
        assert sig.affinity_score < NEUTRAL_PRIOR
        assert sig.affinity_bonus < 0

    def test_bonus_clamped_to_max(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge)
        sig = bridge.signal("0xHI", "delivery")
        assert abs(sig.affinity_bonus) <= MAX_AFFINITY_BONUS

    def test_score_in_range(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge)
        _populate_low_affinity(bridge)
        for w in ["0xHI", "0xLO"]:
            sig = bridge.signal(w, "delivery")
            assert 0.0 <= sig.affinity_score <= 1.0

    def test_high_vs_low_ordering(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge)
        _populate_low_affinity(bridge)
        hi = bridge.signal("0xHI", "delivery")
        lo = bridge.signal("0xLO", "delivery")
        assert hi.affinity_score > lo.affinity_score
        assert hi.affinity_bonus > lo.affinity_bonus

    def test_to_dict(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge)
        d = bridge.signal("0xHI", "delivery").to_dict()
        assert "affinity_score" in d
        assert "affinity_bonus" in d
        assert "velocity_score" in d


# ---------------------------------------------------------------------------
# routing_signal()
# ---------------------------------------------------------------------------

class TestRoutingSignal:
    def test_routing_signal_format(self):
        bridge = AffinityBridge()
        result = bridge.routing_signal("0xNEW", "delivery")
        assert "affinity_bonus" in result
        assert "affinity_score" in result
        assert "confidence" in result
        assert result["affinity_bonus"] == 0.0

    def test_routing_signal_high_affinity(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge)
        result = bridge.routing_signal("0xHI", "delivery")
        assert result["affinity_bonus"] > 0


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

class TestAnalytics:
    def test_category_leaderboard_sorted(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge, worker="0xHI")
        _populate_low_affinity(bridge, worker="0xLO")
        lb = bridge.category_leaderboard("delivery", top_n=10)
        assert len(lb) == 2
        assert lb[0]["worker_id"] == "0xHI"
        assert lb[0]["affinity_score"] > lb[1]["affinity_score"]

    def test_category_leaderboard_empty(self):
        bridge = AffinityBridge()
        bridge.ingest_records([_record()])
        lb = bridge.category_leaderboard("photography")
        assert lb == []

    def test_worker_top_categories(self):
        bridge = AffinityBridge()
        # Two categories with different affinity
        for i in range(MATURE_THRESHOLD):
            bridge.ingest_records([AffinityRecord("0xW", f"d{i}", "delivery",
                assigned_at=1000.0+i*5000, first_action_at=1005.0+i*5000,
                estimated_seconds=3600.0, completed_at=1005.0+i*5000+1800.0,
                complexity_score=1.0)])
            bridge.ingest_records([AffinityRecord("0xW", f"v{i}", "verification",
                assigned_at=1000.0+i*5000, first_action_at=1000.0+i*5000+7200.0,
                estimated_seconds=3600.0, completed_at=1000.0+i*5000+7200.0+9000.0,
                complexity_score=1.0)])
        cats = bridge.worker_top_categories("0xW", top_n=3)
        assert len(cats) == 2
        # delivery (fast) should rank higher than verification (slow)
        assert cats[0]["category"] == "delivery"

    def test_worker_top_categories_unknown(self):
        bridge = AffinityBridge()
        assert bridge.worker_top_categories("0xUNK") == []

    def test_summary_keys(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge)
        s = bridge.summary()
        assert "worker_count" in s
        assert "record_count" in s
        assert "categories" in s

    def test_summary_empty(self):
        bridge = AffinityBridge()
        s = bridge.summary()
        assert s["worker_count"] == 0
        assert s["record_count"] == 0

    def test_health_healthy(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge)
        h = bridge.health()
        assert h["status"] == "healthy"

    def test_health_degraded_empty(self):
        bridge = AffinityBridge()
        h = bridge.health()
        assert h["status"] == "degraded"


# ---------------------------------------------------------------------------
# Aggregate signal
# ---------------------------------------------------------------------------

class TestAggregate:
    def test_aggregate_multiple_categories(self):
        bridge = AffinityBridge()
        for cat in ["delivery", "verification", "photography"]:
            for i in range(MATURE_THRESHOLD):
                bridge.ingest_records([AffinityRecord("0xMULTI", f"{cat}-t{i}", cat,
                    assigned_at=1000.0+i*5000, first_action_at=1010.0+i*5000,
                    estimated_seconds=3600.0, completed_at=1010.0+i*5000+1800.0,
                    complexity_score=1.0)])
        sig = bridge.signal("0xMULTI")
        assert sig.category == "*"
        assert sig.observation_count == MATURE_THRESHOLD * 3


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_load_round_trip(self):
        bridge = AffinityBridge()
        _populate_high_affinity(bridge)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "affinity.json"
            bridge.save(str(path))
            bridge2 = AffinityBridge()
            bridge2.load(str(path))
            orig = bridge.signal("0xHI", "delivery")
            loaded = bridge2.signal("0xHI", "delivery")
            assert abs(orig.affinity_score - loaded.affinity_score) < 1e-9

    def test_save_file_structure(self):
        bridge = AffinityBridge()
        bridge.ingest_records([_record()])
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bridge.json"
            bridge.save(str(path))
            data = json.loads(path.read_text())
            assert "version" in data
            assert "workers" in data

    def test_load_empty_state(self):
        bridge = AffinityBridge()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.json"
            bridge.save(str(path))
            bridge2 = AffinityBridge()
            bridge2.load(str(path))
            assert bridge2.summary()["worker_count"] == 0
