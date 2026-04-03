"""
GeoBridge — Server-Side Geo Proximity Intelligence

Module #68 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's GeoProximityEngine (Signal #21).
Syncs worker task lifecycle events from EM's Supabase tables and builds
spatial routing intelligence without requiring direct AutoJob dependency.

Signal #21 adds the dimension that Signals #1-20 completely missed:
**Physical tasks require physical proximity.**

Four geo sub-signals:
    1. Haversine Proximity — exponential decay curve from task location
    2. Territory Intelligence — historical completions in nearby 1km² grid cells
    3. Commute Willingness — worker's proven travel range vs market median
    4. Temporal Clustering — active hours overlap with task time window

Key capabilities:
    1. Sync from Supabase task_assignments + evidence metadata
    2. Compute geo signal per (worker, task_location) pair
    3. Geographic leaderboard (who covers which areas)
    4. Territory maps per worker
    5. Routing signal: geo_bonus for enrich_agents()
    6. Health monitoring and persistence

Design note: Digital tasks (text_response, document, screenshot, timestamp_proof)
return geo_bonus=0.0 — geography is irrelevant for remote work. Only physical
evidence types (photo, photo_geo, video, measurement, signature, receipt, notarized)
activate the geo routing penalty/bonus.

GPS data extraction:
    EM stores GPS coords in evidence.evidence_data as:
        {"gps": {"lat": float, "lng": float, "accuracy": float}}
    or at top-level as:
        {"latitude": float, "longitude": float}
    This bridge handles both formats.
"""

from __future__ import annotations

import json
import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("em.swarm.geo_bridge")

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Constants (mirrors AutoJob's GeoProximityEngine)
# ---------------------------------------------------------------------------

VERSION = "1.0.0"

EARTH_RADIUS_KM = 6371.0
DECAY_CONSTANT_KM = 10.0          # Distance at which proximity score ≈ 0.37
NEAR_THRESHOLD_KM = 1.0           # Within 1km = full territory score
MAX_USEFUL_DISTANCE_KM = 100.0    # Beyond 100km = effectively no bonus

GRID_CELL_SIZE_DEG = 0.01         # ~1.1km per cell at equator
TERRITORY_MIN_COMPLETIONS = 3     # Need ≥3 completions to call it "territory"
MIN_DISTANCE_EVENTS = 5           # Need ≥5 events before applying commute signal

MAX_GEO_BONUS = 0.08              # Maximum geo contribution to match_score

# Weights for combining sub-signals (must sum to 1.0)
HAVERSINE_WEIGHT = 0.50
TERRITORY_WEIGHT = 0.30
COMMUTE_WEIGHT = 0.10
TEMPORAL_WEIGHT = 0.10

# Task types requiring physical presence (geo signal active)
PHYSICAL_TASK_TYPES = frozenset({
    "photo", "photo_geo", "video", "measurement",
    "signature", "notarized", "receipt",
})

# Task types where location is irrelevant (geo_bonus = 0.0)
DIGITAL_TASK_TYPES = frozenset({
    "text_response", "document", "screenshot",
    "timestamp_proof",
})


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GeoRecord:
    """A single task event in EM format with geographic data."""
    worker_id: str
    task_id: str
    task_type: str                  # Evidence type: photo, photo_geo, etc.
    event_type: str                 # "accepted", "completed", "abandoned"

    # Task location (from evidence or task metadata)
    task_lat: Optional[float] = None
    task_lng: Optional[float] = None

    # Worker location at time of acceptance (rare in EM, but supported)
    worker_lat: Optional[float] = None
    worker_lng: Optional[float] = None

    # Time metadata
    task_hour: Optional[int] = None    # Hour of day (0-23) task was completed
    timestamp: Optional[float] = None  # Unix timestamp


@dataclass
class GeoSignalResult:
    """Signal #21 output for a (worker, task_location) pair."""
    worker_id: str
    task_lat: Optional[float]
    task_lng: Optional[float]
    task_type: str

    haversine_score: float
    territory_score: float
    commute_score: float
    temporal_score: float

    geo_score: float            # Weighted combination: 0.0–1.0
    geo_bonus: float            # Contribution to match_score (clamped to MAX_GEO_BONUS)
    is_physical_task: bool
    distance_km: Optional[float]
    confidence: float           # 0.0–1.0 (data quality)
    reason: str

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "task_lat": self.task_lat,
            "task_lng": self.task_lng,
            "task_type": self.task_type,
            "haversine_score": round(self.haversine_score, 4),
            "territory_score": round(self.territory_score, 4),
            "commute_score": round(self.commute_score, 4),
            "temporal_score": round(self.temporal_score, 4),
            "geo_score": round(self.geo_score, 4),
            "geo_bonus": round(self.geo_bonus, 4),
            "is_physical_task": self.is_physical_task,
            "distance_km": round(self.distance_km, 2) if self.distance_km is not None else None,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
        }


