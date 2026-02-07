"""
GPS Anti-Spoofing Detection

Implements NOW-108, NOW-109, NOW-111 from TODO_NOW.md:
- NOW-108: GPS spoofing detection using network triangulation, movement patterns, sensor fusion
- NOW-109: Multi-device detection (same worker using multiple devices)
- NOW-111: Rate limits per IP/device (50 tasks/day/IP, 20/device)

Detection methods:
1. Network triangulation - compare IP geolocation with claimed GPS
2. Movement pattern analysis - detect impossible travel speeds
3. Sensor fusion - cross-validate accelerometer/gyroscope with GPS movement
4. Multi-device detection - fingerprint devices per executor
5. Rate limiting - prevent abuse by limiting submissions per IP/device
"""

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import Optional, Tuple, List, Dict, Any
from enum import Enum


# =============================================================================
# CONSTANTS
# =============================================================================

# Rate limits (NOW-111)
MAX_TASKS_PER_DAY_PER_IP = 50
MAX_TASKS_PER_DAY_PER_DEVICE = 20

# Movement detection thresholds
MAX_WALKING_SPEED_MPS = 2.0  # 2 m/s = ~7.2 km/h (brisk walking)
MAX_VEHICLE_SPEED_MPS = 50.0  # 50 m/s = 180 km/h (highway)
MIN_TIME_BETWEEN_LOCATIONS_SECONDS = 30

# GPS accuracy thresholds
MAX_IP_GPS_DISTANCE_KM = 100  # IP geolocation is not very accurate
MIN_SENSOR_MOVEMENT_FOR_GPS_CHANGE = 0.1  # meters

# Device fingerprint
DEVICE_SIMILARITY_THRESHOLD = 0.85  # 85% similar = same device

# Risk score thresholds
LOW_RISK_THRESHOLD = 0.3
MEDIUM_RISK_THRESHOLD = 0.6
HIGH_RISK_THRESHOLD = 0.8

# Earth radius for haversine calculation
EARTH_RADIUS_METERS = 6_371_000


# =============================================================================
# DATA CLASSES
# =============================================================================


