---
date: 2026-04-02
tags:
  - type/guide
  - domain/identity
  - domain/testing
status: active
aliases:
  - World Hackathon Testing
  - World Mini Apps Testing Guide
related-files:
  - mcp_server/integrations/world/agentbook.py
  - mcp_server/integrations/worldid/client.py
  - mcp_server/api/routers/workers.py
  - mcp_server/api/routers/worldid.py
  - mcp_server/tests/test_world_agentkit.py
  - mcp_server/tests/test_worldid.py
  - dashboard/src/components/WorldIdVerification.tsx
  - dashboard/src/components/agents/WorldHumanBadge.tsx
  - supabase/migrations/084_world_agentkit.sql
  - supabase/migrations/084_world_id_verification.sql
  - supabase/migrations/085_world_id_rls.sql
---

# Guia de Testing y Demo -- World Hackathon

> Checklist paso a paso para verificar que todo funciona antes de la entrega del hackathon.
> Cubren ambos tracks: **Track 1 (AgentKit / AgentBook)** y **Track 2 (World ID 4.0)**.

---

## 1. Pre-flight Checklist

### Base de datos

- [ ] Migracion `084_world_agentkit.sql` aplicada -- agrega columnas `world_human_id` y `world_verified_at` a `executors`
- [ ] Migracion `084_world_id_verification.sql` aplicada -- crea tabla `world_id_verifications` con constraints `uq_world_id_nullifier` y `uq_world_id_executor`
- [ ] Migracion `085_world_id_rls.sql` aplicada -- habilita RLS en `world_id_verifications`

Verificar en Supabase SQL Editor:

```sql
-- Debe retornar las columnas world_human_id y world_verified_at
SELECT column_name FROM information_schema.columns
WHERE table_name = 'executors' AND column_name LIKE 'world%';

-- Debe retornar la tabla
SELECT tablename FROM pg_tables WHERE tablename = 'world_id_verifications';

-- Debe retornar true
SELECT rowsecurity FROM pg_tables WHERE tablename = 'world_id_verifications';
```

### Variables de entorno (backend)

- [ ] `BASE_RPC_URL` -- RPC de Base Mainnet (QuikNode preferido, fallback: `https://mainnet.base.org`)
- [ ] `WORLD_ID_APP_ID` -- App ID del World Developer Portal (formato `app_XXXXXXXX`)
- [ ] `WORLD_ID_RP_ID` -- RP ID del World Developer Portal
- [ ] `WORLD_ID_SIGNING_KEY` -- Clave de firma RP (hex, 32 bytes). **Solo en `.env.local` o AWS Secrets Manager, NUNCA en codigo**
- [ ] `EM_WORLD_ID_ENABLED` -- Debe ser `true` (default es `true`, verificar que no este en `false`)

Verificar que existen (sin mostrar valores):

```bash
# En el servidor o container
echo "BASE_RPC_URL is ${BASE_RPC_URL:+set}"
echo "WORLD_ID_APP_ID is ${WORLD_ID_APP_ID:+set}"
echo "WORLD_ID_RP_ID is ${WORLD_ID_RP_ID:+set}"
echo "WORLD_ID_SIGNING_KEY is ${WORLD_ID_SIGNING_KEY:+set}"
```

### Dependencias Python (backend)

- [ ] `coincurve` instalado -- firma secp256k1 para RP signatures
- [ ] `pycryptodome` instalado -- keccak256 para hashing
- [ ] `httpx` instalado -- llamadas HTTP async (ya es dependencia existente)

Verificar:

```bash
cd mcp_server
pip install -e . && python -c "import coincurve; print('coincurve OK')"
python -c "from Crypto.Hash import keccak; print('pycryptodome OK')"
```

### Dependencias Dashboard (frontend)

- [ ] `@worldcoin/idkit` v4+ instalado (actualmente `^4.0.11` en `package.json`)

Verificar:

```bash
cd dashboard
npm ls @worldcoin/idkit
```

### Dispositivo / Simulador

- [ ] World App instalada en celular (iOS o Android)
- [ ] **O** Simulador de World ID configurado para testing
- [ ] Cuenta de World ID con Orb verification (necesaria para el flujo completo de Track 2)

---

## 2. Correr Todos los Tests

### Track 1 -- AgentKit (10 tests)

