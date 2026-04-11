"""
Weather Cross-Reference Check for Evidence Verification

If GPS coordinates and timestamp are available, queries historical
weather data and includes it as context for the PHOTINT prompt.
The vision model can then cross-reference visible weather conditions
(clear sky, rain, clouds) against the actual weather.

Uses Open-Meteo API (free, no API key needed).

Part of PHOTINT Verification Overhaul (Phase 5).
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"


@dataclass
class WeatherResult:
    """Historical weather data for cross-reference."""

    temperature_c: Optional[float] = None
    weather_code: Optional[int] = None
    weather_description: Optional[str] = None
    precipitation_mm: Optional[float] = None
    cloud_cover_pct: Optional[int] = None
    wind_speed_kmh: Optional[float] = None
    is_available: bool = False
    error: Optional[str] = None

    @property
    def normalized_score(self) -> float:
        """Normalized score 0.0-1.0 where 1.0 = weather data retrieved (passed).

        Weather is informational context, not pass/fail.
        1.0 = weather data available for cross-reference.
        0.5 = data unavailable (neutral -- does not penalize).
        0.0 = error fetching data.
        """
        if self.error:
            return 0.5  # API errors are neutral, not failures
        if self.is_available:
            return 1.0
        return 0.5  # Not available but no error = neutral

    def to_context(self) -> str:
        """Format weather data for prompt injection."""
        if not self.is_available:
            return ""

        parts = []
        if self.weather_description:
            parts.append(f"Weather: {self.weather_description}")
        if self.temperature_c is not None:
            parts.append(f"Temp: {self.temperature_c:.0f}C")
        if self.cloud_cover_pct is not None:
            parts.append(f"Cloud cover: {self.cloud_cover_pct}%")
        if self.precipitation_mm is not None and self.precipitation_mm > 0:
            parts.append(f"Precipitation: {self.precipitation_mm:.1f}mm")

        return ", ".join(parts)


# WMO weather code descriptions
_WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


async def check_weather(
    latitude: float,
    longitude: float,
    timestamp: str,
) -> WeatherResult:
    """
    Query historical weather for a location and time.

    Args:
        latitude: GPS latitude.
        longitude: GPS longitude.
        timestamp: ISO 8601 timestamp string.

    Returns:
        WeatherResult with historical weather data.
    """
    result = WeatherResult()

    try:
        # Parse timestamp to get date and hour
        dt = _parse_timestamp(timestamp)
        if dt is None:
            result.error = "Could not parse timestamp"
            return result

        date_str = dt.strftime("%Y-%m-%d")
        hour = dt.hour

        # Query Open-Meteo archive API
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": date_str,
            "end_date": date_str,
            "hourly": "temperature_2m,weathercode,precipitation,cloudcover,windspeed_10m",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(OPEN_METEO_URL, params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

        hourly = data.get("hourly", {})
        temps = hourly.get("temperature_2m", [])
        codes = hourly.get("weathercode", [])
        precip = hourly.get("precipitation", [])
        clouds = hourly.get("cloudcover", [])
        winds = hourly.get("windspeed_10m", [])

        if hour < len(temps):
            result.temperature_c = temps[hour]
        if hour < len(codes):
            result.weather_code = codes[hour]
            result.weather_description = _WMO_CODES.get(
                codes[hour], f"Code {codes[hour]}"
            )
        if hour < len(precip):
            result.precipitation_mm = precip[hour]
        if hour < len(clouds):
            result.cloud_cover_pct = (
                int(clouds[hour]) if clouds[hour] is not None else None
            )
        if hour < len(winds):
            result.wind_speed_kmh = winds[hour]

        result.is_available = True
        logger.info(
            "Weather data for %.4f,%.4f on %s %d:00: %s",
            latitude,
            longitude,
            date_str,
            hour,
            result.weather_description,
        )

    except httpx.HTTPError as e:
        result.error = f"Weather API error: {e}"
        logger.debug("Weather API failed: %s", e)
    except Exception as e:
        result.error = f"Weather check failed: {e}"
        logger.debug("Weather check failed: %s", e)

    return result


def _parse_timestamp(timestamp: str) -> Optional[datetime]:
    """Parse various timestamp formats."""
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y:%m:%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(timestamp.strip(), fmt)
        except ValueError:
            continue
    return None
