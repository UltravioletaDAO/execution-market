"""
Tests for Fraud Detection Module (NOW-109, NOW-110)

Tests multi-device detection, wash trading, collusion, and risk scoring.
"""

import pytest
from datetime import datetime, timezone, timedelta

from ..security.fraud_detection import (
    FraudDetector,
    FraudSignal,
    FraudAlert,
    RiskLevel,
    FraudConfig,
    EntityProfile,
    TaskRecord,
)


@pytest.fixture
def detector() -> FraudDetector:
    """Create a fresh fraud detector for each test."""
    return FraudDetector()


@pytest.fixture
def strict_config() -> FraudConfig:
    """Create a strict config for testing edge cases."""
    return FraudConfig(
        max_devices_per_worker=2,
        instant_approval_seconds=10.0,
        inflated_bounty_multiplier=2.0,
        suspicious_pairing_count=2,
    )


class TestMultiDeviceDetection:
    """Tests for NOW-109: Multi-device fraud detection."""

    def test_single_device_no_alert(self, detector: FraudDetector):
        """Single device usage should not trigger alert."""
        alert = detector.check_multi_device(
            worker_id="worker_1",
            device_id="device_a",
            ip_address="1.2.3.4",
        )
        assert alert is None

    def test_multiple_devices_triggers_alert(self, detector: FraudDetector):
        """Using more than max devices should trigger alert."""
        config = FraudConfig(max_devices_per_worker=2)
        detector = FraudDetector(config)

        # First two devices are fine
        assert detector.check_multi_device("worker_1", "device_a") is None
        assert detector.check_multi_device("worker_1", "device_b") is None

        # Third device triggers alert
        alert = detector.check_multi_device("worker_1", "device_c")
        assert alert is not None
        assert alert.signal == FraudSignal.MULTI_DEVICE
        assert alert.risk_level == RiskLevel.HIGH
        assert "worker_1" in alert.entities
        assert alert.evidence["device_count"] == 3

    def test_same_device_no_additional_count(self, detector: FraudDetector):
        """Using same device multiple times should not increase count."""
        detector.check_multi_device("worker_1", "device_a")
        detector.check_multi_device("worker_1", "device_a")
        detector.check_multi_device("worker_1", "device_a")

        profile = detector.get_entity_profile("worker_1")
        assert profile is not None
        assert profile.device_count == 1

    def test_device_farm_detection(self, detector: FraudDetector):
        """Same device used by multiple workers should trigger device farm alert."""
        # First worker uses device
        alert1 = detector.check_multi_device("worker_1", "shared_device")
        assert alert1 is None

        # Second worker uses same device - CRITICAL!
        alert2 = detector.check_multi_device("worker_2", "shared_device")
        assert alert2 is not None
        assert alert2.signal == FraudSignal.DEVICE_FARM
        assert alert2.risk_level == RiskLevel.CRITICAL
        assert "worker_1" in alert2.entities
        assert "worker_2" in alert2.entities

    def test_device_fingerprint_tracking(self, detector: FraudDetector):
        """Device fingerprint should combine device_id with user_agent."""
        detector.check_multi_device(
            worker_id="worker_1",
            device_id="device_a",
            user_agent="Mozilla/5.0 Chrome",
            screen_res="1920x1080",
        )

        profile = detector.get_entity_profile("worker_1")
        assert profile is not None
        assert len(profile.devices) == 1
        device = list(profile.devices.values())[0]
        assert device.device_fingerprint is not None
        assert len(device.device_fingerprint) == 16


