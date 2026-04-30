"""Multi-provider verification tier resolver for Execution Market.

Provides a provider-agnostic enforcement layer over per-provider clients
(World ID, VeryAI, future: Idena, BrightID, etc).

Tier matrix:
  - T0  bounty < t1_threshold        -> no verification required
  - T1  t1 <= bounty < t2_threshold  -> any T1 provider satisfies (VeryAI palm OR Orb)
  - T2  bounty >= t2_threshold       -> only T2 providers (Orb)

See: docs/planning/MASTER_PLAN_VERYAI_INTEGRATION.md Phase 1.4
"""

from .enforcement import check_tier_eligibility, resolve_tier_for_bounty
from .tiers import Tier, TierConfig, load_tier_config

__all__ = [
    "Tier",
    "TierConfig",
    "load_tier_config",
    "check_tier_eligibility",
    "resolve_tier_for_bounty",
]
