# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Developer

| Field | Value |
|-------|-------|
| Name | 0xultravioleta |
| Email | 0xultravioleta@gmail.com |
| GitHub | [@ultravioletadao](https://github.com/ultravioletadao) |

## Project Overview

Execution Market is the **Universal Execution Layer** — the infrastructure that converts AI intent into physical action. A marketplace where AI agents publish bounties for real-world tasks that executors (humans today, robots tomorrow) complete, with instant gasless payment via x402. Registered as **Agent #2106** on Base ERC-8004 Identity Registry (previously #469 on Sepolia).

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

When the user says **"Conéctate a IRC"**, **"charla con el equipo"**, **"chat on IRC"**, or similar — use the **irc-agent** skill at `.claude/skills/irc-agent/SKILL.md`. This connects to `irc.meshrelay.xyz` channel `#Agents` for inter-agent and human-agent collaboration. Config at `.claude/irc-config.json`. Skill source: `https://github.com/0xultravioleta/irc-agent-skill`.

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

The backend test suite (**950 tests**) is organized with **pytest markers** for selective execution. All tests are active — no dormant or redundant markers remain after the 2026-02-17 dead code cleanup.

```bash
cd mcp_server

# Default run — all 950 tests
pytest

# Specific profiles
pytest -m core                             # Core business logic (276 tests)
pytest -m erc8004                          # ERC-8004 integration (177 tests)
pytest -m payments                         # Payment flows (251 tests)
pytest -m security                         # Fraud, GPS, auth (61 tests)
pytest -m infrastructure                   # Webhooks, WS, A2A (77 tests)

# Combine profiles
pytest -m "core or erc8004"                # Core + ERC-8004
pytest -m "core or payments"               # Core + payments
```

**Marker reference** (`mcp_server/pytest.ini`):

| Marker | Tests | What it covers |
|--------|-------|----------------|
| `core` | 276 | Routes, MCP tools, auth, reputation, workers, platform config, architecture |
| `payments` | 251 | PaymentDispatcher, escrow, fees, multichain, protocol fee |
| `erc8004` | 177 | Scoring, side effects, auto-registration, rejection, reputation tools, ERC-8128 |
| `security` | 61 | Fraud detection, GPS antispoofing |
| `infrastructure` | 77 | Webhooks, WebSocket, A2A, timestamps |
| *(unmarked)* | 153 | A2A protocol, gas dust, prepare feedback, task transactions |

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
      "args": ["Z:/ultravioleta/dao/execution-market/mcp_server/server.py"],
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
- **To deploy/redeploy PaymentOperators**: Use the **`deploy-operator` skill** (`.claude/skills/deploy-operator/SKILL.md`) — deploys Fase 5 operators on any supported chain
- Token registry lives in `mcp_server/integrations/x402/sdk_client.py` (`NETWORK_CONFIG` dict — single source of truth, 15 EVM networks, 5 stablecoins, 10 with x402r escrow)
- Other Python files (facilitator_client, tests, platform_config) **auto-derive** from sdk_client.py — no manual updates needed

## On-Chain Contracts

| Contract | Network | Address |
|----------|---------|---------|
| ERC-8004 Identity Registry | All Mainnets (CREATE2) | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| ERC-8004 Identity Registry | All Testnets (CREATE2) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| ERC-8004 Reputation Registry | All Mainnets (CREATE2) | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |
| x402r Escrow (AuthCaptureEscrow) | Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| x402r Escrow (AuthCaptureEscrow) | Ethereum | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` |
| x402r Escrow (AuthCaptureEscrow) | Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| x402r Escrow (AuthCaptureEscrow) | Arbitrum, Avalanche, Celo, Monad, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| x402r Escrow (legacy, deprecated) | Base | `0xC409e6da89E54253fbA86C1CE3E553d24E03f6bC` |
| **EM PaymentOperator (Fase 5 Trustless Fee Split)** | **Base** | **`0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`** |
| **EM PaymentOperator (Fase 5)** | **Ethereum** | **`0x69B67962ffb7c5C7078ff348a87DF604dfA8001b`** |
| **EM PaymentOperator (Fase 5)** | **Polygon** | **`0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`** |
| **EM PaymentOperator (Fase 5)** | **Arbitrum** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |
| **EM PaymentOperator (Fase 5)** | **Avalanche** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |
| **EM PaymentOperator (Fase 5)** | **Monad** | **`0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`** |
| **EM PaymentOperator (Fase 5)** | **Celo** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |
| **EM PaymentOperator (Fase 5)** | **Optimism** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |
| StaticFeeCalculator(1300bps) | Base | `0xd643DB63028Cd1852AAFe62A0E3d2A5238d7465A` |
| StaticFeeCalculator(1150bps, unused) | Base | `0x256eb4454a440767aE688a257ff8EadcBF180EF0` |
| PaymentOperator (Fase 5 1150bps, unused) | Base | `0x466191B6830f23BB6A7A99a62F8dee9CC48e2Cd9` |
| EM PaymentOperator (Fase 4 Secure, legacy) | Base | `0x030353642B936c9D4213caD7BcB0fB8a1489cBe5` |
| EM PaymentOperator (Fase 3 Clean, legacy) | Base | `0xd5149049e7c212ce5436a9581b4307EB9595df95` |
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

**IMPORTANT**: Always use the **default AWS account** (`518898403364`, user `cuchorapido`). Do NOT use account `897729094021` — it is not the deployment target and lacks proper permissions for Execution Market infrastructure.

| Resource | Details |
|----------|---------|
| AWS Account | `518898403364` (default profile) |
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
| `X402_RPC_URL` | AWS SM `em/x402:X402_RPC_URL` | **QuikNode private Base RPC** (avoid public rate limits) |

**Deploy scripts & dotenv**: All TypeScript scripts in `scripts/` load `.env.local` automatically via `dotenv.config({ path: "../.env.local" })`. The `WALLET_PRIVATE_KEY` from `.env.local` is accepted as `PRIVATE_KEY` alias. No need to set env vars manually — just run `npx tsx script.ts` from `scripts/` directory.

### Legacy Custom Escrow — DEPRECATED (DO NOT USE)

**NEVER reference, deploy, or interact with the legacy custom escrow contract** (`_archive/contracts/`). Fully replaced by x402 SDK + Facilitator.

### x402 Payment Architecture

**>>> CRITICAL — ALWAYS USE SDK + FACILITATOR <<<**
Always use the **x402 SDK** (`uvd-x402-sdk`) and the **Ultravioleta Facilitator** for ALL payment operations. **NEVER call contracts directly. NEVER send raw transactions to escrow contracts.** If you're writing `contract.functions.` or `cast send` to a payment contract, you're doing it wrong.

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
- **Treasury** (`0xae07`): Cold wallet (Ledger). **ONLY receives 13% platform fee** on successful task completion (treasury = remainder after worker payment; absorbs x402r protocol fee automatically). **NEVER a settlement target.** If funds land here during task creation, it's a bug.
- `EM_SETTLEMENT_ADDRESS` env var (optional): Overrides the platform wallet for settlement. Defaults to address derived from `WALLET_PRIVATE_KEY`.
- `EM_REPUTATION_RELAY_KEY` env var (optional): Private key for a dedicated relay wallet used when workers rate agents. Platform wallet can't rate Agent #2106 (self-feedback revert). Relay wallet must NOT own any agent NFTs and needs ~0.001 ETH on Base for gas. If not set, worker→agent feedback falls back to Facilitator.
- **Test worker wallet** (`0x52E05C8e45a32eeE169639F6d2cA40f8887b5A15`): Used by Golden Flow for worker-side operations. Key in AWS Secret `em/test-worker:private_key`. Set as `EM_WORKER_PRIVATE_KEY` for worker→agent reputation in multichain Golden Flow tests.
- **Testing budget**: Always use amounts **< $0.30** for test tasks. ~$5 per chain must last through all testing cycles.

**Payment Mode** (`EM_PAYMENT_MODE`, default: `fase1`):
- **`fase1`** (default, production): No auth at task creation — advisory `balanceOf()` check only. At approval, server signs 2 direct EIP-3009 settlements: agent→worker (bounty) + agent→treasury (fee). No intermediary wallet. E2E tested 2026-02-11 ([evidence](docs/planning/FASE1_E2E_EVIDENCE_2026-02-11.md)).
- **`fase2`** (on-chain escrow, gasless): Locks funds on-chain via AdvancedEscrowClient at task creation. Release/refund via facilitator (gasless). **Active Fase 5 Operator on Base: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`** — StaticFeeCalculator(1300 BPS = 13%), trustless fee split at release. E2E tested 2026-02-13. Requires `EM_PAYMENT_OPERATOR` env var.
- **`preauth`** (legacy): Agent signs EIP-3009 auth at creation, stored header settled at approval via 3-step flow through platform wallet.
- **`x402r`** (deprecated): Settles agent auth + locks funds in on-chain escrow at creation time. **Do not use** — caused fund loss bug.

**Payment Flow for Tasks** (Fase 1, as of 2026-02-11):
1. **Balance check** (task creation): `balanceOf(agent)` via RPC — advisory only, task creates regardless. No auth signed, no funds move.
2. **Direct settlement** (task approval): Server signs 2 fresh EIP-3009 auths → Facilitator settles both: agent→worker (bounty) + agent→treasury (13% fee). No platform wallet intermediary.
3. **Cancel** (task cancellation): No-op — no auth was ever signed, nothing to refund.
4. **Platform fee**: Configurable via `EM_PLATFORM_FEE` env var (default 13%). Uses 6-decimal USDC precision with $0.01 minimum fee. Treasury absorbs any x402r protocol fee automatically via `_compute_treasury_remainder()`.

**Payment Flow for Tasks** (Fase 2 — platform_release mode, legacy):
1. **Authorize** (task creation): Lock bounty+fee in on-chain escrow via facilitator (gasless). PaymentInfo stored in escrows table for state reconstruction. Escrow receiver = platform wallet.
2. **Release** (task approval): 2 TXs only — (1) gasless release via facilitator (escrow → platform), (2) disburse bounty to worker via EIP-3009. Fee **stays in platform wallet** (accrued, not transferred per-task).
3. **Refund** (task cancellation): Gasless refund via facilitator — funds return directly to agent wallet.
4. **Query state**: `em_check_escrow_state` MCP tool reads on-chain escrow state (capturableAmount, refundableAmount).
5. **Fee sweep** (admin): `POST /api/v1/admin/fees/sweep` — batch transfer all accrued fees from platform wallet to treasury in a single TX. `GET /api/v1/admin/fees/accrued` to check balance.

**Payment Flow for Tasks** (Fase 5 — credit card model, TRUSTLESS):
1. **Balance check** (task creation): Advisory `balanceOf()` check only. Escrow deferred to assignment (worker address unknown at creation). Escrow status = `pending_assignment`.
2. **Escrow lock** (task assignment): Lock bounty in escrow with **worker as direct receiver**. Bounty = lock amount (credit card model). No separate fee collection — fee calculator handles split at release.
3. **Release** (task approval): **1 TX only** — gasless release via facilitator. Fee calculator splits atomically: worker gets 87% (net), operator holds 13% (fee). `distributeFees()` flushes fee to treasury.
4. **Cancel** (published or accepted): Published → no-op (no escrow locked). Accepted → refund full bounty from escrow to agent. No separate fee refund needed.
5. **Fee distribution**: `distributeFees()` called best-effort after each release, or via admin endpoint `POST /admin/fees/sweep`.
- **Env var**: `EM_ESCROW_MODE=direct_release` (default: `platform_release` for backward compat)
- **Fee model**: Credit card convention — fee is 13% of gross (bounty), deducted on-chain. Agent pays $0.10, worker gets $0.087, treasury gets $0.013.
- **Trust model**: Fully trustless — platform never touches funds. Escrow pays worker, operator holds fee for treasury.

**Audit Trail**: All payment events are logged to `payment_events` table (migration 027). Tracks verify, store_auth, settle, disburse_worker, disburse_fee, refund, cancel, error events with tx hashes and amounts.

**Manual Refund Procedure** (for fund loss incidents):
- If `payment_events` shows a `settle` with `status=success` but no corresponding `disburse_worker`, funds are stuck in the settlement target wallet.
- Check `escrows.metadata.agent_settle_tx` for the on-chain settlement tx.
- Manual refund must be sent from the wallet that received the funds back to the agent wallet.

### x402r Escrow System (Fase 2 — In Progress)

**Full reference:** [`docs/planning/X402R_REFERENCE.md`](docs/planning/X402R_REFERENCE.md) — architecture, ABIs, all contract addresses, condition system, deployment guide.

**Architecture (3 layers):**
- **Layer 1:** `AuthCaptureEscrow` — shared singleton per chain, holds funds in TokenStore clones (EIP-1167)
- **Layer 2:** `PaymentOperator` — per-config contract with pluggable conditions (who can authorize/release/refund)
- **Layer 3:** `Facilitator` — off-chain server, pays gas, enforces business logic

**>>> ACTIVE: Fase 5 Operator (Trustless Fee Split)** (`0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` on Base) — StaticFeeCalculator(1300 BPS = 13%) auto-splits at release: worker gets 87%, operator holds 13%. `distributeFees(USDC)` flushes to EM treasury. Facilitator-ONLY refund (Fase 4 security retained). Deployed + verified on-chain 2026-02-13. **Pending**: Register in Facilitator allowlist.

**Deployment script:** `scripts/deploy-payment-operator.ts` — deploys via x402r factory contracts. Use `--fase3`, `--fase3-clean`, or `--fase4` flag.

**Status:** Fase 5 Operators deployed on **8 chains** (2026-02-20): Base (`0x271f...D8F0Eb`), Ethereum (`0x69B6...001b`), Polygon (`0xB87F...102e`), Arbitrum (`0xC237...938e`), Avalanche (`0xC237...938e`), Monad (`0x9620...8cC3`), Celo (`0xC237...938e`), Optimism (`0xC237...938e`). Credit card model: bounty = lock amount, fee deducted on-chain at release (13% of gross). ALL 8 operators active in Facilitator allowlist. Golden Flow 7/8 PASS consolidated (2026-02-21).

**Key upstream repos:**
| Repo | URL | Stack |
|------|-----|-------|
| x402r-contracts | `github.com/BackTrackCo/x402r-contracts` | Foundry (Solidity) |
| x402r-sdk | `github.com/BackTrackCo/x402r-sdk` | TypeScript monorepo (pnpm) |
| x402r docs | `github.com/BackTrackCo/docs` | Mintlify (docs.x402r.org) |

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

### Facilitator Ownership

**>>> CRITICAL — FACILITATOR IS OURS <<<**
**The Facilitator (`facilitator.ultravioletadao.xyz`) is OURS — Ultravioleta DAO.** Repo: `UltravioletaDAO/x402-rs`. We deploy, control, maintain. **Ali/BackTrack = x402r protocol (contracts, ProtocolFeeConfig) ONLY. NOT the Facilitator.** NEVER say Ali owns/controls the Facilitator.

### x402r Protocol Fee (Automatic Handling)

BackTrack controls `ProtocolFeeConfig` (`0x59314674...`) — a shared singleton affecting ALL operators on Base. They can enable a protocol fee (up to 5% hard cap) with 7-day timelock notice. This is by design and we trust them with this authority.

**Our code reads the protocol fee from chain dynamically** (not from an env var). When BackTrack enables their fee:
- Agent still pays 13% total
- x402r protocol deducts their % on-chain at escrow release
- Worker ALWAYS receives 100% of bounty (fee comes from agent surplus)
- Treasury receives: `13% - protocol_fee%` (the remainder)
- No manual intervention needed — fully automatic

### Task Factory Guidelines

**>>> IMPORTANT: Testing Budget Rules <<<**
- **Bounties**: **ALWAYS under $0.20** for testing. Each mainnet wallet has ~$4 USDC — keep tests small. Never $0.50+. E2E script uses `TEST_BOUNTY = 0.10`.
- **Deadlines**: 5-15 minutes for testing, NOT hours.
- **Script**: `cd scripts && npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10`
- **E2E script**: `python scripts/e2e_mcp_api.py` — tests full lifecycle through REST API ($0.10 bounties)
- **Live escrow**: Add `--live` flag (requires USDC in wallet + uses relay directly — needs SDK migration)
- **Production wallet only**: Use `0xD3868E1eD738CED6945A574a7c769433BeD5d474` for mainnet testing (funded on all 8 chains)

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

#### API Endpoints

Full interactive docs at **`https://api.execution.market/docs`** (Swagger UI) or `/redoc`.

**Key endpoint groups** (`/api/v1`):
- **Tasks**: CRUD, batch create, cancel+refund, submissions (API key required)
- **Workers**: Register, browse available, apply, submit evidence
- **Admin** (`/admin`): Stats, task override, payments, user mgmt, platform config (Admin key)
- **Escrow**: Config, balance, release, refund
- **Reputation**: Scores, rate worker/agent, gasless registration (15 networks)
- **Health**: `/health`, `/health/live`, `/health/ready`, `/health/metrics`, `/health/version`
- **MCP**: `POST /mcp/` (SSE transport), `GET /mcp/` (session init)
- **WebSocket**: `WS /ws` (real-time notifications)

#### Admin Dashboard (`admin.execution.market`)

S3 + CloudFront. Auth via `X-Admin-Key` header. CI/CD: `.github/workflows/deploy-admin.yml` (auto on push to `main` when `admin-dashboard/**` changes). Terraform: `infrastructure/terraform/admin-dashboard.tf`.

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
