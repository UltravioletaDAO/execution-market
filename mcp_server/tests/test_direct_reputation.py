"""
Tests for direct on-chain reputation feedback (bypassing Facilitator).

Tests the give_feedback_direct() function and the modified rate_worker()/rate_agent()
flows that use direct on-chain calls instead of the Facilitator.
"""

import importlib
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.erc8004

# ---------------------------------------------------------------------------
# Module stubbing: ensure patch() can resolve dotted paths without triggering
# heavy imports (web3, httpx, eth_account, etc.) that may not fully load.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

# Stub packages with __path__ so reload() works
_PACKAGES = {
    "integrations": str(Path(__file__).parent.parent / "integrations"),
    "integrations.erc8004": str(
        Path(__file__).parent.parent / "integrations" / "erc8004"
    ),
    "integrations.x402": str(Path(__file__).parent.parent / "integrations" / "x402"),
}
for _pkg, _pkg_path in _PACKAGES.items():
    if _pkg not in sys.modules:
        _stub = ModuleType(_pkg)
        _stub.__path__ = [_pkg_path]
        _stub.__package__ = _pkg
        sys.modules[_pkg] = _stub

# Stub leaf modules that might fail to import
_LEAF_STUBS = {
    "integrations.erc8004.register": {"ERC8004Registry": None},
    "integrations.erc8004.reputation": {"ReputationManager": None},
    "integrations.erc8004.identity": {
        "verify_agent_identity": None,
        "check_worker_identity": None,
        "register_worker_gasless": None,
        "update_executor_identity": None,
    },
    "integrations.erc8004.feedback_store": {"persist_and_hash_feedback": None},
    "integrations.x402.sdk_client": {
        "NETWORK_CONFIG": {
            "base": {
                "chain_id": 8453,
                "usdc": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            },
        },
    },
}
for _mod_name, _attrs in _LEAF_STUBS.items():
    if _mod_name not in sys.modules:
        _stub = ModuleType(_mod_name)
        for _k, _v in _attrs.items():
            setattr(_stub, _k, _v)
        sys.modules[_mod_name] = _stub

# Now load the real modules we're testing
_fc_mod = importlib.import_module("integrations.erc8004.facilitator_client")
importlib.reload(_fc_mod)
sys.modules["integrations.erc8004.facilitator_client"] = _fc_mod

_dr_mod = importlib.import_module("integrations.erc8004.direct_reputation")
importlib.reload(_dr_mod)
sys.modules["integrations.erc8004.direct_reputation"] = _dr_mod

# Also reload feedback_store so we can test _extract_s3_key and FEEDBACK_PUBLIC_URL
_fs_mod = importlib.import_module("integrations.erc8004.feedback_store")
importlib.reload(_fs_mod)
sys.modules["integrations.erc8004.feedback_store"] = _fs_mod


# ============================================================================
# give_feedback_direct() tests
# ============================================================================


