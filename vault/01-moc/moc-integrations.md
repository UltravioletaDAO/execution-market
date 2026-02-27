---
date: 2026-02-26
tags:
  - type/moc
  - domain/integrations
status: active
aliases:
  - Integrations MOC
  - Ecosystem Integrations
  - External Integrations
---

# Integrations & Ecosystem — Map of Content

> External integrations, upstream dependencies, and ecosystem partnerships.
> Everything that connects Execution Market to the wider world.

---

## CRITICAL BOUNDARY

> **Read this before touching anything related to x402r or the Facilitator.**

[[x402r-team-relationship]] — Ownership boundaries between Ultravioleta DAO and BackTrack:

| Entity | Owns | Does NOT Own |
|--------|------|--------------|
| **Ali / BackTrack** | x402r protocol (contracts, SDK `@x402r/sdk`, ProtocolFeeConfig) | Facilitator |
| **Ultravioleta DAO** | Facilitator (`facilitator.ultravioletadao.xyz`), Repo: `UltravioletaDAO/x402-rs` | x402r contracts or SDK |

- **NEVER** say Ali owns/controls the Facilitator.
- **NEVER** ask Ali to update the Facilitator.
- Facilitator allowlist updates = OUR job (update `addresses.rs` in our x402-rs repo).
- x402r-SDK bugs = Ali's responsibility (report via GitHub issues or IRC).
- When factory addresses are wrong, the bug is in **x402r-SDK**, not in our Facilitator.

---

## Upstream Repos

| Repo | Stack | URL |
|------|-------|-----|
| x402r-contracts | Foundry (Solidity) | `github.com/BackTrackCo/x402r-contracts` |
| x402r-sdk | TypeScript monorepo (pnpm) | `github.com/BackTrackCo/x402r-sdk` |
| x402r docs | Mintlify | `github.com/BackTrackCo/docs` (`docs.x402r.org`) |

These are BackTrack's repositories. We consume them as dependencies. Our Facilitator (`UltravioletaDAO/x402-rs`) wraps the on-chain contracts with gasless settlement logic.

---

## Active Integrations

| Integration | Description |
|-------------|-------------|
| [[chainwitness]] | Evidence notarization (Tier 2, score 7). Used for high-value tasks requiring tamper-proof evidence attestation on-chain. |
| [[irc-meshrelay]] | Agent communication via IRC (`irc.meshrelay.xyz` channel `#Agents`). UltraClawd bot lives here. Used by Karma Kadabra swarm for inter-agent coordination. |

### ChainWitness

- Tier 2 integration (score 7 from SYNERGIES.md)
- Attestation service for evidence files: timestamps proof-of-existence on-chain
- Called from `mcp_server/verification/attestation.py`
- Used when task `evidence_requirements` includes notarization
- Links to [[moc-security]] for evidence verification pipeline

### IRC / MeshRelay

- Server: `irc.meshrelay.xyz`, channel `#Agents`
- Config: `.claude/irc-config.json`
- Skill: `.claude/skills/irc-agent/SKILL.md`
- UltraClawd = OpenClaw bot present in channel
- KK V2 agents coordinate task selection and status updates via IRC

---

## Planned Integrations

| Integration | Description | Status |
|-------------|-------------|--------|
| [[openclaw]] | Insurance/arbitration layer (`github.com/OpenClaw/lobster.cash`). Future dispute resolution for contested task submissions. | Planned |
| [[moltcourt]] | Decentralized arbitration (`moltcourt.fun`). Multi-party dispute resolution. **Future, NOT now.** | Future |
| [[superfluid]] | Payment streaming for recurring/long-running tasks. Placeholder exists in codebase for streaming payment mode. | Placeholder |
| [[turnstile]] | Cloudflare bot protection for task posting rate limiting. Prevents automated spam task creation. | Planned |

### OpenClaw

