# Launch State Review - 2026-02-08 (Codex)

## Update de ejecución (2026-02-08, noche)

- Scope MVP confirmado: `execution-market + x402r`; `chambaescrow/contracts` queda fuera de evidencia de launch.
- Cerrado bug crítico de auth header:
  - Frontend ahora envía `Authorization: Bearer <VITE_API_KEY>` en mutaciones/reputación.
  - Backend ahora acepta `Authorization` y `X-API-Key` (compatibilidad backward).
- Cerrado bug de configuración `fail-open` en fallback:
  - mutaciones directas quedan bloqueadas siempre que `VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=false`.
- Cerrados gates de calidad que antes estaban blandos:
  - E2E smoke bloqueante en CI/deploy.
  - `mypy` bloqueante en scope backend estable (sin `continue-on-error`).
- Corrida strict API realizada (sin monitor largo): creación confirmada de task `a0edf1b6-ae46-49eb-81fe-bf8661c33c64` en estado `published`.
- Tests largos `--monitor/--auto-approve` difieren al final por instrucción del usuario.

## 1) Executive Snapshot

Decision:
- `GO` para beta controlada inmediatamente.
- `NO-GO` para claim de "production-ready completo" sin más hardening.

Qué está sólido hoy:
- Producción responde estable en `https://api.execution.market`, `https://mcp.execution.market` y `https://execution.market`.
- Backend core local está fuerte: `658 passed, 8 skipped` en `mcp_server`.
- Smoke de producción pasa (`10/10`) y `health/sanity` está en `ok` con `6/6`.

Qué te frena hoy:
- Falta evidencia strict live x402 completa con `--monitor --auto-approve` y hash de payout/refund en esta misma sesión.
- Falta cerrar contrato de auth único de mutaciones agent (ya mitigado con compatibilidad de headers).
- Queda deuda de frontend (warnings lint + tamaño de bundle), pero no bloquea beta controlada inmediata.

---

## 2) Evidence Ejecutada En Esta Revisión

### Calidad local
- `cd mcp_server && python -m pytest -q` -> `658 passed, 8 skipped, 0 failed`.
- `cd dashboard && npm run lint` -> `161 warnings, 0 errors`.
- `cd dashboard && npm run typecheck` -> `0 errors`.
- `cd dashboard && npm run build` -> build OK.
- `cd dashboard && npm run test:run` -> `13 passed`.
- `cd admin-dashboard && npm run lint` -> `17 warnings, 0 errors`.
- `cd admin-dashboard && npm run build` -> build OK.
- `cd mcp_server && python -m mypy . --ignore-missing-imports` -> `578 errors in 85 files`.
- `cd mcp_server && python -m ruff check .` -> `All checks passed`.

### E2E real
- `cd e2e && npm test` (baseline) -> `41 failed, 8 passed`.
- `cd e2e && npx playwright install chromium` -> instalación correcta.
- `cd e2e && npm run test -- --project=chromium --reporter=list` (tras realineación fixtures/specs) -> `36 passed, 0 failed`.

### Smoke/runtime
- `cd scripts && npm run test:smoke` -> 1ª corrida con `HTTP 429` intermitente en endpoints públicos.
- `cd scripts && npm run test:smoke` -> 2ª corrida `10 passed, 0 failed`.
- `cd scripts && npm run report:sanity:strict` -> `status=ok`, `checks=6/6`, `warnings=0`.
- `cd scripts && npm exec -- tsx check-deposit-state.ts`:
  - wallet: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
  - USDC wallet: `7.267674`
  - ETH: `0.000273151457952358` (muy bajo para maniobra larga).

### Runtime público (direct checks)
- `GET https://api.execution.market/health` -> `200`.
- `GET https://api.execution.market/health/sanity` -> `200`.
- `GET https://api.execution.market/api/v1/public/metrics` -> `200`.
- `GET https://api.execution.market/api/v1/tasks/available?limit=1` -> `200`.
- `GET https://execution.market/api/v1/tasks/available?limit=1` -> `200` JSON (ya no HTML ambiguo).

---

## 3) Hallazgos Críticos (por severidad)

## P0

1. [CERRADO 2026-02-08] Producción permitía mutaciones directas de cliente (fallback Supabase).
- Evidence:
  - `.github/workflows/deploy.yml:164` (`VITE_REQUIRE_AGENT_API_KEY=true`)
  - `.github/workflows/deploy.yml:165` (`VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=false`)
  - `.github/workflows/deploy-prod.yml:108` (`VITE_REQUIRE_AGENT_API_KEY=true`)
  - `.github/workflows/deploy-prod.yml:109` (`VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=false`)
  - `dashboard/src/services/tasks.ts:25`
  - `dashboard/src/services/tasks.ts:180`
  - `dashboard/src/services/tasks.ts:422`
  - `dashboard/src/services/tasks.ts:507`
  - `dashboard/src/services/submissions.ts:19`
