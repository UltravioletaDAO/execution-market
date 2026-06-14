# City-as-a-Service — 1 AM Visible Asset State Internal State Menu (2026-06-14)

> Scope: Execution Market AAS / City-as-a-Service internal/admin planning and fixture work only.
> Governing priority: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`.
> Branch observed: `feat/operator-route-regret-panel`.
> Active posture: `pause_aas_proof_layering`.
> Safe claim: `internal_admin_aas_visible_asset_state_internal_state_menu_landed`.

## Boundary

This slice continues the June 14 00:00 package fixture/schema inventory by taking one concept-only family that lacked a clear operational grammar — **Visible Asset State Snapshot** — and adding a held internal/admin state menu.

It does **not** record or infer an operator answer, approval, selected value, answer receipt, asset class, collection method, field visit authorization, access permission, inspection, repair, remediation, customer/public/worker surface, catalog route, price, quote, queue, dispatch path, runtime/Acontext/IRC mutation, reputation / Worker Skill DNA movement, payment/production change, exact-location/raw-metadata/private-context release, authority claim, worker-copyable doctrine, or stopped-project integration.

The correct default remains:

```text
pause_aas_proof_layering
```

## Repository sync note

Execution Market was synced with:

```bash
git -C /Users/clawdbot/clawd/projects/execution-market pull --ff-only
```

Result: already up to date on `feat/operator-route-regret-panel`.

AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 were not pulled, analyzed, edited, tested, or used as sources because `/Users/clawdbot/clawd/DREAM-PRIORITIES.md` explicitly stops those tracks for dream work, even though the stale cron payload listed them.

Pre-existing untracked files remained untouched and unstaged:

- `scripts/sign_req.mjs`
- `mcp_server/city_ops/tests/`

## Sources consumed

- `docs/planning/CITY_AS_A_SERVICE_12AM_AAS_PACKAGE_FIXTURE_SCHEMA_INVENTORY_2026_06_14.md`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_field_asset_visible_state_fixture_outline.json`
- `mcp_server/city_ops/aas_field_asset_visible_state_fixture_outline.py`
- `mcp_server/tests/city_ops/test_aas_field_asset_visible_state_fixture_outline.py`

## What landed

Added a typed fixture/schema slice for the held Visible Asset State Snapshot lane:

- `mcp_server/city_ops/aas_visible_asset_state_internal_state_menu.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_visible_asset_state_internal_state_menu.json`
- `mcp_server/tests/city_ops/test_aas_visible_asset_state_internal_state_menu.py`

The new fixture consumes the prior Field Asset Ops visible-state fixture outline by digest and maps the older source-family name into the canonical June 13 package family:

```text
field_asset_ops → Visible Asset State Snapshot
```

## Internal state menu rows

The fixture defines six required held state rows:

| State code | Safe internal read | Missing truth family | Forbidden promotion |
| --- | --- | --- | --- |
| `visible_presence_state` | Records whether the asset is visibly present from an allowed review context. | `collection_truth` | Does not confirm ownership, access, installation, functionality, or availability. |
| `apparent_access_or_obstruction_state` | Records only visible obstruction or non-obstruction without access authority. | `authority_truth` | Does not authorize entry, removal, repair, dispatch, or safety clearance. |
| `apparent_surface_condition_state` | Records visible surface markers only. | `authority_truth` | Does not diagnose root cause, severity, repair need, or fault/liability. |
| `visible_indicator_state` | Records visible indicator appearance without interpreting system function. | `authority_truth` | Does not certify functionality, safety, warranty, SLA, or operational status. |
| `redacted_media_reference_state` | Tracks whether a redacted internal reference can support the visible-state row. | `location_privacy_truth` | Does not release exact location, raw metadata, private context, or PII. |
| `uncertainty_state` | Keeps uncertainty attached to the internal/admin row. | `operator_truth` | Does not convert uncertain or out-of-scope data into a customer-ready fact. |

## Why this is the right 1 AM move

The 00:00 inventory said not to build another Bounded Local Count no-answer wrapper. It also identified Visible Asset State Snapshot as concept/outline-only. This slice therefore adds useful structure without crossing the held boundary:

1. It makes the concept testable as schema-backed internal/admin grammar.
2. It keeps every row attached to a missing truth family.
3. It prevents state options from becoming hidden approvals.
4. It keeps privacy, access authority, safety, warranty, SLA, repair, dispatch, and customer-copy claims blocked.

## Validation

Targeted city-ops tests passed:

```text
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_aas_visible_asset_state_internal_state_menu.py \
  mcp_server/tests/city_ops/test_aas_field_asset_visible_state_fixture_outline.py

21 passed
```

Because updating the daytime board changed source-index digests, I regenerated the dependent internal/admin fixture chain (`aas_source_of_truth_index` through the downstream bounded-count pattern compounder) and reran the full city-ops suite:

```text
/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops

2165 passed
```

## Safe claim

```text
internal_admin_aas_visible_asset_state_internal_state_menu_landed
```

Meaning only: internal/admin AAS planning now has a schema-backed Visible Asset State Snapshot state menu that consumes the previous Field Asset Ops outline and preserves all held boundaries. It records no operator answer, approval, selected value, answer receipt, asset class, collection method, field visit authorization, access permission, inspection, repair, remediation, customer/public/worker surface, catalog route, price, quote, queue, dispatch path, runtime/Acontext/IRC mutation, reputation / Worker Skill DNA movement, payment/production change, exact-location/raw-metadata/private-context release, authority claim, worker-copyable doctrine, or stopped-project integration.

## Next safe move

If no operator answer appears, the next useful AAS slice is another concept-only state/menu map for **Pre-Event Blocker Check**, because it is the other canonical family that remains outline-only.

Do not move Visible Asset State Snapshot toward field collection, customer copy, route/queue/dispatch, pricing, reputation, payment, runtime, or publication until a separate explicit operator answer and receipt exist.
