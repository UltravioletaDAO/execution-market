"""
Tests for ERC-8128 Wallet-Based Authentication.

Test categories:
1. Signature verification — valid EOA signatures, invalid signatures, wrong address
2. Nonce management — fresh nonce accepted, replay rejected, TTL expiry
3. Timestamp validation — expired signatures, not-yet-valid, clock skew
4. Content-Digest — body hash match, body hash mismatch, missing digest
5. Request binding — all components signed, missing component, class-bound
6. KeyId parsing — valid format, invalid format, various chain IDs
7. Dual auth — ERC-8128 + API key coexistence
8. InMemoryNonceStore — eviction, TTL, concurrent access
9. Signature-Input parsing — RFC 8941 structured field parsing
10. ERC-1271 ABI encoding — calldata construction
"""

import asyncio
import base64
import hashlib
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.erc8128

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Stub heavy external dependencies that may not be available in test env
_STUB_MODULES = [
    "integrations.erc8004",
    "integrations.erc8004.identity",
    "integrations.erc8004.facilitator_client",
]
for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        stub = ModuleType(_mod_name)
        if _mod_name.endswith(".identity"):
            stub.check_worker_identity = None
        elif _mod_name.endswith(".facilitator_client"):
            stub.get_facilitator_client = None
        sys.modules[_mod_name] = stub

from integrations.erc8128.verifier import (
    verify_erc8128_request,
    ERC8128Result,
    VerifyPolicy,
    DEFAULT_POLICY,
    _parse_signature_input,
    _validate_timestamps,
    _build_signature_base,
    _determine_binding,
    _eip191_recover,
    _extract_signature_bytes,
    _verify_content_digest,
    KEYID_RE,
)
from integrations.erc8128.nonce_store import (
    InMemoryNonceStore,
    NonceStore,
    reset_nonce_store,
)
from integrations.erc8128.erc1271 import (
    _encode_is_valid_signature,
    clear_sca_cache,
)


# ---------------------------------------------------------------------------
# Test Helpers
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

    async def body(self) -> bytes:
        return self._body


def _make_sig_input(components, created=None, expires=None, nonce="test-nonce-123",
                    keyid="erc8128:8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68",
                    label="eth"):
    now = int(time.time())
    if created is None: created = now
    if expires is None: expires = now + 60
    comp_str = " ".join(f'"{c}"' for c in components)
    parts = [f"({comp_str})", f"created={created}", f"expires={expires}"]
    if nonce is not None:
        parts.append(f'nonce="{nonce}"')
    parts.append(f'keyid="{keyid}"')
    return f"{label}={';'.join(parts)}"


def _make_content_digest(body):
    digest = hashlib.sha256(body).digest()
    b64 = base64.b64encode(digest).decode()
    return f"sha-256=:{b64}:"


try:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    HAS_ETH_ACCOUNT = True
except ImportError:
    HAS_ETH_ACCOUNT = False


def _sign_message(message, private_key):
    if not HAS_ETH_ACCOUNT:
        pytest.skip("eth_account not available")
    msg = encode_defunct(text=message)
    signed = Account.sign_message(msg, private_key=private_key)
    return signed.signature


TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
if HAS_ETH_ACCOUNT:
    TEST_ADDRESS = Account.from_key(TEST_PRIVATE_KEY).address.lower()
else:
    TEST_ADDRESS = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
TEST_KEYID = f"erc8128:8453:{TEST_ADDRESS}"


# =========================================================================
# 1. KeyId Parsing
# =========================================================================

