# City as a Service — Morning Brief 2026-05-11

> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`  
> Current branch: `feat/operator-route-regret-panel`

## 00:00 dream implementation — remaining Phase 1 package records

The stale cron payload still listed AutoJob, Frontier Academy, KK v2, and KarmaCadabra work, but `DREAM-PRIORITIES.md` explicitly stops those during dreams. Work stayed on Execution Market AAS / City-as-a-Service.

### What landed

- Added `mcp_server/city_ops/phase1_remaining_offer_internal_package_records.py`
  - `build/load/write_phase1_counter_reality_check_internal_package_record`
  - `build/load/write_phase1_posting_compliance_internal_package_record`
- Added persisted artifacts:
  - `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_counter_reality_check_internal_package_record.json`
  - `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_posting_compliance_internal_package_record.json`
- Updated `mcp_server/city_ops/phase1_controlled_pilot_readiness_board.py`
  - now consumes all three Phase 1 internal package records
  - now reports `all_phase1_offers_have_internal_package_record=true`
  - still keeps customer/pilot/public/live/runtime/dispatch/reputation/privacy/worker-doctrine readiness false
- Updated persisted readiness board:
  - `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_controlled_pilot_readiness_board.json`
- Added tests:
  - `mcp_server/tests/city_ops/test_phase1_remaining_offer_internal_package_records.py`
  - updated `mcp_server/tests/city_ops/test_phase1_controlled_pilot_readiness_board.py`
- Updated docs:
  - `CITY_AS_A_SERVICE_PHASE_1_REMAINING_INTERNAL_PACKAGE_RECORDS_IMPLEMENTATION.md`
  - `CITY_AS_A_SERVICE_PHASE_1_CONTROLLED_PILOT_READINESS_BOARD_IMPLEMENTATION.md`
  - `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`

### Safe to claim

- `phase1_counter_reality_check_internal_package_record_landed`
- `phase1_posting_compliance_internal_package_record_landed`
- all three Phase 1 City Counter Ops offers now have internal package records
- the controlled-pilot readiness board can count package-record coverage internally

### Do not claim

- customer copy readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- live Acontext readiness / sink readiness
- runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004 reputation readiness
- worker Skill DNA or worker-copyable municipal doctrine
- legal/regulator acceptance
- filing success, broad office reuse, city relationship, or approval guarantees
- exact GPS/raw metadata exposure

### Verification

Focused gate:

```bash
python3 -m py_compile \
  mcp_server/city_ops/phase1_remaining_offer_internal_package_records.py \
  mcp_server/city_ops/phase1_controlled_pilot_readiness_board.py \
  mcp_server/city_ops/__init__.py \
  mcp_server/tests/city_ops/test_phase1_remaining_offer_internal_package_records.py \
  mcp_server/tests/city_ops/test_phase1_controlled_pilot_readiness_board.py
PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_phase1_remaining_offer_internal_package_records.py \
  mcp_server/tests/city_ops/test_phase1_controlled_pilot_readiness_board.py -q
# 25 passed, 2 warnings
```

Full city-ops gate:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 278 passed, 2 warnings
```

### Next smallest safe step

If live Acontext prerequisites remain blocked, the next narrow proof-support step is:

1. Add a separate internal customer-output schema review gate over the three internal package records.
2. Require all three records to preserve operator review, blocked-claim adjacency, and false readiness flags.
3. Fail closed on customer/pilot/public language, exact GPS/raw metadata exposure, readiness promotion, worker-copyability strengthening, or route-wrapper drift.
4. Keep live Acontext, runtime parity, dispatch, reputation, privacy, and worker-doctrine gates separate.

Do not add another route wrapper by default.

---

## 01:00 dream implementation — customer-output schema review gate

The stale cron payload again listed AutoJob, Frontier Academy, KK v2, and other stopped tracks. `DREAM-PRIORITIES.md` explicitly blocks those during dreams, so this slice stayed on Execution Market AAS / City-as-a-Service.

### What landed

- Added `mcp_server/city_ops/phase1_customer_output_schema_review_gate.py`
  - `build/load/write_phase1_customer_output_schema_review_gate`
  - consumes the three Phase 1 internal package records only
  - defines a schema-only boundary for future customer outputs
  - fails closed on readiness promotion, customer copy creation, dropped blocked claims, forbidden safe claims, field drift, field overlap, and source package drift
