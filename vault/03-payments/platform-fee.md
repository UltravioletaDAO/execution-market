---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - 13% fee
  - EM_PLATFORM_FEE
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - scripts/deploy-payment-operator.ts
---

# Platform Fee

The **platform fee** is 13% of the task bounty, charged to the publishing agent on successful task completion. It is the primary revenue mechanism for Execution Market.

## Configuration

```bash
EM_PLATFORM_FEE=0.13   # 13%, configurable
```

## Collection Mechanism

The fee is collected differently depending on the payment mode:

### Fase 1 (Direct Settlement)
At approval, the server signs a separate [[eip-3009]] authorization:
- `agent -> [[treasury]]`: 13% of bounty
- Submitted alongside the worker payment via [[facilitator]]

### Fase 5 (Trustless)
The [[static-fee-calculator]] (1300 BPS) is configured in the [[payment-operator]]:
- At release, the on-chain calculator atomically deducts 13%
- Worker receives 87%, operator contract holds 13%
- `distributeFees(USDC)` flushes accumulated fees to [[treasury]]

## Fee Sweep (Admin)

For Fase 5, fees accumulate in the [[payment-operator]] contract until flushed:

```
POST /admin/fees/sweep     # Triggers distributeFees() on all chains
GET  /admin/fees/accrued   # Check accumulated fees per chain
```

`distributeFees()` is also called best-effort after each release.

## Minimums

- **Minimum fee**: $0.01 (enforced in code)
- **6-decimal precision**: USDC native precision, no rounding issues

## Related Concepts

- [[fee-structure]] — overall fee model including protocol fee interaction
- [[static-fee-calculator]] — on-chain 1300 BPS calculator
- [[treasury]] — destination for all collected fees
- [[protocol-fee]] — BackTrack's deduction from our fee share
