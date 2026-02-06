# Execution Market — System Map & Facilitator Gap Analysis
## 2026-02-06 (Updated after deep scan of facilitator + SDKs)

## 1. Principio Arquitectonico

> **El agente solo paga el bounty. Todo lo demas lo paga el facilitador Ultravioleta.**
> Todo en Base Mainnet. Sin excepciones.

---

## 2. Inventario de los Tres Repositorios

### 2.1 Facilitador (x402-rs) — FUENTE DORADA

**Repo**: `/mnt/z/ultravioleta/dao/x402-rs`
**Stack**: Rust + Axum + Alloy + Tokio
**URL**: `https://facilitator.ultravioletadao.xyz`

**Endpoints de Pago:**
| Metodo | Path | Descripcion | Gas |
|--------|------|-------------|-----|
| POST | `/verify` | Verificar firma EIP-3009 (sin mover fondos) | Sin gas |
| POST | `/settle` | Ejecutar transferencia on-chain | Facilitador paga |
| GET | `/supported` | Listar payment kinds por red | N/A |
| GET | `/health` | Health check | N/A |

**Endpoints ERC-8004 Identity:**
| Metodo | Path | Descripcion | Tipo |
|--------|------|-------------|------|
| GET | `/identity/{network}/{agent_id}` | Consultar identidad de agente | READ-ONLY |

**Endpoints ERC-8004 Reputation:**
| Metodo | Path | Descripcion | Gas |
|--------|------|-------------|-----|
| GET | `/reputation/{network}/{agent_id}` | Consultar reputacion | Sin gas |
| POST | `/feedback` | Enviar feedback | Facilitador paga |
| POST | `/feedback/revoke` | Revocar feedback | Facilitador paga |
| POST | `/feedback/response` | Responder a feedback | Facilitador paga |

**Redes soportadas**: 32 total (19 mainnets + 13 testnets)
**ERC-8004 en**: 12 redes (7 mainnets + 5 testnets)
**Tokens**: USDC (todas), AUSD, EURC, USDT, PYUSD

**HALLAZGO CRITICO**: El facilitador es **READ-ONLY** para Identity Registry.
NO tiene endpoint para registrar agentes. Solo lee (`ownerOf`, `tokenURI`, `getAgentWallet`).
Registrar un agente requiere llamada directa al contrato `registerAgent()`.

### 2.2 Python SDK (uvd-x402-sdk v0.6.0)

**Repo**: `/mnt/z/ultravioleta/dao/uvd-x402-sdk-python`
**Paquete**: `uvd-x402-sdk[fastapi]>=0.6.0`

**Clases principales:**

| Clase | Modulo | Proposito |
|-------|--------|-----------|
| `X402Client` | `client.py` | Pagos: verify, settle, process_payment |
| `Erc8004Client` | `erc8004.py` | Identity + Reputation (async) |
| `EscrowClient` | `escrow.py` | Escrow + Refund + Disputes (async) |
| `AdvancedEscrowClient` | `advanced_escrow.py` | On-chain PaymentOperator (Base) |
| `FastAPIX402` | `integrations/` | Middleware FastAPI |

**Erc8004Client API:**
- `get_identity(network, agent_id)` → `AgentIdentity`
- `get_reputation(network, agent_id, tag1, tag2, include_feedback)` → `ReputationResponse`
- `submit_feedback(network, agent_id, value, tags, proof)` → `FeedbackResponse`
- `revoke_feedback(network, agent_id, feedback_index)` → `FeedbackResponse`
- `append_response(network, agent_id, feedback_index, response)` → `FeedbackResponse`
- `get_contracts(network)` → `Erc8004ContractAddresses`
- `is_available(network)` → `bool`
- `resolve_agent_uri(uri)` → `AgentRegistrationFile`

