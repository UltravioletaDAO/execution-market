---
date: 2026-02-26
tags:
  - domain/blockchain
  - concept/escrow
  - contract/auth-capture-escrow
status: active
aliases:
  - AuthCaptureEscrow
  - Escrow Singleton
  - Layer 1 Escrow
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - docs/planning/X402R_REFERENCE.md
---

# AuthCaptureEscrow

**Layer 1** of the x402r escrow architecture. A shared singleton contract
per chain that holds funds in isolated TokenStore clones.

## Architecture Role

```
Layer 1: AuthCaptureEscrow (this contract)
    -- Holds funds in TokenStore clones (EIP-1167 minimal proxies)
    -- One singleton per chain, shared by all PaymentOperators

Layer 2: PaymentOperator
    -- Per-configuration contract with pluggable conditions
    -- Controls who can authorize, release, refund

Layer 3: Facilitator (off-chain)
    -- Pays gas, enforces business logic
    -- Calls escrow/operator methods on behalf of users
```

## How It Works

1. **Authorize**: Agent signs EIP-3009 auth, Facilitator calls
   `authorize()` on the escrow. Funds transfer from agent to a
   TokenStore clone (EIP-1167 minimal proxy).
2. **Release**: PaymentOperator calls `release()` through the escrow.
   Funds transfer from TokenStore to the designated receiver.
3. **Refund**: PaymentOperator calls `refund()` through the escrow.
   Funds return from TokenStore to the original depositor.

## TokenStore Clones (EIP-1167)

Each escrow operation creates an isolated TokenStore using EIP-1167
minimal proxy pattern. This ensures:
- Funds from different operations never co-mingle
- Each clone is a lightweight proxy (~45 bytes of bytecode)
- Clone address is deterministic (can be computed off-chain)

## Deployed Addresses

| Chain(s) | Address |
|----------|---------|
| Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| Ethereum | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` |
| Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| Arbitrum, Avalanche, Celo, Monad, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |

## Related

- [[x402r-escrow]] -- full escrow system overview
- [[payment-operator]] -- Layer 2 that controls this escrow
