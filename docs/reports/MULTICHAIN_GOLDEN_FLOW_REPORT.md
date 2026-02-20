# Multichain Golden Flow Report

> **Date**: 2026-02-20 18:39 UTC
> **API**: `https://api.execution.market`
> **Fee Model**: credit_card (fee deducted from bounty on-chain)
> **Escrow Mode**: direct_release (Fase 5, 1-TX release)
> **Chains tested**: 7
> **Result**: **FAIL**

---

## Executive Summary

Tested the complete Execution Market lifecycle across **7 blockchains** 
using the Fase 5 credit card model. 4/7 chains passed.

**Overall Result: FAIL**

| Metric | Value |
|--------|-------|
| Bounty per chain | $0.10 USDC |
| Worker net (87%) | $0.087000 USDC |
| Fee (13%) | $0.013000 USDC |
| Total cost | $0.70 USDC |
| Total on-chain TXs | 8 |
| Reputation | SKIP |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Base** | 8453 | **PASS** | [View](https://basescan.org/tx/0xf9334d6d9a0eb20cd1f857dc3badafb5c89a8b4b49e824546aed78b0a887e93d) | [View](https://basescan.org/tx/0x8af3fc9ee8e3f0b1f38e1be2f775b5e1753ac9b01f09c4f4ac4b1eefabec4ccb) | $0.087000 | 41.86s |
| **Polygon** | 137 | **PASS** | [View](https://polygonscan.com/tx/0x858b4c894b4568c48fc96baa3f2c084bee4c5c50af19eb1888304ad25423f270) | [View](https://polygonscan.com/tx/0x5d458cf09604da8f6f852aa9b1b70f53f1d50c018129727c24a888be38bbc37b) | $0.087000 | 50.14s |
| **Arbitrum** | 42161 | **PASS** | [View](https://arbiscan.io/tx/0xc5a1ad3a1557bc34b88d7f309e186a1f2d5ad80a3ef3b7a50b8335cc995f770a) | [View](https://arbiscan.io/tx/0x23d0ca911c9e63fa6c35c849c3daf45dcad7adeada9624a48f9ea9ea64747d7a) | $0.087000 | 50.77s |
| **Avalanche** | 43114 | **PASS** | [View](https://snowtrace.io/tx/0xe24d49490dcc56985785d4be66c5e90075880cf7322f029b0b26471e9c446bab) | [View](https://snowtrace.io/tx/0x9700290168efab89036b0b2bda815f2cae13eb3f2fcbc78177d4d6c4eeae075a) | $0.087000 | 37.08s |
| **Monad** | 143 | **FAIL** | N/A | N/A | N/A | 5.99s |
| **Celo** | 42220 | **FAIL** | N/A | N/A | N/A | 5.35s |
| **Optimism** | 10 | **FAIL** | N/A | N/A | N/A | 5.11s |

---

### Base (chain 8453)

- **Status**: PASS
- **Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- **USDC**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Task ID**: `a82c7076-922d-4114-812e-019c89314934`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xf9334d6d9a0eb20cd1...`](https://basescan.org/tx/0xf9334d6d9a0eb20cd1f857dc3badafb5c89a8b4b49e824546aed78b0a887e93d)
- TX 2: [`0x8af3fc9ee8e3f0b1f3...`](https://basescan.org/tx/0x8af3fc9ee8e3f0b1f38e1be2f775b5e1753ac9b01f09c4f4ac4b1eefabec4ccb)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Polygon (chain 137)

- **Status**: PASS
- **Operator**: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
- **USDC**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Task ID**: `6e77f20d-ee08-456a-ab2b-23c2f36bf1ac`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x858b4c894b4568c48f...`](https://polygonscan.com/tx/0x858b4c894b4568c48fc96baa3f2c084bee4c5c50af19eb1888304ad25423f270)
- TX 2: [`0x5d458cf09604da8f6f...`](https://polygonscan.com/tx/0x5d458cf09604da8f6f852aa9b1b70f53f1d50c018129727c24a888be38bbc37b)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Arbitrum (chain 42161)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- **Task ID**: `d9e8eb59-0db9-472c-9ee1-68f0fd96d8b2`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xc5a1ad3a1557bc34b8...`](https://arbiscan.io/tx/0xc5a1ad3a1557bc34b88d7f309e186a1f2d5ad80a3ef3b7a50b8335cc995f770a)
- TX 2: [`0x23d0ca911c9e63fa6c...`](https://arbiscan.io/tx/0x23d0ca911c9e63fa6c35c849c3daf45dcad7adeada9624a48f9ea9ea64747d7a)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Avalanche (chain 43114)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **Task ID**: `fd388423-d6ee-4688-981c-58a43bfcdb70`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xe24d49490dcc569857...`](https://snowtrace.io/tx/0xe24d49490dcc56985785d4be66c5e90075880cf7322f029b0b26471e9c446bab)
- TX 2: [`0x9700290168efab8903...`](https://snowtrace.io/tx/0x9700290168efab89036b0b2bda815f2cae13eb3f2fcbc78177d4d6c4eeae075a)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Monad (chain 143)

- **Status**: FAIL
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Error**: Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("ErrorResp(ErrorPayload { code: -32603, message: \"execution reverted: FiatTokenV2: invalid signature\", data: Some(RawValue(\"0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001e46696174546f6b656e56323a20696e76616c6964207369676e61747572650000\")) })"). Task remains published.
- **Task ID**: `1fa379b0-97e3-4c28-b0d4-4a596f8fe5ba`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | FAIL |

### Celo (chain 42220)

- **Status**: FAIL
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xcebA9300f2b948710d2653dD7B07f33A8B32118C`
- **Error**: Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("ErrorResp(ErrorPayload { code: 3, message: \"execution reverted: FiatTokenV2: invalid signature\", data: Some(RawValue(\"0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001e46696174546f6b656e56323a20696e76616c6964207369676e61747572650000\")) })"). Task remains published.
- **Task ID**: `55b4d270-a42d-4416-ad19-629d3b8916c8`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | FAIL |

### Optimism (chain 10)

- **Status**: FAIL
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85`
- **Error**: Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: PaymentInfo validation failed: operator address mismatch: client=0xa06958d93135bed7e43893897c0d9fa931ef051c, allowed=[0xc2377a9db1de2520bd6b2756ed012f4e82f7938e]. Task remains published.
- **Task ID**: `5e2fb891-990e-40da-bfba-504efd025dec`

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
- [ ] Monad: Failed (Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("ErrorResp(ErrorPayload { code: -32603, message: \"execution reverted: FiatTokenV2: invalid signature\", data: Some(RawValue(\"0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001e46696174546f6b656e56323a20696e76616c6964207369676e61747572650000\")) })"). Task remains published.)
- [ ] Celo: Failed (Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("ErrorResp(ErrorPayload { code: 3, message: \"execution reverted: FiatTokenV2: invalid signature\", data: Some(RawValue(\"0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001e46696174546f6b656e56323a20696e76616c6964207369676e61747572650000\")) })"). Task remains published.)
- [ ] Optimism: Failed (Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: PaymentInfo validation failed: operator address mismatch: client=0xa06958d93135bed7e43893897c0d9fa931ef051c, allowed=[0xc2377a9db1de2520bd6b2756ed012f4e82f7938e]. Task remains published.)
- [ ] Reputation: SKIP

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
