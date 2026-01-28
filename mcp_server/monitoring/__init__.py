"""
Monitoring Module for Chamba.

Provides comprehensive monitoring infrastructure including:
- Metrics collection (Prometheus-compatible)
- Health checks
- Alerting with multiple notification channels

Usage:
    from monitoring import get_metrics, get_alert_manager, MetricsMiddleware

    # Add middleware to FastAPI app
    app.add_middleware(MetricsMiddleware)

    # Record custom metrics
    metrics = get_metrics()
    metrics.record_task_created("verification", 50.0)

    # Start alerting
    from monitoring.alerts import start_alert_manager
    await start_alert_manager()
"""

from .metrics import (
    # Metric types
    Counter,
    Gauge,
    Histogram,
    Summary,
    MetricValue,
    MetricType,
    # Registry
    MetricsRegistry,
    get_metrics,
    # Middleware
    MetricsMiddleware,
    # Router
    metrics_router,
)

from .alerts import (
    # Alert types
    Alert,
    AlertRule,
    AlertRuleBuilder,
    AlertSeverity,
    AlertState,
    # Channels
    NotificationChannel,
    WebhookChannel,
    SlackChannel,
    PagerDutyChannel,
    LogChannel,
    # Manager
    AlertManager,
    get_alert_manager,
    start_alert_manager,
    stop_alert_manager,
    create_default_rules,
    # Router
    alerts_router,
)

__all__ = [
    # Metrics
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "MetricValue",
    "MetricType",
    "MetricsRegistry",
    "get_metrics",
    "MetricsMiddleware",
    "metrics_router",
    # Alerts
    "Alert",
    "AlertRule",
    "AlertRuleBuilder",
    "AlertSeverity",
    "AlertState",
    "NotificationChannel",
    "WebhookChannel",
    "SlackChannel",
    "PagerDutyChannel",
    "LogChannel",
    "AlertManager",
    "get_alert_manager",
    "start_alert_manager",
    "stop_alert_manager",
    "create_default_rules",
    "alerts_router",
]
