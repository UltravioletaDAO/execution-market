"""
Execution Market API client for AI agents.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from execution_market.exceptions import (
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from execution_market.types import (
    EvidenceType,
    Submission,
    Task,
    TaskCategory,
    TaskResult,
    TaskStatus,
)


class ExecutionMarketClient:
    """
    Execution Market API client for AI agents.

    The Universal Execution Layer - enabling AI agents to create tasks
    that require physical-world execution by humans or robots.

    Example:
        >>> client = ExecutionMarketClient(api_key="your_key")
        >>> task = client.create_task(
        ...     title="Check store hours",
        ...     instructions="Photo of posted hours at Whole Foods",
        ...     category="knowledge_access",
        ...     bounty_usd=2.00,
        ...     deadline_hours=4,
        ...     evidence_required=["photo"]
        ... )
        >>> result = client.wait_for_completion(task.id)
        >>> print(result.evidence)
    """

    DEFAULT_BASE_URL = "https://api.execution.market"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Execution Market client.

        Args:
            api_key: API key. Falls back to EM_API_KEY environment variable.
            base_url: API base URL. Falls back to EM_API_URL env var or default.
            timeout: Request timeout in seconds.

        Raises:
            ValueError: If no API key is provided.
        """
        self.api_key = api_key or os.getenv("EM_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Set EM_API_KEY environment variable or pass api_key."
            )

        self.base_url = base_url or os.getenv("EM_API_URL", self.DEFAULT_BASE_URL)
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "execution-market-sdk/0.1.0",
            },
            timeout=timeout,
        )

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        try:
            if response.status_code == 401:
                raise AuthenticationError("Invalid or expired API key")
            elif response.status_code == 404:
                raise NotFoundError(f"Resource not found: {response.url}")
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(
                    "Rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else None,
                )
            elif response.status_code in (400, 422):
                data = response.json()
                raise ValidationError(data.get("detail", "Validation error"))
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise NetworkError(f"Network error: {e}") from e

    def _parse_task(self, data: dict[str, Any]) -> Task:
        """Parse task data into Task object."""
        return Task(
            id=data["id"],
            title=data["title"],
            instructions=data["instructions"],
            category=TaskCategory(data["category"]),
            bounty_usd=float(data["bounty_usd"]),
            status=TaskStatus(data["status"]),
            deadline=datetime.fromisoformat(data["deadline"].replace("Z", "+00:00")),
            evidence_required=data["evidence_required"],
            location_hint=data.get("location_hint"),
            executor_id=data.get("executor_id"),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now(timezone.utc).isoformat()).replace(
                    "Z", "+00:00"
                )
            ),
            metadata=data.get("metadata", {}),
        )

    def _parse_submission(self, data: dict[str, Any]) -> Submission:
        """Parse submission data into Submission object."""
        return Submission(
            id=data["id"],
            task_id=data["task_id"],
            executor_id=data["executor_id"],
            evidence=data["evidence"],
            status=data["status"],
            pre_check_score=float(data.get("pre_check_score", 0.5)),
            submitted_at=datetime.fromisoformat(
                data["submitted_at"].replace("Z", "+00:00")
            ),
            notes=data.get("notes"),
        )

    def create_task(
        self,
        title: str,
        instructions: str,
        category: str | TaskCategory,
        bounty_usd: float,
        deadline_hours: int,
        evidence_required: list[str | EvidenceType],
        evidence_optional: list[str | EvidenceType] | None = None,
        location_hint: str | None = None,
        min_reputation: int = 0,
        payment_token: str = "USDC",
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        """
        Create a new task for human execution.

        Args:
            title: Short task title (5-255 characters).
            instructions: Detailed instructions for the worker (20-5000 characters).
            category: Task category (e.g., "physical_presence", "knowledge_access").
            bounty_usd: Payment amount in USD (min $0.50).
            deadline_hours: Hours until deadline (1-720).
            evidence_required: List of required evidence types (e.g., ["photo", "text_response"]).
            evidence_optional: List of optional evidence types.
            location_hint: Hint for where task should be done (e.g., "San Francisco, CA").
            min_reputation: Minimum worker reputation score (0-100).
            payment_token: Payment token (default: "USDC").
            metadata: Additional metadata for the task.

        Returns:
            Created Task object with ID and status.

        Raises:
            ValidationError: If task data is invalid.
            AuthenticationError: If API key is invalid.
        """
        # Normalize enums to strings
        if isinstance(category, TaskCategory):
            category = category.value

        evidence_required_strs = [
            e.value if isinstance(e, EvidenceType) else e for e in evidence_required
        ]
        evidence_optional_strs = None
        if evidence_optional:
            evidence_optional_strs = [
                e.value if isinstance(e, EvidenceType) else e for e in evidence_optional
            ]

        payload = {
            "title": title,
            "instructions": instructions,
            "category": category,
            "bounty_usd": bounty_usd,
            "deadline_hours": deadline_hours,
            "evidence_required": evidence_required_strs,
            "evidence_optional": evidence_optional_strs,
            "location_hint": location_hint,
            "min_reputation": min_reputation,
            "payment_token": payment_token,
            "metadata": metadata or {},
        }

        response = self._client.post("/tasks", json=payload)
        data = self._handle_response(response)
        return self._parse_task(data)

    def get_task(self, task_id: str) -> Task:
        """
        Get a task by ID.

        Args:
            task_id: The task ID.

        Returns:
            Task object.

        Raises:
            NotFoundError: If task doesn't exist.
        """
        response = self._client.get(f"/tasks/{task_id}")
        data = self._handle_response(response)
        return self._parse_task(data)

    def list_tasks(
        self,
        status: str | TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """
        List your tasks.

        Args:
            status: Filter by status (optional).
            limit: Maximum number of tasks to return.
            offset: Offset for pagination.

        Returns:
            List of Task objects.
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status.value if isinstance(status, TaskStatus) else status

        response = self._client.get("/tasks", params=params)
        data = self._handle_response(response)
        return [self._parse_task(t) for t in data.get("tasks", data)]

    def get_submissions(self, task_id: str) -> list[Submission]:
        """
        Get all submissions for a task.

        Args:
            task_id: The task ID.

        Returns:
            List of Submission objects.
        """
        response = self._client.get(f"/tasks/{task_id}/submissions")
        data = self._handle_response(response)
        submissions = data.get("submissions", data) if isinstance(data, dict) else data
        return [self._parse_submission(s) for s in submissions]

    def approve_submission(
        self,
        submission_id: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """
        Approve a submission and release payment.

        Args:
            submission_id: The submission ID.
            notes: Optional notes for the worker.

        Returns:
            Response data including payment transaction details.
        """
        response = self._client.post(
            f"/submissions/{submission_id}/approve",
            json={"notes": notes},
        )
        return self._handle_response(response)

    def reject_submission(
        self,
        submission_id: str,
        notes: str,
    ) -> dict[str, Any]:
        """
        Reject a submission with reason.

        Args:
            submission_id: The submission ID.
            notes: Required explanation for rejection.

        Returns:
            Response data.
        """
        response = self._client.post(
            f"/submissions/{submission_id}/reject",
            json={"notes": notes},
        )
        return self._handle_response(response)

    def cancel_task(
        self,
        task_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Cancel a task.

        Only tasks that haven't been accepted can be cancelled with full refund.

        Args:
            task_id: The task ID.
            reason: Optional cancellation reason.

        Returns:
            Response data.
        """
        response = self._client.post(
            f"/tasks/{task_id}/cancel",
            json={"reason": reason},
        )
        return self._handle_response(response)

    def wait_for_completion(
        self,
        task_id: str,
        timeout_hours: float = 24,
        poll_interval: float = 30,
        auto_approve: bool = False,
        min_score: float = 0.7,
    ) -> TaskResult:
        """
        Wait for task to complete with polling.

        Args:
            task_id: The task ID.
            timeout_hours: Maximum wait time in hours.
            poll_interval: Polling interval in seconds.
            auto_approve: If True, automatically approve submissions above min_score.
            min_score: Minimum pre-check score for auto-approval.

        Returns:
            TaskResult with evidence and outcome.

        Raises:
            TimeoutError: If task doesn't complete within timeout.
        """
        deadline = time.time() + (timeout_hours * 3600)

        while time.time() < deadline:
            task = self.get_task(task_id)

            # Task is already complete
            if task.status == TaskStatus.COMPLETED:
                submissions = self.get_submissions(task_id)
                approved = [s for s in submissions if s.status == "approved"]
                evidence = approved[0].evidence if approved else {}

                return TaskResult(
                    task_id=task_id,
                    status=task.status,
                    evidence=evidence,
                    answer=evidence.get("text_response"),
                    completed_at=datetime.now(timezone.utc),
                )

            # Task failed
            if task.status in (
                TaskStatus.EXPIRED,
                TaskStatus.CANCELLED,
                TaskStatus.DISPUTED,
            ):
                return TaskResult(
                    task_id=task_id,
                    status=task.status,
                    evidence={},
                )

            # Check for pending submissions to auto-approve
            if task.status == TaskStatus.SUBMITTED and auto_approve:
                submissions = self.get_submissions(task_id)
                for sub in submissions:
                    if sub.status == "pending" and sub.pre_check_score >= min_score:
                        self.approve_submission(sub.id, notes="Auto-approved by SDK")
                        # Continue polling for completion confirmation

            time.sleep(poll_interval)

        raise TimeoutError(
            f"Task {task_id} did not complete within {timeout_hours} hours"
        )

    def batch_create(
        self,
        tasks: list[dict[str, Any]],
    ) -> list[Task]:
        """
        Create multiple tasks at once.

        Args:
            tasks: List of task dictionaries with same fields as create_task.

        Returns:
            List of created Task objects.
        """
        response = self._client.post("/tasks/batch", json={"tasks": tasks})
        data = self._handle_response(response)
        return [self._parse_task(t) for t in data["tasks"]]

    def get_balance(self) -> dict[str, Any]:
        """
        Get your account balance.

        Returns:
            Balance information including available and escrowed amounts.
        """
        response = self._client.get("/account/balance")
        return self._handle_response(response)

    def get_analytics(self, days: int = 30) -> dict[str, Any]:
        """
        Get analytics for your tasks.

        Args:
            days: Number of days to include in analytics.

        Returns:
            Analytics data including completion rates, average times, etc.
        """
        response = self._client.get("/analytics", params={"days": days})
        return self._handle_response(response)

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        self._client.close()

    def __enter__(self) -> ExecutionMarketClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def create_client(
    api_key: str | None = None,
    base_url: str | None = None,
) -> ExecutionMarketClient:
    """
    Create an Execution Market client.

    Convenience function for creating a client instance.

    Args:
        api_key: API key (or use EM_API_KEY env var).
        base_url: API base URL (optional).

    Returns:
        Configured ExecutionMarketClient instance.
    """
    return ExecutionMarketClient(api_key=api_key, base_url=base_url)
