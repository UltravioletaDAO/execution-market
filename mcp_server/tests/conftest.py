"""
Pytest configuration and fixtures for Execution Market MCP Server tests.

Test Profiles (use -m flag):
    pytest                              # ALL tests (950)
    pytest -m core                      # Core business logic (276)
    pytest -m erc8004                   # ERC-8004 integration (177)
    pytest -m payments                  # Payment flows (251)
    pytest -m security                  # Security & fraud (61)
    pytest -m infrastructure            # Webhooks, WS, A2A (77)

Combine profiles:
    pytest -m "core or erc8004"         # Core + ERC-8004
    pytest -m "core or payments"        # Core + payments
"""

import urllib.error
import urllib.request

import pytest
import sys
from pathlib import Path
from datetime import datetime, UTC

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# sys.modules isolation -- prevent cross-test pollution
# ---------------------------------------------------------------------------
#
# 30+ test files manipulate sys.modules at module level to stub heavy
# dependencies (web3, httpx, supabase, etc.).  These stubs can leak to
# other test files, causing failures in the full suite that don't
# reproduce in isolation.
#
# Defense in depth:
#   1. Function-scoped autouse fixture snapshots/restores sys.modules
#      around every test, catching per-test modifications (e.g. a test
#      that deletes or replaces a module entry).
#   2. Arbiter test reordering pushes the heaviest module-level polluters
#      to the end of the collection order.
#
# Module-level stubs installed at import/collection time are PRESERVED
# within their own file's tests (the snapshot includes them).  They are
# only cleaned up if a DIFFERENT test modifies the same entry.


@pytest.fixture(autouse=True)
def _isolate_sys_modules():
    """Snapshot sys.modules before each test; restore after.

    This prevents per-test sys.modules changes from leaking to subsequent
    tests.  Module-level stubs (installed at import time) are part of the
    snapshot and thus preserved for tests within the same file.
    """
    snapshot = dict(sys.modules)
    snapshot_keys = set(sys.modules.keys())

    yield

    # Remove modules that were added during this test
    added = set(sys.modules.keys()) - snapshot_keys
    for mod_name in added:
        sys.modules.pop(mod_name, None)

    # Restore modules that were replaced or removed during this test
    for mod_name, original_mod in snapshot.items():
        current = sys.modules.get(mod_name)
        if current is not original_mod:
            sys.modules[mod_name] = original_mod


# ---------------------------------------------------------------------------
# Arbiter test isolation (Phase 1-5 of commerce scheme + arbiter integration)
# ---------------------------------------------------------------------------
#
# The arbiter test files install sys.modules stubs at module-load time to
# mock api.routers._helpers, events.bus, integrations.x402.payment_dispatcher,
# and supabase_client.  This is necessary because the real modules either
# have unrelated import issues (web3 version) or would hit the real DB / API.
#
# Even with _isolate_sys_modules above, arbiter tests benefit from running
# last: their module-level stubs are installed at collection time, and if
# they run before other tests, those stubs become part of the "clean"
# snapshot that other tests inherit.


def pytest_collection_modifyitems(config, items):
    """Push arbiter tests to the end of the collection order.

    This avoids sys.modules pollution from arbiter test stubs affecting
    unrelated tests like test_event_bus.py and test_channel_manager.py
    that rely on the real events.bus module.
    """
    arbiter_items = []
    non_arbiter_items = []
    for item in items:
        nodeid = item.nodeid.lower()
        if "test_arbiter" in nodeid:
            arbiter_items.append(item)
        else:
            non_arbiter_items.append(item)
    items[:] = non_arbiter_items + arbiter_items


