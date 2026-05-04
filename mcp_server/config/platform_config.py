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
        fee = await PlatformConfig.get_fee_pct()  # Decimal("0.13")
        min_bounty = await PlatformConfig.get_min_bounty()  # Decimal("0.01")

        # Get raw value
        value = await PlatformConfig.get("fees.platform_fee_pct", default=0.13)

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
        "fees.platform_fee_pct": Decimal("0.13"),
        "fees.partial_release_pct": Decimal("0.30"),
        "fees.min_fee_usd": Decimal("0.01"),
        "fees.protection_fund_pct": Decimal("0.005"),
        # Limits
        "bounty.min_usd": Decimal(
            "0.01"
        ),  # Minimum bounty (configurable via admin API)
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
        # World AgentKit (human verification via AgentBook on Base)
        "feature.world_agentkit_enabled": True,
        # World ID 4.0 integration
        "feature.world_id_enabled": True,
        "feature.world_id_required_for_high_value": True,
        "worldid.min_bounty_for_orb_usd": Decimal("500.00"),
        # ----------------------------------------------------------------
        # VeryAI palm-print integration (mid-tier KYC, $50 - $500 band)
        # See: docs/planning/MASTER_PLAN_VERYAI_INTEGRATION.md
        # All flags default OFF until Phase 6 sandbox validation.
        # ----------------------------------------------------------------
        "feature.veryai_enabled": False,
        "feature.veryai_required_for_mid_value": True,
        "veryai.min_bounty_for_palm_usd": Decimal("50.00"),
        "veryai.api_base_url": "https://api.very.org",
        "veryai.oauth2_authorize_path": "/oauth2/authorize",
        "veryai.oauth2_token_path": "/oauth2/token",
        "veryai.oauth2_userinfo_path": "/oauth2/userinfo",
        # Multi-provider tier resolver
        "verification.tiers.t1.min_bounty_usd": Decimal("50.00"),
        "verification.tiers.t2.min_bounty_usd": Decimal("500.00"),
        "verification.tiers.t1.providers": ["veryai_palm", "worldid_orb"],
        "verification.tiers.t2.providers": ["worldid_orb"],
        # ClawKey KYA (Know Your Agent) — additive trust signal, never blocking
        "feature.clawkey_kya_enabled": False,
        "clawkey.api_base_url": "https://api.clawkey.ai",
        "clawkey.verify_public_key_path": "/v1/agent/verify/public-key/",
        "clawkey.verify_device_id_path": "/v1/agent/verify/device/",
        "clawkey.cache_ttl_seconds": 300,
        # MeshRelay integration
        "feature.meshrelay_dynamic_channels": False,
        "feature.meshrelay_relay_chains": False,
        "feature.meshrelay_reverse_auctions": False,
        "meshrelay.enabled": True,
        "meshrelay.api_url": "https://api.meshrelay.xyz",
        "meshrelay.webhook_url": "",
        "meshrelay.partner_api_key": "",
        "meshrelay.channels.bounties": "#bounties",
        "meshrelay.channels.agents": "#Agents",
        "meshrelay.anti_snipe_cooldown_sec": 30,
        "meshrelay.claim_priority_window_sec": 120,
        "meshrelay.channel_auto_expire_minutes": 90,
        "meshrelay.max_bids_per_auction": 20,
        "meshrelay.identity_sync_interval_sec": 300,
        # Task Chat (IRC relay)
        "feature.task_chat_enabled": False,
        "chat.irc_host": os.getenv("CHAT_IRC_HOST", "irc.meshrelay.xyz"),
        "chat.irc_port": int(os.getenv("CHAT_IRC_PORT", "6697")),
        "chat.irc_tls": os.getenv("CHAT_IRC_TLS", "true").lower() == "true",
        "chat.irc_nick_prefix": os.getenv("CHAT_IRC_NICK_PREFIX", "em-relay"),
        "chat.max_message_length": 2000,
        "chat.history_limit": 50,
        "chat.channel_prefix": "#task-",
        "chat.agent_join_mode": os.getenv("CHAT_AGENT_JOIN_MODE", "optional"),
        "chat.retention_days": 90,
        # Payments
        "x402.supported_networks": [
            "base",
            "ethereum",
            "polygon",
            "arbitrum",
            "celo",
            "monad",
            "avalanche",
            "optimism",
            "skale",
        ],
        "x402.supported_tokens": ["USDC", "EURC", "USDT", "PYUSD", "AUSD"],
        "x402.preferred_network": "base",
        "x402.facilitator_url": "https://facilitator.ultravioletadao.xyz",
        # Treasury
        "treasury.wallet_address": "0x0000000000000000000000000000000000000000",
        "treasury.protection_fund_address": "0x0000000000000000000000000000000000000000",
        # ----------------------------------------------------------------
        # Arbiter (Ring 2 dual-inference verdict service)
        # See: docs/planning/MASTER_PLAN_COMMERCE_SCHEME_ARBITER.md
        # ----------------------------------------------------------------
        # Master switch -- when False, all arbiter_mode values fall back to 'manual'
        "feature.arbiter_enabled": False,
        # Tier boundaries (USD bounty thresholds for inference strategy)
        "arbiter.tier.cheap_max_usd": Decimal("1.00"),  # bounty < 1   -> CHEAP   ($0)
        "arbiter.tier.standard_max_usd": Decimal(
            "10.00"
        ),  # 1 <= bounty < 10 -> STANDARD (~$0.001)
        # Default thresholds (overridable per-category in arbiter/registry.py)
        "arbiter.thresholds.pass": Decimal("0.80"),  # >= -> PASS
        "arbiter.thresholds.fail": Decimal("0.30"),  # <= -> FAIL
        # Cost controls
        "arbiter.cost.max_per_eval_usd": Decimal("0.20"),  # Hard cap per submission
        "arbiter.cost.daily_budget_usd": Decimal("100.00"),  # Soft cap, alert at 80%
        "arbiter.cost.alert_threshold_pct": Decimal("0.80"),
        "arbiter.cost.bounty_ratio_max": Decimal("0.10"),  # Cost <= 10% of bounty
        # Escalation (L2 human arbiter)
        "arbiter.escalation.timeout_hours": 24,  # L2 human review window
        "arbiter.escalation.min_human_trust_tier": "high",  # VerificationAdapter tier
        # Provider diversity (Tier MAX requires 2 different providers)
        "arbiter.providers.preferred_ring2_a": "anthropic",
        "arbiter.providers.preferred_ring2_b": "openai",
        # Mobile Feature Flags (Apple Review Mode)
        "mobile.terminology_mode": "conservative",
        "mobile.show_chain_logos": False,
        "mobile.show_chain_selector": False,
        "mobile.show_blockchain_details": False,
        "mobile.show_stablecoin_names": False,
        "mobile.show_protocol_details": False,
        "mobile.show_escrow_details": False,
        "mobile.show_onboarding_crypto_slides": False,
        "mobile.show_faq_blockchain": False,
        "mobile.show_ai_agent_references": True,
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

        # Fall back to class defaults first, then explicit default
        if key in cls._defaults:
            return cls._defaults[key]

        if default is not None:
            return default

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
            except Exception:
                return value

        # Integer values
        if any(pattern in key for pattern in ["_hours", "max_", "limits."]) and not any(
            pattern in key for pattern in ["_usd", "_pct"]
        ):
            try:
                return int(value)
            except Exception:
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
        """Get platform fee percentage (e.g., Decimal("0.13") = 13%)."""
        return await cls.get("fees.platform_fee_pct", Decimal("0.13"))

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
        """Get list of supported payment networks (defaults from sdk_client)."""
        from integrations.x402.sdk_client import get_enabled_networks

        return await cls.get(
            "x402.supported_networks",
            get_enabled_networks(),
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
            k: v for k, v in cls._defaults.items() if k.startswith(category.value + ".")
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
        fee = await get_config("fees.platform_fee_pct", Decimal("0.13"))
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
