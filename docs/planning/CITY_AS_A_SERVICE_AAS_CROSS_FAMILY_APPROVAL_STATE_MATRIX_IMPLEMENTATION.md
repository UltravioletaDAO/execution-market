# City-as-a-Service — AAS Cross-Family Approval-State Matrix Implementation

Date: 2026-05-21
Scope: Execution Market AAS / City-as-a-Service internal/admin proof slice only

## What landed

Added the no-customer-exposure fork from the May 20 handoff: a deterministic internal/admin matrix comparing approval posture across the three active adjacent AAS families.

Files:

- `mcp_server/city_ops/aas_cross_family_approval_state_matrix.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_cross_family_approval_state_matrix.json`
- `mcp_server/tests/city_ops/test_aas_cross_family_approval_state_matrix.py`
- exports in `mcp_server/city_ops/__init__.py`

The matrix consumes:

- `aas_single_boundary_delivery_publication_gate.json`
- `document_handoff_approval_request_read_surface.json`
- `incident_verification_approval_record_validator.json`

## Safe claim

```text
admin_aas_cross_family_approval_state_matrix_landed
```

Conservative meaning: an internal/admin approval-state matrix exists. It is not a customer surface, not an approval record, not a delivery/publication authorization, not a route/catalog/pilot/queue/dispatch/reputation/runtime/GPS/domain-authority/legal/worker-doctrine promotion.

## Matrix posture

| Family | Current state | Human approval record | Delivery authorization |
| --- | --- | ---: | ---: |
| Compliance Desk | approval record exists, but delivery path absent | yes | no |
| Document / Handoff Logistics | pending approval request read surface, no approval record | no | no |
| Incident Verification | validator exists for future record, no approval record | no | no |

Summary counts remain fail-closed:

```text
families_with_human_approval_record = 1
families_with_delivery_authorization = 0
families_publishable = 0
families_with_public_or_catalog_routes = 0
families_ready_for_dispatch = 0
families_with_reputation_attachment_ready = 0
families_with_live_acontext_runtime_parity = 0
families_allowed_to_release_exact_gps_or_raw_metadata = 0
```

## Still blocked

Customer copy, customer delivery, publication, public/catalog routes, controlled pilot, public price/customer quote, operator queue launch, dispatch, ERC-8004 reputation, worker Skill DNA, live Acontext/runtime parity, payment/production reverification, exact GPS/raw metadata release, domain/legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability authority, and worker-copyable AAS doctrine remain blocked.

## Verification

Focused tests:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops/test_aas_cross_family_approval_state_matrix.py
# 10 passed
```

Full city-ops suite:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 1028 passed
```

## Next safe step

If customer exposure is desired, choose exactly one family and create a separate explicit human-operator decision for a named delivery path. If no customer exposure is desired, keep all rows held and continue internal packaging/pricing/operator workflow review.
