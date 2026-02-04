"""
describe.net Seals Integration for Execution Market (NOW-166 to NOW-170)

Bidirectional reputation flow between Execution Market and describe.net:
- Execution Market task completions generate seals on describe.net
- describe.net seals influence Execution Market matching algorithms
- Workers can filter requesters by reputation seals

Seal Types:
- Worker Seals: SKILLFUL, RELIABLE, THOROUGH, ON_TIME
- Requester Seals: FAIR_EVALUATOR, CLEAR_INSTRUCTIONS, FAST_PAYMENT
- Fusion Badges: MASTER_WORKER (50+ tasks, 6+ months)
"""

from .seals import (
    WorkerSealType,
    RequesterSealType,
    BadgeType,
    Seal,
    Badge,
    SealCriteria,
    SealStatus,
)
from .client import DescribeNetClient, DescribeNetError
from .worker_seals import WorkerSealManager
from .requester_seals import RequesterSealManager
from .badges import BadgeManager, MasterWorkerCriteria

__all__ = [
    # Seal types
    "WorkerSealType",
    "RequesterSealType",
    "BadgeType",
    "Seal",
    "Badge",
    "SealCriteria",
    "SealStatus",
    # Managers
    "WorkerSealManager",
    "RequesterSealManager",
    "BadgeManager",
    "MasterWorkerCriteria",
    # Client
    "DescribeNetClient",
    "DescribeNetError",
]
