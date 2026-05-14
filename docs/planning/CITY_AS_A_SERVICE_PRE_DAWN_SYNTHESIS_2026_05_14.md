# City-as-a-Service Pre-Dawn Synthesis — 2026-05-14

> Session: 04:00 America/New_York dream synthesis
> Scope: Execution Market AAS / City-as-a-Service only
> Priority source: `~/clawd/DREAM-PRIORITIES.md`
> Stale payload tracks intentionally skipped: AutoJob, Frontier Academy, KK v2, KarmaCadabra v2

## 1. Governing decision

The cron payload asked for AutoJob, Frontier Academy, and KK v2 work, but `~/clawd/DREAM-PRIORITIES.md` explicitly stops those tracks during dreams. I followed the priority file and continued only Execution Market AAS / City-as-a-Service.

## 2. What landed

Incident Verification now has its separate explicit hold decision over the internal/admin sample output:

- Runtime: `mcp_server/city_ops/incident_verification_sample_output_review_decision.py`
- Artifact: `mcp_server/city_ops/fixtures/aas_package_ladder/incident_verification_sample_output_review_decision.json`
- Tests: `mcp_server/tests/city_ops/test_incident_verification_sample_output_review_decision.py`
- Export: `mcp_server/city_ops/__init__.py`
- Implementation note: `docs/planning/CITY_AS_A_SERVICE_INCIDENT_VERIFICATION_SAMPLE_OUTPUT_REVIEW_DECISION_IMPLEMENTATION.md`

Safe claim earned:

```text
incident_verification_sample_output_review_decision_landed
```

Focused verification:

```text
14 passed
```

## 3. Pattern recognition

The useful 4am connection is that Execution Market AAS is now converging on a repeatable coordination primitive:

```text
reviewed evidence -> internal truth -> operator-readable packet -> customer-output shape -> explicit hold/approval decision
```

That primitive now spans three adjacent families:

| Family | Current conservative state | Still blocked |
|---|---|---|
| Compliance Desk | Explicit sample-output hold decision recorded | legal/regulator/inspection/compliance guarantees; customer/public/dispatch/reputation/live-runtime readiness |
| Document / Handoff Logistics | Explicit sample-output hold decision recorded | legal/notarial/private-identity/acceptance/filing/custody guarantees; customer/public/dispatch/reputation/live-runtime readiness |
| Incident Verification | Explicit sample-output hold decision recorded | emergency/safety/repair/insurance/SLA/official-report/fault/liability claims; customer/public/dispatch/reputation/live-runtime readiness |

The multiplier is not that EM can launch more verticals tomorrow. The multiplier is that every vertical can use the same proof ladder while preserving domain-specific blocked claims beside safe claims.

## 4. IRC / memory coordination insight

The strongest scalable coordination pattern is still compact artifact handoff, not transcript archaeology.

A future agent should be able to resume from:

```text
package_family_id
safe_to_claim[]
do_not_claim_yet[]
ladder_boundary.covered_steps[]
readiness false flags
next_smallest_proof
```

That is the bridge from IRC-style coordination to product strategy: fast agents coordinate through reviewed packets and explicit blocked claims, not through raw chat, private operator context, or vague “we learned this” summaries.

## 5. Cross-project intelligence flow, safely scoped

The cross-project lesson is general, but tonight's output stays inside Execution Market AAS:

- memory systems are useful only when they move reviewed meaning, not raw context
- agent coordination scales when every handoff names the exact artifact, safe claim, blocked claims, and next gate
- reputation should attach only after reviewed customer/worker outcomes exist, not from internal samples or operator-held packets
- dispatch should consume proof-preserving packets only after the promotion gate says dispatch is allowed

## 6. Current honest label

The adjacent-AAS ladder has now proven a conservative repeated path across three families, but it is still internal/admin only.

Still false / blocked across the package set:

- customer copy/customer delivery/public catalog/control-pilot readiness
- public routes or front-door SKUs
- live dispatch or autonomous dispatch
- ERC-8004 reputation receipts
- live Acontext sink or runtime parity
- exact GPS/raw metadata exposure
- worker Skill DNA or worker-copyable doctrine
- legal/regulator/emergency/safety/repair/insurance/SLA/official-report/fault/liability authority unless a separate future gate proves it

## 7. Next safest daytime move

Do not publish by default.

If customer exposure becomes desired, the next safe move is not a catalog. It is one separate human-operator approval artifact for exactly one held sample/text boundary, naming:

1. exact approved text
2. redactions
3. delivery path
4. still-blocked claims
5. readiness flags that remain false

Otherwise, pause adjacent-family expansion and use the three-family ladder as the product proof for AAS packaging discipline.
