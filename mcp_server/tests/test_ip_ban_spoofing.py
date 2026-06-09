"""Regression: spoofed X-Forwarded-For cannot poison a victim's ban bucket.

See ``docs/reports/security-audit-2026-06-09/fixes/FIX-P2-02-xff-spoofing-ratelimit-bypass.md``.

Before FIX-P2-02, ``utils.net.get_client_ip`` returned the LEFT-most XFF hop.
Behind the AWS ALB (append mode) the left-most hop is fully attacker-controlled,
so an attacker could send ``X-Forwarded-For: <victim>`` and have every per-IP
control (rate limiter, A2A limiter, progressive IP auto-ban) key on ``<victim>``
instead of the attacker's real source. That let an attacker:

  * rotate the spoofed hop to evade per-IP limits/bans entirely, and
  * poison the in-memory ban list against an arbitrary third-party victim IP.

After the fix, ``get_client_ip`` returns the RIGHT-most non-trusted hop — the
address the ALB appended (the attacker's real source) — so a spoofed left
prefix can neither evade limits nor select the victim's bucket.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pytest

from utils.net import _reload_trusted_cidrs, get_client_ip

# IP-ban / per-IP rate-limit hardening (FIX-P2-02) — infrastructure abuse
# control with a security dimension.
pytestmark = [pytest.mark.infrastructure, pytest.mark.security]


# ---------------------------------------------------------------------------
# Test fakes (mirror those in test_client_ip.py)
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
# Regression coverage
# ---------------------------------------------------------------------------


def test_spoofed_xff_cannot_poison_victim_ban():
    # Attacker behind the ALB sends "X-Forwarded-For: <victim>". The ALB
    # appends the attacker's real source on the RIGHT.
    victim = "203.0.113.50"
    attacker_real = "198.51.100.99"
    req = _FakeRequest(
        peer_host="10.0.0.5",  # ALB, trusted
        headers={"X-Forwarded-For": f"{victim}, {attacker_real}"},
    )
    resolved = get_client_ip(req)
    # The derived IP is the ALB-appended attacker IP, NOT the victim — so
    # any 401/429 strikes accrue against the attacker, never the victim.
    assert resolved == attacker_real
    assert resolved != victim


def test_rotating_spoofed_hop_keys_on_stable_real_ip():
    # An attacker rotating the spoofed left hop on every request can no longer
    # rotate buckets: every request keys on the same real (appended) IP, so
    # strikes accumulate and the limiter/ban can trip.
    attacker_real = "198.51.100.99"
    resolved = set()
    for n in range(1, 6):
        req = _FakeRequest(
            peer_host="10.0.0.5",
            headers={"X-Forwarded-For": f"7.7.7.{n}, {attacker_real}"},
        )
        resolved.add(get_client_ip(req))
    assert resolved == {attacker_real}


def test_real_victim_connection_resolves_to_victim_only():
    # When the genuine victim connects with no spoofed prefix, the ALB sets
    # XFF=<victim>. The victim's bucket is keyed on the victim — and was never
    # poisoned above — so a legitimate victim is not collateral-banned.
    victim = "203.0.113.50"
    req = _FakeRequest(
        peer_host="10.0.0.5",
        headers={"X-Forwarded-For": victim},
    )
    assert get_client_ip(req) == victim
