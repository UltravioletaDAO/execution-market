"""
Alert Rules and Notification System for Chamba.

Production-ready alerting with:
- Configurable alert rules with thresholds
- Multiple severity levels
- Alert state tracking (pending, firing, resolved)
- Notification channels (webhook, email, Slack, PagerDuty)
- Alert grouping and deduplication
- Silencing and maintenance windows
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from abc import ABC, abstractmethod
import httpx
import os

logger = logging.getLogger(__name__)


# =============================================================================
# Alert Types and Severity
# =============================================================================

class AlertSeverity(str, Enum):
    """Alert severity levels following standard patterns."""
    CRITICAL = "critical"    # Requires immediate attention, service down
    WARNING = "warning"      # Degraded service, may escalate
    INFO = "info"           # Notable event, no immediate action needed


class AlertState(str, Enum):
    """Alert state machine."""
    PENDING = "pending"     # Threshold exceeded, waiting for confirmation
    FIRING = "firing"       # Confirmed alert, notifications sent
    RESOLVED = "resolved"   # Condition no longer met


@dataclass
class Alert:
    """An active or historical alert instance."""
    id: str
    rule_name: str
    severity: AlertSeverity
    state: AlertState
    summary: str
    description: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    value: Optional[float] = None
    threshold: Optional[float] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fired_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    last_evaluated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notification_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "state": self.state.value,
            "summary": self.summary,
            "description": self.description,
            "labels": self.labels,
            "annotations": self.annotations,
            "value": self.value,
            "threshold": self.threshold,
            "started_at": self.started_at.isoformat(),
            "fired_at": self.fired_at.isoformat() if self.fired_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "duration_seconds": self._duration_seconds(),
            "notification_count": self.notification_count
        }

    def _duration_seconds(self) -> float:
        """Calculate alert duration."""
        end = self.resolved_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()

    @staticmethod
    def generate_id(rule_name: str, labels: Dict[str, str]) -> str:
        """Generate unique alert ID from rule name and labels."""
        label_str = json.dumps(labels, sort_keys=True)
        content = f"{rule_name}:{label_str}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


# =============================================================================
# Alert Rules
# =============================================================================

@dataclass
class AlertRule:
    """
    Definition of an alert condition.

    Supports:
    - Threshold-based alerting
    - Rate of change alerting
    - Absence detection
    """
    name: str
    severity: AlertSeverity
    summary_template: str
    description_template: str
    condition: Callable[[], Awaitable[Optional[Dict[str, Any]]]]

    # Timing configuration
    for_duration: timedelta = field(default_factory=lambda: timedelta(minutes=1))
    repeat_interval: timedelta = field(default_factory=lambda: timedelta(hours=4))

    # Grouping
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    # State
    enabled: bool = True
    last_evaluation: Optional[datetime] = None


class AlertRuleBuilder:
    """Fluent builder for creating alert rules."""

    def __init__(self, name: str):
        self._name = name
        self._severity = AlertSeverity.WARNING
        self._summary = ""
        self._description = ""
        self._condition: Optional[Callable] = None
        self._for_duration = timedelta(minutes=1)
        self._repeat_interval = timedelta(hours=4)
        self._labels: Dict[str, str] = {}
        self._annotations: Dict[str, str] = {}

    def severity(self, severity: AlertSeverity) -> "AlertRuleBuilder":
        self._severity = severity
        return self

    def summary(self, template: str) -> "AlertRuleBuilder":
        self._summary = template
        return self

    def description(self, template: str) -> "AlertRuleBuilder":
        self._description = template
        return self

    def condition(self, fn: Callable[[], Awaitable[Optional[Dict[str, Any]]]]) -> "AlertRuleBuilder":
        self._condition = fn
        return self

    def for_duration(self, duration: timedelta) -> "AlertRuleBuilder":
        self._for_duration = duration
        return self

    def repeat_interval(self, interval: timedelta) -> "AlertRuleBuilder":
        self._repeat_interval = interval
        return self

    def with_label(self, key: str, value: str) -> "AlertRuleBuilder":
        self._labels[key] = value
        return self

    def with_annotation(self, key: str, value: str) -> "AlertRuleBuilder":
        self._annotations[key] = value
        return self

    def build(self) -> AlertRule:
        if not self._condition:
            raise ValueError("Alert rule must have a condition")
        if not self._summary:
            raise ValueError("Alert rule must have a summary")

        return AlertRule(
            name=self._name,
            severity=self._severity,
            summary_template=self._summary,
            description_template=self._description,
            condition=self._condition,
            for_duration=self._for_duration,
            repeat_interval=self._repeat_interval,
            labels=self._labels,
            annotations=self._annotations
        )


# =============================================================================
# Notification Channels
# =============================================================================

class NotificationChannel(ABC):
    """Abstract base for notification delivery."""

    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """
        Send alert notification.

        Returns True if successful.
        """
        pass

    @abstractmethod
    async def send_resolved(self, alert: Alert) -> bool:
        """Send resolution notification."""
        pass


class WebhookChannel(NotificationChannel):
    """Send alerts via HTTP webhook."""

    def __init__(self, url: str, headers: Dict[str, str] = None, timeout: float = 10.0):
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout

    async def send(self, alert: Alert) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.url,
                    json={
                        "type": "alert",
                        "status": "firing",
                        "alert": alert.to_dict()
                    },
                    headers=self.headers
                )
                return response.status_code < 300
        except Exception as e:
            logger.error("Webhook notification failed: %s", str(e))
            return False

    async def send_resolved(self, alert: Alert) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.url,
                    json={
                        "type": "alert",
                        "status": "resolved",
                        "alert": alert.to_dict()
                    },
                    headers=self.headers
                )
                return response.status_code < 300
        except Exception as e:
            logger.error("Webhook resolution notification failed: %s", str(e))
            return False


class SlackChannel(NotificationChannel):
    """Send alerts to Slack via incoming webhook."""

    SEVERITY_COLORS = {
        AlertSeverity.CRITICAL: "#FF0000",
        AlertSeverity.WARNING: "#FFA500",
        AlertSeverity.INFO: "#0000FF"
    }

    SEVERITY_EMOJI = {
        AlertSeverity.CRITICAL: ":rotating_light:",
        AlertSeverity.WARNING: ":warning:",
        AlertSeverity.INFO: ":information_source:"
    }

    def __init__(self, webhook_url: str, channel: str = None):
        self.webhook_url = webhook_url
        self.channel = channel

    async def send(self, alert: Alert) -> bool:
        emoji = self.SEVERITY_EMOJI.get(alert.severity, ":bell:")
        color = self.SEVERITY_COLORS.get(alert.severity, "#808080")

        payload = {
            "attachments": [{
                "color": color,
                "title": f"{emoji} [{alert.severity.value.upper()}] {alert.summary}",
                "text": alert.description,
                "fields": [
                    {"title": "Rule", "value": alert.rule_name, "short": True},
                    {"title": "State", "value": alert.state.value, "short": True},
                ],
                "footer": "Chamba Alerts",
                "ts": int(alert.started_at.timestamp())
            }]
        }

        if alert.value is not None and alert.threshold is not None:
            payload["attachments"][0]["fields"].extend([
                {"title": "Current Value", "value": f"{alert.value:.2f}", "short": True},
                {"title": "Threshold", "value": f"{alert.threshold:.2f}", "short": True},
            ])

        if self.channel:
            payload["channel"] = self.channel

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.error("Slack notification failed: %s", str(e))
            return False

    async def send_resolved(self, alert: Alert) -> bool:
        duration = alert._duration_seconds()
        duration_str = self._format_duration(duration)

        payload = {
            "attachments": [{
                "color": "#00FF00",
                "title": f":white_check_mark: [RESOLVED] {alert.summary}",
                "text": f"Alert resolved after {duration_str}",
                "fields": [
                    {"title": "Rule", "value": alert.rule_name, "short": True},
                    {"title": "Duration", "value": duration_str, "short": True},
                ],
                "footer": "Chamba Alerts",
                "ts": int(datetime.now(timezone.utc).timestamp())
            }]
        }

        if self.channel:
            payload["channel"] = self.channel

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                return response.status_code == 200
        except Exception as e:
            logger.error("Slack resolution notification failed: %s", str(e))
            return False

    def _format_duration(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"


class PagerDutyChannel(NotificationChannel):
    """Send alerts to PagerDuty."""

    SEVERITY_MAP = {
        AlertSeverity.CRITICAL: "critical",
        AlertSeverity.WARNING: "warning",
        AlertSeverity.INFO: "info"
    }

    def __init__(self, routing_key: str, api_url: str = "https://events.pagerduty.com/v2/enqueue"):
        self.routing_key = routing_key
        self.api_url = api_url

    async def send(self, alert: Alert) -> bool:
        payload = {
            "routing_key": self.routing_key,
            "event_action": "trigger",
            "dedup_key": alert.id,
            "payload": {
                "summary": alert.summary,
                "severity": self.SEVERITY_MAP.get(alert.severity, "warning"),
                "source": "chamba",
                "component": alert.labels.get("component", "api"),
                "custom_details": {
                    "rule_name": alert.rule_name,
                    "description": alert.description,
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "labels": alert.labels
                }
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload)
                return response.status_code == 202
        except Exception as e:
            logger.error("PagerDuty notification failed: %s", str(e))
            return False

    async def send_resolved(self, alert: Alert) -> bool:
        payload = {
            "routing_key": self.routing_key,
            "event_action": "resolve",
            "dedup_key": alert.id
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.api_url, json=payload)
                return response.status_code == 202
        except Exception as e:
            logger.error("PagerDuty resolution failed: %s", str(e))
            return False


class LogChannel(NotificationChannel):
    """Log alerts (useful for development and debugging)."""

    def __init__(self, logger_name: str = "chamba.alerts"):
        self._logger = logging.getLogger(logger_name)

    async def send(self, alert: Alert) -> bool:
        level = {
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.INFO: logging.INFO
        }.get(alert.severity, logging.WARNING)

        self._logger.log(
            level,
            "[ALERT FIRING] %s - %s (value=%s, threshold=%s)",
            alert.rule_name,
            alert.summary,
            alert.value,
            alert.threshold
        )
        return True

    async def send_resolved(self, alert: Alert) -> bool:
        self._logger.info(
            "[ALERT RESOLVED] %s - %s (duration=%.1fs)",
            alert.rule_name,
            alert.summary,
            alert._duration_seconds()
        )
        return True


# =============================================================================
# Alert Manager
# =============================================================================

class AlertManager:
    """
    Central alert management system.

    Features:
    - Rule evaluation on configurable interval
    - Alert state machine (pending -> firing -> resolved)
    - Multi-channel notifications
    - Alert history
    - Silencing/maintenance windows
    """

    def __init__(self, evaluation_interval: float = 30.0):
        self.evaluation_interval = evaluation_interval

        self._rules: Dict[str, AlertRule] = {}
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._history_max_size = 1000

        self._channels: List[NotificationChannel] = []
        self._silences: Dict[str, datetime] = {}  # rule_name -> silence_until

        self._running = False
        self._task: Optional[asyncio.Task] = None

    def add_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._rules[rule.name] = rule
        logger.info("Registered alert rule: %s", rule.name)

    def remove_rule(self, rule_name: str) -> bool:
        """Remove an alert rule."""
        if rule_name in self._rules:
            del self._rules[rule_name]
            return True
        return False

    def add_channel(self, channel: NotificationChannel) -> None:
        """Add a notification channel."""
        self._channels.append(channel)

    def silence_rule(self, rule_name: str, duration: timedelta) -> None:
        """Silence a rule for specified duration."""
        until = datetime.now(timezone.utc) + duration
        self._silences[rule_name] = until
        logger.info("Silenced rule %s until %s", rule_name, until.isoformat())

    def unsilence_rule(self, rule_name: str) -> bool:
        """Remove silence from a rule."""
        if rule_name in self._silences:
            del self._silences[rule_name]
            return True
        return False

    def is_silenced(self, rule_name: str) -> bool:
        """Check if a rule is currently silenced."""
        if rule_name not in self._silences:
            return False
        until = self._silences[rule_name]
        if datetime.now(timezone.utc) > until:
            del self._silences[rule_name]
            return False
        return True

    async def start(self) -> None:
        """Start the alert evaluation loop."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._evaluation_loop())
        logger.info("Alert manager started with %d rules", len(self._rules))

    async def stop(self) -> None:
        """Stop the alert evaluation loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Alert manager stopped")

    async def _evaluation_loop(self) -> None:
        """Main evaluation loop."""
        while self._running:
            try:
                await self._evaluate_all_rules()
            except Exception as e:
                logger.error("Error in alert evaluation: %s", str(e))

            await asyncio.sleep(self.evaluation_interval)

    async def _evaluate_all_rules(self) -> None:
        """Evaluate all registered rules."""
        for rule_name, rule in self._rules.items():
            if not rule.enabled:
                continue

            if self.is_silenced(rule_name):
                continue

            try:
                await self._evaluate_rule(rule)
            except Exception as e:
                logger.error("Error evaluating rule %s: %s", rule_name, str(e))

    async def _evaluate_rule(self, rule: AlertRule) -> None:
        """Evaluate a single rule."""
        now = datetime.now(timezone.utc)
        rule.last_evaluation = now

        # Execute condition
        result = await rule.condition()

        # Generate alert ID
        labels = {**rule.labels}
        if result and "labels" in result:
            labels.update(result["labels"])
        alert_id = Alert.generate_id(rule.name, labels)

        if result is not None:
            # Condition triggered
            value = result.get("value")
            threshold = result.get("threshold")

            if alert_id not in self._active_alerts:
                # New alert - start in pending state
                alert = Alert(
                    id=alert_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    state=AlertState.PENDING,
                    summary=self._render_template(rule.summary_template, result),
                    description=self._render_template(rule.description_template, result),
                    labels=labels,
                    annotations=rule.annotations,
                    value=value,
                    threshold=threshold
                )
                self._active_alerts[alert_id] = alert
                logger.debug("Alert pending: %s", rule.name)

            else:
                # Update existing alert
                alert = self._active_alerts[alert_id]
                alert.last_evaluated = now
                alert.value = value

                # Check if should transition to firing
                if (
                    alert.state == AlertState.PENDING and
                    now - alert.started_at >= rule.for_duration
                ):
                    alert.state = AlertState.FIRING
                    alert.fired_at = now
                    logger.info("Alert firing: %s", rule.name)
                    await self._send_notifications(alert)

                # Check for repeat notifications
                elif (
                    alert.state == AlertState.FIRING and
                    alert.fired_at and
                    now - alert.fired_at >= rule.repeat_interval * (alert.notification_count + 1)
                ):
                    await self._send_notifications(alert)

        else:
            # Condition not triggered
            if alert_id in self._active_alerts:
                alert = self._active_alerts[alert_id]

                if alert.state == AlertState.FIRING:
                    # Resolve firing alert
                    alert.state = AlertState.RESOLVED
                    alert.resolved_at = now
                    logger.info("Alert resolved: %s", rule.name)
                    await self._send_resolution(alert)

                # Remove from active alerts
                del self._active_alerts[alert_id]

                # Add to history
                self._alert_history.append(alert)
                if len(self._alert_history) > self._history_max_size:
                    self._alert_history.pop(0)

    async def _send_notifications(self, alert: Alert) -> None:
        """Send alert to all channels."""
        for channel in self._channels:
            try:
                success = await channel.send(alert)
                if success:
                    alert.notification_count += 1
            except Exception as e:
                logger.error("Notification channel error: %s", str(e))

    async def _send_resolution(self, alert: Alert) -> None:
        """Send resolution to all channels."""
        for channel in self._channels:
            try:
                await channel.send_resolved(alert)
            except Exception as e:
                logger.error("Resolution notification error: %s", str(e))

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render a template string with context."""
        try:
            return template.format(**context)
        except KeyError:
            return template

    # =========================================================================
    # API Methods
    # =========================================================================

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        return [alert.to_dict() for alert in self._active_alerts.values()]

    def get_firing_alerts(self) -> List[Dict[str, Any]]:
        """Get only firing alerts."""
        return [
            alert.to_dict()
            for alert in self._active_alerts.values()
            if alert.state == AlertState.FIRING
        ]

    def get_alert_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alert history."""
        return [alert.to_dict() for alert in self._alert_history[-limit:]]

    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all registered rules."""
        return [
            {
                "name": rule.name,
                "severity": rule.severity.value,
                "enabled": rule.enabled,
                "silenced": self.is_silenced(rule.name),
                "for_duration_seconds": rule.for_duration.total_seconds(),
                "last_evaluation": rule.last_evaluation.isoformat() if rule.last_evaluation else None
            }
            for rule in self._rules.values()
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get alert system summary."""
        firing = [a for a in self._active_alerts.values() if a.state == AlertState.FIRING]
        pending = [a for a in self._active_alerts.values() if a.state == AlertState.PENDING]

        return {
            "status": "critical" if any(a.severity == AlertSeverity.CRITICAL for a in firing) else (
                "warning" if firing else "ok"
            ),
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "silenced_rules": len(self._silences),
            "alerts": {
                "firing": len(firing),
                "pending": len(pending),
                "firing_by_severity": {
                    "critical": sum(1 for a in firing if a.severity == AlertSeverity.CRITICAL),
                    "warning": sum(1 for a in firing if a.severity == AlertSeverity.WARNING),
                    "info": sum(1 for a in firing if a.severity == AlertSeverity.INFO)
                }
            },
            "history_size": len(self._alert_history),
            "channels": len(self._channels)
        }


# =============================================================================
# Default Alert Rules
# =============================================================================

def create_default_rules() -> List[AlertRule]:
    """
    Create default alert rules for Chamba.

    Returns list of AlertRule objects to register with AlertManager.
    """
    rules = []

    # Import metrics for conditions
    from .metrics import get_metrics

    # -------------------------------------------------------------------------
    # Error Rate Alerts
    # -------------------------------------------------------------------------

    async def high_error_rate_condition() -> Optional[Dict[str, Any]]:
        """Check if API error rate exceeds 5%."""
        metrics = get_metrics()
        total = sum(metrics.api_requests.get_all().values())
        errors = sum(metrics.api_errors.get_all().values())

        if total < 100:  # Not enough data
            return None

        error_rate = (errors / total) * 100
        if error_rate > 5.0:
            return {
                "value": error_rate,
                "threshold": 5.0,
                "total_requests": total,
                "total_errors": errors
            }
        return None

    rules.append(
        AlertRuleBuilder("high_error_rate")
        .severity(AlertSeverity.WARNING)
        .summary("High API error rate: {value:.1f}%")
        .description("API error rate has exceeded 5%. Total requests: {total_requests}, errors: {total_errors}")
        .condition(high_error_rate_condition)
        .for_duration(timedelta(minutes=2))
        .with_label("component", "api")
        .build()
    )

    async def critical_error_rate_condition() -> Optional[Dict[str, Any]]:
        """Check if API error rate exceeds 20%."""
        metrics = get_metrics()
        total = sum(metrics.api_requests.get_all().values())
        errors = sum(metrics.api_errors.get_all().values())

        if total < 50:
            return None

        error_rate = (errors / total) * 100
        if error_rate > 20.0:
            return {
                "value": error_rate,
                "threshold": 20.0,
                "total_requests": total,
                "total_errors": errors
            }
        return None

    rules.append(
        AlertRuleBuilder("critical_error_rate")
        .severity(AlertSeverity.CRITICAL)
        .summary("Critical API error rate: {value:.1f}%")
        .description("API error rate has exceeded 20%. Service may be down.")
        .condition(critical_error_rate_condition)
        .for_duration(timedelta(minutes=1))
        .with_label("component", "api")
        .build()
    )

    # -------------------------------------------------------------------------
    # Response Time Alerts
    # -------------------------------------------------------------------------

    async def slow_response_time_condition() -> Optional[Dict[str, Any]]:
        """Check if p95 response time exceeds 2 seconds."""
        metrics = get_metrics()
        p95 = metrics.api_latency.get_percentile(0.95)

        if p95 is None:
            return None

        if p95 > 2.0:
            return {
                "value": p95,
                "threshold": 2.0,
                "percentile": "p95"
            }
        return None

    rules.append(
        AlertRuleBuilder("slow_response_time")
        .severity(AlertSeverity.WARNING)
        .summary("Slow API response times: p95 = {value:.2f}s")
        .description("95th percentile response time exceeds 2 seconds. Users may experience slowness.")
        .condition(slow_response_time_condition)
        .for_duration(timedelta(minutes=5))
        .with_label("component", "api")
        .build()
    )

    # -------------------------------------------------------------------------
    # Payment Alerts
    # -------------------------------------------------------------------------

    async def payment_failure_condition() -> Optional[Dict[str, Any]]:
        """Check if payment failure rate is high."""
        metrics = get_metrics()
        total = sum(metrics.payments_processed.get_all().values())
        failures = sum(metrics.payment_failures.get_all().values())

        if total < 10:
            return None

        failure_rate = (failures / total) * 100
        if failure_rate > 10.0:
            return {
                "value": failure_rate,
                "threshold": 10.0,
                "total_payments": total,
                "failures": failures
            }
        return None

    rules.append(
        AlertRuleBuilder("high_payment_failure_rate")
        .severity(AlertSeverity.CRITICAL)
        .summary("High payment failure rate: {value:.1f}%")
        .description("Payment failure rate exceeds 10%. Workers may not be receiving payments.")
        .condition(payment_failure_condition)
        .for_duration(timedelta(minutes=5))
        .with_label("component", "payments")
        .build()
    )

    # -------------------------------------------------------------------------
    # Worker Availability Alerts
    # -------------------------------------------------------------------------

    async def low_worker_availability_condition() -> Optional[Dict[str, Any]]:
        """Check if worker availability is low."""
        metrics = get_metrics()
        active_workers = sum(metrics.active_workers.get_all().values())

        # Threshold: less than 5 active workers
        if active_workers < 5:
            return {
                "value": active_workers,
                "threshold": 5,
                "metric": "active_workers"
            }
        return None

    rules.append(
        AlertRuleBuilder("low_worker_availability")
        .severity(AlertSeverity.WARNING)
        .summary("Low worker availability: {value:.0f} workers")
        .description("Less than 5 workers are currently active. Task completion may be delayed.")
        .condition(low_worker_availability_condition)
        .for_duration(timedelta(minutes=10))
        .with_label("component", "workers")
        .build()
    )

    # -------------------------------------------------------------------------
    # System Health Alerts
    # -------------------------------------------------------------------------

    async def health_degraded_condition() -> Optional[Dict[str, Any]]:
        """Check system health from health checker."""
        try:
            from ..api.health import get_health_checker, HealthStatus
            checker = get_health_checker()
            health = await checker.check_all()

            if health.status == HealthStatus.DEGRADED:
                unhealthy = [
                    name for name, comp in health.components.items()
                    if comp.status != HealthStatus.HEALTHY
                ]
                return {
                    "value": len(unhealthy),
                    "threshold": 0,
                    "unhealthy_components": ", ".join(unhealthy)
                }
        except Exception:
            pass
        return None

    rules.append(
        AlertRuleBuilder("system_health_degraded")
        .severity(AlertSeverity.WARNING)
        .summary("System health degraded: {value:.0f} component(s) affected")
        .description("System is in degraded state. Affected components: {unhealthy_components}")
        .condition(health_degraded_condition)
        .for_duration(timedelta(minutes=3))
        .with_label("component", "system")
        .build()
    )

    async def health_unhealthy_condition() -> Optional[Dict[str, Any]]:
        """Check if system is unhealthy."""
        try:
            from ..api.health import get_health_checker, HealthStatus
            checker = get_health_checker()
            health = await checker.check_all()

            if health.status == HealthStatus.UNHEALTHY:
                critical = [
                    name for name, comp in health.components.items()
                    if comp.status == HealthStatus.UNHEALTHY
                ]
                return {
                    "value": 1,
                    "threshold": 0,
                    "critical_components": ", ".join(critical)
                }
        except Exception:
            pass
        return None

    rules.append(
        AlertRuleBuilder("system_health_critical")
        .severity(AlertSeverity.CRITICAL)
        .summary("System health critical")
        .description("System is in unhealthy state. Critical components: {critical_components}")
        .condition(health_unhealthy_condition)
        .for_duration(timedelta(seconds=30))
        .with_label("component", "system")
        .build()
    )

    # -------------------------------------------------------------------------
    # Task Processing Alerts
    # -------------------------------------------------------------------------

    async def task_completion_stalled_condition() -> Optional[Dict[str, Any]]:
        """Check if no tasks have been completed recently."""
        metrics = get_metrics()
        completed = sum(metrics.tasks_completed.get_all().values())
        active = sum(metrics.active_tasks.get_all().values())

        # Alert if there are active tasks but no completions and activity is expected
        if active > 10 and completed == 0:
            return {
                "value": active,
                "threshold": 10,
                "completed": completed
            }
        return None

    rules.append(
        AlertRuleBuilder("task_completion_stalled")
        .severity(AlertSeverity.WARNING)
        .summary("Task completion may be stalled: {value:.0f} active tasks, 0 completed")
        .description("There are active tasks but no completions recorded. Verify task processing is working.")
        .condition(task_completion_stalled_condition)
        .for_duration(timedelta(minutes=30))
        .with_label("component", "tasks")
        .build()
    )

    return rules


# =============================================================================
# Global Instance and FastAPI Routes
# =============================================================================

_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """Get or create the global alert manager."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()

        # Add default log channel
        _alert_manager.add_channel(LogChannel())

        # Add Slack if configured
        slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        if slack_webhook:
            _alert_manager.add_channel(SlackChannel(slack_webhook))

        # Add PagerDuty if configured
        pagerduty_key = os.getenv("PAGERDUTY_ROUTING_KEY")
        if pagerduty_key:
            _alert_manager.add_channel(PagerDutyChannel(pagerduty_key))

        # Register default rules
        for rule in create_default_rules():
            _alert_manager.add_rule(rule)

    return _alert_manager


async def start_alert_manager() -> None:
    """Start the global alert manager."""
    manager = get_alert_manager()
    await manager.start()


async def stop_alert_manager() -> None:
    """Stop the global alert manager."""
    global _alert_manager
    if _alert_manager:
        await _alert_manager.stop()


# FastAPI Router
from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel

alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])


