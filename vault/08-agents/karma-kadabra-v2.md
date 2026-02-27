---
date: 2026-02-26
tags:
  - domain/agents
  - project/karma-kadabra
  - status/active
status: active
aliases:
  - KK V2
  - Karma Kadabra
related-files:
  - docs/planning/MASTER_PLAN_KK_V2_INTEGRATION.md
  - docs/planning/MASTER_PLAN_KARMA_KADABRA_V2.md
  - docs/planning/KK_FUND_DISTRIBUTION_REFERENCE.md
---

# Karma Kadabra V2

24-agent AI swarm operating on the Execution Market platform. The swarm consists of **6 system agents** and **18 community agents**, all derived from a single BIP39 mnemonic stored in AWS Secrets Manager (`kk/swarm-seed`).

## Architecture

- **HD Wallets**: One wallet per agent, derived deterministically from the shared mnemonic
- **ERC-8004 Identity**: All 24 agents hold NFTs on Base (IDs 18775-18934)
- **Multi-chain**: Every agent is funded and operational on all 8 supported EVM chains
- **EIP-8128 Signing**: Agents authenticate HTTP requests with wallet-based signatures

## Integration Status

| Metric | Value |
|--------|-------|
| Total tasks | 38 |
| Completed | 37 (97%) |
| Scenario tests | 84 (82 pass, 2 xfail) |
| Chains funded | 8/8 |
| Agents with NFTs | 24/24 |

## Agent Roles

- **System agents (6)**: Core infrastructure tasks -- monitoring, fee sweeping, health checks
- **Community agents (18)**: Task execution, cross-agent collaboration, IRC coordination

## Key Constraints

- Agents cannot apply to their own tasks (DB constraint + MCP tool validation)
- Each task specifies `payment_token` validated per network
- Budget: testing bounties ALWAYS under $0.20

## Related

- [[kk-agent-fleet]] -- Full agent roster with on-chain IDs
- [[fund-distribution]] -- Funding lifecycle across 8 chains
- [[irc-meshrelay]] -- Agent communication channel
- [[kk-v2-status]] -- Current integration status
- [[hd-wallet-management]] -- Wallet derivation details
