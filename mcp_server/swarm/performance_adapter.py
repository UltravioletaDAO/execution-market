"""
PerformanceAdapter — AutoJob Worker Performance as a DecisionBridge Signal
============================================================================

Adapts AutoJob's WorkerPerformanceAnalyzer output into a DecisionSynthesizer
signal that enriches routing decisions with behavioral depth:

- Reliability trends (improving workers get boosted)
- Risk-adjusted scoring (high-risk workers get penalized)
- Category affinity (workers routed to their best task types)
- Growth trajectory (growing workers are preferred over stagnant ones)

The adapter fetches performance data from AutoJob's API or uses
cached profiles when the API is unavailable.

Usage:
    from .performance_adapter import PerformanceAdapter, make_performance_scorer

    adapter = PerformanceAdapter(autojob_url="https://autojob.cc")
    scorer = make_performance_scorer(adapter)

    # Register with DecisionSynthesizer:
    synthesizer.register_signal(
        SignalType.PERFORMANCE,
        scorer,
        confidence=0.75,
        description="AutoJob WorkerPerformanceAnalyzer",
    )

Thread-safety: read-only cache is safe; API calls are per-invocation.
"""

import json
import logging
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

logger = logging.getLogger("em.swarm.performance_adapter")


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────

@dataclass
class PerformanceSnapshot:
    """Snapshot of a worker's performance profile."""
    worker_id: str
    overall_score: float = 0.5  # 0-1
    reliability: float = 0.5
    speed_percentile: float = 0.5
    quality: float = 0.5
    consistency: float = 0.5
    risk_level: str = "unknown"  # low/medium/high/unknown
    growth_trend: str = "unknown"  # improving/stable/declining/unknown
    optimal_categories: list = field(default_factory=list)
    recommended_complexity: str = "simple"
    fetched_at: Optional[str] = None
    source: str = "default"  # "api" | "cache" | "default"

    @property
    def is_stale(self) -> bool:
        """Check if snapshot is older than 1 hour."""
        if not self.fetched_at:
            return True
        try:
            fetched = datetime.fromisoformat(self.fetched_at)
            return (datetime.now(timezone.utc) - fetched) > timedelta(hours=1)
        except (ValueError, TypeError):
            return True

    @property
    def risk_penalty(self) -> float:
        """Risk as a 0-1 penalty factor."""
        return {"low": 0.0, "medium": 0.05, "high": 0.15}.get(self.risk_level, 0.0)

    @property
    def growth_bonus(self) -> float:
        """Growth trend as a 0-1 bonus factor."""
        return {"improving": 0.10, "stable": 0.0, "declining": -0.05}.get(
            self.growth_trend, 0.0
        )

    def category_affinity(self, category: str) -> float:
        """How well this worker matches the given task category (0-1)."""
        if not self.optimal_categories:
            return 0.5
        if category in self.optimal_categories[:1]:
            return 1.0
        if category in self.optimal_categories[:3]:
            return 0.8
        if category in self.optimal_categories:
            return 0.6
        return 0.3


# ──────────────────────────────────────────────────────────────
# Adapter
# ──────────────────────────────────────────────────────────────

