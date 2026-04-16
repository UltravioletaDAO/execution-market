"""
Shared GPS extraction helpers for the verification stack.

This module centralizes GPS lookup logic so both the Phase A pipeline
(`verification.pipeline`) and the Phase B AI prompt builder
(`verification.prompts.base`) can agree on where GPS lives inside an
evidence payload. Historically this logic lived only in `pipeline.py`,
which meant the AI prompt shipped "GPS coordinates: Not provided" for
perfectly valid browser-captured evidence (see WS-1 of the geo-matching
master plan, 2026-04-16).

Public API:
- `extract_gps_from_evidence(evidence) -> (lat, lng)`
    Backwards-compatible signature used by pipeline & background_runner.
- `extract_gps_details(evidence) -> dict | None`
    Richer extraction that also surfaces accuracy, altitude, and a
    human-readable `source` note ("browser geolocation", "EXIF", etc.).
- `format_gps_for_prompt(evidence) -> str`
    One-line rendering used by the PHOTINT prompt.

Null island ((0, 0) coordinates) is treated as "not provided" by
`extract_gps_details` / `format_gps_for_prompt` because that's the
default returned by broken/uninitialised GPS chipsets. The legacy
(lat, lng) helper preserves historical behaviour and does NOT filter
null island — the Phase A pipeline decides what to do with those
readings.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Evidence keys that are expected to contain nested photo-like payloads.
# `background_runner.py` and the antispoofing flow rely on this list.
_PHOTO_LIKE_KEYS = ("photo", "photo_geo", "screenshot", "document", "receipt", "video")


def _coerce_coord(value: Any) -> Optional[float]:
    """Coerce a coordinate value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_null_island(lat: Optional[float], lng: Optional[float]) -> bool:
    """Return True when coords are effectively (0, 0) — a well-known
    sentinel for uninitialised GPS hardware."""
    if lat is None or lng is None:
        return False
    return abs(lat) < 1e-9 and abs(lng) < 1e-9


