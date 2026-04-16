"""
Focused P0 tests for approve/cancel idempotency and refund behavior,
plus X-Idempotency-Key header support for task creation.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.core
from fastapi import HTTPException

from ..api import routes
from ..api.auth import WorkerAuth
from ..api.routers import tasks as tasks_router


def _mock_request():
    """Create a mock FastAPI Request object."""
    mock = MagicMock()
    mock.url.path = "/test"
    return mock


def _mock_worker_auth(executor_id="test-executor"):
    """Create a WorkerAuth object for testing."""
    return WorkerAuth(executor_id=executor_id, user_id="test-user", auth_method="jwt")


class _FakeEscrowsTable:
    def __init__(self, status: str, escrow_id: str = "escrow_test"):
        self.status = status
        self.escrow_id = escrow_id
        self.last_update = None
        self._use_list = False

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def single(self):
        self._use_list = False
        return self

    def limit(self, *_args, **_kwargs):
        self._use_list = True
        return self

    def update(self, payload):
        self.last_update = payload
        return self

    def execute(self):
        row = {"status": self.status, "escrow_id": self.escrow_id}
        if self._use_list:
            self._use_list = False
            return SimpleNamespace(data=[row])
        return SimpleNamespace(data=row)


class _FakePaymentsTable:
    def __init__(self):
        self.inserted_rows = []

    def insert(self, payload):
        self.inserted_rows.append(payload)
        return self

    def execute(self):
        return SimpleNamespace(
            data=self.inserted_rows[-1] if self.inserted_rows else None
        )


class _FakeTasksTable:
    def __init__(self):
        self.last_update = None

    def update(self, payload):
        self.last_update = payload
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.last_update)


class _FakeClient:
    def __init__(self, escrow_status: str):
        self.escrows = _FakeEscrowsTable(status=escrow_status)
        self.payments = _FakePaymentsTable()
        self.tasks = _FakeTasksTable()

    def table(self, name: str):
        if name == "escrows":
            return self.escrows
        if name == "payments":
            return self.payments
        if name == "tasks":
            return self.tasks
        raise AssertionError(f"Unexpected table access: {name}")


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


class _TaskPaymentQuery:
    def __init__(self, rows=None, fail_message=None):
        self.rows = rows or []
        self.fail_message = fail_message
        self._limit = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, value):
        self._limit = value
        return self

    def not_(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def execute(self):
        if self.fail_message:
            raise Exception(self.fail_message)
        rows = self.rows[: self._limit] if isinstance(self._limit, int) else self.rows
        return SimpleNamespace(data=rows)


class _TaskPaymentClient:
    def __init__(
        self, payments=None, escrows=None, submissions=None, missing_tables=None
    ):
        self._payments = payments or []
        self._escrows = escrows or []
        self._submissions = submissions or []
        self._missing_tables = set(missing_tables or [])

    def table(self, name: str):
        if name in self._missing_tables:
            return _TaskPaymentQuery(
                fail_message=f'PGRST205: relation "public.{name}" does not exist'
            )
        if name == "payments":
            return _TaskPaymentQuery(rows=self._payments)
        if name == "escrows":
            return _TaskPaymentQuery(rows=self._escrows)
        if name == "submissions":
            return _TaskPaymentQuery(rows=self._submissions)
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
        AsyncMock(
            return_value={
                "id": submission_id,
                "agent_verdict": "accepted",
                "task": {"id": "task_1"},
            }
        ),
    )
    monkeypatch.setattr(
        routes,
        "_settle_submission_payment",
        AsyncMock(
            return_value={"payment_tx": "0xalreadysettled", "payment_error": None}
        ),
    )

    update_submission = AsyncMock()
    monkeypatch.setattr(routes.db, "update_submission", update_submission)

    result = await routes.approve_submission(
        submission_id=submission_id,
        request=None,
        auth=api_key,
    )

    assert result.data["idempotent"] is True
    assert result.data["payment_tx"] == "0xalreadysettled"
    update_submission.assert_not_called()


@pytest.mark.asyncio
async def test_approve_submission_requires_tx_before_marking_accepted(monkeypatch):
    submission_id = "12121212-1111-1111-1111-111111111111"
    api_key = SimpleNamespace(agent_id="agent_test")

    submission_payload = {
        "id": submission_id,
        "agent_verdict": "pending",
        "task": {
            "id": "task_approve_guard",
            "status": "submitted",
        },
    }

    monkeypatch.setattr(
        routes, "verify_agent_owns_submission", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        routes.db,
        "get_submission",
        AsyncMock(return_value=submission_payload),
    )
    # Mock escrow lookup so guard passes (escrow in releasable state)
    fake_client = _FakeClient(escrow_status="deposited")
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)
    monkeypatch.setattr(
        routes,
        "_settle_submission_payment",
        AsyncMock(
            return_value={"payment_tx": None, "payment_error": "missing tx hash"}
        ),
    )

    update_submission = AsyncMock()
    monkeypatch.setattr(routes.db, "update_submission", update_submission)

    with pytest.raises(HTTPException) as exc:
        await routes.approve_submission(
            submission_id=submission_id,
            request=routes.ApprovalRequest(notes="approve"),
            auth=api_key,
        )

    assert exc.value.status_code == 502
    update_submission.assert_not_called()


@pytest.mark.asyncio
async def test_submit_work_auto_pays_and_marks_completed(monkeypatch):
    task_id = "88888888-8888-4888-8888-888888888888"
    submission_id = "99999999-9999-4999-9999-999999999999"
    executor_id = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"

    submission_payload = {
        "id": submission_id,
        "task": {
            "id": task_id,
            "agent_id": "agent_test",
            "bounty_usd": 1.0,
            "escrow_tx": "x402_auth_ref",
        },
        "executor": {
            "id": executor_id,
            "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
        },
        "agent_verdict": "pending",
    }

    monkeypatch.setattr(
        routes.db,
        "submit_work",
        AsyncMock(
            return_value={"submission": {"id": submission_id}, "task": {"id": task_id}}
        ),
    )
    monkeypatch.setattr(
        routes.db,
        "get_submission",
        AsyncMock(return_value=submission_payload),
    )
    monkeypatch.setattr(
        routes,
        "_is_submission_ready_for_instant_payout",
        AsyncMock(return_value={"ready": True, "reason": "ready"}),
    )
    monkeypatch.setattr(
        routes,
        "_settle_submission_payment",
        AsyncMock(return_value={"payment_tx": "0x" + "a" * 64, "payment_error": None}),
    )
    auto_approve = AsyncMock(return_value=submission_payload)
    monkeypatch.setattr(routes, "_auto_approve_submission", auto_approve)

    result = await routes.submit_work(
        raw_request=_mock_request(),
        task_id=task_id,
        request=routes.WorkerSubmissionRequest(
            executor_id=executor_id,
            evidence={"screenshot": "https://example.com/proof.png"},
            notes="done",
        ),
        worker_auth=_mock_worker_auth(executor_id=executor_id),
    )

    assert result.message == "Work submitted and paid instantly."
    assert result.data["status"] == "completed"
    assert result.data["verdict"] == "accepted"
    assert result.data["payment_tx"] == "0x" + "a" * 64
    auto_approve.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_work_keeps_review_flow_when_instant_payout_not_ready(monkeypatch):
    task_id = "88888888-8888-4888-8888-888888888889"
    submission_id = "99999999-9999-4999-9999-999999999998"
    executor_id = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"

    submission_payload = {
        "id": submission_id,
        "task": {
            "id": task_id,
            "agent_id": "agent_test",
            "bounty_usd": 1.0,
        },
        "executor": {"id": executor_id, "wallet_address": None},
        "agent_verdict": "pending",
    }

    monkeypatch.setattr(
        routes.db,
        "submit_work",
        AsyncMock(
            return_value={"submission": {"id": submission_id}, "task": {"id": task_id}}
        ),
    )
    monkeypatch.setattr(
        routes.db,
        "get_submission",
        AsyncMock(return_value=submission_payload),
    )
    monkeypatch.setattr(
        routes,
        "_is_submission_ready_for_instant_payout",
        AsyncMock(return_value={"ready": False, "reason": "missing_payment_header"}),
    )
    settle_mock = AsyncMock()
    monkeypatch.setattr(routes, "_settle_submission_payment", settle_mock)
    auto_approve = AsyncMock()
    monkeypatch.setattr(routes, "_auto_approve_submission", auto_approve)

    result = await routes.submit_work(
        raw_request=_mock_request(),
        task_id=task_id,
        request=routes.WorkerSubmissionRequest(
            executor_id=executor_id,
            evidence={"photo": "https://example.com/photo.png"},
        ),
        worker_auth=_mock_worker_auth(executor_id=executor_id),
    )

    assert result.message == "Work submitted successfully. Awaiting agent review."
    assert result.data["status"] == "submitted"
    assert "payment_tx" not in result.data
    settle_mock.assert_not_awaited()
    auto_approve.assert_not_awaited()


def test_release_payment_requires_tx_hash_for_finalization():
    row_without_tx = {
        "payment_type": "full_release",
        "status": "confirmed",
        "tx_hash": None,
        "transaction_hash": None,
    }
    row_with_tx = {
        "payment_type": "full_release",
        "status": "confirmed",
        "tx_hash": "0x" + "a" * 64,
    }

    assert routes._is_payment_finalized(row_without_tx) is False
    assert routes._is_payment_finalized(row_with_tx) is True


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
        AsyncMock(
            return_value={"agent_verdict": "pending", "task": {"status": "cancelled"}}
        ),
    )

    update_submission = AsyncMock()
    monkeypatch.setattr(routes.db, "update_submission", update_submission)

    with pytest.raises(HTTPException) as exc:
        await routes.approve_submission(
            submission_id=submission_id,
            request=None,
            auth=api_key,
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
        AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": "agent_test",
                "status": "cancelled",
            }
        ),
    )

    cancel_task_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "cancel_task", cancel_task_mock)

    result = await routes.cancel_task(
        task_id=task_id,
        request=None,
        auth=api_key,
    )

    assert result.data["idempotent"] is True
    cancel_task_mock.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_task_refunds_when_escrow_is_deposited(monkeypatch):
    task_id = "33333333-3333-3333-3333-333333333333"
    api_key = SimpleNamespace(agent_id="agent_test")

    monkeypatch.setattr(routes, "X402_AVAILABLE", True)

    # Mock the PaymentDispatcher to return a successful refund
    mock_refund = AsyncMock(
        return_value={"success": True, "tx_hash": "0xrefundtx", "mode": "fase2"}
    )
    mock_dispatcher = SimpleNamespace(
        refund_payment=mock_refund,
        get_mode=lambda: "fase2",
        escrow_mode="platform_release",
    )
    monkeypatch.setattr(routes, "get_payment_dispatcher", lambda: mock_dispatcher)

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

    result = await routes.cancel_task(
        task_id=task_id,
        request=None,
        auth=api_key,
    )

    assert result.data["escrow"]["status"] == "refunded"
    assert result.data["escrow"]["tx_hash"] == "0xrefundtx"
    assert fake_client.escrows.last_update["status"] == "refunded"
    assert fake_client.escrows.last_update["refund_tx"] == "0xrefundtx"
    assert fake_client.tasks.last_update["refund_tx"] == "0xrefundtx"
    assert fake_client.payments.inserted_rows[0]["type"] == "refund"
    assert fake_client.payments.inserted_rows[0]["tx_hash"] == "0xrefundtx"
    assert mock_refund.await_count == 1
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
            auth=api_key,
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
        auth=api_key,
    )

    assert result.data["escrow"]["status"] == "authorization_expired"
    assert refund_task_payment.await_count == 0
    cancel_task_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_task_already_refunded_is_noop(monkeypatch):
    task_id = "44444444-4444-4444-4444-444444444445"
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

    fake_client = _FakeClient(escrow_status="refunded")
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)

    cancel_task_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "cancel_task", cancel_task_mock)

    refund_task_payment = AsyncMock()
    monkeypatch.setattr(
        routes,
        "get_sdk",
        lambda: SimpleNamespace(refund_task_payment=refund_task_payment),
    )

    result = await routes.cancel_task(
        task_id=task_id,
        request=None,
        auth=api_key,
    )

    assert result.data["escrow"]["status"] == "already_refunded"
    assert refund_task_payment.await_count == 0
    cancel_task_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_task_unknown_status_attempts_refund(monkeypatch):
    task_id = "44444444-4444-4444-4444-444444444446"
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

    fake_client = _FakeClient(escrow_status="some_unknown_status")
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)

    cancel_task_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "cancel_task", cancel_task_mock)

    refund_task_payment = AsyncMock(
        return_value={
            "success": True,
            "tx_hash": "0xunknownrefund",
            "method": "facilitator",
        }
    )
    monkeypatch.setattr(
        routes,
        "get_sdk",
        lambda: SimpleNamespace(refund_task_payment=refund_task_payment),
    )

    result = await routes.cancel_task(
        task_id=task_id,
        request=None,
        auth=api_key,
    )

    assert result.data["escrow"]["status"] == "refunded"
    assert result.data["escrow"]["tx_hash"] == "0xunknownrefund"
    assert refund_task_payment.await_count == 1
    assert fake_client.tasks.last_update["refund_tx"] == "0xunknownrefund"
    cancel_task_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_task_unknown_status_falls_back_to_expired_on_failure(monkeypatch):
    task_id = "44444444-4444-4444-4444-444444444447"
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

    fake_client = _FakeClient(escrow_status="some_unknown_status")
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)

    cancel_task_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "cancel_task", cancel_task_mock)

    refund_task_payment = AsyncMock(side_effect=Exception("SDK failure"))
    monkeypatch.setattr(
        routes,
        "get_sdk",
        lambda: SimpleNamespace(refund_task_payment=refund_task_payment),
    )

    result = await routes.cancel_task(
        task_id=task_id,
        request=None,
        auth=api_key,
    )

    assert result.data["escrow"]["status"] == "authorization_expired"
    cancel_task_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_payment_timeline_shows_refund_event(monkeypatch):
    task_id = "55555555-5555-5555-5555-555555555556"
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": "agent_test",
                "status": "cancelled",
                "bounty_usd": 5.0,
                "escrow_tx": "x402_auth_reference",
                "escrow_id": "escrow_ref",
                "refund_tx": "0x" + "c" * 64,
                "created_at": "2026-02-06T10:00:00+00:00",
                "updated_at": "2026-02-06T10:05:00+00:00",
            }
        ),
    )
    monkeypatch.setattr(
        routes.db,
        "get_client",
        lambda: _TaskPaymentClient(
            payments=[],
            escrows=[],
            submissions=[],
            missing_tables={"payments", "escrows"},
        ),
    )

    result = await routes.get_task_payment(task_id=task_id, auth=None)

    assert result.status == "refunded"
    refund_events = [e for e in result.events if e.type == "refund"]
    assert len(refund_events) == 1
    assert refund_events[0].tx_hash == "0x" + "c" * 64


@pytest.mark.asyncio
async def test_payment_timeline_shows_auth_expired_for_cancelled_without_refund(
    monkeypatch,
):
    task_id = "55555555-5555-5555-5555-555555555557"
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": "agent_test",
                "status": "cancelled",
                "bounty_usd": 2.0,
                "escrow_tx": "x402_auth_reference",
                "escrow_id": None,
                "refund_tx": None,
                "created_at": "2026-02-06T10:00:00+00:00",
                "updated_at": "2026-02-06T10:03:00+00:00",
            }
        ),
    )
    monkeypatch.setattr(
        routes.db,
        "get_client",
        lambda: _TaskPaymentClient(
            payments=[],
            escrows=[],
            submissions=[],
            missing_tables={"payments", "escrows"},
        ),
    )

    result = await routes.get_task_payment(task_id=task_id, auth=None)

    assert result.status == "refunded"
    auth_expired_events = [
        e for e in result.events if e.type == "authorization_expired"
    ]
    assert len(auth_expired_events) == 1
    assert auth_expired_events[0].tx_hash is None


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
            auth=api_key,
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
    stored_header = (
        "eyJ4NDAyVmVyc2lvbiI6MSwicGF5bG9hZCI6eyJzaWduYXR1cmUiOiJ0ZXN0In19" * 3
    )
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
            {
                "status": "published",
                "executor_id": None,
                "agent_id": "agent_1",
                "bounty_usd": 0,
            },
            {
                "status": "accepted",
                "executor_id": "worker_1",
                "agent_id": "agent_1",
                "bounty_usd": 0,
            },
            {
                "status": "submitted",
                "executor_id": "worker_1",
                "agent_id": "agent_1",
                "bounty_usd": 0,
            },
            {
                "status": "completed",
                "executor_id": "worker_2",
                "agent_id": "agent_2",
                "bounty_usd": 10.5,
            },
            {
                "status": "completed",
                "executor_id": "worker_1",
                "agent_id": "agent_1",
                "bounty_usd": 5.25,
            },
        ],
        escrow_rows=[
            {"total_amount_usdc": 10.5, "platform_fee_usdc": 1.37},
            {"total_amount_usdc": "5.25", "platform_fee_usdc": "0.68"},
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
    assert result.payments["total_fees_usd"] == 2.05


@pytest.mark.asyncio
async def test_get_task_payment_returns_canonical_timeline(monkeypatch):
    task_id = "55555555-5555-5555-5555-555555555555"
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": "agent_test",
                "status": "completed",
                "bounty_usd": 6.5,
                "escrow_tx": "x402_auth_reference_token",
                "escrow_id": "escrow_ref",
                "created_at": "2026-02-06T10:00:00+00:00",
                "updated_at": "2026-02-06T10:15:00+00:00",
            }
        ),
    )
    monkeypatch.setattr(
        routes.db,
        "get_client",
        lambda: _TaskPaymentClient(
            payments=[
                {
                    "id": "payment_1",
                    "type": "release",
                    "status": "confirmed",
                    "amount_usdc": 6.5,
                    "tx_hash": "0x" + "a" * 64,
                    "created_at": "2026-02-06T10:12:00+00:00",
                    "network": "base",
                }
            ],
            escrows=[
                {
                    "task_id": task_id,
                    "status": "released",
                    "created_at": "2026-02-06T10:01:00+00:00",
                }
            ],
            submissions=[],
        ),
    )

    result = await routes.get_task_payment(task_id=task_id, auth=None)

    assert result.task_id == task_id
    assert result.status == "completed"
    assert result.total_amount == 6.5
    assert result.released_amount == 6.5
    assert any(event.type == "final_release" for event in result.events)
    assert any(event.type == "escrow_created" for event in result.events)


@pytest.mark.asyncio
async def test_get_task_payment_falls_back_when_payments_table_missing(monkeypatch):
    task_id = "66666666-6666-6666-6666-666666666666"
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(
            return_value={
                "id": task_id,
                "agent_id": "agent_test",
                "status": "completed",
                "bounty_usd": 3.0,
                "escrow_tx": "x402_auth_reference_token",
                "escrow_id": "escrow_ref",
                "created_at": "2026-02-06T11:00:00+00:00",
                "updated_at": "2026-02-06T11:20:00+00:00",
            }
        ),
    )
    monkeypatch.setattr(
        routes.db,
        "get_client",
        lambda: _TaskPaymentClient(
            payments=[],
            escrows=[],
            submissions=[
                {
                    "id": "sub_1",
                    "payment_tx": "0x" + "b" * 64,
                    "payment_amount": 3.0,
                    "paid_at": "2026-02-06T11:19:00+00:00",
                    "submitted_at": "2026-02-06T11:10:00+00:00",
                }
            ],
            missing_tables={"payments"},
        ),
    )

    result = await routes.get_task_payment(task_id=task_id, auth=None)

    assert result.status == "completed"
    assert result.total_amount == 3.0
    assert result.released_amount == 3.0
    assert any(event.type == "final_release" for event in result.events)


@pytest.mark.asyncio
async def test_get_task_payment_returns_404_when_task_is_missing(monkeypatch):
    task_id = "77777777-7777-7777-7777-777777777777"
    monkeypatch.setattr(
        routes.db,
        "get_task",
        AsyncMock(
            side_effect=Exception(
                "PGRST116: JSON object requested, multiple (or no) rows returned"
            )
        ),
    )

    with pytest.raises(HTTPException) as exc:
        await routes.get_task_payment(task_id=task_id, auth=None)

    assert exc.value.status_code == 404


# =============================================================================
# Side-effect resilience: failures never flip approval success
# =============================================================================


@pytest.mark.asyncio
async def test_side_effect_failure_never_flips_approval_success(monkeypatch):
    """Invariant: ERC-8004 side-effect failures are non-blocking.

    Even when _execute_post_approval_side_effects raises, the approval
    must still return 200 with payment_tx.
    """
    submission_id = "aaa11111-1111-1111-1111-111111111111"
    api_key = SimpleNamespace(agent_id="agent_test")
    release_tx = "0x" + "f" * 64

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
                "task": {"id": "task_se_1", "status": "submitted"},
                "executor": {"id": "exec_1", "wallet_address": "0xworker"},
            }
        ),
    )
    # Mock escrow lookup so guard passes (escrow in releasable state)
    fake_client = _FakeClient(escrow_status="locked")
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)
    monkeypatch.setattr(
        routes,
        "_settle_submission_payment",
        AsyncMock(return_value={"payment_tx": release_tx, "payment_error": None}),
    )
    monkeypatch.setattr(routes.db, "update_submission", AsyncMock())

    # Force side effects to explode
    monkeypatch.setattr(
        routes,
        "_execute_post_approval_side_effects",
        AsyncMock(side_effect=RuntimeError("ERC-8004 facilitator down")),
    )

    result = await routes.approve_submission(
        submission_id=submission_id,
        request=routes.ApprovalRequest(notes="lgtm"),
        auth=api_key,
    )

    # Approval MUST succeed despite side-effect explosion
    assert result.data["verdict"] == "accepted"
    assert result.data["payment_tx"] == release_tx
    assert "idempotent" not in result.data


@pytest.mark.asyncio
async def test_approve_twice_returns_idempotent_no_duplicate_state_write(monkeypatch):
    """Invariant: Calling approve on an already-accepted submission returns
    idempotent success and does NOT call update_submission again."""
    submission_id = "bbb22222-2222-2222-2222-222222222222"
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
                "agent_verdict": "accepted",
                "task": {"id": "task_idem_1"},
            }
        ),
    )
    monkeypatch.setattr(
        routes,
        "_settle_submission_payment",
        AsyncMock(return_value={"payment_tx": "0xoriginal_tx", "payment_error": None}),
    )

    update_mock = AsyncMock()
    monkeypatch.setattr(routes.db, "update_submission", update_mock)

    side_fx_mock = AsyncMock()
    monkeypatch.setattr(routes, "_execute_post_approval_side_effects", side_fx_mock)

    # First call (idempotent path since verdict is already accepted)
    result1 = await routes.approve_submission(
        submission_id=submission_id,
        request=None,
        auth=api_key,
    )
    assert result1.data["idempotent"] is True
    assert result1.data["payment_tx"] == "0xoriginal_tx"

    # Second call — same behavior
    result2 = await routes.approve_submission(
        submission_id=submission_id,
        request=None,
        auth=api_key,
    )
    assert result2.data["idempotent"] is True

    # update_submission must NEVER be called for idempotent approvals
    update_mock.assert_not_called()
    # Side effects must NOT re-run on idempotent path
    side_fx_mock.assert_not_called()


@pytest.mark.asyncio
async def test_feature_flags_disable_side_effects(monkeypatch):
    """Invariant: When _execute_post_approval_side_effects does nothing
    because imports fail (modules absent), approval still succeeds.

    This simulates the feature flag being off (modules not available).
    """
    submission_id = "ccc33333-3333-3333-3333-333333333333"
    api_key = SimpleNamespace(agent_id="agent_test")
    release_tx = "0x" + "d" * 64

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
                "task": {"id": "task_ff_1", "status": "submitted"},
                "executor": {"id": "exec_1", "wallet_address": "0xworker"},
            }
        ),
    )
    # Mock escrow lookup so guard passes (escrow in releasable state)
    fake_client = _FakeClient(escrow_status="funded")
    monkeypatch.setattr(routes.db, "get_client", lambda: fake_client)
    monkeypatch.setattr(
        routes,
        "_settle_submission_payment",
        AsyncMock(return_value={"payment_tx": release_tx, "payment_error": None}),
    )
    monkeypatch.setattr(routes.db, "update_submission", AsyncMock())

    # Simulate feature flags off: side effects return immediately (no-op)
    noop_side_fx = AsyncMock(return_value=None)
    monkeypatch.setattr(routes, "_execute_post_approval_side_effects", noop_side_fx)

    result = await routes.approve_submission(
        submission_id=submission_id,
        request=routes.ApprovalRequest(notes="approved"),
        auth=api_key,
    )

    assert result.data["verdict"] == "accepted"
    assert result.data["payment_tx"] == release_tx
    # Side effects were called but did nothing — approval unaffected
    noop_side_fx.assert_awaited_once()


# =====================================================================
# X-Idempotency-Key tests for task creation
# =====================================================================


def _mock_http_request(idempotency_key=None, extra_headers=None):
    """Create a mock FastAPI Request with optional idempotency key header."""
    headers = {}
    if idempotency_key:
        headers["X-Idempotency-Key"] = idempotency_key
    if extra_headers:
        headers.update(extra_headers)
    mock = MagicMock()
    mock.headers = headers
    mock.url.path = "/api/v1/tasks"
    return mock


def _existing_task(task_id="task-existing-123", agent_id="0xAgent1"):
    """Return a realistic task dict as would be stored in the DB."""
    return {
        "id": task_id,
        "title": "Test idempotent task",
        "status": "published",
        "category": "simple_action",
        "bounty_usd": 0.10,
        "deadline": "2026-04-13T00:00:00+00:00",
        "created_at": "2026-04-12T12:00:00+00:00",
        "agent_id": agent_id,
        "instructions": "Take a screenshot of the store.",
        "evidence_schema": {"required": ["photo"], "optional": []},
        "location_hint": None,
        "min_reputation": 0,
        "erc8004_agent_id": None,
        "payment_network": "base",
        "payment_token": "USDC",
        "escrow_tx": "0xescrow123",
        "refund_tx": None,
        "target_executor_type": None,
        "metadata": None,
        "required_capabilities": None,
        "skill_version": "9.1.0",
    }


@pytest.mark.asyncio
async def test_create_task_idempotent_returns_existing(monkeypatch):
    """When X-Idempotency-Key matches an existing task, return it (HTTP 200)."""
    key = "idem-key-abc-123"
    agent_id = "0xAgent1"
    existing = _existing_task(agent_id=agent_id)

    monkeypatch.setattr(
        tasks_router.db,
        "get_task_by_idempotency_key",
        AsyncMock(return_value=existing),
    )
    create_task_mock = AsyncMock()
    monkeypatch.setattr(tasks_router.db, "create_task", create_task_mock)

    auth = SimpleNamespace(
        agent_id=agent_id, wallet_address=agent_id, auth_method="erc8128"
    )
    req_body = MagicMock()  # CreateTaskRequest (won't be used)

    result = await tasks_router.create_task(
        http_request=_mock_http_request(idempotency_key=key),
        request=req_body,
        auth=auth,
    )

    # Should return JSONResponse with 200 + idempotent header
    assert result.status_code == 200
    assert result.headers.get("X-Idempotent") == "true"
    import json as _json

    body = _json.loads(result.body.decode())
    assert body["id"] == existing["id"]
    assert body["title"] == existing["title"]

    # create_task should NOT have been called
    create_task_mock.assert_not_called()


@pytest.mark.asyncio
async def test_create_task_no_idempotency_key_creates_normally(monkeypatch):
    """Without X-Idempotency-Key, task creation proceeds as normal."""
    lookup_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(tasks_router.db, "get_task_by_idempotency_key", lookup_mock)

    # The function will proceed past the idempotency check and hit
    # get_platform_fee_percent — we verify it was NOT short-circuited.
    fee_mock = AsyncMock(return_value=0)
    monkeypatch.setattr(tasks_router, "get_platform_fee_percent", fee_mock)

    auth = SimpleNamespace(
        agent_id="0xAgent2", wallet_address="0xAgent2", auth_method="erc8128"
    )

    # Without the header, lookup should never be called
    try:
        await tasks_router.create_task(
            http_request=_mock_http_request(idempotency_key=None),
            request=MagicMock(bounty_usd=0.10),
            auth=auth,
        )
    except Exception:
        pass  # We expect it to fail further down — we only care about the idempotency path

    # Idempotency lookup was NOT called (no header)
    lookup_mock.assert_not_called()
    # Normal flow proceeded (fee was fetched)
    fee_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_task_idempotency_key_miss_proceeds_normally(monkeypatch):
    """With X-Idempotency-Key but no match, normal creation continues."""
    key = "idem-key-new-456"
    lookup_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(tasks_router.db, "get_task_by_idempotency_key", lookup_mock)

    fee_mock = AsyncMock(return_value=0)
    monkeypatch.setattr(tasks_router, "get_platform_fee_percent", fee_mock)

    auth = SimpleNamespace(
        agent_id="0xAgent3", wallet_address="0xAgent3", auth_method="erc8128"
    )

    try:
        await tasks_router.create_task(
            http_request=_mock_http_request(idempotency_key=key),
            request=MagicMock(bounty_usd=0.10),
            auth=auth,
        )
    except Exception:
        pass  # Will fail downstream — we only test the idempotency path

    # Lookup WAS called (header present) but returned None
    lookup_mock.assert_awaited_once_with(key, "0xAgent3")
    # Normal flow proceeded
    fee_mock.assert_awaited_once()
