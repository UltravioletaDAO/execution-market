---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - gas relay
  - Ultravioleta Facilitator
related-files:
  - mcp_server/integrations/x402/client.py
  - mcp_server/integrations/erc8004/facilitator_client.py
---

# Facilitator

The **Facilitator** (`facilitator.ultravioletadao.xyz`) is Ultravioleta DAO's off-chain gas relay server. It receives signed [[eip-3009]] authorizations and submits the on-chain transactions, paying gas so agents and workers never need native tokens.

> **CRITICAL OWNERSHIP**: The Facilitator is **OURS** — Ultravioleta DAO. Repo: `UltravioletaDAO/x402-rs`. We deploy, control, and maintain it. Ali/BackTrack controls x402r protocol (contracts, ProtocolFeeConfig) ONLY, **NOT** the Facilitator. See [[x402r-team-relationship]].

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/verify` | Verify an [[eip-3009]] authorization |
| POST | `/settle` | Execute settlement on-chain |
| POST | `/register` | ERC-8004 identity registration (gasless) |
| POST | `/feedback` | ERC-8004 reputation feedback (gasless) |

## How It Works

```
Agent signs EIP-3009 -> x402 SDK -> Facilitator -> On-chain TX
                                         |
                                    Pays gas (ETH)
```

The Facilitator EOA (`0x103040545AC5031A11E8C03dd11324C7333a13C7`) holds native tokens on all supported networks for gas.

## Allowlist

The Facilitator maintains an allowlist of [[payment-operator]] addresses it will interact with. When deploying new operators, update `addresses.rs` in the `x402-rs` repo.

## Responsibilities

- Gas payment for all [[eip-3009]] settlements
- ERC-8004 registration and reputation transactions
- Operator allowlist management
- Transaction monitoring and retry logic

## Related Concepts

- [[x402-sdk]] — client library that communicates with the Facilitator
- [[eip-3009]] — the auth standard the Facilitator executes
- [[x402r-team-relationship]] — ownership boundaries with BackTrack
- [[wallet-roles]] — Facilitator EOA is one of the 5 key wallets
