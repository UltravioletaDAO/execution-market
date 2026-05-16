# City-as-a-Service — 2 AM Handoff 2026-05-16

> Status: 2 AM dream continuation  
> Scope: Execution Market AAS / City-as-a-Service only  
> Priority source: `~/clawd/DREAM-PRIORITIES.md`  
> Product posture: internal/admin only; no customer/public launch claim

## Governing priority note

The cron payload still listed AutoJob, Frontier Academy, and KK v2 work, but `~/clawd/DREAM-PRIORITIES.md` explicitly stops those workstreams during dreams. This pass followed the priority file and stayed inside Execution Market AAS / City-as-a-Service.

`projects/execution-market` was synced with `git pull --ff-only` and was already up to date on `feat/operator-route-regret-panel`. The pre-existing untracked `scripts/sign_req.mjs` remained untouched.

## What changed at 2 AM

### Explicit venv preflight path is now captured fail-closed

The previous Acontext recovery log showed that the default Homebrew Python runner cannot import `acontext`, while `~/clawd/.venv-acontext` can import `acontext==0.1.13`.

This pass added a new internal/admin artifact that separates those two runner paths:

```text
mcp_server/city_ops/acontext_explicit_venv_preflight_rerun.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_explicit_venv_preflight_rerun.json
mcp_server/tests/city_ops/test_acontext_explicit_venv_preflight_rerun.py
docs/planning/CITY_AS_A_SERVICE_ACONTEXT_EXPLICIT_VENV_PREFLIGHT_RERUN_IMPLEMENTATION.md
```

Safe latest claim:

```text
admin_acontext_explicit_venv_preflight_rerun_landed
```

Meaning: the dedicated venv is available for a future read-only preflight rerun, but this does **not** authorize a live Acontext write/retrieve parity attempt.

## Current Acontext state

Confirmed locally during this pass:

- Docker is available.
- The Acontext compose manifest and `.env` exist under `~/clawd/infra/acontext`.
- The dedicated SDK venv imports `acontext==0.1.13`.
- The active Homebrew Python runner still cannot import `acontext`.
- Local API `localhost:8029` and dashboard `localhost:3000` were not reachable at capture time.
- A longer compose image pull was started, did not settle inside the 2 AM window, and was stopped deliberately to avoid leaving an orphaned process.

## What did not change

No approval or readiness was promoted for:

- customer copy
- customer delivery
- publication
- public/catalog routes
- controlled pilots
- public prices or customer quotes
- operator queue launch
- dispatch or autonomous dispatch
- ERC-8004 reputation receipts
- live Acontext sink readiness
- runtime parity
- payment or production-infrastructure reverification
- exact GPS/raw metadata release
- domain-authority, legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability claims
- worker Skill DNA or worker-copyable doctrine

## Next safe step

Use this exact sequence:

1. Let the compose image pull settle, or rerun it with a long enough window; stop and log partial state if it stays silent too long.
2. Start local Acontext compose services.
3. Healthcheck API and dashboard.
4. Rerun the read-only preflight with `~/clawd/.venv-acontext/bin/python` if the default runner remains unwired.
5. Rebuild blocker delta, read surface, and attempt gate.
6. Attempt exactly one live write/retrieve parity pass only if the rebuilt gate explicitly allows it.

## Verification

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops/test_acontext_explicit_venv_preflight_rerun.py
# 9 passed

PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 798 passed
```
