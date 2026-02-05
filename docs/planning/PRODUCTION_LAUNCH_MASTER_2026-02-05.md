# Production Launch Master - 2026-02-05

Documento maestro para salir del caos de backlog y ejecutar lanzamiento con foco.

## 1) Estado actual real (2026-02-05)

### Produccion desplegada

- Cluster ECS: `em-production-cluster`
- Servicio backend: `em-production-mcp-server`
- Servicio frontend: `em-production-dashboard`
- Deploy realizado hoy con tag inmutable:
  - `ship-20260205-155439-1045d7b`
  - `ship-20260205-164347-tx402`
- Revisiones activas:
  - `em-production-mcp-server:3`
  - `em-production-dashboard:3`
- Digests activos:
  - backend: `sha256:4a3b9cc90fb6da4eff16d4f2971c44deaa823914c800638b0fb7aadadce5a18f`
  - dashboard: `sha256:2665312b8a4575b31d5416e1549c4ec08b536d21a3b53d7d6212b59e28aec13f`

### Salud en vivo

- `https://execution.market` -> `200 OK`
- `https://api.execution.market/health` -> `200 OK` (`healthy`)
- `https://mcp.execution.market/health` -> `200 OK` (`healthy`)

### Fix de frustracion principal (wallet re-sign)

Implementado en frontend para reducir re-firma repetida:

- restauracion de wallet persistida (`em_last_wallet_address`) en `AuthContext`
- gating de estado auth para esperar restauracion de Dynamic antes de mostrar CTA de login
- `Start Earning` deshabilitado durante restauracion (`loading`) para evitar prompts prematuros
- limpieza robusta de storage al logout

Archivos clave:

- `dashboard/src/context/AuthContext.tsx`
- `dashboard/src/components/layout/AppHeader.tsx`
- `dashboard/src/components/landing/HeroSection.tsx`

---

## 2) Foto de calidad (lo que SI y lo que NO)

### Backend

Validacion ejecutada:

```bash
python -m pytest -q mcp_server/tests/test_p0_routes_idempotency.py mcp_server/tests/test_admin_auth.py mcp_server/tests/test_websocket_auth_hardening.py mcp_server/tests/test_reputation_ownership.py mcp_server/tests/test_schema_alignment_applications.py
```

Resultado:

- `24 passed`

Estado suite casi completa:

```bash
cd mcp_server
python -m pytest -q --ignore=tests/test_websocket.py
```

Resultado:

- `577 passed`
- `40 failed`
- `8 skipped`

Fallos concentrados en:

- `tests/test_mcp_tools.py` (mocks desalineados con `mcp.tool`)
- `tests/test_platform_config.py` (defaults esperados `0.25` vs actual `0.01`)
- `tests/test_reputation.py` (drift de API Bayesian)
- `tests/test_websocket_module.py` (rate limiter expectation drift)

Coleccion completa:

```bash
cd mcp_server
python -m pytest -q
```

Resultado:

- error de coleccion en `tests/test_websocket.py` por import `WebSocketMessage`

### Frontend dashboard

Validaciones:

```bash
cd dashboard
npm run test:run
npm run build
npm run typecheck
npm run lint
```

Resultado:

- tests unitarios: `13 passed`
- build: `OK`
- typecheck: `FAIL` (errores TS concentrados en notifications/services/evidence)
- lint: `FAIL` (no existe configuracion ESLint)

### Admin dashboard

Validaciones:

```bash
cd admin-dashboard
npm run build
npm run lint
```

Resultado:

- build: `OK`
- lint: `FAIL` (`eslint` no instalado)

---

## 3) Diagnostico ejecutivo (sin maquillaje)

### Lo que ya esta suficientemente fuerte para operar

- backend productivo en salud `healthy`
- idempotencia y hardening de auth P0 backend ya aplicados
- deploy productivo reproducible en ECS/ECR
- ruta principal web estable (`execution.market`)

### Lo que todavia impide launch publico confiable

- frontend quality gate roto (`typecheck` + `lint`)
- suite global backend no verde por drift de tests legacy
- falta validacion E2E real con fondos de escenario completo `approve/cancel`
- contradiccion de topologia API (`/api` en frontend principal no enruta backend en `execution.market`)

---

## 4) Backlog granular de lanzamiento (prioridad real)

## P0 - 24h

- [ ] `P0-FE-TS-001` Corregir tipos de notifications provider (`NotificationProvider`, `NotificationBell`)
- [ ] `P0-FE-TS-002` Corregir tipos en `dashboard/src/services/tasks.ts`
- [ ] `P0-FE-TS-003` Corregir tipos en `EvidenceUpload` y duplicados de componentes evidence
- [x] `P0-PAYMENT-TX-VISIBILITY` Mostrar tx de fondeo y pago final x402 en paneles de detalle de task
- [ ] `P0-FE-LINT-001` Crear config ESLint en `dashboard/` y dejar `npm run lint` verde
- [ ] `P0-ADMIN-LINT-001` Instalar/configurar ESLint en `admin-dashboard` o retirar gate temporalmente
- [ ] `P0-BE-TEST-001` Resolver import drift `WebSocketMessage` en `tests/test_websocket.py`
- [ ] `P0-BE-TEST-002` Adaptar `tests/test_mcp_tools.py` al contrato actual `mcp.tool`
- [ ] `P0-BE-TEST-003` Alinear expectativas `platform_config` (`0.01` vs `0.25`) con decision oficial
- [ ] `P0-BE-TEST-004` Alinear tests Bayesian con firma actual de `BayesianCalculator`
- [ ] `P0-WALLET-SESSION-001` Validar en produccion persistencia de sesion wallet (sin re-firma en click repetido)

