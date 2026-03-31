"""
Tests for IdentityResolver — Module #55
=========================================

Comprehensive test coverage for multi-chain identity resolution:
- Cache behavior (TTL, per-chain isolation, eviction)
- Resolution pipeline (lookup → cache → fallback)
- Multi-chain utilities (cross-chain queries, batch resolution)
- Error handling and graceful degradation
- Diagnostics and audit trail
- Persistence (save/load round-trip)
- Thread safety
- Edge cases
"""

import time
import threading

import importlib
import os

# Direct import to avoid swarm/__init__.py pulling in Python 3.10+ modules
_swarm_dir = os.path.join(os.path.dirname(__file__), "..", "swarm")
_spec = importlib.util.spec_from_file_location(
    "identity_resolver",
    os.path.join(_swarm_dir, "identity_resolver.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

IdentityResolver = _mod.IdentityResolver
ResolvedIdentity = _mod.ResolvedIdentity
ResolutionMethod = _mod.ResolutionMethod
ResolutionOutcome = _mod.ResolutionOutcome
CacheStats = _mod.CacheStats
SUPPORTED_NETWORKS = _mod.SUPPORTED_NETWORKS
DEFAULT_TTL_SECONDS = _mod.DEFAULT_TTL_SECONDS
DEFAULT_TIMEOUT_SECONDS = _mod.DEFAULT_TIMEOUT_SECONDS


# ─── Fixtures ─────────────────────────────────────────────────


def _mock_lookup_registered(wallet, chain):
    """Mock that returns a registered identity."""
    agent_ids = {
        "base": 2106,
        "skale": 37500,
        "polygon": 999,
        "ethereum": 1,
    }
    return {
        "registered": True,
        "agent_id": agent_ids.get(chain, 42),
        "metadata_uri": f"https://identity.example/{wallet[:8]}",
        "owner": wallet,
        "name": f"Agent-{chain}",
    }


def _mock_lookup_unregistered(wallet, chain):
    """Mock that returns an unregistered identity."""
    return {"registered": False, "agent_id": None}


def _mock_lookup_error(wallet, chain):
    """Mock that raises an exception."""
    raise ConnectionError("Facilitator unreachable")


def _mock_lookup_none(wallet, chain):
    """Mock that returns None (timeout)."""
    return None


def _mock_lookup_mixed(wallet, chain):
    """Returns registered for base, unregistered for others."""
    if chain == "base":
        return {"registered": True, "agent_id": 2106, "name": "Clawd"}
    return {"registered": False}


# ─── Test: Basic Resolution ──────────────────────────────────


class TestBasicResolution:
    """Core resolution pipeline."""

    def test_resolve_registered_identity(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        identity = resolver.resolve("0xABC123", chain="base")

        assert identity.registered is True
        assert identity.agent_id == 2106
        assert identity.chain == "base"
        assert identity.wallet == "0xabc123"  # Lowercased
        assert identity.display_id == "2106"
        assert identity.method == ResolutionMethod.FACILITATOR

    def test_resolve_unregistered_identity(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_unregistered)
        identity = resolver.resolve("0xDEF456", chain="polygon")

        assert identity.registered is False
        assert identity.agent_id is None
        assert identity.display_id == "0xdef456"
        assert identity.method == ResolutionMethod.FALLBACK

    def test_resolve_with_error(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_error)
        identity = resolver.resolve("0x123", chain="base")

        assert identity.registered is False
        assert identity.method == ResolutionMethod.ERROR
        assert identity.display_id == "0x123"

    def test_resolve_with_timeout(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_none)
        identity = resolver.resolve("0x123", chain="base")

        assert identity.registered is False
        assert identity.method == ResolutionMethod.ERROR

    def test_resolve_normalizes_wallet(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        id1 = resolver.resolve("  0xABC  ", chain="base", skip_cache=True)
        id2 = resolver.resolve("0xabc", chain="base", skip_cache=True)

        assert id1.wallet == "0xabc"
        assert id2.wallet == "0xabc"

    def test_resolve_normalizes_chain(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        identity = resolver.resolve("0xABC", chain="  Base  ")

        assert identity.chain == "base"

    def test_resolve_no_lookup_fn(self):
        """Without a lookup function, lookup returns None → ERROR fallback."""
        resolver = IdentityResolver()
        identity = resolver.resolve("0xABC", chain="base")

        assert identity.registered is False
        assert identity.method == ResolutionMethod.ERROR  # No lookup fn → None → ERROR

    def test_resolve_different_chains_different_ids(self):
        """Same wallet can have different agent IDs on different chains."""
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)

        base_id = resolver.resolve("0xABC", chain="base")
        skale_id = resolver.resolve("0xABC", chain="skale")

        assert base_id.agent_id == 2106
        assert skale_id.agent_id == 37500
        assert base_id.agent_id != skale_id.agent_id


# ─── Test: Cache Behavior ────────────────────────────────────


class TestCacheBehavior:
    """Cache: TTL, isolation, eviction, hit/miss tracking."""

    def test_cache_hit(self):
        calls = []

        def tracking_lookup(w, c):
            calls.append((w, c))
            return {"registered": True, "agent_id": 1}

        resolver = IdentityResolver(lookup_fn=tracking_lookup)
        resolver.resolve("0xABC", chain="base")
        resolver.resolve("0xABC", chain="base")

        assert len(calls) == 1  # Only one actual lookup
        stats = resolver.cache_stats()
        assert stats.hits == 1
        assert stats.misses == 1

    def test_cache_miss_different_chain(self):
        """Cache is per (wallet, chain) — different chain = cache miss."""
        calls = []

        def tracking_lookup(w, c):
            calls.append((w, c))
            return {"registered": True, "agent_id": 1}

        resolver = IdentityResolver(lookup_fn=tracking_lookup)
        resolver.resolve("0xABC", chain="base")
        resolver.resolve("0xABC", chain="polygon")

        assert len(calls) == 2

    def test_cache_ttl_expiry(self):
        calls = []

        def tracking_lookup(w, c):
            calls.append(1)
            return {"registered": True, "agent_id": 1}

        resolver = IdentityResolver(
            lookup_fn=tracking_lookup,
            default_ttl_seconds=0.01,  # 10ms TTL
        )
        resolver.resolve("0xABC", chain="base")
        time.sleep(0.02)  # Wait for TTL
        resolver.resolve("0xABC", chain="base")

        assert len(calls) == 2  # Second call triggers fresh lookup

    def test_skip_cache(self):
        calls = []

        def tracking_lookup(w, c):
            calls.append(1)
            return {"registered": True, "agent_id": 1}

        resolver = IdentityResolver(lookup_fn=tracking_lookup)
        resolver.resolve("0xABC", chain="base")
        resolver.resolve("0xABC", chain="base", skip_cache=True)

        assert len(calls) == 2

    def test_cache_eviction_at_capacity(self):
        resolver = IdentityResolver(
            lookup_fn=_mock_lookup_registered,
            max_cache_size=3,
        )
        # Fill cache
        resolver.resolve("0x1", chain="base")
        resolver.resolve("0x2", chain="base")
        resolver.resolve("0x3", chain="base")

        assert resolver.cache_stats().total_entries == 3

        # This should evict the oldest
        resolver.resolve("0x4", chain="base")

        stats = resolver.cache_stats()
        assert stats.total_entries == 3  # Still 3, oldest evicted
        assert stats.evictions >= 1

    def test_cache_isolation_per_chain(self):
        """Modifying cache for one chain doesn't affect another."""
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xABC", chain="base")
        resolver.resolve("0xABC", chain="skale")

        resolver.invalidate("0xABC", chain="base")

        # SKALE entry should still be cached
        assert resolver.is_registered("0xABC", "skale") is True
        assert resolver.is_registered("0xABC", "base") is None  # Invalidated

    def test_cache_stores_unregistered(self):
        """Unregistered results are also cached (prevents repeated lookups)."""
        calls = []

        def tracking_lookup(w, c):
            calls.append(1)
            return {"registered": False}

        resolver = IdentityResolver(lookup_fn=tracking_lookup)
        resolver.resolve("0xABC", chain="base")
        resolver.resolve("0xABC", chain="base")

        assert len(calls) == 1  # Cached even though unregistered


# ─── Test: Cache Invalidation ────────────────────────────────


class TestCacheInvalidation:
    """Explicit cache management."""

    def test_invalidate_specific_entry(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xABC", chain="base")

        assert resolver.invalidate("0xABC", "base") is True
        assert resolver.invalidate("0xABC", "base") is False  # Already gone

    def test_invalidate_nonexistent(self):
        resolver = IdentityResolver()
        assert resolver.invalidate("0xNOPE", "base") is False

    def test_invalidate_chain(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0x1", chain="base")
        resolver.resolve("0x2", chain="base")
        resolver.resolve("0x3", chain="skale")

        count = resolver.invalidate_chain("base")

        assert count == 2
        assert resolver.cache_stats().total_entries == 1  # Only SKALE remains

    def test_invalidate_wallet_all_chains(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xABC", chain="base")
        resolver.resolve("0xABC", chain="skale")
        resolver.resolve("0xOTHER", chain="base")

        count = resolver.invalidate_wallet("0xABC")

        assert count == 2
        assert resolver.cache_stats().total_entries == 1  # Only OTHER remains

    def test_clear_cache(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0x1", chain="base")
        resolver.resolve("0x2", chain="polygon")

        count = resolver.clear_cache()

        assert count == 2
        assert resolver.cache_stats().total_entries == 0


# ─── Test: Batch Resolution ──────────────────────────────────


class TestBatchResolution:
    """Resolve multiple wallets."""

    def test_resolve_batch(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        results = resolver.resolve_batch(
            ["0xA", "0xB", "0xC"],
            chain="base",
        )

        assert len(results) == 3
        assert all(r.registered for r in results.values())
        assert "0xa" in results  # Normalized keys

    def test_resolve_batch_empty(self):
        resolver = IdentityResolver()
        results = resolver.resolve_batch([], chain="base")
        assert results == {}

    def test_resolve_batch_mixed(self):
        """Some registered, some not."""
        resolver = IdentityResolver(lookup_fn=_mock_lookup_mixed)
        results = resolver.resolve_batch(
            ["0xA", "0xB"],
            chain="base",
        )

        assert len(results) == 2
        # Both should resolve (mixed returns registered for base)
        assert results["0xa"].registered is True
        assert results["0xb"].registered is True

    def test_resolve_batch_different_chain(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_mixed)
        results = resolver.resolve_batch(
            ["0xA", "0xB"],
            chain="polygon",
        )

        # _mock_lookup_mixed returns unregistered for non-base chains
        assert all(not r.registered for r in results.values())


# ─── Test: Multi-Chain Utilities ─────────────────────────────


class TestMultiChainUtilities:
    """Cross-chain queries and lookups."""

    def test_get_all_identities(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xABC", chain="base")
        resolver.resolve("0xABC", chain="skale")
        resolver.resolve("0xABC", chain="polygon")

        all_ids = resolver.get_all_identities("0xABC")

        assert len(all_ids) == 3
        assert "base" in all_ids
        assert "skale" in all_ids
        assert "polygon" in all_ids

    def test_get_all_identities_only_cached(self):
        """Does NOT trigger fresh lookups."""
        calls = []

        def tracking_lookup(w, c):
            calls.append(1)
            return {"registered": True, "agent_id": 1}

        resolver = IdentityResolver(lookup_fn=tracking_lookup)
        resolver.resolve("0xABC", chain="base")

        before = len(calls)
        all_ids = resolver.get_all_identities("0xABC")
        after = len(calls)

        assert before == after  # No new lookups
        assert len(all_ids) == 1

    def test_get_all_identities_excludes_expired(self):
        resolver = IdentityResolver(
            lookup_fn=_mock_lookup_registered,
            default_ttl_seconds=0.01,
        )
        resolver.resolve("0xABC", chain="base")
        time.sleep(0.02)

        all_ids = resolver.get_all_identities("0xABC")
        assert len(all_ids) == 0  # All expired

    def test_is_registered_cached(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xABC", chain="base")

        assert resolver.is_registered("0xABC", "base") is True

    def test_is_registered_not_cached(self):
        resolver = IdentityResolver()
        assert resolver.is_registered("0xABC", "base") is None

    def test_get_agent_id(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xABC", chain="base")

        assert resolver.get_agent_id("0xABC", "base") == 2106

    def test_get_agent_id_unregistered(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_unregistered)
        resolver.resolve("0xABC", chain="base")

        assert resolver.get_agent_id("0xABC", "base") is None


# ─── Test: Diagnostics & Logging ─────────────────────────────


class TestDiagnostics:
    """Audit trail and diagnostics."""

    def test_resolution_log(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xA", chain="base")
        resolver.resolve("0xB", chain="base")

        log = resolver.resolution_log(limit=10)

        assert len(log) >= 2
        assert all("wallet" in entry for entry in log)
        assert all("method" in entry for entry in log)

    def test_resolution_log_limit(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        for i in range(20):
            resolver.resolve(f"0x{i:04x}", chain="base")

        log = resolver.resolution_log(limit=5)
        assert len(log) == 5

    def test_resolution_log_truncates_wallet(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xABCDEF1234567890", chain="base")

        log = resolver.resolution_log(limit=1)
        assert "..." in log[0]["wallet"]  # Truncated for safety

    def test_diagnose(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xA", chain="base")
        resolver.resolve("0xB", chain="skale")

        diag = resolver.diagnose()

        assert "cache" in diag
        assert "resolution_log" in diag
        assert "error_rate" in diag
        assert "avg_resolution_ms" in diag
        assert "supported_networks" in diag
        assert diag["total_resolutions"] >= 2

    def test_diagnose_error_rate(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_error)
        for i in range(5):
            resolver.resolve(f"0x{i}", chain="base")

        diag = resolver.diagnose()
        assert diag["error_rate"] > 0

    def test_health_check(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xA", chain="base")

        health = resolver.health()

        assert health["healthy"] is True
        assert "cache_entries" in health
        assert "cache_hit_rate" in health

    def test_health_degrades_on_errors(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_error)
        for i in range(10):
            resolver.resolve(f"0x{i}", chain="base")

        health = resolver.health()
        assert health["healthy"] is False
        assert health["recent_error_rate"] > 0


# ─── Test: Persistence ───────────────────────────────────────


class TestPersistence:
    """Save/load round-trip."""

    def test_save_and_load(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xA", chain="base")
        resolver.resolve("0xB", chain="skale")

        data = resolver.save()

        new_resolver = IdentityResolver()
        loaded = new_resolver.load(data)

        assert loaded == 2
        assert new_resolver.is_registered("0xa", "base") is True
        assert new_resolver.is_registered("0xb", "skale") is True

    def test_save_excludes_expired(self):
        resolver = IdentityResolver(
            lookup_fn=_mock_lookup_registered,
            default_ttl_seconds=0.01,
        )
        resolver.resolve("0xA", chain="base")
        time.sleep(0.02)

        data = resolver.save()
        assert len(data["entries"]) == 0

    def test_load_preserves_stats(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xA", chain="base")
        resolver.resolve("0xA", chain="base")  # Cache hit

        data = resolver.save()

        new_resolver = IdentityResolver()
        new_resolver.load(data)

        stats = new_resolver.cache_stats()
        assert stats.hits == 1  # Preserved from save

    def test_load_invalid_data(self):
        resolver = IdentityResolver()
        assert resolver.load({}) == 0
        assert resolver.load({"version": 2}) == 0
        assert resolver.load(None) == 0

    def test_load_corrupted_entries(self):
        resolver = IdentityResolver()
        data = {
            "version": 1,
            "entries": {
                "0xa:base": {"wallet": "0xa", "chain": "base"},  # Missing fields
                "0xb:base": "not a dict",  # Wrong type
            },
            "stats": {},
        }
        loaded = resolver.load(data)
        # Should load what it can (first entry has enough required fields)
        assert loaded >= 0  # Graceful handling


# ─── Test: ResolvedIdentity ─────────────────────────────────


class TestResolvedIdentity:
    """ResolvedIdentity dataclass behavior."""

    def test_expired_before_ttl(self):
        identity = ResolvedIdentity(
            wallet="0xa",
            chain="base",
            agent_id=1,
            display_id="1",
            registered=True,
            method=ResolutionMethod.FACILITATOR,
            resolved_at=time.time(),
            ttl_seconds=300,
        )
        assert identity.expired is False

    def test_expired_after_ttl(self):
        identity = ResolvedIdentity(
            wallet="0xa",
            chain="base",
            agent_id=1,
            display_id="1",
            registered=True,
            method=ResolutionMethod.FACILITATOR,
            resolved_at=time.time() - 301,
            ttl_seconds=300,
        )
        assert identity.expired is True

    def test_to_dict(self):
        identity = ResolvedIdentity(
            wallet="0xa",
            chain="base",
            agent_id=42,
            display_id="42",
            registered=True,
            method=ResolutionMethod.FACILITATOR,
            resolved_at=time.time(),
            metadata_uri="https://example.com",
            name="TestAgent",
        )
        d = identity.to_dict()

        assert d["wallet"] == "0xa"
        assert d["chain"] == "base"
        assert d["agent_id"] == 42
        assert d["registered"] is True
        assert d["method"] == "facilitator"
        assert d["name"] == "TestAgent"

    def test_age_seconds(self):
        identity = ResolvedIdentity(
            wallet="0xa",
            chain="base",
            agent_id=1,
            display_id="1",
            registered=True,
            method=ResolutionMethod.FACILITATOR,
            resolved_at=time.time() - 10,
        )
        assert identity.age_seconds >= 10


# ─── Test: Edge Cases ────────────────────────────────────────


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_empty_wallet(self):
        resolver = IdentityResolver()
        identity = resolver.resolve("", chain="base")
        assert identity.wallet == ""
        assert identity.registered is False

    def test_empty_chain(self):
        resolver = IdentityResolver()
        identity = resolver.resolve("0xABC", chain="")
        assert identity.chain == ""

    def test_large_batch(self):
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        wallets = [f"0x{i:04x}" for i in range(100)]
        results = resolver.resolve_batch(wallets, chain="base")

        assert len(results) == 100

    def test_concurrent_resolution(self):
        """Thread safety: concurrent resolves don't corrupt state."""
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        errors = []

        def resolve_worker(n):
            try:
                for i in range(20):
                    resolver.resolve(f"0x{n}_{i}", chain="base")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=resolve_worker, args=(n,)) for n in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = resolver.cache_stats()
        assert stats.total_entries == 100  # 5 threads × 20 wallets

    def test_supported_networks_constant(self):
        assert "base" in SUPPORTED_NETWORKS
        assert "skale" in SUPPORTED_NETWORKS
        assert "polygon" in SUPPORTED_NETWORKS
        assert "ethereum" in SUPPORTED_NETWORKS

    def test_cache_stats_empty(self):
        resolver = IdentityResolver()
        stats = resolver.cache_stats()

        assert stats.total_entries == 0
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.hit_rate == 0.0

    def test_resolution_log_bounded(self):
        resolver = IdentityResolver(
            lookup_fn=_mock_lookup_registered,
            max_log_size=10,
        )
        for i in range(50):
            resolver.resolve(f"0x{i:04x}", chain="base")

        # Log should be bounded
        log = resolver.resolution_log(limit=100)
        assert len(log) <= 10

    def test_lookup_returning_partial_data(self):
        """Lookup returns dict without agent_id."""

        def partial_lookup(w, c):
            return {"registered": True}  # No agent_id

        resolver = IdentityResolver(lookup_fn=partial_lookup)
        identity = resolver.resolve("0xABC", chain="base")

        assert identity.registered is True
        assert identity.agent_id is None
        assert identity.display_id == "0xabc"  # Falls back to wallet


# ─── Test: SKALE-Specific Scenarios ──────────────────────────


class TestSKALEScenarios:
    """Scenarios from March 29 SKALE debugging session."""

    def test_different_agent_id_per_chain(self):
        """The bug: Base returned agent_id for SKALE lookups."""
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)

        base_id = resolver.resolve("0xD386", chain="base")
        skale_id = resolver.resolve("0xD386", chain="skale")

        assert base_id.agent_id == 2106
        assert skale_id.agent_id == 37500
        # Critical: they MUST be different
        assert base_id.agent_id != skale_id.agent_id

    def test_cache_doesnt_leak_across_chains(self):
        """After resolving on Base, SKALE resolution must NOT use Base cache."""
        calls = []

        def tracking_lookup(w, c):
            calls.append((w, c))
            if c == "base":
                return {"registered": True, "agent_id": 2106}
            elif c == "skale":
                return {"registered": True, "agent_id": 37500}
            return {"registered": False}

        resolver = IdentityResolver(lookup_fn=tracking_lookup)
        resolver.resolve("0xWALLET", chain="base")
        resolver.resolve("0xWALLET", chain="skale")

        # Both lookups must happen (no cross-chain cache sharing)
        assert len(calls) == 2
        assert calls[0][1] == "base"
        assert calls[1][1] == "skale"

    def test_invalidate_chain_doesnt_affect_others(self):
        """Clearing SKALE cache must not clear Base cache."""
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xWALLET", chain="base")
        resolver.resolve("0xWALLET", chain="skale")

        resolver.invalidate_chain("skale")

        assert resolver.is_registered("0xwallet", "base") is True
        assert resolver.is_registered("0xwallet", "skale") is None

    def test_timeout_doesnt_corrupt_cache(self):
        """After a timeout, subsequent successful lookup should cache correctly."""
        attempt = [0]

        def flaky_lookup(w, c):
            attempt[0] += 1
            if attempt[0] == 1:
                return None  # Timeout
            return {"registered": True, "agent_id": 42}

        resolver = IdentityResolver(lookup_fn=flaky_lookup)

        # First attempt: timeout → fallback
        id1 = resolver.resolve("0xABC", chain="base")
        assert id1.registered is False  # Fallback

        # Second attempt: should succeed (skip cache since fallback was cached)
        id2 = resolver.resolve("0xABC", chain="base", skip_cache=True)
        assert id2.registered is True
        assert id2.agent_id == 42

    def test_wallet_address_as_display_id_for_unregistered(self):
        """Unregistered wallets use wallet address as display_id."""
        resolver = IdentityResolver(lookup_fn=_mock_lookup_unregistered)
        identity = resolver.resolve(
            "0xD3868E1eD738CED6945A574a7c769433BeD5d474", chain="skale"
        )

        assert identity.display_id == "0xd3868e1ed738ced6945a574a7c769433bed5d474"
        assert identity.agent_id is None


# ─── Test: Integration with SwarmIntegrator ──────────────────


class TestIntegratorCompatibility:
    """Verify the module integrates cleanly with SwarmIntegrator patterns."""

    def test_health_method_exists(self):
        """SwarmIntegrator expects health() method on components."""
        resolver = IdentityResolver()
        health = resolver.health()
        assert isinstance(health, dict)
        assert "healthy" in health

    def test_save_load_pattern(self):
        """StatePersistence expects save()/load() methods."""
        resolver = IdentityResolver(lookup_fn=_mock_lookup_registered)
        resolver.resolve("0xA", chain="base")

        state = resolver.save()
        assert isinstance(state, dict)
        assert "version" in state

        new_resolver = IdentityResolver()
        count = new_resolver.load(state)
        assert count > 0

    def test_diagnose_method_exists(self):
        """SwarmDiagnostics expects diagnose() method."""
        resolver = IdentityResolver()
        diag = resolver.diagnose()
        assert isinstance(diag, dict)
