"""
Execution Market MCP Server - FastAPI Wrapper with Streamable HTTP Transport

Provides HTTP endpoints for health checks and MCP server initialization.
MCP server exposed via Streamable HTTP transport at /mcp endpoint.
WebSocket support for real-time communication.
A2A Protocol support for agent discovery and interoperability.
REST API for programmatic access.

MCP Transport: Streamable HTTP (2025-03-26 spec)
- Single endpoint at /mcp for all MCP operations
- Supports SSE streaming for long-running operations
- Session management via Mcp-Session-Id header
- Compatible with remote MCP clients
"""

import os
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, field_validator
from pathlib import Path

import supabase_client as db
from jobs.task_expiration import run_task_expiration_loop
from jobs.auto_payment import run_auto_payment_loop

# Import MCP server for Streamable HTTP mounting
from server import mcp as mcp_server
from websocket import ws_router, ws_manager
from a2a import a2a_router
from api import api_router, add_api_middleware
from api import reputation_router, escrow_router
from api.admin import router as admin_router
from health import router as health_router

# x402 SDK Integration (NOW-202)
try:
    from integrations.x402.sdk_client import (
        EMX402SDK,
        setup_x402_for_app,
        check_sdk_available,
        get_sdk_info,
        FACILITATOR_URL,
    )

    X402_SDK_AVAILABLE = check_sdk_available()
except ImportError:
    X402_SDK_AVAILABLE = False
    EMX402SDK = None
    setup_x402_for_app = None
    FACILITATOR_URL = None

# ERC-8004 Integration (Base-first via facilitator)
try:
    from integrations.erc8004 import (
        get_facilitator_client,
        EM_AGENT_ID,
        ERC8004_NETWORK,
        FACILITATOR_URL as ERC8004_FACILITATOR_URL,
    )

    ERC8004_AVAILABLE = True
except ImportError:
    ERC8004_AVAILABLE = False
    EM_AGENT_ID = 469
    ERC8004_NETWORK = "base"
    ERC8004_FACILITATOR_URL = "https://facilitator.ultravioletadao.xyz"

logger = logging.getLogger(__name__)

# Get Streamable HTTP configuration from environment
MCP_STATELESS_HTTP = os.environ.get("MCP_STATELESS_HTTP", "false").lower() == "true"
MCP_JSON_RESPONSE = os.environ.get("MCP_JSON_RESPONSE", "true").lower() == "true"

# Create MCP Streamable HTTP app
# The app will be mounted at /mcp, exposing the MCP endpoint there
try:
    mcp_http_app = mcp_server.streamable_http_app()
    MCP_HTTP_AVAILABLE = True
    logger.info("MCP Streamable HTTP app created successfully")
