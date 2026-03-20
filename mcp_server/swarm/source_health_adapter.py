"""
SourceHealthAdapter — Bridges AutoJob Source Health to Swarm Intelligence
=========================================================================

The swarm makes better routing decisions when it knows the quality of
external intelligence feeds. This adapter:

1. **Fetches health data** from AutoJob's source health monitor
2. **Translates** API-level health into swarm-actionable intelligence
3. **Provides** quality-weighted source selection for enrichment
4. **Tracks** source reliability trends for adaptive behavior

The swarm uses this to:
- Avoid enriching tasks from broken/degraded data sources
- Weight job matches by source reliability
- Detect when critical intelligence feeds go down
- Adjust matching confidence when data quality drops

No external dependencies. Works with AutoJob health data (JSON) or standalone.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger("em.swarm.source_health")


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────


class SourceTier(str, Enum):
    """Source reliability tier for routing decisions."""

    GOLD = "gold"  # Consistently healthy, high quality (health > 0.8)
    SILVER = "silver"  # Usually healthy, good quality (health > 0.5)
    BRONZE = "bronze"  # Sometimes available, variable quality (health > 0.2)
    DEAD = "dead"  # Consistently broken or empty (health <= 0.2)


@dataclass
class SourceStatus:
    """Current status of an external data source."""

    name: str
    tier: str = "unknown"
    health_score: float = 0.0
    data_quality: float = 0.0
    avg_response_ms: float = 0.0
    last_job_count: int = 0
    last_checked: Optional[str] = None
    reliability_pct: float = 0.0  # % of time healthy over history
    consecutive_failures: int = 0
    trend: str = "unknown"  # "improving", "stable", "declining", "unknown"

    def is_usable(self) -> bool:
        """Is this source worth querying?"""
        return self.tier in (SourceTier.GOLD.value, SourceTier.SILVER.value)

    def confidence_factor(self) -> float:
        """Multiplier for match confidence from this source.

        Gold sources don't reduce confidence.
        Silver reduces by 10%.
        Bronze reduces by 40%.
        Dead sources reduce to near-zero.
        """
        factors = {
            SourceTier.GOLD.value: 1.0,
            SourceTier.SILVER.value: 0.9,
            SourceTier.BRONZE.value: 0.6,
            SourceTier.DEAD.value: 0.1,
        }
        return factors.get(self.tier, 0.5)


@dataclass
class HealthSummary:
    """Aggregate health across all sources."""

    total_sources: int = 0
    gold_count: int = 0
    silver_count: int = 0
    bronze_count: int = 0
    dead_count: int = 0
    avg_system_health: float = 0.0
    total_available_jobs: int = 0
    best_sources: list = field(default_factory=list)
    worst_sources: list = field(default_factory=list)
    updated_at: str = ""

    def system_usable(self) -> bool:
        """Is the overall system healthy enough for enrichment?"""
        return (self.gold_count + self.silver_count) >= 3

    def enrichment_quality(self) -> str:
        """Expected quality of enrichment results."""
        if self.gold_count >= 5:
            return "high"
        elif (self.gold_count + self.silver_count) >= 5:
            return "medium"
        elif (self.gold_count + self.silver_count) >= 2:
            return "low"
        return "unreliable"


# ──────────────────────────────────────────────────────────────
# Adapter
# ──────────────────────────────────────────────────────────────


class SourceHealthAdapter:
    """Bridges external source health data to swarm routing intelligence."""

    # Tier thresholds
    GOLD_THRESHOLD = 0.8
    SILVER_THRESHOLD = 0.5
    BRONZE_THRESHOLD = 0.2

    def __init__(self):
        self._sources: dict = {}  # name → SourceStatus
        self._history: list = []  # List of past health snapshots
        self._last_update: float = 0
        self._update_count: int = 0

    def ingest_health_report(self, report: dict):
        """Ingest a health report from AutoJob's source_health_monitor.

        Expects the JSON format from SourceHealthMonitor.probe_all().to_dict()
        """
        if not report:
            return

        probes = report.get("probes", [])
        for probe in probes:
            name = probe.get("name", "")
            if not name:
                continue

            status = self._sources.get(name, SourceStatus(name=name))
            status.health_score = probe.get("overall_health", 0.0)
            status.data_quality = probe.get("data_quality_score", 0.0)
            status.avg_response_ms = probe.get("response_time_ms", 0.0)
            status.last_job_count = probe.get("job_count", 0)
            status.last_checked = probe.get("probed_at", "")
            status.tier = self._classify_tier(status.health_score)

            # Track consecutive failures
            if probe.get("status") in ("error", "timeout"):
                status.consecutive_failures += 1
            else:
                status.consecutive_failures = 0

            self._sources[name] = status

        self._last_update = time.monotonic()
        self._update_count += 1

        # Store in history for trend analysis
        self._history.append(
            {
                "ts": report.get("probed_at", ""),
                "system_health": report.get("overall_system_health", 0),
                "sources": {
                    p["name"]: p.get("overall_health", 0)
                    for p in probes
                    if p.get("name")
                },
            }
        )

        # Compute trends
        self._compute_trends()

    def ingest_history(self, history: list):
        """Ingest historical health data for trend analysis.

        Expects the format from AutoJob's health_history.json
        """
        for entry in history:
            sources = entry.get("sources", {})
            for name, data in sources.items():
                if name not in self._sources:
                    self._sources[name] = SourceStatus(name=name)

                # Update reliability from history
                if isinstance(data, dict):
                    if data.get("status") in ("healthy", "degraded"):
                        pass  # Will compute below

        self._history.extend(history)
        self._compute_reliability()
        self._compute_trends()

    def _classify_tier(self, health: float) -> str:
        """Classify a source into a tier based on health score."""
        if health >= self.GOLD_THRESHOLD:
            return SourceTier.GOLD.value
        elif health >= self.SILVER_THRESHOLD:
            return SourceTier.SILVER.value
        elif health >= self.BRONZE_THRESHOLD:
            return SourceTier.BRONZE.value
        return SourceTier.DEAD.value

    def _compute_reliability(self):
        """Compute reliability percentage from history."""
        if not self._history:
            return

        source_counts = defaultdict(lambda: {"healthy": 0, "total": 0})
        for entry in self._history[-50:]:  # Last 50 snapshots
            sources = entry.get("sources", {})
            for name, data in sources.items():
                source_counts[name]["total"] += 1
                if isinstance(data, dict):
                    if data.get("status") in ("healthy", "degraded"):
                        source_counts[name]["healthy"] += 1
                elif isinstance(data, (int, float)):
                    if data > self.BRONZE_THRESHOLD:
                        source_counts[name]["healthy"] += 1

        for name, counts in source_counts.items():
            if name in self._sources and counts["total"] > 0:
                self._sources[name].reliability_pct = (
                    counts["healthy"] / counts["total"]
                )

    def _compute_trends(self):
        """Compute trend direction for each source."""
        if len(self._history) < 3:
            return

        for name, status in self._sources.items():
            scores = []
            for entry in self._history[-10:]:
                sources = entry.get("sources", {})
                if name in sources:
                    data = sources[name]
                    if isinstance(data, dict):
                        scores.append(data.get("quality", data.get("health", 0)))
                    elif isinstance(data, (int, float)):
                        scores.append(data)

            if len(scores) < 3:
                status.trend = "unknown"
                continue

            recent = sum(scores[-3:]) / 3
            older = sum(scores[:3]) / 3
            diff = recent - older

            if diff > 0.1:
                status.trend = "improving"
            elif diff < -0.1:
                status.trend = "declining"
            else:
                status.trend = "stable"

    # ──────────────────────────────────────────────────────────
    # Query API
    # ──────────────────────────────────────────────────────────

    def get_source(self, name: str) -> Optional[SourceStatus]:
        """Get status for a specific source."""
        return self._sources.get(name)

    def get_usable_sources(self) -> list:
        """Get all sources worth querying (gold + silver)."""
        return [s for s in self._sources.values() if s.is_usable()]

    def get_by_tier(self, tier: str) -> list:
        """Get sources in a specific tier."""
        return [s for s in self._sources.values() if s.tier == tier]

    def get_summary(self) -> HealthSummary:
        """Get aggregate health summary."""
        summary = HealthSummary(
            total_sources=len(self._sources),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

        healths = []
        for s in self._sources.values():
            if s.tier == SourceTier.GOLD.value:
                summary.gold_count += 1
            elif s.tier == SourceTier.SILVER.value:
                summary.silver_count += 1
            elif s.tier == SourceTier.BRONZE.value:
                summary.bronze_count += 1
            else:
                summary.dead_count += 1

            summary.total_available_jobs += s.last_job_count
            healths.append(s.health_score)

        if healths:
            summary.avg_system_health = sum(healths) / len(healths)

        sorted_sources = sorted(
            self._sources.values(),
            key=lambda s: s.health_score,
            reverse=True,
        )
        summary.best_sources = [s.name for s in sorted_sources[:3]]
        summary.worst_sources = [s.name for s in sorted_sources[-3:]]

        return summary

    def confidence_adjustment(self, source_name: str) -> float:
        """Get confidence multiplier for matches from a specific source.

        Used by the swarm to adjust routing confidence based on source quality.
        """
        source = self._sources.get(source_name)
        if not source:
            return 0.5  # Unknown source → moderate penalty
        return source.confidence_factor()

    def should_query(self, source_name: str) -> bool:
        """Should the swarm bother querying this source?"""
        source = self._sources.get(source_name)
        if not source:
            return True  # Unknown → try it
        if source.consecutive_failures >= 5:
            return False  # Too many failures → skip
        return source.is_usable()

    def get_recommended_sources(self, limit: int = 10) -> list:
        """Get the best sources to query, ordered by reliability × quality."""
        usable = self.get_usable_sources()
        scored = []
        for s in usable:
            # Composite: reliability + current health + data quality
            score = (
                s.reliability_pct * 0.3 + s.health_score * 0.4 + s.data_quality * 0.3
            )
            scored.append((s, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:limit]]

    @property
    def update_count(self) -> int:
        return self._update_count

    @property
    def source_count(self) -> int:
        return len(self._sources)