def _read_lat_lng(obj: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    """Pull lat/lng (with latitude/longitude/lon aliases) from a dict."""
    lat = _coerce_coord(obj.get("lat") or obj.get("latitude"))
    lng = _coerce_coord(obj.get("lng") or obj.get("longitude") or obj.get("lon"))
    return lat, lng


def _classify_source(path: str, raw: Dict[str, Any]) -> str:
    """Produce a short human-readable source note for the prompt.

    Heuristic: if the raw dict carries `accuracy` (W3C Geolocation API
    contract — meters of uncertainty) or sits in a `*_metadata.gps`
    slot, we call it "browser geolocation". If it sits anywhere EXIF
    writes land (photo_geo_direct, or raw has no accuracy but has
    altitude), we call it "EXIF". Otherwise just echo the path.
    """
    has_accuracy = "accuracy" in raw
    if path.endswith("metadata_gps") or path == "photo_geo_metadata_gps":
        return "browser geolocation"
    if has_accuracy:
        return "browser geolocation"
    if path == "forensic":
        return "forensic metadata"
    if path == "device_metadata":
        return "device metadata"
    if path in ("direct_gps", "photo_geo_direct", "photo_geo_metadata"):
        # Top-level / shallow GPS with no accuracy marker — most
        # likely EXIF-derived or an agent-provided claim.
        return "EXIF"
    return path.replace("_", " ")


def _candidate_blobs(evidence: Dict[str, Any]):
    """Yield (path, dict) candidates in priority order.

    Order mirrors `pipeline._extract_gps_from_evidence` so both helpers
    produce identical hit paths.
    """
    # 1. Direct top-level GPS / location / coordinates — preserve the
    #    historical `evidence.get("gps") or evidence.get("location") or
    #    evidence.get("coordinates")` short-circuit so only the first
    #    truthy dict is considered (see pipeline.py pre-WS-1 refactor).
    direct_blob = (
        evidence.get("gps") or evidence.get("location") or evidence.get("coordinates")
    )
    if isinstance(direct_blob, dict):
        yield "direct_gps", direct_blob

    # 2. `photo_geo` in three variants: top-level, .metadata, .metadata.gps
    photo_geo = evidence.get("photo_geo")
    if isinstance(photo_geo, dict):
        yield "photo_geo_direct", photo_geo
        metadata = photo_geo.get("metadata")
        if isinstance(metadata, dict):
            yield "photo_geo_metadata", metadata
            meta_gps = metadata.get("gps")
            if isinstance(meta_gps, dict):
                yield "photo_geo_metadata_gps", meta_gps

    # 3. Nested gps / metadata.gps inside known photo-like keys.
    for key in _PHOTO_LIKE_KEYS:
        item = evidence.get(key)
        if not isinstance(item, dict):
            continue
        nested_gps = item.get("gps")
        if isinstance(nested_gps, dict):
            yield f"nested_{key}_gps", nested_gps
        item_meta = item.get("metadata")
        if isinstance(item_meta, dict):
            meta_gps = item_meta.get("gps")
            if isinstance(meta_gps, dict):
                yield f"nested_{key}_metadata_gps", meta_gps

    # 4. Forensic metadata blob.
    forensics = evidence.get("forensic_metadata") or evidence.get("device_info")
    if isinstance(forensics, dict):
        loc = forensics.get("location") or forensics.get("gps")
        if isinstance(loc, dict):
            yield "forensic", loc

    # 5. Mobile device metadata.
    device_meta = evidence.get("device_metadata")
    if isinstance(device_meta, dict):
        dm_gps = device_meta.get("gps")
        if isinstance(dm_gps, dict):
            yield "device_metadata", dm_gps

    # 6. Catch-all: any other top-level key carrying gps or metadata.gps.
    checked_keys = {
        "gps",
        "location",
        "coordinates",
        "photo_geo",
        "forensic_metadata",
        "device_info",
        "device_metadata",
        *_PHOTO_LIKE_KEYS,
    }
    for key, item in evidence.items():
        if key in checked_keys or not isinstance(item, dict):
            continue
        nested_gps = item.get("gps")
        if isinstance(nested_gps, dict):
            yield f"catchall_{key}_gps", nested_gps
        item_meta = item.get("metadata")
        if isinstance(item_meta, dict):
            meta_gps = item_meta.get("gps")
            if isinstance(meta_gps, dict):
                yield f"catchall_{key}_metadata_gps", meta_gps


def _find_first_gps_blob(
    evidence: Dict[str, Any], *, reject_null_island: bool
) -> Optional[Tuple[str, Dict[str, Any], float, float]]:
    """Walk candidate blobs and return the first one with usable coords.

    Returns (path, blob, lat, lng) or None.
    """
    if not isinstance(evidence, dict):
        return None
    for path, blob in _candidate_blobs(evidence):
        lat, lng = _read_lat_lng(blob)
        if lat is None or lng is None:
            continue
        if reject_null_island and _is_null_island(lat, lng):
            logger.info("[AUDIT] gps_utils skipping null-island at path=%s", path)
            continue
        return path, blob, lat, lng
    return None


def extract_gps_details(evidence: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a dict with lat/lng plus optional accuracy/altitude/source.

    Returns `None` when no usable GPS is found. Null island coordinates
    ((0, 0) — the default uninitialised-GPS sentinel) are rejected so
    the AI prompt doesn't render them as a legitimate location.

    Shape:
        {
            "lat": float,
            "lng": float,
            "accuracy": float | None,   # meters
            "altitude": float | None,   # meters
            "source": str,              # short human note
            "path": str,                # internal path tag (debug)
        }
    """
    hit = _find_first_gps_blob(evidence, reject_null_island=True)
    if hit is None:
        logger.info(
            "[AUDIT] extract_gps_details no_gps_found evidence_keys=%s",
            list(evidence.keys()) if isinstance(evidence, dict) else "non_dict",
        )
        return None
    path, blob, lat, lng = hit
    accuracy = _coerce_coord(blob.get("accuracy"))
    altitude = _coerce_coord(blob.get("altitude") or blob.get("alt"))
    return {
        "lat": lat,
        "lng": lng,
        "accuracy": accuracy,
        "altitude": altitude,
        "source": _classify_source(path, blob),
        "path": path,
    }


def extract_gps_from_evidence(
    evidence: Dict[str, Any],
) -> Tuple[Optional[float], Optional[float]]:
    """Backwards-compatible (lat, lng) extraction used by pipeline & background_runner.

    Null island (0, 0) is NOT rejected here so we preserve historical
    behaviour: the Phase A proximity check decides what to do with a
    (0, 0) reading. Returns `(None, None)` only when no GPS blob at all
    was found in the evidence payload.
    """
    hit = _find_first_gps_blob(evidence, reject_null_island=False)
    if hit is None:
        return None, None
    _path, _blob, lat, lng = hit
    return lat, lng


def format_gps_for_prompt(evidence: Dict[str, Any]) -> str:
    """Render GPS details as a one-line string for the AI verifier prompt.

    Returns `"Not provided"` when no GPS is present. Otherwise returns
    something like:
        "25.761700, -80.191800 (source: browser geolocation; accuracy: 15m)"
    """
    details = extract_gps_details(evidence)
    if details is None:
        return "Not provided"

    lat = details["lat"]
    lng = details["lng"]
    parts = [f"{lat:.6f}, {lng:.6f}"]

    extras = [f"source: {details['source']}"]
    accuracy = details.get("accuracy")
    if accuracy is not None:
        extras.append(f"accuracy: {accuracy:g}m")
    altitude = details.get("altitude")
    if altitude is not None:
        extras.append(f"altitude: {altitude:g}m")
    parts.append("(" + "; ".join(extras) + ")")
    return " ".join(parts)
