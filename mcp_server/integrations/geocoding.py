"""
Geocoding service for task location resolution.

Converts location text (city names, addresses) to coordinates using
OpenStreetMap Nominatim (free, no API key required).
"""

import logging
from dataclasses import dataclass
from math import cos, radians
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ExecutionMarket/1.0 (https://execution.market)"


@dataclass
class GeocodingResult:
    lat: float
    lng: float
    display_name: str
    place_type: str  # "city", "town", "village", "house", "road", etc.
    radius_km: float  # Suggested geofencing radius based on place type
    boundingbox: Optional[list[float]] = None  # [south, north, west, east]


# Radius suggestions based on place type from Nominatim
RADIUS_BY_TYPE = {
    # Large areas
    "country": 500.0,
    "state": 100.0,
    "county": 50.0,
    "city": 15.0,
    "town": 10.0,
    "municipality": 10.0,
    "suburb": 5.0,
    "borough": 5.0,
    "neighbourhood": 2.0,
    "village": 3.0,
    "hamlet": 1.0,
    # Specific locations
    "house": 0.5,
    "building": 0.5,
    "road": 1.0,
    "residential": 1.0,
    "commercial": 1.0,
    "industrial": 2.0,
    # Points of interest
    "amenity": 0.5,
    "shop": 0.3,
    "tourism": 0.5,
    "leisure": 1.0,
    "park": 2.0,
}

DEFAULT_RADIUS_KM = 10.0  # Fallback


async def geocode_location(location_text: str) -> Optional[GeocodingResult]:
    """
    Geocode a location string to coordinates.

    Uses OpenStreetMap Nominatim (free, no API key).
    Rate limit: max 1 request/second (Nominatim policy).

    Returns None if geocoding fails or no results found.
    """
    if not location_text or not location_text.strip():
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                NOMINATIM_URL,
                params={
                    "q": location_text.strip(),
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                },
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            results = response.json()

        if not results:
            logger.warning(f"[Geocoding] No results for: {location_text}")
            return None

        result = results[0]
        lat = float(result["lat"])
        lng = float(result["lon"])
        display_name = result.get("display_name", location_text)
        place_type = result.get("type", "unknown")
        place_class = result.get("class", "")

        # Determine radius from place type, then class
        radius_km = RADIUS_BY_TYPE.get(place_type)
        if radius_km is None:
            radius_km = RADIUS_BY_TYPE.get(place_class, DEFAULT_RADIUS_KM)

        # If bounding box available, calculate radius from it
        boundingbox = None
        if "boundingbox" in result:
            bb = [float(x) for x in result["boundingbox"]]
            boundingbox = bb
            # Calculate approximate radius from bounding box
            lat_diff = abs(bb[1] - bb[0])
            lng_diff = abs(bb[3] - bb[2])
            # Approximate km per degree
            km_per_lat = 111.0
            km_per_lng = 111.0 * cos(radians(lat))
            bbox_radius = max(lat_diff * km_per_lat, lng_diff * km_per_lng) / 2
            # Use bounding box radius if larger than type-based radius
            if bbox_radius > radius_km:
                radius_km = round(bbox_radius, 1)

        logger.info(
            f"[Geocoding] '{location_text}' -> ({lat:.5f}, {lng:.5f}), "
            f"type={place_type}, radius={radius_km}km"
        )

        return GeocodingResult(
            lat=round(lat, 6),
            lng=round(lng, 6),
            display_name=display_name,
            place_type=place_type,
            radius_km=radius_km,
            boundingbox=boundingbox,
        )

    except httpx.HTTPError as e:
        logger.error(f"[Geocoding] HTTP error for '{location_text}': {e}")
        return None
    except (KeyError, ValueError, IndexError) as e:
        logger.error(f"[Geocoding] Parse error for '{location_text}': {e}")
        return None
    except Exception as e:
        logger.error(f"[Geocoding] Unexpected error for '{location_text}': {e}")
        return None
