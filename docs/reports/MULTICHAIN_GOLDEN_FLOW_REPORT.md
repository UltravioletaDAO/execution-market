# Multichain Golden Flow Report

> **Date**: 2026-02-21 17:30 UTC
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
| Reputation | PASS |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Base** | 8453 | **PASS** | [View](https://basescan.org/tx/0xa81e616946161730329fe3664696d08fbc72770ede3db69a0df3a24ac14be2e8) | [View](https://basescan.org/tx/0x3fa49dc37e2636008871a7728c17af11abaeb0e562430c5780150a2df8cb2f0b) | $0.087000 | 34.12s |
| **Polygon** | 137 | **PASS** | [View](https://polygonscan.com/tx/0x58693d7e78db239602fd354c7174b043a071e93fc2319edcb00b1940c2a8e54b) | [View](https://polygonscan.com/tx/0x762b6cd8f0482f300991a8506f34a90a1117d7a755d91828d11171dbf2a610b0) | $0.087000 | 51.32s |
| **Arbitrum** | 42161 | **PASS** | [View](https://arbiscan.io/tx/0xa90224ad45e9e5491fddc27e0e3ae9d9d6ba6a7c265b73a0b38352bb7feba366) | [View](https://arbiscan.io/tx/0xd74ba628f751ea6d00061f11bb158829f4a346bd451853d93184038805c1b270) | $0.087000 | 57.69s |
| **Avalanche** | 43114 | **PASS** | [View](https://snowtrace.io/tx/0x08d48dff6efe700ab63c52db456e2d1e170bb9b2f341c2b2ae3c9cf4ee4e3d04) | [View](https://snowtrace.io/tx/0xe3e090e83dae86fd93f73cfcf39934e4dc8dc7bce2984886654e51b6d0d984b0) | $0.087000 | 39.29s |
| **Monad** | 143 | **PASS** | [View](https://explorer.monad.xyz/tx/0xeb15d01d749c1438c47fa96526035018f28f79119a489ec919aed258e19dec98) | [View](https://explorer.monad.xyz/tx/0xa719ec90ba76f9df04a19c8de4528ba13041ad8cd99dfa3270b1e130e0372ed9) | $0.087000 | 59.04s |
| **Celo** | 42220 | **PASS** | [View](https://celoscan.io/tx/0x724afc55ff72b0ad9fecff8fc230fd7cbb7e0615b64bfa7e20666b853d8eb50a) | [View](https://celoscan.io/tx/0xbcf4b513fb0d67d475868d1e9d94c1f443c5f2381637b72bbb7619d39612ec14) | $0.087000 | 43.85s |
| **Optimism** | 10 | **PASS** | [View](https://optimistic.etherscan.io/tx/0x23b06ad40030c1668b52ba004fec5b9acc6448822847e2807af3b6eb9025cee8) | [View](https://optimistic.etherscan.io/tx/0xa9adfac5844dc818157f523c1efccec44f31fc6695e95f07b68cc2cd3a796898) | $0.087000 | 28.34s |

---

### Base (chain 8453)

- **Status**: PASS
- **Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- **USDC**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Task ID**: `d28c28e8-728d-40d9-ad56-2cc1bd1719d7`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xa81e61694616173032...`](https://basescan.org/tx/0xa81e616946161730329fe3664696d08fbc72770ede3db69a0df3a24ac14be2e8)
- TX 2: [`0x3fa49dc37e26360088...`](https://basescan.org/tx/0x3fa49dc37e2636008871a7728c17af11abaeb0e562430c5780150a2df8cb2f0b)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Polygon (chain 137)

- **Status**: PASS
- **Operator**: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
- **USDC**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Task ID**: `9fffbba4-ac4d-4052-97ca-77df711dca7c`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x58693d7e78db239602...`](https://polygonscan.com/tx/0x58693d7e78db239602fd354c7174b043a071e93fc2319edcb00b1940c2a8e54b)
- TX 2: [`0x762b6cd8f0482f3009...`](https://polygonscan.com/tx/0x762b6cd8f0482f300991a8506f34a90a1117d7a755d91828d11171dbf2a610b0)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Arbitrum (chain 42161)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- **Task ID**: `78f496a0-55c1-4f66-9dc8-2f85d6a0c1e8`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xa90224ad45e9e5491f...`](https://arbiscan.io/tx/0xa90224ad45e9e5491fddc27e0e3ae9d9d6ba6a7c265b73a0b38352bb7feba366)
- TX 2: [`0xd74ba628f751ea6d00...`](https://arbiscan.io/tx/0xd74ba628f751ea6d00061f11bb158829f4a346bd451853d93184038805c1b270)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Avalanche (chain 43114)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **Task ID**: `5a2e851d-476d-4d63-8d51-f60f859740a9`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x08d48dff6efe700ab6...`](https://snowtrace.io/tx/0x08d48dff6efe700ab63c52db456e2d1e170bb9b2f341c2b2ae3c9cf4ee4e3d04)
- TX 2: [`0xe3e090e83dae86fd93...`](https://snowtrace.io/tx/0xe3e090e83dae86fd93f73cfcf39934e4dc8dc7bce2984886654e51b6d0d984b0)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Monad (chain 143)

- **Status**: PASS
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Task ID**: `e06d8c8f-3d09-4278-94db-0157a740e5e2`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xeb15d01d749c1438c4...`](https://explorer.monad.xyz/tx/0xeb15d01d749c1438c47fa96526035018f28f79119a489ec919aed258e19dec98)
- TX 2: [`0xa719ec90ba76f9df04...`](https://explorer.monad.xyz/tx/0xa719ec90ba76f9df04a19c8de4528ba13041ad8cd99dfa3270b1e130e0372ed9)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Celo (chain 42220)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`
- **Task ID**: `4cfaf2f3-7185-480b-a8cc-b777a61cab79`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x724afc55ff72b0ad9f...`](https://celoscan.io/tx/0x724afc55ff72b0ad9fecff8fc230fd7cbb7e0615b64bfa7e20666b853d8eb50a)
- TX 2: [`0xbcf4b513fb0d67d475...`](https://celoscan.io/tx/0xbcf4b513fb0d67d475868d1e9d94c1f443c5f2381637b72bbb7619d39612ec14)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Optimism (chain 10)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
- **Task ID**: `ec8f4770-15c8-4e46-9250-3fe1e9248e66`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x23b06ad40030c1668b...`](https://optimistic.etherscan.io/tx/0x23b06ad40030c1668b52ba004fec5b9acc6448822847e2807af3b6eb9025cee8)
- TX 2: [`0xa9adfac5844dc81815...`](https://optimistic.etherscan.io/tx/0xa9adfac5844dc818157f523c1efccec44f31fc6695e95f07b68cc2cd3a796898)

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
- [x] Bidirectional reputation (agent<->worker) on Base

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