```bash
cd mcp_server
pytest -m agentkit -v
```

Tests que deben pasar:

| # | Test | Que valida |
|---|------|------------|
| 1 | `test_lookup_human_verified` | `_eth_call` retorna non-zero = humano verificado |
| 2 | `test_lookup_human_not_verified` | `_eth_call` retorna zero = no verificado |
| 3 | `test_lookup_human_rpc_error_returns_error_status` | Error de RPC no lanza excepcion, retorna status `error` |
| 4 | `test_is_human_shortcut` | `is_human()` retorna `True` para wallets verificadas |
| 5 | `test_is_human_shortcut_returns_false` | `is_human()` retorna `False` para wallets no verificadas |
| 6 | `test_encode_address_lowercase_and_padded` | Encoding ABI correcto: lowercase, 64 chars, sin `0x` |
| 7 | `test_encode_address_already_lowercase` | Funciona con direcciones ya en minusculas |
| 8 | `test_to_dict_converts_enum_to_string` | Serializacion convierte enums a strings |
| 9 | `test_feature_flag_off_skips_lookup` | Feature flag `false` = no se llama `lookup_human` |
| 10 | `test_feature_flag_on_triggers_lookup` | Feature flag `true` = se llama `lookup_human` |

### Track 2 -- World ID 4.0 (10 tests)

```bash
cd mcp_server
pytest -m worldid -v
```

Tests que deben pasar:

| # | Test | Que valida |
|---|------|------------|
| 1 | `test_hash_to_field_length` | `hashToField` retorna 32 bytes con primer byte en cero |
| 2 | `test_hash_to_field_deterministic` | Misma entrada = misma salida (determinista) |
| 3 | `test_hash_ethereum_message` | EIP-191 personal_sign hash produce 32 bytes |
| 4 | `test_compute_rp_signature_message_length` | Mensaje RP tiene 81 bytes exactos (1+32+8+8+32) |
| 5 | `test_sign_request_returns_valid_structure` | `sign_request()` retorna nonce(64 hex), signature(130 hex), timestamps |
| 6 | `test_sign_request_no_key_raises` | Sin `WORLD_ID_SIGNING_KEY` lanza `ValueError` |
| 7 | `test_verify_returns_error_if_no_rp_id` | Sin `WORLD_ID_RP_ID` retorna error sin crash |
| 8 | `test_verify_calls_cloud_api` | Llama a `POST /api/v4/verify/{rp_id}` con payload correcto |
| 9 | `test_to_dict_error_status` | Serializacion de estado error es correcta |
| 10 | `test_to_dict_not_verified_status` | Serializacion de `not_verified` es correcta |

### Ambos tracks juntos

```bash
cd mcp_server
pytest -m "agentkit or worldid" -v
```

**Resultado esperado:** 20/20 PASSED

---

## 3. Test Track 1 (AgentKit) -- Nivel API

> Track 1 consulta el contrato **AgentBook** en Base Mainnet para verificar si una wallet pertenece a un humano registrado en World.

**Contrato:** `0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4` (Base)
**Funcion:** `lookupHuman(address) -> uint256` (retorna `humanId`, 0 = no verificado)

### Paso 1: Consultar una wallet no verificada (API REST)

```bash
curl -s https://api.execution.market/api/v1/workers/world-status?wallet=0x0000000000000000000000000000000000000000 | python -m json.tool
```

**Resultado esperado:**

```json
{
  "message": "World verification status retrieved",
  "data": {
    "status": "not_verified",
    "human_id": 0,
    "wallet_address": "0x0000000000000000000000000000000000000000",
    "error": null,
    "is_human": false
  }
}
```

- [ ] `status` es `"not_verified"`
- [ ] `human_id` es `0`
- [ ] `is_human` es `false`

### Paso 2: Consultar directamente el contrato AgentBook

Usar `cast` (Foundry) para verificar on-chain:

```bash
cast call 0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4 \
  "lookupHuman(address)(uint256)" \
  0x0000000000000000000000000000000000000000 \
  --rpc-url https://mainnet.base.org
```

**Resultado esperado:** `0` (wallet no registrada en World)

### Paso 3: Registrar una wallet de testing (requiere World App)

> Este paso requiere una wallet que haya completado el flujo de World ID en la World App.

