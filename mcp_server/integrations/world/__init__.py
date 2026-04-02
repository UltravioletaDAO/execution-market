"""
World AgentKit Integration — Human Verification via AgentBook

Uses the AgentBook contract on Base to verify that a wallet address
belongs to a World-verified human. This is a read-only on-chain lookup
using the same lightweight JSON-RPC pattern as ERC-8004 identity.py.

Contract: 0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4 (Base Mainnet)
Function: lookupHuman(address) -> uint256 humanId
"""

from .agentbook import lookup_human, WorldHumanResult, WorldHumanStatus

__all__ = [
    "lookup_human",
    "WorldHumanResult",
    "WorldHumanStatus",
]
