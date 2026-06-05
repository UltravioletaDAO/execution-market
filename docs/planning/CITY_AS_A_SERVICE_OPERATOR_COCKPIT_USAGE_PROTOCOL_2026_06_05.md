# City-as-a-Service — Operator Cockpit Usage Protocol (2026-06-05)

> Scope: Execution Market AAS / City-as-a-Service internal/admin operating protocol only.
> Governing priority: `/Users/clawdbot/clawd/DREAM-PRIORITIES.md`.
> Source surface: `CITY_AS_A_SERVICE_AAS_OPERATOR_COCKPIT_READ_SURFACE_IMPLEMENTATION.md` and `mcp_server/city_ops/fixtures/aas_package_ladder/aas_operator_cockpit_read_surface.json`.
> Safe claim: `internal_admin_aas_operator_cockpit_usage_protocol_landed`.
> Status: read-only usage aid; not an answer record, approval record, runtime change, product exposure, buyer copy, worker instruction, queue, dispatch, payment, reputation, public dashboard, or stopped-project integration.

## 1. Why this exists

The June 4 operator cockpit made the current AAS hold state compact enough for a human/operator to read. This protocol answers the next practical question: **how should that cockpit be used without accidentally turning display text into approval?**

It is intentionally not another proof wrapper. It is a stop/act runbook for the existing cockpit:

1. open the cockpit;
2. read the current truth panes;
3. choose whether a real operator answer exists;
4. if no answer exists, stop or keep both lanes held;
5. if an answer exists, create exactly one separate answer artifact before doing anything else.

No answer is recorded here. No future path is selected here.

## 2. Current source posture

Current source-of-truth stack for this protocol:

| Source | Role | Authority limit |
| --- | --- | --- |
| `CITY_AS_A_SERVICE_PRE_DAWN_SYNTHESIS_2026_06_04.md` | Current synthesis entrypoint | says AAS has enough internal/admin structure; next movement needs pause/hold or one explicit answer |
| `CITY_AS_A_SERVICE_6AM_FINAL_WRAP_2026_06_04.md` | Sealed June 4 morning handoff | preserves the default `pause_aas_proof_layering` / `keep_both_lanes_held` posture |
| `CITY_AS_A_SERVICE_AAS_OPERATOR_COCKPIT_READ_SURFACE_IMPLEMENTATION.md` | Deterministic cockpit surface | displays state and allowed values but selects none |
| `CITY_AS_A_SERVICE_OPERATOR_PACKAGING_PLAN_2026_06_04.md` | Operator package framing | label-only; not buyer copy, catalog, quote, or dispatch |
| `EXECUTION_MARKET_AAS_BROADER_CONCEPT_CATALOG_2026_06_04.md` | Broader AAS taxonomy | concept catalog only; no active launch authority |

The stopped-project firewall remains active: AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 are not active dream workstreams and are not sources of authority for this protocol.

## 3. Five-minute cockpit use sequence

Use this exact order when Saúl or an operator asks, “what should we do with City-as-a-Service next?”

### Step 1 — Open the cockpit, not old plans

Start from:

```text
mcp_server/city_ops/fixtures/aas_package_ladder/aas_operator_cockpit_read_surface.json
```

Do not start from older master plans, May concept maps, route/flywheel docs, generic service catalogs, or stale cron payloads. Those can be background context only after the current cockpit state is read.

### Step 2 — Read the safe claim beside blocked claims

The only safe cockpit claim is:

```text
internal_admin_aas_operator_cockpit_read_surface_landed
```

Meaning only: an internal/admin read-only cockpit exists and is tested.

It does not mean:

- operator answer recorded;
- operator approval recorded;
- product exposure approved;
- runtime-memory wiring approved;
- Docker/Acontext readiness restored;
- public/customer/worker surface ready;
- queue, dispatch, payment, or reputation path ready;
- private context, exact location, raw metadata, or authority release ready;
- stopped-project integration approved.

### Step 3 — Check whether a real answer exists

A real answer exists only if Saúl/operator explicitly gives one of these values or a family-specific answer/hold record that references one of these values:

```text
keep_both_lanes_held
create_retail_reality_answer_or_hold_record
create_runtime_memory_operator_answer_record
pause_aas_proof_layering
```

The cockpit displaying those values is not an answer. This protocol listing those values is not an answer.

### Step 4 — If no answer exists, choose only a no-movement posture

Allowed no-answer outcomes:

```text
pause_aas_proof_layering
keep_both_lanes_held
```

Operational meaning:

- do not create more no-answer proof layers;
- do not start Docker/Compose/Acontext work;
- do not draft buyer copy;
- do not expose package/catalog/price/queue language;
- do not create worker instructions;
- do not attach ERC-8004 reputation or Worker Skill DNA;
- do not use stopped-project material as active evidence.

