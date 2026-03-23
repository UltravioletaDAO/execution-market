"""
AffinityAdapter — 17th Signal for DecisionSynthesizer
======================================================

Bridges AutoJob's WorkerAffinityEngine into the swarm routing pipeline.
Adds worker-task preference as a scoring signal: workers with high affinity
for a task's category get a score boost, workers who avoid it get penalized.

Architecture:
    AutoJob WorkerAffinityEngine → AffinityAdapter → DecisionSynthesizer
                                        ↓
    SignalType.AFFINITY (score 0-100, confidence 0-1)

Why it matters:
    The existing 16 signals answer: CAN they do it? WILL they do it well?
    Affinity answers: Do they WANT to do it?

    A motivated worker completes faster, submits better evidence, and
    returns for more tasks. Matching preference improves every downstream
    metric: time-to-accept, evidence quality, worker retention.

Integration:
    from mcp_server.swarm.affinity_adapter import AffinityAdapter, make_affinity_scorer
    from mcp_server.swarm.decision_synthesizer import DecisionSynthesizer

    synthesizer = DecisionSynthesizer()
    adapter = AffinityAdapter(autojob_url="http://localhost:8765")
    synthesizer.register_signal("affinity", make_affinity_scorer(adapter))
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import timezone
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("em.swarm.affinity_adapter")

UTC = timezone.utc


# ──────────────────────────────────────────────────────────────
# Data Types
# ──────────────────────────────────────────────────────────────


@dataclass
class AffinityScore:
    """Single worker's affinity score for a task."""

    worker_id: str
    category: str
    score: float  # 0-100 (normalized for DecisionSynthesizer)
    confidence: float  # 0-1
    style: str  # specialist | generalist | explorer
    is_sweet_spot: bool  # True if this category is the worker's sweet spot
    signal_breakdown: dict = field(default_factory=dict)


@dataclass
class AffinityBatchResult:
    """Batch affinity scores for routing decisions."""

    scores: dict = field(default_factory=dict)  # worker_id -> AffinityScore
    category: str = ""
    cached: bool = False
    latency_ms: float = 0.0
    error: str = ""


# ──────────────────────────────────────────────────────────────
# Cache
# ──────────────────────────────────────────────────────────────


@dataclass
class CacheEntry:
    """Cached affinity profile data."""

    data: dict
    fetched_at: float
    ttl_seconds: float = 3600.0  # 1 hour default

    @property
    def is_stale(self) -> bool:
        return (time.time() - self.fetched_at) > self.ttl_seconds


class AffinityCache:
    """Simple in-memory cache for affinity profiles."""

    def __init__(self, ttl_seconds: float = 3600.0, max_entries: int = 500):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._cache: dict = {}
        self._hits = 0
        self._misses = 0

    def get(self, worker_id: str) -> Optional[dict]:
        """Get cached profile, None if missing or stale."""
        entry = self._cache.get(worker_id)
        if entry and not entry.is_stale:
            self._hits += 1
            return entry.data
        if entry and entry.is_stale:
            del self._cache[worker_id]
        self._misses += 1
        return None

    def put(self, worker_id: str, data: dict):
        """Cache a profile, evicting oldest if full."""
        if len(self._cache) >= self.max_entries:
            # Evict oldest
            oldest_key = min(self._cache, key=lambda k: self._cache[k].fetched_at)
            del self._cache[oldest_key]
        self._cache[worker_id] = CacheEntry(
            data=data, fetched_at=time.time(), ttl_seconds=self.ttl_seconds
        )

    def invalidate(self, worker_id: str):
        """Remove a specific entry."""
        self._cache.pop(worker_id, None)

    def clear(self):
        """Clear all entries."""
        self._cache.clear()

    @property
    def stats(self) -> dict:
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(1, self._hits + self._misses),
        }


# ──────────────────────────────────────────────────────────────
# Adapter
# ──────────────────────────────────────────────────────────────


