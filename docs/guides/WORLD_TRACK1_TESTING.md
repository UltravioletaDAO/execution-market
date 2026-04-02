---
date: 2026-04-02
tags:
  - type/guide
  - domain/identity
  - domain/integrations
status: active
---

# Track 1: AgentKit — Guia de Pruebas

> Como probar la integracion completa de World AgentKit con Execution Market.
> Cubre: AgentBook on-chain, AgentKit x402 gateway, dashboard badge, tests.

---

## 1. Pre-requisitos

- [ ] Migracion `084_world_agentkit.sql` aplicada en Supabase
- [ ] `BASE_RPC_URL` configurada (ya existe en ECS y .env.local)
- [ ] Node.js instalado (para correr el AgentKit server)
- [ ] `cd scripts && npm install` ejecutado (deps de AgentKit ya en package.json)

**NO necesitas**: World Developer Portal, signing keys, ni World App para Track 1. Solo se necesita para Track 2.

---

## 2. Tests Automatizados

```bash
cd mcp_server

# Solo Track 1 (12 tests)
pytest -m agentkit -v

# Esperado:
# test_lookup_human_verified .............. PASSED
# test_lookup_human_not_verified .......... PASSED
# test_lookup_human_rpc_error_returns ..... PASSED
# test_is_human_shortcut ................. PASSED
# test_is_human_shortcut_returns_false ... PASSED
# test_encode_address_lowercase .......... PASSED
# test_encode_address_already_lowercase .. PASSED
# test_to_dict_converts_enum ............. PASSED
# test_to_dict_error_status .............. PASSED
# test_to_dict_not_verified_status ....... PASSED
# test_feature_flag_off_skips_lookup ..... PASSED
# test_feature_flag_on_triggers_lookup ... PASSED
# 12 passed
```

---

## 3. Probar AgentBook On-Chain (API del MCP Server)

### 3.1 Verificar wallet no registrada

```bash
curl "https://api.execution.market/api/v1/workers/world-status?wallet=0x0000000000000000000000000000000000000000"
```

**Esperado**:
```json
{
  "success": true,
  "data": {
    "status": "not_verified",
    "human_id": 0,
    "wallet_address": "0x0000000000000000000000000000000000000000",
    "error": null
  }
}
```

### 3.2 Verificar wallet registrada (si tienes una)

```bash
curl "https://api.execution.market/api/v1/workers/world-status?wallet=0xTU_WALLET_REGISTRADA"
```

**Esperado** (si esta registrada en AgentBook):
```json
{
  "success": true,
  "data": {
    "status": "verified",
    "human_id": 42,
    "wallet_address": "0x...",
    "error": null
  }
}
```

### 3.3 Verificar directamente con cast (on-chain)

```bash
cast call 0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4 \
  "lookupHuman(address)(uint256)" \
  0x0000000000000000000000000000000000000000 \
  --rpc-url https://mainnet.base.org
```

**Esperado**: `0` (no registrada)

---

## 4. Probar AgentKit x402 Gateway Server

### 4.1 Iniciar el server

```bash
cd scripts
npx tsx agentkit-server.ts
```

**Esperado**:
```
  ╔══════════════════════════════════════════════════════════╗
  ║  Execution Market — AgentKit x402 Gateway               ║
  ║  Port: 4021                                             ║
  ║  ...                                                     ║
  ╚══════════════════════════════════════════════════════════╝
```

### 4.2 Health check

```bash
curl http://localhost:4021/health
```

**Esperado**:
```json
{
  "status": "ok",
  "service": "execution-market-agentkit",
  "agentkit": true,
  "agentbook_contract": "0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4",
  "network": "base"
}
```

### 4.3 Info endpoint

```bash
curl http://localhost:4021/
```

**Esperado**: JSON con descripcion del servicio, endpoints disponibles, y contratos.

### 4.4 Acceder a tareas protegidas (sin verificacion)

```bash
curl http://localhost:4021/api/v1/verified-tasks
```

**Esperado**: HTTP 402 Payment Required — el server pide pago x402 porque no hay firma de agente verificado.

### 4.5 Verificar worker status (sin verificacion)

```bash
curl http://localhost:4021/api/v1/verified-worker/0x0000000000000000000000000000000000000000
```

**Esperado**: HTTP 402 Payment Required (para bots) o datos del worker (si el agente esta verificado en AgentBook y firma con CAIP-122).

---

## 5. Registrar una Wallet en AgentBook

Para que un agente/worker sea reconocido como humano verificado:

```bash
npx @worldcoin/agentkit-cli register 0xTU_WALLET
```

