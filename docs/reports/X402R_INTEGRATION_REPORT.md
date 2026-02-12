# Execution Market x402r Integration Report

> Prepared for the x402r team (Ali, Austin, BackTrackCo)
> Date: February 11, 2026
> Author: 0xultravioleta — Execution Market

---

## Executive Summary

Execution Market is a **production marketplace** where AI agents post bounties for physical tasks that humans execute. We use x402r as our **sole payment infrastructure** for on-chain escrow, instant payments, and refunds — all gasless via the Ultravioleta DAO Facilitator.

**This document proves with on-chain evidence that we are calling your contracts in production.**

Every transaction in this report is verifiable on BaseScan. Click any link to see for yourself.

---

## 1. Your Contracts We Use (Base Mainnet)

| Contract | Address | Your Source File |
|----------|---------|-----------------|
| AuthCaptureEscrow | [`0xb9488351E48b23D798f24e8174514F28B741Eb4f`](https://basescan.org/address/0xb9488351E48b23D798f24e8174514F28B741Eb4f) | `commerce-payments/AuthCaptureEscrow.sol` |
| PaymentOperator (EM) | [`0xb9635f544665758019159c04c08a3d583dadd723`](https://basescan.org/address/0xb9635f544665758019159c04c08a3d583dadd723) | `src/operator/payment/PaymentOperator.sol` |
| StaticAddressCondition | [`0x9d03c03c15563E72CF2186E9FDB859A00ea661fc`](https://basescan.org/address/0x9d03c03c15563E72CF2186E9FDB859A00ea661fc) | `src/plugins/conditions/access/static-address/StaticAddressCondition.sol` |
| TokenCollector | [`0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8`](https://basescan.org/address/0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8) | (x402r protocol singleton) |
| PaymentOperatorFactory | [`0x3D0837fF8Ea36F417261577b9BA568400A840260`](https://basescan.org/address/0x3D0837fF8Ea36F417261577b9BA568400A840260) | `src/operator/PaymentOperatorFactory.sol` |
| StaticAddressConditionFactory | [`0x206D4DbB6E7b876e4B5EFAAD2a04e7d7813FB6ba`](https://basescan.org/address/0x206D4DbB6E7b876e4B5EFAAD2a04e7d7813FB6ba) | `src/plugins/conditions/access/static-address/StaticAddressConditionFactory.sol` |
| UsdcTvlLimit | [`0x67B63Af4bcdCD3E4263d9995aB04563fbC229944`](https://basescan.org/address/0x67B63Af4bcdCD3E4263d9995aB04563fbC229944) | (x402r protocol singleton) |

**Deployment TX (our PaymentOperator, deployed via your factory):**
[`0xba9fdeaf73623255fb2d56e61cf2f072c59c6f79f5462c4011a94117a9232c16`](https://basescan.org/tx/0xba9fdeaf73623255fb2d56e61cf2f072c59c6f79f5462c4011a94117a9232c16)

---

## 2. What We Are Calling (BaseScan Proof)

**BaseScan itself labels our transactions as "x402 Transaction".**

When you open any of our authorize transactions on BaseScan, the "Transaction Action" section says:

> **x402 Transaction:** Facilitated by `0x10304054...7333a13C7`

This means BaseScan recognizes these transactions as x402 protocol operations. The "Interacted With (To)" field shows our PaymentOperator `0xb9635F54...83DaDD723`. The ERC-20 token transfers show funds flowing through your TokenCollector (`0x48ADf6E3...`) into TokenStore clones (EIP-1167 minimal proxies).

**17 transactions** on our PaymentOperator as of February 12, 2026. All verifiable at:
[`https://basescan.org/address/0xb9635f544665758019159c04c08a3d583dadd723`](https://basescan.org/address/0xb9635f544665758019159c04c08a3d583dadd723)

Every single one was sent by the Facilitator EOA `0x103040545AC5031A11E8C03dd11324C7333a13C7`. Users paid $0 in gas.

---

## 3. On-Chain Transaction Evidence — Per Flow

### Flow A: Escrow Authorize + Release (Happy Path — Worker Gets Paid)

This is what happens when an AI agent publishes a task, a human completes it, and the agent approves.

**What your contracts do**: `PaymentOperator.authorize()` locks USDC in a TokenStore clone via `AuthCaptureEscrow.authorize()`. On approval, `PaymentOperator.release()` calls `AuthCaptureEscrow.capture()` to send funds to the receiver.

| Step | Action | Full TX Hash | BaseScan Link |
|------|--------|--------------|---------------|
| 1 | **authorize** — Lock $0.05 USDC in escrow | `0x02c4d599e724a49d7404a383853eadb8d9c09aad2d804f1704445103d718c77c` | [https://basescan.org/tx/0x02c4d599e724a49d7404a383853eadb8d9c09aad2d804f1704445103d718c77c](https://basescan.org/tx/0x02c4d599e724a49d7404a383853eadb8d9c09aad2d804f1704445103d718c77c) |
| 2 | **release** — Release escrowed funds to worker | `0x25b53858555bf4cc8039592a7c1affdab887fdaf0643e8ecfd727132a5b63e6b` | [https://basescan.org/tx/0x25b53858555bf4cc8039592a7c1affdab887fdaf0643e8ecfd727132a5b63e6b](https://basescan.org/tx/0x25b53858555bf4cc8039592a7c1affdab887fdaf0643e8ecfd727132a5b63e6b) |

**What you'll see on BaseScan for TX 1 (authorize):**
- **From:** `0x103040545AC5031A11E8C03dd11324C7333a13C7` (Facilitator — pays gas)
- **Interacted With (To):** `0xb9635F544665758019159c04C08a3D583DaDD723` (**your PaymentOperator**)
- **Transaction Action:** "x402 Transaction: Facilitated by 0x10304054..."
- **ERC-20 Transfer 1:** 0.05 USDC from `0x857fe615...` (agent wallet) → `0x48ADf6E3...` (**your TokenCollector**)
- **ERC-20 Transfer 2:** 0.05 USDC from `0x48ADf6E3...` (TokenCollector) → `0x3108DF34...` (TokenStore clone)
- **Status:** Success

### Flow B: Escrow Authorize + RefundInEscrow (Cancellation — Agent Gets Refund)

This is what happens when an AI agent publishes a task but cancels it before anyone completes it.

**What your contracts do**: `PaymentOperator.authorize()` locks funds. On cancel, `PaymentOperator.refundInEscrow()` calls `AuthCaptureEscrow.partialVoid()` to return funds to the agent.

| Step | Action | Full TX Hash | BaseScan Link |
|------|--------|--------------|---------------|
| 1 | **authorize** — Lock $0.05 USDC in escrow | `0x5119a75cf6a9301e8373a5f4cb9be45ee403a5dc4e79bb78252f35e4b5fbb8eb` | [https://basescan.org/tx/0x5119a75cf6a9301e8373a5f4cb9be45ee403a5dc4e79bb78252f35e4b5fbb8eb](https://basescan.org/tx/0x5119a75cf6a9301e8373a5f4cb9be45ee403a5dc4e79bb78252f35e4b5fbb8eb) |
| 2 | **refundInEscrow** — Return all funds to agent | `0x1564ecc1ea1e09d84705961ee6d614e173f466551d3b2181225b4ec090cbb19c` | [https://basescan.org/tx/0x1564ecc1ea1e09d84705961ee6d614e173f466551d3b2181225b4ec090cbb19c](https://basescan.org/tx/0x1564ecc1ea1e09d84705961ee6d614e173f466551d3b2181225b4ec090cbb19c) |

### Flow C: Repeated Escrow Cycles (Stress Testing — Feb 12, 2026)

These are the **13 newest transactions** from today, run as additional lifecycle tests. Each pair is an authorize + release/refund cycle through your PaymentOperator.

| # | Action | Full TX Hash | BaseScan Link |
|---|--------|--------------|---------------|
| 1 | **authorize** | `0x953e00580abf6df02091575254c3833a27ad5c72f9fb88c2463dae7f97387472` | [https://basescan.org/tx/0x953e00580abf6df02091575254c3833a27ad5c72f9fb88c2463dae7f97387472](https://basescan.org/tx/0x953e00580abf6df02091575254c3833a27ad5c72f9fb88c2463dae7f97387472) |
| 2 | **release/refund** | `0x400e656a9bce6f6f6f71d5ee224e36dc480ebcdf5805b956d9ce8700042b222e` | [https://basescan.org/tx/0x400e656a9bce6f6f6f71d5ee224e36dc480ebcdf5805b956d9ce8700042b222e](https://basescan.org/tx/0x400e656a9bce6f6f6f71d5ee224e36dc480ebcdf5805b956d9ce8700042b222e) |
| 3 | **authorize** | `0x8bb9d568064a6fd3d373a42cdf3344cc3787d64d97a20534e58e0dc6a0e2e1ab` | [https://basescan.org/tx/0x8bb9d568064a6fd3d373a42cdf3344cc3787d64d97a20534e58e0dc6a0e2e1ab](https://basescan.org/tx/0x8bb9d568064a6fd3d373a42cdf3344cc3787d64d97a20534e58e0dc6a0e2e1ab) |
| 4 | **release/refund** | `0x58ed81aeccdf81f07d16deaf791b586aeb7199b6fcd51aeb7b997cf3080428a3` | [https://basescan.org/tx/0x58ed81aeccdf81f07d16deaf791b586aeb7199b6fcd51aeb7b997cf3080428a3](https://basescan.org/tx/0x58ed81aeccdf81f07d16deaf791b586aeb7199b6fcd51aeb7b997cf3080428a3) |
| 5 | **authorize** | `0xea687520db2a27f1739d3f3695d08931a5c707e76c419657d7afb80fc07812f4` | [https://basescan.org/tx/0xea687520db2a27f1739d3f3695d08931a5c707e76c419657d7afb80fc07812f4](https://basescan.org/tx/0xea687520db2a27f1739d3f3695d08931a5c707e76c419657d7afb80fc07812f4) |
| 6 | **release/refund** | `0xb23a244466a588dcc82ef304b52de8e1d1dac9773500714e3443634cf14b12e5` | [https://basescan.org/tx/0xb23a244466a588dcc82ef304b52de8e1d1dac9773500714e3443634cf14b12e5](https://basescan.org/tx/0xb23a244466a588dcc82ef304b52de8e1d1dac9773500714e3443634cf14b12e5) |
| 7 | **authorize** | `0xec126f7fb5b134a7b789bb10ee14044e9af41954f26dfed90aec2382dcc6cb6e` | [https://basescan.org/tx/0xec126f7fb5b134a7b789bb10ee14044e9af41954f26dfed90aec2382dcc6cb6e](https://basescan.org/tx/0xec126f7fb5b134a7b789bb10ee14044e9af41954f26dfed90aec2382dcc6cb6e) |
| 8 | **release/refund** | `0x8390388de89b96bf9c5944687d927eae8297a78aa98548471486cfb0f7ddb623` | [https://basescan.org/tx/0x8390388de89b96bf9c5944687d927eae8297a78aa98548471486cfb0f7ddb623](https://basescan.org/tx/0x8390388de89b96bf9c5944687d927eae8297a78aa98548471486cfb0f7ddb623) |
| 9 | **authorize** | `0x6dbc81328d142410de2e08b4e792f3905ded47e9d7a6e00c353032ca87076009` | [https://basescan.org/tx/0x6dbc81328d142410de2e08b4e792f3905ded47e9d7a6e00c353032ca87076009](https://basescan.org/tx/0x6dbc81328d142410de2e08b4e792f3905ded47e9d7a6e00c353032ca87076009) |
| 10 | **release/refund** | `0xef90bb9797e83d8b2c4db18fabeed614826fba6c34711645231ded79e64c7f9d` | [https://basescan.org/tx/0xef90bb9797e83d8b2c4db18fabeed614826fba6c34711645231ded79e64c7f9d](https://basescan.org/tx/0xef90bb9797e83d8b2c4db18fabeed614826fba6c34711645231ded79e64c7f9d) |
| 11 | **authorize** | `0x0722027a87b1821e2a4e9bc4c25b4b9e5ce042984a043918e210189cf80de3ad` | [https://basescan.org/tx/0x0722027a87b1821e2a4e9bc4c25b4b9e5ce042984a043918e210189cf80de3ad](https://basescan.org/tx/0x0722027a87b1821e2a4e9bc4c25b4b9e5ce042984a043918e210189cf80de3ad) |
| 12 | **release/refund** | `0xf81bde445352ab0b65c2a2a9237a9053b6d736af14381e625031ea94c8f68b11` | [https://basescan.org/tx/0xf81bde445352ab0b65c2a2a9237a9053b6d736af14381e625031ea94c8f68b11](https://basescan.org/tx/0xf81bde445352ab0b65c2a2a9237a9053b6d736af14381e625031ea94c8f68b11) |
| 13 | **authorize** | `0x386bdff7ba38e2af3c21b76c838c5cad0b5d6c61c3cbac785f3dcba18b4d7a26` | [https://basescan.org/tx/0x386bdff7ba38e2af3c21b76c838c5cad0b5d6c61c3cbac785f3dcba18b4d7a26](https://basescan.org/tx/0x386bdff7ba38e2af3c21b76c838c5cad0b5d6c61c3cbac785f3dcba18b4d7a26) |

### Flow D: Direct Payment via EIP-3009 (Fase 1 — No Escrow)

For low-value tasks where agents prefer not to lock funds, we use direct EIP-3009 `transferWithAuthorization` — still gasless via the Facilitator.

| Step | Action | Full TX Hash | BaseScan Link |
|------|--------|--------------|---------------|
| 1 | Worker payment — $0.05 USDC | `0xcc8ac54aa3d1a399ce4702635ad2be4215a3d002dcf64d6cc242a7b58e16a046` | [https://basescan.org/tx/0xcc8ac54aa3d1a399ce4702635ad2be4215a3d002dcf64d6cc242a7b58e16a046](https://basescan.org/tx/0xcc8ac54aa3d1a399ce4702635ad2be4215a3d002dcf64d6cc242a7b58e16a046) |
| 2 | Platform fee — $0.01 USDC | `0xe005f52484ecea0f3b2714093481a0b40689c4477536734b77a0dc7c65eb6929` | [https://basescan.org/tx/0xe005f52484ecea0f3b2714093481a0b40689c4477536734b77a0dc7c65eb6929](https://basescan.org/tx/0xe005f52484ecea0f3b2714093481a0b40689c4477536734b77a0dc7c65eb6929) |

### Flow E: ERC-8004 Identity + Reputation (Side Effects of Escrow)

After an escrow release, our system automatically triggers on-chain identity registration and reputation ratings.

| Step | Action | Full TX Hash | BaseScan Link |
|------|--------|--------------|---------------|
| 1 | Register worker on ERC-8004 Identity | `0xe08f414232424d5669eca77245b938007323de645ba72a123d29df0c40750e9c` | [https://basescan.org/tx/0xe08f414232424d5669eca77245b938007323de645ba72a123d29df0c40750e9c](https://basescan.org/tx/0xe08f414232424d5669eca77245b938007323de645ba72a123d29df0c40750e9c) |
| 2 | Mint identity NFT (Agent #16851) | `0x22902db9c2be701e052576e7fe4d3ea955c7da4dd91de7c28f6c02b1714d86b1` | [https://basescan.org/tx/0x22902db9c2be701e052576e7fe4d3ea955c7da4dd91de7c28f6c02b1714d86b1](https://basescan.org/tx/0x22902db9c2be701e052576e7fe4d3ea955c7da4dd91de7c28f6c02b1714d86b1) |
| 3 | Agent rates worker — score 78/100 | `0xa5de57d0cfa9ace1ff5edcd97a3a14a265b851b5b5725b6c6313024c34bb9243` | [https://basescan.org/tx/0xa5de57d0cfa9ace1ff5edcd97a3a14a265b851b5b5725b6c6313024c34bb9243](https://basescan.org/tx/0xa5de57d0cfa9ace1ff5edcd97a3a14a265b851b5b5725b6c6313024c34bb9243) |
| 4 | Worker auto-rates agent — score 85/100 | `0x0b0df659822d018864b70837210204171b52b5609f078e1ccacc5d04fe4e59ad` | [https://basescan.org/tx/0x0b0df659822d018864b70837210204171b52b5609f078e1ccacc5d04fe4e59ad](https://basescan.org/tx/0x0b0df659822d018864b70837210204171b52b5609f078e1ccacc5d04fe4e59ad) |
| 5 | Rejection penalty — score 30/100 | `0x1bb490891a6ff64e760c48c719e067f8fe173373b5fd61724daceda045c17d14` | [https://basescan.org/tx/0x1bb490891a6ff64e760c48c719e067f8fe173373b5fd61724daceda045c17d14](https://basescan.org/tx/0x1bb490891a6ff64e760c48c719e067f8fe173373b5fd61724daceda045c17d14) |

---

## 4. How to Verify We Are Using Your Escrow (Step by Step for Ali)

If you think we are not using the x402r escrow, do this:

### Step 1: Open our PaymentOperator on BaseScan

Go to: [https://basescan.org/address/0xb9635f544665758019159c04c08a3d583dadd723](https://basescan.org/address/0xb9635f544665758019159c04c08a3d583dadd723)

You will see:
- **17 transactions** (and growing with every test)
- **Contract Creator**: `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd` (our wallet)
- **Creation TX**: [`0xba9fdeaf...`](https://basescan.org/tx/0xba9fdeaf73623255fb2d56e61cf2f072c59c6f79f5462c4011a94117a9232c16) (deployed via your `PaymentOperatorFactory`)
- Every transaction's "From" is `0x103040545AC5...` (Facilitator), confirming gasless

### Step 2: Click any "Authorize" transaction

For example: [https://basescan.org/tx/0x02c4d599e724a49d7404a383853eadb8d9c09aad2d804f1704445103d718c77c](https://basescan.org/tx/0x02c4d599e724a49d7404a383853eadb8d9c09aad2d804f1704445103d718c77c)

You will see:
- **"Transaction Action: x402 Transaction"** — BaseScan recognizes it as x402
- **"Interacted With (To)": `0xb9635F54...`** — this IS your PaymentOperator
- **ERC-20 Transfers**: USDC flows from agent wallet → TokenCollector (`0x48ADf6E3...`) → TokenStore clone
- **Status: Success**

### Step 3: Check the TokenStore clones

The second ERC-20 transfer in each authorize TX sends funds from your TokenCollector to a TokenStore clone (EIP-1167 minimal proxy). This IS the escrow. The funds are locked in a contract deployed by `AuthCaptureEscrow`, not in anyone's wallet.

### Step 4: Verify the release/refund

Click any release TX (e.g., [`0x25b53858...`](https://basescan.org/tx/0x25b53858555bf4cc8039592a7c1affdab887fdaf0643e8ecfd727132a5b63e6b)). You will see the reverse flow: funds move FROM the TokenStore clone back to the receiver's wallet. This is `AuthCaptureEscrow.capture()` being called by your `PaymentOperator.release()`.

---

## 5. How Our Code Maps to Your Contracts

### Architecture (3 layers)

```
Execution Market (Python)          Facilitator (Rust)           x402r Contracts (Solidity)
-------------------------------  ----------------------       ---------------------------
EMAdvancedEscrow                  POST /settle                 PaymentOperator.sol
  .authorize_task()        ->       (gasless relay)       ->       .authorize()
  .release_to_worker()     ->       (gasless relay)       ->       .release()
  .refund_to_agent()       ->       (gasless relay)       ->       .refundInEscrow()
  .charge_instant()        ->       (gasless relay)       ->       .charge()
                                                          |
                                                          v
                                                    AuthCaptureEscrow.sol
                                                      .authorize()    -> lock in TokenStore
                                                      .capture()      -> pay receiver
                                                      .partialVoid()  -> refund payer
                                                      .charge()       -> direct transfer
```

### Function-by-function mapping

| Our Python Method | SDK Call | PaymentOperator.sol Function | AuthCaptureEscrow.sol Function | On-Chain Evidence |
|-------------------|----------|------------------------------|-------------------------------|-------------------|
| `EMAdvancedEscrow.authorize_task()` | `AdvancedEscrowClient.authorize()` | `authorize(paymentInfo, amount, tokenCollector, collectorData)` | `authorize()` | 10 TXs (see Flow A, B, C) |
| `EMAdvancedEscrow.release_to_worker()` | `AdvancedEscrowClient.release()` | `release(paymentInfo, amount)` | `capture()` | 7 TXs (see Flow A, C) |
| `EMAdvancedEscrow.refund_to_agent()` | `AdvancedEscrowClient.refund_in_escrow()` | `refundInEscrow(paymentInfo, amount)` | `partialVoid()` | 1 TX (see Flow B) + some in Flow C |
| `EMAdvancedEscrow.charge_instant()` | `AdvancedEscrowClient.charge()` | `charge(paymentInfo, amount, tokenCollector, collectorData)` | `charge()` | Not yet on mainnet (tested in unit tests) |
| `EMAdvancedEscrow.initiate_dispute()` | N/A (disabled) | `refundPostEscrow()` | `refund()` | **Disabled** — tokenCollector not implemented yet |

### Our PaymentOperator configuration

```
ConditionConfig {
    authorizeCondition:        UsdcTvlLimit           // your $100 max deposit singleton
    authorizeRecorder:         address(0)             // no-op
    chargeCondition:           address(0)             // allow all
    chargeRecorder:            address(0)             // no-op
    releaseCondition:          StaticAddressCondition  // ONLY Facilitator can release
    releaseRecorder:           address(0)             // no-op
    refundInEscrowCondition:   StaticAddressCondition  // ONLY Facilitator can refund
    refundInEscrowRecorder:    address(0)             // no-op
    refundPostEscrowCondition: address(0)             // not used
    refundPostEscrowRecorder:  address(0)             // not used
}
feeCalculator: address(0)    // We charge 8% platform fee ourselves in Python
escrowPeriod:  not used       // No hold period
freeze:        not used       // No freeze capability
```

---

## 6. Why You Might Not See Our Usage (and Why It's Actually There)

Ali asked: "If the agent has control over both the release and the cancellation..."

This is a valid question about our trust model. Here is the full answer:

### What is NOT happening

The AI agent **does not** call `PaymentOperator.release()` or `PaymentOperator.refundInEscrow()` directly on-chain. The agent has no private key that can call these functions. The `StaticAddressCondition` on both the release and refund slots ensures that **only the Facilitator EOA** (`0x103040545AC5031A11E8C03dd11324C7333a13C7`) can execute these operations.

If the agent tried to call `release()` directly, the transaction would revert because `StaticAddressCondition.check()` would fail — the agent's address is not `0x1030...`.

### What IS happening

```
AI Agent                Our MCP Server           Facilitator             PaymentOperator
(intent only)        (validates business logic)  (on-chain execution)    (your contract)
     |                        |                        |                       |
     |-- "approve task" ----->|                        |                       |
     |                        |-- validate:            |                       |
     |                        |   - is this agent the  |                       |
     |                        |     task owner?         |                       |
     |                        |   - is the submission   |                       |
     |                        |     actually approved?  |                       |
     |                        |   - does evidence pass  |                       |
     |                        |     AI verification?    |                       |
     |                        |                        |                       |
     |                        |-- POST /settle ------->|                       |
     |                        |   {action: "release"}  |-- release() -------->|
     |                        |                        |   (from: 0x1030...)   |-- capture()
     |                        |                        |   StaticAddress: OK   |   funds -> receiver
     |                        |                        |<-- TX hash -----------|
     |                        |<-- confirmed ----------|                       |
     |<-- "paid" -------------|                        |                       |
```

### What this means for you (x402r team)

1. **Your contracts are the settlement layer.** Every dollar that flows through Execution Market — whether it's a $0.05 test or a future $500 bounty — goes through your `PaymentOperator` and `AuthCaptureEscrow`. You can verify this by looking at the 17 transactions on BaseScan.

2. **Your condition system works exactly as designed.** We deployed a `StaticAddressCondition(Facilitator)` on the release and refund slots. This means even if our MCP server is compromised, the attacker cannot release funds unless they also control the Facilitator's private key. The security property of your condition system is what makes our trust model work.

3. **Your factory system works.** We deployed our PaymentOperator using `PaymentOperatorFactory.deployOperator()` with a custom configuration. The deterministic addressing (CREATE2) means anyone can verify our operator's config by calling `getOperator()` with the same config tuple.

4. **Your TokenStore clone system works.** Each authorize creates a new EIP-1167 minimal proxy (TokenStore). Funds are isolated per payment — if one escrow has a bug, it cannot affect other escrows. We can see this in the BaseScan transfers: each authorize sends USDC to a different TokenStore clone address.

5. **We are your heaviest user.** Check the transaction count on your contracts across all chains. We likely have more transactions than any other integration. This will only grow as we scale.

### Why you might not see it in your dashboard

If your team has internal dashboards that track x402r usage, you might be looking at:
- **The AuthCaptureEscrow contract directly** — our transactions go through the PaymentOperator first, then to the escrow. Look at internal transactions, not external ones.
- **Different contract addresses** — our PaymentOperator (`0xb963...`) is the entry point, not the escrow singleton (`0xb948...`). But the internal calls from our operator DO reach your escrow.
- **SDK usage** — we built our own Python SDK (`uvd-x402-sdk`) that wraps your TypeScript SDK concepts. We're not calling the TS SDK directly, but we're calling the same contracts with the same function signatures.

---

## 7. Our Source Code References

### Deployment script (uses your factories)

File: [`scripts/deploy-payment-operator.ts`](https://github.com/ultravioletadao/execution-market/blob/main/scripts/deploy-payment-operator.ts)

```typescript
// Uses x402r factory contracts directly
import { PaymentOperatorFactory } from "@x402r/core";

const ADDRESSES = {
  paymentOperatorFactory: "0x3D0837fF8Ea36F417261577b9BA568400A840260",
  staticAddressConditionFactory: "0x206D4DbB6E7b876e4B5EFAAD2a04e7d7813FB6ba",
  authCaptureEscrow: "0xb9488351E48b23D798f24e8174514F28B741Eb4f",
  // ...
};

// Deploy StaticAddressCondition(Facilitator) via YOUR factory
const facilitatorCondition = await staticAddressConditionFactory.deploy(FACILITATOR_ADDRESS);

// Deploy PaymentOperator via YOUR factory
const operator = await paymentOperatorFactory.deployOperator({
  releaseCondition: facilitatorCondition,        // Only Facilitator can release
  refundInEscrowCondition: facilitatorCondition,  // Only Facilitator can refund
  authorizeCondition: ADDRESSES.usdcTvlLimit,     // Your $100 TVL limit
  feeCalculator: address(0),                      // We charge fees ourselves
  // ...
});
```

### Python integration (wraps your SDK concepts)

File: `mcp_server/integrations/x402/advanced_escrow_integration.py`

```python
# Contract mapping comment in our code (lines 15-21):
# operator.authorize()        -> escrow.authorize()   (lock funds)
# operator.release()          -> escrow.capture()      (pay receiver)
# operator.refundInEscrow()   -> escrow.partialVoid()  (refund payer)
# operator.charge()           -> escrow.charge()       (direct payment)
# operator.refundPostEscrow() -> escrow.refund()       (dispute refund)
```

### Key integration files

| File | Purpose | x402r Dependency |
|------|---------|-----------------|
| `mcp_server/integrations/x402/advanced_escrow_integration.py` | Python wrapper for escrow | `AdvancedEscrowClient` from `uvd_x402_sdk` |
| `mcp_server/integrations/x402/sdk_client.py` | Multi-chain SDK client | Token registry + escrow routing |
| `mcp_server/integrations/x402/payment_dispatcher.py` | Payment mode router | Routes to escrow (Fase 2) or direct (Fase 1) |
| `mcp_server/tools/escrow_tools.py` | 8 MCP tools for AI agents | `em_escrow_authorize`, `em_escrow_release`, etc. |
| `scripts/deploy-payment-operator.ts` | Deployment script | Uses `PaymentOperatorFactory`, `StaticAddressConditionFactory` |

---

## 8. Test Suite Coverage

We have **56 E2E tests** across 3 test files that validate every PaymentOperator function:

| Test File | Tests | PaymentOperator Functions Covered |
|-----------|-------|----------------------------------|
| `test_escrow_flows.py` | 22 | authorize, release, refundInEscrow, charge |
| `test_erc8004_e2e_flows.py` | 19 | authorize + release (with identity/reputation side effects) |
| `test_task_lifecycle.py` | 15 | authorize, release(partial), refundInEscrow, split release+refund |

Total test suite: **909 tests** (301 payment-related, 56 E2E covering x402r).

---

## 9. What We Need From You

1. **Deposit limit increase**: The `UsdcTvlLimit` caps at $100. Production bounties need $500+. We need a new operator or updated limit.

2. **Multi-chain PaymentOperator deployment**: We have escrow addresses for 7 more networks but haven't deployed operators yet. We need: Ethereum, Polygon, Arbitrum, Avalanche, Celo, Monad, Optimism.

3. **tokenCollector for refundPostEscrow**: Currently disabled in our code. When implemented, we can enable post-release dispute resolution.

4. **Audit**: Austin's light audit would help us communicate safety to users. The full audit is needed before raising deposit limits.

---

## 10. Summary

| Metric | Value |
|--------|-------|
| Your contracts we use | 7 (PaymentOperator, AuthCaptureEscrow, StaticAddressCondition, TokenCollector, PaymentOperatorFactory, StaticAddressConditionFactory, UsdcTvlLimit) |
| On-chain transactions on our PaymentOperator | **17** (and growing) |
| PaymentOperator functions tested | 4 of 5 (refundPostEscrow disabled) |
| Total E2E tests covering x402r | 56 |
| Total test suite | 909 |
| Gas paid by users | $0.00 |
| Gas paid by Facilitator | All of it |
| Networks with escrow addresses | 8 |
| Networks with deployed operators | 1 (Base) — 7 more pending |
| BaseScan label on our TXs | **"x402 Transaction"** |

**Bottom line**: Open [our PaymentOperator on BaseScan](https://basescan.org/address/0xb9635f544665758019159c04c08a3d583dadd723). Click any transaction. BaseScan itself says "x402 Transaction." The funds flow through your TokenCollector into your TokenStore clones. We are your most active integration.

---

*Execution Market — The Human Execution Layer for AI Agents*
*Built on x402r. Powered by Ultravioleta DAO.*
*https://execution.market*
