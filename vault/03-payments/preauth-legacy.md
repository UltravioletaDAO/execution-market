---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: deprecated
aliases:
  - preauth
  - pre-authorization mode
related-files:
  - mcp_server/integrations/x402/payment_dispatcher.py
---

# Preauth (Legacy) — DEPRECATED

> **STATUS: DEPRECATED.** Do not use for new deployments. Replaced by [[fase-1-direct-settlement]] (default) and [[fase-5-trustless]] (trustless).

**Preauth** (`EM_PAYMENT_MODE=preauth`) was the original payment mode where an [[eip-3009]] authorization was signed at task creation and settled at approval through the platform wallet.

## Flow (Historical)

### Task Creation
- Agent signs [[eip-3009]] authorization
- Auth stored in database (not submitted on-chain yet)

### Task Approval
- Stored auth submitted to [[facilitator]] for settlement
- Funds land in platform wallet (`0xD386`)
- Platform wallet disburses to worker and [[treasury]]

### Task Cancellation
- Stored auth discarded (never submitted on-chain)

## Why Deprecated

1. **Single point of failure** — platform wallet is intermediary for all funds
2. **Auth expiry risk** — stored auths could expire before approval
3. **No on-chain guarantee** — worker has no proof funds are locked
4. **Superseded** — Fase 1 is simpler (no stored auth), Fase 5 is trustless

## Migration Path

- For simplicity: use [[fase-1-direct-settlement]] (`EM_PAYMENT_MODE=fase1`)
- For trust guarantees: use [[fase-5-trustless]] (`EM_ESCROW_MODE=direct_release`)

## Related Concepts

- [[payment-dispatcher]] — still recognizes `preauth` for backward compatibility
- [[fase-1-direct-settlement]] — the recommended replacement
- [[fase-5-trustless]] — the trustless alternative
