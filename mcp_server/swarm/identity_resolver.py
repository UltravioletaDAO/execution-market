"""
IdentityResolver — Swarm-Level Multi-Chain Identity Resolution (Module #55)
============================================================================

Provides a clean, cached, fault-tolerant interface for resolving wallet
addresses to ERC-8004 agent identities across multiple chains.

Motivation (March 29, 2026):
    Yesterday's SKALE integration exposed critical identity bugs:
    1. Wrong chain's agent_id returned (DB fallback returned Base ID for SKALE)
    2. 504 timeouts on identity resolution blocking task creation
    3. Cache staleness returning stale data after re-registration
    4. agent_id vs erc8004_agent_id confusion (wallet address vs numeric ID)

    This module provides a unified resolution layer that handles all of these
    concerns at the swarm level, so individual components don't need to worry
    about identity plumbing.

Architecture:
    ┌──────────────────────────────────────────────┐
    │              IdentityResolver                 │
    │                                               │
    │  ┌─────────────┐    ┌───────────────────┐    │
    │  │  TTL Cache   │    │  Resolution Log   │    │
    │  │ (per-chain)  │    │  (audit trail)    │    │
    │  └──────┬──────┘    └───────┬───────────┘    │
    │         │                    │                 │
    │  ┌──────▼──────────────────▼───────────────┐ │
    │  │        Resolution Pipeline               │ │
    │  │  1. Cache check (chain-specific)         │ │
    │  │  2. Facilitator lookup (with timeout)    │ │
    │  │  3. Fallback (wallet-as-identity)        │ │
    │  └──────────────────────────────────────────┘ │
    └──────────────────────────────────────────────┘

Key Design Decisions:
    - Cache is per (wallet, chain) pair — NEVER share identity across chains
    - Timeouts are configurable and short (5s default) — never block routing
    - Resolution always succeeds: fallback to wallet address as identity
    - All resolutions are logged for audit and debugging
    - Cache invalidation is explicit, not time-based-only (supports manual flush)
    - Thread-safe: all mutable state protected

Usage:
    resolver = IdentityResolver(default_timeout_seconds=5.0)
    
    # Resolve wallet to identity
    identity = resolver.resolve("0xABC...", chain="base")
    # → ResolvedIdentity(wallet="0xABC...", agent_id=2106, chain="base", ...)
    
    # Bulk resolve for routing
    identities = resolver.resolve_batch(["0xA...", "0xB..."], chain="skale")
    
    # Cache management
    resolver.invalidate("0xABC...", chain="base")
    resolver.invalidate_chain("skale")  # Flush all SKALE cache
    resolver.clear_cache()
    
    # Diagnostics
    stats = resolver.cache_stats()
    log = resolver.resolution_log(limit=20)
"""

import logging
import time
import threading
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Dict, List

logger = logging.getLogger("em.swarm.identity_resolver")


# ─── Constants ────────────────────────────────────────────────

# Supported networks (matches EM_ENABLED_NETWORKS)
SUPPORTED_NETWORKS = frozenset({
    "base", "ethereum", "polygon", "arbitrum",
    "celo", "monad", "avalanche", "optimism", "skale",
})

DEFAULT_TTL_SECONDS = 300  # 5 minutes
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_CACHE_SIZE = 10_000
MAX_LOG_SIZE = 500


# ─── Types ────────────────────────────────────────────────────


class ResolutionMethod(str, Enum):
    """How the identity was resolved."""
    CACHE = "cache"
    FACILITATOR = "facilitator"
    FALLBACK = "fallback"  # Wallet address used as identity
    ERROR = "error"  # Resolution failed, fallback used


class ResolutionOutcome(str, Enum):
    """Outcome of a resolution attempt."""
    HIT = "hit"  # Found registered identity
    MISS = "miss"  # Not registered, using fallback
    TIMEOUT = "timeout"  # Lookup timed out
    ERROR = "error"  # Lookup errored


