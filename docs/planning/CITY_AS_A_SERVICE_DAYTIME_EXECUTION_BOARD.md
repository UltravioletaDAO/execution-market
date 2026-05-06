# City as a Service — Daytime Execution Board

> Last updated: 2026-05-05 23:45 America/New_York
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_DAYTIME_BUILD_SPEC.md`
> - `CITY_AS_A_SERVICE_IMPLEMENTATION_BACKLOG_AND_DECISIONS.md`
> - `CITY_AS_A_SERVICE_TYPED_VALIDATORS_AND_FIXTURE_SCHEMA.md`
> - `CITY_AS_A_SERVICE_FIXTURE_REPLAY_AND_ACCEPTANCE_TEST_PLAN.md`
> Status: execution handoff board

## 1. Why this doc exists

The planning stack is now broad enough that the main daytime risk is not missing ideas.
The risk is fragmented execution:
- building the right seams in the wrong order
- starting UI before proof artifacts are stable
- treating every planning doc as equally urgent
- losing track of what is already decided versus what still needs a real build choice

This document compresses the current City-as-a-Service work into one execution board.
Its goal is simple:

> make the next 1-2 engineering windows obvious, file-by-file, with acceptance gates and a strict "not yet" list.

## 2. Build thesis

The first live CaaS slice is only successful if it proves:

> one reviewed municipal task can make the next dispatch materially smarter in a traceable way.

That means daytime should optimize for this chain, in this order:
1. validated reviewed closure
2. deterministic replay artifacts
3. compact memory delta
4. improved dispatch brief
5. explicit proof that the brief improved for an operational reason

If a task does not strengthen that chain, it is probably not first-window work.

## 3. What is already decided

These are not active debates anymore.

### 3.1 Scope
- Vertical: **Execution Market CaaS / AAS only**
- First templates: `counter_question`, `packet_submission`
- First proof style: deterministic local replay, not live infra-first
- First memory policy: no durable writes from raw worker uploads

### 3.2 Core objects
The stable first-pass artifacts are:
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- `office_playbook_delta`
- `office_playbook_after`
- `dispatch_brief`
- `brief_improvement_scorecard`
- `event_summary`
- `bundle_manifest`
- `review_packet`

Missing implementation seam now identified:
- operator guidance tone and placement policy derived from `memory_promotion_decision`

### 3.3 Surface priority
Build order remains:
1. contracts + fixtures
2. review normalizer
3. local projector
4. brief composer + replay proof bundle
5. thin operator/admin surfaces
6. observability hardening
7. transport swap later

## 3.1 New review-discipline seam locked

The planning stack now also includes:
- `CITY_AS_A_SERVICE_REPLAY_PROOF_REVIEW_PROTOCOL.md`
- `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_SCOREBOARD_PROTOCOL.md`
- `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_TELEMETRY_GATE.md`
- `CITY_AS_A_SERVICE_DAYTIME_TELEMETRY_GATE_REVIEW_PROTOCOL.md`
- `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_EXECUTION_LADDER.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PROOF_CASE_SELECTION_CARD.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PROOF_ANCHOR_FREEZE_CONTRACT.md`
- `CITY_AS_A_SERVICE_DAYTIME_PR_A_PROJECTION_TRUTH_HANDOFF.md`
- `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_05.md`
- `mcp_server/city_ops/decision_projection.py`
- `mcp_server/tests/city_ops/test_decision_projection.py`

This doc closes one daylight ambiguity that the earlier planning set still left too loose:
- the exact artifact reading order for replay-proof PRs
- the difference between proof, progress, and overclaim
- the bar for when replay is strong enough to justify broader UI wiring
- the minimum telemetry row that must exist before a proof block counts as operationally packaged

Daytime should treat that review protocol as the default tie-breaker whenever a replay bundle exists but implementation readiness still feels debatable.

## 4. The next engineering window

### 4.1 Track A — contracts and validators
Target files/seams:
- `mcp_server/city_ops/contracts.py` or equivalent typed schema home
- fixture validator helpers
- minimal artifact validators for replay outputs

Must lock first:
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- `office_playbook_delta`
- `dispatch_brief`
- `review_packet`
- `bundle_manifest`
- `event_summary`

Acceptance gate:
- rejection fixture, redirect fixture, and evidence-restriction fixture all fail loudly on malformed objects with explainable errors

### 4.2 Track B — replay fixture pack
Target seam:
- `fixtures/city_ops_review_cases/` or equivalent

Minimum fixture families:
- clean acceptance
- packet rejection due to outdated form
- redirect to different office/window
- no-photo/evidence restriction
- blocked visit / appointment required
- repeated rejection reinforcement

Acceptance gate:
- each fixture can be inspected by eye and contains enough structured input to justify reviewed truth without transcript dumps

### 4.3 Track C — deterministic projector
Target files/seams:
- `review_normalizer.py`
- `projector.py`
- `brief_composer.py`

Must produce:
- `reviewed_episode`
- `office_playbook_delta` when justified
- `office_playbook_after`
- `improved_dispatch_brief`
- deterministic output paths for replay bundles

Acceptance gate:
- rerunning the same fixture yields the same operational outputs and the same event ordering

### 4.4 Track D — proof bundle judgment
Target artifacts:
- `brief_improvement_scorecard.json`
- `bundle_manifest.json`
- `review_packet.json`
- `event_summary.json`

Acceptance gate:
- a reviewer can open `bundle_manifest.json` first and understand whether learning passed, was partial, or failed without reading code

### 4.6 Track F — local Acontext server and session discipline seam
Target files/seams:
- local control-plane ledger rows keyed by `coordination_session_id`
- continuity summary artifact / morning pickup artifact
- Acontext sink adapter for `review_packet`, `reviewed_episode`, `office_playbook_after`, and `dispatch_brief`
- retrieval path that preserves promotion class, guidance tone, and placement

Reference docs:
- `CITY_AS_A_SERVICE_ACONTEXT_LOCAL_SERVER_AND_SESSION_DISCIPLINE.md`
- `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
- `CITY_AS_A_SERVICE_DECISION_SUPPORT_CONTROL_PLANE.md`

