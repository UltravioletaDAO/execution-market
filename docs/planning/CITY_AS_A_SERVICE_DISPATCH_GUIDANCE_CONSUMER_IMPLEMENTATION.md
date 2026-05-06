# City as a Service — Dispatch Guidance Consumer Implementation

> Created: 2026-05-06 01:34 America/New_York
> Scope: Execution Market AAS / City as a Service only
> Status: first runtime-consumer parity seed implemented and tested

## 1. Why this slice exists

The compact decision object and coordination packaging now preserve projection truth into ledger rows and a morning pickup brief. The next risk was runtime drift: a dispatch brief composer could still re-derive guidance tone, placement, or worker-copyability from raw replay artifacts and accidentally strengthen trust.

This slice creates the first intentionally small runtime consumer:

> a dispatch guidance block reads the projection-owned `CompactDecisionObject`, refuses drifted continuity artifacts, and emits operator guidance without changing promotion, tone, placement, copyability, claim limits, or dangerous drift axes.

It is still not a broad reuse proof, UI proof, or Acontext retrieval proof. It is the first local PR-B-style runtime convergence proof.

## 2. Files added

```text
mcp_server/city_ops/dispatch_guidance.py
mcp_server/tests/city_ops/test_dispatch_guidance.py
```

The implementation remains local-first. It needs no database, Docker, live API, Acontext, IRC, or dashboard surface.

## 3. New artifact contract

### `city_ops.dispatch_guidance_block.v1`

The block represents the dispatch-brief consumer's operator guidance payload.

It carries the join fields:

- `coordination_session_id`
- `compact_decision_id`
- `review_packet_id`
- `proof_anchor_id`

It mirrors the projection-owned policy fields:

- `promotion_class`
- guidance `tone`
- guidance `placement`
- copyable worker-instruction boundary
- operator preface
- claim limits
- dangerous drift axes
- next smallest proof
- pickup observation class
- ledger event names

For the current `redirect_outdated_packet_001` anchor, the guidance remains conservative:

- tone: `cautionary_or_corrective`
- placement: `operator_visible_before_worker_copy`
- worker-copyable instruction: not allowed
- worker instruction text: `null`

## 4. Integrity gates

### 4.1 Builder-level gate

`build_dispatch_guidance_block(...)` calls `assert_carry_forward_integrity(...)` before emitting. If the ledger rows or pickup brief have already drifted from the compact decision object, the dispatch consumer refuses to build.

This matters because runtime consumers should not become a separate truth source.

### 4.2 Consumer parity gate

`assert_dispatch_guidance_parity(...)` fails when the dispatch guidance block strengthens or drops compact decision truth.

It checks:

- schema and runtime consumer name
- core join fields
- summary judgment
- tone and placement against both the compact decision object and pickup brief
- copyable worker-instruction `allowed` and `reason`
- absence of worker instruction text when copyability is false
- `safe_to_claim`
- `not_safe_to_claim`
- `dangerous_drift_axes`
- `next_smallest_proof`

## 5. What tests prove

Command:

```bash
cd ~/clawd/projects/execution-market/mcp_server
python3 -m pytest tests/city_ops -q
```

Result at implementation time:

```text
16 passed, 1 warning in 0.05s
```

The new tests prove:

1. dispatch guidance reads compact decision truth
2. conservative guidance does not become worker-copyable instruction
3. aligned dispatch guidance passes parity
4. the builder refuses a drifted pickup brief
5. parity fails when a consumer overreaches on worker copyability
6. parity fails when a consumer drops anti-overclaim claim limits

## 6. What is safe to claim now

Safe:

- one deterministic dispatch guidance consumer is wired through the compact decision object
- the consumer shares the same tone, placement, copyability, claim limits, and drift axes as the ledger and pickup brief
- the current anchor has a local runtime-convergence seed for dispatch guidance

Not safe yet:

- full runtime parity across all dispatch brief outputs
- reuse behavior proven by redispatch
- closure-proof handoff readiness
- Acontext sink/retrieval parity
- operator UI parity

## 7. Next smallest proof

The next build should connect this block to a concrete dispatch brief artifact and score whether the visible brief changed for the right operational reason.

Recommended next slice:

1. compose `improved_dispatch_brief.json` from `city_ops.dispatch_guidance_block.v1`
2. require the brief to pass `assert_dispatch_guidance_parity(...)`
3. add a baseline-vs-improved scorecard axis for `runtime_guidance_consumed_from_compact_decision`
4. keep worker-copyability blocked for the conservative redirect anchor
5. only then start reuse/redispatch behavior proof

The key discipline remains: one compact decision object owns trust semantics; every downstream artifact must preserve it, not reinterpret it.
