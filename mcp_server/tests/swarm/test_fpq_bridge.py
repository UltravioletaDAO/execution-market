"""
Tests for FPQBridge — Module #71: Server-Side First-Pass Quality Intelligence

Signal #24 tests covering:
- Module identity
- Full refresh ingestion
- Signal computation (all 4 sub-signals)
- Edge cases
- Analytics (leaderboard, summary, profile)
- Persistence (save/load)
- Health endpoint
- Coordinator wiring
"""

import json
import math
import os
import tempfile
import pytest
from mcp_server.swarm.fpq_bridge import (
    FPQBridge,
    FPQSignalResult,
    MAX_FPQ_BONUS,
    MIN_FPQ_PENALTY,
    MODULE_ID,
    SIGNAL_ID,
    VERSION,
)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def bridge():
    return FPQBridge()


def make_row(worker_wallet="0xw1", task_id="t1", submission_count=1,
             status="approved", quality_score=None,
             first_submission_approved=None):
    row = {
        "worker_wallet": worker_wallet,
        "task_id": task_id,
        "submission_count": submission_count,
        "status": status,
    }
    if quality_score is not None:
        row["quality_score"] = quality_score
    if first_submission_approved is not None:
        row["first_submission_approved"] = first_submission_approved
    return row


# ─── Module Identity ──────────────────────────────────────────────────────────

class TestModuleIdentity:
    def test_module_id(self):
        assert MODULE_ID == 71

    def test_signal_id(self):
        assert SIGNAL_ID == 24

    def test_version(self):
        assert VERSION == "1.0.0"

    def test_max_bonus(self):
        assert MAX_FPQ_BONUS == 0.06

    def test_min_penalty(self):
        assert MIN_FPQ_PENALTY == -0.06

    def test_health_module_and_signal(self, bridge):
        h = bridge.health()
        assert h["module"] == 71
        assert h["signal"] == 24
        assert h["dimension"] == 10


# ─── Init & Health ────────────────────────────────────────────────────────────

class TestInitAndHealth:
    def test_empty_init(self, bridge):
        assert bridge.health()["workers_tracked"] == 0

    def test_health_status_ok(self, bridge):
        assert bridge.health()["status"] == "ok"

    def test_health_max_bonus(self, bridge):
        assert bridge.health()["max_bonus"] == MAX_FPQ_BONUS

    def test_unknown_worker_zero(self, bridge):
        sig = bridge.signal("unknown")
        assert sig.fpq_bonus == 0.0
        assert sig.reason == "no_history"


# ─── Full Refresh Ingestion ────────────────────────────────────────────────────

class TestFullRefresh:
    def test_full_refresh_basic(self, bridge):
        rows = [make_row("0xw1", "t1", 1, "approved")]
        n = bridge.full_refresh(rows)
        assert n == 1
        assert "0xw1" in bridge._workers

    def test_full_refresh_clears_old_state(self, bridge):
        bridge.full_refresh([make_row("0xold", "t1")])
        bridge.full_refresh([make_row("0xnew", "t2")])
        assert "0xold" not in bridge._workers
        assert "0xnew" in bridge._workers

    def test_full_refresh_multiple_workers(self, bridge):
        rows = [
            make_row("0xw1", "t1"),
            make_row("0xw2", "t2"),
            make_row("0xw1", "t3"),
        ]
        n = bridge.full_refresh(rows)
        assert n == 3
        assert len(bridge._workers) == 2
        assert bridge._workers["0xw1"].total_tasks == 2

    def test_ingest_raw_incremental(self, bridge):
        bridge.full_refresh([make_row("0xw1", "t1")])
        bridge.ingest_raw([make_row("0xw1", "t2")])
        assert bridge._workers["0xw1"].total_tasks == 2

    def test_full_refresh_updates_sync_ts(self, bridge):
        bridge.full_refresh([make_row()])
        assert bridge._last_sync_ts is not None


# ─── Worker ID Field Resolution ───────────────────────────────────────────────

class TestWorkerIdResolution:
    def test_worker_wallet(self, bridge):
        bridge.full_refresh([{"worker_wallet": "0xwallet", "task_id": "t1",
                               "status": "approved"}])
        assert "0xwallet" in bridge._workers

    def test_worker_address(self, bridge):
        bridge.full_refresh([{"worker_address": "0xaddr", "task_id": "t1",
                               "status": "approved"}])
        assert "0xaddr" in bridge._workers

    def test_wallet_field(self, bridge):
        bridge.full_refresh([{"wallet": "0xwf", "task_id": "t1",
                               "status": "approved"}])
        assert "0xwf" in bridge._workers

    def test_worker_id_field(self, bridge):
        bridge.full_refresh([{"worker_id": "wid_123", "task_id": "t1",
                               "status": "approved"}])
        assert "wid_123" in bridge._workers

    def test_missing_worker_id_skipped(self, bridge):
        n = bridge.full_refresh([{"task_id": "t1", "status": "approved"}])
        assert n == 0