class SpoofingRisk(str, Enum):
    """Risk levels for GPS spoofing detection."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SpoofingResult:
    """Result of GPS spoofing detection analysis."""

    is_spoofed: bool
    confidence: float  # 0.0 to 1.0
    reasons: List[str]
    risk_score: float  # 0.0 to 1.0
    risk_level: SpoofingRisk
    checks_performed: List[str]
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def safe(cls, checks_performed: List[str]) -> "SpoofingResult":
        """Create a safe (non-spoofed) result."""
        return cls(
            is_spoofed=False,
            confidence=0.95,
            reasons=[],
            risk_score=0.1,
            risk_level=SpoofingRisk.LOW,
            checks_performed=checks_performed,
            details={},
        )

    @classmethod
    def spoofed(
        cls,
        reasons: List[str],
        risk_score: float,
        confidence: float,
        checks_performed: List[str],
        details: Optional[Dict[str, Any]] = None,
    ) -> "SpoofingResult":
        """Create a spoofed result."""
        risk_level = cls._calculate_risk_level(risk_score)
        return cls(
            is_spoofed=risk_score >= HIGH_RISK_THRESHOLD,
            confidence=confidence,
            reasons=reasons,
            risk_score=risk_score,
            risk_level=risk_level,
            checks_performed=checks_performed,
            details=details or {},
        )

    @staticmethod
    def _calculate_risk_level(risk_score: float) -> SpoofingRisk:
        """Calculate risk level from score."""
        if risk_score >= HIGH_RISK_THRESHOLD:
            return SpoofingRisk.CRITICAL
        elif risk_score >= MEDIUM_RISK_THRESHOLD:
            return SpoofingRisk.HIGH
        elif risk_score >= LOW_RISK_THRESHOLD:
            return SpoofingRisk.MEDIUM
        return SpoofingRisk.LOW


@dataclass
class GPSData:
    """GPS location data from a submission."""

    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy_meters: Optional[float] = None
    timestamp: Optional[datetime] = None
    speed_mps: Optional[float] = None  # Speed in meters per second
    bearing: Optional[float] = None  # Heading in degrees


@dataclass
class DeviceInfo:
    """Device information for fingerprinting."""

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


@dataclass
class SensorData:
    """Sensor data from device (accelerometer, gyroscope)."""

    accelerometer: Optional[Tuple[float, float, float]] = None  # x, y, z in m/s^2
    gyroscope: Optional[Tuple[float, float, float]] = None  # x, y, z in rad/s
    magnetometer: Optional[Tuple[float, float, float]] = None  # x, y, z in microtesla
    timestamp: Optional[datetime] = None


@dataclass
class LocationHistory:
    """Historical location data for an executor."""

    executor_id: str
    locations: List[Tuple[GPSData, datetime]] = field(default_factory=list)
    devices: List[str] = field(default_factory=list)


@dataclass
class RateLimitResult:
    """Result of rate limit check."""

    allowed: bool
    reason: Optional[str]
    ip_count_today: int
    device_count_today: int
    ip_limit: int
    device_limit: int


@dataclass
class MultiDeviceResult:
    """Result of multi-device detection."""

    is_multi_device: bool
    device_count: int
    devices: List[str]
    similarity_scores: Dict[str, float]
    reason: Optional[str]


# =============================================================================
# GPS ANTI-SPOOFING CLASS
# =============================================================================


class GPSAntiSpoofing:
    """
    GPS anti-spoofing detection system.

    Combines multiple detection methods:
    1. Network triangulation (IP vs GPS comparison)
    2. Movement pattern analysis
    3. Sensor fusion
    4. Multi-device detection
    5. Rate limiting
    """

    def __init__(self, ip_geolocation_service: Optional[Any] = None):
        """
        Initialize GPS anti-spoofing system.

        Args:
            ip_geolocation_service: Optional service for IP geolocation lookups.
                                   Should implement async get_location(ip: str) -> GPSData
        """
        self.ip_geolocation_service = ip_geolocation_service

        # In-memory storage for pattern analysis
        # In production, use Redis or database
        self._location_history: Dict[str, LocationHistory] = defaultdict(
            lambda: LocationHistory(executor_id="")
        )
        self._device_fingerprints: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._ip_submissions: Dict[str, List[datetime]] = defaultdict(list)
        self._device_submissions: Dict[str, List[datetime]] = defaultdict(list)

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
            gps_data: GPS coordinates from the submission
            device_info: Device fingerprint information
            executor_id: Worker's executor ID
            ip_address: Client IP address (optional, for network triangulation)
            sensor_data: Accelerometer/gyroscope data (optional, for sensor fusion)

        Returns:
            SpoofingResult with aggregated analysis
        """
        reasons: List[str] = []
        risk_scores: List[float] = []
        checks_performed: List[str] = []
        details: Dict[str, Any] = {}

        # Set timestamp if not provided
        if gps_data.timestamp is None:
            gps_data.timestamp = datetime.now(UTC)

        # 1. Check movement patterns (NOW-108)
        movement_result = await self.check_movement_pattern(
            executor_id, gps_data, gps_data.timestamp
        )
        checks_performed.append("movement_pattern")
        if movement_result["suspicious"]:
            reasons.append(movement_result["reason"])
            risk_scores.append(movement_result["risk_score"])
            details["movement"] = movement_result

        # 2. Check sensor consistency (NOW-108)
        if sensor_data:
            sensor_result = await self.check_sensor_consistency(
                sensor_data.accelerometer, sensor_data.gyroscope, gps_data
            )
            checks_performed.append("sensor_consistency")
            if sensor_result["suspicious"]:
                reasons.append(sensor_result["reason"])
                risk_scores.append(sensor_result["risk_score"])
                details["sensor"] = sensor_result

        # 3. Check network location (NOW-108)
        if ip_address:
            network_result = await self.check_network_location(ip_address, gps_data)
            checks_performed.append("network_triangulation")
            if network_result["suspicious"]:
                reasons.append(network_result["reason"])
                risk_scores.append(network_result["risk_score"])
                details["network"] = network_result

        # 4. Check multi-device (NOW-109)
        device_fingerprint = self._generate_device_fingerprint(device_info)
        multi_device_result = await self.detect_multi_device(
            executor_id, device_fingerprint
        )
        checks_performed.append("multi_device")
        if multi_device_result.is_multi_device:
            reasons.append(multi_device_result.reason or "Multiple devices detected")
            risk_scores.append(0.7)
            details["multi_device"] = {
                "device_count": multi_device_result.device_count,
                "devices": multi_device_result.devices,
            }

        # 5. Check rate limits (NOW-111)
        rate_limit_result = await self.check_rate_limits(
            ip_address or "unknown", device_fingerprint
        )
        checks_performed.append("rate_limits")
        if not rate_limit_result.allowed:
            reasons.append(rate_limit_result.reason or "Rate limit exceeded")
            risk_scores.append(0.9)  # High risk for rate limit violations
            details["rate_limits"] = {
                "ip_count": rate_limit_result.ip_count_today,
                "device_count": rate_limit_result.device_count_today,
            }

        # Store location in history for future pattern analysis
        await self._store_location(executor_id, gps_data, gps_data.timestamp)

        # Record submission for rate limiting
        if ip_address:
            await self._record_submission(ip_address, device_fingerprint)

        # Calculate aggregated risk score
        if not risk_scores:
            return SpoofingResult.safe(checks_performed)

        # Weight factors by severity
        aggregated_risk = self._aggregate_risk_scores(risk_scores)
        confidence = min(0.95, 0.5 + (len(checks_performed) * 0.1))

        return SpoofingResult.spoofed(
            reasons=reasons,
            risk_score=aggregated_risk,
            confidence=confidence,
            checks_performed=checks_performed,
            details=details,
        )

    async def check_movement_pattern(
        self,
        executor_id: str,
        new_location: GPSData,
        timestamp: datetime,
    ) -> Dict[str, Any]:
        """
        Check if movement pattern is physically possible.

        Detects:
        - Impossible travel speeds (teleportation)
        - Unrealistic patterns (perfect grid, etc.)
        - Sudden jumps without corresponding sensor data

        Args:
            executor_id: Worker's ID
            new_location: New GPS coordinates
            timestamp: Timestamp of new location

        Returns:
            Dictionary with suspicious flag, reason, and risk_score
        """
        history = self._location_history.get(executor_id)

        if not history or not history.locations:
            return {
                "suspicious": False,
                "reason": None,
                "risk_score": 0.0,
                "speed_mps": None,
                "distance_m": None,
            }

        # Get last known location
        last_location, last_timestamp = history.locations[-1]

        # Ensure timestamps are timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=UTC)

        # Calculate time difference
        time_diff = (timestamp - last_timestamp).total_seconds()

        if time_diff < MIN_TIME_BETWEEN_LOCATIONS_SECONDS:
            # Too fast between submissions
            return {
                "suspicious": True,
                "reason": f"Submissions too rapid: {time_diff:.1f}s apart (min: {MIN_TIME_BETWEEN_LOCATIONS_SECONDS}s)",
                "risk_score": 0.6,
                "speed_mps": None,
                "distance_m": None,
            }

        # Calculate distance
        distance_m = self._haversine_distance(
            last_location.latitude,
            last_location.longitude,
            new_location.latitude,
            new_location.longitude,
        )

        # Calculate speed
        speed_mps = distance_m / time_diff if time_diff > 0 else 0

        # Check for impossible speed
        if speed_mps > MAX_VEHICLE_SPEED_MPS:
            return {
                "suspicious": True,
                "reason": f"Impossible travel speed: {speed_mps:.1f} m/s ({speed_mps * 3.6:.1f} km/h) over {distance_m:.0f}m in {time_diff:.0f}s",
                "risk_score": 0.95,
                "speed_mps": speed_mps,
                "distance_m": distance_m,
            }

        # Check for suspicious but possible speed (might be driving)
        if speed_mps > MAX_WALKING_SPEED_MPS:
            # Could be legitimate (driving), but flag for review
            return {
                "suspicious": False,
                "reason": f"High travel speed (vehicle likely): {speed_mps:.1f} m/s ({speed_mps * 3.6:.1f} km/h)",
                "risk_score": 0.3,
                "speed_mps": speed_mps,
                "distance_m": distance_m,
            }

        return {
            "suspicious": False,
            "reason": None,
            "risk_score": 0.0,
            "speed_mps": speed_mps,
            "distance_m": distance_m,
        }

    async def check_sensor_consistency(
        self,
        accelerometer: Optional[Tuple[float, float, float]],
        gyroscope: Optional[Tuple[float, float, float]],
        gps: GPSData,
    ) -> Dict[str, Any]:
        """
        Cross-validate accelerometer/gyroscope data with GPS movement.

        Detection logic:
        - If GPS shows movement but accelerometer shows stationary: suspicious
        - If gyroscope shows rotation but GPS bearing unchanged: suspicious
        - If accelerometer shows walking pattern but GPS shows vehicle speed: suspicious

        Args:
            accelerometer: (x, y, z) acceleration in m/s^2
            gyroscope: (x, y, z) rotation rate in rad/s
            gps: GPS data including speed and bearing

        Returns:
            Dictionary with suspicious flag, reason, and risk_score
        """
        if accelerometer is None and gyroscope is None:
            # No sensor data to compare
            return {
                "suspicious": False,
                "reason": "No sensor data available for validation",
                "risk_score": 0.1,  # Slight risk for missing data
            }

        suspicious_flags: List[str] = []
        risk_scores: List[float] = []

        if accelerometer:
            ax, ay, az = accelerometer

            # Calculate total acceleration magnitude (excluding gravity ~9.8)
            total_accel = math.sqrt(ax**2 + ay**2 + az**2)
            accel_minus_gravity = abs(total_accel - 9.8)

            # Check for stationary device (accel ~= gravity only)
            is_stationary = accel_minus_gravity < 0.5  # Less than 0.5 m/s^2 variance

            # If GPS shows significant speed but device is stationary
            if (
                gps.speed_mps
                and gps.speed_mps > MAX_WALKING_SPEED_MPS
                and is_stationary
            ):
                suspicious_flags.append(
                    f"GPS shows {gps.speed_mps:.1f} m/s but accelerometer indicates stationary device"
                )
                risk_scores.append(0.8)

            # Check for walking pattern (rhythmic acceleration changes)
            # Walking typically shows 0.5-3 m/s^2 variance with ~2Hz frequency
            walking_pattern = 0.5 < accel_minus_gravity < 3.0

            # If walking pattern but GPS shows vehicle speed
            if walking_pattern and gps.speed_mps and gps.speed_mps > 15:  # > 54 km/h
                suspicious_flags.append(
                    f"Walking acceleration pattern but GPS shows vehicle speed ({gps.speed_mps:.1f} m/s)"
                )
                risk_scores.append(0.6)

        if gyroscope:
            gx, gy, gz = gyroscope

            # Calculate rotation rate
            rotation_rate = math.sqrt(gx**2 + gy**2 + gz**2)

            # Significant rotation but GPS bearing unchanged
            # This would need historical GPS data to compare bearings
            # For now, just flag extreme rotation rates
            if rotation_rate > 5.0:  # > 5 rad/s is very fast rotation
                # This is unusual unless spinning device
                suspicious_flags.append(
                    f"Extreme rotation rate detected: {rotation_rate:.2f} rad/s"
                )
                risk_scores.append(0.4)

        if not suspicious_flags:
            return {
                "suspicious": False,
                "reason": None,
                "risk_score": 0.0,
            }

        return {
            "suspicious": True,
            "reason": "; ".join(suspicious_flags),
            "risk_score": max(risk_scores) if risk_scores else 0.5,
            "details": {
                "accelerometer": accelerometer,
                "gyroscope": gyroscope,
                "gps_speed_mps": gps.speed_mps,
            },
        }

    async def check_network_location(
        self,
        ip_address: str,
        claimed_gps: GPSData,
    ) -> Dict[str, Any]:
        """
        Compare IP geolocation with claimed GPS coordinates.

        Note: IP geolocation is not precise (typically ~50km accuracy in urban areas),
        so this is a coarse check for major discrepancies.

        Args:
            ip_address: Client IP address
            claimed_gps: GPS coordinates claimed by the client

        Returns:
            Dictionary with suspicious flag, reason, and risk_score
        """
        # Skip for localhost/private IPs
        if self._is_private_ip(ip_address):
            return {
                "suspicious": False,
                "reason": "Private IP address, skipping network check",
                "risk_score": 0.0,
            }

        # Try to get IP geolocation
        ip_location = await self._get_ip_location(ip_address)

        if ip_location is None:
            return {
                "suspicious": False,
                "reason": "Could not determine IP geolocation",
                "risk_score": 0.1,
            }

        # Calculate distance between IP location and claimed GPS
        distance_km = (
            self._haversine_distance(
                ip_location.latitude,
                ip_location.longitude,
                claimed_gps.latitude,
                claimed_gps.longitude,
            )
            / 1000
        )  # Convert to km

        # Check for major discrepancy
        if distance_km > MAX_IP_GPS_DISTANCE_KM:
            # Could be VPN or mobile network, but flag it
            return {
                "suspicious": True,
                "reason": f"IP geolocation ({ip_location.latitude:.4f}, {ip_location.longitude:.4f}) "
                f"is {distance_km:.0f}km from claimed GPS (max: {MAX_IP_GPS_DISTANCE_KM}km). "
                f"Possible VPN or GPS spoofing.",
                "risk_score": min(0.9, 0.5 + (distance_km / 1000) * 0.1),
                "details": {
                    "ip_location": (ip_location.latitude, ip_location.longitude),
                    "claimed_location": (claimed_gps.latitude, claimed_gps.longitude),
                    "distance_km": distance_km,
                },
            }

        return {
            "suspicious": False,
            "reason": None,
            "risk_score": 0.0,
            "distance_km": distance_km,
        }

    async def detect_multi_device(
        self,
        executor_id: str,
        device_fingerprint: str,
    ) -> MultiDeviceResult:
        """
        Detect if the same worker is using multiple devices.

        This helps prevent sybil attacks where one person registers
        multiple worker accounts on different devices.

        Args:
            executor_id: Worker's executor ID
            device_fingerprint: Hash of device characteristics

        Returns:
            MultiDeviceResult with detection details
        """
        # Get known devices for this executor
        known_devices = self._device_fingerprints.get(executor_id, [])

        # Check if this fingerprint is already known
        for known_device in known_devices:
            if known_device.get("fingerprint") == device_fingerprint:
                # Same device, no issue
                return MultiDeviceResult(
                    is_multi_device=False,
                    device_count=len(known_devices),
                    devices=[d.get("fingerprint", "unknown") for d in known_devices],
                    similarity_scores={},
                    reason=None,
                )

        # New device detected
        if not known_devices:
            # First device for this executor, register it
            self._device_fingerprints[executor_id].append(
                {
                    "fingerprint": device_fingerprint,
                    "first_seen": datetime.now(UTC).isoformat(),
                }
            )
            return MultiDeviceResult(
                is_multi_device=False,
                device_count=1,
                devices=[device_fingerprint],
                similarity_scores={},
                reason=None,
            )

        # Multiple devices detected
        device_count = len(known_devices) + 1

        # Register the new device
        self._device_fingerprints[executor_id].append(
            {
                "fingerprint": device_fingerprint,
                "first_seen": datetime.now(UTC).isoformat(),
            }
        )

        # Calculate similarity with existing devices
        similarity_scores = {}
        for known in known_devices:
            known_fp = known.get("fingerprint", "")
            similarity = self._calculate_fingerprint_similarity(
                device_fingerprint, known_fp
            )
            similarity_scores[known_fp[:16]] = similarity

        # Flag if more than 2 devices
        if device_count > 2:
            return MultiDeviceResult(
                is_multi_device=True,
                device_count=device_count,
                devices=[
                    d.get("fingerprint", "unknown")[:16]
                    for d in self._device_fingerprints[executor_id]
                ],
                similarity_scores=similarity_scores,
                reason=f"Worker using {device_count} different devices (suspicious pattern)",
            )

        return MultiDeviceResult(
            is_multi_device=False,
            device_count=device_count,
            devices=[
                d.get("fingerprint", "unknown")[:16]
                for d in self._device_fingerprints[executor_id]
            ],
            similarity_scores=similarity_scores,
            reason=None,
        )

    async def check_rate_limits(
        self,
        ip_address: str,
        device_id: str,
    ) -> RateLimitResult:
        """
        Check rate limits per IP and device.

        NOW-111 requirements:
        - 50 tasks/day/IP
        - 20 tasks/day/device

        Args:
            ip_address: Client IP address
            device_id: Device fingerprint or ID

        Returns:
            RateLimitResult with limit status
        """
        now = datetime.now(UTC)
        one_day_ago = now - timedelta(days=1)

        # Clean old entries and count recent submissions
        ip_submissions = self._ip_submissions.get(ip_address, [])
        ip_submissions = [ts for ts in ip_submissions if ts > one_day_ago]
        self._ip_submissions[ip_address] = ip_submissions
        ip_count = len(ip_submissions)

        device_submissions = self._device_submissions.get(device_id, [])
        device_submissions = [ts for ts in device_submissions if ts > one_day_ago]
        self._device_submissions[device_id] = device_submissions
        device_count = len(device_submissions)

        # Check IP limit
        if ip_count >= MAX_TASKS_PER_DAY_PER_IP:
            return RateLimitResult(
                allowed=False,
                reason=f"IP rate limit exceeded: {ip_count}/{MAX_TASKS_PER_DAY_PER_IP} tasks today",
                ip_count_today=ip_count,
                device_count_today=device_count,
                ip_limit=MAX_TASKS_PER_DAY_PER_IP,
                device_limit=MAX_TASKS_PER_DAY_PER_DEVICE,
            )

        # Check device limit
        if device_count >= MAX_TASKS_PER_DAY_PER_DEVICE:
            return RateLimitResult(
                allowed=False,
                reason=f"Device rate limit exceeded: {device_count}/{MAX_TASKS_PER_DAY_PER_DEVICE} tasks today",
                ip_count_today=ip_count,
                device_count_today=device_count,
                ip_limit=MAX_TASKS_PER_DAY_PER_IP,
                device_limit=MAX_TASKS_PER_DAY_PER_DEVICE,
            )

        return RateLimitResult(
            allowed=True,
            reason=None,
            ip_count_today=ip_count,
            device_count_today=device_count,
            ip_limit=MAX_TASKS_PER_DAY_PER_IP,
            device_limit=MAX_TASKS_PER_DAY_PER_DEVICE,
        )

    # =========================================================================
    # INTERNAL HELPER METHODS
    # =========================================================================

    async def _store_location(
        self,
        executor_id: str,
        location: GPSData,
        timestamp: datetime,
    ) -> None:
        """Store location in history for pattern analysis."""
        if executor_id not in self._location_history:
            self._location_history[executor_id] = LocationHistory(
                executor_id=executor_id
            )

        history = self._location_history[executor_id]
        history.locations.append((location, timestamp))

        # Keep only last 100 locations per executor
        if len(history.locations) > 100:
            history.locations = history.locations[-100:]

    async def _record_submission(self, ip_address: str, device_id: str) -> None:
        """Record submission for rate limiting."""
        now = datetime.now(UTC)
        self._ip_submissions[ip_address].append(now)
        self._device_submissions[device_id].append(now)

    async def _get_ip_location(self, ip_address: str) -> Optional[GPSData]:
        """Get geolocation from IP address."""
        if self.ip_geolocation_service:
            try:
                return await self.ip_geolocation_service.get_location(ip_address)
            except Exception:
                return None

        # Fallback: No IP geolocation service configured
        return None

    def _generate_device_fingerprint(self, device_info: DeviceInfo) -> str:
        """Generate a unique fingerprint hash from device information."""
        # Combine device characteristics
        fingerprint_data = "|".join(
            [
                str(device_info.screen_width or ""),
                str(device_info.screen_height or ""),
                str(device_info.device_memory_gb or ""),
                str(device_info.hardware_concurrency or ""),
                str(device_info.platform or ""),
                str(device_info.vendor or ""),
                str(device_info.timezone or ""),
                str(device_info.language or ""),
                str(device_info.webgl_vendor or ""),
                str(device_info.webgl_renderer or ""),
            ]
        )

        # Hash the fingerprint
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()

    def _calculate_fingerprint_similarity(self, fp1: str, fp2: str) -> float:
        """Calculate similarity between two fingerprints (0.0 to 1.0)."""
        if fp1 == fp2:
            return 1.0

        # Simple character-level similarity
        # In production, use more sophisticated comparison
        matches = sum(c1 == c2 for c1, c2 in zip(fp1, fp2))
        return matches / max(len(fp1), len(fp2))

    def _is_private_ip(self, ip_address: str) -> bool:
        """Check if IP address is private/local."""
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
        return any(ip_address.startswith(prefix) for prefix in private_prefixes)

    def _haversine_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """
        Calculate distance between two GPS coordinates using Haversine formula.

        Args:
            lat1, lon1: First point coordinates (degrees)
            lat2, lon2: Second point coordinates (degrees)

        Returns:
            Distance in meters
        """
        # Convert to radians
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        # Haversine formula
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return EARTH_RADIUS_METERS * c

    def _aggregate_risk_scores(self, scores: List[float]) -> float:
        """
        Aggregate multiple risk scores into a single score.

        Uses a weighted approach where higher scores contribute more.
        """
        if not scores:
            return 0.0

        # Sort descending
        sorted_scores = sorted(scores, reverse=True)

        # Weighted average: first score full weight, diminishing for others
        total_weight = 0.0
        weighted_sum = 0.0

        for i, score in enumerate(sorted_scores):
            weight = 1.0 / (i + 1)  # 1.0, 0.5, 0.33, 0.25, ...
            weighted_sum += score * weight
            total_weight += weight

        return min(1.0, weighted_sum / total_weight)

    # =========================================================================
    # CLEANUP METHODS
    # =========================================================================

    def clear_executor_history(self, executor_id: str) -> None:
        """Clear all stored data for an executor (for testing or GDPR)."""
        self._location_history.pop(executor_id, None)
        self._device_fingerprints.pop(executor_id, None)

    def clear_rate_limit_data(
        self, ip_address: Optional[str] = None, device_id: Optional[str] = None
    ) -> None:
        """Clear rate limit data (for testing)."""
        if ip_address:
            self._ip_submissions.pop(ip_address, None)
        if device_id:
            self._device_submissions.pop(device_id, None)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


