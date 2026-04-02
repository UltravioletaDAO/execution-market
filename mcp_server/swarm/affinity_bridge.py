"""
AffinityBridge — Server-Side Intrinsic Motivation Intelligence

Module #67 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's TaskAffinityEngine (Signal #20).
Syncs worker task lifecycle events from EM's Supabase tables and builds
behavioral motivation profiles without requiring direct AutoJob dependency.

The bridge translates EM's task history format into the four behavioral
fingerprints that Signal #20 measures:

1. Acceptance Velocity — assigned_at vs first status change
2. Completion Eagerness — actual duration vs expected duration
3. Voluntary Escalation — complexity ordering within a worker's task history
4. Temporal Clustering — hour-of-day distribution of completions

Key capabilities:
  1. Sync from Supabase `task_assignments` + `tasks` tables
  2. Compute affinity signals per (worker, category) pair
  3. Category affinity leaderboard
  4. Worker's top affinity categories
  5. Routing signal: affinity_bonus for enrich_agents()
  6. Health monitoring and persistence

Design note: This module operates independently from AutoJob. It implements
the same algorithms directly, avoiding the inter-process dependency that
would be needed to import AutoJob modules.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("em.swarm.affinity_bridge")

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Constants (mirrors AutoJob's TaskAffinityEngine)
# ---------------------------------------------------------------------------

VERSION = "1.0.0"

MIN_OBSERVATIONS = 3
MATURE_THRESHOLD = 15
NEUTRAL_PRIOR = 0.5
MAX_AFFINITY_BONUS = 0.06

VELOCITY_WEIGHT = 0.30
EAGERNESS_WEIGHT = 0.30
ESCALATION_WEIGHT = 0.25
TEMPORAL_WEIGHT = 0.15

TEMPORAL_BINS = 6  # 4-hour blocks


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AffinityRecord:
    """A task lifecycle record in EM format."""
    worker_id: str
    task_id: str
    category: str
    assigned_at: Optional[float] = None
    first_action_at: Optional[float] = None
    estimated_seconds: Optional[float] = None
    completed_at: Optional[float] = None
    complexity_score: float = 1.0


@dataclass
class _CategoryState:
    """Per-worker, per-category behavioral state."""
    acceptance_times: list = field(default_factory=list)
    completion_ratios: list = field(default_factory=list)
    complexity_sequence: list = field(default_factory=list)
    completion_hours: list = field(default_factory=list)


@dataclass
class AffinitySignalResult:
    """Signal #20 output for a (worker, category) pair."""
    worker_id: str
    category: str
    affinity_score: float
    affinity_bonus: float
    confidence: float
    observation_count: int
    velocity_score: float
    eagerness_score: float
    escalation_rate: float
    temporal_score: float
    computed_at: str

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "category": self.category,
            "affinity_score": self.affinity_score,
            "affinity_bonus": self.affinity_bonus,
            "confidence": self.confidence,
            "observation_count": self.observation_count,
            "velocity_score": self.velocity_score,
            "eagerness_score": self.eagerness_score,
            "escalation_rate": self.escalation_rate,
            "temporal_score": self.temporal_score,
            "computed_at": self.computed_at,
        }


# ---------------------------------------------------------------------------
# Core engine (server-side implementation of Signal #20)
# ---------------------------------------------------------------------------

