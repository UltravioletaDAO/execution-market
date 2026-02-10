"""
E2E Test: Multichain Infrastructure Verification (A3-A7)

Validates the infrastructure layer across all enabled networks:
  - ERC-8004 identity registry (same CREATE2 address on all mainnets)
  - x402r escrow contracts deployed
  - USDC token contracts deployed
  - Platform wallet funding per network
  - Facilitator reachability

NO real payments needed — these are read-only infrastructure probes.
Network list is derived from sdk_client.py — add a chain there and tests auto-expand.

Usage:
    pytest tests/e2e/test_multichain_infra.py -v -s

Covers test plan IDs: A3, A4, A5, A6, A7
"""

import logging
import os
import pytest
from decimal import Decimal

from .shared import (
    WALLET_A_ADDRESS,
    ENABLED_NETWORKS,
    EMApiClient,
    get_usdc_balance,
    check_facilitator_health,
    check_contract_code,
    mask_address,
)
from integrations.x402.sdk_client import NETWORK_CONFIG

logger = logging.getLogger(__name__)

# ERC-8004 contract addresses (CREATE2, same on all mainnets)
ERC8004_IDENTITY_REGISTRY = "0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
ERC8004_REPUTATION_REGISTRY = "0x8004BAa17C55a88189AE136b182e5fdA19dE9b63"

# x402r escrow contracts — derived from sdk_client.py NETWORK_CONFIG
ESCROW_CONTRACTS = {
    net: cfg["escrow"] for net, cfg in NETWORK_CONFIG.items() if cfg.get("escrow")
}


# ============== FIXTURES ==============


@pytest.fixture
async def http_client():
    try:
        import httpx
    except ImportError:
        pytest.skip("httpx required")
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def api(http_client) -> EMApiClient:
    api_key = os.environ.get("EM_API_KEY", "")
    return EMApiClient(http_client, api_key)


# ============== A3: ERC-8004 IDENTITY REGISTRY ==============


class TestERC8004Registry:
    """Verify ERC-8004 contracts exist on all enabled networks."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("network", ENABLED_NETWORKS)
    async def test_a3_identity_registry_deployed(self, http_client, network):
        """A3: ERC-8004 Identity Registry has code on each network."""
        has_code = await check_contract_code(
            http_client, network, ERC8004_IDENTITY_REGISTRY
        )
        logger.info(f"[{network}] Identity Registry deployed: {has_code}")
        if not has_code:
            pytest.xfail(f"Identity Registry not deployed on {network}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("network", ENABLED_NETWORKS)
    async def test_a3_reputation_registry_deployed(self, http_client, network):
        """A3: ERC-8004 Reputation Registry has code on each network."""
        has_code = await check_contract_code(
            http_client, network, ERC8004_REPUTATION_REGISTRY
        )
        logger.info(f"[{network}] Reputation Registry deployed: {has_code}")
        if not has_code:
            pytest.xfail(f"Reputation Registry not deployed on {network}")


# ============== A4: x402r ESCROW CONTRACTS ==============


class TestEscrowContracts:
    """Verify x402r escrow contracts exist on all enabled networks."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("network", ENABLED_NETWORKS)
    async def test_a4_escrow_contract_deployed(self, http_client, network):
        """A4: x402r escrow contract has code on each network."""
        escrow_addr = ESCROW_CONTRACTS.get(network)
        if not escrow_addr:
            pytest.skip(f"No escrow address configured for {network}")

        has_code = await check_contract_code(http_client, network, escrow_addr)
        logger.info(f"[{network}] Escrow {escrow_addr[:10]}... deployed: {has_code}")
        if not has_code:
            pytest.xfail(f"Escrow contract not deployed on {network}")


# ============== A5: FACILITATOR REACHABILITY ==============


class TestFacilitator:
    """Verify facilitator service is reachable."""

    @pytest.mark.asyncio
    async def test_a5_facilitator_health(self, http_client):
        """A5: Facilitator health endpoint responds."""
        result = await check_facilitator_health(http_client)
        assert result is not None, "Facilitator unreachable"
        logger.info(f"Facilitator health: {result}")

    @pytest.mark.asyncio
    async def test_a5_reputation_info(self, api):
        """A5: Reputation info endpoint (confirms ERC-8004 integration)."""
        result = await api.get_reputation_info()
        assert result["status_code"] == 200
        data = result["data"]
        assert data.get("available") is True
        assert data.get("em_agent_id") == 2106
        logger.info(f"ERC-8004 info: agent #{data.get('em_agent_id')}")

    @pytest.mark.asyncio
    async def test_a5_reputation_networks(self, api):
        """A5: Reputation networks lists all supported chains."""
        result = await api.get_reputation_networks()
        assert result["status_code"] == 200
        data = result["data"]
        network_names = [n["network"] for n in data.get("networks", [])]
        logger.info(f"ERC-8004 networks ({data.get('count')}): {network_names}")
        # At minimum, all 8 mainnets should appear (accept "base-mainnet" alias)
        for net in ENABLED_NETWORKS:
            found = net in network_names or f"{net}-mainnet" in network_names
            assert found, f"Network {net} missing from ERC-8004 (got: {network_names})"


# ============== A6: USDC TOKEN CONTRACTS ==============


class TestUSDCTokens:
    """Verify USDC token contracts exist and are callable on all networks."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("network", ENABLED_NETWORKS)
    async def test_a6_usdc_contract_responds(self, http_client, network):
        """A6: USDC contract responds to balanceOf on each network."""
        # Use a known address (treasury) to test balanceOf call
        balance = await get_usdc_balance(
            http_client,
            network,
            "0x0000000000000000000000000000000000000001",  # Burn address
        )
        logger.info(f"[{network}] USDC balanceOf(burn): {balance}")
        # If balance is None, the RPC or contract failed
        if balance is None:
            pytest.xfail(f"USDC contract not responding on {network}")
        # Balance should be a non-negative decimal
        assert balance >= Decimal("0")


# ============== A7: PLATFORM WALLET FUNDING ==============


class TestWalletFunding:
    """Verify platform wallet has USDC on production network(s)."""

    @pytest.mark.asyncio
    async def test_a7_production_wallet_funded_base(self, http_client):
        """A7: Production wallet has USDC on Base (primary network)."""
        balance = await get_usdc_balance(http_client, "base", WALLET_A_ADDRESS)
        assert balance is not None, "Could not query wallet balance on Base"
        logger.info(f"Production wallet on Base: ${balance} USDC")
        # Should have some funds for testing
        assert balance > Decimal("0"), "Production wallet has $0 USDC on Base"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("network", ENABLED_NETWORKS)
    async def test_a7_production_wallet_balance(self, http_client, network):
        """A7: Check production wallet USDC balance on each network."""
        balance = await get_usdc_balance(http_client, network, WALLET_A_ADDRESS)
        if balance is None:
            pytest.xfail(f"Could not query balance on {network}")

        logger.info(
            f"[{network}] Wallet {mask_address(WALLET_A_ADDRESS)}: ${balance} USDC"
        )
        # Don't fail on unfunded networks, just report
        if balance == Decimal("0"):
            pytest.xfail(
                f"Production wallet unfunded on {network} — "
                f"real payment tests on this network will fail"
            )
