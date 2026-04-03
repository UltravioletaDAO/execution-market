"""
Tests for GeoBridge — Module #68

Signal #21: Geo Proximity Intelligence (server-side)

Coverage:
  - GeoRecord construction + raw row ingestion
  - GPS extraction from multiple EM formats (nested gps, flat, metadata)
  - Haversine distance computation
  - Grid cell computation
  - Nearby cells enumeration
  - Sub-signal computation: haversine, territory, commute, temporal
  - Main signal() method: digital vs physical, no-location fallback
  - Territory building: completions → cell counts
  - Commute willingness: low/high travel workers
  - Temporal clustering: active hours matching
  - Geo bonus sign: close worker positive, far worker negative
  - Leaderboard ordering
  - Worker territory map
  - Geo summary / health
  - Edge cases: unknown worker, minimal data, neutral priors
  - Constants: PHYSICAL_TASK_TYPES, DIGITAL_TASK_TYPES
"""

import math
import pytest

from mcp_server.swarm.geo_bridge import (
    GeoBridge,
    GeoRecord,
    GeoSignalResult,
    _WorkerGeoState,
    PHYSICAL_TASK_TYPES,
    DIGITAL_TASK_TYPES,
    MAX_GEO_BONUS,
    HAVERSINE_WEIGHT,
    TERRITORY_WEIGHT,
    COMMUTE_WEIGHT,
    TEMPORAL_WEIGHT,
    DECAY_CONSTANT_KM,
    EARTH_RADIUS_KM,
)


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

MIAMI_LAT = 25.7617
MIAMI_LNG = -80.1918

CORAL_GABLES_LAT = 25.7215
CORAL_GABLES_LNG = -80.2684   # ~8km from Miami

PARIS_LAT = 48.8566
PARIS_LNG = 2.3522


def make_bridge() -> GeoBridge:
    return GeoBridge()


def make_record(
    worker_id="w1",
    task_id="t1",
    task_type="photo",
    event_type="completed",
    task_lat=MIAMI_LAT,
    task_lng=MIAMI_LNG,
    worker_lat=None,
    worker_lng=None,
    task_hour=10,
    timestamp=None,
) -> GeoRecord:
    return GeoRecord(
        worker_id=worker_id,
        task_id=task_id,
        task_type=task_type,
        event_type=event_type,
        task_lat=task_lat,
        task_lng=task_lng,
        worker_lat=worker_lat,
        worker_lng=worker_lng,
        task_hour=task_hour,
        timestamp=timestamp,
    )


def populate_worker(bridge: GeoBridge, worker_id: str, lat: float, lng: float, n: int = 5):
    """Give a worker n completions at a specific location."""
    for i in range(n):
        rec = make_record(
            worker_id=worker_id,
            task_id=f"task_{i}",
            task_lat=lat + i * 0.001,   # slight variation within same cell
            task_lng=lng,
            task_hour=10,
        )
        bridge.ingest_records([rec])
    # Force last known location
    bridge._state[worker_id].last_known_lat = lat
    bridge._state[worker_id].last_known_lng = lng


# ---------------------------------------------------------------------------
# Haversine math
# ---------------------------------------------------------------------------

class TestHaversine:
    def test_same_point(self):
        d = GeoBridge.haversine_km(MIAMI_LAT, MIAMI_LNG, MIAMI_LAT, MIAMI_LNG)
        assert d == pytest.approx(0.0, abs=1e-9)

    def test_miami_to_coral_gables(self):
        d = GeoBridge.haversine_km(MIAMI_LAT, MIAMI_LNG, CORAL_GABLES_LAT, CORAL_GABLES_LNG)
        assert 6 < d < 10   # roughly 8km

    def test_miami_to_paris(self):
        d = GeoBridge.haversine_km(MIAMI_LAT, MIAMI_LNG, PARIS_LAT, PARIS_LNG)
        assert d > 7000    # intercontinental

    def test_symmetry(self):
        d1 = GeoBridge.haversine_km(MIAMI_LAT, MIAMI_LNG, CORAL_GABLES_LAT, CORAL_GABLES_LNG)
        d2 = GeoBridge.haversine_km(CORAL_GABLES_LAT, CORAL_GABLES_LNG, MIAMI_LAT, MIAMI_LNG)
        assert d1 == pytest.approx(d2, rel=1e-9)

    def test_1km_north(self):
        # 0.009° ≈ 1km
        d = GeoBridge.haversine_km(25.0, -80.0, 25.009, -80.0)
        assert 0.9 < d < 1.1


