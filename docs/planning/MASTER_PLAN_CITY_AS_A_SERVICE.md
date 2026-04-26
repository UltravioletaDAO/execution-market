# MASTER PLAN — City as a Service (CaaS) on Execution Market

> Last updated: 2026-04-24
> Status: active concept expansion
> Dream priority alignment: Execution Market AAS plans only

## 1. Thesis

City as a Service is an Execution Market vertical where agents can buy verified municipal-world execution the same way they buy compute: permits checked, storefronts verified, signs photographed, counters visited, forms submitted, inspectors coordinated, notices posted, queues endured, and local reality converted into structured evidence.

Execution Market already solves the hard substrate:
- agent-authenticated task creation
- escrowed payment + approval flow
- human worker marketplace
- evidence collection + verification
- portable identity/reputation

CaaS packages that substrate into a vertical operating system for anything that touches city bureaucracy, street-level reality, and local compliance.

## 2. Why this vertical fits Execution Market

### 2.1 The core mismatch
AI agents are strong at:
- planning
- document preparation
- policy lookup
- multi-step orchestration
- follow-up automation

Cities still require:
- physical presence
- local inspection
- human signatures
- in-person submissions
- line waiting
- visual verification
- jurisdiction-specific interpretation

That mismatch is exactly Execution Market's edge.

### 2.2 Why cities first
Compared with generic local errands, city workflows have:
- repeated demand
- high pain
- high urgency
- expensive delays
- strong evidence needs
- structured steps that agents can orchestrate well

A missed permit step can cost far more than the task bounty. That makes EM's human execution layer economically obvious.

## 3. Product definition

### 3.1 One-line definition
**City as a Service = municipal interface infrastructure for agents and businesses.**

### 3.2 What customers buy
Customers do **not** buy raw gig work. They buy outcomes like:
- "Verify this permit office requirement today"
- "Submit this packet and prove it was accepted"
- "Check whether this storefront posting is still displayed"
- "Photograph construction progress and code notices"
- "Stand in line, capture answers, and return structured results"
- "Visit city hall and confirm the exact form/version being used now"

## 4. Customer segments

### Segment A — SMB operators
Who: restaurants, contractors, landlords, retail operators, event organizers.
Needs:
- permit handling
- signage verification
- renewal checks
- local compliance errands

### Segment B — Real estate / property ops
Who: property managers, leasing ops, investors, title/compliance teams.
Needs:
- posted notice verification
- vacancy / exterior condition checks
- permit/status lookup
- occupancy / inspection follow-through

### Segment C — AI-native operations teams
Who: agents or startups automating back-office workflows.
Needs:
- physical fallback when APIs stop at the city boundary
- structured evidence from municipal touchpoints
- repeatable local execution in many jurisdictions

### Segment D — Legal / filing / expediting workflows
Who: permit runners, paralegal ops, compliance firms.
Needs:
- overflow capacity
- evidence-backed runs
- city-specific task decomposition
- queue outsourcing

## 5. Initial service catalog

### 5.1 Permit & license ops
- permit office visit
- counter requirement confirmation
- packet drop-off with proof
- renewal status check
- fee payment verification
- rejected packet diagnosis

### 5.2 Compliance visibility
- storefront posting verification
- job-site notice verification
- ADA/signage/photo audits
- sanitation / posted-grade capture
- curbside / zone signage capture

### 5.3 Local document logistics
- notarization run coordination
- copy / print / bind / deliver packet
- wet-signature collection relay
- certified mailing / hand-delivery proof

### 5.4 Field intelligence
- office open/closed reality check
- average queue snapshot
- department routing clarification
- on-site policy drift detection
- city-specific "what actually happens" capture

### 5.5 Hearings / appointments / waits
- stand in line
- hold appointment slot presence
- pre-check counter readiness
- post-hearing document pickup

## 6. Canonical task primitives

CaaS can be decomposed into reusable EM primitives:

1. **verify_place** — confirm office/location/signage exists and is open
2. **capture_notice** — photograph and timestamp municipal/public notices
3. **counter_question** — ask a defined question and capture structured answer
4. **submit_packet** — deliver documents and prove acceptance/rejection
5. **queue_wait** — maintain presence until handoff point
6. **status_pull** — retrieve current local status not available online
7. **site_audit** — capture checklist-based field observations
8. **posting_proof** — show a legally required notice is posted
9. **route_probe** — identify which office/window/process actually applies
10. **handoff_proof** — prove physical transfer of materials

These primitives should later map to templates in the dashboard and API.

## 7. Evidence model by task type

### Required evidence examples

**Counter question**
- timestamped text response
- photo of office / counter signage
- optional audio summary
- worker confidence + exact wording field

**Submit packet**
- receipt or stamped copy
- photo of accepted packet / counter receipt
- structured status: accepted / rejected / redirected
- rejection reason enum + free text

