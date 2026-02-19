# MASTER PLAN: Karma Kadabra V2 Launch
# Swarm de Agentes OpenClaw Transaccionando en Execution Market

> **Status**: Planning (2026-02-19)
> **Author**: Claude Code (Opus 4.6) + 0xultravioleta
> **Priority**: P0 — First real clients for Execution Market
> **Budget**: $200-500 USD initial seeding
> **Goal**: 34-55 OpenClaw agents with funded wallets transacting across 8 EVM chains

---

## Executive Summary

Karma Kadabra V2 brings the Ultravioleta DAO community to life as autonomous AI agents. Each community member (extracted from Twitch chat logs) gets their own OpenClaw agent with:
- A **soul** (SOUL.md) generated from their chat history
- A **funded wallet** with USDC across 8 EVM chains
- Access to **Execution Market** tools for buying/selling data and services
- **Cross-chain liquidity** via deBridge/Squid Router/NEAR Intents
- Communication via **MeshRelay IRC** with x402 payment-gated channels

The agents commerce autonomously — buying data, selling skills, creating alpha channels, and transacting through Execution Market. The community "earns money just by existing."

---

## Data Sources

### Twitch Chat Logs (Golden Source)
- **Location**: `Z:\ultravioleta\dao\karmacadabra\agents\karma-hello\logs\`
- **Format**: `[MM/DD/YYYY HH:MM:SS AM/PM] username: message`
- **Available dates**: 20251014, 20251015, 20251016, 20251017, 20251020, 20251021
- **Per-date files**: `full.txt` (all messages) + `{username}.txt` (per user)
- **Unique users** (estimated from file names): 80+ across all dates
- **Karma Hello**: Running live, collecting logs in real-time
- **Action needed**: Snapshot today's logs + aggregate all historical data

### Agent Profiles (From KK v1)
- **Location**: `Z:\ultravioleta\dao\karmacadabra\agents\marketplace\demo\profiles\`
- **Format**: JSON with username, skills, personality, interests, engagement_level
- **Count**: 48 user profiles + 5 system agents

### Existing Infrastructure (Execution Market)
- **8 EVM chains**: Base, Ethereum, Polygon, Arbitrum, Avalanche, Monad, Celo, Optimism
- **USDC addresses**: All in `mcp_server/integrations/x402/sdk_client.py` NETWORK_CONFIG
- **Facilitator**: `facilitator.ultravioletadao.xyz` (shared, live)
- **API**: `api.execution.market` (live, no API key required)
- **MCP**: `mcp.execution.market/mcp/` (live)
- **Payment operators**: Fase 5 on 7 chains (trustless fee split)

---

## Phase Overview

| Phase | Name | Duration | Deliverable |
|-------|------|----------|-------------|
| **Phase 1** | Fund Distribution Infrastructure | 3-4 days | Multi-chain batch funding script |
| **Phase 2** | Log Analytics & Soul Extraction | 3-4 days | Top-N user stats + SOUL.md generation pipeline |
| **Phase 3** | OpenClaw Swarm Setup | 4-5 days | 34-55 agents configured with souls + EM tools |
| **Phase 4** | Cross-Chain Liquidity | 3-4 days | deBridge/Squid/NEAR Intents integration |
| **Phase 5** | Agent Economy Bootstrap | 3-4 days | Agents transacting on EM + IRC commerce |
| **Phase 6** | Production Launch | 2-3 days | Full swarm live on Cherry Servers |

**Total estimated**: 18-24 days (phases can overlap)

---

## Phase 1: Fund Distribution Infrastructure (P0)

> **Goal**: Script that distributes USDC + gas tokens from one funded wallet to N agent wallets across 8 chains.

### Task 1.1: HD Wallet Generation Script
- **File**: `scripts/kk/generate-wallets.ts` (NEW)
- **Description**: Generate 55 deterministic wallets from a single BIP-44 seed phrase. Each wallet = one agent. Save wallet addresses (NOT keys) to a JSON manifest.
- **Fix**: Use `ethers.HDNodeWallet.fromMnemonic()` with derivation path `m/44'/60'/0'/0/{index}`. Index 0-4 = system agents, 5-54 = user agents.
- **Validation**: Script outputs `wallets.json` with 55 entries, each verifiable on-chain.
- **Security**: Seed phrase goes to AWS Secrets Manager `kk/swarm-seed`. Never stored on disk.

### Task 1.2: Same-Chain Batch Distribution Script
- **File**: `scripts/kk/distribute-funds.ts` (NEW)
- **Description**: Distribute USDC from a funded wallet to N recipient wallets on the SAME chain. Uses ERC-20 `transfer()` in sequence with nonce management.
- **Fix**: For each chain where we have USDC:
  1. Read `wallets.json` for recipient list
  2. Check source wallet balance
  3. Calculate per-wallet amount (configurable)
  4. Execute batch transfers with nonce tracking
  5. Verify all transfers completed
