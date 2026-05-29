# City-as-a-Service — AAS Session Handoff Pickup Brief Implementation

> Date: 2026-05-29 04:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal/admin coordination only
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`

## Priority resolution

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this 4 AM dream pass. It explicitly allows Execution Market AAS / City-as-a-Service work and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream sessions.

The cron payload still contained stale instructions to pull/analyze AutoJob, expand Frontier Academy, and continue KK v2. Those tracks were not pulled, analyzed, edited, expanded, tested, or committed. This work stayed inside the active AAS lane.

## What landed

Implemented a deterministic read-only pickup brief over the 03:00 session handoff capsule:

- `mcp_server/city_ops/aas_session_handoff_pickup_brief.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_session_handoff_pickup_brief.json`
- `mcp_server/tests/city_ops/test_aas_session_handoff_pickup_brief.py`

Exported helpers from `mcp_server/city_ops/__init__.py`:

- `build_aas_session_handoff_pickup_brief`
- `load_aas_session_handoff_pickup_brief`
- `write_aas_session_handoff_pickup_brief`

Safe claim:

```text
internal_admin_aas_session_handoff_pickup_brief_landed
```

## Source artifact consumed

The brief consumes only:

- `aas_session_handoff_capsule.json`

It does not read raw transcripts, unreviewed memory, private operator context, live Acontext sinks, customer copy drafts, route preflight outputs, dispatch queues, payment probes, production health probes, ERC-8004 reputation artifacts, Worker Skill DNA, exact GPS/raw metadata payloads, or worker-instruction templates.

## Why this is the 4 AM connection artifact

The 4 AM prompt asked for pattern recognition:

- what patterns emerge from memory system data;
- how IRC coordination insights inform broader strategy;
- which cross-project intelligence flows create multiplier effects;
- which agent coordination patterns scale best.

The pickup brief answers those questions without reopening stopped projects or promoting launch claims.

It turns the capsule into a copyable first-handoff block plus four conservative pattern cards:

1. **Memory system data compounds only after review**
   Reviewed AAS artifacts become useful when carried as compact IDs and claim boundaries, not as raw transcript replay.

2. **IRC coordination scales with four IDs**
   `proof_anchor_id`, `coordination_session_id`, `compact_decision_id`, and `review_packet_id` are the smallest durable state that later agents can resume from.

3. **Cross-project intelligence is a filter, not autopilot**
   Adjacent/stopped project signals may inform AAS boundaries, but they do not reopen AutoJob, Frontier Academy, KK v2, or customer routes during dream sessions.

4. **Agent coordination quality is boundary survival**
   The best scaling metric is whether agents preserve safe claims, blocked claims, and exactly one next proof — not how many artifacts they add.

## Product meaning

The new artifact makes the next pickup safer and shorter:

```text
session handoff capsule
-> pickup brief
-> first message template
-> selected runtime-prerequisite proof
-> stop if Acontext prerequisites/gate remain blocked
```

This is not another route layer. It is a read-only consumer of the capsule that prepares the exact text/state a later agent should carry into IRC or a new AAS handoff.

## First message template

The persisted fixture renders a first handoff block with:

```text
proof_anchor_id: redirect_outdated_packet_001
coordination_session_id: city_session_redirect_outdated_packet_001
compact_decision_id: cdo_c51f4b767729
review_packet_id: review_packet_redirect_outdated_packet_001
safe_claim: internal_admin_aas_session_handoff_pickup_brief_landed
selected_next_track: runtime_truth_prerequisite_activation
selected_next_proof: clear_acontext_sdk_api_dashboard_then_rerun_read_only_preflight
stop_condition: stop if Acontext prerequisites remain blocked or the gate is non-empty
```

## What it deliberately does not do

The pickup brief is explicitly false / blocked for:

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
payment_coverage_reverified_by_this_brief
production_infrastructure_reverified_by_this_brief
gps_or_metadata_exposure_allowed
domain_or_emergency_authority_ready
worker_copyable_doctrine_ready
```

Additional blocked claims include:

```text
pickup_brief_mutates_irc_runtime_session_manager
pickup_brief_reads_or_replays_raw_transcripts
pickup_brief_writes_live_acontext_memory
pickup_brief_retrieves_live_acontext_memory
pickup_brief_proves_memory_acontext_parity
pickup_brief_authorizes_live_parity_attempt
pickup_brief_authorizes_more_route_layers
pickup_brief_authorizes_customer_copy_delivery_or_publication
pickup_brief_authorizes_public_or_catalog_route
pickup_brief_authorizes_operator_queue_launch_or_dispatch
pickup_brief_authorizes_pricing_or_customer_quote
pickup_brief_authorizes_erc8004_reputation_or_worker_skill_dna
pickup_brief_reverifies_payment_or_production
pickup_brief_allows_exact_gps_or_raw_metadata
pickup_brief_grants_domain_or_emergency_authority
pickup_brief_creates_worker_copyable_doctrine
```

## Acceptance tests added

The focused test suite verifies that the brief:

- matches the persisted fixture exactly;
- preserves the four-ID header and selected next proof;
- maps the 4 AM pattern-recognition prompt without customer/runtime/reputation promotion;
- stays read-only/internal-admin-only;
- carries safe and blocked claims together;
- refuses a capsule that promotes runtime parity;
- refuses a capsule that authorizes a live parity attempt now;
- refuses safe/blocked claim overlap;
- writes/loads temp fixtures deterministically;
- rejects persisted fixture drift.

## Verification

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_session_handoff_pickup_brief.py
# 10 passed

.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_session_handoff_capsule.py \
  mcp_server/tests/city_ops/test_aas_session_handoff_pickup_brief.py
# 20 passed
```

Full city-ops verification after the pickup brief landed:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1516 passed
```

`py_compile` for `aas_session_handoff_pickup_brief.py` was clean.

## Next safe move

Use the pickup brief as the first handoff block for the next AAS agent/IRC coordination pass.

For runtime truth, continue the separate Acontext prerequisite lane:

1. change the trusted image/cache path;
2. rerun image inventory;
3. start local services only after required images are present;
4. verify API/dashboard health;
5. rebuild the read-only preflight gate;
6. attempt exactly one bounded live parity pass only if the gate is empty and explicitly authorizes it.

If runtime prerequisites remain blocked and no human/operator decision exists, stop and carry this pickup brief forward. Do not add more route layers.
