"""
Evidence Handling Module

Manages evidence attachment, retrieval, and integrity verification.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from .models import (
    Dispute,
    DisputeEvidence,
    DisputeParty,
)

logger = logging.getLogger(__name__)


class EvidenceError(Exception):
    """Base exception for evidence operations."""
    pass


class EvidenceLimitError(EvidenceError):
    """Raised when evidence limit is exceeded."""
    pass


class EvidenceNotFoundError(EvidenceError):
    """Raised when evidence is not found."""
    pass


class EvidenceIntegrityError(EvidenceError):
    """Raised when evidence integrity check fails."""
    pass


class EvidenceManager:
    """
    Manages evidence for disputes.

    Handles:
    - Evidence attachment with metadata
    - Integrity verification via SHA-256 hashing
    - Retrieval and listing
    - Storage integration (extensible)

    Example:
        >>> manager = EvidenceManager(max_per_party=10)
        >>>
        >>> # Attach evidence
        >>> evidence = await manager.attach_evidence(
        ...     dispute_id="disp_abc123",
        ...     submitter_id="worker456",
        ...     party=DisputeParty.WORKER,
        ...     file_url="s3://bucket/evidence.jpg",
        ...     file_type="image/jpeg",
        ...     description="Screenshot of completed work",
        ...     file_content=b"..."  # Optional: for hash calculation
        ... )
        >>>
        >>> # Verify integrity
        >>> is_valid = await manager.verify_evidence_integrity(
        ...     evidence_id="ev_xyz789",
        ...     file_content=b"..."
        ... )
    """

    def __init__(
        self,
        max_per_party: int = 10,
        max_file_size_mb: int = 10,
        allowed_types: Optional[List[str]] = None,
    ):
        """
        Initialize evidence manager.

        Args:
            max_per_party: Maximum evidence items per party per dispute
            max_file_size_mb: Maximum file size in MB
            allowed_types: Allowed MIME types (None = all allowed)
        """
        self.max_per_party = max_per_party
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.allowed_types = allowed_types or [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "video/mp4",
            "video/webm",
            "application/pdf",
            "text/plain",
            "application/json",
        ]

        # In-memory storage (should be backed by DB in production)
        self._evidence: Dict[str, DisputeEvidence] = {}
        self._by_dispute: Dict[str, List[str]] = {}  # dispute_id -> [evidence_ids]

        logger.info(
            "EvidenceManager initialized: max_per_party=%d, max_size=%dMB",
            max_per_party,
            max_file_size_mb,
        )

    async def attach_evidence(
        self,
        dispute_id: str,
        submitter_id: str,
        party: DisputeParty,
        file_url: str,
        file_type: str,
        description: str,
        file_content: Optional[bytes] = None,
        dispute: Optional[Dispute] = None,
    ) -> DisputeEvidence:
        """
        Attach evidence to a dispute.

        Args:
            dispute_id: Dispute to attach evidence to
            submitter_id: ID of person submitting
            party: Which party is submitting
            file_url: URL or path to evidence file
            file_type: MIME type of file
            description: Description of what this proves
            file_content: Optional file content for hash calculation
            dispute: Optional Dispute object for limit checking

        Returns:
            Created DisputeEvidence

        Raises:
            EvidenceLimitError: If party has exceeded evidence limit
            EvidenceError: If validation fails
        """
        # Validate file type
        if file_type not in self.allowed_types:
            raise EvidenceError(
                f"File type '{file_type}' not allowed. "
                f"Allowed types: {', '.join(self.allowed_types)}"
            )

        # Check limit if dispute provided
        if dispute:
            party_count = sum(
                1 for e in dispute.evidence if e.party == party
            )
            if party_count >= self.max_per_party:
                raise EvidenceLimitError(
                    f"Evidence limit exceeded ({self.max_per_party} max per party)"
                )

        # Calculate hash if content provided
        file_hash = None
        if file_content:
            file_hash = self._calculate_hash(file_content)

            # Check file size
            if len(file_content) > self.max_file_size_bytes:
                raise EvidenceError(
                    f"File size {len(file_content) / 1024 / 1024:.1f}MB exceeds "
                    f"maximum {self.max_file_size_bytes / 1024 / 1024:.0f}MB"
                )

        # Create evidence
        evidence = DisputeEvidence(
            id=f"ev_{uuid.uuid4().hex[:8]}",
            dispute_id=dispute_id,
            submitted_by=submitter_id,
            party=party,
            file_url=file_url,
            file_type=file_type,
            description=description,
            hash=file_hash,
            verified=file_hash is not None,
        )

        # Store evidence
        self._evidence[evidence.id] = evidence

        # Index by dispute
        if dispute_id not in self._by_dispute:
            self._by_dispute[dispute_id] = []
        self._by_dispute[dispute_id].append(evidence.id)

        # Add to dispute object if provided
        if dispute:
            dispute.evidence.append(evidence)

        logger.info(
            "Evidence attached: id=%s, dispute=%s, party=%s, type=%s",
            evidence.id,
            dispute_id,
            party.value,
            file_type,
        )

        return evidence

    def get_evidence(self, evidence_id: str) -> Optional[DisputeEvidence]:
        """
        Get evidence by ID.

        Args:
            evidence_id: Evidence identifier

        Returns:
            DisputeEvidence or None if not found
        """
        return self._evidence.get(evidence_id)

    def get_evidence_by_dispute(self, dispute_id: str) -> List[DisputeEvidence]:
        """
        Get all evidence for a dispute.

        Args:
            dispute_id: Dispute identifier

        Returns:
            List of DisputeEvidence
        """
        evidence_ids = self._by_dispute.get(dispute_id, [])
        return [
            self._evidence[eid] for eid in evidence_ids
            if eid in self._evidence
        ]

    def get_evidence_by_party(
        self,
        dispute_id: str,
        party: DisputeParty,
    ) -> List[DisputeEvidence]:
        """
        Get evidence from a specific party.

        Args:
            dispute_id: Dispute identifier
            party: Party to filter by

        Returns:
            List of DisputeEvidence from that party
        """
        all_evidence = self.get_evidence_by_dispute(dispute_id)
        return [e for e in all_evidence if e.party == party]

    async def verify_evidence_integrity(
        self,
        evidence_id: str,
        file_content: bytes,
    ) -> bool:
        """
        Verify evidence integrity by comparing hash.

        Args:
            evidence_id: Evidence to verify
            file_content: Current file content

        Returns:
            True if integrity verified (hash matches)

        Raises:
            EvidenceNotFoundError: If evidence not found
            EvidenceIntegrityError: If no stored hash to compare
        """
        evidence = self._evidence.get(evidence_id)
        if not evidence:
            raise EvidenceNotFoundError(f"Evidence not found: {evidence_id}")

        if not evidence.hash:
            raise EvidenceIntegrityError(
                f"No stored hash for evidence {evidence_id}"
            )

        # Calculate current hash
        current_hash = self._calculate_hash(file_content)

        # Compare
        is_valid = current_hash == evidence.hash

        if is_valid:
            evidence.verified = True
            logger.info("Evidence %s integrity verified", evidence_id)
        else:
            evidence.verified = False
            logger.warning(
                "Evidence %s integrity FAILED: expected %s, got %s",
                evidence_id,
                evidence.hash[:16] + "...",
                current_hash[:16] + "...",
            )

        return is_valid

    async def update_evidence_hash(
        self,
        evidence_id: str,
        file_content: bytes,
    ) -> DisputeEvidence:
        """
        Update the hash for evidence (e.g., after upload).

        Args:
            evidence_id: Evidence to update
            file_content: File content for hash calculation

        Returns:
            Updated DisputeEvidence

        Raises:
            EvidenceNotFoundError: If evidence not found
        """
        evidence = self._evidence.get(evidence_id)
        if not evidence:
            raise EvidenceNotFoundError(f"Evidence not found: {evidence_id}")

        evidence.hash = self._calculate_hash(file_content)
        evidence.verified = True

        logger.info(
            "Evidence %s hash updated: %s...",
            evidence_id,
            evidence.hash[:16],
        )

        return evidence

    def remove_evidence(self, evidence_id: str) -> bool:
        """
        Remove evidence from storage.

        Args:
            evidence_id: Evidence to remove

        Returns:
            True if removed, False if not found
        """
        evidence = self._evidence.pop(evidence_id, None)
        if not evidence:
            return False

        # Remove from dispute index
        if evidence.dispute_id in self._by_dispute:
            self._by_dispute[evidence.dispute_id] = [
                eid for eid in self._by_dispute[evidence.dispute_id]
                if eid != evidence_id
            ]

        logger.info("Evidence removed: %s", evidence_id)
        return True

    def get_statistics(self, dispute_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get evidence statistics.

        Args:
            dispute_id: Optional dispute to filter by

        Returns:
            Dict with statistics
        """
        if dispute_id:
            evidence_list = self.get_evidence_by_dispute(dispute_id)
        else:
            evidence_list = list(self._evidence.values())

        # Count by party
        worker_count = sum(1 for e in evidence_list if e.party == DisputeParty.WORKER)
        agent_count = sum(1 for e in evidence_list if e.party == DisputeParty.AGENT)

        # Count by type
        by_type: Dict[str, int] = {}
        for e in evidence_list:
            by_type[e.file_type] = by_type.get(e.file_type, 0) + 1

        # Count verified
        verified_count = sum(1 for e in evidence_list if e.verified)

        return {
            "total": len(evidence_list),
            "by_party": {
                "worker": worker_count,
                "agent": agent_count,
            },
            "by_type": by_type,
            "verified": verified_count,
            "unverified": len(evidence_list) - verified_count,
        }

    def _calculate_hash(self, content: bytes) -> str:
        """Calculate SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()


# Module-level singleton
_default_manager: Optional[EvidenceManager] = None


def get_evidence_manager(
    max_per_party: int = 10,
    max_file_size_mb: int = 10,
) -> EvidenceManager:
    """
    Get or create the default EvidenceManager instance.

    Args:
        max_per_party: Maximum evidence per party
        max_file_size_mb: Maximum file size in MB

    Returns:
        EvidenceManager singleton instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = EvidenceManager(max_per_party, max_file_size_mb)
    return _default_manager


