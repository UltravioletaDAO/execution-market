# City as a Service — 3 AM Stale Cron Firewall Work Queue Implementation (2026-06-12)

Status: internal/admin AAS coordination artifact landed; no stopped-project work performed

Safe claim: `internal_admin_aas_stale_cron_firewall_work_queue_landed`

Posture: `pause_aas_proof_layering`

## Why this exists

The 03:00 dream payload repeated older requests for AutoJob, Frontier Academy, and KK v2 work. `~/clawd/DREAM-PRIORITIES.md` was read first and still explicitly stops those lanes.

This slice turns that reconciliation into a deterministic tested work queue, so future dream agents have a small machine-checkable firewall before they accidentally treat stale cron text as fresher than the active priority file.

## What landed

New deterministic module:

```text
mcp_server/city_ops/aas_stale_cron_firewall_work_queue.py
```

New persisted fixture:

```text
mcp_server/city_ops/fixtures/aas_package_ladder/aas_stale_cron_firewall_work_queue.json
```

New tests:

```text
mcp_server/tests/city_ops/test_aas_stale_cron_firewall_work_queue.py
```

Package export added in:

```text
mcp_server/city_ops/__init__.py
```

## Source contract

The queue consumes the existing conservative system-integration strength bridge packet:

```text
aas_system_integration_strength_bridge_packet.json
```

It verifies:

- source bridge schema and digest;
- stopped-project firewall remains false for AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2;
- bridge lanes remain the expected memory/Acontext, IRC/session, decision support, observability, payment, production, and coordination handoff lanes;
- no promoted runtime, payment, production, customer, dispatch, reputation, or worker-doctrine claim slipped in.

## Stopped-lane decisions recorded

| Stale payload lane | Decision | Reason |
| --- | --- | --- |
| AutoJob pull / analysis / EM integration | skip | stopped by `DREAM-PRIORITIES.md` |
| Frontier Academy guide / PDF expansion | skip | stopped by `DREAM-PRIORITIES.md` |
| KK V2 swarm / reputation / lifecycle / orchestrator | skip | stopped by `DREAM-PRIORITIES.md` |
| KarmaCadabra v2 | skip | stopped by `DREAM-PRIORITIES.md` |

No `git pull` was run in stopped repositories.

## System-integration connections preserved safely

The queue connects the requested strengths only inside the allowed AAS lane:

1. **Memory ↔ Acontext planning** — carry reviewed digests, safe claims, blocked claims, next gate, and posture; no live write/retrieve claim.
2. **IRC/session management** — use read-only handoff capsules and sticky blocked claims; no IRC/session-manager mutation.
3. **Cross-project decision support** — present a hold/answer menu later only if a real operator answer exists; no cross-project autorouting.
4. **Agent observability** — score priority precedence, blocked-claim preservation, and one-next-gate discipline; no public/customer dashboard claim.
5. **8-chain payments + production maturity** — keep as future launch prerequisite context only; no payment, chain, or production reverification from this queue.

## Allowed next actions

The queue now records the only safe selectors:

1. If a real operator answer arrives later: create exactly one separate digest-backed answer receipt, then run the specific gate.
2. If no real operator answer exists: keep `pause_aas_proof_layering` and avoid downstream proof wrappers.
3. If runtime truth becomes available later: run the already-defined Acontext/runtime prerequisite gates before any live parity attempt.
4. If future cron text mentions stopped projects: read `DREAM-PRIORITIES.md` first and ignore stopped-project instructions unless that file changes.

## Explicit non-claims

This work does **not** create an operator answer, approval, answer receipt, selected answer value, customer/public/worker surface, catalog, pricing, route, queue, dispatch, runtime Acontext/IRC/session-manager mutation, live Acontext write/retrieve, payment/production/chain reverification, ERC-8004 reputation receipt, Worker Skill DNA, exact GPS/raw metadata/private-context/PII release, authority claim, worker-copyable doctrine, or stopped-project integration.

## Verification

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_aas_system_integration_strength_bridge_packet.py \
  mcp_server/tests/city_ops/test_aas_stale_cron_firewall_work_queue.py
```

Result:

```text
20 passed
```

## Next safe step

Stop proof layering until one of these changes:

- `DREAM-PRIORITIES.md` changes;
- a real operator answer arrives;
- runtime Acontext evidence is available and the prerequisite gates pass.

Until then, the useful work is preserving source-of-truth discipline, not adding another wrapper.
