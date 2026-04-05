# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Local overrides**: See `CLAUDE.md.local` (gitignored) for real AWS account IDs, ECR URIs, wallet addresses, and copy-paste deploy commands. That file replaces the `<YOUR_*>` placeholders used throughout this file.

## Engineering Discipline — ABSOLUTE RULES

> **NEVER use quick fixes, hardcodes, or workarounds.** Always find and fix the root cause. If you need more logs/traces to diagnose, add them. If the fix requires changing the skill, change the skill. If it requires changing the contract interface, document what needs to change. Quick fixes create debt that compounds into production outages. See INC-2026-03-24 for the cascading failures caused by incomplete ADR-001 migration.

> **NEVER hardcode private keys, API keys, or secrets in ANY source file.** This is a ZERO-TOLERANCE rule. Two incidents (INC-2026-03-23, INC-2026-03-30) resulted in wallet drains because private keys were hardcoded in debug/test scripts that got committed to the public repo. **ALL secrets MUST be read from:** (1) Environment variables (`process.env.*`, `os.environ.*`), (2) AWS Secrets Manager, or (3) `.env.local` (gitignored). **NEVER create throwaway/debug scripts with inline keys** — not even "temporarily". The pre-commit hook in `.git/hooks/pre-commit` scans for `0x` + 64 hex chars and blocks the commit. If you need to test with a key, use `.env.local` and `dotenv`. If Clawd Bot or any agent produces a file with a hardcoded key, DELETE IT and rewrite to use env vars before committing.

> **NEVER use broad `git add -A` or `git add .`** when committing. Always stage specific files by name. Broad staging is how throwaway debug scripts with secrets get accidentally committed. See INC-2026-03-30.

## Open Items — Remind Me

> **[RESOLVED 2026-03-27] API key auth disabled by default** — `EM_API_KEYS_ENABLED=false` (default). All API key auth (x-api-key, Bearer) returns HTTP 403. Only ERC-8128 wallet signing is accepted. This closes the security hole where external agents could use API keys to create tasks as Agent #2106 (platform identity), potentially spending the platform wallet. To re-enable for internal testing: set `EM_API_KEYS_ENABLED=true` in ECS task definition. See INC-2026-03-27.

> **[PARTIALLY RESOLVED 2026-03-22] ERC-8004 identity enforcement** — `EM_REQUIRE_ERC8004=true` deployed on ECS rev 256. Server now returns HTTP 403 for unregistered ERC-8128 agents at `POST /tasks`. `EM_REQUIRE_ERC8004_WORKER=true` deployed on ECS rev 257 — workers auto-register gaslessly at apply time. Phase 4 em-* skills guard also complete (6 skills updated, em-browse-tasks skipped as read-only). skill.md bumped to v3.5.0 with hard enforcement text. See `docs/planning/MASTER_PLAN_ERC8004_ENFORCEMENT.md`. **Remaining**: audit after OWS integration ships to verify no silent fallback to Agent #2106.

## Skill Versioning (IMPORTANT)

**`dashboard/public/skill.md` is the canonical skill file that external agents install.** It has a `version` field in its YAML frontmatter. Every time you modify this file, you MUST:

1. **Bump the version** — use semantic versioning:
   - `PATCH` (x.x.+1): typo fixes, clarifications, no behavior change
   - `MINOR` (x.+1.0): new sections, new options, backward-compatible changes
   - `MAJOR` (+1.0.0): breaking changes (removed options, changed defaults, new required steps)
2. **Add a row to the Changelog table** at the top of the file with date + summary
3. **Sync backend copy**: `cp dashboard/public/skill.md mcp_server/skills/SKILL.md`
4. **Commit with the version in the message**, e.g. `feat(skill): v3.1.0 — wallet required`

**Current version**: check `dashboard/public/skill.md` frontmatter — `version: x.x.x`
**Served at**: `https://execution.market/skill.md` (canonical) and `https://api.execution.market/skill.md` (backend copy)
**Agents check for updates by comparing their installed version against the `version` field in the live file.**
**CI enforces sync**: The `skill-sync-check` job fails if `dashboard/public/skill.md` != `mcp_server/skills/SKILL.md`. Always edit the canonical and copy to backend.
**NEVER edit `mcp_server/skills/SKILL.md` directly** — it's a copy. Edit `dashboard/public/skill.md` and sync.

## Project Overview

