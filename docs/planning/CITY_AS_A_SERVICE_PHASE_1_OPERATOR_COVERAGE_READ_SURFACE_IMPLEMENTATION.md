# City as a Service — Phase 1 Operator Coverage Read Surface Implementation

> Status: landed internal/admin-only read surface contract
> Date: 2026-05-09 02:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only

## What landed

Mounted the persisted Phase 1 operator coverage renderer behind a conservative internal/admin-only read surface contract.

New code:

- `mcp_server/city_ops/phase1_operator_coverage_read_surface.py`
  - `build_phase1_operator_coverage_read_surface()`
  - `write_phase1_operator_coverage_read_surface()`
  - `load_phase1_operator_coverage_read_surface()`
  - `PHASE1_OPERATOR_COVERAGE_READ_SURFACE_SAFE_CLAIM`
  - `PHASE1_OPERATOR_COVERAGE_READ_SURFACE_FILENAME`
- `mcp_server/city_ops/__init__.py`
  - exports the read-surface builder/writer/loader
- `mcp_server/tests/city_ops/test_phase1_operator_coverage_read_surface.py`
  - proves the surface consumes only `phase1_operator_coverage_renderer.json`
  - proves the renderer payload is preserved as-is
  - proves persisted output matches generated output
  - proves safe and blocked claim cards remain visible without softening
  - proves product/external claims remain blocked
  - proves promoted renderer readiness is rejected
  - proves public-route drift is rejected on load
  - proves temp-dir write/load behavior

New persisted artifact:

- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_operator_coverage_read_surface.json`

## What this surface consumes

The surface consumes exactly one artifact by default:

- `phase1_operator_coverage_renderer.json`

It explicitly refuses to depend on:

- raw transcripts
- raw review fixtures
- unreviewed memory
- freeform worker chat
- private operator context
- live Acontext transport
- GPS or metadata payloads

## What this surface exposes

The surface is data-only and internal/admin-only. It exposes the renderer payload without reinterpretation:

- `coverage_totals`
- `coverage_table`
- `display_lines`
- `claim_boundaries`
- `readiness`
- cards for safe claims, blocked claims, coverage totals, and Phase 1 offer rows

The suggested internal path is documented as a mount contract only:

- `GET /internal/admin/city-ops/phase1/operator-coverage`

No public route is registered by this slice.

## Safe to claim

- `phase1_operator_coverage_read_surface_landed`
- the persisted renderer payload now has an internal/admin-only read-surface contract
- the surface preserves renderer `coverage_totals`, `coverage_table`, and `display_lines` as-is
- the surface keeps `safe_to_claim[]` and `do_not_claim_yet[]` visible together
- the surface rejects promoted readiness and public-route drift

## Still blocked / not safe to claim

- public route readiness
- customer-visible catalog readiness
- customer copy readiness
- polished operator console readiness
- operator UI readiness beyond a generated/read-only payload contract
- worker instruction surface readiness
- dispatch routing or dispatch automation readiness
- live Acontext readiness / Acontext sink readiness
- runtime parity
- ERC-8004 reputation readiness
- worker Skill DNA readiness
- legal sufficiency or regulator acceptance
- exact GPS/metadata exposure
- worker-copyable municipal doctrine

## Verification

```bash
python3 -m py_compile mcp_server/city_ops/phase1_operator_coverage_read_surface.py mcp_server/tests/city_ops/test_phase1_operator_coverage_read_surface.py
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Result:

- `169 passed, 1 existing warning`

## Next smallest safe step

Wire this contract to a real authenticated internal/admin route only after an admin auth boundary exists.

That route must continue to use the persisted payload as-is and must not add:

- customer copy
- public catalog language
- dispatch routing
- live Acontext writes
- ERC-8004 reputation updates
- worker Skill DNA
- legal/regulator claims
- GPS/metadata exposure
- worker-copyable municipal doctrine
