"""
Tests for OutcomeAdapter — the 9th signal in the decision pipeline.
"""

import json
import time
import pytest
from unittest.mock import patch, MagicMock

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from swarm.outcome_adapter import (
    OutcomeAdapter,
    PredictionSnapshot,
    OutcomeAdapterStats,
    make_outcome_scorer,
)
from swarm.decision_synthesizer import SignalType


# ──────────────────────────────────────────────────────────
# PredictionSnapshot
# ──────────────────────────────────────────────────────────


class TestPredictionSnapshot:

    def test_fresh_prediction(self):
        snap = PredictionSnapshot(
            wallet="0x1", category="delivery",
            success_probability=0.8, confidence=0.7,
            recommendation="proceed", risk_count=1,
            fetched_at=time.time(),
        )
        assert snap.is_fresh
        assert snap.is_stale_usable

    def test_stale_prediction(self):
        snap = PredictionSnapshot(
            wallet="0x1", category="delivery",
            success_probability=0.8, confidence=0.7,
            recommendation="proceed", risk_count=0,
            fetched_at=time.time() - 3600,
        )
        assert not snap.is_fresh
        assert snap.is_stale_usable

    def test_expired_prediction(self):
        snap = PredictionSnapshot(
            wallet="0x1", category="delivery",
            success_probability=0.8, confidence=0.7,
            recommendation="proceed", risk_count=0,
            fetched_at=time.time() - 20000,
        )
        assert not snap.is_fresh
        assert not snap.is_stale_usable

    def test_age_seconds(self):
        snap = PredictionSnapshot(
            wallet="0x1", category="delivery",
            success_probability=0.5, confidence=0.5,
            recommendation="defer", risk_count=0,
            fetched_at=time.time() - 60,
        )
        assert snap.age_seconds >= 59


# ──────────────────────────────────────────────────────────
# OutcomeAdapter — Cache Behavior
# ──────────────────────────────────────────────────────────


class TestCacheBehavior:

    def test_default_fallback_on_no_api(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        result = adapter.predict("0xWallet", "delivery")
        assert result.source == "default"
        assert result.success_probability == 0.5
        assert result.confidence == 0.1
        assert adapter.stats.default_fallbacks == 1

    def test_cache_hit(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        result1 = adapter.predict("0xA", "delivery")
        assert result1.source == "default"
        result2 = adapter.predict("0xA", "delivery")
        assert adapter.stats.cache_hits == 1

    def test_different_keys_no_collision(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        adapter.predict("0xA", "delivery")
        adapter.predict("0xB", "photography")
        assert adapter.stats.total_predictions == 2
        assert adapter.stats.default_fallbacks == 2

    def test_clear_cache(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        adapter.predict("0xA", "delivery")
        adapter.predict("0xB", "delivery")
        count = adapter.clear_cache()
        assert count == 2

    def test_stale_cache_used_on_api_failure(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        cache_key = "0xwallet:delivery"
        adapter._cache[cache_key] = PredictionSnapshot(
            wallet="0xWallet", category="delivery",
            success_probability=0.85, confidence=0.7,
            recommendation="proceed", risk_count=0,
            fetched_at=time.time() - 3600,
            source="api",
        )
        result = adapter.predict("0xWallet", "delivery")
        assert result.success_probability == 0.85
        assert result.source == "stale_cache"
        assert adapter.stats.stale_hits == 1


# ──────────────────────────────────────────────────────────
# Stats
# ──────────────────────────────────────────────────────────


class TestStats:

    def test_initial_stats(self):
        adapter = OutcomeAdapter()
        stats = adapter.get_stats()
        assert stats["api_calls"] == 0
        assert stats["total_predictions"] == 0

    def test_stats_after_predictions(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        adapter.predict("0xA", "d1")
        adapter.predict("0xB", "d2")
        adapter.predict("0xA", "d1")
        stats = adapter.get_stats()
        assert stats["total_predictions"] == 3
        assert stats["cache_hits"] == 1
        assert stats["cache_size"] == 2


# ──────────────────────────────────────────────────────────
# Batch
# ──────────────────────────────────────────────────────────


class TestBatchPrediction:

    def test_batch_returns_list(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        results = adapter.predict_batch("delivery", ["0xA", "0xB", "0xC"])
        assert len(results) == 3
        assert all(isinstance(r, PredictionSnapshot) for r in results)


# ──────────────────────────────────────────────────────────
# Signal Scorer
# ──────────────────────────────────────────────────────────


class TestOutcomeScorer:

    def test_scorer_returns_score(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        scorer = make_outcome_scorer(adapter)
        score = scorer({"category": "delivery"}, {"wallet": "0xTest"})
        assert 0.0 <= score <= 100.0

    def test_scorer_no_wallet_returns_neutral(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        scorer = make_outcome_scorer(adapter)
        score = scorer({"category": "delivery"}, {})
        assert score == 50.0

    def test_high_probability_high_score(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        cache_key = "0xgood:delivery"
        adapter._cache[cache_key] = PredictionSnapshot(
            wallet="0xGood", category="delivery",
            success_probability=0.95, confidence=0.9,
            recommendation="proceed", risk_count=0,
            fetched_at=time.time(), source="api",
        )
        scorer = make_outcome_scorer(adapter)
        score = scorer({"category": "delivery"}, {"wallet": "0xGood"})
        assert score > 70.0

    def test_low_probability_low_score(self):
        adapter = OutcomeAdapter(autojob_url="http://localhost:1/unreachable")
        cache_key = "0xbad:delivery"
        adapter._cache[cache_key] = PredictionSnapshot(
            wallet="0xBad", category="delivery",
            success_probability=0.15, confidence=0.8,
            recommendation="reject", risk_count=4,
            fetched_at=time.time(), source="api",
        )
        scorer = make_outcome_scorer(adapter)
        score = scorer({"category": "delivery"}, {"wallet": "0xBad"})
        assert score < 40.0


# ──────────────────────────────────────────────────────────
# DecisionSynthesizer Integration
# ──────────────────────────────────────────────────────────


class TestSynthesizerIntegration:

    def test_outcome_signal_type_exists(self):
        assert hasattr(SignalType, "OUTCOME")
        assert SignalType.OUTCOME == "outcome"

    def test_signal_count_at_least_nine(self):
        signal_types = list(SignalType)
        assert len(signal_types) >= 9
        names = [s.value for s in signal_types]
        assert "outcome" in names
        assert "performance" in names
        assert "pricing" in names


# ──────────────────────────────────────────────────────────
# DecisionBridge Wiring
# ──────────────────────────────────────────────────────────


class TestBridgeWiring:

    def test_bridge_accepts_outcome_adapter(self):
        from swarm.decision_bridge import DecisionBridge
        from swarm.decision_synthesizer import DecisionSynthesizer

        adapter = OutcomeAdapter()
        bridge = DecisionBridge(
            synthesizer=DecisionSynthesizer(),
            orchestrator=MagicMock(),
            outcome_adapter=adapter,
        )
        assert bridge.outcome_adapter is adapter

    def test_bridge_registers_outcome_signal(self):
        from swarm.decision_bridge import DecisionBridge
        from swarm.decision_synthesizer import DecisionSynthesizer

        adapter = OutcomeAdapter()
        synth = DecisionSynthesizer()
        bridge = DecisionBridge(
            synthesizer=synth,
            orchestrator=MagicMock(),
            outcome_adapter=adapter,
        )
        registered = list(synth._providers.keys())
        assert SignalType.OUTCOME in registered
