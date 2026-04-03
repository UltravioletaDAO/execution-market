"""
FPQBridge — Server-Side First-Pass Quality Intelligence

Module #71 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's FirstPassQualityEngine (Signal #24).
Syncs submission history from EM's Supabase task_assignments table and builds
first-pass quality routing signals without requiring a direct AutoJob dependency.

Signal #24 asks: "Does this worker nail tasks on the first submission attempt?"

After 23 signals across 9 dimensions — capability, market fit, temporal availability,
self-optimization, discovery, social trust, motivation, spatial proximity, evidence
quality, and communication — Signal #24 closes with the final efficiency metric:
*submission efficiency*.

A worker who submits perfect evidence on the first try is worth dramatically more
than a worker who requires 4 revision cycles. The final output may be the same
quality, but the agent review overhead, escrow cycles, and delivery delay are
entirely different.

Four first-pass sub-signals:
    1. First-Pass Rate (40%)       — Fraction of tasks approved on first submission
    2. Revision Efficiency (30%)   — 1/(avg_attempts - 0.9) for tasks needing revisions
    3. Rejection Recovery (20%)    — When rejected, how often does worker eventually succeed?
    4. Quality Consistency (10%)   — Low quality variance = reliable, predictable worker

Bonus bounds:
    Max bonus:   +0.06 (100% first-pass rate, high quality consistency)
    Max penalty: -0.06 (0% first-pass rate, high rejection abandonment)

Narrower than Signal #22 (±0.09) and Signal #23 (±0.07) because:
    - Many tasks have submission_count=1 regardless of quality (makes FPR ambiguous)
    - First-pass data is only actionable after ≥6 task observations
    - The bonus should be additive, not dominant

Cold-start safety:
    - Workers with < MIN_OBSERVATIONS (6) are confidence-attenuated
    - Workers with no history return neutral bonus = 0.0
    - Unknown workers return neutral bonus = 0.0

Key capabilities:
    1. full_refresh() — Sync from Supabase task_assignments rows
    2. signal(worker_id) — Compute FPQ routing signal
    3. fpq_leaderboard() — Workers ranked by first-pass quality
    4. fpq_summary() — Fleet-wide FPQ analytics
    5. save/load — JSON state persistence
    6. health() — Status endpoint

Architecture decisions:
    - Full refresh model (matching CommBridge/QualityBridge pattern)
    - Field polymorphism: worker_wallet/worker_address/wallet/worker_id all accepted
    - Outcome normalization: "completed"/"done"/"success" → "approved"
    - Score normalization: 0-100 scale detected and converted to 0-1

Dimension 10: First-Pass Quality
Signal #24 is the 10th routing dimension, closing the 24-signal architecture.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("em.swarm.fpq_bridge")

# ---------------------------------------------------------------------------
# Constants (mirrors AutoJob's FirstPassQualityEngine)
# ---------------------------------------------------------------------------

VERSION = "1.0.0"
MODULE_ID = 71
SIGNAL_ID = 24

MAX_FPQ_BONUS: float = 0.06
MIN_FPQ_PENALTY: float = -0.06

# Sub-signal weights
WEIGHT_FIRST_PASS         = 0.40
WEIGHT_REVISION_EFFICIENCY = 0.30
WEIGHT_REJECTION_RECOVERY  = 0.20
WEIGHT_QUALITY_CONSISTENCY = 0.10

# Revision efficiency constants
REVISION_DECAY_CONSTANT = 0.9
MAX_ATTEMPTS_FLOOR       = 8.0

# Quality consistency normalization
QUALITY_STD_NORMALIZER = 0.3

# Confidence scaling
MIN_OBSERVATIONS = 6


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class FPQSignalResult:
    """Signal #24 output for routing decisions."""

    worker_id: str
    fpq_bonus: float = 0.0       # Contribution to match_score (±0.06)
    confidence: float = 0.0      # 0-1, based on observation count

    # Sub-signal breakdown
    first_pass_rate: float = 0.0
    revision_efficiency: float = 0.0
    rejection_recovery_rate: float = 0.0
    quality_consistency: float = 0.5

    task_count: int = 0
    reason: str = "no_history"

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "fpq_bonus": self.fpq_bonus,
            "confidence": self.confidence,
            "first_pass_rate": self.first_pass_rate,
            "revision_efficiency": self.revision_efficiency,
            "rejection_recovery_rate": self.rejection_recovery_rate,
            "quality_consistency": self.quality_consistency,
            "task_count": self.task_count,
            "reason": self.reason,
        }


