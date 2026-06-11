"""
Tests for H2A escrow-mode (sign-on-assignment) — Universal Escrow Consistency.

Covers MASTER_PLAN_UNIVERSAL_ESCROW_CONSISTENCY v2 tasks:
- T1.1/T1.3: publish creates the escrow marker (flag-gated), rolls back the
  task on marker failure, rejects non-escrow networks and bounty > $100.
- T1.5: payment-config serves the escrow signing parameters per network.
- T2.1: assign requires X-Payment-Auth for marker tasks, locks via
  lock_with_fresh_auth, reverts on failure; legacy tasks drain unchanged.
- T3.1: approve releases a locked escrow without settlement signatures;
  legacy tasks still require both signatures.
- T4.1: cancel — free cancel for unlocked markers, on-chain refund for
  deposited escrows, 502 on refund failure (task unchanged).
"""

import sys
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from decimal import Decimal
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# 36-char UUID-shaped id for direct handler calls.
TASK_ID = "00000000-0000-0000-0000-00000000abcd"
SUB_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


# ============================================================================
# Fixtures / helpers
# ============================================================================


def _make_jwt_auth(user_id="user-1", wallet="0xabc123"):
    from api.h2a import JWTData

    return JWTData(user_id=user_id, wallet_address=wallet)


def _publish_request(**overrides):
    from models import PublishH2ATaskRequest

    data = dict(
        title="Escrow test task",
        instructions="Do something important for escrow testing",
        category="data_processing",
        bounty_usd=5.0,
        deadline_hours=24,
        evidence_required=["text_report"],
    )
    data.update(overrides)
    return PublishH2ATaskRequest(**data)


def _publish_mock_client(task_id="task-uuid-new"):
    """Mock Supabase client for create_h2a_task (insert + update + delete)."""
    mock_client = MagicMock()
    insert_result = MagicMock()
    insert_result.data = [{"id": task_id, "status": "published"}]
    mock_client.table.return_value.insert.return_value.execute.return_value = (
        insert_result
    )
    return mock_client


def _task_row(status="published", **overrides):
    row = {
        "id": TASK_ID,
        "human_user_id": "user-1",
        "human_wallet": "0xabc123",
        "publisher_type": "human",
        "status": status,
        "bounty_usd": 5.0,
        "payment_network": "base",
        "payment_token": "USDC",
    }
    row.update(overrides)
    return row


def _assign_mock_client(
    updates,
    task_status="published",
    app_found=True,
    worker_wallet="0xworker456",
):
    """Mock Supabase client for assign_h2a_worker."""
    mock_client = MagicMock()

    task_chain = MagicMock()
    task_result = MagicMock()
    task_result.data = _task_row(status=task_status)
    task_chain.single.return_value.execute.return_value = task_result

    app_result = MagicMock()
    app_result.data = [{"id": "app-1"}] if app_found else []

    exec_result = MagicMock()
    exec_result.data = [{"wallet_address": worker_wallet}]

    def _recorder(table_name):
        def _update(data):
            updates.append((table_name, data))
            return MagicMock()

        return _update

    def table_side_effect(name):
        mock_table = MagicMock()
        if name == "tasks":
            mock_table.select.return_value.eq.return_value = task_chain
            mock_table.update.side_effect = _recorder("tasks")
        elif name == "task_applications":
            mock_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = app_result
            mock_table.update.side_effect = _recorder("task_applications")
        elif name == "executors":
            mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = exec_result
        return mock_table

    mock_client.table.side_effect = table_side_effect
    return mock_client


def _approve_mock_client(esc_rows, updates):
    """Mock Supabase client for approve_h2a_submission."""
    mock_client = MagicMock()

    task_chain = MagicMock()
    task_result = MagicMock()
    task_result.data = _task_row(status="submitted")
    task_chain.single.return_value.execute.return_value = task_result

    sub_chain = MagicMock()
    sub_result = MagicMock()
    sub_result.data = {
        "id": SUB_ID,
        "task_id": TASK_ID,
        "executor": {
            "id": "executor-1",
            "wallet_address": "0xworker456",
            "display_name": "Agent007",
        },
    }
    sub_chain.single.return_value.execute.return_value = sub_result

    esc_result = MagicMock()
    esc_result.data = esc_rows

    def _recorder(table_name):
        def _update(data):
            updates.append((table_name, data))
            return MagicMock()

        return _update

    def table_side_effect(name):
        mock_table = MagicMock()
        if name == "tasks":
            mock_table.select.return_value.eq.return_value = task_chain
            mock_table.update.side_effect = _recorder("tasks")
        elif name == "submissions":
            mock_table.select.return_value.eq.return_value.eq.return_value = sub_chain
            mock_table.update.side_effect = _recorder("submissions")
        elif name == "escrows":
            mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = esc_result
        return mock_table

    mock_client.table.side_effect = table_side_effect
    return mock_client