Execution Market is the **Universal Execution Layer** — the infrastructure that converts AI intent into physical action. A marketplace where AI agents publish bounties for real-world tasks that executors (humans today, robots tomorrow) complete, with instant gasless payment via x402. Registered as **Agent #2106** on Base ERC-8004 Identity Registry (previously #469 on Sepolia).

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend MCP Server | Python 3.10+ + FastMCP + Pydantic v2 |
| Database | Supabase (PostgreSQL) |
| Dashboard | React 18 + TypeScript + Vite + Tailwind CSS |
| Blockchain Scripts | TypeScript + viem |
| Payments | x402 SDK + Facilitator (10 networks: 9 EVM + Solana, gasless) |
| Evidence Storage | S3 + CloudFront CDN (presigned uploads) |
| Agent Identity | ERC-8004 Registry (16 networks via Facilitator) |
| Proof of Humanity | World ID 4.0 (Cloud API v4, RP signing, IDKit) |
| Agent Wallet | [Open Wallet Standard](https://openwallet.sh) (OWS) — MCP server in `ows-mcp-server/` |
| SDKs | Python `uvd-x402-sdk[wallet]>=0.21.0` / TypeScript `uvd-x402-sdk@2.36.0` |

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
├── ows-mcp-server/      # OWS MCP Server (wallet mgmt for AI agents)
└── agent-card.json      # ERC-8004 agent metadata
```

## Git Workflow

**IMPORTANT: Commit Policy**
- ✅ **Commit freely**: Create commits when tasks are complete or logical checkpoints are reached
- ❌ **Never auto-push**: Do NOT push to remote unless explicitly requested by the user
- ⚠️ **Push only when asked**: Only run `git push` when the user explicitly says "push" or "pusha" or similar

**Rationale**: Pushing triggers CI/CD pipelines (GitHub Actions) which take ~20 minutes. User wants control over when deployments happen.

**Workflow:** Make changes → commit locally → user tests → user says "push" → then `git push`.

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

**How to ask: USE AskUserQuestion TOOL**
When presenting decisions with multiple options (architecture questions, config choices, master plan open questions), **always use the AskUserQuestion tool** instead of listing options in plain text. This gives the user structured choices that are faster to respond to.

**Rule of thumb**: If the answer is "obviously yes", don't ask—just do it and report what you did.

## Focus Discipline — One Thread at a Time

**CRITICAL: Protect the conversation context from topic drift.**

The user tends to branch into new ideas mid-conversation. This is natural but poisons the context and derails progress. Claude's job is to **keep the train on the rails**.

### Rules

1. **One topic per conversation.** When a conversation starts working on X, finish X before switching.
2. **Detect off-topic input.** If the user mentions something unrelated to the current task, do NOT engage with it immediately. Instead:
   - Acknowledge it briefly: *"Anotado."*
   - Append it to the **backlog file** (see below)
   - Continue with the current task
3. **Never let the user derail without consent.** If the user starts going down a rabbit hole, gently redirect: *"Eso lo anoté en el backlog. Sigamos con [current task] — nos falta [X]."*
4. **Handoffs, not context switches.** If the off-topic item is urgent or complex, create a **handoff note** instead of switching context:
   - Write a brief description in the backlog with enough context for the next conversation to pick it up
   - Tag it with priority if obvious (P0 = do next, P1 = soon, P2 = eventually)
5. **Backlog review.** At the END of a conversation (or when the user explicitly asks), summarize what's in the backlog so the user can prioritize the next session.

### Backlog File

Location: `docs/planning/BACKLOG.md`

Format:
```markdown
## Backlog

| Date | Item | Context | Priority | Status |
|------|------|---------|----------|--------|
| 2026-03-19 | Add Solana escrow support | Came up during XMTP bug fix | P2 | pending |
```

- Append-only during a conversation (never delete items mid-session)
- User decides what to promote to a Master Plan or tackle next
- Clean up completed items periodically

### What counts as "off-topic"
- New features unrelated to the current task
- Ideas for other parts of the system
- "Oh, also we should..." tangents
- Questions about unrelated components

### What does NOT count as "off-topic"
- Directly related follow-ups ("now that X is fixed, update the test too")
- Necessary context ("this file also has the same bug")
- Blockers ("we can't do X until Y is fixed" — Y becomes the task)

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
| `worldid` | 8 | World ID 4.0 RP signing, Cloud API verify, anti-sybil |
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
cd mcp_server && pip install -e . && python server.py
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
           x402r Escrow (9 EVM networks) + Solana SPL transfers
                ↓
           Payment Release
```

### MCP Tools (for AI agents)

**Execution Market** (18 tools across 4 modules):

| Category | Tool | Description |
|----------|------|-------------|
| **Core** | `em_publish_task` | Publish a new task for human execution |
| | `em_approve_submission` | Approve or reject a submission |
| | `em_cancel_task` | Cancel a published task |
| **Query** | `em_get_tasks` | Get tasks with filters (agent, status, category) |
| | `em_get_task` | Get details of a specific task (includes escrow status + application count) |
| | `em_check_submission` | Check applications and submissions for a task |
| | `em_get_payment_info` | Get payment details for a task |
| | `em_check_escrow_state` | Check escrow lock/release status |
| **Fee** | `em_get_fee_structure` | Get current fee structure (13% split) |
| | `em_calculate_fee` | Calculate fee for a given bounty amount |
| **Worker** | `em_apply_to_task` | Apply to an available task as worker |
| | `em_submit_work` | Submit completed work with evidence |
| | `em_get_my_tasks` | Get tasks assigned to the current worker |
| | `em_withdraw_earnings` | Withdraw earned USDC |
| **Agent** | `em_assign_task` | Assign a task to a specific worker (triggers escrow lock) |
| | `em_batch_create_tasks` | Create multiple tasks in one call |
| | `em_get_task_analytics` | Get analytics for task performance |
| **System** | `em_server_status` | Health check and server status |

**OWS Wallet** (9 tools via `ows-mcp-server/`):

| Tool | Description |
|------|-------------|
| `ows_create_wallet` | Create multi-chain wallet (EVM, Solana, Bitcoin, Cosmos, Tron, TON, Sui, Filecoin) |
| `ows_list_wallets` | List all local wallets |
| `ows_get_wallet` | Get wallet details + all chain addresses |
| `ows_import_wallet` | Import existing private key into encrypted OWS vault |
| `ows_sign_message` | Sign message (any supported chain) |
| `ows_sign_typed_data` | Sign EIP-712 typed data (EVM only) |
| `ows_sign_transaction` | Sign raw transaction (any chain) |
| `ows_sign_eip3009` | Sign USDC escrow authorization for Execution Market (7 EVM chains) |
| `ows_register_identity` | Register ERC-8004 on-chain identity (gasless via Facilitator) |

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
- `world_id_verifications` - World ID proofs with nullifier uniqueness (anti-sybil)

## Environment Variables

Required in `.env.local` (project root):
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `WALLET_PRIVATE_KEY` - For blockchain transactions
- `SEPOLIA_RPC_URL` - Ethereum Sepolia RPC
- `PINATA_JWT_SECRET_ACCESS_TOKEN` - For IPFS uploads
- `SOLANA_RPC_URL` - Solana RPC endpoint (optional, defaults to public mainnet-beta)
- `SOLANA_WALLET_ADDRESS` - Solana wallet for balance checks (base58, no private key needed)
- `WORLD_ID_APP_ID` - World ID application ID (from developer.world.org)
- `WORLD_ID_RP_ID` - Relying Party ID for Cloud API v4
- `WORLD_ID_SIGNING_KEY` - secp256k1 private key for RP signing (hex, no 0x prefix)

Dashboard uses `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`.

### Auth Config
- `EM_API_KEYS_ENABLED` - Enable/disable API key auth (default: `false`). When false, ALL API key requests (x-api-key, Bearer) return HTTP 403. Only ERC-8128 wallet signing is accepted. Set to `true` only for internal testing.
- `EM_REQUIRE_ERC8004` - Require ERC-8004 identity for task creation (default: `true` in production)
- `EM_REQUIRE_ERC8004_WORKER` - Require ERC-8004 identity for workers (default: `true` in production)
- `EM_WORLD_ID_ENABLED` - Enable/disable World ID enforcement on task applications (default: `true`). When true, tasks with bounty >= $500 require Orb-level World ID verification. Threshold is configurable via `worldid.min_bounty_for_orb_usd` in PlatformConfig (single source of truth — frontend reads it from `/api/v1/config`).

### Multichain Payment Config
- `EM_ENABLED_NETWORKS` - Comma-separated list of enabled payment networks (default: `base,ethereum,polygon,arbitrum,celo,monad,avalanche,optimism,skale,solana`)
- `X402_NETWORK` - Default payment network (default: `base`)
- **To add a new chain or stablecoin**: Use the **`add-network` skill** (`.claude/skills/add-network/SKILL.md`) — it has the complete step-by-step checklist
- **To deploy/redeploy PaymentOperators**: Use the **`deploy-operator` skill** (`.claude/skills/deploy-operator/SKILL.md`) — deploys Fase 5 operators on any supported chain
- **Solana**: Uses Fase 1 only (direct SPL transfers, no escrow/operator). USDC + AUSD supported. No PaymentOperator on Solana.
- Token registry lives in `mcp_server/integrations/x402/sdk_client.py` (`NETWORK_CONFIG` dict — single source of truth, 16 EVM networks + Solana, 6 stablecoins, 11 with x402r escrow)
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
| x402r Escrow (AuthCaptureEscrow) | SKALE | `0xBC151792f80C0EB1973d56b0235e6bee2A60e245` |
| **EM PaymentOperator (Fase 5 Trustless Fee Split)** | **Base** | **`0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`** |
| **EM PaymentOperator (Fase 5)** | **Ethereum** | **`0x69B67962ffb7c5C7078ff348a87DF604dfA8001b`** |
| **EM PaymentOperator (Fase 5)** | **Polygon** | **`0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e`** |
| **EM PaymentOperator (Fase 5)** | **Arbitrum** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |
| **EM PaymentOperator (Fase 5)** | **Avalanche** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |
| **EM PaymentOperator (Fase 5)** | **Monad** | **`0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3`** |
| **EM PaymentOperator (Fase 5)** | **Celo** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |
| **EM PaymentOperator (Fase 5)** | **Optimism** | **`0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e`** |
| **EM PaymentOperator (Fase 5)** | **SKALE** | **`0x43E46d4587fCCc382285C52012227555ed78D183`** |
| StaticFeeCalculator(1300bps) | Base | `0xd643DB63028Cd1852AAFe62A0E3d2A5238d7465A` |
| Facilitator EOA | All | `0x103040545AC5031A11E8C03dd11324C7333a13C7` |
| Execution Market Agent ID | **Base** | `2106` |
| Execution Market Agent ID | Sepolia (legacy) | `469` |
| *Solana — no escrow contracts* | *Solana Mainnet* | *Fase 1 only (SPL transfers). ERC-8004 identity via QuantuLabs 8004-solana Anchor programs.* |

## Key Documentation

- `SPEC.md` - Product specification with task categories and edge cases
- `PLAN.md` - Technical architecture and implementation details
- `docs/SYNERGIES.md` - Integration points with ecosystem projects
- `agent-card.json` - ERC-8004 agent metadata (editable)

## Infrastructure & Deployment

**IMPORTANT**: Always use the **default AWS account** (`<YOUR_AWS_ACCOUNT_ID>`, user `<YOUR_IAM_USER>`). Do NOT use account `<OTHER_AWS_ACCOUNT_ID>` — it is not the deployment target and lacks proper permissions for Execution Market infrastructure.

| Resource | Details |
|----------|---------|
| AWS Account | `<YOUR_AWS_ACCOUNT_ID>` (default profile) |
| AWS CLI Access | **Full access** — Claude Code can run `aws` commands directly |
| Region | `us-east-2` (Ohio) |
| Compute | ECS Fargate (`<YOUR_ECS_CLUSTER>`) |
| Container Registry | ECR `us-east-2`: `<YOUR_ECR_DASHBOARD_REPO>`, `<YOUR_ECR_MCP_REPO>` |
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

**Never leave files dangling in root.** If unsure, put in `docs/`.

## Documentation Standards

### Obsidian-Compatible Markdown (MANDATORY)

**ALL `.md` files created or modified MUST follow Obsidian vault conventions.** This ensures every document is interconnected and navigable in the Obsidian knowledge graph.

**YAML Frontmatter** — Every `.md` file MUST start with frontmatter:
```yaml
---
date: YYYY-MM-DD
tags:
  - type/<type>       # concept, adr, incident, runbook, report, plan, guide
  - domain/<domain>   # payments, identity, infrastructure, blockchain, testing, agents, business, integrations, security, operations
status: active        # draft | active | completed | archived | deprecated
aliases:
  - alternate name    # Optional: other names for this concept
related-files:        # Optional: source code paths
  - mcp_server/path/to/file.py
---
```

**Wikilinks** — Use `[[wikilinks]]` to connect related concepts:
- When mentioning a concept that has (or should have) its own note, wrap it: `[[x402r-escrow]]`, `[[golden-flow]]`, `[[erc-8004]]`
- Use aliases for display: `[[erc-8004|ERC-8004 Identity Registry]]`
- Every note should link to at least 2-3 related notes

**Naming** — kebab-case for all filenames:
- Concepts: `x402r-escrow.md`, `payment-operator.md`
- ADRs: `ADR-NNN-short-title.md`
- Runbooks: `runbook-short-title.md`
- Incidents: `INC-YYYY-MM-DD-title.md`
- Reports: `REPORT-YYYY-MM-DD-title.md` (existing `UPPER_SNAKE` reports in `docs/reports/` are grandfathered)

**Tags taxonomy**:
- `type/` → concept, adr, incident, runbook, meeting, sprint, moc, report, plan, guide
- `domain/` → payments, identity, infrastructure, blockchain, testing, agents, business, integrations, security, operations
- `chain/` → base, ethereum, polygon, arbitrum, avalanche, monad, celo, optimism
- `status/` → draft, active, completed, archived, deprecated
- `priority/` → p0, p1, p2

**Vault location**: `vault/` — Obsidian knowledge graph lives here. When creating new documentation, prefer creating in the vault with proper interlinking. Update the relevant MOC in `vault/01-moc/` when adding new notes.

### Mermaid Diagrams
**All docs describing flows, state machines, or architecture MUST include Mermaid diagrams** (GitHub-flavored, triple-backtick `mermaid` blocks). Use `sequenceDiagram` for multi-actor flows, `stateDiagram-v2` for state machines, `graph LR/TD` for architecture. Reference: `docs/planning/PAYMENT_ARCHITECTURE.md`.


## Feature Parity (Web + Mobile)

**IMPORTANT**: When adding features to either the web dashboard or mobile app, update the feature parity document at `docs/planning/FEATURE_PARITY_WEB_MOBILE.md`. Both platforms should stay synchronized. See the document for the current feature matrix and planned work.

Mobile app lives in `em-mobile/` — Expo SDK 54 + React Native + NativeWind + Dynamic.xyz auth.

## Operational State (as of 2026-02-28)

**CRITICAL: ECS Image Tag Rules**
- Task definition revision **150+** uses `:latest` tag. CI/CD may create SHA-tagged revisions — always verify and fix with `deploy-mcp` skill.
- **Use the `deploy-mcp` skill** for all deployments — it handles build, ECR push, force deploy, and health verification.
- **Use the `deploy-check` skill** to verify deployment state without deploying.

**ECR deploy** (use skill or manual):
```bash
MSYS_NO_PATHCONV=1 aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com
# MCP Server
docker build --no-cache -f mcp_server/Dockerfile -t em-mcp ./mcp_server && docker tag em-mcp:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/<YOUR_ECR_MCP_REPO>:latest && docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/<YOUR_ECR_MCP_REPO>:latest
# Dashboard
docker build --no-cache -f dashboard/Dockerfile -t em-dashboard ./dashboard && docker tag em-dashboard:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/<YOUR_ECR_DASHBOARD_REPO>:latest && docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/<YOUR_ECR_DASHBOARD_REPO>:latest
# Force new deployment
MSYS_NO_PATHCONV=1 aws ecs update-service --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECR_MCP_REPO> --force-new-deployment --region us-east-2
MSYS_NO_PATHCONV=1 aws ecs update-service --cluster <YOUR_ECS_CLUSTER> --service <YOUR_ECR_DASHBOARD_REPO> --force-new-deployment --region us-east-2
```

### Secrets & Credentials

See `.env.example` files for required environment variables.

**ECS Task Definition Secrets Checklist**: When adding new features that require env vars, ALWAYS verify they are in the ECS task definition. Missing secrets cause silent 500 errors.

**Deploy scripts**: All TS scripts in `scripts/` auto-load `.env.local` (`WALLET_PRIVATE_KEY` aliased as `PRIVATE_KEY`).

**>>> CRITICAL: NEVER SHOW PRIVATE KEYS IN LOGS <<<**
To use master wallet key from your secrets manager:
```bash
# Retrieve secrets from your secrets manager and pass as env vars
```

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
| **SDK** | `uvd-x402-sdk[fastapi,wallet]>=0.21.0` (in `mcp_server/requirements.txt`) |
| **SDK Client** | `mcp_server/integrations/x402/sdk_client.py` — `EMX402SDK` class |
| **Facilitator URL** | `https://facilitator.ultravioletadao.xyz` |
| **Facilitator Endpoints** | `POST /verify`, `POST /settle`, `POST /register`, `POST /feedback` |
| **Network** | Base Mainnet (chain 8453) for production payments |
| **ERC-8004 Networks** | 16 total: 10 mainnets + 6 testnets (all via Facilitator) |

**Wallet Roles (CRITICAL — read this before touching payments)**:
- **Dev wallet** (`<YOUR_DEV_WALLET>`): Used by local scripts and tests. Key in `.env.local`.
- **Platform wallet** (`<YOUR_PLATFORM_WALLET>`): Used by ECS MCP server. Key in AWS Secrets Manager (see `.env.example`). **This is the settlement transit point** — agent funds settle here at approval, then immediately disburse to worker (87%) + treasury (13%). No funds should accumulate here long-term.
- **Treasury** (`<YOUR_TREASURY_WALLET>`): Cold wallet (Ledger). **ONLY receives 13% platform fee** on successful task completion (treasury = remainder after worker payment; absorbs x402r protocol fee automatically). **NEVER a settlement target.** If funds land here during task creation, it's a bug.
- `EM_SETTLEMENT_ADDRESS` env var (optional): Overrides the platform wallet for settlement. Defaults to address derived from `WALLET_PRIVATE_KEY`.
- `EM_REPUTATION_RELAY_KEY` env var (optional): Private key for a dedicated relay wallet used when workers rate agents. Platform wallet can't rate Agent #2106 (self-feedback revert). Relay wallet must NOT own any agent NFTs and needs ~0.001 ETH on Base for gas. If not set, worker→agent feedback falls back to Facilitator.
- **Test worker wallet** (`<YOUR_TEST_WORKER_WALLET>`): Used by Golden Flow for worker-side operations. Key in AWS Secrets Manager (see `.env.example`). Set as `EM_WORKER_PRIVATE_KEY` for worker→agent reputation in multichain Golden Flow tests.
- **Testing budget**: Always use amounts **< $0.30** for test tasks. ~$5 per chain must last through all testing cycles.

**Payment Mode** (`EM_PAYMENT_MODE`, default: `fase2`):
- **`fase2`** (default, production): Agent-signed on-chain escrow. See ADR-001 flow below.
- **`fase1`** (DEPRECATED): Server-signed EIP-3009 settlements. Only works with `EM_SERVER_SIGNING=true`.
- **`preauth`** (DEPRECATED): Auth at creation, settled at approval through platform wallet.
- **`x402r`** (DEPRECATED): Do not use — caused fund loss bug.

**>>> CRITICAL: EM NEVER SIGNS PAYMENTS IN PRODUCTION (ADR-001) <<<**
The server is a marketplace — it never touches funds. External agents sign their own
escrow operations via `X-Payment-Auth` header. `EM_SERVER_SIGNING=true` enables server-side
signing for internal testing ONLY. Not set in production ECS.

**Payment Flow for Tasks** (ADR-001 — Agent-Signed Escrow, PRODUCTION):
1. **Agent signs pre-auth** (task creation): Agent sends `X-Payment-Auth` header with EIP-3009 `ReceiveWithAuthorization` signature. Funds stay in agent's wallet.
2. **Escrow timing** (configurable via `X-Escrow-Timing` header or `EM_ESCROW_TIMING`):
   - `lock_on_assignment` (DEFAULT): Pre-auth stored in DB. Escrow locks when worker is assigned. Cancel before assignment = free (no-op).
   - `lock_on_creation`: Escrow locks immediately at task creation. Cancel always requires on-chain refund.
3. **Escrow lock** (at assignment or creation): Server relays agent's signed auth to Facilitator `/settle`. Facilitator executes on-chain lock. Worker set as receiver. If lock fails: assignment rolled back, task stays published.
4. **Release** (task approval): **1 TX only** — gasless release via facilitator. StaticFeeCalculator(1300 BPS) splits atomically: worker gets 87% (net), operator holds 13% (fee). `distributeFees()` flushes fee to treasury.
5. **Cancel**: Published + lock_on_assignment → no-op (pre-auth unused). Accepted → refund full bounty from escrow to agent.
6. **Pre-auth expiry**: `validBefore = task.deadline + 1 hour`. If no worker assigned by then, pre-auth expires silently. Zero cost.
- **Architecture doc**: `docs/planning/ADR-001-payment-architecture-v2.md`
- **Fee model**: Credit card convention — fee is 13% of gross (bounty), deducted on-chain. Agent pays $0.10, worker gets $0.087, treasury gets $0.013.
- **Trust model**: Fully trustless — EM never touches funds. Agent signs, escrow holds, worker receives directly.

**Payment Flow for Tasks** (Fase 1, DEPRECATED — testing only with `EM_SERVER_SIGNING=true`):
1. **Balance check** (task creation): `balanceOf(agent)` via RPC — advisory only, task creates regardless. No auth signed, no funds move.
2. **Direct settlement** (task approval): Server signs 2 fresh EIP-3009 auths → Facilitator settles both: agent→worker (bounty) + agent→treasury (13% fee). No platform wallet intermediary.
3. **Cancel** (task cancellation): No-op — no auth was ever signed, nothing to refund.
4. **Platform fee**: Configurable via `EM_PLATFORM_FEE` env var (default 13%). Uses 6-decimal USDC precision with $0.01 minimum fee. Treasury absorbs any x402r protocol fee automatically via `_compute_treasury_remainder()`.

**Audit Trail**: All payment events are logged to `payment_events` table (migration 027). Tracks verify, store_auth, settle, disburse_worker, disburse_fee, refund, cancel, error events with tx hashes and amounts.

**Manual Refund**: If `payment_events` shows `settle` success without `disburse_worker`, funds are stuck. Check `escrows.metadata.agent_settle_tx` and manually refund from receiving wallet to agent.

### x402r Escrow System (Fase 2 — In Progress)

**Full reference:** [`docs/planning/X402R_REFERENCE.md`](docs/planning/X402R_REFERENCE.md) — architecture, ABIs, all contract addresses, condition system, deployment guide.

**Architecture (3 layers):**
- **Layer 1:** `AuthCaptureEscrow` — shared singleton per chain, holds funds in TokenStore clones (EIP-1167)
- **Layer 2:** `PaymentOperator` — per-config contract with pluggable conditions (who can authorize/release/refund)
- **Layer 3:** `Facilitator` — off-chain server, pays gas, enforces business logic

**Fase 5 Operators deployed on 9 EVM chains** (all active in Facilitator allowlist, Golden Flow 7/8 PASS). Solana uses Fase 1 (no operator). Addresses in On-Chain Contracts table above. StaticFeeCalculator(1300 BPS = 13%) auto-splits at release: worker 87%, operator 13%. `distributeFees(USDC)` flushes to treasury. Deploy script: `scripts/deploy-payment-operator.ts`.

**Key upstream repos:**
| Repo | URL | Stack |
|------|-----|-------|
| x402r-contracts | `github.com/BackTrackCo/x402r-contracts` | Foundry (Solidity) |
| x402r-sdk | `github.com/BackTrackCo/x402r-sdk` | TypeScript monorepo (pnpm) |
| x402r docs | `github.com/BackTrackCo/docs` | Mintlify (docs.x402r.org) |

### Database State

**RPC Functions available in live DB**:
- `get_or_create_executor(wallet, name, email)` — Creates or updates executor
- `link_wallet_to_session(user_id, wallet, chain_id)` — Links wallet to auth session
- `apply_to_task(task_id, executor_id, message)` — Accept task atomically (creates application + sets executor_id)
- `expire_tasks()` — Mark overdue tasks as expired
- `create_executor_profile(...)` — Create executor profile

**Known RLS issues**:
- `submissions` INSERT policy requires `executor.user_id = auth.uid()`. If the executor isn't linked to the anonymous session, inserts fail **silently** (no error, just 0 rows). SubmissionForm.tsx now uses `submitWork()` which handles this with proper error messages.

### Known Bugs & TODOs

- [ ] `EvidenceUpload.tsx` (camera, GPS, EXIF) is unused — `SubmissionForm.tsx` is a simpler version
- [ ] Small USDC amount stuck in vault from direct relay deposit. Needs refund or contract expiry
- [ ] Incident Feb 2026: Tasks settled to treasury `<YOUR_TREASURY_WALLET>` instead of platform wallet. Pending refund to `<REFUND_TARGET>` on Base

### Golden Flow (Comprehensive E2E Acceptance Test)

The **Golden Flow** is the definitive acceptance test — if it passes, the platform is healthy. Tests full lifecycle end-to-end on production: health check → task creation (escrow lock) → worker registration → ERC-8004 identity → task application → assignment → evidence submission → approval + payment → bidirectional reputation → on-chain verification.

**Script**: `python scripts/e2e_golden_flow.py`
**Reports**: `docs/reports/GOLDEN_FLOW_REPORT.md` (EN) / `GOLDEN_FLOW_REPORT.es.md` (ES)

### x402r Protocol Fee (Automatic Handling)

BackTrack controls `ProtocolFeeConfig` (`0x59314674...`) — up to 5% hard cap, 7-day timelock. Our code reads it from chain dynamically. When enabled: agent still pays 13% total, x402r deducts their %, worker gets 100% bounty, treasury gets `13% - protocol_fee%`. Fully automatic.

### Task Factory Guidelines

- **Bounties**: **ALWAYS under $0.20** for testing (~$4 USDC per chain). E2E uses `TEST_BOUNTY = 0.10`. Deadlines: 5-15 minutes.
- **Script**: `cd scripts && npx tsx task-factory.ts --preset screenshot --bounty 0.10 --deadline 10`
- **E2E script**: `python scripts/e2e_mcp_api.py` — full lifecycle through REST API
- **Production wallet**: `<YOUR_PLATFORM_WALLET>` (funded on all 9 EVM chains + Solana wallet for SPL)

### ERC-8004 Identity

Agent ID **2106** on Base. Registration and reputation via Facilitator (`POST /register`, `POST /feedback`) — gasless. **16 EVM networks**: 10 mainnets + 6 testnets. On Solana, ERC-8004 identity via QuantuLabs 8004-solana Anchor programs (future). Network naming: `"base"`, `"polygon"`, `"solana"`, etc. (`"base-mainnet"` kept as alias).

### Production URLs

| URL | Service |
|-----|---------|
| `https://execution.market` | Dashboard (React SPA) |
| `https://api.execution.market/docs` | Swagger UI (interactive API docs) |
| `https://api.execution.market/api/v1/*` | REST API (Tasks, Workers, Admin, Escrow, Reputation, Health) |
| `https://mcp.execution.market/mcp/` | MCP Transport (Streamable HTTP) |
| `https://mcp.execution.market/.well-known/agent.json` | A2A Agent discovery |
| `https://admin.execution.market` | Admin Dashboard (S3+CloudFront, `X-Admin-Key` auth) |

### Key Integration Files

| File | Purpose |
|------|---------|
| `mcp_server/integrations/x402/sdk_client.py` | x402 SDK wrapper + multichain token registry (12 EVM + Solana, 6 stablecoins) — **USE THIS for all payments** |
| `mcp_server/integrations/x402/client.py` | Direct HTTP facilitator client (fallback) |
| `mcp_server/integrations/x402/advanced_escrow_integration.py` | Advanced escrow flows documentation |
| `mcp_server/integrations/erc8004/facilitator_client.py` | ERC-8004 identity, reputation, registration (16 networks) |
| `mcp_server/integrations/erc8004/identity.py` | Worker identity check + gasless registration |
| `mcp_server/api/routes.py` | REST API endpoints (task CRUD, submissions, escrow) |
| `mcp_server/api/reputation.py` | Reputation + registration endpoints |
| `mcp_server/server.py` | MCP tools for AI agents |
| `dashboard/src/components/TaskApplicationModal.tsx` | Task acceptance flow |
| `dashboard/src/components/SubmissionForm.tsx` | Evidence upload (uses `submitWork()` service) |
| `dashboard/src/hooks/useProfileUpdate.ts` | Profile update with executor ID resolution |
| `dashboard/src/context/AuthContext.tsx` | Auth state with wallet-based executor lookup |
| `mcp_server/integrations/worldid/client.py` | World ID 4.0 RP signing (secp256k1 + EIP-191) + Cloud API v4 verify |
| `mcp_server/api/routers/worldid.py` | World ID endpoints (GET /rp-signature, POST /verify) |
| `dashboard/src/components/WorldIdVerification.tsx` | IDKit v4 widget + WorldIdBadge component |
| `ows-mcp-server/src/server.ts` | OWS MCP Server — 9 wallet tools, ERC-8004 identity, EIP-3009 USDC signing |
