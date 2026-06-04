# City-as-a-Service — 10 PM AAS Truth-Path Scout (2026-06-03)

> Scope: Execution Market AAS / City-as-a-Service only.
> Governing priority: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`.
> Status: internal/admin read-only prerequisite checkpoint; no operator answer, no approval, no runtime mutation, no customer/public exposure.

## 1. Priority firewall

`/Users/clawdbot/clawd/DREAM-PRIORITIES.md` was read first and obeyed.

Allowed focus:

- Execution Market AAS / City-as-a-Service plans and AAS concepts.

Explicitly not worked on:

- KarmaCadabra v2;
- Frontier Academy;
- AutoJob;
- KK v2;
- stopped-project integrations.

## 2. Source stack inspected

Current June 3 AAS state reviewed:

- `CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_06_03.md`
- `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_06_03.md`
- `CITY_AS_A_SERVICE_OPERATOR_DECISION_AID_2026_06_03.md`
- `CITY_AS_A_SERVICE_10PM_AAS_NEXT_STEPS_2026_06_02.md`

Relevant Acontext/runtime-memory state reviewed:

- `CITY_AS_A_SERVICE_ACONTEXT_ORAS_OCI_LAYOUT_CACHE_BRIDGE_IMPLEMENTATION.md`
- `CITY_AS_A_SERVICE_ACONTEXT_REMAINING_IMAGES_ORAS_COMPOSE_HEALTH_IMPLEMENTATION.md`
- `CITY_AS_A_SERVICE_ACONTEXT_ROOT_PREFIXED_LOCAL_WRITE_RETRIEVE_PARITY_IMPLEMENTATION.md`
- `CITY_AS_A_SERVICE_ACONTEXT_OPERATOR_ACTIVATION_ANSWER_RECORD_DRY_RUN_VALIDATOR_IMPLEMENTATION.md`
- `CITY_AS_A_SERVICE_ACONTEXT_OPERATOR_ACTIVATION_NO_ANSWER_PAUSE_LEDGER_IMPLEMENTATION.md`

## 3. Read-only local prerequisite facts checked

Read-only commands only were used. No Compose startup, no Docker pull, no ORAS copy/pull, no live Acontext write/retrieve, no runtime config mutation, no public/customer route, and no external destructive path were used.

### Required Acontext image list still resolves from code

The code-defined required image set remains nine images:

```text
ghcr.io/memodb-io/acontext-ui:latest
chrislusf/seaweedfs:4.02
pgvector/pgvector:pg16
redis:7.4
rabbitmq:4-management
ghcr.io/memodb-io/acontext-api:latest
amazon/aws-cli:2.32.6
ghcr.io/memodb-io/acontext-core:latest
jaegertracing/all-in-one:1.75.0
```

### Docker daemon is currently not reachable

Current Docker context:

```text
desktop-linux *   Docker Desktop   unix:///Users/clawdbot/.docker/run/docker.sock
```

Current daemon check:

```text
Cannot connect to the Docker daemon at unix:///Users/clawdbot/.docker/run/docker.sock. Is the docker daemon running?
```

Meaning: the current session cannot re-verify local image inventory, container inventory, Compose health, API/core/UI reachability, or live local parity because the Docker daemon is offline/unreachable.

### ORAS is still installed, but no local `/tmp` OCI layouts remain

Observed:

```text
/opt/homebrew/bin/oras
Version: 1.3.2+Homebrew
OS/Arch: darwin/arm64
```

A read-only `/tmp` scan found no remaining `acontext` ORAS/OCI layout paths. That is not a failure by itself; it only means the temporary cache layouts from the earlier ORAS bridge are not currently present in `/tmp`.

### Prior proof fixtures still exist, but are historical proof, not current daemon truth

The persisted proof fixtures still record earlier successful states:

- `acontext_remaining_images_oras_compose_health.json` says all required images were present and local API/core/UI reachability passed during the May 30 observation.
- `acontext_root_prefixed_local_write_retrieve_parity.json` says one sanitized local session/message write-retrieve parity succeeded via root-prefixed bearer auth during the May 30/31 observation.

Because Docker is currently unreachable, those fixtures cannot be promoted to a fresh current-runtime claim.

## 4. Smallest truth-producing step found

The smallest useful step that did **not** require Saúl awake was this read-only prerequisite recheck. It produced one new current fact:

```text
current_local_acontext_runtime_reverification_blocked_by_docker_daemon_unreachable
```

That fact is more useful than another no-answer wrapper because it distinguishes two separate blockers:

1. **Decision blocker:** AAS still needs exactly one explicit operator answer or explicit pause before product/runtime promotion.
2. **Runtime prerequisite blocker:** even if runtime-memory work is later selected, the local Docker daemon must be reachable before image inventory, Compose health, or local Acontext parity can be freshly reverified.

## 5. Safe daytime fork

Pick exactly one daytime path.

### Fork A — recommended default if no operator answer exists

Record/preserve `pause_aas_proof_layering` or keep both lanes held. Do not add more no-answer proof wrappers. The June 3 source index, decision-support map, synthesis, final wrap, and decision aid are enough to preserve state.

### Fork B — product-exposure answer path

Create exactly one separate Retail Reality answer/hold record against the two-lane schema. Do not treat candidate selection, no-answer hold packets, source indexes, or decision aids as approval.

### Fork C — runtime-memory answer path

Create exactly one separate runtime-memory operator answer record first. After that, and only if it explicitly selects runtime-memory work, restore/repair local Docker daemon reachability and rerun read-only inventory before any Compose/API/parity work.

Minimum fresh prerequisite check after Docker is reachable:

```bash
docker context ls
docker info --format 'ServerVersion={{.ServerVersion}} OperatingSystem={{.OperatingSystem}} Architecture={{.Architecture}} Driver={{.Driver}}'
docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.CreatedSince}} {{.Size}}' \
  | grep -E 'memodb|pgvector|redis|rabbitmq|seaweedfs|amazon/aws-cli|jaegertracing'
docker ps -a --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}' \
  | grep -E 'acontext|memodb|pgvector|redis|rabbitmq|seaweedfs|jaeger|aws-cli'
```

Stop there unless a separate authorization allows Compose startup or a bounded local parity rerun.

## 6. Still blocked

This checkpoint does **not** approve or claim:

```text
operator answer recorded
operator approval recorded
selected future answer
Retail Reality answer/hold record creation
Retail Reality product exposure
runtime-memory operator answer record creation
runtime adapter registration or enablement
IRC/session-manager mutation
current local Docker image inventory verified
current local Acontext Compose health
current local Acontext API/core/UI health
fresh live Acontext write or retrieval
runtime parity proven in the current session
cross-project autorouting
customer/public/worker surface
catalog/pricing/operator queue/dispatch readiness
ERC-8004 reputation or Worker Skill DNA
payment or production readiness
exact GPS/raw metadata release
private operator context release
raw transcript authority
legal/emergency/repair/insurance/SLA authority
worker-copyable doctrine
stopped-project integration
```

## 7. Safe claim

Safe to claim only:

```text
internal_admin_aas_10pm_truth_path_scout_landed
```

Meaning only: a read-only scout checked current AAS/Acontext state, found Docker daemon reachability is the immediate local runtime-prerequisite blocker, and produced a daytime fork that avoids additional no-answer ceremony.
