# NOW-220: x402r + ERC-8004 Production Integration

## Metadata
- **Prioridad**: P0 (CRITICO)
- **Estado**: IMPLEMENTADO
- **Fecha**: 2026-01-30

## Resumen

Implementación de dos sistemas críticos para Chamba en producción:

1. **x402r (Pagos)**: x402 con refunds trustless en Base Mainnet
2. **ERC-8004 (Reputación)**: Identidad y feedback bidireccional en Ethereum Mainnet

Ambos sistemas usan el **Facilitator de Ultravioleta DAO** directamente (sin wrappers innecesarios).

## Decisión de Arquitectura

### Por qué x402r en lugar de ChambaEscrow

| Aspecto | ChambaEscrow (custom) | x402r (Facilitator) |
|---------|----------------------|---------------------|
| Madurez | Nuevo, no auditado | Probado en producción |
| Riesgo | Alto - contrato propio | Bajo - sistema existente |
| Complejidad | Alta - deploy y mantener | Baja - solo integrar |
| Tiempo a producción | Semanas | Inmediato |

**Decisión**: Usar x402r para producción inmediata. Mantener ChambaEscrow listo para el futuro.

### Por qué ERC-8004 via Facilitator

| Aspecto | Directo On-Chain | Via Facilitator |
|---------|-----------------|-----------------|
| Gas fees | Chamba paga | Facilitator paga |
| Complejidad | Alta (web3 + keys) | Baja (HTTP API) |
| Transacciones | Manejar nonces, retry | Automático |
| Producción | Requiere infraestructura | Inmediato |

**Decisión**: Usar Facilitator para todas las operaciones ERC-8004.

---

## Arquitectura General

```
                           CHAMBA ARCHITECTURE (2026-01-30)

┌─────────────────────────────────────────────────────────────────────────────┐
│                              AI AGENT                                       │
└─────────────────────────────┬───────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CHAMBA MCP SERVER                                   │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐    │
│  │   Tasks     │  │  Submissions │  │  Reputation │  │    Escrow      │    │
│  │  /api/v1/   │  │   /api/v1/   │  │  /api/v1/   │  │   /api/v1/     │    │
│  │   tasks     │  │  submissions │  │  reputation │  │    escrow      │    │
│  └─────────────┘  └──────────────┘  └──────┬──────┘  └───────┬────────┘    │
│                                            │                  │             │
└────────────────────────────────────────────┼──────────────────┼─────────────┘
                                             │                  │
                    ┌────────────────────────┼──────────────────┼─────────────┐
                    │                        │                  │             │
                    ▼                        ▼                  ▼             │
           ┌────────────────┐       ┌───────────────┐   ┌─────────────┐      │
           │   FACILITATOR  │       │   FACILITATOR │   │  FACILITATOR│      │
           │    /settle     │       │   /feedback   │   │   (future)  │      │
           └───────┬────────┘       └───────┬───────┘   └─────────────┘      │
                   │                        │                                 │
                   │                        │                                 │
                   ▼                        ▼                                 │
┌──────────────────────────────┐  ┌──────────────────────────────────────────┤
│       BASE MAINNET           │  │           ETHEREUM MAINNET               │
│  ┌─────────────────────────┐ │  │  ┌────────────────────────────────────┐  │
│  │ Escrow Contract         │ │  │  │ Identity Registry                  │  │
│  │ 0xC409e6da89E54253...   │ │  │  │ 0x8004A169FB4a3325...              │  │
│  │                         │ │  │  │                                    │  │
│  │  • deposits             │ │  │  │  • Agent #469 (Chamba)             │  │
│  │  • release()            │ │  │  │  • agentURI → IPFS                 │  │
│  │  • refundInEscrow()     │ │  │  │  • services metadata               │  │
│  └─────────────────────────┘ │  │  └────────────────────────────────────┘  │
│                              │  │                                          │
│  ┌─────────────────────────┐ │  │  ┌────────────────────────────────────┐  │
│  │ DepositRelayFactory     │ │  │  │ Reputation Registry                │  │
│  │ 0x41Cc4D337FEC5E91...   │ │  │  │ 0x8004BAa17C55a88189...            │  │
│  │                         │ │  │  │                                    │  │
│  │  • proxy for Chamba     │ │  │  │  • Agent ← Worker feedback         │  │
│  │  • deterministic addr   │ │  │  │  • Worker ← Agent feedback         │  │
│  └─────────────────────────┘ │  │  │  • Bidirectional reputation        │  │
│                              │  │  └────────────────────────────────────┘  │
└──────────────────────────────┘  └──────────────────────────────────────────┘
```

