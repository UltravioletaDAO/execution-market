# KarmaCadabra V2 -- Complete Migration Handoff

> **Purpose**: Comprehensive context document for migrating KarmaCadabra V2 from the Execution Market monorepo to its own repository, and integrating with MeshRelay.
>
> **Date**: 2026-02-23
> **Author**: Claude Code (Opus 4.6) + 0xultravioleta
> **For**: Fresh Claude Code session in the new KK repo

---

## 1. Executive Summary

### What Is KarmaCadabra V2

KarmaCadabra V2 (KK v2) is a **swarm of 24 autonomous AI agents** representing members of the Ultravioleta DAO community. Each agent is a digital twin of a real community member, extracted from Twitch chat logs, with its own:

- **Personality** (SOUL.md) generated from their chat history
- **Funded wallet** with stablecoins across 8 EVM chains ($6.18 per agent)
- **ERC-8004 on-chain identity** (registered on Base mainnet)
- **Execution Market integration** for buying/selling data and services
- **IRC connection** to MeshRelay for inter-agent communication

### Evolution from V1

KK v1 was a simple marketplace demo with static JSON profiles. KK v2 evolved it into a fully autonomous agent swarm:

- **V1**: 48 static user profiles + 5 system agents, no wallets, no on-chain presence, no autonomous behavior
- **V2**: 24 agents (6 system + 18 community) with funded wallets on 8 chains, ERC-8004 identities, autonomous task execution, data economy, IRC communication, and coordinator-based orchestration

### Current State (2026-02-23)

| Metric | Value |
|--------|-------|
| Total agents | 24 (6 system + 18 community) |
| Chains covered | 8 (Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, Monad) |
| Stablecoins | 5 (USDC, EURC, AUSD, PYUSD, USDT) |
| Total funds in agents | $148.12 |
| Total funds in master wallet | $42.81 |
| **Grand total** | **$190.93** |
| Per-agent average | $6.17 |
| ERC-8004 identities | 24/24 on Base mainnet |
| Wallet-chain slots funded | 192/192 |
| Development phases completed | Phases 1-11 (all) |

---

## 2. Architecture Overview

### Swarm Runner Architecture

The swarm operates on a **heartbeat model** -- each agent wakes every 15 minutes, checks for work, executes tasks, and goes back to sleep. The architecture has three layers:

```
COORDINATOR LAYER
  kk-coordinator -- routes tasks, monitors health, generates standups

DATA AGENT LAYER
  kk-karma-hello     -- collects/sells Twitch chat logs
  kk-abracadabra     -- buys data, generates content intelligence
  kk-skill-extractor -- extracts skill profiles from logs
  kk-voice-extractor -- extracts personality/voice profiles
  kk-soul-extractor  -- fuses skills + voice into SOUL.md profiles
  kk-validator       -- verifies evidence and agent behavior

COMMUNITY AGENT LAYER (18 agents)
  kk-juanjumagalp, kk-elboorja, kk-stovedove, ... (see full roster below)
  Each: browses EM, applies to tasks, submits evidence, gets paid
```

### Core Services

| Service | File | Purpose |
|---------|------|---------|
| `coordinator_service.py` | `services/coordinator_service.py` | 6-factor task matching, assignment, health monitoring |
| `karma_hello_service.py` | `services/karma_hello_service.py` | IRC log collection, data publishing, fulfillment |
| `karma_hello_seller.py` | `services/karma_hello_seller.py` | Data product catalog (raw_logs, user_stats, topic_map, skill_profile) |
| `abracadabra_service.py` | `services/abracadabra_service.py` | 4-phase content intelligence: discover, buy, generate, sell |
| `abracadabra_skills.py` | `services/abracadabra_skills.py` | 5-skill registry: analyze, predict, blog, clips, knowledge graph |
| `em_client.py` | `services/em_client.py` | HTTP client for EM REST API with EIP-8128 auth |
| `skill_extractor_service.py` | `services/skill_extractor_service.py` | Buys logs, extracts skill profiles, sells on EM |
| `voice_extractor_service.py` | `services/voice_extractor_service.py` | Buys logs, extracts personality profiles, sells on EM |
| `soul_extractor_service.py` | `services/soul_extractor_service.py` | Fuses skills + voice into complete SOUL.md profiles |
| `standup_service.py` | `services/standup_service.py` | Daily standup report generator |
| `relationship_tracker.py` | `services/relationship_tracker.py` | Agent-to-agent trust scoring |
| `irc_service.py` | `services/irc_service.py` | IRC integration service |

### Core Libraries

| Library | File | Purpose |
|---------|------|---------|
| `chains.ts` | `lib/chains.ts` | 8-chain config, token addresses, RPC URLs, Disperse.app availability |
| `bridge-router.ts` | `lib/bridge-router.ts` | Smart bridge selection (deBridge for most, Squid for Celo) |
| `debridge-client.ts` | `lib/debridge-client.ts` | deBridge DLN REST API client |
| `squid-client.ts` | `lib/squid-client.ts` | Squid Router API client |
| `irc_client.py` | `lib/irc_client.py` | Raw socket IRC client for MeshRelay (TLS, threading, message queue) |
| `eip8128_signer.py` | `lib/eip8128_signer.py` | EIP-8128 request signing for EM API auth |
| `swarm_state.py` | `lib/swarm_state.py` | Supabase client: heartbeats, task claims, notifications |
| `working_state.py` | `lib/working_state.py` | WORKING.md parser/writer for agent state persistence |
| `memory.py` | `lib/memory.py` | MEMORY.md + daily notes management |
| `soul_fusion.py` | `lib/soul_fusion.py` | Merge skills + voice + stats into unified profiles |
| `performance_tracker.py` | `lib/performance_tracker.py` | Agent performance metrics for enhanced matching |
| `observability.py` | `lib/observability.py` | Logging and observability utilities |
| `turnstile_client.py` | `lib/turnstile_client.py` | Turnstile bot payment client |
| `acontext_client.py` | `lib/acontext_client.py` | AContext integration client |

### Monitoring

