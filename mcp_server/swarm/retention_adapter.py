"""
RetentionAdapter — Bridges WorkerRetentionAnalyzer into the DecisionBridge Pipeline
===================================================================================

The 11th signal: RETENTION — "Will this worker still be around tomorrow?"

Signals 1-10 answer capability, availability, pricing, and prediction questions.
But they all assume the worker will be around to complete the task. Worker churn
is expensive: lost institutional knowledge, coverage gaps, routing re-optimization.

The RetentionAdapter calls AutoJob's WorkerRetentionAnalyzer (exposed as
GET /api/worker-retention/{wallet}) and feeds churn intelligence into routing.

Why this matters for routing:
- A high-skill worker with critical churn risk is unreliable for time-sensitive tasks
- A moderate-skill worker with stable retention is more dependable long-term
- High-risk workers should get lower-priority assignments, not critical tasks
- Retention signals can trigger intervention workflows

Architecture:
    Task arrives → DecisionBridge collects candidates
        → RetentionAdapter.analyze(wallet) → AutoJob API
        → Returns RetentionSnapshot (churn_probability, risk, tenure)
        → Normalizes → SignalType.RETENTION score

Caching strategy:
    - Retention profiles cached per wallet for 2 hours
    - Stale cache used on API failure (up to 12h)
    - Default (0.3 churn, "at_risk") on total failure
"""

import json
import logging
import time
from dataclasses import dataclass
from datetime import timezone
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("em.swarm.retention_adapter")

UTC = timezone.utc


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


@dataclass
class RetentionSnapshot:
    """Cached retention analysis for a worker."""

    wallet: str
    churn_probability: float = 0.3
    risk_level: str = "at_risk"
    estimated_days_to_churn: Optional[float] = None
    tenure_days: float = 0.0
    active_categories: int = 0
    signal_count: int = 0
    confidence: float = 0.3
    fetched_at: float = 0.0
    from_cache: bool = False

    @property
    def age_seconds(self) -> float:
        return time.time() - self.fetched_at if self.fetched_at else float("inf")

    @property
    def stability_score(self) -> float:
        """Inverse of churn — how likely to stay (0-100 scale).

        Higher = more stable:
        - churn_probability 0.0 → stability 100
        - churn_probability 0.5 → stability 50
        - churn_probability 1.0 → stability 0
        """
        base = (1.0 - self.churn_probability) * 100

        # Tenure bonus: longer tenure = more stable (up to +10)
        tenure_bonus = min(self.tenure_days / 36.5, 10.0)  # 1 year = +10

        # Risk level adjustments
        risk_adj = {
            "stable": 5.0,
            "at_risk": 0.0,
            "high_risk": -10.0,
            "critical": -20.0,
        }.get(self.risk_level, 0.0)

        return max(0.0, min(100.0, base + tenure_bonus + risk_adj))


# ──────────────────────────────────────────────────────────────
# Adapter
# ──────────────────────────────────────────────────────────────


FRESH_TTL = 7200  # 2 hours — retention changes slowly
STALE_TTL = 43200  # 12 hours — stale cache for API failures


class RetentionAdapter:
    """Bridges AutoJob's WorkerRetentionAnalyzer into the swarm routing pipeline.

    Provides:
    1. analyze(wallet) → RetentionSnapshot
    2. make_retention_scorer() → Callable for DecisionSynthesizer
    """

    def __init__(
        self,
        autojob_base_url: str = "http://localhost:8899",
        timeout_s: float = 5.0,
    ):
        self.base_url = autojob_base_url.rstrip("/")
        self.timeout_s = timeout_s

        # Cache: wallet → RetentionSnapshot
        self._cache: dict[str, RetentionSnapshot] = {}

        # Stats
        self._total_requests = 0
        self._cache_hits = 0
        self._api_calls = 0
        self._api_errors = 0

    def analyze(self, wallet: str) -> RetentionSnapshot:
        """Analyze a worker's retention risk.

        4-tier fallback:
        1. Fresh cache hit
        2. Live API call
        3. Stale cache
        4. Default
        """
        self._total_requests += 1
        wallet_key = wallet.lower()

        # Tier 1: Fresh cache
        cached = self._cache.get(wallet_key)
        if cached and cached.age_seconds < FRESH_TTL:
            self._cache_hits += 1
            cached.from_cache = True
            return cached

        # Tier 2: Live API
        snapshot = self._fetch_from_api(wallet)
        if snapshot:
            self._cache[wallet_key] = snapshot
            return snapshot

        # Tier 3: Stale cache
        if cached and cached.age_seconds < STALE_TTL:
            self._cache_hits += 1
            cached.from_cache = True
            logger.info("Using stale retention cache for %s", wallet[:10])
            return cached

        # Tier 4: Default
        return RetentionSnapshot(
            wallet=wallet,
            churn_probability=0.3,
            risk_level="at_risk",
            confidence=0.1,
            fetched_at=time.time(),
        )

    def _fetch_from_api(self, wallet: str) -> Optional[RetentionSnapshot]:
        """Call AutoJob's /api/worker-retention/{wallet} endpoint."""
        self._api_calls += 1
        url = f"{self.base_url}/api/worker-retention/{wallet}"

        try:
            req = Request(url, method="GET")
            start = time.monotonic()
            with urlopen(req, timeout=self.timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            (time.monotonic() - start) * 1000

            if not data.get("success"):
                logger.warning("Retention API returned failure for %s", wallet[:10])
                self._api_errors += 1
                return None

            retention = data.get("retention", {})

            return RetentionSnapshot(
                wallet=wallet,
                churn_probability=retention.get("churn_probability", 0.3),
                risk_level=retention.get("risk_level", "at_risk"),
                estimated_days_to_churn=retention.get("estimated_days_to_churn"),
                tenure_days=retention.get("tenure_days", 0.0),
                active_categories=retention.get("active_categories", 0),
                signal_count=len(retention.get("signals", [])),
                confidence=retention.get("confidence", 0.3),
                fetched_at=time.time(),
                from_cache=False,
            )

        except (URLError, HTTPError, TimeoutError, OSError) as e:
            self._api_errors += 1
            logger.warning("Retention API error for %s: %s", wallet[:10], e)
            return None
        except Exception as e:
            self._api_errors += 1
            logger.error("Unexpected retention error for %s: %s", wallet[:10], e)
            return None

    def stats(self) -> dict:
        """Return adapter statistics."""
        return {
            "total_requests": self._total_requests,
            "cache_hits": self._cache_hits,
            "api_calls": self._api_calls,
            "api_errors": self._api_errors,
            "cache_size": len(self._cache),
            "hit_rate": (
                round(self._cache_hits / self._total_requests, 3)
                if self._total_requests
                else 0
            ),
        }


# ──────────────────────────────────────────────────────────────
# Scorer Factory
# ──────────────────────────────────────────────────────────────


def make_retention_scorer(adapter: RetentionAdapter) -> Callable:
    """Create a scorer function compatible with DecisionSynthesizer.

    Score formula:
        stability_score (0-100) — inverse of churn probability
        with tenure bonus and risk level adjustments

    Workers who are likely to stay score higher. Workers at churn risk
    score lower, especially for important/time-sensitive tasks.
    """

    def scorer(task: dict, candidate: dict) -> float:
        try:
            wallet = candidate.get("wallet", candidate.get("address", ""))
            if not wallet:
                return 50.0  # Neutral if no wallet

            snapshot = adapter.analyze(wallet)
            return snapshot.stability_score

        except Exception as e:
            logger.debug("Retention scorer error: %s", e)
            return 50.0  # Neutral on error

    return scorer