- Added persisted artifact:
  - `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_customer_output_schema_review_gate.json`
- Added tests:
  - `mcp_server/tests/city_ops/test_phase1_customer_output_schema_review_gate.py`
- Updated exports in `mcp_server/city_ops/__init__.py`
- Added implementation doc:
  - `CITY_AS_A_SERVICE_PHASE_1_CUSTOMER_OUTPUT_SCHEMA_REVIEW_GATE_IMPLEMENTATION.md`

### Safe to claim

- `phase1_customer_output_schema_review_gate_landed`
- the internal schema boundary for future Phase 1 customer-output samples exists
- allowed/forbidden customer-output fields are now machine-checked as an internal/admin artifact

### Do not claim

- customer copy readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- live Acontext readiness / sink readiness
- runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004 reputation readiness
- worker Skill DNA or worker-copyable municipal doctrine
- legal/regulator acceptance
- filing success, broad office reuse, city relationship, or approval guarantees
- exact GPS/raw metadata exposure

### Verification

Focused gate:

```bash
python3 -m py_compile \
  mcp_server/city_ops/phase1_customer_output_schema_review_gate.py \
  mcp_server/city_ops/__init__.py \
  mcp_server/tests/city_ops/test_phase1_customer_output_schema_review_gate.py
PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_phase1_customer_output_schema_review_gate.py -q
# 11 passed, 2 warnings
```

Full city-ops gate:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 289 passed, 2 warnings
```

### Next smallest safe step

Draft one operator-reviewed sample output per Phase 1 offer against this schema, with separate privacy/legal/non-guarantee review.

Do not publish samples, route them publicly, dispatch from them, or claim pilot/customer/catalog readiness. Live Acontext, runtime parity, dispatch, reputation, GPS/raw metadata privacy, pilot exposure, and worker-doctrine gates remain separate.

---

## 02:00 dream implementation — operator-reviewed sample outputs

The stale cron payload again listed AutoJob, Frontier Academy, KK v2, and other stopped tracks. `DREAM-PRIORITIES.md` explicitly blocks those during dreams, so this slice stayed on Execution Market AAS / City-as-a-Service.

### What landed

- Added `mcp_server/city_ops/phase1_operator_reviewed_sample_outputs.py`
  - `build/load/write_phase1_operator_reviewed_sample_outputs`
  - consumes only `phase1_customer_output_schema_review_gate.json`
  - creates one internal/admin sample output per Phase 1 offer
  - keeps the samples as wording-shape review artifacts, not customer copy
  - requires separate privacy-boundary, legal-advice exclusion, and non-guarantee-language review flags
  - keeps operator publish approval and customer delivery approval false
  - fails closed on readiness promotion, forbidden safe claims, missing blocked claims, forbidden field drift, publishability flips, and removed review gates
- Added persisted artifact:
  - `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_operator_reviewed_sample_outputs.json`
- Added tests:
  - `mcp_server/tests/city_ops/test_phase1_operator_reviewed_sample_outputs.py`
- Updated exports in `mcp_server/city_ops/__init__.py`
- Added implementation doc:
  - `CITY_AS_A_SERVICE_PHASE_1_OPERATOR_REVIEWED_SAMPLE_OUTPUTS_IMPLEMENTATION.md`

### Safe to claim

- `phase1_operator_reviewed_sample_outputs_landed`
- one internal/admin sample output exists for each Phase 1 offer
- sample fields are constrained to the customer-output schema gate
- privacy/legal-advice-exclusion/non-guarantee review flags are machine-checked

### Do not claim

- customer copy readiness
- sample publication readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- live Acontext readiness / sink readiness
- runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004 reputation readiness
- worker Skill DNA or worker-copyable municipal doctrine
- legal/regulator acceptance
- filing success, broad office reuse, city relationship, or approval guarantees
- exact GPS/raw metadata exposure

### Verification

Focused gate:

```bash
PYTHONPATH=. python3 -m pytest \
  mcp_server/tests/city_ops/test_phase1_operator_reviewed_sample_outputs.py -q
# 11 passed, 2 warnings
```

Full city-ops gate:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
# 300 passed, 2 warnings
```

### Next smallest safe step

