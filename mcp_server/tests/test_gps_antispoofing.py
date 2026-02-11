"""
Tests for GPS Anti-Spoofing Detection

Tests NOW-108, NOW-109, NOW-111 implementation:
- GPS spoofing detection
- Multi-device detection
- Rate limits
"""

import pytest

pytestmark = pytest.mark.security
from datetime import datetime, timedelta, UTC

from ..verification.gps_antispoofing import (
    GPSAntiSpoofing,
    GPSData,
    DeviceInfo,
    SpoofingResult,
    SpoofingRisk,
    check_gps_spoofing,
    MAX_TASKS_PER_DAY_PER_IP,
    MAX_TASKS_PER_DAY_PER_DEVICE,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def detector():
    """Create a fresh GPS anti-spoofing detector."""
    return GPSAntiSpoofing()


@pytest.fixture
def sample_gps_data():
    """Sample GPS data for testing."""
    return GPSData(
        latitude=19.4326,  # Mexico City
        longitude=-99.1332,
        accuracy_meters=10,
        timestamp=datetime.now(UTC),
    )


@pytest.fixture
def sample_device_info():
    """Sample device info for testing."""
    return DeviceInfo(
        device_id="test-device-001",
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)",
        screen_width=1170,
        screen_height=2532,
        platform="iOS",
        timezone="America/Mexico_City",
        language="es-MX",
    )


# =============================================================================
# MOVEMENT PATTERN TESTS (NOW-108)
# =============================================================================


class TestMovementPattern:
    """Tests for movement pattern detection."""

    @pytest.mark.asyncio
    async def test_first_location_is_not_suspicious(self, detector):
        """First location submission should not be flagged."""
        result = await detector.check_movement_pattern(
            executor_id="worker-001",
            new_location=GPSData(latitude=19.4326, longitude=-99.1332),
            timestamp=datetime.now(UTC),
        )

        assert result["suspicious"] is False
        assert result["risk_score"] == 0.0

    @pytest.mark.asyncio
    async def test_impossible_speed_detected(self, detector):
        """Should detect impossible travel speeds (teleportation)."""
        executor_id = "worker-002"

        # First location: Mexico City
        await detector._store_location(
            executor_id,
            GPSData(latitude=19.4326, longitude=-99.1332),
            datetime.now(UTC) - timedelta(minutes=5),
        )

        # Second location: New York (5000+ km away in 5 minutes = impossible)
        result = await detector.check_movement_pattern(
            executor_id=executor_id,
            new_location=GPSData(latitude=40.7128, longitude=-74.0060),
            timestamp=datetime.now(UTC),
        )

        assert result["suspicious"] is True
        assert "Impossible travel speed" in result["reason"]
        assert result["risk_score"] >= 0.9

    @pytest.mark.asyncio
    async def test_walking_speed_is_normal(self, detector):
        """Walking speed should not be flagged."""
        executor_id = "worker-003"

        # First location
        await detector._store_location(
            executor_id,
            GPSData(latitude=19.4326, longitude=-99.1332),
            datetime.now(UTC) - timedelta(minutes=10),
        )

        # Second location: ~500m away (walking distance in 10 min)
        result = await detector.check_movement_pattern(
            executor_id=executor_id,
            new_location=GPSData(latitude=19.4370, longitude=-99.1332),  # ~500m north
            timestamp=datetime.now(UTC),
        )

        assert result["suspicious"] is False
        assert result["risk_score"] < 0.5

    @pytest.mark.asyncio
    async def test_rapid_submissions_flagged(self, detector):
        """Submissions too close in time should be flagged."""
        executor_id = "worker-004"

        # First location
        await detector._store_location(
            executor_id,
            GPSData(latitude=19.4326, longitude=-99.1332),
            datetime.now(UTC) - timedelta(seconds=10),  # 10 seconds ago
        )

        # Second location: same place but only 10 seconds later
        result = await detector.check_movement_pattern(
            executor_id=executor_id,
            new_location=GPSData(latitude=19.4326, longitude=-99.1332),
            timestamp=datetime.now(UTC),
        )

        assert result["suspicious"] is True
        assert "too rapid" in result["reason"].lower()


# =============================================================================
# SENSOR CONSISTENCY TESTS (NOW-108)
# =============================================================================


