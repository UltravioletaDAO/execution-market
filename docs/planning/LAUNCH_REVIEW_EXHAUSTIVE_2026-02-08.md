# Launch Review Exhaustive - 2026-02-08

Update (2026-02-08, after additional implementation):
- Added deploy/runtime hardening so backend runtime is forced to canonical API base URL.
- Added CI/staging smoke assertions to fail if Agent Card advertises non-HTTPS interface URLs.
- Expanded dashboard API-first coverage for agent mutations (create/cancel/assign/approve/reject) with transitional fallback.
- Added automated sanity warning reporting script (`scripts/report-sanity-warnings.ts`).
- Live sanity re-check is currently green (`6/6`, `warnings=0`).

## 1) Executive status (real state now)

Decision:
- GO for controlled beta launch.
- NO-GO for claiming full production readiness.

Why still NO-GO:
1. Production runtime still serves `http://` in agent card URL.
2. `execution.market/api/*` still returns SPA HTML instead of API JSON.
3. Agent critical dashboard flows are still mixed: API-first is partial, direct Supabase mutations remain.
4. Payment consistency warnings are currently clear, but need sustained monitoring and strict live evidence after latest changes.
5. No fresh end-to-end live payment evidence was generated in this cycle after the latest hardening commits.

## 2) Evidence executed in this review

Environment date: `2026-02-08` (local execution)

### 2.1 Backend quality
- Command: `cd mcp_server && python -m pytest -q`
- Result: `658 passed, 8 skipped, 0 failed`

### 2.2 Production smoke
- Command: `cd scripts && npm exec -- tsx smoke-test.ts`
- Result: `10 passed, 0 failed`
- Notes: API health, MCP health, dashboard reachability, agent card endpoint, and evidence lambda all reachable.

### 2.3 Dashboard build/runtime quality
- Command: `cd dashboard && npm run build`
- Result: build OK
- Risk signal: main JS chunk is still large (`~5.24 MB`), plus rollup dependency warnings.

### 2.4 Production topology checks
- `https://execution.market/api/v1/tasks/available?limit=1` -> `200 text/html`
- `https://api.execution.market/api/v1/tasks/available?limit=1` -> `200 application/json`
- `https://api.execution.market/.well-known/agent.json` currently returns:
  - `url=http://api.execution.market/a2a/v1`

### 2.5 Production sanity checks
- Latest re-check: `https://api.execution.market/health/sanity` -> `status=ok`, `checks=6/6`, `warnings=0`
- Note: keep continuous monitoring to ensure this does not regress.

### 2.6 Tracking state
- `docs/planning/TODO_NOW.md`: `205 total` (`18 done`, `187 pending`)
- `docs/planning/IMPROVEMENT_BACKLOG_2026-02-05.md`: `53 total` (`10 done`, `43 pending`)
- `docs/planning/PRODUCTION_LAUNCH_MASTER_2026-02-05.md`: `27 total` (`1 done`, `26 pending`)
- `terra4mice.state.json`: `120 resources` (`109 implemented`, `11 missing`)

## 3) What changed and is now stronger

Recent commits (this session block):
- `f5ec308`: backend full-suite determinism fixed (`test_escrow_flows` global mock contamination removed).
- `3cb889a`: `/health/sanity` payment evidence query logic corrected.
- `8b55674`: agent card URL normalization with HTTPS enforcement for non-local.
- `35a734c`: docs base URL standardized to `https://api.execution.market/api/v1`.
- `e9b6a10`: backend test failures now block CI/deploy (removed non-blocking behavior).
- `19ca107`: `--direct` flow now requires `--allow-direct-wallet`.
- `6cfd07e`: worker submission switched to API-first with explicit guarded fallback.
- `be7afda`: worker apply switched to API-first with explicit guarded fallback.
- `1d66952`: deploy/infra hardened so runtime uses canonical API URL in ECS/workflows.
- `345c72c`: exhaustive launch review + terra4mice sync.

## 4) Critical gap map (ordered by launch risk)

## P0

1. Runtime drift not deployed yet
- Code hardening exists, but production still publishes `http://api.execution.market/a2a/v1`.
- Likely cause: task definition/runtime env still running older revision.

2. Canonical API contract still ambiguous at public domain edge
- `execution.market/api/*` serves HTML while `api.execution.market/api/*` serves JSON.
- Integrators can silently hit wrong surface and think API is healthy due HTTP 200.

3. Agent mutation path is only partially API-first
- API-first done for `apply`, `submit`, `create`, `cancel`, `assign`, `approve`, and `reject`.
- Still direct Supabase writes in:
  - transitional fallback paths when no `VITE_API_KEY` is available.
  - `dashboard/src/services/submissions.ts:395` (`requestMoreInfo`) still has no backend endpoint parity.

4. Payment data integrity debt in production data
- Current sanity check is green (`warnings=0`).
- Risk moved from active warning to monitoring and regression prevention.

5. No fresh strict live x402 end-to-end evidence after latest changes
- Launch confidence is still incomplete without one strict live run with tx hash evidence and final states.

## P1

