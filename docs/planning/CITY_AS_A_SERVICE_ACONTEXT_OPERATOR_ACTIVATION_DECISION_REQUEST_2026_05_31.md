# City-as-a-Service — Acontext Operator Activation Decision Request (2026-05-31)

> Scope: Execution Market AAS / City-as-a-Service internal/admin coordination only.
> Status: daytime operator decision request; no approval recorded.
> Governing priority: `~/clawd/DREAM-PRIORITIES.md`.

## 1. Source boundary

This request exists because the May 31 night completed the local proof ladder for a disabled Acontext runtime-memory adapter seam:

```text
root-prefixed local write/retrieve parity
-> internal IRC session adapter contract
-> redacted internal IRC session adapter runner fixture
-> fail-closed runtime-memory promotion gate
-> disabled-by-default opt-in runtime adapter seam contract
-> cleanup/quarantine harness gate
-> multi-fixture replay gate
-> this explicit operator activation decision request
```

This document records the exact human decision needed before any runtime adapter registration or IRC/session-manager mutation. It is not itself an approval.

## 2. Activation candidate

| Field | Value |
|---|---|
| Candidate ID | `irc_session_manager_memory_sink` |
| Source proof | `acontext_multi_fixture_replay_gate.json` |
| Latest safe claim | `admin_acontext_multi_fixture_replay_gate_landed` |
| Proposed runtime mutation | Register a disabled-by-default Acontext memory sink behind an explicit kill switch and operator opt-in. |
| Default decision | `hold_no_runtime_mutation` |
| Customer/worker exposure | none |

## 3. What the operator must explicitly answer

A human operator should choose exactly one of these options:

1. **Hold:** keep the adapter unregistered and continue using only local/replay fixtures.
2. **Approve design-only wiring:** allow code to add a disabled adapter registration path, with the kill switch defaulting off and no live IRC/session mutation.
3. **Approve one bounded local activation test:** allow exactly one sanitized local candidate through the adapter with cleanup/quarantine handling, no customer/worker surfaces, and rollback immediately after observation.

If the answer is not explicit, the system must stay at option 1: hold.

## 4. Required approval record fields if activation is chosen

A future approval record must include all of the following before any activation work proceeds:

- source artifact ID and digest from `acontext_multi_fixture_replay_gate.json`
- exact option selected: `design_only_wiring` or `one_bounded_local_activation_test`
- non-secret human/operator reference
- UTC timestamp
- kill-switch name and default-off confirmation
- rollback instruction and cleanup/quarantine requirement
- sanitized candidate source fixture ID if a bounded local test is approved
- confirmation that no session IDs, message IDs, bearer values, project secrets, raw metadata, GPS, private context, customer copy, or worker instructions will be persisted
- still-blocked claims carried forward unchanged

## 5. Still-blocked claims

This request does **not** approve:

```text
runtime adapter registration
runtime adapter enablement
IRC session-manager mutation
cross-project autorouting
customer copy/customer delivery/publication
public catalog route
pricing or customer quote
operator queue launch
worker dispatch
autonomous dispatch
ERC-8004 reputation
Worker Skill DNA
payment or production readiness
exact GPS or raw metadata release
private operator context release
domain authority claims
worker-copyable doctrine
general Acontext sink readiness
runtime parity beyond the named local/replay fixtures
```

## 6. Daytime recommendation

Recommended default: **hold** unless Saúl explicitly wants the runtime-memory path to continue today.

If continuing, choose option 2 first. Add only disabled design-only wiring behind a kill switch, then require a separate approval record before option 3. Do not jump directly from replay proof to live IRC/session-manager mutation.
