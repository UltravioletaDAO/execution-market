"""
Magika-based file type validator for evidence verification.

Detects real file content type from bytes (not from extension or HTTP headers).
Runs in Phase B (background_runner.py) after download_images_to_temp(),
before the 5 parallel verification checks.

Architecture notes:
- Singleton pattern: Magika model loaded once at startup (~150-300 MB ONNX)
- Thread-safe: Magika is stateless after init; validate_bytes() is re-entrant
- Circuit breaker: all exceptions fail-open (don't block verification)
- Not in image_downloader.py (SRP: I/O is not validation)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# MIME types accepted as evidence. application/json excluded (VECTOR-012: injection risk).
ALLOWED_EVIDENCE_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/heic",
        "image/heif",
        "image/gif",
        "image/bmp",
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "application/pdf",
        "text/plain",
        "audio/mpeg",
        "audio/wav",
        "audio/ogg",
    }
)

# Benign mismatches: different container/subtype, same media family.
# Example: WebP uploaded as image/jpeg — still safe to process, warn only.
BENIGN_MISMATCHES: frozenset[tuple[str, str]] = frozenset(
    {
        ("image/webp", "image/jpeg"),
        ("image/webp", "image/png"),
        ("image/png", "image/jpeg"),
        ("image/jpeg", "image/png"),
        ("image/heic", "image/jpeg"),
        ("image/heif", "image/jpeg"),
        ("image/heic", "image/png"),
        ("image/heif", "image/png"),
        ("video/quicktime", "video/mp4"),
    }
)


@dataclass
class MagikaResult:
    """Result of Magika content-type detection for a single file."""

    detected_mime: str  # MIME type detected from bytes
    claimed_mime: str  # MIME type claimed by client
    confidence: float  # Magika confidence score (0.0-1.0)
    is_mismatch: bool  # detected != claimed (normalized comparison)
    is_safe: bool  # detected type in ALLOWED_EVIDENCE_MIME_TYPES
    fraud_score: float  # 0.0=clean, 0.3=benign mismatch, 0.5=uncertain, 0.8=dangerous, 1.0=executable/script
    details: dict = field(default_factory=dict)  # Raw Magika output


class MagikaValidator:
    """
    Singleton wrapper around Google's Magika library.

    Usage:
        validator = MagikaValidator.get_instance()
        result = await asyncio.to_thread(
            validator.validate_bytes, file_bytes, "image/jpeg", "photo.jpg"
        )
    """

    _instance: Optional["MagikaValidator"] = None

    def __init__(self) -> None:
        try:
            from magika import Magika  # type: ignore[import]

            self._magika = Magika()
            logger.info("[MAGIKA] Model loaded successfully")
        except ImportError:
            logger.error(
                "[MAGIKA] magika package not installed — install magika>=0.5.1"
            )
            self._magika = None
        except Exception as exc:
            logger.error("[MAGIKA] Failed to initialize model: %s", exc)
            self._magika = None

    @classmethod
    def get_instance(cls) -> "MagikaValidator":
        """Singleton — Magika model loaded once per process."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton — for tests only."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_bytes(
        self, data: bytes, claimed_mime: str, filename: str = "unknown"
    ) -> MagikaResult:
        """
        Detect real content type from raw bytes.

        Args:
            data: Raw file bytes.
            claimed_mime: MIME type the client declared (from extension or header).
            filename: Original filename, used only for logging context.

        Returns:
            MagikaResult with fraud_score and is_safe flags.
        """
        if not data:
            logger.warning("[MAGIKA] Empty bytes for %s", filename)
            return MagikaResult(
                detected_mime="application/octet-stream",
                claimed_mime=claimed_mime,
                confidence=0.0,
                is_mismatch=True,
                is_safe=False,
                fraud_score=1.0,
                details={"error": "empty_bytes"},
            )

        if self._magika is None:
            # Magika unavailable — fail open, log warning
            logger.warning("[MAGIKA] Not available, failing open for %s", filename)
            return MagikaResult(
                detected_mime=claimed_mime,
                claimed_mime=claimed_mime,
                confidence=0.0,
                is_mismatch=False,
                is_safe=claimed_mime in ALLOWED_EVIDENCE_MIME_TYPES,
                fraud_score=0.0,
                details={"error": "magika_unavailable"},
            )

        try:
            res = self._magika.identify_bytes(data)
            detected = res.output.mime_type or "application/octet-stream"
            # score lives on the top-level MagikaResult, not on output (API change in 0.5.x)
            confidence = float(res.score) if hasattr(res, "score") else 1.0

            return self._build_result(detected, claimed_mime, confidence, filename, res)

        except Exception as exc:
            logger.error("[MAGIKA] Exception on %s: %s — failing open", filename, exc)
            return MagikaResult(
                detected_mime=claimed_mime,
                claimed_mime=claimed_mime,
                confidence=0.0,
                is_mismatch=False,
                is_safe=claimed_mime in ALLOWED_EVIDENCE_MIME_TYPES,
                fraud_score=0.0,
                details={"error": str(exc)},
            )

    def validate_file(self, path: str, claimed_mime: str) -> MagikaResult:
        """
        Detect real content type from a file path.

        Reads the file and delegates to validate_bytes().
        """
        try:
            with open(path, "rb") as f:
                data = f.read()
            filename = os.path.basename(path)
            return self.validate_bytes(data, claimed_mime, filename)
        except OSError as exc:
            logger.error("[MAGIKA] Cannot read file %s: %s", path, exc)
            return MagikaResult(
                detected_mime="application/octet-stream",
                claimed_mime=claimed_mime,
                confidence=0.0,
                is_mismatch=True,
                is_safe=False,
                fraud_score=1.0,
                details={"error": f"file_read_error: {exc}"},
            )

    def is_safe_for_evidence(self, result: MagikaResult) -> bool:
        """True if the detected MIME type is in the allowed evidence whitelist."""
        return result.is_safe

    def get_fraud_score(self, result: MagikaResult) -> float:
        """Return the pre-computed fraud score from a result."""
        return result.fraud_score

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_result(
        self,
        detected: str,
        claimed: str,
        confidence: float,
        filename: str,
        raw,
    ) -> MagikaResult:
        """Compute is_mismatch, is_safe, and fraud_score from Magika output."""
        normalized_detected = _normalize_mime(detected)
        normalized_claimed = _normalize_mime(claimed)
        is_mismatch = normalized_detected != normalized_claimed
        is_safe = normalized_detected in ALLOWED_EVIDENCE_MIME_TYPES

        fraud_score = _compute_fraud_score(
            detected=normalized_detected,
            claimed=normalized_claimed,
            confidence=confidence,
            is_mismatch=is_mismatch,
            is_safe=is_safe,
        )

        details: dict = {}
        try:
            details = {
                # .label is the current API; .ct_label is deprecated in 0.5.x
                "label": getattr(raw.output, "label", None)
                or getattr(raw.output, "ct_label", None),
                "group": getattr(raw.output, "group", None),
                "is_text": getattr(raw.output, "is_text", None),
            }
        except Exception:
            pass

        if fraud_score >= 0.8:
            logger.warning(
                "[MAGIKA] High fraud score %.2f for %s: detected=%s claimed=%s confidence=%.2f",
                fraud_score,
                filename,
                detected,
                claimed,
                confidence,
            )

        return MagikaResult(
            detected_mime=detected,
            claimed_mime=claimed,
            confidence=confidence,
            is_mismatch=is_mismatch,
            is_safe=is_safe,
            fraud_score=fraud_score,
            details=details,
        )


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------


