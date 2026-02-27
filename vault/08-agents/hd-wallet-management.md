---
date: 2026-02-26
tags:
  - domain/agents
  - security/keys
  - infrastructure/aws
status: active
aliases:
  - HD Wallets
  - BIP39 Wallets
related-files:
  - scripts/kk/generate-wallets.ts
  - docs/planning/KK_FUND_DISTRIBUTION_REFERENCE.md
---

# HD Wallet Management

Hierarchical Deterministic (BIP39) wallet system for the Karma Kadabra V2 agent swarm. A single mnemonic derives all 24 agent wallets deterministically.

## Mnemonic Storage

- **Location**: AWS Secrets Manager, secret ID `kk/swarm-seed`
- **Format**: Standard BIP39 mnemonic phrase
- **Access**: Never logged, never displayed in terminal (streaming policy)
- **Retrieval**: `aws secretsmanager get-secret-value --secret-id kk/swarm-seed`

## Derivation

Each agent gets a unique wallet derived from the mnemonic at a sequential index:

```
m/44'/60'/0'/0/0  -> Agent 0 (system)
m/44'/60'/0'/0/1  -> Agent 1 (system)
...
m/44'/60'/0'/0/23 -> Agent 23 (community)
```

**Script**: `scripts/kk/generate-wallets.ts`

## Multi-Chain Operation

Each derived wallet address is valid on all EVM chains. The same private key controls funds on:

| Chain | Native Token | Status |
|-------|-------------|--------|
| Base | ETH | Funded |
| Ethereum | ETH | Funded |
| Polygon | POL | Funded |
| Arbitrum | ETH | Funded |
| Avalanche | AVAX | Funded |
| Monad | MON | Funded |
| Celo | CELO | Funded |
| Optimism | ETH | Funded |

## Security Rules

1. Never show private keys in logs or terminal output
2. Always read keys from AWS SM at runtime
3. Scripts print public addresses only
4. Use `${VAR:+set}` pattern to verify key existence without exposing value

## Related

- [[karma-kadabra-v2]] -- Swarm overview
- [[aws-secrets-manager]] -- Secret storage infrastructure
- [[fund-distribution]] -- How wallets get funded
- [[supported-networks]] -- Chain details
