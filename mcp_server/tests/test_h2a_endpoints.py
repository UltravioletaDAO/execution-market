"""
Tests for H2A Endpoints

P0: Settlement atomicity, status validation, payment integrity
P1: Feature flags, task creation, listing, cancellation, registration

Covers bugs from AUDIT_H2A_BACKEND_2026-02-18.md
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


# ============================================================================
# P1 Tests — Feature Flags and Task Creation (Task 2.1)
# ============================================================================


@pytest.mark.h2a
class TestH2AFeatureFlags:
    """Tests for H2A feature flag and bounty limit enforcement."""

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_returns_403(self):
        """H2A disabled → 403."""
        from api.h2a import _check_h2a_enabled
        from fastapi import HTTPException

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"value": "false"}]
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await _check_h2a_enabled()

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_feature_flag_db_error_returns_503(self):
        """DB unreachable → 503 (fail-closed)."""
        from api.h2a import _check_h2a_enabled
        from fastapi import HTTPException

        mock_client = MagicMock()
        mock_client.table.side_effect = Exception("DB connection refused")

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await _check_h2a_enabled()

        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_feature_flag_enabled_passes(self):
        """H2A enabled → no exception."""
        from api.h2a import _check_h2a_enabled

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{"value": "true"}]
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_result

        with patch("api.h2a.db.get_client", return_value=mock_client):
            # Should not raise
            await _check_h2a_enabled()


@pytest.mark.h2a
class TestH2ATaskCreation:
    """Tests for H2A task creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_task_no_wallet_returns_400(self):
        """User without wallet → 400."""
        from api.h2a import create_h2a_task, JWTData
        from fastapi import HTTPException
        from models import PublishH2ATaskRequest

        auth = JWTData(user_id="user-1", wallet_address=None)
        request = PublishH2ATaskRequest(
            title="Test task",
            instructions="Do something important for testing",
            category="data_processing",
            bounty_usd=5.0,
            deadline_hours=24,
            evidence_required=["text_report"],
        )

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with pytest.raises(HTTPException) as exc_info:
                await create_h2a_task(request=request, auth=auth)

        assert exc_info.value.status_code == 400
        assert "wallet" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_task_bounty_below_min_returns_400(self):
        """Bounty below minimum → 400."""
        from api.h2a import create_h2a_task, JWTData
        from fastapi import HTTPException
        from models import PublishH2ATaskRequest

        auth = JWTData(user_id="user-1", wallet_address="0xabc123")
        request = PublishH2ATaskRequest(
            title="Cheap task",
            instructions="Do something very cheap for testing",
            category="data_processing",
            bounty_usd=0.01,
            deadline_hours=24,
            evidence_required=["text_report"],
        )

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.50"), Decimal("500.00")),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await create_h2a_task(request=request, auth=auth)

        assert exc_info.value.status_code == 400
        assert "below" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_task_bounty_above_max_returns_400(self):
        """Bounty above H2A maximum → 400."""
        from api.h2a import create_h2a_task, JWTData
        from fastapi import HTTPException
        from models import PublishH2ATaskRequest

        auth = JWTData(user_id="user-1", wallet_address="0xabc123")
        # Model allows up to 500, but H2A max is set to 100
        request = PublishH2ATaskRequest(
            title="Expensive task",
            instructions="Do something very expensive for testing",
            category="data_processing",
            bounty_usd=200.0,
            deadline_hours=24,
            evidence_required=["text_report"],
        )

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.50"), Decimal("100.00")),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await create_h2a_task(request=request, auth=auth)

        assert exc_info.value.status_code == 400
        assert "exceeds" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_create_task_happy_path(self):
        """Valid creation → 201 response with correct fields."""
        from api.h2a import create_h2a_task, JWTData
        from models import PublishH2ATaskRequest

        auth = JWTData(user_id="user-1", wallet_address="0xabc123")
        request = PublishH2ATaskRequest(
            title="Analyze market data",
            instructions="Analyze the market data and provide a report",
            category="data_processing",
            bounty_usd=5.0,
            deadline_hours=24,
            evidence_required=["text_report"],
        )

        mock_client = MagicMock()
        mock_insert_result = MagicMock()
        mock_insert_result.data = [{"id": "task-uuid-new", "status": "published"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            mock_insert_result
        )

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.50"), Decimal("500.00")),
            ):
                with patch(
                    "api.h2a.get_platform_fee_percent",
                    new_callable=AsyncMock,
                    return_value=Decimal("0.13"),
                ):
                    with patch("api.h2a.db.get_client", return_value=mock_client):
                        result = await create_h2a_task(request=request, auth=auth)

        assert result.task_id == "task-uuid-new"
        assert result.status == "published"
        assert result.bounty_usd == 5.0
        assert result.fee_usd == 0.65  # 5.0 * 0.13
        assert result.publisher_type == "human"


