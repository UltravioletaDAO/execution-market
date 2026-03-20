---
date: 2026-03-03
tags:
  - type/moc
  - domain/operations
  - priority/p0
status: active
aliases:
  - Plan Tracker
  - Master Plans
---

# Master Plans — Tracker

> Estado consolidado de todos los planes del proyecto.
> Ultima actualizacion: 2026-03-20

---

## Planes Completados

### [[MASTER_PLAN_H2A_A2A_HARDENING|H2A + A2A Hardening]]
- **Creado**: 2026-02-18 | **Completado**: ~2026-02-20
- **36/36 tasks** (100%)
- Fixed 5 P0 fund-safety bugs, 1,182 tests added
- Reportes: `docs/reports/AUDIT_H2A_BACKEND_2026-02-18.md`, `AUDIT_AGENT_EXECUTOR_2026-02-18.md`

### [[MASTER_PLAN_ERC8004_COMPLETION|ERC-8004 Completion]]
- **Creado**: 2026-02-21 | **Completado**: ~2026-02-22
- **14/14 tasks** (100%)
- Self-assignment prevention, ERC-8128 auth migration, DynamoDB nonce store, Python+TS signers
- 8 Facilitator operators allowlisted, 12 commits

---

## Planes En Progreso

### [[post-audit-remediation-2026-03|Post-Audit Remediation (March 2026)]]
- **Creado**: 2026-03-19 | **Verificado**: 2026-03-20
- **17/20 tasks DONE, 2 PARTIAL, 1 NOT DONE** (92.5%)
- All P0 code fixes implemented (Phases 1-2), 8 audit tests missing
- Phase 3: OIDC migration pending (3.1)
- Phase 4: SubmissionForm test missing (4.3)
- Phase 5: `as any` 26->12 (5.4)
- Plan: `docs/planning/MASTER_PLAN_POST_AUDIT_2026_03.md`

### [[MASTER_PLAN_UNIFIED_ECOSYSTEM|Unified Ecosystem]]
- **Creado**: 2026-02-21 | **Actualizado**: 2026-02-25
- **18/29 tasks** (~62%)
- Phase 1-4: DONE (Turnstile, IRC bridge, trading signals, skills marketplace)
- **Phase 5**: NOT STARTED — DCC monetizado, file transfer
- **Phase 6**: NOT STARTED — Multichain Turnstile, moderation, Context2Match, 100+ agents

### [[MASTER_PLAN_OBSIDIAN_VAULT|Obsidian Vault]]
- **Creado**: 2026-02-26
- **~8/36 tasks** (~22%)
- Phase 1-2 parcialmente hechos (skeleton + MOCs)
- Pending: concept notes completar, runbooks, ADRs, Dataview dashboards

---

## Planes Diferidos/Parciales

### [[MASTER_PLAN_KARMA_KADABRA_V2|Karma Kadabra V2]]
- **Creado**: 2026-02-19
- **~14/33 tasks** (~40%)
- KK code **removido de este repo** (2026-02-27, 67K+ lines) → `Z:\ultravioleta\dao\karmakadabra\`
- Phase 1 (fund distribution) DONE, Phase 5 (agent economy) PARTIAL
- Phase 4 (cross-chain bridges) y Phase 6 (production deploy) NOT STARTED
- File paths en el plan apuntan a paths que ya no existen en este repo

### [[MASTER_PLAN_OPEN_SOURCE_PREP|Open Source Prep]]
- **Creado**: 2026-02-18
- **~2/39 tasks** (~5%)
- Decision explicita de diferir. Blocker principal: `git-filter-repo` reescribe toda la historia
- **RELEVANTE AHORA**: Si se va a open-source, este plan se activa inmediatamente

---

## Legacy TODOs (Superseded)

| File | Items | Estado |
|------|-------|--------|
| `docs/planning/TODO_NOW.md` | ~200 | SUPERSEDED — La mayoria hecho o capturado en Master Plans |
| `docs/planning/TODO_FUTURE.md` | ~80 | PARCIALMENTE VIGENTE — MeshRelay items ahora live, robot executors/enterprise future |
| `docs/planning/TODO_LAUNCH.md` | ~50 | HISTORICO — Referencia ChambaEscrow (deprecated) |
| `docs/planning/PROGRESS.md` | Log | HISTORICO — Documenta evolucion Jan 10-19 |

---

## Totales

| Metrica | Valor |
|---------|-------|
| Total tasks definidos | 207 |
| Tasks completados | ~109 |
| Completacion global | ~53% |
| Planes completados | 2/7 |
| Planes en progreso | 3/7 |
| Planes diferidos | 2/7 |
