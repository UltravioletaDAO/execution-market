"""
Tests for LifecycleBridge — Checkpoint-based routing intelligence.

73 tests across 12 test classes:
    1. TestWorkerSignal — Worker signal data class
    2. TestAgentProfile — Agent profile data class
    3. TestFunnelStep — Funnel step data class
    4. TestIngestion — Direct checkpoint ingestion
    5. TestWorkerSignals — Worker signal generation
    6. TestAgentProfiles — Agent profile generation
    7. TestCompletionFunnel — Funnel analysis
    8. TestSummary — Summary statistics
    9. TestHealth — Health check
    10. TestCaching — Signal caching behavior
    11. TestEdgeCases — Boundary conditions
    12. TestTimestampParsing — Timestamp parsing
"""

import time
from datetime import datetime, timezone, timedelta

import pytest

# Handle Python 3.9 vs 3.11+
try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

import sys
import os
import importlib

# Add parent path for imports — direct import to avoid __init__.py Python 3.9 issues
_swarm_dir = os.path.join(os.path.dirname(__file__), "..", "..", "swarm")
spec = importlib.util.spec_from_file_location(
    "lifecycle_bridge",
    os.path.join(_swarm_dir, "lifecycle_bridge.py"),
)
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)

LifecycleBridge = _mod.LifecycleBridge
LifecycleConfig = _mod.LifecycleConfig
WorkerSignal = _mod.WorkerSignal
AgentProfile = _mod.AgentProfile
FunnelStep = _mod.FunnelStep
LIFECYCLE_STAGES = _mod.LIFECYCLE_STAGES


# ── Fixtures ─────────────────────────────────────────────────────

BASE_TIME = datetime(2026, 3, 31, 0, 0, 0, tzinfo=timezone.utc)


def _ts(hours_offset: float = 0) -> str:
    dt = BASE_TIME + timedelta(hours=hours_offset)
    return dt.isoformat()


def make_complete_checkpoint(
    task_id: str = "task_001",
    agent_id: str = "2106",
    worker_id: str = "w1",
    skill_version: str = "4.3.0",
    hours_spread: float = 4.0,
) -> dict:
    """Create a fully-completed checkpoint."""
    step = hours_spread / 14
    return {
        "task_id": task_id,
        "agent_id_resolved": agent_id,
        "worker_id": worker_id,
        "skill_version": skill_version,
        "auth_erc8128": True,
        "auth_erc8128_at": _ts(0),
        "identity_erc8004": True,
        "identity_erc8004_at": _ts(step),
        "balance_sufficient": True,
        "balance_checked_at": _ts(step * 2),
        "payment_auth_signed": True,
        "payment_auth_at": _ts(step * 3),
        "task_created": True,
        "task_created_at": _ts(step * 4),
        "escrow_locked": True,
        "escrow_locked_at": _ts(step * 5),
        "worker_assigned": True,
        "worker_assigned_at": _ts(step * 6),
        "worker_erc8004": True,
        "evidence_submitted": True,
        "evidence_submitted_at": _ts(step * 7),
        "evidence_count": 2,
        "ai_verified": True,
        "ai_verified_at": _ts(step * 8),
        "approved": True,
        "approved_at": _ts(step * 9),
        "payment_released": True,
        "payment_released_at": _ts(step * 10),
        "agent_rated_worker": True,
        "agent_rated_worker_at": _ts(step * 11),
        "worker_rated_agent": True,
        "worker_rated_agent_at": _ts(step * 12),
        "fees_distributed": True,
        "fees_distributed_at": _ts(step * 13),
        "cancelled": False,
        "expired": False,
    }


def make_partial_checkpoint(
    task_id: str = "task_002",
    agent_id: str = "2106",
    worker_id: str = "w2",
    last_stage: str = "evidence_submitted",
) -> dict:
    """Create a checkpoint that stops at a given stage."""
    cp = {
        "task_id": task_id,
        "agent_id_resolved": agent_id,
        "worker_id": worker_id,
        "skill_version": "4.2.0",
        "cancelled": False,
        "expired": False,
    }
    step = 0.5
    reached = False
    for i, stage in enumerate(LIFECYCLE_STAGES):
        if not reached:
            cp[stage] = True
            cp[f"{stage}_at"] = _ts(i * step)
            if stage == "worker_assigned":
                cp["worker_id"] = worker_id
                cp["worker_erc8004"] = False
            if stage == last_stage:
                reached = True
        else:
            cp[stage] = False
    return cp


