# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Execution Market is a **Human Execution Layer for AI Agents** - a marketplace where AI agents publish bounties for physical tasks that humans execute, with instant payment via x402. Registered as **Agent #469** on Sepolia ERC-8004 Identity Registry.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend MCP Server | Python 3.10+ + FastMCP + Pydantic v2 |
| Database | Supabase (PostgreSQL) |
| Dashboard | React 18 + TypeScript + Vite + Tailwind CSS |
| Blockchain Scripts | TypeScript + viem |
| Payments | x402r Escrow (Base Mainnet) |
| Evidence Storage | Supabase Storage + IPFS (Pinata) |
| Agent Identity | ERC-8004 Registry (Sepolia) |

## Project Structure

```
execution-market/
├── mcp_server/          # MCP Server for AI agents
├── dashboard/           # React web portal for human workers
├── contracts/           # Smart contracts (Solidity)
├── scripts/             # Blockchain registration scripts
├── sdk/                 # Client SDKs
├── cli/                 # CLI tools
├── supabase/            # Database migrations and seeds
├── infrastructure/      # Terraform, deployment configs
├── docs/                # All documentation
│   ├── articles/        # Blog posts, competition articles
│   ├── planning/        # TODOs, progress, roadmaps
│   └── internal/        # Internal notes, messages
├── videos/              # Video assets (Remotion projects)
│   ├── v1/              # Original video
│   ├── v18/             # Version 18
│   └── v34/             # Version 34
├── landing/             # Landing page
├── admin-dashboard/     # Admin panel
├── tests/               # Integration tests
├── e2e/                 # End-to-end tests
└── agent-card.json      # ERC-8004 agent metadata
```

## Common Commands

### Dashboard Development

```bash
cd dashboard
npm install
npm run dev          # Start dev server (http://localhost:5173)
npm run build        # Production build
npm run test         # Run Vitest unit tests
npm run e2e          # Run Playwright E2E tests
npm run lint         # ESLint
```

### MCP Server

```bash
cd mcp_server
pip install -e .                    # Install in dev mode
python server.py                    # Run server directly
```

Configure Claude Code (`~/.claude/settings.local.json`):
```json
{
  "mcpServers": {
    "execution-market": {
      "type": "stdio",
      "command": "python",
      "args": ["Z:/ultravioleta/dao/chamba/mcp_server/server.py"],
      "env": {
        "SUPABASE_URL": "https://puyhpytmtkyevnxffksl.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-key"
      }
    }
  }
}
```

### Blockchain Scripts

```bash
cd scripts
npm install
npm run register:erc8004     # Register agent (already done - Agent #469)
npm run upload:metadata      # Update IPFS metadata
npm run register:x402r       # Register as x402r merchant (pending)
```

## Architecture

### Data Flow

```
AI Agent → MCP Server → Supabase → Dashboard → Human Worker
                ↓
           x402r Escrow (Base Mainnet)
                ↓
           Payment Release
```

### MCP Tools (for AI agents)

- `em_publish_task` - Publish a new task for human execution
- `em_get_tasks` - Get tasks with filters (agent, status, category)
- `em_get_task` - Get details of a specific task
- `em_check_submission` - Check submission status
- `em_approve_submission` - Approve or reject a submission
- `em_cancel_task` - Cancel a published task

### Task Categories

| Category | Example Tasks |
|----------|---------------|
| `physical_presence` | Verify if store is open, take photos of location |
| `knowledge_access` | Scan book pages, photograph documents |
| `human_authority` | Notarize documents, certified translations |
| `simple_action` | Buy specific item, deliver package |
| `digital_physical` | Print and deliver, configure IoT device |

### Task Lifecycle

```
PUBLISHED → ACCEPTED → IN_PROGRESS → SUBMITTED → VERIFYING → COMPLETED
                                          ↓
                                      DISPUTED
```

## Database Schema

Main tables in Supabase:
- `tasks` - Published bounties with evidence requirements
- `executors` - Human workers with wallet, reputation, location
- `submissions` - Evidence uploads with verification status
- `disputes` - Contested submissions with arbitration
- `reputation_log` - Audit trail for reputation changes

## Environment Variables

Required in `.env.local` (project root):
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `WALLET_PRIVATE_KEY` - For blockchain transactions
- `SEPOLIA_RPC_URL` - Ethereum Sepolia RPC
- `PINATA_JWT_SECRET_ACCESS_TOKEN` - For IPFS uploads

