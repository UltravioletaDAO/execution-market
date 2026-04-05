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

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse, PlainTextResponse, HTMLResponse, Response
from pydantic import BaseModel, field_validator
from pathlib import Path

import supabase_client as db
from jobs.task_expiration import run_task_expiration_loop
from jobs.auto_payment import run_auto_payment_loop
from jobs.fee_sweep import run_fee_sweep_loop
from audit.escrow_reconciler import run_escrow_reconciliation_loop

# Import MCP server for Streamable HTTP mounting
from server import mcp as mcp_server
from websocket import ws_router, ws_manager
from a2a import a2a_router
from api import api_router, add_api_middleware
from api import reputation_router, escrow_router
from api.admin import router as admin_router
from api.agent_auth import router as agent_auth_router
from api.h2a import router as h2a_router
from health import router as health_router

# Chat relay (IRC bridge)
try:
    from chat import chat_router, setup_chat, teardown_chat

    CHAT_AVAILABLE = True
except ImportError:
    CHAT_AVAILABLE = False
    chat_router = None
    setup_chat = None
    teardown_chat = None

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

    # Start MeshRelay webhook adapter
    meshrelay_adapter = None
    try:
        from events import get_event_bus
        from events.adapters.meshrelay import MeshRelayAdapter

        bus = get_event_bus()
        meshrelay_adapter = MeshRelayAdapter(bus=bus)
        meshrelay_adapter.start()
    except Exception as e:
        logger.warning("MeshRelayAdapter init failed (non-fatal): %s", e)

    # Start chat relay (IRC bridge)
    chat_resources = {}
    if CHAT_AVAILABLE and setup_chat:
        try:
            from events import get_event_bus as _get_bus

            chat_resources = await setup_chat(event_bus=_get_bus())
        except Exception as e:
            logger.warning("Chat relay init failed (non-fatal): %s", e)

    # Start background jobs
    expiration_task = asyncio.create_task(run_task_expiration_loop())
    logger.info("Task expiration background job scheduled")

    auto_payment_task = asyncio.create_task(run_auto_payment_loop())
    logger.info("Auto-payment background job scheduled")

    fee_sweep_task = asyncio.create_task(run_fee_sweep_loop())
    logger.info(
        "Fee sweep background job scheduled (every %ss)",
        os.environ.get("FEE_SWEEP_INTERVAL", "21600"),
    )

    reconciler_task = asyncio.create_task(run_escrow_reconciliation_loop())
    logger.info(
        "Escrow reconciliation background job scheduled (every %ss)",
        os.environ.get("EM_RECONCILE_INTERVAL", "900"),
    )

    # Initialize MCP session manager
    # The session manager must be running for Streamable HTTP to work
    mcp_session_healthy = False
    if MCP_HTTP_AVAILABLE:
        try:
            # Get the session manager after app is created
            session_manager = mcp_server.session_manager
            logger.info("Initializing MCP session manager...")

            # Run the session manager as async context manager
            async with session_manager.run():
                logger.info("MCP session manager started successfully")
                mcp_session_healthy = True
                app.state.mcp_session_healthy = True
                from audit import audit_log

                audit_log(
                    "server_started", version=app.version, host="0.0.0.0", port=8000
                )
                yield
                logger.info("Shutting down MCP session manager...")
        except Exception as e:
            logger.error(
                "MCP session manager FAILED — MCP transport unavailable: %s", e
            )
            app.state.mcp_session_healthy = False
            yield
    else:
        yield

    # Cancel background jobs on shutdown
    _bg_tasks = [expiration_task, auto_payment_task, fee_sweep_task, reconciler_task]
    for task in _bg_tasks:
        task.cancel()
    for task in _bg_tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("Background jobs stopped (4/4 cancelled)")

    # Stop MeshRelay adapter
    if meshrelay_adapter:
        meshrelay_adapter.stop()
        await meshrelay_adapter.close()

    # Stop chat relay
    if chat_resources and CHAT_AVAILABLE and teardown_chat:
        await teardown_chat(chat_resources)

    # Close Supabase client to release connections
    db.close_client()

    logger.info("Shutting down Execution Market MCP Server")


