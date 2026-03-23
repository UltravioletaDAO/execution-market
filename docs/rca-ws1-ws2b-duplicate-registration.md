# Root Cause Analysis: WS-1 Duplicate Registrations & WS-2b Feature Flag

**Date:** 2026-03-23  
**Affected Worker:** 0xe4dc963c56979e0260fc146b87ee24f18220e545 (executor 141d3fe9)  
**Severity:** High — worker received 9 duplicate ERC-8004 identity NFTs  

## Summary

Worker completed 12+ tasks between Mar 14-23 and received a **new ERC-8004 identity NFT on every completion**, resulting in 9+ duplicate identities. Reputation ratings were scattered across different agent IDs (34, 995, 129, 405, 35, 535, 924, 969, 743, 36069), diluting the worker's on-chain reputation.

## Root Causes

### RC-1: `get_submission()` missing `erc8004_agent_id` in executor join

**File:** `mcp_server/supabase_client.py:367`

```python
# BEFORE (broken)
"*, task:tasks(*), executor:executors(id, display_name, wallet_address, reputation_score)"

# AFTER (fixed)
"*, task:tasks(*), executor:executors(id, display_name, wallet_address, reputation_score, erc8004_agent_id)"
```

Guard 1 in `_ws1_auto_register_worker` checked `executor.get("erc8004_agent_id")`, but the field was never fetched from the database. This guard always returned `None`, even after the executor had a valid `erc8004_agent_id` set.

### RC-2: ERC-8004 contract doesn't implement ERC-721 Enumerable

**File:** `mcp_server/integrations/erc8004/identity.py`

`check_worker_identity()` called `tokenOfOwnerByIndex(address, 0)` to resolve the agent ID from an on-chain balance check. The ERC-8004 Identity Registry at `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` does NOT implement ERC-721 Enumerable — this call always reverts.

Result: `check_worker_identity()` returned `status=REGISTERED, agent_id=None`.

Guard 2 required both `status == "registered" AND agent_id` to be truthy, so it never triggered even though the wallet had NFTs.

### RC-3: Guard 2 condition was too strict

**File:** `mcp_server/api/routers/_helpers.py:843`

```python
# BEFORE (broken) - required BOTH conditions
if onchain_result.status.value == "registered" and onchain_result.agent_id:

# AFTER (fixed) - balance > 0 is sufficient proof
if onchain_result.status.value == "registered":
```

### RC-4: Missing `erc8004_agent_rates_worker_enabled` feature flag (WS-2b)

The WS-2b path in `_execute_post_approval_side_effects` checked:
```python
ws2b_enabled = await PlatformConfig.is_feature_enabled("erc8004_agent_rates_worker")
```

This translates to DB key `feature.erc8004_agent_rates_worker_enabled` — which didn't exist. `PlatformConfig.get()` returned the default `False` (not `None`), so the `if ws2b_enabled is None: ws2b_enabled = ERC8004_AVAILABLE` fallback never triggered.

**Impact:** WS-2b was effectively dead from the side effects path. However, reputation ratings still worked because `_settle_submission_payment()` calls `_send_reputation_feedback()` directly in the settlement code path. So this was a redundancy issue, not a total failure.

## Fixes Applied

### Code Changes (commit 82968a5c)

1. **supabase_client.py**: Added `erc8004_agent_id` to executor joins in `get_submission()` and `get_submissions_for_task()` — Guard 1 now works.

2. **identity.py**: Added DB fallback in `check_worker_identity()` — when `tokenOfOwnerByIndex` reverts, looks up `erc8004_agent_id` from the `executors` table.

3. **_helpers.py**: Guard 2 now triggers on `status == "registered"` alone — if the wallet has any ERC-8004 NFTs (balanceOf > 0), skip registration.

### Database Changes (production)

1. Added `feature.erc8004_agent_rates_worker_enabled = true` to `platform_config`
2. Updated executor `141d3fe9` `erc8004_agent_id` to `36069` (the latest registration)

### Manual Actions

1. Registered the worker via facilitator (agent_id 36069 on Base mainnet):
   - Register TX: `0x216b601992d91105417979f00198232b4f4654862a14d581cb97739ed9e0fea8`
   - Transfer TX: `0x9d537927b3fa25c2d0ab99d00520bd16693e14c7bcc425445f1b68aec5dd801e`

## Timeline of Duplicate Registrations

| Date | Side Effect Status | Agent ID | Notes |
|------|-------------------|----------|-------|
| Mar 14 | success | ? | First registration |
| Mar 15 (x2) | success | ? | Duplicates |
| Mar 16 (x2) | success | ? | Duplicates |
| Mar 17 | success | ? | Registered on avalanche network |
| Mar 19 | success + failed | ? | One revert on-chain |
| Mar 19 | success | ? | Second task same day |
| Mar 20 (x2) | success | ? | Duplicates |
| Mar 22 | success | ? | Gas station task |
| Mar 23 | success | 36069 | Dispensary task |

Each "success" meant a new NFT was minted because Guard 1 and Guard 2 both failed to detect the existing identity.

## Future Work

1. **Consolidate duplicate agent IDs** — The worker now has 9+ agent IDs with scattered reputation. Consider:
   - Burning/revoking old duplicates via facilitator
   - Migrating reputation from old IDs to the canonical one (36069)
   
2. **Registration at signup** — Consider registering workers on ERC-8004 when they connect their wallet via Dynamic.xyz, not just on first completion. This would be cleaner and eliminate the need for WS-1 entirely.

3. **Add monitoring** — Alert when the same wallet gets registered more than once.
