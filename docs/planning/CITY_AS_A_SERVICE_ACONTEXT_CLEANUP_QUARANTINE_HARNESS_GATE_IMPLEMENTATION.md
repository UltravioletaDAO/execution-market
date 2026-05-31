# City-as-a-Service — Acontext Cleanup / Quarantine Harness Gate

**Date:** 2026-05-31 03:00 ET dream checkpoint
**Scope:** Internal/admin Execution Market AAS planning only
**Safe claim added:** `admin_acontext_cleanup_quarantine_harness_gate_landed`

## Why this exists

The 02:00 checkpoint landed a disabled-by-default runtime adapter seam for the
future `irc_session_manager_memory_sink`. That seam correctly refused to register
or enable anything until separate cleanup/quarantine and multi-fixture replay
gates existed.

This checkpoint adds the first of those gates as a deterministic **local harness**.
It proves the control logic for two required paths without contacting Acontext or
mutating IRC runtime state:

1. **Success cleanup path** — simulated write/retrieve succeeds, then a
   delete/tombstone observation is required.
2. **Failed-write quarantine path** — simulated write fails, no retrieve happens,
   and a sanitized quarantine envelope is required.

The persisted artifact records only candidate labels, status classes, and
booleans. It does not persist runtime handles, session IDs, message IDs, raw
candidate text, raw metadata, GPS, private operator context, bearer values, or
project secrets.

## Files landed

- `mcp_server/city_ops/acontext_cleanup_quarantine_harness_gate.py`
- `mcp_server/tests/city_ops/test_acontext_cleanup_quarantine_harness_gate.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_cleanup_quarantine_harness_gate.json`

## Source artifact

- `acontext_opt_in_runtime_adapter_seam_contract.json`
- Source safe claim: `admin_acontext_opt_in_runtime_adapter_seam_contract_landed`

## What is now safe to say

- The disabled runtime adapter seam has a deterministic local cleanup/quarantine
  harness gate.
- The harness covers one success cleanup path and one failed-write quarantine
  path.
- Runtime handles are kept in process memory only; persisted data is limited to
  labels, status classes, and booleans.
- This is sufficient input for a **future separate multi-fixture replay gate**.

## What remains blocked

This gate still does **not** authorize:

- runtime adapter registration or enablement
- IRC session-manager mutation
- cross-project autorouting
- customer/public delivery, catalog, pricing, or publication
- operator queue launch or worker dispatch
- ERC-8004 reputation or Worker Skill DNA
- payment/production readiness claims
- GPS/raw metadata exposure
- private-context release
- worker-copyable doctrine
- general Acontext sink readiness
- runtime parity claims
- operator activation approval

## Next safe gate

Build a separate multi-fixture replay gate over at least two reviewed sanitized
fixtures, including success and hold/quarantine cases. That future gate should
continue persisting only labels/status/booleans and should still require a
separate explicit operator activation decision before runtime mutation.
