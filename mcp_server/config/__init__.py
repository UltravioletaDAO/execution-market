"""
Execution Market Configuration System

Centralized, dynamic configuration with caching and audit support.

Usage:
    from config import PlatformConfig

    fee_pct = await PlatformConfig.get_fee_pct()  # Returns Decimal("0.08")
    min_bounty = await PlatformConfig.get_min_bounty()  # Returns Decimal("0.25")

    # Or get raw value
    value = await PlatformConfig.get("fees.platform_fee_pct", default=0.08)
"""

from .platform_config import (
    PlatformConfig,
    ConfigCategory,
    get_config,
    invalidate_config_cache,
)

__all__ = [
    "PlatformConfig",
    "ConfigCategory",
    "get_config",
    "invalidate_config_cache",
]
