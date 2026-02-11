# HANDOFF: Human-to-Agent (H2A) Marketplace Analysis

> **Date**: 2026-02-11
> **From**: A2A analysis session (Agent-to-Agent marketplace plan)
> **To**: New session — analyze and plan Human-to-Agent marketplace
> **Priority**: Run in parallel with A2A implementation

---

## Context: The Full Marketplace Vision

Execution Market is building a **universal task marketplace** with three directions:

| Direction | Publisher | Executor | Status |
|-----------|-----------|----------|--------|
| **Agent → Human** (A2H) | AI Agent | Human Worker | LIVE (production) |
| **Agent → Agent** (A2A) | AI Agent | AI Agent | PLANNED (8-day plan ready, see below) |
| **Human → Agent** (H2A) | Human | AI Agent | THIS TASK — needs analysis + plan |

The end state is a **full quadrant marketplace** where anyone (human or agent) can hire anyone (human or agent). This session focuses on the **H2A direction**: a human posts a task, an AI agent executes it, and gets paid.

**OpenClaw as H2A executor** (originally miscalled "CloudBot" / "OpenCloud"): The primary agent supply for H2A comes from the **OpenClaw ecosystem** (145K GitHub stars, 3000+ ClawHub skills, A2A protocol). An OpenClaw agent installs the EM ClawHub skill (from A2A plan Phase 5) and can then browse + accept + execute H2A tasks. For tasks no agent picks up, the platform can spin up **ephemeral OpenClaw instances** on AWS ECS (existing Terraform) with the EM skill pre-installed. Future: TEE for sensitive tasks.

---

## What Already Exists (Read These Files First)

### Core Architecture
| File | What it tells you |
|------|-------------------|
| `CLAUDE.md` (project root) | Complete project overview, tech stack, all endpoints, all contracts |
| `mcp_server/api/routes.py` | REST API — task CRUD, submissions, payments. ~4000 lines. THE file to understand. |
| `mcp_server/server.py` | MCP tools exposed to AI agents (publisher-side) |
| `mcp_server/models.py` | All Pydantic models — Task, Executor, Submission, CreateTaskRequest |
| `mcp_server/tools/worker_tools.py` | MCP tools for workers (apply, submit, withdraw) |
| `mcp_server/tools/agent_executor_tools.py` | May exist by now — agent executor tools from A2A plan |
| `mcp_server/integrations/x402/sdk_client.py` | Payment SDK — EIP-3009, settlement, 15 networks |
| `mcp_server/integrations/x402/payment_dispatcher.py` | Payment mode routing (fase1, fase2, preauth) |

### Dashboard (React + TypeScript + Vite + Tailwind)
| File | What it tells you |
|------|-------------------|
| `dashboard/src/pages/Tasks.tsx` | Worker task browser — "Disponibles", "Cerca de mi", "Mis Solicitudes" |
| `dashboard/src/pages/AgentDashboard.tsx` | Agent dashboard — published tasks, submissions to review |
| `dashboard/src/pages/agent/CreateTask.tsx` | 4-step task creation wizard |
| `dashboard/src/components/TaskCard.tsx` | Task display card component |
| `dashboard/src/components/TaskApplicationModal.tsx` | Worker applies to task |
| `dashboard/src/components/SubmissionForm.tsx` | Worker submits evidence |
| `dashboard/src/context/AuthContext.tsx` | Auth — Dynamic.xyz wallet, UserType: 'worker' | 'agent' |
| `dashboard/src/types/database.ts` | All TypeScript types |

### Database
| File | What it tells you |
|------|-------------------|
| `supabase/migrations/` | All migrations (001-028+). Key tables: tasks, executors, submissions, disputes |
| Migration 029 (may exist) | Agent executor support — executor_type, capabilities, digital categories |

### Plans & References
| File | What it tells you |
|------|-------------------|
| `docs/planning/A2A_OPENCLAW_EXECUTION_PLAN.md` | COMPLETE A2A plan — 7 phases, all decisions locked. READ THIS FIRST. |
| `docs/planning/PAYMENT_ARCHITECTURE.md` | Payment flow diagrams |
| `docs/planning/X402R_REFERENCE.md` | Escrow architecture |

---

## What the A2A Plan Already Adds (Shared Infrastructure)

The A2A plan (being implemented in parallel) adds infrastructure that H2A can reuse:

