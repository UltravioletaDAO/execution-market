# City-as-a-Service — Pre-Dawn Synthesis (2026-05-29)

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this 5 AM synthesis. It explicitly allows Execution Market AAS / City-as-a-Service work and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream sessions.

The cron payload still contained stale instructions to pull/analyze AutoJob, expand Frontier Academy, and continue KK v2. Those tracks were not pulled, analyzed, edited, expanded, tested, or committed. This synthesis stayed inside Execution Market AAS / City-as-a-Service only.

## Repo state

- Repo: `projects/execution-market`
- Branch: `feat/operator-route-regret-panel`
- Sync check: `git pull --ff-only` returned `Already up to date`
- Pre-existing untracked file left untouched: `scripts/sign_req.mjs`
- Latest pushed implementation before this synthesis: `062f85f4` (`Add AAS session handoff pickup brief`)

## What tonight connected

The night advanced the Acontext runtime-truth lane and then compressed its coordination state into reusable handoff artifacts:

```text
Docker daemon recovery
-> required-image pull retry
-> extended required-image timeout
-> image-cache path probe
-> cache-path resolution plan
-> digest-pinned pull timeout observation
-> session handoff capsule
-> session handoff pickup brief
```

The important connection is that the AAS system now has both:

1. a concrete runtime blocker with digest-level provenance; and
2. a compact handoff shape that preserves proof IDs, safe claims, blocked claims, and the one next proof without replaying raw transcripts.

This is a stronger posture than more planning: the next daytime step must change the image/cache path or deliberately pause.

## Current decision

Selected daytime track remains:

```text
runtime_truth_prerequisite_activation
```

Selected proof remains:

```text
clear_acontext_sdk_api_dashboard_then_rerun_read_only_preflight
```

But the night narrowed the prerequisite work. Repeating blind Docker pulls is no longer useful evidence. The current actionable blocker is:

```text
ghcr.io/memodb-io/acontext-ui:latest is digest-resolved but not locally cached; digest-pinned Docker pull timed out after 240s.
```

The next safe engineering move is exactly one changed cache path:

```text
trusted_registry_client_export_load_path
```

Acceptable variants, in order of preference:

1. Use a trusted registry client (`crane`, `oras`, `skopeo`, or `regctl`) or equivalent trusted source to inspect/export/load the pinned linux/arm64 image.
2. Use a trusted preloaded tar only with explicit provenance and digest verification.
3. Use a verified remote builder/cache export if a trusted builder/cache already exists.
4. Configure a registry mirror only as a deliberate operator/runtime change.
5. Perform Docker Desktop cache/network maintenance only as a last-resort operator maintenance action.

Do not start Compose unless the first required image is locally present. Do not attempt live write/retrieve parity until all prerequisites and the read-only gate are green.

## Strategic synthesis

### 1. Runtime truth now has a narrower problem statement

At the start of the night, the blocker was broad: Docker/Acontext prerequisites. After the cache probe, resolution plan, and digest-pinned pull observation, the blocker is narrower: the first required Acontext UI image can be resolved at the registry but cannot be pulled into local Docker within bounded windows.

That means daytime should stop spending effort on generic Acontext planning and focus on image acquisition/caching mechanics.

### 2. The handoff artifacts are useful only if they prevent drift

The session handoff capsule and pickup brief are not product surfaces. Their value is operational: they give the next agent/IRC handoff a four-ID header, one selected next proof, safe claims, blocked claims, and a stop condition.

The success metric is boundary survival:

```text
same proof anchor
same selected next proof
same blocked customer/runtime/reputation claims
no raw transcript replay
no accidental live parity authorization
```

### 3. Acontext remains a memory plane candidate, not a proven runtime

Acontext is still strategically valuable as the reusable operational memory layer for City-as-a-Service, but tonight did not prove local services, API/dashboard health, live memory writes, retrieval, or parity. The correct claim is not “Acontext ready”; it is “Acontext prerequisite blocker is now narrowed to image/cache acquisition.”

### 4. Customer-exposure lanes remain decision-bound, not synthesis-bound

Retail Reality and Compliance Desk remain the only clean customer-exposure candidates, but no human/operator answer was captured tonight. The Acontext runtime lane does not authorize customer copy, publication, pricing, queue launch, dispatch, or reputation attachment.

If Saúl wants product exposure during daytime, create exactly one separate human/operator decision artifact over Retail Reality or Compliance Desk. Otherwise keep all AAS families internal/admin-only.

## Current safe claims

Safe to claim from tonight's new rungs:

```text
admin_acontext_image_cache_path_probe_landed
admin_acontext_cache_path_resolution_plan_landed
admin_acontext_digest_pinned_pull_timeout_observation_landed
internal_admin_aas_session_handoff_capsule_landed
internal_admin_aas_session_handoff_pickup_brief_landed
```

Safe to say strategically:

```text
acontext_runtime_blocker_narrowed_to_image_cache_acquisition
trusted_registry_client_export_load_path_is_the_selected_next_cache_path
four_id_handoff_capsule_reduces_raw_transcript_replay
claim_boundary_survival_is_the_coordination_quality_metric
```

## Still blocked / not safe to claim

Do not infer any of the following:

```text
first_required_acontext_image_cached_locally
all_required_acontext_images_present
acontext_compose_started
local_acontext_api_healthy
local_acontext_dashboard_healthy
live_acontext_runtime_parity
acontext_sink_ready
acontext_retrieval_ready
one_live_parity_attempt_authorized_now
irc_runtime_session_manager_enhanced
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

Execute exactly one changed cache path for the pinned Acontext UI image, then rerun inventory.

Concrete pickup order:

1. Choose a trusted cache/export path: preferably `crane`, `oras`, `skopeo`, `regctl`, or an equivalent trusted source.
2. Record how the tool/source was obtained.
3. Use the locked linux/arm64 manifest digest from `acontext_digest_pinned_pull_timeout_observation.json`.
4. Export/load or otherwise cache the image locally.
5. Rerun local image inventory.
6. Stop unless `ghcr.io/memodb-io/acontext-ui:latest` is locally present.
7. Only after first-image presence, continue to all required images, Compose startup, API/dashboard health, read-only preflight rebuild, and one bounded live parity attempt if the gate authorizes it.

Stop line: if the changed cache path fails, record one observation artifact and stop. Do not repeat blind pulls.

### Fork B — product-decision move if Saúl wants customer exposure

Create exactly one separate human/operator answer artifact for one prepared question:

1. Retail Reality selected-boundary approval/hold; or
2. Compliance Desk delivery/publication gate with an exact delivery path.

Stop line: if no real human answer exists, do not create an approval record. Keep all AAS families internal/admin-only.

### Fork C — safe pause

If neither a changed cache path nor a human/operator answer is available, stop. Reuse the session handoff pickup brief as the coordination entrypoint. Do not add more route layers or handoff wrappers.

## Handoff recommendation

The daytime headline should be:

> “Acontext is not ready yet, but the blocker is now specific: the UI image is digest-resolved and pull-stalled. The next useful move is one trusted registry-client/export-load cache path, then image inventory. If that is not available, stop or capture one explicit operator decision for Retail Reality/Compliance Desk.”

## Verification for this synthesis

This is a documentation and coordination synthesis over already-landed implementation artifacts. No code or fixture contract changed in this 5 AM pass.

Required local verification before commit:

```bash
git diff --check
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_session_handoff_pickup_brief.py
```

Full city-ops verification from the preceding implementation remains:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1516 passed
```
