---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - EM PaymentOperator
  - Fase 5 operator
related-files:
  - scripts/deploy-payment-operator.ts
  - mcp_server/integrations/x402/sdk_client.py
---

# Payment Operator

The **PaymentOperator** is a Layer 2 contract in the x402r architecture. It sits between the [[x402r-escrow]] (Layer 1) and the [[facilitator]] (Layer 3), defining **pluggable conditions** for who can authorize, release, and refund escrowed funds.

## Fase 5 Deployment (8 Chains)

| Network | Address |
|---------|---------|
| Base | `0x271f9fa7f8907aCf178CCFB470076D9129D8F0Eb` |
| Ethereum | `0x69B67962ffb7c5C7078ff348a87DF604dfA8001b` |
| Polygon | `0xB87F1ECC85f074e50df3DD16A1F40e4e1EC4102e` |
| Arbitrum | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Avalanche | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Celo | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |
| Monad | `0x9620Dbe2BB549E1d080Dc8e7982623A9e1Df8cC3` |
| Optimism | `0xC2377a9Db1de2520BD6b2756eD012f4E82F7938e` |

Arbitrum, Avalanche, Celo, and Optimism share the same address via CREATE2 deterministic deployment.

## Fee Calculator

Each operator is configured with a **[[static-fee-calculator]]** (1300 BPS = 13%). At release, the calculator atomically splits the payment:

- **87%** to worker (net bounty)
- **13%** held by operator (platform fee)

`distributeFees(USDC)` flushes accumulated fees to [[treasury]].

## Deploy Script

```bash
cd scripts && npx tsx deploy-payment-operator.ts
```

Requires `WALLET_PRIVATE_KEY` and network RPC URLs in `.env.local`.

## Related Concepts

- [[x402r-escrow]] — Layer 1, holds the actual funds
- [[fee-structure]] — how the 87/13 split works
- [[static-fee-calculator]] — the on-chain fee calculator contract
- [[fase-5-trustless]] — the payment mode that uses these operators
- [[facilitator]] — Layer 3, submits transactions to the operator
