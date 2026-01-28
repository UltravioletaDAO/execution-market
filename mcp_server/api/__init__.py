"""
Chamba REST API Module

Provides HTTP endpoints in addition to MCP tools.
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

__all__ = [
    "api_router",
    "health_router",
    "verify_api_key",
    "get_api_tier",
    "APIKeyData",
    "add_api_middleware",
    "HealthChecker",
    "HealthStatus",
    "ComponentHealth",
    "SystemHealth",
    "get_health_checker",
    "custom_openapi",
    "setup_openapi",
]
