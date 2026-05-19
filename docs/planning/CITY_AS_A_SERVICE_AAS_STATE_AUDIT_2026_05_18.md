# City-as-a-Service — AAS State Audit 2026-05-18

> Scope: Execution Market AAS / City-as-a-Service only  
> Status: internal/admin state audit; not customer copy; not launch readiness  
> Priority source: `~/clawd/DREAM-PRIORITIES.md`  
> Product posture: one narrow internal label approval exists; customer delivery and runtime parity remain blocked

## Sources checked

- `CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_05_18.md`
- `CITY_AS_A_SERVICE_FINAL_MORNING_HANDOFF_2026_05_18.md`
- `CITY_AS_A_SERVICE_AAS_SINGLE_BOUNDARY_HUMAN_OPERATOR_APPROVAL_RECORD_IMPLEMENTATION.md`
- `EXECUTION_MARKET_AAS_GAP_MAP_2026_05_12.md` including the May 18 update
- `CITY_AS_A_SERVICE_THREE_FAMILY_AAS_READINESS_MATRIX_2026_05_14.md` including the May 18 matrix note
- `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md` May 17/18 tail entries
- `CITY_AS_A_SERVICE_AAS_BLOCKED_CLAIM_TO_PROOF_MAP_2026_05_16.md` for stale-lane detection only

## Latest safe claims

1. `aas_single_boundary_human_operator_approval_record_landed` is now the latest customer-exposure-lane claim.
   - It covers exactly one Compliance Desk internal package-label text boundary: `Visible posting / notice compliance snapshot`.
   - The authorized delivery path remains `none_no_customer_delivery_authorized`.
   - It is an internal/admin approval record only, not publication or customer delivery.
2. Runtime-memory safe claims remain diagnostic/internal only:
   - `admin_acontext_docker_pull_path_diagnostic_landed`
   - `admin_aas_runtime_memory_blocker_decision_board_landed`
   - `admin_aas_intelligence_flow_compounder_landed`
3. Three-family AAS readiness remains conservative:
   - Compliance Desk: one internal label boundary approved, no delivery.
   - Document / Handoff Logistics: held at internal/admin sample-output decision.
   - Incident Verification: held at internal/admin sample-output decision.
4. Current committed baseline test count: `904 tests collected` for `mcp_server/tests/city_ops`. Latest handoff reports the full city-ops suite as `904 passed` after the approval-record implementation. A later working-tree collection may show `916 tests collected` because unrelated untracked delivery-publication-gate test files are present; those files are not part of this audit commit.

## Claims still blocked

Do not claim any of these from the May 18 approval record, matrices, runtime diagnostics, or coordination boards:

- customer copy readiness
- customer delivery approval
- publication approval
- public/catalog route readiness
- controlled pilot, front-door SKU, public pricing, or customer quote readiness
- operator queue launch
- dispatch or autonomous dispatch
- ERC-8004 reputation receipt attachment
- worker Skill DNA or worker-copyable doctrine
- live Acontext sink readiness, runtime parity, or durable live memory writes
- payment or production-infrastructure freshness
- exact GPS/raw metadata release or raw transcript authority
- legal/regulator/notarial/custody/emergency/safety/repair/insurance/SLA/official-report/fault-liability/domain-authority claims

## Recommended next proof paths

### Path A — customer-exposure lane

Start from `aas_single_boundary_human_operator_approval_record.json` and add a separate delivery/publication gate only if customer exposure is explicitly desired.

Required proof before any exposure:

1. exact approved-text parity with the May 18 record;
2. fresh delivery-time redaction checks;
3. explicit delivery-path authorization;
4. publication/customer-delivery approval if granted;
5. all unrelated readiness flags still false unless separately proven.

Do not publish directly from the approval record.

### Path B — runtime-memory lane

Do not attempt live parity directly. First prove prerequisites:

```text
repair Docker Desktop / containerd / network / layer-fetch
OR choose a trusted pre-populated image cache/mirror
-> verify all required Acontext images locally
-> start compose services
-> healthcheck API/dashboard
-> rerun read-only preflight
-> rebuild blocker/gate artifacts
-> run exactly one live write/retrieve parity pass only if the rebuilt gate is empty
```

### Path C — no-exposure internal planning lane

If no human delivery decision and no Acontext prerequisite fix are available, keep work internal/admin only:

- carry source artifact IDs;
- carry invariant IDs;
- keep declared-vs-verified badges explicit;
- keep safe and blocked claims adjacent;
- name exactly one next proof.

## Repo risks / operator cautions

- Current branch observed during this audit: `feat/operator-route-regret-panel`.
- Visible untracked files remain outside this audit and were not staged: `scripts/sign_req.mjs` plus untracked delivery-publication-gate code/test/fixture files.
- The May 18 handoff says the branch was already synced at `508567d3 Add May 18 AAS morning handoff`, after `b371eebd Add AAS single-boundary approval record`.
- Do not use broad staging commands. Stage this audit file explicitly if committing.
- Do not promote docs-only changes into deployment, production endpoint, customer route, or public copy claims.

## Stale docs / statements that should not guide tonight

1. `CITY_AS_A_SERVICE_AAS_BLOCKED_CLAIM_TO_PROOF_MAP_2026_05_16.md` is useful for lane structure but stale for customer-exposure state.
   - Its customer-exposure row still lists `aas_single_boundary_operator_review_brief_landed` and `aas_single_boundary_approval_record_validator_landed` as the active safe claims.
   - Its Branch B still says the next proof is creating a real human approval record.
   - After May 18, that record exists; the next proof is a separate delivery/publication gate over the approval record.
2. Older `CITY_AS_A_SERVICE_DAYTIME_EXECUTION_BOARD.md` sections before the May 17/18 tail entries should not be treated as current next-step authority.
   - Use the May 18 tail entry plus the May 18 final wrap/handoff as the current state.
3. Earlier handoffs that say the active next step is the approval-record validator, operator review brief, or human approval-record creation are superseded.
   - The latest approval-record safe claim is now landed, but it only approves the internal label boundary.
4. Any older note that says Docker/Acontext is merely missing basic prerequisites is incomplete.
   - The current blocker is narrower: GHCR manifests and arm64 indexes are reachable, but Docker Desktop / containerd / network / layer-fetch still stalls on the first GHCR Acontext image pull, or a trusted cache/mirror is needed.
5. `BACKLOG.md` is not an AAS state source for tonight.
   - It contains older Execution Market ops/security items and should not override the AAS final wrap, gap map, readiness matrix, or DREAM priority file.

## Audit conclusion

The May 18 state is narrower but safer: one Compliance Desk internal label boundary has an approval record, while every customer/public/runtime/dispatch/reputation/payment/GPS/domain-authority/worker-doctrine claim remains blocked. Tonight should not broaden readiness. The two meaningful proof paths are either a separate delivery/publication gate over the one approval record, or prerequisite-first Acontext image/service health leading to exactly one gated parity attempt.