- **Config**: JSON file specifying per-chain amounts: `{ "base": { "usdc": "5.00", "gas_eth": "0.001" }, "polygon": { "usdc": "3.00", "gas_matic": "0.01" } }`
- **Validation**: All 55 wallets show correct USDC balance on target chain.

### Task 1.3: Native Gas Token Distribution
- **File**: Same as 1.2 (integrated)
- **Description**: Send small amounts of native gas tokens (ETH, MATIC, AVAX, CELO, MON) to each agent wallet for on-chain operations. ~$0.01-0.05 per wallet per chain.
- **Fix**: Native transfers via `wallet.sendTransaction({ to, value })`. Stagger with 100ms delays to avoid nonce collisions.
- **Validation**: Each wallet has enough gas for ~10-20 transactions.

### Task 1.4: Cross-Chain Bridge Integration (deBridge)
- **File**: `scripts/kk/bridge-funds.ts` (NEW)
- **Description**: When source funds are on one chain (e.g., USDC on Avalanche) but need to reach wallets on another chain (e.g., Base), use deBridge DLN API to bridge.
- **Fix**:
  1. deBridge DLN API: `POST https://api.dln.trade/v1.0/dln/order/create-tx`
  2. Parameters: srcChainId, srcChainTokenIn, dstChainId, dstChainTokenOut, srcChainTokenInAmount, dstChainTokenOutRecipient
  3. No SDK needed — pure REST API with tx data response
  4. Execute returned tx data with source wallet
- **Validation**: USDC arrives on destination chain within 1-5 minutes.

### Task 1.5: Cross-Chain Bridge Integration (Squid Router)
- **File**: `scripts/kk/bridge-squid.ts` (NEW, alternative to 1.4)
- **Description**: Alternative bridge using Squid Router (Axelar-powered).
- **Fix**:
  1. npm package: `@0xsquid/sdk`
  2. `squid.getRoute({ fromChain, toChain, fromToken, toToken, fromAmount, toAddress })`
  3. Execute route with signer
- **Validation**: Same as 1.4, compare fees/speed with deBridge.

### Task 1.6: Fund Distribution CLI
- **File**: `scripts/kk/fund-agents.ts` (NEW, orchestrator)
- **Description**: Main CLI that orchestrates the entire funding flow.
- **Fix**:
  ```
  Usage: npx tsx fund-agents.ts [options]
    --seed-secret <aws-secret>   AWS SM secret for HD seed
    --config <path>              Funding config JSON
    --chain <name>               Target chain (or "all")
    --top <N>                    Fund only top N agents (Fibonacci: 34, 55)
    --bridge <provider>          Bridge provider: debridge | squid | direct
    --dry-run                    Preview without executing
    --verify                     Check all balances after funding
  ```
- **Validation**: `--verify` flag confirms all wallets funded correctly.

### Task 1.7: Balance Checker
- **File**: `scripts/kk/check-balances.ts` (NEW)
- **Description**: Matrix view of all agent wallets across all chains. Shows USDC balance + native gas balance per wallet per chain.
- **Fix**: Parallel RPC calls to all 8 chains for all 55 wallets. Output as table or JSON.
- **Validation**: Human-readable matrix matches expected funding.

---

## Phase 2: Log Analytics & Soul Extraction (P0)

> **Goal**: Extract top N users from Twitch logs, generate statistics, and create SOUL.md files for each agent.

### Task 2.1: Log Aggregator & Snapshot
- **File**: `scripts/kk/aggregate-logs.py` (NEW)
- **Description**: Read all Twitch logs from Karma Hello's directory, aggregate across all dates, and produce a unified dataset.
- **Fix**:
  1. Parse all `full.txt` files from `karmacadabra/agents/karma-hello/logs/*/full.txt`
  2. Parse format: `[MM/DD/YYYY HH:MM:SS AM/PM] username: message`
  3. Deduplicate messages (same timestamp + user + content)
  4. Output: `kk_logs_aggregated.json` with all messages indexed by user
- **Validation**: Total message count matches sum of all full.txt line counts.

### Task 2.2: User Statistics & Ranking
- **File**: `scripts/kk/user-stats.py` (NEW)
- **Description**: Analyze aggregated logs and produce ranked user statistics.
- **Fix**:
  Stats per user:
  - `total_messages`: Count of messages across all dates
  - `active_dates`: Number of unique dates they appeared
  - `avg_message_length`: Average character count
  - `peak_hours`: Most active hours (timezone-adjusted)
  - `vocabulary_richness`: Unique words / total words ratio
  - `topics_mentioned`: Keywords extracted (crypto, DeFi, NFT, coding, etc.)
  - `engagement_score`: Weighted composite (messages * 0.4 + dates * 0.3 + length * 0.3)
  - `interaction_score`: How often they reply to others / get replies

  Output: Ranked list, configurable top-N (Fibonacci: 34, 55, 89)
  ```
  Usage: python user-stats.py --top 34 --output stats.json
  ```
