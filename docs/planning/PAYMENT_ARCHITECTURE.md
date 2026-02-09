# Payment Architecture — Execution Market

> Last updated: 2026-02-06 | SDK: uvd-x402-sdk v0.8.1

## Payment Flow Overview

All payments are **gasless** via the Ultravioleta Facilitator. The facilitator pays gas on Base; agents and the platform only sign EIP-3009 authorizations.

### Current Flow (MVP — has D14 gap)

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Fac as Facilitator
    participant PW as Platform Wallet<br/>0xD386...
    participant Worker as Worker Wallet
    participant Treasury as EM Treasury<br/>0xae07...

    Note over Agent,Treasury: Task Creation
    Agent->>MCP: POST /api/v1/tasks + X-Payment header
    MCP->>Fac: POST /verify (agent's EIP-3009 auth)
    Fac-->>MCP: isValid: true, payer: agent
    MCP->>MCP: Store X-Payment in task.escrow_tx
    MCP-->>Agent: 201 Created (task_id)

    Note over Agent,Treasury: Worker Applies & Submits
    Worker->>MCP: POST /tasks/{id}/apply
    Worker->>MCP: POST /tasks/{id}/submit + evidence

    Note over Agent,Treasury: Approval & Payment (current: D14 gap)
    Agent->>MCP: POST /submissions/{id}/approve
    Note right of MCP: agent's original auth<br/>is NEVER settled!
    MCP->>PW: Sign EIP-3009 (PW → Worker, 92%)
    MCP->>Fac: POST /settle (PW → Worker)
    Fac->>Worker: USDC transfer (gasless)
    Fac-->>MCP: tx_hash (worker payout)
    MCP->>PW: Sign EIP-3009 (PW → Treasury, 8%)
    MCP->>Fac: POST /settle (PW → Treasury)
    Fac->>Treasury: USDC transfer (gasless)
    Fac-->>MCP: tx_hash (fee)
    MCP-->>Agent: 200 OK {tx_hash, fee_tx_hash}
```

### Correct Flow (after D14 fix)

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCP Server
    participant Fac as Facilitator
    participant PW as Platform Wallet<br/>0xD386...
    participant Worker as Worker Wallet

    Note over Agent,Worker: Task Creation (same as current)
    Agent->>MCP: POST /api/v1/tasks + X-Payment header
    Note right of Agent: auth.to = Platform Wallet
    MCP->>Fac: POST /verify
    Fac-->>MCP: isValid: true
    MCP->>MCP: Store X-Payment in task.escrow_tx

    Note over Agent,Worker: Approval & Payment (correct flow)
    Agent->>MCP: POST /submissions/{id}/approve

    rect rgb(200, 255, 200)
        Note over MCP,Fac: Step 1: Settle agent's original auth
        MCP->>Fac: POST /settle (Agent → PW, full bounty)
        Fac->>PW: USDC transfer (agent pays platform)
        Fac-->>MCP: tx_hash (agent settlement)
    end

    rect rgb(200, 220, 255)
        Note over MCP,Worker: Step 2: Disburse to worker
        MCP->>PW: Sign EIP-3009 (PW → Worker, bounty - fee)
        MCP->>Fac: POST /settle (PW → Worker)
        Fac->>Worker: USDC transfer (gasless)
        Fac-->>MCP: tx_hash (worker payout)
    end

    Note over PW: Fee (8%) stays in<br/>Platform Wallet
    MCP-->>Agent: 200 OK {tx_hash, fee_tx_hash}
```

## Key Constraints

### EIP-3009 TransferWithAuthorization
- The `to` address is **cryptographically sealed** in the EIP-712 signature
- Cannot be changed after signing
- The facilitator **validates** `payTo == auth.to` — rejects mismatches

### Facilitator Rules
- `POST /verify`: Validates signature, does NOT move funds
- `POST /settle`: Executes on-chain transfer, facilitator pays gas
- Request format: V1 envelope with amounts/timestamps as **strings**
- OFAC + custom blacklist screening on all operations

## Wallet Map

```mermaid
graph LR
    subgraph "Execution Market Wallets"
        PW["Platform Wallet<br/>0xD386...<br/>(signs disbursements)"]
        TR["EM Treasury<br/>0xae07...<br/>(fee collection)"]
    end

    subgraph "External"
        AG["Agent Wallet<br/>(varies per agent)"]
        WK["Worker Wallet<br/>(varies per worker)"]
    end

    AG -->|"1. Full bounty<br/>(settle original auth)"| PW
    PW -->|"2. Bounty - fee<br/>(new EIP-3009)"| WK
    PW -.->|"Optional: transfer fees"| TR

    style PW fill:#4CAF50,color:white
    style TR fill:#FF9800,color:white
    style AG fill:#2196F3,color:white
    style WK fill:#9C27B0,color:white
```

| Wallet | Address | Purpose | Env Var |
|--------|---------|---------|---------|
| Platform (prod) | `0xD3868E1eD738CED6945A574a7c769433BeD5d474` | Signs worker payouts & fee collection | `em/x402:PRIVATE_KEY` |
| Platform (dev) | `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd` | Local testing | `.env.local:WALLET_PRIVATE_KEY` |
| EM Treasury | `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad` | Fee accumulation | `em/commission:wallet_address` |

## Task Lifecycle & Payment States

```mermaid
stateDiagram-v2
    [*] --> PUBLISHED: Agent creates task<br/>+ X-Payment verified

    PUBLISHED --> ACCEPTED: Worker applies
    PUBLISHED --> CANCELLED: Agent cancels<br/>(auth expires, no funds moved)
    PUBLISHED --> EXPIRED: Deadline passes

    ACCEPTED --> IN_PROGRESS: Worker starts
    ACCEPTED --> CANCELLED: Agent cancels

    IN_PROGRESS --> SUBMITTED: Worker uploads evidence

    SUBMITTED --> VERIFYING: AI review (if configured)
    SUBMITTED --> COMPLETED: Agent approves<br/>→ settle + disburse

    VERIFYING --> COMPLETED: Agent approves
    VERIFYING --> DISPUTED: Agent rejects

    DISPUTED --> COMPLETED: Resolution (pay worker)
    DISPUTED --> CANCELLED: Resolution (refund agent)

    COMPLETED --> [*]
    CANCELLED --> [*]
    EXPIRED --> [*]
```

## Escrow States

```mermaid
stateDiagram-v2
    [*] --> AUTHORIZED: Agent's EIP-3009 auth verified<br/>(no funds moved yet)

    AUTHORIZED --> RELEASED: Task approved<br/>→ settle agent auth<br/>→ disburse to worker
    AUTHORIZED --> CANCELLED: Task cancelled<br/>(auth expires naturally)
    AUTHORIZED --> EXPIRED: Auth validBefore passes

    RELEASED --> [*]: Worker paid on-chain
    CANCELLED --> [*]: No funds moved
    EXPIRED --> [*]: No funds moved

    note right of AUTHORIZED: Current gap (D14):<br/>auth never settled,<br/>platform pays from own wallet
```

## Fee Calculation

```
Bounty:       $X.XX (set by agent at task creation)
Platform Fee: $X.XX * 8% = $Y.YY  (EM_PLATFORM_FEE env var, default 0.08)
Worker Payout: $X.XX - $Y.YY

Example: $1.00 bounty
  → Worker receives: $0.92
  → Platform keeps:  $0.08
```

For MVP launch, commission can be set to 0% via `EM_PLATFORM_FEE=0.00`.

## SDK Usage (v0.8.1)

```python
from uvd_x402_sdk import X402Client

client = X402Client(recipient_address="0xD386...")

# Verify (task creation) — no funds move
payload = client.extract_payload(x_payment_header)
verify = client.verify_payment(payload, Decimal("1.00"))

# Settle to default recipient (task approval step 1)
settle = client.settle_payment(payload, Decimal("1.00"))

# Settle to custom address (worker disbursement)
settle = client.settle_payment(payload, Decimal("0.92"), pay_to="0xWorker...")
```

## Open Issues

| ID | Description | Severity | Status |
|----|-------------|----------|--------|
| D14 | Agent's auth never settled — platform pays from own wallet | HIGH | OPEN |
| D01 | Self-payment bug (compares wallet vs API key ID) | HIGH | OPEN |
| D02 | `payments` table missing in live DB | MEDIUM | OPEN |
| D13 | On-chain splitter contract for automated fee split | FUTURE | OPEN |
| D09 | Funded escrow refund (AdvancedEscrowClient) | FUTURE | OPEN |
