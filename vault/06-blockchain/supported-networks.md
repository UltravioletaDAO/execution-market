---
date: 2026-02-26
tags:
  - domain/blockchain
  - concept/networks
  - reference
status: active
aliases:
  - Networks
  - Supported Chains
  - EVM Networks
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - scripts/chains.ts
---

# Supported Networks

Execution Market operates across **8 production mainnets** and
**1 testnet**, all EVM-compatible.

## Production Mainnets

| Network | Chain ID | RPC Source | Escrow Status |
|---------|----------|------------|---------------|
| **Base** | 8453 | QuikNode (private) | Active (Fase 5) |
| **Ethereum** | 1 | QuikNode (private) | Active (Fase 5) |
| **Polygon** | 137 | QuikNode (private) | Active (Fase 5) |
| **Arbitrum** | 42161 | QuikNode (private) | Active (Fase 5) |
| **Avalanche** | 43114 | QuikNode (private) | Active (Fase 5) |
| **Optimism** | 10 | QuikNode (private) | Active (Fase 5) |
| **Celo** | 42220 | rpc.celocolombia.org | Active (Fase 5) |
| **Monad** | 10143 | Public RPC | Active (Fase 5) |

## Testnets

| Network | Chain ID | Purpose |
|---------|----------|---------|
| **Sepolia** | 11155111 | Legacy testing (Agent #469) |

## RPC Policy

- **Always prefer QuikNode private RPCs** from `.env.local`
- 6 chains have QuikNode: Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism
- Celo uses custom RPC (`rpc.celocolombia.org`)
- Monad uses public RPC only
- Public RPCs are fallback only
- Exception: Ethereum L1 large TXs (>500k gas) -- QuikNode drops them, use LlamaRPC

## Network Configuration

Single source of truth: `NETWORK_CONFIG` dict in
`mcp_server/integrations/x402/sdk_client.py`. All other Python files
auto-derive from it.

TypeScript scripts: `scripts/chains.ts` with `rpc()` helper that
prefers env vars over hardcoded fallbacks.

## Related

- [[contract-addresses]] -- deployed contracts per network
- [[rpc-policy-quiknode]] -- detailed RPC selection policy
