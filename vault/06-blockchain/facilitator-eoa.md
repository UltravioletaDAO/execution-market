---
date: 2026-02-26
tags:
  - domain/blockchain
  - concept/facilitator
  - concept/gasless
status: active
aliases:
  - Facilitator EOA
  - Gas Sponsor
  - Gasless Relay
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - mcp_server/integrations/x402/client.py
---

# Facilitator EOA

The Facilitator EOA is the externally-owned account that pays gas for
all on-chain transactions in the Execution Market ecosystem.

## Address

`0x103040545AC5031A11E8C03dd11324C7333a13C7`

Active on all 8 production mainnets + testnets.

## Role

The Facilitator EOA is the on-chain identity of the **Ultravioleta
Facilitator** (`facilitator.ultravioletadao.xyz`). It:

1. **Pays gas** for all escrow operations (authorize, release, refund)
2. **Pays gas** for ERC-8004 identity registration and reputation
3. **Executes** EIP-3009 `transferWithAuthorization` calls
4. **Submits** `giveFeedback` calls to reputation registry

## Gasless Model

Users (agents and workers) never pay gas directly:

```
Agent signs EIP-3009 authorization (off-chain, free)
    -> SDK sends to Facilitator API
    -> Facilitator submits TX using EOA (pays gas)
    -> On-chain operation executes
    -> Agent/worker wallet state changes
```

This enables:
- Agents to operate without native tokens (ETH, MATIC, etc.)
- Workers to receive payments without gas costs
- Cross-chain operations from a single signing key

## Funding

The Facilitator EOA must maintain native token balances on each chain
for gas. Funded by Ultravioleta DAO treasury operations.

## Ownership

The Facilitator (`facilitator.ultravioletadao.xyz`) is owned and
operated by **Ultravioleta DAO**. Repo: `UltravioletaDAO/x402-rs`.
BackTrack/Ali controls the x402r protocol contracts only, NOT the
Facilitator.

## Related

- [[facilitator]] -- the off-chain server that uses this EOA
- [[wallet-roles]] -- all wallet roles in the system
