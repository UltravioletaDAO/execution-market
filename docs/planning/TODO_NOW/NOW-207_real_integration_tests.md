# NOW-207: Tests con Datos Reales (No Mocks)

## Metadata
- **Prioridad**: P1
- **Fase**: Testing
- **Dependencias**: NOW-202, NOW-203
- **Archivos**: `mcp_server/tests/`
- **Tiempo estimado**: 2-3 horas

## Descripción
Los tests actuales usan mocks. Crear suite de integration tests que usen:
- Supabase real (puede ser proyecto de test)
- Facilitador real (testnet)
- Datos reales de prueba

## Configuración de Test Environment

### 1. Proyecto Supabase de Test
```bash
# Crear proyecto separado para tests
# O usar Supabase local
supabase start
```

### 2. Variables de Entorno para Tests
```bash
# .env.test
SUPABASE_URL=http://localhost:54321  # Supabase local
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...

# Usar testnet para x402
X402_NETWORK=avalanche-fuji
```

### 3. Fixtures con Datos Reales
```python
# tests/conftest.py
import pytest
from supabase import create_client

@pytest.fixture
async def real_supabase():
    """Conexión real a Supabase"""
    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )
    yield client
    # Cleanup después de tests
    await client.table("tasks").delete().neq("id", "").execute()

@pytest.fixture
async def test_executor(real_supabase):
    """Crear executor real para tests"""
    result = await real_supabase.table("executors").insert({
        "wallet_address": "0x1234...",
        "reputation_score": 50.0,
    }).execute()
    yield result.data[0]
    # Cleanup
    await real_supabase.table("executors").delete().eq("id", result.data[0]["id"]).execute()
```

## Tests de Integración

### test_real_task_lifecycle.py
```python
"""
Test completo del ciclo de vida de una tarea con datos reales
"""
import pytest

@pytest.mark.integration
async def test_full_task_lifecycle(real_supabase, test_executor):
    # 1. Crear tarea
    task = await real_supabase.table("tasks").insert({
        "title": "Integration Test Task",
        "description": "Testing with real data",
        "bounty_usdc": 5.00,
        "category": "physical_presence",
        "status": "published",
    }).execute()

    assert task.data[0]["id"] is not None

    # 2. Worker aplica
    application = await real_supabase.table("applications").insert({
        "task_id": task.data[0]["id"],
        "executor_id": test_executor["id"],
        "status": "pending",
    }).execute()

    assert application.data[0]["status"] == "pending"

    # 3. Agente asigna
    await real_supabase.table("tasks").update({
        "assigned_to": test_executor["id"],
        "status": "assigned",
    }).eq("id", task.data[0]["id"]).execute()

    # 4. Worker envía submission
    submission = await real_supabase.table("submissions").insert({
        "task_id": task.data[0]["id"],
        "executor_id": test_executor["id"],
        "evidence_urls": ["https://example.com/photo.jpg"],
        "status": "pending",
    }).execute()

    assert submission.data[0]["status"] == "pending"

    # 5. Verificar que todo está en DB
    final_task = await real_supabase.table("tasks").select("*").eq("id", task.data[0]["id"]).execute()
    assert final_task.data[0]["status"] == "assigned"
```

### test_real_x402_payment.py
```python
"""
Test de pago x402 con facilitador real (testnet)
"""
import pytest
from uvd_x402_sdk import X402Client, X402Config

@pytest.mark.integration
@pytest.mark.x402
async def test_verify_payment_with_real_facilitator():
    """Verificar que podemos conectar al facilitador"""
    config = X402Config(
        recipient_evm="0xTestRecipient...",
        supported_networks=["avalanche-fuji"],  # Testnet
    )
    client = X402Client(config=config)

    # Verificar conexión al facilitador
    # (no podemos hacer pago real sin wallet fondeada)
    assert client.config.facilitator_url == "https://facilitator.ultravioletadao.xyz"
```

## Ejecutar Tests

```bash
# Solo unit tests (rápidos, con mocks)
pytest tests/ -m "not integration"

# Solo integration tests (lentos, datos reales)
pytest tests/ -m integration

# Todos los tests
pytest tests/

# Con coverage
pytest tests/ --cov=mcp_server --cov-report=html
```

## Criterios de Éxito
- [ ] Tests de integración separados de unit tests
- [ ] Conexión real a Supabase (local o test project)
- [ ] Cleanup automático después de cada test
- [ ] Al menos 5 tests de integración pasando
- [ ] CI puede correr tests de integración

## Markers en pytest.ini
```ini
[pytest]
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"')
    x402: marks tests that require x402 facilitator
    slow: marks tests as slow running
```

## ESTADO: 2026-01-25

### Tests Existentes (Unit Tests)
Ya hay 20 archivos de tests con ~200+ tests que usan mocks:
- test_a2a.py (99 tests)
- test_reputation.py
- test_fraud_detection.py
- test_gps.py, test_gps_antispoofing.py
- test_escrow.py, test_fees.py
- etc.

### Integration Tests: BLOQUEADO
Los integration tests requieren:
1. **Supabase** - Proyecto real o `supabase start` local
2. **x402 Facilitador** - Ya disponible en https://facilitator.ultravioletadao.xyz
3. **Testnet funds** - Para probar pagos en Avalanche Fuji

### Ejecutar Tests Existentes (sin dependencias)
```bash
cd ideas/chamba/mcp_server
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx

# Unit tests (funcionan sin servicios externos)
pytest tests/test_a2a.py tests/test_gps.py tests/test_reputation.py -v
# Resultado esperado: 120+ passed
```

### Próximos Pasos
1. Crear proyecto Supabase (NOW-203)
2. Ejecutar `supabase db push` para migraciones
3. Correr integration tests con `pytest tests/ -m integration`
