"""
Tests for Platform Configuration System (NOW-213)

Tests the centralized configuration system including:
- Default values
- Caching behavior
- Type conversion
- Public vs private config
"""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock


class TestPlatformConfigDefaults:
    """Test default configuration values."""

    def test_default_platform_fee(self):
        """Default platform fee should be 8%."""
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["fees.platform_fee_pct"] == Decimal("0.08")

    def test_default_partial_release(self):
        """Default partial release should be 30%."""
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["fees.partial_release_pct"] == Decimal("0.30")

    def test_default_min_bounty(self):
        """Default minimum bounty should be $0.25."""
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["bounty.min_usd"] == Decimal("0.25")

    def test_default_max_bounty(self):
        """Default maximum bounty should be $10,000."""
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["bounty.max_usd"] == Decimal("10000.00")

    def test_default_approval_timeout(self):
        """Default approval timeout should be 48 hours."""
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["timeout.approval_hours"] == 48

    def test_default_max_resubmissions(self):
        """Default max resubmissions should be 3."""
        from config.platform_config import PlatformConfig

        assert PlatformConfig._defaults["limits.max_resubmissions"] == 3

    def test_default_supported_networks(self):
        """Default networks should include base."""
        from config.platform_config import PlatformConfig

        networks = PlatformConfig._defaults["x402.supported_networks"]
        assert "base" in networks
        assert "ethereum" in networks

    def test_default_supported_tokens(self):
        """Default tokens should include USDC."""
        from config.platform_config import PlatformConfig

        tokens = PlatformConfig._defaults["x402.supported_tokens"]
        assert "USDC" in tokens


class TestPlatformConfigCaching:
    """Test caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_returns_default_when_no_db(self):
        """Should return default when database unavailable."""
        from config.platform_config import PlatformConfig

        # Clear cache and mock supabase as unavailable
        PlatformConfig._cache.clear()
        PlatformConfig._supabase = None

        value = await PlatformConfig.get("fees.platform_fee_pct", Decimal("0.08"))
        assert value == Decimal("0.08")

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Cache invalidation should work."""
        from config.platform_config import PlatformConfig

        # Put something in cache
        PlatformConfig._cache["test_key"] = MagicMock(
            value="test_value", expires_at=float("inf")
        )

        # Invalidate
        PlatformConfig.invalidate_cache("test_key")

        assert "test_key" not in PlatformConfig._cache

    @pytest.mark.asyncio
    async def test_cache_invalidation_all(self):
        """Full cache invalidation should clear everything."""
        from config.platform_config import PlatformConfig

        # Put multiple items in cache
        PlatformConfig._cache["key1"] = MagicMock()
        PlatformConfig._cache["key2"] = MagicMock()

        # Invalidate all
        PlatformConfig.invalidate_cache()

        assert len(PlatformConfig._cache) == 0


class TestPlatformConfigTypeConversion:
    """Test type conversion from JSONB values."""

    def test_convert_fee_to_decimal(self):
        """Fee values should be converted to Decimal."""
        from config.platform_config import PlatformConfig

        result = PlatformConfig._convert_type(0.08, "fees.platform_fee_pct")
        assert isinstance(result, Decimal)
        assert result == Decimal("0.08")

    def test_convert_bounty_to_decimal(self):
        """Bounty values should be converted to Decimal."""
        from config.platform_config import PlatformConfig

        result = PlatformConfig._convert_type(0.25, "bounty.min_usd")
        assert isinstance(result, Decimal)
        assert result == Decimal("0.25")

    def test_convert_hours_to_int(self):
        """Hour values should be converted to int."""
        from config.platform_config import PlatformConfig

        result = PlatformConfig._convert_type("48", "timeout.approval_hours")
        assert isinstance(result, int)
        assert result == 48

    def test_convert_limit_to_int(self):
        """Limit values should be converted to int."""
        from config.platform_config import PlatformConfig

        result = PlatformConfig._convert_type("3", "limits.max_resubmissions")
        assert isinstance(result, int)
        assert result == 3