```bash
# Si tienes una wallet ya verificada en World, usar la siguiente consulta
# para confirmar que el contrato la reconoce:
cast call 0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4 \
  "lookupHuman(address)(uint256)" \
  TU_WALLET_VERIFICADA \
  --rpc-url https://mainnet.base.org
```

**Resultado esperado:** Un numero mayor a `0` (el `humanId` asignado por World)

### Paso 4: Re-consultar la wallet verificada via API

```bash
curl -s "https://api.execution.market/api/v1/workers/world-status?wallet=TU_WALLET_VERIFICADA" | python -m json.tool
```

**Resultado esperado:**

```json
{
  "message": "World verification status retrieved",
  "data": {
    "status": "verified",
    "human_id": 42,
    "wallet_address": "0x...",
    "error": null,
    "is_human": true
  }
}
```

- [ ] `status` es `"verified"`
- [ ] `human_id` es `> 0`
- [ ] `is_human` es `true`

### Paso 5: Verificar integracion en apply_to_task

Cuando un worker aplica a una tarea, el backend automaticamente consulta AgentBook:

- [ ] Si la wallet esta verificada: se guarda `world_human_id` y `world_verified_at` en la tabla `executors`
- [ ] La respuesta de `apply_to_task` incluye `world_verified: true` y `world_human_id: N`
- [ ] Si la wallet NO esta verificada: la aplicacion se acepta igual (non-blocking), `world_verified: false`
- [ ] El feature flag `feature.world_agentkit_enabled` controla si se ejecuta el lookup (default: `true`)

---

## 4. Test Track 2 (World ID 4.0) -- Nivel API

> Track 2 implementa verificacion de humanidad via World ID 4.0 con pruebas de conocimiento cero (ZK proofs) a traves del Cloud API v4.

### Paso 1: Obtener firma RP (backend -> frontend)

```bash
curl -s https://api.execution.market/api/v1/world-id/rp-signature?action=verify-worker | python -m json.tool
```

**Resultado esperado:**

```json
{
  "nonce": "00abcdef...",
  "created_at": 1743580800,
  "expires_at": 1743581100,
  "action": "verify-worker",
  "signature": "abcdef1234...",
  "rp_id": "...",
  "app_id": "app_..."
}
```

- [ ] `nonce` tiene 64 caracteres hex (32 bytes)
- [ ] `signature` tiene 130 caracteres hex (65 bytes: r + s + v)
- [ ] `expires_at` es `created_at + 300` (5 minutos de TTL)
- [ ] `app_id` empieza con `app_`
- [ ] `rp_id` no esta vacio
- [ ] HTTP status es `200`

**Si retorna 503:** `WORLD_ID_SIGNING_KEY` no esta configurado en el server.

### Paso 2: Flujo completo via dashboard

1. Abrir `https://execution.market/profile` (logueado con wallet)
2. En la seccion **"Human Verification"**, hacer click en **"Verify with World ID"**
3. El widget de IDKit se abre (modal con QR code)
4. Escanear el QR con la World App
5. Aprobar la verificacion en World App
6. El widget se cierra automaticamente

- [ ] El boton "Verify with World ID" aparece (solo si NO esta verificado)
- [ ] El widget IDKit se abre y muestra QR
- [ ] Despues de escanear: aparece estado "Verifying proof..."
- [ ] Despues de verificar: aparece mensaje verde de exito
- [ ] El badge de World ID aparece en el perfil (circulo negro relleno = Orb, circulo outline = Device)
- [ ] Refrescar la pagina: el badge persiste (dato guardado en DB)

### Paso 3: Anti-sybil (intentar re-verificar con otra wallet)

> Cada identidad de World ID genera un `nullifier_hash` unico por `app_id`. Una persona = una cuenta.

1. Verificar con Wallet A (completa exitosamente)
2. Desconectar Wallet A, conectar Wallet B
3. Intentar verificar con la **misma persona** (mismo World ID) usando Wallet B

**Resultado esperado:**

```
HTTP 409 Conflict
{
  "detail": "This World ID has already been used to verify another account"
}
```

- [ ] La segunda verificacion falla con `409`
- [ ] El mensaje indica que el nullifier ya esta en uso
- [ ] Wallet B NO recibe el badge de verificacion

### Paso 4: Verificar almacenamiento en DB

