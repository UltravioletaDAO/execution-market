---
date: 2026-02-26
tags:
  - domain/testing
  - e2e
  - multichain
status: active
aliases:
  - Multichain Golden Flow
  - Multichain E2E
related-files:
  - scripts/e2e_golden_flow_multichain.py
---

# Multichain Golden Flow

Runs the [[golden-flow]] across all 8 supported EVM chains in a single consolidated test run.

## Script

```bash
python scripts/e2e_golden_flow_multichain.py
```

## Chain Results (2026-02-21)

| Chain | Status | Notes |
|-------|--------|-------|
| Base | PASS | Primary chain, fastest |
| Polygon | PASS | Reliable |
| Arbitrum | PASS | Reliable |
| Avalanche | PASS | Reliable |
| Monad | PASS | Public RPC only |
| Celo | PASS | Community RPC |
| Optimism | PASS | Reliable |
| Ethereum L1 | TIMEOUT (batch) | Passes solo (~130s), times out in batch (>900s) |

**7/8 PASS consolidated.** All 8 PASS individually.

## Verification

- **16 on-chain TXs verified** across all chains
- Bidirectional reputation PASS on all chains
- Agent->Worker: via Facilitator `/feedback`
- Worker->Agent: on-chain `giveFeedback()` on Base

## Known Issues

- **Ethereum L1 timeout**: Not a code bug. Facilitator TX propagation slow on L1. Solo run passes.
- **Intermittent TxWatcher timeouts**: Affect ANY chain randomly. Every chain has passed at least once.

## Timeout Fixes (3-layer)

| Layer | Timeout | Purpose |
|-------|---------|---------|
| Dockerfile SDK patch | 900s | SDK-level escrow wait |
| PaymentDispatcher | 900s | Server-side settlement wait |
| ALB | 960s | Load balancer connection timeout |

## Required Secrets

- `EM_WORKER_PRIVATE_KEY` from [[aws-secrets-manager]] (`em/test-worker:private_key`)
- Platform wallet from `em/x402:PRIVATE_KEY`

## Related

- [[golden-flow]] -- single-chain version
- [[supported-networks]] -- all 15 networks (9 mainnet + 6 testnet)
- [[test-budget]] -- per-chain budget limits
