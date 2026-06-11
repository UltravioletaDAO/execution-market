"""publisher_type='robot' recording on A2A task creation (Task 5.1).

``tasks.publisher_type`` defaults to 'agent' (migration 034). When the
authenticated publisher wallet is registered as a robot executor
(``executors.executor_type='robot'``, persisted by em_register_as_executor),
``create_task`` must record publisher_type='robot'. The lookup is
failure-tolerant: no row / non-robot row / lookup exception all keep today's
default and never block publish.

See MASTER_PLAN_UNIVERSAL_ESCROW_CONSISTENCY.md (Phase 5) and
ESCROW_CONSISTENCY_AUDIT_2026-06-11 (EC-10).
"""

import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.core

from api.routers import tasks as tasks_router
from api.routers._models import CreateTaskRequest
from models import EvidenceType, TargetExecutorType, TaskCategory

ROBOT_WALLET = "0x" + "ab" * 20
TASK_ID = "task-robot-pub-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_http_request(headers=None):
    mock = MagicMock()
    mock.headers = headers or {}
    mock.url.path = "/api/v1/tasks"
    return mock


def _auth(agent_id=ROBOT_WALLET):
    return SimpleNamespace(
        agent_id=agent_id,
        wallet_address=agent_id,
        auth_method="erc8128",
        erc8004_registered=True,
    )


def _request():
    return CreateTaskRequest(
        title="Robot publisher recording task",
        instructions=(
            "Take a screenshot of the dashboard landing page and submit it "
            "as evidence. Smoke test for publisher_type recording."
        ),
        category=TaskCategory.SIMPLE_ACTION,
        bounty_usd=0.10,
        deadline_hours=2,
        evidence_required=[EvidenceType.SCREENSHOT],
        payment_token="USDC",
        payment_network="base",
        target_executor=TargetExecutorType.ANY,
    )


