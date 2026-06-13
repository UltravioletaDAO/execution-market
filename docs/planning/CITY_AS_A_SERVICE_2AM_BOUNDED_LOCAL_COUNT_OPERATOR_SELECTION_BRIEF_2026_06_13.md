# City-as-a-Service — 2 AM Bounded Local Count Operator Selection Brief (2026-06-13)

> Scope: Execution Market AAS / City-as-a-Service internal/admin planning only.  
> Branch: `feat/operator-route-regret-panel`  
> Source posture: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md` wins over the stale cron payload. AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 remain stopped.  
> Active posture: `pause_aas_proof_layering`.  
> Safe claim: `internal_admin_aas_2am_bounded_local_count_operator_selection_brief_2026_06_13_landed`.

## Boundary

This brief is a read-only operator selection aid for the already-selected **Bounded Local Count** AAS pilot candidate. It does **not** record an operator answer, approval, answer receipt, collection authorization, buyer/customer/public/worker surface, catalog route, price, quote, queue, dispatch path, runtime/Acontext/IRC mutation, reputation/Worker Skill DNA movement, payment/production change, exact-location/raw-metadata/private-context release, authority claim, worker-copyable doctrine, or stopped-project integration.

It intentionally avoids another no-answer proof wrapper. Its useful job is narrower: make the next human decision small enough that Saúl can provide exactly one safe answer value later, without having to reread the whole AAS ladder.

## Sources reviewed

- `DREAM-PRIORITIES.md`
- `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
- `CITY_AS_A_SERVICE_1AM_SOURCE_INDEX_ALIGNMENT_2026_06_13.md`
- `CITY_AS_A_SERVICE_00AM_BOUNDED_LOCAL_COUNT_FIXTURE_GATE_2026_06_13.md`
- `CITY_AS_A_SERVICE_11PM_BOUNDED_LOCAL_COUNT_EVIDENCE_CONTRACT_2026_06_12.md`
- `CITY_AS_A_SERVICE_10PM_AAS_PILOT_OFFER_MAP_2026_06_12.md`
- `CITY_AS_A_SERVICE_7AM_AAS_IMPLEMENTATION_CONCEPT_EXPANSION_2026_06_12.md`

## Why this exists

The current AAS stack is correctly paused until there is exactly one real allowed operator answer. The 00:00 fixture gate can validate a future Bounded Local Count packet, but the operator still needs a tiny menu of safe values to choose from.

Without that menu, daytime work risks two bad outcomes:

1. **Over-broad answer drift** — a human says “local count” but the system cannot tell which count question, method, uncertainty language, and blocked claims were actually approved.
2. **Planning loop fatigue** — each dream adds more safe scaffolding while the human still lacks a crisp one-line decision.

This brief converts the Bounded Local Count lane into a small answer menu. It is not the answer. It is the menu that makes a later answer unambiguous.

## Recommended single answer value

If Saúl wants the lowest-risk Bounded Local Count pilot, the recommended value is:

```text
bounded_local_count.visible_posted_state_count.v1
```

Meaning, if later approved through the separate answer-receipt gate:

> Count one visible posted-state category at one operator-approved place or bounded public-facing observation area, during one bounded time window, using observation-only evidence, with explicit uncertainty and coverage limits.

Why this is the safest first value:

- It is observational, not diagnostic.
- It can be bounded to one place and one time window.
- It does not require touching assets, entering restricted areas, interviewing people, asserting legal meaning, or producing representative statistics.
- It teaches the proof spine Execution Market needs for AAS: question → method → window → exclusion list → uncertainty → redacted digest/reference → blocked adjacent claims.

## Allowed answer menu

These are the only three values this brief recommends keeping eligible for the first Bounded Local Count answer. Any later answer should choose exactly one.

| Candidate answer value | Human-readable label | What it can support later | Why it is low-authority | Must remain blocked |
| --- | --- | --- | --- | --- |
| `bounded_local_count.visible_posted_state_count.v1` | Visible Posted-State Count | Count whether/how many visible posted states from an approved category are present in one bounded observation window. | Observation-only; no interpretation of legal validity, office policy, compliance, or customer promise. | legal meaning, official status, guarantee, customer copy, public catalog, pricing, dispatch, reputation, payment, raw metadata, exact location |
| `bounded_local_count.queue_or_presence_count.v1` | Queue / Presence Count | Count visible people/vehicles/items in a bounded public-facing line/area at one moment or narrow window. | Counts visible presence only; no identity, intent, demographic, safety, or representative-statistics claim. | identity inference, surveillance, continuous monitoring, representative dataset, safety/security claim, dispatch, customer surface |
| `bounded_local_count.visible_asset_count.v1` | Visible Asset Count | Count visible assets of an approved category in one bounded area/window without touching or diagnosing them. | Counts visible objects only; no repair, condition certification, ownership, warranty, SLA, or access authority. | diagnosis, repair recommendation, ownership claim, restricted-area access, SLA, worker doctrine, reputation/payment movement |

