"""Tests for trusted-proxy XFF validation (Phase 2.5, SAAS_PRODUCTION_HARDENING).

See ``mcp_server/utils/net.py``.

The rule under test: ``X-Forwarded-For`` is only trusted when the TCP peer
(``request.client.host``) is in ``TRUSTED_PROXY_CIDRS``. Direct callers from
untrusted IPs can spoof XFF at will; the backend must ignore it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pytest

from utils.net import _reload_trusted_cidrs, get_client_ip


# ---------------------------------------------------------------------------
# Test fakes
# ---------------------------------------------------------------------------


@dataclass
class _FakeClient:
    host: str


class _FakeHeaders:
    """Case-insensitive header dict that mirrors Starlette's ``Headers``."""

    def __init__(self, mapping: Optional[Dict[str, str]] = None):
        self._map: Dict[str, str] = {}
        if mapping:
            for k, v in mapping.items():
                self._map[k.lower()] = v

    def get(self, key: str, default: str = "") -> str:
        return self._map.get(key.lower(), default)


class _FakeRequest:
    """Minimal stand-in for ``fastapi.Request``.

    ``utils.net.get_client_ip`` only reads ``request.client.host`` and
    ``request.headers``; no other attributes are touched.
    """

    def __init__(
        self,
        peer_host: Optional[str],
        headers: Optional[Dict[str, str]] = None,
    ):
        self.client = _FakeClient(peer_host) if peer_host is not None else None
        self.headers = _FakeHeaders(headers)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_cidrs(monkeypatch):
    """Reset the module-level trusted CIDR cache before/after each test."""
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    _reload_trusted_cidrs()
    yield
    _reload_trusted_cidrs()


# ---------------------------------------------------------------------------
# Core behavior
# ---------------------------------------------------------------------------


class TestTrustedProxyPath:
    """TCP peer is inside TRUSTED_PROXY_CIDRS → XFF honored."""

    def test_xff_honored_when_peer_is_private_ip(self):
        req = _FakeRequest(
            peer_host="10.0.0.5",  # inside default 10.0.0.0/8
            headers={"X-Forwarded-For": "203.0.113.7"},
        )
        assert get_client_ip(req) == "203.0.113.7"

    def test_xff_hop0_used_when_multiple_entries(self):
        # XFF format: "client, proxy1, proxy2" — leftmost is the original client.
        req = _FakeRequest(
            peer_host="172.20.0.10",  # inside 172.16.0.0/12
            headers={"X-Forwarded-For": "198.51.100.1, 10.0.0.1, 10.0.0.2"},
        )
        assert get_client_ip(req) == "198.51.100.1"

    def test_xff_header_lowercase_also_works(self):
        # HTTP headers are case-insensitive; Starlette normalizes to lowercase.
        req = _FakeRequest(
            peer_host="192.168.1.1",
            headers={"x-forwarded-for": "203.0.113.9"},
        )
        assert get_client_ip(req) == "203.0.113.9"


class TestUntrustedPeerPath:
    """TCP peer is NOT in TRUSTED_PROXY_CIDRS → XFF ignored."""

    def test_xff_ignored_when_peer_is_public_ip(self):
        # Attacker hits the backend directly, sending a spoofed XFF.
        # We must ignore the XFF and return the real peer.
        req = _FakeRequest(
            peer_host="203.0.113.50",  # public, not in any trusted CIDR
            headers={"X-Forwarded-For": "10.0.0.1"},
        )
        assert get_client_ip(req) == "203.0.113.50"

    def test_untrusted_peer_without_xff_returns_peer(self):
        req = _FakeRequest(peer_host="203.0.113.77")
        assert get_client_ip(req) == "203.0.113.77"


class TestMalformedXff:
    """Malformed XFF from a trusted proxy must fall back to peer."""

    def test_non_ip_xff_falls_back_to_peer(self):
        req = _FakeRequest(
            peer_host="10.0.0.1",
            headers={"X-Forwarded-For": "not-an-ip-address"},
        )
        assert get_client_ip(req) == "10.0.0.1"

    def test_empty_xff_returns_peer(self):
        req = _FakeRequest(
            peer_host="10.0.0.1",
            headers={"X-Forwarded-For": ""},
        )
        assert get_client_ip(req) == "10.0.0.1"

    def test_whitespace_only_xff_returns_peer(self):
        req = _FakeRequest(
            peer_host="10.0.0.1",
            headers={"X-Forwarded-For": "   ,  ,  "},
        )
        # First token after split+strip is empty → fall back to peer.
        assert get_client_ip(req) == "10.0.0.1"


class TestEdgeCases:
    """Missing client / missing headers."""

    def test_no_client_returns_unknown(self):
        # ASGI scope may lack a client tuple (test clients, ASGI lifespan).
        req = _FakeRequest(peer_host=None)
        assert get_client_ip(req) == "unknown"

    def test_empty_peer_returns_unknown(self):
        req = _FakeRequest(peer_host="")
        assert get_client_ip(req) == "unknown"

    def test_no_xff_trusted_peer_returns_peer(self):
        req = _FakeRequest(peer_host="10.0.0.1")
        assert get_client_ip(req) == "10.0.0.1"


# ---------------------------------------------------------------------------
# TRUSTED_PROXY_CIDRS env var
# ---------------------------------------------------------------------------


class TestTrustedCidrsEnvVar:
    """``TRUSTED_PROXY_CIDRS`` env var controls trust boundary."""

    def test_custom_cidr_narrows_trust(self, monkeypatch):
        # Only trust a single /32 — everything else is untrusted.
        monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "10.99.0.1/32")
        _reload_trusted_cidrs()

        # Exact match → XFF honored.
        trusted = _FakeRequest(
            peer_host="10.99.0.1",
            headers={"X-Forwarded-For": "203.0.113.1"},
        )
        assert get_client_ip(trusted) == "203.0.113.1"

        # Different private IP → XFF ignored now.
        untrusted = _FakeRequest(
            peer_host="10.0.0.5",
            headers={"X-Forwarded-For": "203.0.113.1"},
        )
        assert get_client_ip(untrusted) == "10.0.0.5"

    def test_multiple_cidrs_whitespace_tolerant(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "  10.1.0.0/16 ,  ,172.30.0.0/16 ,")
        _reload_trusted_cidrs()

        req_a = _FakeRequest(
            peer_host="10.1.2.3",
            headers={"X-Forwarded-For": "198.51.100.1"},
        )
        assert get_client_ip(req_a) == "198.51.100.1"

        req_b = _FakeRequest(
            peer_host="172.30.5.5",
            headers={"X-Forwarded-For": "198.51.100.2"},
        )
        assert get_client_ip(req_b) == "198.51.100.2"

    def test_invalid_cidr_entry_is_skipped(self, monkeypatch, caplog):
        # A typo must not silently disable trust — it logs a warning and
        # the remaining valid entries still work.
        monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "not-a-cidr,10.0.0.0/8")
        _reload_trusted_cidrs()

        req = _FakeRequest(
            peer_host="10.0.0.1",
            headers={"X-Forwarded-For": "203.0.113.1"},
        )
        assert get_client_ip(req) == "203.0.113.1"

    def test_empty_cidr_list_trusts_nothing(self, monkeypatch):
        monkeypatch.setenv("TRUSTED_PROXY_CIDRS", "")
        _reload_trusted_cidrs()

        # Even a private IP is untrusted when the allowlist is empty.
        req = _FakeRequest(
            peer_host="10.0.0.1",
            headers={"X-Forwarded-For": "203.0.113.1"},
        )
        assert get_client_ip(req) == "10.0.0.1"
