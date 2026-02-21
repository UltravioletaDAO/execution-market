# Multichain Golden Flow Report

> **Date**: 2026-02-21 13:24 UTC
> **API**: `https://api.execution.market`
> **Fee Model**: credit_card (fee deducted from bounty on-chain)
> **Escrow Mode**: direct_release (Fase 5, 1-TX release)
> **Chains tested**: 1
> **Result**: **PASS**

---

## Executive Summary

Tested the complete Execution Market lifecycle across **1 blockchains** 
using the Fase 5 credit card model. 1/1 chains passed.

**Overall Result: PASS**

| Metric | Value |
|--------|-------|
| Bounty per chain | $0.10 USDC |
| Worker net (87%) | $0.087000 USDC |
| Fee (13%) | $0.013000 USDC |
| Total cost | $0.10 USDC |
| Total on-chain TXs | 2 |
| Reputation | SKIP |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Ethereum** | 1 | **PASS** | [View](https://etherscan.io/tx/0x5cbdfca6cad5cb584b9aa5857160a67a2bf6b873a9b0793e984c7c599d7712b7) | [View](https://etherscan.io/tx/0x67a69545b6f536e6db5ba2a9c167e91ade50aa1becf44e584bb2eb51c2a0cdf4) | N/A | 191.71s |

---

### Ethereum (chain 1)

- **Status**: PASS
- **Operator**: `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b`
- **USDC**: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
- **Task ID**: `b6ed8e14-cbd3-46a9-bd11-2cf09bc916c5`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x5cbdfca6cad5cb584b...`](https://etherscan.io/tx/0x5cbdfca6cad5cb584b9aa5857160a67a2bf6b873a9b0793e984c7c599d7712b7)
- TX 2: [`0x67a69545b6f536e6db...`](https://etherscan.io/tx/0x67a69545b6f536e6db5ba2a9c167e91ade50aa1becf44e584bb2eb51c2a0cdf4)

---

## Invariants Verified

- [x] Ethereum: Full lifecycle (create -> escrow -> release -> verify)
- [ ] Reputation: SKIP

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
