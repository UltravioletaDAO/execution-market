# City-as-a-Service — Acontext Explicit Venv Preflight Rerun Implementation

> Date: 2026-05-16 02:00 dream continuation  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin proof-support artifact; no live Acontext parity claim

## Why this slice exists

The 01:00 Acontext prerequisite recovery attempt proved a narrow but useful fact:

- Docker is available.
- The Acontext CLI and compose manifest exist.
- `~/clawd/.venv-acontext` exists and imports `acontext==0.1.13`.
- The active Homebrew Python runner still cannot import `acontext`.
- Local API/dashboard services are still unreachable.

That left an ambiguity: is the SDK blocker absolute, or can the next preflight use the dedicated venv explicitly while the default runner is still unwired?

This slice makes the answer inspectable without broadening authority: the dedicated venv may be used for a **read-only preflight rerun only**, but it does not authorize a live write/retrieve parity attempt.

## Landed artifacts

```text
mcp_server/city_ops/acontext_explicit_venv_preflight_rerun.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_explicit_venv_preflight_rerun.json
mcp_server/tests/city_ops/test_acontext_explicit_venv_preflight_rerun.py
```

Safe latest claim:

```text
admin_acontext_explicit_venv_preflight_rerun_landed
```

## What the artifact records

The rerun artifact consumes only:

```text
acontext_prerequisite_recovery_attempt_log.json
```

It records:

- `runner_mode = explicit_dedicated_venv_probe`
- explicit venv SDK is available (`acontext==0.1.13`)
- active runner SDK is still unavailable
- compose pull was started in a longer 02:00 window but had not settled; it was stopped to avoid leaving an orphaned dream process
- compose services were not started
- local API and dashboard were still unreachable
- no live Acontext write was performed
- no live Acontext retrieval was performed

## Claim boundaries preserved

This is **not** any of the following:

- human/customer approval
- customer copy
- customer delivery
- publication
- public/catalog route
- controlled pilot exposure
- operator queue launch
- dispatch or autonomous dispatch
- ERC-8004 reputation receipt
- live Acontext sink readiness
- live memory transport swap
- runtime parity proof
- payment or production-infrastructure reverification
- exact GPS/raw metadata release
- legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability claim
- worker-copyable doctrine

## Why it matters

Before this slice, the setup state mixed two runner concerns:

1. the default city-ops runner cannot import `acontext`; and
2. a dedicated Acontext SDK venv can import it.

The new artifact separates those concerns. It gives the next operator a conservative path:

```text
use ~/clawd/.venv-acontext/bin/python for the next read-only preflight
```

while keeping all live transport gates closed until services and health probes are real.

## Next smallest safe proof

1. Let the compose image pull settle or rerun it with a long enough window; if it is silent for too long, capture the partial state and stop it deliberately.
2. Start the local Acontext compose services.
3. Healthcheck local API and dashboard.
4. Rerun the read-only preflight with the explicit venv runner.
5. Rebuild blocker delta, read surface, and attempt gate.
6. Attempt exactly one live write/retrieve parity pass only if the rebuilt gate explicitly allows it.

## Verification

Focused gate:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops/test_acontext_explicit_venv_preflight_rerun.py
# 9 passed
```

Full city-ops gate should be run before promotion into a broader handoff or route surface.