class _FakeExecutorsClient:
    """Minimal chainable Supabase client stub.

    Returns ``rows`` from every ``execute()`` and records the filters that
    were applied, so the test can assert the robot lookup shape
    (executor_type='robot' + the publisher wallet).
    """

    def __init__(self, rows):
        self.rows = rows
        self.filters = []
        self.tables = []

    def table(self, name):
        self.tables.append(name)
        return self

    def select(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def ilike(self, column, value):
        self.filters.append(("ilike", column, value))
        return self

    def limit(self, n):
        return self

    def execute(self):
        return SimpleNamespace(data=list(self.rows))


def _stub_prelude(monkeypatch, executors_rows=None, get_client_raises=False):
    """Patch out the heavy pre-flight work so create_task() reaches the
    insert + robot-recording block (same recipe as test_task_geo_matching).

    Returns (create_mock, update_mock, fake_client).
    """
    monkeypatch.setenv("EM_MOONPAY_ENABLED", "false")
    monkeypatch.setattr(
        tasks_router.db,
        "get_task_by_idempotency_key",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        tasks_router, "get_platform_fee_percent", AsyncMock(return_value=0)
    )
    monkeypatch.setattr(
        tasks_router, "get_min_bounty", AsyncMock(return_value=Decimal("0.01"))
    )
    monkeypatch.setattr(
        tasks_router, "get_max_bounty", AsyncMock(return_value=Decimal("10000"))
    )
    monkeypatch.setattr(tasks_router, "X402_AVAILABLE", True)

    payment_stub = SimpleNamespace(
        success=True,
        payer_address=ROBOT_WALLET,
        amount_usd=Decimal("0.10"),
        network="base",
        timestamp=datetime.now(timezone.utc),
        task_id="pending",
        tx_hash=None,
        error=None,
    )
    monkeypatch.setattr(
        tasks_router, "verify_x402_payment", AsyncMock(return_value=payment_stub)
    )
    # No dispatcher -> all escrow branches are skipped.
    monkeypatch.setattr(tasks_router, "get_payment_dispatcher", lambda: None)
    monkeypatch.setattr(tasks_router, "ERC8004_IDENTITY_AVAILABLE", False)

    created_task = {
        "id": TASK_ID,
        "title": "Robot publisher recording task",
        "status": "published",
        "category": "simple_action",
        "bounty_usd": 0.10,
        "deadline": "2026-07-01T00:00:00+00:00",
        "created_at": "2026-06-11T12:00:00+00:00",
        "agent_id": ROBOT_WALLET,
        "instructions": "...",
        "evidence_schema": {"required": ["screenshot"], "optional": []},
        "location_hint": None,
        "min_reputation": 0,
        "erc8004_agent_id": None,
        "payment_network": "base",
        "payment_token": "USDC",
        "escrow_tx": None,
        "refund_tx": None,
        "target_executor_type": "any",
        "metadata": None,
        "required_capabilities": None,
        "skill_version": None,
        "geo_match_mode": None,
        "location_radius_m": None,
    }
    create_mock = AsyncMock(return_value=dict(created_task))
    monkeypatch.setattr(tasks_router.db, "create_task", create_mock)
    update_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(tasks_router.db, "update_task", update_mock)

    if get_client_raises:
        fake_client = None
        monkeypatch.setattr(
            tasks_router.db,
            "get_client",
            MagicMock(side_effect=RuntimeError("executors lookup unavailable")),
        )
    else:
        fake_client = _FakeExecutorsClient(executors_rows or [])
        monkeypatch.setattr(tasks_router.db, "get_client", lambda: fake_client)
    return create_mock, update_mock, fake_client


def _publisher_type_updates(update_mock):
    """All update_task payloads that touch publisher_type."""
    return [
        call.args[1]
        for call in update_mock.await_args_list
        if "publisher_type" in call.args[1]
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_robot_wallet_records_publisher_type_robot(monkeypatch):
    """Wallet registered with executor_type='robot' -> publisher_type='robot'
    is persisted on the created task."""
    create_mock, update_mock, fake_client = _stub_prelude(
        monkeypatch, executors_rows=[{"id": "robot-exec-1"}]
    )

    result = await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=_request(),
        auth=_auth(),
    )

    assert result is not None
    create_mock.assert_awaited_once()
    # The persisted payload carries the robot publisher_type.
    robot_updates = _publisher_type_updates(update_mock)
    assert robot_updates == [{"publisher_type": "robot"}]
    robot_call = [
        call for call in update_mock.await_args_list if "publisher_type" in call.args[1]
    ][0]
    assert robot_call.args[0] == TASK_ID
    # The lookup queried executors by robot type + the publisher wallet.
    assert "executors" in fake_client.tables
    assert ("eq", "executor_type", "robot") in fake_client.filters
    assert ("ilike", "wallet_address", ROBOT_WALLET) in fake_client.filters


@pytest.mark.asyncio
async def test_agent_wallet_keeps_default_publisher_type(monkeypatch):
    """No robot executors row for the wallet -> publisher_type untouched
    (DB default 'agent' applies, exactly today's behavior)."""
    create_mock, update_mock, _ = _stub_prelude(monkeypatch, executors_rows=[])

    result = await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=_request(),
        auth=_auth(),
    )

    assert result is not None
    create_mock.assert_awaited_once()
    assert _publisher_type_updates(update_mock) == []


@pytest.mark.asyncio
async def test_lookup_exception_never_blocks_publish(monkeypatch):
    """Executors lookup raising -> publish still succeeds (201 path) and
    publisher_type stays untouched."""
    create_mock, update_mock, _ = _stub_prelude(monkeypatch, get_client_raises=True)

    result = await tasks_router.create_task(
        http_request=_mock_http_request(),
        request=_request(),
        auth=_auth(),
    )

    assert result is not None
    assert result.id == TASK_ID
    create_mock.assert_awaited_once()
    assert _publisher_type_updates(update_mock) == []
