# Multichain Golden Flow Report

> **Date**: 2026-02-21 13:26 UTC
> **API**: `https://api.execution.market`
> **Fee Model**: credit_card (fee deducted from bounty on-chain)
> **Escrow Mode**: direct_release (Fase 5, 1-TX release)
> **Chains tested**: 1
> **Result**: **FAIL**

---

## Executive Summary

Tested the complete Execution Market lifecycle across **1 blockchains** 
using the Fase 5 credit card model. 0/1 chains passed.

**Overall Result: FAIL**

| Metric | Value |
|--------|-------|
| Bounty per chain | $0.10 USDC |
| Worker net (87%) | $0.087000 USDC |
| Fee (13%) | $0.013000 USDC |
| Total cost | $0.10 USDC |
| Total on-chain TXs | 0 |
| Reputation | SKIP |

---

## Results by Chain

| Chain | Chain ID | Status | Escrow TX | Release TX | Worker Net | Time |
|-------|----------|--------|-----------|------------|------------|------|
| **Ethereum** | 1 | **FAIL** | N/A | N/A | N/A | 925.01s |

---

### Ethereum (chain 1)

- **Status**: FAIL
- **Operator**: `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b`
- **USDC**: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48`
- **Error**: Assign failed: Escrow lock failed during assignment: Escrow authorize failed: The read operation timed out. Task remains published.
- **Task ID**: `ce215f20-de06-4b74-b5b0-f25c08cc5691`

| Phase | Status |
|-------|--------|
| create | PASS |
| apply | PASS |
| assign | FAIL |

---

## Invariants Verified

- [ ] Ethereum: Failed (Assign failed: Escrow lock failed during assignment: Escrow authorize failed: The read operation timed out. Task remains published.)
- [ ] Reputation: SKIP

---

## Excluded Chains

- **Ethereum**: x402r-SDK factory label mismatch (pending fix from BackTrack). See [issue report](https://github.com/BackTrackCo/x402r-sdk/issues).
