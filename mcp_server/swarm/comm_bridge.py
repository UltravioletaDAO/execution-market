"""
CommBridge — Server-Side Communication Quality Intelligence

Module #70 in the KK V2 Swarm ecosystem.

Server-side counterpart to AutoJob's CommunicationQualityEngine (Signal #23).
Syncs worker communication records from EM's Supabase tables and builds
communication quality routing signals without requiring a direct AutoJob
dependency.

Signal #23 asks: "Does this worker communicate proactively when things don't
go as planned?"

After 22 signals optimizing task completion on behavioral, reputation, spatial,
and quality dimensions, Signal #23 closes the loop on the final dimension:
*communication*. A worker who goes silent for 6 hours and then cancels is worth
less than a worker who sends "storefront closed — retrying tomorrow at 9 AM."
Routing intelligence should capture this difference.

Four communication sub-signals:
    1. Response Latency Score     — How fast does worker respond after assignment?
    2. Message Clarity Score      — Are messages substantive (length + keywords)?
    3. Engagement Score           — Right amount of communication (optimal = 3 msgs)?
    4. Communication Outcome      — Does communication correlate with task approval?

Sub-signal weights:
    Response Latency:  30%
    Message Clarity:   25%
    Engagement Score:  25%
    Comm Outcome:      20%

Bonus bounds:
    Max bonus:   +0.07 (excellent communicator, fast + clear + outcome-positive)
    Max penalty: -0.07 (slow, chaotic messages, high rejection rate)

Narrower than Signal #22 (±0.09) because:
    - Many workers complete tasks without any messages
    - Absence of communication ≠ poor communication
    - Signal coverage is lower than quality history

Cold-start safety:
    - Workers with < MIN_COMM_OBSERVATIONS (8 comm tasks) are confidence-attenuated
    - Silent workers (never message) return neutral bonus = 0.0
    - Unknown workers return neutral bonus = 0.0

Key capabilities:
    1. Sync from Supabase task_assignments + messages tables
    2. Compute communication signal per worker
    3. Communication leaderboard
    4. Fleet-wide communication analytics
    5. Routing signal: comm_bonus for enrich_agents()
    6. Persistence (save/load)
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

logger = logging.getLogger("em.swarm.comm_bridge")

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Constants (mirrors AutoJob's CommunicationQualityEngine)
# ---------------------------------------------------------------------------

VERSION = "1.0.0"
MODULE_ID = 70
SIGNAL_ID = 23

MAX_COMM_BONUS: float = 0.07
MIN_COMM_PENALTY: float = -0.07

# Sub-signal weights
WEIGHT_LATENCY    = 0.30
WEIGHT_CLARITY    = 0.25
WEIGHT_ENGAGEMENT = 0.25
WEIGHT_OUTCOME    = 0.20

# Response latency decay constant (hours)
RESPONSE_DECAY_HOURS: float = 2.0

# Clarity thresholds (characters)
CLARITY_MIN_LENGTH: int = 30
CLARITY_GOOD_LENGTH: int = 80

# Engagement thresholds
OPTIMAL_MESSAGE_COUNT: int = 3
HIGH_MESSAGE_PENALTY_THRESHOLD: int = 10

# Confidence scaling
MIN_COMM_OBSERVATIONS: int = 8

# Resolution / escalation keywords
RESOLUTION_KEYWORDS = frozenset([
    "done", "complete", "completed", "finished", "attached", "uploaded",
    "at location", "on site", "submitted", "delivered", "photo taken",
    "here", "arrived", "confirmed", "verified", "checked",
])

ESCALATION_KEYWORDS = frozenset([
    "closed", "blocked", "issue", "problem", "delay", "wait", "retry",
    "rescheduling", "tomorrow", "cannot", "access denied", "locked",
    "not available", "need clarification",
])

# Task outcome normalization
OUTCOME_MAP = {
    "approved": "approved",
    "pass": "approved",
    "success": "approved",
    "rejected": "rejected",
    "fail": "rejected",
    "failed": "rejected",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "expired": "expired",
    "in_progress": "in_progress",
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class CommRecord:
    """Parsed communication record from Supabase."""
    worker_id: str
    task_id: str
    task_category: str
    outcome: str                       # normalized: approved/rejected/cancelled/expired/in_progress

    # Communication metrics
    response_time_seconds: float       # 0 = no messages
    message_count: int                 # 0 = silent worker
    avg_message_length: float
    asked_clarifying_question: bool
    used_resolution_keyword: bool
    used_escalation_keyword: bool


@dataclass
class WorkerCommProfile:
    """Aggregated communication statistics for one worker."""
    worker_id: str
    task_count: int = 0
    silent_task_count: int = 0
    total_messages: int = 0
    total_response_time_seconds: float = 0.0
    total_message_length: float = 0.0
    clarifying_question_count: int = 0
    resolution_keyword_count: int = 0
    escalation_keyword_count: int = 0
    approved_with_comm: int = 0
    rejected_with_comm: int = 0
    cancelled_with_comm: int = 0

    def apply(self, rec: CommRecord) -> None:
        self.task_count += 1
        if rec.message_count == 0:
            self.silent_task_count += 1
            return
        self.total_messages += rec.message_count
        self.total_response_time_seconds += rec.response_time_seconds
        self.total_message_length += rec.avg_message_length * rec.message_count
        if rec.asked_clarifying_question:
            self.clarifying_question_count += 1
        if rec.used_resolution_keyword:
            self.resolution_keyword_count += 1
        if rec.used_escalation_keyword:
            self.escalation_keyword_count += 1
        if rec.outcome == "approved":
            self.approved_with_comm += 1
        elif rec.outcome == "rejected":
            self.rejected_with_comm += 1
        elif rec.outcome in ("cancelled", "expired"):
            self.cancelled_with_comm += 1

    @property
    def communicating_task_count(self) -> int:
        return self.task_count - self.silent_task_count

    @property
    def avg_response_time_seconds(self) -> float:
        n = self.communicating_task_count
        if n == 0:
            return 0.0
        return self.total_response_time_seconds / n

    @property
    def avg_messages_per_task(self) -> float:
        n = self.communicating_task_count
        if n == 0:
            return 0.0
        return self.total_messages / n

    @property
    def avg_message_length(self) -> float:
        if self.total_messages == 0:
            return 0.0
        return self.total_message_length / self.total_messages

    @property
    def comm_approved_rate(self) -> float:
        n = self.communicating_task_count
        if n == 0:
            return 0.5  # Neutral — never communicated
        return self.approved_with_comm / n


@dataclass
class CommSignal:
    """Signal #23 output for one worker."""
    worker_id: str
    comm_bonus: float
    response_latency_score: float
    clarity_score: float
    engagement_score: float
    outcome_score: float
    raw_comm_score: float
    confidence: float
    sample_size: int
    reason: str

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "comm_bonus": round(self.comm_bonus, 4),
            "response_latency_score": round(self.response_latency_score, 3),
            "clarity_score": round(self.clarity_score, 3),
            "engagement_score": round(self.engagement_score, 3),
            "outcome_score": round(self.outcome_score, 3),
            "raw_comm_score": round(self.raw_comm_score, 3),
            "confidence": round(self.confidence, 3),
            "sample_size": self.sample_size,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# CommBridge
