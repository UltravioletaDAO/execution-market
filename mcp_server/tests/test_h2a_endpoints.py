"""
P0 Critical Tests for H2A Endpoints

Tests settlement atomicity, status validation, and payment integrity
for the H2A (Human-to-Agent) approval flow.

Covers bugs: S-CRIT-01, S-CRIT-02 from AUDIT_H2A_BACKEND_2026-02-18.md
"""

import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Fixtures
# ============================================================================


def _make_jwt_auth(user_id="user-1", wallet="0xabc123"):
    """Create a JWTData fixture for testing."""
    from api.h2a import JWTData

    return JWTData(user_id=user_id, wallet_address=wallet)


def _mock_task_result(
    task_id="task-uuid-1234",
    status="submitted",
    user_id="user-1",
    bounty_usd=5.0,
):
    """Create a mock task query result."""
    mock_result = MagicMock()
    mock_result.data = {
        "id": task_id,
        "human_user_id": user_id,
        "human_wallet": "0xabc123",
        "publisher_type": "human",
        "bounty_usd": bounty_usd,
        "status": status,
    }
    return mock_result


def _mock_submission_result(
    sub_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    task_id="task-uuid-1234",
    executor_wallet="0xworker456",
):
    """Create a mock submission query result."""
    mock_result = MagicMock()
    mock_result.data = {
        "id": sub_id,
        "task_id": task_id,
        "executor": {
            "id": "executor-1",
            "wallet_address": executor_wallet,
            "display_name": "Agent007",
        },
    }
    return mock_result


def _make_approve_request(
    sub_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    verdict="accepted",
    worker_auth="0xworkerauth123456789012345678901234567890",
    fee_auth="0xfeeauth123456789012345678901234567890123",
):
    """Create an ApproveH2ASubmissionRequest."""
    from models import ApproveH2ASubmissionRequest

    return ApproveH2ASubmissionRequest(
        submission_id=sub_id,
        verdict=verdict,
        settlement_auth_worker=worker_auth,
        settlement_auth_fee=fee_auth,
    )


# ============================================================================
# P0 Critical Tests — H2A Approval
# ============================================================================


