# NOW-065: Gallery upload prohibition

## Metadata
- **Prioridad**: P0
- **Fase**: 5 - Verification
- **Dependencias**: NOW-046
- **Archivos a crear**: `mcp_server/verification/checks/photo_source.py`
- **Tiempo estimado**: 2 horas

## Descripción
SOLO permitir fotos de cámara live, NO de galería. Esto previene el reciclaje de fotos viejas.

## Contexto Técnico
- **Check**: EXIF metadata `source` field
- **Reject if**: Photo from gallery or screenshot
- **Accept if**: Photo from camera within last 5 minutes

## Código de Referencia

### photo_source.py
```python
"""
Photo source verification - ensures photos are from camera, not gallery
"""
import json
from datetime import datetime, timedelta, UTC
from typing import Optional
from dataclasses import dataclass
from PIL import Image
from PIL.ExifTags import TAGS
import piexif


@dataclass
class PhotoSourceResult:
    is_valid: bool
    source: str  # "camera" | "gallery" | "screenshot" | "unknown"
    timestamp: Optional[datetime]
    reason: Optional[str]
    details: dict


def check_photo_source(image_path: str, max_age_minutes: int = 5) -> PhotoSourceResult:
    """
    Verify that a photo was taken from camera (not gallery).

    Args:
        image_path: Path to the image file
        max_age_minutes: Maximum age of photo in minutes

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
            age = datetime.now(UTC) - timestamp
            if age > timedelta(minutes=max_age_minutes):
                return PhotoSourceResult(
                    is_valid=False,
                    source=source,
                    timestamp=timestamp,
                    reason=f"Photo too old ({age.total_seconds() / 60:.1f} minutes). Max allowed: {max_age_minutes} minutes.",
                    details={"age_minutes": age.total_seconds() / 60}
                )

        # Check source
        if source in ["gallery", "screenshot"]:
            return PhotoSourceResult(
                is_valid=False,
                source=source,
                timestamp=timestamp,
                reason=f"Photo source is '{source}'. Only live camera photos are accepted.",
                details=exif_data
            )

        if source == "unknown":
            # Suspicious - no EXIF usually means modified
            return PhotoSourceResult(
                is_valid=False,
                source=source,
                timestamp=timestamp,
                reason="Cannot verify photo source. Missing camera metadata.",
                details={}
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
                "software": exif_data.get("Software")
            }
        )

    except Exception as e:
        return PhotoSourceResult(
            is_valid=False,
            source="error",
            timestamp=None,
            reason=f"Failed to analyze photo: {str(e)}",
            details={}
        )


def get_exif_data(img: Image.Image) -> dict:
    """Extract EXIF data from image"""
    exif_data = {}

    try:
        raw_exif = img._getexif()
        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
    except:
        pass

    # Also try piexif for more detailed data
    try:
        exif_dict = piexif.load(img.info.get("exif", b""))
        for ifd in ("0th", "Exif", "GPS", "1st"):
            if ifd in exif_dict:
                for tag_id, value in exif_dict[ifd].items():
                    tag_name = piexif.TAGS[ifd].get(tag_id, {}).get("name", tag_id)
                    exif_data[tag_name] = value
    except:
        pass

    return exif_data


def determine_source(exif_data: dict, img: Image.Image) -> str:
    """Determine if photo is from camera, gallery, or screenshot"""

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
    """Check if image is a screenshot"""
    # Screenshots typically have:
    # - No camera make/model
    # - Specific dimensions (phone screen sizes)
    # - Software field indicating screenshot tool

    software = str(exif_data.get("Software", "")).lower()
    if any(x in software for x in ["screenshot", "snipping", "grab", "capture"]):
        return True

    # Check for exact phone screen dimensions
    width, height = img.size
    screenshot_sizes = [
        (1170, 2532),  # iPhone 12/13/14 Pro
        (1284, 2778),  # iPhone 12/13/14 Pro Max
        (1080, 2400),  # Common Android
        (1440, 3200),  # Samsung
    ]
    if (width, height) in screenshot_sizes or (height, width) in screenshot_sizes:
        # If no camera data, likely screenshot
        if not exif_data.get("Make") and not exif_data.get("Model"):
            return True

    return False


def is_from_gallery(exif_data: dict) -> bool:
    """Check if photo was selected from gallery (not fresh capture)"""

    # Check for editing software
    software = str(exif_data.get("Software", "")).lower()
    editing_apps = ["photoshop", "lightroom", "snapseed", "vsco", "instagram", "gimp"]
    if any(app in software for app in editing_apps):
        return True

    # Check for specific gallery indicators in UserComment
    user_comment = str(exif_data.get("UserComment", "")).lower()
    if "gallery" in user_comment or "imported" in user_comment:
        return True

    return False


def is_from_camera(exif_data: dict) -> bool:
    """Check if photo was taken with device camera"""

    # Must have camera make or model
    if not exif_data.get("Make") and not exif_data.get("Model"):
        return False

    # Should have capture timestamp
    if not exif_data.get("DateTimeOriginal") and not exif_data.get("DateTime"):
        return False

    # Known camera manufacturers
    known_makes = ["apple", "samsung", "google", "huawei", "xiaomi", "oppo", "oneplus", "sony", "lg"]
    make = str(exif_data.get("Make", "")).lower()
    if any(m in make for m in known_makes):
        return True

    return True  # Default to camera if has basic EXIF


def extract_timestamp(exif_data: dict) -> Optional[datetime]:
    """Extract photo timestamp from EXIF"""

    # Try different timestamp fields
    for field in ["DateTimeOriginal", "DateTime", "DateTimeDigitized"]:
        value = exif_data.get(field)
        if value:
            try:
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                # Common EXIF date format: "2026:01:25 10:30:00"
                dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                return dt.replace(tzinfo=UTC)
            except:
                continue

    return None
```

### Integration with submit_work
```python
# In mcp_server/server.py, modify submit_work handler

from verification.checks.photo_source import check_photo_source

async def submit_work(args: dict):
    # ... existing code ...

    # Validate photo sources
    for photo_url in evidence.get("photos", []):
        # Download to temp file
        temp_path = await download_to_temp(photo_url)

        result = check_photo_source(temp_path, max_age_minutes=5)

        if not result.is_valid:
            return [TextContent(type="text", text=json.dumps({
                "error": f"Photo validation failed: {result.reason}",
                "details": {
                    "source": result.source,
                    "timestamp": result.timestamp.isoformat() if result.timestamp else None
                }
            }))]

    # ... continue with submission ...
```

## Criterios de Éxito
- [ ] Detecta screenshots
- [ ] Detecta gallery photos
- [ ] Acepta camera photos
- [ ] Valida timestamp freshness (< 5 min)
- [ ] Retorna razón clara de rechazo
- [ ] Integrado con submit_work

## Test Cases
```python
def test_camera_photo_accepted():
    result = check_photo_source("tests/fixtures/camera_photo.jpg")
    assert result.is_valid
    assert result.source == "camera"

def test_screenshot_rejected():
    result = check_photo_source("tests/fixtures/screenshot.png")
    assert not result.is_valid
    assert result.source == "screenshot"

def test_old_photo_rejected():
    result = check_photo_source("tests/fixtures/old_photo.jpg", max_age_minutes=5)
    assert not result.is_valid
    assert "too old" in result.reason

def test_no_exif_rejected():
    result = check_photo_source("tests/fixtures/stripped_exif.jpg")
    assert not result.is_valid
    assert result.source == "unknown"
```
