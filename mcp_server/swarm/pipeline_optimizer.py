"""
PipelineOptimizer — Routing Pipeline Performance Analysis & Tuning
===================================================================

Module #60 in the KK V2 Swarm.

Watches the 7-stage routing pipeline and produces actionable
optimization recommendations. Each stage (batch → validate → chain →
score → blend → select → route) emits timing and outcome data;
PipelineOptimizer aggregates, detects bottlenecks, and suggests
parameter changes to improve throughput, latency, and success rate.

Architecture:

    ┌──────────────────────────────────────────────────────────────┐
    │                     PipelineOptimizer                         │
    │                                                               │
    │  Stage Telemetry ──► [Aggregator] ──► [Analyzer] ──► Report  │
    │       │                                    │                  │
    │       │     ┌──────────────────────────────┤                  │
    │       │     │                              │                  │
    │       ▼     ▼                              ▼                  │
    │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐         │
    │  │  Timing     │  │ Bottleneck  │  │ Optimization │         │
    │  │  Profiles   │  │ Detector    │  │ Suggestions  │         │
    │  └─────────────┘  └─────────────┘  └──────────────┘         │
    │                                                               │
    │  7 Pipeline Stages Monitored:                                │
    │  ① Batch  ② Validate  ③ Chain  ④ Score                      │
    │  ⑤ Blend  ⑥ Select    ⑦ Route                               │
    └──────────────────────────────────────────────────────────────┘

What this provides:
    1. Per-stage timing profiles (p50, p90, p99, mean, max)
    2. Bottleneck detection — which stage dominates latency
    3. Throughput analysis — tasks/second at each stage
    4. Drop-off analysis — where tasks are lost (validation rejects, etc.)
    5. Optimization suggestions — concrete parameter changes
    6. Trend detection — is performance improving or degrading over time
    7. Stage correlation — which stages have coupled performance
    8. Cost efficiency — gas and compute cost per successful routing

Usage:
    from mcp_server.swarm.pipeline_optimizer import PipelineOptimizer

    optimizer = PipelineOptimizer()

    # Record stage executions
    optimizer.record("batch", duration_ms=12.5, tasks_in=50, tasks_out=8)
    optimizer.record("validate", duration_ms=1.2, tasks_in=8, tasks_out=7)
    optimizer.record("chain", duration_ms=45.3, tasks_in=7, tasks_out=7)
    optimizer.record("score", duration_ms=120.7, tasks_in=7, tasks_out=7)

    # Analyze
    report = optimizer.analyze()
    print(report.bottleneck)         # "score" (highest latency share)
    print(report.suggestions)        # ["Reduce signal count from 13 to 8"]
    print(report.stage_profiles)     # Per-stage percentile breakdowns

    # Trends
    trend = optimizer.trend("score", window=100)
    print(trend.direction)           # "degrading" | "stable" | "improving"
"""

import json
import logging
import math
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("em.swarm.pipeline_optimizer")


# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────

PIPELINE_STAGES = ["batch", "validate", "chain", "score", "blend", "select", "route"]
DEFAULT_HISTORY_LIMIT = 1000
DEFAULT_TREND_WINDOW = 100
BOTTLENECK_THRESHOLD_PCT = 0.40  # Stage using >40% of total latency = bottleneck
DROPOFF_ALERT_PCT = 0.20  # >20% drop at a stage triggers alert
DEGRADATION_THRESHOLD = 1.5  # 50% slower than baseline = degrading
IMPROVEMENT_THRESHOLD = 0.75  # 25% faster than baseline = improving


# ──────────────────────────────────────────────────────────────
# Types
# ──────────────────────────────────────────────────────────────


class PipelineStage(str, Enum):
    """The 7 stages of the KK V2 routing pipeline."""

    BATCH = "batch"
    VALIDATE = "validate"
    CHAIN = "chain"
    SCORE = "score"
    BLEND = "blend"
    SELECT = "select"
    ROUTE = "route"


class TrendDirection(str, Enum):
    """Performance trend direction."""

    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    INSUFFICIENT_DATA = "insufficient_data"


