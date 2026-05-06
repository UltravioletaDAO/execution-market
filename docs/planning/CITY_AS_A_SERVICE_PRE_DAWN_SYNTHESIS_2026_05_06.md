# City as a Service — Pre-Dawn Synthesis (2026-05-06)

> Created: 2026-05-06 05:00 America/New_York  
> Scope: Execution Market AAS / City as a Service only  
> Status: pre-dawn handoff + first persisted closure-consumer artifact set

## 1. Priority discipline

This session read `~/clawd/DREAM-PRIORITIES.md` first and followed it over the stale cron payload.

No work was done on:

- AutoJob
- Frontier Academy
- KK v2
- KarmaCadabra v2

The session stayed inside Execution Market AAS / City-as-a-Service.

## 2. What changed since the 4am brief

The 4am closure-preview slice proved that session rebuild and Acontext export previews could be built from bounded compact artifacts. The 5am synthesis turned that into a persisted consumer seam.

New files:

```text
mcp_server/city_ops/proof_block_artifacts.py
mcp_server/tests/city_ops/test_proof_block_artifacts.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/session_rebuild_preview.json
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_export_preview.json
```

Regeneration command:

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m mcp_server.city_ops.proof_block_artifacts --write
```

Test gate:

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 37 passed, 1 warning
```

## 3. Integration insight

The useful pattern tonight is now explicit:

> closure should be proven by deterministic compact artifacts, not by a future agent rereading transcripts and deciding what the lesson probably meant.

The proof block now has three persisted consumer-facing artifacts:

1. `proof_block_telemetry_gate.json` — the queryable truth row.
2. `session_rebuild_preview.json` — the restart/rebuild reader contract.
3. `acontext_export_preview.json` — the provenance-safe export contract.

Each one carries the same join fields:

- `coordination_session_id`
- `review_packet_id`
- `compact_decision_id`
- `proof_anchor_id`

And each one preserves the same conservative limits for `redirect_outdated_packet_001`:

- operator-visible routing guidance is allowed
- worker-copyable instruction remains blocked
- raw transcripts are not required
- unreviewed memory is not allowed
- Acontext/session readiness is not promoted by preview artifacts

## 4. Current honest label

Safe to claim now:

```text
reuse_parity_landed + telemetry_gate_landed + closure_preview_persisted
```

Still not safe to claim:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
worker-copyable municipal doctrine ready
```

## 5. Daytime handoff

The next daytime move is now narrower than the 4am brief:

1. Add one consumer test that reads only the persisted JSON fixture set from disk and simulates a session rebuild.
2. Refuse rebuild if any source contract requires `raw_transcript`, `unreviewed_memory`, `freeform_worker_chat`, or `private_operator_context`.
3. Only after that, consider adding a `session_rebuild_consumer_landed` label.
4. Keep `acontext_sink_ready=false` until a real local Acontext sink writes and retrieves the same conservative fields without semantic strengthening.

## 6. Strategic recommendation

Do not broaden to more municipal templates yet. The strongest daytime priority is to close the first proof block end-to-end:

```text
persisted compact artifacts -> read-only rebuild consumer -> no forbidden sources -> same conservative promotion/copyability posture
```

Once that passes, the team will have the first reusable CaaS closure pattern that can be copied to more city workflows without replaying tonight's reasoning.
