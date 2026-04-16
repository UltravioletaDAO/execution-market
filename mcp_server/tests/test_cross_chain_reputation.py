"""
Tests for cross-chain reputation aggregation.

Tests the get_cross_chain_reputation() function which:
1. Checks identity on multiple EVM chains in parallel
2. Gets reputation scores for each identity found
3. Computes per-chain averages
4. Returns average-of-averages as the final score
"""

import asyncio
import importlib
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Optional
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.erc8004

# ---------------------------------------------------------------------------
# Module stubbing
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

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

_LEAF_STUBS = {
    "integrations.erc8004.register": {"ERC8004Registry": None},
    "integrations.erc8004.reputation": {"ReputationManager": None},
    "integrations.erc8004.identity": {
        "verify_agent_identity": None,
        "check_worker_identity": None,
        "register_worker_gasless": None,
        "update_executor_identity": None,
    },
    "integrations.erc8004.feedback_store": {
        "persist_and_hash_feedback": None,
        "FEEDBACK_PUBLIC_URL": "https://cdn.test.com",
    },
    "integrations.x402.sdk_client": {
        "NETWORK_CONFIG": {
            "base": {"chain_id": 8453, "rpc_url": "https://mainnet.base.org"},
            "polygon": {"chain_id": 137, "rpc_url": "https://polygon-rpc.com"},
            "arbitrum": {"chain_id": 42161, "rpc_url": "https://arb1.arbitrum.io/rpc"},
        },
        "get_rpc_url": lambda net: f"https://rpc.{net}.test",
    },
}
for _mod_name, _attrs in _LEAF_STUBS.items():
    if _mod_name not in sys.modules:
        _stub = ModuleType(_mod_name)
        for _k, _v in _attrs.items():
            setattr(_stub, _k, _v)
        sys.modules[_mod_name] = _stub

# Load the REAL facilitator_client module.  Other test files may have
# installed minimal stubs that lack the CrossChainReputationResult
# dataclass we need.  To import the real module we must ensure all its
# transitive dependencies are either real or have sufficient attributes.
_fc_mod = sys.modules.get("integrations.erc8004.facilitator_client")
if _fc_mod is not None and not hasattr(_fc_mod, "CrossChainReputationResult"):
    # Stub from another test file -- remove it and all transitive stubs
    # that would prevent the real module from loading.
    for _stale in [
        "integrations.erc8004.facilitator_client",
    ]:
        sys.modules.pop(_stale, None)
    _fc_mod = None

    # Ensure parent packages have __path__ for import_module to work
    for _pname, _ppath in _PACKAGES.items():
        _ppkg = sys.modules.get(_pname)
        if _ppkg is not None and not hasattr(_ppkg, "__path__"):
            _ppkg.__path__ = [_ppath]

    # Ensure feedback_store stub has FEEDBACK_PUBLIC_URL (used by the real
    # facilitator_client at import time)
    _fs = sys.modules.get("integrations.erc8004.feedback_store")
    if _fs is not None and not hasattr(_fs, "FEEDBACK_PUBLIC_URL"):
        _fs.FEEDBACK_PUBLIC_URL = "https://cdn.test.com"

if _fc_mod is None:
    _fc_mod = importlib.import_module("integrations.erc8004.facilitator_client")
    importlib.reload(_fc_mod)
    sys.modules["integrations.erc8004.facilitator_client"] = _fc_mod

# Re-import from the (possibly already loaded) module to ensure we get the right objects
CrossChainReputationResult = _fc_mod.CrossChainReputationResult
ChainReputationDetail = _fc_mod.ChainReputationDetail
invalidate_cross_chain_cache = _fc_mod.invalidate_cross_chain_cache
_cross_chain_cache = _fc_mod._cross_chain_cache
_CROSS_CHAIN_EVM_NETWORKS = _fc_mod._CROSS_CHAIN_EVM_NETWORKS
ReputationSummary = _fc_mod.ReputationSummary


async def get_cross_chain_reputation(wallet_address, networks=None):
    """Wrapper that always calls the live module's function."""
    fc = sys.modules.get("integrations.erc8004.facilitator_client", _fc_mod)
    return await fc.get_cross_chain_reputation(wallet_address, networks=networks)


# Helpers for mocking identity results
class _MockIdentityStatus:
    def __init__(self, val):
        self.value = val


@dataclass
class _MockIdentityResult:
    status: _MockIdentityStatus
    agent_id: Optional[int] = None
    wallet_address: str = ""
    network: str = "base"
    chain_id: int = 8453
    registry_address: Optional[str] = None
    error: Optional[str] = None