class PerformanceAdapter:
    """
    Fetches and caches worker performance profiles from AutoJob.

    Uses a two-tier strategy:
    1. In-memory cache (TTL 1 hour)
    2. AutoJob API fallback

    When both fail, returns a neutral default profile (0.5 across the board).
    """

    def __init__(
        self,
        autojob_url: str = "https://autojob.cc",
        cache_ttl_seconds: int = 3600,
        request_timeout_seconds: int = 5,
    ):
        self.autojob_url = autojob_url.rstrip("/")
        self.cache_ttl = cache_ttl_seconds
        self.timeout = request_timeout_seconds
        self._cache: dict[str, PerformanceSnapshot] = {}
        self._stats = {
            "api_calls": 0,
            "cache_hits": 0,
            "defaults_used": 0,
            "errors": 0,
        }

    def get_performance(self, worker_id: str) -> PerformanceSnapshot:
        """
        Get a worker's performance profile.

        Strategy:
        1. Check cache → return if fresh
        2. Call AutoJob API → cache and return
        3. Return neutral default
        """
        # Check cache
        cached = self._cache.get(worker_id)
        if cached and not cached.is_stale:
            self._stats["cache_hits"] += 1
            return cached

        # Try API
        try:
            profile = self._fetch_from_api(worker_id)
            if profile:
                self._cache[worker_id] = profile
                return profile
        except Exception as e:
            logger.debug("AutoJob API error for %s: %s", worker_id, e)
            self._stats["errors"] += 1

        # Return stale cache if available
        if cached:
            self._stats["cache_hits"] += 1
            return cached

        # Default
        self._stats["defaults_used"] += 1
        return PerformanceSnapshot(
            worker_id=worker_id,
            source="default",
        )

    def get_stats(self) -> dict:
        """Return adapter statistics."""
        return {
            **self._stats,
            "cache_size": len(self._cache),
        }

    def clear_cache(self):
        """Clear the performance cache."""
        self._cache.clear()

    def invalidate(self, worker_id: str):
        """Remove a specific worker from cache."""
        self._cache.pop(worker_id, None)

    def _fetch_from_api(self, worker_id: str) -> Optional[PerformanceSnapshot]:
        """Fetch performance profile from AutoJob API."""
        url = f"{self.autojob_url}/api/worker-performance/{worker_id}"
        self._stats["api_calls"] += 1

        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, method="GET")
            req.add_header("Accept", "application/json")

            with urllib.request.urlopen(req, timeout=self.timeout, context=ctx) as resp:
                data = json.loads(resp.read().decode())

            if not data.get("success"):
                return None

            profile_data = data.get("profile")
            if not profile_data:
                return None

            return PerformanceSnapshot(
                worker_id=worker_id,
                overall_score=profile_data.get("overall_score", 0.5),
                reliability=profile_data.get("reliability_score", 0.5),
                speed_percentile=profile_data.get("speed_percentile", 0.5),
                quality=profile_data.get("quality_score", 0.5),
                consistency=profile_data.get("consistency_score", 0.5),
                risk_level=profile_data.get("risk", {}).get("overall_risk", "unknown"),
                growth_trend=profile_data.get("growth", {}).get("trend", "unknown"),
                optimal_categories=profile_data.get("optimal_categories", []),
                recommended_complexity=profile_data.get("recommended_complexity", "simple"),
                fetched_at=datetime.now(timezone.utc).isoformat(),
                source="api",
            )

        except (urllib.error.URLError, json.JSONDecodeError, KeyError, OSError) as e:
            logger.debug("AutoJob API request failed: %s", e)
            raise

    def bulk_fetch(self, worker_ids: list[str]) -> dict[str, PerformanceSnapshot]:
        """Fetch performance for multiple workers."""
        results = {}
        for wid in worker_ids:
            results[wid] = self.get_performance(wid)
        return results


# ──────────────────────────────────────────────────────────────
# Scorer Factory — for DecisionSynthesizer
# ──────────────────────────────────────────────────────────────

def make_performance_scorer(adapter: PerformanceAdapter):
    """
    Create a scorer function compatible with DecisionSynthesizer.

    The scorer returns 0-100 based on:
    - Overall score (50% weight)
    - Category affinity (20% weight)
    - Growth trend bonus (15% weight)
    - Risk penalty (15% weight)
    """
    def scorer(task: dict, candidate: dict) -> float:
        worker_id = candidate.get("wallet", candidate.get("worker_id", ""))
        if not worker_id:
            return 50.0  # neutral

        perf = adapter.get_performance(worker_id)

        # Base: overall performance (0-100)
        base = perf.overall_score * 100

        # Category affinity
        category = task.get("category", task.get("task_type", ""))
        affinity = perf.category_affinity(category) * 100 if category else 50.0

        # Growth bonus/penalty (-5 to +10)
        growth = perf.growth_bonus * 100

        # Risk penalty (0 to -15)
        risk = perf.risk_penalty * 100

        # Weighted composite
        score = (
            0.50 * base
            + 0.20 * affinity
            + 0.15 * growth
            - 0.15 * risk
        )

        return max(0.0, min(100.0, score))

    return scorer


def make_performance_scorer_from_url(autojob_url: str = "https://autojob.cc"):
    """Convenience: create scorer with fresh adapter."""
    adapter = PerformanceAdapter(autojob_url=autojob_url)
    return make_performance_scorer(adapter)
