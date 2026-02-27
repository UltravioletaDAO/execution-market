---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - fee model
  - payment fees
  - 87/13 split
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - mcp_server/integrations/x402/payment_dispatcher.py
---

# Fee Structure

Execution Market charges a **13% platform fee** on every completed task. The fee is configurable, uses 6-decimal USDC precision, and has a $0.01 minimum.

## Fee Breakdown

For a $0.10 bounty task:

| Recipient | Amount | Percentage |
|-----------|--------|------------|
| Worker | $0.087 | 87% |
| [[treasury]] | $0.013 | 13% |
| **Total (agent pays)** | **$0.10** | **100%** |

## Configuration

```bash
EM_PLATFORM_FEE=0.13   # Default: 13%. Configurable per deployment.
```

## Fee Collection by Mode

| Mode | When Fee Collected | How |
|------|-------------------|-----|
| [[fase-1-direct-settlement]] | At approval | Separate [[eip-3009]] auth (agent -> treasury) |
| [[fase-2-escrow]] | At release | Platform wallet disburses after receiving from escrow |
| [[fase-5-trustless]] | At release | [[static-fee-calculator]] splits atomically on-chain |

## Protocol Fee Interaction

When BackTrack's [[protocol-fee]] is active, the x402r protocol takes its percentage (up to 5%) from the total. The [[treasury]] absorbs this automatically:

```
Treasury receives = 13% - protocol_fee%
```

This is computed by `_compute_treasury_remainder()` in the SDK client. The agent always pays exactly 13% — the protocol fee comes out of our share, not the agent's.

## Precision

- USDC uses **6 decimals** (1 USDC = 1,000,000 units)
- Minimum fee: **$0.01** (10,000 units)
- All fee calculations use `Decimal` for precision, sanitized to JSON-safe types before storage

## Related Concepts

- [[platform-fee]] — the 13% fee in detail
- [[protocol-fee]] — BackTrack's automatic deduction
- [[treasury]] — where platform fees accumulate
- [[static-fee-calculator]] — on-chain fee calculator for Fase 5
