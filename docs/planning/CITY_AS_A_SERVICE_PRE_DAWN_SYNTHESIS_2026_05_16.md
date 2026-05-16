# City as a Service — Pre-Dawn Synthesis 2026-05-16

> Status: 5 AM synthesis for daytime operations
> Scope: Execution Market AAS / City-as-a-Service only
> Priority source: `~/clawd/DREAM-PRIORITIES.md`
> Product posture: internal/admin only; no customer/public launch claim

## Governing priority note

`~/clawd/DREAM-PRIORITIES.md` explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream sessions. The stale cron payload still listed those tracks, but this synthesis follows the priority file and stays inside Execution Market AAS / City-as-a-Service.

`projects/execution-market` was synced with `git pull --ff-only` and was already up to date on `feat/operator-route-regret-panel`. The pre-existing untracked `scripts/sign_req.mjs` remains untouched.

## Night synthesis

Tonight's useful work did not expand public product scope. It tightened the internal/admin coordination system around the two live decision lanes:

1. **Runtime-memory proof lane** — Acontext prerequisites are more clearly separated between setup progress and true readiness.
2. **Coordination multiplier lane** — future agents now have a compact pattern map for preserving proof continuity without reopening raw transcripts or promoting blocked claims.

The core insight is:

```text
AAS scales only when every handoff preserves invariant IDs, declared-vs-verified badges, sticky blocked claims, and exactly one next proof.
```

That is stronger than adding another surface. It gives daytime operators a way to decide what is safe to do next without confusing setup progress with launch readiness.

## What changed since the May 15 final handoff

### 1. Acontext blockers moved from vague to operationally inspectable

The live-memory lane now has a sequence of internal/admin artifacts:

- `acontext_live_preflight_blocker_delta.json`
- `acontext_live_preflight_blocker_delta_read_surface.json`
- `acontext_live_parity_attempt_readiness_gate.json`
- `acontext_prerequisite_activation_board.json`
- `acontext_prerequisite_recovery_attempt_log.json`
- `acontext_explicit_venv_preflight_rerun.json`

Current conservative state:

- Docker is available.
- Acontext CLI / compose files / `.env` exist.
- Dedicated SDK venv imports `acontext==0.1.13`.
- Default Homebrew Python runner still cannot import `acontext`.
- Local API `localhost:8029` and dashboard `localhost:3000` remain unreachable.
- Compose image pulls did not finish inside tight cron windows.
- No live write/retrieve parity attempt is authorized yet.

Safe latest Acontext claim:

```text
admin_acontext_explicit_venv_preflight_rerun_landed
```

### 2. Coordination observability became a scoring contract

The new board:

- `aas_coordination_observability_success_metrics_board.json`

scores future-agent success as:

```text
boundary preservation + invariant-ID handoff + declared-vs-verified honesty + one next proof
```

Safe claim:

```text
admin_aas_coordination_observability_success_metrics_board_landed
```

### 3. Coordination multiplier patterns became reusable

The new map:

- `aas_coordination_multiplier_pattern_map.json`

turns the board into a compact operator playbook:

1. Start with the four invariant IDs.
2. Badge every strength as declared or verified.
3. Keep safe and blocked claims adjacent.
4. Leave one concrete next-proof slot.
5. Treat cross-project intelligence as an internal filter, not autopilot.

Safe claim:

```text
admin_aas_coordination_multiplier_pattern_map_landed
```

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

Run the prerequisite sequence, not the parity attempt directly:

1. Let Acontext compose image pulls complete with a long enough window.
2. Start local Acontext services.
3. Healthcheck API and dashboard.
4. Rerun read-only preflight with `~/clawd/.venv-acontext/bin/python` if default runner remains unwired.
5. Rebuild blocker delta, read surface, and readiness gate.
6. Attempt exactly one live write/retrieve parity pass only if the rebuilt gate has empty blockers.

### If customer exposure is the daytime priority

Do not use the Acontext or coordination artifacts as approval. Create one separate human-operator approval record for the exact Compliance Desk label boundary:

```text
Visible posting / notice compliance snapshot
```

Then validate it with the existing fail-closed validator. Even a passing record approves only that narrow text boundary, not customer delivery, publication, pricing, routes, queue launch, dispatch, reputation, runtime, GPS/raw metadata, domain authority, or worker doctrine.

### If neither prerequisite is ready

Keep building only narrow internal/admin guardrails that preserve the same invariant IDs, declared-vs-verified badges, sticky blocked claims, and one-next-proof slot. Do not broaden routes, public packaging, dispatch, reputation, or worker instructions.

## Current entrypoints for daytime

Read in this order:

1. `CITY_AS_A_SERVICE_FINAL_MORNING_HANDOFF_2026_05_16.md`
2. `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_05_16.md`
3. `CITY_AS_A_SERVICE_2AM_HANDOFF_2026_05_16.md`
4. `CITY_AS_A_SERVICE_AAS_COORDINATION_MULTIPLIER_PATTERN_MAP_IMPLEMENTATION.md`
5. `CITY_AS_A_SERVICE_AAS_COORDINATION_OBSERVABILITY_SUCCESS_METRICS_BOARD_IMPLEMENTATION.md`
6. `CITY_AS_A_SERVICE_THREE_FAMILY_AAS_READINESS_MATRIX_2026_05_14.md`
7. `EXECUTION_MARKET_AAS_GAP_MAP_2026_05_12.md`
8. `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md`
