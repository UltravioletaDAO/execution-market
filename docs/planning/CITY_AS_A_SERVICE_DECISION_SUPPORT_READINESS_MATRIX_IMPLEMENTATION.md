# City as a Service — Decision Support Readiness Matrix Implementation

> Last updated: 2026-05-09
> Parent docs:
> - `MASTER_PLAN_CITY_AS_A_SERVICE.md`
> - `CITY_AS_A_SERVICE_DECISION_SUPPORT_CONTROL_PLANE.md`
> - `CITY_AS_A_SERVICE_Acontext_MEMORY_BRIDGE.md`
> - `CITY_AS_A_SERVICE_OBSERVABILITY_AND_SUCCESS_METRICS.md`
> - `CITY_AS_A_SERVICE_COORDINATION_INTELLIGENCE_IMPLEMENTATION.md`
> Status: implemented conservative proof slice

## Why this slice exists

The current City-as-a-Service stack already has compact proof artifacts, local Acontext transport planning, coordination intelligence, and proof observability.
The missing nighttime seam was a small artifact that lets a future operator or agent answer:

> Which system-integration surfaces are safe to use now, which are only attemptable, and which must remain blocked?

The new decision-support readiness matrix provides that seam without broadening product claims.
It is intentionally read-only and derives from the existing `coordination_intelligence_snapshot.json` fixture.

## What landed

Code:

- `mcp_server/city_ops/decision_support_readiness_matrix.py`
  - `build_decision_support_readiness_matrix()`
  - `write_decision_support_readiness_matrix_fixture()`
  - `load_decision_support_readiness_matrix()`
  - schema: `city_ops.decision_support_readiness_matrix.v1`
  - safe claim: `decision_support_readiness_matrix_landed`

Tests:

- `mcp_server/tests/city_ops/test_decision_support_readiness_matrix.py`
  - generated matrix matches the persisted fixture
  - matrix names the four system-integration axes
  - live Acontext can become attemptable without becoming ready
  - blocked claims cannot move into safe claims
  - worker-copyable doctrine cannot be promoted
  - raw conversation replay cannot be reopened
  - persisted fixture loader rejects readiness promotion

Fixture:

- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/decision_support_readiness_matrix.json`

Exports:

- `mcp_server/city_ops/__init__.py`

## Matrix axes

The persisted matrix has four axes:

1. `memory_system_to_acontext_bridge`
   - current state: blocked until live Acontext write/retrieve parity is proven
   - safe use: operator planning from reviewed compact artifacts only
2. `irc_session_management`
   - current state: compact ID handoff active
   - safe use: hand off by invariant IDs instead of raw chat replay
3. `cross_project_decision_support`
   - current state: bounded verdict reusable for operator-only EM AAS planning
   - safe use: move safe/blocked verdicts and next-proof rules across planning surfaces
4. `agent_observability_success_metrics`
   - current state: proof-block metrics landed
   - safe use: track whether future agents preserve claim boundaries and reuse IDs

## Safe to claim

- `decision_support_readiness_matrix_landed`
- one read-only matrix now joins memory/Acontext planning, IRC-style handoff discipline, cross-project decision support, and agent observability metrics
- three of four axes are safe for conservative internal use
- the Acontext axis remains blocked/attemptable only; it does not become sink-ready
- future agents can consume invariant IDs and safe/blocked claims without opening raw transcripts

## Still blocked / not safe to claim

- `session_rebuild_ready`
- `acontext_sink_ready`
- `runtime_parity_proven`
- `acontext_live_write_completed`
- `acontext_live_retrieval_completed`
- `acontext_live_transport_parity_landed`
- autonomous city dispatch readiness
- polished review console readiness
- office memory view readiness
- broad operator workflow readiness
- customer-visible catalog readiness
- public route readiness
- worker Skill DNA readiness
- worker-copyable municipal doctrine

## Why this matters for the AAS product

This turns the latest coordination work into a reusable product primitive:

- memory is treated as reviewed dispatch capital, not raw transcript storage
- IRC/session management gets an explicit invariant-ID handoff rule
- cross-project decision support can reuse bounded verdicts without leaking raw context
- observability has a small success definition for future agents: preserve IDs, keep safe/blocked claims adjacent, recommend the next proof, and avoid readiness promotion

## Next smallest safe step

Use this matrix as the read-only input for a morning/daytime build card:

1. render the four axes in an internal operator/admin-only surface
2. keep `safe_to_claim[]` and `do_not_claim_yet[]` visible together
3. keep the Acontext axis blocked until one live local write/retrieve parity pass exists
4. add a second reviewed municipal case before promoting cross-case doctrine

Do not connect this matrix to customer copy, public routes, broad dispatch automation, live Acontext sink writes, worker Skill DNA, ERC-8004 reputation claims, or worker-copyable municipal doctrine yet.
