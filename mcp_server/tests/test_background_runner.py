"""
Phase B background runner tests — Magika integration (Tarea 2.5)

Tests _validate_images_with_magika() and helper functions.
Marked with @pytest.mark.magika for selective runs.

pytest -m magika
"""

from __future__ import annotations

import os
import tempfile
from typing import List, Tuple
from unittest.mock import AsyncMock, patch

import pytest

from verification.background_runner import (
    _build_magika_detections_payload,
    _get_claimed_mime,
    _validate_images_with_magika,
)
from verification.magika_validator import MagikaResult, MagikaValidator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_magika_singleton():
    MagikaValidator.reset_instance()
    yield
    MagikaValidator.reset_instance()


def _make_temp_jpg(content: bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100) -> str:
    """Write bytes to a temp .jpg file and return its path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg", prefix="em_test_")
    tmp.write(content)
    tmp.close()
    return tmp.name


def _make_magika_result(
    fraud_score: float = 0.0,
    is_mismatch: bool = False,
    is_safe: bool = True,
    detected: str = "image/jpeg",
    claimed: str = "image/jpeg",
) -> MagikaResult:
    return MagikaResult(
        detected_mime=detected,
        claimed_mime=claimed,
        confidence=0.99,
        is_mismatch=is_mismatch,
        is_safe=is_safe,
        fraud_score=fraud_score,
    )


# PlatformConfig is a lazy import inside _validate_images_with_magika.
# Patch its .get classmethod at the source module path.
_CFG_PATCH = "config.platform_config.PlatformConfig.get"
_ENABLED_CFG = AsyncMock(return_value={"enabled": True, "hard_block": False})


# ---------------------------------------------------------------------------
# Test 1 — Clean JPEG passes Magika
# ---------------------------------------------------------------------------


@pytest.mark.magika
@pytest.mark.asyncio
async def test_clean_jpeg_passes_magika():
    """Clean JPEG -> validated_images has 1 entry, magika_context is clean."""
    path = _make_temp_jpg()
    url = "https://cdn.example.com/photo.jpg"
    downloaded = [(path, url)]
    clean_result = _make_magika_result(fraud_score=0.0)

    try:
        with patch(_CFG_PATCH, new=AsyncMock(return_value={"enabled": True})):
            with patch(
                "verification.magika_validator.MagikaValidator.validate_bytes",
                return_value=clean_result,
            ):
                (
                    validated,
                    magika_context,
                    rejected,
                    payload,
                ) = await _validate_images_with_magika(downloaded)

        assert len(validated) == 1
        assert len(rejected) == 0
        assert url in magika_context
        assert magika_context[url].fraud_score == pytest.approx(0.0)
        assert payload["has_critical_mismatch"] is False
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Test 2 — PDF disguised as JPEG is blocked
# ---------------------------------------------------------------------------


@pytest.mark.magika
@pytest.mark.asyncio
async def test_pdf_as_jpeg_blocked_by_magika():
    """PDF bytes renamed .jpg -> validated empty, rejected has 1 entry."""
    path = _make_temp_jpg(b"%PDF-1.4\n" + b"\x00" * 100)
    url = "https://cdn.example.com/photo.jpg"
    downloaded = [(path, url)]
    block_result = _make_magika_result(
        fraud_score=0.8,
        is_mismatch=True,
        is_safe=True,
        detected="application/pdf",
        claimed="image/jpeg",
    )

    try:
        with patch(_CFG_PATCH, new=AsyncMock(return_value={"enabled": True})):
            with patch(
                "verification.magika_validator.MagikaValidator.validate_bytes",
                return_value=block_result,
            ):
                (
                    validated,
                    magika_context,
                    rejected,
                    payload,
                ) = await _validate_images_with_magika(downloaded)

        assert len(validated) == 0
        assert len(rejected) == 1
        assert rejected[0]["fraud_score"] == pytest.approx(0.8)
        assert rejected[0]["reason"] == "application/pdf"
        assert payload["has_critical_mismatch"] is True
        assert payload["max_fraud_score"] == pytest.approx(0.8)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Test 3 — Magika exception fails open (circuit breaker)
# ---------------------------------------------------------------------------


@pytest.mark.magika
@pytest.mark.asyncio
async def test_magika_exception_fails_open():
    """validate_bytes() raises exception -> image passes (circuit breaker)."""
    path = _make_temp_jpg()
    url = "https://cdn.example.com/photo.jpg"
    downloaded = [(path, url)]

    try:
        with patch(_CFG_PATCH, new=AsyncMock(return_value={"enabled": True})):
            with patch(
                "verification.magika_validator.MagikaValidator.validate_bytes",
                side_effect=RuntimeError("ONNX model crashed"),
            ):
                (
                    validated,
                    magika_context,
                    rejected,
                    payload,
                ) = await _validate_images_with_magika(downloaded)

        # Circuit breaker: image must pass through despite exception
        assert len(validated) == 1
        assert len(rejected) == 0
        assert magika_context == {}  # exception prevented assignment
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Test 4 — Text evidence has no binary files -> skipped gracefully
# ---------------------------------------------------------------------------


@pytest.mark.magika
@pytest.mark.asyncio
async def test_text_evidence_skips_magika():
    """Empty downloaded list -> all outputs empty, payload says files_analyzed=0."""
    downloaded: List[Tuple[str, str]] = []

    with patch(_CFG_PATCH, new=AsyncMock(return_value={"enabled": True})):
        (
            validated,
            magika_context,
            rejected,
            payload,
        ) = await _validate_images_with_magika(downloaded)

    assert validated == []
    assert magika_context == {}
    assert rejected == []
    assert payload.get("files_analyzed") == 0
    assert payload.get("analyzed") is True


# ---------------------------------------------------------------------------
# Unit tests for helpers (no async, no patches needed)
# ---------------------------------------------------------------------------


def test_get_claimed_mime_jpg():
    assert _get_claimed_mime("/tmp/em_verify_abc123.jpg") == "image/jpeg"


def test_get_claimed_mime_png():
    assert _get_claimed_mime("/tmp/em_verify_abc123.png") == "image/png"


def test_get_claimed_mime_unknown_falls_back():
    assert _get_claimed_mime("/tmp/em_verify_noext") == "application/octet-stream"


def test_build_magika_detections_payload_empty():
    payload = _build_magika_detections_payload({}, [])
    assert payload["analyzed"] is True
    assert payload["files_analyzed"] == 0
    assert payload["max_fraud_score"] == pytest.approx(0.0)


def test_build_magika_detections_payload_with_results():
    ctx = {
        "https://cdn.example.com/a.jpg": _make_magika_result(fraud_score=0.0),
        "https://cdn.example.com/b.jpg": _make_magika_result(
            fraud_score=0.8,
            is_mismatch=True,
            detected="application/pdf",
        ),
    }
    rejected = [
        {
            "url": "https://cdn.example.com/b.jpg",
            "reason": "application/pdf",
            "fraud_score": 0.8,
        }
    ]
    payload = _build_magika_detections_payload(ctx, rejected)

    assert payload["max_fraud_score"] == pytest.approx(0.8)
    assert payload["has_critical_mismatch"] is True
    assert payload["files_analyzed"] == 2
    assert payload["files_rejected"] == 1
    assert "details" in payload
