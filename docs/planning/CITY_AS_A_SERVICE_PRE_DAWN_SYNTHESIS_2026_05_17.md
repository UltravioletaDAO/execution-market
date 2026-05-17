# City-as-a-Service — Pre-Dawn Synthesis 2026-05-17

> Status: 5 AM synthesis for daytime operations  
> Scope: Execution Market AAS / City-as-a-Service only  
> Priority source: `~/clawd/DREAM-PRIORITIES.md`  
> Product posture: internal/admin only; no customer/public launch claim

## Governing priority note

`~/clawd/DREAM-PRIORITIES.md` explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream sessions. The cron payload still listed those stale tracks and asked for an AutoJob pull, but this synthesis follows the active priority file and stays inside Execution Market AAS / City-as-a-Service.

`projects/execution-market` was synced with `git pull --ff-only` and was already up to date on `feat/operator-route-regret-panel`. The pre-existing untracked `scripts/sign_req.mjs` remains untouched.

## Night synthesis

Tonight did not broaden product surface. It converted the live-runtime-memory blocker from a vague infrastructure complaint into a precise operational boundary and then connected that boundary to the AAS coordination system.

The night now reads as one chain:

```text
Acontext image-pull timeout
-> GHCR manifest vs Docker pull-stall diagnostic
-> Docker Desktop / BuildKit pull-path diagnostic
-> runtime-memory blocker decision board
-> intelligence-flow compounder
-> pre-dawn daytime handoff
```

The useful insight is:

```text
AAS coordination compounds only when blocked runtime facts are preserved as first-class artifacts, not reinterpreted as progress.
```

This is the same proof-ladder discipline that protects customer copy, dispatch, reputation, GPS/raw metadata, payment claims, and worker doctrine. Runtime-memory must earn promotion through the same gates.

## What changed overnight

### 1. Acontext blocker is now narrow and evidence-backed

The Acontext lane now has three increasingly specific diagnostics:

- `acontext_individual_image_pull_timeout_probe.json`
- `acontext_registry_manifest_pull_stall_diagnostic.json`
- `acontext_docker_pull_path_diagnostic.json`

Current conservative read:

- Docker Desktop is reachable on `desktop-linux`.
- Docker server is local and arm64-capable.
- Buildx / BuildKit is running and advertises `linux/arm64` support.
- GHCR anonymous manifest fetches for key Acontext images succeed.
- GHCR manifests advertise `linux/arm64`.
- Explicit-platform `docker pull --platform linux/arm64 ghcr.io/memodb-io/acontext-ui:latest` still timed out silently inside bounded windows.
- The blocker is now the Docker Desktop / containerd / network / layer-fetch path, or the need for a trusted image cache/mirror.

Safe latest diagnostic claim:

```text
admin_acontext_docker_pull_path_diagnostic_landed
```

It does not prove any image was pulled, compose started, API/dashboard reached, or live Acontext write/retrieve parity.

### 2. Runtime-memory blocker became a daytime decision board

The 3 AM artifact:

- `aas_runtime_memory_blocker_decision_board.json`

turns the diagnostic into a daytime choice rather than a repeated dream loop:

1. repair Docker Desktop / containerd / network layer-fetch;
2. use a trusted pre-populated image cache or mirror;
3. defer live runtime and continue fixture-backed handoffs;
4. replace Acontext runtime only after a separate architecture decision.

Safe claim:

```text
admin_aas_runtime_memory_blocker_decision_board_landed
```

The board explicitly keeps `authorizes_live_runtime=false` until image inventory, compose health, API/dashboard health, an empty rebuilt readiness gate, and one live write/retrieve parity pass all succeed.

### 3. Pattern recognition became a fail-closed compounder

The 4 AM artifact:

- `aas_intelligence_flow_compounder.json`

connects runtime-memory facts to the broader AAS coordination pattern:

1. memory prerequisites → next proof;
2. IRC/session IDs → coordination compression;
3. cross-project patterns → claim quarantine;
4. agent selection → boundary preservation.

Safe claim:

```text
admin_aas_intelligence_flow_compounder_landed
```

It is an internal/admin coordination filter only. It does not authorize autonomous routing, public/customer packaging, dispatch, reputation, payment claims, GPS/raw metadata exposure, or worker-copyable doctrine.

## What did not change

No approval or readiness was promoted for:

- customer copy
- customer delivery
- publication
- public/catalog routes
- controlled pilots
- public prices or customer quotes
- operator queue launch
- dispatch or autonomous dispatch
- ERC-8004 reputation receipts
- worker Skill DNA
- live Acontext sink readiness
- runtime parity
- payment or production-infrastructure reverification
- exact GPS/raw metadata release
- domain-authority, legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability claims
- worker-copyable doctrine

## Integrated daytime recommendation

### If runtime-memory proof is the daytime priority

Do **not** retry compose blindly from cron. Pick one explicit remediation path:

1. inspect/repair Docker Desktop, containerd, network, proxy, or registry layer-fetch behavior; or
2. use a trusted pre-populated image cache/mirror with provenance recorded.

Then proceed only in this order:

```text
verify all required Acontext images present locally
-> start compose
-> healthcheck API and dashboard
-> rerun read-only preflight
-> rebuild blocker delta/read surface/attempt gate
-> attempt exactly one live write/retrieve parity pass only if blockers are empty
```

### If customer exposure is the daytime priority

Do not use tonight's Acontext or coordination artifacts as customer approval. The safe customer-exposure fork is unchanged: create one separate human-operator approval record for the exact Compliance Desk label boundary:

```text
Visible posting / notice compliance snapshot
```

Then validate it with the fail-closed validator. Even a valid record approves only that narrow text boundary unless a separate delivery/publication/pricing/route gate says otherwise.

### If neither prerequisite is ready

Stop adding new public or route surfaces. Continue only narrow internal/admin guardrails that preserve:

- source artifact identity;
- invariant IDs;
- declared-vs-verified badges;
- adjacent safe and blocked claims;
- one next proof.

## Current entrypoints for daytime

Read in this order:

1. `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_17.md`
2. `CITY_AS_A_SERVICE_4AM_HANDOFF_2026_05_17.md`
3. `CITY_AS_A_SERVICE_AAS_INTELLIGENCE_FLOW_COMPOUNDER_IMPLEMENTATION.md`
4. `CITY_AS_A_SERVICE_AAS_RUNTIME_MEMORY_BLOCKER_DECISION_BOARD_IMPLEMENTATION.md`
5. `CITY_AS_A_SERVICE_ACONTEXT_DOCKER_PULL_PATH_DIAGNOSTIC_IMPLEMENTATION.md`
6. `CITY_AS_A_SERVICE_ACONTEXT_REGISTRY_MANIFEST_PULL_STALL_DIAGNOSTIC_IMPLEMENTATION.md`
7. `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
8. `EXECUTION_MARKET_AAS_GAP_MAP_2026_05_12.md`
9. `CITY_AS_A_SERVICE_THREE_FAMILY_AAS_READINESS_MATRIX_2026_05_14.md`
