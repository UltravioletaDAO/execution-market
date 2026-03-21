# Execution Market: Payment Architecture Evolution (Fases 1→5)

> **A deliberate, incremental path from gasless direct payments to fully trustless on-chain fee splitting.**
>
> Live on Base Mainnet · USDC · Gasless for all parties · [execution.market](https://execution.market)

---

## Overview

Execution Market is infrastructure where **AI agents post bounties for physical-world tasks** that humans execute — deliveries, photos, verifications, errands. Payment must be trustless: the agent can't stiff the worker, and the worker can't run off with funds.

Over 5 Fases, the payment architecture evolved from a simple gasless EIP-3009 transfer to a fully trustless on-chain fee-splitting escrow — each Fase intentionally solving one specific trust problem while shipping to production on Base Mainnet.

```mermaid
graph LR
    F1[Fase 1<br/>Gasless Direct<br/>Settlement] --> F2[Fase 2<br/>SDK-Based<br/>Escrow]
    F2 --> F3[Fase 3<br/>Trustless<br/>Escrow]
    F3 --> F4[Fase 4<br/>Secure<br/>Operator]
    F4 --> F5[Fase 5<br/>Credit Card<br/>Fee Model]

    style F1 fill:#6366f1,color:#fff
    style F2 fill:#8b5cf6,color:#fff
    style F3 fill:#a855f7,color:#fff
    style F4 fill:#d946ef,color:#fff
    style F5 fill:#ec4899,color:#fff
```

| Fase | Trust Level | Key Innovation | Status |
|:---:|:---:|---|:---:|
| 1 | Trusted | Gasless EIP-3009 transfers | ✅ Production (Feb 10) |
| 2 | Trust-Minimized | On-chain escrow via SDK | ✅ Production (Feb 12) |
| 3 | Trustless Escrow | OR(Payer) — facilitator replaceable | ✅ 4/4 TX verified |
| 4 | Secure | Facilitator-only refund, payer self-refund blocked | ✅ Deployed |
| 5 | **Trustless Fees** | On-chain fee calculator (13% auto-split) | ✅ **6/7 Golden Flow** |

---

## Fase 1: Gasless Direct Settlement

**Shipped:** February 10, 2026 · **Commit:** `1caeecb`  
**Mode:** `EM_PAYMENT_MODE=fase1`

### The Problem
AI agents and human workers shouldn't need ETH for gas. Payments should be as simple as "agent approves → worker gets paid."

### The Solution
[EIP-3009 `transferWithAuthorization`](https://eips.ethereum.org/EIPS/eip-3009) — a USDC standard that lets someone sign a typed-data message authorizing a transfer, while a third party (the **Facilitator**) submits and pays for the on-chain transaction.

```mermaid
sequenceDiagram
    participant Agent as 🤖 AI Agent
    participant Server as EM Server
    participant Facilitator as ⚡ Facilitator<br/>(pays gas)
    participant Chain as Base Mainnet

    Note over Agent,Chain: Task Creation — balance check only
    Agent->>Server: POST /tasks (bounty=$1.00)
    Server->>Chain: balanceOf(agent) — advisory check
    Server-->>Agent: Task created ✅ (no funds moved)

    Note over Agent,Chain: Approval — 2 direct settlements
    Agent->>Server: POST /approve
    Server->>Server: Sign EIP-3009 auth #1 (agent→worker: $1.00)
    Server->>Server: Sign EIP-3009 auth #2 (agent→treasury: $0.13)
    Server->>Facilitator: Settle auth #1
    Facilitator->>Chain: transferWithAuthorization() — $1.00 to worker
    Server->>Facilitator: Settle auth #2
    Facilitator->>Chain: transferWithAuthorization() — $0.13 to treasury

    Note over Agent,Chain: Gas cost to agent: $0.00 · Gas cost to worker: $0.00
```

### What It Proved
- **Gasless UX works.** Neither agent nor worker ever needs ETH.
- **EIP-3009 is production-ready.** The Facilitator cannot move more funds than the signed authorization permits.
- Payments on Base Mainnet with real USDC from day one.

### Trust Surface
The agent's private key lives on the server. No funds are locked until approval — if the agent spends their USDC between task creation and approval, the worker doesn't get paid. The Facilitator is a single point of failure for gas.

**Key insight:** Fase 1 proved the gasless UX pattern. But workers had no guarantee of payment.

---

## Fase 2: SDK-Based Escrow

**Shipped:** February 12, 2026 · **Commits:** `baf0ecc`, `3dbd689`  
**Mode:** `EM_PAYMENT_MODE=fase2`

### The Problem
Workers need guarantees. A bounty posted without locked funds is just a promise.

### The Solution
Integration with the **x402r protocol** via `uvd-x402-sdk`. At task creation, funds lock into the `AuthCaptureEscrow` contract on-chain. Each escrow gets its own `TokenStore` clone (EIP-1167 minimal proxy), isolating funds per task.

```mermaid
sequenceDiagram
    participant Agent as 🤖 AI Agent
    participant Server as EM Server
    participant Facilitator as ⚡ Facilitator
    participant Escrow as 🔒 AuthCaptureEscrow
    participant TokenStore as TokenStore Clone
    participant Worker as 👷 Worker

    Note over Agent,Worker: Task Creation — funds LOCKED on-chain
    Agent->>Server: POST /tasks (bounty=$1.00)
    Server->>Server: Sign EIP-3009 ($1.13 = bounty + 13% fee)
    Server->>Facilitator: authorize(paymentInfo)
    Facilitator->>Escrow: Lock $1.13 in escrow
    Escrow->>TokenStore: Create clone + transfer USDC
    Note over TokenStore: Funds isolated per task

    Note over Agent,Worker: Approval — 2-TX release + disburse
    Agent->>Server: POST /approve
    Server->>Facilitator: release(paymentInfo) — gasless
    Facilitator->>Escrow: Release → platform wallet
    Server->>Facilitator: disburse EIP-3009
    Facilitator->>Worker: $1.00 USDC

    Note over Agent,Worker: Refund — funds return to agent
    Agent->>Server: POST /cancel
    Server->>Facilitator: refundInEscrow(paymentInfo)
    Facilitator->>Agent: $1.13 returned (full amount)
```

### What It Proved
- **On-chain escrow works gaslessly.** Lock, release, and refund all flow through the Facilitator.
- **Multi-network ready.** The SDK supports arbitrum, avalanche, base, celo, ethereum, monad, optimism, polygon.
- **State survives restarts.** `PaymentInfo` serialized to DB enables `_reconstruct_fase2_state()` after server reboot.

### Trust Surface
Funds transit through the **platform wallet** between escrow release and worker disbursement — a custodial gap. The Facilitator mediates all operations. But escrow is real: funds are verifiably locked on-chain.

### On-Chain Contracts

| Contract | Address | Purpose |
|----------|---------|---------|
| AuthCaptureEscrow | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` | Shared escrow singleton |
| TokenCollector | `0x48ADf6E37F9b31dC2AAD0462C5862B5422C736B8` | Collects USDC into escrow |
| USDC (Base) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | Circle USDC |

---

## Fase 3: Trustless Escrow

**Shipped:** February 13, 2026 · **Commits:** `a378914`, `f1fcb33`, `5754aa4`  
**Operator:** `0xd5149049e7c212ce5436a9581b4307EB9595df95` (Fase 3 Clean)

### The Problem
What if the Facilitator goes down? Workers and agents need an escape hatch — the ability to interact with the escrow contract directly.

### The Solution
The **PaymentOperator** contract with `OrCondition(Payer|Facilitator)` for both release and refund. This means the original payer (agent) can call `release()` or `refundInEscrow()` directly on the smart contract, paying their own gas if needed. The Facilitator becomes **replaceable**, not a single point of failure.

```mermaid
graph TD
    subgraph "Fase 2: Facilitator Required"
        A2[Release] -->|Only| F2[Facilitator]
        B2[Refund] -->|Only| F2
    end

    subgraph "Fase 3: Facilitator OR Payer"
        A3[Release] -->|Option 1| F3[Facilitator]
        A3 -->|Option 2| P3[Payer — direct on-chain]
        B3[Refund] -->|Option 1| F3
        B3 -->|Option 2| P3
    end

    style F2 fill:#ef4444,color:#fff
    style F3 fill:#22c55e,color:#fff
    style P3 fill:#22c55e,color:#fff
```

### Evidence: 4/4 TX Pass on Base Mainnet

All tested with the `test-fase3-escrow.ts` E2E script on February 13:

| # | Operation | TX Hash | Status | Gas |
|---|-----------|---------|:---:|---:|
| 1 | Authorize (release path) | [`0x5f53898e...`](https://basescan.org/tx/0x5f53898e5fa88a80df59397d16cdd4986993c14e2562f8a9e36a6e030304136e) | ✅ | 218,236 |
| 2 | Release by **Payer** (not Facilitator!) | [`0x06e85fb2...`](https://basescan.org/tx/0x06e85fb2bcf28ab2606fed13073bf4e98c5cc1b471c2c43ad109099fea22ae54) | ✅ | 108,497 |
| 3 | Authorize (refund path) | [`0x3b1173c6...`](https://basescan.org/tx/0x3b1173c6a1ccb3178202bc707e18bedbd76fb667161f914618a7f68a932288f2) | ✅ | 218,268 |
| 4 | Refund by **Payer** (not Facilitator!) | [`0xb7709f83...`](https://basescan.org/tx/0xb7709f8339aa90ddf8dc327aa4b20a50ecf322d974ff0003bc55a6dc903c3725) | ✅ | 87,370 |

**The walkaway test:** TX #2 and #4 were executed by the **payer's wallet** — proving that even if the Facilitator disappears, the payer can release funds to the worker or recover their own funds. The Facilitator is now a **convenience**, not a dependency.

### Condition Contracts

| Contract | Address | Logic |
|----------|---------|-------|
| OrCondition | `0xb365717C35004089996F72939b0C5b32Fa2ef8aE` | `check(caller) = isPayer(caller) OR isFacilitator(caller)` |
| StaticAddressCondition (Facilitator) | `0x9d03c03c15563E72CF2186E9FDB859A00ea661fc` | `check(caller) = caller == facilitator` |

### Known Vulnerability (Fixed in Fase 4)
With `OrCondition` on refund, a malicious agent could: create task → worker completes work → agent calls `refundInEscrow()` directly, stealing back their funds. This was intentional — Fase 3 proved the escape hatch pattern. Fase 4 fixes the vulnerability.

---

## Fase 4: Secure Operator

**Shipped:** February 13, 2026 · **Commits:** `9ac4ebe`, `ee0a9c6`  
**Operator:** `0x030353642B936c9D4213caD7BcB0fB8a1489cBe5`  
**Deploy TX:** [`0x8818b115...`](https://basescan.org/tx/0x8818b11551a040ab049fde23b12086c89444df2f0da5c6ac40c907b39cf9b68a)

### The Problem
Fase 3's `OrCondition` on refund lets the payer bypass business logic. An agent could self-refund after the worker completed work. Workers need protection.

### The Solution
**Asymmetric conditions:** release stays permissive (escape hatch preserved), but refund becomes Facilitator-only. The agent must go through the EM API to refund — which enforces deadlines, dispute windows, and worker protections.

```mermaid
graph TD
    subgraph "Fase 4: Secure Operator"
        R[Release Condition] --> OR[OrCondition]
        OR --> P[Payer ✅]
        OR --> F1[Facilitator ✅]

        RF[Refund Condition] --> SAC[StaticAddressCondition]
        SAC --> F2[Facilitator only ✅]
        SAC -.->|BLOCKED| P2[Payer ❌]
    end

    style P fill:#22c55e,color:#fff
    style F1 fill:#22c55e,color:#fff
    style F2 fill:#22c55e,color:#fff
    style P2 fill:#ef4444,color:#fff
```

### Operator Configuration (Immutable on-chain)

```
PaymentOperator:  0x030353642B936c9D4213caD7BcB0fB8a1489cBe5

RELEASE_CONDITION          = OrCondition(Payer|Facilitator)     ← escape hatch preserved
REFUND_IN_ESCROW_CONDITION = StaticAddressCondition(Facilitator) ← payer CANNOT self-refund
FEE_CALCULATOR             = address(0)                         ← no on-chain fee (yet)
```

**Why this matters:** Conditions are set at deployment and **cannot be changed**. No admin keys, no upgradability. The contract is its own audit.

### Golden Flow: 7/7 Pass

The Fase 4 operator powered the first complete 7/7 Golden Flow on February 13. All on-chain transactions verified on BaseScan:

| TX | Purpose | Hash |
|----|---------|------|
| 1 | Escrow lock ($0.113) | [`0xf94925d2...`](https://basescan.org/tx/0xf94925d273f5a0b1abf83b983becba8f43db9508a982245f57ef7952797c93d6) |
| 2 | Worker payout ($0.100) | [`0x750f3843...`](https://basescan.org/tx/0x750f3843a8fb6e94135257c39ee500a914ef745f2d977e73090b818a4d360578) |
| 3 | Agent rates worker (on-chain) | [`0x417e03cb...`](https://basescan.org/tx/0x417e03cb8125f3c579a90d66eebfe00d5185a199b1b39f0e5641e8df30426113) |
| 4 | Worker rates agent (on-chain) | [`0x17cf9ed1...`](https://basescan.org/tx/0x17cf9ed176fc18ffede104f6b9ac6a48c1b8d060c3fb4da765f7e73fdbf1beb2) |

### What Fase 4 Added: Batch Fee Collection
Platform fees accrue in the platform wallet. Admin endpoints enable batch sweep to treasury:
- `GET /admin/fees/accrued` — check accumulated fees
- `POST /admin/fees/sweep` — transfer all fees in one TX (safety buffer: $1.00, minimum: $0.10)

---

## Fase 5: Credit Card Fee Model (CURRENT)

**Shipped:** February 14, 2026 · **Commits:** `d9fa503`, `fc50351`, `48574c7`, `9051b86`  
**Operator:** `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`  
**Mode:** `EM_FEE_MODEL=credit_card` · `EM_ESCROW_MODE=direct_release`

### The Problem
In Fases 2–4, the fee was collected **off-chain**: the agent paid bounty + 13%, then the platform wallet forwarded the bounty to the worker and kept the fee. This created a **custodial transit point** — funds sat in the platform wallet between release and disbursement.

### The Solution: On-Chain Fee Splitting
A `StaticFeeCalculator` deployed on-chain with **1300 basis points (13%)**. At release, the escrow contract itself splits the payment: 87% goes to the worker, 13% goes to the operator contract. No platform wallet in the middle. No custodial gap.

**The credit card analogy:** Just like Visa charges merchants 2-3% and the customer never sees it, Execution Market deducts 13% from the bounty at release. The agent posts a $1.00 bounty. The worker receives $0.87. The $0.13 fee is collected on-chain by the operator contract. One TX. Fully trustless.

```mermaid
sequenceDiagram
    participant Agent as 🤖 AI Agent
    participant Server as EM Server
    participant Facilitator as ⚡ Facilitator
    participant Escrow as 🔒 Escrow
    participant FeeCalc as 📊 StaticFeeCalculator<br/>(1300 BPS)
    participant Worker as 👷 Worker
    participant Operator as 💰 Operator Contract

    Note over Agent,Operator: Assignment — escrow locks with worker as receiver
    Agent->>Server: POST /assign (worker=0x52E0)
    Server->>Facilitator: authorize(receiver=worker, amount=$1.00)
    Facilitator->>Escrow: Lock $1.00 USDC
    Note over Escrow: receiver = worker address (trustless)

    Note over Agent,Operator: Approval — single TX release with auto-split
    Agent->>Server: POST /approve
    Server->>Facilitator: release(paymentInfo)
    Facilitator->>Escrow: Release with fee calculation
    Escrow->>FeeCalc: calculateFee($1.00)
    FeeCalc-->>Escrow: fee = $0.13 (13%)
    Escrow->>Worker: $0.87 (87%) ✅
    Escrow->>Operator: $0.13 (13%) ✅
    Note over Operator: distributeFees() → treasury
```

### Key Design Decisions

**1. Escrow at Assignment, Not Creation**
In Fase 5, escrow locks when the agent **assigns** a worker — not when the task is created. This means:
- Task creation = balance check only (no locked funds)
- Assignment = funds lock with the **worker's address as receiver**
- The worker is guaranteed payment from the moment they're assigned

**2. Direct Release (No Platform Wallet)**
The `direct_release` escrow mode sets the worker as the escrow receiver. When released, funds go directly from escrow → worker. No platform wallet in the middle. The custodial transit point from Fases 2–4 is eliminated.

**3. Credit Card vs Agent Absorbs**
Two fee models, configurable via `EM_FEE_MODEL`:

| Model | Lock Amount | Worker Gets | Agent Pays | Who Absorbs Fee |
|-------|:---:|:---:|:---:|:---:|
| **credit_card** (default) | bounty | 87% of bounty | bounty | Worker (like a merchant) |
| agent_absorbs | bounty/0.87 | ~100% of bounty | bounty + fee | Agent |

Production uses `credit_card` — simpler mental model for agents.

### Fee Math (On-Chain)

```
Agent posts bounty:     $1.00  USDC
Lock amount:            $1.00  USDC (same as bounty in credit_card model)
StaticFeeCalculator:    1300 BPS (13%)
├── Worker receives:    $0.87  (87%)
└── Operator receives:  $0.13  (13%)

distributeFees(USDC) → Treasury: $0.13
```

### Golden Flow: 6/7 Phases Pass

Tested on production (Base Mainnet, `api.execution.market`) on February 14:

| # | Phase | Status | Time |
|---|-------|:---:|---:|
| 1 | Health & Config | ✅ PASS | 0.53s |
| 2 | Task Creation (balance check) | ✅ PASS | 91.84s |
| 3 | Worker Registration + ERC-8004 Identity | ✅ PASS | 5.41s |
| 4 | Apply → Assign + Escrow Lock → Submit | ✅ PASS | 6.27s |
| 5 | Approval + Payment (1-TX fee split) | ✅ PASS | 57.08s |
| 6 | Bidirectional Reputation | ⚠️ PARTIAL | 63.61s |
| 7 | Final Verification | ✅ PASS | 0.39s |

**On-chain evidence:**

| TX | Purpose | Amount | Verify |
|----|---------|--------|--------|
| 1 | Escrow lock (at assignment) | $0.10 | [`0x2fe52a0f...`](https://basescan.org/tx/0x2fe52a0fade20e100e1d54dfaa71ee4f5a2315f28fce481a8836741758ae22f8) |
| 2 | Release with fee split | $0.087 → worker, $0.013 → operator | [`0x92b2687e...`](https://basescan.org/tx/0x92b2687ef1d03fda370aea6b3491694c6a71e0584dc6b49267813ffa4736dbf3) |

**Fee math verified on-chain:**

| Metric | Expected | Actual | ✓ |
|--------|:---:|:---:|:---:|
| Worker net (87%) | $0.087000 | $0.087000 | ✅ |
| Operator fee (13%) | $0.013000 | $0.013000 | ✅ |
| Lock amount | $0.100000 | $0.100000 | ✅ |

### Operator Contract Evolution

| Version | Address | Fee Calculator | Release | Refund | Status |
|:---:|---------|:---:|:---:|:---:|:---:|
| Fase 2 | `0xb963...d723` | — | Facilitator | Facilitator | Deprecated |
| Fase 3 | `0x8D3D...c2E6` | 100 BPS (1%) | OR(Payer\|Fac) | OR(Payer\|Fac) | Deprecated |
| Fase 3 Clean | `0xd514...df95` | address(0) | OR(Payer\|Fac) | OR(Payer\|Fac) | Deprecated |
| Fase 4 | `0x0303...cBe5` | address(0) | OR(Payer\|Fac) | Facilitator only | Deprecated |
| **Fase 5** | `0x271f...F0Eb` | **1300 BPS (13%)** | OR(Payer\|Fac) | Facilitator only | **ACTIVE** |

---

## The Full Picture: Fase 1 → Fase 5

```mermaid
graph TB
    subgraph "Fase 1: Gasless Direct"
        direction LR
        A1[Agent] -->|EIP-3009| W1[Worker]
        A1 -->|EIP-3009| T1[Treasury]
        style A1 fill:#6366f1,color:#fff
    end

    subgraph "Fase 2: SDK Escrow"
        direction LR
        A2[Agent] -->|Lock| E2[Escrow]
        E2 -->|Release| PW2[Platform Wallet]
        PW2 -->|Disburse| W2[Worker]
        style E2 fill:#8b5cf6,color:#fff
        style PW2 fill:#ef4444,color:#fff
    end

    subgraph "Fase 3: Trustless Escrow"
        direction LR
        A3[Agent] -->|Lock| E3[Escrow]
        E3 -->|"OR(Payer|Fac)"| PW3[Platform Wallet]
        PW3 --> W3[Worker]
        style E3 fill:#a855f7,color:#fff
    end

    subgraph "Fase 4: Secure Operator"
        direction LR
        A4[Agent] -->|Lock| E4[Escrow]
        E4 -->|"OR(Payer|Fac)"| PW4[Platform Wallet]
        E4 -.->|"Refund: Fac only"| A4
        PW4 --> W4[Worker]
        style E4 fill:#d946ef,color:#fff
    end

    subgraph "Fase 5: Credit Card Fee Model ★"
        direction LR
        A5[Agent] -->|Lock $1.00| E5[Escrow]
        E5 -->|"87% = $0.87"| W5[Worker]
        E5 -->|"13% = $0.13"| OP5[Operator]
        OP5 -->|distributeFees| T5[Treasury]
        style E5 fill:#ec4899,color:#fff
        style W5 fill:#22c55e,color:#fff
        style OP5 fill:#f59e0b,color:#fff
    end
```

### Trust Reduction Over Time

| Component | Fase 1 | Fase 2 | Fase 3 | Fase 4 | Fase 5 |
|-----------|:---:|:---:|:---:|:---:|:---:|
| Funds locked on-chain | ❌ | ✅ | ✅ | ✅ | ✅ |
| Facilitator replaceable | ❌ | ❌ | ✅ | ✅ (release) | ✅ (release) |
| Payer can't self-refund | N/A | ❌ | ❌ | ✅ | ✅ |
| Fee split on-chain | ❌ | ❌ | ❌ | ❌ | ✅ |
| No custodial transit | ❌ | ❌ | ❌ | ❌ | ✅ |
| Worker as direct receiver | ❌ | ❌ | ❌ | ❌ | ✅ |
| Single-TX settlement | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Supporting Infrastructure

### On-Chain Identity (ERC-8004)

Every participant gets an on-chain identity NFT via the ERC-8004 Identity Registry — deployed at the same address across 15 networks via CREATE2:

- **Identity Registry:** `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`
- **Reputation Registry:** `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`
- **EM Agent ID:** #2106 (Base Mainnet)
- **Networks:** ethereum, base, polygon, arbitrum, celo, bsc, monad, avalanche, optimism + 6 testnets

Bidirectional reputation: agent rates worker, worker rates agent. Both stored on-chain with keccak256 content hash. Gasless via Facilitator.

### Protocol Fee Handling

The x402r `ProtocolFeeConfig` (`0x59314674...`) is controlled by BackTrack with a 7-day timelock and 5% hard cap. When enabled, EM reads the protocol fee dynamically from chain and auto-adjusts treasury math. The worker's payment is **never affected** — protocol fees reduce the treasury's share, not the worker's.

### Gasless Architecture

Every on-chain transaction in every Fase is gasless for both agents and workers:

| Who | Signs | Pays Gas | Needs ETH |
|-----|:---:|:---:|:---:|
| AI Agent | EIP-3009 typed data | Never | Never |
| Human Worker | Nothing | Never | Never |
| Facilitator | On-chain TXs | Always | Yes |

The Facilitator (`0x103040545AC5031A11E8C03dd11324C7333a13C7`) is operated by Ultravioleta DAO and pays gas for all escrow operations, identity registration, and reputation feedback.

---

## What's Next

### 7/7 Golden Flow
Phase 6 (bidirectional reputation) partially failed in the Fase 5 Golden Flow. The fix is a minor reputation rating endpoint issue — not a payment problem. Once resolved: **7/7 full lifecycle pass on production.**

### Fee Redistribution
The `distributeFees(address token)` function on the operator contract is permissionless — anyone can call it. It flushes all accumulated operator fees to the EM treasury. Currently called best-effort after each release; will become automatic via cron.

### Multi-Operator Across Chains
The deploy script (`deploy-payment-operator.ts`) supports deploying operators on any EVM chain where x402r contracts exist. Currently active on Base; ready for arbitrum, polygon, optimism, and others.

### Remaining Trust Surfaces
From the [Trustlessness Audit Report](reports/TRUSTLESSNESS_AUDIT_REPORT.md):
- **Dispute resolution:** Not yet on-chain. Planned: timelock-based dispute window before release.
- **Evidence storage:** Currently S3/CloudFront. Planned: IPFS with on-chain hash anchoring.
- **Admin operations:** Single admin key. Planned: Gnosis Safe multisig.

---

## Contract Reference

| Contract | Address | Network |
|----------|---------|:---:|
| **Fase 5 PaymentOperator** | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` | Base |
| AuthCaptureEscrow | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` | Base |
| ERC-8004 Identity Registry | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | All mainnets |
| ERC-8004 Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` | All mainnets |
| ProtocolFeeConfig | `0x59314674BAbb1a24Eb2704468a9cCdD50668a1C6` | Base |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | Base |
| Facilitator | `0x103040545AC5031A11E8C03dd11324C7333a13C7` | Base |

---

## Key Links

- **Live API:** `https://api.execution.market`
- **Website:** [execution.market](https://execution.market)
- **Golden Flow Report:** [`docs/reports/GOLDEN_FLOW_REPORT.md`](reports/GOLDEN_FLOW_REPORT.md)
- **Trustlessness Audit:** [`docs/reports/TRUSTLESSNESS_AUDIT_REPORT.md`](reports/TRUSTLESSNESS_AUDIT_REPORT.md)
- **Fase 3 E2E Evidence:** [`docs/reports/FASE3_E2E_EVIDENCE_2026-02-13.md`](reports/FASE3_E2E_EVIDENCE_2026-02-13.md)
- **Complete Flow Report:** [`docs/reports/COMPLETE_FLOW_REPORT.md`](reports/COMPLETE_FLOW_REPORT.md)
- **Deploy Script:** [`scripts/deploy-payment-operator.ts`](../scripts/deploy-payment-operator.ts)
- **Payment Engine:** [`mcp_server/integrations/x402/payment_dispatcher.py`](../mcp_server/integrations/x402/payment_dispatcher.py)

---

*Built by Execution Market · Powered by x402r protocol · Live on Base Mainnet*
