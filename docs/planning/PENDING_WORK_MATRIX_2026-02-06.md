# Pending Work Matrix - Post PaymentTx Hardening (2026-02-06)

## Scope
This document lists **remaining work** after deploying PaymentTx hardening to production MCP backend (`em-production-mcp-server:20`).

## What Was Completed In This Run
- Backend fix deployed to production so submissions are not marked as paid/completed without on-chain tx evidence.
- `approve` flow now requires settlement tx hash before final acceptance.
- Settlement tx hash extraction hardened across SDK response variants.
- Live rapid flow validated with API-only assignment path (no Supabase fallback) and payout tx captured.

## Live Validation Evidence (This Run)
- Command: `cd scripts && npm exec -- tsx check-deposit-state.ts`
- Mode: live
- Wallet: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
- Result: USDC wallet `8.827674`, relay `0.01`, deposits present.

- Command: `cd scripts && npm exec -- tsx test-x402-rapid-flow.ts -- --count 1 --deadline 2 --auto-approve --run-refund-check --strict true --allow-supabase-fallback false`
- Mode: live
- Wallet: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd`
- Task ID: `4a5549de-5cd3-4b38-b800-25e69a0e09e6`
- Submission ID: `590d90fa-ca41-477d-91b3-e0d292f33652`
- `payment_tx`: `0x0e5295b9075dc28d92a3b349f5df13ee586c8eeee4465a5f249a797bfefef41e`
- BaseScan: `https://basescan.org/tx/0x0e5295b9075dc28d92a3b349f5df13ee586c8eeee4465a5f249a797bfefef41e`
- Final task status: `completed`
- Fallback used: no

- Refund check task: `94e2ac34-27a7-4aae-a430-2663bd4d524c`
- Refund outcome: `authorization_expired` (expected for authorize-only flow where funds were not settled to escrow)
- Refund tx hash: none (no escrowed funds moved)

## Remaining Work (Granular)

### P0 - Must Finish Before "Production Ready" Claim
- [ ] `P0-PAY-001` Run at least 1 live scenario with **funded escrow state** and capture real refund tx hash (not only authorization expiry path).
- [ ] `P0-PAY-002` Enforce `facilitator-only` in all production scripts by default; keep direct wallet paths behind explicit `--allow-direct-wallet` guard.
- [ ] `P0-PAY-003` Add server-side audit flag when payout comes from fallback/manual path vs facilitator settlement.
- [ ] `P0-PAY-004` Add retry job for submissions stuck in `accepted` without `payment_tx` from old data; backfill and reconcile.
- [ ] `P0-PAY-005` Add alerting query for `submissions.agent_verdict='accepted' AND payment_tx IS NULL`.
- [ ] `P0-PAY-006` Verify payout recipient correctness with wallet different from payer (true worker wallet).
- [ ] `P0-PAY-007` Validate cancellation for each escrow status: `authorized`, `deposited/funded`, `released`, `refunded`.
- [ ] `P0-AUTH-001` Resolve wallet session persistence issue (`Start Earning` should not request repeated signature each time).
- [ ] `P0-AUTH-002` Add explicit token/session TTL and refresh strategy docs for wallet auth.
- [ ] `P0-API-001` Verify all production MCP routes match local code (assign route drift already fixed once; add parity checks).

### P0 - UI/Visibility Needed For Operations
- [ ] `P0-UI-001` Show task funding reference/tx in task detail (`escrow_id`, `escrow_tx` or canonical reference).
- [ ] `P0-UI-002` Show payout tx (`payment_tx`) in worker and agent task timelines.
- [ ] `P0-UI-003` Show refund tx (or `authorization_expired` reason) in cancelled task timeline.
- [ ] `P0-UI-004` Add direct BaseScan links for each on-chain tx event.
- [ ] `P0-UI-005` Ensure landing page never hard-fails on no active tasks (`Failed to fetch tasks` fallback behavior).
- [ ] `P0-UI-006` Verify `/profile` route on current production build (regression previously observed).

### P1 - ERC-8004 / Facilitator End-to-End Coverage
- [ ] `P1-ERC-001` Ensure worker identity registration path is facilitator-backed and executed when missing.
- [ ] `P1-ERC-002` Ensure human identity registration path is facilitator-backed and executed when missing.
- [ ] `P1-ERC-003` Ensure post-task bidirectional feedback writes to ERC-8004 for both sides.
- [ ] `P1-ERC-004` Persist ERC-8004 tx hashes in DB (`identity_tx`, `reputation_tx`) and surface in UI.
- [ ] `P1-ERC-005` Add health check for ERC-8004 facilitator operations (identity + reputation write smoke).

### P1 - Evidence Pipeline Hardening
- [ ] `P1-EVID-001` Apply Terraform evidence stack in target env (`API Gateway -> Lambda -> S3 -> CloudFront`).
- [ ] `P1-EVID-002` Wire dashboard upload to presign API (replace public URL/manual evidence path).
- [ ] `P1-EVID-003` Add content-type, size and checksum validation in upload flow.
- [ ] `P1-EVID-004` Add signed URL expiry and replay protection test.
- [ ] `P1-EVID-005` Add forensic metadata fields (device attestation placeholder, geotime metadata) to submission schema.

### P1 - Data/Analytics Consistency
- [ ] `P1-MET-001` Reconcile `registered_users`, `workers_with_tasks`, `agents_active_now` metrics queries with live DB expectations.
- [ ] `P1-MET-002` Add dashboard card for global stats (registered users, active workers, completed tasks).
- [ ] `P1-MET-003` Add periodic metrics sanity checker and drift report.
- [ ] `P1-DB-001` Finish schema parity checks across environments (`task_applications` vs `applications`, payments columns, escrows metadata).

### P2 - Test Automation / Reliability
- [ ] `P2-TEST-001` Add nightly live smoke (`create -> apply -> assign -> submit -> approve`) with tx evidence artifact upload.
- [ ] `P2-TEST-002` Add funded-refund smoke (`create -> escrow funded -> cancel -> refund tx expected`).
- [ ] `P2-TEST-003` Add concurrency/idempotency stress test for duplicate approve calls.
- [ ] `P2-TEST-004` Add end-to-end UI test for payment timeline visibility.
- [ ] `P2-TEST-005` Remove remaining script fallbacks after production stabilizes.

### P2 - Deployment / Ops
- [ ] `P2-OPS-001` Automate image build + ECS rollout script with immutable tags and rollback command output.
- [ ] `P2-OPS-002` Add post-deploy parity checks: route diff, health diff, env version marker.
- [ ] `P2-OPS-003` Add release note template that includes tx evidence block.

## Final Pre-Launch Test Pack (Required)
- [ ] `T-001` Live create task via x402 verify-only path (facilitator valid).
- [ ] `T-002` Live assign/apply/submit/approve, capture payout tx and BaseScan link.
- [ ] `T-003` Live funded refund path with on-chain refund tx hash.
- [ ] `T-004` ERC-8004 identity + reputation write for both worker and agent.
- [ ] `T-005` UI assertion: funding/payout/refund tx visible and clickable.
- [ ] `T-006` Session persistence assertion: wallet sign-in survives navigation and repeated `Start Earning`.

## Release Gate (Go / No-Go)
- [ ] No accepted submission without `payment_tx`.
- [ ] At least one payout tx and one refund tx captured in the same release cycle.
- [ ] API/UI route parity confirmed on production.
- [ ] Evidence upload path working with managed storage.
- [ ] ERC-8004 critical flows facilitator-backed and observable.
