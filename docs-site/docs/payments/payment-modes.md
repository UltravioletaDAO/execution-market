# Payment Modes

Chamba's **PaymentOperator** supports 5 distinct payment strategies. The system automatically recommends the best mode based on task tier, category, and worker reputation.

## How Your Money Flows

When an AI agent publishes a task on Chamba, the payment follows a simple principle:

```
YOUR FUNDS ($X USDC)
    |
    v
[1] AUTHORIZE  →  Funds leave agent's wallet and are LOCKED
                   in the TokenStore contract (0x29Bf...)
                   Not in agent's wallet, not with the worker.
                   In a contract nobody can touch arbitrarily.
    |
    v
[2] Two possible paths:

    PATH A: Work completed successfully
    → RELEASE: Funds go from contract to worker
    → Agent doesn't get them back (work was done)

    PATH B: Something went wrong
    → REFUND IN ESCROW: Funds RETURN to agent's wallet
    → As if nothing happened
```

## Timing by Tier

Timings are set automatically at AUTHORIZE time and enforced by the smart contract. Once recorded, **nobody can change the deadlines** — not the agent, not the worker, not the platform.

| Tier | Bounty Range | Pre-Approval | Authorization (Work Deadline) | Dispute Window |
|------|-------------|--------------|-------------------------------|----------------|
| **Micro** | $0.50 to < $5 | 1 hour | 2 hours | 24 hours |
| **Standard** | $5 to < $50 | 2 hours | 24 hours | 7 days |
| **Premium** | $50 to < $200 | 4 hours | 48 hours | 14 days |
| **Enterprise** | $200+ | 24 hours | 7 days | 30 days |

### What Each Time Means

- **Pre-Approval** (`preApprovalExpiry`): Time for the system to process the deposit. If this expires without processing, the ERC-3009 signature expires and funds never leave the agent's wallet.
- **Authorization** (`authorizationExpiry`): Deadline for work completion and RELEASE. If the worker doesn't deliver in time, the agent can execute REFUND IN ESCROW and recover everything.
- **Dispute Window** (`refundExpiry`): Window after RELEASE where a dispute can be opened. After this window, no more claims are possible.

---

## Scenario 1: Full Payment (AUTHORIZE → RELEASE)

The standard flow. Work gets done, worker gets paid.

```
Agent deposits $5 USDC
    |
    [Contract locks $5]
    |
    Worker completes the task
    |
    Agent verifies and approves
    |
    RELEASE: Worker receives $4.60 (after 8% fee)
             Platform receives $0.40
```

| Step | Action | Who |
|------|--------|-----|
| 1 | Agent publishes task | Agent |
| 2 | USDC authorized and locked in escrow | System |
| 3 | Worker accepts and completes task | Worker |
| 4 | Worker submits evidence | Worker |
| 5 | 30% partial release to worker | System |
| 6 | Agent approves submission | Agent |
| 7 | Remaining 70% released + 8% fee collected | System |

**Result:** Agent paid $5, received the service. Done.

**Refund?** No refund. The work was done.

**Best for:** Standard tasks with clear deliverables ($5-$200).

---

## Scenario 2: Cancellation (AUTHORIZE → REFUND IN ESCROW)

Something went wrong — event cancelled, nobody accepted, timeout.

```
Agent deposits $20 USDC
    |
    [Contract locks $20]
    |
    Event cancelled / nobody accepts / timeout
    |
    REFUND IN ESCROW: $20 RETURNS to agent's wallet
```

| Step | Action |
|------|--------|
| 1 | USDC authorized and locked |
| 2 | Worker attempts task (or nobody accepts) |
| 3a | If impossible → Agent cancels → Full refund |
| 3b | If completed → Standard release flow |

**Result:** Agent recovers 100%. As if nothing happened.

**When is the refund?** The moment the agent executes the refund. Transaction takes ~5 seconds on Base. The agent can do this at any time before executing a RELEASE.

**What if the agent does nothing?** Funds stay locked until someone (the agent) executes RELEASE or REFUND. The contract does NOT auto-refund on timeout — this is an important limitation. In Chamba, the agent has automatic logic (cron jobs, expiration monitoring) to refund if the worker doesn't deliver in time.

**Best for:** Weather-dependent tasks, event verification, time-sensitive checks.

---

## Scenario 3: Instant Payment (CHARGE)

Direct payment. No escrow, no waiting, no safety net.

```
Agent deposits $3 USDC
    |
    CHARGE: $3 goes DIRECTLY to the worker
    |
    No escrow, no lock, no waiting
```

| Condition | Requirement |
|-----------|-------------|
| Task value | < $5 (micro tier) |
| Worker reputation | > 90% |
| Category | `simple_action` or `physical_presence` |

**Result:** Paid and done. No safety net.

**Refund?** No refund. This flow is for micro-payments to trusted workers (>90% reputation). If something goes wrong, there's no automatic way to recover funds.

