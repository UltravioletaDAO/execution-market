"""
Dispute Data Models

Core data structures for the dispute resolution system.
Defines status enums, reason categories, and dispute records.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List


class DisputeStatus(str, Enum):
    """
    Status of a dispute through its lifecycle.

    Flow:
    OPEN -> UNDER_REVIEW -> RESOLVED
                        -> ESCALATED -> RESOLVED
    """
    OPEN = "open"                    # Newly created, awaiting review
    UNDER_REVIEW = "under_review"    # Being reviewed by system/arbitrators
    RESOLVED = "resolved"            # Final decision made
    ESCALATED = "escalated"          # Escalated to human review
    WITHDRAWN = "withdrawn"          # Withdrawn by initiator
    EXPIRED = "expired"              # Timed out without resolution


class DisputeReason(str, Enum):
    """
    Categories of dispute reasons.

    Used for routing and statistics.
    """
    QUALITY = "quality"              # Work quality not acceptable
    FRAUD = "fraud"                  # Suspected fraudulent activity
    INCOMPLETE = "incomplete"        # Work not fully completed
    NON_DELIVERY = "non_delivery"    # Work not delivered at all
    LATE_DELIVERY = "late_delivery"  # Deadline missed
    WRONG_WORK = "wrong_work"        # Work doesn't match requirements
    PAYMENT = "payment"              # Payment issues
    COMMUNICATION = "communication"  # Communication breakdown
    SAFETY = "safety"                # Safety concerns
    OTHER = "other"                  # Other reasons


class DisputeParty(str, Enum):
    """Party in a dispute."""
    WORKER = "worker"
    AGENT = "agent"


class ResolutionType(str, Enum):
    """Type of resolution applied."""
    FULL_WORKER = "full_worker"      # 100% to worker
    FULL_AGENT = "full_agent"        # 100% refund to agent
    SPLIT = "split"                  # Split between parties
    DISMISSED = "dismissed"          # No action needed
    MUTUAL = "mutual"                # Mutual agreement


@dataclass
class DisputeEvidence:
    """
    Evidence attached to a dispute.

    Attributes:
        id: Unique evidence identifier
        dispute_id: Parent dispute ID
        submitted_by: Who submitted the evidence
        party: Which party submitted
        file_url: URL or path to evidence file
        file_type: MIME type or category
        description: Description of what this proves
        hash: SHA-256 hash for integrity verification
        submitted_at: When evidence was submitted
        verified: Whether integrity has been verified
    """
    id: str
    dispute_id: str
    submitted_by: str
    party: DisputeParty
    file_url: str
    file_type: str
    description: str
    hash: Optional[str] = None
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "dispute_id": self.dispute_id,
            "submitted_by": self.submitted_by,
            "party": self.party.value,
            "file_url": self.file_url,
            "file_type": self.file_type,
            "description": self.description,
            "hash": self.hash,
            "submitted_at": self.submitted_at.isoformat(),
            "verified": self.verified,
        }


@dataclass
class DisputeResponse:
    """
    Response from a party in the dispute.

    Allows parties to add their side of the story and additional evidence.
    """
    id: str
    dispute_id: str
    responder_id: str
    responder_party: DisputeParty
    message: str
    evidence_ids: List[str] = field(default_factory=list)
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "dispute_id": self.dispute_id,
            "responder_id": self.responder_id,
            "responder_party": self.responder_party.value,
            "message": self.message,
            "evidence_ids": self.evidence_ids,
            "submitted_at": self.submitted_at.isoformat(),
        }


@dataclass
class DisputeResolution:
    """
    Resolution details for a dispute.

    Records the final decision and payment distribution.
    """
    winner: Optional[DisputeParty]
    resolution_type: ResolutionType
    worker_payout_pct: Decimal         # 0.0 to 1.0
    agent_refund_pct: Decimal           # 0.0 to 1.0
    notes: str
    resolved_by: str                    # System, arbitrator ID, or "mutual"
    resolved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tx_hashes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "winner": self.winner.value if self.winner else None,
            "resolution_type": self.resolution_type.value,
            "worker_payout_pct": float(self.worker_payout_pct),
            "agent_refund_pct": float(self.agent_refund_pct),
            "notes": self.notes,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat(),
            "tx_hashes": self.tx_hashes,
        }


@dataclass
class Dispute:
    """
    Complete dispute record.

    Tracks the full lifecycle of a dispute from creation to resolution.

    Attributes:
        id: Unique dispute identifier
        task_id: Task being disputed
        submission_id: Submission being disputed (if applicable)
        escrow_id: Associated escrow (for fund locking)

        initiator_id: Who opened the dispute
        initiator_party: Worker or agent
        respondent_id: Other party
        respondent_party: Worker or agent

        reason: Category of dispute
        description: Detailed description
        amount_disputed: Amount in dispute (USD)

        status: Current status
        created_at: When dispute was opened
        updated_at: Last update timestamp
        deadline: SLA deadline for resolution

        responses: Responses from parties
        evidence: Attached evidence
        resolution: Final resolution (if resolved)

        metadata: Additional data
    """
    id: str
    task_id: str
    submission_id: Optional[str]
    escrow_id: Optional[str]

    initiator_id: str
    initiator_party: DisputeParty
    respondent_id: str
    respondent_party: DisputeParty

    reason: DisputeReason
    description: str
    amount_disputed: Decimal

    status: DisputeStatus = DisputeStatus.OPEN
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deadline: Optional[datetime] = None

    responses: List[DisputeResponse] = field(default_factory=list)
    evidence: List[DisputeEvidence] = field(default_factory=list)
    resolution: Optional[DisputeResolution] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def generate_id() -> str:
        """Generate a unique dispute ID."""
        return f"disp_{uuid.uuid4().hex[:12]}"

    @property
    def is_open(self) -> bool:
        """Check if dispute is still active."""
        return self.status in (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW, DisputeStatus.ESCALATED)

    @property
    def is_resolved(self) -> bool:
        """Check if dispute has been resolved."""
        return self.status == DisputeStatus.RESOLVED

    @property
    def days_open(self) -> int:
        """Calculate days since dispute was opened."""
        now = datetime.now(timezone.utc)
        delta = now - self.created_at
        return delta.days

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "submission_id": self.submission_id,
            "escrow_id": self.escrow_id,

            "initiator_id": self.initiator_id,
            "initiator_party": self.initiator_party.value,
            "respondent_id": self.respondent_id,
            "respondent_party": self.respondent_party.value,

            "reason": self.reason.value,
            "description": self.description,
            "amount_disputed": float(self.amount_disputed),

            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,

            "responses": [r.to_dict() for r in self.responses],
            "evidence": [e.to_dict() for e in self.evidence],
            "resolution": self.resolution.to_dict() if self.resolution else None,

            "is_open": self.is_open,
            "days_open": self.days_open,
            "metadata": self.metadata,
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Serialize to summary dictionary (for listings)."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "reason": self.reason.value,
            "amount_disputed": float(self.amount_disputed),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "days_open": self.days_open,
            "initiator_party": self.initiator_party.value,
        }


@dataclass
class DisputeConfig:
    """
    Configuration for dispute handling.

    Attributes:
        response_window_hours: Hours for respondent to reply
        resolution_sla_hours: SLA for resolution (before auto-escalation)
        escalation_threshold_usd: Disputes above this always escalate
        auto_resolve_below_usd: Disputes below this can auto-resolve
        max_evidence_per_party: Max evidence items per party
        max_response_length: Max characters in response message
    """
    response_window_hours: int = 72          # 3 days
    resolution_sla_hours: int = 168          # 7 days
    escalation_threshold_usd: Decimal = Decimal("100.00")
    auto_resolve_below_usd: Decimal = Decimal("10.00")
    max_evidence_per_party: int = 10
    max_response_length: int = 5000

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "response_window_hours": self.response_window_hours,
            "resolution_sla_hours": self.resolution_sla_hours,
            "escalation_threshold_usd": float(self.escalation_threshold_usd),
            "auto_resolve_below_usd": float(self.auto_resolve_below_usd),
            "max_evidence_per_party": self.max_evidence_per_party,
            "max_response_length": self.max_response_length,
        }