Dashboard uses `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.

## On-Chain Contracts

| Contract | Network | Address |
|----------|---------|---------|
| ERC-8004 Identity Registry | Sepolia | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| x402r Escrow | Base Mainnet | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| Execution Market Agent ID | Sepolia | `469` |

## Key Documentation

- `SPEC.md` - Product specification with task categories and edge cases
- `PLAN.md` - Technical architecture and implementation details
- `docs/SYNERGIES.md` - Integration points with ecosystem projects
- `agent-card.json` - ERC-8004 agent metadata (editable)

## Infrastructure & Deployment

**IMPORTANT**: Always use the **default AWS account** (`518898403364`, user `cuchorapido`). Do NOT use account `897729094021` — it is not the deployment target and lacks proper permissions for Execution Market infrastructure.

| Resource | Details |
|----------|---------|
| AWS Account | `518898403364` (default profile) |
| Region | `us-east-2` (Ohio) |
| Compute | ECS Fargate (`em-production-cluster`) |
| Container Registry | ECR `us-east-2`: `em-production-dashboard`, `em-production-mcp-server` |
| Load Balancer | ALB with HTTPS (ACM wildcard cert) |
| DNS | Route53 `execution.market` (dashboard), `mcp.execution.market` (MCP) |
| CI/CD | GitHub Actions `deploy.yml` (auto-deploy on push to `main`) |

Dashboard Docker build: `docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard`

## File Organization Rules

**Keep the root clean.** Only these files belong in root:
- `README.md`, `CLAUDE.md` - Project documentation
- `SPEC.md`, `PLAN.md` - Core specification docs
- `agent-card.json`, `IDEA.yaml` - Agent metadata
- `Dockerfile*`, `docker-compose*.yml`, `Makefile` - Build configs
- `.env*`, `.gitignore`, `.dockerignore` - Environment configs

**Everything else goes to its folder:**

| Content Type | Location |
|--------------|----------|
| Articles, blog posts | `docs/articles/` |
| TODOs, progress, roadmaps | `docs/planning/` |
| Internal notes, messages | `docs/internal/` |
| API docs, architecture | `docs/` |
| Video projects (Remotion) | `videos/v{version}/` |
| Scripts for blockchain | `scripts/` |
| Database migrations | `supabase/migrations/` |

**When creating new files:**
1. Articles/posts → `docs/articles/ARTICLE_NAME.md`
2. TODOs/planning → `docs/planning/TODO_TOPIC.md`
3. New video version → `videos/v{N}/`
4. Analysis/notes → `docs/internal/`

**Never leave files dangling in root.** If unsure, put in `docs/`.

## Operational State (as of 2026-02-04)

### Deployment Details

| Service | URL | ECR Repo | ECS Service |
|---------|-----|----------|-------------|
| Dashboard | `execution.market` | `em-production-dashboard:latest` | `em-production-cluster` / `em-production-dashboard` |
| MCP Server | `mcp.execution.market` | `em-production-mcp-server:latest` | `em-production-cluster` / `em-production-mcp-server` |

**CRITICAL: ECS Image Tag Rules**
- Always use the `:latest` tag for all images. ECS task definitions MUST reference `:latest`.
- CI/CD may create specific tags (`ship-*`) but the task definition must use `:latest` so manual deploys work.
- If a task definition references a specific tag (e.g., `ship-20260206-*`), update it to `:latest` by registering a new revision.
- When deploying from multiple sessions in parallel, always build from the latest code and push as `:latest`.
- After `docker push :latest`, always verify the ECS task definition references `:latest` (not a `ship-*` tag).

Always push to the correct ECR repo in **us-east-2**:
```bash
# Login to ECR (default account, us-east-2)
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 518898403364.dkr.ecr.us-east-2.amazonaws.com

# Build + push dashboard
docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard
docker tag em-dashboard:latest 518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest
docker push 518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest

# Build + push MCP server
docker build --no-cache -f mcp_server/Dockerfile -t em-mcp ./mcp_server
docker tag em-mcp:latest 518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
docker push 518898403364.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest

# Force new deployment (task def MUST use :latest tag)
aws ecs update-service --cluster em-production-cluster --service em-production-dashboard --force-new-deployment --region us-east-2
aws ecs update-service --cluster em-production-cluster --service em-production-mcp-server --force-new-deployment --region us-east-2
```

### Secrets & Credentials

| Secret | Location | Purpose |
|--------|----------|---------|
| `SUPABASE_URL` | `.env.local` | `https://puyhpytmtkyevnxffksl.supabase.co` |
| `SUPABASE_ANON_KEY` | `.env.local` | Publishable key for frontend (`sb_publishable_...`) |
| `SUPABASE_SERVICE_KEY` | `mcp_server/.env` | Service role key (bypasses RLS) |
| `WALLET_PRIVATE_KEY` | `.env.local` | **Dev** agent wallet `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd` |
| `SUPABASE_DB_PASSWORD` | `.env.local` | Direct postgres password |
| Supabase Management API | `~/.supabase/access-token` | For running SQL migrations (`sbp_c5dd...`) |
| AWS ECR | Standard AWS CLI auth | `518898403364.dkr.ecr.us-east-2.amazonaws.com` |

### x402 Payment Architecture

**CRITICAL**: Always use the **x402 SDK** (`uvd-x402-sdk`) and the **Ultravioleta Facilitator** for ALL payment operations. Never call contracts directly.

```
Correct Flow (gasless):
  Agent signs EIP-3009 auth → SDK → Facilitator → On-chain TX (Facilitator pays gas)

Wrong Flow (DO NOT USE):
  Agent → Direct contract call (pays gas from wallet)
```

| Component | Details |
|-----------|---------|
| **SDK** | `uvd-x402-sdk[fastapi]>=0.3.0` (in `mcp_server/requirements.txt`) |
| **SDK Client** | `mcp_server/integrations/x402/sdk_client.py` — `EMX402Client` class |
| **Facilitator URL** | `https://facilitator.ultravioletadao.xyz` |
| **Facilitator Endpoints** | `POST /verify` (verify payment), `POST /settle` (release payment) |
| **Network** | Base Mainnet (chain 8453) for production |

**Contract Addresses (Base Mainnet)**:

| Contract | Address |
|----------|---------|
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| x402r Escrow | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| DepositRelayFactory | `0x41Cc4D337FEC5E91ddcf4C363700FC6dB5f3A814` |
| Deposit Relay (our wallet) | `0xe8CCF8Be24867cf21b4031fB1A5226932483EAF3` |
| Vault | `0x0b3fC8BA8952C6cA6807F667894b0b7c9c40fc8b` |
| Agent Wallet (dev) | `0x857fe6150401bFB4641Fe0D2B2621cc3B05543Cd` |
| Agent Wallet (production/ECS) | `0x34033041a5944B8F10f8E4D8496Bfb84f1A293A8` |
| Execution Market Treasury | `0xae07ceb6b395bc685a776a0b4c489e8d9ce9a6ad` |

**Wallet Notes**:
- **Dev wallet** (`0x857f`): Used by local scripts and tests. Key in `.env.local`.
- **Production wallet** (`0x3403`): Used by ECS MCP server. Key in AWS Secret `em/x402:PRIVATE_KEY`.
- These are currently different keys. Production wallet has ~$30 USDC for live payments.

**Payment Flow for Tasks** (as of 2026-02-06):
1. **Deposit** (task creation): Agent signs EIP-3009 auth → MCP verifies via Facilitator → Task created (no funds move yet)
2. **Release** (task approval): MCP signs TWO new EIP-3009 auths: agent→worker (92%) + agent→treasury (8%) → Facilitator settles both (gasless)
3. **Refund** (task cancellation): Original auth expires — no funds ever moved, no action needed
4. **Platform fee**: Configurable via `EM_PLATFORM_FEE` env var (default 8%). Set to `0.00` for 0% fee.

