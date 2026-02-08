# Handoff - Launch + Live Validation (Linux/WSL) - 2026-02-08

## 1) Executive summary

Current state as of **2026-02-08**:
- Production runtime is healthy and stable.
- `agent.json` is HTTPS-correct in production.
- `execution.market/api/*` now redirects (`308`) to canonical `https://api.execution.market/...` (no more silent SPA HTML for API paths).
- Backend tests are green (`658 passed, 8 skipped`).
- Smoke + sanity are green (`10/10`, `6/6 warnings=0`).
- Main remaining launch blocker: **strict live end-to-end x402 evidence** with final payout/refund tx proof.

## 2) Why it was taking so long

Root cause:
1. `test-x402-full-flow.ts` monitor mode is long-running by design (poll loop up to `--monitor-timeout`, default 20 min), waiting for real task transitions.
2. A previous monitor run was interrupted from chat UI, but the `tsx` process stayed alive in background (Windows process not fully terminated).
3. That background process kept polling and caused temporary API rate-limit noise.

What was fixed:
- Killed stale monitor processes.
- Re-validated task states and environment after cleanup.

## 3) What was completed in this handoff cycle

### 3.1 Code + tracking commits
- `4e05afd` - `fix(edge): redirect execution.market/api to canonical API domain and sync launch tracking`
- `e5cf492` - `docs(plan): mark api edge redirect and runtime rollout as completed with live evidence`

### 3.2 Production deploy executed
- Built + pushed dashboard image:
  - `518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:4e05afd`
  - digest: `sha256:c86ee70aecf58f953753410b2fb1c3385fdcbeb953c490896c2883143e91b848`
- Forced ECS rollout to immutable image tag.
- Current ECS state:
  - backend: `em-production-mcp-server:32` (`COMPLETED`)
  - dashboard: `em-production-dashboard:21` (`COMPLETED`)

### 3.3 Runtime evidence
- `curl -i https://execution.market/api/v1/tasks/available?limit=1`
  - returns `308` with `Location: https://api.execution.market/api/v1/tasks/available?limit=1`
- Following redirect ends in API JSON `200`.
- `https://api.execution.market/.well-known/agent.json` reports HTTPS interfaces.
- `npm run report:sanity:strict`:
  - `status=ok`, `checks=6/6`, `warnings=0` (timestamp `2026-02-08T04:33:51Z`).

## 4) Live x402 runs already executed

### Preflight
- `.env.local` keys present:
  - `SUPABASE_URL=true`
  - `SUPABASE_ANON_KEY=true`
  - `WALLET_PRIVATE_KEY=true`
- `check-deposit-state.ts`:
  - wallet: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
  - USDC wallet: `7.277674`
  - ETH: `0.000273151457952358`

### Strict API creation runs done
1. Single-task strict run:
   - task: `507779c8-9c84-4cc4-86d7-eac993bba299`
2. Multi-task strict run (Fibonacci defaults):
   - `804632a8-04a1-46ca-9493-f656102f8560`
   - `31c77cec-fc70-4737-8024-dc1fdab130e1`
   - `9a583669-db64-4ceb-9635-cdaa8c13849e`
   - `f0294ba8-fd7c-409c-befd-428bc2ca5ab0`
   - `bfe2e67a-cc62-417c-8771-53ce350f3734`

Current status of these tasks:
- All are `published` (not yet accepted/submitted/approved).
- They include `escrow_id` + `escrow_tx` auth references (e.g., `x402_auth_*`), but there is no payout tx yet because lifecycle not completed.

## 5) What is still pending (handoff targets)

## P0 blockers
1. **C04 strict live payout evidence**
   - Need one full path: publish -> apply -> submit -> approve -> completed with payout tx evidence.
2. **C05 strict live cancel/refund evidence**
   - Need funded/cancellable path evidence with tx hash OR explicit authorization-expired evidence (as applicable).
3. **B01 auth contract consolidation**
   - API-first exists, but production-safe single auth path (and fallback policy) still needs closure.

## P1
4. CI post-deploy evidence artifact automation (`A02` / `IMP-260208-006`).
5. Lint/bundle debt (`D03`, `D04`).

## 6) Exact Linux/WSL execution plan

Use these commands in WSL (recommended):

```bash
cd /mnt/z/ultravioleta/dao/execution-market

# 1) Preflight (required)
cd scripts
npm exec -- tsx check-deposit-state.ts

# 2) Strict create run (single task)
npm exec -- tsx test-x402-full-flow.ts --count 1 --strict-api

# 3) Strict monitored run (single task)
npm exec -- tsx test-x402-full-flow.ts --count 1 --strict-api --monitor --monitor-timeout 20

# 4) Strict monitored + auto-approve
npm exec -- tsx test-x402-full-flow.ts --count 1 --strict-api --monitor --auto-approve --monitor-timeout 20
```

Important notes:
- `--help` is not implemented in this script; do not use it as a dry-run.
- `--monitor` waits for real state transitions. If no worker accepts/submits, it will idle until timeout.
- If you interrupt monitor, verify no process remains:
```bash
pkill -f "test-x402-full-flow.ts" || true
ps aux | grep test-x402-full-flow | grep -v grep
```

## 7) Evidence format to return

For each run, capture:
- exact command
- mode (`live` strict API)
- wallet address
- created task IDs
- `escrow_id` + `escrow_tx`
- payout/refund tx hash (BaseScan URL)
- final task status
- any retries/errors

## 8) How you can help me fastest

If you want me to continue from here with your handoff:
1. Send me your pending bug list in this format:
   - `BUG-ID`
   - repro command
   - expected vs actual
   - files touched (if known)
2. If you run the strict flow in WSL, paste raw outputs and I will:
   - classify pass/fail,
   - update launch boards,
   - produce final production-readiness gate report.

## 9) Files already updated in planning/tracking

- `docs/planning/LAUNCH_REVIEW_EXHAUSTIVE_2026-02-08.md`
- `docs/planning/IMPROVEMENT_SCENARIOS_BOARD_2026-02-08.md`
- `terra4mice.spec.yaml`