@dataclass(frozen=True)
class ResolvedIdentity:
    """Result of identity resolution."""
    wallet: str
    chain: str
    agent_id: Optional[int]  # Numeric ERC-8004 token ID (None if unregistered)
    display_id: str  # What to use as identifier (agent_id or wallet)
    registered: bool
    method: ResolutionMethod
    resolved_at: float
    ttl_seconds: float = DEFAULT_TTL_SECONDS
    metadata_uri: Optional[str] = None
    owner: Optional[str] = None
    name: Optional[str] = None

    @property
    def expired(self) -> bool:
        """Check if this cached identity has expired."""
        return (time.time() - self.resolved_at) > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        return time.time() - self.resolved_at

    def to_dict(self) -> dict:
        return {
            "wallet": self.wallet,
            "chain": self.chain,
            "agent_id": self.agent_id,
            "display_id": self.display_id,
            "registered": self.registered,
            "method": self.method.value,
            "age_seconds": round(self.age_seconds, 1),
            "expired": self.expired,
            "metadata_uri": self.metadata_uri,
            "name": self.name,
        }


@dataclass
class ResolutionLogEntry:
    """Audit trail entry for a resolution attempt."""
    wallet: str
    chain: str
    method: ResolutionMethod
    outcome: ResolutionOutcome
    agent_id: Optional[int]
    duration_ms: float
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "wallet": self.wallet[:10] + "...",  # Truncate for safety
            "chain": self.chain,
            "method": self.method.value,
            "outcome": self.outcome.value,
            "agent_id": self.agent_id,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
        }


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_entries: int
    entries_by_chain: Dict[str, int]
    hits: int
    misses: int
    evictions: int
    hit_rate: float  # 0-1
    avg_age_seconds: float
    expired_count: int

    def to_dict(self) -> dict:
        return {
            "total_entries": self.total_entries,
            "entries_by_chain": self.entries_by_chain,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": round(self.hit_rate, 3),
            "avg_age_seconds": round(self.avg_age_seconds, 1),
            "expired_count": self.expired_count,
        }


# ─── IdentityResolver ────────────────────────────────────────


