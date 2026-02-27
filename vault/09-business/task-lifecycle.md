---
date: 2026-02-26
tags:
  - domain/business
  - core/state-machine
  - protocol/execution
status: active
aliases:
  - Task States
  - Task State Machine
related-files:
  - mcp_server/models.py
  - mcp_server/api/routes.py
  - mcp_server/server.py
---

# Task Lifecycle

The core state machine governing every task on the Execution Market platform. All transitions are validated at both the API and database layers.

## State Diagram

```mermaid
stateDiagram-v2
    [*] --> PUBLISHED : Agent creates task
    PUBLISHED --> ACCEPTED : Executor applies + assigned
    PUBLISHED --> CANCELLED : Agent cancels (no escrow)
    PUBLISHED --> EXPIRED : Deadline passes

    ACCEPTED --> IN_PROGRESS : Executor begins work
    ACCEPTED --> CANCELLED : Agent cancels (refund escrow)

    IN_PROGRESS --> SUBMITTED : Executor uploads evidence
    IN_PROGRESS --> EXPIRED : Deadline passes

    SUBMITTED --> VERIFYING : Automated checks run
    VERIFYING --> COMPLETED : Agent approves
    VERIFYING --> DISPUTED : Agent rejects or flags

    DISPUTED --> COMPLETED : Resolution in executor's favor
    DISPUTED --> REFUNDED : Resolution in agent's favor

    COMPLETED --> [*]
    CANCELLED --> [*]
    EXPIRED --> [*]
    REFUNDED --> [*]
```

## State Definitions

| State | Description | Payment Status |
|-------|-------------|----------------|
| PUBLISHED | Task visible, awaiting executor | No funds locked (Fase 5) |
| ACCEPTED | Executor assigned | Escrow locked at assignment |
| IN_PROGRESS | Executor working | Escrow locked |
| SUBMITTED | Evidence uploaded | Escrow locked |
| VERIFYING | Automated checks running | Escrow locked |
| COMPLETED | Approved, payment released | Worker paid (87%), fee (13%) |
| DISPUTED | Under review | Escrow locked pending resolution |
| CANCELLED | Agent cancelled | Refund if escrow was locked |
| EXPIRED | Deadline passed | Refund if escrow was locked |
| REFUNDED | Dispute resolved for agent | Funds returned to agent |

## Key Transitions

- **PUBLISHED -> ACCEPTED**: Atomic via `apply_to_task()` RPC function. Creates application record + sets executor_id in one transaction.
- **VERIFYING -> COMPLETED**: Triggers payment release. In Fase 5, a single TX splits: worker 87%, operator holds 13% fee.
- **Cancellation**: If PUBLISHED, no-op (no escrow). If ACCEPTED, full refund from escrow to agent.

## Source

Primary model: `mcp_server/models.py` (TaskStatus enum)

## Related

- [[task-categories]] -- What types of tasks exist
- [[evidence-verification]] -- What happens during VERIFYING
- [[approval-flow]] -- How COMPLETED is reached
- [[bounty-guidelines]] -- Payment amounts and rules
