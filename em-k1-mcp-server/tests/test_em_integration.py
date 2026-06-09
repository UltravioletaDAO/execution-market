"""Tests for the Execution Market integration tools.

We mock the EM REST API by passing a custom ``httpx.AsyncClient`` backed
by ``httpx.MockTransport``, so no real network call is ever made.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from em_k1_mcp.config import K1Config
from em_k1_mcp.tools.em_integration import EMClient


def _make_handler(captured: list, response_status: int, response_body: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(
            {
                "method": request.method,
                "url": str(request.url),
                "body": json.loads(request.content) if request.content else {},
            }
        )
        return httpx.Response(response_status, json=response_body)

    return handler


@pytest.fixture
def mock_http_client_factory():
    def factory(status: int, body: dict):
        captured: list = []
        transport = httpx.MockTransport(_make_handler(captured, status, body))
        client = httpx.AsyncClient(transport=transport, timeout=5.0)
        return client, captured

    return factory


# ---------------------------------------------------------------------------
# em_claim_task
# ---------------------------------------------------------------------------


async def test_claim_task_happy_path(config: K1Config, mock_http_client_factory):
    client, captured = mock_http_client_factory(
        201,
        {
            "application_id": "app_abc123",
            "status": "accepted",
            "task_id": "task_xyz",
        },
    )
    em_client = EMClient(
        api_url=config.em_api_url,
        worker_name=config.em_worker_name,
        wallet_key_path=config.em_wallet_key_path,
        http_client=client,
    )
    data = await em_client.claim_task(task_id="task_xyz", evidence_url="https://example.com/e.jpg")
    assert data["_ok"] is True
    assert data["application_id"] == "app_abc123"
    assert data["status"] == "accepted"

    assert len(captured) == 1
    req = captured[0]
    assert req["method"] == "POST"
    assert req["url"].endswith("/api/v1/tasks/task_xyz/applications")
    assert req["body"]["evidence_url"] == "https://example.com/e.jpg"
    assert req["body"]["worker_name"] == config.em_worker_name


async def test_claim_task_propagates_http_error(config: K1Config, mock_http_client_factory):
    client, _ = mock_http_client_factory(404, {"detail": "task not found"})
    em_client = EMClient(
        api_url=config.em_api_url,
        worker_name=config.em_worker_name,
        wallet_key_path=config.em_wallet_key_path,
        http_client=client,
    )
    data = await em_client.claim_task(task_id="missing", evidence_url="https://example.com/e.jpg")
    assert data["_ok"] is False
    assert data["_status_code"] == 404
    assert data["detail"] == "task not found"


# ---------------------------------------------------------------------------
# em_submit_evidence
# ---------------------------------------------------------------------------


async def test_submit_evidence_happy_path(
    config: K1Config, mock_http_client_factory, tmp_path: Path
):
    client, captured = mock_http_client_factory(
        200,
        {
            "submission_id": "sub_xyz789",
            "status": "submitted",
            "task_id": "task_xyz",
        },
    )
    em_client = EMClient(
        api_url=config.em_api_url,
        worker_name=config.em_worker_name,
        wallet_key_path=config.em_wallet_key_path,
        http_client=client,
    )
    photo = tmp_path / "frame.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-bytes")

    data = await em_client.submit_evidence(
        task_id="task_xyz",
        photo_path=str(photo),
        metadata={"gps": {"lat": 25.7, "lng": -80.2}, "captured_at": "2026-05-20T10:00:00Z"},
    )
    assert data["_ok"] is True
    assert data["submission_id"] == "sub_xyz789"

    assert len(captured) == 1
    req = captured[0]
    assert req["method"] == "POST"
    assert req["url"].endswith("/api/v1/tasks/task_xyz/submissions")
    assert req["body"]["photo_path"].endswith("frame.jpg")
    assert req["body"]["metadata"]["gps"]["lat"] == 25.7


# ---------------------------------------------------------------------------
# Tool registration — end-to-end via the FastMCP server
# ---------------------------------------------------------------------------


async def test_em_claim_task_tool_end_to_end(
    config: K1Config, mock_backend, mock_http_client_factory
):
    from mcp.server.fastmcp import FastMCP

    from em_k1_mcp.tools.em_integration import register_em_integration_tools

    client, captured = mock_http_client_factory(
        201,
        {
            "application_id": "app_42",
            "status": "accepted",
        },
    )
    em_client = EMClient(
        api_url=config.em_api_url,
        worker_name=config.em_worker_name,
        wallet_key_path=config.em_wallet_key_path,
        http_client=client,
    )

    mcp = FastMCP("em-k1-mcp-test")
    register_em_integration_tools(mcp, config, em_client=em_client)

    result = await mcp.call_tool(
        "em_claim_task",
        {"params": {"task_id": "task_xyz", "evidence_url": "https://example.com/e.jpg"}},
    )
    structured = _extract_structured(result)
    assert structured["ok"] is True
    assert structured["application_id"] == "app_42"
    assert structured["status"] == "accepted"
    assert len(captured) == 1


async def test_em_submit_evidence_missing_photo_fails_fast(
    config: K1Config, mock_http_client_factory
):
    from mcp.server.fastmcp import FastMCP

    from em_k1_mcp.tools.em_integration import register_em_integration_tools

    client, captured = mock_http_client_factory(200, {})
    em_client = EMClient(
        api_url=config.em_api_url,
        worker_name=config.em_worker_name,
        wallet_key_path=config.em_wallet_key_path,
        http_client=client,
    )

    mcp = FastMCP("em-k1-mcp-test")
    register_em_integration_tools(mcp, config, em_client=em_client)

    result = await mcp.call_tool(
        "em_submit_evidence",
        {
            "params": {
                "task_id": "task_xyz",
                "photo_path": "/nonexistent/path/to/photo.jpg",
                "metadata": {},
            }
        },
    )
    structured = _extract_structured(result)
    assert structured["ok"] is False
    assert "does not exist" in structured["message"]
    # We must NOT have made the HTTP call when the photo is missing.
    assert len(captured) == 0


# ---------------------------------------------------------------------------
# Helpers (duplicated from test_tools.py to keep the file self-contained)
# ---------------------------------------------------------------------------


def _extract_structured(result):
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured
    if isinstance(result, tuple) and len(result) == 2:
        _, structured = result
        if isinstance(structured, dict):
            return structured
    if isinstance(result, tuple):
        result = result[0]
    if isinstance(result, list):
        for block in result:
            data = getattr(block, "data", None)
            if isinstance(data, dict):
                return data
            text = getattr(block, "text", None)
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue
    raise AssertionError(f"Could not extract structured content from {result!r}")
