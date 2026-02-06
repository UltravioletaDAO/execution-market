# Ship Execution Report - Unified Deploy + Public Metrics (2026-02-05)

## 1) Executive status

Current status after this iteration:

- Production backend and frontend are deployed from the same release cut.
- Public metrics endpoint is live: `/api/v1/public/metrics`.
- Landing now shows real metrics (registered users, workers taking tasks, completed tasks).
- Logged-in dashboards now show platform-level user/task activity metrics.
- Core validation for this release passed (`pytest` target, `vitest`, `vite build`).

What is still not green:

- Frontend `typecheck` is still failing with `88` errors (same baseline bucket, not newly introduced by this patch).
- Full facilitator end-to-end proof (`publish -> submit -> approve` with tx evidence chain in UI) remains pending as a formal production test case.

---

## 2) Scope delivered in this release

### Backend

- File: `mcp_server/api/routes.py`
- Added public endpoint:
  - `GET /api/v1/public/metrics`
- Response includes:
  - `users`: registered workers/agents, workers with tasks, active workers, workers completed, active agents
  - `tasks`: total + status breakdown + `live`
  - `activity`: workers with active/completed tasks, agents with live tasks
  - `payments`: total volume + platform fees (from escrows)
  - `generated_at`

### Backend tests

- File: `mcp_server/tests/test_p0_routes_idempotency.py`
- Added test:
  - `test_get_public_platform_metrics_aggregates_counts`
- Existing tests in that file remained green.

### Frontend

- New hook: `dashboard/src/hooks/usePublicMetrics.ts`
  - Fetches public metrics from API
  - Handles loading/error
  - Auto-refresh every 60s
- Exports updated in `dashboard/src/hooks/index.ts`
- Landing metrics bar connected to real data:
  - `dashboard/src/components/landing/StatsBar.tsx`
- Landing integrates stats bar:
  - `dashboard/src/pages/Home.tsx`
- Worker logged-in dashboard metrics cards:
  - `dashboard/src/pages/WorkerTasks.tsx`
- Agent dashboard metrics cards:
  - `dashboard/src/pages/AgentDashboard.tsx`

### Planning docs updated

- `docs/planning/IMPROVEMENT_BACKLOG_2026-02-05.md`
  - Added/updated `PAY-009`, `PAY-010`, `OPS-007`, `OPS-008`, `MET-001..005`

---

## 3) Production deploy evidence

## Images

- MCP image:
  - Repo: `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server`
  - Tag: `ship-20260205-173835-metrics`
  - Digest: `sha256:dcd40fdd26164675cb46e74d55fa08bc47551affc7090eae60729436151a316b`
- Dashboard image:
  - Repo: `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard`
  - Tag: `ship-20260205-173835-metrics`
  - Digest: `sha256:b090083eeab8abc67a8a4bc79c2452ec36e209a9b929eaba9584da600b929bfb`

## ECS services

- `em-production-mcp-server` -> task definition `em-production-mcp-server:10`
- `em-production-dashboard` -> task definition `em-production-dashboard:5`
- Both with `rollout = COMPLETED`, `running = desired = 1`

## Live endpoint checks

- `https://execution.market` -> `200`
- `https://api.execution.market/health` -> `healthy`
- `https://api.execution.market/api/v1/public/metrics` -> returns live JSON payload

Snapshot observed during deployment verification:

- `users.registered_workers = 24`
- `users.workers_active_now = 5`
- `tasks.live = 9`
- `tasks.completed = 1`

---

## 4) Validation matrix (executed)

### Backend

```bash
python -m pytest mcp_server/tests/test_p0_routes_idempotency.py -q
python -m pytest mcp_server/tests/test_admin_auth.py -q
```

Result:

- `10 passed` in `test_p0_routes_idempotency.py`
- `7 passed` in `test_admin_auth.py`

### Frontend

```bash
npm --prefix dashboard run test:run
npm --prefix dashboard run build
npm --prefix dashboard run typecheck
```

Result:

- `test:run`: pass (`13 passed`)
- `build`: pass
- `typecheck`: fail (`88` errors)

Top TS codes:

- `TS6133 = 43`
- `TS7006 = 20`
- `TS2322 = 11`

Top files by errors:

- `src/hooks/useProfile.ts` = 11
- `src/hooks/useTransaction.ts` = 8
- `src/hooks/useTokenBalance.ts` = 7
- `src/pages/Disputes.tsx` = 7

