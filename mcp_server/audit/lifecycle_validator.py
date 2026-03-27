"""Deterministic state machine that validates task status transitions."""

import logging

logger = logging.getLogger(__name__)

# Legal transitions: {from_status: {allowed_to_statuses}}
VALID_TRANSITIONS = {
    "published": {"accepted", "cancelled", "expired"},
    "accepted": {"in_progress", "cancelled"},
    "in_progress": {"submitted", "cancelled"},
    "submitted": {"verifying", "completed", "in_progress", "cancelled"},
    "verifying": {"completed", "in_progress", "disputed"},
    "completed": set(),  # Terminal
    "cancelled": set(),  # Terminal
    "expired": set(),  # Terminal
    "disputed": {"completed", "cancelled"},
}


def validate_transition(
    current_status: str, new_status: str, task_id: str = ""
) -> bool:
    """
    Check if a status transition is legal.
    Returns True if allowed, False if illegal.
    Logs AUDIT_ILLEGAL_TRANSITION on failure.
    """
    current = current_status.lower().strip()
    new = new_status.lower().strip()

    if current == new:
        return True  # No-op transitions are always OK

    allowed = VALID_TRANSITIONS.get(current, set())
    if new in allowed:
        return True

    from audit import audit_log

    audit_log(
        "AUDIT_ILLEGAL_TRANSITION",
        task_id=task_id,
        from_status=current,
        to_status=new,
        allowed=list(allowed),
        severity="CRITICAL",
    )
    logger.error(
        "ILLEGAL TRANSITION: task=%s from=%s to=%s (allowed: %s)",
        task_id,
        current,
        new,
        allowed,
    )
    return False
