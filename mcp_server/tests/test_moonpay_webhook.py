"""Tests for the MoonPay webhook receiver + moonpay_transactions persistence (Phase 4.5).

Covers:
  - `_extract_moonpay_row()` projection from MoonPay's webhook payload onto
    the moonpay_transactions schema (handles nested/flat currency code,
    rejects payloads without id or walletAddress, coerces non-numeric to
    None).
  - `_persist_moonpay_webhook()` best-effort upsert behaviour (success ->
    True, missing fields -> False, DB exception -> False with no leak).
  - HTTP contract of POST /api/v1/moonpay/webhook: 200 on signed body even
    if persistence fails, 401 on bad signature, 400 on bad JSON, 404 when
    master switch is off.

Live MoonPay infrastructure is never touched; the HMAC-SHA256 signature is
manually generated with the same algorithm verify_webhook() uses.
"""

from __future__ import annotations

import hashlib
import hmac
import importlib
import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.payments


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_SECRET = "sk_test_secret_value_for_unit_tests_only"
_PUBLIC = "pk_test_public_value_for_unit_tests_only"
_WEBHOOK_SECRET = "whsec_test_value_for_unit_tests_only"


@pytest.fixture(autouse=True)
def _moonpay_env(monkeypatch):
    """Inject deterministic MoonPay env for every test in this module."""
    monkeypatch.setenv("MOONPAY_SECRET_KEY", _SECRET)
    monkeypatch.setenv("MOONPAY_PUBLIC_KEY", _PUBLIC)
    monkeypatch.setenv("MOONPAY_WEBHOOK_SECRET", _WEBHOOK_SECRET)
    monkeypatch.setenv("MOONPAY_WIDGET_BASE_URL", "https://buy.moonpay.com")
    yield


@pytest.fixture
def router_module():
    """Reload the MoonPay router so it picks up the patched env."""
    import api.routers.moonpay as mod

    return importlib.reload(mod)


@pytest.fixture
def test_client():
    """Build a TestClient with EM_MOONPAY_ENABLED=true so the router mounts."""
    os.environ["EM_MOONPAY_ENABLED"] = "true"

    import api.routes as routes_mod
    import integrations.moonpay.client as client_mod

    importlib.reload(client_mod)
    routes_mod = importlib.reload(routes_mod)

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(routes_mod.router)
    return TestClient(app)


def _sign(raw_body: bytes, secret: str = _WEBHOOK_SECRET, ts: int | None = None) -> str:
    """Build a valid Moonpay-Signature-V2 header for the given body."""
    ts = ts if ts is not None else int(time.time())
    signed_payload = f"{ts}.{raw_body.decode('utf-8')}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},s={sig}"


def _canonical_payload(**overrides) -> dict:
    """A MoonPay webhook payload that has every column we care about."""
    base = {
        "type": "transaction_updated",
        "data": {
            "id": "txn-abc-123",
            "status": "completed",
            "walletAddress": "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV",
            "externalCustomerId": "exec-uuid-1",
            "currency": {"code": "usdc_sol"},
            "baseCurrencyAmount": 20.0,
            "quoteCurrencyAmount": 19.5,
            "feeAmount": 0.5,
            "cryptoTransactionId": "5sigBase58OnSolana",
        },
    }
    base["data"].update(overrides)
    return base


# ---------------------------------------------------------------------------
# _extract_moonpay_row() — pure projection
# ---------------------------------------------------------------------------


