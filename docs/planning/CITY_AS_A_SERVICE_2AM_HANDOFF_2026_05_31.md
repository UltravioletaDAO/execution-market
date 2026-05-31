# City-as-a-Service — 2 AM Handoff (2026-05-31)

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this dream session. It explicitly allows Execution Market AAS / City-as-a-Service work and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2.

The cron payload still contained stale instructions to pull/analyze AutoJob, expand Frontier Academy, and continue KK v2. Those instructions conflicted with the active dream priority stop list, so they were not followed. No AutoJob, Frontier Academy, KK v2, or KarmaCadabra files were pulled, analyzed, edited, tested, or committed.

## Repo state

- Repo used: `projects/execution-market`
- Branch: `feat/operator-route-regret-panel`
- Sync check: `git pull --ff-only` returned `Already up to date`
- Pre-existing untracked file left untouched: `scripts/sign_req.mjs`

## What changed in this 2 AM slice

Added a disabled-by-default Acontext runtime adapter seam contract after the 1 AM runtime-memory promotion gate.

The 1 AM gate proved that one redacted local runner success can inform internal adapter design, but it still blocks runtime/session-manager mutation and all product/external claims. The new 2 AM contract converts the next seam into an explicit internal/admin contract before any runtime code is wired.

## Landed files

```text
mcp_server/city_ops/acontext_opt_in_runtime_adapter_seam_contract.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/acontext_opt_in_runtime_adapter_seam_contract.json
mcp_server/tests/city_ops/test_acontext_opt_in_runtime_adapter_seam_contract.py
docs/planning/CITY_AS_A_SERVICE_ACONTEXT_OPT_IN_RUNTIME_ADAPTER_SEAM_CONTRACT_IMPLEMENTATION.md
docs/planning/CITY_AS_A_SERVICE_2AM_HANDOFF_2026_05_31.md
```

Updated:

```text
mcp_server/city_ops/__init__.py
```

## Safe claim added

```text
admin_acontext_opt_in_runtime_adapter_seam_contract_landed
```

## Strategic position

Execution Market AAS now has a safer runtime-memory ladder:

```text
root-prefixed local write/retrieve parity
-> internal IRC adapter contract
-> redacted internal IRC adapter runner fixture
-> fail-closed runtime-memory promotion gate
-> disabled-by-default opt-in runtime adapter seam contract
-> next: cleanup/quarantine execution proof
-> then: multi-fixture replay gate
-> only then: separate operator activation decision
```

The new contract defines:

- a design-only `irc_session_manager_memory_sink` insertion point that is not registered or enabled
- a candidate input contract that forbids tokens, secrets, session IDs, message IDs, GPS coordinates, raw metadata, private context, customer copy, and worker instructions
- cleanup/quarantine requirements before any activation
- multi-fixture replay requirements before generalized sink claims
- rollback defaults: kill switch required, operator hold default, customer/worker/dispatch/reputation/payment defaults false

## Still blocked

The contract does **not** authorize:

```text
runtime adapter registration
IRC runtime session-manager mutation
cross-project autorouting
customer/public/catalog delivery
pricing/customer quote
operator queue launch or worker dispatch
ERC-8004 reputation or Worker Skill DNA
payment or production readiness
exact GPS/raw metadata exposure
private operator context release
worker-copyable doctrine
general Acontext sink readiness
runtime parity
cleanup/quarantine execution
multi-fixture replay execution
```

## Verification so far

Targeted verification passed:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q \
  mcp_server/tests/city_ops/test_acontext_opt_in_runtime_adapter_seam_contract.py
# 10 passed
```

Full city-ops verification remains the final gate before commit:

```bash
git diff --check && PYTHONPATH=. .venv/bin/python -m pytest -q mcp_server/tests/city_ops
```
