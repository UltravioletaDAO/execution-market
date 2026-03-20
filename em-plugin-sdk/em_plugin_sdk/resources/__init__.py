"""Resource-based API namespaces (Stripe pattern)."""

from .tasks import TasksResource
from .submissions import SubmissionsResource
from .workers import WorkersResource

__all__ = ["TasksResource", "SubmissionsResource", "WorkersResource"]
