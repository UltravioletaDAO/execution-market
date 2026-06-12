# City as a Service — 1 AM Intake Template Contract Repair (2026-06-12)

Status: internal/admin AAS contract repair only
Safe claim: `internal_admin_aas_1am_intake_template_contract_repair_2026_06_12_landed`
Posture: `pause_aas_proof_layering`

## Scope

This slice obeys `/Users/clawdbot/clawd/DREAM-PRIORITIES.md` over the stale 1 AM cron payload. AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 remain stopped for dream work.

It does not create an operator answer, approval, selected value, answer receipt, customer/public/worker surface, runtime/Acontext/IRC mutation, dispatch, reputation/Worker Skill DNA, payment/production change, exact-location/raw-metadata/private-context release, authority claim, worker-copyable doctrine, or stopped-project integration.

## Repair

The 00:00 answer-intake packet introduced a future receipt template, but its `blocked_claims_preserved` example used the full blocked-claim list. The receipt validator expects `blocked_claims_preserved` to be boolean `true` and treats the detailed blocked-claim material as context, not as the boolean contract field.

The repair now separates the two meanings:

- `blocked_claims_preserved: true` — the validator-facing boolean required by the future receipt contract.
- `blocked_claims_snapshot: [...]` — the internal/admin context list that future handoffs can carry without changing the receipt validator's required field shape.

## Files changed

- `mcp_server/city_ops/aas_operator_answer_intake_packet.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_operator_answer_intake_packet.json`
- `mcp_server/tests/city_ops/test_aas_operator_answer_intake_packet.py`
- `mcp_server/city_ops/aas_source_of_truth_index.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_source_of_truth_index.json`
- `docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
- `docs/planning/CITY_AS_A_SERVICE_1AM_INTAKE_TEMPLATE_CONTRACT_REPAIR_2026_06_12.md`

## Added guard

The intake-packet loader now fails closed if a future change regresses the template back to a list-shaped `blocked_claims_preserved` field, or if the new `blocked_claims_snapshot` no longer matches the packet's `still_blocked_claims` list.

## Verification

```text
Focused intake/source-index/dependent fixture chain: `87 passed`
Full city-ops gate: `2100 passed`
```

## Next valid move

If Saúl gives exactly one allowed AAS answer value, create exactly one separate digest-backed answer receipt using an opaque non-secret reference and validate it through the hardened gate. Otherwise hold at `pause_aas_proof_layering`; do not add downstream product/runtime/reputation/payment layers.
