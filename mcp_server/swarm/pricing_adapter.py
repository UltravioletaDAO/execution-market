"""
PricingAdapter — AutoJob Pricing Intelligence as a Swarm Signal
=================================================================

Adapts AutoJob's TaskPricingEngine and CompetitiveAnalyzer output into
swarm-consumable data for task creation and routing decisions:

- Optimal bounty recommendations for new tasks
- Market demand signals for category prioritization
- Supply gap identification for proactive task sourcing
- Timing recommendations for optimal worker acceptance

This adapter answers: "What should we pay, and when should we post?"

Usage:
    from .pricing_adapter import PricingAdapter

    adapter = PricingAdapter(autojob_url="https://autojob.cc")

    # Get pricing for a task
    pricing = adapter.get_task_pricing("physical_verification")

    # Get market intelligence
    report = adapter.get_market_report()
    gaps = adapter.get_supply_gaps()

    # Create a scorer for DecisionSynthesizer
    scorer = make_pricing_scorer(adapter)

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

logger = logging.getLogger("em.swarm.pricing_adapter")


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


@dataclass
class PricingSnapshot:
    """Cached pricing recommendation for a category."""
    category: str
    recommended_usd: float = 3.0
    range_low_usd: float = 1.50
    range_high_usd: float = 5.0
    confidence: float = 0.3
    urgency_multiplier: float = 1.0
    complexity_multiplier: float = 1.0
    fetched_at: float = 0.0
    source: str = "default"  # "api" | "cache" | "default"

    def is_stale(self, max_age_seconds: float = 3600) -> bool:
        """True if snapshot is older than max_age_seconds."""
        return (time.time() - self.fetched_at) > max_age_seconds

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "recommended_usd": round(self.recommended_usd, 2),
            "range": [round(self.range_low_usd, 2), round(self.range_high_usd, 2)],
            "confidence": round(self.confidence, 3),
            "urgency_multiplier": round(self.urgency_multiplier, 3),
            "complexity_multiplier": round(self.complexity_multiplier, 3),
            "source": self.source,
        }


@dataclass
class MarketDemandSnapshot:
    """Cached market demand for a category."""
    category: str
    demand_score: float = 0.5  # 0-1: higher = more demand
    completion_rate: float = 0.5
    expiry_rate: float = 0.2
    trend: str = "stable"  # growing/stable/declining
    avg_bounty_usd: float = 3.0
    supply_gap_severity: str = "none"  # none/mild/moderate/critical
    fetched_at: float = 0.0
    source: str = "default"

    def is_stale(self, max_age_seconds: float = 3600) -> bool:
        return (time.time() - self.fetched_at) > max_age_seconds

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "demand_score": round(self.demand_score, 3),
            "completion_rate": round(self.completion_rate, 3),
            "expiry_rate": round(self.expiry_rate, 3),
            "trend": self.trend,
            "avg_bounty_usd": round(self.avg_bounty_usd, 2),
            "supply_gap_severity": self.supply_gap_severity,
            "source": self.source,
        }


# Default category pricing (when API unavailable)
DEFAULT_PRICING = {
    "physical_verification": {"median": 3.0, "low": 2.0, "high": 5.0},
    "delivery": {"median": 8.0, "low": 5.0, "high": 15.0},
    "data_collection": {"median": 2.5, "low": 1.5, "high": 4.0},
    "content_creation": {"median": 10.0, "low": 5.0, "high": 25.0},
    "research": {"median": 5.0, "low": 3.0, "high": 10.0},
    "testing": {"median": 4.0, "low": 2.0, "high": 8.0},
    "survey": {"median": 1.5, "low": 0.5, "high": 3.0},
    "general": {"median": 3.0, "low": 1.5, "high": 5.0},
}


# ──────────────────────────────────────────────────────────────
# Adapter
# ──────────────────────────────────────────────────────────────


class PricingAdapter:
    """
    Fetches pricing intelligence from AutoJob and caches results.

    Two-tier fetch strategy:
    1. Try API → parse + cache
    2. On failure → use stale cache or defaults

    Cache TTL: 1 hour (pricing data doesn't change rapidly).
    """

    def __init__(
        self,
        autojob_url: str = "https://autojob.cc",
        timeout_seconds: float = 8.0,
        cache_ttl_seconds: float = 3600.0,
    ):
        self._url = autojob_url.rstrip("/")
        self._timeout = timeout_seconds
        self._cache_ttl = cache_ttl_seconds
        self._pricing_cache: dict[str, PricingSnapshot] = {}
        self._demand_cache: dict[str, MarketDemandSnapshot] = {}
        self._market_report_cache: Optional[dict] = None
        self._market_report_ts: float = 0.0
        self._stats = {
            "api_calls": 0,
            "api_errors": 0,
            "cache_hits": 0,
            "default_fallbacks": 0,
        }

    # ─── Public API ───────────────────────────────────────────────

    def get_task_pricing(
        self,
        category: str,
        deadline_hours: Optional[float] = None,
        quality_target: str = "any",
    ) -> PricingSnapshot:
        """
        Get pricing recommendation for a task category.

        Tries:
        1. Fresh API data
        2. Cached (possibly stale) data
        3. Hardcoded defaults
        """
        category = self._normalize(category)

        # Check cache
        cached = self._pricing_cache.get(category)
        if cached and not cached.is_stale(self._cache_ttl):
            self._stats["cache_hits"] += 1
            return cached

        # Try API
        try:
            data = self._api_get(f"/api/pricing/category/{category}")
            if data and data.get("success") and data.get("pricing"):
                pricing = data["pricing"]
                snapshot = PricingSnapshot(
                    category=category,
                    recommended_usd=pricing.get("recommended_usd", 3.0),
                    range_low_usd=pricing.get("range", [1.5, 5.0])[0],
                    range_high_usd=pricing.get("range", [1.5, 5.0])[1],
                    confidence=pricing.get("confidence", 0.5),
                    urgency_multiplier=pricing.get("multipliers", {}).get("urgency", 1.0),
                    complexity_multiplier=pricing.get("multipliers", {}).get("complexity", 1.0),
                    fetched_at=time.time(),
                    source="api",
                )
                self._pricing_cache[category] = snapshot
                return snapshot
        except Exception as e:
            logger.debug(f"PricingAdapter API error for {category}: {e}")
            self._stats["api_errors"] += 1

        # Stale cache fallback
        if cached:
            self._stats["cache_hits"] += 1
            return cached

        # Default fallback
        self._stats["default_fallbacks"] += 1
        defaults = DEFAULT_PRICING.get(category, DEFAULT_PRICING["general"])
        return PricingSnapshot(
            category=category,
            recommended_usd=defaults["median"],
            range_low_usd=defaults["low"],
            range_high_usd=defaults["high"],
            confidence=0.3,
            fetched_at=time.time(),
            source="default",
        )

    def get_market_demand(self, category: str) -> MarketDemandSnapshot:
        """
        Get market demand signal for a category.

        Used by the swarm to prioritize which tasks to create/seek.
        """
        category = self._normalize(category)

        cached = self._demand_cache.get(category)
        if cached and not cached.is_stale(self._cache_ttl):
            self._stats["cache_hits"] += 1
            return cached

        # Try API (market report endpoint)
        try:
            report = self._get_market_report()
            if report:
                # Find gaps for this category
                gaps = report.get("supply_gaps", [])
                gap_severity = "none"
                for g in gaps:
                    if g.get("category") == category:
                        gap_severity = g.get("severity", "mild")
                        break

                snapshot = MarketDemandSnapshot(
                    category=category,
                    demand_score=0.5,  # Will be enriched if category data available
                    completion_rate=report.get("overall_completion_rate", 0.5),
                    expiry_rate=report.get("overall_expiry_rate", 0.2),
                    trend="stable",
                    avg_bounty_usd=report.get("avg_bounty_usd", 3.0),
                    supply_gap_severity=gap_severity,
                    fetched_at=time.time(),
                    source="api",
                )
                self._demand_cache[category] = snapshot
                return snapshot
        except Exception as e:
            logger.debug(f"PricingAdapter market demand error: {e}")

        if cached:
            self._stats["cache_hits"] += 1
            return cached

        self._stats["default_fallbacks"] += 1
        return MarketDemandSnapshot(
            category=category,
            fetched_at=time.time(),
            source="default",
        )

    def get_supply_gaps(self) -> list[dict]:
        """Get current supply gaps (underserved categories)."""
        try:
            data = self._api_get("/api/market/gaps")
            if data and data.get("success"):
                return data.get("gaps", [])
        except Exception as e:
            logger.debug(f"PricingAdapter supply gaps error: {e}")
        return []

    def get_stats(self) -> dict:
        """Get adapter usage statistics."""
        return dict(self._stats)

    # ─── Internals ────────────────────────────────────────────────

    def _get_market_report(self) -> Optional[dict]:
        """Cached market report fetch."""
        if self._market_report_cache and (time.time() - self._market_report_ts) < self._cache_ttl:
            return self._market_report_cache

        data = self._api_get("/api/market/report")
        if data and data.get("success"):
            self._market_report_cache = data.get("report", {})
            self._market_report_ts = time.time()
            return self._market_report_cache
        return None

    def _api_get(self, path: str) -> Optional[dict]:
        """Make a GET request to AutoJob API."""
        url = f"{self._url}{path}"
        self._stats["api_calls"] += 1

        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
            self._stats["api_errors"] += 1
            raise

    @staticmethod
    def _normalize(category: str) -> str:
        if not category:
            return "general"
        return category.lower().strip().replace(" ", "_").replace("-", "_")


# ──────────────────────────────────────────────────────────────
# DecisionSynthesizer Scorer Factory
# ──────────────────────────────────────────────────────────────


def make_pricing_scorer(adapter: PricingAdapter):
    """
    Create a scorer function compatible with DecisionSynthesizer.

    The pricing scorer evaluates whether a task's bounty is competitive
    for the category. Higher score = bounty is well-calibrated.

    Formula:
      - If bounty >= recommended → score 0.8 + bonus for generosity
      - If bounty >= range_low → score proportional to range position
      - If bounty < range_low → penalty score (underpriced)
    """

    def scorer(task: dict, candidate: dict) -> float:
        category = task.get("category", "general")
        bounty = 0.0
        for key in ("bounty_usd", "bounty_amount_usdc", "bounty", "amount"):
            val = task.get(key)
            if val is not None:
                try:
                    bounty = float(val)
                    break
                except (ValueError, TypeError):
                    continue

        if bounty <= 0:
            return 0.5  # No bounty info → neutral

        pricing = adapter.get_task_pricing(category)

        if bounty >= pricing.recommended_usd:
            # Well-priced or generous — high score
            generosity = min(0.2, (bounty - pricing.recommended_usd) / pricing.recommended_usd * 0.2)
            return min(1.0, 0.8 + generosity)
        elif bounty >= pricing.range_low_usd:
            # Within acceptable range — proportional score
            range_width = pricing.recommended_usd - pricing.range_low_usd
            if range_width > 0:
                position = (bounty - pricing.range_low_usd) / range_width
                return 0.5 + position * 0.3  # 0.5 to 0.8
            return 0.65
        else:
            # Underpriced — low score
            if pricing.range_low_usd > 0:
                ratio = bounty / pricing.range_low_usd
                return max(0.1, ratio * 0.5)
            return 0.3

    return scorer
