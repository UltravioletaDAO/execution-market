# Improvement Backlog - 2026-02-05

Backlog operativo enfocado en **ship rápido** y reducir caos de cambios.

## Update 2026-02-06
- Ver análisis completo: `docs/planning/SHIP_REVIEW_2026-02-06.md`.
- Deploy vigente validado en producción: `em-production-dashboard:8` y `em-production-mcp-server:14`.
- Se confirmó drift de esquema productivo: faltan tablas `payments` y `escrows` (impacta trazabilidad canónica de tx).
- Se agregaron fixes live:
`dashboard/src/hooks/useTaskPayment.ts` ahora degrada sin tabla `payments` y toma payout tx desde `submissions.payment_tx`.
`mcp_server/api/routes.py` calcula métricas públicas financieras desde `tasks`.

## Regla base
- No meter features nuevas mientras haya P0 abiertos.
- Todo item debe tener owner, criterio de aceptación y fecha.

---

## P0 (ahora mismo)

### Frontend quality gate

- [ ] `UI-001` Crear `eslint` config en `dashboard`.
- [ ] `UI-002` Corregir errores TS en `src/components/notifications/*`.
- [ ] `UI-003` Corregir errores TS en `src/services/tasks.ts`.
- [ ] `UI-004` Corregir errores TS en `src/components/EvidenceUpload.tsx`.
- [ ] `UI-005` Corregir tipos en `src/services/types.ts`.
- [ ] `UI-006` Añadir `eslint` a `admin-dashboard` o remover script `lint`.
- [ ] `UI-007` Validar `npm run typecheck && npm run lint && npm run test:run && npm run build` en CI.
- [ ] `UI-008` Ejecutar plan de triage de `docs/planning/FRONTEND_TYPECHECK_TRIAGE_2026-02-05.md`.

### Pagos y estado

- [ ] `PAY-001` Prueba real `approve -> settle` con fondos y tx hash registrado.
- [ ] `PAY-002` Prueba real `cancel -> refund` con fondos y tx hash registrado.
- [ ] `PAY-003` Definir y documentar state machine escrow (transiciones válidas).
- [ ] `PAY-004` Añadir test de carrera `approve vs cancel` con lock/orden determinista.
- [x] `PAY-005` Mostrar transaccion de fondeo x402 en detalle de tarea (incluye fallback con `escrow_tx` del task).
- [x] `PAY-006` Mostrar transaccion de pago final al worker en timeline de `PaymentStatus`.
- [ ] `PAY-007` Validar en produccion `publish -> submit -> approve` y comprobar links de tx en UI.
- [x] `PAY-008` Corregir flujo `task-factory --live`: `createEscrow` revierte y deja task huerfana sin `escrow_tx` (rollback/cancel automatico + error diagnostico).
- [x] `PAY-009` Exponer endpoint publico de metricas para reflejar actividad real (`/api/v1/public/metrics`).
- [ ] `PAY-010` Garantizar que las tx de pago visibles en UI provienen de flujo facilitador (no wallet directa) y bloquear rutas de prueba directas en scripts de release.

### Operación de release

- [ ] `OPS-001` Unificar dominio API canónico en docs (`api` vs `mcp`).
- [ ] `OPS-002` Publicar checklist único de release.
- [ ] `OPS-003` Definir rollback plan con pasos exactos.
- [ ] `OPS-004` Congelar scope 72h (solo bugfixes).
- [x] `OPS-007` Deploy unificado backend+frontend en ECS con tags inmutables y verificacion de `rollout=COMPLETED`.
- [ ] `OPS-008` Automatizar deploy unificado con script reproducible (build/push/register/update/wait/health).

---

## P1 (siguiente ola)

### Rendimiento

- [ ] `PERF-001` Aplicar `React.lazy` en rutas pesadas de dashboard.
- [ ] `PERF-002` Mover inicialización wallet/auth a carga diferida.
- [ ] `PERF-003` Definir presupuesto de bundle y fallo en CI si se excede.

### Pruebas y CI

- [ ] `TEST-001` Reparar `tests/test_websocket.py` (import drift).
- [ ] `TEST-002` Actualizar tests MCP según contrato actual.
- [ ] `TEST-003` Actualizar tests Bayesian/reputation por API actual.
- [ ] `TEST-004` Pipeline de smoke release (backend + frontend + health).

### Seguridad y auditoría

- [ ] `SEC-001` Revisar todos los write endpoints para logs estructurados homogéneos.
- [ ] `SEC-002` Revisar exposición de secretos en logs y query params.
- [ ] `SEC-003` Agregar alertas por intentos auth fallidos repetidos.

---

## Escenarios nuevos a probar (no obvios)

- [ ] `SCN-001` Retry storm: 10 reintentos de approve en 3s.
- [ ] `SCN-002` Retry storm: 10 reintentos de cancel en 3s.
- [ ] `SCN-003` Worker sube evidencia después de cancelación (UI stale).
- [ ] `SCN-004` Facilitador cae entre verify y settle.
- [ ] `SCN-005` DB en modo legacy (`applications`) pero app esperando canonical.
- [ ] `SCN-006` Token websocket válido con user_id spoofed.
- [ ] `SCN-007` Admin key correcta, actor vacío o malformado.
- [ ] `SCN-008` Reputación: task-agent mismatch con agent_id válido.

---

## Formato mínimo por item (para ejecutar sin perderse)

Usar esta plantilla:
- `ID`:
- `Owner`:
- `Status`: `todo | doing | blocked | done`
- `Definition of done`:
- `Validation command`:
- `Evidence link`:

### Sesion Wallet (P0 UX/Conversion)

- [x] `AUTH-001` Persistir wallet en AuthContext para restauracion sin reconexion.
- [x] `AUTH-002` Bloquear CTA de login mientras se restaura estado auth (evita prompts falsos).
- [ ] `AUTH-003` Validar manualmente en produccion que Start Earning no vuelve a pedir firma tras login inicial.
- [ ] `AUTH-004` Agregar test e2e de persistencia: login -> home -> Start Earning -> no-sign -> refresh -> sigue autenticado.

### Observabilidad de plataforma (nuevo)

- [x] `MET-001` Mostrar metrica real de `registered workers` en landing.
- [x] `MET-002` Mostrar metrica real de `workers taking tasks` en landing.
- [x] `MET-003` Mostrar metrica real de actividad de usuarios en dashboard logueado.
- [ ] `MET-004` Añadir cache server-side (30-60s) para endpoint de metricas y reducir carga de consultas.
- [ ] `MET-005` Incluir `total_volume_usd` confiable una vez que escrows/funding rows estén sincronizados en prod.

### Topologia API (P0 claridad)

- [ ] `OPS-005` Definir comportamiento oficial de `/api/*` en `execution.market` (hoy responde SPA HTML).
- [ ] `OPS-006` Si `/api` no sera proxy publico, remover referencias y usar `api.execution.market` explicitamente.
