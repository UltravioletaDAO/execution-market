"""
Execution Market API client for CLI.

Provides a robust HTTP client wrapper with:
- Auth header injection
- Retry logic with exponential backoff
- Error handling
- Response validation
"""

import time
import logging
from typing import Optional, Dict, Any, List, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

from .config import get_api_key, get_api_url, get_executor_id


logger = logging.getLogger(__name__)


# Type variable for generic responses
T = TypeVar('T')


class TaskStatus(str, Enum):
    """Task status values."""
    PUBLISHED = "published"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TaskCategory(str, Enum):
    """Task categories."""
    PHYSICAL_PRESENCE = "physical_presence"
    KNOWLEDGE_ACCESS = "knowledge_access"
    HUMAN_AUTHORITY = "human_authority"
    SIMPLE_ACTION = "simple_action"
    DIGITAL_PHYSICAL = "digital_physical"


class EvidenceType(str, Enum):
    """Evidence types."""
    PHOTO = "photo"
    PHOTO_GEO = "photo_geo"
    VIDEO = "video"
    DOCUMENT = "document"
    SIGNATURE = "signature"
    TEXT_RESPONSE = "text_response"
    RECEIPT = "receipt"
    TIMESTAMP_PROOF = "timestamp_proof"


@dataclass
class APIError(Exception):
    """API error with details."""
    message: str
    status_code: int
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message} (HTTP {self.status_code})"
        return f"{self.message} (HTTP {self.status_code})"


