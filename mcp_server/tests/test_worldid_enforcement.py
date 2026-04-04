"""Tests for World ID enforcement utility (shared by REST + MCP)."""

import sys
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

# Ensure mcp_server root is on sys.path
_mcp_root = str(Path(__file__).resolve().parent.parent)
if _mcp_root not in sys.path:
    sys.path.insert(0, _mcp_root)

# Force-remove stale integrations stub
if "integrations" in sys.modules and not hasattr(
    sys.modules["integrations"], "__path__"
):
    del sys.modules["integrations"]
if "integrations.worldid" in sys.modules and not hasattr(
    sys.modules["integrations.worldid"], "__path__"
):
    del sys.modules["integrations.worldid"]

pytestmark = pytest.mark.worldid


def _mock_db_client(world_id_verified=False, world_id_level=None, executor_found=True):
    """Create a mock Supabase client that returns executor World ID status."""
    mock = MagicMock()
    if executor_found:
        data = [
            {"world_id_verified": world_id_verified, "world_id_level": world_id_level}
        ]
    else:
        data = []
    mock.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=data
    )
    return mock


class TestCheckWorldIdEligibility:
    """Tests for check_world_id_eligibility() shared utility."""

    @pytest.mark.asyncio
    async def test_low_bounty_unverified_allowed(self):
        """Tasks below threshold should allow unverified workers."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        db = _mock_db_client(world_id_verified=False)
        allowed, err = await check_world_id_eligibility(
            "exec-1", Decimal("1.00"), db_client=db
        )

        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    async def test_high_bounty_orb_verified_allowed(self):
        """High-value tasks should allow orb-verified workers."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        db = _mock_db_client(world_id_verified=True, world_id_level="orb")
        allowed, err = await check_world_id_eligibility(
            "exec-1", Decimal("10.00"), db_client=db
        )

        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    async def test_high_bounty_unverified_blocked(self):
        """High-value tasks should block unverified workers."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        db = _mock_db_client(world_id_verified=False)
        allowed, err = await check_world_id_eligibility(
            "exec-1", Decimal("10.00"), db_client=db
        )

        assert allowed is False
        assert err is not None
        assert err["error"] == "world_id_orb_required"
        assert err["required_level"] == "orb"
        assert err["current_level"] is None

    @pytest.mark.asyncio
    async def test_high_bounty_device_verified_blocked(self):
        """Device-level verification is not enough for high-value tasks."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        db = _mock_db_client(world_id_verified=True, world_id_level="device")
        allowed, err = await check_world_id_eligibility(
            "exec-1", Decimal("5.00"), db_client=db
        )

        assert allowed is False
        assert err["error"] == "world_id_orb_required"
        assert err["current_level"] == "device"

    @pytest.mark.asyncio
    async def test_exact_threshold_requires_orb(self):
        """Bounty exactly at threshold still requires verification."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        db = _mock_db_client(world_id_verified=False)
        allowed, err = await check_world_id_eligibility(
            "exec-1", Decimal("5.00"), db_client=db
        )

        assert allowed is False
        assert err["error"] == "world_id_orb_required"

    @pytest.mark.asyncio
    @patch.dict("os.environ", {"EM_WORLD_ID_ENABLED": "false"})
    async def test_disabled_via_env_allows_all(self):
        """When EM_WORLD_ID_ENABLED=false, all applications are allowed."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        db = _mock_db_client(world_id_verified=False)
        allowed, err = await check_world_id_eligibility(
            "exec-1", Decimal("100.00"), db_client=db
        )

        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    async def test_config_disabled_allows_all(self):
        """When feature.world_id_required_for_high_value=false, all allowed."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        with patch("config.platform_config.PlatformConfig") as mock_config:
            mock_config.get = AsyncMock(side_effect=lambda key, default: False)
            db = _mock_db_client(world_id_verified=False)
            allowed, err = await check_world_id_eligibility(
                "exec-1", Decimal("100.00"), db_client=db
            )

        assert allowed is True
        assert err is None

    @pytest.mark.asyncio
    async def test_executor_not_found_blocked(self):
        """If executor doesn't exist in DB, should be blocked (fail-closed for missing data)."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        db = _mock_db_client(executor_found=False)
        allowed, err = await check_world_id_eligibility(
            "exec-nonexistent", Decimal("10.00"), db_client=db
        )

        assert allowed is False
        assert err["error"] == "world_id_orb_required"

    @pytest.mark.asyncio
    async def test_db_error_fails_open(self):
        """Transient DB errors should fail-open (don't block workers)."""
        from integrations.worldid.enforcement import check_world_id_eligibility

        db = MagicMock()
        db.table.side_effect = Exception("Connection timeout")

        allowed, err = await check_world_id_eligibility(
            "exec-1", Decimal("10.00"), db_client=db
        )

        assert allowed is True
        assert err is None
