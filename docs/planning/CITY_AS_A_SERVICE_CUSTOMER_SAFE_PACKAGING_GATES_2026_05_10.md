# City as a Service — Customer-Safe Packaging Gates 2026-05-10

> Status: 7 AM planning synthesis; internal packaging gate only
> Scope: Execution Market AAS / City-as-a-Service only
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`
> Non-goal: this is not customer copy, not a public catalog, and not a
> route/dispatch/reputation/Acontext implementation plan.

## 1. Why this doc exists

The May 10 handoff says the internal/admin route proof chain is boxed in and
that live Acontext remains blocked before any sink write. The May 7 packaging
audit and May 8 offer cards already define the narrow concierge package shape.

This synthesis adds only one missing planning layer: **a customer-safe packaging
gate checklist** for deciding when an internal CaaS offer card may be prepared
for a controlled concierge pilot without accidentally sounding like a finished
platform.

It deliberately does not add:

- route layers
- customer-facing copy
- public service-catalog claims
- autonomous dispatch claims
- reputation or worker Skill DNA claims
- live Acontext readiness claims
- GPS or raw metadata exposure policy
- worker-copyable municipal doctrine

## 2. Current conservative baseline

Safe internal baseline after the May 10 morning handoff:

- Phase 1 reviewed fixture coverage exists locally for the current proof set.
- Internal/admin proof carriers exist through the compact route handoff packet.
- Safe claims and blocked claims are already expected to travel together.
- Live Acontext preflight exists but is blocked before sink write.
- The next product-significant proof remains one live write/retrieve parity pass
  only after Docker, Acontext SDK, local API, and dashboard prerequisites are
  real.

This is enough to keep shaping a concierge pilot package internally. It is not
enough to publish a broad customer catalog or imply live automation.

## 3. Packaging promotion ladder

Use this ladder before any CaaS package moves from internal scoping to a
controlled customer pilot.

### Level 0 — planning concept

- Allowed use: internal discussion only.
- Required evidence: source planning doc and explicit forbidden claims.
- Must still block: customer, live, dispatch, reputation, GPS/metadata, and
  worker-doctrine claims.

### Level 1 — internal offer card

- Allowed use: operator scoping and review rehearsal.
- Required evidence: intake fields, outcome statuses, review gate, and forbidden
  claims list.
- Must still block: customer copy, public catalog, live Acontext, autonomous
  dispatch, reputation, and worker instructions.

### Level 2 — fixture-supported offer

- Allowed use: internal pilot rehearsal.
- Required evidence: at least one reviewed fixture, normalized output,
  adjacent safe/blocked claims, and proof status label.
- Must still block: broad repeatability, multi-jurisdiction, live memory,
  public route, and legal/regulator claims.

### Level 3 — controlled concierge pilot candidate

- Allowed use: human-reviewed pilot with explicit limitations.
- Required evidence: fixture-supported offer, operator review checklist,
  customer-safe output schema, and rollback/blocked-outcome handling.
- Must still block: platform readiness, automated routing, reputation updates,
  worker-copyable doctrine, and exact GPS/raw metadata exposure.

### Level 4 — repeatable package candidate

- Allowed use: later, after repeated reviewed outcomes.
- Required evidence: multiple reviewed outcomes with stable registry coverage
  and no claim-boundary drift.
- Must still block: broad automation until live transport/runtime parity and
  operational evidence separately pass.

The current Phase 1 package should be treated as **Level 1 to Level 2 depending
on the offer and fixture coverage**, not as Level 3+ by default.

## 4. Gate checklist for each Phase 1 offer

Before a package is exposed even in a controlled concierge pilot, require a
yes/no answer for every gate below.

### Gate A — evidence support

- Does the offer have a named proof status label?
- Does at least one reviewed fixture exist for the specific offer behavior being
  claimed?
- Are limitations tied to the exact fixture behavior rather than generalized
  across offices or jurisdictions?
- Is the proof source local reviewed artifact data, not raw transcript memory?

If any answer is no, keep the offer internal-only.

### Gate B — customer-safe output shape

- Does the customer output schema separate observed, heard, documented,
  customer-supplied, and mixed sources?
- Does the output include an outcome status without implying city cooperation or
  approval?
- Does the structured next step avoid legal advice and regulator acceptance
  language?
- Does every inconclusive, blocked, rejected, or redirected outcome require
  operator review before closure?

If any answer is no, do not prepare customer-visible materials.

### Gate C — blocked-claim adjacency

- Are `safe_to_claim[]` and `do_not_claim_yet[]` adjacent in the underlying
  artifact or review packet?
- Does the package preserve blocked claims in handoff summaries?
- Does the package fail closed if blocked claims are dropped or promoted?
- Is every readiness flag still false unless its separate proof gate has passed?

If any answer is no, the package is not customer-safe.

### Gate D — prerequisite gates before stronger language

The following gates must pass before stronger package language is allowed:

- Live Acontext language requires successful preflight, one write/retrieve pass,
  and parity assertion.
- Runtime parity language requires a separate runtime parity artifact, not just
  route or fixture parity.
- Dispatch language requires separate operational evidence and must not be
  inferred from proof carriers.
- Reputation language requires a separate ERC-8004/reputation proof path.
- Worker instruction language requires a separate worker-safety and copyability
  review.
- GPS/metadata language requires a separate privacy review that avoids exposing
  exact location data.

Until those gates pass, keep these as blocked claims, not roadmap promises.

## 5. Offer-specific status as of this synthesis

### Counter Reality Check

- Current safe internal status: fixture-supported local planning/coverage exists,
  but claims must stay narrow.
- Customer-safe gate result: not automatically customer-ready.
- Next prerequisite: confirm output schema and review gate against the reviewed
  fixture before any pilot wording.

### Packet Submission Attempt

- Current safe internal status: strongest local anchor, especially
  redirect/outdated-packet behavior.
- Customer-safe gate result: candidate only for tightly bounded concierge pilot
  review.
- Next prerequisite: keep claim tied to the exact reviewed behavior; no broad
  filing-success or office-reuse claim.

### Posting Compliance Check

- Current safe internal status: fixture-supported local planning/coverage exists,
  but claims must stay narrow.
- Customer-safe gate result: not automatically customer-ready.
- Next prerequisite: confirm evidence/output schema and blocked-claim
  preservation before any pilot wording.

This status list is intentionally conservative. It does not publish the offers;
it only tells operators what must be true before a package can be safely
prepared.

## 6. Required package record before pilot use

Every controlled-pilot candidate should have one internal package record with:

```json
{
  "package_id": "city_counter_ops.<offer>.<date>",
  "promotion_level": "controlled_concierge_pilot_candidate",
  "offer": "counter_reality_check|packet_submission_attempt|posting_compliance_check",
  "proof_status_label": "string",
  "reviewed_fixture_ids": ["string"],
  "safe_to_claim": ["string"],
  "do_not_claim_yet": ["string"],
  "customer_output_schema_reviewed": false,
  "operator_review_required_before_closure": true,
  "forbidden_claims_preserved": true,
  "live_acontext_ready": false,
  "runtime_parity_proven": false,
  "autonomous_dispatch_ready": false,
  "reputation_ready": false,
  "worker_copyable_doctrine_ready": false,
  "exact_gps_or_raw_metadata_exposure_allowed": false
}
```

The booleans are part of the safety contract. They should not flip to true from
packaging work alone.

## 7. Next smallest non-overlapping step

Do not add more route wrappers by default. Do not draft public copy yet.

The next planning-safe step was to create one internal package record for
**Packet Submission Attempt** only, because it has the strongest local proof
anchor. That record now exists as
`mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_packet_submission_internal_package_record.json`
and is implemented by
`mcp_server/city_ops/phase1_packet_submission_internal_package_record.py`. It
references only the existing reviewed fixture ID, keeps safe and blocked claims
adjacent, and leaves all live/dispatch/reputation/GPS and worker-doctrine
readiness flags false.

This earns only `phase1_packet_submission_internal_package_record_landed`; it
does not make customer copy, public catalog language, route wrappers, filing
success, office reuse, live Acontext, dispatch, reputation, GPS/raw metadata
exposure, or worker-copyable doctrine ready.

If Acontext prerequisites become available first, prioritize the May 10 handoff
path instead: rerun preflight and perform exactly one live write/retrieve parity
pass before any live-memory language is allowed.