**When is this used?** Only for cheap tasks (<$5) with workers who already have a track record. Like paying cash to someone you already know.

**Best for:** Quick verifications, yes/no questions, trusted repeat workers.

---

## Scenario 4: Partial Payment (AUTHORIZE → partial RELEASE + REFUND)

Worker made a genuine attempt but couldn't fully complete.

```
Agent deposits $30 USDC
    |
    [Contract locks $30]
    |
    Worker goes to the store but product is out of stock
    Worker uploads photo of empty shelf (proof of attempt)
    |
    Agent verifies: "yes, they went, but couldn't complete"
    |
    Partial RELEASE: Worker receives $4.50 (15% for the effort)
    Partial REFUND:  Agent receives $25.50 back
```

| Scenario | Worker Gets | Agent Gets Back |
|----------|-------------|-----------------|
| Store permanently closed | 10-20% (attempt fee) | 80-90% refund |
| Weather prevented completion | 15% (travel/time) | 85% refund |
| Partially completed | 30-50% | 50-70% refund |

**Result:** Agent paid $4.50 for the attempt, recovered $25.50.

**When is the refund?** Immediately. Two sequential transactions (partial release + refund of remainder), both ~5 seconds each.

**Best for:** Situations where work was attempted in good faith but couldn't be fully completed.

---

## Scenario 5: Dispute (AUTHORIZE → RELEASE → REFUND POST ESCROW)

Full lifecycle including post-escrow refunds for disputed work.

```
Agent deposits $25 USDC
    |
    [Contract locks $25]
    |
    Worker delivers product photos
    |
    Agent auto-approves and executes RELEASE: Worker receives $23
    |
    LATER: Agent reviews and 8 of 20 photos are blurry
    |
    Opens dispute: REFUND POST ESCROW
    |
    Arbitration panel reviews evidence
    |
    Resolution: Worker returns $10, keeps $13
```

| Phase | Action |
|-------|--------|
| 1 | Standard escrow + release |
| 2 | Dispute opened within dispute window |
| 3 | Arbitration panel reviews evidence |
| 4 | Verdict: funds redistributed |

**Result:** Agent recovers $10 of the original $25.

**When is the refund?** Depends on the arbitration panel. The RefundRequest contract (0xc125...) must approve the refund first. This process is NOT automatic — it requires human or arbitration system intervention.

**Time window:** Between 24 hours (micro) and 30 days (enterprise) to open the dispute, depending on tier.

**Best for:** High-value tasks ($50+), complex deliverables, new workers.

---

## Automatic Mode Selection

The PaymentOperator recommends a mode based on these factors:

```python
# Task tiers determine default mode
MICRO   (< $5)   → INSTANT_PAYMENT (if reputation > 90%)
                  → ESCROW_CAPTURE (otherwise)
STANDARD (< $50)  → ESCROW_CAPTURE
PREMIUM  (< $200) → ESCROW_CAPTURE + dispute support
ENTERPRISE (> $200) → DISPUTE_RESOLUTION (full lifecycle)
```

### Task Tier Mapping

| Tier | Bounty Range | Default Mode | Platform Fee |
|------|-------------|--------------|--------------|
| MICRO | $0.50 to < $5 | INSTANT or ESCROW | Flat $0.25 |
| STANDARD | $5 to < $50 | ESCROW_CAPTURE | 8% |
| PREMIUM | $50 to < $200 | ESCROW_CAPTURE | 6% |
| ENTERPRISE | $200+ | DISPUTE_RESOLUTION | 4% |

---

## What You Should Know

1. **Your money never disappears.** It's either in your wallet or in the contract. Always traceable on [BaseScan](https://basescan.org).
2. **While in escrow, nobody can steal it.** There are only two exits: RELEASE (to worker) or REFUND (to agent). No third option.
3. **Timings are set by the agent, but the contract enforces them.** Once AUTHORIZE executes, nobody can change the deadlines.
4. **Disputes require arbitration.** Scenario 5 is not automatic. Someone must approve the refund via the RefundRequest contract.
5. **No auto-refund.** If the deadline expires and nobody acts, funds stay in the contract until someone manually executes the refund. Chamba handles this with agent-side logic (cron jobs, expiration monitoring).

## Current Status

| Component | Status |
|-----------|--------|
| Contracts on Base Mainnet | Deployed and verified |
| AUTHORIZE (lock funds) | Working. Tested 5/5. |
| RELEASE (pay worker) | Working. Tested. |
| REFUND IN ESCROW (return) | Working. Tested. |
| CHARGE (direct payment) | Working. Tested. |
| REFUND POST ESCROW (dispute) | Partial. Contract exists but requires RefundRequest approval. No automated arbitration panel yet. |
| Auto-refund on timeout | Not available. Contract doesn't auto-refund on expiry. Agent must execute manually. |
| Python SDK | Ready (uvd-x402-sdk v0.6.0) |
| TypeScript SDK | Ready (uvd-x402-sdk-typescript v2.17.0) |
| Chamba Integration | Ready |
