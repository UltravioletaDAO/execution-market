"""Tasks resource — client.tasks.create(), .list(), .get(), etc."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..models import (
    CreateTaskParams,
    Task,
    TaskList,
    Application,
    ApplicationList,
    PaymentTimeline,
    PlatformConfig,
)
from ..pagination import PageIterator

if TYPE_CHECKING:
    from ..client import EMClient


class TasksResource:
    """Operations on tasks.

    Usage::

        task = await client.tasks.create(CreateTaskParams(...))
        task = await client.tasks.get("task-uuid")

        async for task in client.tasks.list(status="published"):
            print(task.title)
    """

    def __init__(self, client: EMClient) -> None:
        self._client = client

    async def create(self, params: CreateTaskParams) -> Task:
        """Publish a new task."""
        data = await self._client._request(
            "POST", "/tasks",
            json=params.model_dump(exclude_none=True),
        )
        return Task.model_validate(data)

    async def get(self, task_id: str) -> Task:
        """Get task details by ID."""
        data = await self._client._request("GET", f"/tasks/{task_id}")
        return Task.model_validate(data)

    def list(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        agent_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> PageIterator[Task]:
        """List tasks with auto-pagination.

        Returns an async iterator that fetches pages lazily::

            async for task in client.tasks.list(status="published"):
                print(task.title)

            # Or collect all at once
            all_tasks = await client.tasks.list(status="published").collect()
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if category:
            params["category"] = category
        if agent_id:
            params["agent_id"] = agent_id

        async def fetch(p: dict[str, Any]) -> dict[str, Any]:
            return await self._client._request("GET", "/tasks", params=p)

        return PageIterator(fetch, "tasks", Task, params, page_size=limit)

    async def list_page(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        agent_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> TaskList:
        """Get a single page of tasks (non-iterating)."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if category:
            params["category"] = category
        if agent_id:
            params["agent_id"] = agent_id
        data = await self._client._request("GET", "/tasks", params=params)
        return TaskList.model_validate(data)

    async def cancel(self, task_id: str, reason: str | None = None) -> dict[str, Any]:
        """Cancel a task."""
        body: dict[str, Any] = {}
        if reason:
            body["reason"] = reason
        return await self._client._request("POST", f"/tasks/{task_id}/cancel", json=body)

    async def assign(
        self,
        task_id: str,
        executor_id: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Assign a worker to a task."""
        body: dict[str, Any] = {"executor_id": executor_id}
        if notes:
            body["notes"] = notes
        return await self._client._request("POST", f"/tasks/{task_id}/assign", json=body)

    async def batch_create(
        self,
        tasks: list[dict[str, Any]],
        payment_token: str = "USDC",
    ) -> dict[str, Any]:
        """Create multiple tasks in a single request (max 50)."""
        return await self._client._request(
            "POST", "/tasks/batch",
            json={"tasks": tasks, "payment_token": payment_token},
        )

    # -- applications -------------------------------------------------------

    async def apply(
        self,
        task_id: str,
        executor_id: str,
        message: str | None = None,
    ) -> Application:
        """Apply to work on a task (worker operation)."""
        body: dict[str, Any] = {"executor_id": executor_id}
        if message:
            body["message"] = message
        data = await self._client._request("POST", f"/tasks/{task_id}/apply", json=body)
        return Application.model_validate(data)

    async def list_applications(self, task_id: str) -> ApplicationList:
        """List applications for a task."""
        data = await self._client._request("GET", f"/tasks/{task_id}/applications")
        return ApplicationList.model_validate(data)

    # -- payment info -------------------------------------------------------

    async def get_payment(self, task_id: str) -> PaymentTimeline:
        """Get payment status and timeline for a task."""
        data = await self._client._request("GET", f"/tasks/{task_id}/payment")
        return PaymentTimeline.model_validate(data)

    async def get_transactions(self, task_id: str) -> dict[str, Any]:
        """Get the full transaction history for a task."""
        return await self._client._request("GET", f"/tasks/{task_id}/transactions")

    # -- discovery ----------------------------------------------------------

    async def available(
        self,
        *,
        category: str | None = None,
        min_bounty: float | None = None,
        max_bounty: float | None = None,
        location: str | None = None,
        skills: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Browse available tasks (public, no auth required)."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category
        if min_bounty is not None:
            params["min_bounty"] = min_bounty
        if max_bounty is not None:
            params["max_bounty"] = max_bounty
        if location:
            params["location"] = location
        if skills:
            params["skills"] = ",".join(skills)
        return await self._client._request("GET", "/tasks/available", params=params)
