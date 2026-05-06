# City as a Service — Telemetry Gate Implementation

> Last updated: 2026-05-06 03:45 America/New_York  
> Status: first local implementation landed  
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_TELEMETRY_GATE.md`
> - `CITY_AS_A_SERVICE_REUSE_BEHAVIOR_IMPLEMENTATION.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> - `CITY_AS_A_SERVICE_DECISION_SUPPORT_CONTROL_PLANE.md`

## 1. What landed

The first proof-block telemetry gate now exists as local deterministic code:

- `mcp_server/city_ops/observability.py`
- `mcp_server/tests/city_ops/test_observability.py`

It joins the existing CaaS proof seams into one compact row:

1. `CompactDecisionObject`
2. coordination ledger events
3. morning pickup brief
4. reuse observability row
5. reuse behavior scoreboard

The key point: downstream observability, Acontext export review, IRC/session rebuild, and cross-project decision support can now read one conservative gate row instead of reinterpreting the proof block from prose.

## 2. New schema

```text
city_ops.proof_block_telemetry_gate.v1
```

The row includes:

- join fields: `coordination_session_id`, `review_packet_id`, `compact_decision_id`, `proof_anchor_id`
- verdict: `combined_verdict`
- behavior: `behavior_change_class`, `reuse_mode`, `supported_behavior_change_reason[]`
- trust: `trust_preservation_result`, `promotion_rendering_aligned`, `dangerous_axes_failed[]`
- portability: `coordination_trace_complete`, `session_rebuild_ready`, `acontext_sink_ready`, `cross_project_event_reusable`
- anti-overclaim carry-forward: `do_not_claim_yet[]`, `next_smallest_proof[]`, `safe_to_claim[]`

## 3. What the gate proves now

For `redirect_outdated_packet_001`, the gate can honestly say:

- projection truth landed
- coordination carry-forward landed
- dispatch guidance consumed the compact decision
- reuse behavior changed routing for the right reason
- promotion/tone/placement stayed aligned across projection, ledger, pickup, reuse row, and reuse scoreboard
- claim limits survived into telemetry

The current combined verdict is:

```text
reuse_parity_landed
```

## 4. What it refuses to overclaim

The fixture's compact decision still has:

```json
"readiness": {
  "continuity_ready": true,
  "export_ready": false,
  "session_rebuild_ready": false,
  "operator_surface_ready": true
}
```

So the telemetry gate intentionally emits:

```json
"session_rebuild_ready": false,
"acontext_sink_ready": false
```

That is not a failure of the gate. It is the gate doing its job: preventing the proof block from claiming Acontext/session closure before the underlying artifact set is ready.

## 5. Guardrails added

`build_proof_block_telemetry_gate(...)` and `assert_proof_block_telemetry_gate(...)` fail if:

- pickup brief drops `not_safe_to_claim[]`
- ledger event names or join fields drift
- reuse row and reuse scoreboard disagree on behavior class
- reuse scoreboard reports overclaim
- telemetry tries to mark session rebuild ready when the compact decision says it is not
- telemetry tries to mark Acontext sink ready when export readiness is still false

## 6. Why this connects tonight's integration themes

### Memory ↔ Acontext

Acontext readiness is now an explicit boolean derived from export readiness and coordination trace completeness. It is no longer assumed from the existence of memory-like prose.

### IRC/session management

`coordination_trace_complete` checks for the compact decision projection event and session rebuild checkpoint event tied to the same `coordination_session_id`.

### Cross-project decision support

`cross_project_event_reusable` confirms the row has stable join fields, behavior class, and aligned promotion rendering. Adjacent AAS/control-plane surfaces can reuse this event shape without inheriting CaaS-specific prose.

### Agent observability

The gate row is directly queryable as a proof-block success metric and can be rolled up later into CaaS dashboards.

## 7. Verification

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 29 passed, 1 warning
```

## 8. Honest next move

The next smallest proof is not another planning doc. It is an artifact/export slice:

1. emit a concrete telemetry gate JSON fixture for `redirect_outdated_packet_001`
2. add a session-rebuild preview that reads only ledger + pickup + telemetry gate
3. add an Acontext export preview that refuses raw transcripts and exports only compact decision-safe fields
4. flip readiness only after those consumers pass without semantic reinterpretation

Until then, the correct label remains:

```text
reuse_parity_landed + telemetry_gate_landed
```

Do **not** claim:

- `closure_proof_landed`
- `session_rebuild_ready`
- `acontext_sink_ready`
- `worker-copyable municipal doctrine ready`
