# Multichain Golden Flow Report

> **Date**: 2026-02-20 21:16 UTC
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
| Total on-chain TXs | 14 |
| Reputation | PARTIAL |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Base** | 8453 | **PASS** | [View](https://basescan.org/tx/0x3de54e6d3d04a56e12f97a6743bc54cbd583b4bace4a5044fbe24a8efe32d765) | [View](https://basescan.org/tx/0x5bc8be993d926c2a836293f7c7c31329012b4a0490c77cded899fc2436f851de) | $0.087000 | 44.37s |
| **Polygon** | 137 | **PASS** | [View](https://polygonscan.com/tx/0x65143e3898ff023d9ead398164720db4628a6e4bed1fb6af32aadb2f80a29f9b) | [View](https://polygonscan.com/tx/0xf761dedfb9619011417253c90d427e64074be1585d7b9156bb789a1813dcd3b9) | $0.087000 | 43.88s |
| **Arbitrum** | 42161 | **PASS** | [View](https://arbiscan.io/tx/0xa1c8161dfe308a8bf32d151e2cd5238f83840b18b83ed0beef67478a6a9109dc) | [View](https://arbiscan.io/tx/0x3f197d09f085c74230718909e937444e900611ad64643800bda369de45be5930) | $0.087000 | 50.19s |
| **Avalanche** | 43114 | **PASS** | [View](https://snowtrace.io/tx/0x09d7eb0e5b7b4169c8fed2ea40b21a942911bfc15c6729a7b18f59b1f28e70a7) | [View](https://snowtrace.io/tx/0x7b79f94670faff72e35a12f7ec66b3c079cd4a497cae2d7eba37609088c486cc) | $0.087000 | 41.01s |
| **Monad** | 143 | **PASS** | [View](https://explorer.monad.xyz/tx/0x7e9f51454046bdf7cfdec1970d8372c2fddbc19db1c47b005ff3beeb7f4160c3) | [View](https://explorer.monad.xyz/tx/0x00700af53410089ead5953f581a60ee825b2e4ad95062db52486ccd3fbcdc7fa) | $0.087000 | 50.71s |
| **Celo** | 42220 | **PASS** | [View](https://celoscan.io/tx/0x78c75f4b6a215c1d5f621bc055703094b262a45985525b160ddddcce589ac716) | [View](https://celoscan.io/tx/0x0f7e3e67b1c6b40b01e7b859cb6111ca8fcd56e75a85cd2153e621dfd1e65a72) | $0.087000 | 54.14s |
| **Optimism** | 10 | **PASS** | [View](https://optimistic.etherscan.io/tx/0x1179ee3f92241c55f6fff436b91849a9b94cf78cdc8c45d3ec9f65eeea18b5f8) | [View](https://optimistic.etherscan.io/tx/0x825ebd374024b65d9f482eb544ec63782db7ac4ee66d3122a54422761202d2a9) | $0.087000 | 72.38s |
| **Ethereum** | 1 | **FAIL** | N/A | N/A | N/A | 67.28s |

---

### Base (chain 8453)

- **Status**: PASS
- **Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- **USDC**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Task ID**: `157b1744-4268-4fb6-97cd-ab6e25d8cf3e`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x3de54e6d3d04a56e12...`](https://basescan.org/tx/0x3de54e6d3d04a56e12f97a6743bc54cbd583b4bace4a5044fbe24a8efe32d765)
- TX 2: [`0x5bc8be993d926c2a83...`](https://basescan.org/tx/0x5bc8be993d926c2a836293f7c7c31329012b4a0490c77cded899fc2436f851de)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Polygon (chain 137)

- **Status**: PASS
- **Operator**: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
- **USDC**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Task ID**: `20380b6e-b3c5-4acc-a0e6-837c7c469ef3`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x65143e3898ff023d9e...`](https://polygonscan.com/tx/0x65143e3898ff023d9ead398164720db4628a6e4bed1fb6af32aadb2f80a29f9b)
- TX 2: [`0xf761dedfb961901141...`](https://polygonscan.com/tx/0xf761dedfb9619011417253c90d427e64074be1585d7b9156bb789a1813dcd3b9)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Arbitrum (chain 42161)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- **Task ID**: `e8d36125-15a1-4d75-8477-961aacb5145d`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xa1c8161dfe308a8bf3...`](https://arbiscan.io/tx/0xa1c8161dfe308a8bf32d151e2cd5238f83840b18b83ed0beef67478a6a9109dc)
- TX 2: [`0x3f197d09f085c74230...`](https://arbiscan.io/tx/0x3f197d09f085c74230718909e937444e900611ad64643800bda369de45be5930)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Avalanche (chain 43114)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **Task ID**: `b6a6346e-513e-46e7-8230-38ccb5f2c7d5`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x09d7eb0e5b7b4169c8...`](https://snowtrace.io/tx/0x09d7eb0e5b7b4169c8fed2ea40b21a942911bfc15c6729a7b18f59b1f28e70a7)
- TX 2: [`0x7b79f94670faff72e3...`](https://snowtrace.io/tx/0x7b79f94670faff72e35a12f7ec66b3c079cd4a497cae2d7eba37609088c486cc)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Monad (chain 143)

- **Status**: PASS
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Task ID**: `1b7e2b51-b7dd-4db7-85c3-693ecd3fffb7`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x7e9f51454046bdf7cf...`](https://explorer.monad.xyz/tx/0x7e9f51454046bdf7cfdec1970d8372c2fddbc19db1c47b005ff3beeb7f4160c3)
- TX 2: [`0x00700af53410089ead...`](https://explorer.monad.xyz/tx/0x00700af53410089ead5953f581a60ee825b2e4ad95062db52486ccd3fbcdc7fa)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Celo (chain 42220)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`
- **Task ID**: `b67475d7-06b6-49a4-b986-066776b619fc`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x78c75f4b6a215c1d5f...`](https://celoscan.io/tx/0x78c75f4b6a215c1d5f621bc055703094b262a45985525b160ddddcce589ac716)
- TX 2: [`0x0f7e3e67b1c6b40b01...`](https://celoscan.io/tx/0x0f7e3e67b1c6b40b01e7b859cb6111ca8fcd56e75a85cd2153e621dfd1e65a72)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Optimism (chain 10)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
- **Task ID**: `cb6c2a44-b922-415f-9297-6fabba4fec6f`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x1179ee3f92241c55f6...`](https://optimistic.etherscan.io/tx/0x1179ee3f92241c55f6fff436b91849a9b94cf78cdc8c45d3ec9f65eeea18b5f8)
- TX 2: [`0x825ebd374024b65d9f...`](https://optimistic.etherscan.io/tx/0x825ebd374024b65d9f482eb544ec63782db7ac4ee66d3122a54422761202d2a9)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Ethereum (chain 1)

- **Status**: FAIL
- **Operator**: `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b`
- **USDC**: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
- **Error**: Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("TxWatcher(Timeout)"). Task remains published.
- **Task ID**: `59d4b636-e935-42c8-b573-bf2e6f9d95ad`

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
- [x] Avalanche: Full lifecycle (create -> escrow -> release -> verify)
- [x] Monad: Full lifecycle (create -> escrow -> release -> verify)
- [x] Celo: Full lifecycle (create -> escrow -> release -> verify)
- [x] Optimism: Full lifecycle (create -> escrow -> release -> verify)
- [ ] Ethereum: Failed (Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("TxWatcher(Timeout)"). Task remains published.)
- [~] Reputation: partial (one direction only)

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
