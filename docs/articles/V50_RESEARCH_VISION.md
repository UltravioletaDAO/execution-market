# V50 Manifesto Research Brief: Execution Market

> Research compiled from SPEC.md, PLAN.md, agent-card.json, landing page, published articles, and CLAUDE.md operational data.
> Date: 2026-02-18

---

## 1. Core Thesis

Execution Market is the **Universal Execution Layer** -- the missing bridge between digital intelligence and physical reality. While the agent economy protocol stack (MCP for tools, A2A for agent communication, ERC-8004 for identity, x402 for payments) is complete for digital-to-digital interactions, **90% of economic value still requires human senses, judgment, or hands**. Execution Market is the digital-to-physical layer: permissionless, instant, gasless, with cryptographic proof of completion. Every entity -- human, AI agent, robot, IoT device -- can both request and execute work, paid in stablecoins, with portable on-chain reputation.

---

## 2. Key Differentiators

- **Not a gig platform -- a protocol.** No accounts required. No 30% take rate. Permissionless participation. 13% transparent fee, on-chain.
- **Gasless payments via x402 + EIP-3009.** Worker pays $0.00 gas. Agent pays $0.00 gas. Facilitator relays meta-transactions. Zero barrier to entry for workers in Lagos, Bogota, or Manila.
- **On-chain reputation via ERC-8004.** Portable, bidirectional (Human<->Agent, Agent<->Agent), survives platform shutdown. Four-quadrant reputation seals.
- **MCP-native.** 24+ MCP tools mean any Claude, GPT, or custom agent can discover and use Execution Market as a tool. Not an API integration -- a first-class agent capability.
- **Trustless escrow evolution.** Five phases of escrow architecture, from direct meta-transaction settlements (Fase 1) to fully trustless on-chain fee splits with PaymentOperator (Fase 5). No platform wallet custody at any point.
- **Micro-task economics.** $0.25 minimum task. On-chain gasless settlements make sub-dollar tasks profitable for all parties. This unlocks task categories that never existed.
- **Universal Execution Layer vision.** Not just humans executing for agents -- eventually robots, IoT devices, autonomous physical agents. The same protocol, same reputation, same payments. TODOS ejecutan para TODOS.
- **Walkaway test passed.** If the Facilitator disappears, deploy your own. EIP-3009 authorizations are valid regardless of who submits them. If Execution Market shuts down, your reputation persists on-chain.
- **Geographic arbitrage.** $0.50 is nothing in SF. $0.50 is $2,000 COP in Colombia. Agents don't distinguish geographies -- this creates a global micro-task economy accessible to anyone with a phone.

---

## 3. Milestones Achieved (with dates and evidence)

| Date | Milestone | Evidence |
|------|-----------|----------|
| Jan 2026 | Database schema, React dashboard, MCP server with 6 tools | PLAN.md Section 12 |
| Feb 7, 2026 | E2E test framework with auth escape hatch (Dynamic.xyz workaround) | `e2e/fixtures/auth.ts` |
| **Feb 10, 2026** | **First Agent-to-Human Payment on Base Mainnet** -- $0.06 ($0.05 worker + $0.01 fee), gasless, 3 min 13 sec | `docs/articles/FIRST_AGENT_TO_HUMAN_PAYMENT.md`, Base Etherscan TX hashes |
| Feb 11, 2026 | ERC-8004 integration: 6 workstreams, 122 new tests, 5 feature flags, scoring engine, side effects outbox, 5 MCP reputation tools | Migration 028, `mcp_server/reputation/` |
| Feb 11, 2026 | Fase 1 E2E tested on mainnet with real USDC | `docs/planning/FASE1_E2E_EVIDENCE_2026-02-11.md` |
| Feb 13, 2026 | Agent #2106 ownership transfer to platform wallet (from Facilitator) | TX `0xcf3bd6c3...` on Base |
| Feb 13, 2026 | Golden Flow: 7/7 PASS -- full lifecycle including bidirectional reputation | `docs/reports/GOLDEN_FLOW_REPORT.md` |
| Feb 13, 2026 | Trustless Direct Release (EM_ESCROW_MODE=direct_release) -- escrow pays worker directly, platform never touches funds | 16 new tests |
| Feb 13, 2026 | Batch fee collection: admin sweep endpoint, safety buffer, min sweep | 86 tests in test_payment_dispatcher.py + test_admin_fees.py |
| **Feb 14, 2026** | **Fase 5 Operator deployed on Base** -- `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` -- StaticFeeCalculator(1300 BPS = 13%), trustless on-chain fee split | BaseScan verified contract |
| Feb 14, 2026 | Ali (x402r/BackTrack) validates fee math and architecture | `docs/reports/ALI_VALIDATION_NOTES.md` |
| Feb 18, 2026 | Security audit: 5 P0 bugs, 11 P1 issues identified and remediation plan created | `docs/reports/AUDIT_*_2026-02-18.md` (4 reports) |
| Feb 18, 2026 | Test suite: **1,027+ tests** (950 original + 77 new H2A/agent executor tests) | `mcp_server/tests/` |
| Feb 18, 2026 | Master Plan: 36 tasks across 4 phases for H2A/A2A hardening | `docs/planning/MASTER_PLAN_H2A_A2A_HARDENING.md` |

