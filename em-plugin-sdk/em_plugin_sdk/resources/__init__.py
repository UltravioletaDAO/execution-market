"""Resource-based API namespaces (Stripe pattern)."""

from .tasks import TasksResource
from .submissions import SubmissionsResource
from .workers import WorkersResource
from .reputation import ReputationResource
from .evidence import EvidenceResource
from .payments import PaymentsResource

__all__ = [
    "TasksResource",
    "SubmissionsResource",
    "WorkersResource",
    "ReputationResource",
    "EvidenceResource",
    "PaymentsResource",
]
