"""
Photo Source Verification

Ensures photos are from camera (not gallery or screenshot).
Prevents fraud by recycling old photos.
"""

from datetime import datetime, timedelta, UTC
from typing import Optional
from dataclasses import dataclass
from PIL import Image
from PIL.ExifTags import TAGS
import piexif


@dataclass
class PhotoSourceResult:
    """Result of photo source verification."""

    is_valid: bool
    source: str  # "camera" | "gallery" | "screenshot" | "unknown"
    timestamp: Optional[datetime]
    reason: Optional[str]
    details: dict


def check_photo_source(image_path: str, max_age_minutes: int = 5) -> PhotoSourceResult:
    """
    Verify that a photo was taken from camera (not gallery).

    Checks:
    1. EXIF data exists and indicates camera source
    2. Photo is recent (within max_age_minutes)
    3. No indicators of screenshot or editing

    Args:
        image_path: Path to the image file
        max_age_minutes: Maximum age of photo in minutes (default 5)

    Returns:
        PhotoSourceResult with validation details
    """
    try:
        # Load image and EXIF data
        img = Image.open(image_path)
        exif_data = get_exif_data(img)

        # Check for indicators of gallery/screenshot
        source = determine_source(exif_data, img)
        timestamp = extract_timestamp(exif_data)

        # Validate freshness
        if timestamp:
            now = datetime.now(UTC)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)

            age = now - timestamp
            if age > timedelta(minutes=max_age_minutes):
                return PhotoSourceResult(
                    is_valid=False,
                    source=source,
                    timestamp=timestamp,
                    reason=f"Photo too old ({age.total_seconds() / 60:.1f} minutes). Max allowed: {max_age_minutes} minutes.",
                    details={"age_minutes": age.total_seconds() / 60},
                )

        # Check source
        if source in ["gallery", "screenshot"]:
            return PhotoSourceResult(
                is_valid=False,
                source=source,
                timestamp=timestamp,
                reason=f"Photo source is '{source}'. Only live camera photos are accepted.",
                details=exif_data,
            )

        if source == "unknown":
            # Suspicious - no EXIF usually means modified
            return PhotoSourceResult(
                is_valid=False,
                source=source,
                timestamp=timestamp,
                reason="Cannot verify photo source. Missing camera metadata.",
                details={},
            )

        # Valid camera photo
        return PhotoSourceResult(
            is_valid=True,
            source="camera",
            timestamp=timestamp,
            reason=None,
            details={
                "camera_make": exif_data.get("Make"),
                "camera_model": exif_data.get("Model"),
                "software": exif_data.get("Software"),
            },
        )

    except Exception as e:
        return PhotoSourceResult(
            is_valid=False,
            source="error",
            timestamp=None,
            reason=f"Failed to analyze photo: {str(e)}",
            details={},
        )


def get_exif_data(img: Image.Image) -> dict:
    """Extract EXIF data from image."""
    exif_data = {}

    try:
        raw_exif = img._getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, tag_id)
                # Convert bytes to string if possible
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


def determine_source(exif_data: dict, img: Image.Image) -> str:
    """Determine if photo is from camera, gallery, or screenshot."""

    # Check for screenshot indicators
    if is_screenshot(exif_data, img):
        return "screenshot"

    # Check for gallery indicators
    if is_from_gallery(exif_data):
        return "gallery"

    # Check for camera indicators
    if is_from_camera(exif_data):
        return "camera"

    return "unknown"


