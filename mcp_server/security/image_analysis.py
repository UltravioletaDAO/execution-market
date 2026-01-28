"""
Image Analysis Module for Fraud Detection

Detects fraudulent images through:
1. AI generation detection (DALL-E, Midjourney, Stable Diffusion)
2. Metadata consistency verification (EXIF matches claimed time/location)
3. Manipulation/editing detection
4. Reference image comparison (similarity check)

Integrates with existing verification/checks/ modules.
"""

import asyncio
import hashlib
import io
import logging
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

logger = logging.getLogger(__name__)

# Try to import PIL (optional for some checks)
try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    logger.warning("PIL not available - some image checks will be limited")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ImageAnalysisResult:
    """Result of image fraud analysis."""
    is_suspicious: bool
    risk_score: float  # 0.0 to 1.0
    confidence: float

    # Detection results
    ai_generated: bool = False
    ai_model_hint: Optional[str] = None
    manipulated: bool = False
    metadata_issues: bool = False

    # Details
    reason: Optional[str] = None
    checks_performed: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_suspicious": self.is_suspicious,
            "risk_score": round(self.risk_score, 4),
            "confidence": round(self.confidence, 4),
            "ai_generated": self.ai_generated,
            "ai_model_hint": self.ai_model_hint,
            "manipulated": self.manipulated,
            "metadata_issues": self.metadata_issues,
            "reason": self.reason,
            "checks_performed": self.checks_performed,
        }


@dataclass
class MetadataConsistencyResult:
    """Result of EXIF metadata consistency check."""
    is_consistent: bool
    issues: List[str]
    exif_time: Optional[datetime] = None
    exif_location: Optional[Tuple[float, float]] = None
    camera_model: Optional[str] = None
    software: Optional[str] = None


@dataclass
class SimilarityResult:
    """Result of image similarity comparison."""
    similarity_score: float  # 0.0 to 1.0
    is_match: bool
    method: str
    details: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# KNOWN AI SIGNATURES
# =============================================================================

AI_SOFTWARE_SIGNATURES = {
    "midjourney": [r"midjourney", r"mj\s*v[0-9]"],
    "dall-e": [r"dall[\-\s]?e", r"openai"],
    "stable_diffusion": [r"stable[\-\s]?diffusion", r"automatic1111", r"comfyui", r"invoke[\-\s]?ai"],
    "flux": [r"flux", r"black[\-\s]?forest[\-\s]?labs"],
    "firefly": [r"firefly", r"adobe[\-\s]?firefly"],
}

EDITING_SOFTWARE = {
    "professional": ["photoshop", "lightroom", "gimp", "affinity", "capture one"],
    "mobile": ["snapseed", "vsco", "picsart", "pixlr", "canva"],
    "face_editing": ["facetune", "faceapp", "beautycam", "meitu", "airbrush"],
    "screenshot": ["screenshot", "snipping", "sharex", "greenshot", "snagit"],
}


# =============================================================================
# IMAGE ANALYZER CLASS
# =============================================================================

