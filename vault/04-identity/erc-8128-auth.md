---
date: 2026-02-26
tags:
  - type/concept
  - domain/identity
status: active
aliases:
  - ERC-8128
  - EIP-8128
related-files:
  - mcp_server/api/agent_auth.py
  - mcp_server/api/h2a.py
  - dashboard/src/context/AuthContext.tsx
---

# ERC-8128 Authentication

Wallet-based HTTP authentication protocol that replaces traditional API keys with cryptographic signatures. An agent proves its identity by signing requests with the private key associated with its [[erc-8004]] NFT.

## How It Works

1. Client constructs the HTTP request (method, path, body, timestamp)
2. Client signs a canonical representation of the request with its wallet key
3. Signature is included in the `Authorization` header as a bearer token
4. Server verifies the signature against the [[erc-8004]] registry to confirm identity
5. If valid, the request is authenticated as the agent owning that wallet

## Advantages Over API Keys

| Feature | API Keys | ERC-8128 |
|---------|----------|----------|
| Rotation | Manual, error-prone | Automatic (wallet-based) |
| Revocation | Centralized database | On-chain ownership transfer |
| Cross-platform | Per-service | Universal (any ERC-8004 network) |
| Replay protection | None (unless custom) | Timestamp + nonce built-in |

## Implementation

Both **TypeScript** and **Python** signing libraries are implemented:

- **Server verification**: `mcp_server/api/agent_auth.py`
- **TS client signing**: `@slicekit/erc8128` library
- **Python client signing**: Built into the MCP server for agent-to-agent calls

## Integration Points

- **H2A (Human-to-Agent)**: Human publishers authenticate via Supabase JWT; agents authenticate via ERC-8128
- **A2A (Agent-to-Agent)**: Agents authenticate to each other using ERC-8128 signatures
- **KK V2**: All 24 Karma Kadabra agents use ERC-8128 for task operations

## Related

- [[erc-8004]] — The identity registry that anchors authentication
- [[authentication]] — Broader auth architecture (Supabase JWT + ERC-8128)
- [[karma-kadabra-v2]] — Swarm agents using ERC-8128 auth
- [[agent-2106]] — The agent identity being authenticated
