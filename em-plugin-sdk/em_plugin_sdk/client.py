"""Async HTTP client for the Execution Market REST API.

Resource-based namespacing (Stripe pattern)::

    async with EMClient(api_key="em_...") as client:
        # Tasks
        task = await client.tasks.create(CreateTaskParams(...))
        async for t in client.tasks.list(status="published"):
            print(t.title)

        # Submissions
        await client.submissions.approve("sub-uuid")

        # Workers
        worker = await client.workers.register(wallet_address="0x...")
"""

from __future__ import annotations

from typing import Any

import httpx

from .exceptions import EMAuthError, EMError, EMNotFoundError, EMServerError, EMValidationError
from .models import HealthResponse, PlatformConfig
from .resources.tasks import TasksResource
from .resources.submissions import SubmissionsResource
from .resources.workers import WorkersResource
from .resources.reputation import ReputationResource
from .resources.evidence import EvidenceResource
from .resources.payments import PaymentsResource
from .retry import request_with_retry, DEFAULT_MAX_RETRIES, DEFAULT_BACKOFF_FACTOR

DEFAULT_BASE_URL = "https://api.execution.market/api/v1"
DEFAULT_TIMEOUT = 30.0


class EMClient:
    """Async client for the Execution Market API.

    Args:
        api_key: API key for authentication. Optional for open-access endpoints.
        base_url: Base URL for the API.
        timeout: Request timeout in seconds.
        max_retries: Number of retries on transient failures (429, 5xx).
        http_client: Optional pre-configured httpx.AsyncClient.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._external_client = http_client is not None
        self._client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._default_headers(),
        )
        if http_client is not None:
            self._client.headers.update(self._default_headers())

        # Resource namespaces
        self.tasks = TasksResource(self)
        self.submissions = SubmissionsResource(self)
        self.workers = WorkersResource(self)
        self.reputation = ReputationResource(self)
        self.evidence = EvidenceResource(self)
        self.payments = PaymentsResource(self)

    def _default_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "em-plugin-sdk/0.2.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    # -- lifecycle ----------------------------------------------------------

    async def __aenter__(self) -> EMClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if not self._external_client:
            await self._client.aclose()

    # -- request core (used by resources) -----------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        resp = await request_with_retry(
            self._client,
            method,
            path,
            max_retries=self._max_retries,
            json=json,
            params=params,
        )
        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: httpx.Response) -> Any:
        if resp.status_code in (401, 403):
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

    # -- top-level endpoints ------------------------------------------------

    async def health(self) -> HealthResponse:
        """Check API health."""
        data = await self._request("GET", "/health")
        return HealthResponse.model_validate(data)

    async def config(self) -> PlatformConfig:
        """Get public platform configuration (bounty limits, networks, tokens)."""
        data = await self._request("GET", "/config")
        return PlatformConfig.model_validate(data)


def _safe_json(resp: httpx.Response) -> dict[str, Any]:
    try:
        return resp.json()
    except Exception:
        return {"message": resp.text or f"HTTP {resp.status_code}"}
