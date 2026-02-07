# Launch Review - 2026-02-07

## Executive Summary

Current state is **operable but not release-disciplined**.

- Production endpoints are live and healthy (`mcp.execution.market` and `api.execution.market`).
- Worker-facing flow has real API integration in key paths.
- Payment infra has live evidence for payout txs, but refund evidence is still incomplete for funded escrow.
- Agent-facing dashboard routes are still demo/mocked in active routes.
- Frontend quality gates are red (`typecheck`, `lint`), so regressions can ship silently.
- Tracking is fragmented: `TODO_NOW` says 205 items (18 done), while `terra4mice.state.json` marks all 98 resources as implemented.

Bottom line: **you can keep shipping patches**, but **you cannot claim production-ready launch quality yet** without closing P0 listed below.

## Resolved Decisions (2026-02-07)

These three launch decisions are now confirmed and should be treated as fixed constraints:

1. **Canonical API domain**
   - Canonical public API domain: `api.execution.market` (closest to standard API topology).
   - `mcp.execution.market` remains as technical alias/backward-compatible entrypoint, mainly for MCP transport and existing integrations.

2. **Go/No-Go requirement for agent routes**
   - Launch requires real production agent routes (no mock/demo data on active `/agent/*` paths).

3. **Payment production-ready claim gate**
   - Do not claim `production-ready payments` until at least one funded refund flow has an on-chain refund tx hash captured and documented.
   - Priority: execute this refund evidence run ASAP.

## Evidence Collected (2026-02-07)

### Runtime checks (live)

- `https://execution.market` -> `200`
- `https://execution.market/api/v1/tasks/available?limit=1` -> `200` but serves SPA HTML (not API JSON)
- `https://mcp.execution.market/health` -> `200 healthy`
- `https://api.execution.market/health` -> `200 healthy`
- `https://mcp.execution.market/api/v1/tasks/available?limit=1` -> `200` JSON
- `https://api.execution.market/api/v1/tasks/available?limit=1` -> `200` JSON
- `https://mcp.execution.market/.well-known/agent.json` -> `200` but advertises `http://mcp.execution.market/a2a/v1` in card URL

### Frontend checks

Command:

```bash
cd dashboard
npm run typecheck
npm run lint
npm run test:run
npm run build
```

Result:

- `typecheck`: **fail** (`100` TS errors)
- `lint`: **fail** (missing ESLint config)
- `test:run`: pass (`13` tests)
- `build`: pass (but very large main chunk)

### Admin checks

Command:

```bash
cd admin-dashboard
npm run build
npm run lint
```

Result:

- `build`: pass
- `lint`: **fail** (`eslint` command not installed)

### Backend checks

Command:

```bash
cd mcp_server
python -m pytest -q
```

Result:

- `603 passed`
- `39 failed`
- `8 skipped`

Failing clusters:

- `tests/test_mcp_tools.py` (FastMCP registration contract drift)
- `tests/test_platform_config.py` (min bounty expectation drift `0.25` vs current `0.01`)
- `tests/test_reputation.py` (Bayesian API drift)

### Payment readiness check

Command:

```bash
cd scripts
npm exec -- tsx check-deposit-state.ts
```

Result:

- Wallet: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
- USDC wallet: `7.277674`
- Relay: `0.01`
- Vault: `0.14`
- ETH remaining: `0.000273151457952358`

## Critical Findings (Ordered)

## P0

1. **Agent routes are still mock/demo in active production routes**
   - `dashboard/src/pages/AgentDashboard.tsx:357` (mock data load)
   - `dashboard/src/pages/agent/TaskManagement.tsx:441` (simulated API call + mock tasks)
   - `dashboard/src/pages/agent/CreateTask.tsx:747` (simulated success)
   - `dashboard/src/pages/agent/SubmissionReview.tsx:255` (mock evidence from picsum)

2. **Domain topology is ambiguous and can break integrations**
   - `execution.market/api/*` serves SPA HTML (not API)
   - `docs-site/docs/api/reference.md:3` still uses `https://execution.market/api/v1`
   - `dashboard/src/hooks/useTasks.ts:180` and `dashboard/src/hooks/useTaskPayment.ts:71` default to `api.execution.market`
   - This mismatch creates support/debug confusion and failed client calls when people copy docs.