| Component | File | Purpose |
|-----------|------|---------|
| `balance_monitor.py` | `monitoring/balance_monitor.py` | Cross-chain USDC balance monitoring for all 24 wallets |
| `health_check.py` | `monitoring/health_check.py` | EM API, IRC, wallet, transaction, workspace health checks |

### Fund Management Pipeline

The complete lifecycle for managing agent funds across 8 chains:

```
1. INVENTORY:    npx tsx kk/check-full-inventory.ts
                 Shows all stablecoin + native gas balances on all 8 chains

2. PLAN:         npx tsx kk/generate-allocation.ts --budget 200
                 Generates randomized per-agent allocation

3. BRIDGE:       npx tsx kk/bridge-from-source.ts --source avalanche
                 Bridges USDC from source chain to all targets via deBridge/Squid

4. GAS:          npx tsx kk/bridge-gas.ts
                 Bridges USDC -> native gas tokens on all chains

5. DISTRIBUTE:   npx tsx kk/distribute-funds.ts --chain base --tokens USDC,EURC --amount 0.10
                 Fan-out tokens to all 24 agents (Disperse.app or sequential)

6. VERIFY:       npx tsx kk/check-full-inventory.ts
                 Confirm all slots funded

7. REBALANCE:    npx tsx kk/sweep-funds.ts --target 0xD386...
                 Sweep back to master if needed
```

### Coordinator Matching Algorithm

The coordinator uses **6-factor enhanced matching** to assign tasks:

| Factor | Weight | Description |
|--------|--------|-------------|
| Skill keywords | 30% | How well agent skills match task title/description |
| Reliability | 20% | Historical completion rate |
| Category experience | 15% | Previous success in same task category |
| Chain experience | 10% | Familiarity with the payment network |
| Budget fit | 10% | Whether agent can afford the task |
| Unified reputation | 15% | ERC-8004 on-chain reputation score |

---

## 3. The 24 Agents

### System Agents (6)

| # | Agent | HD Index | ERC-8004 ID (Base) | Wallet | Role |
|---|-------|----------|-------------------|--------|------|
| 0 | kk-coordinator | m/44'/60'/0'/0/0 | 18775 | `0xE66C0A51...` | Squad lead, task routing, health monitoring |
| 1 | kk-karma-hello | m/44'/60'/0'/0/1 | 18776 | `0xa3279F74...` | Data seller, Twitch/IRC log collection |
| 2 | kk-skill-extractor | m/44'/60'/0'/0/2 | 18777 | `0xE3fB9e15...` | Skill profile extraction from logs |
| 3 | kk-voice-extractor | m/44'/60'/0'/0/3 | 18778 | `0x8E503212...` | Personality/voice profile extraction |
| 4 | kk-validator | m/44'/60'/0'/0/4 | 18779 | `0x7a729393...` | Quality assurance, evidence verification |
| 5 | kk-soul-extractor | m/44'/60'/0'/0/5 | 18895 | `0x04EaEDdB...` | Fuses skills + voice into SOUL.md profiles |

### Community Agents (18)

| # | Agent | HD Index | ERC-8004 ID (Base) | Wallet |
|---|-------|----------|-------------------|--------|
| 6 | kk-juanjumagalp | m/44'/60'/0'/0/6 | 18896 | `0x3aebb73a...` |
| 7 | kk-elboorja | m/44'/60'/0'/0/7 | 18897 | `0xFa1c6fF4...` |
| 8 | kk-stovedove | m/44'/60'/0'/0/8 | 18898 | `0x6F2b09b3...` |
| 9 | kk-0xroypi | m/44'/60'/0'/0/9 | 18934 | `0x46BdfD82...` |
| 10 | kk-sanvalencia2 | m/44'/60'/0'/0/10 | 18814 | `0x64dbE996...` |
| 11 | kk-0xjokker | m/44'/60'/0'/0/11 | 18815 | `0x5975442E...` |
| 12 | kk-cyberpaisa | m/44'/60'/0'/0/12 | 18816 | `0x3a42417C...` |
| 13 | kk-cymatix | m/44'/60'/0'/0/13 | 18817 | `0x812d9Aa3...` |
| 14 | kk-eljuyan | m/44'/60'/0'/0/14 | 18818 | `0x914c38fC...` |
| 15 | kk-1nocty | m/44'/60'/0'/0/15 | 18843 | `0x3a3f992d...` |
| 16 | kk-elbitterx | m/44'/60'/0'/0/16 | 18844 | `0x7Fd9F9E5...` |
| 17 | kk-acpm444 | m/44'/60'/0'/0/17 | 18849 | `0x724159D6...` |
| 18 | kk-davidtherich | m/44'/60'/0'/0/18 | 18850 | `0x9688385...` |
| 19 | kk-karenngo | m/44'/60'/0'/0/19 | 18894 | `0x0ad9a136...` |
| 20 | kk-datbo0i_lp | m/44'/60'/0'/0/20 | 18904 | `0x350Ef06F...` |
| 21 | kk-psilocibin3 | m/44'/60'/0'/0/21 | 18905 | `0xEDc637d4...` |
| 22 | kk-0xsoulavax | m/44'/60'/0'/0/22 | 18906 | `0x62e55e03...` |
| 23 | kk-painbrayan | m/44'/60'/0'/0/23 | 18907 | `0xc059B9cd...` |

### Per-Agent Funding (as of 2026-02-23)

Each agent holds approximately $6.18 total across 8 chains:

| Chain | USDC | EURC | AUSD | PYUSD | USDT | Total/agent |
|-------|------|------|------|-------|------|-------------|
| Monad | $0.75 | - | $0.25 | - | - | $1.00 |
| Arbitrum | $0.75 | - | - | - | $0.20 | $0.95 |
| Avalanche | $0.50 | $0.35 | $0.10 | - | - | $0.95 |
| Base | $0.75 | $0.10 | - | - | - | $0.85 |
| Polygon | $0.50 | - | $0.25 | - | - | $0.75 |
| Optimism | $0.75 | - | - | - | - | $0.75 |
| Celo | $0.02 | - | - | - | $0.45 | $0.47 |
| Ethereum | $0.10 | $0.12 | $0.12 | $0.12 | - | $0.46 |
| **Total** | **$4.12** | **$0.57** | **$0.72** | **$0.12** | **$0.65** | **$6.18** |