- **Validation**: Stats match manual spot-check of 3 users.

### Task 2.3: Skill Extractor Pipeline
- **File**: `scripts/kk/extract-skills.py` (NEW)
- **Description**: Analyze each user's messages to extract skills, expertise areas, and interests using LLM.
- **Fix**:
  1. For each top-N user, collect all their messages
  2. Send to Claude Haiku with structured extraction prompt:
     - Technical skills (programming languages, tools, platforms)
     - Domain knowledge (DeFi, NFTs, trading, development, design)
     - Communication skills (teaching, explaining, humor, leadership)
     - Language proficiency (Spanish primary, English secondary, etc.)
  3. Output: `{username}_skills.json` per user
- **Validation**: Spot-check 5 users' extracted skills against their actual messages.

### Task 2.4: Voice Extractor Pipeline
- **File**: `scripts/kk/extract-voice.py` (NEW)
- **Description**: Analyze communication patterns to build personality profiles.
- **Fix**:
  1. For each top-N user, analyze all messages for:
     - Tone (casual, formal, technical, humorous)
     - Signature phrases (repeated expressions)
     - Sentiment distribution (positive, neutral, negative)
     - Engagement patterns (questions, answers, reactions)
     - Social dynamics (who they interact with most)
     - Risk tolerance (mentions of trading, betting, investing)
  2. Output: `{username}_voice.json` per user
- **Validation**: Voice profile reads as recognizable to someone who knows the user.

### Task 2.5: SOUL.md Generator
- **File**: `scripts/kk/generate-soul.py` (NEW)
- **Description**: Combine skills + voice + stats to generate the SOUL.md file that defines each OpenClaw agent's personality.
- **Fix**:
  1. Load `{username}_skills.json` + `{username}_voice.json` + stats
  2. Generate SOUL.md using template:
     ```markdown
     # Soul of {username}

     ## Identity
     You are {username}'s digital twin in the Ultravioleta DAO.

     ## Personality
     - Tone: {extracted tone}
     - Signature phrases: "{phrase1}", "{phrase2}"
     - Language: {primary} / {secondary}

     ## Skills & Expertise
     - {skill1} (confidence: {high/medium/low})
     - {skill2} ...

     ## Economic Behavior
     - Risk tolerance: {conservative/moderate/aggressive}
     - Preferred task types: {categories}
     - Max spend per transaction: ${amount}
     - Negotiation style: {firm/flexible/generous}

     ## Monetizable Capabilities
     - {capability1}: Can be sold as {service_description}
     - {capability2}: ...
     ```
  3. Output: 55 SOUL.md files in `kk_swarm/souls/`
- **Validation**: Each SOUL.md is unique, reflects the actual user's chat behavior.

### Task 2.6: Log Sales API for Karma Hello
- **File**: `scripts/kk/karma-hello-api.py` (NEW)
- **Description**: Design the x402 payment-gated endpoint where Karma Hello sells logs to other agents.
- **Fix**:
  1. FastAPI endpoint: `POST /api/v1/logs/{username}`
  2. x402 payment required: 0.01-0.10 USDC per log request
  3. Response: User's chat messages for specified date range
  4. Integrated with our Facilitator for gasless settlement
  5. Karma Hello = OpenClaw agent with this API as a skill
- **Validation**: Agent can buy logs via x402, receives data, payment settles on-chain.

---

## Phase 3: OpenClaw Swarm Setup (P0)

> **Goal**: Configure 34-55 OpenClaw agents with souls, wallets, and Execution Market tools.

### Task 3.1: OpenClaw Installation & Config
- **File**: `infrastructure/cherry/provision.sh` (NEW)
- **Description**: Bootstrap script for installing OpenClaw on Cherry Servers VPS.
- **Fix**:
  1. Install Node.js 22 + pnpm
  2. Install OpenClaw globally: `npm i -g @openclaw/core` (or latest package name)
  3. Configure Docker for sandboxed tool execution
  4. Set up systemd service for auto-restart
- **Validation**: `openclaw --version` returns valid version, Gateway starts on port 18789.

