"""
Execution Market A2A Protocol Integration

Agent-to-Agent communication following the A2A Protocol specification.
https://a2a-protocol.org/
"""

from .agent_card import (
    AgentCard,
    AgentProvider,
    AgentCapabilities,
    AgentSkill,
    AgentInterface,
    SecurityScheme,
    get_agent_card,
    router as a2a_discovery_router,
)

from .jsonrpc_router import router as a2a_jsonrpc_router

# Combined router: merge discovery + JSON-RPC into single export
from fastapi import APIRouter

a2a_router = APIRouter()
a2a_router.include_router(a2a_discovery_router)
a2a_router.include_router(a2a_jsonrpc_router)

__all__ = [
    "AgentCard",
    "AgentProvider",
    "AgentCapabilities",
    "AgentSkill",
    "AgentInterface",
    "SecurityScheme",
    "get_agent_card",
    "a2a_router",
    "a2a_discovery_router",
    "a2a_jsonrpc_router",
]
