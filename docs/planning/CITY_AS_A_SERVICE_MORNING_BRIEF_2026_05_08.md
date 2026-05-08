# City as a Service — Morning Brief 2026-05-08

> Scope: Execution Market AAS / City-as-a-Service only  
> Dream priority: followed `~/clawd/DREAM-PRIORITIES.md`; did not work on AutoJob, Frontier Academy, KK v2, or KarmaCadabra v2.  
> Branch: `feat/operator-route-regret-panel`

## 1. 00:00 dream output — Phase 1 fixture specs

The Phase 1 offer card pack now has deterministic fixture specs and tests.

Added:

- `mcp_server/city_ops/phase1_offer_fixture_specs.py`
- `mcp_server/tests/city_ops/test_phase1_offer_fixture_specs.py`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/counter_reality_check.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/packet_submission_attempt.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/posting_compliance_check.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/phase1_offer_fixture_spec_summary.json`
- `docs/planning/CITY_AS_A_SERVICE_PHASE_1_FIXTURE_SPECS_IMPLEMENTATION.md`

Updated:

- `mcp_server/city_ops/__init__.py`
- `docs/planning/CITY_AS_A_SERVICE_PHASE_1_OFFER_CARDS.md`
- `docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
- `docs/internal/planning/CITY_AS_A_SERVICE_IMPLEMENTATION_BACKLOG_AND_DECISIONS.md`

## 2. Earned label

```text
phase_1_offer_fixture_specs_landed
```

This is an internal packaging/proof-support claim only.

## 3. Still not safe to claim

```text
guaranteed_approval
legal_sufficiency
city_relationship_or_influence
unlimited_retries
broad_multi_office_base_order
live_acontext_readiness
autonomous_dispatch_readiness
multi_jurisdiction_playbook_readiness
worker_copyable_municipal_doctrine
```

Also still blocked from previous CaaS proof work:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
runtime_parity_proven
acontext_live_transport_parity_landed
worker-copyable municipal doctrine
```

## 4. Why it matters

The AAS packaging stack can now move from offer-card prose to fixture-backed proof without ambiguity.

The guardrail fails if a future builder:

- broadens Packet Submission Attempt beyond the current redirect/outdated-packet anchor
- drops `source_type`, `operator_review_status`, `structured_next_step`, `follow_on_task_trigger`, `proof_status_label`, or `forbidden_claims_preserved`
- moves blocked claims into `safe_to_claim[]`
- implies automation, live Acontext readiness, multi-jurisdiction readiness, or worker-copyable municipal doctrine

## 5. 01:00 dream output — Phase 1 review-output schemas

The fixture specs now have a deterministic reviewed-output schema bundle before the review normalizer exists.

Added:

- `mcp_server/city_ops/phase1_review_output_schemas.py`
- `mcp_server/tests/city_ops/test_phase1_review_output_schemas.py`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/phase1_review_output_schema_bundle.json`
- `docs/planning/CITY_AS_A_SERVICE_PHASE_1_REVIEW_OUTPUT_SCHEMAS.md`

Updated:

- `mcp_server/city_ops/__init__.py`

New earned label:

```text
phase_1_review_output_schema_drafts_landed
```

This remains an internal schema/review contract only. It does not claim `review_normalizer_landed`, live customer schema readiness, autonomous review closure, or live Acontext readiness.

## 6. Next smallest proof/build

If local Acontext infra is still blocked, use this order:

1. Wire `phase1_review_output_schema_bundle.json` into a first review normalizer draft.
2. Create the first Counter Reality Check reviewed-output proof fixture.
3. Create the first Posting Compliance Check reviewed-output proof fixture.
4. Create the Non-redirect Packet Submission Attempt proof fixture.

If Docker/local Acontext/SDK/API/dashboard become available, run the already-defined live write/retrieve parity pass before claiming any live transport readiness.

## 7. Test gate

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Latest result after the 01:00 slice: `115 passed, 1 warning in 0.13s`.

## 8. 03:00 dream output — First Counter Reality Check reviewed fixture

The Phase 1 CaaS pack now has its first concrete reviewed proof fixture.

Added:

- `mcp_server/city_ops/phase1_reviewed_fixtures.py`
- `mcp_server/tests/city_ops/test_phase1_reviewed_fixtures.py`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/counter_reality_check_redirect_outdated_packet_001.json`
- `docs/planning/CITY_AS_A_SERVICE_PHASE_1_COUNTER_REALITY_FIXTURE_IMPLEMENTATION.md`

Updated:

- `mcp_server/city_ops/__init__.py`

New earned label:

```text
counter_reality_check_reviewed_fixture_landed
```

This remains a local fixture/proof-support claim only. It proves that one synthetic Counter Reality Check case can move through the normalizer and reviewed-output schema with source separation, an operator-reviewed redirect result, and a bounded follow-on trigger.

## 9. Still not safe to claim after 03:00

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

The fixture explicitly keeps these false:

```text
customer_copy_changed=false
durable_municipal_memory_write_performed=false
acontext_write_performed=false
autonomous_dispatch_enabled=false
```

## 10. Next smallest proof/build after 03:00

If local Acontext infra is still blocked, use this order:

1. Create the first Posting Compliance Check reviewed fixture.
2. Create one non-redirect Packet Submission Attempt fixture.
3. Add a small reviewed-fixture registry/summary so operator surfaces can count which Phase 1 offers have local proof support.

If Docker/local Acontext/SDK/API/dashboard become available, run exactly one live write/retrieve parity pass before claiming any live transport readiness.

## 11. 04:00 dream output — First Posting Compliance Check reviewed fixture

The Phase 1 CaaS pack now has its second concrete reviewed proof fixture.

Added:

- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/posting_compliance_check_partial_legibility_001.json`
- `docs/planning/CITY_AS_A_SERVICE_PHASE_1_POSTING_FIXTURE_IMPLEMENTATION.md`

Updated:

- `mcp_server/city_ops/phase1_reviewed_fixtures.py`
- `mcp_server/tests/city_ops/test_phase1_reviewed_fixtures.py`
- `mcp_server/city_ops/__init__.py`

New earned label:

```text
posting_compliance_check_reviewed_fixture_landed
```

This remains a local fixture/proof-support claim only. It proves that one synthetic Posting Compliance Check case can move through the normalizer and reviewed-output schema with observed-only source type, a partial result, wide/close evidence boundaries, access-constraint preservation, and a bounded `posting_recheck` trigger.

## 12. Still not safe to claim after 04:00

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

The fixture explicitly keeps these false:

```text
customer_copy_changed=false
durable_municipal_memory_write_performed=false
acontext_write_performed=false
autonomous_dispatch_enabled=false
exact_gps_or_metadata_exposed=false
```

## 13. 04:00 pattern insight

The strongest multiplier tonight is the reviewed-fixture chain, not more planning surface area:

```text
offer card → fixture spec → reviewed-output schema → normalizer → reviewed fixture → registry/observability → runtime consumer
```

Counter Reality Check and Posting Compliance Check now cover two different evidence regimes:

- contradictory/stale municipal knowledge,
- visual posting evidence with access and privacy constraints.

That is the useful bridge to broader agent coordination: IRC/chat can surface route ideas, but only replayable reviewed artifacts should graduate into worker Skill DNA, ERC-8004 reputation signals, dispatch routing, or Acontext memory. The safe claim and blocked claim must travel together at every hop.

## 14. Next smallest proof/build after 04:00

If local Acontext infra is still blocked, use this order:

1. Create one non-redirect Packet Submission Attempt reviewed fixture.
2. Add a tiny reviewed-fixture registry/summary for operator observability.
3. Only then consider customer-copy or UI surfaces, and only with blocked claims preserved beside safe labels.

If Docker/local Acontext/SDK/API/dashboard become available, run exactly one live write/retrieve parity pass before claiming any live transport readiness.

## 15. Latest test gate

```bash
python3 -m py_compile mcp_server/city_ops/phase1_reviewed_fixtures.py mcp_server/tests/city_ops/test_phase1_reviewed_fixtures.py
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Result after the 04:00 slice:

```text
135 passed, 1 warning in 0.14s
```