- Repo: `github.com/OpenClaw/lobster.cash`
- Purpose: Insurance layer for high-value tasks + arbitration for disputes
- Integration plan: `docs/planning/A2A_OPENCLAW_EXECUTION_PLAN.md`
- Detailed plan: `docs/planning/OPENCLAW_INTEGRATION_PLAN.md`
- UltraClawd bot already present in IRC `#Agents` — future bridge to EM dispute flow
- See [[moc-architecture]] for A2A protocol integration points

### MoltCourt

- URL: `moltcourt.fun`
- Decentralized arbitration protocol
- **Status: Future** — no active integration work. Placeholder for when dispute volume justifies dedicated arbitration.

### Superfluid

- Payment streaming protocol
- Use case: Recurring tasks (e.g., daily photo verification) or long-running tasks billed by duration
- Placeholder in codebase — no active implementation

### Turnstile

- Cloudflare Turnstile for bot detection
- Protects task creation and worker registration endpoints
- Links to [[moc-security]] for rate limiting strategy

---

## Ecosystem Partners

From `SYNERGIES.md` — projects with scored integration potential:

| Partner | Tier | Score | Description |
|---------|------|-------|-------------|
| [[colmena]] | 2 | 7 | AI agent orchestration. Colmena foragers discover Execution Market tasks and route them to capable agents. |
| [[council]] | 2 | 7 | Agent governance protocol. Multi-agent task workflows where Council coordinates which agents collaborate on complex tasks. |
| [[ultratrack]] | 3 | 5 | Agent tracking and analytics. Monitors agent performance across Execution Market task completions. |

### Colmena

- AI agent orchestration / swarm intelligence
- Integration: Colmena foragers query EM task feed, select tasks matching agent capabilities
- Synergy: KK V2 swarm agents could be managed by Colmena orchestrator
- Tier 2 — moderate integration effort, high value

### Council

- Multi-agent governance and coordination
- Integration: Council decides which agent in a swarm takes which task
- Synergy: Task workflows requiring multiple agents (e.g., one photographs, another verifies)
- Tier 2 — moderate integration effort, high value

### UltraTrack

- Agent analytics and performance monitoring
- Integration: Consumes reputation data from ERC-8004 registry
- Synergy: Dashboard for monitoring KK swarm health and task completion rates
- Tier 3 — lower priority, useful for observability

---

## Source Files

| File | Purpose |
|------|---------|
| `mcp_server/integrations/x402/sdk_client.py` | `EMX402SDK` — x402 SDK wrapper + multichain token registry (15 EVM, 5 stablecoins). **Single source of truth.** |
| `mcp_server/integrations/x402/payment_dispatcher.py` | Routes payment operations by mode (fase1, fase2, fase5) |
| `mcp_server/integrations/x402/client.py` | Direct HTTP facilitator client (fallback) |
| `mcp_server/a2a/models.py` | A2A protocol models for agent-to-agent communication |
| `mcp_server/verification/attestation.py` | ChainWitness attestation integration |
| `.claude/irc-config.json` | IRC connection config for MeshRelay |
| `.claude/skills/irc-agent/SKILL.md` | IRC agent skill definition |

---

## Documentation

| Doc | Location |
|-----|----------|
| [[SYNERGIES]] | `SYNERGIES.md` — Full ecosystem scoring matrix |
| [[A2A_OPENCLAW_EXECUTION_PLAN]] | `docs/planning/A2A_OPENCLAW_EXECUTION_PLAN.md` |
| [[OPENCLAW_INTEGRATION_PLAN]] | `docs/planning/OPENCLAW_INTEGRATION_PLAN.md` |
| [[X402R_REFERENCE]] | `docs/planning/X402R_REFERENCE.md` — ABIs, contract addresses, condition system |

---

## Cross-Links

- [[moc-blockchain]] — Contract addresses for escrow and operators deployed by x402r team
- [[moc-payments]] — Facilitator integration, SDK client, payment flows
- [[moc-agents]] — IRC for KK swarm coordination, A2A protocol for agent interop
- [[moc-security]] — ChainWitness for evidence notarization, Turnstile for rate limiting
