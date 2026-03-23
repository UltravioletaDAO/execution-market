---
date: 2026-03-23
tags:
  - type/adr
  - domain/payments
  - domain/security
status: active
aliases:
  - Payment Architecture v2
  - Escrow Redesign
related-files:
  - mcp_server/integrations/x402/payment_dispatcher.py
  - mcp_server/api/routers/_helpers.py
  - mcp_server/integrations/x402/sdk_client.py
---

# ADR-001: Payment Architecture v2 — Agent-Signed Escrow

## Status

**ACCEPTED** — 2026-03-23

## Context

During the OpenClaw live transaction debugging session (2026-03-23), we discovered a
fundamental architectural flaw: the EM server was signing escrow operations and
EIP-3009 settlements using `WALLET_PRIVATE_KEY` (the platform wallet) **on behalf of
external agents**. This means EM was acting as a financial intermediary — the platform
wallet was paying for escrows that agents should have funded themselves.

This is wrong for three reasons:

1. **Economic**: Any agent could create tasks and EM would pay for them. Agents get
   free human labor at EM's expense.
2. **Trust model**: EM holds and moves funds on behalf of agents, making it a custodial
   intermediary — the opposite of trustless.
3. **Regulatory**: Acting as a payment intermediary creates compliance obligations EM
   should not have.

A subsequent commit (`ed36874`) attempted to fix this by introducing
`AGENT_WALLET_PRIVATE_KEY` — a separate wallet for "agent operations" vs "platform
operations". This was also wrong: EM is a marketplace, not an agent that buys tasks.
EM does not need an "agent wallet" because EM never purchases services.

## Decision

### Principle: EM never touches funds

The Execution Market server **never signs payment transactions**. The agent who creates
the task is the one who signs. The server only orchestrates (updates DB, verifies
evidence, triggers escrow release). Funds flow directly from agent to escrow to worker
— the platform wallet is never in the payment path.

### Payment mode: Fase 2 escrow only

Fase 1 ("server signs EIP-3009 at approval") is **eliminated** as a production payment
mode. Only Fase 2 (on-chain escrow via x402r + PaymentOperator) is the production path.

Fase 1 remains available **only** when `EM_SERVER_SIGNING=true` is set, for internal
testing by the EM team using the platform wallet from OpenClaw or similar tools.

### Escrow timing: Configurable — two modes

The escrow lock timing is configurable via `EM_ESCROW_TIMING` env var:

| Value | Description | Default? |
|-------|-------------|----------|
| `lock_on_assignment` | Agent signs pre-auth at creation. Lock executes when worker is assigned. | **Yes (default)** |
| `lock_on_creation` | Agent signs and locks escrow immediately at task creation. | No |

Both modes are fully agent-signed. The server never signs payments in either mode.
Agents can also signal their preferred mode via the `X-Escrow-Timing` request header
when creating a task, overriding the server default per-task.

---

## Mode A: Lock on Creation (`lock_on_creation`)

```
AGENT CREATES TASK (T=0, deadline=T+24h)
|
+-- Agent signs EIP-3009 authorization
|     from: agent wallet
|     to:   escrow contract
|     value: bounty amount (e.g., $5.00 USDC)
|
+-- Agent sends signed auth with task creation request
|     Header: X-Payment-Auth (signed EIP-3009)
|
+-- Server forwards auth to Facilitator immediately
|     POST /lock with:
|       - auth signature
|       - operator address (PaymentOperator for fee split)
|       - receiver: ZERO_ADDRESS (no worker yet)
|
+-- Facilitator executes on-chain:
|     transferWithAuthorization() -> funds move to escrow NOW
|
+-- Task status: PUBLISHED
|     escrow_status: locked (no receiver yet)
|
+-- If lock FAILS (insufficient balance, bad signature):
|     - Task creation rejected with 402 Payment Required
|     - Agent notified: "Escrow lock failed — check balance and signature"
|
|
WORKER ASSIGNED (T+N hours)
|
+-- NO escrow operation
|     Escrow already locked. Server only updates receiver:
|     Facilitator: POST /update-receiver (or handled at release time)
|
+-- Task status: ACCEPTED
|     escrow_status: locked (receiver = worker address)
|
|
APPROVAL
|
+-- Server calls Facilitator: POST /release
|     Worker receives 87%, treasury 13% (same as Mode B)
|
+-- Task status: COMPLETED
|     escrow_status: released
|
|
CANCELLATION
|
+-- If PUBLISHED (locked but no worker):
|     Server calls Facilitator: POST /refund
|     Full bounty returned to agent.
|     (Note: requires on-chain TX even with no worker)
|
+-- If ACCEPTED (locked with worker):
|     Server calls Facilitator: POST /refund
|     Full bounty returned to agent.
|
|
EXPIRATION
|
+-- Always requires refund (funds are locked from creation).
|     Server calls Facilitator: POST /refund
|     Task status: EXPIRED, escrow_status: refunded
```