**Split Payment Architecture** (current MVP):
- At approval, `sdk_client.py:settle_task_payment()` signs fresh EIP-3009 auths from the agent wallet
- Uses direct HTTP to facilitator `/settle` (not SDK's `settle_payment()` — see note below)
- The facilitator validates `payTo == auth.to`, so the SDK's `settle_payment()` which hardcodes `payTo=config.recipient` cannot be used for worker disbursement
- **TODO**: Modify `uvd-x402-sdk` to support custom `payTo` parameter, then switch from direct HTTP back to SDK

### Database State

**Supabase project**: `puyhpytmtkyevnxffksl`

**RPC Functions available in live DB**:
- `get_or_create_executor(wallet, name, email)` — Creates or updates executor
- `link_wallet_to_session(user_id, wallet, chain_id)` — Links wallet to auth session
- `apply_to_task(task_id, executor_id, message)` — Accept task atomically (creates application + sets executor_id)
- `expire_tasks()` — Mark overdue tasks as expired
- `create_executor_profile(...)` — Create executor profile

**Missing RPC functions** (in migrations but NOT in live DB):
- `claim_task` — Exists in `005_rpc_functions.sql` but never applied. `apply_to_task` handles this for now.

**Columns added manually** (not in original migration):
- `executors.email`, `executors.phone`, `executors.skills`, `executors.languages`, `executors.timezone`, `executors.status`, `executors.tier`, `executors.is_verified`, `executors.kyc_completed_at`, `executors.balance_usdc`, `executors.total_earned_usdc`, `executors.total_withdrawn_usdc`, `executors.erc8004_agent_id`
- `tasks.escrow_amount_usdc`, `tasks.escrow_created_at`

**Known RLS issues**:
- `submissions` INSERT policy requires `executor.user_id = auth.uid()`. If the executor isn't linked to the anonymous session, inserts fail **silently** (no error, just 0 rows). The SubmissionForm.tsx doesn't handle this properly.

### Known Bugs & TODOs

**Dashboard**:
- [ ] `SubmissionForm.tsx` uses direct Supabase insert (bypasses service layer, fails silently on RLS). Should use `services/submissions.ts` `submitWork()` instead.
- [ ] Evidence uploads may fail silently if `executor.user_id` is null.
- [ ] The proper `EvidenceUpload.tsx` component (with camera, GPS, EXIF) is unused — `SubmissionForm.tsx` is a simpler but less reliable version.

**MCP Server / Payments**:
- [ ] `routes.py` `create_task()` escrow wiring calls contracts directly — must use SDK/facilitator instead.
- [ ] `routes.py` `approve_submission()` escrow release calls contracts directly — must use `sdk_client.settle_task_payment()`.
- [ ] `x402r_escrow.py` ABI doesn't match actual contract (e.g., `merchantBalance` doesn't exist on escrow contract).
- [ ] Task creation should flow: Agent → MCP API (402) → Agent signs x402 payment → MCP verifies via facilitator → Task created.

**Escrow**:
- [ ] $0.10 USDC stuck in vault from direct relay deposit (tx `0xda31cbe...`). Needs refund via facilitator or contract expiry.
- [ ] Deposit limit: $100 max per deposit (contract-enforced).

### Task Factory Guidelines

When creating test tasks:
- **Deadlines**: 5-15 minutes for testing, NOT hours.
- **Bounties**: Small amounts ($0.05–$0.25) for test tasks.
- **Script**: `cd scripts && npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10`
- **Live escrow**: Add `--live` flag (requires USDC in wallet + uses relay directly — needs SDK migration)

### ERC-8004 Identity

| Field | Value |
|-------|-------|
| Agent ID | 469 |
| Registry (Sepolia) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| Identity Registry (Mainnet) | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| Reputation Registry | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |
| Facilitator Reputation API | `POST /feedback`, `GET /reputation/{network}/{agentId}` |

### Complete URL Map

#### Production URLs

| URL | Service | Description |
|-----|---------|-------------|
| `https://execution.market` | Dashboard | Worker-facing React SPA |
| `https://api.execution.market` | API Gateway | Redirects to Swagger UI at `/docs` |
| `https://api.execution.market/docs` | Swagger UI | Interactive API documentation |
| `https://api.execution.market/redoc` | ReDoc | Alternative API documentation |
| `https://api.execution.market/api/v1/*` | REST API | All API endpoints |
| `https://mcp.execution.market` | MCP Server | MCP transport for agents |
| `https://mcp.execution.market/mcp/` | MCP Transport | Streamable HTTP endpoint |
| `https://mcp.execution.market/.well-known/agent.json` | A2A | Agent discovery card |

#### Dashboard Pages (`https://execution.market`)

| Path | Page | Auth |
|------|------|------|
| `/` | Home (hero, task browser, how-it-works) | Public |
| `/about` | About Execution Market | Public |
| `/faq` | FAQ | Public |
| `/tasks` | Browse & apply for tasks | Worker |
| `/profile` | Worker profile, earnings, reputation | Worker |
| `/earnings` | Earnings tracking (placeholder) | Worker |
| `/agent/dashboard` | Agent analytics, task mgmt, submissions | Agent |
| `/agent/tasks` | Agent task management (placeholder) | Agent |
| `/agent/tasks/new` | Create new task (placeholder) | Agent |

#### API Endpoints (`https://api.execution.market` or `https://mcp.execution.market`)

**Health & Monitoring:**
- `GET /health` — Basic health check (ALB)
- `GET /health/` — Detailed health with component latency
- `GET /health/live` | `/health/ready` | `/health/startup` — K8s probes
- `GET /health/metrics` — Prometheus metrics
- `GET /health/version` — Version info