def make_cancelled_checkpoint(task_id: str = "task_003", agent_id: str = "2106") -> dict:
    return {
        "task_id": task_id,
        "agent_id_resolved": agent_id,
        "skill_version": "4.1.0",
        "task_created": True,
        "task_created_at": _ts(0),
        "auth_erc8128": True,
        "auth_erc8128_at": _ts(0),
        "identity_erc8004": True,
        "identity_erc8004_at": _ts(0.1),
        "balance_sufficient": True,
        "balance_checked_at": _ts(0.2),
        "payment_auth_signed": True,
        "payment_auth_at": _ts(0.3),
        "escrow_locked": False,
        "worker_assigned": False,
        "evidence_submitted": False,
        "ai_verified": False,
        "approved": False,
        "payment_released": False,
        "agent_rated_worker": False,
        "worker_rated_agent": False,
        "fees_distributed": False,
        "cancelled": True,
        "cancelled_at": _ts(1.0),
        "expired": False,
    }


# ── Test Classes ─────────────────────────────────────────────────


class TestWorkerSignal:
    def test_to_dict(self):
        signal = WorkerSignal(
            worker_id="w1", tasks_assigned=5, evidence_rate=0.8,
            approval_rate=0.7, avg_evidence_minutes=30.0, has_erc8004=True,
            reputation_engagement=0.6, lifecycle_score=75.0,
            risk_factors=[], recommendation="good_match", confidence=0.8,
        )
        d = signal.to_dict()
        assert d["worker_id"] == "w1"
        assert d["lifecycle_score"] == 75.0
        assert d["recommendation"] == "good_match"

    def test_none_evidence_time(self):
        signal = WorkerSignal(
            worker_id="w1", tasks_assigned=1, evidence_rate=0.0,
            approval_rate=0.0, avg_evidence_minutes=None, has_erc8004=False,
            reputation_engagement=0.0, lifecycle_score=50.0,
            risk_factors=["no_lifecycle_history"], recommendation="caution",
            confidence=0.15,
        )
        d = signal.to_dict()
        assert d["avg_evidence_minutes"] is None


class TestAgentProfile:
    def test_to_dict(self):
        profile = AgentProfile(
            agent_id="2106", total_tasks=10, completion_rate=0.8,
            full_lifecycle_rate=0.6, avg_time_to_payment_hours=3.5,
            weakest_stage="reputation", reputation_rate=0.5,
            skill_versions=["4.2.0", "4.3.0"],
        )
        d = profile.to_dict()
        assert d["agent_id"] == "2106"
        assert d["total_tasks"] == 10

    def test_none_payment_time(self):
        profile = AgentProfile(
            agent_id="a1", total_tasks=1, completion_rate=0.0,
            full_lifecycle_rate=0.0, avg_time_to_payment_hours=None,
            weakest_stage=None, reputation_rate=0.0,
            skill_versions=[],
        )
        d = profile.to_dict()
        assert d["avg_time_to_payment_hours"] is None


class TestFunnelStep:
    def test_to_dict(self):
        step = FunnelStep("auth_erc8128", 80, 100, 0.8, 0.8, 0.2)
        d = step.to_dict()
        assert d["stage"] == "auth_erc8128"
        assert d["dropoff"] == 0.2

    def test_full_conversion(self):
        step = FunnelStep("auth_erc8128", 100, 100, 1.0, 1.0, 0.0)
        assert step.dropoff_rate == 0.0


class TestIngestion:
    def test_ingest_single(self):
        bridge = LifecycleBridge()
        count = bridge.ingest([make_complete_checkpoint()])
        assert count == 1

    def test_ingest_multiple(self):
        bridge = LifecycleBridge()
        cps = [make_complete_checkpoint(task_id=f"t{i}") for i in range(10)]
        count = bridge.ingest(cps)
        assert count == 10

    def test_ingest_limit(self):
        config = LifecycleConfig(max_checkpoints=5)
        bridge = LifecycleBridge(config=config)
        cps = [make_complete_checkpoint(task_id=f"t{i}") for i in range(10)]
        bridge.ingest(cps)
        assert len(bridge._checkpoints) == 5

    def test_incremental_ingest(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint(task_id="t1")])
        bridge.ingest([make_complete_checkpoint(task_id="t2")])
        assert len(bridge._checkpoints) == 2

    def test_ingest_clears_cache(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint(worker_id="w1")])
        _ = bridge.worker_signal("w1")
        assert "w1" in bridge._worker_cache
        bridge.ingest([make_complete_checkpoint(task_id="t2", worker_id="w1")])
        assert "w1" not in bridge._worker_cache


