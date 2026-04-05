"""Tests for ERC-8128 Wallet-Based Authentication (80 tests)."""

import base64
import hashlib
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional
import pytest

pytestmark = pytest.mark.erc8128
sys.path.insert(0, str(Path(__file__).parent.parent))

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
    DynamoDBNonceStore,
    reset_nonce_store,
)
from integrations.erc8128.erc1271 import _encode_is_valid_signature


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


def _sig_input(
    components,
    created=None,
    expires=None,
    nonce="test-nonce",
    keyid="erc8128:8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68",
    label="eth",
):
    now = int(time.time())
    c, e = created or now, expires or now + 60
    comp_str = " ".join(f'"{x}"' for x in components)
    parts = [f"({comp_str})", f"created={c}", f"expires={e}"]
    if nonce is not None:
        parts.append(f'nonce="{nonce}"')
    parts.append(f'keyid="{keyid}"')
    return f"{label}={';'.join(parts)}"


def _content_digest(body):
    return f"sha-256=:{base64.b64encode(hashlib.sha256(body).digest()).decode()}:"


try:
    from eth_account import Account
    from eth_account.messages import encode_defunct

    HAS_ETH = True
except ImportError:
    HAS_ETH = False


def _sign(message, key):
    if not HAS_ETH:
        pytest.skip("eth_account not available")
    return Account.sign_message(encode_defunct(text=message), private_key=key).signature


PK = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
ADDR = (
    Account.from_key(PK).address.lower()
    if HAS_ETH
    else "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
)
KEYID = f"erc8128:8453:{ADDR}"


class TestKeyIdParsing:
    def test_valid(self):
        assert KEYID_RE.match("erc8128:8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68")

    def test_chain_1(self):
        assert KEYID_RE.match("erc8128:1:0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")

    def test_lowercase(self):
        assert KEYID_RE.match("erc8128:8453:0xabcdef1234567890abcdef1234567890abcdef12")

    def test_no_prefix(self):
        assert not KEYID_RE.match("8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68")

    def test_wrong_prefix(self):
        assert not KEYID_RE.match(
            "eip4361:8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68"
        )

    def test_short_addr(self):
        assert not KEYID_RE.match("erc8128:8453:0x742d35Cc")

    def test_no_chain(self):
        assert not KEYID_RE.match("erc8128::0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68")

    def test_no_0x(self):
        assert not KEYID_RE.match(
            "erc8128:8453:742d35Cc6634C0532925a3b844Bc9e7595f2bD68"
        )


class TestSigInputParsing:
    def test_basic(self):
        l, c, p = _parse_signature_input(
            'eth=("@method" "@authority" "@path");created=1700000000;expires=1700000060;nonce="abc";keyid="erc8128:1:0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"'
        )
        assert (
            l == "eth"
            and c == ["@method", "@authority", "@path"]
            and p["created"] == 1700000000
        )

    def test_non_eth(self):
        assert (
            _parse_signature_input(
                'sig1=("@method");created=100;expires=200;keyid="k"'
            )[0]
            == "sig1"
        )

    def test_strict_rejects(self):
        assert (
            _parse_signature_input(
                'sig1=("@method");created=100;expires=200;keyid="k"', strict_label=True
            )[0]
            is None
        )

    def test_strict_accepts(self):
        assert (
            _parse_signature_input(
                'eth=("@method");created=100;expires=200;keyid="k"', strict_label=True
            )[0]
            == "eth"
        )

    def test_prefers_eth(self):
        assert (
            _parse_signature_input(
                'sig1=("@method");created=1;expires=2;keyid="x", eth=("@authority");created=3;expires=4;keyid="y"'
            )[0]
            == "eth"
        )

    def test_empty(self):
        assert _parse_signature_input("")[0] is None

    def test_content_digest(self):
        assert (
            "content-digest"
            in _parse_signature_input(
                'eth=("@method" "content-digest");created=100;expires=200;keyid="k"'
            )[1]
        )

    def test_query(self):
        assert (
            "@query"
            in _parse_signature_input(
                'eth=("@method" "@query");created=100;expires=200;keyid="k"'
            )[1]
        )