except Exception as e:
    logger.warning(f"Failed to create MCP HTTP app: {e}")
    mcp_http_app = None
    MCP_HTTP_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Manages MCP session manager, background jobs, and other async resources.
    Required for Streamable HTTP transport to work correctly.
    """
    logger.info("Starting Execution Market MCP Server with Streamable HTTP transport")

    # Start background jobs
    expiration_task = asyncio.create_task(run_task_expiration_loop())
    logger.info("Task expiration background job scheduled")

    auto_payment_task = asyncio.create_task(run_auto_payment_loop())
    logger.info("Auto-payment background job scheduled")

    # Initialize MCP session manager
    # The session manager must be running for Streamable HTTP to work
    if MCP_HTTP_AVAILABLE:
        try:
            # Get the session manager after app is created
            session_manager = mcp_server.session_manager
            logger.info("Initializing MCP session manager...")

            # Run the session manager as async context manager
            async with session_manager.run():
                logger.info("MCP session manager started successfully")
                yield
                logger.info("Shutting down MCP session manager...")
        except Exception as e:
            logger.error(f"Failed to start MCP session manager: {e}")
            yield
    else:
        yield

    # Cancel background jobs on shutdown
    expiration_task.cancel()
    auto_payment_task.cancel()
    try:
        await expiration_task
    except asyncio.CancelledError:
        pass
    try:
        await auto_payment_task
    except asyncio.CancelledError:
        pass
    logger.info("Background jobs stopped")

    logger.info("Shutting down Execution Market MCP Server")


# OpenAPI Tags for documentation organization (NOW-206)
tags_metadata = [
    {
        "name": "Health",
        "description": "Health checks and server status endpoints",
    },
    {
        "name": "Tasks",
        "description": "Task management for agents and workers",
    },
    {
        "name": "Workers",
        "description": "Worker (executor) registration and management",
    },
    {
        "name": "Submissions",
        "description": "Evidence submissions from workers",
    },
    {
        "name": "Payments",
        "description": "x402 payment operations and configuration",
    },
    {
        "name": "Escrow",
        "description": "x402r escrow management on Base Mainnet. Release payments to workers, refund agents.",
    },
    {
        "name": "Reputation",
        "description": "ERC-8004 reputation and identity via facilitator (Base-first configuration). Bidirectional feedback between agents and workers.",
    },
    {
        "name": "A2A",
        "description": "Agent-to-Agent protocol endpoints",
    },
    {
        "name": "WebSocket",
        "description": "Real-time WebSocket connections",
    },
    {
        "name": "Admin",
        "description": "Platform administration and configuration (requires admin key)",
    },
]

# Initialize FastAPI app with enhanced metadata (NOW-206)
# Include lifespan for MCP Streamable HTTP session management
app = FastAPI(
    title="Execution Market API",
    lifespan=lifespan,
    description="""
## Human Execution Layer for AI Agents

Execution Market connects AI agents with human workers for physical-world tasks.

### Features
- **x402 Payments**: Gasless stablecoin payments via facilitator
- **A2A Protocol**: Agent-to-Agent communication (v0.3.0)
- **MCP Tools**: Model Context Protocol integration
- **Real-time Updates**: WebSocket notifications

### Authentication
- API Key via `X-API-Key` header
- Bearer token via `Authorization` header
- ERC-8004 identity tokens (coming soon)

### Payment Networks
Supports 19 mainnets including Ethereum, Base, Polygon, Optimism, Arbitrum, Avalanche.

