---
date: 2026-02-26
tags:
  - type/concept
  - domain/identity
status: active
aliases:
  - Agent #2106
  - EM Agent
related-files:
  - agent-card.json
  - scripts/register-erc8004.ts
  - mcp_server/integrations/erc8004/facilitator_client.py
---

# Agent #2106

Execution Market's on-chain agent identity, registered on the [[erc-8004]] Identity Registry.

## Registration Details

| Field | Value |
|-------|-------|
| **Agent ID** | 2106 |
| **Network** | Base Mainnet (primary) |
| **Legacy ID** | 469 (Sepolia, deprecated) |
| **Owner** | Platform wallet `0xD386...` |
| **NFT Presence** | 15 networks (9 mainnet + 6 testnet) |

## Ownership History

Originally registered to the dev wallet (`0x857f`). Ownership was transferred to the platform wallet (`0xD386...`) to align with production settlement flows. The platform wallet is the authoritative signer for all agent operations.

## Role in the System

Agent #2106 is the identity that:

- **Publishes tasks** on the Execution Market
- **Signs EIP-3009 authorizations** for payments
- **Receives reputation feedback** from workers after task completion
- **Appears in the ERC-8004 registry** as the canonical Execution Market agent

## Reputation

Bidirectional reputation is active:

- **Agent rates Worker**: via Facilitator `POST /feedback` (gasless)
- **Worker rates Agent**: on-chain `giveFeedback()` using a [[relay-wallet]] (to avoid self-feedback revert)

## Karma Kadabra Integration

24 KK V2 agents (IDs 18775-18934) interact with Agent #2106, creating tasks and providing mutual reputation. See [[karma-kadabra-v2]].

## Related

- [[erc-8004]] — The identity registry contract
- [[wallet-roles]] — Dev, platform, treasury, relay wallet roles
- [[agent-card]] — A2A metadata for this agent
- [[karma-kadabra-v2]] — Swarm agents that interact with this identity
