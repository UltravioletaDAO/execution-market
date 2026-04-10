"""
Tests for Phase 1 CRY-001 — Content-Digest mandatory for bodied requests.

Validates that the ERC-8128 verifier rejects signed requests where a body
is present but content-digest is NOT in the signed components. Before this
fix, an attacker could intercept a signed POST and swap the body entirely
without invalidating the signature.

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
)

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
    nonce: str = "test-nonce-001",
    keyid: str = KEYID,
    label: str = "eth",
) -> str:
    now = int(time.time())
    c = created or now
    e = expires or (now + 120)
    comp_str = " ".join(f'"{x}"' for x in components)
    parts = [f"({comp_str})", f"created={c}", f"expires={e}"]
    if nonce is not None:
        parts.append(f'nonce="{nonce}"')
    parts.append(f'keyid="{keyid}"')
    return f"{label}={';'.join(parts)}"


def _build_sig_base(
    components: list[str],
    request: MockRequest,
    sig_input_value: str,
) -> str:
    """Reconstruct signature base for signing (mirrors verifier logic)."""
    lines = []
    for comp in components:
        if comp == "@method":
            lines.append(f'"@method": {request.method.upper()}')
        elif comp == "@authority":
            lines.append(f'"@authority": {request.url.netloc}')
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
        components, created=now, expires=now + 120, nonce="test-nonce-cry001"
    )

    sig_base = _build_sig_base(components, req, sig_input_str)
    sig_bytes = _sign_message(sig_base)
    sig_b64 = base64.b64encode(sig_bytes).decode("ascii")

    req.headers["signature-input"] = sig_input_str
    req.headers["signature"] = f"eth=:{sig_b64}:"

    return req


# Lenient policy for tests: allow replayable and class-bound
LENIENT_POLICY = VerifyPolicy(
    max_validity_sec=300,
    clock_skew_sec=60,
    allow_replayable=True,
    allow_class_bound=True,
)


# ---------------------------------------------------------------------------
# CRY-001 Tests
# ---------------------------------------------------------------------------


class TestCRY001ContentDigestMandatory:
    """CRY-001: Bodied requests MUST include content-digest in signed components."""

    @pytest.mark.asyncio
    async def test_bodied_post_without_content_digest_rejected(self):
        """POST with body, signed without content-digest in components -> rejected."""
        body = b'{"title": "test task", "bounty": "0.10"}'
        # Sign only @method @authority @path — omit content-digest
        req = _make_signed_request(
            components=["@method", "@authority", "@path"],
            body=body,
        )
        result = await verify_erc8128_request(req, policy=LENIENT_POLICY)
        assert not result.ok, f"Expected rejection but got ok=True: {result}"
        assert "CRY-001" in (result.reason or ""), (
            f"Expected CRY-001 in reason: {result.reason}"
        )
        assert "content-digest" in (result.reason or "").lower()

    @pytest.mark.asyncio
    async def test_bodied_post_with_content_digest_accepted(self):
        """POST with body, signed WITH content-digest -> accepted."""
        body = b'{"title": "test task", "bounty": "0.10"}'
        req = _make_signed_request(
            components=["@method", "@authority", "@path", "content-digest"],
            body=body,
        )
        result = await verify_erc8128_request(req, policy=LENIENT_POLICY)
        assert result.ok, f"Expected ok=True but got: {result.reason}"
        assert result.address == ADDR

    @pytest.mark.asyncio
    async def test_get_without_content_digest_accepted(self):
        """GET request (no body) without content-digest -> accepted."""
        req = _make_signed_request(
            components=["@method", "@authority", "@path"],
            body=b"",
            method="GET",
        )
        # GET has no body, so content-length is not set (no "0" header either)
        # Remove content-length if accidentally set
        req.headers.pop("content-length", None)
        result = await verify_erc8128_request(req, policy=LENIENT_POLICY)
        assert result.ok, f"Expected ok=True for bodyless GET but got: {result.reason}"

    @pytest.mark.asyncio
    async def test_body_tampered_after_signing_rejected(self):
        """Sign with content-digest, then change body -> rejected (digest mismatch)."""
        original_body = b'{"title": "original"}'
        req = _make_signed_request(
            components=["@method", "@authority", "@path", "content-digest"],
            body=original_body,
        )
        # Tamper the body AFTER signing
        req._body = b'{"title": "TAMPERED", "admin": true}'
        # Content-Length still reflects the signed digest, but body is different
        result = await verify_erc8128_request(req, policy=LENIENT_POLICY)
        assert not result.ok, "Expected rejection for tampered body"
        assert (
            "mismatch" in (result.reason or "").lower()
            or "tamper" in (result.reason or "").lower()
        )

    @pytest.mark.asyncio
    async def test_transfer_encoding_without_content_digest_rejected(self):
        """Request with transfer-encoding header but no content-digest -> rejected."""
        body = b'{"chunked": "data"}'
        req = _make_signed_request(
            components=["@method", "@authority", "@path"],
            body=body,
            extra_headers={"transfer-encoding": "chunked"},
        )
        # Remove content-length so only transfer-encoding signals body presence
        req.headers.pop("content-length", None)
        result = await verify_erc8128_request(req, policy=LENIENT_POLICY)
        assert not result.ok
        assert "CRY-001" in (result.reason or "")

    @pytest.mark.asyncio
    async def test_content_length_zero_without_content_digest_accepted(self):
        """Request with content-length: 0 (no body) without content-digest -> accepted."""
        req = _make_signed_request(
            components=["@method", "@authority", "@path"],
            body=b"",
            method="POST",
            extra_headers={"content-length": "0"},
        )
        result = await verify_erc8128_request(req, policy=LENIENT_POLICY)
        assert result.ok, (
            f"Expected ok for empty body with content-length=0: {result.reason}"
        )