If Saúl wants customer-facing Phase 1 copy, add a tiny publication-approval checklist over these internal samples only.

Do not publish samples, route them publicly, dispatch from them, attach reputation receipts, expose exact GPS/raw metadata, or claim pilot/customer/catalog readiness by default. Live Acontext, runtime parity, dispatch, reputation, GPS/privacy, pilot exposure, and worker-doctrine gates remain separate.

---

## 03:00 dream implementation — sample publication approval checklist

The stale cron payload again listed AutoJob, Frontier Academy, KK v2, and other stopped tracks. `DREAM-PRIORITIES.md` explicitly blocks those during dreams, so this slice stayed on Execution Market AAS / City-as-a-Service.

### What landed

- Added `mcp_server/city_ops/phase1_sample_publication_approval_checklist.py`
  - `build/load/write_phase1_sample_publication_approval_checklist`
  - consumes only `phase1_operator_reviewed_sample_outputs.json`
  - verifies the source samples remain internal/admin only and not publishable
  - names pre-publication gates for privacy, legal-advice exclusion, non-guarantee language, evidence redaction, exact GPS/raw metadata exclusion, and no dispatch/reputation claim
  - keeps operator publish approval, customer delivery approval, and publication approval false
  - fails closed on readiness promotion, forbidden safe claims, source publishability drift, approval flips, missing blocked claims, and offer-review publication drift
- Added persisted artifact:
  - `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_sample_publication_approval_checklist.json`
- Added tests:
  - `mcp_server/tests/city_ops/test_phase1_sample_publication_approval_checklist.py`
- Updated exports in `mcp_server/city_ops/__init__.py`
- Added implementation doc:
  - `CITY_AS_A_SERVICE_PHASE_1_SAMPLE_PUBLICATION_APPROVAL_CHECKLIST_IMPLEMENTATION.md`

### Safe to claim

- `phase1_sample_publication_approval_checklist_landed`
- an internal/admin checklist exists over the Phase 1 sample outputs
- publication prerequisites are explicit and machine-checked as **not yet approved**

### Do not claim

- publication approval readiness
- sample output publication readiness
- customer copy creation/readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- live Acontext readiness / sink readiness
- runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004 reputation readiness
- worker Skill DNA or worker-copyable municipal doctrine
- legal/regulator acceptance
- filing success, broad office reuse, city relationship, or approval guarantees
- exact GPS/raw metadata exposure

### Verification

Focused gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_phase1_sample_publication_approval_checklist.py
# 12 passed
```

Full city-ops gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 312 passed
```

### Next smallest safe step

If Saúl wants customer-facing Phase 1 copy, create one draft packet that consumes this checklist and still keeps `publication_approved=false` until explicit operator review is recorded.

Do not publish samples, route them publicly, dispatch from them, attach reputation receipts, expose exact GPS/raw metadata, or claim pilot/customer/catalog readiness by default. Live Acontext, runtime parity, dispatch, reputation, GPS/privacy, pilot exposure, and worker-doctrine gates remain separate.

---

## 04:00 dream implementation — customer-facing draft packet, still unapproved

The cron payload again listed stopped tracks, but `~/clawd/DREAM-PRIORITIES.md` explicitly blocks AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dreams. This slice stayed inside Execution Market AAS / City-as-a-Service.

### What landed

- Added `mcp_server/city_ops/phase1_customer_facing_draft_packet.py`
  - `build/load/write_phase1_customer_facing_draft_packet`
  - consumes only `phase1_sample_publication_approval_checklist.json`
  - creates one internal/admin draft card per Phase 1 offer
  - keeps the packet copy-shaped but **not customer copy**, not approved, and not publishable
  - fails closed on source approval-gate promotion, publication approval, offer publishability, forbidden safe claims, missing blocked claims, and draft-card readiness drift
- Added persisted artifact:
  - `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_customer_facing_draft_packet.json`
- Added tests:
  - `mcp_server/tests/city_ops/test_phase1_customer_facing_draft_packet.py`
- Updated exports in `mcp_server/city_ops/__init__.py`
- Added implementation doc:
  - `CITY_AS_A_SERVICE_PHASE_1_CUSTOMER_FACING_DRAFT_PACKET_IMPLEMENTATION.md`

### Safe to claim

