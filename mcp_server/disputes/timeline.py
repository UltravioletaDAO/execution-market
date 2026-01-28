"""
Dispute Timeline Module

Tracks the complete history of a dispute with SLA monitoring.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List

from .models import Dispute, DisputeStatus

logger = logging.getLogger(__name__)


class TimelineEventType(str, Enum):
    """Types of timeline events."""
    # Lifecycle events
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_UPDATED = "dispute_updated"
    STATUS_CHANGED = "status_changed"
    DISPUTE_RESOLVED = "dispute_resolved"
    DISPUTE_ESCALATED = "dispute_escalated"
    DISPUTE_WITHDRAWN = "dispute_withdrawn"

    # Response events
    RESPONSE_ADDED = "response_added"
    EVIDENCE_ATTACHED = "evidence_attached"
    EVIDENCE_VERIFIED = "evidence_verified"

    # SLA events
    SLA_WARNING = "sla_warning"
    SLA_BREACH = "sla_breach"
    RESPONSE_DEADLINE_WARNING = "response_deadline_warning"
    RESPONSE_DEADLINE_EXPIRED = "response_deadline_expired"

    # Administrative events
    ARBITRATOR_ASSIGNED = "arbitrator_assigned"
    NOTE_ADDED = "note_added"
    PRIORITY_CHANGED = "priority_changed"

    # Payment events
    ESCROW_LOCKED = "escrow_locked"
    PAYMENT_RELEASED = "payment_released"
    REFUND_ISSUED = "refund_issued"


class SLAStatus(str, Enum):
    """SLA status levels."""
    ON_TRACK = "on_track"
    WARNING = "warning"
    BREACHED = "breached"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class TimelineEvent:
    """
    A single event in the dispute timeline.

    Attributes:
        id: Unique event identifier
        dispute_id: Parent dispute ID
        event_type: Type of event
        timestamp: When event occurred
        actor_id: Who triggered the event (if applicable)
        description: Human-readable description
        data: Additional event-specific data
        is_system: Whether this is a system-generated event
    """
    id: str
    dispute_id: str
    event_type: TimelineEventType
    timestamp: datetime
    description: str
    actor_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    is_system: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "dispute_id": self.dispute_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "actor_id": self.actor_id,
            "description": self.description,
            "data": self.data,
            "is_system": self.is_system,
        }


@dataclass
class SLAInfo:
    """
    SLA status information for a dispute.

    Attributes:
        status: Current SLA status
        deadline: Resolution deadline
        time_remaining: Time remaining until deadline
        time_elapsed: Time since dispute opened
        response_deadline: Deadline for respondent to reply
        response_remaining: Time remaining for response
        warnings: List of active warnings
    """
    status: SLAStatus
    deadline: Optional[datetime]
    time_remaining: Optional[timedelta]
    time_elapsed: timedelta
    response_deadline: Optional[datetime]
    response_remaining: Optional[timedelta]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "status": self.status.value,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "time_remaining_hours": (
                self.time_remaining.total_seconds() / 3600
                if self.time_remaining else None
            ),
            "time_elapsed_hours": self.time_elapsed.total_seconds() / 3600,
            "response_deadline": (
                self.response_deadline.isoformat()
                if self.response_deadline else None
            ),
            "response_remaining_hours": (
                self.response_remaining.total_seconds() / 3600
                if self.response_remaining else None
            ),
            "warnings": self.warnings,
        }


class TimelineManager:
    """
    Manages dispute timelines and SLA tracking.

    Tracks:
    - All events in dispute lifecycle
    - SLA deadlines and status
    - Response windows
    - Automatic warnings

    Example:
        >>> manager = TimelineManager(sla_hours=168, response_hours=72)
        >>>
        >>> # Add event
        >>> event = manager.add_event(
        ...     dispute_id="disp_abc123",
        ...     event_type=TimelineEventType.RESPONSE_ADDED,
        ...     description="Agent responded to dispute",
        ...     actor_id="agent456",
        ...     data={"response_id": "resp_xyz"}
        ... )
        >>>
        >>> # Get timeline
        >>> timeline = manager.get_timeline("disp_abc123")
        >>>
        >>> # Check SLA
        >>> sla = manager.calculate_sla_status(dispute)
    """

    def __init__(
        self,
        sla_hours: int = 168,
        response_hours: int = 72,
        sla_warning_threshold: float = 0.25,
    ):
        """
        Initialize timeline manager.

        Args:
            sla_hours: Hours for resolution SLA
            response_hours: Hours for response window
            sla_warning_threshold: Threshold for SLA warning (% remaining)
        """
        self.sla_hours = sla_hours
        self.response_hours = response_hours
        self.sla_warning_threshold = sla_warning_threshold

        # In-memory storage (should be backed by DB in production)
        self._events: Dict[str, List[TimelineEvent]] = {}  # dispute_id -> events
        self._event_counter = 0

        logger.info(
            "TimelineManager initialized: sla=%dh, response=%dh, warning=%.0f%%",
            sla_hours,
            response_hours,
            sla_warning_threshold * 100,
        )

    def add_event(
        self,
        dispute_id: str,
        event_type: TimelineEventType,
        description: str,
        actor_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        is_system: bool = False,
        timestamp: Optional[datetime] = None,
    ) -> TimelineEvent:
        """
        Add an event to a dispute's timeline.

        Args:
            dispute_id: Dispute to add event to
            event_type: Type of event
            description: Human-readable description
            actor_id: Who triggered the event
            data: Additional event data
            is_system: Whether this is system-generated
            timestamp: Event timestamp (defaults to now)

        Returns:
            Created TimelineEvent
        """
        self._event_counter += 1
        event_id = f"evt_{self._event_counter:06d}"

        event = TimelineEvent(
            id=event_id,
            dispute_id=dispute_id,
            event_type=event_type,
            timestamp=timestamp or datetime.now(timezone.utc),
            actor_id=actor_id,
            description=description,
            data=data or {},
            is_system=is_system,
        )

        if dispute_id not in self._events:
            self._events[dispute_id] = []
        self._events[dispute_id].append(event)

        logger.debug(
            "Timeline event added: dispute=%s, type=%s, desc=%s",
            dispute_id,
            event_type.value,
            description[:50],
        )

        return event

    def get_timeline(
        self,
        dispute_id: str,
        event_types: Optional[List[TimelineEventType]] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[TimelineEvent]:
        """
        Get timeline for a dispute.

        Args:
            dispute_id: Dispute to get timeline for
            event_types: Filter by event types
            since: Only events after this timestamp
            limit: Maximum events to return

        Returns:
            List of TimelineEvent sorted by timestamp
        """
        events = self._events.get(dispute_id, [])

        # Filter by type
        if event_types:
            events = [e for e in events if e.event_type in event_types]

        # Filter by time
        if since:
            events = [e for e in events if e.timestamp >= since]

        # Sort by timestamp (newest first)
        events = sorted(events, key=lambda e: e.timestamp, reverse=True)

        # Apply limit
        return events[:limit]

    def calculate_sla_status(self, dispute: Dispute) -> SLAInfo:
        """
        Calculate SLA status for a dispute.

        Args:
            dispute: Dispute to check

        Returns:
            SLAInfo with current status
        """
        now = datetime.now(timezone.utc)
        warnings = []

        # Calculate time elapsed
        time_elapsed = now - dispute.created_at

        # Not applicable for resolved disputes
        if not dispute.is_open:
            return SLAInfo(
                status=SLAStatus.NOT_APPLICABLE,
                deadline=dispute.deadline,
                time_remaining=None,
                time_elapsed=time_elapsed,
                response_deadline=None,
                response_remaining=None,
            )

        # Calculate resolution deadline
        resolution_deadline = dispute.deadline or (
            dispute.created_at + timedelta(hours=self.sla_hours)
        )
        time_remaining = resolution_deadline - now

        # Calculate response deadline
        response_deadline = dispute.created_at + timedelta(hours=self.response_hours)
        response_remaining = response_deadline - now

        # Check if respondent has responded
        has_respondent_response = any(
            r.responder_id == dispute.respondent_id
            for r in dispute.responses
        )

        # Determine SLA status
        if time_remaining.total_seconds() < 0:
            status = SLAStatus.BREACHED
            warnings.append("Resolution SLA has been breached")
            self._log_sla_event(dispute.id, TimelineEventType.SLA_BREACH)
        elif time_remaining.total_seconds() < (self.sla_hours * 3600 * self.sla_warning_threshold):
            status = SLAStatus.WARNING
            hours_left = time_remaining.total_seconds() / 3600
            warnings.append(f"Resolution deadline approaching: {hours_left:.1f}h remaining")
        else:
            status = SLAStatus.ON_TRACK

        # Check response deadline
        if not has_respondent_response:
            if response_remaining.total_seconds() < 0:
                warnings.append("Response deadline has expired")
                self._log_sla_event(
                    dispute.id,
                    TimelineEventType.RESPONSE_DEADLINE_EXPIRED
                )
            elif response_remaining.total_seconds() < (self.response_hours * 3600 * 0.25):
                hours_left = response_remaining.total_seconds() / 3600
                warnings.append(f"Response deadline approaching: {hours_left:.1f}h remaining")
        else:
            response_deadline = None
            response_remaining = None

        return SLAInfo(
            status=status,
            deadline=resolution_deadline,
            time_remaining=time_remaining if time_remaining.total_seconds() > 0 else None,
            time_elapsed=time_elapsed,
            response_deadline=response_deadline,
            response_remaining=response_remaining if response_remaining and response_remaining.total_seconds() > 0 else None,
            warnings=warnings,
        )

    def _log_sla_event(
        self,
        dispute_id: str,
        event_type: TimelineEventType,
    ) -> None:
        """Log SLA event (deduplicated)."""
        # Check if we already logged this event recently
        recent_events = self.get_timeline(
            dispute_id,
            event_types=[event_type],
            since=datetime.now(timezone.utc) - timedelta(hours=1),
            limit=1,
        )
        if not recent_events:
            self.add_event(
                dispute_id=dispute_id,
                event_type=event_type,
                description=f"SLA event: {event_type.value}",
                is_system=True,
            )

    def record_dispute_opened(
        self,
        dispute: Dispute,
    ) -> TimelineEvent:
        """
        Record dispute opening event.

        Args:
            dispute: The opened dispute

        Returns:
            Created TimelineEvent
        """
        return self.add_event(
            dispute_id=dispute.id,
            event_type=TimelineEventType.DISPUTE_OPENED,
            description=f"Dispute opened by {dispute.initiator_party.value}: {dispute.reason.value}",
            actor_id=dispute.initiator_id,
            data={
                "reason": dispute.reason.value,
                "amount": float(dispute.amount_disputed),
                "task_id": dispute.task_id,
            },
        )

    def record_response_added(
        self,
        dispute_id: str,
        responder_id: str,
        response_id: str,
        party: str,
    ) -> TimelineEvent:
        """
        Record response added event.

        Args:
            dispute_id: Dispute ID
            responder_id: Who responded
            response_id: Response ID
            party: Party (worker/agent)

        Returns:
            Created TimelineEvent
        """
        return self.add_event(
            dispute_id=dispute_id,
            event_type=TimelineEventType.RESPONSE_ADDED,
            description=f"Response added by {party}",
            actor_id=responder_id,
            data={"response_id": response_id},
        )

    def record_evidence_attached(
        self,
        dispute_id: str,
        submitter_id: str,
        evidence_id: str,
        party: str,
        file_type: str,
    ) -> TimelineEvent:
        """
        Record evidence attachment event.

        Args:
            dispute_id: Dispute ID
            submitter_id: Who submitted
            evidence_id: Evidence ID
            party: Party (worker/agent)
            file_type: Type of evidence file

        Returns:
            Created TimelineEvent
        """
        return self.add_event(
            dispute_id=dispute_id,
            event_type=TimelineEventType.EVIDENCE_ATTACHED,
            description=f"Evidence attached by {party}: {file_type}",
            actor_id=submitter_id,
            data={
                "evidence_id": evidence_id,
                "file_type": file_type,
            },
        )

    def record_status_change(
        self,
        dispute_id: str,
        old_status: DisputeStatus,
        new_status: DisputeStatus,
        actor_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> TimelineEvent:
        """
        Record status change event.

        Args:
            dispute_id: Dispute ID
            old_status: Previous status
            new_status: New status
            actor_id: Who changed status
            reason: Reason for change

        Returns:
            Created TimelineEvent
        """
        description = f"Status changed: {old_status.value} -> {new_status.value}"
        if reason:
            description += f" ({reason})"

        return self.add_event(
            dispute_id=dispute_id,
            event_type=TimelineEventType.STATUS_CHANGED,
            description=description,
            actor_id=actor_id,
            data={
                "old_status": old_status.value,
                "new_status": new_status.value,
                "reason": reason,
            },
        )

    def record_resolution(
        self,
        dispute: Dispute,
        resolved_by: str,
    ) -> TimelineEvent:
        """
        Record dispute resolution event.

        Args:
            dispute: Resolved dispute
            resolved_by: Who resolved

        Returns:
            Created TimelineEvent
        """
        resolution = dispute.resolution
        winner = resolution.winner.value if resolution and resolution.winner else "none"

        return self.add_event(
            dispute_id=dispute.id,
            event_type=TimelineEventType.DISPUTE_RESOLVED,
            description=f"Dispute resolved in favor of {winner}",
            actor_id=resolved_by,
            data={
                "winner": winner,
                "worker_payout_pct": float(resolution.worker_payout_pct) if resolution else 0,
                "resolution_type": resolution.resolution_type.value if resolution else None,
            },
        )

    def get_statistics(self, dispute_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get timeline statistics.

        Args:
            dispute_id: Optional dispute to filter by

        Returns:
            Dict with statistics
        """
        if dispute_id:
            events = self._events.get(dispute_id, [])
        else:
            events = [e for evts in self._events.values() for e in evts]

        # Count by type
        by_type: Dict[str, int] = {}
        for e in events:
            etype = e.event_type.value
            by_type[etype] = by_type.get(etype, 0) + 1

        # Count system vs user events
        system_count = sum(1 for e in events if e.is_system)

        return {
            "total_events": len(events),
            "by_type": by_type,
            "system_events": system_count,
            "user_events": len(events) - system_count,
            "disputes_tracked": len(self._events),
        }