**Posting proof**
- wide photo for context
- close-up photo for legibility
- timestamp proof
- optional geo verification where safe

**Queue wait**
- arrival proof
- elapsed time proof
- handoff completion proof
- outcome classification

### Important note
CaaS depends less on generic photo upload and more on **structured municipal outcome capture**. The winning product surface is not “upload evidence”; it is “convert messy city interaction into normalized operator-grade data.”

## 8. Workflow architecture

### 8.1 Agent-led orchestration loop
1. Agent/user defines desired municipal outcome
2. EM decomposes into CaaS template + evidence contract
3. Worker executes physical step
4. Evidence returns in structured schema
5. Agent decides next step automatically
6. EM may spawn follow-on tasks until workflow completes

This makes CaaS a strong fit for chained task graphs, not just one-off gigs.

### 8.2 Example multi-step flow
**Open a food business permit workflow**
1. verify current permit office and hours
2. counter_question on exact packet/version required
3. submit_packet draft v1
4. collect rejection reasons if rejected
5. agent revises docs
6. resubmit
7. posting_proof after issuance
8. site_audit before inspection

Execution Market becomes the physical execution engine under a city workflow copilot.

## 9. Marketplace design implications

### 9.1 Worker specialization
CaaS likely needs worker tags such as:
- permit runner
- courthouse/city hall runner
- notary-capable
- bilingual counter operator
- document courier
- construction-site verifier
- hearing / appointment standby

### 9.2 Reputation dimensions
Generic reputation is not enough. Add vertical signals later:
- submission accuracy
- first-pass acceptance rate
- office familiarity by jurisdiction
- queue reliability
- document handling quality
- municipal response fidelity

### 9.3 Geography model
City work is hyperlocal. Good matching will need:
- jurisdiction tags
- neighborhood / borough / district affinity
- known office coverage radius
- transit-aware ETA
- office-hours-aware dispatching

## 10. SaaS packaging

### 10.1 Product tiers

**Tier 1 — Self-serve city tasks**
- template-driven task posting
- pay per task
- basic evidence outputs

**Tier 2 — City workflow automation**
- chained task orchestration
- saved jurisdiction playbooks
- operator dashboard
- structured audit history

**Tier 3 — Embedded CaaS API**
- external products call EM for municipal execution
- webhook/event-driven workflow state
- white-label or partner surfaces

### 10.2 Packaging insight
The best business may not be “task marketplace for city errands.”
It may be **municipal operations infrastructure** sold as:
- API
- workflow product
- vertical dashboard
- managed operations layer

## 11. Recommended first wedge

### Best initial wedge: **Permit runners + compliance proofs for SMBs**

Why this wedge wins:
- frequent recurring need
- clear willingness to pay
- easy before/after ROI story
- many steps already fit EM primitives
- low conceptual burden versus broader “city OS” vision

#### Example starter offers
- permit office verification pack
- permit packet drop-off proof
- storefront compliance photo audit
- posting verification bundle
- city counter Q&A task

## 12. UX / product surfaces to add later

### Dashboard surfaces
- city task templates
- jurisdiction selector
- permit/compliance outcome forms
- municipal evidence schema presets
- workflow timeline for multi-step cases

### API / schema ideas
- `workflow_type: city_ops`
- `jurisdiction`
- `office_type`
- `required_outcome`
- `structured_answers`
- `redirected_to`
- `accepted_rejected_pending`
- `next_recommended_step`

### Ops surfaces
- office knowledge base
- jurisdiction playbooks
- common rejection reasons by city
- SLA by office/time/day

## 13. Risks and constraints

### Operational risks
- city processes are inconsistent
- rules drift offline faster than websites update
- workers may paraphrase inaccurately
- office staff may refuse photos/audio
- turnaround is office-hours bounded

### Product risks
- too broad if launched as “everything city-related”
- hard to standardize across jurisdictions too early
- may require stronger worker training than generic tasks

### Mitigation
- start with narrow templates
- structure outcomes aggressively
- separate "observed" vs "heard" vs "documented"
- build office/jurisdiction memory over time

## 14. Moat thesis

CaaS becomes defensible when EM accumulates:
- jurisdiction-specific playbooks
- worker reputation in municipal workflows
- structured evidence datasets
- outcome histories by office/process
- real-world municipal process intelligence

The moat is not just labor supply. It is **municipal reality memory**.

## 15. Concrete roadmap

### Phase 0 — Planning / spec
- define CaaS service taxonomy
- define first 5 templates
- define municipal evidence schemas
- define jurisdiction metadata model

### Phase 1 — Template MVP
- add dashboard templates for:
  - counter_question
  - submit_packet
  - posting_proof
  - site_audit
- add structured result forms
- add jurisdiction fielding

