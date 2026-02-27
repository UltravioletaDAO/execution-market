---
date: 2026-02-26
tags:
  - domain/blockchain
  - concept/fees
  - contract/fee-calculator
status: active
aliases:
  - StaticFeeCalculator
  - Fee Calculator
  - 13% Fee Split
related-files:
  - scripts/deploy-payment-operator.ts
  - mcp_server/integrations/x402/sdk_client.py
---

# StaticFeeCalculator

On-chain fee calculation contract used by Fase 5 [[payment-operator]]
contracts to split payments atomically at release time.

## Configuration

| Parameter | Value |
|-----------|-------|
| Fee rate | **1300 BPS** (13%) |
| Base address | `0xd643DB63028Cd1852AAFe62A0E3d2A5238d7465A` |

## How It Works

When a PaymentOperator releases escrowed funds, the StaticFeeCalculator
determines the split:

```
Gross bounty: $1.00 (locked in escrow)
    |
    +-- Worker receives: $0.87 (87%)
    +-- Operator holds:  $0.13 (13% fee)
```

The split happens atomically in a single transaction -- no intermediate
state where funds could be lost.

## Credit Card Model

Execution Market uses the **credit card convention** for fees:
- Agent pays the gross amount (bounty) into escrow
- Fee is deducted from the gross at release time
- Worker receives net (bounty - fee)
- Agent sees: "I paid $1.00"
- Worker sees: "I received $0.87"

## Fee Distribution

After release, fees accumulate in the PaymentOperator contract.
`distributeFees(USDC_address)` flushes accumulated fees to the
treasury wallet (`0xae07...`).

- Called best-effort after each release
- Also available via admin endpoint `POST /admin/fees/sweep`
- No urgency -- fees are safe in the operator contract until swept

## Interaction with Protocol Fee

When BackTrack's [[protocol-fee-config]] is active, the protocol fee
is deducted first. Treasury receives `13% - protocol_fee%`.

## Related

- [[fee-structure]] -- complete fee model documentation
- [[payment-operator]] -- contract that uses this calculator