---

## 4. Tech Stack Highlights

| Layer | Technology | Why |
|-------|-----------|-----|
| **Backend** | Python 3.10+ / FastMCP / Pydantic v2 / FastAPI | Async, typed, MCP-native agent integration |
| **Database** | Supabase (PostgreSQL) with RLS, PostGIS, realtime | Managed, realtime subscriptions, geospatial queries |
| **Dashboard** | React 18 + TypeScript + Vite + Tailwind CSS | Worker-facing SPA at `execution.market` |
| **Payments** | x402 SDK (`uvd-x402-sdk`) + Ultravioleta Facilitator | Gasless EIP-3009 meta-transactions, stablecoin-native |
| **Escrow** | x402r AuthCaptureEscrow + PaymentOperator (Fase 5) | On-chain trustless escrow with pluggable fee calculator |
| **Identity** | ERC-8004 Registry (CREATE2 on 15 networks) | Agent #2106 on Base, gasless registration for workers |
| **Reputation** | ERC-8004 Reputation Registry (on-chain, bidirectional) | 4-dimension scoring, portable, platform-agnostic |
| **Evidence** | S3 + CloudFront CDN (presigned uploads) | Tamper-evident, geo-tagged, timestamped |
| **Agent Protocol** | MCP (Streamable HTTP) + A2A (JSON-RPC) + WebSocket | Triple transport: MCP for tools, A2A for discovery, WS for realtime |
| **Infrastructure** | AWS ECS Fargate, ECR, ALB, Route53 | Production on `execution.market`, `api.execution.market`, `mcp.execution.market` |
| **CI/CD** | GitHub Actions auto-deploy on push to main | Full pipeline: ruff + mypy + pytest + tsc + eslint |

---

## 5. Vision: Universal Execution Layer

### Phase 1: Humans Execute for Agents (NOW -- LIVE)
AI agents publish bounties. Human workers execute physical tasks. Payment via x402. The original product.

### Phase 2: Humans Hire Agents (H2A -- IN PROGRESS)
The other side of the market. Humans post digital tasks (research, analysis, code, content). AI agents compete to execute them. Same escrow, same reputation, reversed roles. Landing page already advertises this: "HIRE AI AGENTS."

### Phase 3: Agents Delegate to Agents (A2A -- DESIGNED)
Agent-to-agent task marketplace. A trading bot hires an NLP agent for sentiment analysis. A content agent hires an image generation agent. Autonomous economic coordination. Same ERC-8004 reputation.

### Phase 4: Robots and IoT (FUTURE)
Physical robots, delivery drones, IoT devices as executors. Same protocol, same identity (ERC-8004 supports `type: robot`), same payments. A logistics agent hires a delivery robot. A maintenance AI hires an inspection drone.

### Phase 5: Universal Execution (VISION)
**TODOS ejecutan para TODOS.** Human, robot, AI agent -- any entity can be both requester and executor. The same ERC-8004 identity, the same x402 payments, the same on-chain reputation. Execution becomes a universal, composable primitive.

The SPEC.md explicitly defines executor types:
- **Humans**: judgment, creativity, physical presence, social communication
- **Robots**: precision, endurance, 24/7 operation, sensor data collection
- **AI Agents**: processing speed, scale, availability, consistency

IRC x402-flow is the envisioned backbone for the Universal Execution Layer -- a 35-year battle-tested protocol (RFC 1459) where bots are first-class citizens, extended with x402 payment commands and task protocol layers.

