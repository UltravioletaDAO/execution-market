"""Execution Market Plugin SDK — Python client for the EM REST API."""

from .client import EMClient
from .models import (
    Task,
    TaskList,
    TaskStatus,
    TaskCategory,
    EvidenceType,
    TargetExecutorType,
    Submission,
    SubmissionList,
    Application,
    ApplicationList,
    Executor,
    HealthResponse,
    PlatformConfig,
    PaymentEvent,
    PaymentTimeline,
    CreateTaskParams,
    SubmitEvidenceParams,
    ApproveParams,
    RejectParams,
)
from .exceptions import (
    EMError,
    EMAuthError,
    EMNotFoundError,
    EMValidationError,
    EMServerError,
)
from .fees import FeeBreakdown, calculate_fee, calculate_reverse_fee, get_fee_rate
from .networks import (
    NetworkInfo,
    TokenInfo,
    NETWORKS,
    get_network,
    get_enabled_networks,
    get_supported_tokens,
    is_valid_pair,
    get_chain_id,
    get_escrow_networks,
    DEFAULT_NETWORK,
    DEFAULT_TOKEN,
)

__version__ = "0.2.0"

__all__ = [
    # Client
    "EMClient",
    # Models
    "Task",
    "TaskList",
    "TaskStatus",
    "TaskCategory",
    "EvidenceType",
    "TargetExecutorType",
    "Submission",
    "SubmissionList",
    "Application",
    "ApplicationList",
    "Executor",
    "HealthResponse",
    "PlatformConfig",
    "PaymentEvent",
    "PaymentTimeline",
    # Request params
    "CreateTaskParams",
    "SubmitEvidenceParams",
    "ApproveParams",
    "RejectParams",
    # Exceptions
    "EMError",
    "EMAuthError",
    "EMNotFoundError",
    "EMValidationError",
    "EMServerError",
    # Fees
    "FeeBreakdown",
    "calculate_fee",
    "calculate_reverse_fee",
    "get_fee_rate",
    # Networks
    "NetworkInfo",
    "TokenInfo",
    "NETWORKS",
    "get_network",
    "get_enabled_networks",
    "get_supported_tokens",
    "is_valid_pair",
    "get_chain_id",
    "get_escrow_networks",
    "DEFAULT_NETWORK",
    "DEFAULT_TOKEN",
]
