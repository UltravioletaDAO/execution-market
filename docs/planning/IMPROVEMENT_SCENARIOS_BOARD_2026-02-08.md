# Improvement + Scenarios Board - 2026-02-08

Purpose:
- Keep improvements and scenario drills tracked in one launch-focused board.
- Separate "ship blockers" from "next leverage" so execution stays clear.

Status legend:
- `[ ]` pending
- `[x]` done
- `[~]` in progress

## 1) Launch-critical improvements (next 72h)

- [x] `IMP-260208-001 | P0 | Runtime HTTPS contract enforced for agent card | DoD: production publishes HTTPS interfaces | Validation: curl https://api.execution.market/.well-known/agent.json`
- [x] `IMP-260208-002 | P0 | Edge API contract fix for execution.market/api/* | DoD: API paths no longer return SPA HTML 200 | Validation: curl -i https://execution.market/api/v1/tasks/available?limit=1`
- [~] `IMP-260208-003 | P0 | Agent mutation auth contract consolidation | DoD: one production-safe mutation auth path, fallback disabled in prod policy | Validation: dashboard mutation matrix`
- [ ] `IMP-260208-004 | P0 | Strict live x402 evidence bundle | DoD: one full strict run with task_id + escrow_id + tx hashes + final statuses | Validation: scripts/test-x402-full-flow.ts -- --count 1 --strict-api --monitor --auto-approve`
- [ ] `IMP-260208-005 | P0 | Canonical API domain communication lock | DoD: docs, SDK examples, runbooks point to api.execution.market consistently | Validation: rg -n "execution.market/api/v1" docs README.md docs-site`
- [ ] `IMP-260208-006 | P1 | CI adds blocking post-deploy evidence artifact | DoD: smoke + sanity outputs uploaded every deploy | Validation: workflow artifact presence`
- [ ] `IMP-260208-007 | P1 | Lint warning burn-down under 100 | DoD: dashboard lint warnings <= 100 | Validation: cd dashboard && npm run lint`
- [ ] `IMP-260208-008 | P1 | Bundle budget under 3 MB main chunk | DoD: dashboard main chunk < 3 MB | Validation: cd dashboard && npm run build`

## 2) Product and GTM leverage ideas (after launch blockers)

- [ ] `LEV-260208-001 | P1 | "Trust strip" in task detail | Idea: show payout proof tier (strict tx / pending sync / no evidence) to reduce support load`
- [ ] `LEV-260208-002 | P1 | Launch-mode banner in dashboard | Idea: explicit beta mode + limitations + support link to reduce false expectations`
- [ ] `LEV-260208-003 | P1 | Agent onboarding quickstart script | Idea: copy/paste curl + API key test to reduce integration friction`
- [ ] `LEV-260208-004 | P2 | Daily automated "launch scorecard" | Idea: warnings, strict-live count, pending P0 count posted to docs/planning`
- [ ] `LEV-260208-005 | P2 | Worker confidence nudges | Idea: clear escrow state + expected payment timing per task`
- [ ] `LEV-260208-006 | P2 | Ops "one-click rollback" cookbook | Idea: backend/frontend independent rollback commands ready`

## 3) Scenario drills (non-obvious but high-impact)

- [ ] `SCN-260208-A01 | P0 | Integrator wrong-domain trap | Trigger: client calls execution.market/api/* but does not follow redirects | Expected: docs + SDK examples handle canonical API domain correctly`
- [ ] `SCN-260208-A02 | P0 | Approve retry storm | Trigger: 10 approve retries in 3s | Expected: one settlement only, deterministic idempotent responses`
- [ ] `SCN-260208-A03 | P0 | Cancel retry storm | Trigger: 10 cancel retries in 3s | Expected: one terminal cancel/refund state only`
- [ ] `SCN-260208-A04 | P0 | Network flap after settle | Trigger: tx mined but DB update delayed | Expected: reconciliation eventually aligns state and UI`
- [ ] `SCN-260208-A05 | P0 | Fallback leak in production | Trigger: missing API key with mutation attempt | Expected: hard fail when require-api-key policy is enabled`
- [ ] `SCN-260208-A06 | P1 | Stale UI submit after cancel | Trigger: worker submits from stale client | Expected: consistent rejection with clear reason`
- [ ] `SCN-260208-A07 | P1 | API key/wallet identity mismatch | Trigger: connected wallet differs from key owner | Expected: authorization failure + actionable message`
- [ ] `SCN-260208-A08 | P1 | CI green without live proof | Trigger: deploy passes but no strict live evidence | Expected: release gate blocks production-ready claim`
- [ ] `SCN-260208-A09 | P1 | Sanity regression bounce | Trigger: warnings jump > 0 after deploy | Expected: auto-alert and rollback decision path`
- [ ] `SCN-260208-A10 | P2 | Metrics mismatch in UI | Trigger: completed/payment counters diverge from backend | Expected: source-of-truth reconciliation report`

## 4) Execution protocol (anti-chaos)

Rules:
1. No new features while any `P0` in sections 1 or 3 remains open.
2. Every closed item must include command + output evidence.
3. If evidence is missing, item returns to pending.
4. Daily board update at end of deploy window.

Current recommended focus order:
1. `IMP-260208-004`
2. `IMP-260208-003`
3. `IMP-260208-005`
4. `IMP-260208-006`
