# City-as-a-Service — 00 AM Bounded Local Count Fixture Gate (2026-06-13)

> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.
> Branch: `feat/operator-route-regret-panel`
> Priority source: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`
> Active posture: `pause_aas_proof_layering`.
> Safe claim: `internal_admin_aas_bounded_local_count_fixture_gate_landed`.

## Priority override honored

`DREAM-PRIORITIES.md` was read first and treated as the hard override. The cron payload repeated older requests for AutoJob, Frontier Academy, KK v2, and adjacent tracks, but those are explicitly stopped for dream work. This pass therefore records no AutoJob analysis/integration, no Frontier Academy expansion, no KK v2 continuation, and no KarmaCadabra v2 work.

The mandatory all-repo sync ran first. Execution Market was already up to date on `feat/operator-route-regret-panel`. Some unrelated repos reported pull/stash failures during the all-repo sync; this pass did not inspect or modify those lanes.

## Source contract consumed

This implementation consumes the 23:00 bounded evidence contract:

```text
docs/planning/CITY_AS_A_SERVICE_11PM_BOUNDED_LOCAL_COUNT_EVIDENCE_CONTRACT_2026_06_12.md
```

That contract selected **Bounded Local Count** as the lowest-authority pilot candidate because it can stay within:

```text
one place + one window + one counting question + explicit uncertainty + no representativeness
```

## What landed

Added a deterministic internal fixture schema/review gate:

- `mcp_server/city_ops/aas_bounded_local_count_fixture_gate.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_bounded_local_count_fixture_gate.json`
- `mcp_server/tests/city_ops/test_aas_bounded_local_count_fixture_gate.py`

The gate validates exactly one future internal/admin bounded count packet and fails closed if the packet drifts beyond the evidence contract.

## Fail-closed checks now enforced

A bounded count packet must preserve all of these:

| Check | Gate behavior |
| --- | --- |
| bounded count grammar | requires one count / “how many” / “number of” question and rejects citywide, representative, continuous, predictive, diagnostic, or certification language |
| observation window | requires a bounded non-empty window |
| place boundary | requires a generalized or opaque site reference and rejects raw location/private metadata language |
| count method | only allows `direct_visual_count`, `posted_count`, `receipt_or_log_count`, `visible_subset`, or `unable_to_count` |
| observed value | only allows non-negative integer, bounded range, or `unable_to_count` |
| coverage limits | requires non-empty missingness / exclusion / ambiguity notes |
| uncertainty | requires plain-language uncertainty / boundedness / visibility / not-representative caveat |
| evidence reference | allows digest or opaque non-secret reference only; rejects raw URL/path/data references |
| redaction state | only allows `not_reviewed` or `reviewed_internal_only` |
| blocked claims | requires the full blocked-claim snapshot from the 23:00 contract |
| readiness drift | rejects customer/public/worker/dispatch/reputation/payment/runtime/location/private-context/authority/stopped-project promotion |

## Internal sample packet shape

The persisted artifact includes a safe internal sample packet with:

```json
{
  "schema": "execution_market.aas.bounded_local_count.evidence_contract.v0",
  "status": "internal_admin_contract_only_no_answer_no_approval",
  "count_question": "Count visible queue markers inside one operator-approved zone.",
  "observation_window": "single bounded daytime observation window",
  "place_boundary": "opaque_site_ref_alpha_general_area_only",
  "count_method": "direct_visual_count",
  "observed_value": "3-5",
  "coverage_limits": [
    "rear area not visible",
    "temporary obstruction prevented exact count"
  ],
  "uncertainty_statement": "This is a bounded internal observation with visibility limits; it is not representative.",
  "evidence_digest_reference": "sha256:example_non_secret_digest_reference_only",
  "redaction_review_state": "not_reviewed",
  "blocked_claims_snapshot": [
    "customer_public_worker_surface",
    "dataset_publication_or_representativeness",
    "catalog_pricing_queue_dispatch",
    "reputation_worker_skill_dna",
    "payment_production_change",
    "exact_location_raw_metadata_private_context_release",
    "authority_or_certification_claim",
    "worker_copyable_doctrine"
  ]
}
```

This is a schema/review sample only. It is not an instruction to collect anything.

## Current operator state

```json
{
  "explicit_operator_answer_available": false,
  "operator_approval_recorded": false,
  "answer_receipt_created": false,
  "collection_authorized": false,
  "selected_decision": null,
  "recommended_posture": "pause_aas_proof_layering"
}
```

## Explicit non-claims

This pass records no operator answer, operator approval, answer receipt, collection authorization, customer/public/worker copy, catalog, price, quote, route, queue, dispatch, runtime/Acontext/IRC mutation, reputation/Worker Skill DNA, payment/production change, exact-location/raw-metadata/private-context/PII release, legal/regulatory/safety/repair/insurance/statistical authority, worker-copyable doctrine, or stopped-project integration.

## Verification

Verification:

```text
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops/test_aas_bounded_local_count_fixture_gate.py -q
14 passed

PYTHONPATH=. .venv/bin/python -m pytest mcp_server/tests/city_ops -q
2145 passed
```

## Smallest next safe move

If a real human/operator answer arrives, create exactly one bounded count packet for exactly one approved use case and run it through `validate_bounded_local_count_packet`. Without that answer, keep `pause_aas_proof_layering`; do not create collection tasks, customer copy, worker instructions, catalog/pricing/dispatch paths, reputation events, payment flows, runtime mutation, or public claims.

## Safe claim

```text
internal_admin_aas_bounded_local_count_fixture_gate_landed
```

Meaning only: internal/admin AAS planning now has a deterministic fixture schema/review gate for future Bounded Local Count packets. It preserves the 23:00 evidence contract and fails closed on unbounded questions, missing uncertainty, missing coverage limits, raw location/private metadata, customer/public/worker/dispatch/reputation/payment/runtime/authority promotion, and stopped-project integration.
