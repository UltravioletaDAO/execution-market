---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - Fase 5
  - credit card model
  - trustless escrow
  - direct_release
related-files:
  - mcp_server/integrations/x402/payment_dispatcher.py
  - scripts/deploy-payment-operator.ts
  - scripts/e2e_golden_flow_multichain.py
---

# Fase 5 — Trustless Payment

**Fase 5** is the **credit card model** for Execution Market payments. The platform **never touches funds**. Escrow pays the worker directly, and the [[payment-operator]] holds the fee for [[treasury]] distribution.

## Flow

### Task Creation
- Advisory `balanceOf()` check only
- **No escrow locked** — worker address unknown at creation
- Escrow status = `pending_assignment`

### Task Assignment (Worker Accepts)
- Lock bounty in [[x402r-escrow]] with **worker as direct receiver**
- Bounty = lock amount (credit card convention)
- [[static-fee-calculator]] configured in the [[payment-operator]]

### Task Approval
- **1 TX only** — gasless release via [[facilitator]]
- [[static-fee-calculator]] splits atomically on-chain:
  - Worker receives **87%** (net bounty)
  - Operator holds **13%** (fee)
- `distributeFees()` flushes accumulated fee to [[treasury]]

### Task Cancellation
- **Published** (no worker yet): no-op, no escrow locked
- **Accepted** (worker assigned): refund full bounty from escrow to agent

## Configuration

```bash
EM_PAYMENT_MODE=fase2           # Uses Fase 2 infrastructure
EM_ESCROW_MODE=direct_release   # Enables Fase 5 trustless behavior
```

## Key Properties

- **Fully trustless** — platform wallet never holds user funds
- **1 transaction at approval** — most gas-efficient release
- **Atomic fee split** — on-chain, no off-chain fee calculation
- **Deferred escrow** — only locks when worker is known
- **8 chains deployed** — Golden Flow 7/8 PASS consolidated

## Why "Credit Card Model"?

Like a credit card authorization: the charge is authorized (escrow locked) when the service provider (worker) is identified, not when the order is placed. The fee is deducted automatically at settlement.

## Related Concepts

- [[payment-operator]] — holds the fee and defines release conditions
- [[fee-structure]] — 87/13 split handled by [[static-fee-calculator]]
- [[x402r-escrow]] — Layer 1 contract holding locked funds
- [[facilitator]] — submits the single release transaction
- [[payment-dispatcher]] — routes to Fase 5 when `EM_ESCROW_MODE=direct_release`
