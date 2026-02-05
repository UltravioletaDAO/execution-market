# Ship-Now Audit - 2026-02-05

This document is a single source of truth for:
- what is actually working today,
- what is partially implemented,
- what is blocking production launch,
- and the exact granular TODO list to ship fast.

---

## 1) Scope and method used

Repository surfaces reviewed:
- `mcp_server/`
- `dashboard/`
- `admin-dashboard/`
- `supabase/`
- `infrastructure/`
- `scripts/`
- `docs/planning/`
- root docs (`README.md`, `PLAN.md`, etc.)

Technical validation executed:
- Backend tests:
  - `python -m pytest -q`
  - `python -m pytest -q --ignore=tests/test_websocket.py`
- Frontend tests/build:
  - `dashboard`: `npm run typecheck`, `npm run lint`, `npm run test:run`, `npm run build`
  - `admin-dashboard`: `npm run build`, `npm run lint`
  - `docs-site`: `npm run build`
- Runtime smoke checks:
  - local `uvicorn main:app`
  - `GET /health`
  - `GET /mcp/`
  - `GET /mcp/sse`
  - `GET /openapi.json`

---

## 2) Executive status snapshot

| Area | Status | Notes |
|---|---|---|
| Core backend API | `YELLOW` | Main flows exist, but there are production gaps and legacy/duplicate endpoint surface. |
| Payment release on approval | `YELLOW` | Implemented via SDK call path, but needs full live validation and hardening. |
| Cancellation refund | `RED` | Current path still marks manual refund scenarios instead of guaranteed automated refund. |
| Backend automated tests | `YELLOW` | 553 pass, but 40 fail (+1 collection error in full run). |
| Dashboard build | `YELLOW` | `vite build` passes, but very large bundle and multiple warnings. |
| Dashboard type safety | `RED` | `tsc --noEmit` fails with many typing errors. |
| Dashboard test setup | `RED` | Vitest includes Playwright specs and fails suite setup. |
| Linting | `RED` | No ESLint config in dashboard; admin lint script references eslint not installed. |
| Admin dashboard build | `YELLOW` | Builds successfully; chunk warning >500k. |
| Runtime health defaults | `RED` | Local `/health` returns 503 when core env vars are absent. |
| Docs consistency | `RED` | Significant contradiction across launch/prod docs and TODO docs. |

---

## 2.1) Post-audit execution update (2026-02-05)

Implemented immediately after this audit:
- `DONE` `P0-PAYMENT-IDEMPOTENCY`:
  - idempotent approve behavior for already accepted submissions.
  - duplicate approve retries now return stable success response.
- `DONE` `P0-PLACEHOLDER-ROUTES`:
  - `/earnings` now renders real earnings UI flow.
  - `/agent/tasks` now renders task management UI.
  - `/agent/tasks/new` now renders create-task UI.
- `DONE` `P0-AUTH-HARDENING` (phase 1):
  - admin auth now prefers `Authorization: Bearer` or `X-Admin-Key`.
  - query-param admin auth remains only as legacy fallback.
- `DONE` cancellation path hardening:
  - added refund helper in x402 SDK wrapper.
  - cancel flow now attempts automatic refund for funded/deposited escrows.
  - authorize-only flow still uses EIP-3009 expiry (no funds moved).
  - cancel endpoint now returns idempotent success when task is already cancelled.
- `DONE` `P0-WS-VALIDATION`:
  - websocket token/api-key validation is enforced.
  - strict mode (`WS_REQUIRE_AUTH_TOKEN=true`) blocks unauthenticated agent auth.
- `DONE` reputation ownership hardening:
  - worker rating endpoint validates task ownership + assigned worker wallet.
  - agent rating endpoint validates task-agent identity coherence.
- `DONE` `P0-API-CANONICAL` (legacy route deprecation):
  - `/api/v1/tasks/apply` returns `410` with canonical path hint.
  - `/api/v1/submissions` returns `410` with canonical path hint.
