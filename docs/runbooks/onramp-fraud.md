---
date: 2026-06-04
tags:
  - type/runbook
  - domain/payments
  - domain/onramp
  - domain/security
  - chain/base
status: active
aliases:
  - Onramp Fraud Runbook
  - MoonPay Fraud Runbook
related-files:
  - mcp_server/api/routers/moonpay.py
  - mcp_server/integrations/moonpay/client.py
  - mcp_server/integrations/moonpay/onramp.py
  - mcp_server/integrations/moonpay/balance_gate.py
  - supabase/migrations/109_moonpay_transactions.sql
  - docs/planning/MASTER_PLAN_FIAT_ONRAMP.md
---

# Onramp Fraud Runbook (MoonPay → USDC on Base)

> **Owner**: founder + backend eng (no anti-fraud specialist hire — fiat-plan
> decision O2, self-serve with this runbook). Escalate to a specialist only if
> post-launch GMV justifies it.

This runbook covers the fraud surface of the fiat onramp that funds the
human-hires-human loop: a human buys USDC on **Base** via MoonPay, then funds a
task. EM **never custodies fiat** (fiat-plan L6) — MoonPay is the money
transmitter of record. EM only sees USDC after settlement. That bounds, but
does not eliminate, our exposure.

## Threat model

| # | Vector | Impact | Primary mitigation |
|---|--------|--------|--------------------|
| R3 | **Chargeback fraud**: buy USDC with a stolen card → fake task → colluding worker → approve → cash out → dispute weeks later. Killed BitInstant + LocalBitcoins. | Wallet drain + MoonPay account closure + reputation damage | MoonPay owns card-fraud + 3DS (it's the merchant of record). EM adds hold periods + velocity caps + collusion signals. |
| — | **Self-collusion**: same human funds + executes via a second account to launder a stolen card into USDC. | Same as R3 | Worker ≠ publisher wallet check; reputation/World ID gating on payout. |
| R5 | **Webhook loss/replay**: a lost or duplicated `transaction.completed` causes "card charged but no balance" or double-credit. | UX disaster / double credit | Idempotent upsert (below) + provider retries. SQS/Lambda for prod scale. |
| — | **Onramp link abuse**: signed Widget URL is bearer-like — anyone with it can initiate a buy against our MoonPay account. | MoonPay spend against our key | Never log signed URLs/signatures (enforced in client.py). Short-lived, per-wallet, server-signed only. |

## Mitigations in place (code)

1. **Webhook idempotency (R5) — DONE.** `mcp_server/api/routers/moonpay.py::_persist_moonpay_webhook`
   upserts with `on_conflict="moonpay_transaction_id"`, so a duplicated
   `transaction_updated` event never double-credits. The endpoint always ACKs
   200 on valid signature (even if persistence fails) so MoonPay does not
   retry-storm; failures are logged.
2. **Signature verification.** Every webhook is HMAC-verified
   (`Moonpay-Signature-V2`, constant-time compare, 300s replay window) in
   `client.py::verify_webhook`. Mismatch → 401.
3. **Bearer-secret hygiene.** Signed Widget URLs + signatures are never logged
   verbatim (client.py docstring + onramp.py). Secret key is server-only
   (env / AWS Secrets Manager), never in the bundle.
4. **$5 floor.** `onramp.py::_MIN_BUY_USD` (usdc_base=$5) matches MoonPay's
   `minBuyAmount` and the EM min bounty (O6), so micro-laundering via dust
   buys is not economical.
5. **Balance gate, not custody.** `balance_gate.py::check_evm_balance_gate`
   only reads balance to decide whether to surface an onramp. EM never holds
   the fiat or the pre-settlement USDC.

## Mitigations to wire before production launch (TODO)

> These are **pre-launch blockers** when `EM_MOONPAY_ENABLED=true` ships to prod
> with real card flow. Tracked here per O2.

- [ ] **Force 3DS** in the MoonPay dashboard (Strong Customer Authentication)
      for all card buys. Verify the flag is on; MoonPay owns the SCA challenge.
- [ ] **Velocity caps** (per user + per IP), enforced server-side at the
      sign-url endpoint before issuing a URL:
      - ~3 onramps / 24h per user (executor.id / externalCustomerId)
      - ~$200 / 24h per user
      - per-IP cap to catch account farming
- [ ] **Hold periods**: block USDC release (task approval settlement) for N
      hours after an onramp until the provider's settlement is final. A
      chargeback-eligible window should not be cashable.
- [ ] **Worker ≠ publisher wallet** check on H2H payout (anti-self-collusion).
      Reuse the existing escrow `worker != treasury` / `worker != agent`
      guards; extend to `worker_wallet != human_wallet` for H2H tasks.
- [ ] **World ID / reputation gate on payout** above a threshold (existing
      `EM_WORLD_ID_ENABLED`, Orb for bounty ≥ $500) — raises the cost of
      sybil collusion rings.
- [ ] **SQS + Lambda webhook infra** (fiat-plan Phase 2): move the in-process
      webhook receiver behind API Gateway → SQS → Lambda so a 5xx streak does
      not make MoonPay disable the endpoint (R5). The idempotent upsert makes
      the consumer safe to retry.

## Sentry alert rules to configure

| Alert | Condition | Severity |
|-------|-----------|----------|
| Chargeback received | MoonPay webhook `type` indicates chargeback/refund-reversal | HIGH — investigate the funded task + worker |
| Repeated 3DS failures | N 3DS-declined events from same user/IP in 1h | MEDIUM |
| Velocity-cap hit | sign-url rejected by a velocity rule | LOW (signal of probing) |
| Geo mismatch | MoonPay KYC country ≠ request IP country | MEDIUM |
| Webhook persist failure streak | `_persist_moonpay_webhook` returns False N times | HIGH — DB/mirror down |

## Incident response

1. **Suspected chargeback ring**: pause `EM_MOONPAY_ENABLED` (ECS task def env
   → force new deployment). Onramp routes 404; existing balances unaffected.
2. **Identify the funded task(s)**: query `payment_events` + `moonpay_transactions`
   by `external_customer_id` / `wallet_address` for the flagged user.
3. **Freeze payout**: if the task is not yet approved, the publisher simply
   doesn't approve (sign-on-approval — no funds move). If already settled,
   funds are gone (trustless) — document the loss, report the worker, adjust
   reputation.
4. **Rotate**: if the MoonPay key is suspected leaked, rotate
   `MOONPAY_SECRET_KEY` + `MOONPAY_WEBHOOK_SECRET` in AWS Secrets Manager and
   redeploy.

## Why the exposure is bounded

Because H2A/H2H is **sign-on-approval** (the human signs EIP-3009 only at
approval, no upfront escrow on the H2A path), a fraudulently-funded buyer who
never gets colluding-worker approval simply holds USDC they bought with their
own (or a stolen) card — the chargeback is MoonPay's problem, not EM's, unless
EM released a payout. The hold-period + worker≠publisher checks above close the
remaining self-collusion gap.
