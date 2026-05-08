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

## 5. Next smallest proof

If local Acontext infra is still blocked, use this fixture order:

1. Counter Reality Check proof fixture.
2. Posting Compliance Check proof fixture.
3. Non-redirect Packet Submission Attempt proof fixture.

If Docker/local Acontext/SDK/API/dashboard become available, run the already-defined live write/retrieve parity pass before claiming any live transport readiness.

## 6. Test gate

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Expected after this slice: all city-ops tests pass, including the new Phase 1 fixture-spec tests.
