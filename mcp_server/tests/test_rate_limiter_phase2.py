"""
Tests for Phase 2 AI-009 — In-memory rate-limit bucket cap.

Validates that the rate limiter in arbiter_public.py caps the in-memory
dict size to prevent unbounded memory growth in long-running processes.

Marker: arbiter
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.arbiter

# Add mcp_server/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Stub out transitive dependencies that are not needed for rate-limiter tests.
# api.routers.arbiter_public -> api.__init__ -> api.reputation ->
# integrations.erc8004.feedback_store (and others)
_stubs = {
    "integrations.erc8004": ModuleType("integrations.erc8004"),
    "integrations.erc8004.identity": ModuleType("integrations.erc8004.identity"),
    "integrations.erc8004.facilitator_client": ModuleType(
        "integrations.erc8004.facilitator_client"
    ),
    "integrations.erc8004.feedback_store": ModuleType(
        "integrations.erc8004.feedback_store"
    ),
    "integrations.arbiter": ModuleType("integrations.arbiter"),
    "integrations.arbiter.config": ModuleType("integrations.arbiter.config"),
    "integrations.arbiter.service": ModuleType("integrations.arbiter.service"),
    "integrations.arbiter.types": ModuleType("integrations.arbiter.types"),
}

# Set minimal attributes the downstream code expects
_stubs["integrations.erc8004.identity"].check_worker_identity = None
_stubs["integrations.erc8004.facilitator_client"].get_facilitator_client = None
_stubs[
    "integrations.erc8004.feedback_store"
].FEEDBACK_PUBLIC_URL = "https://example.com"

# arbiter stubs
import enum as _enum


class _FakeDecision(_enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"


_stubs["integrations.arbiter.types"].ArbiterDecision = _FakeDecision
_stubs["integrations.arbiter.config"].is_arbiter_enabled = None
_stubs["integrations.arbiter.service"].ArbiterService = None

for _name, _mod in _stubs.items():
    if _name not in sys.modules:
        sys.modules[_name] = _mod


class TestAI009RateLimiterCap:
    """AI-009: In-memory rate-limit bucket dict must not grow unbounded."""

    def _import_rate_limiter(self):
        """Import rate-limiter internals from arbiter_public."""
        from api.routers.arbiter_public import (
            MAX_RATE_LIMIT_BUCKETS,
            RATE_LIMIT_MAX_PER_MINUTE,
            _check_rate_limit,
            _evict_rate_limit_buckets,
            _rate_limit_buckets,
        )

        return (
            _rate_limit_buckets,
            _check_rate_limit,
            _evict_rate_limit_buckets,
            MAX_RATE_LIMIT_BUCKETS,
            RATE_LIMIT_MAX_PER_MINUTE,
        )

    def test_max_buckets_constant_exists(self):
        """MAX_RATE_LIMIT_BUCKETS should be defined and > 0."""
        (
            _,
            _,
            _,
            MAX_RATE_LIMIT_BUCKETS,
            _,
        ) = self._import_rate_limiter()
        assert MAX_RATE_LIMIT_BUCKETS > 0
        assert MAX_RATE_LIMIT_BUCKETS == 10_000

    def test_eviction_does_nothing_under_capacity(self):
        """No eviction occurs when buckets are under the cap."""
        (
            _rate_limit_buckets,
            _,
            _evict_rate_limit_buckets,
            _,
            _,
        ) = self._import_rate_limiter()
        _rate_limit_buckets.clear()

        # Add a few buckets
        for i in range(10):
            _rate_limit_buckets[f"caller-{i}"] = [time.time()]

        _evict_rate_limit_buckets()
        assert len(_rate_limit_buckets) == 10

        _rate_limit_buckets.clear()

    def test_eviction_triggers_over_capacity(self):
        """When buckets exceed MAX, oldest half is evicted."""
        (
            _rate_limit_buckets,
            _,
            _evict_rate_limit_buckets,
            MAX_RATE_LIMIT_BUCKETS,
            _,
        ) = self._import_rate_limiter()
        _rate_limit_buckets.clear()

        import api.routers.arbiter_public as module

        base_time = time.time() - 1000
        for i in range(150):
            _rate_limit_buckets[f"caller-{i:05d}"] = [base_time + i]

        assert len(_rate_limit_buckets) == 150

        # Patch to a small cap for testing
        original_max = module.MAX_RATE_LIMIT_BUCKETS
        module.MAX_RATE_LIMIT_BUCKETS = 100
        try:
            module._evict_rate_limit_buckets()
            # Should have evicted oldest 50 (half of 100)
            assert len(_rate_limit_buckets) <= 100
            # The remaining entries should be the NEWEST ones
            remaining_keys = list(_rate_limit_buckets.keys())
            for key in remaining_keys:
                idx = int(key.split("-")[1])
                # Oldest 50 should be gone (indices 0-49)
                assert idx >= 50, f"Old bucket {key} should have been evicted"
        finally:
            module.MAX_RATE_LIMIT_BUCKETS = original_max
            _rate_limit_buckets.clear()

    def test_check_rate_limit_calls_eviction(self):
        """_check_rate_limit calls _evict_rate_limit_buckets on each call."""
        (
            _rate_limit_buckets,
            _check_rate_limit,
            _,
            _,
            _,
        ) = self._import_rate_limiter()
        _rate_limit_buckets.clear()

        with patch(
            "api.routers.arbiter_public._evict_rate_limit_buckets"
        ) as mock_evict:
            _check_rate_limit("test-caller")
            mock_evict.assert_called_once()

        _rate_limit_buckets.clear()

    def test_rate_limit_still_enforced(self):
        """Rate limiting (100 req/min) still works after AI-009 changes."""
        from fastapi import HTTPException

        (
            _rate_limit_buckets,
            _check_rate_limit,
            _,
            _,
            RATE_LIMIT_MAX_PER_MINUTE,
        ) = self._import_rate_limiter()
        _rate_limit_buckets.clear()

        caller = "test-rate-limit-caller"
        # Fill up to the limit
        for _ in range(RATE_LIMIT_MAX_PER_MINUTE):
            _check_rate_limit(caller)

        # Next call should raise 429
        with pytest.raises(HTTPException) as exc_info:
            _check_rate_limit(caller)
        assert exc_info.value.status_code == 429

        _rate_limit_buckets.clear()

    def test_eviction_preserves_empty_buckets_by_age(self):
        """Empty buckets (timestamp=0) are evicted first as oldest."""
        (
            _rate_limit_buckets,
            _,
            _,
            _,
            _,
        ) = self._import_rate_limiter()
        _rate_limit_buckets.clear()

        import api.routers.arbiter_public as module

        original_max = module.MAX_RATE_LIMIT_BUCKETS
        module.MAX_RATE_LIMIT_BUCKETS = 10
        try:
            # Add 5 empty buckets and 10 non-empty ones
            for i in range(5):
                _rate_limit_buckets[f"empty-{i}"] = []
            for i in range(10):
                _rate_limit_buckets[f"active-{i}"] = [time.time()]

            assert len(_rate_limit_buckets) == 15

            module._evict_rate_limit_buckets()

            # Empty buckets should have been evicted first (sort key=0)
            for i in range(5):
                assert f"empty-{i}" not in _rate_limit_buckets
        finally:
            module.MAX_RATE_LIMIT_BUCKETS = original_max
            _rate_limit_buckets.clear()