@dataclass
class _WorkerGeoState:
    """Per-worker geographic history accumulated from EM events."""

    # Grid cells where worker has completed physical tasks: {cell_key: count}
    territory_cells: dict[str, int] = field(default_factory=dict)

    # Distances to completed physical task locations (km)
    accepted_distances: list[float] = field(default_factory=list)

    # Hour-of-day distribution for completed physical tasks
    active_hours: list[int] = field(default_factory=list)

    # Worker's last known location (from acceptance events with worker GPS)
    last_known_lat: Optional[float] = None
    last_known_lng: Optional[float] = None

    # Count of completed physical tasks
    physical_completions: int = 0
    total_events: int = 0


# ---------------------------------------------------------------------------
# Core bridge
# ---------------------------------------------------------------------------

class GeoBridge:
    """
    Module #68 — Server-side geo proximity bridge.

    Syncs worker geographic data from EM Supabase tables and computes
    Signal #21 (GeoProximityEngine) server-side.
    """

    def __init__(self) -> None:
        # worker_id → _WorkerGeoState
        self._state: dict[str, _WorkerGeoState] = defaultdict(_WorkerGeoState)
        self._last_sync: float = 0.0
        self._record_count: int = 0

    # ------------------------------------------------------------------
    # Math helpers
    # ------------------------------------------------------------------

    @staticmethod
    def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Great-circle distance between two points in kilometers.
        Haversine formula — accurate to ~0.3% for distances ≤1000km.
        """
        r = EARTH_RADIUS_KM
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lng2 - lng1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r * c

    @staticmethod
    def _grid_cell(lat: float, lng: float, size: float = GRID_CELL_SIZE_DEG) -> str:
        """Convert coordinates to ~1.1km grid cell key."""
        return f"{int(lat / size)}:{int(lng / size)}"

    def _nearby_cells(self, lat: float, lng: float, radius: int = 2) -> set[str]:
        """All grid cells within radius cells of a point (roughly 5x5 = ~25km²)."""
        cl = int(lat / GRID_CELL_SIZE_DEG)
        cn = int(lng / GRID_CELL_SIZE_DEG)
        return {f"{cl + dl}:{cn + dn}"
                for dl in range(-radius, radius + 1)
                for dn in range(-radius, radius + 1)}

    # ------------------------------------------------------------------
    # GPS extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_gps(row: dict) -> tuple[Optional[float], Optional[float]]:
        """
        Extract GPS coordinates from a raw EM task/assignment row.

        EM stores GPS in multiple places depending on evidence type:
        1. evidence_data.gps.{lat,lng}  — photo_geo evidence
        2. evidence_data.{latitude,longitude}  — some workers use flat format
        3. metadata.{latitude,longitude}  — task-level geo context
        4. task_lat / task_lng  — pre-parsed in some queries
        """
        # Direct fields first (from pre-joined queries)
        if row.get("task_lat") is not None and row.get("task_lng") is not None:
            return float(row["task_lat"]), float(row["task_lng"])

        # evidence_data nested
        ev = row.get("evidence_data") or {}
        if isinstance(ev, str):
            try:
                ev = json.loads(ev)
            except Exception:
                ev = {}

        gps = ev.get("gps")
        if isinstance(gps, dict):
            lat = gps.get("lat") or gps.get("latitude")
            lng = gps.get("lng") or gps.get("longitude")
            if lat is not None and lng is not None:
                return float(lat), float(lng)

        # Flat format in evidence_data
        if ev.get("latitude") is not None:
            return float(ev["latitude"]), float(ev.get("longitude", 0))

        # Task-level metadata
        meta = row.get("metadata") or {}
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        if meta.get("latitude") is not None:
            return float(meta["latitude"]), float(meta.get("longitude", 0))

        return None, None

    @staticmethod
    def _parse_ts(val: Any) -> Optional[float]:
        """Parse ISO timestamp or unix float to seconds."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        try:
            dt = datetime.fromisoformat(str(val).replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_records(self, records: list[GeoRecord]) -> int:
        """Ingest a batch of GeoRecord objects."""
        count = 0
        for rec in records:
            self._ingest_one(rec)
            count += 1
        self._record_count += count
        logger.debug(f"GeoBridge: ingested {count} records")
        return count

    def ingest_raw(self, rows: list[dict]) -> int:
        """
        Ingest from raw Supabase rows (task_assignments JOIN tasks).

        Expected fields:
            worker_wallet (str): worker identifier
            task_id / id (str): task identifier
            evidence_type (str): task type (photo, photo_geo, etc.)
            status (str): 'completed', 'accepted', etc.
            evidence_data (dict|str): JSON with GPS if photo_geo
            assigned_at (str|None): ISO timestamp of assignment
            completed_at (str|None): ISO timestamp of completion
            bounty_usd (float|None): task bounty
        """
        records = []
        for row in rows:
            try:
                rec = self._row_to_record(row)
                if rec:
                    records.append(rec)
            except Exception as e:
                logger.warning(f"GeoBridge: skipping malformed row: {e}")
        return self.ingest_records(records)

    def _row_to_record(self, row: dict) -> Optional[GeoRecord]:
        """Convert raw Supabase row to GeoRecord."""
        worker_id = row.get("worker_wallet") or row.get("worker_id")
        task_id = row.get("task_id") or row.get("id")
        if not worker_id or not task_id:
            return None

        # Determine task type from evidence_type or category
        task_type = (
            row.get("evidence_type")
            or row.get("task_type")
            or row.get("category", "other")
        )

        # Determine event type from status
        status = (row.get("status") or "").lower()
        if status == "completed":
            event_type = "completed"
        elif status in ("accepted", "in_progress"):
            event_type = "accepted"
        elif status in ("cancelled", "expired", "failed"):
            event_type = "abandoned"
        else:
            event_type = "accepted"

        # Extract GPS
        task_lat, task_lng = self._extract_gps(row)

        # Extract task hour from completed_at or assigned_at
        task_hour = None
        completed_ts = self._parse_ts(row.get("completed_at"))
        if completed_ts:
            task_hour = datetime.fromtimestamp(completed_ts, tz=UTC).hour

        return GeoRecord(
            worker_id=worker_id,
            task_id=task_id,
            task_type=task_type,
            event_type=event_type,
            task_lat=task_lat,
            task_lng=task_lng,
            task_hour=task_hour,
            timestamp=completed_ts or self._parse_ts(row.get("assigned_at")),
        )

    def _ingest_one(self, rec: GeoRecord) -> None:
        """Update worker state from a single GeoRecord."""
        state = self._state[rec.worker_id]
        state.total_events += 1

        is_physical = rec.task_type in PHYSICAL_TASK_TYPES

        if rec.event_type == "accepted":
            # Record worker-to-task distance if both locations available
            if (rec.worker_lat is not None and rec.worker_lng is not None
                    and rec.task_lat is not None and rec.task_lng is not None):
                dist = self.haversine_km(
                    rec.worker_lat, rec.worker_lng,
                    rec.task_lat, rec.task_lng
                )
                state.accepted_distances.append(dist)
            # Update last known location
            if rec.worker_lat is not None:
                state.last_known_lat = rec.worker_lat
                state.last_known_lng = rec.worker_lng

        elif rec.event_type == "completed":
            if is_physical:
                state.physical_completions += 1

            if rec.task_lat is not None and rec.task_lng is not None:
                # Build territory map
                cell = self._grid_cell(rec.task_lat, rec.task_lng)
                state.territory_cells[cell] = state.territory_cells.get(cell, 0) + 1

                # If we have a last known location, record the commute distance
                if (state.last_known_lat is not None
                        and len(state.accepted_distances) < MIN_DISTANCE_EVENTS * 3):
                    dist = self.haversine_km(
                        state.last_known_lat, state.last_known_lng,
                        rec.task_lat, rec.task_lng
                    )
                    state.accepted_distances.append(dist)

                # Update last known location from task completion (worker was there)
                if is_physical:
                    state.last_known_lat = rec.task_lat
                    state.last_known_lng = rec.task_lng

            # Record active hour for physical tasks
            if rec.task_hour is not None and is_physical:
                state.active_hours.append(rec.task_hour)

    # ------------------------------------------------------------------
    # Sub-signal computation
    # ------------------------------------------------------------------

    def _haversine_score(
        self, worker_id: str, task_lat: float, task_lng: float
    ) -> tuple[float, Optional[float]]:
        """Proximity score from straight-line distance. Returns (score, dist_km)."""
        state = self._state[worker_id]
        if state.last_known_lat is None:
            return 0.5, None   # Unknown location → neutral

        dist = self.haversine_km(
            state.last_known_lat, state.last_known_lng,
            task_lat, task_lng
        )
        # exp(-dist / 10) decay: 0km→1.0, 1km→0.90, 3km→0.74, 10km→0.37, 50km→0.007
        score = math.exp(-dist / DECAY_CONSTANT_KM)
        return max(0.0, min(1.0, score)), dist

    def _territory_score(self, worker_id: str, task_lat: float, task_lng: float) -> float:
        """Territory score from historical completions near task location."""
        state = self._state[worker_id]
        if not state.territory_cells:
            return 0.5   # No history → neutral

        nearby = self._nearby_cells(task_lat, task_lng, radius=2)
        nearby_count = sum(state.territory_cells.get(c, 0) for c in nearby)
        total = sum(state.territory_cells.values())

        if total == 0:
            return 0.5

        if nearby_count >= TERRITORY_MIN_COMPLETIONS:
            # Solid territory: 0.7–1.0
            score = 0.7 + 0.3 * min(1.0, nearby_count / 10)
        elif nearby_count > 0:
            # Some presence: 0.5–0.7
            score = 0.5 + 0.2 * (nearby_count / TERRITORY_MIN_COMPLETIONS)
        else:
            # No presence; penalize if we have data indicating they work elsewhere
            score = 0.3 if total >= 10 else 0.5

        return max(0.0, min(1.0, score))

    def _commute_score(self, worker_id: str) -> float:
        """Commute willingness: ratio of worker's avg travel to market median (5km)."""
        state = self._state[worker_id]
        dists = state.accepted_distances
        if len(dists) < MIN_DISTANCE_EVENTS:
            return 0.5   # Insufficient data → neutral

        avg = sum(dists) / len(dists)
        market_median = 5.0
        # Workers who travel >10km avg get 1.0; <2.5km avg get 0.25
        score = min(1.0, avg / (market_median * 2))
        return max(0.0, min(1.0, score))

    def _temporal_score(self, worker_id: str, task_hour: Optional[int]) -> float:
        """Temporal overlap: fraction of worker's active hours within ±3h of task hour."""
        state = self._state[worker_id]
        if task_hour is None or not state.active_hours:
            return 0.5

        window = sum(
            1 for h in state.active_hours
            if abs(h - task_hour) <= 3 or abs(h - task_hour) >= 21
        )
        frac = window / len(state.active_hours)
        # Scale: 0.67 overlap → 1.0
        return max(0.0, min(1.0, frac * 1.5))

    # ------------------------------------------------------------------
    # Main signal
    # ------------------------------------------------------------------

    def signal(
        self,
        worker_id: str,
        task_lat: Optional[float],
        task_lng: Optional[float],
        task_type: str,
        task_hour: Optional[int] = None,
    ) -> GeoSignalResult:
        """
        Compute Signal #21 for a (worker, task_location) pair.

        Digital tasks: geo_bonus = 0.0 (geography irrelevant).
        Physical tasks with no location: neutral (0.5) with low confidence.
        """
        is_physical = task_type in PHYSICAL_TASK_TYPES

        if not is_physical:
            return GeoSignalResult(
                worker_id=worker_id,
                task_lat=task_lat, task_lng=task_lng, task_type=task_type,
                haversine_score=0.5, territory_score=0.5,
                commute_score=0.5, temporal_score=0.5,
                geo_score=0.5, geo_bonus=0.0,
                is_physical_task=False, distance_km=None,
                confidence=1.0, reason="Digital task — geo signal not applicable",
            )

        if task_lat is None or task_lng is None:
            return GeoSignalResult(
                worker_id=worker_id,
                task_lat=None, task_lng=None, task_type=task_type,
                haversine_score=0.5, territory_score=0.5,
                commute_score=0.5, temporal_score=0.5,
                geo_score=0.5, geo_bonus=0.0,
                is_physical_task=True, distance_km=None,
                confidence=0.0, reason="Physical task with no location — cannot compute geo",
            )

        haversine_s, dist_km = self._haversine_score(worker_id, task_lat, task_lng)
        territory_s = self._territory_score(worker_id, task_lat, task_lng)
        commute_s = self._commute_score(worker_id)
        temporal_s = self._temporal_score(worker_id, task_hour)

        geo_score = (
            HAVERSINE_WEIGHT * haversine_s
            + TERRITORY_WEIGHT * territory_s
            + COMMUTE_WEIGHT * commute_s
            + TEMPORAL_WEIGHT * temporal_s
        )

        # Bonus: deviation from neutral (0.5), scaled to MAX_GEO_BONUS
        # Score 1.0 → +MAX_GEO_BONUS, Score 0.0 → -MAX_GEO_BONUS, Score 0.5 → 0
        geo_bonus = (geo_score - 0.5) * 2 * MAX_GEO_BONUS
        geo_bonus = max(-MAX_GEO_BONUS, min(MAX_GEO_BONUS, geo_bonus))

        state = self._state[worker_id]
        has_history = bool(state.territory_cells or state.accepted_distances)
        confidence = 0.3 + (0.7 if has_history else 0.0)

        # Build reason string
        if dist_km is not None:
            dist_str = f"{dist_km:.1f}km away"
        else:
            dist_str = "distance unknown"
        territory_str = "territory" if territory_s >= 0.7 else ("some area history" if territory_s > 0.5 else "no area history")
        reason = f"{dist_str}, {territory_str}, geo_score={geo_score:.3f}"

        return GeoSignalResult(
            worker_id=worker_id,
            task_lat=task_lat, task_lng=task_lng, task_type=task_type,
            haversine_score=haversine_s, territory_score=territory_s,
            commute_score=commute_s, temporal_score=temporal_s,
            geo_score=geo_score, geo_bonus=geo_bonus,
            is_physical_task=True, distance_km=dist_km,
            confidence=confidence, reason=reason,
        )

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def geo_leaderboard(
        self,
        task_lat: float,
        task_lng: float,
        task_type: str = "photo",
        task_hour: Optional[int] = None,
        top_n: int = 10,
    ) -> list[dict]:
        """
        Rank all known workers by geo bonus for a specific task location.
        Returns top_n workers sorted by geo_bonus descending.
        """
        results = []
        for worker_id in self._state:
            sig = self.signal(worker_id, task_lat, task_lng, task_type, task_hour)
            results.append(sig.to_dict())
        results.sort(key=lambda x: x["geo_bonus"], reverse=True)
        return results[:top_n]

    def worker_territory_map(self, worker_id: str) -> dict:
        """Return worker's territorial footprint."""
        state = self._state.get(worker_id)
        if not state:
            return {"worker_id": worker_id, "cells": {}, "physical_completions": 0}
        return {
            "worker_id": worker_id,
            "cells": dict(state.territory_cells),
            "physical_completions": state.physical_completions,
            "last_known_lat": state.last_known_lat,
            "last_known_lng": state.last_known_lng,
        }

    def geo_summary(self) -> dict:
        """High-level health stats for the geo bridge."""
        workers_with_history = sum(
            1 for s in self._state.values()
            if s.territory_cells or s.accepted_distances
        )
        workers_with_location = sum(
            1 for s in self._state.values()
            if s.last_known_lat is not None
        )
        return {
            "module": "GeoBridge",
            "version": VERSION,
            "signal": "Signal #21 — Geo Proximity",
            "total_workers": len(self._state),
            "workers_with_history": workers_with_history,
            "workers_with_location": workers_with_location,
            "total_records_ingested": self._record_count,
            "last_sync": self._last_sync,
            "last_sync_ago_s": round(time.time() - self._last_sync, 1) if self._last_sync else None,
        }

    def health(self) -> dict:
        """Alias for geo_summary for consistency with other bridges."""
        return self.geo_summary()
