"""
Execution Market Seals & Credentials Module (NOW-183 to NOW-187)

On-chain verifiable credentials for worker capabilities.

Seals are discrete achievements that:
- Verify worker abilities (SKILL seals)
- Track work milestones (WORK seals)
- Recognize behavioral patterns (BEHAVIOR seals)

Components:
- types: Seal type definitions and requirements
- registry: On-chain seal storage interface
- issuance: Seal issuance logic and eligibility
- verification: Seal verification service
- display: UI formatting for profiles and cards

Usage:
    >>> from mcp_server.seals import (
    ...     SealRegistry,
    ...     SealIssuanceService,
    ...     SealVerificationService,
    ...     SealDisplayFormatter,
    ...     WorkerStats,
    ... )
    >>>
    >>> # Initialize services
    >>> registry = SealRegistry(network="base-sepolia")
    >>> issuance = SealIssuanceService(registry)
    >>> verification = SealVerificationService(registry)
    >>> display = SealDisplayFormatter()
    >>>
    >>> # Check and issue automatic seals
    >>> stats = WorkerStats(
    ...     wallet_address="0x1234...",
    ...     total_tasks_completed=100,
    ...     average_rating=92.0
    ... )
    >>> results = await issuance.check_and_issue_automatic(stats)
    >>>
    >>> # Verify seals for task eligibility
    >>> from mcp_server.seals import TaskSealRequirement
    >>> requirements = TaskSealRequirement(
    ...     required_seals=["delivery_certified"],
    ...     preferred_seals=["tasks_100_completed"],
    ...     any_of_seals=[]
    ... )
    >>> eligibility = await verification.check_task_eligibility(
    ...     "0x1234...", requirements
    ... )
    >>>
    >>> # Format for display
    >>> bundle = await registry.get_seal_bundle("0x1234...")
    >>> profile = display.format_profile(bundle)
"""

# Type definitions
from .types import (
    # Enums
    SealCategory,
    SealStatus,
    VerificationMethod,
    SkillSealType,
    WorkSealType,
    BehaviorSealType,
    # Dataclasses
    Seal,
    SealBundle,
    SealRequirement,
    # Functions
    get_requirement,
    get_requirements_by_category,
    get_automatic_seals,
    # Constants
    SEAL_REQUIREMENTS,
)

# Registry
from .registry import (
    SealRegistry,
    MockSealRegistry,
    get_seal_type_id,
    get_seal_type_from_id,
    SEAL_TYPE_IDS,
)

# Issuance
from .issuance import (
    SealIssuanceService,
    WorkerStats,
    EligibilityResult,
    IssuanceResult,
)

# Verification
from .verification import (
    SealVerificationService,
    VerificationContext,
    SealVerificationResult,
    TaskSealRequirement,
    TaskEligibilityResult,
)

# Display
from .display import (
    SealDisplayFormatter,
    DisplayConfig,
    format_seals_for_profile,
    format_seals_for_card,
    get_seal_display_name,
)

__all__ = [
    # Types
    "SealCategory",
    "SealStatus",
    "VerificationMethod",
    "SkillSealType",
    "WorkSealType",
    "BehaviorSealType",
    "Seal",
    "SealBundle",
    "SealRequirement",
    "get_requirement",
    "get_requirements_by_category",
    "get_automatic_seals",
    "SEAL_REQUIREMENTS",
    # Registry
    "SealRegistry",
    "MockSealRegistry",
    "get_seal_type_id",
    "get_seal_type_from_id",
    "SEAL_TYPE_IDS",
    # Issuance
    "SealIssuanceService",
    "WorkerStats",
    "EligibilityResult",
    "IssuanceResult",
    # Verification
    "SealVerificationService",
    "VerificationContext",
    "SealVerificationResult",
    "TaskSealRequirement",
    "TaskEligibilityResult",
    # Display
    "SealDisplayFormatter",
    "DisplayConfig",
    "format_seals_for_profile",
    "format_seals_for_card",
    "get_seal_display_name",
]

__version__ = "0.1.0"