# ---------------------------------------------------------------------------
# Grid cell computation
# ---------------------------------------------------------------------------

class TestGridCell:
    def test_deterministic(self):
        c1 = GeoBridge._grid_cell(MIAMI_LAT, MIAMI_LNG)
        c2 = GeoBridge._grid_cell(MIAMI_LAT, MIAMI_LNG)
        assert c1 == c2

    def test_format(self):
        cell = GeoBridge._grid_cell(25.7617, -80.1918)
        parts = cell.split(":")
        assert len(parts) == 2
        int(parts[0])   # must be parseable as int
        int(parts[1])

    def test_nearby_points_same_cell(self):
        # Two points 50m apart should share a cell at 0.01° resolution
        c1 = GeoBridge._grid_cell(25.7617, -80.1918)
        c2 = GeoBridge._grid_cell(25.7617 + 0.0004, -80.1918)
        assert c1 == c2

    def test_different_area_different_cell(self):
        c_miami = GeoBridge._grid_cell(MIAMI_LAT, MIAMI_LNG)
        c_paris = GeoBridge._grid_cell(PARIS_LAT, PARIS_LNG)
        assert c_miami != c_paris


# ---------------------------------------------------------------------------
# Nearby cells
# ---------------------------------------------------------------------------

class TestNearbyCells:
    def test_size(self):
        bridge = make_bridge()
        cells = bridge._nearby_cells(MIAMI_LAT, MIAMI_LNG, radius=2)
        # 5x5 grid = 25 cells
        assert len(cells) == 25

    def test_center_included(self):
        bridge = make_bridge()
        center = GeoBridge._grid_cell(MIAMI_LAT, MIAMI_LNG)
        nearby = bridge._nearby_cells(MIAMI_LAT, MIAMI_LNG, radius=2)
        assert center in nearby

    def test_radius_1(self):
        bridge = make_bridge()
        cells = bridge._nearby_cells(MIAMI_LAT, MIAMI_LNG, radius=1)
        assert len(cells) == 9   # 3x3


# ---------------------------------------------------------------------------
# GPS extraction
# ---------------------------------------------------------------------------

class TestGPSExtraction:
    def test_direct_fields(self):
        row = {"task_lat": 25.7617, "task_lng": -80.1918}
        lat, lng = GeoBridge._extract_gps(row)
        assert lat == pytest.approx(25.7617)
        assert lng == pytest.approx(-80.1918)

    def test_evidence_data_gps_nested(self):
        row = {
            "evidence_data": {"gps": {"lat": 25.7617, "lng": -80.1918}}
        }
        lat, lng = GeoBridge._extract_gps(row)
        assert lat == pytest.approx(25.7617)
        assert lng == pytest.approx(-80.1918)

    def test_evidence_data_gps_json_string(self):
        import json
        row = {
            "evidence_data": json.dumps({"gps": {"lat": 25.7617, "lng": -80.1918}})
        }
        lat, lng = GeoBridge._extract_gps(row)
        assert lat == pytest.approx(25.7617)

    def test_evidence_data_flat(self):
        row = {"evidence_data": {"latitude": 25.7617, "longitude": -80.1918}}
        lat, lng = GeoBridge._extract_gps(row)
        assert lat == pytest.approx(25.7617)

    def test_metadata_field(self):
        row = {"metadata": {"latitude": 25.7617, "longitude": -80.1918}}
        lat, lng = GeoBridge._extract_gps(row)
        assert lat == pytest.approx(25.7617)

    def test_no_gps(self):
        row = {"worker_wallet": "0xabc", "task_id": "t1"}
        lat, lng = GeoBridge._extract_gps(row)
        assert lat is None
        assert lng is None

    def test_gps_latitude_alt_key(self):
        row = {"evidence_data": {"gps": {"latitude": 25.7617, "longitude": -80.1918}}}
        lat, lng = GeoBridge._extract_gps(row)
        assert lat == pytest.approx(25.7617)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