def _cancel_mock_client(esc_rows, updates, task_status="published"):
    """Mock Supabase client for cancel_h2a_task."""
    mock_client = MagicMock()

    task_chain = MagicMock()
    task_result = MagicMock()
    task_result.data = _task_row(status=task_status)
    task_chain.single.return_value.execute.return_value = task_result

    esc_result = MagicMock()
    esc_result.data = esc_rows

    def _recorder(table_name):
        def _update(data):
            updates.append((table_name, data))
            return MagicMock()

        return _update

    def table_side_effect(name):
        mock_table = MagicMock()
        if name == "tasks":
            mock_table.select.return_value.eq.return_value = task_chain
            mock_table.update.side_effect = _recorder("tasks")
        elif name == "escrows":
            mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = esc_result
            mock_table.update.side_effect = _recorder("escrows")
        return mock_table

    mock_client.table.side_effect = table_side_effect
    return mock_client


# ============================================================================
# T1.1 / T1.3 — Publish (escrow marker, flag-gated)
# ============================================================================


@pytest.mark.h2a
class TestH2AEscrowPublish:
    @pytest.mark.asyncio
    async def test_flag_on_publish_creates_marker(self, monkeypatch):
        """Flag on -> escrow marker row created after the task insert."""
        monkeypatch.setenv("EM_H2A_ESCROW_ENABLED", "true")
        from api.h2a import create_h2a_task

        auth = _make_jwt_auth()
        request = _publish_request()
        mock_client = _publish_mock_client()

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.01"), Decimal("500.00")),
            ):
                with patch(
                    "api.h2a.get_platform_fee_percent",
                    new_callable=AsyncMock,
                    return_value=Decimal("0.13"),
                ):
                    with patch("api.h2a.db.get_client", return_value=mock_client):
                        with patch(
                            "api.h2a.create_escrow_marker", new_callable=AsyncMock
                        ) as mock_marker:
                            result = await create_h2a_task(request=request, auth=auth)

        assert result.task_id == "task-uuid-new"
        mock_marker.assert_awaited_once()
        args = mock_marker.await_args[0]
        assert args == ("task-uuid-new", 5.0, "base", "0xabc123")

    @pytest.mark.asyncio
    async def test_flag_on_marker_failure_rolls_back_task(self, monkeypatch):
        """Marker insert raises -> the just-inserted task row is deleted, 500."""
        monkeypatch.setenv("EM_H2A_ESCROW_ENABLED", "true")
        from api.h2a import create_h2a_task
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        request = _publish_request()
        mock_client = _publish_mock_client()

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.01"), Decimal("500.00")),
            ):
                with patch(
                    "api.h2a.get_platform_fee_percent",
                    new_callable=AsyncMock,
                    return_value=Decimal("0.13"),
                ):
                    with patch("api.h2a.db.get_client", return_value=mock_client):
                        with patch(
                            "api.h2a.create_escrow_marker",
                            new_callable=AsyncMock,
                            side_effect=Exception("escrows insert failed"),
                        ):
                            with pytest.raises(HTTPException) as exc_info:
                                await create_h2a_task(request=request, auth=auth)

        assert exc_info.value.status_code == 500
        assert "escrow marker" in exc_info.value.detail.lower()
        # The task row must have been deleted (no escrow-mode task without marker)
        assert mock_client.table.return_value.delete.called

    @pytest.mark.asyncio
    async def test_flag_on_rejects_solana(self, monkeypatch):
        """Flag on + Solana (no x402r escrow) -> 400."""
        monkeypatch.setenv("EM_H2A_ESCROW_ENABLED", "true")
        from api.h2a import create_h2a_task
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        request = _publish_request(payment_network="solana")

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.01"), Decimal("500.00")),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await create_h2a_task(request=request, auth=auth)

        assert exc_info.value.status_code == 400
        assert "escrow" in exc_info.value.detail.lower()
        assert "solana" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_flag_on_rejects_bounty_over_100(self, monkeypatch):
        """Flag on + bounty > $100 -> 400 (DEPOSIT_LIMIT contract condition)."""
        monkeypatch.setenv("EM_H2A_ESCROW_ENABLED", "true")
        from api.h2a import create_h2a_task
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        request = _publish_request(bounty_usd=150.0)

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.01"), Decimal("500.00")),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await create_h2a_task(request=request, auth=auth)

        assert exc_info.value.status_code == 400
        assert "$100" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_flag_off_publish_unchanged(self, monkeypatch):
        """Flag off (default) -> no marker, behavior unchanged."""
        monkeypatch.delenv("EM_H2A_ESCROW_ENABLED", raising=False)
        from api.h2a import create_h2a_task

        auth = _make_jwt_auth()
        request = _publish_request()
        mock_client = _publish_mock_client()

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.01"), Decimal("500.00")),
            ):
                with patch(
                    "api.h2a.get_platform_fee_percent",
                    new_callable=AsyncMock,
                    return_value=Decimal("0.13"),
                ):
                    with patch("api.h2a.db.get_client", return_value=mock_client):
                        with patch(
                            "api.h2a.create_escrow_marker", new_callable=AsyncMock
                        ) as mock_marker:
                            result = await create_h2a_task(request=request, auth=auth)

        assert result.task_id == "task-uuid-new"
        assert result.status == "published"
        mock_marker.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_flag_off_allows_solana_and_large_bounty(self, monkeypatch):
        """Flag off -> escrow-only restrictions do not apply."""
        monkeypatch.delenv("EM_H2A_ESCROW_ENABLED", raising=False)
        from api.h2a import create_h2a_task

        auth = _make_jwt_auth()
        request = _publish_request(bounty_usd=150.0)
        mock_client = _publish_mock_client()

        with patch("api.h2a._check_h2a_enabled", new_callable=AsyncMock):
            with patch(
                "api.h2a._get_h2a_bounty_limits",
                new_callable=AsyncMock,
                return_value=(Decimal("0.01"), Decimal("500.00")),
            ):
                with patch(
                    "api.h2a.get_platform_fee_percent",
                    new_callable=AsyncMock,
                    return_value=Decimal("0.13"),
                ):
                    with patch("api.h2a.db.get_client", return_value=mock_client):
                        result = await create_h2a_task(request=request, auth=auth)

        assert result.bounty_usd == 150.0


