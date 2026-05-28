# City as a Service — System-Integration Flywheel Route Pickup Board

**Date:** 2026-05-28 01:00 America/New_York
**Scope:** Execution Market AAS / City-as-a-Service internal/admin proof ladder
**Status:** Landed as an internal/admin pickup board only

## What landed

`mcp_server/city_ops/aas_system_integration_flywheel_route_pickup_board.py` consumes the midnight route handoff packet and turns it into one deterministic operator pickup board:

- Source handoff: `aas_system_integration_flywheel_route_handoff_packet.json`
- New fixture: `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_system_integration_flywheel_route_pickup_board.json`
- Safe claim: `internal_admin_aas_system_integration_flywheel_route_pickup_board_landed`
- Default next action: `stop_route_expansion_and_wait_for_operator_or_runtime_truth`
- Board verdict: `route_handoff_pickup_ready_default_stop_until_operator_or_runtime_truth`

The board names exactly three forks: default stop, runtime truth, and operator truth. Only default stop is allowed now. Runtime truth remains blocked until Docker/Acontext prerequisites are actually green and a separate live parity attempt is justified. Operator truth remains blocked until a real human/operator answer exists for one exact boundary and delivery path.

## Claim boundary

Safe to claim:

- The internal/admin system-integration route handoff exists.
- The pickup board exists as a deterministic internal/admin coordination artifact.
- Route expansion remains paused by default.
- The next choices are explicit and fail-closed.

Still blocked / not safe to claim:

- Customer copy, customer delivery, publication, public/catalog routes, pricing, quote readiness
- Operator queue launch, dispatch, worker visibility
- ERC-8004 reputation, Worker Skill DNA
- Live Acontext sink readiness or runtime parity
- Payment or production reverification
- Exact GPS/raw metadata/private-context release
- Legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability authority
- Worker-copyable municipal doctrine

## Verification

Focused gate:

```bash
.venv/bin/python -m pytest mcp_server/tests/city_ops/test_aas_system_integration_flywheel_route_pickup_board.py
# 6 passed
```

Full city-ops gate:

```bash
.venv/bin/python -m pytest mcp_server/tests/city_ops
# 1419 passed
```

## Next safe move

Do not add more route layers by default. Pick exactly one:

1. Stop at the route handoff + pickup board; or
2. Prove Docker/Acontext prerequisites first, then attempt exactly one live write/retrieve parity pass; or
3. If Saúl gives a real operator answer, create one separate human/operator decision artifact for one exact customer-exposure boundary.

Do not treat this board as launch readiness.
