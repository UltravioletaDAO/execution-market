# Multichain Golden Flow Report

> **Date**: 2026-02-21 17:45 UTC
> **API**: `https://api.execution.market`
> **Fee Model**: credit_card (fee deducted from bounty on-chain)
> **Escrow Mode**: direct_release (Fase 5, 1-TX release)
> **Chains tested**: 8
> **Result**: **FAIL**

---

## Executive Summary

Tested the complete Execution Market lifecycle across **8 blockchains** 
using the Fase 5 credit card model. 7/8 chains passed.

**Overall Result: FAIL**

| Metric | Value |
|--------|-------|
| Bounty per chain | $0.10 USDC |
| Worker net (87%) | $0.087000 USDC |
| Fee (13%) | $0.013000 USDC |
| Total cost | $0.80 USDC |
| Total on-chain TXs | 15 |
| Reputation | PASS |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Base** | 8453 | **PASS** | [View](https://basescan.org/tx/0xe68c838badc1a6f5778eb05ac534eda0524e1047aff0abf6521fdbdb050acd6c) | [View](https://basescan.org/tx/0x3859f52cea557d0f537f4196cb7133b7f4ea2568e1a1a58a25d70ff222b07cf4) | $0.087000 | 30.29s |
| **Polygon** | 137 | **PASS** | [View](https://polygonscan.com/tx/0x9b9b6f6d826740fc68ab1cfe1e804e8db30331fc1be7c9c7ca33d2ef2bb76872) | [View](https://polygonscan.com/tx/0xdaf95fb09f391aff589532efb8d96fa5a94a6d8936db622009a8a3b70a110662) | $0.087000 | 51.06s |
| **Arbitrum** | 42161 | **PASS** | [View](https://arbiscan.io/tx/0xf1e202041acdaa5f2a83e927524cac05434d4c69bc2b019844a349a7b4e0d61a) | [View](https://arbiscan.io/tx/0xf903b0c5b4ae1d1f2cfddb8d3ecd6f2cb8c38fab45ca5d8be26617bc73ba4508) | $0.087000 | 53.83s |
| **Avalanche** | 43114 | **PASS** | [View](https://snowtrace.io/tx/0xaf969449b8cd89eb3e8bd2913087bd5cd1a3cfe6b6b04a6648860365b80ebdec) | [View](https://snowtrace.io/tx/0xbfa7afc02e8e1927ba17108bd763a08fb2b64f43214c5b810a40b969dcdc3029) | $0.087000 | 36.17s |
| **Monad** | 143 | **PASS** | [View](https://explorer.monad.xyz/tx/0xa7090e185a9307bd4607761689919685361b130dbee60dc180c72dd053d88d3d) | [View](https://explorer.monad.xyz/tx/0xcc3c488670a73143ea49f1c6930826cfacca173e53ce5af2382dc8b4b83dad11) | $0.087000 | 51.95s |
| **Celo** | 42220 | **PASS** | [View](https://celoscan.io/tx/0x7554345593e3e2230f89f3b1cbfe3c9b056284f7e5afa2853186e2026bfda3d0) | [View](https://celoscan.io/tx/0x4ab35359412e8d0968e24bcbc46e8d5c559d3d100111f0055271e45f82f2a3f4) | $0.087000 | 53.83s |
| **Optimism** | 10 | **PASS** | [View](https://optimistic.etherscan.io/tx/0xbdfa49f5e9c7359ecf4545e28514c48d019045632527d620fb8453782cb7a6e3) | [View](https://optimistic.etherscan.io/tx/0x077fd1f3df73dd944fd2cb0cea8a34686ca5c22c65ea7072b932be9df029032a) | $0.087000 | 39.53s |
| **Ethereum** | 1 | **FAIL** | [View](https://etherscan.io/tx/0x3ca2354904351a8f5a751da0d03bdc0a2342189de12c1eeceb420a1ea0cbefcd) | N/A | N/A | 984.34s |

---

### Base (chain 8453)

- **Status**: PASS
- **Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- **USDC**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Task ID**: `60206fa2-65d4-4184-ac67-acfda3382f6d`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xe68c838badc1a6f577...`](https://basescan.org/tx/0xe68c838badc1a6f5778eb05ac534eda0524e1047aff0abf6521fdbdb050acd6c)
- TX 2: [`0x3859f52cea557d0f53...`](https://basescan.org/tx/0x3859f52cea557d0f537f4196cb7133b7f4ea2568e1a1a58a25d70ff222b07cf4)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Polygon (chain 137)

- **Status**: PASS
- **Operator**: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
- **USDC**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Task ID**: `2e3f8fe3-0775-4f71-b06a-cc9806ff64c8`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x9b9b6f6d826740fc68...`](https://polygonscan.com/tx/0x9b9b6f6d826740fc68ab1cfe1e804e8db30331fc1be7c9c7ca33d2ef2bb76872)
- TX 2: [`0xdaf95fb09f391aff58...`](https://polygonscan.com/tx/0xdaf95fb09f391aff589532efb8d96fa5a94a6d8936db622009a8a3b70a110662)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Arbitrum (chain 42161)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- **Task ID**: `b9e3f2c9-9c25-4b14-94d0-19b802149708`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xf1e202041acdaa5f2a...`](https://arbiscan.io/tx/0xf1e202041acdaa5f2a83e927524cac05434d4c69bc2b019844a349a7b4e0d61a)
- TX 2: [`0xf903b0c5b4ae1d1f2c...`](https://arbiscan.io/tx/0xf903b0c5b4ae1d1f2cfddb8d3ecd6f2cb8c38fab45ca5d8be26617bc73ba4508)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Avalanche (chain 43114)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **Task ID**: `f1bb9634-227a-4b54-a3d2-f27e0f7eafe8`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xaf969449b8cd89eb3e...`](https://snowtrace.io/tx/0xaf969449b8cd89eb3e8bd2913087bd5cd1a3cfe6b6b04a6648860365b80ebdec)
- TX 2: [`0xbfa7afc02e8e1927ba...`](https://snowtrace.io/tx/0xbfa7afc02e8e1927ba17108bd763a08fb2b64f43214c5b810a40b969dcdc3029)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Monad (chain 143)

- **Status**: PASS
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Task ID**: `c83e99d5-2dd7-4a99-8da4-164f4cebd05b`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xa7090e185a9307bd46...`](https://explorer.monad.xyz/tx/0xa7090e185a9307bd4607761689919685361b130dbee60dc180c72dd053d88d3d)
- TX 2: [`0xcc3c488670a73143ea...`](https://explorer.monad.xyz/tx/0xcc3c488670a73143ea49f1c6930826cfacca173e53ce5af2382dc8b4b83dad11)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Celo (chain 42220)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`
- **Task ID**: `4ba7034d-198f-4753-a2c5-de8ede27fd39`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x7554345593e3e2230f...`](https://celoscan.io/tx/0x7554345593e3e2230f89f3b1cbfe3c9b056284f7e5afa2853186e2026bfda3d0)
- TX 2: [`0x4ab35359412e8d0968...`](https://celoscan.io/tx/0x4ab35359412e8d0968e24bcbc46e8d5c559d3d100111f0055271e45f82f2a3f4)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Optimism (chain 10)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
- **Task ID**: `2c2d81d1-7613-4b2b-a65b-943dd725be63`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xbdfa49f5e9c7359ecf...`](https://optimistic.etherscan.io/tx/0xbdfa49f5e9c7359ecf4545e28514c48d019045632527d620fb8453782cb7a6e3)
- TX 2: [`0x077fd1f3df73dd944f...`](https://optimistic.etherscan.io/tx/0x077fd1f3df73dd944fd2cb0cea8a34686ca5c22c65ea7072b932be9df029032a)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Ethereum (chain 1)

- **Status**: FAIL
- **Operator**: `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b`
- **USDC**: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
- **Error**: Approval failed: HTTP 502 - Could not settle payment before approval: Escrow release failed: The read operation timed out
- **Task ID**: `db756d20-fa1c-403e-8b8a-9f0ff48afdf7`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | FAIL |

**Transactions:**
- TX 1: [`0x3ca2354904351a8f5a...`](https://etherscan.io/tx/0x3ca2354904351a8f5a751da0d03bdc0a2342189de12c1eeceb420a1ea0cbefcd)

---

## Invariants Verified

- [x] Base: Full lifecycle (create -> escrow -> release -> verify)
- [x] Polygon: Full lifecycle (create -> escrow -> release -> verify)
- [x] Arbitrum: Full lifecycle (create -> escrow -> release -> verify)
- [x] Avalanche: Full lifecycle (create -> escrow -> release -> verify)
- [x] Monad: Full lifecycle (create -> escrow -> release -> verify)
- [x] Celo: Full lifecycle (create -> escrow -> release -> verify)
- [x] Optimism: Full lifecycle (create -> escrow -> release -> verify)
- [ ] Ethereum: Failed (Approval failed: HTTP 502 - Could not settle payment before approval: Escrow release failed: The read operation timed out)
- [x] Bidirectional reputation (agent<->worker) on Base

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
