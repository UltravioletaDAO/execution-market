"""
Evidence Tampering Detection

Detects signs of image manipulation, editing, or fraud using:
- EXIF software tag analysis
- Compression artifact analysis
- Error Level Analysis (ELA)
- Resolution anomaly detection
- Metadata consistency checks
"""

import io
import math
from dataclasses import dataclass
from typing import Optional
from PIL import Image
from PIL.ExifTags import TAGS
import piexif


@dataclass
class TamperingResult:
    """Result of tampering detection analysis."""

    is_suspicious: bool
    confidence: float  # 0.0 to 1.0 (how likely tampered)
    signals: list[str]  # List of detected tampering signals
    details: dict  # Detailed analysis data
    reason: Optional[str]  # Human-readable summary if suspicious

    @property
    def normalized_score(self) -> float:
        """Normalized score 0.0-1.0 where 1.0 = no tampering detected (passed).

        Inverts confidence: low tampering confidence -> high score (good).
        An untampered photo (confidence=0) scores 1.0,
        a confirmed tampered photo (confidence=1) scores 0.0.
        """
        return round(1.0 - self.confidence, 4)


def check_tampering(image_path: str) -> TamperingResult:
    """
    Analyze an image for evidence of tampering or manipulation.

    Performs multiple checks:
    1. EXIF software tags (detect editing apps)
    2. Compression artifacts (JPEG quality analysis)
    3. Error Level Analysis (ELA)
    4. Resolution anomaly detection
    5. Metadata consistency

    Args:
        image_path: Path to the image file

    Returns:
        TamperingResult with suspicion level and details
    """
    signals: list[str] = []
    details: dict = {}

    try:
        img = Image.open(image_path)
        exif_data = _get_exif_data(img)

        # Run all tampering checks
        software_signals = _check_software_tags(exif_data)
        signals.extend(software_signals)
        details["software_analysis"] = {
            "signals": software_signals,
            "software_tag": exif_data.get("Software"),
            "processing_software": exif_data.get("ProcessingSoftware"),
        }

        compression_result = _check_compression_artifacts(img, image_path)
        signals.extend(compression_result["signals"])
        details["compression_analysis"] = compression_result

        ela_result = _perform_ela_analysis(img)
        signals.extend(ela_result["signals"])
        details["ela_analysis"] = ela_result

        resolution_result = _check_resolution_anomalies(img, exif_data)
        signals.extend(resolution_result["signals"])
        details["resolution_analysis"] = resolution_result

        metadata_result = _check_metadata_consistency(exif_data, img)
        signals.extend(metadata_result["signals"])
        details["metadata_analysis"] = metadata_result

        # Calculate overall confidence
        confidence = _calculate_confidence(signals, details)

        # Determine if suspicious
        is_suspicious = confidence >= 0.5 or len(signals) >= 3

        # Generate reason
        reason = None
        if is_suspicious:
            if signals:
                reason = f"Tampering suspected ({len(signals)} signals): {', '.join(signals[:3])}"
                if len(signals) > 3:
                    reason += f" (+{len(signals) - 3} more)"
            else:
                reason = "Image analysis indicates potential manipulation"

        return TamperingResult(
            is_suspicious=is_suspicious,
            confidence=confidence,
            signals=signals,
            details=details,
            reason=reason,
        )

    except Exception as e:
        return TamperingResult(
            is_suspicious=True,
            confidence=0.8,
            signals=["analysis_failed"],
            details={"error": str(e)},
            reason=f"Failed to analyze image: {str(e)}",
        )


def _get_exif_data(img: Image.Image) -> dict:
    """Extract EXIF data from image."""
    exif_data = {}

    try:
        raw_exif = img._getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8", errors="ignore")
                    except Exception:
                        value = str(value)
                exif_data[tag] = value
    except Exception:
        pass

    # Also try piexif for more detailed data
    try:
        exif_bytes = img.info.get("exif", b"")
        if exif_bytes:
            exif_dict = piexif.load(exif_bytes)
            for ifd in ("0th", "Exif", "GPS", "1st"):
                if ifd in exif_dict and exif_dict[ifd]:
                    for tag_id, value in exif_dict[ifd].items():
                        tag_info = piexif.TAGS.get(ifd, {}).get(tag_id, {})
                        tag_name = tag_info.get("name", str(tag_id))
                        if isinstance(value, bytes):
                            try:
                                value = value.decode("utf-8", errors="ignore")
                            except Exception:
                                value = str(value)
                        exif_data[tag_name] = value
    except Exception:
        pass

    return exif_data


