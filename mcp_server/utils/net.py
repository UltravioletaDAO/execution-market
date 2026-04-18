"""Trusted proxy / client IP extraction.

Background (Phase 2.5, SAAS_PRODUCTION_HARDENING)
-------------------------------------------------
FastAPI request objects expose ``request.client.host`` (the direct peer of
the TCP connection) and any HTTP header the caller sent, including
``X-Forwarded-For``. Rate-limit and IP-ban logic that blindly trusts
``X-Forwarded-For`` can be bypassed by any caller that connects directly
to the backend (e.g. hitting the raw ECS/CloudFront origin URL) and sends
a spoofed XFF header. The attacker gets unlimited requests by rotating the
spoofed hop-0 IP on each call.

The correct defense is: only trust ``X-Forwarded-For`` when the TCP peer
is itself a trusted proxy (the ALB / CloudFront). This module expresses
that via the ``TRUSTED_PROXY_CIDRS`` env var (default covers the AWS VPC
private ranges where our ALB sits).

Usage
-----
::

    from utils.net import get_client_ip
    client_ip = get_client_ip(request)

This replaces ad-hoc ``request.headers.get("X-Forwarded-For")`` logic in
middleware / auth.
"""

from __future__ import annotations

import ipaddress
import logging
import os
from typing import List, Optional, Union

from fastapi import Request

logger = logging.getLogger(__name__)

# Module-level cache of parsed networks. Filled lazily on first call so
# tests can mutate the env var via ``monkeypatch`` and call
# :func:`_reload_trusted_cidrs` to re-read.
_TRUSTED_NETWORKS: Optional[
    List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]
] = None

# AWS private-IP space (RFC 1918) — the default conservatively trusts the
# entire VPC IP range so internal ECS-to-ECS calls work without extra
# config. Tighten in production by setting ``TRUSTED_PROXY_CIDRS`` to the
# actual VPC CIDR.
_DEFAULT_CIDRS = "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.0/8"


def _load_trusted_cidrs() -> List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]]:
    """Parse the ``TRUSTED_PROXY_CIDRS`` env var into a network list."""
    raw = os.getenv("TRUSTED_PROXY_CIDRS", _DEFAULT_CIDRS)
    out: List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            out.append(ipaddress.ip_network(chunk, strict=False))
        except ValueError:
            # Bad entries should never silently disable trust — log loudly
            # but keep going so a single typo doesn't take down parsing.
            logger.warning("Invalid TRUSTED_PROXY_CIDRS entry: %r (skipped)", chunk)
    return out


def _get_trusted_networks() -> List[
    Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
]:
    global _TRUSTED_NETWORKS
    if _TRUSTED_NETWORKS is None:
        _TRUSTED_NETWORKS = _load_trusted_cidrs()
    return _TRUSTED_NETWORKS


def _reload_trusted_cidrs() -> None:
    """Force a re-parse of ``TRUSTED_PROXY_CIDRS`` (for tests)."""
    global _TRUSTED_NETWORKS
    _TRUSTED_NETWORKS = _load_trusted_cidrs()


def _is_trusted_proxy(host: Optional[str]) -> bool:
    """Return True if ``host`` is inside any trusted CIDR."""
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return any(ip in net for net in _get_trusted_networks())


def get_client_ip(request: Request) -> str:
    """Return the real client IP, respecting the trusted-proxy boundary.

    Rules
    -----
    1. If there is no TCP peer at all (``request.client is None``), return
       ``"unknown"``. Test clients and some ASGI servers may trigger this.
    2. If the TCP peer is NOT in ``TRUSTED_PROXY_CIDRS``, return its IP
       directly and ignore any ``X-Forwarded-For`` header. This is the
       spoofing-resistant path — an attacker hitting the backend directly
       can set XFF to anything, but the backend ignores it.
    3. If the TCP peer IS a trusted proxy, return the first hop of
       ``X-Forwarded-For`` (the original client). Malformed XFF falls back
       to the TCP peer.

    Notes
    -----
    We do not consult ``X-Real-IP`` here. Only AWS ALB sets it and it's
    equivalent to hop-0 of ``X-Forwarded-For`` in that setup — adding a
    second header would just multiply the spoofing surface.
    """
    client = request.client
    client_host = (client.host if client else "") or ""

    if not client_host:
        return "unknown"

    if not _is_trusted_proxy(client_host):
        # Direct connection from an untrusted peer — NEVER trust XFF.
        return client_host

    xff = request.headers.get("x-forwarded-for") or request.headers.get(
        "X-Forwarded-For", ""
    )
    if not xff:
        return client_host

    # XFF is a comma-separated chain "client, proxy1, proxy2". The left-most
    # entry is the original client.
    hop0 = xff.split(",")[0].strip()
    if not hop0:
        return client_host

    # Guard against malformed entries (non-IP strings) — return the peer
    # rather than echoing junk back into rate limiter keys.
    try:
        ipaddress.ip_address(hop0)
    except ValueError:
        return client_host

    return hop0
