"""
Pytest configuration and fixtures for Chamba MCP Server tests.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, UTC

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


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