---

## 6. Integration Points

### MCP (Model Context Protocol)
- **24+ MCP tools** for AI agents: `em_publish_task`, `em_get_tasks`, `em_approve_submission`, `em_cancel_task`, `em_check_escrow_state`, reputation tools, etc.
- MCP transport: Streamable HTTP at `https://mcp.execution.market/mcp/`
- Any agent framework (Claude, GPT, custom) can discover and use EM as a tool
- MCP annotations: `readOnlyHint`, `destructiveHint` for safe agent interaction

### A2A (Agent-to-Agent Protocol)
- A2A discovery card: `https://mcp.execution.market/.well-known/agent.json`
- JSON-RPC message types: `task/publish`, `task/status`, `task/verify`, `task/cancel`, `tasks/list`, `discovery/capabilities`
- MeshRelay integration for agent-to-agent communication
- H2A endpoint at `/api/v1/h2a/` for humans hiring agents

### ERC-8004 (Agent Identity)
- **Agent #2106** on Base Mainnet (production)
- Legacy Agent #469 on Sepolia
- Identity Registry: `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (all mainnets via CREATE2)
- Reputation Registry: `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` (all mainnets)
- **15 networks**: 9 mainnets (ethereum, base, polygon, arbitrum, celo, bsc, monad, avalanche, optimism) + 6 testnets
- Gasless registration for workers via Facilitator (`POST /register`)
- 4-dimension reputation scoring engine: task completion, quality, timeliness, dispute rate
- Bidirectional reputation: workers rate agents, agents rate workers, all on-chain

### x402 (Payment Protocol)
- **Ultravioleta Facilitator**: `facilitator.ultravioletadao.xyz` (OURS -- we deploy, control, maintain)
- Gasless EIP-3009 `transferWithAuthorization` meta-transactions
- USDC on Base (primary), support for 5 stablecoins across 15 EVM networks
- Escrow via x402r: AuthCaptureEscrow + PaymentOperator + FeeCalculator
- **Active Fase 5 Operator**: `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` on Base
- StaticFeeCalculator: 1300 BPS (13%) with atomic on-chain fee split

### ERC-8128 (HTTP Authentication)
- Signed HTTP Requests with Ethereum wallets
- No API keys, no passwords -- agents sign requests with their wallet
- Verification on-chain via ERC-1271/ERC-191
- Built on RFC 9421
- One key for auth, identity, reputation, and payments
- Featured on landing page with SDK quick start

---

## 7. On-Chain Evidence

### Contract Addresses (Production)

| Contract | Network | Address |
|----------|---------|---------|
| ERC-8004 Identity Registry | All Mainnets | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` |
| ERC-8004 Reputation Registry | All Mainnets | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |
| x402r Escrow (AuthCaptureEscrow) | Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| x402r Escrow (AuthCaptureEscrow) | Ethereum | `0xc1256Bb30bd0cdDa07D8C8Cf67a59105f2EA1b98` |
| x402r Escrow (AuthCaptureEscrow) | Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| x402r Escrow (AuthCaptureEscrow) | Arbitrum, Avalanche, Celo, Monad, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |
| **EM PaymentOperator (Fase 5)** | **Base** | **`0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`** |
| StaticFeeCalculator (1300 BPS) | Base | `0xd643DB63028Cd1852AAFe62A0E3d2A5238d7465A` |
| OrCondition (Payer OR Facilitator) | Base | `0xb365717C35004089996F72939b0C5b32Fa2ef8aE` |
| Facilitator EOA | All | `0x103040545AC5031A11E8C03dd11324C7333a13C7` |

### Key Transaction Hashes

| Event | TX / Evidence |
|-------|---------------|
| First Agent-to-Human Payment (Feb 10, 2026) | Two EIP-3009 meta-txs on Base -- $0.05 worker + $0.01 fee |
| Agent #2106 Ownership Transfer | `0xcf3bd6c3964fef1963795b2c6f688d6e8b117b18e0616e7e81cddab0e0ed1ae3` |
| Golden Flow E2E (7/7 PASS) | Documented in `docs/reports/GOLDEN_FLOW_REPORT.md` |

### BaseScan Verification Links
- Fase 5 PaymentOperator: `https://basescan.org/address/0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb`
- ERC-8004 Identity Registry: `https://basescan.org/address/0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`
- ERC-8004 Reputation Registry: `https://basescan.org/address/0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`
- Facilitator EOA: `https://basescan.org/address/0x103040545AC5031A11E8C03dd11324C7333a13C7`

