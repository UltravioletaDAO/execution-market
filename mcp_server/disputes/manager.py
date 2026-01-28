"""
Dispute Manager

Core dispute lifecycle management with escrow integration.
Handles creation, responses, resolution, and escalation.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, List

from .models import (
    Dispute,
    DisputeStatus,
    DisputeReason,
    DisputeParty,
    DisputeResponse,
    DisputeEvidence,
    DisputeResolution,
    ResolutionType,
    DisputeConfig,
)

logger = logging.getLogger(__name__)


class DisputeError(Exception):
    """Base exception for dispute operations."""
    pass


class DisputeNotFoundError(DisputeError):
    """Raised when a dispute is not found."""
    pass


class InvalidDisputeStateError(DisputeError):
    """Raised when an operation is invalid for the current state."""
    pass


class DisputeManager:
    """
    Manages the dispute lifecycle.

    Handles:
    - Dispute creation and escrow locking
    - Response collection from parties
    - Evidence management
    - Resolution and payment distribution
    - Escalation to human review

    Example:
        >>> manager = DisputeManager()
        >>>
        >>> # Create a dispute
        >>> dispute = await manager.create_dispute(
        ...     task_id="task123",
        ...     submission_id="sub456",
        ...     initiator_id="worker789",
        ...     initiator_party=DisputeParty.WORKER,
        ...     respondent_id="agent012",
        ...     reason=DisputeReason.QUALITY,
        ...     description="Work was rejected unfairly",
        ...     amount=Decimal("50.00"),
        ...     evidence=[{"file_url": "s3://...", "description": "Screenshot"}]
        ... )
        >>>
        >>> # Agent responds
        >>> dispute = await manager.add_response(
        ...     dispute_id=dispute.id,
        ...     responder_id="agent012",
        ...     message="Work did not meet requirements",
        ...     evidence=[{"file_url": "s3://...", "description": "Requirements doc"}]
        ... )
        >>>
        >>> # Resolve dispute
        >>> dispute = await manager.resolve_dispute(
        ...     dispute_id=dispute.id,
        ...     winner=DisputeParty.WORKER,
        ...     worker_payout_pct=0.7,
        ...     resolution_notes="Partial completion acknowledged"
        ... )
    """

    def __init__(
        self,
        config: Optional[DisputeConfig] = None,
        escrow_manager: Optional[Any] = None,
    ):
        """
        Initialize dispute manager.

        Args:
            config: Dispute configuration (uses defaults if not provided)
            escrow_manager: EscrowManager for fund locking (optional)
        """
        self.config = config or DisputeConfig()
        self.escrow_manager = escrow_manager

        # In-memory storage (should be backed by DB in production)
        self._disputes: Dict[str, Dispute] = {}
        self._by_task: Dict[str, List[str]] = {}  # task_id -> [dispute_ids]
        self._by_party: Dict[str, List[str]] = {}  # party_id -> [dispute_ids]

        logger.info(
            "DisputeManager initialized: response_window=%dh, resolution_sla=%dh",
            self.config.response_window_hours,
            self.config.resolution_sla_hours,
        )

    async def create_dispute(
        self,
        task_id: str,
        initiator_id: str,
        initiator_party: DisputeParty,
        respondent_id: str,
        reason: DisputeReason,
        description: str,
        amount: Decimal,
        submission_id: Optional[str] = None,
        escrow_id: Optional[str] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Dispute:
        """
        Create a new dispute.

        Args:
            task_id: Task being disputed
            initiator_id: ID of party opening dispute
            initiator_party: Worker or agent
            respondent_id: ID of other party
            reason: Category of dispute
            description: Detailed description
            amount: Amount in dispute
            submission_id: Submission ID (if applicable)
            escrow_id: Escrow ID (for fund locking)
            evidence: Initial evidence list

        Returns:
            Created Dispute

        Raises:
            DisputeError: If validation fails
        """
        # Validate description length
        if len(description) > self.config.max_response_length:
            raise DisputeError(
                f"Description exceeds maximum length of {self.config.max_response_length}"
            )

        # Determine respondent party
        respondent_party = (
            DisputeParty.AGENT if initiator_party == DisputeParty.WORKER
            else DisputeParty.WORKER
        )

        # Calculate deadline
        deadline = datetime.now(timezone.utc) + timedelta(
            hours=self.config.resolution_sla_hours
        )

        # Create dispute
        dispute = Dispute(
            id=Dispute.generate_id(),
            task_id=task_id,
            submission_id=submission_id,
            escrow_id=escrow_id,
            initiator_id=initiator_id,
            initiator_party=initiator_party,
            respondent_id=respondent_id,
            respondent_party=respondent_party,
            reason=reason,
            description=description,
            amount_disputed=amount,
            deadline=deadline,
        )

        # Add initial evidence
        if evidence:
            for ev in evidence:
                dispute.evidence.append(
                    DisputeEvidence(
                        id=f"ev_{uuid.uuid4().hex[:8]}",
                        dispute_id=dispute.id,
                        submitted_by=initiator_id,
                        party=initiator_party,
                        file_url=ev.get("file_url", ""),
                        file_type=ev.get("file_type", "unknown"),
                        description=ev.get("description", ""),
                    )
                )

        # Store dispute
        self._disputes[dispute.id] = dispute

        # Index by task
        if task_id not in self._by_task:
            self._by_task[task_id] = []
        self._by_task[task_id].append(dispute.id)

        # Index by parties
        for party_id in [initiator_id, respondent_id]:
            if party_id not in self._by_party:
                self._by_party[party_id] = []
            self._by_party[party_id].append(dispute.id)

        # Lock escrow if available
        if self.escrow_manager and escrow_id:
            try:
                await self.escrow_manager.handle_dispute(
                    task_id=task_id,
                    dispute_reason=f"Dispute opened: {reason.value}"
                )
                logger.info(
                    "Escrow locked for dispute %s, task %s",
                    dispute.id, task_id
                )
            except Exception as e:
                logger.warning(
                    "Failed to lock escrow for dispute %s: %s",
                    dispute.id, str(e)
                )

        logger.info(
            "Dispute created: id=%s, task=%s, reason=%s, amount=$%.2f, initiator=%s",
            dispute.id,
            task_id,
            reason.value,
            float(amount),
            initiator_party.value,
        )

        return dispute

    def get_dispute(self, dispute_id: str) -> Optional[Dispute]:
        """
        Get a dispute by ID.

        Args:
            dispute_id: Dispute identifier

        Returns:
            Dispute or None if not found
        """
        return self._disputes.get(dispute_id)

    def get_disputes_by_task(self, task_id: str) -> List[Dispute]:
        """Get all disputes for a task."""
        dispute_ids = self._by_task.get(task_id, [])
        return [self._disputes[did] for did in dispute_ids if did in self._disputes]

    def get_disputes_by_party(self, party_id: str) -> List[Dispute]:
        """Get all disputes involving a party."""
        dispute_ids = self._by_party.get(party_id, [])
        return [self._disputes[did] for did in dispute_ids if did in self._disputes]

    def get_open_disputes(self) -> List[Dispute]:
        """Get all open disputes."""
        return [d for d in self._disputes.values() if d.is_open]

    async def add_response(
        self,
        dispute_id: str,
        responder_id: str,
        message: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
    ) -> Dispute:
        """
        Add a response to a dispute.

        Args:
            dispute_id: Dispute to respond to
            responder_id: ID of responder
            message: Response message
            evidence: Additional evidence

        Returns:
            Updated Dispute

        Raises:
            DisputeNotFoundError: If dispute not found
            InvalidDisputeStateError: If dispute is not open
            DisputeError: If validation fails
        """
        dispute = self._get_dispute(dispute_id)

        # Validate state
        if not dispute.is_open:
            raise InvalidDisputeStateError(
                f"Cannot respond to dispute in status {dispute.status.value}"
            )

        # Validate responder is a party
        if responder_id not in [dispute.initiator_id, dispute.respondent_id]:
            raise DisputeError(
                f"Responder {responder_id} is not a party to this dispute"
            )

        # Determine responder party
        responder_party = (
            dispute.initiator_party if responder_id == dispute.initiator_id
            else dispute.respondent_party
        )

        # Validate message length
        if len(message) > self.config.max_response_length:
            raise DisputeError(
                f"Message exceeds maximum length of {self.config.max_response_length}"
            )

        # Create response
        response = DisputeResponse(
            id=f"resp_{uuid.uuid4().hex[:8]}",
            dispute_id=dispute_id,
            responder_id=responder_id,
            responder_party=responder_party,
            message=message,
        )

        # Add evidence
        evidence_ids = []
        if evidence:
            # Check evidence limit
            party_evidence = [
                e for e in dispute.evidence if e.party == responder_party
            ]
            if len(party_evidence) + len(evidence) > self.config.max_evidence_per_party:
                raise DisputeError(
                    f"Evidence limit exceeded ({self.config.max_evidence_per_party} max)"
                )

            for ev in evidence:
                ev_obj = DisputeEvidence(
                    id=f"ev_{uuid.uuid4().hex[:8]}",
                    dispute_id=dispute_id,
                    submitted_by=responder_id,
                    party=responder_party,
                    file_url=ev.get("file_url", ""),
                    file_type=ev.get("file_type", "unknown"),
                    description=ev.get("description", ""),
                )
                dispute.evidence.append(ev_obj)
                evidence_ids.append(ev_obj.id)

        response.evidence_ids = evidence_ids
        dispute.responses.append(response)
        dispute.updated_at = datetime.now(timezone.utc)

        # Move to under review if both parties have responded
        if dispute.status == DisputeStatus.OPEN:
            initiator_responded = any(
                r.responder_id == dispute.initiator_id for r in dispute.responses
            )
            respondent_responded = any(
                r.responder_id == dispute.respondent_id for r in dispute.responses
            )
            if initiator_responded and respondent_responded:
                dispute.status = DisputeStatus.UNDER_REVIEW

        logger.info(
            "Response added to dispute %s by %s (%s), evidence_count=%d",
            dispute_id,
            responder_id[:8] + "...",
            responder_party.value,
            len(evidence_ids),
        )

        return dispute

    async def resolve_dispute(
        self,
        dispute_id: str,
        winner: Optional[DisputeParty],
        resolution_notes: str,
        worker_payout_pct: float = 1.0,
        resolved_by: str = "system",
    ) -> Dispute:
        """
        Resolve a dispute.

        Args:
            dispute_id: Dispute to resolve
            winner: Winning party (None for split/dismissed)
            resolution_notes: Explanation of resolution
            worker_payout_pct: Percentage to pay worker (0.0 to 1.0)
            resolved_by: Who resolved (system, arbitrator ID, etc.)

        Returns:
            Resolved Dispute

        Raises:
            DisputeNotFoundError: If dispute not found
            InvalidDisputeStateError: If dispute cannot be resolved
        """
        dispute = self._get_dispute(dispute_id)

        # Validate state
        if not dispute.is_open:
            raise InvalidDisputeStateError(
                f"Cannot resolve dispute in status {dispute.status.value}"
            )

        # Determine resolution type
        if winner == DisputeParty.WORKER and worker_payout_pct >= 1.0:
            resolution_type = ResolutionType.FULL_WORKER
        elif winner == DisputeParty.AGENT and worker_payout_pct <= 0.0:
            resolution_type = ResolutionType.FULL_AGENT
        elif winner is None:
            resolution_type = ResolutionType.DISMISSED
        else:
            resolution_type = ResolutionType.SPLIT

        # Create resolution
        resolution = DisputeResolution(
            winner=winner,
            resolution_type=resolution_type,
            worker_payout_pct=Decimal(str(worker_payout_pct)),
            agent_refund_pct=Decimal(str(1.0 - worker_payout_pct)),
            notes=resolution_notes,
            resolved_by=resolved_by,
        )

        # Apply resolution to escrow if available
        if self.escrow_manager and dispute.escrow_id:
            try:
                from .resolution import apply_resolution
                tx_hashes = await apply_resolution(
                    dispute=dispute,
                    resolution=resolution,
                    escrow_manager=self.escrow_manager,
                )
                resolution.tx_hashes = tx_hashes
            except Exception as e:
                logger.error(
                    "Failed to apply resolution to escrow for dispute %s: %s",
                    dispute_id, str(e)
                )
                # Continue with resolution record even if escrow fails
                resolution.notes += f" [Escrow update failed: {str(e)}]"

        dispute.resolution = resolution
        dispute.status = DisputeStatus.RESOLVED
        dispute.updated_at = datetime.now(timezone.utc)

        logger.info(
            "Dispute resolved: id=%s, winner=%s, worker_pct=%.0f%%, type=%s",
            dispute_id,
            winner.value if winner else "none",
            worker_payout_pct * 100,
            resolution_type.value,
        )

        return dispute

    async def escalate_dispute(
        self,
        dispute_id: str,
        escalation_reason: Optional[str] = None,
    ) -> Dispute:
        """
        Escalate a dispute to human review.

        Args:
            dispute_id: Dispute to escalate
            escalation_reason: Why escalation is needed

        Returns:
            Escalated Dispute

        Raises:
            DisputeNotFoundError: If dispute not found
            InvalidDisputeStateError: If dispute cannot be escalated
        """
        dispute = self._get_dispute(dispute_id)

        # Validate state
        if dispute.status not in (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW):
            raise InvalidDisputeStateError(
                f"Cannot escalate dispute in status {dispute.status.value}"
            )

        dispute.status = DisputeStatus.ESCALATED
        dispute.updated_at = datetime.now(timezone.utc)

        if escalation_reason:
            dispute.metadata["escalation_reason"] = escalation_reason

        logger.info(
            "Dispute escalated: id=%s, reason=%s",
            dispute_id,
            escalation_reason or "manual escalation",
        )

        return dispute

    async def withdraw_dispute(
        self,
        dispute_id: str,
        withdrawer_id: str,
        reason: str,
    ) -> Dispute:
        """
        Withdraw a dispute (only initiator can withdraw).

        Args:
            dispute_id: Dispute to withdraw
            withdrawer_id: ID of withdrawer (must be initiator)
            reason: Reason for withdrawal

        Returns:
            Withdrawn Dispute

        Raises:
            DisputeNotFoundError: If dispute not found
            InvalidDisputeStateError: If dispute cannot be withdrawn
            DisputeError: If withdrawer is not the initiator
        """
        dispute = self._get_dispute(dispute_id)

        # Validate state
        if dispute.status not in (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW):
            raise InvalidDisputeStateError(
                f"Cannot withdraw dispute in status {dispute.status.value}"
            )

        # Validate withdrawer
        if withdrawer_id != dispute.initiator_id:
            raise DisputeError("Only the initiator can withdraw a dispute")

        dispute.status = DisputeStatus.WITHDRAWN
        dispute.updated_at = datetime.now(timezone.utc)
        dispute.metadata["withdrawal_reason"] = reason

        # Unlock escrow if available
        if self.escrow_manager and dispute.escrow_id:
            try:
                # Resolve in favor of respondent (initiator withdrew)
                winner = dispute.respondent_party
                await self.escrow_manager.resolve_dispute(
                    task_id=dispute.task_id,
                    winner=winner.value,
                )
            except Exception as e:
                logger.warning(
                    "Failed to unlock escrow after withdrawal: %s", str(e)
                )

        logger.info(
            "Dispute withdrawn: id=%s, by=%s, reason=%s",
            dispute_id,
            withdrawer_id[:8] + "...",
            reason[:50],
        )

        return dispute

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get dispute statistics.

        Returns:
            Dict with statistics
        """
        all_disputes = list(self._disputes.values())
        open_disputes = [d for d in all_disputes if d.is_open]
        resolved_disputes = [d for d in all_disputes if d.status == DisputeStatus.RESOLVED]

        # Calculate resolution stats
        worker_wins = sum(
            1 for d in resolved_disputes
            if d.resolution and d.resolution.winner == DisputeParty.WORKER
        )
        agent_wins = sum(
            1 for d in resolved_disputes
            if d.resolution and d.resolution.winner == DisputeParty.AGENT
        )
        splits = sum(
            1 for d in resolved_disputes
            if d.resolution and d.resolution.resolution_type == ResolutionType.SPLIT
        )

        # Calculate average resolution time
        resolution_times = []
        for d in resolved_disputes:
            if d.resolution:
                delta = d.resolution.resolved_at - d.created_at
                resolution_times.append(delta.total_seconds() / 3600)  # hours

        avg_resolution_hours = (
            sum(resolution_times) / len(resolution_times)
            if resolution_times else 0
        )

        # Count by reason
        by_reason = {}
        for d in all_disputes:
            reason = d.reason.value
            by_reason[reason] = by_reason.get(reason, 0) + 1

        return {
            "total": len(all_disputes),
            "open": len(open_disputes),
            "resolved": len(resolved_disputes),
            "escalated": sum(1 for d in all_disputes if d.status == DisputeStatus.ESCALATED),
            "withdrawn": sum(1 for d in all_disputes if d.status == DisputeStatus.WITHDRAWN),
            "outcomes": {
                "worker_wins": worker_wins,
                "agent_wins": agent_wins,
                "splits": splits,
            },
            "avg_resolution_hours": round(avg_resolution_hours, 1),
            "by_reason": by_reason,
            "total_amount_disputed": float(sum(d.amount_disputed for d in all_disputes)),
        }

    def _get_dispute(self, dispute_id: str) -> Dispute:
        """Get dispute or raise error."""
        dispute = self._disputes.get(dispute_id)
        if not dispute:
            raise DisputeNotFoundError(f"Dispute not found: {dispute_id}")
        return dispute