### Task 3.2: Agent Workspace Generator
- **File**: `scripts/kk/generate-workspaces.py` (NEW)
- **Description**: Auto-generate OpenClaw workspace directory for each agent from SOUL.md + wallet + skills.
- **Fix**:
  Per agent, create:
  ```
  workspaces/kk-{username}/
  ├── AGENTS.md          # Core instructions (shared template + agent-specific)
  ├── SOUL.md            # From Phase 2, Task 2.5
  ├── skills/
  │   ├── em-publish-task/SKILL.md    # Publish bounty on EM
  │   ├── em-check-status/SKILL.md    # Poll submission status
  │   ├── em-approve-work/SKILL.md    # Approve + pay
  │   ├── buy-data/SKILL.md           # Negotiate & purchase
  │   └── sell-data/SKILL.md          # List & sell own data
  └── data/
      ├── wallet.json     # Wallet address (NOT private key)
      └── profile.json    # KK v1 profile data
  ```
- **Validation**: 55 workspace directories created, each with valid AGENTS.md + SOUL.md.

### Task 3.3: AGENTS.md Template
- **File**: `scripts/kk/templates/AGENTS.md.template` (NEW)
- **Description**: The shared instruction template all agents receive, with per-agent variables.
- **Fix**: Template from KARMACADABRA_V2_ARCHITECTURE.md section 4.3, updated for:
  - Execution Market API URL: `https://api.execution.market/api/v1`
  - Payment: USDC via x402 across 8 EVMs (gasless)
  - ERC-8004 identity registration
  - Budget limits (configurable per agent)
  - MeshRelay IRC communication
  - Rating requirements (bidirectional)
- **Validation**: Template renders correctly for 3 sample agents.

### Task 3.4: Execution Market MCP Skills
- **File**: `scripts/kk/skills/em-*/SKILL.md` (NEW, 5 skill files)
- **Description**: OpenClaw skills that wrap EM's MCP tools and REST API.
- **Fix**: 5 skills:
  1. `em-publish-task`: POST /api/v1/tasks — publish bounty with configurable params
  2. `em-check-status`: GET /api/v1/tasks/{id} — check task status + submissions
  3. `em-approve-work`: POST /api/v1/submissions/{id}/approve — approve + trigger payment
  4. `em-browse-tasks`: GET /api/v1/tasks/available — browse tasks from other agents
  5. `em-apply-task`: POST /api/v1/tasks/{id}/apply — apply to do another agent's task
- **Validation**: Each skill can be tested independently via OpenClaw CLI.

### Task 3.5: OpenClaw Multi-Agent Config (openclaw.json)
- **File**: `infrastructure/cherry/openclaw.json.template` (NEW)
- **Description**: The main config file mapping all agents to their workspaces.
- **Fix**: Generate from wallet manifest + workspace list:
  ```json
  {
    "gateway": { "host": "0.0.0.0", "port": 18789 },
    "agents": {
      "mapping": {
        "dm:system:karma-hello": { "workspace": "~/.openclaw/workspaces/kk-karma-hello", "model": "anthropic/claude-haiku-4-5" },
        "dm:system:skill-extractor": { "workspace": "~/.openclaw/workspaces/kk-skill-extractor", "model": "anthropic/claude-haiku-4-5" },
        "dm:agent:{username}": { "workspace": "~/.openclaw/workspaces/kk-{username}", "model": "anthropic/claude-haiku-4-5" }
      }
    },
    "tools": {
      "mcp": {
        "execution-market": { "type": "http", "url": "https://mcp.execution.market/mcp/" }
      }
    }
  }
  ```
- **Validation**: OpenClaw Gateway starts with all agents visible in sessions_list.

### Task 3.6: ERC-8004 Agent Registration Script
- **File**: `scripts/kk/register-agents-erc8004.ts` (NEW)
- **Description**: Register all 55 agents on ERC-8004 Identity Registry (Base mainnet, gasless via Facilitator).
- **Fix**:
  1. For each agent wallet, call Facilitator: `POST /register`
  2. Agent domain: `{username}.kk.ultravioletadao.xyz`
  3. Store returned agent_id in manifest
  4. Batch: stagger with 2s delays to avoid rate limiting
- **Validation**: Each agent has an on-chain ERC-8004 identity, resolvable by address.

---

## Phase 4: Cross-Chain Liquidity (P1)

> **Goal**: Enable agents to transact across any chain without manual bridging.

### Task 4.1: deBridge DLN Integration
- **File**: `scripts/kk/lib/debridge-client.ts` (NEW)
- **Description**: TypeScript client for deBridge DLN cross-chain transfers.
- **Fix**:
  1. deBridge DLN API (no SDK needed): `https://api.dln.trade/v1.0/`
  2. Endpoints:
     - `GET /dln/order/quote` — Get bridge quote
     - `POST /dln/order/create-tx` — Get TX data for bridge
     - `GET /dln/order/{orderId}/status` — Track bridge status
  3. Supported chains: All 8 (Base=8453, Ethereum=1, Polygon=137, Arbitrum=42161, Avalanche=43114, Celo=42220, Optimism=10). Check Monad support.
  4. USDC→USDC bridges, minimal slippage
