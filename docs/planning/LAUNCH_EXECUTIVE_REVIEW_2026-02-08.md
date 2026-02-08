# Launch Executive Review - 2026-02-08 (Exhaustivo)

## 1) Estado Ejecutivo (hoy)

**Decision:**
- **GO** para beta controlada (seguir shippeando fixes).
- **NO-GO** para claim de "production-ready" completo.

**Por que NO-GO:**
1. Flujos criticos del dashboard de agent/worker siguen mutando datos directo en Supabase y saltan endpoints backend con reglas de pago.
2. El suite backend completo no es determinista por contaminacion global de tests (falla en full-run, pasa aislado).
3. Agent card en produccion publica URL `http://...` en vez de `https://...`.
4. El endpoint `/health/sanity` reporta advertencias de pagos con una consulta inconsistente (falso positivo operativo).
5. Topologia API/documentacion sigue contradictoria (`execution.market/api/*` devuelve HTML SPA).

## 2) Evidencia Ejecutada (2026-02-08)

### 2.1 Calidad local
- `dashboard`: `typecheck` OK, `lint` OK (168 warnings), `test:run` OK (13/13), `build` OK.
- `admin-dashboard`: `build` OK, `lint` OK tras `npm install` (17 warnings).
- `mcp_server`: full suite `637 passed, 21 failed, 8 skipped`.
- `mcp_server` sin `tests/e2e/test_escrow_flows.py`: `636 passed, 0 failed, 8 skipped`.
- `mcp_server/tests/test_mcp_tools.py` aislado: `32 passed`.

### 2.2 Produccion runtime
- `https://execution.market` -> 200 HTML.
- `https://execution.market/api/v1/tasks/available?limit=1` -> 200 HTML (SPA), no JSON.
- `https://mcp.execution.market/health` -> 200 healthy.
- `https://api.execution.market/health` -> 200 healthy.
- `https://mcp.execution.market/api/v1/tasks/available?limit=1` -> 200 JSON.
- `https://api.execution.market/api/v1/tasks/available?limit=1` -> 200 JSON.

### 2.3 Smoke test
- `cd scripts && npm exec -- tsx smoke-test.ts` -> **10 passed, 0 failed**.
- `/health/sanity` en vivo: `checks_passed=5/6`, warning `completed_no_payment`.

### 2.4 Preflight fondos (Base)
- `cd scripts && npm exec -- tsx check-deposit-state.ts`
- Wallet: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
- USDC wallet: `7.277674`
- Relay: `0.01`
- Vault: `0.14`
- ETH restante: `0.000273151457952358` (muy bajo para maniobra prolongada)

### 2.5 Tracking
- `docs/planning/TODO_NOW.md`: 205 items (18 done / 187 pending).
- `terra4mice.state.json`: 120 resources (109 implemented / 11 missing).
- Drift de tracking sigue alto.

## 3) Hallazgos Criticos (ordenados por severidad)

## P0

1. **Bypass de backend en operaciones de negocio/pago desde UI**
- `dashboard/src/services/tasks.ts:127` crea tareas por insercion directa en `tasks`.
- `dashboard/src/services/tasks.ts:253` cancela tarea con update directo de estado.
- `dashboard/src/services/submissions.ts:23` y `dashboard/src/services/submissions.ts:85` inserta submission y cambia estado sin endpoint backend.
- `dashboard/src/pages/agent/CreateTask.tsx:16` + `dashboard/src/pages/agent/CreateTask.tsx:752` usa ese servicio directo.
- `dashboard/src/pages/agent/TaskManagement.tsx:14` + `dashboard/src/pages/agent/TaskManagement.tsx:522` usa cancel directo.
- `dashboard/src/components/SubmissionForm.tsx:13` + `dashboard/src/components/SubmissionForm.tsx:336` usa submit directo.
- **Impacto:** se puede romper enforcement de x402/escrow, auditoria de pagos e idempotencia central.

2. **Suite backend no determinista por contaminacion global de `sys.modules`**
- `mcp_server/tests/e2e/test_escrow_flows.py:29` a `mcp_server/tests/e2e/test_escrow_flows.py:35` reemplaza `mcp.server.fastmcp.FastMCP` globalmente con `MagicMock`.
- En corrida completa, esto rompe `mcp_server/tests/test_mcp_tools.py` con `Mock object has no attribute 'tool'`.
- **Impacto:** señal de calidad falsa, builds inestables, riesgo de regresiones escondidas.

