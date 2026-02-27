---
date: 2026-02-26
tags:
  - type/concept
  - domain/identity
status: active
aliases:
  - Bayesian Reputation
  - Bayesian Scoring
related-files:
  - mcp_server/reputation/bayesian.py
---

# Bayesian Reputation

Aggregation layer that combines feedback from multiple sources into a single confidence-weighted reputation score, handling uncertainty with Bayesian priors.

## Why Bayesian?

Simple averages are unreliable with few data points. A worker with 1 perfect review (5/5) should not outrank a worker with 50 reviews averaging 4.8. Bayesian priors solve this by pulling scores toward a neutral baseline until enough evidence accumulates.

## How It Works

1. **Prior**: New executors start with a neutral prior (e.g., 50/100)
2. **Evidence accumulation**: Each completed task adds a data point
3. **Posterior update**: Score shifts from prior toward observed performance
4. **Confidence interval**: Widens with few observations, narrows with many

The more tasks an executor completes, the more their score reflects actual performance rather than the prior.

## Feedback Sources

- **Agent feedback**: The publishing agent rates task completion
- **AI verification**: Automated scoring from [[reputation-scoring]] dimensions
- **On-chain reputation**: Recorded via [[erc-8004]] Reputation Registry
- **Dispute outcomes**: Resolved disputes contribute strong positive/negative signals

## Uncertainty Handling

| Scenario | Behavior |
|----------|----------|
| New executor, no history | Returns prior (neutral) |
| Few tasks, high variance | Wide confidence interval, prior-weighted |
| Many tasks, consistent | Narrow interval, data-driven |
| Sudden quality drop | Bayesian smoothing prevents single-event collapse |

## Related

- [[reputation-scoring]] — The four scoring dimensions that feed into this aggregator
- [[erc-8004]] — On-chain registry where aggregated scores are recorded
- [[executor-tiers]] — Tier placement depends on the Bayesian aggregate