**Flujo**:
1. El CLI muestra un QR code
2. Abre World App en tu telefono
3. Escanea el QR
4. World App verifica tu World ID (requiere verificacion previa con Orb o Device)
5. La wallet se registra en el contrato AgentBook en Base (gasless)
6. Ahora `lookupHuman(wallet)` retorna un `humanId > 0`

**Verificar despues del registro**:
```bash
curl "https://api.execution.market/api/v1/workers/world-status?wallet=0xTU_WALLET"
# Debe retornar status: "verified", human_id > 0
```

---

## 6. Probar el Dashboard (Badge)

1. Abre `https://execution.market`
2. Conecta una wallet que este registrada en AgentBook
3. Aplica a una tarea
4. En el modal de aplicacion, debe aparecer un badge verde "Verified Human" junto a tu perfil
5. En las cards de agentes (AgentMiniCard), el badge tambien debe aparecer

**Si no aparece**: La wallet no esta registrada en AgentBook, o el `world_human_id` no se ha guardado en la DB. Aplica a una tarea primero (el lookup se hace automaticamente en `apply_to_task()`).

---

## 7. Probar Enrichment en apply_to_task

Cuando un worker aplica a una tarea, el backend automaticamente:
1. Lee `lookupHuman(wallet)` del contrato AgentBook
2. Si el worker esta verificado, guarda `world_human_id` en la tabla `executors`
3. La respuesta de la aplicacion incluye `world_verified: true`

```bash
# Aplicar a una tarea (requiere autenticacion)
curl -X POST "https://api.execution.market/api/v1/tasks/TASK_ID/apply" \
  -H "Content-Type: application/json" \
  -H "Signature: ..." \
  -H "Signature-Input: ..." \
  -d '{"message": "I can do this task"}'
```

**Verificar en DB**:
```sql
SELECT id, wallet_address, world_human_id, world_verified_at
FROM executors
WHERE wallet_address = '0xTU_WALLET';
```

---

## 8. Feature Flags

| Flag | Default | Que controla |
|------|---------|-------------|
| `feature.world_agentkit_enabled` | `true` | Lookup de AgentBook en apply_to_task |
| `feature.world_agentkit_priority_boost` | `true` | Prioridad visual para humanos verificados |

**Para deshabilitar** (si algo falla):
```sql
UPDATE platform_config
SET value = 'false'
WHERE key = 'feature.world_agentkit_enabled';
```

---

## 9. Resumen de Endpoints

| Endpoint | Server | Proteccion |
|----------|--------|------------|
| `GET /api/v1/workers/world-status?wallet=` | MCP (Python, :8000) | Ninguna — lookup publico |
| `GET /health` | AgentKit Gateway (:4021) | Ninguna |
| `GET /` | AgentKit Gateway (:4021) | Ninguna — info |
| `GET /api/v1/verified-tasks` | AgentKit Gateway (:4021) | x402 + AgentKit (humanos gratis, bots pagan) |
| `GET /api/v1/verified-worker/:wallet` | AgentKit Gateway (:4021) | x402 + AgentKit (free para humanos) |

---

## 10. Archivos Clave

| Archivo | Que es |
|---------|--------|
| `mcp_server/integrations/world/agentbook.py` | Lectura on-chain de AgentBook via JSON-RPC |
| `scripts/agentkit-server.ts` | Gateway x402 + `@worldcoin/agentkit` SDK |
| `mcp_server/api/routers/workers.py` | Enrichment en apply_to_task + endpoint /world-status |
| `dashboard/src/components/agents/WorldHumanBadge.tsx` | Badge verde "Verified Human" |
| `mcp_server/tests/test_world_agentkit.py` | 12 tests automatizados |
| `supabase/migrations/084_world_agentkit.sql` | Columnas world_human_id, world_verified_at |
| `mcp_server/config/platform_config.py` | Feature flags |

---

## 11. Troubleshooting

| Problema | Causa | Solucion |
|----------|-------|----------|
| `/world-status` retorna `status: error` | RPC de Base no responde | Verificar `BASE_RPC_URL` en env |
| Badge no aparece en dashboard | Worker no ha aplicado a ninguna tarea | El lookup se hace en `apply_to_task()`. Aplicar a una tarea primero |
| AgentKit server no arranca | Deps no instaladas | `cd scripts && npm install` |
| `402 Payment Required` en gateway | Agente no verificado en AgentBook | Registrar: `npx @worldcoin/agentkit-cli register <wallet>` |
| `lookupHuman` retorna 0 para wallet registrada | TX de registro aun no confirmada | Esperar ~15s y reintentar |
| Tests fallan con import error | Ejecutar desde directorio incorrecto | `cd mcp_server && pytest -m agentkit -v` |