def reset_manager() -> None:
    """Reset the singleton manager (for testing)."""
    global _default_manager
    _default_manager = None


# Convenience functions

async def attach_evidence(
    dispute_id: str,
    submitter_id: str,
    party: DisputeParty,
    file_url: str,
    file_type: str,
    description: str,
    file_content: Optional[bytes] = None,
) -> DisputeEvidence:
    """
    Convenience function to attach evidence.

    See EvidenceManager.attach_evidence for full documentation.
    """
    manager = get_evidence_manager()
    return await manager.attach_evidence(
        dispute_id=dispute_id,
        submitter_id=submitter_id,
        party=party,
        file_url=file_url,
        file_type=file_type,
        description=description,
        file_content=file_content,
    )


def get_dispute_evidence(dispute_id: str) -> List[DisputeEvidence]:
    """
    Convenience function to get evidence for a dispute.

    See EvidenceManager.get_evidence_by_dispute for full documentation.
    """
    manager = get_evidence_manager()
    return manager.get_evidence_by_dispute(dispute_id)


async def verify_integrity(evidence_id: str, file_content: bytes) -> bool:
    """
    Convenience function to verify evidence integrity.

    See EvidenceManager.verify_evidence_integrity for full documentation.
    """
    manager = get_evidence_manager()
    return await manager.verify_evidence_integrity(evidence_id, file_content)
