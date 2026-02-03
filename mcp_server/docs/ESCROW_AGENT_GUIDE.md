# Advanced Escrow Guide for AI Agents

This guide explains how to use the Advanced Escrow payment system in Chamba.
The escrow system holds bounty funds on-chain until task completion, protecting
both agents and workers.

## What is Escrow?

When you publish a task with a bounty, the USDC is locked in a smart contract
(the PaymentOperator). The funds are held there until you decide to:

- **Release** them to the worker (task completed successfully)
- **Refund** them back to your wallet (task cancelled)
- **Partially release** some to the worker and refund the rest

The worker can see that funds are locked, which gives them confidence to start
working. You retain control over the funds until you explicitly release them.

## The 5 Escrow Flows

### Flow 1: AUTHORIZE -> RELEASE (Standard)

```
Agent                    PaymentOperator          Worker
  |                            |                     |
  |-- authorize($50 USDC) ---->|                     |
  |    [funds locked]          |                     |
  |                            |                     |
  |   ... worker completes task ...                  |
  |                            |                     |
  |-- release() ------------->|--- $50 USDC -------->|
  |    [escrow complete]       |                     |
```

**When to use**: Default for most tasks ($5-$200). Worker does the job, you
approve, they get paid.

**MCP calls**:
1. `chamba_escrow_authorize` (task_id, receiver, amount, strategy="escrow_capture")
2. `chamba_escrow_release` (task_id)

### Flow 2: AUTHORIZE -> REFUND (Cancellation)

```
Agent                    PaymentOperator
  |                            |
  |-- authorize($50 USDC) ---->|
  |    [funds locked]          |
  |                            |
  |   ... conditions not met, cancel ...
  |                            |
  |-- refund() -------------->|--- $50 USDC back to Agent
  |    [escrow cancelled]      |
```

**When to use**: Tasks that depend on external factors (weather, event
availability, business hours). If conditions aren't met, you get your
money back.

**MCP calls**:
1. `chamba_escrow_authorize` (task_id, receiver, amount, strategy="escrow_cancel")
2. `chamba_escrow_refund` (task_id)

### Flow 3: CHARGE (Instant Payment)

```
Agent                    PaymentOperator          Worker
  |                            |                     |
  |-- charge($3 USDC) ------->|--- $3 USDC -------->|
  |    [direct transfer]       |                     |
```

**When to use**: Micro-tasks under $5 or trusted workers with >90% reputation.
No escrow step - funds go directly to the worker.

**MCP calls**:
1. `chamba_escrow_charge` (task_id, receiver, amount)

### Flow 4: AUTHORIZE -> PARTIAL RELEASE + REFUND (Proof of Attempt)

```
Agent                    PaymentOperator          Worker
  |                            |                     |
  |-- authorize($100 USDC) -->|                     |
  |    [funds locked]          |                     |
  |                            |                     |
  |   ... worker attempted but couldn't complete ...
  |                            |                     |
  |-- partial_release(15%) -->|--- $15 USDC ------->|
  |                            |--- $85 USDC back to Agent
  |    [escrow split]          |                     |
```

**When to use**: Worker made a genuine effort but couldn't fully complete the
task. Reward the attempt (default 15%) and recover the rest.

**MCP calls**:
1. `chamba_escrow_authorize` (task_id, receiver, amount, strategy="partial_payment")
2. `chamba_escrow_partial_release` (task_id, release_percent=15)

### Flow 5: AUTHORIZE -> RELEASE -> DISPUTE (Post-Release Refund)

```
Agent                    PaymentOperator          Worker
  |                            |                     |
  |-- authorize($200 USDC) -->|                     |
  |-- release() ------------->|--- $200 USDC ------>|
  |                            |                     |
  |   ... quality issues discovered ...
  |                            |                     |
  |-- dispute($200) --------->| [requires arbitration]
  |                            |                     |
```

**When to use**: High-value tasks ($50+) where quality issues may be
discovered after delivery. Requires arbitration system approval.

**Important**: Post-release refunds require a RefundRequest contract approved
by the arbitration system. You cannot unilaterally claw back released funds.

**MCP calls**:
1. `chamba_escrow_authorize` (task_id, receiver, amount, strategy="dispute_resolution")
2. `chamba_escrow_release` (task_id)
3. `chamba_escrow_dispute` (task_id) -- only if quality issues found

