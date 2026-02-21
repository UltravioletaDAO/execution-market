# Golden Flow Report -- Definitive E2E Acceptance Test (Fase 5)

> **Date**: 2026-02-21 04:10 UTC
> **Environment**: Production (Base Mainnet, chain 8453)
> **API**: `https://api.execution.market`
> **Fee Model**: credit_card (fee deducted from bounty on-chain)
> **Escrow Mode**: direct_release (escrow at assignment, 1-TX release)
> **Token**: USDC (`0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`)
> **Result**: **PARTIAL**

---

## Executive Summary

The Golden Flow tested the complete Execution Market lifecycle end-to-end 
on production against Base Mainnet using the Fase 5 credit card fee model with **USDC**. 6/7 phases passed.

**Overall Result: PARTIAL**

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Payment Token | USDC |
| Token Contract | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
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
| 1 | Health & Config Verification | **PASS** | 0.83s |
| 2 | Task Creation (Balance Check) | **PASS** | 1.28s |
| 3 | Worker Registration & Identity | **PASS** | 13.51s |
| 4 | Task Lifecycle (Apply -> Assign+Escrow -> Submit) | **PASS** | 10.34s |
| 5 | Approval & Payment Settlement | **PASS** | 26.02s |
| 6 | Bidirectional Reputation | **PARTIAL** | 1.76s |
| 7 | Final Verification | **PASS** | 0.29s |

---

## Health & Config Verification

- **Status**: PASS
- **Time**: 0.83s


## Task Creation (Balance Check)

- **Status**: PASS
- **Time**: 1.28s

- **Task ID**: `15b43386-6221-4e0d-84e3-dd3866648f84`
- **Escrow at creation**: False
- **Fee model**: credit_card

## Worker Registration & Identity

- **Status**: PASS
- **Time**: 13.51s

- **Executor ID**: `803dfbf1-7b91-4a41-8d31-518f4fa2fcd4`
- **ERC-8004 Agent ID**: 18616
- **ERC-8004 TX**: [`0xdb6cea7b1d34ab...`](https://basescan.org/tx/0xdb6cea7b1d34ab3f875253fc94e7af997f5a4c79c39c36d4544542baa161b960)

## Task Lifecycle (Apply -> Assign+Escrow -> Submit)

- **Status**: PASS
- **Time**: 10.34s

- **Submission ID**: `7852a41d-dbbe-4eb4-87de-5f5e1cf6eb5f`
- **Escrow TX (at assignment)**: [`0x43e5d75cc11d43...`](https://basescan.org/tx/0x43e5d75cc11d43d468a468d9279da52947726069b28dece9de106c5ad097075c)
- **Escrow Verified**: True
- **Escrow mode**: direct_release

## Approval & Payment Settlement

- **Status**: PASS
- **Time**: 26.02s

- **Payment Mode**: `unknown`
- **Worker TX**: [`0xb6229e82316a5c...`](https://basescan.org/tx/0xb6229e82316a5c56285845b16f0fa0979780c370f28f8be3549839d49d8108e2)
- **Fee TX**: [`0xc4c7b9ba3a990d...`](https://basescan.org/tx/0xc4c7b9ba3a990d8ffb1edfde869a5f17cba4503d93aaeb9d0f6797ca22c48f17)

## Bidirectional Reputation

- **Status**: PARTIAL
- **Time**: 1.76s
- **Error**: Worker->Agent: HTTP 200, success=False, error=EM_WORKER_PRIVATE_KEY not set — worker cannot sign on-chain TX

- **Agent->Worker TX**: [`51cd777c225d6155...`](https://basescan.org/tx/51cd777c225d6155458d5e271aa28ba7cdcc7311e35916faa4a39b0d89f450c8)

## Final Verification

- **Status**: PASS
- **Time**: 0.29s

- **EM Reputation Score**: 79.0
- **EM Reputation Count**: 14
- **Feedback Available**: True

---

## ERC-8004 Identity Verification

| Field | Value |
|-------|-------|
| Worker Wallet | `0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15` |
| ERC-8004 Agent ID | 18616 |
| Network | base |
| Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| Registration TX | `0xdb6cea7b1d34ab3f875253fc94e7af997f5a4c79c39c36d4544542baa161b960` |

---

## On-Chain Transaction Summary

| # | TX Hash | BaseScan |
|---|---------|----------|
| 1 | `0xdb6cea7b1d34ab3f87...` | [View](https://basescan.org/tx/0xdb6cea7b1d34ab3f875253fc94e7af997f5a4c79c39c36d4544542baa161b960) |
| 2 | `0x43e5d75cc11d43d468...` | [View](https://basescan.org/tx/0x43e5d75cc11d43d468a468d9279da52947726069b28dece9de106c5ad097075c) |
| 3 | `0xb6229e82316a5c5628...` | [View](https://basescan.org/tx/0xb6229e82316a5c56285845b16f0fa0979780c370f28f8be3549839d49d8108e2) |
| 4 | `0xc4c7b9ba3a990d8ffb...` | [View](https://basescan.org/tx/0xc4c7b9ba3a990d8ffb1edfde869a5f17cba4503d93aaeb9d0f6797ca22c48f17) |
| 5 | `51cd777c225d6155458d...` | [View](https://basescan.org/tx/51cd777c225d6155458d5e271aa28ba7cdcc7311e35916faa4a39b0d89f450c8) |

---

## Invariants Verified

- [x] API is healthy and returning correct configuration
- [x] Task created successfully with published status (balance check only)
- [x] Escrow locked at assignment (direct_release, worker as receiver)
- [x] Escrow lock TX verified on-chain (status: SUCCESS)
- [x] Worker registered with executor ID
- [x] Operator receives $0.013000 (13% on-chain fee calculator)
- [x] All payment TXs verified on-chain (status: 0x1)
- [x] Single-TX escrow release (fee split by StaticFeeCalculator 1300bps)
