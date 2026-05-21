# City-as-a-Service — AAS Single-Boundary Delivery/Publication Gate Implementation

Date: 2026-05-18
Scope: Execution Market AAS / City-as-a-Service internal/admin proof slice only

## What landed

Added a delivery/publication gate over the existing single-boundary human-operator approval record:

- `mcp_server/city_ops/aas_single_boundary_delivery_publication_gate.py`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_single_boundary_delivery_publication_gate.json`
- `mcp_server/tests/city_ops/test_aas_single_boundary_delivery_publication_gate.py`

The gate consumes:

- `aas_single_boundary_human_operator_approval_record.json`

and preserves the exact approved internal text boundary:

- family: `Compliance Desk as a Service`
- offer: `visible_posting_notice_compliance_snapshot`
- text boundary: `internal_package_label_only`
- approved text: `Visible posting / notice compliance snapshot`

## Safe claim

```text
delivery_publication_gate_landed
```

Conservative meaning: an internal/admin gate exists after the single-boundary approval record. It does **not** authorize delivery, publication, customer copy, a public/catalog route, pilot, queue, dispatch, reputation, live runtime parity, GPS/raw metadata release, domain-authority/legal claims, or worker-copyable doctrine.

## Delivery/publication posture

The gate keeps:

```text
authorized_delivery_path = none_no_customer_delivery_authorized
authorized_delivery_path_authorized = false
publication_approved = false
customer_delivery_approval = false
operator_publish_approval = false
```

It also requires delivery-time reruns for:

- all carried-forward redaction checks;
- domain-authority claim review.

Those delivery-time checks are explicitly `passed_for_delivery=false` and `authorizes_delivery_or_publication=false`.

## Blocked claims preserved

Still blocked unless separately proven by a later explicit approval artifact:

- customer delivery / customer copy;
- publication / publish route;
- public route / catalog route;
- controlled pilot / front-door SKU;
- public price / customer quote;
- operator queue launch;
- dispatch / autonomous dispatch;
- ERC-8004 reputation receipts;
- live Acontext/runtime parity;
- exact GPS/raw metadata exposure;
- domain-authority, legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability claims;
- worker Skill DNA / worker-copyable doctrine.

## Verification

Focused tests:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops/test_aas_single_boundary_delivery_publication_gate.py
```

Full city-ops suite:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
```

## May 20 22:00 handoff re-verification

The May 20 daytime handoff again selected this exact fork as the safest
customer-exposure boundary over the existing Compliance Desk approval record.
The already-landed gate remains the correct implementation target and still
fails closed:

- source approval record: `aas_single_boundary_human_operator_approval_record.json`
- approved boundary: `Visible posting / notice compliance snapshot`
- verdict: `hold_no_authorized_delivery_path`
- delivery path: `none_no_customer_delivery_authorized`
- customer delivery/publication authorization: `false`

No additional route, catalog, pilot, dispatch, reputation, live-runtime,
GPS/raw-metadata, legal/domain-authority, or worker-doctrine promotion was added.
The current safe claim remains only `delivery_publication_gate_landed`; all
customer/public/runtime claims stay in `do_not_claim_yet[]` / `still_blocked_claims[]`.
