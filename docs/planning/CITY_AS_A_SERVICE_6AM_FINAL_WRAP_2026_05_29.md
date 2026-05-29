# City-as-a-Service — 6 AM Final Wrap (2026-05-29)

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this final dream handoff. It explicitly keeps dream work on Execution Market AAS / City-as-a-Service and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2.

The cron payload still carried stale instructions to pull/analyze AutoJob, expand Frontier Academy, and continue KK v2. Those tracks were not pulled, analyzed, edited, expanded, tested, or committed. The final handoff stayed inside Execution Market AAS / City-as-a-Service only.

## Repo state

- Repo used: `projects/execution-market`
- Branch: `feat/operator-route-regret-panel`
- Sync check: `git pull --ff-only` returned `Already up to date`
- Current head before this final wrap: `53b73b4a` (`Add AAS pre-dawn synthesis handoff`)
- Pre-existing untracked file left untouched: `scripts/sign_req.mjs`
- Repos intentionally not used because stopped by `DREAM-PRIORITIES.md`: AutoJob, Frontier Academy, KK v2/KarmaCadabra tracks

## What was accomplished vs planned

### Planned by active dream priority

Continue Execution Market AAS / City-as-a-Service and prepare a clean daytime handoff.

### Completed tonight

The night produced a narrow runtime-truth stack for Acontext plus reusable coordination artifacts:

```text
Docker daemon recovery
-> required-image pull retry
-> extended required-image timeout
-> image-cache path probe
-> cache-path resolution plan
-> digest-pinned pull timeout observation
-> session handoff capsule
-> session handoff pickup brief
-> pre-dawn synthesis
-> 6 AM final wrap
```

The key accomplishment is not that Acontext is ready. It is that the blocker is now specific enough for daytime execution:

```text
ghcr.io/memodb-io/acontext-ui:latest is digest-resolved, linux/arm64 metadata is known, but the digest-pinned Docker pull timed out after 240 seconds and the image is still not locally cached.
```

### Not done, intentionally

- No AutoJob pull, analysis, or EM integration file work.
- No Frontier Academy guide expansion.
- No KK v2 swarm work.
- No Compose startup.
- No local Acontext API/dashboard health claim.
- No live write/retrieve parity attempt.
- No customer/public/pricing/dispatch/reputation/payment/worker-doctrine promotion.

## Morning briefing

### What changed overnight

The AAS runtime lane moved from broad “Acontext/Docker prerequisites” to a concrete image/cache acquisition problem. The system now knows the first required UI image can be resolved at GHCR, but Docker cannot pull/cache it within bounded windows.

The coordination lane also improved: the session handoff capsule and pickup brief preserve proof IDs, safe claims, blocked claims, and the selected next proof without replaying raw transcripts or accidentally authorizing runtime/customer claims.

### Key insights for ongoing priorities

1. **Stop repeating blind pulls.** Further `docker pull ghcr.io/memodb-io/acontext-ui:latest` attempts are unlikely to produce new evidence unless the cache/acquisition path changes.
2. **Acontext is still strategic, but unproven.** It remains a good candidate for the AAS operational memory plane; local API/dashboard/runtime parity are still unproven.
3. **Handoffs are now useful only if they preserve boundaries.** The success metric is claim-boundary survival: same proof anchor, same selected next proof, same blocked claims, no raw transcript replay, no accidental live parity authorization.
4. **Customer exposure still needs a human/operator decision.** Retail Reality and Compliance Desk remain the clean candidates, but no approval/hold answer was captured tonight.

### Immediate daytime attention

Pick exactly one fork:

#### Fork A — recommended engineering move

Execute one trusted registry-client/export-load cache path for the pinned `acontext-ui` linux/arm64 image, then rerun image inventory.

Concrete order:

1. Choose a trusted registry/cache tool or equivalent trusted source (`crane`, `oras`, `skopeo`, `regctl`, trusted preloaded tar, or verified remote cache/export).
2. Record tool/source provenance.
3. Use the locked linux/arm64 manifest digest from `acontext_digest_pinned_pull_timeout_observation.json`.
4. Export/load/cache the image locally.
5. Rerun image inventory.
6. Stop unless `ghcr.io/memodb-io/acontext-ui:latest` is locally present.
7. Only after first-image presence: continue to all required images, Compose startup, API/dashboard health, read-only preflight rebuild, and one bounded live parity attempt if the gate authorizes it.

Stop line: if the changed cache path fails, record one observation artifact and stop. Do not repeat blind pulls.

#### Fork B — product-decision move

If Saúl wants customer exposure, create exactly one separate human/operator answer artifact for one prepared question:

1. Retail Reality selected-boundary approval/hold; or
2. Compliance Desk delivery/publication gate with an exact delivery path.

Stop line: if no real human answer exists, do not create an approval record.

#### Fork C — safe pause

If neither a changed cache path nor a human/operator answer is available, stop. Reuse the pickup brief as the coordination entrypoint. Do not add more route layers or handoff wrappers.

## Current safe claims

```text
admin_acontext_image_cache_path_probe_landed
admin_acontext_cache_path_resolution_plan_landed
admin_acontext_digest_pinned_pull_timeout_observation_landed
internal_admin_aas_session_handoff_capsule_landed
internal_admin_aas_session_handoff_pickup_brief_landed
admin_aas_pre_dawn_synthesis_handoff_landed
admin_aas_6am_final_wrap_landed
```

Safe strategic wording:

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

## Ecosystem position after tonight

Execution Market AAS is better positioned as a disciplined evidence product because the runtime work now has a falsifiable next gate instead of open-ended planning. The ecosystem posture is:

- AAS package/customer lanes remain conservative and review-bound.
- Acontext runtime-memory remains high-upside but blocked on image acquisition.
- Coordination artifacts reduce drift across agents/sessions without expanding public claims.
- The next meaningful advance must be either one runtime prerequisite proof or one explicit operator decision.

## Verification for this final wrap

This is a documentation and coordination wrap over already-landed implementation artifacts. Required verification before commit:

```bash
git diff --check
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_session_handoff_pickup_brief.py
```

Full city-ops verification from the preceding implementation remains:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1516 passed
```
