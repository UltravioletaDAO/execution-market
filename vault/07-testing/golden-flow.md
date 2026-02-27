---
date: 2026-02-26
tags:
  - domain/testing
  - e2e
  - acceptance
status: active
aliases:
  - Golden Flow
  - E2E Acceptance Test
related-files:
  - scripts/e2e_golden_flow.py
  - docs/reports/GOLDEN_FLOW_REPORT.md
  - docs/reports/GOLDEN_FLOW_REPORT.es.md
---

# Golden Flow

The **definitive end-to-end acceptance test** for Execution Market. If it passes, the platform is healthy.

## Script

```bash
python scripts/e2e_golden_flow.py
```

## 10 Stages

| # | Stage | What it tests |
|---|-------|---------------|
| 1 | Health check | API and MCP server responding |
| 2 | Task creation | Balance check + task publish (escrow lock if Fase 5) |
| 3 | Worker registration | Executor profile creation |
| 4 | ERC-8004 identity | Agent NFT verification on Base |
| 5 | Application | Worker applies to task |
| 6 | Assignment | Task assigned to worker (escrow locks here in direct_release mode) |
| 7 | Evidence submission | S3/CloudFront upload + submission record |
| 8 | Approval + payment | Release escrow, USDC settlement |
| 9 | Bidirectional reputation | Agent rates worker + worker rates agent |
| 10 | On-chain verification | TX hashes verified on-chain |

## Escrow Modes

- **`direct_release`** (Fase 5): Escrow locks at assignment (not creation). Approval = 1 TX.
- **`platform_release`** (legacy): Escrow locks at creation. Approval = 3 TXs.

## Reports

- `docs/reports/GOLDEN_FLOW_REPORT.md` (English)
- `docs/reports/GOLDEN_FLOW_REPORT.es.md` (Spanish)
- `docs/reports/PAYMENT_FLOW_REPORT.md`
- `docs/reports/ERC8004_FLOW_REPORT.md`

## Rule

If Golden Flow fails, the platform has a regression. Do not deploy.

## Related

- [[multichain-golden-flow]] -- same test across 8 chains
- [[test-profiles-markers]] -- unit test coverage
- [[test-budget]] -- bounty limits for test tasks
