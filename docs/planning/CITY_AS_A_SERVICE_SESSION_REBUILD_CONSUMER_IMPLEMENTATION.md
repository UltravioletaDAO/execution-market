# City as a Service — Read-Only Session Rebuild Consumer Implementation

> Created: 2026-05-06 07:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: implementation landed on `feat/operator-route-regret-panel`

## 1. Why this slice exists

The 5am/6am handoff left one deliberately small next move: prove that a real consumer can rebuild the first CaaS proof block from persisted compact artifacts without reopening raw transcripts, unreviewed memory, worker chat, or private operator context.

This slice adds that read-only consumer.

It does **not** claim full closure proof, Acontext sink readiness, or worker-copyable municipal doctrine.

## 2. New code artifacts

```text
mcp_server/city_ops/session_rebuild_consumer.py
mcp_server/tests/city_ops/test_session_rebuild_consumer.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/session_rebuild_report.json
```

The consumer reads only the persisted proof-block fixture set:

```text
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/proof_block_telemetry_gate.json
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/session_rebuild_preview.json
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_export_preview.json
```

## 3. New consumer contract

The emitted bundle schema is:

```text
city_ops.session_rebuild_consumer_bundle.v1
```

The emitted read-only debug report schema is:

```text
city_ops.session_rebuild_report.v1
```

The report is derived from the validated consumer bundle only. Its source
contract allows `city_ops.session_rebuild_consumer_bundle.v1` and keeps raw
transcripts, unreviewed memory, freeform worker chat, private operator context,
and live sinks out of scope.

The bundle marks:

```text
consumer_verdict = read_only_session_rebuild_consumer_landed
safe_to_claim += session_rebuild_consumer_landed
```

The source-read contract stays bounded:

```text
allowed_sources:
  - persisted_proof_block_telemetry_gate
  - persisted_session_rebuild_preview
  - persisted_acontext_export_preview
forbidden_sources:
  - raw_transcript
  - unreviewed_memory
  - freeform_worker_chat
  - private_operator_context
raw_transcript_required: false
read_only: true
writes_live_sink: false
```

## 4. Guardrails added

The consumer fails if any persisted artifact or source contract:

- is missing
- points at the wrong `proof_anchor_id`
- lists a forbidden source as allowed
- actively references a forbidden source outside explicit forbidden/excluded guardrail lists
- drifts on identity fields:
  - `coordination_session_id`
  - `compact_decision_id`
  - `review_packet_id`
  - `proof_anchor_id`
- drops or changes `safe_to_claim[]` / `not_safe_to_claim[]`
- changes promotion class, guidance tone, guidance placement, or copyable-worker boundary across previews
- tries to mark cautious learning as worker-copyable
- promotes session rebuild or Acontext readiness from preview state

## 5. Honest label after this slice

Use this label now:

```text
reuse_parity_landed + telemetry_gate_landed + closure_preview_persisted + session_rebuild_consumer_landed
```

Still do **not** claim:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
worker-copyable municipal doctrine ready
```

The consumer is real and read-only. Readiness remains false because no live rebuild or Acontext sink has written/retrieved the same fields without semantic strengthening yet.

## 5.1 Honest label after the report fixture slice

Use this label now:

```text
reuse_parity_landed + telemetry_gate_landed + closure_preview_persisted + session_rebuild_consumer_landed + session_rebuild_report_fixture_landed
```

Still do **not** claim:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
worker-copyable municipal doctrine ready
```

The report is a debug/read-only fixture for downstream UI inspection. It is not a live session rebuild, not an Acontext sink write/retrieve, and not worker-copyable municipal doctrine.

## 6. Verification

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 48 passed, 1 warning
```

## 7. Next smallest proof

The next safe move is an Acontext transport test: write/retrieve the same consumer bundle and rebuild report fields, then prove the same identity, claim, promotion, copyability, and readiness boundaries survive without semantic strengthening.
