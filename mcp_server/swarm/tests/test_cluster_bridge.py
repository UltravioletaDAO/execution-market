"""
Tests for ClusterBridge — Module #78: Multi-Task Batch Intelligence
===================================================================

Server-side counterpart to AutoJob's TaskClusterEngine (Signal #31).
Tests: cluster detection, signal computation, assignment tracking,
Supabase sync, batch opportunities, health, persistence, edge cases,
coordinator integration.
"""

import json
import tempfile
import time
from pathlib import Path

import pytest

import sys
import os
import importlib

# Ensure cluster_bridge is importable WITHOUT pulling in the full swarm package
# (reputation_bridge uses `list[str] | None` syntax that fails on Python <3.10)
_bridge_dir = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _bridge_dir)

_mod = importlib.import_module("cluster_bridge")
ClusterBridge = _mod.ClusterBridge
ClusterBridgeConfig = _mod.ClusterBridgeConfig
BridgeTaskRecord = _mod.BridgeTaskRecord
BridgeCluster = _mod.BridgeCluster
BridgeClusterSignal = _mod.BridgeClusterSignal
BridgeClusterHealth = _mod.BridgeClusterHealth
_haversine_km = _mod._haversine_km
_compute_centroid = _mod._compute_centroid
_category_mode = _mod._category_mode
_cluster_coherence = _mod._cluster_coherence
MAX_TOTAL_BONUS = _mod.MAX_TOTAL_BONUS


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def bridge():
    return ClusterBridge(ClusterBridgeConfig())


@pytest.fixture
def nearby_tasks():
    return [
        {"id": "t_a", "title": "Photo storefront", "lat": 25.7617, "lng": -80.1918,
         "category": "physical_verification", "bounty_usd": 3.0, "deadline_hours": 24},
        {"id": "t_b", "title": "Verify signage", "lat": 25.7619, "lng": -80.1916,
         "category": "physical_verification", "bounty_usd": 2.5, "deadline_hours": 24},
        {"id": "t_c", "title": "Check parking", "lat": 25.7621, "lng": -80.1914,
         "category": "physical_verification", "bounty_usd": 2.0, "deadline_hours": 24},
    ]


@pytest.fixture
def digital_tasks():
    return [
        {"id": "d1", "category": "translation", "bounty_usd": 5.0},
        {"id": "d2", "category": "translation", "bounty_usd": 3.0},
        {"id": "d3", "category": "translation", "bounty_usd": 8.0},
    ]


# ─── Config ───────────────────────────────────────────────────────────────────

class TestConfig:
    def test_default_valid(self):
        config = ClusterBridgeConfig()
        assert config.validate() == []

    def test_invalid_radius(self):
        config = ClusterBridgeConfig(spatial_radius_km=0)
        assert len(config.validate()) > 0

    def test_invalid_min_size(self):
        config = ClusterBridgeConfig(min_cluster_size=1)
        assert len(config.validate()) > 0

    def test_max_lt_min(self):
        config = ClusterBridgeConfig(min_cluster_size=5, max_cluster_size=3)
        assert len(config.validate()) > 0

    def test_constructor_rejects_invalid(self):
        with pytest.raises(ValueError):
            ClusterBridge(ClusterBridgeConfig(spatial_radius_km=-1))


# ─── Task Registration ───────────────────────────────────────────────────────

class TestRegistration:
    def test_register_basic(self, bridge):
        rec = bridge.register_task({"id": "t1", "title": "Test"})
        assert rec.task_id == "t1"

    def test_register_with_location(self, bridge):
        rec = bridge.register_task({"id": "t1", "lat": 25.0, "lng": -80.0})
        assert rec.has_location()

    def test_register_string_coords(self, bridge):
        rec = bridge.register_task({"id": "t1", "lat": "25.5", "lng": "-80.5"})
        assert rec.lat == 25.5

    def test_no_id_raises(self, bridge):
        with pytest.raises(ValueError):
            bridge.register_task({"title": "No ID"})

    def test_physical_detection(self, bridge):
        rec = bridge.register_task({"id": "t1", "category": "physical_verification"})
        assert rec.is_physical


