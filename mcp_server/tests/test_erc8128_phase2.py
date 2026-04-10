"""
Tests for Phase 2 security remediation — ERC-8128 verifier hardening.

CRY-005: @authority resolution behind ALB (X-Forwarded-Host)
CRY-006: Signature-params ordering preserved from signer
CRY-012: Nonce consumed BEFORE signature recovery

Marker: security
"""

from __future__ import annotations

import base64
import hashlib
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional

import pytest

pytestmark = pytest.mark.security

# Add mcp_server/ to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Stub out dependencies that are not needed for verifier unit tests
for _m in [
    "integrations.erc8004",
    "integrations.erc8004.identity",
    "integrations.erc8004.facilitator_client",
]:
    if _m not in sys.modules:
        s = ModuleType(_m)
        if _m.endswith(".identity"):
            s.check_worker_identity = None
        elif _m.endswith(".facilitator_client"):
            s.get_facilitator_client = None
        sys.modules[_m] = s

from integrations.erc8128.verifier import (
    verify_erc8128_request,
    VerifyPolicy,
    _resolve_authority,
    _build_signature_params,
    _resolve_component,
)
from integrations.erc8128.nonce_store import InMemoryNonceStore

try:
    from eth_account import Account
    from eth_account.messages import encode_defunct

    HAS_ETH = True
except ImportError:
    HAS_ETH = False

# Hardhat test key #0 — deterministic, not a real key
PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
ADDR = (
    Account.from_key(PK).address.lower()
    if HAS_ETH
    else "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
)
KEYID = f"erc8128:8453:{ADDR}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class MockURL:
    path: str = "/api/v1/tasks"
    query: str = ""
    netloc: str = "api.execution.market"
    hostname: str = "api.execution.market"
    port: Optional[int] = None


@dataclass
class MockRequest:
    method: str = "POST"
    url: MockURL = None
    headers: dict = None
    _body: bytes = b""

    def __post_init__(self):
        if self.url is None:
            self.url = MockURL()
        if self.headers is None:
            self.headers = {}

    async def body(self):
        return self._body


def _content_digest(body: bytes) -> str:
    return f"sha-256=:{base64.b64encode(hashlib.sha256(body).digest()).decode()}:"


def _build_sig_input(
    components: list[str],
    created: int | None = None,
    expires: int | None = None,
    nonce: str = "test-nonce-phase2",
    keyid: str = KEYID,
    label: str = "eth",
    param_order: list[str] | None = None,
) -> str:
    """Build Signature-Input header value.

    param_order controls the ordering of parameters.  If None, uses
    the default order (created, expires, nonce, keyid).
    """
    now = int(time.time())
    c = created or now
    e = expires or (now + 120)

    comp_str = " ".join(f'"{x}"' for x in components)

    # Build params dict for ordering
    all_params = {
        "created": str(c),
        "expires": str(e),
    }
    if nonce is not None:
        all_params["nonce"] = f'"{nonce}"'
    all_params["keyid"] = f'"{keyid}"'

    order = param_order or ["created", "expires", "nonce", "keyid"]

    parts = [f"({comp_str})"]
    for key in order:
        if key in all_params:
            parts.append(f"{key}={all_params[key]}")

    return f"{label}={';'.join(parts)}"


def _build_sig_base_manual(
    components: list[str],
    request: MockRequest,
    sig_input_value: str,
    authority_override: str | None = None,
) -> str:
    """Reconstruct signature base for signing (mirrors verifier logic)."""
    lines = []
    for comp in components:
        if comp == "@method":
            lines.append(f'"@method": {request.method.upper()}')
        elif comp == "@authority":
            authority = authority_override or request.url.netloc
            lines.append(f'"@authority": {authority}')
        elif comp == "@path":
            lines.append(f'"@path": {request.url.path}')
        elif comp == "@query":
            q = request.url.query
            lines.append(f'"@query": ?{q}' if q else '"@query": ?')
        elif comp == "content-digest":
            digest = request.headers.get("content-digest", "")
            lines.append(f'"content-digest": {digest}')

    # Extract the params portion from sig_input_value (after label=)
    params_str = sig_input_value.split("=", 1)[1]
    lines.append(f'"@signature-params": {params_str}')
    return "\n".join(lines)