### Phase 2 — Operator intelligence
- office outcome summaries
- common rejection analytics
- worker specialization tags
- office-hours and routing memory

### Phase 3 — Workflow product
- multi-step municipal workflow chaining
- next-step recommendation engine
- city workflow dashboards for operators

### Phase 4 — CaaS API
- external systems create municipal execution workflows programmatically
- webhook callbacks for workflow state changes
- partner integrations for permit/compliance SaaS

## 16. Immediate next docs worth creating

1. `CITY_AS_A_SERVICE_SERVICE_CATALOG.md`
2. `CITY_AS_A_SERVICE_EVIDENCE_SCHEMAS.md`
3. `CITY_AS_A_SERVICE_JURISDICTION_MODEL.md`
4. `CITY_AS_A_SERVICE_GO_TO_MARKET.md`
5. `CITY_AS_A_SERVICE_TEMPLATE_SPECS.md`
6. `CITY_AS_A_SERVICE_OPERATOR_PLAYBOOK.md`

## 17. Strong recommendation

Do **not** pitch this first as a vague smart-city concept.
Pitch it as:

> **Execution Market for permits, postings, inspections, and city-counter reality.**

That is concrete, painful, urgent, and already aligned with EM's strengths.

## 18. Summary

City as a Service is one of the cleanest AAS verticals for Execution Market because it turns the hardest non-API surface in business operations — the city itself — into a programmable execution layer.

If EM is the universal human execution substrate, CaaS is the first vertical where:
- pain is constant
- demand repeats
- evidence matters
- agent orchestration compounds value

This feels real, monetizable, and sharply on-strategy.

## 19. Ideal customer profiles (ICPs)

### ICP 1 — Multi-location SMB operator
Examples:
- restaurant groups
- contractors operating across municipalities
- retail franchises
- laundromats, salons, medical offices

Pain profile:
- every city has slightly different forms, office rules, and enforcement behavior
- local admin work steals owner/operator time
- a missed posting, renewal, or permit handoff can delay revenue

What they buy first:
- permit office verification
- packet drop-off with proof
- signage / notice compliance audits
- renewal status checks

Why they convert:
- obvious ROI against owner or manager time
- recurring demand
- fast before/after story

### ICP 2 — Permit expediters and compliance firms
Pain profile:
- demand spikes are lumpy
- local field coverage is inconsistent
- they need overflow execution, not another generic gig marketplace

What they buy first:
- white-labeled runner capacity
- city-counter Q&A tasks
- hearing / line-wait coverage
- proof-backed resubmission loops

Why they convert:
- Execution Market becomes burst capacity plus evidence normalization

### ICP 3 — Real estate and property operations teams
Pain profile:
- occupancy, inspection, notice posting, and exterior verification require local physical presence
- internal teams waste time coordinating one-off vendors

What they buy first:
- vacancy / exterior condition checks
- permit/status verification
- posting proof
- hearing / inspection follow-through

### ICP 4 — AI-native back-office operators
Pain profile:
- software handles docs and reminders, but the city boundary still breaks automation
- they need a programmable human execution layer with structured outputs

What they buy first:
- API-triggered office visits
- route probes
- packet submission with normalized outcomes
- chained municipal workflows

## 20. Service templates that should exist first

The goal is not a giant catalog. The goal is a tiny set of repeatable templates with high information value.

### Template A — Counter Question
Best for:
- "what form/version is actually required right now?"
- "which window handles this permit now?"

Inputs:
- jurisdiction
- office/location
- exact question
- acceptable answer format
- whether a same-day answer is required

Outputs:
- structured answer
- answer confidence
- source type: heard / observed / documented
- office photo and timestamp
- redirect destination if bounced

### Template B — Packet Submission
Best for:
- filing documents in person
- getting acceptance/rejection proof

Inputs:
- packet checklist
- acceptance criteria
- rejection taxonomy
- instructions for what to do if redirected

Outputs:
- accepted / rejected / redirected
- receipt or stamped copy
- rejection reasons
- next required step
- office / clerk notes

### Template C — Posting Proof
Best for:
- storefront notices
- construction permits
- hearing notices
- legally required public display checks

Inputs:
- notice type
- visibility requirements
- legibility requirements
- repeat cadence if recurring

Outputs:
- wide photo
- close-up photo
- pass/fail checklist
- optional repeat schedule for re-checks

### Template D — Site Audit
Best for:
- exterior compliance
- signage / accessibility / condition sweeps
- pre-inspection readiness

Inputs:
- checklist
- must-capture angles
- fail conditions
- escalation threshold

Outputs:
- per-item pass/fail
- annotated observations
- photo set
- recommended next action

### Template E — Queue Wait + Handoff
Best for:
- line waiting
- appointment presence
- document pickup or handoff

Inputs:
- arrival deadline
- max wait budget
- handoff condition
- fallback if office closes or refuses service

