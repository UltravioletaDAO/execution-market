"""
Exception classes for Execution Market SDK.
"""

from __future__ import annotations


class ExecutionMarketError(Exception):
    """Base exception for all Execution Market errors."""

    pass


class AuthenticationError(ExecutionMarketError):
    """Raised when authentication fails (HTTP 401).

    Wallet signing failed: the ERC-8128 signature was rejected by the
    server. Typical causes — OWS vault locked, wallet not in the local
    vault, chain_id mismatch with the task's payment_network, or signing
    drift (e.g. clock skew). Re-run wallet auth (`ows wallet list`,
    confirm the wallet exists, retry).
    """

    pass


class ValidationError(ExecutionMarketError):
    """Raised when request validation fails (HTTP 400/422).
    
    This means the request data was invalid (e.g., missing required fields,
    invalid values, etc.).
    """

    pass


class NotFoundError(ExecutionMarketError):
    """Raised when a resource is not found (HTTP 404).
    
    This means the requested task, submission, or other resource doesn't exist.
    """

    pass


class RateLimitError(ExecutionMarketError):
    """Raised when rate limit is exceeded (HTTP 429).
    
    Attributes:
        retry_after: Seconds to wait before retrying (if provided by server).
    """

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class NetworkError(ExecutionMarketError):
    """Raised when a network error occurs.
    
    This includes connection errors, timeouts, and other transport-level issues.
    """

    pass


class TaskError(ExecutionMarketError):
    """Raised for task-specific errors.
    
    Examples: task already cancelled, task not in valid state for operation, etc.
    """

    pass
