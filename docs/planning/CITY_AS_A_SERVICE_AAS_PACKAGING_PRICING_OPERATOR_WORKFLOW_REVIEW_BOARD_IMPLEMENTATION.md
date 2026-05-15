# City as a Service — AAS Packaging/Pricing/Operator Workflow Review Board Implementation

> Date: 2026-05-14 22:30 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal planning only
> Status: internal/admin review board; not customer exposure; not pricing approval

## What landed

Added the next no-customer-exposure internal/admin slice after the three-family packaging review packet:

- `mcp_server/city_ops/aas_packaging_pricing_operator_workflow_review_board.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_packaging_pricing_operator_workflow_review_board.json`
- `mcp_server/tests/city_ops/test_aas_packaging_pricing_operator_workflow_review_board.py`
- exports in `mcp_server/city_ops/__init__.py`

## Source consumed

The board consumes only:

- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_three_family_packaging_review_packet.json`

It does not inspect or promote the underlying family artifacts directly. The source packet must still prove all three families are held at explicit internal/admin sample-output hold decisions.

## New safe claim

`aas_packaging_pricing_operator_workflow_review_board_landed`

This means only: an internal/admin board now exists for reviewing package labels, pricing inputs, and operator queue/workflow questions across the three held AAS families.

## What is reviewable

- internal package labels
- pricing input questions such as operator minutes, evidence/media complexity, redaction complexity, and follow-on task triggers
- operator queue names
- workflow question order for intake, evidence contract selection, limitation/redaction review, and possible separate approval records

## What remains blocked

The board does **not** approve or imply:

- customer copy, customer delivery, or publication
- public prices or customer quotes
- public/catalog routes
- controlled pilots or front-door SKUs
- worker dispatch or dispatch instructions
- ERC-8004 reputation receipts
- live Acontext/runtime parity
- exact GPS/raw metadata release
- domain-authority, legal, notarial, emergency, safety, repair, insurance, SLA, official-report, or custody claims
- worker-copyable doctrine

## Fail-closed coverage

Tests cover source and board drift for:

- source hold promotion
- forbidden safe claims
- public route / pilot / dispatch / reputation / live-runtime / GPS/raw-metadata / worker-doctrine boundary drift
- public price and customer quote drift
- domain-authority block drift
- operator workflow launch drift
- board-level readiness flips

## Next safe step

Use this board for internal package-label, pricing-input, and workflow review only. If customer exposure is later desired, create a separate human-operator approval artifact for exactly one held text boundary, naming the exact approved text, redactions, delivery path, and still-blocked claims.
