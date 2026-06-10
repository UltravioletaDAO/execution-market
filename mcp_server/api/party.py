"""
Universal Hiring Matrix — party matching helpers.

A *party* is anyone who can publish or execute a task. The canonical taxonomy
is :class:`models.PartyType` = ``{human, agent, robot}``. This module is the
single source of truth for the matching question — "may this executor take this
task?" — shared by every apply/accept path so the 3x3 matrix behaves identically
everywhere.

See ``docs/planning/MASTER_PLAN_UNIVERSAL_HIRING_MATRIX.md`` (Phase 3).
"""

from typing import Optional


def can_execute(
    executor_party: Optional[str], target_executor_type: Optional[str]
) -> bool:
    """Return True iff an executor of ``executor_party`` may take a task whose
    ``target_executor_type`` is given.

    Rule: ``any`` (or unset) target is open to all parties; otherwise the
    executor's party must equal the target party exactly.
    """
    if not target_executor_type or target_executor_type == "any":
        return True
    return executor_party == target_executor_type


def party_required_label(target_executor_type: Optional[str]) -> str:
    """Human-readable name of the party a task requires, for error messages."""
    if not target_executor_type or target_executor_type == "any":
        return "any party"
    return f"{target_executor_type} executors"