# OpenAPI Tags for documentation organization (NOW-206)
tags_metadata = [
    {
        "name": "Health",
        "description": "Health checks, readiness probes, and server status.",
    },
    {
        "name": "Tasks",
        "description": "Task CRUD — publish bounties, query, cancel. Core resource for agents.",
    },
    {
        "name": "Workers",
        "description": "Worker (executor) registration, profiles, and management.",
    },
    {
        "name": "Submissions",
        "description": "Evidence submissions from workers — upload proof, check status.",
    },
    {
        "name": "Evidence",
        "description": "Evidence processing — AI verification, EXIF extraction, S3 uploads.",
    },
    {
        "name": "Payments",
        "description": "x402 payment operations — balance checks, fee calculation, settlement info.",
    },
    {
        "name": "Escrow",
        "description": "x402r on-chain escrow — lock, release, refund across 9 EVM chains.",
    },
    {
        "name": "Reputation",
        "description": "ERC-8004 on-chain reputation — bidirectional feedback, scores, identity.",
    },
    {
        "name": "Identity",
        "description": "ERC-8004 agent/worker identity — registration, lookup, verification.",
    },
    {
        "name": "World ID",
        "description": "World ID 4.0 proof of humanity — RP signing, Orb-level verification.",
    },
    {
        "name": "Agent Auth",
        "description": "ERC-8128 wallet-based authentication for dashboard and agents.",
    },
    {
        "name": "H2A Marketplace",
        "description": "Human-to-Agent marketplace — humans publish tasks for AI agents.",
    },
    {
        "name": "Agent Directory",
        "description": "Registered agent discovery and profiles.",
    },
    {
        "name": "A2A Protocol",
        "description": "Agent-to-Agent JSON-RPC protocol (v0.3.0).",
    },
    {
        "name": "A2A Discovery",
        "description": "A2A agent card and capability discovery (/.well-known/agent.json).",
    },
    {
        "name": "x402 Discovery",
        "description": "x402 protocol auto-discovery (/.well-known/x402).",
    },
    {
        "name": "Webhooks",
        "description": "Webhook registration and event delivery.",
    },
    {
        "name": "Account",
        "description": "User account management and preferences.",
    },
    {
        "name": "Moderation",
        "description": "Content moderation and platform safety.",
    },
    {
        "name": "Audit",
        "description": "Audit grid and payment event trail.",
    },
    {
        "name": "Legal",
        "description": "Terms of service and legal documents.",
    },
    {
        "name": "Chat",
        "description": "Real-time chat relay (IRC bridge) per task.",
    },
    {
        "name": "WebSocket",
        "description": "Real-time WebSocket connections for live updates.",
    },
    {
        "name": "Admin",
        "description": "Platform administration — config, stats, feature flags (requires admin key).",
    },
    {
        "name": "Misc",
        "description": "Miscellaneous utility endpoints.",
    },
]