class TestGiveFeedbackDirect:
    """Tests for the direct on-chain giveFeedback() call."""

    @pytest.mark.asyncio
    async def test_successful_feedback(self):
        """Successful TX returns FeedbackResult with tx hash."""
        mock_receipt = {"status": 1, "from": "0xD386..."}
        mock_tx_hash = MagicMock()
        mock_tx_hash.hex.return_value = "0xabc123"

        mock_w3 = MagicMock()
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.get_transaction_count.return_value = 5
        mock_w3.eth.estimate_gas.return_value = 150000
        mock_w3.eth.send_raw_transaction.return_value = mock_tx_hash
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        mock_account = MagicMock()
        mock_account.address = "0xD3868E1eD738CED6945A574a7c769433BeD5d474"
        mock_w3.eth.account.from_key.return_value = mock_account
        mock_w3.eth.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b"\x00"
        )

        # Mock contract
        mock_contract = MagicMock()
        mock_func = MagicMock()
        mock_func.build_transaction.return_value = {
            "from": mock_account.address,
            "chainId": 8453,
            "gas": 200000,
            "gasPrice": 1000000000,
            "nonce": 5,
        }
        mock_contract.functions.giveFeedback.return_value = mock_func
        mock_w3.eth.contract.return_value = mock_contract

        with (
            patch(
                "integrations.erc8004.direct_reputation._get_web3",
                return_value=mock_w3,
            ),
            patch.dict(
                "os.environ",
                {"WALLET_PRIVATE_KEY": "0x" + "ab" * 32},
            ),
        ):
            from integrations.erc8004.direct_reputation import give_feedback_direct

            result = await give_feedback_direct(
                agent_id=999,
                value=85,
                tag1="worker_rating",
                tag2="0xABC...",
                endpoint="task:test-123",
                feedback_uri="https://cdn.example.com/feedback.json",
                feedback_hash="0x" + "ff" * 32,
            )

        assert result.success is True
        assert result.transaction_hash == "0xabc123"

    @pytest.mark.asyncio
    async def test_reverted_transaction(self):
        """Reverted TX (e.g. self-feedback) returns failure."""
        mock_receipt = {"status": 0, "from": "0xD386..."}
        mock_tx_hash = MagicMock()
        mock_tx_hash.hex.return_value = "0xdead"

        mock_w3 = MagicMock()
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.get_transaction_count.return_value = 0
        mock_w3.eth.estimate_gas.return_value = 150000
        mock_w3.eth.send_raw_transaction.return_value = mock_tx_hash
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        mock_account = MagicMock()
        mock_account.address = "0xD3868E1eD738CED6945A574a7c769433BeD5d474"
        mock_w3.eth.account.from_key.return_value = mock_account
        mock_w3.eth.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b"\x00"
        )

        mock_contract = MagicMock()
        mock_func = MagicMock()
        mock_func.build_transaction.return_value = {
            "from": mock_account.address,
            "chainId": 8453,
            "gas": 200000,
            "gasPrice": 1000000000,
            "nonce": 0,
        }
        mock_contract.functions.giveFeedback.return_value = mock_func
        mock_w3.eth.contract.return_value = mock_contract

        with (
            patch(
                "integrations.erc8004.direct_reputation._get_web3",
                return_value=mock_w3,
            ),
            patch.dict(
                "os.environ",
                {"WALLET_PRIVATE_KEY": "0x" + "ab" * 32},
            ),
        ):
            from integrations.erc8004.direct_reputation import give_feedback_direct

            result = await give_feedback_direct(
                agent_id=2106,
                value=90,
                tag1="agent_rating",
            )

        assert result.success is False
        assert result.transaction_hash == "0xdead"
        assert "reverted" in result.error.lower()

    @pytest.mark.asyncio
    async def test_no_private_key(self):
        """Missing private key returns failure immediately."""
        with patch.dict("os.environ", {}, clear=True):
            # Ensure WALLET_PRIVATE_KEY is not set
            import os

            os.environ.pop("WALLET_PRIVATE_KEY", None)

            from integrations.erc8004.direct_reputation import give_feedback_direct

            result = await give_feedback_direct(agent_id=999, value=80)

        assert result.success is False
        assert "private key" in result.error.lower()

    @pytest.mark.asyncio
    async def test_explicit_private_key(self):
        """Explicit private_key param overrides env var."""
        mock_receipt = {"status": 1, "from": "0xRelay..."}
        mock_tx_hash = MagicMock()
        mock_tx_hash.hex.return_value = "0xrelay_tx"

        mock_w3 = MagicMock()
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.get_transaction_count.return_value = 0
        mock_w3.eth.estimate_gas.return_value = 100000
        mock_w3.eth.send_raw_transaction.return_value = mock_tx_hash
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        mock_account = MagicMock()
        mock_account.address = "0xRelayWallet"
        mock_w3.eth.account.from_key.return_value = mock_account
        mock_w3.eth.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b"\x00"
        )

        mock_contract = MagicMock()
        mock_func = MagicMock()
        mock_func.build_transaction.return_value = {
            "from": mock_account.address,
            "chainId": 8453,
            "gas": 200000,
            "gasPrice": 1000000000,
            "nonce": 0,
        }
        mock_contract.functions.giveFeedback.return_value = mock_func
        mock_w3.eth.contract.return_value = mock_contract

        relay_key = "0x" + "cc" * 32

        with patch(
            "integrations.erc8004.direct_reputation._get_web3",
            return_value=mock_w3,
        ):
            from integrations.erc8004.direct_reputation import give_feedback_direct

            result = await give_feedback_direct(
                agent_id=2106,
                value=90,
                private_key=relay_key,
            )

        assert result.success is True
        # Verify the explicit key was used, not env var
        mock_w3.eth.account.from_key.assert_called_with(relay_key)

    @pytest.mark.asyncio
    async def test_rpc_error_handling(self):
        """RPC errors are caught and returned as FeedbackResult."""
        mock_w3 = MagicMock()
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.get_transaction_count.side_effect = Exception("connection refused")

        mock_account = MagicMock()
        mock_account.address = "0xTest"
        mock_w3.eth.account.from_key.return_value = mock_account

        mock_contract = MagicMock()
        mock_func = MagicMock()
        mock_func.build_transaction.return_value = {
            "from": mock_account.address,
            "chainId": 8453,
            "gas": 200000,
            "gasPrice": 1000000000,
            "nonce": 0,
        }
        mock_contract.functions.giveFeedback.return_value = mock_func
        mock_w3.eth.contract.return_value = mock_contract

        with (
            patch(
                "integrations.erc8004.direct_reputation._get_web3",
                return_value=mock_w3,
            ),
            patch.dict(
                "os.environ",
                {"WALLET_PRIVATE_KEY": "0x" + "ab" * 32},
            ),
        ):
            from integrations.erc8004.direct_reputation import give_feedback_direct

            result = await give_feedback_direct(agent_id=999, value=80)

        assert result.success is False
        assert "connection refused" in result.error

    @pytest.mark.asyncio
    async def test_gas_estimation_fallback(self):
        """When gas estimation fails, falls back to 200k default."""
        mock_receipt = {"status": 1, "from": "0xTest"}
        mock_tx_hash = MagicMock()
        mock_tx_hash.hex.return_value = "0xgas_fallback"

        mock_w3 = MagicMock()
        mock_w3.eth.gas_price = 1000000000
        mock_w3.eth.get_transaction_count.return_value = 0
        mock_w3.eth.estimate_gas.side_effect = Exception("estimation failed")
        mock_w3.eth.send_raw_transaction.return_value = mock_tx_hash
        mock_w3.eth.wait_for_transaction_receipt.return_value = mock_receipt

        mock_account = MagicMock()
        mock_account.address = "0xTestAddr"
        mock_w3.eth.account.from_key.return_value = mock_account
        mock_w3.eth.account.sign_transaction.return_value = MagicMock(
            raw_transaction=b"\x00"
        )

        mock_contract = MagicMock()
        mock_func = MagicMock()
        tx_dict = {
            "from": mock_account.address,
            "chainId": 8453,
            "gasPrice": 1000000000,
            "nonce": 0,
        }
        mock_func.build_transaction.return_value = tx_dict
        mock_contract.functions.giveFeedback.return_value = mock_func
        mock_w3.eth.contract.return_value = mock_contract

        with (
            patch(
                "integrations.erc8004.direct_reputation._get_web3",
                return_value=mock_w3,
            ),
            patch.dict(
                "os.environ",
                {"WALLET_PRIVATE_KEY": "0x" + "ab" * 32},
            ),
        ):
            from integrations.erc8004.direct_reputation import give_feedback_direct

            result = await give_feedback_direct(agent_id=999, value=80)

        assert result.success is True
        # Verify gas was set to 200k fallback
        assert tx_dict["gas"] == 200_000


