# NOW-198: Tests para x402 Escrow

**Prioridad**: P1
**Status**: TODO
**Archivo**: `mcp_server/tests/test_escrow.py` (crear)

## Descripción

Tests para el módulo de escrow que maneja depósitos, releases y refunds usando x402-rs.

## Dependencias

- NOW-021: Escrow deposit en publish_task
- NOW-022: Escrow release en approve_submission
- NOW-023: Refund en cancel_task
- NOW-024: x402 SDK client

## Tests a Implementar

### Deposit Tests
- `test_deposit_creates_escrow` - Deposit crea registro en DB
- `test_deposit_requires_valid_amount` - Valida monto mínimo
- `test_deposit_emits_event` - Emite evento de depósito
- `test_deposit_with_agent_bond` - Incluye bond del agent

### Release Tests
- `test_release_full_amount` - Release completo al worker
- `test_release_with_platform_fee` - Deduce fee (6-8%)
- `test_release_calculates_net_correctly` - Math de fees
- `test_release_requires_approval` - Solo si submission aprobada
- `test_release_updates_escrow_status` - Actualiza DB

### Partial Release Tests
- `test_partial_release_on_submission` - 30-50% al submit
- `test_partial_release_tracking` - Track montos parciales
- `test_final_release_after_partial` - Completa el resto

### Refund Tests
- `test_refund_on_cancel` - Refund cuando task cancelada
- `test_refund_on_timeout` - Refund por timeout
- `test_refund_minus_partial` - Resta lo ya liberado
- `test_refund_requires_valid_status` - Solo si cancellable

### Error Cases
- `test_deposit_fails_insufficient_balance` - Sin fondos
- `test_release_fails_already_released` - Double release
- `test_refund_fails_already_completed` - Task ya completada

## Template de Test

```python
"""
Tests for x402 Escrow module.
"""

import pytest
from unittest.mock import AsyncMock, patch
from decimal import Decimal

from ..integrations.x402.escrow import (
    EscrowManager,
    create_escrow_deposit,
    release_escrow,
    refund_escrow,
    partial_release,
)


class TestEscrowDeposit:
    """Tests for escrow deposit."""

    @pytest.fixture
    def escrow_manager(self):
        return EscrowManager()

    @pytest.mark.asyncio
    async def test_deposit_creates_escrow(self, escrow_manager):
        """Deposit should create escrow record."""
        result = await escrow_manager.create_deposit(
            task_id="task-123",
            agent_id="agent-456",
            amount=Decimal("10.00"),
            token="USDC",
        )

        assert result.status == "deposited"
        assert result.amount == Decimal("10.00")

    # ... more tests


class TestEscrowRelease:
    """Tests for escrow release."""

    @pytest.mark.asyncio
    async def test_release_with_platform_fee(self, escrow_manager):
        """Release should deduct platform fee."""
        # Setup: Create deposit first
        await escrow_manager.create_deposit(
            task_id="task-123",
            agent_id="agent-456",
            amount=Decimal("100.00"),
            token="USDC",
        )

        # Release
        result = await escrow_manager.release(
            task_id="task-123",
            worker_wallet="0xworker...",
            platform_fee_percent=8,
        )

        assert result.worker_amount == Decimal("92.00")  # 100 - 8%
        assert result.platform_fee == Decimal("8.00")
```

## Ejecución

```bash
pytest tests/test_escrow.py -v
```
