"""
Platform Configuration System

Provides centralized, cached access to platform settings stored in Supabase.
All configuration values are stored in the platform_config table and can be
modified via admin API without redeploying.

Thread-safe caching with configurable TTL.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ConfigCategory(str, Enum):
    """Configuration categories."""

    FEES = "fees"
    LIMITS = "limits"
    TIMING = "timing"
    FEATURES = "features"
    PAYMENTS = "payments"
    TREASURY = "treasury"


@dataclass
class CacheEntry:
    """Single cache entry with expiration."""

    value: Any
    expires_at: float


class PlatformConfig:
    """
    Centralized platform configuration with caching.

    Values are read from Supabase platform_config table and cached
    in memory to avoid database calls on every request.

    Usage:
        # Get specific config methods (recommended)
        fee = await PlatformConfig.get_fee_pct()  # Decimal("0.08")
        min_bounty = await PlatformConfig.get_min_bounty()  # Decimal("0.25")

        # Get raw value
        value = await PlatformConfig.get("fees.platform_fee_pct", default=0.08)

        # Invalidate cache (after admin update)
        PlatformConfig.invalidate_cache("fees.platform_fee_pct")
        PlatformConfig.invalidate_cache()  # Invalidate all
    """

    # Cache storage
    _cache: Dict[str, CacheEntry] = {}
    _cache_lock = asyncio.Lock()

    # Cache TTL in seconds (5 minutes default)
    _cache_ttl: int = int(os.environ.get("CONFIG_CACHE_TTL_SECONDS", "300"))

    # Supabase client (lazy loaded)
    _supabase = None

    # Default values (used when DB is unavailable)
    _defaults: Dict[str, Any] = {
        # Fees
        "fees.platform_fee_pct": Decimal("0.08"),
        "fees.partial_release_pct": Decimal("0.30"),
        "fees.min_fee_usd": Decimal("0.01"),
        "fees.protection_fund_pct": Decimal("0.005"),
        # Limits
        "bounty.min_usd": Decimal("0.01"),  # Lowered for testing micropayments
        "bounty.max_usd": Decimal("10000.00"),
        "limits.max_resubmissions": 3,
        "limits.max_active_tasks_per_agent": 100,
        "limits.max_applications_per_task": 50,
        "limits.max_active_tasks_per_worker": 10,
        # Timing
        "timeout.approval_hours": 48,
        "timeout.task_default_hours": 24,
        "timeout.auto_release_on_timeout": True,
        # Features
        "feature.disputes_enabled": True,
        "feature.reputation_enabled": True,
        "feature.auto_matching_enabled": False,
        "feature.partial_release_enabled": True,
        "feature.websocket_notifications": True,
        # Payments
        "x402.supported_networks": ["base", "ethereum", "polygon", "optimism", "arbitrum"],
        "x402.supported_tokens": ["USDC", "USDT", "DAI"],
        "x402.preferred_network": "ethereum",
        "x402.facilitator_url": "https://facilitator.ultravioletadao.xyz",
        # Treasury
        "treasury.wallet_address": "0x0000000000000000000000000000000000000000",
        "treasury.protection_fund_address": "0x0000000000000000000000000000000000000000",
    }

    @classmethod
    def _get_supabase(cls):
        """Lazy load Supabase client."""
        if cls._supabase is None:
            try:
                from supabase_client import get_supabase_client

                cls._supabase = get_supabase_client()
            except Exception as e:
                logger.warning(f"Could not initialize Supabase client: {e}")
        return cls._supabase

    @classmethod
    async def get(cls, key: str, default: T = None) -> Union[Any, T]:
        """
        Get configuration value with caching.

        Args:
            key: Configuration key (e.g., "fees.platform_fee_pct")
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        # Check cache first
        async with cls._cache_lock:
            if key in cls._cache:
                entry = cls._cache[key]
                if entry.expires_at > time.time():
                    return entry.value
                else:
                    # Expired, remove from cache
                    del cls._cache[key]

        # Try to load from database
        try:
            supabase = cls._get_supabase()
            if supabase:
                result = (
                    supabase.table("platform_config")
                    .select("value")
                    .eq("key", key)
                    .single()
                    .execute()
                )

                if result.data:
                    raw_value = result.data["value"]
                    # Parse JSONB value
                    value = cls._parse_value(raw_value, key)

                    # Cache it
                    async with cls._cache_lock:
                        cls._cache[key] = CacheEntry(
                            value=value, expires_at=time.time() + cls._cache_ttl
                        )

                    return value
        except Exception as e:
            logger.warning(f"Error loading config {key} from DB: {e}")

        # Fall back to defaults
        if default is not None:
            return default

        if key in cls._defaults:
            return cls._defaults[key]

        return None

    @classmethod
    def _parse_value(cls, raw_value: Any, key: str) -> Any:
        """Parse JSONB value to appropriate Python type."""
        # If it's already parsed by supabase-py
        if not isinstance(raw_value, str):
            return cls._convert_type(raw_value, key)

        try:
            parsed = json.loads(raw_value)
            return cls._convert_type(parsed, key)
        except (json.JSONDecodeError, TypeError):
            return raw_value

    @classmethod
    def _convert_type(cls, value: Any, key: str) -> Any:
        """Convert value to appropriate type based on key pattern."""
        # Decimal values (fees, amounts)
        if any(
            pattern in key
            for pattern in ["_pct", "_usd", "bounty.min", "bounty.max", "min_fee"]
        ):
            try:
                return Decimal(str(value))
            except:
                return value

        # Integer values
        if any(
            pattern in key for pattern in ["_hours", "max_", "limits."]
        ) and not any(pattern in key for pattern in ["_usd", "_pct"]):
            try:
                return int(value)
            except:
                return value

        return value

    @classmethod
    def invalidate_cache(cls, key: Optional[str] = None) -> None:
        """
        Invalidate cache entries.

        Args:
            key: Specific key to invalidate, or None for all
        """
        if key:
            cls._cache.pop(key, None)
            logger.info(f"Invalidated config cache for: {key}")
        else:
            cls._cache.clear()
            logger.info("Invalidated all config cache")

    # ==================== CONVENIENCE METHODS ====================
    # These provide typed access to common configuration values

    @classmethod
    async def get_fee_pct(cls) -> Decimal:
        """Get platform fee percentage (e.g., Decimal("0.08") = 8%)."""
        return await cls.get("fees.platform_fee_pct", Decimal("0.08"))

    @classmethod
    async def get_partial_release_pct(cls) -> Decimal:
        """Get partial release percentage on submission (e.g., Decimal("0.30") = 30%)."""
        return await cls.get("fees.partial_release_pct", Decimal("0.30"))

    @classmethod
    async def get_min_fee_usd(cls) -> Decimal:
        """Get minimum platform fee in USD."""
        return await cls.get("fees.min_fee_usd", Decimal("0.01"))

    @classmethod
    async def get_min_bounty(cls) -> Decimal:
        """Get minimum bounty in USD."""
        return await cls.get("bounty.min_usd", Decimal("0.01"))

    @classmethod
    async def get_max_bounty(cls) -> Decimal:
        """Get maximum bounty in USD."""
        return await cls.get("bounty.max_usd", Decimal("10000.00"))

    @classmethod
    async def get_approval_timeout_hours(cls) -> int:
        """Get approval timeout in hours."""
        return await cls.get("timeout.approval_hours", 48)

    @classmethod
    async def get_default_deadline_hours(cls) -> int:
        """Get default task deadline in hours."""
        return await cls.get("timeout.task_default_hours", 24)

    @classmethod
    async def get_max_resubmissions(cls) -> int:
        """Get maximum resubmission attempts."""
        return await cls.get("limits.max_resubmissions", 3)

    @classmethod
    async def get_max_applications_per_task(cls) -> int:
        """Get maximum applications per task."""
        return await cls.get("limits.max_applications_per_task", 50)

    @classmethod
    async def is_feature_enabled(cls, feature: str) -> bool:
        """Check if a feature is enabled."""
        return await cls.get(f"feature.{feature}_enabled", False)

    @classmethod
    async def get_supported_networks(cls) -> List[str]:
        """Get list of supported payment networks."""
        return await cls.get(
            "x402.supported_networks",
            ["base", "ethereum", "polygon", "optimism", "arbitrum"],
        )

    @classmethod
    async def get_supported_tokens(cls) -> List[str]:
        """Get list of supported payment tokens."""
        return await cls.get("x402.supported_tokens", ["USDC", "USDT", "DAI"])

    @classmethod
    async def get_preferred_network(cls) -> str:
        """Get preferred payment network."""
        return await cls.get("x402.preferred_network", "base")

    @classmethod
    async def get_facilitator_url(cls) -> str:
        """Get x402 facilitator URL."""
        return await cls.get(
            "x402.facilitator_url", "https://facilitator.ultravioletadao.xyz"
        )

    @classmethod
    async def get_treasury_address(cls) -> str:
        """Get treasury wallet address."""
        return await cls.get(
            "treasury.wallet_address",
            "0x0000000000000000000000000000000000000000",
        )

    # ==================== BATCH OPERATIONS ====================

    @classmethod
    async def get_all_by_category(cls, category: ConfigCategory) -> Dict[str, Any]:
        """
        Get all configuration values for a category.

        Args:
            category: Configuration category

        Returns:
            Dictionary of key -> value
        """
        try:
            supabase = cls._get_supabase()
            if supabase:
                result = (
                    supabase.table("platform_config")
                    .select("key, value")
                    .eq("category", category.value)
                    .execute()
                )

                if result.data:
                    configs = {}
                    for row in result.data:
                        key = row["key"]
                        value = cls._parse_value(row["value"], key)
                        configs[key] = value

                        # Cache each value
                        async with cls._cache_lock:
                            cls._cache[key] = CacheEntry(
                                value=value, expires_at=time.time() + cls._cache_ttl
                            )

                    return configs
        except Exception as e:
            logger.warning(f"Error loading config category {category}: {e}")

        # Return defaults for this category
        return {
            k: v
            for k, v in cls._defaults.items()
            if k.startswith(category.value + ".")
        }

    @classmethod
    async def get_public_config(cls) -> Dict[str, Any]:
        """
        Get all public configuration values (safe for API response).

        Returns:
            Dictionary of public config values
        """
        try:
            supabase = cls._get_supabase()
            if supabase:
                result = (
                    supabase.table("platform_config")
                    .select("key, value")
                    .eq("is_public", True)
                    .execute()
                )

                if result.data:
                    configs = {}
                    for row in result.data:
                        key = row["key"]
                        value = cls._parse_value(row["value"], key)

                        # Strip prefix for cleaner API response
                        short_key = key.split(".", 1)[-1] if "." in key else key
                        configs[short_key] = value

                    return configs
        except Exception as e:
            logger.warning(f"Error loading public config: {e}")

        # Return public defaults
        return {
            "min_bounty_usd": float(cls._defaults["bounty.min_usd"]),
            "max_bounty_usd": float(cls._defaults["bounty.max_usd"]),
            "supported_networks": cls._defaults["x402.supported_networks"],
            "supported_tokens": cls._defaults["x402.supported_tokens"],
            "preferred_network": cls._defaults["x402.preferred_network"],
        }

    @classmethod
    async def set(
        cls,
        key: str,
        value: Any,
        changed_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Update a configuration value.

        Args:
            key: Configuration key
            value: New value
            changed_by: User ID making the change (for audit)
            reason: Reason for change (for audit)

        Returns:
            True if successful
        """
        try:
            supabase = cls._get_supabase()
            if supabase:
                # Serialize value for JSONB
                json_value = json.dumps(value) if not isinstance(value, str) else value

                result = (
                    supabase.table("platform_config")
                    .update(
                        {
                            "value": json_value,
                            "updated_by": changed_by,
                        }
                    )
                    .eq("key", key)
                    .execute()
                )

                if result.data:
                    # Invalidate cache
                    cls.invalidate_cache(key)
                    logger.info(f"Updated config {key} (reason: {reason})")
                    return True
        except Exception as e:
            logger.error(f"Error updating config {key}: {e}")

        return False


# ==================== MODULE-LEVEL HELPERS ====================


async def get_config(key: str, default: T = None) -> Union[Any, T]:
    """
    Get configuration value (convenience function).

    Usage:
        from config import get_config
        fee = await get_config("fees.platform_fee_pct", Decimal("0.08"))
    """
    return await PlatformConfig.get(key, default)


def invalidate_config_cache(key: Optional[str] = None) -> None:
    """
    Invalidate configuration cache (convenience function).

    Usage:
        from config import invalidate_config_cache
        invalidate_config_cache("fees.platform_fee_pct")  # Specific key
        invalidate_config_cache()  # All keys
    """
    PlatformConfig.invalidate_cache(key)
