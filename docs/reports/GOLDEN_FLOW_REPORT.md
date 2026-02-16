# Golden Flow Report -- Definitive E2E Acceptance Test (Fase 5)

> **Date**: 2026-02-16 10:04 UTC
> **Environment**: Production (Base Mainnet, chain 8453)
> **API**: `https://api.execution.market`
> **Fee Model**: credit_card (fee deducted from bounty on-chain)
> **Escrow Mode**: direct_release (escrow at assignment, 1-TX release)
> **Result**: **PARTIAL**

---

## Executive Summary

The Golden Flow tested the complete Execution Market lifecycle end-to-end 
on production against Base Mainnet using the Fase 5 credit card fee model. 6/7 phases passed.

**Overall Result: PARTIAL**

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Bounty (lock amount) | $0.10 USDC |
| Worker Net (87%) | $0.087000 USDC |
| Operator Fee (13%) | $0.013000 USDC |
| Total Cost to Agent | $0.10 USDC |
| Fee Model | credit_card |
| Escrow Mode | direct_release |
| Worker Wallet | `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` |
| Treasury | `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad` |
| API Base | `https://api.execution.market` |
| EM Agent ID | 2106 |

---

## Flow Diagram

```mermaid
sequenceDiagram
    participant Agent
    participant API
    participant Facilitator
    participant Escrow
    participant Worker
    participant ERC8004

    Note over Agent,ERC8004: Phase 1: Health
    Agent->>API: GET /health
    Agent->>API: GET /config
    Agent->>API: GET /reputation/info

    Note over Agent,ERC8004: Phase 2: Task Creation (balance check only)
    Agent->>API: POST /tasks (bounty=$0.10)
    API->>API: balanceOf(agent) -- advisory check
    Note right of API: No escrow yet (deferred to assignment)

    Note over Agent,ERC8004: Phase 3: Worker Identity
    Worker->>API: POST /executors/register
    Worker->>API: POST /reputation/register
    API->>Facilitator: Gasless registration
    Facilitator->>ERC8004: Mint identity NFT

    Note over Agent,ERC8004: Phase 4: Apply + Assign (escrow lock) + Submit
    Worker->>API: POST /tasks/{id}/apply
    Agent->>API: POST /tasks/{id}/assign
    API->>Facilitator: Lock $0.10 in escrow (receiver=worker)
    Facilitator->>Escrow: TX1: Lock $0.10
    Worker->>API: POST /tasks/{id}/submit (evidence)

    Note over Agent,ERC8004: Phase 5: Approval + Payment (1 TX)
    Agent->>API: POST /submissions/{id}/approve
    API->>Facilitator: Release escrow
    Facilitator->>Escrow: TX2: Release (fee calc splits)
    Escrow->>Worker: $0.087000 (87%)
    Escrow->>Operator: $0.013000 (13%)

    Note over Agent,ERC8004: Phase 6: Reputation
    Agent->>API: Rate worker (score: 90)
    API->>Facilitator: POST /feedback
    Worker->>API: Rate agent (score: 85)
    API->>Facilitator: POST /feedback

    Note over Agent,ERC8004: Phase 7: Verification
    Agent->>API: GET /reputation/em
    Agent->>API: GET /reputation/feedback/{task_id}
```

---

## Phase Results

| # | Phase | Status | Time |
|---|-------|--------|------|
| 1 | Health & Config Verification | **PASS** | 0.52s |
| 2 | Task Creation (Balance Check) | **PASS** | 6.59s |
| 3 | Worker Registration & Identity | **PASS** | 11.47s |
| 4 | Task Lifecycle (Apply -> Assign+Escrow -> Submit) | **PASS** | 26.97s |
| 5 | Approval & Payment Settlement | **PASS** | 19.49s |
| 6 | Bidirectional Reputation | **PARTIAL** | 2.82s |
| 7 | Final Verification | **PASS** | 0.27s |

---

## Health & Config Verification

- **Status**: PASS
- **Time**: 0.52s


## Task Creation (Balance Check)

- **Status**: PASS
- **Time**: 6.59s

- **Task ID**: `4eabee24-3780-4d1b-bbc6-e3a165cd931c`
- **Escrow at creation**: False
- **Fee model**: credit_card

## Worker Registration & Identity

- **Status**: PASS
- **Time**: 11.47s

