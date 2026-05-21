# City as a Service — AAS Strength Connection Control Packet Implementation

> Created: 2026-05-21 03:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only
> Status: internal/admin control packet landed; no live Acontext, no IRC runtime mutation, no customer/public surface, no dispatch, no payment/infra reverification, no ERC-8004 reputation, no GPS/raw metadata exposure, no worker-copyable doctrine

## 1. Why this slice exists

The stale 03:00 cron payload still named stopped tracks, but `~/clawd/DREAM-PRIORITIES.md` explicitly blocks AutoJob, Frontier Academy, and KK v2. This slice stays strictly inside Execution Market AAS / City-as-a-Service and turns the current system-integration strengths into one bounded control packet.

The packet connects the active strengths without inflating them into unproven launch claims:

- latest landed `city_ops` code and fixture graph;
- 8/8 chain payment confidence as declared context only;
- intelligent memory / reviewed insight work as Acontext candidate structure, not a live sink;
- production infrastructure confidence as declared context only;
- agent coordination excellence as a consumed internal metrics/read-surface signal.

The output is an internal/admin handoff object future agents can read before choosing work. It preserves the pattern that has been working: invariant IDs, declared-vs-verified badges, sticky blocked claims, and exactly one next-proof slot.

## 2. New files

```text
mcp_server/city_ops/aas_strength_connection_control_packet.py
mcp_server/tests/city_ops/test_aas_strength_connection_control_packet.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_strength_connection_control_packet.json
docs/planning/CITY_AS_A_SERVICE_AAS_STRENGTH_CONNECTION_CONTROL_PACKET_IMPLEMENTATION.md
```

`mcp_server/city_ops/__init__.py` now exports:

```python
build_aas_strength_connection_control_packet
load_aas_strength_connection_control_packet
write_aas_strength_connection_control_packet
```

## 3. Schema and safe claim

```text
city_ops.aas_strength_connection_control_packet.v1
```

Safe claim added:

```text
admin_aas_strength_connection_control_packet_landed
```

This claim means only that a deterministic internal/admin packet exists over already-reviewed local artifacts.

## 4. Source contract

The packet consumes only:

```text
aas_coordination_observability_success_metrics_read_surface.json
aas_intelligence_flow_compounder.json
```

It refuses sources that:

- promote live Acontext or runtime parity;
- change IRC/session-management runtime;
- enable autonomous routing, dispatch, or an operator queue;
- publish customer/public surfaces;
- emit reputation receipts or worker Skill DNA;
- revalidate payment coverage or production health;
- expose GPS/raw metadata;
- publish worker-copyable doctrine;
- split safe claims away from blocked claims;
- mismatch the four invariant IDs.

## 5. What the packet renders

The packet is intentionally small and handoff-shaped:

1. `handoff_header` — `proof_anchor_id`, `coordination_session_id`, `compact_decision_id`, and `review_packet_id` plus the rule to include them before recommendations.
2. `strength_connection_cards` — five current-strength cards with verification badges and explicit `reverified_by_this_packet=false`.
3. `integration_lane_cards` — memory/Acontext, IRC session management, cross-project decision support, and agent observability lanes with authorizations kept false.
4. `control_plane_action_cards` — three internal actions for future agents: start from the packet, convert strengths into gates/quarantines, and use coordination quality as internal selection signal only.
5. `one_next_proof_queue` — exactly one next proof: Acontext runtime-memory prerequisites followed by a single live parity attempt only after prerequisites clear.
6. `claim_boundaries` — sticky safe and blocked claims carried together.

## 6. Readiness posture

The packet keeps these false:

```text
packet_promotes_live_readiness=false
live_acontext_memory_integration_ready=false
acontext_sink_ready=false
runtime_parity_proven=false
irc_runtime_coordination_ready=false
irc_session_manager_runtime_enhanced=false
cross_project_autorouting_ready=false
autonomous_prioritization_ready=false
agent_observability_live_dashboard_ready=false
customer_visible_packaging_ready=false
public_route_ready=false
operator_queue_launch_ready=false
dispatch_ready=false
autonomous_dispatch_ready=false
erc8004_reputation_ready=false
agent_success_score_reputation_ready=false
worker_skill_dna_ready=false
pricing_or_customer_quote_ready=false
payment_coverage_reverified_by_this_packet=false
production_infrastructure_reverified_by_this_packet=false
gps_or_metadata_exposure_allowed=false
worker_copyable_doctrine_ready=false
```

## 7. Practical planning impact

This packet makes the next daytime/nighttime choice clearer:

- If Acontext prerequisites can be cleared, the next proof is a single write/retrieve parity attempt.
- If Acontext remains blocked, future agents should add only internal/admin guardrails that preserve four IDs, claim boundaries, and one next-proof discipline.
- Payment and production confidence remain useful context, but must not be repeated as current proof until a separate probe revalidates them.
- Coordination quality can guide internal agent selection, but it is not ERC-8004 reputation, not public scoring, and not worker Skill DNA.

## 8. Test coverage

Targeted coverage verifies:

- fixture equality;
- all five current strengths are represented;
- declared payment/infrastructure strengths are not revalidated by the packet;
- all integration lanes keep runtime/customer/reputation authorizations false;
- exactly one next-proof slot is preserved;
- sticky blocked claims include payment, production, live Acontext, dispatch, GPS/raw metadata, and worker-doctrine blocks;
- source invariant-ID mismatches are rejected;
- promoted metrics/read-surface readiness is rejected;
- promoted intelligence-flow authorization is rejected;
- temp write/load roundtrip;
- loader drift rejection.

Verification command:

```bash
PYTHONPATH=. python3 -m pytest -q \
  mcp_server/tests/city_ops/test_aas_strength_connection_control_packet.py
```

Result during implementation:

```text
10 passed
```
