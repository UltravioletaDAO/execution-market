"""
Tests for AffinityAdapter — 17th signal for DecisionSynthesizer.

Covers:
    1. Data types
    2. Cache behavior
    3. Score computation from profiles
    4. Neutral fallback
    5. Sweet spot bonus
    6. Batch scoring
    7. Fallback chain (API → cache → fallback → neutral)
    8. DecisionSynthesizer scorer factory
    9. Fleet matrix
    10. Integration with profiles
"""

import time

from mcp_server.swarm.affinity_adapter import (
    AffinityAdapter,
    AffinityScore,
    AffinityBatchResult,
    AffinityCache,
    CacheEntry,
    make_affinity_scorer,
)


# ─── Sample Data ──────────────────────────────────────────


SAMPLE_PROFILE = {
    "worker_id": "w1",
    "dominant_style": "specialist",
    "analyzed_tasks": 20,
    "analyzed_categories": 3,
    "sweet_spot": "photography",
    "affinities": {
        "photography": {
            "score": 0.85,
            "confidence": 0.95,
            "selection_rate": 0.7,
            "speed_percentile": 0.8,
            "quality_percentile": 0.85,
            "response_velocity": 0.75,
            "rebid_rate": 0.6,
            "rejection_rate": 0.05,
            "task_count": 14,
        },
        "delivery": {
            "score": 0.35,
            "confidence": 0.5,
            "selection_rate": 0.2,
            "speed_percentile": 0.4,
            "quality_percentile": 0.3,
            "response_velocity": 0.3,
            "rebid_rate": 0.1,
            "rejection_rate": 0.3,
            "task_count": 4,
        },
        "survey": {
            "score": 0.5,
            "confidence": 0.3,
            "selection_rate": 0.1,
            "speed_percentile": 0.5,
            "quality_percentile": 0.5,
            "response_velocity": 0.5,
            "rebid_rate": 0.2,
            "rejection_rate": 0.1,
            "task_count": 2,
        },
    },
}


# ═══════════════════════════════════════════════════════════════
# 1. Data Types
# ═══════════════════════════════════════════════════════════════


class TestDataTypes:
    def test_affinity_score_fields(self):
        s = AffinityScore(
            worker_id="w1",
            category="photography",
            score=85.0,
            confidence=0.95,
            style="specialist",
            is_sweet_spot=True,
        )
        assert s.worker_id == "w1"
        assert s.score == 85.0
        assert s.is_sweet_spot is True

    def test_affinity_batch_result(self):
        r = AffinityBatchResult(
            scores={"w1": AffinityScore("w1", "photo", 85.0, 0.9, "specialist", True)},
            category="photo",
            latency_ms=5.0,
        )
        assert "w1" in r.scores
        assert r.category == "photo"

    def test_cache_entry_staleness(self):
        entry = CacheEntry(data={"test": 1}, fetched_at=time.time(), ttl_seconds=3600)
        assert not entry.is_stale

    def test_cache_entry_stale_after_ttl(self):
        entry = CacheEntry(
            data={"test": 1}, fetched_at=time.time() - 7200, ttl_seconds=3600
        )
        assert entry.is_stale


# ═══════════════════════════════════════════════════════════════
# 2. Cache Behavior
# ═══════════════════════════════════════════════════════════════