3. **Agent card en produccion anuncia URL insegura (`http`)**
- Runtime en vivo: `/.well-known/agent.json` devuelve `url=http://api.execution.market/a2a/v1`.
- Codigo de fallback existe en `mcp_server/a2a/agent_card.py:584` pero en runtime parece prevalecer `EM_BASE_URL` inseguro.
- **Impacto:** clientes A2A estrictos pueden rechazar/penalizar integracion.

4. **Observabilidad de pagos degradada por chequeo de sanidad inconsistente**
- `mcp_server/health/endpoints.py:522` no selecciona `payment_tx` ni `escrow_tx`.
- `mcp_server/health/endpoints.py:544` y `mcp_server/health/endpoints.py:545` validan campos que nunca se seleccionaron.
- **Impacto:** warning persistente/falso en produccion, baja confianza operativa.

## P1

5. **Topologia API/documentacion contradice comportamiento real**
- `docs-site/docs/api/reference.md:3` usa base URL `https://execution.market/api/v1`.
- Runtime: `execution.market/api/v1/*` devuelve HTML SPA.
- `dashboard/src/hooks/useTasks.ts:180` y `dashboard/src/hooks/useTaskPayment.ts:71` usan `api.execution.market` (correcto).
- **Impacto:** integraciones externas fallan por copiar docs.

6. **CI permite que backend tests fallen sin bloquear**
- `.github/workflows/ci.yml:101` usa `continue-on-error: true` para tests backend.
- `.github/workflows/ci.yml:162` mantiene e2e deshabilitado.
- `.github/workflows/deploy.yml:54` tambien permite tests backend sin bloquear.
- **Impacto:** release gate blando; se puede desplegar con regresiones.

7. **Drift de tracking entre TODO y terra4mice**
- TODO_NOW sigue con backlog gigante heredado.
- terra4mice marca recursos "implemented" aunque hay gaps reales de launch.
- **Impacto:** decisiones de shipping basadas en señales inconsistentes.

## P2

8. **Performance y debt operativa**
- `dashboard` build reporta chunk principal ~5.2MB.
- `dashboard lint` y `admin lint` pasan, pero acumulan warnings (168/17).
- **Impacto:** conversion movil y mantenibilidad.

## 4) Lo que SI esta fuerte hoy

1. Produccion sana a nivel health (`api` y `mcp` con `healthy`).
2. Smoke test read-only pasa completo (10/10).
3. Dashboard principal hoy compila, typecheck pasa y tests unitarios pasan.
4. Backend core pasa mas de 600 pruebas cuando se elimina contaminacion cruzada.
5. Flujo x402 tiene preflight y balance verificable en Base.

## 5) Lo que falta para declarar "Production Ready"

1. Mover mutaciones criticas del dashboard a endpoints backend (API-first) con idempotencia.
2. Reparar aislamiento de tests para que `pytest -q` full sea verde y estable.
3. Forzar `https` en Agent Card en runtime (env + proxy trust).
4. Corregir sanity check para pagos y usarlo como semaforo real.
5. Unificar dominio API canonico y comportamiento de `execution.market/api/*`.
6. Endurecer CI: tests backend y checks criticos deben bloquear deploy.
7. Unificar tracking operativo en un solo board ejecutable.

## 6) Backlog Granular Ship-Now (72h)

Formato: `ID | Prioridad | Owner | Tarea | Definition of Done | Validacion`

