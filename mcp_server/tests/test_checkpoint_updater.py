"""Tests for audit/checkpoint_updater.py — lifecycle checkpoint tracking."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_supabase():
    """Mock supabase_client for checkpoint tests."""
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_upsert = MagicMock()
    mock_upsert.execute = MagicMock(
        return_value=MagicMock(data=[{"task_id": "test-task"}])
    )
    mock_table.upsert = MagicMock(return_value=mock_upsert)
    mock_client.table = MagicMock(return_value=mock_table)

    with patch.dict("sys.modules", {"supabase_client": MagicMock()}):
        import sys

        sys.modules["supabase_client"].get_client = MagicMock(return_value=mock_client)
        yield mock_client, mock_table


@pytest.mark.asyncio
async def test_init_checkpoint(mock_supabase):
    """Test that init_checkpoint creates a checkpoint row."""
    from audit.checkpoint_updater import init_checkpoint

    result = await init_checkpoint(
        "task-123",
        skill_version="4.1.0",
        network="base",
        token="USDC",
        bounty_usdc=0.10,
    )
    assert result is True


@pytest.mark.asyncio
async def test_mark_auth_erc8128(mock_supabase):
    """Test marking ERC-8128 auth checkpoint."""
    from audit.checkpoint_updater import mark_auth_erc8128

    result = await mark_auth_erc8128("task-123")
    assert result is True
    _, mock_table = mock_supabase
    call_args = mock_table.upsert.call_args[0][0]
    assert call_args["auth_erc8128"] is True
    assert "auth_erc8128_at" in call_args


@pytest.mark.asyncio
async def test_mark_identity_erc8004(mock_supabase):
    """Test marking ERC-8004 identity checkpoint with agent ID."""
    from audit.checkpoint_updater import mark_identity_erc8004

    result = await mark_identity_erc8004("task-123", agent_id="2106")
    assert result is True
    _, mock_table = mock_supabase
    call_args = mock_table.upsert.call_args[0][0]
    assert call_args["identity_erc8004"] is True
    assert call_args["agent_id_resolved"] == "2106"


@pytest.mark.asyncio
async def test_mark_balance_checked(mock_supabase):
    """Test marking balance check with amount."""
    from audit.checkpoint_updater import mark_balance_checked

    result = await mark_balance_checked("task-123", amount_usdc=5.23)
    assert result is True
    _, mock_table = mock_supabase
    call_args = mock_table.upsert.call_args[0][0]
    assert call_args["balance_sufficient"] is True
    assert call_args["balance_amount_usdc"] == 5.23


@pytest.mark.asyncio
async def test_mark_payment_released(mock_supabase):
    """Test marking payment release with tx and amounts."""
    from audit.checkpoint_updater import mark_payment_released

    result = await mark_payment_released(
        "task-123",
        tx_hash="0xabc123",
        worker_amount=0.087,
        fee_amount=0.013,
    )
    assert result is True
    _, mock_table = mock_supabase
    call_args = mock_table.upsert.call_args[0][0]
    assert call_args["payment_released"] is True
    assert call_args["payment_tx"] == "0xabc123"
    assert call_args["worker_amount_usdc"] == 0.087
    assert call_args["fee_amount_usdc"] == 0.013


@pytest.mark.asyncio
async def test_mark_reputation_agent_to_worker(mock_supabase):
    """Test marking agent→worker reputation."""
    from audit.checkpoint_updater import mark_reputation

    result = await mark_reputation("task-123", "agent_to_worker")
    assert result is True
    _, mock_table = mock_supabase
    call_args = mock_table.upsert.call_args[0][0]
    assert call_args["agent_rated_worker"] is True


@pytest.mark.asyncio
async def test_mark_reputation_worker_to_agent(mock_supabase):
    """Test marking worker→agent reputation."""
    from audit.checkpoint_updater import mark_reputation

    result = await mark_reputation("task-123", "worker_to_agent")
    assert result is True
    _, mock_table = mock_supabase
    call_args = mock_table.upsert.call_args[0][0]
    assert call_args["worker_rated_agent"] is True


@pytest.mark.asyncio
async def test_mark_reputation_invalid_direction(mock_supabase):
    """Test that invalid direction returns False."""
    from audit.checkpoint_updater import mark_reputation

    result = await mark_reputation("task-123", "invalid")
    assert result is False


@pytest.mark.asyncio
async def test_mark_cancelled(mock_supabase):
    """Test marking task cancelled."""
    from audit.checkpoint_updater import mark_cancelled

    result = await mark_cancelled("task-123")
    assert result is True
    _, mock_table = mock_supabase
    call_args = mock_table.upsert.call_args[0][0]
    assert call_args["cancelled"] is True


@pytest.mark.asyncio
async def test_mark_refunded_with_tx(mock_supabase):
    """Test marking refund with tx hash."""
    from audit.checkpoint_updater import mark_refunded

    result = await mark_refunded("task-123", tx_hash="0xrefund456")
    assert result is True
    _, mock_table = mock_supabase
    call_args = mock_table.upsert.call_args[0][0]
    assert call_args["refunded"] is True
    assert call_args["refund_tx"] == "0xrefund456"


@pytest.mark.asyncio
async def test_mark_expired(mock_supabase):
    """Test marking task expired."""
    from audit.checkpoint_updater import mark_expired

    result = await mark_expired("task-123")
    assert result is True
    _, mock_table = mock_supabase
    call_args = mock_table.upsert.call_args[0][0]
    assert call_args["expired"] is True


@pytest.mark.asyncio
async def test_non_blocking_on_db_error():
    """Test that checkpoint updates don't raise on DB errors."""
    with patch.dict("sys.modules", {"supabase_client": MagicMock()}):
        import sys

        mock_client = MagicMock()
        mock_client.table.return_value.upsert.side_effect = Exception("DB down")
        sys.modules["supabase_client"].get_client = MagicMock(return_value=mock_client)

        from audit.checkpoint_updater import mark_cancelled

        # Should NOT raise
        result = await mark_cancelled("task-123")
        assert result is False


@pytest.mark.asyncio
async def test_get_checkpoint(mock_supabase):
    """Test getting a checkpoint."""
    mock_client, _ = mock_supabase
    mock_select = MagicMock()
    mock_eq = MagicMock()
    mock_eq.execute = MagicMock(
        return_value=MagicMock(data=[{"task_id": "task-123", "task_created": True}])
    )
    mock_select.eq = MagicMock(return_value=mock_eq)
    mock_client.table.return_value.select = MagicMock(return_value=mock_select)

    from audit.checkpoint_updater import get_checkpoint

    result = await get_checkpoint("task-123")
    assert result is not None
    assert result["task_created"] is True
