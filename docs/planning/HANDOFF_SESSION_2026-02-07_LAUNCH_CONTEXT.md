# Handoff - Launch Context (2026-02-07)

## Scope of this handoff

This document packages the current launch analysis into one operational handoff for the next session:

- what is already true in production
- what is blocking launch confidence
- what decisions are locked
- what to execute next (with command order)
- what evidence must be captured

Primary source of truth for the audit details: `docs/planning/LAUNCH_REVIEW_2026-02-07.md`.

## Snapshot

- Repository: `execution-market`
- Branch: `main`
- HEAD at review time: `2d6a49e` (merge commit)
- Launch status: **NO-GO** for "production-ready" claim today

Reason for NO-GO:

1. Agent routes still contain mock/demo behavior on active production paths.
2. Frontend quality gates are red (`dashboard` typecheck/lint).
3. Domain behavior is ambiguous (`execution.market/api/*` serves SPA HTML).
4. Agent card currently advertises `http://...` URL.
5. Missing one funded refund tx hash evidence run.

## Locked decisions (confirmed by user)

1. Canonical API domain is `api.execution.market`.
2. `mcp.execution.market` remains technical alias/backward-compatible entrypoint.
3. Go/No-Go requires real agent routes (no demo routes for launch).
4. Do not claim production-ready payments until at least one funded refund tx hash is captured.
5. Refund tx evidence is top priority and must be done ASAP.

## Current strengths (already in place)

- Live health endpoints are up.
- API on `api.execution.market` and `mcp.execution.market` responds with JSON on task endpoints.
- Build passes for key apps (`dashboard` build passes, `admin-dashboard` build passes).
- Payments have payout-side evidence; infra is close.

## Critical blockers by area

## Frontend agent flow (P0)

Mock/demo logic still present in active routes:

- `dashboard/src/pages/AgentDashboard.tsx:357`
- `dashboard/src/pages/agent/TaskManagement.tsx:441`
- `dashboard/src/pages/agent/CreateTask.tsx:747`
- `dashboard/src/pages/agent/SubmissionReview.tsx:255`

## Domain/API consistency (P0)

- `execution.market/api/v1/*` behavior is not canonical API behavior.
- Docs still point to `https://execution.market/api/v1` in:
  - `docs-site/docs/api/reference.md:3`

## Agent Card transport/security (P0)

- URL generation can expose `http://...`:
  - `mcp_server/a2a/agent_card.py:563`

## Quality gates (P0/P1)

- `dashboard`:
  - `typecheck` failing (~100 TS errors at audit time)
  - `lint` not enforceable due to missing ESLint setup
- `admin-dashboard`:
  - lint script exists but eslint dependency/config missing

## Backend test drift (P1)

- Full suite has failing clusters:
  - `mcp_server/tests/test_mcp_tools.py`
  - `mcp_server/tests/test_reputation.py`
  - `mcp_server/tests/test_platform_config.py`

## Payments evidence gap (P0)

- Need one funded refund tx hash + basescan link + final DB status to unlock claim.

## Launch backlog (execution order)

P0 first, no parallel scope creep:

1. Unmock agent routes (`LCH-P0-001..004`)
2. Restore dashboard release gates (`LCH-P0-005..006`)
3. Canonicalize domains + fix agent card HTTPS (`LCH-P0-007..009`)
4. Execute funded refund evidence run (`LCH-P0-010`)

Then P1:

1. Align failing backend test contracts (`LCH-P1-001..003`)
2. Fix admin lint tooling (`LCH-P1-004`)
3. Normalize submission write path (`LCH-P1-005`)

## Refund tx ASAP runbook (real validation)

Follow this order:

1. Confirm env has:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `WALLET_PRIVATE_KEY`
2. Check funding:
   - `cd scripts && npm exec -- tsx check-deposit-state.ts`
3. Execute preferred sequence:
   - `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api`
   - `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api --monitor`
   - `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api --monitor --auto-approve`

Fallback when funds/network block live:

- `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api false`
- `cd scripts && npm exec -- tsx test-x402-full-flow.ts -- --direct --count 1` (debug only, non-facilitator)

Guardrail:

- If deposit step reverts after task insert, immediately set task status to `cancelled` with service-role credentials.

## Mandatory evidence format per run

For each validation run, record:

1. script + exact command
2. mode (`live` or `simulated`)
3. wallet address
4. task ids
5. `escrow_id` + `escrow_tx` (or explicit reason missing)
6. basescan links (if available)
7. final task status in Supabase/API
8. errors, retries, unresolved blockers

## Terra4mice tracking status

Launch tracking resources were added in `terra4mice.spec.yaml` for P0/P1 launch items, including:

- `launch_20260207_agent_routes_unmock`
- `launch_20260207_dashboard_typecheck`
- `launch_20260207_dashboard_eslint_config`
- `launch_20260207_agent_card_https`
- `launch_20260207_funded_refund_live_evidence`

Action for next session:

1. Regenerate state from spec (if CLI available) so these appear in `terra4mice.state.json`.
2. Keep these as launch board of record; avoid split tracking in parallel docs.

## Suggested 72h operating cadence

## 0-8h

- Ship agent route de-mock patches
- Make `dashboard` lint/typecheck green

## 8-24h

- Canonical domain and API behavior cleanup
- Agent card HTTPS fix and live verify

## 24-48h

- Execute funded refund run until tx evidence is captured
- Patch top backend test drifts

## 48-72h

- Freeze scope
- Run final release candidate checklist
- Decide Go/No-Go with evidence only

## Copy/paste prompt for next session

Use this to continue without losing context:

```text
Continue from docs/planning/HANDOFF_SESSION_2026-02-07_LAUNCH_CONTEXT.md and docs/planning/LAUNCH_REVIEW_2026-02-07.md.
Assume launch decisions are locked:
- canonical API domain = api.execution.market
- mcp.execution.market = technical alias
- Go/No-Go requires real agent routes (no mock/demo)
- do not claim production-ready payments without 1 funded refund tx hash

Priority now:
1) execute/refine P0 fixes LCH-P0-001..009
2) run live funded refund flow and capture tx evidence for LCH-P0-010
3) update ship report with required evidence fields
4) keep terra4mice launch resources synced with actual completion

Work in strict execution mode: make code changes, run validation commands, and report exact evidence (commands, task ids, tx hashes, final statuses).
```

## Related docs

- `docs/planning/LAUNCH_REVIEW_2026-02-07.md`
- `docs/planning/PRODUCTION_LAUNCH_MASTER_2026-02-05.md`
- `docs/planning/IMPROVEMENT_BACKLOG_2026-02-05.md`
- `docs/planning/SHIP_EXECUTION_REPORT_2026-02-05_TX402.md`
- `docs/planning/SHIP_NOW_AUDIT_2026-02-05.md`