Acceptance gate:
- one replay-backed reviewed case can be ingested into local Acontext after local artifact generation
- session rebuild works from compact artifacts without transcript dependence
- Acontext-assisted retrieval preserves the same next-dispatch guidance class as the local-only path

### 4.5 Track E — operator guidance expression seam
Target files/seams:
- dispatch brief composer tone/placement mapping
- Review Console memory-write preview
- Office Memory View guidance grouping
- replay-bundle-to-pickup-brief continuity writer

Reference docs:
- `CITY_AS_A_SERVICE_OPERATOR_GUIDANCE_TONE_AND_PLACEMENT_POLICY.md`
- `CITY_AS_A_SERVICE_MORNING_PICKUP_BRIEF_CONTRACT.md`

Acceptance gate:
- confident, cautious, held, and blocked learning render with distinct operator-facing tone and placement instead of collapsing into one warning style
- each replay-proof block can emit one compact morning pickup brief that preserves the promotion/tone/placement verdict without forcing the next builder to reopen the whole bundle

## 5. File-by-file done criteria

### 5.1 Contracts layer is done when
- shared enums are stable
- template-specific required fields are enforced
- unknown values fail parse-time validation
- provenance references can be validated

### 5.2 Fixture pack is done when
- at least one rejection case and one redirect case prove before/after brief differences
- one low-learning case stays valid without overclaiming improvement
- one ambiguous case proves conservative promotion behavior

### 5.3 Projector is done when
- raw upload cannot bypass review
- one reviewed task always emits `reviewed_result`, `review_artifact`, and `reviewed_episode`
- office memory changes only when learning is meaningful
- the next dispatch brief becomes reproducibly richer where justified

### 5.4 Scorecard seam is done when
- it can distinguish "changed" from "improved"
- it punishes unsupported certainty
- it makes routing clarity or rejection avoidance improvement explicit

### 5.5 Manifest seam is done when
- missing artifacts are never ambiguous
- acceptance checks are inspectable
- summary judgment is conservative and reproducible

### 5.6 Review packet seam is done when
- it mirrors manifest judgment
- it carries explicit learning strength
- it states memory promotion stance clearly enough for downstream retrieval or UI to respect

## 6. What daytime should NOT build yet

Do not spend the next window on:
- broad multi-city rollout logic
- embeddings or semantic retrieval
- heavy Acontext plumbing before local proof is solid
- polished executive dashboards
- generalized workflow engines
- more template expansion beyond what strengthens the first proof seam
- marketplace redesign work unrelated to reviewed-result compounding

If the team is tempted to build one of these first, it likely means the proof seam still feels too vague.

## 7. Recommended PR sequence

### PR 1
Contracts + validators + fixture schema skeleton

### PR 2
Initial fixture pack with expected outputs and deterministic failing tests

### PR 3
Review normalizer + projector + office playbook merge logic

### PR 4
Dispatch brief composer + scorecard + manifest + event summary + review packet bundle writer

### PR 5
Thin Review Console / Dispatch Brief Panel / Office Memory Debug surface consuming the same artifacts

### PR 6
Morning pickup brief writer + debug surfacing so each replay-proof block hands off exact gate status, behavior-change assessment, and anti-overclaim warnings

### PR 7
Compact decision object + coordination ledger slice so one replay-backed case emits:
1. `city_compact_decision_object.json`
2. `city_coordination_ledger.jsonl`
3. pickup brief / export / observability rows derived from the same decision object
4. one restart-safe session rebuild preview

