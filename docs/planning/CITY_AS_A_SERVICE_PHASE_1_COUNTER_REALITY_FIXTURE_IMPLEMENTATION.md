# City as a Service — Phase 1 Counter Reality Check Reviewed Fixture

> Created: 2026-05-08 03:00 dream session  
> Scope: Execution Market AAS / City-as-a-Service only  
> Parent docs:
> - `CITY_AS_A_SERVICE_PHASE_1_OFFER_CARDS.md`
> - `CITY_AS_A_SERVICE_PHASE_1_FIXTURE_SPECS_IMPLEMENTATION.md`
> - `CITY_AS_A_SERVICE_PHASE_1_REVIEW_OUTPUT_SCHEMAS.md`
> - `CITY_AS_A_SERVICE_PHASE_1_REVIEW_NORMALIZER_IMPLEMENTATION.md`
> Status: landed first local reviewed proof fixture; no live customer copy or memory write

## 1. Why this slice exists

The Phase 1 offer cards, fixture specs, reviewed-output schemas, and review normalizer were all present, but the pack still lacked a concrete reviewed output.

This slice materializes the first proof fixture for the safest hero offer:

> Counter Reality Check → contradictory/stale guidance → reviewed redirect result → bounded next step.

The purpose is not to claim live city automation. The purpose is to prove that the deterministic local contract can carry a reviewed municipal answer without losing source separation or upgrading a redirect into certainty.

## 2. Files added

Code and tests:

- `mcp_server/city_ops/phase1_reviewed_fixtures.py`
- `mcp_server/tests/city_ops/test_phase1_reviewed_fixtures.py`

Persisted fixture artifact:

- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/counter_reality_check_redirect_outdated_packet_001.json`

Export updated:

- `mcp_server/city_ops/__init__.py`

## 3. What the fixture proves

The fixture is a synthetic, non-jurisdiction-specific reviewed example with:

1. stale public guidance as a documented source,
2. observed signage as a separate source,
3. staff-heard redirect as a separate source,
4. operator-reviewed outcome status: `redirected`,
5. source type: `mixed`,
6. bounded follow-on trigger: `office_redirect_follow_through`,
7. proof label preserved: `planning_supported_needs_first_fixture`,
8. forbidden claims preserved: `true`.

It passes the same `validate_phase1_review_output("counter_reality_check", reviewed_output)` contract used by the review normalizer.

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
```

The fixture explicitly records:

- `customer_copy_changed=false`
- `durable_municipal_memory_write_performed=false`
- `acontext_write_performed=false`
- `autonomous_dispatch_enabled=false`

## 5. Earned label

```text
counter_reality_check_reviewed_fixture_landed
```

This is a local fixture/proof-support claim only. It means the first Counter Reality Check reviewed output exists and validates. It does not mean the offer is live, automated, legally sufficient, or Acontext-backed.

## 6. Why this compounds the AAS plan

The Phase 1 chain now has its first concrete artifact:

1. offer card bounds the SKU,
2. fixture spec defines the proof shape,
3. reviewed-output schema defines the closure fields,
4. normalizer turns operator review into schema-valid output,
5. reviewed fixture proves the path with a redirect/outdated-guidance case.

This gives later runtime work something real to replay through promotion gates, observability, Acontext transport, and decision-support surfaces.

## 7. Test gate

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Expected after this slice: full `city_ops` suite passes.

## 8. Next smallest proof

If live Acontext remains blocked:

1. create the Posting Compliance Check reviewed fixture,
2. create one non-redirect Packet Submission Attempt fixture,
3. then add a tiny fixture summary/registry so operator surfaces can count which Phase 1 offers have local proof support.

If Docker/local Acontext/SDK/API/dashboard become available, run exactly one live write/retrieve parity pass from the existing transport packet before claiming live transport readiness.
