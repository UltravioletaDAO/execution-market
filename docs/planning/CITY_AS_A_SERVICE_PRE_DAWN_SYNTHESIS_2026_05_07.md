# City as a Service — Pre-Dawn Synthesis (2026-05-07)

> Time: 05:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Branch: `feat/operator-route-regret-panel`  
> Status: synthesis handoff; no new readiness claim

## 1. Priority discipline

This session read `~/clawd/DREAM-PRIORITIES.md` first and treated it as authoritative.
The older cron body still mentioned AutoJob, Frontier Academy, and KK v2, but those are explicitly stopped in the dream priority file.
No AutoJob, Frontier Academy, KK v2, or KarmaCadabra v2 work was performed.

## 2. What tonight actually built

The night converted the City-as-a-Service proof loop from a pile of replay artifacts into a compact coordination spine that can survive handoff across agents, operator surfaces, and future Acontext transport without strengthening the claim.

Current earned label:

```text
reuse_parity_landed
+ telemetry_gate_landed
+ closure_preview_persisted
+ session_rebuild_consumer_landed
+ session_rebuild_report_fixture_landed
+ acontext_transport_parity_test_landed
+ acontext_live_preflight_landed
+ thin_operator_debug_surface_landed
+ proof_observability_metrics_landed
+ coordination_intelligence_snapshot_landed
```

Still false / blocked:

```text
closure_proof_landed
session_rebuild_ready
acontext_sink_ready
runtime_parity_proven
acontext_live_write_completed
acontext_live_retrieval_completed
acontext_live_transport_parity_landed
worker-copyable municipal doctrine
polished_review_console_ready
office_memory_view_ready
broad_operator_workflow_ready
multi_jurisdiction_playbook_ready
autonomous_city_dispatch_ready
```

## 3. Artifact spine now available

For proof anchor `redirect_outdated_packet_001`, the persisted proof-block directory now contains:

```text
city_shared_decision_parity_scoreboard.json
proof_block_telemetry_gate.json
session_rebuild_preview.json
acontext_export_preview.json
session_rebuild_report.json
acontext_transport_parity_result.json
acontext_live_preflight_result.json
operator_debug_surface.json
proof_observability_snapshot.json
coordination_intelligence_snapshot.json
```

The important integration point is not the number of files.
It is that each downstream artifact is constrained to preserve the same judged truth:

```text
compact decision object
-> coordination ledger / pickup brief
-> dispatch guidance
-> reuse behavior scoreboard
-> shared decision parity scoreboard
-> telemetry gate
-> closure previews
-> session rebuild report
-> Acontext transport packet/parity fixture
-> live preflight
-> operator debug surface
-> observability snapshot
-> coordination intelligence snapshot
```

A downstream consumer is allowed to render or transport the reviewed meaning.
It is not allowed to upgrade trust, tone, placement, readiness, or worker-copyability.

## 4. Strategic connections

### 4.1 Execution Market dispatch

CaaS is now best framed as **dispatch compounding**, not a city-task catalog.
The product claim is narrow and strong:

> reviewed municipal reality can make the next dispatch more accurate, while preserving proof of why it changed.

This connects directly to EM's existing task lifecycle and evidence model because the value appears after review, not at task creation.

### 4.2 Acontext

Acontext should be treated as transport and retrieval infrastructure for compact reviewed meaning.
It must not be treated as the source of truth.
The live sink remains blocked until local prerequisites are real, but the contract is ready:

1. preflight must report `ready_to_attempt_live_transport=true`
2. the same compact packet must be written and retrieved
3. `assert_acontext_transport_parity(...)` must pass
4. only then can the team claim live transport parity

### 4.3 Operator surfaces

The thin debug surface is useful because it shows safe claims and blocked claims together.
That should influence future dashboard work: every operator-facing CaaS surface needs to show the claim boundary, not just the helpful recommendation.

### 4.4 Agent coordination

The coordination intelligence snapshot makes the main pattern explicit:

- coordinate through invariant proof IDs, not chat-log archaeology
- carry safe and blocked claims together
- reuse municipal learning as operator-visible preparation before worker-copyable doctrine
- keep transport separate from truth

This is the same pattern that can later apply to other AAS verticals, but City-as-a-Service should remain the proving ground.

## 5. Daytime recommendations

### Recommendation A — clear live Acontext prerequisites first if possible

This is the highest-value daytime move if the environment can be changed:

1. start Docker / local Acontext services
2. install or expose the Acontext Python SDK
3. make `http://localhost:8029/api/v1` reachable
4. make the local dashboard reachable if the preflight requires it
5. rerun the live preflight until `ready_to_attempt_live_transport=true`
6. run one write/retrieve pass using the existing transport packet
7. assert the retrieved result preserves promotion class, tone, placement, copyability, readiness, safe claims, and blocked claims

Do not claim `acontext_sink_ready` from a preflight alone.

### Recommendation B — if infra is still blocked, add no broad product surface yet

If Docker/Acontext cannot be cleared during the day, the next safe work is not a polished dashboard.
It is one more narrow proof-support seam, such as:

- a command that prints the current proof-block readiness summary from the persisted artifacts
- a second deliberately failing drift fixture for the debug/observability stack
- a checklist runner that fails if any artifact drops `do_not_claim_yet[]`

Keep this boring.
Boring proof rails are the moat.

### Recommendation C — defer expansion until the first anchor earns live parity or a second anchor is frozen

Do not expand to multi-jurisdiction playbooks, autonomous dispatch, or worker-copyable doctrine from this single redirect/outdated-packet anchor.
The next expansion should require either:

1. live local Acontext write/retrieve parity for the current anchor, or
2. a second frozen proof anchor with the same compact-artifact discipline.

## 6. Daytime handoff checklist

Before any broader claim, verify:

- [ ] `PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q` passes
- [ ] `scripts/sign_req.mjs` remains untouched/untracked unless intentionally handled in a separate safety review
- [ ] no commit uses `git add -A` or `git add .`
- [ ] staged diff contains only CaaS files for the current PR
- [ ] `git diff --staged | grep -E '0x[0-9a-fA-F]{64}'` returns nothing
- [ ] safe claims and blocked claims still appear together in handoff artifacts
- [ ] `acontext_sink_ready=false` until a live write/retrieve parity pass exists

## 7. Sharp morning summary

CaaS is getting close to a real product loop, but the honest milestone is still not “city operations ready.”
The milestone is:

> one reviewed city task becomes compact, inspectable operational memory that improves the next dispatch and survives handoff, observability, and transport without overclaiming.

Tonight strengthened the handoff/observability side of that loop.
Daytime should either unblock live Acontext parity or keep adding narrow guardrails that make overclaiming impossible.