3. **Agent Card publishes HTTP URL behind TLS edge**
   - `mcp_server/a2a/agent_card.py:563` builds base URL from `request.url.scheme`
   - Live card advertises `http://mcp.execution.market/a2a/v1`
   - Some clients reject or downgrade insecure URLs.

4. **Frontend release gate is broken**
   - `dashboard/package.json:10` defines lint script, but no ESLint config in package.
   - `dashboard` `typecheck` currently fails with `100` errors.
   - This allows regressions in critical auth/payment views.

5. **Funded refund evidence is still missing as launch proof**
   - Current live evidence favors payout and authorization-expiry flows.
   - Need one funded refund tx hash to claim end-to-end escrow robustness.

## P1

6. **Backend full suite not green**
   - `mcp_server/tests/test_mcp_tools.py` failing around current `@mcp.tool` contract.
   - `mcp_server/tests/test_reputation.py` lags current Bayesian interface (`mcp_server/reputation/bayesian.py`).
   - `mcp_server/tests/test_platform_config.py` expects old min-bounty default.

7. **Admin dashboard quality gate not enforceable**
   - `admin-dashboard/package.json:9` has lint script.
   - `admin-dashboard/package.json` has no eslint dependency/config.

8. **Tracking drift is currently high**
   - `docs/planning/TODO_NOW.md` shows `205` items (`18` done).
   - `terra4mice.state.json` marks all resources implemented.
   - Result: no trustworthy single truth for launch decisions.

## P2

9. **Worker path still bypasses API in parts**
   - `dashboard/src/services/submissions.ts` writes directly to Supabase.
   - Works for speed, but weakens policy centralization and API observability.

10. **Bundle size still heavy**
   - Dashboard build warns about large chunks.
   - Impacts mobile cold-start and conversion.

## What Is Already Strong

- Health checks are healthy with real component probes.
- Live API returns consistent metrics (`/api/v1/public/metrics` on `api` and `mcp` domains).
- Focused backend hardening tests pass (`idempotency/admin auth/ws auth/reputation ownership/schema alignment`).
- Worker-facing core list/detail/submit flow is wired to real data paths.

## What Still Blocks "Launch With Confidence"

- Real agent workflow (create/manage/review) must stop using mock data.
- Release gates must be objective and green (`typecheck`, `lint`, key backend suite).
- One canonical API domain and clear behavior for `execution.market/api/*`.
- At least one funded-refund live run with on-chain tx hash.

## Granular TODO Backlog

## P0 - Must Close

- [ ] `LCH-P0-001` Replace mock data in `AgentDashboard` with API fetch.
  - DoD: no hardcoded tasks/submissions/activity blocks remain.
  - Validate: open `/agent/dashboard` and verify data changes with live backend writes.
- [ ] `LCH-P0-002` Replace mock data in `TaskManagement`.
  - DoD: task list/cancel/actions call real API.
  - Validate: cancel a live task and confirm backend status update + audit row.
- [ ] `LCH-P0-003` Wire `CreateTask` to real publish endpoint.
  - DoD: no simulated timeout/id; task id comes from API.
  - Validate: create task then fetch by id from `/api/v1/tasks/{id}`.
- [ ] `LCH-P0-004` Replace mock evidence gallery in `SubmissionReview`.
  - DoD: displays actual submission evidence URLs and metadata.
  - Validate: compare against stored submission evidence payload.
- [ ] `LCH-P0-005` Add dashboard ESLint config and make lint pass.
  - DoD: `npm --prefix dashboard run lint` exit code 0.
- [ ] `LCH-P0-006` Bring dashboard typecheck to 0.
  - DoD: `npm --prefix dashboard run typecheck` exit code 0.
- [ ] `LCH-P0-007` Enforce canonical API domain policy (`api.execution.market`) across docs/frontend/env.
  - DoD: one primary domain in README/docs-site/hooks; `mcp.execution.market` documented as technical alias.
  - Validate: smoke tests for canonical and redirect/deprecated domains.
- [ ] `LCH-P0-008` Define official behavior for `execution.market/api/*`.
  - DoD: either valid reverse-proxy API or explicit 404/redirect.
  - Validate: `curl https://execution.market/api/v1/public/metrics` returns expected behavior (not SPA).
- [ ] `LCH-P0-009` Force HTTPS in agent card URLs.
  - DoD: card `url` uses `https://...`.
  - Validate: `curl https://mcp.execution.market/.well-known/agent.json | jq .url`.
