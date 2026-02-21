# Multichain Golden Flow Report

> **Date**: 2026-02-21 12:25 UTC
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
| **Monad** | 143 | **PASS** | [View](https://explorer.monad.xyz/tx/0x38e906b7571c9cc716183f124e43758c06a05f21ec44e3451fcf3b0e2e4d0062) | [View](https://explorer.monad.xyz/tx/0x938232eeb1b6f4e7b6194e287a1784f947f730e91f712eb5e598aa32b3477e63) | N/A | 53.98s |

---

### Monad (chain 143)

- **Status**: PASS
- **Operator**: `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`
- **USDC**: `0x754704Bc059F8C67012fEd69BC8A327a5aafb603`
- **Task ID**: `07099231-f94d-4742-be86-83c9e62cdff0`
- **Payment Mode**: `direct_release`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | PASS |
| submit | PASS |
| approve | PASS |

**Transactions:**
- TX 1: [`0x38e906b7571c9cc716...`](https://explorer.monad.xyz/tx/0x38e906b7571c9cc716183f124e43758c06a05f21ec44e3451fcf3b0e2e4d0062)
- TX 2: [`0x938232eeb1b6f4e7b6...`](https://explorer.monad.xyz/tx/0x938232eeb1b6f4e7b6194e287a1784f947f730e91f712eb5e598aa32b3477e63)

---

## Invariants Verified

- [x] Monad: Full lifecycle (create -> escrow -> release -> verify)
- [ ] Reputation: SKIP

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