class TestWorkerSignals:
    def test_complete_worker(self):
        bridge = LifecycleBridge()
        cps = [make_complete_checkpoint(task_id=f"t{i}", worker_id="w1") for i in range(10)]
        bridge.ingest(cps)

        signal = bridge.worker_signal("w1")
        assert signal.tasks_assigned == 10
        assert signal.evidence_rate == 1.0
        assert signal.approval_rate == 1.0
        assert signal.has_erc8004 is True
        assert signal.recommendation in ("strong_match", "good_match")

    def test_unknown_worker(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint()])
        signal = bridge.worker_signal("unknown")
        assert signal.tasks_assigned == 0
        assert signal.confidence == 0.0
        assert "no_lifecycle_history" in signal.risk_factors
        assert signal.recommendation == "caution"

    def test_low_evidence_worker(self):
        bridge = LifecycleBridge()
        cps = []
        for i in range(10):
            cp = make_complete_checkpoint(task_id=f"t{i}", worker_id="w1")
            if i >= 5:
                cp["evidence_submitted"] = False
                cp["approved"] = False
            cps.append(cp)
        bridge.ingest(cps)

        signal = bridge.worker_signal("w1")
        assert signal.evidence_rate < 0.7
        assert "low_evidence_submission_rate" in signal.risk_factors

    def test_no_erc8004_risk(self):
        bridge = LifecycleBridge()
        cp = make_complete_checkpoint(worker_id="w1")
        cp["worker_erc8004"] = False
        bridge.ingest([cp])

        signal = bridge.worker_signal("w1")
        assert "no_erc8004_identity" in signal.risk_factors

    def test_confidence_scales_with_tasks(self):
        bridge = LifecycleBridge()
        cps = [make_complete_checkpoint(task_id=f"t{i}", worker_id="w1") for i in range(25)]
        bridge.ingest(cps)

        signal = bridge.worker_signal("w1")
        assert signal.confidence >= 0.9

    def test_single_task_low_confidence(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint(worker_id="w1")])
        signal = bridge.worker_signal("w1")
        assert signal.confidence <= 0.15

    def test_strong_match_threshold(self):
        bridge = LifecycleBridge()
        cps = [make_complete_checkpoint(task_id=f"t{i}", worker_id="w1") for i in range(20)]
        bridge.ingest(cps)
        signal = bridge.worker_signal("w1")
        assert signal.recommendation == "strong_match"

    def test_evidence_speed(self):
        bridge = LifecycleBridge()
        cps = [make_complete_checkpoint(task_id=f"t{i}", worker_id="w1", hours_spread=4.0) for i in range(5)]
        bridge.ingest(cps)
        signal = bridge.worker_signal("w1")
        assert signal.avg_evidence_minutes is not None
        assert signal.avg_evidence_minutes > 0

    def test_reputation_engagement(self):
        bridge = LifecycleBridge()
        cp1 = make_complete_checkpoint(task_id="t1", worker_id="w1")
        cp2 = make_complete_checkpoint(task_id="t2", worker_id="w1")
        cp2["worker_rated_agent"] = False
        bridge.ingest([cp1, cp2])
        signal = bridge.worker_signal("w1")
        assert signal.reputation_engagement == 0.5


