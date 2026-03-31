"""
WorkloadBridge — Connects EM task history to demand forecasting intelligence.

Module #63 in the swarm architecture.

Bridges the gap between EM's tasks table (server-side data) and
AutoJob's WorkloadForecaster (client-side Signal #15). The bridge:

1. Fetches task creation history from Supabase on demand or on schedule
2. Converts task rows into the format WorkloadForecaster expects
3. Caches demand forecasts for quick routing lookups
4. Generates capacity gap and pricing pressure signals
5. Detects demand spikes in real-time

This module enables the swarm coordinator to use workload intelligence
as Signal #15 without direct AutoJob dependency.

Usage:
    bridge = WorkloadBridge()
    await bridge.sync()  # Pull latest task history

    forecast = bridge.demand_forecast(horizon_hours=24)
    gap = bridge.capacity_gap(available_workers=10)
    signal = bridge.routing_signal(available_workers=10)
    spikes = bridge.active_spikes()
"""

import logging
import math
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("em.swarm.workload_bridge")

UTC = timezone.utc

# Default categories (mirrors AutoJob)
DEFAULT_CATEGORIES = [
    "physical_verification",
    "delivery",
    "digital_task",
    "data_collection",
    "content_creation",
    "research",
    "translation",
    "testing",
    "other",
]

# Minimum data points for forecasting
MIN_TASKS_FOR_FORECAST = 5
MIN_TASKS_FOR_SEASONAL = 14

# Exponential moving average alpha
EMA_ALPHA = 0.3

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────

@dataclass
class WorkloadConfig:
    """Configuration for the WorkloadBridge."""
    sync_interval_seconds: int = 300  # 5 minutes
    max_tasks: int = 10000
    cache_ttl_seconds: int = 60
    ema_alpha: float = EMA_ALPHA
    spike_threshold_sigma: float = 2.0
    capacity_buffer_pct: float = 0.20
    tasks_per_worker_per_day: float = 2.0
    enable_spike_detection: bool = True
    enable_seasonal_analysis: bool = True
    lookback_days: int = 30  # How far back to fetch tasks


# ──────────────────────────────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────────────────────────────

@dataclass
class DemandForecast:
    """Predicted demand over a time horizon."""
    horizon_hours: float
    predicted_tasks: float
    confidence_low: float
    confidence_high: float
    peak_hour: int
    dominant_category: str
    category_breakdown: Dict[str, float]
    trend: str  # "accelerating", "steady", "decelerating", "insufficient_data"
    seasonal_factor: float
    data_points_used: int

    def to_dict(self) -> dict:
        return {
            "horizon_hours": self.horizon_hours,
            "predicted_tasks": round(self.predicted_tasks, 2),
            "confidence_interval": [round(self.confidence_low, 2), round(self.confidence_high, 2)],
            "peak_hour": self.peak_hour,
            "dominant_category": self.dominant_category,
            "category_breakdown": {k: round(v, 2) for k, v in self.category_breakdown.items()},
            "trend": self.trend,
            "seasonal_factor": round(self.seasonal_factor, 3),
            "data_points_used": self.data_points_used,
        }


@dataclass
class CapacityGap:
    """Supply vs demand analysis."""
    predicted_demand: float
    available_workers: int
    surplus_or_deficit: float
    utilization_pct: float
    pricing_pressure: str  # "low", "moderate", "high", "critical"
    suggested_bounty_adj: float
    recommended_workers: int
    category_gaps: Dict[str, float]

    def to_dict(self) -> dict:
        return {
            "predicted_demand": round(self.predicted_demand, 2),
            "available_workers": self.available_workers,
            "surplus_or_deficit": round(self.surplus_or_deficit, 2),
            "utilization_pct": round(self.utilization_pct, 3),
            "pricing_pressure": self.pricing_pressure,
            "suggested_bounty_adj": round(self.suggested_bounty_adj, 3),
            "recommended_workers": self.recommended_workers,
            "category_gaps": {k: round(v, 2) for k, v in self.category_gaps.items()},
        }


@dataclass
class DemandSpike:
    """Detected demand spike."""
    detected_at: datetime
    category: str
    current_rate: float
    baseline_rate: float
    spike_magnitude: float
    predicted_duration_hours: float
    confidence: float

    def to_dict(self) -> dict:
        return {
            "detected_at": self.detected_at.isoformat(),
            "category": self.category,
            "current_rate": round(self.current_rate, 2),
            "baseline_rate": round(self.baseline_rate, 2),
            "spike_magnitude": round(self.spike_magnitude, 2),
            "predicted_duration_hours": round(self.predicted_duration_hours, 1),
            "confidence": round(self.confidence, 3),
        }


