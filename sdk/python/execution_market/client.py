"""
Execution Market API client for AI agents.

Auth: ERC-8128 wallet signing via the Open Wallet Standard (OWS). The
private key never leaves the local OWS vault — this client owns an
`OwsEM8128Client` for signature production (composition pattern) and
issues HTTP calls with the resulting ERC-8128 headers attached.

API keys are no longer accepted by the backend; only ERC-8128 wallet
signatures are honored.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from execution_market._signer import OwsEM8128Client, task_fingerprint, with_backoff
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

    Authentication is ERC-8128 wallet signing via OWS; the wallet must
    already exist in the local OWS vault (see `ows wallet create` or
    `ows wallet import`).

    Example:
        >>> client = ExecutionMarketClient(
        ...     wallet_name="my-agent",
        ...     wallet_address="0xYOUR_EVM_ADDR",
        ... )
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
        wallet_name: str,
        wallet_address: str,
        chain_id: int = 8453,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Execution Market client.

        Args:
            wallet_name: OWS wallet name (see `ows wallet list`).
            wallet_address: EVM address `0x...` (same on every EVM chain).
                The keyid sent to the backend is always lowercased.
            chain_id: EVM chain id of the payment network (default 8453 = Base).
            base_url: API base URL. Falls back to EM_API_URL env var or default.
            timeout: Request timeout in seconds.

        Raises:
            ValueError: If wallet_name or wallet_address is missing.
        """
        if not wallet_name or not wallet_address:
            raise ValueError(
                "wallet_name and wallet_address required. "
                "Run `ows wallet list` to discover both."
            )

        self.base_url = (base_url or os.getenv("EM_API_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = timeout

        # Composition: own an OwsEM8128Client for signature production. We use
        # its `_sign_headers` primitive (rather than the high-level post/get
        # convenience methods) so this class can keep the legacy status-code
        # dispatch in `_handle_response()` — the convenience methods on the
        # signer return parsed JSON and would lose HTTP status visibility.
        self._ows = OwsEM8128Client(
            wallet_name=wallet_name,
            wallet_address=wallet_address,
            chain_id=chain_id,
            api_url=self.base_url,
        )
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"User-Agent": "execution-market-sdk/1.0.0"},
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Internal request helpers
    # ------------------------------------------------------------------

    def _sign(self, method: str, path: str, body: str | None = None) -> dict[str, str]:
        """Produce ERC-8128 auth headers for a request (sync wrapper)."""
        url = f"{self.base_url}{path}"
        return asyncio.run(self._ows._sign_headers(method, url, body))

    def _signed_get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        # Build the path with query string so the signature covers @query.
        if params:
            full_path = str(httpx.URL(path, params=params))
        else:
            full_path = path
        headers = self._sign("GET", full_path)
        return self._client.get(full_path, headers=headers)

    def _signed_post(
        self,
        path: str,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        body = json.dumps(json_body) if json_body is not None else None
        headers = self._sign("POST", path, body)
        headers["Content-Type"] = "application/json"
        if extra_headers:
            # extra_headers (e.g. X-Idempotency-Key) are NOT covered by the
            # ERC-8128 signature — adding them never invalidates it.
            headers.update(extra_headers)
        return self._client.post(path, content=body, headers=headers)

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response and raise appropriate exceptions."""
        try:
            if response.status_code == 401:
                raise AuthenticationError(
                    "Wallet signature rejected. Re-run wallet auth: confirm OWS "
                    "vault is unlocked, the wallet exists (`ows wallet list`), "
                    "and the chain_id matches your task's payment_network."
                )
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
            submitted_at=datetime.fromisoformat(data["submitted_at"].replace("Z", "+00:00")),
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

        The `X-Idempotency-Key` header is set to `task_fingerprint(body)` —
        a deterministic SHA-256 over the fields that define task identity.
        Retrying the same call after a network timeout produces the SAME
        key, so the backend dedupes against the original task instead of
        creating a duplicate. (A random UUID here would defeat dedupe.)

        Args:
            title: Short task title (5-255 characters).
            instructions: Detailed instructions for the worker (20-5000 characters).
            category: Task category (e.g., "physical_presence", "knowledge_access").
            bounty_usd: Payment amount in USD (min $0.01).
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
            AuthenticationError: If wallet signature is rejected.
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

        idempotency_key = task_fingerprint(payload)
        response = self._signed_post(
            "/tasks",
            json_body=payload,
            extra_headers={"X-Idempotency-Key": idempotency_key},
        )
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
        response = self._signed_get(f"/tasks/{task_id}")
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

        response = self._signed_get("/tasks", params=params)
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
        response = self._signed_get(f"/tasks/{task_id}/submissions")
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
        response = self._signed_post(
            f"/submissions/{submission_id}/approve",
            json_body={"notes": notes},
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
        response = self._signed_post(
            f"/submissions/{submission_id}/reject",
            json_body={"notes": notes},
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
        response = self._signed_post(
            f"/tasks/{task_id}/cancel",
            json_body={"reason": reason},
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

        Each poll is wrapped in `with_backoff` so transient 429s from the
        rate limiter don't break the loop.

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

        async def _get_task_async() -> Task:
            return self.get_task(task_id)

        while time.time() < deadline:
            task = asyncio.run(with_backoff(_get_task_async))

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

        raise TimeoutError(f"Task {task_id} did not complete within {timeout_hours} hours")

    def batch_create(
        self,
        tasks: list[dict[str, Any]],
    ) -> list[Task]:
        """
        Create multiple tasks at once.

        Each task in the batch gets its own per-task `X-Idempotency-Key`
        fingerprint, so an individual task in a retried batch dedupes
        independently of its siblings.

        Args:
            tasks: List of task dictionaries with same fields as create_task.

        Returns:
            List of created Task objects.
        """
        per_task_keys = [task_fingerprint(t) for t in tasks]
        response = self._signed_post(
            "/tasks/batch",
            json_body={"tasks": tasks, "idempotency_keys": per_task_keys},
        )
        data = self._handle_response(response)
        return [self._parse_task(t) for t in data["tasks"]]

    def get_balance(self) -> dict[str, Any]:
        """
        Get your account balance.

        Returns:
            Balance information including available and escrowed amounts.
        """
        response = self._signed_get("/account/balance")
        return self._handle_response(response)

    def get_analytics(self, days: int = 30) -> dict[str, Any]:
        """
        Get analytics for your tasks.

        Args:
            days: Number of days to include in analytics.

        Returns:
            Analytics data including completion rates, average times, etc.
        """
        response = self._signed_get("/analytics", params={"days": days})
        return self._handle_response(response)

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        self._client.close()

    def __enter__(self) -> ExecutionMarketClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


def create_client(
    wallet_name: str,
    wallet_address: str,
    chain_id: int = 8453,
    base_url: str = ExecutionMarketClient.DEFAULT_BASE_URL,
) -> ExecutionMarketClient:
    """
    Create an Execution Market client.

    Convenience function for creating a client instance.

    Args:
        wallet_name: OWS wallet name (see `ows wallet list`).
        wallet_address: EVM address `0x...`.
        chain_id: EVM chain id of the payment network (default 8453 = Base).
        base_url: API base URL (optional).

    Returns:
        Configured ExecutionMarketClient instance.
    """
    return ExecutionMarketClient(
        wallet_name=wallet_name,
        wallet_address=wallet_address,
        chain_id=chain_id,
        base_url=base_url,
    )
