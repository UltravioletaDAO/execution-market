"""
Focused P0 tests for approve/cancel idempotency and refund behavior.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from ..api import routes


class _FakeEscrowsTable:
    def __init__(self, status: str, escrow_id: str = "escrow_test"):
        self.status = status
        self.escrow_id = escrow_id
        self.last_update = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def single(self):
        return self

    def update(self, payload):
        self.last_update = payload
        return self

    def execute(self):
        return SimpleNamespace(
            data={"status": self.status, "escrow_id": self.escrow_id}
        )


class _FakePaymentsTable:
    def __init__(self):
        self.inserted_rows = []

    def insert(self, payload):
        self.inserted_rows.append(payload)
        return self

    def execute(self):
        return SimpleNamespace(data=self.inserted_rows[-1] if self.inserted_rows else None)


class _FakeClient:
    def __init__(self, escrow_status: str):
        self.escrows = _FakeEscrowsTable(status=escrow_status)
        self.payments = _FakePaymentsTable()

    def table(self, name: str):
        if name == "escrows":
            return self.escrows
        if name == "payments":
            return self.payments
        if name != "escrows":
            raise AssertionError(f"Unexpected table access: {name}")
        return self.escrows


class _HeaderEscrowTable:
    def __init__(self, metadata):
        self.metadata = metadata

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=[{"metadata": self.metadata}])


class _HeaderClient:
    def __init__(self, metadata):
        self._table = _HeaderEscrowTable(metadata)

    def table(self, name: str):
        if name != "escrows":
            raise AssertionError(f"Unexpected table access: {name}")
        return self._table


class _MetricsQuery:
    def __init__(self, rows=None, count=None):
        self._rows = rows or []
        self._count = count

    def select(self, *_args, **kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        resolved_count = self._count if isinstance(self._count, int) else None
        return SimpleNamespace(data=self._rows, count=resolved_count)


class _MetricsClient:
    def __init__(self, tasks_rows, escrow_rows, worker_count=0, agent_count=0):
        self._tasks_rows = tasks_rows
        self._escrow_rows = escrow_rows
        self._worker_count = worker_count
        self._agent_count = agent_count

    def table(self, name: str):
        if name == "tasks":
            return _MetricsQuery(rows=self._tasks_rows)
        if name == "escrows":
            return _MetricsQuery(rows=self._escrow_rows)
        if name == "executors":
            return _MetricsQuery(rows=[], count=self._worker_count)
        if name == "api_keys":
            return _MetricsQuery(rows=[], count=self._agent_count)
        raise AssertionError(f"Unexpected table access: {name}")


@pytest.mark.asyncio
async def test_approve_submission_returns_idempotent_success(monkeypatch):
    submission_id = "11111111-1111-1111-1111-111111111111"
    api_key = SimpleNamespace(agent_id="agent_test")

    monkeypatch.setattr(
        routes, "verify_agent_owns_submission", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        routes.db,
        "get_submission",
        AsyncMock(return_value={"agent_verdict": "accepted"}),
    )
    monkeypatch.setattr(
        routes,
        "_get_existing_submission_payment",
        lambda _submission_id: {"tx_hash": "0xalreadysettled"},
    )

    update_submission = AsyncMock()
    monkeypatch.setattr(routes.db, "update_submission", update_submission)

    result = await routes.approve_submission(
        submission_id=submission_id,
        request=None,
        api_key=api_key,
    )

    assert result.data["idempotent"] is True
    assert result.data["payment_tx"] == "0xalreadysettled"
    update_submission.assert_not_called()


@pytest.mark.asyncio
async def test_approve_submission_rejects_when_task_is_cancelled(monkeypatch):
    submission_id = "11111111-1111-1111-1111-111111111112"
    api_key = SimpleNamespace(agent_id="agent_test")

    monkeypatch.setattr(
        routes, "verify_agent_owns_submission", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        routes.db,
        "get_submission",
        AsyncMock(return_value={"agent_verdict": "pending", "task": {"status": "cancelled"}}),
    )

    update_submission = AsyncMock()
    monkeypatch.setattr(routes.db, "update_submission", update_submission)

    with pytest.raises(HTTPException) as exc:
        await routes.approve_submission(
            submission_id=submission_id,
            request=None,
            api_key=api_key,
        )

    assert exc.value.status_code == 409
    update_submission.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_task_returns_idempotent_when_already_cancelled(monkeypatch):
    task_id = "22222222-2222-2222-2222-222222222222"
    api_key = SimpleNamespace(agent_id="agent_test")

    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(return_value={"id": task_id, "agent_id": "agent_test", "status": "cancelled"}),
    )

    cancel_task_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "cancel_task", cancel_task_mock)

    result = await routes.cancel_task(
        task_id=task_id,
        request=None,
        api_key=api_key,
    )

    assert result.data["idempotent"] is True
    cancel_task_mock.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_task_refunds_when_escrow_is_deposited(monkeypatch):
    task_id = "33333333-3333-3333-3333-333333333333"
    api_key = SimpleNamespace(agent_id="agent_test")

    monkeypatch.setattr(routes, "X402_AVAILABLE", True)
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": "agent_test",
                "status": "published",
                "escrow_tx": "x-payment-payload",
                "escrow_id": "escrow_test",
            }
        ),
    )

    fake_client = _FakeClient(escrow_status="deposited")
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)

    cancel_task_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "cancel_task", cancel_task_mock)

    refund_task_payment = AsyncMock(
        return_value={"success": True, "tx_hash": "0xrefundtx"}
    )
    monkeypatch.setattr(
        routes,
        "get_sdk",
        lambda: SimpleNamespace(refund_task_payment=refund_task_payment),
    )

    result = await routes.cancel_task(
        task_id=task_id,
        request=None,
        api_key=api_key,
    )

    assert result.data["escrow"]["status"] == "refunded"
    assert result.data["escrow"]["tx_hash"] == "0xrefundtx"
    assert fake_client.escrows.last_update["status"] == "refunded"
    assert fake_client.payments.inserted_rows[0]["type"] == "refund"
    assert fake_client.payments.inserted_rows[0]["tx_hash"] == "0xrefundtx"
    assert refund_task_payment.await_count == 1
    cancel_task_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_task_rejects_when_escrow_is_already_released(monkeypatch):
    task_id = "33333333-3333-3333-3333-333333333334"
    api_key = SimpleNamespace(agent_id="agent_test")

    monkeypatch.setattr(routes, "X402_AVAILABLE", True)
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": "agent_test",
                "status": "published",
                "escrow_tx": "x-payment-payload",
                "escrow_id": "escrow_test",
            }
        ),
    )

    fake_client = _FakeClient(escrow_status="released")
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)

    cancel_task_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "cancel_task", cancel_task_mock)

    with pytest.raises(HTTPException) as exc:
        await routes.cancel_task(
            task_id=task_id,
            request=None,
            api_key=api_key,
        )

    assert exc.value.status_code == 409
    cancel_task_mock.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_task_uses_authorization_expiry_when_not_funded(monkeypatch):
    task_id = "44444444-4444-4444-4444-444444444444"
    api_key = SimpleNamespace(agent_id="agent_test")

    monkeypatch.setattr(routes, "X402_AVAILABLE", True)
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": "agent_test",
                "status": "published",
                "escrow_tx": "x-payment-payload",
                "escrow_id": "escrow_test",
            }
        ),
    )

    fake_client = _FakeClient(escrow_status="authorized")
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)

    cancel_task_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "cancel_task", cancel_task_mock)

    refund_task_payment = AsyncMock(
        return_value={"success": True, "tx_hash": "0xshouldnotrun"}
    )
    monkeypatch.setattr(
        routes,
        "get_sdk",
        lambda: SimpleNamespace(refund_task_payment=refund_task_payment),
    )

    result = await routes.cancel_task(
        task_id=task_id,
        request=None,
        api_key=api_key,
    )

    assert result.data["escrow"]["status"] == "authorization_expired"
    assert refund_task_payment.await_count == 0
    cancel_task_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_task_requires_x402_sdk_available(monkeypatch):
    api_key = SimpleNamespace(agent_id="agent_test")
    http_request = SimpleNamespace(headers={})
    request = routes.CreateTaskRequest(
        title="Test facilitator-only task",
        instructions="Create task should fail when x402 SDK is unavailable in production mode.",
        category=routes.TaskCategory.SIMPLE_ACTION,
        bounty_usd=0.5,
        deadline_hours=1,
        evidence_required=[routes.EvidenceType.SCREENSHOT],
        payment_token="USDC",
    )

    monkeypatch.setattr(routes, "X402_AVAILABLE", False)
    create_task_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "create_task", create_task_mock)

    with pytest.raises(HTTPException) as exc:
        await routes.create_task(
            http_request=http_request,
            request=request,
            api_key=api_key,
        )

    assert exc.value.status_code == 503
    create_task_mock.assert_not_called()


def test_resolve_task_payment_header_prefers_full_header_in_task():
    full_header = "eyJ4NDAyVmVyc2lvbiI6MSwic2NoZW1lIjoiZXhhY3QifQ" * 4
    resolved = routes._resolve_task_payment_header(
        task_id="task_test",
        task_escrow_tx=full_header,
    )
    assert resolved == full_header


def test_resolve_task_payment_header_reads_from_escrow_metadata(monkeypatch):
    stored_header = "eyJ4NDAyVmVyc2lvbiI6MSwicGF5bG9hZCI6eyJzaWduYXR1cmUiOiJ0ZXN0In19" * 3
    monkeypatch.setattr(
        routes.db,
        "get_client",
        lambda: _HeaderClient({"x_payment_header": stored_header}),
    )

    resolved = routes._resolve_task_payment_header(
        task_id="task_test",
        task_escrow_tx="x402_auth_abc123",
    )
    assert resolved == stored_header


@pytest.mark.asyncio
async def test_get_public_platform_metrics_aggregates_counts(monkeypatch):
    fake_client = _MetricsClient(
        tasks_rows=[
            {"status": "published", "executor_id": None, "agent_id": "agent_1", "bounty_usd": 0},
            {"status": "accepted", "executor_id": "worker_1", "agent_id": "agent_1", "bounty_usd": 0},
            {"status": "submitted", "executor_id": "worker_1", "agent_id": "agent_1", "bounty_usd": 0},
            {"status": "completed", "executor_id": "worker_2", "agent_id": "agent_2", "bounty_usd": 10.5},
            {"status": "completed", "executor_id": "worker_1", "agent_id": "agent_1", "bounty_usd": 5.25},
        ],
        escrow_rows=[
            {"total_amount_usdc": 10.5, "platform_fee_usdc": 0.8},
            {"total_amount_usdc": "5.25", "platform_fee_usdc": "0.42"},
        ],
        worker_count=12,
        agent_count=4,
    )
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)

    result = await routes.get_public_platform_metrics()

    assert result.users["registered_workers"] == 12
    assert result.users["registered_agents"] == 4
    assert result.users["workers_with_tasks"] == 2
    assert result.users["workers_active_now"] == 1
    assert result.users["workers_completed"] == 2
    assert result.users["agents_active_now"] == 1

    assert result.tasks["total"] == 5
    assert result.tasks["published"] == 1
    assert result.tasks["accepted"] == 1
    assert result.tasks["submitted"] == 1
    assert result.tasks["completed"] == 2
    assert result.tasks["live"] == 3

    assert result.activity["workers_with_active_tasks"] == 1
    assert result.activity["workers_with_completed_tasks"] == 2
    assert result.activity["agents_with_live_tasks"] == 1

    assert result.payments["total_volume_usd"] == 15.75
    assert result.payments["total_fees_usd"] == 1.26