class TestWashTradingDetection:
    """Tests for NOW-110: Wash trading detection."""

    def test_same_ip_agent_worker_critical(self, detector: FraudDetector):
        """Same IP for agent and worker should be CRITICAL."""
        alerts = detector.check_wash_trading(
            task_id="task_1",
            agent_id="agent_1",
            worker_id="worker_1",
            agent_ip="192.168.1.1",
            worker_ip="192.168.1.1",  # Same IP!
            approval_time_seconds=60.0,
            bounty=10.0,
            avg_bounty=10.0,
        )

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.signal == FraudSignal.SAME_IP_AGENT_WORKER
        assert alert.risk_level == RiskLevel.CRITICAL
        assert alert.evidence["shared_ip"] == "192.168.1.1"

    def test_instant_approval_high_risk(self, detector: FraudDetector):
        """Very fast approval should be HIGH risk."""
        alerts = detector.check_wash_trading(
            task_id="task_1",
            agent_id="agent_1",
            worker_id="worker_1",
            agent_ip="1.1.1.1",
            worker_ip="2.2.2.2",
            approval_time_seconds=5.0,  # Very fast!
            bounty=10.0,
            avg_bounty=10.0,
        )

        instant_alerts = [a for a in alerts if a.signal == FraudSignal.INSTANT_APPROVAL]
        assert len(instant_alerts) == 1
        assert instant_alerts[0].risk_level == RiskLevel.HIGH

    def test_instant_approval_medium_risk(self, detector: FraudDetector):
        """Fast but not instant approval should be MEDIUM risk."""
        alerts = detector.check_wash_trading(
            task_id="task_1",
            agent_id="agent_1",
            worker_id="worker_1",
            agent_ip="1.1.1.1",
            worker_ip="2.2.2.2",
            approval_time_seconds=20.0,  # Fast but reviewed
            bounty=10.0,
            avg_bounty=10.0,
        )

        instant_alerts = [a for a in alerts if a.signal == FraudSignal.INSTANT_APPROVAL]
        assert len(instant_alerts) == 1
        assert instant_alerts[0].risk_level == RiskLevel.MEDIUM

    def test_inflated_bounty_detection(self, detector: FraudDetector):
        """Bounty much higher than average should trigger alert."""
        alerts = detector.check_wash_trading(
            task_id="task_1",
            agent_id="agent_1",
            worker_id="worker_1",
            agent_ip="1.1.1.1",
            worker_ip="2.2.2.2",
            approval_time_seconds=120.0,
            bounty=100.0,  # 5x average!
            avg_bounty=20.0,
        )

        inflated_alerts = [a for a in alerts if a.signal == FraudSignal.INFLATED_BOUNTY]
        assert len(inflated_alerts) == 1
        assert inflated_alerts[0].risk_level == RiskLevel.HIGH
        assert inflated_alerts[0].evidence["multiplier"] == 5.0

    def test_rapid_completion_detection(self, detector: FraudDetector):
        """Very fast task completion should trigger alert."""
        alerts = detector.check_wash_trading(
            task_id="task_1",
            agent_id="agent_1",
            worker_id="worker_1",
            agent_ip="1.1.1.1",
            worker_ip="2.2.2.2",
            approval_time_seconds=120.0,
            bounty=10.0,
            avg_bounty=10.0,
            completion_time_minutes=2.0,  # Very fast!
        )

        rapid_alerts = [a for a in alerts if a.signal == FraudSignal.RAPID_COMPLETION]
        assert len(rapid_alerts) == 1

    def test_multiple_wash_trading_signals(self, detector: FraudDetector):
        """Multiple wash trading signals should all be detected."""
        alerts = detector.check_wash_trading(
            task_id="task_1",
            agent_id="agent_1",
            worker_id="worker_1",
            agent_ip="192.168.1.1",
            worker_ip="192.168.1.1",  # Same IP!
            approval_time_seconds=5.0,  # Instant!
            bounty=100.0,  # 10x average!
            avg_bounty=10.0,
            completion_time_minutes=1.0,  # Rapid!
        )

        signals = {a.signal for a in alerts}
        assert FraudSignal.SAME_IP_AGENT_WORKER in signals
        assert FraudSignal.INSTANT_APPROVAL in signals
        assert FraudSignal.INFLATED_BOUNTY in signals
        assert FraudSignal.RAPID_COMPLETION in signals

    def test_normal_transaction_no_alerts(self, detector: FraudDetector):
        """Normal transaction should not trigger alerts."""
        alerts = detector.check_wash_trading(
            task_id="task_1",
            agent_id="agent_1",
            worker_id="worker_1",
            agent_ip="1.1.1.1",
            worker_ip="2.2.2.2",
            approval_time_seconds=300.0,  # 5 min review
            bounty=15.0,
            avg_bounty=10.0,  # 1.5x is fine
            completion_time_minutes=30.0,  # Normal time
        )

        assert len(alerts) == 0


