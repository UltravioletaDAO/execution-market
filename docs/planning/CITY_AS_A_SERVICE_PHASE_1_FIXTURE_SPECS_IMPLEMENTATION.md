# City as a Service — Phase 1 Fixture Specs Implementation

> Created: 2026-05-08 00:00 dream session  
> Scope: Execution Market AAS / City-as-a-Service only  
> Parent docs:
> - `CITY_AS_A_SERVICE_PHASE_1_OFFER_CARDS.md`
> - `CITY_AS_A_SERVICE_AAS_PACKAGING_AUDIT_2026_05_07.md`
> - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
> Status: landed fixture-spec contract; no live customer copy changed

## 1. Why this exists

The Phase 1 offer card pack made the first CaaS package sellable as a concierge/operator-reviewed service, but its daytime pickup was still vulnerable to drift:

- a fixture could omit blocked claims while still looking complete
- Packet Submission Attempt could silently broaden beyond the one `redirect_outdated_packet_001` anchor
- customer-output schemas could forget source type, review status, follow-on trigger, or proof label
- a planning-supported card could be mistaken for automation-ready proof

This implementation converts the three offer cards into deterministic fixture specs plus a summary guardrail.

## 2. Files added

Code and tests:

- `mcp_server/city_ops/phase1_offer_fixture_specs.py`
- `mcp_server/tests/city_ops/test_phase1_offer_fixture_specs.py`

Fixture specs:

- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/counter_reality_check.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/packet_submission_attempt.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/posting_compliance_check.json`
- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/phase1_offer_fixture_spec_summary.json`

Export:

- `mcp_server/city_ops/__init__.py` now exports `build_phase1_offer_fixture_spec_summary`.

## 3. What the guardrail enforces

The summary builder validates all three fixture specs before emitting `city_ops.phase1_offer_fixture_spec_summary.v1`.

It fails if any spec:

- is not exactly one of the three Phase 1 offers
- changes the expected proof status label
- drops `operator_review_required=true`
- allows automation claims
- omits required customer-output fields:
  - `source_type`
  - `operator_review_status`
  - `structured_next_step`
  - `follow_on_task_trigger`
  - `proof_status_label`
  - `forbidden_claims_preserved`
- drops any blocked customer claim:
  - guaranteed approval
  - legal sufficiency
  - city relationship or influence
  - unlimited retries
  - broad multi-office base order
  - live Acontext readiness
  - autonomous dispatch readiness
  - multi-jurisdiction playbook readiness
  - worker-copyable municipal doctrine
- moves a blocked claim into `safe_to_claim[]`
- stops preserving safe and blocked claims in the fixture acceptance gate

## 4. Current proof-status labels

| Offer | Proof status after this slice | Meaning |
|---|---|---|
| Counter Reality Check | `planning_supported_needs_first_fixture` | Sellable only as concierge/operator-reviewed; needs first reviewed proof fixture. |
| Packet Submission Attempt | `local_anchor_supported_redirect_outdated_packet_only` | Current proof anchor supports only conservative redirect/outdated-packet behavior. |
| Posting Compliance Check | `planning_supported_needs_first_fixture` | Sellable only as concierge/operator-reviewed; needs first reviewed proof fixture. |

The important nuance is that the packet offer did **not** get upgraded to broad `local_anchor_supported`. The label stays narrow until a non-redirect submission fixture exists.

## 5. Safe claim now earned

Safe to claim internally:

```text
phase_1_offer_fixture_specs_landed
```

Still not safe to claim:

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

## 6. How this connects to the AAS plan

The CaaS/AAS path is now one step closer to a real product loop:

1. offer card defines a bounded concierge SKU
2. fixture spec defines the proof case required before the SKU can claim local support
3. reviewed fixture will later produce a proof block
4. proof block can feed operator memory, dispatch improvement, and eventually Acontext transport

This keeps packaging and proof aligned. The system can sell the concierge service while refusing to overclaim automation, broad jurisdiction readiness, or live memory transport.

## 7. Next smallest proof

Create fixtures in this order:

1. `counter_reality_check` — stale/contradictory online guidance with reviewed source separation.
2. `posting_compliance_check` — wide/close evidence with partial/fail outcome and no GPS/customer metadata exposure.
3. `packet_submission_attempt_non_redirect` — a second packet-submission case that is not the existing redirect/outdated-packet anchor.

Do **not** expand front-door offers, customer copy, live Acontext claims, or worker-copyable guidance before these proof cases exist.

## 8. Test gate

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Expected after this slice: all city-ops tests pass, including the new fixture-spec contract tests.
