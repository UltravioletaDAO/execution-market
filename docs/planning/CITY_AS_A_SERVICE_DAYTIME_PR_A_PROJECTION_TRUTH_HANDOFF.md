# City as a Service — Daytime PR A Projection Truth Handoff

> Last updated: 2026-05-05 23:05 America/New_York
> Parent docs:
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PROOF_ANCHOR_FREEZE_CONTRACT.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_EXECUTION_LADDER.md`
> - `CITY_AS_A_SERVICE_DECISION_PROJECTION_IMPLEMENTATION_SLICE.md`
> Status: PR A kickoff packet for the first shared-decision ladder

## 1. Why this doc exists

The first proof-anchor freeze note answers **which case** daytime should use.
The first PR split strategy answers **how the whole ladder should be packaged**.
What still needs to be explicit before coding starts is the PR A handoff:

> how does the frozen proof anchor become one shared projection helper and compact decision object without accidentally claiming runtime parity, reuse parity, or closure proof too early?

This doc is the narrow kickoff packet for PR A only.
It should be filled from the selected `proof_anchor_freeze_note.json` before implementation starts.

## 2. PR A single objective

PR A should land only this claim:

> `projection_truth_landed`: one helper owns the trust semantics for the frozen replay-backed case and can emit one deterministic compact decision object.

PR A should not try to prove the flywheel.
It should make the flywheel possible by removing semantic ownership ambiguity.

## 3. Inputs PR A must reference

PR A starts from these inputs:

1. selected `proof_anchor_freeze_note.json`
2. selected source fixture / replay-backed case
3. `review_packet.json` for that case, or the smallest replay input needed to produce it deterministically
4. compact provenance refs required to avoid transcript dependency

If any of those are missing, PR A is not ready.

## 4. Projection-owned fields

PR A must make one helper own these fields:

- `compact_decision_id`
- `coordination_session_id`
- `review_packet_id`
- `summary_judgment`
- `learning_strength`
- `memory_promotion_decision`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`
- `copyable_worker_instruction`
- `continuity_ready`
- `export_ready`
- `session_rebuild_ready`
- `operator_surface_ready`
- `safe_to_claim[]`
- `not_safe_to_claim[]`
- `next_smallest_proof[]`
- `dangerous_drift_axes[]`
- `source_episode_ids[]`
- compact provenance refs

The exact internal names may change during PR A, but the ownership may not.
No later consumer should need to reinvent these semantics.

## 5. Expected compact decision object shape

The first compact object should be inspectable without raw transcripts:

```json
{
  "schema": "city_ops.compact_decision_object.v1",
  "compact_decision_id": "cdo_<stable_id>",
  "coordination_session_id": "city_session_<stable_id>",
  "review_packet_id": "review_packet_<stable_id>",
  "proof_anchor_id": "redirect_outdated_packet_001",
  "summary_judgment": "redirect/reject because reviewed municipal reality invalidated the previous path",
  "learning_strength": "cautionary",
  "memory_promotion_decision": "promote_conservative_delta",
  "promotion_class": "conservative_memory_delta",
  "guidance_tone": "cautionary_or_corrective",
  "guidance_placement": "operator_visible_before_worker_copy",
  "copyable_worker_instruction": {
    "allowed": false,
    "reason": "Reviewed truth supports operator guidance but not direct worker-copyable instruction yet."
  },
  "readiness": {
    "continuity_ready": true,
    "export_ready": false,
    "session_rebuild_ready": false,
    "operator_surface_ready": true
  },
  "safe_to_claim": [
    "projection_truth_landed"
  ],
  "not_safe_to_claim": [
    "runtime_parity_proven",
    "reuse_behavior_proven",
    "closure_proof_ready"
  ],
  "next_smallest_proof": [
    "wire runtime consumers through this compact decision object without strengthening trust semantics"
  ],
  "dangerous_drift_axes": [
    "trust_inflation",
    "worker_copyability_overreach",
    "runtime_consumer_stronger_than_projection",
    "pickup_brief_optimism",
    "reuse_claim_without_behavior_change"
  ],
  "provenance_refs": {
    "source_fixture": "fixtures/city_ops_review_cases/redirect_outdated_packet_001.json",
    "proof_anchor_freeze_note": "artifacts/city_ops/proof_anchors/redirect_outdated_packet_001/proof_anchor_freeze_note.json"
  }
}
```

## 6. PR A should include

- typed projection object / schema
- deterministic projection helper
- compact decision object writer
- downgrade-note shape, even if no downgrade is used yet
- one fixture-backed projection emission test
- one negative test proving missing or ambiguous trust fields fail loudly
- reference to the selected proof-anchor freeze note

Recommended first code seams, if no package exists yet:

```text
mcp_server/city_ops/contracts.py
mcp_server/city_ops/decision_projection.py
mcp_server/tests/city_ops/test_decision_projection.py
mcp_server/city_ops/fixtures/city_ops_review_cases/<selected_anchor>.json
```

Do not start in dashboard surfaces. PR A should be deterministic backend/file-harness work first.

## 7. PR A should not include

- broad dispatch brief rewrites
- morning pickup brief closure packaging
- runtime parity scoreboard claims
- reuse behavior changes
- redispatch behavior claims
- final telemetry gate rows
- closure-proof checklist completion

Those belong to PR B, PR C, and PR D.

## 8. PR A acceptance gate before PR B

Before PR B may start, reviewers should confirm:

- the selected frozen anchor emits the compact decision object deterministically
- projection-owned fields are present or explicitly unavailable with loud failure
- dangerous drift axes from the freeze note appear in the compact object
- `safe_to_claim[]` and `not_safe_to_claim[]` prevent overclaiming
- no downstream helper already contains hidden trust-semantic branches that will compete with the projection owner later

Minimum local check:

```bash
cd mcp_server && pytest tests/city_ops -q
```

That test path should prove, at minimum:
- one replay-backed `review_packet.json` creates projection + compact decision object deterministically
- unknown enums and missing required fields fail loudly
- projection does not require transcript parsing or consumer-specific arguments

If this gate fails, tighten PR A.
Do not continue to runtime consumer wiring.

## 9. Stop conditions

Stop PR A and rework the projection seam if:

- promotion class depends on consumer opinion
- guidance tone or placement is rendered directly from prose instead of projection state
- copyability limits are not represented structurally
- readiness posture is implied instead of explicit
- the compact object requires raw transcript rereads to understand
- the selected proof anchor cannot produce stable deterministic output

## 10. Bottom line

PR A is successful when one frozen replay-backed case can produce one compact decision object that owns trust semantics conservatively.

That is enough.
Anything beyond that should wait for the next rung.