# ============================================================================
# T2.1 — Assign (lock at assignment / legacy drain)
# ============================================================================

_MARKER_ROW = {"id": "esc-1", "status": "pending_assignment", "metadata": {}}


@pytest.mark.h2a
class TestH2AEscrowAssign:
    @pytest.mark.asyncio
    async def test_legacy_no_marker_passthrough(self):
        """No escrow marker -> status-only assign, lock helper never called."""
        from api.h2a import assign_h2a_worker, H2AAssignRequest

        auth = _make_jwt_auth()
        updates = []
        mock_client = _assign_mock_client(updates)

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "api.h2a.lock_with_fresh_auth", new_callable=AsyncMock
                ) as mock_lock:
                    result = await assign_h2a_worker(
                        task_id=TASK_ID,
                        request=H2AAssignRequest(executor_id="exec-1"),
                        auth=auth,
                        x_payment_auth=None,
                    )

        assert result["status"] == "accepted"
        assert "escrow_tx" not in result
        mock_lock.assert_not_awaited()
        assert ("tasks", {"executor_id": "exec-1", "status": "accepted"}) in updates

    @pytest.mark.asyncio
    async def test_marker_without_header_returns_402(self):
        """Marker task + no X-Payment-Auth -> 402, no mutation."""
        from api.h2a import assign_h2a_worker, H2AAssignRequest
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        updates = []
        mock_client = _assign_mock_client(updates)

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=dict(_MARKER_ROW),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await assign_h2a_worker(
                        task_id=TASK_ID,
                        request=H2AAssignRequest(executor_id="exec-1"),
                        auth=auth,
                        x_payment_auth=None,
                    )

        assert exc_info.value.status_code == 402
        assert "X-Payment-Auth" in exc_info.value.detail
        assert "payment-config" in exc_info.value.detail
        assert updates == []  # nothing mutated

    @pytest.mark.asyncio
    async def test_marker_locked_happy_path(self):
        """Marker + header -> accepted, escrow locked, applications updated."""
        from api.h2a import assign_h2a_worker, H2AAssignRequest

        auth = _make_jwt_auth()
        updates = []
        mock_client = _assign_mock_client(updates)
        mock_dispatcher = MagicMock()

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=dict(_MARKER_ROW),
            ):
                with patch(
                    "api.h2a.get_payment_dispatcher", return_value=mock_dispatcher
                ):
                    with patch(
                        "api.h2a.lock_with_fresh_auth",
                        new_callable=AsyncMock,
                        return_value={
                            "status": "locked",
                            "escrow_tx": "0xlock123",
                            "network": "base",
                        },
                    ) as mock_lock:
                        result = await assign_h2a_worker(
                            task_id=TASK_ID,
                            request=H2AAssignRequest(executor_id="exec-1"),
                            auth=auth,
                            x_payment_auth='{"x402Version": 2}',
                        )

        assert result["status"] == "accepted"
        assert result["escrow_tx"] == "0xlock123"
        # Assignment mutation happened BEFORE the lock
        assert ("tasks", {"executor_id": "exec-1", "status": "accepted"}) in updates
        # Applications updated as today
        assert ("task_applications", {"status": "accepted"}) in updates
        assert ("task_applications", {"status": "rejected"}) in updates
        # Lock called with the worker wallet and the publisher as payer
        kwargs = mock_lock.await_args
        assert kwargs[0][2] == "0xworker456"  # worker_wallet
        assert kwargs[1]["expected_payer"] == "0xabc123"

    @pytest.mark.asyncio
    async def test_marker_invalid_auth_reverts_and_400(self):
        """invalid_auth -> task reverted to published, HTTP 400."""
        from api.h2a import assign_h2a_worker, H2AAssignRequest
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        updates = []
        mock_client = _assign_mock_client(updates)

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=dict(_MARKER_ROW),
            ):
                with patch("api.h2a.get_payment_dispatcher", return_value=MagicMock()):
                    with patch(
                        "api.h2a.lock_with_fresh_auth",
                        new_callable=AsyncMock,
                        return_value={
                            "status": "invalid_auth",
                            "error": "receiver mismatch",
                        },
                    ):
                        with pytest.raises(HTTPException) as exc_info:
                            await assign_h2a_worker(
                                task_id=TASK_ID,
                                request=H2AAssignRequest(executor_id="exec-1"),
                                auth=auth,
                                x_payment_auth='{"x402Version": 2}',
                            )

        assert exc_info.value.status_code == 400
        assert "receiver mismatch" in exc_info.value.detail
        assert ("tasks", {"status": "published", "executor_id": None}) in updates

    @pytest.mark.asyncio
    async def test_marker_lock_failed_reverts_and_402(self):
        """lock_failed -> task reverted to published, HTTP 402."""
        from api.h2a import assign_h2a_worker, H2AAssignRequest
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        updates = []
        mock_client = _assign_mock_client(updates)

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=dict(_MARKER_ROW),
            ):
                with patch("api.h2a.get_payment_dispatcher", return_value=MagicMock()):
                    with patch(
                        "api.h2a.lock_with_fresh_auth",
                        new_callable=AsyncMock,
                        return_value={
                            "status": "lock_failed",
                            "error": "Facilitator refused",
                        },
                    ):
                        with pytest.raises(HTTPException) as exc_info:
                            await assign_h2a_worker(
                                task_id=TASK_ID,
                                request=H2AAssignRequest(executor_id="exec-1"),
                                auth=auth,
                                x_payment_auth='{"x402Version": 2}',
                            )

        assert exc_info.value.status_code == 402
        assert "Escrow lock failed. Task remains published" in exc_info.value.detail
        assert ("tasks", {"status": "published", "executor_id": None}) in updates

    @pytest.mark.asyncio
    async def test_marker_worker_without_wallet_400_before_mutation(self):
        """Missing worker wallet -> 400 BEFORE any task mutation."""
        from api.h2a import assign_h2a_worker, H2AAssignRequest
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        updates = []
        mock_client = _assign_mock_client(updates, worker_wallet=None)

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=dict(_MARKER_ROW),
            ):
                with pytest.raises(HTTPException) as exc_info:
                    await assign_h2a_worker(
                        task_id=TASK_ID,
                        request=H2AAssignRequest(executor_id="exec-1"),
                        auth=auth,
                        x_payment_auth='{"x402Version": 2}',
                    )

        assert exc_info.value.status_code == 400
        assert "wallet" in exc_info.value.detail.lower()
        assert updates == []


