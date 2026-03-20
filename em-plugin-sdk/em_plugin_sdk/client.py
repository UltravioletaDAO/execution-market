"""Async HTTP client for the Execution Market REST API."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from .exceptions import EMAuthError, EMError, EMNotFoundError, EMServerError, EMValidationError
from .models import (
    Application,
    ApplicationList,
    ApproveParams,
    CreateTaskParams,
    Executor,
    HealthResponse,
    RejectParams,
    Submission,
    SubmissionList,
    SubmitEvidenceParams,
    Task,
    TaskList,
)

DEFAULT_BASE_URL = "https://api.execution.market/api/v1"
DEFAULT_TIMEOUT = 30.0


class EMClient:
    """Async client for the Execution Market API.

    Usage::

        async with EMClient(api_key="em_...") as client:
            tasks = await client.list_tasks(status="published")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._external_client = http_client is not None
        self._client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._default_headers(),
        )
        if http_client is not None:
            self._client.headers.update(self._default_headers())

    def _default_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "em-plugin-sdk/0.1.0",
        }

    # -- lifecycle ----------------------------------------------------------

    async def __aenter__(self) -> EMClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if not self._external_client:
            await self._client.aclose()

    # -- request helpers ----------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        resp = await self._client.request(method, path, json=json, params=params)
        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: httpx.Response) -> Any:
        if resp.status_code == 401 or resp.status_code == 403:
            body = _safe_json(resp)
            raise EMAuthError(
                message=body.get("message", "Authentication failed"),
                details=body,
            )
        if resp.status_code == 404:
            body = _safe_json(resp)
            raise EMNotFoundError(
                message=body.get("message", "Not found"),
                details=body,
            )
        if resp.status_code == 422:
            body = _safe_json(resp)
            raise EMValidationError(
                message=body.get("message", "Validation error"),
                details=body,
            )
        if resp.status_code >= 500:
            body = _safe_json(resp)
            raise EMServerError(
                message=body.get("message", "Server error"),
                status_code=resp.status_code,
                details=body,
            )
        if resp.status_code >= 400:
            body = _safe_json(resp)
            raise EMError(
                message=body.get("message", f"HTTP {resp.status_code}"),
                status_code=resp.status_code,
                details=body,
            )
        if resp.status_code == 204:
            return None
        return resp.json()

    # -- health -------------------------------------------------------------

    async def health(self) -> HealthResponse:
        data = await self._request("GET", "/health")
        return HealthResponse.model_validate(data)

    # -- tasks --------------------------------------------------------------

    async def list_tasks(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
        agent_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> TaskList:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if category:
            params["category"] = category
        if agent_id:
            params["agent_id"] = agent_id
        data = await self._request("GET", "/tasks", params=params)
        return TaskList.model_validate(data)

    async def get_task(self, task_id: str) -> Task:
        data = await self._request("GET", f"/tasks/{task_id}")
        return Task.model_validate(data)

    async def publish_task(self, params: CreateTaskParams) -> Task:
        data = await self._request(
            "POST",
            "/tasks",
            json=params.model_dump(exclude_none=True),
        )
        return Task.model_validate(data)

    async def cancel_task(self, task_id: str, reason: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if reason:
            body["reason"] = reason
        return await self._request("POST", f"/tasks/{task_id}/cancel", json=body)

    # -- applications -------------------------------------------------------

    async def apply_to_task(
        self,
        task_id: str,
        executor_id: str,
        message: str | None = None,
    ) -> Application:
        body: dict[str, Any] = {"executor_id": executor_id}
        if message:
            body["message"] = message
        data = await self._request("POST", f"/tasks/{task_id}/apply", json=body)
        return Application.model_validate(data)

    async def list_applications(self, task_id: str) -> ApplicationList:
        data = await self._request("GET", f"/tasks/{task_id}/applications")
        return ApplicationList.model_validate(data)

    async def assign_task(
        self,
        task_id: str,
        executor_id: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"executor_id": executor_id}
        if notes:
            body["notes"] = notes
        return await self._request("POST", f"/tasks/{task_id}/assign", json=body)

    # -- submissions --------------------------------------------------------

    async def submit_evidence(
        self,
        task_id: str,
        params: SubmitEvidenceParams,
    ) -> Submission:
        data = await self._request(
            "POST",
            f"/tasks/{task_id}/submit",
            json=params.model_dump(exclude_none=True),
        )
        return Submission.model_validate(data)

    async def list_submissions(self, task_id: str) -> SubmissionList:
        data = await self._request("GET", f"/tasks/{task_id}/submissions")
        return SubmissionList.model_validate(data)

    async def approve_submission(
        self,
        submission_id: str,
        params: ApproveParams | None = None,
    ) -> dict[str, Any]:
        body = params.model_dump(exclude_none=True) if params else {}
        return await self._request(
            "POST",
            f"/submissions/{submission_id}/approve",
            json=body,
        )

    async def reject_submission(
        self,
        submission_id: str,
        params: RejectParams,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/submissions/{submission_id}/reject",
            json=params.model_dump(exclude_none=True),
        )

    # -- workers / executors ------------------------------------------------

    async def get_executor(self, executor_id: str) -> Executor:
        data = await self._request("GET", f"/workers/{executor_id}")
        return Executor.model_validate(data)

    async def register_worker(
        self,
        wallet_address: str,
        name: str | None = None,
        email: str | None = None,
    ) -> Executor:
        body: dict[str, Any] = {"wallet_address": wallet_address}
        if name:
            body["name"] = name
        if email:
            body["email"] = email
        data = await self._request("POST", "/workers/register", json=body)
        return Executor.model_validate(data)


def _safe_json(resp: httpx.Response) -> dict[str, Any]:
    try:
        return resp.json()
    except Exception:
        return {"message": resp.text or f"HTTP {resp.status_code}"}