# ─── Outcome Normalization ────────────────────────────────────────────────────

class TestOutcomeNormalization:
    def test_completed_is_approved(self, bridge):
        rows = [make_row("w1", "t1", 1, "completed")]
        bridge.full_refresh(rows)
        state = bridge._workers["w1"]
        # "completed" → "approved" → 1-pass
        assert state.first_pass_count == 1

    def test_done_is_approved(self, bridge):
        rows = [make_row("w1", "t1", 1, "done")]
        bridge.full_refresh(rows)
        assert bridge._workers["w1"].first_pass_count == 1

    def test_failed_is_rejected(self, bridge):
        rows = [make_row("w1", "t1", 1, "failed")]
        bridge.full_refresh(rows)
        state = bridge._workers["w1"]
        assert state.first_pass_count == 0
        assert state.rejection_events == 1

    def test_pending_neutral(self, bridge):
        rows = [make_row("w1", "t1", 1, "pending")]
        bridge.full_refresh(rows)
        state = bridge._workers["w1"]
        assert state.total_tasks == 1
        assert state.first_pass_count == 0


# ─── Sub-Signal: First-Pass Rate ─────────────────────────────────────────────

class TestFirstPassRate:
    def test_single_approved_first_pass(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        assert bridge._workers["w1"].first_pass_rate() == 1.0

    def test_multi_submit_not_first_pass(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 3, "approved")])
        assert bridge._workers["w1"].first_pass_count == 0

    def test_explicit_first_submission_approved(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 2, "approved",
                                       first_submission_approved=True)])
        assert bridge._workers["w1"].first_pass_count == 1

    def test_mixed_rate(self, bridge):
        rows = [
            make_row("w1", "t1", 1, "approved"),
            make_row("w1", "t2", 1, "approved"),
            make_row("w1", "t3", 3, "approved"),
        ]
        bridge.full_refresh(rows)
        state = bridge._workers["w1"]
        assert state.first_pass_rate() == pytest.approx(2/3, abs=0.001)


# ─── Sub-Signal: Revision Efficiency ─────────────────────────────────────────

class TestRevisionEfficiency:
    def test_no_revisions_perfect(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        assert bridge._workers["w1"].revision_efficiency() == 1.0

    def test_multi_attempt_efficiency(self, bridge):
        rows = [
            make_row("w1", "t1", 1, "approved"),
            make_row("w1", "t2", 3, "approved"),
        ]
        bridge.full_refresh(rows)
        state = bridge._workers["w1"]
        # avg_attempts = 2.0 → 1/(2-0.9) ≈ 0.91
        assert state.revision_efficiency() == pytest.approx(1/1.1, abs=0.001)


# ─── Sub-Signal: Rejection Recovery ──────────────────────────────────────────

class TestRejectionRecovery:
    def test_no_rejections_perfect(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        assert bridge._workers["w1"].rejection_recovery_rate() == 1.0

    def test_rejection_with_recovery(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 2, "approved")])
        state = bridge._workers["w1"]
        assert state.rejection_events == 1
        assert state.recovery_events == 1

    def test_rejection_no_recovery(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 2, "rejected")])
        state = bridge._workers["w1"]
        assert state.rejection_events == 1
        assert state.recovery_events == 0
        assert state.rejection_recovery_rate() == 0.0


# ─── Sub-Signal: Quality Consistency ──────────────────────────────────────────

