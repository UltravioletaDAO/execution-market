"""
Focused tests for reputation endpoint ownership and assignment checks.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.erc8004
from fastapi import HTTPException

from ..api import reputation
from ..api import routes


def _mock_request():
    """Create a mock FastAPI Request object."""
    mock = MagicMock()
    mock.url.path = "/test"
    return mock


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
        await reputation.rate_worker_endpoint(request=request, auth=api_key)

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

    result = await reputation.rate_worker_endpoint(request=request, auth=api_key)

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
        await reputation.rate_agent_endpoint(
            raw_request=_mock_request(),
            request=request,
            worker_auth=None,
        )

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
        await reputation.rate_agent_endpoint(
            raw_request=_mock_request(),
            request=request,
            worker_auth=None,
        )

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

    result = await reputation.rate_agent_endpoint(
        raw_request=_mock_request(),
        request=request,
        worker_auth=None,
    )

    assert result.success is True
    assert rate_agent_mock.await_count == 1


# =============================================================================
# Rejection ownership and rate-limiting
# =============================================================================

REJECTION_SUBMISSION_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


@pytest.mark.asyncio
async def test_reject_submission_rejects_non_owner(monkeypatch):
    """Only the agent who owns the task can reject a submission."""
    monkeypatch.setattr(
        routes, "verify_agent_owns_submission", AsyncMock(return_value=False)
    )
    monkeypatch.setattr(
        routes.db,
        "get_submission",
        AsyncMock(return_value={"id": REJECTION_SUBMISSION_ID}),
    )

    api_key = SimpleNamespace(agent_id="wrong_agent")

    with pytest.raises(HTTPException) as exc:
        await routes.reject_submission(
            submission_id=REJECTION_SUBMISSION_ID,
            request=routes.RejectionRequest(
                notes="This work is unacceptable",
                severity="minor",
            ),
            auth=api_key,
        )

    assert exc.value.status_code == 403


class _FakeSideEffectsCountQuery:
    """Simulates the erc8004_side_effects table for rate-limit counting."""

    def __init__(self, rows, count=None):
        self._rows = rows
        self._count = count

    def select(self, *_args, **kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(
            data=self._rows,
            count=self._count if self._count is not None else len(self._rows),
        )


class _FakeRateLimitClient:
    """Fake Supabase client for rate-limit tests."""

    def __init__(self, agent_id: str, rejection_count: int):
        self._agent_id = agent_id
        self._rejection_count = rejection_count

    def table(self, name: str):
        if name == "erc8004_side_effects":
            rows = [
                {"payload": {"agent_id": self._agent_id}}
                for _ in range(self._rejection_count)
            ]
            return _FakeSideEffectsCountQuery(rows, count=self._rejection_count)
        raise AssertionError(f"Unexpected table access: {name}")


@pytest.mark.asyncio
async def test_major_rejection_rate_limit_returns_429(monkeypatch):
    """Invariant: >3 major rejections per agent per 24h returns 429.

    WS-3 policy: rate-limit major rejection on-chain writes to prevent abuse.
    """
    submission_id = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    agent_id = "agent_abuser"
    api_key = SimpleNamespace(agent_id=agent_id)

    # Agent owns the submission
    monkeypatch.setattr(
        routes, "verify_agent_owns_submission", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        routes.db,
        "get_submission",
        AsyncMock(
            return_value={
                "id": submission_id,
                "agent_verdict": "pending",
                "task": {"id": "task_rl_1"},
                "executor": {"wallet_address": "0xworker"},
            }
        ),
    )
    monkeypatch.setattr(routes.db, "update_submission", AsyncMock())

    # Fake PlatformConfig: rejection feedback enabled
    class FakePlatformConfig:
        @staticmethod
        async def is_feature_enabled(flag: str) -> bool:
            return flag == "erc8004_rejection_feedback"

    monkeypatch.setattr(
        "config.platform_config.PlatformConfig",
        FakePlatformConfig,
    )

    # Already 3 major rejections in the last 24h for this agent
    fake_client = _FakeRateLimitClient(agent_id=agent_id, rejection_count=3)
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)

    with pytest.raises(HTTPException) as exc:
        await routes.reject_submission(
            submission_id=submission_id,
            request=routes.RejectionRequest(
                notes="This is terrible work, completely wrong location",
                severity="major",
                reputation_score=20,
            ),
            auth=api_key,
        )

    assert exc.value.status_code == 429
    assert "max 3" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_minor_rejection_does_not_create_on_chain_side_effect(monkeypatch):
    """Minor rejection must NOT create any on-chain side effect row.

    WS-3 policy: minor = local rejection only, no on-chain write.
    """
    submission_id = "dddddddd-dddd-dddd-dddd-dddddddddddd"
    api_key = SimpleNamespace(agent_id="agent_test")

    monkeypatch.setattr(
        routes, "verify_agent_owns_submission", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        routes.db,
        "get_submission",
        AsyncMock(
            return_value={
                "id": submission_id,
                "agent_verdict": "pending",
                "task": {"id": "task_minor_1"},
                "executor": {"wallet_address": "0xworker"},
            }
        ),
    )
    update_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "update_submission", update_mock)

    result = await routes.reject_submission(
        submission_id=submission_id,
        request=routes.RejectionRequest(
            notes="Photo slightly blurry, please retake",
            severity="minor",
        ),
        auth=api_key,
    )

    assert result.data["verdict"] == "rejected"
    # No severity key for minor rejections
    assert "severity" not in result.data
    # No side_effect_id for minor rejections
    assert "side_effect_id" not in result.data
    update_mock.assert_awaited_once()
