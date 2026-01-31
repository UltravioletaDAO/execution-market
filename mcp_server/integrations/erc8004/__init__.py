"""
Chamba ERC-8004 Integration

On-chain identity and reputation for the Chamba platform.

Two approaches available:
1. Direct on-chain (register.py, reputation.py) - for full control
2. Via Facilitator (facilitator_client.py) - PRODUCTION RECOMMENDED

Facilitator: https://facilitator.ultravioletadao.xyz

Contracts (Ethereum Mainnet):
- Identity Registry: 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
- Reputation Registry: 0x8004BAa17C55a88189AE136b182e5fdA19dE9b63
"""

# Direct on-chain (for future full control)
from .register import ERC8004Registry
from .reputation import ReputationManager

# Via Facilitator (PRODUCTION - use this!)
from .facilitator_client import (
    # Client
    ERC8004FacilitatorClient,
    get_facilitator_client,
    # Types
    AgentIdentity,
    FeedbackResult,
    ReputationSummary,
    # Chamba functions
    get_chamba_reputation,
    get_chamba_identity,
    rate_worker,
    rate_agent,
    get_agent_info,
    get_agent_reputation,
    # Config
    CHAMBA_AGENT_ID,
    ERC8004_CONTRACTS,
    ERC8004_NETWORK,
    FACILITATOR_URL,
)

__all__ = [
    # Direct (future)
    'ERC8004Registry',
    'ReputationManager',
    # Facilitator (production)
    'ERC8004FacilitatorClient',
    'get_facilitator_client',
    'AgentIdentity',
    'FeedbackResult',
    'ReputationSummary',
    'get_chamba_reputation',
    'get_chamba_identity',
    'rate_worker',
    'rate_agent',
    'get_agent_info',
    'get_agent_reputation',
    'CHAMBA_AGENT_ID',
    'ERC8004_CONTRACTS',
    'ERC8004_NETWORK',
    'FACILITATOR_URL',
]
