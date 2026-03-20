"""Execution Market Plugin SDK — Python client for the EM REST API."""

from .client import EMClient
from .models import (
    Task,
    TaskStatus,
    TaskCategory,
    EvidenceType,
    Submission,
    Application,
    CreateTaskParams,
    SubmitEvidenceParams,
)
from .exceptions import (
    EMError,
    EMAuthError,
    EMNotFoundError,
    EMValidationError,
    EMServerError,
)

__version__ = "0.1.0"

__all__ = [
    "EMClient",
    "Task",
    "TaskStatus",
    "TaskCategory",
    "EvidenceType",
    "Submission",
    "Application",
    "CreateTaskParams",
    "SubmitEvidenceParams",
    "EMError",
    "EMAuthError",
    "EMNotFoundError",
    "EMValidationError",
    "EMServerError",
]