# ============================================================================
# T3.1 — Approve (escrow release vs legacy signatures)
# ============================================================================


@pytest.mark.h2a
class TestH2AEscrowApprove:
    def _approve_request(self, with_sigs=False):
        from models import ApproveH2ASubmissionRequest

        kwargs = dict(submission_id=SUB_ID, verdict="accepted")
        if with_sigs:
            kwargs["settlement_auth_worker"] = "0xworkerauth"
            kwargs["settlement_auth_fee"] = "0xfeeauth"
        return ApproveH2ASubmissionRequest(**kwargs)

    @pytest.mark.asyncio
    async def test_escrow_release_without_signatures(self):
        """Releasable escrow -> release via dispatcher, no signatures needed."""
        from api.h2a import approve_h2a_submission

        auth = _make_jwt_auth()
        updates = []
        mock_client = _approve_mock_client(
            esc_rows=[{"id": "esc-1", "status": "deposited", "funding_tx": "0xfund"}],
            updates=updates,
        )
        mock_dispatcher = MagicMock()
        mock_dispatcher.release_direct_to_worker = AsyncMock(
            return_value={
                "success": True,
                "tx_hash": "0xrelease789",
                "fee_distribute_tx": "0xfeedist",
            }
        )

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch("api.h2a.get_payment_dispatcher", return_value=mock_dispatcher):
                result = await approve_h2a_submission(
                    task_id=TASK_ID,
                    request=self._approve_request(with_sigs=False),
                    auth=auth,
                )

        assert result.status == "accepted"
        assert result.worker_tx == "0xrelease789"
        assert result.fee_tx == "0xfeedist"
        mock_dispatcher.release_direct_to_worker.assert_awaited_once_with(
            task_id=TASK_ID, network="base", token="USDC"
        )
        # Status updates happened as today
        tasks_updates = [d for t, d in updates if t == "tasks"]
        assert any(u.get("status") == "completed" for u in tasks_updates)
        sub_updates = [d for t, d in updates if t == "submissions"]
        assert any(u.get("agent_verdict") == "accepted" for u in sub_updates)

    @pytest.mark.asyncio
    async def test_escrow_release_ignores_sent_signatures(self):
        """settlement_auth_* are ignored when the escrow is releasable."""
        from api.h2a import approve_h2a_submission

        auth = _make_jwt_auth()
        updates = []
        mock_client = _approve_mock_client(
            esc_rows=[{"id": "esc-1", "status": "LOCKED", "funding_tx": "0xfund"}],
            updates=updates,
        )
        mock_dispatcher = MagicMock()
        mock_dispatcher.release_direct_to_worker = AsyncMock(
            return_value={
                "success": True,
                "tx_hash": "0xrel",
                "fee_distribute_tx": None,
            }
        )
        mock_sdk = AsyncMock()

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch("api.h2a.get_payment_dispatcher", return_value=mock_dispatcher):
                with patch(
                    "integrations.x402.sdk_client.get_sdk", return_value=mock_sdk
                ):
                    result = await approve_h2a_submission(
                        task_id=TASK_ID,
                        request=self._approve_request(with_sigs=True),
                        auth=auth,
                    )

        assert result.status == "accepted"
        assert result.worker_tx == "0xrel"
        # The legacy 2-transfer settlement must NOT have been used
        mock_sdk._settle_external_auths.assert_not_called()

    @pytest.mark.asyncio
    async def test_escrow_release_failure_returns_502_statuses_unchanged(self):
        """Release failure -> 502 and NO task/submission status updates."""
        from api.h2a import approve_h2a_submission
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        updates = []
        mock_client = _approve_mock_client(
            esc_rows=[{"id": "esc-1", "status": "deposited", "funding_tx": "0xfund"}],
            updates=updates,
        )
        mock_dispatcher = MagicMock()
        mock_dispatcher.release_direct_to_worker = AsyncMock(
            return_value={"success": False, "error": "facilitator down"}
        )

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch("api.h2a.get_payment_dispatcher", return_value=mock_dispatcher):
                with pytest.raises(HTTPException) as exc_info:
                    await approve_h2a_submission(
                        task_id=TASK_ID,
                        request=self._approve_request(with_sigs=False),
                        auth=auth,
                    )

        assert exc_info.value.status_code == 502
        assert "facilitator down" in exc_info.value.detail
        assert updates == []  # statuses untouched

    @pytest.mark.asyncio
    async def test_legacy_path_still_requires_signatures(self):
        """No escrow row -> legacy branch -> 400 without both signatures."""
        from api.h2a import approve_h2a_submission
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        updates = []
        mock_client = _approve_mock_client(esc_rows=[], updates=updates)

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await approve_h2a_submission(
                    task_id=TASK_ID,
                    request=self._approve_request(with_sigs=False),
                    auth=auth,
                )

        assert exc_info.value.status_code == 400
        assert "signatures required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_self_collusion_guard_applies_to_escrow_branch(self):
        """Worker wallet == publisher wallet -> 403 even with a locked escrow."""
        from api.h2a import approve_h2a_submission
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        updates = []
        mock_client = _approve_mock_client(
            esc_rows=[{"id": "esc-1", "status": "deposited", "funding_tx": "0xfund"}],
            updates=updates,
        )
        # Make the submission's executor wallet equal the publisher wallet
        sub_result = MagicMock()
        sub_result.data = {
            "id": SUB_ID,
            "task_id": TASK_ID,
            "executor": {
                "id": "executor-1",
                "wallet_address": "0xabc123",
                "display_name": "SelfDealer",
            },
        }
        # Rebuild client with the colluding submission
        orig_side_effect = mock_client.table.side_effect

        def table_side_effect(name):
            table = orig_side_effect(name)
            if name == "submissions":
                chain = MagicMock()
                chain.single.return_value.execute.return_value = sub_result
                table.select.return_value.eq.return_value.eq.return_value = chain
            return table

        mock_client.table.side_effect = table_side_effect

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await approve_h2a_submission(
                    task_id=TASK_ID,
                    request=self._approve_request(with_sigs=False),
                    auth=auth,
                )

        assert exc_info.value.status_code == 403


