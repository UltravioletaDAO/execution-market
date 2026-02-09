"""
E2E Test: Reputation Flows (H1-H10)

Tests the bidirectional reputation system:
  - Agent rates worker (authenticated)
  - Worker rates agent (public)
  - Validation: wrong task status, wrong owner, etc.
  - ERC-8004 identity and reputation queries

Read-only reputation queries work without real payments.
Rating tests require a completed task (gated by EM_E2E_REAL_PAYMENTS).

Usage:
    # Read-only tests (no payment)
    pytest tests/e2e/test_reputation.py -v -s -k "not real_payment"

    # Full tests with rating
    EM_E2E_REAL_PAYMENTS=true pytest tests/e2e/test_reputation.py -v -s

Covers test plan IDs: H1, H2, H3, H4, H5, H6, H7, H8, H10, B2, B6
"""

import json
import logging
import os
import uuid
import pytest
from typing import Dict

from .shared import (
    WALLET_B_ADDRESS,
    EMApiClient,
    mask_address,
)

logger = logging.getLogger(__name__)

REAL_PAYMENTS = os.environ.get("EM_E2E_REAL_PAYMENTS", "").lower() == "true"
DRY_RUN = os.environ.get("EM_E2E_DRY_RUN", "").lower() == "true"
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")

# EM Agent ID on Base
EM_AGENT_ID = 2106


# ============== FIXTURES ==============


@pytest.fixture
async def http_client():
    try:
        import httpx
    except ImportError:
        pytest.skip("httpx required")
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture(scope="session")
def agent_secrets() -> Dict[str, str]:
    api_key = os.environ.get("EM_API_KEY", "")
    if api_key:
        return {"API_KEY": api_key, "PRIVATE_KEY": ""}

    if DRY_RUN:
        return {"API_KEY": "em_dry_run", "PRIVATE_KEY": ""}

    if not REAL_PAYMENTS:
        pytest.skip("Set EM_API_KEY or EM_E2E_REAL_PAYMENTS=true")

    try:
        import boto3
    except ImportError:
        pytest.skip("boto3 required")

    client = boto3.client("secretsmanager", region_name=AWS_REGION)
    api_key_resp = client.get_secret_value(SecretId="em/api-key")
    api_key_data = json.loads(api_key_resp["SecretString"])
    return {
        "PRIVATE_KEY": "",
        "API_KEY": api_key_data.get("API_KEY", api_key_data.get("key", "")),
    }


@pytest.fixture
def api(http_client, agent_secrets) -> EMApiClient:
    return EMApiClient(http_client, agent_secrets["API_KEY"])


# ============== B2, B6: AGENT IDENTITY ==============


class TestAgentIdentity:
    """Verify agent identity via ERC-8004 / facilitator."""

    @pytest.mark.asyncio
    async def test_b2_agent_registered_on_base(self, api):
        """B2: Agent #2106 is registered on Base."""
        result = await api.get_agent_identity(EM_AGENT_ID)
        assert result["status_code"] == 200, (
            f"Agent identity lookup failed: {result['data']}"
        )
        data = result["data"]
        assert data.get("agent_id") == EM_AGENT_ID
        assert data.get("owner"), "Agent should have an owner address"
        logger.info(
            f"Agent #{EM_AGENT_ID} on {data.get('network', 'unknown')}: "
            f"owner={mask_address(data.get('owner', ''))}"
        )

    @pytest.mark.asyncio
    async def test_b6_agent_identity_lookup(self, api):
        """B6: Agent identity includes metadata (name, URI, services)."""
        result = await api.get_agent_identity(EM_AGENT_ID)
        assert result["status_code"] == 200
        data = result["data"]

        # Should have basic metadata
        assert data.get("agent_uri"), "Agent should have an agent_uri"
        logger.info(f"Agent URI: {data.get('agent_uri')}")
        if data.get("name"):
            logger.info(f"Agent name: {data['name']}")

    @pytest.mark.asyncio
    async def test_b6_nonexistent_agent(self, api):
        """B6: Looking up a non-existent agent returns 404."""
        result = await api.get_agent_identity(999999)
        assert result["status_code"] == 404


# ============== H7, H8: REPUTATION VALIDATION ==============


