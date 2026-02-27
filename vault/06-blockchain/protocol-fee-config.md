---
date: 2026-02-26
tags:
  - domain/blockchain
  - concept/fees
  - contract/protocol-fee
  - external/backtrack
status: active
aliases:
  - ProtocolFeeConfig
  - Protocol Fee
  - x402r Protocol Fee
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - docs/planning/X402R_REFERENCE.md
---

# ProtocolFeeConfig

On-chain contract controlled by **BackTrack** (Ali) that defines the
x402r protocol fee. This is separate from and additional to
Execution Market's 13% platform fee.

## Contract Details

| Field | Value |
|-------|-------|
| Address | `0x59314674...` (truncated for brevity) |
| Controller | BackTrack (Ali) |
| Hard cap | **5%** (immutable on-chain) |
| Timelock | **7 days** for any fee change |
| Current status | May be 0% (read dynamically) |

## How It Works

The protocol fee is read **dynamically from chain** at settlement time:

```
Agent pays 13% total platform fee
    |
    +-- Protocol fee (0-5%): goes to x402r protocol (BackTrack)
    +-- Remainder: goes to Execution Market treasury
    |
    Example with 2% protocol fee:
      Agent pays $0.13 fee on $1.00 bounty
      x402r protocol gets: $0.02
      EM treasury gets:    $0.11
      Worker gets:         $0.87 (unchanged)
```

## Key Properties

- **Agent cost unchanged**: Agent always pays 13% regardless of protocol fee
- **Worker payment unchanged**: Worker always gets 87% of bounty
- **Treasury absorbs**: Protocol fee comes from treasury share, not worker
- **Automatic**: Code reads from chain, no manual updates needed
- **Capped**: Cannot exceed 5% (enforced by smart contract)
- **Timelocked**: 7-day delay for any changes (visible on-chain)

## Ownership Boundary

- **BackTrack controls**: ProtocolFeeConfig contract, fee percentage
- **Ultravioleta controls**: Facilitator, PaymentOperators, platform fee %
- Our code reads their contract; they cannot change our contracts

## Treasury Remainder Calculation

`_compute_treasury_remainder()` in the PaymentDispatcher:

```python
treasury_amount = total_fee - protocol_fee - worker_payment_overhead
```

Treasury is always the remainder after all other deductions.

## Related

- [[protocol-fee]] -- broader fee strategy discussion
- [[x402r-team-relationship]] -- BackTrack/Ali coordination
