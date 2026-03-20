"""
Phase 2 Audit Tests — Backend Hardening

Covers four security/correctness invariants identified in the post-audit remediation:
1. Missing EM_TREASURY_ADDRESS raises RuntimeError at import time
2. assign_task() rejects insufficient agent balance
3. auto_approve_submission() skips cancelled/expired tasks
4. API key cache is safe under concurrent access
"""

import os
import sys
import importlib
import threading
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

pytestmark = pytest.mark.core


# =============================================================================
# Test 1: EM_TREASURY_ADDRESS guard at import time
# =============================================================================


def test_missing_treasury_address_raises_on_import(monkeypatch):
    """
    Importing sdk_client without EM_TREASURY_ADDRESS must raise RuntimeError.

    Guards against fee payments being silently lost to the zero address.
    """
    # Ensure the guard conditions are all unset
    monkeypatch.delenv("EM_TREASURY_ADDRESS", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase1")  # not "disabled"

    # Remove the cached module so the module-level code re-executes
    module_name = "integrations.x402.sdk_client"
    saved = sys.modules.pop(module_name, None)

    try:
        with pytest.raises(RuntimeError, match="EM_TREASURY_ADDRESS"):
            importlib.import_module(module_name)
    finally:
        # Restore original module state so other tests are unaffected
        sys.modules.pop(module_name, None)
        if saved is not None:
            sys.modules[module_name] = saved


def test_treasury_address_guard_bypassed_in_testing_mode(monkeypatch):
    """
    When TESTING=true the guard must not raise, even with EM_TREASURY_ADDRESS unset.
    """
    monkeypatch.delenv("EM_TREASURY_ADDRESS", raising=False)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("EM_PAYMENT_MODE", "fase1")

    module_name = "integrations.x402.sdk_client"
    saved = sys.modules.pop(module_name, None)

    try:
        mod = importlib.import_module(module_name)
        # Zero-address fallback is used
        assert mod.EM_TREASURY == "0x0000000000000000000000000000000000000000"
    finally:
        sys.modules.pop(module_name, None)
        if saved is not None:
            sys.modules[module_name] = saved


# =============================================================================
# Test 2: assign_task() rejects insufficient balance
# =============================================================================


@pytest.mark.asyncio
async def test_assignment_rejects_insufficient_balance():
    """
    assign_task() must raise an Exception when the agent has insufficient USDC
    balance to cover the task bounty (Fase 1 pre-assignment balance check).

    assign_task() does a local `from integrations.x402.sdk_client import EMX402SDK`
    at runtime, so we patch via sys.modules before calling the function.
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
    # applications table lookup (no active application needed for this path)
    mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[]
    )

    # SDK instance that reports insufficient balance
    sdk_instance = MagicMock()
    sdk_instance.check_agent_balance = AsyncMock(
        return_value={"sufficient": False, "balance": "0.01"}
    )

    # Fake module standing in for integrations.x402.sdk_client at import time
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
# Test 3: auto_approve_submission() skips cancelled/expired tasks
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


@pytest.mark.asyncio
async def test_auto_approve_skips_completed_task():
    """
    auto_approve_submission() must also skip tasks with status 'completed'
    (already finalized — approving again would double-pay).
    """
    from uuid import uuid4

    import supabase_client

    submission_id = str(uuid4())
    task_id = str(uuid4())

    mock_client = MagicMock()

    sub_result = MagicMock()
    sub_result.data = {"agent_verdict": None, "task_id": task_id}

    task_result = MagicMock()
    task_result.data = [{"status": "completed"}]

    def table_side_effect(name):
        tbl = MagicMock()
        if name == "submissions":
            tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = sub_result
        elif name == "tasks":
            tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = task_result
        return tbl

    mock_client.table.side_effect = table_side_effect

    with patch.object(supabase_client, "get_client", return_value=mock_client):
        result = await supabase_client.auto_approve_submission(
            submission_id=submission_id,
            score=0.9,
            agent_notes="Auto-check",
        )

    assert result is False


# =============================================================================
# Test 4: API key cache thread-safety
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

    # Start with a clean cache
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
            # Write
            with _api_key_cache_lock:
                auth_module._api_key_cache[key_hash] = fake_data

            # Read back
            with _api_key_cache_lock:
                found = auth_module._api_key_cache.get(key_hash)

            results.append(found is not None)

            # Delete (TTLCache uses __delitem__; guard against already-evicted entries)
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


def test_api_key_cache_concurrent_clear():
    """
    clear_api_key_cache() called concurrently from multiple threads must not
    raise and must leave the cache in a valid (empty) state.
    """
    import api.auth as auth_module
    from api.auth import APIKeyData, APITier, clear_api_key_cache

    # Pre-populate
    for i in range(20):
        key_hash = f"aabbcc{i:04x}" + "0" * 54
        with auth_module._api_key_cache_lock:
            auth_module._api_key_cache[key_hash] = APIKeyData(
                key_hash=key_hash,
                agent_id=f"agent_{i}",
                tier=APITier.FREE,
                is_valid=True,
            )

    errors = []

    def do_clear():
        try:
            clear_api_key_cache()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=do_clear) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"clear_api_key_cache raised in threads: {errors}"
    with auth_module._api_key_cache_lock:
        assert len(auth_module._api_key_cache) == 0
