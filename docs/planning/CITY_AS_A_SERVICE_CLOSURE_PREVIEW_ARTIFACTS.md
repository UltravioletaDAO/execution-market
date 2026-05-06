# City as a Service — Closure Preview Artifacts

> Last updated: 2026-05-06 04:35 America/New_York  
> Status: bounded local implementation landed  
> Parent docs:
> - `CITY_AS_A_SERVICE_TELEMETRY_GATE_IMPLEMENTATION.md`
> - `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> - `CITY_AS_A_SERVICE_ACONTEXT_LOCAL_SERVER_AND_SESSION_DISCIPLINE.md`

## 1. What landed

The CaaS proof ladder now has a bounded closure-preview layer:

- `mcp_server/city_ops/closure.py`
- `mcp_server/tests/city_ops/test_closure.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/proof_block_telemetry_gate.json`

This does **not** claim full closure readiness. It proves the next consumers can read the proof block without reopening transcripts or reinterpreting municipal truth.

## 2. New schemas

```text
city_ops.session_rebuild_preview.v1
city_ops.acontext_export_preview.v1
```

The session rebuild preview is constrained to:

```text
coordination_ledger + morning_pickup_brief + proof_block_telemetry_gate
```

The Acontext export preview is constrained to:

```text
compact_decision_object + morning_pickup_brief + proof_block_telemetry_gate
```

Both explicitly forbid:

```text
raw_transcript
unreviewed_memory
freeform_worker_chat
private_operator_context
```

## 3. Why this matters

Tonight's pattern-recognition insight is that agent coordination scales best when every handoff has the same four properties:

1. **Stable join fields** — `coordination_session_id`, `review_packet_id`, `compact_decision_id`, `proof_anchor_id`.
2. **Bounded claims** — the artifact carries `not_safe_to_claim[]` as loudly as `safe_to_claim[]`.
3. **Source discipline** — downstream agents know exactly which artifacts they may read.
4. **No semantic promotion by transport** — exporting to Acontext or rebuilding a session cannot make the lesson more confident than the compact decision allowed.

That pattern generalizes beyond CaaS: IRC coordination, Acontext memory, observability, and cross-project decision support all need compact decision objects plus append-only coordination events, not prose-only summaries.

## 4. Current proof state for `redirect_outdated_packet_001`

The fixture proves:

- prior reviewed redirect learning changed later dispatch routing
- the change stayed operator-visible
- worker-copyable instruction stayed blocked
- telemetry stayed queryable through one JSON fixture
- session rebuild and Acontext export can preview from safe compact sources

The honest labels are now:

```text
reuse_parity_landed + telemetry_gate_landed + closure_preview_landed
```

The labels still **not** allowed are:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
worker-copyable municipal doctrine ready
```

## 5. Implementation notes

`build_session_rebuild_preview(...)` validates the compact decision, coordination ledger, morning pickup brief, and telemetry gate before emitting a preview. It keeps:

```json
"preview_promotes_readiness": false
```

`build_acontext_export_preview(...)` exports only provenance-safe fields:

- summary judgment
- learning strength
- promotion decision/class
- tone and placement
- copyability boundary
- telemetry verdict
- supported behavior-change reasons
- claim limits
- source episode IDs
- provenance refs

It does not include raw transcripts, worker chat, private operator context, or unreviewed memory.

## 6. Verification

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 34 passed, 1 warning
```

## 7. Best next move

The next daylight engineering slice should promote this from preview to real closure only after one consumer passes without reinterpretation:

1. write the session preview and Acontext preview as deterministic JSON artifacts beside the telemetry gate fixture
2. add a tiny CLI/script that regenerates all proof-block artifacts from the fixture pack
3. add one replay test that fails if a consumer reads a forbidden source
4. only then consider flipping `session_rebuild_ready` or `export_ready` in the compact decision readiness posture
