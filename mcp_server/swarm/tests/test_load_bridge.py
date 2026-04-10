"""
Tests for LoadBridge — Module #75: Server-Side Load Balancing

Tests cover:
  1. Lifecycle hooks (assign/complete/expire)
  2. Signal generation
  3. Penalty curve
  4. Capacity estimation
  5. Cooling mechanism
  6. Fleet utilization
  7. Persistence
  8. Coordinator integration patterns
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest

# Ensure load_bridge is importable WITHOUT pulling in the full swarm package
# (reputation_bridge uses `list[str] | None` syntax that fails on Python <3.10)
_bridge_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _bridge_dir)

# Direct import — load_bridge has no cross-module swarm dependencies
import importlib
load_bridge_mod = importlib.import_module("load_bridge")
LoadBridge = load_bridge_mod.LoadBridge
LoadBridgeConfig = load_bridge_mod.LoadBridgeConfig
LoadSignal = load_bridge_mod.LoadSignal
FleetUtilization = load_bridge_mod.FleetUtilization


class TestLifecycleHooks(unittest.TestCase):
    """Test the coordinator-facing lifecycle hooks."""

    def setUp(self):
        self.lb = LoadBridge(LoadBridgeConfig(default_capacity=10.0))

    def test_on_task_assigned(self):
        """Assignment should track active task."""
        sig = self.lb.on_task_assigned("t1", "w1", task_type="photo")
        self.assertEqual(sig.active_tasks, 1)
        self.assertEqual(sig.worker_id, "w1")

    def test_on_task_completed(self):
        """Completion should remove active task."""
        self.lb.on_task_assigned("t1", "w1")
        sig = self.lb.on_task_completed("t1", "w1")
        self.assertEqual(sig.active_tasks, 0)

    def test_on_task_expired(self):
        """Expiration should remove without recording completion."""
        self.lb.on_task_assigned("t1", "w1")
        self.lb.on_task_expired("t1", "w1")
        sig = self.lb.signal("w1")
        self.assertEqual(sig.active_tasks, 0)

    def test_multiple_assignments(self):
        """Multiple tasks should accumulate."""
        for i in range(5):
            self.lb.on_task_assigned(f"t{i}", "w1")
        sig = self.lb.signal("w1")
        self.assertEqual(sig.active_tasks, 5)

    def test_complexity_from_task_type(self):
        """Task type should resolve complexity."""
        self.lb.on_task_assigned("t1", "w1", task_type="notarized")  # 2.5x
        sig = self.lb.signal("w1")
        self.assertAlmostEqual(sig.active_complexity, 2.5)

    def test_explicit_complexity_overrides_type(self):
        """Explicit complexity should be used when provided."""
        self.lb.on_task_assigned("t1", "w1", task_type="photo", complexity=3.0)
        sig = self.lb.signal("w1")
        self.assertAlmostEqual(sig.active_complexity, 3.0)

    def test_returns_signal_after_assign(self):
        """Assignment should return current signal."""
        sig = self.lb.on_task_assigned("t1", "w1")
        self.assertIsInstance(sig, LoadSignal)
        self.assertEqual(sig.active_tasks, 1)

    def test_returns_signal_after_complete(self):
        """Completion should return updated signal."""
        self.lb.on_task_assigned("t1", "w1")
        sig = self.lb.on_task_completed("t1", "w1")
        self.assertIsInstance(sig, LoadSignal)
        self.assertEqual(sig.active_tasks, 0)

    def test_complete_unknown_task(self):
        """Completing untracked task should not error."""
        sig = self.lb.on_task_completed("unknown", "w1")
        self.assertEqual(sig.active_tasks, 0)


class TestSignalGeneration(unittest.TestCase):
    """Test load signal output."""

    def test_idle_signal(self):
        lb = LoadBridge()
        sig = lb.signal("idle_worker")
        self.assertEqual(sig.load_penalty, 0.0)
        self.assertEqual(sig.risk_level, "idle")
        self.assertEqual(sig.utilization, 0.0)

    def test_signal_fields(self):
        lb = LoadBridge(LoadBridgeConfig(default_capacity=10.0))
        lb.on_task_assigned("t1", "w1")
        sig = lb.signal("w1")

        self.assertIsNotNone(sig.worker_id)
        self.assertIsNotNone(sig.load_penalty)
        self.assertIsNotNone(sig.utilization)
        self.assertIsNotNone(sig.active_tasks)
        self.assertIsNotNone(sig.risk_level)
        self.assertIsNotNone(sig.recommendation)

    def test_signal_to_dict(self):
        lb = LoadBridge()
        sig = lb.signal("w1")
        d = sig.to_dict()
        self.assertIn("worker_id", d)
        self.assertIn("load_penalty", d)
        self.assertIn("risk_level", d)


class TestPenaltyCurve(unittest.TestCase):
    """Test the 5-zone penalty curve."""

    def setUp(self):
        self.lb = LoadBridge(LoadBridgeConfig(
            default_capacity=10.0,
            enable_cooling=False,
        ))

    def _assign_n(self, worker: str, n: int, complexity: float = 1.0):
        now = time.time()
        for i in range(n):
            self.lb.on_task_assigned(
                f"t_{worker}_{i}", worker,
                complexity=complexity, assigned_at=now,
            )

    def test_no_penalty_under_50pct(self):
        self._assign_n("w1", 3)  # 30%
        sig = self.lb.signal("w1")
        self.assertEqual(sig.load_penalty, 0.0)

    def test_gentle_penalty_50_to_80pct(self):
        self._assign_n("w1", 7)  # 70%
        sig = self.lb.signal("w1")
        self.assertLess(sig.load_penalty, 0.0)
        self.assertGreater(sig.load_penalty, -0.05)

    def test_steep_penalty_80_to_100pct(self):
        self._assign_n("w1", 9)  # 90%
        sig = self.lb.signal("w1")
        self.assertLess(sig.load_penalty, -0.01)

    def test_overloaded_max_penalty(self):
        self._assign_n("w1", 15)  # 150%
        sig = self.lb.signal("w1")
        self.assertLessEqual(sig.load_penalty, -0.04)

    def test_penalty_monotonically_worsens(self):
        penalties = []
        for n in range(0, 15):
            lb = LoadBridge(LoadBridgeConfig(
                default_capacity=10.0, enable_cooling=False,
            ))
            now = time.time()
            for i in range(n):
                lb.on_task_assigned(f"t{i}", "w1", assigned_at=now)
            penalties.append(lb.signal("w1").load_penalty)

        for i in range(1, len(penalties)):
            self.assertLessEqual(penalties[i], penalties[i-1])


class TestCapacityEstimation(unittest.TestCase):
    """Test EWMA capacity estimation."""

    def test_default_capacity(self):
        lb = LoadBridge(LoadBridgeConfig(default_capacity=5.0))
        sig = lb.signal("new")
        self.assertEqual(sig.estimated_capacity, 5.0)

    def test_capacity_adapts(self):
        lb = LoadBridge(LoadBridgeConfig(default_capacity=3.0, ewma_alpha=0.3))
        now = time.time()

        for day in range(5):
            day_ts = now - (5 - day) * 86400
            for i in range(8):
                lb.on_task_assigned(f"d{day}_t{i}", "w1", assigned_at=day_ts)
                lb.on_task_completed(f"d{day}_t{i}", "w1", completed_at=day_ts + i * 1000)

        sig = lb.signal("w1")
        self.assertGreater(sig.estimated_capacity, 5.0)

    def test_confidence_grows(self):
        lb = LoadBridge(LoadBridgeConfig(min_history_days=2))
        now = time.time()

        lb.on_task_assigned("t1", "w1", assigned_at=now - 86400)
        lb.on_task_completed("t1", "w1", completed_at=now - 86400 + 100)

        lb.on_task_assigned("t2", "w1", assigned_at=now)
        lb.on_task_completed("t2", "w1", completed_at=now + 100)

        sig = lb.signal("w1")
        self.assertGreater(sig.capacity_confidence, 0.0)


class TestCooling(unittest.TestCase):
    """Test burst detection and cooling."""

    def test_cooling_on_burst(self):
        lb = LoadBridge(LoadBridgeConfig(
            default_capacity=20.0,
            enable_cooling=True,
            cooling_burst_count=3,
            cooling_window_seconds=3600.0,
        ))
        now = time.time()
        for i in range(4):
            lb.on_task_assigned(f"t{i}", "w1", assigned_at=now - 1000)
            lb.on_task_completed(f"t{i}", "w1", completed_at=now - (3 - i) * 60)

        sig = lb.signal("w1")
        self.assertTrue(sig.cooling_active)

    def test_no_cooling_below_threshold(self):
        lb = LoadBridge(LoadBridgeConfig(
            enable_cooling=True,
            cooling_burst_count=5,
        ))
        now = time.time()
        for i in range(3):
            lb.on_task_assigned(f"t{i}", "w1", assigned_at=now - 500)
            lb.on_task_completed(f"t{i}", "w1", completed_at=now - (2 - i) * 100)

        sig = lb.signal("w1")
        self.assertFalse(sig.cooling_active)

    def test_cooling_disabled(self):
        lb = LoadBridge(LoadBridgeConfig(enable_cooling=False))
        now = time.time()
        for i in range(10):
            lb.on_task_assigned(f"t{i}", "w1", assigned_at=now - 1000)
            lb.on_task_completed(f"t{i}", "w1", completed_at=now - (9 - i) * 30)

        sig = lb.signal("w1")
        self.assertFalse(sig.cooling_active)


class TestFleetUtilization(unittest.TestCase):
    """Test fleet-wide status."""

    def test_empty_fleet(self):
        lb = LoadBridge()
        fleet = lb.fleet_utilization()
        self.assertEqual(fleet.total_workers, 0)

    def test_mixed_fleet(self):
        lb = LoadBridge(LoadBridgeConfig(default_capacity=10.0))
        now = time.time()

        for i in range(3):
            lb.on_task_assigned(f"w1_t{i}", "w1", assigned_at=now)
        for i in range(8):
            lb.on_task_assigned(f"w2_t{i}", "w2", assigned_at=now)

        fleet = lb.fleet_utilization()
        self.assertEqual(fleet.active_workers, 2)
        self.assertEqual(fleet.total_active_tasks, 11)

    def test_bottleneck_detection(self):
        lb = LoadBridge(LoadBridgeConfig(default_capacity=10.0, enable_cooling=False))
        now = time.time()
        for i in range(10):
            lb.on_task_assigned(f"t{i}", "heavy", assigned_at=now)

        fleet = lb.fleet_utilization()
        self.assertIn("heavy", fleet.bottleneck_workers)

    def test_fleet_to_dict(self):
        lb = LoadBridge()
        fleet = lb.fleet_utilization()
        d = fleet.to_dict()
        self.assertIn("total_workers", d)
        self.assertIn("avg_utilization", d)


class TestLeastLoaded(unittest.TestCase):
    """Test least-loaded selection."""

    def test_ordering(self):
        lb = LoadBridge(LoadBridgeConfig(default_capacity=10.0))
        now = time.time()

        for i in range(8):
            lb.on_task_assigned(f"w1_{i}", "w1", assigned_at=now)
        for i in range(2):
            lb.on_task_assigned(f"w2_{i}", "w2", assigned_at=now)

        least = lb.get_least_loaded(["w1", "w2"])
        self.assertEqual(least[0].worker_id, "w2")
        self.assertEqual(least[1].worker_id, "w1")


class TestRiskClassification(unittest.TestCase):
    """Test risk level classification."""

    def test_all_levels(self):
        lb = LoadBridge(LoadBridgeConfig(default_capacity=10.0, enable_cooling=False))

        # idle
        self.assertEqual(lb.signal("idle").risk_level, "idle")

        # light
        lb.on_task_assigned("t1", "light")
        self.assertEqual(lb.signal("light").risk_level, "light")

        # moderate
        for i in range(7):
            lb.on_task_assigned(f"m{i}", "mod")
        self.assertEqual(lb.signal("mod").risk_level, "moderate")

        # heavy
        for i in range(9):
            lb.on_task_assigned(f"h{i}", "heavy")
        self.assertEqual(lb.signal("heavy").risk_level, "heavy")

        # overloaded
        for i in range(12):
            lb.on_task_assigned(f"o{i}", "over")
        self.assertEqual(lb.signal("over").risk_level, "overloaded")


class TestWorkerProfile(unittest.TestCase):
    """Test worker profile endpoint."""

    def test_profile(self):
        lb = LoadBridge()
        now = time.time()

        for i in range(3):
            lb.on_task_assigned(f"t{i}", "w1", assigned_at=now - 1000)
            lb.on_task_completed(f"t{i}", "w1", completed_at=now)

        profile = lb.worker_profile("w1", days=7)
        self.assertEqual(profile["total_completions"], 3)
        self.assertEqual(profile["worker_id"], "w1")
        self.assertIn("avg_duration_seconds", profile)


class TestPersistence(unittest.TestCase):
    """Test save/load."""

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "lb.json")

            lb1 = LoadBridge(LoadBridgeConfig(default_capacity=10.0))
            now = time.time()
            for i in range(5):
                lb1.on_task_assigned(f"t{i}", "w1", assigned_at=now)
            lb1.on_task_completed("t0", "w1", completed_at=now + 100)
            lb1.save(path)

            lb2 = LoadBridge(LoadBridgeConfig(default_capacity=10.0))
            lb2.load(path)
            sig = lb2.signal("w1")
            self.assertEqual(sig.active_tasks, 4)

    def test_load_missing(self):
        lb = LoadBridge()
        lb.load("/nonexistent/path.json")
        self.assertEqual(lb.fleet_utilization().total_workers, 0)


class TestCleanup(unittest.TestCase):
    """Test stale cleanup."""

    def test_cleanup_stale(self):
        lb = LoadBridge()
        old = time.time() - 200000
        lb.on_task_assigned("stale", "w1", assigned_at=old)
        lb.on_task_assigned("fresh", "w1", assigned_at=time.time())

        removed = lb.cleanup_stale(max_age_hours=48.0)
        self.assertEqual(removed, 1)
        self.assertEqual(lb.signal("w1").active_tasks, 1)


class TestHealth(unittest.TestCase):
    """Test health endpoint."""

    def test_health(self):
        lb = LoadBridge()
        h = lb.health()
        self.assertEqual(h["status"], "operational")
        self.assertEqual(h["module_number"], 75)
        self.assertEqual(h["signal_number"], 28)

    def test_repr(self):
        lb = LoadBridge()
        r = repr(lb)
        self.assertIn("LoadBridge", r)


class TestEdgeCases(unittest.TestCase):
    """Edge cases."""

    def test_same_task_diff_workers(self):
        lb = LoadBridge()
        lb.on_task_assigned("t1", "w1")
        lb.on_task_assigned("t1", "w2")
        self.assertEqual(lb.signal("w1").active_tasks, 1)
        self.assertEqual(lb.signal("w2").active_tasks, 1)

    def test_duplicate_assignment(self):
        lb = LoadBridge()
        lb.on_task_assigned("t1", "w1", complexity=1.0)
        lb.on_task_assigned("t1", "w1", complexity=2.0)
        sig = lb.signal("w1")
        self.assertEqual(sig.active_tasks, 1)
        self.assertAlmostEqual(sig.active_complexity, 2.0)

    def test_zero_capacity(self):
        lb = LoadBridge(LoadBridgeConfig(default_capacity=0.0, min_capacity=1.0))
        sig = lb.signal("w1")
        self.assertGreaterEqual(sig.estimated_capacity, 1.0)

    def test_stats_counting(self):
        lb = LoadBridge()
        lb.on_task_assigned("t1", "w1")
        lb.on_task_assigned("t2", "w1")
        lb.on_task_completed("t1", "w1")
        lb.on_task_expired("t2", "w1")

        h = lb.health()
        self.assertEqual(h["total_assignments"], 2)
        self.assertEqual(h["total_completions"], 1)
        self.assertEqual(h["total_expirations"], 1)


if __name__ == "__main__":
    unittest.main()
