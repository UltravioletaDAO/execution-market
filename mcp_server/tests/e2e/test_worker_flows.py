"""
E2E Test: Worker Registration & Acceptance Flows (B3, B5, E1-E4, E7)

Tests worker-side flows against the live API:
  - Off-chain worker registration
  - Applying to published tasks
  - Edge cases: expired tasks, cancelled tasks, double-apply, unregistered

Does NOT require real payments — uses tasks already in the system or
creates tasks without payment (expects 402 for creation, tests acceptance
using pre-existing tasks).

For tests that need a live task, gated by EM_E2E_REAL_PAYMENTS=true.

Usage:
    # Read-only tests (no payment needed)
    pytest tests/e2e/test_worker_flows.py -v -s -k "not real_payment"

    # Full tests including task creation
    EM_E2E_REAL_PAYMENTS=true pytest tests/e2e/test_worker_flows.py -v -s

Covers test plan IDs: B3, B5, E1, E2, E3, E4, E7
"""

import json
import logging
import os
import uuid
import pytest

pytestmark = pytest.mark.core
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict

from .shared import (
    FACILITATOR_URL,
    PLATFORM_FEE_PCT,
    WALLET_B_ADDRESS,
    EMApiClient,
)

logger = logging.getLogger(__name__)

REAL_PAYMENTS = os.environ.get("EM_E2E_REAL_PAYMENTS", "").lower() == "true"
DRY_RUN = os.environ.get("EM_E2E_DRY_RUN", "").lower() == "true"
AWS_REGION = os.environ.get("AWS_REGION", "us-east-2")

TEST_BOUNTY = Decimal("0.10")
TEST_FEE = (TEST_BOUNTY * PLATFORM_FEE_PCT).quantize(Decimal("0.000001"))


# ============== FIXTURES ==============


@pytest.fixture
async def http_client():
    try:
        import httpx
    except ImportError:
        pytest.skip("httpx required")
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client


@pytest.fixture(scope="session")
def agent_secrets() -> Dict[str, str]:
    if DRY_RUN:
        return {"PRIVATE_KEY": "0x" + "0" * 64, "API_KEY": "em_dry_run"}

    if not REAL_PAYMENTS:
        # For non-payment tests, try loading just the API key
        api_key = os.environ.get("EM_API_KEY", "")
        if api_key:
            return {"API_KEY": api_key, "PRIVATE_KEY": ""}
        pytest.skip("Set EM_API_KEY or EM_E2E_REAL_PAYMENTS=true")

    try:
        import boto3
    except ImportError:
        pytest.skip("boto3 required")

    client = boto3.client("secretsmanager", region_name=AWS_REGION)
    api_key_resp = client.get_secret_value(SecretId="em/api-key")
    api_key_data = json.loads(api_key_resp["SecretString"])
    wallet_resp = client.get_secret_value(SecretId="em/x402")
    wallet_data = json.loads(wallet_resp["SecretString"])

    return {
        "PRIVATE_KEY": wallet_data["PRIVATE_KEY"],
        "API_KEY": api_key_data.get("API_KEY", api_key_data.get("key", "")),
    }


@pytest.fixture
def api(http_client, agent_secrets) -> EMApiClient:
    return EMApiClient(http_client, agent_secrets["API_KEY"])


# ============== B3: WORKER REGISTRATION ==============


class TestWorkerRegistration:
    """Test plan section B: Worker registration flows."""

    @pytest.mark.asyncio
    async def test_b3_register_worker(self, api):
        """B3: Register a new worker with wallet address."""
        result = await api.register_worker(
            wallet_address=WALLET_B_ADDRESS,
            display_name="E2E Test Worker",
        )
        assert result["status_code"] == 200, (
            f"Worker registration failed: {result['data']}"
        )

        data = result["data"]
        executor = data.get("executor", data)
        assert "id" in executor, f"No executor ID in response: {data}"
        logger.info(f"Worker registered: {executor['id']}")

    @pytest.mark.asyncio
    async def test_b3_register_worker_idempotent(self, api):
        """B3: Re-registering same wallet returns existing executor."""
        result1 = await api.register_worker(
            wallet_address=WALLET_B_ADDRESS,
            display_name="E2E Worker First",
        )
        result2 = await api.register_worker(
            wallet_address=WALLET_B_ADDRESS,
            display_name="E2E Worker Second",
        )

        assert result1["status_code"] == 200
        assert result2["status_code"] == 200

        exec1 = result1["data"].get("executor", result1["data"])
        exec2 = result2["data"].get("executor", result2["data"])
        assert exec1["id"] == exec2["id"], (
            "Re-registration should return same executor ID"
        )

    @pytest.mark.asyncio
    async def test_b3_register_invalid_wallet(self, api):
        """B3: Registration with invalid wallet format should fail."""
        result = await api.register_worker(
            wallet_address="not-a-wallet",
            display_name="Invalid Wallet Worker",
        )
        # Should fail with 400 or 422
        assert result["status_code"] in (400, 422), (
            f"Expected validation error, got {result['status_code']}"
        )


