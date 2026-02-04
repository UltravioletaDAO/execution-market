"""
Execution Market Disputes Module

Complete dispute resolution system for the Execution Market platform.

Components:
- models: Data structures (Dispute, DisputeStatus, DisputeReason, etc.)
- manager: Core dispute lifecycle management
- resolution: Resolution logic and payment distribution
- evidence: Evidence attachment and integrity verification
- timeline: Event timeline and SLA tracking
- router: Dispute routing to appropriate resolution mechanisms

Example:
    >>> from mcp_server.disputes import (
    ...     DisputeManager,
    ...     DisputeReason,
    ...     DisputeParty,
    ... )
    >>>
    >>> # Create manager
    >>> manager = DisputeManager()
    >>>
    >>> # Open a dispute
    >>> dispute = await manager.create_dispute(
    ...     task_id="task_123",
    ...     initiator_id="worker_456",
    ...     initiator_party=DisputeParty.WORKER,
    ...     respondent_id="agent_789",
    ...     reason=DisputeReason.QUALITY,
    ...     description="Work was rejected unfairly",
    ...     amount=Decimal("50.00"),
    ... )
    >>>
    >>> # Add response from other party
    >>> dispute = await manager.add_response(
    ...     dispute_id=dispute.id,
    ...     responder_id="agent_789",
    ...     message="Work did not meet requirements",
    ... )
    >>>
    >>> # Resolve dispute
    >>> dispute = await manager.resolve_dispute(
    ...     dispute_id=dispute.id,
    ...     winner=DisputeParty.WORKER,
    ...     worker_payout_pct=0.7,
    ...     resolution_notes="Partial completion acknowledged",
    ... )
"""

# Models
from .models import (
    DisputeStatus,
    DisputeReason,
    DisputeParty,
    ResolutionType,
    DisputeEvidence,
    DisputeResponse,
    DisputeResolution,
    Dispute,
    DisputeConfig,
)

# Manager
from .manager import (
    DisputeManager,
    DisputeError,
    DisputeNotFoundError,
    InvalidDisputeStateError,
    get_dispute_manager,
    reset_manager as reset_dispute_manager,
    create_dispute,
    resolve_dispute,
)

# Resolution
from .resolution import (
    ResolutionError,
    calculate_refund_split,
    apply_resolution,
    notify_parties,
    determine_auto_resolution,
    get_resolution_recommendations,
)

# Evidence
from .evidence import (
    EvidenceManager,
    EvidenceError,
    EvidenceLimitError,
    EvidenceNotFoundError,
    EvidenceIntegrityError,
    get_evidence_manager,
    reset_manager as reset_evidence_manager,
    attach_evidence,
    get_dispute_evidence,
    verify_integrity,
)

# Timeline
from .timeline import (
    TimelineEventType,
    SLAStatus,
    TimelineEvent,
    SLAInfo,
    TimelineManager,
    get_timeline_manager,
    reset_manager as reset_timeline_manager,
    add_event,
    get_timeline,
    calculate_sla_status,
)

# Router (existing)
from .router import DisputeRouter

__all__ = [
    # Models
    "DisputeStatus",
    "DisputeReason",
    "DisputeParty",
    "ResolutionType",
    "DisputeEvidence",
    "DisputeResponse",
    "DisputeResolution",
    "Dispute",
    "DisputeConfig",

    # Manager
    "DisputeManager",
    "DisputeError",
    "DisputeNotFoundError",
    "InvalidDisputeStateError",
    "get_dispute_manager",
    "reset_dispute_manager",
    "create_dispute",
    "resolve_dispute",

    # Resolution
    "ResolutionError",
    "calculate_refund_split",
    "apply_resolution",
    "notify_parties",
    "determine_auto_resolution",
    "get_resolution_recommendations",

    # Evidence
    "EvidenceManager",
    "EvidenceError",
    "EvidenceLimitError",
    "EvidenceNotFoundError",
    "EvidenceIntegrityError",
    "get_evidence_manager",
    "reset_evidence_manager",
    "attach_evidence",
    "get_dispute_evidence",
    "verify_integrity",

    # Timeline
    "TimelineEventType",
    "SLAStatus",
    "TimelineEvent",
    "SLAInfo",
    "TimelineManager",
    "get_timeline_manager",
    "reset_timeline_manager",
    "add_event",
    "get_timeline",
    "calculate_sla_status",

    # Router
    "DisputeRouter",
]
