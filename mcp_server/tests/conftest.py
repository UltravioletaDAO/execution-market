"""
Pytest configuration and fixtures for Execution Market MCP Server tests.

Test Profiles (use -m flag):
    pytest                              # ALL tests (909)
    pytest -m "not dormant"             # Active tests only (~815) - DEFAULT for CI
    pytest -m "not dormant and not redundant"  # Lean suite (~720)
    pytest -m core                      # Core business logic (~200)
    pytest -m erc8004                   # ERC-8004 integration (~120)
    pytest -m payments                  # Payment flows (~130)
    pytest -m security                  # Security & fraud (~80)
    pytest -m infrastructure            # Webhooks, WS, A2A (~70)
    pytest -m dormant                   # Dormant/unwired modules (~95)
    pytest -m redundant                 # Redundant/low-value (~99)

Combine profiles:
    pytest -m "core or erc8004"         # Core + ERC-8004
    pytest -m "core or payments"        # Core + payments
"""

import os
import pytest
import sys
from pathlib import Path
from datetime import datetime, UTC

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_collection_modifyitems(config, items):
    """Auto-exclude dormant and redundant tests unless explicitly requested.

    Default behavior (no -m flag): skip dormant tests.
    If user passes any -m expression: respect it exactly.
    Set EM_TEST_PROFILE=full to run everything.
    """
    profile = os.environ.get("EM_TEST_PROFILE", "").lower()

    # If user explicitly set a marker expression or wants full, don't interfere
    if config.getoption("-m") or profile == "full":
        return

    # Default: skip dormant tests (not wired into production)
    skip_dormant = pytest.mark.skip(
        reason="Dormant test (module not in active endpoints). Run with -m dormant or EM_TEST_PROFILE=full"
    )

    for item in items:
        if "dormant" in item.keywords:
            item.add_marker(skip_dormant)


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