class TestIngestion:
    def test_ingest_single_record(self):
        bridge = make_bridge()
        rec = make_record()
        n = bridge.ingest_records([rec])
        assert n == 1
        assert "w1" in bridge._state

    def test_ingest_multiple_workers(self):
        bridge = make_bridge()
        records = [make_record(worker_id=f"w{i}", task_id=f"t{i}") for i in range(5)]
        bridge.ingest_records(records)
        assert len(bridge._state) == 5

    def test_ingest_raw_basic(self):
        bridge = make_bridge()
        rows = [{
            "worker_wallet": "0xabc",
            "task_id": "t1",
            "evidence_type": "photo",
            "status": "completed",
            "evidence_data": {"gps": {"lat": MIAMI_LAT, "lng": MIAMI_LNG}},
            "completed_at": "2026-04-03T02:00:00Z",
        }]
        n = bridge.ingest_raw(rows)
        assert n == 1
        assert "0xabc" in bridge._state

    def test_ingest_raw_missing_worker_skipped(self):
        bridge = make_bridge()
        rows = [{"task_id": "t1", "status": "completed"}]
        n = bridge.ingest_raw(rows)
        assert n == 0

    def test_ingest_raw_malformed_graceful(self):
        bridge = make_bridge()
        rows = [{"worker_wallet": "w1", "task_id": "t1", "status": "completed"},
                None,
                {"worker_wallet": "w2", "task_id": "t2", "status": "completed"}]
        # Should not raise, should process valid rows
        try:
            bridge.ingest_raw(rows)
        except Exception:
            pytest.fail("ingest_raw raised on malformed input")

    def test_completed_task_builds_territory(self):
        bridge = make_bridge()
        rec = make_record(task_lat=MIAMI_LAT, task_lng=MIAMI_LNG, event_type="completed")
        bridge.ingest_records([rec])
        state = bridge._state["w1"]
        assert len(state.territory_cells) == 1
        assert state.physical_completions == 1

    def test_digital_task_no_territory(self):
        bridge = make_bridge()
        rec = make_record(task_type="text_response", event_type="completed")
        bridge.ingest_records([rec])
        state = bridge._state["w1"]
        # No territory recorded for digital tasks
        assert state.physical_completions == 0

    def test_active_hours_recorded(self):
        bridge = make_bridge()
        for h in [9, 10, 11, 14]:
            bridge.ingest_records([make_record(task_hour=h, task_id=f"t{h}")])
        state = bridge._state["w1"]
        assert 9 in state.active_hours
        assert 14 in state.active_hours

    def test_last_known_location_from_completion(self):
        bridge = make_bridge()
        rec = make_record(task_lat=MIAMI_LAT, task_lng=MIAMI_LNG, event_type="completed")
        bridge.ingest_records([rec])
        state = bridge._state["w1"]
        assert state.last_known_lat == pytest.approx(MIAMI_LAT)
        assert state.last_known_lng == pytest.approx(MIAMI_LNG)

    def test_acceptance_with_worker_location_records_distance(self):
        bridge = make_bridge()
        rec = make_record(
            event_type="accepted",
            task_lat=MIAMI_LAT, task_lng=MIAMI_LNG,
            worker_lat=CORAL_GABLES_LAT, worker_lng=CORAL_GABLES_LNG,
        )
        bridge.ingest_records([rec])
        state = bridge._state["w1"]
        assert len(state.accepted_distances) == 1
        assert state.accepted_distances[0] > 0


# ---------------------------------------------------------------------------
# Sub-signal: haversine score
# ---------------------------------------------------------------------------

