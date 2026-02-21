# Multichain Golden Flow Report

> **Date**: 2026-02-21 01:19 UTC
> **API**: `https://api.execution.market`
> **Fee Model**: credit_card (fee deducted from bounty on-chain)
> **Escrow Mode**: direct_release (Fase 5, 1-TX release)
> **Chains tested**: 8
> **Result**: **FAIL**

---

## Executive Summary

Tested the complete Execution Market lifecycle across **8 blockchains** 
using the Fase 5 credit card model. 6/8 chains passed.

**Overall Result: FAIL**

| Metric | Value |
|--------|-------|
| Bounty per chain | $0.10 USDC |
| Worker net (87%) | $0.087000 USDC |
| Fee (13%) | $0.013000 USDC |
| Total cost | $0.80 USDC |
| Total on-chain TXs | 13 |
| Reputation | PARTIAL |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Base** | 8453 | **PASS** | [View](https://basescan.org/tx/0x10790298e9153f7e3338f958a787520de3461d5a18904b7d58b3bc45cf7a373a) | [View](https://basescan.org/tx/0xa084af11c5bac4e503c80a8547d849c00c8214405e5cc7b32f6375a9cee1d043) | N/A | 23.67s |
| **Polygon** | 137 | **PASS** | [View](https://polygonscan.com/tx/0x630827b31281d6b53cbe0ad6f1a3c42f6a31d6afdb40ea2f0044ef8af784bad8) | [View](https://polygonscan.com/tx/0x7aa3b3dad79429102f9de4b9bfe1c410cb7fd195d8309d2b661cf5566bf819fe) | N/A | 47.72s |
| **Arbitrum** | 42161 | **PASS** | [View](https://arbiscan.io/tx/0x24b1f03301aa7faa6000184e63f494746a7408acd93b06f6917414dfd7fd0f65) | [View](https://arbiscan.io/tx/0xeeec542ad0c3caa5482b7a9d5638ca428788f20fd724d9bffadc30acd7f2076a) | N/A | 50.32s |
| **Avalanche** | 43114 | **FAIL** | [View](https://snowtrace.io/tx/0x512028b0bcb015f4934999192fd504cbdde84954d214fa34cf676e4a496fd935) | N/A | N/A | 19.24s |
| **Monad** | 143 | **PASS** | [View](https://explorer.monad.xyz/tx/0x7c747695ccb7c76a2d612a84cb78631987c897119332ad626b0ee89e4e90c7d8) | [View](https://explorer.monad.xyz/tx/0xa3f0de7e5c2ae8beeb02a65e8159453744763f3122a44f7d1c4b366d70535fa5) | N/A | 42.03s |
| **Celo** | 42220 | **PASS** | [View](https://celoscan.io/tx/0x6e33c0953eefa7193c3bf35d33a7b6acb4ebaa15488454e515652c129f5ac136) | [View](https://celoscan.io/tx/0x61d8e7cee6a74b01a7d3b63075a6265714dd615b0b223e265d8a4b9ba9efdf85) | N/A | 48.12s |
| **Optimism** | 10 | **PASS** | [View](https://optimistic.etherscan.io/tx/0xc9ffa7bb46e7cfc338e7cd5890fb51c731b0657ef7ddeac135eea743027e1530) | [View](https://optimistic.etherscan.io/tx/0xa9ea07e24c7e1eb877baf4f599d7228229334248a2aaa59e4be36873920855f2) | N/A | 28.37s |
| **Ethereum** | 1 | **FAIL** | N/A | N/A | N/A | 304.9s |

---

### Base (chain 8453)

- **Status**: PASS
- **Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- **USDC**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Task ID**: `ea88196c-d171-467b-ac07-73e15793c60d`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x10790298e9153f7e33...`](https://basescan.org/tx/0x10790298e9153f7e3338f958a787520de3461d5a18904b7d58b3bc45cf7a373a)
- TX 2: [`0xa084af11c5bac4e503...`](https://basescan.org/tx/0xa084af11c5bac4e503c80a8547d849c00c8214405e5cc7b32f6375a9cee1d043)

### Polygon (chain 137)

- **Status**: PASS
- **Operator**: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
- **USDC**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Task ID**: `bc7b01da-a9b1-4469-8fec-d51c444e5da6`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x630827b31281d6b53c...`](https://polygonscan.com/tx/0x630827b31281d6b53cbe0ad6f1a3c42f6a31d6afdb40ea2f0044ef8af784bad8)
- TX 2: [`0x7aa3b3dad79429102f...`](https://polygonscan.com/tx/0x7aa3b3dad79429102f9de4b9bfe1c410cb7fd195d8309d2b661cf5566bf819fe)

### Arbitrum (chain 42161)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- **Task ID**: `f71b8ded-5387-44cb-87bc-10f2346f2b67`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x24b1f03301aa7faa60...`](https://arbiscan.io/tx/0x24b1f03301aa7faa6000184e63f494746a7408acd93b06f6917414dfd7fd0f65)
- TX 2: [`0xeeec542ad0c3caa548...`](https://arbiscan.io/tx/0xeeec542ad0c3caa5482b7a9d5638ca428788f20fd724d9bffadc30acd7f2076a)

### Avalanche (chain 43114)

- **Status**: FAIL
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **Error**: Approval failed: HTTP 502 - Could not settle payment before approval: Facilitator HTTP 400: {"error":"Contract call failed: ErrorResp(ErrorPayload { code: 3, message: \"execution reverted: FiatTokenV2: invalid signature\", data: Some(RawValue(\"0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001e46696174546f6b656e56323a20696e76616c6964207369676e61747572650000\")) })"}
- **Task ID**: `4ac95838-c586-410b-b67c-cad28bbc7555`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | FAIL |

**Transactions:**
- TX 1: [`0x512028b0bcb015f493...`](https://snowtrace.io/tx/0x512028b0bcb015f4934999192fd504cbdde84954d214fa34cf676e4a496fd935)

### Monad (chain 143)

- **Status**: PASS
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Task ID**: `95b73392-f5c3-4248-96ea-48f80bbba9ee`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x7c747695ccb7c76a2d...`](https://explorer.monad.xyz/tx/0x7c747695ccb7c76a2d612a84cb78631987c897119332ad626b0ee89e4e90c7d8)
- TX 2: [`0xa3f0de7e5c2ae8beeb...`](https://explorer.monad.xyz/tx/0xa3f0de7e5c2ae8beeb02a65e8159453744763f3122a44f7d1c4b366d70535fa5)

### Celo (chain 42220)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`
- **Task ID**: `84f8861d-95a3-4ca5-b5a0-a1000f4a11a8`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x6e33c0953eefa7193c...`](https://celoscan.io/tx/0x6e33c0953eefa7193c3bf35d33a7b6acb4ebaa15488454e515652c129f5ac136)
- TX 2: [`0x61d8e7cee6a74b01a7...`](https://celoscan.io/tx/0x61d8e7cee6a74b01a7d3b63075a6265714dd615b0b223e265d8a4b9ba9efdf85)

### Optimism (chain 10)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
- **Task ID**: `e6f4f24a-4360-4dd6-ba95-62f66dd30670`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xc9ffa7bb46e7cfc338...`](https://optimistic.etherscan.io/tx/0xc9ffa7bb46e7cfc338e7cd5890fb51c731b0657ef7ddeac135eea743027e1530)
- TX 2: [`0xa9ea07e24c7e1eb877...`](https://optimistic.etherscan.io/tx/0xa9ea07e24c7e1eb877baf4f599d7228229334248a2aaa59e4be36873920855f2)

### Ethereum (chain 1)

- **Status**: FAIL
- **Operator**: `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b`
- **USDC**: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
- **Error**: Assign failed: Escrow lock failed during assignment: Escrow authorize failed: The read operation timed out. Task remains published.
- **Task ID**: `1980bba0-1491-4d2b-a86c-86a17b005693`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | FAIL |

---

## Invariants Verified

- [x] Base: Full lifecycle (create -> escrow -> release -> verify)
- [x] Polygon: Full lifecycle (create -> escrow -> release -> verify)
- [x] Arbitrum: Full lifecycle (create -> escrow -> release -> verify)
- [ ] Avalanche: Failed (Approval failed: HTTP 502 - Could not settle payment before approval: Facilitator HTTP 400: {"error":"Contract call failed: ErrorResp(ErrorPayload { code: 3, message: \"execution reverted: FiatTokenV2: invalid signature\", data: Some(RawValue(\"0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001e46696174546f6b656e56323a20696e76616c6964207369676e61747572650000\")) })"})
- [x] Monad: Full lifecycle (create -> escrow -> release -> verify)
- [x] Celo: Full lifecycle (create -> escrow -> release -> verify)
- [x] Optimism: Full lifecycle (create -> escrow -> release -> verify)
- [ ] Ethereum: Failed (Assign failed: Escrow lock failed during assignment: Escrow authorize failed: The read operation timed out. Task remains published.)
- [~] Reputation: partial (one direction only)

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
