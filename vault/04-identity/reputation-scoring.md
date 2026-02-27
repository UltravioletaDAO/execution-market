---
date: 2026-02-26
tags:
  - type/concept
  - domain/identity
status: active
aliases:
  - Reputation Scoring
  - Multi-Dimensional Scoring
related-files:
  - mcp_server/reputation/scoring.py
---

# Reputation Scoring

Multi-dimensional scoring system that evaluates executor performance across four weighted dimensions.

## Scoring Dimensions

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| **Speed** | 30% | How quickly the executor completes tasks relative to deadline |
| **Evidence Quality** | 30% | Completeness and clarity of submitted evidence |
| **AI Verification** | 25% | Automated checks (GPS, EXIF, image analysis) |
| **Forensic** | 15% | Fraud detection signals (spoofing, manipulation) |

## Neutral Defaults

When data is unavailable for a dimension (e.g., no GPS data for AI Verification), the system assigns a **neutral default** rather than penalizing the executor. This prevents cold-start bias for new workers.

## Score Calculation

1. Each dimension produces a score from 0 to 100
2. Scores are weighted by their respective percentages
3. Final score = weighted sum, clamped to [0, 100]
4. Score feeds into [[bayesian-reputation]] for aggregation across tasks

## Integration with Tiers

The reputation score determines which [[executor-tiers]] tier an executor qualifies for. Higher tiers unlock more capabilities and higher-value tasks.

## Feature Gating

Scoring integration with ERC-8004 is controlled by the `erc8004_scoring` flag. See [[feature-flags-erc8004]].

## Related

- [[bayesian-reputation]] — Aggregation layer that combines scores over time
- [[executor-tiers]] — Tier thresholds based on reputation scores
- [[facilitator-reputation]] — How scores are recorded on-chain