- Estado: build de deploy endurecido; queda pendiente validar contract final de auth (`COD-260208-A02`).

2. [CERRADO 2026-02-08] Suite E2E no representaba el producto actual.
- Evidence:
  - `e2e/tests/agent.spec.ts:22`
  - `e2e/tests/tasks.spec.ts:77`
  - `e2e/fixtures/mocks.ts:260`
  - `dashboard/src/hooks/useTasks.ts:180`
  - `dashboard/src/hooks/usePublicMetrics.ts:58`
- Resolución: mocks API-first + selectores resilientes i18n; `36/36` tests E2E en verde.

3. No hay evidencia estricta live x402 en esta sesión para claim final de pagos production-ready.
- Evidence:
  - `scripts/test-x402-full-flow.ts` disponible pero no ejecutado en modo live estricto en esta revisión.
- Riesgo: no puedes afirmar robustez end-to-end de pagos con tx hash reciente en esta corrida.

## P1

4. [CERRADO 2026-02-08] Gates de CI/deploy reforzados en smoke E2E y mypy core.
- Evidence:
  - `.github/workflows/ci.yml`
  - `.github/workflows/deploy.yml`
  - commits `5328cc8`, `ef4bba1`

5. Typing debt backend sigue alta fuera del scope gateado.
- Evidence:
  - `mcp_server` -> `578 errors in 85 files`.
- Riesgo: el gate actual cubre módulos core, pero aún hay deuda amplia.

6. [CERRADO 2026-02-08] SDK TypeScript ya no tiene drift de versión.
- Evidence:
  - commit `e3440a9`

7. [CERRADO 2026-02-08] Tests locales de contratos desbloqueados sin deploy key.
- Evidence:
  - commit `7503694`
- Nota: no forma parte del scope MVP de launch `x402r`.

## P2

8. Deuda operativa frontend visible (warnings + bundle).
- Dashboard lint: `161` warnings (top rule `@typescript-eslint/no-explicit-any`).
- Admin lint: `17` warnings.
- Bundle dashboard: `vendor-dynamic` ~`4.15 MB` (`dashboard/dist/assets/vendor-dynamic-BxXMOrgX.js`).

9. Documentación de estado muy fragmentada y una parte está desactualizada.
- Evidence:
  - `docs/planning/TODO_NOW/STATUS_SUMMARY.md:1` (snapshot viejo de 2026-01-27).
  - Múltiples boards activos con criterios distintos.

---

## 4) Perspectivas Para Decidir Sin Perderte

1. Perspectiva Founder (velocidad):
- Ya puedes abrir beta controlada hoy si cierras 4-6 riesgos de lanzamiento.

2. Perspectiva Riesgo de pago:
- Tu mayor riesgo no es uptime; es consistencia de mutaciones y evidencia de pago.

3. Perspectiva Integraciones:
- Si SDK TS no instala y docs/flows de E2E están drifted, crecimiento técnico se frena.

4. Perspectiva Operación:
- Sin board único y sin gates fuertes, vas a seguir iterando sin sentir “ship real”.

---

## 5) Backlog Granular Ship-Now

Formato:
- `ID | Pri | Owner | Tarea | DoD | Validación`

### Track A - Bloqueadores 0-24h

