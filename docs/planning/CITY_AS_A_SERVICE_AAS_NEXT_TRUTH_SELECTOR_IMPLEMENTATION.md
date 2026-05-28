# City-as-a-Service AAS Next Truth Selector Implementation

**Date:** 2026-05-28 04:00 ET
**Scope:** Execution Market AAS / City-as-a-Service only
**Artifact:** `aas_next_truth_selector.json`
**Safe claim:** `admin_aas_next_truth_selector_landed`

## Why this exists

The late-night pattern was clear: the highest-value AAS work is no longer another internal route layer. The current proof ladder already has:

1. an exponential-value pathfinder that identifies runtime memory/Acontext parity as the highest-multiplier unlock,
2. an Acontext prerequisite activation board that records setup progress but blocks live transport claims, and
3. a system-integration route regret panel that says more route layers add ceremony rather than truth.

The selector joins those signals into one conservative decision: **advance runtime-truth prerequisite work next; do not create more route layers or customer/public surfaces.**

## Pattern recognition distilled

| Pattern | Useful action | Explicitly blocked shortcut |
| --- | --- | --- |
| Memory insights compound only after reviewed transport exists | Clear Acontext SDK/API/dashboard prerequisites first | Raw memory or transcript direct to live Acontext |
| IRC coordination scales through invariant IDs | Carry source artifact IDs and claim boundaries | Runtime session-manager changes from strategy docs |
| Cross-project intelligence is a filter, not autopilot | Convert insights into one proof gate plus quarantines | Resuming stopped projects or auto-routing customer work |
| Agent coordination quality is private until separately approved | Score proof discipline internally | ERC-8004 reputation / Worker Skill DNA publication |

## Selector decision

Selected track: `runtime_truth_prerequisite_activation`
Selected proof: `clear_acontext_sdk_api_dashboard_then_rerun_read_only_preflight`

Allowed now:

- complete local Acontext service startup,
- wire the active runner to the Acontext SDK,
- rerun read-only preflight after prerequisites clear.

Must rebuild before any live attempt:

- `acontext_live_preflight_blocker_delta`,
- `acontext_live_preflight_blocker_delta_read_surface`,
- `acontext_live_parity_attempt_readiness_gate`.

## Boundaries preserved

The selector does **not** authorize:

- more internal route layers,
- live Acontext write/retrieve,
- runtime parity claims,
- customer copy, delivery, publication, catalog/public routes,
- operator queue launch or dispatch,
- pricing or customer quotes,
- ERC-8004 reputation or Worker Skill DNA,
- payment or production reverification,
- exact GPS/raw metadata exposure,
- domain/emergency/legal/repair/insurance/SLA/official-report/fault authority,
- worker-copyable doctrine.

## Implementation

Added:

- `mcp_server/city_ops/aas_next_truth_selector.py`
- `mcp_server/tests/city_ops/test_aas_next_truth_selector.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_next_truth_selector.json`

Updated:

- `mcp_server/city_ops/__init__.py`

## Verification

Targeted gate:

```bash
./.venv/bin/python -m pytest mcp_server/tests/city_ops/test_aas_next_truth_selector.py -q
# 9 passed
```

Full city-ops gate:

```bash
./.venv/bin/python -m pytest mcp_server/tests/city_ops -q
# 1442 passed
```
