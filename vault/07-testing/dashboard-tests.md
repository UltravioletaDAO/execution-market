---
date: 2026-02-26
tags:
  - domain/testing
  - frontend
  - vitest
  - playwright
status: active
aliases:
  - Dashboard Tests
  - Frontend Tests
related-files:
  - dashboard/e2e/
  - dashboard/vitest.config.ts
  - dashboard/playwright.config.ts
---

# Dashboard Tests

Two testing layers cover the React dashboard: unit tests (Vitest) and end-to-end tests (Playwright).

## Unit Tests (Vitest)

```bash
cd dashboard
npm run test
```

- Framework: Vitest (Vite-native test runner)
- Location: `dashboard/src/**/*.test.ts` and `dashboard/src/**/*.test.tsx`
- Coverage: Component rendering, hooks, utility functions
- Speed: Fast (no browser needed)

## End-to-End Tests (Playwright)

```bash
cd dashboard
npm run e2e
```

- Framework: Playwright
- Location: `dashboard/e2e/`
- Coverage: Full user flows in a real browser
- Requires: Running dev server or production build

## Key Components Under Test

| Component | File | What it does |
|-----------|------|--------------|
| TaskApplicationModal | `TaskApplicationModal.tsx` | Task acceptance flow |
| SubmissionForm | `SubmissionForm.tsx` | Evidence upload (uses `submitWork()`) |
| useProfileUpdate | `useProfileUpdate.ts` | Profile update with executor ID |
| AuthContext | `AuthContext.tsx` | Auth state + wallet-based executor lookup |

## CI Integration

Both test suites run as part of the [[ci-pipeline]]:
- `npx tsc --noEmit` -- type checking
- `npm run lint` -- ESLint
- Unit tests run via `npm run test` (when configured in CI)

## UI Language

Dashboard UI text is in **Spanish**:
- Tasks page: "Buscar Tareas", tabs: "Disponibles", "Cerca de mi", "Mis Solicitudes"
- Agent dashboard: "Panel de Agente", "Crear Tarea", "Entregas por Revisar"
- Publisher dashboard: "Panel de Publicador"

## Related

- [[ci-pipeline]] -- where these tests run
- [[golden-flow]] -- backend-focused E2E (separate)
