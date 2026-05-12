# City-as-a-Service Pre-Dawn Synthesis — 2026-05-12

> Session: 05:00 America/New_York dream synthesis
> Scope: Execution Market AAS / City-as-a-Service only
> Priority source: `~/clawd/DREAM-PRIORITIES.md`
> Stale payload tracks intentionally skipped: AutoJob, Frontier Academy, KK v2, KarmaCadabra v2

## 1. Night synthesis

Tonight moved the CaaS proof discipline from a single municipal Phase 1 ladder into the first reusable adjacent-AAS family: **Compliance Desk as a Service**.

The important connection is not the specific compliance example. The product lesson is the ladder:

1. define a narrow concierge offer
2. freeze fixture/review evidence requirements
3. create one local reviewed fixture
4. package it internally
5. expose it to an operator as read-only data
6. only then consider customer-output schema, samples, and explicit approval/hold decisions

That pattern is now encoded in code and fixtures, not just prose.

## 2. What landed tonight

### Phase 1 customer delivery discipline

- `phase1_approved_offer_customer_delivery_hold_checklist_landed`
- One text-boundary-approved offer (`counter_reality_check`) now has a delivery hold checklist.
- Customer delivery remains **not authorized**.

### Adjacent-AAS reusable ladder

- `aas_minimum_ladder_template_landed`
- Defines the promotion sequence for:
  - Compliance Desk
  - Property / Permit Desk
  - Incident Verification
  - Document / Handoff Logistics
  - Procurement / Admin Ops

### Compliance Desk first-family ladder

- `compliance_desk_fixture_review_gate_landed`
- `compliance_desk_local_reviewed_fixture_landed`
- `compliance_desk_internal_package_record_landed`
- `compliance_desk_operator_read_surface_landed`

The current Compliance Desk slice is now internally visible to an operator as read-only cards over package position, evidence contract, reviewed output, limitations, safe claims, and blocked claims.

## 3. Latest implementation surface

Latest commit:

- `a686a799 feat: add compliance desk read surface`

Key files:

- `mcp_server/city_ops/compliance_desk_operator_read_surface.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/compliance_desk_operator_read_surface.json`
- `mcp_server/tests/city_ops/test_compliance_desk_operator_read_surface.py`
- `docs/planning/EXECUTION_MARKET_COMPLIANCE_DESK_OPERATOR_READ_SURFACE_IMPLEMENTATION.md`
- `docs/planning/CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`

Verification:

- Focused Compliance Desk read-surface + package tests: `25 passed`
- Full city-ops suite: `431 passed`

## 4. Strategic connection

Compliance Desk is becoming the repeatable proof template for AAS expansion:

- **CaaS gives the primitive:** reviewed local task evidence and operator-held truth.
- **AAS packages give the product shape:** narrow desk-like services agents can buy.
- **Read-only operator surfaces give the control plane:** humans/operators can inspect packages without accidentally publishing, dispatching, or converting them into legal claims.

This is the right direction for Execution Market because it packages human evidence work into safe, composable service families without overclaiming automation.

## 5. What is still false / blocked

Do not claim any of the following from tonight's work:

- customer copy readiness
- customer delivery approval
- public service catalog readiness
- controlled pilot / customer exposure
- publication approval
- live Acontext sink readiness or runtime parity
- autonomous dispatch / route assignment
- ERC-8004 reputation receipts
- worker Skill DNA
- exact GPS/raw metadata exposure
- legal compliance, legal sufficiency, regulator acceptance, official inspection, continuous monitoring, filing success, city influence, or guaranteed approval
- worker-copyable compliance doctrine

## 6. Daytime recommendations

### Recommendation A — next safest build slice

Create a **Compliance Desk customer-output schema gate** that consumes `compliance_desk_operator_read_surface.json` and defines allowed future customer-output fields.

It should still keep:

- publication approval false
- customer delivery false
- dispatch false
- reputation false
- live Acontext/runtime false
- GPS/raw metadata exposure false
- legal/regulator claims false
- worker doctrine false

### Recommendation B — product strategy

Treat Compliance Desk as the first adjacent-AAS family, but do not rush public UI. The useful daytime demo is an internal/admin evidence package ladder, not a customer catalog.

### Recommendation C — parallel option if Saúl wants broader AAS planning

Instantiate the same ladder for **Document / Handoff Logistics** next. It is the cleanest sibling because it reuses packet-submission evidence patterns without requiring legal/regulator claims.

## 7. Repo state

- Branch: `feat/operator-route-regret-panel`
- Pushed: yes, through `a686a799`
- Full city-ops suite: `431 passed`
- Known untouched untracked repo file: `scripts/sign_req.mjs` (pre-existing; left alone)

## 8. Morning handoff sentence

Execution Market AAS now has a reusable proof ladder and a first adjacent Compliance Desk package carried all the way to a read-only internal operator surface; the next safe daytime move is a customer-output schema gate, not publication or dispatch.
