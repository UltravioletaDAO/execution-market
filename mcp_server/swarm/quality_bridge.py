"""
QualityBridge — Server-Side Evidence Quality Intelligence

Module #69 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's EvidenceQualityEngine (Signal #22).
Syncs PHOTINT verification inference records from EM's Supabase tables
and builds evidence quality routing signals without requiring a direct
AutoJob dependency.

Signal #22 asks: "How good will this worker's evidence be?"

All previous signals optimize *who accepts* and *whether they complete*.
Signal #22 optimizes *how well they complete* by predicting evidence quality
based on historical PHOTINT verification history.

Four quality sub-signals:
    1. Historical Quality Score   — Average PHOTINT score across all submissions
    2. Category-Specific Score    — Quality specifically for this task category
    3. EXIF/GPS Compliance        — Metadata integrity for physical tasks
    4. Rejection Rate             — How often evidence was rejected by PHOTINT

Key capabilities:
    1. Sync from Supabase verification_inferences table
    2. Compute quality signal per (worker, task_category, task_type)
    3. Quality leaderboard for a specific task type
    4. Fleet-wide quality analytics
    5. Routing signal: quality_bonus for enrich_agents()
    6. Persistence (save/load)

Sub-signal weights:
    Historical quality: 40%
    Category competence: 35%
    EXIF/GPS compliance: 15%
    Rejection rate: 10%

Bonus bounds:
    Max bonus:   +0.09 (exemplary quality worker on matching task)
    Max penalty: -0.09 (poor quality worker with high rejection rate)

Physical vs Digital split:
    EXIF/GPS sub-signal is physical-only (photo, photo_geo, video, measurement, etc.)
    All other sub-signals apply to both physical and digital tasks.
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

logger = logging.getLogger("em.swarm.quality_bridge")

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Constants (mirrors AutoJob's EvidenceQualityEngine)
# ---------------------------------------------------------------------------

VERSION = "1.0.0"
MODULE_ID = 69
SIGNAL_ID = 22

MAX_EQP_BONUS = 0.09
MIN_EQP_PENALTY = -0.09

# Sub-signal weights
WEIGHT_HISTORICAL = 0.40
WEIGHT_CATEGORY   = 0.35
WEIGHT_EXIF_GPS   = 0.15
WEIGHT_REJECTION  = 0.10

# Quality thresholds
QUALITY_EXEMPLARY = 0.90
QUALITY_GOOD      = 0.80
QUALITY_STANDARD  = 0.65
QUALITY_POOR      = 0.50

COLD_START_MIN_OBS = 3
MATURE_OBS         = 20

# Task types with physical evidence requirements (EXIF/GPS matters)
PHYSICAL_TASK_TYPES = frozenset({
    "photo", "photo_geo", "video", "measurement",
    "signature", "notarized", "receipt",
})

DIGITAL_TASK_TYPES = frozenset({
    "text_response", "document", "screenshot",
    "timestamp_proof",
})


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class QualitySignalResult:
    """Signal #22 output for routing decisions."""

    worker_id: str
    task_category: str
    task_type: str

    quality_bonus: float = 0.0         # Contribution to match_score (±0.09)
    predicted_quality: float = 0.5     # 0-1 prediction of evidence quality
    confidence: float = 0.0            # 0-1, based on observation count

    # Sub-signal breakdown
    historical_score: float = 0.5
    category_score: float = 0.5
    exif_gps_score: float = 0.5
    rejection_score: float = 0.5

    total_obs: int = 0
    category_obs: int = 0
    reason: str = "no_history"

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "task_category": self.task_category,
            "task_type": self.task_type,
            "quality_bonus": self.quality_bonus,
            "predicted_quality": self.predicted_quality,
            "confidence": self.confidence,
            "historical_score": self.historical_score,
            "category_score": self.category_score,
            "exif_gps_score": self.exif_gps_score,
            "rejection_score": self.rejection_score,
            "total_obs": self.total_obs,
            "category_obs": self.category_obs,
            "reason": self.reason,
        }


