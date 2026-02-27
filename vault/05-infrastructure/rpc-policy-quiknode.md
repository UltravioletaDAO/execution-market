---
date: 2026-02-26
tags:
  - domain/infrastructure
  - rpc
  - blockchain
  - policy
status: active
aliases:
  - RPC Policy
  - QuikNode
related-files:
  - .env.local
  - scripts/chains.ts
  - mcp_server/integrations/x402/sdk_client.py
---

# RPC Policy - QuikNode

**ALWAYS prefer QuikNode private RPCs** from `.env.local` over public endpoints.

## QuikNode Coverage (6 chains)

| Chain | Env Var | Status |
|-------|---------|--------|
| Base | `BASE_RPC_URL` | QuikNode |
| Ethereum | `ETHEREUM_RPC_URL` | QuikNode |
| Polygon | `POLYGON_RPC_URL` | QuikNode |
| Arbitrum | `ARBITRUM_RPC_URL` | QuikNode |
| Avalanche | `AVALANCHE_RPC_URL` | QuikNode |
| Optimism | `OPTIMISM_RPC_URL` | QuikNode |

## Non-QuikNode Chains

| Chain | RPC | Notes |
|-------|-----|-------|
| Celo | `rpc.celocolombia.org` | Custom community RPC |
| Monad | Public RPC | No private option yet |

## Code Pattern

Scripts must use the fallback pattern:

```typescript
const rpcUrl = process.env.ETHEREUM_RPC_URL || "https://eth.llamarpc.com";
```

**NEVER hardcode public RPCs** when a QuikNode env var exists.

## Known Exception

**Ethereum L1 large transactions** (>500k gas): QuikNode drops them from mempool. Use LlamaRPC as fallback for these specific cases only.

## Where RPCs Are Configured

- `scripts/chains.ts` -- auto-loads `.env.local`, prefers env vars via `rpc()` helper
- `mcp_server/integrations/x402/sdk_client.py` -- `NETWORK_CONFIG` dict
- [[aws-secrets-manager]] -- `em/x402:X402_RPC_URL` (Base QuikNode for production)

## Related

- [[supported-networks]] -- all 15 supported chains
- [[aws-secrets-manager]] -- production RPC URLs stored here