### When to use Mode A

- High-value tasks where worker trust matters (worker sees funded escrow)
- Agents that want guaranteed commitment (no balance risk at assignment)
- Short-deadline tasks where time between create and assign is minimal
- Tasks where capital lockup cost is low relative to bounty

---

## Mode B: Lock on Assignment (`lock_on_assignment`) — DEFAULT

```
AGENT CREATES TASK (T=0, deadline=T+24h)
|
+-- Agent signs EIP-3009 pre-authorization
|     from: agent wallet
|     to:   escrow contract (known, deterministic per chain)
|     value: bounty amount (e.g., $5.00 USDC)
|     validAfter: 0 (immediate)
|     validBefore: task deadline + 1h buffer
|     nonce: unique per task (keccak256(taskId + "preauth"))
|
+-- Server stores signed pre-auth in DB (escrows table metadata)
|     No funds move. Agent's USDC is still in their wallet.
|
+-- Balance check: advisory balanceOf() to warn if insufficient
|
+-- Task status: PUBLISHED
|     escrow_status: pending_assignment
|
|
WORKER ASSIGNED (T+N hours, where N < deadline)
|
+-- Server sends stored pre-auth to Facilitator
|     POST /lock with:
|       - pre-auth signature
|       - worker address (receiver)
|       - operator address (PaymentOperator for fee split)
|
+-- Facilitator executes on-chain:
|     transferWithAuthorization() -> funds move to escrow
|     Worker set as receiver in PaymentOperator
|
+-- Task status: ACCEPTED
|     escrow_status: locked
|
+-- If pre-auth execution FAILS (insufficient balance, expired):
|     - Task reverts to PUBLISHED (assignment rolled back)
|     - Agent notified: "Escrow lock failed — insufficient balance or expired auth"
|     - Worker released, can apply to other tasks
|
|
WORKER SUBMITS EVIDENCE
|
+-- Normal flow: evidence upload, AI verification, etc.
|     No escrow operations.
|
|
APPROVAL (agent or server approves submission)
|
+-- Server calls Facilitator: POST /release
|     Escrow releases trustlessly (1 TX):
|       - Worker receives 87% (net bounty)
|       - PaymentOperator holds 13% (fee)
|       - distributeFees() flushes fee to treasury
|
+-- Task status: COMPLETED
|     escrow_status: released
|
|
CANCELLATION (before or after assignment)
|
+-- If PUBLISHED (no worker assigned):
|     No-op. Pre-auth was never executed. Nothing to refund.
|     Agent's funds were never locked.
|
+-- If ACCEPTED (worker assigned, escrow locked):
|     Server calls Facilitator: POST /refund
|     Escrow returns full bounty to agent wallet.
|     Task status: CANCELLED
|     escrow_status: refunded
|
|
EXPIRATION (deadline reached, no completion)
|
+-- If PUBLISHED (pre-auth expired, no worker ever assigned):
|     No-op. Pre-auth expired naturally. Zero cost.
|     Task status: EXPIRED
|
+-- If ACCEPTED (escrow locked, worker failed to deliver):
|     Server calls Facilitator: POST /refund
|     Same as cancellation refund.
|     Task status: EXPIRED
|     escrow_status: refunded
```

### Pre-auth validity window

The EIP-3009 `validBefore` timestamp determines how long the pre-authorization is
valid. It MUST cover the entire window during which a worker could be assigned:

```
validBefore = task_deadline + 1_hour_buffer
```

- The buffer accounts for edge cases where assignment happens moments before deadline.
- Once the escrow is locked, `validBefore` is irrelevant — the escrow holds the funds
  and release/refund are separate operations.
- If `validBefore` passes without assignment, the pre-auth expires silently. No funds
  were ever moved. The task is marked EXPIRED by the expiration job.

### Why Option B (pre-auth at creation, lock at assignment) over Option A (lock at creation)

