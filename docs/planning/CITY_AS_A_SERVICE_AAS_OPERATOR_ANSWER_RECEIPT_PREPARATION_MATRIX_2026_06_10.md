# City-as-a-Service — AAS Operator Answer Receipt Preparation Matrix (2026-06-10)

> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.  
> Governing priority: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`.  
> Safe claim: `internal_admin_aas_operator_answer_receipt_preparation_matrix_landed`.  
> Status: receipt-preparation plan only; no operator answer, approval, customer/public/worker copy, route, queue, dispatch, runtime mutation, Acontext write/retrieve, reputation/Worker Skill DNA, payment/production reverification, exact-location/raw-metadata release, private-context release, authority claim, worker-copyable doctrine, or stopped-project integration.

## 1. Why this exists

The latest AAS stack is intentionally conservative: the June 7 final wrap says the correct posture is `pause_aas_proof_layering` until Saúl provides exactly one explicit allowed answer value. More no-answer wrappers create ceremony without unlocking product movement.

This matrix prepares the *next useful artifact after a real answer exists* while still preserving the current no-answer hold. Its job is to make the future answer receipt unambiguous enough that a daytime operator or later dream session can create exactly one validated receipt instead of accidentally treating planning copy, an option display, a score, or a candidate selection as approval.

## 2. Current state, stated plainly

| Field | Current value |
| --- | --- |
| Explicit operator answer | Absent |
| Operator approval record | Absent |
| Selected future answer | None |
| Effective decision | `keep_both_lanes_held_internal_admin_only` / `pause_aas_proof_layering` posture |
| Customer/public/worker surface | Not authorized |
| Runtime-memory / Acontext mutation | Not authorized |
| Route / queue / dispatch | Not authorized |
| ERC-8004 reputation / Worker Skill DNA | Not authorized |
| Payment / production readiness | Not reverified |
| Exact GPS/raw metadata/private context | Not releasable |
| Domain/legal/emergency/repair/insurance/SLA authority | Not granted |
| AutoJob / Frontier Academy / KK v2 / KarmaCadabra v2 | Explicitly stopped by `DREAM-PRIORITIES.md` |

## 3. Allowed future answer values

A real answer receipt should select exactly one value from the existing two-lane answer schema:

1. `keep_both_lanes_held`
2. `create_retail_reality_answer_or_hold_record`
3. `create_runtime_memory_operator_answer_record`
4. `pause_aas_proof_layering`

Anything else is invalid for the current AAS decision. Any answer that tries to authorize multiple lanes at once should fail closed.

## 4. Receipt envelope required after an answer

The future receipt should be a separate artifact, not an edit to this preparation matrix. Minimum envelope:

```json
{
  "schema": "city_ops.aas_two_lane_operator_answer_record.v1",
  "source_guard_id": "<from aas_two_lane_no_cross_promotion_guard.json>",
  "source_guard_digest_sha256": "<sha256 of source guard payload>",
  "selected_decision": "<one allowed value>",
  "human_operator_answer_recorded": true,
  "human_operator_reference": "<non-secret operator reference>",
  "answer_timestamp_utc": "<UTC timestamp>",
  "answer_scope": "one_of_four_two_lane_decisions_only_not_approval",
  "approvals_not_granted": [
    "product_exposure_approved",
    "runtime_memory_wiring_approved",
    "runtime_adapter_registered",
    "runtime_adapter_enabled",
    "irc_session_manager_mutated",
    "live_acontext_ready",
    "customer_copy_ready",
    "catalog_ready",
    "pricing_ready",
    "dispatch_ready",
    "erc8004_reputation_ready",
    "worker_skill_dna_ready",
    "payment_production_reverified",
    "gps_release_ready",
    "private_context_release_ready",
    "domain_authority_ready",
    "worker_copyable_doctrine_ready",
    "stopped_project_integration_ready"
  ],
  "still_blocked_claims": ["<full blocked claim list copied from the source schema>"]
}
```

Hard rules:

- The receipt records an answer, not approval.
- The receipt cannot infer approval from a prompt, UI display, score, source index, candidate card, route preflight, or no-answer board.
- The receipt cannot silently unlock runtime, product, dispatch, reputation, payment, location, private-context, authority, or worker-doctrine claims.
- The receipt cannot mention or reactivate stopped projects.

## 5. Decision-specific follow-on gates

| Selected decision | Immediate next artifact | Still explicitly blocked |
| --- | --- | --- |
| `keep_both_lanes_held` | `aas_two_lane_hold_receipt.json` or equivalent final hold note | Product exposure, runtime-memory, dispatch, reputation, payment, customer copy, stopped projects |
| `create_retail_reality_answer_or_hold_record` | Retail Reality answer-or-hold record against the receipt digest | Customer/public copy, catalog/pricing/queue/dispatch, field/site authority, worker doctrine, payment/reputation |
| `create_runtime_memory_operator_answer_record` | Runtime-memory operator answer record against the receipt digest | Runtime adapter registration/enablement, IRC/session-manager mutation, Acontext write/retrieve, live parity, private context release |
| `pause_aas_proof_layering` | Pause receipt and source-index/daytime-board note | Additional proof wrappers, product/runtime/dispatch escalation, stopped-project integration |

The safest default with no answer remains `pause_aas_proof_layering`.

## 6. Family preparation matrix

| AAS family / lane | Current useful preparation | What the future receipt may unlock | What it does **not** unlock |
| --- | --- | --- | --- |
| Retail Reality | Prepare answer-or-hold record shape and product-exposure boundary checklist | One internal/admin record deciding whether to continue product-exposure preparation | Customer copy, pricing, public catalog, queue, dispatch, worker instructions |
| Runtime Memory / Acontext | Prepare operator answer record shape and prerequisite inventory | One internal/admin record deciding whether to inventory runtime prerequisites | Docker repair, local server start, adapter registration, Acontext writes/retrievals, IRC mutation |
| Document / Handoff | Preserve redaction/delivery gap notes as context | Only context for future product-family decisions after separate receipt | Delivery approval, legal/notarial/custody claims, customer copy |
| Compliance Desk | Preserve delivery-path hold gap as context | Only context for future product-family decisions after separate receipt | Regulatory authority, official submission claims, pricing/dispatch |
| Incident Verification | Preserve observation uncertainty and sample-output review context | Only context for future product-family decisions after separate receipt | Emergency, repair, fault/liability, insurance, SLA, official report claims |
| Local Data Collection | Preserve measurement uncertainty rubric as context | Only context for future product-family decisions after separate receipt | Certified datasets, exact GPS/raw metadata release, field access authority |
| Property Ops | Preserve blocked-claim quarantine vocabulary as context | Only context for future product-family decisions after separate receipt | Site access, inspection/repair authority, warranty/SLA, worker-copyable doctrine |

## 7. Validation checklist for the future receipt

Before a future receipt is accepted:

1. Read `DREAM-PRIORITIES.md` first; reject stopped-project work.
2. Load the current two-lane answer schema and guard fixture.
3. Recompute the source guard digest.
4. Confirm `selected_decision` is exactly one of the four allowed values.
5. Confirm `human_operator_answer_recorded` is true and a non-secret operator reference exists.
6. Confirm `approvals_not_granted` still includes every blocked downstream class.
7. Confirm no customer/public/worker copy appears in the receipt.
8. Confirm no exact GPS/raw metadata, private context, secrets, session IDs, or message IDs are persisted.
9. Confirm no Acontext write/retrieve, IRC/session-manager mutation, adapter registration, dispatch, reputation, or payment claim is implied.
10. Only after the receipt passes, create the selected follow-on gate as a second artifact.

## 8. Recommended daytime ask

Ask for exactly one value, with no extra inference:

```text
Choose exactly one AAS decision value:
1. keep_both_lanes_held
2. create_retail_reality_answer_or_hold_record
3. create_runtime_memory_operator_answer_record
4. pause_aas_proof_layering
```

If the answer is anything broader than one value, treat it as non-machine-actionable guidance and stay held until it is narrowed.

## 9. Implementation sequence after a valid answer

1. Create `aas_two_lane_operator_answer_record` as a new fixture/module/test pair.
2. Add a negative test proving displayed options do not count as answer or approval.
3. Add a negative test proving selected answer does not grant product/runtime/dispatch/reputation/payment/location/private-context/authority/stopped-project claims.
4. Add exactly one follow-on gate matching the selected decision.
5. Update the source-of-truth index and daytime board only after the receipt fixture is stable.
6. Run focused city-ops tests, then full `mcp_server/tests/city_ops` if any fixture digests cascade.

## 10. Safe one-line handoff

Execution Market AAS is ready for a future *answer receipt*, not for product/runtime/customer/dispatch movement; until Saúl selects exactly one allowed value, keep both lanes held and avoid stopped-project work.
