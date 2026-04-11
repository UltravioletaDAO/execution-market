"""
EXIF Metadata Extractor for Evidence Verification

Extracts technical metadata from evidence images BEFORE sending to
vision models. This enriches the PHOTINT prompt with data the model
can cross-reference against visual content.

Uses Pillow (already in deps) + piexif (already in deps).

Part of PHOTINT Verification Overhaul (Phase 3).
"""

import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExifData:
    """Structured EXIF metadata extracted from an image."""

    # Camera info
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None

    # GPS
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_altitude: Optional[float] = None

    # Timestamps
    datetime_original: Optional[str] = None
    datetime_digitized: Optional[str] = None
    datetime_modified: Optional[str] = None

    # Software / editing
    software: Optional[str] = None
    has_editing_software: bool = False

    # Image properties
    orientation: Optional[int] = None
    flash_fired: Optional[bool] = None
    focal_length: Optional[float] = None
    aperture: Optional[float] = None
    iso: Optional[int] = None
    exposure_time: Optional[str] = None

    # File-level
    width: Optional[int] = None
    height: Optional[int] = None
    megapixels: Optional[float] = None
    file_size_bytes: Optional[int] = None
    format: Optional[str] = None  # JPEG, PNG, etc.
    has_exif: bool = False
    container_type: Optional[str] = None  # "EXIF" or "JFIF"

    # Forensic flags
    timestamp_inconsistency: bool = False
    metadata_stripped: bool = False
    editing_indicators: List[str] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Format EXIF data as a text block for prompt injection."""
        lines = []

        # Camera
        if self.camera_make or self.camera_model:
            camera = " ".join(filter(None, [self.camera_make, self.camera_model]))
            lines.append(f"- Camera: {camera}")
        elif not self.has_exif:
            lines.append("- Camera: UNKNOWN (no EXIF metadata)")

        # GPS
        if self.gps_latitude is not None and self.gps_longitude is not None:
            lines.append(f"- GPS: {self.gps_latitude:.6f}, {self.gps_longitude:.6f}")
            if self.gps_altitude is not None:
                lines[-1] += f" (altitude: {self.gps_altitude:.1f}m)"
        else:
            lines.append("- GPS: NOT PRESENT")

        # Timestamps
        if self.datetime_original:
            lines.append(f"- Captured: {self.datetime_original}")
        elif self.datetime_digitized:
            lines.append(f"- Digitized: {self.datetime_digitized}")
        else:
            lines.append("- Capture time: NOT PRESENT")

        if self.datetime_modified and self.datetime_modified != self.datetime_original:
            lines.append(f"- Modified: {self.datetime_modified}")

        # Software
        if self.software:
            flag = " [EDITING SOFTWARE DETECTED]" if self.has_editing_software else ""
            lines.append(f"- Software: {self.software}{flag}")

        # Image properties
        if self.width and self.height:
            mp = self.megapixels or (self.width * self.height / 1_000_000)
            lines.append(f"- Resolution: {self.width}x{self.height} ({mp:.1f} MP)")

        if self.focal_length:
            lines.append(f"- Focal length: {self.focal_length}mm")

        if self.iso:
            lines.append(f"- ISO: {self.iso}")

        # Container
        if self.container_type:
            lines.append(f"- Container: {self.container_type}")

        # EXIF status
        if self.metadata_stripped:
            lines.append("- EXIF Status: STRIPPED (image processed through a platform)")
        elif self.has_exif:
            lines.append("- EXIF Status: Present")
        else:
            lines.append("- EXIF Status: Absent")

        # Forensic flags
        if self.timestamp_inconsistency:
            lines.append("- WARNING: Timestamp inconsistency detected")
        if self.editing_indicators:
            lines.append(
                f"- WARNING: Editing indicators: {', '.join(self.editing_indicators)}"
            )

        return "\n".join(lines)


# Known editing software signatures
_EDITING_SOFTWARE = {
    "photoshop",
    "gimp",
    "snapseed",
    "lightroom",
    "vsco",
    "afterlight",
    "picsart",
    "canva",
    "pixlr",
    "fotor",
    "inshot",
    "facetune",
    "faceapp",
    "remini",
    "beautycam",
    "meitu",
    "b612",
    "snow",
    "airbrush",
    "polish",
}


def extract_exif(file_path: str) -> ExifData:
    """
    Extract EXIF metadata from an image file.

    Uses Pillow for basic metadata and piexif for detailed EXIF.
    Gracefully handles images with no EXIF, corrupted data, or non-JPEG formats.

    Args:
        file_path: Path to the image file.

    Returns:
        ExifData with all extractable metadata.
    """
    data = ExifData()

    try:
        path = Path(file_path)
        if not path.exists():
            logger.warning("EXIF extraction: file not found: %s", file_path)
            return data

        data.file_size_bytes = path.stat().st_size

        # Use Pillow for basic image info
        from PIL import Image

        with Image.open(file_path) as img:
            data.width = img.width
            data.height = img.height
            data.megapixels = round(img.width * img.height / 1_000_000, 1)
            data.format = img.format  # JPEG, PNG, WEBP, etc.

            # Check container type
            if img.format == "JPEG":
                data.container_type = _detect_jpeg_container(file_path)

            # Try Pillow EXIF first
            exif_dict = img.getexif()
            if exif_dict:
                data.has_exif = True
                _parse_pillow_exif(data, exif_dict)

        # Try piexif for more detailed EXIF (JPEG/TIFF only)
        if data.format in ("JPEG", "TIFF"):
            _parse_piexif(data, file_path)

        # Post-processing: detect stripped metadata
        if not data.has_exif and data.format == "JPEG":
            data.metadata_stripped = True

        # Post-processing: check timestamp consistency
        if data.datetime_original and data.datetime_modified:
            data.timestamp_inconsistency = _check_timestamp_inconsistency(
                data.datetime_original, data.datetime_modified
            )

        # Post-processing: check for editing software
        if data.software:
            sw_lower = data.software.lower()
            for editor in _EDITING_SOFTWARE:
                if editor in sw_lower:
                    data.has_editing_software = True
                    data.editing_indicators.append(f"Software: {data.software}")
                    break

        # Post-processing: resolution check (modern phones should be > 2MP)
        if data.megapixels and data.megapixels < 2.0 and data.format == "JPEG":
            data.editing_indicators.append(
                f"Low resolution ({data.megapixels:.1f} MP) — likely processed through messaging platform"
            )

    except Exception as e:
        logger.warning("EXIF extraction failed for %s: %s", file_path, e)

    return data


def extract_exif_from_bytes(image_bytes: bytes, filename: str = "unknown") -> ExifData:
    """Extract EXIF from in-memory image bytes."""
    data = ExifData()

    try:
        data.file_size_bytes = len(image_bytes)

        from PIL import Image

        with Image.open(io.BytesIO(image_bytes)) as img:
            data.width = img.width
            data.height = img.height
            data.megapixels = round(img.width * img.height / 1_000_000, 1)
            data.format = img.format

            exif_dict = img.getexif()
            if exif_dict:
                data.has_exif = True
                _parse_pillow_exif(data, exif_dict)

        # piexif from bytes (JPEG only)
        if data.format == "JPEG":
            try:
                import piexif

                exif_data = piexif.load(image_bytes)
                _apply_piexif_data(data, exif_data)
            except Exception:
                pass

        # Post-processing
        if not data.has_exif and data.format == "JPEG":
            data.metadata_stripped = True

        if data.software:
            sw_lower = data.software.lower()
            for editor in _EDITING_SOFTWARE:
                if editor in sw_lower:
                    data.has_editing_software = True
                    data.editing_indicators.append(f"Software: {data.software}")
                    break

    except Exception as e:
        logger.warning("EXIF extraction from bytes failed (%s): %s", filename, e)

    return data


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def extract_exif_multi(file_paths: List[str]) -> List[ExifData]:
    """
    Extract EXIF metadata from ALL images in a list.

    Unlike extract_exif() which processes a single file, this function
    processes every image and returns a list of ExifData results.
    Useful for multi-image evidence submissions.

    Args:
        file_paths: List of paths to image files.

    Returns:
        List of ExifData, one per file (in the same order).
        Failed extractions return an ExifData with has_exif=False.
    """
    results = []
    for path in file_paths:
        try:
            data = extract_exif(path)
            results.append(data)
        except Exception as e:
            logger.warning("EXIF multi-extraction failed for %s: %s", path, e)
            results.append(ExifData())
    return results


def extract_exif_multi_from_bytes(
    images: List[tuple],
) -> List[ExifData]:
    """
    Extract EXIF from multiple in-memory images.

    Args:
        images: List of (image_bytes, filename) tuples.

    Returns:
        List of ExifData, one per image.
    """
    results = []
    for image_bytes, filename in images:
        try:
            data = extract_exif_from_bytes(image_bytes, filename)
            results.append(data)
        except Exception as e:
            logger.warning(
                "EXIF multi-extraction from bytes failed for %s: %s", filename, e
            )
            results.append(ExifData())
    return results


def merge_exif_to_prompt_context(exif_list: List[ExifData]) -> str:
    """
    Merge multiple EXIF results into a single prompt context string.

    Args:
        exif_list: List of ExifData from extract_exif_multi().

    Returns:
        Combined prompt context with image numbering.
    """
    if not exif_list:
        return "No EXIF data available."

    if len(exif_list) == 1:
        return exif_list[0].to_prompt_context()

    sections = []
    for i, exif in enumerate(exif_list, 1):
        context = exif.to_prompt_context()
        if context:
            sections.append(f"[Image {i}]\n{context}")

    return "\n\n".join(sections) if sections else "No EXIF data available."


def _detect_jpeg_container(file_path: str) -> str:
    """Detect JPEG container type: EXIF or JFIF."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(20)
            if b"Exif" in header:
                return "EXIF"
            elif b"JFIF" in header:
                return "JFIF"
    except Exception:
        pass
    return "UNKNOWN"


