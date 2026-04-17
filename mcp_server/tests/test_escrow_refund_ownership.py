"""
P0-1: Ownership check on POST /api/v1/escrow/refund

Regression tests for the SaaS hardening hotfix where any authenticated agent
could refund any deposit_id. The endpoint now must:

- 404 when the escrow row does not exist
- 403 when the escrow belongs to a different agent_id
- Allow the owner through (may still 500 on downstream SDK in test mode)

Markers: security, payments (per mcp_server/pytest.ini).
"""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest


DEPOSIT_ID = "0x" + "ab" * 32  # 66 chars including 0x
OWNER_AGENT_ID = "agent-owner-001"
OTHER_AGENT_ID = "agent-intruder-002"


class _FakeQueryResult:
    """Chainable stub for Supabase query result."""

    def __init__(self, data=None):
        self.data = data or []

    def execute(self):
        return self

    def select(self, *a, **kw):
        return self

    def eq(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

    def single(self):
        return self


class _FakeTable:
    def __init__(self, data=None):
        self._data = data

    def select(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def eq(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def limit(self, *a, **kw):
        return _FakeQueryResult(self._data)


class _FakeClient:
    def __init__(self, tables=None):
        self._tables = tables or {}

    def table(self, name: str):
        return self._tables.get(name, _FakeTable())


def _build_app_with_override(mock_auth):
    """Build a minimal FastAPI app exposing the escrow router with auth override."""
    from fastapi import FastAPI
    from api.escrow import router
    from api.auth import verify_agent_auth_write

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_agent_auth_write] = lambda: mock_auth
    return app


@pytest.mark.security
@pytest.mark.payments
def test_refund_denied_for_non_owner():
    """P0-1: Agent B must not be able to refund agent A's escrow (403)."""
    from fastapi.testclient import TestClient

    # Caller is agent B, but escrow in DB is owned by agent A.
    caller_auth = MagicMock()
    caller_auth.agent_id = OTHER_AGENT_ID
    caller_auth.wallet_address = "0x" + "cd" * 20

    escrow_row = {"agent_id": OWNER_AGENT_ID, "status": "funded"}
    fake_client = _FakeClient(tables={"escrows": _FakeTable(data=[escrow_row])})

    app = _build_app_with_override(caller_auth)

    with (
        patch("api.escrow.X402_SDK_AVAILABLE", True),
        patch("api.escrow.db") as mock_db,
    ):
        mock_db.get_client.return_value = fake_client

        try:
            client = TestClient(app, raise_server_exceptions=False)
        except TypeError:
            pytest.skip("httpx/starlette TestClient incompatibility")

        resp = client.post(
            "/api/v1/escrow/refund",
            json={"deposit_id": DEPOSIT_ID},
        )

    assert resp.status_code == 403, (
        f"Expected 403 when non-owner tries to refund, got {resp.status_code}: {resp.text}"
    )
    assert "does not belong" in resp.json()["detail"].lower()


@pytest.mark.security
@pytest.mark.payments
def test_refund_allowed_for_owner():
    """P0-1: The owning agent reaches the SDK call path (not 403/404)."""
    from fastapi.testclient import TestClient

    caller_auth = MagicMock()
    caller_auth.agent_id = OWNER_AGENT_ID
    caller_auth.wallet_address = "0x" + "ab" * 20

    escrow_row = {"agent_id": OWNER_AGENT_ID, "status": "funded"}
    fake_client = _FakeClient(tables={"escrows": _FakeTable(data=[escrow_row])})

    # SDK stub — we only care that the ownership guard lets the call through.
    mock_sdk = MagicMock()
    mock_sdk.refund_task_payment = AsyncMock(
        return_value={
            "success": True,
            "tx_hash": "0x" + "ef" * 32,
            "method": "facilitator",
            "payer": "0x" + "ab" * 20,
            "amount": "1.00",
        }
    )

    app = _build_app_with_override(caller_auth)

    with (
        patch("api.escrow.X402_SDK_AVAILABLE", True),
        patch("api.escrow.db") as mock_db,
        patch("api.escrow.get_sdk", return_value=mock_sdk),
    ):
        mock_db.get_client.return_value = fake_client

        try:
            client = TestClient(app, raise_server_exceptions=False)
        except TypeError:
            pytest.skip("httpx/starlette TestClient incompatibility")

        resp = client.post(
            "/api/v1/escrow/refund",
            json={"deposit_id": DEPOSIT_ID},
        )

    # Owner must not be rejected by the ownership guard.
    assert resp.status_code not in (403, 404), (
        f"Owner request must not be blocked by ownership guard, got {resp.status_code}: {resp.text}"
    )
    # 200 on happy path, 500 acceptable if SDK mock interop fails in test runtime.
    assert resp.status_code in (200, 500), (
        f"Unexpected status for owner refund: {resp.status_code}: {resp.text}"
    )
