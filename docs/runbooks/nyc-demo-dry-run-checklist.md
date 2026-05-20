---
date: 2026-05-20
tags:
  - type/runbook
  - domain/operations
  - chain/solana
  - status/active
status: active
aliases:
  - Dry-run preflight
  - Pre-rehearsal sanity script
related-files:
  - docs/runbooks/nyc-demo-runbook.md
  - docs/runbooks/payshell-ops.md
  - docs/runbooks/surfpool-payshell-dev-env.md
  - scripts/demo/dry-run-preflight.ts
  - scripts/demo/prefund-demo-wallets.ts
  - docs/planning/MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO.md
---

# Dry-Run Preflight Checklist — MoonPay NYC Demo

> **Phases 4.11 + 6.1 prep deliverable.** Run this checklist *before* each
> dry-run (Saul's office #1 + NYC stage #2). The goal is to surface any
> environment, balance, or build regression *before* the human operator
> starts the camera. The dry-run execution itself remains HITL — this doc
> only automates the boring "is everything wired" gate.
>
> If any block fails: do not start the dry-run. Fix the failure first.

## When to run this

| Phase | When | Where | Who runs it |
|-------|------|-------|-------------|
| **4.11 prep** | T-30 min before dry-run #1 | Saul's office, surfpool local | Saul or Felipe |
| **6.1 prep** | T-30 min before dry-run #2 | NYC stage laptop, mainnet | Saul or Felipe |
| **6.8 prep** | T-30 min before live demo | NYC stage laptop, mainnet | Saul or Felipe |

## How to run

```bash
# From repo root, with .env.local populated:
npx tsx scripts/demo/dry-run-preflight.ts --mode <surfpool|mainnet>
```

The script reads `.env.local`, runs each check, and prints a pass/fail line
per check. Exit code `0` = all green, `>0` = something needs attention.

> **Never** pass keys as CLI flags or env-prefix on the command line — the
> user is always streaming. The script reads from `.env.local` only.

## Checks the script performs

Each row maps to a check in `scripts/demo/dry-run-preflight.ts`.

| # | Check | What it validates | If it fails |
|---|-------|-------------------|-------------|
| 1 | Env vars present | All `DEMO_*`, `MOONPAY_*`, `SOLANA_RPC_URL`, `PAYSHELL_*` keys are set | Copy missing keys from `.env.example` and fill from AWS Secrets Manager |
| 2 | Solana RPC reachable | `getSlot` returns within 2s | Switch RPC URL (QuikNode primary, public fallback) |
| 3 | pay.sh control plane reachable | `GET {PAYSHELL_BASE_URL}/healthz` returns 200 | Check infrastructure/pay/ + Terraform state |
| 4 | EM backend reachable | `GET https://api.execution.market/health` returns 200 | Check ECS service status |
| 5 | Dashboard reachable | `GET https://execution.market/` returns 200 with HTML | Check CloudFront distribution |
| 6 | `/demo/nyc` renders | Playwright navigates + asserts beat 1 visible | Re-run `npm run build` + redeploy dashboard |
| 7 | Saul wallet baseline | USDC = 0, SOL ≥ 0.05 | Run `prefund-demo-wallets.ts --reset` or fund SOL from Ledger |
| 8 | Robot wallet baseline | USDC = 0, SOL = 0 | Drain robot wallet — fee sponsorship is the selling point |
| 9 | Backup wallet baseline | USDC ≥ 40, SOL ≥ 0.05 | Top up from Ledger before flying |
| 10 | Treasury wallet readable | balance query succeeds (no transfer) | Verify pubkey in `.env.local` |
| 11 | MoonPay test quote | `moonpay_get_quote(20, solana, usdc)` returns a price | API keys may have rotated; check MoonPay dashboard |
| 12 | URL signing roundtrip | Backend `/api/v1/moonpay/sign` returns signed URL with valid HMAC | Check `MOONPAY_SECRET_KEY` rotated or webhook URL changed |

## Manual steps after the script passes

Once all 12 checks are green, the **human** still needs to:

1. **Visually confirm** the stage laptop displays `/demo/nyc` correctly on the 4K monitor (see also `[[nyc-demo-filming]]` §"On-site test")
2. **Test audio playback** — unmute the voucher tick and confirm the cue is audible
3. **Phone in airplane mode** during the live take, but reachable for the camera operator
4. **Camera roll test** — 10s of B-roll to confirm exposure and audio levels
5. **Robot battery** at ≥ 80% (if hardware demo, not simulator)

These last 5 cannot be automated — they require eyes, ears, hands, and a
charged robot. The script gates everything that *can* be automated.

## Outputs

The script writes a structured JSON report to `./.dry-run-reports/<UTC>.json`:

```json
{
  "mode": "mainnet",
  "ranAt": "2026-06-01T18:23:11Z",
  "passed": 11,
  "failed": 1,
  "checks": [
    { "id": "moonpay-quote", "status": "fail", "hint": "API key rotated" }
  ]
}
```

This file is gitignored by default. Operators can `git add` a specific
report if it documents a known-good baseline worth archiving.

## What this checklist does **not** cover

- **The dry-run itself** — see `[[nyc-demo-runbook]]` §"Demo execution"
- **Cinematography setup** — see `[[nyc-demo-filming]]`
- **Fault-injection practice** — see `[[nyc-demo-contingency-drills]]`
- **NYC logistics** — internal coord (Halsey/spacemandev/Office Ops), HITL

## Linked sub-tasks

- Phase 4.11 — Dry-run #1 (Saul's office, surfpool, $0 real money) → uses this with `--mode surfpool`
- Phase 6.1 — Dry-run #2 (NYC stage, mainnet, real $20) → uses this with `--mode mainnet`
- Phase 6.8 — Demo day execution → uses this with `--mode mainnet` one last time
