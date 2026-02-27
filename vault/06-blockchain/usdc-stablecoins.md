---
date: 2026-02-26
tags:
  - domain/blockchain
  - concept/tokens
  - concept/stablecoins
status: active
aliases:
  - USDC
  - Stablecoins
  - Payment Tokens
related-files:
  - mcp_server/integrations/x402/sdk_client.py
---

# USDC and Stablecoins

Execution Market supports **5 stablecoins** for task payments, with
**USDC as the primary and recommended token**.

## Supported Tokens

| Token | Standard | Primary Use |
|-------|----------|-------------|
| **USDC** | ERC-20 + EIP-3009 | Default payment token (all chains) |
| **USDT** | ERC-20 | Alternative (select chains) |
| **EURC** | ERC-20 + EIP-3009 | Euro-denominated payments |
| **AUSD** | ERC-20 | Agora dollar (select chains) |
| **PYUSD** | ERC-20 | PayPal USD (select chains) |

## USDC Addresses by Chain

All addresses sourced from `NETWORK_CONFIG` in `sdk_client.py`:

| Chain | USDC Address |
|-------|-------------|
| Base | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| Ethereum | `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` |
| Polygon | `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` |
| Arbitrum | `0xaf88d065e77c8cC2239327C5EDb3A432268e5831` |
| Avalanche | `0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E` |
| Optimism | `0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85` |
| Celo | `0xcebA9300f2b948710d2653dD7B07f33A8B32118C` |

## Why USDC

- **EIP-3009** support enables gasless transfers (transferWithAuthorization)
- Universal acceptance across all 8 production chains
- Native Circle-issued (not bridged) on most chains
- 6-decimal precision (standard for USDC)

## Token Registry

Single source of truth: `NETWORK_CONFIG` dictionary in
`mcp_server/integrations/x402/sdk_client.py`. Contains token addresses,
decimals, and EIP-3009 support flags for all 15 networks and 5 tokens.

Other Python files (facilitator_client, tests, platform_config)
**auto-derive** from sdk_client.py -- no manual updates needed.

## Per-Task Token Selection

Migration 038 added `payment_token` field to tasks table. Each task can
specify which stablecoin to use, validated per-network at creation time.

## Related

- [[supported-networks]] -- chains where these tokens are deployed
- [[payment-token-selection]] -- per-task token configuration
