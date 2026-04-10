"""Tests for TrajectoryBridge — Module #77, Signal #30: Worker Growth Intelligence."""

import json
import math
import os
import sys
import tempfile
import time
import importlib
from typing import Optional

import pytest

# Ensure trajectory_bridge is importable WITHOUT pulling in the full swarm package
# (reputation_bridge uses `list[str] | None` syntax that fails on Python <3.10)
_bridge_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _bridge_dir)

_mod = importlib.import_module("trajectory_bridge")
TrajectoryBridge = _mod.TrajectoryBridge
TrajectoryBridgeConfig = _mod.TrajectoryBridgeConfig
PerformanceObservation = _mod.PerformanceObservation
TrajectoryResult = _mod.TrajectoryResult
TrajectorySignal = _mod.TrajectorySignal


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bridge():
    return TrajectoryBridge()


@pytest.fixture
def configured_bridge():
    cfg = TrajectoryBridgeConfig(
        min_observations_short=3,
        min_observations_medium=5,
        improving_threshold=0.02,
        declining_threshold=-0.02,
    )
    return TrajectoryBridge(config=cfg)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------

class TestInit:
    def test_default_init(self, bridge):
        h = bridge.health()
        assert h["status"] == "healthy"
        assert h["module"] == "trajectory_bridge"
        assert h["module_number"] == 77
        assert h["signal_number"] == 30
        assert h["total_workers"] == 0

    def test_custom_config(self):
        cfg = TrajectoryBridgeConfig(improving_threshold=0.05)
        b = TrajectoryBridge(config=cfg)
        assert b.config.improving_threshold == 0.05


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

class TestRecording:
    def test_record_single(self, bridge):
        bridge.record_performance("w1", "photo", 0.8)
        h = bridge.health()
        assert h["total_workers"] == 1
        assert h["total_observations"] == 1

    def test_record_multiple_categories(self, bridge):
        bridge.record_performance("w1", "photo", 0.8)
        bridge.record_performance("w1", "audio", 0.6)
        h = bridge.health()
        assert h["categories_tracked"] == 2

    def test_record_multiple_workers(self, bridge):
        bridge.record_performance("w1", "photo", 0.8)
        bridge.record_performance("w2", "photo", 0.7)
        assert bridge.health()["total_workers"] == 2

    def test_score_clamping(self, bridge):
        bridge.record_performance("w1", "photo", 1.5)
        assert bridge._observations["w1"]["photo"][0].score == 1.0
        bridge.record_performance("w1", "photo", -0.3)
        assert bridge._observations["w1"]["photo"][1].score == 0.0

    def test_cap_observations(self):
        cfg = TrajectoryBridgeConfig(max_observations_per_worker=5)
        b = TrajectoryBridge(config=cfg)
        for i in range(10):
            b.record_performance("w1", "photo", 0.5, timestamp=time.time() + i)
        assert len(b._observations["w1"]["photo"]) == 5

    def test_cache_invalidation(self, bridge):
        now = time.time()
        for i in range(5):
            bridge.record_performance("w1", "photo", 0.5, timestamp=now - (4 - i) * 86400)
        bridge.analyze_trajectory("w1", "photo", now)
        assert "photo" in bridge._cache.get("w1", {})
        bridge.record_performance("w1", "photo", 0.9, timestamp=now)
        assert "photo" not in bridge._cache.get("w1", {})


# ---------------------------------------------------------------------------
# Trajectory Analysis
# ---------------------------------------------------------------------------

