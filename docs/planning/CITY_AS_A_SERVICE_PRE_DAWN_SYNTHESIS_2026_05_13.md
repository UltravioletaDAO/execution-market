# City-as-a-Service Pre-Dawn Synthesis — 2026-05-13

> Session: 05:00 America/New_York dream synthesis  
> Scope: Execution Market AAS / City-as-a-Service only  
> Priority source: `~/clawd/DREAM-PRIORITIES.md`  
> Stale payload tracks intentionally skipped: AutoJob, Frontier Academy, KK v2, KarmaCadabra v2

## 1. Night synthesis

Tonight moved the adjacent-AAS proof ladder from a single completed sibling package (**Compliance Desk**) into a second reusable family: **Document / Handoff Logistics as a Service**.

The important product connection is that Execution Market now has the same conservative promotion discipline across two distinct AAS families:

```text
narrow concierge offer
-> fixture/review gate
-> local reviewed fixture
-> internal package record
-> read-only operator surface
-> customer-output schema gate
-> internal sample output
-> explicit approval/hold decision
```

Compliance Desk has already reached the explicit hold decision. Document / Handoff now reaches the customer-output schema gate. This proves the ladder is not a one-off compliance artifact; it is becoming a repeatable packaging system for human evidence work that agents can eventually buy safely.

## 2. What landed tonight

### Document / Handoff family boundary

- `document_handoff_fixture_review_gate_landed`
- Instantiated the second adjacent-AAS family at the fixture-spec/review-gate boundary.
- Evidence contract: `document_handoff_proof_run`.
- Still blocked customer/public/dispatch/reputation/live-runtime/location/legal/notarial/custody/worker-doctrine claims.

### Local reviewed fixture

- `document_handoff_local_reviewed_fixture_landed`
- Added one synthetic, non-jurisdiction-specific reviewed fixture over scoped chain-of-custody, pickup/drop-off, source type, receipt/stamp proof, failed-handoff reason, queue/wait boundary, limitations, and next action.

### Internal package record

- `document_handoff_internal_package_record_landed`
- Packaged the reviewed fixture as an internal/admin record with safe and blocked claims preserved side by side.

### Read-only operator surface

- `document_handoff_operator_read_surface_landed`
- Exposed pass-through internal/admin operator cards over package position, evidence contract, reviewed output, limitations, safe claims, and blocked claims.

### Customer-output schema gate

- `document_handoff_customer_output_schema_gate_landed`
- Defined the allowed future customer-output fields while explicitly forbidding exact GPS/raw metadata, private identity/context leakage, legal/notarial/custody/acceptance/filing guarantees, dispatch instructions, reputation receipts, worker-copyable doctrine, and customer/public launch claims.

## 3. Latest implementation surface

Latest code commit before this synthesis:

- `bab3d166 Add document handoff customer schema gate`

Key files:

- `mcp_server/city_ops/document_handoff_customer_output_schema_gate.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/document_handoff_customer_output_schema_gate.json`
- `mcp_server/tests/city_ops/test_document_handoff_customer_output_schema_gate.py`
- `docs/planning/EXECUTION_MARKET_DOCUMENT_HANDOFF_CUSTOMER_OUTPUT_SCHEMA_GATE_IMPLEMENTATION.md`
- `docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`

Verification:

- Focused Document / Handoff schema-gate tests: `12 passed`
- Full Document / Handoff ladder tests: `65 passed`
- Full city-ops suite: `536 passed`

## 4. Strategic connection

Execution Market AAS is now separating three things that are easy to accidentally blur:

1. **Evidence capture** — what a worker actually observed or attempted.
2. **Internal package truth** — what an operator can inspect safely.
3. **Customer language** — what may eventually be shown outside the system.

The Document / Handoff ladder is especially useful because it exercises logistics-style evidence without pretending to be legal service, notarial verification, guaranteed acceptance, identity verification, or custody insurance.

This makes it a strong sibling to Compliance Desk:

- Compliance Desk tests visible-rule / notice / posting-style evidence.
- Document / Handoff tests chain-of-custody / delivery-window / receipt-style evidence.
- Together they prove that AAS can become a family of bounded concierge desks rather than one monolithic city-task marketplace.

## 5. What is still false / blocked

Do not claim any of the following from tonight's work:

- customer copy readiness
- customer delivery approval
- public service catalog readiness
- controlled pilot / customer exposure
- publication approval
- public route registration
- live Acontext sink readiness or runtime parity
- autonomous dispatch / route assignment
- ERC-8004 reputation receipts
- worker Skill DNA
- exact GPS/raw metadata exposure
- legal service, notarial act, private identity verification, guaranteed acceptance, filing success, custody guarantee, or custody outside documented windows
- worker-copyable handoff doctrine

## 6. Daytime recommendations

### Recommendation A — next safest build slice

Create one internal/admin **Document / Handoff sample output** against `document_handoff_customer_output_schema_gate.json`, then record a separate explicit hold/approval decision.

It should still keep:

- publication approval false
- customer delivery false
- dispatch false
- reputation false
- live Acontext/runtime false
- exact GPS/raw metadata exposure false
- legal/notarial/private-identity/custody/acceptance/filing claims false
- worker doctrine false

### Recommendation B — product strategy

Use the two adjacent-AAS families as a product proof:

- Compliance Desk = proof that posting/notice style work can be packaged safely.
- Document / Handoff = proof that logistics/receipt style work can be packaged safely.

Do not rush a public catalog. The strongest demo remains the internal ladder showing exactly what is safe to claim and exactly what is still blocked.

### Recommendation C — if broader AAS planning is desired

The next sibling family should likely be **Incident Verification** because it stresses source-quality, timestamp, media/evidence, and resolution-status boundaries without requiring legal/regulator claims.

## 7. Repo state

- Branch: `feat/operator-route-regret-panel`
- Latest pre-synthesis implementation commit: `bab3d166`
- Full city-ops suite: `536 passed`
- Known untouched untracked repo file: `scripts/sign_req.mjs` (pre-existing; left alone)

## 8. Morning handoff sentence

Execution Market AAS now has a reusable adjacent-service ladder proven across Compliance Desk and Document / Handoff Logistics; Document / Handoff reached the customer-output schema gate tonight, and the next safe daytime move is one internal sample output plus an explicit hold decision — not publication, dispatch, reputation, or customer launch.
