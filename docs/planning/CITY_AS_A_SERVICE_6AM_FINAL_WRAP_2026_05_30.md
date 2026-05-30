# City-as-a-Service — 6 AM Final Wrap (2026-05-30)

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this final dream handoff. It explicitly keeps dream work on Execution Market AAS / City-as-a-Service and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2.

The cron payload still carried stale instructions to pull/analyze AutoJob, expand Frontier Academy, and continue KK v2. Those tracks were not pulled, analyzed, edited, expanded, tested, or committed. The final handoff stayed inside Execution Market AAS / City-as-a-Service only.

## Repo state

- Repo used: `projects/execution-market`
- Branch: `feat/operator-route-regret-panel`
- Sync check: `git pull --ff-only` returned `Already up to date`
- Current head before this final wrap: `ee09a443` (`Add AAS pre-dawn synthesis handoff`)
- Pre-existing untracked file left untouched: `scripts/sign_req.mjs`
- Repos intentionally not used because stopped by `DREAM-PRIORITIES.md`: AutoJob, Frontier Academy, KK v2/KarmaCadabra tracks

## What was accomplished vs planned

### Planned by active dream priority

Continue Execution Market AAS / City-as-a-Service and prepare a clean daytime handoff.

### Completed tonight

The night converted Acontext from a Docker/image acquisition problem into a locally running stack with one narrow route/auth blocker:

```text
ORAS OCI-layout cache bridge
-> remaining required images ORAS export/load
-> Compose startup and health observation
-> SDK/API contract discovery smoke
-> project-admin route mismatch observation
-> pre-dawn synthesis
-> 6 AM final wrap
```

The key accomplishment is that yesterday's cache blocker is closed locally:

```text
All nine required Acontext Compose images are present locally, Compose starts with --no-build, API/core health returns 200, and the UI redirects to /dashboard.
```

The new blocker is higher in the stack and more precise:

```text
Swagger advertises POST /admin/v1/project, but the running local API returns 404 page not found for both /admin/v1/project and /api/v1/admin/v1/project, so a scoped project Bearer secret has not been acquired yet.
```

### Not done, intentionally

- No AutoJob pull, analysis, or EM integration file work.
- No Frontier Academy guide expansion.
- No KK v2 swarm work.
- No live Acontext project creation.
- No project Bearer secret persisted or printed.
- No live session/message write/retrieve parity attempt.
- No IRC runtime session-manager mutation.
- No customer/public/pricing/dispatch/reputation/payment/worker-doctrine promotion.

## Morning briefing

### What changed overnight

Acontext moved from "can we even fetch/cache the runtime?" to "the runtime is up locally, but the documented/admin project-secret path does not match the served API." That is a much better daytime problem: route mounting, version/config, or supported credential-creation path investigation instead of another blind Docker/cache retry.

### Key insights for ongoing priorities

1. **The ORAS cache path worked.** It should remain the preferred repeatable image acquisition path if image inventory regresses, but it is no longer the active blocker.
2. **Health is not parity.** API/core 200s and UI redirect prove local stack liveness, not write/retrieve memory semantics.
3. **The project secret is now the boundary-critical object.** Any root/admin token or scoped Bearer secret must remain in process memory only; docs/fixtures/logs should record redacted pass/fail evidence only.
4. **Runtime repair does not authorize product exposure.** Customer copy, public catalog, delivery path, dispatch, reputation, pricing, GPS/raw metadata, and worker-copyable doctrine still require separate gates.

### Immediate daytime attention

Pick exactly one fork.

#### Fork A — recommended engineering move

Resolve the Acontext project-secret route/path, then run one separate redacted write/retrieve parity artifact.

Concrete pickup order:

1. Inspect the local Acontext server route mounting/config to explain the `POST /admin/v1/project` Swagger-vs-runtime mismatch.
2. Check whether the route is behind a different base path, build tag, service, gateway, or version than the served Swagger document.
3. If the route is intentionally unavailable, identify the supported local project-secret creation path.
4. Use any root/admin token only in memory; never print, log, fixture, or commit it.
5. Once a scoped project Bearer secret exists, create one sanitized session and one sanitized message payload.
6. Retrieve that payload through the documented API.
7. Persist only redacted evidence and claim boundaries in a new fixture/artifact.
8. Stop unless both write and retrieval succeed.

Stop line: if project-secret acquisition remains blocked, record exactly one mismatch/resolution observation and stop. Do not mutate IRC runtime management or claim parity.

#### Fork B — product-decision move

If Saúl wants customer exposure, create exactly one separate human/operator answer artifact for one prepared question:

1. Retail Reality selected-boundary approval/hold; or
2. Compliance Desk delivery/publication gate with an exact delivery path.

Stop line: if no real human answer exists, do not create an approval record.

#### Fork C — safe pause

If neither route/auth investigation nor a human/operator answer is available, stop. The current board is sufficient; do not add more handoff wrappers, route layers, or customer-facing copy.

## Current safe claims

```text
admin_acontext_oras_oci_layout_cache_bridge_landed
admin_acontext_remaining_images_oras_compose_health_landed
admin_acontext_sdk_api_contract_discovery_smoke_landed
admin_acontext_project_admin_route_mismatch_observation_landed
admin_aas_pre_dawn_synthesis_2026_05_30_landed
admin_aas_6am_final_wrap_2026_05_30_landed
```

Safe strategic wording:

```text
acontext_image_cache_blocker_cleared_locally
all_required_acontext_compose_images_present_locally
local_acontext_compose_stack_started_and_health_checked
acontext_project_secret_path_is_the_current_runtime_parity_blocker
next_gate_is_route_or_supported_secret_creation_path_resolution
```

## Still blocked / not safe to claim

Do not infer any of the following:

```text
acontext_project_created
project_bearer_secret_acquired
live_acontext_session_created
live_acontext_message_written
live_acontext_message_retrieved
live_acontext_runtime_parity
acontext_sink_ready
acontext_retrieval_ready
irc_runtime_session_manager_enhanced
cross_project_autorouting_ready
customer_copy_ready
customer_delivery_approved
publication_approved
public_catalog_ready
public_route_ready
public_pricing_or_customer_quote_ready
paid_pilot_ready
operator_queue_launch_ready
autonomous_dispatch_ready
autojob_integration_ready
frontier_academy_expansion_ready
kk_v2_swarm_ready
erc8004_reputation_ready
worker_skill_dna_ready
payment_or_production_reverified
exact_gps_or_raw_metadata_release_allowed
private_operator_context_release_allowed
raw_transcript_authority
legal_or_regulator_or_domain_authority
emergency_or_safety_authority
repair_or_insurance_or_sla_authority
official_report_or_fault_liability_authority
dataset_or_analytics_publication_ready
worker_copyable_aas_doctrine
worker_copyable_municipal_doctrine
```

## Ecosystem position after tonight

Execution Market AAS is better positioned because the runtime-memory lane now has a real local stack and a falsifiable credential-path gate. The ecosystem posture is:

- AAS package/customer lanes remain conservative and review-bound.
- Acontext runtime-memory is locally alive but blocked before write/retrieve parity.
- Coordination artifacts reduce drift across agents/sessions without expanding public claims.
- The next meaningful advance must be either one route/auth proof or one explicit operator decision.

## Verification for this final wrap

This is a documentation and coordination wrap over already-landed implementation artifacts. Required verification before commit:

```bash
git diff --check
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_acontext_project_admin_route_mismatch_observation.py
```

Full city-ops verification from the preceding implementation remains:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1564 passed
```
