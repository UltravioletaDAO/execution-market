---
date: 2026-02-26
tags:
  - domain/testing
  - budget
  - usdc
  - policy
status: active
aliases:
  - Test Budget
  - Testing Budget
related-files:
  - scripts/task-factory.ts
  - scripts/e2e_golden_flow.py
  - scripts/e2e_golden_flow_multichain.py
---

# Test Budget

Strict USDC budget constraints for all test task creation across Execution Market.

## Rules

| Constraint | Value |
|------------|-------|
| Max bounty per test task | **< $0.20 USDC** |
| Standard E2E bounty | `TEST_BOUNTY = 0.10` USDC |
| Budget per chain | ~$5 USDC |
| Task deadlines | 5-15 minutes |
| Total chains | 8 (all funded) |

## Why

~$5 per chain must last through **all testing cycles** -- Golden Flow, multichain tests, manual QA, and developer testing. At $0.10 per task, that is ~50 test tasks per chain before funds run out.

## Production Wallet

| Field | Value |
|-------|-------|
| Address | `0xD3868E1eD738CED6945A574a7c769433BeD5d474` |
| Funded on | All 8 chains |
| Role | Platform wallet (agent-side payments) |

See [[wallet-roles]] for the full wallet architecture.

## Per-Chain Funding

All 8 chains funded with USDC:
- Base, Ethereum, Polygon, Arbitrum, Avalanche, Optimism, Celo, Monad
- KK agents: $200 USDC bridged from Avalanche (distributed across 24 agents, 8 chains)

## Cost Breakdown (per Golden Flow run)

| Item | Cost |
|------|------|
| Task bounty | $0.10 |
| Platform fee (13%) | $0.013 |
| Gas (Facilitator pays) | $0.00 |
| **Total per run** | **~$0.113** |

## Related

- [[task-factory]] -- tool for creating test tasks
- [[golden-flow]] -- primary E2E consumer of budget
- [[multichain-golden-flow]] -- runs across all 8 chains
- [[wallet-roles]] -- wallet architecture
