# City-as-a-Service — Acontext Opt-In Runtime Adapter Seam Contract

**Date:** 2026-05-31
**Scope:** Execution Market AAS / City-as-a-Service internal admin proof ladder
**Safe claim:** `admin_acontext_opt_in_runtime_adapter_seam_contract_landed`

## Governing boundary

`~/clawd/DREAM-PRIORITIES.md` controls this dream work. It allows Execution Market AAS / City-as-a-Service and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2. This slice stayed inside Execution Market AAS only.

## Why this exists

The previous proof block landed a fail-closed runtime-memory promotion gate after one redacted local Acontext runner succeeded. That gate deliberately said: one local 201/201/200 runner is useful for internal design, but it does **not** authorize runtime/session-manager mutation, customer/public delivery, dispatch, reputation, payment, GPS/raw metadata exposure, private-context release, or worker-copyable doctrine.

This contract turns the next implementation seam into a deterministic internal artifact before any runtime code is wired. It defines the shape of an opt-in adapter seam and the gates that must pass first.

## What landed

- `mcp_server/city_ops/acontext_opt_in_runtime_adapter_seam_contract.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_opt_in_runtime_adapter_seam_contract.json`
- `mcp_server/tests/city_ops/test_acontext_opt_in_runtime_adapter_seam_contract.py`
- `mcp_server/city_ops/__init__.py` export wiring

## Contract behavior

The artifact is read-only over the existing promotion gate. It does not contact Acontext, use tokens, record session/message IDs, register runtime hooks, mutate IRC session management, touch customer routes, launch dispatch, emit reputation, verify payments, expose private context, or publish worker instructions.

It defines:

1. **Disabled-by-default runtime insertion point**
   - `irc_session_manager_memory_sink`
   - status: `design_only_not_registered`
   - activation requires a separate operator opt-in after future gates

2. **Candidate input contract**
   - requires sanitized message text, sanitized metadata, source fixture ID, and operator hold default
   - requires sensitive/product booleans to be false
   - forbids root tokens, bearer tokens, project secrets, session IDs, message IDs, GPS coordinates, raw metadata, private context, customer copy, and worker instructions

3. **Cleanup/quarantine contract**
   - defined, not executed
   - must keep runtime IDs in process memory only
   - must record only status booleans
   - must provide quarantine handling for failed write/retrieve
   - must include delete/tombstone observation before activation

4. **Multi-fixture replay contract**
   - defined, not executed
   - requires at least two reviewed sanitized fixtures
   - must include success and hold cases
   - must reject private-context or GPS/raw-metadata fixtures
   - must not infer general Acontext sink readiness

5. **Rollback controls**
   - kill switch required
   - operator hold default
   - customer/worker surfaces, dispatch, reputation, and payment remain default false

## Claim boundary

Safe to claim:

```text
admin_acontext_opt_in_runtime_adapter_seam_contract_landed
```

Still blocked:

```text
runtime adapter registration
IRC runtime session-manager mutation
cross-project autorouting
customer copy/public/catalog delivery
pricing/customer quote
operator queue launch/dispatch
ERC-8004 reputation or Worker Skill DNA
payment/production readiness
exact GPS/raw metadata exposure
private operator context release
worker-copyable doctrine
general Acontext sink readiness
runtime parity
cleanup/quarantine execution
multi-fixture replay execution
```

## Verification

Targeted verification:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_opt_in_runtime_adapter_seam_contract.py
# 10 passed
```

Full city-ops verification should be run before final handoff/commit:

```bash
git diff --check && PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
```

## Next safe slice

Execute a cleanup/quarantine proof on reviewed sanitized fixtures while persisting only status booleans, then run a multi-fixture replay gate. Keep the adapter disabled until both pass and a separate operator activation decision exists.