@dataclass
class _WorkerQualityState:
    """Per-worker accumulated quality state."""

    worker_id: str
    total_obs: int = 0
    total_quality: float = 0.0
    total_approved: int = 0
    total_rejected: int = 0
    total_has_exif: int = 0
    total_has_gps: int = 0
    total_physical: int = 0
    category_quality: dict = field(default_factory=dict)
    last_updated: str = ""

    @property
    def avg_quality(self) -> float:
        return self.total_quality / self.total_obs if self.total_obs else 0.5

    @property
    def rejection_rate(self) -> float:
        return self.total_rejected / self.total_obs if self.total_obs else 0.0

    @property
    def approval_rate(self) -> float:
        return self.total_approved / self.total_obs if self.total_obs else 0.0

    @property
    def exif_compliance(self) -> float:
        return self.total_has_exif / self.total_physical if self.total_physical else 0.5

    @property
    def gps_compliance(self) -> float:
        return self.total_has_gps / self.total_physical if self.total_physical else 0.5

    def category_avg(self, cat: str) -> float:
        entry = self.category_quality.get(cat)
        if not entry or entry.get("obs", 0) == 0:
            return 0.5
        return entry["total_q"] / entry["obs"]

    def category_obs_count(self, cat: str) -> int:
        entry = self.category_quality.get(cat)
        return entry.get("obs", 0) if entry else 0

    def category_rejection_rate(self, cat: str) -> float:
        entry = self.category_quality.get(cat)
        if not entry or entry.get("obs", 0) == 0:
            return 0.0
        return entry.get("rejected", 0) / entry["obs"]


# ---------------------------------------------------------------------------
# QualityBridge
# ---------------------------------------------------------------------------