### PR 8
Replay-proof review protocol adoption in PR/review discipline so reviewers read:
1. manifest
2. event summary
3. review packet
4. compact decision object
5. pickup brief
6. scorecard
7. improved brief
before deeper artifacts or broader UI claims

### PR 9
Reuse and redispatch alignment slice so one replay-backed case also proves:
1. dispatch-context reuse from the compact decision object
2. redispatch fallback reuse without trust-class drift
3. worker-instruction copyability filtering from the same decision seam
4. reuse observability rows and ledger events with behavior-change classes

### PR 10
Decision flywheel proof target so daytime treats replay, runtime continuity, and reuse as one acceptance harness rather than separate feature wins:
1. one normalized decision projection helper powers all consumers
2. one replay-backed case emits replay, pickup, export, rebuild, observability, and reuse outputs from the same shared fields
3. one behavior-change proof shows the next dispatch got smarter for the right reason
4. deliberate drift fixtures fail loudly on trust-class, tone, placement, copyability, readiness, and anti-overclaim drift
5. one shared decision parity scoreboard grades whether all downstream consumers preserved the same judged truth
6. one decision-projection implementation slice wires the normalized helper into core runtime consumers, reuse consumers, and both scoreboards before wider surface growth
7. one drift-triage playbook tells daytime exactly how to classify, localize, and fix the first parity/reuse failures instead of debating whether they are "just rendering"
8. one strict daytime proof-block runbook governs the execution order: choose case -> emit archive -> emit shared decision seam -> emit proof receipts -> classify pass/partial/fail -> choose the next smallest honest move
9. one combined scoreboard protocol converts parity + reuse scoreboards into a single honest expand / tighten / fix-drift verdict so daylight cannot hand-wave mixed proof states
10. one proof-block telemetry gate emits the compact join fields, portability judgments, and anti-overclaim carry-forward needed for pickup, observability, rebuild, and later Acontext export review
11. one telemetry-gate review protocol verifies that the compact closure row preserves the exact scoreboard verdict and claim limits before daytime treats the block as handoff-ready
12. one closure-proof pickup brief contract forces the next-session brief to mirror the exact verdict, behavior class, dangerous axes, anti-overclaim limits, and next smallest proof instead of becoming a softened summary
13. one closure-proof checklist gives daytime a final pass/partial/fail gate over manifest, telemetry, and pickup fidelity before claiming handoff-safe proof
14. one first-PR split strategy keeps the shared-decision seam reviewable in the right order: projection truth -> runtime convergence -> reuse convergence -> closure-proof packaging
15. one first-PR execution ladder defines the exact rung-by-rung advancement rule: allowed claim -> forbidden claim -> required checkpoint -> authoritative artifact -> honest stop condition

This sequence keeps UI downstream of proof instead of masking uncertainty.

## 8. The sharpest acceptance test

The first convincing CaaS product proof is not "artifacts were emitted."
It is this:

1. run a baseline fixture
2. review one rejection or redirect case
3. replay the projector
4. inspect the improved brief
5. confirm the scorecard marks a meaningful operational improvement
6. confirm the manifest and review packet stay conservative about learning strength

If that proof is not obvious by inspection, the build should not claim the learning loop is real yet.

Review discipline for that proof should now be standardized:
1. `bundle_manifest.json`
2. `event_summary.json`
3. `review_packet.json`
4. `city_compact_decision_object.json`
5. `morning_pickup_brief.json`
6. `brief_improvement_scorecard.json`
7. `improved_dispatch_brief.json`

If reviewers need to jump into code or raw supporting artifacts before those seven objects tell a coherent story, the seam is still too loose for broader surface expansion.

## 9. Strong recommendation

Treat this execution board as the daytime tie-breaker.
When two tasks look useful, choose the one that most directly strengthens:

`reviewed truth -> replay artifact -> memory delta -> better next dispatch -> inspectable proof`

That is the narrow seam that turns City as a Service from a strong concept into a shippable product loop.

A stronger tie-breaker now exists for the next coding window too:
- implement the shared decision projection seam first
- wire every required consumer through it
- force proof to end in parity + reuse-behavior scoreboards
- run the whole first push as one four-rung daytime program anchored to one active replay-backed case
- split the first implementation by verification boundary rather than by directory or artifact family
- choose one replay-backed redirect/rejection proof anchor before PR A and keep it stable across the ladder
- freeze that anchor in a durable proof-anchor note before coding starts
- start PR A from the projection-truth handoff so it lands only the shared owner + compact decision object claim
- advance only when each rung has earned its allowed claim and checkpoint