class TestHaversineScore:
    def test_same_location_score_1(self):
        bridge = make_bridge()
        state = bridge._state["w1"]
        state.last_known_lat = MIAMI_LAT
        state.last_known_lng = MIAMI_LNG
        score, dist = bridge._haversine_score("w1", MIAMI_LAT, MIAMI_LNG)
        assert score == pytest.approx(1.0, abs=0.001)
        assert dist == pytest.approx(0.0, abs=0.001)

    def test_unknown_location_neutral(self):
        bridge = make_bridge()
        score, dist = bridge._haversine_score("w1", MIAMI_LAT, MIAMI_LNG)
        assert score == pytest.approx(0.5)
        assert dist is None

    def test_8km_low_score(self):
        bridge = make_bridge()
        state = bridge._state["w1"]
        state.last_known_lat = MIAMI_LAT
        state.last_known_lng = MIAMI_LNG
        score, dist = bridge._haversine_score("w1", CORAL_GABLES_LAT, CORAL_GABLES_LNG)
        # ~8km → exp(-8/10) ≈ 0.45
        assert 0.3 < score < 0.6

    def test_far_distance_near_zero(self):
        bridge = make_bridge()
        state = bridge._state["w1"]
        state.last_known_lat = MIAMI_LAT
        state.last_known_lng = MIAMI_LNG
        score, dist = bridge._haversine_score("w1", PARIS_LAT, PARIS_LNG)
        assert score < 0.01   # intercontinental → essentially zero
        assert dist > 7000

    def test_score_bounded_0_1(self):
        bridge = make_bridge()
        state = bridge._state["w1"]
        state.last_known_lat = MIAMI_LAT
        state.last_known_lng = MIAMI_LNG
        for test_lat, test_lng in [(25.7617, -80.1918), (48.85, 2.35), (35.0, 139.0)]:
            score, _ = bridge._haversine_score("w1", test_lat, test_lng)
            assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Sub-signal: territory score
# ---------------------------------------------------------------------------

class TestTerritoryScore:
    def test_no_history_neutral(self):
        bridge = make_bridge()
        score = bridge._territory_score("w1", MIAMI_LAT, MIAMI_LNG)
        assert score == pytest.approx(0.5)

    def test_territory_player_high_score(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=5)
        score = bridge._territory_score("w1", MIAMI_LAT, MIAMI_LNG)
        assert score >= 0.7

    def test_no_nearby_completions_low_score(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=15)
        # Task in Paris — no history there
        score = bridge._territory_score("w1", PARIS_LAT, PARIS_LNG)
        assert score < 0.5

    def test_some_presence_mid_score(self):
        bridge = make_bridge()
        # Only 2 completions near task location (below TERRITORY_MIN_COMPLETIONS=3)
        for i in range(2):
            rec = make_record(worker_id="w1", task_id=f"t{i}",
                              task_lat=MIAMI_LAT + i * 0.001, task_lng=MIAMI_LNG)
            bridge.ingest_records([rec])
        score = bridge._territory_score("w1", MIAMI_LAT, MIAMI_LNG)
        assert 0.5 <= score < 0.7

    def test_score_bounded(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=20)
        score = bridge._territory_score("w1", MIAMI_LAT, MIAMI_LNG)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Sub-signal: commute willingness
# ---------------------------------------------------------------------------

class TestCommuteScore:
    def test_insufficient_events_neutral(self):
        bridge = make_bridge()
        bridge._state["w1"].accepted_distances = [5.0] * 3   # < MIN_DISTANCE_EVENTS
        score = bridge._commute_score("w1")
        assert score == pytest.approx(0.5)

    def test_high_travel_worker(self):
        bridge = make_bridge()
        bridge._state["w1"].accepted_distances = [12.0, 15.0, 10.0, 18.0, 14.0, 11.0]
        score = bridge._commute_score("w1")
        assert score > 0.7   # avg ~13km vs 5km median → high

    def test_hyperlocal_worker(self):
        bridge = make_bridge()
        bridge._state["w1"].accepted_distances = [1.0, 0.5, 1.2, 0.8, 0.7, 0.6]
        score = bridge._commute_score("w1")
        assert score < 0.3   # avg ~0.8km vs 5km median → very low

    def test_market_median_worker(self):
        bridge = make_bridge()
        # avg = 5km = market median → score ≈ 0.5
        bridge._state["w1"].accepted_distances = [5.0] * 6
        score = bridge._commute_score("w1")
        assert score == pytest.approx(0.5)

    def test_score_bounded(self):
        bridge = make_bridge()
        bridge._state["w1"].accepted_distances = [100.0] * 10
        score = bridge._commute_score("w1")
        assert score <= 1.0


