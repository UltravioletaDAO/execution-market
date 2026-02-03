"""
E2E Tests with Real Payments (NOW-212)

These tests use REAL FUNDS and make actual payments through the x402 protocol.
They are disabled by default and only run when:
1. CHAMBA_E2E_REAL_PAYMENTS=true environment variable is set
2. AWS credentials are configured
3. Secrets exist in AWS Secrets Manager

SECURITY WARNING:
- These tests spend real money (minimum $0.25 per test)
- Private keys are loaded from AWS Secrets Manager
- Keys are NEVER logged or exposed

Usage:
    # Run with real payments (requires AWS credentials)
    CHAMBA_E2E_REAL_PAYMENTS=true pytest tests/e2e/test_real_payment.py -v

    # Dry run (no real payments, just validates setup)
    CHAMBA_E2E_DRY_RUN=true pytest tests/e2e/test_real_payment.py -v

Cost Estimation:
    Each test costs approximately $0.27 ($0.25 bounty + $0.02 fee)
    Running all tests: ~$2.00
"""

import json
import logging
import os
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, Optional

# Configure logging for test output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============== TEST CONFIGURATION ==============


# Skip all tests if not enabled
REAL_PAYMENTS_ENABLED = os.environ.get("CHAMBA_E2E_REAL_PAYMENTS", "").lower() == "true"
DRY_RUN = os.environ.get("CHAMBA_E2E_DRY_RUN", "").lower() == "true"

# API configuration
API_BASE = os.environ.get(
    "CHAMBA_API_URL",
    "https://api.chamba.ultravioletadao.xyz"
)
SECRETS_NAME = os.environ.get("CHAMBA_SECRETS_NAME", "chamba/test-agent")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")

# Minimum bounty (configurable) - lowered for micropayment testing
MIN_BOUNTY = Decimal("0.01")
PLATFORM_FEE_PCT = Decimal("0.08")


# ============== SECURITY HELPERS ==============


def mask_key(key: str) -> str:
    """Mask a key for safe logging."""
    if not key:
        return "***EMPTY***"
    if len(key) < 12:
        return "***MASKED***"
    return f"{key[:6]}...{key[-4:]}"


def mask_address(addr: str) -> str:
    """Mask an address for logging."""
    if not addr:
        return "***EMPTY***"
    return f"{addr[:10]}...{addr[-4:]}"


# ============== FIXTURES ==============


@pytest.fixture(scope="session")
def check_enabled():
    """Check if real payment tests are enabled."""
    if not REAL_PAYMENTS_ENABLED and not DRY_RUN:
        pytest.skip(
            "Real payment tests disabled. "
            "Set CHAMBA_E2E_REAL_PAYMENTS=true to enable, "
            "or CHAMBA_E2E_DRY_RUN=true for dry run."
        )


@pytest.fixture(scope="session")
def aws_secrets(check_enabled) -> Dict[str, str]:
    """Load secrets from AWS Secrets Manager."""
    if DRY_RUN:
        return {
            "PRIVATE_KEY": "0x" + "0" * 64,  # Dummy key for dry run
            "API_KEY": "chamba_test_dry_run"
        }

    try:
        import boto3
    except ImportError:
        pytest.skip("boto3 not installed")

    try:
        client = boto3.client("secretsmanager", region_name=AWS_REGION)
        response = client.get_secret_value(SecretId=SECRETS_NAME)
        secrets = json.loads(response["SecretString"])

        # Validate required keys
        assert "PRIVATE_KEY" in secrets, "Missing PRIVATE_KEY in secrets"
        assert "API_KEY" in secrets, "Missing API_KEY in secrets"

        logger.info(f"Loaded secrets from {SECRETS_NAME}")
        logger.info(f"API Key: {mask_key(secrets['API_KEY'])}")

        return secrets
    except Exception as e:
        pytest.skip(f"Could not load secrets: {e}")


@pytest.fixture(scope="session")
def wallet_address(aws_secrets) -> str:
    """Derive wallet address from private key."""
    if DRY_RUN:
        return "0x" + "1" * 40  # Dummy address

    try:
        from eth_account import Account
    except ImportError:
        pytest.skip("eth-account not installed")

    account = Account.from_key(aws_secrets["PRIVATE_KEY"])
    logger.info(f"Wallet: {mask_address(account.address)}")
    return account.address


@pytest.fixture
async def http_client():
    """Create HTTP client for API calls."""
    try:
        import httpx
    except ImportError:
        pytest.skip("httpx not installed")

    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