**Exceptions**: `kk-coordinator` and `kk-karma-hello` have Base USDC = $0.65 (total $6.08/agent).

### Per-Agent Native Gas

| Chain | Symbol | Amount | Sufficient for |
|-------|--------|--------|----------------|
| Base | ETH | 0.0002 | ~50 TXs |
| Ethereum | ETH | 0.0003 | ~5 TXs |
| Polygon | POL | 0.1000 | ~200 TXs |
| Arbitrum | ETH | 0.0002 | ~50 TXs |
| Avalanche | AVAX | 0.0050 | ~20 TXs |
| Optimism | ETH | 0.0002 | ~50 TXs |
| Celo | CELO | 0.0100 | ~100 TXs |
| Monad | MON | 0.0100 | ~100 TXs |

---

## 4. Multi-Chain Infrastructure

### The 8 Chains

| Chain | Chain ID | Native Token | deBridge Support | Squid Support | Disperse.app |
|-------|----------|-------------|-----------------|---------------|-------------|
| Base | 8453 | ETH | Yes | Yes | Yes |
| Ethereum | 1 | ETH | Yes | Yes | Yes |
| Polygon | 137 | POL | Yes | Yes | Yes |
| Arbitrum | 42161 | ETH | Yes | Yes | Yes |
| Avalanche | 43114 | AVAX | Yes | Yes | No |
| Optimism | 10 | ETH | Yes | Yes | Yes |
| Celo | 42220 | CELO | **No** | Yes | No |
| Monad | 143 | MON | Yes (chain ID: 100000030) | **No** | No |

### Token Addresses Per Chain

#### USDC (all 8 chains)

| Chain | Address |
|-------|---------|
| Base | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Ethereum | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| Polygon | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| Arbitrum | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| Avalanche | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` |
| Optimism | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |
| Celo | `0xcebA9300f2b948710d2653dD7B07f33A8B32118C` |
| Monad | `0x754704Bc059F8C67012fEd69BC8A327a5aafb603` |

#### EURC (3 chains)

| Chain | Address |
|-------|---------|
| Base | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` |
| Ethereum | `0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c` |
| Avalanche | `0xC891EB4cbdEFf6e073e859e987815Ed1505c2ACD` |

#### AUSD -- Agora Dollar (5 chains, CREATE2: same address)

| Chain | Address |
|-------|---------|
| Ethereum | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |
| Polygon | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |
| Arbitrum | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |
| Avalanche | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |
| Monad | `0x00000000eFE302BEAA2b3e6e1b18d08D69a9012a` |

#### PYUSD (1 chain)

| Chain | Address |
|-------|---------|
| Ethereum | `0x6c3ea9036406852006290770BEdFcAbA0e23A0e8` |

#### USDT (4 chains)

| Chain | Address |
|-------|---------|
| Arbitrum | `0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9` |
| Optimism | `0x01bff41798a0bcf287b996046ca68b395dbc1071` |
| Celo | `0x48065fbBE25f71C9282ddf5e1cD6D6A887483D5e` |

### Bridge Infrastructure

**deBridge DLN** (preferred, 7/8 chains):
- REST API: `https://api.dln.trade/v1.0/`
- No SDK needed, pure HTTP
- Monad uses special chain ID: `100000030`
- Fees: ~0.04-0.1%, fastest (1-5 min)
- Client: `lib/debridge-client.ts`

**Squid Router** (fallback, 7/8 chains):
- REST API, requires `SQUID_INTEGRATOR_ID`
- Only bridge that supports Celo
- Does NOT support Monad
- Fees: ~0.1-0.3%
- Client: `lib/squid-client.ts`

**Bridge Router** (`lib/bridge-router.ts`):
- Auto-selects optimal bridge per route
- Rules: Same chain = direct, Celo = Squid, Monad = deBridge, else = deBridge

### Disperse.app

Address (same on all deployed chains): `0xD152f549545093347A162Dce210e7293f1452150`

Sends tokens/ETH to N recipients in 1 TX (45% gas savings). Available on Base, Ethereum, Polygon, Arbitrum, Optimism. NOT available on Avalanche, Celo, Monad (uses sequential transfers instead).

---

## 5. Execution Market Integration

### How KK Agents Use EM

KK agents interact with Execution Market as both **publishers** (offering data/services for bounties) and **workers** (completing tasks for payment):

```
PUBLISH FLOW:
  Agent -> POST /api/v1/tasks (publish task with bounty)
  Other agents browse -> GET /api/v1/tasks/available
  Worker applies -> POST /api/v1/tasks/{id}/apply
  Agent assigns -> POST /api/v1/tasks/{id}/assign
  Worker submits evidence -> POST /api/v1/tasks/{id}/submit
  Agent approves -> POST /api/v1/submissions/{id}/approve
  Payment settles via x402 (gasless, EIP-3009)

CONSUME FLOW:
  Agent browses -> GET /api/v1/tasks/available
  Agent applies -> POST /api/v1/tasks/{id}/apply
  Agent submits work -> POST /api/v1/tasks/{id}/submit
  Publisher approves -> payment received
```

### EM API Endpoints Used by Agents

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/tasks` | POST | Publish a new task |
| `/api/v1/tasks/available` | GET | Browse available tasks |
| `/api/v1/tasks/{id}` | GET | Get task details |
| `/api/v1/tasks/{id}/apply` | POST | Apply to a task as worker |
| `/api/v1/tasks/{id}/assign` | POST | Assign a worker to a task |
| `/api/v1/tasks/{id}/submit` | POST | Submit evidence for a task |
| `/api/v1/tasks/{id}/cancel` | POST | Cancel a published task |
| `/api/v1/submissions/{id}/approve` | POST | Approve a submission + trigger payment |
| `/api/v1/submissions/{id}/reject` | POST | Reject a submission |
| `/api/v1/tasks/{id}/submissions` | GET | Get submissions for a task |
| `/api/v1/health` | GET | API health check |
| `/api/v1/public/metrics` | GET | Public metrics (tasks today, etc.) |

### The em_client.py Service

The `EMClient` class is the shared HTTP client for all agent-EM interactions:

```python
from services.em_client import EMClient, AgentContext, load_agent_context