## P1 - 72h

- [ ] `P1-E2E-REAL-001` Happy path real funds: publish -> apply -> submit -> approve -> settle
- [ ] `P1-E2E-REAL-002` Cancel path real funds: publish -> accept/cancel -> refund/expiry audit
- [ ] `P1-RACE-001` Escenario race approve vs cancel con resultado determinista e idempotente
- [ ] `P1-PERF-001` Split del bundle principal con `React.lazy`
- [ ] `P1-PERF-002` Definir budget de bundle en CI
- [ ] `P1-DOCS-001` Unificar dominio canonico API y actualizar docs publicos

## P2 - despues de launch publico

- [ ] `P2-OPS-001` Alerting operativo por auth failures repetidos
- [ ] `P2-OPS-002` Dashboard de SLOs (health, p95, error rate, settle latency)
- [ ] `P2-UX-001` Afinar UX para sesiones agente/worker multi-rol en home

---

## 5) Escenarios criticos a validar antes de abrir publico

- [ ] `SCN-001` Usuario worker firma una sola vez y vuelve a `Start Earning` sin reprompt
- [ ] `SCN-002` Refresh hard del browser mantiene sesion y entra a `/tasks`
- [ ] `SCN-003` Logout limpia sesion y vuelve a requerir firma
- [ ] `SCN-004` Retry storm de approve (10 reintentos) no duplica settlement
- [ ] `SCN-005` Retry storm de cancel (10 reintentos) no duplica refund
- [ ] `SCN-006` Worker envia submission con task cancelado -> rechazo limpio
- [ ] `SCN-007` Facilitador caido en settle/refund -> audit y reintento claros

---

## 6) Plan de ejecucion rapido

### Ventana 0-6 horas

- cerrar `P0-FE-TS-001..003`
- configurar lint dashboard/admin
- estabilizar `test_websocket.py` + `test_mcp_tools.py`

### Ventana 6-24 horas

- ejecutar suite global backend y frontend gates en verde
- validar `SCN-001..003` en produccion con evidencia
- publicar release note y abrir beta publica controlada

### Ventana 24-72 horas

- ejecutar E2E real-funds (`P1-E2E-REAL-001/002`)
- resolver performance principal (`P1-PERF-001`)
- abrir onboarding publico total

---

## 7) Checklist exacto para que tu pruebes TODO

## A. Verificar deploy activo en AWS

```bash
aws ecs describe-services --cluster em-production-cluster --services em-production-mcp-server em-production-dashboard --region us-east-2 --query "services[].{name:serviceName,taskDef:taskDefinition,running:runningCount,desired:desiredCount,rollout:deployments[0].rolloutState}"
```

Esperado:

- ambas `rollout=COMPLETED`
- backend `taskDefinition ...:3`
- dashboard `taskDefinition ...:3`

## B. Verificar salud productiva

```bash
curl -i https://execution.market
curl -i https://api.execution.market/health
curl -i https://mcp.execution.market/health
```

Esperado:

- `execution.market` responde `200` con HTML
- health endpoints responden `200` con JSON `status: healthy`

## C. Verificar fix de sesion wallet (manual)

1. Abrir `https://execution.market`
2. Click en `Start Earning`
3. Conectar wallet y firmar una vez
4. Confirmar redireccion a `/tasks`
5. Volver a home (`/`)
6. Click nuevamente en `Start Earning`
7. Esperado: NO pedir firma otra vez, entrar directo a `/tasks`
8. Hacer refresh del navegador en `/tasks`
9. Esperado: sigue autenticado
10. Hacer logout
11. Click `Start Earning` de nuevo
12. Esperado: ahora SI pide firma (comportamiento correcto)

## D. Verificar suite critica backend

```bash
python -m pytest -q mcp_server/tests/test_p0_routes_idempotency.py mcp_server/tests/test_admin_auth.py mcp_server/tests/test_websocket_auth_hardening.py mcp_server/tests/test_reputation_ownership.py mcp_server/tests/test_schema_alignment_applications.py
```

Esperado:

- `24 passed`

## E. Verificar gaps pendientes (para no auto-engañarnos)

```bash
cd dashboard
npm run typecheck
npm run lint

cd ../admin-dashboard
npm run lint
```

Esperado hoy:

- siguen fallando (esta es la lista corta de bloqueo real para launch publico)

---

## 8) Regla operativa para no volver al caos

- un solo backlog activo: este documento
- todo nuevo feature entra como `P2` automaticamente hasta cerrar P0
- dos deploy windows al dia, no despliegues random
- cada deploy con evidencia minima: salud + smoke + comando exacto
