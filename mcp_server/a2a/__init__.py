"""
Execution Market A2A Protocol Integration

Agent-to-Agent communication following the A2A Protocol specification.
https://a2a-protocol.org/

Provides:
- Agent Card discovery (/.well-known/agent.json)
- JSON-RPC 2.0 endpoint for task operations (/a2a/v1)
- SSE streaming for real-time task updates (/a2a/v1/stream)

Three access paths to Execution Market:
  Agent → A2A (interop)  → EM  ← JSON-RPC, standard protocol
  Agent → MCP (tools)    → EM  ← Tool calling, framework integration
  Agent → REST (direct)  → EM  ← HTTP API, maximum control
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

from .models import (
    A2ATask,
    A2ATaskState,
    A2ATaskStatus,
    Message,
    Artifact,
    TextPart,
    FilePart,
    DataPart,
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    em_status_to_a2a,
)

from .task_manager import A2ATaskManager

from .jsonrpc_router import router as a2a_jsonrpc_router

__all__ = [
    # Agent Card
    "AgentCard",
    "AgentProvider",
    "AgentCapabilities",
    "AgentSkill",
    "AgentInterface",
    "SecurityScheme",
    "get_agent_card",
    "a2a_discovery_router",
    # A2A Models
    "A2ATask",
    "A2ATaskState",
    "A2ATaskStatus",
    "Message",
    "Artifact",
    "TextPart",
    "FilePart",
    "DataPart",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCError",
    "em_status_to_a2a",
    # Task Manager
    "A2ATaskManager",
    # Router
    "a2a_jsonrpc_router",
]