# ---------------------------------------------------------------------------
# Sub-signal: temporal
# ---------------------------------------------------------------------------

class TestTemporalScore:
    def test_no_data_neutral(self):
        bridge = make_bridge()
        score = bridge._temporal_score("w1", task_hour=10)
        assert score == pytest.approx(0.5)

    def test_no_task_hour_neutral(self):
        bridge = make_bridge()
        bridge._state["w1"].active_hours = [9, 10, 11, 12]
        score = bridge._temporal_score("w1", task_hour=None)
        assert score == pytest.approx(0.5)

    def test_worker_active_at_task_hour(self):
        bridge = make_bridge()
        bridge._state["w1"].active_hours = [9, 10, 11, 10, 10, 9, 11]
        score = bridge._temporal_score("w1", task_hour=10)
        assert score > 0.7   # All hours within ±3 of 10

    def test_worker_inactive_at_task_hour(self):
        bridge = make_bridge()
        # Worker only active at night (22-23), task at midday (12)
        bridge._state["w1"].active_hours = [22, 23, 22, 23, 22, 23, 22, 23]
        score = bridge._temporal_score("w1", task_hour=12)
        assert score < 0.3

    def test_wraparound_midnight(self):
        # Hours 23 and 0 should be close (diff = 1)
        bridge = make_bridge()
        bridge._state["w1"].active_hours = [23, 23, 23, 23, 23]
        score = bridge._temporal_score("w1", task_hour=0)
        assert score > 0.5   # 23-0 = 1 hour diff → within window


# ---------------------------------------------------------------------------
# Main signal()
# ---------------------------------------------------------------------------

