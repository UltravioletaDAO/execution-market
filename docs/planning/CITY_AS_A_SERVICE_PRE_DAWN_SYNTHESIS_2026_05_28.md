# City-as-a-Service — Pre-Dawn Synthesis (2026-05-28)

## Governing priority

`~/clawd/DREAM-PRIORITIES.md` was read first and controlled this 5 AM synthesis. It explicitly allows Execution Market AAS / City-as-a-Service work and explicitly stops AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream sessions.

The cron payload still contained stale instructions to pull/analyze AutoJob, expand Frontier Academy, and continue KK v2. Those tracks were not pulled, analyzed, edited, expanded, tested, or committed. This synthesis stayed inside Execution Market AAS / City-as-a-Service only.

## Repo state

- Repo: `projects/execution-market`
- Branch: `feat/operator-route-regret-panel`
- Sync check: `git pull --ff-only` returned `Already up to date`
- Pre-existing untracked file left untouched: `scripts/sign_req.mjs`
- Latest pushed implementation before this synthesis: `fcefe456` (`Add AAS next truth selector`)

## What tonight connected

The night moved the AAS portfolio from “more internal coordination surfaces” into a cleaner truth-selection posture:

```text
portfolio promotion ledger
-> portfolio next-gate board
-> no-answer operator authorization packet
-> system-integration route handoff
-> route pickup board
-> route regret panel
-> runtime truth queue
-> next truth selector
```

The important shift is that the system now knows when to stop documenting and when to demand a new kind of evidence. The route regret panel and next truth selector agree: without runtime evidence or a real operator answer, another route/read-surface/handoff layer adds ceremony, not truth.

## Current decision

Selected daytime track:

```text
runtime_truth_prerequisite_activation
```

Selected proof:

```text
clear_acontext_sdk_api_dashboard_then_rerun_read_only_preflight
```

Meaning: daytime should focus on the Acontext/Docker prerequisite chain before any live Memory ↔ Acontext parity attempt.

This is not permission to run a live write/retrieve parity pass yet. The prerequisite order remains:

1. Docker daemon/socket reachable and Buildx healthy.
2. Required Acontext image inventory checked/present.
3. Local Acontext API and dashboard reachable after Compose startup.
4. Read-only live preflight / readiness gate rebuilt with no blockers.
5. Exactly one bounded live write/retrieve parity attempt, only if the readiness gate explicitly allows it.

## Strategic synthesis

### 1. The highest multiplier is now runtime truth, not another AAS wrapper

The proof ladder has enough internal/admin wrappers to preserve claims. The next valuable artifact must reduce uncertainty about live runtime state. Acontext is the leverage point because it can turn memory, handoffs, route regrets, and proof anchors into retrievable context instead of static docs.

### 2. Operator truth is the only customer-exposure fork

Retail Reality and Compliance Desk remain the cleanest possible customer-exposure candidates, but only through a separate human/operator decision artifact. No current synthesis, board, queue, selector, or route packet should be treated as approval.

Allowed later, only with a real answer:

- Retail Reality selected-boundary approval/hold record; or
- Compliance Desk delivery/publication gate with one exact delivery path.

Without that answer, all five AAS families stay internal/admin-only.

### 3. The stale-priority firewall is part of product quality

Repeated stale cron payloads still mention AutoJob, Frontier Academy, and KK v2. `DREAM-PRIORITIES.md` is now functioning as a decision-support guardrail, not just a reminder. It prevents the AAS workstream from fragmenting into old project lanes while the City-as-a-Service proof ladder is close to a real runtime unlock.

### 4. Claim quarantine has become the operating model

The strongest pattern across the night is restraint as progress:

```text
prevented overclaim -> blocked claim adjacency -> next proof selector -> one safer next gate
```

This is the core AAS operating model. It lets Execution Market package real-world proof without accidentally claiming public routes, customer delivery, dispatch readiness, reputation portability, exact-location release, legal/domain authority, or worker-copyable doctrine.

## Current safe claims

Safe to claim from tonight's new rungs:

```text
internal_admin_aas_system_integration_flywheel_route_handoff_packet_landed
internal_admin_aas_system_integration_flywheel_route_pickup_board_landed
internal_admin_aas_system_integration_flywheel_route_regret_panel_landed
internal_admin_aas_system_integration_runtime_truth_queue_landed
admin_aas_next_truth_selector_landed
```

Safe to say strategically:

```text
route_expansion_should_stop_until_runtime_or_operator_truth_exists
runtime_truth_prerequisite_activation_is_the_selected_next_track
acontext_read_only_preflight_must_be_rebuilt_before_any_live_parity_attempt
operator_customer_exposure_requires_a_separate_human_decision_artifact
```

## Still blocked / not safe to claim

Do not infer any of the following:

```text
customer_copy_ready
customer_delivery_approved
publication_approved
public_catalog_ready
public_route_ready
public_pricing_or_customer_quote_ready
paid_pilot_ready
operator_queue_launch_ready
autonomous_dispatch_ready
live_acontext_runtime_parity
acontext_sink_ready
acontext_retrieval_ready
irc_runtime_session_manager_enhanced
autojob_integration_ready
frontier_academy_expansion_ready
kk_v2_swarm_ready
erc8004_reputation_ready
worker_skill_dna_ready
payment_or_production_reverified
exact_gps_or_raw_metadata_release_allowed
private_operator_context_release_allowed
raw_transcript_authority
legal_or_regulator_or_domain_authority
emergency_or_safety_authority
repair_or_insurance_or_sla_authority
official_report_or_fault_liability_authority
dataset_or_analytics_publication_ready
worker_copyable_aas_doctrine
worker_copyable_municipal_doctrine
```

## Daytime action board

Pick exactly one fork.

### Fork A — recommended engineering move

Prove the runtime prerequisites for Acontext, then rerun the read-only gate.

Concrete pickup order:

1. Confirm Docker daemon/socket and active context.
2. Confirm Buildx health.
3. Check required Acontext images and containers.
4. Start or verify the local Acontext API/dashboard.
5. Rebuild the live preflight blocker delta and read surface.
6. Only if the readiness gate is empty, prepare exactly one bounded live write/retrieve parity attempt.

Stop line: if any prerequisite fails, record a prerequisite observation/recovery artifact only. Do not claim parity.

### Fork B — recommended product-decision move if Saúl wants customer exposure

Create exactly one separate human/operator answer artifact for one prepared question:

1. Retail Reality selected-boundary approval/hold; or
2. Compliance Desk delivery/publication gate with an exact delivery path.

Stop line: if no real human answer exists, do not create an approval record. Keep all AAS families internal/admin-only.

### Fork C — safe pause

If neither runtime prerequisites nor a human answer are available, stop. Reuse the pickup board, route regret panel, runtime truth queue, and next truth selector as the current coordination handoff. Do not add more route layers.

## Handoff recommendation

The daytime headline should be:

> “The AAS ladder has enough coordination structure. Next progress must be truth-producing: either prove Acontext runtime prerequisites or capture one explicit human operator decision. Otherwise, stop and preserve the current proof boundary.”

## Verification for this synthesis

This is a documentation and coordination synthesis over already-landed implementation artifacts. No code or fixture contract changed in this 5 AM pass.

Required local verification before commit:

```bash
git diff --check
.venv/bin/python -m pytest -q mcp_server/tests/city_ops/test_aas_next_truth_selector.py
```

Full city-ops verification from the preceding implementation remains:

```text
.venv/bin/python -m pytest -q mcp_server/tests/city_ops
# 1442 passed
```