| Factor | Option A (lock at creation) | Option B (pre-auth at creation) |
|--------|---------------------------|-------------------------------|
| Capital efficiency | Bad — funds locked from minute 0, even if no worker for days | Good — funds free until worker commits |
| Agent with 10 tasks | Needs all capital locked upfront | Only pays as workers are assigned |
| Cancel before worker | Requires on-chain refund | Free — no-op, pre-auth unused |
| Worker trust | High — sees locked funds | Medium — sees "pre-authorized" badge |
| Complexity | Simple — one signing moment | Medium — store pre-auth, execute later |
| Industry precedent | Prepaid model | Credit card model (Uber, Airbnb, etc.) |
| Pre-auth expiry risk | None | Low — validBefore = deadline + buffer |
| Balance risk | None — locked upfront | Low — agent could spend between create and assign |

**Option B wins on capital efficiency and cancel cost**, which are the factors that
matter most for agent adoption. The "balance risk" is mitigated by the advisory
balance check at creation and the lock failure handler at assignment.

## What changes

### Removed

| Component | Why |
|-----------|-----|
| `AGENT_WALLET_PRIVATE_KEY` env var | EM is not an agent. No separate agent wallet. |
| `_resolve_payer_wallet()` | Server doesn't choose which wallet to sign with — it doesn't sign at all. |
| `_get_agent_address()` | No agent wallet concept. |
| `_cached_agent_address` global | No agent wallet concept. |
| `_fase2_clients_legacy` dict | Dead code (already removed in audit fix commit). |
| Fase 1 as default payment mode | Server-signed settlements eliminated. |
| "server-managed" settlement path | Server never signs payments in production. |

### Added

| Component | Purpose |
|-----------|---------|
| `EM_SERVER_SIGNING` env var | `true` enables server-side signing for testing. Default: `false` (disabled). In production ECS: not set or `false`. |
| `EM_ESCROW_TIMING` env var | `lock_on_assignment` (default) or `lock_on_creation`. Sets server-wide default. |
| `X-Escrow-Timing` request header | Per-task override: agent can choose `lock_on_creation` or `lock_on_assignment` when creating a task. |
| `X-Payment-Auth` request header | Agent's signed EIP-3009 authorization. Required for both modes. |
| Pre-auth storage in escrows table | `metadata.preauth_signature` stores the agent's signed EIP-3009 (Mode B only; Mode A executes immediately). |
| Pre-auth execution at assignment | Assignment endpoint sends stored pre-auth to Facilitator for lock (Mode B). |
| Lock failure handler | If lock fails (at creation for Mode A, at assignment for Mode B), reject with 402 + rollback. |
| `validBefore` calculation | Mode A: not needed (executes immediately). Mode B: `task.deadline + 3600` (1 hour buffer). |

### Modified

| Component | Change |
|-----------|--------|
| `POST /tasks` (create) | Requires `X-Payment-Auth` header. Mode A: executes lock immediately (402 on failure). Mode B: stores pre-auth, defers lock. Returns 400 if header missing (unless `EM_SERVER_SIGNING=true`). |
| `POST /tasks/{id}/assign` | Mode A: no escrow op (already locked), just updates receiver. Mode B: executes stored pre-auth via Facilitator. On failure: rolls back assignment. |
| `POST /submissions/{id}/approve` | Calls Facilitator release (unchanged, but now escrow was locked with agent's funds, not platform's). |
| `POST /tasks/{id}/cancel` | Mode A: always refund (funds locked from creation). Mode B: published = no-op, accepted = refund. |
| `PaymentDispatcher` | Simplified: no wallet resolution logic. Routes to lock-on-creation or lock-on-assignment path based on mode. |

### Platform wallet role (clarified)

`WALLET_PRIVATE_KEY` (platform wallet) is used **only** for:

| Operation | Why platform wallet is needed |
|-----------|------------------------------|
| Gasless ERC-8004 registration | Workers register identity via Facilitator relay |
| Reputation relay (`EM_REPUTATION_RELAY_KEY`) | Platform can't rate Agent #2106 (self-feedback), needs relay wallet |
| Gas dust distribution | Tiny ETH amounts for worker wallets |
| Testing (when `EM_SERVER_SIGNING=true`) | EM team tests full flow from OpenClaw using platform wallet as agent |

The platform wallet **never**:
- Signs escrow locks for real agent tasks
- Signs EIP-3009 settlements
- Acts as a financial intermediary
- Holds agent funds in transit