class TestSensorConsistency:
    """Tests for sensor fusion detection."""

    @pytest.mark.asyncio
    async def test_no_sensor_data_low_risk(self, detector):
        """Missing sensor data should have low risk score."""
        result = await detector.check_sensor_consistency(
            accelerometer=None,
            gyroscope=None,
            gps=GPSData(latitude=19.4326, longitude=-99.1332),
        )

        assert result["suspicious"] is False
        assert result["risk_score"] <= 0.2

    @pytest.mark.asyncio
    async def test_stationary_device_with_high_gps_speed(self, detector):
        """Stationary accelerometer + high GPS speed should be suspicious."""
        result = await detector.check_sensor_consistency(
            accelerometer=(0.0, 0.0, 9.8),  # Only gravity, device stationary
            gyroscope=None,
            gps=GPSData(
                latitude=19.4326,
                longitude=-99.1332,
                speed_mps=30.0,  # 108 km/h but device not moving
            ),
        )

        assert result["suspicious"] is True
        assert result["risk_score"] >= 0.7

    @pytest.mark.asyncio
    async def test_walking_pattern_matches_walking_speed(self, detector):
        """Walking acceleration pattern + walking GPS speed should be fine."""
        result = await detector.check_sensor_consistency(
            accelerometer=(0.5, 1.0, 10.2),  # Slight variance = walking
            gyroscope=None,
            gps=GPSData(
                latitude=19.4326,
                longitude=-99.1332,
                speed_mps=1.5,  # ~5.4 km/h walking
            ),
        )

        assert result["suspicious"] is False


# =============================================================================
# MULTI-DEVICE DETECTION TESTS (NOW-109)
# =============================================================================


class TestMultiDeviceDetection:
    """Tests for multi-device detection."""

    @pytest.mark.asyncio
    async def test_first_device_is_allowed(self, detector):
        """First device should be allowed."""
        result = await detector.detect_multi_device(
            executor_id="worker-010",
            device_fingerprint="device-fingerprint-001",
        )

        assert result.is_multi_device is False
        assert result.device_count == 1

    @pytest.mark.asyncio
    async def test_same_device_is_recognized(self, detector):
        """Same device fingerprint should be recognized."""
        executor_id = "worker-011"
        fingerprint = "device-fingerprint-002"

        # First submission
        await detector.detect_multi_device(executor_id, fingerprint)

        # Second submission with same fingerprint
        result = await detector.detect_multi_device(executor_id, fingerprint)

        assert result.is_multi_device is False
        assert result.device_count == 1

    @pytest.mark.asyncio
    async def test_multiple_devices_flagged(self, detector):
        """More than 2 devices should be flagged."""
        executor_id = "worker-012"

        # Register 3 different devices
        await detector.detect_multi_device(executor_id, "device-fp-a")
        await detector.detect_multi_device(executor_id, "device-fp-b")
        result = await detector.detect_multi_device(executor_id, "device-fp-c")

        assert result.is_multi_device is True
        assert result.device_count == 3
        assert "suspicious" in result.reason.lower()


# =============================================================================
# RATE LIMIT TESTS (NOW-111)
# =============================================================================