### Migration 029 (A2A) — Reusable for H2A
```sql
-- These columns serve BOTH A2A and H2A:
executors.executor_type    -- 'human' | 'agent' — H2A needs agents as executors
executors.capabilities     -- TEXT[] — what the agent can do
executors.agent_card_url   -- URL to agent's A2A card
executors.mcp_endpoint_url -- URL to agent's MCP server

tasks.target_executor_type   -- 'human' | 'agent' | 'any'
tasks.verification_mode      -- 'manual' | 'auto' | 'oracle'
tasks.verification_criteria  -- JSONB for auto-verify
tasks.required_capabilities  -- TEXT[] match against executor capabilities

-- New digital task categories (also for H2A):
'data_processing', 'api_integration', 'content_generation',
'code_execution', 'research', 'multi_step_workflow'
```

### Agent Executor Tools (A2A) — Reusable for H2A
These MCP tools let agents act as executors:
- `em_register_as_executor` — agent registers with capabilities + wallet
- `em_browse_agent_tasks` — agent finds tasks it can do
- `em_accept_agent_task` — agent accepts a task
- `em_submit_agent_work` — agent submits structured deliverables
- `em_get_my_executions` — agent tracks its accepted tasks

### Payment Flow — Already Works
x402 settlement is wallet-agnostic. `_settle_submission_payment()` sends USDC to `executor.wallet_address` — doesn't matter if the publisher was human or agent.

---

## What H2A Specifically Needs (Your Analysis Scope)

### 1. Human Publisher Flow (THE KEY DIFFERENCE)

Currently, only AI agents publish tasks (via MCP tools or REST API with API key). For H2A:
- **A human needs a UI to create tasks for agents** (similar to CreateTask.tsx but from worker perspective)
- **Auth**: Human publishers authenticate via Dynamic.xyz wallet (like workers today)
- **Payment**: Human signs EIP-3009 authorization from their wallet (not server-signed like agent publishers)
- **Task description**: Humans describe tasks in natural language; the system should help match to agent capabilities

**Key question**: Does the human use the existing dashboard (new page/section)? Or is this a separate interface?

### 2. Agent Discovery for Humans

Currently there's no "browse agents" feature. Humans need to:
- See a directory of registered agent executors with their capabilities
- Filter by capability, reputation, price range
- See agent ratings from previous task completions
- Possibly see the agent's A2A card / MCP endpoint for transparency

### 3. Human-Initiated Payment Flow

Current Fase 1 flow: **Server** signs EIP-3009 from `WALLET_PRIVATE_KEY` (platform key).

For H2A, the **human's wallet** is the funding source. Two approaches:
1. **Browser wallet signing**: Human connects wallet via Dynamic.xyz, signs EIP-3009 auth in browser, server stores and settles later
2. **Deposit model**: Human deposits USDC to escrow upfront (like Fase 2), released on completion

**Critical**: The human does NOT have a server-side private key. All signing must happen client-side (browser).

### 4. Dashboard UI for Human Publishers

New pages/sections needed:
- "Contratar Agente" / "Hire an Agent" — task creation flow targeting agent executors
- Agent directory / browser — discover capable agents
- "Mis Contratos" — tasks the human has published for agents
- Submission review — view agent deliverables (JSON, code, reports)
- Rating — human rates agent executor after completion

### 5. Auth Model Extension

Current `UserType = 'worker' | 'agent'`. For H2A:
- A human user needs to be BOTH a worker (executes tasks from agents) AND a publisher (creates tasks for agents)
- Or: A third role `'publisher'` or make roles non-exclusive
- The `agent` role currently means "AI agent publisher" — needs clarification

### 6. OpenClaw as H2A Executor (formerly miscalled "CloudBot" / "OpenCloud")

The user meant **OpenClaw** — the open-source agent platform already in the A2A plan:
- OpenClaw agents install the EM ClawHub skill (A2A plan Phase 5) → can browse + accept H2A tasks
- Same skill serves both A2A and H2A marketplace directions (one skill, two flows)
- 3000+ ClawHub skills give agents instant capabilities (research, code, data processing, etc.)
- For unmatched tasks: spin up **ephemeral OpenClaw instances** on AWS ECS (existing Terraform)
- Future: TEE (Nitro Enclaves) for sensitive tasks
- **Deferred to Phase 2** — build H2A direct marketplace first, then OpenClaw executor supply

---

## Recommended Analysis Approach

Spin up a team of agents (like the A2A session did) to analyze:

### Agent 1: Dashboard UI Analysis
- Read all dashboard pages and components
- Design the "human publishes task for agent" flow
- Design agent directory / browser for humans
- Identify reusable components from existing worker and agent dashboards

### Agent 2: Backend / API Analysis
- Read routes.py, server.py, models.py
- Identify what REST endpoints need to change for human publishers
- Design the client-side EIP-3009 signing flow (vs server-side)
- Analyze auth model changes needed

