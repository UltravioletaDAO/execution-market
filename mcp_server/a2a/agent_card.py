"""
A2A Agent Card for Chamba (NOW-083, NOW-084, NOW-085)

Implements the Agent2Agent Protocol specification for agent discovery.
https://a2a-protocol.org/latest/specification/

This module provides:
- AgentCard dataclass with all A2A fields
- Function to generate the card JSON
- FastAPI router for serving the card at /.well-known/agent.json
- Agent capabilities declaration for Chamba
"""

import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse


# ============== CONSTANTS ==============

# Protocol version - A2A 0.3 is the current version
A2A_PROTOCOL_VERSION = "0.3.0"

# Chamba version
CHAMBA_VERSION = "0.1.0"

# Base URL - configurable via environment
DEFAULT_BASE_URL = "https://api.chamba.ultravioletadao.xyz"


# ============== ENUMS ==============


class TransportType(str, Enum):
    """Supported transport protocols for A2A communication."""
    JSONRPC = "JSONRPC"
    GRPC = "GRPC"
    HTTP_JSON = "HTTP+JSON"
    WEBSOCKET = "WEBSOCKET"
    STREAMABLE_HTTP = "STREAMABLE_HTTP"


class SecurityType(str, Enum):
    """Security scheme types per A2A spec."""
    OAUTH2 = "oauth2"
    OPENID_CONNECT = "openIdConnect"
    API_KEY = "apiKey"
    HTTP = "http"


class InputOutputMode(str, Enum):
    """Supported input/output MIME types."""
    JSON = "application/json"
    TEXT_PLAIN = "text/plain"
    FORM_URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"


# ============== DATA CLASSES ==============


@dataclass
class AgentProvider:
    """
    Information about the organization providing the agent.

    Attributes:
        organization: Legal name of the provider organization
        url: Website URL of the provider
        contact_email: Optional contact email for support
    """
    organization: str
    url: str
    contact_email: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {
            "organization": self.organization,
            "url": self.url,
        }
        if self.contact_email:
            result["contactEmail"] = self.contact_email
        return result


