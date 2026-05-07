# City as a Service — Persisted Artifact Guardrail Implementation

> Created: 2026-05-07 07:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only
> Status: landed as a read-only persisted-artifact guardrail

## 1. Why this seam exists

Live Acontext transport is still blocked in this environment: Docker is unavailable, the Acontext Python SDK is missing, and the local API/dashboard are not reachable.

Rather than pretending the sink exists, this seam adds the narrow guardrail called for by the 6am handoff: validate the already persisted proof artifacts and fail if later consumers make the proof sound more mature than it is.

## 2. New artifact

```text
city_ops.persisted_artifact_guardrail.v1
```

Persisted fixture:

```text
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/persisted_artifact_guardrail.json
```

Runtime implementation:

```text
mcp_server/city_ops/persisted_artifact_guardrail.py
mcp_server/tests/city_ops/test_persisted_artifact_guardrail.py
```

## 3. What it checks

The guardrail reads only the latest persisted proof surfaces:

```text
operator_debug_surface.json
proof_observability_snapshot.json
coordination_intelligence_snapshot.json
```

It fails on four drift classes:

1. **Dropped blocked claims** — critical `do_not_claim_yet[]` entries must stay visible.
2. **Readiness overclaim** — `session_rebuild_ready`, `acontext_sink_ready`, `runtime_parity_proven`, live Acontext write/retrieval, and worker-copyable doctrine flags must remain false.
3. **Raw-source dependency** — consumers must remain read-only over persisted artifacts and must not reopen raw transcripts, unreviewed memory, worker chat, or private operator context.
4. **Worker-copyability drift** — the current municipal learning may stay operator-visible, but it must not become copyable worker instruction or worker-copyable doctrine.

## 4. Current earned label

```text
reuse_parity_landed + telemetry_gate_landed + closure_preview_persisted + session_rebuild_consumer_landed + session_rebuild_report_fixture_landed + acontext_transport_parity_test_landed + acontext_live_preflight_landed + thin_operator_debug_surface_landed + proof_observability_metrics_landed + coordination_intelligence_snapshot_landed + final_morning_handoff_landed + persisted_artifact_guardrail_landed
```

Still false / blocked:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
runtime_parity_proven
acontext_live_write_completed
acontext_live_retrieval_completed
acontext_live_transport_parity_landed
worker-copyable municipal doctrine
polished_review_console_ready
office_memory_view_ready
broad_operator_workflow_ready
multi_jurisdiction_playbook_ready
autonomous_city_dispatch_ready
```

## 5. Verification

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops/test_persisted_artifact_guardrail.py -q
# 6 passed, 1 warning
```

Full city-ops gate after this seam:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 85 passed, 1 warning
```

## 6. Next smallest proof

The useful next step is still live local Acontext transport parity after prerequisites are available. Until then, keep work limited to proof-support guardrails and do not broaden into UI, templates, multi-jurisdiction playbooks, autonomous dispatch, or worker-copyable municipal doctrine.
