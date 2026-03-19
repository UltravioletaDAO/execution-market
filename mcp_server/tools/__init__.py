"""
Execution Market MCP Server Tools

Modular tool implementations for the Execution Market MCP server.

Tools are organized by role:
- agent_tools: Enhanced tools for AI agents managing tasks at scale
- worker_tools: Tools for human workers executing tasks (NOW-011 to NOW-014)
- escrow_tools: Advanced Escrow payment tools (authorize, release, refund, charge, dispute)
"""

from .agent_tools import (
    # Registration function
    register_agent_tools,
    # Config
    AgentToolsConfig,
    # Input models
    AssignTaskInput,
    BatchCreateTasksInput,
    BatchTaskDefinition,
    GetTaskAnalyticsInput,
    # Enums
    WorkerEligibilityStatus,
    BatchOperationMode,
    AnalyticsTimeframe,
    TaskCategory,
    EvidenceType,
    ResponseFormat,
    # Data classes
    WorkerEligibility,
    BatchTaskResult,
    TaskAnalytics,
    # Helpers
    check_worker_eligibility,
    calculate_batch_escrow,
    format_analytics_markdown,
)

from .escrow_tools import (
    # Registration function
    register_escrow_tools,
    # Availability flag
    ADVANCED_ESCROW_AVAILABLE,
    # Input models
    EscrowRecommendInput,
    EscrowAuthorizeInput,
    EscrowReleaseInput,
    EscrowRefundInput,
    EscrowChargeInput,
    EscrowPartialReleaseInput,
    EscrowDisputeInput,
    EscrowStatusInput,
)

from .worker_tools import (
    # Registration function
    register_worker_tools,
    # Config
    WorkerToolsConfig,
    # Helpers
    validate_evidence_schema,
    EvidenceValidationError,
    # Status transitions
    VALID_TRANSITIONS,
    can_transition,
    # Standalone factory
    create_worker_tools_standalone,
)

from .reputation_tools import (
    # Registration function
    register_reputation_tools,
    # Availability flags
    ERC8004_AVAILABLE as REPUTATION_TOOLS_AVAILABLE,
)

from .core_tools import (
    # Registration function
    register_core_tools,
    # Config
    CoreToolsConfig,
)

__all__ = [
    # Agent Tools
    "register_agent_tools",
    "AgentToolsConfig",
    "AssignTaskInput",
    "BatchCreateTasksInput",
    "BatchTaskDefinition",
    "GetTaskAnalyticsInput",
    "WorkerEligibilityStatus",
    "BatchOperationMode",
    "AnalyticsTimeframe",
    "TaskCategory",
    "EvidenceType",
    "ResponseFormat",
    "WorkerEligibility",
    "BatchTaskResult",
    "TaskAnalytics",
    "check_worker_eligibility",
    "calculate_batch_escrow",
    "format_analytics_markdown",
    # Escrow Tools (Advanced Escrow via SDK)
    "register_escrow_tools",
    "ADVANCED_ESCROW_AVAILABLE",
    "EscrowRecommendInput",
    "EscrowAuthorizeInput",
    "EscrowReleaseInput",
    "EscrowRefundInput",
    "EscrowChargeInput",
    "EscrowPartialReleaseInput",
    "EscrowDisputeInput",
    "EscrowStatusInput",
    # Worker Tools (NOW-011 to NOW-014)
    "register_worker_tools",
    "WorkerToolsConfig",
    "validate_evidence_schema",
    "EvidenceValidationError",
    "VALID_TRANSITIONS",
    "can_transition",
    "create_worker_tools_standalone",
    # Reputation Tools (WS-4)
    "register_reputation_tools",
    "REPUTATION_TOOLS_AVAILABLE",
    # Core Tools (employer: publish, approve, cancel)
    "register_core_tools",
    "CoreToolsConfig",
]