@dataclass
class Task:
    """An Execution Market task."""
    id: str
    title: str
    instructions: str
    category: str
    bounty_usd: float
    status: str
    deadline: datetime
    evidence_required: List[str]
    evidence_optional: Optional[List[str]] = None
    location_hint: Optional[str] = None
    executor_id: Optional[str] = None
    created_at: Optional[datetime] = None
    agent_id: Optional[str] = None
    min_reputation: Optional[int] = None
    payment_token: str = "USDC"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from API response."""
        return cls(
            id=data["id"],
            title=data["title"],
            instructions=data["instructions"],
            category=data["category"],
            bounty_usd=data["bounty_usd"],
            status=data["status"],
            deadline=datetime.fromisoformat(data["deadline"].replace("Z", "+00:00")),
            evidence_required=data.get("evidence_required", []),
            evidence_optional=data.get("evidence_optional"),
            location_hint=data.get("location_hint"),
            executor_id=data.get("executor_id"),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")) if data.get("created_at") else None,
            agent_id=data.get("agent_id"),
            min_reputation=data.get("min_reputation"),
            payment_token=data.get("payment_token", "USDC")
        )


@dataclass
class Submission:
    """A task submission."""
    id: str
    task_id: str
    executor_id: str
    evidence: Dict[str, Any]
    status: str
    pre_check_score: float
    submitted_at: datetime
    notes: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Submission":
        """Create Submission from API response."""
        return cls(
            id=data["id"],
            task_id=data["task_id"],
            executor_id=data["executor_id"],
            evidence=data.get("evidence", {}),
            status=data["status"],
            pre_check_score=data.get("pre_check_score", 0.0),
            submitted_at=datetime.fromisoformat(data["submitted_at"].replace("Z", "+00:00")),
            notes=data.get("notes")
        )


@dataclass
class WalletBalance:
    """Wallet balance information."""
    available_usd: float
    pending_usd: float
    total_earned_usd: float
    total_withdrawn_usd: float
    token: str = "USDC"


@dataclass
class WithdrawResult:
    """Withdrawal result."""
    success: bool
    amount_usd: float
    tx_hash: Optional[str] = None
    destination: Optional[str] = None
    error: Optional[str] = None


class EMAPIClient:
    """
    Execution Market API client with retry logic and error handling.

    Example:
        >>> client = EMAPIClient()
        >>> tasks = client.list_tasks(status="published", limit=10)
        >>> for task in tasks:
        ...     print(f"{task.title}: ${task.bounty_usd}")
    """

    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0  # Initial delay in seconds
    RETRY_BACKOFF = 2.0  # Exponential backoff multiplier

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None
    ):
        """
        Initialize API client.

        Args:
            api_key: API key (default: from config/env)
            base_url: API base URL (default: from config/env)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key or get_api_key()
        self.base_url = base_url or get_api_url()
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else self.MAX_RETRIES

        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client

    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response, raising appropriate errors."""
        if response.status_code >= 400:
            try:
                error_data = response.json()
                raise APIError(
                    message=error_data.get("message", response.text),
                    status_code=response.status_code,
                    code=error_data.get("code"),
                    details=error_data.get("details")
                )
            except (ValueError, KeyError):
                raise APIError(
                    message=response.text or f"HTTP {response.status_code}",
                    status_code=response.status_code
                )

        if response.status_code == 204:
            return {}

        try:
            return response.json()
        except ValueError:
            return {}

    def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            **kwargs: Additional request arguments

        Returns:
            Response data

        Raises:
            APIError: On API errors after retries exhausted
        """
        last_error: Optional[Exception] = None
        delay = self.RETRY_DELAY

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(method, path, **kwargs)
                return self._handle_response(response)

            except httpx.TimeoutException as e:
                last_error = APIError(
                    message=f"Request timed out: {e}",
                    status_code=408
                )
            except httpx.ConnectError as e:
                last_error = APIError(
                    message=f"Connection failed: {e}",
                    status_code=503
                )
            except APIError as e:
                # Don't retry client errors (4xx)
                if 400 <= e.status_code < 500:
                    raise
                last_error = e

            # Wait before retrying
            if attempt < self.max_retries:
                logger.debug(f"Retry {attempt + 1}/{self.max_retries} after {delay}s")
                time.sleep(delay)
                delay *= self.RETRY_BACKOFF

        # Exhausted retries
        if last_error:
            raise last_error
        raise APIError(message="Request failed", status_code=500)

    # =========================================================================
    # Task Operations (Agent)
    # =========================================================================

    def list_tasks(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Task]:
        """
        List tasks.

        Args:
            status: Filter by status
            category: Filter by category
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of tasks
        """
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if category:
            params["category"] = category

        data = self._request_with_retry("GET", "/v1/tasks", params=params)

        return [Task.from_dict(t) for t in data.get("tasks", data.get("items", []))]

    def get_task(self, task_id: str) -> Task:
        """Get a task by ID."""
        data = self._request_with_retry("GET", f"/v1/tasks/{task_id}")
        return Task.from_dict(data)

    def create_task(
        self,
        title: str,
        instructions: str,
        category: str,
        bounty_usd: float,
        deadline_hours: int,
        evidence_required: List[str],
        evidence_optional: Optional[List[str]] = None,
        location_hint: Optional[str] = None,
        min_reputation: int = 0,
        payment_token: str = "USDC",
        **kwargs
    ) -> Task:
        """
        Create a new task.

        Args:
            title: Task title (5-255 chars)
            instructions: Detailed instructions (20-5000 chars)
            category: Task category
            bounty_usd: Payment amount in USD
            deadline_hours: Hours until deadline
            evidence_required: Required evidence types
            evidence_optional: Optional evidence types
            location_hint: Location hint for workers
            min_reputation: Minimum worker reputation
            payment_token: Payment token (default: USDC)

        Returns:
            Created task
        """
        payload = {
            "title": title,
            "instructions": instructions,
            "category": category,
            "bounty_usd": bounty_usd,
            "deadline_hours": deadline_hours,
            "evidence_required": evidence_required,
            "evidence_optional": evidence_optional,
            "location_hint": location_hint,
            "min_reputation": min_reputation,
            "payment_token": payment_token,
            **kwargs
        }

        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}

        data = self._request_with_retry("POST", "/v1/tasks", json=payload)
        return Task.from_dict(data)

    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Cancel a task."""
        payload = {}
        if reason:
            payload["reason"] = reason

        return self._request_with_retry(
            "POST",
            f"/v1/tasks/{task_id}/cancel",
            json=payload
        )

    def get_task_submissions(self, task_id: str) -> List[Submission]:
        """Get submissions for a task."""
        data = self._request_with_retry("GET", f"/v1/tasks/{task_id}/submissions")
        return [Submission.from_dict(s) for s in data.get("submissions", data.get("items", []))]

    def approve_submission(
        self,
        submission_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve a submission."""
        payload = {}
        if notes:
            payload["notes"] = notes

        return self._request_with_retry(
            "POST",
            f"/v1/submissions/{submission_id}/approve",
            json=payload
        )

    def reject_submission(
        self,
        submission_id: str,
        notes: str
    ) -> Dict[str, Any]:
        """Reject a submission."""
        return self._request_with_retry(
            "POST",
            f"/v1/submissions/{submission_id}/reject",
            json={"notes": notes}
        )

    # =========================================================================
    # Worker Operations
    # =========================================================================

    def list_available_tasks(
        self,
        category: Optional[str] = None,
        location: Optional[str] = None,
        min_bounty: Optional[float] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Task]:
        """
        List available tasks for workers.

        Args:
            category: Filter by category
            location: Filter by location
            min_bounty: Minimum bounty amount
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of available tasks
        """
        params = {
            "status": "published",
            "limit": limit,
            "offset": offset
        }
        if category:
            params["category"] = category
        if location:
            params["location"] = location
        if min_bounty:
            params["min_bounty"] = min_bounty

        data = self._request_with_retry("GET", "/v1/tasks/available", params=params)
        return [Task.from_dict(t) for t in data.get("tasks", data.get("items", []))]

    def apply_to_task(
        self,
        task_id: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply to a task as a worker.

        Args:
            task_id: Task to apply for
            message: Optional message to the agent

        Returns:
            Application result
        """
        executor_id = get_executor_id()
        if not executor_id:
            raise APIError(
                message="Executor ID not configured. Set EM_EXECUTOR_ID or run 'em login --worker'",
                status_code=400
            )

        payload = {"executor_id": executor_id}
        if message:
            payload["message"] = message

        return self._request_with_retry(
            "POST",
            f"/v1/tasks/{task_id}/apply",
            json=payload
        )

    def submit_evidence(
        self,
        task_id: str,
        evidence: Dict[str, Any],
        notes: Optional[str] = None
    ) -> Submission:
        """
        Submit evidence for a task.

        Args:
            task_id: Task ID
            evidence: Evidence dictionary
            notes: Optional notes

        Returns:
            Created submission
        """
        executor_id = get_executor_id()
        if not executor_id:
            raise APIError(
                message="Executor ID not configured. Set EM_EXECUTOR_ID or run 'em login --worker'",
                status_code=400
            )

        payload = {
            "executor_id": executor_id,
            "evidence": evidence
        }
        if notes:
            payload["notes"] = notes

        data = self._request_with_retry(
            "POST",
            f"/v1/tasks/{task_id}/submit",
            json=payload
        )
        return Submission.from_dict(data)

    def get_my_tasks(
        self,
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Task]:
        """Get tasks assigned to current worker."""
        executor_id = get_executor_id()
        if not executor_id:
            raise APIError(
                message="Executor ID not configured",
                status_code=400
            )

        params = {
            "executor_id": executor_id,
            "limit": limit
        }
        if status:
            params["status"] = status

        data = self._request_with_retry("GET", "/v1/worker/tasks", params=params)
        return [Task.from_dict(t) for t in data.get("tasks", data.get("items", []))]

    # =========================================================================
    # Wallet Operations
    # =========================================================================

    def get_wallet_balance(self) -> WalletBalance:
        """Get wallet balance for current user."""
        data = self._request_with_retry("GET", "/v1/wallet/balance")
        return WalletBalance(
            available_usd=data.get("available_usd", 0.0),
            pending_usd=data.get("pending_usd", 0.0),
            total_earned_usd=data.get("total_earned_usd", 0.0),
            total_withdrawn_usd=data.get("total_withdrawn_usd", 0.0),
            token=data.get("token", "USDC")
        )

    def withdraw(
        self,
        amount_usd: Optional[float] = None,
        destination: Optional[str] = None
    ) -> WithdrawResult:
        """
        Withdraw earnings.

        Args:
            amount_usd: Amount to withdraw (None = all available)
            destination: Destination wallet address

        Returns:
            Withdrawal result
        """
        payload = {}
        if amount_usd:
            payload["amount_usd"] = amount_usd
        if destination:
            payload["destination"] = destination

        data = self._request_with_retry("POST", "/v1/wallet/withdraw", json=payload)
        return WithdrawResult(
            success=data.get("success", False),
            amount_usd=data.get("amount_usd", 0.0),
            tx_hash=data.get("tx_hash"),
            destination=data.get("destination"),
            error=data.get("error")
        )

    def get_transactions(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get transaction history."""
        data = self._request_with_retry(
            "GET",
            "/v1/wallet/transactions",
            params={"limit": limit, "offset": offset}
        )
        return data.get("transactions", data.get("items", []))

    # =========================================================================
    # Analytics
    # =========================================================================

    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get analytics for the current user."""
        return self._request_with_retry(
            "GET",
            "/v1/analytics",
            params={"days": days}
        )

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "EMAPIClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()


# Global client instance
_client: Optional[EMAPIClient] = None


def get_client() -> EMAPIClient:
    """Get or create the global API client."""
    global _client
    if _client is None:
        _client = EMAPIClient()
    return _client


def reset_client() -> None:
    """Reset the global API client."""
    global _client
    if _client:
        _client.close()
    _client = None


