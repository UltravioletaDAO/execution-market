from __future__ import annotations
"""
ClusterBridge — Server-Side Multi-Task Batch Intelligence

Module #78 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's TaskClusterEngine (Signal #31).
Detects clusters of related tasks (spatial, categorical, temporal) and
produces routing bonuses that favor batching multiple tasks to the same
worker — reducing overhead, travel time, and coordination cost.

The Island Problem
==================

Signals #1-30 optimize each task-worker match independently. But tasks
cluster naturally:

  Task A: "Photo storefront at 123 Main St"   → $3.00
  Task B: "Verify signage at 125 Main St"     → $2.50
  Task C: "Check parking at 130 Main St"      → $2.00

Without cluster intelligence: three workers, three trips, $7.50 overhead.
With cluster intelligence: one worker, one trip, $7.50 earned efficiently.

The worker is happier (more earnings/hour). The agent is happier (faster
completion). The platform is happier (lower cost per task).

The Architecture
================

ClusterBridge operates in two phases:

**Phase 1: Cluster Detection**
DBSCAN-inspired density clustering across spatial, categorical, and
temporal dimensions. Spatial clusters take priority.

**Phase 2: Batch Signal**
For each worker-task pair, compute bonus based on:
1. Active task in same cluster → strongest bonus
2. Proximity to cluster centroid → distance-decayed bonus
3. Batch completion → bonus for completing full clusters
4. Category coherence → bonus for matching cluster theme

Integration with SwarmCoordinator:
    signal = coordinator.cluster_bridge.signal(
        worker_id="0xABC",
        task_id="task_123",
    )
    # signal.cluster_bonus → routing adjustment
    # signal.cluster_id → "sc_1"
    # signal.batch_tasks → ["task_a", "task_b"]
    # signal.estimated_savings → 0.35

Author: Clawd (Dream Session, April 4 2026 — 4AM)
"""

import json
import logging
import math
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("swarm.cluster_bridge")


# ===========================================================================
# Constants
# ===========================================================================

EARTH_RADIUS_KM = 6371.0

DEFAULT_SPATIAL_RADIUS_KM = 2.0
DEFAULT_TEMPORAL_WINDOW_HOURS = 48.0
DEFAULT_MIN_CLUSTER_SIZE = 2
DEFAULT_MAX_CLUSTER_SIZE = 8

MAX_ACTIVE_TASK_BONUS = 0.10
MAX_PROXIMITY_BONUS = 0.06
MAX_BATCH_COMPLETION_BONUS = 0.04
MAX_CATEGORY_COHERENCE_BONUS = 0.03
MAX_TOTAL_BONUS = 0.12

MIN_CLUSTER_CONFIDENCE = 0.3
MATURE_CLUSTER_SIZE = 4

BASE_OVERHEAD_PER_TASK = 0.15
BATCH_OVERHEAD_REDUCTION = 0.60

TASK_STALE_HOURS = 72.0
ASSIGNMENT_STALE_HOURS = 48.0


# ===========================================================================
# Configuration
# ===========================================================================

@dataclass
class ClusterBridgeConfig:
    """Configuration for ClusterBridge."""

    spatial_radius_km: float = DEFAULT_SPATIAL_RADIUS_KM
    temporal_window_hours: float = DEFAULT_TEMPORAL_WINDOW_HOURS
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE
    max_cluster_size: int = DEFAULT_MAX_CLUSTER_SIZE

    active_task_bonus: float = MAX_ACTIVE_TASK_BONUS
    proximity_bonus: float = MAX_PROXIMITY_BONUS
    batch_completion_bonus: float = MAX_BATCH_COMPLETION_BONUS
    category_coherence_bonus: float = MAX_CATEGORY_COHERENCE_BONUS
    max_total_bonus: float = MAX_TOTAL_BONUS

    task_stale_hours: float = TASK_STALE_HOURS
    assignment_stale_hours: float = ASSIGNMENT_STALE_HOURS

    def validate(self) -> list[str]:
        errors = []
        if self.spatial_radius_km <= 0:
            errors.append("spatial_radius_km must be positive")
        if self.min_cluster_size < 2:
            errors.append("min_cluster_size must be >= 2")
        if self.max_cluster_size < self.min_cluster_size:
            errors.append("max_cluster_size must be >= min_cluster_size")
        if self.temporal_window_hours <= 0:
            errors.append("temporal_window_hours must be positive")
        return errors


