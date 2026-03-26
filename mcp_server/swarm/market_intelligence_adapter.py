"""
MarketIntelligenceAdapter — AutoJob Market Intelligence as a Swarm Signal
==========================================================================

The 12th signal: MARKET_INTELLIGENCE — "Is the market favorable for this task?"

Signals 1-11 focus on individual workers: their skills, reputation, availability,
performance, pricing, retention, etc. But they all ignore the *marketplace context*.

The MarketIntelligenceAdapter brings category-level market intelligence into routing:
- Supply/demand balance per category (is this category oversaturated or underserved?)
- Task expiry risk (what % of tasks in this category fail to complete?)
- Optimal timing (is now a good time to post, or should we wait?)
- Worker competition intensity (how many workers compete per task?)
- Market trend (is this category growing, stable, or declining?)

This is a *task-level* signal, not a *worker-level* signal. All candidates for the
same task get the same market intelligence score. The value is in routing context:
- High-demand categories → lower bounties can still attract workers → cost optimization
- Low-supply categories → need higher bounties or wider matching → avoid expiry
- Declining categories → flag for task creator intervention

Architecture:
    Task arrives → DecisionBridge collects candidates
        → MarketIntelligenceAdapter.analyze(category) → AutoJob API
        → Returns MarketSnapshot (demand_score, completion_rate, trend)
        → Normalizes → SignalType.MARKET_INTELLIGENCE score

Caching strategy:
    - Market data cached per category for 30 minutes (markets change faster than workers)
    - Stale cache used on API failure (up to 4 hours)
    - Default (neutral 0.5 demand, 50% completion) on total failure

Why 30 minutes?
    Supply/demand shifts as tasks are posted and completed throughout the day.
    A category that was balanced 2 hours ago might be saturated now. Worker retention
    changes slowly (2h cache), but market dynamics move faster.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("em.swarm.market_intelligence_adapter")


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


@dataclass
class MarketSnapshot:
    """Cached market intelligence for a task category."""

    category: str
    demand_score: float = 0.5  # 0-1: higher = more demand relative to supply
    completion_rate: float = 0.5  # 0-1: % of tasks that complete successfully
    expiry_rate: float = 0.5  # 0-1: % of tasks that expire without completion
    trend: str = "stable"  # "growing" | "stable" | "declining"
    avg_bounty_usd: float = 3.0
    avg_time_to_acceptance_hours: float = 24.0
    active_tasks: int = 0
    unique_workers: int = 0
    competition_intensity: float = 0.5  # avg workers per task (normalized 0-1)
    confidence: float = 0.3
    fetched_at: float = 0.0
    from_cache: bool = False

    @property
    def age_seconds(self) -> float:
        return time.time() - self.fetched_at if self.fetched_at else float("inf")

    @property
    def market_health_score(self) -> float:
        """Composite market health (0-100 scale).

        Factors:
        - Completion rate (40%) — higher is better
        - Inverse expiry rate (20%) — lower expiry is better
        - Demand balance (20%) — moderate demand is ideal (0.3-0.7)
        - Trend bonus (20%) — growing = +10, stable = 0, declining = -10
        """
        # Completion rate contributes most (0-40)
        completion_contrib = self.completion_rate * 40.0

        # Inverse expiry (0-20)
        expiry_contrib = (1.0 - self.expiry_rate) * 20.0

        # Demand balance: moderate demand is best (0.3-0.7 sweet spot)
        # Too low = no workers care; too high = can't fill tasks
        if 0.3 <= self.demand_score <= 0.7:
            demand_contrib = 20.0  # Ideal range
        elif self.demand_score < 0.3:
            demand_contrib = self.demand_score / 0.3 * 15.0  # 0-15 for low demand
        else:
            # High demand — still acceptable but risky
            demand_contrib = max(5.0, 20.0 - (self.demand_score - 0.7) * 30.0)

        # Trend bonus
        trend_map = {
            "growing": 15.0,
            "stable": 10.0,
            "declining": 0.0,
        }
        trend_contrib = trend_map.get(self.trend, 10.0)

        return max(
            0.0,
            min(
                100.0,
                completion_contrib + expiry_contrib + demand_contrib + trend_contrib,
            ),
        )


# ──────────────────────────────────────────────────────────────
# Timing Recommendation
# ──────────────────────────────────────────────────────────────


@dataclass
class TimingSnapshot:
    """Cached timing recommendation for a category."""

    category: str
    best_hour_utc: int = 14  # Default: 2pm UTC
    best_day: str = "tuesday"
    acceptance_likelihood: float = 0.5  # 0-1: how likely task gets accepted now
    confidence: float = 0.3
    fetched_at: float = 0.0

    @property
    def age_seconds(self) -> float:
        return time.time() - self.fetched_at if self.fetched_at else float("inf")


# ──────────────────────────────────────────────────────────────
# Supply Gap
# ──────────────────────────────────────────────────────────────


@dataclass
class SupplyGapSnapshot:
    """Cached supply gap data."""

    category: str
    gap_severity: float = 0.0  # 0-1: how severe the supply shortage
    worker_deficit: int = 0  # Estimated additional workers needed
    avg_wait_hours: float = 24.0
    recommendation: str = ""  # "increase_bounty" | "extend_deadline" | "notify_workers"
    fetched_at: float = 0.0

    @property
    def age_seconds(self) -> float:
        return time.time() - self.fetched_at if self.fetched_at else float("inf")


# ──────────────────────────────────────────────────────────────
# Adapter
# ──────────────────────────────────────────────────────────────


FRESH_TTL = 1800  # 30 minutes — market dynamics change faster
STALE_TTL = 14400  # 4 hours — stale cache for API failures


class MarketIntelligenceAdapter:
    """Bridges AutoJob's CompetitiveAnalyzer into the swarm routing pipeline.

    Provides:
    1. analyze(category) → MarketSnapshot
    2. get_timing(category) → TimingSnapshot
    3. get_supply_gaps() → list[SupplyGapSnapshot]
    4. make_market_scorer() → Callable for DecisionSynthesizer
    """

    def __init__(
        self,
        autojob_base_url: str = "http://localhost:8899",
        timeout_s: float = 5.0,
    ):
        self.base_url = autojob_base_url.rstrip("/")
        self.timeout_s = timeout_s

        # Cache: category → MarketSnapshot
        self._market_cache: dict[str, MarketSnapshot] = {}
        self._timing_cache: dict[str, TimingSnapshot] = {}
        self._gaps_cache: Optional[list[SupplyGapSnapshot]] = None
        self._gaps_fetched_at: float = 0.0

        # Stats
        self._total_requests = 0
        self._cache_hits = 0
        self._api_calls = 0
        self._api_errors = 0

    def analyze(self, category: str) -> MarketSnapshot:
        """Analyze market conditions for a task category.

        4-tier fallback:
        1. Fresh cache hit
        2. Live API call (market report + category extraction)
        3. Stale cache
        4. Default
        """
        self._total_requests += 1
        cache_key = category.lower().replace(" ", "_")

        # Tier 1: Fresh cache
        cached = self._market_cache.get(cache_key)
        if cached and cached.age_seconds < FRESH_TTL:
            self._cache_hits += 1
            cached.from_cache = True
            return cached

        # Tier 2: Live API
        snapshot = self._fetch_category_demand(category)
        if snapshot:
            self._market_cache[cache_key] = snapshot
            return snapshot

        # Tier 3: Stale cache
        if cached and cached.age_seconds < STALE_TTL:
            self._cache_hits += 1
            cached.from_cache = True
            logger.info("Using stale market cache for %s", category)
            return cached

        # Tier 4: Default
        return MarketSnapshot(
            category=category,
            confidence=0.1,
            fetched_at=time.time(),
        )

    def get_timing(self, category: str) -> TimingSnapshot:
        """Get optimal timing recommendation for a category.

        4-tier fallback with same pattern.
        """
        cache_key = category.lower().replace(" ", "_")

        # Fresh cache
        cached = self._timing_cache.get(cache_key)
        if cached and cached.age_seconds < FRESH_TTL:
            return cached

        # Live API
        snapshot = self._fetch_timing(category)
        if snapshot:
            self._timing_cache[cache_key] = snapshot
            return snapshot

        # Stale cache
        if cached and cached.age_seconds < STALE_TTL:
            return cached

        return TimingSnapshot(category=category, fetched_at=time.time())

    def get_supply_gaps(self) -> list[SupplyGapSnapshot]:
        """Get current supply gaps across all categories.

        Cached for 30 minutes (market-level data).
        """
        if self._gaps_cache and (time.time() - self._gaps_fetched_at) < FRESH_TTL:
            return self._gaps_cache

        gaps = self._fetch_supply_gaps()
        if gaps is not None:
            self._gaps_cache = gaps
            self._gaps_fetched_at = time.time()
            return gaps

        # Stale cache
        if self._gaps_cache and (time.time() - self._gaps_fetched_at) < STALE_TTL:
            return self._gaps_cache

        return []

    def _fetch_category_demand(self, category: str) -> Optional[MarketSnapshot]:
        """Call AutoJob's /api/market/report to get category-level demand data."""
        self._api_calls += 1
        url = f"{self.base_url}/api/market/report"

        try:
            req = Request(url, method="GET")
            start = time.monotonic()
            with urlopen(req, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            (time.monotonic() - start) * 1000

            if not data.get("success"):
                logger.warning("Market report API returned failure")
                self._api_errors += 1
                return None

            report = data.get("report", {})
            categories = report.get("categories", {})
            cat_data = categories.get(category.lower(), categories.get(category, {}))

            if not cat_data:
                # Try fuzzy match
                for key, val in categories.items():
                    if (
                        category.lower() in key.lower()
                        or key.lower() in category.lower()
                    ):
                        cat_data = val
                        break

            if not cat_data:
                # No data for this category — still informative (emerging category)
                return MarketSnapshot(
                    category=category,
                    demand_score=0.0,
                    completion_rate=0.0,
                    expiry_rate=0.0,
                    trend="stable",
                    active_tasks=0,
                    unique_workers=0,
                    confidence=0.2,
                    fetched_at=time.time(),
                )

            return MarketSnapshot(
                category=category,
                demand_score=cat_data.get("demand_score", 0.5),
                completion_rate=cat_data.get("completion_rate", 0.5),
                expiry_rate=cat_data.get("expiry_rate", 0.5),
                trend=cat_data.get("trend", "stable"),
                avg_bounty_usd=cat_data.get("avg_bounty_usd", 3.0),
                avg_time_to_acceptance_hours=cat_data.get(
                    "avg_time_to_acceptance_hours", 24.0
                ),
                active_tasks=cat_data.get("active_tasks", 0),
                unique_workers=cat_data.get("unique_workers", 0),
                competition_intensity=min(
                    1.0, cat_data.get("avg_applications_per_task", 1.0) / 5.0
                ),
                confidence=min(0.9, 0.3 + cat_data.get("total_tasks", 0) * 0.01),
                fetched_at=time.time(),
            )

        except (URLError, HTTPError, TimeoutError, OSError) as e:
            self._api_errors += 1
            logger.warning("Market report API error: %s", e)
            return None
        except Exception as e:
            self._api_errors += 1
            logger.error("Unexpected market report error: %s", e)
            return None

    def _fetch_timing(self, category: str) -> Optional[TimingSnapshot]:
        """Call AutoJob's /api/market/timing/{category} endpoint."""
        self._api_calls += 1
        url = f"{self.base_url}/api/market/timing/{category}"

        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if not data.get("success"):
                self._api_errors += 1
                return None

            timing = data.get("timing", {})
            return TimingSnapshot(
                category=category,
                best_hour_utc=timing.get("best_hour_utc", 14),
                best_day=timing.get("best_day", "tuesday"),
                acceptance_likelihood=timing.get("acceptance_likelihood", 0.5),
                confidence=timing.get("confidence", 0.3),
                fetched_at=time.time(),
            )

        except (URLError, HTTPError, TimeoutError, OSError) as e:
            self._api_errors += 1
            logger.warning("Market timing API error for %s: %s", category, e)
            return None
        except Exception as e:
            self._api_errors += 1
            logger.error("Unexpected timing error for %s: %s", category, e)
            return None

    def _fetch_supply_gaps(self) -> Optional[list[SupplyGapSnapshot]]:
        """Call AutoJob's /api/market/gaps endpoint."""
        self._api_calls += 1
        url = f"{self.base_url}/api/market/gaps"

        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if not data.get("success"):
                self._api_errors += 1
                return None

            gaps_data = data.get("gaps", [])
            return [
                SupplyGapSnapshot(
                    category=g.get("category", "unknown"),
                    gap_severity=g.get("severity", 0.0),
                    worker_deficit=g.get("worker_deficit", 0),
                    avg_wait_hours=g.get("avg_wait_hours", 24.0),
                    recommendation=g.get("recommendation", ""),
                    fetched_at=time.time(),
                )
                for g in gaps_data
            ]

        except (URLError, HTTPError, TimeoutError, OSError) as e:
            self._api_errors += 1
            logger.warning("Supply gaps API error: %s", e)
            return None
        except Exception as e:
            self._api_errors += 1
            logger.error("Unexpected supply gaps error: %s", e)
            return None

    def stats(self) -> dict:
        """Return adapter statistics."""
        return {
            "total_requests": self._total_requests,
            "cache_hits": self._cache_hits,
            "api_calls": self._api_calls,
            "api_errors": self._api_errors,
            "market_cache_size": len(self._market_cache),
            "timing_cache_size": len(self._timing_cache),
            "has_gaps": self._gaps_cache is not None,
            "hit_rate": (
                round(self._cache_hits / self._total_requests, 3)
                if self._total_requests
                else 0
            ),
        }


# ──────────────────────────────────────────────────────────────
# Scorer Factory
# ──────────────────────────────────────────────────────────────


def make_market_scorer(adapter: MarketIntelligenceAdapter) -> Callable:
    """Create a scorer function compatible with DecisionSynthesizer.

    Score formula:
        market_health_score (0-100) — composite of completion rate,
        expiry patterns, demand balance, and market trend.

    This is a task-level signal: all candidates for the same task get the
    same base market score. The value is context — the synthesizer uses
    this alongside per-worker signals to make informed routing decisions.

    High market health → standard routing confidence
    Low market health → signal to adjust strategy (raise bounty, extend deadline)
    """

    def scorer(task: dict, candidate: dict) -> float:
        try:
            category = task.get("category", task.get("task_type", "general"))
            snapshot = adapter.analyze(category)
            return snapshot.market_health_score

        except Exception as e:
            logger.debug("Market scorer error: %s", e)
            return 50.0  # Neutral on error

    return scorer
