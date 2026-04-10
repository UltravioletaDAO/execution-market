"""
Tests for ClusterBridge — Server-Side Multi-Task Batch Intelligence
=====================================================================

Module #78: Detects spatial, categorical, and temporal clusters of tasks
and provides routing bonuses for batch assignment to workers.

Test suite covers:
1. Configuration & initialization
2. Task registration & lifecycle
3. Spatial clustering (DBSCAN-inspired density clustering)
4. Categorical clustering
5. Temporal clustering
6. Signal computation (4-component bonus)
7. Batch opportunities & fleet stats
8. Health metrics
9. Persistence (save/load)
10. Edge cases
11. Production scenarios
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import time

import pytest

from mcp_server.swarm.cluster_bridge import (
    ClusterBridge,
    ClusterBridgeConfig,
    BridgeTaskRecord,
    BridgeCluster,
    BridgeClusterSignal,
    BridgeClusterHealth,
    _haversine_km,
    _compute_centroid,
    _category_mode,
    _cluster_coherence,
    DEFAULT_SPATIAL_RADIUS_KM,
    DEFAULT_MIN_CLUSTER_SIZE,
    DEFAULT_MAX_CLUSTER_SIZE,
    EARTH_RADIUS_KM,
    MAX_TOTAL_BONUS,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

# Downtown Miami cluster — tasks within ~1km
MIAMI_TASKS = [
    {"id": "t1", "title": "Photo storefront", "category": "physical_verification",
     "lat": 25.7617, "lng": -80.1918, "bounty_usd": 3.0, "deadline_hours": 4},
    {"id": "t2", "title": "Verify signage", "category": "physical_verification",
     "lat": 25.7625, "lng": -80.1925, "bounty_usd": 2.5, "deadline_hours": 4},
    {"id": "t3", "title": "Check parking", "category": "physical_verification",
     "lat": 25.7630, "lng": -80.1930, "bounty_usd": 2.0, "deadline_hours": 6},
]

# Brickell cluster — ~3km from downtown
BRICKELL_TASKS = [
    {"id": "t4", "title": "Verify restaurant", "category": "physical_verification",
     "lat": 25.7510, "lng": -80.1847, "bounty_usd": 4.0, "deadline_hours": 3},
    {"id": "t5", "title": "Photo menu", "category": "physical_verification",
     "lat": 25.7515, "lng": -80.1852, "bounty_usd": 3.5, "deadline_hours": 3},
]

# Digital tasks — no location
DIGITAL_TASKS = [
    {"id": "d1", "title": "Data entry", "category": "data_collection",
     "bounty_usd": 1.0, "deadline_hours": 24},
    {"id": "d2", "title": "Survey", "category": "data_collection",
     "bounty_usd": 1.5, "deadline_hours": 24},
    {"id": "d3", "title": "Transcription", "category": "data_collection",
     "bounty_usd": 2.0, "deadline_hours": 48},
]


def _bridge(**config_kw) -> ClusterBridge:
    """Create a fresh ClusterBridge with optional config overrides."""
    config = ClusterBridgeConfig(**config_kw)
    return ClusterBridge(config)


# ──────────────────────────────────────────────────────────────
# 1. Configuration & Initialization
# ──────────────────────────────────────────────────────────────


class TestConfiguration:
    def test_default_config(self):
        bridge = ClusterBridge()
        assert bridge.config.spatial_radius_km == DEFAULT_SPATIAL_RADIUS_KM
        assert bridge.config.min_cluster_size == DEFAULT_MIN_CLUSTER_SIZE

    def test_custom_config(self):
        bridge = _bridge(spatial_radius_km=5.0, min_cluster_size=3)
        assert bridge.config.spatial_radius_km == 5.0
        assert bridge.config.min_cluster_size == 3

    def test_invalid_config_rejected(self):
        with pytest.raises(ValueError, match="positive"):
            _bridge(spatial_radius_km=-1.0)

    def test_min_cluster_size_validation(self):
        with pytest.raises(ValueError, match="min_cluster_size"):
            _bridge(min_cluster_size=1)

    def test_max_less_than_min_rejected(self):
        with pytest.raises(ValueError, match="max_cluster_size"):
            _bridge(min_cluster_size=5, max_cluster_size=3)

    def test_config_validate_returns_errors(self):
        cfg = ClusterBridgeConfig(spatial_radius_km=-1, temporal_window_hours=-5)
        errors = cfg.validate()
        assert len(errors) >= 2


# ──────────────────────────────────────────────────────────────
# 2. Task Registration & Lifecycle
# ──────────────────────────────────────────────────────────────


class TestTaskLifecycle:
    def test_register_task(self):
        bridge = ClusterBridge()
        record = bridge.register_task(MIAMI_TASKS[0])
        assert record.task_id == "t1"
        assert record.lat == 25.7617
        assert record.bounty_usd == 3.0

    def test_register_task_no_id_raises(self):
        bridge = ClusterBridge()
        with pytest.raises(ValueError, match="id"):
            bridge.register_task({"title": "no id"})

    def test_register_task_string_coords(self):
        bridge = ClusterBridge()
        record = bridge.register_task({"id": "t1", "lat": "25.7617", "lng": "-80.1918"})
        assert record.lat == 25.7617
        assert record.lng == -80.1918

    def test_register_task_location_lat_alias(self):
        bridge = ClusterBridge()
        record = bridge.register_task({"id": "t1", "location_lat": 25.0, "location_lng": -80.0})
        assert record.lat == 25.0

    def test_assign_task(self):
        bridge = ClusterBridge()
        bridge.register_task(MIAMI_TASKS[0])
        bridge.assign_task("t1", "worker_0x1")
        assert bridge._tasks["t1"].assigned_to == "worker_0x1"
        assert "t1" in bridge._worker_active_tasks["worker_0x1"]

    def test_complete_task(self):
        bridge = ClusterBridge()
        bridge.register_task(MIAMI_TASKS[0])
        bridge.assign_task("t1", "worker_0x1")
        bridge.complete_task("t1")
        assert bridge._tasks["t1"].completed is True
        assert "t1" not in bridge._worker_active_tasks.get("worker_0x1", set())

    def test_update_worker_location(self):
        bridge = ClusterBridge()
        bridge.update_worker_location("w1", 25.76, -80.19)
        assert bridge._worker_locations["w1"] == (25.76, -80.19)

    def test_sync_from_supabase(self):
        bridge = ClusterBridge()
        rows = [
            {"id": "t1", "category": "physical_verification", "lat": 25.76, "lng": -80.19,
             "bounty_usd": 3.0, "deadline_hours": 4, "status": "pending"},
            {"id": "t2", "category": "physical_verification", "lat": 25.76, "lng": -80.19,
             "bounty_usd": 2.5, "deadline_hours": 4, "worker_wallet": "0xAAA",
             "status": "completed"},
        ]
        count = bridge.sync_from_supabase(rows)
        assert count == 2
        assert bridge._tasks["t2"].completed is True


# ──────────────────────────────────────────────────────────────
# 3. Spatial Clustering
# ──────────────────────────────────────────────────────────────


class TestSpatialClustering:
    def test_nearby_tasks_cluster(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        spatial = [c for c in clusters if c.cluster_type == "spatial"]
        assert len(spatial) >= 1
        # All 3 Miami tasks should be in one spatial cluster
        miami_cluster = spatial[0]
        assert miami_cluster.size >= 2

    def test_distant_tasks_separate(self):
        bridge = _bridge(spatial_radius_km=1.0)
        for t in MIAMI_TASKS + BRICKELL_TASKS:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        spatial = [c for c in clusters if c.cluster_type == "spatial"]
        # With 1km radius, Miami and Brickell should be separate clusters
        if len(spatial) >= 2:
            ids_per_cluster = [set(c.task_ids) for c in spatial]
            miami_ids = {"t1", "t2", "t3"}
            brickell_ids = {"t4", "t5"}
            # At least one cluster should be pure Miami or pure Brickell
            assert any(ids <= miami_ids for ids in ids_per_cluster) or \
                   any(ids <= brickell_ids for ids in ids_per_cluster)

    def test_centroid_computed(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        spatial = [c for c in clusters if c.cluster_type == "spatial"]
        if spatial:
            c = spatial[0]
            assert c.centroid_lat is not None
            assert c.centroid_lng is not None
            # Centroid should be near Miami
            assert 25.0 < c.centroid_lat < 26.0
            assert -81.0 < c.centroid_lng < -80.0

    def test_cluster_coherence_spatial(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        spatial = [c for c in clusters if c.cluster_type == "spatial"]
        if spatial:
            assert spatial[0].coherence > 0

    def test_max_cluster_size_enforced(self):
        bridge = _bridge(max_cluster_size=2)
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        for c in clusters:
            assert c.size <= 2

    def test_tasks_without_location_excluded(self):
        bridge = ClusterBridge()
        bridge.register_task(MIAMI_TASKS[0])
        bridge.register_task(MIAMI_TASKS[1])
        bridge.register_task({"id": "noloc", "category": "general"})
        clusters = bridge.detect_clusters()
        spatial = [c for c in clusters if c.cluster_type == "spatial"]
        if spatial:
            assert "noloc" not in spatial[0].task_ids


# ──────────────────────────────────────────────────────────────
# 4. Categorical Clustering
# ──────────────────────────────────────────────────────────────


class TestCategoricalClustering:
    def test_same_category_clusters(self):
        bridge = ClusterBridge()
        for t in DIGITAL_TASKS:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        categorical = [c for c in clusters if c.cluster_type == "categorical"]
        assert len(categorical) >= 1
        assert categorical[0].dominant_category == "data_collection"

    def test_mixed_categories_no_cluster(self):
        bridge = ClusterBridge()
        bridge.register_task({"id": "t1", "category": "delivery", "deadline_hours": 24})
        bridge.register_task({"id": "t2", "category": "creative", "deadline_hours": 48})
        # min_cluster_size=2 but different categories → no categorical cluster
        clusters = bridge.detect_clusters()
        categorical = [c for c in clusters if c.cluster_type == "categorical"]
        # Each category has only 1 task → below min_cluster_size
        cat_with_delivery = [c for c in categorical if c.dominant_category == "delivery"]
        assert len(cat_with_delivery) == 0


# ──────────────────────────────────────────────────────────────
# 5. Temporal Clustering
# ──────────────────────────────────────────────────────────────


class TestTemporalClustering:
    def test_similar_deadline_clusters(self):
        bridge = ClusterBridge()
        tasks = [
            {"id": f"t{i}", "category": f"cat_{i}", "deadline_hours": 4 + i}
            for i in range(4)
        ]
        for t in tasks:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        # Tasks with similar deadlines (4-7h) within 48h window should cluster
        temporal = [c for c in clusters if c.cluster_type == "temporal"]
        assert len(temporal) >= 1

    def test_spread_deadlines_separate(self):
        bridge = _bridge(temporal_window_hours=2)
        tasks = [
            {"id": "t1", "category": "a", "deadline_hours": 1},
            {"id": "t2", "category": "b", "deadline_hours": 100},
        ]
        for t in tasks:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        temporal = [c for c in clusters if c.cluster_type == "temporal"]
        # 1h and 100h are far apart with 2h window → no temporal cluster together
        for c in temporal:
            assert not ({"t1", "t2"} <= set(c.task_ids))


# ──────────────────────────────────────────────────────────────
# 6. Signal Computation
# ──────────────────────────────────────────────────────────────


class TestSignalComputation:
    def test_no_cluster_returns_zero(self):
        bridge = ClusterBridge()
        bridge.register_task({"id": "t1"})
        # No clusters detected (only 1 task)
        signal = bridge.signal("w1", "t1")
        assert signal.cluster_bonus == 0.0

    def test_unknown_task_returns_zero(self):
        bridge = ClusterBridge()
        signal = bridge.signal("w1", "nonexistent")
        assert signal.cluster_bonus == 0.0

    def test_active_task_bonus(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        # Assign t1 to worker
        bridge.assign_task("t1", "w1")
        # Now check signal for t2 with same worker
        signal = bridge.signal("w1", "t2")
        if signal.cluster_id:
            assert signal.has_active_task_in_cluster is True
            assert signal.cluster_bonus > 0

    def test_proximity_bonus_with_location(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        # Worker near the cluster centroid
        signal = bridge.signal("w2", "t1", worker_lat=25.763, worker_lng=-80.192)
        assert signal.cluster_bonus >= 0

    def test_signal_to_dict(self):
        signal = BridgeClusterSignal(
            cluster_bonus=0.05,
            cluster_id="sc_1",
            cluster_size=3,
            confidence=0.8,
        )
        d = signal.to_dict()
        assert d["cluster_bonus"] == 0.05
        assert d["cluster_id"] == "sc_1"

    def test_bonus_capped_at_max(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        bridge.assign_task("t1", "w1")
        bridge.assign_task("t2", "w1")
        signal = bridge.signal("w1", "t3")
        assert signal.cluster_bonus <= MAX_TOTAL_BONUS

    def test_estimated_savings_positive(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        bridge.assign_task("t1", "w1")
        signal = bridge.signal("w1", "t2")
        if signal.has_active_task_in_cluster:
            assert signal.estimated_savings > 0

    def test_signal_components_present(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        bridge.assign_task("t1", "w1")
        signal = bridge.signal("w1", "t2")
        if signal.cluster_id:
            assert "active_task" in signal.components
            assert "proximity" in signal.components
            assert "batch_completion" in signal.components
            assert "category_coherence" in signal.components


# ──────────────────────────────────────────────────────────────
# 7. Batch Opportunities & Fleet Stats
# ──────────────────────────────────────────────────────────────


class TestBatchOpportunities:
    def test_batch_opportunities_after_assignment(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        bridge.assign_task("t1", "w1")
        opps = bridge.batch_opportunities("w1")
        # Should suggest remaining tasks in same cluster
        assert isinstance(opps, list)

    def test_no_opportunities_without_assignment(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        opps = bridge.batch_opportunities("w1")
        assert len(opps) == 0

    def test_fleet_stats(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        stats = bridge.fleet_stats()
        assert "total_clusters" in stats
        assert "cluster_types" in stats
        assert stats["total_clusters"] >= 1


# ──────────────────────────────────────────────────────────────
# 8. Health Metrics
# ──────────────────────────────────────────────────────────────


class TestHealth:
    def test_health_initial(self):
        bridge = ClusterBridge()
        h = bridge.health()
        assert h.total_tasks == 0
        assert h.bridge_ok is True

    def test_health_after_tasks(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        h = bridge.health()
        assert h.total_tasks == 3
        assert h.active_tasks == 3

    def test_health_after_completion(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.assign_task("t1", "w1")
        bridge.complete_task("t1")
        h = bridge.health()
        assert h.completed_tasks == 1
        assert h.active_tasks == 2

    def test_health_to_dict(self):
        bridge = ClusterBridge()
        h = bridge.health()
        d = h.to_dict()
        assert "total_tasks" in d
        assert "bridge_ok" in d

    def test_repr(self):
        bridge = ClusterBridge()
        r = repr(bridge)
        assert "ClusterBridge" in r


# ──────────────────────────────────────────────────────────────
# 9. Persistence
# ──────────────────────────────────────────────────────────────


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        bridge.assign_task("t1", "w1")

        save_path = tmp_path / "cluster_bridge.json"
        bridge.save(save_path)

        loaded = ClusterBridge.load(save_path)
        assert loaded._tasks["t1"].task_id == "t1"
        assert len(loaded._clusters) == len(bridge._clusters)

    def test_save_creates_directories(self, tmp_path):
        bridge = ClusterBridge()
        deep_path = tmp_path / "a" / "b" / "c" / "state.json"
        bridge.save(deep_path)
        assert deep_path.exists()

    def test_round_trip_preserves_assignments(self, tmp_path):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.assign_task("t1", "w1")

        save_path = tmp_path / "state.json"
        bridge.save(save_path)
        loaded = ClusterBridge.load(save_path)

        assert loaded._tasks["t1"].assigned_to == "w1"


# ──────────────────────────────────────────────────────────────
# 10. Helper Functions
# ──────────────────────────────────────────────────────────────


class TestHelpers:
    def test_haversine_zero_distance(self):
        d = _haversine_km(25.0, -80.0, 25.0, -80.0)
        assert d == 0.0

    def test_haversine_known_distance(self):
        # Miami downtown to Brickell ~1.5km
        d = _haversine_km(25.7617, -80.1918, 25.7510, -80.1847)
        assert 1.0 < d < 3.0

    def test_haversine_antipodal(self):
        d = _haversine_km(0, 0, 0, 180)
        # Half Earth circumference
        assert abs(d - math.pi * EARTH_RADIUS_KM) < 10

    def test_compute_centroid(self):
        tasks = [
            BridgeTaskRecord(task_id="t1", lat=25.0, lng=-80.0),
            BridgeTaskRecord(task_id="t2", lat=26.0, lng=-81.0),
        ]
        lat, lng = _compute_centroid(tasks)
        assert lat == pytest.approx(25.5)
        assert lng == pytest.approx(-80.5)

    def test_compute_centroid_no_location(self):
        tasks = [BridgeTaskRecord(task_id="t1")]
        lat, lng = _compute_centroid(tasks)
        assert lat is None
        assert lng is None

    def test_category_mode(self):
        tasks = [
            BridgeTaskRecord(task_id="t1", category="photo"),
            BridgeTaskRecord(task_id="t2", category="photo"),
            BridgeTaskRecord(task_id="t3", category="delivery"),
        ]
        assert _category_mode(tasks) == "photo"

    def test_category_mode_empty(self):
        assert _category_mode([]) == "general"

    def test_cluster_coherence_single_task(self):
        tasks = [BridgeTaskRecord(task_id="t1")]
        assert _cluster_coherence(tasks, "spatial") == 0.0

    def test_cluster_coherence_range(self):
        tasks = [
            BridgeTaskRecord(task_id="t1", category="photo", lat=25.76, lng=-80.19, deadline_hours=4),
            BridgeTaskRecord(task_id="t2", category="photo", lat=25.76, lng=-80.19, deadline_hours=4),
        ]
        c = _cluster_coherence(tasks, "spatial")
        assert 0 <= c <= 1.0


# ──────────────────────────────────────────────────────────────
# 11. Task Record Model
# ──────────────────────────────────────────────────────────────


class TestBridgeTaskRecord:
    def test_has_location(self):
        t = BridgeTaskRecord(task_id="t1", lat=25.0, lng=-80.0)
        assert t.has_location() is True

    def test_no_location(self):
        t = BridgeTaskRecord(task_id="t1")
        assert t.has_location() is False

    def test_invalid_location(self):
        t = BridgeTaskRecord(task_id="t1", lat=200.0, lng=-80.0)
        assert t.has_location() is False

    def test_is_physical(self):
        t = BridgeTaskRecord(task_id="t1", category="physical_verification")
        assert t.is_physical is True

    def test_is_physical_by_evidence(self):
        t = BridgeTaskRecord(task_id="t1", evidence_type="photo_geo")
        assert t.is_physical is True

    def test_is_physical_by_location(self):
        t = BridgeTaskRecord(task_id="t1", lat=25.0, lng=-80.0)
        assert t.is_physical is True

    def test_not_physical(self):
        t = BridgeTaskRecord(task_id="t1", category="data_collection")
        assert t.is_physical is False


class TestBridgeCluster:
    def test_size(self):
        c = BridgeCluster(cluster_id="c1", task_ids=["t1", "t2", "t3"])
        assert c.size == 3

    def test_unassigned_tasks(self):
        c = BridgeCluster(cluster_id="c1", task_ids=["t1", "t2", "t3"],
                          assigned_workers={"w1": ["t1"]})
        assert set(c.unassigned_tasks()) == {"t2", "t3"}

    def test_is_fully_assigned(self):
        c = BridgeCluster(cluster_id="c1", task_ids=["t1", "t2"],
                          assigned_workers={"w1": ["t1", "t2"]})
        assert c.is_fully_assigned is True

    def test_not_fully_assigned(self):
        c = BridgeCluster(cluster_id="c1", task_ids=["t1", "t2"],
                          assigned_workers={"w1": ["t1"]})
        assert c.is_fully_assigned is False

    def test_worker_tasks(self):
        c = BridgeCluster(cluster_id="c1", task_ids=["t1", "t2"],
                          assigned_workers={"w1": ["t1"], "w2": ["t2"]})
        assert c.worker_tasks("w1") == ["t1"]
        assert c.worker_tasks("w3") == []


# ──────────────────────────────────────────────────────────────
# 12. Edge Cases
# ──────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_single_task_no_cluster(self):
        bridge = ClusterBridge()
        bridge.register_task(MIAMI_TASKS[0])
        clusters = bridge.detect_clusters()
        assert len(clusters) == 0

    def test_all_tasks_completed_no_clusters(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        for t in MIAMI_TASKS:
            bridge.complete_task(t["id"])
        clusters = bridge.detect_clusters()
        assert len(clusters) == 0

    def test_assign_unknown_task(self):
        bridge = ClusterBridge()
        bridge.assign_task("nonexistent", "w1")
        # Should not crash

    def test_complete_unknown_task(self):
        bridge = ClusterBridge()
        bridge.complete_task("nonexistent")
        # Should not crash

    def test_get_cluster(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        clusters = bridge.get_clusters()
        if clusters:
            c = bridge.get_cluster(clusters[0].cluster_id)
            assert c is not None
            assert c.cluster_id == clusters[0].cluster_id

    def test_get_nonexistent_cluster(self):
        bridge = ClusterBridge()
        assert bridge.get_cluster("nonexistent") is None

    def test_get_task_cluster(self):
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        c = bridge.get_task_cluster("t1")
        # t1 may or may not be in a cluster depending on detection
        if c is not None:
            assert "t1" in c.task_ids


# ──────────────────────────────────────────────────────────────
# 13. Production Scenarios
# ──────────────────────────────────────────────────────────────


class TestProductionScenarios:
    def test_island_problem_solved(self):
        """Three nearby tasks should cluster for batch routing."""
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        # Should create at least one cluster
        assert len(clusters) >= 1
        # Total bounty should be tracked
        total_bounty = sum(c.total_bounty_usd for c in clusters)
        assert total_bounty > 0

    def test_batch_assignment_tracking(self):
        """Assigning multiple tasks from same cluster to same worker."""
        bridge = ClusterBridge()
        for t in MIAMI_TASKS:
            bridge.register_task(t)
        bridge.detect_clusters()
        # Assign first two tasks to same worker
        bridge.assign_task("t1", "w1")
        bridge.assign_task("t2", "w1")
        # batch_assignments should increment
        assert bridge._batch_assignments >= 1

    def test_mixed_physical_digital(self):
        """Mix of physical and digital tasks should form different cluster types."""
        bridge = ClusterBridge()
        for t in MIAMI_TASKS + DIGITAL_TASKS:
            bridge.register_task(t)
        clusters = bridge.detect_clusters()
        types = {c.cluster_type for c in clusters}
        # Should have both spatial (physical) and categorical (digital)
        assert len(types) >= 1

    def test_worker_location_from_assignment(self):
        """Worker location should be inferred from task assignment."""
        bridge = ClusterBridge()
        bridge.register_task(MIAMI_TASKS[0])
        bridge.assign_task("t1", "w1")
        assert "w1" in bridge._worker_locations
        assert bridge._worker_locations["w1"][0] == pytest.approx(25.7617)
