# Improvement + Scenarios Board - 2026-02-08 (Codex)

Status legend:
- `[ ]` pending
- `[~]` in progress
- `[x]` done

## 1) Launch-Critical Improvements

- [x] `IMP-COD-001 | P0 | Desactivar mutaciones directas Supabase en producción`
- [~] `IMP-COD-002 | P0 | Definir contrato único de auth para mutaciones de agent`
- [ ] `IMP-COD-003 | P0 | Ejecutar strict live x402 con evidencia completa`
- [x] `IMP-COD-004 | P0 | Alinear E2E a API-first + auth actual + i18n resiliente`
- [x] `IMP-COD-005 | P0 | Rehabilitar E2E bloqueante mínimo en CI`
- [x] `IMP-COD-006 | P1 | Corregir drift `uvd-x402-sdk` en SDK TypeScript`
- [x] `IMP-COD-007 | P1 | Permitir `hardhat test` local sin deploy key`
- [x] `IMP-COD-008 | P1 | Definir scope mypy bloqueante (baseline realista)`
- [ ] `IMP-COD-009 | P1 | Reducir lint dashboard <= 100 warnings`
- [ ] `IMP-COD-010 | P1 | Reducir lint admin <= 10 warnings`
- [ ] `IMP-COD-011 | P1 | Reducir chunk crítico dashboard < 3 MB`
- [ ] `IMP-COD-012 | P1 | Estabilizar rate-limit para métricas públicas`
- [~] `IMP-COD-013 | P1 | Unificar docs de estado (retirar snapshot desactualizados)`
- [x] `IMP-COD-014 | P0 | Alinear Authorization Bearer vs X-API-Key en backend+frontend`

## 2) Escenarios Nuevos De Validación

- [ ] `SCN-COD-001 | Approve/cancel retry storm (idempotencia fuerte)`
- [ ] `SCN-COD-002 | Submit desde cliente stale en task cancelada`
- [ ] `SCN-COD-003 | Run live con fondos al límite (ETH/USDC threshold check)`
- [ ] `SCN-COD-004 | 429 burst en endpoints públicos bajo polling agresivo`
- [ ] `SCN-COD-005 | tx on-chain existe pero sincronización DB retrasada`
- [ ] `SCN-COD-006 | idioma EN/ES altera visibilidad de elementos críticos UI`
- [ ] `SCN-COD-007 | mismatch wallet conectada vs identidad autorizada`
- [ ] `SCN-COD-008 | pipeline green sin evidencia live payment (debe bloquear claim)`
- [ ] `SCN-COD-009 | integrador consume endpoint legacy por ejemplo de docs`
- [ ] `SCN-COD-010 | fallback directo Supabase queda habilitado tras deploy`

## 3) Orden Recomendado (48h)

1. `IMP-COD-001`
2. `IMP-COD-002`
3. `IMP-COD-003`
4. `IMP-COD-004`
5. `IMP-COD-005`
6. `IMP-COD-006`
7. `IMP-COD-007`

## 4) Nota Operativa

- Pruebas largas live x402 (`--monitor`, `--auto-approve`) quedan movidas al bloque final de validación.
- Hasta correr ese bloque final, el estado de pagos queda `in_progress` y no se debe hacer claim de production-ready completo.
