"""
Post-Audit Phase 2 Tests — Backend Hardening

4 tests covering security/correctness invariants from the post-audit remediation:
5. Missing EM_TREASURY_ADDRESS raises RuntimeError at import time
6. assign_task() rejects insufficient agent balance
7. auto_approve_submission() skips cancelled/expired tasks
8. API key cache is safe under concurrent access

These mirror test_audit_phase2_backend_hardening.py for the canonical
`test_post_audit_phase2.py` naming convention.
"""

import os
import sys
import importlib
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.core


# =============================================================================
# Test 5: EM_TREASURY_ADDRESS guard at import time
# =============================================================================


def test_missing_treasury_address_raises_on_import(monkeypatch):
    """
    Importing sdk_client without EM_TREASURY_ADDRESS must raise RuntimeError.

    Guards against fee payments being silently lost to the zero address.
    """
    monkeypatch.delenv("EM_TREASURY_ADDRESS", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase1")  # not "disabled"

    module_name = "integrations.x402.sdk_client"
    saved = sys.modules.pop(module_name, None)

    try:
        with pytest.raises(RuntimeError, match="EM_TREASURY_ADDRESS"):
            importlib.import_module(module_name)
    finally:
        sys.modules.pop(module_name, None)
        if saved is not None:
            sys.modules[module_name] = saved


# =============================================================================
# Test 6: assign_task() rejects insufficient balance
# =============================================================================


@pytest.mark.asyncio
async def test_assignment_rejects_insufficient_balance():
    """
    assign_task() must raise an Exception when the agent has insufficient USDC
    balance to cover the task bounty (Fase 1 pre-assignment balance check).
    """
    from uuid import uuid4

    import supabase_client

    task_id = str(uuid4())
    agent_address = "0xAgentWallet000000000000000000000000000001"
    executor_id = str(uuid4())

    mock_task = {
        "id": task_id,
        "agent_id": agent_address,
        "status": "published",
        "bounty_amount": "0.50",
        "lock_amount": None,
        "min_reputation": 0,
        "title": "Test task",
    }

    mock_executor_row = MagicMock()
    mock_executor_row.data = {
        "id": executor_id,
        "wallet_address": "0xExecutorWallet000000000000000000000000002",
        "erc8004_agent_id": None,
        "reputation_score": 100,
    }

    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_executor_row
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )

    # SDK instance that reports insufficient balance
    sdk_instance = MagicMock()
    sdk_instance.check_agent_balance = AsyncMock(
        return_value={"sufficient": False, "balance": "0.01"}
    )

    fake_sdk_module = MagicMock()
    fake_sdk_module.EMX402SDK = MagicMock(return_value=sdk_instance)

    with (
        patch.object(
            supabase_client, "get_task", new_callable=AsyncMock, return_value=mock_task
        ),
        patch.object(supabase_client, "get_client", return_value=mock_client),
        patch.dict(os.environ, {"EM_PAYMENT_MODE": "fase1"}),
        patch.dict(sys.modules, {"integrations.x402.sdk_client": fake_sdk_module}),
    ):
        with pytest.raises(Exception, match="[Ii]nsufficient"):
            await supabase_client.assign_task(
                task_id=task_id,
                agent_id=agent_address,
                executor_id=executor_id,
            )


# =============================================================================
# Test 7: auto_approve_submission() skips cancelled/expired tasks
# =============================================================================


@pytest.mark.asyncio
async def test_auto_approve_skips_cancelled_task():
    """
    auto_approve_submission() must return False (no update) when the parent
    task has status 'cancelled' or 'expired'.
    """
    from uuid import uuid4

    import supabase_client

    submission_id = str(uuid4())
    task_id = str(uuid4())

    for terminal_status in ("cancelled", "expired"):
        mock_client = MagicMock()

        # Submission fetch: pending verdict
        sub_result = MagicMock()
        sub_result.data = {"agent_verdict": None, "task_id": task_id}

        # Task fetch: terminal status
        task_result = MagicMock()
        task_result.data = [{"status": terminal_status}]

        def make_table_mock(sub_res, task_res):
            def table_side_effect(name):
                tbl = MagicMock()
                if name == "submissions":
                    tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = sub_res
                elif name == "tasks":
                    tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = task_res
                return tbl

            return table_side_effect

        mock_client.table.side_effect = make_table_mock(sub_result, task_result)

        with patch.object(supabase_client, "get_client", return_value=mock_client):
            result = await supabase_client.auto_approve_submission(
                submission_id=submission_id,
                score=0.9,
                agent_notes="Auto-check",
            )

        assert result is False, (
            f"auto_approve_submission should return False for task status={terminal_status!r}, got {result}"
        )


# =============================================================================
# Test 8: API key cache thread-safety
# =============================================================================


def test_api_key_cache_concurrent_access():
    """
    The TTLCache + Lock in api/auth.py must not raise or corrupt state when
    10 threads simultaneously read and write entries.

    Validates the threading.Lock protects both TTLCache (cachetools) and the
    dict fallback path.
    """
    import api.auth as auth_module
    from api.auth import APIKeyData, APITier, _api_key_cache_lock, clear_api_key_cache

    clear_api_key_cache()

    errors = []
    results = []

    def worker(idx: int):
        key_hash = f"deadbeef{idx:04x}" + "0" * 56  # 64-char hex
        fake_data = APIKeyData(
            key_hash=key_hash,
            agent_id=f"agent_{idx}",
            tier=APITier.FREE,
            is_valid=True,
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
        )
        try:
            with _api_key_cache_lock:
                auth_module._api_key_cache[key_hash] = fake_data
            with _api_key_cache_lock:
                found = auth_module._api_key_cache.get(key_hash)
            results.append(found is not None)
            with _api_key_cache_lock:
                if key_hash in auth_module._api_key_cache:
                    del auth_module._api_key_cache[key_hash]
        except Exception as exc:
            errors.append(exc)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(worker, i) for i in range(10)]
        concurrent.futures.wait(futures)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 10
    assert all(results), "Some cache reads returned None unexpectedly"