Outputs:
- arrival proof
- elapsed wait
- handoff result
- blocked reason if unresolved

## 21. Proposed structured schema additions

These are product-facing fields, not necessarily final database names.

### Workflow-level metadata
- `vertical = city_ops`
- `workflow_template`
- `jurisdiction_name`
- `jurisdiction_type` (city, county, state office, special district)
- `office_name`
- `office_type`
- `time_sensitivity`
- `office_hours_confidence`
- `follow_on_allowed`

### Evidence-level metadata
- `source_type` = observed | heard | documented
- `outcome_status` = completed | accepted | rejected | redirected | blocked | inconclusive
- `confidence_score`
- `redirect_target`
- `rejection_reasons[]`
- `next_step_recommendation`
- `worker_notes_structured`

### Ops intelligence metadata
- `office_visit_count`
- `office_reliability_score`
- `common_rejection_code`
- `jurisdiction_playbook_version`
- `worker_familiarity_score`

## 22. Jurisdiction memory model

The long-term moat is a memory layer keyed by office + workflow type + jurisdiction.

### What EM should remember over time
- which office actually handles a request
- common redirect patterns
- office-specific acceptance quirks
- seasonal or weekday timing patterns
- whether photos are tolerated at a location
- which workers reliably succeed there

### Minimal memory objects
1. **Office profile**
   - name
   - address / district metadata
   - likely hours
   - photo policy
   - common workflows

2. **Workflow playbook**
   - task type
   - required documents
   - common rejection causes
   - known redirect targets
   - expected elapsed time

3. **Observed episode log**
   - timestamp
   - worker
   - outcome
   - structured observations

This turns EM from a task router into a municipal intelligence network.

## 23. Pricing and SLA logic

### Recommended pricing posture
Do not sell the first version as cheap labor.
Sell it as avoided delay, avoided confusion, and verified local reality.

### Suggested pricing building blocks
- base dispatch fee
- urgency multiplier
- queue-time surcharge
- document complexity surcharge
- retry/resubmission add-on
- jurisdiction difficulty multiplier

### Example starter packages
- **Counter Reality Check** — same-day office verification + one structured answer
- **Packet Drop-Off Proof** — submission attempt + acceptance/rejection evidence
- **Compliance Photo Sweep** — checklist-based site audit with pass/fail output
- **Permit Follow-Through** — chained steps until a defined municipal checkpoint is reached

### SLA framing
The product promise should be framed as:
- response window
- attempt window
- evidence completeness
- escalation behavior if blocked

Not as a naive guarantee that the city itself will cooperate.

## 24. Workflow chaining opportunities

CaaS gets much stronger when it is not trapped as a one-task marketplace feature.

### Example chain: restaurant permit recovery
1. route_probe to confirm correct office
2. counter_question to confirm exact live requirement
3. packet_submission attempt
4. rejection normalization if bounced
5. agent updates packet
6. resubmission
7. posting_proof after approval

### Example chain: property compliance loop
1. exterior site audit
2. notice posting proof
3. hearing attendance / queue wait
4. post-hearing document pickup
5. follow-up remedial task if needed

This is where Execution Market's orchestration layer compounds value.

## 25. Worker network design for CaaS

### Early worker archetypes
- permit runner
- document courier
- bilingual counter operator
- property compliance field auditor
- hearing standby runner
- construction-site verifier

### What workers need beyond generic marketplace tooling
- better structured forms
- jurisdiction-specific instructions
- explicit "if redirected, do X" playbooks
- quality scoring tied to fidelity, not just speed

### Training insight
CaaS probably needs lightweight worker enablement packs:
- how to distinguish observed vs heard info
- how to capture legible evidence
- how to report uncertainty without inventing facts
- how to handle photo-restricted counters

## 26. Go-to-market recommendation

### Recommended launch order
1. Miami-area pilot with narrow templates
2. one or two high-friction verticals (permits + posting/compliance)
3. convert repeated workflows into operator playbooks
4. then expose API/embedded surfaces

### Best initial message
Not:
- "smart city orchestration"
- "city AI platform"

Yes:
- **"We handle the physical city steps your software can't reach."**
- **"Permits, postings, inspections, and city-counter proof — on demand."**

### Distribution angles
- permit expediters
- contractor back offices
- property ops teams
- compliance consultants
- AI-native ops startups

## 27. Product decisions worth making soon

1. Should CaaS live as a named vertical in the dashboard, or start as hidden templates under generic tasks?
2. Which 3 templates are mandatory for a pilot?
3. What minimum structured fields are required to make municipal outcomes replayable and analyzable?
4. Should jurisdiction memory be human-curated first, machine-extracted second?
5. What escalation policy applies when city staff refuse evidence capture?

## 28. Sharpest next step