# ---------------------------------------------------------------------------

class CommBridge:
    """
    Module #70 — Server-Side Communication Quality Intelligence.

    Mirrors AutoJob's CommunicationQualityEngine for EM's coordinator.
    Ingests raw Supabase rows from task_assignments and optional messages
    tables, computes Signal #23 per worker, and provides routing bonuses.

    Usage:
        bridge = CommBridge()
        bridge.ingest_raw(rows)                    # Supabase rows
        sig = bridge.signal("0xWorker")
        # sig.comm_bonus → contribution to match_score
        # sig.reason → human-readable explanation
    """

    def __init__(self) -> None:
        self._profiles: dict[str, WorkerCommProfile] = {}
        self._total_records = 0
        self._last_sync_at: Optional[float] = None
        self._sync_count = 0

    # ─── Ingestion ────────────────────────────────────────────────────────

    def ingest_raw(self, rows: list[dict]) -> int:
        """
        Ingest raw Supabase rows.

        Flexible field handling — handles multiple EM schema variations:
          worker_wallet / worker_address / wallet / worker_id
          status / verdict / outcome
          task_category / evidence_type / category
          response_time_seconds (optional)
          message_count (optional — defaults to 0)
          avg_message_length (optional)
          has_question / has_resolution_keyword / has_escalation_keyword
        """
        ingested = 0
        for row in rows:
            rec = self._parse_row(row)
            if rec:
                self._apply_record(rec)
                ingested += 1
        self._total_records += ingested
        self._last_sync_at = time.time()
        self._sync_count += 1
        logger.debug(f"CommBridge: ingested {ingested}/{len(rows)} rows (sync #{self._sync_count})")
        return ingested

    def _apply_record(self, rec: CommRecord) -> None:
        if rec.worker_id not in self._profiles:
            self._profiles[rec.worker_id] = WorkerCommProfile(worker_id=rec.worker_id)
        self._profiles[rec.worker_id].apply(rec)

    def _parse_row(self, row: dict) -> Optional[CommRecord]:
        """Parse one Supabase row into a CommRecord. Returns None if unusable."""
        worker_id = (
            row.get("worker_wallet") or
            row.get("worker_address") or
            row.get("wallet") or
            row.get("worker_id")
        )
        if not worker_id:
            return None

        task_id = str(row.get("task_id") or row.get("id") or "")
        category = str(
            row.get("task_category") or
            row.get("evidence_type") or
            row.get("category") or
            "unknown"
        )

        outcome_raw = str(
            row.get("status") or
            row.get("verdict") or
            row.get("outcome") or
            "unknown"
        ).lower()
        outcome = OUTCOME_MAP.get(outcome_raw, "unknown")

        response_time = float(row.get("response_time_seconds", 0.0) or 0.0)
        message_count = int(row.get("message_count", 0) or 0)
        avg_len = float(row.get("avg_message_length", 0.0) or 0.0)
        has_question = bool(row.get("has_question", False))
        has_resolution = bool(row.get("has_resolution_keyword", False))
        has_escalation = bool(row.get("has_escalation_keyword", False))

        return CommRecord(
            worker_id=str(worker_id),
            task_id=task_id,
            task_category=category,
            outcome=outcome,
            response_time_seconds=response_time,
            message_count=message_count,
            avg_message_length=avg_len,
            asked_clarifying_question=has_question,
            used_resolution_keyword=has_resolution,
            used_escalation_keyword=has_escalation,
        )

    def full_refresh(self, rows: list[dict]) -> int:
        """Replace all profiles with a fresh batch of rows (full refresh model)."""
        self._profiles.clear()
        self._total_records = 0
        return self.ingest_raw(rows)

    # ─── Signal Computation ───────────────────────────────────────────────

    def signal(self, worker_id: str) -> CommSignal:
        """
        Compute Signal #23 for a worker.

        Returns:
            CommSignal with comm_bonus in [-0.07, +0.07]
        """
        profile = self._profiles.get(worker_id)

        # Cold start — no data
        if not profile or profile.task_count == 0:
            return CommSignal(
                worker_id=worker_id,
                comm_bonus=0.0,
                response_latency_score=0.5,
                clarity_score=0.5,
                engagement_score=0.5,
                outcome_score=0.5,
                raw_comm_score=0.5,
                confidence=0.0,
                sample_size=0,
                reason="no communication data — neutral signal",
            )

        # Silent worker — never messages → neutral (no penalty, no bonus)
        if profile.communicating_task_count == 0:
            return CommSignal(
                worker_id=worker_id,
                comm_bonus=0.0,
                response_latency_score=0.5,
                clarity_score=0.5,
                engagement_score=0.5,
                outcome_score=0.5,
                raw_comm_score=0.5,
                confidence=0.0,
                sample_size=profile.task_count,
                reason=f"silent worker — {profile.task_count} tasks, no messages observed",
            )

        # Sub-signal 1: Response Latency (30%)
        avg_response_hours = profile.avg_response_time_seconds / 3600.0
        latency_score = max(0.0, min(1.0,
            math.exp(-avg_response_hours / RESPONSE_DECAY_HOURS)
        ))

        # Sub-signal 2: Message Clarity (25%)
        avg_len = profile.avg_message_length
        if avg_len <= CLARITY_MIN_LENGTH:
            length_component = 0.3
        elif avg_len >= CLARITY_GOOD_LENGTH:
            length_component = 1.0
        else:
            frac = (avg_len - CLARITY_MIN_LENGTH) / (CLARITY_GOOD_LENGTH - CLARITY_MIN_LENGTH)
            length_component = 0.3 + 0.7 * frac

        comm_count = profile.communicating_task_count
        question_rate = profile.clarifying_question_count / comm_count
        resolution_rate = profile.resolution_keyword_count / comm_count
        escalation_rate = profile.escalation_keyword_count / comm_count

        clarity_score = max(0.0, min(1.0,
            length_component * 0.5 +
            question_rate * 0.2 +
            resolution_rate * 0.2 +
            escalation_rate * 0.1
        ))

        # Sub-signal 3: Engagement Score (25%)
        avg_msgs = profile.avg_messages_per_task
        opt = OPTIMAL_MESSAGE_COUNT
        if avg_msgs <= 0:
            engagement_score = 0.0
        elif avg_msgs <= opt:
            engagement_score = avg_msgs / opt
        elif avg_msgs <= HIGH_MESSAGE_PENALTY_THRESHOLD:
            overshoot = avg_msgs - opt
            max_overshoot = HIGH_MESSAGE_PENALTY_THRESHOLD - opt
            engagement_score = 1.0 - 0.5 * (overshoot / max_overshoot)
        else:
            engagement_score = 0.2
        engagement_score = max(0.0, min(1.0, engagement_score))

        # Sub-signal 4: Communication Outcome (20%)
        outcome_score = profile.comm_approved_rate

        # Weighted combination
        raw_comm_score = (
            latency_score * WEIGHT_LATENCY +
            clarity_score * WEIGHT_CLARITY +
            engagement_score * WEIGHT_ENGAGEMENT +
            outcome_score * WEIGHT_OUTCOME
        )

        # Confidence scaling
        n = comm_count
        confidence = min(1.0, math.log(n + 1) / math.log(MIN_COMM_OBSERVATIONS + 1))

        # Bonus
        comm_bonus = (raw_comm_score - 0.5) * 2.0 * MAX_COMM_BONUS * confidence
        comm_bonus = max(MIN_COMM_PENALTY, min(MAX_COMM_BONUS, comm_bonus))

        # Reason
        parts = []
        if latency_score >= 0.8:
            parts.append(f"fast responder (~{avg_response_hours:.1f}h)")
        elif latency_score <= 0.3:
            parts.append(f"slow responder (~{avg_response_hours:.1f}h)")
        if clarity_score >= 0.75:
            parts.append("clear communicator")
        if escalation_rate >= 0.3:
            parts.append("proactively flags issues")
        if outcome_score >= 0.8:
            parts.append("comm→success link strong")
        elif outcome_score <= 0.3:
            parts.append("comm→rejection link present")
        if not parts:
            parts.append("average communication pattern")

        reason = (
            f"Signal #23 Module #{MODULE_ID}: {'; '.join(parts)} "
            f"({n} comm tasks, conf={confidence:.2f})"
        )

        return CommSignal(
            worker_id=worker_id,
            comm_bonus=comm_bonus,
            response_latency_score=latency_score,
            clarity_score=clarity_score,
            engagement_score=engagement_score,
            outcome_score=outcome_score,
            raw_comm_score=raw_comm_score,
            confidence=confidence,
            sample_size=profile.task_count,
            reason=reason,
        )

    # ─── Analytics ────────────────────────────────────────────────────────

    def comm_leaderboard(self, top_n: int = 10) -> list[dict]:
        """Workers ranked by communication quality (highest bonus first)."""
        results = []
        for worker_id in self._profiles:
            sig = self.signal(worker_id)
            results.append({
                "worker_id": worker_id,
                "comm_bonus": sig.comm_bonus,
                "raw_comm_score": sig.raw_comm_score,
                "confidence": sig.confidence,
                "sample_size": sig.sample_size,
                "reason": sig.reason,
            })
        results.sort(key=lambda x: x["comm_bonus"], reverse=True)
        return results[:top_n]

    def silent_workers(self) -> list[dict]:
        """Workers who never message — neither penalized nor rewarded."""
        return [
            {
                "worker_id": wid,
                "task_count": p.task_count,
                "note": "silent worker — no communication signal",
            }
            for wid, p in self._profiles.items()
            if p.communicating_task_count == 0 and p.task_count > 0
        ]

    def comm_summary(self) -> dict:
        """Fleet-wide communication statistics."""
        if not self._profiles:
            return {
                "worker_count": 0,
                "total_records": self._total_records,
                "module_id": MODULE_ID,
                "signal_id": SIGNAL_ID,
                "version": VERSION,
            }

        all_profiles = list(self._profiles.values())
        comm_profiles = [p for p in all_profiles if p.communicating_task_count > 0]

        avg_response = (
            sum(p.avg_response_time_seconds for p in comm_profiles) / len(comm_profiles)
            if comm_profiles else 0.0
        )
        avg_msgs = (
            sum(p.avg_messages_per_task for p in comm_profiles) / len(comm_profiles)
            if comm_profiles else 0.0
        )

        signals = [self.signal(wid) for wid in self._profiles]
        positive_count = sum(1 for s in signals if s.comm_bonus > 0.01)
        negative_count = sum(1 for s in signals if s.comm_bonus < -0.01)
        neutral_count = len(signals) - positive_count - negative_count

        return {
            "worker_count": len(self._profiles),
            "total_records": self._total_records,
            "communicating_workers": len(comm_profiles),
            "silent_workers": len(all_profiles) - len(comm_profiles),
            "avg_response_hours": round(avg_response / 3600.0, 2),
            "avg_messages_per_task": round(avg_msgs, 2),
            "positive_signal_workers": positive_count,
            "negative_signal_workers": negative_count,
            "neutral_signal_workers": neutral_count,
            "last_sync_at": self._last_sync_at,
            "sync_count": self._sync_count,
            "module_id": MODULE_ID,
            "signal_id": SIGNAL_ID,
            "version": VERSION,
        }

    def worker_profile(self, worker_id: str) -> dict:
        """Detailed communication breakdown for a worker."""
        profile = self._profiles.get(worker_id)
        if not profile:
            return {"worker_id": worker_id, "error": "no data"}

        sig = self.signal(worker_id)
        return {
            "worker_id": worker_id,
            "signal": sig.to_dict(),
            "profile": {
                "task_count": profile.task_count,
                "communicating_task_count": profile.communicating_task_count,
                "silent_task_count": profile.silent_task_count,
                "avg_response_hours": round(profile.avg_response_time_seconds / 3600.0, 2),
                "avg_messages_per_task": round(profile.avg_messages_per_task, 2),
                "avg_message_length": round(profile.avg_message_length, 1),
                "clarifying_question_rate": round(
                    profile.clarifying_question_count / max(1, profile.communicating_task_count), 3
                ),
                "resolution_keyword_rate": round(
                    profile.resolution_keyword_count / max(1, profile.communicating_task_count), 3
                ),
                "escalation_keyword_rate": round(
                    profile.escalation_keyword_count / max(1, profile.communicating_task_count), 3
                ),
                "comm_approved_rate": round(profile.comm_approved_rate, 3),
                "approved_with_comm": profile.approved_with_comm,
                "rejected_with_comm": profile.rejected_with_comm,
                "cancelled_with_comm": profile.cancelled_with_comm,
            },
        }

    # ─── Persistence ──────────────────────────────────────────────────────

    def save(self, path: str) -> None:
        """Persist bridge state to a JSON file."""
        data = {
            "version": VERSION,
            "module_id": MODULE_ID,
            "signal_id": SIGNAL_ID,
            "total_records": self._total_records,
            "last_sync_at": self._last_sync_at,
            "sync_count": self._sync_count,
            "profiles": {
                wid: {
                    "worker_id": p.worker_id,
                    "task_count": p.task_count,
                    "silent_task_count": p.silent_task_count,
                    "total_messages": p.total_messages,
                    "total_response_time_seconds": p.total_response_time_seconds,
                    "total_message_length": p.total_message_length,
                    "clarifying_question_count": p.clarifying_question_count,
                    "resolution_keyword_count": p.resolution_keyword_count,
                    "escalation_keyword_count": p.escalation_keyword_count,
                    "approved_with_comm": p.approved_with_comm,
                    "rejected_with_comm": p.rejected_with_comm,
                    "cancelled_with_comm": p.cancelled_with_comm,
                }
                for wid, p in self._profiles.items()
            },
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"CommBridge: saved {len(self._profiles)} profiles to {path}")

    def load(self, path: str) -> None:
        """Load bridge state from a JSON file."""
        with open(path) as f:
            data = json.load(f)
        self._total_records = data.get("total_records", 0)
        self._last_sync_at = data.get("last_sync_at")
        self._sync_count = data.get("sync_count", 0)
        self._profiles = {}
        for wid, p in data.get("profiles", {}).items():
            profile = WorkerCommProfile(worker_id=wid)
            profile.task_count = p.get("task_count", 0)
            profile.silent_task_count = p.get("silent_task_count", 0)
            profile.total_messages = p.get("total_messages", 0)
            profile.total_response_time_seconds = p.get("total_response_time_seconds", 0.0)
            profile.total_message_length = p.get("total_message_length", 0.0)
            profile.clarifying_question_count = p.get("clarifying_question_count", 0)
            profile.resolution_keyword_count = p.get("resolution_keyword_count", 0)
            profile.escalation_keyword_count = p.get("escalation_keyword_count", 0)
            profile.approved_with_comm = p.get("approved_with_comm", 0)
            profile.rejected_with_comm = p.get("rejected_with_comm", 0)
            profile.cancelled_with_comm = p.get("cancelled_with_comm", 0)
            self._profiles[wid] = profile
        logger.info(f"CommBridge: loaded {len(self._profiles)} profiles from {path}")

    # ─── Diagnostics ─────────────────────────────────────────────────────

    def health(self) -> dict:
        """Health status for monitoring."""
        worker_count = len(self._profiles)
        comm_workers = sum(
            1 for p in self._profiles.values() if p.communicating_task_count > 0
        )
        return {
            "status": "healthy" if worker_count > 0 else "empty",
            "worker_count": worker_count,
            "communicating_workers": comm_workers,
            "total_records": self._total_records,
            "last_sync_at": self._last_sync_at,
            "sync_count": self._sync_count,
            "module_id": MODULE_ID,
            "signal_id": SIGNAL_ID,
            "version": VERSION,
        }
