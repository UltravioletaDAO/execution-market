---
date: 2026-02-26
tags:
  - domain/agents
  - project/karma-kadabra
  - payments/funding
status: active
aliases:
  - Fund Distribution
  - KK Funding
related-files:
  - docs/planning/KK_FUND_DISTRIBUTION_REFERENCE.md
  - .claude/skills/fund-distribution/SKILL.md
  - scripts/kk/
---

# Fund Distribution

Complex multi-step lifecycle for distributing funds to all 24 Karma Kadabra V2 agent wallets across 8 EVM chains. Total budget: $200 USDC bridged from Avalanche.

## Lifecycle Stages

```
Inventory -> Bridge -> Fan-out -> Gas Distribution -> Rebalance -> Sweep
```

### 1. Inventory

Check balances across all 24 wallets on all 8 chains. Identify which wallets need USDC and which need native gas tokens.

### 2. Bridge

Transfer USDC from source chain to target chains via cross-chain bridges. The $200 USDC was initially bridged from Avalanche to distribute across all networks.

### 3. Fan-out

From a funded master wallet, send USDC to each of the 24 agent wallets on the target chain. Each agent receives enough for testing bounties (~$5 per chain).

### 4. Gas Distribution

Distribute native tokens (ETH, POL, AVAX, MON, CELO) so agents can pay transaction fees on chains without gasless support.

### 5. Rebalance

Move surplus funds between chains or wallets to maintain minimum operating balances.

### 6. Sweep

Collect unused funds back to the master wallet for redeployment or bridging.

## Budget Constraints

| Item | Amount |
|------|--------|
| Total bridged | $200 USDC |
| Per chain target | ~$5 USDC |
| Test bounty max | $0.20 |
| E2E test bounty | $0.10 |

## Skill

The **`fund-distribution` skill** (`.claude/skills/fund-distribution/SKILL.md`) automates the full lifecycle. Reference doc: `docs/planning/KK_FUND_DISTRIBUTION_REFERENCE.md`.

## RPC Policy

Always prefer QuikNode private RPCs from `.env.local`. Public RPCs are fallback only.

## Related

- [[hd-wallet-management]] -- Wallet derivation and storage
- [[supported-networks]] -- Chain details and RPC endpoints
- [[karma-kadabra-v2]] -- Swarm overview
- [[bounty-guidelines]] -- Testing budget rules