class TestSignal:
    def test_digital_task_zero_bonus(self):
        bridge = make_bridge()
        for task_type in DIGITAL_TASK_TYPES:
            sig = bridge.signal("w1", MIAMI_LAT, MIAMI_LNG, task_type)
            assert sig.geo_bonus == pytest.approx(0.0), f"Expected 0.0 for {task_type}"
            assert sig.is_physical_task is False

    def test_physical_types_activate_signal(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=5)
        for task_type in PHYSICAL_TASK_TYPES:
            sig = bridge.signal("w1", MIAMI_LAT, MIAMI_LNG, task_type)
            assert sig.is_physical_task is True

    def test_no_task_location_neutral(self):
        bridge = make_bridge()
        sig = bridge.signal("w1", None, None, "photo")
        assert sig.geo_bonus == pytest.approx(0.0)
        assert sig.confidence == pytest.approx(0.0)

    def test_unknown_worker_neutral(self):
        bridge = make_bridge()
        sig = bridge.signal("unknown_worker", MIAMI_LAT, MIAMI_LNG, "photo")
        assert sig.geo_bonus == pytest.approx(0.0)   # neutral score → 0 bonus

    def test_nearby_worker_positive_bonus(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=5)
        sig = bridge.signal("w1", MIAMI_LAT, MIAMI_LNG, "photo")
        assert sig.geo_bonus > 0.0

    def test_far_worker_negative_bonus(self):
        bridge = make_bridge()
        # Worker known to be in Paris
        bridge._state["w_paris"].last_known_lat = PARIS_LAT
        bridge._state["w_paris"].last_known_lng = PARIS_LNG
        sig = bridge.signal("w_paris", MIAMI_LAT, MIAMI_LNG, "photo")
        assert sig.geo_bonus < 0.0   # Far away → below neutral

    def test_bonus_bounded_by_max(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=20)
        sig = bridge.signal("w1", MIAMI_LAT, MIAMI_LNG, "photo", task_hour=10)
        assert abs(sig.geo_bonus) <= MAX_GEO_BONUS

    def test_result_fields_complete(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=5)
        sig = bridge.signal("w1", MIAMI_LAT, MIAMI_LNG, "photo")
        assert sig.worker_id == "w1"
        assert sig.task_type == "photo"
        assert sig.is_physical_task is True
        assert isinstance(sig.reason, str) and len(sig.reason) > 0
        assert 0.0 <= sig.haversine_score <= 1.0
        assert 0.0 <= sig.territory_score <= 1.0
        assert 0.0 <= sig.commute_score <= 1.0
        assert 0.0 <= sig.temporal_score <= 1.0
        assert 0.0 <= sig.geo_score <= 1.0

    def test_to_dict_serializable(self):
        bridge = make_bridge()
        sig = bridge.signal("w1", MIAMI_LAT, MIAMI_LNG, "photo_geo")
        d = sig.to_dict()
        assert isinstance(d, dict)
        assert "geo_bonus" in d
        assert "geo_score" in d
        assert "distance_km" in d

    def test_geo_score_weights_sum_to_1(self):
        total = HAVERSINE_WEIGHT + TERRITORY_WEIGHT + COMMUTE_WEIGHT + TEMPORAL_WEIGHT
        assert total == pytest.approx(1.0)

    def test_photo_geo_type_activates(self):
        bridge = make_bridge()
        sig = bridge.signal("w1", MIAMI_LAT, MIAMI_LNG, "photo_geo")
        assert sig.is_physical_task is True

    def test_task_hour_affects_score(self):
        bridge = make_bridge()
        # Worker active at 10am
        bridge._state["w1"].last_known_lat = MIAMI_LAT
        bridge._state["w1"].last_known_lng = MIAMI_LNG
        bridge._state["w1"].active_hours = [10] * 10

        sig_match = bridge.signal("w1", MIAMI_LAT, MIAMI_LNG, "photo", task_hour=10)
        sig_mismatch = bridge.signal("w1", MIAMI_LAT, MIAMI_LNG, "photo", task_hour=22)
        assert sig_match.temporal_score > sig_mismatch.temporal_score


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------

