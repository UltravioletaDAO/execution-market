"""
Generative AI Image Detection

Detects AI-generated images (Midjourney, DALL-E, Stable Diffusion, Flux, etc.)
using multiple detection methods:
1. C2PA metadata check (Content Authenticity Initiative)
2. Steganographic AI watermark detection
3. AI artifact analysis
4. EXIF anomalies for AI
5. Statistical analysis
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from PIL import Image
from PIL.ExifTags import TAGS
import re


@dataclass
class GenAIResult:
    """Result of AI-generated image detection."""

    is_ai_generated: bool
    confidence: float  # 0.0 to 1.0 (how likely AI-generated)
    model_hint: Optional[str]  # Detected AI model (e.g., "midjourney", "dall-e")
    signals: List[str]  # List of detected signals
    details: Dict[str, Any]  # Detailed findings
    reason: Optional[str]  # Human-readable explanation

    @property
    def normalized_score(self) -> float:
        """Normalized score 0.0-1.0 where 1.0 = not AI-generated (passed).

        Inverts confidence: low AI confidence -> high score (good).
        A real photo (confidence=0) scores 1.0,
        a confirmed AI image (confidence=1) scores 0.0.
        """
        return round(1.0 - self.confidence, 4)


# Known AI generator signatures
AI_SIGNATURES = {
    "midjourney": {
        "software_patterns": [
            r"midjourney",
            r"mj\s*v[0-9]",
        ],
        "metadata_keys": ["midjourney"],
        "watermark_patterns": [],  # Midjourney doesn't use steganographic watermarks
    },
    "dall-e": {
        "software_patterns": [
            r"dall[\-\s]?e",
            r"openai",
        ],
        "metadata_keys": ["openai", "dall-e", "dalle"],
        "watermark_patterns": [],  # DALL-E uses C2PA
    },
    "stable_diffusion": {
        "software_patterns": [
            r"stable[\-\s]?diffusion",
            r"automatic1111",
            r"a1111",
            r"comfyui",
            r"invoke[\-\s]?ai",
            r"fooocus",
        ],
        "metadata_keys": ["sd", "stable diffusion", "automatic1111", "comfyui"],
        "watermark_patterns": [],
    },
    "flux": {
        "software_patterns": [
            r"flux",
            r"black[\-\s]?forest[\-\s]?labs",
        ],
        "metadata_keys": ["flux", "bfl"],
        "watermark_patterns": [],
    },
    "firefly": {
        "software_patterns": [
            r"firefly",
            r"adobe[\-\s]?firefly",
        ],
        "metadata_keys": ["firefly", "adobe firefly"],
        "watermark_patterns": [],  # Firefly uses C2PA
    },
    "imagen": {
        "software_patterns": [
            r"imagen",
            r"google[\-\s]?imagen",
        ],
        "metadata_keys": ["imagen", "google imagen"],
        "watermark_patterns": [],
    },
}

# C2PA (Content Authenticity Initiative) markers
C2PA_MARKERS = {
    "jumbf_box_type": b"jumb",  # JUMBF box type
    "c2pa_manifest": b"c2pa",  # C2PA manifest marker
    "c2pa_claim": b"c2cl",  # C2PA claim marker
    "xmp_c2pa": "c2pa:",  # XMP namespace for C2PA
    "ai_generated_claim": "c2pa.ai_generated",
}

# SynthID watermark detection (Google's steganographic watermark)
SYNTHID_PATTERNS = {
    "frequency_domain": True,  # SynthID operates in frequency domain
    "detection_method": "dct_analysis",  # Discrete Cosine Transform
}


def _has_real_camera_exif(img: Image.Image) -> bool:
    """Return True if image EXIF contains real camera Make/Model data.

    Used to suppress false positives on photos from real cameras (iPhone,
    Android, DSLR) where computational photography pipelines produce
    JPEG artifacts that mimic AI-generation signals.
    """
    try:
        exif_raw = img._getexif()
        if not exif_raw:
            return False
        for tag_id, value in exif_raw.items():
            tag = TAGS.get(tag_id, "")
            if tag in ("Make", "Model") and value and str(value).strip():
                return True
    except Exception:
        pass
    return False


def check_genai(image_path: str) -> GenAIResult:
    """
    Main function to detect if an image is AI-generated.

    Args:
        image_path: Path to the image file

    Returns:
        GenAIResult with detection findings
    """
    signals = []
    details = {}
    model_hint = None
    confidence = 0.0

    try:
        img = Image.open(image_path)

        # Read raw bytes for binary analysis
        with open(image_path, "rb") as f:
            raw_bytes = f.read()

        # Detect real camera EXIF to suppress false positives from
        # computational photography pipelines (Apple, Google, Samsung).
        has_camera_exif = _has_real_camera_exif(img)

        # 1. C2PA metadata check
        c2pa_result = _check_c2pa_metadata(raw_bytes, img)
        if c2pa_result["detected"]:
            signals.append("c2pa_ai_metadata")
            details["c2pa"] = c2pa_result
            confidence += 0.4  # Strong signal
            if c2pa_result.get("generator"):
                model_hint = c2pa_result["generator"]

        # 2. Steganographic watermark detection
        watermark_result = _check_steganographic_watermarks(img, raw_bytes)
        if watermark_result["detected"]:
            # qt_watermark is a known false positive for iPhone/Android photos:
            # Apple's optimized JPEG quantization tables have qt_variance < 20
            # due to their computational photography pipeline, not AI generation.
            wm_type = watermark_result.get("type", "")
            if has_camera_exif and wm_type == "qt_watermark":
                pass  # Suppress: camera EXIF present, QT artifact is not an AI signal
            else:
                signals.append("ai_watermark_detected")
                details["watermark"] = watermark_result
                confidence += 0.35
                if watermark_result.get("type"):
                    model_hint = model_hint or watermark_result["type"]

        # 3. AI artifact analysis
        artifact_result = _check_ai_artifacts(img)
        if artifact_result["detected"]:
            signals.append("ai_artifacts_found")
            details["artifacts"] = artifact_result
            confidence += 0.15

        # 4. EXIF anomalies for AI
        exif_result = _check_exif_anomalies(img, raw_bytes)
        if exif_result["detected"]:
            signals.append("ai_exif_anomalies")
            details["exif"] = exif_result
            confidence += 0.25
            if exif_result.get("generator"):
                model_hint = model_hint or exif_result["generator"]

        # 5. Statistical analysis
        stats_result = _check_statistical_patterns(img)
        if stats_result["detected"]:
            signals.append("ai_statistical_patterns")
            details["statistics"] = stats_result
            confidence += 0.1

        # Normalize confidence to max 1.0
        confidence = min(confidence, 1.0)

        # Determine if AI-generated
        is_ai_generated = confidence >= 0.50 and len(signals) >= 2

        # Generate reason
        if is_ai_generated:
            if model_hint:
                reason = f"Image appears to be AI-generated (likely {model_hint}). Detected signals: {', '.join(signals)}"
            else:
                reason = f"Image appears to be AI-generated. Detected signals: {', '.join(signals)}"
        else:
            reason = "No strong indicators of AI generation detected."

        return GenAIResult(
            is_ai_generated=is_ai_generated,
            confidence=round(confidence, 3),
            model_hint=model_hint,
            signals=signals,
            details=details,
            reason=reason,
        )

    except Exception as e:
        return GenAIResult(
            is_ai_generated=False,
            confidence=0.0,
            model_hint=None,
            signals=[],
            details={"error": str(e)},
            reason=f"Failed to analyze image: {str(e)}",
        )


def _check_c2pa_metadata(raw_bytes: bytes, img: Image.Image) -> Dict[str, Any]:
    """
    Check for C2PA (Content Authenticity Initiative) metadata.

    C2PA is used by Adobe Firefly, DALL-E 3, and other major AI tools
    to embed provenance information including AI generation claims.
    """
    result = {
        "detected": False,
        "has_jumbf": False,
        "has_c2pa_manifest": False,
        "ai_generated_claim": False,
        "generator": None,
        "claims": [],
    }

    # Check for JUMBF box (JPEG/PNG)
    if C2PA_MARKERS["jumbf_box_type"] in raw_bytes:
        result["has_jumbf"] = True

    # Check for C2PA manifest marker
    if C2PA_MARKERS["c2pa_manifest"] in raw_bytes:
        result["has_c2pa_manifest"] = True

    # Check for C2PA claim marker
    if C2PA_MARKERS["c2pa_claim"] in raw_bytes:
        result["detected"] = True

        # Try to extract claim information
        try:
            claim_idx = raw_bytes.find(C2PA_MARKERS["c2pa_claim"])
            # Look for AI-related claims in nearby bytes
            context = raw_bytes[
                max(0, claim_idx - 500) : min(len(raw_bytes), claim_idx + 500)
            ]
            context_str = context.decode("utf-8", errors="ignore").lower()

            if "ai_generated" in context_str or "generative" in context_str:
                result["ai_generated_claim"] = True

            # Try to identify generator
            for gen_name, patterns in AI_SIGNATURES.items():
                for pattern in patterns["software_patterns"]:
                    if re.search(pattern, context_str, re.IGNORECASE):
                        result["generator"] = gen_name
                        break
        except Exception:
            pass

    # Check XMP metadata for C2PA namespace
    try:
        xmp_data = _extract_xmp(raw_bytes)
        if xmp_data and C2PA_MARKERS["xmp_c2pa"] in xmp_data:
            result["detected"] = True

            # Check for AI generation assertions
            if "ai_generated" in xmp_data.lower():
                result["ai_generated_claim"] = True

            # Check for known generators in XMP
            xmp_lower = xmp_data.lower()
            for gen_name, patterns in AI_SIGNATURES.items():
                for key in patterns["metadata_keys"]:
                    if key in xmp_lower:
                        result["generator"] = gen_name
                        break
    except Exception:
        pass

    return result


def _extract_xmp(raw_bytes: bytes) -> Optional[str]:
    """Extract XMP metadata from image bytes."""
    # Look for XMP packet
    xmp_start = raw_bytes.find(b"<?xpacket begin")
    if xmp_start == -1:
        xmp_start = raw_bytes.find(b"<x:xmpmeta")

    if xmp_start == -1:
        return None

    xmp_end = raw_bytes.find(b"<?xpacket end", xmp_start)
    if xmp_end == -1:
        xmp_end = raw_bytes.find(b"</x:xmpmeta>", xmp_start)
        if xmp_end != -1:
            xmp_end += len(b"</x:xmpmeta>")
    else:
        xmp_end = raw_bytes.find(b"?>", xmp_end) + 2

    if xmp_end > xmp_start:
        return raw_bytes[xmp_start:xmp_end].decode("utf-8", errors="ignore")

    return None


def _check_steganographic_watermarks(
    img: Image.Image, raw_bytes: bytes
) -> Dict[str, Any]:
    """
    Detect steganographic AI watermarks.

    Methods:
    - SynthID detection (Google) - frequency domain analysis
    - LSB pattern analysis for known AI watermarks
    - DCT coefficient analysis
    """
    result = {
        "detected": False,
        "type": None,
        "confidence": 0.0,
        "method": None,
    }

    try:
        # Convert to RGB if needed
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 1. Check for SynthID-like patterns (simplified heuristic)
        synthid_score = _analyze_synthid_patterns(img)
        if synthid_score > 0.6:
            result["detected"] = True
            result["type"] = "synthid"
            result["confidence"] = synthid_score
            result["method"] = "frequency_analysis"
            return result

        # 2. LSB watermark detection
        lsb_result = _analyze_lsb_patterns(img)
        if lsb_result["suspicious"]:
            result["detected"] = True
            result["type"] = "lsb_watermark"
            result["confidence"] = lsb_result["confidence"]
            result["method"] = "lsb_analysis"
            return result

        # 3. Check for hidden watermark in JPEG quantization tables
        if img.format == "JPEG" or raw_bytes[:2] == b"\xff\xd8":
            qt_result = _analyze_quantization_tables(raw_bytes)
            if qt_result["suspicious"]:
                result["detected"] = True
                result["type"] = "qt_watermark"
                result["confidence"] = qt_result["confidence"]
                result["method"] = "quantization_analysis"
                return result

    except Exception:
        pass

    return result


def _analyze_synthid_patterns(img: Image.Image) -> float:
    """
    Analyze for SynthID-like watermark patterns.

    SynthID embeds watermarks in the frequency domain that are
    imperceptible but statistically detectable.

    This is a simplified heuristic - real SynthID detection
    requires the trained detector model.
    """
    try:
        # Resize for consistent analysis
        small = img.resize((256, 256), Image.Resampling.LANCZOS)
        pixels = list(small.getdata())

        # Analyze channel correlations
        r_vals = [p[0] for p in pixels]
        g_vals = [p[1] for p in pixels]
        b_vals = [p[2] for p in pixels]

        # Calculate statistical measures
        # SynthID creates subtle correlations between channels
        # that differ from natural images

        # Mean absolute difference between consecutive pixels
        def channel_smoothness(vals):
            diffs = [abs(vals[i] - vals[i - 1]) for i in range(1, len(vals))]
            return sum(diffs) / len(diffs)

        r_smooth = channel_smoothness(r_vals)
        g_smooth = channel_smoothness(g_vals)
        b_smooth = channel_smoothness(b_vals)

        # AI images often have unnaturally consistent smoothness across channels
        smoothness_variance = max(r_smooth, g_smooth, b_smooth) - min(
            r_smooth, g_smooth, b_smooth
        )

        # Very low variance might indicate AI generation
        if smoothness_variance < 2.0:
            return 0.4
        elif smoothness_variance < 5.0:
            return 0.2

        return 0.0

    except Exception:
        return 0.0


def _analyze_lsb_patterns(img: Image.Image) -> Dict[str, Any]:
    """Analyze least significant bit patterns for watermarks."""
    result = {"suspicious": False, "confidence": 0.0}

    try:
        # Sample pixels
        small = img.resize((128, 128), Image.Resampling.NEAREST)
        pixels = list(small.getdata())

        # Extract LSB from each channel
        lsb_r = [p[0] & 1 for p in pixels]
        lsb_g = [p[1] & 1 for p in pixels]
        lsb_b = [p[2] & 1 for p in pixels]

        # In natural images, LSB should be ~50% 0s and ~50% 1s
        # Watermarks may create patterns

        def bit_ratio(bits):
            return sum(bits) / len(bits)

        r_ratio = bit_ratio(lsb_r)
        g_ratio = bit_ratio(lsb_g)
        b_ratio = bit_ratio(lsb_b)

        # Check for unusual patterns
        # Very biased ratios might indicate watermarking
        bias_threshold = 0.15  # Deviation from 0.5

        if (
            abs(r_ratio - 0.5) > bias_threshold
            or abs(g_ratio - 0.5) > bias_threshold
            or abs(b_ratio - 0.5) > bias_threshold
        ):
            result["suspicious"] = True
            result["confidence"] = 0.4

        # Check for correlations between channels (watermark signature)
        # Matching patterns across channels might indicate embedded data
        matches = sum(1 for i in range(len(lsb_r)) if lsb_r[i] == lsb_g[i] == lsb_b[i])
        match_ratio = matches / len(lsb_r)

        # Unusually high correlation might indicate watermark
        if match_ratio > 0.6:
            result["suspicious"] = True
            result["confidence"] = max(result["confidence"], 0.5)

    except Exception:
        pass

    return result


def _analyze_quantization_tables(raw_bytes: bytes) -> Dict[str, Any]:
    """Analyze JPEG quantization tables for AI signatures."""
    result = {"suspicious": False, "confidence": 0.0}

    try:
        # Find DQT marker (0xFF, 0xDB)
        dqt_positions = []
        for i in range(len(raw_bytes) - 1):
            if raw_bytes[i] == 0xFF and raw_bytes[i + 1] == 0xDB:
                dqt_positions.append(i)

        if not dqt_positions:
            return result

        # Analyze quantization table values
        # AI-generated JPEGs may have unusual QT values
        for pos in dqt_positions:
            if pos + 69 > len(raw_bytes):
                continue

            # Skip marker and length
            qt_data = raw_bytes[pos + 4 : pos + 68]

            # Check for known AI generator QT patterns
            # (This would need calibration with real AI image samples)

            # Heuristic: Very uniform QT values are suspicious
            qt_variance = max(qt_data) - min(qt_data)
            if qt_variance < 20:
                result["suspicious"] = True
                result["confidence"] = 0.3
                break

    except Exception:
        pass

    return result


def _check_ai_artifacts(img: Image.Image) -> Dict[str, Any]:
    """
    Check for visual artifacts common in AI-generated images.

    Common AI artifacts:
    - Unusual gradients
    - Texture inconsistencies
    - Edge anomalies
    - Pattern repetition
    """
    result = {
        "detected": False,
        "artifacts": [],
        "confidence": 0.0,
    }

    try:
        # Convert to RGB if needed
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 1. Check for unusual color distributions
        color_result = _analyze_color_distribution(img)
        if color_result["unusual"]:
            result["artifacts"].append("unusual_color_distribution")
            result["confidence"] += 0.15

        # 2. Check for texture consistency
        texture_result = _analyze_texture_consistency(img)
        if texture_result["too_consistent"]:
            result["artifacts"].append("overly_consistent_texture")
            result["confidence"] += 0.1

        # 3. Check for repeating patterns
        pattern_result = _analyze_pattern_repetition(img)
        if pattern_result["repetition_detected"]:
            result["artifacts"].append("pattern_repetition")
            result["confidence"] += 0.1

        result["detected"] = len(result["artifacts"]) > 0

    except Exception:
        pass

    return result


def _analyze_color_distribution(img: Image.Image) -> Dict[str, Any]:
    """Analyze color distribution for AI-like patterns."""
    result = {"unusual": False}

    try:
        # Get histogram
        histogram = img.histogram()

        # Split into RGB channels (assuming RGB mode)
        r_hist = histogram[0:256]
        g_hist = histogram[256:512]
        b_hist = histogram[512:768]

        # AI images often have smoother histograms
        def histogram_smoothness(hist):
            diffs = [abs(hist[i] - hist[i - 1]) for i in range(1, len(hist))]
            return sum(diffs) / sum(hist) if sum(hist) > 0 else 0

        r_smooth = histogram_smoothness(r_hist)
        g_smooth = histogram_smoothness(g_hist)
        b_smooth = histogram_smoothness(b_hist)

        avg_smoothness = (r_smooth + g_smooth + b_smooth) / 3

        # Very smooth histograms might indicate AI generation
        if avg_smoothness < 0.5:
            result["unusual"] = True
            result["smoothness"] = avg_smoothness

    except Exception:
        pass

    return result


def _analyze_texture_consistency(img: Image.Image) -> Dict[str, Any]:
    """Check if texture is unnaturally consistent (common in AI images)."""
    result = {"too_consistent": False}

    try:
        # Analyze local variance in different regions
        width, height = img.size
        block_size = min(64, width // 4, height // 4)

        if block_size < 16:
            return result

        variances = []
        for y in range(0, height - block_size, block_size):
            for x in range(0, width - block_size, block_size):
                block = img.crop((x, y, x + block_size, y + block_size))
                block_pixels = list(block.getdata())

                # Calculate variance for this block
                r_vals = [p[0] for p in block_pixels]
                variance = sum(
                    (v - sum(r_vals) / len(r_vals)) ** 2 for v in r_vals
                ) / len(r_vals)
                variances.append(variance)

        if not variances:
            return result

        # Check variance of variances
        # AI images tend to have more uniform local variance
        mean_var = sum(variances) / len(variances)
        var_of_var = sum((v - mean_var) ** 2 for v in variances) / len(variances)

        # Very low variance of variances might indicate AI
        if var_of_var < 100 and mean_var > 100:
            result["too_consistent"] = True
            result["variance_metric"] = var_of_var

    except Exception:
        pass

    return result


def _analyze_pattern_repetition(img: Image.Image) -> Dict[str, Any]:
    """Check for repeating patterns (common AI artifact)."""
    result = {"repetition_detected": False}

    try:
        # Resize for faster analysis
        small = img.resize((128, 128), Image.Resampling.LANCZOS)
        pixels = list(small.getdata())

        # Look for repeated pixel sequences
        # (simplified - real implementation would use autocorrelation)

        # Check rows for repetition
        width = 128
        repetition_count = 0

        for row_start in range(0, len(pixels), width):
            row = pixels[row_start : row_start + width]
            # Check if any pattern repeats
            for pattern_len in range(4, width // 4):
                pattern = row[:pattern_len]
                repetitions = 0
                for i in range(0, len(row) - pattern_len, pattern_len):
                    segment = row[i : i + pattern_len]
                    if all(
                        abs(a[0] - b[0]) < 10
                        and abs(a[1] - b[1]) < 10
                        and abs(a[2] - b[2]) < 10
                        for a, b in zip(pattern, segment)
                    ):
                        repetitions += 1
                if repetitions > 2:
                    repetition_count += 1
                    break

        # If many rows have repetition, it's suspicious
        if repetition_count > 10:
            result["repetition_detected"] = True
            result["repetition_count"] = repetition_count

    except Exception:
        pass

    return result


def _check_exif_anomalies(img: Image.Image, raw_bytes: bytes) -> Dict[str, Any]:
    """
    Check EXIF metadata for AI generation indicators.

    AI-generated images often have:
    - No camera make/model
    - Specific software signatures
    - Missing or invalid GPS data
    - Unusual timestamps
    """
    result = {
        "detected": False,
        "generator": None,
        "anomalies": [],
    }

    try:
        # Get EXIF data
        exif_data = {}
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

        # Check software field for AI signatures
        software = str(exif_data.get("Software", "")).lower()

        for gen_name, patterns in AI_SIGNATURES.items():
            for pattern in patterns["software_patterns"]:
                if re.search(pattern, software, re.IGNORECASE):
                    result["detected"] = True
                    result["generator"] = gen_name
                    result["anomalies"].append(f"software_signature_{gen_name}")
                    return result

        # Check for AI-related keywords in any text field
        text_fields = [
            "Software",
            "Artist",
            "Copyright",
            "ImageDescription",
            "UserComment",
            "XPComment",
            "XPAuthor",
            "XPTitle",
        ]

        for field in text_fields:
            value = str(exif_data.get(field, "")).lower()

            # Check for explicit AI indicators
            ai_keywords = [
                "ai generated",
                "ai-generated",
                "artificial intelligence",
                "generated by",
                "created with ai",
                "synthetically generated",
                "machine generated",
                "neural network",
            ]

            for keyword in ai_keywords:
                if keyword in value:
                    result["detected"] = True
                    result["anomalies"].append(f"ai_keyword_{field}")

            # Check for known generator names
            for gen_name, patterns in AI_SIGNATURES.items():
                for key in patterns["metadata_keys"]:
                    if key in value:
                        result["detected"] = True
                        result["generator"] = gen_name
                        result["anomalies"].append(f"generator_{gen_name}_{field}")

        # Check for suspicious missing data
        # Real camera photos typically have Make, Model, and timestamp
        has_camera_data = exif_data.get("Make") or exif_data.get("Model")
        has_timestamp = exif_data.get("DateTimeOriginal") or exif_data.get("DateTime")

        if not has_camera_data and not has_timestamp and len(exif_data) > 0:
            # Has some EXIF but missing typical camera data
            result["anomalies"].append("missing_camera_metadata")

        # Also check XMP for AI indicators
        xmp_data = _extract_xmp(raw_bytes)
        if xmp_data:
            xmp_lower = xmp_data.lower()

            # Check for AI-related namespaces and tags
            ai_xmp_indicators = [
                "ai:generated",
                "ai_generated",
                "aimodel",
                "generativeai",
                "synthetic",
            ]

            for indicator in ai_xmp_indicators:
                if indicator in xmp_lower:
                    result["detected"] = True
                    result["anomalies"].append(f"xmp_{indicator}")

            # Check for known generators in XMP
            for gen_name, patterns in AI_SIGNATURES.items():
                for key in patterns["metadata_keys"]:
                    if key in xmp_lower:
                        result["detected"] = True
                        result["generator"] = gen_name
                        result["anomalies"].append(f"xmp_generator_{gen_name}")

    except Exception:
        pass

    return result


def _check_statistical_patterns(img: Image.Image) -> Dict[str, Any]:
    """
    Perform statistical analysis to detect AI generation patterns.

    AI images often have different statistical properties:
    - Different noise patterns
    - Unusual frequency distributions
    - Different entropy characteristics
    """
    result = {
        "detected": False,
        "patterns": [],
        "confidence": 0.0,
    }

    try:
        # Convert to RGB if needed
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 1. Analyze image entropy
        entropy_result = _analyze_entropy(img)
        if entropy_result["unusual"]:
            result["patterns"].append("unusual_entropy")
            result["confidence"] += 0.1

        # 2. Analyze noise patterns
        noise_result = _analyze_noise_patterns(img)
        if noise_result["synthetic"]:
            result["patterns"].append("synthetic_noise")
            result["confidence"] += 0.1

        # 3. Analyze edge sharpness consistency
        edge_result = _analyze_edge_consistency(img)
        if edge_result["too_consistent"]:
            result["patterns"].append("consistent_edges")
            result["confidence"] += 0.1

        result["detected"] = len(result["patterns"]) > 0

    except Exception:
        pass

    return result


def _analyze_entropy(img: Image.Image) -> Dict[str, Any]:
    """Analyze image entropy for AI patterns."""
    result = {"unusual": False}

    try:
        # Calculate histogram-based entropy
        histogram = img.histogram()
        total = sum(histogram)

        if total == 0:
            return result

        entropy = 0
        for count in histogram:
            if count > 0:
                prob = count / total
                entropy -= prob * (
                    prob if prob > 0 else 1
                )  # Simplified log approximation

        # AI images often have different entropy characteristics
        # (This would need calibration with real data)
        # Very low or very high entropy might indicate AI

        # Normalize entropy
        max_entropy = len(histogram)  # Theoretical max
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

        result["entropy"] = normalized_entropy

        # Heuristic thresholds (would need tuning)
        if normalized_entropy < 0.001 or normalized_entropy > 0.5:
            result["unusual"] = True

    except Exception:
        pass

    return result


def _analyze_noise_patterns(img: Image.Image) -> Dict[str, Any]:
    """Analyze noise patterns for synthetic characteristics."""
    result = {"synthetic": False}

    try:
        # Sample high-frequency components (noise)
        small = img.resize((64, 64), Image.Resampling.LANCZOS)
        pixels = list(small.getdata())

        # Calculate local noise (difference from neighbors)
        width = 64
        noise_values = []

        for i in range(width, len(pixels) - width):
            if i % width == 0 or i % width == width - 1:
                continue

            center = pixels[i]
            neighbors = [
                pixels[i - 1],
                pixels[i + 1],
                pixels[i - width],
                pixels[i + width],
            ]

            # Calculate noise as deviation from neighbor average
            avg_r = sum(n[0] for n in neighbors) / 4
            avg_g = sum(n[1] for n in neighbors) / 4
            avg_b = sum(n[2] for n in neighbors) / 4

            noise = (
                abs(center[0] - avg_r) + abs(center[1] - avg_g) + abs(center[2] - avg_b)
            )
            noise_values.append(noise)

        if not noise_values:
            return result

        # AI images often have unnaturally uniform noise
        mean_noise = sum(noise_values) / len(noise_values)
        noise_variance = sum((n - mean_noise) ** 2 for n in noise_values) / len(
            noise_values
        )

        # Very low variance in noise might indicate synthetic
        if noise_variance < 10 and mean_noise > 5:
            result["synthetic"] = True
            result["noise_variance"] = noise_variance

    except Exception:
        pass

    return result


def _analyze_edge_consistency(img: Image.Image) -> Dict[str, Any]:
    """Analyze edge sharpness consistency."""
    result = {"too_consistent": False}

    try:
        # Simple edge detection using pixel differences
        small = img.resize((64, 64), Image.Resampling.LANCZOS)
        pixels = list(small.getdata())
        width = 64

        edge_strengths = []

        for i in range(len(pixels) - width - 1):
            if i % width == width - 1:
                continue

            # Horizontal and vertical gradients
            curr = pixels[i]
            right = pixels[i + 1]
            below = pixels[i + width]

            grad_h = (
                abs(curr[0] - right[0])
                + abs(curr[1] - right[1])
                + abs(curr[2] - right[2])
            )
            grad_v = (
                abs(curr[0] - below[0])
                + abs(curr[1] - below[1])
                + abs(curr[2] - below[2])
            )

            edge_strength = (grad_h + grad_v) / 2
            if edge_strength > 20:  # Only count significant edges
                edge_strengths.append(edge_strength)

        if len(edge_strengths) < 10:
            return result

        # Calculate variance of edge strengths
        mean_edge = sum(edge_strengths) / len(edge_strengths)
        edge_variance = sum((e - mean_edge) ** 2 for e in edge_strengths) / len(
            edge_strengths
        )

        # AI images often have unnaturally consistent edge sharpness
        if edge_variance < 100:
            result["too_consistent"] = True
            result["edge_variance"] = edge_variance

    except Exception:
        pass

    return result