### Links
- [Dashboard](https://execution.market)
- [Documentation](https://docs.execution.market)
- [GitHub](https://github.com/ultravioleta-dao/execution-market)
    """,
    version="1.0.0",
    contact={
        "name": "Ultravioleta DAO",
        "url": "https://ultravioletadao.xyz",
        "email": "ultravioletadao@gmail.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add API middleware (rate limiting, logging, error handling)
add_api_middleware(app)

# Initialize x402 SDK (NOW-202)
x402_sdk: Optional[EMX402SDK] = None
if X402_SDK_AVAILABLE and setup_x402_for_app:
    try:
        treasury_address = os.environ.get("EM_TREASURY_ADDRESS")
        network = os.environ.get("X402_NETWORK", "base")
        x402_sdk = setup_x402_for_app(
            app,
            recipient_address=treasury_address,
            network=network,
        )
        logger.info(
            "x402 SDK initialized: facilitator=%s, network=%s",
            FACILITATOR_URL,
            network,
        )
    except Exception as e:
        logger.warning("Failed to initialize x402 SDK: %s", e)
else:
    logger.info("x402 SDK not available, payments will be simulated")

# Include WebSocket router
app.include_router(ws_router)

# Include A2A discovery router
app.include_router(a2a_router)

# Include REST API router
app.include_router(api_router)

# Include comprehensive health router (from health/ module)
# Provides /health/ready, /health/live, /health/detailed, /health/metrics
app.include_router(health_router)

# Include Admin router for platform management
# Provides /api/v1/admin/config, /api/v1/admin/stats
app.include_router(admin_router)

# Include ERC-8004 Reputation router (Base-first)
# Provides /api/v1/reputation/* for on-chain identity and feedback
app.include_router(reputation_router)

# Include x402r Escrow router (Base Mainnet)
# Provides /api/v1/escrow/* for payment management
app.include_router(escrow_router)

# CORS configuration with MCP headers support
# MCP Streamable HTTP requires specific headers for session management
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",  # MCP Inspector
        "http://localhost:6274",  # Claude Desktop MCP Inspector
        "https://execution.market",
        "https://app.execution.market",
        "https://admin.execution.market",
        "https://inspector.modelcontextprotocol.io",  # Official MCP Inspector
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Admin-Key",
        "X-Admin-Actor",
        "X-Device-ID",
        "X-Request-ID",
        "X-Payment",
        "Accept",
        "Origin",
        "mcp-protocol-version",
        "mcp-session-id",
    ],
    expose_headers=[
        "mcp-session-id",  # CRITICAL: Required for MCP session management
        "mcp-protocol-version",
    ],
)

# Mount MCP Streamable HTTP app at /mcp
# Note: Due to Starlette routing, the canonical URL is /mcp/ (with trailing slash)
# Requests to /mcp will redirect to /mcp/
if MCP_HTTP_AVAILABLE and mcp_http_app:
    app.mount("/mcp", mcp_http_app)
    logger.info("MCP Streamable HTTP mounted at /mcp/")
else:
    logger.warning("MCP Streamable HTTP not available - stdio transport only")


# Models
class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    environment: str
    services: Dict[str, str]


class ExecutorRegistration(BaseModel):
    wallet_address: str
    display_name: str | None = None

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        import re

        if not re.match(r"^0x[0-9a-fA-F]{40}$", v):
            raise ValueError("Invalid Ethereum wallet address")
        return v


class TaskApplication(BaseModel):
    task_id: str
    executor_id: str
    message: str | None = None


class WorkSubmission(BaseModel):
    task_id: str
    executor_id: str
    evidence: Dict[str, Any]


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers and monitoring."""

    # Check Supabase connection
    supabase_status = "healthy"
    try:
        client = db.get_client()
        # Simple query to verify connection
        client.table("tasks").select("id").limit(1).execute()
    except Exception as e:
        supabase_status = f"unhealthy: {str(e)[:50]}"

    # Check WebSocket status
    ws_stats = ws_manager.get_stats()
    ws_status = "healthy" if ws_stats.get("running", False) else "starting"

    # Check x402 SDK status (NOW-202)
    x402_status = "disabled"
    if x402_sdk:
        try:
            health = await x402_sdk.health_check()
            x402_status = "healthy" if health.get("facilitator_healthy") else "degraded"
        except Exception:
            x402_status = "error"
    elif X402_SDK_AVAILABLE:
        x402_status = "not_configured"

    # MCP Streamable HTTP status
    mcp_status = "healthy" if MCP_HTTP_AVAILABLE else "disabled"

    # ERC-8004 status (Base-first via facilitator)
    erc8004_status = "disabled"
    if ERC8004_AVAILABLE:
        try:
            # Just check if client can be created
            client = get_facilitator_client()
            erc8004_status = "healthy"
        except Exception:
            erc8004_status = "error"

    return HealthResponse(
        status="healthy" if supabase_status == "healthy" else "degraded",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=os.environ.get("ENVIRONMENT", "development"),
        services={
            "supabase": supabase_status,
            "mcp_http": mcp_status,  # Streamable HTTP transport
            "websocket": ws_status,
            "x402": x402_status,
            "erc8004": erc8004_status,  # Facilitator-backed reputation
        },
    )


# Worker endpoints (for dashboard/mobile)
@app.post("/api/v1/executors/register", tags=["Workers"])
async def register_executor(data: ExecutorRegistration):
    """Register a new executor (worker) with wallet address."""
    try:
        client = db.get_client()

        # Check if executor already exists
        existing = (
            client.table("executors")
            .select("*")
            .eq("wallet_address", data.wallet_address.lower())
            .execute()
        )

        if existing.data and len(existing.data) > 0:
            return {"executor": existing.data[0], "created": False}

        # Create new executor
        executor_data = {
            "wallet_address": data.wallet_address.lower(),
            "display_name": data.display_name or f"Worker {data.wallet_address[:8]}",
            "reputation_score": 50,  # Start at Bayesian prior mean
            "tasks_completed": 0,
            "tasks_disputed": 0,
        }

        result = client.table("executors").insert(executor_data).execute()

        if result.data and len(result.data) > 0:
            return {"executor": result.data[0], "created": True}

        raise HTTPException(status_code=500, detail="Failed to create executor")

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post(
    "/api/v1/tasks/apply",
    tags=["Tasks"],
    deprecated=True,
    include_in_schema=False,
)
async def apply_to_task(data: TaskApplication):
    """Deprecated legacy endpoint. Use /api/v1/tasks/{task_id}/apply instead."""
    canonical = f"/api/v1/tasks/{data.task_id}/apply"
    logger.warning(
        "Legacy endpoint /api/v1/tasks/apply called. Redirect users to %s",
        canonical,
    )
    raise HTTPException(
        status_code=410,
        detail={
            "error": "Endpoint deprecated",
            "message": "Use canonical worker application endpoint.",
            "canonical_endpoint": canonical,
        },
    )


@app.post(
    "/api/v1/submissions",
    tags=["Submissions"],
    deprecated=True,
    include_in_schema=False,
)
async def submit_work(data: WorkSubmission):
    """Deprecated legacy endpoint. Use /api/v1/tasks/{task_id}/submit instead."""
    canonical = f"/api/v1/tasks/{data.task_id}/submit"
    logger.warning(
        "Legacy endpoint /api/v1/submissions called. Redirect users to %s",
        canonical,
    )
    raise HTTPException(
        status_code=410,
        detail={
            "error": "Endpoint deprecated",
            "message": "Use canonical worker submission endpoint.",
            "canonical_endpoint": canonical,
        },
    )


@app.get("/api/v1/executors/{executor_id}/tasks", tags=["Workers"])
async def get_my_tasks(executor_id: str, status: str | None = None):
    """Get tasks for a specific executor."""
    try:
        client = db.get_client()

        query = (
            client.table("tasks")
            .select("*, agent:agents(id, display_name)")
            .eq("executor_id", executor_id)
        )

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).execute()

        return {
            "tasks": result.data or [],
            "count": len(result.data) if result.data else 0,
        }

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/executors/{executor_id}/stats", tags=["Workers"])
async def get_executor_stats(executor_id: str):
    """Get statistics for an executor."""
    try:
        stats = await db.get_executor_stats(executor_id)
        if not stats:
            raise HTTPException(status_code=404, detail="Executor not found")
        return stats
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/v1/tasks/available", tags=["Tasks"])
async def get_available_tasks(
    category: str | None = None,
    min_bounty: float | None = None,
    max_bounty: float | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """Get available tasks for workers to browse."""
    try:
        client = db.get_client()

        query = client.table("tasks").select("*").eq("status", "published")

        if category:
            query = query.eq("category", category)
        if min_bounty is not None:
            query = query.gte("bounty_usd", min_bounty)
        if max_bounty is not None:
            query = query.lte("bounty_usd", max_bounty)

        result = (
            query.order("bounty_usd", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return {
            "tasks": result.data or [],
            "count": len(result.data) if result.data else 0,
            "offset": offset,
        }

    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


# x402 SDK info endpoint (NOW-202)
@app.get("/api/v1/x402/info", tags=["Payments"])
async def x402_info():
    """Get x402 payment SDK status and configuration."""
    if not X402_SDK_AVAILABLE:
        return {
            "available": False,
            "error": "uvd-x402-sdk not installed",
            "install": "pip install uvd-x402-sdk[fastapi]",
        }

    info = get_sdk_info() if get_sdk_info else {"available": False}

    if x402_sdk:
        try:
            health = await x402_sdk.health_check()
            info["health"] = health
        except Exception as e:
            info["health_error"] = str(e)

    return info


@app.get("/api/v1/x402/networks", tags=["Payments"])
async def x402_networks():
    """Get supported networks for x402 payments."""
    return {
        "facilitator": FACILITATOR_URL or "https://facilitator.ultravioletadao.xyz",
        "mainnets": [
            "ethereum",
            "base",
            "polygon",
            "optimism",
            "arbitrum",
            "avalanche",
            "bsc",
            "gnosis",
            "celo",
            "linea",
            "scroll",
            "zksync",
            "mantle",
            "mode",
            "hyperliquid",
            "sonic",
            "megaeth",
            "worldchain",
            "ink",
        ],
        "testnets": [
            "sepolia",
            "base-sepolia",
            "polygon-amoy",
            "optimism-sepolia",
            "arbitrum-sepolia",
            "avalanche-fuji",
            "bsc-testnet",
        ],
        "tokens": {
            "USDC": "Native Circle USDC on all networks",
            "EURC": "Euro Coin on Base, Polygon",
            "DAI": "DAI stablecoin",
            "USDT": "Tether USD",
        },
    }


# MCP info endpoint
@app.get("/")
async def root():
    """Root endpoint with MCP server info."""
    base_url = os.environ.get("MCP_BASE_URL", "https://api.execution.market")

    return {
        "name": "Execution Market MCP Server",
        "version": "0.1.0",
        "description": "Human Execution Layer for AI Agents",
        "mcp": {
            "transport": "streamable-http",
            "endpoint": f"{base_url}/mcp/",
            "protocol_version": "2025-03-26",
            "status": "enabled" if MCP_HTTP_AVAILABLE else "disabled",
            "stateless_mode": MCP_STATELESS_HTTP,
            "features": [
                "tool_invocation",
                "sse_streaming",
                "session_management",
                "batch_requests",
            ],
            "tools": [
                "em_publish_task",
                "em_get_tasks",
                "em_get_task",
                "em_check_submission",
                "em_approve_submission",
                "em_cancel_task",
                "em_apply_to_task",
                "em_submit_work",
                "em_get_my_tasks",
                "em_withdraw_earnings",
            ],
        },
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "mcp_streamable_http": "/mcp",  # Streamable HTTP endpoint
            "websocket": "/ws",
            "websocket_stats": "/ws/stats",
            "a2a_agent_card": "/.well-known/agent.json",
            "a2a_discovery": "/discovery/agents",
            "api": {
                "base": "/api/v1",
                "tasks": "/api/v1/tasks",
                "analytics": "/api/v1/analytics",
                "available_tasks": "/api/v1/tasks/available",
                "reputation": "/api/v1/reputation",
                "escrow": "/api/v1/escrow",
            },
        },
        "protocols": {
            "mcp_http": f"{base_url}/mcp",  # Primary MCP endpoint
            "http": f"{base_url}/api/v1",
            "websocket": f"wss://{base_url.replace('https://', '').replace('http://', '')}/ws",
            "a2a": f"{base_url}/a2a/v1",
        },
        "links": {
            "dashboard": "https://execution.market",
            "docs": "https://docs.execution.market",
            "github": "https://github.com/ultravioleta-dao/execution-market",
            "mcp_spec": "https://modelcontextprotocol.io/specification/2025-03-26",
            "a2a_spec": "https://a2a-protocol.org/latest/specification/",
        },
        "skills": {
            "main": f"{base_url}/skill.md",
            "heartbeat": f"{base_url}/heartbeat.md",
            "workflows": f"{base_url}/workflows.md",
            "list": f"{base_url}/skills",
            "install": "clawhub install execution-market",
        },
        "payments": {
            "x402_sdk": "enabled" if x402_sdk else "disabled",
            "facilitator": FACILITATOR_URL or "https://facilitator.ultravioletadao.xyz",
            "escrow_network": "base",
            "supported_tokens": ["USDC", "EURC", "USDT", "PYUSD"],
        },
        "reputation": {
            "erc8004": "enabled" if ERC8004_AVAILABLE else "disabled",
            "network": ERC8004_NETWORK,
            "em_agent_id": EM_AGENT_ID,
            "facilitator": ERC8004_FACILITATOR_URL
            if ERC8004_AVAILABLE
            else "https://facilitator.ultravioletadao.xyz",
            "contracts": {
                "identity_registry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
                "reputation_registry": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
            },
        },
    }


# =============================================================================
# SKILL DOCUMENTATION ENDPOINTS (OpenClaw / MoltX compatible)
# =============================================================================

# Path to skill files (inside mcp_server for Docker compatibility)
SKILL_DIR = Path(__file__).parent / "skills"


@app.get("/skill.md", response_class=PlainTextResponse, tags=["A2A"])
async def get_skill_md():
    """
    Get the main skill documentation for AI agents.

    This file follows the OpenClaw SKILL.md format and can be used by:
    - OpenClaw agents (install via `clawhub install execution-market`)
    - MoltX/MoltBook agents (read and follow instructions)
    - Any AI agent that understands markdown documentation

    Install locally:
    ```bash
    mkdir -p ~/.openclaw/skills/execution-market
    curl -s https://api.execution.market/skill.md > ~/.openclaw/skills/execution-market/SKILL.md
    ```
    """
    skill_file = SKILL_DIR / "SKILL.md"
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail="SKILL.md not found")
    return skill_file.read_text(encoding="utf-8")


@app.get("/heartbeat.md", response_class=PlainTextResponse, tags=["A2A"])
async def get_heartbeat_md():
    """
    Get the heartbeat documentation for task monitoring.

    Describes efficient polling patterns and health checks for AI agents
    integrating with Execution Market.
    """
    heartbeat_file = SKILL_DIR / "HEARTBEAT.md"
    if not heartbeat_file.exists():
        raise HTTPException(status_code=404, detail="HEARTBEAT.md not found")
    return heartbeat_file.read_text(encoding="utf-8")


@app.get("/workflows.md", response_class=PlainTextResponse, tags=["A2A"])
async def get_workflows_md():
    """
    Get common workflow patterns for Execution Market tasks.

    Includes examples for physical verification, knowledge access,
    simple actions, and more.
    """
    workflows_file = SKILL_DIR / "WORKFLOWS.md"
    if not workflows_file.exists():
        raise HTTPException(status_code=404, detail="WORKFLOWS.md not found")
    return workflows_file.read_text(encoding="utf-8")


@app.get("/skills", tags=["A2A"])
async def list_skills():
    """
    List all available skill documentation files.

    Returns URLs for each skill file that agents can fetch.
    """
    base_url = os.environ.get("MCP_BASE_URL", "https://api.execution.market")

    files = []
    if SKILL_DIR.exists():
        for f in SKILL_DIR.glob("*.md"):
            files.append(
                {
                    "name": f.stem,
                    "filename": f.name,
                    "url": f"{base_url}/{f.name.lower()}",
                }
            )

    return {
        "name": "execution-market",
        "version": "1.0.0",
        "description": "Hire humans for physical-world tasks",
        "install": {
            "openclaw": "clawhub install execution-market",
            "manual": f"curl -s {base_url}/skill.md > ~/.openclaw/skills/execution-market/SKILL.md",
        },
        "files": files,
        "primary": f"{base_url}/skill.md",
    }


# Run with: uvicorn api:app --reload
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
