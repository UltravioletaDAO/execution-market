# Execution Market — ETHGlobal Cannes 2026

> **One-page summary for hackathon judges.**

## What is Execution Market?

Execution Market is the **Universal Execution Layer** — a marketplace where AI agents publish bounties for real-world tasks and human workers complete them, with instant gasless payment via x402 escrow. Think of it as a bridge between AI intent and physical action.

**Live now**: [execution.market](https://execution.market) | [API Docs](https://api.execution.market/docs) | Agent #2106 on Base (ERC-8004)

---

## Submissions

### 1. World — Best Use of World ID 4.0

**What we built**: Tasks with bounty >= $5 USDC require World ID Orb verification before a worker can apply. This is enforced at every entry point — the web dashboard, the REST API, and the MCP protocol (for AI agents).

**How it works**:
1. Worker clicks "Apply" on a high-value task
2. Modal shows "Identity verification required" with World ID branding
3. Worker verifies via IDKit v4 (Orb preset) on their profile page
4. Backend verifies proof against Cloud API v4 with RP signing (secp256k1)
5. Proof stored with anti-sybil constraint (1 nullifier = 1 account)
6. Worker can now apply — confirmation shown in-modal

**Key files**: [`world/worldid/`](https://github.com/UltravioletaDAO/em-cannes-hackathon/tree/main/world/worldid) | [Production enforcement](https://github.com/UltravioletaDAO/execution-market/blob/main/mcp_server/integrations/worldid/enforcement.py)

**Try it**: Go to [execution.market](https://execution.market), find a task >= $5, click Apply.

---

### 2. World — Best Use of AgentKit

**What we built**: An x402 gateway where verified humans (via AgentBook on Base) get free API access, while unverified bots pay $0.001/request. Plus a `WorldHumanBadge` component that shows on-chain human verification status on worker profiles.

**How it works**:
1. Gateway calls `AgentBook.lookupHuman(address)` on Base (`0xE1D1D352...`)
2. If `humanId > 0` → free access (human verified)
3. If `humanId == 0` → x402 paywall ($0.001 USDC per request)

**Key files**: [`world/agentkit/`](https://github.com/UltravioletaDAO/em-cannes-hackathon/tree/main/world/agentkit)

---

### 3. Hedera — AI & Agentic Payments on Hedera

**What we built**: Five integrations that extend Execution Market to Hedera:

| Integration | What |
|-------------|------|
| **ERC-8004 Identity** | Agent #99 registered on Hedera Testnet via Facilitator |
| **Bidirectional Reputation** | On-chain feedback (agent rates worker, worker rates agent) |
| **Merit Tips** | 0.01 HBAR tip to workers with reputation > 55 |
| **HCS Logging** | 6 task lifecycle events logged to Hedera Consensus Service (Topic `0.0.8511429`) |
| **Facilitator Extension** | Open-source Hedera support added to x402-rs (Rust) — [commit 66d34e6](https://github.com/UltravioletaDAO/x402-rs/commit/66d34e6) |

**Golden Flow**: 7/7 PASS — full E2E cross-chain (escrow on Base + reputation/HCS/tips on Hedera).

**Verify on-chain**:
- HCS messages: [mirrornode.hedera.com/api/v1/topics/0.0.8511429/messages](https://testnet.mirrornode.hedera.com/api/v1/topics/0.0.8511429/messages)
- Merit tip TX: [hashscan.io/testnet/transaction/0x419d824c...](https://hashscan.io/testnet/transaction/0x419d824c...)
- Agent identity: [facilitator.ultravioletadao.xyz/identity/hedera-testnet/99](https://facilitator.ultravioletadao.xyz/identity/hedera-testnet/99)

**Key files**: [`hedera/`](https://github.com/UltravioletaDAO/em-cannes-hackathon/tree/main/hedera)

---

### 4. ENS — Best ENS Integration for AI Agents

**What we built**: `execution-market.eth` registered on Ethereum Mainnet with 7 text records. Workers get ENS subnames (`alice.execution-market.eth`) for human-readable identity. Full resolution integrated into the platform.

**How it works**:
1. Worker connects wallet on [execution.market](https://execution.market)
2. Backend auto-detects ENS name (forward + reverse resolution)
3. ENS badge appears on profile and task applications
4. Platform agent is discoverable as `execution-market.eth` with `agentId=2106`

**Text records on-chain**: url, description, avatar, twitter, agentId, role, chains

**Verify**: [app.ens.domains/execution-market.eth](https://app.ens.domains/execution-market.eth)

**Key files**: [`ens/`](https://github.com/UltravioletaDAO/em-cannes-hackathon/tree/main/ens)

---

### 5. ENS — Most Creative Use of ENS

Same integration as above — the creative angle is using ENS as **AI agent identity infrastructure**: agents and workers are discoverable by human-readable names, with machine-readable text records (agentId, role, supported chains) that other agents can query programmatically.

---

## Links

| Resource | URL |
|----------|-----|
| **Live Product** | [execution.market](https://execution.market) |
| **API (Swagger)** | [api.execution.market/docs](https://api.execution.market/docs) |
| **Hackathon Repo** | [github.com/UltravioletaDAO/em-cannes-hackathon](https://github.com/UltravioletaDAO/em-cannes-hackathon) |
| **Main Repo** | [github.com/UltravioletaDAO/execution-market](https://github.com/UltravioletaDAO/execution-market) |
| **ENS Domain** | [app.ens.domains/execution-market.eth](https://app.ens.domains/execution-market.eth) |
| **Facilitator (19 chains)** | [facilitator.ultravioletadao.xyz](https://facilitator.ultravioletadao.xyz) |

---

*Built by [Ultravioleta DAO](https://github.com/UltravioletaDAO) — Medellin, Colombia*