@dataclass
class _WorkerFPQState:
    """Per-worker accumulated FPQ state."""

    worker_id: str
    total_tasks: int = 0
    first_pass_count: int = 0
    total_attempts: int = 0
    multi_attempt_tasks: int = 0
    rejection_events: int = 0
    recovery_events: int = 0
    quality_scores: list = field(default_factory=list)

    def first_pass_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.5  # neutral
        return self.first_pass_count / self.total_tasks

    def revision_efficiency(self) -> float:
        if self.multi_attempt_tasks == 0:
            return 1.0  # no revisions = perfect
        avg = min(self.total_attempts / self.total_tasks, MAX_ATTEMPTS_FLOOR)
        raw = 1.0 / (avg - REVISION_DECAY_CONSTANT)
        return min(1.0, raw)

    def rejection_recovery_rate(self) -> float:
        if self.rejection_events == 0:
            return 1.0  # no rejections = perfect
        return self.recovery_events / self.rejection_events

    def quality_consistency(self) -> float:
        if len(self.quality_scores) < 2:
            return 0.5  # neutral
        std_dev = statistics.stdev(self.quality_scores)
        return max(0.0, 1.0 - std_dev / QUALITY_STD_NORMALIZER)


# ---------------------------------------------------------------------------
# FPQBridge
# ---------------------------------------------------------------------------

