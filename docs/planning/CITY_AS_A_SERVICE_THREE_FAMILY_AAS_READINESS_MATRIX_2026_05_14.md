# City as a Service — Three-Family AAS Readiness Matrix 2026-05-14

> Scope: Execution Market AAS / City-as-a-Service internal planning only  
> Status: internal/admin readiness matrix; not public copy; not customer-facing approval  
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`

## Why this exists

The May 14 night ended with the same conservative package ladder proven through explicit internal/admin hold decisions across three adjacent AAS families. This matrix is the daytime review shortcut: one row per family, latest safe claim, blocked authority class, readiness flags, and next smallest gate.

It intentionally does **not** add a product surface, customer copy, route, dispatch behavior, reputation receipt, live-runtime claim, or worker doctrine.

## Common ladder now proven

```text
fixture/review gate
-> local reviewed fixture
-> internal package record
-> read-only operator surface
-> customer-output schema gate
-> internal/admin sample output
-> explicit hold/approval decision
```

## Matrix

| Family | Current ladder step | Latest safe claim | Primary blocked authority class | Next smallest safe gate |
|---|---|---|---|---|
| Compliance Desk | Explicit internal/admin sample-output hold decision | `compliance_desk_sample_output_review_decision_landed` | legal/regulator/inspection/compliance guarantees | If customer exposure is desired: one separate human-operator approval artifact for exactly one held Compliance Desk text boundary; otherwise keep held. |
| Document / Handoff Logistics | Explicit internal/admin sample-output hold decision | `document_handoff_sample_output_review_decision_landed` | legal service, notarial, private-identity, guaranteed acceptance, filing success, custody guarantees | If customer exposure is desired: one separate human-operator approval artifact for exactly one held Document/Handoff text boundary; otherwise keep held. |
| Incident Verification | Explicit internal/admin sample-output hold decision | `incident_verification_sample_output_review_decision_landed` | emergency response, safety certification, repair, insurance, SLA, official report, fault/liability claims | If customer exposure is desired: one separate human-operator approval artifact for exactly one held Incident Verification text boundary; otherwise keep held. |

## Readiness flags that remain false across all three families

- customer copy ready
- customer delivery approved
- public/catalog route ready
- controlled pilot ready
- dispatch ready
- autonomous dispatch ready
- ERC-8004 reputation receipt attachable
- worker Skill DNA attachable
- worker-copyable doctrine ready
- live Acontext sink ready
- runtime parity proven
- exact GPS/raw metadata releasable
- raw transcript authority allowed
- public/domain-authority claims approved

## What the matrix proves

This proves packaging discipline, not launch readiness:

1. Each adjacent AAS family can preserve reviewed evidence, safe claims, and blocked claims through the same ladder.
2. Each family can produce an internal/admin sample output without converting it into customer copy.
3. Each family can stop at an explicit hold decision rather than silently promoting a draft into publication.
4. Domain-specific overclaim classes remain visible next to each safe claim.

## What daytime should do next

Recommended daytime fork:

1. **Customer exposure desired:** choose exactly one held sample/text boundary and create a separate human-operator approval artifact naming exact approved text, redactions, delivery path, and still-blocked claims.
2. **No customer exposure yet:** keep all three families held and use this matrix as the internal review entrypoint for packaging, pricing, or operator workflow discussion.

Do **not** use this matrix as authorization for publication, routes, dispatch, reputation, live runtime, exact GPS/raw metadata release, or worker-copyable doctrine.

## 07:00 no-customer-exposure follow-up

The no-customer-exposure fork now has a compact internal/admin review artifact:

- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_three_family_packaging_review_packet.json`
- implementation note: `CITY_AS_A_SERVICE_AAS_THREE_FAMILY_PACKAGING_REVIEW_PACKET_IMPLEMENTATION.md`
- safe claim: `aas_three_family_packaging_review_packet_landed`

It keeps all three families held and makes only package labels, pricing inputs, and operator queue/workflow shape reviewable. It does not approve customer copy, delivery, routes, public prices, dispatch, reputation, live runtime, exact GPS/raw metadata release, or worker doctrine.

## 22:30 no-customer-exposure review-board follow-up

The packaging packet now feeds one further internal/admin board:

- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_packaging_pricing_operator_workflow_review_board.json`
- implementation note: `CITY_AS_A_SERVICE_AAS_PACKAGING_PRICING_OPERATOR_WORKFLOW_REVIEW_BOARD_IMPLEMENTATION.md`
- safe claim: `aas_packaging_pricing_operator_workflow_review_board_landed`

The board consumes only `aas_three_family_packaging_review_packet.json` and makes package labels, pricing inputs, and operator queue/workflow questions reviewable. It still does not approve customer copy, customer delivery, public prices/customer quotes, routes, pilots, dispatch, reputation, live runtime, exact GPS/raw metadata release, domain authority, or worker doctrine.

## Source artifacts

- `CITY_AS_A_SERVICE_FINAL_MORNING_HANDOFF_2026_05_14.md`
- `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_14.md`
- `EXECUTION_MARKET_AAS_GAP_MAP_2026_05_12.md`
- `mcp_server/city_ops/fixtures/aas_package_ladder/compliance_desk_sample_output_review_decision.json`
- `mcp_server/city_ops/fixtures/aas_package_ladder/document_handoff_sample_output_review_decision.json`
- `mcp_server/city_ops/fixtures/aas_package_ladder/incident_verification_sample_output_review_decision.json`
