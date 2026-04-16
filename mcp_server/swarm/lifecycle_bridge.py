"""
LifecycleBridge — Connects EM checkpoint data to routing intelligence.

Module #62 in the swarm architecture.

Bridges the gap between EM's task_lifecycle_checkpoints table
(server-side audit data) and AutoJob's LifecycleIntelligence
(client-side routing signal). The bridge:

1. Fetches checkpoint data from Supabase on demand or on schedule
2. Converts checkpoint rows into the format AutoJob expects
3. Caches lifecycle profiles for quick routing lookups
4. Provides MCP tool surface for swarm coordinators

This module enables the swarm coordinator to use lifecycle
intelligence as Signal #14 without direct AutoJob dependency.

Usage:
    bridge = LifecycleBridge()
    await bridge.sync()  # Pull latest checkpoints

    signal = bridge.worker_signal("worker_uuid")
    profile = bridge.agent_profile("agent_id")
    funnel = bridge.completion_funnel()
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("em.swarm.lifecycle_bridge")

UTC = timezone.utc

# Lifecycle stages (mirrors AutoJob's constants)
LIFECYCLE_STAGES = [
    "auth_erc8128",
    "identity_erc8004",
    "balance_sufficient",
    "payment_auth_signed",
    "task_created",
    "escrow_locked",
    "worker_assigned",
    "evidence_submitted",
    "ai_verified",
    "approved",
    "payment_released",
    "agent_rated_worker",
    "worker_rated_agent",
    "fees_distributed",
]


@dataclass
class LifecycleConfig:
    """Configuration for the LifecycleBridge."""

    sync_interval_seconds: int = 300  # 5 minutes
    max_checkpoints: int = 5000
    cache_ttl_seconds: int = 60
    enable_worker_signals: bool = True
    enable_agent_profiles: bool = True
    enable_version_analysis: bool = True


@dataclass
class WorkerSignal:
    """Lifecycle-based routing signal for a worker."""

    worker_id: str
    tasks_assigned: int
    evidence_rate: float  # 0-1
    approval_rate: float  # 0-1
    avg_evidence_minutes: Optional[float]
    has_erc8004: bool
    reputation_engagement: float  # 0-1
    lifecycle_score: float  # 0-100
    risk_factors: List[str]
    recommendation: str  # strong_match | good_match | caution | avoid
    confidence: float  # 0-1
    cached_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "tasks_assigned": self.tasks_assigned,
            "evidence_rate": round(self.evidence_rate, 4),
            "approval_rate": round(self.approval_rate, 4),
            "avg_evidence_minutes": (
                round(self.avg_evidence_minutes, 1)
                if self.avg_evidence_minutes is not None
                else None
            ),
            "has_erc8004": self.has_erc8004,
            "reputation_engagement": round(self.reputation_engagement, 4),
            "lifecycle_score": round(self.lifecycle_score, 2),
            "risk_factors": self.risk_factors,
            "recommendation": self.recommendation,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class AgentProfile:
    """Lifecycle profile for a task-creating agent."""

    agent_id: str
    total_tasks: int
    completion_rate: float
    full_lifecycle_rate: float
    avg_time_to_payment_hours: Optional[float]
    weakest_stage: Optional[str]
    reputation_rate: float
    skill_versions: List[str]
    cached_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "total_tasks": self.total_tasks,
            "completion_rate": round(self.completion_rate, 4),
            "full_lifecycle_rate": round(self.full_lifecycle_rate, 4),
            "avg_time_to_payment_hours": (
                round(self.avg_time_to_payment_hours, 2)
                if self.avg_time_to_payment_hours
                else None
            ),
            "weakest_stage": self.weakest_stage,
            "reputation_rate": round(self.reputation_rate, 4),
            "skill_versions": self.skill_versions,
        }


@dataclass
class FunnelStep:
    """One step in the completion funnel."""

    stage: str
    reached_count: int
    total_tasks: int
    conversion_rate: float
    cumulative_rate: float
    dropoff_rate: float

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "reached": self.reached_count,
            "total": self.total_tasks,
            "conversion": round(self.conversion_rate, 4),
            "cumulative": round(self.cumulative_rate, 4),
            "dropoff": round(self.dropoff_rate, 4),
        }


class LifecycleBridge:
    """
    Bridges EM's checkpoint data to routing intelligence.

    Standalone module that works without AutoJob dependency.
    Implements the same analysis patterns but reads directly
    from Supabase rather than ingesting via API.
    """

    def __init__(self, config: Optional[LifecycleConfig] = None):
        self.config = config or LifecycleConfig()
        self._checkpoints: List[Dict[str, Any]] = []
        self._last_sync: float = 0
        self._worker_cache: Dict[str, WorkerSignal] = {}
        self._agent_cache: Dict[str, AgentProfile] = {}
        self._initialized = False

    # ── Sync ─────────────────────────────────────────────────────

    async def sync(self, force: bool = False) -> int:
        """
        Sync checkpoint data from Supabase.

        Args:
            force: Force sync even if within interval

        Returns:
            Number of checkpoints loaded
        """
        now = time.time()
        if not force and (now - self._last_sync) < self.config.sync_interval_seconds:
            return len(self._checkpoints)

        try:
            import supabase_client as db

            client = db.get_client()

            result = (
                client.table("task_lifecycle_checkpoints")
                .select("*")
                .order("updated_at", desc=True)
                .limit(self.config.max_checkpoints)
                .execute()
            )

            rows = result.data or []
            self._checkpoints = rows
            self._last_sync = now
            self._worker_cache.clear()
            self._agent_cache.clear()
            self._initialized = True

            logger.info("Synced %d lifecycle checkpoints", len(rows))
            return len(rows)

        except Exception as e:
            logger.warning("Lifecycle sync failed: %s", e)
            return len(self._checkpoints)

    def ingest(self, checkpoints: List[Dict[str, Any]]) -> int:
        """
        Directly ingest checkpoint data (for testing or offline use).

        Args:
            checkpoints: Checkpoint rows

        Returns:
            Number ingested
        """
        self._checkpoints.extend(checkpoints)
        if len(self._checkpoints) > self.config.max_checkpoints:
            excess = len(self._checkpoints) - self.config.max_checkpoints
            self._checkpoints = self._checkpoints[excess:]
        self._worker_cache.clear()
        self._agent_cache.clear()
        self._initialized = True
        return len(checkpoints)

    # ── Worker Signals ───────────────────────────────────────────

    def worker_signal(self, worker_id: str) -> WorkerSignal:
        """
        Get lifecycle routing signal for a worker.

        Returns cached signal if available and fresh.
        """
        # Check cache
        cached = self._worker_cache.get(worker_id)
        if cached and (time.time() - cached.cached_at) < self.config.cache_ttl_seconds:
            return cached

        # Build from checkpoints
        worker_cps = [
            cp for cp in self._checkpoints if cp.get("worker_id") == worker_id
        ]

        if not worker_cps:
            signal = WorkerSignal(
                worker_id=worker_id,
                tasks_assigned=0,
                evidence_rate=0.0,
                approval_rate=0.0,
                avg_evidence_minutes=None,
                has_erc8004=False,
                reputation_engagement=0.0,
                lifecycle_score=50.0,
                risk_factors=["no_lifecycle_history"],
                recommendation="caution",
                confidence=0.0,
            )
            self._worker_cache[worker_id] = signal
            return signal

        assigned = len(worker_cps)
        evidence_count = sum(1 for cp in worker_cps if cp.get("evidence_submitted"))
        approved_count = sum(1 for cp in worker_cps if cp.get("approved"))

        # Evidence timing
        evidence_times = []
        for cp in worker_cps:
            assigned_at = self._parse_ts(cp.get("worker_assigned_at"))
            evidence_at = self._parse_ts(cp.get("evidence_submitted_at"))
            if assigned_at and evidence_at and evidence_at > assigned_at:
                evidence_times.append(
                    (evidence_at - assigned_at).total_seconds() / 60.0
                )

        avg_evidence = (
            sum(evidence_times) / len(evidence_times) if evidence_times else None
        )

        has_8004 = any(cp.get("worker_erc8004") for cp in worker_cps)
        rated_agent = sum(1 for cp in worker_cps if cp.get("worker_rated_agent"))
        rep_engagement = rated_agent / assigned if assigned > 0 else 0.0

        # Compute lifecycle score
        evidence_rate = evidence_count / assigned if assigned > 0 else 0.0
        approval_rate = approved_count / assigned if assigned > 0 else 0.0

        score = 50.0
        score += evidence_rate * 25.0
        score += approval_rate * 25.0
        if has_8004:
            score += 5.0
        score += min(1.0, rep_engagement) * 5.0

        # Risk factors
        risks = []
        if evidence_rate < 0.7:
            risks.append("low_evidence_submission_rate")
        if avg_evidence and avg_evidence > 120:
            risks.append("slow_evidence_submitter")
        if not has_8004:
            risks.append("no_erc8004_identity")
        if rep_engagement < 0.2 and assigned > 3:
            risks.append("low_reputation_engagement")

        score -= len(risks) * 3.0
        score = max(0.0, min(100.0, score))

        # Confidence
        if assigned >= 20:
            confidence = 0.9
        elif assigned >= 10:
            confidence = 0.7
        elif assigned >= 5:
            confidence = 0.5
        elif assigned >= 2:
            confidence = 0.3
        else:
            confidence = 0.15

        # Recommendation
        if score >= 80 and confidence >= 0.5:
            recommendation = "strong_match"
        elif score >= 60:
            recommendation = "good_match"
        elif score >= 40:
            recommendation = "caution"
        else:
            recommendation = "avoid"

        signal = WorkerSignal(
            worker_id=worker_id,
            tasks_assigned=assigned,
            evidence_rate=evidence_rate,
            approval_rate=approval_rate,
            avg_evidence_minutes=avg_evidence,
            has_erc8004=has_8004,
            reputation_engagement=rep_engagement,
            lifecycle_score=score,
            risk_factors=risks,
            recommendation=recommendation,
            confidence=confidence,
        )
        self._worker_cache[worker_id] = signal
        return signal

    # ── Agent Profiles ───────────────────────────────────────────

    def agent_profile(self, agent_id: str) -> Optional[AgentProfile]:
        """Get lifecycle profile for an agent (task creator)."""
        cached = self._agent_cache.get(agent_id)
        if cached and (time.time() - cached.cached_at) < self.config.cache_ttl_seconds:
            return cached

        agent_cps = [
            cp for cp in self._checkpoints if cp.get("agent_id_resolved") == agent_id
        ]

        if not agent_cps:
            return None

        total = len(agent_cps)
        completed = sum(1 for cp in agent_cps if cp.get("payment_released"))
        full = sum(1 for cp in agent_cps if cp.get("fees_distributed"))

        # Time to payment
        payment_hours = []
        for cp in agent_cps:
            created = self._parse_ts(cp.get("task_created_at"))
            paid = self._parse_ts(cp.get("payment_released_at"))
            if created and paid and paid > created:
                payment_hours.append((paid - created).total_seconds() / 3600.0)

        avg_payment = sum(payment_hours) / len(payment_hours) if payment_hours else None

        # Weakest stage (highest dropoff)
        weakest = None
        worst = 0.0
        prev_count = total
        for stage in LIFECYCLE_STAGES:
            if stage == "task_created":
                prev_count = total
                continue
            reached = sum(1 for cp in agent_cps if cp.get(stage))
            if prev_count > 0:
                dropoff = 1.0 - (reached / prev_count)
                if dropoff > worst:
                    worst = dropoff
                    weakest = stage
            prev_count = reached

        # Reputation rate
        both_rated = sum(
            1
            for cp in agent_cps
            if cp.get("agent_rated_worker") and cp.get("worker_rated_agent")
        )

        # Skill versions
        versions = sorted(
            set(
                cp.get("skill_version", "unknown")
                for cp in agent_cps
                if cp.get("skill_version")
            )
        )

        profile = AgentProfile(
            agent_id=agent_id,
            total_tasks=total,
            completion_rate=completed / total if total > 0 else 0.0,
            full_lifecycle_rate=full / total if total > 0 else 0.0,
            avg_time_to_payment_hours=avg_payment,
            weakest_stage=weakest,
            reputation_rate=both_rated / completed if completed > 0 else 0.0,
            skill_versions=versions,
        )
        self._agent_cache[agent_id] = profile
        return profile

    # ── Funnel ───────────────────────────────────────────────────

    def completion_funnel(
        self,
        agent_id: Optional[str] = None,
        skill_version: Optional[str] = None,
    ) -> List[FunnelStep]:
        """
        Build completion funnel with optional filters.

        Args:
            agent_id: Filter to specific agent
            skill_version: Filter to specific skill version
        """
        cps = self._checkpoints
        if agent_id:
            cps = [cp for cp in cps if cp.get("agent_id_resolved") == agent_id]
        if skill_version:
            cps = [cp for cp in cps if cp.get("skill_version") == skill_version]

        if not cps:
            return []

        total = len(cps)
        prev_count = total
        funnel = []

        for stage in LIFECYCLE_STAGES:
            reached = sum(1 for cp in cps if cp.get(stage))
            conversion = reached / prev_count if prev_count > 0 else 0.0
            cumulative = reached / total if total > 0 else 0.0
            dropoff = 1.0 - conversion

            funnel.append(
                FunnelStep(
                    stage=stage,
                    reached_count=reached,
                    total_tasks=total,
                    conversion_rate=conversion,
                    cumulative_rate=cumulative,
                    dropoff_rate=dropoff,
                )
            )
            prev_count = reached

        return funnel

    # ── Summary ──────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        """High-level summary statistics."""
        total = len(self._checkpoints)
        if total == 0:
            return {
                "total_checkpoints": 0,
                "initialized": self._initialized,
                "last_sync": self._last_sync,
            }

        completed = sum(1 for cp in self._checkpoints if cp.get("payment_released"))
        cancelled = sum(1 for cp in self._checkpoints if cp.get("cancelled"))
        expired = sum(1 for cp in self._checkpoints if cp.get("expired"))

        agents = set(
            cp.get("agent_id_resolved")
            for cp in self._checkpoints
            if cp.get("agent_id_resolved")
        )
        workers = set(
            cp.get("worker_id") for cp in self._checkpoints if cp.get("worker_id")
        )
        versions = set(
            cp.get("skill_version")
            for cp in self._checkpoints
            if cp.get("skill_version")
        )

        return {
            "total_checkpoints": total,
            "completed": completed,
            "cancelled": cancelled,
            "expired": expired,
            "completion_rate": round(completed / total, 4) if total > 0 else 0.0,
            "unique_agents": len(agents),
            "unique_workers": len(workers),
            "skill_versions": sorted(versions),
            "initialized": self._initialized,
            "last_sync": self._last_sync,
            "cache_sizes": {
                "workers": len(self._worker_cache),
                "agents": len(self._agent_cache),
            },
        }

    # ── Health ───────────────────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """Health check for the integrator."""
        now = time.time()
        sync_age = now - self._last_sync if self._last_sync > 0 else float("inf")

        if not self._initialized:
            status = "not_initialized"
        elif sync_age > self.config.sync_interval_seconds * 3:
            status = "stale"
        elif len(self._checkpoints) == 0:
            status = "empty"
        else:
            status = "healthy"

        return {
            "status": status,
            "checkpoints": len(self._checkpoints),
            "last_sync_ago_seconds": round(sync_age, 0)
            if self._last_sync > 0
            else None,
            "cache_hit_rate": self._cache_hit_rate(),
        }

    def _cache_hit_rate(self) -> float:
        """Estimate cache utilization."""
        total_cached = len(self._worker_cache) + len(self._agent_cache)
        total_unique = len(
            set(
                cp.get("worker_id") or cp.get("agent_id_resolved")
                for cp in self._checkpoints
            )
        )
        return total_cached / total_unique if total_unique > 0 else 0.0

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _parse_ts(ts: Union[str, datetime, None]) -> Optional[datetime]:
        """Parse ISO timestamp."""
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
        if isinstance(ts, str):
            try:
                clean = ts.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean)
                return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                return None
        return None
