---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - x402r protocol fee
  - ProtocolFeeConfig
  - BackTrack fee
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - docs/planning/X402R_REFERENCE.md
---

# Protocol Fee

The **protocol fee** is BackTrack's fee for the x402r escrow protocol, controlled by the `ProtocolFeeConfig` contract (`0x59314674...`). It is completely separate from our [[platform-fee]].

## Key Parameters

| Parameter | Value |
|-----------|-------|
| Contract | `ProtocolFeeConfig` (`0x59314674...`) |
| Hard cap | **5%** (cannot exceed) |
| Timelock | **7 days** (changes take effect after delay) |
| Controller | BackTrack (Ali's team) |
| Reading | Dynamic, from chain |

## How It Works

When the protocol fee is active:

1. Agent pays **13% total** (unchanged from their perspective)
2. x402r protocol deducts its percentage (e.g., 2%)
3. Worker receives **100% of bounty** (unaffected)
4. [[treasury]] receives the **remainder**: `13% - protocol_fee%` (e.g., 11%)

The protocol fee is **read dynamically from chain** — our code adapts automatically via `_compute_treasury_remainder()` in the SDK client.

## Automatic Handling

No manual intervention needed. The SDK:

1. Reads `ProtocolFeeConfig` from chain
2. Computes treasury remainder after protocol deduction
3. Adjusts fee calculations transparently

The agent always sees 13%. The worker always gets their full bounty. Only our treasury share changes.

## Ownership Boundary

- **BackTrack controls**: `ProtocolFeeConfig` contract, fee percentage, timelock
- **We control**: how we read it, how we compute treasury remainder, [[facilitator]]
- See [[x402r-team-relationship]] for full ownership boundaries

## Related Concepts

- [[fee-structure]] — overall fee model
- [[platform-fee]] — our 13% fee (from which protocol fee is deducted)
- [[treasury]] — receives `13% - protocol_fee%`
- [[x402r-team-relationship]] — who controls what