class IdentityResolver:
    """
    Multi-chain identity resolution with caching and audit trail.
    
    Resolves wallet addresses to ERC-8004 agent identities, handling:
    - Per-chain cache isolation (Base identity ≠ SKALE identity)
    - Configurable timeouts (never blocks routing)
    - Graceful fallback (wallet address as identity)
    - Resolution audit trail
    - Thread-safe operations
    """

    def __init__(
        self,
        default_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        default_ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_cache_size: int = MAX_CACHE_SIZE,
        max_log_size: int = MAX_LOG_SIZE,
        lookup_fn: Optional[Callable] = None,
    ):
        """
        Initialize the IdentityResolver.

        Parameters
        ----------
        default_timeout_seconds:
            Max time to wait for a facilitator lookup (default 5s).
        default_ttl_seconds:
            Cache entry lifetime (default 300s / 5 minutes).
        max_cache_size:
            Maximum total cache entries across all chains.
        max_log_size:
            Maximum resolution log entries (bounded deque).
        lookup_fn:
            Optional external lookup function for testing.
            Signature: fn(wallet: str, chain: str) -> dict | None
            Returns dict with: registered, agent_id, metadata_uri, owner, name
            Returns None on timeout/error.
        """
        self._timeout = default_timeout_seconds
        self._ttl = default_ttl_seconds
        self._max_cache = max_cache_size
        self._lookup_fn = lookup_fn

        # Per-(wallet, chain) cache
        self._cache: Dict[str, ResolvedIdentity] = {}  # key = f"{wallet}:{chain}"
        self._log: deque = deque(maxlen=max_log_size)

        # Stats
        self._hits = 0
        self._misses = 0
        self._evictions = 0

        # Thread safety
        self._lock = threading.Lock()

    # ─── Core Resolution ──────────────────────────────────────

    def resolve(
        self,
        wallet: str,
        chain: str = "base",
        timeout_seconds: Optional[float] = None,
        skip_cache: bool = False,
    ) -> ResolvedIdentity:
        """
        Resolve a wallet address to an ERC-8004 identity on a specific chain.

        Always returns a ResolvedIdentity — never raises exceptions.
        If the lookup fails or times out, returns a fallback identity
        using the wallet address as the display_id.

        Parameters
        ----------
        wallet:
            Ethereum wallet address (0x-prefixed).
        chain:
            Network to resolve on (default "base").
        timeout_seconds:
            Override default timeout for this resolution.
        skip_cache:
            Force a fresh lookup (ignore cache).
        """
        wallet = wallet.lower().strip()
        chain = chain.lower().strip()
        timeout = timeout_seconds or self._timeout
        cache_key = f"{wallet}:{chain}"

        # 1. Cache check
        if not skip_cache:
            cached = None
            with self._lock:
                entry = self._cache.get(cache_key)
                if entry and not entry.expired:
                    self._hits += 1
                    cached = entry
            # Log OUTSIDE the lock to avoid deadlock
            if cached is not None:
                self._log_resolution(
                    wallet, chain, ResolutionMethod.CACHE,
                    ResolutionOutcome.HIT, cached.agent_id, 0.0,
                )
                return cached

        # 2. Fresh lookup
        start = time.time()
        try:
            result = self._do_lookup(wallet, chain, timeout)
            duration_ms = (time.time() - start) * 1000

            if result is None:
                # Timeout or error — use fallback with ERROR method
                identity = self._make_fallback(wallet, chain, method=ResolutionMethod.ERROR)
                self._log_resolution(
                    wallet, chain, ResolutionMethod.ERROR,
                    ResolutionOutcome.TIMEOUT, None, duration_ms,
                    error="lookup returned None",
                )
            elif result.get("registered"):
                identity = ResolvedIdentity(
                    wallet=wallet,
                    chain=chain,
                    agent_id=result.get("agent_id"),
                    display_id=str(result["agent_id"]) if result.get("agent_id") else wallet,
                    registered=True,
                    method=ResolutionMethod.FACILITATOR,
                    resolved_at=time.time(),
                    ttl_seconds=self._ttl,
                    metadata_uri=result.get("metadata_uri"),
                    owner=result.get("owner"),
                    name=result.get("name"),
                )
                self._log_resolution(
                    wallet, chain, ResolutionMethod.FACILITATOR,
                    ResolutionOutcome.HIT, result.get("agent_id"), duration_ms,
                )
            else:
                # Not registered on this chain
                identity = self._make_fallback(wallet, chain)
                self._log_resolution(
                    wallet, chain, ResolutionMethod.FALLBACK,
                    ResolutionOutcome.MISS, None, duration_ms,
                )

        except Exception as exc:
            duration_ms = (time.time() - start) * 1000
            identity = self._make_fallback(wallet, chain, method=ResolutionMethod.ERROR)
            self._log_resolution(
                wallet, chain, ResolutionMethod.ERROR,
                ResolutionOutcome.ERROR, None, duration_ms,
                error=str(exc)[:200],
            )
            logger.warning(
                "Identity resolution error: wallet=%s chain=%s: %s",
                wallet[:10], chain, exc,
            )

        # 3. Cache the result
        with self._lock:
            self._misses += 1
            self._cache_put(cache_key, identity)

        return identity

    def resolve_batch(
        self,
        wallets: List[str],
        chain: str = "base",
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, ResolvedIdentity]:
        """
        Resolve multiple wallets on the same chain.

        Returns a dict mapping wallet → ResolvedIdentity.
        """
        results = {}
        for wallet in wallets:
            results[wallet.lower().strip()] = self.resolve(
                wallet, chain, timeout_seconds,
            )
        return results

    # ─── Cache Management ─────────────────────────────────────

    def invalidate(self, wallet: str, chain: str) -> bool:
        """Invalidate a specific (wallet, chain) cache entry."""
        key = f"{wallet.lower().strip()}:{chain.lower().strip()}"
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._evictions += 1
                return True
            return False

    def invalidate_chain(self, chain: str) -> int:
        """Invalidate ALL cache entries for a specific chain."""
        chain = chain.lower().strip()
        count = 0
        with self._lock:
            keys_to_remove = [
                k for k in self._cache if k.endswith(f":{chain}")
            ]
            for k in keys_to_remove:
                del self._cache[k]
                count += 1
            self._evictions += count
        return count

    def invalidate_wallet(self, wallet: str) -> int:
        """Invalidate ALL cache entries for a wallet across ALL chains."""
        wallet = wallet.lower().strip()
        count = 0
        with self._lock:
            keys_to_remove = [
                k for k in self._cache if k.startswith(f"{wallet}:")
            ]
            for k in keys_to_remove:
                del self._cache[k]
                count += 1
            self._evictions += count
        return count

    def clear_cache(self) -> int:
        """Clear the entire cache. Returns number of entries removed."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._evictions += count
            return count

    def cache_stats(self) -> CacheStats:
        """Get cache performance statistics."""
        with self._lock:
            entries = list(self._cache.values())

        now = time.time()
        by_chain: Dict[str, int] = {}
        total_age = 0.0
        expired_count = 0

        for entry in entries:
            by_chain[entry.chain] = by_chain.get(entry.chain, 0) + 1
            total_age += now - entry.resolved_at
            if entry.expired:
                expired_count += 1

        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        avg_age = total_age / len(entries) if entries else 0.0

        return CacheStats(
            total_entries=len(entries),
            entries_by_chain=by_chain,
            hits=self._hits,
            misses=self._misses,
            evictions=self._evictions,
            hit_rate=hit_rate,
            avg_age_seconds=avg_age,
            expired_count=expired_count,
        )

    # ─── Multi-Chain Utilities ────────────────────────────────

    def get_all_identities(self, wallet: str) -> Dict[str, ResolvedIdentity]:
        """
        Get all cached identities for a wallet across all chains.
        Does NOT trigger fresh lookups — only returns cached data.
        """
        wallet = wallet.lower().strip()
        results = {}
        with self._lock:
            for key, identity in self._cache.items():
                if key.startswith(f"{wallet}:"):
                    if not identity.expired:
                        results[identity.chain] = identity
        return results

    def is_registered(self, wallet: str, chain: str) -> Optional[bool]:
        """
        Quick check if a wallet is registered on a chain.
        Returns None if not in cache (does not trigger lookup).
        """
        key = f"{wallet.lower().strip()}:{chain.lower().strip()}"
        with self._lock:
            cached = self._cache.get(key)
            if cached and not cached.expired:
                return cached.registered
            return None

    def get_agent_id(self, wallet: str, chain: str) -> Optional[int]:
        """
        Get the numeric agent ID for a wallet on a chain.
        Returns None if not in cache or not registered.
        """
        key = f"{wallet.lower().strip()}:{chain.lower().strip()}"
        with self._lock:
            cached = self._cache.get(key)
            if cached and not cached.expired and cached.registered:
                return cached.agent_id
            return None

    # ─── Diagnostics ──────────────────────────────────────────

    def resolution_log(self, limit: int = 20) -> List[dict]:
        """Get recent resolution log entries."""
        with self._lock:
            entries = list(self._log)
        return [e.to_dict() for e in entries[-limit:]]

    def diagnose(self) -> dict:
        """Full diagnostic snapshot."""
        stats = self.cache_stats()
        log_entries = self.resolution_log(limit=10)

        # Error rate from log
        with self._lock:
            all_entries = list(self._log)

        total_resolutions = len(all_entries)
        error_count = sum(
            1 for e in all_entries
            if e.outcome in (ResolutionOutcome.ERROR, ResolutionOutcome.TIMEOUT)
        )
        error_rate = error_count / total_resolutions if total_resolutions > 0 else 0.0

        # Average resolution time (non-cache)
        non_cache = [
            e.duration_ms for e in all_entries
            if e.method != ResolutionMethod.CACHE
        ]
        avg_duration = sum(non_cache) / len(non_cache) if non_cache else 0.0

        return {
            "cache": stats.to_dict(),
            "resolution_log": log_entries,
            "error_rate": round(error_rate, 3),
            "avg_resolution_ms": round(avg_duration, 1),
            "total_resolutions": total_resolutions,
            "supported_networks": sorted(SUPPORTED_NETWORKS),
        }

    def health(self) -> dict:
        """Quick health check."""
        stats = self.cache_stats()
        with self._lock:
            recent = list(self._log)[-10:] if self._log else []

        recent_errors = sum(
            1 for e in recent
            if e.outcome in (ResolutionOutcome.ERROR, ResolutionOutcome.TIMEOUT)
        )

        healthy = recent_errors < 5  # <50% error rate in last 10
        return {
            "healthy": healthy,
            "cache_entries": stats.total_entries,
            "cache_hit_rate": stats.hit_rate,
            "recent_error_rate": recent_errors / len(recent) if recent else 0.0,
        }

    # ─── Persistence ──────────────────────────────────────────

    def save(self) -> dict:
        """Serialize resolver state for persistence."""
        with self._lock:
            entries = {}
            for key, identity in self._cache.items():
                if not identity.expired:
                    entries[key] = identity.to_dict()

            return {
                "version": 1,
                "entries": entries,
                "stats": {
                    "hits": self._hits,
                    "misses": self._misses,
                    "evictions": self._evictions,
                },
            }

    def load(self, data: dict) -> int:
        """Load resolver state from persistence. Returns entries loaded."""
        if not isinstance(data, dict) or data.get("version") != 1:
            return 0

        entries = data.get("entries", {})
        stats = data.get("stats", {})
        loaded = 0

        with self._lock:
            self._hits = stats.get("hits", 0)
            self._misses = stats.get("misses", 0)
            self._evictions = stats.get("evictions", 0)

            for key, entry_dict in entries.items():
                try:
                    identity = ResolvedIdentity(
                        wallet=entry_dict["wallet"],
                        chain=entry_dict["chain"],
                        agent_id=entry_dict.get("agent_id"),
                        display_id=entry_dict.get("display_id", entry_dict["wallet"]),
                        registered=entry_dict.get("registered", False),
                        method=ResolutionMethod(entry_dict.get("method", "cache")),
                        resolved_at=time.time(),  # Reset TTL on load
                        ttl_seconds=self._ttl,
                        metadata_uri=entry_dict.get("metadata_uri"),
                        name=entry_dict.get("name"),
                    )
                    self._cache[key] = identity
                    loaded += 1
                except (KeyError, ValueError, TypeError):
                    continue

        return loaded

    # ─── Internal Helpers ─────────────────────────────────────

    def _do_lookup(self, wallet: str, chain: str, timeout: float) -> Optional[dict]:
        """
        Perform the actual identity lookup.

        Uses the injected lookup_fn if available (for testing),
        otherwise returns None (subclasses or production code should
        override with actual facilitator/SDK calls).
        """
        if self._lookup_fn:
            return self._lookup_fn(wallet, chain)
        # Default: no lookup configured
        return None

    def _make_fallback(
        self,
        wallet: str,
        chain: str,
        method: ResolutionMethod = ResolutionMethod.FALLBACK,
    ) -> ResolvedIdentity:
        """Create a fallback identity using the wallet address."""
        return ResolvedIdentity(
            wallet=wallet,
            chain=chain,
            agent_id=None,
            display_id=wallet,
            registered=False,
            method=method,
            resolved_at=time.time(),
            ttl_seconds=self._ttl,
        )

    def _cache_put(self, key: str, identity: ResolvedIdentity):
        """Put an entry in cache, evicting if at capacity."""
        # LRU eviction: remove oldest entry if at capacity
        if len(self._cache) >= self._max_cache and key not in self._cache:
            oldest_key = min(
                self._cache, key=lambda k: self._cache[k].resolved_at,
            )
            del self._cache[oldest_key]
            self._evictions += 1

        self._cache[key] = identity

    def _log_resolution(
        self,
        wallet: str,
        chain: str,
        method: ResolutionMethod,
        outcome: ResolutionOutcome,
        agent_id: Optional[int],
        duration_ms: float,
        error: Optional[str] = None,
    ):
        """Add a resolution log entry."""
        entry = ResolutionLogEntry(
            wallet=wallet,
            chain=chain,
            method=method,
            outcome=outcome,
            agent_id=agent_id,
            duration_ms=duration_ms,
            error=error,
        )
        with self._lock:
            self._log.append(entry)
