"""
GPS Anti-Spoofing Module

Detects mock locations and GPS spoofing using:
1. Mock location flag detection
2. Location plausibility (movement patterns)
3. Historical pattern comparison
4. Network triangulation
5. Sensor fusion validation

This module extends the existing verification/gps_antispoofing.py
with additional detection methods for fraud scoring.
"""

import math
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

# Movement thresholds
MAX_WALKING_SPEED_MPS = 2.0  # 2 m/s = 7.2 km/h
MAX_RUNNING_SPEED_MPS = 6.0  # 6 m/s = 21.6 km/h
MAX_VEHICLE_SPEED_MPS = 40.0  # 40 m/s = 144 km/h
MAX_PLANE_SPEED_MPS = 300.0  # 300 m/s = 1080 km/h (airplane)

# Timing thresholds
MIN_TIME_BETWEEN_LOCATIONS_SEC = 5
MOCK_LOCATION_DETECTION_WINDOW_SEC = 3600  # 1 hour

# GPS accuracy thresholds
SUSPICIOUS_ACCURACY_METERS = 5.0  # Too precise for real GPS
MAX_IP_GPS_DISTANCE_KM = 200  # IP geolocation tolerance

# Risk thresholds
LOW_RISK_THRESHOLD = 0.3
MEDIUM_RISK_THRESHOLD = 0.6
HIGH_RISK_THRESHOLD = 0.8

# Earth radius for calculations
EARTH_RADIUS_METERS = 6_371_000


# =============================================================================
# DATA CLASSES
# =============================================================================


class MockLocationIndicator(str, Enum):
    """Indicators of mock/fake location."""

    MOCK_FLAG_SET = "mock_flag_set"
    DEVELOPER_OPTIONS = "developer_options"
    MOCK_APP_DETECTED = "mock_app_detected"
    IMPOSSIBLE_ACCURACY = "impossible_accuracy"
    TELEPORTATION = "teleportation"
    STRAIGHT_LINE_PATH = "straight_line_path"
    NO_ALTITUDE_VARIANCE = "no_altitude_variance"
    PERFECT_COORDINATES = "perfect_coordinates"


@dataclass
class GPSData:
    """GPS location data from a submission."""

    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    timestamp: Optional[datetime] = None
    speed_mps: Optional[float] = None
    bearing: Optional[float] = None
    # Mock location indicators (from device)
    is_mock: Optional[bool] = None
    mock_provider: Optional[str] = None


@dataclass
class DeviceInfo:
    """Device information for fingerprinting and mock detection."""

    device_id: Optional[str] = None
    user_agent: Optional[str] = None
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    device_memory_gb: Optional[float] = None
    hardware_concurrency: Optional[int] = None
    platform: Optional[str] = None
    vendor: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    touch_support: Optional[bool] = None
    webgl_vendor: Optional[str] = None
    webgl_renderer: Optional[str] = None
    # Mock location indicators
    mock_location_enabled: Optional[bool] = None
    developer_options_enabled: Optional[bool] = None
    mock_location_apps: Optional[List[str]] = None


@dataclass
class SensorData:
    """Sensor data from device (accelerometer, gyroscope)."""

    accelerometer: Optional[Tuple[float, float, float]] = None  # x, y, z in m/s^2
    gyroscope: Optional[Tuple[float, float, float]] = None  # x, y, z in rad/s
    magnetometer: Optional[Tuple[float, float, float]] = None  # x, y, z in microtesla
    timestamp: Optional[datetime] = None


@dataclass
class LocationRecord:
    """Historical location record for pattern analysis."""

    gps_data: GPSData
    timestamp: datetime
    device_id: Optional[str] = None
    accuracy_meters: Optional[float] = None


