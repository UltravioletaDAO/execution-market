# City-as-a-Service — Pre-Dawn Synthesis (2026-06-03)

> Scope: Execution Market AAS / City-as-a-Service only.
> Status: 5 AM synthesis and daytime handoff; no operator answer, no approval, no runtime mutation, no customer/public exposure.
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`.

## 1. Priority firewall

`~/clawd/DREAM-PRIORITIES.md` was read first. It explicitly allows Execution Market AAS / City-as-a-Service work and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2.

The cron payload still carried stale instructions to pull/analyze AutoJob, expand Frontier Academy, and continue KK v2. Those instructions were intentionally skipped. No stopped-project files were pulled, analyzed, edited, expanded, tested, or committed.

## 2. Tonight's connected stack

The June 3 night moved the AAS no-answer posture from "many useful handoff docs" into a clearer source-of-truth and decision-support shape:

```text
product-exposure candidate review gate
-> product-exposure no-answer hold packet
-> two-lane no-cross-promotion guard
-> two-lane operator answer schema
-> source-of-truth index
-> system-integration decision-support map
-> 4 AM pattern-synthesis handoff
-> 5 AM pre-dawn synthesis
```

The key synthesis: the system is no longer blocked by missing planning structure. It is blocked, correctly, by the absence of a real human/operator answer. The best next daytime action is not another read-only wrapper; it is either a real answer record for one lane or an explicit pause.

## 3. What changed tonight

### 00:00 — two-lane operator answer schema

Turned the previous no-cross-promotion guard into a deterministic internal/admin schema for exactly one future decision.

Allowed future values:

- `keep_both_lanes_held`
- `create_retail_reality_answer_or_hold_record`
- `create_runtime_memory_operator_answer_record`
- `pause_aas_proof_layering`

Safe claim: `internal_admin_aas_two_lane_operator_answer_schema_landed`.

### 02:00 — source-of-truth index

Created a deterministic source-of-truth index over the two-lane schema. It marks current entrypoints, demotes older master/catalog/May synthesis docs to historical context only, and carries a stale-pattern extension ban list.

Safe claim: `internal_admin_aas_source_of_truth_index_landed`.

### 03:00 — system-integration decision-support map

Connected five current strengths as support-only lanes: memory/Acontext readiness, IRC session-management discipline, cross-project source filtering, agent observability boundary metrics, and payment/production context.

Safe claim: `internal_admin_aas_system_integration_decision_support_map_landed`.

### 04:00 — pattern-synthesis handoff

Captured four reusable internal/admin patterns without selecting or approving any future path:

1. memory data compounds only after boundary distillation;
2. IRC coordination scales through sanitized handoff invariants;
3. cross-project intelligence is a filter, not autopilot;
4. agent coordination quality is claim-boundary survival.

Safe claim: `internal_admin_aas_four_am_pattern_synthesis_handoff_landed`.

### 05:00 — synthesis and daytime handoff

This document consolidates the night's proof path and makes the daytime choice explicit: stop/pause, or create one separate answer record. It does not add new product authority.

Safe claim: `internal_admin_aas_pre_dawn_synthesis_2026_06_03_landed`.

## 4. Strategic connections

### AAS source-of-truth is now an anti-drift control

The source index matters because City-as-a-Service has many strong older docs. Without an index, future sessions can accidentally treat historical taxonomy as launch authority. The new posture is stricter:

```text
current entrypoint != launch authority
historical context != approval
source digest != runtime truth
planning strength != customer/public readiness
```

### Memory/Acontext and product exposure are separate lanes

The two-lane schema prevents a common failure mode: using product-review progress to justify runtime-memory wiring, or using runtime-memory progress to justify product/customer exposure. Both lanes are useful; neither can cross-promote.

### Coordination quality has a concrete metric

The night distilled a useful operator-quality heuristic:

```text
A handoff is good when safe claims, blocked claims, source refs, and next gate survive together.
```

That metric can improve agent coordination immediately without becoming a public dashboard, worker credential, reputation score, or dispatch trigger.

### Cross-project intelligence should filter, not route

The stopped-project firewall is not just compliance with `DREAM-PRIORITIES.md`; it is a product design principle. Cross-project context can help filter stale authority and preserve lessons, but it must not autoroute AAS decisions into AutoJob, Frontier Academy, KK v2, KarmaCadabra v2, or any customer/worker flow.

## 5. Daytime recommendations

### Recommended default

Keep both lanes held and pause proof layering unless Saúl explicitly gives a real answer. The current structure is enough to preserve state; more no-answer ceremony now has diminishing returns.

### If Saúl wants product exposure next

Create exactly one separate Retail Reality answer/hold record against the two-lane schema. The record should name:

- exact selected value;
- non-secret human/operator reference;
- source artifact digest;
- precise approved or held boundary;
- authorized review path, if any;
- still-blocked claims.

Do not treat the existing Retail Reality candidate/review/hold artifacts as approval.

### If Saúl wants runtime memory next

Create exactly one separate runtime-memory operator answer record first. Only after that, and only if the answer selects a runtime-memory lane, use the prior carry-forward card and session-manager no-mutation field map as design-only/default-off inputs.

Do not register or enable an adapter, mutate IRC/session-manager state, write to Acontext, or claim parity from the answer schema alone.

### If Saúl wants to stop the loop

Use `pause_aas_proof_layering` as the next answer value. This is a clean state: the system has enough internal/admin structure and should wait for a product/runtime decision rather than adding another wrapper.

## 6. Still blocked

The June 3 stack does **not** approve:

```text
operator answer recording
operator approval recording
selected future answer
Retail Reality answer/hold record creation
Retail Reality product exposure
runtime-memory operator answer record creation
runtime-memory wiring
runtime adapter registration or enablement
IRC/session-manager mutation
live Acontext write or retrieval
runtime parity
cross-project autorouting
customer/public/worker surface
dashboard/public metric
public catalog routes
public pricing or customer quotes
operator queue launch
worker dispatch/autonomous dispatch
ERC-8004 reputation
Worker Skill DNA
payment or production readiness claims from this slice
exact GPS/raw metadata release
private operator context release
raw transcript authority
domain/legal/emergency/safety/repair/insurance/SLA authority claims
worker-copyable doctrine
stopped-project integration
```

## 7. Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1884 passed
```

## 8. Daytime entrypoints

- Current synthesis: `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_06_03.md`
- Current source index implementation: `CITY_AS_A_SERVICE_AAS_SOURCE_OF_TRUTH_INDEX_IMPLEMENTATION.md`
- Current decision map implementation: `CITY_AS_A_SERVICE_AAS_SYSTEM_INTEGRATION_DECISION_SUPPORT_MAP_IMPLEMENTATION.md`
- Current 4 AM handoff implementation: `CITY_AS_A_SERVICE_AAS_FOUR_AM_PATTERN_SYNTHESIS_HANDOFF_IMPLEMENTATION.md`
- Current operator board: `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`

## 9. One-line handoff

Execution Market AAS now has a source-indexed, two-lane, no-cross-promotion decision path; the next real progress requires exactly one human/operator answer, otherwise pause proof layering and preserve the hold.