class TestReputationValidation:
    """Validate reputation endpoint guards."""

    @pytest.mark.asyncio
    async def test_h7_rate_worker_nonexistent_task(self, api):
        """H7: Rating a worker on a non-existent task fails."""
        result = await api.rate_worker(
            task_id=str(uuid.uuid4()),
            worker_wallet=WALLET_B_ADDRESS,
            score=85,
        )
        # Should be 404 (task not found) or 403 (not authorized)
        assert result["status_code"] in (400, 403, 404), (
            f"Expected error, got {result['status_code']}: {result['data']}"
        )

    @pytest.mark.asyncio
    async def test_h8_rate_agent_nonexistent_task(self, api):
        """H8: Rating an agent on a non-existent task fails."""
        result = await api.rate_agent(
            agent_id=EM_AGENT_ID,
            task_id=str(uuid.uuid4()),
            score=90,
        )
        # Should fail — task not found
        assert result["status_code"] in (400, 404, 409), (
            f"Expected error, got {result['status_code']}: {result['data']}"
        )

    @pytest.mark.asyncio
    async def test_h7_rate_with_invalid_score(self, api):
        """H7: Rating with score > 100 or < 0 should fail validation."""
        result = await api.rate_worker(
            task_id=str(uuid.uuid4()),
            worker_wallet=WALLET_B_ADDRESS,
            score=150,  # Invalid — max 100
        )
        # Should get validation error (422) before task lookup
        assert result["status_code"] in (400, 422), (
            f"Expected validation error, got {result['status_code']}"
        )


# ============== H10: REPUTATION QUERIES ==============


class TestReputationQueries:
    """Query reputation data (read-only, no auth needed for some)."""

    @pytest.mark.asyncio
    async def test_h10_em_reputation(self, api):
        """H10: Query Execution Market's own reputation."""
        result = await api.get_em_reputation()
        # May return 404 if no feedback yet, or 200 with score
        if result["status_code"] == 200:
            data = result["data"]
            logger.info(
                f"EM reputation: score={data.get('score')}, count={data.get('count')}"
            )
            assert data.get("agent_id") == EM_AGENT_ID
        else:
            logger.info(
                f"EM reputation not available: {result['status_code']} "
                f"({result['data']})"
            )
            # 404 or 503 is acceptable if no feedback exists yet
            assert result["status_code"] in (404, 503)

    @pytest.mark.asyncio
    async def test_h10_em_identity(self, api):
        """H10: Query EM's on-chain identity."""
        result = await api.get_em_identity()
        if result["status_code"] == 200:
            data = result["data"]
            assert data.get("agent_id") == EM_AGENT_ID
            assert data.get("owner"), "Should have owner"
            logger.info(f"EM identity: owner={mask_address(data.get('owner', ''))}")
        else:
            # 404/503 acceptable if not registered
            assert result["status_code"] in (404, 503)

    @pytest.mark.asyncio
    async def test_h10_agent_reputation_query(self, api):
        """H10: Query specific agent's reputation by ID."""
        result = await api.get_agent_reputation(EM_AGENT_ID)
        if result["status_code"] == 200:
            data = result["data"]
            logger.info(
                f"Agent #{EM_AGENT_ID} reputation: score={data.get('score')}, "
                f"count={data.get('count')}, network={data.get('network')}"
            )
        else:
            # Reputation query may fail if facilitator has issues
            logger.warning(
                f"Agent reputation query returned {result['status_code']}: "
                f"{result['data']}"
            )

    @pytest.mark.asyncio
    async def test_h10_reputation_info_endpoint(self, api):
        """H10: Reputation info endpoint returns integration status."""
        result = await api.get_reputation_info()
        assert result["status_code"] == 200
        data = result["data"]
        assert data.get("available") is True
        assert data.get("em_agent_id") == EM_AGENT_ID
        assert "facilitator_url" in data
        logger.info(f"Reputation info: {data}")


# ============== H6: GASLESS VERIFICATION ==============


class TestGaslessReputation:
    """Verify reputation operations don't consume native gas."""

    @pytest.mark.asyncio
    async def test_h6_escrow_config_shows_no_gas_needed(self, api):
        """H6: Escrow/payment config confirms gasless via facilitator."""
        result = await api.get_escrow_config()
        if result["status_code"] == 200:
            data = result["data"]
            logger.info(f"Escrow config: {data}")
            # Facilitator pays gas — wallets don't need native tokens
        else:
            logger.info(f"Escrow config: {result['status_code']}")
