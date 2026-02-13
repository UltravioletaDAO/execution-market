# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Developer

| Field | Value |
|-------|-------|
| Name | 0xultravioleta |
| Email | 0xultravioleta@gmail.com |
| GitHub | [@ultravioletadao](https://github.com/ultravioletadao) |

## Project Overview

Execution Market is a **Human Execution Layer for AI Agents** - a marketplace where AI agents publish bounties for physical tasks that humans execute, with instant payment via x402. Registered as **Agent #2106** on Base ERC-8004 Identity Registry (previously #469 on Sepolia).

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend MCP Server | Python 3.10+ + FastMCP + Pydantic v2 |
| Database | Supabase (PostgreSQL) |
| Dashboard | React 18 + TypeScript + Vite + Tailwind CSS |
| Blockchain Scripts | TypeScript + viem |
| Payments | x402 SDK + Facilitator (Base Mainnet, gasless) |
| Evidence Storage | S3 + CloudFront CDN (presigned uploads) |
| Agent Identity | ERC-8004 Registry (15 networks via Facilitator) |
| SDKs | Python `uvd-x402-sdk>=0.11.0` / TypeScript `uvd-x402-sdk@2.23.0` |

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

## Git Workflow

**IMPORTANT: Commit Policy**
- ✅ **Commit freely**: Create commits when tasks are complete or logical checkpoints are reached
- ❌ **Never auto-push**: Do NOT push to remote unless explicitly requested by the user
- ⚠️ **Push only when asked**: Only run `git push` when the user explicitly says "push" or "pusha" or similar

**Rationale**: Pushing triggers CI/CD pipelines (GitHub Actions) which take ~20 minutes. User wants control over when deployments happen.

**Workflow:**
1. Make changes → commit locally
2. User tests locally with `.\scripts\test-local.ps1`
3. User explicitly says "push" → then `git push`

**Example:**
```bash
# ✅ OK - Auto commit when done
git commit -m "feat: nueva feature"

# ❌ NEVER - Do not auto-push
# git push  # ← NO!

# ✅ OK - Only when user explicitly requests
# User: "push"
# Assistant: git push
```

## Working Style - Be Proactive

**IMPORTANT: Default to implementation, not questions.**

When you know something will be needed or is a logical next step:
- ✅ **DO**: Implement it directly and notify the user
- ❌ **DON'T**: Ask "Should I also do X?" when you know X is needed

**Examples:**
- If you add a Python pre-commit hook, also add one for TypeScript (don't ask)
- If you fix a bug in one file, check similar files for the same issue (don't ask)
- If you update a component, update its tests too (don't ask)
- If you see an obvious improvement or missing piece, implement it (don't ask)

**When to ask:**
- Multiple valid approaches with trade-offs
- User preference needed (design, naming, architecture)
- Breaking changes or risky operations
- Unclear requirements

**Rule of thumb**: If the answer is "obviously yes", don't ask—just do it and report what you did.

---

## IRC Collaboration

When the user says **"Conéctate a IRC"**, **"charla con el facilitador"**, **"chat with facilitator"**, or similar — use the **irc-collab** skill at `.claude/skills/irc-collab/SKILL.md`. This connects to `irc.meshrelay.xyz` channel `#execution-market-facilitator` to discuss with other Ultravioleta DAO Claude Code sessions (facilitator, SDK teams).

---

## Common Commands

### Quick Commands (Local Development)

```powershell
# Testing
/test                                    # All tests (5-7 min)
/test-quick                              # Only unit tests (2-3 min)

# Development
/dev-start                               # Start Docker stack
/dev-logs                                # View logs
/dev-stop                                # Stop Docker stack
```

See `COMMANDS.md` for complete reference.

### Backend Test Profiles

The backend test suite (909 tests) is organized with **pytest markers** for selective execution. By default, dormant tests (modules not wired into active endpoints) are auto-skipped.

```bash
cd mcp_server

# Default run — skips dormant (111 tests), runs ~800 active tests
pytest

# Specific profiles
pytest -m core                             # Core business logic (213 tests)
pytest -m erc8004                          # ERC-8004 integration (108 tests)
pytest -m payments                         # Payment flows (204 tests)
pytest -m security                         # Fraud, GPS, auth (80 tests)
pytest -m infrastructure                   # Webhooks, WS, A2A (70 tests)

# Combine profiles
pytest -m "core or erc8004"                # Core + ERC-8004
pytest -m "core or payments"               # Core + payments
pytest -m "not dormant and not redundant"  # Lean suite (~720 tests)

# Include everything (CI full sweep)
EM_TEST_PROFILE=full pytest                # All 909 tests including dormant

# View dormant tests only
pytest -m dormant                          # 111 tests for unwired modules
pytest -m redundant                        # 99 tests (a2a serialization)
```

**Marker reference** (`mcp_server/pytest.ini`):

| Marker | Tests | What it covers |
|--------|-------|----------------|
| `core` | 213 | Routes, MCP tools, auth, reputation, workers, platform config |
| `payments` | 204 | PaymentDispatcher, escrow, fees, multichain |
| `erc8004` | 108 | Scoring, side effects, auto-registration, rejection, reputation tools |
| `security` | 80 | Fraud detection, GPS antispoofing, safety |
| `infrastructure` | 70 | Webhooks, WebSocket, A2A, timestamps |
| `dormant` | 111 | Seals, consensus, protection fund, recon (NOT in active endpoints) |
| `redundant` | 99 | A2A enum/serialization tests (low value) |

**Dormant tests** are preserved in-place (not deleted) with a `pytestmark = pytest.mark.dormant` marker. They test modules that exist in the codebase but aren't wired into `routes.py` or `server.py`:
- `test_seals.py` (43) — Seals & Credentials (in `mcp_server/seals/`)
- `test_consensus.py` (27) — Validator Consensus (in `mcp_server/validation/consensus.py`)
- `test_protection_fund.py` (30) — Worker Protection Fund (in `mcp_server/protection/fund.py`)
- `test_recon.py` (11) — Recon task types (in `mcp_server/task_types/recon.py`)

---

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
npm run register:erc8004     # Register agent (Agent #2106 on Base, #469 on Sepolia)
npm run upload:metadata      # Update IPFS metadata
npm run register:x402r       # Register as x402r merchant (pending)
```

## Architecture

### Data Flow

```
AI Agent → MCP Server → Supabase → Dashboard → Human Worker
                ↓
           x402r Escrow (8 networks: 1 live + 7 pending)
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

### Multichain Payment Config
- `EM_ENABLED_NETWORKS` - Comma-separated list of enabled payment networks (default: `base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism`)
- `X402_NETWORK` - Default payment network (default: `base`)
- **To add a new chain or stablecoin**: Use the **`add-network` skill** (`.claude/skills/add-network/SKILL.md`) — it has the complete step-by-step checklist
- Token registry lives in `mcp_server/integrations/x402/sdk_client.py` (`NETWORK_CONFIG` dict — single source of truth, 15 EVM networks, 5 stablecoins, 10 with x402r escrow)
- Other Python files (facilitator_client, tests, platform_config) **auto-derive** from sdk_client.py — no manual updates needed

## On-Chain Contracts

| Contract | Network | Address |
|----------|---------|---------|
| ERC-8004 Identity Registry | All Mainnets (CREATE2) | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| ERC-8004 Identity Registry | All Testnets (CREATE2) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| ERC-8004 Reputation Registry | All Mainnets (CREATE2) | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |
| x402r Escrow (AuthCaptureEscrow) | Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| x402r Escrow (AuthCaptureEscrow) | Ethereum | `0xc1256Bb30bd0cdDa07D8C8Cf67a59105f2EA1b98` |
| x402r Escrow (AuthCaptureEscrow) | Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| x402r Escrow (AuthCaptureEscrow) | Arbitrum, Avalanche, Celo, Monad, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| x402r Escrow (legacy, deprecated) | Base | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| **EM PaymentOperator (Fase 3 Clean)** | **Base** | **`0xd5149049e7c212ce5436a9581b4307EB9595df95`** |
| EM PaymentOperator (Fase 3 v1, legacy) | Base | `0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6` |
| EM PaymentOperator (Fase 2, legacy) | Base | `0xb9635f544665758019159c04c08a3d583dadd723` |
| StaticAddressCondition(Facilitator) | Base | `0x9d03c03c15563E72CF2186E9FDB859A00ea661fc` |
| OrCondition(Payer\|Facilitator) | Base | `0xb365717C35004089996F72939b0C5b32Fa2ef8aE` |
| StaticFeeCalculator(100bps) | Base | `0xB422A41aae5aFCb150249228eEfCDcd54f1FD987` |
| Facilitator EOA | All | `0x103040545AC5031A11E8C03dd11324C7333a13C7` |
| Execution Market Agent ID | **Base** | `2106` |
| Execution Market Agent ID | Sepolia (legacy) | `469` |

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
| AWS CLI Access | **Full access** — Claude Code can run `aws` commands directly |
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

## Documentation Standards

### Mermaid Diagrams
**All documentation that describes flows, state machines, or architecture MUST include Mermaid diagrams.** This is a mandatory standard for this project.

- Use `sequenceDiagram` for multi-actor flows (payment flow, API calls, auth flow)
- Use `stateDiagram-v2` for state machines (task lifecycle, escrow states)
- Use `graph LR` or `graph TD` for architecture/relationship diagrams (wallet map, infrastructure)
- Use `flowchart` for decision trees and conditional logic

**When to add diagrams:**
- Any new flow involving 3+ steps → sequence diagram
- Any entity with 3+ states → state diagram
- Any system with 3+ interacting components → architecture graph

**Format:** GitHub-flavored Mermaid (renders in GitHub, VS Code, and most Markdown viewers). Wrap in triple-backtick `mermaid` code blocks.

**Reference:** See `docs/planning/PAYMENT_ARCHITECTURE.md` for examples of all diagram types.


## Operational State (as of 2026-02-13)

**CRITICAL: ECS Image Tag Rules**
- Always use the `:latest` tag for all images. ECS task definitions MUST reference `:latest`.
- CI/CD may create specific tags (`ship-*`) but the task definition must use `:latest` so manual deploys work.
- If a task definition references a specific tag (e.g., `ship-20260206-*`), update it to `:latest` by registering a new revision.
- When deploying from multiple sessions in parallel, always build from the latest code and push as `:latest`.
- After `docker push :latest`, always verify the ECS task definition references `:latest` (not a `ship-*` tag).

Always push to the correct ECR repo in **us-east-2**:
```bash
# Login to ECR (default account, us-east-2)
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com

# Build + push dashboard
docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard
docker tag em-dashboard:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/em-production-dashboard:latest

# Build + push MCP server
docker build --no-cache -f mcp_server/Dockerfile -t em-mcp ./mcp_server
docker tag em-mcp:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com/em-production-mcp-server:latest

# Force new deployment (task def MUST use :latest tag)
aws ecs update-service --cluster em-production-cluster --service em-production-dashboard --force-new-deployment --region us-east-2
aws ecs update-service --cluster em-production-cluster --service em-production-mcp-server --force-new-deployment --region us-east-2
```

### Secrets & Credentials

| Secret | Location | Purpose |
|--------|----------|---------|
| `SUPABASE_URL` | `.env.local` | `https://YOUR_PROJECT_REF.supabase.co` |
| `SUPABASE_ANON_KEY` | `.env.local` | Publishable key for frontend (`sb_publishable_...`) |
| `SUPABASE_SERVICE_KEY` | `mcp_server/.env` | Service role key (bypasses RLS) |
| `WALLET_PRIVATE_KEY` | `.env.local` | **Dev** agent wallet `YOUR_DEV_WALLET` |
| `SUPABASE_DB_PASSWORD` | `.env.local` | Direct postgres password |
| Supabase Management API | `~/.supabase/access-token` | For running SQL migrations (`sbp_c5dd...`) |
| AWS ECR | Standard AWS CLI auth | `YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-2.amazonaws.com` |

### ChambaEscrow — DEPRECATED (DO NOT USE)

**NEVER reference, deploy, or interact with ChambaEscrow** (`_archive/contracts/`). Fully replaced by x402 SDK + Facilitator.

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
| **SDK** | `uvd-x402-sdk[fastapi]>=0.11.0` (in `mcp_server/requirements.txt`) |
| **SDK Client** | `mcp_server/integrations/x402/sdk_client.py` — `EMX402SDK` class |
| **Facilitator URL** | `https://facilitator.ultravioletadao.xyz` |
| **Facilitator Endpoints** | `POST /verify`, `POST /settle`, `POST /register`, `POST /feedback` |
| **Network** | Base Mainnet (chain 8453) for production payments |
| **ERC-8004 Networks** | 15 total: 9 mainnets + 6 testnets (all via Facilitator) |

**Wallet Roles (CRITICAL — read this before touching payments)**:
- **Dev wallet** (`0x857f`): Used by local scripts and tests. Key in `.env.local`.
- **Platform wallet** (`0xD386`): Used by ECS MCP server. Key in AWS Secret `em/x402:PRIVATE_KEY`. **This is the settlement transit point** — agent funds settle here at approval, then immediately disburse to worker (87%) + treasury (13%). No funds should accumulate here long-term.
- **Treasury** (`0xae07`): Cold wallet (Ledger). **ONLY receives 13% platform fee (12% EM + 1% x402r)** on successful task completion. **NEVER a settlement target.** If funds land here during task creation, it's a bug.
- `EM_SETTLEMENT_ADDRESS` env var (optional): Overrides the platform wallet for settlement. Defaults to address derived from `WALLET_PRIVATE_KEY`.
- **Testing budget**: Always use amounts **< $0.30** for test tasks. ~$5 per chain must last through all testing cycles.

**Payment Mode** (`EM_PAYMENT_MODE`, default: `fase1`):
- **`fase1`** (default, production): No auth at task creation — advisory `balanceOf()` check only. At approval, server signs 2 direct EIP-3009 settlements: agent→worker (bounty) + agent→treasury (fee). No intermediary wallet. E2E tested 2026-02-11 ([evidence](docs/planning/FASE1_E2E_EVIDENCE_2026-02-11.md)).
- **`fase2`** (on-chain escrow, gasless): Locks funds on-chain via AdvancedEscrowClient at task creation. Release/refund via facilitator (gasless). **Fase 3 PaymentOperator on Base: `0x8D3DeCBAe68F6BA6f8104B60De1a42cE1869c2E6`** (OR(Payer,Facilitator) + 1% on-chain fee). Legacy operator: `0xb9635f...`. E2E tested 2026-02-11 ([evidence](docs/planning/FASE2_E2E_EVIDENCE_2026-02-11.md)). Requires `EM_PAYMENT_OPERATOR` env var.
- **`preauth`** (legacy): Agent signs EIP-3009 auth at creation, stored header settled at approval via 3-step flow through platform wallet.
- **`x402r`** (deprecated): Settles agent auth + locks funds in on-chain escrow at creation time. **Do not use** — caused fund loss bug.

**Payment Flow for Tasks** (Fase 1, as of 2026-02-11):
1. **Balance check** (task creation): `balanceOf(agent)` via RPC — advisory only, task creates regardless. No auth signed, no funds move.
2. **Direct settlement** (task approval): Server signs 2 fresh EIP-3009 auths → Facilitator settles both: agent→worker (bounty) + agent→treasury (13% fee). No platform wallet intermediary.
3. **Cancel** (task cancellation): No-op — no auth was ever signed, nothing to refund.
4. **Platform fee**: Configurable via `EM_PLATFORM_FEE` env var (default 13% — 12% EM + 1% x402r). Uses 6-decimal USDC precision with $0.01 minimum fee.

**Payment Flow for Tasks** (Fase 2):
1. **Authorize** (task creation): Lock bounty+fee in on-chain escrow via facilitator (gasless). PaymentInfo stored in escrows table for state reconstruction.
2. **Release** (task approval): Gasless release via facilitator (escrow → platform), then disburse to worker + fee to treasury via EIP-3009.
3. **Refund** (task cancellation): Gasless refund via facilitator — funds return directly to agent wallet.
4. **Query state**: `em_check_escrow_state` MCP tool reads on-chain escrow state (capturableAmount, refundableAmount).

**Audit Trail**: All payment events are logged to `payment_events` table (migration 027). Tracks verify, store_auth, settle, disburse_worker, disburse_fee, refund, cancel, error events with tx hashes and amounts.

**Manual Refund Procedure** (for fund loss incidents):
- If `payment_events` shows a `settle` with `status=success` but no corresponding `disburse_worker`, funds are stuck in the settlement target wallet.
- Check `escrows.metadata.agent_settle_tx` for the on-chain settlement tx.
- Manual refund must be sent from the wallet that received the funds back to the agent wallet.
- Incident Feb 2026: 3 tasks ($0.54 + $0.54 + $0.324 = $1.404) settled to treasury `0xae07` instead of platform wallet. Requires Ledger refund to `0x13ef` on Base.

### x402r Escrow System (Fase 2 — In Progress)

**Full reference:** [`docs/planning/X402R_REFERENCE.md`](docs/planning/X402R_REFERENCE.md) — architecture, ABIs, all contract addresses, condition system, deployment guide.

**Architecture (3 layers):**
- **Layer 1:** `AuthCaptureEscrow` — shared singleton per chain, holds funds in TokenStore clones (EIP-1167)
- **Layer 2:** `PaymentOperator` — per-config contract with pluggable conditions (who can authorize/release/refund)
- **Layer 3:** `Facilitator` — off-chain server, pays gas, enforces business logic

**>>> IMPORTANT: Active Fase 3 Clean Operator** (`0xd5149049e7c212ce5436a9581b4307EB9595df95` on Base): OR(Payer|Facilitator) release/refund, **feeCalculator=address(0) — NO on-chain operator fee**. All contract addresses in the On-Chain Contracts table above. Old operators (Fase 3 v1 at `0x8D3D...`, Fase 2 at `0xb963...`) are legacy — keep for historical tasks only.

**Deployment script:** `scripts/deploy-payment-operator.ts` — deploys via x402r factory contracts. Use `--fase3` flag.

**Status:** Fase 3 PaymentOperator deployed on Base (2026-02-12). Facilitator v1.33.3 supports Vec<Address> for multi-operator. Need to register new operator in facilitator `addresses.rs`. Other 7 networks pending deployment.

**Key upstream repos:**
| Repo | URL | Stack |
|------|-----|-------|
| x402r-contracts | `github.com/BackTrackCo/x402r-contracts` | Foundry (Solidity) |
| x402r-sdk | `github.com/BackTrackCo/x402r-sdk` | TypeScript monorepo (pnpm) |
| x402r docs | `github.com/BackTrackCo/docs` | Mintlify (docs.x402r.org) |

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
- `tasks.payment_network` (migration 023, default `'base'`)

**Known RLS issues**:
- `submissions` INSERT policy requires `executor.user_id = auth.uid()`. If the executor isn't linked to the anonymous session, inserts fail **silently** (no error, just 0 rows). SubmissionForm.tsx now uses `submitWork()` which handles this with proper error messages.

### Known Bugs & TODOs

- [ ] `EvidenceUpload.tsx` (camera, GPS, EXIF) is unused — `SubmissionForm.tsx` is a simpler version
- [ ] $0.10 USDC stuck in vault from direct relay deposit (tx `0xda31cbe...`). Needs refund or contract expiry
- [ ] Incident Feb 2026: 3 tasks ($1.404) settled to treasury `0xae07` instead of platform wallet. Pending Ledger refund to `0x13ef` on Base

### Golden Flow (Comprehensive E2E Acceptance Test)

The **Golden Flow** is the definitive acceptance test. If the Golden Flow passes, the platform is healthy. It tests EVERYTHING end-to-end on production (Base Mainnet):

**Script**: `python scripts/e2e_golden_flow.py`

**What it tests (in order):**
1. **Health check** — API reachable
2. **Task creation** — Fase 2 escrow lock on-chain ($0.10 bounty, 13% fee = $0.113 locked)
3. **Worker auto-registration** — Worker registers via API (creates executor profile)
4. **ERC-8004 Identity** — Worker gets on-chain identity via Facilitator (gasless)
5. **Task application** — Worker applies to task
6. **Task assignment** — Agent assigns worker
7. **Evidence submission** — Worker submits evidence (stored on S3/CloudFront CDN)
8. **Task approval + payment** — Agent approves, 3 on-chain TXs: escrow release, worker payout ($0.10), fee collection ($0.013)
9. **Agent rates worker** — Reputation feedback (on-chain via Facilitator)
10. **Worker rates agent** — Bidirectional reputation
11. **On-chain verification** — All TXs verified via Base RPC
12. **Reputation verification** — Scores readable from ERC-8004 Reputation Registry

**Reports generated:**
- `docs/reports/GOLDEN_FLOW_REPORT.md` (English)
- `docs/reports/GOLDEN_FLOW_REPORT.es.md` (Spanish)

**Separate reports (focused):**
- `docs/reports/PAYMENT_FLOW_REPORT.md` — Escrow + fee split only (existing Complete Flow Report)
- `docs/reports/ERC8004_FLOW_REPORT.md` — Identity + reputation only

### Facilitator Ownership (CRITICAL)

**The Facilitator (`facilitator.ultravioletadao.xyz`) is OURS — Ultravioleta DAO.** Repo: `UltravioletaDAO/x402-rs`. We deploy, control, and maintain it. Ali/BackTrack has NOTHING to do with the Facilitator.

- **Ali Abdoli / BackTrack** = x402r protocol (contracts, factories, ProtocolFeeConfig). NOT the Facilitator.
- **Ultravioleta DAO** = Facilitator server, pays gas, enforces business logic.

### x402r Protocol Fee (Automatic Handling)

BackTrack controls `ProtocolFeeConfig` (`0x59314674...`) — a shared singleton affecting ALL operators on Base. They can enable a protocol fee (up to 5% hard cap) with 7-day timelock notice. This is by design and we trust them with this authority.

**Our code reads the protocol fee from chain dynamically** (not from an env var). When BackTrack enables their fee:
- Agent still pays 13% total
- x402r protocol deducts their % on-chain at escrow release
- Worker ALWAYS receives 100% of bounty (fee comes from agent surplus)
- Treasury receives: `13% - protocol_fee%` (the remainder)
- No manual intervention needed — fully automatic

### Task Factory Guidelines

When creating test tasks:
- **Deadlines**: 5-15 minutes for testing, NOT hours.
- **Bounties**: Use amounts **under $0.20** for testing. Each mainnet wallet has ~$4 USDC on Base — keep tests small to make funds last. Never use $0.50+ amounts for test tasks. The E2E script uses `TEST_BOUNTY = 0.10`. Ignore any DB-level `min_bounty` config for local E2E testing.
- **Script**: `cd scripts && npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10`
- **E2E script**: `python scripts/e2e_mcp_api.py` — tests full lifecycle through REST API ($0.10 bounties)
- **Live escrow**: Add `--live` flag (requires USDC in wallet + uses relay directly — needs SDK migration)
- **Production wallet only**: Use `YOUR_PLATFORM_WALLET` for mainnet testing (funded on all 8 chains)

### ERC-8004 Identity

Agent ID **2106** on Base (production). Registry addresses in On-Chain Contracts table above. Registration and reputation via Facilitator (`POST /register`, `POST /feedback`) — gasless.

**Supported ERC-8004 Networks (15)**: 9 mainnets (ethereum, base, polygon, arbitrum, celo, bsc, monad, avalanche, optimism) + 6 testnets (ethereum-sepolia, base-sepolia, polygon-amoy, arbitrum-sepolia, celo-sepolia, avalanche-fuji). Network naming uses `Network` enum: `"base"`, `"polygon"`, etc. Our code keeps `"base-mainnet"` as alias.

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

**Reputation & Identity (`/api/v1/reputation`):**
- `GET /api/v1/reputation/em` — EM reputation score
- `GET /api/v1/reputation/agents/{id}` — Agent reputation
- `POST /api/v1/reputation/workers/rate` — Rate worker
- `POST /api/v1/reputation/agents/rate` — Rate agent
- `POST /api/v1/reputation/register` — Gasless agent/worker registration (any of 15 networks)
- `GET /api/v1/reputation/networks` — List supported ERC-8004 networks

**WebSocket:**
- `WS /ws` — Real-time task notifications
- `GET /ws/stats` — WebSocket stats

#### Admin Dashboard (`admin.execution.market`)

| Resource | Details |
|----------|---------|
| URL | `https://admin.execution.market` |
| Hosting | S3 (`em-production-admin-dashboard`) + CloudFront (`E2IUZLTDUFIAQP`) |
| CDN Domain | `d10ucc05zs1fwn.cloudfront.net` |
| ACM Cert | `arn:aws:acm:us-east-1:YOUR_AWS_ACCOUNT_ID:certificate/841084f8-b130-4b12-87ee-88ac7d81be24` |
| OAC | `E3HPQ9VBJWQVDR` |
| Auth | Admin key via `X-Admin-Key` header (key in `EM_ADMIN_KEY` secret) |
| CI/CD | `.github/workflows/deploy-admin.yml` — auto-deploy on push to `main` when `admin-dashboard/**` changes |
| Manual Deploy | `cd admin-dashboard && VITE_API_URL=https://mcp.execution.market npm run build && aws s3 sync dist/ s3://em-production-admin-dashboard/ --delete --cache-control "public, max-age=31536000" --exclude "index.html" && aws s3 cp dist/index.html s3://em-production-admin-dashboard/index.html --cache-control "no-cache" --content-type "text/html"` |
| Terraform | `infrastructure/terraform/admin-dashboard.tf` (resources created via CLI, importable) |

#### Not Yet Deployed

| App | Directory | Intended URL | Status |
|-----|-----------|-------------|--------|
| Docs Site | `docs-site/` | `docs.execution.market` | VitePress, no pipeline |
| Landing Pages | `landing/` | N/A | Static HTML, no deployment |

### Key Integration Files

| File | Purpose |
|------|---------|
| `mcp_server/integrations/x402/sdk_client.py` | x402 SDK wrapper + multichain token registry (12 EVM, 4 stablecoins) — **USE THIS for all payments** |
| `mcp_server/integrations/x402/client.py` | Direct HTTP facilitator client (fallback) |
| `mcp_server/integrations/x402/advanced_escrow_integration.py` | Advanced escrow flows documentation |
| `mcp_server/integrations/erc8004/facilitator_client.py` | ERC-8004 identity, reputation, registration (15 networks) |
| `mcp_server/integrations/erc8004/identity.py` | Worker identity check + gasless registration |
| `mcp_server/api/routes.py` | REST API endpoints (task CRUD, submissions, escrow) |
| `mcp_server/api/reputation.py` | Reputation + registration endpoints |
| `mcp_server/server.py` | MCP tools for AI agents |
| `dashboard/src/components/TaskApplicationModal.tsx` | Task acceptance flow |
| `dashboard/src/components/SubmissionForm.tsx` | Evidence upload (uses `submitWork()` service) |
| `dashboard/src/hooks/useProfileUpdate.ts` | Profile update with executor ID resolution |
| `dashboard/src/context/AuthContext.tsx` | Auth state with wallet-based executor lookup |
