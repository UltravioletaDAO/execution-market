"""
Execution Market SDK for Python

Simple client for AI agents to create and manage execution tasks.
The Universal Execution Layer for AI agents — humans today, robots tomorrow.

Example:
    >>> from execution_market import ExecutionMarketClient
    >>> client = ExecutionMarketClient(
    ...     wallet_name="my-agent",
    ...     wallet_address="0xYOUR_EVM_ADDR",
    ... )
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
from execution_market._signer import (
    OwsEM8128Client,
    OwsSignError,
    task_fingerprint,
    with_backoff,
)

__version__ = "1.0.0"

__all__ = [
    # Client
    "ExecutionMarketClient",
    "create_client",
    # Signer (OWS / ERC-8128)
    "OwsEM8128Client",
    "OwsSignError",
    "task_fingerprint",
    "with_backoff",
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