- [x] `COD-260208-A01 | P0 | Frontend+DevOps | Desactivar fallback directo Supabase en producción` | Build prod con `VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=false` y política estricta | deploy workflows actualizados (`deploy.yml`, `deploy-prod.yml`)
- [~] `COD-260208-A02 | P0 | Frontend+Backend | Definir auth contract único para mutaciones agent` | una sola vía soportada en prod (API key o token wallet-bound) | compatibilidad `Authorization`+`X-API-Key` cerrada; falta decisión final wallet-bound
- [x] `COD-260208-A03 | P0 | QA | Reescribir fixtures E2E para API-first (`/api/v1/*`)` | tests dejan de depender de `rest/v1/*` legacy | `cd e2e && npm run test -- --project=chromium --reporter=list` => `36 passed`
- [x] `COD-260208-A04 | P0 | QA | Hacer E2E resiliente a i18n` | selectors por role/testid, no texto fijo ES | specs actualizados (EN/ES regex + roles)
- [~] `COD-260208-A05 | P0 | QA/Ops | Ejecutar 1 strict live x402 y guardar evidencia completa` | comando + task_id + escrow_id + tx hashes + estados finales | strict-api run ejecutado; pendiente corrida final `--monitor --auto-approve`
- [x] `COD-260208-A06 | P0 | Ops | Definir umbral mínimo fondos ETH/USDC para runs live` | abort temprano con mensaje claro | `cd scripts && npm run check:funds:strict` (soporta `--min-usdc` y `--min-eth`)
- [x] `COD-260208-A07 | P0 | Docs | Actualizar estado maestro con snapshot real de hoy` | un documento canónico vigente | `docs/planning/TODO_NOW/STATUS_SUMMARY.md` refrescado 2026-02-08
- [x] `COD-260208-A08 | P0 | Frontend+Backend | Corregir mismatch Authorization vs X-API-Key` | mutaciones agent no fallan por header inválido | `mcp_server/api/auth.py` + `dashboard/src/services/*.ts`

### Track B - Estabilidad 24-72h

- [x] `COD-260208-B01 | P1 | CI | Rehabilitar E2E mínimo bloqueante en CI` | al menos 1 suite smoke E2E bloquea merge | commit `5328cc8`
- [x] `COD-260208-B02 | P1 | Backend | Definir scope mypy gateable (módulos core)` | mypy bloqueante solo en scope limpio | commit `ef4bba1`
- [x] `COD-260208-B03 | P1 | SDK | Corregir drift de `uvd-x402-sdk` en SDK TS` | `npm ci` + `npm test` en `sdk/typescript` pasa | commit `e3440a9`
- [x] `COD-260208-B04 | P1 | Contracts | Permitir tests local hardhat sin private key` | `cd contracts && npm test` corre en hardhat local | commit `7503694` (fuera de scope MVP actual)
- [ ] `COD-260208-B05 | P1 | Frontend | Reducir lint dashboard <= 100 warnings` | warning budget inicial | `npm --prefix dashboard run lint`
- [ ] `COD-260208-B06 | P1 | Frontend | Reducir lint admin <= 10 warnings` | warning budget inicial | `npm --prefix admin-dashboard run lint`
- [ ] `COD-260208-B07 | P1 | Frontend | Bajar chunk principal efectivo < 3 MB` | strategy de code splitting real | `npm --prefix dashboard run build`

### Track C - Consolidación >72h

- [ ] `COD-260208-C01 | P2 | Product+Eng | Unificar boards en un único source of truth` | boards viejos marcados snapshot/archive | docs clean PR
- [ ] `COD-260208-C02 | P2 | Ops | Publicar release evidence bundle automático` | artefacto por deploy con health/smoke/tx | workflow artifact
- [ ] `COD-260208-C03 | P2 | Growth | Instrumentar funnel launch (home -> task apply -> submit)` | métricas visibles y trazables | dashboard métricas

---

## 6) Escenarios Nuevos (Brainstorm de alto valor)

- [ ] `SCN-COD-001` Retry storm de approve y cancel simultáneo sobre misma task.
- [ ] `SCN-COD-002` UI stale intenta submit en task ya cancelada.
- [ ] `SCN-COD-003` Deploy green sin evidencia live tx (bloquear claim).
- [ ] `SCN-COD-004` Integrador usa endpoint legado por docs desactualizada.
- [ ] `SCN-COD-005` API responde 429 en burst de métricas públicas (debe degradar limpio).
- [ ] `SCN-COD-006` Fallback directo Supabase activado accidentalmente en prod.
- [ ] `SCN-COD-007` Reconciliación tardía: tx existe pero UI aún no refleja pago.
- [ ] `SCN-COD-008` Wallet session válida pero identidad/role inválida en mutation path.
- [ ] `SCN-COD-009` E2E pasa en un idioma y falla en otro.
- [ ] `SCN-COD-010` Rotura de SDK TS por drift de dependencia no publicada.

---

## 7) Recomendación De Lanzamiento Inmediato

Si quieres lanzar "ya":
1. Haz launch beta controlado hoy.
2. Cierra `COD-260208-A02`, `COD-260208-A05` y `COD-260208-A06` antes de claim público de production-ready.
3. Mantén freeze de features nuevas hasta cerrar esos P0.

---

## 8) Nota Terra4mice

Se agregó tracking adicional en `terra4mice.spec.yaml` para los gaps detectados en esta revisión.

Limitación operativa en este entorno:
- CLI `terra4mice` no está instalada, por lo que `terra4mice.state.json` no se puede regenerar automáticamente en esta sesión.
