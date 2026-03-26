"""
OutcomeAdapter — Bridges TaskOutcomePredictor into the DecisionBridge Pipeline
===============================================================================

The 9th signal: OUTCOME — "Will this specific pairing succeed?"

While the existing 8 signals answer WHO, WHAT, WHEN, HOW MUCH, and HOW WELL,
they don't directly answer: "Given everything we know, what's the probability
THIS task assigned to THIS worker will actually complete?"

The OutcomeAdapter fetches predictions from AutoJob's TaskOutcomePredictor
(exposed as /api/predict/{wallet}/{category}) and transforms them into
DecisionSynthesizer signals.

Architecture:
    Task arrives → DecisionBridge collects candidates
        → OutcomeAdapter.predict(task, wallet) → AutoJob API
        → Returns PredictionResult (probability, confidence, risks)
        → OutcomeAdapter normalizes → SignalType.OUTCOME score

Caching strategy:
    - Predictions cached per (wallet, category) for 30 minutes
    - Stale cache used on API failure (up to 4h)
    - Default prediction (0.5 probability, 0.1 confidence) on total failure
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import timezone
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

logger = logging.getLogger("em.swarm.outcome_adapter")

UTC = timezone.utc


@dataclass
class PredictionSnapshot:
    """Cached prediction for a wallet+category pair."""

    wallet: str
    category: str
    success_probability: float
    confidence: float
    recommendation: str
    risk_count: int
    risk_names: list[str] = field(default_factory=list)
    fetched_at: float = 0.0
    source: str = "api"

    @property
    def age_seconds(self) -> float:
        return time.time() - self.fetched_at

    @property
    def is_fresh(self) -> bool:
        return self.age_seconds < 1800

    @property
    def is_stale_usable(self) -> bool:
        return self.age_seconds < 14400


@dataclass
class OutcomeAdapterStats:
    api_calls: int = 0
    api_errors: int = 0
    cache_hits: int = 0
    stale_hits: int = 0
    default_fallbacks: int = 0
    total_predictions: int = 0
    avg_probability: float = 0.0
    last_api_call_ms: float = 0.0


class OutcomeAdapter:
    def __init__(self, autojob_url="http://localhost:8765", timeout_seconds=5.0):
        self.autojob_url = autojob_url.rstrip("/")
        self.timeout = timeout_seconds
        self._cache: dict[str, PredictionSnapshot] = {}
        self._stats = OutcomeAdapterStats()

    @property
    def stats(self) -> OutcomeAdapterStats:
        return self._stats

    def predict(self, wallet: str, category: str) -> PredictionSnapshot:
        cache_key = f"{wallet.lower()}:{category.lower()}"
        self._stats.total_predictions += 1

        cached = self._cache.get(cache_key)
        if cached and cached.is_fresh:
            self._stats.cache_hits += 1
            return cached

        prediction = self._fetch_from_api(wallet, category)
        if prediction:
            prediction.source = "api"
            self._cache[cache_key] = prediction
            self._update_avg(prediction.success_probability)
            return prediction

        if cached and cached.is_stale_usable:
            self._stats.stale_hits += 1
            cached.source = "stale_cache"
            return cached

        self._stats.default_fallbacks += 1
        default = PredictionSnapshot(
            wallet=wallet,
            category=category,
            success_probability=0.5,
            confidence=0.1,
            recommendation="proceed_with_caution",
            risk_count=0,
            fetched_at=time.time(),
            source="default",
        )
        self._cache[cache_key] = default
        return default

    def predict_batch(
        self, task_category: str, wallets: list[str]
    ) -> list[PredictionSnapshot]:
        return [self.predict(w, task_category) for w in wallets]

    def get_stats(self) -> dict:
        return {
            "api_calls": self._stats.api_calls,
            "api_errors": self._stats.api_errors,
            "cache_hits": self._stats.cache_hits,
            "stale_hits": self._stats.stale_hits,
            "default_fallbacks": self._stats.default_fallbacks,
            "total_predictions": self._stats.total_predictions,
            "avg_probability": round(self._stats.avg_probability, 4),
            "cache_size": len(self._cache),
        }

    def clear_cache(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count

    def _fetch_from_api(
        self, wallet: str, category: str
    ) -> Optional[PredictionSnapshot]:
        url = f"{self.autojob_url}/api/predict/{wallet}/{category}"
        self._stats.api_calls += 1
        try:
            start = time.time()
            req = Request(url, method="GET")
            req.add_header("Accept", "application/json")
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            elapsed_ms = (time.time() - start) * 1000
            self._stats.last_api_call_ms = elapsed_ms
            if not data.get("success"):
                self._stats.api_errors += 1
                return None
            pred = data.get("prediction", {})
            return PredictionSnapshot(
                wallet=wallet,
                category=category,
                success_probability=pred.get("success_probability", 0.5),
                confidence=pred.get("confidence", 0.1),
                recommendation=pred.get("recommendation", "proceed_with_caution"),
                risk_count=len(pred.get("risk_factors", [])),
                risk_names=[
                    r.get("name", "") for r in pred.get("risk_factors", [])[:5]
                ],
                fetched_at=time.time(),
            )
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
            self._stats.api_errors += 1
            logger.debug(f"OutcomeAdapter API error for {wallet}/{category}: {e}")
            return None
        except Exception as e:
            self._stats.api_errors += 1
            logger.error(f"OutcomeAdapter unexpected error: {e}")
            return None

    def _update_avg(self, probability: float) -> None:
        api_count = self._stats.api_calls - self._stats.api_errors
        if api_count <= 1:
            self._stats.avg_probability = probability
        else:
            alpha = 0.1
            self._stats.avg_probability = (
                alpha * probability + (1 - alpha) * self._stats.avg_probability
            )


def make_outcome_scorer(adapter: OutcomeAdapter) -> Callable:
    """
    Create a scorer function compatible with DecisionSynthesizer.
    Score = 70% probability + 20% confidence - 10% risk penalty.
    """

    def scorer(task: dict, candidate: dict) -> float:
        wallet = candidate.get("wallet", candidate.get("agent_id", ""))
        category = task.get("category", task.get("task_type", "general"))
        if not wallet:
            return 50.0
        prediction = adapter.predict(wallet, category)
        prob_score = prediction.success_probability * 100
        conf_score = prediction.confidence * 100
        risk_penalty = min(30, prediction.risk_count * 8)
        score = prob_score * 0.70 + conf_score * 0.20 - risk_penalty * 0.10
        return max(0.0, min(100.0, score))

    return scorer
