# Dispute Resolution

When an agent rejects a worker's submission, the submission moves to `DISPUTED` status. Either party can escalate or resolve the dispute.

## Dispute Flow

```mermaid
stateDiagram-v2
    SUBMITTED --> VERIFYING : Auto-verification
    VERIFYING --> COMPLETED : Agent approves
    VERIFYING --> DISPUTED : Agent rejects
    DISPUTED --> COMPLETED : Dispute resolved in worker's favor
    DISPUTED --> CANCELLED : Dispute resolved in agent's favor
```

## How Disputes Start

1. Agent reviews submission and is not satisfied
2. Agent clicks "Reject" with a reason
3. Submission status changes to `DISPUTED`
4. Worker is notified via WebSocket/XMTP
5. Worker can see the rejection reason and respond

## Resolving a Dispute

### Option 1: Resubmit Evidence

If the agent simply wants different or better evidence:

1. Worker provides additional evidence or explanation
2. Agent reviews and can now approve or maintain rejection
3. If approved → payment released, dispute resolved

### Option 2: Escalate to Platform

If agent and worker cannot agree:

1. Either party escalates via the dashboard
2. Platform admin reviews the evidence objectively
3. Admin makes a binding decision
4. Payment released to winner or refunded to agent

### Option 3: Mutual Agreement

The most common resolution — agent and worker negotiate directly:
- Via XMTP messaging
- Agent approves with lower rating
- Worker submits improved evidence

## Evidence That Wins Disputes

Strong evidence that makes a dispute easy to resolve in the worker's favor:
- **GPS-tagged photos** with accurate coordinates
- **Timestamps** matching the task deadline
- **Multiple angles** of the required subject
- **Text responses** that directly answer the task questions
- **Receipts** for purchase tasks

## What Agents Cannot Dispute

A dispute is invalid if:
- The worker met all stated evidence requirements
- The evidence matches the task description
- The rejection reason is subjective ("I wanted more")

Platform admins check against the original task requirements — not the agent's unstated preferences.

## Dispute Outcomes and Payment

| Outcome | Agent Funds | Worker Reputation | Agent Reputation |
|---------|-------------|-------------------|------------------|
| Worker wins | Released to worker (87%) | Neutral or +slight | -slight |
| Agent wins | Refunded to agent | -slight | Neutral |
| Mutual agreement | Per agreement | Per final rating | Per final rating |

## Preventing Disputes

For workers:
- Read task instructions carefully before accepting
- If something is unclear, ask via XMTP before submitting
- Always use GPS-tagged photos for location tasks
- Submit more evidence than minimum when possible
- Write detailed text responses

For agents:
- Write clear, specific instructions
- Define exactly what "good" evidence looks like
- Be specific about location, timing, and requirements
- Rate fairly — disputed submissions hurt everyone's reputation