class SuggestionPriority(str, Enum):
    """Optimization suggestion priority level."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class StageRecord:
    """Single execution record for a pipeline stage."""

    stage: str
    duration_ms: float
    tasks_in: int
    tasks_out: int
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    @property
    def dropoff_rate(self) -> float:
        """Fraction of tasks lost at this stage."""
        if self.tasks_in == 0:
            return 0.0
        return 1.0 - (self.tasks_out / self.tasks_in)

    @property
    def throughput(self) -> float:
        """Tasks processed per second (based on output count)."""
        if self.duration_ms <= 0:
            return float("inf")
        return (self.tasks_out / self.duration_ms) * 1000


@dataclass
class StageProfile:
    """Statistical profile for a pipeline stage."""

    stage: str
    count: int
    mean_ms: float
    median_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    std_dev_ms: float
    total_tasks_in: int
    total_tasks_out: int
    avg_dropoff_rate: float
    avg_throughput: float  # tasks/sec

    @property
    def latency_share(self) -> float:
        """Placeholder — set by analyzer based on total pipeline latency."""
        return self._latency_share if hasattr(self, "_latency_share") else 0.0

    @latency_share.setter
    def latency_share(self, value: float):
        self._latency_share = value


@dataclass
class Suggestion:
    """An optimization suggestion."""

    priority: SuggestionPriority
    stage: str
    title: str
    detail: str
    metric_before: Optional[float] = None
    metric_name: Optional[str] = None
    estimated_improvement: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "priority": self.priority.value,
            "stage": self.stage,
            "title": self.title,
            "detail": self.detail,
        }
        if self.metric_before is not None:
            d["metric_before"] = self.metric_before
        if self.metric_name:
            d["metric_name"] = self.metric_name
        if self.estimated_improvement:
            d["estimated_improvement"] = self.estimated_improvement
        return d


@dataclass
class TrendResult:
    """Trend analysis result for a stage."""

    stage: str
    direction: TrendDirection
    baseline_ms: float  # mean of first half of window
    current_ms: float  # mean of second half of window
    change_pct: float  # positive = slower, negative = faster
    sample_count: int


@dataclass
class CorrelationResult:
    """Correlation between two pipeline stages."""

    stage_a: str
    stage_b: str
    coefficient: float  # Pearson correlation [-1, 1]
    sample_count: int
    interpretation: str  # human-readable


@dataclass
class PipelineReport:
    """Complete pipeline optimization report."""

    generated_at: str
    total_executions: int
    stage_profiles: Dict[str, StageProfile]
    bottleneck: Optional[str]  # stage name with highest latency share
    bottleneck_share: float  # percentage of total latency
    suggestions: List[Suggestion]
    dropoff_stages: List[str]  # stages with significant task loss
    trends: Dict[str, TrendResult]
    correlations: List[CorrelationResult]
    overall_throughput: float  # end-to-end tasks/sec
    overall_latency_ms: float  # end-to-end mean latency
    health_score: float  # 0-100 composite health

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "total_executions": self.total_executions,
            "bottleneck": self.bottleneck,
            "bottleneck_share": round(self.bottleneck_share, 3),
            "overall_throughput": round(self.overall_throughput, 2),
            "overall_latency_ms": round(self.overall_latency_ms, 2),
            "health_score": round(self.health_score, 1),
            "dropoff_stages": self.dropoff_stages,
            "suggestions": [s.to_dict() for s in self.suggestions],
            "stage_profiles": {
                k: {
                    "count": v.count,
                    "mean_ms": round(v.mean_ms, 2),
                    "median_ms": round(v.median_ms, 2),
                    "p90_ms": round(v.p90_ms, 2),
                    "p95_ms": round(v.p95_ms, 2),
                    "p99_ms": round(v.p99_ms, 2),
                    "min_ms": round(v.min_ms, 2),
                    "max_ms": round(v.max_ms, 2),
                    "avg_dropoff_rate": round(v.avg_dropoff_rate, 4),
                    "avg_throughput": round(v.avg_throughput, 2),
                    "latency_share": round(v.latency_share, 3),
                }
                for k, v in v.items()
            }
            if isinstance(self.stage_profiles, dict)
            and all(isinstance(v, dict) for v in self.stage_profiles.values())
            else {
                k: {
                    "count": v.count,
                    "mean_ms": round(v.mean_ms, 2),
                    "median_ms": round(v.median_ms, 2),
                    "p90_ms": round(v.p90_ms, 2),
                    "p95_ms": round(v.p95_ms, 2),
                    "p99_ms": round(v.p99_ms, 2),
                    "min_ms": round(v.min_ms, 2),
                    "max_ms": round(v.max_ms, 2),
                    "avg_dropoff_rate": round(v.avg_dropoff_rate, 4),
                    "avg_throughput": round(v.avg_throughput, 2),
                    "latency_share": round(v.latency_share, 3),
                }
                for k, v in self.stage_profiles.items()
            },
            "trends": {
                k: {
                    "direction": v.direction.value,
                    "baseline_ms": round(v.baseline_ms, 2),
                    "current_ms": round(v.current_ms, 2),
                    "change_pct": round(v.change_pct, 1),
                    "sample_count": v.sample_count,
                }
                for k, v in self.trends.items()
            },
            "correlations": [
                {
                    "stage_a": c.stage_a,
                    "stage_b": c.stage_b,
                    "coefficient": round(c.coefficient, 3),
                    "interpretation": c.interpretation,
                }
                for c in self.correlations
            ],
        }

    def summary(self) -> str:
        """Human-readable summary."""
        lines = [
            f"Pipeline Report ({self.generated_at})",
            f"  Health: {self.health_score:.0f}/100",
            f"  Executions: {self.total_executions}",
            f"  Throughput: {self.overall_throughput:.1f} tasks/sec",
            f"  Latency: {self.overall_latency_ms:.1f}ms (end-to-end)",
        ]
        if self.bottleneck:
            lines.append(
                f"  Bottleneck: {self.bottleneck} ({self.bottleneck_share:.0%} of latency)"
            )
        if self.dropoff_stages:
            lines.append(f"  High dropoff: {', '.join(self.dropoff_stages)}")
        if self.suggestions:
            lines.append(f"  Suggestions: {len(self.suggestions)}")
            for s in self.suggestions[:3]:
                lines.append(f"    [{s.priority.value.upper()}] {s.title}")
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# PipelineOptimizer
# ──────────────────────────────────────────────────────────────


class PipelineOptimizer:
    """
    Monitors and optimizes the 7-stage routing pipeline.

    Records per-stage execution data, computes statistical profiles,
    detects bottlenecks, tracks trends, identifies correlations,
    and produces actionable optimization suggestions.
    """

    def __init__(
        self,
        *,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        trend_window: int = DEFAULT_TREND_WINDOW,
        bottleneck_threshold: float = BOTTLENECK_THRESHOLD_PCT,
        dropoff_threshold: float = DROPOFF_ALERT_PCT,
        custom_analyzers: Optional[List[Callable]] = None,
    ):
        """
        Initialize PipelineOptimizer.

        Args:
            history_limit: Max records to retain per stage
            trend_window: Records to consider for trend analysis
            bottleneck_threshold: Latency share % that qualifies as bottleneck
            dropoff_threshold: Task drop rate that triggers alert
            custom_analyzers: Additional analyzer functions (take history, return suggestions)
        """
        self._history_limit = history_limit
        self._trend_window = trend_window
        self._bottleneck_threshold = bottleneck_threshold
        self._dropoff_threshold = dropoff_threshold
        self._custom_analyzers = custom_analyzers or []

        # Per-stage record history
        self._records: Dict[str, deque] = {
            stage: deque(maxlen=history_limit) for stage in PIPELINE_STAGES
        }

        # Pipeline-level tracking
        self._pipeline_runs: deque = deque(maxlen=history_limit)
        self._total_records = 0
        self._total_pipeline_runs = 0
        self._created_at = time.time()

    # ── Recording ──────────────────────────────────────────────

    def record(
        self,
        stage: str,
        *,
        duration_ms: float,
        tasks_in: int,
        tasks_out: int,
        metadata: Optional[dict] = None,
    ) -> StageRecord:
        """
        Record a single stage execution.

        Args:
            stage: Pipeline stage name (batch/validate/chain/score/blend/select/route)
            duration_ms: Execution time in milliseconds
            tasks_in: Number of tasks entering the stage
            tasks_out: Number of tasks exiting the stage
            metadata: Optional additional data (e.g., strategy used, errors)

        Returns:
            The created StageRecord

        Raises:
            ValueError: If stage name is not recognized
        """
        stage_lower = stage.lower()
        if stage_lower not in self._records:
            raise ValueError(
                f"Unknown stage '{stage}'. Valid stages: {PIPELINE_STAGES}"
            )

        record = StageRecord(
            stage=stage_lower,
            duration_ms=max(0.0, duration_ms),
            tasks_in=max(0, tasks_in),
            tasks_out=max(0, min(tasks_out, tasks_in)) if tasks_in > 0 else 0,
            metadata=metadata or {},
        )

        self._records[stage_lower].append(record)
        self._total_records += 1
        return record

    def record_pipeline_run(
        self,
        *,
        total_duration_ms: float,
        tasks_submitted: int,
        tasks_routed: int,
        stage_durations: Optional[Dict[str, float]] = None,
    ):
        """
        Record a complete pipeline run (all stages).

        Args:
            total_duration_ms: Total end-to-end time
            tasks_submitted: Tasks that entered the pipeline
            tasks_routed: Tasks successfully routed
            stage_durations: Per-stage breakdown in ms
        """
        run = {
            "total_duration_ms": max(0.0, total_duration_ms),
            "tasks_submitted": tasks_submitted,
            "tasks_routed": tasks_routed,
            "stage_durations": stage_durations or {},
            "timestamp": time.time(),
            "success_rate": (
                tasks_routed / tasks_submitted if tasks_submitted > 0 else 0.0
            ),
        }
        self._pipeline_runs.append(run)
        self._total_pipeline_runs += 1

    # ── Analysis ───────────────────────────────────────────────

    def analyze(self) -> PipelineReport:
        """
        Produce a full pipeline optimization report.

        Returns:
            PipelineReport with profiles, bottleneck, suggestions, trends, correlations
        """
        profiles = self._compute_profiles()
        bottleneck, bottleneck_share = self._detect_bottleneck(profiles)
        dropoff_stages = self._detect_dropoff(profiles)
        trends = self._compute_trends()
        correlations = self._compute_correlations()
        suggestions = self._generate_suggestions(
            profiles, bottleneck, dropoff_stages, trends
        )
        overall_throughput = self._compute_overall_throughput()
        overall_latency = self._compute_overall_latency()
        health_score = self._compute_health_score(
            profiles, bottleneck_share, dropoff_stages, trends
        )

        return PipelineReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_executions=self._total_records,
            stage_profiles=profiles,
            bottleneck=bottleneck,
            bottleneck_share=bottleneck_share,
            suggestions=suggestions,
            dropoff_stages=dropoff_stages,
            trends=trends,
            correlations=correlations,
            overall_throughput=overall_throughput,
            overall_latency_ms=overall_latency,
            health_score=health_score,
        )

    def profile(self, stage: str) -> Optional[StageProfile]:
        """Get statistical profile for a single stage."""
        stage_lower = stage.lower()
        records = list(self._records.get(stage_lower, []))
        if not records:
            return None
        return self._profile_from_records(stage_lower, records)

    def trend(
        self, stage: str, *, window: Optional[int] = None
    ) -> Optional[TrendResult]:
        """
        Analyze performance trend for a stage.

        Compares first half vs second half of the window.
        Returns None if no data exists for the stage.
        """
        stage_lower = stage.lower()
        records = list(self._records.get(stage_lower, []))
        if not records:
            return None
        w = window or self._trend_window
        recent = records[-w:] if len(records) > w else records
        return self._trend_from_records(stage_lower, recent)

    def bottleneck(self) -> Optional[Tuple[str, float]]:
        """Quick bottleneck check — returns (stage_name, share) or None."""
        profiles = self._compute_profiles()
        bn, share = self._detect_bottleneck(profiles)
        if bn:
            return (bn, share)
        return None

    def suggestions(self) -> List[Suggestion]:
        """Generate optimization suggestions without full report."""
        profiles = self._compute_profiles()
        bottleneck, _ = self._detect_bottleneck(profiles)
        dropoff_stages = self._detect_dropoff(profiles)
        trends = self._compute_trends()
        return self._generate_suggestions(profiles, bottleneck, dropoff_stages, trends)

    # ── Querying ───────────────────────────────────────────────

    def stage_records(self, stage: str, *, last: Optional[int] = None) -> List[StageRecord]:
        """Get raw records for a stage."""
        stage_lower = stage.lower()
        records = list(self._records.get(stage_lower, []))
        if last:
            return records[-last:]
        return records

    def stage_names(self) -> List[str]:
        """Return list of pipeline stage names."""
        return list(PIPELINE_STAGES)

    def has_data(self) -> bool:
        """Check if any records have been recorded."""
        return self._total_records > 0

    def record_count(self, stage: Optional[str] = None) -> int:
        """Count records for a stage, or total across all stages."""
        if stage:
            return len(self._records.get(stage.lower(), []))
        return sum(len(r) for r in self._records.values())

    # ── Metrics ────────────────────────────────────────────────

    def metrics(self) -> dict:
        """Operational metrics for the optimizer itself."""
        return {
            "total_records": self._total_records,
            "total_pipeline_runs": self._total_pipeline_runs,
            "records_per_stage": {k: len(v) for k, v in self._records.items()},
            "history_limit": self._history_limit,
            "trend_window": self._trend_window,
            "uptime_seconds": round(time.time() - self._created_at, 1),
            "custom_analyzers": len(self._custom_analyzers),
        }

    # ── Persistence ────────────────────────────────────────────

    def save(self, path: str):
        """Save optimizer state to JSON file."""
        state = {
            "version": "1.0",
            "created_at": self._created_at,
            "config": {
                "history_limit": self._history_limit,
                "trend_window": self._trend_window,
                "bottleneck_threshold": self._bottleneck_threshold,
                "dropoff_threshold": self._dropoff_threshold,
            },
            "records": {
                stage: [
                    {
                        "duration_ms": r.duration_ms,
                        "tasks_in": r.tasks_in,
                        "tasks_out": r.tasks_out,
                        "timestamp": r.timestamp,
                        "metadata": r.metadata,
                    }
                    for r in records
                ]
                for stage, records in self._records.items()
            },
            "pipeline_runs": list(self._pipeline_runs),
            "total_records": self._total_records,
            "total_pipeline_runs": self._total_pipeline_runs,
        }
        with open(path, "w") as f:
            json.dump(state, f, indent=2)
        logger.info(f"Saved PipelineOptimizer state to {path}")

    @classmethod
    def load(cls, path: str) -> "PipelineOptimizer":
        """Load optimizer state from JSON file."""
        with open(path) as f:
            state = json.load(f)

        config = state.get("config", {})
        optimizer = cls(
            history_limit=config.get("history_limit", DEFAULT_HISTORY_LIMIT),
            trend_window=config.get("trend_window", DEFAULT_TREND_WINDOW),
            bottleneck_threshold=config.get(
                "bottleneck_threshold", BOTTLENECK_THRESHOLD_PCT
            ),
            dropoff_threshold=config.get("dropoff_threshold", DROPOFF_ALERT_PCT),
        )

        optimizer._created_at = state.get("created_at", time.time())
        optimizer._total_records = state.get("total_records", 0)
        optimizer._total_pipeline_runs = state.get("total_pipeline_runs", 0)

        # Restore records
        for stage, records_data in state.get("records", {}).items():
            if stage in optimizer._records:
                for rd in records_data:
                    record = StageRecord(
                        stage=stage,
                        duration_ms=rd["duration_ms"],
                        tasks_in=rd["tasks_in"],
                        tasks_out=rd["tasks_out"],
                        timestamp=rd.get("timestamp", 0),
                        metadata=rd.get("metadata", {}),
                    )
                    optimizer._records[stage].append(record)

        # Restore pipeline runs
        for run in state.get("pipeline_runs", []):
            optimizer._pipeline_runs.append(run)

        logger.info(f"Loaded PipelineOptimizer state from {path}")
        return optimizer

    # ── Diagnostics ────────────────────────────────────────────

    def diagnostics(self) -> dict:
        """Full diagnostic dump."""
        return {
            "config": {
                "history_limit": self._history_limit,
                "trend_window": self._trend_window,
                "bottleneck_threshold": self._bottleneck_threshold,
                "dropoff_threshold": self._dropoff_threshold,
                "custom_analyzers": len(self._custom_analyzers),
            },
            "metrics": self.metrics(),
            "has_data": self.has_data(),
            "stages": PIPELINE_STAGES,
            "records_per_stage": {k: len(v) for k, v in self._records.items()},
            "pipeline_runs_count": len(self._pipeline_runs),
        }

    def reset(self):
        """Clear all recorded data."""
        for stage in self._records:
            self._records[stage].clear()
        self._pipeline_runs.clear()
        self._total_records = 0
        self._total_pipeline_runs = 0
        logger.info("PipelineOptimizer reset")

    # ── Internal: Profile Computation ──────────────────────────

    def _compute_profiles(self) -> Dict[str, StageProfile]:
        """Compute statistical profiles for all stages with data."""
        profiles = {}
        for stage in PIPELINE_STAGES:
            records = list(self._records[stage])
            if records:
                profiles[stage] = self._profile_from_records(stage, records)
        return profiles

    def _profile_from_records(
        self, stage: str, records: List[StageRecord]
    ) -> StageProfile:
        """Compute profile from a list of records."""
        durations = [r.duration_ms for r in records]
        sorted_d = sorted(durations)
        n = len(sorted_d)

        total_in = sum(r.tasks_in for r in records)
        total_out = sum(r.tasks_out for r in records)
        dropoff_rates = [r.dropoff_rate for r in records if r.tasks_in > 0]
        throughputs = [
            r.throughput for r in records if r.duration_ms > 0 and r.throughput != float("inf")
        ]

        profile = StageProfile(
            stage=stage,
            count=n,
            mean_ms=statistics.mean(durations),
            median_ms=statistics.median(durations),
            p90_ms=self._percentile(sorted_d, 0.90),
            p95_ms=self._percentile(sorted_d, 0.95),
            p99_ms=self._percentile(sorted_d, 0.99),
            min_ms=sorted_d[0],
            max_ms=sorted_d[-1],
            std_dev_ms=statistics.stdev(durations) if n > 1 else 0.0,
            total_tasks_in=total_in,
            total_tasks_out=total_out,
            avg_dropoff_rate=(
                statistics.mean(dropoff_rates) if dropoff_rates else 0.0
            ),
            avg_throughput=statistics.mean(throughputs) if throughputs else 0.0,
        )
        return profile

    @staticmethod
    def _percentile(sorted_values: List[float], pct: float) -> float:
        """Compute percentile from sorted values."""
        if not sorted_values:
            return 0.0
        n = len(sorted_values)
        if n == 1:
            return sorted_values[0]
        idx = pct * (n - 1)
        lower = int(math.floor(idx))
        upper = min(lower + 1, n - 1)
        frac = idx - lower
        return sorted_values[lower] + frac * (sorted_values[upper] - sorted_values[lower])

    # ── Internal: Bottleneck Detection ─────────────────────────

    def _detect_bottleneck(
        self, profiles: Dict[str, StageProfile]
    ) -> Tuple[Optional[str], float]:
        """Identify the bottleneck stage (highest latency share)."""
        if not profiles:
            return None, 0.0

        total_mean = sum(p.mean_ms for p in profiles.values())
        if total_mean <= 0:
            return None, 0.0

        # Compute latency shares
        shares = {}
        for stage, profile in profiles.items():
            share = profile.mean_ms / total_mean
            profile.latency_share = share
            shares[stage] = share

        # Find the stage with highest share
        bottleneck_stage = max(shares, key=shares.get)
        bottleneck_share = shares[bottleneck_stage]

        if bottleneck_share >= self._bottleneck_threshold:
            return bottleneck_stage, bottleneck_share

        return bottleneck_stage, bottleneck_share

    # ── Internal: Dropoff Detection ────────────────────────────

    def _detect_dropoff(self, profiles: Dict[str, StageProfile]) -> List[str]:
        """Identify stages with significant task loss."""
        dropoff_stages = []
        for stage, profile in profiles.items():
            if profile.avg_dropoff_rate >= self._dropoff_threshold:
                dropoff_stages.append(stage)
        return dropoff_stages

    # ── Internal: Trend Analysis ───────────────────────────────

    def _compute_trends(self) -> Dict[str, TrendResult]:
        """Compute trends for all stages with sufficient data."""
        trends = {}
        for stage in PIPELINE_STAGES:
            records = list(self._records[stage])
            if len(records) >= 4:  # Need at least 4 for meaningful split
                trend = self._trend_from_records(stage, records[-self._trend_window :])
                if trend:
                    trends[stage] = trend
        return trends

    def _trend_from_records(
        self, stage: str, records: List[StageRecord]
    ) -> Optional[TrendResult]:
        """Compute trend from a list of records by comparing halves."""
        if len(records) < 4:
            return TrendResult(
                stage=stage,
                direction=TrendDirection.INSUFFICIENT_DATA,
                baseline_ms=0.0,
                current_ms=0.0,
                change_pct=0.0,
                sample_count=len(records),
            )

        mid = len(records) // 2
        first_half = [r.duration_ms for r in records[:mid]]
        second_half = [r.duration_ms for r in records[mid:]]

        baseline = statistics.mean(first_half)
        current = statistics.mean(second_half)

        if baseline == 0:
            change_pct = 0.0
        else:
            change_pct = ((current - baseline) / baseline) * 100

        ratio = current / baseline if baseline > 0 else 1.0

        if ratio >= DEGRADATION_THRESHOLD:
            direction = TrendDirection.DEGRADING
        elif ratio <= IMPROVEMENT_THRESHOLD:
            direction = TrendDirection.IMPROVING
        else:
            direction = TrendDirection.STABLE

        return TrendResult(
            stage=stage,
            direction=direction,
            baseline_ms=baseline,
            current_ms=current,
            change_pct=change_pct,
            sample_count=len(records),
        )

    # ── Internal: Correlation Analysis ─────────────────────────

    def _compute_correlations(self) -> List[CorrelationResult]:
        """
        Compute pairwise Pearson correlations between adjacent stages.

        Adjacent stages often have correlated performance — e.g., slower
        chain routing may correlate with slower scoring (more candidates).
        """
        correlations = []
        for i in range(len(PIPELINE_STAGES) - 1):
            stage_a = PIPELINE_STAGES[i]
            stage_b = PIPELINE_STAGES[i + 1]
            records_a = list(self._records[stage_a])
            records_b = list(self._records[stage_b])

            # Need paired observations (matched by index)
            n = min(len(records_a), len(records_b))
            if n < 5:
                continue

            # Use the last n records from each
            vals_a = [r.duration_ms for r in records_a[-n:]]
            vals_b = [r.duration_ms for r in records_b[-n:]]

            coeff = self._pearson(vals_a, vals_b)
            interpretation = self._interpret_correlation(coeff, stage_a, stage_b)

            correlations.append(
                CorrelationResult(
                    stage_a=stage_a,
                    stage_b=stage_b,
                    coefficient=coeff,
                    sample_count=n,
                    interpretation=interpretation,
                )
            )

        return correlations

    @staticmethod
    def _pearson(x: List[float], y: List[float]) -> float:
        """Compute Pearson correlation coefficient."""
        n = len(x)
        if n < 2:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
        denom_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
        denom_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))

        if denom_x == 0 or denom_y == 0:
            return 0.0

        return numerator / (denom_x * denom_y)

    @staticmethod
    def _interpret_correlation(
        coeff: float, stage_a: str, stage_b: str
    ) -> str:
        """Human-readable interpretation of correlation."""
        abs_coeff = abs(coeff)
        if abs_coeff < 0.3:
            strength = "weak"
        elif abs_coeff < 0.7:
            strength = "moderate"
        else:
            strength = "strong"

        if coeff > 0:
            direction = "positive"
            meaning = f"When {stage_a} slows, {stage_b} tends to slow too"
        else:
            direction = "negative"
            meaning = f"When {stage_a} slows, {stage_b} tends to speed up"

        return f"{strength.capitalize()} {direction} correlation ({coeff:.2f}). {meaning}."

    # ── Internal: Suggestion Generation ────────────────────────

    def _generate_suggestions(
        self,
        profiles: Dict[str, StageProfile],
        bottleneck: Optional[str],
        dropoff_stages: List[str],
        trends: Dict[str, TrendResult],
    ) -> List[Suggestion]:
        """Generate optimization suggestions based on analysis."""
        suggestions = []

        # 1. Bottleneck-specific suggestions
        if bottleneck and bottleneck in profiles:
            bp = profiles[bottleneck]
            suggestions.append(
                Suggestion(
                    priority=SuggestionPriority.HIGH,
                    stage=bottleneck,
                    title=f"Optimize {bottleneck} stage (bottleneck)",
                    detail=self._bottleneck_advice(bottleneck, bp),
                    metric_before=bp.mean_ms,
                    metric_name="mean_latency_ms",
                    estimated_improvement=f"Reduce from {bp.mean_ms:.1f}ms to improve overall throughput",
                )
            )

        # 2. High-variability stages
        for stage, profile in profiles.items():
            if profile.count >= 5 and profile.std_dev_ms > profile.mean_ms:
                suggestions.append(
                    Suggestion(
                        priority=SuggestionPriority.MEDIUM,
                        stage=stage,
                        title=f"High variance in {stage} stage",
                        detail=(
                            f"Std dev ({profile.std_dev_ms:.1f}ms) exceeds mean "
                            f"({profile.mean_ms:.1f}ms). P99 is {profile.p99_ms:.1f}ms "
                            f"vs median {profile.median_ms:.1f}ms. Look for outlier "
                            f"conditions causing tail latency."
                        ),
                        metric_before=profile.std_dev_ms,
                        metric_name="std_dev_ms",
                    )
                )

        # 3. Dropoff alerts
        for stage in dropoff_stages:
            if stage in profiles:
                dp = profiles[stage]
                suggestions.append(
                    Suggestion(
                        priority=SuggestionPriority.HIGH,
                        stage=stage,
                        title=f"High task dropoff at {stage} ({dp.avg_dropoff_rate:.0%})",
                        detail=self._dropoff_advice(stage, dp),
                        metric_before=dp.avg_dropoff_rate,
                        metric_name="dropoff_rate",
                    )
                )

        # 4. Degradation alerts
        for stage, trend in trends.items():
            if trend.direction == TrendDirection.DEGRADING:
                suggestions.append(
                    Suggestion(
                        priority=SuggestionPriority.CRITICAL,
                        stage=stage,
                        title=f"{stage} stage degrading ({trend.change_pct:+.0f}%)",
                        detail=(
                            f"Performance has degraded from {trend.baseline_ms:.1f}ms "
                            f"to {trend.current_ms:.1f}ms ({trend.change_pct:+.0f}%). "
                            f"Investigate recent changes to {stage} configuration or "
                            f"upstream data quality."
                        ),
                        metric_before=trend.current_ms,
                        metric_name="current_mean_ms",
                    )
                )

        # 5. Low-throughput stages
        for stage, profile in profiles.items():
            if profile.avg_throughput > 0 and profile.avg_throughput < 10:
                suggestions.append(
                    Suggestion(
                        priority=SuggestionPriority.LOW,
                        stage=stage,
                        title=f"Low throughput at {stage} ({profile.avg_throughput:.1f} tasks/sec)",
                        detail=(
                            f"Consider parallelizing {stage} processing or reducing "
                            f"per-task compute cost."
                        ),
                        metric_before=profile.avg_throughput,
                        metric_name="throughput_tasks_per_sec",
                    )
                )

        # 6. Custom analyzers
        for analyzer in self._custom_analyzers:
            try:
                custom_suggestions = analyzer(self._records, profiles)
                if custom_suggestions:
                    suggestions.extend(custom_suggestions)
            except Exception as e:
                logger.warning(f"Custom analyzer failed: {e}")

        # Sort by priority
        priority_order = {
            SuggestionPriority.CRITICAL: 0,
            SuggestionPriority.HIGH: 1,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 3,
            SuggestionPriority.INFO: 4,
        }
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 99))

        return suggestions

    @staticmethod
    def _bottleneck_advice(stage: str, profile: StageProfile) -> str:
        """Stage-specific optimization advice for the bottleneck."""
        advice = {
            "batch": (
                f"BatchScheduler is consuming {profile.mean_ms:.1f}ms avg. "
                f"Consider reducing max batch size, simplifying hybrid strategy, "
                f"or pre-sorting tasks before batching."
            ),
            "validate": (
                f"TaskValidator is consuming {profile.mean_ms:.1f}ms avg. "
                f"Disable expensive rules (duplicate detection) or switch to "
                f"fail-fast mode for quicker rejection."
            ),
            "chain": (
                f"ChainRouter is consuming {profile.mean_ms:.1f}ms avg. "
                f"Cache chain profiles, reduce candidate chains, or use "
                f"pre-computed routing tables."
            ),
            "score": (
                f"SignalHarness is consuming {profile.mean_ms:.1f}ms avg. "
                f"Reduce active signals from 13 to top-8 by impact, or "
                f"implement lazy signal evaluation."
            ),
            "blend": (
                f"DecisionSynthesizer is consuming {profile.mean_ms:.1f}ms avg. "
                f"Simplify blending weights or reduce candidate pool size "
                f"before blending."
            ),
            "select": (
                f"FleetManager is consuming {profile.mean_ms:.1f}ms avg. "
                f"Optimize fleet index queries, reduce availability window "
                f"checks, or pre-filter by capability."
            ),
            "route": (
                f"CoordinatorPipeline is consuming {profile.mean_ms:.1f}ms avg. "
                f"Optimize audit trail generation, reduce logging verbosity, "
                f"or batch assignment writes."
            ),
        }
        return advice.get(stage, f"Stage {stage} is the bottleneck at {profile.mean_ms:.1f}ms avg.")

    @staticmethod
    def _dropoff_advice(stage: str, profile: StageProfile) -> str:
        """Stage-specific advice for high task dropoff."""
        advice = {
            "batch": (
                f"Tasks are being dropped during batching ({profile.avg_dropoff_rate:.0%}). "
                f"Check min batch size settings or singleton handling."
            ),
            "validate": (
                f"Validation is rejecting {profile.avg_dropoff_rate:.0%} of tasks. "
                f"Review bounty minimum, check if description length rules are too strict, "
                f"or if evidence type validation is catching legitimate types."
            ),
            "chain": (
                f"Chain routing is dropping {profile.avg_dropoff_rate:.0%} of tasks. "
                f"Ensure target networks are in the enabled list and chains aren't "
                f"marked degraded when they're actually healthy."
            ),
            "score": (
                f"Signal scoring is dropping {profile.avg_dropoff_rate:.0%} of tasks. "
                f"Check if signal thresholds are too aggressive or if candidate "
                f"pools are being exhausted."
            ),
            "blend": (
                f"Decision blending is dropping {profile.avg_dropoff_rate:.0%} of tasks. "
                f"Review minimum composite score thresholds."
            ),
            "select": (
                f"Fleet selection is dropping {profile.avg_dropoff_rate:.0%} of tasks. "
                f"Check agent availability windows, capacity limits, and "
                f"whether enough agents are registered."
            ),
            "route": (
                f"Final routing is dropping {profile.avg_dropoff_rate:.0%} of tasks. "
                f"Check for assignment conflicts or connectivity issues."
            ),
        }
        return advice.get(
            stage,
            f"Stage {stage} is dropping {profile.avg_dropoff_rate:.0%} of tasks.",
        )

    # ── Internal: Overall Metrics ──────────────────────────────

    def _compute_overall_throughput(self) -> float:
        """Compute overall pipeline throughput from pipeline runs."""
        if not self._pipeline_runs:
            # Estimate from route stage
            route_records = list(self._records["route"])
            if not route_records:
                return 0.0
            total_tasks = sum(r.tasks_out for r in route_records)
            total_time_ms = sum(r.duration_ms for r in route_records)
            if total_time_ms <= 0:
                return 0.0
            return (total_tasks / total_time_ms) * 1000

        recent = list(self._pipeline_runs)[-50:]
        total_tasks = sum(r["tasks_routed"] for r in recent)
        total_time_ms = sum(r["total_duration_ms"] for r in recent)
        if total_time_ms <= 0:
            return 0.0
        return (total_tasks / total_time_ms) * 1000

    def _compute_overall_latency(self) -> float:
        """Compute end-to-end pipeline latency."""
        if self._pipeline_runs:
            recent = list(self._pipeline_runs)[-50:]
            return statistics.mean(r["total_duration_ms"] for r in recent)

        # Sum mean latencies across stages
        total = 0.0
        for stage in PIPELINE_STAGES:
            records = list(self._records[stage])
            if records:
                total += statistics.mean(r.duration_ms for r in records)
        return total

    def _compute_health_score(
        self,
        profiles: Dict[str, StageProfile],
        bottleneck_share: float,
        dropoff_stages: List[str],
        trends: Dict[str, TrendResult],
    ) -> float:
        """
        Compute a 0-100 health score for the pipeline.

        Factors:
        - Bottleneck concentration (deduct for >50%)
        - Dropoff stages (deduct per stage)
        - Degrading trends (deduct per stage)
        - Variance (deduct for high variance)
        """
        score = 100.0

        # Bottleneck penalty: up to -20 points
        if bottleneck_share > 0.5:
            score -= min(20, (bottleneck_share - 0.5) * 40)

        # Dropoff penalty: -10 per high-dropoff stage
        score -= len(dropoff_stages) * 10

        # Degradation penalty: -15 per degrading stage
        degrading = sum(
            1 for t in trends.values() if t.direction == TrendDirection.DEGRADING
        )
        score -= degrading * 15

        # Variance penalty: -5 per high-variance stage
        high_var = sum(
            1
            for p in profiles.values()
            if p.count >= 5 and p.std_dev_ms > p.mean_ms
        )
        score -= high_var * 5

        # Improvement bonus: +5 per improving stage
        improving = sum(
            1 for t in trends.values() if t.direction == TrendDirection.IMPROVING
        )
        score += improving * 5

        return max(0.0, min(100.0, score))