def _check_software_tags(exif_data: dict) -> list[str]:
    """
    Detect editing software from EXIF tags.

    Looks for known photo editing applications in:
    - Software tag
    - ProcessingSoftware tag
    - HostComputer tag
    """
    signals = []

    # Known editing/manipulation software
    editing_apps = {
        # Professional editors
        "photoshop": "professional_editor",
        "lightroom": "professional_editor",
        "gimp": "professional_editor",
        "affinity": "professional_editor",
        "capture one": "professional_editor",
        "darktable": "professional_editor",
        "rawtherapee": "professional_editor",
        # Mobile editors
        "snapseed": "mobile_editor",
        "vsco": "mobile_editor",
        "picsart": "mobile_editor",
        "pics art": "mobile_editor",
        "pixlr": "mobile_editor",
        "canva": "mobile_editor",
        "afterlight": "mobile_editor",
        "facetune": "face_editor",
        "retouch": "mobile_editor",
        "airbrush": "face_editor",
        "beautycam": "face_editor",
        "snow": "face_editor",
        "b612": "face_editor",
        "meitu": "face_editor",
        "faceapp": "ai_manipulation",
        # AI tools
        "midjourney": "ai_generated",
        "dall-e": "ai_generated",
        "stable diffusion": "ai_generated",
        "stablediffusion": "ai_generated",
        "comfyui": "ai_generated",
        "automatic1111": "ai_generated",
        # Screenshot tools
        "screenshot": "screenshot_tool",
        "snipping": "screenshot_tool",
        "grab": "screenshot_tool",
        "capture": "screenshot_tool",
        "greenshot": "screenshot_tool",
        "snagit": "screenshot_tool",
        "sharex": "screenshot_tool",
        # Social media (indicates re-save)
        "instagram": "social_media_resave",
        "facebook": "social_media_resave",
        "twitter": "social_media_resave",
        "whatsapp": "social_media_resave",
        "telegram": "social_media_resave",
        "snapchat": "social_media_resave",
        "tiktok": "social_media_resave",
    }

    # Check Software tag
    software = str(exif_data.get("Software", "")).lower()
    processing = str(exif_data.get("ProcessingSoftware", "")).lower()
    host = str(exif_data.get("HostComputer", "")).lower()

    for app, category in editing_apps.items():
        if app in software or app in processing or app in host:
            signals.append(f"{category}_detected:{app}")

    # Check for generic modification indicators
    if "edited" in software or "modified" in software:
        signals.append("edited_flag_in_software")

    # Check ImageHistory tag (Adobe products)
    history = str(exif_data.get("ImageHistory", "")).lower()
    if history and ("save" in history or "edit" in history or "adjust" in history):
        signals.append("image_history_shows_edits")

    # Check HistorySoftwareAgent (common in edited images)
    history_agent = str(exif_data.get("HistorySoftwareAgent", "")).lower()
    if history_agent:
        signals.append(f"history_software_agent_present:{history_agent[:50]}")

    return signals


