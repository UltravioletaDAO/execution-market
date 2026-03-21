"""Custom exceptions for the Execution Market SDK."""

from __future__ import annotations

from typing import Any


class EMError(Exception):
    """Base exception for all EM SDK errors."""

    def __init__(self, message: str, status_code: int | None = None, details: dict[str, Any] | None = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class EMAuthError(EMError):
    """Raised on 401/403 — invalid or missing API key."""

    def __init__(self, message: str = "Authentication failed", details: dict[str, Any] | None = None):
        super().__init__(message, status_code=401, details=details)


class EMNotFoundError(EMError):
    """Raised on 404 — resource not found."""

    def __init__(self, message: str = "Resource not found", details: dict[str, Any] | None = None):
        super().__init__(message, status_code=404, details=details)


class EMValidationError(EMError):
    """Raised on 422 — request validation failed."""

    def __init__(self, message: str = "Validation error", details: dict[str, Any] | None = None):
        super().__init__(message, status_code=422, details=details)


class EMServerError(EMError):
    """Raised on 5xx — server-side error."""

    def __init__(self, message: str = "Server error", status_code: int = 500, details: dict[str, Any] | None = None):
        super().__init__(message, status_code=status_code, details=details)