# ============================================================================
# _normalize_feedback_hash() tests
# ============================================================================


class TestNormalizeFeedbackHash:
    """Tests for feedback hash normalization."""

    def test_none_returns_zero_bytes(self):
        from integrations.erc8004.direct_reputation import _normalize_feedback_hash

        result = _normalize_feedback_hash(None)
        assert result == b"\x00" * 32
        assert len(result) == 32

    def test_empty_string_returns_zero_bytes(self):
        from integrations.erc8004.direct_reputation import _normalize_feedback_hash

        result = _normalize_feedback_hash("")
        assert result == b"\x00" * 32

    def test_valid_hex_with_prefix(self):
        from integrations.erc8004.direct_reputation import _normalize_feedback_hash

        hex_hash = "0x" + "ff" * 32
        result = _normalize_feedback_hash(hex_hash)
        assert result == b"\xff" * 32
        assert len(result) == 32

    def test_valid_hex_without_prefix(self):
        from integrations.erc8004.direct_reputation import _normalize_feedback_hash

        hex_hash = "ab" * 32
        result = _normalize_feedback_hash(hex_hash)
        assert result == b"\xab" * 32

    def test_short_hash_is_padded(self):
        from integrations.erc8004.direct_reputation import _normalize_feedback_hash

        # Short hash gets right-padded with zeros
        result = _normalize_feedback_hash("0xabcd")
        assert len(result) == 32
        assert result[:2] == b"\xab\xcd"


# ============================================================================
# rate_worker() direct path tests
# ============================================================================