- `phase1_customer_facing_draft_packet_landed`
- an internal/admin draft-review packet exists over the Phase 1 sample-publication checklist
- each Phase 1 offer has a draft card requiring pre-send review gates

### Do not claim

- draft packet publication readiness
- publication approval/readiness
- sample output publication readiness
- customer copy creation/readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- live Acontext readiness / sink readiness
- runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004 reputation readiness
- worker Skill DNA or worker-copyable municipal doctrine
- legal/regulator acceptance
- filing success, broad office reuse, city relationship, or approval guarantees
- exact GPS/raw metadata exposure

### Verification

Focused gate:

```bash
/opt/homebrew/bin/python3.14 -m py_compile \
  mcp_server/city_ops/phase1_customer_facing_draft_packet.py \
  mcp_server/city_ops/__init__.py \
  mcp_server/tests/city_ops/test_phase1_customer_facing_draft_packet.py
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_phase1_customer_facing_draft_packet.py
# 12 passed
```

Full city-ops gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 324 passed
```

### Next smallest safe step

Record an explicit operator review decision against the draft packet. Do not flip `publication_approved` without a separate approval artifact, and do not expose a public/customer route by default.

---

## 05:00 pre-dawn synthesis — draft packet hold decision

The cron payload requested old AutoJob/Frontier/KK work, but `~/clawd/DREAM-PRIORITIES.md` explicitly says those tracks are stopped during dreams. The 5 AM synthesis stayed on Execution Market AAS / City-as-a-Service and connected the Phase 1 customer-output ladder into a daytime-safe handoff.

### What landed

- Added `mcp_server/city_ops/phase1_draft_packet_operator_review_decision.py`
  - `build/load/write_phase1_draft_packet_operator_review_decision`
  - consumes only `phase1_customer_facing_draft_packet.json`
  - records `review_decision=hold_not_approved_not_publishable`
  - keeps `operator_review_recorded=true` while `operator_review_granted=false`
  - holds every offer card for explicit human operator review
  - fails closed on source readiness promotion, offer-card publishability, forbidden safe claims, missing blocked claims, and approval/readiness drift
- Added persisted artifact:
  - `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_draft_packet_operator_review_decision.json`
- Added tests:
  - `mcp_server/tests/city_ops/test_phase1_draft_packet_operator_review_decision.py`
- Updated exports in `mcp_server/city_ops/__init__.py`
- Added implementation doc:
  - `CITY_AS_A_SERVICE_PHASE_1_DRAFT_PACKET_OPERATOR_REVIEW_DECISION_IMPLEMENTATION.md`

### Safe to claim

- `phase1_draft_packet_operator_review_decision_landed`
- an internal/admin hold decision exists over the Phase 1 draft packet
- the draft packet has been explicitly kept out of publication/customer-delivery readiness
- offer cards are held for human operator approval rather than promoted by default

### Do not claim

- operator review approval/grant
- operator publish approval
- customer delivery approval
- draft packet publication readiness
- publication approval/readiness
- sample output publication readiness
- customer copy creation/readiness
- customer-visible catalog readiness
- public service catalog readiness
- controlled concierge pilot readiness
- customer pilot exposure
- front-door SKU readiness
- live Acontext readiness / sink readiness
- runtime parity
- autonomous dispatch or dispatch routing
- ERC-8004 reputation readiness
- worker Skill DNA or worker-copyable municipal doctrine
- legal/regulator acceptance
- filing success, broad office reuse, city relationship, or approval guarantees
- exact GPS/raw metadata exposure

### Verification

Focused gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_phase1_draft_packet_operator_review_decision.py
# 12 passed
```

Full city-ops gate:

```bash
/opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 336 passed
```

### Daytime recommendation

The Phase 1 customer-output ladder is now coherent enough to hand to Saúl without adding another route or public surface:

1. internal package records for all three offers,
2. customer-output schema review gate,
3. operator-reviewed sample outputs,
4. sample publication checklist,
5. copy-shaped draft packet,
6. explicit hold decision.

If Saúl wants customer-facing exposure, the next artifact should be a **separate human operator approval record** for exactly one offer card. It should name approved text, passed redactions, delivery path, and still-blocked claims. Do not flip `publication_approved`, expose a public route, dispatch, attach reputation receipts, or claim catalog/pilot readiness from the hold decision.
