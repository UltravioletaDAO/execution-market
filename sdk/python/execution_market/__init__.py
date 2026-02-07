"""
Execution Market SDK for Python

Simple client for AI agents to create and manage human tasks.
The Human Execution Layer (HEL) for AI agents.

Example:
    >>> from execution_market import ExecutionMarketClient
    >>> client = ExecutionMarketClient(api_key="your_key")
    >>> task = client.create_task(
    ...     title="Check store hours",
    ...     instructions="Photo of posted hours",
    ...     category="knowledge_access",
    ...     bounty_usd=2.00,
    ...     deadline_hours=4,
    ...     evidence_required=["photo"]
    ... )
    >>> result = client.wait_for_completion(task.id)
"""

from execution_market.client import (
    ExecutionMarketClient,
    create_client,
)
from execution_market.types import (
    Task,
    Submission,
    TaskResult,
    TaskStatus,
    TaskCategory,
    EvidenceType,
)
from execution_market.exceptions import (
    ExecutionMarketError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    RateLimitError,
    NetworkError,
    TaskError,
)

__version__ = "0.1.0"

__all__ = [
    # Client
    "ExecutionMarketClient",
    "create_client",
    # Types
    "Task",
    "Submission", 
    "TaskResult",
    "TaskStatus",
    "TaskCategory",
    "EvidenceType",
    # Exceptions
    "ExecutionMarketError",
    "AuthenticationError",
    "ValidationError",
    "NotFoundError",
    "RateLimitError",
    "NetworkError",
    "TaskError",
]