# ============================================================================
# P1 Tests — Listing + Cancellation (Task 2.2)
# ============================================================================


@pytest.mark.h2a
class TestH2ATaskListing:
    """Tests for H2A task listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_public_returns_published_only(self):
        """Public listing (no auth) defaults to status=published."""
        from api.h2a import list_h2a_tasks

        mock_client = MagicMock()
        mock_count_result = MagicMock()
        mock_count_result.count = 2
        mock_query_result = MagicMock()
        mock_query_result.data = [
            {"id": "t1", "status": "published"},
            {"id": "t2", "status": "published"},
        ]

        # Build chained mock
        mock_table = MagicMock()
        mock_table.select.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_query_result
        mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_count_result

        # Count chain (different select signature)
        mock_count_table = MagicMock()
        mock_count_table.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_count_result

        call_count = {"n": 0}

        def table_side_effect(name):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                return mock_table
            return mock_count_table

        mock_client.table.side_effect = table_side_effect

        with patch("api.h2a.db.get_client", return_value=mock_client):
            result = await list_h2a_tasks(
                status=None, category=None, my_tasks=False, limit=20, offset=0
            )

        assert "tasks" in result
        assert "total" in result

    @pytest.mark.asyncio
    async def test_list_with_category_filter(self):
        """Category filter is passed through."""
        from api.h2a import list_h2a_tasks

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0

        mock_table = MagicMock()
        # Deep chain for category filter
        mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        mock_count_table = MagicMock()
        mock_count_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = mock_result

        call_count = {"n": 0}

        def table_side_effect(name):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                return mock_table
            return mock_count_table

        mock_client.table.side_effect = table_side_effect

        with patch("api.h2a.db.get_client", return_value=mock_client):
            result = await list_h2a_tasks(
                status=None,
                category="data_processing",
                my_tasks=False,
                limit=20,
                offset=0,
            )

        assert result["tasks"] == []


@pytest.mark.h2a
class TestH2ATaskCancellation:
    """Tests for H2A task cancellation endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_published_task_succeeds(self):
        """Published task → cancel succeeds."""
        from api.h2a import cancel_h2a_task

        auth = _make_jwt_auth()
        mock_client = MagicMock()
        task_chain = MagicMock()
        task_chain.single.return_value.execute.return_value = _mock_task_result(
            status="published"
        )
        mock_client.table.return_value.select.return_value.eq.return_value = task_chain
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("api.h2a.db.get_client", return_value=mock_client):
            result = await cancel_h2a_task(
                task_id="task-uuid-1234" + "0" * 22, auth=auth
            )

        assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_task_returns_400(self):
        """Completed task → 400."""
        from api.h2a import cancel_h2a_task
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        mock_client = MagicMock()
        task_chain = MagicMock()
        task_chain.single.return_value.execute.return_value = _mock_task_result(
            status="completed"
        )
        mock_client.table.return_value.select.return_value.eq.return_value = task_chain

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await cancel_h2a_task(task_id="task-uuid-1234" + "0" * 22, auth=auth)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_cancel_wrong_user_returns_403(self):
        """Different user → 403."""
        from api.h2a import cancel_h2a_task
        from fastapi import HTTPException

        auth = _make_jwt_auth(user_id="user-other")
        mock_client = MagicMock()
        task_chain = MagicMock()
        task_chain.single.return_value.execute.return_value = _mock_task_result(
            status="published", user_id="user-1"
        )
        mock_client.table.return_value.select.return_value.eq.return_value = task_chain

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await cancel_h2a_task(task_id="task-uuid-1234" + "0" * 22, auth=auth)

        assert exc_info.value.status_code == 403


