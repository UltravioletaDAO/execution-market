"""Route-level tests for the EVM balance gate on publish + assign (Task 1.4).

These exercise the gate *through the FastAPI route handlers* in
``api.routers.tasks`` (``create_task`` and ``assign_task_to_worker``), not the
``check_evm_balance_gate`` helper in isolation (that is covered by
``test_evm_balance.py::TestCheckEvmBalanceGate``). The point is to prove the
route wiring added for the human-hires-human onramp loop:

  * publish, short balance  -> 402 INSUFFICIENT_FUNDS + onramp payload.
  * publish, enough balance -> gate passed; execution reaches the x402 branch.
  * assign,  short balance  -> 402 BEFORE any DB state mutation (F-02 short-circuit
                               on the *no-escrow* path).
  * assign,  escrow_tx set  -> gate skipped; assignment proceeds to db.assign_task
                               (F-02: an already SDK-locked escrow is not re-gated).

Conventions (matching test_escrow_refund_ownership.py + test_evm_balance.py):
  * Minimal FastAPI app with only the tasks router; auth dependency overridden.
  * ``EM_MOONPAY_ENABLED`` toggled with ``monkeypatch.setenv`` (auto-reverted) —
    NEVER ``os.environ[...] =`` and NEVER ``importlib.reload`` (both leaked state
    across the suite in earlier rounds and broke CI).
  * ``get_evm_usdc_balance`` is mocked with ``patch(..., AsyncMock)`` at its source
    module (``integrations.evm.balance``) — the gate imports it from there at
    call time, so patching the source is what takes effect.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.payments


# A real 0x address (40 hex) so the gate's is_valid_evm_address() guard passes
# and the balance read is reached. A valid 0x..64 escrow tx hash for the
# skip-path test.
PUBLISHER_WALLET = "0x" + "11" * 20
ESCROW_TX = "0x" + "ab" * 32  # 0x + 64 hex
WORKER_WALLET = "0x" + "22" * 20
EXECUTOR_ID = "12345678-1234-1234-1234-1234567890ab"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def moonpay_enabled(monkeypatch):
    """Flip the MoonPay master switch ON and give the client deterministic test
    keys so the onramp builder returns a payload (not None).

    Keys are set on the imported module OBJECT (revertible) rather than via a
    dotted-string path, mirroring test_evm_balance.py::_moonpay_enabled — the
    string path can fail to resolve after another test reloads the client. The
    env flag is read live by both the route gate and _is_moonpay_enabled(), so
    setenv alone covers the switch.
    """
    import integrations.moonpay.client as mp_client

    monkeypatch.setenv("EM_MOONPAY_ENABLED", "true")
    monkeypatch.setattr(mp_client, "MOONPAY_SECRET_KEY", "sk_test_secret_route_gate")
    monkeypatch.setattr(mp_client, "MOONPAY_PUBLIC_KEY", "pk_test_public_route_gate")
    monkeypatch.setattr(mp_client, "MOONPAY_WIDGET_BASE_URL", "https://buy.moonpay.com")
    yield


def _wallet_auth():
    """An ERC-8128 wallet-authed agent (so is_valid_evm_address passes)."""
    auth = MagicMock()
    auth.agent_id = PUBLISHER_WALLET
    auth.wallet_address = PUBLISHER_WALLET
    auth.auth_method = "erc8128"
    auth.erc8004_registered = True
    return auth


class _FakeQueryResult:
    """Chainable Supabase query stub returning a fixed dataset."""

    def __init__(self, data=None):
        self.data = data if data is not None else []

    def select(self, *a, **kw):
        return self

    def eq(self, *a, **kw):
        return self

    def limit(self, *a, **kw):
        return self

    def single(self):
        return self

    def execute(self):
        return self


class _FakeTable:
    def __init__(self, data=None):
        self._data = data if data is not None else []

    def select(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def update(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def eq(self, *a, **kw):
        return _FakeQueryResult(self._data)

    def limit(self, *a, **kw):
        return _FakeQueryResult(self._data)


class _FakeClient:
    def __init__(self, tables=None):
        self._tables = tables or {}

    def table(self, name):
        return self._tables.get(name, _FakeTable())


def _tasks_app(auth):
    """Minimal app exposing the tasks router with the write-auth dep overridden."""
    from fastapi import FastAPI
    from api.routers.tasks import router
    from api.auth import verify_agent_auth_write

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[verify_agent_auth_write] = lambda: auth
    return app


def _client(app):
    from fastapi.testclient import TestClient

    try:
        return TestClient(app, raise_server_exceptions=False)
    except TypeError:
        pytest.skip("httpx/starlette TestClient incompatibility")


_VALID_CREATE_BODY = {
    "title": "Deliver a package across town",
    "instructions": "Pick up at the front desk and deliver to suite 200 by 5pm.",
    "category": "physical_presence",
    "bounty_usd": 10.0,
    "deadline_hours": 6,
    "evidence_required": ["photo"],
    "payment_network": "base",
    "payment_token": "USDC",
}


# ---------------------------------------------------------------------------
# create_task (publish) gate
# ---------------------------------------------------------------------------


class TestCreateTaskEvmGate:
    def test_short_balance_returns_402_with_onramp(self, moonpay_enabled):
        """Publisher wallet below the escrow hold amount -> 402 + onramp, and
        db.create_task is never reached (the gate runs before task creation)."""
        app = _tasks_app(_wallet_auth())

        mock_db = MagicMock()
        # If the gate leaks, these would be hit — assert they are NOT.
        mock_db.get_task_by_idempotency_key = AsyncMock(return_value=None)
        mock_db.create_task = AsyncMock(
            side_effect=AssertionError("db.create_task reached despite short balance")
        )

        with (
            patch("api.routers.tasks.db", mock_db),
            patch(
                "integrations.evm.balance.get_evm_usdc_balance",
                new=AsyncMock(return_value=Decimal("1")),
            ),
        ):
            resp = _client(app).post("/api/v1/tasks", json=_VALID_CREATE_BODY)

        assert resp.status_code == 402, resp.text
        body = resp.json()
        assert body["error"] == "INSUFFICIENT_FUNDS"
        assert body["network"] == "base"
        # F-01: gate asks for the BOUNTY (credit_card model — fee taken on-chain
        # at release), NOT bounty + 13% fee. Compare numerically: the value is
        # quantized to 6 USDC decimals ("10.000000"), so == "10" would be wrong.
        assert Decimal(body["required_usdc"]) == Decimal("10")
        assert Decimal(body["required_usdc"]) != Decimal("11.30")  # not bounty+fee
        assert Decimal(body["balance_usdc"]) == Decimal("1")
        # onramp payload present because MoonPay is enabled + keyed.
        assert body.get("onramp") is not None
        assert body["onramp"]["url"].startswith("https://buy.moonpay.com")
        mock_db.create_task.assert_not_called()

    def test_enough_balance_passes_gate_to_x402_branch(self, moonpay_enabled):
        """Publisher wallet at/above the hold amount -> gate passes; execution
        continues into the x402 payment branch (proven by a distinct 402 whose
        body is the x402 'Payment required' error, NOT the gate's
        INSUFFICIENT_FUNDS)."""
        app = _tasks_app(_wallet_auth())

        mock_db = MagicMock()
        mock_db.get_task_by_idempotency_key = AsyncMock(return_value=None)

        # Force the x402 verification to fail so the handler returns its own 402
        # immediately after the gate, without us mocking the whole create path.
        failed_payment = MagicMock()
        failed_payment.success = False
        failed_payment.error = "no x402 payment provided"

        with (
            patch("api.routers.tasks.db", mock_db),
            patch("api.routers.tasks.X402_AVAILABLE", True),
            patch("api.routers.tasks.get_payment_dispatcher", return_value=None),
            patch(
                "api.routers.tasks.verify_x402_payment",
                new=AsyncMock(return_value=failed_payment),
            ),
            patch(
                "integrations.evm.balance.get_evm_usdc_balance",
                new=AsyncMock(return_value=Decimal("250")),
            ),
        ):
            resp = _client(app).post("/api/v1/tasks", json=_VALID_CREATE_BODY)

        # Passed the balance gate; the x402 branch produced this 402.
        assert resp.status_code == 402, resp.text
        body = resp.json()
        assert body.get("error") != "INSUFFICIENT_FUNDS", (
            "balance gate fired even though the wallet held enough USDC"
        )
        assert body.get("error") == "Payment required"

    def test_gate_off_by_default_does_not_block(self):
        """With EM_MOONPAY_ENABLED unset (default OFF), the EVM gate is inert:
        a short balance must NOT produce an INSUFFICIENT_FUNDS 402 — the
        crypto-native flow and the rest of the suite are unaffected."""
        import os

        # Guard: this asserts default behavior, so the flag must not be ON.
        assert os.environ.get("EM_MOONPAY_ENABLED", "false").lower() not in (
            "1",
            "true",
            "yes",
        )

        app = _tasks_app(_wallet_auth())

        mock_db = MagicMock()
        mock_db.get_task_by_idempotency_key = AsyncMock(return_value=None)
        failed_payment = MagicMock()
        failed_payment.success = False
        failed_payment.error = "no x402 payment provided"

        # balanceOf would return 0 here, but the gate must never run.
        balance_spy = AsyncMock(return_value=Decimal("0"))

        with (
            patch("api.routers.tasks.db", mock_db),
            patch("api.routers.tasks.X402_AVAILABLE", True),
            patch("api.routers.tasks.get_payment_dispatcher", return_value=None),
            patch(
                "api.routers.tasks.verify_x402_payment",
                new=AsyncMock(return_value=failed_payment),
            ),
            patch("integrations.evm.balance.get_evm_usdc_balance", new=balance_spy),
        ):
            resp = _client(app).post("/api/v1/tasks", json=_VALID_CREATE_BODY)

        body = resp.json()
        assert body.get("error") != "INSUFFICIENT_FUNDS", (
            "EVM gate fired while MoonPay was disabled"
        )
        balance_spy.assert_not_awaited()


# ---------------------------------------------------------------------------
# assign_task_to_worker gate
# ---------------------------------------------------------------------------


class TestAssignTaskEvmGate:
    def test_short_balance_returns_402_before_db_mutation(self, moonpay_enabled):
        """No escrow_tx + short publisher balance -> 402 INSUFFICIENT_FUNDS and
        db.assign_task is NOT called (the gate runs before state mutation)."""
        app = _tasks_app(_wallet_auth())

        mock_db = MagicMock()
        mock_db.get_task = AsyncMock(
            return_value={
                "id": "task-1",
                "payment_network": "base",
                "bounty_usd": 10.0,
            }
        )
        # escrows lookup returns empty -> _escrow_already_locked stays False.
        mock_db.get_client.return_value = _FakeClient(
            tables={"escrows": _FakeTable(data=[])}
        )
        mock_db.assign_task = AsyncMock(
            side_effect=AssertionError("db.assign_task reached despite short balance")
        )

        with (
            patch("api.routers.tasks.db", mock_db),
            patch(
                "integrations.evm.balance.get_evm_usdc_balance",
                new=AsyncMock(return_value=Decimal("2")),
            ),
        ):
            resp = _client(app).post(
                f"/api/v1/tasks/{EXECUTOR_ID}/assign",
                json={"executor_id": EXECUTOR_ID},
            )

        assert resp.status_code == 402, resp.text
        body = resp.json()
        assert body["error"] == "INSUFFICIENT_FUNDS"
        # F-01: required hold is the bounty, not bounty + fee (quantized to 6dp).
        assert Decimal(body["required_usdc"]) == Decimal("10")
        mock_db.assign_task.assert_not_called()

    def test_escrow_tx_present_skips_gate_and_proceeds(self, moonpay_enabled):
        """An SDK-locked escrow (valid escrow_tx) skips the balance gate even
        when the wallet now reads short, and the assignment proceeds to
        db.assign_task (F-02)."""
        app = _tasks_app(_wallet_auth())

        mock_db = MagicMock()
        mock_db.get_task = AsyncMock(
            return_value={
                "id": "task-1",
                "payment_network": "base",
                "bounty_usd": 10.0,
            }
        )
        mock_db.get_client.return_value = _FakeClient(
            tables={"escrows": _FakeTable(data=[])}
        )
        mock_db.assign_task = AsyncMock(
            return_value={
                "task": {
                    "id": "task-1",
                    "payment_network": "base",
                    "bounty_usd": 10.0,
                },
                "executor": {"wallet_address": WORKER_WALLET},
            }
        )
        mock_db.update_task = AsyncMock(return_value={})

        # balanceOf would return ~0 (funds already in escrow); the gate must be
        # skipped because escrow_tx proves the lock.
        balance_spy = AsyncMock(return_value=Decimal("0"))

        with (
            patch("api.routers.tasks.db", mock_db),
            patch("integrations.evm.balance.get_evm_usdc_balance", new=balance_spy),
        ):
            resp = _client(app).post(
                f"/api/v1/tasks/{EXECUTOR_ID}/assign",
                json={"executor_id": EXECUTOR_ID, "escrow_tx": ESCROW_TX},
            )

        # Must not be rejected by the balance gate.
        assert resp.status_code != 402, resp.text
        if resp.status_code == 200:
            body = resp.json()
            assert body.get("error") != "INSUFFICIENT_FUNDS"
        # The assignment reached the DB mutation (gate skipped)...
        mock_db.assign_task.assert_awaited_once()
        # ...and the balance read was never performed.
        balance_spy.assert_not_awaited()