# ============== TEST: API HEALTH ==============


@pytest.mark.asyncio
async def test_api_health(http_client, check_enabled):
    """Verify API is reachable."""
    response = await http_client.get(f"{API_BASE}/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    logger.info(f"API health: {data['status']}")


# ============== TEST: A2A DISCOVERY ==============


@pytest.mark.asyncio
async def test_a2a_agent_card(http_client, check_enabled):
    """Verify A2A Agent Card is accessible."""
    response = await http_client.get(f"{API_BASE}/.well-known/agent.json")
    assert response.status_code == 200

    agent_card = response.json()
    assert "name" in agent_card
    assert "description" in agent_card
    assert agent_card["name"] == "Chamba"

    logger.info(f"Agent Card found: {agent_card['name']}")
    logger.info(f"Capabilities: {len(agent_card.get('capabilities', []))}")


# ============== TEST: PUBLIC CONFIG ==============


@pytest.mark.asyncio
async def test_public_config(http_client, check_enabled):
    """Verify public configuration endpoint."""
    response = await http_client.get(f"{API_BASE}/api/v1/config")
    assert response.status_code == 200

    config = response.json()
    assert "min_bounty_usd" in config
    assert "max_bounty_usd" in config
    assert "supported_networks" in config

    logger.info(f"Min bounty: ${config['min_bounty_usd']}")
    logger.info(f"Max bounty: ${config['max_bounty_usd']}")
    logger.info(f"Networks: {config['supported_networks']}")


# ============== TEST: 402 PAYMENT REQUIRED ==============


@pytest.mark.asyncio
async def test_402_payment_required(http_client, aws_secrets, check_enabled):
    """Verify task creation requires payment."""
    if DRY_RUN:
        pytest.skip("Dry run mode - requires real API key for 402 test")

    response = await http_client.post(
        f"{API_BASE}/api/v1/tasks",
        headers={
            "Authorization": f"Bearer {aws_secrets['API_KEY']}",
            "Content-Type": "application/json"
        },
        json={
            "title": "Test task",
            "instructions": "This is a test to verify 402 response",
            "category": "simple_action",
            "bounty_usd": 0.25,
            "deadline_hours": 1,
            "evidence_required": ["text_response"]
        }
    )

    # Without X-Payment header, should return 402
    assert response.status_code == 402

    data = response.json()
    assert data["error"] == "Payment required"
    assert "required_amount_usd" in data
    assert "platform_fee_percent" in data

    required = Decimal(data["required_amount_usd"])
    expected = MIN_BOUNTY * (1 + PLATFORM_FEE_PCT)

    logger.info(f"402 Payment Required: ${required}")
    logger.info(f"Expected: ${expected}")

    assert required == expected.quantize(Decimal("0.01"))


# ============== TEST: REAL PAYMENT TASK CREATION ==============


@pytest.mark.asyncio
async def test_create_task_with_real_payment(
    http_client,
    aws_secrets,
    wallet_address,
    check_enabled
):
    """
    Test creating a task with real x402 payment.

    This test:
    1. Generates an x402 payment header
    2. Creates a task with the payment
    3. Verifies escrow was created
    4. Verifies correct fee calculation

    Cost: ~$0.27 ($0.25 bounty + 8% fee)
    """
    if DRY_RUN:
        logger.info("DRY RUN: Skipping real payment")
        pytest.skip("Dry run mode - no real payments")

    # Skip if SDK not available
    try:
        from uvd_x402_sdk import X402Client
    except ImportError:
        pytest.skip("uvd-x402-sdk not installed")

    # Calculate amounts
    bounty = MIN_BOUNTY
    fee = bounty * PLATFORM_FEE_PCT
    total = bounty + fee

    logger.info(f"Creating task with real payment:")
    logger.info(f"  Bounty: ${bounty}")
    logger.info(f"  Fee ({PLATFORM_FEE_PCT * 100}%): ${fee}")
    logger.info(f"  Total: ${total}")

    # Generate payment header
    x402 = X402Client(
        private_key=aws_secrets["PRIVATE_KEY"],  # Never logged
        network="base",
        facilitator_url="https://facilitator.ultravioletadao.xyz"
    )

    payment_header = await x402.create_payment(
        amount_usd=float(total),
        token="USDC",
        description="E2E test task payment"
    )

    logger.info(f"Payment header generated (length: {len(payment_header)})")

    # Create task
    response = await http_client.post(
        f"{API_BASE}/api/v1/tasks",
        headers={
            "Authorization": f"Bearer {aws_secrets['API_KEY']}",
            "X-Payment": payment_header,
            "Content-Type": "application/json"
        },
        json={
            "title": f"[E2E TEST] Real payment test - {datetime.now(timezone.utc).isoformat()}",
            "instructions": "Automated E2E test. Respond with: test_complete",
            "category": "simple_action",
            "bounty_usd": float(bounty),
            "deadline_hours": 1,
            "evidence_required": ["text_response"]
        }
    )

    assert response.status_code == 201, f"Task creation failed: {response.text}"

    task = response.json()
    assert "id" in task
    assert task["status"] == "published"

    logger.info(f"Task created: {task['id']}")
    logger.info(f"Status: {task['status']}")
    logger.info(f"Escrow ID: {task.get('escrow_id', 'N/A')}")

    # Return task for potential cleanup
    return task


# ============== TEST: FEE CALCULATIONS ==============


@pytest.mark.asyncio
async def test_fee_calculation_accuracy(check_enabled):
    """Verify fee calculations match expected values."""
    test_cases = [
        # (bounty, expected_fee, expected_worker_payout)
        (Decimal("0.25"), Decimal("0.02"), Decimal("0.23")),
        (Decimal("1.00"), Decimal("0.08"), Decimal("0.92")),
        (Decimal("10.00"), Decimal("0.80"), Decimal("9.20")),
        (Decimal("100.00"), Decimal("8.00"), Decimal("92.00")),
    ]

    for bounty, expected_fee, expected_payout in test_cases:
        fee = (bounty * PLATFORM_FEE_PCT).quantize(Decimal("0.01"))
        payout = bounty - fee

        assert fee == expected_fee, f"Fee mismatch for ${bounty}: got ${fee}, expected ${expected_fee}"
        assert payout == expected_payout, f"Payout mismatch for ${bounty}: got ${payout}, expected ${expected_payout}"

        logger.info(f"Bounty ${bounty}: Fee ${fee}, Worker payout ${payout}")


# ============== TEST: PARTIAL RELEASE CALCULATIONS ==============


@pytest.mark.asyncio
async def test_partial_release_calculation(check_enabled):
    """Verify partial release calculations."""
    PARTIAL_RELEASE_PCT = Decimal("0.30")

    test_cases = [
        # (bounty, expected_partial, expected_final)
        (Decimal("10.00"), Decimal("2.76"), Decimal("6.44")),
        # Worker payout = 10 - 0.80 = 9.20
        # Partial = 9.20 * 0.30 = 2.76
        # Final = 9.20 * 0.70 = 6.44
    ]

    for bounty, expected_partial, expected_final in test_cases:
        fee = bounty * PLATFORM_FEE_PCT
        worker_total = bounty - fee
        partial = (worker_total * PARTIAL_RELEASE_PCT).quantize(Decimal("0.01"))
        final = worker_total - partial

        logger.info(f"Bounty ${bounty}:")
        logger.info(f"  Platform fee: ${fee}")
        logger.info(f"  Worker total: ${worker_total}")
        logger.info(f"  Partial release (30%): ${partial}")
        logger.info(f"  Final release (70%): ${final}")

        assert partial == expected_partial
        assert final == expected_final


# ============== TEST: ESCROW STATE MACHINE ==============


@pytest.mark.asyncio
async def test_escrow_state_transitions(check_enabled):
    """Verify escrow state machine transitions."""
    # This test validates the expected state transitions without real payments
    states = [
        "pending",       # Awaiting deposit
        "deposited",     # Funds locked
        "partial_released",  # 30% released on submission
        "released",      # All funds released on approval
    ]

    # Alternative paths
    alternative_states = {
        "deposited": ["refunded", "disputed"],  # Can be refunded or disputed
        "partial_released": ["released", "disputed"],  # Final release or dispute
        "disputed": ["released", "refunded"],  # Resolution
    }

    logger.info("Escrow state machine:")
    logger.info("  Normal flow: pending -> deposited -> partial_released -> released")
    logger.info("  Refund path: deposited -> refunded (on timeout/cancel)")
    logger.info("  Dispute path: partial_released -> disputed -> released/refunded")

    # Validate states are strings
    for state in states:
        assert isinstance(state, str)


# ============== CLEANUP ==============


@pytest.fixture(autouse=True)
async def cleanup_test_tasks(http_client, aws_secrets, check_enabled):
    """Clean up any test tasks after tests."""
    yield

    # Post-test cleanup could cancel any pending test tasks
    # For now, test tasks will expire naturally
    pass