---

## x402r Escrow (Base Mainnet)

### Contratos

| Contract | Address |
|----------|---------|
| DepositRelayFactory | `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814` |
| Escrow | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |

### Setup (Una sola vez)

```bash
# 1. Registrar Chamba como Merchant
cd scripts
npx tsx register_x402r_merchant.ts --network=base

# 2. Configurar .env.local
X402R_NETWORK=base
X402R_MERCHANT_ADDRESS=0x...  # Tu wallet
X402R_PROXY_ADDRESS=0x...      # Proxy del Factory
WALLET_PRIVATE_KEY=0x...       # Para firmar release/refund
```

### API Endpoints

| Endpoint | Method | Auth | Descripción |
|----------|--------|------|-------------|
| `/api/v1/escrow/config` | GET | No | Configuración del escrow |
| `/api/v1/escrow/payment-extension` | GET | No | Extension para pagos x402 |
| `/api/v1/escrow/deposits/{id}` | GET | No | Info de un depósito |
| `/api/v1/escrow/balance` | GET | No | Balance en escrow |
| `/api/v1/escrow/release` | POST | Sí | Liberar fondos a worker |
| `/api/v1/escrow/refund` | POST | Sí | Reembolsar a agente |

### Uso en Código

```python
from integrations.x402 import release_payment, refund_payment, get_deposit_info

# Liberar pago a worker
result = await release_payment(
    deposit_id="0x...",
    worker_address="0x...",
    amount=Decimal("10.00")
)
if result.success:
    print(f"Released! TX: {result.tx_hash}")

# Reembolsar a agente
result = await refund_payment(deposit_id="0x...")
if result.success:
    print(f"Refunded {result.amount} USDC to {result.payer}")

# Consultar depósito
deposit = get_deposit_info("0x...")
print(f"State: {deposit.state.name}, Amount: {deposit.amount}")
```

### Documentación para Agentes

Los agentes deben incluir esta extension cuando pagan:

```json
{
  "paymentPayload": {
    "x402Version": 2,
    "accepted": {
      "payTo": "<PROXY_ADDRESS>",
      "amount": "10000000"
    },
    "extensions": {
      "refund": {
        "info": {
          "factoryAddress": "0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814",
          "merchantPayouts": {
            "<PROXY_ADDRESS>": "<MERCHANT_ADDRESS>"
          }
        }
      }
    }
  }
}
```

---

## ERC-8004 Reputation (Ethereum Mainnet)

### Contratos

| Contract | Address |
|----------|---------|
| Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |
| Chamba Agent ID | `469` |

### Feedback Bidireccional

```
┌──────────────────────────────────────────────────────────────┐
│                    BIDIRECTIONAL FEEDBACK                    │
│                                                              │
│    ┌─────────┐        rate_worker()        ┌─────────┐      │
│    │  Agent  │ ─────────────────────────▶  │  Worker │      │
│    │  (AI)   │                             │ (Human) │      │
│    └─────────┘  ◀─────────────────────────  └─────────┘      │
│                        rate_agent()                          │
│                                                              │
│    Both ratings stored on-chain in ERC-8004 Reputation       │
│    Registry on Ethereum Mainnet                              │
└──────────────────────────────────────────────────────────────┘
```

### API Endpoints

| Endpoint | Method | Auth | Descripción |
|----------|--------|------|-------------|
| `/api/v1/reputation/info` | GET | No | Config de ERC-8004 |
| `/api/v1/reputation/chamba` | GET | No | Reputación de Chamba |
| `/api/v1/reputation/chamba/identity` | GET | No | Identidad de Chamba |
| `/api/v1/reputation/agents/{id}` | GET | No | Reputación de un agente |
| `/api/v1/reputation/agents/{id}/identity` | GET | No | Identidad de un agente |
| `/api/v1/reputation/workers/rate` | POST | Sí | Agente califica worker |
| `/api/v1/reputation/agents/rate` | POST | No | Worker califica agente |

### Uso en Código

