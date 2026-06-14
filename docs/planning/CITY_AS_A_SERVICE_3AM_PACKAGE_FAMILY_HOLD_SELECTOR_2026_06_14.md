# City as a Service — 03:00 Package-Family Hold Selector

**Date:** 2026-06-14 03:00 America/New_York
**Scope:** Execution Market AAS / City-as-a-Service internal/admin planning
**Posture:** `pause_aas_proof_layering`

## Why this slice exists

`DREAM-PRIORITIES.md` still wins over the stale cron payload. This pass did **not** pull or analyze AutoJob, expand Frontier Academy, continue KK v2, or touch KarmaCadabra v2.

The 00:00 inventory, 01:00 Visible Asset State state menu, and 02:00 Pre-Event Blocker checklist made three package-family lanes more explicit. The risk after that is menu drift: treating fixture depth as permission. This slice creates a single deterministic selector that keeps the package set held and points back to the one legitimate next gate.

## Added artifacts

- `mcp_server/city_ops/aas_package_family_hold_selector.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_package_family_hold_selector.json`
- `mcp_server/tests/city_ops/test_aas_package_family_hold_selector.py`

## Sources consumed

The selector consumes these held artifacts by digest:

1. `aas_bounded_local_count_fixture_gate.json`
2. `aas_visible_asset_state_internal_state_menu.json`
3. `aas_pre_event_blocker_internal_checklist.json`

## Package-family posture

| Family | State now | Allowed next gate | Still blocked |
|---|---|---|---|
| Bounded Local Count | Fixture gate ready, but no answer | One explicit operator value, then one digest-backed answer receipt | Collection, customer copy, route, dispatch, reputation, payment, runtime, authority |
| Visible Asset State Snapshot | Internal/admin state menu only | Separate asset class + method + boundary + operator answer receipt | Field access, inspection, repair, safety, warranty, SLA, customer copy, dispatch |
| Pre-Event Blocker Check | Internal/admin checklist only | Separate event type + observation window + operator answer receipt | Event-site access, permit/security/vendor/venue decisions, crowd-control authority, customer copy, dispatch |

Recommended single next value if Saúl chooses to move the Bounded Local Count lane:

```text
bounded_local_count.visible_posted_state_count.v1
```

The selector does **not** select it. It only names it as the safest future answer value.

## System-integration connections kept read-only

- **Memory system ↔ Acontext:** carry reviewed `safe_claims`, `blocked_claims`, source digests, and posture only; no live Acontext write/retrieve or memory mutation.
- **IRC session management:** read-only handoff capsule fields only; no session manager mutation, route, queue, or agent assignment.
- **Cross-project decision support:** stale cron filtering and AAS-only hold/answer paths; no AutoJob, Frontier Academy, KK v2, or KarmaCadabra v2 work.
- **Agent observability:** track no-answer discipline, package-family hold, and one-next-gate clarity; no public/customer metric claim.
- **Payment / production maturity:** future launch prerequisite context only; no payment, chain, or production reverification.

## Safe claim

```text
internal_admin_aas_package_family_hold_selector_landed
```

Meaning only: internal/admin AAS planning now has a deterministic selector that consumes the three latest held package-family artifacts, preserves `pause_aas_proof_layering`, and names the single safest future Bounded Local Count answer value without selecting it.

It records no operator answer, approval, selected value, answer receipt, asset class, event type, collection method, customer/public/worker surface, catalog route, price, quote, queue, dispatch path, runtime/Acontext/IRC mutation, reputation / Worker Skill DNA movement, payment/production/chain reverification, exact-location/raw-metadata/private-context release, authority claim, worker-copyable doctrine, or stopped-project integration.

## Verification

```text
PYTHONPATH=. .venv/bin/python -m pytest \
  mcp_server/tests/city_ops/test_aas_package_family_hold_selector.py \
  mcp_server/tests/city_ops/test_aas_pre_event_blocker_internal_checklist.py \
  mcp_server/tests/city_ops/test_aas_visible_asset_state_internal_state_menu.py \
  mcp_server/tests/city_ops/test_aas_bounded_local_count_fixture_gate.py -q

44 passed
```

Next safe action without a human/operator answer: hold. If a real operator answer appears, create one separate digest-backed answer receipt before any downstream gate.