class FPQBridge:
    """
    Module #71: First-Pass Quality Bridge.

    Server-side Signal #24. Syncs EM submission history and provides
    first-pass quality routing signals for worker selection.
    """

    def __init__(self):
        self._workers: dict[str, _WorkerFPQState] = {}
        self._last_sync_ts: Optional[float] = None
        self._records_processed: int = 0
        logger.info(f"FPQBridge v{VERSION} initialized (Signal #{SIGNAL_ID}, Module #{MODULE_ID})")

    # -----------------------------------------------------------------------
    # Ingestion
    # -----------------------------------------------------------------------

    def full_refresh(self, rows: list[dict]) -> int:
        """
        Full-refresh sync from task_assignments rows.

        Clears existing state and rebuilds from the provided rows.
        Matches the CommBridge/QualityBridge full-refresh pattern.

        Args:
            rows: List of raw Supabase task_assignments dicts.

        Returns:
            Number of valid records processed.
        """
        self._workers.clear()
        count = self._ingest_rows(rows)
        self._last_sync_ts = time.time()
        self._records_processed = count
        logger.info(f"FPQBridge full_refresh: {count}/{len(rows)} rows → {len(self._workers)} workers")
        return count

    def ingest_raw(self, rows: list[dict]) -> int:
        """
        Incremental ingestion (no reset). Useful for event-driven updates.

        Args:
            rows: List of raw Supabase task_assignments dicts.

        Returns:
            Number of valid records processed.
        """
        return self._ingest_rows(rows)

    def _ingest_rows(self, rows: list[dict]) -> int:
        """Internal ingestion — parses rows and updates per-worker state."""
        count = 0
        for row in rows:
            worker_id = self._resolve_worker_id(row)
            if not worker_id:
                continue

            if worker_id not in self._workers:
                self._workers[worker_id] = _WorkerFPQState(worker_id=worker_id)

            state = self._workers[worker_id]
            state.total_tasks += 1

            submission_count = int(row.get("submission_count") or 1)
            state.total_attempts += submission_count

            outcome = self._normalize_outcome(row)

            # First-pass detection
            first_pass_approved = row.get("first_submission_approved")
            if first_pass_approved is True:
                state.first_pass_count += 1
            elif first_pass_approved is False:
                pass  # explicitly not first-pass
            elif submission_count == 1 and outcome == "approved":
                state.first_pass_count += 1

            # Multi-attempt tracking
            if submission_count > 1:
                state.multi_attempt_tasks += 1

            # Rejection recovery
            had_rejection = (
                submission_count > 1
                or (outcome == "rejected" and submission_count >= 1)
            )
            if had_rejection:
                state.rejection_events += 1
                if outcome == "approved":
                    state.recovery_events += 1

            # Quality score
            qs = self._parse_quality_score(row)
            if qs is not None:
                state.quality_scores.append(qs)

            count += 1

        return count

    def _resolve_worker_id(self, row: dict) -> Optional[str]:
        """Extract worker identifier from row, trying all known field names."""
        return (
            row.get("worker_wallet")
            or row.get("worker_address")
            or row.get("wallet")
            or row.get("worker_id")
            or None
        )

    def _normalize_outcome(self, row: dict) -> str:
        """Normalize status/outcome/final_status to canonical values."""
        raw = (
            row.get("status")
            or row.get("outcome")
            or row.get("final_status")
            or "pending"
        ).lower().strip()
        if raw in ("completed", "done", "success"):
            return "approved"
        if raw in ("failed", "declined"):
            return "rejected"
        return raw

    def _parse_quality_score(self, row: dict) -> Optional[float]:
        """Parse quality score, normalizing from 0-100 if needed."""
        raw = row.get("quality_score") or row.get("score")
        if raw is None:
            return None
        try:
            qs = float(raw)
            if qs > 1.0:
                qs = qs / 100.0
            return max(0.0, min(1.0, qs))
        except (TypeError, ValueError):
            return None

    # -----------------------------------------------------------------------
    # Signal Computation
    # -----------------------------------------------------------------------

    def signal(self, worker_id: str) -> FPQSignalResult:
        """
        Compute Signal #24 for a worker.

        Returns FPQSignalResult with fpq_bonus in [MIN_FPQ_PENALTY, MAX_FPQ_BONUS].
        Workers with no history return fpq_bonus=0.0 (neutral).
        """
        if worker_id not in self._workers:
            return FPQSignalResult(
                worker_id=worker_id,
                fpq_bonus=0.0,
                reason="no_history",
            )

        state = self._workers[worker_id]
        n = state.total_tasks

        # Confidence scaling
        confidence = min(1.0, math.log(n + 1) / math.log(MIN_OBSERVATIONS + 1))

        # Sub-signals
        fpr = state.first_pass_rate()
        rev = state.revision_efficiency()
        rrr = state.rejection_recovery_rate()
        qc = state.quality_consistency()

        # Weighted composite → center on 0.5 → scale to bonus range
        composite = (
            WEIGHT_FIRST_PASS * fpr
            + WEIGHT_REVISION_EFFICIENCY * rev
            + WEIGHT_REJECTION_RECOVERY * rrr
            + WEIGHT_QUALITY_CONSISTENCY * qc
        )
        raw_bonus = (composite - 0.5) * 2.0 * MAX_FPQ_BONUS
        fpq_bonus = max(MIN_FPQ_PENALTY, min(MAX_FPQ_BONUS, raw_bonus * confidence))

        reason = "computed"
        if n < MIN_OBSERVATIONS:
            reason = f"attenuated_{n}_obs"

        return FPQSignalResult(
            worker_id=worker_id,
            fpq_bonus=fpq_bonus,
            confidence=confidence,
            first_pass_rate=fpr,
            revision_efficiency=rev,
            rejection_recovery_rate=rrr,
            quality_consistency=qc,
            task_count=n,
            reason=reason,
        )

    # -----------------------------------------------------------------------
    # Analytics
    # -----------------------------------------------------------------------

    def fpq_leaderboard(self, top_n: int = 20) -> list[dict]:
        """Workers ranked by FPQ bonus (best to worst)."""
        signals = [self.signal(wid) for wid in self._workers]
        signals.sort(key=lambda s: s.fpq_bonus, reverse=True)
        return [
            {
                "rank": i + 1,
                "worker_id": s.worker_id,
                "fpq_bonus": round(s.fpq_bonus, 4),
                "first_pass_rate": round(s.first_pass_rate, 3),
                "revision_efficiency": round(s.revision_efficiency, 3),
                "rejection_recovery_rate": round(s.rejection_recovery_rate, 3),
                "quality_consistency": round(s.quality_consistency, 3),
                "confidence": round(s.confidence, 3),
                "task_count": s.task_count,
            }
            for i, s in enumerate(signals[:top_n])
        ]

    def fpq_summary(self) -> dict:
        """Fleet-wide FPQ statistics."""
        if not self._workers:
            return {
                "total_workers": 0,
                "signal": SIGNAL_ID,
                "module": MODULE_ID,
            }

        all_signals = [self.signal(wid) for wid in self._workers]
        bonuses = [s.fpq_bonus for s in all_signals]
        fprs = [self._workers[wid].first_pass_rate() for wid in self._workers]

        return {
            "total_workers": len(self._workers),
            "avg_fpq_bonus": round(sum(bonuses) / len(bonuses), 4),
            "avg_first_pass_rate": round(sum(fprs) / len(fprs), 3),
            "perfect_first_pass_workers": sum(1 for r in fprs if r >= 1.0),
            "low_first_pass_workers": sum(1 for r in fprs if r <= 0.3),
            "positive_bonus_workers": sum(1 for b in bonuses if b > 0),
            "negative_bonus_workers": sum(1 for b in bonuses if b < 0),
            "signal": SIGNAL_ID,
            "module": MODULE_ID,
            "last_sync_ts": self._last_sync_ts,
            "records_processed": self._records_processed,
        }

    def worker_fpq_profile(self, worker_id: str) -> dict:
        """Detailed FPQ profile for a single worker."""
        if worker_id not in self._workers:
            return {"worker_id": worker_id, "status": "unknown"}

        state = self._workers[worker_id]
        sig = self.signal(worker_id)

        return {
            "worker_id": worker_id,
            "task_count": state.total_tasks,
            "first_pass_count": state.first_pass_count,
            "first_pass_rate": round(state.first_pass_rate(), 3),
            "multi_attempt_tasks": state.multi_attempt_tasks,
            "revision_efficiency": round(state.revision_efficiency(), 3),
            "rejection_events": state.rejection_events,
            "recovery_events": state.recovery_events,
            "rejection_recovery_rate": round(state.rejection_recovery_rate(), 3),
            "quality_scores_count": len(state.quality_scores),
            "quality_consistency": round(state.quality_consistency(), 3),
            "fpq_bonus": round(sig.fpq_bonus, 4),
            "confidence": round(sig.confidence, 3),
        }

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Persist bridge state to JSON file."""
        data = {
            "version": VERSION,
            "module": MODULE_ID,
            "signal": SIGNAL_ID,
            "last_sync_ts": self._last_sync_ts,
            "records_processed": self._records_processed,
            "workers": {
                wid: {
                    "total_tasks": s.total_tasks,
                    "first_pass_count": s.first_pass_count,
                    "total_attempts": s.total_attempts,
                    "multi_attempt_tasks": s.multi_attempt_tasks,
                    "rejection_events": s.rejection_events,
                    "recovery_events": s.recovery_events,
                    "quality_scores": s.quality_scores,
                }
                for wid, s in self._workers.items()
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"FPQBridge saved {len(self._workers)} workers → {path}")

    def load(self, path: str) -> None:
        """Load bridge state from JSON file."""
        with open(path) as f:
            data = json.load(f)

        self._workers.clear()
        self._last_sync_ts = data.get("last_sync_ts")
        self._records_processed = data.get("records_processed", 0)

        for wid, w in data.get("workers", {}).items():
            state = _WorkerFPQState(worker_id=wid)
            state.total_tasks = w.get("total_tasks", 0)
            state.first_pass_count = w.get("first_pass_count", 0)
            state.total_attempts = w.get("total_attempts", 0)
            state.multi_attempt_tasks = w.get("multi_attempt_tasks", 0)
            state.rejection_events = w.get("rejection_events", 0)
            state.recovery_events = w.get("recovery_events", 0)
            state.quality_scores = w.get("quality_scores", [])
            self._workers[wid] = state

        logger.info(f"FPQBridge loaded {len(self._workers)} workers from {path}")

    # -----------------------------------------------------------------------
    # Health
    # -----------------------------------------------------------------------

    def health(self) -> dict:
        """Health check for monitoring."""
        return {
            "status": "ok",
            "signal": SIGNAL_ID,
            "module": MODULE_ID,
            "name": "first_pass_quality",
            "dimension": 10,
            "workers_tracked": len(self._workers),
            "max_bonus": MAX_FPQ_BONUS,
            "last_sync_ts": self._last_sync_ts,
            "records_processed": self._records_processed,
        }
