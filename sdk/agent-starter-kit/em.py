"""
Execution Market Agent Starter Kit (Python)

Thin async facade over `execution_market.OwsEM8128Client` — the canonical
ERC-8128 wallet signer that shells out to the Open Wallet Standard (OWS)
CLI. The private key NEVER leaves the OWS vault.

This kit is the smallest "hello world" client: it owns one `OwsEM8128Client`
and exposes a handful of typed convenience methods (create_task, get_task,
wait_for_completion, approve/reject submission, cancel_task). For anything
beyond that, drop down to the signer directly with `client._ows.post(...)`
or use the full SDK in `sdk/python/`.

Auth model: ERC-8128 wallet signing only. API-key auth was removed in v1.0.0
(see EM_API_KEYS_ENABLED=false in production). There is no `EM_API_KEY` env
var fallback.

Example:
    >>> import asyncio
    >>> from em import ExecutionMarketClient
    >>>
    >>> async def main():
    ...     client = ExecutionMarketClient(
    ...         wallet_name="my-agent",
    ...         wallet_address="0xYOUR_EVM_ADDR",
    ...     )
    ...     task = await client.create_task(
    ...         title="Check store hours",
    ...         instructions="Photo of posted hours on the door",
    ...         category="knowledge_access",
    ...         bounty_usd=2.00,
    ...         deadline_hours=4,
    ...         evidence_required=["photo"],
    ...     )
    ...     result = await client.wait_for_completion(task.id)
    ...
    >>> asyncio.run(main())
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from execution_market import OwsEM8128Client, task_fingerprint, with_backoff


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


@dataclass
class Task:
    """Execution Market task."""
    id: str
    title: str
    instructions: str
    category: TaskCategory
    bounty_usd: float
    status: TaskStatus
    deadline: datetime
    evidence_required: List[str]
    location_hint: Optional[str] = None
    executor_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Submission:
    """Task submission."""
    id: str
    task_id: str
    executor_id: str
    evidence: Dict[str, Any]
    status: str
    pre_check_score: float
    submitted_at: datetime
    notes: Optional[str] = None


@dataclass
class TaskResult:
    """Completed task result."""
    task_id: str
    status: TaskStatus
    evidence: Dict[str, Any]
    answer: Optional[str] = None
    completed_at: Optional[datetime] = None
    payment_tx: Optional[str] = None


def _parse_task(data: Dict[str, Any]) -> Task:
    """Parse server task payload into a Task dataclass."""
    deadline_raw = data["deadline"]
    if isinstance(deadline_raw, str):
        deadline = datetime.fromisoformat(deadline_raw.replace("Z", "+00:00"))
    else:
        deadline = deadline_raw
    return Task(
        id=data["id"],
        title=data["title"],
        instructions=data["instructions"],
        category=TaskCategory(data["category"]),
        bounty_usd=float(data["bounty_usd"]),
        status=TaskStatus(data["status"]),
        deadline=deadline,
        evidence_required=data["evidence_required"],
        location_hint=data.get("location_hint"),
        executor_id=data.get("executor_id"),
        metadata=data.get("metadata", {}),
    )


def _parse_submission(data: Dict[str, Any]) -> Submission:
    """Parse server submission payload into a Submission dataclass."""
    submitted_raw = data["submitted_at"]
    if isinstance(submitted_raw, str):
        submitted_at = datetime.fromisoformat(submitted_raw.replace("Z", "+00:00"))
    else:
        submitted_at = submitted_raw
    return Submission(
        id=data["id"],
        task_id=data["task_id"],
        executor_id=data["executor_id"],
        evidence=data["evidence"],
        status=data["status"],
        pre_check_score=float(data.get("pre_check_score", 0.5)),
        submitted_at=submitted_at,
        notes=data.get("notes"),
    )


class ExecutionMarketClient:
    """
    Execution Market API client for AI agents (ERC-8128 wallet auth).

    Composition over inheritance: holds a single `OwsEM8128Client` and
    delegates every signed call to it. Every public method is `async` —
    the signer fetches a fresh nonce per call and shells out to `ows sign
    message`, so blocking the event loop would defeat the point.

    Args:
        wallet_name: Wallet name as shown by `ows wallet list`.
        wallet_address: The 0x... EVM address (same on every EVM chain).
        chain_id: EVM chain id of the task's payment_network (default 8453 = Base).
            This is part of the ERC-8128 keyid the server uses to resolve identity.
        api_url: API base URL (no trailing slash). Default: production.
        timeout: Reserved for future per-request override; currently unused
            because `OwsEM8128Client` owns its own httpx timeouts (180s for
            POST, 30s for GET) which are tuned for the signing round-trip.

    Example:
        >>> import asyncio
        >>> async def main():
        ...     client = ExecutionMarketClient(
        ...         wallet_name="my-agent",
        ...         wallet_address="0xYOUR_EVM_ADDR",
        ...         chain_id=8453,
        ...     )
        ...     task = await client.create_task(
        ...         title="Check if Walmart is open",
        ...         instructions="Photo of storefront showing open/closed status",
        ...         category="physical_presence",
        ...         bounty_usd=0.10,
        ...         deadline_hours=4,
        ...         evidence_required=["photo", "photo_geo"],
        ...         location_hint="Miami, FL",
        ...     )
        ...     result = await client.wait_for_completion(task.id, timeout_hours=4)
        ...
        >>> asyncio.run(main())
    """

    DEFAULT_BASE_URL = "https://api.execution.market"

    def __init__(
        self,
        wallet_name: str,
        wallet_address: str,
        chain_id: int = 8453,
        api_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize Execution Market client backed by OWS / ERC-8128.

        Args:
            wallet_name: Name as shown by `ows wallet list`.
            wallet_address: 42-char 0x... EVM address.
            chain_id: EVM chain id (default 8453 = Base).
            api_url: API base URL (no trailing slash).
            timeout: Reserved; see class docstring.
        """
        self._ows = OwsEM8128Client(
            wallet_name=wallet_name,
            wallet_address=wallet_address,
            chain_id=chain_id,
            api_url=api_url,
        )
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def wallet_name(self) -> str:
        return self._ows.wallet_name

    @property
    def wallet_address(self) -> str:
        return self._ows.wallet

    @property
    def chain_id(self) -> int:
        return self._ows.chain_id

    @property
    def base_url(self) -> str:
        return self._ows.api_url

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    async def create_task(
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
        **kwargs: Any,
    ) -> Task:
        """
        Create a new task.

        Sends `X-Idempotency-Key = task_fingerprint(body)` so retries after
        a timeout return the original task (with `X-Idempotent: true` on the
        server side) instead of producing a duplicate. The fingerprint
        deterministically hashes the identity-defining fields (title,
        instructions, location, bounty, deadline, evidence, payment_network)
        so this is safe to call multiple times with the same payload.

        Wrapped in `with_backoff` to ride out transient 429/5xx from the
        signed endpoint.

        Args:
            title: Short task title (5-255 chars).
            instructions: Detailed instructions (20-5000 chars).
            category: Task category.
            bounty_usd: Payment amount in USD.
            deadline_hours: Hours until deadline.
            evidence_required: Required evidence types.
            evidence_optional: Optional evidence types.
            location_hint: Location hint for workers.
            min_reputation: Minimum worker reputation (0-100).
            payment_token: Payment token (default USDC).
            **kwargs: Extra fields forwarded to the API body verbatim.

        Returns:
            Created Task object.
        """
        body: Dict[str, Any] = {
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
            **kwargs,
        }
        idem = task_fingerprint(body)
        data = await with_backoff(
            lambda: self._ows.post(
                "/api/v1/tasks",
                body,
                extra_headers={"X-Idempotency-Key": idem},
            )
        )
        return _parse_task(data)

    async def get_task(self, task_id: str) -> Task:
        """Get task by ID."""
        data = await with_backoff(lambda: self._ows.get(f"/api/v1/tasks/{task_id}"))
        return _parse_task(data)

    async def get_submissions(self, task_id: str) -> List[Submission]:
        """Get submissions for a task."""
        data = await with_backoff(
            lambda: self._ows.get(f"/api/v1/tasks/{task_id}/submissions")
        )
        # Server may return either a bare list or {"submissions": [...]}.
        items = data.get("submissions", data) if isinstance(data, dict) else data
        return [_parse_submission(s) for s in items]

    async def approve_submission(
        self,
        submission_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve a submission and release payment."""
        return await with_backoff(
            lambda: self._ows.post(
                f"/api/v1/submissions/{submission_id}/approve",
                {"notes": notes},
            )
        )

    async def reject_submission(
        self,
        submission_id: str,
        notes: str,
    ) -> Dict[str, Any]:
        """Reject a submission with a reason."""
        return await with_backoff(
            lambda: self._ows.post(
                f"/api/v1/submissions/{submission_id}/reject",
                {"notes": notes},
            )
        )

    async def cancel_task(
        self,
        task_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cancel a task."""
        return await with_backoff(
            lambda: self._ows.post(
                f"/api/v1/tasks/{task_id}/cancel",
                {"reason": reason},
            )
        )

    async def wait_for_completion(
        self,
        task_id: str,
        timeout_hours: float = 24,
        poll_interval: float = 30,
    ) -> TaskResult:
        """
        Wait for task to complete via signed-GET polling.

        Each poll is a signed `GET /api/v1/tasks/{id}` wrapped in `with_backoff`,
        so 429s from the rate-limited signed endpoint don't tear down the wait.

        Args:
            task_id: Task ID.
            timeout_hours: Maximum wait time in hours.
            poll_interval: Polling interval in seconds.

        Returns:
            TaskResult with evidence and outcome.
        """
        loop = asyncio.get_event_loop()
        deadline = loop.time() + (timeout_hours * 3600)

        while loop.time() < deadline:
            task = await self.get_task(task_id)

            if task.status == TaskStatus.COMPLETED:
                submissions = await self.get_submissions(task_id)
                approved = [s for s in submissions if s.status == "approved"]
                evidence = approved[0].evidence if approved else {}

                return TaskResult(
                    task_id=task_id,
                    status=task.status,
                    evidence=evidence,
                    answer=evidence.get("text_response"),
                    completed_at=datetime.now(timezone.utc),
                )

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

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Task {task_id} did not complete within {timeout_hours} hours")

    async def batch_create(
        self,
        tasks: List[Dict[str, Any]],
    ) -> List[Task]:
        """Create multiple tasks in one signed call."""
        data = await with_backoff(
            lambda: self._ows.post("/api/v1/tasks/batch", {"tasks": tasks})
        )
        return [_parse_task(t) for t in data["tasks"]]

    async def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get agent analytics."""
        return await with_backoff(
            lambda: self._ows.get(f"/api/v1/analytics?days={days}")
        )


# Convenience function — kept as a thin alias for the constructor.
def create_client(
    wallet_name: str,
    wallet_address: str,
    chain_id: int = 8453,
    api_url: str = ExecutionMarketClient.DEFAULT_BASE_URL,
) -> ExecutionMarketClient:
    """Create an Execution Market client backed by OWS / ERC-8128."""
    return ExecutionMarketClient(
        wallet_name=wallet_name,
        wallet_address=wallet_address,
        chain_id=chain_id,
        api_url=api_url,
    )