- `DONE` schema alignment safety:
  - backend now prefers `task_applications` and falls back to legacy `applications`.
  - fallback is logged explicitly to force migration visibility.
- Validation:
  - focused backend tests added and passing:
    - `mcp_server/tests/test_p0_routes_idempotency.py`
    - `mcp_server/tests/test_admin_auth.py`
    - `mcp_server/tests/test_websocket_auth_hardening.py`
    - `mcp_server/tests/test_reputation_ownership.py`
    - `mcp_server/tests/test_schema_alignment_applications.py`
  - `dashboard` production build remains green after route changes.

---

## 3) What the code says (evidence highlights)

### 3.1 Backend test evidence

- Full run:
  - `python -m pytest -q` fails at collection due `WebSocketMessage` import mismatch in `tests/test_websocket.py` against `mcp_server/websocket/__init__.py`.
- Partial run (excluding collector error file):
  - `python -m pytest -q --ignore=tests/test_websocket.py`
  - Result: `553 passed`, `40 failed`, `8 skipped`.

Main failing clusters:
- MCP tools tests around mocked MCP registration expectations.
- Platform config defaults mismatch (`0.01` vs tests expecting `0.25`).
- Reputation tests tied to old Bayesian API signature/model.
- WebSocket event rate limiter behavior mismatch.

### 3.2 Frontend evidence

`dashboard`:
- `npm run typecheck` fails with many TS errors.
- `npm run lint` fails: missing ESLint config.
- `npm run test:run` fails because Vitest is trying to execute Playwright files in `dashboard/e2e/`.
- `npm run build` passes but with:
  - giant main chunk (`~4.97 MB` minified),
  - CSS ordering warning,
  - node crypto/export warnings from dependencies.

`admin-dashboard`:
- `npm run build` passes.
- `npm run lint` fails because eslint is not installed in this package while the script expects it.

`docs-site`:
- build passes.

### 3.3 Runtime smoke checks

Local server (`uvicorn main:app`):
- `GET /health` returned `503` with `unhealthy` due missing required Supabase/X402 env configuration.
- `GET /mcp/sse` returned `404`.
- `GET /mcp/` returned `406` with plain GET.

### 3.4 Concrete code-level gaps

Payment cancellation refund gap:
- `mcp_server/api/routes.py:1058` to `mcp_server/api/routes.py:1069` still marks `needs_manual_refund`.

No explicit refund helper in current SDK wrapper:
- `mcp_server/integrations/x402/sdk_client.py` contains `verify_task_payment` and `settle_task_payment`, but no direct refund helper method.

Legacy + current endpoint mix in main app:
- router mounting in `mcp_server/main.py:276`
- legacy direct endpoints continue below (example: `mcp_server/main.py:469`, `mcp_server/main.py:533`), creating mixed API surface.

Schema drift risk (`applications` vs `task_applications`):
- code uses `applications` in `mcp_server/supabase_client.py:306`
- canonical migration table is `task_applications` in `supabase/migrations/001_initial_schema.sql:264`.

Auth/security TODOs still in critical surfaces:
- admin auth TODO: `mcp_server/api/admin.py:37`
- websocket token/API key validation TODOs: `mcp_server/websocket/server.py:373`, `mcp_server/websocket/server.py:879`
- ownership checks TODOs in reputation API: `mcp_server/api/reputation.py:335`, `mcp_server/api/reputation.py:387`.

Placeholder/partial product routes in shipped dashboard:
- `dashboard/src/App.tsx:98` earnings page marked "en desarrollo".
- `dashboard/src/App.tsx:174` agent tasks page marked "en desarrollo".

Tests/scripts that bypass business path in fallback mode:
- `scripts/test-x402-full-flow.ts:599` to `scripts/test-x402-full-flow.ts:613` fallback to direct Supabase updates when API approval fails (no payment settlement).