### Step 5 — If an answer exists, create exactly one separate artifact

If Saúl/operator explicitly chooses product exposure:

```text
create_retail_reality_answer_or_hold_record
```

then the next artifact must be a separate Retail Reality answer/hold record. It must include approved-or-held text, redactions passed, delivery path status, blocked claims, and rollback rule. It must not publish or dispatch.

If Saúl/operator explicitly chooses runtime memory:

```text
create_runtime_memory_operator_answer_record
```

then the next artifact must be a separate runtime-memory answer record. After that, restore Docker daemon reachability and rerun read-only image/container/Compose/API/core/UI inventory before any bounded activation attempt.

If Saúl/operator explicitly chooses hold/pause, record only a small hold/pause note and stop.

## 4. Decision receipt shape for future use

If a real answer appears later, the receipt should be small and explicit:

```yaml
answer_receipt_id: execution_market.aas.operator_answer.<date>.<short_label>
source_cockpit_ref: mcp_server/city_ops/fixtures/aas_package_ladder/aas_operator_cockpit_read_surface.json
operator_answer_value: <one of the four allowed values>
operator_answer_recorded: true
operator_approval_recorded: <true only if explicit approval text exists>
approved_sections: []
held_sections: []
redactions_passed: false
delivery_path_authorized: false
runtime_path_authorized: false
blocked_claims_preserved: true
next_required_gate: <one gate only>
```

This protocol does **not** fill that receipt. It only defines the safe future shape.

## 5. Anti-drift checklist

Before using any AAS planning artifact after the cockpit, answer these questions:

| Question | Required answer before movement |
| --- | --- |
| Was `DREAM-PRIORITIES.md` read first? | yes |
| Is the source artifact the cockpit or a direct child of it? | yes |
| Is exactly one allowed answer value present as explicit operator text? | yes, or no-movement only |
| Are safe and blocked claims adjacent? | yes |
| Are AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 absent from active sources? | yes |
| Are exact GPS/raw metadata/private context absent? | yes |
| Is buyer copy/public catalog/worker doctrine absent unless separately approved? | yes |
| Is Docker/Acontext parity claimed only after fresh runtime proof? | yes |
| Is dispatch/reputation/payment claimed only after separate proofs? | yes |

If any answer is missing, stop at `pause_aas_proof_layering` or `keep_both_lanes_held`.

## 6. Operator copy/paste prompts, internal only

These prompts are for an internal operator note, not public copy.

### Hold both lanes

```text
AAS cockpit reviewed. No product/runtime answer is being recorded. Keep both lanes held. No buyer copy, runtime mutation, dispatch, reputation, payment, private-context, location, authority, worker-doctrine, or stopped-project movement is authorized.
```

### Pause proof layering

```text
AAS cockpit reviewed. Pause proof layering because the current internal/admin structure is sufficient and no explicit operator answer exists. Next movement requires one separate answer artifact or fresh runtime prerequisite proof after Docker reachability is restored.
```

### Product-exposure answer path

```text
AAS cockpit reviewed. Operator explicitly requests a separate Retail Reality answer/hold record. Do not publish, price, queue, dispatch, or create buyer/worker copy. First artifact must record approved-or-held text, redactions, delivery path status, blocked claims, and rollback rule.
```

### Runtime-memory answer path

```text
AAS cockpit reviewed. Operator explicitly requests a separate runtime-memory answer record. Do not mutate runtime, register adapters, or write/retrieve live Acontext yet. First restore Docker reachability and rerun read-only runtime inventory after the answer record exists.
```

## 7. Safe-to-claim / do-not-claim-yet

Safe to claim from this protocol:

```text
internal_admin_aas_operator_cockpit_usage_protocol_landed
```

Meaning only: a read-only internal usage protocol exists for using the AAS operator cockpit without converting display state into approval.

Do not claim yet:

```text
operator_answer_recorded
operator_approval_recorded
retail_reality_answer_or_hold_record_created
runtime_memory_operator_answer_record_created
product_exposure_approved
buyer_copy_ready
public_catalog_ready
pricing_ready
queue_ready
dispatch_ready
worker_instruction_ready
live_acontext_ready
runtime_parity_proven
runtime_adapter_registered
irc_session_manager_mutated
cross_project_autorouting_ready
erc8004_reputation_ready
worker_skill_dna_ready
payment_production_reverified
exact_gps_or_raw_metadata_release_ready
private_context_release_ready
domain_authority_ready
worker_copyable_doctrine_ready
stopped_project_integration_ready
```

## 8. Next safe move

Default next move remains:

```text
pause_aas_proof_layering
```

Alternative safe hold:

```text
keep_both_lanes_held
```

Only move beyond that if Saúl gives one explicit answer value. Then create exactly one separate answer artifact before product/runtime work.
