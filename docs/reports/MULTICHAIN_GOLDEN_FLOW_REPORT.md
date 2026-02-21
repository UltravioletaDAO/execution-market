# Multichain Golden Flow Report

> **Date**: 2026-02-21 15:57 UTC
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
| Reputation | PASS |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Base** | 8453 | **PASS** | [View](https://basescan.org/tx/0x69bdc7940e215ba1e345ac6f3fe095d1a3f36130d994059914b7c8076301ff3b) | [View](https://basescan.org/tx/0x66efb5dbf4318b902e4aae7e2c64fbe1fb342e3dcfebb110be5cfba476235bc6) | N/A | 25.9s |
| **Polygon** | 137 | **PASS** | [View](https://polygonscan.com/tx/0xdf366b634005a0cec693f880f75f8c0d9de8cde10b5b4e05fbb48b02a872f84e) | [View](https://polygonscan.com/tx/0x0edb4b4f51ccf58a323cb13f2cb2852db8af78468f0e628171317497d956b012) | N/A | 51.95s |
| **Arbitrum** | 42161 | **PASS** | [View](https://arbiscan.io/tx/0x8de10908b0400f5649eb7af71d8dbafde9265f1078d262da5060aeafccf8dd55) | [View](https://arbiscan.io/tx/0x1c36d22f62b38ea40eabc31b5f57df068b99e30eafbfc5916e32f151c3bbb532) | N/A | 49.28s |
| **Avalanche** | 43114 | **PASS** | [View](https://snowtrace.io/tx/0x51a07b3f0b7c03f411a542b87190c3107cf8958fde80d8b842b526995deb01f7) | [View](https://snowtrace.io/tx/0x70dc7714ffb2b4f431f713205ec44f438bcd5229701939cc6e2e1fd152bd395c) | N/A | 43.96s |
| **Monad** | 143 | **PASS** | [View](https://explorer.monad.xyz/tx/0x081ac6833588935a875464ca6b5b8259c6634f04e37227cf7f3528668f89990c) | [View](https://explorer.monad.xyz/tx/0x06ca4619975020609da7e7a78891c73557a20f2c483a02fe25a33b70586599b1) | N/A | 54.02s |
| **Celo** | 42220 | **PASS** | [View](https://celoscan.io/tx/0x517a012396ebcbe9d700d3c660339602deddeacc839ed0b97c73dd6e22bf4b76) | [View](https://celoscan.io/tx/0xf6b2eb350af3a3f2ab4e6c813154f793ead048d08c04229f3454aeda958e2eb8) | N/A | 50.42s |
| **Optimism** | 10 | **FAIL** | N/A | N/A | N/A | 41.81s |
| **Ethereum** | 1 | **FAIL** | [View](https://etherscan.io/tx/0x7755d527ecc1b68045392e1ebd64616d655fbc40f765476a25eff2cc952990a2) | N/A | N/A | 516.81s |

---

### Base (chain 8453)

- **Status**: PASS
- **Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- **USDC**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Task ID**: `19bdaaf1-9dea-47a5-88d7-32d4b0621caa`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x69bdc7940e215ba1e3...`](https://basescan.org/tx/0x69bdc7940e215ba1e345ac6f3fe095d1a3f36130d994059914b7c8076301ff3b)
- TX 2: [`0x66efb5dbf4318b902e...`](https://basescan.org/tx/0x66efb5dbf4318b902e4aae7e2c64fbe1fb342e3dcfebb110be5cfba476235bc6)

### Polygon (chain 137)

- **Status**: PASS
- **Operator**: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
- **USDC**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Task ID**: `3fcc090c-6030-4727-be37-006dd216cb8c`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xdf366b634005a0cec6...`](https://polygonscan.com/tx/0xdf366b634005a0cec693f880f75f8c0d9de8cde10b5b4e05fbb48b02a872f84e)
- TX 2: [`0x0edb4b4f51ccf58a32...`](https://polygonscan.com/tx/0x0edb4b4f51ccf58a323cb13f2cb2852db8af78468f0e628171317497d956b012)

### Arbitrum (chain 42161)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- **Task ID**: `21eccda5-ccb9-4675-bcb2-f45f4a1930cd`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x8de10908b0400f5649...`](https://arbiscan.io/tx/0x8de10908b0400f5649eb7af71d8dbafde9265f1078d262da5060aeafccf8dd55)
- TX 2: [`0x1c36d22f62b38ea40e...`](https://arbiscan.io/tx/0x1c36d22f62b38ea40eabc31b5f57df068b99e30eafbfc5916e32f151c3bbb532)

### Avalanche (chain 43114)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **Task ID**: `10c6c471-204b-4bd4-a794-13191e7e2add`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x51a07b3f0b7c03f411...`](https://snowtrace.io/tx/0x51a07b3f0b7c03f411a542b87190c3107cf8958fde80d8b842b526995deb01f7)
- TX 2: [`0x70dc7714ffb2b4f431...`](https://snowtrace.io/tx/0x70dc7714ffb2b4f431f713205ec44f438bcd5229701939cc6e2e1fd152bd395c)

### Monad (chain 143)

- **Status**: PASS
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Task ID**: `ce1b6d47-1f66-4db5-b0c7-563e6be1d454`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x081ac6833588935a87...`](https://explorer.monad.xyz/tx/0x081ac6833588935a875464ca6b5b8259c6634f04e37227cf7f3528668f89990c)
- TX 2: [`0x06ca4619975020609d...`](https://explorer.monad.xyz/tx/0x06ca4619975020609da7e7a78891c73557a20f2c483a02fe25a33b70586599b1)

### Celo (chain 42220)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`
- **Task ID**: `9111fcaf-3560-4e90-8f68-5ce5d387bce9`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x517a012396ebcbe9d7...`](https://celoscan.io/tx/0x517a012396ebcbe9d700d3c660339602deddeacc839ed0b97c73dd6e22bf4b76)
- TX 2: [`0xf6b2eb350af3a3f2ab...`](https://celoscan.io/tx/0xf6b2eb350af3a3f2ab4e6c813154f793ead048d08c04229f3454aeda958e2eb8)

### Optimism (chain 10)

- **Status**: FAIL
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
- **Error**: Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("TxWatcher(Timeout)"). Task remains published.
- **Task ID**: `a8cf60ef-9a44-4de3-a462-40f34fc2f8b5`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | FAIL |

### Ethereum (chain 1)

- **Status**: FAIL
- **Operator**: `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b`
- **USDC**: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
- **Error**: Approval failed: HTTP 502 - {'raw': '<html>\r\n<head><title>502 Bad Gateway</title></head>\r\n<body>\r\n<center><h1>502 Bad Gateway</h1></center>\r\n</body>\r\n</html>\r\n', 'status_code': 502, '_http_status': 502}
- **Task ID**: `f6478a34-dab0-4121-9478-1feec0e13182`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | FAIL |

**Transactions:**
- TX 1: [`0x7755d527ecc1b68045...`](https://etherscan.io/tx/0x7755d527ecc1b68045392e1ebd64616d655fbc40f765476a25eff2cc952990a2)

---

## Invariants Verified

- [x] Base: Full lifecycle (create -> escrow -> release -> verify)
- [x] Polygon: Full lifecycle (create -> escrow -> release -> verify)
- [x] Arbitrum: Full lifecycle (create -> escrow -> release -> verify)
- [x] Avalanche: Full lifecycle (create -> escrow -> release -> verify)
- [x] Monad: Full lifecycle (create -> escrow -> release -> verify)
- [x] Celo: Full lifecycle (create -> escrow -> release -> verify)
- [ ] Optimism: Failed (Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("TxWatcher(Timeout)"). Task remains published.)
- [ ] Ethereum: Failed (Approval failed: HTTP 502 - {'raw': '<html>\r\n<head><title>502 Bad Gateway</title></head>\r\n<body>\r\n<center><h1>502 Bad Gateway</h1></center>\r\n</body>\r\n</html>\r\n', 'status_code': 502, '_http_status': 502})
- [x] Bidirectional reputation (agent<->worker) on Base

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
