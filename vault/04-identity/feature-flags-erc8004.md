---
date: 2026-02-26
tags:
  - type/concept
  - domain/identity
status: active
aliases:
  - ERC-8004 Feature Flags
  - Identity Feature Flags
related-files:
  - mcp_server/platform_config.py
---

# ERC-8004 Feature Flags

Five feature flags in `platform_config.py` that gate [[erc-8004]] integration behavior. All default to **false** for safe rollout.

## Flag Reference

| Flag | Default | Purpose |
|------|---------|---------|
| `erc8004_scoring` | `false` | Include on-chain reputation in [[reputation-scoring]] calculations |
| `erc8004_auto_registration` | `false` | Automatically register new executors on [[erc-8004]] when they join |
| `erc8004_auto_rating` | `false` | Automatically submit ratings to [[erc-8004]] Reputation Registry after task approval |
| `erc8004_rejection` | `false` | Use on-chain reputation as a factor in task application rejection |
| `erc8004_mcp_tools` | `false` | Expose ERC-8004 tools (`em_check_identity`, `em_get_reputation`) via MCP |

## Configuration

Flags are set via environment variables or the `platform_config` table in Supabase:

```python
# Environment variable pattern
ERC8004_SCORING=true

# Or via platform_config table
INSERT INTO platform_config (key, value) VALUES ('feature.erc8004_scoring', 'true');
```

Environment variables take precedence over database values.

## Rollout Strategy

Flags enable incremental activation:

1. **Phase 1**: Enable `erc8004_mcp_tools` -- agents can query identity/reputation
2. **Phase 2**: Enable `erc8004_auto_registration` -- new executors get on-chain IDs
3. **Phase 3**: Enable `erc8004_auto_rating` -- ratings flow to chain automatically
4. **Phase 4**: Enable `erc8004_scoring` -- on-chain data influences task matching
5. **Phase 5**: Enable `erc8004_rejection` -- low on-chain reputation blocks applications

## Test Coverage

122 tests across 7 test files cover all flag combinations. Marker: `pytest -m erc8004` (177 tests including integration).

## Related

- [[erc-8004]] — The registry these flags control integration with
- [[reputation-scoring]] — Scoring behavior modified by `erc8004_scoring`
- [[agent-2106]] — The agent whose operations are affected by these flags
