"""MoonPay device-IP resolution hardening (FIX-P2-02).

``moonpay._resolve_device_ip`` previously parsed ``X-Forwarded-For`` itself,
taking the LEFT-most hop with NO trusted-proxy gate at all — strictly worse
than the central helper. It now delegates to ``utils.net.get_client_ip`` so the
trusted-proxy boundary and right-most-hop selection apply, while an explicit
``override`` still wins.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pytest

from api.routers.moonpay import _resolve_device_ip
from utils.net import _reload_trusted_cidrs

pytestmark = [pytest.mark.infrastructure, pytest.mark.security]


# ---------------------------------------------------------------------------
# Test fakes (mirror those in test_client_ip.py)
# ---------------------------------------------------------------------------


@dataclass
class _FakeClient:
    host: str


class _FakeHeaders:
    def __init__(self, mapping: Optional[Dict[str, str]] = None):
        self._map: Dict[str, str] = {}
        if mapping:
            for k, v in mapping.items():
                self._map[k.lower()] = v

    def get(self, key: str, default: str = "") -> str:
        return self._map.get(key.lower(), default)


class _FakeRequest:
    def __init__(
        self,
        peer_host: Optional[str],
        headers: Optional[Dict[str, str]] = None,
    ):
        self.client = _FakeClient(peer_host) if peer_host is not None else None
        self.headers = _FakeHeaders(headers)


@pytest.fixture(autouse=True)
def _reset_cidrs(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_CIDRS", raising=False)
    _reload_trusted_cidrs()
    yield
    _reload_trusted_cidrs()


# ---------------------------------------------------------------------------
# _resolve_device_ip
# ---------------------------------------------------------------------------


def test_uses_rightmost_hop_not_leftmost_spoofed():
    # Behind the ALB (trusted peer) with a spoofed left prefix: must resolve
    # to the appended (right-most non-trusted) IP, NOT the spoofed 1.2.3.4.
    req = _FakeRequest(
        peer_host="10.0.0.5",
        headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.7"},
    )
    assert _resolve_device_ip(req, override=None) == "203.0.113.7"


def test_override_still_wins():
    req = _FakeRequest(
        peer_host="10.0.0.5",
        headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.7"},
    )
    assert _resolve_device_ip(req, override="9.8.7.6") == "9.8.7.6"


def test_untrusted_peer_ignores_spoofed_xff():
    # Direct hit from an untrusted public peer: XFF is ignored entirely.
    req = _FakeRequest(
        peer_host="203.0.113.50",
        headers={"X-Forwarded-For": "10.0.0.1"},
    )
    assert _resolve_device_ip(req, override=None) == "203.0.113.50"