@dataclass
class AgentCapabilities:
    """
    Declares supported A2A features.

    Attributes:
        streaming: Whether the agent supports streaming responses (SSE)
        push_notifications: Whether the agent can send push notifications
        state_transition_history: Whether task state history is available
        supports_authenticated_extended_card: Whether extended card is available after auth
    """
    streaming: bool = False
    push_notifications: bool = False
    state_transition_history: bool = True
    supports_authenticated_extended_card: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to camelCase dictionary."""
        return {
            "streaming": self.streaming,
            "pushNotifications": self.push_notifications,
            "stateTransitionHistory": self.state_transition_history,
            "supportsAuthenticatedExtendedCard": self.supports_authenticated_extended_card,
        }


@dataclass
class AgentSkill:
    """
    Describes a specific capability/operation the agent can perform.

    Attributes:
        id: Unique identifier for the skill (used for routing)
        name: Human-readable skill name
        description: Detailed description of what the skill does
        tags: List of tags for categorization and discovery
        examples: Example prompts/inputs that trigger this skill
        input_modes: Supported input MIME types
        output_modes: Supported output MIME types
    """
    id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    input_modes: List[str] = field(default_factory=lambda: ["application/json", "text/plain"])
    output_modes: List[str] = field(default_factory=lambda: ["application/json", "text/plain"])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to camelCase dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "examples": self.examples,
            "inputModes": self.input_modes,
            "outputModes": self.output_modes,
        }


@dataclass
class AgentInterface:
    """
    Describes an endpoint/transport binding for A2A communication.

    Attributes:
        url: Full URL for this interface
        transport: Transport protocol type
    """
    url: str
    transport: TransportType

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "transport": self.transport.value,
        }


@dataclass
class SecurityScheme:
    """
    Describes an authentication method.

    Attributes:
        name: Scheme identifier (e.g., "bearer", "oauth2")
        type: Security type (oauth2, openIdConnect, apiKey, http)
        scheme: HTTP auth scheme if type is "http" (e.g., "bearer")
        bearer_format: Token format if using bearer (e.g., "JWT")
        description: Human-readable description
        openid_connect_url: URL for OpenID Connect discovery
        flows: OAuth2 flows configuration
        in_header: Header name for API key
        in_query: Query parameter name for API key
    """
    name: str
    type: SecurityType
    scheme: Optional[str] = None
    bearer_format: Optional[str] = None
    description: Optional[str] = None
    openid_connect_url: Optional[str] = None
    flows: Optional[Dict[str, Any]] = None
    in_header: Optional[str] = None
    in_query: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result: Dict[str, Any] = {"type": self.type.value}

        if self.scheme:
            result["scheme"] = self.scheme
        if self.bearer_format:
            result["bearerFormat"] = self.bearer_format
        if self.description:
            result["description"] = self.description
        if self.openid_connect_url:
            result["openIdConnectUrl"] = self.openid_connect_url
        if self.flows:
            result["flows"] = self.flows
        if self.in_header:
            result["in"] = "header"
            result["name"] = self.in_header
        if self.in_query:
            result["in"] = "query"
            result["name"] = self.in_query

        return result


@dataclass
class AgentCard:
    """
    Complete A2A Agent Card per specification.

    The Agent Card is the primary discovery document that describes
    an agent's capabilities, skills, and how to communicate with it.

    Attributes:
        name: Human-readable agent name
        description: Short description of agent purpose
        url: Primary endpoint URL
        version: Agent version string
        protocol_version: A2A protocol version supported
        provider: Organization information
        capabilities: Supported A2A features
        skills: List of available operations
        additional_interfaces: Alternative endpoints/transports
        security_schemes: Authentication methods
        security: Required security for operations
        default_input_modes: Default accepted input types
        default_output_modes: Default output types
        preferred_transport: Preferred communication protocol
    """
    name: str
    description: str
    url: str
    version: str = CHAMBA_VERSION
    protocol_version: str = A2A_PROTOCOL_VERSION
    provider: Optional[AgentProvider] = None
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    skills: List[AgentSkill] = field(default_factory=list)
    additional_interfaces: List[AgentInterface] = field(default_factory=list)
    security_schemes: Dict[str, SecurityScheme] = field(default_factory=dict)
    security: List[Dict[str, List[str]]] = field(default_factory=list)
    default_input_modes: List[str] = field(default_factory=lambda: ["application/json", "text/plain"])
    default_output_modes: List[str] = field(default_factory=lambda: ["application/json", "text/plain"])
    preferred_transport: TransportType = TransportType.JSONRPC

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to A2A-compliant JSON dictionary.

        Uses camelCase keys per A2A specification.
        """
        result: Dict[str, Any] = {
            "protocolVersion": self.protocol_version,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "preferredTransport": self.preferred_transport.value,
            "capabilities": self.capabilities.to_dict(),
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
        }

        if self.provider:
            result["provider"] = self.provider.to_dict()

        if self.skills:
            result["skills"] = [s.to_dict() for s in self.skills]

        if self.additional_interfaces:
            result["additionalInterfaces"] = [i.to_dict() for i in self.additional_interfaces]

        if self.security_schemes:
            result["securitySchemes"] = {
                name: scheme.to_dict()
                for name, scheme in self.security_schemes.items()
            }

        if self.security:
            result["security"] = self.security

        return result

    def to_json(self) -> str:
        """Serialize to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2)


# ============== CHAMBA SKILLS DEFINITION ==============


def get_chamba_skills() -> List[AgentSkill]:
    """
    Define Chamba's available skills for A2A discovery.

    These map to the MCP tools implemented in server.py.
    """
    return [
        AgentSkill(
            id="publish-task",
            name="Publish Task for Human Execution",
            description=(
                "Create a new task that requires human execution. "
                "Specify task details, bounty, deadline, and evidence requirements. "
                "Human workers will browse, accept, and complete the task with verified evidence."
            ),
            tags=["task", "human-execution", "create", "bounty", "work"],
            examples=[
                "I need someone to verify if the store at 123 Main St is open",
                "Get a photo of the queue length at the DMV on Oak Avenue",
                "Have someone sign this document in person at the notary office",
                "Send someone to pick up a package from the post office",
            ],
            input_modes=["application/json", "text/plain"],
            output_modes=["application/json", "text/plain"],
        ),
        AgentSkill(
            id="manage-tasks",
            name="Manage Published Tasks",
            description=(
                "View, filter, and manage your published tasks. "
                "Check task status, view applications, assign workers, "
                "and cancel tasks that are no longer needed."
            ),
            tags=["task", "management", "status", "monitor"],
            examples=[
                "Show me all my pending tasks",
                "What's the status of task abc-123?",
                "Cancel my task for the store verification",
                "List all completed tasks from this week",
            ],
            input_modes=["application/json", "text/plain"],
            output_modes=["application/json", "text/plain"],
        ),
        AgentSkill(
            id="review-submissions",
            name="Review and Approve Submissions",
            description=(
                "Review evidence submitted by human workers. "
                "Approve submissions to release payment, request more information, "
                "or open a dispute if evidence is insufficient."
            ),
            tags=["submission", "review", "approval", "evidence", "payment"],
            examples=[
                "Show me the submission for task xyz-789",
                "Approve the submission with evidence photos",
                "Request more information about the receipt submission",
                "Dispute the submission due to invalid GPS coordinates",
            ],
            input_modes=["application/json", "text/plain"],
            output_modes=["application/json", "text/plain"],
        ),
        AgentSkill(
            id="worker-management",
            name="Worker Assignment and Management",
            description=(
                "Assign tasks to specific workers, view worker statistics, "
                "check reputation scores, and manage the workforce for your tasks."
            ),
            tags=["worker", "assignment", "reputation", "management"],
            examples=[
                "Assign task abc-123 to worker with highest reputation",
                "Show me the stats for worker xyz",
                "List workers who have completed similar tasks",
            ],
            input_modes=["application/json", "text/plain"],
            output_modes=["application/json", "text/plain"],
        ),
        AgentSkill(
            id="batch-operations",
            name="Batch Task Operations",
            description=(
                "Create multiple tasks in a single operation. "
                "Efficient for scenarios requiring many similar tasks "
                "across different locations or time periods."
            ),
            tags=["batch", "bulk", "efficiency", "multiple-tasks"],
            examples=[
                "Create 10 store verification tasks across these locations",
                "Set up daily photo capture tasks for the next week",
                "Batch create price check tasks for 20 stores",
            ],
            input_modes=["application/json"],
            output_modes=["application/json", "text/plain"],
        ),
        AgentSkill(
            id="analytics",
            name="Task Analytics and Reporting",
            description=(
                "Get analytics on your task history including completion rates, "
                "average times, bounty statistics, and worker performance metrics."
            ),
            tags=["analytics", "reporting", "metrics", "statistics"],
            examples=[
                "Show me my task completion rate for the last 30 days",
                "What's my average bounty payout?",
                "Which workers have the best performance?",
                "Give me a summary of all completed tasks this month",
            ],
            input_modes=["application/json", "text/plain"],
            output_modes=["application/json", "text/plain"],
        ),
        AgentSkill(
            id="payments",
            name="Payment Management",
            description=(
                "Manage payments including escrow deposits, payment releases, "
                "refunds, and viewing payment history. Supports USDC via x402 protocol."
            ),
            tags=["payment", "escrow", "usdc", "x402", "refund"],
            examples=[
                "What's the escrow balance for task abc-123?",
                "Release payment for approved submission",
                "Process refund for cancelled task",
            ],
            input_modes=["application/json"],
            output_modes=["application/json", "text/plain"],
        ),
    ]


# ============== AGENT CARD GENERATION ==============


def get_agent_card(base_url: Optional[str] = None) -> AgentCard:
    """
    Generate the complete Chamba Agent Card.

    Args:
        base_url: Override the default base URL (useful for testing)

    Returns:
        AgentCard configured for Chamba
    """
    url = base_url or os.environ.get("CHAMBA_BASE_URL", DEFAULT_BASE_URL)

    return AgentCard(
        name="Chamba",
        description=(
            "Human Execution Layer for AI Agents. Chamba enables AI agents to delegate "
            "real-world tasks to human workers, with verified evidence submission, "
            "reputation scoring, and instant crypto payments via x402 protocol."
        ),
        url=f"{url}/a2a/v1",
        version=CHAMBA_VERSION,
        protocol_version=A2A_PROTOCOL_VERSION,
        provider=AgentProvider(
            organization="Ultravioleta DAO",
            url="https://ultravioletadao.xyz",
            contact_email="ultravioletadao@gmail.com",
        ),
        capabilities=AgentCapabilities(
            streaming=True,  # SSE for real-time updates
            push_notifications=True,  # Webhooks for task events
            state_transition_history=True,  # Full task state history
            supports_authenticated_extended_card=True,  # Extended info after auth
        ),
        skills=get_chamba_skills(),
        additional_interfaces=[
            AgentInterface(
                url=f"{url}/a2a/v1",
                transport=TransportType.JSONRPC,
            ),
            AgentInterface(
                url=f"{url}/mcp",
                transport=TransportType.STREAMABLE_HTTP,
            ),
            AgentInterface(
                url=f"{url}/api/v1",
                transport=TransportType.HTTP_JSON,
            ),
        ],
        security_schemes={
            "bearer": SecurityScheme(
                name="bearer",
                type=SecurityType.HTTP,
                scheme="bearer",
                bearer_format="JWT",
                description="JWT token issued by Chamba auth service",
            ),
            "apiKey": SecurityScheme(
                name="apiKey",
                type=SecurityType.API_KEY,
                in_header="X-API-Key",
                description="API key for agent authentication",
            ),
            "erc8004": SecurityScheme(
                name="erc8004",
                type=SecurityType.HTTP,
                scheme="bearer",
                bearer_format="ERC-8004",
                description="ERC-8004 Agent Registry identity token",
            ),
        },
        security=[
            {"bearer": []},
            {"apiKey": []},
            {"erc8004": []},
        ],
        default_input_modes=["application/json", "text/plain"],
        default_output_modes=["application/json", "text/plain"],
        preferred_transport=TransportType.JSONRPC,
    )


# ============== FASTAPI ROUTER ==============


router = APIRouter(tags=["A2A Discovery"])


@router.get(
    "/.well-known/agent.json",
    response_class=JSONResponse,
    summary="A2A Agent Card",
    description="Discover Chamba's capabilities via the A2A Agent Card",
    responses={
        200: {
            "description": "Agent Card JSON",
            "content": {
                "application/json": {
                    "example": {
                        "protocolVersion": "0.3.0",
                        "name": "Chamba",
                        "description": "Human Execution Layer for AI Agents",
                        "url": "https://api.chamba.ultravioletadao.xyz/a2a/v1",
                    }
                }
            }
        }
    }
)
async def get_agent_card_endpoint(request: Request) -> JSONResponse:
    """
    Serve the A2A Agent Card at the well-known discovery URL.

    This endpoint allows other agents to discover Chamba's capabilities,
    available skills, authentication requirements, and how to communicate.

    Returns:
        JSONResponse with the complete Agent Card
    """
    # Build base URL from request if not configured
    base_url = os.environ.get("CHAMBA_BASE_URL")
    if not base_url:
        base_url = f"{request.url.scheme}://{request.url.netloc}"

    card = get_agent_card(base_url)

    return JSONResponse(
        content=card.to_dict(),
        headers={
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "X-A2A-Protocol-Version": A2A_PROTOCOL_VERSION,
        }
    )


@router.get(
    "/v1/card",
    response_class=JSONResponse,
    summary="A2A Agent Card (REST)",
    description="Alternative REST endpoint for Agent Card discovery",
)
async def get_agent_card_rest(request: Request) -> JSONResponse:
    """
    REST API endpoint for Agent Card.

    Alternative to /.well-known/agent.json per A2A spec.
    """
    return await get_agent_card_endpoint(request)


@router.get(
    "/discovery/agents",
    response_class=JSONResponse,
    summary="Agent Discovery",
    description="Discover available agents (returns self for now)",
)
async def discover_agents(request: Request) -> JSONResponse:
    """
    Agent discovery endpoint (NOW-084).

    Returns a list of discoverable agents. Currently returns only Chamba,
    but could be extended to return other ecosystem agents.

    Returns:
        JSONResponse with list of discoverable agent cards
    """
    base_url = os.environ.get("CHAMBA_BASE_URL")
    if not base_url:
        base_url = f"{request.url.scheme}://{request.url.netloc}"

    card = get_agent_card(base_url)

    return JSONResponse(
        content={
            "agents": [card.to_dict()],
            "total": 1,
            "discoveredAt": datetime.now(timezone.utc).isoformat(),
        },
        headers={
            "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
        }
    )


# ============== CLI FOR TESTING ==============


if __name__ == "__main__":
    import json

    card = get_agent_card("https://api.chamba.ultravioletadao.xyz")
    print(json.dumps(card.to_dict(), indent=2))