def is_screenshot(exif_data: dict, img: Image.Image) -> bool:
    """Check if image is a screenshot."""

    # Screenshots typically have:
    # - No camera make/model
    # - Specific dimensions (phone screen sizes)
    # - Software field indicating screenshot tool

    software = str(exif_data.get("Software", "")).lower()
    if any(
        x in software for x in ["screenshot", "snipping", "grab", "capture", "screen"]
    ):
        return True

    # Check for exact phone screen dimensions (common screenshot sizes)
    width, height = img.size
    screenshot_sizes = [
        (1170, 2532),  # iPhone 12/13/14 Pro
        (1284, 2778),  # iPhone 12/13/14 Pro Max
        (1179, 2556),  # iPhone 14 Pro
        (1290, 2796),  # iPhone 14 Pro Max
        (1080, 2400),  # Common Android
        (1080, 2340),  # Common Android
        (1440, 3200),  # Samsung flagship
        (1440, 3088),  # Samsung flagship
        (1080, 1920),  # Standard FHD
        (1920, 1080),  # FHD landscape
    ]

    # Check both orientations
    if (width, height) in screenshot_sizes or (height, width) in screenshot_sizes:
        # If exact screen dimensions AND no camera data, likely screenshot
        if not exif_data.get("Make") and not exif_data.get("Model"):
            return True

    # Check for PNG format (common for screenshots)
    if img.format == "PNG" and not exif_data.get("Make"):
        return True

    return False


def is_from_gallery(exif_data: dict) -> bool:
    """Check if photo was selected from gallery (not fresh capture)."""

    # Check for editing software
    software = str(exif_data.get("Software", "")).lower()
    editing_apps = [
        "photoshop",
        "lightroom",
        "snapseed",
        "vsco",
        "instagram",
        "gimp",
        "pixlr",
        "canva",
        "pics art",
        "picsart",
        "afterlight",
        "facetune",
        "retouch",
        "airbrush",
        "beautycam",
        "snow",
    ]
    if any(app in software for app in editing_apps):
        return True

    # Check for specific gallery indicators in UserComment
    user_comment = str(exif_data.get("UserComment", "")).lower()
    if any(x in user_comment for x in ["gallery", "imported", "edited", "modified"]):
        return True

    # Check ProcessingSoftware tag
    processing = str(exif_data.get("ProcessingSoftware", "")).lower()
    if any(app in processing for app in editing_apps):
        return True

    return False


def is_from_camera(exif_data: dict) -> bool:
    """Check if photo was taken with device camera."""

    # Must have camera make or model
    if not exif_data.get("Make") and not exif_data.get("Model"):
        return False

    # Should have capture timestamp
    has_timestamp = any(
        [
            exif_data.get("DateTimeOriginal"),
            exif_data.get("DateTime"),
            exif_data.get("DateTimeDigitized"),
        ]
    )
    if not has_timestamp:
        return False

    # Known camera/phone manufacturers
    known_makes = [
        "apple",
        "samsung",
        "google",
        "huawei",
        "xiaomi",
        "oppo",
        "oneplus",
        "sony",
        "lg",
        "motorola",
        "nokia",
        "realme",
        "vivo",
        "poco",
        "nothing",
        "asus",
        "pixel",
    ]
    make = str(exif_data.get("Make", "")).lower()
    if any(m in make for m in known_makes):
        return True

    # Has GPS data (strong indicator of camera photo)
    if exif_data.get("GPSLatitude") or exif_data.get("GPSLongitude"):
        return True

    # Default to camera if has basic EXIF with timestamp
    return True


def extract_timestamp(exif_data: dict) -> Optional[datetime]:
    """Extract photo timestamp from EXIF."""

    # Try different timestamp fields in order of preference
    timestamp_fields = [
        "DateTimeOriginal",
        "DateTimeDigitized",
        "DateTime",
        "CreateDate",
    ]

    for field in timestamp_fields:
        value = exif_data.get(field)
        if value:
            try:
                if isinstance(value, bytes):
                    value = value.decode("utf-8")

                # Common EXIF date format: "2026:01:25 10:30:00"
                if ":" in value and " " in value:
                    dt = datetime.strptime(value.strip(), "%Y:%m:%d %H:%M:%S")
                    return dt.replace(tzinfo=UTC)

                # ISO format
                if "T" in value:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))

            except Exception:
                continue

    return None
