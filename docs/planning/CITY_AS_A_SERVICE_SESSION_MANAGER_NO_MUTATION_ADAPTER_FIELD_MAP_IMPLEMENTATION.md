# City as a Service — Session-Manager No-Mutation Adapter Field Map Implementation

> Scope: Execution Market AAS / City-as-a-Service internal/admin only.
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`.
> Status: no-mutation adapter field map landed; no operator answer, no approval, no runtime mutation, no customer/public exposure.
> Safe claim: `internal_admin_aas_session_manager_no_mutation_adapter_field_map_landed`.

## What landed

Implemented the second no-answer proof from the June 2 decision-support plan: a deterministic **disabled/default-off session-manager adapter field map**.

The map consumes:

- `aas_memory_acontext_readiness_carry_forward_card.json`

It answers only one narrow question:

> If a future operator explicitly approves disabled/default-off design-only wiring, which carry-forward fields may enter an IRC/session-manager adapter shape, and which fields must remain excluded?

It does **not** approve, select, wire, register, enable, configure, mutate, or test anything.

## Files added

- `mcp_server/city_ops/aas_session_manager_no_mutation_adapter_field_map.py`
- `mcp_server/tests/city_ops/test_aas_session_manager_no_mutation_adapter_field_map.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_session_manager_no_mutation_adapter_field_map.json`

Also exported the build/load/write helpers from `mcp_server.city_ops`.

## Allowed adapter field shape

The future disabled/default-off adapter shape may carry only sanitized, reviewed, non-customer/worker-visible fields:

| Adapter field | Source field | Boundary |
|---|---|---|
| `proof_anchor_ref` | `proof_anchor_id` | reviewed proof anchor only |
| `session_alias` | `coordination_session_id_alias` | sanitized alias only; no raw session/message IDs |
| `review_packet_ref` | `review_packet_id` | reviewed internal artifact only |
| `compact_decision_ref` | `compact_decision_id` | reviewed decision object only |
| `source_artifact_digests` | `source_artifact_digests` | SHA-256 digests only |
| `safe_to_claim` | `safe_to_claim` | safe claims must survive beside blocked claims |
| `do_not_claim_yet` | `do_not_claim_yet` | blocked claims remain sticky |
| `next_required_gate` | `next_required_gate` | prevents retrieval from masquerading as approval |
| `kill_switch_default` | `kill_switch_default` | default remains disabled |

## Excluded forever from this adapter shape

- raw session IDs, raw message IDs, chat IDs, message IDs;
- raw transcripts or unreviewed memory blobs;
- private operator context, tokens, API secrets, credentials;
- exact GPS, longitude/latitude, raw EXIF/device metadata;
- customer copy, public routes, worker instructions;
- price quotes, queue launch, dispatch instructions, reputation events, payment readiness claims;
- stopped-project inputs: AutoJob, Frontier Academy, KK v2, KarmaCadabra v2.

## Runtime defaults

All runtime defaults remain disabled:

```text
default_decision = hold_no_runtime_mutation
kill_switch_default = disabled
register_adapter = false
enable_adapter = false
write_session_manager_config = false
mutate_session_manager_state = false
write_live_acontext = false
retrieve_live_acontext = false
autoroute_cross_project = false
emit_customer_copy = false
emit_worker_instruction = false
launch_queue_or_dispatch = false
emit_reputation_or_worker_skill_dna = false
```

## Still blocked

The implementation keeps these false:

```text
operator answer recorded
operator approval recorded
design-only wiring selected
bounded activation test selected or authorized
runtime adapter registration or enablement
session-manager config write
IRC/session-manager mutation
live Acontext write or retrieval
runtime parity
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
  mcp_server/tests/city_ops/test_aas_memory_acontext_readiness_carry_forward_card.py \
  mcp_server/tests/city_ops/test_aas_session_manager_no_mutation_adapter_field_map.py
# 26 passed
```

Full city-ops regression:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1792 passed
```

## Next safe move if no human answer exists

Proceed to the third item from the no-answer plan: a **no-answer observability rubric fixture**.

That next slice should score future agents on boundary preservation, invariant-ID carry-forward, declared-vs-verified honesty, and one-next-proof discipline. It should still create no dashboard, no reputation signal, no public/customer metrics surface, and no runtime mutation.
