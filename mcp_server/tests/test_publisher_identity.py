"""
Phase 1 — human-publisher ERC-8004 identity (gasless, idempotent).

ensure_publisher_identity() mirrors the worker WS-1 registration rail: check
on-chain, mint gaslessly via the Facilitator only when absent, never double-mint.
"""

import pytest

pytestmark = pytest.mark.erc8004

from unittest.mock import patch, AsyncMock

from integrations.erc8004.identity import (
    ensure_publisher_identity,
    WorkerIdentityResult,
    WorkerIdentityStatus,
)

WALLET = "0xAbC0000000000000000000000000000000000001"


@pytest.mark.asyncio
async def test_registers_when_absent():
    """NOT_REGISTERED -> gasless mint -> returns the new agent_id."""
    not_reg = WorkerIdentityResult(
        status=WorkerIdentityStatus.NOT_REGISTERED,
        wallet_address=WALLET.lower(),
        network="base",
    )
    minted = WorkerIdentityResult(
        status=WorkerIdentityStatus.REGISTERED,
        agent_id=4242,
        wallet_address=WALLET.lower(),
        network="base",
    )
    with (
        patch(
            "integrations.erc8004.identity.check_worker_identity",
            new_callable=AsyncMock,
            return_value=not_reg,
        ),
        patch(
            "integrations.erc8004.identity.register_worker_gasless",
            new_callable=AsyncMock,
            return_value=minted,
        ) as reg,
    ):
        result = await ensure_publisher_identity(WALLET, network="base")

    assert result.status == WorkerIdentityStatus.REGISTERED
    assert result.agent_id == 4242
    reg.assert_awaited_once()
    # Publishers get the /publishers/ URI namespace, not /workers/.
    assert "/publishers/" in reg.call_args.kwargs["agent_uri"]


@pytest.mark.asyncio
async def test_idempotent_when_already_registered():
    """REGISTERED -> return as-is, NEVER a second mint."""
    already = WorkerIdentityResult(
        status=WorkerIdentityStatus.REGISTERED,
        agent_id=99,
        wallet_address=WALLET.lower(),
        network="base",
    )
    with (
        patch(
            "integrations.erc8004.identity.check_worker_identity",
            new_callable=AsyncMock,
            return_value=already,
        ),
        patch(
            "integrations.erc8004.identity.register_worker_gasless",
            new_callable=AsyncMock,
        ) as reg,
    ):
        result = await ensure_publisher_identity(WALLET, network="base")

    assert result.agent_id == 99
    reg.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_mint_on_check_error():
    """An on-chain check error must NOT trigger a mint (double-register risk)."""
    errored = WorkerIdentityResult(
        status=WorkerIdentityStatus.ERROR,
        wallet_address=WALLET.lower(),
        network="base",
        error="rpc down",
    )
    with (
        patch(
            "integrations.erc8004.identity.check_worker_identity",
            new_callable=AsyncMock,
            return_value=errored,
        ),
        patch(
            "integrations.erc8004.identity.register_worker_gasless",
            new_callable=AsyncMock,
        ) as reg,
    ):
        result = await ensure_publisher_identity(WALLET, network="base")

    assert result.status == WorkerIdentityStatus.ERROR
    reg.assert_not_awaited()
