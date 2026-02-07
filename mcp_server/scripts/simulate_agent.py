#!/usr/bin/env python3
"""
Agent Simulation Script - Real Funds Test (NOW-215)

This script simulates an AI agent using Execution Market with real payments.
It demonstrates the full lifecycle:
1. Discover Execution Market via A2A Agent Card
2. Create a task with real x402 payment
3. Monitor task status
4. Approve submission when worker completes
5. Verify payment release

Usage:
    python simulate_agent.py --bounty 0.25 --network base
    python simulate_agent.py --bounty 0.25 --network base --wait-for-submission
    python simulate_agent.py --dry-run  # No real payments

Environment:
    AWS credentials must be configured (aws configure)
    Or set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

SECURITY: This script reads private keys from AWS Secrets Manager.
         Keys are NEVER logged or printed.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ============== SECURITY UTILITIES ==============


def mask_key(key: str) -> str:
    """
    Mask a private key for safe logging.

    NEVER log full private keys. This function ensures
    only the first 6 and last 4 characters are visible.
    """
    if not key:
        return "***EMPTY***"
    if len(key) < 12:
        return "***MASKED***"
    return f"{key[:6]}...{key[-4:]}"


def mask_address(addr: str) -> str:
    """
    Mask an Ethereum address for logging.

    Shows first 8 and last 4 characters for identification
    without exposing the full address.
    """
    if not addr:
        return "***EMPTY***"
    return f"{addr[:10]}...{addr[-4:]}"


def mask_api_key(key: str) -> str:
    """Mask an API key for logging."""
    if not key:
        return "***EMPTY***"
    if len(key) < 20:
        return f"{key[:8]}...***"
    return f"{key[:16]}...{key[-4:]}"


# ============== CONFIGURATION ==============


class Config:
    """Configuration with environment variable support."""

    # API endpoint (production by default)
    API_BASE = os.environ.get("EM_API_URL", "https://api.execution.market")

    # AWS Secrets Manager
    SECRETS_NAME = os.environ.get("EM_SECRETS_NAME", "em/test-agent")
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")

    # x402 facilitator
    FACILITATOR_URL = os.environ.get(
        "X402_FACILITATOR_URL", "https://facilitator.ultravioletadao.xyz"
    )

    # Supported networks
    SUPPORTED_NETWORKS = ["base", "ethereum", "polygon", "optimism", "arbitrum"]
    SUPPORTED_TOKENS = ["USDC", "USDT", "DAI"]


# ============== AWS SECRETS ==============


def get_secrets() -> Dict[str, str]:
    """
    Load secrets from AWS Secrets Manager.

    Returns:
        Dictionary with PRIVATE_KEY and API_KEY

    SECURITY: Values are validated but NEVER logged.
    """
    try:
        import boto3
    except ImportError:
        logger.error("boto3 not installed. Run: pip install boto3")
        sys.exit(1)

    logger.info(f"[SETUP] Loading secrets from {Config.SECRETS_NAME}...")

    try:
        client = boto3.client("secretsmanager", region_name=Config.AWS_REGION)
        response = client.get_secret_value(SecretId=Config.SECRETS_NAME)
        secrets = json.loads(response["SecretString"])
    except Exception as e:
        logger.error(f"[SETUP] Failed to load secrets: {e}")
        logger.error("[SETUP] Ensure AWS credentials are configured and secret exists")
        sys.exit(1)

    # Validate required keys exist (but NEVER log them)
    required = ["PRIVATE_KEY", "API_KEY"]
    for key in required:
        if key not in secrets:
            logger.error(f"[SETUP] Missing required secret: {key}")
            sys.exit(1)

    # Log only metadata
    logger.info(f"[SETUP] Loaded secrets: {list(secrets.keys())}")
    logger.info(f"[SETUP] API Key: {mask_api_key(secrets['API_KEY'])}")

    return secrets


# ============== WALLET UTILITIES ==============


def get_wallet_address(private_key: str) -> str:
    """
    Derive wallet address from private key.

    SECURITY: The private key is only used to derive the address,
    never logged or stored beyond this function.
    """
    try:
        from eth_account import Account
    except ImportError:
        logger.error("eth-account not installed. Run: pip install eth-account")
        sys.exit(1)

    try:
        account = Account.from_key(private_key)
        return account.address
    except Exception as e:
        logger.error(f"[SETUP] Invalid private key: {e}")
        sys.exit(1)


# ============== A2A DISCOVERY ==============


async def discover_em(client) -> Dict[str, Any]:
    """
    Discover Execution Market via A2A Agent Card.

    This simulates how an AI agent would discover Execution Market's
    capabilities before using the service.
    """
    logger.info(f"\n[DISCOVERY] Fetching Agent Card from {Config.API_BASE}...")

    try:
        response = await client.get(f"{Config.API_BASE}/.well-known/agent.json")
        response.raise_for_status()

        agent_card = response.json()
        logger.info(f"[DISCOVERY] Found: {agent_card['name']}")

        description = agent_card.get("description", "")
        if len(description) > 100:
            description = description[:100] + "..."
        logger.info(f"[DISCOVERY] Description: {description}")

        capabilities = agent_card.get("capabilities", [])
        logger.info(f"[DISCOVERY] Capabilities: {len(capabilities)}")

        for cap in capabilities[:3]:
            logger.info(f"  - {cap.get('name', 'unnamed')}")

        return agent_card
    except Exception as e:
        logger.error(f"[DISCOVERY] Failed: {e}")
        raise


# ============== PAYMENT GENERATION ==============


async def generate_payment_header(
    private_key: str, amount_usd: Decimal, network: str = "base", token: str = "USDC"
) -> str:
    """
    Generate x402 payment header.

    SECURITY: The private key is used to sign the payment
    but is NEVER logged or exposed.

    Args:
        private_key: Wallet private key (MASKED in all logs)
        amount_usd: Payment amount in USD
        network: Blockchain network
        token: Payment token

    Returns:
        x402 payment header string
    """
    logger.info("[PAYMENT] Generating x402 payment...")
    logger.info(f"[PAYMENT] Amount: ${amount_usd}")
    logger.info(f"[PAYMENT] Network: {network}, Token: {token}")

    try:
        from uvd_x402_sdk import X402Client
    except ImportError:
        logger.warning("[PAYMENT] uvd-x402-sdk not installed, using mock payment")
        return "mock_payment_header_for_testing"

    try:
        x402 = X402Client(
            private_key=private_key,  # Never logged
            network=network,
            facilitator_url=Config.FACILITATOR_URL,
        )

        payment_header = await x402.create_payment(
            amount_usd=float(amount_usd),
            token=token,
            description=f"Execution Market task payment: ${amount_usd}",
        )

        logger.info(f"[PAYMENT] Header generated (length: {len(payment_header)})")
        return payment_header
    except Exception as e:
        logger.error(f"[PAYMENT] Failed to generate payment: {e}")
        raise


# ============== TASK OPERATIONS ==============


async def create_task(
    client,
    api_key: str,
    bounty_usd: Decimal,
    payment_header: str,
    deadline_hours: int = 1,
) -> Dict[str, Any]:
    """
    Create a task with real payment.

    Args:
        client: HTTP client
        api_key: API key (masked in logs)
        bounty_usd: Bounty amount
        payment_header: x402 payment header
        deadline_hours: Task deadline

    Returns:
        Created task data
    """
    logger.info(f"\n[CREATE] Creating task with bounty ${bounty_usd}...")

    # Calculate fee (8%)
    fee_pct = Decimal("0.08")
    total_usd = bounty_usd * (1 + fee_pct)
    logger.info(f"[CREATE] Total with fee: ${total_usd} ({fee_pct * 100}% fee)")

    task_data = {
        "title": f"[TEST] Automated verification - {datetime.now(timezone.utc).isoformat()}",
        "instructions": """
