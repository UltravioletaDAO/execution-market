# Multichain Golden Flow Report

> **Date**: 2026-02-20 20:13 UTC
> **API**: `https://api.execution.market`
> **Fee Model**: credit_card (fee deducted from bounty on-chain)
> **Escrow Mode**: direct_release (Fase 5, 1-TX release)
> **Chains tested**: 7
> **Result**: **PASS**

---

## Executive Summary

Tested the complete Execution Market lifecycle across **7 blockchains** 
using the Fase 5 credit card model. 7/7 chains passed.

**Overall Result: PASS**

| Metric | Value |
|--------|-------|
| Bounty per chain | $0.10 USDC |
| Worker net (87%) | $0.087000 USDC |
| Fee (13%) | $0.013000 USDC |
| Total cost | $0.70 USDC |
| Total on-chain TXs | 14 |
| Reputation | PARTIAL |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Base** | 8453 | **PASS** | [View](https://basescan.org/tx/0x484593ce95e12421753a36469bc3b1f624416603eed8299af6e730404ae1ec8d) | [View](https://basescan.org/tx/0xcaf6b4ed10cc77fa543ca8031ebddf2d5b1f9fa8b2fe737a7c2be412e66a67ea) | $0.087000 | 29.12s |
| **Polygon** | 137 | **PASS** | [View](https://polygonscan.com/tx/0xaf889084dfd5b73b3a8b57d213a95c09e21a8c672cb6bd852f39761b6739cc2c) | [View](https://polygonscan.com/tx/0xd9236abca08c5d017a7b0e51dfd847d47df25fb206300f47b6daebaf857acf36) | $0.087000 | 43.91s |
| **Arbitrum** | 42161 | **PASS** | [View](https://arbiscan.io/tx/0x305062d9fa6c1d53e8cdd6c8854c0a93e20cc032f13da53eb6cdbe6e7031c3ec) | [View](https://arbiscan.io/tx/0xc04bc5edc695f6ccd0cc3af7b5095d89fe2efea2d0e8723bd3f9d3ceeb15888d) | $0.087000 | 49.73s |
| **Avalanche** | 43114 | **PASS** | [View](https://snowtrace.io/tx/0x870a77e86abd5132cfea2a76c2a8e168bceb115ceaf089cbcef2e5c151784ce3) | [View](https://snowtrace.io/tx/0xbe81636a22062d9386e2902fd1db3211431883945b91da0090fa2b04659bcf3f) | $0.087000 | 40.35s |
| **Monad** | 143 | **PASS** | [View](https://explorer.monad.xyz/tx/0xaeb4658dbf7678b952034a5f5ea3daecef20993ce29e89b6dd1aa8e6b75fab89) | [View](https://explorer.monad.xyz/tx/0x3c38056a1eac9bf6cc4d38185f007ee72148f60559cf7c298df200950996e9dd) | $0.087000 | 50.1s |
| **Celo** | 42220 | **PASS** | [View](https://celoscan.io/tx/0x55263f8d72198e901d28595feb86ab94eda117e63ac38ca912e5f2522188622d) | [View](https://celoscan.io/tx/0xe08700c201c5ad1f4744551d11d1fc508d0becefb037fde0b9bd339e36999e63) | $0.087000 | 40.53s |
| **Optimism** | 10 | **PASS** | [View](https://optimistic.etherscan.io/tx/0x23a29894e48129358819d22515c055376d6cca1aa46fd83febd6c2e398a929f4) | [View](https://optimistic.etherscan.io/tx/0x08796a7395cab8b338cfe8c26fb51d3ffc495f44abf0df1baebcd0d4c0c611a9) | $0.087000 | 44.46s |

---

### Base (chain 8453)

- **Status**: PASS
- **Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- **USDC**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Task ID**: `1049710b-4223-44f2-b4e2-b5453e7f61b8`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x484593ce95e1242175...`](https://basescan.org/tx/0x484593ce95e12421753a36469bc3b1f624416603eed8299af6e730404ae1ec8d)
- TX 2: [`0xcaf6b4ed10cc77fa54...`](https://basescan.org/tx/0xcaf6b4ed10cc77fa543ca8031ebddf2d5b1f9fa8b2fe737a7c2be412e66a67ea)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Polygon (chain 137)

- **Status**: PASS
- **Operator**: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
- **USDC**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Task ID**: `26af2fd6-b439-4db9-8c0d-d8c6ca82beff`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xaf889084dfd5b73b3a...`](https://polygonscan.com/tx/0xaf889084dfd5b73b3a8b57d213a95c09e21a8c672cb6bd852f39761b6739cc2c)
- TX 2: [`0xd9236abca08c5d017a...`](https://polygonscan.com/tx/0xd9236abca08c5d017a7b0e51dfd847d47df25fb206300f47b6daebaf857acf36)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Arbitrum (chain 42161)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- **Task ID**: `6dd585ef-1d3e-4b85-9e9f-b7bbe99de114`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x305062d9fa6c1d53e8...`](https://arbiscan.io/tx/0x305062d9fa6c1d53e8cdd6c8854c0a93e20cc032f13da53eb6cdbe6e7031c3ec)
- TX 2: [`0xc04bc5edc695f6ccd0...`](https://arbiscan.io/tx/0xc04bc5edc695f6ccd0cc3af7b5095d89fe2efea2d0e8723bd3f9d3ceeb15888d)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Avalanche (chain 43114)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **Task ID**: `165f65a1-be73-49b7-a73f-27ca3ee25ea1`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x870a77e86abd5132cf...`](https://snowtrace.io/tx/0x870a77e86abd5132cfea2a76c2a8e168bceb115ceaf089cbcef2e5c151784ce3)
- TX 2: [`0xbe81636a22062d9386...`](https://snowtrace.io/tx/0xbe81636a22062d9386e2902fd1db3211431883945b91da0090fa2b04659bcf3f)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Monad (chain 143)

- **Status**: PASS
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Task ID**: `39d204e8-0162-4989-9ab1-f1cdbed9e4b7`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xaeb4658dbf7678b952...`](https://explorer.monad.xyz/tx/0xaeb4658dbf7678b952034a5f5ea3daecef20993ce29e89b6dd1aa8e6b75fab89)
- TX 2: [`0x3c38056a1eac9bf6cc...`](https://explorer.monad.xyz/tx/0x3c38056a1eac9bf6cc4d38185f007ee72148f60559cf7c298df200950996e9dd)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Celo (chain 42220)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`
- **Task ID**: `c1e0e607-9e7b-4734-a9da-a73ade83592d`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x55263f8d72198e901d...`](https://celoscan.io/tx/0x55263f8d72198e901d28595feb86ab94eda117e63ac38ca912e5f2522188622d)
- TX 2: [`0xe08700c201c5ad1f47...`](https://celoscan.io/tx/0xe08700c201c5ad1f4744551d11d1fc508d0becefb037fde0b9bd339e36999e63)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Optimism (chain 10)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
- **Task ID**: `35b91ab2-7a09-402e-9b4e-89a16e34a666`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x23a29894e481293588...`](https://optimistic.etherscan.io/tx/0x23a29894e48129358819d22515c055376d6cca1aa46fd83febd6c2e398a929f4)
- TX 2: [`0x08796a7395cab8b338...`](https://optimistic.etherscan.io/tx/0x08796a7395cab8b338cfe8c26fb51d3ffc495f44abf0df1baebcd0d4c0c611a9)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

---

## Invariants Verified

- [x] Base: Full lifecycle (create -> escrow -> release -> verify)
- [x] Polygon: Full lifecycle (create -> escrow -> release -> verify)
- [x] Arbitrum: Full lifecycle (create -> escrow -> release -> verify)
- [x] Avalanche: Full lifecycle (create -> escrow -> release -> verify)
- [x] Monad: Full lifecycle (create -> escrow -> release -> verify)
- [x] Celo: Full lifecycle (create -> escrow -> release -> verify)
- [x] Optimism: Full lifecycle (create -> escrow -> release -> verify)
- [~] Reputation: partial (one direction only)

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
