"""
AWS Rekognition Integration for Evidence Verification

Provides structured image analysis as supplementary context for
PHOTINT verification prompts. NOT a replacement for vision LLMs —
Rekognition detects labels/text/moderation but cannot reason about
task completion semantics.

Results are injected into the PHOTINT prompt as "Pre-Analysis" context
so the vision model can cross-reference.

Part of PHOTINT Verification Overhaul (Phase 4).
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Kill switch
REKOGNITION_ENABLED = os.environ.get(
    "VERIFICATION_REKOGNITION_ENABLED", "false"
).lower() in (
    "true",
    "1",
    "yes",
)
REKOGNITION_REGION = os.environ.get("AWS_REKOGNITION_REGION", "us-east-2")


@dataclass
class RekognitionResult:
    """Structured results from AWS Rekognition analysis."""

    # Labels: objects, scenes, activities
    labels: List[Dict[str, Any]] = field(default_factory=list)

    # Detected text (OCR)
    text_detections: List[Dict[str, Any]] = field(default_factory=list)
    extracted_text: str = ""

    # Content moderation
    moderation_labels: List[Dict[str, Any]] = field(default_factory=list)
    has_moderation_flags: bool = False

    # Image quality
    quality: Optional[Dict[str, float]] = None

    # Face detection
    face_count: int = 0

    # Meta
    available: bool = False
    error: Optional[str] = None

    def to_prompt_context(self) -> str:
        """Format Rekognition results for prompt injection."""
        if not self.available:
            return ""

        lines = []

        # Top labels
        if self.labels:
            top = self.labels[:10]
            label_strs = [f"{l['name']}({l['confidence']:.0f}%)" for l in top]
            lines.append(f"Detected objects/scenes: {', '.join(label_strs)}")

        # Extracted text
        if self.extracted_text:
            # Truncate to avoid prompt bloat
            text = self.extracted_text[:500]
            lines.append(f"Detected text (OCR): {text}")

        # Moderation
        if self.has_moderation_flags:
            mod_strs = [
                f"{m['name']}({m['confidence']:.0f}%)"
                for m in self.moderation_labels[:5]
            ]
            lines.append(f"Moderation flags: {', '.join(mod_strs)}")

        # Faces
        if self.face_count > 0:
            lines.append(f"Faces detected: {self.face_count}")

        # Quality
        if self.quality:
            sharpness = self.quality.get("sharpness", 0)
            brightness = self.quality.get("brightness", 0)
            lines.append(
                f"Image quality: sharpness={sharpness:.0f}, brightness={brightness:.0f}"
            )

        return "\n".join(lines) if lines else ""


async def analyze_with_rekognition(
    image_bytes: bytes,
) -> RekognitionResult:
    """
    Analyze an image using AWS Rekognition.

    Runs detect_labels, detect_text, and detect_moderation_labels.
    Fire-and-forget: returns empty result on any failure.

    Args:
        image_bytes: Raw image bytes.

    Returns:
        RekognitionResult with all detections.
    """
    result = RekognitionResult()

    if not REKOGNITION_ENABLED:
        return result

    try:
        import boto3

        client = boto3.client("rekognition", region_name=REKOGNITION_REGION)
        image_param = {"Bytes": image_bytes}

        # Run all three detections
        # Labels
        try:
            labels_resp = client.detect_labels(
                Image=image_param,
                MaxLabels=15,
                MinConfidence=60,
            )
            result.labels = [
                {"name": l["Name"], "confidence": l["Confidence"]}
                for l in labels_resp.get("Labels", [])
            ]
        except Exception as e:
            logger.warning("Rekognition detect_labels failed: %s", e)

        # Text (OCR)
        try:
            text_resp = client.detect_text(Image=image_param)
            detections = text_resp.get("TextDetections", [])
            result.text_detections = [
                {
                    "text": d["DetectedText"],
                    "type": d["Type"],
                    "confidence": d["Confidence"],
                }
                for d in detections
                if d["Type"] == "LINE" and d["Confidence"] >= 70
            ]
            result.extracted_text = " | ".join(
                d["text"] for d in result.text_detections
            )
        except Exception as e:
            logger.warning("Rekognition detect_text failed: %s", e)

        # Moderation
        try:
            mod_resp = client.detect_moderation_labels(
                Image=image_param,
                MinConfidence=60,
            )
            result.moderation_labels = [
                {"name": m["Name"], "confidence": m["Confidence"]}
                for m in mod_resp.get("ModerationLabels", [])
            ]
            result.has_moderation_flags = len(result.moderation_labels) > 0
        except Exception as e:
            logger.warning("Rekognition detect_moderation_labels failed: %s", e)

        # Face detection (lightweight)
        try:
            face_resp = client.detect_faces(
                Image=image_param,
                Attributes=["DEFAULT"],
            )
            faces = face_resp.get("FaceDetails", [])
            result.face_count = len(faces)
            if faces:
                # Get quality from first face
                quality = faces[0].get("Quality", {})
                result.quality = {
                    "sharpness": quality.get("Sharpness", 0),
                    "brightness": quality.get("Brightness", 0),
                }
        except Exception as e:
            logger.warning("Rekognition detect_faces failed: %s", e)

        result.available = True
        logger.info(
            "Rekognition analysis: %d labels, %d text, %d moderation, %d faces",
            len(result.labels),
            len(result.text_detections),
            len(result.moderation_labels),
            result.face_count,
        )

    except ImportError:
        result.error = "boto3 not available"
        logger.debug("Rekognition skipped: boto3 not installed")
    except Exception as e:
        result.error = str(e)
        logger.warning("Rekognition analysis failed: %s", e)

    return result