class TestLeaderboard:
    def test_returns_ordered_by_bonus(self):
        bridge = make_bridge()
        # Worker A: close to Miami
        populate_worker(bridge, "w_close", MIAMI_LAT, MIAMI_LNG, n=5)
        # Worker B: far (Paris)
        bridge._state["w_far"].last_known_lat = PARIS_LAT
        bridge._state["w_far"].last_known_lng = PARIS_LNG

        lb = bridge.geo_leaderboard(MIAMI_LAT, MIAMI_LNG, task_type="photo", top_n=10)
        assert len(lb) >= 2
        # Close worker should rank first
        assert lb[0]["worker_id"] == "w_close"

    def test_top_n_respected(self):
        bridge = make_bridge()
        for i in range(8):
            populate_worker(bridge, f"w{i}", MIAMI_LAT + i * 0.01, MIAMI_LNG, n=3)
        lb = bridge.geo_leaderboard(MIAMI_LAT, MIAMI_LNG, task_type="photo", top_n=5)
        assert len(lb) <= 5

    def test_digital_task_all_zero_bonus(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=5)
        populate_worker(bridge, "w2", PARIS_LAT, PARIS_LNG, n=5)
        lb = bridge.geo_leaderboard(MIAMI_LAT, MIAMI_LNG, task_type="text_response")
        for entry in lb:
            assert entry["geo_bonus"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Territory map
# ---------------------------------------------------------------------------

class TestTerritoryMap:
    def test_unknown_worker(self):
        bridge = make_bridge()
        result = bridge.worker_territory_map("unknown")
        assert result["worker_id"] == "unknown"
        assert result["cells"] == {}
        assert result["physical_completions"] == 0

    def test_worker_with_completions(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=5)
        result = bridge.worker_territory_map("w1")
        assert result["physical_completions"] == 5
        assert len(result["cells"]) >= 1
        assert result["last_known_lat"] is not None


# ---------------------------------------------------------------------------
# Summary & health
# ---------------------------------------------------------------------------

class TestSummary:
    def test_empty_bridge(self):
        bridge = make_bridge()
        summary = bridge.geo_summary()
        assert summary["total_workers"] == 0
        assert summary["total_records_ingested"] == 0
        assert summary["signal"] == "Signal #21 — Geo Proximity"

    def test_after_ingestion(self):
        bridge = make_bridge()
        populate_worker(bridge, "w1", MIAMI_LAT, MIAMI_LNG, n=5)
        populate_worker(bridge, "w2", PARIS_LAT, PARIS_LNG, n=3)
        summary = bridge.geo_summary()
        assert summary["total_workers"] == 2
        assert summary["workers_with_history"] == 2
        assert summary["workers_with_location"] == 2

    def test_health_alias(self):
        bridge = make_bridge()
        assert bridge.health() == bridge.geo_summary()

    def test_version_present(self):
        bridge = make_bridge()
        summary = bridge.geo_summary()
        assert "version" in summary
        assert summary["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_ingest_zero_records(self):
        bridge = make_bridge()
        n = bridge.ingest_records([])
        assert n == 0

    def test_ingest_raw_empty(self):
        bridge = make_bridge()
        n = bridge.ingest_raw([])
        assert n == 0

    def test_physical_task_types_set(self):
        assert "photo" in PHYSICAL_TASK_TYPES
        assert "photo_geo" in PHYSICAL_TASK_TYPES
        assert "video" in PHYSICAL_TASK_TYPES
        assert "measurement" in PHYSICAL_TASK_TYPES
        assert "text_response" not in PHYSICAL_TASK_TYPES

    def test_digital_task_types_set(self):
        assert "text_response" in DIGITAL_TASK_TYPES
        assert "document" in DIGITAL_TASK_TYPES
        assert "screenshot" in DIGITAL_TASK_TYPES
        assert "photo" not in DIGITAL_TASK_TYPES

    def test_max_geo_bonus_positive(self):
        assert MAX_GEO_BONUS > 0.0
        assert MAX_GEO_BONUS <= 0.15   # Reasonable cap

    def test_many_workers_same_location(self):
        bridge = make_bridge()
        for i in range(20):
            populate_worker(bridge, f"w{i}", MIAMI_LAT, MIAMI_LNG, n=3)
        # Should not raise
        lb = bridge.geo_leaderboard(MIAMI_LAT, MIAMI_LNG, task_type="photo")
        assert len(lb) <= 10

    def test_ingesting_same_task_twice(self):
        bridge = make_bridge()
        rec = make_record()
        bridge.ingest_records([rec, rec])   # duplicate
        # Should handle gracefully — just doubles the data
        state = bridge._state["w1"]
        assert state.physical_completions == 2  # counted twice

    def test_raw_row_with_alternative_id_fields(self):
        bridge = make_bridge()
        rows = [{
            "worker_id": "0xdef",   # alternative to worker_wallet
            "id": "t1",             # alternative to task_id
            "evidence_type": "photo",
            "status": "completed",
        }]
        n = bridge.ingest_raw(rows)
        assert n == 1
        assert "0xdef" in bridge._state

    def test_latitude_zero_treated_as_no_data(self):
        """lat=0/lng=0 is valid (Gulf of Guinea) — we should NOT treat as None."""
        row = {"worker_wallet": "w1", "task_id": "t1", "task_lat": 0.0, "task_lng": 0.0}
        lat, lng = GeoBridge._extract_gps(row)
        # 0.0 is a valid coordinate — it should be returned
        assert lat == 0.0
        assert lng == 0.0

    def test_record_count_tracks_correctly(self):
        bridge = make_bridge()
        records = [make_record(worker_id="w1", task_id=f"t{i}") for i in range(7)]
        bridge.ingest_records(records)
        assert bridge._record_count == 7
