# City as a Service — Memory-to-Acontext Readiness Carry-Forward Card Implementation

> Scope: Execution Market AAS / City-as-a-Service internal/admin only.
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`.
> Status: readiness carry-forward card landed; no operator answer, no approval, no runtime mutation, no customer/public exposure.
> Safe claim: `internal_admin_aas_memory_acontext_readiness_carry_forward_card_landed`.

## What landed

Implemented the next no-answer proof from the June 2 decision-support plan: a deterministic **memory-to-Acontext readiness carry-forward card**.

The card consumes:

- `acontext_operator_activation_daytime_handoff_packet.json`
- `docs/planning/CITY_AS_A_SERVICE_COORDINATION_CARRY_FORWARD_MATRIX.md`

It answers only one narrow question:

> If a future operator explicitly approves disabled/default-off design-only wiring, which invariant fields must survive into that adapter contract?

It does **not** approve, select, wire, register, enable, or test anything.

## Files added

- `mcp_server/city_ops/aas_memory_acontext_readiness_carry_forward_card.py`
- `mcp_server/tests/city_ops/test_aas_memory_acontext_readiness_carry_forward_card.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_memory_acontext_readiness_carry_forward_card.json`

## Field contract named

The future disabled/default-off adapter must preserve these fields before any runtime memory path can be trusted:

| Field | Why it must survive |
|---|---|
| `proof_anchor_id` | ties future memory to a reviewed proof block |
| `coordination_session_id_alias` | carries only a sanitized alias, not raw session/message IDs |
| `review_packet_id` | preserves the reviewed surface that bounded the claim |
| `compact_decision_id` | explains why future dispatch guidance changed |
| `source_artifact_digests` | keeps retrieval auditable without reopening raw transcripts |
| `safe_to_claim` | keeps allowed claims attached to the memory unit |
| `do_not_claim_yet` | keeps blocked claims sticky and attached |
| `next_required_gate` | prevents retrieved memory from masquerading as approval |
| `kill_switch_default` | forces default-off behavior until a separate approval exists |

## Survival rules

The card makes four fail-closed rules explicit:

1. `safe_to_claim` and `do_not_claim_yet` must survive together.
2. invariant IDs must survive without raw session/message identifiers.
3. source digests must survive without payload replay.
4. approval absence must survive retrieval.

## Still blocked

The implementation keeps these false:

```text
operator answer recorded
operator approval recorded
design-only wiring selected
bounded activation test selected or authorized
runtime adapter registration or enablement
live Acontext write or retrieval
runtime parity
IRC/session-manager mutation
cross-project autorouting
customer/public/worker exposure
pricing, queue, dispatch
ERC-8004 reputation or Worker Skill DNA
payment or production readiness claim
exact GPS/raw metadata release
private operator context release
domain/legal/emergency/repair/insurance/SLA authority
worker-copyable doctrine
stopped-project integration
```

## Verification

```bash
git diff --check
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_memory_acontext_readiness_carry_forward_card.py
# 13 passed
```

## Next safe move if no human answer exists

Proceed to the second item from the no-answer plan: a **disabled/default-off session-manager adapter field map**.

That next slice should consume this carry-forward card and answer only:

> Which of these fields may enter the IRC/session-manager adapter shape if a future approval exists, and which fields must remain excluded forever?

It should still perform no runtime mutation.