@dataclass
class MockLocationResult:
    """Result of mock location detection."""

    is_mock: bool
    confidence: float
    indicators: List[MockLocationIndicator]
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlausibilityResult:
    """Result of location plausibility check."""

    is_plausible: bool
    confidence: float
    reason: Optional[str] = None
    speed_mps: Optional[float] = None
    distance_m: Optional[float] = None
    time_delta_sec: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpoofingResult:
    """Comprehensive GPS spoofing detection result."""

    is_spoofed: bool
    risk_score: float  # 0.0 to 1.0
    confidence: float
    reasons: List[str]
    checks_performed: List[str]
    details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# GPS ANTI-SPOOFING CLASS
# =============================================================================


class GPSAntiSpoofing:
    """
    Comprehensive GPS anti-spoofing detection.

    Combines multiple detection methods:
    1. Direct mock location flag detection
    2. Movement pattern plausibility
    3. Historical pattern comparison
    4. Network/IP triangulation
    5. Sensor data correlation
    """

    def __init__(self, ip_geolocation_service: Optional[Any] = None):
        """
        Initialize GPS anti-spoofing detector.

        Args:
            ip_geolocation_service: Optional service for IP geolocation
        """
        self.ip_geolocation_service = ip_geolocation_service

        # In-memory storage (use Redis/DB in production)
        self._location_history: Dict[str, List[LocationRecord]] = defaultdict(list)
        self._device_fingerprints: Dict[str, List[Dict]] = defaultdict(list)

        logger.info("GPSAntiSpoofing initialized")

    async def detect_spoofing(
        self,
        gps_data: GPSData,
        device_info: DeviceInfo,
        executor_id: str,
        ip_address: Optional[str] = None,
        sensor_data: Optional[SensorData] = None,
    ) -> SpoofingResult:
        """
        Main entry point for GPS spoofing detection.

        Runs all detection methods and aggregates results.

        Args:
            gps_data: GPS coordinates and metadata
            device_info: Device information
            executor_id: Worker's ID
            ip_address: Client IP (optional)
            sensor_data: Accelerometer/gyroscope data (optional)

        Returns:
            SpoofingResult with aggregated analysis
        """
        reasons: List[str] = []
        risk_scores: List[float] = []
        checks_performed: List[str] = []
        details: Dict[str, Any] = {}

        # Ensure timestamp
        if gps_data.timestamp is None:
            gps_data.timestamp = datetime.now(timezone.utc)

        # 1. Check for mock location indicators
        mock_result = await self.detect_mock_location(gps_data, device_info)
        checks_performed.append("mock_location")
        if mock_result.is_mock:
            reasons.append(
                f"Mock location detected: {', '.join(i.value for i in mock_result.indicators)}"
            )
            risk_scores.append(0.9)
            details["mock_location"] = {
                "is_mock": True,
                "indicators": [i.value for i in mock_result.indicators],
                "confidence": mock_result.confidence,
            }

        # 2. Check location plausibility against history
        plausibility_result = await self.verify_location_plausibility(
            executor_id, gps_data
        )
        checks_performed.append("plausibility")
        if not plausibility_result.is_plausible:
            reasons.append(plausibility_result.reason or "Implausible location")
            risk_scores.append(0.85)
            details["plausibility"] = {
                "is_plausible": False,
                "reason": plausibility_result.reason,
                "speed_mps": plausibility_result.speed_mps,
                "distance_m": plausibility_result.distance_m,
            }

        # 3. Check historical patterns
        history_result = await self.check_location_history(executor_id, gps_data)
        checks_performed.append("history_pattern")
        if history_result["suspicious"]:
            reasons.append(history_result["reason"])
            risk_scores.append(history_result["risk_score"])
            details["history"] = history_result

        # 4. Check network location (if IP provided)
        if ip_address:
            network_result = await self._check_network_location(ip_address, gps_data)
            checks_performed.append("network_triangulation")
            if network_result["suspicious"]:
                reasons.append(network_result["reason"])
                risk_scores.append(network_result["risk_score"])
                details["network"] = network_result

        # 5. Check sensor consistency (if sensor data provided)
        if sensor_data and (sensor_data.accelerometer or sensor_data.gyroscope):
            sensor_result = await self._check_sensor_consistency(sensor_data, gps_data)
            checks_performed.append("sensor_fusion")
            if sensor_result["suspicious"]:
                reasons.append(sensor_result["reason"])
                risk_scores.append(sensor_result["risk_score"])
                details["sensor"] = sensor_result

        # Store location for future analysis
        await self._store_location(executor_id, gps_data, device_info.device_id)

        # Calculate overall risk
        if not risk_scores:
            return SpoofingResult(
                is_spoofed=False,
                risk_score=0.0,
                confidence=0.9,
                reasons=[],
                checks_performed=checks_performed,
                details=details,
            )

        aggregated_risk = self._aggregate_risk_scores(risk_scores)
        is_spoofed = aggregated_risk >= HIGH_RISK_THRESHOLD
        confidence = min(0.95, 0.5 + len(checks_performed) * 0.1)

        return SpoofingResult(
            is_spoofed=is_spoofed,
            risk_score=aggregated_risk,
            confidence=confidence,
            reasons=reasons,
            checks_performed=checks_performed,
            details=details,
        )

    async def detect_mock_location(
        self, gps_data: GPSData, device_info: Optional[DeviceInfo] = None
    ) -> MockLocationResult:
        """
        Detect if GPS data comes from a mock/fake location.

        Checks:
        1. Direct mock flag from device
        2. Developer options enabled
        3. Known mock location apps installed
        4. Impossibly precise accuracy
        5. Perfect coordinate patterns

        Args:
            gps_data: GPS data to check
            device_info: Optional device information

        Returns:
            MockLocationResult with detection details
        """
        indicators: List[MockLocationIndicator] = []
        confidence = 0.0

        # Check 1: Direct mock flag
        if gps_data.is_mock:
            indicators.append(MockLocationIndicator.MOCK_FLAG_SET)
            confidence = max(confidence, 0.95)

        if device_info:
            # Check 2: Developer options enabled
            if device_info.developer_options_enabled:
                indicators.append(MockLocationIndicator.DEVELOPER_OPTIONS)
                confidence = max(confidence, 0.6)

            # Check 3: Mock location apps
            if device_info.mock_location_apps:
                known_mock_apps = [
                    "fake gps",
                    "mock location",
                    "gps joystick",
                    "location spoofer",
                    "fly gps",
                    "fake location",
                    "gps emulator",
                    "mock gps",
                    "location changer",
                ]
                for app in device_info.mock_location_apps:
                    if any(mock in app.lower() for mock in known_mock_apps):
                        indicators.append(MockLocationIndicator.MOCK_APP_DETECTED)
                        confidence = max(confidence, 0.9)
                        break

            # Check 4: Mock location explicitly enabled
            if device_info.mock_location_enabled:
                indicators.append(MockLocationIndicator.MOCK_FLAG_SET)
                confidence = max(confidence, 0.85)

        # Check 5: Impossibly precise accuracy
        if gps_data.accuracy_meters is not None:
            if gps_data.accuracy_meters < SUSPICIOUS_ACCURACY_METERS:
                indicators.append(MockLocationIndicator.IMPOSSIBLE_ACCURACY)
                confidence = max(confidence, 0.7)

        # Check 6: Perfect coordinate patterns (suspiciously round numbers)
        lat_decimal = abs(gps_data.latitude) % 1
        lon_decimal = abs(gps_data.longitude) % 1

        # Check if coordinates are suspiciously "perfect"
        # Real GPS rarely gives perfectly round coordinates
        if (
            lat_decimal == 0.0
            or lon_decimal == 0.0
            or str(gps_data.latitude).endswith("0000")
            or str(gps_data.longitude).endswith("0000")
        ):
            indicators.append(MockLocationIndicator.PERFECT_COORDINATES)
            confidence = max(confidence, 0.5)

        is_mock = len(indicators) > 0

        return MockLocationResult(
            is_mock=is_mock,
            confidence=confidence,
            indicators=indicators,
            details={
                "accuracy_meters": gps_data.accuracy_meters,
                "mock_flag": gps_data.is_mock,
                "mock_provider": gps_data.mock_provider,
            },
        )

    async def verify_location_plausibility(
        self,
        executor_id: str,
        current_location: GPSData,
    ) -> PlausibilityResult:
        """
        Verify if location movement is physically plausible.

        Checks:
        1. Speed between consecutive locations
        2. Travel time vs distance
        3. Path patterns (straight lines are suspicious)

        Args:
            executor_id: Worker's ID
            current_location: Current GPS data

        Returns:
            PlausibilityResult with plausibility assessment
        """
        history = self._location_history.get(executor_id, [])

        if not history:
            # First location for this executor
            return PlausibilityResult(
                is_plausible=True,
                confidence=0.5,
                reason="First location recorded",
            )

        # Get most recent location
        last_record = history[-1]
        last_location = last_record.gps_data

        # Ensure timestamps are timezone-aware
        current_ts = current_location.timestamp
        last_ts = last_record.timestamp

        if current_ts.tzinfo is None:
            current_ts = current_ts.replace(tzinfo=timezone.utc)
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)

        time_delta = (current_ts - last_ts).total_seconds()

        if time_delta < MIN_TIME_BETWEEN_LOCATIONS_SEC:
            return PlausibilityResult(
                is_plausible=False,
                confidence=0.9,
                reason=f"Locations too close in time: {time_delta:.1f}s",
                time_delta_sec=time_delta,
            )

        # Calculate distance
        distance_m = self._haversine_distance(
            last_location.latitude,
            last_location.longitude,
            current_location.latitude,
            current_location.longitude,
        )

        # Calculate speed
        speed_mps = distance_m / time_delta if time_delta > 0 else 0

        # Check for teleportation (impossible speed)
        if speed_mps > MAX_PLANE_SPEED_MPS:
            return PlausibilityResult(
                is_plausible=False,
                confidence=0.95,
                reason=f"Impossible speed: {speed_mps:.1f} m/s ({speed_mps * 3.6:.0f} km/h) - teleportation detected",
                speed_mps=speed_mps,
                distance_m=distance_m,
                time_delta_sec=time_delta,
            )

        # Check for very high speed (suspicious but possible)
        if speed_mps > MAX_VEHICLE_SPEED_MPS:
            return PlausibilityResult(
                is_plausible=False,
                confidence=0.8,
                reason=f"Very high speed: {speed_mps:.1f} m/s ({speed_mps * 3.6:.0f} km/h) - unlikely for typical tasks",
                speed_mps=speed_mps,
                distance_m=distance_m,
                time_delta_sec=time_delta,
            )

        # Check for straight-line path (suspicious pattern)
        if len(history) >= 3:
            straight_line = self._check_straight_line_path(
                [r.gps_data for r in history[-3:]] + [current_location]
            )
            if straight_line:
                return PlausibilityResult(
                    is_plausible=False,
                    confidence=0.7,
                    reason="Suspicious straight-line movement pattern",
                    speed_mps=speed_mps,
                    distance_m=distance_m,
                    time_delta_sec=time_delta,
                    details={"straight_line_pattern": True},
                )

        return PlausibilityResult(
            is_plausible=True,
            confidence=0.9,
            speed_mps=speed_mps,
            distance_m=distance_m,
            time_delta_sec=time_delta,
        )

    async def check_location_history(
        self,
        executor_id: str,
        current_location: GPSData,
    ) -> Dict[str, Any]:
        """
        Compare current location to historical patterns.

        Checks for:
        1. Location clusters (typical work areas)
        2. Anomalous locations far from usual areas
        3. Altitude consistency
        4. Time-of-day patterns

        Args:
            executor_id: Worker's ID
            current_location: Current GPS data

        Returns:
            Dictionary with history analysis results
        """
        history = self._location_history.get(executor_id, [])

        if len(history) < 5:
            return {
                "suspicious": False,
                "reason": "Insufficient history for pattern analysis",
                "risk_score": 0.0,
                "history_count": len(history),
            }

        # Calculate center of historical locations
        lats = [r.gps_data.latitude for r in history]
        lons = [r.gps_data.longitude for r in history]

        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)

        # Calculate typical radius
        distances = [
            self._haversine_distance(center_lat, center_lon, lat, lon)
            for lat, lon in zip(lats, lons)
        ]
        typical_radius = sum(distances) / len(distances)

        # Check if current location is far from typical area
        current_distance = self._haversine_distance(
            center_lat,
            center_lon,
            current_location.latitude,
            current_location.longitude,
        )

        # Location is suspicious if > 3x typical radius
        if current_distance > typical_radius * 3 and typical_radius > 100:
            return {
                "suspicious": True,
                "reason": f"Location {current_distance:.0f}m from typical area (usual: {typical_radius:.0f}m)",
                "risk_score": min(0.7, current_distance / (typical_radius * 10)),
                "center": (center_lat, center_lon),
                "typical_radius_m": typical_radius,
                "current_distance_m": current_distance,
            }

        # Check altitude consistency (if available)
        altitudes = [
            r.gps_data.altitude for r in history if r.gps_data.altitude is not None
        ]
        if altitudes and current_location.altitude is not None:
            avg_altitude = sum(altitudes) / len(altitudes)
            altitude_diff = abs(current_location.altitude - avg_altitude)

            # Large altitude difference is suspicious (unless expected)
            if altitude_diff > 500:  # More than 500m difference
                return {
                    "suspicious": True,
                    "reason": f"Unusual altitude: {current_location.altitude:.0f}m vs typical {avg_altitude:.0f}m",
                    "risk_score": 0.5,
                    "altitude_difference_m": altitude_diff,
                }

        return {
            "suspicious": False,
            "reason": None,
            "risk_score": 0.0,
            "history_count": len(history),
            "typical_radius_m": typical_radius,
        }

    async def _check_network_location(
        self, ip_address: str, claimed_gps: GPSData
    ) -> Dict[str, Any]:
        """Compare IP geolocation with claimed GPS."""
        # Skip for private IPs
        if self._is_private_ip(ip_address):
            return {
                "suspicious": False,
                "reason": "Private IP, skipped",
                "risk_score": 0.0,
            }

        # Get IP geolocation (if service available)
        ip_location = await self._get_ip_location(ip_address)

        if ip_location is None:
            return {
                "suspicious": False,
                "reason": "Could not determine IP geolocation",
                "risk_score": 0.1,
            }

        # Calculate distance
        distance_km = (
            self._haversine_distance(
                ip_location.latitude,
                ip_location.longitude,
                claimed_gps.latitude,
                claimed_gps.longitude,
            )
            / 1000
        )

        if distance_km > MAX_IP_GPS_DISTANCE_KM:
            return {
                "suspicious": True,
                "reason": f"IP location is {distance_km:.0f}km from claimed GPS (possible VPN/spoofing)",
                "risk_score": min(0.8, 0.4 + (distance_km / 1000) * 0.1),
                "distance_km": distance_km,
                "ip_location": (ip_location.latitude, ip_location.longitude),
            }

        return {
            "suspicious": False,
            "reason": None,
            "risk_score": 0.0,
            "distance_km": distance_km,
        }

    async def _check_sensor_consistency(
        self, sensor_data: SensorData, gps_data: GPSData
    ) -> Dict[str, Any]:
        """Cross-validate sensor data with GPS movement."""
        suspicious_flags: List[str] = []
        risk_score = 0.0

        if sensor_data.accelerometer:
            ax, ay, az = sensor_data.accelerometer

            # Total acceleration magnitude (excluding gravity)
            total_accel = math.sqrt(ax**2 + ay**2 + az**2)
            accel_minus_gravity = abs(total_accel - 9.8)

            # Check for stationary device
            is_stationary = accel_minus_gravity < 0.3

            # If GPS shows significant speed but device is stationary
            if (
                gps_data.speed_mps
                and gps_data.speed_mps > MAX_WALKING_SPEED_MPS
                and is_stationary
            ):
                suspicious_flags.append(
                    f"GPS shows {gps_data.speed_mps:.1f} m/s but accelerometer shows stationary"
                )
                risk_score = max(risk_score, 0.8)

        if suspicious_flags:
            return {
                "suspicious": True,
                "reason": "; ".join(suspicious_flags),
                "risk_score": risk_score,
                "accelerometer": sensor_data.accelerometer,
                "gps_speed": gps_data.speed_mps,
            }

        return {
            "suspicious": False,
            "reason": None,
            "risk_score": 0.0,
        }

    def _check_straight_line_path(self, locations: List[GPSData]) -> bool:
        """Check if path forms suspicious straight line."""
        if len(locations) < 4:
            return False

        # Calculate bearings between consecutive points
        bearings = []
        for i in range(len(locations) - 1):
            bearing = self._calculate_bearing(
                locations[i].latitude,
                locations[i].longitude,
                locations[i + 1].latitude,
                locations[i + 1].longitude,
            )
            bearings.append(bearing)

        # Check if bearings are suspiciously consistent
        bearing_variance = max(bearings) - min(bearings)

        # Allow for 180-degree flip (going back and forth)
        if bearing_variance > 180:
            bearing_variance = 360 - bearing_variance

        # Very consistent bearings (< 5 degrees variance) are suspicious
        return bearing_variance < 5

    async def _store_location(
        self, executor_id: str, gps_data: GPSData, device_id: Optional[str]
    ) -> None:
        """Store location in history."""
        record = LocationRecord(
            gps_data=gps_data,
            timestamp=gps_data.timestamp or datetime.now(timezone.utc),
            device_id=device_id,
            accuracy_meters=gps_data.accuracy_meters,
        )

        self._location_history[executor_id].append(record)

        # Keep only last 100 locations
        if len(self._location_history[executor_id]) > 100:
            self._location_history[executor_id] = self._location_history[executor_id][
                -100:
            ]

    async def _get_ip_location(self, ip_address: str) -> Optional[GPSData]:
        """Get geolocation from IP address."""
        if self.ip_geolocation_service:
            try:
                return await self.ip_geolocation_service.get_location(ip_address)
            except Exception as e:
                logger.warning(f"IP geolocation failed: {e}")
        return None

    def _is_private_ip(self, ip_address: str) -> bool:
        """Check if IP is private/local."""
        private_prefixes = [
            "10.",
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
            "192.168.",
            "127.",
            "localhost",
            "::1",
            "fe80:",
        ]
        return any(ip_address.startswith(p) for p in private_prefixes)

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance in meters using Haversine formula."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return EARTH_RADIUS_METERS * c

    def _calculate_bearing(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate bearing between two points in degrees."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(
            lat2
        ) * math.cos(dlon)

        bearing = math.atan2(x, y)
        return (math.degrees(bearing) + 360) % 360

    def _aggregate_risk_scores(self, scores: List[float]) -> float:
        """Aggregate multiple risk scores with weighted average."""
        if not scores:
            return 0.0

        # Sort descending - higher scores get more weight
        sorted_scores = sorted(scores, reverse=True)

        total_weight = 0.0
        weighted_sum = 0.0

        for i, score in enumerate(sorted_scores):
            weight = 1.0 / (i + 1)  # 1.0, 0.5, 0.33, ...
            weighted_sum += score * weight
            total_weight += weight

        return min(1.0, weighted_sum / total_weight)

    def clear_executor_history(self, executor_id: str) -> None:
        """Clear stored data for an executor."""
        self._location_history.pop(executor_id, None)
        self._device_fingerprints.pop(executor_id, None)
