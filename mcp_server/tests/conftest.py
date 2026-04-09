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

import pytest
import sys
from pathlib import Path
from datetime import datetime, UTC

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Arbiter test isolation (Phase 1-5 of commerce scheme + arbiter integration)
# ---------------------------------------------------------------------------
#
# The arbiter test files install sys.modules stubs at module-load time to
# mock api.routers._helpers, events.bus, integrations.x402.payment_dispatcher,
# and supabase_client. This is necessary because the real modules either
# have unrelated import issues (web3 version) or would hit the real DB / API.
#
# Problem: module-level sys.modules manipulation leaks to OTHER test files
# that run AFTER the arbiter tests (e.g., test_event_bus.py gets a fake
# events.bus module and crashes).
#
# Fix: reorder test collection so arbiter tests run LAST, after all other
# tests have had a chance to import the real modules into sys.modules.
# This way the arbiter stubs (which use setdefault in most cases) don't
# pollute the import cache of subsequent tests -- because there are no
# subsequent tests.


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
