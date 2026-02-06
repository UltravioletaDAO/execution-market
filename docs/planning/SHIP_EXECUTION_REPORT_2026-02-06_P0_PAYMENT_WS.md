# Ship Execution Report - P0 Payment Ledger + WebSocket ACL (2026-02-06)

## 1) Scope ejecutado

Objetivo: cerrar el bloque operativo pedido como `1` y `2`:

- `P0-001..P0-004`:
  - migracion minima de ledger canonico (`payments` / `escrows`),
  - endpoint canonico `GET /api/v1/tasks/{task_id}/payment`,
  - escritura canonica en approve/cancel.
- `P0-005..P0-006`:
  - hardening ACL de websocket para `task:{id}`,
  - arreglo de `mcp_server/tests/test_websocket.py` para collection estable.

## 2) Commits granulares

- `771231d` `feat(db): add canonical payment ledger compatibility migrations`
- `aaa0ace` `feat(api): add canonical task payment endpoint with ledger normalization`
- `050ef19` `fix(websocket): enforce task room ACL and repair test collection`
- `1b5058b` `feat(dashboard): consume canonical task payment endpoint with fallback`
- `7fc64f4` `fix(api): return 404 for missing task in canonical payment endpoint`

Push realizado a `origin/main`.

## 3) Cambios tecnicos

### 3.1 Database / migraciones

Archivos:

- `supabase/migrations/015_payment_ledger_canonical.sql`
- `mcp_server/supabase/migrations/20260206000006_payment_ledger_canonical.sql`

Incluyen:

- creacion `escrows` y `payments` si faltan,
- columnas canonicas minimas (`task_id`, `submission_id`, `type`, `status`, `tx_hash`, `amount_usdc`, `network`, `created_at`),
- compatibilidad legacy (`payment_type`, `transaction_hash`, `chain_id`, etc.),
- indices operativos.

### 3.2 API canonica de pagos por task

Archivo:

- `mcp_server/api/routes.py`

Nuevo endpoint:

- `GET /api/v1/tasks/{task_id}/payment`

Comportamiento:

- normaliza drift de columnas en `payments`,
- agrega fallback con `tasks`, `escrows`, `submissions.payment_tx`,
- devuelve timeline canonico para UI,
- devuelve `404` cuando la task no existe (hotfix `7fc64f4`).

### 3.3 Escritura canonica en flujos de pago

Archivo:

- `mcp_server/api/routes.py`

Se robustecio escritura de ledger en:

- `approve_submission`: guarda `type` + `payment_type`, `tx_hash` + `transaction_hash`, `network`,
- `cancel_task` refund: idem para refund row.

### 3.4 WebSocket ACL hardening

Archivo:

- `mcp_server/websocket/server.py`

Cambios:

- `task:{uuid}` valida ownership/asignacion real contra DB,
- `user:{id}` privado (solo su room),
- rooms desconocidos pasan a denegado por defecto,
- compatibilidad para rooms de test/demo no-UUID.

### 3.5 Dashboard consume endpoint canonico

Archivo:

- `dashboard/src/hooks/useTaskPayment.ts`

Cambios:

- consulta primero `GET /api/v1/tasks/{task_id}/payment`,
- mantiene fallback actual por Supabase si endpoint falla/degrada.

## 4) Tests ejecutados

Backend:

```bash
python -m pytest -q mcp_server/tests/test_p0_routes_idempotency.py
python -m pytest -q mcp_server/tests/test_websocket.py mcp_server/tests/test_websocket_auth_hardening.py mcp_server/tests/test_websocket_module.py
```

Resultado:

- `43 passed`

Frontend:

```bash
npm --prefix dashboard run build
```

Resultado:

- build `OK`

## 5) Deploy a produccion

Imagenes publicadas:

- `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:ship-20260205-202613-7fc64f4`
- `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:ship-20260205-202028-1b5058b`

Task definitions activas:

- `em-production-mcp-server:16`
- `em-production-dashboard:9`

Estado ECS:

- ambos servicios en `COMPLETED`, `running=desired=1`.

Health:

- `https://execution.market` -> `200`
- `https://www.execution.market` -> `200`
- `https://api.execution.market/health` -> `200`

Endpoint nuevo:

- `GET /api/v1/tasks/00000000-0000-0000-0000-000000000000/payment` -> `404` (correcto)
- `GET /api/v1/tasks/11111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa/payment` -> `200`

## 6) Gap critico restante (DB prod)

Verificacion real contra Supabase (2026-02-06):

- `public.payments` -> no existe (`PGRST205`)
- `public.escrows` -> no existe (`PGRST205`)

Implicacion:

- el endpoint canonico funciona en modo degradado (fallback),
- para cerrar `P0-001` de forma real falta aplicar SQL de migracion en la DB productiva.

## 7) TODO granular pendiente (post-ship inmediato)

### P0 restante

- [ ] Aplicar `supabase/migrations/015_payment_ledger_canonical.sql` en DB de produccion.
- [ ] Crear smoke real con flujo completo y verificar rows reales en `payments`.
- [ ] Validar persistencia de sesion wallet (`Start Earning` sin firma repetida).

### P1 siguiente

- [ ] Reducir bundle principal (code-splitting por rutas pesadas).
- [ ] Cerrar baseline TS/lint para gate de release estable.

## 8) Checklist exacto para validar manualmente

### A. Sanidad de deploy

```bash
curl -I https://execution.market
curl -I https://www.execution.market
curl https://api.execution.market/health
```

Esperado: `200`.

### B. Endpoint canonico por task

```bash
curl https://api.execution.market/api/v1/tasks/11111111-aaaa-aaaa-aaaa-aaaaaaaaaaaa/payment
curl -i https://api.execution.market/api/v1/tasks/00000000-0000-0000-0000-000000000000/payment
```

Esperado:

- primer endpoint `200` con `status/events`,
- segundo endpoint `404`.

### C. Flujo funcional en UI (landing + dashboard)

1. Abre una task con escrow en detalle.
2. Verifica bloque `Escrow/Pago` y timeline.
3. Completa un flujo real `publish -> accept -> submit -> approve`.
4. Verifica que aparezca tx final en timeline.

### D. ACL websocket (seguridad)

1. Conecta dos usuarios distintos por websocket.
2. Usuario A intenta subscribe a `task:{uuid_de_B}`.
3. Esperado: `Access denied to room`.

### E. DB migration pendiente

1. Ejecuta SQL de `supabase/migrations/015_payment_ledger_canonical.sql` en Supabase SQL Editor.
2. Repite:
   - `GET /api/v1/tasks/{task_id}/payment`
3. Esperado: response alimentado por ledger real `payments`.