@dataclass
class WorkloadRoutingSignal:
    """Routing intelligence output (Signal #15)."""
    demand_trend: str
    demand_level: str
    tasks_per_hour: float
    forecast_24h: float
    active_spikes: List[DemandSpike]
    pricing_pressure: str
    suggested_bounty_adj: float
    category_hotspots: List[str]
    optimal_posting_hours: List[int]
    seasonal_factor: float

    def to_dict(self) -> dict:
        return {
            "demand_trend": self.demand_trend,
            "demand_level": self.demand_level,
            "tasks_per_hour": round(self.tasks_per_hour, 2),
            "forecast_24h": round(self.forecast_24h, 2),
            "active_spikes": [s.to_dict() for s in self.active_spikes],
            "pricing_pressure": self.pricing_pressure,
            "suggested_bounty_adj": round(self.suggested_bounty_adj, 3),
            "category_hotspots": self.category_hotspots,
            "optimal_posting_hours": self.optimal_posting_hours,
            "seasonal_factor": round(self.seasonal_factor, 3),
        }


@dataclass
class _TaskEntry:
    """Internal minimal task representation."""
    task_id: str
    created_at: datetime
    category: str
    bounty_usd: float
    status: str


# ──────────────────────────────────────────────────────────────────────
# WorkloadBridge
# ──────────────────────────────────────────────────────────────────────

