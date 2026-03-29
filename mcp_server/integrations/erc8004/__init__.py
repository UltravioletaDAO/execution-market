"""
Execution Market ERC-8004 Integration

On-chain identity and reputation for the Execution Market platform.

Two approaches available:
1. Direct on-chain (register.py, reputation.py) - for full control
2. Via Facilitator (facilitator_client.py) - PRODUCTION RECOMMENDED

Facilitator: https://facilitator.ultravioletadao.xyz

Supported networks (14): All use CREATE2-deployed contracts at deterministic addresses.
  Mainnets: ethereum, base-mainnet, polygon, arbitrum, celo, bsc, monad, avalanche
  Testnets: ethereum-sepolia, base-sepolia, polygon-amoy, arbitrum-sepolia, celo-sepolia, avalanche-fuji
"""

# Direct on-chain (for future full control)
from .register import ERC8004Registry
from .reputation import ReputationManager

# Via Facilitator (PRODUCTION - use this!)
from .facilitator_client import (
    # Backward-compatible shim
    ERC8004FacilitatorClient,
    get_facilitator_client,
    # Types
    AgentIdentity,
    FeedbackResult,
    ReputationSummary,
    # SDK-backed module-level functions (preferred)
    get_identity,
    register_agent,
    get_reputation,
    submit_feedback,
    revoke_feedback,
    respond_to_feedback,
    get_identity_metadata,
    get_total_supply,
    # EM functions
    get_em_reputation,
    get_em_identity,
    rate_worker,
    rate_agent,
    get_agent_info,
    get_agent_reputation,
    # Config
    EM_AGENT_ID,
    ERC8004_CONTRACTS,
    ERC8004_NETWORK,
    ERC8004_SUPPORTED_NETWORKS,
    FACILITATOR_URL,
)

# Direct on-chain reputation (bypasses Facilitator)
from .direct_reputation import give_feedback_direct

# Identity verification (non-blocking, always fresh) & worker registration
from .identity import (
    verify_agent_identity,
    # Worker identity check & registration
    check_worker_identity,
    register_worker_gasless,
    build_worker_registration_tx,
    confirm_worker_registration,
    update_executor_identity,
    # Types
    WorkerIdentityStatus,
    WorkerIdentityResult,
    RegistrationTxData,
    # Constants
    IDENTITY_REGISTRY_MAINNET,
    IDENTITY_REGISTRY_TESTNET,
)

__all__ = [
    # Direct (future)
    "ERC8004Registry",
    "ReputationManager",
    # Facilitator (production)
    "ERC8004FacilitatorClient",
    "get_facilitator_client",
    "AgentIdentity",
    "FeedbackResult",
    "ReputationSummary",
    "get_identity",
    "register_agent",
    "get_reputation",
    "submit_feedback",
    "revoke_feedback",
    "respond_to_feedback",
    "get_identity_metadata",
    "get_total_supply",
    "get_em_reputation",
    "get_em_identity",
    "rate_worker",
    "rate_agent",
    "get_agent_info",
    "get_agent_reputation",
    "EM_AGENT_ID",
    "ERC8004_CONTRACTS",
    "ERC8004_NETWORK",
    "ERC8004_SUPPORTED_NETWORKS",
    "FACILITATOR_URL",
    # Direct reputation
    "give_feedback_direct",
    # Identity verification
    "verify_agent_identity",
    # Worker identity
    "check_worker_identity",
    "register_worker_gasless",
    "build_worker_registration_tx",
    "confirm_worker_registration",
    "update_executor_identity",
    "WorkerIdentityStatus",
    "WorkerIdentityResult",
    "RegistrationTxData",
    "IDENTITY_REGISTRY_MAINNET",
    "IDENTITY_REGISTRY_TESTNET",
]
