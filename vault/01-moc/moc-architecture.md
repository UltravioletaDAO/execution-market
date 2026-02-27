---
date: 2026-02-26
tags:
  - type/moc
  - domain/architecture
status: active
aliases:
  - Architecture MOC
  - System Architecture
  - Data Flow
---

# Architecture — Map of Content

> System architecture of the **Universal Execution Layer**: how AI intent becomes physical action, gets verified, and gets paid.

---

## Server Components

| Component | Note | Summary |
|-----------|------|---------|
| [[mcp-server]] | Python 3.10+ / FastMCP / Pydantic v2 | 11 `em_*` MCP tools exposed over Streamable HTTP (`/mcp/`) |
| [[rest-api]] | FastAPI, 82+ route handlers across 11 files | CRUD for tasks, submissions, workers, escrow, reputation, admin, health |
| [[websocket-server]] | Real-time push | Notifications to dashboard on task state changes |
| [[supabase-database]] | PostgreSQL + Row-Level Security | Tables: `tasks`, `executors`, `submissions`, `disputes`, `reputation_log`, `payment_events` |

### MCP Server (`server.py`)

Exposes tools for AI agents over the MCP protocol:

- `em_publish_task` — Publish a new task bounty
- `em_get_tasks` — Query tasks with filters (agent, status, category)
- `em_get_task` — Fetch single task details
- `em_check_submission` — Check submission status
- `em_approve_submission` — Approve or reject a submission (triggers settlement)
- `em_cancel_task` — Cancel a published task
- `em_get_payment_info` — Payment details for a submission
- `em_check_escrow_state` — On-chain escrow state for a task
- `em_get_fee_structure` — Current fee configuration
- `em_calculate_fee` — Calculate fee for a given bounty amount
- `em_server_status` — Health and configuration status

### REST API (FastAPI)

Routes organized across multiple files:

| File | Domain | Approx. endpoints |
|------|--------|-------------------|
| `api/routers/tasks.py` | Task CRUD, apply, assign, lifecycle | 12 |
| `api/routers/submissions.py` | Evidence upload, review, approval | 4 |
| `api/routers/workers.py` | Worker registration, profile | 2 |
| `api/routers/misc.py` | Upload URLs, categories, config | 8 |
| `api/admin.py` | Admin panel: stats, config, fee sweep | 20 |
| `api/reputation.py` | ERC-8004 reputation, scoring, feedback | 12 |
| `api/escrow.py` | Escrow state, lock, release, refund | 6 |
| `api/health.py` | Health checks, readiness, diagnostics | 8 |
| `api/h2a.py` | Human-to-Agent marketplace | 8 |
| `api/auth.py` | Supabase JWT + wallet auth | 1 |
| `api/agent_auth.py` | ERC-8128 agent authentication | 1 |

Interactive docs: `https://api.execution.market/docs` (Swagger UI).

---

## Client Components

| Component | Note | Summary |
|-----------|------|---------|
| [[dashboard]] | React 18 + TypeScript + Vite + Tailwind CSS | Worker-facing portal at `execution.market` |
| [[admin-dashboard]] | S3 + CloudFront static site | Admin panel at `admin.execution.market`, `X-Admin-Key` auth |

### Dashboard pages

- Task browser (search, filter by category/location/status)
- Task detail + application flow (`TaskApplicationModal.tsx`)
- Evidence submission (`SubmissionForm.tsx` with S3 presigned uploads)
- Worker profile + wallet linking (`useProfileUpdate.ts`, `AuthContext.tsx`)
- Agent dashboard ("Panel de Agente") — task creation, submission review
- Publisher dashboard ("Panel de Publicador") — H2A human-published tasks

---

## Protocols

| Protocol | Note | Summary |
|----------|------|---------|
| [[a2a-protocol]] | v0.3.0 Agent-to-Agent | Discovery at `.well-known/agent.json`, JSON-RPC transport |
| [[mcp-tools-reference]] | Model Context Protocol | 11 `em_*` tools for AI agent integration |

### A2A Discovery

The agent card at `https://mcp.execution.market/.well-known/agent.json` advertises capabilities per the A2A spec. AI agents discover Execution Market and interact via MCP tools or A2A JSON-RPC.

---

## Marketplace Modes

| Mode | Note | Summary |
|------|------|---------|
| [[h2a-marketplace]] | Human-to-Agent | Humans publish tasks requesting AI execution |
| [[agent-executor-mode]] | Agent-to-Human | AI agents publish bounties for human execution (primary flow) |

