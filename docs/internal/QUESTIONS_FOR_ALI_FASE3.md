# Questions for Ali — Fase 3 Trustless PaymentOperator

**Date:** 2026-02-12
**Context:** We're upgrading our PaymentOperator on Base to be truly trustless with `OR(Payer, Facilitator)` conditions and enabling x402r on-chain fees.

**Current operator:** `0xb9635f544665758019159c04c08a3d583dadd723` (Facilitator-only, feeCalculator=address(0))

---

## Must-Ask Questions

### 1. What address should be the `feeRecipient`?

This is who receives the 1% operator fee from each release. We need BackTrack's treasury address on Base.

### 2. Is `StaticFeeCalculator` the right contract for a fixed 1% fee?

ABI: `deploy(address feeRecipient, uint16 feeBps)` at factory `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0`.

Confirm the factory interface and that 100 BPS = 1%.

### 3. Does the protocol fee (`ProtocolFeeConfig` at `0x59314674...`) apply ON TOP of the operator fee?

If yes, the agent pays 1% operator + protocol fee to the x402r ecosystem. We need to know the total on-chain deduction to calculate EM's share correctly.

### 4. Do we need to call `distributeFees()` on the operator to flush accumulated fees, or are fees deducted at release time?

Determines if we need a cron job / manual trigger.

### 5. After we deploy the new operator, do you (Facilitator) need to register it in `addresses.rs`?

Current operator `0xb9635f...` is registered. New operator with different config = different address. Facilitator needs to know about it.

**Important:** Both old AND new operators must remain registered. Old tasks reference old operator in their PaymentInfo.

### 6. For `OR(PayerCondition, StaticAddressCondition(Facilitator))`: does the Facilitator need any code changes to work with this?

Currently Facilitator only expects to be the sole authorized caller. If payer can also release, does this affect Facilitator's state tracking?

### 7. Is there an `OrConditionFactory.getDeployed()` view function to check if a specific OR condition already exists?

For idempotent deployment. Factory at `0x1e52a74cE6b69F04a506eF815743E1052A1BD28F`.

---

## Nice-to-Ask Questions

### 8. Does x402r have a standard "marketplace" fee split recommendation?

You have `deployMarketplaceOperator()` preset with `operatorFeeBps` param. Any recommended range?

### 9. Can the `ArbiterRegistry` (`0xB68C02...`) be used for future dispute resolution with MoltCourt?

Future phase — just understanding capability.

### 10. When agents call release/refund directly (via `PayerCondition`), do they need to interact with the Facilitator first, or can they call the operator contract directly?

Determines if we need a new MCP tool for direct agent release.

---

## Our Planned Config (for reference)

```
feeRecipient              = [YOUR ANSWER TO Q1]
feeCalculator             = StaticFeeCalculator(feeRecipient, 100 BPS)
authorizeCondition        = UsdcTvlLimit (0x67B6...)         ← no change
releaseCondition          = OR(PayerCondition, StaticAddressCondition(Facilitator))
refundInEscrowCondition   = OR(PayerCondition, StaticAddressCondition(Facilitator))
refundPostEscrowCondition = address(0)                       ← future: dispute resolution
all recorders             = address(0)
```

**Fee model:**
- Total fee to agent: **13% of bounty**
- EM treasury: **12%**
- x402r on-chain (via feeCalculator): **~1%**
- Worker gets: **full bounty** (no change)

**Deploy script ready:** `scripts/deploy-payment-operator.ts --fase3 --dry-run`