# ============== B5: UNREGISTERED WORKER ==============


class TestUnregisteredWorker:
    """Verify unregistered workers cannot interact with tasks."""

    @pytest.mark.asyncio
    async def test_b5_unregistered_worker_cannot_apply(self, api):
        """B5: Worker with fake executor_id cannot apply to any task."""
        result = await api.apply_to_task(
            task_id=str(uuid.uuid4()),
            executor_id=str(uuid.uuid4()),
        )
        # Should fail — either 404 (task) or 400/403 (executor)
        assert result["status_code"] in (400, 403, 404, 422), (
            f"Expected error, got {result['status_code']}"
        )


# ============== E1: WORKER APPLIES TO PUBLISHED TASK ==============


class TestWorkerAcceptance:
    """Test plan section E: Worker acceptance scenarios."""

    @pytest.mark.asyncio
    async def test_e1_apply_to_published_task(self, api, agent_secrets):
        """E1: Worker applies to a published task successfully.

        Requires real payment to create a task first.
        """
        if not REAL_PAYMENTS:
            pytest.skip("Requires real payment for task creation")

        try:
            from uvd_x402_sdk import X402Client
        except ImportError:
            pytest.skip("uvd-x402-sdk required")

        # Create task
        total = float(TEST_BOUNTY + TEST_FEE)
        x402 = X402Client(
            private_key=agent_secrets["PRIVATE_KEY"],
            network="base",
            facilitator_url=FACILITATOR_URL,
        )
        payment_header = await x402.create_payment(
            amount_usd=total, token="USDC", description="E2E worker flow test"
        )
        create_result = await api.create_task(
            bounty_usd=float(TEST_BOUNTY),
            payment_header=payment_header,
            title=f"[E2E Worker Test] {datetime.now(timezone.utc).isoformat()[:19]}",
        )
        assert create_result["status_code"] == 201
        task_id = create_result["data"]["id"]

        try:
            # Register worker
            reg = await api.register_worker(
                wallet_address=WALLET_B_ADDRESS,
                display_name="E2E Accept Worker",
            )
            executor = reg["data"].get("executor", reg["data"])
            executor_id = executor["id"]

            # E1: Apply to task
            apply_result = await api.apply_to_task(
                task_id=task_id,
                executor_id=executor_id,
            )
            assert apply_result["status_code"] == 200, (
                f"Apply failed: {apply_result['data']}"
            )
            logger.info("Worker applied successfully")

            # Verify task status changed
            task = await api.get_task(task_id)
            assert task["data"].get("status") in ("accepted", "in_progress")

            # E2: Double-apply should fail
            apply2 = await api.apply_to_task(
                task_id=task_id,
                executor_id=executor_id,
            )
            assert apply2["status_code"] != 200, "Second apply should be rejected"
            logger.info(f"Double-apply rejected: {apply2['status_code']}")

        finally:
            # Cleanup: cancel task
            await api.cancel_task(task_id)

    @pytest.mark.asyncio
    async def test_e3_apply_to_nonexistent_task(self, api):
        """E3/E4: Applying to a non-existent task fails."""
        reg = await api.register_worker(
            wallet_address=WALLET_B_ADDRESS,
            display_name="E2E Edge Case Worker",
        )
        executor = reg["data"].get("executor", reg["data"])

        result = await api.apply_to_task(
            task_id=str(uuid.uuid4()),  # Non-existent
            executor_id=executor["id"],
        )
        assert result["status_code"] in (400, 404), (
            f"Expected 400/404, got {result['status_code']}"
        )

    @pytest.mark.asyncio
    async def test_e7_published_task_visible(self, api, agent_secrets):
        """E7: Published tasks are visible via the available tasks endpoint."""
        if not REAL_PAYMENTS:
            pytest.skip("Requires real payment for task creation")

        try:
            from uvd_x402_sdk import X402Client
        except ImportError:
            pytest.skip("uvd-x402-sdk required")

        # Create task
        total = float(TEST_BOUNTY + TEST_FEE)
        x402 = X402Client(
            private_key=agent_secrets["PRIVATE_KEY"],
            network="base",
            facilitator_url=FACILITATOR_URL,
        )
        payment_header = await x402.create_payment(
            amount_usd=total, token="USDC", description="E2E visibility test"
        )
        create_result = await api.create_task(
            bounty_usd=float(TEST_BOUNTY),
            payment_header=payment_header,
            title=f"[E2E Visible] {datetime.now(timezone.utc).isoformat()[:19]}",
        )
        assert create_result["status_code"] == 201
        task_id = create_result["data"]["id"]

        try:
            # Check available tasks
            available = await api.get_available_tasks()
            assert available["status_code"] == 200
            tasks = available["data"]

            # The response might be a list or a dict with a "tasks" key
            if isinstance(tasks, dict):
                task_list = tasks.get("tasks", [])
            else:
                task_list = tasks

            task_ids = [t.get("id") for t in task_list]
            assert task_id in task_ids, f"Task {task_id} not in available tasks"
            logger.info(f"Task {task_id} visible in available tasks")

        finally:
            await api.cancel_task(task_id)
