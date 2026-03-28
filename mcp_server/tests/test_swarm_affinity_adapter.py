"""
Test Suite: AffinityAdapter — Worker-Task Preference Matching
================================================================

Tests cover:
    1. AffinityScore data type
    2. AffinityCache (get, put, eviction, staleness, stats)
    3. AffinityAdapter (score_worker, score_batch, fallback tiers)
    4. Profile-to-score conversion (sweet spot, neutral, categories)
    5. Scorer factory (make_affinity_scorer)
    6. Edge cases (no data, API unavailable, batch errors)
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


# ══════════════════════════════════════════════════════════════
# Data Type Tests
# ══════════════════════════════════════════════════════════════


class TestAffinityScore:
    def test_basic(self):
        score = AffinityScore(
            worker_id="0x001",
            category="photo",
            score=85.0,
            confidence=0.9,
            style="specialist",
            is_sweet_spot=True,
        )
        assert score.score == 85.0
        assert score.is_sweet_spot is True

    def test_neutral(self):
        score = AffinityScore(
            worker_id="0x001",
            category="photo",
            score=50.0,
            confidence=0.0,
            style="generalist",
            is_sweet_spot=False,
        )
        assert score.confidence == 0.0


class TestAffinityBatchResult:
    def test_empty(self):
        result = AffinityBatchResult()
        assert result.scores == {}
        assert result.error == ""

    def test_with_scores(self):
        result = AffinityBatchResult(
            scores={
                "0x001": AffinityScore(
                    worker_id="0x001",
                    category="photo",
                    score=80.0,
                    confidence=0.8,
                    style="specialist",
                    is_sweet_spot=True,
                )
            },
            category="photo",
            latency_ms=15.0,
        )
        assert len(result.scores) == 1


# ══════════════════════════════════════════════════════════════
# Cache Tests
# ══════════════════════════════════════════════════════════════


class TestCacheEntry:
    def test_fresh(self):
        entry = CacheEntry(data={"test": True}, fetched_at=time.time())
        assert entry.is_stale is False

    def test_stale(self):
        entry = CacheEntry(data={}, fetched_at=time.time() - 7200, ttl_seconds=3600)
        assert entry.is_stale is True


class TestAffinityCache:
    def test_put_and_get(self):
        cache = AffinityCache()
        cache.put("0x001", {"affinities": {"photo": {"score": 0.8}}})
        result = cache.get("0x001")
        assert result is not None
        assert result["affinities"]["photo"]["score"] == 0.8

    def test_miss(self):
        cache = AffinityCache()
        assert cache.get("nonexistent") is None

    def test_stale_eviction(self):
        cache = AffinityCache(ttl_seconds=0.01)
        cache.put("0x001", {"test": True})
        time.sleep(0.02)
        assert cache.get("0x001") is None

    def test_max_entries_eviction(self):
        cache = AffinityCache(max_entries=3)
        for i in range(5):
            cache.put(f"0x{i:03x}", {"id": i})
        assert len(cache._cache) <= 3

    def test_invalidate(self):
        cache = AffinityCache()
        cache.put("0x001", {"data": True})
        cache.invalidate("0x001")
        assert cache.get("0x001") is None

    def test_clear(self):
        cache = AffinityCache()
        cache.put("0x001", {})
        cache.put("0x002", {})
        cache.clear()
        assert len(cache._cache) == 0

    def test_stats(self):
        cache = AffinityCache()
        cache.put("0x001", {"data": True})
        cache.get("0x001")  # hit
        cache.get("0x002")  # miss

        stats = cache.stats
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["entries"] == 1
        assert stats["hit_rate"] == 0.5

    def test_stats_empty(self):
        cache = AffinityCache()
        stats = cache.stats
        assert stats["hit_rate"] == 0.0


# ══════════════════════════════════════════════════════════════
# Adapter Tests
# ══════════════════════════════════════════════════════════════


class TestAffinityAdapterScoring:
    def test_neutral_score_no_data(self):
        adapter = AffinityAdapter()
        score = adapter.score_worker("0xunknown", "photo")
        assert score.score == 50.0
        assert score.confidence == 0.0
        assert score.style == "generalist"

    def test_cached_profile(self):
        adapter = AffinityAdapter()
        adapter.cache.put(
            "0x001",
            {
                "affinities": {"photo": {"score": 0.85, "confidence": 0.9}},
                "dominant_style": "specialist",
                "sweet_spot": "photo",
            },
        )

        score = adapter.score_worker("0x001", "photo")
        assert score.score > 80  # 0.85 * 100 * 1.1 (sweet spot bonus)
        assert score.is_sweet_spot is True
        assert score.style == "specialist"

    def test_fallback_profile(self):
        fallback = {
            "0x001": {
                "affinities": {"delivery": {"score": 0.7, "confidence": 0.6}},
                "dominant_style": "generalist",
            }
        }
        adapter = AffinityAdapter(fallback_profiles=fallback)

        score = adapter.score_worker("0x001", "delivery")
        assert score.score == 70.0
        assert score.confidence == 0.6

    def test_category_not_in_profile(self):
        adapter = AffinityAdapter()
        adapter.cache.put(
            "0x001",
            {
                "affinities": {"photo": {"score": 0.9}},
                "dominant_style": "specialist",
            },
        )

        score = adapter.score_worker("0x001", "delivery")
        assert score.score == 50.0
        assert score.confidence == 0.0

    def test_sweet_spot_bonus(self):
        adapter = AffinityAdapter()
        adapter.cache.put(
            "0x001",
            {
                "affinities": {"photo": {"score": 0.8, "confidence": 0.8}},
                "sweet_spot": "photo",
                "dominant_style": "specialist",
            },
        )

        score = adapter.score_worker("0x001", "photo")
        # 0.8 * 100 * 1.1 = 88.0 (with sweet spot)
        assert score.score > 80

    def test_no_sweet_spot_bonus_low_confidence(self):
        adapter = AffinityAdapter()
        adapter.cache.put(
            "0x001",
            {
                "affinities": {"photo": {"score": 0.8, "confidence": 0.3}},
                "sweet_spot": "photo",
                "dominant_style": "specialist",
            },
        )

        score = adapter.score_worker("0x001", "photo")
        # Confidence 0.3 < 0.5 → no sweet spot bonus
        assert score.score == 80.0

    def test_score_clamped_at_100(self):
        adapter = AffinityAdapter()
        adapter.cache.put(
            "0x001",
            {
                "affinities": {"photo": {"score": 0.99, "confidence": 0.9}},
                "sweet_spot": "photo",
            },
        )

        score = adapter.score_worker("0x001", "photo")
        assert score.score <= 100.0


class TestAffinityAdapterBatch:
    def test_batch_scoring(self):
        adapter = AffinityAdapter()
        for i in range(3):
            adapter.cache.put(
                f"0x{i:03x}",
                {
                    "affinities": {"photo": {"score": 0.5 + i * 0.1}},
                    "dominant_style": "generalist",
                },
            )

        result = adapter.score_batch(["0x000", "0x001", "0x002"], "photo")
        assert len(result.scores) == 3
        assert result.category == "photo"
        assert result.latency_ms >= 0

    def test_batch_with_errors(self):
        adapter = AffinityAdapter()
        result = adapter.score_batch(["0x001", "0x002"], "photo")
        # All should get neutral scores (no data)
        for score in result.scores.values():
            assert score.score == 50.0


class TestAffinityAdapterMisc:
    def test_invalidate_worker(self):
        adapter = AffinityAdapter()
        adapter.cache.put("0x001", {"data": True})
        adapter.invalidate_worker("0x001")
        assert adapter.cache.get("0x001") is None

    def test_stats(self):
        adapter = AffinityAdapter()
        stats = adapter.stats
        assert "api_available" in stats
        assert "cache" in stats
        assert "fallback_profiles" in stats

    def test_url_cleanup(self):
        adapter = AffinityAdapter(autojob_url="http://test.com/")
        assert adapter.autojob_url == "http://test.com"

    def test_api_check_interval(self):
        adapter = AffinityAdapter()
        adapter._api_available = False
        adapter._last_api_check = time.time()
        assert adapter._should_try_api() is False

        adapter._last_api_check = time.time() - 600  # 10 min ago
        assert adapter._should_try_api() is True


# ══════════════════════════════════════════════════════════════
# Scorer Factory Tests
# ══════════════════════════════════════════════════════════════


class TestMakeAffinityScorer:
    def test_basic_scoring(self):
        adapter = AffinityAdapter()
        scorer = make_affinity_scorer(adapter)

        score = scorer(
            {"category": "photo"},
            {"wallet": "0x001"},
        )
        assert 0 <= score <= 100

    def test_with_cached_data(self):
        adapter = AffinityAdapter()
        adapter.cache.put(
            "0x001",
            {
                "affinities": {"photo": {"score": 0.9, "confidence": 0.8}},
                "dominant_style": "specialist",
            },
        )
        scorer = make_affinity_scorer(adapter)

        score = scorer(
            {"category": "photo"},
            {"wallet": "0x001"},
        )
        assert score == 90.0

    def test_uses_agent_id_fallback(self):
        adapter = AffinityAdapter()
        scorer = make_affinity_scorer(adapter)

        score = scorer(
            {"category": "photo"},
            {"agent_id": "42"},
        )
        assert score == 50.0  # Neutral

    def test_uses_id_fallback(self):
        adapter = AffinityAdapter()
        scorer = make_affinity_scorer(adapter)

        score = scorer(
            {"category": "photo"},
            {"id": "42"},
        )
        assert score == 50.0  # Neutral