class TestKeyIdParsing:
    def test_valid_keyid(self):
        m = KEYID_RE.match("erc8128:8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68")
        assert m is not None
        assert m.group(1) == "8453"

    def test_valid_keyid_chain_1(self):
        m = KEYID_RE.match("erc8128:1:0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        assert m is not None

    def test_valid_keyid_lowercase(self):
        assert KEYID_RE.match("erc8128:8453:0xabcdef1234567890abcdef1234567890abcdef12")

    def test_invalid_no_prefix(self):
        assert KEYID_RE.match("8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68") is None

    def test_invalid_wrong_prefix(self):
        assert KEYID_RE.match("eip4361:8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68") is None

    def test_invalid_short_address(self):
        assert KEYID_RE.match("erc8128:8453:0x742d35Cc") is None

    def test_invalid_no_chain(self):
        assert KEYID_RE.match("erc8128::0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68") is None

    def test_invalid_no_0x(self):
        assert KEYID_RE.match("erc8128:8453:742d35Cc6634C0532925a3b844Bc9e7595f2bD68") is None


# =========================================================================
# 2. Signature-Input Parsing
# =========================================================================

class TestSignatureInputParsing:
    def test_parse_basic(self):
        raw = 'eth=("@method" "@authority" "@path");created=1700000000;expires=1700000060;nonce="abc123";keyid="erc8128:1:0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"'
        label, components, params = _parse_signature_input(raw)
        assert label == "eth"
        assert components == ["@method", "@authority", "@path"]
        assert params["created"] == 1700000000
        assert params["nonce"] == "abc123"

    def test_parse_non_eth_label(self):
        raw = 'sig1=("@method" "@authority");created=100;expires=200;keyid="k"'
        label, _, _ = _parse_signature_input(raw)
        assert label == "sig1"

    def test_strict_label_rejects_non_eth(self):
        raw = 'sig1=("@method");created=100;expires=200;keyid="k"'
        label, _, _ = _parse_signature_input(raw, strict_label=True)
        assert label is None

    def test_strict_label_accepts_eth(self):
        raw = 'eth=("@method");created=100;expires=200;keyid="k"'
        label, _, _ = _parse_signature_input(raw, strict_label=True)
        assert label == "eth"

    def test_prefers_eth_label(self):
        raw = 'sig1=("@method");created=1;expires=2;keyid="x", eth=("@authority");created=3;expires=4;keyid="y"'
        label, _, _ = _parse_signature_input(raw)
        assert label == "eth"

    def test_empty_string(self):
        label, components, _ = _parse_signature_input("")
        assert label is None
        assert components == []

    def test_with_content_digest(self):
        raw = 'eth=("@method" "@authority" "@path" "content-digest");created=100;expires=200;keyid="k"'
        _, components, _ = _parse_signature_input(raw)
        assert "content-digest" in components

    def test_with_query(self):
        raw = 'eth=("@method" "@authority" "@path" "@query");created=100;expires=200;keyid="k"'
        _, components, _ = _parse_signature_input(raw)
        assert "@query" in components


# =========================================================================
# 3. Timestamp Validation
# =========================================================================

class TestTimestampValidation:
    def test_valid(self):
        now = int(time.time())
        assert _validate_timestamps(now, now + 60, DEFAULT_POLICY) is None

    def test_expired(self):
        now = int(time.time())
        err = _validate_timestamps(now - 600, now - 300, DEFAULT_POLICY)
        assert "expired" in err.lower()

    def test_future_created(self):
        now = int(time.time())
        err = _validate_timestamps(now + 600, now + 660, DEFAULT_POLICY)
        assert "future" in err.lower()

    def test_expires_before_created(self):
        now = int(time.time())
        err = _validate_timestamps(now + 60, now, DEFAULT_POLICY)
        assert "greater" in err.lower()

    def test_window_too_large(self):
        now = int(time.time())
        err = _validate_timestamps(now, now + 600, DEFAULT_POLICY)
        assert "too large" in err.lower()

    def test_clock_skew_tolerance(self):
        now = int(time.time())
        assert _validate_timestamps(now + 20, now + 80, DEFAULT_POLICY) is None

    def test_non_integer(self):
        err = _validate_timestamps("abc", "def", DEFAULT_POLICY)
        assert "integer" in err.lower()

    def test_custom_policy_max_validity(self):
        policy = VerifyPolicy(max_validity_sec=30)
        now = int(time.time())
        err = _validate_timestamps(now, now + 60, policy)
        assert "too large" in err.lower()


# =========================================================================
# 4. Binding Determination
# =========================================================================

class TestBindingDetermination:
    def test_request_bound_minimal(self):
        req = MockRequest(url=MockURL(query=""))
        assert _determine_binding(req, ["@method", "@authority", "@path"]) == "request-bound"

    def test_request_bound_with_query(self):
        req = MockRequest(url=MockURL(query="a=1"))
        assert _determine_binding(req, ["@method", "@authority", "@path", "@query"]) == "request-bound"

    def test_class_bound_missing_method(self):
        req = MockRequest(url=MockURL(query=""))
        assert _determine_binding(req, ["@authority", "@path"]) == "class-bound"

    def test_class_bound_missing_authority(self):
        req = MockRequest(url=MockURL(query=""))
        assert _determine_binding(req, ["@method", "@path"]) == "class-bound"

    def test_class_bound_query_not_covered(self):
        req = MockRequest(url=MockURL(query="param=value"))
        assert _determine_binding(req, ["@method", "@authority", "@path"]) == "class-bound"


# =========================================================================
# 5. Content-Digest
# =========================================================================

class TestContentDigest:
    @pytest.mark.asyncio
    async def test_valid_digest(self):
        body = b'{"title": "Test Task"}'
        req = MockRequest(headers={"content-digest": _make_content_digest(body)}, _body=body)
        assert await _verify_content_digest(req) is None

    @pytest.mark.asyncio
    async def test_mismatched_digest(self):
        body = b'{"title": "Test Task"}'
        req = MockRequest(headers={"content-digest": _make_content_digest(b"wrong")}, _body=body)
        err = await _verify_content_digest(req)
        assert "mismatch" in err.lower()

    @pytest.mark.asyncio
    async def test_missing_header(self):
        req = MockRequest(headers={}, _body=b"body")
        assert "missing" in (await _verify_content_digest(req)).lower()

    @pytest.mark.asyncio
    async def test_empty_body(self):
        body = b""
        req = MockRequest(headers={"content-digest": _make_content_digest(body)}, _body=body)
        assert await _verify_content_digest(req) is None


# =========================================================================
# 6. Signature Base Construction
# =========================================================================

class TestSignatureBase:
    @pytest.mark.asyncio
    async def test_basic(self):
        req = MockRequest(method="POST", url=MockURL(path="/api/v1/tasks", netloc="api.execution.market"))
        sig_base = await _build_signature_base(req, "eth", ["@method", "@authority", "@path"],
            {"created": 1700000000, "expires": 1700000060, "keyid": "test"})
        assert '"@method": POST' in sig_base
        assert '"@authority": api.execution.market' in sig_base
        assert '"@signature-params":' in sig_base

    @pytest.mark.asyncio
    async def test_with_query(self):
        req = MockRequest(method="GET", url=MockURL(query="status=open&limit=10"))
        sig_base = await _build_signature_base(req, "eth", ["@method", "@authority", "@path", "@query"],
            {"created": 100, "expires": 200, "keyid": "k"})
        assert '"@query": ?status=open&limit=10' in sig_base

    @pytest.mark.asyncio
    async def test_with_content_digest(self):
        body = b'{"test": true}'
        digest = _make_content_digest(body)
        req = MockRequest(method="POST", headers={"content-digest": digest}, _body=body)
        sig_base = await _build_signature_base(req, "eth", ["@method", "@authority", "@path", "content-digest"],
            {"created": 100, "expires": 200, "keyid": "k"})
        assert f'"content-digest": {digest}' in sig_base

    @pytest.mark.asyncio
    async def test_params_ordering(self):
        req = MockRequest()
        sig_base = await _build_signature_base(req, "eth", ["@method"],
            {"keyid": "k", "nonce": "n", "expires": 200, "created": 100})
        params_line = [l for l in sig_base.split("\n") if "@signature-params" in l][0]
        assert params_line.index("created=") < params_line.index("expires=")
        assert params_line.index("expires=") < params_line.index('nonce=')


# =========================================================================
# 7. EIP-191 Recovery
# =========================================================================

@pytest.mark.skipif(not HAS_ETH_ACCOUNT, reason="eth_account not available")
class TestEIP191Recovery:
    def test_valid(self):
        sig = _sign_message("test message", TEST_PRIVATE_KEY)
        assert _eip191_recover("test message", sig) == TEST_ADDRESS

    def test_different_message(self):
        sig = _sign_message("original", TEST_PRIVATE_KEY)
        assert _eip191_recover("tampered", sig) != TEST_ADDRESS

    def test_invalid_signature(self):
        recovered = _eip191_recover("test", b"\x00" * 65)
        assert recovered is None or recovered != TEST_ADDRESS

    def test_empty_signature(self):
        assert _eip191_recover("test", b"") is None


# =========================================================================
# 8. Signature Extraction
# =========================================================================

class TestSignatureExtraction:
    def test_extract_valid(self):
        sig_data = b"\x01\x02\x03\x04"
        b64 = base64.b64encode(sig_data).decode()
        assert _extract_signature_bytes(f"eth=:{b64}:", "eth") == sig_data

    def test_wrong_label(self):
        assert _extract_signature_bytes("eth=:AQIDBA==:", "sig1") is None

    def test_invalid_base64(self):
        assert _extract_signature_bytes("eth=:not-valid!:", "eth") is None


# =========================================================================
# 9. InMemoryNonceStore
# =========================================================================

class TestInMemoryNonceStore:
    @pytest.fixture
    def store(self):
        return InMemoryNonceStore()

    @pytest.mark.asyncio
    async def test_fresh_nonce(self, store):
        assert await store.consume("nonce:1", 300) is True

    @pytest.mark.asyncio
    async def test_replay_rejected(self, store):
        await store.consume("nonce:1", 300)
        assert await store.consume("nonce:1", 300) is False

    @pytest.mark.asyncio
    async def test_different_nonces(self, store):
        assert await store.consume("nonce:1", 300) is True
        assert await store.consume("nonce:2", 300) is True

    @pytest.mark.asyncio
    async def test_expired_evicted(self, store):
        await store.consume("nonce:1", 0)
        time.sleep(0.01)
        assert await store.consume("nonce:1", 300) is True

    @pytest.mark.asyncio
    async def test_generate(self, store):
        n1 = await store.generate()
        n2 = await store.generate()
        assert len(n1) > 20 and n1 != n2

    @pytest.mark.asyncio
    async def test_len(self, store):
        assert len(store) == 0
        await store.consume("a", 300)
        await store.consume("b", 300)
        assert len(store) == 2

    @pytest.mark.asyncio
    async def test_clear(self, store):
        await store.consume("a", 300)
        store.clear()
        assert len(store) == 0
        assert await store.consume("a", 300) is True


# =========================================================================
# 10. Full Verification Flow
# =========================================================================

@pytest.mark.skipif(not HAS_ETH_ACCOUNT, reason="eth_account not available")
class TestFullVerification:
    @pytest.fixture
    def nonce_store(self):
        return InMemoryNonceStore()

    async def _sign_request(self, request, private_key=TEST_PRIVATE_KEY,
                            components=None, nonce="test-nonce-abc",
                            chain_id=8453, created=None, expires=None, label="eth"):
        if components is None:
            components = ["@method", "@authority", "@path"]
        account = Account.from_key(private_key)
        address = account.address.lower()
        keyid = f"erc8128:{chain_id}:{address}"
        now = int(time.time())
        if created is None: created = now
        if expires is None: expires = now + 60
        params = {"created": created, "expires": expires, "keyid": keyid}
        if nonce: params["nonce"] = nonce
        sig_base = await _build_signature_base(request, label, components, params)
        sig_bytes = _sign_message(sig_base, private_key)
        sig_input = _make_sig_input(components, created=created, expires=expires,
                                     nonce=nonce, keyid=keyid, label=label)
        sig_b64 = base64.b64encode(sig_bytes).decode()
        request.headers["signature-input"] = sig_input
        request.headers["signature"] = f"{label}=:{sig_b64}:"
        return request

    @pytest.mark.asyncio
    async def test_valid_eoa_signature(self, nonce_store):
        req = MockRequest(method="POST", url=MockURL(query=""))
        req = await self._sign_request(req)
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is True
        assert result.address == TEST_ADDRESS
        assert result.chain_id == 8453
        assert result.binding == "request-bound"
        assert result.replayable is False

    @pytest.mark.asyncio
    async def test_replay_rejected(self, nonce_store):
        r1 = MockRequest(method="POST", url=MockURL(query=""))
        r1 = await self._sign_request(r1, nonce="replay-nonce")
        r2 = MockRequest(method="POST", url=MockURL(query=""))
        r2 = await self._sign_request(r2, nonce="replay-nonce")
        assert (await verify_erc8128_request(r1, nonce_store=nonce_store)).ok is True
        result = await verify_erc8128_request(r2, nonce_store=nonce_store)
        assert result.ok is False
        assert "replay" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_expired_rejected(self, nonce_store):
        req = MockRequest(method="POST", url=MockURL(query=""))
        now = int(time.time())
        req = await self._sign_request(req, created=now - 600, expires=now - 300)
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is False and "expired" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_future_rejected(self, nonce_store):
        req = MockRequest(method="POST", url=MockURL(query=""))
        now = int(time.time())
        req = await self._sign_request(req, created=now + 600, expires=now + 660)
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is False and "future" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_missing_signature_header(self, nonce_store):
        req = MockRequest(headers={"signature-input": "eth=()"})
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is False and "Missing Signature header" in result.reason

    @pytest.mark.asyncio
    async def test_missing_signature_input(self, nonce_store):
        req = MockRequest(headers={"signature": "eth=:abc:"})
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is False and "Missing Signature-Input" in result.reason

    @pytest.mark.asyncio
    async def test_replayable_rejected_by_default(self, nonce_store):
        req = MockRequest(method="POST", url=MockURL(query=""))
        req = await self._sign_request(req, nonce=None)
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is False and "replayable" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_replayable_accepted_with_policy(self, nonce_store):
        policy = VerifyPolicy(allow_replayable=True)
        req = MockRequest(method="POST", url=MockURL(query=""))
        req = await self._sign_request(req, nonce=None)
        result = await verify_erc8128_request(req, nonce_store=nonce_store, policy=policy)
        assert result.ok is True and result.replayable is True

    @pytest.mark.asyncio
    async def test_class_bound_rejected(self, nonce_store):
        req = MockRequest(method="POST", url=MockURL(query=""))
        req = await self._sign_request(req, components=["@authority"])
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is False and "class-bound" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_class_bound_accepted_with_policy(self, nonce_store):
        policy = VerifyPolicy(allow_class_bound=True)
        req = MockRequest(method="POST", url=MockURL(query=""))
        req = await self._sign_request(req, components=["@authority"])
        result = await verify_erc8128_request(req, nonce_store=nonce_store, policy=policy)
        assert result.ok is True and result.binding == "class-bound"

    @pytest.mark.asyncio
    async def test_content_digest_verified(self, nonce_store):
        body = b'{"title": "Verify store is open", "bounty_usd": 5.00}'
        digest = _make_content_digest(body)
        req = MockRequest(method="POST", url=MockURL(query=""),
                          headers={"content-digest": digest}, _body=body)
        req = await self._sign_request(req, components=["@method", "@authority", "@path", "content-digest"])
        assert (await verify_erc8128_request(req, nonce_store=nonce_store)).ok is True

    @pytest.mark.asyncio
    async def test_tampered_body_rejected(self, nonce_store):
        original = b'{"title": "Original"}'
        tampered = b'{"title": "Tampered"}'
        digest = _make_content_digest(original)
        req = MockRequest(method="POST", url=MockURL(query=""),
                          headers={"content-digest": digest}, _body=tampered)
        req = await self._sign_request(req, components=["@method", "@authority", "@path", "content-digest"])
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is False and "mismatch" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_wrong_address_in_keyid(self, nonce_store):
        req = MockRequest(method="POST", url=MockURL(query=""))
        req = await self._sign_request(req)
        req.headers["signature-input"] = req.headers["signature-input"].replace(
            TEST_ADDRESS, "0x0000000000000000000000000000000000000001")
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is False and "mismatch" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_different_chain_ids(self, nonce_store):
        for cid in [1, 8453, 11155111]:
            req = MockRequest(method="POST", url=MockURL(query=""))
            req = await self._sign_request(req, chain_id=cid, nonce=f"nonce-{cid}")
            result = await verify_erc8128_request(req, nonce_store=nonce_store)
            assert result.ok is True and result.chain_id == cid

    @pytest.mark.asyncio
    async def test_custom_label(self, nonce_store):
        req = MockRequest(method="POST", url=MockURL(query=""))
        req = await self._sign_request(req, label="sig1")
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is True and result.label == "sig1"

    @pytest.mark.asyncio
    async def test_get_with_query(self, nonce_store):
        req = MockRequest(method="GET", url=MockURL(path="/api/v1/tasks", query="status=open&limit=10"))
        req = await self._sign_request(req, components=["@method", "@authority", "@path", "@query"])
        result = await verify_erc8128_request(req, nonce_store=nonce_store)
        assert result.ok is True and result.binding == "request-bound"


# =========================================================================
# 11. ERC-1271 ABI Encoding
# =========================================================================

class TestERC1271Encoding:
    def test_encode_is_valid_signature(self):
        calldata = _encode_is_valid_signature(b"\x01" * 32, b"\x02" * 65)
        assert calldata.startswith("0x1626ba7e")
        assert "01" * 32 in calldata

    def test_encode_empty_signature(self):
        calldata = _encode_is_valid_signature(b"\x00" * 32, b"")
        assert calldata.startswith("0x1626ba7e")


# =========================================================================
# 12. AgentAuth & Dual Auth
# =========================================================================

class TestAgentAuth:
    def test_api_key_defaults(self):
        from api.auth import AgentAuth
        auth = AgentAuth(agent_id="test-agent", tier="starter")
        assert auth.auth_method == "api_key"
        assert auth.wallet_address is None

    def test_erc8128(self):
        from api.auth import AgentAuth
        auth = AgentAuth(agent_id="42", wallet_address="0xabc", auth_method="erc8128",
                         chain_id=8453, erc8004_registered=True, erc8004_agent_id=42)
        assert auth.auth_method == "erc8128"
        assert auth.chain_id == 8453

    @pytest.mark.asyncio
    async def test_generate_nonce(self):
        from api.auth import generate_auth_nonce
        reset_nonce_store()
        result = await generate_auth_nonce()
        assert "nonce" in result and result.get("ttl_seconds") == 300


# =========================================================================
# 13. Middleware Wallet Extraction
# =========================================================================

class TestMiddlewareWalletExtraction:
    def test_extract_wallet(self):
        from api.middleware import _extract_erc8128_wallet
        req = MockRequest(headers={
            "signature-input": 'eth=("@method");created=1;expires=2;keyid="erc8128:8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68"'
        })
        assert _extract_erc8128_wallet(req) == "0x742d35cc6634c0532925a3b844bc9e7595f2bd68"

    def test_no_erc8128(self):
        from api.middleware import _extract_erc8128_wallet
        req = MockRequest(headers={"signature-input": 'eth=("@method");created=1;expires=2'})
        assert _extract_erc8128_wallet(req) is None

    def test_no_header(self):
        from api.middleware import _extract_erc8128_wallet
        assert _extract_erc8128_wallet(MockRequest(headers={})) is None


# =========================================================================
# 14. Policy
# =========================================================================

class TestVerifyPolicy:
    def test_defaults(self):
        assert DEFAULT_POLICY.max_validity_sec == 300
        assert DEFAULT_POLICY.allow_replayable is False
        assert DEFAULT_POLICY.allow_class_bound is False

    def test_custom(self):
        p = VerifyPolicy(max_validity_sec=60, allow_replayable=True,
                         required_components={"content-digest"})
        assert p.max_validity_sec == 60
        assert "content-digest" in p.required_components

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_ETH_ACCOUNT, reason="eth_account not available")
    async def test_required_components_enforced(self):
        policy = VerifyPolicy(required_components={"content-digest"})
        store = InMemoryNonceStore()
        req = MockRequest(method="POST", url=MockURL(query=""))
        components = ["@method", "@authority", "@path"]
        now = int(time.time())
        params = {"created": now, "expires": now + 60, "nonce": "rc-test", "keyid": TEST_KEYID}
        sig_base = await _build_signature_base(req, "eth", components, params)
        sig_bytes = _sign_message(sig_base, TEST_PRIVATE_KEY)
        req.headers["signature-input"] = _make_sig_input(components, created=now,
            expires=now + 60, nonce="rc-test", keyid=TEST_KEYID)
        req.headers["signature"] = f"eth=:{base64.b64encode(sig_bytes).decode()}:"
        result = await verify_erc8128_request(req, nonce_store=store, policy=policy)
        assert result.ok is False and "content-digest" in result.reason


# =========================================================================
# 15. Nonce Store Factory
# =========================================================================

class TestNonceStoreFactory:
    def test_reset_and_get(self):
        reset_nonce_store()
        from integrations.erc8128.nonce_store import get_nonce_store
        assert isinstance(get_nonce_store(), InMemoryNonceStore)

    def test_singleton(self):
        reset_nonce_store()
        from integrations.erc8128.nonce_store import get_nonce_store
        assert get_nonce_store() is get_nonce_store()
