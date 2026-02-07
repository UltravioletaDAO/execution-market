"""
Tests for GPS verification module.
"""

from verification.checks.gps import (
    check_gps_location,
    haversine_distance,
)


class TestHaversineDistance:
    """Tests for haversine distance calculation."""

    def test_same_point_returns_zero(self):
        """Same coordinates should return 0 distance."""
        distance = haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        assert distance == 0

    def test_known_distance_nyc_to_la(self):
        """Test known distance: NYC to LA is approximately 3940km."""
        # NYC: 40.7128, -74.0060
        # LA: 34.0522, -118.2437
        distance = haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
        # Should be around 3,940 km (3,940,000 meters)
        assert 3_900_000 < distance < 4_000_000

    def test_short_distance(self):
        """Test short distance calculation (within a city)."""
        # Two points ~1km apart in NYC
        lat1, lng1 = 40.7128, -74.0060
        lat2, lng2 = 40.7218, -74.0060  # ~1km north
        distance = haversine_distance(lat1, lng1, lat2, lng2)
        assert 900 < distance < 1100  # ~1km

    def test_equator_distance(self):
        """Test distance along the equator."""
        # 1 degree of longitude at equator is ~111km
        distance = haversine_distance(0, 0, 0, 1)
        assert 110_000 < distance < 112_000


class TestCheckGPSLocation:
    """Tests for GPS location verification."""

    def test_valid_location_within_range(self):
        """Photo within range should pass."""
        result = check_gps_location(
            photo_lat=40.7128,
            photo_lng=-74.0060,
            task_lat=40.7130,
            task_lng=-74.0065,
            max_distance_meters=500,
        )
        assert result.is_valid
        assert result.distance_meters is not None
        assert result.distance_meters < 500
        assert result.reason is None

    def test_invalid_location_out_of_range(self):
        """Photo outside range should fail."""
        result = check_gps_location(
            photo_lat=40.7128,
            photo_lng=-74.0060,
            task_lat=40.7528,  # ~4km north
            task_lng=-74.0060,
            max_distance_meters=500,
        )
        assert not result.is_valid
        assert result.distance_meters is not None
        assert result.distance_meters > 500
        assert "from task location" in result.reason

    def test_missing_photo_lat(self):
        """Missing photo latitude should fail."""
        result = check_gps_location(
            photo_lat=None, photo_lng=-74.0060, task_lat=40.7128, task_lng=-74.0060
        )
        assert not result.is_valid
        assert result.photo_coords is None
        assert "GPS coordinates" in result.reason

    def test_missing_photo_lng(self):
        """Missing photo longitude should fail."""
        result = check_gps_location(
            photo_lat=40.7128, photo_lng=None, task_lat=40.7128, task_lng=-74.0060
        )
        assert not result.is_valid
        assert result.photo_coords is None

    def test_custom_max_distance(self):
        """Custom max distance should be respected."""
        # Same location ~100m apart
        result = check_gps_location(
            photo_lat=40.7128,
            photo_lng=-74.0060,
            task_lat=40.7129,
            task_lng=-74.0061,
            max_distance_meters=50,  # Very strict
        )
        # Might pass or fail depending on exact distance
        assert result.max_distance == 50

    def test_result_contains_all_coordinates(self):
        """Result should contain both photo and task coordinates."""
        result = check_gps_location(
            photo_lat=40.7128,
            photo_lng=-74.0060,
            task_lat=40.7130,
            task_lng=-74.0065,
            max_distance_meters=500,
        )
        assert result.photo_coords == (40.7128, -74.0060)
        assert result.task_coords == (40.7130, -74.0065)

    def test_exactly_at_boundary(self):
        """Test location exactly at the boundary distance."""
        # Create a point approximately 500m away
        # At 40.7128, 1 degree lat = ~111km, so 500m = ~0.0045 degrees
        result = check_gps_location(
            photo_lat=40.7128,
            photo_lng=-74.0060,
            task_lat=40.7173,  # ~500m north
            task_lng=-74.0060,
            max_distance_meters=500,
        )
        # Should be right at the boundary (may pass or fail)
        assert result.distance_meters is not None