This is an automated test task created by the agent simulation script.

To complete this task, please respond with the text: "test_verification_complete"

This confirms the task system is working correctly.

Note: This is a real task with real payment. The bounty will be released
upon successful verification of the response.
        """.strip(),
        "category": "simple_action",
        "bounty_usd": float(bounty_usd),
        "deadline_hours": deadline_hours,
        "evidence_required": ["text_response"],
    }

    try:
        response = await client.post(
            f"{Config.API_BASE}/api/v1/tasks",
            headers={
                "Authorization": f"Bearer {api_key}",
                "X-Payment": payment_header,
                "Content-Type": "application/json",
            },
            json=task_data,
        )

        if response.status_code == 402:
            error_data = response.json()
            logger.error("[CREATE] Payment Required (402)")
            logger.error(f"[CREATE] Error: {error_data.get('message', 'Unknown')}")
            logger.error(
                f"[CREATE] Required: ${error_data.get('required_amount_usd', '?')}"
            )
            raise ValueError("Payment not accepted - check balance and amount")

        response.raise_for_status()
        task = response.json()

        logger.info("[CREATE] Task created successfully!")
        logger.info(f"[CREATE] Task ID: {task['id']}")
        logger.info(f"[CREATE] Status: {task.get('status', 'unknown')}")
        logger.info(f"[CREATE] Escrow ID: {task.get('escrow_id', 'N/A')}")

        return task
    except Exception as e:
        logger.error(f"[CREATE] Failed: {e}")
        raise


async def monitor_task(
    client,
    api_key: str,
    task_id: str,
    timeout_minutes: int = 65,
    poll_interval: int = 10,
) -> Optional[Dict[str, Any]]:
    """
    Monitor task until submission or timeout.

    Args:
        client: HTTP client
        api_key: API key
        task_id: Task to monitor
        timeout_minutes: Maximum wait time
        poll_interval: Seconds between checks

    Returns:
        Final task state or None on timeout
    """
    logger.info(f"\n[MONITOR] Watching task {task_id}...")
    logger.info(f"[MONITOR] Timeout: {timeout_minutes} minutes")

    start_time = datetime.now(timezone.utc)

    while True:
        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds() / 60

        if elapsed > timeout_minutes:
            logger.warning(f"[MONITOR] Timeout after {timeout_minutes} minutes")
            return None

        try:
            response = await client.get(
                f"{Config.API_BASE}/api/v1/tasks/{task_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            task = response.json()

            status = task.get("status", "unknown")
            logger.info(f"[MONITOR] {elapsed:.1f}m - Status: {status}")

            if status == "submitted":
                logger.info("[MONITOR] Submission received!")
                return task

            if status in ["completed", "expired", "cancelled"]:
                logger.info(f"[MONITOR] Task ended with status: {status}")
                return task

            await asyncio.sleep(poll_interval)
        except Exception as e:
            logger.error(f"[MONITOR] Error checking status: {e}")
            await asyncio.sleep(poll_interval)


async def get_submissions(
    client, api_key: str, task_id: str
) -> Optional[Dict[str, Any]]:
    """Get submissions for a task."""
    try:
        response = await client.get(
            f"{Config.API_BASE}/api/v1/tasks/{task_id}/submissions",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"[SUBMISSIONS] Error: {e}")
        return None


async def approve_submission(
    client,
    api_key: str,
    task_id: str,
    submission_id: str,
    notes: str = "Automated test approval",
) -> Optional[Dict[str, Any]]:
    """
    Approve a submission and release payment.

    Args:
        client: HTTP client
        api_key: API key
        task_id: Task ID
        submission_id: Submission to approve
        notes: Approval notes

    Returns:
        Approval result with payment details
    """
    logger.info(f"\n[APPROVE] Approving submission {submission_id}...")

    try:
        response = await client.post(
            f"{Config.API_BASE}/api/v1/submissions/{submission_id}/approve",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"notes": notes},
        )
        response.raise_for_status()
        result = response.json()

        logger.info("[APPROVE] Approved successfully!")
        if "worker_payment" in result:
            logger.info(f"[APPROVE] Worker payment: ${result['worker_payment']}")
        if "platform_fee" in result:
            logger.info(f"[APPROVE] Platform fee: ${result['platform_fee']}")

        return result
    except Exception as e:
        logger.error(f"[APPROVE] Failed: {e}")
        return None


# ============== MAIN SIMULATION ==============


async def run_simulation(
    bounty: float, network: str, token: str, wait_for_submission: bool, dry_run: bool
) -> None:
    """
    Run the full agent simulation.

    Args:
        bounty: Bounty amount in USD
        network: Payment network
        token: Payment token
        wait_for_submission: If True, wait for worker submission
        dry_run: If True, skip real payments
    """
    print("=" * 60)
    print("EM AGENT SIMULATION - " + ("DRY RUN" if dry_run else "REAL FUNDS"))
    print("=" * 60)
    print(f"Bounty: ${bounty}")
    print(f"Network: {network}")
    print(f"Token: {token}")
    print(f"API: {Config.API_BASE}")
    print("=" * 60)

    # Load secrets
    secrets = get_secrets()
    private_key = secrets["PRIVATE_KEY"]
    api_key = secrets["API_KEY"]

    # Get wallet address (safe to show masked)
    wallet = get_wallet_address(private_key)
    logger.info(f"[SETUP] Wallet: {mask_address(wallet)}")

    try:
        import httpx
    except ImportError:
        logger.error("httpx not installed. Run: pip install httpx")
        sys.exit(1)

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Discovery
        try:
            await discover_em(client)
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return

        if dry_run:
            logger.info("\n[DRY RUN] Skipping real payment generation")
            payment_header = "dry_run_mock_payment"
        else:
            # 2. Generate payment
            bounty_decimal = Decimal(str(bounty))
            fee_pct = Decimal("0.08")
            total = bounty_decimal * (1 + fee_pct)

            try:
                payment_header = await generate_payment_header(
                    private_key=private_key,
                    amount_usd=total,
                    network=network,
                    token=token,
                )
            except Exception as e:
                logger.error(f"Payment generation failed: {e}")
                return

        # 3. Create task
        try:
            task = await create_task(
                client=client,
                api_key=api_key,
                bounty_usd=Decimal(str(bounty)),
                payment_header=payment_header,
                deadline_hours=1,
            )
            task_id = task["id"]
        except Exception as e:
            logger.error(f"Task creation failed: {e}")
            return

        # 4. Output task URL
        logger.info("\n[INFO] Task created successfully!")
        logger.info(f"[INFO] Task URL: {Config.API_BASE}/api/v1/tasks/{task_id}")

        if wait_for_submission:
            # 5. Monitor for submission
            task = await monitor_task(
                client=client, api_key=api_key, task_id=task_id, timeout_minutes=65
            )

            if task and task.get("status") == "submitted":
                # 6. Get submissions
                submissions_data = await get_submissions(client, api_key, task_id)

                if submissions_data and submissions_data.get("submissions"):
                    submission = submissions_data["submissions"][0]
                    submission_id = submission["id"]

                    # Log evidence (sanitized)
                    evidence = submission.get("evidence", {})
                    logger.info(
                        f"[EVIDENCE] Text response: {evidence.get('text_response', 'N/A')[:100]}"
                    )

                    # 7. Approve
                    await approve_submission(
                        client=client,
                        api_key=api_key,
                        task_id=task_id,
                        submission_id=submission_id,
                    )
        else:
            logger.info("\n[INFO] --wait-for-submission not set")
            logger.info("[INFO] Task will be monitored separately or expire")

    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)


def main():
    """Parse arguments and run simulation."""
    parser = argparse.ArgumentParser(
        description="Simulate an AI agent using Execution Market with real payments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Create a task with minimum bounty
    python simulate_agent.py --bounty 0.25 --network base

    # Create and wait for submission (will block until worker submits)
    python simulate_agent.py --bounty 0.25 --wait-for-submission

    # Dry run (no real payments)
    python simulate_agent.py --dry-run

Environment Variables:
    EM_API_URL          API endpoint (default: production)
    EM_SECRETS_NAME     AWS Secrets Manager secret name
    AWS_REGION              AWS region for Secrets Manager
    X402_FACILITATOR_URL    x402 facilitator URL

Security:
    Private keys are loaded from AWS Secrets Manager and NEVER logged.
    All sensitive data is masked in output.
        """,
    )

    parser.add_argument(
        "--bounty",
        type=float,
        default=0.25,
        help="Bounty amount in USD (default: 0.25, minimum)",
    )
    parser.add_argument(
        "--network",
        type=str,
        default="base",
        choices=Config.SUPPORTED_NETWORKS,
        help="Payment network (default: base)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default="USDC",
        choices=Config.SUPPORTED_TOKENS,
        help="Payment token (default: USDC)",
    )
    parser.add_argument(
        "--wait-for-submission",
        action="store_true",
        help="Wait for worker submission before exiting",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Run without real payments (test mode)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate bounty
    if args.bounty < 0.25:
        logger.error("Minimum bounty is $0.25")
        sys.exit(1)

    if args.bounty > 100 and not args.dry_run:
        logger.warning(f"Large bounty (${args.bounty}). Use --dry-run for testing.")
        response = input("Continue? [y/N] ")
        if response.lower() != "y":
            sys.exit(0)

    # Run simulation
    asyncio.run(
        run_simulation(
            bounty=args.bounty,
            network=args.network,
            token=args.token,
            wait_for_submission=args.wait_for_submission,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
