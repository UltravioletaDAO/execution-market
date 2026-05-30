# City-as-a-Service — Pre-Dawn Synthesis (2026-05-30)

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this 5 AM synthesis. It explicitly allows Execution Market AAS / City-as-a-Service work and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream sessions.

The cron payload still contained stale instructions to pull/analyze AutoJob, expand Frontier Academy, and continue KK v2. Those tracks were not pulled, analyzed, edited, expanded, tested, or committed. This synthesis stayed inside Execution Market AAS / City-as-a-Service only.

## Repo state

- Repo: `projects/execution-market`
- Branch: `feat/operator-route-regret-panel`
- Sync check: `git pull --ff-only` returned `Already up to date`
- Pre-existing untracked file left untouched: `scripts/sign_req.mjs`
- Latest pushed implementation before this synthesis: `b3468a9e` (`Add Acontext admin route mismatch observation`)

## What tonight connected

The night converted Acontext from a broad image/cache blocker into a running local stack with a precise API/auth blocker:

```text
ORAS OCI-layout cache bridge
-> remaining required images ORAS export/load
-> Compose startup and health observation
-> SDK/API contract discovery smoke
-> project-admin route mismatch observation
```

The important connection is that the prior May 29 blocker is now closed: the required image inventory and Compose health gates are green locally. The new blocker is narrower and higher in the stack: Swagger advertises the project-admin creation route, but the running API does not serve it at the probed paths, so a project Bearer secret cannot yet be acquired for a sanitized write/retrieve parity smoke.

## Current decision

Selected daytime track remains:

```text
runtime_truth_prerequisite_activation
```

Selected proof is now narrower than yesterday:

```text
resolve_acontext_project_secret_path_then_run_one_sanitized_write_retrieve_parity_smoke
```

The previous selected cache path succeeded. Do not repeat image-cache work unless image inventory regresses. The next safe engineering move is exactly one route/auth resolution path:

1. Determine why Swagger advertises `POST /admin/v1/project` while the running local API returns `404 page not found` for `/admin/v1/project` and `/api/v1/admin/v1/project`.
2. Or identify the supported non-admin path for creating/obtaining a local project Bearer secret.
3. Keep any secret value in process memory only; do not print, log, fixture, or commit it.
4. In a separate artifact, create one sanitized test session, store one sanitized payload, retrieve it, and record only redacted pass/fail evidence.
5. Stop unless both write and retrieval succeed.

## Strategic synthesis

### 1. Runtime truth moved from supply-chain acquisition to API contract mismatch

The ORAS path proved useful: all nine Acontext Compose images are locally present, Compose starts with `--no-build`, API/core health returns 200, and the UI redirects to `/dashboard`. That means the active risk is no longer “can we get the runtime onto the machine?” It is now “can we create the scoped project credential required to use the runtime safely?”

This is real progress because the next action is an API/route contract investigation, not another Docker/cache retry.

### 2. Acontext is running locally, but runtime parity is still unproven

Local health and Swagger discovery are prerequisites, not parity. The system has not yet proven live session creation, message write, message retrieval, cleanup/quarantine, IRC session-manager integration, or cross-project memory autorouting.

The correct claim is:

```text
acontext_local_stack_healthy_project_secret_path_blocked
```

not:

```text
acontext_runtime_parity_ready
```

### 3. The project Bearer secret is the next boundary-critical object

The project secret is now the critical interface between local Acontext and Execution Market AAS memory claims. It must be handled as an ephemeral credential:

- no token value in fixtures;
- no token value in docs;
- no token value in logs;
- no project/session/message IDs persisted unless deliberately sanitized and non-sensitive;
- one bounded test object only;
- cleanup/quarantine if the API supports it.

### 4. Product exposure is still a separate human/operator decision

The local Acontext stack does not authorize customer/public exposure. Retail Reality and Compliance Desk remain the only clean customer-exposure candidates, and only if Saúl gives one explicit operator answer. Runtime repair should not be interpreted as approval for copy, publication, pricing, dispatch, reputation, payment claims, exact GPS/raw metadata release, or worker doctrine.

## Current safe claims

Safe to claim from tonight's new rungs:

```text
admin_acontext_oras_oci_layout_cache_bridge_landed
admin_acontext_remaining_images_oras_compose_health_landed
admin_acontext_sdk_api_contract_discovery_smoke_landed
admin_acontext_project_admin_route_mismatch_observation_landed
```

Safe to say strategically:

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

## Daytime action board

Pick exactly one fork.

### Fork A — recommended engineering move

Resolve the Acontext project-secret path, then run one separate sanitized write/retrieve parity artifact.

Concrete pickup order:

1. Inspect the local Acontext server route mounting/config to explain the `POST /admin/v1/project` Swagger-vs-runtime mismatch.
2. Check whether the admin route is behind a different base path, build tag, service, gateway, or version than the served Swagger document.
3. If the route is intentionally unavailable, identify the supported local project-secret creation path.
4. Use any root/admin token only in memory; never print or persist it.
5. Once a scoped project Bearer secret exists, create one sanitized session and one sanitized message payload.
6. Retrieve that payload through the documented API.
7. Persist only redacted evidence and claim boundaries in a new fixture/artifact.
8. Stop unless both write and retrieval succeed.

Stop line: if project-secret acquisition remains blocked, record exactly one mismatch/resolution observation and stop. Do not mutate IRC runtime management or claim parity.

### Fork B — product-decision move if Saúl wants customer exposure

Create exactly one separate human/operator answer artifact for one prepared question:

1. Retail Reality selected-boundary approval/hold; or
2. Compliance Desk delivery/publication gate with an exact delivery path.

Stop line: if no real human answer exists, do not create an approval record. Keep all AAS families internal/admin-only.

### Fork C — safe pause

If neither route/auth investigation nor a human/operator answer is available, stop. The current board is sufficient; do not add more handoff wrappers, route layers, or customer-facing copy.

## Handoff recommendation

The daytime headline should be:

> “Acontext image/cache and Compose blockers are cleared locally. The stack is healthy enough for contract work, but runtime parity is still blocked because project-secret acquisition is unresolved: Swagger advertises `POST /admin/v1/project`, while the running API returns 404 at the probed paths. Next: resolve that route/auth path, then run one redacted write/retrieve parity smoke.”

## Verification for this synthesis

This is a documentation and coordination synthesis over already-landed implementation artifacts. No code or fixture contract changed in this 5 AM pass.

Required local verification before commit:

```bash
git diff --check
```

Full city-ops verification from the preceding implementation remains:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1564 passed
```