class TestAgentProfiles:
    def test_complete_agent(self):
        bridge = LifecycleBridge()
        cps = [make_complete_checkpoint(task_id=f"t{i}") for i in range(5)]
        bridge.ingest(cps)

        profile = bridge.agent_profile("2106")
        assert profile is not None
        assert profile.total_tasks == 5
        assert profile.completion_rate == 1.0
        assert profile.full_lifecycle_rate == 1.0

    def test_mixed_agent(self):
        bridge = LifecycleBridge()
        cps = [
            make_complete_checkpoint(task_id="t1"),
            make_complete_checkpoint(task_id="t2"),
            make_partial_checkpoint(task_id="t3"),
            make_cancelled_checkpoint(task_id="t4"),
        ]
        bridge.ingest(cps)

        profile = bridge.agent_profile("2106")
        assert profile.total_tasks == 4
        assert profile.completion_rate == 0.5

    def test_unknown_agent(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint()])
        assert bridge.agent_profile("unknown") is None

    def test_skill_versions(self):
        bridge = LifecycleBridge()
        cps = [
            make_complete_checkpoint(task_id="t1", skill_version="4.2.0"),
            make_complete_checkpoint(task_id="t2", skill_version="4.3.0"),
        ]
        bridge.ingest(cps)
        profile = bridge.agent_profile("2106")
        assert "4.2.0" in profile.skill_versions
        assert "4.3.0" in profile.skill_versions

    def test_reputation_rate(self):
        bridge = LifecycleBridge()
        cp1 = make_complete_checkpoint(task_id="t1")
        cp2 = make_complete_checkpoint(task_id="t2")
        cp2["agent_rated_worker"] = False
        cp2["worker_rated_agent"] = False
        bridge.ingest([cp1, cp2])
        profile = bridge.agent_profile("2106")
        assert profile.reputation_rate == 0.5

    def test_weakest_stage(self):
        bridge = LifecycleBridge()
        cps = [make_complete_checkpoint(task_id=f"t{i}") for i in range(2)]
        cps.extend([make_partial_checkpoint(task_id=f"p{i}") for i in range(3)])
        bridge.ingest(cps)
        profile = bridge.agent_profile("2106")
        assert profile.weakest_stage is not None


class TestCompletionFunnel:
    def test_full_funnel(self):
        bridge = LifecycleBridge()
        cps = [make_complete_checkpoint(task_id=f"t{i}") for i in range(5)]
        bridge.ingest(cps)

        funnel = bridge.completion_funnel()
        assert len(funnel) == 14
        for step in funnel:
            assert step.reached_count == 5

    def test_partial_funnel(self):
        bridge = LifecycleBridge()
        cps = [
            make_complete_checkpoint(task_id="t1"),
            make_partial_checkpoint(task_id="t2"),
            make_cancelled_checkpoint(task_id="t3"),
        ]
        bridge.ingest(cps)

        funnel = bridge.completion_funnel()
        assert funnel[0].reached_count == 3  # auth

    def test_empty_funnel(self):
        bridge = LifecycleBridge()
        assert bridge.completion_funnel() == []

    def test_filtered_by_agent(self):
        bridge = LifecycleBridge()
        cps = [
            make_complete_checkpoint(task_id="t1", agent_id="a1"),
            make_complete_checkpoint(task_id="t2", agent_id="a2"),
        ]
        bridge.ingest(cps)

        funnel = bridge.completion_funnel(agent_id="a1")
        assert funnel[0].total_tasks == 1

    def test_filtered_by_version(self):
        bridge = LifecycleBridge()
        cps = [
            make_complete_checkpoint(task_id="t1", skill_version="4.2.0"),
            make_complete_checkpoint(task_id="t2", skill_version="4.3.0"),
        ]
        bridge.ingest(cps)

        funnel = bridge.completion_funnel(skill_version="4.3.0")
        assert funnel[0].total_tasks == 1

    def test_funnel_to_dict(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint()])
        funnel = bridge.completion_funnel()
        d = funnel[0].to_dict()
        assert "stage" in d
        assert "conversion" in d


class TestSummary:
    def test_basic_summary(self):
        bridge = LifecycleBridge()
        bridge.ingest([
            make_complete_checkpoint(task_id="t1"),
            make_cancelled_checkpoint(task_id="t2"),
        ])
        s = bridge.summary()
        assert s["total_checkpoints"] == 2
        assert s["completed"] == 1
        assert s["cancelled"] == 1
        assert s["initialized"] is True

    def test_empty_summary(self):
        bridge = LifecycleBridge()
        s = bridge.summary()
        assert s["total_checkpoints"] == 0
        assert s["initialized"] is False

    def test_unique_counts(self):
        bridge = LifecycleBridge()
        cps = [
            make_complete_checkpoint(task_id="t1", agent_id="a1", worker_id="w1"),
            make_complete_checkpoint(task_id="t2", agent_id="a1", worker_id="w2"),
            make_complete_checkpoint(task_id="t3", agent_id="a2", worker_id="w1"),
        ]
        bridge.ingest(cps)
        s = bridge.summary()
        assert s["unique_agents"] == 2
        assert s["unique_workers"] == 2