---

## 4) Done vs missing (functional perspective)

## What is effectively done

- Core REST + MCP structure exists and runs.
- Worker apply/submit and agent approve/reject/cancel endpoints exist.
- Payment settle path is implemented in approval route.
- ERC-8004 integration call path exists on approval.
- Admin dashboard and docs-site can produce production build artifacts.
- Large part of backend test suite passes.

## What is only partially done

- End-to-end production confidence:
  - tests are mixed (many pass, but key clusters fail),
  - real payment tests are gated/skipped by env and secrets.
- Frontend quality gates:
  - build is green, but typecheck/lint/tests are red.
- Docs and status tracking:
  - multiple contradictory "production truths".

## What is missing or blocking launch confidence

- Deterministic cancellation refund path (automated, auditable, idempotent).
- Single canonical API surface (remove legacy duplicates or formally deprecate).
- Schema naming consistency and typed client alignment.
- Frontend release discipline (no placeholder routes in default user journey).
- CI gates that actually represent production risk (typecheck/lint/unit/integration/e2e smoke).

---

## 5) Contradictions and drift you should resolve first

Domain/documentation contradiction:
- `README.md` positions API under `mcp.execution.market`,
- several internal docs and code examples still use `api.execution.market`.
- This causes integration and ops confusion during incidents.

Status contradiction:
- Some docs claim "production completed",
- while launch/status docs still report degraded health and manual infra steps.

Backlog contradiction:
- `docs/planning/TODO_NOW.md` has 205 tracked items (`18 done`, `187 pending`),
- but status summaries claim several streams as completed.

Product/UI contradiction:
- README describes agent/earnings pages as shipped experiences,
- current route implementations still show placeholder screens.

---

## 6) P0 blockers for a production launch (must-fix)

1. `P0-REFUND-AUTO`
- Implement deterministic refund execution path for cancelled funded tasks.
- Acceptance: no `needs_manual_refund` branch remains for normal cancellation flow.

2. `P0-PAYMENT-IDEMPOTENCY`
- Add idempotency around approve/release and cancel/refund operations.
- Acceptance: duplicate requests do not double-settle or double-refund.

3. `P0-API-CANONICAL`
- Decide canonical worker/submit endpoints and deprecate legacy duplicates.
- Acceptance: one documented path per action; deprecated endpoints return explicit migration hints.

4. `P0-SCHEMA-ALIGNMENT`
- Reconcile `applications` vs `task_applications` usage across backend and docs.
- Acceptance: one table name everywhere in code, migrations, docs, and tests.

5. `P0-HEALTH-FAIL-FAST`
- Add startup config validation for required production env vars.
- Acceptance: startup clearly fails on missing critical secrets in production mode.

6. `P0-AUTH-HARDENING`
- Replace query-param admin key with header-based auth plus audit identity.
- Acceptance: no admin secret in query strings; audit includes actor identity.

7. `P0-WS-VALIDATION`
- Enforce websocket token/API-key validation (remove TODO behavior).
- Acceptance: unauthorized clients cannot subscribe/broadcast.

8. `P0-DASHBOARD-QA-GATE`
- Make `dashboard` typecheck, lint, unit tests green.
- Acceptance: CI fails on regressions before deploy.

9. `P0-VITEST-SCOPE`
- Exclude Playwright e2e specs from Vitest.
- Acceptance: `npm run test:run` executes only unit/integration tests.

10. `P0-PLACEHOLDER-ROUTES`
- Remove or hide incomplete pages from primary nav/routes (`/earnings`, `/agent/tasks`).
- Acceptance: users never land on "en desarrollo" in production path.

11. `P0-BUNDLE-SPLIT`
- Apply route-level lazy loading and split heavy wallet/auth bundles.
- Acceptance: main JS chunk materially reduced and below defined budget.

12. `P0-DOCS-TRUTH`
- Publish one authoritative "current production topology" doc.
- Acceptance: all docs reference same API domain and deploy path.