## Explicit non-answer state

As of this brief:

```yaml
operator_answer_recorded: false
operator_approval_recorded: false
selected_answer_value: null
answer_receipt_created: false
collection_authorized: false
customer_surface_authorized: false
worker_surface_authorized: false
runtime_mutation_authorized: false
reputation_or_payment_authorized: false
stopped_project_integration_authorized: false
```

The active decision is still:

```text
pause_aas_proof_layering
```

## Future answer shape

If Saúl later approves one value, the answer should be captured outside this brief as a separate digest-backed receipt. The safest human-readable shape is:

```text
Approved AAS answer value: <exact candidate answer value>
Pilot boundary: one place/area, one observation window, one count question, observation-only, uncertainty required, no raw private metadata or exact-location release.
```

The receipt should not include private addresses, GPS coordinates, customer names, worker identities, private chat context, raw images, or secrets. Use an opaque non-secret reference if any source evidence needs to be tied back later.

## Minimum future packet fields

If one answer value is later approved, the first packet should contain exactly these planning fields before any code or fixture promotion:

| Field | Required shape | Fail-closed reason |
| --- | --- | --- |
| `answer_value` | exactly one value from the allowed menu | prevents multi-lane ambiguity |
| `count_question` | one bounded question | rejects open-ended collection |
| `observation_window` | bounded start/end or bounded moment | rejects continuous monitoring |
| `method_summary` | observation-only method | rejects interviews, access, manipulation, diagnosis |
| `coverage_limits` | explicit exclusions and non-representativeness | rejects dataset/statistical overclaim |
| `uncertainty_language` | present and adjacent to result | rejects exactness certification |
| `redaction_state` | states no raw private metadata / exact-location release | rejects dox/private-context leakage |
| `blocked_claims_preserved` | true | rejects promotion into customer/public/runtime/reputation/payment/authority/stopped projects |
| `opaque_reference` | non-secret reference only | prevents raw evidence leakage |

## Reject examples

The future receipt gate should reject answers or packets with any of these shapes:

- “Count everything around X.” — unbounded question.
- “Monitor throughout the day.” — continuous monitoring.
- “Verify compliance.” — authority/legal claim.
- “Tell the customer we can guarantee it.” — customer/public promise.
- “Use the GPS/photo metadata as proof.” — raw metadata/exact-location release.
- “Assign workers now.” — dispatch authorization.
- “Turn this into Worker Skill DNA.” — reputation promotion.
- “Take payment / publish the catalog item.” — payment/product exposure.
- “Connect this to AutoJob / Frontier Academy / KK v2.” — stopped-project breach.

## Strategic value for Execution Market AAS

Bounded Local Count is small, but it is a multiplier because it teaches the core AAS muscle without requiring authority:

1. **A buyer has a real-world uncertainty.**  
   The system narrows it to one countable, visible, non-authoritative question.

2. **A human/operator gate chooses one allowed value.**  
   Planning cannot silently promote itself into execution.

3. **The evidence packet carries uncertainty next to the result.**  
   The output says what was observed and what was not covered.

4. **The digest/reference layer supports review without leaking private context.**  
   Evidence can be auditable without becoming public raw data.

5. **The same skeleton can later serve other AAS families.**  
   Visible Asset State, Pre-Event Blocker Check, and Handoff Attempt Proof can reuse the question/window/method/limits/redaction pattern after their own human gates.

This is how AAS compounds: not by launching a broad marketplace promise first, but by proving a repeatable observation contract that refuses overclaiming.

## Daytime recommendation

If Saúl wants to unblock the next implementation slice, ask for exactly one of these answer values, preferably the first:

```text
bounded_local_count.visible_posted_state_count.v1
bounded_local_count.queue_or_presence_count.v1
bounded_local_count.visible_asset_count.v1
```

Recommended first answer:

```text
bounded_local_count.visible_posted_state_count.v1
```

After that answer exists, the next safe implementation slice is **one separate digest-backed answer receipt**, not a customer feature, not worker copy, not a dispatch route, not runtime/Acontext mutation, not reputation, and not payment.

## Safe claim

```text
internal_admin_aas_2am_bounded_local_count_operator_selection_brief_2026_06_13_landed
```

Meaning only: internal/admin AAS planning now has a concise operator selection brief for the first Bounded Local Count answer value. It preserves `pause_aas_proof_layering` and authorizes no answer, approval, receipt, collection, exposure, dispatch, runtime mutation, reputation, payment, authority, raw metadata/private-context release, worker doctrine, or stopped-project work.
