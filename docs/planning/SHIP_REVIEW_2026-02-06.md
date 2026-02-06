# Ship Review And Launch Plan - 2026-02-06

## 1) Estado real ahora (produccion)

Fecha de corte: 2026-02-06

Deploy activo:
- Frontend ECS: `em-production-dashboard:8`
- Backend ECS: `em-production-mcp-server:14`
- Commit deployado: `3f0d7bd`

Cambios ya live:
- Fallback de landing para mostrar expiradas cuando no hay activas.
- Hotfix de service worker/cache para evitar que vuelva la UI vieja.
- Public metrics calculadas desde `tasks` (sin depender de `escrows`).
- Hook de pagos en frontend resiliente cuando falta tabla `payments`.
- Hook de pagos ahora puede mostrar tx de pago final desde `submissions.payment_tx`.

## 2) Lo que esta bien

- Rutas publicas principales responden (`/`, `/profile`, `/api/v1/public/metrics`, `/api/v1/tasks/available`).
- Rollout ECS completo y estable en ambos servicios.
- Tests smoke clave pasando:
  - `python -m pytest mcp_server/tests/test_p0_routes_idempotency.py -q`
  - `python -m pytest mcp_server/tests/test_admin_auth.py -q`
  - `npm --prefix dashboard run test:run`
  - `npm --prefix dashboard run build`

## 3) Gaps criticos (para ship confiable)

### P0 - Bloqueadores reales

1. `P0-SCHEMA-PAYMENTS`
- Hallazgo: en DB productiva no existen `public.payments` ni `public.escrows`.
- Impacto: no hay ledger canonico de tx; parte del flujo depende de fallback.
- Riesgo: inconsistencias de trazabilidad y reporting financiero.

2. `P0-TX-TRACEABILITY`
- Hallazgo: el sistema muestra estado de pago con datos parciales (tasks/submissions) cuando falta `payments`.
- Impacto: no siempre puedes demostrar de forma uniforme "deposito via facilitador" y "payout final" en una sola vista canonica.
- Riesgo: confusion operativa y auditoria dificil.

3. `P0-WS-ACCESS-CONTROL`
- Hallazgo: `mcp_server/websocket/server.py` mantiene acceso permisivo en `_validate_room_access`.
- Impacto: suscripciones a rooms de task no validadas por ownership/asignacion.
- Riesgo: leakage de eventos entre usuarios.

4. `P0-TEST-COLLECTION`
- Hallazgo: suite backend completa se corta en collection.
- Error: `ImportError` en `mcp_server/tests/test_websocket.py` (drift con API websocket actual).
- Impacto: no hay gate de regresiones full-suite.

### P1 - Alta prioridad

5. `P1-FRONTEND-TYPECHECK`
- Hallazgo: `npm --prefix dashboard run typecheck` falla con muchos errores TS.
- Impacto: refactors inseguros y deuda acumulada.

6. `P1-LINT-BASELINE`
- Hallazgo: `npm --prefix dashboard run lint` falla porque no hay config ESLint detectada.
- Impacto: no hay disciplina de calidad automatizada.

7. `P1-BUNDLE-SPLIT`
- Hallazgo: bundle principal ~5MB (`index-*.js`).
- Impacto: UX lenta en cold load y móviles.

### P2 - Mejora continua

8. `P2-DEPLOY-AUTOMATION`
- Unificar pipeline build/push/register/update/wait/health en script único reproducible.

9. `P2-DOCS-UNIFICATION`
- Consolidar docs de deploy/release; hoy hay documentos con estados mezclados.

## 4) TODO granular (accionable)

## P0
- [ ] `P0-001` Aplicar migracion minima productiva para crear `payments` (y `escrows` si aplica al modelo actual).
- [ ] `P0-002` Definir contrato canonico de pago: columnas minimas obligatorias (`task_id`, `submission_id`, `type`, `status`, `tx_hash`, `amount_usdc`, `network`, `created_at`).
- [ ] `P0-003` Escribir en ese ledger en `approve_submission` (release) y `cancel_task` (refund cuando corresponda).
- [ ] `P0-004` Crear endpoint backend canonico `GET /api/v1/tasks/{task_id}/payment` para no depender de consultas directas del frontend a tablas drifting.
- [ ] `P0-005` En websocket, validar acceso a `task:{id}` por ownership/asignacion.
- [ ] `P0-006` Arreglar `mcp_server/tests/test_websocket.py` para que la suite completa coleccione.
- [ ] `P0-007` QA manual de persistencia de sesion wallet: login una vez, luego `Start Earning` sin pedir firma repetida.