- [ ] `LCH-P0-010` Run one funded-refund live scenario and capture tx hash.
  - DoD: task + escrow id + refund tx + basescan link + final DB status.
  - Validate: evidence block in ship report.

## P1 - High Priority

- [ ] `LCH-P1-001` Fix `test_mcp_tools` contract drift with current FastMCP API.
- [ ] `LCH-P1-002` Update reputation tests to current Bayesian interfaces.
- [ ] `LCH-P1-003` Align platform config tests with official min bounty decision.
- [ ] `LCH-P1-004` Add lint tooling in `admin-dashboard` (or remove lint script).
- [ ] `LCH-P1-005` Convert direct Supabase submission writes to backend endpoint path.
- [ ] `LCH-P1-006` Add CI gate for critical live-smoke command output artifact.
- [ ] `LCH-P1-007` Add production parity check script (`api` vs `mcp` route inventory).

## P2 - Next Wave

- [ ] `LCH-P2-001` Route-level code splitting for heavy agent/validator views.
- [ ] `LCH-P2-002` Bundle budget thresholds enforced in CI.
- [ ] `LCH-P2-003` Consolidate obsolete planning docs to one active launch board.
- [ ] `LCH-P2-004` Expand payment timeline UX with explicit settlement method labels.
- [ ] `LCH-P2-005` Add release evidence template with mandatory tx proof block.

## Brainstorm Scenarios (Non-Obvious)

- [ ] `SCN-001` Approve and cancel racing within 500ms on same task.
- [ ] `SCN-002` Submission arrives after task auto-expired while worker UI is stale.
- [ ] `SCN-003` Agent card advertises HTTP, client refuses connection silently.
- [ ] `SCN-004` API domain copied from docs (`execution.market/api`) during integration.
- [ ] `SCN-005` Worker submits evidence while payments table is temporarily unavailable.
- [ ] `SCN-006` Payout tx exists but task status update fails (already partly handled).
- [ ] `SCN-007` Multiple approve retries from flaky mobile network.
- [ ] `SCN-008` Wallet session restored but executor row lookup fails transiently.
- [ ] `SCN-009` Category room websocket subscription with malformed `task:` id.
- [ ] `SCN-010` Admin auth via query parameter leaked through logs/history.
- [ ] `SCN-011` Agent route renders mock values while real backend shows opposite state.
- [ ] `SCN-012` Rollback deploy leaves frontend referencing stale API base URL.
- [ ] `SCN-013` Payment timeline shows deposit reference without explorer tx hash.
- [ ] `SCN-014` Empty live tasks causes false-negative "Failed to fetch tasks" UX regression.
- [ ] `SCN-015` TTL mismatch between docs cache and live OpenAPI route changes.

## 72-Hour Ship Plan

## 0-8h

- Close `LCH-P0-001..004` (agent routes unmocked).
- Close `LCH-P0-005..006` (dashboard lint/typecheck green).

## 8-24h

- Close `LCH-P0-007..009` (domain canonicalization + agent card HTTPS).
- Run full smoke and update docs links.

## 24-48h

- Execute funded refund run (`LCH-P0-010`) with tx evidence.
- Fix highest-risk backend failing clusters (`LCH-P1-001..003`).

## 48-72h

- Freeze feature scope.
- Do one final release candidate with explicit Go/No-Go checklist:
  - payment payout tx evidence
  - funded refund tx evidence
  - green frontend gates
  - healthy runtime endpoints
  - no mock flows in active routes

## Terra4mice Tracking Update

Added launch-tracking TODO resources to `terra4mice.spec.yaml`:

- `launch_20260207_dashboard_typecheck`
- `launch_20260207_dashboard_eslint_config`
- `launch_20260207_admin_lint_tooling`
- `launch_20260207_agent_routes_unmock`
- `launch_20260207_agent_create_task_api`
- `launch_20260207_payment_path_consistency`
- `launch_20260207_agent_card_https`
- `launch_20260207_backend_test_alignment_mcp_tools`
- `launch_20260207_backend_test_alignment_reputation`
- `launch_20260207_backend_config_defaults_decision`
- `launch_20260207_funded_refund_live_evidence`

If the `terra4mice` CLI is available later, regenerate state from this spec so launch tasks appear in `terra4mice.state.json`.
