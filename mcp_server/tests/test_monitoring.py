"""
Tests for the monitoring/alerts module.

Covers:
- AlertSeverity and AlertState enums
- Alert model (to_dict, generate_id, duration)
- AlertRule and AlertRuleBuilder
- Edge cases (deduplication, state transitions)
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta

import pytest

from mcp_server.monitoring.alerts import (
    AlertSeverity,
    AlertState,
    Alert,
    AlertRule,
    AlertRuleBuilder,
)


# ═══════════════════════════════════════════════════════════
# Alert Enums
# ═══════════════════════════════════════════════════════════

class TestAlertEnums:
    """Tests for AlertSeverity and AlertState enums."""

    def test_severity_values(self):
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.INFO.value == "info"

    def test_state_values(self):
        assert AlertState.PENDING.value == "pending"
        assert AlertState.FIRING.value == "firing"
        assert AlertState.RESOLVED.value == "resolved"


# ═══════════════════════════════════════════════════════════
# Alert Model
# ═══════════════════════════════════════════════════════════

class TestAlertModel:
    """Tests for the Alert dataclass."""

    def _make_alert(self, **kw):
        defaults = dict(
            id="alert_001",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            state=AlertState.PENDING,
            summary="Test alert",
            description="Test description",
        )
        defaults.update(kw)
        return Alert(**defaults)

    def test_to_dict_keys(self):
        alert = self._make_alert()
        d = alert.to_dict()
        assert "id" in d
        assert "rule_name" in d
        assert "severity" in d
        assert "state" in d
        assert "duration_seconds" in d
        assert d["severity"] == "warning"

    def test_to_dict_with_fired_resolved(self):
        now = datetime.now(timezone.utc)
        alert = self._make_alert(
            state=AlertState.RESOLVED,
            fired_at=now - timedelta(hours=1),
            resolved_at=now,
        )
        d = alert.to_dict()
        assert d["fired_at"] is not None
        assert d["resolved_at"] is not None

    def test_duration_pending(self):
        alert = self._make_alert(
            started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        duration = alert._duration_seconds()
        assert 280 < duration < 320  # roughly 5 minutes

    def test_duration_resolved(self):
        start = datetime.now(timezone.utc) - timedelta(hours=2)
        end = datetime.now(timezone.utc) - timedelta(hours=1)
        alert = self._make_alert(
            started_at=start,
            resolved_at=end,
        )
        duration = alert._duration_seconds()
        assert 3500 < duration < 3700  # ~1 hour

    def test_generate_id_deterministic(self):
        id1 = Alert.generate_id("cpu_high", {"host": "web-1"})
        id2 = Alert.generate_id("cpu_high", {"host": "web-1"})
        assert id1 == id2

    def test_generate_id_different_labels(self):
        id1 = Alert.generate_id("cpu_high", {"host": "web-1"})
        id2 = Alert.generate_id("cpu_high", {"host": "web-2"})
        assert id1 != id2

    def test_generate_id_different_rules(self):
        id1 = Alert.generate_id("cpu_high", {"host": "web-1"})
        id2 = Alert.generate_id("mem_high", {"host": "web-1"})
        assert id1 != id2

    def test_alert_labels_and_annotations(self):
        alert = self._make_alert(
            labels={"host": "prod-1", "service": "api"},
            annotations={"runbook": "https://wiki/alert"},
        )
        d = alert.to_dict()
        assert d["labels"]["host"] == "prod-1"
        assert d["annotations"]["runbook"] == "https://wiki/alert"

    def test_alert_value_and_threshold(self):
        alert = self._make_alert(value=95.5, threshold=90.0)
        d = alert.to_dict()
        assert d["value"] == 95.5
        assert d["threshold"] == 90.0

    def test_notification_count_default(self):
        alert = self._make_alert()
        assert alert.notification_count == 0


# ═══════════════════════════════════════════════════════════
# AlertRuleBuilder
# ═══════════════════════════════════════════════════════════

class TestAlertRuleBuilder:
    """Tests for the fluent AlertRuleBuilder."""

    @staticmethod
    async def _dummy_condition():
        return {"value": 42}

    def test_build_minimal(self):
        rule = (
            AlertRuleBuilder("test")
            .summary("Test alert")
            .condition(self._dummy_condition)
            .build()
        )
        assert rule.name == "test"
        assert rule.severity == AlertSeverity.WARNING  # default
        assert rule.enabled is True

    def test_build_full(self):
        rule = (
            AlertRuleBuilder("cpu_high")
            .severity(AlertSeverity.CRITICAL)
            .summary("CPU usage is {{value}}%")
            .description("CPU on {{host}} exceeded threshold")
            .condition(self._dummy_condition)
            .for_duration(timedelta(minutes=5))
            .repeat_interval(timedelta(hours=1))
            .with_label("host", "prod-1")
            .with_annotation("runbook", "https://wiki/cpu")
            .build()
        )
        assert rule.severity == AlertSeverity.CRITICAL
        assert rule.for_duration == timedelta(minutes=5)
        assert rule.labels["host"] == "prod-1"

    def test_build_no_condition_raises(self):
        with pytest.raises(ValueError, match="condition"):
            AlertRuleBuilder("test").summary("test").build()

    def test_build_no_summary_raises(self):
        with pytest.raises(ValueError, match="summary"):
            AlertRuleBuilder("test").condition(self._dummy_condition).build()

    def test_builder_chaining(self):
        builder = AlertRuleBuilder("test")
        assert builder.severity(AlertSeverity.INFO) is builder
        assert builder.summary("s") is builder
        assert builder.description("d") is builder
        assert builder.with_label("k", "v") is builder
