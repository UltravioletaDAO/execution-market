"""Mock client for testing SDK consumers without network calls.

Usage::

    from em_plugin_sdk.testing import MockEMClient

    async def test_my_agent():
        client = MockEMClient()

        # Override defaults
        client.tasks._create_response = {"id": "custom-id", ...}

        task = await client.tasks.create(params)
        assert task.id == "custom-id"
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

from ..models import (
    Application,
    ApplicationList,
    ApproveParams,
    CreateTaskParams,
    EvidenceUploadInfo,
    EvidenceVerifyResult,
    Executor,
    HealthResponse,
    PaymentTimeline,
    PlatformConfig,
    RejectParams,
    Submission,
    SubmissionList,
    SubmitEvidenceParams,
    Task,
    TaskList,
    AgentReputation,
    AgentIdentity,
    Webhook,
    WebhookList,
)


_NOW = "2026-01-01T00:00:00Z"

_TASK = {
    "id": "mock-task-001",
    "title": "Mock task",
    "status": "published",
    "category": "simple_action",
    "bounty_usd": 1.00,
    "deadline": _NOW,
    "created_at": _NOW,
    "agent_id": "mock-agent",
    "payment_network": "base",
    "payment_token": "USDC",
}

_SUBMISSION = {
    "id": "mock-sub-001",
    "task_id": "mock-task-001",
    "executor_id": "mock-exec-001",
    "status": "pending",
    "submitted_at": _NOW,
}

_APPLICATION = {
    "id": "mock-app-001",
    "task_id": "mock-task-001",
    "executor_id": "mock-exec-001",
    "status": "pending",
    "created_at": _NOW,
}

_EXECUTOR = {
    "id": "mock-exec-001",
    "wallet_address": "0x" + "ab" * 20,
    "name": "Mock Worker",
}


class _MockTasks:
    def __init__(self) -> None:
        self._create_response: dict[str, Any] = _TASK
        self._calls: list[tuple[str, Any]] = []

    async def create(self, params: CreateTaskParams) -> Task:
        self._calls.append(("create", params))
        return Task.model_validate(self._create_response)

    async def get(self, task_id: str) -> Task:
        self._calls.append(("get", task_id))
        return Task.model_validate({**self._create_response, "id": task_id})

    def list(self, **kwargs: Any) -> _MockPageIter:
        self._calls.append(("list", kwargs))
        return _MockPageIter([Task.model_validate(self._create_response)])

    async def list_page(self, **kwargs: Any) -> TaskList:
        self._calls.append(("list_page", kwargs))
        return TaskList(tasks=[Task.model_validate(self._create_response)], total=1, count=1, offset=0, has_more=False)

    async def cancel(self, task_id: str, reason: str | None = None) -> dict[str, Any]:
        self._calls.append(("cancel", task_id))
        return {"success": True, "message": "Cancelled"}

    async def assign(self, task_id: str, executor_id: str, notes: str | None = None) -> dict[str, Any]:
        self._calls.append(("assign", (task_id, executor_id)))
        return {"success": True, "message": "Assigned"}

    async def batch_create(self, tasks: list, payment_token: str = "USDC") -> dict[str, Any]:
        self._calls.append(("batch_create", len(tasks)))
        return {"created": len(tasks), "failed": 0, "tasks": [], "errors": [], "total_bounty": 0}

    async def apply(self, task_id: str, executor_id: str, message: str | None = None) -> Application:
        self._calls.append(("apply", (task_id, executor_id)))
        return Application.model_validate({**_APPLICATION, "task_id": task_id, "executor_id": executor_id})

    async def list_applications(self, task_id: str) -> ApplicationList:
        self._calls.append(("list_applications", task_id))
        return ApplicationList(applications=[Application.model_validate(_APPLICATION)], count=1)

    async def get_payment(self, task_id: str) -> PaymentTimeline:
        self._calls.append(("get_payment", task_id))
        return PaymentTimeline(task_id=task_id, status="pending", total_amount=1.0, released_amount=0.0)

    async def get_transactions(self, task_id: str) -> dict[str, Any]:
        self._calls.append(("get_transactions", task_id))
        return {"task_id": task_id, "transactions": [], "total_count": 0, "summary": {}}

    async def available(self, **kwargs: Any) -> dict[str, Any]:
        self._calls.append(("available", kwargs))
        return {"tasks": [self._create_response], "count": 1, "offset": 0, "filters_applied": {}}


class _MockSubmissions:
    def __init__(self) -> None:
        self._calls: list[tuple[str, Any]] = []

    async def list(self, task_id: str) -> SubmissionList:
        self._calls.append(("list", task_id))
        return SubmissionList(submissions=[Submission.model_validate(_SUBMISSION)], count=1)

    async def submit(self, task_id: str, params: SubmitEvidenceParams) -> Submission:
        self._calls.append(("submit", (task_id, params)))
        return Submission.model_validate({**_SUBMISSION, "task_id": task_id})

    async def approve(self, submission_id: str, params: ApproveParams | None = None) -> dict[str, Any]:
        self._calls.append(("approve", submission_id))
        return {"success": True, "message": "Approved"}

    async def reject(self, submission_id: str, params: RejectParams) -> dict[str, Any]:
        self._calls.append(("reject", submission_id))
        return {"success": True, "message": "Rejected"}

    async def request_more_info(self, submission_id: str, notes: str) -> dict[str, Any]:
        self._calls.append(("request_more_info", submission_id))
        return {"success": True, "message": "Info requested"}


class _MockWorkers:
    def __init__(self) -> None:
        self._calls: list[tuple[str, Any]] = []

    async def get(self, executor_id: str) -> Executor:
        self._calls.append(("get", executor_id))
        return Executor.model_validate({**_EXECUTOR, "id": executor_id})

    async def register(self, wallet_address: str, name: str | None = None, email: str | None = None) -> Executor:
        self._calls.append(("register", wallet_address))
        return Executor.model_validate({**_EXECUTOR, "wallet_address": wallet_address, "name": name or "Mock"})

    async def balance(self, wallet_address: str) -> dict[str, Any]:
        self._calls.append(("balance", wallet_address))
        return {"base": {"USDC": "10.00"}}

    async def payment_events(self, wallet_address: str, **kwargs: Any) -> dict[str, Any]:
        self._calls.append(("payment_events", wallet_address))
        return {"events": [], "total": 0}


class _MockPageIter:
    """Minimal async iterator for mock list results."""

    def __init__(self, items: list) -> None:
        self._items = list(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._items:
            raise StopAsyncIteration
        return self._items.pop(0)

    async def collect(self) -> list:
        return [item async for item in self]


class MockEMClient:
    """Drop-in mock for EMClient — no network calls.

    All resource methods track calls in ``resource._calls`` for assertions.

    Usage::

        client = MockEMClient()
        task = await client.tasks.create(params)
        assert client.tasks._calls[0] == ("create", params)
    """

    def __init__(self) -> None:
        self.tasks = _MockTasks()
        self.submissions = _MockSubmissions()
        self.workers = _MockWorkers()

    async def health(self) -> HealthResponse:
        return HealthResponse(status="ok", version="mock")

    async def config(self) -> PlatformConfig:
        return PlatformConfig(
            min_bounty_usd=0.01,
            max_bounty_usd=10000,
            supported_networks=["base"],
            supported_tokens=["USDC"],
            preferred_network="base",
            require_api_key=False,
        )

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> MockEMClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        pass