## P1
- [ ] `P1-001` Plan de 2 tandas para bajar errores TS: primero hooks/services, luego pages/components.
- [ ] `P1-002` Definir `eslint.config` (o `.eslintrc`) en dashboard y dejar `lint` ejecutable.
- [ ] `P1-003` Crear smoke e2e de pagos: publish -> accept -> submit -> approve -> verificar tx visible.
- [ ] `P1-004` Code-split por ruta (`agent/*`, `disputes`, `validator`, `analytics`).

## P2
- [ ] `P2-001` Telemetria de errores de pago (Sentry/CloudWatch structured logs con correlation id).
- [ ] `P2-002` Dashboard admin con metricas operativas de conversión y embudo por etapa.
- [ ] `P2-003` Script de "release evidence" que guarde hashes de imagen, task defs y health checks.

## 5) Escenarios no obvios (brainstorm)

- `SCN-001` Aprobacion y cancelacion casi simultaneas sobre la misma tarea.
- `SCN-002` UI stale: worker ve task activa justo cuando ya expiro/cancelo.
- `SCN-003` Facilitador responde verify OK pero falla settle.
- `SCN-004` Reintentos de approve (idempotencia) con latencia alta de DB.
- `SCN-005` Falta parcial de tablas en prod (drift), pero app debe entrar en modo degradado explicito.
- `SCN-006` Sesion wallet restaurada, pero executor RPC falla: no debe forzar reconexion de wallet.
- `SCN-007` Service worker viejo + nuevo index: validar estrategia de cache reset sin loop.
- `SCN-008` Submission con `payment_tx` presente pero `task.status != completed`.

## 6) Validacion exacta para probar tu mismo

## A. Sanidad general
1. Abre `https://execution.market` y verifica que carga landing nueva.
2. Abre `https://execution.market/profile` y confirma que no rompe.
3. Ejecuta:
```powershell
Invoke-WebRequest https://api.execution.market/health | Select-Object -ExpandProperty StatusCode
```
Debe retornar `200`.

## B. Landing con tareas expiradas fallback
1. Si no hay publicadas, revisa que el browser muestre expiradas (no "Failed to fetch tasks").
2. API:
```powershell
Invoke-WebRequest "https://api.execution.market/api/v1/tasks/available?limit=5" | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest "https://api.execution.market/api/v1/tasks/available?limit=5&include_expired=true" | Select-Object -ExpandProperty StatusCode
```
Ambas deben retornar `200`.

## C. Persistencia de sesion wallet
1. Logueate una sola vez.
2. Vuelve a Home y pulsa `Start Earning`.
3. Esperado: no pedir nueva firma de wallet en ese paso.
4. Haz refresh duro y repite.

## D. Flujo pago completo y evidencia de tx
1. Crea tarea con pago x402.
2. Acepta tarea, envia evidencia.
3. Aprueba submission.
4. En detalle de task/worker:
- Debes ver timeline de pago.
- Debe aparecer tx final (`submission.payment_tx` o ledger canonico cuando se habilite P0-001/004).

## E. Metricas publicas
```powershell
Invoke-RestMethod https://api.execution.market/api/v1/public/metrics | ConvertTo-Json -Depth 6
```
Validar:
- `users.registered_workers`
- `users.workers_with_tasks`
- `tasks.live`
- `payments.total_volume_usd`

## F. Pruebas automatizadas minimas (ahora)
```powershell
python -m pytest mcp_server/tests/test_admin_auth.py -q
python -m pytest mcp_server/tests/test_p0_routes_idempotency.py -q
npm --prefix dashboard run test:run
npm --prefix dashboard run build
```

## 7) Enfoque de ejecucion recomendado (ship rapido)

Semana corta (secuencia):
1. Cerrar `P0-001..P0-004` (ledger + endpoint canonico + escritura de tx).
2. Cerrar `P0-005..P0-006` (seguridad websocket + test collection).
3. QA manual de `P0-007` + smoke release.
4. Congelar features 72h y solo bugfix de release.