def _registered(agent_id: int, network: str = "base"):
    return _MockIdentityResult(
        status=_MockIdentityStatus("registered"),
        agent_id=agent_id,
        wallet_address="0xtest",
        network=network,
    )


def _not_registered(network: str = "base"):
    return _MockIdentityResult(
        status=_MockIdentityStatus("not_registered"),
        network=network,
    )


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cross-chain cache before each test."""
    # Access the cache from ALL possible module instances to handle module reloading
    for mod_name in list(sys.modules):
        if "facilitator_client" in mod_name:
            mod = sys.modules[mod_name]
            if hasattr(mod, "_cross_chain_cache"):
                mod._cross_chain_cache.clear()
    _cross_chain_cache.clear()
    yield
    for mod_name in list(sys.modules):
        if "facilitator_client" in mod_name:
            mod = sys.modules[mod_name]
            if hasattr(mod, "_cross_chain_cache"):
                mod._cross_chain_cache.clear()
    _cross_chain_cache.clear()


# ============================================================================
# Cross-Chain Aggregation Math Tests
# ============================================================================


class TestCrossChainReputationAggregation:
    """Test the average-of-averages math."""

    @pytest.mark.asyncio
    async def test_single_chain_single_identity(self):
        """One chain, one identity, one score → final = that score."""
        mock_identity = AsyncMock(
            side_effect=lambda wallet, network="base": (
                _registered(2106, network)
                if network == "base"
                else _not_registered(network)
            )
        )
        mock_rep = ReputationSummary(
            agent_id=2106, count=1, summary_value=85, network="base"
        )

        with patch(
            "integrations.erc8004.identity.check_worker_identity",
            mock_identity,
        ):
            with patch.object(
                _fc_mod,
                "get_reputation",
                new_callable=AsyncMock,
                return_value=mock_rep,
            ):
                result = await get_cross_chain_reputation(
                    "0x1234567890123456789012345678901234567890",
                    networks=["base", "polygon"],
                )

        assert result.final_score == 85.0
        assert result.chain_count == 1
        assert result.total_reviews == 1
        assert result.chains_with_identity == 1
        assert "base" in result.per_chain
        assert result.per_chain["base"].average == 85.0

    @pytest.mark.asyncio
    async def test_two_chains_equal_weight(self):
        """Two chains -> final = average of per-chain averages."""

        async def mock_check_identity(wallet, network="base"):
            if network in ("base", "polygon"):
                return _registered(2106, network)
            return _not_registered(network)

        async def mock_get_rep(agent_id, network="base", **kwargs):
            # Base: score 90, Polygon: score 70
            if network == "base":
                return ReputationSummary(
                    agent_id=2106, count=1, summary_value=90, network="base"
                )
            elif network == "polygon":
                return ReputationSummary(
                    agent_id=2106, count=1, summary_value=70, network="polygon"
                )
            return None

        with patch(
            "integrations.erc8004.identity.check_worker_identity",
            side_effect=mock_check_identity,
        ):
            with patch.object(
                _fc_mod,
                "get_reputation",
                side_effect=mock_get_rep,
            ):
                result = await get_cross_chain_reputation(
                    "0x1234567890123456789012345678901234567890",
                    networks=["base", "polygon"],
                )

        # (90 + 70) / 2 = 80.0
        assert result.final_score == 80.0
        assert result.chain_count == 2
        assert result.total_reviews == 2

    @pytest.mark.asyncio
    async def test_chain_with_zero_reviews_excluded(self):
        """Chain with identity but 0 reviews is excluded from average."""

        async def mock_check_identity(wallet, network="base"):
            if network in ("base", "polygon"):
                return _registered(2106, network)
            return _not_registered(network)

        async def mock_get_rep(agent_id, network="base", **kwargs):
            if network == "base":
                return ReputationSummary(
                    agent_id=2106, count=3, summary_value=90, network="base"
                )
            elif network == "polygon":
                # 0 reviews = count is 0
                return ReputationSummary(
                    agent_id=2106, count=0, summary_value=0, network="polygon"
                )
            return None

        with patch(
            "integrations.erc8004.identity.check_worker_identity",
            side_effect=mock_check_identity,
        ):
            with patch.object(
                _fc_mod,
                "get_reputation",
                side_effect=mock_get_rep,
            ):
                result = await get_cross_chain_reputation(
                    "0x1234567890123456789012345678901234567890",
                    networks=["base", "polygon"],
                )

        # Only base contributes, polygon has identity but 0 reviews → skipped
        assert result.final_score == 90.0
        assert result.chain_count == 1
        assert result.chains_with_identity == 2
        assert result.chains_skipped == 1

    @pytest.mark.asyncio
    async def test_no_identity_anywhere(self):
        """No identity on any chain → final score 0, chain_count 0."""

        async def mock_check_identity(wallet, network="base"):
            return _not_registered(network)

        with patch(
            "integrations.erc8004.identity.check_worker_identity",
            side_effect=mock_check_identity,
        ):
            result = await get_cross_chain_reputation(
                "0x1234567890123456789012345678901234567890",
                networks=["base", "polygon"],
            )

        assert result.final_score == 0.0
        assert result.chain_count == 0
        assert result.chains_with_identity == 0

    @pytest.mark.asyncio
    async def test_rpc_timeout_skips_chain(self):
        """If identity check times out on one chain, skip it gracefully."""

        async def mock_check_identity(wallet, network="base"):
            if network == "base":
                return _registered(2106, network)
            elif network == "polygon":
                await asyncio.sleep(10)  # Will timeout at 5s
                return _registered(2106, network)
            return _not_registered(network)

        mock_rep = ReputationSummary(
            agent_id=2106, count=1, summary_value=80, network="base"
        )

        with patch(
            "integrations.erc8004.identity.check_worker_identity",
            side_effect=mock_check_identity,
        ):
            with patch.object(
                _fc_mod,
                "get_reputation",
                new_callable=AsyncMock,
                return_value=mock_rep,
            ):
                result = await get_cross_chain_reputation(
                    "0x1234567890123456789012345678901234567890",
                    networks=["base", "polygon"],
                )

        # Polygon timed out, only base contributes
        assert result.final_score == 80.0
        assert result.chain_count == 1

    @pytest.mark.asyncio
    async def test_cache_works(self):
        """Second call returns cached result."""

        async def mock_check_identity(wallet, network="base"):
            if network == "base":
                return _registered(2106, network)
            return _not_registered(network)

        mock_rep = ReputationSummary(
            agent_id=2106, count=1, summary_value=75, network="base"
        )

        with patch(
            "integrations.erc8004.identity.check_worker_identity",
            side_effect=mock_check_identity,
        ):
            with patch.object(
                _fc_mod,
                "get_reputation",
                new_callable=AsyncMock,
                return_value=mock_rep,
            ):
                wallet = "0x1234567890123456789012345678901234567890"
                result1 = await get_cross_chain_reputation(wallet, networks=["base"])
                result2 = await get_cross_chain_reputation(wallet, networks=["base"])

        assert result1.cached is False
        assert result2.cached is True
        assert result1.final_score == result2.final_score

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """invalidate_cross_chain_cache clears the entry."""
        wallet = "0x1234567890123456789012345678901234567890"

        async def mock_check_identity(w, network="base"):
            return _not_registered(network)

        fc = sys.modules.get("integrations.erc8004.facilitator_client", _fc_mod)

        with patch(
            "integrations.erc8004.identity.check_worker_identity",
            side_effect=mock_check_identity,
        ):
            await get_cross_chain_reputation(wallet, networks=["base"])
            assert wallet.lower() in fc._cross_chain_cache

            fc.invalidate_cross_chain_cache(wallet)
            assert wallet.lower() not in fc._cross_chain_cache


class TestCrossChainReputationResult:
    """Test the result dataclass serialization."""

    def test_to_dict(self):
        result = CrossChainReputationResult(
            wallet_address="0xabc",
            final_score=82.333333,
            chain_count=2,
            total_reviews=5,
            per_chain={
                "base": ChainReputationDetail(
                    network="base",
                    agent_ids=[2106],
                    scores=[90.0, 80.0],
                    average=85.0,
                    review_count=2,
                ),
                "polygon": ChainReputationDetail(
                    network="polygon",
                    agent_ids=[2106, 500],
                    scores=[75.0, 80.0, 85.0],
                    average=80.0,
                    review_count=3,
                ),
            },
            chains_with_identity=3,
            chains_skipped=1,
            cached=False,
        )
        d = result.to_dict()
        assert d["final_score"] == 82.33
        assert d["chain_count"] == 2
        assert d["total_reviews"] == 5
        assert d["chains_with_identity"] == 3
        assert d["chains_skipped"] == 1
        assert "base" in d["per_chain"]
        assert d["per_chain"]["base"]["average"] == 85.0
        assert d["per_chain"]["polygon"]["review_count"] == 3

    def test_all_9_evm_networks(self):
        """Verify the constant has exactly 9 EVM chains (no Solana, no BSC)."""
        assert len(_CROSS_CHAIN_EVM_NETWORKS) == 9
        assert "solana" not in _CROSS_CHAIN_EVM_NETWORKS
        assert "bsc" not in _CROSS_CHAIN_EVM_NETWORKS
        assert "base" in _CROSS_CHAIN_EVM_NETWORKS
        assert "skale" in _CROSS_CHAIN_EVM_NETWORKS