class TestExtractMoonpayRow:
    def test_canonical_payload_yields_all_columns(self, router_module):
        row = router_module._extract_moonpay_row(_canonical_payload())
        assert row is not None
        assert row["moonpay_transaction_id"] == "txn-abc-123"
        assert row["external_customer_id"] == "exec-uuid-1"
        assert row["wallet_address"] == "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV"
        assert row["crypto_currency_code"] == "usdc_sol"
        assert row["base_amount"] == 20.0
        assert row["quote_amount"] == 19.5
        assert row["fee_amount"] == 0.5
        assert row["status"] == "completed"
        assert row["crypto_transaction_id"] == "5sigBase58OnSolana"
        assert row["raw_event"]["type"] == "transaction_updated"

    def test_flat_currency_code_resolves(self, router_module):
        payload = _canonical_payload()
        del payload["data"]["currency"]
        payload["data"]["currencyCode"] = "usdc_base"
        row = router_module._extract_moonpay_row(payload)
        assert row is not None
        assert row["crypto_currency_code"] == "usdc_base"

    def test_missing_currency_falls_back_to_unknown(self, router_module):
        payload = _canonical_payload()
        del payload["data"]["currency"]
        row = router_module._extract_moonpay_row(payload)
        assert row is not None
        assert row["crypto_currency_code"] == "unknown"

    def test_missing_id_returns_none(self, router_module):
        payload = _canonical_payload()
        del payload["data"]["id"]
        assert router_module._extract_moonpay_row(payload) is None

    def test_missing_wallet_returns_none(self, router_module):
        payload = _canonical_payload()
        del payload["data"]["walletAddress"]
        assert router_module._extract_moonpay_row(payload) is None

    def test_non_dict_payload_returns_none(self, router_module):
        assert router_module._extract_moonpay_row("not a dict") is None
        assert router_module._extract_moonpay_row(None) is None
        assert router_module._extract_moonpay_row({"data": "not a dict"}) is None

    def test_non_numeric_amounts_coerce_to_none(self, router_module):
        row = router_module._extract_moonpay_row(
            _canonical_payload(
                baseCurrencyAmount="not a number",
                feeAmount=None,
            )
        )
        assert row is not None
        assert row["base_amount"] is None
        assert row["fee_amount"] is None
        # quote_amount untouched, still a float
        assert row["quote_amount"] == 19.5

    def test_null_external_customer_id_passes_through(self, router_module):
        row = router_module._extract_moonpay_row(
            _canonical_payload(externalCustomerId=None)
        )
        assert row is not None
        assert row["external_customer_id"] is None


# ---------------------------------------------------------------------------
# _persist_moonpay_webhook() — best-effort upsert
# ---------------------------------------------------------------------------


