# Ship Execution Report - 2026-02-05

## TL;DR

Hoy se avanzó fuerte en P0 backend (idempotencia de pagos, hardening de auth, validación websocket, ownership de reputación, deprecación de endpoints legacy y alineación de schema para aplicaciones).  
El backend crítico está en estado **shippable para beta privada**; el **bloqueador principal** para release público sigue siendo frontend quality gate (`typecheck`/`lint`).

---

## 1) Estado real por área

### Backend API + pagos

**Estado**: `YELLOW -> casi GREEN`  

Hecho:
- Idempotencia de `approve_submission` y `cancel_task`.
- Guardrails de estado:
  - no aprobar submissions si el task ya está `cancelled/refunded/expired/completed`,
  - no cancelar task cuando escrow ya está `released`.
- Refund cancel-flow:
  - reembolso automático en escrows `deposited/funded/partial_released`,
  - expiración natural para authorize-only,
  - persistencia de auditoría de refund en `payments`.
- Auth hardening:
  - admin por headers (`Authorization` / `X-Admin-Key`) con `actor_id`,
  - websocket token/API-key validation,
  - ownership checks en reputación.
- API canonical:
  - endpoints legacy deprecated con `410` + `canonical_endpoint`.
- Schema alignment:
  - backend prefiere `task_applications` y cae a `applications` con warning explícito.

Archivos clave:
- `mcp_server/api/routes.py`
- `mcp_server/websocket/server.py`
- `mcp_server/api/reputation.py`
- `mcp_server/api/admin.py`
- `mcp_server/main.py`
- `mcp_server/supabase_client.py`

### Frontend dashboard

**Estado**: `YELLOW/RED`  

Hecho:
- `vitest` ya corre solo tests unitarios (no Playwright).
- Build de producción compila.

Pendiente crítico:
- `typecheck` rojo masivo (353 errores TS).
- `lint` rojo por falta de configuración ESLint.
- Bundle principal sigue grande (~5 MB minificado).
- Triage granular por archivo en `docs/planning/FRONTEND_TYPECHECK_TRIAGE_2026-02-05.md`.

### Docs / governance de release

**Estado**: `YELLOW`

Hecho:
- Se actualizó `SHIP_NOW_AUDIT_2026-02-05.md` con avances reales.
- Se dejó este reporte como documento operativo.

Pendiente:
- Unificar dominio canónico (`api.execution.market` vs `mcp.execution.market`) en toda la documentación pública.

---

## 2) Cambios implementados en esta iteración

### Seguridad y consistencia backend

1. `mcp_server/main.py`
- Deprecación formal de endpoints legacy:
  - `POST /api/v1/tasks/apply`
  - `POST /api/v1/submissions`
- Respuesta `410` con hint explícito al endpoint canónico.

2. `mcp_server/supabase_client.py`
- Resolución dinámica de tabla de aplicaciones:
  - prioridad `task_applications`,
  - fallback `applications` (compatibilidad DB legacy),
  - warning si cae a legacy.

3. `mcp_server/api/routes.py`
- Nuevo helper `_record_refund_payment(...)`.
- Guardrails extra en `approve_submission`.
- Bloqueo de cancelación si escrow ya fue `released`.
- Persistencia de refund en tabla `payments`.

4. `mcp_server/api/admin.py`
- Normalización robusta de `actor_id`.
- Audit log estructurado para cambios de config.

5. `mcp_server/api/reputation.py`
- Audit log estructurado de acciones de reputación.

### Tests nuevos/actualizados

- `mcp_server/tests/test_p0_routes_idempotency.py` (extendido)
- `mcp_server/tests/test_schema_alignment_applications.py` (nuevo)

---

## 3) Validación ejecutada (automática)

### Backend

Comandos:
```bash
python -m py_compile mcp_server\supabase_client.py mcp_server\main.py mcp_server\api\routes.py mcp_server\api\admin.py mcp_server\api\reputation.py
python -m pytest -q mcp_server\tests\test_p0_routes_idempotency.py mcp_server\tests\test_admin_auth.py mcp_server\tests\test_websocket_auth_hardening.py mcp_server\tests\test_reputation_ownership.py mcp_server\tests\test_schema_alignment_applications.py
```

Resultado:
- `24 passed`

### Frontend

Comandos:
```bash
cd dashboard
npm run test:run
npm run build
npm run typecheck
npm run lint
```

Resultado:
- `test:run`: `13 passed`
- `build`: `OK` (warning de chunks grandes)
- `typecheck`: `FAIL` (`353` errores TS)
- `lint`: `FAIL` (no hay ESLint config)

---

## 4) Qué falta para producción (granular y priorizado)

### P0 inmediatos (bloquean release público)

1. Frontend quality gate:
- resolver errors TS en `notifications`, `tasks` services y `evidence`.
- agregar config ESLint en `dashboard`.
- instalar/configurar ESLint en `admin-dashboard` o remover script temporalmente.