def _sign_message(message: str) -> bytes:
    if not HAS_ETH:
        pytest.skip("eth_account not available")
    msg = encode_defunct(text=message)
    return Account.sign_message(msg, private_key=PK).signature


def _make_signed_request(
    components: list[str],
    body: bytes = b"",
    method: str = "POST",
    extra_headers: dict | None = None,
    param_order: list[str] | None = None,
    authority_override: str | None = None,
    nonce: str = "test-nonce-phase2",
) -> MockRequest:
    """Build a fully signed MockRequest."""
    headers = dict(extra_headers or {})

    if body:
        headers["content-length"] = str(len(body))
        if "content-digest" not in headers and "content-digest" in components:
            headers["content-digest"] = _content_digest(body)

    req = MockRequest(method=method, _body=body, headers=headers)

    now = int(time.time())
    sig_input_str = _build_sig_input(
        components,
        created=now,
        expires=now + 120,
        nonce=nonce,
        param_order=param_order,
    )

    sig_base = _build_sig_base_manual(
        components, req, sig_input_str, authority_override=authority_override
    )
    sig_bytes = _sign_message(sig_base)
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    req.headers["signature-input"] = sig_input_str
    req.headers["signature"] = f"eth=:{sig_b64}:"

    return req


LENIENT_POLICY = VerifyPolicy(
    max_validity_sec=300,
    clock_skew_sec=60,
    allow_replayable=True,
    allow_class_bound=True,
)


# ===========================================================================
# CRY-005: @authority resolution behind ALB
# ===========================================================================


class TestCRY005AuthorityResolution:
    """CRY-005: Use X-Forwarded-Host when resolving @authority behind ALB."""

    def test_resolve_authority_uses_forwarded_host(self):
        """X-Forwarded-Host takes priority over url.netloc."""
        req = MockRequest(
            url=MockURL(netloc="internal-alb-1234.us-east-2.elb.amazonaws.com"),
            headers={"x-forwarded-host": "api.execution.market"},
        )
        assert _resolve_authority(req) == "api.execution.market"

    def test_resolve_authority_chained_forwarded_host(self):
        """ALB may chain multiple values; take the first (client-facing)."""
        req = MockRequest(
            url=MockURL(netloc="internal-host"),
            headers={"x-forwarded-host": "api.execution.market, cdn.cloudfront.net"},
        )
        assert _resolve_authority(req) == "api.execution.market"

    def test_resolve_authority_strips_whitespace(self):
        """Whitespace around forwarded host is stripped."""
        req = MockRequest(
            url=MockURL(netloc="internal-host"),
            headers={"x-forwarded-host": "  api.execution.market  "},
        )
        assert _resolve_authority(req) == "api.execution.market"

    def test_resolve_authority_fallback_to_netloc(self):
        """Without X-Forwarded-Host, falls back to url.netloc."""
        req = MockRequest(
            url=MockURL(netloc="api.execution.market"),
            headers={},
        )
        assert _resolve_authority(req) == "api.execution.market"

    def test_resolve_authority_fallback_to_hostname_with_port(self):
        """Without netloc, uses hostname:port."""

        class HostnameOnlyURL:
            """URL object that has hostname and port but no netloc."""

            hostname = "api.execution.market"
            port = 8443
            path = "/test"
            query = ""

        req = MockRequest(url=HostnameOnlyURL(), headers={})
        result = _resolve_authority(req)
        assert result == "api.execution.market:8443"

    def test_resolve_authority_fallback_to_host_header(self):
        """Without URL or forwarded host, falls back to Host header."""
        req = MockRequest(headers={"host": "api.execution.market"})
        req.url = None
        assert _resolve_authority(req) == "api.execution.market"

    @pytest.mark.asyncio
    async def test_signed_request_behind_alb_verifies(self):
        """Full E2E: signer signs for public host, verifier behind ALB sees
        internal netloc but X-Forwarded-Host corrects it."""
        components = ["@method", "@authority", "@path"]
        req = _make_signed_request(
            components=components,
            body=b"",
            method="GET",
            authority_override="api.execution.market",
        )
        # Simulate ALB: internal netloc differs, but X-Forwarded-Host is set
        req.url = MockURL(netloc="internal-alb-1234.us-east-2.elb.amazonaws.com")
        req.headers["x-forwarded-host"] = "api.execution.market"
        req.headers.pop("content-length", None)

        result = await verify_erc8128_request(req, policy=LENIENT_POLICY)
        assert result.ok, f"Expected ok=True but got: {result.reason}"
        assert result.address == ADDR

    @pytest.mark.asyncio
    async def test_resolve_component_authority_delegates(self):
        """_resolve_component('@authority', ...) delegates to _resolve_authority."""
        req = MockRequest(
            url=MockURL(netloc="internal-host"),
            headers={"x-forwarded-host": "public.host.com"},
        )
        value = await _resolve_component(req, "@authority")
        assert value == "public.host.com"


