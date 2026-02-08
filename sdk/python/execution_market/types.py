"""
Type definitions for Execution Market SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    """Task status values."""
    PUBLISHED = "published"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskCategory(str, Enum):
    """Task categories."""
    PHYSICAL_PRESENCE = "physical_presence"
    KNOWLEDGE_ACCESS = "knowledge_access"
    HUMAN_AUTHORITY = "human_authority"
    SIMPLE_ACTION = "simple_action"
    DIGITAL_PHYSICAL = "digital_physical"


class EvidenceType(str, Enum):
    """Evidence types."""
    PHOTO = "photo"
    PHOTO_GEO = "photo_geo"
    VIDEO = "video"
    DOCUMENT = "document"
    SIGNATURE = "signature"
    TEXT_RESPONSE = "text_response"


@dataclass
class Task:
    """Execution Market task."""

    id: str
    title: str
    instructions: str
    category: TaskCategory
    bounty_usd: float
    status: TaskStatus
    deadline: datetime
    evidence_required: list[str]
    location_hint: str | None = None
    executor_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if task is still active (can be worked on)."""
        return self.status in (
            TaskStatus.PUBLISHED,
            TaskStatus.ACCEPTED,
            TaskStatus.IN_PROGRESS,
        )

    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.EXPIRED,
            TaskStatus.CANCELLED,
        )


@dataclass
class Submission:
    """Task submission from a worker."""

    id: str
    task_id: str
    executor_id: str
    evidence: dict[str, Any]
    status: str
    pre_check_score: float
    submitted_at: datetime
    notes: str | None = None

    def is_approved(self) -> bool:
        """Check if submission was approved."""
        return self.status == "approved"

    def is_pending(self) -> bool:
        """Check if submission is pending review."""
        return self.status == "pending"


@dataclass
class TaskResult:
    """Completed task result."""

    task_id: str
    status: TaskStatus
    evidence: dict[str, Any]
    answer: str | None = None
    completed_at: datetime | None = None
    payment_tx: str | None = None

    @property
    def succeeded(self) -> bool:
        """Check if task completed successfully."""
        return self.status == TaskStatus.COMPLETED

    @property
    def failed(self) -> bool:
        """Check if task failed (expired, cancelled, disputed)."""
        return self.status in (
            TaskStatus.EXPIRED,
            TaskStatus.CANCELLED,
            TaskStatus.DISPUTED,
        )
