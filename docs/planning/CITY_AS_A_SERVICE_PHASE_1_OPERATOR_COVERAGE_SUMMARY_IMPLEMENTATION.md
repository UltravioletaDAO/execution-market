# City as a Service — Phase 1 Operator Coverage Summary Implementation

> Date: 2026-05-08 23:15 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: implemented local read-only operator/admin seam; no customer, dispatch, live Acontext, legal, regulator, reputation, worker Skill DNA, GPS/metadata, or worker-copyable doctrine readiness claim

## 1. Why this seam exists

The Phase 1 CaaS proof ladder now has one reviewed fixture for each launch offer:

- `counter_reality_check`
- `packet_submission_attempt`
- `posting_compliance_check`

The previous registry summary proved fixture coverage, but the next safe product surface is not customer copy or dispatch automation. The next safe surface is a tiny internal operator/admin summary that answers:

> What Phase 1 offer coverage exists, what can we safely claim, and which readiness claims remain blocked?

This implementation gives operators that answer without reopening raw transcripts, strengthening claims, writing municipal memory, attempting live Acontext transport, exposing exact GPS/metadata, or turning reviewed fixture lessons into worker-copyable municipal doctrine.

## 2. Implemented files

Added:

- `mcp_server/city_ops/phase1_operator_coverage_summary.py`
- `mcp_server/tests/city_ops/test_phase1_operator_coverage_summary.py`

Updated:

- `mcp_server/city_ops/__init__.py`

## 3. Contract

`build_phase1_operator_coverage_summary()` consumes only the already-reviewed registry from:

- `phase1_reviewed_fixture_registry_summary.json`

It refuses sources that are not the reviewed registry schema and marks the derived summary as read-only.

The summary emits:

- source registry id
- reviewed fixture count
- offer count
- whether all Phase 1 offers have reviewed fixture coverage
- one coverage row per offer
- adjacent `safe_to_claim[]` and `do_not_claim_yet[]` at summary level
- adjacent safe/blocked claims per offer row
- explicit false readiness flags
- a conservative verdict: `operator_coverage_summary_landed_read_only_not_customer_ready`

## 4. Earned claim

This seam earns only:

```text
phase1_operator_coverage_summary_landed
```

It preserves the prior registry claim:

```text
phase1_reviewed_fixture_registry_summary_landed
```

## 5. Still blocked

The operator coverage summary explicitly blocks or refuses promotion of:

- `customer_copy_ready`
- `operator_ui_ready`
- `dispatch_routing_ready`
- `dispatch_automation_ready`
- `live_acontext_readiness`
- `acontext_sink_ready`
- `runtime_parity_proven`
- `erc8004_reputation_ready`
- `worker_skill_dna_ready`
- `legal_sufficiency`
- `regulator_acceptance`
- `exact_gps_or_metadata_exposure`
- `worker_copyable_municipal_doctrine`

The implementation also keeps all readiness flags false:

- `customer_copy_ready=false`
- `dispatch_automation_ready=false`
- `live_acontext_ready=false`
- `erc8004_reputation_ready=false`
- `worker_skill_dna_ready=false`
- `legal_sufficiency_claim_allowed=false`
- `regulator_acceptance_claim_allowed=false`
- `gps_or_metadata_exposure_allowed=false`
- `worker_copyable_municipal_doctrine_ready=false`

## 6. Guardrail behavior

The summary fails loudly if:

- the source artifact is not the Phase 1 reviewed fixture registry schema
- fixture counts drift from `coverage_by_offer`
- safe and blocked claim lists stop travelling together
- exact GPS or metadata is exposed
- commercial scope flags are upgraded
- a forbidden readiness claim appears in `safe_to_claim[]`
- safe and blocked claim sets overlap
- per-offer rows drop blocked claims
- per-offer rows promote customer copy, durable municipal memory, Acontext writes, or autonomous dispatch

## 7. Test coverage

Focused verification command:

```bash
cd ~/clawd/projects/execution-market
python3 -m pytest mcp_server/tests/city_ops/test_phase1_operator_coverage_summary.py mcp_server/tests/city_ops/test_phase1_reviewed_fixtures.py -q
```

Observed result:

```text
24 passed, 1 warning
```

The warning is the pre-existing pytest config warning for `asyncio_mode`.

## 8. Product meaning

This is the first safe operator/admin read surface after the fixture registry. It lets a reviewer see that Phase 1 offer coverage exists without making the dangerous leap to:

- public offer copy
- automated dispatch routing
- live memory/Acontext claims
- ERC-8004 reputation or worker Skill DNA updates
- legal/regulator claims
- GPS/metadata exposure
- reusable worker instructions for municipal doctrine

## 9. Next smallest proof

If continuing the AAS/CaaS ladder, the next smallest safe step is one of:

1. Persist this operator summary as a reviewed local artifact and compare build output to file contents, or
2. Render this summary in a thin internal operator/admin read-only endpoint/component that consumes only the generated summary and keeps all readiness flags false.

Do **not** move to customer copy, dispatch automation, live Acontext, reputation, worker Skill DNA, GPS/metadata exposure, or worker-copyable doctrine until a separate parity gate proves claim preservation end-to-end.