# ===========================================================================
# CRY-006: Signature-params ordering preserved from signer
# ===========================================================================


class TestCRY006SignatureParamsOrdering:
    """CRY-006: Verifier must use signer's parameter ordering, not its own."""

    def test_params_ordering_preserved(self):
        """Parameters appear in the order they exist in the dict (insertion order)."""
        from collections import OrderedDict

        # Alphabetic order: created, expires, keyid, nonce
        params = OrderedDict()
        params["keyid"] = "erc8128:8453:0xabc"
        params["nonce"] = "test-123"
        params["created"] = 1000
        params["expires"] = 2000

        result = _build_signature_params(["@method", "@path"], params)
        # Should be: ("@method" "@path");keyid="erc8128:8453:0xabc";nonce="test-123";created=1000;expires=2000
        parts = result.split(";")
        assert parts[0] == '("@method" "@path")'
        assert parts[1] == 'keyid="erc8128:8453:0xabc"'
        assert parts[2] == 'nonce="test-123"'
        assert parts[3] == "created=1000"
        assert parts[4] == "expires=2000"

    def test_default_ordering_still_works(self):
        """Standard created/expires/nonce/keyid ordering still produces valid params."""
        params = {
            "created": 1000,
            "expires": 2000,
            "nonce": "abc",
            "keyid": "erc8128:8453:0xdef",
        }
        result = _build_signature_params(["@method"], params)
        parts = result.split(";")
        assert parts[0] == '("@method")'
        assert parts[1] == "created=1000"
        assert parts[2] == "expires=2000"
        assert parts[3] == 'nonce="abc"'
        assert parts[4] == 'keyid="erc8128:8453:0xdef"'

    @pytest.mark.asyncio
    async def test_alphabetic_ordered_params_verify(self):
        """A signer using alphabetic param order should verify successfully."""
        # Alphabetic: created, expires, keyid, nonce
        components = ["@method", "@authority", "@path"]
        param_order = ["created", "expires", "keyid", "nonce"]
        req = _make_signed_request(
            components=components,
            body=b"",
            method="GET",
            param_order=param_order,
        )
        req.headers.pop("content-length", None)

        result = await verify_erc8128_request(req, policy=LENIENT_POLICY)
        assert result.ok, f"Expected ok=True but got: {result.reason}"

    @pytest.mark.asyncio
    async def test_reversed_param_order_verify(self):
        """A signer using reversed param order (keyid, nonce, expires, created)
        should verify successfully."""
        components = ["@method", "@authority", "@path"]
        param_order = ["keyid", "nonce", "expires", "created"]
        req = _make_signed_request(
            components=components,
            body=b"",
            method="GET",
            param_order=param_order,
        )
        req.headers.pop("content-length", None)

        result = await verify_erc8128_request(req, policy=LENIENT_POLICY)
        assert result.ok, f"Expected ok=True but got: {result.reason}"

    @pytest.mark.asyncio
    async def test_custom_extra_params_preserved(self):
        """Extra non-standard params should be preserved in insertion order."""
        params = {
            "created": 1000,
            "alg": "eth-personal-sign",
            "expires": 2000,
            "keyid": "erc8128:1:0xabc",
        }
        result = _build_signature_params(["@method"], params)
        parts = result.split(";")
        assert parts[1] == "created=1000"
        assert parts[2] == 'alg="eth-personal-sign"'
        assert parts[3] == "expires=2000"
        assert parts[4] == 'keyid="erc8128:1:0xabc"'