```sql
-- Ver verificaciones almacenadas
SELECT executor_id, verification_level, nullifier_hash, verified_at
FROM world_id_verifications
ORDER BY verified_at DESC
LIMIT 5;

-- Ver flag en executor
SELECT id, display_name, world_id_verified, world_id_level
FROM executors
WHERE world_id_verified = true;
```

- [ ] Registro existe en `world_id_verifications` con el `nullifier_hash` correcto
- [ ] `verification_level` es `"orb"` o `"device"` segun el nivel de verificacion
- [ ] El executor tiene `world_id_verified = true` y `world_id_level` correcto

---

## 5. Test de Enforcement (High-Value Tasks)

> Las tareas con bounty >= $500 requieren World ID Orb verification. Este es el enforcement real que convierte World ID en anti-sybil con dientes.

**Configuracion:**

| Variable / Config | Valor | Efecto |
|---|---|---|
| `EM_WORLD_ID_ENABLED` | `true` | Activa enforcement (default) |
| `feature.world_id_required_for_high_value` | `true` | Habilita regla de bounty (default) |
| `worldid.min_bounty_for_orb_usd` | `500.00` | Threshold de bounty para requerir Orb |

### Paso 1: Crear una tarea con bounty >= $500

Crear la tarea via API o dashboard con `bounty_usd >= 500.00`.

### Paso 2: Intentar aplicar con un worker NO verificado

```bash
# Worker sin World ID Orb intenta aplicar
curl -s -X POST "https://api.execution.market/api/v1/workers/tasks/TASK_UUID/apply" \
  -H "Content-Type: application/json" \
  -d '{"executor_id": "UUID_DEL_WORKER", "message": "Test apply"}' \
  | python -m json.tool
```

**Resultado esperado:**

```json
{
  "detail": {
    "error": "world_id_orb_required",
    "message": "Tasks with bounty >= $5.00 require World ID Orb verification. Please verify your identity at https://execution.market/profile.",
    "verification_url": "/profile",
    "required_level": "orb",
    "current_level": null
  }
}
```

- [ ] HTTP status es `403`
- [ ] `error` es `"world_id_orb_required"`
- [ ] `required_level` es `"orb"`
- [ ] `current_level` muestra `null` o el nivel actual del worker

### Paso 3: Verificar el worker (Orb level) y re-intentar

1. Completar el flujo de World ID Orb (Seccion 4, Paso 2)
2. Aplicar nuevamente a la misma tarea

```bash
# Worker CON World ID Orb aplica
curl -s -X POST "https://api.execution.market/api/v1/workers/tasks/TASK_UUID/apply" \
  -H "Content-Type: application/json" \
  -d '{"executor_id": "UUID_DEL_WORKER", "message": "Test apply"}' \
  | python -m json.tool
```

**Resultado esperado:**

```json
{
  "message": "Application submitted successfully",
  "data": {
    "application_id": "...",
    "task_id": "...",
    "status": "pending",
    "world_verified": true,
    "world_human_id": 42
  }
}
```

- [ ] HTTP status es `200`
- [ ] `world_verified` es `true`
- [ ] El worker puede aplicar exitosamente

### Paso 4: Tareas con bounty < $5 no requieren Orb

- [ ] Un worker sin World ID puede aplicar a tareas con bounty < $5 sin problemas
- [ ] La respuesta incluye `world_verified: false` pero la aplicacion se acepta

---

## 6. Checklist para Demo Recording

### Que capturar para Track 1 (AgentKit -- On-Chain Human Verification)

| Escena | Que mostrar | Duracion sugerida |
|--------|-------------|-------------------|
| 1. Intro | Contrato AgentBook en Basescan: `0xE1D1D3526A6FAa37eb36bD10B933C1b77f4561a4` | 15s |
| 2. Lookup negativo | `curl .../world-status?wallet=0x000...` retorna `is_human: false` | 15s |
| 3. Lookup positivo | `curl .../world-status?wallet=VERIFICADA` retorna `is_human: true, human_id: N` | 15s |
| 4. Aplicacion con badge | Worker aplica a tarea, respuesta incluye `world_verified: true` | 20s |
| 5. Dashboard badge | Mostrar el badge verde "Verified Human" en la tarjeta del worker | 10s |

### Que capturar para Track 2 (World ID 4.0 -- ZK Proof of Humanity)

