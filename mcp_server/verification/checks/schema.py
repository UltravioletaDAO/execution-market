"""
Evidence Schema Validation

Validates that submitted evidence matches task requirements.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum


class EvidenceType(str, Enum):
    """Supported evidence types."""

    PHOTO = "photo"
    GPS = "gps"
    TIMESTAMP = "timestamp"
    VIDEO = "video"
    DOCUMENT = "document"
    TEXT = "text"
    SIGNATURE = "signature"
    RECEIPT = "receipt"
    QR_CODE = "qr_code"
    BARCODE = "barcode"
    AUDIO = "audio"


@dataclass
class SchemaValidationResult:
    """Result of schema validation."""

    is_valid: bool
    missing_required: List[str]
    invalid_fields: List[Dict[str, str]]
    warnings: List[str]
    reason: Optional[str]

    @property
    def normalized_score(self) -> float:
        """Normalized score 0.0-1.0 where 1.0 = schema fully valid (passed).

        Proportional to how many required fields are present and valid.
        Warnings reduce score slightly but don't cause failure.
        """
        if self.is_valid and not self.warnings:
            return 1.0
        if self.is_valid and self.warnings:
            # Valid but with warnings -- slight deduction
            return max(0.8, 1.0 - 0.05 * len(self.warnings))
        # Invalid -- proportional to severity
        issues = len(self.missing_required) + len(self.invalid_fields)
        if issues == 0:
            return 0.5  # Shouldn't happen but defensive
        # Each missing/invalid field reduces score
        return round(max(0.0, 1.0 - 0.25 * issues), 4)


def validate_evidence_schema(
    evidence: Dict[str, Any],
    required: List[str],
    optional: List[str] = None,
    strict: bool = True,
) -> SchemaValidationResult:
    """
    Validate evidence against schema requirements.

    Args:
        evidence: Submitted evidence dict
        required: List of required evidence types
        optional: List of optional evidence types
        strict: If True, reject unknown fields

    Returns:
        SchemaValidationResult with validation details
    """
    optional = optional or []
    missing = []
    invalid = []
    warnings = []

    # Check required fields
    for req in required:
        if req not in evidence:
            missing.append(req)
        elif not validate_field(req, evidence[req]):
            invalid.append({"field": req, "error": f"Invalid format for {req}"})

    # Check for unknown fields in strict mode
    if strict:
        known_fields = set(required + optional)
        for field in evidence:
            if field not in known_fields:
                warnings.append(f"Unknown field '{field}' will be ignored")

    # Build result
    is_valid = len(missing) == 0 and len(invalid) == 0

    reason = None
    if missing:
        reason = f"Missing required evidence: {', '.join(missing)}"
    elif invalid:
        reason = f"Invalid evidence: {invalid[0]['field']} - {invalid[0]['error']}"

    return SchemaValidationResult(
        is_valid=is_valid,
        missing_required=missing,
        invalid_fields=invalid,
        warnings=warnings,
        reason=reason,
    )


def validate_field(field_type: str, value: Any) -> bool:
    """
    Validate a single evidence field.

    Args:
        field_type: Type of evidence field
        value: Field value

    Returns:
        True if valid
    """
    validators = {
        EvidenceType.PHOTO: validate_photo,
        EvidenceType.GPS: validate_gps,
        EvidenceType.TIMESTAMP: validate_timestamp,
        EvidenceType.VIDEO: validate_video,
        EvidenceType.DOCUMENT: validate_document,
        EvidenceType.TEXT: validate_text,
        EvidenceType.SIGNATURE: validate_signature,
        EvidenceType.RECEIPT: validate_receipt,
        EvidenceType.QR_CODE: validate_qr_code,
        EvidenceType.BARCODE: validate_barcode,
        EvidenceType.AUDIO: validate_audio,
    }

    # Convert string to enum if needed
    try:
        field_enum = EvidenceType(field_type)
    except ValueError:
        # Unknown type, accept any non-empty value
        return bool(value)

    validator = validators.get(field_enum, lambda x: bool(x))
    return validator(value)


def validate_photo(value: Any) -> bool:
    """Validate photo evidence."""
    if isinstance(value, str):
        # URL or IPFS hash
        return value.startswith(("http", "ipfs://", "data:image"))
    if isinstance(value, dict):
        # Object with URL and metadata
        return "url" in value or "file" in value or "ipfs" in value
    return False


def validate_gps(value: Any) -> bool:
    """Validate GPS evidence."""
    if isinstance(value, dict):
        lat = value.get("lat") or value.get("latitude")
        lng = value.get("lng") or value.get("longitude") or value.get("lon")
        if lat is not None and lng is not None:
            try:
                lat = float(lat)
                lng = float(lng)
                return -90 <= lat <= 90 and -180 <= lng <= 180
            except (TypeError, ValueError):
                pass
    return False


def validate_timestamp(value: Any) -> bool:
    """Validate timestamp evidence."""
    if isinstance(value, str):
        # ISO format or Unix timestamp
        try:
            from datetime import datetime

            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return True
        except Exception:
            pass
        try:
            int(value)
            return True
        except Exception:
            pass
    if isinstance(value, (int, float)):
        # Unix timestamp
        return value > 0
    return False


def validate_video(value: Any) -> bool:
    """Validate video evidence."""
    if isinstance(value, str):
        return value.startswith(("http", "ipfs://"))
    if isinstance(value, dict):
        return "url" in value or "file" in value
    return False


def validate_document(value: Any) -> bool:
    """Validate document evidence."""
    if isinstance(value, str):
        return value.startswith(("http", "ipfs://"))
    if isinstance(value, dict):
        return "url" in value or "file" in value
    return False


def validate_text(value: Any) -> bool:
    """Validate text evidence."""
    return isinstance(value, str) and len(value) > 0


def validate_signature(value: Any) -> bool:
    """Validate signature evidence."""
    if isinstance(value, str):
        # Image or base64
        return len(value) > 0
    if isinstance(value, dict):
        return "image" in value or "data" in value
    return False


def validate_receipt(value: Any) -> bool:
    """Validate receipt evidence."""
    # Same as photo
    return validate_photo(value)


def validate_qr_code(value: Any) -> bool:
    """Validate QR code evidence."""
    if isinstance(value, str):
        return len(value) > 0  # QR code content
    if isinstance(value, dict):
        return "content" in value or "image" in value
    return False


def validate_barcode(value: Any) -> bool:
    """Validate barcode evidence."""
    if isinstance(value, str):
        return len(value) > 0  # Barcode number/content
    if isinstance(value, dict):
        return "code" in value or "image" in value
    return False


def validate_audio(value: Any) -> bool:
    """Validate audio evidence."""
    if isinstance(value, str):
        return value.startswith(("http", "ipfs://", "data:audio"))
    if isinstance(value, dict):
        return "url" in value or "file" in value
    return False
