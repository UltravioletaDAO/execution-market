"""
Tests for MagikaValidator (Tarea 1.4 — MASTER_PLAN_MAGIKA_INTEGRATION.md)

7 unit tests covering the core validation contracts:
  1. Real JPEG bytes detected correctly (fraud_score 0.0)
  2. PDF disguised as JPEG -> hard block (fraud_score 0.8)
  3. Script disguised as PNG -> executable block (fraud_score 1.0)
  4. WebP claimed as JPEG -> benign mismatch (fraud_score 0.3)
  5. Low confidence -> polyglot signal (fraud_score 0.5)
  6. Empty bytes -> graceful handling (fraud_score 1.0, no exception)
  7. Singleton identity (get_instance() returns same object)
"""

from __future__ import annotations

import struct
import pytest
from unittest.mock import MagicMock, patch

from verification.magika_validator import (
    MagikaValidator,
    _compute_fraud_score,
    _normalize_mime,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure a clean MagikaValidator singleton for each test."""
    MagikaValidator.reset_instance()
    yield
    MagikaValidator.reset_instance()


def _make_magika_output(mime_type: str, score: float = 0.99, ct_label: str = "jpeg"):
    """Build a minimal Magika result mock matching the real Magika 0.5.x API shape.

    In Magika 0.5.x:
      - res.score          -> top-level confidence (float)
      - res.output.mime_type -> detected MIME type
      - res.output.label   -> content type label (ct_label deprecated)
    """
    output = MagicMock()
    output.mime_type = mime_type
    output.label = ct_label
    output.ct_label = ct_label  # kept for compat, but deprecated
    output.group = mime_type.split("/")[0]
    output.is_text = mime_type.startswith("text/")
    # score is NOT on output in 0.5.x — it's on the top-level result
    output.score = score  # kept on mock only for safety; real code uses res.score
    result = MagicMock()
    result.output = output
    result.score = score  # top-level score (0.5.x API)
    return result


def _make_validator_with_mock(mime_type: str, score: float = 0.99) -> MagikaValidator:
    """Create a MagikaValidator whose _magika.identify_bytes() is mocked."""
    v = MagikaValidator.__new__(MagikaValidator)
    mock_magika = MagicMock()
    mock_magika.identify_bytes.return_value = _make_magika_output(mime_type, score)
    v._magika = mock_magika
    return v


# ---------------------------------------------------------------------------
# Test 1 — Real JPEG bytes detected as JPEG -> fraud_score 0.0
# ---------------------------------------------------------------------------


def test_jpeg_bytes_detected_as_jpeg():
    validator = _make_validator_with_mock("image/jpeg", score=0.99)
    jpeg_magic = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    result = validator.validate_bytes(jpeg_magic, "image/jpeg", "photo.jpg")

    assert result.detected_mime == "image/jpeg"
    assert result.claimed_mime == "image/jpeg"
    assert result.confidence == pytest.approx(0.99)
    assert result.is_mismatch is False
    assert result.is_safe is True
    assert result.fraud_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test 2 — PDF disguised as JPEG -> dangerous mismatch (fraud_score 0.8)
# ---------------------------------------------------------------------------


def test_pdf_disguised_as_jpeg():
    validator = _make_validator_with_mock("application/pdf", score=0.98)
    pdf_magic = b"%PDF-1.4\n" + b"\x00" * 100
    result = validator.validate_bytes(pdf_magic, "image/jpeg", "screenshot.jpg")

    assert result.detected_mime == "application/pdf"
    assert result.claimed_mime == "image/jpeg"
    assert result.is_mismatch is True
    assert result.is_safe is True  # PDF is in whitelist
    assert result.fraud_score == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# Test 3 — Script disguised as PNG -> non-whitelist type (fraud_score 1.0)
# ---------------------------------------------------------------------------


def test_script_disguised_as_png():
    validator = _make_validator_with_mock("text/x-python", score=0.97)
    # Arbitrary script-like bytes — no dangerous literal payload
    py_bytes = b"#!" + b"python3" + b"\n" + b"x = 1\n"
    result = validator.validate_bytes(py_bytes, "image/png", "photo.png")

    assert result.detected_mime == "text/x-python"
    assert result.is_mismatch is True
    assert result.is_safe is False  # text/x-python NOT in whitelist
    assert result.fraud_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Test 4 — WebP as JPEG -> benign mismatch (fraud_score 0.3)
# ---------------------------------------------------------------------------


def test_webp_as_jpeg_benign_mismatch():
    validator = _make_validator_with_mock("image/webp", score=0.99)
    webp_magic = b"RIFF" + struct.pack("<I", 100) + b"WEBP" + b"\x00" * 90
    result = validator.validate_bytes(webp_magic, "image/jpeg", "photo.jpg")

    assert result.detected_mime == "image/webp"
    assert result.claimed_mime == "image/jpeg"
    assert result.is_mismatch is True
    assert result.is_safe is True
    assert result.fraud_score == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Test 5 — Low confidence (0.60) -> polyglot signal (fraud_score 0.5)
# ---------------------------------------------------------------------------


def test_low_confidence_polyglot_signal():
    validator = _make_validator_with_mock("image/jpeg", score=0.60)
    jpeg_magic = b"\xff\xd8\xff" + b"\x00" * 100
    result = validator.validate_bytes(jpeg_magic, "image/jpeg", "ambiguous.jpg")

    assert result.detected_mime == "image/jpeg"
    assert result.is_mismatch is False
    assert result.is_safe is True
    assert result.confidence == pytest.approx(0.60)
    assert result.fraud_score == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Test 6 — Empty bytes -> graceful, no exception, fraud_score 1.0
# ---------------------------------------------------------------------------


def test_empty_bytes_graceful():
    validator = _make_validator_with_mock("image/jpeg")  # should not be called
    result = validator.validate_bytes(b"", "image/jpeg", "empty.jpg")

    assert result.detected_mime == "application/octet-stream"
    assert result.is_safe is False
    assert result.fraud_score == pytest.approx(1.0)
    assert "empty_bytes" in result.details.get("error", "")


# ---------------------------------------------------------------------------
# Test 7 — Singleton identity
# ---------------------------------------------------------------------------


def test_singleton_same_instance():
    with patch(
        "verification.magika_validator.MagikaValidator.__init__", return_value=None
    ):
        # Patch __init__ so no real Magika model is loaded during this test
        inst1 = MagikaValidator.get_instance()
        inst2 = MagikaValidator.get_instance()

    assert inst1 is inst2


# ---------------------------------------------------------------------------
# Edge case — Magika unavailable (ImportError) -> fail open
# ---------------------------------------------------------------------------


def test_magika_unavailable_fails_open():
    v = MagikaValidator.__new__(MagikaValidator)
    v._magika = None  # simulate unavailable Magika
    result = v.validate_bytes(b"\xff\xd8\xff", "image/jpeg", "photo.jpg")

    # Fail open: treat as clean
    assert result.fraud_score == pytest.approx(0.0)
    assert result.is_mismatch is False
    assert "magika_unavailable" in result.details.get("error", "")


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------


def test_normalize_mime_strips_params():
    assert _normalize_mime("image/jpeg; charset=utf-8") == "image/jpeg"
    assert _normalize_mime("TEXT/PLAIN") == "text/plain"


def test_compute_fraud_score_clean():
    score = _compute_fraud_score("image/jpeg", "image/jpeg", 0.99, False, True)
    assert score == pytest.approx(0.0)


def test_compute_fraud_score_non_whitelist():
    score = _compute_fraud_score(
        "application/x-executable", "image/jpeg", 0.98, True, False
    )
    assert score == pytest.approx(1.0)


def test_compute_fraud_score_dangerous_mismatch():
    score = _compute_fraud_score("application/pdf", "image/jpeg", 0.98, True, True)
    assert score == pytest.approx(0.8)


def test_benign_mismatches_symmetric():
    # Both directions of the benign pair should map to 0.3
    score_fwd = _compute_fraud_score("image/webp", "image/jpeg", 0.99, True, True)
    score_rev = _compute_fraud_score("image/jpeg", "image/webp", 0.99, True, True)
    assert score_fwd == pytest.approx(0.3)
    assert score_rev == pytest.approx(0.3)
