# City as a Service — Acontext Live Parity Attempt Readiness Gate Implementation

> Date: 2026-05-15 23:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal/admin proof only
> Status: landed as fail-closed local artifact + tests
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`

## Why this exists

The Acontext blocker-delta read surface made the partial prerequisite state visible: Docker cleared, but the Acontext Python SDK, local API, and dashboard were still blocked. That surface is useful, but it should never be treated as permission to run a live write/retrieve parity attempt.

This slice adds the missing launch-control seam: an explicit fail-closed gate that consumes the blocker read surface and answers one question only:

> May we attempt the live Acontext write/retrieve parity run now?

Current answer: **no**.

## Landed artifacts

- `mcp_server/city_ops/acontext_live_parity_attempt_readiness_gate.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_live_parity_attempt_readiness_gate.json`
- `mcp_server/tests/city_ops/test_acontext_live_parity_attempt_readiness_gate.py`

Safe claim added:

```text
admin_acontext_live_parity_attempt_gate_landed
```

## Source consumed

The gate consumes only:

```text
acontext_live_preflight_blocker_delta_read_surface.json
```

It preserves the same proof-anchor/session/decision IDs from the read surface and does not reinterpret raw transcripts, private operator context, unreviewed memory, freeform worker chat, payment probes, production probes, GPS/raw metadata payloads, customer-copy drafts, or worker instruction templates.

## Current verdict

```text
live_parity_attempt_blocked_prerequisites_missing
```

The gate keeps these blockers active:

```text
acontext_python_sdk_missing
local_acontext_api_unreachable
local_acontext_dashboard_unreachable
```

Docker being cleared is recorded only as prerequisite progress. It does not authorize a live write/retrieve attempt.

## Allowed next action classes

The gate allows only prerequisite and preflight-only work:

1. install or mount the Acontext Python SDK;
2. start or reach the local Acontext API;
3. start or reach the local Acontext dashboard;
4. rerun the preflight without performing live writes or retrievals;
5. rebuild the blocker delta, read surface, and this gate from the new preflight result.

## Explicitly still blocked

This gate does **not** authorize or prove:

- live Acontext write/retrieve attempt started or completed;
- live Acontext sink readiness;
- runtime parity;
- live memory transport swap readiness;
- customer-visible AAS packaging;
- customer copy;
- public/catalog route;
- operator queue launch;
- autonomous dispatch;
- ERC-8004 reputation;
- payment coverage;
- production infrastructure health;
- exact GPS/raw metadata release;
- worker-copyable municipal doctrine.

## Validation

Focused gate:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_live_parity_attempt_readiness_gate.py \
  mcp_server/tests/city_ops/test_acontext_live_preflight_blocker_delta_read_surface.py
# 16 passed
```

## Next smallest proof

Clear the remaining SDK/API/dashboard blockers, rerun the preflight, and rebuild this gate. Only a future gate built from a blocker-free preflight should consider authorizing one live Acontext write/retrieve parity attempt, and even that would still be separate from customer/public/dispatch/reputation/runtime-product launch claims.