### Agent 3: Payment Flow Design
- Read sdk_client.py, payment_dispatcher.py
- Design how a browser-connected wallet signs x402 payments
- Compare: direct wallet signing vs on-chain escrow vs deposit model
- Consider: can the facilitator handle browser-initiated settlements?

### Agent 4: Agent Discovery & Matching
- Design the agent executor registry (how agents list their services)
- Capability matching algorithm (task requirements → agent capabilities)
- Pricing model (do agents set their own rates? or publishers set bounties?)
- How does this integrate with OpenClaw agent discovery?

---

## Decisions Already Made (From A2A Session — Apply to H2A Too)

| Decision | Value | Applies to H2A? |
|----------|-------|-----------------|
| Platform fee | 8% | Yes |
| Auto-verify default | `manual`, `auto` opt-in | Yes — human might want auto for simple tasks |
| Capability taxonomy | Own categories, mapped to OpenClaw | Yes — same categories |
| Digital evidence types | json_response, code_output, api_response, etc. | Yes |
| OpenClaw integration | Community skill on ClawHub | Yes — agents discovered via same channel |

---

## Key Technical Constraints

1. **Windows development**: Paths use `Z:\ultravioleta\dao\...`, use `python` not `python3`
2. **Ruff formatting**: ALWAYS run `ruff format .` before committing Python. Must be ruff 0.15.0+
3. **Never auto-push**: Commit freely, but NEVER `git push` unless user explicitly says "push"
4. **Dashboard is in Spanish**: UI text is Spanish ("Buscar Tareas", "Panel de Agente", etc.)
5. **Testing**: 909 tests with pytest markers. Run `pytest` in `mcp_server/` (auto-skips dormant)
6. **CI replication**: `ruff check . && ruff format --check .` + `mypy` + `pytest` + `tsc --noEmit && npm run lint`

---

## Output Expected

Create a plan similar to `docs/planning/A2A_OPENCLAW_EXECUTION_PLAN.md` but for H2A:
- File: `docs/planning/H2A_MARKETPLACE_EXECUTION_PLAN.md`
- Include: database changes, API changes, dashboard UI, payment flow, testing
- Identify what's shared with A2A (don't duplicate work)
- Identify what's H2A-specific
- Include Mermaid diagrams for flows
- Estimate effort in days
- List decision points for user approval

---

## Vision Note: Karma Kadabra

The user has a future project called **Karma Kadabra** — a swarm of agents from Ultravioleta DAO. Agents use logs from "Karma Hello" to generate tasks for other agents. This is the Phase 2 vision that will use both A2A and potentially H2A infrastructure. Don't design for it now, but keep it in mind as a future integration point.

---

## The Complete Marketplace Quadrant (End State)

```
              EXECUTOR
           Human    Agent
         ┌────────┬────────┐
  Human  │  H2H   │  H2A   │  ← THIS TASK
PUBLISHER│(future)│(plan)  │
         ├────────┼────────┤
  Agent  │  A2H   │  A2A   │  ← Already planned
         │(LIVE!) │(plan)  │
         └────────┴────────┘
```

The H2H quadrant (human hires human, like Fiverr/TaskRabbit) is an obvious future extension but NOT in scope now.

---

## Vision Note: Messaging Bot + Local Payments (WhatsApp/Telegram)

**Concept**: A human talks to a bot on WhatsApp or Telegram, describes what they need, the bot publishes a task on Execution Market, an agent executes it, and the human pays via:
- **USDC** (crypto-native users)
- **Nequi** (Colombian payment service — fiat onramp for non-crypto users)
- Other local payment rails per country

**Why this matters**:
- OpenClaw already connects to 12+ messaging channels (WhatsApp, Telegram, Slack, Discord, Signal, iMessage)
- A ClawHub skill for Execution Market + messaging channel = instant H2A access for billions of people
- Nequi/local payments = fiat onramp → USDC → x402 settlement → agent gets paid
- "Just talk to a bot and it does the task" = the simplest possible UX

**Integration path**:
1. OpenClaw bot on WhatsApp/Telegram (already supported channels)
2. EM ClawHub skill installed on the bot (from A2A plan)
3. Human describes task → bot creates task via EM API → agent executes
4. Payment: Nequi → fiat-to-USDC bridge → x402 settlement
5. Wallet management: custodial (bot holds wallet) or Telegram native wallet

**Keep in mind during H2A design**: The "human publisher" might not have a web browser at all — just a messaging app. The H2A flow should support both dashboard UI AND messaging bot as input channels.
