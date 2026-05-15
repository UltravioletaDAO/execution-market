# City as a Service — AAS System Integration Flywheel Read Surface Implementation

> Created: 2026-05-15 04:00 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin read surface landed; no route, no customer surface, no live Acontext, no dispatch, no payment/infra reverification

## 1. Why this slice exists

The 03:00 system-integration flywheel connected the current night-work pattern:

- reviewed memory should become bounded Acontext retrieval candidates, not raw transcript replay;
- IRC/session coordination scales best through invariant IDs;
- cross-project decision support works only when safe and blocked claims travel together;
- observability should measure boundary preservation, not just activity volume;
- payment/infrastructure confidence can inform packaging context without being re-claimed by a planning artifact.

This 04:00 slice turns that flywheel into a deterministic internal/admin read surface so an operator or future agent can inspect the connections without reading the full proof bundle.

## 2. New files

```text
mcp_server/city_ops/aas_system_integration_flywheel_read_surface.py
mcp_server/tests/city_ops/test_aas_system_integration_flywheel_read_surface.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_system_integration_flywheel_read_surface.json
docs/planning/CITY_AS_A_SERVICE_AAS_SYSTEM_INTEGRATION_FLYWHEEL_READ_SURFACE_IMPLEMENTATION.md
```

`mcp_server/city_ops/__init__.py` now exports:

```python
build_aas_system_integration_flywheel_read_surface
load_aas_system_integration_flywheel_read_surface
write_aas_system_integration_flywheel_read_surface
```

## 3. Schema and safe claim

```text
city_ops.aas_system_integration_flywheel_read_surface.v1
```

Safe claim added:

```text
admin_system_integration_flywheel_surface_landed
```

This claim means only that a persisted internal/admin read surface exists over the flywheel.

## 4. Source contract

The surface consumes only:

```text
aas_system_integration_flywheel.json
```

It refuses sources that:

- promote live Acontext sink readiness;
- prove runtime parity;
- enable autonomous dispatch;
- promote customer-visible packaging;
- reverify payment coverage;
- reverify production infrastructure;
- soften blocked claims;
- require raw transcript replay.

## 5. What the surface renders

The payload is deliberately card-shaped and pass-through:

1. `four_id_session_header` — `proof_anchor_id`, `coordination_session_id`, `compact_decision_id`, and `review_packet_id`.
2. `strength_cards` — every strength has a `verification_badge`; declared strengths cannot be repeated as freshly reverified.
3. `connection_loop_cards` — memory/Acontext, IRC, decision support, observability, and payment-confidence loops.
4. `success_metric_cards` — axis coverage, ready/blocked split, declared-strength count, claim-boundary preservation, and future-agent success definition.
5. `session_management_cards` — four-ID headers, declared-vs-verified badges, sticky blocked-claim footer, and single next-proof slot.
6. `operator_next_action_cards` — live Acontext parity probe, admin flywheel surface, separate payment/infra probe, and matrix recommendation preservation.
7. `claim_boundary_footer` — sticky `safe_to_claim[]` beside `do_not_claim_yet[]`.

## 6. Readiness posture

The surface keeps all of these false:

```text
surface_promotes_live_readiness=false
acontext_sink_ready=false
runtime_parity_proven=false
autonomous_dispatch_ready=false
customer_visible_packaging_ready=false
public_route_ready=false
payment_coverage_reverified_by_this_surface=false
production_infrastructure_reverified_by_this_surface=false
operator_queue_launch_ready=false
erc8004_reputation_ready=false
worker_skill_dna_ready=false
worker_copyable_doctrine_ready=false
gps_or_metadata_exposure_allowed=false
```

It also registers no network route. The suggested path is only a future internal/admin path:

```text
/internal/admin/city-ops/aas-system-integration-flywheel
```

## 7. Pattern insight captured

The scalable agent coordination pattern is now explicit:

```text
invariant IDs + declared-vs-verified badges + sticky blocked claims + one next-proof slot
```

That is the multiplier. It lets future agents continue from compact reviewed state instead of reopening raw transcripts, repeating stale confidence claims, or broadening product readiness accidentally.

## 8. Test coverage

Targeted coverage verifies:

- fixture equality;
- four-ID header parity with source flywheel;
- strength cards preserve declared-vs-verified badges;
- connection loop cards preserve all required axes;
- sticky claim footer carries safe and blocked claims together;
- promoted Acontext readiness is rejected;
- payment-reverification drift is rejected;
- blocked safe claims are rejected;
- route-registration drift is rejected by the loader;
- temp write/load roundtrip.

Verification command:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_aas_system_integration_flywheel.py \
  mcp_server/tests/city_ops/test_aas_system_integration_flywheel_read_surface.py
```

Result during implementation:

```text
19 passed
```

## 9. Next safe step

Do not broaden into customer/public/package launch from this surface.

The next product-significant proof remains one of:

1. clear the real Acontext prerequisites and run exactly one live write/retrieve parity pass; or
2. if Acontext remains blocked, add only narrow internal/admin pass-through surfaces or guardrails that preserve invariant IDs, declared-vs-verified badges, sticky blocked claims, and one next-proof slot.
