---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - Fase 1
  - direct settlement
  - default payment mode
related-files:
  - mcp_server/integrations/x402/payment_dispatcher.py
  - docs/planning/FASE1_E2E_EVIDENCE_2026-02-11.md
---

# Fase 1 — Direct Settlement

**Fase 1** is the default production payment mode (`EM_PAYMENT_MODE=fase1`). It uses the simplest possible flow: no funds are locked at task creation, and settlement happens directly at approval via two fresh [[eip-3009]] authorizations.

## Flow

### Task Creation
- **Advisory `balanceOf()` check only** — verifies agent has sufficient USDC
- No auth signed, no funds move, no escrow locked
- Task creates regardless of balance (advisory)

### Task Approval
Server signs 2 fresh [[eip-3009]] authorizations:
1. **Agent -> Worker**: bounty amount (e.g., $0.087 for $0.10 task)
2. **Agent -> [[treasury]]**: platform fee (e.g., $0.013 for 13%)

Both are submitted to the [[facilitator]] for on-chain settlement. No platform wallet intermediary.

### Task Cancellation
- **No-op** — no auth was ever signed, nothing to refund

## Key Properties

- **No intermediary wallet** — funds flow directly agent->worker and agent->treasury
- **No escrow lock** — agent retains control of funds until approval
- **2 transactions at approval** — one for worker, one for treasury
- **Risk**: agent could spend funds between creation and approval (no lock)

## E2E Evidence

Fully tested end-to-end on 2026-02-11. See `docs/planning/FASE1_E2E_EVIDENCE_2026-02-11.md`.

## When to Use

Fase 1 is ideal for:
- Low-value tasks where escrow overhead is unnecessary
- Trusted agent-worker relationships
- Quick iteration during development

For higher-value tasks requiring fund guarantees, see [[fase-5-trustless]].

## Related Concepts

- [[payment-dispatcher]] — routes to Fase 1 when `EM_PAYMENT_MODE=fase1`
- [[eip-3009]] — the authorization standard used for both settlements
- [[wallet-roles]] — no platform wallet intermediary in this mode
- [[fee-structure]] — 13% fee sent directly to treasury