def _check_compression_artifacts(img: Image.Image, image_path: str) -> dict:
    """
    Analyze JPEG compression artifacts.

    Multiple re-saves at different quality levels leave artifacts.
    """
    result = {
        "signals": [],
        "format": img.format,
        "estimated_quality": None,
        "double_compression_suspected": False,
    }

    # Only applicable to JPEG
    if img.format not in ("JPEG", "MPO"):
        result["skipped"] = "not_jpeg"
        return result

    try:
        # Estimate JPEG quality by re-encoding and comparing
        quality_estimates = []

        for test_quality in [95, 85, 75, 65, 55, 45]:
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=test_quality)
            compressed_size = buffer.tell()
            quality_estimates.append((test_quality, compressed_size))

        # Get original file size
        with open(image_path, "rb") as f:
            f.seek(0, 2)
            original_size = f.tell()

        # Estimate original quality
        result["original_size"] = original_size
        result["quality_estimates"] = quality_estimates

        # Find closest quality match
        min_diff = float("inf")
        estimated_quality = 85
        for quality, size in quality_estimates:
            diff = abs(size - original_size)
            if diff < min_diff:
                min_diff = diff
                estimated_quality = quality

        result["estimated_quality"] = estimated_quality

        # Very low quality (< 60) is suspicious for "fresh" photos
        if estimated_quality < 60:
            result["signals"].append("very_low_jpeg_quality")

        # Check for double compression artifacts
        # This is a simplified check - in practice would use DCT analysis
        if estimated_quality < 80:
            # Re-compress at estimated quality and compare
            buffer1 = io.BytesIO()
            img.save(buffer1, format="JPEG", quality=estimated_quality)
            buffer1.seek(0)
            recompressed = Image.open(buffer1)

            # Compare histogram distributions
            orig_hist = img.histogram()
            recomp_hist = recompressed.histogram()

            hist_diff = sum(abs(a - b) for a, b in zip(orig_hist, recomp_hist))
            hist_diff_normalized = hist_diff / (sum(orig_hist) + 1)

            result["histogram_difference"] = hist_diff_normalized

            # High difference at low quality suggests double compression
            if hist_diff_normalized > 0.1 and estimated_quality < 70:
                result["signals"].append("double_compression_suspected")
                result["double_compression_suspected"] = True

    except Exception as e:
        result["error"] = str(e)

    return result


def _perform_ela_analysis(img: Image.Image) -> dict:
    """
    Perform Error Level Analysis (ELA).

    ELA highlights areas that were saved at different compression levels,
    which can indicate manipulation.
    """
    result = {
        "signals": [],
        "max_ela_value": 0,
        "ela_variance": 0,
        "suspicious_regions": 0,
    }

    try:
        # Convert to RGB if needed
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Compress image at known quality
        quality = 90
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        compressed = Image.open(buffer)

        # Calculate difference
        orig_pixels = list(img.getdata())
        comp_pixels = list(compressed.getdata())

        ela_values = []
        for orig, comp in zip(orig_pixels, comp_pixels):
            # Calculate RGB difference
            diff = sum(abs(o - c) for o, c in zip(orig, comp))
            ela_values.append(diff)

        if ela_values:
            # Statistical analysis
            max_ela = max(ela_values)
            mean_ela = sum(ela_values) / len(ela_values)
            variance = sum((v - mean_ela) ** 2 for v in ela_values) / len(ela_values)
            std_dev = math.sqrt(variance)

            result["max_ela_value"] = max_ela
            result["mean_ela_value"] = mean_ela
            result["ela_variance"] = variance
            result["ela_std_dev"] = std_dev

            # Count suspicious regions (high ELA values)
            threshold = mean_ela + 2 * std_dev
            suspicious_count = sum(1 for v in ela_values if v > threshold)
            suspicious_ratio = suspicious_count / len(ela_values)

            result["suspicious_pixel_ratio"] = suspicious_ratio
            result["suspicious_threshold"] = threshold

            # High variance with localized high values suggests manipulation
            if suspicious_ratio > 0.05 and max_ela > 100:
                result["signals"].append("ela_anomaly_detected")

            # Very uniform ELA can indicate AI generation
            if std_dev < 5 and mean_ela < 10:
                result["signals"].append("ela_too_uniform_possible_ai")

    except Exception as e:
        result["error"] = str(e)

    return result