class TestPlatformConfigConvenienceMethods:
    """Test convenience methods for common config values."""

    @pytest.mark.asyncio
    async def test_get_fee_pct(self):
        """get_fee_pct should return Decimal."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None  # Force default
        value = await PlatformConfig.get_fee_pct()

        assert isinstance(value, Decimal)
        assert value == Decimal("0.08")

    @pytest.mark.asyncio
    async def test_get_partial_release_pct(self):
        """get_partial_release_pct should return Decimal."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None
        value = await PlatformConfig.get_partial_release_pct()

        assert isinstance(value, Decimal)
        assert value == Decimal("0.30")

    @pytest.mark.asyncio
    async def test_get_min_bounty(self):
        """get_min_bounty should return Decimal."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None
        value = await PlatformConfig.get_min_bounty()

        assert isinstance(value, Decimal)
        assert value == Decimal("0.25")

    @pytest.mark.asyncio
    async def test_get_max_bounty(self):
        """get_max_bounty should return Decimal."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None
        value = await PlatformConfig.get_max_bounty()

        assert isinstance(value, Decimal)
        assert value == Decimal("10000.00")

    @pytest.mark.asyncio
    async def test_get_approval_timeout_hours(self):
        """get_approval_timeout_hours should return int."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None
        value = await PlatformConfig.get_approval_timeout_hours()

        assert isinstance(value, int)
        assert value == 48

    @pytest.mark.asyncio
    async def test_get_max_resubmissions(self):
        """get_max_resubmissions should return int."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None
        value = await PlatformConfig.get_max_resubmissions()

        assert isinstance(value, int)
        assert value == 3

    @pytest.mark.asyncio
    async def test_get_supported_networks(self):
        """get_supported_networks should return list."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None
        value = await PlatformConfig.get_supported_networks()

        assert isinstance(value, list)
        assert "base" in value

    @pytest.mark.asyncio
    async def test_get_supported_tokens(self):
        """get_supported_tokens should return list."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None
        value = await PlatformConfig.get_supported_tokens()

        assert isinstance(value, list)
        assert "USDC" in value

    @pytest.mark.asyncio
    async def test_get_preferred_network(self):
        """get_preferred_network should return string."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None
        value = await PlatformConfig.get_preferred_network()

        assert isinstance(value, str)
        assert value == "base"


class TestPlatformConfigPublicConfig:
    """Test public configuration endpoint."""

    @pytest.mark.asyncio
    async def test_get_public_config(self):
        """get_public_config should return only public values."""
        from config.platform_config import PlatformConfig

        PlatformConfig._supabase = None  # Force defaults
        config = await PlatformConfig.get_public_config()

        # Should include public values
        assert "min_bounty_usd" in config
        assert "max_bounty_usd" in config
        assert "supported_networks" in config

        # Should not include private values (fees, treasury, etc)
        assert "platform_fee_pct" not in config
        assert "treasury_address" not in config


class TestModuleLevelHelpers:
    """Test module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_get_config_helper(self):
        """get_config() should work like PlatformConfig.get()."""
        from config import get_config

        value = await get_config("fees.platform_fee_pct", Decimal("0.08"))
        assert value == Decimal("0.08")

    def test_invalidate_config_cache_helper(self):
        """invalidate_config_cache() should work."""
        from config import invalidate_config_cache

        # Should not raise
        invalidate_config_cache("some_key")
        invalidate_config_cache()


class TestFeeCalculations:
    """Test fee calculations using config values."""

    @pytest.mark.asyncio
    async def test_calculate_total_with_fee(self):
        """Calculate total payment including platform fee."""
        from config.platform_config import PlatformConfig

        bounty = Decimal("10.00")
        fee_pct = await PlatformConfig.get_fee_pct()

        total = bounty * (1 + fee_pct)

        assert total == Decimal("10.80")  # $10 + 8% = $10.80

    @pytest.mark.asyncio
    async def test_calculate_worker_payout(self):
        """Calculate worker payout after fee deduction."""
        from config.platform_config import PlatformConfig

        bounty = Decimal("10.00")
        fee_pct = await PlatformConfig.get_fee_pct()

        platform_fee = bounty * fee_pct
        worker_payout = bounty - platform_fee

        assert platform_fee == Decimal("0.80")  # 8% of $10
        assert worker_payout == Decimal("9.20")  # $10 - $0.80

    @pytest.mark.asyncio
    async def test_calculate_partial_release(self):
        """Calculate partial release on submission."""
        from config.platform_config import PlatformConfig

        bounty = Decimal("10.00")
        fee_pct = await PlatformConfig.get_fee_pct()
        partial_pct = await PlatformConfig.get_partial_release_pct()

        # Worker payout after fee
        worker_payout = bounty * (1 - fee_pct)  # $9.20

        # Partial release (30% of worker payout)
        partial_release = worker_payout * partial_pct

        assert partial_release == Decimal("2.76")  # 30% of $9.20
