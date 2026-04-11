"""
GPS Location Verification

Validates that photo GPS coordinates match task location requirements.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class GPSResult:
    """Result of GPS verification."""

    is_valid: bool
    distance_meters: Optional[float]
    photo_coords: Optional[Tuple[float, float]]
    task_coords: Optional[Tuple[float, float]]
    max_distance: float
    reason: Optional[str]

    @property
    def normalized_score(self) -> float:
        """Normalized score 0.0-1.0 where 1.0 = GPS matches perfectly (passed).

        Proportional: distance=0 -> 1.0, distance>=max_distance -> 0.0.
        No GPS coordinates at all -> 0.0 (failed check).
        """
        if self.distance_meters is None:
            return 0.0  # No GPS data = failed
        if self.max_distance <= 0:
            return 1.0 if self.distance_meters == 0 else 0.0
        # Linear decay: at max_distance score is 0.0
        ratio = max(0.0, 1.0 - (self.distance_meters / self.max_distance))
        return round(ratio, 4)


def check_gps_location(
    photo_lat: Optional[float],
    photo_lng: Optional[float],
    task_lat: float,
    task_lng: float,
    max_distance_meters: float = 500,
) -> GPSResult:
    """
    Check if photo GPS coordinates are within range of task location.

    Args:
        photo_lat: Photo latitude (from EXIF)
        photo_lng: Photo longitude (from EXIF)
        task_lat: Task required latitude
        task_lng: Task required longitude
        max_distance_meters: Maximum allowed distance (default 500m)

    Returns:
        GPSResult with validation details
    """
    # Check if photo has GPS
    if photo_lat is None or photo_lng is None:
        return GPSResult(
            is_valid=False,
            distance_meters=None,
            photo_coords=None,
            task_coords=(task_lat, task_lng),
            max_distance=max_distance_meters,
            reason="Photo does not contain GPS coordinates",
        )

    # Calculate distance
    distance = haversine_distance(photo_lat, photo_lng, task_lat, task_lng)

    if distance > max_distance_meters:
        return GPSResult(
            is_valid=False,
            distance_meters=distance,
            photo_coords=(photo_lat, photo_lng),
            task_coords=(task_lat, task_lng),
            max_distance=max_distance_meters,
            reason=f"Photo location is {distance:.0f}m from task location (max: {max_distance_meters}m)",
        )

    return GPSResult(
        is_valid=True,
        distance_meters=distance,
        photo_coords=(photo_lat, photo_lng),
        task_coords=(task_lat, task_lng),
        max_distance=max_distance_meters,
        reason=None,
    )


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates

    Returns:
        Distance in meters
    """
    R = 6371000  # Earth's radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def extract_gps_from_exif(exif_data: dict) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract GPS coordinates from EXIF data.

    Args:
        exif_data: EXIF data dictionary

    Returns:
        Tuple of (latitude, longitude) or (None, None)
    """
    try:
        # Get GPS data
        gps_lat = exif_data.get("GPSLatitude")
        gps_lat_ref = exif_data.get("GPSLatitudeRef", "N")
        gps_lng = exif_data.get("GPSLongitude")
        gps_lng_ref = exif_data.get("GPSLongitudeRef", "E")

        if not gps_lat or not gps_lng:
            return None, None

        # Convert DMS to decimal
        lat = convert_to_decimal(gps_lat, gps_lat_ref)
        lng = convert_to_decimal(gps_lng, gps_lng_ref)

        return lat, lng

    except Exception:
        return None, None


def convert_to_decimal(dms: tuple, ref: str) -> float:
    """
    Convert GPS coordinates from DMS (degrees, minutes, seconds) to decimal.

    Args:
        dms: Tuple of (degrees, minutes, seconds) - each may be a tuple (num, denom)
        ref: Reference (N/S for lat, E/W for lng)

    Returns:
        Decimal degrees
    """

    def to_float(value):
        if isinstance(value, tuple):
            return value[0] / value[1]
        return float(value)

    degrees = to_float(dms[0])
    minutes = to_float(dms[1])
    seconds = to_float(dms[2]) if len(dms) > 2 else 0

    decimal = degrees + minutes / 60 + seconds / 3600

    if ref in ("S", "W"):
        decimal = -decimal

    return decimal