2. Validación E2E con fondos reales:
- happy path con settle real.
- cancel path con refund real.
- prueba de race `approve vs cancel`.

3. Docs de topología:
- único dominio canónico y endpoints oficiales.

### P1 (siguiente ola)

1. Reducir bundle principal:
- `React.lazy` por rutas pesadas,
- split de wallet/auth providers.

2. Completar state machine de escrow:
- transición explícita `authorized -> released/refunded/cancelled`.

3. Pipeline CI de ship:
- backend crítico,
- frontend gates,
- smoke deploy checks.

---

## 5) Perspectivas estratégicas (brainstorm)

### Perspectiva A: API-first launch (rápida y controlada)
- Lanza backend + agentes primero.
- Dashboard público limitado hasta cerrar TS/lint.
- Ventaja: monetizas/validas flujo real ya.

### Perspectiva B: Private beta cerrada de 7 días
- Allowlist de agentes/workers.
- Límites de bounty por task.
- Monitoreo manual y rollback fácil.
- Ventaja: aprende rápido sin riesgo reputacional grande.

### Perspectiva C: “Ship-train” rígido (operación)
- Congelar features 72h.
- Solo bugfix/security/performance.
- Dos ventanas fijas de deploy por día.
- Ventaja: reduces caos de backlog y por fin embarcas.

### Escenarios no obvios a cubrir
- Reintentos de cliente con latencia alta (idempotencia cruzada).
- Stale UI: worker envía submission tras cancelación.
- Falla parcial de facilitador: verify ok, settle/refund fail.
- Drift schema en staging/prod (tabla legacy activa sin saberlo).

---

## 6) Checklist exacto para que tú pruebes todo

### A. Backend hardening (rápido)

1. Ejecuta:
```bash
python -m pytest -q mcp_server\tests\test_p0_routes_idempotency.py
```
Esperado: `6 passed`.

2. Ejecuta:
```bash
python -m pytest -q mcp_server\tests\test_admin_auth.py mcp_server\tests\test_websocket_auth_hardening.py mcp_server\tests\test_reputation_ownership.py mcp_server\tests\test_schema_alignment_applications.py
```
Esperado: todo en verde.

### B. Endpoints legacy deprecated

Con API levantada:
```bash
curl -X POST http://localhost:8000/api/v1/tasks/apply -H "Content-Type: application/json" -d "{\"task_id\":\"00000000-0000-0000-0000-000000000000\",\"executor_id\":\"00000000-0000-0000-0000-000000000000\"}"
curl -X POST http://localhost:8000/api/v1/submissions -H "Content-Type: application/json" -d "{\"task_id\":\"00000000-0000-0000-0000-000000000000\",\"executor_id\":\"00000000-0000-0000-0000-000000000000\",\"evidence\":{}}"
```
Esperado: `410` con `canonical_endpoint`.

### C. Frontend gates

```bash
cd dashboard
npm run test:run
npm run build
npm run typecheck
npm run lint
```
Esperado ahora:
- tests/build: verdes.
- typecheck/lint: rojos (esto define el trabajo pendiente exacto para release público).

### D. Gate final antes de deploy

No publiques a público abierto hasta que se cumplan:
- `dashboard typecheck` verde,
- `dashboard lint` verde,
- al menos 1 E2E real con fondos (approve + cancel) documentado.

---

## 7) Update de produccion (2026-02-05 15:59 EST)

Deploy ejecutado a produccion con imagenes nuevas y task definitions inmutables:

- Backend:
  - image: `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:ship-20260205-155439-1045d7b`
  - task definition: `em-production-mcp-server:3`
  - digest: `sha256:4a3b9cc90fb6da4eff16d4f2971c44deaa823914c800638b0fb7aadadce5a18f`
- Dashboard:
  - image: `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:ship-20260205-155439-1045d7b`
  - task definition: `em-production-dashboard:2`
  - digest: `sha256:ca7d29ff4ac0c0bf58dcfee1b8986c98fa2f4e626daf97ad8c6c893b3e97d086`

Verificacion post-deploy:

- ECS: ambos servicios en `rollout=COMPLETED`
- `https://execution.market` -> `200 OK`
- `https://api.execution.market/health` -> `200 OK`
- `https://mcp.execution.market/health` -> `200 OK`

### Session persistence fix (wallet)

Se desplego fix para evitar reprompts de firma en click repetido de `Start Earning`:

- `AuthContext` ahora restaura wallet persistida y evita estado falso-unauth durante bootstrap
- CTA `Start Earning` queda deshabilitado mientras `loading` para no abrir modal prematuramente
- logout limpia wallet persistida

Archivos:

- `dashboard/src/context/AuthContext.tsx`
- `dashboard/src/components/layout/AppHeader.tsx`
- `dashboard/src/components/landing/HeroSection.tsx`
