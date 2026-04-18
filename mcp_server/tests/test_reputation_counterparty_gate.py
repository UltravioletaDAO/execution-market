"""
Integration tests for the counterparty-proof gate on reputation endpoints
(SAAS hardening Task 5.2 — verification layer).

These exercise the full request path through ``rate_worker_endpoint`` and
``rate_agent_endpoint``. The unit coverage of
``verify_counterparty_proof`` lives in ``test_counterparty_proof.py``;
here we only care about how the endpoint translates its result into HTTP
semantics under both states of ``EM_REQUIRE_COUNTERPARTY_PROOF``.

Strategy
--------
We monkeypatch ``reputation.counterparty_proof_required`` and
``reputation.verify_counterparty_proof`` because
``_verify_counterparty_proof_or_raise`` looks them up through the module
globals. The DB helpers and ``rate_worker`` / ``rate_agent`` are stubbed
with ``AsyncMock`` so nothing reaches a real facilitator or Supabase.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from ..api import reputation

# Pull the exception classes through ``reputation`` rather than importing
# them directly from the package — reputation.py imports them via the
# ``integrations.reputation.counterparty_proof`` path (sys.path rooted at
# mcp_server/), and a second import under the ``mcp_server.`` prefix
# would load a sibling module with distinct class identities, breaking
# ``except ProofMismatch`` matching inside the endpoint.
ProofMismatch = reputation.ProofMismatch
ProofUnverifiable = reputation.ProofUnverifiable

pytestmark = pytest.mark.erc8004


TASK_ID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
AGENT_WALLET = "0x00000000000000000000000000000000000000aa"
WORKER_WALLET = "0x00000000000000000000000000000000000000bb"
VALID_PROOF = "0x" + "a" * 64


def _mock_request():
    mock = MagicMock()
    mock.url.path = "/test"
    return mock


# =============================================================================
# rate_worker_endpoint — agent rates worker
# =============================================================================


def _install_worker_task(monkeypatch):
    """Stub DB + ERC-8004 flag for rate_worker_endpoint happy path."""
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
                "executor": {"wallet_address": WORKER_WALLET},
                "payment_network": "base",
            }
        ),
    )


def _install_worker_rate_mock(monkeypatch):
    rate_worker_mock = AsyncMock(
        return_value=SimpleNamespace(
            success=True,
            transaction_hash="0xrate",
            feedback_index=1,
            network="base",
            error=None,
        )
    )
    monkeypatch.setattr(reputation, "rate_worker", rate_worker_mock, raising=False)
    return rate_worker_mock


@pytest.mark.asyncio
async def test_rate_worker_missing_proof_when_flag_on_returns_400(monkeypatch):
    _install_worker_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: True)
    verify_mock = MagicMock()
    monkeypatch.setattr(reputation, "verify_counterparty_proof", verify_mock)
    rate_mock = _install_worker_rate_mock(monkeypatch)

    request = reputation.WorkerFeedbackRequest(
        task_id=TASK_ID,
        score=80,
        comment="good",
        worker_address=None,
        proof_tx=None,
    )
    auth = SimpleNamespace(agent_id="agent_owner", wallet_address=AGENT_WALLET)

    with pytest.raises(HTTPException) as exc:
        await reputation.rate_worker_endpoint(request=request, auth=auth)

    assert exc.value.status_code == 400
    assert "proof_tx" in exc.value.detail
    verify_mock.assert_not_called()
    assert rate_mock.await_count == 0


@pytest.mark.asyncio
async def test_rate_worker_proof_mismatch_when_flag_on_returns_403(monkeypatch):
    _install_worker_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: True)

    def _raise_mismatch(**_kwargs):
        raise ProofMismatch("wrong counterparty")

    monkeypatch.setattr(reputation, "verify_counterparty_proof", _raise_mismatch)
    rate_mock = _install_worker_rate_mock(monkeypatch)

    request = reputation.WorkerFeedbackRequest(
        task_id=TASK_ID,
        score=80,
        comment="good",
        worker_address=None,
        proof_tx=VALID_PROOF,
    )
    auth = SimpleNamespace(agent_id="agent_owner", wallet_address=AGENT_WALLET)

    with pytest.raises(HTTPException) as exc:
        await reputation.rate_worker_endpoint(request=request, auth=auth)

    assert exc.value.status_code == 403
    assert rate_mock.await_count == 0


@pytest.mark.asyncio
async def test_rate_worker_proof_unverifiable_when_flag_on_returns_503(monkeypatch):
    _install_worker_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: True)

    def _raise_unverifiable(**_kwargs):
        raise ProofUnverifiable("rpc down")

    monkeypatch.setattr(reputation, "verify_counterparty_proof", _raise_unverifiable)
    rate_mock = _install_worker_rate_mock(monkeypatch)

    request = reputation.WorkerFeedbackRequest(
        task_id=TASK_ID,
        score=80,
        comment="good",
        worker_address=None,
        proof_tx=VALID_PROOF,
    )
    auth = SimpleNamespace(agent_id="agent_owner", wallet_address=AGENT_WALLET)

    with pytest.raises(HTTPException) as exc:
        await reputation.rate_worker_endpoint(request=request, auth=auth)

    assert exc.value.status_code == 503
    assert rate_mock.await_count == 0


@pytest.mark.asyncio
async def test_rate_worker_valid_proof_when_flag_on_succeeds(monkeypatch):
    _install_worker_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: True)
    verify_mock = MagicMock(
        return_value={
            "tx_hash": VALID_PROOF,
            "block_number": 100,
            "amount_raw": 100_000,
            "match": "direct",
        }
    )
    monkeypatch.setattr(reputation, "verify_counterparty_proof", verify_mock)
    rate_mock = _install_worker_rate_mock(monkeypatch)

    request = reputation.WorkerFeedbackRequest(
        task_id=TASK_ID,
        score=80,
        comment="good",
        worker_address=None,
        proof_tx=VALID_PROOF,
    )
    auth = SimpleNamespace(agent_id="agent_owner", wallet_address=AGENT_WALLET)

    result = await reputation.rate_worker_endpoint(request=request, auth=auth)

    assert result.success is True
    verify_mock.assert_called_once()
    kwargs = verify_mock.call_args.kwargs
    assert kwargs["rater_wallet"] == AGENT_WALLET
    assert kwargs["ratee_wallet"] == WORKER_WALLET
    assert kwargs["network"] == "base"
    assert rate_mock.await_count == 1


@pytest.mark.asyncio
async def test_rate_worker_flag_off_missing_proof_passes_through(monkeypatch):
    _install_worker_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: False)
    verify_mock = MagicMock()
    monkeypatch.setattr(reputation, "verify_counterparty_proof", verify_mock)
    rate_mock = _install_worker_rate_mock(monkeypatch)

    request = reputation.WorkerFeedbackRequest(
        task_id=TASK_ID,
        score=80,
        comment="good",
        worker_address=None,
        proof_tx=None,
    )
    auth = SimpleNamespace(agent_id="agent_owner", wallet_address=AGENT_WALLET)

    result = await reputation.rate_worker_endpoint(request=request, auth=auth)

    assert result.success is True
    # No proof supplied + flag off -> verification helper never invoked
    verify_mock.assert_not_called()
    assert rate_mock.await_count == 1


@pytest.mark.asyncio
async def test_rate_worker_flag_off_mismatch_logs_and_proceeds(monkeypatch, caplog):
    """A bogus proof with the flag off must log the mismatch but not block."""
    _install_worker_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: False)

    def _raise_mismatch(**_kwargs):
        raise ProofMismatch("wrong counterparty")

    monkeypatch.setattr(reputation, "verify_counterparty_proof", _raise_mismatch)
    rate_mock = _install_worker_rate_mock(monkeypatch)

    request = reputation.WorkerFeedbackRequest(
        task_id=TASK_ID,
        score=80,
        comment="good",
        worker_address=None,
        proof_tx=VALID_PROOF,
    )
    auth = SimpleNamespace(agent_id="agent_owner", wallet_address=AGENT_WALLET)

    with caplog.at_level("WARNING", logger=reputation.logger.name):
        result = await reputation.rate_worker_endpoint(request=request, auth=auth)

    assert result.success is True
    assert rate_mock.await_count == 1
    assert any("rating.proof_mismatch" in record.message for record in caplog.records)


# =============================================================================
# rate_agent_endpoint — worker rates agent
# =============================================================================


def _install_agent_task(monkeypatch):
    """Stub DB + get_agent_info for rate_agent_endpoint happy path."""
    monkeypatch.setattr(reputation, "ERC8004_AVAILABLE", True)
    monkeypatch.setattr(
        reputation.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": TASK_ID,
                "agent_id": "0xplatform",
                "erc8004_agent_id": "10",
                "status": "completed",
                "executor_id": "exec_1",
                "executor": {"wallet_address": WORKER_WALLET},
                "payment_network": "base",
            }
        ),
    )
    monkeypatch.setattr(
        reputation,
        "get_agent_info",
        AsyncMock(
            return_value=SimpleNamespace(
                owner=AGENT_WALLET,
                agent_wallet=AGENT_WALLET,
            )
        ),
        raising=False,
    )


def _install_agent_rate_mock(monkeypatch):
    rate_agent_mock = AsyncMock(
        return_value=SimpleNamespace(
            success=True,
            transaction_hash="0xabc",
            feedback_index=7,
            network="base",
            error=None,
        )
    )
    monkeypatch.setattr(reputation, "rate_agent", rate_agent_mock, raising=False)
    return rate_agent_mock


@pytest.mark.asyncio
async def test_rate_agent_missing_proof_when_flag_on_returns_400(monkeypatch):
    _install_agent_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: True)
    verify_mock = MagicMock()
    monkeypatch.setattr(reputation, "verify_counterparty_proof", verify_mock)
    rate_mock = _install_agent_rate_mock(monkeypatch)

    request = reputation.AgentFeedbackRequest(
        agent_id=10,
        task_id=TASK_ID,
        score=85,
        comment="great",
        proof_tx=None,
    )

    with pytest.raises(HTTPException) as exc:
        await reputation.rate_agent_endpoint(
            raw_request=_mock_request(),
            request=request,
            worker_auth=None,
        )

    assert exc.value.status_code == 400
    verify_mock.assert_not_called()
    assert rate_mock.await_count == 0


@pytest.mark.asyncio
async def test_rate_agent_proof_mismatch_when_flag_on_returns_403(monkeypatch):
    _install_agent_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: True)

    def _raise_mismatch(**_kwargs):
        raise ProofMismatch("wrong counterparty")

    monkeypatch.setattr(reputation, "verify_counterparty_proof", _raise_mismatch)
    rate_mock = _install_agent_rate_mock(monkeypatch)

    request = reputation.AgentFeedbackRequest(
        agent_id=10,
        task_id=TASK_ID,
        score=85,
        comment="great",
        proof_tx=VALID_PROOF,
    )

    with pytest.raises(HTTPException) as exc:
        await reputation.rate_agent_endpoint(
            raw_request=_mock_request(),
            request=request,
            worker_auth=None,
        )

    assert exc.value.status_code == 403
    assert rate_mock.await_count == 0


@pytest.mark.asyncio
async def test_rate_agent_valid_proof_when_flag_on_succeeds(monkeypatch):
    _install_agent_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: True)
    verify_mock = MagicMock(
        return_value={
            "tx_hash": VALID_PROOF,
            "block_number": 100,
            "amount_raw": 87_000,
            "match": "intermediary",
        }
    )
    monkeypatch.setattr(reputation, "verify_counterparty_proof", verify_mock)
    rate_mock = _install_agent_rate_mock(monkeypatch)

    request = reputation.AgentFeedbackRequest(
        agent_id=10,
        task_id=TASK_ID,
        score=85,
        comment="great",
        proof_tx=VALID_PROOF,
    )

    result = await reputation.rate_agent_endpoint(
        raw_request=_mock_request(),
        request=request,
        worker_auth=None,
    )

    assert result.success is True
    verify_mock.assert_called_once()
    kwargs = verify_mock.call_args.kwargs
    assert kwargs["rater_wallet"] == WORKER_WALLET
    assert kwargs["ratee_wallet"] == AGENT_WALLET
    assert kwargs["network"] == "base"
    assert rate_mock.await_count == 1


@pytest.mark.asyncio
async def test_rate_agent_flag_off_missing_proof_passes_through(monkeypatch):
    _install_agent_task(monkeypatch)
    monkeypatch.setattr(reputation, "counterparty_proof_required", lambda: False)
    verify_mock = MagicMock()
    monkeypatch.setattr(reputation, "verify_counterparty_proof", verify_mock)
    rate_mock = _install_agent_rate_mock(monkeypatch)

    request = reputation.AgentFeedbackRequest(
        agent_id=10,
        task_id=TASK_ID,
        score=85,
        comment="great",
        proof_tx=None,
    )

    result = await reputation.rate_agent_endpoint(
        raw_request=_mock_request(),
        request=request,
        worker_auth=None,
    )

    assert result.success is True
    verify_mock.assert_not_called()
    assert rate_mock.await_count == 1
