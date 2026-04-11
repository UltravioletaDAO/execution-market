"""
Evidence Verification Pipeline

Orchestrates all verification checks on a submission.
Runs checks that work without downloading files (schema, GPS, timestamp).
Image-level checks (tampering, genai, duplicate, photo_source) require
a file download step and are deferred to Phase 3.

Usage:
    result = await run_verification_pipeline(submission, task)
    # result.passed, result.score, result.details
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .checks.schema import validate_evidence_schema, SchemaValidationResult
from .checks.gps import check_gps_location, GPSResult
from .checks.timestamp import validate_submission_window
from .gps_antispoofing import GPSAntiSpoofing, GPSData, DeviceInfo, SensorData
from .attestation import (
    AttestationLevel,
    get_attestation_requirement,
)

logger = logging.getLogger(__name__)

# Categories that require physical presence (GPS verification)
PHYSICAL_CATEGORIES = {"physical_presence", "simple_action"}

# Phase A weights (sync checks, subtotal = 0.50)
PHASE_A_WEIGHTS = {
    "schema": 0.12,
    "gps": 0.12,
    "gps_antispoofing": 0.06,
    "timestamp": 0.08,
    "evidence_hash": 0.05,
    "metadata": 0.04,
    "attestation": 0.03,
}

# Phase B weights (async checks, subtotal = 0.50)
PHASE_B_WEIGHTS = {
    "ai_semantic": 0.20,
    "tampering": 0.10,
    "genai_detection": 0.05,
    "photo_source": 0.05,
    "duplicate": 0.03,
    "weather": 0.04,
    "platform_fingerprint": 0.03,
}

# Combined weights for full scoring
ALL_WEIGHTS = {**PHASE_A_WEIGHTS, **PHASE_B_WEIGHTS}

# Legacy alias for backward compatibility
CHECK_WEIGHTS = PHASE_A_WEIGHTS


@dataclass
class CheckResult:
    """Result of a single verification check."""

    name: str
    passed: bool
    score: float  # 0.0 to 1.0
    reason: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Aggregate result of the verification pipeline."""

    passed: bool
    score: float  # 0.0 to 1.0 weighted aggregate
    checks: List[CheckResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    phase: str = "A"  # "A", "B", or "AB"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSONB storage."""
        return {
            "passed": self.passed,
            "score": round(self.score, 3),
            "checks": [asdict(c) for c in self.checks],
            "warnings": self.warnings,
            "phase": self.phase,
        }


async def run_verification_pipeline(
    submission: Dict[str, Any],
    task: Dict[str, Any],
) -> VerificationResult:
    """
    Run all applicable verification checks on a submission.

    This is a non-blocking pipeline: failures flag the submission
    for manual review rather than rejecting it outright.

    Args:
        submission: Submission dict from DB (has evidence, submitted_at, etc.)
        task: Task dict from DB (has evidence_schema, category, location_*, deadline, etc.)

    Returns:
        VerificationResult with aggregate score and per-check details.
    """
    checks: List[CheckResult] = []
    warnings: List[str] = []

    evidence = submission.get("evidence") or {}
    category = task.get("category", "")

    # --- Check 1: Schema validation ---
    schema_result = _run_schema_check(evidence, task)
    checks.append(schema_result)

    # --- Check 2: GPS proximity (only for physical categories) ---
    gps_result = _run_gps_check(evidence, task, category)
    if gps_result:
        checks.append(gps_result)

        # --- Check 2b: GPS anti-spoofing (only if basic GPS passed) ---
        if gps_result.passed:
            antispoof_result = await _run_gps_antispoofing_check(
                evidence, submission, task
            )
            if antispoof_result:
                checks.append(antispoof_result)
    elif category in PHYSICAL_CATEGORIES:
        warnings.append(
            "GPS check skipped: task has no location coordinates. Agent should include location_lat/location_lng or location_hint when publishing tasks requiring physical presence."
        )

    # --- Check 3: Timestamp / submission window ---
    timestamp_result = _run_timestamp_check(submission, task)
    if timestamp_result:
        checks.append(timestamp_result)

    # --- Check 4: Evidence hash (exact duplicate detection) ---
    hash_result = _run_evidence_hash_check(evidence)
    if hash_result:
        checks.append(hash_result)

    # --- Check 5: Metadata presence ---
    metadata_result = _run_metadata_check(evidence, category)
    checks.append(metadata_result)

    # --- Check 6: Hardware attestation (optional, no-penalty) ---
    attestation_result = _run_attestation_check(evidence, task)
    if attestation_result:
        checks.append(attestation_result)

    # --- Aggregate score (Phase A only — Phase B runs async) ---
    total_weight = 0.0
    weighted_score = 0.0

    for check in checks:
        weight = PHASE_A_WEIGHTS.get(check.name, 0.10)
        weighted_score += check.score * weight
        total_weight += weight

    aggregate_score = weighted_score / total_weight if total_weight > 0 else 0.0

    # Pipeline passes if aggregate score >= 0.5 and schema check passed
    schema_passed = any(c.name == "schema" and c.passed for c in checks)
    pipeline_passed = aggregate_score >= 0.5 and schema_passed

    result = VerificationResult(
        passed=pipeline_passed,
        score=aggregate_score,
        checks=checks,
        warnings=warnings,
        phase="A",
    )

    logger.info(
        "Verification pipeline (Phase A): passed=%s, score=%.2f, checks=%d, warnings=%d",
        result.passed,
        result.score,
        len(checks),
        len(warnings),
    )

    return result


def _run_schema_check(
    evidence: Dict[str, Any],
    task: Dict[str, Any],
) -> CheckResult:
    """Validate that submitted evidence matches task requirements."""
    evidence_schema = task.get("evidence_schema") or {}
    required = evidence_schema.get("required", [])
    optional = evidence_schema.get("optional", [])

    if not required:
        # No schema defined — pass by default
        return CheckResult(
            name="schema",
            passed=True,
            score=1.0,
            reason="No evidence requirements defined for this task",
        )

    result: SchemaValidationResult = validate_evidence_schema(
        evidence=evidence,
        required=required,
        optional=optional,
        strict=False,  # Don't reject unknown fields
    )

    # Score: 1.0 if all required present, proportional otherwise
    if not required:
        score = 1.0
    else:
        present = len(required) - len(result.missing_required)
        score = present / len(required)

    return CheckResult(
        name="schema",
        passed=result.is_valid,
        score=score,
        reason=result.reason,
        details={
            "required": required,
            "missing": result.missing_required,
            "invalid": result.invalid_fields,
            "warnings": result.warnings,
        },
    )


def _run_gps_check(
    evidence: Dict[str, Any],
    task: Dict[str, Any],
    category: str,
) -> Optional[CheckResult]:
    """Verify GPS proximity for location-based tasks.

    Handles four cases:
    1. Task has coords + evidence has GPS -> proximity check
    2. Task has coords + evidence has no GPS -> fail (physical) or pass (non-physical)
    3. Task has NO coords + evidence has GPS -> partial pass (score 0.7)
    4. Task has NO coords + evidence has no GPS -> fail (physical) or skip (non-physical)
    """
    task_lat = task.get("location_lat")
    task_lng = task.get("location_lng")

    # Extract GPS from evidence
    photo_lat, photo_lng = _extract_gps_from_evidence(evidence)
    logger.info(
        "[AUDIT] _run_gps_check photo_gps=%s task_gps=%s",
        "present" if photo_lat is not None else "absent",
        "present" if task_lat is not None else "absent",
    )

    # Case: task has reference coords — do proximity check
    if task_lat is not None and task_lng is not None:
        if photo_lat is not None and photo_lng is not None:
            # Fall through to proximity logic below
            pass
        else:
            # No GPS in evidence but task has coords
            if category in PHYSICAL_CATEGORIES:
                return CheckResult(
                    name="gps",
                    passed=False,
                    score=0.0,
                    reason="No GPS coordinates found in evidence for physical task",
                )
            # Non-physical task, GPS is optional
            return CheckResult(
                name="gps",
                passed=True,
                score=0.7,
                reason="GPS not required for this task category",
            )
    else:
        # Case: task has NO reference coords
        if photo_lat is not None and photo_lng is not None:
            # Evidence has GPS even though task doesn't require specific location
            return CheckResult(
                name="gps",
                passed=True,
                score=0.7,
                reason="GPS coordinates present in evidence (no task reference location to compare)",
            )

        # No GPS anywhere
        if category in PHYSICAL_CATEGORIES:
            return CheckResult(
                name="gps",
                passed=False,
                score=0.0,
                reason="No GPS coordinates found in evidence for physical task",
            )

        return None  # non-physical, no GPS needed

    # Distance threshold: use task-specific radius if set, otherwise category defaults
    task_radius_km = task.get("location_radius_km")
    if task_radius_km is not None and task_radius_km > 0:
        max_distance = task_radius_km * 1000  # Convert km to meters
    elif category == "physical_presence":
        max_distance = 500
    elif category == "simple_action":
        max_distance = 1000  # more lenient for delivery tasks
    else:
        max_distance = 500

    result: GPSResult = check_gps_location(
        photo_lat=photo_lat,
        photo_lng=photo_lng,
        task_lat=task_lat,
        task_lng=task_lng,
        max_distance_meters=max_distance,
    )

    # Score: 1.0 if within range, proportional falloff
    if result.is_valid:
        # Closer = higher score
        distance_ratio = (result.distance_meters or 0) / max_distance
        score = max(0.5, 1.0 - distance_ratio * 0.5)
    else:
        # Out of range — partial score based on how far
        if result.distance_meters:
            overshoot = result.distance_meters / max_distance
            score = max(0.0, 0.5 - (overshoot - 1.0) * 0.25)
        else:
            score = 0.0

    return CheckResult(
        name="gps",
        passed=result.is_valid,
        score=round(score, 3),
        reason=result.reason,
        details={
            "distance_meters": result.distance_meters,
            "max_distance_meters": max_distance,
            "photo_coords": list(result.photo_coords) if result.photo_coords else None,
            "task_coords": list(result.task_coords) if result.task_coords else None,
        },
    )


def _extract_gps_from_evidence(evidence: Dict[str, Any]) -> tuple:
    """Extract GPS coordinates from evidence dict (multiple locations to check)."""

    def _found(path: str, lat: float, lng: float) -> tuple:
        logger.info("[AUDIT] _extract_gps FOUND path=%s", path)
        return lat, lng

    # Check direct GPS field
    gps = evidence.get("gps") or evidence.get("location") or evidence.get("coordinates")
    if isinstance(gps, dict):
        lat = gps.get("lat") or gps.get("latitude")
        lng = gps.get("lng") or gps.get("longitude") or gps.get("lon")
        if lat is not None and lng is not None:
            try:
                return _found("direct_gps", float(lat), float(lng))
            except (TypeError, ValueError):
                pass

    # Check photo_geo evidence for embedded coords (top-level lat/lng)
    photo_geo = evidence.get("photo_geo")
    if isinstance(photo_geo, dict):
        lat = photo_geo.get("lat") or photo_geo.get("latitude")
        lng = photo_geo.get("lng") or photo_geo.get("longitude") or photo_geo.get("lon")
        if lat is not None and lng is not None:
            try:
                return _found("photo_geo_direct", float(lat), float(lng))
            except (TypeError, ValueError):
                pass
        # Check nested metadata (direct coords or nested .gps object)
        metadata = photo_geo.get("metadata") or {}
        lat = metadata.get("lat") or metadata.get("latitude")
        lng = metadata.get("lng") or metadata.get("longitude") or metadata.get("lon")
        if lat is not None and lng is not None:
            try:
                return _found("photo_geo_metadata", float(lat), float(lng))
            except (TypeError, ValueError):
                pass
        # Frontend sends evidence[type].metadata.gps = {latitude, longitude, accuracy}
        meta_gps = metadata.get("gps")
        if isinstance(meta_gps, dict):
            lat = meta_gps.get("lat") or meta_gps.get("latitude")
            lng = (
                meta_gps.get("lng") or meta_gps.get("longitude") or meta_gps.get("lon")
            )
            if lat is not None and lng is not None:
                try:
                    return _found("photo_geo_metadata_gps", float(lat), float(lng))
                except (TypeError, ValueError):
                    pass

    # Check nested .gps or .metadata.gps inside any evidence type
    # Mobile app sends evidence.photo.gps, web dashboard sends evidence.photo.metadata.gps
    for key in ("photo", "photo_geo", "screenshot", "document", "receipt", "video"):
        item = evidence.get(key)
        if isinstance(item, dict):
            nested_gps = item.get("gps")
            if isinstance(nested_gps, dict):
                lat = nested_gps.get("lat") or nested_gps.get("latitude")
                lng = (
                    nested_gps.get("lng")
                    or nested_gps.get("longitude")
                    or nested_gps.get("lon")
                )
                if lat is not None and lng is not None:
                    try:
                        return _found(f"nested_{key}_gps", float(lat), float(lng))
                    except (TypeError, ValueError):
                        pass
            # Web dashboard: evidence[type].metadata.gps = {latitude, longitude}
            item_meta = item.get("metadata")
            if isinstance(item_meta, dict):
                meta_gps = item_meta.get("gps")
                if isinstance(meta_gps, dict):
                    lat = meta_gps.get("lat") or meta_gps.get("latitude")
                    lng = (
                        meta_gps.get("lng")
                        or meta_gps.get("longitude")
                        or meta_gps.get("lon")
                    )
                    if lat is not None and lng is not None:
                        try:
                            return _found(
                                f"nested_{key}_metadata_gps", float(lat), float(lng)
                            )
                        except (TypeError, ValueError):
                            pass

    # Check forensic metadata (from frontend collectForensicMetadata)
    forensics = evidence.get("forensic_metadata") or evidence.get("device_info") or {}
    if isinstance(forensics, dict):
        loc = forensics.get("location") or forensics.get("gps") or {}
        if isinstance(loc, dict):
            lat = loc.get("lat") or loc.get("latitude")
            lng = loc.get("lng") or loc.get("longitude") or loc.get("lon")
            if lat is not None and lng is not None:
                try:
                    return _found("forensic", float(lat), float(lng))
                except (TypeError, ValueError):
                    pass

    # Check device_metadata.gps (mobile app sends this as a separate field,
    # persisted inside evidence by the submission endpoint)
    device_meta = evidence.get("device_metadata")
    if isinstance(device_meta, dict):
        dm_gps = device_meta.get("gps")
        if isinstance(dm_gps, dict):
            lat = dm_gps.get("lat") or dm_gps.get("latitude")
            lng = dm_gps.get("lng") or dm_gps.get("longitude") or dm_gps.get("lon")
            if lat is not None and lng is not None:
                try:
                    return _found("device_metadata", float(lat), float(lng))
                except (TypeError, ValueError):
                    pass

    # Catch-all: check ALL remaining evidence keys for nested gps or metadata.gps
    checked_keys = {
        "gps",
        "location",
        "coordinates",
        "photo_geo",
        "forensic_metadata",
        "device_info",
        "device_metadata",
        "photo",
        "screenshot",
        "document",
        "receipt",
        "video",
    }
    for key, item in evidence.items():
        if key in checked_keys or not isinstance(item, dict):
            continue
        # Check item.gps
        nested_gps = item.get("gps")
        if isinstance(nested_gps, dict):
            lat = nested_gps.get("lat") or nested_gps.get("latitude")
            lng = (
                nested_gps.get("lng")
                or nested_gps.get("longitude")
                or nested_gps.get("lon")
            )
            if lat is not None and lng is not None:
                try:
                    return _found(f"catchall_{key}_gps", float(lat), float(lng))
                except (TypeError, ValueError):
                    pass
        # Check item.metadata.gps
        item_meta = item.get("metadata")
        if isinstance(item_meta, dict):
            meta_gps = item_meta.get("gps")
            if isinstance(meta_gps, dict):
                lat = meta_gps.get("lat") or meta_gps.get("latitude")
                lng = (
                    meta_gps.get("lng")
                    or meta_gps.get("longitude")
                    or meta_gps.get("lon")
                )
                if lat is not None and lng is not None:
                    try:
                        return _found(
                            f"catchall_{key}_metadata_gps", float(lat), float(lng)
                        )
                    except (TypeError, ValueError):
                        pass

    # Debug: log which paths were checked and none had GPS
    logger.info(
        "[AUDIT] _extract_gps evidence_keys=%s photo_geo_keys=%s no_gps_found=true",
        list(evidence.keys()),
        list((evidence.get("photo_geo") or {}).keys())
        if isinstance(evidence.get("photo_geo"), dict)
        else "not_dict",
    )
    return None, None


def _run_timestamp_check(
    submission: Dict[str, Any],
    task: Dict[str, Any],
) -> Optional[CheckResult]:
    """Validate submission is within the allowed time window."""
    submitted_at_raw = submission.get("submitted_at")
    # Do NOT fallback to updated_at — it gets refreshed on every status
    # change and would make the window check fail.
    assigned_at_raw = task.get("assigned_at")
    deadline_raw = task.get("deadline")

    if not submitted_at_raw or not deadline_raw:
        return None

    try:
        submitted_at = _parse_datetime(submitted_at_raw)
        deadline = _parse_datetime(deadline_raw)
        assigned_at = _parse_datetime(assigned_at_raw) if assigned_at_raw else None

        if not submitted_at or not deadline:
            return None

        # Use validate_submission_window if we have assigned_at
        if assigned_at:
            is_valid, reason = validate_submission_window(
                submission_timestamp=submitted_at,
                task_assigned_at=assigned_at,
                task_deadline=deadline,
                grace_period_minutes=5,
            )
        else:
            # Just check deadline
            is_valid = submitted_at <= deadline
            reason = (
                "Submission is within deadline"
                if is_valid
                else "Submission is past deadline"
            )

        return CheckResult(
            name="timestamp",
            passed=is_valid,
            score=1.0 if is_valid else 0.0,
            reason=reason,
            details={
                "submitted_at": submitted_at.isoformat(),
                "deadline": deadline.isoformat(),
                "assigned_at": assigned_at.isoformat() if assigned_at else None,
            },
        )

    except Exception as e:
        logger.warning("Timestamp check failed: %s", e)
        return None


def _run_evidence_hash_check(evidence: Dict[str, Any]) -> Optional[CheckResult]:
    """Check evidence integrity hash — verify if possible, not just presence."""
    # Look for hash fields that the frontend may have computed
    hash_value = (
        evidence.get("evidence_hash")
        or evidence.get("sha256")
        or evidence.get("file_hash")
        or evidence.get("integrity_hash")
    )

    if not hash_value:
        return CheckResult(
            name="evidence_hash",
            passed=True,
            score=0.5,  # Neutral — no hash to verify (older clients)
            reason="No evidence hash provided (integrity unverified)",
        )

    # Attempt server-side verification: compute hash of the evidence payload
    # and compare against the claimed hash.
    computed_hash = _compute_evidence_hash(evidence)
    if computed_hash and computed_hash == str(hash_value):
        return CheckResult(
            name="evidence_hash",
            passed=True,
            score=1.0,
            reason="Evidence hash verified — integrity confirmed",
            details={
                "hash": str(hash_value)[:16] + "...",
                "verified": True,
            },
        )
    elif computed_hash and computed_hash != str(hash_value):
        # Hash mismatch — possible tampering
        return CheckResult(
            name="evidence_hash",
            passed=False,
            score=0.0,
            reason="Evidence hash mismatch — possible tampering",
            details={
                "claimed_hash": str(hash_value)[:16] + "...",
                "computed_hash": computed_hash[:16] + "...",
                "verified": False,
            },
        )
    else:
        # Could not recompute (e.g., hash covers downloaded file bytes).
        # Hash presence is still a positive signal.
        return CheckResult(
            name="evidence_hash",
            passed=True,
            score=0.8,
            reason="Evidence hash present (file-level verification deferred to Phase B)",
            details={
                "hash": str(hash_value)[:16] + "...",
                "verified": False,
            },
        )


def _run_metadata_check(
    evidence: Dict[str, Any],
    category: str,
) -> CheckResult:
    """Check for the presence of useful metadata in evidence."""
    metadata_signals = []
    score = 0.5  # Base score

    # Check for forensic metadata from frontend
    if evidence.get("forensic_metadata") or evidence.get("device_info"):
        metadata_signals.append("device_metadata_present")
        score += 0.2

    # Check for timestamps in evidence
    for key in ("timestamp", "captured_at", "created_at"):
        if evidence.get(key):
            metadata_signals.append(f"{key}_present")
            score += 0.1
            break

    # Check for photo URLs (evidence was actually uploaded)
    photo_keys = {"photo", "photo_geo", "screenshot", "document", "receipt", "video"}
    evidence_files = [k for k in evidence if k in photo_keys and evidence[k]]
    if evidence_files:
        metadata_signals.append(f"evidence_files_present:{len(evidence_files)}")
        score += 0.1

    # Check for notes
    if evidence.get("notes") or evidence.get("description"):
        metadata_signals.append("worker_notes_present")
        score += 0.05

    score = min(1.0, score)

    return CheckResult(
        name="metadata",
        passed=True,
        score=round(score, 3),
        reason=f"{len(metadata_signals)} metadata signals found",
        details={"signals": metadata_signals},
    )


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Parse a datetime from various formats."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            pass

    return None


def _compute_evidence_hash(evidence: Dict[str, Any]) -> Optional[str]:
    """
    Compute a SHA-256 hash of the evidence payload for verification.

    The frontend hashes the JSON-serialized evidence (sorted keys, no whitespace).
    We replicate that here. If the hash covers file bytes (not JSON), we cannot
    recompute server-side without downloading — return None.
    """
    try:
        # Exclude hash fields themselves from the payload to hash
        hashable = {
            k: v
            for k, v in evidence.items()
            if k not in ("evidence_hash", "sha256", "file_hash", "integrity_hash")
        }
        # Canonical JSON: sorted keys, no whitespace, ensure_ascii for determinism
        canonical = json.dumps(
            hashable, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    except (TypeError, ValueError) as e:
        logger.debug("Could not compute evidence hash: %s", e)
        return None


async def _run_gps_antispoofing_check(
    evidence: Dict[str, Any],
    submission: Dict[str, Any],
    task: Dict[str, Any],
) -> Optional[CheckResult]:
    """
    Run GPS anti-spoofing analysis after basic GPS check passed.

    Uses movement patterns, sensor fusion, and device fingerprinting
    to detect GPS spoofing.
    """
    try:
        # Extract GPS coordinates from evidence
        photo_lat, photo_lng = _extract_gps_from_evidence(evidence)
        if photo_lat is None or photo_lng is None:
            return None  # No GPS to anti-spoof

        executor_id = submission.get("executor_id") or "unknown"

        # Build GPSData
        gps_data = GPSData(
            latitude=photo_lat,
            longitude=photo_lng,
        )

        # Extract device info if available
        forensics = (
            evidence.get("forensic_metadata") or evidence.get("device_info") or {}
        )
        device_info = DeviceInfo(
            device_id=forensics.get("device_id"),
            user_agent=forensics.get("user_agent"),
            screen_width=forensics.get("screen_width"),
            screen_height=forensics.get("screen_height"),
            platform=forensics.get("platform"),
            timezone=forensics.get("timezone"),
            language=forensics.get("language"),
        )

        # Extract sensor data if available
        sensor_data = None
        accel = forensics.get("accelerometer")
        gyro = forensics.get("gyroscope")
        if accel or gyro:
            sensor_data = SensorData(
                accelerometer=tuple(accel) if accel and len(accel) == 3 else None,
                gyroscope=tuple(gyro) if gyro and len(gyro) == 3 else None,
            )

        # Extract IP if available (from submission metadata)
        ip_address = submission.get("ip_address") or submission.get("client_ip")

        detector = GPSAntiSpoofing()
        result = await detector.detect_spoofing(
            gps_data=gps_data,
            device_info=device_info,
            executor_id=executor_id,
            ip_address=ip_address,
            sensor_data=sensor_data,
        )

        # Convert SpoofingResult to CheckResult
        # risk_score 0.0 (safe) -> score 1.0 (good)
        # risk_score 1.0 (spoofed) -> score 0.0 (bad)
        score = max(0.0, 1.0 - result.risk_score)

        return CheckResult(
            name="gps_antispoofing",
            passed=not result.is_spoofed,
            score=round(score, 3),
            reason=(
                "; ".join(result.reasons)
                if result.reasons
                else "GPS anti-spoofing: no anomalies detected"
            ),
            details={
                "risk_level": result.risk_level.value,
                "risk_score": result.risk_score,
                "confidence": result.confidence,
                "checks_performed": result.checks_performed,
            },
        )

    except Exception as e:
        logger.warning("GPS anti-spoofing check failed: %s", e)
        # Failure of anti-spoofing should not block pipeline
        return CheckResult(
            name="gps_antispoofing",
            passed=True,
            score=0.5,
            reason=f"GPS anti-spoofing check error (non-blocking): {e}",
        )


def _run_attestation_check(
    evidence: Dict[str, Any],
    task: Dict[str, Any],
) -> Optional[CheckResult]:
    """
    Check for hardware attestation data in evidence.

    This is an optional bonus check. When attestation data is present
    and valid, it boosts the score. When absent, it does NOT penalize
    — returns a neutral score. This avoids punishing older clients or
    devices without hardware security modules.
    """
    # Look for attestation data in evidence
    attestation_data = (
        evidence.get("attestation")
        or evidence.get("device_attestation")
        or evidence.get("hardware_attestation")
    )

    # Check if attestation is required for this task
    category = task.get("category", "")
    bounty = task.get("bounty", 0)
    try:
        bounty_usd = float(bounty)
    except (TypeError, ValueError):
        bounty_usd = 0.0

    requirement = get_attestation_requirement(category, bounty_usd)

    if not attestation_data:
        if requirement.required:
            # High-value task without attestation — partial penalty
            return CheckResult(
                name="attestation",
                passed=False,
                score=0.3,
                reason=f"Hardware attestation required for {category} tasks with bounty ${bounty_usd:.2f} but not provided",
                details={
                    "required": True,
                    "provided": False,
                    "min_level": requirement.min_level.value,
                },
            )
        elif requirement.recommended:
            # Recommended but not provided — neutral
            return CheckResult(
                name="attestation",
                passed=True,
                score=0.6,
                reason="Hardware attestation recommended but not provided",
                details={"required": False, "recommended": True, "provided": False},
            )
        else:
            # Not required, not provided — fully neutral, skip weight
            return None

    # Attestation data is present — validate its structure
    if isinstance(attestation_data, dict):
        platform = attestation_data.get("platform", "unknown")
        level = attestation_data.get("level", "basic")

        try:
            att_level = AttestationLevel(level)
        except ValueError:
            att_level = AttestationLevel.BASIC

        # Score based on attestation level
        level_scores = {
            AttestationLevel.NONE: 0.3,
            AttestationLevel.BASIC: 0.6,
            AttestationLevel.STRONG: 0.85,
            AttestationLevel.VERIFIED: 1.0,
        }
        score = level_scores.get(att_level, 0.5)

        return CheckResult(
            name="attestation",
            passed=True,
            score=score,
            reason=f"Hardware attestation present ({platform}, level: {level})",
            details={
                "platform": platform,
                "level": level,
                "required": requirement.required,
            },
        )

    # Attestation present but unrecognized format
    return CheckResult(
        name="attestation",
        passed=True,
        score=0.5,
        reason="Hardware attestation data present but format unrecognized",
        details={"provided": True, "format": type(attestation_data).__name__},
    )


def recompute_aggregate(
    phase_a_checks: List[CheckResult],
    phase_b_checks: List[CheckResult],
) -> tuple:
    """
    Recompute the aggregate score using ALL_WEIGHTS across both phases.

    Returns:
        (aggregate_score, pipeline_passed)
    """
    all_checks = phase_a_checks + phase_b_checks
    total_weight = 0.0
    weighted_score = 0.0

    for check in all_checks:
        weight = ALL_WEIGHTS.get(check.name, 0.05)
        weighted_score += check.score * weight
        total_weight += weight

    aggregate_score = weighted_score / total_weight if total_weight > 0 else 0.0

    schema_passed = any(c.name == "schema" and c.passed for c in all_checks)
    pipeline_passed = aggregate_score >= 0.5 and schema_passed

    return aggregate_score, pipeline_passed


def merge_phase_b(
    existing_dict: Dict[str, Any],
    phase_b_checks: List[CheckResult],
) -> Dict[str, Any]:
    """
    Merge Phase B check results into existing auto_check_details dict.

    Recomputes the aggregate score using all checks from both phases.

    Returns:
        Updated auto_check_details dict with phase="AB".
    """
    # Reconstruct Phase A CheckResults from existing dict
    phase_a_checks = []
    for c in existing_dict.get("checks", []):
        phase_a_checks.append(
            CheckResult(
                name=c["name"],
                passed=c["passed"],
                score=c["score"],
                reason=c.get("reason"),
                details=c.get("details", {}),
            )
        )

    # Recompute aggregate
    aggregate_score, pipeline_passed = recompute_aggregate(
        phase_a_checks, phase_b_checks
    )

    # Build merged dict
    all_checks = phase_a_checks + phase_b_checks
    warnings = list(existing_dict.get("warnings", []))

    return {
        "passed": pipeline_passed,
        "score": round(aggregate_score, 3),
        "checks": [asdict(c) for c in all_checks],
        "warnings": warnings,
        "phase": "AB",
    }
