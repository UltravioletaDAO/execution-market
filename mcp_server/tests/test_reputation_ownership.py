"""
Focused tests for reputation endpoint ownership and assignment checks.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from ..api import reputation


TASK_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


@pytest.mark.asyncio
async def test_rate_worker_rejects_non_owner_agent(monkeypatch):
    monkeypatch.setattr(reputation, "ERC8004_AVAILABLE", True)
    monkeypatch.setattr(
        reputation.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": TASK_ID,
                "agent_id": "agent_owner",
                "status": "submitted",
                "executor": {"wallet_address": "0xworker"},
            }
        ),
    )

    request = reputation.WorkerFeedbackRequest(
        task_id=TASK_ID,
        score=80,
        comment="good",
        worker_address=None,
        proof_tx=None,
    )
    api_key = SimpleNamespace(agent_id="another_agent")

    with pytest.raises(HTTPException) as exc:
        await reputation.rate_worker_endpoint(request=request, api_key=api_key)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_rate_worker_uses_assigned_executor_wallet(monkeypatch):
    monkeypatch.setattr(reputation, "ERC8004_AVAILABLE", True)
    monkeypatch.setattr(
        reputation.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": TASK_ID,
                "agent_id": "agent_owner",
                "status": "submitted",
                "executor_id": "exec_1",
                "executor": {"wallet_address": "0xworker"},
            }
        ),
    )

    rate_worker_mock = AsyncMock(
        return_value=SimpleNamespace(
            success=True,
            transaction_hash="0xrate",
            feedback_index=1,
            network="ethereum",
            error=None,
        )
    )
    monkeypatch.setattr(reputation, "rate_worker", rate_worker_mock, raising=False)

    request = reputation.WorkerFeedbackRequest(
        task_id=TASK_ID,
        score=90,
        comment="great",
        worker_address=None,
        proof_tx="0xproof",
    )
    api_key = SimpleNamespace(agent_id="agent_owner")

    result = await reputation.rate_worker_endpoint(request=request, api_key=api_key)

    assert result.success is True
    assert rate_worker_mock.await_count == 1
    kwargs = rate_worker_mock.await_args.kwargs
    assert kwargs["worker_address"] == "0xworker"


@pytest.mark.asyncio
async def test_rate_agent_rejects_task_without_assigned_worker(monkeypatch):
    monkeypatch.setattr(reputation, "ERC8004_AVAILABLE", True)
    monkeypatch.setattr(
        reputation.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": TASK_ID,
                "agent_id": "0xagent",
                "status": "completed",
                "executor_id": None,
                "executor": {},
            }
        ),
    )

    request = reputation.AgentFeedbackRequest(
        agent_id=10,
        task_id=TASK_ID,
        score=70,
        comment="ok",
        proof_tx=None,
    )

    with pytest.raises(HTTPException) as exc:
        await reputation.rate_agent_endpoint(request=request)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_rate_agent_rejects_mismatched_agent_identity(monkeypatch):
    monkeypatch.setattr(reputation, "ERC8004_AVAILABLE", True)
    monkeypatch.setattr(
        reputation.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": TASK_ID,
                "agent_id": "0xagentowner",
                "status": "completed",
                "executor_id": "exec_1",
                "executor": {"wallet_address": "0xworker"},
            }
        ),
    )
    monkeypatch.setattr(
        reputation,
        "get_agent_info",
        AsyncMock(return_value=SimpleNamespace(owner="0xanotherowner")),
        raising=False,
    )

    request = reputation.AgentFeedbackRequest(
        agent_id=10,
        task_id=TASK_ID,
        score=70,
        comment="ok",
        proof_tx=None,
    )

    with pytest.raises(HTTPException) as exc:
        await reputation.rate_agent_endpoint(request=request)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_rate_agent_succeeds_with_valid_task_context(monkeypatch):
    monkeypatch.setattr(reputation, "ERC8004_AVAILABLE", True)
    monkeypatch.setattr(
        reputation.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": TASK_ID,
                "agent_id": "0xagentowner",
                "status": "completed",
                "executor_id": "exec_1",
                "executor": {"wallet_address": "0xworker"},
            }
        ),
    )
    monkeypatch.setattr(
        reputation,
        "get_agent_info",
        AsyncMock(return_value=SimpleNamespace(owner="0xagentowner")),
        raising=False,
    )
    rate_agent_mock = AsyncMock(
        return_value=SimpleNamespace(
            success=True,
            transaction_hash="0xabc",
            feedback_index=7,
            network="ethereum",
            error=None,
        )
    )
    monkeypatch.setattr(reputation, "rate_agent", rate_agent_mock, raising=False)

    request = reputation.AgentFeedbackRequest(
        agent_id=10,
        task_id=TASK_ID,
        score=85,
        comment="great",
        proof_tx="0xproof",
    )

    result = await reputation.rate_agent_endpoint(request=request)

    assert result.success is True
    assert rate_agent_mock.await_count == 1