**EscrowClient API (GASLESS REFUND!):**
- `create_escrow(payment_header, requirements, duration)` → `EscrowPayment`
- `get_escrow(escrow_id)` → `EscrowPayment`
- `release(escrow_id)` → `EscrowPayment`
- `request_refund(escrow_id, reason, amount, evidence)` → `RefundRequest`
- `approve_refund(refund_id, amount)` → `RefundRequest`
- `reject_refund(refund_id, reason)` → `RefundRequest`
- `get_refund(refund_id)` → `RefundRequest`
- `open_dispute(escrow_id, reason, evidence)` → Dispute
- `health_check()` → Health

**Redes**: 21 (13 EVM + 2 SVM + NEAR + Stellar + 2 Algorand + 2 Sui)

### 2.3 TypeScript SDK (uvd-x402-sdk v2.19.0)

**Repo**: `/mnt/z/ultravioleta/dao/uvd-x402-sdk-typescript`
**Paquete**: `uvd-x402-sdk`

**Exports principales:**

| Export | Clases | Proposito |
|--------|--------|-----------|
| `uvd-x402-sdk` | `X402Client` | Client-side wallet + payments |
| `uvd-x402-sdk/backend` | `FacilitatorClient`, `EscrowClient`, `Erc8004Client`, `BazaarClient` | Server-side |
| `uvd-x402-sdk/react` | `X402Provider`, hooks | React integration |
| `uvd-x402-sdk/wagmi` | `createPaymentFromWalletClient` | Wagmi adapter |
| `uvd-x402-sdk/evm` | `EVMProvider` | EVM wallets |

**Erc8004Client API (TS):**
- `getIdentity(network, agentId)` → `AgentIdentity`
- `getReputation(network, agentId, options)` → `ReputationResponse`
- `submitFeedback(request)` → `FeedbackResponse`
- `revokeFeedback(network, agentId, feedbackIndex)` → `FeedbackResponse`
- `resolveAgentUri(agentUri)` → `AgentRegistrationFile`

**EscrowClient API (TS):**
- `createEscrow(options)` → `EscrowPayment`
- `getEscrow(escrowId)` → `EscrowPayment`
- `release(escrowId)` → `EscrowPayment`
- `requestRefund(options)` → `RefundRequest`
- `approveRefund(refundId, amount)` → `RefundRequest`
- `rejectRefund(refundId)` → `RefundRequest`

**Redes**: 21 (mismas que Python)

---

## 3. Contratos ERC-8004 (CREATE2 — misma direccion en todas las EVM)