# ===========================================================================
# Data Types
# ===========================================================================

@dataclass
class BridgeTaskRecord:
    """Task registered for cluster analysis."""
    task_id: str
    title: str = ""
    category: str = "general"
    lat: float | None = None
    lng: float | None = None
    bounty_usd: float = 0.0
    deadline_hours: float = 24.0
    evidence_type: str = ""
    registered_at: float = 0.0
    assigned_to: str | None = None
    assigned_at: float = 0.0
    completed: bool = False

    def has_location(self) -> bool:
        return (
            self.lat is not None and self.lng is not None
            and -90.0 <= self.lat <= 90.0
            and -180.0 <= self.lng <= 180.0
        )

    @property
    def is_physical(self) -> bool:
        physical_categories = {
            "physical_verification", "field_work", "delivery",
            "photo_verification", "site_inspection", "in_person",
        }
        physical_evidence = {"photo", "photo_geo", "video"}
        return (
            self.category in physical_categories
            or self.evidence_type in physical_evidence
            or self.has_location()
        )


@dataclass
class BridgeCluster:
    """A detected task cluster."""
    cluster_id: str
    task_ids: list[str]
    centroid_lat: float | None = None
    centroid_lng: float | None = None
    dominant_category: str = "mixed"
    total_bounty_usd: float = 0.0
    avg_deadline_hours: float = 24.0
    cluster_type: str = "spatial"
    coherence: float = 0.0
    created_at: float = 0.0
    assigned_workers: dict[str, list[str]] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.task_ids)

    @property
    def is_fully_assigned(self) -> bool:
        assigned = set()
        for tasks in self.assigned_workers.values():
            assigned.update(tasks)
        return assigned == set(self.task_ids)

    def unassigned_tasks(self) -> list[str]:
        assigned = set()
        for tasks in self.assigned_workers.values():
            assigned.update(tasks)
        return [t for t in self.task_ids if t not in assigned]

    def worker_tasks(self, worker_id: str) -> list[str]:
        return self.assigned_workers.get(worker_id, [])


@dataclass
class BridgeClusterSignal:
    """Cluster signal output."""
    cluster_bonus: float = 0.0
    cluster_id: str | None = None
    cluster_size: int = 0
    batch_tasks: list[str] = field(default_factory=list)
    has_active_task_in_cluster: bool = False
    distance_to_centroid_km: float | None = None
    estimated_savings: float = 0.0
    batch_value_usd: float = 0.0
    confidence: float = 0.0
    cluster_type: str = "none"
    components: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            k: v for k, v in asdict(self).items()
            if v is not None and v != 0.0 and v != [] and v != {} and v != "none"
        }


@dataclass
class BridgeClusterHealth:
    """Bridge health metrics."""
    total_tasks: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    total_clusters: int = 0
    active_clusters: int = 0
    avg_cluster_size: float = 0.0
    batch_assignments: int = 0
    total_savings_estimated: float = 0.0
    last_detection_at: float = 0.0
    bridge_ok: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


