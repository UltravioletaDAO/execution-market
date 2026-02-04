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
        "SUPABASE_URL": "https://YOUR_PROJECT_REF.supabase.co",
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

**IMPORTANT**: Always use the **default AWS account** (`YOUR_AWS_ACCOUNT_ID`, user `YOUR_IAM_USER`). Do NOT use account `897729094021` — it is not the deployment target and lacks proper permissions for Execution Market infrastructure.

| Resource | Details |
|----------|---------|
| AWS Account | `YOUR_AWS_ACCOUNT_ID` (default profile) |
| Region | `us-east-2` (Ohio) |
| Compute | ECS Fargate (`chamba-production-cluster`) *(legacy name, kept for backward compat)* |
| Container Registry | ECR `us-east-2`: `execution-market-dashboard`, `execution-market-mcp-server` *(legacy: `chamba-dashboard`, `chamba-mcp-server`)* |
| Load Balancer | ALB with HTTPS (ACM wildcard cert) |
| DNS | Route53 `execution.market` (dashboard), `mcp.execution.market` (MCP) |
| CI/CD | GitHub Actions `deploy.yml` (auto-deploy on push to `main`) |

Dashboard Docker build: `docker build --no-cache -f dashboard/Dockerfile -t execution-market-dashboard ./dashboard`

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

## Operational State (as of 2026-02-03)

### Deployment Details

| Service | URL | ECR Repo | ECS Cluster *(legacy names, kept for backward compat)* |
|---------|-----|----------|-------------|
| Dashboard | `execution.market` | `execution-market-dashboard:latest` | `chamba-production-cluster` / `chamba-production-dashboard` |
| MCP Server | `mcp.execution.market` | `execution-market-mcp-server:latest` | `chamba-production-cluster` / `chamba-production-mcp-server` |

**IMPORTANT**: The dashboard ECS task definition uses `execution-market-dashboard`. Always push to the correct ECR repo in **us-east-2**:
```bash
# Login to ECR (default account, us-east-2)
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com

# Build + push dashboard
docker build --no-cache -f dashboard/Dockerfile -t execution-market-dashboard ./dashboard
docker tag execution-market-dashboard:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/execution-market-dashboard:latest
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/execution-market-dashboard:latest

# Force new deployment (ECS service names are legacy, kept for backward compat)
aws ecs update-service --cluster chamba-production-cluster --service chamba-production-dashboard --force-new-deployment --region us-east-2
```

### Secrets & Credentials

| Secret | Location | Purpose |
|--------|----------|---------|
| `SUPABASE_URL` | `.env.local` | `https://YOUR_PROJECT_REF.supabase.co` |
| `SUPABASE_ANON_KEY` | `.env.local` | Publishable key for frontend (`sb_publishable_...`) |
| `SUPABASE_SERVICE_KEY` | `mcp_server/.env` | Service role key (bypasses RLS) |
| `WALLET_PRIVATE_KEY` | `.env.local` | Agent wallet `YOUR_DEV_WALLET` |
| `SUPABASE_DB_PASSWORD` | `.env.local` | Direct postgres password |
| Supabase Management API | `~/.supabase/access-token` | For running SQL migrations (`sbp_c5dd...`) |
| AWS ECR | Standard AWS CLI auth | `YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com` |

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
| Agent Wallet | `YOUR_DEV_WALLET` |
| Execution Market Treasury | `YOUR_TREASURY_WALLET` |

**Payment Flow for Tasks**:
1. **Deposit** (task creation): SDK signs → Facilitator → Relay → Vault → Escrow tracks it
2. **Release** (task approval): SDK `settle()` → Facilitator → USDC to worker (gasless)
3. **Refund** (task cancellation): SDK → Facilitator → USDC back to agent
4. **Platform fee**: 8% deducted on release (worker gets 92% of bounty)

### Database State

**Supabase project**: `YOUR_PROJECT_REF`

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