| Escena | Que mostrar | Duracion sugerida |
|--------|-------------|-------------------|
| 1. RP Signature | `curl .../world-id/rp-signature` retorna firma criptografica v4 | 15s |
| 2. Widget IDKit | Click "Verify with World ID" en profile, se abre el QR | 15s |
| 3. World App scan | Escanear QR con celular, aprobar en World App | 20s |
| 4. Verificacion exitosa | Badge aparece en el perfil, mensaje verde de exito | 10s |
| 5. Anti-sybil 409 | Intentar verificar con otra wallet, recibir `409 Conflict` | 15s |
| 6. Enforcement 403 | Worker sin Orb intenta aplicar a tarea de $5+, recibe `403 world_id_orb_required` | 15s |
| 7. Post-verificacion 200 | Mismo worker despues de verificar Orb, aplica exitosamente | 10s |

### Tips para el recording

- Usar `| python -m json.tool` en los curls para pretty-print
- Resaltar los campos clave en la respuesta JSON (status codes, `is_human`, `nullifier_hash`, `error`)
- Si usas terminal, aumentar el font size para legibilidad
- Capturar la transicion del dashboard: sin badge -> con badge
- Para anti-sybil: mostrar que el mismo QR/persona genera el mismo `nullifier_hash`

---

## 7. Verificacion de Produccion

### Health check general

```bash
curl -s https://api.execution.market/health | python -m json.tool
```

- [ ] Retorna `200` con status `healthy`

### Swagger -- endpoints nuevos visibles

Abrir: `https://api.execution.market/docs`

- [ ] Endpoint `GET /api/v1/workers/world-status` aparece bajo tags "Workers" y "World"
- [ ] Endpoint `GET /api/v1/world-id/rp-signature` aparece bajo tag "World ID"
- [ ] Endpoint `POST /api/v1/world-id/verify` aparece bajo tag "World ID"
- [ ] Schemas `RPSignatureResponse`, `VerifyWorldIdRequest`, `VerifyWorldIdResponse` visibles

### Dashboard -- componentes visibles

Abrir: `https://execution.market`

- [ ] Pagina de perfil (`/profile`): seccion "Human Verification" con boton "Verify with World ID"
- [ ] Si ya esta verificado: badge de World ID visible (circulo negro = Orb, circulo gris = Device)
- [ ] En `TaskApplicationModal`: badge verde "Verified Human" visible si el worker tiene `world_human_id > 0`
- [ ] En `TaskApplicationModal`: badge de World ID (Orb/Device) visible si el worker tiene `world_id_verified = true`

### Base de datos -- tablas y columnas

```sql
-- Track 1: columnas en executors
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'executors'
  AND column_name IN ('world_human_id', 'world_verified_at', 'world_id_verified', 'world_id_level');
```

- [ ] `world_human_id` (integer) -- Track 1
- [ ] `world_verified_at` (timestamptz) -- Track 1
- [ ] `world_id_verified` (boolean) -- Track 2
- [ ] `world_id_level` (text) -- Track 2

```sql
-- Track 2: tabla de verificaciones
SELECT count(*) FROM world_id_verifications;
```

- [ ] La tabla existe y es consultable

---

## Resumen de Arquitectura

```
                    TRACK 1 (AgentKit)                    TRACK 2 (World ID 4.0)
                    ==================                    ======================

  Contrato:         AgentBook (Base)                      Cloud API v4 (World)
                    lookupHuman(addr)                     POST /api/v4/verify/{rp_id}

  Backend:          agentbook.py                          client.py (RP signing + verify)
                    _eth_call (JSON-RPC)                  coincurve (secp256k1)
                         |                                     |
                         v                                     v
                    workers.py                             worldid.py
                    GET /world-status                      GET /rp-signature
                    apply_to_task() <-- lookup              POST /verify
                         |                                     |
                         v                                     v
                    executors.world_human_id               world_id_verifications
                                                          executors.world_id_verified

  Frontend:         WorldHumanBadge.tsx                   WorldIdVerification.tsx
                    (badge verde)                         (IDKit widget + badge)

  Enforcement:      Non-blocking (info)                   Blocking: bounty >= $5
                    Se guarda en DB pero                  requiere Orb verification
                    no bloquea aplicacion                 o retorna 403
```