# Load agent from workspace
agent = load_agent_context(Path("data/workspaces/kk-juanjumagalp"))

# Create client (auto-configures EIP-8128 auth if private key available)
client = EMClient(agent)

# Publish a task
result = await client.publish_task(
    title="[KK Data] Community Stats",
    instructions="...",
    category="knowledge_access",
    bounty_usd=0.03,
    deadline_hours=24,
    evidence_required=["text"],
)

# Browse tasks
tasks = await client.browse_tasks(status="published", limit=20)

# Apply to a task
await client.apply_to_task(task_id="abc-123", executor_id="uuid", message="KK agent")

# Submit evidence
await client.submit_evidence(task_id="abc-123", executor_id="uuid", evidence={"url": "...", "type": "text"})

# Approve submission
await client.approve_submission(submission_id="def-456", rating_score=85)

await client.close()
```

**Authentication priority**:
1. EIP-8128 wallet signatures (if `agent.private_key` is set)
2. API key header (if `agent.api_key` is set)
3. Plain `X-Agent-Wallet` header (fallback)

**API Base**: `https://api.execution.market` (production), configurable via `EM_API_URL` env var.

### x402 Payment Flow

Payments between agents use the x402 protocol with gasless EIP-3009 signatures:

```
1. Agent publishes task with bounty (e.g., $0.10 USDC on Base)
2. Worker applies, gets assigned, submits evidence
3. Agent approves submission
4. EM server signs 2 EIP-3009 transferWithAuthorization:
   a. Agent -> Worker (bounty amount, e.g., $0.087)
   b. Agent -> Treasury (13% platform fee, e.g., $0.013)
5. Facilitator settles both on-chain (gasless -- Facilitator pays gas)
6. Both parties rate each other (ERC-8004 reputation)
```

**Facilitator**: `https://facilitator.ultravioletadao.xyz` (OURS -- Ultravioleta DAO controls it)

---

## 6. MeshRelay Integration (NEW)

### What Is MeshRelay

MeshRelay (`meshrelay.xyz`) is an IRC server for AI agents with:
- **IRC Server**: InspIRCd 3.x + Anope services at `irc.meshrelay.xyz:6697` (TLS)
- **x402 Payments**: Premium channels with USDC paywall on Base via Turnstile bot
- **Unified API + MCP**: `api.meshrelay.xyz` with 9 MCP tools + REST + Swagger UI
- **Agent Verification**: Registration system via Lambda + Supabase
- **Website**: `meshrelay.xyz` with live chat, 3D visualization, stats

### What Agents Can Do TODAY

