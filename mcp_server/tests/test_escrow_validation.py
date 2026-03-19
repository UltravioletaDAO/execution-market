"""
Tests for escrow validation at assignment, submission, and approval checkpoints.

Verifies that evidence cannot be submitted or approved without confirmed escrow
when EM_PAYMENT_MODE is not "fase1". Also verifies that fase1 mode skips
escrow validation entirely.

Checkpoint locations:
- submit_work()     in supabase_client.py  — rejects if escrow not funded
- assign_task()     in supabase_client.py  — rejects if no escrow record or wrong status
- approve_submission() in api/routers/submissions.py — rejects if escrow not releasable
"""

import pytest

pytestmark = pytest.mark.payments

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock


# =============================================================================
# Helpers
# =============================================================================


def _make_task(
    task_id=None,
    agent_id="agent-test-001",
    executor_id="exec-test-001",
    status="accepted",
):
    """Build a minimal task dict that passes submit_work / assign_task preconditions."""
    return {
        "id": task_id or str(uuid.uuid4()),
        "agent_id": agent_id,
        "executor_id": executor_id,
        "status": status,
        "title": "Test escrow validation task",
        "instructions": "Verify escrow state",
        "category": "simple_action",
        "bounty_usd": 10.00,
        "deadline": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "evidence_schema": {"required": ["text_response"], "optional": []},
        "min_reputation": 0,
    }


def _mock_escrow_query(mock_client, escrow_data):
    """
    Wire up the mock supabase client so that
    client.table("escrows").select(...).eq(...).limit(1).execute()
    returns the given escrow_data list.
    """
    mock_result = MagicMock()
    mock_result.data = escrow_data

    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = mock_result

    # table() should return a different chain depending on the table name.
    # We set up "escrows" to use our chain, and everything else to use a
    # passthrough that returns empty data by default.
    original_table = mock_client.table

    def _table_router(name):
        if name == "escrows":
            return chain
        return original_table(name)

    mock_client.table = MagicMock(side_effect=_table_router)
    return chain


