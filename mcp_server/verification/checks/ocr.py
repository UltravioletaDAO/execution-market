"""
OCR Enhancement for Evidence Verification

Pre-extracts text from receipt/document photos before sending to
the vision model. Results are included in the PHOTINT prompt as
additional context for cross-referencing.

Supports:
- AWS Rekognition detect_text (preferred, if available)
- Pillow-based basic text region detection (fallback)

Part of PHOTINT Verification Overhaul (Phase 5).
"""

import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OcrResult:
    """OCR extraction result."""

    text_blocks: List[dict] = field(default_factory=list)  # [{text, confidence, type}]
    full_text: str = ""
    has_text: bool = False
    method: str = "none"  # "rekognition", "pillow", "none"
    error: Optional[str] = None

    def to_context(self) -> str:
        """Format OCR results for prompt injection."""
        if not self.has_text:
            return ""

        lines = [f"Extracted text ({self.method}):"]
        # Show up to 10 text blocks
        for block in self.text_blocks[:10]:
            text = block.get("text", "")
            confidence = block.get("confidence", 0)
            lines.append(f'  - "{text}" ({confidence:.0f}%)')

        return "\n".join(lines)


async def extract_text(
    image_path: Optional[str] = None,
    image_bytes: Optional[bytes] = None,
) -> OcrResult:
    """
    Extract text from an image using available OCR method.

    Tries AWS Rekognition first (if enabled), falls back to basic detection.

    Args:
        image_path: Path to image file.
        image_bytes: Raw image bytes (alternative to path).

    Returns:
        OcrResult with extracted text blocks.
    """
    result = OcrResult()

    # Load image bytes if path provided
    if image_bytes is None and image_path:
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
        except Exception as e:
            result.error = f"Failed to read image: {e}"
            return result

    if image_bytes is None:
        result.error = "No image provided"
        return result

    # Try Rekognition first
    rekognition_enabled = os.environ.get(
        "VERIFICATION_REKOGNITION_ENABLED", "false"
    ).lower() in ("true", "1", "yes")

    if rekognition_enabled:
        try:
            result = await _extract_with_rekognition(image_bytes)
            if result.has_text:
                return result
        except Exception as e:
            logger.debug("Rekognition OCR failed, using fallback: %s", e)

    # Fallback: basic text presence detection via Pillow
    try:
        result = _detect_text_regions(image_bytes)
    except Exception as e:
        result.error = f"OCR failed: {e}"
        logger.warning("OCR extraction failed: %s", e)

    return result


async def _extract_with_rekognition(image_bytes: bytes) -> OcrResult:
    """Extract text using AWS Rekognition."""
    import boto3

    region = os.environ.get("AWS_REKOGNITION_REGION", "us-east-2")
    client = boto3.client("rekognition", region_name=region)

    resp = client.detect_text(Image={"Bytes": image_bytes})
    detections = resp.get("TextDetections", [])

    result = OcrResult(method="rekognition")

    for det in detections:
        if det["Type"] == "LINE" and det["Confidence"] >= 60:
            result.text_blocks.append(
                {
                    "text": det["DetectedText"],
                    "confidence": det["Confidence"],
                    "type": det["Type"],
                }
            )

    if result.text_blocks:
        result.has_text = True
        result.full_text = " | ".join(b["text"] for b in result.text_blocks)

    return result


def _detect_text_regions(image_bytes: bytes) -> OcrResult:
    """
    Basic text region detection using Pillow.

    Does NOT perform actual OCR — just detects likely text regions
    based on high-contrast, sharp-edge patterns. Reports whether
    text appears to be present and roughly how much.
    """
    import io

    from PIL import Image, ImageFilter, ImageStat

    result = OcrResult(method="pillow")

    with Image.open(io.BytesIO(image_bytes)) as img:
        # Convert to grayscale
        gray = img.convert("L")

        # Edge detection to find text-like regions
        edges = gray.filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(edges)

        edge_mean = stat.mean[0]
        edge_std = stat.stddev[0]

        # High edge density suggests text presence
        if edge_mean > 15 and edge_std > 20:
            result.has_text = True
            density = "high" if edge_mean > 30 else "moderate"
            result.text_blocks = [
                {
                    "text": f"[Text regions detected - {density} density]",
                    "confidence": min(edge_mean * 2, 95),
                    "type": "detection",
                }
            ]
            result.full_text = f"Text regions detected ({density} density)"

    return result