class TestCollusionDetection:
    """Tests for collusion pattern detection."""

    def test_repeated_pairing_detection(self):
        """Same agent-worker pair too many times should trigger alert."""
        config = FraudConfig(suspicious_pairing_count=2)
        detector = FraudDetector(config)

        # First pairing is fine
        detector.check_wash_trading(
            task_id="task_1",
            agent_id="agent_1",
            worker_id="worker_1",
            agent_ip="1.1.1.1",
            worker_ip="2.2.2.2",
            approval_time_seconds=300.0,
            bounty=10.0,
            avg_bounty=10.0,
        )
        alert1 = detector.check_collusion("agent_1", "worker_1")
        assert alert1 is None

        # Second pairing triggers alert
        detector.check_wash_trading(
            task_id="task_2",
            agent_id="agent_1",
            worker_id="worker_1",
            agent_ip="1.1.1.1",
            worker_ip="2.2.2.2",
            approval_time_seconds=300.0,
            bounty=10.0,
            avg_bounty=10.0,
        )
        alert2 = detector.check_collusion("agent_1", "worker_1", "task_2")
        assert alert2 is not None
        assert alert2.signal == FraudSignal.REPEATED_PAIRING

    def test_wallet_clustering_detection(self, detector: FraudDetector):
        """Same wallet used by agent and worker should be CRITICAL."""
        # Register wallet for agent
        detector.register_wallet("agent_1", "0xABC123", "agent")

        # Try to register same wallet for worker
        alert = detector.register_wallet("worker_1", "0xABC123", "worker")

        assert alert is not None
        assert alert.signal == FraudSignal.WALLET_CLUSTERING
        assert alert.risk_level == RiskLevel.CRITICAL

    def test_wallet_clustering_via_collusion_check(self, detector: FraudDetector):
        """Collusion check should detect shared wallets."""
        detector.register_wallet("agent_1", "0xWALLET", "agent")
        detector.register_wallet("worker_1", "0xWALLET", "worker")

        alert = detector.check_collusion("agent_1", "worker_1")
        assert alert is not None
        assert alert.signal == FraudSignal.WALLET_CLUSTERING


class TestNewAccountRisk:
    """Tests for new account monitoring."""

    def test_new_account_high_value_alert(self, detector: FraudDetector):
        """New account attempting high-value task should alert."""
        created_at = datetime.now(timezone.utc) - timedelta(days=2)

        alert = detector.check_new_account_risk(
            worker_id="worker_1",
            task_value=100.0,  # Above $50 threshold
            account_created_at=created_at,
        )

        assert alert is not None
        assert alert.signal == FraudSignal.NEW_ACCOUNT_HIGH_VALUE
        assert alert.evidence["account_age_days"] == 2

    def test_established_account_high_value_ok(self, detector: FraudDetector):
        """Established account with high-value task should be fine."""
        created_at = datetime.now(timezone.utc) - timedelta(days=30)

        alert = detector.check_new_account_risk(
            worker_id="worker_1",
            task_value=100.0,
            account_created_at=created_at,
        )

        assert alert is None

    def test_new_account_low_value_ok(self, detector: FraudDetector):
        """New account with low-value task should be fine."""
        created_at = datetime.now(timezone.utc) - timedelta(days=2)

        alert = detector.check_new_account_risk(
            worker_id="worker_1",
            task_value=10.0,  # Below $50 threshold
            account_created_at=created_at,
        )

        assert alert is None