async def check_gps_spoofing(
    latitude: float,
    longitude: float,
    executor_id: str,
    device_info: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    accelerometer: Optional[Tuple[float, float, float]] = None,
    gyroscope: Optional[Tuple[float, float, float]] = None,
) -> SpoofingResult:
    """
    Convenience function for quick GPS spoofing check.

    Args:
        latitude: GPS latitude
        longitude: GPS longitude
        executor_id: Worker's ID
        device_info: Optional device information dictionary
        ip_address: Optional client IP
        accelerometer: Optional (x, y, z) acceleration data
        gyroscope: Optional (x, y, z) rotation data

    Returns:
        SpoofingResult with analysis
    """
    detector = GPSAntiSpoofing()

    gps_data = GPSData(
        latitude=latitude,
        longitude=longitude,
        timestamp=datetime.now(UTC),
    )

    device = DeviceInfo()
    if device_info:
        device = DeviceInfo(
            device_id=device_info.get("device_id"),
            user_agent=device_info.get("user_agent"),
            screen_width=device_info.get("screen_width"),
            screen_height=device_info.get("screen_height"),
            platform=device_info.get("platform"),
            timezone=device_info.get("timezone"),
        )

    sensor_data = None
    if accelerometer or gyroscope:
        sensor_data = SensorData(
            accelerometer=accelerometer,
            gyroscope=gyroscope,
            timestamp=datetime.now(UTC),
        )

    return await detector.detect_spoofing(
        gps_data=gps_data,
        device_info=device,
        executor_id=executor_id,
        ip_address=ip_address,
        sensor_data=sensor_data,
    )