class AffinityBridge:
    """
    Module #67 — Server-side intrinsic motivation bridge.

    Syncs worker behavioral data from EM Supabase tables and computes
    Signal #20 (TaskAffinityEngine) server-side.
    """

    def __init__(self) -> None:
        # worker_id → category → _CategoryState
        self._state: dict[str, dict[str, _CategoryState]] = defaultdict(
            lambda: defaultdict(_CategoryState)
        )
        self._last_sync: float = 0.0
        self._record_count: int = 0
        self._worker_count: int = 0

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_records(self, records: list[AffinityRecord]) -> int:
        """Ingest a batch of AffinityRecord objects."""
        count = 0
        for rec in records:
            self._ingest_one(rec)
            count += 1
        self._worker_count = len(self._state)
        self._record_count += count
        logger.debug(f"AffinityBridge: ingested {count} records")
        return count

    def ingest_raw(self, rows: list[dict]) -> int:
        """
        Ingest from raw Supabase task_assignments JOIN tasks rows.

        Expected fields:
            worker_wallet (str): worker identifier
            task_id (str): task identifier
            category (str): task category
            assigned_at (str|None): ISO timestamp
            accepted_at (str|None): ISO timestamp (first worker action)
            completed_at (str|None): ISO timestamp
            bounty_usd (float|None): used to estimate complexity
            time_estimate_seconds (float|None): platform time estimate
        """
        records = []
        for row in rows:
            try:
                rec = self._row_to_record(row)
                if rec:
                    records.append(rec)
            except Exception as e:
                logger.warning(f"AffinityBridge: skipping malformed row: {e}")
        return self.ingest_records(records)

    def _row_to_record(self, row: dict) -> Optional[AffinityRecord]:
        """Convert a raw Supabase row to AffinityRecord."""
        worker_id = row.get("worker_wallet") or row.get("worker_id")
        task_id = row.get("task_id") or row.get("id")
        category = row.get("category", "other")

        if not worker_id or not task_id:
            return None

        def _ts(key: str) -> Optional[float]:
            val = row.get(key)
            if not val:
                return None
            try:
                if isinstance(val, (int, float)):
                    return float(val)
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                return dt.timestamp()
            except Exception:
                return None

        assigned_at = _ts("assigned_at")
        first_action_at = _ts("accepted_at") or _ts("first_action_at")
        completed_at = _ts("completed_at")
        estimated_seconds = row.get("time_estimate_seconds") or row.get("estimated_seconds")

        # Infer complexity from bounty (log-normalized relative to $10 baseline)
        bounty = row.get("bounty_usd") or row.get("reward_usd") or 5.0
        if bounty > 0:
            complexity = max(0.5, min(3.0, math.log(bounty + 1) / math.log(11)))
        else:
            complexity = 1.0

        return AffinityRecord(
            worker_id=worker_id,
            task_id=task_id,
            category=category,
            assigned_at=assigned_at,
            first_action_at=first_action_at,
            estimated_seconds=float(estimated_seconds) if estimated_seconds else None,
            completed_at=completed_at,
            complexity_score=complexity,
        )

    def _ingest_one(self, rec: AffinityRecord) -> None:
        cs = self._state[rec.worker_id][rec.category]

        # Acceptance velocity
        if rec.assigned_at and rec.first_action_at:
            accept_secs = max(0.0, rec.first_action_at - rec.assigned_at)
            cs.acceptance_times.append(accept_secs)

        # Completion eagerness
        if (rec.estimated_seconds and rec.estimated_seconds > 0
                and rec.completed_at):
            start = rec.first_action_at or rec.assigned_at
            if start:
                actual_secs = max(1.0, rec.completed_at - start)
                cs.completion_ratios.append(actual_secs / rec.estimated_seconds)

        # Escalation
        cs.complexity_sequence.append(rec.complexity_score)

        # Temporal
        if rec.completed_at:
            dt = datetime.fromtimestamp(rec.completed_at, tz=UTC)
            cs.completion_hours.append(dt.hour)

    # ------------------------------------------------------------------
    # Signal computation
    # ------------------------------------------------------------------

    def signal(
        self,
        worker_id: str,
        category: str | None = None,
    ) -> AffinitySignalResult:
        """Compute Signal #20 for a worker, optionally in a category."""
        if category is None:
            return self._aggregate_signal(worker_id)
        return self._category_signal(worker_id, category)

    def routing_signal(
        self,
        worker_id: str,
        category: str | None = None,
    ) -> dict:
        """
        Simplified routing signal for enrich_agents() integration.
        Returns {'affinity_bonus': float, 'affinity_score': float}.
        """
        sig = self.signal(worker_id, category=category)
        return {
            "affinity_bonus": sig.affinity_bonus,
            "affinity_score": sig.affinity_score,
            "confidence": sig.confidence,
            "observation_count": sig.observation_count,
        }

    def _category_signal(self, worker_id: str, category: str) -> AffinitySignalResult:
        ts = datetime.now(tz=UTC).isoformat()

        if worker_id not in self._state or category not in self._state[worker_id]:
            return AffinitySignalResult(
                worker_id=worker_id,
                category=category,
                affinity_score=NEUTRAL_PRIOR,
                affinity_bonus=0.0,
                confidence=0.0,
                observation_count=0,
                velocity_score=0.5,
                eagerness_score=0.5,
                escalation_rate=0.0,
                temporal_score=0.5,
                computed_at=ts,
            )

        cs = self._state[worker_id][category]
        obs = max(len(cs.complexity_sequence), len(cs.acceptance_times))
        confidence = self._confidence(obs)

        velocity = self._compute_velocity(cs)
        eagerness = self._compute_eagerness(cs)
        escalation_rate = self._compute_escalation(cs)
        escalation_score = min(1.0, escalation_rate * 2.0)
        temporal = self._compute_temporal(cs)

        raw_score = (
            velocity * VELOCITY_WEIGHT
            + eagerness * EAGERNESS_WEIGHT
            + escalation_score * ESCALATION_WEIGHT
            + temporal * TEMPORAL_WEIGHT
        )
        affinity_score = raw_score * confidence + NEUTRAL_PRIOR * (1.0 - confidence)
        affinity_score = max(0.0, min(1.0, affinity_score))

        deviation = affinity_score - NEUTRAL_PRIOR
        affinity_bonus = deviation * (MAX_AFFINITY_BONUS / 0.5)
        affinity_bonus = max(-MAX_AFFINITY_BONUS, min(MAX_AFFINITY_BONUS, affinity_bonus))

        return AffinitySignalResult(
            worker_id=worker_id,
            category=category,
            affinity_score=affinity_score,
            affinity_bonus=affinity_bonus,
            confidence=confidence,
            observation_count=obs,
            velocity_score=velocity,
            eagerness_score=eagerness,
            escalation_rate=escalation_rate,
            temporal_score=temporal,
            computed_at=ts,
        )

    def _aggregate_signal(self, worker_id: str) -> AffinitySignalResult:
        if worker_id not in self._state or not self._state[worker_id]:
            return AffinitySignalResult(
                worker_id=worker_id,
                category="*",
                affinity_score=NEUTRAL_PRIOR,
                affinity_bonus=0.0,
                confidence=0.0,
                observation_count=0,
                velocity_score=0.5,
                eagerness_score=0.5,
                escalation_rate=0.0,
                temporal_score=0.5,
                computed_at=datetime.now(tz=UTC).isoformat(),
            )
        sigs = [self._category_signal(worker_id, c) for c in self._state[worker_id]]
        total_obs = sum(s.observation_count for s in sigs)
        if total_obs == 0:
            affinity_score = NEUTRAL_PRIOR
            confidence = 0.0
        else:
            affinity_score = sum(s.affinity_score * s.observation_count for s in sigs) / total_obs
            confidence = sum(s.confidence * s.observation_count for s in sigs) / total_obs

        deviation = affinity_score - NEUTRAL_PRIOR
        bonus = deviation * (MAX_AFFINITY_BONUS / 0.5)
        bonus = max(-MAX_AFFINITY_BONUS, min(MAX_AFFINITY_BONUS, bonus))

        return AffinitySignalResult(
            worker_id=worker_id,
            category="*",
            affinity_score=affinity_score,
            affinity_bonus=bonus,
            confidence=confidence,
            observation_count=total_obs,
            velocity_score=sum(s.velocity_score for s in sigs) / max(1, len(sigs)),
            eagerness_score=sum(s.eagerness_score for s in sigs) / max(1, len(sigs)),
            escalation_rate=sum(s.escalation_rate for s in sigs) / max(1, len(sigs)),
            temporal_score=sum(s.temporal_score for s in sigs) / max(1, len(sigs)),
            computed_at=datetime.now(tz=UTC).isoformat(),
        )

    # ------------------------------------------------------------------
    # Sub-signal computations
    # ------------------------------------------------------------------

    def _confidence(self, obs: int) -> float:
        if obs <= 0:
            return 0.0
        return min(1.0, math.log(obs + 1) / math.log(MATURE_THRESHOLD + 1))

    def _compute_velocity(self, cs: _CategoryState) -> float:
        times = cs.acceptance_times
        if len(times) < 2:
            return 0.5
        median = sorted(times)[len(times) // 2]
        if median <= 0:
            return 0.5
        recent = sum(times[-3:]) / min(3, len(times))
        return max(0.0, min(1.0, 1.0 - recent / median / 2.0))

    def _compute_eagerness(self, cs: _CategoryState) -> float:
        ratios = cs.completion_ratios
        if not ratios:
            return 0.5
        avg_ratio = sum(ratios) / len(ratios)
        return max(0.0, min(1.0, 1.0 - avg_ratio / 2.0))

    def _compute_escalation(self, cs: _CategoryState) -> float:
        seq = cs.complexity_sequence
        if len(seq) < 2:
            return 0.0
        escalations = sum(1 for i in range(1, len(seq)) if seq[i] > seq[i - 1])
        return escalations / (len(seq) - 1)

    def _compute_temporal(self, cs: _CategoryState) -> float:
        hours = cs.completion_hours
        if len(hours) < 3:
            return 0.5
        bins = [0] * TEMPORAL_BINS
        for h in hours:
            bins[h // 4] += 1
        total = sum(bins)
        probs = [b / total for b in bins if b > 0]
        entropy = -sum(p * math.log(p) for p in probs)
        max_entropy = math.log(TEMPORAL_BINS)
        if max_entropy == 0:
            return 0.5
        return max(0.0, min(1.0, 1.0 - entropy / max_entropy))

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def category_leaderboard(
        self,
        category: str,
        top_n: int = 10,
    ) -> list[dict]:
        """Workers ranked by affinity for a specific category."""
        results = []
        for worker_id in self._state:
            if category in self._state[worker_id]:
                sig = self._category_signal(worker_id, category)
                results.append(sig.to_dict())
        results.sort(key=lambda x: x["affinity_score"], reverse=True)
        return results[:top_n]

    def worker_top_categories(
        self,
        worker_id: str,
        top_n: int = 5,
    ) -> list[dict]:
        """Return a worker's top categories by affinity."""
        if worker_id not in self._state:
            return []
        results = [
            self._category_signal(worker_id, cat).to_dict()
            for cat in self._state[worker_id]
        ]
        results.sort(key=lambda x: x["affinity_score"], reverse=True)
        return results[:top_n]

    def summary(self) -> dict:
        """Engine health and stats."""
        total_events = sum(
            len(cs.complexity_sequence)
            for worker_data in self._state.values()
            for cs in worker_data.values()
        )
        categories: set[str] = set()
        for worker_data in self._state.values():
            categories.update(worker_data.keys())
        return {
            "module": "AffinityBridge",
            "version": VERSION,
            "signal": "#20",
            "worker_count": len(self._state),
            "record_count": total_events,
            "categories": sorted(categories),
            "last_sync": self._last_sync,
        }

    def health(self) -> dict:
        s = self.summary()
        status = "healthy" if s["worker_count"] >= 1 else "degraded"
        return {
            "status": status,
            "module": "AffinityBridge",
            "signal": "#20",
            "workers": s["worker_count"],
            "records": s["record_count"],
            "categories": s["category_count"] if "category_count" in s else len(s["categories"]),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Persist state to JSON file."""
        payload: dict = {
            "version": VERSION,
            "last_sync": self._last_sync,
            "workers": {},
        }
        for worker_id, categories in self._state.items():
            payload["workers"][worker_id] = {}
            for cat, cs in categories.items():
                payload["workers"][worker_id][cat] = {
                    "acceptance_times": cs.acceptance_times,
                    "completion_ratios": cs.completion_ratios,
                    "complexity_sequence": cs.complexity_sequence,
                    "completion_hours": cs.completion_hours,
                }
        import pathlib
        pathlib.Path(path).write_text(json.dumps(payload, indent=2))
        logger.info(f"AffinityBridge saved to {path}")

    def load(self, path: str) -> None:
        """Load state from JSON file (in-place)."""
        import pathlib
        data = json.loads(pathlib.Path(path).read_text())
        self._last_sync = data.get("last_sync", 0.0)
        for worker_id, categories in data.get("workers", {}).items():
            for cat, cs_data in categories.items():
                cs = self._state[worker_id][cat]
                cs.acceptance_times = cs_data.get("acceptance_times", [])
                cs.completion_ratios = cs_data.get("completion_ratios", [])
                cs.complexity_sequence = cs_data.get("complexity_sequence", [])
                cs.completion_hours = cs_data.get("completion_hours", [])
        self._worker_count = len(self._state)
        logger.info(f"AffinityBridge loaded from {path}")