---

## 7) Granular ship-fast TODO list

### 7.1 Backend and payments (P0)

- [x] Add `refund_task_payment(...)` (or equivalent) in `mcp_server/integrations/x402/sdk_client.py`.
- [x] In `mcp_server/api/routes.py`, replace manual-refund branch with real refund execution.
- [x] Persist refund tx/hash and reason in payment audit records (`payments` table).
- [ ] Add explicit state machine guards: `authorized -> released/refunded/cancelled`.
- [x] Add idempotency key handling for `approve_submission`.
- [x] Add idempotency key handling for `cancel_task`.
- [x] Prevent approve when task already cancelled/refunded.
- [x] Prevent cancel when task already released.
- [x] Ensure `rate_worker` is non-blocking and logs structured result (success/failure with context id).
- [ ] Add integration test for approve then duplicate approve (same submission).
- [ ] Add integration test for cancel then duplicate cancel (same task).
- [ ] Add integration test for cancel-after-approve race condition.

### 7.2 API and schema coherence (P0)

- [x] Remove or formally deprecate `/api/v1/tasks/apply` legacy endpoint.
- [x] Remove or formally deprecate `/api/v1/submissions` legacy submission endpoint.
- [x] Keep canonical worker endpoints under `/api/v1/tasks/{task_id}/apply` and `/api/v1/tasks/{task_id}/submit`.
- [x] Align `supabase_client.py` to `task_applications` table.
- [ ] Align remaining queries/joins to schema in migrations.
- [ ] Regenerate/verify typed contracts if any client typing depends on old schema names.

### 7.3 Security and auth (P0)

- [x] Replace admin query auth with header auth.
- [x] Add admin actor id in config audit log entries.
- [x] Enforce websocket auth validation for both token and API key paths.
- [x] Implement missing ownership validations in reputation endpoints.
- [x] Add structured security audit logs for admin/reputation/write actions.

### 7.4 Frontend release quality (P0)

- [ ] Add ESLint config to `dashboard/`.
- [ ] Add ESLint dependency/config to `admin-dashboard/` or remove lint script until configured.
- [ ] Fix TS errors in `dashboard` (notifications/services/evidence components first).
- [x] Exclude `dashboard/e2e/**` from Vitest (`vite.config.ts` test config).
- [ ] Keep Playwright only under `npx playwright test`.
- [x] Remove/hide placeholder route content from production nav.
- [ ] Route-level `React.lazy` for heavy pages.
- [ ] Defer heavy wallet provider initialization when user enters auth flow.
- [ ] Define chunk-size budget and fail CI when exceeded.

### 7.5 Data path consistency (P0/P1)

- [ ] Decide policy: dashboard writes via backend API vs direct Supabase.
- [ ] If API-first: move submit/apply/cancel writes to backend endpoints.
- [ ] If direct-Supabase remains: enforce strict RLS for each write path and document guarantees.
- [ ] Remove fallback scripts that silently bypass payment settlement in "success-looking" paths.

### 7.6 Testing and CI (P0/P1)

- [ ] Fix `tests/test_websocket.py` import drift (`WebSocketMessage` export mismatch).
- [ ] Update MCP tools tests to match current tool registration contract.
- [ ] Update reputation tests to current Bayesian API (or provide adapter layer).
- [ ] Add a smoke pipeline:
  - backend import + health,
  - backend critical test subset,
  - dashboard typecheck/lint/unit,
  - optional Playwright smoke.
- [ ] Mark "real payment" tests as explicit manual/protected stage.

### 7.7 Docs and release operations (P0/P1)

- [ ] Consolidate domain strategy (`mcp.execution.market` vs `api.execution.market`) and update all docs.
- [ ] Create one release checklist doc used by CI and humans.
- [ ] Archive stale/contradictory status docs to reduce planning noise.
- [ ] Keep only one active launch backlog and one status dashboard.