class TestTimestamps:
    def test_valid(self):
        now = int(time.time())
        assert _validate_timestamps(now, now + 60, DEFAULT_POLICY) is None

    def test_expired(self):
        now = int(time.time())
        assert (
            "expired"
            in _validate_timestamps(now - 600, now - 300, DEFAULT_POLICY).lower()
        )

    def test_future(self):
        now = int(time.time())
        assert (
            "future"
            in _validate_timestamps(now + 600, now + 660, DEFAULT_POLICY).lower()
        )

    def test_expires_before(self):
        now = int(time.time())
        assert "greater" in _validate_timestamps(now + 60, now, DEFAULT_POLICY).lower()

    def test_window_large(self):
        now = int(time.time())
        assert (
            "too large" in _validate_timestamps(now, now + 600, DEFAULT_POLICY).lower()
        )

    def test_clock_skew(self):
        now = int(time.time())
        assert _validate_timestamps(now + 20, now + 80, DEFAULT_POLICY) is None

    def test_non_integer(self):
        assert "integer" in _validate_timestamps("abc", "def", DEFAULT_POLICY).lower()

    def test_custom_max(self):
        now = int(time.time())
        assert (
            "too large"
            in _validate_timestamps(
                now, now + 60, VerifyPolicy(max_validity_sec=30)
            ).lower()
        )


class TestBinding:
    def test_request_bound(self):
        assert (
            _determine_binding(
                MockRequest(url=MockURL(query="")), ["@method", "@authority", "@path"]
            )
            == "request-bound"
        )

    def test_with_query(self):
        assert (
            _determine_binding(
                MockRequest(url=MockURL(query="a=1")),
                ["@method", "@authority", "@path", "@query"],
            )
            == "request-bound"
        )

    def test_no_method(self):
        assert (
            _determine_binding(
                MockRequest(url=MockURL(query="")), ["@authority", "@path"]
            )
            == "class-bound"
        )

    def test_no_authority(self):
        assert (
            _determine_binding(MockRequest(url=MockURL(query="")), ["@method", "@path"])
            == "class-bound"
        )

    def test_query_uncovered(self):
        assert (
            _determine_binding(
                MockRequest(url=MockURL(query="p=v")),
                ["@method", "@authority", "@path"],
            )
            == "class-bound"
        )