def _check_resolution_anomalies(img: Image.Image, exif_data: dict) -> dict:
    """
    Detect resolution anomalies that indicate manipulation.

    Checks:
    - Unusual aspect ratios
    - Non-standard resolutions
    - Mismatch between EXIF and actual dimensions
    - Evidence of cropping or resizing
    """
    result = {
        "signals": [],
        "width": img.width,
        "height": img.height,
        "aspect_ratio": img.width / img.height if img.height > 0 else 0,
    }

    # Check EXIF dimensions vs actual
    exif_width = exif_data.get("ExifImageWidth") or exif_data.get("ImageWidth")
    exif_height = exif_data.get("ExifImageHeight") or exif_data.get("ImageLength")

    if exif_width and exif_height:
        try:
            exif_width = int(exif_width)
            exif_height = int(exif_height)
            result["exif_width"] = exif_width
            result["exif_height"] = exif_height

            # Check for dimension mismatch
            if exif_width != img.width or exif_height != img.height:
                # Allow small differences (some apps round)
                width_diff = abs(exif_width - img.width)
                height_diff = abs(exif_height - img.height)

                if width_diff > 10 or height_diff > 10:
                    result["signals"].append("exif_dimension_mismatch")
                    result["dimension_mismatch"] = {
                        "exif": (exif_width, exif_height),
                        "actual": (img.width, img.height),
                    }
        except Exception:
            pass

    # Check for suspicious aspect ratios
    aspect = result["aspect_ratio"]

    # Common photo aspect ratios
    standard_aspects = [
        4 / 3,  # Most phone cameras
        3 / 4,  # Portrait
        16 / 9,  # Wide
        9 / 16,  # Vertical video/stories
        1.0,  # Square (social media)
        3 / 2,  # DSLR default
        2 / 3,  # Portrait DSLR
    ]

    min_diff = min(abs(aspect - std) for std in standard_aspects)
    result["aspect_ratio_deviation"] = min_diff

    # Very unusual aspect ratio might indicate cropping
    if min_diff > 0.15:
        result["signals"].append("unusual_aspect_ratio")

    # Check for suspiciously round numbers (often means manual resize)
    if img.width % 100 == 0 and img.height % 100 == 0:
        # Round hundreds are suspicious unless common resolution
        common_sizes = [
            (1920, 1080),
            (1080, 1920),
            (1280, 720),
            (720, 1280),
            (3840, 2160),
            (2160, 3840),
            (1200, 1200),
            (1000, 1000),
            (800, 800),
            (600, 600),
        ]
        if (img.width, img.height) not in common_sizes:
            result["signals"].append("suspiciously_round_dimensions")

    # Very small images are suspicious for verification
    if img.width < 640 or img.height < 480:
        result["signals"].append("resolution_too_low")

    # Check for typical screenshot dimensions without camera metadata
    screenshot_sizes = [
        (1170, 2532),
        (2532, 1170),  # iPhone
        (1284, 2778),
        (2778, 1284),  # iPhone Pro Max
        (1179, 2556),
        (2556, 1179),  # iPhone 14 Pro
        (1290, 2796),
        (2796, 1290),  # iPhone 14 Pro Max
        (1080, 2400),
        (2400, 1080),  # Common Android
        (1440, 3200),
        (3200, 1440),  # Samsung
    ]

    if (img.width, img.height) in screenshot_sizes:
        if not exif_data.get("Make") and not exif_data.get("Model"):
            result["signals"].append("screenshot_dimensions_no_camera_data")

    return result


def _check_metadata_consistency(exif_data: dict, img: Image.Image) -> dict:
    """
    Check for metadata inconsistencies that indicate tampering.

    Checks:
    - Missing expected fields
    - Inconsistent timestamps
    - GPS/timestamp mismatches
    - Suspicious UserComment fields
    """
    result = {
        "signals": [],
        "has_camera_info": bool(exif_data.get("Make") or exif_data.get("Model")),
        "has_timestamp": bool(exif_data.get("DateTimeOriginal")),
        "has_gps": bool(exif_data.get("GPSLatitude")),
    }

    # Check for stripped metadata (common in edited images)
    if img.format == "JPEG" and not exif_data:
        result["signals"].append("no_exif_data_in_jpeg")

    # Camera info without timestamp is suspicious
    if result["has_camera_info"] and not result["has_timestamp"]:
        result["signals"].append("camera_info_but_no_timestamp")

    # Check for timestamp inconsistencies
    datetime_original = exif_data.get("DateTimeOriginal")
    datetime_digitized = exif_data.get("DateTimeDigitized")
    datetime_modified = exif_data.get("DateTime")

    timestamps = {
        "original": datetime_original,
        "digitized": datetime_digitized,
        "modified": datetime_modified,
    }
    result["timestamps"] = timestamps

    # Original should equal digitized for camera photos
    if datetime_original and datetime_digitized:
        if str(datetime_original) != str(datetime_digitized):
            result["signals"].append("timestamp_original_digitized_mismatch")

    # Modified after original indicates editing
    if datetime_original and datetime_modified:
        if str(datetime_original) != str(datetime_modified):
            result["signals"].append("modification_timestamp_differs")

    # Check UserComment for suspicious content
    user_comment = str(exif_data.get("UserComment", ""))
    if user_comment:
        result["user_comment"] = user_comment[:200]
        suspicious_comments = [
            "edited",
            "modified",
            "cropped",
            "resized",
            "filtered",
            "screenshot",
            "saved from",
            "downloaded",
            "imported",
        ]
        for word in suspicious_comments:
            if word in user_comment.lower():
                result["signals"].append(f"suspicious_user_comment:{word}")
                break

    # Check for thumbnail inconsistency
    if "1st" in str(exif_data.keys()):
        # Has thumbnail - check if dimensions match (roughly)
        thumb_width = exif_data.get("ThumbnailWidth") or exif_data.get("1st", {}).get(
            256
        )
        if thumb_width:
            result["has_thumbnail"] = True
            # Thumbnail dimension ratio should match image ratio
            # (Not implementing full check here - would need to extract thumbnail)

    # Check MakerNote (camera-specific data)
    if exif_data.get("MakerNote"):
        result["has_maker_note"] = True
    else:
        # Missing MakerNote on photos claiming to be from certain cameras
        make = str(exif_data.get("Make", "")).lower()
        if make in ["apple", "samsung", "google", "sony", "canon", "nikon"]:
            if result["has_camera_info"]:
                result["signals"].append("missing_makernote_from_known_brand")

    # Check for XMP data indicating editing
    xmp_toolkit = exif_data.get("XMPToolkit", "")
    if xmp_toolkit and "photoshop" in str(xmp_toolkit).lower():
        result["signals"].append("xmp_indicates_photoshop")

    return result


