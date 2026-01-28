# NOW-081: End-to-End Test Suite

## Status: PENDING
## Priority: P1

## Objetivo

Tests E2E que verifican el flujo completo:
1. Agent crea task
2. Worker aplica
3. Worker es asignado
4. Worker sube evidencia
5. Validator valida
6. Pago se ejecuta

## Ubicación

`mcp_server/tests/e2e/` (a crear)

## Tests Requeridos

### test_e2e_task_lifecycle.py

```python
"""
E2E: Complete task lifecycle
"""
import pytest
from httpx import AsyncClient

@pytest.mark.e2e
async def test_full_task_flow():
    """Test complete flow: create -> assign -> submit -> validate -> pay"""

    # 1. Create task
    task = await create_task(
        task_type="physical_presence",
        bounty_usdc=5.00,
        location={"lat": 4.7110, "lng": -74.0721}
    )
    assert task["status"] == "open"

    # 2. Worker applies
    application = await apply_to_task(
        task_id=task["id"],
        worker_wallet="0x..."
    )
    assert application["status"] == "pending"

    # 3. Assign worker
    assignment = await assign_worker(
        task_id=task["id"],
        worker_id=application["worker_id"]
    )
    assert assignment["status"] == "assigned"

    # 4. Submit evidence
    submission = await submit_evidence(
        task_id=task["id"],
        evidence={
            "photo_url": "https://...",
            "gps": {"lat": 4.7110, "lng": -74.0721},
            "timestamp": "2026-01-25T12:00:00Z"
        }
    )
    assert submission["status"] == "submitted"

    # 5. Validate (auto or manual)
    validation = await validate_submission(
        submission_id=submission["id"],
        vote="approve"
    )
    assert validation["consensus_reached"] == True

    # 6. Verify payment
    payment = await get_payment_status(task_id=task["id"])
    assert payment["status"] == "completed"
```

### test_e2e_websocket.py

```python
"""
E2E: WebSocket real-time updates
"""
import pytest
import websockets

@pytest.mark.e2e
async def test_websocket_task_updates():
    """Test real-time updates via WebSocket"""

    async with websockets.connect("ws://localhost:8000/ws") as ws:
        # Subscribe to task updates
        await ws.send('{"type": "subscribe", "channel": "tasks"}')

        # Create task in another connection
        task = await create_task(...)

        # Receive update
        msg = await ws.recv()
        assert msg["type"] == "task_created"
        assert msg["task_id"] == task["id"]
```

### test_e2e_x402_payment.py

```python
"""
E2E: x402 payment flow
"""
import pytest

@pytest.mark.e2e
async def test_x402_escrow_and_release():
    """Test x402 escrow deposit and release"""

    # 1. Create escrow
    escrow = await create_escrow(
        amount_usdc=10.00,
        worker_address="0x...",
        agent_address="0x..."
    )
    assert escrow["status"] == "funded"

    # 2. Complete task
    await complete_task(task_id=escrow["task_id"])

    # 3. Release payment
    release = await release_escrow(escrow_id=escrow["id"])
    assert release["status"] == "released"
    assert release["worker_received"] > 0
```

## Ejecutar E2E Tests

```bash
# Requiere servicios corriendo
docker-compose up -d

# Ejecutar solo E2E
pytest tests/e2e/ -v -m e2e

# Con coverage
pytest tests/e2e/ -v -m e2e --cov=.
```

## Configuración

### conftest.py

```python
import pytest
import os

@pytest.fixture(scope="session")
def api_url():
    return os.getenv("TEST_API_URL", "http://localhost:8000")

@pytest.fixture(scope="session")
def test_wallet():
    """Test wallet with testnet funds"""
    return {
        "address": "0x...",
        "private_key": os.getenv("TEST_WALLET_KEY")
    }
```

### pytest.ini

```ini
[pytest]
markers =
    e2e: End-to-end tests (require running services)
    integration: Integration tests
    unit: Unit tests
```

## Coverage Target

- E2E: 5 critical flows
- Integration: 20+ scenarios
- Unit: 90%+ coverage
