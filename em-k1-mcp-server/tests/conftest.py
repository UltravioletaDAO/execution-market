"""Shared pytest fixtures for em-k1-mcp tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from em_k1_mcp.backends.mock import MockK1Backend
from em_k1_mcp.config import K1Config


@pytest.fixture
def config(tmp_path: Path) -> K1Config:
    """A safe, isolated K1Config — captures go to a tmp_path subdir."""
    return K1Config(
        k1_host="127.0.0.1",
        backend="mock",
        max_linear_velocity_mps=0.6,
        max_angular_velocity_rps=0.8,
        max_grip_force_n=40.0,
        vision_model="claude-opus-4-7",
        capture_dir=tmp_path / "captures",
        em_api_url="https://api.test.execution.market",
        em_wallet_key_path="YOUR_KEYSTORE_PATH_HERE",
        em_agent_id="",
        em_worker_name="k1-test-executor",
        log_level="WARNING",
    )


@pytest.fixture
def mock_backend(config: K1Config) -> MockK1Backend:
    return MockK1Backend(config)
