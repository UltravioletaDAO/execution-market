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
    AgentReputation,
    AgentIdentity,
    EvidenceUploadInfo,
    EvidenceVerifyResult,
    Webhook,
    WebhookList,
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

# Wallet adapter (optional — requires uvd-x402-sdk[wallet]>=0.20.0)
try:
    from uvd_x402_sdk.wallet import WalletAdapter, EnvKeyAdapter, OWSWalletAdapter
except ImportError:
    pass

__version__ = "0.4.0"

__all__ = [
    # Client
    "EMClient",
    # Models — responses
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
    "AgentReputation",
    "AgentIdentity",
    "EvidenceUploadInfo",
    "EvidenceVerifyResult",
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
    # Wallet adapter (optional — requires uvd-x402-sdk[wallet])
    "WalletAdapter",
    "EnvKeyAdapter",
    "OWSWalletAdapter",
]