**MCP Transport:**
- `POST /mcp/` — MCP Streamable HTTP (SSE) for AI agent tool invocation
- `GET /mcp/` — MCP session initialization

**REST API — Agent Endpoints (`/api/v1`):** (API key required)
- `POST /api/v1/tasks` — Create task (with x402 payment)
- `GET /api/v1/tasks` — List agent's tasks
- `GET /api/v1/tasks/{id}` — Get task details
- `POST /api/v1/tasks/batch` — Batch create (max 50)
- `POST /api/v1/tasks/{id}/cancel` — Cancel + refund
- `GET /api/v1/tasks/{id}/submissions` — Get submissions
- `POST /api/v1/submissions/{id}/approve` — Approve + pay
- `POST /api/v1/submissions/{id}/reject` — Reject
- `GET /api/v1/analytics` — Agent analytics

**REST API — Worker Endpoints (`/api/v1`):**
- `POST /api/v1/executors/register` — Register worker
- `GET /api/v1/tasks/available` — Browse available tasks
- `POST /api/v1/tasks/{id}/apply` — Apply to task
- `POST /api/v1/tasks/{id}/submit` — Submit work + evidence
- `GET /api/v1/executors/{id}/tasks` — Worker's tasks
- `GET /api/v1/executors/{id}/stats` — Worker stats

**REST API — Admin Endpoints (`/api/v1/admin`):** (Admin key required)
- `GET /api/v1/admin/verify` — Verify admin key
- `GET /api/v1/admin/stats` — Platform statistics
- `GET /api/v1/admin/tasks` — All tasks (search, filter)
- `GET|PUT /api/v1/admin/tasks/{id}` — Task details/override
- `GET /api/v1/admin/payments` — Transaction history
- `GET /api/v1/admin/payments/stats` — Payment stats
- `GET /api/v1/admin/users/agents` | `/workers` — User lists
- `PUT /api/v1/admin/users/{id}/status` — Suspend/activate
- `GET|PUT /api/v1/admin/config` | `/{key}` — Platform config
- `GET /api/v1/admin/config/audit` — Config change audit
- `GET /api/v1/admin/analytics` — Analytics data

**Escrow (`/api/v1/escrow`):**
- `GET /api/v1/escrow/config` — x402r configuration
- `GET /api/v1/escrow/balance` — Merchant USDC balance
- `POST /api/v1/escrow/release` — Release to worker
- `POST /api/v1/escrow/refund` — Refund to agent

**Reputation (`/api/v1/reputation`):**
- `GET /api/v1/reputation/em` — EM reputation score
- `GET /api/v1/reputation/agents/{id}` — Agent reputation
- `POST /api/v1/reputation/workers/rate` — Rate worker
- `POST /api/v1/reputation/agents/rate` — Rate agent

**WebSocket:**
- `WS /ws` — Real-time task notifications
- `GET /ws/stats` — WebSocket stats

#### Not Yet Deployed

| App | Directory | Intended URL | Status |
|-----|-----------|-------------|--------|
| Admin Dashboard | `admin-dashboard/` | `admin.execution.market` | Built, no CI/CD pipeline |
| Docs Site | `docs-site/` | `docs.execution.market` | VitePress, no pipeline |
| Landing Pages | `landing/` | N/A | Static HTML, no deployment |

### Key Integration Files

| File | Purpose |
|------|---------|
| `mcp_server/integrations/x402/sdk_client.py` | x402 SDK wrapper — **USE THIS for all payments** |
| `mcp_server/integrations/x402/client.py` | Direct HTTP facilitator client (fallback) |
| `mcp_server/integrations/x402/x402r_escrow.py` | Direct contract calls (AVOID — use SDK instead) |
| `mcp_server/integrations/x402/advanced_escrow_integration.py` | Advanced escrow flows documentation |
| `mcp_server/integrations/erc8004/facilitator_client.py` | ERC-8004 reputation via facilitator |
| `mcp_server/api/routes.py` | REST API endpoints (task CRUD, submissions, escrow) |
| `mcp_server/server.py` | MCP tools for AI agents |
| `dashboard/src/components/TaskApplicationModal.tsx` | Task acceptance flow |
| `dashboard/src/components/SubmissionForm.tsx` | Evidence upload (needs fix) |
| `dashboard/src/hooks/useProfileUpdate.ts` | Profile update with executor ID resolution |
| `dashboard/src/context/AuthContext.tsx` | Auth state with wallet-based executor lookup |