# ===========================================================================
# CRY-012: Nonce consumed BEFORE signature recovery
# ===========================================================================


class TestCRY012NonceConsumeOrder:
    """CRY-012: Nonce must be consumed before the expensive signature check."""

    @pytest.mark.asyncio
    async def test_nonce_consumed_before_sig_check(self):
        """Same nonce used twice -> second request rejected even if signature
        would be valid."""
        nonce_store = InMemoryNonceStore()

        components = ["@method", "@authority", "@path"]
        req1 = _make_signed_request(
            components=components,
            body=b"",
            method="GET",
            nonce="unique-nonce-cry012",
        )
        req1.headers.pop("content-length", None)

        result1 = await verify_erc8128_request(
            req1, nonce_store=nonce_store, policy=LENIENT_POLICY
        )
        assert result1.ok, f"First request should pass: {result1.reason}"

        # Second request with the same nonce
        req2 = _make_signed_request(
            components=components,
            body=b"",
            method="GET",
            nonce="unique-nonce-cry012",
        )
        req2.headers.pop("content-length", None)

        result2 = await verify_erc8128_request(
            req2, nonce_store=nonce_store, policy=LENIENT_POLICY
        )
        assert not result2.ok
        assert "replay" in (result2.reason or "").lower()

    @pytest.mark.asyncio
    async def test_nonce_consumed_even_on_invalid_signature(self):
        """If nonce is consumed early and then signature fails, the nonce
        stays consumed (not rolled back)."""
        nonce_store = InMemoryNonceStore()
        nonce_val = "nonce-consumed-early-test"

        # Create a request with a valid structure but WRONG signature
        components = ["@method", "@authority", "@path"]
        now = int(time.time())
        sig_input = _build_sig_input(
            components, created=now, expires=now + 120, nonce=nonce_val
        )
        req = MockRequest(
            method="GET",
            headers={
                "signature-input": sig_input,
                "signature": "eth=:AAAA:",  # Invalid signature
            },
        )

        result = await verify_erc8128_request(
            req, nonce_store=nonce_store, policy=LENIENT_POLICY
        )
        # Should fail on signature verification, not on nonce
        assert not result.ok
        assert "replay" not in (result.reason or "").lower()

        # Now use the same nonce with a valid signature — should be rejected
        # because nonce was consumed
        nonce_key = f"erc8128:8453:{ADDR}:{nonce_val}"
        consumed = await nonce_store.consume(nonce_key, 300)
        assert not consumed, "Nonce should already be consumed"

    @pytest.mark.asyncio
    async def test_replayable_skips_nonce_check(self):
        """Replayable signatures (no nonce) skip the nonce store entirely."""
        nonce_store = InMemoryNonceStore()

        components = ["@method", "@authority", "@path"]
        req = _make_signed_request(
            components=components,
            body=b"",
            method="GET",
            nonce=None,  # No nonce -> replayable
            param_order=["created", "expires", "keyid"],
        )
        req.headers.pop("content-length", None)

        policy = VerifyPolicy(
            max_validity_sec=300,
            clock_skew_sec=60,
            allow_replayable=True,
            allow_class_bound=True,
        )
        result = await verify_erc8128_request(
            req, nonce_store=nonce_store, policy=policy
        )
        assert result.ok, f"Replayable request should pass: {result.reason}"
        assert result.replayable is True
        # Nonce store should be empty (nothing consumed)
        assert len(nonce_store) == 0

    @pytest.mark.asyncio
    async def test_no_nonce_store_skips_consumption(self):
        """When no nonce_store is provided, nonce check is skipped."""
        components = ["@method", "@authority", "@path"]
        req = _make_signed_request(
            components=components,
            body=b"",
            method="GET",
            nonce="nonce-but-no-store",
        )
        req.headers.pop("content-length", None)

        result = await verify_erc8128_request(
            req, nonce_store=None, policy=LENIENT_POLICY
        )
        assert result.ok, f"Should pass without nonce store: {result.reason}"
