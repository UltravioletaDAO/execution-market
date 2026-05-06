# City as a Service — Coordination Ledger and Pickup Brief Implementation

> Created: 2026-05-06 00:24 America/New_York  
> Scope: Execution Market AAS / City as a Service only  
> Status: PR-B seed implemented and tested

## 1. Why this slice exists

The first CaaS implementation seed already proved one narrow claim:

> a reviewed packet plus a frozen proof-anchor note can emit one projection-owned compact decision object.

That is useful, but still too local. The next risk is that continuity, export, rebuild, observability, Acontext, and pickup surfaces each reinterpret that decision object in slightly different ways.

This slice closes the first gap after projection truth:

> one compact decision object can generate restart-safe coordination rows and a conservative morning pickup brief without strengthening trust semantics.

It does **not** claim runtime parity, reuse behavior, or closure-proof readiness yet.

## 2. Files added

```text
mcp_server/city_ops/coordination.py
mcp_server/tests/city_ops/test_coordination.py
```

The implementation is intentionally small and local-first. It does not require a database, Docker, live Acontext, IRC, or raw transcript history.

## 3. New artifact contracts

### 3.1 `city_ops.coordination_ledger_event.v1`

Append-only event rows derived from `CompactDecisionObject`.

Current emitted events:

1. `city_compact_decision_projected`
2. `city_session_rebuild_checkpoint_written`

Each row carries the required join fields:

- `coordination_session_id`
- `compact_decision_id`
- `review_packet_id`
- `proof_anchor_id`
- `promotion_class`
- `guidance_tone`
- `guidance_placement`

The first event mirrors reviewed decision truth. The second event mirrors rebuild posture, allowed claims, forbidden claims, next smallest proof, and dangerous drift axes.

### 3.2 `city_ops.morning_pickup_brief.v1`

A compact next-session handoff object derived from the same decision object plus the ledger rows.

It carries:

- exact promotion stance
- guidance tone
- guidance placement
- copyability boundary
- readiness posture
- safe / not-safe claims
- dangerous drift axes
- source episode IDs
- ledger event names
- provenance refs

It also derives a pickup observation class:

| Promotion class | Pickup observation class |
|---|---|
| `confident_memory_delta` | `confirmed` |
| `conservative_memory_delta` | `cautious` |
| `episode_only` | `held` |
| `blocked_from_memory` | `suppressed` |

This keeps conservative learning from being softened into a confident morning handoff.

## 4. Integrity gate

`assert_carry_forward_integrity(...)` fails loudly when downstream continuity artifacts drop or strengthen compact decision truth.

It currently checks:

- ledger schema and join fields
- ordered ledger event indexes
- duplicate event names
- pickup schema
- pickup join fields
- memory promotion decision
- promotion class
- guidance tone
- guidance placement
- `not_safe_to_claim`
- dangerous drift axes

This is the first local version of the carry-forward join check described in the CaaS planning docs.

## 5. What tests prove

Command:

```bash
cd ~/clawd/projects/execution-market/mcp_server
python3 -m pytest tests/city_ops -q
```

Result at implementation time:

```text
11 passed, 1 warning in 0.03s
```

The new tests prove:

1. ledger events preserve compact decision truth
2. morning pickup brief carries anti-overclaim boundaries
3. aligned artifacts pass carry-forward integrity
4. guidance-tone drift fails loudly
5. ledger join drift fails loudly

## 6. What is safe to claim now

Safe:

- projection truth has a first continuity packaging seam
- the current redirect/outdated-packet anchor can emit ledger events and a pickup brief from one compact decision object
- tone, placement, copyability, dangerous drift axes, and anti-overclaim boundaries survive this local handoff

Not safe yet:

- runtime consumers are wired through the compact object
- dispatch reuse behavior is proven
- Acontext retrieval preserves the same decision class
- closure-proof handoff is complete
- operator UI parity is proven

## 7. Next smallest proof

The next implementation slice should wire one runtime consumer through the same compact decision object and require the consumer to pass `assert_carry_forward_integrity(...)` before it can emit pickup/export/rebuild/observability outputs.

Recommended next runtime target:

1. deterministic dispatch-brief composer reads the compact object
2. composer emits guidance tone and placement from the shared fields
3. pickup brief and ledger rows are emitted from the same object
4. a parity test fails if the brief, pickup brief, ledger, or future export row disagree on promotion/tone/placement/copyability

Only after that should the team connect Acontext as a sink/retrieval surface.