| Contrato | Mainnets | Testnets |
|----------|----------|----------|
| Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` | `0x8004B663056A597Dffe9eCcC1965A193B7388713` |
| Validation Registry | (no usado aun) | `0x8004Cb1BF31DAf7788923b405b754f57acEB4272` |

**NOTA**: CREATE2 = misma direccion en cada red, pero **estado separado por red**.
Agent #469 registrado en Ethereum Mainnet NO existe en Base Mainnet.
Necesita registro separado en Base.

**Redes con ERC-8004 (12):**
- Mainnets: Ethereum, Base, Polygon, Arbitrum, Celo, BSC, Monad
- Testnets: Ethereum Sepolia, Base Sepolia, Polygon Amoy, Arbitrum Sepolia, Celo Sepolia

---

## 4. Mapa Visual del Flujo Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FLUJO COMPLETO DE UNA TAREA                            │
│                                                                             │
│  ┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────┐  │
│  │ AI AGENT │     │ FACILITADOR  │     │   BASE       │     │  WORKER  │  │
│  │          │     │ ULTRAVIOLETA │     │   MAINNET    │     │          │  │
│  └────┬─────┘     └──────┬───────┘     └──────┬───────┘     └────┬─────┘  │
│       │                  │                     │                  │         │
│  ═══ REGISTRO (una vez) ═══                    │                  │         │
│       │                  │                     │                  │         │
│  1.   │──registerAgent()─┼─────────────────────>│                  │         │
│       │  (directo, paga gas ~$0.01 en Base)    │                  │         │
│       │                  │                     │                  │         │
│       │                  │                     │             2.   │         │
│       │                  │                     │<──registerAgent()─│         │
│       │                  │                     │  (directo, paga gas)       │
│       │                  │                     │                  │         │
│  ═══ CREAR TAREA ═══     │                     │                  │         │
│       │                  │                     │                  │         │
│  3.   │─ firma EIP-3009 ─>│                     │                  │         │
│       │  X-Payment header│                     │                  │         │
│       │                  │── verify ──────────>│                  │         │
│       │  ✅ verificado   │<────────────────────│                  │         │
│       │  (sin gas, sin   │                     │                  │         │
│       │   mover fondos)  │                     │                  │         │
│       │                  │                     │                  │         │
│  ═══ WORKER EJECUTA ═══  │                     │                  │         │
│       │                  │                     │                  │         │
│       │                  │                     │             4.   │         │
│       │                  │                     │  aplica (Supabase, sin gas)│
│       │                  │                     │             5.   │         │
│       │                  │                     │  sube evidencia (off-chain)│
│       │                  │                     │                  │         │
│  ═══ APROBAR + PAGAR ═══ │                     │                  │         │
│       │                  │                     │                  │         │
│  6.   │── settle ────────>│                     │                  │         │
│       │                  │── transferWithAuth──>│                  │         │
│       │                  │   (facilit. paga gas)│── USDC ────────>│         │
│       │  ✅ tx_hash      │<────────────────────│                  │         │
│       │                  │                     │                  │         │
│  ═══ REPUTACION ═══      │                     │                  │         │
│       │                  │                     │                  │         │
│  7.   │── POST /feedback─>│                     │                  │         │
│       │  (agente califica │── giveFeedback ────>│                  │         │
│       │   al worker)     │   (facilit. paga gas)│                  │         │
│       │                  │                     │                  │         │
│       │                  │                     │             8.   │         │
│       │                  │<── POST /feedback ──┼──────────────────│         │
│       │                  │── giveFeedback ────>│  (worker califica│         │
│       │                  │   (facilit. paga gas)│   al agente)    │         │
│       │                  │                     │                  │         │
│  ═══ CANCELAR (alt) ═══  │                     │                  │         │
│       │                  │                     │                  │         │
│  9.   │── requestRefund ─>│                     │                  │         │
│       │  (via EscrowClient)── refund ─────────>│                  │         │
│       │  ✅ refund_tx    │   (facilit. paga gas)│                  │         │
│       │                  │<────────────────────│                  │         │
│       │                  │                     │                  │         │
│  └────┴──────────────────┴─────────────────────┴──────────────────┘         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Matriz de Estado Actualizada (Post Deep Scan)

```
┌───┬──────────────────────────────────┬────────────────────┬─────────────┬──────────┐
│ # │ OPERACION                        │ IMPLEMENTACION     │ GAS         │ ESTADO   │
├───┼──────────────────────────────────┼────────────────────┼─────────────┼──────────┤
│ 1 │ Verificar pago (task create)     │ SDK verify()       │ Facilitador │ ✅ OK    │
│ 2 │ Liquidar pago (approve)          │ SDK settle()       │ Facilitador │ ✅ OK    │
│ 3 │ Agente → califica worker         │ Facilitador        │ Facilitador │ ✅ OK    │
│ 4 │ Worker → califica agente         │ Facilitador        │ Facilitador │ ✅ Sin UI│
│ 5 │ Consultar identidad/reputacion   │ Facilitador        │ N/A (read)  │ ✅ OK    │
├───┼──────────────────────────────────┼────────────────────┼─────────────┼──────────┤
│ 6 │ Refund (cancel task)             │ x402r_escrow.py    │ ⚠ AGENTE   │ ❌ FIX   │
│   │                                  │ DEBE SER:          │             │          │
│   │                                  │ EscrowClient.      │ Facilitador │          │
│   │                                  │ request_refund()   │             │          │
├───┼──────────────────────────────────┼────────────────────┼─────────────┼──────────┤
│ 7 │ Registrar agente en ERC-8004     │ registerAgent()    │ Agente paga │ ⚠ NOTA   │
│   │ (Base Mainnet)                   │ directo contrato   │ ~$0.01 Base │          │
├───┼──────────────────────────────────┼────────────────────┼─────────────┼──────────┤
│ 8 │ Registrar worker en ERC-8004     │ NO EXISTE          │ Worker paga │ ❌ CREAR │
│   │ (Base Mainnet)                   │                    │ ~$0.01 Base │          │
└───┴──────────────────────────────────┴────────────────────┴─────────────┴──────────┘