---

## 8. Open Source Narrative

### What Exists
- **Full MCP server** with 24+ tools, 63+ REST API endpoints, WebSocket realtime notifications
- **React dashboard** for worker task discovery, evidence submission, reputation tracking
- **Python + TypeScript SDKs** (`uvd-x402-sdk`) with aligned APIs
- **35 database migrations** covering tasks, executors, submissions, disputes, reputation, escrow, payment events, platform config, ERC-8004 side effects, gas dust tracking
- **Landing page** with matrix rain aesthetic, typing effect, H2A + A2A sections, ERC-8128 explainer, FAQ
- **Production infrastructure** on AWS ECS Fargate with CI/CD via GitHub Actions

### What the 1,027+ Tests Prove
- **276 core tests**: Routes, MCP tools, auth, reputation, workers, platform config, architecture
- **251 payment tests**: PaymentDispatcher, escrow modes (platform_release, direct_release), fee calculations, multichain, protocol fee handling
- **177 ERC-8004 tests**: Scoring engine, side effects outbox, auto-registration, rejection flows, reputation tools, ERC-8128 auth
- **61 security tests**: Fraud detection, GPS anti-spoofing
- **77 infrastructure tests**: Webhooks, WebSocket, A2A bridge, timestamp handling
- **77 new tests** (post-audit): H2A endpoint hardening (31), agent executor validation (46)
- **31 migration tests**: Schema validation for migrations 031-033
- **E2E Playwright tests**: Auth escape hatch, task lifecycle, evidence submission

The test suite demonstrates production-grade reliability across the entire stack: payments, identity, reputation, security, and infrastructure. The 5 P0 bugs and 11 P1 issues identified in the Feb 18 audit are being systematically addressed through a 36-task, 4-phase hardening plan.

### The Recursion
The payment refactor that made Fase 1 possible was designed, implemented, and shipped by **five AI agents coordinating in real-time over IRC**. 91 files changed. ~12,000 lines added. Tested with real money. Same day. AI agents built the system that lets AI agents hire humans.

---

## 9. Task Categories

Five categories of physical-world tasks that agents cannot execute digitally:

| Category | Key | Examples | Bounty Range |
|----------|-----|----------|-------------|
| **Physical Presence** | `physical_presence` | Verify store is open, take photos of location, count people in queue | $1-25 |
| **Knowledge Access** | `knowledge_access` | Scan book pages, photograph documents, transcribe physical text | $2-20 |
| **Human Authority** | `human_authority` | Notarize documents, certified translations, property inspection | $30-300 |
| **Simple Action** | `simple_action` | Buy specific item, deliver package, measure dimensions | $2-30 |
| **Digital-Physical Bridge** | `digital_physical` | Print and deliver, configure IoT device, digitize collection | $5-100 |

Each category has structured evidence schemas (required photos, GPS proofs, timestamps, documents), edge case handling (weather delays, access denied, item unavailable), and location-based pricing multipliers (0.5x LATAM to 1.5x US/EU).

---

## 10. Competitive Landscape Quote

> "rentahuman.ai launched with a simple premise: let people rent other people for tasks. Result: 3.6M visits, 260K signups. They proved massive demand for human-execution-as-a-service. But they built zero infrastructure. 260,057 profiles, 1 rating. No escrow. No verification. No agent API. No reputation system. They proved the market exists. We built the infrastructure to serve it."

---

## 11. Key Quotes for Manifesto

From SPEC.md:
> "Los agentes no necesitan poder legal, necesitan acceso programable a autoridad humana."

From landing page:
> "Los agentes pueden PENSAR. Pero no pueden ESTAR AHI. Tu si. Y te van a pagar por eso."

From SPEC.md:
> "TODOS ejecutan para TODOS. TODOS pagan via x402. TODOS tienen reputacion ERC-8004."

From the first payment article:
> "AI agents built the system that lets AI agents hire humans. The recursion is the point."

From the "8 Billion Employees" article:
> "In the agent economy, the hardest problem isn't computation. It's truth about the physical world."

---

*Research brief prepared for v50-manifesto article. All contract addresses, TX hashes, and test counts are verified against production codebase as of 2026-02-18.*
