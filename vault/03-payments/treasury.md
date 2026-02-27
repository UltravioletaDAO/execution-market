---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - cold wallet
  - treasury wallet
  - 0xae07
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - mcp_server/integrations/x402/payment_dispatcher.py
---

# Treasury

The **treasury** is a cold wallet (Ledger hardware wallet) at address `0xae07...` that receives the 13% [[platform-fee]] on every successful task completion.

## Address

```
0xae07...  (Ledger cold wallet)
```

## Rules

> **CRITICAL**: The treasury has strict rules about what funds it receives.

- **ONLY receives**: 13% platform fee on successful task completion
- **NEVER a settlement target**: funds should not land here during task creation or escrow locking
- **If funds land here during task creation**: this is a **bug** (see incident below)
- **No withdrawal automation**: Ledger requires manual signing

## How Fees Arrive

| Payment Mode | How Treasury Gets Paid |
|--------------|----------------------|
| [[fase-1-direct-settlement]] | Direct [[eip-3009]] auth: agent -> treasury |
| [[fase-2-escrow]] | Platform wallet disburses after escrow release |
| [[fase-5-trustless]] | `distributeFees(USDC)` from [[payment-operator]] |

## Protocol Fee Absorption

When BackTrack's [[protocol-fee]] is active, the treasury automatically absorbs the reduction:

```
Treasury receives = 13% - protocol_fee%
```

Computed by `_compute_treasury_remainder()`. See [[fee-structure]] for details.

## Known Incidents

- **Feb 2026**: 3 tasks ($1.404 total) settled to treasury instead of platform wallet due to misconfigured settlement address. Pending Ledger refund to `0x13ef` on Base.

## Related Concepts

- [[wallet-roles]] — treasury is one of 5 key wallets
- [[fee-structure]] — how the 13% fee is computed
- [[platform-fee]] — the fee that flows to treasury
- [[protocol-fee]] — reduces treasury's share when active
