"""
Execution Market Task Types Module

Defines different task types and their requirements:
- Base: Abstract task type base class
- Recon: Observation tasks (store checks, crowd counts)
- Trials: Experience testing (mystery shopping)
- LastMile: Delivery coordination
- Prime: Premium worker tier
- Bundles: Task grouping for efficiency
- Cascading: Parent-child task chains
- Insurance: Task insurance tiers

New pluggable task types:
- PhotoVerification: GPS-verified photos
- Delivery: Pickup and delivery with signature
- Survey: Form-based data collection
- MysteryShop: Experience evaluation with receipt
- PriceCheck: Product price verification

NOW-131 through NOW-140 implementation.
"""

# Base task type (abstract class)
from .base import (
    TaskType,
    TaskContext,
    EvidenceSpec,
    EvidenceCategory,
    ValidationResult,
    ValidationSeverity,
    BountyRecommendation as BaseBountyRecommendation,
    TimeEstimate,
)

# Core tiers (NOW-131)
from .tiers import (
    TaskTier,
    TierConfig,
    TierManager,
    TIER_CONFIGS,
    get_tier_for_bounty,
    get_tier_config,
)

# Recon tasks (NOW-132)
from .recon import (
    ReconTaskType,
    ReconTask,
    ReconTaskFactory,
    EvidenceRequirement,
    EvidenceType,
    BountySuggestion,
    Location,
)

# Trials - Experience testing (NOW-132)
from .trials import (
    TrialType,
    EvaluationCriteria,
    CriteriaConfig,
    ReimbursementConfig,
    TrialTask,
    TrialSubmission,
    TrialFactory,
    TRIAL_CRITERIA,
    create_trial,
    get_criteria_for_type,
)

# Last Mile delivery (NOW-133)
from .lastmile import (
    DeliveryType,
    DeliveryStatus,
    ProofType,
    Location as DeliveryLocation,
    DeliveryWindow,
    PackageInfo,
    DeliveryStop,
    DeliveryTask,
    LastMilePricing,
    LastMileFactory,
    DeliveryTracker,
    create_delivery,
    estimate_delivery_price,
)

# Execution Market Prime (NOW-134)
from .prime import (
    PrimeStatus,
    BackgroundCheckStatus,
    InsuranceType,
    SLALevel,
    BackgroundCheck,
    InsuranceCoverage,
    SLAConfig,
    SLA_CONFIGS,
    PrimeRequirements,
    PrimeMembership,
    SLAMetrics,
    PrimeManager,
    check_prime_eligibility,
    get_sla_config,
    get_prime_requirements,
)

# Gamified progression (NOW-135)
from .progression import (
    WorkerLevel,
    LevelRequirements,
    LevelPerks,
    LEVEL_REQUIREMENTS,
    LEVEL_PERKS,
    AchievementType,
    Achievement,
    ACHIEVEMENTS,
    XPEvent,
    XP_AWARDS,
    ProgressionManager,
    get_worker_level,
    calculate_bounty_with_level,
)

# Task bundles (NOW-136, NOW-137)
from .bundles import (
    BundleStatus,
    BundleType,
    GeoZone,
    BundleTask,
    BundleBonus,
    TaskBundle,
    BundleOptimizer,
    BundleFactory,
    create_bundle,
    calculate_bundle_bonus,
)

# Cascading tasks (NOW-138)
from .cascading import (
    TriggerType,
    CascadeStatus,
    TriggerCondition,
    TaskTemplate,
    CascadeRule,
    CascadeChain,
    CascadeEngine,
    CascadeTemplates,
    create_cascade_chain,
    get_template,
)

# Task insurance (NOW-139, NOW-140)
from .insurance import (
    InsuranceTier,
    ClaimType,
    ClaimStatus,
    InsuranceTierConfig,
    INSURANCE_TIERS,
    TaskInsurance,
    InsuranceClaim,
    InsuranceManager,
    get_insurance_fee,
    get_max_coverage,
    recommend_tier,
    get_tier_comparison,
)

# Pluggable task types
from .photo_verification import (
    PhotoVerificationTask,
    PhotoValidationConfig,
    PhotoEvidence,
)

from .delivery import (
    DeliveryTask as PluggableDeliveryTask,
    DeliveryValidationConfig,
    DeliveryEvidence,
    DeliveryLocation as PluggableDeliveryLocation,
)

from .survey import (
    SurveyTask,
    SurveyValidationConfig,
    SurveyEvidence,
    FormField,
    FieldType,
    create_price_survey,
    create_customer_feedback_survey,
)

from .mystery_shop import (
    MysteryShopTask,
    MysteryShopConfig,
    MysteryShopEvidence,
    EvaluationCriterion,
    EvaluationCategory,
    RatingScale,
    create_retail_mystery_shop,
    create_restaurant_mystery_shop,
)