def _calculate_confidence(signals: list[str], details: dict) -> float:
    """
    Calculate overall tampering confidence score.

    Returns a value from 0.0 (definitely not tampered) to 1.0 (definitely tampered).
    """
    if not signals:
        return 0.0

    # Weight different signal types
    weights = {
        # High weight - strong indicators
        "professional_editor_detected": 0.8,
        "ai_manipulation": 0.9,
        "ai_generated": 0.95,
        "ela_anomaly_detected": 0.7,
        "double_compression_suspected": 0.6,
        "exif_dimension_mismatch": 0.7,
        # Medium weight
        "mobile_editor": 0.5,
        "face_editor": 0.6,
        "social_media_resave": 0.4,
        "screenshot_tool": 0.8,
        "screenshot_dimensions_no_camera_data": 0.7,
        "modification_timestamp_differs": 0.5,
        "timestamp_original_digitized_mismatch": 0.6,
        "no_exif_data_in_jpeg": 0.5,
        "missing_makernote_from_known_brand": 0.4,
        "unusual_aspect_ratio": 0.3,
        # Low weight
        "very_low_jpeg_quality": 0.3,
        "ela_too_uniform_possible_ai": 0.4,
        "suspiciously_round_dimensions": 0.25,
        "resolution_too_low": 0.2,
        "camera_info_but_no_timestamp": 0.3,
        "edited_flag_in_software": 0.6,
        "image_history_shows_edits": 0.5,
        "xmp_indicates_photoshop": 0.7,
        # Very low weight - circumstantial
        "suspicious_user_comment": 0.2,
        "history_software_agent_present": 0.3,
    }

    # Calculate weighted score
    total_weight = 0.0
    for signal in signals:
        # Handle signals with suffixes (e.g., "professional_editor_detected:photoshop")
        signal_base = signal.split(":")[0]

        # Find matching weight
        matched_weight = 0.2  # Default weight for unknown signals
        for key, weight in weights.items():
            if key in signal_base or signal_base in key:
                matched_weight = max(matched_weight, weight)
                break

        total_weight += matched_weight

    # Normalize - more signals increase confidence
    # But cap at 1.0
    confidence = min(1.0, total_weight / 2.0)

    # Boost if ELA analysis found issues
    ela = details.get("ela_analysis", {})
    if ela.get("suspicious_pixel_ratio", 0) > 0.1:
        confidence = min(1.0, confidence + 0.15)

    # Boost if compression analysis found issues
    compression = details.get("compression_analysis", {})
    if compression.get("double_compression_suspected"):
        confidence = min(1.0, confidence + 0.1)

    return round(confidence, 3)