class TestPersistMoonpayWebhook:
    def test_happy_path_calls_upsert(self, router_module):
        fake_table = MagicMock()
        fake_table.upsert.return_value.execute.return_value = MagicMock()
        fake_client = MagicMock()
        fake_client.table.return_value = fake_table

        with patch("supabase_client.get_client", return_value=fake_client, create=True):
            ok = router_module._persist_moonpay_webhook(_canonical_payload())

        assert ok is True
        fake_client.table.assert_called_once_with("moonpay_transactions")
        upsert_args, upsert_kwargs = fake_table.upsert.call_args
        row = upsert_args[0]
        assert row["moonpay_transaction_id"] == "txn-abc-123"
        assert row["status"] == "completed"
        assert upsert_kwargs["on_conflict"] == "moonpay_transaction_id"

    def test_missing_fields_skip_persistence(self, router_module):
        bad_payload = {"type": "transaction_updated", "data": {"status": "pending"}}
        with patch("supabase_client.get_client") as fake_client_factory:
            ok = router_module._persist_moonpay_webhook(bad_payload)
        assert ok is False
        # supabase client must not be touched when we can't project a row
        fake_client_factory.assert_not_called()

    def test_db_exception_returns_false_no_leak(self, router_module, caplog):
        import logging

        caplog.set_level(logging.ERROR, logger="api.routers.moonpay")

        fake_client = MagicMock()
        fake_client.table.return_value.upsert.return_value.execute.side_effect = (
            RuntimeError("supabase down")
        )

        with patch("supabase_client.get_client", return_value=fake_client, create=True):
            ok = router_module._persist_moonpay_webhook(_canonical_payload())

        assert ok is False
        assert any("persist failed" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# POST /api/v1/moonpay/webhook — HTTP contract
# ---------------------------------------------------------------------------


class TestWebhookEndpoint:
    def test_valid_signature_persists_and_acks_200(self, test_client):
        payload = _canonical_payload()
        raw = json.dumps(payload).encode("utf-8")

        fake_client = MagicMock()
        fake_client.table.return_value.upsert.return_value.execute.return_value = (
            MagicMock()
        )

        with patch("supabase_client.get_client", return_value=fake_client, create=True):
            resp = test_client.post(
                "/api/v1/moonpay/webhook",
                content=raw,
                headers={
                    "Moonpay-Signature-V2": _sign(raw),
                    "Content-Type": "application/json",
                },
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["ok"] is True
        assert body["event"] == "transaction_updated"
        assert body["persisted"] is True

    def test_persistence_failure_still_acks_200(self, test_client):
        """If supabase upsert raises, the endpoint must still ACK so MoonPay does not retry-storm."""
        payload = _canonical_payload()
        raw = json.dumps(payload).encode("utf-8")

        fake_client = MagicMock()
        fake_client.table.return_value.upsert.return_value.execute.side_effect = (
            RuntimeError("supabase down")
        )

        with patch("supabase_client.get_client", return_value=fake_client, create=True):
            resp = test_client.post(
                "/api/v1/moonpay/webhook",
                content=raw,
                headers={
                    "Moonpay-Signature-V2": _sign(raw),
                    "Content-Type": "application/json",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["persisted"] is False

    def test_bad_signature_returns_401(self, test_client):
        raw = json.dumps(_canonical_payload()).encode("utf-8")
        # Sign with the wrong secret
        wrong_sig = _sign(raw, secret="not-the-real-secret")

        resp = test_client.post(
            "/api/v1/moonpay/webhook",
            content=raw,
            headers={
                "Moonpay-Signature-V2": wrong_sig,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401

    def test_malformed_json_returns_400(self, test_client):
        raw = b"{not-json"
        resp = test_client.post(
            "/api/v1/moonpay/webhook",
            content=raw,
            headers={
                "Moonpay-Signature-V2": _sign(raw),
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 400

    def test_stale_timestamp_returns_401(self, test_client):
        """Replay protection — 10 minutes old must be rejected even with valid sig."""
        raw = json.dumps(_canonical_payload()).encode("utf-8")
        stale = _sign(raw, ts=int(time.time()) - 600)

        resp = test_client.post(
            "/api/v1/moonpay/webhook",
            content=raw,
            headers={
                "Moonpay-Signature-V2": stale,
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401

    def test_404_when_master_switch_off(self, monkeypatch):
        monkeypatch.delenv("EM_MOONPAY_ENABLED", raising=False)

        import api.routes as routes_mod

        routes_mod = importlib.reload(routes_mod)

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(routes_mod.router)
        tc = TestClient(app)

        raw = json.dumps(_canonical_payload()).encode("utf-8")
        resp = tc.post(
            "/api/v1/moonpay/webhook",
            content=raw,
            headers={
                "Moonpay-Signature-V2": _sign(raw),
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 404

    def test_503_when_webhook_secret_unset(self, monkeypatch):
        """Endpoint surfaces 503 (not 500) when webhook secret is missing."""
        os.environ["EM_MOONPAY_ENABLED"] = "true"
        monkeypatch.delenv("MOONPAY_WEBHOOK_SECRET", raising=False)

        # Force a fresh import chain so the missing secret is observed.
        # The conftest._isolate_sys_modules fixture clears sys.modules between
        # tests, so we must re-import (not just reload) before reloading.
        import integrations.moonpay.client  # noqa: F401  (force into sys.modules)
        import api.routes as routes_mod

        importlib.reload(sys.modules["integrations.moonpay.client"])
        routes_mod = importlib.reload(routes_mod)

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(routes_mod.router)
        tc = TestClient(app)

        raw = json.dumps(_canonical_payload()).encode("utf-8")
        resp = tc.post(
            "/api/v1/moonpay/webhook",
            content=raw,
            headers={
                "Moonpay-Signature-V2": "t=1,s=deadbeef",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 503
