"""
Duplicate Photo Detection

Uses perceptual hashing to detect if a photo was used before.
Prevents reuse of old evidence across tasks.
"""

import hashlib
from dataclasses import dataclass
from typing import Optional, List, Tuple
from PIL import Image
import imagehash


@dataclass
class DuplicateResult:
    """Result of duplicate detection."""

    is_duplicate: bool
    match_id: Optional[str]  # Task/submission ID if duplicate found
    similarity: float  # 0-1, higher = more similar
    phash: str  # Perceptual hash for storage
    reason: Optional[str]

    @property
    def normalized_score(self) -> float:
        """Normalized score 0.0-1.0 where 1.0 = no duplicate found (passed).

        Inverts similarity: a unique image (similarity=0) scores 1.0,
        a perfect duplicate (similarity=1) scores 0.0.
        """
        return round(1.0 - self.similarity, 4)


class DuplicateDetector:
    """
    Detect duplicate photos using perceptual hashing.

    Perceptual hashing allows detecting similar images even if:
    - Resized
    - Slightly cropped
    - Compressed differently
    - Minor edits applied

    This prevents workers from reusing old photos.
    """

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize detector.

        Args:
            similarity_threshold: Similarity score above which images
                                  are considered duplicates (0-1)
        """
        self.threshold = similarity_threshold

    def compute_hash(self, image_path: str) -> Tuple[str, str, str]:
        """
        Compute multiple perceptual hashes for an image.

        Uses multiple hash types for better accuracy:
        - phash: DCT-based, good for general similarity
        - dhash: Gradient-based, good for resized images
        - ahash: Average-based, fastest but less accurate

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (phash, dhash, ahash) as hex strings
        """
        img = Image.open(image_path)

        phash = str(imagehash.phash(img))
        dhash = str(imagehash.dhash(img))
        ahash = str(imagehash.average_hash(img))

        return phash, dhash, ahash

    def compute_similarity(
        self, hash1: Tuple[str, str, str], hash2: Tuple[str, str, str]
    ) -> float:
        """
        Compute similarity between two hash sets.

        Args:
            hash1: (phash, dhash, ahash) of first image
            hash2: (phash, dhash, ahash) of second image

        Returns:
            Similarity score (0-1)
        """
        phash1, dhash1, ahash1 = hash1
        phash2, dhash2, ahash2 = hash2

        # Compute hamming distances
        def hamming(h1: str, h2: str) -> int:
            return bin(int(h1, 16) ^ int(h2, 16)).count("1")

        # Max hamming distance for 64-bit hash
        max_distance = 64

        phash_sim = 1 - (hamming(phash1, phash2) / max_distance)
        dhash_sim = 1 - (hamming(dhash1, dhash2) / max_distance)
        ahash_sim = 1 - (hamming(ahash1, ahash2) / max_distance)

        # Weighted average (phash is most reliable)
        return 0.5 * phash_sim + 0.3 * dhash_sim + 0.2 * ahash_sim

    def check_duplicate(
        self,
        image_path: str,
        existing_hashes: List[Tuple[str, Tuple[str, str, str]]],
    ) -> DuplicateResult:
        """
        Check if an image is a duplicate of existing photos.

        Args:
            image_path: Path to the new image
            existing_hashes: List of (id, (phash, dhash, ahash)) tuples

        Returns:
            DuplicateResult with detection details
        """
        try:
            new_hashes = self.compute_hash(image_path)

            # Check against all existing
            best_match_id = None
            best_similarity = 0.0

            for existing_id, existing_hash in existing_hashes:
                sim = self.compute_similarity(new_hashes, existing_hash)
                if sim > best_similarity:
                    best_similarity = sim
                    best_match_id = existing_id

            is_duplicate = best_similarity >= self.threshold

            return DuplicateResult(
                is_duplicate=is_duplicate,
                match_id=best_match_id if is_duplicate else None,
                similarity=best_similarity,
                phash=new_hashes[0],
                reason=f"Image is {best_similarity * 100:.1f}% similar to existing photo {best_match_id}"
                if is_duplicate
                else None,
            )

        except Exception as e:
            return DuplicateResult(
                is_duplicate=False,
                match_id=None,
                similarity=0.0,
                phash="",
                reason=f"Error computing hash: {str(e)}",
            )


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA-256 hash of file content.

    This is an exact match hash - only identical files match.
    Used as a quick first check before perceptual hashing.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def check_exact_duplicate(file_path: str, existing_hashes: List[str]) -> bool:
    """
    Quick check for exact file duplicates.

    Args:
        file_path: Path to new file
        existing_hashes: List of SHA-256 hashes

    Returns:
        True if exact duplicate found
    """
    new_hash = compute_file_hash(file_path)
    return new_hash in existing_hashes
