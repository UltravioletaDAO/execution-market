# City-as-a-Service — AAS Document Handoff Redaction + Delivery Gap Note Implementation

> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.
> Safe claim: `internal_admin_aas_document_handoff_redaction_delivery_gap_note_landed`.
> Status: maintenance-only gap note; not an operator answer, approval record, answer receipt, customer/public/worker surface, delivery authorization, legal/notarial/custody acceptance claim, pricing/catalog route, queue/dispatch, reputation, payment, runtime/Acontext/IRC mutation, exact GPS/raw metadata/private-context/PII release, worker doctrine, or stopped-project integration.

## Why this exists

The June 5 concept-gap roadmap ranked `document_handoff` as the safest non-answer planning slice after Retail Reality remains blocked on a real operator answer. The allowed action was narrow:

```text
redaction_and_delivery_path_gap_note_maintenance_only
```

This implementation turns that one roadmap row into a deterministic internal/admin fixture so future Document Handoff work can see the exact redaction checks, delivery-path unknowns, safe language, forbidden language, and next gate without mistaking maintenance for approval.

## What landed

- `mcp_server/city_ops/aas_document_handoff_redaction_delivery_gap_note.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_document_handoff_redaction_delivery_gap_note.json`
- `mcp_server/tests/city_ops/test_aas_document_handoff_redaction_delivery_gap_note.py`

The fixture consumes `aas_concept_gap_implementation_roadmap.json` by digest and locks to the rank-2 `document_handoff` row.

## Safe use

```text
internal_admin_redaction_delivery_path_gap_note_maintenance_only
```

Allowed meaning:

- keep Document Handoff redaction checks visible;
- keep delivery-path unknowns visible;
- preserve safe internal language;
- quarantine forbidden legal/custody/delivery/customer claims;
- require a separate explicit operator answer receipt before any delivery/publication gate.

## Redaction checks captured

- mask private person identifiers before any operator review packet;
- exclude exact locations, coordinates, raw metadata, and private context;
- exclude signatures, payment details, account numbers, tokens, keys, and credentials;
- reference sources by non-secret digest or label, not raw sensitive content;
- keep excerpts bounded to visible document facts only if a future answer authorizes them.

## Delivery-path unknowns preserved

- authorized recipient/review role is not selected;
- authorized delivery channel is not selected;
- acceptance criteria are not recorded;
- custody chain is not authorized;
- legal/notarial/regulatory sufficiency is not authorized;
- customer-facing format is not approved.

## Still blocked

```text
operator answer
operator approval
answer receipt
selected future answer
customer/public/worker copy
recipient/channel/delivery/acceptance authorization
catalog/pricing/quote/route/queue/dispatch
worker instruction
ERC-8004 reputation / Worker Skill DNA
payment / production readiness
runtime/Acontext/IRC mutation
exact GPS/raw metadata/private context/PII release
legal/notarial/custody/regulatory/acceptance authority
worker-copyable doctrine
AutoJob / Frontier Academy / KK v2 / KarmaCadabra v2 work
```

## Next gate

If Saúl gives exactly one explicit Document Handoff answer later, the next artifact should be separate and should validate an answer receipt before any delivery/publication gate:

```text
separate_explicit_operator_answer_receipt_then_document_handoff_delivery_publication_gate
```

This gap note itself does not create that receipt.

## Verification

```bash
git diff --check
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_concept_gap_implementation_roadmap.py \
  mcp_server/tests/city_ops/test_aas_document_handoff_redaction_delivery_gap_note.py
```

No deploy is required because this is an internal/admin planning artifact and fixture only.