class TestTrajectoryAnalysis:
    def test_unknown_worker(self, bridge):
        result = bridge.analyze_trajectory("nobody", "photo")
        assert result.trajectory == "unknown"
        assert result.confidence == 0.0

    def test_improving_trajectory(self, bridge):
        now = time.time()
        for i in range(15):
            bridge.record_performance(
                "w1", "photo", 0.5 + i * 0.025,
                timestamp=now - (14 - i) * 86400,
            )
        result = bridge.analyze_trajectory("w1", "photo", now)
        assert result.trajectory == "improving"
        assert result.growth_rate > 0

    def test_declining_trajectory(self, bridge):
        now = time.time()
        for i in range(15):
            bridge.record_performance(
                "w1", "photo", 0.9 - i * 0.025,
                timestamp=now - (14 - i) * 86400,
            )
        result = bridge.analyze_trajectory("w1", "photo", now)
        assert result.trajectory == "declining"
        assert result.growth_rate < 0

    def test_stable_trajectory(self, bridge):
        now = time.time()
        for i in range(15):
            bridge.record_performance(
                "w1", "photo", 0.75 + (0.005 if i % 2 == 0 else -0.005),
                timestamp=now - (14 - i) * 86400,
            )
        result = bridge.analyze_trajectory("w1", "photo", now)
        assert result.trajectory in ("stable", "plateau")

    def test_predictions_bounded(self, bridge):
        now = time.time()
        for i in range(10):
            bridge.record_performance(
                "w1", "photo", min(1.0, 0.1 + i * 0.1),
                timestamp=now - (9 - i) * 86400,
            )
        result = bridge.analyze_trajectory("w1", "photo", now)
        assert 0.0 <= result.predicted_score_7d <= 1.0
        assert 0.0 <= result.predicted_score_30d <= 1.0

    def test_cross_category_fallback(self, bridge):
        now = time.time()
        for i in range(10):
            bridge.record_performance(
                "w1", "general", 0.6,
                timestamp=now - (9 - i) * 86400,
            )
        result = bridge.analyze_trajectory("w1", "photo", now)
        assert result.observation_count > 0

    def test_cache_hit(self, bridge):
        now = time.time()
        for i in range(5):
            bridge.record_performance("w1", "photo", 0.7, timestamp=now - (4 - i) * 86400)
        r1 = bridge.analyze_trajectory("w1", "photo", now)
        r2 = bridge.analyze_trajectory("w1", "photo", now)
        assert r1.growth_rate == r2.growth_rate


# ---------------------------------------------------------------------------
# ZPD
# ---------------------------------------------------------------------------

class TestZPD:
    def test_zpd_range_valid(self, bridge):
        now = time.time()
        for i in range(10):
            bridge.record_performance("w1", "photo", 0.6, timestamp=now - (9 - i) * 86400)
        result = bridge.analyze_trajectory("w1", "photo", now)
        lower, upper = result.zpd_range
        assert 0.0 <= lower <= upper <= 1.0

    def test_zpd_wider_for_growers(self, bridge):
        now = time.time()
        for i in range(15):
            bridge.record_performance("imp", "photo", 0.5 + i * 0.025, timestamp=now - (14 - i) * 86400)
        for i in range(15):
            bridge.record_performance("stb", "photo", 0.75, timestamp=now - (14 - i) * 86400)

        imp = bridge.analyze_trajectory("imp", "photo", now)
        stb = bridge.analyze_trajectory("stb", "photo", now)
        imp_w = imp.zpd_range[1] - imp.zpd_range[0]
        stb_w = stb.zpd_range[1] - stb.zpd_range[0]
        assert imp_w >= stb_w * 0.8


# ---------------------------------------------------------------------------
# Routing Signal
# ---------------------------------------------------------------------------

class TestRoutingSignal:
    def test_unknown_worker_signal(self, bridge):
        sig = bridge.signal("nobody", "photo", 0.5)
        assert sig.trajectory_bonus == 0.0
        assert sig.trajectory == "unknown"

    def test_improving_worker_bonus(self, bridge):
        now = time.time()
        for i in range(15):
            bridge.record_performance(
                "w1", "photo", 0.5 + i * 0.025,
                timestamp=now - (14 - i) * 86400,
            )
        sig = bridge.signal("w1", "photo", 0.85, now=now)
        assert sig.trajectory == "improving"
        assert sig.trajectory_bonus > 0.0

    def test_declining_worker_penalty(self, bridge):
        now = time.time()
        for i in range(15):
            bridge.record_performance(
                "w1", "photo", 0.9 - i * 0.03,
                timestamp=now - (14 - i) * 86400,
            )
        sig = bridge.signal("w1", "photo", 0.5, now=now)
        if sig.trajectory == "declining":
            assert sig.trajectory_bonus < 0.0

    def test_stable_neutral(self, bridge):
        now = time.time()
        for i in range(15):
            bridge.record_performance("w1", "photo", 0.75, timestamp=now - (14 - i) * 86400)
        sig = bridge.signal("w1", "photo", 0.75, now=now)
        assert abs(sig.trajectory_bonus) < 0.05

    def test_signal_to_dict(self, bridge):
        sig = bridge.signal("w1", "photo", 0.5)
        d = sig.to_dict()
        assert "trajectory_bonus" in d
        assert "zpd_range" in d
        assert isinstance(d["zpd_range"], list)

    def test_stretch_fit_bounded(self, bridge):
        now = time.time()
        for i in range(10):
            bridge.record_performance("w1", "photo", 0.6 + i * 0.02, timestamp=now - (9 - i) * 86400)
        sig = bridge.signal("w1", "photo", 0.9, now=now)
        assert 0.0 <= sig.stretch_fit <= 1.0

    def test_recommendation_non_empty(self, bridge):
        now = time.time()
        for i in range(10):
            bridge.record_performance("w1", "photo", 0.5 + i * 0.03, timestamp=now - (9 - i) * 86400)
        sig = bridge.signal("w1", "photo", 0.8, now=now)
        assert len(sig.recommendation) > 0