@pytest.fixture(autouse=True)
def _mock_swarm_network_for_top_level_tests(request, monkeypatch):
    """Prevent real network calls in top-level test_swarm_* test files.

    Only activates when the test module name starts with 'test_swarm_'.
    Patches urlopen in every swarm module to raise URLError immediately so
    AutoJobClient / AffinityAdapter / etc. don't block for 5-8s per call.
    """
    module_name = request.module.__name__.rsplit(".", 1)[-1]
    if not module_name.startswith("test_swarm_"):
        return

    # All swarm modules that do `from urllib.request import urlopen`.
    # Some top-level test files import via `from swarm.*` (bare), others via
    # `from mcp_server.swarm.*`. Both paths end up as separate sys.modules
    # entries, so we must patch both.
    _base_modules = [
        "autojob_client",
        "affinity_adapter",
        "coordinator",
        "outcome_adapter",
        "market_intelligence_adapter",
        "preflight",
        "xmtp_bridge",
        "feedback_pipeline",
        "expiry_analyzer",
        "decomposition_adapter",
        "retention_adapter",
        "performance_adapter",
        "pricing_adapter",
    ]
    swarm_modules_with_urlopen = [f"swarm.{m}" for m in _base_modules] + [
        f"mcp_server.swarm.{m}" for m in _base_modules
    ]

    def _fake_urlopen(*args, **kwargs):
        raise urllib.error.URLError("mocked - no AutoJob/EM server in tests")

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)

    for mod_path in swarm_modules_with_urlopen:
        mod = sys.modules.get(mod_path)
        if mod and hasattr(mod, "urlopen"):
            monkeypatch.setattr(mod, "urlopen", _fake_urlopen)


@pytest.fixture
def sample_task():
    """Sample task for testing."""
    return {
        "id": "task-123",
        "agent_id": "agent-456",
        "title": "Verify store is open",
        "task_type": "store_verification",
        "instructions": "Take a photo of the Walmart entrance showing it's open.",
        "location": {"lat": 25.7617, "lng": -80.1918},
        "bounty_amount_usdc": 5.00,
        "deadline": datetime.now(UTC).isoformat(),
        "evidence_schema": {
            "required": ["photo_geo"],
            "optional": ["text_response"],
        },
    }


@pytest.fixture
def sample_executor():
    """Sample executor for testing."""
    return {
        "id": "exec-789",
        "user_id": "user-101",
        "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        "display_name": "Test Worker",
        "rating": 85,
        "completed_tasks": 50,
        "status": "active",
    }


@pytest.fixture
def sample_evidence():
    """Sample evidence submission for testing."""
    return {
        "gps": {"lat": 25.7617, "lng": -80.1918},
        "timestamp": datetime.now(UTC).isoformat(),
        "notes": "Store is open. Took photo of entrance.",
        "photos": ["https://example.com/photo1.jpg"],
    }


@pytest.fixture
def miami_coordinates():
    """Miami coordinates for GPS testing."""
    return {
        "lat": 25.7617,
        "lng": -80.1918,
    }


@pytest.fixture
def nyc_coordinates():
    """NYC coordinates for GPS testing."""
    return {
        "lat": 40.7128,
        "lng": -74.0060,
    }


@pytest.fixture
def sample_solana_executor():
    """Sample Solana executor for testing (Base58 wallet address)."""
    return {
        "id": "exec-sol-001",
        "user_id": "user-sol-101",
        "wallet_address": "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV",
        "display_name": "Solana Worker",
        "rating": 90,
        "completed_tasks": 10,
        "status": "active",
    }


@pytest.fixture
def sample_solana_task():
    """Sample Solana task for testing."""
    return {
        "id": "task-sol-123",
        "agent_id": "agent-sol-456",
        "title": "Verify store is open (Solana)",
        "task_type": "store_verification",
        "instructions": "Take a photo of the store entrance showing it's open.",
        "location": {"lat": 25.7617, "lng": -80.1918},
        "bounty_amount_usdc": 0.10,
        "deadline": datetime.now(UTC).isoformat(),
        "network": "solana",
        "evidence_schema": {
            "required": ["photo_geo"],
            "optional": ["text_response"],
        },
    }
