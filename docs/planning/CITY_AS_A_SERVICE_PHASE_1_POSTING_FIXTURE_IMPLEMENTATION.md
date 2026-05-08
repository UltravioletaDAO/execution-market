# City as a Service — Phase 1 Posting Compliance Check Reviewed Fixture

> Created: 2026-05-08 04:00 dream session  
> Scope: Execution Market AAS / City-as-a-Service only  
> Parent docs:
> - `CITY_AS_A_SERVICE_PHASE_1_OFFER_CARDS.md`
> - `CITY_AS_A_SERVICE_PHASE_1_FIXTURE_SPECS_IMPLEMENTATION.md`
> - `CITY_AS_A_SERVICE_PHASE_1_REVIEW_OUTPUT_SCHEMAS.md`
> - `CITY_AS_A_SERVICE_PHASE_1_REVIEW_NORMALIZER_IMPLEMENTATION.md`
> - `CITY_AS_A_SERVICE_PHASE_1_COUNTER_REALITY_FIXTURE_IMPLEMENTATION.md`
> Status: landed second local reviewed proof fixture; no live customer copy, memory write, or recurring compliance claim

## 1. Why this slice exists

The Phase 1 CaaS pack had one reviewed fixture for Counter Reality Check. That proved a stale-guidance redirect path, but it did not yet prove a visual/evidence-heavy compliance path.

This slice adds the first `posting_compliance_check` reviewed fixture:

> single-site posting visible from context evidence → close/legibility incomplete → reviewed partial result → bounded posting recheck.

The purpose is not to claim compliance automation. The purpose is to prove that a posting proof can stay useful while still preserving access constraints, evidence limits, and the exact anti-doxxing / anti-overclaim boundaries the product needs.

## 2. Files changed

Code and tests:

- `mcp_server/city_ops/phase1_reviewed_fixtures.py`
- `mcp_server/tests/city_ops/test_phase1_reviewed_fixtures.py`
- `mcp_server/city_ops/__init__.py`

Persisted fixture artifact:

- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/posting_compliance_check_partial_legibility_001.json`

## 3. What the fixture proves

The fixture is a synthetic, non-jurisdiction-specific reviewed example with:

1. offer: `posting_compliance_check`,
2. outcome status: `verified_partial`,
3. source type: `observed`,
4. checklist result: `partial_visibility_legibility_not_confirmed`,
5. wide/context evidence present,
6. close/legibility evidence limited,
7. access angle constraint preserved,
8. exact GPS / metadata exposure explicitly false,
9. follow-on trigger: `posting_recheck`,
10. proof label preserved: `planning_supported_needs_first_fixture`,
11. forbidden claims preserved: `true`.

It passes `validate_phase1_review_output("posting_compliance_check", reviewed_output)` and the reviewed-fixture promotion gate.

## 4. What it deliberately does not claim

Still not safe to claim:

```text
live_customer_schema_contract
autonomous_review_closure
durable_municipal_memory_write
live_acontext_readiness
autonomous_dispatch_readiness
multi_jurisdiction_playbook_readiness
worker_copyable_municipal_doctrine
guaranteed_approval
legal_sufficiency
city_relationship_or_influence
unlimited_retries
broad_multi_office_base_order
```

The fixture explicitly records:

- `customer_copy_changed=false`
- `durable_municipal_memory_write_performed=false`
- `acontext_write_performed=false`
- `autonomous_dispatch_enabled=false`
- `exact_gps_or_metadata_exposed=false`

## 5. Earned label

```text
posting_compliance_check_reviewed_fixture_landed
```

This is a local fixture/proof-support claim only. It means one reviewed Posting Compliance Check output exists and validates. It does not mean a recurring posting-compliance service is live, legally sufficient, automated, or regulator-accepted.

## 6. Late-night pattern insight

The useful connection is not "add more city task types." The compounding loop is:

```text
offer card → fixture spec → reviewed-output schema → normalizer → reviewed fixture → registry/observability → runtime consumer
```

Counter Reality Check and Posting Compliance Check now exercise two different proof muscles:

- **contradictory knowledge**: stale public guidance vs current counter reality
- **visual compliance evidence**: presence/legibility/access constraints without metadata exposure

That matters for broader Execution Market strategy because worker history should become Skill DNA only after reviewed proof boundaries are stable. IRC/chat coordination can suggest promising routes, but the durable multiplier is a replayable artifact that carries safe claims and blocked claims together.

## 7. Test gate

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Latest result after this slice:

```text
135 passed, 1 warning in 0.14s
```

## 8. Next smallest proof

If live Acontext remains blocked:

1. create one non-redirect Packet Submission Attempt reviewed fixture,
2. add a tiny reviewed-fixture registry/summary so operator surfaces can count which Phase 1 offers have local proof support,
3. only then consider customer-copy or UI surfaces, and only with `do_not_claim_yet[]` traveling beside `safe_to_claim[]`.

If Docker/local Acontext/SDK/API/dashboard become available, run exactly one live write/retrieve parity pass from the existing transport packet before claiming live transport readiness.
