# City-as-a-Service — Pre-Dawn Synthesis (2026-06-04)

> Scope: Execution Market AAS / City-as-a-Service internal/admin synthesis only.
> Governing priority: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`.
> Status: 5 AM daytime handoff; no operator answer, no approval, no runtime mutation, no customer/public/worker surface.

## 1. Priority firewall

`/Users/clawdbot/clawd/DREAM-PRIORITIES.md` was read first and treated as authoritative over the stale cron payload.

Allowed work:

- Execution Market AAS / City-as-a-Service plans and AAS concepts.

Explicitly not worked on:

- AutoJob;
- Frontier Academy;
- KK v2;
- KarmaCadabra v2;
- stopped-project integrations.

The stale 5 AM payload asked for AutoJob pull/analysis, Frontier Academy expansion, and KK v2 continuation. Those requests conflict with the current dream priority file, so they were intentionally skipped. No stopped-project repository was pulled, analyzed, edited, expanded, tested, committed, or used as a source.

## 2. Repository sync and current-runtime truth

Execution Market was synced only on the active AAS branch:

```bash
git -C /Users/clawdbot/clawd/projects/execution-market pull --ff-only
# Already up to date.
```

Observed state for this synthesis:

```text
branch: feat/operator-route-regret-panel
HEAD before 5 AM work: 285941db docs: add AAS 4am value connections
pre-existing untracked file preserved: scripts/sign_req.mjs
```

A bounded read-only runtime check still shows the same current blocker:

```text
docker context: desktop-linux
docker info: cannot connect to unix:///Users/clawdbot/.docker/run/docker.sock
http://localhost:3000: connection refused
http://localhost:8080: connection refused
http://localhost:5173: connection refused
```

No Docker repair, Docker pull, ORAS copy, Compose startup, container mutation, live Acontext write/retrieve, runtime adapter registration, or IRC/session-manager mutation was performed.

## 3. Tonight's connected path

The June 4 night did not need another proof wrapper. It sharpened the same AAS hold into a clearer daytime decision surface:

```text
00:00 current Acontext runtime prerequisite recheck
-> 01:00 hold continuity
-> 02:00 catalog governance + decision-aid sharpening
-> 03:00 pause handoff
-> 04:00 exponential value connections
-> 05:00 pre-dawn synthesis
```

The durable connection: AAS has a strong internal/admin coordination stack, but the system is now blocked by two real-world facts, not missing docs:

1. no explicit human/operator answer exists for the product/runtime lane;
2. local Acontext runtime cannot be freshly proven while Docker daemon access is unavailable.

## 4. Key synthesis

### Synthesis A — the decision surface is mature enough to stop layering

The current AAS support stack already carries:

- a priority firewall;
- a source-of-truth index;
- a two-lane answer schema;
- decision-aid copy/paste answer shapes;
- service catalog governance;
- current runtime blocker truth;
- safe claims beside blocked claims.

Adding another no-answer implementation layer now risks creating ceremony that looks like progress. The safer move is to stop, hold, or record one real answer.

### Synthesis B — the highest-value product is an operator cockpit, not a public marketplace page

The marketable AAS insight is not "we can launch a catalog." The stronger product is an internal/admin operator cockpit that keeps this shape together:

```text
source ref + current truth check + allowed answer values + safe claim + blocked claim + next required gate
```

That cockpit can later become UI/CLI/admin route work, but only as internal/admin support. It must not become customer copy, pricing, queue launch, dispatch, reputation, worker matching, or public catalog authority.

### Synthesis C — memory, IRC, cross-project intelligence, and agent coordination all compound through boundary survival

The useful reusable pattern is narrow:

- Memory helps only after distillation, not by raw accumulation.
- IRC/session handoffs help only when sanitized invariants survive.
- Cross-project intelligence helps only as a firewall/filter, not as autorouting.
- Agent coordination helps only when safe claims, blocked claims, source references, and next gates survive together.

This is why the stopped-project firewall is product strategy, not just obedience: it proves AAS can resist attractive stale context.

## 5. Daytime recommendations

### Recommended default

Use one of these two values only:

```text
pause_aas_proof_layering
```

or

```text
keep_both_lanes_held
```

Recommendation: `pause_aas_proof_layering` if Saúl wants a clean stop to no-answer layers; `keep_both_lanes_held` if he wants the workstream open while waiting for a real product/runtime decision.

### If Saúl wants product exposure next

Create exactly one separate Retail Reality answer/hold record first. It should name:

- selected value: `create_retail_reality_answer_or_hold_record`;
- non-secret human/operator reference;
- source artifact digest/reference;
- exact approved-or-held boundary;
- authorized review path, if any;
- still-blocked claims.

Do not treat prior candidate, catalog, sample, decision-aid, hold, or synthesis artifacts as approval.

### If Saúl wants runtime memory next

Create exactly one separate runtime-memory operator answer record first. Only after that, and only if the answer selects the runtime-memory lane:

1. restore Docker daemon reachability;
2. rerun read-only image inventory;
3. rerun read-only container inventory;
4. rerun Compose/API/core/UI health checks;
5. only then consider a separate bounded parity attempt.

Do not register/enable an adapter, mutate IRC/session-manager state, write to Acontext, or claim runtime parity from this synthesis.

### If Saúl wants a cockpit next

Treat the cockpit as internal/admin display only. Minimum permitted first slice:

```text
read-only operator cockpit draft over existing docs/fixtures
no answer recording
no approval recording
no public route
no customer copy
no pricing
no queue/dispatch
```

The cockpit should display current truth and allowed choices; it should not select them.

## 6. Still blocked

This synthesis does **not** authorize or claim:

```text
operator answer recorded
operator approval recorded
selected future answer
Retail Reality answer/hold record creation
Retail Reality product exposure
runtime-memory operator answer record creation
runtime-memory wiring
Docker daemon repair
current image inventory verification
current container inventory verification
Compose startup
current Compose health
current Acontext API/core/UI health
live Acontext write or retrieval
runtime parity
runtime adapter registration or enablement
IRC/session-manager mutation
cross-project autorouting
AutoJob integration
Frontier Academy expansion
KK v2 continuation
KarmaCadabra v2 work
customer/public/worker surface
public catalog/pricing/operator queue/dispatch
autonomous dispatch
ERC-8004 reputation
Worker Skill DNA
payment or production readiness
exact GPS/raw metadata release
private-context release
domain/legal/emergency/repair/insurance/SLA authority
worker-copyable doctrine
```

## 7. Verification

Synthesis gate:

```bash
git diff --check
# clean
PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1896 passed in 26.85s
```

Because the daytime board is a current entrypoint indexed by persisted proof artifacts, its digest refresh required regenerating the dependent source-of-truth, decision-support-map, and 4 AM handoff fixtures. No new approval, answer, runtime, product, or public/worker claim was added.

## 8. Daytime entrypoints

- Current synthesis: `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_06_04.md`
- Current board: `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
- Current strategy handoff: `CITY_AS_A_SERVICE_4AM_EXPONENTIAL_VALUE_CONNECTIONS_2026_06_04.md`
- Current decision aid: `CITY_AS_A_SERVICE_OPERATOR_DECISION_AID_2026_06_03.md`
- Current governed catalog: `CITY_AS_A_SERVICE_SERVICE_CATALOG.md`
- Current runtime blocker proof: `CITY_AS_A_SERVICE_ACONTEXT_RUNTIME_PREREQUISITE_CURRENT_RECHECK_IMPLEMENTATION.md`

## 9. One-line handoff

Execution Market AAS has enough internal/admin structure for now; daytime should either explicitly choose `pause_aas_proof_layering`, keep both lanes held, or record exactly one real human/operator answer before any product exposure or runtime-memory movement.
