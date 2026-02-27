---
date: 2026-02-26
tags:
  - type/concept
  - domain/payments
status: active
aliases:
  - PaymentDispatcher
  - payment mode router
related-files:
  - mcp_server/integrations/x402/payment_dispatcher.py
---

# Payment Dispatcher

The **PaymentDispatcher** is the smart router that selects the correct payment flow based on the `EM_PAYMENT_MODE` environment variable. It abstracts all payment complexity behind a unified interface.

## Payment Modes

| Mode | Env Value | Status | Description |
|------|-----------|--------|-------------|
| [[fase-1-direct-settlement]] | `fase1` | **Default, Production** | No auth at creation, direct settlement at approval |
| [[fase-2-escrow]] | `fase2` | Active | On-chain escrow lock at creation |
| [[fase-5-trustless]] | `fase5` | Active | Credit card model, escrow at assignment |
| [[preauth-legacy]] | `preauth` | Deprecated | Auth at creation, settle through platform wallet |
| x402r | `x402r` | **DEPRECATED** | Caused fund loss bug, do not use |

## Configuration

```bash
# In .env or ECS task definition
EM_PAYMENT_MODE=fase1        # Default
EM_ESCROW_MODE=direct_release  # For Fase 5 trustless release
```

## Interface

The dispatcher exposes a consistent API regardless of mode:

1. **Balance check** (task creation) — advisory, never blocks
2. **Lock/Auth** (creation or assignment, depending on mode)
3. **Release** (task approval) — pays worker + fee
4. **Refund** (task cancellation) — returns funds to agent

## Source

`payment_dispatcher.py` reads `EM_PAYMENT_MODE` at startup and instantiates the appropriate handler. All payment events are logged to the `payment_events` table (migration 027).

## Related Concepts

- [[fase-1-direct-settlement]] — default production mode
- [[fase-2-escrow]] — on-chain escrow mode
- [[fase-5-trustless]] — trustless credit card model
- [[preauth-legacy]] — deprecated preauth mode
- [[x402-sdk]] — underlying SDK used by all modes
