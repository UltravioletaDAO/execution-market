"""Tier configuration loaded from PlatformConfig.

Tiers express which verification providers satisfy a given bounty band.
Loaded on every check (PlatformConfig is cached, ~300s TTL).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List


class Tier(str, Enum):
    """Verification tier required for a task bounty."""

    T0 = "t0"  # No verification required
    T1 = "t1"  # Mid-value: any T1 provider satisfies
    T2 = "t2"  # High-value: only T2 providers satisfy


# Provider keys used in PlatformConfig and on executor flags.
PROVIDER_VERYAI_PALM = "veryai_palm"
PROVIDER_WORLDID_ORB = "worldid_orb"
PROVIDER_WORLDID_DEVICE = "worldid_device"


@dataclass(frozen=True)
class TierConfig:
    """Resolved tier configuration."""

    t1_min_bounty_usd: Decimal
    t2_min_bounty_usd: Decimal
    t1_providers: List[str] = field(default_factory=list)
    t2_providers: List[str] = field(default_factory=list)


async def load_tier_config() -> TierConfig:
    """Load the active tier configuration from PlatformConfig.

    Falls back to safe defaults if PlatformConfig is unavailable.
    Defaults preserve current Orb-only behavior at $500.
    """
    from config.platform_config import PlatformConfig

    t1_min = await PlatformConfig.get(
        "verification.tiers.t1.min_bounty_usd", Decimal("50.00")
    )
    t2_min = await PlatformConfig.get(
        "verification.tiers.t2.min_bounty_usd", Decimal("500.00")
    )
    t1_providers = await PlatformConfig.get(
        "verification.tiers.t1.providers",
        [PROVIDER_VERYAI_PALM, PROVIDER_WORLDID_ORB],
    )
    t2_providers = await PlatformConfig.get(
        "verification.tiers.t2.providers", [PROVIDER_WORLDID_ORB]
    )

    return TierConfig(
        t1_min_bounty_usd=Decimal(str(t1_min)),
        t2_min_bounty_usd=Decimal(str(t2_min)),
        t1_providers=list(t1_providers) if t1_providers else [],
        t2_providers=list(t2_providers) if t2_providers else [],
    )