class TestContentDigest:
    @pytest.mark.asyncio
    async def test_valid(self):
        b = b'{"t":1}'
        assert (
            await _verify_content_digest(
                MockRequest(headers={"content-digest": _content_digest(b)}, _body=b)
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_mismatch(self):
        assert (
            "mismatch"
            in (
                await _verify_content_digest(
                    MockRequest(
                        headers={"content-digest": _content_digest(b"wrong")},
                        _body=b"actual",
                    )
                )
            ).lower()
        )

    @pytest.mark.asyncio
    async def test_missing(self):
        assert (
            "missing"
            in (
                await _verify_content_digest(MockRequest(headers={}, _body=b"x"))
            ).lower()
        )

    @pytest.mark.asyncio
    async def test_empty_body(self):
        assert (
            await _verify_content_digest(
                MockRequest(headers={"content-digest": _content_digest(b"")}, _body=b"")
            )
            is None
        )


class TestSigBase:
    @pytest.mark.asyncio
    async def test_basic(self):
        sb = await _build_signature_base(
            MockRequest(method="POST", url=MockURL(path="/api/v1/tasks")),
            "eth",
            ["@method", "@authority", "@path"],
            {"created": 100, "expires": 200, "keyid": "k"},
        )
        assert '"@method": POST' in sb and '"@signature-params":' in sb

    @pytest.mark.asyncio
    async def test_query(self):
        sb = await _build_signature_base(
            MockRequest(method="GET", url=MockURL(query="s=1")),
            "eth",
            ["@method", "@authority", "@path", "@query"],
            {"created": 100, "expires": 200, "keyid": "k"},
        )
        assert '"@query": ?s=1' in sb

    @pytest.mark.asyncio
    async def test_digest(self):
        d = _content_digest(b'{"t":1}')
        sb = await _build_signature_base(
            MockRequest(headers={"content-digest": d}),
            "eth",
            ["@method", "content-digest"],
            {"created": 100, "expires": 200, "keyid": "k"},
        )
        assert f'"content-digest": {d}' in sb

    @pytest.mark.asyncio
    async def test_param_order(self):
        sb = await _build_signature_base(
            MockRequest(),
            "eth",
            ["@method"],
            {"keyid": "k", "nonce": "n", "expires": 200, "created": 100},
        )
        p = [l for l in sb.split("\n") if "@signature-params" in l][0]
        assert p.index("created=") < p.index("expires=") < p.index("nonce=")


@pytest.mark.skipif(not HAS_ETH, reason="eth_account not available")
class TestEIP191:
    def test_valid(self):
        assert _eip191_recover("test", _sign("test", PK)) == ADDR

    def test_wrong_msg(self):
        assert _eip191_recover("tampered", _sign("original", PK)) != ADDR

    def test_invalid_sig(self):
        r = _eip191_recover("test", b"\x00" * 65)
        assert r is None or r != ADDR

    def test_empty_sig(self):
        assert _eip191_recover("test", b"") is None


class TestSigExtraction:
    def test_valid(self):
        d = b"\x01\x02\x03"
        assert (
            _extract_signature_bytes(f"eth=:{base64.b64encode(d).decode()}:", "eth")
            == d
        )

    def test_wrong_label(self):
        assert _extract_signature_bytes("eth=:AQIDBA==:", "sig1") is None

    def test_bad_b64(self):
        assert _extract_signature_bytes("eth=no-colon-wrapping", "eth") is None


class TestNonceStore:
    @pytest.fixture
    def store(self):
        return InMemoryNonceStore()

    @pytest.mark.asyncio
    async def test_fresh(self, store):
        assert await store.consume("n:1", 300) is True

    @pytest.mark.asyncio
    async def test_replay(self, store):
        await store.consume("n:1", 300)
        assert await store.consume("n:1", 300) is False

    @pytest.mark.asyncio
    async def test_different(self, store):
        assert await store.consume("n:1", 300) and await store.consume("n:2", 300)

    @pytest.mark.asyncio
    async def test_expired(self, store):
        await store.consume("n:1", 0)
        time.sleep(0.01)
        assert await store.consume("n:1", 300) is True

    @pytest.mark.asyncio
    async def test_generate(self, store):
        n1, n2 = await store.generate(), await store.generate()
        assert len(n1) > 20 and n1 != n2

    @pytest.mark.asyncio
    async def test_len(self, store):
        await store.consume("a", 300)
        await store.consume("b", 300)
        assert len(store) == 2

    @pytest.mark.asyncio
    async def test_clear(self, store):
        await store.consume("a", 300)
        store.clear()
        assert len(store) == 0 and await store.consume("a", 300) is True


class TestDynamoDBNonceStore:
    """Tests for DynamoDBNonceStore — verifies async wrapping of sync boto3 calls."""

    @pytest.mark.asyncio
    async def test_consume_fresh_nonce(self):
        """DynamoDB consume returns True for fresh nonce via asyncio.to_thread."""
        from unittest.mock import MagicMock

        mock_table = MagicMock()
        mock_table.put_item = MagicMock()  # No exception = fresh nonce

        store = DynamoDBNonceStore(table_name="test-table")
        store._table = mock_table

        result = await store.consume("erc8128:8453:0xabc:nonce1", 300)
        assert result is True
        mock_table.put_item.assert_called_once()
        call_kwargs = mock_table.put_item.call_args[1]
        assert call_kwargs["Item"]["nonce_key"] == "erc8128:8453:0xabc:nonce1"
        assert call_kwargs["ConditionExpression"] == "attribute_not_exists(nonce_key)"

    @pytest.mark.asyncio
    async def test_consume_replay_detected(self):
        """DynamoDB consume returns False when ConditionalCheckFailedException."""
        from unittest.mock import MagicMock
        from botocore.exceptions import ClientError

        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "exists"}},
            "PutItem",
        )

        store = DynamoDBNonceStore(table_name="test-table")
        store._table = mock_table

        result = await store.consume("erc8128:8453:0xabc:replay", 300)
        assert result is False

    @pytest.mark.asyncio
    async def test_consume_other_error_raises(self):
        """DynamoDB consume re-raises non-conditional ClientError."""
        from unittest.mock import MagicMock
        from botocore.exceptions import ClientError

        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {
                "Error": {
                    "Code": "ProvisionedThroughputExceededException",
                    "Message": "throttled",
                }
            },
            "PutItem",
        )

        store = DynamoDBNonceStore(table_name="test-table")
        store._table = mock_table

        with pytest.raises(ClientError):
            await store.consume("erc8128:8453:0xabc:err", 300)

    @pytest.mark.asyncio
    async def test_consume_runs_in_thread(self):
        """Verify consume dispatches to a thread (does not block event loop)."""
        import asyncio
        from unittest.mock import MagicMock, patch

        mock_table = MagicMock()
        mock_table.put_item = MagicMock()

        store = DynamoDBNonceStore(table_name="test-table")
        store._table = mock_table

        with patch(
            "integrations.erc8128.nonce_store.asyncio.to_thread",
            wraps=asyncio.to_thread,
        ) as mock_to_thread:
            result = await store.consume("erc8128:8453:0xabc:thread", 300)
            assert result is True
            mock_to_thread.assert_called_once_with(
                store._sync_put_item, "erc8128:8453:0xabc:thread", 300
            )

    @pytest.mark.asyncio
    async def test_generate(self):
        """DynamoDB store generates unique nonces."""
        store = DynamoDBNonceStore(table_name="test-table")
        n1, n2 = await store.generate(), await store.generate()
        assert len(n1) > 20 and n1 != n2