---

## 8) Scenario matrix (launch-critical)

### 8.1 Core lifecycle scenarios

1. Happy path
- Publish -> accept -> submit -> approve -> settle payment -> reputation update.
- Status now: partially covered; needs live confirmation with strict assertions.

2. Rejection and reopen
- Publish -> accept -> submit -> reject -> task reopened.
- Status now: modeled and tested in mocks; confirm real API + DB invariants.

3. Cancellation before assignment
- Publish -> cancel -> refund/authorization expiry handling.
- Status now: implemented with authorization-expiry + refund branch + released-state guard; pending live-funds validation.

4. Expiry before acceptance
- Publish -> deadline exceeded -> expire + refund behavior.
- Status now: logic exists, needs production-grade verification.

5. Dispute path
- Submit -> dispute -> arbiter resolution (release/refund/split).
- Status now: partial and mostly simulated/mocked.

### 8.2 High-risk technical scenarios (often missed)

6. Approve/cancel race
- agent clicks approve and cancel near-simultaneously.
- Required: deterministic single final state.

7. Duplicate approve requests
- retries/network duplicates.
- Required: idempotent payment release.

8. Duplicate cancel requests
- repeated cancel by client retries.
- Required: idempotent refund/cancel response.

9. Worker submits after cancellation
- stale UI races.
- Required: strong status guard + clear error.

10. Facilitator partial outage
- verify succeeds, settle/refund fails.
- Required: retriable state + compensating action + audit trail.

11. Session desync / stale token
- user authenticated in UI but no valid server-side write privileges.
- Required: clear auth recovery path.

12. Fallback bypass risk
- script/test path updates DB directly when API fails.
- Required: disallow/flag non-production fallback paths.

---

## 9) Three launch strategies (different perspectives)

### Option A - "Private beta now" (fastest)

Ship with tight guardrails:
- small allowlist of agents/workers,
- low bounty caps,
- no public growth push yet.

Pros:
- immediate learning loop.

Cons:
- ops burden and manual oversight.

### Option B - "72h hardening then public launch" (recommended)

Do P0 items first, then open public onboarding.

Pros:
- fastest path with meaningful reliability.

Cons:
- requires strict freeze and focus for 2-3 days.

### Option C - "API-first launch, dashboard soft launch"

Launch agent/API + controlled worker ops; keep advanced UI surfaces hidden.

Pros:
- reduces frontend risk surface immediately.

Cons:
- less polished user experience.

---

## 10) Recommended immediate plan (72h)

### Day 0 (today)

- Freeze scope and branch policy.
- Close payment cancel/refund gap.
- Define canonical endpoint policy.
- Hide placeholder routes.
- Fix Vitest scope and lint config setup.

### Day 1

- Resolve top TS errors blocking dashboard quality gate.
- Fix websocket test/export mismatch.
- Fix MCP tools test drift.
- Add idempotency tests for approve/cancel. (done)

### Day 2

- Run release checklist end-to-end.
- Run happy/reject/cancel/expiry scenario suite.
- Publish one final production status doc.
- Deploy with rollback plan validated.

---

## 11) Definition of "ready to ship"

A release is considered launch-ready only when all are true:
- [ ] `pytest` critical suite green (or documented, accepted exceptions).
- [ ] `dashboard`: typecheck + lint + unit tests green.
- [x] No placeholder pages in production route flow.
- [ ] Payment approve and cancel/refund flows validated end-to-end.
- [x] Auth hardening tasks done (admin + websocket + ownership checks).
- [ ] Health endpoint reports healthy under production config.
- [ ] Single authoritative release status document updated.

---

## 12) Hard rule to stop backlog chaos

From now on:
- one active launch backlog,
- one active production status doc,
- one "ship gate" checklist tied to CI,
- no new features merged while P0 launch blockers are open.

If you follow this rule for one week, shipping cadence will improve dramatically.
