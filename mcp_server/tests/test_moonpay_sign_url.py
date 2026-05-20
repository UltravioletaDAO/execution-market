"""Tests for the MoonPay Widget URL signing surface (Phase 4.4).

Covers both the pure `sign_url()` helper in integrations.moonpay.client and
the FastAPI router endpoint POST /api/v1/moonpay/sign-url.

The tests never touch live MoonPay infrastructure — they exercise only the
HMAC-SHA256 derivation and the request/response contract.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import os
from urllib.parse import parse_qs, quote_plus, urlsplit

import pytest

pytestmark = pytest.mark.payments


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_SECRET = "sk_test_secret_value_for_unit_tests_only"
_PUBLIC = "pk_test_public_value_for_unit_tests_only"


@pytest.fixture(autouse=True)
def _moonpay_env(monkeypatch):
    """Inject deterministic MoonPay env for every test in this module.

    The autouse fixture in tests/conftest.py snapshots sys.modules around
    each test, so we can safely reload `integrations.moonpay.client`
    without polluting other tests.
    """
    monkeypatch.setenv("MOONPAY_SECRET_KEY", _SECRET)
    monkeypatch.setenv("MOONPAY_PUBLIC_KEY", _PUBLIC)
    monkeypatch.setenv("MOONPAY_WIDGET_BASE_URL", "https://buy.moonpay.com")
    yield


@pytest.fixture
def client_module():
    """Reload the MoonPay client module so it picks up the patched env."""
    import integrations.moonpay.client as mod

    return importlib.reload(mod)


# ---------------------------------------------------------------------------
# sign_url() — pure function
# ---------------------------------------------------------------------------


class TestSignUrlHelper:
    def test_signature_matches_manual_hmac(self, client_module):
        """Signed URL's signature equals base64(HMAC-SHA256(secret, query_string))."""
        result = client_module.sign_url(
            {
                "currencyCode": "usdc_sol",
                "baseCurrencyAmount": 20,
                "baseCurrencyCode": "usd",
                "walletAddress": "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV",
            }
        )

        # apiKey is auto-injected as the first param.
        expected_qs = (
            "?apiKey="
            + _PUBLIC
            + "&currencyCode=usdc_sol"
            + "&baseCurrencyAmount=20"
            + "&baseCurrencyCode=usd"
            + "&walletAddress=7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV"
        )
        assert result.query_string == expected_qs

        expected_sig = base64.b64encode(
            hmac.new(
                _SECRET.encode("utf-8"),
                expected_qs.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("ascii")
        assert result.signature == expected_sig

    def test_url_appends_signature_as_last_param(self, client_module):
        result = client_module.sign_url(
            {
                "currencyCode": "usdc_sol",
                "walletAddress": "abc",
                "baseCurrencyAmount": 25.5,
            }
        )
        parts = urlsplit(result.url)
        assert parts.scheme == "https"
        assert parts.netloc == "buy.moonpay.com"
        # Signature is URL-encoded with quote_plus, so parse_qs handles it.
        qs = parse_qs(parts.query)
        assert qs["signature"][0] == result.signature

    def test_deterministic_for_same_input(self, client_module):
        params = {
            "currencyCode": "usdc_sol",
            "walletAddress": "abc",
            "baseCurrencyAmount": 20,
        }
        a = client_module.sign_url(params)
        b = client_module.sign_url(params)
        assert a.url == b.url
        assert a.signature == b.signature

    def test_param_order_changes_signature(self, client_module):
        """MoonPay signs the raw query string; reordering MUST change the sig."""
        a = client_module.sign_url({"currencyCode": "usdc_sol", "walletAddress": "abc"})
        b = client_module.sign_url({"walletAddress": "abc", "currencyCode": "usdc_sol"})
        assert a.signature != b.signature

    def test_boolean_param_coerced_to_lowercase(self, client_module):
        result = client_module.sign_url(
            {
                "currencyCode": "usdc_sol",
                "walletAddress": "abc",
                "showAllCurrencies": False,
            }
        )
        # showAllCurrencies=false (NOT False, NOT 0).
        assert "showAllCurrencies=false" in result.query_string

    def test_decimal_amount_serialized_as_string(self, client_module):
        result = client_module.sign_url(
            {
                "currencyCode": "usdc_sol",
                "walletAddress": "abc",
                "baseCurrencyAmount": 20.55,
            }
        )
        assert "baseCurrencyAmount=20.55" in result.query_string

    def test_special_characters_url_encoded(self, client_module):
        """redirectURL with query params must be percent-encoded inside the signed string."""
        result = client_module.sign_url(
            {
                "currencyCode": "usdc_sol",
                "walletAddress": "abc",
                "redirectURL": "https://execution.market/callback?wallet=abc",
            }
        )
        # Colon and slash inside the redirect get percent-encoded by quote_plus.
        assert (
            "redirectURL=https%3A%2F%2Fexecution.market%2Fcallback"
            in result.query_string
        )

    def test_explicit_apikey_overrides_public_env(self, client_module):
        """Caller-provided apiKey is preserved (no auto-injection)."""
        result = client_module.sign_url(
            {
                "apiKey": "pk_override_value",
                "currencyCode": "usdc_sol",
                "walletAddress": "abc",
            }
        )
        assert "apiKey=pk_override_value" in result.query_string
        assert _PUBLIC not in result.query_string

    def test_base_url_override(self, client_module):
        result = client_module.sign_url(
            {"currencyCode": "usdc_sol", "walletAddress": "abc"},
            base_url="https://buy-sandbox.moonpay.com",
        )
        # MoonPay accepts both "host?..." and "host/?..." — our impl emits "host?...".
        assert result.url.startswith("https://buy-sandbox.moonpay.com?")

    def test_missing_secret_raises(self, monkeypatch):
        monkeypatch.delenv("MOONPAY_SECRET_KEY", raising=False)
        import integrations.moonpay.client as mod

        mod = importlib.reload(mod)
        with pytest.raises(ValueError, match="MOONPAY_SECRET_KEY"):
            mod.sign_url({"currencyCode": "usdc_sol", "walletAddress": "abc"})

    def test_missing_public_key_raises_when_apikey_absent(self, monkeypatch):
        """Without apiKey in params AND without MOONPAY_PUBLIC_KEY env, fail loud."""
        monkeypatch.delenv("MOONPAY_PUBLIC_KEY", raising=False)
        import integrations.moonpay.client as mod

        mod = importlib.reload(mod)
        with pytest.raises(ValueError, match="MOONPAY_PUBLIC_KEY"):
            mod.sign_url({"currencyCode": "usdc_sol", "walletAddress": "abc"})


# ---------------------------------------------------------------------------
# POST /api/v1/moonpay/sign-url — FastAPI endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def test_client():
    """Build a TestClient with EM_MOONPAY_ENABLED=true so the router mounts."""
    os.environ["EM_MOONPAY_ENABLED"] = "true"

    # Reload routes so the moonpay router gets included.
    import api.routes as routes_mod

    routes_mod = importlib.reload(routes_mod)

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(routes_mod.router)
    return TestClient(app)


class TestSignUrlEndpoint:
    def test_returns_signed_url_with_valid_body(self, test_client):
        resp = test_client.post(
            "/api/v1/moonpay/sign-url",
            json={
                "wallet_address": "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV",
                "base_currency_amount": 20,
                "currency_code": "usdc_sol",
                "external_customer_id": "exec-test-uuid",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["currency_code"] == "usdc_sol"
        assert body["wallet_address"] == "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV"
        assert body["url"].startswith("https://buy.moonpay.com?")
        assert "signature=" in body["url"]
        assert "externalCustomerId=exec-test-uuid" in body["url"]

    def test_rejects_zero_amount(self, test_client):
        resp = test_client.post(
            "/api/v1/moonpay/sign-url",
            json={
                "wallet_address": "abc",
                "base_currency_amount": 0,
            },
        )
        assert resp.status_code == 422

    def test_rejects_negative_amount(self, test_client):
        resp = test_client.post(
            "/api/v1/moonpay/sign-url",
            json={
                "wallet_address": "abc",
                "base_currency_amount": -5,
            },
        )
        assert resp.status_code == 422

    def test_rejects_empty_wallet(self, test_client):
        resp = test_client.post(
            "/api/v1/moonpay/sign-url",
            json={
                "wallet_address": "",
                "base_currency_amount": 20,
            },
        )
        assert resp.status_code == 422

    def test_rejects_non_https_redirect(self, test_client):
        resp = test_client.post(
            "/api/v1/moonpay/sign-url",
            json={
                "wallet_address": "abc",
                "base_currency_amount": 20,
                "redirect_url": "http://evil.example.com/cb",
            },
        )
        assert resp.status_code == 422

    def test_accepts_localhost_redirect(self, test_client):
        resp = test_client.post(
            "/api/v1/moonpay/sign-url",
            json={
                "wallet_address": "abc",
                "base_currency_amount": 20,
                "redirect_url": "http://localhost:5173/callback",
            },
        )
        assert resp.status_code == 200, resp.text

    def test_503_when_secret_unset(self, monkeypatch):
        """If the secret is missing, the endpoint must surface 503, not 500."""
        os.environ["EM_MOONPAY_ENABLED"] = "true"
        monkeypatch.delenv("MOONPAY_SECRET_KEY", raising=False)

        import api.routes as routes_mod
        import integrations.moonpay.client as client_mod

        importlib.reload(client_mod)
        routes_mod = importlib.reload(routes_mod)

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(routes_mod.router)
        tc = TestClient(app)

        resp = tc.post(
            "/api/v1/moonpay/sign-url",
            json={
                "wallet_address": "abc",
                "base_currency_amount": 20,
            },
        )
        assert resp.status_code == 503

    def test_404_when_master_switch_off(self, monkeypatch):
        """When EM_MOONPAY_ENABLED is unset/false, the router is not mounted."""
        monkeypatch.delenv("EM_MOONPAY_ENABLED", raising=False)

        import api.routes as routes_mod

        routes_mod = importlib.reload(routes_mod)

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(routes_mod.router)
        tc = TestClient(app)

        resp = tc.post(
            "/api/v1/moonpay/sign-url",
            json={
                "wallet_address": "abc",
                "base_currency_amount": 20,
            },
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Wallet masking — defense against accidental log leakage
# ---------------------------------------------------------------------------


class TestWalletMaskingInLogs:
    def test_short_wallet_fully_masked(self, test_client, caplog):
        """Anything <=10 chars must render as *** so we don't leak the whole string."""
        import logging

        caplog.set_level(logging.INFO, logger="api.routers.moonpay")
        resp = test_client.post(
            "/api/v1/moonpay/sign-url",
            json={"wallet_address": "abc", "base_currency_amount": 20},
        )
        assert resp.status_code == 200
        log_text = "\n".join(r.message for r in caplog.records)
        assert "wallet=***" in log_text

    def test_long_wallet_partially_masked(self, test_client, caplog):
        import logging

        caplog.set_level(logging.INFO, logger="api.routers.moonpay")
        wallet = "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV"
        resp = test_client.post(
            "/api/v1/moonpay/sign-url",
            json={"wallet_address": wallet, "base_currency_amount": 20},
        )
        assert resp.status_code == 200
        log_text = "\n".join(r.message for r in caplog.records)
        # First 6 + last 4 visible, middle hidden — and the full wallet must NOT appear.
        assert "wallet=7EcDhS...FLtV" in log_text
        assert wallet not in log_text

    def test_log_never_contains_signature(self, test_client, caplog):
        """Signed URLs and signatures are bearer-like and must stay out of logs."""
        import logging

        caplog.set_level(logging.INFO, logger="api.routers.moonpay")
        resp = test_client.post(
            "/api/v1/moonpay/sign-url",
            json={
                "wallet_address": "abc",
                "base_currency_amount": 20,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        log_text = "\n".join(r.message for r in caplog.records)
        assert body["url"] not in log_text
        # Extract sig and assert absence.
        sig = body["url"].split("signature=")[1]
        # Drop trailing params if any (there shouldn't be any but be defensive).
        sig = sig.split("&")[0]
        # The signature in the URL is percent-encoded; the raw base64 form has
        # different characters (= → %3D, + → %2B, / → %2F). Neither must leak.
        from urllib.parse import unquote_plus

        raw_sig = unquote_plus(sig)
        assert sig not in log_text
        assert raw_sig not in log_text


# ---------------------------------------------------------------------------
# Compatibility — signed URL parses against a manual verifier
# ---------------------------------------------------------------------------


class TestSignatureRoundTrip:
    def test_caller_can_verify_signature(self, client_module):
        """A consumer that knows the secret can re-derive the signature."""
        params = {
            "currencyCode": "usdc_sol",
            "walletAddress": "abc",
            "baseCurrencyAmount": 20,
        }
        result = client_module.sign_url(params)

        # Re-derive the signature from the recovered query string.
        url_parts = urlsplit(result.url)
        # Remove "&signature=..." that we appended.
        raw_query = "?" + url_parts.query.split("&signature=")[0]

        recomputed = base64.b64encode(
            hmac.new(
                _SECRET.encode("utf-8"),
                raw_query.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("ascii")

        from urllib.parse import unquote_plus

        sig_in_url = unquote_plus(url_parts.query.split("&signature=")[1])
        assert sig_in_url == recomputed == result.signature

    def test_quote_plus_is_consistent_for_signature(self, client_module):
        """Whatever we base64-encode, the URL must use quote_plus on it."""
        result = client_module.sign_url(
            {"currencyCode": "usdc_sol", "walletAddress": "abc"}
        )
        # Reconstruct the encoded signature from the result and compare.
        assert quote_plus(result.signature) in result.url
