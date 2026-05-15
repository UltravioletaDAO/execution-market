# City as a Service — AAS System Integration Flywheel Implementation

> Created: 2026-05-15 03:05 America/New_York  
> Scope: Execution Market AAS / City-as-a-Service only  
> Status: conservative read-only integration flywheel landed; no live Acontext, payment, production, dispatch, or customer-visible readiness promoted

## 1. Why this slice exists

The dream prompt asked for connections between four system-integration tracks:

- memory system ↔ Acontext integration planning
- IRC session management enhancement
- cross-project decision support systems
- agent observability and success metrics

`DREAM-PRIORITIES.md` overrides older AutoJob, Frontier Academy, and KK V2 requests, so this slice stays inside Execution Market AAS / City-as-a-Service.

The new artifact is a small, deterministic flywheel that lets future agents and operators see how the current strengths reinforce one another **without accidentally promoting unproven readiness**.

## 2. New files

```text
mcp_server/city_ops/aas_system_integration_flywheel.py
mcp_server/tests/city_ops/test_aas_system_integration_flywheel.py
mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_system_integration_flywheel.json
docs/planning/CITY_AS_A_SERVICE_AAS_SYSTEM_INTEGRATION_FLYWHEEL_IMPLEMENTATION.md
```

`mcp_server/city_ops/__init__.py` now exports:

```python
build_aas_system_integration_flywheel
load_aas_system_integration_flywheel
write_aas_system_integration_flywheel
```

## 3. New schema

```text
city_ops.aas_system_integration_flywheel.v1
```

Safe claim added:

```text
aas_system_integration_flywheel_landed
```

## 4. Source contract

The flywheel consumes only the existing decision-support readiness matrix:

```text
city_ops.decision_support_readiness_matrix.v1
```

It preserves these invariants:

- read-only source consumption
- no live sink write
- no raw conversation replay
- no semantic reinterpretation
- no payment-system reverification
- no production-infrastructure reverification
- no Acontext sink readiness promotion

## 5. Strengths connected

The artifact records five strength inputs and labels whether they were consumed from the local proof graph or merely declared and not reverified by this slice:

| Strength | Verification level in this artifact | Safe use |
|---|---|---|
| Latest `city_ops` code changes | consumed from local artifact graph | Use recent proof slices as the bounded implementation substrate |
| 8/8 chain payment integration | declared, not reverified | Use as production-confidence context only; do not restate as freshly verified |
| Intelligent memory with 26+ insights | declared, not recounted | Shape memory/Acontext requirements without writing live memory |
| Production infrastructure operational | declared, not reverified | Prefer deployable admin/operator seams, but keep this slice non-deploying |
| Legendary agent coordination | consumed from decision-support matrix | Codify invariant-ID handoff and claim-boundary preservation |

This separation is the important part: future agents can use the strengths as planning context without repeating claims the slice did not verify.

## 6. Connection loops

The flywheel names five loops:

1. **Reviewed memory → Acontext → better dispatch**
   - Uses `memory_system_to_acontext_bridge`
   - Guardrail: no `acontext_sink_ready` until live write/retrieve parity passes

2. **IRC session IDs → cross-session continuity**
   - Uses `irc_session_management`
   - Guardrail: normal path uses invariant IDs, not raw transcript replay

3. **Decision matrix → cross-project operator choices**
   - Uses `cross_project_decision_support`
   - Guardrail: require a second reviewed municipal case before cross-case doctrine

4. **Observability → agent success metrics**
   - Uses `agent_observability_success_metrics`
   - Guardrail: planning metrics are not a live dashboard or customer-visible metric surface

5. **Payment confidence → deployable AAS boundaries**
   - Uses `cross_project_decision_support`
   - Guardrail: this artifact does not rerun or restate 8/8 payment verification

## 7. Readiness posture

The flywheel may claim only:

```text
aas_system_integration_flywheel_landed
```

It must keep these false:

```text
flywheel_promotes_live_readiness=false
acontext_sink_ready=false
runtime_parity_proven=false
autonomous_dispatch_ready=false
customer_visible_packaging_ready=false
payment_coverage_reverified_by_this_artifact=false
worker_copyable_doctrine_ready=false
```

It also adds blocked claims for live Acontext, runtime parity, autonomous dispatch, customer-visible packaging, public route readiness, payment revalidation, and worker-copyable doctrine.

## 8. IRC/session-management enhancement rules

The artifact adds four operator/agent session rules:

1. **Four-ID session header** — include `proof_anchor_id`, `coordination_session_id`, `compact_decision_id`, and `review_packet_id` at the top of every IRC/admin handoff.
2. **Declared-vs-verified badges** — label payment, infrastructure, and memory-strength claims before agents repeat them.
3. **Blocked-claim sticky footer** — render blocked claims after every recommendation, not only in debug artifacts.
4. **Single next-proof slot** — keep the readiness matrix recommendation visible instead of letting agents invent parallel proof ladders.

## 9. Operator next actions

The flywheel recommends four next actions, each with a claim that can unlock only if independently proven:

| Action | Why | Claim unlocked only if passes |
|---|---|---|
| Live Acontext parity probe | Turn memory/Acontext bridge from planned/attemptable into verified sink behavior | `acontext_live_transport_parity_landed` |
| Admin flywheel read surface | Let operators see strength connections without reading the full proof bundle | `admin_system_integration_flywheel_surface_landed` |
| Separate payment and infra probe | Avoid mixing AAS planning proof with payment/production-health claims | `payment_and_infra_status_reverified_for_aas_packaging` |
| Preserve matrix recommendation | Keep the current decision-support next step visible | current matrix `recommended_next_action` |

## 10. Test coverage

Added tests cover:

- fixture equality
- all four required axes connected
- all five strengths represented
- declared-but-not-reverified badges for payment and infrastructure
- blocked-claim preservation
- attemptable live transport without readiness promotion
- refusal of promoted Acontext readiness
- refusal of blocked claims in `safe_to_claim`
- refusal of missing required axes
- temp write/load roundtrip
- loader refusal when payment reverification is falsely marked true

Targeted gate:

```bash
PYTHONPATH=. python3 -m pytest mcp_server/tests/city_ops/test_aas_system_integration_flywheel.py
```