class QualityBridge:
    """
    Module #69: Server-side evidence quality routing intelligence.

    Mirrors AutoJob's EvidenceQualityEngine (Signal #22) using EM's
    native Supabase schema.
    """

    def __init__(self) -> None:
        self._state: dict[str, _WorkerQualityState] = {}
        self._record_count: int = 0
        self._last_sync: Optional[float] = None
        logger.info("QualityBridge initialized (Module #%d, Signal #%d, v%s)",
                    MODULE_ID, SIGNAL_ID, VERSION)

    # -----------------------------------------------------------------------
    # Data Ingestion
    # -----------------------------------------------------------------------

    def ingest_raw(self, rows: list[dict]) -> int:
        """
        Ingest raw Supabase rows from the verification_inferences table.

        Handles all EM field name variants and GPS extraction formats.
        Returns count of records successfully ingested.
        """
        count = 0
        for row in rows:
            try:
                if self._process_row(row):
                    count += 1
            except Exception as e:
                logger.debug("QualityBridge: skipping row %s: %s",
                             row.get("task_id", "?"), e)
        self._record_count += count
        self._last_sync = time.time()
        logger.debug("QualityBridge.ingest_raw: ingested %d/%d rows", count, len(rows))
        return count

    def _process_row(self, row: dict) -> bool:
        """Process a single Supabase row. Returns True if accepted."""
        # Extract worker identifier
        worker = (
            row.get("worker_wallet")
            or row.get("worker_address")
            or row.get("wallet")
            or ""
        )
        if not worker:
            return False
        worker = worker.lower()

        # Extract quality score (multiple field names in EM schema)
        quality = float(
            row.get("quality_score")
            or row.get("evidence_quality")
            or row.get("score")
            or 0.5
        )
        quality = max(0.0, min(1.0, quality))

        # Category and task type
        category = (
            row.get("task_category")
            or row.get("category")
            or row.get("verification_category")
            or "general"
        )
        task_type = (
            row.get("task_type")
            or row.get("evidence_type")
            or "unknown"
        )

        # Verdict
        verdict = row.get("verdict") or row.get("status") or ""
        approved = verdict in ("approved", "accept", "pass") or row.get("approved") is True
        rejected = verdict in ("rejected", "reject", "fail") or row.get("rejected") is True

        # Metadata (EXIF, GPS)
        metadata = row.get("metadata") or row.get("evidence_data") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except Exception:
                metadata = {}

        has_exif = bool(
            metadata.get("has_exif")
            or metadata.get("exif")
            or row.get("has_exif")
        )
        has_gps = bool(
            metadata.get("has_gps")
            or metadata.get("gps")
            or row.get("has_gps")
            or metadata.get("location")
        )
        is_physical = task_type in PHYSICAL_TASK_TYPES

        # Update worker state
        if worker not in self._state:
            self._state[worker] = _WorkerQualityState(worker_id=worker)

        state = self._state[worker]
        state.total_obs += 1
        state.total_quality += quality

        if approved:
            state.total_approved += 1
        if rejected:
            state.total_rejected += 1

        if is_physical:
            state.total_physical += 1
            if has_exif:
                state.total_has_exif += 1
            if has_gps:
                state.total_has_gps += 1

        cat = category
        if cat not in state.category_quality:
            state.category_quality[cat] = {"obs": 0, "total_q": 0.0, "rejected": 0}
        state.category_quality[cat]["obs"] += 1
        state.category_quality[cat]["total_q"] += quality
        if rejected:
            state.category_quality[cat]["rejected"] += 1

        state.last_updated = datetime.now(UTC).isoformat()
        return True

    def record_outcome(
        self,
        worker_id: str,
        task_id: str,
        task_category: str,
        task_type: str,
        quality_score: float,
        approved: bool = True,
        rejected: bool = False,
        has_exif: bool = False,
        has_gps: bool = False,
    ) -> None:
        """Record a single task outcome directly (without a Supabase row)."""
        row = {
            "worker_wallet": worker_id,
            "task_id": task_id,
            "task_category": task_category,
            "task_type": task_type,
            "quality_score": quality_score,
            "approved": approved,
            "rejected": rejected,
            "metadata": {"has_exif": has_exif, "has_gps": has_gps},
        }
        self._process_row(row)

    # -----------------------------------------------------------------------
    # Signal Computation
    # -----------------------------------------------------------------------

    def signal(
        self,
        worker_id: str,
        task_category: str = "general",
        task_type: str = "photo",
    ) -> QualitySignalResult:
        """
        Compute Signal #22 for a worker on a specific task.

        Returns a QualitySignalResult with quality_bonus (±0.09) and
        predicted_quality (0-1).
        """
        wid = worker_id.lower() if worker_id else ""
        state = self._state.get(wid)
        is_physical = task_type in PHYSICAL_TASK_TYPES

        if not state or state.total_obs == 0:
            return QualitySignalResult(
                worker_id=worker_id,
                task_category=task_category,
                task_type=task_type,
                quality_bonus=0.0,
                predicted_quality=0.5,
                confidence=0.0,
                reason="no_verification_history",
            )

        # Sub-signal 1: Historical Quality (40%)
        hist_q = state.avg_quality
        if hist_q >= QUALITY_EXEMPLARY:
            hist_c = 1.0
        elif hist_q >= QUALITY_GOOD:
            hist_c = 0.75
        elif hist_q >= QUALITY_STANDARD:
            hist_c = 0.50
        elif hist_q >= QUALITY_POOR:
            hist_c = 0.25
        else:
            hist_c = 0.0

        # Sub-signal 2: Category Competence (35%)
        cat_obs = state.category_obs_count(task_category)
        if cat_obs < COLD_START_MIN_OBS:
            cat_c = 0.5  # Neutral cold start
        else:
            cat_q = state.category_avg(task_category)
            if cat_q >= QUALITY_EXEMPLARY:
                cat_c = 1.0
            elif cat_q >= QUALITY_GOOD:
                cat_c = 0.75
            elif cat_q >= QUALITY_STANDARD:
                cat_c = 0.50
            elif cat_q >= QUALITY_POOR:
                cat_c = 0.25
            else:
                cat_c = 0.0

        # Sub-signal 3: EXIF/GPS Compliance (15%)
        if is_physical and state.total_physical >= COLD_START_MIN_OBS:
            exif_gps_c = 0.6 * state.exif_compliance + 0.4 * state.gps_compliance
        else:
            exif_gps_c = 0.5  # Neutral for digital or no physical history

        # Sub-signal 4: Rejection Rate (10%)
        rej = state.rejection_rate
        if rej > 0.30:
            rej_c = 0.0
        elif rej > 0.20:
            rej_c = 0.2
        elif rej > 0.10:
            rej_c = 0.4
        elif rej < 0.05 and state.approval_rate > 0.70:
            rej_c = 0.8
        else:
            rej_c = 0.6

        # Combine
        combined = (
            WEIGHT_HISTORICAL * hist_c
            + WEIGHT_CATEGORY * cat_c
            + WEIGHT_EXIF_GPS * exif_gps_c
            + WEIGHT_REJECTION * rej_c
        )

        raw_bonus = (combined - 0.5) * 2.0 * MAX_EQP_BONUS
        raw_bonus = max(MIN_EQP_PENALTY, min(MAX_EQP_BONUS, raw_bonus))

        # Confidence scaling
        confidence = min(1.0, math.log1p(state.total_obs) / math.log1p(MATURE_OBS))
        quality_bonus = round(raw_bonus * confidence, 4)

        # Predicted quality
        predicted_quality = round(
            0.5 * hist_q + 0.3 * state.category_avg(task_category) + 0.2 * (1 - rej),
            3,
        )

        reason = self._build_reason(state, task_category, is_physical, quality_bonus)

        return QualitySignalResult(
            worker_id=worker_id,
            task_category=task_category,
            task_type=task_type,
            quality_bonus=quality_bonus,
            predicted_quality=predicted_quality,
            confidence=round(confidence, 3),
            historical_score=round(hist_q, 3),
            category_score=round(state.category_avg(task_category), 3),
            exif_gps_score=round(exif_gps_c, 3),
            rejection_score=round(1.0 - rej, 3),
            total_obs=state.total_obs,
            category_obs=cat_obs,
            reason=reason,
        )

    def _build_reason(
        self,
        state: _WorkerQualityState,
        category: str,
        is_physical: bool,
        bonus: float,
    ) -> str:
        parts = []
        avg_q = state.avg_quality
        if avg_q >= QUALITY_EXEMPLARY:
            parts.append(f"exemplary_quality:{avg_q:.2f}")
        elif avg_q >= QUALITY_GOOD:
            parts.append(f"good_quality:{avg_q:.2f}")
        elif avg_q < QUALITY_POOR:
            parts.append(f"poor_quality:{avg_q:.2f}")

        cat_obs = state.category_obs_count(category)
        if cat_obs >= COLD_START_MIN_OBS:
            cat_q = state.category_avg(category)
            if cat_q >= QUALITY_EXEMPLARY:
                parts.append(f"cat_expert:{category}")
            elif cat_q < QUALITY_POOR:
                parts.append(f"cat_weak:{category}")

        if is_physical and state.total_physical >= COLD_START_MIN_OBS:
            if state.exif_compliance >= 0.9:
                parts.append("exif_compliant")
            elif state.exif_compliance < 0.4:
                parts.append("poor_exif")

        rej = state.rejection_rate
        if rej > 0.20:
            parts.append(f"high_rejection:{rej:.0%}")
        elif rej < 0.05 and state.total_obs >= 5:
            parts.append("low_rejection")

        return "|".join(parts) if parts else (
            "quality_bonus" if bonus > 0
            else "quality_penalty" if bonus < 0
            else "standard"
        )

    # -----------------------------------------------------------------------
    # Analytics
    # -----------------------------------------------------------------------

    def quality_leaderboard(
        self,
        task_category: str = "general",
        task_type: str = "photo",
        top_n: int = 20,
    ) -> list[dict]:
        """Workers ranked by predicted quality bonus (descending)."""
        results = []
        for wid in self._state:
            sig = self.signal(wid, task_category, task_type)
            results.append({
                "worker_id": wid,
                "quality_bonus": sig.quality_bonus,
                "predicted_quality": sig.predicted_quality,
                "confidence": sig.confidence,
                "total_obs": sig.total_obs,
                "reason": sig.reason,
            })
        results.sort(key=lambda x: x["quality_bonus"], reverse=True)
        return results[:top_n]

    def worker_quality_profile(self, worker_id: str) -> dict:
        """Detailed quality breakdown for a single worker."""
        wid = worker_id.lower()
        state = self._state.get(wid)
        if not state:
            return {"worker_id": worker_id, "status": "no_history", "total_obs": 0}
        return {
            "worker_id": worker_id,
            "total_obs": state.total_obs,
            "avg_quality": round(state.avg_quality, 3),
            "rejection_rate": round(state.rejection_rate, 3),
            "approval_rate": round(state.approval_rate, 3),
            "exif_compliance": round(state.exif_compliance, 3),
            "gps_compliance": round(state.gps_compliance, 3),
            "total_physical": state.total_physical,
            "category_breakdown": {
                cat: {
                    "obs": v["obs"],
                    "avg_quality": round(v["total_q"] / v["obs"], 3) if v["obs"] else 0.5,
                    "rejection_rate": round(v.get("rejected", 0) / v["obs"], 3) if v["obs"] else 0.0,
                }
                for cat, v in state.category_quality.items()
            },
            "last_updated": state.last_updated,
        }

    def quality_summary(self) -> dict:
        """Fleet-wide quality statistics."""
        if not self._state:
            return {
                "module": "QualityBridge",
                "version": VERSION,
                "signal": f"Signal #{SIGNAL_ID} — Evidence Quality Prediction",
                "total_workers": 0,
                "total_inferences": self._record_count,
            }

        qualities = [s.avg_quality for s in self._state.values() if s.total_obs > 0]
        rej_rates = [s.rejection_rate for s in self._state.values() if s.total_obs > 0]

        exemplary = sum(1 for q in qualities if q >= QUALITY_EXEMPLARY)
        poor = sum(1 for q in qualities if q < QUALITY_POOR)

        return {
            "module": "QualityBridge",
            "version": VERSION,
            "signal": f"Signal #{SIGNAL_ID} — Evidence Quality Prediction",
            "total_workers": len(self._state),
            "total_inferences": self._record_count,
            "avg_fleet_quality": round(statistics.mean(qualities), 3) if qualities else 0.5,
            "avg_rejection_rate": round(statistics.mean(rej_rates), 3) if rej_rates else 0.0,
            "exemplary_workers": exemplary,
            "poor_quality_workers": poor,
            "quality_distribution": {
                "exemplary": exemplary,
                "good": sum(1 for q in qualities if QUALITY_GOOD <= q < QUALITY_EXEMPLARY),
                "standard": sum(1 for q in qualities if QUALITY_STANDARD <= q < QUALITY_GOOD),
                "poor": poor,
            },
            "last_sync": self._last_sync,
            "last_sync_ago_s": round(time.time() - self._last_sync, 1) if self._last_sync else None,
        }

    def health(self) -> dict:
        """Alias for quality_summary for consistency with other bridges."""
        return self.quality_summary()

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Serialize bridge state to JSON."""
        import os
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        data = {
            "version": VERSION,
            "module_id": MODULE_ID,
            "signal_id": SIGNAL_ID,
            "record_count": self._record_count,
            "last_sync": self._last_sync,
            "workers": {
                wid: {
                    "worker_id": s.worker_id,
                    "total_obs": s.total_obs,
                    "total_quality": s.total_quality,
                    "total_approved": s.total_approved,
                    "total_rejected": s.total_rejected,
                    "total_has_exif": s.total_has_exif,
                    "total_has_gps": s.total_has_gps,
                    "total_physical": s.total_physical,
                    "category_quality": s.category_quality,
                    "last_updated": s.last_updated,
                }
                for wid, s in self._state.items()
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.debug("QualityBridge saved %d workers to %s", len(self._state), path)

    @classmethod
    def load(cls, path: str) -> "QualityBridge":
        """Load bridge state from JSON."""
        bridge = cls()
        try:
            with open(path) as f:
                data = json.load(f)
        except FileNotFoundError:
            return bridge
        bridge._record_count = data.get("record_count", 0)
        bridge._last_sync = data.get("last_sync")
        for wid, sd in data.get("workers", {}).items():
            state = _WorkerQualityState(
                worker_id=sd["worker_id"],
                total_obs=sd["total_obs"],
                total_quality=sd["total_quality"],
                total_approved=sd["total_approved"],
                total_rejected=sd["total_rejected"],
                total_has_exif=sd.get("total_has_exif", 0),
                total_has_gps=sd.get("total_has_gps", 0),
                total_physical=sd.get("total_physical", 0),
                category_quality=sd.get("category_quality", {}),
                last_updated=sd.get("last_updated", ""),
            )
            bridge._state[wid] = state
        logger.debug("QualityBridge loaded %d workers from %s", len(bridge._state), path)
        return bridge
