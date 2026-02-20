# Multichain Golden Flow Report

> **Date**: 2026-02-20 19:25 UTC
> **API**: `https://api.execution.market`
> **Fee Model**: credit_card (fee deducted from bounty on-chain)
> **Escrow Mode**: direct_release (Fase 5, 1-TX release)
> **Chains tested**: 7
> **Result**: **FAIL**

---

## Executive Summary

Tested the complete Execution Market lifecycle across **7 blockchains** 
using the Fase 5 credit card model. 5/7 chains passed.

**Overall Result: FAIL**

| Metric | Value |
|--------|-------|
| Bounty per chain | $0.10 USDC |
| Worker net (87%) | $0.087000 USDC |
| Fee (13%) | $0.013000 USDC |
| Total cost | $0.70 USDC |
| Total on-chain TXs | 11 |
| Reputation | SKIP |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Base** | 8453 | **PASS** | [View](https://basescan.org/tx/0x911588224312256ae178c637483d1a52fd22b0f86c958ac14d4483edb2b4aee9) | [View](https://basescan.org/tx/0xb465fe66b6c2b302e0a0710d28f59f17b0c8391f890c7db19b2c99c0e97f1b41) | $0.087000 | 42.21s |
| **Polygon** | 137 | **FAIL** | [View](https://polygonscan.com/tx/0x16cc7c093898f2e12ff249b9e2a2f7856c557c8292d2d3122d871f4d899e2e6d) | N/A | N/A | 29.0s |
| **Arbitrum** | 42161 | **PASS** | [View](https://arbiscan.io/tx/0x3ec638ccb7d9a600fe1a73b757b3cb6a8a10320896f9cc0fb33deb88d5e49b1e) | [View](https://arbiscan.io/tx/0xd3bdf5c2cdfba9f0c25a91ed3d0e09be412a0ffd8b7626fa8955f55203138307) | $0.087000 | 52.99s |
| **Avalanche** | 43114 | **PASS** | [View](https://snowtrace.io/tx/0x1ee5a4a2ee6a4241504ad0e4e7ca97d44148aae6cf834e22c5a26e99deefc190) | [View](https://snowtrace.io/tx/0xc8a229ca33d42cb2de8221efd2536ab32bb5de520901c7e9d5ab955ac6fa007c) | $0.087000 | 41.71s |
| **Monad** | 143 | **PASS** | [View](https://explorer.monad.xyz/tx/0xb71dc8abb6901d6b745228769a0e8b5d60e3a9c555ab142cd921319291bc842a) | [View](https://explorer.monad.xyz/tx/0x0d82823686f81e3c882d6fd9e9c4ee03f67e3df458f08e24bb8978b777b925f4) | $0.087000 | 50.29s |
| **Celo** | 42220 | **PASS** | [View](https://celoscan.io/tx/0xdde62451bb4a8b9cce03bd22036d89fa1d4b71b908c7d8a398923090423222bc) | [View](https://celoscan.io/tx/0xe8373658076200e166f0e6ec4734a941d4e9f1e08c65cf3240ace9fa60583141) | $0.087000 | 44.08s |
| **Optimism** | 10 | **FAIL** | N/A | N/A | N/A | 5.2s |

---

### Base (chain 8453)

- **Status**: PASS
- **Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- **USDC**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Task ID**: `1d3820fb-7bd3-403f-a92d-130c69ea1780`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x911588224312256ae1...`](https://basescan.org/tx/0x911588224312256ae178c637483d1a52fd22b0f86c958ac14d4483edb2b4aee9)
- TX 2: [`0xb465fe66b6c2b302e0...`](https://basescan.org/tx/0xb465fe66b6c2b302e0a0710d28f59f17b0c8391f890c7db19b2c99c0e97f1b41)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Polygon (chain 137)

- **Status**: FAIL
- **Operator**: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
- **USDC**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Error**: Approval failed: HTTP 502 - Could not settle payment before approval: Escrow release failed: Escrow scheme error: Contract call failed: ContractCall("TransportError(NullResp)")
- **Task ID**: `1d1d2d7d-8e3c-42ad-bdd4-d21335e6714c`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | FAIL |

**Transactions:**
- TX 1: [`0x16cc7c093898f2e12f...`](https://polygonscan.com/tx/0x16cc7c093898f2e12ff249b9e2a2f7856c557c8292d2d3122d871f4d899e2e6d)

### Arbitrum (chain 42161)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- **Task ID**: `b7bc596b-9a1b-4744-9324-3dd4899f0928`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x3ec638ccb7d9a600fe...`](https://arbiscan.io/tx/0x3ec638ccb7d9a600fe1a73b757b3cb6a8a10320896f9cc0fb33deb88d5e49b1e)
- TX 2: [`0xd3bdf5c2cdfba9f0c2...`](https://arbiscan.io/tx/0xd3bdf5c2cdfba9f0c25a91ed3d0e09be412a0ffd8b7626fa8955f55203138307)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Avalanche (chain 43114)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **Task ID**: `0b4ec810-a5aa-430e-943b-46a901499539`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x1ee5a4a2ee6a424150...`](https://snowtrace.io/tx/0x1ee5a4a2ee6a4241504ad0e4e7ca97d44148aae6cf834e22c5a26e99deefc190)
- TX 2: [`0xc8a229ca33d42cb2de...`](https://snowtrace.io/tx/0xc8a229ca33d42cb2de8221efd2536ab32bb5de520901c7e9d5ab955ac6fa007c)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Monad (chain 143)

- **Status**: PASS
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Task ID**: `e1183cbf-2afc-42b8-8644-55aa3c4ec27d`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xb71dc8abb6901d6b74...`](https://explorer.monad.xyz/tx/0xb71dc8abb6901d6b745228769a0e8b5d60e3a9c555ab142cd921319291bc842a)
- TX 2: [`0x0d82823686f81e3c88...`](https://explorer.monad.xyz/tx/0x0d82823686f81e3c882d6fd9e9c4ee03f67e3df458f08e24bb8978b777b925f4)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Celo (chain 42220)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`
- **Task ID**: `63a16a50-f8f4-443b-80a5-615cf4b9baec`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xdde62451bb4a8b9cce...`](https://celoscan.io/tx/0xdde62451bb4a8b9cce03bd22036d89fa1d4b71b908c7d8a398923090423222bc)
- TX 2: [`0xe8373658076200e166...`](https://celoscan.io/tx/0xe8373658076200e166f0e6ec4734a941d4e9f1e08c65cf3240ace9fa60583141)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Optimism (chain 10)

- **Status**: FAIL
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
- **Error**: Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: PaymentInfo validation failed: token_collector mismatch: client=0x0ddf51e62ddd41b5f67beaf2dce9f2e99e2c5af5, expected=0x230fd3a171750fa45db2976121376b7f47cba308. Task remains published.
- **Task ID**: `d3ef5b42-9e73-4a25-9e44-f35593c57d11`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | FAIL |

---

## Invariants Verified

- [x] Base: Full lifecycle (create -> escrow -> release -> verify)
- [ ] Polygon: Failed (Approval failed: HTTP 502 - Could not settle payment before approval: Escrow release failed: Escrow scheme error: Contract call failed: ContractCall("TransportError(NullResp)"))
- [x] Arbitrum: Full lifecycle (create -> escrow -> release -> verify)
- [x] Avalanche: Full lifecycle (create -> escrow -> release -> verify)
- [x] Monad: Full lifecycle (create -> escrow -> release -> verify)
- [x] Celo: Full lifecycle (create -> escrow -> release -> verify)
- [ ] Optimism: Failed (Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: PaymentInfo validation failed: token_collector mismatch: client=0x0ddf51e62ddd41b5f67beaf2dce9f2e99e2c5af5, expected=0x230fd3a171750fa45db2976121376b7f47cba308. Task remains published.)
- [ ] Reputation: SKIP

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