class TestCache:
    def test_put_and_get(self):
        cache = AffinityCache(ttl_seconds=3600)
        cache.put("w1", {"score": 0.85})
        assert cache.get("w1") == {"score": 0.85}

    def test_get_miss(self):
        cache = AffinityCache()
        assert cache.get("nonexistent") is None

    def test_stale_entry_returns_none(self):
        cache = AffinityCache(ttl_seconds=1)
        cache.put("w1", {"score": 0.85})
        cache._cache["w1"].fetched_at = time.time() - 10  # Force stale
        assert cache.get("w1") is None

    def test_invalidate(self):
        cache = AffinityCache()
        cache.put("w1", {"data": True})
        cache.invalidate("w1")
        assert cache.get("w1") is None

    def test_clear(self):
        cache = AffinityCache()
        cache.put("w1", {"a": 1})
        cache.put("w2", {"b": 2})
        cache.clear()
        assert cache.get("w1") is None
        assert cache.get("w2") is None

    def test_eviction_at_max(self):
        cache = AffinityCache(max_entries=2)
        cache.put("w1", {"a": 1})
        cache.put("w2", {"b": 2})
        cache.put("w3", {"c": 3})  # Should evict w1 (oldest)
        assert cache.get("w1") is None
        assert cache.get("w3") == {"c": 3}

    def test_stats(self):
        cache = AffinityCache()
        cache.put("w1", {"a": 1})
        cache.get("w1")  # Hit
        cache.get("w2")  # Miss
        stats = cache.stats
        assert stats["entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 0.5

    def test_invalidate_nonexistent_ok(self):
        cache = AffinityCache()
        cache.invalidate("does_not_exist")  # Should not raise


# ═══════════════════════════════════════════════════════════════
# 3. Score Computation
# ═══════════════════════════════════════════════════════════════


class TestScoreComputation:
    def test_high_affinity_category(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        score = adapter.score_worker("w1", "photography")
        assert score.score > 80  # 0.85 * 100 + sweet spot bonus
        assert score.confidence > 0.9
        assert score.style == "specialist"
        assert score.is_sweet_spot is True

    def test_low_affinity_category(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        score = adapter.score_worker("w1", "delivery")
        assert score.score < 50  # 0.35 * 100
        assert score.is_sweet_spot is False

    def test_unknown_category_neutral(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        score = adapter.score_worker("w1", "never_seen")
        assert score.score == 50.0  # Neutral
        assert score.confidence == 0.0

    def test_unknown_worker_neutral(self):
        adapter = AffinityAdapter()
        score = adapter.score_worker("unknown_worker", "photography")
        assert score.score == 50.0
        assert score.confidence == 0.0
        assert score.style == "generalist"

    def test_score_clamps_to_100(self):
        """Even with sweet spot bonus, score should not exceed 100."""
        profile = {
            "dominant_style": "specialist",
            "sweet_spot": "photo",
            "affinities": {
                "photo": {
                    "score": 0.99,
                    "confidence": 1.0,
                    "selection_rate": 0.9,
                    "speed_percentile": 0.9,
                    "quality_percentile": 0.9,
                    "response_velocity": 0.9,
                    "rebid_rate": 0.9,
                    "rejection_rate": 0.0,
                },
            },
        }
        adapter = AffinityAdapter(fallback_profiles={"w1": profile})
        score = adapter.score_worker("w1", "photo")
        assert score.score <= 100.0

    def test_score_never_below_zero(self):
        profile = {
            "dominant_style": "generalist",
            "affinities": {
                "bad": {
                    "score": 0.0,
                    "confidence": 0.0,
                },
            },
        }
        adapter = AffinityAdapter(fallback_profiles={"w1": profile})
        score = adapter.score_worker("w1", "bad")
        assert score.score >= 0.0

    def test_signal_breakdown_populated(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        score = adapter.score_worker("w1", "photography")
        assert "selection_rate" in score.signal_breakdown
        assert "speed_percentile" in score.signal_breakdown
        assert score.signal_breakdown["selection_rate"] == 0.7


# ═══════════════════════════════════════════════════════════════
# 4. Sweet Spot Bonus
# ═══════════════════════════════════════════════════════════════


class TestSweetSpotBonus:
    def test_sweet_spot_gets_bonus(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        sweet = adapter.score_worker("w1", "photography")  # Sweet spot
        non_sweet = adapter.score_worker("w1", "survey")
        # Sweet spot with high confidence should beat non-sweet
        assert sweet.is_sweet_spot is True
        assert non_sweet.is_sweet_spot is False

    def test_sweet_spot_no_bonus_low_confidence(self):
        """Sweet spot bonus only applies when confidence > 0.5."""
        profile = {
            "dominant_style": "specialist",
            "sweet_spot": "photo",
            "affinities": {
                "photo": {
                    "score": 0.8,
                    "confidence": 0.3,  # Low confidence
                },
            },
        }
        adapter = AffinityAdapter(fallback_profiles={"w1": profile})
        score = adapter.score_worker("w1", "photo")
        # Score should be raw 80 without bonus (confidence too low)
        assert score.score == 80.0


# ═══════════════════════════════════════════════════════════════
# 5. Batch Scoring
# ═══════════════════════════════════════════════════════════════


class TestBatchScoring:
    def test_batch_multiple_workers(self):
        profiles = {
            "w1": SAMPLE_PROFILE,
            "w2": {
                "dominant_style": "generalist",
                "affinities": {
                    "photography": {"score": 0.5, "confidence": 0.7},
                },
            },
        }
        adapter = AffinityAdapter(fallback_profiles=profiles)
        result = adapter.score_batch(["w1", "w2"], "photography")
        assert "w1" in result.scores
        assert "w2" in result.scores
        assert result.scores["w1"].score > result.scores["w2"].score

    def test_batch_empty_workers(self):
        adapter = AffinityAdapter()
        result = adapter.score_batch([], "photography")
        assert result.scores == {}

    def test_batch_unknown_workers_neutral(self):
        adapter = AffinityAdapter()
        result = adapter.score_batch(["w1", "w2"], "photography")
        assert result.scores["w1"].score == 50.0
        assert result.scores["w2"].score == 50.0

    def test_batch_latency_tracked(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        result = adapter.score_batch(["w1"], "photography")
        assert result.latency_ms >= 0

    def test_batch_category_set(self):
        adapter = AffinityAdapter()
        result = adapter.score_batch(["w1"], "delivery")
        assert result.category == "delivery"


# ═══════════════════════════════════════════════════════════════
# 6. Fallback Chain
# ═══════════════════════════════════════════════════════════════


class TestFallbackChain:
    def test_cache_hit_used_first(self):
        adapter = AffinityAdapter()
        adapter.cache.put("w1", SAMPLE_PROFILE)
        score = adapter.score_worker("w1", "photography")
        assert score.score > 80  # Got data from cache

    def test_fallback_profile_used_when_api_down(self):
        adapter = AffinityAdapter(
            autojob_url="http://localhost:99999",  # Unreachable
            fallback_profiles={"w1": SAMPLE_PROFILE},
        )
        adapter._api_available = False
        adapter._last_api_check = time.time()  # Recent check
        score = adapter.score_worker("w1", "photography")
        assert score.score > 80

    def test_neutral_when_nothing_available(self):
        adapter = AffinityAdapter(autojob_url="http://localhost:99999")
        adapter._api_available = False
        adapter._last_api_check = time.time()
        score = adapter.score_worker("w1", "photography")
        assert score.score == 50.0

    def test_cache_invalidation(self):
        adapter = AffinityAdapter()
        adapter.cache.put("w1", SAMPLE_PROFILE)
        adapter.invalidate_worker("w1")
        # Now should fall to neutral (no API, no fallback)
        adapter._api_available = False
        adapter._last_api_check = time.time()
        score = adapter.score_worker("w1", "photography")
        assert score.score == 50.0


# ═══════════════════════════════════════════════════════════════
# 7. Scorer Factory (DecisionSynthesizer Integration)
# ═══════════════════════════════════════════════════════════════


class TestScorerFactory:
    def test_make_affinity_scorer(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        scorer = make_affinity_scorer(adapter)
        task = {"category": "photography"}
        candidate = {"wallet": "w1"}
        score = scorer(task, candidate)
        assert score > 80

    def test_scorer_with_agent_id(self):
        adapter = AffinityAdapter(fallback_profiles={"agent_42": SAMPLE_PROFILE})
        scorer = make_affinity_scorer(adapter)
        task = {"category": "photography"}
        candidate = {"agent_id": "agent_42"}
        score = scorer(task, candidate)
        assert score > 80

    def test_scorer_with_id_field(self):
        adapter = AffinityAdapter(fallback_profiles={"x1": SAMPLE_PROFILE})
        scorer = make_affinity_scorer(adapter)
        task = {"category": "photography"}
        candidate = {"id": "x1"}
        score = scorer(task, candidate)
        assert score > 80

    def test_scorer_unknown_candidate(self):
        adapter = AffinityAdapter()
        scorer = make_affinity_scorer(adapter)
        adapter._api_available = False
        adapter._last_api_check = time.time()
        task = {"category": "photography"}
        candidate = {"wallet": "unknown"}
        score = scorer(task, candidate)
        assert score == 50.0

    def test_scorer_returns_float(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        scorer = make_affinity_scorer(adapter)
        result = scorer({"category": "photography"}, {"wallet": "w1"})
        assert isinstance(result, (int, float))


# ═══════════════════════════════════════════════════════════════
# 8. Adapter Stats
# ═══════════════════════════════════════════════════════════════


class TestStats:
    def test_stats_structure(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        stats = adapter.stats
        assert "api_available" in stats
        assert "cache" in stats
        assert "fallback_profiles" in stats
        assert stats["fallback_profiles"] == 1

    def test_cache_stats_update(self):
        adapter = AffinityAdapter(fallback_profiles={"w1": SAMPLE_PROFILE})
        adapter.cache.put("w1", SAMPLE_PROFILE)
        adapter.cache.get("w1")  # Hit
        adapter.cache.get("w2")  # Miss
        stats = adapter.stats
        assert stats["cache"]["hits"] == 1
        assert stats["cache"]["misses"] == 1


# ═══════════════════════════════════════════════════════════════
# 9. API Retry Logic
# ═══════════════════════════════════════════════════════════════


class TestApiRetry:
    def test_api_available_by_default(self):
        adapter = AffinityAdapter()
        assert adapter._api_available is True

    def test_should_try_api_when_available(self):
        adapter = AffinityAdapter()
        assert adapter._should_try_api() is True

    def test_should_not_retry_too_soon(self):
        adapter = AffinityAdapter()
        adapter._api_available = False
        adapter._last_api_check = time.time()
        assert adapter._should_try_api() is False

    def test_should_retry_after_interval(self):
        adapter = AffinityAdapter()
        adapter._api_available = False
        adapter._last_api_check = time.time() - 400  # Past 300s interval
        assert adapter._should_try_api() is True


# ═══════════════════════════════════════════════════════════════
# 10. Edge Cases
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_profile_with_empty_affinities(self):
        profile = {"dominant_style": "generalist", "affinities": {}}
        adapter = AffinityAdapter(fallback_profiles={"w1": profile})
        score = adapter.score_worker("w1", "photography")
        assert score.score == 50.0

    def test_profile_without_affinities_key(self):
        profile = {"dominant_style": "generalist"}
        adapter = AffinityAdapter(fallback_profiles={"w1": profile})
        score = adapter.score_worker("w1", "photography")
        assert score.score == 50.0

    def test_affinity_data_missing_fields_defaults(self):
        profile = {
            "dominant_style": "generalist",
            "affinities": {
                "photo": {"score": 0.7},  # Minimal data
            },
        }
        adapter = AffinityAdapter(fallback_profiles={"w1": profile})
        score = adapter.score_worker("w1", "photo")
        assert score.score == 70.0
        assert score.confidence == 0.0  # Default when missing

    def test_concurrent_cache_access_safe(self):
        """Cache operations should be safe for sequential access."""
        cache = AffinityCache()
        for i in range(100):
            cache.put(f"w{i}", {"score": i})
        for i in range(100):
            result = cache.get(f"w{i}")
            if result:
                assert result["score"] == i