class TestRateWorkerDirectPath:
    """Tests that rate_worker() uses the direct on-chain path."""

    @pytest.mark.asyncio
    async def test_rate_worker_uses_direct_feedback(self):
        """rate_worker() should call give_feedback_direct, not Facilitator."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.transaction_hash = "0xdirect_worker"

        with (
            patch("integrations.erc8004.facilitator_client.get_facilitator_client"),
            patch(
                "integrations.erc8004.direct_reputation.give_feedback_direct",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_direct,
            patch(
                "integrations.erc8004.feedback_store.persist_and_hash_feedback",
                new_callable=AsyncMock,
                return_value=("https://cdn/feedback.json", "0x" + "aa" * 32),
            ),
        ):
            from integrations.erc8004.facilitator_client import rate_worker

            result = await rate_worker(
                task_id="test-task-1",
                score=90,
                worker_address="0xWorkerAddr1234567890",
                worker_agent_id=999,
            )

        assert result.success is True
        mock_direct.assert_called_once()
        call_kwargs = mock_direct.call_args
        assert call_kwargs.kwargs["agent_id"] == 999
        assert call_kwargs.kwargs["value"] == 90
        assert call_kwargs.kwargs["tag1"] == "worker_rating"

    @pytest.mark.asyncio
    async def test_rate_worker_no_agent_id_returns_error(self):
        """rate_worker() with no worker_agent_id and no DB/chain lookup fails."""
        with (
            patch("integrations.erc8004.facilitator_client.get_facilitator_client"),
            patch(
                "integrations.erc8004.feedback_store.persist_and_hash_feedback",
                new_callable=AsyncMock,
                return_value=("https://cdn/feedback.json", "0xhash"),
            ),
        ):
            from integrations.erc8004.facilitator_client import rate_worker

            result = await rate_worker(
                task_id="test-task-2",
                score=75,
                worker_address="",
            )

        assert result.success is False
        assert "no erc-8004 identity" in result.error.lower()


# ============================================================================
# rate_agent() path selection tests
# ============================================================================


class TestRateAgentPathSelection:
    """Tests that rate_agent() chooses the right path based on EM_REPUTATION_RELAY_KEY."""

    @pytest.mark.asyncio
    async def test_rate_agent_with_relay_key_uses_direct(self):
        """With EM_REPUTATION_RELAY_KEY set, rate_agent() uses direct path."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.transaction_hash = "0xrelay_agent"

        relay_key = "0x" + "dd" * 32

        with (
            patch.dict("os.environ", {"EM_REPUTATION_RELAY_KEY": relay_key}),
            patch("integrations.erc8004.facilitator_client.get_facilitator_client"),
            patch(
                "integrations.erc8004.direct_reputation.give_feedback_direct",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_direct,
            patch(
                "integrations.erc8004.feedback_store.persist_and_hash_feedback",
                new_callable=AsyncMock,
                return_value=("https://cdn/feedback.json", "0x" + "bb" * 32),
            ),
        ):
            from integrations.erc8004.facilitator_client import rate_agent

            result = await rate_agent(
                agent_id=2106,
                task_id="test-task-3",
                score=95,
            )

        assert result.success is True
        mock_direct.assert_called_once()
        call_kwargs = mock_direct.call_args
        assert call_kwargs.kwargs["agent_id"] == 2106
        assert call_kwargs.kwargs["private_key"] == relay_key
        assert call_kwargs.kwargs["tag1"] == "agent_rating"

    @pytest.mark.asyncio
    async def test_rate_agent_without_relay_key_uses_facilitator(self):
        """Without EM_REPUTATION_RELAY_KEY, rate_agent() falls back to Facilitator."""
        mock_feedback_result = MagicMock()
        mock_feedback_result.success = True
        mock_feedback_result.transaction_hash = "0xfacilitator_agent"

        mock_client_instance = AsyncMock()
        mock_client_instance.submit_feedback = AsyncMock(
            return_value=mock_feedback_result
        )

        with (
            patch.dict("os.environ", {}, clear=False),
            patch(
                "integrations.erc8004.facilitator_client.get_facilitator_client",
                return_value=mock_client_instance,
            ),
            patch(
                "integrations.erc8004.feedback_store.persist_and_hash_feedback",
                new_callable=AsyncMock,
                return_value=("https://cdn/feedback.json", "0x" + "cc" * 32),
            ),
        ):
            # Ensure relay key is NOT set
            import os

            os.environ.pop("EM_REPUTATION_RELAY_KEY", None)

            from integrations.erc8004.facilitator_client import rate_agent

            result = await rate_agent(
                agent_id=2106,
                task_id="test-task-4",
                score=88,
            )

        assert result.success is True
        # Facilitator client's submit_feedback should have been called
        mock_client_instance.submit_feedback.assert_called_once()


# ============================================================================
# ABI encoding tests
# ============================================================================


class TestABIEncoding:
    """Tests for ABI-related constants and encoding."""

    def test_reputation_registry_address(self):
        """Registry address should be the CREATE2 mainnet address."""
        from integrations.erc8004.direct_reputation import REPUTATION_REGISTRY_ADDRESS

        assert (
            REPUTATION_REGISTRY_ADDRESS == "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"
        )

    def test_give_feedback_abi_has_correct_inputs(self):
        """ABI should match the on-chain contract signature."""
        from integrations.erc8004.direct_reputation import GIVE_FEEDBACK_ABI

        abi = GIVE_FEEDBACK_ABI[0]
        assert abi["name"] == "giveFeedback"
        assert len(abi["inputs"]) == 8

        input_names = [i["name"] for i in abi["inputs"]]
        assert input_names == [
            "agentId",
            "value",
            "valueDecimals",
            "tag1",
            "tag2",
            "endpoint",
            "feedbackURI",
            "feedbackHash",
        ]

        input_types = [i["type"] for i in abi["inputs"]]
        assert input_types == [
            "uint256",
            "int128",
            "uint8",
            "string",
            "string",
            "string",
            "string",
            "bytes32",
        ]

    def test_give_feedback_abi_is_nonpayable(self):
        """giveFeedback should be nonpayable."""
        from integrations.erc8004.direct_reputation import GIVE_FEEDBACK_ABI

        assert GIVE_FEEDBACK_ABI[0]["stateMutability"] == "nonpayable"

    def test_give_feedback_abi_no_outputs(self):
        """giveFeedback returns nothing."""
        from integrations.erc8004.direct_reputation import GIVE_FEEDBACK_ABI

        assert GIVE_FEEDBACK_ABI[0]["outputs"] == []


# ============================================================================
# Feedback URI & S3 key extraction tests
# ============================================================================


class TestFeedbackURI:
    """Tests for feedbackURI construction and S3 key extraction."""

    def test_extract_s3_key_from_execution_market_url(self):
        """execution.market/feedback/... URLs should resolve to S3 keys."""
        from integrations.erc8004.feedback_store import _extract_s3_key

        uri = "https://execution.market/feedback/abc-123/worker_rating_1234.json"
        with patch(
            "integrations.erc8004.feedback_store.FEEDBACK_PUBLIC_URL",
            "https://execution.market",
        ):
            key = _extract_s3_key(uri)
        assert key == "feedback/abc-123/worker_rating_1234.json"

    def test_extract_s3_key_from_cloudfront_url(self):
        """Legacy CloudFront URLs should still resolve to S3 keys."""
        from integrations.erc8004.feedback_store import _extract_s3_key

        uri = "https://d3h6yzj24t9k8z.cloudfront.net/feedback/abc-123/agent_rating_5678.json"
        key = _extract_s3_key(uri)
        assert key == "feedback/abc-123/agent_rating_5678.json"

    def test_extract_s3_key_from_s3_url(self):
        """Direct S3 URLs should resolve to S3 keys."""
        from integrations.erc8004.feedback_store import _extract_s3_key

        uri = (
            "https://evidence.s3.amazonaws.com/feedback/abc-123/worker_rating_1234.json"
        )
        key = _extract_s3_key(uri)
        assert key == "feedback/abc-123/worker_rating_1234.json"

    def test_extract_s3_key_from_cdn_env_url(self):
        """CDN env var URL should resolve to S3 keys."""
        from integrations.erc8004.feedback_store import _extract_s3_key

        uri = (
            "https://storage.execution.market/feedback/abc-123/worker_rating_1234.json"
        )
        with patch(
            "integrations.erc8004.feedback_store.FEEDBACK_CDN_URL",
            "https://storage.execution.market",
        ):
            key = _extract_s3_key(uri)
        assert key == "feedback/abc-123/worker_rating_1234.json"

    def test_extract_s3_key_none_for_unknown_url(self):
        """Unknown URLs should return None."""
        from integrations.erc8004.feedback_store import _extract_s3_key

        key = _extract_s3_key("https://example.com/some/path")
        assert key is None

    def test_extract_s3_key_none_for_empty(self):
        """Empty or None URIs should return None."""
        from integrations.erc8004.feedback_store import _extract_s3_key

        assert _extract_s3_key("") is None
        assert _extract_s3_key(None) is None

    def test_feedback_public_url_default(self):
        """FEEDBACK_PUBLIC_URL should default to execution.market."""
        from integrations.erc8004 import feedback_store

        # The module-level default (without env var override)
        assert "execution.market" in feedback_store.FEEDBACK_PUBLIC_URL