class TestHealth:
    def test_not_initialized(self):
        bridge = LifecycleBridge()
        h = bridge.health()
        assert h["status"] == "not_initialized"

    def test_healthy(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint()])
        bridge._last_sync = time.time()
        h = bridge.health()
        assert h["status"] == "healthy"

    def test_empty_after_sync(self):
        bridge = LifecycleBridge()
        bridge._initialized = True
        bridge._last_sync = time.time()
        h = bridge.health()
        assert h["status"] == "empty"

    def test_stale(self):
        config = LifecycleConfig(sync_interval_seconds=10)
        bridge = LifecycleBridge(config=config)
        bridge._initialized = True
        bridge._checkpoints = [make_complete_checkpoint()]
        bridge._last_sync = time.time() - 100  # Way past 3x interval
        h = bridge.health()
        assert h["status"] == "stale"


class TestCaching:
    def test_worker_cache_hit(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint(worker_id="w1")])

        signal1 = bridge.worker_signal("w1")
        signal2 = bridge.worker_signal("w1")
        assert signal1 is signal2  # Same object from cache

    def test_agent_cache_hit(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint()])
        p1 = bridge.agent_profile("2106")
        p2 = bridge.agent_profile("2106")
        assert p1 is p2

    def test_cache_expires(self):
        config = LifecycleConfig(cache_ttl_seconds=0)
        bridge = LifecycleBridge(config=config)
        bridge.ingest([make_complete_checkpoint(worker_id="w1")])

        signal1 = bridge.worker_signal("w1")
        time.sleep(0.01)
        signal2 = bridge.worker_signal("w1")
        # After TTL=0, should rebuild (different objects)
        assert signal1 is not signal2


class TestEdgeCases:
    def test_single_task(self):
        bridge = LifecycleBridge()
        bridge.ingest([make_complete_checkpoint()])
        s = bridge.summary()
        assert s["total_checkpoints"] == 1

    def test_all_cancelled(self):
        bridge = LifecycleBridge()
        cps = [make_cancelled_checkpoint(task_id=f"c{i}") for i in range(5)]
        bridge.ingest(cps)
        s = bridge.summary()
        assert s["cancelled"] == 5
        assert s["completed"] == 0

    def test_no_timestamps(self):
        bridge = LifecycleBridge()
        cp = {
            "task_id": "t1",
            "agent_id_resolved": "2106",
            "worker_id": "w1",
            "auth_erc8128": True,
            "task_created": True,
            "evidence_submitted": True,
            "approved": True,
            "payment_released": False,
            "cancelled": False,
            "expired": False,
        }
        bridge.ingest([cp])
        signal = bridge.worker_signal("w1")
        assert signal.avg_evidence_minutes is None

    def test_multiple_workers_different_speeds(self):
        bridge = LifecycleBridge()
        fast = [
            make_complete_checkpoint(task_id=f"f{i}", worker_id="fast", hours_spread=2.0)
            for i in range(5)
        ]
        slow = [
            make_complete_checkpoint(task_id=f"s{i}", worker_id="slow", hours_spread=8.0)
            for i in range(5)
        ]
        bridge.ingest(fast + slow)

        fast_signal = bridge.worker_signal("fast")
        slow_signal = bridge.worker_signal("slow")
        assert fast_signal.avg_evidence_minutes < slow_signal.avg_evidence_minutes


class TestTimestampParsing:
    def test_iso_format(self):
        result = LifecycleBridge._parse_ts("2026-03-31T00:00:00+00:00")
        assert result is not None

    def test_z_suffix(self):
        result = LifecycleBridge._parse_ts("2026-03-31T00:00:00Z")
        assert result is not None

    def test_none(self):
        assert LifecycleBridge._parse_ts(None) is None

    def test_invalid(self):
        assert LifecycleBridge._parse_ts("not-a-date") is None

    def test_datetime_input(self):
        dt = datetime(2026, 3, 31, tzinfo=timezone.utc)
        result = LifecycleBridge._parse_ts(dt)
        assert result == dt
