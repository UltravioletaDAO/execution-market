# City-as-a-Service — 11 PM Bounded Local Count Evidence Contract (2026-06-12)

> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.
> Branch: `feat/operator-route-regret-panel`
> Source posture: follows `/Users/clawdbot/clawd/DREAM-PRIORITIES.md` and the June 12 AAS pilot offer map.
> Active posture: `pause_aas_proof_layering`.
> Safe claim: `internal_admin_aas_11pm_bounded_local_count_evidence_contract_2026_06_12_landed`.

## Boundary

This artifact expands the safest pilot-offer lane from the 10 PM map: **Bounded Local Count**. It is an internal/admin evidence contract only. It does **not** create an operator answer, approval, answer receipt, customer/public/worker copy, catalog route, price, quote, queue, dispatch path, runtime/Acontext mutation, reputation path, payment/production change, exact-location/raw-metadata/private-context release, statistical certification, official dataset, authority claim, worker-copyable doctrine, or stopped-project integration.

It is not a collection authorization. It only defines what a future bounded count packet must preserve before any separate human decision can consider exposure.

## Sources reviewed

- `CITY_AS_A_SERVICE_10PM_AAS_PILOT_OFFER_MAP_2026_06_12.md`
- `CITY_AS_A_SERVICE_7AM_AAS_IMPLEMENTATION_CONCEPT_EXPANSION_2026_06_12.md`
- `CITY_AS_A_SERVICE_AAS_LOCAL_DATA_COLLECTION_MEASUREMENT_UNCERTAINTY_RUBRIC_IMPLEMENTATION.md`
- `CITY_AS_A_SERVICE_AAS_CONCEPT_GAP_IMPLEMENTATION_ROADMAP_2026_06_05.md`
- `CITY_AS_A_SERVICE_SERVICE_CATALOG.md`
- `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`

## Why this lane first

Bounded Local Count is the lowest-authority AAS pilot candidate because the value can stay inside a narrow claim:

```text
one place + one window + one counting question + explicit uncertainty + no representativeness
```

That makes it useful for agent operations without pretending that a small observation is a citywide dataset, official measurement, continuous monitor, or legally reliable record.

## Evidence contract

| Contract field | Required shape | Why it exists | Fail-closed if missing |
| --- | --- | --- | --- |
| `count_question` | One bounded, observable question phrased as a count/range, not a diagnosis or prediction. | Prevents scope creep into analytics or authority claims. | Hold; no packet can advance. |
| `observation_window` | Start/end window or coarse time label, with no private schedule or exact sensitive timing. | Prevents timeless or continuous-monitoring claims. | Hold; result cannot be interpreted. |
| `place_boundary` | Generalized non-doxxing site boundary or operator-approved opaque reference. | Keeps exact location/private context out of planning artifacts. | Hold; do not expose coordinates/address/raw metadata. |
| `count_method` | Human-readable method: direct visual count, posted count, receipt/log count, or sampled visible subset. | Makes the method auditable and limits precision. | Hold; no method means no count. |
| `observed_value` | Integer, bounded range, or `unable_to_count`, with reason. | Forces honest output instead of fabricated precision. | Hold unless value is explicitly unavailable with reason. |
| `coverage_limits` | What was excluded, blocked, hidden, ambiguous, or not checked. | Preserves missingness. | Hold if empty for non-trivial environments. |
| `uncertainty_statement` | Plain-language caveat tied to method and visibility. | Stops certification/representativeness claims. | Hold; count without uncertainty is unsafe. |
| `evidence_digest_reference` | Digest or opaque non-secret reference only; no raw GPS/private data. | Allows later audit without leaking private context. | Hold; do not ship raw evidence. |
| `redaction_review_state` | `not_reviewed`, `reviewed_internal_only`, or future separate approval value. | Keeps exposure gated. | Hold for anything outside internal/admin. |
| `blocked_claims_snapshot` | Adjacent list of claims still blocked. | Prevents safe claim drift. | Hold if blocked claims are absent. |

## Allowed output grammar

A future internal/admin packet may say:

- `Observed count: N within the stated window and method.`
- `Observed range: N–M because visibility/source limits prevented exact counting.`
- `Unable to count because [bounded reason].`
- `This is a bounded observation, not a representative dataset or continuous monitor.`
- `Coverage limits: [specific missingness].`
- `Evidence is held by digest/reference only; raw metadata remains blocked.`

A future packet must not say:

- `statistically valid`
- `representative sample`
- `certified count`
- `complete dataset`
- `continuous monitoring`
- `official measurement`
- `customer-ready report`
- `dispatch ready`
- `reputation ready`
- `payment ready`
- `worker instructions approved`

## Internal packet skeleton

```json
{
  "schema": "execution_market.aas.bounded_local_count.evidence_contract.v0",
  "status": "internal_admin_contract_only_no_answer_no_approval",
  "count_question": "<one bounded count/range question>",
  "observation_window": "<bounded window, non-sensitive>",
  "place_boundary": "<opaque non-secret reference or generalized boundary>",
  "count_method": "direct_visual_count | posted_count | receipt_or_log_count | visible_subset | unable_to_count",
  "observed_value": "<integer | range | unable_to_count>",
  "coverage_limits": ["<missingness / exclusions / ambiguity>"],
  "uncertainty_statement": "<plain-language caveat>",
  "evidence_digest_reference": "<opaque digest/reference only>",
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

## Human decision required after this contract

Before any Bounded Local Count packet can become customer-facing, worker-facing, priced, routed, dispatched, reputation-bearing, runtime-backed, or payment-connected, a separate human/operator gate must approve all of the following for exactly one use case:

1. the exact count question;
2. the allowed method;
3. the allowed place-boundary/redaction shape;
4. the limitation/uncertainty language;
5. the delivery path, if any;
6. the claims that remain blocked.

If that decision does not exist, the only valid state remains:

```text
pause_aas_proof_layering
```

## Smallest next implementation slice

If work continues without a human answer, the smallest safe implementation is a deterministic **internal fixture schema/review gate** for this contract that fails closed when:

- the count question is unbounded;
- uncertainty is missing;
- coverage limits are missing;
- raw GPS/private metadata appears;
- customer/public/worker/dispatch/reputation/payment readiness is claimed;
- stopped-project integration is suggested.

That next slice would still be internal/admin only and would not authorize collection, exposure, dispatch, or runtime mutation.

## Safe claim

```text
internal_admin_aas_11pm_bounded_local_count_evidence_contract_2026_06_12_landed
```

Meaning only: internal/admin AAS planning now has a bounded evidence contract for the safest pilot candidate, connecting one count question to method, uncertainty, redaction, blocked claims, and the separate human decision required before exposure. It preserves `pause_aas_proof_layering` and does not authorize customer copy, worker instructions, catalog/pricing/queue/dispatch, runtime/Acontext movement, reputation, payment, exact-location/raw-metadata/private-context release, authority claims, or stopped-project work.
