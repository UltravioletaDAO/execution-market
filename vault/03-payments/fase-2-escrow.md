---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - Fase 2
  - on-chain escrow mode
  - platform_release
related-files:
  - mcp_server/integrations/x402/advanced_escrow_integration.py
  - mcp_server/integrations/x402/sdk_client.py
---

# Fase 2 — On-Chain Escrow

**Fase 2** (`EM_PAYMENT_MODE=fase2`) locks funds in [[x402r-escrow]] at task creation and releases them via the [[facilitator]] at approval. It provides stronger guarantees than [[fase-1-direct-settlement]] by ensuring funds exist before work begins.

## Flow

### Task Creation
- Lock bounty + fee in [[x402r-escrow]] via [[eip-3009]]
- Receiver = platform wallet (`0xD386`)
- Escrow creates a TokenStore clone (EIP-1167) to isolate funds

### Task Approval
- [[facilitator]] releases funds from escrow to platform wallet
- Platform wallet disburses: worker (87%) + [[treasury]] (13%) via [[eip-3009]]
- 3 transactions total (release + 2 disbursements)

### Task Cancellation
- Refund from escrow directly to agent
- Single transaction via [[facilitator]]

## Configuration

```bash
EM_PAYMENT_MODE=fase2
EM_PAYMENT_OPERATOR=0x...  # Required — operator address for the target chain
```

## Key Properties

- **Funds locked at creation** — worker guaranteed payment exists
- **Platform wallet intermediary** — funds pass through `0xD386` before reaching worker
- **3 transactions at approval** — more gas than Fase 1 or Fase 5
- **Requires EM_PAYMENT_OPERATOR** env var

## Comparison with Fase 5

Fase 2 uses `platform_release` mode where the platform wallet receives and redistributes. [[fase-5-trustless]] eliminates this intermediary with `direct_release` mode.

## Related Concepts

- [[x402r-escrow]] — Layer 1 contract holding the funds
- [[payment-operator]] — Layer 2 contract defining release conditions
- [[facilitator]] — submits release/refund transactions
- [[fase-5-trustless]] — the evolved version without platform intermediary
- [[payment-dispatcher]] — routes to Fase 2 when configured