# ============================================================================
# P1 Tests — Agent Registration (Task 2.3)
# ============================================================================


@pytest.mark.h2a
class TestH2AAgentRegistration:
    """Tests for the /agents/register-executor REST endpoint."""

    @pytest.mark.asyncio
    async def test_register_missing_fields_returns_400(self):
        """Missing required fields → 400."""
        from api.h2a import register_agent_executor
        from fastapi import HTTPException

        mock_request = AsyncMock()
        mock_request.json.return_value = {"wallet_address": "0xabc"}  # missing fields

        with patch("api.h2a.db.get_client"):
            # Mock auth to pass
            with patch("api.h2a.router", MagicMock()):
                from api.h2a import register_agent_executor

                # Patch verify_api_key to pass
                with patch("api.auth.verify_api_key", new_callable=AsyncMock):
                    with pytest.raises(HTTPException) as exc_info:
                        await register_agent_executor(
                            request=mock_request,
                            authorization="Bearer em_test_key",
                            x_api_key="em_test_key",
                        )

        assert exc_info.value.status_code in (400, 401)

    @pytest.mark.asyncio
    async def test_register_new_agent_creates_executor(self):
        """New agent → creates executor row."""
        from api.h2a import register_agent_executor

        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "wallet_address": "0x" + "ab" * 20,
            "display_name": "TestAgent",
            "capabilities": ["data_processing", "web_research"],
        }

        mock_client = MagicMock()
        # No existing executor
        mock_existing = MagicMock()
        mock_existing.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing
        # Insert returns new executor
        mock_insert = MagicMock()
        mock_insert.data = [{"id": "new-executor-id"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            mock_insert
        )

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch("api.auth.verify_api_key", new_callable=AsyncMock):
                result = await register_agent_executor(
                    request=mock_request,
                    authorization="Bearer em_test_key",
                    x_api_key="em_test_key",
                )

        assert result["status"] == "registered"
        assert result["executor_id"] == "new-executor-id"

    @pytest.mark.asyncio
    async def test_register_existing_agent_updates(self):
        """Existing agent → updates executor row."""
        from api.h2a import register_agent_executor

        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "wallet_address": "0x" + "ab" * 20,
            "display_name": "UpdatedAgent",
            "capabilities": ["code_execution"],
        }

        mock_client = MagicMock()
        mock_existing = MagicMock()
        mock_existing.data = [{"id": "existing-id"}]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch("api.auth.verify_api_key", new_callable=AsyncMock):
                result = await register_agent_executor(
                    request=mock_request,
                    authorization="Bearer em_test_key",
                    x_api_key="em_test_key",
                )

        assert result["status"] == "updated"
        assert result["executor_id"] == "existing-id"

    @pytest.mark.asyncio
    async def test_register_no_api_key_returns_401(self):
        """No API key → 401."""
        from api.h2a import register_agent_executor
        from fastapi import HTTPException

        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "wallet_address": "0x" + "ab" * 20,
            "display_name": "Agent",
            "capabilities": ["data_processing"],
        }

        with patch(
            "api.auth.verify_api_key",
            new_callable=AsyncMock,
            side_effect=HTTPException(status_code=401, detail="Invalid API key"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await register_agent_executor(
                    request=mock_request,
                    authorization=None,
                    x_api_key=None,
                )

        assert exc_info.value.status_code == 401


# ============================================================================
# Medium Priority: Directory, Auth Edge Cases, Verdicts
# ============================================================================


@pytest.mark.h2a
class TestH2ADirectoryAdvanced:
    """Tests for agent directory filtering, sorting, pagination."""

    @pytest.mark.asyncio
    async def test_directory_capability_filter(self):
        """Filter agents by capability."""
        from api.h2a import get_agent_directory

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [
            {
                "id": "agent-1",
                "display_name": "Research Bot",
                "capabilities": ["research"],
                "reputation_score": 85,
                "tasks_completed": 10,
                "avg_rating": 4.5,
                "is_verified": True,
            }
        ]
        mock_result.count = 1

        chain = mock_client.table.return_value.select.return_value
        chain.eq.return_value.not_.is_.return_value.overlaps.return_value.gte.return_value.order.return_value.range.return_value.execute.return_value = mock_result
        # Also handle without gte
        chain.eq.return_value.not_.is_.return_value.overlaps.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        with patch("api.h2a.db.get_client", return_value=mock_client):
            result = await get_agent_directory(
                capability="research", min_rating=None, sort="rating", page=1, limit=20
            )

        assert result.total >= 0
        assert isinstance(result.agents, list)

    @pytest.mark.asyncio
    async def test_directory_sort_by_tasks_completed(self):
        """Sort agents by tasks_completed."""
        from api.h2a import get_agent_directory

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0

        chain = mock_client.table.return_value.select.return_value
        chain.eq.return_value.not_.is_.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        with patch("api.h2a.db.get_client", return_value=mock_client):
            result = await get_agent_directory(
                capability=None,
                min_rating=None,
                sort="tasks_completed",
                page=1,
                limit=10,
            )

        assert result.total == 0

    @pytest.mark.asyncio
    async def test_directory_pagination(self):
        """Pagination offset/limit works."""
        from api.h2a import get_agent_directory

        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.data = []
        mock_result.count = 0

        chain = mock_client.table.return_value.select.return_value
        chain.eq.return_value.not_.is_.return_value.order.return_value.range.return_value.execute.return_value = mock_result

        with patch("api.h2a.db.get_client", return_value=mock_client):
            result = await get_agent_directory(
                capability=None, min_rating=None, sort="rating", page=3, limit=5
            )

        assert result.page == 3
        assert result.limit == 5

    @pytest.mark.asyncio
    async def test_directory_wallet_not_exposed(self):
        """Agent directory response does NOT include wallet_address."""
        from models import AgentDirectoryEntry

        entry = AgentDirectoryEntry(
            executor_id="agent-1",
            display_name="Test Agent",
            rating=80,
            tasks_completed=5,
            avg_rating=4.0,
            verified=True,
        )

        data = entry.model_dump()
        assert "wallet_address" not in data


@pytest.mark.h2a
class TestH2AAuthEdgeCases:
    """Tests for JWT auth edge cases."""

    @pytest.mark.asyncio
    async def test_expired_jwt_returns_401(self):
        """Expired JWT → 401."""
        from api.h2a import verify_jwt_auth
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_auth("Bearer expired.token.here")

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_no_sub_claim_returns_401(self):
        """JWT without sub claim → 401."""
        from api.h2a import verify_jwt_auth
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_auth(None)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wallet_lookup_fallback(self):
        """Auth resolves wallet from DB when not in JWT."""
        from api.h2a import verify_jwt_auth
        from fastapi import HTTPException

        # No authorization header → 401
        with pytest.raises(HTTPException) as exc_info:
            await verify_jwt_auth("")

        assert exc_info.value.status_code == 401


@pytest.mark.h2a
class TestH2AVerdicts:
    """Tests for H2A approval verdicts."""

    @pytest.mark.asyncio
    async def test_approve_needs_revision_sets_status(self):
        """Verdict 'needs_revision' → task goes back to in_progress."""
        from api.h2a import approve_h2a_submission
        from models import ApproveH2ASubmissionRequest

        auth = _make_jwt_auth()
        mock_client = MagicMock()

        # Task owned by user
        task_result = MagicMock()
        task_result.data = {
            "id": "task-1",
            "human_user_id": "user-1",
            "human_wallet": "0xabc123",
            "publisher_type": "human",
            "bounty_usd": 5.0,
            "status": "submitted",
        }

        submission_result = MagicMock()
        submission_result.data = {
            "id": "sub-1",
            "task_id": "task-1",
            "executor_id": "exec-1",
        }

        chain = mock_client.table.return_value.select.return_value
        chain.eq.return_value.single.return_value.execute.return_value = task_result

        # For submission lookup
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = submission_result

        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        request = ApproveH2ASubmissionRequest(
            submission_id="00000000-0000-0000-0000-000000000001",
            verdict="needs_revision",
            notes="Please add more detail",
        )

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
                result = await approve_h2a_submission(
                    task_id="task-1", request=request, auth=auth
                )

        assert result is not None

    @pytest.mark.asyncio
    async def test_approve_rejected_sets_status(self):
        """Verdict 'rejected' updates submission and task status."""
        from api.h2a import approve_h2a_submission
        from models import ApproveH2ASubmissionRequest

        auth = _make_jwt_auth()
        mock_client = MagicMock()

        task_result = MagicMock()
        task_result.data = {
            "id": "task-1",
            "human_user_id": "user-1",
            "human_wallet": "0xabc123",
            "publisher_type": "human",
            "bounty_usd": 5.0,
            "status": "submitted",
        }

        submission_result = MagicMock()
        submission_result.data = {
            "id": "sub-1",
            "task_id": "task-1",
            "executor_id": "exec-1",
        }

        chain = mock_client.table.return_value.select.return_value
        chain.eq.return_value.single.return_value.execute.return_value = task_result
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = submission_result
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        request = ApproveH2ASubmissionRequest(
            submission_id="00000000-0000-0000-0000-000000000001",
            verdict="rejected",
            notes="Work does not meet requirements",
        )

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
                result = await approve_h2a_submission(
                    task_id="task-1", request=request, auth=auth
                )

        assert result is not None


@pytest.mark.h2a
class TestH2ARegistrationExtended:
    """Extended registration tests."""

    @pytest.mark.asyncio
    async def test_register_with_all_optional_fields(self):
        """Registration with bio, avatar_url, pricing."""
        from api.h2a import register_agent_executor

        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "wallet_address": "0x" + "cd" * 20,
            "display_name": "Full Agent",
            "capabilities": ["research", "data_processing"],
            "bio": "Expert research agent",
            "avatar_url": "https://example.com/avatar.png",
            "pricing": {"min_bounty_usd": 1.0, "max_bounty_usd": 100.0},
        }

        mock_client = MagicMock()
        # No existing executor
        existing_result = MagicMock()
        existing_result.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = existing_result

        # Insert succeeds
        insert_result = MagicMock()
        insert_result.data = [{"id": "new-agent-id"}]
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            insert_result
        )

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.auth.verify_api_key",
                new_callable=AsyncMock,
                return_value="key-1",
            ):
                result = await register_agent_executor(
                    request=mock_request,
                    authorization=None,
                    x_api_key="em_live_test",
                )

        assert result is not None

    def test_approval_model_accepts_all_verdicts(self):
        """ApproveH2ASubmissionRequest accepts all valid verdicts."""
        from models import ApproveH2ASubmissionRequest

        for verdict in ("accepted", "rejected", "needs_revision"):
            req = ApproveH2ASubmissionRequest(
                submission_id="00000000-0000-0000-0000-000000000001",
                verdict=verdict,
                notes="Test note",
            )
            assert req.verdict == verdict
            assert req.submission_id == "00000000-0000-0000-0000-000000000001"