def _mock_submissions_insert(mock_client, submission_id=None):
    """
    Wire up mock for client.table("submissions").insert(...).execute()
    so submit_work() can create the submission row.
    """
    sub_id = submission_id or str(uuid.uuid4())
    insert_result = MagicMock()
    insert_result.data = [
        {
            "id": sub_id,
            "task_id": "will-be-set",
            "executor_id": "will-be-set",
            "evidence": {},
            "agent_verdict": "pending",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    # Build: client.table("submissions").insert(data).execute()
    insert_chain = MagicMock()
    insert_chain.execute.return_value = insert_result

    submissions_chain = MagicMock()
    submissions_chain.insert.return_value = insert_chain

    original_table = mock_client.table

    def _table_router(name):
        if name == "submissions":
            return submissions_chain
        return original_table(name)

    mock_client.table = MagicMock(side_effect=_table_router)
    return sub_id


def _mock_table_router(mock_client, table_map):
    """
    General-purpose table router: table_map = {"escrows": chain, "submissions": chain, ...}.
    Falls back to a default MagicMock for unspecified tables.
    """
    default = MagicMock()
    default_result = MagicMock()
    default_result.data = []
    default.select.return_value = default
    default.eq.return_value = default
    default.limit.return_value = default
    default.single.return_value = default
    default.execute.return_value = default_result

    def _router(name):
        return table_map.get(name, default)

    mock_client.table = MagicMock(side_effect=_router)


# =============================================================================
# Test 1: submit_work rejects when no escrow record exists (fase2)
# =============================================================================


@pytest.mark.asyncio
async def test_submit_work_rejects_without_escrow(monkeypatch):
    """
    In fase2 mode, submit_work() must reject if no escrow record is found
    for the task in the escrows table.
    """
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase2")

    task = _make_task(status="accepted")
    task_id = task["id"]

    mock_client = MagicMock()

    # Escrow query returns empty — no record
    _mock_escrow_query(mock_client, escrow_data=[])

    with (
        patch("supabase_client.get_client", return_value=mock_client),
        patch("supabase_client.get_task", new_callable=AsyncMock, return_value=task),
    ):
        from supabase_client import submit_work

        with pytest.raises(Exception, match="no escrow record found"):
            await submit_work(
                task_id=task_id,
                executor_id=task["executor_id"],
                evidence={"text_response": "test answer"},
            )


# =============================================================================
# Test 2: submit_work rejects when escrow exists but status is pending
# =============================================================================


@pytest.mark.asyncio
async def test_submit_work_rejects_pending_escrow(monkeypatch):
    """
    In fase2 mode, submit_work() must reject if the escrow record exists
    but its status is not in the set of funded statuses (e.g. "pending").
    """
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase2")

    task = _make_task(status="accepted")
    task_id = task["id"]

    mock_client = MagicMock()

    # Escrow exists but status is "pending" (not funded)
    _mock_escrow_query(mock_client, escrow_data=[{"status": "pending"}])

    with (
        patch("supabase_client.get_client", return_value=mock_client),
        patch("supabase_client.get_task", new_callable=AsyncMock, return_value=task),
    ):
        from supabase_client import submit_work

        with pytest.raises(Exception, match="escrow not confirmed"):
            await submit_work(
                task_id=task_id,
                executor_id=task["executor_id"],
                evidence={"text_response": "test answer"},
            )


# =============================================================================
# Test 3: submit_work allows submission when escrow is funded
# =============================================================================


@pytest.mark.asyncio
async def test_submit_work_allows_funded_escrow(monkeypatch):
    """
    In fase2 mode, submit_work() must allow submission when escrow
    status is "funded" (one of the accepted funded statuses).
    """
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase2")

    task = _make_task(status="accepted")
    task_id = task["id"]

    mock_client = MagicMock()

    # --- Set up escrow chain (funded) ---
    escrow_result = MagicMock()
    escrow_result.data = [{"status": "funded", "expires_at": None}]
    escrow_chain = MagicMock()
    escrow_chain.select.return_value = escrow_chain
    escrow_chain.eq.return_value = escrow_chain
    escrow_chain.limit.return_value = escrow_chain
    escrow_chain.execute.return_value = escrow_result

    # --- Set up submissions insert chain ---
    sub_id = str(uuid.uuid4())
    insert_result = MagicMock()
    insert_result.data = [
        {
            "id": sub_id,
            "task_id": task_id,
            "executor_id": task["executor_id"],
            "evidence": {"text_response": "test answer"},
            "agent_verdict": "pending",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    insert_chain = MagicMock()
    insert_chain.execute.return_value = insert_result
    submissions_chain = MagicMock()
    submissions_chain.insert.return_value = insert_chain

    # --- Wire up table router ---
    _mock_table_router(
        mock_client,
        {"escrows": escrow_chain, "submissions": submissions_chain},
    )

    # update_task is called to set status to "submitted"
    with (
        patch("supabase_client.get_client", return_value=mock_client),
        patch("supabase_client.get_task", new_callable=AsyncMock, return_value=task),
        patch("supabase_client.update_task", new_callable=AsyncMock, return_value=task),
    ):
        from supabase_client import submit_work

        result = await submit_work(
            task_id=task_id,
            executor_id=task["executor_id"],
            evidence={"text_response": "test answer"},
        )

        # Should succeed — no escrow-related exception
        assert result is not None
        assert "submission" in result
        assert result["submission"]["id"] == sub_id


# =============================================================================
# Test 4: assign_task rejects when no escrow record exists (fase2)
# =============================================================================


@pytest.mark.asyncio
async def test_assign_task_rejects_without_escrow(monkeypatch):
    """
    In fase2 mode, assign_task() must reject if no escrow record is found
    for the task.
    """
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase2")

    task = _make_task(status="published", executor_id=None)
    task_id = task["id"]
    agent_id = task["agent_id"]
    executor_id = "exec-worker-001"

    mock_client = MagicMock()

    # --- Set up executor lookup (must pass precondition checks) ---
    executor_result = MagicMock()
    executor_result.data = {
        "id": executor_id,
        "wallet_address": "0x" + "A" * 40,
        "reputation_score": 100,
        "display_name": "Test Worker",
        "erc8004_agent_id": None,
    }
    executor_chain = MagicMock()
    executor_chain.select.return_value = executor_chain
    executor_chain.eq.return_value = executor_chain
    executor_chain.single.return_value = executor_chain
    executor_chain.execute.return_value = executor_result

    # --- Set up escrow chain (no records) ---
    escrow_result = MagicMock()
    escrow_result.data = []
    escrow_chain = MagicMock()
    escrow_chain.select.return_value = escrow_chain
    escrow_chain.eq.return_value = escrow_chain
    escrow_chain.limit.return_value = escrow_chain
    escrow_chain.execute.return_value = escrow_result

    # --- Wire up table router ---
    _mock_table_router(
        mock_client,
        {"executors": executor_chain, "escrows": escrow_chain},
    )

    with (
        patch("supabase_client.get_client", return_value=mock_client),
        patch("supabase_client.get_task", new_callable=AsyncMock, return_value=task),
    ):
        from supabase_client import assign_task

        with pytest.raises(Exception, match="no escrow record found"):
            await assign_task(
                task_id=task_id,
                agent_id=agent_id,
                executor_id=executor_id,
            )


# =============================================================================
# Test 5: submit_work skips escrow validation entirely in fase1
# =============================================================================


@pytest.mark.asyncio
async def test_submit_work_skips_validation_in_fase1(monkeypatch):
    """
    In fase1 mode (default), submit_work() must NOT check escrow at all.
    A task with no escrow record should succeed.
    """
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase1")

    task = _make_task(status="accepted")
    task_id = task["id"]

    mock_client = MagicMock()

    # --- Set up submissions insert chain ---
    sub_id = str(uuid.uuid4())
    insert_result = MagicMock()
    insert_result.data = [
        {
            "id": sub_id,
            "task_id": task_id,
            "executor_id": task["executor_id"],
            "evidence": {"text_response": "test answer"},
            "agent_verdict": "pending",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    insert_chain = MagicMock()
    insert_chain.execute.return_value = insert_result
    submissions_chain = MagicMock()
    submissions_chain.insert.return_value = insert_chain

    # Wire up: only submissions table needed (escrows should NOT be queried)
    _mock_table_router(mock_client, {"submissions": submissions_chain})

    with (
        patch("supabase_client.get_client", return_value=mock_client),
        patch("supabase_client.get_task", new_callable=AsyncMock, return_value=task),
        patch("supabase_client.update_task", new_callable=AsyncMock, return_value=task),
    ):
        from supabase_client import submit_work

        result = await submit_work(
            task_id=task_id,
            executor_id=task["executor_id"],
            evidence={"text_response": "test answer"},
        )

        # Should succeed — escrow check skipped entirely
        assert result is not None
        assert "submission" in result
        assert result["submission"]["id"] == sub_id

        # Verify escrows table was never queried
        for call in mock_client.table.call_args_list:
            assert call[0][0] != "escrows", (
                "Escrows table should NOT be queried in fase1 mode"
            )
