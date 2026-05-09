# City as a Service — Phase 1 Operator Coverage Renderer Implementation

> Status: landed local read-only renderer
> Date: 2026-05-09 01:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service only

## What landed

Added a thin internal read-only renderer for the persisted Phase 1 operator coverage summary.

New code:

- `mcp_server/city_ops/phase1_operator_coverage_renderer.py`
  - `build_phase1_operator_coverage_renderer()`
  - `write_phase1_operator_coverage_renderer()`
  - `load_phase1_operator_coverage_renderer()`
  - `PHASE1_OPERATOR_COVERAGE_RENDERER_SAFE_CLAIM`
  - `PHASE1_OPERATOR_COVERAGE_RENDERER_FILENAME`
- `mcp_server/city_ops/__init__.py`
  - exports the renderer builder/writer/loader
- `mcp_server/tests/city_ops/test_phase1_operator_coverage_renderer.py`
  - proves the renderer consumes only `phase1_operator_coverage_summary.json`
  - proves per-offer rows display adjacent `safe_to_claim[]` and `do_not_claim_yet[]`
  - proves persisted renderer output matches generated output
  - proves summary readiness promotions are rejected before rendering
  - proves per-row readiness promotions are rejected before rendering
  - proves forbidden safe claims remain blocked
  - proves temp-dir write/load behavior
  - proves persisted renderer load rejects readiness drift

New persisted artifact:

- `mcp_server/city_ops/fixtures/phase1_offer_fixture_specs/reviewed_outputs/phase1_operator_coverage_renderer.json`

## What the renderer consumes

The renderer consumes exactly one artifact by default:

- `phase1_operator_coverage_summary.json`

It explicitly refuses to depend on:

- raw transcripts
- raw review fixtures
- unreviewed memory
- freeform worker chat
- private operator context
- live Acontext transport
- GPS or metadata payloads

## What the renderer displays

The renderer returns a data-only internal payload with:

- coverage totals
- one row per Phase 1 offer
- fixture ID
- source file
- normalized outcome status
- source type
- follow-on task trigger
- proof status label
- adjacent `safe_to_claim[]`
- adjacent `do_not_claim_yet[]`
- deterministic display lines for a future internal/admin-only surface

Current Phase 1 rows:

1. `counter_reality_check`
2. `packet_submission_attempt`
3. `posting_compliance_check`

## Safe to claim

- `phase1_operator_coverage_renderer_landed`
- the persisted Phase 1 operator coverage summary can now be rendered through a deterministic read-only internal payload
- per-offer safe and blocked claims remain adjacent in generated and persisted renderer outputs
- the renderer refuses promoted readiness flags before rendering

## Still blocked / not safe to claim

- customer copy readiness
- operator UI readiness beyond a generated/read-only payload
- polished operator console readiness
- customer-visible catalog readiness
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
python3 -m py_compile mcp_server/city_ops/phase1_operator_coverage_renderer.py mcp_server/tests/city_ops/test_phase1_operator_coverage_renderer.py
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops -q
```

Result:

- `161 passed, 1 existing warning`

## Next smallest safe step

Mount this renderer behind an internal/admin-only read surface that uses the generated payload as-is.

The next surface must continue to refuse:

- customer copy
- autonomous dispatch
- live Acontext writes
- ERC-8004 reputation updates
- worker Skill DNA
- legal/regulator claims
- GPS/metadata exposure
- worker-copyable municipal doctrine

A good next implementation seam is a tiny internal route or CLI/debug command that calls `build_phase1_operator_coverage_renderer()` and returns only its `coverage_table`, `display_lines`, `claim_boundaries`, and `readiness` fields without adding new interpretation.