---

## 5) Priority TODOs (granular)

## P0 - Ship blockers (next)

1. `AUTH-003` Validate wallet session persistence in production.
- Why: user-facing conversion bug if wallet prompts again on "Start Earning".
- DoD: after first auth, returning to landing and pressing "Start Earning" does not trigger a new sign request.

2. `PAY-010` Enforce facilitator-only transaction visibility paths.
- Why: direct-wallet tx evidence is invalid for the desired escrow model.
- DoD: release scripts and UI evidence only reference facilitator-backed tx for publish/settle/refund.

3. `PAY-007` Execute full production flow test (`publish -> submit -> approve`) and archive tx evidence.
- Why: closes uncertainty around final payout tx traceability.
- DoD: one documented task with publish/payment tx and final settle tx visible in UI and explorer.

4. `OPS-008` Automate unified deploy.
- Why: avoid drift between concurrent deployers and reduce manual errors.
- DoD: one script performs build/push/register/update/wait/health for backend+frontend.

## P1 - Technical debt with direct impact

1. `P0-FE-TS-A/B/C/D` bring `typecheck` from `88 -> 0`.
2. `MET-004` add 30-60s server-side caching for public metrics endpoint.
3. `OPS-006` normalize frontend API base (`/api` vs `api.execution.market`) to avoid ambiguous routing in browser runtime.

## P2 - Quality/performance

1. `PERF-001` split heavy dashboard chunk (`~5MB`).
2. `TEST-004` release smoke pipeline (backend health + frontend sanity + payment contract).

---

## 6) Exact manual QA checklist (step-by-step)

## A. Verify deploy versions

```bash
aws ecs describe-services \
  --cluster em-production-cluster \
  --services em-production-mcp-server em-production-dashboard \
  --region us-east-2 \
  --query "services[].{service:serviceName,taskDefinition:taskDefinition,rollout:deployments[0].rolloutState,running:runningCount,desired:desiredCount}"
```

Expected:

- MCP on `em-production-mcp-server:10`
- Dashboard on `em-production-dashboard:5`
- both `rollout=COMPLETED`, `running=desired=1`

## B. Verify public metrics API

```bash
curl https://api.execution.market/api/v1/public/metrics
```

Expected:

- valid JSON with `users`, `tasks`, `activity`, `payments`, `generated_at`

## C. Verify landing metrics UI

1. Open `https://execution.market`.
2. Confirm metrics strip is visible under hero.
3. Confirm values are numeric and not static marketing placeholders.
4. Refresh page and confirm values keep matching API trend (allowing normal drift).

## D. Verify logged-in dashboard metrics

1. Log in as worker and open `/tasks`.
2. Confirm 4 metrics cards are visible at top:
- Registered Users
- Workers Taking Tasks
- Active Agents
- Completed Tasks
3. Log in as agent and open `/agent/dashboard`.
4. Confirm "Platform Pulse" section appears with live metrics.

## E. Verify wallet session persistence bug (critical UX)

1. Log in once with wallet (complete signature flow).
2. Return to landing page.
3. Click `Start Earning`.
4. Refresh browser tab and repeat.

Expected:

- no repeated wallet signature prompt in these transitions
- user remains authenticated and routed to task area

## F. Verify facilitator transaction trace (publish + settle)

1. Publish a paid task through facilitator flow.
2. Capture and store:
- task id
- escrow/payment reference
- explorer tx (if available)
3. Complete task lifecycle to approval.
4. As worker, open completed task detail and payment timeline.

Expected:

- publish side shows escrow/payment evidence linked to facilitator path
- completion side shows payout tx evidence
- no direct-wallet-only tx accepted as canonical proof for this test

---

## 7) Risks currently open

1. API base ambiguity in frontend runtime (`/api` default) can still create environment-specific regressions.
2. `typecheck` debt remains high and can hide real regressions in future changes.
3. Payment volume metrics are currently tied to escrow rows; if escrow sync is partial, financial aggregates may underreport.

---

## 8) Next execution block (recommended order)

1. Close `AUTH-003` + produce evidence video/log.
2. Run and document `PAY-007` full facilitator E2E in production.
3. Fix top TS buckets (`TS6133`, `TS7006`, `TS2322`) in the top 4 files.
4. Implement `OPS-008` deploy script for deterministic releases.
