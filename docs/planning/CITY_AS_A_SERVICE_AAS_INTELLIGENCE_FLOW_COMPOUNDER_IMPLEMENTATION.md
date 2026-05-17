# City-as-a-Service — AAS Intelligence Flow Compounder Implementation

> Date: 2026-05-17 04:00 America/New_York
> Scope: Execution Market AAS / City-as-a-Service internal/admin coordination only
> Safe claim: `admin_aas_intelligence_flow_compounder_landed`

## Why this exists

The 4 AM dream prompt asked for late-night pattern recognition: which memory, IRC/session, cross-project, and agent-coordination patterns create exponential value.

`~/clawd/DREAM-PRIORITIES.md` explicitly blocks AutoJob, Frontier Academy, KK v2, and KarmaCadabra v2 during dream work, so this implementation keeps the pattern-recognition work strictly inside Execution Market AAS / City-as-a-Service.

The new artifact converts the existing coordination multiplier pattern map into a bounded intelligence-flow compounder. It answers:

- which insights can safely compound across AAS handoffs;
- which flows are internal filters rather than autonomous routing authority;
- which claim classes must stay quarantined until separate proof exists;
- which single next proof each flow points toward.

## Files added

- `mcp_server/city_ops/aas_intelligence_flow_compounder.py`
- `mcp_server/city_ops/fixtures/proof_blocks/redirect_outdated_packet_001/aas_intelligence_flow_compounder.json`
- `mcp_server/tests/city_ops/test_aas_intelligence_flow_compounder.py`

`mcp_server/city_ops/__init__.py` exports the build/load/write helpers.

## Source artifact

The compounder consumes only:

- `aas_coordination_multiplier_pattern_map.json`

It does not read raw transcripts, unreviewed memory, private operator context, worker chat, live Acontext sinks, payment probes, production probes, GPS/raw metadata payloads, customer-copy drafts, or worker-instruction templates.

## Intelligence flows captured

1. **Memory prerequisites → next proof**
   Preserve the exact runtime-memory blocker and next proof instead of repeating optimistic Acontext attempts.

2. **IRC/session IDs → coordination compression**
   Use the four invariant IDs as the handoff spine instead of replaying raw context.

3. **Cross-project patterns → claim quarantine**
   Reuse the proof ladder only when safe claims and blocked claims travel together.

4. **Agent selection → boundary preservation**
   Prefer agents that leave smaller verified proof deltas, not broader unproved surfaces.

## Quarantine rules

The artifact keeps five authority classes explicitly blocked:

- live runtime memory;
- customer/public packaging;
- dispatch/operator queue;
- reputation or worker Skill DNA;
- payment/production health.

Each class names the separate gate required before promotion. The compounder itself cannot auto-promote any of them.

## Readiness deliberately not promoted

This artifact does **not** approve or prove:

- live Acontext memory integration;
- runtime parity;
- IRC runtime/session-manager changes;
- autonomous cross-project routing;
- autonomous prioritization;
- customer-visible packaging;
- public/catalog routes;
- customer delivery or publication;
- controlled pilots;
- operator queue launch;
- dispatch or autonomous dispatch;
- ERC-8004 reputation receipts;
- worker Skill DNA;
- pricing or customer quotes;
- payment or production reverification;
- exact GPS/raw metadata release;
- worker-copyable doctrine.

## Operator use

Use the compounder as the 4 AM pattern-recognition entrypoint for future AAS dream/day handoffs:

1. Start from the four invariant IDs.
2. Treat cross-project intelligence as an internal filter, not autopilot.
3. Convert every insight into exactly one verifiable next proof.
4. Keep safe and blocked claims adjacent.
5. Route customer, dispatch, reputation, payment, GPS, live-memory, and worker-doctrine claims through separate gates.

## Verification

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q \
  mcp_server/tests/city_ops/test_aas_intelligence_flow_compounder.py \
  mcp_server/tests/city_ops/test_aas_coordination_multiplier_pattern_map.py
# 19 passed
```

Full city-ops suite was also run after documentation updates:

```bash
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m pytest -q mcp_server/tests/city_ops
# 892 passed
```

## Next safe step

The next proof remains narrow and prerequisite-first: fix or bypass the Docker Desktop/containerd layer-fetch stall, verify all nine required Acontext images are present, start services, healthcheck API/dashboard, rerun read-only preflight, rebuild an empty readiness gate, and attempt exactly one live write/retrieve parity pass only if the gate has no blockers.