# Module-level singleton
_default_manager: Optional[DisputeManager] = None


def get_dispute_manager(
    config: Optional[DisputeConfig] = None,
    escrow_manager: Optional[Any] = None,
) -> DisputeManager:
    """
    Get or create the default DisputeManager instance.

    Args:
        config: Optional configuration
        escrow_manager: Optional escrow manager for integration

    Returns:
        DisputeManager singleton instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = DisputeManager(config, escrow_manager)
    return _default_manager


def reset_manager() -> None:
    """Reset the singleton manager (for testing)."""
    global _default_manager
    _default_manager = None


# Convenience functions

async def create_dispute(
    task_id: str,
    initiator_id: str,
    initiator_party: DisputeParty,
    respondent_id: str,
    reason: DisputeReason,
    description: str,
    amount: Decimal,
    evidence: Optional[List[Dict[str, Any]]] = None,
) -> Dispute:
    """
    Convenience function to create a dispute.

    See DisputeManager.create_dispute for full documentation.
    """
    manager = get_dispute_manager()
    return await manager.create_dispute(
        task_id=task_id,
        initiator_id=initiator_id,
        initiator_party=initiator_party,
        respondent_id=respondent_id,
        reason=reason,
        description=description,
        amount=amount,
        evidence=evidence,
    )


async def resolve_dispute(
    dispute_id: str,
    winner: Optional[DisputeParty],
    resolution_notes: str,
    worker_payout_pct: float = 1.0,
) -> Dispute:
    """
    Convenience function to resolve a dispute.

    See DisputeManager.resolve_dispute for full documentation.
    """
    manager = get_dispute_manager()
    return await manager.resolve_dispute(
        dispute_id=dispute_id,
        winner=winner,
        resolution_notes=resolution_notes,
        worker_payout_pct=worker_payout_pct,
    )