def _parse_pillow_exif(data: ExifData, exif_dict) -> None:
    """Parse Pillow EXIF dict into ExifData."""
    for tag_id, value in exif_dict.items():
        try:
            if tag_id == 0x010F:  # Make
                data.camera_make = _clean_string(value)
            elif tag_id == 0x0110:  # Model
                data.camera_model = _clean_string(value)
            elif tag_id == 0x0131:  # Software
                data.software = _clean_string(value)
            elif tag_id == 0x0112:  # Orientation
                data.orientation = int(value) if value else None
            elif tag_id == 0x9003:  # DateTimeOriginal
                data.datetime_original = _clean_string(value)
            elif tag_id == 0x9004:  # DateTimeDigitized
                data.datetime_digitized = _clean_string(value)
            elif tag_id == 0x0132:  # DateTime (modified)
                data.datetime_modified = _clean_string(value)
        except Exception:
            continue


def _parse_piexif(data: ExifData, file_path: str) -> None:
    """Parse EXIF using piexif for detailed metadata."""
    try:
        import piexif

        exif_data = piexif.load(file_path)
        _apply_piexif_data(data, exif_data)
    except Exception as e:
        logger.debug("piexif parsing failed for %s: %s", file_path, e)


def _apply_piexif_data(data: ExifData, exif_data: dict) -> None:
    """Apply piexif parsed data to ExifData."""
    import piexif

    data.has_exif = True

    # 0th IFD
    zeroth = exif_data.get("0th", {})
    if piexif.ImageIFD.Make in zeroth and not data.camera_make:
        data.camera_make = _decode_bytes(zeroth[piexif.ImageIFD.Make])
    if piexif.ImageIFD.Model in zeroth and not data.camera_model:
        data.camera_model = _decode_bytes(zeroth[piexif.ImageIFD.Model])
    if piexif.ImageIFD.Software in zeroth and not data.software:
        data.software = _decode_bytes(zeroth[piexif.ImageIFD.Software])
    if piexif.ImageIFD.Orientation in zeroth and not data.orientation:
        data.orientation = zeroth[piexif.ImageIFD.Orientation]

    # Exif IFD
    exif_ifd = exif_data.get("Exif", {})
    if piexif.ExifIFD.DateTimeOriginal in exif_ifd and not data.datetime_original:
        data.datetime_original = _decode_bytes(
            exif_ifd[piexif.ExifIFD.DateTimeOriginal]
        )
    if piexif.ExifIFD.DateTimeDigitized in exif_ifd and not data.datetime_digitized:
        data.datetime_digitized = _decode_bytes(
            exif_ifd[piexif.ExifIFD.DateTimeDigitized]
        )

    # Focal length
    if piexif.ExifIFD.FocalLength in exif_ifd and not data.focal_length:
        fl = exif_ifd[piexif.ExifIFD.FocalLength]
        if isinstance(fl, tuple) and len(fl) == 2 and fl[1] != 0:
            data.focal_length = round(fl[0] / fl[1], 1)

    # Aperture (FNumber)
    if piexif.ExifIFD.FNumber in exif_ifd and not data.aperture:
        fn = exif_ifd[piexif.ExifIFD.FNumber]
        if isinstance(fn, tuple) and len(fn) == 2 and fn[1] != 0:
            data.aperture = round(fn[0] / fn[1], 1)

    # ISO
    if piexif.ExifIFD.ISOSpeedRatings in exif_ifd and not data.iso:
        iso_val = exif_ifd[piexif.ExifIFD.ISOSpeedRatings]
        data.iso = int(iso_val) if isinstance(iso_val, (int, float)) else None

    # Exposure time
    if piexif.ExifIFD.ExposureTime in exif_ifd and not data.exposure_time:
        et = exif_ifd[piexif.ExifIFD.ExposureTime]
        if isinstance(et, tuple) and len(et) == 2 and et[1] != 0:
            if et[0] < et[1]:
                data.exposure_time = f"{et[0]}/{et[1]}s"
            else:
                data.exposure_time = f"{et[0] / et[1]:.1f}s"

    # Flash
    if piexif.ExifIFD.Flash in exif_ifd and data.flash_fired is None:
        flash_val = exif_ifd[piexif.ExifIFD.Flash]
        if isinstance(flash_val, int):
            data.flash_fired = bool(flash_val & 0x01)

    # GPS IFD
    gps = exif_data.get("GPS", {})
    if gps:
        lat = _parse_gps_coordinate(
            gps.get(piexif.GPSIFD.GPSLatitude),
            gps.get(piexif.GPSIFD.GPSLatitudeRef),
        )
        lng = _parse_gps_coordinate(
            gps.get(piexif.GPSIFD.GPSLongitude),
            gps.get(piexif.GPSIFD.GPSLongitudeRef),
        )
        if lat is not None:
            data.gps_latitude = lat
        if lng is not None:
            data.gps_longitude = lng

        alt = gps.get(piexif.GPSIFD.GPSAltitude)
        if alt and isinstance(alt, tuple) and len(alt) == 2 and alt[1] != 0:
            data.gps_altitude = round(alt[0] / alt[1], 1)
            alt_ref = gps.get(piexif.GPSIFD.GPSAltitudeRef)
            if alt_ref == 1:  # Below sea level
                data.gps_altitude = -data.gps_altitude


