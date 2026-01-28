# NOW-201: Test E2E - Task Lifecycle Completo

**Prioridad**: P1
**Status**: TODO
**Archivo**: `mcp_server/tests/e2e/test_task_lifecycle.py` (crear)

## Descripción

Test end-to-end que verifica el ciclo de vida completo de una tarea desde publicación hasta pago.

## Flujo Completo

```
Agent publica tarea (publish_task)
    ↓
Worker ve tarea (get_tasks)
    ↓
Worker aplica (apply_to_task)
    ↓
Agent asigna worker (assign_task)
    ↓
Worker sube evidencia (submit_work)
    ↓
Verificación automática + parcial release (30%)
    ↓
Agent aprueba (approve_submission)
    ↓
Release final (70% restante)
    ↓
Task completada
```

## Setup Requerido

- Supabase local o test DB
- Mock x402 para pagos
- Test wallets para agent y worker

## Implementación

```python
"""
E2E Test: Complete task lifecycle.

This test verifies the entire flow from task publication to payment.
"""

import pytest
from datetime import datetime, UTC
from decimal import Decimal

# These would be your actual imports
from ..server import (
    chamba_publish_task,
    chamba_get_tasks,
    chamba_apply_to_task,
    chamba_assign_task,
    chamba_submit_work,
    chamba_approve_submission,
)
from ..integrations.x402.escrow import EscrowManager


@pytest.fixture
def test_agent():
    """Test agent credentials."""
    return {
        "agent_id": "test-agent-e2e",
        "api_key": "chamba_enterprise_test1234567890abcdef1234567890ab",
        "wallet": "0xAgentWallet...",
    }


@pytest.fixture
def test_worker():
    """Test worker credentials."""
    return {
        "executor_id": "test-worker-e2e",
        "wallet": "0xWorkerWallet...",
    }


class TestTaskLifecycleE2E:
    """E2E test for complete task lifecycle."""

    @pytest.mark.asyncio
    async def test_complete_lifecycle(self, test_agent, test_worker):
        """
        Test: publish → apply → assign → submit → approve → pay
        """
        # ========== STEP 1: Agent publishes task ==========
        task_result = await chamba_publish_task(
            title="E2E Test Task",
            description="Take a photo of the storefront",
            bounty_usdc=10.00,
            location={"lat": 19.4326, "lng": -99.1332},
            deadline_hours=24,
            evidence_required=["photo", "gps"],
            agent_id=test_agent["agent_id"],
        )

        task_id = task_result["task_id"]
        assert task_id is not None
        assert task_result["status"] == "pending"

        # Verify escrow was created
        escrow = await EscrowManager().get_escrow(task_id)
        assert escrow.amount == Decimal("10.00")
        assert escrow.status == "deposited"

        # ========== STEP 2: Worker sees task ==========
        tasks = await chamba_get_tasks(
            location={"lat": 19.4326, "lng": -99.1332},
            radius_km=10,
            status="pending",
        )

        matching_tasks = [t for t in tasks if t["id"] == task_id]
        assert len(matching_tasks) == 1

        # ========== STEP 3: Worker applies ==========
        application = await chamba_apply_to_task(
            task_id=task_id,
            executor_id=test_worker["executor_id"],
            message="I can complete this task",
        )

        assert application["status"] == "applied"

        # ========== STEP 4: Agent assigns worker ==========
        assignment = await chamba_assign_task(
            task_id=task_id,
            executor_id=test_worker["executor_id"],
            agent_id=test_agent["agent_id"],
        )

        assert assignment["status"] == "assigned"

        # ========== STEP 5: Worker submits work ==========
        submission = await chamba_submit_work(
            task_id=task_id,
            executor_id=test_worker["executor_id"],
            evidence={
                "photo_url": "https://storage.chamba.xyz/evidence/test.jpg",
                "gps": {"lat": 19.4326, "lng": -99.1332},
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        submission_id = submission["submission_id"]
        assert submission_id is not None

        # Verify partial release (30%)
        escrow = await EscrowManager().get_escrow(task_id)
        assert escrow.partial_released == Decimal("3.00")  # 30% of 10

        # ========== STEP 6: Agent approves ==========
        approval = await chamba_approve_submission(
            submission_id=submission_id,
            agent_id=test_agent["agent_id"],
            rating=90,  # Good work
        )

        assert approval["status"] == "approved"
        assert approval["payment_status"] == "completed"

        # ========== VERIFY FINAL STATE ==========
        # Task completed
        from ..supabase_client import get_task
        final_task = await get_task(task_id)
        assert final_task["status"] == "completed"

        # Escrow fully released
        escrow = await EscrowManager().get_escrow(task_id)
        assert escrow.status == "released"

        # Worker received payment (10 - 8% fee = 9.20)
        assert escrow.worker_received == Decimal("9.20")
        assert escrow.platform_fee == Decimal("0.80")

        # Worker reputation updated
        from ..reputation.bayesian import BayesianCalculator
        calc = BayesianCalculator()
        # ... verify reputation change


    @pytest.mark.asyncio
    async def test_lifecycle_with_rejection(self, test_agent, test_worker):
        """Test flow when submission is rejected."""
        # Similar setup...
        # Agent rejects → worker can resubmit or dispute
        pass

    @pytest.mark.asyncio
    async def test_lifecycle_with_timeout(self, test_agent):
        """Test flow when task times out."""
        # Publish task with short deadline
        # Wait for timeout
        # Verify refund to agent
        pass
```

## Ejecución

```bash
# Requires test database
pytest tests/e2e/test_task_lifecycle.py -v -s

# With real Supabase (staging)
SUPABASE_URL=... SUPABASE_KEY=... pytest tests/e2e/ -v
```

## Criterios de Aceptación

- [ ] Flujo completo publish → pay funciona
- [ ] Escrow se crea y libera correctamente
- [ ] Partial release funciona (30% on submit)
- [ ] Platform fee se deduce correctamente (8%)
- [ ] Reputación se actualiza post-approval
- [ ] Timeout refund funciona