- **Executor ID**: `803dfbf1-7b91-4a41-8d31-518f4fa2fcd4`
- **ERC-8004 Agent ID**: 17841
- **ERC-8004 TX**: [`0xc77e3209dcba70...`](https://basescan.org/tx/0xc77e3209dcba705d8bffebc1c2ed9d099d65433361ca0702dbe5bc2711fed4dc)

## Task Lifecycle (Apply -> Assign+Escrow -> Submit)

- **Status**: PASS
- **Time**: 26.97s

- **Submission ID**: `d6275a6d-c4b4-49d6-bfd5-5c7c639dbcc9`
- **Escrow TX (at assignment)**: [`0x88837b64962aba...`](https://basescan.org/tx/0x88837b64962abaaf3ca2f0d1049bbfcc840ea0badd091497c67d008e172bf54a)
- **Escrow Verified**: True
- **Escrow mode**: direct_release

## Approval & Payment Settlement

- **Status**: PASS
- **Time**: 19.49s

- **Payment Mode**: `fase2`
- **Worker TX**: [`0x5838585d434f35...`](https://basescan.org/tx/0x5838585d434f35cda943b8e17d4fcce905c83fcfc1ded3ca7bca6702425419dd)
- **Escrow Release**: [`0x5838585d434f35...`](https://basescan.org/tx/0x5838585d434f35cda943b8e17d4fcce905c83fcfc1ded3ca7bca6702425419dd)

### Fee Math Verification (Credit Card Model)

| Metric | Expected | Actual | Match |
|--------|----------|--------|-------|
| Worker net (87%) | $0.087000 | $0.087000 | YES |
| Operator fee (13%) | $0.013000 | $0.013000 | YES |
| Lock amount | $0.100000 | $0.100000 | YES |

## Bidirectional Reputation

- **Status**: PARTIAL
- **Time**: 2.82s
- **Error**: Worker->Agent: HTTP 200, success=False, error=On-chain signing failed: {'code': -32000, 'message': 'nonce too low: next nonce 47, tx nonce 46'}

- **Agent->Worker TX**: [`ebcfccb6294cfeab...`](https://basescan.org/tx/ebcfccb6294cfeab3ad8d17af95ff529ce810c6c1ddd4998adc27ef55d15a57d)

## Final Verification

- **Status**: PASS
- **Time**: 0.27s

- **EM Reputation Score**: 78.0
- **EM Reputation Count**: 13
- **Feedback Available**: True

---

## ERC-8004 Identity Verification

| Field | Value |
|-------|-------|
| Worker Wallet | `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` |
| ERC-8004 Agent ID | 17841 |
| Network | base |
| Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| Registration TX | `0xc77e3209dcba705d8bffebc1c2ed9d099d65433361ca0702dbe5bc2711fed4dc` |

---

## On-Chain Transaction Summary

| # | TX Hash | BaseScan |
|---|---------|----------|
| 1 | `0xc77e3209dcba705d8b...` | [View](https://basescan.org/tx/0xc77e3209dcba705d8bffebc1c2ed9d099d65433361ca0702dbe5bc2711fed4dc) |
| 2 | `0x88837b64962abaaf3c...` | [View](https://basescan.org/tx/0x88837b64962abaaf3ca2f0d1049bbfcc840ea0badd091497c67d008e172bf54a) |
| 3 | `0x5838585d434f35cda9...` | [View](https://basescan.org/tx/0x5838585d434f35cda943b8e17d4fcce905c83fcfc1ded3ca7bca6702425419dd) |
| 4 | `ebcfccb6294cfeab3ad8...` | [View](https://basescan.org/tx/ebcfccb6294cfeab3ad8d17af95ff529ce810c6c1ddd4998adc27ef55d15a57d) |

---

## Invariants Verified

- [x] API is healthy and returning correct configuration
- [x] Task created successfully with published status (balance check only)
- [x] Escrow locked at assignment (direct_release, worker as receiver)
- [x] Escrow lock TX verified on-chain (status: SUCCESS)
- [x] Worker registered with executor ID
- [x] Worker receives $0.087000 (87% of bounty, credit card model)
- [x] Operator receives $0.013000 (13% on-chain fee calculator)
- [x] All payment TXs verified on-chain (status: 0x1)
- [x] Single-TX escrow release (fee split by StaticFeeCalculator 1300bps)