def _parse_gps_coordinate(
    coord: Optional[tuple],
    ref: Optional[bytes],
) -> Optional[float]:
    """Parse GPS coordinate from EXIF rational format to decimal degrees."""
    if coord is None or ref is None:
        return None

    try:
        # coord is ((deg_num, deg_den), (min_num, min_den), (sec_num, sec_den))
        if not isinstance(coord, (list, tuple)) or len(coord) != 3:
            return None

        degrees = coord[0][0] / coord[0][1] if coord[0][1] != 0 else 0
        minutes = coord[1][0] / coord[1][1] if coord[1][1] != 0 else 0
        seconds = coord[2][0] / coord[2][1] if coord[2][1] != 0 else 0

        decimal = degrees + minutes / 60 + seconds / 3600

        ref_str = (
            _decode_bytes(ref).upper() if isinstance(ref, bytes) else str(ref).upper()
        )
        if ref_str in ("S", "W"):
            decimal = -decimal

        return round(decimal, 6)
    except Exception:
        return None


def _check_timestamp_inconsistency(original: str, modified: str) -> bool:
    """Check if modification timestamp predates the original."""
    try:
        fmt = "%Y:%m:%d %H:%M:%S"
        dt_orig = datetime.strptime(original.strip(), fmt)
        dt_mod = datetime.strptime(modified.strip(), fmt)
        # Modified before original is suspicious
        return dt_mod < dt_orig
    except (ValueError, AttributeError):
        return False


def _clean_string(value) -> Optional[str]:
    """Clean a string value from EXIF, handling bytes."""
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip().rstrip("\x00")
    return str(value).strip()


def _decode_bytes(value) -> str:
    """Decode bytes to string."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip().rstrip("\x00")
    return str(value).strip()