Implementation seed now exists for the first PR A rung:
- `mcp_server/city_ops/contracts.py` defines projection-owned enums and compact decision object shape
- `mcp_server/city_ops/decision_projection.py` projects one reviewed packet + one freeze note into the compact object
- `mcp_server/city_ops/fixtures/city_ops_review_cases/redirect_outdated_packet_001.json` is the first replay-backed redirect/rejection anchor packet
- `mcp_server/city_ops/fixtures/proof_anchors/redirect_outdated_packet_001/proof_anchor_freeze_note.json` freezes the drift axes and conservative expectations
- `mcp_server/tests/city_ops/test_decision_projection.py` proves deterministic output, loud enum/field failures, freeze expectation drift detection, and carried drift axes

Do not let daytime treat this as runtime parity. It earns only `projection_truth_landed`; PR B still has to wire runtime consumers through the same compact object without strengthening trust semantics.

See also:
- `CITY_AS_A_SERVICE_DECISION_PROJECTION_IMPLEMENTATION_SLICE.md`
- `CITY_AS_A_SERVICE_DECISION_DRIFT_TRIAGE_PLAYBOOK.md`
- `CITY_AS_A_SERVICE_DAYTIME_REPLAY_PROOF_RUNBOOK.md`
- `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_SCOREBOARD_PROTOCOL.md`
- `CITY_AS_A_SERVICE_DAYTIME_PROOF_BLOCK_TELEMETRY_GATE.md`
- `CITY_AS_A_SERVICE_DAYTIME_TELEMETRY_GATE_REVIEW_PROTOCOL.md`
- `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_PICKUP_BRIEF_CONTRACT.md`
- `CITY_AS_A_SERVICE_DAYTIME_CLOSURE_PROOF_CHECKLIST.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_SPLIT_STRATEGY.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_EXECUTION_LADDER.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PR_PROGRAM_CARD.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PROOF_CASE_SELECTION_CARD.md`
- `CITY_AS_A_SERVICE_DAYTIME_FIRST_PROOF_ANCHOR_FREEZE_CONTRACT.md`
- `CITY_AS_A_SERVICE_DAYTIME_PR_A_PROJECTION_TRUTH_HANDOFF.md`
- `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_05.md`
- `CITY_AS_A_SERVICE_COORDINATION_CARRY_FORWARD_MATRIX.md`
- `CITY_AS_A_SERVICE_REPLAY_PROOF_REVIEW_PROTOCOL.md`

## 10. Recommended next daytime slice: coordination-aware replay proof

If daytime has one extra engineering window after the current contract/projector path, the highest-leverage next slice is not more templates.
It is a coordination-aware replay proof, paired with a compact pickup-brief continuity object and one reuse-alignment pass that proves the next dispatch consumes the same judged truth.

### 10.1 What to add
Extend the existing proof seam so each replay bundle can include:
- `coordination_session_id`
- compact `event_summary.json`
- explicit intervention markers
- a scorecard axis for `coordination_trace_complete`

### 10.2 Why this is the right next move
This ties together tonight's strongest system themes:
- memory ↔ Acontext integration planning
- IRC session management enhancement
- cross-project decision support systems
- agent observability and success metrics

It also prevents a common failure mode: building strong reviewed-result artifacts that still depend on fragile chat transcripts or operator memory to explain why a reroute or redispatch happened.

### 10.3 File-first recommendation
The next implementation window should likely touch only a small set of seams:
- typed event envelope contract
- compact decision object writer
- append-only coordination ledger writer
- replay bundle writer
- morning pickup brief writer
- brief composer provenance references
- thin debug surface for event-chain inspection and rebuild preview

That is narrow enough to ship, but strong enough to prove that CaaS learning can plug into the broader EM coordination stack instead of becoming another isolated planning branch.

### 10.4 Why the pickup brief belongs in the same slice
The coordination-aware replay proof already creates the exact ingredients the next engineering block needs:
- deterministic event order
- manifest judgment
- packet-level promotion stance
- behavior-change evidence from the scorecard and improved brief

Adding `morning_pickup_brief.json` in the same slice prevents that proof from becoming another archive that daytime must mentally recompute.
The same slice should also emit one compact decision object plus one append-only coordination ledger so continuity, export, rebuild, and observability all inherit the same judged truth.
It gives the next builder one compact continuity seam with:
- acceptance gates passed/failed/partial
- promotion-policy observations
- guidance tone and placement observations
- next smallest proof
- explicit anti-overclaim warnings
- restart-safe decision state and mirrored runtime events

That handoff seam now also needs one explicit carry-forward join check across pickup, ledger, telemetry, export, rebuild, and later retrieval surfaces so daytime can detect quiet field-drop drift before calling the block handoff-safe.
See `CITY_AS_A_SERVICE_COORDINATION_CARRY_FORWARD_MATRIX.md`.

That keeps the handoff seam as disciplined as the replay seam itself.