# Initialize FastAPI app with enhanced metadata (NOW-206)
# Include lifespan for MCP Streamable HTTP session management
app = FastAPI(
    title="Execution Market API",
    lifespan=lifespan,
    description="""
## Universal Execution Layer

Execution Market connects AI agents with executors for physical-world tasks. Humans today, robots tomorrow.

### Features

| Feature | Description |
|---------|-------------|
| **x402r Escrow** | Trustless on-chain escrow with gasless settlement (9 EVM chains + Solana) |
| **ERC-8004 Identity** | On-chain agent/worker identity on 16 networks via Facilitator |
| **ERC-8128 Auth** | Wallet-based authentication with signed challenges |
| **World ID** | Sybil-resistant proof of humanity (Orb-level verification) |
| **OWS Wallet** | Open Wallet Standard — multi-chain wallet management for AI agents (separate MCP server) |
| **A2A Protocol** | Agent-to-Agent communication (v0.3.0) |
| **MCP Tools** | 18 tools across 4 modules for AI agent integration |
| **Real-time** | WebSocket notifications + MeshRelay event bus |

### Authentication

| Method | Header | Status |
|--------|--------|--------|
| **ERC-8128 Wallet Signing** | `Authorization: ERC-8128 <signed-challenge>` | **Primary** |
| API Key | `X-API-Key` | Disabled by default (`EM_API_KEYS_ENABLED=false`) |
| Bearer Token | `Authorization: Bearer <token>` | Disabled by default |

### Payment Networks

10 networks supported: Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, Monad, SKALE + Solana (SPL transfers).
Gasless via [Ultravioleta Facilitator](https://facilitator.ultravioletadao.xyz). Agent signs EIP-3009 auth, Facilitator pays gas.

### Links

- [Dashboard](https://execution.market)
- [GitHub](https://github.com/ultravioleta-dao/execution-market)
- [Skill for AI Agents](https://execution.market/skill.md)
    """,
    version="2.0.0",
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
    docs_url=None,  # Custom dark-themed Swagger served at /docs
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ── Custom dark-themed Swagger UI ────────────────────────────────────────────

_SWAGGER_DARK_CSS = """
/* Execution Market — Dark Swagger Theme v2 */
body { background: #09090b; margin: 0; }

.swagger-ui .topbar {
  background-color: #18181b;
  border-bottom: 1px solid #3f3f46;
  padding: 8px 0;
}
.swagger-ui .topbar .download-url-wrapper { display: none; }
.swagger-ui .topbar-wrapper img { content: none; }
.swagger-ui .topbar-wrapper::before {
  content: 'Execution Market API';
  font-family: 'Roboto Mono', monospace;
  font-size: 16px;
  font-weight: 700;
  color: #0ea5e9;
  letter-spacing: -0.04em;
}

.swagger-ui { font-family: 'Roboto Mono', monospace; color: #fafafa; }

/* Info block — tight layout */
.swagger-ui .info { margin: 32px 0 24px; }
.swagger-ui .info hgroup.main { margin: 0 0 16px; }
.swagger-ui .info .title { color: #fafafa; font-family: 'Roboto Mono', monospace; font-size: 28px; }
.swagger-ui .info .title small { background: #0ea5e9; color: #fff; border-radius: 3px; font-size: 11px; padding: 2px 8px; vertical-align: middle; }
.swagger-ui .info p, .swagger-ui .info li { color: #a1a1aa; font-size: 13px; line-height: 1.6; }
.swagger-ui .info a { color: #0ea5e9; }

/* Info block — headings */
.swagger-ui .info .renderedMarkdown h2 { color: #fafafa; font-family: 'Roboto Mono', monospace; font-size: 20px; margin: 24px 0 8px; border-bottom: 1px solid #3f3f46; padding-bottom: 8px; }
.swagger-ui .info .renderedMarkdown h3 { color: #e4e4e7; font-family: 'Roboto Mono', monospace; font-size: 14px; margin: 20px 0 8px; text-transform: uppercase; letter-spacing: 0.05em; }

/* Info block — tables (features, auth, etc.) */
.swagger-ui .info table { color: #a1a1aa; border-collapse: collapse; width: 100%; margin: 8px 0 16px; font-size: 12px; }
.swagger-ui .info table thead tr th {
  color: #71717a; background: #18181b; border: 1px solid #3f3f46;
  font-family: 'Roboto Mono', monospace; font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.05em; padding: 8px 12px; text-align: left;
}
.swagger-ui .info table tbody tr td {
  border: 1px solid #3f3f46; padding: 8px 12px; background: transparent; vertical-align: top;
}
.swagger-ui .info table tbody tr:hover td { background: rgba(14,165,233,0.04); }
.swagger-ui .info table strong { color: #fafafa; }
.swagger-ui .info table code { color: #38bdf8; background: #27272a; padding: 1px 5px; border-radius: 3px; font-size: 11px; }

/* Info block — lists */
.swagger-ui .info ul { padding-left: 20px; margin: 4px 0 12px; }
.swagger-ui .info li { margin: 2px 0; }

/* Version badge row — inline */
.swagger-ui .info .base-url { color: #71717a; font-size: 12px; }

/* Scheme selector / OAS version row — compact */
.swagger-ui .scheme-container { background: #18181b; box-shadow: none; border-bottom: 1px solid #3f3f46; padding: 8px 0; }
.swagger-ui .schemes > label { color: #71717a; font-family: 'Roboto Mono', monospace; font-size: 12px; }

/* Contact/license links — subtle */
.swagger-ui .info .info__contact, .swagger-ui .info .info__license,
.swagger-ui .info .info__extdocs, .swagger-ui .info .info__tos {
  font-size: 12px; color: #71717a; margin: 2px 0;
}

/* Main wrapper */
.swagger-ui .wrapper { background: #09090b; max-width: 1200px; }
#swagger-ui { background: #09090b; }

/* Tags */
.swagger-ui .opblock-tag {
  border-bottom: 1px solid #3f3f46;
  color: #fafafa;
  font-family: 'Roboto Mono', monospace;
  font-size: 14px;
}
.swagger-ui .opblock-tag:hover { background: #18181b; }
.swagger-ui .opblock-tag small { color: #71717a; }

/* Operation blocks */
.swagger-ui .opblock {
  background: #18181b;
  border: 1px solid #3f3f46;
  border-radius: 6px;
  margin: 4px 0;
  box-shadow: none;
}
.swagger-ui .opblock .opblock-summary {
  border-bottom: 1px solid #3f3f46;
}
.swagger-ui .opblock .opblock-summary-path {
  font-family: 'Roboto Mono', monospace;
  font-size: 13px;
  color: #fafafa;
}
.swagger-ui .opblock .opblock-summary-operation-id,
.swagger-ui .opblock .opblock-summary-description {
  color: #a1a1aa;
  font-family: 'Roboto Mono', monospace;
  font-size: 12px;
}
.swagger-ui .opblock .opblock-section-header {
  background: #27272a;
}
.swagger-ui .opblock .opblock-section-header h4 {
  color: #a1a1aa;
  font-family: 'Roboto Mono', monospace;
}

/* GET, POST, etc. color coding */
.swagger-ui .opblock.opblock-get    { border-color: #0ea5e9; }
.swagger-ui .opblock.opblock-post   { border-color: #22c55e; }
.swagger-ui .opblock.opblock-put    { border-color: #f59e0b; }
.swagger-ui .opblock.opblock-patch  { border-color: #f97316; }
.swagger-ui .opblock.opblock-delete { border-color: #ef4444; }

.swagger-ui .opblock.opblock-get    .opblock-summary { background: rgba(14,165,233,0.07); }
.swagger-ui .opblock.opblock-post   .opblock-summary { background: rgba(34,197,94,0.07); }
.swagger-ui .opblock.opblock-put    .opblock-summary { background: rgba(245,158,11,0.07); }
.swagger-ui .opblock.opblock-patch  .opblock-summary { background: rgba(249,115,22,0.07); }
.swagger-ui .opblock.opblock-delete .opblock-summary { background: rgba(239,68,68,0.07); }

/* HTTP method badges */
.swagger-ui .opblock-summary-method {
  font-family: 'Roboto Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  border-radius: 3px;
  min-width: 60px;
}

/* Body/description text */
.swagger-ui .opblock-body { background: #09090b; }
.swagger-ui textarea { background: #27272a; color: #fafafa; border-color: #3f3f46; font-family: 'Roboto Mono', monospace; font-size: 12px; }
.swagger-ui input[type=text], .swagger-ui input[type=password], .swagger-ui input[type=search], .swagger-ui input[type=email] {
  background: #27272a; color: #fafafa; border-color: #3f3f46; font-family: 'Roboto Mono', monospace;
}
.swagger-ui select {
  background: #27272a; color: #fafafa; border-color: #3f3f46; font-family: 'Roboto Mono', monospace;
}
.swagger-ui label { color: #a1a1aa; font-family: 'Roboto Mono', monospace; font-size: 12px; }

/* Parameters table (scoped to avoid overriding info tables) */
.swagger-ui .opblock table { color: #fafafa; }
.swagger-ui .opblock table tbody tr td { border-color: #3f3f46; background: transparent; }
.swagger-ui .opblock table thead tr th { color: #71717a; border-color: #3f3f46; font-family: 'Roboto Mono', monospace; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
.swagger-ui table.responses-table { color: #fafafa; }
.swagger-ui table.responses-table thead tr th { color: #71717a; border-color: #3f3f46; font-family: 'Roboto Mono', monospace; font-size: 11px; text-transform: uppercase; }
.swagger-ui .parameters-col_description p { color: #a1a1aa; }
.swagger-ui .parameter__name { color: #0ea5e9; font-family: 'Roboto Mono', monospace; }
.swagger-ui .parameter__type { color: #71717a; font-family: 'Roboto Mono', monospace; font-size: 12px; }
.swagger-ui .parameter__in { color: #52525b; font-family: 'Roboto Mono', monospace; font-size: 11px; }

/* Code / schema blocks */
.swagger-ui .highlight-code, .swagger-ui pre { background: #18181b !important; border: 1px solid #3f3f46; border-radius: 4px; }
.swagger-ui code { color: #38bdf8; font-family: 'Roboto Mono', monospace; font-size: 12px; }

/* Response blocks */
.swagger-ui .responses-wrapper { background: #09090b; }
.swagger-ui .response-col_status { color: #a1a1aa; font-family: 'Roboto Mono', monospace; }
.swagger-ui .response-col_description { color: #a1a1aa; }
.swagger-ui table.responses-table tbody tr { background: transparent; }

/* Authorization modal */
.swagger-ui .dialog-ux .modal-ux { background: #18181b; border: 1px solid #3f3f46; }
.swagger-ui .dialog-ux .modal-ux-header { background: #27272a; border-bottom: 1px solid #3f3f46; }
.swagger-ui .dialog-ux .modal-ux-header h3 { color: #fafafa; font-family: 'Roboto Mono', monospace; }

/* Buttons */
.swagger-ui .btn {
  font-family: 'Roboto Mono', monospace;
  font-size: 12px;
  border-radius: 4px;
}
.swagger-ui .btn.authorize { background: #0ea5e9; border-color: #0ea5e9; color: #fff; }
.swagger-ui .btn.authorize svg { fill: #fff; }
.swagger-ui .btn.execute { background: #0ea5e9; border-color: #0ea5e9; }
.swagger-ui .btn.cancel { background: transparent; border-color: #3f3f46; color: #a1a1aa; }

/* Models section */
.swagger-ui section.models { background: #18181b; border: 1px solid #3f3f46; border-radius: 6px; }
.swagger-ui section.models h4 { color: #fafafa; font-family: 'Roboto Mono', monospace; }
.swagger-ui section.models .model-container { background: #09090b; }
.swagger-ui .model { color: #a1a1aa; }
.swagger-ui .model-title { color: #fafafa; font-family: 'Roboto Mono', monospace; }
.swagger-ui .prop-name { color: #0ea5e9; }
.swagger-ui .prop-type { color: #22c55e; }
.swagger-ui .prop-format { color: #71717a; }

/* Filter */
.swagger-ui .filter .operation-filter-input {
  background: #27272a; border-color: #3f3f46; color: #fafafa; font-family: 'Roboto Mono', monospace;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #18181b; }
::-webkit-scrollbar-thumb { background: #3f3f46; border-radius: 3px; }
"""


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    # Generate default Swagger HTML (keeps CDN base CSS for layout/flexbox)
    base = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Execution Market API",
        swagger_favicon_url="https://execution.market/favicon.ico",
        swagger_ui_parameters={
            "deepLinking": True,
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "defaultModelsExpandDepth": 1,
            "syntaxHighlight.theme": "monokai",
        },
    )
    # Inject dark theme as additional stylesheet AFTER the CDN base CSS
    html = base.body.decode()
    html = html.replace(
        "</head>",
        '<link rel="stylesheet" href="/docs/swagger-dark.css">\n</head>',
    )
    return HTMLResponse(content=html)