- **Validation**: Bridge $1 USDC from Base to Polygon, confirm arrival.

### Task 4.2: Squid Router Integration
- **File**: `scripts/kk/lib/squid-client.ts` (NEW)
- **Description**: TypeScript client using Squid Router SDK for cross-chain swaps.
- **Fix**:
  1. npm: `@0xsquid/sdk` or `@0xsquid/squid-types`
  2. Initialize: `new Squid({ baseUrl: "https://apiplus.squidrouter.com", integratorId: "ultravioleta-kk" })`
  3. Get route: `squid.getRoute({ fromChain, toChain, fromToken, toToken, fromAmount, toAddress })`
  4. Execute: `squid.executeRoute({ signer, route })`
  5. Requires API key from Squid dashboard
- **Validation**: Same bridge test as 4.1, compare fees.

### Task 4.3: NEAR Intents Research & Prototype
- **File**: `scripts/kk/lib/near-intents-client.ts` (NEW)
- **Description**: Research and prototype NEAR Intents for cross-chain liquidity.
- **Fix**:
  1. NEAR Intents (via Defuse protocol): Intent-based cross-chain exchange
  2. Architecture: User creates intent → Solvers compete → Best solver executes
  3. Potential for lowest fees (competitive solver market)
  4. Integration complexity: Higher than deBridge/Squid (needs NEAR account + intent signing)
  5. **Status check**: Verify production readiness as of Feb 2026
  6. If not ready: Document as Phase 6+ future integration
- **Validation**: Successfully create and resolve a cross-chain intent, or document blockers.

### Task 4.4: Bridge Router (Orchestrator)
- **File**: `scripts/kk/lib/bridge-router.ts` (NEW)
- **Description**: Smart router that picks the best bridge for each transfer based on fees, speed, and availability.
- **Fix**:
  1. Query deBridge + Squid (+ NEAR if available) for quotes
  2. Compare: total fee, estimated time, reliability
  3. Execute via cheapest option
  4. Fallback: if primary fails, try secondary
  5. Config: preferred provider per chain pair
- **Validation**: Router picks optimal bridge for 5 different chain pairs.

### Task 4.5: NEAR Intents Payment Flexibility Wrapper (FUTURE TODO)
- **File**: `scripts/kk/lib/near-intents-wrapper.ts` (NEW, future)
- **Description**: Allow workers/agents to choose which chain they receive payment on. If someone pays in USDC on Ethereum but the worker wants it on Avalanche, auto-bridge via NEAR Intents 1Click API.
- **Fix**:
  1. NEAR Intents 1Click API: `https://1click.chaindefuser.com/v0/`
  2. MCP server available: `@iqai/mcp-near-intent-swaps` (5 tools)
  3. Fees: ~0.01-0.05% (cheapest of all bridges, competitive solver market)
  4. Integration: Worker sets `preferred_receive_chain` in profile. PaymentDispatcher detects mismatch → routes through NEAR Intents → worker receives on preferred chain.
  5. API key: Free registration, store JWT in AWS Secrets Manager
- **Status**: NOT IN SCOPE for KK v2 — this is a platform-level feature for Execution Market itself. Documented here as the planned solution for cross-chain payment flexibility.
- **Validation**: Worker on Avalanche receives USDC when agent pays on Base.

---

## Phase 5: Agent Economy Bootstrap (P1)

> **Goal**: Agents start transacting on Execution Market and IRC.

### Task 5.1: Karma Hello Log Sales Service
- **File**: `scripts/kk/services/karma-hello-seller.py` (NEW)
- **Description**: Karma Hello OpenClaw agent sells Twitch logs via x402 on Execution Market.
- **Fix**:
  1. Karma Hello publishes tasks on EM: "Twitch log data available for purchase"
  2. Other agents browse EM, find Karma Hello's offerings
  3. Purchase flow: Agent signs x402 payment → Karma Hello delivers data
  4. Data products: raw logs, user stats, topic analysis, sentiment data
  5. Pricing: 0.01-0.10 USDC per data package
- **Validation**: One agent successfully buys logs from Karma Hello via EM, payment on-chain.

### Task 5.2: Skill Extractor Service
- **File**: `scripts/kk/services/skill-extractor-service.py` (NEW)
- **Description**: Skill Extractor agent buys logs from Karma Hello, processes them, sells skill profiles.
- **Fix**:
  1. Skill Extractor agent discovers Karma Hello's data on EM
  2. Buys raw logs (0.01 USDC)
  3. Processes with LLM → generates skill profile
  4. Publishes enriched skill profile as EM task/service (0.05 USDC)
  5. Other agents buy the enriched data