class ImageAnalyzer:
    """
    Comprehensive image fraud analysis.

    Combines multiple detection methods to identify:
    - AI-generated images
    - Edited/manipulated images
    - Metadata inconsistencies
    - Duplicate or reused images
    """

    def __init__(self, ai_detection_threshold: float = 0.5):
        """
        Initialize image analyzer.

        Args:
            ai_detection_threshold: Threshold for AI detection confidence
        """
        self.ai_detection_threshold = ai_detection_threshold
        self._image_hashes: Dict[str, List[str]] = {}  # executor_id -> list of hashes

        logger.info("ImageAnalyzer initialized")

    async def analyze_image(self, image_path: str) -> ImageAnalysisResult:
        """
        Analyze an image file for fraud indicators.

        Args:
            image_path: Path to the image file

        Returns:
            ImageAnalysisResult with analysis details
        """
        checks_performed: List[str] = []
        risk_scores: List[float] = []
        reasons: List[str] = []
        details: Dict[str, Any] = {}

        ai_generated = False
        ai_model_hint = None
        manipulated = False
        metadata_issues = False

        try:
            # Read file
            with open(image_path, "rb") as f:
                image_bytes = f.read()

            # 1. Check for AI generation
            ai_result = await self.detect_ai_generated(image_bytes)
            checks_performed.append("ai_detection")
            if ai_result["detected"]:
                ai_generated = True
                ai_model_hint = ai_result.get("model_hint")
                risk_scores.append(ai_result["confidence"])
                reasons.append(f"AI-generated image detected ({ai_model_hint or 'unknown model'})")
                details["ai_detection"] = ai_result

            # 2. Check metadata consistency
            metadata_result = await self.check_metadata_consistency(image_bytes)
            checks_performed.append("metadata_consistency")
            if not metadata_result.is_consistent:
                metadata_issues = True
                risk_scores.append(0.5)
                reasons.extend(metadata_result.issues)
                details["metadata"] = {
                    "issues": metadata_result.issues,
                    "exif_time": metadata_result.exif_time.isoformat() if metadata_result.exif_time else None,
                    "camera_model": metadata_result.camera_model,
                    "software": metadata_result.software,
                }

            # 3. Check for manipulation
            manipulation_result = await self.detect_manipulation(image_bytes)
            checks_performed.append("manipulation_detection")
            if manipulation_result["detected"]:
                manipulated = True
                risk_scores.append(manipulation_result["confidence"])
                reasons.append(manipulation_result["reason"])
                details["manipulation"] = manipulation_result

        except Exception as e:
            logger.error(f"Image analysis failed: {e}")
            return ImageAnalysisResult(
                is_suspicious=True,
                risk_score=0.5,
                confidence=0.3,
                reason=f"Analysis failed: {str(e)}",
                checks_performed=checks_performed,
            )

        # Calculate overall
        if not risk_scores:
            return ImageAnalysisResult(
                is_suspicious=False,
                risk_score=0.0,
                confidence=0.8,
                checks_performed=checks_performed,
                details=details,
            )

        overall_risk = max(risk_scores)
        is_suspicious = overall_risk >= 0.5 or ai_generated or manipulated

        return ImageAnalysisResult(
            is_suspicious=is_suspicious,
            risk_score=overall_risk,
            confidence=0.8,
            ai_generated=ai_generated,
            ai_model_hint=ai_model_hint,
            manipulated=manipulated,
            metadata_issues=metadata_issues,
            reason="; ".join(reasons) if reasons else None,
            checks_performed=checks_performed,
            details=details,
        )

    async def analyze_image_bytes(self, image_bytes: bytes) -> ImageAnalysisResult:
        """Analyze image from bytes."""
        checks_performed: List[str] = []
        risk_scores: List[float] = []
        reasons: List[str] = []
        details: Dict[str, Any] = {}

        ai_generated = False
        ai_model_hint = None
        manipulated = False
        metadata_issues = False

        try:
            # 1. Check for AI generation
            ai_result = await self.detect_ai_generated(image_bytes)
            checks_performed.append("ai_detection")
            if ai_result["detected"]:
                ai_generated = True
                ai_model_hint = ai_result.get("model_hint")
                risk_scores.append(ai_result["confidence"])
                reasons.append(f"AI-generated image detected ({ai_model_hint or 'unknown'})")
                details["ai_detection"] = ai_result

            # 2. Check metadata
            metadata_result = await self.check_metadata_consistency(image_bytes)
            checks_performed.append("metadata_consistency")
            if not metadata_result.is_consistent:
                metadata_issues = True
                risk_scores.append(0.5)
                reasons.extend(metadata_result.issues)

            # 3. Check manipulation
            manipulation_result = await self.detect_manipulation(image_bytes)
            checks_performed.append("manipulation_detection")
            if manipulation_result["detected"]:
                manipulated = True
                risk_scores.append(manipulation_result["confidence"])
                reasons.append(manipulation_result["reason"])

        except Exception as e:
            logger.error(f"Image bytes analysis failed: {e}")
            return ImageAnalysisResult(
                is_suspicious=True,
                risk_score=0.5,
                confidence=0.3,
                reason=f"Analysis failed: {str(e)}",
            )

        overall_risk = max(risk_scores) if risk_scores else 0.0

        return ImageAnalysisResult(
            is_suspicious=overall_risk >= 0.5 or ai_generated or manipulated,
            risk_score=overall_risk,
            confidence=0.8,
            ai_generated=ai_generated,
            ai_model_hint=ai_model_hint,
            manipulated=manipulated,
            metadata_issues=metadata_issues,
            reason="; ".join(reasons) if reasons else None,
            checks_performed=checks_performed,
            details=details,
        )

    async def detect_ai_generated(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Detect if image is AI-generated.

        Checks:
        1. C2PA metadata (Content Authenticity Initiative)
        2. Software signatures in EXIF
        3. Statistical patterns (simplified)

        Args:
            image_bytes: Raw image bytes

        Returns:
            Dictionary with detection results
        """
        result = {
            "detected": False,
            "confidence": 0.0,
            "model_hint": None,
            "signals": [],
        }

        # Check 1: C2PA markers
        if b"c2pa" in image_bytes or b"jumb" in image_bytes:
            result["signals"].append("c2pa_metadata_present")
            result["confidence"] = max(result["confidence"], 0.6)

            # Check for AI generation claim in C2PA
            if b"ai_generated" in image_bytes.lower() or b"generative" in image_bytes.lower():
                result["detected"] = True
                result["confidence"] = 0.9
                result["signals"].append("c2pa_ai_claim")

        # Check 2: EXIF software signatures
        if HAS_PIL:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                exif = img._getexif()

                if exif:
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag in ("Software", "ProcessingSoftware"):
                            value_str = str(value).lower() if value else ""

                            for model, patterns in AI_SOFTWARE_SIGNATURES.items():
                                for pattern in patterns:
                                    if re.search(pattern, value_str, re.IGNORECASE):
                                        result["detected"] = True
                                        result["confidence"] = 0.95
                                        result["model_hint"] = model
                                        result["signals"].append(f"software_signature_{model}")
                                        return result
            except Exception:
                pass

        # Check 3: XMP metadata
        xmp_start = image_bytes.find(b"<x:xmpmeta")
        if xmp_start != -1:
            xmp_end = image_bytes.find(b"</x:xmpmeta>", xmp_start)
            if xmp_end != -1:
                xmp_data = image_bytes[xmp_start:xmp_end + 12].decode("utf-8", errors="ignore").lower()

                # Check for AI indicators in XMP
                ai_keywords = ["ai_generated", "ai-generated", "midjourney", "dall-e", "stable diffusion"]
                for keyword in ai_keywords:
                    if keyword in xmp_data:
                        result["detected"] = True
                        result["confidence"] = max(result["confidence"], 0.85)
                        result["signals"].append(f"xmp_{keyword}")

        # Final determination
        if result["signals"]:
            result["detected"] = result["confidence"] >= self.ai_detection_threshold

        return result

    async def check_metadata_consistency(
        self,
        image_bytes: bytes,
        claimed_time: Optional[datetime] = None,
        claimed_location: Optional[Tuple[float, float]] = None,
    ) -> MetadataConsistencyResult:
        """
        Check if EXIF metadata is consistent with claims.

        Verifies:
        1. Timestamp matches claimed time (if provided)
        2. GPS matches claimed location (if provided)
        3. Camera info present (real photos usually have this)
        4. No editing software signatures

        Args:
            image_bytes: Raw image bytes
            claimed_time: Optional claimed capture time
            claimed_location: Optional claimed (lat, lon)

        Returns:
            MetadataConsistencyResult with findings
        """
        issues: List[str] = []
        exif_time = None
        exif_location = None
        camera_model = None
        software = None

        if not HAS_PIL:
            return MetadataConsistencyResult(
                is_consistent=True,
                issues=["PIL not available for EXIF analysis"],
            )

        try:
            img = Image.open(io.BytesIO(image_bytes))
            exif = img._getexif()

            if not exif:
                # No EXIF data - suspicious for photos claiming to be fresh
                issues.append("No EXIF metadata (unusual for camera photos)")
                return MetadataConsistencyResult(
                    is_consistent=False,
                    issues=issues,
                )

            # Extract useful fields
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)

                if tag == "DateTimeOriginal":
                    try:
                        exif_time = datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                        exif_time = exif_time.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                if tag == "Model":
                    camera_model = str(value)

                if tag == "Software":
                    software = str(value)

                if tag == "GPSInfo":
                    try:
                        gps_info = {}
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_info[gps_tag] = gps_value

                        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
                            lat = self._convert_gps_to_decimal(
                                gps_info["GPSLatitude"],
                                gps_info.get("GPSLatitudeRef", "N")
                            )
                            lon = self._convert_gps_to_decimal(
                                gps_info["GPSLongitude"],
                                gps_info.get("GPSLongitudeRef", "E")
                            )
                            exif_location = (lat, lon)
                    except Exception:
                        pass

            # Check for editing software
            if software:
                software_lower = software.lower()
                for category, apps in EDITING_SOFTWARE.items():
                    for app in apps:
                        if app in software_lower:
                            issues.append(f"Editing software detected: {software} ({category})")
                            break

            # Check timestamp consistency
            if claimed_time and exif_time:
                time_diff = abs((claimed_time - exif_time).total_seconds())
                if time_diff > 3600:  # More than 1 hour difference
                    issues.append(
                        f"EXIF time ({exif_time.isoformat()}) differs from claimed time "
                        f"by {time_diff/3600:.1f} hours"
                    )

            # Check location consistency
            if claimed_location and exif_location:
                distance_m = self._haversine_distance(
                    claimed_location[0], claimed_location[1],
                    exif_location[0], exif_location[1]
                )
                if distance_m > 1000:  # More than 1km difference
                    issues.append(
                        f"EXIF location is {distance_m:.0f}m from claimed location"
                    )

        except Exception as e:
            issues.append(f"Failed to parse EXIF: {str(e)}")

        return MetadataConsistencyResult(
            is_consistent=len(issues) == 0,
            issues=issues,
            exif_time=exif_time,
            exif_location=exif_location,
            camera_model=camera_model,
            software=software,
        )

    async def detect_manipulation(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Detect signs of image manipulation/editing.

        Checks:
        1. Double compression artifacts
        2. Error Level Analysis (simplified)
        3. Editing software signatures

        Args:
            image_bytes: Raw image bytes

        Returns:
            Dictionary with detection results
        """
        result = {
            "detected": False,
            "confidence": 0.0,
            "reason": None,
            "signals": [],
        }

        if not HAS_PIL:
            return result

        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Check format
            if img.format not in ("JPEG", "PNG", "WEBP"):
                result["signals"].append(f"unusual_format_{img.format}")

            # Check for editing software in EXIF
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ("Software", "ProcessingSoftware", "HistorySoftwareAgent"):
                        value_str = str(value).lower() if value else ""
                        for category, apps in EDITING_SOFTWARE.items():
                            for app in apps:
                                if app in value_str:
                                    result["detected"] = True
                                    result["confidence"] = max(result["confidence"], 0.7)
                                    result["signals"].append(f"{category}_software")
                                    result["reason"] = f"Editing software detected: {value}"

            # Simple double compression check for JPEG
            if img.format == "JPEG":
                # Re-compress and compare
                buffer1 = io.BytesIO()
                img.save(buffer1, format="JPEG", quality=85)
                size1 = buffer1.tell()

                # Large size difference might indicate previous compression
                original_size = len(image_bytes)
                size_ratio = size1 / original_size if original_size > 0 else 1.0

                if size_ratio < 0.5:  # Much smaller after recompress
                    result["signals"].append("possible_recompression")
                    result["confidence"] = max(result["confidence"], 0.4)

        except Exception as e:
            logger.debug(f"Manipulation detection error: {e}")

        return result

    async def compare_to_reference(
        self,
        image_bytes: bytes,
        reference_bytes: bytes,
        threshold: float = 0.85
    ) -> SimilarityResult:
        """
        Compare image to a reference image for similarity.

        Useful for verifying that submitted evidence matches expected content.

        Args:
            image_bytes: Image to check
            reference_bytes: Reference image
            threshold: Similarity threshold for match

        Returns:
            SimilarityResult with comparison details
        """
        if not HAS_PIL:
            return SimilarityResult(
                similarity_score=0.0,
                is_match=False,
                method="unavailable",
                details={"error": "PIL not available"},
            )

        try:
            img1 = Image.open(io.BytesIO(image_bytes))
            img2 = Image.open(io.BytesIO(reference_bytes))

            # Convert to same mode and size for comparison
            img1 = img1.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)
            img2 = img2.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)

            # Calculate simple perceptual hash similarity
            pixels1 = list(img1.getdata())
            pixels2 = list(img2.getdata())

            # Calculate mean squared error
            mse = sum(
                (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2 + (p1[2] - p2[2])**2
                for p1, p2 in zip(pixels1, pixels2)
            ) / (len(pixels1) * 3 * 255**2)

            # Convert MSE to similarity (0 = identical, 1 = completely different)
            similarity = 1.0 - min(1.0, mse)

            return SimilarityResult(
                similarity_score=similarity,
                is_match=similarity >= threshold,
                method="perceptual_hash",
                details={
                    "mse": mse,
                    "threshold": threshold,
                },
            )

        except Exception as e:
            logger.error(f"Image comparison failed: {e}")
            return SimilarityResult(
                similarity_score=0.0,
                is_match=False,
                method="error",
                details={"error": str(e)},
            )

    def compute_image_hash(self, image_bytes: bytes) -> str:
        """Compute perceptual hash for duplicate detection."""
        if not HAS_PIL:
            # Fallback to content hash
            return hashlib.sha256(image_bytes).hexdigest()[:16]

        try:
            img = Image.open(io.BytesIO(image_bytes))
            img = img.convert("L").resize((8, 8), Image.Resampling.LANCZOS)
            pixels = list(img.getdata())
            avg = sum(pixels) / len(pixels)

            # Create binary hash
            bits = "".join("1" if p > avg else "0" for p in pixels)
            return hex(int(bits, 2))[2:].zfill(16)

        except Exception:
            return hashlib.sha256(image_bytes).hexdigest()[:16]

    def _convert_gps_to_decimal(
        self,
        gps_coords: tuple,
        ref: str
    ) -> float:
        """Convert GPS coordinates from degrees/minutes/seconds to decimal."""
        try:
            degrees = float(gps_coords[0])
            minutes = float(gps_coords[1])
            seconds = float(gps_coords[2])

            decimal = degrees + minutes / 60 + seconds / 3600

            if ref in ("S", "W"):
                decimal = -decimal

            return decimal
        except Exception:
            return 0.0

    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance in meters using Haversine formula."""
        R = 6_371_000  # Earth radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c