RESUMEN:  5 de 8 operaciones ✅ gasless via facilitador
          1 refund ❌ necesita migracion a EscrowClient (gasless)
          2 registros ⚠ NO son gasless (facilitador NO soporta registro)
```

---

## 6. HALLAZGO CRITICO: Registro en Identity Registry

### El facilitador NO registra agentes

El facilitador (x402-rs) es **READ-ONLY** para el Identity Registry:
- Solo expone `GET /identity/{network}/{agent_id}`
- No tiene `POST /identity` ni `registerAgent()` endpoint
- Los ABIs que carga son solo funciones de lectura: `ownerOf`, `tokenURI`, `getAgentWallet`

### Implicaciones

1. **Registrar Agent #469 en Base** requiere llamada directa al contrato:
   ```solidity
   IdentityRegistry(0x8004A169FB4a3325136EB29fA0ceB6D2e539a432).registerAgent(agentUri)
   ```
   - Costo: ~$0.01 en Base (gas muy barato)
   - Se hace UNA VEZ, no por cada tarea
   - El script `scripts/register_erc8004.ts` ya hace esto (pero en Ethereum Mainnet)

2. **Registrar workers** tambien requiere llamada directa:
   - El worker necesita firmar la transaccion (su wallet es el `msg.sender` = owner del NFT)
   - Opciones: (a) worker paga gas (~$0.01), (b) meta-transaccion donde backend paga gas
   - Ni el facilitador ni los SDKs soportan registro hoy

3. **El gas de registro es minimo** (~$0.01 en Base) y ocurre UNA SOLA VEZ:
   - No es un costo recurrente
   - Comparado con el bounty ($5+), es insignificante
   - Podria subsidiarse desde el backend si se implementa meta-transaccion

---

## 7. Solucion para Refund Gasless

### Actual (INCORRECTO — agente paga gas):
```python
# sdk_client.py → x402r_escrow.py → contrato directo
refund_result = await refund_payment(deposit_id=escrow_id)
# El wallet del agente firma y paga gas
```

### Correcto (usar EscrowClient del SDK):
```python
from uvd_x402_sdk.escrow import EscrowClient