class TestRiskScoring:
    """Tests for risk score calculation."""

    def test_clean_profile_low_risk(self, detector: FraudDetector):
        """Clean profile should have LOW risk."""
        detector.check_multi_device("worker_1", "device_a")

        level, reasons, score = detector.get_risk_score("worker_1")

        assert level == RiskLevel.LOW
        assert score < 0.25

    def test_multiple_alerts_increase_risk(self, detector: FraudDetector):
        """Multiple unresolved alerts should increase risk."""
        # Trigger multiple alerts
        config = FraudConfig(max_devices_per_worker=1)
        detector = FraudDetector(config)

        detector.check_multi_device("worker_1", "device_a")
        detector.check_multi_device("worker_1", "device_b")  # Alert

        detector.check_new_account_risk(
            "worker_1",
            100.0,
            datetime.now(timezone.utc) - timedelta(days=2)
        )  # Another alert

        level, reasons, score = detector.get_risk_score("worker_1")

        assert level in [RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert len(reasons) > 0

    def test_resolved_alerts_dont_count(self, detector: FraudDetector):
        """Resolved alerts should not affect risk score."""
        config = FraudConfig(max_devices_per_worker=1)
        detector = FraudDetector(config)

        detector.check_multi_device("worker_1", "device_a")
        alert = detector.check_multi_device("worker_1", "device_b")

        # Resolve the alert
        detector.resolve_alert(alert.id, "False positive", "admin")

        level, reasons, score = detector.get_risk_score("worker_1")

        # Should still have device concern but no unresolved alert
        assert "Unresolved" not in " ".join(reasons)

    def test_unknown_entity_low_risk(self, detector: FraudDetector):
        """Unknown entity should return LOW risk."""
        level, reasons, score = detector.get_risk_score("unknown_worker")

        assert level == RiskLevel.LOW
        assert score == 0.0


class TestAlertManagement:
    """Tests for alert management operations."""

    def test_resolve_alert(self, detector: FraudDetector):
        """Should be able to resolve alerts."""
        config = FraudConfig(max_devices_per_worker=1)
        detector = FraudDetector(config)

        detector.check_multi_device("worker_1", "device_a")
        alert = detector.check_multi_device("worker_1", "device_b")

        success = detector.resolve_alert(
            alert.id,
            "Legitimate use - user has multiple phones",
            "admin_123"
        )

        assert success is True
        assert alert.resolved is True
        assert alert.resolution == "Legitimate use - user has multiple phones"
        assert alert.resolved_by == "admin_123"
        assert alert.resolved_at is not None

    def test_resolve_nonexistent_alert(self, detector: FraudDetector):
        """Resolving nonexistent alert should return False."""
        success = detector.resolve_alert("fake_alert_id", "test", "admin")
        assert success is False

    def test_get_alerts_filtering(self, detector: FraudDetector):
        """Should filter alerts by criteria."""
        config = FraudConfig(max_devices_per_worker=1)
        detector = FraudDetector(config)

        # Create alerts for different workers
        detector.check_multi_device("worker_1", "device_a")
        detector.check_multi_device("worker_1", "device_b")

        detector.check_multi_device("worker_2", "device_c")
        detector.check_multi_device("worker_2", "device_d")

        # Filter by entity
        w1_alerts = detector.get_alerts(entity_id="worker_1")
        assert len(w1_alerts) == 1
        assert "worker_1" in w1_alerts[0].entities

        # Filter by risk level
        high_alerts = detector.get_alerts(risk_level=RiskLevel.HIGH)
        assert all(a.risk_level == RiskLevel.HIGH for a in high_alerts)

    def test_get_alerts_excludes_resolved(self, detector: FraudDetector):
        """By default should exclude resolved alerts."""
        config = FraudConfig(max_devices_per_worker=1)
        detector = FraudDetector(config)

        detector.check_multi_device("worker_1", "device_a")
        alert = detector.check_multi_device("worker_1", "device_b")
        detector.resolve_alert(alert.id, "resolved", "admin")

        alerts = detector.get_alerts()
        assert len(alerts) == 0

        # Include resolved
        all_alerts = detector.get_alerts(include_resolved=True)
        assert len(all_alerts) == 1


class TestBatchAnalysis:
    """Tests for batch task analysis."""

    def test_coordinated_timing_detection(self, detector: FraudDetector):
        """Tasks created too close together should trigger alert."""
        now = datetime.now(timezone.utc)

        tasks = [
            TaskRecord(
                task_id=f"task_{i}",
                agent_id="agent_1",
                worker_id=None,
                bounty_usd=10.0,
                created_at=now + timedelta(seconds=i * 10),  # 10 sec apart
            )
            for i in range(5)
        ]

        alerts = detector.analyze_task_batch(tasks)

        coord_alerts = [a for a in alerts if a.signal == FraudSignal.COORDINATED_TIMING]
        assert len(coord_alerts) > 0

    def test_normal_timing_no_alert(self, detector: FraudDetector):
        """Tasks with normal spacing should not trigger alert."""
        now = datetime.now(timezone.utc)

        tasks = [
            TaskRecord(
                task_id=f"task_{i}",
                agent_id="agent_1",
                worker_id=None,
                bounty_usd=10.0,
                created_at=now + timedelta(minutes=i * 10),  # 10 min apart
            )
            for i in range(5)
        ]

        alerts = detector.analyze_task_batch(tasks)

        coord_alerts = [a for a in alerts if a.signal == FraudSignal.COORDINATED_TIMING]
        assert len(coord_alerts) == 0


class TestStats:
    """Tests for statistics gathering."""

    def test_get_stats(self, detector: FraudDetector):
        """Should return meaningful statistics."""
        config = FraudConfig(max_devices_per_worker=1)
        detector = FraudDetector(config)

        # Create some activity
        detector.check_multi_device("worker_1", "device_a", ip_address="1.1.1.1")
        detector.check_multi_device("worker_1", "device_b", ip_address="2.2.2.2")
        detector.register_wallet("worker_1", "0xABC")

        stats = detector.get_stats()

        assert stats["total_profiles"] == 1
        assert stats["total_alerts"] == 1
        assert stats["unresolved_alerts"] == 1
        assert stats["unique_ips_tracked"] == 2
        assert stats["unique_wallets_tracked"] == 1
        assert stats["unique_devices_tracked"] == 2
