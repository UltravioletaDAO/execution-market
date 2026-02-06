# X402 Fast-Track TODO (2026-02-06)

> Updated execution map + launch backlog:
> `docs/planning/EM_SYSTEM_MAP_AND_LAUNCH_PLAN_2026-02-06.md`

## Objective
Ship a production-safe fast loop for Execution Market where one script can validate:
1. x402 payment authorization for task creation
2. Task execution lifecycle (apply -> assign -> submit -> approve)
3. Worker payout evidence (`payment_tx` + payment timeline events)
4. Cancellation/refund behavior

## Current Snapshot

### Done in this iteration
- Added REST assignment endpoint: `POST /api/v1/tasks/{task_id}/assign`
- Added rapid E2E script: `scripts/test-x402-rapid-flow.ts`
- Added npm command: `scripts/package.json` -> `test:x402:rapid`
- Upgraded Python x402 SDK baseline: `mcp_server/requirements.txt` -> `uvd-x402-sdk[fastapi]>=0.7.0`
- Added TypeScript SDK dependency baseline: `scripts/package.json` -> `uvd-x402-sdk@^2.19.0`
- Added monitor timeout guard to full flow script:
  - `scripts/test-x402-full-flow.ts` now supports `--monitor-timeout <minutes>`

### Confirmed protocol capabilities
- `refundInEscrow` is implemented and wired (`x402r_escrow.py`).
- `release` to worker from escrow is implemented and wired (`x402r_escrow.py`).
- Post-release dispute refund (`refundPostEscrow`) is documented as not production-ready until tokenCollector exists (`advanced_escrow_integration.py`).

### Still pending
- Enforce facilitator-only flow in every script path (remove DB fallbacks after rollout stability).
- Ensure ERC-8004 worker registration path is facilitator-first in all production flows.
- End-to-end production evidence run with explicit tx hashes for: create escrow, worker payout, refund.
- Managed evidence pipeline on AWS (`API Gateway -> Lambda -> S3 -> CloudFront`) for deterministic upload/storage/audit.

## Priority Plan

## P0 (Ship blockers)
- P0.1 Run rapid E2E live and capture evidence bundle (task ids, tx hashes, final statuses).
- P0.2 Verify instant payout behavior on submit in production (`/tasks/{id}/submit` -> `payment_tx`).
- P0.3 Verify cancellation path with real escrow status and refund tx when refundable.
- P0.4 Remove or explicitly gate non-facilitator paths in production scripts (`--allow-direct-wallet` style guards already exist in several scripts; complete audit needed).
- P0.5 Add production smoke test gate in CI/CD (at least strict API simulation + schema checks).

## P1 (High value)
- P1.1 Add explicit transaction surfacing in dashboard/landing for:
  - task funding tx (`escrow_tx`)
  - payout tx (`payment_tx`)
  - refund tx (when cancelled/refunded)
- P1.5 Wire dashboard evidence uploads to managed presign API once infra is applied.
- P1.2 Add API endpoint for worker-focused payment history that normalizes `payments` + `escrows` schema drift.
- P1.3 Add deterministic fixtures for 2-minute test tasks in staging/local.
- P1.4 Add retry/idempotency tests for approve endpoint and payout settlement.

## P2 (Hardening)
- P2.1 Migrate all old scripts to shared x402 helper library.
- P2.2 Remove legacy `applications` fallback once `task_applications` migration is guaranteed in all environments.
- P2.3 Add long-run soak test (hourly) for publish/apply/assign/submit/approve/cancel.

## Execution Order (next)
1. Run `test-x402-rapid-flow.ts` in strict mode and archive output JSON.
2. If payout missing, inspect `/api/v1/tasks/{task_id}/payment` and submission records for settlement blocker.
3. Run `--run-refund-check` and classify as:
   - `refunded` with tx hash
   - `authorization_expired` (no settle occurred)
   - `refund_manual_required` (needs intervention)
4. Implement dashboard tx rendering once evidence confirms stable event fields.

## Validation Commands

```bash
cd scripts
npm exec -- tsx check-deposit-state.ts
npm exec -- tsx test-x402-rapid-flow.ts -- --count 1 --deadline 2 --auto-approve --run-refund-check
npm exec -- tsx test-x402-full-flow.ts -- --count 1 --strict-api --monitor --auto-approve
```

## Evidence Required Per Run
- Command used
- Mode (`live` or `simulated`)
- Wallet address
- Task IDs
- Escrow ID and escrow tx/reference
- Payout tx hash (if any)
- Refund tx hash (if any)
- Final task status
- Any fallback path used (`api` vs `supabase-fallback`)
