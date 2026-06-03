# City-as-a-Service — Operator Decision Aid (2026-06-03)

> Scope: Execution Market AAS / City-as-a-Service only.
> Purpose: help Saúl/operator choose exactly one next value from the June 3 two-lane schema.
> Status: internal/admin decision aid only; not an answer record, approval record, proof wrapper, runtime change, or product surface.

## Governing state

The 6 AM final wrap concluded that AAS has enough read-only coordination structure. The next useful move is exactly one explicit human/operator answer or an explicit pause.

Allowed values remain exactly:

```text
keep_both_lanes_held
create_retail_reality_answer_or_hold_record
create_runtime_memory_operator_answer_record
pause_aas_proof_layering
```

None is selected by this document.

## Fast choice guide

| Choose this value | When it is the right operator choice | Immediate next action | What stays blocked |
| --- | --- | --- | --- |
| `keep_both_lanes_held` | You want product exposure and runtime memory to remain held, but you do not want to formally stop future AAS work. | Record a separate answer artifact saying both lanes stay held. | Retail Reality exposure, runtime-memory wiring, public/customer/worker surfaces, dispatch, reputation, payment/production claims. |
| `create_retail_reality_answer_or_hold_record` | You want the product-exposure lane handled first, either approving a bounded review path or recording an explicit hold. | Create exactly one separate Retail Reality answer/hold record against the two-lane schema. | Runtime-memory answer/wiring, adapter registration, IRC/session-manager mutation, live Acontext writes, cross-lane promotion. |
| `create_runtime_memory_operator_answer_record` | You want the runtime-memory lane handled first, without implying any product exposure. | Create exactly one separate runtime-memory operator answer record; only then may prior design-only/default-off inputs be considered. | Retail Reality exposure, public/customer/worker surfaces, adapter enablement, IRC/session-manager mutation, live Acontext writes unless separately authorized later. |
| `pause_aas_proof_layering` | You agree the no-answer proof/read-only layering should stop until a real product/runtime decision exists. | Record a separate pause answer and stop adding no-answer wrappers. | All product exposure, runtime mutation, public surfaces, worker/dispatch/reputation/payment claims. |

## Recommended default if no answer exists

Pick `pause_aas_proof_layering`, or equivalently keep both lanes held while explicitly pausing new no-answer proof layers. This avoids turning coordination quality into false progress.

## Non-authorization statement

This document records:

- **NO answer**;
- **NO approval**;
- **NO product exposure**;
- **NO runtime mutation**;
- **NO public/customer/worker surface**;
- **NO payment, reputation, GPS, private-context, authority, or worker-doctrine claim**;
- **NO stopped-project integration**.

It also records no selected future answer, no Retail Reality answer/hold record, no runtime-memory operator answer record, no runtime adapter registration or enablement, no IRC/session-manager mutation, no live Acontext write or retrieval, no cross-project autorouting, no catalog/pricing/queue/dispatch readiness, no ERC-8004 reputation, no Worker Skill DNA, no payment/production reverification, no exact GPS/raw metadata release, no private operator context release, no raw transcript authority, and no domain/legal/emergency/safety/repair/insurance/SLA authority claim.

## Safe claim

Safe to claim only:

```text
internal_admin_aas_operator_decision_aid_landed
```

Meaning only: a concise internal/admin aid now helps choose one of the four already-allowed answer values. It does not choose the value and does not authorize the next artifact.
