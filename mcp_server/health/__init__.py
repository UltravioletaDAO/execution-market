"""
Execution Market Health Check and Monitoring Module

Provides comprehensive health checking, metrics, and monitoring utilities for
production deployments.

Components:
- checks: Individual health check functions for dependencies
- endpoints: FastAPI router with health probe endpoints
- metrics: Prometheus metrics collection and exposition
- monitoring: Structured logging, error tracking, and tracing
"""

from .checks import (
    HealthChecker,
    ComponentHealth,
    HealthStatus,
    check_database,
    check_redis,
    check_x402,
    check_storage,
    check_blockchain,
)

from .endpoints import router, get_health_checker

from .metrics import (
    MetricsCollector,
    get_metrics_collector,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    ACTIVE_TASKS,
    ESCROW_BALANCE,
)

from .monitoring import (
    setup_logging,
    setup_error_tracking,
    TracingContext,
    trace_operation,
)

__all__ = [
    # Health checks
    "HealthChecker",
    "ComponentHealth",
    "HealthStatus",
    "check_database",
    "check_redis",
    "check_x402",
    "check_storage",
    "check_blockchain",
    # Endpoints
    "router",
    "get_health_checker",
    # Metrics
    "MetricsCollector",
    "get_metrics_collector",
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "ACTIVE_TASKS",
    "ESCROW_BALANCE",
    # Monitoring
    "setup_logging",
    "setup_error_tracking",
    "TracingContext",
    "trace_operation",
]
