"""
Chamba MCP Server - FastAPI Wrapper with Streamable HTTP Transport

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
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Mount
from pydantic import BaseModel

import supabase_client as db

# Import MCP server for Streamable HTTP mounting
from server import mcp as mcp_server
from websocket import ws_router, ws_manager
from a2a import a2a_router
from api import api_router, add_api_middleware, health_router as api_health_router
from api import reputation_router, escrow_router
from api.admin import router as admin_router
from health import router as health_router, setup_logging, get_metrics_collector

# x402 SDK Integration (NOW-202)
try:
    from integrations.x402.sdk_client import (
        ChambaX402SDK,
        setup_x402_for_app,
        check_sdk_available,
        get_sdk_info,
        FACILITATOR_URL,
    )
    X402_SDK_AVAILABLE = check_sdk_available()
except ImportError:
    X402_SDK_AVAILABLE = False
    ChambaX402SDK = None
    setup_x402_for_app = None
    FACILITATOR_URL = None

# x402r Escrow Integration (NOW-220 - Production)
try:
    from integrations.x402 import (
        get_x402r_escrow,
        X402R_CONTRACTS,
    )
    X402R_AVAILABLE = True
except ImportError:
    X402R_AVAILABLE = False

# ERC-8004 Integration (Ethereum Mainnet)
try:
    from integrations.erc8004 import (
        get_facilitator_client,
        get_chamba_reputation,
        CHAMBA_AGENT_ID,
        ERC8004_NETWORK,
        FACILITATOR_URL as ERC8004_FACILITATOR_URL,
    )
    ERC8004_AVAILABLE = True
except ImportError:
    ERC8004_AVAILABLE = False
    CHAMBA_AGENT_ID = 469
    ERC8004_NETWORK = "ethereum"
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

    Manages MCP session manager and other async resources.
    Required for Streamable HTTP transport to work correctly.
    """
    logger.info("Starting Chamba MCP Server with Streamable HTTP transport")

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

    logger.info("Shutting down Chamba MCP Server")


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
        "description": "ERC-8004 reputation and identity on Ethereum Mainnet. Bidirectional feedback between agents and workers.",
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
    title="Chamba API",
    lifespan=lifespan,
    description="""
## Human Execution Layer for AI Agents

Chamba connects AI agents with human workers for physical-world tasks.

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
- [Dashboard](https://app.chamba.ultravioletadao.xyz)
- [Documentation](https://docs.chamba.ultravioletadao.xyz)
- [GitHub](https://github.com/ultravioleta-dao/chamba)
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
x402_sdk: Optional[ChambaX402SDK] = None
if X402_SDK_AVAILABLE and setup_x402_for_app:
    try:
        treasury_address = os.environ.get("CHAMBA_TREASURY_ADDRESS")
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

# Include ERC-8004 Reputation router (Ethereum Mainnet)
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
        "https://chamba.ultravioletadao.xyz",
        "https://app.chamba.ultravioletadao.xyz",
        "https://admin.chamba.ultravioletadao.xyz",
        "https://inspector.modelcontextprotocol.io",  # Official MCP Inspector
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=[
        "*",
        "mcp-protocol-version",  # MCP protocol version header
        "mcp-session-id",  # MCP session management
        "Authorization",
        "Content-Type",
        "X-API-Key",
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

    # x402r Escrow status (Base Mainnet)
    x402r_status = "disabled"
    if X402R_AVAILABLE:
        try:
            escrow = get_x402r_escrow()
            config = escrow.get_config()
            x402r_status = "healthy" if config.get("account") else "read_only"
        except Exception:
            x402r_status = "error"

    # ERC-8004 status (Ethereum Mainnet)
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
            "x402r_escrow": x402r_status,  # Base Mainnet escrow
            "erc8004": erc8004_status,  # Ethereum Mainnet reputation
        }
    )


# Worker endpoints (for dashboard/mobile)
@app.post("/api/v1/executors/register", tags=["Workers"])
async def register_executor(data: ExecutorRegistration):
    """Register a new executor (worker) with wallet address."""
    try:
        client = db.get_client()

        # Check if executor already exists
        existing = client.table("executors").select("*").eq(
            "wallet_address", data.wallet_address.lower()
        ).execute()

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/tasks/apply", tags=["Tasks"])
async def apply_to_task(data: TaskApplication):
    """Apply to work on a task."""
    try:
        client = db.get_client()

        # Get task
        task = await db.get_task(data.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task["status"] != "published":
            raise HTTPException(
                status_code=400,
                detail=f"Task is not available (status: {task['status']})"
            )

        # Check if executor exists
        executor = client.table("executors").select("*").eq(
            "id", data.executor_id
        ).single().execute()

        if not executor.data:
            raise HTTPException(status_code=404, detail="Executor not found")

        # Check minimum reputation
        if task.get("min_reputation", 0) > executor.data.get("reputation_score", 0):
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient reputation. Required: {task['min_reputation']}, yours: {executor.data['reputation_score']}"
            )

        # Check for existing application
        existing = client.table("applications").select("*").eq(
            "task_id", data.task_id
        ).eq("executor_id", data.executor_id).execute()

        if existing.data and len(existing.data) > 0:
            raise HTTPException(status_code=400, detail="Already applied to this task")

        # Create application
        application_data = {
            "task_id": data.task_id,
            "executor_id": data.executor_id,
            "message": data.message,
            "status": "pending",
        }

        result = client.table("applications").insert(application_data).execute()

        if result.data and len(result.data) > 0:
            return {
                "application": result.data[0],
                "message": "Application submitted successfully"
            }

        raise HTTPException(status_code=500, detail="Failed to create application")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/submissions", tags=["Submissions"])
async def submit_work(data: WorkSubmission):
    """Submit completed work with evidence."""
    try:
        client = db.get_client()

        # Get task
        task = await db.get_task(data.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        # Verify executor is assigned to this task
        if task.get("executor_id") != data.executor_id:
            raise HTTPException(
                status_code=403,
                detail="You are not assigned to this task"
            )

        if task["status"] not in ["accepted", "in_progress"]:
            raise HTTPException(
                status_code=400,
                detail=f"Task is not in a submittable state (status: {task['status']})"
            )

        # Validate evidence schema
        required = task.get("evidence_schema", {}).get("required", [])
        for req in required:
            if req not in data.evidence:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required evidence: {req}"
                )

        # Create submission
        submission_data = {
            "task_id": data.task_id,
            "executor_id": data.executor_id,
            "evidence": data.evidence,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "agent_verdict": "pending",
        }

        result = client.table("submissions").insert(submission_data).execute()

        if result.data and len(result.data) > 0:
            # Update task status
            await db.update_task(data.task_id, {"status": "submitted"})

            return {
                "submission": result.data[0],
                "message": "Work submitted successfully. Awaiting agent review."
            }

        raise HTTPException(status_code=500, detail="Failed to create submission")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/executors/{executor_id}/tasks", tags=["Workers"])
async def get_my_tasks(executor_id: str, status: str | None = None):
    """Get tasks for a specific executor."""
    try:
        client = db.get_client()

        query = client.table("tasks").select(
            "*, agent:agents(id, display_name)"
        ).eq("executor_id", executor_id)

        if status:
            query = query.eq("status", status)

        result = query.order("created_at", desc=True).execute()

        return {
            "tasks": result.data or [],
            "count": len(result.data) if result.data else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

        result = query.order("bounty_usd", desc=True).range(offset, offset + limit - 1).execute()

        return {
            "tasks": result.data or [],
            "count": len(result.data) if result.data else 0,
            "offset": offset,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            "ethereum", "base", "polygon", "optimism", "arbitrum",
            "avalanche", "bsc", "gnosis", "celo", "linea",
            "scroll", "zksync", "mantle", "mode", "hyperliquid",
            "sonic", "megaeth", "worldchain", "ink",
        ],
        "testnets": [
            "sepolia", "base-sepolia", "polygon-amoy", "optimism-sepolia",
            "arbitrum-sepolia", "avalanche-fuji", "bsc-testnet",
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
    base_url = os.environ.get("MCP_BASE_URL", "https://api.chamba.ultravioletadao.xyz")

    return {
        "name": "Chamba MCP Server",
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
                "chamba_publish_task",
                "chamba_get_tasks",
                "chamba_get_task",
                "chamba_check_submission",
                "chamba_approve_submission",
                "chamba_cancel_task",
                "chamba_apply_to_task",
                "chamba_submit_work",
                "chamba_get_my_tasks",
                "chamba_withdraw_earnings",
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
            "dashboard": "https://app.chamba.ultravioletadao.xyz",
            "docs": "https://docs.chamba.ultravioletadao.xyz",
            "github": "https://github.com/ultravioleta-dao/chamba",
            "mcp_spec": "https://modelcontextprotocol.io/specification/2025-03-26",
            "a2a_spec": "https://a2a-protocol.org/latest/specification/",
        },
        "payments": {
            "x402_sdk": "enabled" if x402_sdk else "disabled",
            "x402r_escrow": "enabled" if X402R_AVAILABLE else "disabled",
            "facilitator": FACILITATOR_URL or "https://facilitator.ultravioletadao.xyz",
            "escrow_network": "base",
            "supported_tokens": ["USDC", "EURC", "DAI", "USDT"],
            "supported_networks": ["base", "polygon", "optimism", "arbitrum", "ethereum", "avalanche"],
        },
        "reputation": {
            "erc8004": "enabled" if ERC8004_AVAILABLE else "disabled",
            "network": ERC8004_NETWORK,
            "chamba_agent_id": CHAMBA_AGENT_ID,
            "facilitator": ERC8004_FACILITATOR_URL if ERC8004_AVAILABLE else "https://facilitator.ultravioletadao.xyz",
            "contracts": {
                "identity_registry": "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432",
                "reputation_registry": "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63",
            },
        },
    }


# Run with: uvicorn api:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
