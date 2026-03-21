"""Resource-based API namespaces (Stripe pattern)."""

from .tasks import TasksResource
from .submissions import SubmissionsResource
from .workers import WorkersResource
from .reputation import ReputationResource
from .evidence import EvidenceResource
from .payments import PaymentsResource
from .webhooks import WebhooksResource
from .h2a import H2AResource, AgentsResource

__all__ = [
    "TasksResource",
    "SubmissionsResource",
    "WorkersResource",
    "ReputationResource",
    "EvidenceResource",
    "PaymentsResource",
    "WebhooksResource",
    "H2AResource",
    "AgentsResource",
]
