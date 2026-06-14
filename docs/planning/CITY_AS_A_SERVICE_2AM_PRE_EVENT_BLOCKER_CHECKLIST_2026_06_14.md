# City-as-a-Service — 2 AM Pre-Event Blocker Internal Checklist (2026-06-14)

> Scope: Execution Market AAS / City-as-a-Service internal/admin planning and fixture work only.
> Governing priority: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`.
> Branch observed: `feat/operator-route-regret-panel`.
> Active posture: `pause_aas_proof_layering`.
> Safe claim: `internal_admin_aas_pre_event_blocker_internal_checklist_landed`.

## Boundary

This slice continues the June 14 package-family work by taking the other concept-only family named by the 01:00 handoff — **Pre-Event Blocker Check** — and giving it a held internal/admin checklist grammar.

It does **not** record or infer an operator answer, approval, selected value, answer receipt, event type, collection method, event-site access authorization, permit/security/vendor/venue decision, crowd-control authority, customer/public/worker surface, catalog route, price, quote, queue, dispatch path, runtime/Acontext/IRC mutation, reputation / Worker Skill DNA movement, payment/production change, exact-location/raw-metadata/private-context release, authority claim, worker-copyable doctrine, or stopped-project integration.

The correct default remains:

```text
pause_aas_proof_layering
```

## Repository sync note

Execution Market was synced first within the allowed lane:

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
- `docs/planning/CITY_AS_A_SERVICE_1AM_VISIBLE_ASSET_STATE_MENU_2026_06_14.md`
- `mcp_server/city_ops/aas_event_readiness_observation_outline.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_event_readiness_observation_outline.json`
- `mcp_server/tests/city_ops/test_aas_event_readiness_observation_outline.py`

## What landed

Added a typed fixture/schema slice for the held Pre-Event Blocker Check lane:

- `mcp_server/city_ops/aas_pre_event_blocker_internal_checklist.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_pre_event_blocker_internal_checklist.json`
- `mcp_server/tests/city_ops/test_aas_pre_event_blocker_internal_checklist.py`

The new fixture consumes the prior Event Readiness observation outline by digest and maps the older source-family name into the canonical June 13 package family:

```text
event_readiness → Pre-Event Blocker Check
```

## Internal checklist rows

The fixture defines seven required held checklist rows:

| Check code | Safe internal read | Missing truth family | Forbidden promotion |
| --- | --- | --- | --- |
| `visible_setup_presence_state` | Records only whether visible pre-event setup appears present from an allowed review context. | `authority_truth` | Does not certify operational readiness, capacity, safety, attendance, or event outcome. |
| `wayfinding_and_staging_state` | Records visible wayfinding or staging markers without deciding whether they are sufficient. | `authority_truth` | Does not confirm permit compliance, crowd flow, accessibility, or event readiness. |
| `apparent_access_or_obstruction_state` | Records only visible obstruction signals without access or crowd-control authority. | `authority_truth` | Does not authorize entry, removal, route change, security action, or safety clearance. |
| `visible_vendor_or_equipment_state` | Records visible vendor or equipment presence without performance or commitment claims. | `surface_truth` | Does not confirm vendor commitment, equipment functionality, service level, or delivery outcome. |
| `time_window_warning_state` | Keeps any pre-event blocker observation tied to a bounded time window. | `runtime_truth` | Does not create monitoring, SLA, real-time status, or event-day guarantee. |
| `redacted_reference_state` | Tracks whether a redacted internal reference can support the blocker row. | `location_privacy_truth` | Does not release exact location, raw metadata, private context, contact data, or PII. |
| `unresolved_not_checked_state` | Keeps not-checked and inconclusive facts attached to any blocker summary. | `operator_truth` | Does not convert omitted, ambiguous, or out-of-scope facts into customer-ready claims. |

## Why this is the right 2 AM move

The 00:00 inventory and 01:00 visible-state slice both said not to build another Bounded Local Count no-answer wrapper. They also identified Pre-Event Blocker Check as a remaining concept-only grammar gap.

This slice adds useful structure without crossing the held boundary:

1. It makes the Pre-Event Blocker Check concept testable as schema-backed internal/admin grammar.
2. It keeps every checklist row attached to a missing truth family.
3. It prevents checklist options from becoming hidden approvals.
4. It keeps event-site access, permits, security, vendors, venue decisions, crowd-control, capacity, safety, SLA, dispatch, customer-copy, and exact-location/raw-metadata/private-context claims blocked.

## Validation

Targeted city-ops tests passed:

```text
PYTHONPATH=. python3 -m pytest -q \
  mcp_server/tests/city_ops/test_aas_pre_event_blocker_internal_checklist.py \
  mcp_server/tests/city_ops/test_aas_event_readiness_observation_outline.py

21 passed, 2 warnings
```

Full city-ops verification is the appropriate broader gate after updating the daytime board/source-index digest chain.

## Safe claim

```text
internal_admin_aas_pre_event_blocker_internal_checklist_landed
```

Meaning only: internal/admin AAS planning now has a schema-backed Pre-Event Blocker Check checklist that consumes the previous Event Readiness observation outline and preserves all held boundaries. It records no operator answer, approval, selected value, answer receipt, event type, collection method, event-site access authorization, permit/security/vendor/venue decision, crowd-control authority, customer/public/worker surface, catalog route, price, quote, queue, dispatch path, runtime/Acontext/IRC mutation, reputation / Worker Skill DNA movement, payment/production change, exact-location/raw-metadata/private-context release, authority claim, worker-copyable doctrine, or stopped-project integration.

## Next safe move

If no operator answer appears, stop adding concept-only schema menus for these two outline families and return to the central gate:

1. if Saúl provides exactly one allowed Bounded Local Count value, create exactly one separate digest-backed answer receipt with an opaque non-secret reference; otherwise
2. keep `pause_aas_proof_layering` and do not add customer copy, worker instructions, public routes, runtime writes, reputation receipts, payments, or authority claims.