- **Validation**: Full chain: KH sells → SE buys → SE processes → SE sells → Agent buys.

### Task 5.3: Voice Extractor Service
- **File**: `scripts/kk/services/voice-extractor-service.py` (NEW)
- **Description**: Voice Extractor agent buys logs, processes voice patterns, sells personality profiles.
- **Fix**: Same pattern as 5.2 but for personality/voice analysis.
- **Validation**: Full chain working, personality profile generated and sold.

### Task 5.4: Agent-to-Agent Task Trading
- **File**: `scripts/kk/swarm-runner.py` (NEW)
- **Description**: Orchestrator that enables agents to discover and complete each other's tasks on EM.
- **Fix**:
  1. Each agent periodically browses EM for tasks matching their skills
  2. Agent applies to tasks they can complete
  3. Agent submits evidence/results
  4. Publishing agent reviews and approves/rejects
  5. Payment settles via x402 (gasless)
  6. Both agents rate each other (ERC-8004 reputation)
- **Validation**: 5+ agent-to-agent transactions completed, reputation updated.

### Task 5.5: MeshRelay IRC Integration
- **File**: `scripts/kk/irc/agent-irc-client.py` (NEW)
- **Description**: Each agent connects to MeshRelay IRC for communication and x402 payment-gated channels.
- **Fix**:
  1. Agents connect to `irc.meshrelay.xyz` channel `#Agents`
  2. Agents post in `#marketplace`: "NEED: X data" or "HAVE: Y skill"
  3. Negotiation in private channels
  4. Deals executed on EM
  5. Payment-gated alpha channels (Phase 6 feature)
- **Validation**: 3+ agents visible on IRC, negotiating and executing deals.

### Task 5.6: Daily Activity Cron
- **File**: `scripts/kk/cron/daily-routine.py` (NEW)
- **Description**: Scheduled activity for each agent to maintain economic activity.
- **Fix**:
  Staggered by agent index (agent N starts at minute N*2):
  ```
  06:00 UTC — Check EM for new tasks matching skills
  08:00 UTC — Review own published tasks, check submissions
  10:00 UTC — Post in IRC #marketplace, discover new data
  14:00 UTC — Publish new tasks based on knowledge gaps
  18:00 UTC — Rate completed interactions (ERC-8004)
  22:00 UTC — Summarize daily activity, update memory
  ```
- **Validation**: Cron executes for 24 hours, agents show activity patterns.

---

## Phase 6: Production Launch (P1)

> **Goal**: Full swarm live on Cherry Servers, monitored and self-sustaining.

### Task 6.1: Cherry Servers Terraform
- **File**: `infrastructure/cherry/` (NEW directory, from V2 Architecture doc)
- **Description**: Deploy 2 Cherry Servers VPS with Terraform.
- **Fix**: Use existing Terraform templates from KARMACADABRA_V2_ARCHITECTURE.md section 6.
  - 2x `cloud_vds_2` (4GB RAM, 2 vCPU) in `us_chicago_1`
  - 25 agents per server
  - WireGuard VPN tunnel between servers
  - UFW firewall
- **Validation**: Both servers provisioned, accessible via SSH.

### Task 6.2: Ansible Deployment
- **File**: `infrastructure/cherry/ansible/` (NEW directory)
- **Description**: Ansible playbooks to install OpenClaw, deploy workspaces, configure agents.
- **Fix**: Use playbook from V2 Architecture doc section 7, updated with:
  - Current OpenClaw version
  - Our generated openclaw.json
  - All 55 agent workspaces
  - MCP server connection to EM
- **Validation**: Ansible playbook completes on both servers, all agents boot.

### Task 6.3: Monitoring & Alerting
- **File**: `scripts/kk/monitoring/health-check.py` (NEW)
- **Description**: Health monitoring for the swarm.
- **Fix**:
  1. Check agent count (all 55 online)
  2. Check wallet balances (alert if < $0.50 USDC)
  3. Check EM API connectivity
  4. Check IRC connectivity
  5. Check daily transaction count (alert if 0)
  6. CloudWatch metrics + Slack alerts
- **Validation**: Health check runs every 5 minutes, alerts on simulated failure.

### Task 6.4: Community Dashboard Widget
- **File**: `dashboard/src/components/KKSwarmWidget.tsx` (NEW)
- **Description**: Dashboard widget showing KK swarm activity on execution.market.
- **Fix**:
  1. "Karma Kadabra Swarm" section on dashboard
  2. Shows: active agents count, tasks published today, transactions today, total USDC moved
  3. Agent leaderboard: most active agents
  4. Recent transactions feed
- **Validation**: Widget renders with live data from EM API.

---

## Cross-Chain Token Registry

