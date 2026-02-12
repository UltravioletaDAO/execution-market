# Follow-up for Ali — Fase 3 (Round 2, Final)

**Date:** 2026-02-12
**Context:** We sent 10 questions. Ali answered 4. We researched the remaining 6 ourselves by reading the x402r-contracts source code, x402r-sdk, docs, and querying the contracts on-chain via `cast`.

**Current operator:** `0xb9635f544665758019159c04c08a3d583dadd723` (Facilitator-only, feeCalculator=address(0))

---

## What we figured out ourselves (no need to ask Ali)

### C1. FEE_RECIPIENT on our operator

**ANSWERED:** `FEE_RECIPIENT` is a field on the PaymentOperator itself, NOT on the StaticFeeCalculator. Our current operator already has `FEE_RECIPIENT = 0xae07...` (our treasury). The `StaticFeeCalculator` constructor takes only `uint256 feeBps` — no address parameter.

```
Verified on-chain:
  cast call 0xb9635f...  "FEE_RECIPIENT()(address)" → 0xae07cEB6b395BC685a776a0b4c489E8d9cE9A6ad ✓
  cast call 0xb9635f...  "FEE_CALCULATOR()(address)" → address(0) ✓
```

**Deployment plan:** `StaticFeeCalculatorFactory.deploy(100)` → 1% fee. `FEE_RECIPIENT` stays as our treasury. Factory: `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0`.

### C2. ProtocolFeeConfig current fee on Base

**ANSWERED:** Protocol fee is currently **0%**. The fee calculator on ProtocolFeeConfig is set to `address(0)`.

```
Verified on-chain (ProtocolFeeConfig: 0x59314674BAbb1a24Eb2704468a9cCdD50668a1C6):
  cast call ... "calculator()(address)"              → address(0) ← NO FEE CURRENTLY
  cast call ... "MAX_PROTOCOL_FEE_BPS()(uint256)"    → 500 (5% hard cap)
  cast call ... "TIMELOCK_DELAY()(uint256)"           → 604800 (7 days)
  cast call ... "owner()(address)"                    → 0x773dBcB5... (BackTrack)
  cast call ... "getProtocolFeeRecipient()(address)"  → 0x773dBcB5... (BackTrack)
```

**Impact on our fee model:** Agent pays 13% total = 12% EM (off-chain) + 1% operator fee (on-chain to our treasury) + 0% protocol fee. If BackTrack enables protocol fees later, it stacks on top (up to 5%, with 7-day timelock notice).

### Q2. StaticFeeCalculator interface

**ANSWERED:** Read the Solidity source. Constructor: `constructor(uint256 _feeBps)`. Factory: `deploy(uint256 feeBps)`, `getDeployed(uint256 feeBps)`, `computeAddress(uint256 feeBps)`. 100 BPS = 1% confirmed.

### Q4. distributeFees() behavior

**ANSWERED:** Read the PaymentOperator Solidity source. Fees accumulate in the operator contract after each `release()`. The `distributeFees(address token)` function must be called explicitly to flush them. It's permissionless — anyone can call it. Splits between protocol fee recipient and FEE_RECIPIENT based on fee calculator ratios.

We'll set up a cron job or call it periodically.

### Q6. Facilitator + OR conditions

**ANSWERED:** The Facilitator has **zero awareness** of conditions. All condition checks happen on-chain in the PaymentOperator contract. The Facilitator just calls `operator.release(paymentId)` — the contract checks `releaseCondition.check()` which evaluates the OR.

If a payer releases directly (bypassing Facilitator), the Facilitator won't know about it. But the Facilitator has no internal "locked" state — it's stateless per-request. It will simply get a revert if it tries to release already-released funds. No corruption.

**Source:** Read `PaymentOperator.sol` — conditions are checked inline during release/refund. Facilitator code has no condition-related logic.

### Q7. OrConditionFactory.getDeployed()

**ANSWERED:** Yes, it exists. `getDeployed(ICondition[] memory conditions)` returns the deployed address or `address(0)` if not yet deployed. Also has `computeAddress(ICondition[] memory conditions)` for pre-computation. CREATE2 deterministic = idempotent.

### Q8. Recommended fee range

**ANSWERED:** The SDK's `deployMarketplaceOperator()` has an `operatorFeeBps` parameter with no enforced range. Our 100 BPS (1%) is reasonable. The only hard cap is on protocol fees (500 BPS / 5%).

---

## What ONLY Ali can answer / do

### NOTHING IS BLOCKING ON ALI

After further investigation, we confirmed that `addresses.rs` is in **our own fork** (`UltravioletaDAO/x402-rs`), not BackTrack's. We control the Facilitator deployment entirely.

**What we'll do ourselves when deploying the new operator:**

1. Change `payment_operator: Option<Address>` → `Vec<Address>` in `addresses.rs` (line 233)
2. Update `validate_addresses()` in `operator.rs` (line 586) to check against the vec
3. Add both old (`0xb9635f...`) and new operator addresses to the Base entry
4. Rebuild and redeploy our Facilitator at `facilitator.ultravioletadao.xyz`

### Nice-to-have: Protocol fee change notification

Currently protocol fee = 0% on Base. When BackTrack enables it (via ProtocolFeeConfig), the 7-day timelock gives on-chain notice. But it would be nice to get a heads-up from Ali so we can update our UI.

**Not blocking.** We can also monitor the ProtocolFeeConfig contract's `pendingCalculator()` and `pendingCalculatorTimestamp()` functions ourselves.

---

## Summary

| Status | Count | Detail |
|--------|-------|--------|
| Answered by Ali (Round 1) | 4 | Q1, Q3, Q9, Q10 |
| Answered by our research | 6 | C1, C2, Q2, Q4, Q6, Q7, Q8 |
| Answered (we own the facilitator) | 1 | Operator registration = our own code |
| Nice to have from Ali | 1 | Protocol fee change heads-up |

**Result: ZERO blocking questions for Ali. We can deploy Fase 3 autonomously.**

---

## Our research method

We ran a 5-agent parallel research swarm that read:
1. `BackTrackCo/x402r-contracts` — All Solidity source (PaymentOperator, StaticFeeCalculator, OrCondition, PayerCondition, ProtocolFeeConfig)
2. `BackTrackCo/x402r-sdk` — TypeScript SDK (deployment presets, factory wrappers, marketplace helpers)
3. `BackTrackCo/docs` — x402r docs site (Mintlify, architecture guides)
4. Local `x402-rs/` — Our Facilitator fork (addresses.rs, payment handler, state management)
5. Other BackTrackCo repos — Supporting infrastructure

Plus on-chain verification via `cast` on Base mainnet for ProtocolFeeConfig and our PaymentOperator.