The next smart move is not more abstract strategy.
It is to turn this plan into 3 implementation-ready specs:
- template spec
- evidence schema spec
- jurisdiction memory spec

Once those exist, EM can prototype City as a Service as an actual product surface instead of just a thesis.

## 29. Implementation docs created

On 2026-04-25 and 2026-04-26, this plan was expanded into eight implementation-facing companion docs:
- `CITY_AS_A_SERVICE_TEMPLATE_SPECS.md`
- `CITY_AS_A_SERVICE_EVIDENCE_SCHEMAS.md`
- `CITY_AS_A_SERVICE_JURISDICTION_MODEL.md`
- `CITY_AS_A_SERVICE_OPERATOR_PLAYBOOK.md`
- `CITY_AS_A_SERVICE_PILOT_BLUEPRINT.md`
- `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
- `CITY_AS_A_SERVICE_LOCAL_PROJECTOR_BOOTSTRAP.md`
- `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`

These docs convert the CaaS thesis into:
- concrete MVP templates
- normalized municipal evidence contracts
- a reusable office/jurisdiction memory layer
- an operator workflow for intake, dispatch, review, chaining, and memory updates
- a narrow first-pilot blueprint that can move from planning into live execution
- a memory/observability bridge for turning reviewed city episodes into future dispatch intelligence
- a local-first projector bootstrap that can test the memory loop before full Acontext infra wiring
- a first success-metrics layer for measuring whether reviewed city work improves future dispatch

This is the right level of specificity for the next product step: prototype city-ops surfaces without overcommitting to a giant platform build.

## 30. Recommended execution sequence

If daytime product work picks this up next, the highest-leverage build order is:

1. **Ship Packet Submission + Counter Question templates first**
   - they sit closest to obvious customer pain
   - they create the strongest rejection/redirect memory

2. **Require normalized municipal result fields**
   - `outcome_status`
   - `source_type`
   - `rejection_reasons[]`
   - `next_step_recommendation`

3. **Persist office-level episode memory**
   - `office + workflow_template + outcome_status + redirect_target`
   - enough to start building real municipal intelligence

4. **Pilot in one metro area first**
   - likely Miami-area permit/posting/compliance workflows
   - stay narrow before nationalizing the model

5. **Run with an explicit operator playbook from day one**
   - enforce fallback behavior
   - require closure artifacts (success proof, rejection diagnosis, or redirect target)
   - update office memory after every meaningful episode

6. **Constrain the first pilot brutally**
   - one metro area
   - three templates first: Counter Question, Packet Submission, Posting Proof
   - manual review on all rejected/redirected/blocked outcomes
   - treat repeat office learning as the primary success signal

7. **Project reviewed episodes into reusable dispatch memory**
   - keep EM as execution ledger
   - generate reviewed episode summaries, office playbooks, and jurisdiction briefs
   - use those artifacts to shape future dispatch instructions and routing

8. **Prove the loop locally before Acontext infra work**
   - emit reviewed result + reviewed episode artifacts from a local projector
   - merge office playbook deltas deterministically
   - compose a dispatch brief from local artifacts first

That sequence keeps CaaS grounded in product reality: real operator surfaces, real evidence structure, real memory accumulation, a pilot small enough to learn from quickly, and a clean bridge into Acontext-backed operational memory.

## 31. Pre-dawn synthesis and daytime handoff

Tonight's work clarified that the CaaS problem is no longer a thesis problem. The planning stack is now strong enough to support a very specific daytime move: define the first implementation contracts and treat the Miami pilot as an operator-learning system, not a generic marketplace launch.

### 31.1 What became clear tonight
- the strongest first wedge remains **Packet Submission + Counter Question**
- the core product breakthrough is **normalized municipal outcome capture**, not generic evidence upload
- the real moat is **reviewed office memory** that makes the second run better than the first
- Acontext should be treated as the **retrieval and observability layer**, while Execution Market remains the execution ledger

### 31.2 The missing bridge has narrowed
The remaining gap is no longer broad strategy. It is the build interface between:
- task templates
- normalized result JSON
- office-memory writes
- reviewed episode summaries
- dispatch-time retrieval briefs

That means daytime work should avoid more concept expansion and move directly into implementation-facing contracts.

### 31.3 Recommended daytime priorities

#### Priority A — lock the v1 product/result contract
Define the exact implementation shape for:
- `workflow_template`
- `outcome_status`
- `source_type`
- `rejection_reasons[]`
- `redirect_target`
- `next_step_recommendation`
- per-template `structured_result` payloads

This should produce one thin contract that both operator UI and API surfaces can share.

#### Priority B — build reviewed episode artifacts before full Acontext wiring
Before worrying about live infra, implement a local projector path that emits:
- `episode_summary`
- `office_playbook`
- `jurisdiction_brief`

That de-risks the memory loop and lets the team test retrieval quality before Docker/Acontext plumbing is finished.

#### Priority C — operationalize one brutally narrow Miami pilot
Constrain the first real rollout to:
- one metro area
- Counter Question, Packet Submission, Posting Proof only
- mandatory review on all non-clean outcomes
- office-memory write after every meaningful episode

The success target should be improved routing/rejection learning, not raw volume.

### 31.4 Practical recommendation for the next engineering slice
If only one code slice is started next, it should be:
1. a shared city-ops result schema
2. a reviewed episode-summary writer
3. a simple dispatch-brief retrieval helper
4. a local projector artifact layout that can later swap to Acontext sinks

That would connect the planning work to an actual product loop without requiring the entire CaaS platform to exist first.

### 31.5 Strategic handoff sentence
**Daytime should stop expanding the concept and start implementing the replay loop: template -> reviewed result -> office memory -> better next dispatch.**

## 32. Final 6am wrap-up

### 32.1 What was accomplished vs planned
The stale cron payload still pointed at AutoJob, Frontier Academy, and KK v2, but `DREAM-PRIORITIES.md` overrode that completely. The night therefore stayed correctly focused on Execution Market AAS work only.

Accomplished:
- expanded the core CaaS master plan into a full implementation-oriented planning stack
- produced concrete docs for templates, evidence schemas, jurisdiction memory, operator workflow, pilot design, and Acontext memory bridging
- tightened the recommended execution order around a narrow Miami-area pilot
- converted the night's work into a clearer daytime engineering handoff

Not done because it is explicitly stopped:
- no AutoJob work
- no Frontier Academy work
- no KK v2 work

### 32.2 Core insight from the night
The highest-value shift is that CaaS is no longer blocked on imagination. It is now blocked on implementation contracts.

The next leverage point is a thin shared loop:
1. template selected
2. reviewed structured result captured
3. office/jurisdiction memory updated
4. future dispatch improved by retrieval

### 32.3 Immediate daytime attention
If daytime touches only one thing next, it should be the shared result/memory seam:
- finalize the v1 city-ops result schema
- implement a reviewed episode projector that emits `episode_summary`, `office_playbook`, and `jurisdiction_brief`
- wire a lightweight dispatch briefing helper that consumes those artifacts
- keep the first loop local/file-based until the artifacts and retrieval shape feel obviously right

### 32.4 How tonight positions the ecosystem
Tonight moved Execution Market's AAS direction from concept exploration into product-shaping territory.

That matters because CaaS now has:
- a concrete customer wedge
- a minimal pilot shape
- a structured evidence contract
- an operator review discipline
- a memory architecture that can compound across runs

In other words: this is now close enough to build, not just discuss.

### 32.5 Repo hygiene / continuity note
All dream-session work stayed in `projects/execution-market` on `feat/operator-route-regret-panel`.
The repo is synced with origin, and the only intentionally untouched local item remains the unrelated untracked file `scripts/sign_req.mjs`.

The planning docs under `docs/planning/` are now the canonical handoff surface for daytime follow-through.

## 33. Local projector bootstrap added

The next practical gap after the result/memory contract was not more concept design. It was the pre-infra build path.

`CITY_AS_A_SERVICE_LOCAL_PROJECTOR_BOOTSTRAP.md` now defines that path:
- suggested local artifact directory layout
- minimal reviewed-result / reviewed-episode / office-playbook / jurisdiction-brief / dispatch-brief outputs
- write rules that only promote reviewed outcomes into memory
- a deterministic first dispatch-brief composer
- a fixture-driven way to test whether the second city task actually becomes better than the first

This matters because Acontext should remain a sink swap, not a product-thinking crutch.
The cleanest next daytime move is to prove the memory loop locally, then wire the same contracts into Acontext once the artifacts are obviously useful.

## 34. First implementation milestones and acceptance gates

The next move should not be "start building CaaS" in the abstract.
It should be two narrow milestones with visible acceptance criteria.

### 34.1 Milestone A — review-to-artifact loop

Goal:
Turn one reviewed city task into reusable local artifacts with zero Acontext dependency.

Scope:
- one Review Console flow for `counter_question` and `packet_submission`
- one reviewed result artifact emitted on closure
- one reviewed episode artifact emitted on closure
- office playbook merge logic for redirect/rejection/evidence-learning fields
- deterministic dispatch-brief composer

Minimum acceptance gate:
- given 5-10 fixture episodes, the projector writes stable JSON artifacts
- the same office/template produces a visibly richer dispatch brief after repeated reviewed runs
- operators can inspect the memory-write preview before closure
- no artifact is written directly from raw worker upload

### 34.2 Milestone B — dispatch quality loop

Goal:
Prove that prior reviewed city work improves the next dispatch.

Scope:
- Dispatch Brief Panel appears when creating or rerouting a city task
- panel shows top rejection reasons, redirect targets, evidence warnings, and fallback instructions
- follow-on task creation reuses prior task context instead of forcing re-entry
- Office Memory View exposes whether repeated runs are actually producing better routing knowledge

Minimum acceptance gate:
- operator can open a city task and see a compact office/template briefing before dispatch
- at least one reroute/resubmit flow can be created without manual restatement of the full office context
- reviewed episodes are inspectable from the briefing surface
- the pilot team can measure memory reuse rate and redirect/rejection concentration from the generated artifacts

### 34.3 Build-order recommendation

1. reviewed result contract
2. review console form/state
3. local projector writes
4. dispatch-brief composer
5. dispatch brief panel
6. office memory view
7. only then Acontext sink replacement

This order keeps the hardest product truth in the open: whether reviewed city work actually compounds into better future dispatch decisions.

## 35. Operator surfaces and state contracts for the first build

The remaining ambiguity is no longer strategic. It is interface-level.
Daytime should be able to point at three concrete surfaces and say exactly what state each one owns.

### 35.1 Review Console

Purpose:
Turn messy worker evidence into one reviewed city result that can close the task and feed memory.

The Review Console should own:
- reviewed `outcome_status`
- reviewed `source_type`
- template-specific `structured_result`
- `rejection_reasons[]`
- `redirect_target`
- `next_step_recommendation`
- `risk_flags[]`
- review artifact fields (`review_status`, `closure_type`, `result_trust_level`, `memory_write_recommended`)

The Review Console should show side-by-side:
- raw worker evidence
- normalized result draft
- memory-write preview
- follow-on recommendation preview

Hard rule:
no city task should write office memory from raw submission alone.
The review surface is the promotion gate.

### 35.2 Dispatch Brief Panel

Purpose:
Inject office/jurisdiction memory at the exact moment an operator is about to create, reroute, or resubmit a city task.

The Dispatch Brief Panel should show:
- office/jurisdiction summary
- top rejection reasons for the template
- top redirect targets
- evidence warnings
- fallback instruction recommendation
- last reviewed episode count / freshness

The Dispatch Brief Panel should influence:
- worker instructions
- whether the operator chooses Counter Question before Packet Submission
- whether a reroute target is already obvious
- whether extra evidence requirements should be added before dispatch

Hard rule:
retrieval should be compact and operational, not a long transcript dump.
If the operator cannot act on it in under a minute, the brief is too noisy.

### 35.3 Office Memory View

Purpose:
Make office learning inspectable so operators trust the loop and can correct bad inferences early.

The Office Memory View should show:
- current office playbook summary
- recent reviewed episodes for that office/template pair
- rejection/redirect concentration
- confidence/freshness markers
- changes introduced by the latest playbook delta

This is not a general knowledge browser.
It is a debugging and trust surface for the municipal memory loop.

### 35.4 Minimal shared state objects

If the first implementation wants the smallest stable seam, it should define and reuse exactly these objects:
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- `office_playbook_delta`
- `dispatch_brief`

If these five objects remain stable, UI surfaces and memory sinks can evolve independently without losing product coherence.

### 35.5 First UI acceptance gates

The first city-ops UI slice should not be called done until:
- an operator can review a worker submission into a valid `reviewed_result`
- that action emits a visible memory-write preview before confirmation
- a future task for the same office/template shows a compact `dispatch_brief`
- the operator can inspect why the brief says what it says via recent reviewed episodes
- reroute/resubmit creation can reuse prior office context instead of starting from blank fields

This is the narrowest real product loop: review -> memory -> next dispatch improvement.

## 36. Observability is now a first-class build seam

The planning stack now also includes `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`.
That matters because the next implementation risk is not only whether reviewed artifacts can be written, but whether they actually improve routing, rejection handling, and dispatch quality.

Daytime should therefore treat observability as part of the product loop, not an afterthought.
The first city-ops slice should emit stable events around:
- dispatch brief composition and use
- reviewed-result completion
- reviewed episode and playbook-delta writes
- redirect and rejection observations
- follow-on or resubmission creation

The right early success measures are not just volume or GMV.
They are:
- first-attempt routing accuracy
- redirect rate by office/template
- repeat rejection rate for already-known causes
- memory-backed dispatch rate
- resubmission success after learning

If those move in the right direction, CaaS is becoming real infrastructure instead of a one-off municipal errand layer.

## 37. First code-facing implementation package

The planning stack is now conceptually strong enough that the next missing piece is not more prose.
It is a compact package that daytime engineering can implement without reinterpreting the strategy docs.

### 37.1 Ship one narrow `city_ops_review` package first

The first code-facing slice should be treated as a package, even if it initially lives inside the existing EM codebase.
Its job is to own the full reviewed-result -> projector -> dispatch-brief seam for city work.

Minimum package responsibilities:
- validate the shared `reviewed_result` contract
- validate the `review_artifact` contract
- emit a `reviewed_episode`
- emit zero or one `office_playbook_delta`
- compose a deterministic `dispatch_brief`
- emit stable observability events for each transition

This package boundary matters because it prevents CaaS logic from being scattered across UI forms, ad hoc review code, and later memory sinks.

### 37.2 Minimal modules inside that package

If daytime wants the smallest coherent implementation unit, it should start with these modules:

1. `city_ops/contracts.py` or equivalent
   - shared schemas / validators for `reviewed_result`, `review_artifact`, `reviewed_episode`, `office_playbook_delta`, `dispatch_brief`

2. `city_ops/projector.py`
   - pure function path from reviewed inputs to reviewed episode + playbook delta + dispatch brief

3. `city_ops/playbook_merge.py`
   - deterministic merge rules for redirect patterns, rejection patterns, evidence restrictions, and confidence/freshness updates

4. `city_ops/events.py`
   - stable event-name wrappers for `city_review_completed`, `city_reviewed_episode_written`, `city_office_playbook_delta_written`, `city_dispatch_brief_composed`

5. `city_ops/fixtures/`
   - small reviewed city episodes covering acceptance, rejection, redirect, blocked visit, and evidence restriction

The goal is to make the first engineering slice testable and replayable before any larger city-specific UI build.

### 37.3 First acceptance test bundle

The first code slice should not be called done until a fixture bundle proves all of this end to end:
- a reviewed packet submission with rejection emits a valid `reviewed_episode`
- repeated reviewed rejections strengthen the office playbook rather than duplicating noise
- a redirect episode updates the top redirect targets deterministically
- a later dispatch brief includes the learned rejection and redirect guidance
- each reviewed closure emits the expected observability events in stable order

This is the smallest proof that the system can learn from reviewed municipal work instead of merely storing it.

### 37.4 Why this package should come before bigger UI work

Without a code-facing package boundary, daytime risks building:
- review UI state that does not map cleanly to durable contracts
- office-memory writes that are impossible to reason about
- dispatch retrieval that depends on transcript scraping instead of stable artifacts

By contrast, if the package exists first, UI and infra become clients of a known city-ops learning seam.

### 37.5 Strong recommendation

The next engineering move should be:
1. implement the shared contract validators
2. implement the local projector package
3. prove it with fixture replays
4. only then wire Review Console and Dispatch Brief Panel onto those contracts

That is the cleanest route from planning to a buildable product loop.

## 38. Pre-dawn synthesis: what daytime should do next

The night's planning work now has enough depth.
What matters next is reducing daytime ambiguity to almost zero.

### 38.1 The real bottleneck

CaaS is no longer blocked on strategy, TAM, or template ideation.
It is blocked on whether Execution Market can turn reviewed municipal interactions into reusable operational memory without creating a noisy knowledge swamp.

That means the first real product test is not:
- how many city templates exist
- how polished the UI looks
- how quickly Acontext is wired

It is this:

> after one reviewed city task, is the next city task dispatched more intelligently?

If daytime protects that question, the vertical will compound.
If daytime loses that question, the product will drift into decorative docs and labor routing.

### 38.2 Daytime implementation order

If there is only one clean daytime sequence, it should be:

1. finalize typed validators for `reviewed_result`, `review_artifact`, `reviewed_episode`, `office_playbook_delta`, and `dispatch_brief`
2. create a tiny fixture set for `counter_question` and `packet_submission`
3. implement the deterministic local projector and playbook merge rules
4. verify that repeat rejections and redirects visibly change the dispatch brief
5. only then attach Review Console state and Dispatch Brief UI to those artifacts

This keeps product truth ahead of interface work.

### 38.3 What should count as a meaningful daytime win

A strong next daytime session does not need to ship the full city vertical.
It only needs to prove one repeatable learning loop.

A meaningful win would be:
- one reviewed rejection fixture
- one reviewed redirect fixture
- one resulting office playbook artifact
- one resulting dispatch brief that is clearly better than the empty-state brief
- one rerun showing that the learned guidance appears before the next dispatch

If that works, the system has crossed from theory into compounding behavior.

### 38.4 What to postpone on purpose

Daytime should resist a few tempting distractions until the loop above is proven:
- broad template expansion
- heavy Acontext or Docker dependency
- generalized workflow automation
- multi-city rollout logic
- long-form office memory authoring surfaces

Those can all come later.
The scarce question right now is whether reviewed city work improves future city work.

### 38.5 Recommended handoff framing

If this gets picked up in daylight, the shortest correct framing is:

**Build the city-ops learning seam, not the whole city product.**

Concretely, that means:
- contracts first
- projector second
- fixture replays third
- operator surfaces last

That ordering should save a lot of churn.