All USDC addresses for the 8 supported chains (from `sdk_client.py` NETWORK_CONFIG):

| Chain | Chain ID | USDC Address | Native Token |
|-------|----------|-------------|--------------|
| Base | 8453 | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | ETH |
| Ethereum | 1 | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` | ETH |
| Polygon | 137 | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` | MATIC |
| Arbitrum | 42161 | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` | ETH |
| Avalanche | 43114 | (need to extract from NETWORK_CONFIG) | AVAX |
| Monad | 143 | `0x754704Bc059F8C67012fEd69BC8A327a5aafb603` | MON |
| Celo | 42220 | `0xcebA9300f2b948710d2653dD7B07f33A8B32118C` | CELO |
| Optimism | 10 | (need to extract from NETWORK_CONFIG) | ETH |

---

## Cross-Chain Bridging Comparison

| Feature | deBridge DLN | Squid Router | NEAR Intents |
|---------|-------------|--------------|--------------|
| **Type** | Direct bridge | Axelar-powered router | Intent-based solver market |
| **SDK** | REST API (no npm) | `@0xsquid/sdk` (npm) | NEAR SDK + Defuse |
| **Chains** | 20+ EVM + Solana | 60+ (Axelar) | EVM + NEAR + Solana |
| **Speed** | 1-5 min | 2-10 min | Variable (solver-dependent) |
| **Fees** | Low (~0.04-0.1%) | Medium (~0.1-0.3%) | Lowest (competitive) |
| **Complexity** | Low (REST calls) | Medium (SDK) | High (NEAR account) |
| **Best for** | Bulk funding | Multi-hop swaps | Agent autonomy |
| **Recommendation** | Phase 1 (funding) | Phase 4 (agent use) | Phase 6+ (future) |

---

## Budget Allocation ($200-500)

| Allocation | Amount | Purpose |
|-----------|--------|---------|
| USDC for agent wallets | $100-250 | $3-5 per agent across 2-3 primary chains |
| Gas tokens (ETH, MATIC, AVAX) | $20-50 | $0.50-1 per chain for gas |
| Bridge fees | $10-20 | Cross-chain transfers |
| LLM costs (Haiku for extraction) | $5-10 | Skill/voice extraction pipeline |
| Cherry Servers (2 months) | $50-60 | 2x cloud_vds_2 |
| **Reserve** | $20-60 | Unexpected costs |
| **Total** | **$205-450** | Within $200-500 budget |

### Primary Chains (funded first)
1. **Base** — Primary EM chain, most liquidity
2. **Polygon** — Low fees, good for micro-transactions
3. **Arbitrum** — Active DeFi ecosystem

### Secondary Chains (funded in Phase 4)
4. Avalanche, Celo, Optimism, Monad, Ethereum

---

## Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenClaw API changes | Medium | Pin version, test before upgrade |
| USDC balance depletion | High | Balance monitoring + auto-alert at $0.50 |
| Karma Hello logs insufficient | Medium | Supplement with Discord/other sources |
| Bridge fees eat budget | Medium | Use direct transfers where possible, bridge only when needed |
| Agent wallets compromised | Critical | HD wallet from AWS SM, minimal balances |
| Cherry Servers outage | Medium | Auto-restart via systemd, manual failover |
| NEAR Intents not production-ready | Low | Fallback to deBridge/Squid |

---

## Dependencies & Blockers

| Dependency | Status | Blocker? |
|-----------|--------|----------|
| Twitch logs from Karma Hello | AVAILABLE (6 dates + live) | No |
| Execution Market API | LIVE | No |
| x402 Facilitator | LIVE | No |
| Cherry Servers account | EXISTS (team 157112) | No |
| ERC-8004 Registry | LIVE (15 networks) | No |
| OpenClaw latest version | NEEDS VERIFICATION | Possible |
| deBridge DLN API | LIVE | No |
| Squid Router API key | NEEDS REGISTRATION | Minor |
| NEAR Intents SDK | NEEDS RESEARCH | Possible |
| Anthropic API key (for Haiku) | AVAILABLE | No |

---

## Success Metrics

| Metric | Phase 3 Target | Phase 5 Target | Phase 6 Target |
|--------|---------------|---------------|----------------|
| Agents with funded wallets | 34+ | 55 | 55 |
| Agents with SOUL.md | 34+ | 55 | 55 |
| Active agents on EM | 5+ | 20+ | 40+ |
| Tasks published/day | 5+ | 20+ | 50+ |
| Agent-to-agent transactions | 1+ | 10+/day | 50+/day |
| Chains with activity | 1 (Base) | 3+ | 5+ |
| Total USDC moved | $1+ | $10+/day | $50+/day |
| ERC-8004 ratings | 2+ | 20+ | 100+ |
| IRC agents online | 0 | 10+ | 30+ |

---

## File Map (New Files)

```
execution-market/
├── scripts/kk/                          # All KK v2 scripts
│   ├── generate-wallets.ts              # Task 1.1: HD wallet generation
│   ├── distribute-funds.ts              # Task 1.2-1.3: Batch USDC + gas distribution
│   ├── bridge-funds.ts                  # Task 1.4: deBridge cross-chain
│   ├── bridge-squid.ts                  # Task 1.5: Squid Router alternative
│   ├── fund-agents.ts                   # Task 1.6: Main CLI orchestrator
│   ├── check-balances.ts                # Task 1.7: Balance matrix checker
│   ├── aggregate-logs.py                # Task 2.1: Log aggregation
│   ├── user-stats.py                    # Task 2.2: User ranking & stats
│   ├── extract-skills.py                # Task 2.3: LLM skill extraction
│   ├── extract-voice.py                 # Task 2.4: LLM voice/personality extraction
│   ├── generate-soul.py                 # Task 2.5: SOUL.md generator
│   ├── karma-hello-api.py              # Task 2.6: x402 log sales API
│   ├── generate-workspaces.py           # Task 3.2: OpenClaw workspace generator
│   ├── register-agents-erc8004.ts       # Task 3.6: On-chain registration
│   ├── lib/
│   │   ├── debridge-client.ts           # Task 4.1: deBridge integration
│   │   ├── squid-client.ts              # Task 4.2: Squid Router integration
│   │   ├── near-intents-client.ts       # Task 4.3: NEAR Intents prototype
│   │   └── bridge-router.ts             # Task 4.4: Smart bridge router
│   ├── services/
│   │   ├── karma-hello-seller.py        # Task 5.1: KH log sales
│   │   ├── skill-extractor-service.py   # Task 5.2: SE skill sales
│   │   └── voice-extractor-service.py   # Task 5.3: VE personality sales
│   ├── swarm-runner.py                  # Task 5.4: Agent-to-agent trading
│   ├── irc/
│   │   └── agent-irc-client.py          # Task 5.5: IRC integration
│   ├── cron/
│   │   └── daily-routine.py             # Task 5.6: Daily activity cron
│   ├── monitoring/
│   │   └── health-check.py              # Task 6.3: Swarm health monitoring
│   ├── templates/
│   │   └── AGENTS.md.template           # Task 3.3: Agent instruction template
│   ├── skills/
│   │   ├── em-publish-task/SKILL.md     # Task 3.4: EM skill
│   │   ├── em-check-status/SKILL.md     # Task 3.4: EM skill
│   │   ├── em-approve-work/SKILL.md     # Task 3.4: EM skill
│   │   ├── em-browse-tasks/SKILL.md     # Task 3.4: EM skill
│   │   └── em-apply-task/SKILL.md       # Task 3.4: EM skill
│   └── config/
│       ├── funding-config.json          # Per-chain funding amounts
│       └── wallets.json                 # Generated wallet manifest
├── infrastructure/cherry/               # Task 6.1-6.2: Cherry Servers IaC
│   ├── providers.tf
│   ├── variables.tf
│   ├── project.tf
│   ├── ssh_keys.tf
│   ├── swarm_servers.tf
│   ├── outputs.tf
│   ├── openclaw.json.template           # Task 3.5: Multi-agent config
│   └── ansible/
│       ├── playbooks/openclaw.yml
│       └── templates/
│           └── agent-workspace.sh.j2
├── kk_swarm/                            # Generated data (gitignored)
│   ├── souls/                           # 55 SOUL.md files
│   ├── skills/                          # Extracted skill profiles
│   ├── voices/                          # Extracted voice profiles
│   ├── stats/                           # User statistics
│   └── logs/                            # Aggregated log snapshot
└── dashboard/src/components/
    └── KKSwarmWidget.tsx                # Task 6.4: Dashboard widget
```

---

## Reminder: Karma Kadabra Context

> **Karma Kadabra** = Swarm of AI agents from Ultravioleta DAO community
> **Karma Hello** = The bot that collects Twitch chat logs (golden source, running live)
> **OpenClaw** = Agent framework (145K+ stars, formerly Eliza)
> **UltraClawd** = OpenClaw bot on IRC/Telegram
> **MeshRelay IRC** = `irc.meshrelay.xyz` channel `#Agents`
> **Execution Market** = Universal Execution Layer where agents transact
> **x402** = Gasless payment protocol via our Facilitator
> **ERC-8004** = On-chain agent identity + reputation

---

*Plan generated by Claude Opus 4.6 with 6 parallel research agents on 2026-02-19*
*Research covered: deBridge SDK, Squid Router SDK, NEAR Intents, OpenClaw setup, batch EVM distribution, KK repo analysis*
