---
name: em-robot-skill
version: 0.1.0
stability: alpha
description: Robot worker skill for Execution Market on Solana — accepts tasks, scans evidence, opens MPP payment channels via pay.sh, signs Ed25519 vouchers, closes session with on-chain settlement. Server pays gas (fee sponsorship), robot wallet keeps 0 SOL.
homepage: https://execution.market
api_docs: https://api.execution.market/docs
maintainer: Ultravioleta DAO
license: MIT
metadata:
  category: marketplace/robot
  chain: solana
  payment: x402-mpp
  requires:
    env:
      - OWS_ROBOT_SKILL_ENABLED
      - EM_PAYSHELL_URL
      - EM_API_BASE
      - EM_ROBOT_WALLET_NAME
    optional_env:
      - EM_ROBOT_WALLET_PASSPHRASE
      - EM_ROBOT_SKILL_DEBUG
related-docs:
  - docs/planning/MASTER_PLAN_SOLANA_MPP_ROBOT_DEMO.md
  - docs/runbooks/payshell-ops.md
  - docs/runbooks/mpp-scenarios-runbook.md
  - vault/02-architecture/payshell-proxy.md
---

# em-robot-skill — Universal worker skill for Solana MPP

> **Phase 3 deliverable** of the Solana MPP demo master plan. The skill exposes a
> handful of MCP tools that take an Ed25519-capable OWS wallet from "task
> assigned" all the way through "settlement complete" — without the robot ever
> needing SOL of its own (server-side fee sponsorship via pay.sh per spec §3.2).

## What this skill does (one paragraph)

The robot (or any worker capable of running an MCP client) loads its OWS Solana
account, accepts an Execution Market task, optionally produces evidence
(`robot_scan_barcode` is mocked for the demo), opens an MPP session against the
**pay.sh proxy** deployed in Phase 2, signs continuous voucher ticks while it
does the work, and closes the channel — at which point pay.sh atomically
settles 87 % to the worker and 13 % to the treasury, refunding any unused cap.
The Execution Market backend mirrors every event through `task_channel_bindings`
(Phase 2.5.1) so the task transitions to `COMPLETED` the moment settlement
lands. The robot itself never touches USDC plumbing or signs payments — it
signs **vouchers** (cumulative micro-USDC counters), which is the MPP primitive
that makes this entire flow trustless for the agent paying the bill.

## Tools exposed

| Tool | Phase task | Purpose |
|------|-----------|---------|
| `robot_accept_task` | 3.2 | Apply to an assigned task via ERC-8128 wallet-signed `POST /api/v1/tasks/{id}/applications` |
| `robot_scan_barcode` | 3.3 | Decode a base64 QR/barcode payload and post the scan as evidence (mock-friendly) |
| `robot_open_payshell_session` | 3.4 | Receive a 402 challenge from pay.sh, sign `OpenChannelAuth` (Ed25519), receive `channelId` |
| `robot_sign_voucher_tick` | 3.5 | Sign a single 48-byte Borsh voucher and POST `/_sessions/{id}/voucher` — caller drives cadence |
| `robot_close_payshell_session` | 3.6 | Close the channel and receive the settlement tx hash from `settleAndFinalize` |

> **Why "tick" and not "loop"?** The MCP transport is request/response. A long
> loop owned by the server would tie up the agent context. Each tool call is a
> single tick; the calling agent (or the bundled simulator in
> `scripts/demo/robot-sim.ts`) decides cadence and termination condition.

## Wire protocol (identical across scenarios A/B/C/D)

Per `docs/runbooks/mpp-scenarios-runbook.md`, the four worker scenarios share
exactly one wire protocol — only the signer identity changes:

```
Agent (or human) publishes Solana task
         │
         ▼
Worker (this skill) accepts → robot_accept_task
         │
         ▼
Worker scans evidence       → robot_scan_barcode  (optional)
         │
         ▼
Worker opens MPP session    → robot_open_payshell_session
         │                    (pay.sh sponsors fees → server signs on-chain)
         ▼
Worker signs voucher ticks  → robot_sign_voucher_tick × N
         │                    (driven by caller, e.g. 1 / second)
         ▼
Worker closes session       → robot_close_payshell_session
         │                    (pay.sh runs settleAndFinalize + distribute)
         ▼
EM backend mirrors settle   → task_channel_bindings.status = settled
                              tasks.status = completed
```

## Authorized signer (per `SOLANA_MPP_specs_pr201` §3.4)

The Solana spec defines three signer modes: **direct OWS hot wallet**, passkey,
and delegated keys. Only direct OWS hot wallet is `MUST`-support today — the
other two are `MAY`. This skill uses the OWS hot wallet account exclusively.
Every signature this skill emits is one of:

- `ows.signMessage(wallet, "solana", ...)` for `OpenChannelAuth`
- `ows.signTransaction(wallet, "solana", ...)` when pay.sh needs a partial
  signature on a multi-sig instruction (the robot's contribution; pay.sh adds
  the fee-payer signature server-side)

