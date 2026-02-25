"""
Image Download Utility for Phase B Verification

Downloads evidence images from S3/CloudFront URLs to temporary files
for analysis by AI and image-processing checks.
"""

import logging
import os
import tempfile
from typing import Any, Dict, List, Tuple

import httpx

logger = logging.getLogger(__name__)

# Maximum images to process per submission
MAX_IMAGES = 8


def extract_photo_urls(evidence: Dict[str, Any]) -> List[str]:
    """
    Extract photo URLs from evidence JSONB.

    Walks the evidence dict looking for fileUrl values and direct URL strings
    under known photo keys. Deduplicates and caps at MAX_IMAGES.

    Args:
        evidence: Evidence JSONB dict from submission.

    Returns:
        Deduplicated list of image URLs (max MAX_IMAGES).
    """
    urls: List[str] = []
    seen: set = set()

    photo_keys = {
        "photo",
        "photo_geo",
        "screenshot",
        "document",
        "receipt",
        "video",
        "image",
        "file",
    }

    def _add_url(url: str) -> None:
        if url and url not in seen and len(urls) < MAX_IMAGES:
            seen.add(url)
            urls.append(url)

    def _walk(value: Any, depth: int = 0) -> None:
        if depth > 5:
            return
        if isinstance(value, str) and _looks_like_image_url(value):
            _add_url(value)
        elif isinstance(value, dict):
            # Prioritize fileUrl key
            if "fileUrl" in value:
                file_url = value["fileUrl"]
                if isinstance(file_url, str) and _looks_like_image_url(file_url):
                    _add_url(file_url)
            if "url" in value:
                url_val = value["url"]
                if isinstance(url_val, str) and _looks_like_image_url(url_val):
                    _add_url(url_val)
            for k, v in value.items():
                if k in photo_keys or k == "fileUrl" or k == "url":
                    _walk(v, depth + 1)
                elif isinstance(v, (dict, list)):
                    _walk(v, depth + 1)
        elif isinstance(value, list):
            for item in value:
                _walk(item, depth + 1)

    _walk(evidence)
    return urls


def _looks_like_image_url(s: str) -> bool:
    """Check if a string looks like an image URL."""
    if not s.startswith(("http://", "https://")):
        return False
    lower = s.lower().split("?")[0]
    return lower.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")) or (
        "cloudfront.net" in lower or "s3.amazonaws.com" in lower
    )


async def download_images_to_temp(
    urls: List[str],
    max_images: int = 4,
    timeout: float = 15.0,
) -> List[Tuple[str, str]]:
    """
    Download images to temporary files.

    Args:
        urls: List of image URLs to download.
        max_images: Maximum number of images to download.
        timeout: HTTP timeout per request in seconds.

    Returns:
        List of (temp_file_path, original_url) tuples.
    """
    results: List[Tuple[str, str]] = []

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for url in urls[:max_images]:
            try:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if not content_type.startswith("image/"):
                    logger.warning(
                        "Skipping non-image content-type %s for %s",
                        content_type,
                        url[:80],
                    )
                    continue

                # Determine extension from content-type
                ext = ".jpg"
                if "png" in content_type:
                    ext = ".png"
                elif "webp" in content_type:
                    ext = ".webp"
                elif "gif" in content_type:
                    ext = ".gif"

                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=ext, prefix="em_verify_"
                )
                tmp.write(response.content)
                tmp.close()

                results.append((tmp.name, url))
                logger.debug("Downloaded %s -> %s", url[:60], tmp.name)

            except Exception as e:
                logger.warning("Failed to download image %s: %s", url[:80], e)

    return results


def cleanup_temp_files(paths: List[str]) -> None:
    """Remove temporary files, ignoring errors (e.g. PermissionError on Windows)."""
    for path in paths:
        try:
            os.unlink(path)
        except (OSError, PermissionError):
            pass
