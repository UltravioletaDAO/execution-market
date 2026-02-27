---
date: 2026-02-26
tags:
  - domain/agents
  - payments/tokens
  - database/migrations
status: active
aliases:
  - Payment Token
  - Token Selection
related-files:
  - supabase/migrations/038_payment_token.sql
  - mcp_server/integrations/x402/sdk_client.py
  - mcp_server/models.py
---

# Payment Token Selection

Each task specifies a `payment_token` field indicating which stablecoin will be used for the bounty. Validated per network to ensure the token exists on the target chain.

## Supported Tokens

| Token | Symbol | Decimals | Chains |
|-------|--------|----------|--------|
| USD Coin | USDC | 6 | All 8 |
| Tether | USDT | 6 | Most |
| Euro Coin | EURC | 6 | Base, Ethereum |
| Aave USD | AUSD | 18 | Select |
| PayPal USD | PYUSD | 6 | Ethereum, Polygon |

## Validation Logic

When a task is created with a `payment_token`:

1. Look up the token in `NETWORK_CONFIG` (source of truth: `sdk_client.py`)
2. Verify the token has a contract address on the task's target network
3. Reject if token is not available on that chain

```python
# Example: PYUSD on Avalanche -> rejected (not deployed there)
# Example: USDC on Base -> accepted (available everywhere)
```

## Database

Migration 038 adds the `payment_token` column to the `tasks` table:

```sql
ALTER TABLE tasks ADD COLUMN payment_token TEXT DEFAULT 'USDC';
```

Default is USDC for backward compatibility with existing tasks.

## Token Registry

The single source of truth is `mcp_server/integrations/x402/sdk_client.py` (`NETWORK_CONFIG` dict). This covers:
- 15 EVM networks (9 mainnets + 6 testnets)
- 5 stablecoins
- 10 networks with x402r escrow support

Other Python files (facilitator_client, tests, platform_config) auto-derive from `sdk_client.py`.

## Related

- [[usdc-stablecoins]] -- Primary payment token details
- [[task-lifecycle]] -- Where token selection fits in task creation
- [[supported-networks]] -- Chain availability matrix
