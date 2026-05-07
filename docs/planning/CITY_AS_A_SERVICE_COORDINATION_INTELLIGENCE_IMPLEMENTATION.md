# City as a Service — Coordination Intelligence Snapshot Implementation

> Created: 2026-05-07 04:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only
> Status: landed as a read-only strategy/coordination artifact

## 1. Why this seam exists

The 4am dream question was not “add another broad feature.” It was pattern recognition:

- What patterns emerge from memory-system data?
- How do IRC-style coordination insights inform broader strategy?
- What cross-project intelligence flows create multiplier effects?
- Which agent coordination patterns scale best?

The safe CaaS answer is now encoded as a deterministic artifact instead of a loose prose memo.

The new seam converts `proof_observability_snapshot.json` into a bounded coordination packet that future agents can use without reopening raw transcripts, unreviewed memory, private operator context, or live sinks.

## 2. New artifact

```text
city_ops.coordination_intelligence_snapshot.v1
```

Persisted fixture:

```text
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/coordination_intelligence_snapshot.json
```

Runtime implementation:

```text
mcp_server/city_ops/coordination_intelligence.py
mcp_server/tests/city_ops/test_coordination_intelligence.py
```

## 3. What it derives from

Only:

```text
proof_observability_snapshot.json
```

Explicitly forbidden:

```text
raw_transcript
unreviewed_memory
freeform_worker_chat
private_operator_context
```

The artifact is read-only, performs no live sink write, and marks `semantic_reinterpretation_performed=false`.

## 4. Patterns captured

The snapshot makes four coordination patterns machine-readable:

1. **compact_artifact_spine** — future sessions should coordinate through invariant proof IDs and compact reviewed artifacts, not chat-log archaeology.
2. **claim_boundary_visibility** — safe claims and blocked claims must travel together so speed does not create overclaiming.
3. **operator_only_learning_reuse** — municipal learning may improve operator-visible dispatch prep while worker-copyable doctrine remains blocked.
4. **transport_is_not_truth** — Acontext should transport already-reviewed meaning, not become a semantic source of truth.

## 5. Multiplier insight

The strategic connection is:

> Execution Market becomes more valuable when each reviewed real-world task becomes reusable operational memory, but only if the memory is compact, review-gated, traceable, and honest about what it has not proven.

This bridges memory-system thinking, IRC-style coordination, dispatch, and future Acontext transport through one common handoff language:

```text
coordination_session_id
compact_decision_id
review_packet_id
proof_anchor_id
```

## 6. Guardrails

The snapshot refuses to build if:

- a blocked claim appears in `safe_to_claim`
- the proof observability source is not read-only
- the source writes a live sink
- the source performs semantic reinterpretation
- `session_rebuild_ready`, `acontext_sink_ready`, `runtime_parity_proven`, or worker-copyable doctrine are promoted

It adds two extra blocked claims that are important for scale discipline:

```text
multi_jurisdiction_playbook_ready
autonomous_city_dispatch_ready
```

## 7. Current honest label

```text
reuse_parity_landed + telemetry_gate_landed + closure_preview_persisted + session_rebuild_consumer_landed + session_rebuild_report_fixture_landed + acontext_transport_parity_test_landed + acontext_live_preflight_landed + thin_operator_debug_surface_landed + proof_observability_metrics_landed + coordination_intelligence_snapshot_landed
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

## 8. Verification

```bash
cd ~/clawd/projects/execution-market
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 79 passed, 1 warning

python3 -m py_compile mcp_server/city_ops/coordination_intelligence.py mcp_server/tests/city_ops/test_coordination_intelligence.py
# passed
```

## 9. Next smallest proof

Live Acontext remains blocked. The next useful step is unchanged:

1. Start Docker/local Acontext and expose the Python SDK.
2. Rerun live preflight until `ready_to_attempt_live_transport=true`.
3. Perform one live write/retrieve parity run using the same consumer/report fields.
4. Only then consider `acontext_live_transport_parity_landed`.

Do not broaden into multi-jurisdiction playbooks, autonomous city dispatch, polished review UI, or worker-copyable municipal doctrine from a single redirect proof block.