# ---------------------------------------------------------------------------
# Fleet Analytics
# ---------------------------------------------------------------------------

class TestFleetAnalytics:
    def test_empty_fleet(self, bridge):
        result = bridge.fleet_trajectories()
        assert result["total_workers"] == 0

    def test_fleet_distribution(self, bridge):
        now = time.time()
        for i in range(10):
            bridge.record_performance("w1", "photo", 0.4 + i * 0.04, timestamp=now - (9 - i) * 86400)
        for i in range(10):
            bridge.record_performance("w2", "photo", 0.75, timestamp=now - (9 - i) * 86400)
        for i in range(10):
            bridge.record_performance("w3", "photo", 0.9 - i * 0.04, timestamp=now - (9 - i) * 86400)

        result = bridge.fleet_trajectories("photo", now)
        assert result["total_workers"] == 3
        assert isinstance(result["trajectory_distribution"], dict)

    def test_worker_growth_report(self, bridge):
        now = time.time()
        for i in range(10):
            bridge.record_performance("w1", "photo", 0.5 + i * 0.03, timestamp=now - (9 - i) * 86400)
            bridge.record_performance("w1", "audio", 0.6 + i * 0.02, timestamp=now - (9 - i) * 86400)

        report = bridge.worker_growth_report("w1", now)
        assert report["total_observations"] == 20
        assert "photo" in report["categories"]
        assert "audio" in report["categories"]

    def test_unknown_worker_report(self, bridge):
        report = bridge.worker_growth_report("nobody")
        assert report["overall_trajectory"] == "unknown"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_load_roundtrip(self, bridge):
        now = time.time()
        for i in range(10):
            bridge.record_performance(
                "w1", "photo", 0.5 + i * 0.03,
                timestamp=now - (9 - i) * 86400,
                task_id=f"t{i}", was_stretch=(i > 5),
            )
        bridge.record_performance("w2", "audio", 0.8, timestamp=now)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            loaded = TrajectoryBridge.load(path)
            assert len(loaded._observations) == 2
            assert len(loaded._observations["w1"]["photo"]) == 10
        finally:
            os.unlink(path)

    def test_save_empty(self, bridge):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            bridge.save(path)
            loaded = TrajectoryBridge.load(path)
            assert len(loaded._observations) == 0
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Coordinator Integration
# ---------------------------------------------------------------------------

class TestCoordinatorIntegration:
    def test_coordinator_has_trajectory_bridge(self):
        """SwarmCoordinator exposes trajectory_bridge attribute."""
        try:
            coordinator_mod = importlib.import_module("coordinator")
            rep_mod = importlib.import_module("reputation_bridge")
            lm_mod = importlib.import_module("lifecycle_manager")
            orch_mod = importlib.import_module("orchestrator")
        except (TypeError, ImportError):
            pytest.skip("Coordinator imports fail on Python <3.10 (union type syntax)")

        bridge = rep_mod.ReputationBridge()
        lifecycle = lm_mod.LifecycleManager()
        orchestrator = orch_mod.SwarmOrchestrator(bridge, lifecycle)

        coord = coordinator_mod.SwarmCoordinator(
            bridge=bridge,
            lifecycle=lifecycle,
            orchestrator=orchestrator,
        )
        assert hasattr(coord, "trajectory_bridge")
        assert isinstance(coord.trajectory_bridge, TrajectoryBridge)

    def test_coordinator_custom_trajectory(self):
        """SwarmCoordinator accepts custom TrajectoryBridge."""
        try:
            coordinator_mod = importlib.import_module("coordinator")
            rep_mod = importlib.import_module("reputation_bridge")
            lm_mod = importlib.import_module("lifecycle_manager")
            orch_mod = importlib.import_module("orchestrator")
        except (TypeError, ImportError):
            pytest.skip("Coordinator imports fail on Python <3.10 (union type syntax)")

        custom = TrajectoryBridge(TrajectoryBridgeConfig(improving_threshold=0.10))

        coord = coordinator_mod.SwarmCoordinator(
            bridge=rep_mod.ReputationBridge(),
            lifecycle=lm_mod.LifecycleManager(),
            orchestrator=orch_mod.SwarmOrchestrator(rep_mod.ReputationBridge(), lm_mod.LifecycleManager()),
            trajectory_bridge=custom,
        )
        assert coord.trajectory_bridge.config.improving_threshold == 0.10


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

