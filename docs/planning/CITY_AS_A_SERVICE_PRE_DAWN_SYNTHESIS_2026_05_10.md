# City as a Service — Pre-Dawn Synthesis 2026-05-10

> Status: 5 AM synthesis / daytime handoff prep  
> Scope: Execution Market AAS / City-as-a-Service only  
> Governing priority file: `~/clawd/DREAM-PRIORITIES.md`

## 1. Priority reconciliation

The cron payload still included older workstreams: AutoJob, Frontier Academy, and KK v2. The required first read of `~/clawd/DREAM-PRIORITIES.md` overrode that payload. I did **not** pull, analyze, edit, or expand those stopped tracks.

Active dream work remained on Execution Market AAS / City-as-a-Service.

## 2. What tonight connected

Tonight moved the CaaS stack from “we have reviewed proof artifacts” into “we have a conservative internal/admin route handoff chain that can survive day/night coordination.”

The latest chain is now:

```text
Phase 1 reviewed fixtures
-> operator coverage summary artifact
-> read-only coverage renderer/read surface
-> decision-support readiness matrix
-> internal/admin matrix card
-> fail-closed route preflight
-> authenticated internal/admin route
-> operator consumer
-> operator display adapter
-> display-adapter admin route
-> app-level route mount manifest
-> compact route handoff packet
```

The important synthesis is not that CaaS needs another route layer. The important synthesis is that the route layer is now sufficiently boxed in:

- internal/admin-only
- GET-only
- admin-authenticated
- pass-through over persisted artifacts
- digest/parity checked
- safe and blocked claims adjacent
- no customer/public/dispatch/live-memory/reputation/GPS/worker-doctrine promotion

That means the next product-significant frontier is not more internal/admin route wrapping. It is the blocked live transport seam: Acontext write/retrieve parity.

## 3. Live Acontext preflight result at 5 AM

A read-only live Acontext preflight was rerun during synthesis. It did not write to Acontext and did not promote readiness.

Result:

```text
preflight_verdict = live_transport_blocked_before_sink_write
ready_to_attempt_live_transport = false
acontext_sink_ready = false
runtime_parity_proven = false
live_acontext_write_performed = false
live_acontext_retrieval_performed = false
```

Current blockers:

```text
docker_daemon_unavailable
acontext_python_sdk_missing
local_acontext_api_unreachable
local_acontext_dashboard_unreachable
```

Therefore: do not attempt or claim live Acontext transport yet. The correct daytime step is to clear prerequisites first, then rerun preflight before any sink write.

## 4. Daytime recommendation

### Recommendation A — highest value

Clear the local Acontext prerequisites and run exactly one live write/retrieve parity pass using the existing packet contract.

Required order:

1. Start/connect Docker in the execution environment.
2. Install or expose the Acontext Python SDK/CLI.
3. Start/reach local Acontext API at `http://localhost:8029/api/v1`.
4. Start/reach dashboard at `http://localhost:3000`.
5. Rerun `build_acontext_live_preflight_result()` and require `ready_to_attempt_live_transport=true`.
6. Write the existing `city_ops.acontext_transport_packet.v1.stored_payload` under namespace `execution_market.city_as_a_service`.
7. Retrieve by `proof_anchor_id`, `packet_id`, and namespace.
8. Feed retrieval into `assert_acontext_transport_parity(packet, retrieval)`.
9. Only after parity passes, add a separate live transport result artifact/claim.

### Recommendation B — if Acontext remains blocked

Pause route expansion. Do only proof-support fallback work that tightens already-existing guardrails, such as:

- fail if `safe_to_claim[]` and `do_not_claim_yet[]` drift apart
- fail if a route/consumer/display payload invents readiness
- fail if raw transcripts, unreviewed memory, or private operator context become required
- fail if any artifact becomes worker-copyable municipal doctrine

### Recommendation C — what not to do next

Do not broaden into:

- public/customer routes
- customer-facing CaaS catalog copy
- polished console claims
- autonomous dispatch routing
- ERC-8004 reputation receipts
- worker Skill DNA
- legal/regulator readiness
- exact GPS/metadata exposure
- worker-copyable municipal doctrine
- AutoJob / Frontier Academy / KK v2 during dream sessions while the priority stop list remains active

## 5. Strategic insight

CaaS is becoming a product because it refuses to confuse transport with truth.

The proof stack now has three separable layers:

1. **Reviewed truth** — local reviewed fixtures and proof packets.
2. **Proof carriers** — internal/admin artifacts, cards, routes, consumers, display adapters, and handoff packets that preserve reviewed truth without strengthening it.
3. **Transport** — future Acontext write/retrieve parity, which should carry already-reviewed meaning but must not create meaning.

This separation is the moat. Execution Market can sell real-world execution only if every downstream surface can prove exactly what it knows, what it does not know yet, and why it refuses to overclaim.

## 6. Safe claims after synthesis

Safe to claim:

- Phase 1 reviewed fixtures exist for the current local proof set.
- Internal/admin proof carriers exist through the compact route handoff packet.
- The route handoff packet makes the day/night coordination boundary explicit.
- Acontext live preflight exists and is currently blocked before sink write.

Not safe to claim:

- `acontext_sink_ready`
- `runtime_parity_proven`
- `acontext_live_transport_parity_landed`
- public/customer route readiness
- customer copy/catalog readiness
- polished operator console readiness
- dispatch automation readiness
- ERC-8004 reputation readiness
- worker Skill DNA readiness
- legal/regulator readiness
- exact GPS/metadata exposure
- worker-copyable municipal doctrine

## 7. Daytime pickup checklist

- [ ] Decide whether daytime can clear Docker + Acontext SDK/API/dashboard prerequisites.
- [ ] If yes, rerun preflight before any live write.
- [ ] If preflight is ready, run one write/retrieve parity pass only.
- [ ] If preflight remains blocked, do not add more route layers by default.
- [ ] Keep `safe_to_claim[]` and `do_not_claim_yet[]` adjacent in every new artifact.
