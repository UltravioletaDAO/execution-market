"""
Execution Market SDK for Python

Simple client for AI agents to create and manage human tasks.
"""

import os
import time
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


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


class ExecutionMarketClient:
    """
    Execution Market API client for AI agents.

    Example:
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

    DEFAULT_BASE_URL = "https://api.execution.market"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize Execution Market client.

        Args:
            api_key: API key (or EXECUTION_MARKET_API_KEY env var)
            base_url: API base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("EXECUTION_MARKET_API_KEY")
        if not self.api_key:
            raise ValueError("API key required. Set EXECUTION_MARKET_API_KEY or pass api_key.")

        self.base_url = base_url or os.getenv("EXECUTION_MARKET_API_URL", self.DEFAULT_BASE_URL)
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=timeout
        )

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
            title: Short task title (5-255 chars)
            instructions: Detailed instructions (20-5000 chars)
            category: Task category
            bounty_usd: Payment amount in USD
            deadline_hours: Hours until deadline
            evidence_required: Required evidence types
            evidence_optional: Optional evidence types
            location_hint: Location hint for workers
            min_reputation: Minimum worker reputation (0-100)
            payment_token: Payment token (default USDC)

        Returns:
            Created Task object
        """
        response = self._client.post("/tasks", json={
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
        })
        response.raise_for_status()
        data = response.json()

        return Task(
            id=data["id"],
            title=data["title"],
            instructions=data["instructions"],
            category=TaskCategory(data["category"]),
            bounty_usd=data["bounty_usd"],
            status=TaskStatus(data["status"]),
            deadline=datetime.fromisoformat(data["deadline"]),
            evidence_required=data["evidence_required"],
            location_hint=data.get("location_hint")
        )

    def get_task(self, task_id: str) -> Task:
        """Get task by ID."""
        response = self._client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        data = response.json()

        return Task(
            id=data["id"],
            title=data["title"],
            instructions=data["instructions"],
            category=TaskCategory(data["category"]),
            bounty_usd=data["bounty_usd"],
            status=TaskStatus(data["status"]),
            deadline=datetime.fromisoformat(data["deadline"]),
            evidence_required=data["evidence_required"],
            location_hint=data.get("location_hint"),
            executor_id=data.get("executor_id")
        )

    def get_submissions(self, task_id: str) -> List[Submission]:
        """Get submissions for a task."""
        response = self._client.get(f"/tasks/{task_id}/submissions")
        response.raise_for_status()

        return [
            Submission(
                id=s["id"],
                task_id=s["task_id"],
                executor_id=s["executor_id"],
                evidence=s["evidence"],
                status=s["status"],
                pre_check_score=s.get("pre_check_score", 0.5),
                submitted_at=datetime.fromisoformat(s["submitted_at"]),
                notes=s.get("notes")
            )
            for s in response.json()
        ]

    def approve_submission(
        self,
        submission_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve a submission."""
        response = self._client.post(f"/submissions/{submission_id}/approve", json={
            "notes": notes
        })
        response.raise_for_status()
        return response.json()

    def reject_submission(
        self,
        submission_id: str,
        notes: str
    ) -> Dict[str, Any]:
        """Reject a submission."""
        response = self._client.post(f"/submissions/{submission_id}/reject", json={
            "notes": notes
        })
        response.raise_for_status()
        return response.json()

    def cancel_task(
        self,
        task_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a task."""
        response = self._client.post(f"/tasks/{task_id}/cancel", json={
            "reason": reason
        })
        response.raise_for_status()
        return response.json()

    def wait_for_completion(
        self,
        task_id: str,
        timeout_hours: float = 24,
        poll_interval: float = 30
    ) -> TaskResult:
        """
        Wait for task to complete.

        Args:
            task_id: Task ID
            timeout_hours: Maximum wait time in hours
            poll_interval: Polling interval in seconds

        Returns:
            TaskResult with evidence and outcome
        """
        deadline = time.time() + (timeout_hours * 3600)

        while time.time() < deadline:
            task = self.get_task(task_id)

            if task.status == TaskStatus.COMPLETED:
                submissions = self.get_submissions(task_id)
                approved = [s for s in submissions if s.status == "approved"]
                evidence = approved[0].evidence if approved else {}

                return TaskResult(
                    task_id=task_id,
                    status=task.status,
                    evidence=evidence,
                    answer=evidence.get("text_response"),
                    completed_at=datetime.now(timezone.utc)
                )

            if task.status in [TaskStatus.EXPIRED, TaskStatus.CANCELLED, TaskStatus.DISPUTED]:
                return TaskResult(
                    task_id=task_id,
                    status=task.status,
                    evidence={}
                )

            time.sleep(poll_interval)

        raise TimeoutError(f"Task {task_id} did not complete within {timeout_hours} hours")

    def batch_create(
        self,
        tasks: List[Dict[str, Any]]
    ) -> List[Task]:
        """Create multiple tasks at once."""
        response = self._client.post("/tasks/batch", json={"tasks": tasks})
        response.raise_for_status()

        return [
            Task(
                id=t["id"],
                title=t["title"],
                instructions=t["instructions"],
                category=TaskCategory(t["category"]),
                bounty_usd=t["bounty_usd"],
                status=TaskStatus(t["status"]),
                deadline=datetime.fromisoformat(t["deadline"]),
                evidence_required=t["evidence_required"],
                location_hint=t.get("location_hint")
            )
            for t in response.json()["tasks"]
        ]

    def get_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get agent analytics."""
        response = self._client.get("/analytics", params={"days": days})
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Convenience function
def create_client(api_key: Optional[str] = None) -> ExecutionMarketClient:
    """Create an Execution Market client."""
    return ExecutionMarketClient(api_key=api_key)