class TestRateLimits:
    """Tests for rate limiting (NOW-111)."""

    @pytest.mark.asyncio
    async def test_first_submission_allowed(self, detector):
        """First submission should be allowed."""
        result = await detector.check_rate_limits(
            ip_address="192.0.2.1",
            device_id="device-001",
        )

        assert result.allowed is True
        assert result.ip_count_today == 0
        assert result.device_count_today == 0

    @pytest.mark.asyncio
    async def test_ip_limit_enforced(self, detector):
        """IP limit of 50/day should be enforced."""
        ip = "192.0.2.100"

        # Simulate 50 submissions
        for _ in range(MAX_TASKS_PER_DAY_PER_IP):
            detector._ip_submissions[ip].append(datetime.now(UTC))

        result = await detector.check_rate_limits(
            ip_address=ip,
            device_id="device-new",
        )

        assert result.allowed is False
        assert "IP rate limit exceeded" in result.reason
        assert result.ip_limit == MAX_TASKS_PER_DAY_PER_IP

    @pytest.mark.asyncio
    async def test_device_limit_enforced(self, detector):
        """Device limit of 20/day should be enforced."""
        device_id = "device-heavy-user"

        # Simulate 20 submissions
        for _ in range(MAX_TASKS_PER_DAY_PER_DEVICE):
            detector._device_submissions[device_id].append(datetime.now(UTC))

        result = await detector.check_rate_limits(
            ip_address="192.0.2.200",
            device_id=device_id,
        )

        assert result.allowed is False
        assert "Device rate limit exceeded" in result.reason
        assert result.device_limit == MAX_TASKS_PER_DAY_PER_DEVICE

    @pytest.mark.asyncio
    async def test_old_submissions_not_counted(self, detector):
        """Submissions older than 24 hours should not count."""
        ip = "192.0.2.300"
        old_time = datetime.now(UTC) - timedelta(days=2)

        # Add old submissions
        for _ in range(100):
            detector._ip_submissions[ip].append(old_time)

        result = await detector.check_rate_limits(
            ip_address=ip,
            device_id="device-fresh",
        )

        # Old submissions should be cleaned up
        assert result.allowed is True
        assert result.ip_count_today == 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestFullSpoofingDetection:
    """Integration tests for complete spoofing detection."""

    @pytest.mark.asyncio
    async def test_normal_submission_passes(
        self, detector, sample_gps_data, sample_device_info
    ):
        """Normal submission should pass all checks."""
        result = await detector.detect_spoofing(
            gps_data=sample_gps_data,
            device_info=sample_device_info,
            executor_id="worker-good",
        )

        assert result.is_spoofed is False
        assert result.risk_level == SpoofingRisk.LOW
        assert len(result.checks_performed) >= 3

    @pytest.mark.asyncio
    async def test_convenience_function_works(self):
        """Test the convenience function."""
        result = await check_gps_spoofing(
            latitude=19.4326,
            longitude=-99.1332,
            executor_id="worker-convenience",
            device_info={"platform": "iOS", "timezone": "America/Mexico_City"},
        )

        assert isinstance(result, SpoofingResult)
        assert result.risk_level in list(SpoofingRisk)


# =============================================================================
# HELPER FUNCTION TESTS
# =============================================================================


class TestHelperFunctions:
    """Tests for internal helper functions."""

    def test_haversine_distance(self, detector):
        """Test distance calculation."""
        # Mexico City to Guadalajara (~470km)
        distance = detector._haversine_distance(
            19.4326,
            -99.1332,  # Mexico City
            20.6597,
            -103.3496,  # Guadalajara
        )

        # Should be approximately 470km
        assert 450_000 < distance < 490_000  # meters

    def test_private_ip_detection(self, detector):
        """Test private IP detection."""
        assert detector._is_private_ip("192.168.1.1") is True
        assert detector._is_private_ip("10.0.0.1") is True
        assert detector._is_private_ip("127.0.0.1") is True
        assert detector._is_private_ip("8.8.8.8") is False
        assert detector._is_private_ip("1.2.3.4") is False

    def test_risk_score_aggregation(self, detector):
        """Test risk score aggregation."""
        # Single high score
        assert detector._aggregate_risk_scores([0.9]) == 0.9

        # Multiple scores - weighted average with diminishing weights
        # Weights: [1.0, 0.5, 0.33], weighted_sum ~= 1.25, total_weight ~= 1.83
        # Result ~= 0.68
        aggregated = detector._aggregate_risk_scores([0.9, 0.5, 0.3])
        assert 0.65 < aggregated < 0.75

        # Empty list
        assert detector._aggregate_risk_scores([]) == 0.0

    def test_device_fingerprint_generation(self, detector, sample_device_info):
        """Test device fingerprint generation."""
        fp1 = detector._generate_device_fingerprint(sample_device_info)
        fp2 = detector._generate_device_fingerprint(sample_device_info)

        # Same device info should produce same fingerprint
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA256 hex digest

        # Different device should produce different fingerprint
        different_device = DeviceInfo(
            screen_width=1920,
            screen_height=1080,
            platform="Windows",
        )
        fp3 = detector._generate_device_fingerprint(different_device)
        assert fp1 != fp3


# =============================================================================
# CLEANUP TESTS
# =============================================================================


class TestCleanup:
    """Tests for cleanup methods."""

    @pytest.mark.asyncio
    async def test_clear_executor_history(self, detector):
        """Test clearing executor data."""
        executor_id = "worker-cleanup"

        # Add some data
        await detector._store_location(
            executor_id,
            GPSData(latitude=19.4326, longitude=-99.1332),
            datetime.now(UTC),
        )
        await detector.detect_multi_device(executor_id, "device-cleanup")

        # Clear
        detector.clear_executor_history(executor_id)

        # Verify cleared
        assert executor_id not in detector._location_history
        assert executor_id not in detector._device_fingerprints