class AffinityAdapter:
    """
    Bridges AutoJob WorkerAffinityEngine to EM swarm routing.

    Fetches affinity profiles from AutoJob API or uses local fallback data.
    Converts affinity scores (0-1) to routing signal scores (0-100).
    """

    def __init__(
        self,
        autojob_url: str = "http://localhost:8765",
        cache_ttl: float = 3600.0,
        timeout_seconds: float = 5.0,
        fallback_profiles: Optional[dict] = None,
    ):
        self.autojob_url = autojob_url.rstrip("/")
        self.timeout = timeout_seconds
        self.cache = AffinityCache(ttl_seconds=cache_ttl)
        self.fallback_profiles = fallback_profiles or {}
        self._api_available = True
        self._last_api_check = 0.0
        self._api_check_interval = 300.0  # Re-check every 5 min

    def score_worker(self, worker_id: str, category: str) -> AffinityScore:
        """
        Get affinity score for a single worker-category pair.

        Falls back gracefully: API → cache → fallback profiles → neutral.
        """
        profile = self._get_profile(worker_id)
        return self._profile_to_score(worker_id, category, profile)

    def score_batch(
        self,
        worker_ids: list,
        category: str,
    ) -> AffinityBatchResult:
        """
        Score multiple workers for the same task category.
        """
        start = time.time()
        scores = {}

        for wid in worker_ids:
            try:
                scores[wid] = self.score_worker(wid, category)
            except Exception as e:
                logger.warning("Affinity score failed for %s: %s", wid, e)
                scores[wid] = self._neutral_score(wid, category)

        return AffinityBatchResult(
            scores=scores,
            category=category,
            latency_ms=(time.time() - start) * 1000,
        )

    def get_fleet_matrix(self) -> dict:
        """Get the full worker×category affinity matrix."""
        try:
            url = f"{self.autojob_url}/api/affinity/fleet"
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.debug("Fleet matrix unavailable: %s", e)
            return {"matrix": {}, "coverage": {}, "gaps": [], "overlaps": []}

    def invalidate_worker(self, worker_id: str):
        """Invalidate cached profile after task completion."""
        self.cache.invalidate(worker_id)

    @property
    def stats(self) -> dict:
        return {
            "api_available": self._api_available,
            "cache": self.cache.stats,
            "fallback_profiles": len(self.fallback_profiles),
        }

    # ────────────────────────────────────────────
    # Internal
    # ────────────────────────────────────────────

    def _get_profile(self, worker_id: str) -> Optional[dict]:
        """Get affinity profile with 4-tier fallback."""
        # Tier 1: Fresh cache
        cached = self.cache.get(worker_id)
        if cached:
            return cached

        # Tier 2: Live API
        if self._should_try_api():
            profile = self._fetch_from_api(worker_id)
            if profile:
                self.cache.put(worker_id, profile)
                return profile

        # Tier 3: Fallback profiles
        if worker_id in self.fallback_profiles:
            return self.fallback_profiles[worker_id]

        # Tier 4: None (will produce neutral score)
        return None

    def _fetch_from_api(self, worker_id: str) -> Optional[dict]:
        """Fetch affinity profile from AutoJob API."""
        try:
            url = f"{self.autojob_url}/api/affinity/{worker_id}"
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
                self._api_available = True
                return data
        except (URLError, HTTPError, TimeoutError) as e:
            logger.debug("AutoJob affinity API unavailable: %s", e)
            self._api_available = False
            self._last_api_check = time.time()
            return None
        except Exception as e:
            logger.warning("Unexpected error fetching affinity: %s", e)
            return None

    def _should_try_api(self) -> bool:
        """Check if we should attempt an API call."""
        if self._api_available:
            return True
        # Retry after interval
        return (time.time() - self._last_api_check) > self._api_check_interval

    def _profile_to_score(
        self,
        worker_id: str,
        category: str,
        profile: Optional[dict],
    ) -> AffinityScore:
        """Convert affinity profile to routing score."""
        if not profile or "affinities" not in profile:
            return self._neutral_score(worker_id, category)

        affinities = profile.get("affinities", {})
        cat_data = affinities.get(category)

        if not cat_data:
            return AffinityScore(
                worker_id=worker_id,
                category=category,
                score=50.0,  # Neutral
                confidence=0.0,
                style=profile.get("dominant_style", "generalist"),
                is_sweet_spot=False,
            )

        # Convert 0-1 score to 0-100
        raw_score = cat_data.get("score", 0.5)
        score = max(0.0, min(100.0, raw_score * 100))

        confidence = cat_data.get("confidence", 0.0)
        sweet_spot = profile.get("sweet_spot") == category
        style = profile.get("dominant_style", "generalist")

        # Bonus for sweet spot
        if sweet_spot and confidence > 0.5:
            score = min(100.0, score * 1.1)

        return AffinityScore(
            worker_id=worker_id,
            category=category,
            score=round(score, 2),
            confidence=round(confidence, 3),
            style=style,
            is_sweet_spot=sweet_spot,
            signal_breakdown={
                "selection_rate": cat_data.get("selection_rate", 0.0),
                "speed_percentile": cat_data.get("speed_percentile", 0.0),
                "quality_percentile": cat_data.get("quality_percentile", 0.0),
                "response_velocity": cat_data.get("response_velocity", 0.0),
                "rebid_rate": cat_data.get("rebid_rate", 0.0),
                "rejection_rate": cat_data.get("rejection_rate", 0.0),
            },
        )

    def _neutral_score(self, worker_id: str, category: str) -> AffinityScore:
        """Produce a neutral score when no data available."""
        return AffinityScore(
            worker_id=worker_id,
            category=category,
            score=50.0,
            confidence=0.0,
            style="generalist",
            is_sweet_spot=False,
        )


# ──────────────────────────────────────────────────────────────
# DecisionSynthesizer Integration
# ──────────────────────────────────────────────────────────────


def make_affinity_scorer(adapter: AffinityAdapter) -> Callable:
    """
    Create a scorer function compatible with DecisionSynthesizer.register_signal().

    Usage:
        synthesizer.register_signal("affinity", make_affinity_scorer(adapter))
    """

    def score(task: dict, candidate: dict) -> float:
        """Returns score 0-100, compatible with DecisionSynthesizer."""
        worker_id = (
            candidate.get("wallet")
            or candidate.get("agent_id")
            or candidate.get("id", "")
        )
        category = task.get("category", "unknown")
        result = adapter.score_worker(worker_id, category)
        return result.score

    return score