# ─── Spatial Clustering ───────────────────────────────────────────────────────

class TestSpatialClustering:
    def test_nearby_tasks_form_cluster(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        spatial = [c for c in clusters if c.cluster_type == "spatial"]
        assert len(spatial) >= 1
        assert set(spatial[0].task_ids) == {"t_a", "t_b", "t_c"}

    def test_distant_no_cluster(self, bridge):
        bridge.register_task({"id": "t1", "lat": 25.0, "lng": -80.0})
        bridge.register_task({"id": "t2", "lat": 40.0, "lng": -74.0})
        clusters = bridge.detect_clusters()
        spatial = [c for c in clusters if c.cluster_type == "spatial"]
        assert len(spatial) == 0

    def test_centroid_computed(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        spatial = [c for c in clusters if c.cluster_type == "spatial"]
        assert spatial[0].centroid_lat is not None

    def test_two_separate_clusters(self, bridge):
        bridge.register_task({"id": "a1", "lat": 25.76, "lng": -80.19})
        bridge.register_task({"id": "a2", "lat": 25.7601, "lng": -80.1901})
        bridge.register_task({"id": "b1", "lat": 25.79, "lng": -80.13})
        bridge.register_task({"id": "b2", "lat": 25.7901, "lng": -80.1301})
        clusters = bridge.detect_clusters()
        spatial = [c for c in clusters if c.cluster_type == "spatial"]
        assert len(spatial) == 2


# ─── Categorical Clustering ──────────────────────────────────────────────────

class TestCategoricalClustering:
    def test_same_category_clusters(self, bridge, digital_tasks):
        for t in digital_tasks:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        cat = [c for c in clusters if c.cluster_type == "categorical"]
        assert len(cat) >= 1
        assert cat[0].dominant_category == "translation"


# ─── Temporal Clustering ─────────────────────────────────────────────────────

class TestTemporalClustering:
    def test_similar_deadlines_cluster(self, bridge):
        bridge.register_task({"id": "t1", "category": "survey", "deadline_hours": 12})
        bridge.register_task({"id": "t2", "category": "review", "deadline_hours": 14})
        bridge.register_task({"id": "t3", "category": "audit", "deadline_hours": 10})
        clusters = bridge.detect_clusters()
        temporal = [c for c in clusters if c.cluster_type == "temporal"]
        assert len(temporal) >= 1


# ─── Signal Computation ──────────────────────────────────────────────────────

class TestSignal:
    def test_no_cluster_zero(self, bridge):
        bridge.register_task({"id": "t1"})
        sig = bridge.signal("w1", "t1")
        assert sig.cluster_bonus == 0.0

    def test_active_task_bonus(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")
        sig = bridge.signal("w1", "t_b")
        assert sig.cluster_bonus > 0
        assert sig.has_active_task_in_cluster

    def test_proximity_bonus(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        sig = bridge.signal("wx", "t_a", worker_lat=25.762, worker_lng=-80.192)
        assert sig.cluster_bonus > 0
        assert sig.distance_to_centroid_km is not None

    def test_far_worker_no_bonus(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        sig = bridge.signal("wfar", "t_a", worker_lat=40.0, worker_lng=-74.0)
        assert sig.cluster_bonus < 0.001

    def test_bonus_capped(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")
        bridge.assign_task("t_b", "w1")
        bridge.detect_clusters()
        sig = bridge.signal("w1", "t_c")
        assert sig.cluster_bonus <= MAX_TOTAL_BONUS

    def test_estimated_savings(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")
        sig = bridge.signal("w1", "t_b")
        assert sig.estimated_savings > 0

    def test_signal_to_dict(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")
        sig = bridge.signal("w1", "t_b")
        d = sig.to_dict()
        assert isinstance(d, dict)


# ─── Assignment Tracking ─────────────────────────────────────────────────────

class TestAssignment:
    def test_assign(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")
        assert bridge._tasks["t_a"].assigned_to == "w1"

    def test_complete(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")
        bridge.complete_task("t_a")
        assert bridge._tasks["t_a"].completed

    def test_location_from_assignment(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")
        assert "w1" in bridge._worker_locations

    def test_batch_counted(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")
        bridge.assign_task("t_b", "w1")
        assert bridge._batch_assignments >= 1


# ─── Supabase Sync ───────────────────────────────────────────────────────────

class TestSupabaseSync:
    def test_sync_basic(self, bridge):
        rows = [
            {"id": "t1", "lat": 25.76, "lng": -80.19, "category": "photo"},
            {"id": "t2", "lat": 25.7601, "lng": -80.1901, "category": "photo"},
        ]
        count = bridge.sync_from_supabase(rows)
        assert count == 2
        assert "t1" in bridge._tasks

    def test_sync_with_assignments(self, bridge):
        rows = [
            {"id": "t1", "lat": 25.76, "lng": -80.19, "worker_wallet": "0xABC"},
            {"id": "t2", "lat": 25.7601, "lng": -80.1901},
        ]
        bridge.sync_from_supabase(rows)
        assert bridge._tasks["t1"].assigned_to == "0xABC"

    def test_sync_completed(self, bridge):
        rows = [
            {"id": "t1", "status": "completed"},
            {"id": "t2", "status": "approved"},
        ]
        bridge.sync_from_supabase(rows)
        assert bridge._tasks["t1"].completed
        assert bridge._tasks["t2"].completed


# ─── Batch Opportunities ─────────────────────────────────────────────────────

class TestBatchOpportunities:
    def test_find_opportunities(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")
        opps = bridge.batch_opportunities("w1")
        assert len(opps) >= 1

    def test_no_assignments_no_opps(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        assert bridge.batch_opportunities("w1") == []


# ─── Analytics ────────────────────────────────────────────────────────────────

class TestAnalytics:
    def test_fleet_stats(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        stats = bridge.fleet_stats()
        assert stats["total_clusters"] >= 1
        assert "spatial" in stats["cluster_types"]

    def test_get_task_cluster(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        cluster = bridge.get_task_cluster("t_a")
        assert cluster is not None


# ─── Health ───────────────────────────────────────────────────────────────────

class TestHealth:
    def test_empty_healthy(self, bridge):
        h = bridge.health()
        assert h.bridge_ok
        assert h.total_tasks == 0

    def test_with_tasks(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        h = bridge.health()
        assert h.total_tasks == 3
        assert h.total_clusters >= 1

    def test_to_dict(self, bridge):
        d = bridge.health().to_dict()
        assert "bridge_ok" in d


# ─── Persistence ──────────────────────────────────────────────────────────────

class TestPersistence:
    def test_save_load(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        bridge.assign_task("t_a", "w1")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name

        bridge.save(path)
        loaded = ClusterBridge.load(path)
        assert len(loaded._tasks) == len(bridge._tasks)
        assert loaded._tasks["t_a"].assigned_to == "w1"
        Path(path).unlink()

    def test_loaded_functional(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        bridge.save(path)
        loaded = ClusterBridge.load(path)
        sig = loaded.signal("wx", "t_a", worker_lat=25.762, worker_lng=-80.192)
        assert sig.cluster_id is not None
        Path(path).unlink()


# ─── Edge Cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_unknown_task_signal(self, bridge):
        sig = bridge.signal("w1", "nonexistent")
        assert sig.cluster_bonus == 0.0

    def test_assign_nonexistent(self, bridge):
        bridge.assign_task("nope", "w1")  # Should not crash

    def test_complete_nonexistent(self, bridge):
        bridge.complete_task("nope")  # Should not crash

    def test_repr(self, bridge, nearby_tasks):
        for t in nearby_tasks:
            bridge.register_task(t)
        r = repr(bridge)
        assert "ClusterBridge" in r

    def test_single_task_no_cluster(self, bridge):
        bridge.register_task({"id": "solo"})
        assert bridge.detect_clusters() == []


# ─── Coordinator Integration ─────────────────────────────────────────────────

class TestCoordinatorIntegration:
    def test_coordinator_imports_cluster_bridge(self):
        """Verify coordinator.py file references ClusterBridge."""
        coord_path = os.path.join(os.path.dirname(__file__), "..", "coordinator.py")
        with open(coord_path) as f:
            source = f.read()
        assert "ClusterBridge" in source
        assert "cluster_bridge" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