6. CI still has blind spots
- E2E auth/flow tests remain disabled in CI.
- `mypy` remains non-blocking.

7. Frontend operational debt
- Lint warnings remain high.
- Bundle remains large and risks mobile performance/regression under poor networks.

8. Planning docs drift
- Multiple planning documents still conflict on what is done vs pending.

## 5) Perspectives to unblock decision-making

1. Founder velocity view:
- You can launch beta now if scope is strictly controlled and marketing claims are limited.

2. SRE/operations view:
- System uptime is acceptable, but routing/API contract ambiguity is still a support and incident magnet.

3. Payment/audit view:
- Main risk is not endpoint availability; it is proving payout correctness per completed task.

4. Integrator trust view:
- Wrong docs/domain behavior causes silent integration failures that look like client bugs.

5. Product focus view:
- New features should pause until mutation path is fully coherent and payout evidence is clean.

## 6) Granular ship-now TODO list

Format:
- `ID | Priority | Owner | Task | Definition of done | Validation`

## Track A - Runtime and deployment hardening

- [ ] `LCH-260208-A01 | P0 | DevOps | Deploy latest backend task definition with EM_BASE_URL canonicalized | Agent card URL is HTTPS on production | curl https://api.execution.market/.well-known/agent.json`
- [ ] `LCH-260208-A02 | P0 | DevOps | Deploy latest CI/CD workflow updates | New deploy run shows API checks against api.execution.market | workflow run logs`
- [ ] `LCH-260208-A03 | P0 | DevOps | Verify ECS running revisions after deploy | backend/frontend rollout=COMPLETED with expected revision | aws ecs describe-services ...`
- [ ] `LCH-260208-A04 | P0 | Infra | Decide and enforce `execution.market/api/*` behavior (proxy or explicit block) | No ambiguous HTML 200 for API paths | curl -i https://execution.market/api/v1/tasks/available?limit=1`
- [x] `LCH-260208-A05 | P1 | Infra | Add post-deploy assertion for agent card URL scheme | pipeline fails if URL starts with http:// | CI step assertion`
- [ ] `LCH-260208-A06 | P1 | Infra | Ensure staging has same canonical EM_BASE_URL behavior | staging agent card uses HTTPS canonical URL | curl staging agent card endpoint`

## Track B - API-first business mutations

- [ ] `LCH-260208-B01 | P0 | Frontend+Backend | Define agent auth strategy for dashboard API mutations (API key vs wallet-bound token) | single supported auth path documented and implemented | doc + working mutation call`
- [ ] `LCH-260208-B02 | P0 | Frontend | Migrate create-task UI to backend endpoint path (no direct insert in prod path) | create task no longer writes directly to tasks table in prod mode | integration test + grep`
- [ ] `LCH-260208-B03 | P0 | Frontend | Migrate cancel-task UI to backend `/tasks/{id}/cancel` | refund/authorization status returned in UI flow | manual cancel + API payload`
- [ ] `LCH-260208-B04 | P0 | Frontend | Migrate assign-task UI to backend `/tasks/{id}/assign` | assign flow uses backend response source of truth | task assignment test`
- [ ] `LCH-260208-B05 | P0 | Frontend | Migrate approve-submission to backend `/submissions/{id}/approve` | approval path yields tx evidence from backend | approve flow test`
- [ ] `LCH-260208-B06 | P0 | Frontend | Migrate reject-submission to backend `/submissions/{id}/reject` | rejection uses backend status transition | reject flow test`
- [ ] `LCH-260208-B07 | P1 | Frontend | Migrate request-more-info to backend route (or add route if missing) | no direct submission/task updates from client path | route + UI test`
- [ ] `LCH-260208-B08 | P1 | Frontend | Add explicit non-prod escape hatch documentation for direct Supabase fallback | fallback is only possible with explicit env flag | runtime logs + docs`
- [ ] `LCH-260208-B09 | P1 | Backend | Add server-side idempotency keys for create/cancel/approve endpoints | duplicate requests become deterministic no-op responses | API test`
- [ ] `LCH-260208-B10 | P1 | QA | Build one end-to-end dashboard mutation matrix | matrix covers create/apply/assign/submit/review/cancel transitions | test report`

Progress note:
- Implemented API-first paths for create/cancel/assign/approve/reject with transitional fallback when `VITE_API_KEY` is not configured.
- Remaining blocker is auth contract consolidation and backend parity for `requestMoreInfo`.

## Track C - Payment integrity and evidence

- [ ] `LCH-260208-C01 | P0 | Data+Backend | Audit 15 completed_no_payment tasks and classify cause (legacy/manual/bug) | each task has category and remediation plan | audit sheet`
- [ ] `LCH-260208-C02 | P0 | Data | Backfill missing payment evidence where tx exists | sanity warning count decreases with traceable updates | health/sanity`
- [ ] `LCH-260208-C03 | P0 | Backend | Mark unresolvable legacy tasks with explicit non-facilitator marker | no silent unknown payment source remains | DB query + API audit`
- [ ] `LCH-260208-C04 | P0 | QA | Execute strict live run with tx hash evidence | command, task id, escrow id, tx hash, final status documented | script artifact`
- [ ] `LCH-260208-C05 | P0 | QA | Execute strict live cancel/refund run with tx evidence or explicit authorization-expired evidence | refund path evidence documented | script artifact`
- [ ] `LCH-260208-C06 | P1 | Backend | Expose per-task payment consistency endpoint/flag | UI and ops can detect payout mismatch quickly | endpoint test`
- [ ] `LCH-260208-C07 | P1 | Backend | Add DB query/script to flag completed tasks missing payment evidence daily | recurring report available | cron/report output`
- Status: script added (`scripts/report-sanity-warnings.ts` + `npm run report:sanity:strict`) using `/health/sanity`; DB-level daily job still pending.
- [ ] `LCH-260208-C08 | P1 | Ops | Define launch claim policy: no payout claim without tx evidence | release notes gate blocks unsupported claims | release checklist`

## Track D - Quality gates and CI

- [ ] `LCH-260208-D01 | P0 | CI | Re-enable E2E flow in CI with Dynamic auth-compatible path | CI includes one blocking E2E smoke | workflow green`
- [ ] `LCH-260208-D02 | P1 | CI | Make mypy blocking for backend core modules | type regressions block merge | CI`
- [ ] `LCH-260208-D03 | P1 | Frontend | Reduce dashboard ESLint warnings below 100 | warning count threshold enforced in CI | npm run lint`
- [ ] `LCH-260208-D04 | P1 | Frontend | Reduce dashboard main chunk under 3 MB | bundle budget enforced | npm run build`
- [ ] `LCH-260208-D05 | P1 | QA | Add post-deploy smoke artifact upload in CI (commands + outputs) | release has reproducible evidence bundle | workflow artifact`
- [ ] `LCH-260208-D06 | P2 | QA | Add replay test for approve/cancel retry storm | deterministic outcomes under retries | test report`

## Track E - Planning and execution discipline

- [ ] `LCH-260208-E01 | P0 | Product+Eng | Freeze net-new features for 72h while launch blockers close | all PR labels enforce launch-only scope | PR policy`
- [ ] `LCH-260208-E02 | P0 | Product | Maintain single launch board as source of truth | old launch docs marked archived/snapshot | docs update`
- [ ] `LCH-260208-E03 | P1 | Product+Ops | Daily launch standup with fixed metrics: warnings, tx-evidence runs, pending blockers | one daily report generated | daily note`
- [ ] `LCH-260208-E04 | P1 | Ops | Publish rollback decision tree (when/how to rollback backend/frontend independently) | runbook with commands validated | runbook drill`

## 7) Scenario matrix (brainstorm, non-obvious, high impact)

- [ ] `SCN-260208-001` Deployment succeeds but agent card still publishes http due stale task definition.
- [ ] `SCN-260208-002` Integrator uses `execution.market/api/*`, gets HTML 200, parses fails silently.
- [ ] `SCN-260208-003` Dashboard approve path goes direct and marks completed even when facilitator payout failed.
- [ ] `SCN-260208-004` Retry storm: 10 approve retries in 3s, payout must remain single-settlement.
- [ ] `SCN-260208-005` Retry storm: 10 cancel retries in 3s, refund/authorization state remains consistent.
- [ ] `SCN-260208-006` Network flap after payout tx but before DB update: task state lags payment state.
- [ ] `SCN-260208-007` Worker submits after task cancel due stale UI; API must reject consistently.
- [ ] `SCN-260208-008` Direct fallback flag enabled in production accidentally.
- [ ] `SCN-260208-009` Completed tasks with no payment evidence continue to grow week-over-week.
- [ ] `SCN-260208-010` CI green but release has no live tx evidence artifact.
- [ ] `SCN-260208-011` API key mismatch with wallet identity causes unauthorized mutation despite connected wallet UX.
- [ ] `SCN-260208-012` `execution.market` edge cache serves stale HTML for API path post-routing change.
- [ ] `SCN-260208-013` Approval endpoint idempotent path settles payment, but frontend double-counts payout in UI metrics.
- [ ] `SCN-260208-014` Legacy tasks migrated to completed without canonical payment rows.
- [ ] `SCN-260208-015` Staging passes because API URL is correct, production fails due env drift.
- [ ] `SCN-260208-016` Worker apply succeeds via API but local refetch fails, UI shows false error.

## 8) Immediate execution plan

### 0-12h (launch-critical)
- Close `A01-A04`, `C01-C05`, `B01`.
- Produce one strict live evidence bundle.
- Do not ship new features.

### 12-36h
- Close `B02-B06`, `D01`, `E02`.
- Re-audit sanity warnings after data backfill/classification.

### 36-72h
- Close `D03-D05`, `E03-E04`, and top scenario tests.
- Move from controlled beta to wider launch only if warnings and payment evidence gates are acceptable.

## 9) Rule of shipping (anti-chaos)

Work is not done unless all four exist:
1. reproducible validation command,
2. machine-readable evidence,
3. tracking state updated,
4. user-visible behavior verified in production runtime.