escrow_client = EscrowClient(facilitator_url="https://facilitator.ultravioletadao.xyz")
refund = await escrow_client.request_refund(
    escrow_id=escrow_id,
    reason="Task cancelled by agent",
    amount=bounty_usd
)
# El facilitador paga gas, agente recupera USDC intacto
```

**Ambos SDKs (Python y TypeScript) tienen `EscrowClient.requestRefund()`** que es gasless.

---

## 8. Inconsistencias Facilitador vs SDKs

| Aspecto | Facilitador (x402-rs) | Python SDK (v0.6.0) | TypeScript SDK (v2.19.0) |
|---------|----------------------|---------------------|--------------------------|
| Redes totales | 32 | 21 | 21 |
| ERC-8004 redes | 12 | 12 | 12+ (incl BSC, Monad) |
| Nombre red Base | "base" | "base-mainnet" | "base" |
| Identity registro | NO (read-only) | NO | NO |
| Escrow refund | Via extension x402r | EscrowClient | EscrowClient |
| AdvancedEscrow | PaymentOperator ext | AdvancedEscrowClient | AdvancedEscrowClient |
| Discovery/Bazaar | Endpoints propios | NO | BazaarClient |
| Compliance/OFAC | SI | NO | NO |
| Version mismatch | N/A | v0.6.0 | v2.19.0 |

### Inconsistencia de nombres de red
- Python SDK usa `"base-mainnet"` en `Erc8004Client`
- Facilitador usa `"base"` en rutas `/identity/base/469`
- **Posible bug**: Si el SDK envia "base-mainnet" al facilitador y este espera "base", fallara

### Funcionalidad faltante en SDKs
- Ninguno soporta registro de identidad (no hay `register_agent()`)
- Python SDK no tiene BazaarClient (discovery)
- TypeScript SDK no tiene `append_response` para feedback

---

## 9. Plan de Accion Actualizado

### Fase 0: Fundaciones (corregido post deep-scan)

| Tarea | Descripcion | Mecanismo | Gas |
|-------|-------------|-----------|-----|
| #45 P0-CHAIN-001 | Registrar Agent #469 en Base | Script directo al contrato (como register_erc8004.ts pero para Base) | ~$0.01 (una vez) |
| #46 P0-PAY-008 | Migrar refund a EscrowClient | Reemplazar x402r_escrow.py con SDK EscrowClient.request_refund() | Facilitador |
| #47 P0-INFRA-001 | ECS env vars | Agregar ERC8004_NETWORK=base, EM_AGENT_ID | N/A |

### Fase 1: Flujos Core

| Tarea | Descripcion | Nota |
|-------|-------------|------|
| #17 P0-ERC-001 | Worker identity en Base | Requiere llamada directa al contrato (NO facilitador). Worker paga ~$0.01 o implementar meta-tx |
| #18 P0-ERC-002 | Verificar identity en task creation | Usa GET /identity/{network}/{id} del facilitador (ya funciona) |
| #48 P0-UI-007 | Worker rating UI | Endpoint POST /feedback ya existe, solo falta UI |

### Fase 2: Todo lo demas (tareas #1-44 existentes)

---

## 10. Referencia Rapida de APIs

### Para Execution Market Backend (Python)

```python
# Pago: verificar
from uvd_x402_sdk import X402Client
client = X402Client(recipient_evm=TREASURY, facilitator_url=FACILITATOR)
result = client.verify_payment(payload, amount)  # gasless

# Pago: liquidar
result = client.settle_payment(payload, amount)  # facilitador paga gas

# Pago: refund (CORRECTO — usar EscrowClient)
from uvd_x402_sdk.escrow import EscrowClient
escrow = EscrowClient(facilitator_url=FACILITATOR)
refund = await escrow.request_refund(escrow_id, reason="cancelled")  # gasless

# Reputacion: calificar worker
from uvd_x402_sdk.erc8004 import Erc8004Client
erc = Erc8004Client(facilitator_url=FACILITATOR)
result = await erc.submit_feedback("base", agent_id=469, value=80,
    tag1="worker_rating", proof=proof_of_payment)  # gasless

# Identidad: consultar
identity = await erc.get_identity("base", agent_id=469)  # read-only

# Identidad: registrar (NO hay API — requiere contrato directo)
# Ver scripts/register_erc8004.ts como referencia
```

### Contratos en Base Mainnet

```
Identity Registry: 0x8004A169FB4a3325136EB29fA0ceB6D2e539a432
Reputation Registry: 0x8004BAa17C55a88189AE136b182e5fdA19dE9b63
USDC: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
PaymentOperator (AdvancedEscrow): 0xa06958D93135BEd7e43893897C0d9fA931EF051C
Facilitador EVM Mainnet: 0x103040545AC5031A11E8C03dd11324C7333a13C7
```