# Module-level singleton
_default_manager: Optional[TimelineManager] = None


def get_timeline_manager(
    sla_hours: int = 168,
    response_hours: int = 72,
) -> TimelineManager:
    """
    Get or create the default TimelineManager instance.

    Args:
        sla_hours: Hours for resolution SLA
        response_hours: Hours for response window

    Returns:
        TimelineManager singleton instance
    """
    global _default_manager
    if _default_manager is None:
        _default_manager = TimelineManager(sla_hours, response_hours)
    return _default_manager


def reset_manager() -> None:
    """Reset the singleton manager (for testing)."""
    global _default_manager
    _default_manager = None


# Convenience functions

def add_event(
    dispute_id: str,
    event_type: TimelineEventType,
    description: str,
    actor_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> TimelineEvent:
    """
    Convenience function to add a timeline event.

    See TimelineManager.add_event for full documentation.
    """
    manager = get_timeline_manager()
    return manager.add_event(
        dispute_id=dispute_id,
        event_type=event_type,
        description=description,
        actor_id=actor_id,
        data=data,
    )


def get_timeline(dispute_id: str, limit: int = 100) -> List[TimelineEvent]:
    """
    Convenience function to get timeline for a dispute.

    See TimelineManager.get_timeline for full documentation.
    """
    manager = get_timeline_manager()
    return manager.get_timeline(dispute_id, limit=limit)


def calculate_sla_status(dispute: Dispute) -> SLAInfo:
    """
    Convenience function to calculate SLA status.

    See TimelineManager.calculate_sla_status for full documentation.
    """
    manager = get_timeline_manager()
    return manager.calculate_sla_status(dispute)