- [ ] `LCH-260208-001 | P0 | Backend | Aislar mock global en escrow e2e (evitar contaminar FastMCP)` | `pytest -q` full sin flakiness de orden | `cd mcp_server && python -m pytest -q`
- [ ] `LCH-260208-002 | P0 | Backend | Corregir /health/sanity check para payment evidence real` | warning `completed_no_payment` solo cuando aplica de verdad | `curl https://api.execution.market/health/sanity`
- [ ] `LCH-260208-003 | P0 | Backend/Infra | Forzar `EM_BASE_URL=https://api.execution.market` en runtime` | agent card publica URL https en ambos dominios | `curl https://api.execution.market/.well-known/agent.json`
- [ ] `LCH-260208-004 | P0 | Frontend | Reemplazar `createTask()` directo por POST backend con `X-Payment`` | crear task desde UI requiere flujo x402 | prueba manual + API logs
- [ ] `LCH-260208-005 | P0 | Frontend | Reemplazar `cancelTask()` directo por endpoint `/tasks/{id}/cancel`` | cancel desde UI genera payload escrow/refund coherente | API response incluye `escrow.status`
- [ ] `LCH-260208-006 | P0 | Frontend | Reemplazar `submitWork()` directo por endpoint backend` | submission entra por API con trazabilidad completa | revisar `submissions` + logs API
- [ ] `LCH-260208-007 | P0 | Docs | Base URL oficial: `api.execution.market` en docs-site y guias` | no quedan referencias publicas a `execution.market/api/v1` | `rg -n "execution.market/api/v1" docs-site docs README.md`
- [ ] `LCH-260208-008 | P0 | Infra | Definir comportamiento oficial de `execution.market/api/*`` | proxy real o 404/redirect explicito | `curl -i https://execution.market/api/v1/tasks/available?limit=1`
- [ ] `LCH-260208-009 | P0 | CI | Quitar `continue-on-error` en tests backend` | test failure bloquea CI/deploy | ejecutar pipeline CI en PR
- [ ] `LCH-260208-010 | P0 | QA | Ejecutar 1 run live estricta x402 con evidencia completa` | command + task_id + tx hash + estado final documentados | `scripts/test-x402-full-flow.ts -- --count 1 --strict-api`

- [ ] `LCH-260208-011 | P1 | Frontend | Introducir API client canónico para mutaciones` | `services/tasks.ts` y `services/submissions.ts` dejan de escribir directo en Supabase | tests + grep de `.from('tasks').insert` en servicios UI
- [ ] `LCH-260208-012 | P1 | Backend | Endpoint de auditoria de pagos por task con consistency flags` | mismatch payout/status visible en API | endpoint + unit tests
- [ ] `LCH-260208-013 | P1 | Frontend | Mostrar origen de settlement (`facilitator|manual`) en timeline` | usuario distingue flows productivos vs debug | snapshot UI
- [ ] `LCH-260208-014 | P1 | CI | Agregar smoke job post-deploy con artifact obligatorio` | deploy falla si smoke falla | workflow artifact presente
- [ ] `LCH-260208-015 | P1 | Frontend | Reducir warnings ESLint dashboard < 50` | lint warnings <= 50 | `npm --prefix dashboard run lint`
- [ ] `LCH-260208-016 | P1 | Frontend | Reducir warnings ESLint admin < 5` | lint warnings <= 5 | `npm --prefix admin-dashboard run lint`
- [ ] `LCH-260208-017 | P1 | Frontend | Route-level code splitting en rutas agent/analytics` | chunk principal < 2.5MB | `npm --prefix dashboard run build`
- [ ] `LCH-260208-018 | P1 | Ops | Definir umbral minimo de fondos (ETH/USDC) para runs live` | run aborta temprano con mensaje claro | `npm --prefix scripts exec -- tsx check-deposit-state.ts`

- [ ] `LCH-260208-019 | P2 | Product | Unificar backlog activo (archivar docs de launch obsoletos)` | un solo board vivo para release | PR de docs
- [ ] `LCH-260208-020 | P2 | Growth | Instrumentar conversion funnel: home -> start earning -> submit` | dashboard con tasas de conversion | metricas visibles
- [ ] `LCH-260208-021 | P2 | Security | Revisar query-param auth legado y telemetria de leaks` | sin secretos en URLs/logs | tests + scan logs
- [ ] `LCH-260208-022 | P2 | DevEx | Script unico de release evidence bundle` | genera md con commands, tx, task ids, health | `./.claude/scripts/release-notes.sh`

## 7) Escenarios Brainstorm (no obvios, alta utilidad)

- [ ] `SCN-260208-001` Agent crea task por UI sin x402 real, pero task parece valida en dashboard.
- [ ] `SCN-260208-002` Cancel desde UI deja task cancelada sin evento de refund/auth-expiry en ledger.
- [ ] `SCN-260208-003` Submission via UI directa entra aunque API policy la hubiera rechazado.
- [ ] `SCN-260208-004` Retry storm de approve (10x) con red movil inestable.
- [ ] `SCN-260208-005` Retry storm de cancel (10x) durante degradacion del facilitator.
- [ ] `SCN-260208-006` Agent card `http://` provoca rechazo silencioso en cliente enterprise.
- [ ] `SCN-260208-007` Integrador copia docs viejas (`execution.market/api/v1`) y reporta 200 HTML.
- [ ] `SCN-260208-008` Full suite verde local, roja en CI por orden diferente de tests.
- [ ] `SCN-260208-009` Health reporta warning de pagos aunque task tiene tx real (falso positivo).
- [ ] `SCN-260208-010` `--strict-api false` en script de prueba produce evidencia no-facilitator sin marcar.
- [ ] `SCN-260208-011` ETH cae por debajo de umbral y rompe run live a mitad.
- [ ] `SCN-260208-012` Task completada con tx hash, pero UI no la muestra por fallback legacy.
- [ ] `SCN-260208-013` `execution.market/api/*` cachea HTML y se usa en SDK externo por accidente.
- [ ] `SCN-260208-014` Agent cancela en paralelo con auto-approve worker.
- [ ] `SCN-260208-015` Submission llega cuando task expiro y UI stale la sigue mostrando editable.
- [ ] `SCN-260208-016` Pagos en tabla canonical y legacy divergen por sincronizacion parcial.
- [ ] `SCN-260208-017` Rollback de deploy deja frontend apuntando a dominio API no canonico.
- [ ] `SCN-260208-018` E2E deshabilitado en CI permite regression en auth Dynamic.
- [ ] `SCN-260208-019` Wallet session se restaura, pero executor profile lookup falla transiente.
- [ ] `SCN-260208-020` Worker con baja reputacion se asigna por bypass de servicio directo.

## 8) Perspectivas (para decidir rapido, no perderte)

1. **Perspectiva Founder (ship velocity):** ya puedes lanzar beta controlada hoy, pero no vendas "production-ready" aun.
2. **Perspectiva Riesgo Operativo:** el mayor riesgo no es uptime; es consistencia de reglas de negocio entre UI y backend.
3. **Perspectiva Confianza de Integradores:** dominios/docs inconsistentes cuestan mas soporte que arreglarlo ahora.
4. **Perspectiva Dinero/Payments:** lo critico es trazabilidad verificable por API, no solo que exista tx en algun lado.
5. **Perspectiva QA:** sin full-suite determinista, cada release es una loteria estadistica.
6. **Perspectiva Escala:** tech debt de warnings/chunk size no mata hoy, pero afecta conversion y costo de cambio.

## 9) Plan de Ejecucion Inmediata

### 0-6h
- Congelar features nuevas.
- Cerrar `LCH-260208-001..006`.
- Revalidar smoke + health + full pytest.

### 6-24h
- Cerrar `LCH-260208-007..010`.
- Publicar evidencia unica de launch candidate (commands + tx + task status).

### 24-72h
- Cerrar `LCH-260208-011..018`.
- Abrir beta publica con guardrails y rollback claro.

## 10) Regla de Oro (para no volver al caos)

No se considera "hecho" si no tiene:
1. comando de validacion repetible,
2. evidencia de salida,
3. estado sincronizado en tracking,
4. impacto visible en flujo real de usuario.

## 11) Terra4mice Sync (2026-02-08)

Se agregaron nuevos recursos de tracking en `terra4mice.spec.yaml`:
- `launch_20260208_backend_full_suite_isolation`
- `launch_20260208_dashboard_api_first_mutations`
- `launch_20260208_health_sanity_payment_evidence_fix`
- `launch_20260208_agent_card_https_runtime`
- `launch_20260208_api_domain_contract`
- `launch_20260208_ci_hard_gate_backend`
- `launch_20260208_launch_board_sync`

Nota operativa:
- CLI `terra4mice` no esta instalada en este entorno hoy, por eso el `state.json` no se regenero automaticamente en esta sesion.
