"""
Timestamp Verification

Validates that evidence was created within acceptable time windows.
"""

from datetime import datetime, timedelta, UTC
from dataclasses import dataclass
from typing import Optional


@dataclass
class TimestampResult:
    """Result of timestamp verification."""

    is_valid: bool
    photo_timestamp: Optional[datetime]
    submission_timestamp: datetime
    task_start: Optional[datetime]
    task_deadline: Optional[datetime]
    age_seconds: Optional[float]
    reason: Optional[str]

    @property
    def normalized_score(self) -> float:
        """Normalized score 0.0-1.0 where 1.0 = timestamp valid (passed).

        1.0 = valid and recent. Decays with age.
        0.0 = no timestamp, future timestamp, or outside task window.
        Proportional decay based on age relative to a 5-minute window.
        """
        if not self.is_valid:
            return 0.0
        if self.age_seconds is None:
            return 0.0  # No timestamp data
        # Valid -- score decays with age (fresher = better)
        # 0 seconds = 1.0, 300 seconds (5 min) = 0.7, older decays further
        max_ideal_age = 300.0  # 5 minutes
        if self.age_seconds <= 0:
            return 1.0
        decay = min(self.age_seconds / max_ideal_age, 1.0) * 0.3
        return round(max(0.5, 1.0 - decay), 4)


def check_timestamp(
    photo_timestamp: Optional[datetime],
    submission_timestamp: Optional[datetime] = None,
    task_start: Optional[datetime] = None,
    task_deadline: Optional[datetime] = None,
    max_age_minutes: int = 5,
    allow_future: bool = False,
) -> TimestampResult:
    """
    Verify that photo timestamp is valid for the task.

    Checks:
    1. Photo is not too old (max_age_minutes)
    2. Photo was taken after task started (if task_start provided)
    3. Photo was taken before deadline (if deadline provided)
    4. Photo is not from the future (unless allow_future)

    Args:
        photo_timestamp: Photo creation timestamp (from EXIF)
        submission_timestamp: When the submission was made (default: now)
        task_start: When the task was assigned/started
        task_deadline: Task deadline
        max_age_minutes: Maximum photo age in minutes
        allow_future: Allow timestamps slightly in the future (for timezone issues)

    Returns:
        TimestampResult with validation details
    """
    now = datetime.now(UTC)
    submission = submission_timestamp or now

    # Ensure all timestamps are timezone-aware
    if photo_timestamp and photo_timestamp.tzinfo is None:
        photo_timestamp = photo_timestamp.replace(tzinfo=UTC)
    if submission.tzinfo is None:
        submission = submission.replace(tzinfo=UTC)
    if task_start and task_start.tzinfo is None:
        task_start = task_start.replace(tzinfo=UTC)
    if task_deadline and task_deadline.tzinfo is None:
        task_deadline = task_deadline.replace(tzinfo=UTC)

    # No timestamp in photo
    if not photo_timestamp:
        return TimestampResult(
            is_valid=False,
            photo_timestamp=None,
            submission_timestamp=submission,
            task_start=task_start,
            task_deadline=task_deadline,
            age_seconds=None,
            reason="Photo does not contain timestamp metadata",
        )

    # Calculate age
    age = submission - photo_timestamp
    age_seconds = age.total_seconds()

    # Check for future timestamps
    if age_seconds < 0:
        # Allow small future offset for timezone issues (up to 5 minutes)
        if not allow_future or age_seconds < -300:
            return TimestampResult(
                is_valid=False,
                photo_timestamp=photo_timestamp,
                submission_timestamp=submission,
                task_start=task_start,
                task_deadline=task_deadline,
                age_seconds=age_seconds,
                reason=f"Photo timestamp is in the future by {abs(age_seconds):.0f} seconds",
            )

    # Check maximum age
    max_age_seconds = max_age_minutes * 60
    if age_seconds > max_age_seconds:
        return TimestampResult(
            is_valid=False,
            photo_timestamp=photo_timestamp,
            submission_timestamp=submission,
            task_start=task_start,
            task_deadline=task_deadline,
            age_seconds=age_seconds,
            reason=f"Photo is too old ({age_seconds / 60:.1f} minutes). Maximum allowed: {max_age_minutes} minutes",
        )

    # Check if photo was taken before task started
    if task_start and photo_timestamp < task_start:
        return TimestampResult(
            is_valid=False,
            photo_timestamp=photo_timestamp,
            submission_timestamp=submission,
            task_start=task_start,
            task_deadline=task_deadline,
            age_seconds=age_seconds,
            reason="Photo was taken before task was assigned",
        )

    # Check if photo was taken after deadline
    if task_deadline and photo_timestamp > task_deadline:
        return TimestampResult(
            is_valid=False,
            photo_timestamp=photo_timestamp,
            submission_timestamp=submission,
            task_start=task_start,
            task_deadline=task_deadline,
            age_seconds=age_seconds,
            reason="Photo was taken after task deadline",
        )

    return TimestampResult(
        is_valid=True,
        photo_timestamp=photo_timestamp,
        submission_timestamp=submission,
        task_start=task_start,
        task_deadline=task_deadline,
        age_seconds=age_seconds,
        reason=None,
    )


def validate_submission_window(
    submission_timestamp: datetime,
    task_assigned_at: datetime,
    task_deadline: datetime,
    grace_period_minutes: int = 5,
) -> tuple[bool, str]:
    """
    Validate that a submission is within the allowed time window.

    Args:
        submission_timestamp: When the submission was made
        task_assigned_at: When the task was assigned
        task_deadline: Task deadline
        grace_period_minutes: Grace period after deadline

    Returns:
        Tuple of (is_valid, reason)
    """
    # Ensure timezone awareness
    if submission_timestamp.tzinfo is None:
        submission_timestamp = submission_timestamp.replace(tzinfo=UTC)
    if task_assigned_at.tzinfo is None:
        task_assigned_at = task_assigned_at.replace(tzinfo=UTC)
    if task_deadline.tzinfo is None:
        task_deadline = task_deadline.replace(tzinfo=UTC)

    # Check if submitted before assignment
    if submission_timestamp < task_assigned_at:
        return False, "Submission timestamp is before task assignment"

    # Check deadline with grace period
    deadline_with_grace = task_deadline + timedelta(minutes=grace_period_minutes)
    if submission_timestamp > deadline_with_grace:
        return (
            False,
            f"Submission is past deadline (including {grace_period_minutes} minute grace period)",
        )

    return True, "Submission is within valid time window"
