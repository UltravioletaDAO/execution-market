"""Tests for the audit grid API endpoint."""

import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_deps():
    """Mock dependencies for audit grid API."""
    mock_client = MagicMock()

    # Mock tasks query
    mock_query = MagicMock()
    mock_query.eq = MagicMock(return_value=mock_query)
    mock_query.order = MagicMock(return_value=mock_query)
    mock_query.range = MagicMock(return_value=mock_query)
    mock_query.execute = MagicMock(
        return_value=MagicMock(
            data=[
                {
                    "id": "task-001",
                    "title": "Test Task",
                    "status": "completed",
                    "agent_id": "0xAgent",
                    "bounty_usd": 0.10,
                    "created_at": "2026-03-30T10:00:00Z",
                    "payment_network": "base",
                    "payment_token": "USDC",
                    "skill_version": "4.1.0",
                    "erc8004_agent_id": "2106",
                    "executor_id": "exec-001",
                    "escrow_tx": "0xescrow123",
                }
            ],
            count=1,
        )
    )
    mock_client.table.return_value.select = MagicMock(return_value=mock_query)

    return mock_client


def test_compute_completion_pct_completed():
    """Test completion % for a fully completed task."""
    from api.routers.audit_grid import _compute_completion_pct

    checkpoint = {
        "auth_erc8128": True,
        "identity_erc8004": True,
        "balance_sufficient": True,
        "payment_auth_signed": True,
        "task_created": True,
        "escrow_locked": True,
        "worker_assigned": True,
        "evidence_submitted": True,
        "ai_verified": True,
        "approved": True,
        "payment_released": True,
        "agent_rated_worker": True,
        "worker_rated_agent": True,
        "fees_distributed": True,
    }
    pct = _compute_completion_pct(checkpoint, "completed")
    assert pct == 100


def test_compute_completion_pct_partial():
    """Test completion % for a partially completed task."""
    from api.routers.audit_grid import _compute_completion_pct

    checkpoint = {
        "auth_erc8128": True,
        "identity_erc8004": True,
        "balance_sufficient": True,
        "payment_auth_signed": True,
        "task_created": True,
        "escrow_locked": True,
        "worker_assigned": True,
        "evidence_submitted": False,
        "ai_verified": False,
        "approved": False,
        "payment_released": False,
        "agent_rated_worker": False,
        "worker_rated_agent": False,
        "fees_distributed": False,
    }
    pct = _compute_completion_pct(checkpoint, "completed")
    assert pct == 50  # 7/14 = 50%


def test_compute_completion_pct_cancelled():
    """Test completion % for a cancelled task."""
    from api.routers.audit_grid import _compute_completion_pct

    checkpoint = {"task_created": True, "cancelled": True}
    pct = _compute_completion_pct(checkpoint, "cancelled")
    assert pct == 100  # 2/2 expected for cancelled


def test_compute_completion_pct_expired():
    """Test completion % for an expired task."""
    from api.routers.audit_grid import _compute_completion_pct

    checkpoint = {"task_created": True, "expired": True}
    pct = _compute_completion_pct(checkpoint, "expired")
    assert pct == 100  # 2/2 expected for expired


def test_build_checkpoint_response_empty():
    """Test building response with no checkpoint data."""
    from api.routers.audit_grid import _build_checkpoint_response

    result = _build_checkpoint_response(None)
    assert "auth" in result
    assert result["auth"]["done"] == 0
    assert result["auth"]["total"] == 2
    assert "payment" in result
    assert "execution" in result
    assert "reputation" in result


def test_build_checkpoint_response_full():
    """Test building response with full checkpoint data."""
    from api.routers.audit_grid import _build_checkpoint_response

    checkpoint = {
        "auth_erc8128": True,
        "auth_erc8128_at": "2026-03-30T10:00:00Z",
        "identity_erc8004": True,
        "identity_erc8004_at": "2026-03-30T10:00:01Z",
        "agent_id_resolved": "2106",
        "balance_sufficient": True,
        "balance_checked_at": "2026-03-30T10:00:02Z",
        "balance_amount_usdc": 5.23,
        "payment_auth_signed": False,
        "escrow_locked": True,
        "escrow_tx": "0xabc",
        "escrow_locked_at": "2026-03-30T10:05:00Z",
        "payment_released": True,
        "payment_released_at": "2026-03-30T10:15:00Z",
        "payment_tx": "0xpay",
        "worker_amount_usdc": 0.087,
        "fee_amount_usdc": 0.013,
        "task_created": True,
        "worker_assigned": True,
        "worker_id": "worker-001",
        "evidence_submitted": True,
        "evidence_count": 2,
        "ai_verified": True,
        "ai_verdict": "approved",
        "approved": True,
        "agent_rated_worker": True,
        "worker_rated_agent": False,
        "cancelled": False,
        "refunded": False,
        "expired": False,
        "fees_distributed": True,
    }

    result = _build_checkpoint_response(checkpoint)

    # Auth group
    assert result["auth"]["done"] == 2
    assert result["auth"]["total"] == 2
    assert result["auth"]["items"]["identity_erc8004"]["agent_id"] == "2106"

    # Payment group
    assert (
        result["payment"]["done"] == 3
    )  # balance + escrow + released (not auth_signed)
    assert result["payment"]["items"]["escrow_locked"]["tx"] == "0xabc"
    assert result["payment"]["items"]["payment_released"]["worker_amount"] == 0.087

    # Execution group
    assert result["execution"]["done"] == 5
    assert result["execution"]["items"]["evidence_submitted"]["count"] == 2
    assert result["execution"]["items"]["ai_verified"]["verdict"] == "approved"

    # Reputation group
    assert result["reputation"]["done"] == 1
    assert result["reputation"]["total"] == 2

    # Terminal states
    assert result["fees_distributed"]["done"] is True
    assert result["cancelled"]["done"] is False
