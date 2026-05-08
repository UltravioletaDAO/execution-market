# City as a Service — AAS Packaging Plan Audit (2026-05-07)

> Scope: Execution Market AAS / City-as-a-Service only  
> Branch context: `feat/operator-route-regret-panel`  
> Status: sellable packaging audit; no new readiness claim

## 1. Why this doc exists

The CaaS planning stack now has strong strategy, commercial packaging, pilot scope, and a growing proof-artifact spine. The daytime risk is no longer lack of ideas. It is accidentally selling or building beyond what the proof spine has actually earned.

This audit compresses the current planning docs into one packaging view:

- what is already supported by planning or local replay/proof artifacts
- what can be packaged now as a narrow sellable AAS slice
- what remains blocked and must not appear in sales, UI, or operator language as ready
- the smallest next packaging step that sharpens the offer without overclaiming

## 2. Source docs reviewed

Primary docs:

- `MASTER_PLAN_CITY_AS_A_SERVICE.md`
- `CITY_AS_A_SERVICE_GO_TO_MARKET.md`
- `CITY_AS_A_SERVICE_SERVICE_CATALOG.md`
- `CITY_AS_A_SERVICE_PILOT_BLUEPRINT.md`
- `CITY_AS_A_SERVICE_IMPLEMENTATION_BACKLOG_AND_DECISIONS.md`
- `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
- `CITY_AS_A_SERVICE_MORNING_BRIEF_2026_05_07.md`
- `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_07.md`
- `CITY_AS_A_SERVICE_FINAL_MORNING_HANDOFF_2026_05_07.md`

Supporting implementation notes reviewed by reference:

- Acontext transport parity, live preflight, operator/debug surface, proof observability, coordination intelligence, and persisted-artifact guardrail notes from May 7.

## 3. Audit summary

The safest commercial package is not “city operations automated.” It is:

> **A concierge municipal execution proof service for one metro area: office reality checks, packet submission attempts, and posting proof, with structured evidence and operator-reviewed next steps.**

The strategic product under that package is still dispatch compounding:

> reviewed municipal reality -> compact operational memory -> safer next dispatch

That loop is the moat. The sellable surface should stay small enough that every order can produce a reviewed result, a bounded next-step recommendation, and eventually a replayable proof bundle.

## 4. What is already supported

### 4.1 Commercial packaging is supported at the planning level

The planning docs consistently support three Phase 1 launch offers:

1. **Counter Reality Check** — confirm office/window/form/routing reality.
2. **Packet Submission Attempt** — attempt filing and classify accepted/rejected/redirected/blocked.
3. **Posting Compliance Check** — prove visible notice/posting state with checklist evidence.

These are sellable as concierge services because they have:

- clear buyer pain
- bounded deliverables
- explicit exclusions
- required intake fields
- pricing levers
- follow-on offer paths
- a one-metro pilot discipline

### 4.2 The first proof anchor supports conservative operator learning

The current proof anchor, `redirect_outdated_packet_001`, supports a conservative claim:

- one reviewed municipal interaction can be converted into compact, inspectable artifacts
- those artifacts can preserve safe and blocked claims together
- operator-facing prep can improve without turning into worker-copyable doctrine
- downstream inspection/observability surfaces can render the same boundaries without raw transcript dependence

This is useful packaging evidence, but only for an operator-reviewed concierge pilot. It is not yet evidence for autonomous dispatch or broad city playbooks.

### 4.3 Transport boundaries are well-defined

Acontext is ready to be described internally as a future transport seam, not the source of truth.

The docs and fixtures already establish this rule:

- reviewed artifacts are truth
- Acontext carries compact reviewed meaning
- retrieval must preserve safe claims, blocked claims, tone, placement, copyability boundary, and readiness flags
- preflight is not a live write/retrieve proof

This is packaging-relevant because the offer can promise structured records and replayable evidence now, while avoiding claims about a live memory backend until it is actually verified.

### 4.4 Guardrails are stronger than the commercial surface

The proof spine is currently stricter than the sales package needs to be. That is good.

Existing local artifacts and guardrails focus on:

- claim-boundary preservation
- operator/debug visibility
- proof observability
- coordination intelligence
- dropped-blocked-claim failure modes
- readiness overclaim detection
- worker-copyability drift prevention

This gives the concierge package a credible internal operating discipline even before broad UI or live transport exists.

## 5. What can be packaged now

### 5.1 Package name

Use a concrete offer family, not a platform claim:

> **City Counter Ops — verified municipal errands with structured next steps**

Alternative copy:

> **Municipal Proof Desk — office checks, filing attempts, and posting proof with reviewed outcomes**

Avoid “autonomous city ops,” “smart-city OS,” or “we handle any city workflow.”

### 5.2 Initial sellable slice

Package only a concierge pilot with manual operator review:

- one metro area
- one office or site per base order
- one primary municipal step per order
- one proof objective per order
- explicit same-day / next-business-day attempt windows only where operationally realistic
- all rejected, redirected, blocked, or inconclusive outcomes reviewed before customer-facing closure

### 5.3 First menu

Launch menu should stay at three offers:

| Offer | Sellable promise | Output | Internal proof dependency |
|---|---|---|---|
| Counter Reality Check | “We verify the office/window/form/routing reality.” | Structured answer, source type, redirect target if any, next step. | Reviewed result + operator next-step review. |
| Packet Submission Attempt | “We attempt filing and prove what happened.” | Accepted/rejected/redirected/blocked classification, evidence, next required step. | Current `redirect_outdated_packet_001` anchor is closest here. |
| Posting Compliance Check | “We verify visible posting/compliance state.” | Wide/close evidence, checklist pass/fail, remediation next step. | Planning-supported; needs its own proof fixture before strong automation claims. |

### 5.4 Customer-facing promise

Use this promise sentence:

> We promise a verified attempt window, evidence of what happened, and a structured next-step output — not city cooperation, approval, or legal sufficiency we cannot control.

### 5.5 What can be included in sales materials now

Safe language:

- verified office visit / site visit attempt
- structured evidence packet
- accepted / rejected / redirected / blocked / inconclusive outcome classification
- source type separation: observed, heard, documented
- reviewed next-step recommendation
- follow-on task suggestion when the outcome requires repair, reroute, or revisit

Avoid language that implies:

- guaranteed approval
- legal interpretation
- city relationship or influence
- unlimited retries
- broad multi-office handling in one base order
- worker instructions learned from a single proof anchor are generally reusable

## 6. What remains blocked

The following must remain out of sales copy, public roadmap language, and broad UI readiness labels until separately proven:

- live Acontext sink readiness
- live write/retrieve transport parity
- runtime parity between local replay and live systems
- session rebuild readiness as an operational product claim
- closure proof as a completed milestone
- worker-copyable municipal doctrine
- polished Review Console readiness
- Office Memory View readiness
- broad operator workflow readiness
- multi-jurisdiction playbooks
- autonomous city dispatch

The docs are especially clear on two boundaries:

1. **Acontext is transport, not truth.** It can carry reviewed meaning later, but cannot upgrade the meaning.
2. **Safe and blocked claims travel together.** A package that hides blocked claims is not safe to sell or automate.

## 7. Packaging gap analysis

### Gap A — sellable offer sheet does not yet point to proof artifacts

The service catalog is commercially useful, but it does not yet map each offer to:

- exact intake fields
- required review artifacts
- customer-facing output fields
- blocked-claim language
- follow-on task triggers

This is the most immediate packaging gap.

### Gap B — only one proof anchor exists

The current anchor is valuable but narrow: a redirect/outdated-packet case. It supports Packet Submission Attempt discipline more than the other two launch offers.

Before broader packaging, add at least:

- one Counter Reality Check proof fixture
- one Posting Compliance Check proof fixture

These should preserve the same claim-boundary discipline.

### Gap C — customer copy needs anti-overclaim defaults

The docs contain the right exclusions, but an actual landing/sales page could easily drift. Copy should be written from the blocked list first, then promises second.

### Gap D — pricing exists as logic, not SKU cards

Pricing levers are defined, but the sellable SKU card is not yet day-ready. Keep pricing simple until the first concierge runs produce real time/cost data.

### Gap E — follow-on bundles should wait

Rejection Diagnosis, Office Redirect Follow-Through, Permit Follow-Through Bundle, and Multi-Site Posting Verification Bundle are good later products, but should not be front-door offers until Phase 1 has repeated outcomes.

## 8. Smallest next packaging step

Create one internal **Phase 1 CaaS offer card pack** with exactly three one-page cards:

1. Counter Reality Check
2. Packet Submission Attempt
3. Posting Compliance Check

Each card should contain only:

- buyer pain
- sellable promise
- required intake fields
- included deliverables
- explicit exclusions
- outcome statuses
- review gate
- customer-facing output fields
- follow-on task triggers
- forbidden claims
- proof status: `planning_supported`, `local_anchor_supported`, or `needs_fixture`

Recommended proof status today:

- Counter Reality Check: `planning_supported`; needs first proof fixture
- Packet Submission Attempt: `local_anchor_supported` for redirect/outdated-packet behavior only
- Posting Compliance Check: `planning_supported`; needs first proof fixture

Do not build a broad city landing page before this pack exists. The offer cards are the bridge between the planning stack and a sellable pilot.

## 9. Top packaging recommendations

1. **Sell a concierge proof service, not a platform.** The first package should be manual, narrow, and operator-reviewed.
2. **Lead with three offers only.** Counter Reality Check, Packet Submission Attempt, and Posting Compliance Check are enough for Phase 1.
3. **Map every offer to reviewed artifacts.** Each SKU needs intake, deliverables, review gate, output fields, follow-on triggers, and forbidden claims.
4. **Use the current proof anchor only where it fits.** It supports conservative Packet Submission Attempt packaging; it does not justify broad doctrine.
5. **Keep Acontext out of customer promises for now.** Internally it is a future transport seam. Customer value should be evidence, reviewed outcomes, and structured next steps.

## 10. Daytime pickup

Best next daytime task:

> Draft the three Phase 1 offer cards and add proof-status labels to each card, without changing live product copy yet.

Acceptance gate:

- all three cards preserve exclusions and forbidden claims
- Packet Submission Attempt references the current local anchor conservatively
- Counter Reality Check and Posting Compliance Check are marked as needing first proof fixtures
- no card implies broad workflow automation, multi-jurisdiction rollout, live Acontext readiness, or worker-copyable doctrine
