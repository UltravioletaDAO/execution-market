"""
Shadow/Lighting Analysis for Evidence Verification

Analyzes image brightness distribution and shadow characteristics
to estimate time of day. Cross-references with claimed submission time.

Uses Pillow for image processing (no OpenCV dependency for basic analysis).

Part of PHOTINT Verification Overhaul (Phase 5).
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LightingResult:
    """Result of lighting/shadow analysis."""

    estimated_time_of_day: Optional[str] = (
        None  # "morning", "midday", "afternoon", "evening", "night", "indoor"
    )
    brightness_mean: float = 0.0  # 0-255
    brightness_std: float = 0.0  # Standard deviation
    contrast_ratio: float = 0.0  # Max/min brightness ratio
    shadow_intensity: Optional[str] = None  # "strong", "moderate", "weak", "none"
    is_consistent_with_time: Optional[bool] = None  # Cross-reference with claimed time
    reason: str = ""


def check_lighting(
    image_path: str,
    claimed_hour: Optional[int] = None,
) -> LightingResult:
    """
    Analyze image lighting to estimate time of day.

    Args:
        image_path: Path to the image file.
        claimed_hour: Hour (0-23) from submission timestamp for cross-reference.

    Returns:
        LightingResult with estimated time and consistency check.
    """
    result = LightingResult()

    try:
        from PIL import Image, ImageStat

        with Image.open(image_path) as img:
            # Convert to grayscale for brightness analysis
            gray = img.convert("L")
            stat = ImageStat.Stat(gray)

            result.brightness_mean = stat.mean[0]
            result.brightness_std = stat.stddev[0]

            # Contrast ratio
            extrema = gray.getextrema()
            if extrema[0] > 0:
                result.contrast_ratio = round(extrema[1] / extrema[0], 2)
            else:
                result.contrast_ratio = float(extrema[1]) if extrema[1] > 0 else 0.0

            # Estimate time of day from brightness
            mean = result.brightness_mean
            std = result.brightness_std

            if mean < 40:
                result.estimated_time_of_day = "night"
                result.shadow_intensity = "none"
            elif mean < 80:
                result.estimated_time_of_day = "evening"
                result.shadow_intensity = "weak"
            elif mean < 120:
                if std > 60:
                    result.estimated_time_of_day = "morning"
                    result.shadow_intensity = "strong"
                else:
                    result.estimated_time_of_day = "indoor"
                    result.shadow_intensity = "weak"
            elif mean < 160:
                if std > 50:
                    result.estimated_time_of_day = "afternoon"
                    result.shadow_intensity = "moderate"
                else:
                    result.estimated_time_of_day = "midday"
                    result.shadow_intensity = "strong"
            else:
                result.estimated_time_of_day = "midday"
                result.shadow_intensity = "strong"

            # Cross-reference with claimed time
            if claimed_hour is not None and result.estimated_time_of_day:
                result.is_consistent_with_time = _check_time_consistency(
                    result.estimated_time_of_day, claimed_hour
                )
                if result.is_consistent_with_time:
                    result.reason = (
                        f"Lighting ({result.estimated_time_of_day}) is consistent "
                        f"with claimed hour ({claimed_hour}:00)"
                    )
                else:
                    result.reason = (
                        f"Lighting suggests {result.estimated_time_of_day} but "
                        f"claimed time is {claimed_hour}:00"
                    )
            else:
                result.reason = f"Estimated: {result.estimated_time_of_day}"

    except Exception as e:
        logger.warning("Lighting analysis failed for %s: %s", image_path, e)
        result.reason = f"Analysis failed: {e}"

    return result


def _check_time_consistency(estimated: str, hour: int) -> bool:
    """Check if estimated time of day is consistent with the claimed hour."""
    time_ranges = {
        "night": list(range(0, 6)) + list(range(20, 24)),
        "morning": list(range(5, 10)),
        "midday": list(range(10, 15)),
        "afternoon": list(range(13, 18)),
        "evening": list(range(16, 21)),
        "indoor": list(range(0, 24)),  # Indoor is always consistent
    }
    valid_hours = time_ranges.get(estimated, list(range(0, 24)))
    return hour in valid_hours
