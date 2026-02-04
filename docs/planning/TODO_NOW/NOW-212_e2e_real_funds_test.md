# NOW-212: E2E Test con Fondos Reales (Micro-transacciones)

## Metadata
- **Prioridad**: P0 (CRÍTICO)
- **Fase**: Testing / Production Validation
- **Dependencias**: NOW-202 (x402 SDK), Llave privada con fondos
- **Archivos**: `mcp_server/tests/e2e/`, nuevo script de simulación
- **Razón**: Validar flujo completo antes de lanzar a usuarios reales

## Objetivo
Crear un script que simule el flujo completo de un agente usando Execution Market con pagos reales:

1. Agente descubre Execution Market via A2A Agent Card
2. Agente crea tarea con pago real ($0.25 mínimo para test)
3. Worker (simulado) aplica a la tarea
4. Agent asigna worker
5. Worker submitea evidencia
6. Agent aprueba → pago liberado
7. Verificar que el fee se cobró correctamente

## Flujo de Pago (Clarificación)

```
┌─────────────────────────────────────────────────────────────────┐
│  PASO 1: Agente publica tarea                                   │
│  ─────────────────────────────────────────────────────────────  │
│  • Agente llama POST /api/v1/tasks con X-Payment header         │
│  • x402 SDK valida el pago                                      │
│  • Facilitador recibe: bounty + platform_fee                    │
│  • Escrow record creado en DB con status="funded"               │
│  • Timeout configurado (default: deadline_hours del task)       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PASO 2: Worker completa y submitea                             │
│  ─────────────────────────────────────────────────────────────  │
│  • Worker llama POST /api/v1/tasks/{id}/submit                  │
│  • Sistema valida evidencia requerida                           │
│  • PARTIAL_RELEASE_PCT (30%) liberado inmediatamente al worker  │
│  • Escrow status → "partial_released"                           │
│  • Webhook/notificación enviada al agente                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PASO 3A: Agente aprueba (Happy Path)                           │
│  ─────────────────────────────────────────────────────────────  │
│  • Agent llama POST /api/v1/submissions/{id}/approve            │
│  • Remaining 70% liberado al worker                             │
│  • Platform fee (configurable, default 8%) retenido             │
│  • Escrow status → "released"                                   │
│  • Task status → "completed"                                    │
│                                                                 │
│  CÁLCULO:                                                       │
│  bounty = $1.00                                                 │
│  platform_fee = $1.00 * 8% = $0.08                              │
│  worker_receives = $1.00 - $0.08 = $0.92                        │
│  partial_on_submit = $0.92 * 30% = $0.276                       │
│  final_on_approve = $0.92 * 70% = $0.644                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PASO 3B: Timeout (Agent no responde)                           │
│  ─────────────────────────────────────────────────────────────  │
│  • approval_timeout_hours pasa sin respuesta del agent          │
│  • Automatic: remaining 70% liberado al worker                  │
│  • Platform fee igual se cobra                                  │
│  • Escrow status → "auto_released"                              │
│  • Agent notificado de auto-release                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  PASO 3C: Agent rechaza                                         │
│  ─────────────────────────────────────────────────────────────  │
│  • Agent llama POST /api/v1/submissions/{id}/reject             │
│  • Worker puede re-submitear (max_resubmissions configurable)   │
│  • Si límite alcanzado → dispute o refund parcial               │
│  • Escrow status → "disputed" o "partial_refund"                │
└─────────────────────────────────────────────────────────────────┘
```

## Escenarios de Timeout

| Escenario | Estado | Acción |
|-----------|--------|--------|
| Timeout sin worker asignado | published → expired | 100% refund al agent |
| Timeout con worker asignado pero sin submit | accepted → expired | 100% refund al agent |
| Timeout después de submit sin aprobación | submitted → auto_released | 30% ya al worker, 70% → worker, fee cobrado |

## Script de Test

```python
# tests/e2e/test_real_payment.py

import os
from web3 import Web3
from uvd_x402_sdk import create_payment_header

# NUNCA loggear esto completo
PRIVATE_KEY = os.environ.get("TEST_AGENT_PRIVATE_KEY")
API_BASE = "https://api.execution.market"

async def test_full_lifecycle_with_real_payment():
    """
    E2E test con fondos reales.
    Usa $0.25 (mínimo) para minimizar costos de testing.
    """
    # 1. Crear payment header
    payment = create_payment_header(
        amount_usd=0.27,  # 0.25 bounty + 0.02 fee (8%)
        private_key=PRIVATE_KEY,
        network="base",
        token="USDC"
    )

    # 2. Crear task
    response = await http_client.post(
        f"{API_BASE}/api/v1/tasks",
        headers={
            "X-Payment": payment,
            "Authorization": f"Bearer {API_KEY}"
        },
        json={
            "title": "E2E Test Task",
            "instructions": "This is an automated test. Respond with 'test_complete'.",
            "category": "simple_action",
            "bounty_usd": 0.25,
            "deadline_hours": 1,
            "evidence_required": ["text_response"]
        }
    )
    assert response.status_code == 201
    task_id = response.json()["id"]

    # 3. Simular worker apply + assign + submit + approve
    # ... (ver implementación completa)

    # 4. Verificar balance final
    # Agent gastó: $0.27
    # Worker recibió: $0.25 * 0.92 = $0.23
    # Platform fee: $0.25 * 0.08 = $0.02
```

## Requisitos

1. **Llave privada con fondos** (desde AWS Secrets Manager)
2. **Mínimo $5 USDC en Base** para múltiples tests
3. **Worker wallet** para recibir pagos
4. **Logging seguro** (nunca mostrar keys completas)

## Acceptance Criteria

- [x] Script lee private key de AWS Secrets Manager
- [x] Crea tarea con pago real de $0.25
- [x] Simula todo el lifecycle
- [x] Verifica que el fee se cobró correctamente
- [x] Logs no muestran información sensible
- [x] Test es reproducible

## Implementación (2026-01-27)

**Files Created**:
- `mcp_server/tests/e2e/test_real_payment.py` - E2E test suite with real payments

**Features**:
- Disabled by default (set EXECUTION MARKET_E2E_REAL_PAYMENTS=true to enable)
- Dry run mode (EXECUTION MARKET_E2E_DRY_RUN=true)
- Tests: API health, A2A discovery, public config, 402 payment required
- Fee calculation verification
- Partial release calculation verification
- All sensitive data masked in logs

**Related**:
- `mcp_server/scripts/simulate_agent.py` - Manual simulation script (NOW-215)

## Notas

- Bounty mínimo: $0.25 (configurable via NOW-213)
- Fee actual: 8% (hardcodeado, debe ser configurable via NOW-213)
- El script debe ser idempotente (puede correrse múltiples veces)
