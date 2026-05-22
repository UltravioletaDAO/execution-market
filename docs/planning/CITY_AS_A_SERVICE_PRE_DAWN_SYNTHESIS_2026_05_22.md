# City-as-a-Service — Pre-Dawn Synthesis (2026-05-22)

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled the session. It explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dreams.

The stale cron payload requested AutoJob pull/analysis, Frontier Academy expansion, and KK v2 work. Those tracks were not pulled, analyzed, edited, or expanded. Work stayed inside Execution Market AAS / City-as-a-Service.

## Night pattern

Tonight converted the May 21 claim-control plane into a stronger **operator learning loop**.

The progression was deliberately narrow:

```text
claim quarantine read surface
→ authenticated internal/admin route mount
→ route + prevented-claim panel handoff packet
→ prevented-claim trend summary
→ prevented-claim trend read surface
→ pre-dawn synthesis / daytime handoff
```

The important product shift is that AAS now treats prevented overclaims as useful operational data. The system is no longer only saying “not yet.” It now records which launch/customer/runtime/payment/reputation/location/domain-authority claims were stopped, why they were stopped, and what exact proof slot would be required before any of them can advance.

No part of that chain creates customer copy, delivery authorization, publication readiness, public routes, pricing, queue launch, dispatch, reputation, worker Skill DNA, runtime parity, payment/production reverification, exact GPS/raw metadata release, domain-authority claims, or worker-copyable doctrine.

## What connected tonight

### 1. Quarantine became an internal/admin route, but not a public surface

The AAS claim quarantine read surface now has a real internal/admin route:

```text
GET /internal/admin/city-ops/aas-claim-quarantine
```

The route requires the internal admin auth boundary and returns the persisted quarantine read surface as-is. This creates a usable operator inspection path while preserving the key boundary:

```text
internal/admin read access != customer copy
internal/admin route != public route
operator inspection != delivery authorization
```

### 2. Route state and prevented-claim state became one pickup artifact

The route+panel handoff packet connects the mounted quarantine route with the prevented-claim panel. It records source digests and keeps `safe_to_claim[]` beside `do_not_claim_yet[]`.

This makes the next operator context compact: a daytime reviewer can inspect one packet and understand both what is mounted and which tempting claims are still blocked.

### 3. Prevented claims became trendable product intelligence

The prevented-claim trend summary ranks five blocked-claim buckets and attaches exact next-proof requirements to each one. That means the product can now learn from restraint:

- customer/public claims blocked → need explicit human delivery-path approval;
- pricing/queue claims blocked → need quote/pricing/queue artifacts;
- dispatch/reputation/worker Skill DNA claims blocked → need dispatch and reputation proof chains;
- runtime/payment claims blocked → need live Acontext/runtime/payment reverification;
- GPS/domain-authority claims blocked → need separate privacy/domain-authority approval gates.

This turns overclaim prevention into roadmap ordering, not just compliance friction.

### 4. The trend read surface connected tonight’s discoveries to existing systems

The final read surface added five durable connection edges:

```text
memory patterns → reviewed proof slots, not immediate claims
IRC coordination → state cards/source digests, not raw transcript authority
cross-project intelligence → priority firewall, not scope drift
agent metrics → restraint/reputation candidate, not launch pressure
claim quarantine → product sequencing, not readiness
```

This is the strongest synthesis from the night: Execution Market AAS should compound by converting lessons into reviewed proof slots and source digests, not by letting more context mutate live claims.

## Current safe claims from tonight

```text
internal_admin_aas_claim_quarantine_route_mount_smoke_landed
internal_admin_aas_claim_quarantine_route_panel_handoff_packet_landed
internal_admin_aas_claim_quarantine_prevented_claim_trend_summary_landed
internal_admin_aas_claim_quarantine_prevented_claim_trend_read_surface_landed
```

These claims are internal/admin-only.

## Still blocked

Do not infer any of the following from tonight's work:

```text
customer_copy_ready
customer_delivery_approved
publication_approved
public_catalog_ready
public_route_ready
controlled_pilot_ready
public_pricing_or_customer_quote_ready
operator_queue_launch_ready
autonomous_dispatch_ready
erc8004_reputation_ready
worker_skill_dna_ready
live_acontext_runtime_parity
acontext_sink_ready
payment_or_production_reverified
exact_gps_or_raw_metadata_release_allowed
raw_transcript_authority
domain_or_legal_or_regulator_or_notarial_or_custody_authority
emergency_or_safety_or_repair_or_insurance_or_sla_or_official_report_or_fault_liability_authority
worker_copyable_aas_doctrine
```

## Daytime recommendations

### 1. Best product move if an operator surface is needed

Create a fail-closed route preflight or mount manifest for:

```text
mcp_server/city_ops/fixtures/aas_package_ladder/aas_claim_quarantine_prevented_claim_trend_read_surface.json
```

It should prove:

- internal/admin access only;
- source fixture digest parity;
- pass-through response semantics;
- no public/customer/worker route registration;
- safe and blocked claims remain adjacent;
- all launch/readiness/authority flags stay false.

Do not mount it just because it exists. Mount only if a real operator read need exists.

### 2. Best customer-exposure move, only if explicitly desired

Create a separate human-operator selected-boundary approval record for exactly one customer-exposure path. It must name:

- exact approved text;
- redactions passed;
- authorized delivery path;
- still-blocked claims;
- whether publication/customer delivery is actually authorized.

Do not infer this from the existing Compliance Desk approval record, because delivery remains separately blocked.

### 3. Best runtime-memory move

Acontext remains blocked until prerequisites are real. The next proof is still:

```text
clear Docker/image/cache or trusted mirror prerequisites
→ compose startup
→ localhost API/dashboard reachable
→ rebuilt empty readiness gate
→ exactly one live write/retrieve parity pass
```

No live Acontext/runtime parity claim is safe before that chain succeeds.

### 4. Best strategic posture

Stop broadening AAS families by default. The portfolio already has enough concept surface. The highest leverage now is proof-sequencing discipline: selected-boundary approvals, route preflights, runtime parity gates, and prevented-claim trend loops.

## Morning handoff

Daytime should treat May 22 as a choice between three narrow moves:

1. **Operator learning:** route preflight/mount manifest for the prevented-claim trend read surface, only if there is a real internal/admin read need.
2. **Customer exposure:** one explicit human selected-boundary approval/delivery artifact; no publication by inference.
3. **Runtime parity:** repair Acontext prerequisites before any live write/retrieve attempt.

AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 remain stopped for dream work by `DREAM-PRIORITIES.md`.
