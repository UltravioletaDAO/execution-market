# Multichain Golden Flow Report

> **Date**: 2026-02-19 17:54 UTC
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
| Reputation | PARTIAL |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Base** | 8453 | **PASS** | [View](https://basescan.org/tx/0xd4e0300d025eb1ecd86f82e7ba20839f22d72d0054b24a5e7e0e166002dba2e9) | [View](https://basescan.org/tx/0xd2bab27cf0b1ce698b852be913d528391f067890eb90ba823e73314508a3d0ca) | $0.087000 | 37.95s |
| **Polygon** | 137 | **PASS** | [View](https://polygonscan.com/tx/0x781e08f4b2ab1130416cb8ac2a1d8c9a4df338923d2ea2e1bb437ec87539a192) | [View](https://polygonscan.com/tx/0xb93190a576ad429b1a3051697e05cbfb4cbcb4e4c075b4f7b3acb2bdb7c36532) | $0.087000 | 50.14s |
| **Arbitrum** | 42161 | **PASS** | [View](https://arbiscan.io/tx/0xfb471b4d807faa08d2c8c71feb5cad619b9b85798c827d13ab9d7083904e3e3c) | [View](https://arbiscan.io/tx/0xeb7557d811f390c24a49567571779915dfe6e3ded5cabea5460e6d7424ccf52d) | $0.087000 | 50.47s |
| **Avalanche** | 43114 | **PASS** | [View](https://snowtrace.io/tx/0xfae22be2707484bc1216fc7dcd97e4a05dc0de957cfcc3d91449827e54214b46) | [View](https://snowtrace.io/tx/0x07a4e92d8f06f18a79f9f5bbee7843d57d92f22e3b451605a38751ef91066550) | $0.087000 | 43.95s |
| **Monad** | 143 | **FAIL** | N/A | N/A | N/A | 5.37s |
| **Celo** | 42220 | **FAIL** | N/A | N/A | N/A | 5.31s |
| **Optimism** | 10 | **FAIL** | N/A | N/A | N/A | 6.11s |

---

### Base (chain 8453)

- **Status**: PASS
- **Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- **USDC**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`
- **Task ID**: `dc3e1ff6-ed94-4b8e-843e-ec97583d5b6d`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xd4e0300d025eb1ecd8...`](https://basescan.org/tx/0xd4e0300d025eb1ecd86f82e7ba20839f22d72d0054b24a5e7e0e166002dba2e9)
- TX 2: [`0xd2bab27cf0b1ce698b...`](https://basescan.org/tx/0xd2bab27cf0b1ce698b852be913d528391f067890eb90ba823e73314508a3d0ca)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Polygon (chain 137)

- **Status**: PASS
- **Operator**: `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`
- **USDC**: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359`
- **Task ID**: `181e89f4-50c2-484c-9a87-65d901926b49`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x781e08f4b2ab113041...`](https://polygonscan.com/tx/0x781e08f4b2ab1130416cb8ac2a1d8c9a4df338923d2ea2e1bb437ec87539a192)
- TX 2: [`0xb93190a576ad429b1a...`](https://polygonscan.com/tx/0xb93190a576ad429b1a3051697e05cbfb4cbcb4e4c075b4f7b3acb2bdb7c36532)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Arbitrum (chain 42161)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`
- **Task ID**: `561a4495-87bb-4411-878e-3aec8e49558c`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xfb471b4d807faa08d2...`](https://arbiscan.io/tx/0xfb471b4d807faa08d2c8c71feb5cad619b9b85798c827d13ab9d7083904e3e3c)
- TX 2: [`0xeb7557d811f390c24a...`](https://arbiscan.io/tx/0xeb7557d811f390c24a49567571779915dfe6e3ded5cabea5460e6d7424ccf52d)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Avalanche (chain 43114)

- **Status**: PASS
- **Operator**: `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`
- **USDC**: `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E`
- **Task ID**: `77005092-1964-4f9e-b35f-7115d44bfef3`
- **Payment Mode**: `fase2`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0xfae22be2707484bc12...`](https://snowtrace.io/tx/0xfae22be2707484bc1216fc7dcd97e4a05dc0de957cfcc3d91449827e54214b46)
- TX 2: [`0x07a4e92d8f06f18a79...`](https://snowtrace.io/tx/0x07a4e92d8f06f18a79f9f5bbee7843d57d92f22e3b451605a38751ef91066550)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker (87%) | $0.087000 | $0.087000 | YES |
| Fee (13%) | $0.013000 | $0.013000 | YES |

### Monad (chain 143)

- **Status**: FAIL
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Error**: Assign failed: Escrow lock failed during assignment: Escrow authorize failed: Escrow scheme error: Contract call failed: ContractCall("ErrorResp(ErrorPayload { code: -32603, message: \"execution reverted: FiatTokenV2: invalid signature\", data: Some(RawValue(\"0x08c379a00000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000001e46696174546f6b656e56323a20696e76616c6964207369676e61747572650000\")) })"). Task remains published.
- **Task ID**: `de00ace1-1201-442a-b645-ddb74e0c78b5`

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
- **Task ID**: `029f031b-3e2d-497d-8691-c7af496d1d22`

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
- **Task ID**: `336cf47e-5367-4aad-92c5-54df153b47bf`

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
- [~] Reputation: partial (one direction only)

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
