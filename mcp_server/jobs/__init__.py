"""
Execution Market Background Jobs

Scheduled and triggered jobs:
- Bounty escalation
- Task expiration & auto-refund
- Deadline monitoring
- Cleanup tasks
- Phase B orphan recovery (startup + periodic)
"""

from .task_expiration import run_task_expiration_loop
from .auto_payment import run_auto_payment_loop
from .phase_b_recovery import (
    recover_orphaned_phase_b,
    graceful_shutdown_phase_b,
    track_phase_b_task,
    inflight_count,
)

__all__ = [
    "run_task_expiration_loop",
    "run_auto_payment_loop",
    "recover_orphaned_phase_b",
    "graceful_shutdown_phase_b",
    "track_phase_b_task",
    "inflight_count",
]
