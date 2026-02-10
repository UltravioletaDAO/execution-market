"""
Enterprise Configuration System (NOW-158)

Manages enterprise-specific settings and customization.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from ..rewards.types import RewardType, RewardConfig

logger = logging.getLogger(__name__)


class PlanTier(str, Enum):
    """Enterprise plan tiers."""

    STARTER = "starter"  # Free tier
    GROWTH = "growth"  # $99/mo
    SCALE = "scale"  # $499/mo
    ENTERPRISE = "enterprise"  # Custom


@dataclass
class RateLimitConfig:
    """API rate limit configuration."""

    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    concurrent_tasks: int = 100
    max_bounty_per_task: float = 500.0
    max_monthly_spend: float = 5000.0


@dataclass
class BudgetConfig:
    """Budget management configuration."""

    monthly_limit: float = 1000.0
    daily_limit: Optional[float] = None
    per_task_limit: float = 100.0
    require_approval_above: float = 50.0
    alert_threshold_pct: float = 0.8  # Alert at 80%


@dataclass
class EnterpriseConfig:
    """
    Complete enterprise configuration.

    Includes all customizable settings for an enterprise customer.
    """

    # Identity
    org_id: str
    org_name: str
    plan: PlanTier = PlanTier.STARTER

    # Rewards
    reward_type: RewardType = RewardType.X402
    reward_config: Optional[RewardConfig] = None
    allow_multiple_reward_types: bool = False

    # Rate limits
    rate_limits: RateLimitConfig = field(default_factory=RateLimitConfig)

    # Budget
    budget: BudgetConfig = field(default_factory=BudgetConfig)

    # Features
    features: Dict[str, bool] = field(
        default_factory=lambda: {
            "custom_branding": False,
            "api_access": True,
            "webhooks": True,
            "analytics": True,
            "bulk_upload": False,
            "approval_workflows": False,
            "sso": False,
            "dedicated_support": False,
        }
    )

    # Webhooks
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    webhook_events: List[str] = field(
        default_factory=lambda: ["task.created", "task.completed", "payment.sent"]
    )

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


# Default configurations by plan

PLAN_CONFIGS = {
    PlanTier.STARTER: {
        "rate_limits": RateLimitConfig(
            requests_per_minute=30,
            requests_per_hour=500,
            requests_per_day=5000,
            concurrent_tasks=10,
            max_bounty_per_task=50.0,
            max_monthly_spend=500.0,
        ),
        "budget": BudgetConfig(
            monthly_limit=500.0, per_task_limit=50.0, require_approval_above=25.0
        ),
        "features": {
            "custom_branding": False,
            "api_access": True,
            "webhooks": False,
            "analytics": False,
            "bulk_upload": False,
            "approval_workflows": False,
            "sso": False,
            "dedicated_support": False,
        },
    },
    PlanTier.GROWTH: {
        "rate_limits": RateLimitConfig(
            requests_per_minute=60,
            requests_per_hour=2000,
            requests_per_day=20000,
            concurrent_tasks=50,
            max_bounty_per_task=200.0,
            max_monthly_spend=5000.0,
        ),
        "budget": BudgetConfig(
            monthly_limit=5000.0, per_task_limit=200.0, require_approval_above=100.0
        ),
        "features": {
            "custom_branding": False,
            "api_access": True,
            "webhooks": True,
            "analytics": True,
            "bulk_upload": True,
            "approval_workflows": False,
            "sso": False,
            "dedicated_support": False,
        },
    },
    PlanTier.SCALE: {
        "rate_limits": RateLimitConfig(
            requests_per_minute=120,
            requests_per_hour=5000,
            requests_per_day=50000,
            concurrent_tasks=200,
            max_bounty_per_task=500.0,
            max_monthly_spend=25000.0,
        ),
        "budget": BudgetConfig(
            monthly_limit=25000.0, per_task_limit=500.0, require_approval_above=250.0
        ),
        "features": {
            "custom_branding": True,
            "api_access": True,
            "webhooks": True,
            "analytics": True,
            "bulk_upload": True,
            "approval_workflows": True,
            "sso": False,
            "dedicated_support": True,
        },
    },
    PlanTier.ENTERPRISE: {
        "rate_limits": RateLimitConfig(
            requests_per_minute=300,
            requests_per_hour=10000,
            requests_per_day=100000,
            concurrent_tasks=1000,
            max_bounty_per_task=10000.0,
            max_monthly_spend=100000.0,
        ),
        "budget": BudgetConfig(
            monthly_limit=100000.0,
            per_task_limit=10000.0,
            require_approval_above=1000.0,
        ),
        "features": {
            "custom_branding": True,
            "api_access": True,
            "webhooks": True,
            "analytics": True,
            "bulk_upload": True,
            "approval_workflows": True,
            "sso": True,
            "dedicated_support": True,
        },
    },
}


class EnterpriseManager:
    """
    Manages enterprise configurations.

    Handles:
    - Configuration CRUD
    - Plan upgrades
    - Feature checks
    - Budget tracking
    """

    def __init__(self):
        """Initialize enterprise manager."""
        self._configs: Dict[str, EnterpriseConfig] = {}
        self._spend_tracking: Dict[str, Dict[str, float]] = {}

    async def create_config(
        self, org_id: str, org_name: str, plan: PlanTier = PlanTier.STARTER, **overrides
    ) -> EnterpriseConfig:
        """
        Create enterprise configuration.

        Args:
            org_id: Organization ID
            org_name: Organization name
            plan: Plan tier
            **overrides: Override specific settings

        Returns:
            Created EnterpriseConfig
        """
        plan_defaults = PLAN_CONFIGS.get(plan, PLAN_CONFIGS[PlanTier.STARTER])

        config = EnterpriseConfig(
            org_id=org_id,
            org_name=org_name,
            plan=plan,
            rate_limits=plan_defaults["rate_limits"],
            budget=plan_defaults["budget"],
            features=plan_defaults["features"].copy(),
        )

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)

        self._configs[org_id] = config
        self._spend_tracking[org_id] = {"monthly": 0.0, "daily": 0.0}

        logger.info(f"Enterprise config created: {org_id} ({plan.value})")
        return config

    async def get_config(self, org_id: str) -> Optional[EnterpriseConfig]:
        """Get enterprise configuration."""
        return self._configs.get(org_id)

    async def update_config(self, org_id: str, **updates) -> EnterpriseConfig:
        """Update enterprise configuration."""
        config = self._configs.get(org_id)
        if not config:
            raise ValueError(f"Config not found: {org_id}")

        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)

        config.updated_at = datetime.now(timezone.utc)
        logger.info(f"Enterprise config updated: {org_id}")
        return config

    async def upgrade_plan(self, org_id: str, new_plan: PlanTier) -> EnterpriseConfig:
        """
        Upgrade organization to new plan.

        Args:
            org_id: Organization ID
            new_plan: New plan tier

        Returns:
            Updated config
        """
        config = self._configs.get(org_id)
        if not config:
            raise ValueError(f"Config not found: {org_id}")

        plan_defaults = PLAN_CONFIGS.get(new_plan)
        if not plan_defaults:
            raise ValueError(f"Invalid plan: {new_plan}")

        config.plan = new_plan
        config.rate_limits = plan_defaults["rate_limits"]
        config.budget = plan_defaults["budget"]
        # Merge features (keep custom overrides where possible)
        for feature, enabled in plan_defaults["features"].items():
            if enabled:  # Only enable, don't disable custom features
                config.features[feature] = enabled

        config.updated_at = datetime.now(timezone.utc)
        logger.info(f"Enterprise plan upgraded: {org_id} -> {new_plan.value}")
        return config

    def has_feature(self, org_id: str, feature: str) -> bool:
        """Check if organization has a feature."""
        config = self._configs.get(org_id)
        if not config:
            return False
        return config.features.get(feature, False)

    async def check_budget(self, org_id: str, amount: float) -> Dict[str, Any]:
        """
        Check if spend is within budget.

        Args:
            org_id: Organization ID
            amount: Amount to spend

        Returns:
            Dict with allowed, remaining, requires_approval
        """
        config = self._configs.get(org_id)
        if not config:
            return {"allowed": False, "reason": "config_not_found"}

        tracking = self._spend_tracking.get(org_id, {"monthly": 0.0, "daily": 0.0})
        budget = config.budget

        # Check per-task limit
        if amount > budget.per_task_limit:
            return {
                "allowed": False,
                "reason": "exceeds_per_task_limit",
                "limit": budget.per_task_limit,
            }

        # Check monthly limit
        new_monthly = tracking["monthly"] + amount
        if new_monthly > budget.monthly_limit:
            return {
                "allowed": False,
                "reason": "exceeds_monthly_limit",
                "remaining": budget.monthly_limit - tracking["monthly"],
            }

        # Check daily limit if set
        if budget.daily_limit:
            new_daily = tracking["daily"] + amount
            if new_daily > budget.daily_limit:
                return {
                    "allowed": False,
                    "reason": "exceeds_daily_limit",
                    "remaining": budget.daily_limit - tracking["daily"],
                }

        # Check if requires approval
        requires_approval = amount > budget.require_approval_above

        return {
            "allowed": True,
            "requires_approval": requires_approval,
            "remaining_monthly": budget.monthly_limit - new_monthly,
            "usage_pct": new_monthly / budget.monthly_limit,
        }

    async def record_spend(self, org_id: str, amount: float):
        """Record spend against budget."""
        if org_id not in self._spend_tracking:
            self._spend_tracking[org_id] = {"monthly": 0.0, "daily": 0.0}

        self._spend_tracking[org_id]["monthly"] += amount
        self._spend_tracking[org_id]["daily"] += amount

        # Check alert threshold
        config = self._configs.get(org_id)
        if config:
            usage_pct = (
                self._spend_tracking[org_id]["monthly"] / config.budget.monthly_limit
            )
            if usage_pct >= config.budget.alert_threshold_pct:
                logger.warning(
                    f"Budget alert: {org_id} at {usage_pct:.1%} of monthly limit"
                )
