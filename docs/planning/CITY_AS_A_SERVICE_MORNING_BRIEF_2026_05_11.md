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