class WorkloadBridge:
    """
    Server-side demand forecasting intelligence for the swarm.

    Reads task creation history from Supabase and produces demand
    forecasts, capacity gap analysis, and spike detection — feeding
    Signal #15 into the routing pipeline.

    Module #63 in the swarm architecture.
    """

    def __init__(self, config: Optional[WorkloadConfig] = None):
        self._config = config or WorkloadConfig()

        # Task storage
        self._tasks: List[_TaskEntry] = []
        self._hourly_counts: Dict[str, int] = defaultdict(int)
        self._daily_counts: Dict[str, int] = defaultdict(int)
        self._category_hourly: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._category_daily: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # State
        self._last_sync: Optional[float] = None
        self._sync_count: int = 0
        self._spike_history: List[DemandSpike] = []

        # Cache
        self._forecast_cache: Dict[str, Tuple[float, DemandForecast]] = {}

        logger.info(
            "WorkloadBridge initialized (alpha=%.2f, lookback=%dd)",
            self._config.ema_alpha,
            self._config.lookback_days,
        )

    # ── Sync ─────────────────────────────────────────────────────

    async def sync(self, force: bool = False) -> int:
        """Sync task history from Supabase.

        Args:
            force: Force sync even if interval hasn't elapsed

        Returns:
            Number of tasks synced
        """
        now = time.monotonic()
        if (
            not force
            and self._last_sync is not None
            and (now - self._last_sync) < self._config.sync_interval_seconds
        ):
            return 0

        try:
            import supabase_client as db
            client = db.get_client()

            cutoff = (datetime.now(UTC) - timedelta(days=self._config.lookback_days)).isoformat()

            resp = (
                client.table("tasks")
                .select("id, created_at, category, bounty_usd, status")
                .gte("created_at", cutoff)
                .order("created_at", desc=False)
                .limit(self._config.max_tasks)
                .execute()
            )

            rows = resp.data if resp.data else []
            self._ingest_rows(rows)

            self._last_sync = now
            self._sync_count += 1
            logger.info(
                "WorkloadBridge sync #%d: %d tasks from last %d days",
                self._sync_count, len(rows), self._config.lookback_days,
            )
            return len(rows)

        except Exception as e:
            logger.warning("WorkloadBridge sync failed: %s", e)
            return 0

    def _ingest_rows(self, rows: List[Dict[str, Any]]) -> int:
        """Ingest raw Supabase rows into internal tracking."""
        # Clear existing data for full refresh
        self._tasks.clear()
        self._hourly_counts.clear()
        self._daily_counts.clear()
        self._category_hourly.clear()
        self._category_daily.clear()

        ingested = 0
        for row in rows:
            entry = self._parse_row(row)
            if entry:
                self._add_entry(entry)
                ingested += 1

        # Clear forecast cache after sync
        self._forecast_cache.clear()

        return ingested

    def ingest_rows(self, rows: List[Dict[str, Any]]) -> int:
        """Public API for ingesting task rows (testing/direct use)."""
        return self._ingest_rows(rows)

    def _parse_row(self, row: Dict[str, Any]) -> Optional[_TaskEntry]:
        """Parse a Supabase row into a _TaskEntry."""
        task_id = row.get("id") or row.get("task_id")
        if not task_id:
            return None

        created_at = row.get("created_at")
        if isinstance(created_at, str):
            created_at = created_at.replace("Z", "+00:00")
            try:
                created_at = datetime.fromisoformat(created_at)
            except (ValueError, TypeError):
                return None
        elif not isinstance(created_at, datetime):
            return None

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        category = str(row.get("category", "other")).lower().strip()
        if category not in DEFAULT_CATEGORIES:
            category = "other"

        return _TaskEntry(
            task_id=str(task_id),
            created_at=created_at,
            category=category,
            bounty_usd=float(row.get("bounty_usd", 0)),
            status=str(row.get("status", "open")),
        )

    def _add_entry(self, entry: _TaskEntry) -> None:
        """Add a task entry to all tracking structures."""
        self._tasks.append(entry)

        hour_key = entry.created_at.strftime("%Y-%m-%d-%H")
        self._hourly_counts[hour_key] += 1
        self._category_hourly[entry.category][hour_key] += 1

        day_key = entry.created_at.strftime("%Y-%m-%d")
        self._daily_counts[day_key] += 1
        self._category_daily[entry.category][day_key] += 1

    # ── Demand Forecasting ───────────────────────────────────────

    def demand_forecast(
        self,
        horizon_hours: float = 24,
        now: Optional[datetime] = None,
    ) -> DemandForecast:
        """Forecast task demand over the given horizon.

        Uses EMA of hourly rates, adjusted by seasonal patterns.
        """
        if now is None:
            now = datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        n = len(self._tasks)
        if n < MIN_TASKS_FOR_FORECAST:
            return DemandForecast(
                horizon_hours=horizon_hours,
                predicted_tasks=0.0,
                confidence_low=0.0,
                confidence_high=0.0,
                peak_hour=12,
                dominant_category="other",
                category_breakdown={},
                trend="insufficient_data",
                seasonal_factor=1.0,
                data_points_used=n,
            )

        hourly_rate = self._ema_hourly_rate()
        seasonal = self._seasonal_factor(now)
        adjusted_rate = hourly_rate * seasonal
        predicted = adjusted_rate * horizon_hours

        std_dev = self._hourly_stddev()
        margin = 1.96 * std_dev * math.sqrt(max(horizon_hours, 0.01))
        confidence_low = max(0.0, predicted - margin)
        confidence_high = predicted + margin

        cat_breakdown = self._category_forecast(horizon_hours, now)
        peak_hour = self._find_peak_hour()
        dominant = max(cat_breakdown.items(), key=lambda x: x[1])[0] if cat_breakdown else "other"
        trend = self._detect_trend()

        return DemandForecast(
            horizon_hours=horizon_hours,
            predicted_tasks=predicted,
            confidence_low=confidence_low,
            confidence_high=confidence_high,
            peak_hour=peak_hour,
            dominant_category=dominant,
            category_breakdown=cat_breakdown,
            trend=trend,
            seasonal_factor=seasonal,
            data_points_used=n,
        )

    def forecast_category(
        self,
        category: str,
        horizon_hours: float = 24,
        now: Optional[datetime] = None,
    ) -> DemandForecast:
        """Forecast demand for a specific category."""
        if now is None:
            now = datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        category = category.lower().strip()
        cat_tasks = [t for t in self._tasks if t.category == category]
        n = len(cat_tasks)

        if n < MIN_TASKS_FOR_FORECAST:
            return DemandForecast(
                horizon_hours=horizon_hours,
                predicted_tasks=0.0,
                confidence_low=0.0,
                confidence_high=0.0,
                peak_hour=12,
                dominant_category=category,
                category_breakdown={category: 0.0},
                trend="insufficient_data",
                seasonal_factor=1.0,
                data_points_used=n,
            )

        hourly_rate = self._ema_category_rate(category)
        seasonal = self._seasonal_factor(now)
        predicted = hourly_rate * seasonal * horizon_hours

        cat_hourly = self._category_hourly.get(category, {})
        values = list(cat_hourly.values())
        std_dev = statistics.stdev(values) if len(values) >= 2 else 0
        margin = 1.96 * std_dev * math.sqrt(max(horizon_hours, 0.01))

        return DemandForecast(
            horizon_hours=horizon_hours,
            predicted_tasks=predicted,
            confidence_low=max(0.0, predicted - margin),
            confidence_high=predicted + margin,
            peak_hour=self._peak_hour_for_category(category),
            dominant_category=category,
            category_breakdown={category: predicted},
            trend=self._category_trend(category),
            seasonal_factor=seasonal,
            data_points_used=n,
        )

    # ── Capacity Gap ─────────────────────────────────────────────

    def capacity_gap(
        self,
        available_workers: int,
        horizon_hours: float = 24,
        workers_per_category: Optional[Dict[str, int]] = None,
        now: Optional[datetime] = None,
    ) -> CapacityGap:
        """Analyze gap between predicted demand and available workforce."""
        forecast = self.demand_forecast(horizon_hours=horizon_hours, now=now)

        tpw = self._config.tasks_per_worker_per_day
        worker_capacity = available_workers * tpw * (horizon_hours / 24.0)

        surplus = worker_capacity - forecast.predicted_tasks
        utilization = forecast.predicted_tasks / max(worker_capacity, 0.01)

        if utilization < 0.5:
            pricing_pressure = "low"
            bounty_adj = -0.10
        elif utilization < 0.8:
            pricing_pressure = "moderate"
            bounty_adj = 0.0
        elif utilization < 1.0:
            pricing_pressure = "high"
            bounty_adj = 0.15
        else:
            pricing_pressure = "critical"
            bounty_adj = min(0.50, 0.10 * (utilization - 1.0) + 0.20)

        recommended = math.ceil(
            forecast.predicted_tasks
            / max(tpw * (horizon_hours / 24.0), 0.01)
            * (1 + self._config.capacity_buffer_pct)
        )

        category_gaps = {}
        if workers_per_category and forecast.category_breakdown:
            for cat, demand in forecast.category_breakdown.items():
                cw = workers_per_category.get(cat, 0)
                category_gaps[cat] = cw * tpw * (horizon_hours / 24.0) - demand
        elif forecast.category_breakdown:
            total_demand = max(sum(forecast.category_breakdown.values()), 0.01)
            for cat, demand in forecast.category_breakdown.items():
                proportion = demand / total_demand
                cat_cap = available_workers * proportion * tpw * (horizon_hours / 24.0)
                category_gaps[cat] = cat_cap - demand

        return CapacityGap(
            predicted_demand=forecast.predicted_tasks,
            available_workers=available_workers,
            surplus_or_deficit=surplus,
            utilization_pct=utilization,
            pricing_pressure=pricing_pressure,
            suggested_bounty_adj=bounty_adj,
            recommended_workers=recommended,
            category_gaps=category_gaps,
        )

    # ── Spike Detection ──────────────────────────────────────────

    def detect_spikes(
        self,
        window_hours: float = 4,
        now: Optional[datetime] = None,
    ) -> List[DemandSpike]:
        """Detect current demand spikes."""
        if not self._config.enable_spike_detection:
            return []
        if len(self._tasks) < MIN_TASKS_FOR_FORECAST:
            return []

        if now is None:
            now = datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        spikes = []

        overall = self._check_spike("all", window_hours, now)
        if overall:
            spikes.append(overall)

        for cat in set(t.category for t in self._tasks):
            cat_spike = self._check_spike(cat, window_hours, now)
            if cat_spike:
                spikes.append(cat_spike)

        self._spike_history.extend(spikes)
        if len(self._spike_history) > 100:
            self._spike_history = self._spike_history[-100:]

        return spikes

    def active_spikes(self, now: Optional[datetime] = None) -> List[Dict]:
        """Get currently active spikes (convenience method)."""
        spikes = self.detect_spikes(now=now)
        return [s.to_dict() for s in spikes]

    def _check_spike(self, category: str, window_hours: float, now: datetime) -> Optional[DemandSpike]:
        tasks = self._tasks if category == "all" else [t for t in self._tasks if t.category == category]
        if len(tasks) < MIN_TASKS_FOR_FORECAST:
            return None

        window_start = now - timedelta(hours=window_hours)
        recent = [t for t in tasks if t.created_at >= window_start]
        recent_rate = len(recent) / max(window_hours, 0.01)

        if len(tasks) >= 2:
            span = (tasks[-1].created_at - tasks[0].created_at).total_seconds() / 3600
            baseline_rate = len(tasks) / max(span, 0.01)
        else:
            baseline_rate = 0.0

        if baseline_rate <= 0:
            return None

        hourly_counts: Dict[str, int] = defaultdict(int)
        for t in tasks:
            hourly_counts[t.created_at.strftime("%Y-%m-%d-%H")] += 1
        rates = list(hourly_counts.values())

        if len(rates) < 3:
            return None

        std_dev = statistics.stdev(rates) if len(rates) >= 2 else 0
        if std_dev <= 0:
            return None

        sigma = (recent_rate - baseline_rate) / std_dev

        if sigma >= self._config.spike_threshold_sigma:
            return DemandSpike(
                detected_at=now,
                category=category,
                current_rate=recent_rate,
                baseline_rate=baseline_rate,
                spike_magnitude=sigma,
                predicted_duration_hours=window_hours * 2,
                confidence=min(1.0, 0.5 + 0.1 * len(recent)),
            )

        return None

    # ── Routing Signal ───────────────────────────────────────────

    def routing_signal(
        self,
        available_workers: int = 10,
        now: Optional[datetime] = None,
    ) -> WorkloadRoutingSignal:
        """Generate Signal #15 for the swarm routing pipeline."""
        if now is None:
            now = datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        forecast = self.demand_forecast(horizon_hours=24, now=now)
        gap = self.capacity_gap(available_workers, horizon_hours=24, now=now)
        spikes = self.detect_spikes(window_hours=4, now=now)

        current_rate = self._ema_hourly_rate()

        if current_rate <= 0.5:
            demand_level = "low"
        elif current_rate <= 2.0:
            demand_level = "moderate"
        elif current_rate <= 5.0 and not spikes:
            demand_level = "high"
        else:
            demand_level = "spike" if spikes else "high"

        cat_forecast = forecast.category_breakdown
        if cat_forecast:
            avg = sum(cat_forecast.values()) / max(len(cat_forecast), 1)
            hotspots = [c for c, d in cat_forecast.items() if d > avg * 1.5]
        else:
            hotspots = []

        # Optimal posting hours
        seasonal = self._detect_seasonal_patterns()
        if seasonal:
            sorted_hours = sorted(seasonal.items(), key=lambda x: x[1], reverse=True)
            optimal = [(h - 2) % 24 for h, _ in sorted_hours[:4]]
        else:
            optimal = [9, 10, 13, 14]

        return WorkloadRoutingSignal(
            demand_trend=forecast.trend,
            demand_level=demand_level,
            tasks_per_hour=current_rate,
            forecast_24h=forecast.predicted_tasks,
            active_spikes=spikes,
            pricing_pressure=gap.pricing_pressure,
            suggested_bounty_adj=gap.suggested_bounty_adj,
            category_hotspots=hotspots,
            optimal_posting_hours=optimal,
            seasonal_factor=forecast.seasonal_factor,
        )

    # ── Health / Diagnostics ─────────────────────────────────────

    def health(self) -> Dict[str, Any]:
        """Health check for the workload bridge."""
        stale = False
        if self._last_sync is not None:
            age = time.monotonic() - self._last_sync
            stale = age > self._config.sync_interval_seconds * 3

        return {
            "module": "workload_bridge",
            "module_number": 63,
            "status": "degraded" if stale else "healthy",
            "total_tasks": len(self._tasks),
            "categories": len(set(t.category for t in self._tasks)),
            "hourly_buckets": len(self._hourly_counts),
            "daily_buckets": len(self._daily_counts),
            "sync_count": self._sync_count,
            "stale": stale,
            "spike_history": len(self._spike_history),
            "config": {
                "sync_interval": self._config.sync_interval_seconds,
                "lookback_days": self._config.lookback_days,
                "spike_detection": self._config.enable_spike_detection,
            },
        }

    def status(self) -> str:
        """Human-readable status string."""
        h = self.health()
        lines = [
            f"WorkloadBridge (Module #63): {h['status']}",
            f"  Tasks: {h['total_tasks']} across {h['categories']} categories",
            f"  Syncs: {h['sync_count']}",
            f"  Spikes detected: {h['spike_history']}",
        ]
        return "\n".join(lines)

    # ── Internal Helpers ─────────────────────────────────────────

    def _ema_hourly_rate(self) -> float:
        if not self._hourly_counts:
            return 0.0
        rates = [v for _, v in sorted(self._hourly_counts.items())]
        if not rates:
            return 0.0
        ema = float(rates[0])
        alpha = self._config.ema_alpha
        for r in rates[1:]:
            ema = alpha * r + (1 - alpha) * ema
        return ema

    def _ema_category_rate(self, category: str) -> float:
        cat_hourly = self._category_hourly.get(category, {})
        if not cat_hourly:
            return 0.0
        rates = [v for _, v in sorted(cat_hourly.items())]
        if not rates:
            return 0.0
        ema = float(rates[0])
        alpha = self._config.ema_alpha
        for r in rates[1:]:
            ema = alpha * r + (1 - alpha) * ema
        return ema

    def _hourly_stddev(self) -> float:
        rates = [v for _, v in sorted(self._hourly_counts.items())]
        if len(rates) < 2:
            return 0.0
        return statistics.stdev(rates)

    def _seasonal_factor(self, now: datetime) -> float:
        if len(self._tasks) < MIN_TASKS_FOR_SEASONAL:
            return 1.0
        patterns_hourly = self._detect_seasonal_patterns()
        if not patterns_hourly:
            return 1.0

        hourly_factor = patterns_hourly.get(now.hour, 1.0)

        day_counts: Dict[int, int] = defaultdict(int)
        for t in self._tasks:
            day_counts[t.created_at.weekday()] += 1
        total = sum(day_counts.values())
        mean_daily = total / 7 if total > 0 else 1
        daily_factor = day_counts.get(now.weekday(), 0) / max(mean_daily, 0.01)

        combined = math.sqrt(max(hourly_factor, 0.01) * max(daily_factor, 0.01))
        return max(0.1, min(5.0, combined))

    def _detect_seasonal_patterns(self) -> Optional[Dict[int, float]]:
        """Return hourly factors dict or None."""
        if len(self._tasks) < MIN_TASKS_FOR_SEASONAL:
            return None
        hour_counts: Dict[int, int] = defaultdict(int)
        for t in self._tasks:
            hour_counts[t.created_at.hour] += 1
        total = sum(hour_counts.values())
        mean = total / 24 if total > 0 else 1
        return {h: hour_counts.get(h, 0) / max(mean, 0.01) for h in range(24)}

    def _category_forecast(self, horizon_hours: float, now: datetime) -> Dict[str, float]:
        breakdown = {}
        for cat in set(t.category for t in self._tasks):
            rate = self._ema_category_rate(cat)
            seasonal = self._seasonal_factor(now)
            breakdown[cat] = rate * seasonal * horizon_hours
        return breakdown

    def _find_peak_hour(self) -> int:
        hour_counts: Dict[int, int] = defaultdict(int)
        for t in self._tasks:
            hour_counts[t.created_at.hour] += 1
        if not hour_counts:
            return 12
        return max(hour_counts.items(), key=lambda x: x[1])[0]

    def _peak_hour_for_category(self, category: str) -> int:
        hour_counts: Dict[int, int] = defaultdict(int)
        for t in self._tasks:
            if t.category == category:
                hour_counts[t.created_at.hour] += 1
        if not hour_counts:
            return 12
        return max(hour_counts.items(), key=lambda x: x[1])[0]

    def _detect_trend(self) -> str:
        if len(self._daily_counts) < 3:
            return "insufficient_data"
        values = [v for _, v in sorted(self._daily_counts.items())]
        if len(values) < 3:
            return "insufficient_data"
        mid = len(values) // 2
        older = statistics.mean(values[:mid])
        newer = statistics.mean(values[mid:])
        if older == 0:
            return "accelerating" if newer > 0 else "steady"
        ratio = newer / older
        if ratio > 1.20:
            return "accelerating"
        elif ratio < 0.80:
            return "decelerating"
        return "steady"

    def _category_trend(self, category: str) -> str:
        cat_daily = self._category_daily.get(category, {})
        if len(cat_daily) < 3:
            return "insufficient_data"
        values = [v for _, v in sorted(cat_daily.items())]
        if len(values) < 3:
            return "insufficient_data"
        mid = len(values) // 2
        older = statistics.mean(values[:mid])
        newer = statistics.mean(values[mid:])
        if older == 0:
            return "accelerating" if newer > 0 else "steady"
        ratio = newer / older
        if ratio > 1.20:
            return "accelerating"
        elif ratio < 0.80:
            return "decelerating"
        return "steady"