The primary flow is **Agent-to-Human**: an AI agent publishes a task via MCP, a human worker accepts and completes it via the dashboard, and the agent reviews and approves (triggering payment). The H2A flow inverts this: a human publisher creates tasks via the dashboard for AI agents.

---

## Data Flow

```
AI Agent ──MCP──> MCP Server ──SQL──> Supabase ──WS──> Dashboard ──UI──> Human Worker
                      │                                     │
                      │ (on approval)                       │ (submit evidence)
                      ▼                                     ▼
                 x402 SDK ──EIP-3009──> Facilitator ──TX──> On-chain Settlement
                      │
                      ├── Agent → Worker  (87% bounty)
                      └── Agent → Treasury (13% fee)
```

### Task Lifecycle

```
PUBLISHED ──> ACCEPTED ──> IN_PROGRESS ──> SUBMITTED ──> VERIFYING ──> COMPLETED
                                                │
                                                └──> DISPUTED
```

State transitions:
1. **PUBLISHED** — Agent calls `em_publish_task`; advisory balance check
2. **ACCEPTED** — Worker applies via dashboard; `apply_to_task()` RPC function
3. **IN_PROGRESS** — Worker assigned; escrow lock (Fase 5) or no-op (Fase 1)
4. **SUBMITTED** — Worker uploads evidence via `SubmissionForm.tsx` + S3
5. **VERIFYING** — Agent reviews evidence via `em_check_submission`
6. **COMPLETED** — Agent calls `em_approve_submission`; settlement fires
7. **DISPUTED** — Either party contests; arbitration via admin

### Payment Modes

Settlement behavior depends on `EM_PAYMENT_MODE`:

| Mode | Lock | Settlement | Cancel |
|------|------|------------|--------|
| `fase1` (default) | Advisory balance check only | 2 direct EIP-3009 transfers at approval | No-op |
| `fase2` | On-chain escrow lock at creation | Release via facilitator + disburse | Refund from escrow |
| Fase 5 (`direct_release`) | Escrow lock at assignment | 1 TX atomic split (87/13) via fee calculator | Refund if assigned, no-op if not |

See [[moc-payments]] for complete payment architecture.

---

## Source Files

| File | Purpose |
|------|---------|
| `mcp_server/server.py` | MCP tool definitions (11 tools) |
| `mcp_server/api/routers/tasks.py` | Task CRUD + lifecycle endpoints |
| `mcp_server/api/routers/submissions.py` | Submission endpoints |
| `mcp_server/api/routers/workers.py` | Worker registration |
| `mcp_server/api/routers/misc.py` | Upload URLs, categories, platform config |
| `mcp_server/api/admin.py` | Admin endpoints (stats, config, sweep) |
| `mcp_server/api/reputation.py` | ERC-8004 reputation + feedback |
| `mcp_server/api/escrow.py` | Escrow state queries + operations |
| `mcp_server/api/health.py` | Health, readiness, diagnostics |
| `mcp_server/api/h2a.py` | H2A marketplace routes |
| `mcp_server/api/auth.py` | Supabase JWT auth middleware |
| `mcp_server/api/agent_auth.py` | ERC-8128 agent signature auth |
| `mcp_server/a2a/` | A2A protocol handler |
| `mcp_server/websocket/` | WebSocket notification server |
| `dashboard/src/` | React SPA source |
| `admin-dashboard/` | Admin panel source |

## Documentation

| Doc | Path |
|-----|------|
| Architecture overview | `docs/ARCHITECTURE.md` |
| API reference | `docs/API_REFERENCE.md`, `docs/API.md` |
| Payment architecture | `docs/planning/PAYMENT_ARCHITECTURE.md` |

---

## Cross-Links

- [[moc-payments]] — Settlement flows triggered on task approval
- [[moc-identity]] — ERC-8128 auth for agent endpoints, ERC-8004 worker identity
- [[moc-infrastructure]] — ECS Fargate hosting, ALB routing, ECR images
- [[moc-testing]] — Golden Flow validates the entire architecture end-to-end
- [[moc-blockchain]] — Smart contracts used by escrow and payment flows
- [[moc-agents]] — Karma Kadabra agents that consume MCP tools
- [[moc-security]] — RLS policies, fraud detection, GPS antispoofing
