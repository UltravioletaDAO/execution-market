"""
Nominatim (OpenStreetMap) geocoding wrapper — forward + reverse.

Used as the last-resort resolver when static datasets (US ZIP, GeoNames
cities500) don't recognise a location hint. Honours Nominatim's usage
policy: <= 1 request/second per-host, meaningful User-Agent, modest
timeouts.

Design notes:
- Self-rate-limited with a per-host token bucket (not full QPS budget —
  just "no more than 1 req/s").
- In-memory LRU of size 1024 for the process lifetime. The master plan
  calls for a persistence cache (`geo_cache` table) in a later task; that
  is out of scope here.
- Timeouts return None (never raise) — callers treat None as "layer
  degraded, try the next".
- Single blocking HTTP client (`httpx.Client`) — the geo matcher API is
  sync for simplicity. If an async variant is needed later we can add
  `async_forward` + `async_reverse` alongside.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "execution-market-geo/1.0"
DEFAULT_TIMEOUT_S = 8.0
MIN_INTERVAL_S = 1.0  # Self-rate-limit: max 1 req/s per-host
LRU_SIZE = 1024


@dataclass(frozen=True)
class NominatimPlace:
    """A minimal normalized Nominatim response."""

    lat: float
    lng: float
    display_name: str
    country_code: Optional[str]  # lower-case ISO-3166-1 alpha-2
    city: Optional[str]
    state: Optional[str]
    place_type: Optional[str]  # Nominatim "type" (city, town, administrative, ...)
    place_class: Optional[str]  # Nominatim "class" (place, boundary, ...)
    raw: dict[str, Any]


class _RateLimiter:
    """Simplest possible per-host 1 req/s limiter (blocking sleep)."""

    def __init__(self, min_interval_s: float = MIN_INTERVAL_S) -> None:
        self._min = min_interval_s
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def acquire(self, host: str) -> None:
        with self._lock:
            now = time.monotonic()
            last = self._last.get(host, 0.0)
            wait = self._min - (now - last)
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._last[host] = now


class _LRU:
    """Thread-safe size-bounded LRU cache."""

    def __init__(self, maxsize: int = LRU_SIZE) -> None:
        self._max = maxsize
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any:
        with self._lock:
            if key not in self._data:
                return _LRU._MISS
            self._data.move_to_end(key)
            return self._data[key]

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = value
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    _MISS = object()


class NominatimClient:
    """Thin forward/reverse Nominatim wrapper."""

    def __init__(
        self,
        base_url: str = NOMINATIM_BASE,
        user_agent: str = USER_AGENT,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        rate_limiter: Optional[_RateLimiter] = None,
        cache: Optional[_LRU] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._ua = user_agent
        self._timeout = timeout_s
        self._rate = rate_limiter or _RateLimiter()
        self._cache = cache or _LRU()
        self._client = http_client  # Injected for tests; otherwise per-call

    # ------------------------------------------------------------------ helpers

    def _host(self) -> str:
        try:
            return httpx.URL(self._base).host
        except Exception:
            return self._base

    def _get_json(self, path: str, params: dict[str, Any]) -> Optional[Any]:
        """Execute a GET request and return parsed JSON, or None on any failure."""
        url = f"{self._base}{path}"
        try:
            self._rate.acquire(self._host())
            if self._client is not None:
                resp = self._client.get(
                    url,
                    params=params,
                    headers={"User-Agent": self._ua},
                    timeout=self._timeout,
                )
            else:
                with httpx.Client(timeout=self._timeout) as client:
                    resp = client.get(
                        url,
                        params=params,
                        headers={"User-Agent": self._ua},
                    )
            if resp.status_code == 429:
                logger.warning("nominatim: rate-limited (429) on %s", url)
                return None
            if resp.status_code >= 400:
                logger.warning(
                    "nominatim: HTTP %s on %s (%s)",
                    resp.status_code,
                    path,
                    params,
                )
                return None
            return resp.json()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            logger.warning("nominatim: network error on %s: %s", path, exc)
            return None
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("nominatim: unexpected error on %s: %s", path, exc)
            return None

    # ------------------------------------------------------------------ API

    def forward(self, query: str) -> Optional[NominatimPlace]:
        """Forward geocode a free-text hint. Returns None if unresolved."""
        if not query or not query.strip():
            return None
        cache_key = f"fwd:{query.strip().lower()}"
        cached = self._cache.get(cache_key)
        if cached is not _LRU._MISS:
            return cached
        result = self._get_json(
            "/search",
            {
                "q": query.strip(),
                "format": "jsonv2",
                "limit": 1,
                "addressdetails": 1,
            },
        )
        place = _parse_forward(result)
        # Cache None misses too — caller already re-checks static layers
        # on subsequent calls with a different hint; a repeated hit for
        # the same unresolved hint should not re-hammer Nominatim.
        self._cache.set(cache_key, place)
        return place

    def reverse(self, lat: float, lng: float) -> Optional[NominatimPlace]:
        """Reverse geocode. Returns None if unresolved."""
        cache_key = f"rev:{round(lat, 4)},{round(lng, 4)}"
        cached = self._cache.get(cache_key)
        if cached is not _LRU._MISS:
            return cached
        result = self._get_json(
            "/reverse",
            {
                "lat": lat,
                "lon": lng,
                "format": "jsonv2",
                "zoom": 10,
                "addressdetails": 1,
            },
        )
        place = _parse_reverse(result)
        self._cache.set(cache_key, place)
        return place

    # ------------------------------------------------------------------ test hooks

    def clear_cache(self) -> None:
        self._cache.clear()


def _parse_forward(result: Optional[Any]) -> Optional[NominatimPlace]:
    if not result or not isinstance(result, list):
        return None
    first = result[0]
    return _parse_single(first)


def _parse_reverse(result: Optional[Any]) -> Optional[NominatimPlace]:
    if not result or not isinstance(result, dict):
        return None
    if result.get("error"):
        return None
    return _parse_single(result)


def _parse_single(payload: dict[str, Any]) -> Optional[NominatimPlace]:
    try:
        lat = float(payload.get("lat"))
        lng = float(payload.get("lon"))
    except (TypeError, ValueError):
        return None
    address = payload.get("address") or {}
    country_code = (address.get("country_code") or "").lower() or None
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or address.get("municipality")
    )
    state = address.get("state") or address.get("region")
    return NominatimPlace(
        lat=lat,
        lng=lng,
        display_name=payload.get("display_name", ""),
        country_code=country_code,
        city=city,
        state=state,
        place_type=payload.get("type"),
        place_class=payload.get("class"),
        raw=payload,
    )
