# City as a Service — First Implementation Slice

> Last updated: 2026-04-26
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_RESULT_AND_MEMORY_CONTRACT.md`
> - `CITY_AS_A_SERVICE_FIXTURE_REPLAY_AND_ACCEPTANCE_TEST_PLAN.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> Status: implementation-oriented planning draft

## 1. Why this doc exists

The planning stack already says what to build next in pieces:
- shared reviewed-result contracts
- deterministic projector logic
- fixture replay
- observability events
- operator surfaces that come later

What is still missing is **one thin, code-facing build brief** that daytime engineering can pick up without stitching four docs together.

This doc defines that first implementation slice.

## 2. Scope of the first slice

The first slice should prove the narrowest real CaaS learning loop:

1. ingest one reviewed city task
2. validate normalized contracts
3. emit a reviewed episode
4. merge a small office playbook delta
5. compose the next dispatch brief
6. emit stable events explaining what changed

If that loop works, CaaS has crossed from planning into compounding product behavior.

## 3. In scope

### 3.1 Workflow templates
Only support these templates first:
- `counter_question`
- `packet_submission`

### 3.2 Durable objects
The slice should define and validate exactly these objects:
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- `office_playbook_delta`
- `dispatch_brief`

### 3.3 Core package responsibilities
The slice should include:
- contract validators
- projector logic from reviewed inputs to outputs
- deterministic playbook merge rules
- stable observability event emitters
- a tiny replay fixture harness

## 4. Explicitly out of scope

Do not expand scope into:
- broad city template coverage
- polished Review Console UX
- broad Dispatch Brief UI work
- Acontext sink wiring
- multi-city rollout logic
- worker matching optimization
- general workflow automation

Those should wait until the replay loop is proven.

## 5. Proposed package shape

```text
city_ops_review/
  contracts.py
  projector.py
  playbook_merge.py
  events.py
  fixtures/
  tests/
```

Equivalent naming is fine, but the boundary should stay this small and this explicit.

## 6. Module responsibilities

### 6.1 `contracts.py`
Owns schema validation for:
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- `office_playbook_delta`
- `dispatch_brief`

Hard rule:
- no projector or UI path should invent fields outside these contracts silently

### 6.2 `projector.py`
Owns pure transformation from:
- prior office memory
- reviewed result
- review artifact

to:
- reviewed episode
- optional office playbook delta
- next dispatch brief
- event payload inputs

Hard rule:
- same inputs should produce the same outputs

### 6.3 `playbook_merge.py`
Owns deterministic merge rules for:
- repeated rejection reasons
- redirect targets
- evidence restrictions
- access friction notes
- freshness/confidence updates

Hard rule:
- repeated learning should strengthen known guidance, not duplicate noisy strings

### 6.4 `events.py`
Owns stable wrappers for:
- `city_review_completed`
- `city_reviewed_episode_written`
- `city_office_playbook_delta_written`
- `city_dispatch_brief_composed`

Hard rule:
- event naming and ordering should stay stable across replay runs

### 6.5 `fixtures/` and `tests/`
Own:
- tiny reviewed city episodes
- expected projector outputs
- expected event sequences

Hard rule:
- fixtures must stay small enough for direct human inspection

## 7. Required fixture set

The first slice should ship with at least these fixtures:

1. clean counter answer
2. packet rejection
3. repeated packet rejection for same reason
4. redirect to another desk/window
5. evidence restriction at counter
6. blocked office visit

These should map directly to the replay plan already defined elsewhere.

## 8. Acceptance gates

The first slice is only done if it can prove all of the following:

### 8.1 Contract gate
Every fixture produces valid:
- `reviewed_result`
- `review_artifact`
- `reviewed_episode`
- `dispatch_brief` when applicable

### 8.2 Learning gate
Repeated reviewed rejections and redirects:
- change the office memory deterministically
- make the next dispatch brief more specific
- avoid duplicate clutter

### 8.3 Event gate
Each reviewed closure emits stable events in the expected order.

### 8.4 Product gate
A later dispatch for the same office/template is visibly better than the empty-state brief.

If these gates are not passing, UI expansion should wait.

## 9. Recommended build order

1. implement contract validators
2. implement projector output shape
3. implement playbook merge rules
4. add replay fixtures and expected outputs
5. add event assertions
6. only then wire operator-facing surfaces

## 10. Handoff sentence for daytime

**Build the smallest city-ops review package that can prove: reviewed municipal work makes the next dispatch better.**

That is the best next seam because it connects every existing planning doc to one testable implementation unit without reopening strategy debates.
