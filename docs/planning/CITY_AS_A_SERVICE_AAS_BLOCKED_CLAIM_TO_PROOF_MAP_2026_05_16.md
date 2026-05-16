# City as a Service — AAS Blocked-Claim to Proof Map 2026-05-16

> Scope: Execution Market AAS / City-as-a-Service first; adjacent AAS families only as reusable slots.
> Status: internal/admin implementation planning artifact. Not public copy, not a customer catalog, not a launch claim.

## Purpose

The current CaaS/AAS stack has many useful internal artifacts, but the product risk is treating a landed planning/read-surface claim as permission to expose customer copy, launch queues, write live memory, dispatch workers, attach reputation, or make authority claims.

This map turns the active blocked claims into implementation lanes. Each lane names:

1. the **current safe claim** that may be repeated,
2. the **claim that remains blocked**,
3. the **only allowed next proof** that can move the lane forward, and
4. the **overclaim that must stay forbidden** even if the next proof passes.

Use it as an internal/admin routing page before selecting the next CaaS or adjacent AAS slice.

## Source artifacts checked

- `docs/planning/CITY_AS_A_SERVICE_FINAL_MORNING_HANDOFF_2026_05_16.md`
- `docs/planning/CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_16.md`
- `docs/planning/CITY_AS_A_SERVICE_6AM_MORNING_BRIEF_2026_05_16.md`
- `docs/planning/EXECUTION_MARKET_AAS_GAP_MAP_2026_05_12.md`
- `docs/planning/CITY_AS_A_SERVICE_THREE_FAMILY_AAS_READINESS_MATRIX_2026_05_14.md`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_explicit_venv_preflight_rerun.json`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_live_preflight_blocker_delta.json`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_coordination_observability_success_metrics_board.json`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_coordination_multiplier_pattern_map.json`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_three_family_packaging_review_packet.json`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_single_boundary_operator_review_brief.json`
- `mcp_server/city_ops/fixtures/aas_package_ladder/aas_single_boundary_approval_record_schema_gate.json`

## Routing rule

A claim may move forward only when all five fields travel together:

```text
source artifact -> invariant IDs -> declared/verified badge -> safe + blocked claims -> one next proof
```

If any field is missing, route the work to a proof-support guardrail or handoff cleanup. Do not route it to customer copy, public routes, queues, dispatch, reputation, live memory, pricing, or worker instructions.

## Blocked-claim implementation lanes

| Lane | Current safe claim | Still blocked | Allowed next proof | Forbidden overclaim after next proof |
| --- | --- | --- | --- | --- |
| Runtime memory / Acontext | `admin_acontext_explicit_venv_preflight_rerun_landed` | live Acontext sink readiness, runtime parity, live write/retrieve completion | Complete service prerequisites, rerun read-only preflight, rebuild blocker delta/read surface/readiness gate, then attempt exactly one live write/retrieve parity pass only if blockers are empty. | Do not infer customer readiness, dispatch readiness, public route readiness, payment/infra freshness, or worker-copyable doctrine from the Acontext pass. |
| Customer exposure / Compliance Desk label boundary | `aas_single_boundary_operator_review_brief_landed` and `aas_single_boundary_approval_record_validator_landed` | customer delivery approval, publication approval, public catalog, public route, controlled pilot | A real human operator creates one separate approval record for exactly `Visible posting / notice compliance snapshot`; validator must pass fail-closed with source digest parity, redaction evidence references, authorized delivery path, false future flags, and still-blocked claims preserved. | Even a valid record approves only the exact text boundary and delivery path named in that record. It does not approve broad customer delivery, publication, pricing, routes, pilots, queues, dispatch, reputation, runtime, or domain authority. |
| Three-family package planning | `aas_three_family_packaging_review_packet_landed` | customer package readiness, public prices/customer quotes, operator workflow launch | Keep an internal package/pricing/operator workflow review that consumes the three held sample-output decisions and produces review decisions without customer exposure. | Do not turn labels, price inputs, or workflow notes into public SKUs, quotes, launch plans, or queue activation. |
| Internal/admin coordination | `admin_aas_coordination_observability_success_metrics_board_landed` and `admin_aas_coordination_multiplier_pattern_map_landed` | public/customer metrics dashboard, cross-project autorouting, agent reputation scoring | Reuse the four-id header, declared-vs-verified badge, blocked-claim adjacency, and one-next-proof slot in the next AAS handoff. | Coordination discipline is not product readiness. It cannot approve runtime, customer routes, payment/infra state, dispatch, reputation, or worker doctrine. |
| Queue / dispatch / worker instruction | internal proof ladder preserves operator guidance boundaries | operator queue launch, autonomous dispatch, dispatch instruction readiness, worker Skill DNA, worker-copyable doctrine | Separate dispatch/worker-doctrine gate that consumes reviewed outputs and proves copyability, tone, placement, and operator authorization without dropping blocked claims. | No existing proof support artifact should be copied into worker instructions or treated as autonomous routing authority. |
| Reputation / ERC-8004 receipts | none in the current CaaS/AAS proof chain | ERC-8004 reputation readiness, reputation receipt attachability | Separate reputation proof path with explicit event source, signer, identity, privacy, and revocation/rollback semantics. | Do not attach reputation because a reviewed fixture, sample, approval request, or coordination board exists. |
| Privacy / sensitive metadata | internal redaction/privacy checks exist for samples and gates | exact location/raw metadata release, raw transcript authority, private operator context | Separate privacy review that proves output redaction, no raw transcript dependency, no sensitive metadata exposure, and customer-safe source labeling. | Never expose exact location/raw metadata or raw transcript authority from fixture/review artifacts. |
| Domain authority | reviewed evidence and limitation language can exist internally | legal sufficiency, regulator acceptance, official inspection/report, notarial/custody/emergency/safety/repair/insurance/SLA/fault-liability claims | Separate credentialed/scope-specific authority gate, or keep language limited to observed/documented/customer-supplied facts and limitations. | A CaaS/AAS package can describe evidence and constraints; it cannot claim official authority, legal outcome, acceptance, safety, custody, or liability. |
| Payment / production freshness | no current May 16 artifact reverified payment or production infra | payment coverage, production infrastructure health, multi-chain payment perfection | Fresh probe of the exact live endpoint/contract/payment path before repeating current operational confidence. | Do not quote old payment/infra status from planning artifacts as current readiness. |
| Adjacent AAS reuse | adjacent families have held internal sample-output decisions and the minimum ladder template | adjacent-family customer readiness, public catalog, live runtime, dispatch, reputation, authority claims | Start each family with its own fixture, reviewed output, package record, read-only operator surface, customer-output schema gate, held/approved decision, and blocked-claim set. | CaaS proof discipline is reusable; CaaS proof coverage is not automatically transferable. |

