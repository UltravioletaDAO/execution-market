---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - uvd-x402-sdk
  - x402 SDK
related-files:
  - mcp_server/integrations/x402/sdk_client.py
  - mcp_server/requirements.txt
---

# x402 SDK

The **x402 SDK** (`uvd-x402-sdk`) is the Python and TypeScript client library for gasless payments via the [[facilitator]]. It wraps [[eip-3009]] authorization signing and communicates with the Facilitator's HTTP endpoints.

## Versions

| Language | Package | Min Version |
|----------|---------|-------------|
| Python | `uvd-x402-sdk[fastapi]` | `>=0.14.0` |
| TypeScript | `uvd-x402-sdk` | `@2.26.0` |

## Core Class

`EMX402SDK` in `sdk_client.py` is the single entry point for all payment operations. It contains:

- **`NETWORK_CONFIG`** dict — single source of truth for 15 EVM networks, 5 stablecoins, 10 with x402r escrow
- Balance checks (`balanceOf`)
- [[eip-3009]] authorization signing
- Settlement via [[facilitator]]

Other Python files (`facilitator_client.py`, tests, `platform_config.py`) **auto-derive** from `sdk_client.py` — no manual updates needed when adding networks.

## Usage Pattern

```
Agent signs EIP-3009 auth -> SDK -> Facilitator -> On-chain TX (Facilitator pays gas)
```

**NEVER call contracts directly.** If you're writing `contract.functions.` or `cast send` to a payment contract, you're doing it wrong. Always go through the SDK.

## Related Concepts

- [[facilitator]] — off-chain relay that executes the on-chain TX
- [[eip-3009]] — the authorization standard the SDK signs
- [[payment-operator]] — on-chain contract the Facilitator interacts with (Fase 5)
- [[payment-dispatcher]] — selects which payment mode to use
- [[supported-networks]] — 15 EVM networks configured in `NETWORK_CONFIG`