@pytest.mark.skipif(not HAS_ETH, reason="eth_account not available")
class TestFullVerification:
    @pytest.fixture
    def ns(self):
        return InMemoryNonceStore()

    async def _sign_req(
        self,
        req,
        components=None,
        nonce="test-nonce",
        chain_id=8453,
        created=None,
        expires=None,
        label="eth",
    ):
        if components is None:
            components = ["@method", "@authority", "@path"]
        addr = Account.from_key(PK).address.lower()
        keyid = f"erc8128:{chain_id}:{addr}"
        now = int(time.time())
        c, e = created or now, expires or now + 60
        params = {"created": c, "expires": e, "keyid": keyid}
        if nonce:
            params["nonce"] = nonce
        sb = await _build_signature_base(req, label, components, params)
        sig = _sign(sb, PK)
        req.headers["signature-input"] = _sig_input(
            components, created=c, expires=e, nonce=nonce, keyid=keyid, label=label
        )
        req.headers["signature"] = f"{label}=:{base64.b64encode(sig).decode()}:"
        return req

    @pytest.mark.asyncio
    async def test_valid_eoa(self, ns):
        r = await self._sign_req(MockRequest(method="POST", url=MockURL(query="")))
        res = await verify_erc8128_request(r, nonce_store=ns)
        assert (
            res.ok
            and res.address == ADDR
            and res.chain_id == 8453
            and res.binding == "request-bound"
        )

    @pytest.mark.asyncio
    async def test_replay(self, ns):
        r1 = await self._sign_req(
            MockRequest(method="POST", url=MockURL(query="")), nonce="rp"
        )
        r2 = await self._sign_req(
            MockRequest(method="POST", url=MockURL(query="")), nonce="rp"
        )
        assert (await verify_erc8128_request(r1, nonce_store=ns)).ok
        assert not (await verify_erc8128_request(r2, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_expired(self, ns):
        now = int(time.time())
        r = await self._sign_req(
            MockRequest(method="POST", url=MockURL(query="")),
            created=now - 600,
            expires=now - 300,
        )
        assert not (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_future(self, ns):
        now = int(time.time())
        r = await self._sign_req(
            MockRequest(method="POST", url=MockURL(query="")),
            created=now + 600,
            expires=now + 660,
        )
        assert not (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_missing_sig(self, ns):
        assert not (
            await verify_erc8128_request(
                MockRequest(headers={"signature-input": "eth=()"}), nonce_store=ns
            )
        ).ok

    @pytest.mark.asyncio
    async def test_missing_input(self, ns):
        assert not (
            await verify_erc8128_request(
                MockRequest(headers={"signature": "eth=:abc:"}), nonce_store=ns
            )
        ).ok

    @pytest.mark.asyncio
    async def test_replayable_rejected(self, ns):
        r = await self._sign_req(
            MockRequest(method="POST", url=MockURL(query="")), nonce=None
        )
        assert not (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_replayable_accepted(self, ns):
        r = await self._sign_req(
            MockRequest(method="POST", url=MockURL(query="")), nonce=None
        )
        assert (
            await verify_erc8128_request(
                r, nonce_store=ns, policy=VerifyPolicy(allow_replayable=True)
            )
        ).ok

    @pytest.mark.asyncio
    async def test_class_bound_rejected(self, ns):
        r = await self._sign_req(
            MockRequest(method="POST", url=MockURL(query="")), components=["@authority"]
        )
        assert not (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_class_bound_accepted(self, ns):
        r = await self._sign_req(
            MockRequest(method="POST", url=MockURL(query="")), components=["@authority"]
        )
        assert (
            await verify_erc8128_request(
                r, nonce_store=ns, policy=VerifyPolicy(allow_class_bound=True)
            )
        ).ok

    @pytest.mark.asyncio
    async def test_content_digest_ok(self, ns):
        body = b'{"title": "Test", "bounty_usd": 5.00}'
        r = MockRequest(
            method="POST",
            url=MockURL(query=""),
            headers={"content-digest": _content_digest(body)},
            _body=body,
        )
        r = await self._sign_req(
            r, components=["@method", "@authority", "@path", "content-digest"]
        )
        assert (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_tampered_body(self, ns):
        r = MockRequest(
            method="POST",
            url=MockURL(query=""),
            headers={"content-digest": _content_digest(b'{"a":1}')},
            _body=b'{"a":2}',
        )
        r = await self._sign_req(
            r, components=["@method", "@authority", "@path", "content-digest"]
        )
        assert not (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_wrong_address(self, ns):
        r = await self._sign_req(MockRequest(method="POST", url=MockURL(query="")))
        r.headers["signature-input"] = r.headers["signature-input"].replace(
            ADDR, "0x0000000000000000000000000000000000000001"
        )
        assert not (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_chain_ids(self, ns):
        for cid in [1, 8453, 11155111]:
            r = await self._sign_req(
                MockRequest(method="POST", url=MockURL(query="")),
                chain_id=cid,
                nonce=f"n-{cid}",
            )
            assert (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_custom_label(self, ns):
        r = await self._sign_req(
            MockRequest(method="POST", url=MockURL(query="")), label="sig1"
        )
        assert (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_get_with_query(self, ns):
        r = await self._sign_req(
            MockRequest(method="GET", url=MockURL(query="s=1&l=10")),
            components=["@method", "@authority", "@path", "@query"],
        )
        assert (await verify_erc8128_request(r, nonce_store=ns)).ok

    @pytest.mark.asyncio
    async def test_no_nonce_store(self, ns):
        r = await self._sign_req(MockRequest(method="POST", url=MockURL(query="")))
        assert (await verify_erc8128_request(r, nonce_store=None)).ok


class TestERC1271:
    def test_encode(self):
        assert _encode_is_valid_signature(b"\x01" * 32, b"\x02" * 65).startswith(
            "0x1626ba7e"
        )

    def test_empty_sig(self):
        assert _encode_is_valid_signature(b"\x00" * 32, b"").startswith("0x1626ba7e")

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_ETH, reason="eth_account not available")
    async def test_erc1271_fallback_called(self):
        """Verify ERC-1271 fallback is attempted when ecrecover mismatches (e.g., SCA wallet)."""
        from integrations.erc8128.verifier import _try_erc1271_fallback

        # With no RPC, fallback should return (False, error_reason) gracefully (not crash)
        result, error_reason = await _try_erc1271_fallback(
            "0x0000000000000000000000000000000000000001",
            "test message",
            b"\x00" * 65,
            8453,
        )
        assert result is False  # No RPC available, but no crash

    def test_cache_bounded(self):
        """Verify _SCA_CACHE does not grow beyond _SCA_CACHE_MAX_SIZE."""
        from integrations.erc8128.erc1271 import (
            _SCA_CACHE,
            _SCA_CACHE_MAX_SIZE,
            _cache_put,
            clear_sca_cache,
        )

        clear_sca_cache()
        for i in range(_SCA_CACHE_MAX_SIZE + 50):
            _cache_put(f"0xaddr:{i:064x}", True)
        assert len(_SCA_CACHE) == _SCA_CACHE_MAX_SIZE
        clear_sca_cache()

    def test_cache_lru_eviction_order(self):
        """Verify LRU eviction removes oldest entries first."""
        from integrations.erc8128.erc1271 import (
            _SCA_CACHE_MAX_SIZE,
            _cache_put,
            _cache_get,
            clear_sca_cache,
        )

        clear_sca_cache()
        for i in range(_SCA_CACHE_MAX_SIZE):
            _cache_put(f"key:{i}", True)
        # Access the first entry to make it recently used
        _cache_get("key:0")
        # Add one more — should evict key:1 (oldest untouched), not key:0
        _cache_put("key:new", True)
        assert _cache_get("key:0") is True, (
            "key:0 was accessed recently and should not be evicted"
        )
        assert _cache_get("key:1") is None, (
            "key:1 should have been evicted as the oldest"
        )
        assert _cache_get("key:new") is True
        clear_sca_cache()

    def test_cache_ttl_expiry(self):
        """Verify expired entries are evicted on access."""
        from integrations.erc8128.erc1271 import (
            _SCA_CACHE,
            _cache_put,
            _cache_get,
            clear_sca_cache,
            _SCA_CACHE_TTL,
        )

        clear_sca_cache()
        _cache_put("expired_key", True)
        # Manually backdate the timestamp so it appears expired
        _SCA_CACHE["expired_key"] = (True, time.time() - _SCA_CACHE_TTL - 1)
        assert _cache_get("expired_key") is None
        assert "expired_key" not in _SCA_CACHE
        clear_sca_cache()

    def test_rpc_urls_cover_all_chains(self):
        """Verify _RPC_URLS covers all EVM chains from NETWORK_CONFIG."""
        from integrations.erc8128.erc1271 import _RPC_URLS
        from integrations.x402.sdk_client import NETWORK_CONFIG

        for name, cfg in NETWORK_CONFIG.items():
            chain_id = cfg["chain_id"]
            if chain_id is None:
                continue  # Non-EVM networks (e.g. Solana) have no chain ID
            assert chain_id in _RPC_URLS, (
                f"Chain {name} (id={chain_id}) missing from _RPC_URLS"
            )


class TestAgentAuth:
    def test_api_key(self):
        from api.auth import AgentAuth

        a = AgentAuth(agent_id="t", tier="starter")
        assert a.auth_method == "api_key"

    def test_erc8128(self):
        from api.auth import AgentAuth

        a = AgentAuth(
            agent_id="42", wallet_address="0xabc", auth_method="erc8128", chain_id=8453
        )
        assert a.auth_method == "erc8128"

    @pytest.mark.asyncio
    async def test_nonce(self):
        from api.auth import generate_auth_nonce, _nonce_requests

        reset_nonce_store()
        _nonce_requests.clear()
        mock_req = MockRequest(headers={"X-Forwarded-For": "10.0.0.1"})
        r = await generate_auth_nonce(mock_req)
        assert r.get("nonce") and r.get("ttl_seconds") == 300


class TestMiddleware:
    def test_extract(self):
        from api.middleware import _extract_erc8128_wallet

        assert (
            _extract_erc8128_wallet(
                MockRequest(
                    headers={
                        "signature-input": 'eth=("@method");keyid="erc8128:8453:0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68"'
                    }
                )
            )
            == "0x742d35cc6634c0532925a3b844bc9e7595f2bd68"
        )

    def test_no_erc8128(self):
        from api.middleware import _extract_erc8128_wallet

        assert (
            _extract_erc8128_wallet(MockRequest(headers={"signature-input": "eth=()"}))
            is None
        )

    def test_no_header(self):
        from api.middleware import _extract_erc8128_wallet

        assert _extract_erc8128_wallet(MockRequest(headers={})) is None


class TestPolicy:
    def test_defaults(self):
        assert (
            DEFAULT_POLICY.max_validity_sec == 300
            and not DEFAULT_POLICY.allow_replayable
        )

    def test_custom(self):
        p = VerifyPolicy(max_validity_sec=60, required_components={"content-digest"})
        assert "content-digest" in p.required_components

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_ETH, reason="eth_account not available")
    async def test_required_components(self):
        store = InMemoryNonceStore()
        now = int(time.time())
        req = MockRequest(method="POST", url=MockURL(query=""))
        comps = ["@method", "@authority", "@path"]
        params = {"created": now, "expires": now + 60, "nonce": "rc", "keyid": KEYID}
        sb = await _build_signature_base(req, "eth", comps, params)
        sig = _sign(sb, PK)
        req.headers["signature-input"] = _sig_input(
            comps, created=now, expires=now + 60, nonce="rc", keyid=KEYID
        )
        req.headers["signature"] = f"eth=:{base64.b64encode(sig).decode()}:"
        res = await verify_erc8128_request(
            req,
            nonce_store=store,
            policy=VerifyPolicy(required_components={"content-digest"}),
        )
        assert not res.ok and "content-digest" in res.reason


class TestFactory:
    def test_reset(self):
        reset_nonce_store()
        from integrations.erc8128.nonce_store import get_nonce_store

        assert isinstance(get_nonce_store(), InMemoryNonceStore)

    def test_singleton(self):
        reset_nonce_store()
        from integrations.erc8128.nonce_store import get_nonce_store

        assert get_nonce_store() is get_nonce_store()


# =============================================================================
# Signer Tests (Task 0.5)
# =============================================================================

# Aliases for clarity in signer tests
PRIVATE_KEY = PK
EXPECTED_ADDR = ADDR


def FakeRequest(method, headers, path, body_bytes):
    """Create a MockRequest compatible with the verifier."""
    return MockRequest(
        method=method,
        url=MockURL(path=path),
        headers=headers,
        _body=body_bytes,
    )


class TestSigner:
    """Test ERC-8128 signer module."""

    def test_sign_request_returns_headers(self):
        from integrations.erc8128.signer import sign_request

        headers = sign_request(
            private_key=PRIVATE_KEY,
            method="POST",
            url="https://api.execution.market/api/v1/tasks",
            body='{"title": "test"}',
            nonce="test-nonce-1",
            chain_id=8453,
        )
        assert "Signature" in headers
        assert "Signature-Input" in headers
        assert "Content-Digest" in headers
        assert headers["Signature"].startswith("eth=:")
        assert headers["Signature-Input"].startswith("eth=")

    def test_sign_request_no_body(self):
        from integrations.erc8128.signer import sign_request

        headers = sign_request(
            private_key=PRIVATE_KEY,
            method="GET",
            url="https://api.execution.market/api/v1/tasks",
            nonce="test-nonce-2",
            chain_id=8453,
        )
        assert "Signature" in headers
        assert "Signature-Input" in headers
        assert "Content-Digest" not in headers

    def test_sign_request_includes_query(self):
        from integrations.erc8128.signer import sign_request

        headers = sign_request(
            private_key=PRIVATE_KEY,
            method="GET",
            url="https://api.execution.market/api/v1/tasks?status=published",
            nonce="test-nonce-3",
            chain_id=8453,
        )
        assert "@query" in headers["Signature-Input"]


class TestSignerRoundtrip:
    """Sign with signer, verify with verifier — full roundtrip."""

    @pytest.mark.asyncio
    async def test_roundtrip_post_with_body(self):
        from integrations.erc8128.signer import sign_request

        body = '{"title": "roundtrip test", "bounty": 0.10}'
        url = "https://api.execution.market/api/v1/tasks"
        nonce_val = f"roundtrip-{int(time.time())}"

        headers = sign_request(
            private_key=PRIVATE_KEY,
            method="POST",
            url=url,
            body=body,
            nonce=nonce_val,
            chain_id=8453,
        )

        # Build a fake request that the verifier can process
        request = FakeRequest(
            method="POST",
            headers={
                "signature": headers["Signature"],
                "signature-input": headers["Signature-Input"],
                "content-digest": headers["Content-Digest"],
                "host": "api.execution.market",
            },
            path="/api/v1/tasks",
            body_bytes=body.encode("utf-8"),
        )

        result = await verify_erc8128_request(
            request, policy=VerifyPolicy(allow_replayable=True)
        )
        assert result.ok, f"Verification failed: {result.reason}"
        assert result.address == EXPECTED_ADDR.lower()
        assert result.chain_id == 8453

    @pytest.mark.asyncio
    async def test_roundtrip_get_no_body(self):
        from integrations.erc8128.signer import sign_request

        url = "https://api.execution.market/api/v1/tasks"
        nonce_val = f"roundtrip-get-{int(time.time())}"

        headers = sign_request(
            private_key=PRIVATE_KEY,
            method="GET",
            url=url,
            nonce=nonce_val,
            chain_id=8453,
        )

        request = FakeRequest(
            method="GET",
            headers={
                "signature": headers["Signature"],
                "signature-input": headers["Signature-Input"],
                "host": "api.execution.market",
            },
            path="/api/v1/tasks",
            body_bytes=b"",
        )

        result = await verify_erc8128_request(
            request, policy=VerifyPolicy(allow_replayable=True)
        )
        assert result.ok, f"Verification failed: {result.reason}"
        assert result.address == EXPECTED_ADDR.lower()

    @pytest.mark.asyncio
    async def test_roundtrip_with_nonce_store(self):
        """Roundtrip using the in-memory nonce store (nonce consumed on first verify)."""
        from integrations.erc8128.signer import sign_request

        nonce_val = f"nonce-store-{int(time.time())}"
        body = '{"test": true}'
        url = "https://api.execution.market/api/v1/tasks"

        headers = sign_request(
            private_key=PRIVATE_KEY,
            method="POST",
            url=url,
            body=body,
            nonce=nonce_val,
            chain_id=8453,
        )

        nonce_store = InMemoryNonceStore()

        request = FakeRequest(
            method="POST",
            headers={
                "signature": headers["Signature"],
                "signature-input": headers["Signature-Input"],
                "content-digest": headers["Content-Digest"],
                "host": "api.execution.market",
            },
            path="/api/v1/tasks",
            body_bytes=body.encode("utf-8"),
        )

        # First verification should succeed
        result = await verify_erc8128_request(request, nonce_store=nonce_store)
        assert result.ok, f"First verify failed: {result.reason}"

        # Replay should fail (nonce already consumed)
        result2 = await verify_erc8128_request(request, nonce_store=nonce_store)
        assert not result2.ok
        assert (
            "nonce" in (result2.reason or "").lower()
            or "replay" in (result2.reason or "").lower()
        )
