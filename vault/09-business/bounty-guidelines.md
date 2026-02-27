---
date: 2026-02-26
tags:
  - domain/business
  - payments/pricing
  - testing
status: active
aliases:
  - Bounty Rules
  - Pricing Guidelines
related-files:
  - scripts/e2e_golden_flow.py
  - scripts/task-factory.ts
  - mcp_server/integrations/x402/sdk_client.py
---

# Bounty Guidelines

Rules for task bounty amounts across testing and production environments. The 13% platform fee is applied on top of every bounty.

## Testing Budget

| Parameter | Value |
|-----------|-------|
| Max test bounty | **$0.20** |
| E2E test bounty | $0.10 (`TEST_BOUNTY`) |
| Budget per chain | ~$5 USDC |
| Test deadline | 5 - 15 minutes |

These limits exist because ~$5 USDC per chain must last through all testing cycles across 8 networks. Exceeding $0.20 per test task drains the budget too fast.

## Production Pricing

Varies by [[task-categories]]:

| Category | Range |
|----------|-------|
| `physical_presence` | $1 - $15 |
| `knowledge_access` | $5 - $30 |
| `human_authority` | $30 - $200 |
| `simple_action` | $2 - $30 |
| `digital_physical` | $5 - $50 |

## Fee Structure

The platform applies a **13% fee** on every completed task:

```
Agent pays:     $1.00 (bounty)
Worker receives: $0.87 (87%)
Platform fee:    $0.13 (13%)
```

- Fee is configurable via `EM_PLATFORM_FEE` env var (default 13%)
- Uses 6-decimal USDC precision
- Minimum fee: $0.01
- Treasury absorbs any x402r protocol fee automatically

In Fase 5 (trustless): Fee is split atomically on-chain by `StaticFeeCalculator(1300 BPS)`. No platform wallet intermediary.

## Task Factory

For creating test tasks quickly:

```bash
cd scripts && npx tsx task-factory.ts \
  --preset screenshot \
  --bounty 0.10 \
  --deadline 10
```

## E2E Script

```bash
python scripts/e2e_mcp_api.py  # Full lifecycle via REST API
python scripts/e2e_golden_flow.py  # Golden Flow acceptance test
```

## Related

- [[test-budget]] -- Overall testing budget tracking
- [[fee-structure]] -- Detailed fee calculation
- [[task-categories]] -- Pricing by category
- [[fund-distribution]] -- How test budgets are funded
