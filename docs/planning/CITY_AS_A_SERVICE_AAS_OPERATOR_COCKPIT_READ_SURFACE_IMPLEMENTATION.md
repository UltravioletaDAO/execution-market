# City-as-a-Service — AAS Operator Cockpit Read Surface Implementation

> Date: 2026-06-04 23:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.
> Governing priority: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`.
> Safe claim: `internal_admin_aas_operator_cockpit_read_surface_landed`.

## What landed

Added a deterministic internal/admin read surface that turns the current AAS hold state into a cockpit-shaped artifact without creating an answer, approval, runtime change, product surface, or public dashboard.

- Implementation: `mcp_server/city_ops/aas_operator_cockpit_read_surface.py`
- Fixture: `mcp_server/city_ops/fixtures/aas_package_ladder/aas_operator_cockpit_read_surface.json`
- Tests: `mcp_server/tests/city_ops/test_aas_operator_cockpit_read_surface.py`
- Source consumed: `mcp_server/city_ops/fixtures/aas_package_ladder/aas_four_am_pattern_synthesis_handoff.json`

The artifact exists because the June 4 synthesis named the next useful internal/admin product shape as an operator cockpit rather than another public/customer surface. This slice keeps that cockpit read-only and low-authority.

## Cockpit panes

The fixture renders five panes from existing source-of-truth and handoff artifacts:

1. `source_truth` — current source handoff digest, safe claims, blocked claims, and stopped-project firewall.
2. `allowed_answer_values` — the exact four allowed future two-lane values.
3. `runtime_blocker` — Docker/Acontext/current-runtime blocker truth.
4. `product_exposure_blocker` — Retail Reality/product exposure hold truth.
5. `recommended_no_answer_posture` — `pause_aas_proof_layering` or `keep_both_lanes_held` when no explicit answer exists.

Every pane is explicitly:

```text
internal_admin_read_only = true
selected_by_this_cockpit = false
approval_granted_by_this_cockpit = false
runtime_or_external_promotion_allowed = false
```

## Answer panel

The cockpit displays the four allowed future values exactly:

```text
keep_both_lanes_held
create_retail_reality_answer_or_hold_record
create_runtime_memory_operator_answer_record
pause_aas_proof_layering
```

It selects none of them. Every displayed value requires a separate answer record. Display text is not an answer.

## Runtime blocker snapshot

The read surface carries the current blocker posture as display-only state:

```text
docker_context_observed = desktop-linux
docker_daemon_reachable = false
local_acontext_3000_reachable = false
local_acontext_8080_reachable = false
local_acontext_5173_reachable = false
snapshot_is_runtime_repair = false
snapshot_claims_runtime_parity = false
```

This preserves the current truth without attempting Docker repair, Compose startup, Acontext writes/retrievals, adapter registration, or IRC/session-manager mutation.

## Boundary posture

This artifact records:

- no operator answer;
- no operator approval;
- no selected future answer;
- no answer record;
- no Retail Reality answer/hold record;
- no Retail Reality product exposure;
- no runtime-memory answer record;
- no runtime-memory wiring;
- no runtime adapter registration or enablement;
- no IRC/session-manager mutation;
- no live Acontext write or retrieval;
- no cross-project autorouting;
- no customer/public/worker surface;
- no public dashboard or metric;
- no catalog, pricing, queue, dispatch, or autonomous dispatch;
- no ERC-8004 reputation or Worker Skill DNA;
- no payment or production reverification;
- no exact GPS/raw metadata/private-context release;
- no domain/legal/emergency/safety/repair/insurance/SLA authority;
- no worker-copyable doctrine;
- no stopped-project integration.

## Why this is safe progress

The previous hold-state docs warned against adding more no-answer ceremony. This implementation is intentionally different from another wrapper: it is the first compact internal/admin display contract over existing artifacts. It makes the actual daytime decision easier while preserving the stop/hold boundary.

Safe to claim only:

```text
internal_admin_aas_operator_cockpit_read_surface_landed
```

Meaning only: a deterministic read-only operator cockpit fixture exists and is tested. It orients an internal/admin operator around current truth, allowed answer values, runtime/product blockers, and no-answer posture without selecting or authorizing anything.

## Verification

Focused verification:

```text
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_operator_cockpit_read_surface.py
# 11 passed in 2.47s
```

Full city-ops verification:

```text
git diff --check
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1907 passed in 29.52s
```

## Next safe move

If no explicit human/operator answer exists, use the cockpit to preserve one of two no-answer postures:

```text
pause_aas_proof_layering
```

or

```text
keep_both_lanes_held
```

If Saúl explicitly chooses product exposure later, create exactly one separate Retail Reality answer/hold record first.

If Saúl explicitly chooses runtime memory later, create exactly one separate runtime-memory operator answer record first, then restore Docker daemon reachability and rerun read-only image/container/Compose/API/core/UI checks before any bounded activation attempt.
