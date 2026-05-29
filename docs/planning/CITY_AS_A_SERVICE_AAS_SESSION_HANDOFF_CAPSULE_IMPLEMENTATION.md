# City-as-a-Service — AAS Session Handoff Capsule Implementation

> Date: 2026-05-29 03:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service internal/admin coordination only  
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`

## Priority resolution

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this dream pass. It explicitly allows Execution Market AAS / City-as-a-Service work and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream sessions.

The 03:00 cron payload still contained stale instructions to pull/analyze AutoJob, expand Frontier Academy, and continue KK v2. Those tracks were not pulled, analyzed, edited, expanded, tested, or committed. This implementation stayed inside the active AAS lane.

## What landed

Implemented a deterministic read-only session handoff capsule:

- `mcp_server/city_ops/aas_session_handoff_capsule.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_session_handoff_capsule.json`
- `mcp_server/tests/city_ops/test_aas_session_handoff_capsule.py`

Exported helpers from `mcp_server/city_ops/__init__.py`:

- `build_aas_session_handoff_capsule`
- `load_aas_session_handoff_capsule`
- `write_aas_session_handoff_capsule`

Safe claim:

```text
internal_admin_aas_session_handoff_capsule_landed
```

## Source artifacts consumed

The capsule consumes only existing conservative internal/admin artifacts:

1. `aas_next_truth_selector.json`
   - selected track: `runtime_truth_prerequisite_activation`
   - selected proof: `clear_acontext_sdk_api_dashboard_then_rerun_read_only_preflight`
2. `aas_coordination_observability_success_metrics_board.json`
   - carries the proof anchor, coordination session, compact decision, and review packet IDs
   - measures four-ID handoff completeness, claim-boundary preservation, and one-next-proof discipline

No raw transcripts, unreviewed memory, private operator context, live Acontext writes/retrievals, payment probes, production health probes, GPS/raw metadata payloads, customer copy drafts, or worker templates are consumed.

## Product meaning

This closes a small but important system-integration seam:

```text
next truth selector
+ coordination observability board
-> read-only IRC/session handoff capsule
```

The result is a compact object that future agents or IRC handoffs can carry without replaying a long transcript:

```text
proof_anchor_id: redirect_outdated_packet_001
coordination_session_id: city_session_redirect_outdated_packet_001
compact_decision_id: cdo_c51f4b767729
review_packet_id: review_packet_redirect_outdated_packet_001
```

Then it carries:

- one safe claim;
- source safe claims;
- sticky blocked-claim footer;
- selected next track;
- selected next proof;
- stop condition;
- claim-boundary and four-ID survival metrics.

The implementation turns “legendary coordination” into a reusable handoff shape, not another freeform planning doc.

## What it deliberately does not do

The capsule is explicitly false / blocked for:

```text
runtime_session_manager_mutated
raw_transcript_replay_required
live_acontext_memory_integration_ready
acontext_sink_ready
runtime_parity_proven
one_live_parity_attempt_authorized
more_route_layers_allowed
customer_copy_ready
customer_delivery_ready
publication_ready
public_or_catalog_route_ready
operator_queue_launch_ready
dispatch_ready
pricing_or_customer_quote_ready
erc8004_reputation_ready
worker_skill_dna_ready
payment_coverage_reverified_by_this_capsule
production_infrastructure_reverified_by_this_capsule
gps_or_metadata_exposure_allowed
domain_or_emergency_authority_ready
worker_copyable_doctrine_ready
```

Additional blocked claims include:

```text
session_handoff_capsule_mutates_irc_runtime_session_manager
session_handoff_capsule_reads_or_replays_raw_transcripts
session_handoff_capsule_writes_live_acontext_memory
session_handoff_capsule_retrieves_live_acontext_memory
session_handoff_capsule_proves_memory_acontext_parity
session_handoff_capsule_authorizes_live_parity_attempt
session_handoff_capsule_authorizes_more_route_layers
session_handoff_capsule_authorizes_customer_copy_delivery_or_publication
session_handoff_capsule_authorizes_public_or_catalog_route
session_handoff_capsule_authorizes_operator_queue_launch_or_dispatch
session_handoff_capsule_authorizes_pricing_or_customer_quote
session_handoff_capsule_authorizes_erc8004_reputation_or_worker_skill_dna
session_handoff_capsule_reverifies_payment_or_production
session_handoff_capsule_allows_exact_gps_or_raw_metadata
session_handoff_capsule_grants_domain_or_emergency_authority
session_handoff_capsule_creates_worker_copyable_doctrine
```

## Acceptance tests added

The focused test suite verifies that the capsule:

- matches the persisted fixture exactly;
- preserves the four-ID header;
- preserves the selected runtime-prerequisite next proof;
- stays read-only/internal-admin-only;
- carries safe and blocked claims together;
- keeps success metrics non-customer-visible;
- refuses a selector that promotes route layers or live Acontext readiness;
- refuses a metrics board that promotes live dashboard/customer readiness;
- refuses safe/blocked claim overlap;
- writes/loads temp fixtures deterministically;
- rejects persisted fixture drift.

## Verification

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_session_handoff_capsule.py
# 10 passed

.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_next_truth_selector.py \
  mcp_server/tests/city_ops/test_aas_coordination_observability_success_metrics_board.py \
  mcp_server/tests/city_ops/test_aas_session_handoff_capsule.py
# 28 passed
```

.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1506 passed

`git diff --check` and `py_compile` for `aas_session_handoff_capsule.py` were clean.

## Next safe move

Use the capsule as the first reusable handoff line for future AAS IRC/session coordination. It should reduce transcript replay and prevent claim promotion.

For runtime truth, continue the already-selected Acontext prerequisite lane separately:

1. resolve the trusted image/cache path;
2. rerun image inventory;
3. start local services only after required images are present;
4. verify API/dashboard health;
5. rebuild the read-only preflight gate;
6. attempt exactly one bounded live write/retrieve parity pass only if the gate is empty and explicitly authorizes it.

If runtime prerequisites remain blocked and no human/operator decision exists, stop and carry this capsule forward. Do not add more route layers.