The robot's secret key is never exfiltrated from the OWS vault. The OWS server
process decrypts in-memory, signs, and immediately wipes — see
`ows-mcp-server/src/server.ts` for the existing `ows_sign_*` tools this skill
delegates to.

## Fee sponsorship contract (`_fee_payer.ts`)

The robot wallet is asserted to hold **0 SOL** before each session open. If the
balance is non-zero, the skill warns (still proceeds, but logs a "non-canonical
demo state" note). This preserves the cinematic moment: "an empty wallet does
real work because the protocol sponsors it."

Concretely, pay.sh adds the fee payer signature at `ix open PDA` time per spec
§3.2. The robot only signs the worker side of the voucher / open-channel auth.
See `_fee_payer.ts` for the precise integration boundary.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OWS_ROBOT_SKILL_ENABLED` | yes | `true` (or `1`) to register the 5 robot tools. The skill is alpha and disabled by default — without it the tools do not appear in `tools/list` |
| `EM_PAYSHELL_URL` | yes | pay.sh proxy URL — e.g. `https://api.execution.market` (prod) or `http://127.0.0.1:7081` (local) |
| `EM_API_BASE` | yes | EM REST API base — same host as pay.sh in prod, or `http://127.0.0.1:8080` for local stub |
| `EM_ROBOT_WALLET_NAME` | yes | OWS wallet name (created via `ows_create_wallet`) |
| `EM_ROBOT_WALLET_PASSPHRASE` | no | Passphrase if the wallet was created with one |
| `EM_ROBOT_SKILL_DEBUG` | no | `1` or `true` to emit verbose JSON traces — never leak in production |

## Idempotency and retries

- `robot_accept_task` is idempotent at the EM side — re-applying for the same
  task with the same wallet is a no-op (returns the existing application row).
- `robot_open_payshell_session` returns the existing `channelId` if pay.sh
  detects an open session for the same `(task, payer, payee)` triple.
- `robot_sign_voucher_tick` is **cumulative** by construction. Re-sending the
  same `cumulativeMicroUSDC` is a server-side dedupe (pay.sh keeps the max);
  it is NOT a regression. Vouchers are monotonically increasing.
- `robot_close_payshell_session` is idempotent — calling it twice produces the
  same tx hash. Pay.sh's `settleAndFinalize` is atomic on-chain.

## Errors the tools may return

| Error | When | Recovery |
|-------|------|----------|
| `wallet_not_found` | `EM_ROBOT_WALLET_NAME` does not exist in vault | Run `ows_create_wallet` and fund nothing — fee sponsorship covers gas |
| `no_solana_account` | OWS wallet has no `solana:mainnet` account | Recreate wallet — `ows.createWallet` always provisions a Solana account |
| `payshell_unreachable` | `EM_PAYSHELL_URL` 5xx or timeout | Check ECS sidecar per `docs/runbooks/payshell-ops.md` |
| `task_not_assignable` | EM returned 4xx on accept | Verify task is still in `published` state; check it is Solana-paid |
| `voucher_rejected` | pay.sh returned 4xx on `/voucher` | Check cumulative did not regress; check expiresAt is in the future |
| `settlement_no_tx_hash` | Close succeeded but pay.sh did not return tx hash | Operator runbook — verify on Solscan, re-emit `settlement_complete` via SSE |

## Differences vs the original Phase 3 plan (pre-D-15)

The original master plan included a TypeScript sidecar that this skill would
talk to directly. After **D-15** (Solana Foundation `pay.sh` adoption), the
sidecar is gone — the skill talks straight to the `pay.sh` proxy that was
deployed in Phase 2. Practical consequences for any reader expecting the older
design:

1. There is no `sidecar/` directory anymore. Everything happens against
   `EM_PAYSHELL_URL`.
2. The voucher signing path (`robot_sign_voucher_tick`) signs against the
   canonical MPP voucher format (per `[[SOLANA_MPP_specs_pr201]]`), not a
   custom EM-flavoured envelope.
3. Fee sponsorship is delegated to pay.sh's embedded facilitator — there is no
   EM-managed fee-payer keypair anywhere.

## Validation steps (per master-plan §3 exit criteria)

1. `ows skill validate em-robot-skill` parses this manifest without warnings.
2. `pnpm tsx scripts/demo/robot-sim.ts --task-id <uuid>` completes a full
   30-second session against a local Surfpool + pay.sh proxy without
   intervention.
3. The robot OWS wallet keeps `lamports=0` throughout — verified by
   `_fee_payer.ts` runtime assertion.

## See also

- [[surfpool-payshell-dev-env]] — local dev setup
- [[payshell-ops]] — production operations runbook
- [[mpp-scenarios-runbook]] — A/B/C/D scenario matrix this skill plugs into