from .price_check import (
    PriceCheckTask,
    PriceCheckConfig,
    PriceCheckEvidence,
    ProductSpec,
    PriceType,
    create_competitive_price_check,
    create_sale_verification_task,
)

# Task type registry
from .registry import (
    TaskTypeRegistry,
    TaskTypeInfo,
    get_registry,
    get_task_type,
    list_task_types,
    register_task_type,
    TASK_TYPES,
)

__all__ = [
    # Base task type
    "TaskType",
    "TaskContext",
    "EvidenceSpec",
    "EvidenceCategory",
    "ValidationResult",
    "ValidationSeverity",
    "BaseBountyRecommendation",
    "TimeEstimate",

    # Tiers (NOW-131)
    "TaskTier",
    "TierConfig",
    "TierManager",
    "TIER_CONFIGS",
    "get_tier_for_bounty",
    "get_tier_config",

    # Recon
    "ReconTaskType",
    "ReconTask",
    "ReconTaskFactory",
    "EvidenceRequirement",
    "EvidenceType",
    "BountySuggestion",
    "Location",

    # Trials (NOW-132)
    "TrialType",
    "EvaluationCriteria",
    "CriteriaConfig",
    "ReimbursementConfig",
    "TrialTask",
    "TrialSubmission",
    "TrialFactory",
    "TRIAL_CRITERIA",
    "create_trial",
    "get_criteria_for_type",

    # LastMile (NOW-133)
    "DeliveryType",
    "DeliveryStatus",
    "ProofType",
    "DeliveryLocation",
    "DeliveryWindow",
    "PackageInfo",
    "DeliveryStop",
    "DeliveryTask",
    "LastMilePricing",
    "LastMileFactory",
    "DeliveryTracker",
    "create_delivery",
    "estimate_delivery_price",

    # Prime (NOW-134)
    "PrimeStatus",
    "BackgroundCheckStatus",
    "InsuranceType",
    "SLALevel",
    "BackgroundCheck",
    "InsuranceCoverage",
    "SLAConfig",
    "SLA_CONFIGS",
    "PrimeRequirements",
    "PrimeMembership",
    "SLAMetrics",
    "PrimeManager",
    "check_prime_eligibility",
    "get_sla_config",
    "get_prime_requirements",

    # Progression (NOW-135)
    "WorkerLevel",
    "LevelRequirements",
    "LevelPerks",
    "LEVEL_REQUIREMENTS",
    "LEVEL_PERKS",
    "AchievementType",
    "Achievement",
    "ACHIEVEMENTS",
    "XPEvent",
    "XP_AWARDS",
    "ProgressionManager",
    "get_worker_level",
    "calculate_bounty_with_level",

    # Bundles (NOW-136, NOW-137)
    "BundleStatus",
    "BundleType",
    "GeoZone",
    "BundleTask",
    "BundleBonus",
    "TaskBundle",
    "BundleOptimizer",
    "BundleFactory",
    "create_bundle",
    "calculate_bundle_bonus",

    # Cascading (NOW-138)
    "TriggerType",
    "CascadeStatus",
    "TriggerCondition",
    "TaskTemplate",
    "CascadeRule",
    "CascadeChain",
    "CascadeEngine",
    "CascadeTemplates",
    "create_cascade_chain",
    "get_template",

    # Insurance (NOW-139, NOW-140)
    "InsuranceTier",
    "ClaimType",
    "ClaimStatus",
    "InsuranceTierConfig",
    "INSURANCE_TIERS",
    "TaskInsurance",
    "InsuranceClaim",
    "InsuranceManager",
    "get_insurance_fee",
    "get_max_coverage",
    "recommend_tier",
    "get_tier_comparison",

    # Photo Verification
    "PhotoVerificationTask",
    "PhotoValidationConfig",
    "PhotoEvidence",

    # Delivery (pluggable)
    "PluggableDeliveryTask",
    "DeliveryValidationConfig",
    "DeliveryEvidence",
    "PluggableDeliveryLocation",

    # Survey
    "SurveyTask",
    "SurveyValidationConfig",
    "SurveyEvidence",
    "FormField",
    "FieldType",
    "create_price_survey",
    "create_customer_feedback_survey",

    # Mystery Shop
    "MysteryShopTask",
    "MysteryShopConfig",
    "MysteryShopEvidence",
    "EvaluationCriterion",
    "EvaluationCategory",
    "RatingScale",
    "create_retail_mystery_shop",
    "create_restaurant_mystery_shop",

    # Price Check
    "PriceCheckTask",
    "PriceCheckConfig",
    "PriceCheckEvidence",
    "ProductSpec",
    "PriceType",
    "create_competitive_price_check",
    "create_sale_verification_task",

    # Registry
    "TaskTypeRegistry",
    "TaskTypeInfo",
    "get_registry",
    "get_task_type",
    "list_task_types",
    "register_task_type",
    "TASK_TYPES",
]