```python
from integrations.erc8004 import (
    rate_worker,
    rate_agent,
    get_chamba_reputation,
    get_agent_reputation,
    get_agent_info,
)

# Agente califica worker (después de completar tarea)
result = await rate_worker(
    task_id="uuid-del-task",
    score=85,  # 0-100
    worker_address="0x...",
    comment="Great work!",
    proof_tx="0x...",  # TX del pago (opcional, para feedback verificado)
)
if result.success:
    print(f"Feedback on-chain: {result.transaction_hash}")

# Worker califica agente
result = await rate_agent(
    agent_id=469,  # Chamba's agent ID
    task_id="uuid-del-task",
    score=90,
    comment="Clear instructions, fast payment",
)

# Consultar reputación
reputation = await get_chamba_reputation()
print(f"Chamba score: {reputation.score}/100 ({reputation.count} ratings)")

# Consultar identidad de un agente
identity = await get_agent_info(469)
print(f"Agent: {identity.name}, URI: {identity.agent_uri}")
```

---

## Archivos Creados/Modificados

### Nuevos Archivos

```
mcp_server/
├── integrations/
│   ├── x402/
│   │   └── x402r_escrow.py          # Cliente directo para x402r contracts
│   └── erc8004/
│       ├── __init__.py              # Exports actualizados
│       └── facilitator_client.py    # Cliente para ERC-8004 via Facilitator
└── api/
    ├── reputation.py                # API endpoints para ERC-8004
    └── escrow.py                    # API endpoints para x402r
```

### Archivos Modificados

```
mcp_server/
├── main.py                          # Nuevos routers, health checks, root info
├── api/__init__.py                  # Exports de reputation_router, escrow_router
└── integrations/x402/__init__.py    # Exports de x402r

.env.example                         # Variables de x402r
```

---

## Variables de Entorno

```bash
# x402r Escrow (Base Mainnet)
X402R_NETWORK=base                    # base | base-sepolia
X402R_MERCHANT_ADDRESS=0x...          # Tu wallet que recibe pagos
X402R_PROXY_ADDRESS=0x...             # Proxy del Factory
X402R_FACTORY_ADDRESS=0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814
X402R_ESCROW_ADDRESS=0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC
WALLET_PRIVATE_KEY=0x...              # Para firmar release/refund

# ERC-8004 (Ethereum Mainnet)
ERC8004_NETWORK=ethereum              # ethereum | ethereum-sepolia
CHAMBA_AGENT_ID=469                   # Chamba's registered agent ID
X402_FACILITATOR_URL=https://facilitator.ultravioletadao.xyz
```

---

## Health Check

El endpoint `/health` ahora incluye:

```json
{
  "status": "healthy",
  "services": {
    "supabase": "healthy",
    "mcp_http": "healthy",
    "websocket": "healthy",
    "x402": "healthy",
    "x402r_escrow": "healthy",    // NEW: Base Mainnet escrow
    "erc8004": "healthy"          // NEW: Ethereum Mainnet reputation
  }
}
```

---

## Checklist de Producción

### x402r Escrow
- [ ] Registrar merchant en Base Mainnet (`npx tsx scripts/register_x402r_merchant.ts --network=base`)
- [ ] Configurar variables de entorno en producción
- [ ] Verificar proxy address en [Basescan](https://basescan.org)
- [ ] Test de release con cantidad pequeña
- [ ] Test de refund
- [ ] Documentar proxy address para agentes

### ERC-8004 Reputation
- [ ] Verificar Agent #469 en [Etherscan](https://etherscan.io/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432)
- [ ] Test de feedback submission via Facilitator
- [ ] Test de get reputation/identity
- [ ] Integrar rating automático después de task completion

---

## Migración Futura a ChambaEscrow

Cuando queramos control total:

1. Auditar y deployar ChambaEscrow.sol
2. Registrar Chamba como merchant en nuestro contrato
3. Cambiar `X402R_ESCROW_ADDRESS` al nuevo contrato
4. Migrar gradualmente los pagos

El código de `escrow.py` (EscrowManager) ya está listo para esto.

---

## Referencias

### x402r
- [x402r Proposal](https://github.com/coinbase/x402/issues/864)
- [x402r Contracts](https://github.com/BackTrackCo/x402r-contracts)
- [Escrow on Basescan](https://basescan.org/address/0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC)

### ERC-8004
- [ERC-8004 Spec](https://ercs.ethereum.org/ERCS/erc-8004)
- [Identity Registry](https://etherscan.io/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432)
- [Reputation Registry](https://etherscan.io/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63)

### Facilitator
- [Facilitator Landing](https://facilitator.ultravioletadao.xyz)
- [API Docs](https://facilitator.ultravioletadao.xyz/docs)
