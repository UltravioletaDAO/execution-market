# City as a Service — Reuse Behavior Implementation Seed

> Last updated: 2026-05-06 02:55 America/New_York  
> Parent docs:
> - `CITY_AS_A_SERVICE_REUSE_AND_REDISPATCH_ALIGNMENT_SLICE.md`
> - `CITY_AS_A_SERVICE_REUSE_BEHAVIOR_PROOF_SCOREBOARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_PROGRAM_CARD.md`
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> Status: implementation seed landed

## 1. Why this exists

The compact decision projection, coordination ledger, morning pickup brief, and dispatch guidance block now prove that reviewed municipal truth can move through local runtime artifacts without semantic drift.

The next product risk is subtler:

> a later dispatch can display prior city learning but still fail to prove that behavior changed for the right reviewed reason.

This implementation seed adds the first local reuse/redispatch proof surface. It keeps the current `redirect_outdated_packet_001` anchor conservative: the next dispatch may change routing/evidence prep because reviewed city reality invalidated an old packet path, but it still may **not** convert that caution into direct worker-copyable doctrine.

## 2. Files landed

- `mcp_server/city_ops/reuse.py`
- `mcp_server/tests/city_ops/test_reuse.py`

## 3. New artifact contracts

### 3.1 `city_ops.reuse_event.v1`

Records one reuse moment with:
- `coordination_session_id`
- `task_id`
- `compact_decision_id`
- `review_packet_id`
- `proof_anchor_id`
- `reuse_mode`
- `behavior_change_class`
- governing promotion/tone/placement
- copyability boundary
- safe / not-safe claims
- dangerous drift axes
- reused guidance refs

The builder refuses unsupported behavior changes. For the conservative redirect anchor, `routing_changed`, `evidence_guidance_changed`, `redispatch_changed`, and `escalation_changed` may be supported; `instruction_changed` is blocked because worker-copyable text remains false.

### 3.2 `city_ops.worker_instruction_block.v1`

Builds the worker handoff block from the same compact decision truth.

For the current anchor:
- `copyable=false`
- `worker_instruction_text=null`
- `operator_visible_guidance` may still show the reviewed caution
- `excluded_claims` carries the compact decision object's `not_safe_to_claim[]`

This prevents cautious municipal learning from leaking into worker handoff copy via formatting or fallback grouping.

### 3.3 `city_ops.reuse_observability_row.v1`

Records whether reuse was merely shown or materially changed behavior.

The first useful material class is `routing_changed` because the reviewed redirect/rejection truth should change operator-visible routing prep without upgrading copyability.

### 3.4 `city_ops.reuse_behavior_scoreboard.v1`

Compresses the reuse proof into one reviewable verdict:
- behavior change supported
- trust posture preserved
- overclaim detected / not detected
- smarter for the right reason
- supporting evidence
- next review need

The first passing scoreboard can honestly claim **reuse behavior mirrors the shared semantic owner**. It still cannot claim closure proof until telemetry/pickup/checklist packaging preserves that same verdict.

## 4. New acceptance gates

`assert_reuse_alignment(...)` fails if reuse artifacts:
- upgrade promotion class
- change guidance tone or placement
- mark blocked/cautious guidance copyable
- emit worker-copyable text when compact decision copyability is false
- drop `not_safe_to_claim[]`
- report unsupported behavior-change classes

Fixture-backed tests now cover:
- reuse event parity
- non-copyable worker-instruction filtering
- material behavior-change observability
- reuse behavior scoreboard pass case
- rejection of unsupported `instruction_changed` under conservative copyability
- trust-upgrade failure
- worker-copyability leak failure
- claim-limit-drop failure

## 5. What this earns

This seed earns a narrow rung-3 claim:

> one replay-backed CaaS decision can change a later dispatch's routing behavior through reuse while preserving compact decision trust boundaries.

It does **not** yet earn:
- full runtime parity across export/rebuild/Acontext
- closure-proof readiness
- telemetry/pickup handoff safety
- confident worker-copyable municipal doctrine

## 6. Next smallest honest move

The next CaaS build should package the projection/runtime/reuse verdict into closure artifacts:

1. shared decision parity scoreboard
2. reuse behavior scoreboard
3. combined verdict
4. telemetry gate row
5. morning pickup brief fidelity review
6. closure-proof checklist result

Until that chain exists, keep reporting progress as `reuse_parity_landed`, not `closure_proof_landed`.
