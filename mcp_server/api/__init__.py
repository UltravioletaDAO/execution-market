"""
Execution Market REST API Module

Provides HTTP endpoints in addition to MCP tools.

Routes:
- /api/v1/tasks - Task management
- /api/v1/submissions - Evidence submissions
- /api/v1/reputation - ERC-8004 identity and reputation (Ethereum Mainnet)
- /api/v1/escrow - x402r escrow management (Base Mainnet)
"""

from .routes import router as api_router
from .auth import verify_api_key, get_api_tier, APIKeyData
from .middleware import add_api_middleware
from .health import (
    router as health_router,
    HealthChecker,
    HealthStatus,
    ComponentHealth,
    SystemHealth,
    get_health_checker,
)
from .openapi import custom_openapi, setup_openapi

# ERC-8004 Reputation routes (Ethereum Mainnet)
from .reputation import router as reputation_router

# x402r Escrow routes (Base Mainnet)
from .escrow import router as escrow_router

# Agent authentication (JWT login for dashboard)
from .agent_auth import router as agent_auth_router

__all__ = [
    # Core routers
    "api_router",
    "health_router",
    "reputation_router",
    "escrow_router",
    "agent_auth_router",
    # Auth
    "verify_api_key",
    "get_api_tier",
    "APIKeyData",
    # Middleware
    "add_api_middleware",
    # Health
    "HealthChecker",
    "HealthStatus",
    "ComponentHealth",
    "SystemHealth",
    "get_health_checker",
    # OpenAPI
    "custom_openapi",
    "setup_openapi",
]
