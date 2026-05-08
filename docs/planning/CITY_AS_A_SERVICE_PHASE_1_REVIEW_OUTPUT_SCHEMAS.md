# City as a Service — Phase 1 Review Output Schemas

> Created: 2026-05-08 01:00 dream session
> Scope: Execution Market AAS / City-as-a-Service only
> Parent docs:
> - `CITY_AS_A_SERVICE_PHASE_1_OFFER_CARDS.md`
> - `CITY_AS_A_SERVICE_PHASE_1_FIXTURE_SPECS_IMPLEMENTATION.md`
> - `CITY_AS_A_SERVICE_AAS_PACKAGING_AUDIT_2026_05_07.md`
> Status: internal review/schema draft; not live customer copy

## 1. Why this slice exists

The midnight slice converted the Phase 1 CaaS offer cards into fixture specs. The next ambiguity was the handoff between “a worker/operator says what happened” and “the product can safely close a reviewed municipal result.”

This slice adds a deterministic reviewed-output schema bundle for the three Phase 1 offers:

- `counter_reality_check`
- `packet_submission_attempt`
- `posting_compliance_check`

The goal is narrow: every first proof fixture must produce a reviewed output with the same trust-bearing seams before we build the review normalizer or promote any live customer-copy contract.

## 2. What landed

Added:

- `mcp_server/city_ops/phase1_review_output_schemas.py`
- `mcp_server/tests/city_ops/test_phase1_review_output_schemas.py`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/phase1_review_output_schema_bundle.json`

Updated:

- `mcp_server/city_ops/__init__.py`

## 3. Contract now enforced

Every Phase 1 reviewed output schema must preserve:

```text
offer
outcome_status
source_type
evidence_summary
operator_review_status
structured_next_step
follow_on_task_trigger
proof_status_label
forbidden_claims_preserved
```

It also carries offer-specific fields from the offer fixture spec, so a future proof builder cannot accidentally drop card-specific output requirements while standardizing the review seam.

## 4. Guardrails

The schema bundle explicitly preserves these boundaries:

- operator review required
- concierge/manual Phase 1 only
- no customer copy change
- no automation claim
- no live transport readiness claim
- proof status label must match the fixture spec
- forbidden claims must remain blocked

Earned label:

```text
phase_1_review_output_schema_drafts_landed
```

Still not safe to claim:

```text
review_normalizer_landed
live_customer_schema_contract
autonomous_review_closure
live_acontext_readiness
guaranteed_approval
legal_sufficiency
city_relationship_or_influence
unlimited_retries
broad_multi_office_base_order
autonomous_dispatch_readiness
multi_jurisdiction_playbook_readiness
worker_copyable_municipal_doctrine
```

## 5. Validation behavior

`validate_phase1_review_output(offer_id, reviewed_output)` now rejects:

- unreviewed outputs (`operator_review_status != reviewed`)
- broadened proof labels
- missing `forbidden_claims_preserved=true`
- invalid `outcome_status`, `source_type`, or follow-on trigger values
- empty/non-list evidence summaries
- empty structured next steps

This is intentionally not a full public JSON Schema surface yet. It is a deterministic Python contract plus persisted JSON bundle for the next review-normalizer implementation.

## 6. Test gate

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Result after this slice:

```text
115 passed, 1 warning in 0.13s
```

## 7. Next smallest build

Wire this bundle into a first `phase1_review_normalizer` draft that:

1. accepts operator/admin review-form input,
2. emits one reviewed output matching the offer schema,
3. refuses closure when review-only fields are missing,
4. still does not write durable municipal memory until the reviewed-result/review-artifact promotion gate is satisfied.

If live Acontext remains unavailable, the next proof should stay local/deterministic and produce the first Counter Reality Check reviewed-output fixture.