class TestDataTypes:
    def test_observation_roundtrip(self):
        obs = PerformanceObservation(
            score=0.8, task_difficulty=0.6, category="photo",
            timestamp=1000.0, task_id="t1", was_stretch=True, revision_count=2,
        )
        d = obs.to_dict()
        restored = PerformanceObservation.from_dict(d)
        assert restored.score == obs.score
        assert restored.was_stretch is True

    def test_trajectory_result_to_dict(self):
        r = TrajectoryResult(
            trajectory="improving", growth_rate=0.05, confidence=0.8,
            current_level=0.7, predicted_score_7d=0.75, predicted_score_30d=0.85,
            zpd_range=(0.75, 0.95), investment_score=0.9,
            plateau_duration_weeks=0.0, observation_count=15,
            short_trend=0.06, medium_trend=0.05, long_trend=0.04,
        )
        d = r.to_dict()
        assert d["trajectory"] == "improving"
        assert isinstance(d["zpd_range"], list)


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_all_same_score(self, bridge):
        now = time.time()
        for i in range(20):
            bridge.record_performance("w1", "photo", 0.5, timestamp=now - (19 - i) * 86400)
        result = bridge.analyze_trajectory("w1", "photo", now)
        assert abs(result.growth_rate) < 0.01

    def test_extreme_growth(self, bridge):
        now = time.time()
        for i in range(10):
            bridge.record_performance("w1", "photo", min(1.0, 0.1 + i * 0.1), timestamp=now - (9 - i) * 86400)
        result = bridge.analyze_trajectory("w1", "photo", now)
        assert 0.0 <= result.predicted_score_7d <= 1.0

    def test_very_old_observations(self, bridge):
        now = time.time()
        for i in range(5):
            bridge.record_performance("w1", "photo", 0.8, timestamp=now - 180 * 86400 + i * 86400)
        result = bridge.analyze_trajectory("w1", "photo", now)
        assert result.confidence < 0.5

    def test_two_observations(self, bridge):
        now = time.time()
        bridge.record_performance("w1", "photo", 0.5, timestamp=now - 86400)
        bridge.record_performance("w1", "photo", 0.8, timestamp=now)
        result = bridge.analyze_trajectory("w1", "photo", now)
        assert result.observation_count == 2

    def test_health_after_usage(self, bridge):
        now = time.time()
        bridge.record_performance("w1", "photo", 0.5, timestamp=now)
        bridge.record_performance("w1", "audio", 0.6, timestamp=now)
        bridge.record_performance("w2", "photo", 0.7, timestamp=now)
        bridge.analyze_trajectory("w1", "photo", now)

        h = bridge.health()
        assert h["total_workers"] == 2
        assert h["total_observations"] == 3
        assert h["categories_tracked"] == 2
        assert h["cache_entries"] >= 1


# ---------------------------------------------------------------------------
# Integration Scenarios
# ---------------------------------------------------------------------------

class TestIntegrationScenarios:
    def test_new_worker_ramp_up(self, bridge):
        now = time.time()
        for w in range(4):
            for d in range(7):
                bridge.record_performance(
                    "newbie", "photo", 0.35 + (w * 7 + d) * 0.02,
                    task_difficulty=0.4 + w * 0.1,
                    timestamp=now - (27 - w * 7 - d) * 86400,
                )

        result = bridge.analyze_trajectory("newbie", "photo", now)
        assert result.trajectory == "improving"
        assert result.investment_score > 0.3

    def test_veteran_burnout(self, bridge):
        now = time.time()
        for d in range(60):
            bridge.record_performance("vet", "photo", 0.90, timestamp=now - (89 - d) * 86400)
        for d in range(30):
            bridge.record_performance("vet", "photo", 0.85 - d * 0.008, timestamp=now - (29 - d) * 86400)

        result = bridge.analyze_trajectory("vet", "photo", now)
        assert result.trajectory in ("declining", "stable")
