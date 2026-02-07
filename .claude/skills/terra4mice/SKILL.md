# Terra4mice — Convergence Tracking Workflow

Manage spec-driven development convergence for Execution Market. Use when the user says "terra4mice", "convergence", "check progress", "what's missing", "mark as done", "refresh state", or wants to track implementation status against the spec.

## Quick Reference

| Action | Command |
|--------|---------|
| See what needs work | `terra4mice plan` |
| Scan codebase | `terra4mice refresh` |
| Mark resource done | `terra4mice mark <resource> -s implemented` |
| Mark + lock (survives refresh) | `terra4mice mark <resource> -s implemented --lock` |
| Lock existing resource | `terra4mice lock <resource>` |
| Unlock resource | `terra4mice unlock <resource>` |
| Mark resource partial | `terra4mice mark <resource> -s partial` |
| List all resources | `terra4mice state list` |
| Show one resource | `terra4mice state show <resource>` |

**IMPORTANT**: Always run commands from project root (`/mnt/z/ultravioleta/dao/execution-market`).

## Lock Mechanism

Resources can be **locked** to prevent `refresh` from overwriting them. This eliminates the need to re-mark external/manual items after every refresh.

```bash
# Lock when marking (recommended for external items)
terra4mice mark contract.x402r_escrow -s implemented --lock

# Lock an existing resource
terra4mice lock expansion.erc8004_base_registration

# Unlock if you want refresh to re-scan it
terra4mice unlock expansion.erc8004_base_registration

# State list shows [locked] indicator
terra4mice state list  # locked items show cyan [locked] tag
```

**When to lock:**
- On-chain contracts (always lock — can't be detected from files)
- Live-validated features (lock after manual verification)
- ECS/infrastructure changes (lock — not in codebase)
- Any resource you've manually verified and don't want refresh to touch

**When NOT to lock:**
- File-based resources that refresh can accurately detect
- Resources under active development (let refresh track progress)

## Workflow: Check Current Status

```bash
# 1. See overall convergence
terra4mice plan

# 2. If stale, refresh from codebase (locked items are preserved)
terra4mice refresh

# 3. Check plan again — no need to re-mark locked items!
terra4mice plan
```

## Workflow: After Implementing a Feature

```bash
# 1. Implement the feature (write code, tests, etc.)
# 2. Run refresh to auto-detect file-based resources
terra4mice refresh

# 3. If the feature is external (ECS, on-chain, live test), mark + lock:
terra4mice mark <resource_name> -s implemented --lock

# 4. Verify with plan
terra4mice plan
```

## Workflow: Adding New Resources to Spec

1. Edit `terra4mice.spec.yaml` — add the resource under the appropriate section
2. Run `terra4mice plan` — it will show the new resource as "to create"
3. Implement the feature
4. Run `terra4mice refresh` or `terra4mice mark <resource> -s implemented`

## Gotchas

### 1. Partial Items Get Auto-Promoted
If files exist for a resource, refresh marks it "implemented" even if functionality is incomplete. Either:
- Lock partial items: `terra4mice mark <resource> -s partial --lock`
- Or re-mark after refresh

### 2. Spec File Location
- Spec: `terra4mice.spec.yaml` (project root)
- State: `terra4mice.state.json` (project root, auto-managed)

### 3. Lock Is Resource-Level
Lock protects the entire resource from refresh. If you want refresh to update files/symbols but not status, you'll need to unlock, refresh, then re-lock.

## Currently Locked Resources (16)

Contracts (5): `x402r_escrow`, `usdc_base`, `deposit_relay_factory`, `deposit_relay`, `vault`
Expansion (7): `erc8004_base_registration`, `gasless_agent_registration`, `gasless_worker_registration`, `identity_metadata_api`, `multichain_identity_verification`, `task_network_field`, `task_token_field`
TODOs (4): `d04_register_agent_on_base`, `d11_submission_form_rls`, `fee_rounding_fix`, `admin_dashboard_deploy`

## Current Convergence (2026-02-06)

| Metric | Value |
|--------|-------|
| Total resources | 109 |
| Implemented | ~93 |
| Missing | ~16 (to create) |
| Convergence | 85.3% |

### Remaining To-Create Items
- 5 additional EVM payment networks (optimism, hyperevm, unichain, scroll, skale)
- 6 non-EVM payment networks (solana, near, stellar, algorand, sui, fogo)
- Misc TODOs (d10_stuck_vault, d13_payment_splitter, d15_mermaid, session_persistence_test, cross_chain_agent_discovery)