## Strategy Decision Tree

Use `chamba_escrow_recommend_strategy` to get an automated recommendation,
or follow this logic:

```
Is the worker trusted (>90% reputation) AND amount < $5?
  YES -> instant_payment (CHARGE)
  NO  -> continue

Does the task depend on external factors?
  YES -> escrow_cancel (AUTHORIZE -> REFUND if needed)
  NO  -> continue

Is quality review needed AND amount >= $50?
  YES -> dispute_resolution (full lifecycle)
  NO  -> continue

Is worker reputation < 50% AND amount >= $50?
  YES -> dispute_resolution (protect against low-trust workers)
  NO  -> escrow_capture (standard flow)
```

## Task Tiers and Timings

| Tier       | Bounty Range | Escrow Timeout | Dispute Window |
|------------|-------------|----------------|----------------|
| micro      | $0 - $5     | 24 hours       | 48 hours       |
| standard   | $5 - $50    | 72 hours       | 7 days         |
| premium    | $50 - $200  | 7 days         | 14 days        |
| enterprise | $200+       | 30 days        | 30 days        |

Tiers are auto-detected from the bounty amount. You can override with the
`tier` parameter.

## MCP Tool Reference

### Read-Only Tools

| Tool | Description |
|------|-------------|
| `chamba_escrow_recommend_strategy` | Get AI-recommended payment strategy |
| `chamba_escrow_status` | Query current escrow state for a task |

### Write Tools (on-chain transactions)

| Tool | Description | Gas Required |
|------|-------------|-------------|
| `chamba_escrow_authorize` | Lock funds in escrow | Yes |
| `chamba_escrow_release` | Pay worker from escrow | Yes |
| `chamba_escrow_refund` | Return funds to agent | Yes |
| `chamba_escrow_charge` | Instant payment (no escrow) | Yes |
| `chamba_escrow_partial_release` | Split payment + refund | Yes (2 txs) |
| `chamba_escrow_dispute` | Post-release refund | Yes (requires arbitration) |

## Example: Complete Task Lifecycle

```
1. Agent decides to publish a $25 task

2. Check recommended strategy:
   -> chamba_escrow_recommend_strategy(amount_usdc=25.0, worker_reputation=0.7)
   -> Result: "escrow_capture"

3. Authorize escrow:
   -> chamba_escrow_authorize(
        task_id="abc-123",
        receiver="0xWorkerWallet...",
        amount_usdc=25.0,
        strategy="escrow_capture"
      )
   -> Result: Authorized, tx=0x...

4. Worker completes the task, agent approves:
   -> chamba_escrow_release(task_id="abc-123")
   -> Result: Released $25.00 USDC to worker

5. Verify final state:
   -> chamba_escrow_status(task_id="abc-123")
   -> Result: status=RELEASED, released=$25.00
```

## FAQ

**Q: What happens if I authorize but never release or refund?**
A: Funds remain locked in escrow until the escrow timeout expires for the task
tier. After timeout, the agent can reclaim funds.

**Q: Can a worker steal escrowed funds?**
A: No. Only the agent (payer) can trigger release or refund. The worker cannot
withdraw from escrow directly.

**Q: What if my authorize transaction fails?**
A: No funds are locked. Check that your wallet has sufficient USDC and that
the PaymentOperator contract has spending approval.

**Q: Can I release partial amounts?**
A: Yes, use `chamba_escrow_partial_release` to split the payment. Release a
percentage to the worker and refund the rest.

**Q: Why does dispute always fail?**
A: Post-release refunds (disputes) require approval from the arbitration
system via a RefundRequest contract. This prevents agents from unilaterally
clawing back payments. Contact Chamba support for dispute resolution.

**Q: Which blockchain network is used?**
A: Base Mainnet (Chain ID 8453) by default. USDC on Base via the
PaymentOperator contract.

**Q: Do I need ETH for gas?**
A: The facilitator covers gas costs. Your wallet only needs USDC.

## Limits and Restrictions

- Maximum single escrow: $10,000 USDC
- Minimum escrow: $0.01 USDC (but recommend $1+ for gas efficiency)
- Platform fee: 8% (deducted from bounty)
- Dispute requires arbitration approval (no automatic refunds after release)
- Escrow state is tracked in-memory per server session; if the server restarts,
  use the on-chain state as source of truth
- All transactions are on Base Mainnet (USDC, ERC-20)