# ===========================================================================
# Helpers
# ===========================================================================

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in km."""
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def _compute_centroid(tasks: list[BridgeTaskRecord]) -> tuple[float | None, float | None]:
    located = [t for t in tasks if t.has_location()]
    if not located:
        return None, None
    avg_lat = sum(t.lat for t in located) / len(located)
    avg_lng = sum(t.lng for t in located) / len(located)
    return avg_lat, avg_lng


def _category_mode(tasks: list[BridgeTaskRecord]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for t in tasks:
        counts[t.category] += 1
    if not counts:
        return "general"
    return max(counts, key=counts.get)


def _cluster_coherence(tasks: list[BridgeTaskRecord], cluster_type: str) -> float:
    if len(tasks) < 2:
        return 0.0

    dominant = _category_mode(tasks)
    cat_fraction = sum(1 for t in tasks if t.category == dominant) / len(tasks)

    spatial_coherence = 0.5
    located = [t for t in tasks if t.has_location()]
    if len(located) >= 2:
        max_dist = 0.0
        for i in range(len(located)):
            for j in range(i + 1, len(located)):
                d = _haversine_km(located[i].lat, located[i].lng, located[j].lat, located[j].lng)
                max_dist = max(max_dist, d)
        spatial_coherence = 1.0 / (1.0 + max_dist) if max_dist > 0 else 1.0

    deadlines = [t.deadline_hours for t in tasks if t.deadline_hours > 0]
    temporal_coherence = 0.5
    if len(deadlines) >= 2:
        spread = max(deadlines) - min(deadlines)
        temporal_coherence = 1.0 / (1.0 + spread / 24.0)

    if cluster_type == "spatial":
        return 0.5 * spatial_coherence + 0.3 * cat_fraction + 0.2 * temporal_coherence
    elif cluster_type == "categorical":
        return 0.5 * cat_fraction + 0.3 * spatial_coherence + 0.2 * temporal_coherence
    elif cluster_type == "temporal":
        return 0.5 * temporal_coherence + 0.3 * cat_fraction + 0.2 * spatial_coherence
    else:
        return (spatial_coherence + cat_fraction + temporal_coherence) / 3.0


# ===========================================================================
# Main Bridge
# ===========================================================================

class ClusterBridge:
    """
    Module #78: Server-side multi-task batch intelligence for the
    KK V2 Swarm coordinator.
    """

    def __init__(self, config: ClusterBridgeConfig | None = None):
        self.config = config or ClusterBridgeConfig()
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Invalid ClusterBridgeConfig: {'; '.join(errors)}")

        self._tasks: dict[str, BridgeTaskRecord] = {}
        self._clusters: dict[str, BridgeCluster] = {}
        self._worker_locations: dict[str, tuple[float, float]] = {}
        self._worker_active_tasks: dict[str, set[str]] = defaultdict(set)

        self._cluster_counter = 0
        self._batch_assignments = 0
        self._last_detection_at = 0.0
        self._total_savings = 0.0

        logger.info(
            "ClusterBridge initialized (Module #78): radius=%.1fkm, "
            "min_size=%d, max_size=%d",
            self.config.spatial_radius_km,
            self.config.min_cluster_size,
            self.config.max_cluster_size,
        )

    # ─── Task Lifecycle ───────────────────────────────────────────────────

    def register_task(self, task: dict) -> BridgeTaskRecord:
        """Register a task from EM API or Supabase."""
        task_id = task.get("id") or task.get("task_id", "")
        if not task_id:
            raise ValueError("Task must have an 'id'")

        lat = task.get("lat") or task.get("location_lat")
        lng = task.get("lng") or task.get("location_lng")
        for coord_ref in [lat, lng]:
            pass
        if isinstance(lat, str):
            try: lat = float(lat)
            except: lat = None
        if isinstance(lng, str):
            try: lng = float(lng)
            except: lng = None

        record = BridgeTaskRecord(
            task_id=task_id,
            title=task.get("title", ""),
            category=task.get("category", "general"),
            lat=lat, lng=lng,
            bounty_usd=float(task.get("bounty_usd", 0)),
            deadline_hours=float(task.get("deadline_hours", 24)),
            evidence_type=task.get("evidence_type", ""),
            registered_at=time.time(),
        )
        self._tasks[task_id] = record

        active = [t for t in self._tasks.values() if not t.completed]
        if len(active) >= self.config.min_cluster_size:
            self.detect_clusters()

        return record

    def sync_from_supabase(self, rows: list[dict]) -> int:
        """Bulk sync tasks from Supabase query results."""
        count = 0
        for row in rows:
            task_id = row.get("id") or row.get("task_id", "")
            if not task_id:
                continue
            self.register_task(row)
            if row.get("worker_wallet") or row.get("assigned_to"):
                worker = row.get("worker_wallet") or row.get("assigned_to")
                self.assign_task(task_id, worker)
            if row.get("status") in ("completed", "approved"):
                self.complete_task(task_id)
            count += 1
        logger.info("Synced %d tasks from Supabase", count)
        return count

    def assign_task(self, task_id: str, worker_id: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].assigned_to = worker_id
            self._tasks[task_id].assigned_at = time.time()
            self._worker_active_tasks[worker_id].add(task_id)

            task = self._tasks[task_id]
            if task.has_location():
                self._worker_locations[worker_id] = (task.lat, task.lng)

            for cluster in self._clusters.values():
                if task_id in cluster.task_ids:
                    if worker_id not in cluster.assigned_workers:
                        cluster.assigned_workers[worker_id] = []
                    if task_id not in cluster.assigned_workers[worker_id]:
                        cluster.assigned_workers[worker_id].append(task_id)
                    if len(cluster.assigned_workers[worker_id]) >= 2:
                        self._batch_assignments += 1

    def complete_task(self, task_id: str, quality: float = 0.8) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].completed = True
            worker = self._tasks[task_id].assigned_to
            if worker and task_id in self._worker_active_tasks.get(worker, set()):
                self._worker_active_tasks[worker].discard(task_id)

    def update_worker_location(self, worker_id: str, lat: float, lng: float) -> None:
        self._worker_locations[worker_id] = (lat, lng)

    # ─── Cluster Detection ────────────────────────────────────────────────

    def detect_clusters(self) -> list[BridgeCluster]:
        self._prune_stale()

        active = [t for t in self._tasks.values() if not t.completed]
        if len(active) < self.config.min_cluster_size:
            self._clusters = {}
            return []

        spatial = self._cluster_spatial(active)
        claimed = set()
        for c in spatial:
            claimed.update(c.task_ids)

        remaining = [t for t in active if t.task_id not in claimed]
        categorical = self._cluster_categorical(remaining)
        for c in categorical:
            claimed.update(c.task_ids)

        remaining2 = [t for t in active if t.task_id not in claimed]
        temporal = self._cluster_temporal(remaining2)

        all_clusters = spatial + categorical + temporal
        self._clusters = {c.cluster_id: c for c in all_clusters}
        self._last_detection_at = time.time()

        logger.info(
            "Detected %d clusters (%d spatial, %d cat, %d temporal) from %d tasks",
            len(all_clusters), len(spatial), len(categorical), len(temporal), len(active),
        )
        return all_clusters

    def _cluster_spatial(self, tasks: list[BridgeTaskRecord]) -> list[BridgeCluster]:
        located = [t for t in tasks if t.has_location()]
        if len(located) < self.config.min_cluster_size:
            return []

        clusters = []
        used = set()
        radius = self.config.spatial_radius_km
        located.sort(key=lambda t: t.registered_at)

        for seed in located:
            if seed.task_id in used:
                continue
            nearby = [seed]
            for candidate in located:
                if candidate.task_id == seed.task_id or candidate.task_id in used:
                    continue
                dist = _haversine_km(seed.lat, seed.lng, candidate.lat, candidate.lng)
                if dist <= radius:
                    nearby.append(candidate)

            if len(nearby) < self.config.min_cluster_size:
                continue

            nearby = nearby[:self.config.max_cluster_size]
            for t in nearby:
                used.add(t.task_id)

            self._cluster_counter += 1
            centroid_lat, centroid_lng = _compute_centroid(nearby)
            cluster = BridgeCluster(
                cluster_id=f"sc_{self._cluster_counter}",
                task_ids=[t.task_id for t in nearby],
                centroid_lat=centroid_lat, centroid_lng=centroid_lng,
                dominant_category=_category_mode(nearby),
                total_bounty_usd=sum(t.bounty_usd for t in nearby),
                avg_deadline_hours=sum(t.deadline_hours for t in nearby) / len(nearby),
                cluster_type="spatial",
                coherence=_cluster_coherence(nearby, "spatial"),
                created_at=time.time(),
            )
            for t in nearby:
                if t.assigned_to:
                    if t.assigned_to not in cluster.assigned_workers:
                        cluster.assigned_workers[t.assigned_to] = []
                    cluster.assigned_workers[t.assigned_to].append(t.task_id)
            clusters.append(cluster)

        return clusters

    def _cluster_categorical(self, tasks: list[BridgeTaskRecord]) -> list[BridgeCluster]:
        if len(tasks) < self.config.min_cluster_size:
            return []
        by_cat: dict[str, list[BridgeTaskRecord]] = defaultdict(list)
        for t in tasks:
            by_cat[t.category].append(t)

        clusters = []
        for category, group in by_cat.items():
            if len(group) < self.config.min_cluster_size:
                continue
            group = sorted(group, key=lambda t: t.registered_at)[:self.config.max_cluster_size]
            self._cluster_counter += 1
            centroid_lat, centroid_lng = _compute_centroid(group)
            cluster = BridgeCluster(
                cluster_id=f"cc_{self._cluster_counter}",
                task_ids=[t.task_id for t in group],
                centroid_lat=centroid_lat, centroid_lng=centroid_lng,
                dominant_category=category,
                total_bounty_usd=sum(t.bounty_usd for t in group),
                avg_deadline_hours=sum(t.deadline_hours for t in group) / len(group),
                cluster_type="categorical",
                coherence=_cluster_coherence(group, "categorical"),
                created_at=time.time(),
            )
            for t in group:
                if t.assigned_to:
                    if t.assigned_to not in cluster.assigned_workers:
                        cluster.assigned_workers[t.assigned_to] = []
                    cluster.assigned_workers[t.assigned_to].append(t.task_id)
            clusters.append(cluster)

        return clusters

    def _cluster_temporal(self, tasks: list[BridgeTaskRecord]) -> list[BridgeCluster]:
        if len(tasks) < self.config.min_cluster_size:
            return []
        sorted_tasks = sorted(tasks, key=lambda t: t.deadline_hours)
        window = self.config.temporal_window_hours
        clusters = []
        used = set()

        for i, seed in enumerate(sorted_tasks):
            if seed.task_id in used:
                continue
            group = [seed]
            for j in range(i + 1, len(sorted_tasks)):
                candidate = sorted_tasks[j]
                if candidate.task_id in used:
                    continue
                if abs(candidate.deadline_hours - seed.deadline_hours) <= window:
                    group.append(candidate)

            if len(group) < self.config.min_cluster_size:
                continue

            group = group[:self.config.max_cluster_size]
            for t in group:
                used.add(t.task_id)

            self._cluster_counter += 1
            centroid_lat, centroid_lng = _compute_centroid(group)
            cluster = BridgeCluster(
                cluster_id=f"tc_{self._cluster_counter}",
                task_ids=[t.task_id for t in group],
                centroid_lat=centroid_lat, centroid_lng=centroid_lng,
                dominant_category=_category_mode(group),
                total_bounty_usd=sum(t.bounty_usd for t in group),
                avg_deadline_hours=sum(t.deadline_hours for t in group) / len(group),
                cluster_type="temporal",
                coherence=_cluster_coherence(group, "temporal"),
                created_at=time.time(),
            )
            for t in group:
                if t.assigned_to:
                    if t.assigned_to not in cluster.assigned_workers:
                        cluster.assigned_workers[t.assigned_to] = []
                    cluster.assigned_workers[t.assigned_to].append(t.task_id)
            clusters.append(cluster)

        return clusters

    # ─── Signal Computation ───────────────────────────────────────────────

    def signal(
        self,
        worker_id: str,
        task_id: str,
        worker_lat: float | None = None,
        worker_lng: float | None = None,
    ) -> BridgeClusterSignal:
        """Compute cluster routing signal for a worker-task pair."""
        if task_id not in self._tasks:
            return BridgeClusterSignal()

        target_cluster: BridgeCluster | None = None
        for cluster in self._clusters.values():
            if task_id in cluster.task_ids:
                target_cluster = cluster
                break

        if target_cluster is None:
            return BridgeClusterSignal()

        w_lat, w_lng = worker_lat, worker_lng
        if w_lat is None or w_lng is None:
            if worker_id in self._worker_locations:
                w_lat, w_lng = self._worker_locations[worker_id]

        # Component 1: Active task bonus
        active_bonus = 0.0
        worker_cluster_tasks = target_cluster.worker_tasks(worker_id)
        active_in_cluster = [
            tid for tid in worker_cluster_tasks
            if tid in self._tasks and not self._tasks[tid].completed
        ]
        has_active = len(active_in_cluster) > 0
        if has_active:
            active_bonus = min(
                self.config.active_task_bonus,
                self.config.active_task_bonus * (0.6 + 0.4 * min(len(active_in_cluster), 3) / 3),
            )

        # Component 2: Proximity bonus
        proximity_bonus = 0.0
        distance_km: float | None = None
        if (
            not has_active
            and w_lat is not None and w_lng is not None
            and target_cluster.centroid_lat is not None
            and target_cluster.centroid_lng is not None
        ):
            distance_km = _haversine_km(
                w_lat, w_lng,
                target_cluster.centroid_lat, target_cluster.centroid_lng,
            )
            decay = self.config.spatial_radius_km
            proximity_bonus = self.config.proximity_bonus * math.exp(-distance_km / decay)

        # Component 3: Batch completion bonus
        batch_bonus = 0.0
        unassigned = target_cluster.unassigned_tasks()
        if task_id in unassigned:
            remaining_after = len(unassigned) - 1
            if remaining_after == 0 and has_active:
                batch_bonus = self.config.batch_completion_bonus
            elif remaining_after <= 1 and has_active:
                batch_bonus = self.config.batch_completion_bonus * 0.5

        # Component 4: Category coherence bonus
        category_bonus = 0.0
        if target_cluster.dominant_category != "general":
            worker_tasks_all = self._worker_active_tasks.get(worker_id, set())
            match_count = 0
            for tid in worker_tasks_all:
                if tid in self._tasks and self._tasks[tid].category == target_cluster.dominant_category:
                    match_count += 1
            if match_count > 0:
                category_bonus = min(
                    self.config.category_coherence_bonus,
                    self.config.category_coherence_bonus * min(match_count, 3) / 3,
                )

        # Confidence
        confidence = self._compute_confidence(target_cluster)

        # Total
        raw_total = active_bonus + proximity_bonus + batch_bonus + category_bonus
        capped = min(raw_total, self.config.max_total_bonus)
        cluster_bonus = capped * confidence

        # Savings
        estimated_savings = 0.0
        if has_active or proximity_bonus > 0:
            batch_size = len(active_in_cluster) + 1 if has_active else 2
            estimated_savings = (
                (batch_size - 1) / batch_size
                * BATCH_OVERHEAD_REDUCTION
                * BASE_OVERHEAD_PER_TASK
            )

        # Batch tasks
        batch_tasks = []
        if has_active:
            batch_tasks = active_in_cluster + [task_id]
        elif cluster_bonus > 0:
            batch_tasks = [task_id]

        return BridgeClusterSignal(
            cluster_bonus=round(cluster_bonus, 6),
            cluster_id=target_cluster.cluster_id,
            cluster_size=target_cluster.size,
            batch_tasks=batch_tasks,
            has_active_task_in_cluster=has_active,
            distance_to_centroid_km=round(distance_km, 3) if distance_km is not None else None,
            estimated_savings=round(estimated_savings, 4),
            batch_value_usd=round(target_cluster.total_bounty_usd, 2),
            confidence=round(confidence, 4),
            cluster_type=target_cluster.cluster_type,
            components={
                "active_task": round(active_bonus, 6),
                "proximity": round(proximity_bonus, 6),
                "batch_completion": round(batch_bonus, 6),
                "category_coherence": round(category_bonus, 6),
            },
        )

    def _compute_confidence(self, cluster: BridgeCluster) -> float:
        size_conf = min(1.0, cluster.size / MATURE_CLUSTER_SIZE)
        coherence_conf = cluster.coherence
        age_hours = (time.time() - cluster.created_at) / 3600.0
        freshness = 1.0 / (1.0 + age_hours / 24.0)
        confidence = 0.4 * size_conf + 0.4 * coherence_conf + 0.2 * freshness
        return max(MIN_CLUSTER_CONFIDENCE, min(1.0, confidence))

    # ─── Pruning ──────────────────────────────────────────────────────────

    def _prune_stale(self) -> int:
        now = time.time()
        stale_cutoff = now - (self.config.task_stale_hours * 3600)
        pruned = 0

        stale_ids = [
            tid for tid, t in self._tasks.items()
            if t.completed or t.registered_at < stale_cutoff
        ]
        for tid in stale_ids:
            task = self._tasks.pop(tid)
            if task.assigned_to:
                self._worker_active_tasks[task.assigned_to].discard(tid)
            pruned += 1

        for worker_id in list(self._worker_active_tasks.keys()):
            stale = [tid for tid in self._worker_active_tasks[worker_id] if tid not in self._tasks]
            for tid in stale:
                self._worker_active_tasks[worker_id].discard(tid)
            if not self._worker_active_tasks[worker_id]:
                del self._worker_active_tasks[worker_id]

        return pruned

    # ─── Query & Analytics ────────────────────────────────────────────────

    def get_clusters(self) -> list[BridgeCluster]:
        return list(self._clusters.values())

    def get_cluster(self, cluster_id: str) -> BridgeCluster | None:
        return self._clusters.get(cluster_id)

    def get_task_cluster(self, task_id: str) -> BridgeCluster | None:
        for cluster in self._clusters.values():
            if task_id in cluster.task_ids:
                return cluster
        return None

    def batch_opportunities(self, worker_id: str) -> list[dict]:
        opportunities = []
        for cluster in self._clusters.values():
            worker_tasks = cluster.worker_tasks(worker_id)
            active = [
                tid for tid in worker_tasks
                if tid in self._tasks and not self._tasks[tid].completed
            ]
            if not active:
                continue
            unassigned = cluster.unassigned_tasks()
            if not unassigned:
                continue
            for tid in unassigned:
                task = self._tasks.get(tid)
                if task:
                    opportunities.append({
                        "task_id": tid,
                        "cluster_id": cluster.cluster_id,
                        "cluster_type": cluster.cluster_type,
                        "bounty_usd": task.bounty_usd,
                        "category": task.category,
                        "existing_tasks": len(active),
                        "estimated_savings": round(
                            len(active) / (len(active) + 1) * BATCH_OVERHEAD_REDUCTION * BASE_OVERHEAD_PER_TASK, 4),
                    })
        return sorted(opportunities, key=lambda o: o["estimated_savings"], reverse=True)

    def fleet_stats(self) -> dict:
        active_clusters = [c for c in self._clusters.values() if c.unassigned_tasks()]
        batch_workers = set()
        for cluster in self._clusters.values():
            for w, tasks in cluster.assigned_workers.items():
                if len(tasks) >= 2:
                    batch_workers.add(w)

        return {
            "total_clusters": len(self._clusters),
            "active_clusters": len(active_clusters),
            "avg_cluster_size": (
                sum(c.size for c in self._clusters.values()) / len(self._clusters)
                if self._clusters else 0.0
            ),
            "total_batch_value_usd": sum(c.total_bounty_usd for c in self._clusters.values()),
            "batch_workers": len(batch_workers),
            "cluster_types": {
                "spatial": sum(1 for c in self._clusters.values() if c.cluster_type == "spatial"),
                "categorical": sum(1 for c in self._clusters.values() if c.cluster_type == "categorical"),
                "temporal": sum(1 for c in self._clusters.values() if c.cluster_type == "temporal"),
            },
        }

    # ─── Health ───────────────────────────────────────────────────────────

    def health(self) -> BridgeClusterHealth:
        active = [t for t in self._tasks.values() if not t.completed]
        completed = [t for t in self._tasks.values() if t.completed]
        active_clusters = [c for c in self._clusters.values() if c.unassigned_tasks()]
        return BridgeClusterHealth(
            total_tasks=len(self._tasks),
            active_tasks=len(active),
            completed_tasks=len(completed),
            total_clusters=len(self._clusters),
            active_clusters=len(active_clusters),
            avg_cluster_size=(
                sum(c.size for c in self._clusters.values()) / len(self._clusters)
                if self._clusters else 0.0
            ),
            batch_assignments=self._batch_assignments,
            total_savings_estimated=round(self._total_savings, 4),
            last_detection_at=self._last_detection_at,
            bridge_ok=True,
        )

    # ─── Persistence ──────────────────────────────────────────────────────

    def save(self, path: str | Path) -> None:
        state = {
            "version": 1,
            "module": "cluster_bridge",
            "module_number": 78,
            "config": asdict(self.config),
            "tasks": {tid: asdict(t) for tid, t in self._tasks.items()},
            "clusters": {cid: asdict(c) for cid, c in self._clusters.items()},
            "worker_locations": {w: list(loc) for w, loc in self._worker_locations.items()},
            "worker_active_tasks": {w: list(tasks) for w, tasks in self._worker_active_tasks.items()},
            "cluster_counter": self._cluster_counter,
            "batch_assignments": self._batch_assignments,
            "last_detection_at": self._last_detection_at,
            "saved_at": time.time(),
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, default=str))

    @classmethod
    def load(cls, path: str | Path) -> "ClusterBridge":
        path = Path(path)
        data = json.loads(path.read_text())
        config = ClusterBridgeConfig(**data.get("config", {}))
        bridge = cls(config)

        for tid, tdata in data.get("tasks", {}).items():
            bridge._tasks[tid] = BridgeTaskRecord(**tdata)
        for cid, cdata in data.get("clusters", {}).items():
            bridge._clusters[cid] = BridgeCluster(**cdata)
        for w, loc in data.get("worker_locations", {}).items():
            bridge._worker_locations[w] = tuple(loc)
        for w, tasks in data.get("worker_active_tasks", {}).items():
            bridge._worker_active_tasks[w] = set(tasks)

        bridge._cluster_counter = data.get("cluster_counter", 0)
        bridge._batch_assignments = data.get("batch_assignments", 0)
        bridge._last_detection_at = data.get("last_detection_at", 0.0)

        return bridge

    def __repr__(self) -> str:
        h = self.health()
        return (
            f"ClusterBridge(tasks={h.total_tasks}, clusters={h.total_clusters}, "
            f"active={h.active_clusters}, batches={h.batch_assignments})"
        )