def _normalize_mime(mime: str) -> str:
    """Normalize MIME type for comparison (lowercase, strip params)."""
    return mime.lower().split(";")[0].strip()


def _compute_fraud_score(
    detected: str,
    claimed: str,
    confidence: float,
    is_mismatch: bool,
    is_safe: bool,
) -> float:
    """
    Compute fraud score (0.0-1.0).

    Score table:
        0.0  — whitelist type, matches claimed, high confidence
        0.3  — benign mismatch (same media family, different subtype)
        0.5  — whitelist type but low confidence (possible polyglot)
        0.8  — mismatch with potentially dangerous type (PDF as JPEG)
        1.0  — type outside whitelist (executable, script, archive)
    """
    # Immediately flag non-whitelist types (executables, scripts, archives, etc.)
    if not is_safe:
        return 1.0

    if not is_mismatch:
        # Clean match — low confidence is a mild concern (potential polyglot)
        if confidence < 0.85:
            return 0.5
        return 0.0

    # Mismatch: check if it's benign (same media family)
    if (detected, claimed) in BENIGN_MISMATCHES or (
        claimed,
        detected,
    ) in BENIGN_MISMATCHES:
        return 0.3

    # Mismatch with type that is in whitelist but differs from claimed family
    # (e.g., application/pdf submitted as image/jpeg)
    return 0.8
