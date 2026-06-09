"""Regression tests for GET /api/v1/agent-info.

Guards against the ImportError that returned HTTP 500 on every request to this
endpoint since it was introduced (misc.py imported a non-existent
`get_platform_config` from config.platform_config). The endpoint is advertised
publicly as the agent-card `dynamic_info` link, so a broken handler silently
degrades ERC-8004 agent discoverability.

See: docs/planning/MASTER_PLAN_FACILITATOR_REPUTATION_DIAGNOSIS_2026-06-05.md
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# mcp_server root on sys.path + bypass prod env guards BEFORE importing the router
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("TESTING", "true")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.routers.misc import router as misc_router  # noqa: E402

pytestmark = pytest.mark.core

_MISC_PY = Path(__file__).resolve().parent.parent / "api" / "routers" / "misc.py"


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(misc_router)
    return TestClient(app)


def test_agent_info_returns_200_not_500():
    """The endpoint must return 200 — it 500'd for months via a broken import.

    Exercises the real handler over HTTP (the pre-existing route-inventory test
    only checked registration, which is why the ImportError shipped undetected).
    """
    resp = _client().get("/api/v1/agent-info")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["name"] == "Execution Market"
    assert body["agent_id"] == 2106
    assert isinstance(body["payment"]["networks"], list)
    assert len(body["payment"]["networks"]) >= 1
    assert body["payment"]["fee_percent"] == 13
    assert "stats" in body


def test_misc_router_has_no_get_platform_config_reference():
    """Guard against reintroducing the non-existent `get_platform_config` symbol.

    config.platform_config exposes the async `PlatformConfig` class and
    `get_config`, never a sync `get_platform_config`. Importing it raises
    ImportError at request time (lazy in-body import, invisible to startup
    checks), which is exactly how this bug evaded CI.
    """
    source = _MISC_PY.read_text(encoding="utf-8")
    assert "get_platform_config" not in source, (
        "misc.py must not reference get_platform_config — the symbol does not "
        "exist in config.platform_config and 500'd /api/v1/agent-info. "
        "Use the async PlatformConfig API instead."
    )
