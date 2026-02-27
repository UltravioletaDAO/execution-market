---
date: 2026-02-26
tags:
  - type/moc
  - domain/payments
status: active
aliases:
  - Payments MOC
  - Payment System
  - x402 Payments
---

# Payments — Map of Content

> Everything related to how money moves through Execution Market.
> Gasless EIP-3009 settlements via the x402 SDK and Ultravioleta Facilitator.

---

## Core Components

| Concept | Description |
|---------|-------------|
| [[x402-sdk]] | `uvd-x402-sdk` — Python/TS SDK wrapping the Facilitator. **Single entry point for all payments.** |
| [[x402r-escrow]] | `AuthCaptureEscrow` — shared singleton per chain, holds funds in TokenStore clones (EIP-1167) |
| [[facilitator]] | `facilitator.ultravioletadao.xyz` — off-chain server, pays gas, enforces business logic. **We own this.** |
| [[payment-operator]] | `PaymentOperator` — per-config contract with pluggable conditions. Fase 5 deployed on 8 chains. |
| [[payment-dispatcher]] | `PaymentDispatcher` — Python class that routes payment operations based on `EM_PAYMENT_MODE` |
| [[eip-3009]] | EIP-3009 `transferWithAuthorization` — gasless USDC transfers signed by the agent |

---

## Payment Flows

### [[fase-1-direct-settlement]] — Production Default
- `EM_PAYMENT_MODE=fase1`
- Advisory `balanceOf()` at task creation (no funds locked)
- At approval: 2 fresh EIP-3009 auths — agent to worker (bounty) + agent to treasury (13% fee)
- Cancel is a no-op (nothing was ever locked)

### [[fase-2-escrow]] — On-Chain Escrow (Legacy)
- `EM_PAYMENT_MODE=fase2`
- Lock bounty+fee in escrow at creation (receiver = platform wallet)
- Release via Facilitator, disburse to worker via EIP-3009
- Fee swept via `POST /admin/fees/sweep`

### [[fase-5-trustless]] — Credit Card Model (Trustless)
- `EM_ESCROW_MODE=direct_release`
- No lock at creation. Lock at assignment (worker known). Worker is direct receiver.
- 1 TX release: StaticFeeCalculator splits atomically — worker 87%, operator 13%
- `distributeFees()` flushes operator balance to treasury
- **Deployed on 8 chains**, Golden Flow 7/8 PASS consolidated

### [[preauth-legacy]] — Deprecated
- Auth at creation, settle at approval through platform wallet
- Superseded by Fase 1 and Fase 5

---

## Financial Model

| Concept | Description |
|---------|-------------|
| [[fee-structure]] | 13% platform fee (configurable via `EM_PLATFORM_FEE`), 6-decimal USDC precision, $0.01 minimum |
| [[platform-fee]] | Treasury receives 13% of gross bounty. Computed by `_compute_treasury_remainder()`. |
| [[protocol-fee]] | BackTrack's x402r protocol fee (up to 5% hard cap, 7-day timelock). Read dynamically from chain. |
| [[treasury]] | Cold wallet (Ledger) `0xae07...` — ONLY receives fee portion. Never a settlement target. |

---

## Wallets

See [[wallet-roles]] for the full breakdown:

| Wallet | Address | Role |
|--------|---------|------|
| Dev wallet | `0x857f...` | Local scripts and tests. Key in `.env.local`. |
| Platform wallet | `0xD386...` | ECS MCP server. Settlement transit point. Key in AWS SM `em/x402:PRIVATE_KEY`. |
| Treasury | `0xae07...` | Cold Ledger. Receives 13% fee only. |
| Test worker | `0x52E0...` | Golden Flow worker-side operations. Key in AWS SM `em/test-worker:private_key`. |
| Facilitator EOA | `0x1030...` | Pays gas for all on-chain TXs. All networks. |

---

## Operations

| Runbook | When to use |
|---------|-------------|
| [[runbook-manual-refund]] | `payment_events` shows `settle` without `disburse_worker` — funds stuck |
| [[runbook-fee-sweep]] | `POST /admin/fees/sweep` — flush accumulated fees from operator to treasury |
| [[runbook-escrow-debug]] | `em_check_escrow_state` MCP tool — inspect on-chain escrow state |

---

## Source Files

| File | Purpose |
|------|---------|
| `mcp_server/integrations/x402/sdk_client.py` | `EMX402SDK` — x402 SDK wrapper + multichain token registry (15 EVM, 5 stablecoins). **Single source of truth.** |
| `mcp_server/integrations/x402/client.py` | Direct HTTP facilitator client (fallback) |
| `mcp_server/payments/payment_dispatcher.py` | Routes operations by `EM_PAYMENT_MODE` (fase1, fase2, preauth, x402r) |
| `mcp_server/payments/payment_events.py` | Audit trail — logs to `payment_events` table (migration 027) |
| `mcp_server/payments/_helpers.py` | `_compute_treasury_remainder()`, fee calculations |
| `mcp_server/integrations/x402/advanced_escrow_integration.py` | Advanced escrow flows documentation |

---

## Documentation

| Doc | Location |
|-----|----------|
| [[PAYMENT_ARCHITECTURE]] | `docs/planning/PAYMENT_ARCHITECTURE.md` |
| [[X402R_REFERENCE]] | `docs/planning/X402R_REFERENCE.md` — ABIs, all contract addresses, condition system |
| [[FASE1_E2E_EVIDENCE]] | `docs/planning/FASE1_E2E_EVIDENCE_2026-02-11.md` |
| [[GOLDEN_FLOW_REPORT]] | `docs/reports/GOLDEN_FLOW_REPORT.md` — payment verification included |

---

## Architecture Decision Records

| ADR | Decision |
|-----|----------|
| [[ADR-001-sdk-over-contracts]] | Always use SDK + Facilitator. Never call contracts directly. |
| [[ADR-002-fase5-trustless-fee-split]] | Fase 5 credit card model with StaticFeeCalculator on-chain split. |
| [[ADR-006-gasless-payments]] | EIP-3009 gasless flow — Facilitator pays all gas. |

---

## Cross-Links

- [[moc-blockchain]] — Contract addresses for escrow, operators, fee calculators across 8 chains
- [[moc-identity]] — Reputation scoring triggers after successful payment settlement
- [[moc-testing]] — Golden Flow E2E validates the full payment lifecycle
- [[moc-infrastructure]] — AWS secrets for wallet keys, ECS env vars for payment mode
- [[moc-security]] — Fund safety, escrow invariants, refund procedures