1. **IRC Basic** (LIVE):
   - Connect to `irc.meshrelay.xyz:6697` with TLS
   - Register nick via NickServ
   - Join public channels (#general, #Agents)
   - Send messages and DMs

2. **x402 Premium Channels** (LIVE):
   - Pay USDC on Base to access premium channels
   - Endpoint: `POST https://api.meshrelay.xyz/payments/access/#channel`
   - Header `Payment` with x402 signature
   - After payment: Turnstile executes SAJOIN automatically
   - Sessions with duration and auto-expiry
   - First real payment: 2026-02-22, $0.10 USDC

3. **MCP Tools** (LIVE):
   - `POST https://api.meshrelay.xyz/mcp` (Streamable HTTP)
   - Available tools: `meshrelay_get_stats`, `meshrelay_list_channels`, `meshrelay_get_messages`, etc.

### What Is Coming (MRServ Phases)

| Capability | Phase | Status |
|------------|-------|--------|
| MRServ feedback (`/msg MRServ FEEDBACK #chan 4 "good"`) | 1 | Planned |
| Channel analytics/scores | 2 | Planned |
| ERC-8004 identity on-chain linking | 3 | Planned |
| Referral system (P2P marketing) | 4 | Planned |
| Create own premium channels + revenue split | 5 | Planned |
| Full MCP tools for all features | 6 | Planned |

### 4 Business Scenarios for KK Agents

**Scenario 1 -- Consume Alpha**:
```
Agent browses top channels by score -> pays $1.00 via x402 -> SAJOIN ->
listens for 1 hour -> gives feedback 5/5 -> reputation boost
```

**Scenario 2 -- Create Alpha Channel**:
```
3 KK agents detect good info -> Agent-1 creates #kk-triple-alpha at $2.00/hr ->
adds 2 co-owners -> revenue split: 85% owners (28.3% each), 10% MeshRelay, 5% referrer
```

**Scenario 3 -- P2P Marketing**:
```
Agent had good experience -> refers channel to another agent ->
if referred agent pays, referrer gets reputation boost
```

**Scenario 4 -- Reputation as Social Currency**:
```
High-reputation agent (95/100) enters channel -> channel score rises ->
more agents pay to enter (flywheel) -> agent can create premium channels
```

### APIs KK Needs to Know

#### Live Now

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `wss://bridge.meshrelay.xyz/ws` | WebSocket | Real-time chat |
| `https://api.meshrelay.xyz/irc/stats` | GET | Server statistics |
| `https://api.meshrelay.xyz/irc/channels` | GET | List channels |
| `https://api.meshrelay.xyz/irc/channels/:ch/messages` | GET | Recent messages |
| `https://api.meshrelay.xyz/payments/channels` | GET | Premium channels |
| `https://api.meshrelay.xyz/payments/access/:ch` | POST | Pay + access channel |
| `https://api.meshrelay.xyz/payments/sessions/:nick` | GET | Active sessions |
| `https://api.meshrelay.xyz/mcp` | POST | MCP endpoint |

#### Coming Soon

| Endpoint | Phase | Purpose |
|----------|-------|---------|
| `GET /analytics/channels` | 2 | Channels with scores |
| `GET /analytics/agents/:nick` | 2 | Agent reputation |
| `GET /analytics/leaderboard/channels` | 2 | Top channels |
| `GET /analytics/leaderboard/agents` | 2 | Top agents |
| MRServ IRC commands | 1-5 | Feedback, reputation, referrals, channel creation |

### What Needs Implementation in Each Agent

1. **IRC Client Integration** -- use `lib/irc_client.py` (already written, raw socket, TLS)
2. **NickServ Registration** -- `/msg NickServ REGISTER password email`
3. **x402 Payment Capability** -- wallet with USDC on Base, EIP-3009 signing
4. **MRServ Commands** (when available) -- feedback, reputation, referrals, channel creation
5. **ERC-8004 Identity Linking** (when available) -- link IRC nick to on-chain identity

### IRC Connection Example (Python)

```python
from lib.irc_client import IRCClient

client = IRCClient(
    server="irc.meshrelay.xyz",
    port=6697,
    nick="kk-juanjumagalp",
    realname="Karma Kadabra Agent - Ultravioleta DAO",
    use_tls=True,
)

if client.connect():
    # Authenticate with NickServ
    client.send_message("NickServ", "IDENTIFY mypassword")

    # Join channels
    client.join("#Agents")
    client.join("#general")

    # Send message
    client.send_message("#Agents", "[HELLO] kk-juanjumagalp online!")

    # Poll for messages (non-blocking)
    messages = client.poll_messages()
    for msg in messages:
        print(f"[{msg.channel}] {msg.nick}: {msg.text}")

    client.disconnect()
```

### IRC Connection Example (Node.js)

```javascript
import IRC from 'irc-framework';

const client = new IRC.Client();
client.connect({
    host: 'irc.meshrelay.xyz',
    port: 6697,
    tls: true,
    nick: 'KK-Agent-001',
    username: 'kk-agent',
    gecos: 'KarmaCadabra Agent',
});

client.on('registered', () => {
    client.say('NickServ', 'IDENTIFY mypassword');
    client.join('#general');
});

client.on('message', (event) => {
    console.log(`[${event.target}] ${event.nick}: ${event.message}`);
});
```

---

## 7. IRC Infrastructure

### Current Setup

| Field | Value |
|-------|-------|
| Server | `irc.meshrelay.xyz` |
| Plaintext port | 6667 |
| TLS port | 6697 |
| IRC daemon | InspIRCd 3.x |
| Services | Anope (NickServ, ChanServ) |
| Default channel | `#Agents` |
| Max message length | 512 bytes (IRC standard) |

### The irc_client.py Library

The KK repo includes a pure-Python IRC client with zero external dependencies:

- **Raw sockets** (no `irc` or `irc-framework` dependency)
- **TLS support** (wrap_socket with CERT_NONE for self-signed)
- **Threading** (background recv loop with message queue)
- **Nick collision handling** (auto-appends timestamp suffix)
- **Message splitting** (chunks at 400 chars for safety)
- **Callbacks** (`on_message` for real-time message handling)

### NickServ Registration

Each agent needs a registered nick:

```
/msg NickServ REGISTER <password> <email>
/msg NickServ IDENTIFY <password>
```

**Action needed**: Register all 24 agent nicks on MeshRelay NickServ. Use format `kk-{name}` (e.g., `kk-juanjumagalp`, `kk-coordinator`).

### Channels

| Channel | Purpose |
|---------|---------|
| `#Agents` | General agent communication |
| `#general` | Public chat |
| `#meshrelay` | MeshRelay support/discussion |
| `#kk-ops` | (planned) KK operational channel |
| `#kk-data-market` | (planned) KK data marketplace |

Channels are case-insensitive: `#KK-Alpha` = `#kk-alpha`.

---

## 8. AWS Infrastructure

### Secrets

| Secret | Location | Contents |
|--------|----------|----------|
| `kk/swarm-seed` | AWS Secrets Manager (us-east-2) | BIP-44 HD mnemonic for all 24 agent wallets |
| `em/x402` | AWS Secrets Manager (us-east-2) | `PRIVATE_KEY` (master wallet), `SQUID_INTEGRATOR_ID` |
| `em/anthropic` | AWS Secrets Manager (us-east-2) | `ANTHROPIC_API_KEY` |
| `em/test-worker` | AWS Secrets Manager (us-east-2) | `private_key` (test worker wallet) |

### Key Loading Pattern

```javascript
// NEVER show private keys in output
const { execSync } = require('child_process');
const raw = execSync(
    'aws secretsmanager get-secret-value --secret-id em/x402 --query SecretString --output text --region us-east-2',
    { encoding: 'utf8' }
);
const secrets = JSON.parse(raw);
execSync('npx tsx kk/<script>.ts', {
    stdio: 'inherit',
    env: {
        ...process.env,
        WALLET_PRIVATE_KEY: secrets.PRIVATE_KEY,
        PRIVATE_KEY: secrets.PRIVATE_KEY,
        SQUID_INTEGRATOR_ID: secrets.SQUID_INTEGRATOR_ID,
    },
});
```

### Master Wallet

| Field | Value |
|-------|-------|
| Address | `0xD3868E1eD738CED6945A574a7c769433BeD5d474` |
| Key source | AWS SM `em/x402:PRIVATE_KEY` |
| Role | Funds all agent wallets, pays gas for bridges and distribution |
| Current balance | $42.81 across 8 chains |

### Agent Wallets

- 24 wallets derived from HD mnemonic (BIP-44 path `m/44'/60'/0'/0/{0..23}`)
- Mnemonic stored in AWS SM `kk/swarm-seed`
- Wallet manifest: `config/identities.json`

### ECS Infrastructure (terraform/swarm/)

The `terraform/swarm/` directory contains a complete AWS ECS Fargate setup for running the swarm in production:

- **VPC**: `10.0.0.0/16` with public/private subnets
- **ECS Cluster**: `kk-swarm-{environment}` with Fargate + Fargate Spot
- **ECR**: `kk-swarm/openclaw-agent` (shared container image)
- **S3**: Agent state bucket with versioning + Glacier lifecycle
- **CloudWatch**: Centralized logging
- **Secrets Manager**: Anthropic API key
- **Cost alerts**: CloudWatch + SNS

The Dockerfile (`terraform/swarm/Dockerfile`) builds a container with:
- Node.js 22 + Python 3 + AWS CLI
- OpenClaw (Claude Code) globally installed
- Python venv with: httpx, pydantic, eth-account, web3, etc.
- em_bridge package for KC-EM integration
- Personality templates and workspace bootstrapping

**Cost estimates**:
| Agents | Monthly Cost |
|--------|-------------|
| 5 | ~$62 |
| 55 | ~$258 |
| 200 | ~$827 |

---

## 9. Migration Plan

### Directory Structure in New KK Repo

```
karmacadabra/
├── CLAUDE.md                      # Project instructions (generated from this handoff)
├── README.md                      # Project overview
├── package.json                   # TypeScript dependencies (viem, etc.)
├── requirements.txt               # Python dependencies
├── .env.local.example             # Environment variable template
│
├── config/
│   ├── identities.json            # Agent roster with wallets, ERC-8004 IDs
│   ├── funding-config.json        # Per-chain funding amounts
│   └── funding-config.example.json
│
├── lib/                           # Shared libraries
│   ├── chains.ts                  # 8-chain config (TypeScript)
│   ├── bridge-router.ts           # Smart bridge selection
│   ├── debridge-client.ts         # deBridge DLN client
│   ├── squid-client.ts            # Squid Router client
│   ├── irc_client.py              # IRC client (Python)
│   ├── irc-client.ts              # IRC client (TypeScript)
│   ├── eip8128_signer.py          # EIP-8128 auth signer
│   ├── eip8128-signer.ts          # EIP-8128 auth signer (TS)
│   ├── swarm_state.py             # Supabase swarm state client
│   ├── working_state.py           # WORKING.md parser/writer
│   ├── memory.py                  # MEMORY.md + daily notes
│   ├── soul_fusion.py             # Profile fusion logic
│   ├── performance_tracker.py     # Agent performance metrics
│   ├── observability.py           # Logging utilities
│   ├── turnstile_client.py        # Turnstile payment client
│   ├── acontext_client.py         # AContext integration
│   └── memory_bridge.py           # Memory bridge utility
│
├── services/                      # Agent services
│   ├── em_client.py               # EM API client
│   ├── coordinator_service.py     # Coordinator heartbeat + assignment
│   ├── karma_hello_service.py     # Data collection + publishing
│   ├── karma_hello_seller.py      # Data product catalog
│   ├── karma_hello_scheduler.py   # Background scheduler
│   ├── abracadabra_service.py     # Content intelligence (4-phase)
│   ├── abracadabra_skills.py      # 5-skill registry
│   ├── skill_extractor_service.py # Skill extraction
│   ├── voice_extractor_service.py # Voice extraction
│   ├── soul_extractor_service.py  # Soul fusion service
│   ├── standup_service.py         # Daily standup generator
│   ├── relationship_tracker.py    # Trust scoring
│   └── irc_service.py             # IRC integration
│
├── monitoring/                    # Health + balance monitoring
│   ├── balance_monitor.py
│   └── health_check.py
│
├── cron/                          # Scheduled tasks
│   ├── daily_routine.py
│   ├── heartbeat.py
│   └── shutdown_handler.py
│
├── irc/                           # IRC-specific modules
│   ├── abracadabra_irc.py
│   ├── agent_irc_client.py
│   └── log_listener.py
│
├── scripts/                       # CLI scripts (TypeScript)
│   ├── generate-wallets.ts
│   ├── distribute-funds.ts
│   ├── bridge-from-source.ts
│   ├── bridge-gas.ts
│   ├── check-balances.ts
│   ├── check-full-inventory.ts
│   ├── check-all-balances.ts
│   ├── check-eth-status.ts
│   ├── check-native.ts
│   ├── generate-allocation.ts
│   ├── fund-agents.ts
│   ├── sweep-funds.ts
│   └── register-agents-erc8004.ts
│
├── scripts-py/                    # CLI scripts (Python)
│   ├── aggregate-logs.py
│   ├── user-stats.py
│   ├── extract-skills.py
│   ├── extract-voice.py
│   ├── generate-soul.py
│   ├── generate-workspaces.py
│   ├── install-irc-skill.py
│   └── swarm_runner.py
│
├── skills/                        # OpenClaw EM skills
│   ├── em-apply-task/SKILL.md
│   ├── em-approve-work/SKILL.md
│   ├── em-browse-tasks/SKILL.md
│   ├── em-check-status/SKILL.md
│   ├── em-publish-task/SKILL.md
│   ├── em-register-identity/
│   └── irc-agent/SKILL.md
│
├── templates/                     # Agent workspace templates
│   └── AGENTS.md.template
│
├── terraform/                     # AWS ECS Fargate deployment
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── Dockerfile
│   ├── modules/agent/
│   ├── modules/cost-alerts/
│   ├── scripts/
│   └── templates/
│
├── tests/                         # Test suite
│   ├── test_abracadabra_service.py
│   ├── test_acontext_client.py
│   ├── test_balance_monitor.py
│   ├── test_coordinator_enhanced.py
│   ├── test_eip8128_signer.py
│   ├── test_em_client.py
│   ├── test_health_check.py
│   ├── test_irc_client.py
│   ├── test_karma_hello_service.py
│   ├── test_memory.py
│   ├── test_memory_bridge.py
│   ├── test_observability.py
│   ├── test_performance_tracker.py
│   ├── test_relationship_tracker.py
│   ├── test_soul_fusion.py
│   ├── test_standup_service.py
│   ├── test_turnstile_client.py
│   ├── test_turnstile_e2e.py
│   ├── test_turnstile_real_payment.py
│   └── test_working_state.py
│
├── data/                          # Runtime data (gitignored mostly)
│   ├── .gitignore
│   ├── workspaces/                # Per-agent workspaces
│   │   ├── _manifest.json
│   │   ├── kk-coordinator/
│   │   ├── kk-karma-hello/
│   │   └── ...
│   ├── skills/                    # Extracted skills JSON
│   ├── voices/                    # Extracted voice JSON
│   ├── soul-profiles/             # Fused soul profiles
│   ├── irc-logs/                  # IRC message logs
│   └── reputation/                # Reputation snapshots
│
└── docs/                          # Documentation
    ├── FUND_DISTRIBUTION.md       # Fund management reference
    ├── MISSION_CONTROL.md         # Architecture document
    ├── MASTER_PLAN.md             # Original v2 master plan
    └── INVENTORY_2026-02-23.md    # Latest inventory snapshot
```

### What Stays in EM Repo

The Execution Market repo keeps:
- The MCP server (`mcp_server/`)
- The dashboard (`dashboard/`)
- REST API endpoints that KK agents call
- The Supabase migrations (including `036_kk_swarm_state.sql`)
- The admin dashboard
- All EM-specific infrastructure (ECS, ECR, ALB, etc.)

### What Moves to KK Repo

Everything under `scripts/kk/` moves, plus:
- `terraform/swarm/` (complete ECS Fargate setup)
- Relevant docs from `docs/planning/` and `docs/reports/`
- The `scripts/kk/skills/` directory

### Dependencies on EM That KK Keeps

KK agents depend on EM as an **external API**:
- `https://api.execution.market/api/v1/*` -- REST API for tasks, submissions, etc.
- `https://mcp.execution.market/mcp/` -- MCP transport for AI agents
- `https://facilitator.ultravioletadao.xyz` -- x402 payment settlement
- Supabase `kk_swarm_state` table -- shared state (may eventually move to KK's own DB)

The `em_client.py` service abstracts all EM interactions. After migration, update the `API_BASE` default to ensure it points to the correct EM production URL.

---

## 10. Immediate Next Steps

### Priority 1: MeshRelay IRC Integration

1. **Register all 24 agent nicks on MeshRelay NickServ**
   - Use nick format: `kk-{name}` (e.g., `kk-juanjumagalp`)
   - Password strategy: derive from agent private key hash (deterministic, no storage needed)
   - Script: iterate identities.json, connect per agent, send REGISTER command

2. **Implement MeshRelay IRC connection in swarm_runner.py**
   - On heartbeat: connect to IRC if not connected, join #Agents
   - Post agent status: `[HEARTBEAT] kk-{name} online, idle/busy`
   - Listen for @mentions: respond to direct commands
   - Post task announcements: `[TASK] Published: {title} (${bounty})`

3. **Test x402 channel payments from agent wallets**
   - Each agent has USDC on Base ($0.75+)
   - Use `POST https://api.meshrelay.xyz/payments/access/#channel`
   - Sign EIP-3009 authorization
   - Verify SAJOIN after payment

### Priority 2: Business Scenario Implementations

4. **Implement "Consume Alpha" scenario**
   - Agent queries `GET /analytics/leaderboard/channels` (when available)
   - Evaluates channel score vs. price
   - Pays via x402 if score/price ratio exceeds threshold
   - Listens for configurable duration
   - Gives feedback on exit

5. **Implement "Create Alpha Channel" scenario**
   - 3+ agents with related data create premium channel via MRServ
   - Revenue split to co-owners
   - Channel promoted via agent IRC messages

### Priority 3: Repo Setup

6. **Initialize KK repo with proper structure**
   - Copy files from EM repo per migration plan above
   - Update import paths (remove `scripts/kk/` prefix)
   - Set up package.json and requirements.txt
   - Configure CI/CD (GitHub Actions)
   - Write CLAUDE.md for the new repo

7. **Update EM CLAUDE.md to reference KK as external**
   - Remove KK-specific details from EM CLAUDE.md
   - Add note: "KK v2 swarm has moved to its own repo"
   - Keep cross-reference to KK API usage patterns

---

## 11. Key Contracts and Addresses

### ERC-8004 Identity Registry

| Network | Address | Type |
|---------|---------|------|
| All Mainnets | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | CREATE2 (same on all) |
| All Testnets | `0x8004A818BFB912233c491871b3d84c89A494BD9e` | CREATE2 (same on all) |

### ERC-8004 Reputation Registry

| Network | Address |
|---------|---------|
| All Mainnets | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` |

### x402r Escrow (AuthCaptureEscrow)

| Network | Address |
|---------|---------|
| Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| Ethereum | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` |
| Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| Arbitrum, Avalanche, Celo, Monad, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |

### EM PaymentOperator (Fase 5 Trustless Fee Split)

| Network | Address |
|---------|---------|
| Base | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` |
| Ethereum | `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b` |
| Polygon | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` |
| Arbitrum | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Avalanche | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Monad | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` |
| Celo | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Optimism | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |

### Other Addresses

| Entity | Address | Notes |
|--------|---------|-------|
| StaticFeeCalculator (1300 BPS) | `0xd643DB63028Cd1852AAFe62A0E3d2A5238d7465A` | Base |
| Facilitator EOA | `0x103040545AC5031A11E8C03dd11324C7333a13C7` | All chains |
| Execution Market Agent ID | `2106` | Base ERC-8004 |
| EM Platform Wallet | `0xD3868E1eD738CED6945A574a7c769433BeD5d474` | Also KK master wallet |
| EM Treasury | `0xae07...` (Ledger) | Receives 13% platform fee |
| Disperse.app | `0xD152f549545093347A162Dce210e7293f1452150` | Same on all chains |

---

## 12. Environment Variables Reference

### Required for KK Operations

```bash
# --- Execution Market API ---
EM_API_URL=https://api.execution.market          # EM REST API base URL
EM_API_KEY=                                        # Optional API key

# --- Wallets ---
WALLET_PRIVATE_KEY=                                # Master wallet private key (from AWS SM em/x402)
PRIVATE_KEY=                                       # Alias for WALLET_PRIVATE_KEY

# --- Supabase (for swarm state) ---
SUPABASE_URL=https://your-project.supabase.co     # Supabase project URL
SUPABASE_ANON_KEY=                                 # Supabase anonymous key

# --- Bridge Providers ---
SQUID_INTEGRATOR_ID=                               # Squid Router integrator ID (from AWS SM em/x402)

# --- RPC URLs (QuikNode private RPCs preferred) ---
BASE_MAINNET_RPC_URL=                              # Base RPC (fallback: https://mainnet.base.org)
ETHEREUM_RPC_URL=                                  # Ethereum RPC (fallback: https://eth.llamarpc.com)
POLYGON_RPC_URL=                                   # Polygon RPC (fallback: https://polygon-bor-rpc.publicnode.com)
ARBITRUM_RPC_URL=                                  # Arbitrum RPC (fallback: https://arb1.arbitrum.io/rpc)
AVALANCHE_RPC_URL=                                 # Avalanche RPC (fallback: https://api.avax.network/ext/bc/C/rpc)
OPTIMISM_RPC_URL=                                  # Optimism RPC (fallback: https://mainnet.optimism.io)
CELO_RPC_URL=                                      # Celo RPC (fallback: https://forno.celo.org)
MONAD_RPC_URL=                                     # Monad RPC (fallback: https://rpc.monad.xyz)

# --- AI (for extraction pipelines) ---
ANTHROPIC_API_KEY=                                 # For skill/voice extraction (Haiku)

# --- x402 / Facilitator ---
X402_FACILITATOR_URL=https://facilitator.ultravioletadao.xyz
X402_NETWORK=base                                  # Default payment network
```

### AWS Secrets It Reads

| Secret ID | Region | Keys | Purpose |
|-----------|--------|------|---------|
| `kk/swarm-seed` | us-east-2 | `mnemonic` | HD seed for 24 agent wallets |
| `em/x402` | us-east-2 | `PRIVATE_KEY`, `SQUID_INTEGRATOR_ID` | Master wallet key + Squid API |
| `em/anthropic` | us-east-2 | `ANTHROPIC_API_KEY` | LLM API key |

### RPC URL Env Var Mapping

The `chains.ts` module maps env vars to chains:

```typescript
const RPC_ENV_MAP = {
    base: "BASE_MAINNET_RPC_URL",
    ethereum: "ETHEREUM_RPC_URL",
    polygon: "POLYGON_RPC_URL",
    arbitrum: "ARBITRUM_RPC_URL",
    avalanche: "AVALANCHE_RPC_URL",
    optimism: "OPTIMISM_RPC_URL",
    celo: "CELO_RPC_URL",
    monad: "MONAD_RPC_URL",
};
```

**Policy**: Always prefer QuikNode private RPCs from `.env.local`. Only use public RPCs when QuikNode fails for specific known issues.

---

## Appendix A: Data Economy Pricing Matrix

| Data Asset | Seller Agent | Price (USDC) | Refresh |
|-----------|-------------|-------------|---------|
| Chat logs (per stream day) | kk-karma-hello | $0.01-0.05 | On-demand |
| User sentiment scores | kk-karma-hello | $0.02 | Daily |
| Trending topics (global) | kk-abracadabra | $0.01/hour | 5 min |
| 7-day topic predictions | kk-abracadabra | $0.05 | Daily |
| Blog post (generated) | kk-abracadabra | $0.10 | On-demand |
| Clip suggestions | kk-abracadabra | $0.03 | Daily |
| Knowledge graph | kk-abracadabra | $0.02 | On-demand |
| Skill profile | kk-skill-extractor | $0.02 | Weekly |
| Voice/personality profile | kk-voice-extractor | $0.02 | Weekly |
| Complete SOUL.md profile | kk-soul-extractor | $0.08-0.15 | On-demand |
| Profile update (delta) | kk-soul-extractor | $0.04 | On-demand |

## Appendix B: Heartbeat Stagger Schedule

```
:00  kk-coordinator (checks all agents, generates assignments)
:02  kk-karma-hello (collect/publish/fulfill)
:04  kk-abracadabra (discover/buy/generate/sell)
:06  kk-skill-extractor
:08  kk-voice-extractor
:09  kk-soul-extractor
:10  kk-validator + community agents 1-10 (2s apart)
:12  community agents 11-18
```

Each agent wakes every 15 minutes, staggered to avoid rate limiting on EM API and LLM APIs.

## Appendix C: Known Issues and Quirks

1. **Celo is underfunded** ($0.47/agent vs ~$0.95 target) -- Squid Router had zero USDC liquidity during rebalancing. Retry when liquidity returns.

2. **Ethereum is intentionally light** ($0.46/agent) -- L1 gas makes frequent small tasks uneconomical. Agents carry 4 diverse stablecoins for protocol coverage testing.

3. **chains.ts evaluates at module-load time** -- Private RPC URLs from `.env.local` must be loaded BEFORE importing chains.ts. The file self-loads dotenv, but consumer scripts should also load it early.

4. **deBridge approve buffer** -- deBridge execution fee varies between quote and TX time. Always add 2% buffer to approve amount.

5. **Windows shell issues** -- If `echo`, `export` fail in Git Bash, use the Node.js wrapper pattern (see AWS Secrets section).

6. **Python Decimal JSON serialization** -- Python `Decimal` types crash JSON serialization. Use `_sanitize_for_json()`.

7. **Monad USDC address** -- The correct address is `0x754704Bc059F8C67012fEd69BC8A327a5aafb603` (NOT `0xf817...` which was an old incorrect value).

8. **Network naming** -- Use `"base"` not `"base-mainnet"`. The facilitator rejects `"base-mainnet"`.

9. **IRC max message length** -- 512 bytes per IRC standard. The `irc_client.py` splits at 400 chars to be safe.

10. **NEVER SHOW PRIVATE KEYS IN LOGS** -- The developer is always streaming. Use AWS SM wrapper pattern.

---

*Generated 2026-02-23 by Claude Code (Opus 4.6). Source: 20 files across execution-market and meshrelay repos.*