@app.get("/docs/swagger-dark.css", include_in_schema=False)
async def swagger_dark_css() -> Response:
    return Response(
        content=_SWAGGER_DARK_CSS,
        media_type="text/css",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# Custom 422 handler: return field-level validation errors instead of generic message
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = []
    for error in exc.errors():
        loc = error.get("loc", ())
        # Skip "body" prefix in location path
        field_path = ".".join(str(p) for p in loc if p != "body")
        errors.append(
            {
                "field": field_path or "(unknown)",
                "message": error.get("msg", "Validation error"),
                "type": error.get("type", "unknown"),
            }
        )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": errors,
        },
    )


# Add API middleware (rate limiting, logging, error handling)
add_api_middleware(app)

# Initialize x402 SDK (NOW-202)
x402_sdk: Optional[EMX402SDK] = None
if X402_SDK_AVAILABLE and setup_x402_for_app:
    try:
        # Settlement address: platform wallet (transit) for split-payment disbursement.
        # Do NOT pass EM_TREASURY_ADDRESS here — that causes funds to settle directly
        # to treasury, preventing worker payout. The SDK resolves the correct address
        # from EM_SETTLEMENT_ADDRESS > WALLET_PRIVATE_KEY > EM_TREASURY (fallback).
        network = os.environ.get("X402_NETWORK", "base")
        x402_sdk = setup_x402_for_app(
            app,
            recipient_address=None,  # Let SDK resolve from env
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

# Include Chat relay router (IRC bridge)
if CHAT_AVAILABLE and chat_router:
    app.include_router(chat_router)
    logger.info("Chat relay WebSocket router mounted at /ws/chat/{task_id}")

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

# Include Agent Auth router for dashboard login
# Provides /api/v1/agent/auth
app.include_router(agent_auth_router)

# Include ERC-8004 Reputation router (Base-first)
# Provides /api/v1/reputation/* for on-chain identity and feedback
app.include_router(reputation_router)

# Include x402r Escrow router (Base Mainnet)
# Provides /api/v1/escrow/* for payment management
app.include_router(escrow_router)

# Include H2A (Human-to-Agent) marketplace router
# Provides /api/v1/h2a/* for human publisher flow and /api/v1/agents/* for agent directory
app.include_router(h2a_router)

# Include x402 Discovery router
# Provides /.well-known/x402 for x402 protocol auto-discovery (AgentCash, x402scan, etc.)
try:
    from api.routers.x402_discovery import router as x402_discovery_router

    app.include_router(x402_discovery_router)
    logger.info("x402 Discovery router registered at /.well-known/x402")
except ImportError as e:
    logger.info("x402 Discovery router not available: %s", e)

# Include KK V2 Swarm router (optional, enabled via SWARM_ENABLED env)
# Provides /api/v1/swarm/* for swarm coordination, monitoring, and operations
try:
    from api.swarm import router as swarm_router

    app.include_router(swarm_router)
    logger.info("Swarm API router registered at /api/v1/swarm/*")
except ImportError as e:
    logger.info("Swarm API not available: %s", e)

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
        "https://meshrelay.xyz",  # MeshRelay integration
        "https://api.meshrelay.xyz",  # MeshRelay API
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Admin-Key",
        "X-Admin-Actor",
        "X-Client-Info",
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

# Request timeout middleware — prevent hung requests from consuming resources
from starlette.middleware.base import BaseHTTPMiddleware


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    LONG_TIMEOUT_PATHS = ("/api/v1/tasks/", "/api/v1/submissions/", "/api/v1/escrow/")
    STREAM_PATHS = ("/a2a/v1", "/mcp/")

    async def dispatch(self, request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.STREAM_PATHS):
            timeout = 300.0
        elif any(path.startswith(p) for p in self.LONG_TIMEOUT_PATHS):
            timeout = 120.0
        else:
            timeout = 30.0
        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"error": "Request timeout", "timeout_seconds": timeout},
            )


