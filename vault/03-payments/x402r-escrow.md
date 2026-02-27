---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - x402r
  - escrow protocol
  - AuthCaptureEscrow
related-files:
  - contracts/
  - docs/planning/X402R_REFERENCE.md
---

# x402r Escrow

The **x402r Escrow** (`AuthCaptureEscrow`) is the Layer 1 contract in the x402r payment architecture. It is a **shared singleton per chain** that holds funds in isolated TokenStore clones created via EIP-1167 minimal proxies.

## Architecture

The x402r system has 3 layers:

1. **Layer 1: AuthCaptureEscrow** (this note) — holds funds in TokenStore clones
2. **Layer 2: [[payment-operator]]** — per-config contract with pluggable conditions
3. **Layer 3: [[facilitator]]** — off-chain server, pays gas, enforces business logic

## Deployed Addresses

| Network | Address |
|---------|---------|
| Base | `0xb9488351E48b23D798f24e8174514F28B741Eb4f` |
| Ethereum | `0x9D4146EF898c8E60B3e865AE254ef438E7cEd2A0` |
| Polygon | `0x32d6AC59BCe8DFB3026F10BcaDB8D00AB218f5b6` |
| Arbitrum, Avalanche, Celo, Monad, Optimism | `0x320a3c35F131E5D2Fb36af56345726B298936037` |

## How It Works

1. Agent authorizes a payment via [[eip-3009]]
2. [[facilitator]] submits the auth to AuthCaptureEscrow
3. Escrow creates a TokenStore clone (EIP-1167) to isolate the funds
4. On release, the [[payment-operator]] directs where funds go
5. On refund, funds return to the original agent

## Key Properties

- **Singleton per chain** — one contract, many TokenStore clones
- **EIP-1167 minimal proxies** — gas-efficient storage isolation
- **Condition system** — [[payment-operator]] defines who can authorize/release/refund

## Related Concepts

- [[payment-operator]] — Layer 2, controls release/refund conditions
- [[facilitator]] — Layer 3, pays gas and enforces business logic
- [[supported-networks]] — chains where escrow is deployed
- [[fase-2-escrow]] — payment mode that uses this escrow
- [[fase-5-trustless]] — credit card model using this escrow
