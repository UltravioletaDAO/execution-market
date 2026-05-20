# City-as-a-Service — Coordination Metrics Read Surface Implementation

Date: 2026-05-20 04:00 America/New_York
Status: landed as internal/admin-only proof artifact

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this dream session. The stale cron payload requested AutoJob, Frontier Academy, and KK v2 work, but the active priority file explicitly stops those tracks. This implementation stays inside Execution Market AAS / City-as-a-Service.

## What landed

Added a deterministic read-only internal/admin surface over the existing AAS coordination observability success-metrics board:

- `mcp_server/city_ops/aas_coordination_observability_success_metrics_read_surface.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_coordination_observability_success_metrics_read_surface.json`
- `mcp_server/tests/city_ops/test_aas_coordination_observability_success_metrics_read_surface.py`
- exports in `mcp_server/city_ops/__init__.py`

Safe claim added:

```text
admin_aas_coordination_observability_success_metrics_read_surface_landed
```

## Product meaning

The surface turns the prior metrics board into a bounded operator payload with:

- a four-ID handoff header;
- read-only integration-track cards for memory/Acontext, IRC/session management, cross-project decision support, observability, and payment/infra context;
- success metric cards for claim-boundary integrity, invariant-ID handoff, Acontext prerequisite honesty, and one-next-proof discipline;
- agent-success rubric cards that future agents can be scored against;
- sticky safe and blocked claim boundaries.

The key connection: agent coordination scales best when handoffs are made by stable reviewed IDs plus declared-vs-verified status, not by reopening raw transcripts or promoting old claims. IRC coordination insights become useful only when they are compacted into invariant IDs, conservative state cards, and a single next-proof slot.

## Still blocked

This read surface does **not** authorize or prove any of the following:

```text
live_acontext_memory_integration
runtime_parity
irc_runtime_or_session_manager_changes
customer_visible_success_metrics_dashboard
customer_copy_or_customer_delivery
public_or_catalog_routes
pricing_or_customer_quotes
operator_queue_launch
autonomous_dispatch
erc8004_reputation
worker_skill_dna
payment_or_production_reverification
exact_gps_or_raw_metadata_exposure
raw_transcript_authority
worker_copyable_aas_doctrine
```

## Verification

- Focused coordination metrics read-surface + board tests: `20 passed`
- Full city-ops suite: `1018 passed`.

## Next safe step

If runtime prerequisites become real, rerun the read-only Acontext preflight and attempt exactly one live write/retrieve parity pass only behind an empty rebuilt gate. If runtime remains blocked, keep adding only narrow internal/admin proof surfaces that preserve invariant IDs, sticky blocked claims, and one-next-proof discipline.