## Migration plan

### Phase 1: Disable server signing + cleanup (small, ~2h)

**Files touched**: `payment_dispatcher.py`, `_helpers.py`, 1 new migration

1. Add `EM_SERVER_SIGNING` env var guard to `PaymentDispatcher`
   - When not `true`: reject any `authorize_payment()` / `_settle_submission_payment()`
     call that would use `WALLET_PRIVATE_KEY` to sign on behalf of an agent
   - Return clear error: "Server signing disabled. Agent must provide X-Payment-Auth."
2. Remove dead code:
   - `AGENT_WALLET_PRIVATE_KEY` env var reads
   - `_resolve_payer_wallet()` function
   - `_get_agent_address()` function
   - `_cached_agent_address` global
3. Create migration 074: revert migration 073 (remove `payer_wallet` from escrow metadata)
4. Deploy to ECS **without** `EM_SERVER_SIGNING`
   - Production becomes sign-free immediately
   - No payment operations will work until Phase 2 (acceptable: no real agents
     are creating tasks with real money yet)

### Phase 2: Agent-signed escrow — Mode B default (~6-8h)

**Files touched**: `payment_dispatcher.py`, `routes.py`/`tasks.py`, `_helpers.py`,
`skill.md`, escrow table, tests

1. **Header parsing**: Add `X-Payment-Auth` and `X-Escrow-Timing` header parsing
   to `POST /tasks` endpoint
2. **Pre-auth storage** (Mode B): Store signed auth in `escrows.metadata.preauth_signature`
   with `escrow_status: pending_assignment`
3. **Immediate lock** (Mode A): If `X-Escrow-Timing: lock_on_creation`, execute the
   auth immediately via Facilitator. Return 402 on failure.
4. **Lock at assignment** (Mode B): In `POST /tasks/{id}/assign`, retrieve stored
   pre-auth → send to Facilitator → lock escrow with worker as receiver
5. **Lock failure handler**: If Facilitator returns error at assignment:
   - Revert assignment (task back to PUBLISHED)
   - Return 402 to caller with reason (expired, insufficient balance, etc.)
6. **Escrow timing in task metadata**: Store `escrow_timing` field in task so
   cancel/expire logic knows which flow to follow
7. **Cancel/expire updates**: Mode A always refunds. Mode B: published = no-op,
   accepted = refund.
8. **Skill update** (`skill.md` v3.11.0): Document `X-Payment-Auth` header format,
   EIP-3009 signing instructions, both modes
9. **Tests**: Unit tests for both modes, integration test with mock Facilitator

### Phase 3: Golden Flow + cleanup (~2-3h)

1. Update Golden Flow E2E to use agent-signed pre-auth
2. Remove Fase 1 code paths entirely
3. Simplify `EM_PAYMENT_MODE` — only `fase2` remains (remove env var, hardcode)
4. Archive Fase 1 docs
5. Update CLAUDE.md payment sections

## Consequences

- **Breaking change for agents on Fase 1**: Any agent that relied on server-managed
  settlement will need to sign their own EIP-3009 auths. This affects agents created
  before this ADR. Mitigation: `EM_SERVER_SIGNING=true` as temporary escape hatch.
- **Skill update required**: `skill.md` must document the `X-Payment-Auth` header,
  EIP-3009 signing instructions, and both escrow timing modes. Version bump to `3.11.0`.
- **Dashboard impact**: Worker-facing UI should show:
  - "Pre-authorized" badge for Mode B tasks (pre-auth stored, not yet locked)
  - "Funded" badge for Mode A tasks and Mode B tasks after assignment (escrow locked)
- **Testing workflow**: EM team uses OpenClaw with `EM_SERVER_SIGNING=true` in local
  dev. Production ECS never has this flag.
- **Two modes to maintain**: Both `lock_on_creation` and `lock_on_assignment` share the
  same release/refund paths but differ at creation and assignment. The divergence is
  small (~50 lines in the dispatcher) and worth maintaining for flexibility.

## References

- [[x402r-escrow]] — Escrow contract architecture
- [[payment-operator]] — Fase 5 PaymentOperator (fee split)
- [[erc-8004]] — Agent identity registry
- EIP-3009 spec: https://eips.ethereum.org/EIPS/eip-3009
- Commit `ed36874` — the multi-wallet fix this ADR supersedes
- Post-audit commit `fc986c3` — interim fixes before this redesign
