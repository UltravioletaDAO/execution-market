---
date: 2026-02-26
tags:
  - type/concept
  - domain/identity
  - domain/business
status: active
aliases:
  - Executor Tiers
  - Worker Tiers
related-files:
  - mcp_server/reputation/scoring.py
---

# Executor Tiers

Five-tier progression system that gates executor capabilities based on completed tasks and [[reputation-scoring]] scores.

## Tier Definitions

| Tier | Tasks Required | Min Reputation | Unlocks |
|------|---------------|----------------|---------|
| **Probation** | < 10 | -- | Basic tasks only, limited bounty amounts |
| **Standard** | 10-49 | >= 60 | Standard task pool, moderate bounties |
| **Verified** | 50-99 | >= 75 | Priority assignment, higher-value tasks |
| **Expert** | 100-199 | >= 85 | Complex tasks, expedited disputes |
| **Master** | 200+ | >= 90 | All tasks, maximum bounties, mentorship |

## Progression Rules

- **Both criteria must be met**: An executor with 200 tasks but reputation 70 remains Standard
- **Tiers can decrease**: Sustained poor performance drops reputation below thresholds
- **No manual overrides**: Tier is computed dynamically from on-chain and off-chain data
- **Cold start**: New executors enter Probation with a neutral Bayesian prior (see [[bayesian-reputation]])

## Business Logic

Tiers affect task matching:

1. **Task publishers** can set minimum tier requirements
2. **Auto-assignment** prioritizes higher-tier executors for time-sensitive tasks
3. **Dispute resolution** weighs executor tier as a credibility signal
4. **Bounty limits** scale with tier to protect both parties

## Tier Transitions

```
Probation --[10 tasks, rep>=60]--> Standard
Standard  --[50 tasks, rep>=75]--> Verified
Verified  --[100 tasks, rep>=85]--> Expert
Expert    --[200 tasks, rep>=90]--> Master
```

Any tier can drop back if reputation falls below the threshold for more than a review period.

## Related

- [[reputation-scoring]] — The scoring dimensions that determine reputation
- [[bayesian-reputation]] — How reputation aggregates over time
- [[task-lifecycle]] — The task flow that generates reputation data
