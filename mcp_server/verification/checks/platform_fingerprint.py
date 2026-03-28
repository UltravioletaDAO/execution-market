"""
Platform Fingerprinting for Evidence Verification

Detects which messaging/social platform processed an image based on
file characteristics: resolution, DPI, container type, filename pattern,
compression signature.

Part of PHOTINT Verification Overhaul (Phase 5).
"""

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PlatformFingerprint:
    """Detected platform processing chain."""

    platform: str  # "original", "whatsapp", "telegram", "instagram", "twitter", "screenshot", "unknown"
    confidence: float  # 0.0-1.0
    hops_estimate: int  # Estimated number of platform hops
    signals: list  # Evidence supporting the detection
    reason: str = ""

    def to_context(self) -> str:
        """Format for prompt injection."""
        if self.platform == "original":
            return f"Platform chain: Original camera capture (confidence: {self.confidence:.0%})"
        return (
            f"Platform chain: {self.platform} "
            f"(confidence: {self.confidence:.0%}, ~{self.hops_estimate} hop(s)). "
            f"Signals: {', '.join(self.signals[:3])}"
        )


# Known platform patterns
_WHATSAPP_FILENAME = re.compile(r"IMG-\d{8}-WA\d{4}", re.IGNORECASE)
_TELEGRAM_FILENAME = re.compile(r"photo_\d{4}-\d{2}-\d{2}", re.IGNORECASE)
_SCREENSHOT_FILENAME = re.compile(r"Screenshot[_\s]", re.IGNORECASE)
_CAMERA_ANDROID = re.compile(r"IMG_\d{8}_\d{6}", re.IGNORECASE)
_CAMERA_IPHONE = re.compile(r"IMG_\d{4}\.(HEIC|JPG|jpeg)", re.IGNORECASE)
_CAMERA_PIXEL = re.compile(r"PXL_\d{8}_\d+", re.IGNORECASE)


def check_platform(
    image_path: str,
    *,
    width: Optional[int] = None,
    height: Optional[int] = None,
    has_exif: bool = True,
    container_type: Optional[str] = None,
) -> PlatformFingerprint:
    """
    Detect which platform processed an image.

    Args:
        image_path: Path to the image file.
        width: Image width in pixels (if already known).
        height: Image height in pixels (if already known).
        has_exif: Whether EXIF metadata is present.
        container_type: "EXIF" or "JFIF" (if already detected).

    Returns:
        PlatformFingerprint with detection results.
    """
    signals = []
    scores = {}  # platform -> cumulative score

    filename = os.path.basename(image_path)
    path = Path(image_path)

    # --- Filename analysis ---
    if _WHATSAPP_FILENAME.search(filename):
        scores["whatsapp"] = scores.get("whatsapp", 0) + 0.6
        signals.append(f"WhatsApp filename pattern: {filename}")

    if _TELEGRAM_FILENAME.search(filename):
        scores["telegram"] = scores.get("telegram", 0) + 0.6
        signals.append(f"Telegram filename pattern: {filename}")

    if _SCREENSHOT_FILENAME.search(filename):
        scores["screenshot"] = scores.get("screenshot", 0) + 0.5
        signals.append("Screenshot filename pattern")

    if _CAMERA_ANDROID.search(filename) or _CAMERA_PIXEL.search(filename):
        scores["original"] = scores.get("original", 0) + 0.3
        signals.append("Android camera filename pattern")

    if _CAMERA_IPHONE.search(filename):
        scores["original"] = scores.get("original", 0) + 0.3
        signals.append("iPhone camera filename pattern")

    # --- EXIF analysis ---
    if not has_exif:
        # No EXIF = processed through a stripping platform
        for p in ("whatsapp", "telegram", "instagram"):
            scores[p] = scores.get(p, 0) + 0.3
        signals.append("EXIF metadata stripped")
    else:
        scores["original"] = scores.get("original", 0) + 0.3
        signals.append("EXIF metadata present")

    # --- Container analysis ---
    if container_type == "JFIF":
        # JFIF = re-encoded (messaging platform)
        for p in ("whatsapp", "telegram"):
            scores[p] = scores.get(p, 0) + 0.2
        signals.append("JFIF container (re-encoded)")
    elif container_type == "EXIF":
        scores["original"] = scores.get("original", 0) + 0.2
        signals.append("EXIF container (closer to original)")

    # --- Resolution analysis ---
    if width and height:
        long_edge = max(width, height)
        megapixels = (width * height) / 1_000_000

        if 1500 <= long_edge <= 1700:
            scores["whatsapp"] = scores.get("whatsapp", 0) + 0.3
            signals.append(f"WhatsApp standard resolution ({long_edge}px)")
        elif 3900 <= long_edge <= 4200:
            scores["whatsapp_hd"] = scores.get("whatsapp", 0) + 0.2
            signals.append(f"WhatsApp HD resolution ({long_edge}px)")
        elif 1200 <= long_edge <= 1400:
            scores["telegram"] = scores.get("telegram", 0) + 0.3
            signals.append(f"Telegram standard resolution ({long_edge}px)")
        elif long_edge == 1080 and width == 1080:
            scores["instagram"] = scores.get("instagram", 0) + 0.4
            signals.append("Instagram square crop (1080px)")

        if megapixels >= 8:
            scores["original"] = scores.get("original", 0) + 0.2
            signals.append(f"High resolution ({megapixels:.1f} MP)")
        elif megapixels < 2:
            signals.append(f"Low resolution ({megapixels:.1f} MP) — platform-processed")

    # --- File size analysis ---
    try:
        file_size = path.stat().st_size
        if file_size < 200_000 and width and width > 1000:
            # Small file for large image = heavy compression
            signals.append(
                f"Heavy compression ({file_size / 1024:.0f} KB for {width}px)"
            )
            for p in ("whatsapp", "telegram"):
                scores[p] = scores.get(p, 0) + 0.1
    except Exception:
        pass

    # --- Determine winner ---
    if not scores:
        return PlatformFingerprint(
            platform="unknown",
            confidence=0.0,
            hops_estimate=0,
            signals=signals,
            reason="Insufficient data for platform detection",
        )

    best_platform = max(scores, key=scores.get)
    best_score = min(scores[best_platform], 1.0)

    # Estimate hops
    hops = 0
    if best_platform == "original":
        hops = 0
    elif best_platform in ("whatsapp", "telegram", "instagram", "twitter"):
        hops = 1
    elif best_platform == "screenshot":
        hops = 1

    return PlatformFingerprint(
        platform=best_platform,
        confidence=round(best_score, 2),
        hops_estimate=hops,
        signals=signals,
        reason=f"Detected: {best_platform} ({best_score:.0%} confidence, {len(signals)} signals)",
    )