app.add_middleware(RequestTimeoutMiddleware)

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
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Basic Health Check",
    description="Lightweight health check for load balancers and monitoring. Returns status of all integrated services.",
    responses={
        200: {"description": "Server is healthy or degraded"},
        503: {"description": "Server is unhealthy"},
    },
)
async def health_check():
    """Health check endpoint for load balancers and monitoring."""

    # Check Supabase connection (with timeout to prevent health check hang)
    supabase_status = "healthy"
    try:
        client = db.get_client()
        await asyncio.wait_for(
            asyncio.to_thread(
                lambda: client.table("tasks").select("id").limit(1).execute()
            ),
            timeout=5.0,
        )
    except asyncio.TimeoutError:
        supabase_status = "timeout (>5s)"
    except Exception as e:
        supabase_status = f"unhealthy: {str(e)[:50]}"

    # Check WebSocket status
    ws_stats = ws_manager.get_stats()
    ws_status = "healthy" if ws_stats.get("running", False) else "starting"

    # Check x402 SDK status (NOW-202)
    x402_status = "disabled"
    if x402_sdk:
        try:
            health = await asyncio.wait_for(x402_sdk.health_check(), timeout=5.0)
            x402_status = "healthy" if health.get("facilitator_healthy") else "degraded"
        except asyncio.TimeoutError:
            x402_status = "timeout"
        except Exception:
            logger.exception("x402 SDK health check failed")
            x402_status = "error"
    elif X402_SDK_AVAILABLE:
        x402_status = "not_configured"

    # MCP Streamable HTTP status (tracks actual session manager state)
    mcp_status = "disabled"
    if MCP_HTTP_AVAILABLE:
        mcp_session_ok = getattr(app.state, "mcp_session_healthy", None)
        if mcp_session_ok is True:
            mcp_status = "healthy"
        elif mcp_session_ok is False:
            mcp_status = "error"
        else:
            mcp_status = "unknown"

    # ERC-8004 status (Base-first via facilitator)
    erc8004_status = "disabled"
    if ERC8004_AVAILABLE:
        try:
            # Just check if client can be created
            client = get_facilitator_client()
            erc8004_status = "healthy"
        except Exception:
            logger.exception("ERC-8004 facilitator client creation failed")
            erc8004_status = "error"

    # Chat relay status
    chat_status = "disabled"
    if CHAT_AVAILABLE:
        try:
            from chat.irc_pool import IRCPool

            pool = IRCPool._instance
            if pool and pool.is_connected:
                chat_status = "healthy"
            elif pool:
                chat_status = "disconnected"
            else:
                chat_status = "not_initialized"
        except Exception:
            logger.exception("Chat relay status check failed")
            chat_status = "error"

    # Dynamic.xyz environment check (informational — frontend SDK config)
    dynamic_env_id = os.environ.get("VITE_DYNAMIC_ENVIRONMENT_ID", "")
    dynamic_status = "configured" if dynamic_env_id else "not_configured"

    # Background jobs health pulse
    bg_jobs = {}
    try:
        from jobs.task_expiration import get_expiration_health

        bg_jobs["task_expiration"] = get_expiration_health()
    except Exception:
        bg_jobs["task_expiration"] = {"status": "import_error"}
    try:
        from jobs.auto_payment import get_auto_payment_health

        bg_jobs["auto_payment"] = get_auto_payment_health()
    except Exception:
        bg_jobs["auto_payment"] = {"status": "import_error"}
    try:
        from jobs.fee_sweep import get_fee_sweep_health

        bg_jobs["fee_sweep"] = get_fee_sweep_health()
    except Exception:
        bg_jobs["fee_sweep"] = {"status": "import_error"}

    # Overall status: degraded if any critical service is down
    any_job_unhealthy = any(j.get("status") == "unhealthy" for j in bg_jobs.values())
    overall = "healthy"
    if supabase_status != "healthy":
        overall = "degraded"
    if any_job_unhealthy:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=os.environ.get("ENVIRONMENT", "development"),
        services={
            "supabase": supabase_status,
            "mcp_http": mcp_status,  # Streamable HTTP transport
            "websocket": ws_status,
            "x402": x402_status,
            "erc8004": erc8004_status,  # Facilitator-backed reputation
            "chat_relay": chat_status,
            "dynamic": dynamic_status,  # Dynamic.xyz auth SDK env
            "background_jobs": bg_jobs,
        },
    )


