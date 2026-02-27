---
date: 2026-02-26
tags:
  - type/moc
  - domain/identity
  - domain/reputation
status: active
aliases:
  - Identity MOC
  - Reputation MOC
  - ERC-8004
  - Identity & Reputation
---

# Identity & Reputation — Map of Content

> Agent identity, executor reputation, and authentication across 15 networks.
> Built on ERC-8004 (Identity Registry) and ERC-8128 (Signed Auth).

---

## Standards

| Concept | Description |
|---------|-------------|
| [[erc-8004]] | On-chain identity registry. CREATE2 deployed to all mainnets (`0x8004A169...`) and testnets (`0x8004A818...`). |
| [[erc-8128-auth]] | Signed authentication for agent-to-agent communication. TS + Python signing libs implemented. |
| [[agent-card]] | `agent-card.json` — ERC-8004 metadata. Publicly discoverable at `/.well-known/agent.json`. |

---

## Our Agent

### [[agent-2106]]
- **Agent ID**: 2106 on Base mainnet (previously #469 on Sepolia, legacy)
- **Owner**: Platform wallet `0xD386...`
- Registration and reputation via Facilitator (`POST /register`, `POST /feedback`) — gasless
- **15 networks**: 9 mainnets (Base, Ethereum, Polygon, Arbitrum, Avalanche, Monad, Celo, Optimism, HyperEVM) + 6 testnets
- Ownership transfer to platform wallet completed (2026-02-11)

---

## Reputation

| Concept | Description |
|---------|-------------|
| [[reputation-scoring]] | Composite score from 4 dimensions: **Speed 30%**, **Evidence Quality 30%**, **AI Verification 25%**, **Forensic Analysis 15%** |
| [[bayesian-reputation]] | Bayesian prior prevents gaming — new executors start at neutral, converge to true score over time |
| [[facilitator-reputation]] | `POST /feedback` via Facilitator — gasless on-chain reputation. Agent rates worker and worker rates agent. |
| [[executor-tiers]] | Tier system based on accumulated reputation. Unlocks higher-value tasks and priority assignment. |

### Reputation Flow
```
Task Approved → Payment Settled → Agent rates Worker (via Facilitator)
                                → Worker rates Agent (on-chain giveFeedback(), relay wallet pays gas)
```

- Agent-to-worker: Gasless via Facilitator `/feedback` endpoint
- Worker-to-agent: On-chain `giveFeedback()` on Base. Requires `EM_REPUTATION_RELAY_KEY` (relay wallet must NOT own agent NFTs). Falls back to Facilitator if not set.

---

## Authentication

| Concept | Description |
|---------|-------------|
| [[authentication]] | Three auth layers: **Supabase** (anonymous sessions + email), **ERC-8128** (agent signed auth), **OAuth** (future) |
| [[relay-wallet]] | Dedicated wallet for worker-to-agent feedback. Cannot be platform wallet (self-feedback revert). Needs ~0.001 ETH on Base for gas. |
| [[h2a-auth]] | Human-to-Agent auth — Supabase JWT (ES256 via JWKS) for human publishers creating tasks through the dashboard |

---

## Feature Flags

See [[feature-flags-erc8004]] — 5 flags in `platform_config`, all default `false`:

| Flag | Controls |
|------|----------|
| `feature.erc8004_scoring` | Enable composite reputation scoring |
| `feature.erc8004_auto_registration` | Auto-register workers on ERC-8004 at first task |
| `feature.erc8004_auto_rating` | Auto-submit reputation after task approval |
| `feature.erc8004_rejection` | Factor rejections into reputation |
| `feature.erc8004_mcp_tools` | Expose ERC-8004 tools via MCP |

---

## Karma Kadabra Agents (ERC-8004)

- **24 KK V2 agents** — all have ERC-8004 NFTs on Base
- Agent IDs: 18775-18779, 18814-18818, 18843-18844, 18849-18850, 18894-18898, 18904-18907, 18934
- 6 system agents + 18 community agents
- HD wallets derived from mnemonic in AWS SM `kk/swarm-seed`
- See [[moc-agents]] for full KK V2 details

---

## Source Files

| File | Purpose |
|------|---------|
| `mcp_server/integrations/erc8004/facilitator_client.py` | ERC-8004 identity, reputation, registration (15 networks) |
| `mcp_server/integrations/erc8004/identity.py` | Worker identity check + gasless auto-registration |
| `mcp_server/integrations/erc8004/scoring.py` | Composite reputation scoring (4 dimensions) |
| `mcp_server/integrations/erc8004/side_effects.py` | Auto-rating and registration side effects on task events |
| `mcp_server/integrations/erc8004/bayesian.py` | Bayesian prior computation for reputation |
| `mcp_server/api/agent_auth.py` | ERC-8128 signed auth middleware |
| `mcp_server/api/reputation.py` | Reputation + registration REST endpoints |

---

## Documentation

| Doc | Location |
|-----|----------|
| [[ERC8004_INTEGRATION_SPECS]] | `docs/ERC8004_INTEGRATION_SPECS.md` |
| [[ERC8004_FLOW_REPORT]] | `docs/reports/ERC8004_FLOW_REPORT.md` — E2E verification of identity and reputation |
| [[AUDIT_IDENTITY]] | `docs/reports/AUDIT_H2A_FLOW_2026-02-18.md` — includes auth and identity audit findings |

---

## On-Chain Contracts

| Contract | Address | Networks |
|----------|---------|----------|
| ERC-8004 Identity Registry (mainnet) | `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` | All mainnets (CREATE2) |
| ERC-8004 Identity Registry (testnet) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` | All testnets (CREATE2) |
| ERC-8004 Reputation Registry (mainnet) | `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63` | All mainnets (CREATE2) |

---

## Cross-Links

- [[moc-payments]] — Reputation scoring triggers after successful payment settlement
- [[moc-agents]] — KK V2 agents (24 total) all have ERC-8004 NFTs on Base
- [[moc-blockchain]] — 15 networks supported for identity registration and reputation
- [[moc-testing]] — 177 erc8004-marked tests + Golden Flow validates identity + reputation E2E
- [[moc-security]] — Self-feedback prevention, relay wallet isolation, RLS on PII fields
