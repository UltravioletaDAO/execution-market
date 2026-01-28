"""
Chamba MCP Server Tools

Modular tool implementations for the Chamba MCP server.

Tools are organized by role:
- agent_tools: Enhanced tools for AI agents managing tasks at scale
- worker_tools: Tools for human workers executing tasks (NOW-011 to NOW-014)
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
    # Worker Tools (NOW-011 to NOW-014)
    "register_worker_tools",
    "WorkerToolsConfig",
    "validate_evidence_schema",
    "EvidenceValidationError",
    "VALID_TRANSITIONS",
    "can_transition",
    "create_worker_tools_standalone",
]
