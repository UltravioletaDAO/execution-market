"""Execution Market integration tools.

Two tools that bridge the K1 into the Execution Market marketplace:

* ``em_claim_task`` — claim a published task as this worker.
* ``em_submit_evidence`` — submit completed work with evidence.

Both go through the public REST API at ``EM_API_URL``. Authentication uses
the OWS-encrypted keystore pointed to by ``EM_WALLET_KEY_PATH`` (signing
is handled outside this MCP server — we just pass through the signed
payload from the caller's context). Until OWS hand-off is wired, the
default keystore path is a placeholder and the integration runs in
``signature_pending`` mode against staging.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import FastMCP

from ..config import K1Config
from ..models import (
    ClaimTaskInput,
    ClaimTaskResult,
    SubmitEvidenceInput,
    SubmitEvidenceResult,
)

logger = logging.getLogger(__name__)


class EMClient:
    """Thin async wrapper around the EM REST API.

    Constructed once per server startup and reused across tool calls so we
    don't burn a TCP connection per request.
    """

    def __init__(
        self,
        api_url: str,
        worker_name: str,
        wallet_key_path: str,
        agent_id: str = "",
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.worker_name = worker_name
        self.wallet_key_path = wallet_key_path
        self.agent_id = agent_id
        self._http_client = http_client
        self._owns_client = http_client is None

    async def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
            self._owns_client = True
        return self._http_client

    async def aclose(self) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def claim_task(self, task_id: str, evidence_url: str) -> Dict[str, Any]:
        """Apply to + claim a task. POSTs ``/api/v1/tasks/{task_id}/applications``."""
        client = await self._client()
        body = {
            "worker_name": self.worker_name,
            "agent_id": self.agent_id or None,
            "evidence_url": evidence_url,
            "message": f"k1-executor claim via em-k1-mcp ({self.worker_name})",
        }
        # Strip Nones so we don't surprise the API with explicit nulls.
        body = {k: v for k, v in body.items() if v is not None}
        url = f"{self.api_url}/api/v1/tasks/{task_id}/applications"
        resp = await client.post(url, json=body)
        return self._parse_response(resp)

    async def submit_evidence(
        self,
        task_id: str,
        photo_path: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """POST evidence to ``/api/v1/tasks/{task_id}/submissions``.

        The actual image upload uses a presigned S3 URL in production —
        here we send the local path + metadata, and the backend resolves
        the upload step. This keeps the MCP tool simple while we wire the
        full S3 flow during hardware integration.
        """
        client = await self._client()
        body = {
            "worker_name": self.worker_name,
            "agent_id": self.agent_id or None,
            "photo_path": photo_path,
            "metadata": metadata,
        }
        body = {k: v for k, v in body.items() if v is not None}
        url = f"{self.api_url}/api/v1/tasks/{task_id}/submissions"
        resp = await client.post(url, json=body)
        return self._parse_response(resp)

    @staticmethod
    def _parse_response(resp: httpx.Response) -> Dict[str, Any]:
        try:
            data = resp.json()
        except ValueError:
            data = {"raw": resp.text}
        data["_status_code"] = resp.status_code
        data["_ok"] = 200 <= resp.status_code < 300
        return data


def register_em_integration_tools(
    mcp: FastMCP,
    config: K1Config,
    em_client: Optional[EMClient] = None,
) -> EMClient:
    """Attach ``em_claim_task`` and ``em_submit_evidence`` to ``mcp``.

    Returns the :class:`EMClient` instance so callers can close it on
    server shutdown.
    """
    if em_client is None:
        em_client = EMClient(
            api_url=config.em_api_url,
            worker_name=config.em_worker_name,
            wallet_key_path=config.em_wallet_key_path,
            agent_id=config.em_agent_id,
        )

    @mcp.tool(
        name="em_claim_task",
        annotations={
            "title": "Claim Execution Market Task",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_claim_task(params: ClaimTaskInput) -> ClaimTaskResult:
        """Apply to and claim a published Execution Market task as this K1.

        Args:
            params: ``task_id`` of an Execution Market task and
                ``evidence_url`` pointing to pre-uploaded evidence (e.g.
                S3/CloudFront/IPFS).

        Returns:
            :class:`ClaimTaskResult` with the resulting ``application_id``
            on success.
        """
        try:
            data = await em_client.claim_task(params.task_id, params.evidence_url)
        except httpx.HTTPError as exc:
            logger.exception("em_claim_task HTTP failure for task %s", params.task_id)
            return ClaimTaskResult(
                ok=False,
                task_id=params.task_id,
                message=f"HTTP error contacting Execution Market: {exc}",
            )
        return ClaimTaskResult(
            ok=bool(data.get("_ok")),
            task_id=params.task_id,
            application_id=data.get("application_id") or data.get("id"),
            status=data.get("status"),
            message=(
                f"Claimed task {params.task_id} (status={data.get('status')})."
                if data.get("_ok")
                else f"Claim failed (HTTP {data.get('_status_code')}): "
                f"{data.get('detail') or data.get('message') or data.get('raw')}"
            ),
        )

    @mcp.tool(
        name="em_submit_evidence",
        annotations={
            "title": "Submit Evidence for Task",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def em_submit_evidence(params: SubmitEvidenceInput) -> SubmitEvidenceResult:
        """Submit completed work with evidence for an Execution Market task.

        Args:
            params: ``task_id``, ``photo_path`` (path to the captured
                image on this machine — the backend handles the actual
                upload via a presigned S3 URL), and arbitrary
                ``metadata`` (GPS, sensor readings, timestamps).

        Returns:
            :class:`SubmitEvidenceResult` with the new ``submission_id``.
        """
        # Light pre-flight check — surface a clear error before contacting
        # the API if the file is obviously missing on this machine.
        photo = Path(params.photo_path)
        if not photo.exists():
            logger.warning("em_submit_evidence: photo_path %s does not exist", photo)
            return SubmitEvidenceResult(
                ok=False,
                task_id=params.task_id,
                message=(
                    f"photo_path {photo} does not exist on this machine. "
                    "Capture the frame first via k1_observe()."
                ),
            )

        try:
            data = await em_client.submit_evidence(
                task_id=params.task_id,
                photo_path=str(photo),
                metadata=params.metadata,
            )
        except httpx.HTTPError as exc:
            logger.exception("em_submit_evidence HTTP failure for task %s", params.task_id)
            return SubmitEvidenceResult(
                ok=False,
                task_id=params.task_id,
                message=f"HTTP error contacting Execution Market: {exc}",
            )
        return SubmitEvidenceResult(
            ok=bool(data.get("_ok")),
            task_id=params.task_id,
            submission_id=data.get("submission_id") or data.get("id"),
            status=data.get("status"),
            message=(
                f"Submitted evidence for task {params.task_id} (status={data.get('status')})."
                if data.get("_ok")
                else f"Submission failed (HTTP {data.get('_status_code')}): "
                f"{data.get('detail') or data.get('message') or data.get('raw')}"
            ),
        )

    return em_client
