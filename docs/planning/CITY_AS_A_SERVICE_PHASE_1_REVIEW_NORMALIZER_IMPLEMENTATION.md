# City as a Service — Phase 1 Review Normalizer Implementation

> Created: 2026-05-08 02:00 dream session
> Scope: Execution Market AAS / City-as-a-Service only
> Parent docs:
> - `CITY_AS_A_SERVICE_PHASE_1_OFFER_CARDS.md`
> - `CITY_AS_A_SERVICE_PHASE_1_FIXTURE_SPECS_IMPLEMENTATION.md`
> - `CITY_AS_A_SERVICE_PHASE_1_REVIEW_OUTPUT_SCHEMAS.md`
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> Status: landed deterministic normalizer draft; no live customer copy changed

## 1. Why this slice exists

The 01:00 slice defined reviewed-output schemas for the three Phase 1 CaaS offers, but there was still no deterministic seam between an operator/admin review form and a closure-safe reviewed output.

That gap matters because the first sellable CaaS package depends on reviewed municipal outcomes without overclaiming automation, live Acontext readiness, or worker-copyable city doctrine.

This slice adds the first narrow review normalizer draft:

> operator/admin review form → reviewed Phase 1 output → schema validation → no memory write.

## 2. Files added

Code and tests:

- `mcp_server/city_ops/phase1_review_normalizer.py`
- `mcp_server/tests/city_ops/test_phase1_review_normalizer.py`

Persisted fixture artifact:

- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/phase1_review_normalizer_summary.json`

Export updated:

- `mcp_server/city_ops/__init__.py`

## 3. What the normalizer does now

`normalize_phase1_review_output(review_form)` accepts one operator/admin review form for:

- `counter_reality_check`
- `packet_submission_attempt`
- `posting_compliance_check`

It then:

1. accepts `offer` or `offer_id`,
2. stamps `operator_review_status=reviewed` when omitted,
3. stamps the exact offer-specific `proof_status_label` when omitted,
4. stamps `forbidden_claims_preserved=true` when omitted,
5. rejects missing required reviewed-output fields,
6. rejects empty required string fields,
7. rejects unreviewed operator status,
8. rejects broadened proof-status labels,
9. rejects any attempt to mark forbidden claims as not preserved,
10. validates the final output through `validate_phase1_review_output`.

## 4. What it deliberately does not do

Still not safe to claim:

```text
live_customer_schema_contract
autonomous_review_closure
durable_municipal_memory_write
live_acontext_readiness
autonomous_dispatch_readiness
multi_jurisdiction_playbook_readiness
worker_copyable_municipal_doctrine
```

The normalizer is a deterministic local contract only. It does not publish customer copy, update pricing, write durable municipal memory, call Acontext, or authorize autonomous dispatch.

## 5. Why this compounds the AAS plan

The Phase 1 chain is now tighter:

1. offer card bounds the sellable concierge SKU,
2. fixture spec locks the proof expectations,
3. reviewed-output schema locks the closure shape,
4. review normalizer turns operator input into a schema-valid reviewed result.

That gives the next builder a direct, testable handoff for the first Counter Reality Check proof fixture without reopening broad catalog, UI, or transport questions.

## 6. Test gate

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Result after this slice:

```text
125 passed, 1 warning in 0.12s
```

## 7. Next smallest proof

Use the normalizer to create the first `counter_reality_check` reviewed fixture:

1. stale/contradictory online guidance input,
2. explicit source separation (`observed`, `heard_from_staff`, `documented`, or `mixed`),
3. operator-reviewed structured next step,
4. no durable memory write until replay/promotion gates pass,
5. proof label remains `planning_supported_needs_first_fixture` until the fixture exists and is reviewed.

Do not expand front-door offers, customer copy, live Acontext claims, broad municipal doctrine, or autonomous dispatch before this first reviewed fixture is in place.