@alerts_router.get("/")
async def list_alerts(firing_only: bool = False) -> Dict[str, Any]:
    """
    List all active alerts.

    Args:
        firing_only: If true, only return firing alerts
    """
    manager = get_alert_manager()
    if firing_only:
        return {"alerts": manager.get_firing_alerts()}
    return {"alerts": manager.get_active_alerts()}


@alerts_router.get("/history")
async def alert_history(limit: int = 100) -> Dict[str, Any]:
    """Get recent alert history."""
    manager = get_alert_manager()
    return {"history": manager.get_alert_history(limit)}


@alerts_router.get("/rules")
async def list_rules() -> Dict[str, Any]:
    """List all alert rules."""
    manager = get_alert_manager()
    return {"rules": manager.get_rules()}


@alerts_router.get("/summary")
async def alert_summary() -> Dict[str, Any]:
    """Get alert system summary."""
    manager = get_alert_manager()
    return manager.get_summary()


class SilenceRequest(BaseModel):
    duration_minutes: int = 60


@alerts_router.post("/rules/{rule_name}/silence")
async def silence_rule(rule_name: str, request: SilenceRequest) -> Dict[str, Any]:
    """Silence a rule for specified duration."""
    manager = get_alert_manager()

    if rule_name not in manager._rules:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_name}")

    duration = timedelta(minutes=request.duration_minutes)
    manager.silence_rule(rule_name, duration)

    return {
        "status": "silenced",
        "rule": rule_name,
        "duration_minutes": request.duration_minutes,
        "until": (datetime.now(timezone.utc) + duration).isoformat()
    }


@alerts_router.delete("/rules/{rule_name}/silence")
async def unsilence_rule(rule_name: str) -> Dict[str, Any]:
    """Remove silence from a rule."""
    manager = get_alert_manager()

    if manager.unsilence_rule(rule_name):
        return {"status": "unsilenced", "rule": rule_name}
    else:
        return {"status": "not_silenced", "rule": rule_name}


@alerts_router.post("/test")
async def test_alert() -> Dict[str, Any]:
    """
    Send a test alert to all channels.

    Useful for verifying notification configuration.
    """
    manager = get_alert_manager()

    test_alert = Alert(
        id="test_" + str(int(time.time())),
        rule_name="test_alert",
        severity=AlertSeverity.INFO,
        state=AlertState.FIRING,
        summary="Test Alert - Ignore",
        description="This is a test alert to verify notification channels are working.",
        labels={"component": "test"},
        value=100,
        threshold=50
    )

    for channel in manager._channels:
        try:
            await channel.send(test_alert)
        except Exception as e:
            logger.error("Test alert failed for channel: %s", str(e))

    return {
        "status": "sent",
        "channels": len(manager._channels),
        "alert_id": test_alert.id
    }