# Worker endpoints (for dashboard/mobile)
@app.post(
    "/api/v1/executors/register",
    tags=["Workers"],
    summary="Register Worker",
    description="Register a new executor (worker) with their Ethereum wallet address. If the wallet is already registered, returns the existing record.",
    responses={
        200: {"description": "Executor registered or already exists"},
        422: {"description": "Invalid wallet address format"},
        500: {"description": "Internal server error"},
    },
)
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
        logger.exception("Failed to register executor")
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


@app.get(
    "/api/v1/executors/{executor_id}/tasks",
    tags=["Workers"],
    summary="Get Worker Tasks",
    description="Retrieve all tasks assigned to a specific executor, optionally filtered by status.",
    responses={
        200: {"description": "List of tasks for the executor"},
        500: {"description": "Internal server error"},
    },
)
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
        logger.exception("Failed to get tasks for executor %s", executor_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/api/v1/executors/{executor_id}/stats",
    tags=["Workers"],
    summary="Get Worker Statistics",
    description="Retrieve performance statistics for a specific executor including tasks completed, reputation score, and earnings.",
    responses={
        200: {"description": "Executor statistics"},
        404: {"description": "Executor not found"},
        500: {"description": "Internal server error"},
    },
)
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
        logger.exception("Failed to get executor stats for %s", executor_id)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/api/v1/tasks/available",
    tags=["Tasks"],
    summary="Browse Available Tasks (Legacy)",
    description="Get published tasks available for workers. Supports filtering by category and bounty range. **Note:** Prefer `/api/v1/tasks/available` on the API router for richer filtering.",
    responses={
        200: {"description": "List of available tasks"},
        500: {"description": "Internal server error"},
    },
)
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
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return {
            "tasks": result.data or [],
            "count": len(result.data) if result.data else 0,
            "offset": offset,
        }

    except Exception:
        logger.exception("Failed to get available tasks")
        raise HTTPException(status_code=500, detail="Internal server error")


# x402 SDK info endpoint (NOW-202)
@app.get(
    "/api/v1/x402/info",
    tags=["Payments"],
    summary="x402 SDK Info",
    description="Get the current status and configuration of the x402 payment SDK, including facilitator health and supported networks.",
    responses={
        200: {"description": "x402 SDK status and configuration"},
    },
)
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


@app.get(
    "/api/v1/x402/networks",
    tags=["Payments"],
    summary="Supported Payment Networks",
    description="Get all supported mainnet and testnet networks for x402 payments, including supported tokens per network.",
    responses={
        200: {"description": "Supported networks and tokens"},
    },
)
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
        "description": "Universal Execution Layer",
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
                "em_register_as_executor",
                "em_browse_agent_tasks",
                "em_accept_agent_task",
                "em_submit_agent_work",
                "em_get_my_executions",
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
