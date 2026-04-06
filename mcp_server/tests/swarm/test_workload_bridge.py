"""
Tests for WorkloadBridge — Server-side demand forecasting (Module #63).

Coverage:
1. Initialization & Configuration
2. Row Ingestion & Parsing
3. Demand Forecasting (overall and per-category)
4. Capacity Gap Analysis
5. Spike Detection
6. Routing Signal (Signal #15)
7. Health & Diagnostics
8. Seasonal Pattern Detection
9. Trend Detection
10. Edge Cases
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List

import pytest

import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from swarm.workload_bridge import (
    WorkloadBridge,
    WorkloadConfig,
    DemandSpike,
    WorkloadRoutingSignal,
    DEFAULT_CATEGORIES,
    MIN_TASKS_FOR_SEASONAL,
)

UTC = timezone.utc


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


def make_row(
    task_id: str = "task_001",
    hours_ago: float = 0,
    category: str = "physical_verification",
    bounty: float = 5.0,
    status: str = "open",
    now: datetime = None,
) -> Dict:
    if now is None:
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
    created = now - timedelta(hours=hours_ago)
    return {
        "id": task_id,
        "created_at": created.isoformat(),
        "category": category,
        "bounty_usd": bounty,
        "status": status,
    }


def make_history(
    n: int = 50,
    spread_hours: float = 168,
    categories: List[str] = None,
    now: datetime = None,
) -> List[Dict]:
    if now is None:
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
    if categories is None:
        categories = ["physical_verification", "delivery", "data_collection"]

    rows = []
    for i in range(n):
        hours_ago = spread_hours * (n - i) / n
        cat = categories[i % len(categories)]
        rows.append(
            make_row(
                task_id=f"task_{i:04d}",
                hours_ago=hours_ago,
                category=cat,
                bounty=3.0 + (i % 5),
                now=now,
            )
        )
    return rows


def make_seasonal_history(
    weeks: int = 3, tasks_per_day: int = 5, now: datetime = None
) -> List[Dict]:
    if now is None:
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
    rows = []
    task_id = 0
    categories = DEFAULT_CATEGORIES[:4]
    for week in range(weeks):
        for day in range(7):
            day_tasks = tasks_per_day if day < 5 else max(1, tasks_per_day // 3)
            for t in range(day_tasks):
                hours_ago = (weeks - week) * 168 + (6 - day) * 24 + (24 - t * 3)
                hour_offset = 9 + (t * 2) % 8
                hours_ago = hours_ago - 12 + hour_offset
                rows.append(
                    make_row(
                        task_id=f"seasonal_{task_id:04d}",
                        hours_ago=max(0.1, hours_ago),
                        category=categories[task_id % len(categories)],
                        bounty=2.0 + (task_id % 8),
                        now=now,
                    )
                )
                task_id += 1
    return rows


@pytest.fixture
def bridge():
    return WorkloadBridge()


@pytest.fixture
def loaded_bridge():
    now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
    b = WorkloadBridge()
    b.ingest_rows(make_history(50, now=now))
    return b


@pytest.fixture
def seasonal_bridge():
    now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
    b = WorkloadBridge()
    b.ingest_rows(make_seasonal_history(weeks=3, now=now))
    return b


# ──────────────────────────────────────────────────────────────────────
# 1. Initialization & Configuration
# ──────────────────────────────────────────────────────────────────────


class TestInitialization:
    def test_default_config(self, bridge):
        h = bridge.health()
        assert h["module"] == "workload_bridge"
        assert h["module_number"] == 63
        assert h["total_tasks"] == 0

    def test_custom_config(self):
        config = WorkloadConfig(
            sync_interval_seconds=60,
            lookback_days=7,
            ema_alpha=0.5,
        )
        b = WorkloadBridge(config=config)
        assert b._config.sync_interval_seconds == 60
        assert b._config.lookback_days == 7
        assert b._config.ema_alpha == 0.5

    def test_initial_state(self, bridge):
        assert len(bridge._tasks) == 0
        assert bridge._last_sync is None
        assert bridge._sync_count == 0

    def test_status_string(self, bridge):
        s = bridge.status()
        assert "WorkloadBridge" in s
        assert "Module #63" in s


# ──────────────────────────────────────────────────────────────────────
# 2. Row Ingestion & Parsing
# ──────────────────────────────────────────────────────────────────────


class TestIngestion:
    def test_ingest_empty(self, bridge):
        assert bridge.ingest_rows([]) == 0

    def test_ingest_single(self, bridge):
        assert bridge.ingest_rows([make_row()]) == 1
        assert len(bridge._tasks) == 1

    def test_ingest_batch(self, bridge):
        rows = make_history(20)
        assert bridge.ingest_rows(rows) == 20
        assert len(bridge._tasks) == 20

    def test_ingest_replaces_previous(self, bridge):
        bridge.ingest_rows(make_history(10))
        assert len(bridge._tasks) == 10
        bridge.ingest_rows(make_history(5))
        assert len(bridge._tasks) == 5  # Full refresh, not append

    def test_invalid_row_skipped(self, bridge):
        rows = [
            make_row(task_id="good"),
            {"invalid": True},
            make_row(task_id="good2"),
        ]
        assert bridge.ingest_rows(rows) == 2

    def test_no_id_skipped(self, bridge):
        assert bridge.ingest_rows([{"created_at": "2026-03-31T12:00:00Z"}]) == 0

    def test_no_date_skipped(self, bridge):
        assert bridge.ingest_rows([{"id": "no_date"}]) == 0

    def test_z_suffix_handled(self, bridge):
        row = {
            "id": "z_test",
            "created_at": "2026-03-30T10:00:00Z",
            "category": "delivery",
        }
        assert bridge.ingest_rows([row]) == 1

    def test_unknown_category_becomes_other(self, bridge):
        row = make_row(category="alien_task")
        bridge.ingest_rows([row])
        assert bridge._tasks[0].category == "other"

    def test_hourly_counts_populated(self, bridge):
        bridge.ingest_rows(make_history(10))
        assert len(bridge._hourly_counts) > 0

    def test_daily_counts_populated(self, bridge):
        bridge.ingest_rows(make_history(10))
        assert len(bridge._daily_counts) > 0

    def test_category_tracking(self, bridge):
        bridge.ingest_rows(make_history(10))
        assert len(bridge._category_hourly) > 0

    def test_task_id_alias(self, bridge):
        row = {"task_id": "alt_id", "created_at": "2026-03-30T10:00:00+00:00"}
        assert bridge.ingest_rows([row]) == 1
        assert bridge._tasks[0].task_id == "alt_id"


# ──────────────────────────────────────────────────────────────────────
# 3. Demand Forecasting
# ──────────────────────────────────────────────────────────────────────


class TestDemandForecast:
    def test_insufficient_data(self, bridge):
        bridge.ingest_rows(make_history(3))
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = bridge.demand_forecast(now=now)
        assert f.trend == "insufficient_data"
        assert f.predicted_tasks == 0.0

    def test_basic_forecast(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = loaded_bridge.demand_forecast(horizon_hours=24, now=now)
        assert f.predicted_tasks > 0
        assert f.data_points_used == 50

    def test_confidence_interval(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = loaded_bridge.demand_forecast(horizon_hours=24, now=now)
        assert f.confidence_low <= f.predicted_tasks
        assert f.confidence_high >= f.predicted_tasks
        assert f.confidence_low >= 0

    def test_longer_horizon(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f12 = loaded_bridge.demand_forecast(horizon_hours=12, now=now)
        f48 = loaded_bridge.demand_forecast(horizon_hours=48, now=now)
        assert f48.predicted_tasks > f12.predicted_tasks

    def test_has_category_breakdown(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = loaded_bridge.demand_forecast(now=now)
        assert len(f.category_breakdown) > 0

    def test_to_dict(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        d = loaded_bridge.demand_forecast(now=now).to_dict()
        assert "predicted_tasks" in d
        assert "confidence_interval" in d
        assert "trend" in d

    def test_category_forecast(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = loaded_bridge.forecast_category("delivery", now=now)
        assert f.dominant_category == "delivery"
        assert f.predicted_tasks >= 0

    def test_unknown_category(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = loaded_bridge.forecast_category("nonexistent", now=now)
        assert f.trend == "insufficient_data"


# ──────────────────────────────────────────────────────────────────────
# 4. Capacity Gap Analysis
# ──────────────────────────────────────────────────────────────────────


class TestCapacityGap:
    def test_surplus(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        gap = loaded_bridge.capacity_gap(available_workers=100, now=now)
        assert gap.surplus_or_deficit > 0
        assert gap.pricing_pressure == "low"

    def test_deficit(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        gap = loaded_bridge.capacity_gap(available_workers=0, now=now)
        assert gap.surplus_or_deficit <= 0

    def test_bounty_direction(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        surplus = loaded_bridge.capacity_gap(available_workers=100, now=now)
        deficit = loaded_bridge.capacity_gap(available_workers=0, now=now)
        assert surplus.suggested_bounty_adj <= deficit.suggested_bounty_adj

    def test_recommended_workers(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        gap = loaded_bridge.capacity_gap(available_workers=5, now=now)
        assert isinstance(gap.recommended_workers, int)
        assert gap.recommended_workers >= 0

    def test_to_dict(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        d = loaded_bridge.capacity_gap(available_workers=5, now=now).to_dict()
        assert "predicted_demand" in d
        assert "pricing_pressure" in d

    def test_per_category_workers(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        gap = loaded_bridge.capacity_gap(
            available_workers=10,
            workers_per_category={"physical_verification": 5, "delivery": 3},
            now=now,
        )
        assert isinstance(gap.category_gaps, dict)


# ──────────────────────────────────────────────────────────────────────
# 5. Spike Detection
# ──────────────────────────────────────────────────────────────────────


class TestSpikeDetection:
    def test_no_spikes_normal(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        spikes = loaded_bridge.detect_spikes(now=now)
        assert isinstance(spikes, list)

    def test_insufficient_data(self, bridge):
        bridge.ingest_rows(make_history(3))
        assert bridge.detect_spikes() == []

    def test_spike_disabled(self):
        config = WorkloadConfig(enable_spike_detection=False)
        b = WorkloadBridge(config=config)
        b.ingest_rows(make_history(50))
        assert b.detect_spikes() == []

    def test_active_spikes_returns_dicts(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        active = loaded_bridge.active_spikes(now=now)
        assert isinstance(active, list)
        for s in active:
            assert isinstance(s, dict)

    def test_spike_data_structure(self):
        spike = DemandSpike(
            detected_at=datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC),
            category="delivery",
            current_rate=10.0,
            baseline_rate=2.0,
            spike_magnitude=3.5,
            predicted_duration_hours=8.0,
            confidence=0.85,
        )
        d = spike.to_dict()
        assert d["category"] == "delivery"
        assert d["spike_magnitude"] == 3.5


# ──────────────────────────────────────────────────────────────────────
# 6. Routing Signal (Signal #15)
# ──────────────────────────────────────────────────────────────────────


class TestRoutingSignal:
    def test_basic_signal(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        signal = loaded_bridge.routing_signal(available_workers=10, now=now)
        assert isinstance(signal, WorkloadRoutingSignal)
        assert signal.demand_trend in (
            "accelerating",
            "steady",
            "decelerating",
            "insufficient_data",
        )

    def test_signal_fields(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        signal = loaded_bridge.routing_signal(available_workers=10, now=now)
        assert signal.forecast_24h >= 0
        assert signal.pricing_pressure in ("low", "moderate", "high", "critical")
        assert isinstance(signal.optimal_posting_hours, list)

    def test_signal_to_dict(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        d = loaded_bridge.routing_signal(available_workers=10, now=now).to_dict()
        assert "demand_trend" in d
        assert "pricing_pressure" in d
        assert "forecast_24h" in d

    def test_signal_few_workers(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        few = loaded_bridge.routing_signal(available_workers=0, now=now)
        many = loaded_bridge.routing_signal(available_workers=100, now=now)
        levels = {"low": 0, "moderate": 1, "high": 2, "critical": 3}
        assert levels.get(few.pricing_pressure, 0) >= levels.get(
            many.pricing_pressure, 0
        )

    def test_signal_insufficient_data(self, bridge):
        bridge.ingest_rows(make_history(3))
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        signal = bridge.routing_signal(available_workers=10, now=now)
        assert signal.demand_trend == "insufficient_data"

    def test_signal_with_seasonal(self, seasonal_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        signal = seasonal_bridge.routing_signal(available_workers=10, now=now)
        assert signal.seasonal_factor > 0


# ──────────────────────────────────────────────────────────────────────
# 7. Health & Diagnostics
# ──────────────────────────────────────────────────────────────────────


class TestHealth:
    def test_empty_health(self, bridge):
        h = bridge.health()
        assert h["status"] == "healthy"
        assert h["total_tasks"] == 0
        assert h["stale"] is False

    def test_loaded_health(self, loaded_bridge):
        h = loaded_bridge.health()
        assert h["total_tasks"] == 50
        assert h["categories"] > 0

    def test_status_text(self, loaded_bridge):
        s = loaded_bridge.status()
        assert "50" in s
        assert "Module #63" in s

    def test_health_config(self, bridge):
        h = bridge.health()
        assert "config" in h
        assert "sync_interval" in h["config"]


# ──────────────────────────────────────────────────────────────────────
# 8. Seasonal Patterns
# ──────────────────────────────────────────────────────────────────────


class TestSeasonalPatterns:
    def test_insufficient_data(self, bridge):
        bridge.ingest_rows(make_history(5))
        patterns = bridge._detect_seasonal_patterns()
        assert patterns is None

    def test_seasonal_detected(self, seasonal_bridge):
        patterns = seasonal_bridge._detect_seasonal_patterns()
        assert patterns is not None
        assert len(patterns) == 24  # One factor per hour

    def test_seasonal_affects_forecast(self, seasonal_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = seasonal_bridge.demand_forecast(now=now)
        assert f.seasonal_factor != 1.0 or f.data_points_used < MIN_TASKS_FOR_SEASONAL


# ──────────────────────────────────────────────────────────────────────
# 9. Trend Detection
# ──────────────────────────────────────────────────────────────────────


class TestTrendDetection:
    def test_insufficient_data(self, bridge):
        bridge.ingest_rows(make_history(3))
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = bridge.demand_forecast(now=now)
        assert f.trend == "insufficient_data"

    def test_accelerating(self, bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        rows = []
        for d in range(7):
            rows.append(make_row(task_id=f"slow_{d}", hours_ago=24 * (14 - d), now=now))
        for d in range(7):
            for t in range(5):
                rows.append(
                    make_row(
                        task_id=f"fast_{d}_{t}", hours_ago=24 * (7 - d) + t * 2, now=now
                    )
                )
        bridge.ingest_rows(rows)
        f = bridge.demand_forecast(now=now)
        assert f.trend == "accelerating"

    def test_decelerating(self, bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        rows = []
        for d in range(7):
            for t in range(5):
                rows.append(
                    make_row(
                        task_id=f"fast_{d}_{t}",
                        hours_ago=24 * (14 - d) + t * 2,
                        now=now,
                    )
                )
        for d in range(7):
            rows.append(make_row(task_id=f"slow_{d}", hours_ago=24 * (7 - d), now=now))
        bridge.ingest_rows(rows)
        f = bridge.demand_forecast(now=now)
        assert f.trend == "decelerating"

    def test_steady(self, bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        rows = []
        for d in range(14):
            for t in range(3):
                rows.append(
                    make_row(
                        task_id=f"s_{d}_{t}", hours_ago=24 * (14 - d) + t * 4, now=now
                    )
                )
        bridge.ingest_rows(rows)
        f = bridge.demand_forecast(now=now)
        assert f.trend == "steady"


# ──────────────────────────────────────────────────────────────────────
# 10. Edge Cases
# ──────────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_single_task(self, bridge):
        bridge.ingest_rows([make_row()])
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = bridge.demand_forecast(now=now)
        assert f.trend == "insufficient_data"

    def test_zero_horizon(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = loaded_bridge.demand_forecast(horizon_hours=0, now=now)
        assert f.predicted_tasks == 0.0

    def test_all_same_category(self, bridge):
        rows = [
            make_row(task_id=f"same_{i}", hours_ago=i * 2, category="delivery")
            for i in range(20)
        ]
        bridge.ingest_rows(rows)
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        f = bridge.demand_forecast(now=now)
        assert f.dominant_category == "delivery"

    def test_naive_datetime(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0)  # No tzinfo
        f = loaded_bridge.demand_forecast(now=now)
        assert f.predicted_tasks >= 0

    def test_capacity_zero_workers(self, loaded_bridge):
        now = datetime(2026, 3, 31, 12, 0, 0, tzinfo=UTC)
        gap = loaded_bridge.capacity_gap(available_workers=0, now=now)
        assert gap.available_workers == 0
        assert gap.surplus_or_deficit <= 0


# ──────────────────────────────────────────────────────────────────────
# Async Sync (mocked)
# ──────────────────────────────────────────────────────────────────────


class TestAsyncSync:
    @pytest.mark.asyncio
    async def test_sync_no_module(self, bridge):
        """Sync fails gracefully without supabase_client."""
        import unittest.mock as _m

        with _m.patch.dict("sys.modules", {"supabase_client": None}):
            result = await bridge.sync(force=True)
        assert result == 0

    @pytest.mark.asyncio
    async def test_sync_cooldown(self, bridge):
        """Sync respects interval cooldown."""
        bridge._last_sync = 999999999999  # Far future
        result = await bridge.sync(force=False)
        assert result == 0
