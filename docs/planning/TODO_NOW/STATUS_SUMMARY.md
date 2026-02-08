# Estado Ship-Now (Execution Market) — 2026-02-08

## Snapshot Actual

- Scope MVP activo: `execution-market` + `x402r`.
- Scope fuera de launch MVP: `contracts/chambaescrow` (solo diagnóstico, no evidencia de producción).
- Decisión operativa: `GO` para beta controlada; `NO-GO` para claim full production-ready hasta cerrar evidencia live final.

## Lo Ya Cerrado (Esta Racha de Trabajo)

- Deploy hardening para mutaciones agent:
  - `VITE_REQUIRE_AGENT_API_KEY=true`
  - `VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=false`
- E2E smoke bloqueante reactivado en CI/deploy.
- `mypy` bloqueante en scope backend estable (sin `continue-on-error`).
- Drift SDK TypeScript corregido (`uvd-x402-sdk` alineado a `2.20.0`).
- Header auth mismatch corregido (`Authorization: Bearer` + compatibilidad `X-API-Key`):
  - backend: `mcp_server/api/auth.py`, `mcp_server/api/middleware.py`
  - frontend: `dashboard/src/services/tasks.ts`, `dashboard/src/services/submissions.ts`, `dashboard/src/services/reputation.ts`, `dashboard/src/services/api.ts`
- Lógica de fallback endurecida a `fail-closed`:
  - si `VITE_ALLOW_DIRECT_SUPABASE_MUTATIONS=false`, no hay mutación directa aunque falte `VITE_REQUIRE_AGENT_API_KEY`.
  - aplicado en create/cancel/assign/approve/reject/request-more-info.
- Gate de fondos live agregado:
  - `npm run check:funds:strict` valida umbrales mínimos de ETH/USDC y retorna exit code `1` si no alcanza.
  - parámetros: `--min-usdc`, `--min-eth`, `--strict`.

## Evidencia x402 Ejecutada Hoy

- Comando:
  - `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api`
- Resultado:
  - Task creada: `a0edf1b6-ae46-49eb-81fe-bf8661c33c64`
  - Estado: `published`
  - Wallet: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
  - Modo: strict API (sin monitor/auto-approve)
- Nota:
  - No hay `escrow_tx`/`payment_tx` final porque no se corrió la fase larga de monitoreo/aprobación en esta tanda.

## Bloqueadores Reales Pendientes

1. Ejecutar corrida strict live final con `--monitor --auto-approve` y capturar evidencia completa:
   - task IDs
   - `escrow_id` / `escrow_tx`
   - `payment_tx`
   - estados finales
2. Definir cierre final del contrato de auth para mutaciones agent (decisión producto: solo API key vs wallet-bound token).
3. Reducir deuda frontend no-bloqueante pero relevante de operación (`lint warnings` y tamaño de bundle).

## Pruebas Largas Diferidas (Por Instrucción de Usuario)

- `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api --monitor`
- `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api --monitor --auto-approve`

Estas corridas quedan explícitamente para el bloque final de validación.