class TestQualityConsistency:
    def test_no_scores_neutral(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        assert bridge._workers["w1"].quality_consistency() == 0.5

    def test_consistent_scores(self, bridge):
        rows = [
            make_row("w1", f"t{i}", 1, "approved", quality_score=0.9)
            for i in range(5)
        ]
        bridge.full_refresh(rows)
        assert bridge._workers["w1"].quality_consistency() == 1.0  # zero variance

    def test_high_variance_low_consistency(self, bridge):
        rows = [
            make_row("w1", f"t{i}", 1, "approved",
                     quality_score=[0.1, 0.9, 0.1, 0.9, 0.1][i])
            for i in range(5)
        ]
        bridge.full_refresh(rows)
        consistency = bridge._workers["w1"].quality_consistency()
        assert consistency < 0.5  # High variance → low consistency

    def test_quality_score_normalization_100scale(self, bridge):
        rows = [{"worker_wallet": "w1", "task_id": "t1",
                 "status": "approved", "score": 85.0}]
        bridge.full_refresh(rows)
        state = bridge._workers["w1"]
        assert state.quality_scores[0] == pytest.approx(0.85, abs=0.001)


# ─── Signal Computation ───────────────────────────────────────────────────────

class TestSignalComputation:
    def test_unknown_worker_zero(self, bridge):
        sig = bridge.signal("unknown")
        assert sig.fpq_bonus == 0.0
        assert sig.reason == "no_history"

    def test_bonus_within_bounds(self, bridge):
        rows = [make_row("w1", f"t{i}", 1, "approved") for i in range(20)]
        bridge.full_refresh(rows)
        sig = bridge.signal("w1")
        assert MIN_FPQ_PENALTY <= sig.fpq_bonus <= MAX_FPQ_BONUS

    def test_perfect_worker_positive_bonus(self, bridge):
        rows = [make_row("w1", f"t{i}", 1, "approved", quality_score=0.9)
                for i in range(15)]
        bridge.full_refresh(rows)
        sig = bridge.signal("w1")
        assert sig.fpq_bonus > 0.0

    def test_terrible_worker_negative_bonus(self, bridge):
        rows = [make_row("w1", f"t{i}", 7, "rejected") for i in range(15)]
        bridge.full_refresh(rows)
        sig = bridge.signal("w1")
        assert sig.fpq_bonus < 0.0

    def test_confidence_attenuated_few_tasks(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        sig = bridge.signal("w1")
        assert sig.fpq_bonus < MAX_FPQ_BONUS  # Attenuated

    def test_attenuated_reason_for_few_obs(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        sig = bridge.signal("w1")
        assert "attenuated" in sig.reason

    def test_signal_result_fields(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        sig = bridge.signal("w1")
        assert isinstance(sig, FPQSignalResult)
        assert sig.worker_id == "w1"
        assert hasattr(sig, "first_pass_rate")
        assert hasattr(sig, "revision_efficiency")
        assert hasattr(sig, "rejection_recovery_rate")
        assert hasattr(sig, "quality_consistency")
        assert hasattr(sig, "confidence")
        assert hasattr(sig, "task_count")

    def test_to_dict(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        d = bridge.signal("w1").to_dict()
        assert d["worker_id"] == "w1"
        assert "fpq_bonus" in d
        assert "first_pass_rate" in d

    def test_better_worker_higher_bonus(self, bridge):
        # Perfect first-pass worker
        rows_good = [make_row("good", f"t{i}", 1, "approved") for i in range(10)]
        # High revision worker
        rows_bad = [make_row("bad", f"t{i}", 5, "rejected") for i in range(10)]
        bridge.full_refresh(rows_good + rows_bad)
        sig_good = bridge.signal("good")
        sig_bad = bridge.signal("bad")
        assert sig_good.fpq_bonus > sig_bad.fpq_bonus


# ─── Analytics ────────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_fpq_leaderboard_ordering(self, bridge):
        rows_perfect = [make_row("perfect", f"t{i}", 1, "approved") for i in range(10)]
        rows_bad = [make_row("bad", f"t{i}", 5, "rejected") for i in range(10)]
        bridge.full_refresh(rows_perfect + rows_bad)
        lb = bridge.fpq_leaderboard()
        ids = [e["worker_id"] for e in lb]
        assert ids[0] == "perfect"
        assert ids[-1] == "bad"

    def test_fpq_leaderboard_fields(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        lb = bridge.fpq_leaderboard()
        assert len(lb) >= 1
        e = lb[0]
        assert "rank" in e
        assert "fpq_bonus" in e
        assert "first_pass_rate" in e
        assert "confidence" in e

    def test_fpq_summary_empty(self, bridge):
        s = bridge.fpq_summary()
        assert s["total_workers"] == 0

    def test_fpq_summary_with_data(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        s = bridge.fpq_summary()
        assert s["total_workers"] == 1
        assert "avg_fpq_bonus" in s
        assert "avg_first_pass_rate" in s
        assert s["signal"] == 24
        assert s["module"] == 71

    def test_worker_fpq_profile_known(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])
        p = bridge.worker_fpq_profile("w1")
        assert p["worker_id"] == "w1"
        assert p["task_count"] == 1

    def test_worker_fpq_profile_unknown(self, bridge):
        p = bridge.worker_fpq_profile("x")
        assert p["status"] == "unknown"

    def test_top_n_respected(self, bridge):
        for i in range(10):
            bridge.full_refresh([make_row(f"w{i}", "t1", 1, "approved")])
        lb = bridge.fpq_leaderboard(top_n=3)
        assert len(lb) <= 3


# ─── Persistence ──────────────────────────────────────────────────────────────

class TestPersistence:
    def test_save_and_load(self, bridge):
        rows = [make_row("w1", f"t{i}", 1, "approved", quality_score=0.9)
                for i in range(5)]
        bridge.full_refresh(rows)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name

        try:
            bridge.save(path)

            bridge2 = FPQBridge()
            bridge2.load(path)

            assert "w1" in bridge2._workers
            state = bridge2._workers["w1"]
            assert state.total_tasks == 5
            assert state.first_pass_count == 5
            assert len(state.quality_scores) == 5
        finally:
            os.unlink(path)

    def test_save_json_structure(self, bridge):
        bridge.full_refresh([make_row("w1", "t1", 1, "approved")])

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name

        try:
            bridge.save(path)
            with open(path) as f:
                data = json.load(f)
            assert data["module"] == MODULE_ID
            assert data["signal"] == SIGNAL_ID
            assert "workers" in data
            assert "w1" in data["workers"]
        finally:
            os.unlink(path)

    def test_load_signal_preserved(self, bridge):
        rows = [make_row("w1", f"t{i}", 1, "approved") for i in range(10)]
        bridge.full_refresh(rows)
        sig_before = bridge.signal("w1")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name

        try:
            bridge.save(path)
            bridge2 = FPQBridge()
            bridge2.load(path)
            sig_after = bridge2.signal("w1")
            assert abs(sig_before.fpq_bonus - sig_after.fpq_bonus) < 0.001
        finally:
            os.unlink(path)


# ─── Coordinator Wiring ───────────────────────────────────────────────────────

class TestCoordinatorWiring:
    def test_fpq_bridge_in_coordinator(self):
        from mcp_server.swarm.coordinator import SwarmCoordinator
        coordinator = SwarmCoordinator.create()
        assert hasattr(coordinator, "fpq_bridge")
        assert isinstance(coordinator.fpq_bridge, FPQBridge)

    def test_coordinator_fpq_bridge_initialized(self):
        from mcp_server.swarm.coordinator import SwarmCoordinator
        coordinator = SwarmCoordinator.create()
        h = coordinator.fpq_bridge.health()
        assert h["status"] == "ok"
        assert h["module"] == 71

    def test_coordinator_custom_fpq_bridge(self):
        from mcp_server.swarm.coordinator import SwarmCoordinator
        custom_bridge = FPQBridge()
        coordinator = SwarmCoordinator.create(fpq_bridge=custom_bridge)
        assert coordinator.fpq_bridge is custom_bridge

    def test_coordinator_fpq_bridge_functional(self):
        from mcp_server.swarm.coordinator import SwarmCoordinator
        coordinator = SwarmCoordinator.create()
        rows = [make_row("0xw1", f"t{i}", 1, "approved") for i in range(10)]
        coordinator.fpq_bridge.full_refresh(rows)
        sig = coordinator.fpq_bridge.signal("0xw1")
        assert sig.fpq_bonus > 0.0


# ─── Integration ──────────────────────────────────────────────────────────────

class TestIntegration:
    def test_em_rows_full_scenario(self, bridge):
        """Simulate real EM task_assignments rows."""
        rows = (
            [{"worker_wallet": f"0xworker{i}", "task_id": f"task_{i}",
              "status": "approved", "submission_count": 1, "score": 88.0}
             for i in range(10)]
            + [{"worker_wallet": "0xbad", "task_id": f"task_{i+10}",
                "status": "rejected", "submission_count": 5}
               for i in range(10)]
        )
        bridge.full_refresh(rows)
        assert len(bridge._workers) == 11

        for i in range(10):
            sig = bridge.signal(f"0xworker{i}")
            assert sig.fpq_bonus >= 0.0  # All first-pass workers positive/neutral

        sig_bad = bridge.signal("0xbad")
        assert sig_bad.fpq_bonus < 0.0  # Bad worker penalized

    def test_leaderboard_reflects_quality(self, bridge):
        rows_perfect = [make_row("perfect", f"t{i}", 1, "approved", quality_score=0.95)
                        for i in range(12)]
        rows_average = [make_row("average", f"t{i}", 2, "approved")
                        for i in range(12)]
        bridge.full_refresh(rows_perfect + rows_average)
        lb = bridge.fpq_leaderboard()
        ids = [e["worker_id"] for e in lb]
        assert ids.index("perfect") < ids.index("average")

    def test_incremental_updates(self, bridge):
        """Test incremental ingestion pattern (event-driven updates)."""
        initial = [make_row("w1", f"t{i}", 1, "approved") for i in range(5)]
        bridge.full_refresh(initial)
        assert bridge._workers["w1"].total_tasks == 5

        new_rows = [make_row("w1", "t10", 1, "approved")]
        bridge.ingest_raw(new_rows)
        assert bridge._workers["w1"].total_tasks == 6