## Primary City-as-a-Service next-proof fork

Choose exactly one branch for the next implementation slice.

### Branch A — live-memory proof

Use when the goal is runtime confidence.

1. Settle/start Acontext services until local API and dashboard are reachable.
2. Run the read-only preflight with the explicit venv runner.
3. Rebuild the blocker delta, read surface, and readiness gate.
4. If and only if the rebuilt gate has empty blockers, run one write/retrieve parity attempt.
5. Record result with safe and blocked claims adjacent.

Allowed outcome labels:

- `acontext_prerequisites_cleared_for_one_attempt` only if the rebuilt gate proves it.
- `live_acontext_transport_parity_landed` only if the single write/retrieve pass preserves identity, claim boundaries, and payload parity.
- Otherwise keep `live_transport_still_blocked_*` style labels.

### Branch B — customer-exposure proof

Use when the goal is a narrow human-approved customer-facing test.

1. Keep the selected boundary exactly `Visible posting / notice compliance snapshot` unless a new request artifact chooses another single boundary.
2. Have a real human operator create one approval record.
3. Validate the record fail-closed.
4. Preserve all false future flags and still-blocked claims.
5. Stop at the exact authorized boundary; do not generate public catalog/route/price/queue claims.

Allowed outcome labels:

- `single_boundary_human_approval_record_validated` only for the named boundary and authorized delivery path.
- `single_boundary_human_approval_record_rejected` if any digest, redaction, scope, timestamp, or blocked-claim condition fails.

### Branch C — no-exposure internal packaging proof

Use when neither runtime nor customer exposure is ready.

1. Keep all families held.
2. Consume only held decisions and internal package records.
3. Add a review decision for package labels, pricing inputs, or operator workflow shape.
4. Preserve `customer/public/pilot/dispatch/reputation/runtime/location metadata/domain authority/worker doctrine` as blocked.

Allowed outcome label:

- `internal_package_review_decision_landed` for the exact review decision only.

## Generic AAS slots derived from CaaS

These slots may be reused by Compliance Desk, Document / Handoff Logistics, Incident Verification, or a future AAS family. They are patterns, not approvals.

| Slot | Required local artifact before next step | Must stay blocked |
| --- | --- | --- |
| Fixture gate | family-specific fixture/review gate | customer readiness, route readiness, authority claims |
| Reviewed output | source-labeled reviewed output with limitations | legal/regulator/safety/custody/compliance guarantees |
| Internal package record | package record tied to reviewed fixture IDs | public catalog, customer delivery, pricing, queue launch |
| Operator read surface | pass-through internal/admin read surface | interpretation drift, public dashboard, dispatch readiness |
| Customer-output schema gate | output shape with forbidden fields and redaction constraints | publication, exact location/raw metadata, raw transcript authority |
| Sample output decision | explicit hold or one-boundary approval request | broad customer copy, delivery, or domain authority |
| Human approval record | one real operator record for one exact boundary | anything outside the named text boundary and delivery path |

## Stop conditions

Stop and produce only a handoff/guardrail if any of these happen:

- the next proof depends on current live infra/payment status but no fresh probe was run;
- a safe claim is present without its adjacent blocked claims;
- a route/UI/read surface adds interpretation instead of pass-through rendering;
- a customer-facing phrase appears before the exact human approval record exists;
- exact location/raw metadata, raw transcripts, or private operator context would be exposed;
- the work would create dispatch, reputation, pricing, legal, regulator, safety, custody, repair, insurance, SLA, official-report, or worker-doctrine claims from planning artifacts alone.

## Recommended next implementation selection

Default to **Branch A** only if the operator is prepared to finish local Acontext prerequisites and run a fresh read-only preflight.

Default to **Branch B** only if a real human operator is available to approve exactly one text boundary.

Otherwise choose **Branch C** and keep the work internal/admin-only. The safest no-human, no-live-runtime slice is an `internal_package_review_decision_landed` artifact that consumes held decisions, keeps all readiness flags false, and clarifies the next single proof without broadening surface area.
