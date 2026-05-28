# City as a Service — System-Integration Runtime Truth Queue

**Date:** 2026-05-28 03:00 America/New_York
**Scope:** Execution Market AAS / City-as-a-Service internal/admin proof ladder
**Status:** Landed as a planning queue only; no live runtime attempt

## What landed

`mcp_server/city_ops/aas_system_integration_runtime_truth_queue.py` consumes two existing internal/admin artifacts:

- `aas_system_integration_flywheel_route_regret_panel.json`
- `acontext_runtime_memory_daemon_recheck.json`

It persists a new fixture at:

- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_system_integration_runtime_truth_queue.json`

Safe claim:

- `internal_admin_aas_system_integration_runtime_truth_queue_landed`

Verdict:

- `runtime_truth_queue_ready_but_live_parity_blocked_by_daemon_prerequisites`

The queue converts the route-regret conclusion into the next truth-producing path: stop adding route layers, then prove runtime prerequisites in order before any Memory ↔ Acontext parity claim.

## Runtime gate order

The queue names five gates, all currently blocked / not authorized:

1. Docker daemon/socket available and Buildx healthy
2. Required Acontext image inventory checked and present
3. Local Acontext API/dashboard reachable after Compose startup
4. Empty readiness gate rebuilt
5. Exactly one live write/retrieve parity attempt authorized

None of these gates are marked passed. The artifact does not start Docker Desktop, pull images, start Compose, write to Acontext, retrieve from Acontext, or authorize the parity attempt.

## System-integration connections captured

The queue preserves four connection cards without promoting them to runtime changes:

- **Memory system ↔ Acontext:** plan the gate order only; no parity claim until live write + retrieval exist.
- **IRC session management:** carry four-ID handoff discipline as a design input; no runtime manager change.
- **Cross-project decision support:** use the DREAM priority firewall as a decision-support signal; no stopped-project work.
- **Agent observability and success metrics:** measure restraint, gate order, and blocked-claim adjacency before any reputation or public claim.

## Claim boundary

Still blocked / not safe to claim:

- Docker/socket repair, image pull/cache, Compose startup, local API/dashboard reachability
- Empty readiness gate rebuild or live write/retrieve authorization
- Memory ↔ Acontext parity
- IRC runtime session-manager changes
- Cross-project autorouting
- Customer copy, delivery, publication, public/catalog routes, pricing/quotes
- Queue launch, dispatch, ERC-8004 reputation, Worker Skill DNA
- Payment or production reverification
- Exact GPS/raw metadata/private-context release
- Legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability authority
- Worker-copyable municipal doctrine

## Verification

Focused gate:

```bash
.venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_system_integration_flywheel_route_regret_panel.py \
  mcp_server/tests/city_ops/test_acontext_runtime_memory_daemon_recheck.py \
  mcp_server/tests/city_ops/test_aas_system_integration_runtime_truth_queue.py
# 24 passed
```

Full city-ops gate:

```bash
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1433 passed
```

## Next safe move

Do not add more route layers. The next productive move is a real runtime prerequisite observation after Docker is available, or a separate human/operator decision record if Saúl gives an explicit customer-exposure answer. Until then, this queue is the safe internal/admin pickup point.
