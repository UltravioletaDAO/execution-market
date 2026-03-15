"""Tests for geocoding service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from integrations.geocoding import geocode_location, RADIUS_BY_TYPE


@pytest.fixture
def mock_nominatim_city():
    """Mock Nominatim response for a city (Miami Gardens)."""
    return [
        {
            "lat": "25.9420377",
            "lon": "-80.2456045",
            "display_name": "Miami Gardens, Miami-Dade County, Florida, USA",
            "type": "city",
            "class": "place",
            "boundingbox": ["25.9102", "25.9767", "-80.2838", "-80.1758"],
        }
    ]


@pytest.fixture
def mock_nominatim_address():
    """Mock Nominatim response for a specific address."""
    return [
        {
            "lat": "40.7484",
            "lon": "-73.9857",
            "display_name": "Empire State Building, 350 5th Ave, New York, NY 10118, USA",
            "type": "building",
            "class": "tourism",
            "boundingbox": ["40.7479", "40.7489", "-73.9862", "-73.9852"],
        }
    ]


@pytest.mark.asyncio
async def test_geocode_city(mock_nominatim_city):
    """City geocoding returns appropriate radius."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_nominatim_city
    mock_response.raise_for_status = MagicMock()

    with patch("integrations.geocoding.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await geocode_location("Miami Gardens")

    assert result is not None
    assert abs(result.lat - 25.942) < 0.01
    assert abs(result.lng - (-80.246)) < 0.01
    assert result.place_type == "city"
    assert result.radius_km >= 5.0  # Cities should have generous radius


@pytest.mark.asyncio
async def test_geocode_building(mock_nominatim_address):
    """Building geocoding returns small radius."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_nominatim_address
    mock_response.raise_for_status = MagicMock()

    with patch("integrations.geocoding.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await geocode_location("Empire State Building, NYC")

    assert result is not None
    assert result.place_type == "building"
    assert result.radius_km <= 2.0  # Buildings should have tight radius


@pytest.mark.asyncio
async def test_geocode_empty_string():
    """Empty string returns None without making HTTP request."""
    result = await geocode_location("")
    assert result is None


@pytest.mark.asyncio
async def test_geocode_none():
    """None input returns None."""
    result = await geocode_location(None)
    assert result is None


@pytest.mark.asyncio
async def test_geocode_no_results():
    """No results returns None."""
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = MagicMock()

    with patch("integrations.geocoding.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await geocode_location("xyznonexistentplace12345")

    assert result is None


@pytest.mark.asyncio
async def test_geocode_http_error():
    """HTTP error returns None gracefully."""
    with patch("integrations.geocoding.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("Connection timeout")
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_instance

        result = await geocode_location("Miami Gardens")

    assert result is None


def test_radius_by_type_coverage():
    """Verify key place types have radius mappings."""
    assert "city" in RADIUS_BY_TYPE
    assert "town" in RADIUS_BY_TYPE
    assert "village" in RADIUS_BY_TYPE
    assert "house" in RADIUS_BY_TYPE
    assert "building" in RADIUS_BY_TYPE
    assert RADIUS_BY_TYPE["city"] > RADIUS_BY_TYPE["building"]
    assert RADIUS_BY_TYPE["town"] > RADIUS_BY_TYPE["house"]