# ============================================================================
# T4.1 — Cancel (free cancel / refund / refund failure)
# ============================================================================


@pytest.mark.h2a
class TestH2AEscrowCancel:
    @pytest.mark.asyncio
    async def test_cancel_with_pending_marker_is_free(self):
        """pending_assignment marker -> cancel task + escrow row cancelled."""
        from api.h2a import cancel_h2a_task

        auth = _make_jwt_auth()
        updates = []
        mock_client = _cancel_mock_client(esc_rows=[], updates=updates)

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=dict(_MARKER_ROW),
            ):
                result = await cancel_h2a_task(task_id=TASK_ID, auth=auth)

        assert result["status"] == "cancelled"
        assert "refund_tx" not in result
        assert ("tasks", {"status": "cancelled"}) in updates
        assert ("escrows", {"status": "cancelled"}) in updates

    @pytest.mark.asyncio
    async def test_cancel_deposited_escrow_refunds(self):
        """Deposited escrow -> refund_trustless_escrow then cancel."""
        from api.h2a import cancel_h2a_task

        auth = _make_jwt_auth()
        updates = []
        mock_client = _cancel_mock_client(
            esc_rows=[{"id": "esc-1", "status": "deposited"}],
            updates=updates,
            task_status="accepted",
        )
        mock_dispatcher = MagicMock()
        mock_dispatcher.refund_trustless_escrow = AsyncMock(
            return_value={"success": True, "tx_hash": "0xrefund42"}
        )

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "api.h2a.get_payment_dispatcher", return_value=mock_dispatcher
                ):
                    result = await cancel_h2a_task(task_id=TASK_ID, auth=auth)

        assert result["status"] == "cancelled"
        assert result["refund_tx"] == "0xrefund42"
        mock_dispatcher.refund_trustless_escrow.assert_awaited_once_with(
            task_id=TASK_ID, reason="h2a_cancel"
        )
        assert ("tasks", {"status": "cancelled"}) in updates
        escrow_updates = [d for t, d in updates if t == "escrows"]
        assert any(u.get("status") == "refunded" for u in escrow_updates)

    @pytest.mark.asyncio
    async def test_cancel_refund_failure_returns_502_task_unchanged(self):
        """Refund failure -> 502, task NOT cancelled."""
        from api.h2a import cancel_h2a_task
        from fastapi import HTTPException

        auth = _make_jwt_auth()
        updates = []
        mock_client = _cancel_mock_client(
            esc_rows=[{"id": "esc-1", "status": "deposited"}],
            updates=updates,
            task_status="accepted",
        )
        mock_dispatcher = MagicMock()
        mock_dispatcher.refund_trustless_escrow = AsyncMock(
            return_value={"success": False, "error": "refund reverted"}
        )

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=None,
            ):
                with patch(
                    "api.h2a.get_payment_dispatcher", return_value=mock_dispatcher
                ):
                    with pytest.raises(HTTPException) as exc_info:
                        await cancel_h2a_task(task_id=TASK_ID, auth=auth)

        assert exc_info.value.status_code == 502
        assert "refund reverted" in exc_info.value.detail
        assert ("tasks", {"status": "cancelled"}) not in updates

    @pytest.mark.asyncio
    async def test_cancel_no_escrow_rows_legacy(self):
        """No marker, no escrow rows -> legacy status-only cancel."""
        from api.h2a import cancel_h2a_task

        auth = _make_jwt_auth()
        updates = []
        mock_client = _cancel_mock_client(esc_rows=[], updates=updates)

        with patch("api.h2a.db.get_client", return_value=mock_client):
            with patch(
                "api.h2a.get_escrow_marker",
                new_callable=AsyncMock,
                return_value=None,
            ):
                result = await cancel_h2a_task(task_id=TASK_ID, auth=auth)

        assert result["status"] == "cancelled"
        assert ("tasks", {"status": "cancelled"}) in updates
        # No escrow mutations
        assert not any(t == "escrows" for t, _ in updates)