@pytest.mark.h2a
class TestH2AApprovalCritical:
    """P0 critical tests for H2A settlement atomicity and status validation."""

    @pytest.mark.asyncio
    async def test_approve_happy_path_settles_both_txs(self):
        """
        Happy path: both worker and fee settlements succeed.
        Task and submission should be updated to completed/accepted.
        """
        from api.h2a import approve_h2a_submission

        auth = _make_jwt_auth()
        request = _make_approve_request()

        mock_client = MagicMock()
        # First .eq call chain → task result
        task_chain = MagicMock()
        task_chain.single.return_value.execute.return_value = _mock_task_result(
            status="submitted"
        )

        # Second .eq call chain → submission result
        sub_chain = MagicMock()
        sub_chain.single.return_value.execute.return_value = _mock_submission_result()

        # Build chain: table("tasks").select(...).eq("id", ...) returns task_chain
        # table("submissions").select(...).eq("id", ...).eq("task_id", ...) returns sub_chain
        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "tasks":
                mock_table.select.return_value.eq.return_value = task_chain
                mock_table.update.return_value.eq.return_value.execute.return_value = (
                    MagicMock()
                )
            elif name == "submissions":
                mock_table.select.return_value.eq.return_value.eq.return_value = (
                    sub_chain
                )
                mock_table.update.return_value.eq.return_value.execute.return_value = (
                    MagicMock()
                )
            return mock_table

        mock_client.table.side_effect = table_side_effect

        # Mock SDK to return successful tx hashes
        mock_sdk = AsyncMock()
        mock_sdk.settle_payment.side_effect = [
            {"tx_hash": "0xworkertx123"},
            {"tx_hash": "0xfeetx456"},
        ]

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_platform_fee_percent",
                new_callable=AsyncMock,
                return_value=Decimal("0.13"),
            ):
                with patch("api.h2a.log_payment_event", new_callable=AsyncMock):
                    with patch(
                        "integrations.x402.sdk_client.get_sdk", return_value=mock_sdk
                    ):
                        with patch("integrations.x402.sdk_client.SDK_AVAILABLE", True):
                            result = await approve_h2a_submission(
                                task_id="task-uuid-1234",
                                request=request,
                                auth=auth,
                            )

        assert result.status == "accepted"
        assert result.worker_tx == "0xworkertx123"
        assert result.fee_tx == "0xfeetx456"

    @pytest.mark.asyncio
    async def test_approve_settlement_failure_is_atomic(self):
        """
        S-CRIT-01: If SDK settlement fails, must raise 502.
        Task and submission status must NOT be changed.
        """
        from api.h2a import approve_h2a_submission
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        request = _make_approve_request()

        mock_client = MagicMock()
        task_chain = MagicMock()
        task_chain.single.return_value.execute.return_value = _mock_task_result(
            status="submitted"
        )
        sub_chain = MagicMock()
        sub_chain.single.return_value.execute.return_value = _mock_submission_result()

        # Track update calls to verify they're NOT called
        update_tracker = MagicMock()

        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "tasks":
                mock_table.select.return_value.eq.return_value = task_chain
                mock_table.update.side_effect = lambda data: update_tracker(
                    "tasks", data
                )
            elif name == "submissions":
                mock_table.select.return_value.eq.return_value.eq.return_value = (
                    sub_chain
                )
                mock_table.update.side_effect = lambda data: update_tracker(
                    "submissions", data
                )
            return mock_table

        mock_client.table.side_effect = table_side_effect

        # Mock SDK to raise an exception
        mock_sdk = AsyncMock()
        mock_sdk.settle_payment.side_effect = Exception("Settlement RPC timeout")

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_platform_fee_percent",
                new_callable=AsyncMock,
                return_value=Decimal("0.13"),
            ):
                with patch("api.h2a.log_payment_event", new_callable=AsyncMock):
                    with patch(
                        "integrations.x402.sdk_client.get_sdk", return_value=mock_sdk
                    ):
                        with patch("integrations.x402.sdk_client.SDK_AVAILABLE", True):
                            with pytest.raises(HTTPException) as exc_info:
                                await approve_h2a_submission(
                                    task_id="task-uuid-1234",
                                    request=request,
                                    auth=auth,
                                )

        # Must be 502
        assert exc_info.value.status_code == 502
        assert "settlement failed" in exc_info.value.detail.lower()

        # Task/submission update should NOT have been called with completed/accepted
        for call_args in update_tracker.call_args_list:
            table_name, data = call_args[0]
            if table_name == "tasks":
                assert data.get("status") != "completed"
            if table_name == "submissions":
                assert data.get("agent_verdict") != "accepted"

    @pytest.mark.asyncio
    async def test_approve_rejects_already_completed_task(self):
        """
        S-CRIT-02: Cannot approve a task that is already completed.
        """
        from api.h2a import approve_h2a_submission
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        request = _make_approve_request()

        mock_client = MagicMock()
        task_chain = MagicMock()
        task_chain.single.return_value.execute.return_value = _mock_task_result(
            status="completed"
        )

        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "tasks":
                mock_table.select.return_value.eq.return_value = task_chain
            return mock_table

        mock_client.table.side_effect = table_side_effect

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await approve_h2a_submission(
                    task_id="task-uuid-1234",
                    request=request,
                    auth=auth,
                )

        assert exc_info.value.status_code == 400
        assert "completed" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_approve_rejects_cancelled_task(self):
        """
        S-CRIT-02: Cannot approve a task that has been cancelled.
        """
        from api.h2a import approve_h2a_submission
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        request = _make_approve_request()

        mock_client = MagicMock()
        task_chain = MagicMock()
        task_chain.single.return_value.execute.return_value = _mock_task_result(
            status="cancelled"
        )

        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "tasks":
                mock_table.select.return_value.eq.return_value = task_chain
            return mock_table

        mock_client.table.side_effect = table_side_effect

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await approve_h2a_submission(
                    task_id="task-uuid-1234",
                    request=request,
                    auth=auth,
                )

        assert exc_info.value.status_code == 400
        assert "cancelled" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_approve_rejects_expired_task(self):
        """
        S-CRIT-02: Cannot approve a task that has expired.
        """
        from api.h2a import approve_h2a_submission
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        request = _make_approve_request()

        mock_client = MagicMock()
        task_chain = MagicMock()
        task_chain.single.return_value.execute.return_value = _mock_task_result(
            status="expired"
        )

        def table_side_effect(name):
            mock_table = MagicMock()
            if name == "tasks":
                mock_table.select.return_value.eq.return_value = task_chain
            return mock_table

        mock_client.table.side_effect = table_side_effect

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await approve_h2a_submission(
                    task_id="task-uuid-1234",
                    request=request,
                    auth=auth,
                )

        assert exc_info.value.status_code == 400
        assert "expired" in exc_info.value.detail.lower()