# ============================================================================
# T1.5 — Payment config (escrow signing parameters)
# ============================================================================


@pytest.mark.h2a
class TestH2APaymentConfig:
    @pytest.mark.asyncio
    async def test_payment_config_serves_escrow_parameters(self):
        from api.h2a import get_h2a_payment_config

        with patch(
            "api.h2a.get_platform_fee_percent",
            new_callable=AsyncMock,
            return_value=Decimal("0.13"),
        ):
            cfg = await get_h2a_payment_config()

        # Backward-compatible top-level keys
        assert cfg["fee_pct"] == 0.13
        assert cfg["treasury"]

        escrow = cfg["escrow"]
        assert escrow["payment_info_typehash"] == (
            "0xae68ac7ce30c86ece8196b61a7c486d8f0061f575037fbd34e7fe4e2820c6591"
        )
        assert escrow["min_fee_bps"] == 0
        assert escrow["max_fee_bps"] == 1800
        assert escrow["deposit_limit_usd"] == 100
        assert escrow["tier_timings"]["micro"] == {
            "pre": 3600,
            "auth": 7200,
            "refund": 86400,
        }
        assert escrow["tier_timings"]["standard"] == {
            "pre": 7200,
            "auth": 86400,
            "refund": 604800,
        }

    @pytest.mark.asyncio
    async def test_payment_config_per_network_entries(self):
        from api.h2a import get_h2a_payment_config
        from integrations.x402.sdk_client import has_escrow_support

        with patch(
            "api.h2a.get_platform_fee_percent",
            new_callable=AsyncMock,
            return_value=Decimal("0.13"),
        ):
            cfg = await get_h2a_payment_config()

        networks = cfg["escrow"]["networks"]
        # Solana has no x402r escrow -> excluded
        assert "solana" not in networks
        assert not any(not has_escrow_support(n) for n in networks)

        base = networks["base"]
        assert base["chain_id"] == 8453
        assert base["operator"] == "0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb"
        assert base["escrow"] == "0xb9488351E48b23D798f24e8174514F28B741Eb4f"
        assert base["token_collector"] == ("0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8")
        assert base["usdc"] == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        assert base["usdc_domain_name"] == "USD Coin"
        assert base["usdc_domain_version"] == "2"
